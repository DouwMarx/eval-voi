"""Over-determined elicitation of the Gaussian-state model (chapter, "An
elicitation protocol for the Gaussian-state model"; spec v2.1): validation of
the Gaussian JSON payload and the mapping of the eight questions onto the
stored quantities, with per-quantity residuals and warnings.

Questions (all in the expert's own state unit u, bad is high, and USD):
  Q1  theta:  p5 / p50 / p95 of theta
              -> mu0 = p50, sigma0 = (p95 - p5) / 3.29
                 residual = |(p95 - p50) - (p50 - p5)| / (p95 - p5)
  Q2a theta_c: value of theta at which the correct response changes
  Q2b p_above: P(theta > theta_c)
              -> d_a = (mu0 - theta_c) / sigma0, d_b = Phi^-1(Q2b), d = mean(d_a, d_b)
                 residual = |Q2b - Phi(d_a)|
  Q3a W_rr:   two runs on the same system differ by less than W_rr in 90% of cases
              -> r_a = (W_rr / (1.645 sqrt 2))^2
  Q3b W1:     total width of the 90% interval for theta after the result
              -> sigma1 = W1 / 3.29, r_b = sigma0^2 sigma1^2 / (sigma0^2 - sigma1^2)
                 (invalid when sigma1 >= sigma0: a measurement cannot widen belief)
  Q3c c_move: probability that the result moves the estimate by more than half the
              prior 90% half-width, U/2 with U = 1.645 sigma0
              -> sigtilde = (U/2) / Phi^-1(1 - c/2), r_c = sigma0^2 (sigma0^2 / sigtilde^2 - 1)
                 (the preposterior sd cannot exceed the prior sd, which bounds c below
                 C_MOVE_MAX = 2 (1 - Phi(1.645/2)) = 0.4108; the route is dropped with a
                 warning when c > C_MOVE_DROP = 0.40, because within 0.01 of the bound a
                 two-decimal c no longer resolves x: x_c = 0.22 at c = 0.40, 0.06 at 0.41)
              x = exp(median of log(sqrt(r_i) / sigma0) over the valid routes) (the mean
                 when two remain), so one coarse route cannot move x on its own
              residual = std of the log x's
  Q4  loss:   L1m, L2m: cost of under-responding when theta is 1 and 2 sigma0 above the
              estimate; L1p, L2p: cost of over-responding by 1 and 2 sigma0 (USD)
              -> k_side = log2(L2 / L1), k = mean clipped to [0.5, 4], residual = |k_m - k_p|
                 L = min over m of [L1m M_k(m) + L1p M_k(-m)], M_k(m) = E[(z - m)^+^k]
                 (gaussian.min_expected_loss; 0.5 (L1m + L1p) E|z|^k when L1m = L1p)
  Q5  kappa_sigma0: value of responding when theta is one sigma0 above theta_c (USD)
  Q6  B, K:   as in the binary protocol (USD, single decision)
  Q7  sigma_b: plausible systematic error that repeating the measurement would not
              reveal (u, 0 allowed) -> sigma_b / sigma0
  Q8  C:      p5 / p50 / p95 as in the binary protocol (lognormal, voi_rank.fit)

L is the chapter's L = c_k sigma0^k (eq. lossfamily): the MINIMAL expected
loss of acting on the prior alone, i.e. under the optimal action, which
asymmetric costs shift above the prior mean by m* sigma0 (L1m = c_- sigma0^k
and L1p = c_+ sigma0^k, so sigma0 never enters). Acting at the mean instead
would cost 0.5 (L1m + L1p) E|z|^k, more by a factor that depends on the
asymmetry and k (1.78 at anchor A1), so that is not L. The same shift
applies after the measurement, hence EVSI = L (1 - (1 - R^2)^(k/2)) exactly
(chapter, "Other loss shapes and asymmetry"). The shift is written into the
g_L reasoning for the spot-read.

Warnings (fit_warning on the stored rows): asymmetry > 0.25, d mismatch >
0.15 in probability, x route spread > 0.5 in log units (or a dropped route),
k mismatch > 1.0. The per-elicitation consistency score is derived at
analysis time as the largest residual relative to its threshold
(consistency_score).
"""

from __future__ import annotations

import json

import numpy as np
from scipy import stats

from voi_rank import fit as fitmod
from voi_rank import gaussian
from voi_rank.fit import GAUSS_PARAM_NAMES, FitResult, fit_point

QUESTIONS = ("theta", "theta_c", "p_above", "W_rr", "W1", "c_move", "loss",
             "kappa_sigma0", "B", "K", "sigma_b", "C")
TRIPLE_QUESTIONS = ("theta", "C")
VALUE_QUESTIONS = ("theta_c", "p_above", "W_rr", "W1", "c_move", "kappa_sigma0", "B", "K", "sigma_b")
LOSS_KEYS = ("L1m", "L2m", "L1p", "L2p")
PROB_QUESTIONS = ("p_above", "c_move")
PROB_RANGE = (0.001, 0.999)
K_RANGE = (0.5, 4.0)
# Q3c: c at which the implied preposterior sd equals the prior sd (route c undefined
# beyond it), and the drop point below it where a two-decimal c stops resolving x
C_MOVE_MAX = float(2.0 * (1.0 - stats.norm.cdf(gaussian.Z95 / 2.0)))   # 0.4108
C_MOVE_DROP = 0.40
# warning thresholds per stored quantity (spec v2.1)
THRESHOLDS = {"g_mu0": 0.25, "g_sigma0": 0.25, "g_d": 0.15, "g_x": 0.5, "g_k": 1.0, "g_L": 1.0}
DIMENSIONLESS = "dimensionless"


def _num(d: dict, key: str):
    try:
        v = float(d[key])
    except (KeyError, TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def validate_gauss_payload(obj) -> tuple[dict | None, str | None]:
    """Schema + constraint checks of a Gaussian payload:
        {"state": {"variable", "unit", "bad_is_high": true, "reasoning"},
         "answers": {theta{p5,p50,p95}, theta_c{value}, p_above{value}, W_rr{value},
                     W1{value}, c_move{value}, loss{L1m,L2m,L1p,L2p}, kappa_sigma0{value},
                     B{value}, K{value}, sigma_b{value}, C{p5,p50,p95}}, each with "reasoning"}
    Returns (clean, None) or (None, error) with the same 'schema:' /
    'constraint:' prefixes as validate.validate_payload. Extra keys are ignored."""
    if not isinstance(obj, dict) or not isinstance(obj.get("state"), dict):
        return None, "schema: missing 'state' object"
    if not isinstance(obj.get("answers"), dict):
        return None, "schema: missing 'answers' object"
    st = obj["state"]
    for key in ("variable", "unit"):
        if not isinstance(st.get(key), str) or not st[key].strip():
            return None, f"schema: state.{key} must be a non-empty string"
    if st.get("bad_is_high") is not True:
        return None, "schema: state.bad_is_high must be true (negate the variable so that bad is high)"
    ans = obj["answers"]
    missing = [q for q in QUESTIONS if q not in ans]
    if missing:
        return None, f"schema: missing answers {missing}"
    clean: dict = {"state": {"variable": st["variable"].strip(), "unit": st["unit"].strip(),
                             "reasoning": str(st.get("reasoning", ""))}}
    for q in QUESTIONS:
        d = ans[q]
        if not isinstance(d, dict):
            return None, f"schema: {q} is not an object"
        entry: dict = {"reasoning": str(d.get("reasoning", ""))}
        if q in TRIPLE_QUESTIONS:
            vals = [_num(d, k) for k in ("p5", "p50", "p95")]
            if any(v is None for v in vals):
                return None, f"schema: {q}: missing or non-numeric percentiles"
            entry.update(zip(("p5", "p50", "p95"), vals, strict=True))
        elif q == "loss":
            vals = [_num(d, k) for k in LOSS_KEYS]
            if any(v is None for v in vals):
                return None, f"schema: loss: missing or non-numeric {'/'.join(LOSS_KEYS)}"
            entry.update(zip(LOSS_KEYS, vals, strict=True))
        else:
            v = _num(d, "value")
            if v is None:
                return None, f"schema: {q}: missing or non-numeric value"
            entry["value"] = v
        clean[q] = entry
    # constraints (spec v2.1)
    th = clean["theta"]
    if not (th["p5"] < th["p50"] < th["p95"]):
        return None, "constraint: theta: percentiles not strictly increasing"
    for q in PROB_QUESTIONS:
        if not (PROB_RANGE[0] < clean[q]["value"] < PROB_RANGE[1]):
            return None, f"constraint: {q}: must lie in ({PROB_RANGE[0]}, {PROB_RANGE[1]})"
    for q in ("W_rr", "W1", "kappa_sigma0", "B", "K"):
        if clean[q]["value"] <= 0.0:
            return None, f"constraint: {q}: must be > 0"
    if clean["W1"]["value"] >= th["p95"] - th["p5"]:
        return None, ("constraint: W1: the 90% interval after the result must be narrower than"
                      " the prior 90% interval (sigma1 >= sigma0: a measurement cannot widen belief)")
    loss = clean["loss"]
    if any(loss[k] <= 0.0 for k in LOSS_KEYS):
        return None, "constraint: loss: L1m, L2m, L1p, L2p must be > 0"
    if loss["L2m"] < loss["L1m"] or loss["L2p"] < loss["L1p"]:
        return None, "constraint: loss: L2m >= L1m and L2p >= L1p (a larger error cannot cost less)"
    if clean["sigma_b"]["value"] < 0.0:
        return None, "constraint: sigma_b: must be >= 0"
    C = clean["C"]
    if not (C["p5"] < C["p50"] < C["p95"]):
        return None, "constraint: C: percentiles not strictly increasing"
    if C["p5"] <= 0.0:
        return None, "constraint: C: must be > 0"
    return clean, None


# --- derivation ---------------------------------------------------------------

def x_routes(sigma0: float, W_rr: float, W1: float, c: float) -> dict[str, float]:
    """log(sqrt(r_i) / sigma0) per route a, b, c (Q3); a route the model
    cannot accommodate is absent (b is excluded by validation; c when
    c > C_MOVE_DROP, i.e. sigtilde within a hair of sigma0)."""
    out = {}
    out["a"] = float(np.log(W_rr / (gaussian.Z95 * np.sqrt(2.0)) / sigma0))
    sigma1 = W1 / gaussian.W90
    if sigma1 < sigma0:
        r_b = sigma0**2 * sigma1**2 / (sigma0**2 - sigma1**2)
        out["b"] = float(np.log(np.sqrt(r_b) / sigma0))
    if c <= C_MOVE_DROP:
        half_u = 0.5 * gaussian.Z95 * sigma0
        sigtilde = half_u / stats.norm.ppf(1.0 - c / 2.0)
        r_c = sigma0**2 * (sigma0**2 / sigtilde**2 - 1.0)
        out["c"] = float(np.log(np.sqrt(r_c) / sigma0))
    return out


def derive(clean: dict) -> dict:
    """The stored quantities from a validated payload: {"values": {name:
    float}, "residuals": {name: float}, "warnings": {name: bool}, "notes":
    [str], "routes": {route: log x}, "shift": m* of the optimal action in
    sigma0 units}."""
    th = clean["theta"]
    mu0 = th["p50"]
    width = th["p95"] - th["p5"]
    sigma0 = width / gaussian.W90
    asym = abs((th["p95"] - th["p50"]) - (th["p50"] - th["p5"])) / width
    d_a = (mu0 - clean["theta_c"]["value"]) / sigma0
    q = clean["p_above"]["value"]
    d_b = float(stats.norm.ppf(q))
    d = 0.5 * (d_a + d_b)
    d_res = abs(q - float(stats.norm.cdf(d_a)))
    routes = x_routes(sigma0, clean["W_rr"]["value"], clean["W1"]["value"], clean["c_move"]["value"])
    logs = np.array(list(routes.values()))
    x = float(np.exp(np.median(logs)))   # the mean of two, the middle of three
    x_res = float(logs.std())
    notes = []
    if "c" not in routes:
        notes.append(f"Q3c dropped: c > {C_MOVE_DROP:g} (a Gaussian sensor allows at most"
                     f" {C_MOVE_MAX:.4f}, where the preposterior sd equals the prior sd, and within"
                     " 0.01 of that bound a two-decimal c no longer resolves x)")
    loss = clean["loss"]
    k_m = float(np.log2(loss["L2m"] / loss["L1m"]))
    k_p = float(np.log2(loss["L2p"] / loss["L1p"]))
    k_raw = 0.5 * (k_m + k_p)
    k = float(np.clip(k_raw, *K_RANGE))
    if k != k_raw:
        notes.append(f"k clipped from {k_raw:.3g} to {k:g}")
    k_res = abs(k_m - k_p)
    L, shift = gaussian.min_expected_loss(k, loss["L1m"], loss["L1p"])
    values = {
        "g_mu0": mu0, "g_sigma0": sigma0, "g_d": d, "g_x": x, "g_k": k, "g_L": L,
        "g_kappa_sigma0": clean["kappa_sigma0"]["value"], "g_B": clean["B"]["value"],
        "g_K": clean["K"]["value"], "g_sigma_b_rel": clean["sigma_b"]["value"] / sigma0,
    }
    residuals = {"g_mu0": asym, "g_sigma0": asym, "g_d": d_res, "g_x": x_res, "g_k": k_res,
                 "g_L": k_res}
    warnings = {name: residuals[name] > THRESHOLDS[name] for name in residuals}
    warnings["g_x"] = warnings["g_x"] or "c" not in routes
    return {"values": values, "residuals": residuals, "warnings": warnings, "notes": notes,
            "routes": routes, "shift": shift}


def _reasoning(clean: dict, *questions: str) -> str:
    return " | ".join(f"{q}: {clean[q]['reasoning']}" for q in questions if clean[q]["reasoning"])


def fit_gauss(clean: dict) -> tuple[dict | None, dict | None, str | None]:
    """(rows, fits, None) or (None, None, 'fit: ...'). rows[name] = {p5, p50,
    p95, unit, reasoning} for every GAUSS_PARAM_NAMES entry (a point row
    stores its value in all three percentile columns); fits[name] is the
    FitResult that carries the derived value, residual and warning, and the
    lognormal fit of C."""
    try:
        der = derive(clean)
        c_fit = fitmod.fit_lognormal(clean["C"]["p5"], clean["C"]["p50"], clean["C"]["p95"])
    except Exception as ex:
        return None, None, f"fit: {ex}"
    unit = clean["state"]["unit"]
    units = {"g_mu0": unit, "g_sigma0": unit, "g_d": DIMENSIONLESS, "g_x": DIMENSIONLESS,
             "g_k": DIMENSIONLESS, "g_L": "USD", "g_kappa_sigma0": "USD", "g_B": "USD",
             "g_K": "USD", "g_sigma_b_rel": DIMENSIONLESS}
    state = f"state: {clean['state']['variable']} [{unit}]"
    notes = ("; ".join(der["notes"]) + " | ") if der["notes"] else ""
    reasoning = {
        "g_mu0": f"{state} | {_reasoning(clean, 'theta')}",
        "g_sigma0": f"{state} | {_reasoning(clean, 'theta')}",
        "g_d": _reasoning(clean, "theta_c", "p_above"),
        "g_x": notes + _reasoning(clean, "W_rr", "W1", "c_move"),
        "g_k": notes + _reasoning(clean, "loss"),
        "g_L": f"optimal action shift {der['shift']:+.2f} sigma0 | " + _reasoning(clean, "loss"),
        "g_kappa_sigma0": _reasoning(clean, "kappa_sigma0"),
        "g_B": _reasoning(clean, "B"),
        "g_K": _reasoning(clean, "K"),
        "g_sigma_b_rel": _reasoning(clean, "sigma_b"),
    }
    rows: dict[str, dict] = {}
    fits: dict[str, FitResult] = {}
    for name in GAUSS_PARAM_NAMES:
        if name == "C":
            rows[name] = {"p5": clean["C"]["p5"], "p50": clean["C"]["p50"], "p95": clean["C"]["p95"],
                          "unit": "USD", "reasoning": clean["C"]["reasoning"]}
            fits[name] = c_fit
            continue
        v = der["values"][name]
        rows[name] = {"p5": v, "p50": v, "p95": v, "unit": units[name], "reasoning": reasoning[name]}
        fits[name] = fit_point(v, der["residuals"].get(name, 0.0), der["warnings"].get(name, False))
    return rows, fits, None


def consistency_score(residuals: dict[str, float]) -> float | None:
    """Largest over-determination residual relative to its warning threshold
    (1.0 = at the threshold), over the stored quantities that carry one;
    None when none does."""
    ratios = [residuals[n] / THRESHOLDS[n] for n in ("g_sigma0", "g_d", "g_x", "g_k")
              if residuals.get(n) is not None]
    return float(max(ratios)) if ratios else None


def parse_gauss(text: str) -> tuple[dict | None, dict | None, str | None]:
    """Convenience: JSON text -> (rows, fits, error)."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as ex:
        return None, None, f"json: result parse failed: {ex}"
    clean, err = validate_gauss_payload(obj)
    if err:
        return None, None, err
    return fit_gauss(clean)
