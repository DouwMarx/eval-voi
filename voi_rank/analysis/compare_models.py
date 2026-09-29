"""Binary model vs Gaussian-state family on the same scenarios (spec v2.1 §4),
reading only from a study's voi.db. Over the scenarios ranked by both the
latest run of the binary protocol and the latest run of the Gaussian
protocol, writes to <study>/report/generated/ (generated/TAG/ with --tag TAG,
every macro then \\voiTAG...; study.Study.tagged):

- compare_models.tex: Spearman and Kendall rank correlation of median
  efficiency, binary vs each action model (quad, kg, step, stepfix) and among
  the action models, with top-10 overlaps; and the gate-agreement confusion
  table between "binary median EVSI = 0" and "stepfix median EVSI = 0".
- fig_compare_models.pdf: binary efficiency vs stepfix efficiency, log-log,
  iso line, coloured by group (zero medians floored, open markers).
- fig_derived_pst.pdf: derived p = Phi(d), s, t (the Gaussian run's medians
  of the fixed-mark orthant probabilities) against the binary protocol's
  pooled elicited p50 of p, s, t, with Spearman and median absolute difference.
- consistency_gauss.tex: distribution of the over-determination residuals per
  quantity (theta asymmetry, d mismatch, x route spread, k mismatch) over the
  valid elicitations of the Gaussian run's members (the stored subset of a
  --members run), the fraction flagged, and their
  Spearman with the cross-repeat spread of the corresponding quantity
  (per-scenario median residual vs db.elicited_spread of the quantity: (max -
  min) / pooled p50 of the repeat values, or max - min for d, which crosses
  zero, as everywhere else).
  The second tabular gives, per quantity, the derived-vs-elicited Spearman,
  the median absolute difference and the MEAN SIGNED DIFFERENCE (derived
  minus elicited), i.e. the bias of the Gaussian family's implied p, s, t
  against the binary protocol's elicited ones (macros \\voiGaussBiasP/S/T).
- macros_compare.tex: \\voiGaussRhoQuad, \\voiGaussRhoKg, \\voiGaussRhoStep,
  \\voiGaussRhoStepfix, \\voiGaussTopOverlapStepfix, \\voiGaussRhoP, \\voiGaussRhoS,
  \\voiGaussRhoT, \\voiGaussBiasP/S/T, \\voiGaussGateAgree, \\voiGaussN (+ the
  run ids), and the macros of the three cross-family extensions below.

Cross-family extensions (spec v2.3), each over the members the two selected
runs pooled:

- compare_members.tex: the member-matched matrix. For every member present
  in both protocols, the Spearman of median efficiency between THAT member's
  binary ranking and THAT member's Gaussian ranking, per action model, so a
  cross-family agreement is read at one elicitor (the pooled-vs-pooled row
  compares the two selected runs; pooling incoherent members is what
  LEARNINGS iteration 2 warned about). A member's ranking is read from its
  stored subset run when one exists (db.latest_run(protocol, [member]); a
  single-member protocol's all-member run counts) and otherwise re-drawn
  locally from that member's fits alone with the selected run's seed and
  draw count, as extra.member_rankings does (not the stored run; the source
  column and the caption say which). Macros
  \\voiGaussRhoMember<Model><Member> (e.g. \\voiGaussRhoMemberStepfixHaiku).
- compare_plugin.tex + fig_compare_plugin.pdf: the threshold-robust
  comparison. Binary plug-in efficiency at the pooled medians of p, s, t, B,
  K, C (extra.plugin_point, exactly the plugin.tex point) against the
  Gaussian plug-in efficiency per action model at the pooled medians of d,
  x, k, L, kappa sigma0, B, K, sigma_b/sigma0, C through
  gaussian.scenario_metrics; and three fence pairs, the binary fence value
  EVSI* = (B + K) p (1 - p) (s + t - 1) (model.voi_fence, eq. fence: the
  binary EVSI maximised over the threshold pi* at fixed stakes and fixed
  p, s, t) against a Gaussian value that also needs no pi*.
  (i) Stepfix fence: the same eq. fence at p = Phi(d) and the derived s, t
  with the same stakes B + K (the chapter's summary: "binary action with
  step payoff gives back the binary model with p = Phi(d) and derived
  s, t"), the same formula and stakes, only the family's elicitation
  differs. (ii) Step fence, the chapter's own Gaussian analog (fig:action:
  the step models peak "where [their] own decision is on the fence",
  d = Phi^-1(pi*)): gaussian.voi_step_fence, the continuous-signal step
  value at d* = Phi^-1(K / (B + K)), its exact maximum over d; it removes d
  at the elicited pi* where eq. fence removes pi* at the elicited p.
  (iii) The quad value L R^2 (chapter eq. lqg, the k = 2 form, R^2 the
  bias-corrected one): this repo's choice of two quantities that are each
  threshold-free, not a pairing the chapter makes; it compares two action
  models and two stakes elicitations (B + K against L), two "stakes x
  sensor quality" products. Each as values and as efficiencies (each over
  its own protocol's median C), with Spearman, Kendall and top-k overlap.
  The figure plots binary plug-in eff vs Gaussian stepfix plug-in eff and
  EVSI* against each of the three, log-log (zeros floored, open markers).
  Macros \\voiGaussPluginRho<Model>, \\voiFenceStepfixRho /
  \\voiFenceStepRho / \\voiFenceQuadRho (values), \\voiFenceStepfixEffRho /
  \\voiFenceStepEffRho / \\voiFenceQuadEffRho (efficiencies), plus Kendall
  and top-overlap variants.
- compare_noise.tex: the joint noise table. Per member present in both
  protocols, at matched k (the first MATCHED_K valid repeats of each
  scenario, as protocol_noise_matched.tex), the median cross-repeat spread
  of the binary quantities p, s, t, B, K, C next to the Gaussian ones d
  (max - min in prior-sd units), x, k, L, kappa sigma0, B, K, C ((max -
  min) / pooled p50, db.elicited_spread), so a reader sees whether the
  Gaussian questions are more reproducible at the same elicitor; final
  rows give the ratio of the median USD spreads, Gaussian L over binary B
  (macros \\voiGaussNoiseRatio<Member>), K over K and C over C.

Usage: python -m voi_rank.analysis.compare_models --study PATH [--binary p001] [--gaussian g001]
       [--members claude_cli:sonnet,claude_cli:opus] [--tag NAME]
(--members selects, for BOTH protocols, the latest run that pooled exactly
that member subset, so the two framings are compared on the same elicitors;
the derived-vs-elicited panel pools the binary protocol's medians over the
same subset, and the member matrix and noise table cover that subset)
"""

from __future__ import annotations

import argparse
import re
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from voi_rank import db, gaussian, model  # noqa: E402
from voi_rank.analysis import extra, figures  # noqa: E402
from voi_rank.analysis.tables import esc, num, pooled_p50, tex_param  # noqa: E402
from voi_rank.fit import GAUSS_PARAM_NAMES  # noqa: E402
from voi_rank.gauss_fit import THRESHOLDS, consistency_score  # noqa: E402
from voi_rank.gaussian import ACTION_MODELS  # noqa: E402
from voi_rank.sensitivity import spearman  # noqa: E402
from voi_rank.study import MACRO_PREFIX, Study, add_study_arg, add_tag_arg, newcommands  # noqa: E402

EVSI_ZERO_USD = 1e-6
TOP_N = 10
MODEL_MACRO = {"quad": "Quad", "kg": "Kg", "step": "Step", "stepfix": "Stepfix"}
# residual-carrying quantities: (stored name, label, spread of which quantity)
RESIDUALS = (("g_sigma0", r"$\theta$ triple asymmetry", "g_sigma0"),
             ("g_d", r"$d$ mismatch (sd units)", "g_d"),
             ("g_x", r"$x$ route spread (log units)", "g_x"),
             ("g_k", r"$k$ mismatch", "g_k"))
# the joint noise table: the binary quantities next to the Gaussian ones
NOISE_BINARY = ("p", "s", "t", "B", "K", "C")
NOISE_GAUSS = ("g_d", "g_x", "g_k", "g_L", "g_kappa_sigma0", "g_B", "g_K", "C")
# the USD spread ratios of its final rows: (label, Gaussian quantity, binary quantity)
NOISE_RATIOS = (("L", "g_L", "B"), ("K", "g_K", "K"), ("C", "C", "C"))
MATCHED_K = extra.MATCHED_K
# the fence rows of the plug-in table: (plugin_comparison key, macro name stem)
FENCE_PAIRS = (("fence_stepfix", "voiFenceStepfix"), ("fence_stepfix_eff", "voiFenceStepfixEff"),
               ("fence_step", "voiFenceStep"), ("fence_step_eff", "voiFenceStepEff"),
               ("fence_quad", "voiFenceQuad"), ("fence_quad_eff", "voiFenceQuadEff"))
# (plugin_comparison key, binary plugin_point key, gauss_plugin_point key) per fence row
FENCE_SERIES = (("fence_stepfix", "EVSI_star", "fence_stepfix"),
                ("fence_stepfix_eff", "eff_star", "eff_fence_stepfix"),
                ("fence_step", "EVSI_star", "fence_step"),
                ("fence_step_eff", "eff_star", "eff_fence_step"),
                ("fence_quad", "EVSI_star", "quad_lr2"),
                ("fence_quad_eff", "eff_star", "eff_lr2"))
OUTPUTS = ("compare_models.tex", "fig_compare_models.pdf", "fig_derived_pst.pdf",
           "consistency_gauss.tex", "compare_members.tex", "compare_plugin.tex",
           "fig_compare_plugin.pdf", "compare_noise.tex", "macros_compare.tex")


DIGIT_WORDS = ("Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine")


def macro_name(text: str) -> str:
    """A LaTeX-safe CamelCase name from a member's model name: the letter
    runs capitalised and the digits spelled out, so versioned names stay
    distinct ('haiku' -> 'Haiku', 'claude-3-5-sonnet' -> 'ClaudeThreeFiveSonnet',
    'openai/gpt-4o-mini' -> 'OpenaiGptFourOMini'); write_macros refuses two
    members that still map to one name."""
    parts = []
    for part in re.findall(r"[A-Za-z]+|[0-9]+", text):
        parts.append(part.capitalize() if part.isalpha() else "".join(DIGIT_WORDS[int(c)] for c in part))
    return "".join(parts)


def member_macro_names(labels: list[str]) -> dict[str, str]:
    """{member label: macro_name of its model}, refused when two members
    collide (their macros would silently overwrite each other)."""
    names = {label: macro_name(label.split(":", 1)[-1]) for label in labels}
    seen: dict[str, str] = {}
    for label, name in names.items():
        if name in seen:
            raise ValueError(f"members {seen[name]!r} and {label!r} both map to the macro name"
                             f" {name!r}; rename one so the \\voi...{name} macros stay distinct")
        seen[name] = label
    return names


def kendall(x, y) -> float | None:
    tau = stats.kendalltau(x, y).statistic
    return None if np.isnan(tau) else float(tau)


def pct(v) -> str:
    return "--" if v is None else f"{100.0 * v:.0f}\\%"


def medians(con, run_id: int, metric: str) -> dict[int, float]:
    return {s: float(r["q50"] or 0.0) for s, r in figures.metric_rows(con, run_id, metric).items()}


def top_ids(med: dict[int, float], sids: list[int], k: int) -> set[int]:
    return set(sorted(sids, key=lambda s: (-med[s], s))[:k])


def select_runs(con, binary: str, gaussian: str, members: list[str] | None = None):
    """(binary run, gaussian run): the latest run of each protocol (of the
    `members` subset when given), refused when a protocol is not of the
    expected model kind."""
    b = figures.select_run(con, None, binary, members)
    g = figures.select_run(con, None, gaussian, members)
    for run, want, name in ((b, db.BINARY_KIND, binary), (g, db.GAUSSIAN_KIND, gaussian)):
        kind = db.run_model_kind(con, run)
        if kind != want:
            raise RuntimeError(f"protocol {name} is a {kind} protocol; --{want} needs a {want} one")
    return b, g


def rank_stats(con, b_run, g_run) -> dict:
    """Shared scenarios, per-series medians, pairwise rank agreement and the gate table."""
    series = {"binary": medians(con, b_run["id"], "efficiency")}
    for m in ACTION_MODELS:
        series[m] = medians(con, g_run["id"], f"eff_{m}")
    shared = sorted(set(series["binary"]) & set(series["stepfix"]))
    if len(shared) < 2:
        raise RuntimeError(f"only {len(shared)} scenario(s) ranked by both runs; nothing to compare")
    k = min(TOP_N, len(shared))
    pairs = [("binary", m) for m in ACTION_MODELS] + list(combinations(ACTION_MODELS, 2))
    agreement = {}
    for a, c in pairs:
        x = [series[a][s] for s in shared]
        y = [series[c][s] for s in shared]
        agreement[(a, c)] = {
            "rho": spearman(x, y) if len(shared) >= 3 else None,
            "tau": kendall(x, y) if len(shared) >= 3 else None,
            "overlap": len(top_ids(series[a], shared, k) & top_ids(series[c], shared, k)),
        }
    b_evsi = medians(con, b_run["id"], "EVSI")
    g_evsi = medians(con, g_run["id"], "EVSI_stepfix")
    b_zero = {s: b_evsi[s] < EVSI_ZERO_USD for s in shared}
    g_zero = {s: g_evsi[s] < EVSI_ZERO_USD for s in shared}
    gate = {
        "both_zero": sum(b_zero[s] and g_zero[s] for s in shared),
        "binary_only": sum(b_zero[s] and not g_zero[s] for s in shared),
        "gauss_only": sum(g_zero[s] and not b_zero[s] for s in shared),
        "both_positive": sum(not b_zero[s] and not g_zero[s] for s in shared),
    }
    gate["agree"] = (gate["both_zero"] + gate["both_positive"]) / len(shared)
    return {"shared": shared, "series": series, "agreement": agreement, "top_k": k, "gate": gate}


def derived_vs_elicited(con, b_run, g_run, shared: list[int]) -> dict:
    """{name: {"x": elicited pooled p50 (binary protocol), "y": derived median
    (Gaussian run), "rho", "mad", "bias" (mean of derived - elicited: the
    signed offset of the Gaussian family's implied probability against the
    binary elicitation), "n"}} for p, s, t."""
    out = {}
    labels = db.run_member_labels(b_run)
    for name in ("p", "s", "t"):
        der = medians(con, g_run["id"], f"{name}_derived")
        pts = [(pooled_p50(con, b_run["protocol_id"], s, name, labels), der[s]) for s in shared if s in der]
        pts = [(x, y) for x, y in pts if x is not None]
        x = np.array([p[0] for p in pts], dtype=float)
        y = np.array([p[1] for p in pts], dtype=float)
        out[name] = {"x": x, "y": y, "rho": spearman(x, y) if len(pts) >= 3 else None,
                     "mad": float(np.median(np.abs(y - x))) if len(pts) else None,
                     "bias": float(np.mean(y - x)) if len(pts) else None, "n": len(pts)}
    return out


def residual_stats(con, g_run) -> dict:
    """Per residual quantity: quantiles over the valid elicitations of the
    run's members (every member, or the subset a --members run stored, so the
    table describes the elicitors the compared runs pooled), fraction
    flagged, and the Spearman between the per-scenario median residual and
    the cross-repeat spread of the quantity over the same members; plus the
    consistency-score quantiles (max residual / threshold per elicitation)."""
    pid = g_run["protocol_id"]
    labels = db.run_member_labels(g_run)
    clause, margs = db.member_filter(labels)
    rows = con.execute(
        "SELECT e.id AS eid, e.scenario_id, p.name, p.p50, p.fit_residual, p.fit_warning"
        " FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        f" WHERE e.protocol_id=? AND e.valid=1{clause}", (pid, *margs)).fetchall()
    by_name: dict[str, dict[int, list]] = {}
    per_elic: dict[int, dict[str, float]] = {}
    for r in rows:
        by_name.setdefault(r["name"], {}).setdefault(r["scenario_id"], []).append(
            (r["p50"], r["fit_residual"], r["fit_warning"]))
        if r["fit_residual"] is not None:
            per_elic.setdefault(r["eid"], {})[r["name"]] = r["fit_residual"]
    out = {}
    for name, label, spread_of in RESIDUALS:
        per_sid = by_name.get(name, {})
        res = [v[1] for lst in per_sid.values() for v in lst if v[1] is not None]
        flagged = [bool(v[2]) for lst in per_sid.values() for v in lst]
        xs, ys = [], []
        for sid, lst in per_sid.items():
            spread = db.elicited_spread(con, pid, sid, spread_of, members=labels)
            if spread is None:
                continue
            xs.append(float(np.median([v[1] for v in lst if v[1] is not None])))
            ys.append(spread)
        q = np.quantile(res, [0.25, 0.5, 0.75]) if res else np.full(3, np.nan)
        out[name] = {"label": label, "n": len(res), "q25": float(q[0]), "q50": float(q[1]),
                     "q75": float(q[2]), "threshold": THRESHOLDS[name],
                     "flagged": (sum(flagged) / len(flagged)) if flagged else None,
                     "rho_spread": spearman(xs, ys) if len(xs) >= 3 else None, "n_spread": len(xs)}
    scores = [s for s in (consistency_score(r) for r in per_elic.values()) if s is not None]
    sq = np.quantile(scores, [0.25, 0.5, 0.75]) if scores else np.full(3, np.nan)
    out["score"] = {"n": len(scores), "q25": float(sq[0]), "q50": float(sq[1]), "q75": float(sq[2]),
                    "above_one": (sum(s > 1.0 for s in scores) / len(scores)) if scores else None}
    return out


# --- member-matched matrix (v2.3) --------------------------------------------------

def elicited_labels(con, protocol_id: int) -> set[str]:
    """Member labels holding at least one valid elicitation under a protocol."""
    return {r[0] for r in con.execute(
        "SELECT DISTINCT provider || ':' || model FROM elicitations WHERE protocol_id=? AND valid=1",
        (protocol_id,))}


def shared_members(con, b_run, g_run) -> list[dict]:
    """The members both selected runs pooled AND that elicited both protocols
    (a member listed by a protocol but never elicited has no ranking), as
    protocol member dicts in the binary run's member order, matched by label."""
    g_labels = {db.member_label(m) for m in db.run_members(con, g_run)}
    have = elicited_labels(con, b_run["protocol_id"]) & elicited_labels(con, g_run["protocol_id"])
    return [m for m in db.run_members(con, b_run) if db.member_label(m) in g_labels & have]


def stored_member_run(con, protocol_id: int, member: dict):
    """The latest stored run of the protocol that pooled exactly this member
    (a single-member protocol's all-member run counts), or None."""
    name = con.execute("SELECT name FROM protocols WHERE id=?", (protocol_id,)).fetchone()["name"]
    try:
        return db.latest_run(con, name, [db.member_label(member)])
    except RuntimeError:
        return None


def redraw_binary_member(con, run, member: dict) -> dict[int, float]:
    """{sid: median efficiency} from the member's binary fits alone, the
    mixture re-drawn with the run's seed and draw count (extra.member_rankings:
    a fresh rng, scenarios in id order; not the stored run's draws)."""
    rng = np.random.default_rng(run["seed"])
    out = {}
    for sid, fits in extra.member_fits(extra.run_fits(con, run), member).items():
        d = extra.draw_metrics(rng, fits, run["n_draws"])
        out[sid] = float(np.median(d["EVSI"] / d["C"]))
    return out


def gauss_member_fits(con, run, member: dict) -> dict[int, dict[str, list[dict]]]:
    """One member's valid Gaussian fits, on the scenarios where it carries
    every stored quantity, in scenario-id order."""
    fits_all = db.scenario_param_fits(con, run["protocol_id"], GAUSS_PARAM_NAMES,
                                      db.run_member_labels(run))
    out = {}
    for sid, fits in sorted(fits_all.items()):
        mine = {name: [f for f in rows
                       if f["provider"] == member["provider"] and f["model"] == member["model"]]
                for name, rows in fits.items()}
        if all(mine.get(name) for name in GAUSS_PARAM_NAMES):
            out[sid] = mine
    return out


def redraw_gauss_member(con, run, member: dict) -> dict[str, dict[int, float]]:
    """{action model: {sid: median eff_<m>}} from the member's Gaussian fits
    alone, re-drawn like redraw_binary_member (rng consumed in
    GAUSS_PARAM_NAMES order per scenario, as mc.iter_scenario_draws does)."""
    rng = np.random.default_rng(run["seed"])
    out: dict[str, dict[int, float]] = {m: {} for m in ACTION_MODELS}
    for sid, fits in gauss_member_fits(con, run, member).items():
        draws = {name: extra.sample_mixture(rng, fits[name], run["n_draws"]) for name in GAUSS_PARAM_NAMES}
        metrics = gaussian.scenario_metrics(draws)
        for m in ACTION_MODELS:
            out[m][sid] = float(np.median(metrics[f"eff_{m}"]))
    return out


def member_series(con, b_run, g_run, member: dict) -> dict:
    """One member's binary ranking and Gaussian rankings (per action model):
    {"binary": {sid: eff}, "gauss": {m: {sid: eff}}, "source": {"binary":
    'run <id>' | 're-drawn', "gauss": ...}}. Stored subset runs are read when
    they exist, else the member's fits are re-drawn locally."""
    out = {"source": {}}
    b_stored = stored_member_run(con, b_run["protocol_id"], member)
    if b_stored is not None:
        out["binary"] = medians(con, b_stored["id"], "efficiency")
        out["source"]["binary"] = f"run {b_stored['id']}"
    else:
        out["binary"] = redraw_binary_member(con, b_run, member)
        out["source"]["binary"] = "re-drawn"
    g_stored = stored_member_run(con, g_run["protocol_id"], member)
    if g_stored is not None:
        out["gauss"] = {m: medians(con, g_stored["id"], f"eff_{m}") for m in ACTION_MODELS}
        out["source"]["gauss"] = f"run {g_stored['id']}"
    else:
        out["gauss"] = redraw_gauss_member(con, g_run, member)
        out["source"]["gauss"] = "re-drawn"
    return out


def member_matrix(con, b_run, g_run, rs: dict) -> dict:
    """{"rows": [{"label", "rho": {m: rho | None}, "n": {m: shared scenarios},
    "source": {...}}], "pooled": {"rho": {m: rho}, "n": len(shared)}} over
    shared_members; the pooled row is rank_stats's binary-vs-model agreement
    of the two selected runs."""
    rows = []
    for m in shared_members(con, b_run, g_run):
        ser = member_series(con, b_run, g_run, m)
        rho, n = {}, {}
        for am in ACTION_MODELS:
            shared = sorted(set(ser["binary"]) & set(ser["gauss"][am]))
            n[am] = len(shared)
            rho[am] = (spearman([ser["binary"][s] for s in shared], [ser["gauss"][am][s] for s in shared])
                       if len(shared) >= 3 else None)
        rows.append({"label": db.member_label(m), "model": m["model"], "rho": rho, "n": n,
                     "source": ser["source"]})
    pooled = {"rho": {am: rs["agreement"][("binary", am)]["rho"] for am in ACTION_MODELS},
              "n": len(rs["shared"])}
    return {"rows": rows, "pooled": pooled}


def write_members(mm: dict, b_run, g_run, out: Path) -> None:
    # the members the two selected runs pooled (a --members selection pools a subset)
    b_lab, g_lab = (db.members_label(db.run_member_labels(r)) for r in (b_run, g_run))
    pooled_by = b_lab if b_lab == g_lab else f"binary: {b_lab}; Gaussian: {g_lab}"
    head = " & ".join(f"eff\\_{m}" for m in ACTION_MODELS)
    lines = [r"\begin{tabular}{@{}l" + "r" * len(ACTION_MODELS) + r"rl@{}}", r"\toprule",
             f"member & {head} & $n$ & source (binary / Gaussian)\\\\", r"\midrule"]
    for r in mm["rows"]:
        cells = " & ".join(num(r["rho"][m], "{:.2f}") for m in ACTION_MODELS)
        ns = sorted(set(r["n"].values()))
        n_cell = str(ns[0]) if len(ns) == 1 else f"{ns[0]}..{ns[-1]}"
        lines.append(f"{esc(r['label'])} & {cells} & {n_cell} & {esc(r['source']['binary'])} /"
                     f" {esc(r['source']['gauss'])}\\\\")
    if not mm["rows"]:
        lines.append(r"\multicolumn{" + str(len(ACTION_MODELS) + 3)
                     + r"}{@{}l}{(no member elicits both protocols)}\\")
    lines.append(r"\midrule")
    p = mm["pooled"]
    lines.append("pooled & " + " & ".join(num(p["rho"][m], "{:.2f}") for m in ACTION_MODELS)
                 + f" & {p['n']} & run {b_run['id']} / run {g_run['id']}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\par\medskip",
              r"\noindent\emph{Member-matched rank agreement: Spearman $\rho$ of median efficiency"
              r" between one member's binary ranking (EVSI/C from its fits alone) and the same"
              r" member's Gaussian ranking (EVSI of the action model / C), over the scenarios both"
              r" rank ($n$). A ranking marked `run <id>' is that member's stored subset run;"
              r" `re-drawn' means the member's fits were re-drawn locally with the selected run's"
              f" seed and draw count ({b_run['n_draws']:,} binary, {g_run['n_draws']:,} Gaussian), as"
              r" the member-agreement analysis does, not the stored run. The pooled row is the"
              f" agreement of the two selected runs ({esc(pooled_by)} pooled).}}"]
    (out / "compare_members.tex").write_text("\n".join(lines) + "\n")


# --- plug-in comparison (v2.3) -------------------------------------------------------

def gauss_plugin_point(con, run, sid: int) -> dict | None:
    """The Gaussian plug-in point of one scenario: gaussian.scenario_metrics
    at the pooled medians (median of the repeat values, the catalog's) of
    d, x, k, L, kappa sigma0, B, K, sigma_b/sigma0 and C, over the run's
    members: {"medians", "eff": {m: EVSI_m / C}, "EVSI": {m: ...}, "R2",
    "fence_stepfix": the stepfix model's fence value, eq. fence at p =
    Phi(d) and the derived s, t with the same stakes B + K (the maximum of
    EVSI_stepfix over the threshold pi*, as EVSI* is of the binary EVSI),
    "eff_fence_stepfix": that over C, "fence_step": the step model with its
    prior on the fence, gaussian.voi_step_fence (its maximum over d),
    "eff_fence_step": that over C, "quad_lr2": L R^2 (the k = 2 quad value,
    threshold-free), "eff_lr2": L R^2 / C}; None when a quantity has no
    valid elicitation."""
    labels = db.run_member_labels(run)
    names = [n for n in GAUSS_PARAM_NAMES if n not in ("g_mu0", "g_sigma0")]
    med = {name: pooled_p50(con, run["protocol_id"], sid, name, labels) for name in names}
    if any(v is None for v in med.values()):
        return None
    metrics = gaussian.scenario_metrics({name: np.array([v]) for name, v in med.items()})
    r2 = float(metrics["R2"][0])
    lr2 = med["g_L"] * r2
    fence = float(model.voi_fence(metrics["p_derived"][0], metrics["s_derived"][0],
                                  metrics["t_derived"][0], med["g_B"], med["g_K"]))
    fence_step = float(gaussian.voi_step_fence(r2, med["g_B"], med["g_K"])[0])
    return {"medians": med, "eff": {m: float(metrics[f"eff_{m}"][0]) for m in ACTION_MODELS},
            "EVSI": {m: float(metrics[f"EVSI_{m}"][0]) for m in ACTION_MODELS},
            "R2": r2, "fence_stepfix": fence, "eff_fence_stepfix": fence / med["C"],
            "fence_step": fence_step, "eff_fence_step": fence_step / med["C"],
            "quad_lr2": lr2, "eff_lr2": lr2 / med["C"]}


def agreement(x, y, k: int) -> dict:
    """Spearman, Kendall and top-k overlap (ids by value, ties by index) of
    two aligned series; the correlations are None with fewer than 3 points
    or a constant series."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    ids = list(range(len(x)))
    top_x = set(sorted(ids, key=lambda i: (-x[i], i))[:k])
    top_y = set(sorted(ids, key=lambda i: (-y[i], i))[:k])
    return {"rho": spearman(x, y) if len(x) >= 3 else None,
            "tau": kendall(x, y) if len(x) >= 3 else None, "overlap": len(top_x & top_y)}


def plugin_comparison(con, b_run, g_run, shared: list[int]) -> dict:
    """Over the shared scenarios with a complete plug-in point in both
    protocols: {"sids", "binary": {sid: extra.plugin_point}, "gauss": {sid:
    gauss_plugin_point}, "models": {m: agreement of binary eff vs eff_m},
    "fence_stepfix": agreement of EVSI* vs the stepfix fence value (the same
    eq. fence, same stakes, the other family's p, s, t), "fence_step": EVSI*
    vs the step value on the fence (voi_step_fence), "fence_quad": EVSI* vs
    L R^2, each also over each protocol's own C ("<key>_eff"), "top_k",
    "n_zero_binary" (plug-in EVSI = 0: outside the gate at the medians),
    "n_zero_stepfix"}."""
    b_pts = {s: extra.plugin_point(con, b_run, s) for s in shared}
    g_pts = {s: gauss_plugin_point(con, g_run, s) for s in shared}
    sids = [s for s in shared if b_pts[s] is not None and g_pts[s] is not None]
    k = min(TOP_N, len(sids))
    b_eff = [b_pts[s]["eff"] for s in sids]
    out = {"sids": sids, "binary": {s: b_pts[s] for s in sids}, "gauss": {s: g_pts[s] for s in sids},
           "top_k": k, "models": {}}
    for m in ACTION_MODELS:
        out["models"][m] = agreement(b_eff, [g_pts[s]["eff"][m] for s in sids], k)
    for key, b_key, g_key in FENCE_SERIES:
        out[key] = agreement([b_pts[s][b_key] for s in sids], [g_pts[s][g_key] for s in sids], k)
    out["n_zero_binary"] = sum(1 for s in sids if b_pts[s]["EVSI"] <= 0.0)
    out["n_zero_stepfix"] = sum(1 for s in sids if g_pts[s]["EVSI"]["stepfix"] <= 0.0)
    return out


def write_plugin(pc: dict, b_run, g_run, out: Path) -> None:
    n, k = len(pc["sids"]), pc["top_k"]
    lines = [r"\begin{tabular}{@{}llrrr@{}}", r"\toprule",
             r"binary (plug-in) & Gaussian (plug-in) & Spearman $\rho$ & Kendall $\tau$ &"
             f" top-{k} overlap\\\\", r"\midrule"]

    def row(a: str, b: str, st: dict) -> str:
        return (f"{a} & {b} & {num(st['rho'], '{:.2f}')} & {num(st['tau'], '{:.2f}')}"
                f" & {st['overlap']} / {k}\\\\")

    for m in ACTION_MODELS:
        lines.append(row("eff $=$ EVSI$/C$", f"eff\\_{m}", pc["models"][m]))
    lines.append(r"\midrule")
    lines.append(row(r"EVSI$^\star$ (fence)", r"EVSI$^\star_{\mathrm{stepfix}}$ (fence)",
                     pc["fence_stepfix"]))
    lines.append(row(r"eff$^\star = $ EVSI$^\star/C$", r"EVSI$^\star_{\mathrm{stepfix}}/C$",
                     pc["fence_stepfix_eff"]))
    lines.append(row(r"EVSI$^\star$ (fence)", r"EVSI$_{\mathrm{step}}$ at $\Phi(d) = \pi^\star$ (fence)",
                     pc["fence_step"]))
    lines.append(row(r"eff$^\star = $ EVSI$^\star/C$", r"EVSI$_{\mathrm{step}}(\Phi^{-1}(\pi^\star))/C$",
                     pc["fence_step_eff"]))
    lines.append(row(r"EVSI$^\star$ (fence)", r"$L R^2$ (quad, $k=2$)", pc["fence_quad"]))
    lines.append(row(r"eff$^\star = $ EVSI$^\star/C$", r"$L R^2 / C$", pc["fence_quad_eff"]))
    lines += [r"\bottomrule", r"\end{tabular}", r"\par\medskip",
              r"\noindent\emph{Threshold-robust comparison over the " + str(n)
              + r" scenarios with a complete plug-in point in both protocols (of run "
              + str(b_run["id"]) + r" and run " + str(g_run["id"]) + r"'s members). Binary plug-in:"
              r" \texttt{model.voi} at the pooled elicited medians of $p$, $s$, $t$, $B$, $K$ and $C$"
              r" (the plugin.tex point); Gaussian plug-in: the action models at the pooled medians of"
              r" $d$, $x$, $k$, $L$, $\kappa\sigma_0$, $B$, $K$, $\sigma_b/\sigma_0$ and $C$. The"
              r" fence rows put each decision on the fence, so no gate applies:"
              r" EVSI$^\star = (B+K)\,p(1-p)(s+t-1)$ is the binary EVSI maximised over the threshold"
              r" $\pi^\star$ at fixed stakes (eq. fence), and"
              r" EVSI$^\star_{\mathrm{stepfix}}$ is the same maximum of the stepfix action model,"
              r" eq. fence at $p = \Phi(d)$ and the derived $s$, $t$ with the same stakes $B+K$"
              r" (the same action model and stakes, the other family's elicitation)."
              r" EVSI$_{\mathrm{step}}$ at $\Phi(d) = \pi^\star$ is the chapter's Gaussian fence:"
              r" the continuous-signal step value with the prior on the fence, $d = \Phi^{-1}(\pi^\star)$,"
              r" $\pi^\star = K/(B+K)$, its maximum over $d$; it removes $d$ at the elicited"
              r" $\pi^\star$ where EVSI$^\star$ removes $\pi^\star$ at the elicited $p$. The quad"
              r" value $L R^2$ (the $k=2$ loss, $R^2$ bias-corrected) has no threshold at all; pairing"
              r" it with EVSI$^\star$ is this study's choice, not the chapter's: a graded response"
              r" with its own stakes scale $L$, so that pair compares two action models and two stakes"
              r" elicitations. Each pair is compared"
              r" as values and as efficiencies over each protocol's own median $C$. Binary plug-in"
              r" EVSI $= 0$ (outside the gate at the medians) on " + str(pc["n_zero_binary"])
              + r" scenarios, Gaussian stepfix on " + str(pc["n_zero_stepfix"]) + r".}"]
    (out / "compare_plugin.tex").write_text("\n".join(lines) + "\n")


def fig_plugin(con, pc: dict, out: Path) -> None:
    sids = pc["sids"]
    groups = figures.scenario_groups(con)
    grp_of = [groups.get(s) or "(no group)" for s in sids]
    names = sorted(set(grp_of))
    colors = figures.group_colors(names)
    panels = (("(a) plug-in efficiency", "binary plug-in eff (EVSI / C)", "Gaussian stepfix plug-in eff",
               np.array([pc["binary"][s]["eff"] for s in sids]),
               np.array([pc["gauss"][s]["eff"]["stepfix"] for s in sids]),
               pc["models"]["stepfix"]["rho"], figures.EFF_FLOOR),
              (r"(b) the stepfix fence ($p = \Phi(d)$, derived $s, t$)",
               "binary fence EVSI* (USD)", "Gaussian stepfix fence EVSI* (USD)",
               np.array([pc["binary"][s]["EVSI_star"] for s in sids]),
               np.array([pc["gauss"][s]["fence_stepfix"] for s in sids]),
               pc["fence_stepfix"]["rho"], figures.EVSI_FLOOR),
              (r"(c) the step value on the fence ($d = \Phi^{-1}(\pi^*)$)",
               "binary fence EVSI* (USD)", "Gaussian step value on the fence (USD)",
               np.array([pc["binary"][s]["EVSI_star"] for s in sids]),
               np.array([pc["gauss"][s]["fence_step"] for s in sids]),
               pc["fence_step"]["rho"], figures.EVSI_FLOOR),
              ("(d) the quad value L R$^2$ (no threshold)", "binary fence EVSI* (USD)",
               "Gaussian quad value L R$^2$ (USD)",
               np.array([pc["binary"][s]["EVSI_star"] for s in sids]),
               np.array([pc["gauss"][s]["quad_lr2"] for s in sids]),
               pc["fence_quad"]["rho"], figures.EVSI_FLOOR))
    fig, axes = plt.subplots(2, 2, figsize=(6.2, 5.8))
    axes = axes.ravel()
    for ax, (title, xl, yl, x, y, rho, floor) in zip(axes, panels, strict=True):
        xf, yf = np.maximum(x, floor), np.maximum(y, floor)
        floored = (x < floor) | (y < floor)
        for g in names:
            mask = np.array([v == g for v in grp_of])
            ax.plot(xf[mask & ~floored], yf[mask & ~floored], "o", color=colors[g], ms=4.5, mec="white",
                    mew=0.5, label=g if len(names) > 1 else None, zorder=3)
            ax.plot(xf[mask & floored], yf[mask & floored], "o", mfc="white", mec=colors[g], ms=4.5, zorder=3)
        if len(sids):
            lim = [min(xf.min(), yf.min()) / 3, max(xf.max(), yf.max()) * 3]
            ax.plot(lim, lim, ls="--", lw=0.8, color="#555555", zorder=1)
            ax.set_xlim(*lim)
            ax.set_ylim(*lim)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.text(0.03, 0.95, f"Spearman $\\rho$ = {'--' if rho is None else f'{rho:.2f}'} (n={len(sids)})",
                transform=ax.transAxes, fontsize=7, va="top")
        ax.set_title(title, fontsize=7)
        ax.set_xlabel(xl, fontsize=7)
        ax.set_ylabel(yl, fontsize=7)
        ax.tick_params(labelsize=7)
    if len(names) > 1:
        axes[0].legend(fontsize=6, loc="lower right", frameon=False, title="group", title_fontsize=6)
    fig.suptitle("Plug-in points at each protocol's pooled medians (open markers: floored at"
                 f" {figures.EFF_FLOOR:g} / {figures.EVSI_FLOOR:g});\n(b)-(d): the binary fence value"
                 " EVSI* = (B+K) p (1-p) (s+t-1) against a Gaussian value no gate can zero", fontsize=7)
    fig.savefig(out / "fig_compare_plugin.pdf")
    plt.close(fig)


# --- joint noise table (v2.3) ----------------------------------------------------------

def noise_comparison(con, b_run, g_run) -> dict:
    """Per shared member: {"members": [labels], "binary": {label: ({name:
    median spread}, {name: n})}, "gauss": {label: (...)}, "ratios": {label:
    {ratio label: Gaussian median spread / binary median spread}}}, every
    spread over the first MATCHED_K valid repeats of each scenario
    (extra.member_noise, i.e. db.elicited_spread: relative, or max - min in
    sd units for d)."""
    b_prot = con.execute("SELECT * FROM protocols WHERE id=?", (b_run["protocol_id"],)).fetchone()
    out = {"members": [], "binary": {}, "gauss": {}, "ratios": {},
           # a staged binary protocol: its decision-stage spreads are medians over groups
           "b_name": b_prot["name"], "b_stages": db.protocol_stages(b_prot)}
    for m in shared_members(con, b_run, g_run):
        label = db.member_label(m)
        b = extra.member_noise(con, b_run["protocol_id"], m, MATCHED_K, list(NOISE_BINARY))
        g = extra.member_noise(con, g_run["protocol_id"], m, MATCHED_K, list(NOISE_GAUSS))
        out["members"].append(label)
        out["binary"][label], out["gauss"][label] = b, g
        out["ratios"][label] = {
            lab: (g[0][gq] / b[0][bq] if g[0].get(gq) is not None and b[0].get(bq) else None)
            for lab, gq, bq in NOISE_RATIOS}
    return out


def write_noise(nc: dict, b_run, g_run, out: Path) -> None:
    """compare_noise.tex; every row is built as a cell list joined once, so
    the column count always matches the tabular's (with no shared member
    the table holds only its note). A staged binary protocol's n row reads
    `groups / scenarios` (extra.noise_n_label) and the caption says which
    unit its decision-stage cells are over (extra.staged_noise_note)."""
    members = nc["members"]
    stages = nc.get("b_stages")

    def cells(*items) -> str:
        return " & ".join(items) + r"\\"

    lines = [r"\begin{tabular}{@{}ll" + "r" * len(members) + r"@{}}", r"\toprule",
             cells("protocol", "quantity", *(esc(m) for m in members)), r"\midrule"]

    def block(title: str, names, key: str, n_stages) -> None:
        lines.append(r"\multicolumn{" + str(len(members) + 2) + r"}{@{}l}{\emph{" + title + r"}}\\")
        for name in names:
            label = tex_param(name) + esc(db.spread_label(name)).replace(" - ", " $-$ ")
            lines.append(cells("", label, *(num(nc[key][m][0].get(name), "{:.2f}") for m in members)))
        n_label = "$n$ (groups / scenarios)" if n_stages is not None else "$n$ (scenarios)"
        lines.append(cells("", n_label, *(extra.noise_n_label(nc[key][m][1], n_stages) for m in members)))

    if members:
        block("binary", NOISE_BINARY, "binary", stages)
        lines.append(r"\midrule")
        block("Gaussian", NOISE_GAUSS, "gauss", None)
        lines.append(r"\midrule")
        for lab, gq, bq in NOISE_RATIOS:
            lines.append(cells("ratio", f"{tex_param(gq)} (Gaussian) / {tex_param(bq)} (binary)",
                               *(num(nc["ratios"][m][lab], "{:.2f}") for m in members)))
    else:
        lines.append(r"\multicolumn{2}{@{}l}{(no member elicits both protocols)}\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\par\medskip",
              r"\noindent\emph{Cross-repeat spread per member at matched $k$: median over scenarios of"
              r" $(\max - \min) / $ pooled p50 of the repeat values ($\max - \min$ in prior-sd units for"
              f" $d$) over the first {MATCHED_K} valid repeats of each scenario, for the binary"
              r" quantities and the Gaussian ones side by side; the members listed elicit both"
              r" protocols (of run " + str(b_run["id"]) + r" and run " + str(g_run["id"])
              + r"). The ratio rows divide the Gaussian median USD spread by the binary one: below 1,"
              r" the Gaussian question is the more reproducible at the same elicitor"
              + extra.staged_noise_note([nc.get("b_name", "")] if stages is not None else []) + r".}"]
    (out / "compare_noise.tex").write_text("\n".join(lines) + "\n")


# --- outputs ------------------------------------------------------------------

def write_compare(rs: dict, b_run, g_run, out: Path) -> None:
    n = len(rs["shared"])
    lines = [r"\begin{tabular}{@{}llrrr@{}}", r"\toprule",
             r"ranking A & ranking B & Spearman $\rho$ & Kendall $\tau$ & "
             f"top-{rs['top_k']} overlap\\\\", r"\midrule"]
    for (a, c), st in rs["agreement"].items():
        lines.append(f"{esc(a)} & {esc(c)} & {num(st['rho'], '{:.2f}')} & {num(st['tau'], '{:.2f}')}"
                     f" & {st['overlap']} / {rs['top_k']}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\par\medskip",
              r"\noindent\emph{Rank agreement of median efficiency over the " + str(n)
              + r" scenarios ranked by both run " + str(b_run["id"]) + " (binary) and run "
              + str(g_run["id"]) + r" (Gaussian): binary efficiency = EVSI/C; eff\_quad, eff\_kg,"
              r" eff\_step, eff\_stepfix = EVSI of that action model / C.}", r"\par\medskip",
              r"\begin{tabular}{@{}lrr@{}}", r"\toprule",
              r" & stepfix median EVSI $= 0$ & stepfix median EVSI $> 0$\\", r"\midrule"]
    g = rs["gate"]
    lines.append(f"binary median EVSI $= 0$ & {g['both_zero']} & {g['binary_only']}\\\\")
    lines.append(f"binary median EVSI $> 0$ & {g['gauss_only']} & {g['both_positive']}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\par\medskip",
              r"\noindent\emph{Gate agreement: " + f"{100 * g['agree']:.0f}" + r"\% of the "
              + str(n) + r" scenarios fall on the diagonal (a median EVSI below "
              + f"{EVSI_ZERO_USD:g}" + r" USD counts as zero).}"]
    (out / "compare_models.tex").write_text("\n".join(lines) + "\n")


def write_consistency(res: dict, g_run, out: Path, pst: dict | None = None) -> None:
    lines = [r"\begin{tabular}{@{}lrrrrrrr@{}}", r"\toprule",
             r"residual & $n$ & q25 & q50 & q75 & threshold & flagged & $\rho$(spread)\\", r"\midrule"]
    for name, _label, _ in RESIDUALS:
        st = res[name]
        lines.append(f"{st['label']} & {st['n']} & {num(st['q25'])} & {num(st['q50'])} & {num(st['q75'])}"
                     f" & {st['threshold']:g} & {pct(st['flagged'])}"
                     f" & {num(st['rho_spread'], '{:.2f}')} ($n$={st['n_spread']})\\\\")
    sc = res["score"]
    lines.append(r"\midrule")
    lines.append(f"consistency score (max residual / threshold) & {sc['n']} & {num(sc['q25'])} &"
                 f" {num(sc['q50'])} & {num(sc['q75'])} & 1 & {pct(sc['above_one'])} & --\\\\")
    members = esc(db.members_label(db.run_member_labels(g_run)))
    lines += [r"\bottomrule", r"\end{tabular}", r"\par\medskip",
              r"\noindent\emph{Over-determination residuals of the Gaussian protocol (run "
              + str(g_run["id"]) + r"), over the valid elicitations of " + members
              + r": quantiles, the warning"
              r" threshold, the fraction of elicitations flagged, and the Spearman between each"
              r" scenario's median residual and the cross-repeat spread of the quantity the"
              r" residual checks ((max - min) / pooled p50 of the repeat values; max - min"
              r" in sd units for $d$, which crosses zero).}"]
    if pst is not None:
        lines += [r"\par\medskip", r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule",
                  r"quantity & $n$ & Spearman $\rho$ & median $|$derived $-$ elicited$|$ &"
                  r" mean (derived $-$ elicited)\\", r"\midrule"]
        for name in ("p", "s", "t"):
            st = pst[name]
            lines.append(f"${name}$ & {st['n']} & {num(st['rho'], '{:.2f}')} & {num(st['mad'], '{:.3f}')}"
                         f" & {num(st['bias'], '{:+.3f}')}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}", r"\par\medskip",
                  r"\noindent\emph{Derived vs elicited: the Gaussian run's median $p = \Phi(d)$, $s$, $t$"
                  r" (fixed-mark orthant probabilities) against the binary protocol's pooled elicited"
                  r" p50; the last column is the mean signed difference, the bias of the Gaussian"
                  r" family's implied probability against the binary elicitation.}"]
    (out / "consistency_gauss.tex").write_text("\n".join(lines) + "\n")


def write_macros(rs: dict, pst: dict, b_run, g_run, out: Path, mm: dict | None = None,
                 pc: dict | None = None, nc: dict | None = None, prefix: str = MACRO_PREFIX) -> dict:
    """macros_compare.tex, written under `prefix` (study.newcommands);
    returned with their voi names."""
    ag = rs["agreement"]
    macros = {
        "voiGaussBinaryRunId": b_run["id"],
        "voiGaussRunId": g_run["id"],
        "voiGaussN": len(rs["shared"]),
        "voiGaussTopK": rs["top_k"],
        "voiGaussGateAgree": f"{100 * rs['gate']['agree']:.0f}\\%",
    }
    for m in ACTION_MODELS:
        macros[f"voiGaussRho{MODEL_MACRO[m]}"] = num(ag[("binary", m)]["rho"], "{:.2f}")
        macros[f"voiGaussTau{MODEL_MACRO[m]}"] = num(ag[("binary", m)]["tau"], "{:.2f}")
        macros[f"voiGaussTopOverlap{MODEL_MACRO[m]}"] = ag[("binary", m)]["overlap"]
    for name in ("p", "s", "t"):
        macros[f"voiGaussRho{name.upper()}"] = num(pst[name]["rho"], "{:.2f}")
        macros[f"voiGaussMad{name.upper()}"] = num(pst[name]["mad"], "{:.2f}")
        macros[f"voiGaussBias{name.upper()}"] = num(pst[name]["bias"], "{:+.3f}")
    if mm is not None:
        names = member_macro_names([r["label"] for r in mm["rows"]])
        for r in mm["rows"]:
            for m in ACTION_MODELS:
                key = f"voiGaussRhoMember{MODEL_MACRO[m]}{names[r['label']]}"
                macros[key] = num(r["rho"][m], "{:.2f}")
        macros["voiGaussNMembersMatched"] = len(mm["rows"])
    if pc is not None:
        macros["voiGaussPluginN"] = len(pc["sids"])
        macros["voiGaussPluginTopK"] = pc["top_k"]
        for m in ACTION_MODELS:
            st = pc["models"][m]
            macros[f"voiGaussPluginRho{MODEL_MACRO[m]}"] = num(st["rho"], "{:.2f}")
            macros[f"voiGaussPluginTau{MODEL_MACRO[m]}"] = num(st["tau"], "{:.2f}")
            macros[f"voiGaussPluginTopOverlap{MODEL_MACRO[m]}"] = st["overlap"]
        for key, stem in FENCE_PAIRS:
            macros[f"{stem}Rho"] = num(pc[key]["rho"], "{:.2f}")
            macros[f"{stem}Tau"] = num(pc[key]["tau"], "{:.2f}")
            macros[f"{stem}TopOverlap"] = pc[key]["overlap"]
    if nc is not None:
        names = member_macro_names(nc["members"])
        for label in nc["members"]:
            macros[f"voiGaussNoiseRatio{names[label]}"] = num(nc["ratios"][label]["L"], "{:.2f}")
    (out / "macros_compare.tex").write_text("\n".join(newcommands(macros, prefix)) + "\n")
    return macros


def fig_compare(con, rs: dict, out: Path) -> None:
    shared = rs["shared"]
    groups = figures.scenario_groups(con)
    x = np.array([rs["series"]["binary"][s] for s in shared])
    y = np.array([rs["series"]["stepfix"][s] for s in shared])
    xf, yf = np.maximum(x, figures.EFF_FLOOR), np.maximum(y, figures.EFF_FLOOR)
    floored = (x < figures.EFF_FLOOR) | (y < figures.EFF_FLOOR)
    grp_of = [groups.get(s) or "(no group)" for s in shared]
    names = sorted(set(grp_of))
    colors = figures.group_colors(names)
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    for g in names:
        mask = np.array([v == g for v in grp_of])
        ax.plot(xf[mask & ~floored], yf[mask & ~floored], "o", color=colors[g], ms=5, mec="white",
                mew=0.5, label=g if len(names) > 1 else None, zorder=3)
        ax.plot(xf[mask & floored], yf[mask & floored], "o", mfc="white", mec=colors[g], ms=5, zorder=3)
    lim = [min(xf.min(), yf.min()) / 3, max(xf.max(), yf.max()) * 3]
    ax.plot(lim, lim, ls="--", lw=0.8, color="#555555", zorder=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    rho = rs["agreement"][("binary", "stepfix")]["rho"]
    ax.text(0.03, 0.95, f"Spearman $\\rho$ = {'--' if rho is None else f'{rho:.2f}'} (n={len(shared)})",
            transform=ax.transAxes, fontsize=8, va="top")
    if len(names) > 1:
        ax.legend(fontsize=6.5, loc="lower right", frameon=False, title="group", title_fontsize=6.5)
    ax.set_xlabel(f"binary median efficiency (EVSI / C; open: floored at {figures.EFF_FLOOR:g})")
    ax.set_ylabel("Gaussian median eff_stepfix (EVSI_stepfix / C)")
    ax.set_title("Binary model vs Gaussian stepfix action model, median efficiency")
    fig.savefig(out / "fig_compare_models.pdf")
    plt.close(fig)


def fig_derived(pst: dict, out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(6.2, 2.4))
    for ax, name in zip(axes, ("p", "s", "t"), strict=True):
        st = pst[name]
        ax.plot(st["x"], st["y"], "o", color=figures.ACCENT, ms=4, mec="white", mew=0.4, alpha=0.85)
        ax.plot([0, 1], [0, 1], ls="--", lw=0.7, color="#c9c9c9", zorder=0)
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.set_xlabel(f"elicited ${name}$ (binary protocol, pooled p50)", fontsize=7)
        ax.set_ylabel(f"derived ${name}$ (Gaussian run median)", fontsize=7)
        rho = "--" if st["rho"] is None else f"{st['rho']:.2f}"
        mad = "--" if st["mad"] is None else f"{st['mad']:.2f}"
        bias = "--" if st["bias"] is None else f"{st['bias']:+.3f}"
        ax.text(0.96, 0.05, f"$\\rho$ = {rho}, med |diff| = {mad},\nmean diff = {bias} (n={st['n']})",
                transform=ax.transAxes, fontsize=6, ha="right")
        ax.tick_params(labelsize=7)
    fig.suptitle("Derived p = Phi(d), s, t (fixed mark at theta_c) vs the binary elicitation", fontsize=8)
    fig.savefig(out / "fig_derived_pst.pdf")
    plt.close(fig)


def make_all(con, b_run, g_run, out: Path, prefix: str = MACRO_PREFIX) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(figures.STYLE)
    rs = rank_stats(con, b_run, g_run)
    pst = derived_vs_elicited(con, b_run, g_run, rs["shared"])
    res = residual_stats(con, g_run)
    mm = member_matrix(con, b_run, g_run, rs)
    pc = plugin_comparison(con, b_run, g_run, rs["shared"])
    nc = noise_comparison(con, b_run, g_run)
    write_compare(rs, b_run, g_run, out)
    write_consistency(res, g_run, out, pst)
    write_members(mm, b_run, g_run, out)
    write_plugin(pc, b_run, g_run, out)
    write_noise(nc, b_run, g_run, out)
    macros = write_macros(rs, pst, b_run, g_run, out, mm, pc, nc, prefix)
    fig_compare(con, rs, out)
    fig_derived(pst, out)
    fig_plugin(con, pc, out)
    return {"rank": rs, "pst": pst, "residuals": res, "members": mm, "plugin": pc, "noise": nc,
            "macros": macros}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    ap.add_argument("--binary", default="p001", help="binary protocol (latest run; default p001)")
    ap.add_argument("--gaussian", default="g001", help="Gaussian protocol (latest run; default g001)")
    ap.add_argument("--members", default=None,
                    help="comma-separated provider:model subset: the latest run of each protocol"
                         " that pooled exactly these members")
    add_tag_arg(ap)
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    out, prefix = study.tagged(args.tag)
    con = study.connect()
    b_run, g_run = select_runs(con, args.binary, args.gaussian, db.parse_member_labels(args.members))
    result = make_all(con, b_run, g_run, out, prefix)
    ag = result["rank"]["agreement"]
    print(f"{len(result['rank']['shared'])} shared scenarios; Spearman binary vs "
          + ", ".join(f"{m} {num(ag[('binary', m)]['rho'], '{:.2f}')}" for m in ACTION_MODELS)
          + f"; gate agreement {100 * result['rank']['gate']['agree']:.0f}%")
    for r in result["members"]["rows"]:
        print(f"member {r['label']}: Spearman binary vs "
              + ", ".join(f"{m} {num(r['rho'][m], '{:.2f}')}" for m in ACTION_MODELS)
              + f" (binary {r['source']['binary']}, Gaussian {r['source']['gauss']})")
    pc = result["plugin"]
    print(f"plug-in ({len(pc['sids'])} scenarios): Spearman binary eff vs "
          + ", ".join(f"{m} {num(pc['models'][m]['rho'], '{:.2f}')}" for m in ACTION_MODELS)
          + f"; fence EVSI* vs stepfix fence {num(pc['fence_stepfix']['rho'], '{:.2f}')}, vs step on the"
          f" fence {num(pc['fence_step']['rho'], '{:.2f}')}, vs quad L R^2"
          f" {num(pc['fence_quad']['rho'], '{:.2f}')}")
    for label in result["noise"]["members"]:
        print(f"noise ratio {label}: Gaussian L / binary B spread"
              f" {num(result['noise']['ratios'][label]['L'], '{:.2f}')}")
    print("wrote " + ", ".join(str(out / f) for f in OUTPUTS))


if __name__ == "__main__":
    main()
