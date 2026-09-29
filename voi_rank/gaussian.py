"""Closed forms of the Gaussian-state family (chapter sections "The
linear-Gaussian model: sensors, estimation and control", "Action models: one
state, one sensor, three decisions"), vectorised over NumPy arrays.

State and sensor (chapter eq. posterior / prepost):
    theta ~ N(mu0, sigma0^2), bad is high; y = theta + v, v ~ N(0, r)
    x = sqrt(r) / sigma0                     relative sensor error
    R^2 = 1 / (1 + x^2)                      fraction of prior variance removed
    sigma1^2 = sigma0^2 (1 - R^2)            posterior variance
    sigtilde^2 = sigma0^2 R^2                preposterior variance of mu1
A common-mode bias b >= 0, half-normal with scale sigma_b, acts on one
measurement as extra sensor variance r -> r + sigma_b^2 (1 - 2/pi) (chapter,
"What monotonicity buys", item 3); every action model below uses that
effective R^2.

Action models, all on the same (d, R^2) with d = (mu0 - theta_c) / sigma0:
    quad     graded response, loss c |a - theta|^k: EVPI = L, EVSI = L (1 - (1 - R^2)^(k/2))
             (eq. lossfamily; k = 2 gives eq. lqg, EVSI = L R^2); L = c_k sigma0^k is the
             minimal expected loss under the prior (min_expected_loss)
    kg       binary action, payoff linear in the state: EVSI = kappa sigtilde Psi(d / R),
             EVPI = kappa sigma0 Psi(d), Psi(z) = phi(z) - |z| Phi(-|z|) (eq. kg)
    step     binary action, step payoff, the agent sees y itself: eq. stepcont, evaluated
             exactly through the decision-optimal cutoff ybar* (chapter, "Pass/fail report
             at a cutoff chosen for this decision": a threshold policy is optimal, so
             reporting 1[y > ybar*] loses nothing and EVSI is the binary closed form at
             (p, s(ybar*), t(ybar*)) with orthant probabilities of correlation R)
    stepfix  binary action, step payoff, pass/fail at the fixed mark ybar = theta_c:
             s, t are the orthant probabilities at that mark and EVSI is the binary
             closed form voi_rank.model.voi(p, s, t, B, K) (chapter, "Pass/fail report at
             a fixed mark"); this is the model that maps onto the binary protocol
voi_step_fence is the step value with the prior on the fence, d = Phi^-1(pi*): the maximum
of EVSI_step over d, the chapter's Gaussian counterpart of the binary fence value.

The design (spec v2.1) evaluated `step` by 64-node Gauss-Hermite quadrature
over mu1. That quadrature is kept as voi_step_gh for the cross-check tests
but is NOT the stored metric: the integrand (Phi((mu1 - theta_c)/sigma1) -
pi*)^+ tends to a step function as R^2 -> 1 and 64 nodes miss the integral
by up to 1.8e-3 Lambda at R^2 = 0.9, 1.6e-2 Lambda (67% of the value) at
0.99 and 4.3e-2 Lambda (almost all of the value) at 0.999 (max over d in
[-4, 4] at 0.005 steps; the error is spiky in d because the fixed nodes
straddle the moving step), while the cutoff route is exact to machine
precision (tests/test_gaussian.py measures both).
"""

from __future__ import annotations

import numpy as np
from scipy import integrate, optimize, special, stats

from voi_rank import model

Z95 = float(stats.norm.ppf(0.95))     # 1.6449: half-width of a 90% interval in sd units
W90 = 2.0 * Z95                        # 3.2897: full width of a 90% interval (spec: 3.29)
BIAS_VARIANCE_FACTOR = 1.0 - 2.0 / np.pi   # variance of a half-normal with scale 1
GH_NODES = 64                          # the design's quadrature order (voi_step_gh)
LOSS_SHIFT_BOUND = 12.0                # |m*| bound (sd units) for min_expected_loss: the k = 1
                                       # shift is Phi^-1(c_-/(c_- + c_+)), 7.0 at a 1e12 cost ratio
TAIL_D = 5.0                           # |d| beyond which orthant_st integrates the rare side
                                       # (Phi(-5) = 2.9e-7; Owen's T route is 1e-10 there, garbage by 8)
ACTION_MODELS = ("quad", "kg", "step", "stepfix")
# metrics an MC run stores for a Gaussian protocol, in this order
METRIC_NAMES = [f"{kind}_{m}" for m in ACTION_MODELS for kind in ("EVSI", "EVPI", "eff")] + [
    "R2", "d", "x", "k", "p_derived", "s_derived", "t_derived", "C"]
# the drawn quantities scenario_metrics reads: the ones a sensitivity against
# eff_step is defined for (g_mu0 and g_sigma0 are stored, drawn and reported as
# noise, but enter no metric: d and x are already in prior-sd units)
METRIC_INPUTS = ("g_d", "g_x", "g_k", "g_L", "g_kappa_sigma0", "g_B", "g_K", "g_sigma_b_rel", "C")
PRIMARY_METRIC = "eff_step"
EVSI_METRIC = "EVSI_step"

_norm = stats.norm


def _arrays(*values):
    return tuple(np.asarray(v, dtype=float) for v in values)


# --- state and sensor ---------------------------------------------------------

def r2_effective(x, sigma_b_rel=0.0):
    """R^2 = 1 / (1 + x_eff^2) with x_eff^2 = x^2 + (sigma_b / sigma0)^2 (1 - 2/pi):
    eq. posterior with the bias correction r -> r + sigma_b^2 (1 - 2/pi)."""
    x, sb = _arrays(x, sigma_b_rel)
    return 1.0 / (1.0 + x**2 + sb**2 * BIAS_VARIANCE_FACTOR)


def posterior_sds(sigma0, R2):
    """(sigma1, sigtilde): posterior sd sigma0 sqrt(1 - R^2) and preposterior sd
    sigma0 sqrt(R^2) (eq. posterior, eq. prepost)."""
    sigma0, R2 = _arrays(sigma0, R2)
    return sigma0 * np.sqrt(1.0 - R2), sigma0 * np.sqrt(R2)


def psi(z):
    """Unit normal loss integral Psi(z) = phi(z) - |z| Phi(-|z|) (eq. kg), even,
    Psi(0) = 1/sqrt(2 pi), Gaussian-tail decay."""
    z = np.abs(np.asarray(z, dtype=float))
    finite = np.isfinite(z)
    zf = np.where(finite, z, 0.0)
    return np.where(finite, _norm.pdf(zf) - zf * _norm.cdf(-zf), 0.0)


def abs_moment(k):
    """E|z|^k for z ~ N(0, 1): 2^(k/2) Gamma((k + 1) / 2) / sqrt(pi) (spec, Q4);
    equals 1 at k = 2 and sqrt(2 / pi) at k = 1."""
    k = np.asarray(k, dtype=float)
    return 2.0 ** (k / 2.0) * special.gamma((k + 1.0) / 2.0) / np.sqrt(np.pi)


def partial_moment(k, delta):
    """M_k(delta) = E[(z - delta)^+^k] for z ~ N(0, 1):
    Gamma(k + 1) exp(-delta^2 / 4) D_{-(k+1)}(delta) / sqrt(2 pi) with D the
    parabolic cylinder function (Gradshteyn and Ryzhik 3.462.1, scipy.special.pbdv).
    abs_moment(k) / 2 at delta = 0, ~ |delta|^k as delta -> -inf, Gaussian-tail
    decay as delta -> +inf; 1e-9 against quadrature for k in [0.5, 4] (tests)."""
    k, delta = np.broadcast_arrays(*_arrays(k, delta))
    return (special.gamma(k + 1.0) * np.exp(-delta**2 / 4.0) * special.pbdv(-(k + 1.0), delta)[0]
            / np.sqrt(2.0 * np.pi))


def min_expected_loss(k: float, L1m: float, L1p: float) -> tuple[float, float]:
    """(L, m*): the minimal expected loss under the prior, L = c_k sigma0^k
    (eq. lossfamily; the chapter's L and the quad EVPI), and the shift m* of
    the optimal action above the prior mean in prior-sd units. L1m = c_-
    sigma0^k and L1p = c_+ sigma0^k are the elicited costs of under- and
    over-responding by one sigma0 (Q4), so acting at a = mu0 + m sigma0 costs
        E loss(m) = L1m E[(z - m)^+^k] + L1p E[(m - z)^+^k] = L1m M_k(m) + L1p M_k(-m),
    minimised over m by bounded Brent (unimodal; convex for k >= 1). Symmetric
    costs give m* = 0 and L = 0.5 (L1m + L1p) E|z|^k, the loss of acting at
    the mean; asymmetry shifts the action by a fixed multiple of sigma and
    lowers L, and the same shift applies after the measurement, so
    EVSI = L (1 - (1 - R^2)^(k/2)) is exact (chapter, "Other loss shapes")."""
    def expected_loss(m):
        return float(L1m * partial_moment(k, m) + L1p * partial_moment(k, -m))

    res = optimize.minimize_scalar(expected_loss, bounds=(-LOSS_SHIFT_BOUND, LOSS_SHIFT_BOUND),
                                   method="bounded", options={"xatol": 1e-9})
    return float(res.fun), float(res.x)


# --- bivariate normal ---------------------------------------------------------

def bvn_cdf(h, k, rho):
    """P(X <= h, Y <= k) for a standard bivariate normal with correlation rho,
    by Owen's T function (Owen 1956, eq. 3.1):
        Phi2(h, k; rho) = [Phi(h) + Phi(k)] / 2 - T(h, a_h) - T(k, a_k) - beta,
        a_h = (k - rho h) / (h sqrt(1 - rho^2)), a_k = (h - rho k) / (k sqrt(1 - rho^2)),
        beta = 1/2 when h k < 0 or (h k = 0 and h + k < 0), else 0.
    Limits handled explicitly: h = 0 or k = 0 (a = +-inf, T(h, +-inf) =
    +-Phi(-|h|)/2 which scipy's owens_t returns), h = k = 0 (1/4 +
    arcsin(rho) / 2 pi), infinite arguments, rho = 0 and |rho| = 1. Exact to
    ~1e-16 against scipy.stats.multivariate_normal.cdf (tests)."""
    h, k, rho = np.broadcast_arrays(*_arrays(h, k, rho))
    out = np.empty(h.shape)
    neg_inf = (h == -np.inf) | (k == -np.inf)
    h_inf, k_inf = h == np.inf, k == np.inf
    one = np.abs(rho) >= 1.0 - 1e-12
    zero = np.abs(rho) < 1e-12
    gen = ~(one | zero | neg_inf | h_inf | k_inf)
    out[neg_inf] = 0.0
    out[h_inf & ~neg_inf] = _norm.cdf(k[h_inf & ~neg_inf])
    out[k_inf & ~neg_inf & ~h_inf] = _norm.cdf(h[k_inf & ~neg_inf & ~h_inf])
    rest = ~(neg_inf | h_inf | k_inf)
    pos_one = one & rest & (rho > 0)
    neg_one = one & rest & (rho < 0)
    out[pos_one] = _norm.cdf(np.minimum(h[pos_one], k[pos_one]))
    out[neg_one] = np.maximum(0.0, _norm.cdf(h[neg_one]) + _norm.cdf(k[neg_one]) - 1.0)
    z = zero & rest
    out[z] = _norm.cdf(h[z]) * _norm.cdf(k[z])
    hg, kg, rg = h[gen], k[gen], rho[gen]
    den = np.sqrt(1.0 - rg**2)
    with np.errstate(divide="ignore", invalid="ignore"):
        ah = np.where(hg != 0.0, (kg - rg * hg) / (hg * den), np.sign(kg) * np.inf)
        ak = np.where(kg != 0.0, (hg - rg * kg) / (kg * den), np.sign(hg) * np.inf)
    beta = np.where((hg * kg < 0.0) | ((hg * kg == 0.0) & (hg + kg < 0.0)), 0.5, 0.0)
    val = (0.5 * (_norm.cdf(hg) + _norm.cdf(kg)) - special.owens_t(hg, ah)
           - special.owens_t(kg, ak) - beta)
    both0 = (hg == 0.0) & (kg == 0.0)
    val[both0] = 0.25 + np.arcsin(rg[both0]) / (2.0 * np.pi)
    out[gen] = np.clip(val, 0.0, 1.0)
    return out


def _tail_s(a: float, R2: float, c: float) -> float:
    """s = P(w > c | u > a) for a standard bivariate normal (u, w) of
    correlation R, by the conditional 1-D integral over the excess v = u - a:
        s = int_0^inf [phi(a + v) / Phi(-a)] Phi((R (a + v) - c) / sqrt(1 - R^2)) dv,
    the density ratio taken in logs (scipy's log_ndtr is exact in the far
    tail), so it is stable however rare the conditioning event u > a is.
    Scalar; used by orthant_st beyond TAIL_D, where Owen's T route subtracts
    terms of order Phi(-c) to leave Phi(-a) ~ 1e-20 and loses everything."""
    R, s1 = np.sqrt(R2), np.sqrt(max(1.0 - R2, 0.0))
    log_mass = float(_norm.logcdf(-a))

    def integrand(v):
        z = R * (a + v) - c
        cond = _norm.cdf(z / s1) if s1 > 0.0 else float(z > 0.0)
        return np.exp(_norm.logpdf(a + v) - log_mass) * cond

    val = integrate.quad(integrand, 0.0, np.inf, epsabs=0.0, epsrel=1e-12, limit=200)[0]
    return float(np.clip(val, 0.0, 1.0))


def orthant_st(d, R2, cutoff):
    """Sensitivity and specificity of the pass/fail report 1[w > cutoff] on the
    standardised reading w = (y - mu0) R / sigma0 (so Var(w) = 1 and
    corr(u, w) = R for u = (theta - mu0) / sigma0), against the binary state
    theta > theta_c, i.e. u > -d (chapter, sec. step):
        s = P(w > c | u > -d) = Phi2(d, -c; R) / Phi(d)
        t = P(w <= c | u <= -d) = Phi2(-d, c; R) / Phi(-d)
    (P(u > -d, w > c) = P(-u < d, -w < -c) and (-u, -w) has the same
    correlation, so t(d, c) = s(-d, -c).) Where the prior puts no mass on
    one side the conditional is undefined and 1 is returned (that side's
    EVSI term vanishes anyway). Beyond |d| = TAIL_D the rare side (s for
    d < -TAIL_D, t for d > TAIL_D) is the ratio of two vanishing numbers,
    which Owen's T route cannot resolve (s = 0.045 instead of 0.522 at
    R^2 = 0.2, d = -9); it is evaluated by the stable 1-D integral _tail_s
    instead, per distinct (d, R^2, c) triple. Both routes agree to 1e-10 at
    the switch."""
    d, R2, c = np.broadcast_arrays(*_arrays(d, R2, cutoff))
    shape = d.shape
    d, R2, c = d.ravel(), R2.ravel(), c.ravel()
    R = np.sqrt(R2)
    p = _norm.cdf(d)
    q = _norm.cdf(-d)
    num_s = bvn_cdf(d, -c, R)
    num_t = bvn_cdf(-d, c, R)
    s = np.where(p > 0.0, num_s / np.where(p > 0.0, p, 1.0), 1.0)
    t = np.where(q > 0.0, num_t / np.where(q > 0.0, q, 1.0), 1.0)
    s, t = np.clip(s, 0.0, 1.0), np.clip(t, 0.0, 1.0)
    # the rare side: s conditions on u > -d (mass Phi(d)), t on u < -d (mass Phi(-d)),
    # and t(d, c) = s(-d, -c)
    for out, sign in ((s, 1.0), (t, -1.0)):
        rare = (sign * d < -TAIL_D) & np.isfinite(d) & np.isfinite(c)
        if not rare.any():
            continue
        triples = np.stack([-sign * d[rare], R2[rare], sign * c[rare]], axis=-1)
        uniq, inv = np.unique(triples, axis=0, return_inverse=True)
        vals = np.array([_tail_s(a, r2, cc) for a, r2, cc in uniq])
        out[rare] = vals[inv.ravel()]
    return s.reshape(shape)[()], t.reshape(shape)[()]


def derived_st(d, R2):
    """(s, t) of a pass/fail report at the fixed mark ybar = theta_c:
    y > theta_c is w > -d R (chapter, "Pass/fail report at a fixed mark")."""
    d, R2 = _arrays(d, R2)
    return orthant_st(d, R2, -d * np.sqrt(R2))


def optimal_cutoff(d, R2, pistar):
    """The decision-optimal cutoff on w: the posterior Phi((mu1(y) - theta_c) /
    sigma1) equals pi* at ybar* = mu0 + (theta_c + sigma1 Phi^-1(pi*) - mu0) / R^2
    (chapter), i.e. w* = (-d + sqrt(1 - R^2) Phi^-1(pi*)) / R. +-inf at R = 0."""
    d, R2, pistar = np.broadcast_arrays(*_arrays(d, R2, pistar))
    R = np.sqrt(R2)
    num = -d + np.sqrt(1.0 - R2) * _norm.ppf(pistar)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(R > 0.0, num / np.where(R > 0.0, R, 1.0), np.sign(num) * np.inf)


# --- action models --------------------------------------------------------------

def voi_quad(L, R2, k=2.0):
    """Graded response, loss c |a - theta|^k: (EVSI, EVPI) = (L (1 - (1 - R^2)^(k/2)), L)
    (eq. lossfamily; k = 2 is eq. lqg). L = c_k sigma0^k is the minimal expected
    loss of acting on the prior alone, under the optimal (shifted, for
    asymmetric costs) action: min_expected_loss."""
    L, R2, k = _arrays(L, R2, k)
    evsi = L * (1.0 - (1.0 - R2) ** (k / 2.0))
    return np.minimum(np.maximum(evsi, 0.0), L), L * np.ones_like(evsi)


def voi_kg(kappa_sigma0, d, R2):
    """Binary action, payoff kappa (theta - theta_c): (EVSI, EVPI) =
    (kappa sigtilde Psi(d / R), kappa sigma0 Psi(d)) with sigtilde = sigma0 R
    (eq. kg and the EVPI below it). Zero EVSI at R = 0."""
    ks, d, R2 = np.broadcast_arrays(*_arrays(kappa_sigma0, d, R2))
    R = np.sqrt(R2)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(R > 0.0, d / np.where(R > 0.0, R, 1.0), np.inf)
    evsi = np.where(R > 0.0, ks * R * psi(z), 0.0)
    evpi = ks * psi(d)
    return np.minimum(np.maximum(evsi, 0.0), evpi), evpi


def voi_stepfix(d, R2, B, K):
    """Binary action, step payoff, pass/fail at the fixed mark theta_c:
    (EVSI, EVPI, s, t) with p = Phi(d), (s, t) = derived_st and the binary
    closed form voi_rank.model.voi (eq. evsi_binary, eq. evpi_binary)."""
    d, R2, B, K = np.broadcast_arrays(*_arrays(d, R2, B, K))
    s, t = derived_st(d, R2)
    evsi, evpi = model.voi(_norm.cdf(d), s, t, B, K)
    return evsi, evpi, s, t


def voi_step(d, R2, B, K):
    """Binary action, step payoff, the agent sees the continuous reading y
    (eq. stepcont): EVSI = Lambda (E_mu1[(Phi((mu1 - theta_c)/sigma1) - pi*)^+]
    - (Phi(d) - pi*)^+), evaluated exactly as the binary closed form at the
    decision-optimal cutoff (chapter: a pass/fail report at ybar* gives the
    same action and the same EVSI). EVPI = min(pB, (1 - p)K). Returns
    (EVSI, EVPI). R = 0: no information, EVSI = 0; R = 1: EVSI = EVPI."""
    d, R2, B, K = np.broadcast_arrays(*_arrays(d, R2, B, K))
    pistar = K / (B + K)
    s, t = orthant_st(d, R2, optimal_cutoff(d, R2, pistar))
    return model.voi(_norm.cdf(d), s, t, B, K)


def voi_step_fence(R2, B, K):
    """The step model with its prior on the fence: voi_step at d* =
    Phi^-1(pi*), pi* = K / (B + K), so that p = Phi(d*) = pi* (chapter,
    "The three models side by side": the step models peak "where [their]
    own decision is on the fence", d = Phi^-1(pi*) in fig:action). For the
    continuous signal this is the exact maximum of EVSI_step over d, i.e.
    over the state threshold theta_c at fixed prior, sensor and stakes: with
    pi_y the posterior probability, EVSI = Lambda (E[(pi_y - pi*)^+] -
    (Phi(d) - pi*)^+); below the fence the first term rises with d; above
    it the slope is Lambda (E[1{pi_y > pi*} dpi_y/dd] - phi(d)) < 0 because
    E[dpi_y/dd] = phi(d) (the martingale E[pi_y] = Phi(d)). It depends on R^2
    and the stakes split, not on d: the Gaussian counterpart of eq. fence,
    which removes pi* at the elicited p where this removes d at the
    elicited pi*. Returns (EVSI, EVPI) at d*."""
    R2, B, K = np.broadcast_arrays(*_arrays(R2, B, K))
    return voi_step(_norm.ppf(K / (B + K)), R2, B, K)


def voi_step_gh(d, R2, B, K, n_nodes: int = GH_NODES):
    """The design's evaluation of eq. stepcont: Gauss-Hermite quadrature with
    n_nodes over mu1 ~ N(mu0, sigtilde^2), in standardised form z ~ N(0, 1),
    (mu1 - theta_c) / sigma1 = (d + R z) / sqrt(1 - R^2). Kept as a
    cross-check only (see the module docstring): the kinked, near-step
    integrand is resolved poorly as R^2 -> 1."""
    d, R2, B, K = np.broadcast_arrays(*_arrays(d, R2, B, K))
    nodes, weights = np.polynomial.hermite_e.hermegauss(n_nodes)
    weights = weights / np.sqrt(2.0 * np.pi)
    pistar = K / (B + K)
    lam = B + K
    R = np.sqrt(R2)
    s1 = np.sqrt(1.0 - R2)
    p = _norm.cdf(d)
    with np.errstate(divide="ignore", invalid="ignore"):
        arg = (d[..., None] + R[..., None] * nodes) / np.where(s1 > 0.0, s1, 1.0)[..., None]
        arg = np.where(s1[..., None] > 0.0, arg, np.sign(d[..., None] + R[..., None] * nodes) * np.inf)
    expected = np.sum(weights * np.maximum(_norm.cdf(arg) - pistar[..., None], 0.0), axis=-1)
    evsi = lam * (expected - np.maximum(p - pistar, 0.0))
    evpi = np.minimum(p * B, (1.0 - p) * K)
    return np.minimum(np.maximum(evsi, 0.0), evpi), evpi


# --- everything an MC draw needs -----------------------------------------------

def scenario_metrics(draws: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Per-draw metrics of a Gaussian scenario from its drawn quantities
    (the METRIC_INPUTS keys; g_mu0 and g_sigma0 are not read):
    EVSI_<m>, EVPI_<m>, eff_<m> = EVSI_<m> / C for m in ACTION_MODELS, plus
    R2, d, x, k, p_derived = Phi(d), s_derived, t_derived (the fixed-mark
    orthant probabilities) and C. Returned in METRIC_NAMES order."""
    d, x, k, L = draws["g_d"], draws["g_x"], draws["g_k"], draws["g_L"]
    B, K, C = draws["g_B"], draws["g_K"], draws["C"]
    R2 = r2_effective(x, draws["g_sigma_b_rel"])
    out: dict[str, np.ndarray] = {}
    evsi_q, evpi_q = voi_quad(L, R2, k)
    evsi_kg, evpi_kg = voi_kg(draws["g_kappa_sigma0"], d, R2)
    evsi_s, evpi_s = voi_step(d, R2, B, K)
    evsi_f, evpi_f, s_der, t_der = voi_stepfix(d, R2, B, K)
    for name, evsi, evpi in (("quad", evsi_q, evpi_q), ("kg", evsi_kg, evpi_kg),
                             ("step", evsi_s, evpi_s), ("stepfix", evsi_f, evpi_f)):
        out[f"EVSI_{name}"] = evsi
        out[f"EVPI_{name}"] = evpi
        out[f"eff_{name}"] = evsi / C
    out.update({"R2": R2, "d": d, "x": x, "k": k, "p_derived": _norm.cdf(d),
                "s_derived": s_der, "t_derived": t_der, "C": C})
    return {name: out[name] for name in METRIC_NAMES}
