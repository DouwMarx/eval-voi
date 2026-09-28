"""Eval-study analyses beyond figures.py / tables.py, reading only from a
study's voi.db. Outputs land in <study>/report/generated/:

1. fig_level_uplift.pdf + level_uplift.tex: ladders = groups whose leveled
   scenarios share one agent / decision / theta text (a step between two
   different decisions is not a marginal of anything; other leveled groups
   are skipped with a printed reason). Per ladder the draws use common random
   numbers: p, B, K (level-invariant under that gate) are drawn once from the
   pooled fits of all rungs, s, t, C per rung from its own fits, so the
   adjacent-rung marginals dEVSI = EVSI[l+1] - EVSI[l] and dC = C[l+1] - C[l]
   isolate the rung's effect. The marginal efficiency is the ratio of medians
   median(dEVSI) / median(dC) with P(dC > 0), P(dEVSI > 0) and
   P(dEVSI > dC): quantiles of the per-draw ratio are dominated by draws with
   dC near zero and were reporting noise. These are NOT the stored run's
   draws (fresh rng from the run's seed and draw count).
2. fig_within_group_consistency.pdf + consistency.tex: for groups whose
   scenarios share identical agent / decision / theta text, the elicited p50
   of p, B, K should be level-invariant while s, t, C move with the rung;
   the table reports the ratio CV(p) / mean(CV(s), CV(t)), which a staged
   protocol (p, B, K elicited once per group) makes 0 by design.
3. fig_domain_map.pdf + domain_summary.tex: EVSI vs C by attributes.risk_domain
   (colour) and group (marker), with per-domain / per-group summaries and the
   percentile rank of every non-reference scenario within the reference
   group ('AI safety eval', else the other groups). Skipped without risk_domain.
4. fig_member_agreement.pdf + member_agreement.tex: protocols with > 1
   member only; pairwise p50 agreement per parameter and a per-member
   efficiency ranking (each member's fits pooled alone, mixture re-drawn
   locally with the run's seed and draw count: these draws are NOT the stored
   run, whose mixture pools all members) with a Spearman matrix and top-5 ids.
5. simplicity.tex + macros_extra.tex: is the EVSI/C ranking reproduced by
   the simpler EVPI/C ranking (Spearman, top-10 overlap, headroom), both
   rankings being medians of per-draw ratios stored by the run (metrics
   'efficiency' and 'evpi_efficiency', so no estimator difference leaks into
   the comparison), and the global |rho| per parameter over all scenarios vs
   the top quartile (n = scenarios with a defined rho, which a constant
   efficiency, EVSI = 0 on every draw, has not).
6. protocol_noise_matched.tex: per protocol and member with at least two
   valid repeats, cross-repeat p50 spread over the first MATCHED_K VALID
   repeats of each scenario (a count in repeat_ix order, so an invalid
   middle repeat does not shrink the pool) and, when the member holds more
   on any scenario, over all of them (labelled with the count actually
   pooled per scenario, min..max where scenarios differ), plus the Spearman
   compare matrix between the latest v2 runs of every protocol pair (a run
   the v2 analyses refuse, db.run_predates_v2, is skipped).
7. plugin.tex + fig_plugin.pdf + macros in macros_extra.tex: the plug-in
   summary next to the Monte Carlo one, a longtable like catalog.tex. Per
   scenario (in the run's median efficiency order): EVSI, EVPI and
   efficiency from model.voi at the pooled elicited medians of p, s, t, B, K,
   C (median of the p50 across valid elicitations, as tables.write_catalog
   defines them for p, s, t, B, K, whose values the catalog already lists and
   this table does not repeat; for C too, NOT the catalog's mixture median,
   so C is printed here), the gate regime at the medians (in gate / always
   respond / never respond, from the threshold pi* = K / (B + K) against the
   posteriors pi1, pi0), the run's median and MEAN efficiency (the mean over
   the run's draws, replayed from the DB and verified against the stored
   quantiles), P(EVSI > C) and P(EVSI > 0) over the draws. The figure
   compares the three rankings pairwise (rank scatter, Spearman annotated).
   The elicited stakes vary several-fold across repeats, so the mixture can
   close the gate in more than half the draws (median EVSI 0) where the
   medians sit inside it; this table shows that side by side.

Usage: python -m voi_rank.analysis.extra --study PATH [--protocol p001] [--run ID]
       [--members claude_cli:sonnet,claude_cli:opus]
(default: the latest all-member run of protocol p001; --members selects the
latest run that pooled exactly that subset; --run overrides; prints
'run <id> (protocol <name>[, members ...])' like figures.py. Every analysis
of the run reads its members only: the pooled medians, the ladder and
per-member re-draws, the replay, the member agreement.) Only the plug-in analysis
replays the stored run (for the mean over its draws); when repeats added
under the protocol after the run desynchronise the replay, it is skipped
with a printed reason and nothing aborts. Every other analysis reads the
stored results or draws its own mixture. Analyses whose inputs are absent
are skipped with a printed reason and their stale outputs removed.

Helpers duplicated from figures.py / tables.py / mc.py (style constants, run
selection, LaTeX escaping, mixture sampling) are copied here on purpose so
this module depends only on db, model, sensitivity and study.
"""

from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

from voi_rank import db, model  # noqa: E402
from voi_rank.fit import FAMILY_BY_PARAM  # noqa: E402
from voi_rank.sensitivity import spearman  # noqa: E402
from voi_rank.study import Study, add_study_arg  # noqa: E402

# --- style (mirrors figures.py) --------------------------------------------

ACCENT = "#0072B2"
INTERVAL = "#9aa5b1"
CATEGORICAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7",
               "#56B4E9", "#F0E442", "#000000"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
EFF_FLOOR = 1e-3
EVSI_FLOOR = 1e-2
STYLE = {
    "font.family": "serif",
    "mathtext.fontset": "cm",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e3e3e3",
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "figure.constrained_layout.use": True,
}

# --- constants (mirror mc.py / tables.py) -----------------------------------

Q3 = (0.05, 0.50, 0.95)
# level uplift: parameters of the decision (shared by every rung of a ladder)
# and of the instrument (drawn per rung)
SHARED_PARAMS = ("p", "B", "K")
RUNG_PARAMS = ("s", "t", "C")
REFERENCE_GROUP = "AI safety eval"
MATCHED_K = 3
TOP_N_MEMBER = 5
TOP_N_OVERLAP = 10
TOP_N_PLUGIN = 5
# replay verification (mirrors mc.py): the stored efficiency summary a replay must reproduce
REPLAY_RTOL = 1e-9
SUMMARY_QS = (0.05, 0.25, 0.50, 0.75, 0.95)
RESULT_COLUMNS = ("q05", "q25", "q50", "q75", "q95")
# gate regime at the plug-in medians -> table cell
REGIME_CELL = {"in gate": "gate", "always respond": "always", "never respond": "never"}
# scatter panels of fig_plugin: (x ranking, y ranking) keys of plugin_stats rows
PLUGIN_PANELS = (("plugin", "mc_median"), ("plugin", "mc_mean"), ("mc_median", "mc_mean"))
PLUGIN_AXIS = {"plugin": "plug-in rank", "mc_median": "MC median rank", "mc_mean": "MC mean rank"}
PLUGIN_ANNOTATE_MAX = 25
PARAM_MACRO = {"p": "P", "s": "S", "t": "T", "B": "B", "K": "K", "C": "C"}
LATEX_SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
                  "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
                  "^": r"\textasciicircum{}"}
OUTPUTS = {
    "level_uplift": ("fig_level_uplift.pdf", "level_uplift.tex"),
    "consistency": ("fig_within_group_consistency.pdf", "consistency.tex"),
    "domain_map": ("fig_domain_map.pdf", "domain_summary.tex"),
    "member_agreement": ("fig_member_agreement.pdf", "member_agreement.tex"),
    "simplicity": ("simplicity.tex", "macros_extra.tex"),
    "plugin": ("fig_plugin.pdf", "plugin.tex", "macros_extra.tex"),
    "protocol_noise_matched": ("protocol_noise_matched.tex",),
}
MACROS_FILE = "macros_extra.tex"


# --- LaTeX helpers (mirror tables.py) ---------------------------------------

def esc(text) -> str:
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in str(text))


def money(v) -> str:
    if v is None or not np.isfinite(v):
        return "--"
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1e6:
        return f"{sign}{v/1e6:.3g}M"
    if v >= 1e3:
        return f"{sign}{v/1e3:.3g}k"
    return f"{sign}{v:.3g}"


def num(v, fmt: str = "{:.3g}") -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "--"
    return fmt.format(v)


def pct(v) -> str:
    return "--" if v is None or not np.isfinite(v) else f"{100.0 * v:.0f}\\%"


def tabular(colspec: str, header: str, rows: list[str], caption: str | None = None) -> str:
    """A booktabs tabular fragment (rows already joined with &, no \\\\)."""
    lines = [r"\begin{tabular}{" + colspec + "}", r"\toprule", header + r"\\", r"\midrule"]
    lines += [r if r.startswith(r"\midrule") else r + r"\\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}"]
    text = "\n".join(lines) + "\n"
    return (f"% {caption}\n" + text) if caption else text


def longtable(colspec: str, header: str, rows: list[str], caption: str, label: str) -> str:
    """A booktabs longtable fragment with the head and foot of
    tables.write_catalog (rows already joined with &, no \\\\); the caption is
    part of the fragment, so the report inputs it outside any float."""
    lines = [r"\begin{longtable}{" + colspec + "}",
             r"\caption{" + caption + r"}\label{" + label + r"}\\",
             r"\toprule", header + r"\\", r"\midrule\endfirsthead",
             r"\toprule " + header + r"\\\midrule\endhead", r"\bottomrule\endfoot"]
    lines += [r + r"\\" for r in rows]
    lines.append(r"\end{longtable}")
    return "\n".join(lines) + "\n"


def _write(out: Path, name: str, text: str) -> Path:
    path = out / name
    path.write_text(text)
    return path


def _unlink(out: Path, names) -> None:
    for name in names:
        p = out / name
        if p.exists():
            p.unlink()


def write_macros(out: Path, macros: dict, merge: bool = False) -> Path:
    """\\newcommand lines in MACROS_FILE. merge=True keeps the other analyses'
    macros already in the file and replaces those with the same name, so the
    file is never left with a duplicate \\newcommand (a LaTeX error)."""
    path = out / MACROS_FILE
    keep = []
    if merge and path.exists():
        names = {f"\\newcommand{{\\{k}}}" for k in macros}
        keep = [line for line in path.read_text().splitlines()
                if line.strip() and not any(line.startswith(n) for n in names)]
    lines = keep + [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in macros.items()]
    path.write_text("\n".join(lines) + "\n")
    return path


# --- shared readers (mirror figures.py) -------------------------------------

def metric_rows(con, run_id: int, metric: str) -> dict[int, dict]:
    return {r["scenario_id"]: dict(r) for r in con.execute(
        "SELECT * FROM results WHERE run_id=? AND metric=?", (run_id, metric))}


def titles(con) -> dict[int, str]:
    return {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}


def run_kind(con, run_id: int) -> str:
    return db.run_model_kind(con, db.get_run(con, run_id))


def primary_metric(con, run_id: int) -> str:
    return db.primary_metric(run_kind(con, run_id))


def evsi_metric(con, run_id: int) -> str:
    return db.evsi_metric(run_kind(con, run_id))


def ranked_ids(con, run_id: int) -> list[int]:
    eff = metric_rows(con, run_id, primary_metric(con, run_id))
    return sorted(eff, key=lambda s: (-(eff[s]["q50"] or 0.0), -(eff[s]["p_positive"] or 0.0), s))


def scenario_groups(con) -> dict[int, str | None]:
    return {r["id"]: r["grp"] for r in con.execute("SELECT id, grp FROM scenarios")}


def group_colors(groups: list[str]) -> dict[str, str]:
    return {g: CATEGORICAL[i % len(CATEGORICAL)] for i, g in enumerate(groups)}


def run_members(con, run) -> list[dict]:
    """The members the run pooled (the protocol's, or the stored subset)."""
    return db.run_members(con, run)


def run_fits(con, run) -> dict[int, dict[str, list[dict]]]:
    """complete_fits over the run's members (mc.complete_fits of the run)."""
    return complete_fits(db.scenario_param_fits(con, run["protocol_id"], members=db.run_member_labels(run)))


def add_run_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--protocol", default="p001",
                    help="use the latest run of this protocol (default: p001)")
    ap.add_argument("--run", type=int, default=None, help="explicit run id (overrides --protocol)")
    ap.add_argument("--members", default=None,
                    help="comma-separated provider:model subset: use the latest run of the protocol"
                         " that pooled exactly these members (default: the all-member run)")


def select_run(con, run_id: int | None, protocol: str, members: list[str] | None = None):
    """As figures.select_run: a v1 run (no data_hash, or sensitivities for
    the retired parameter e) is refused."""
    run = db.get_run(con, run_id) if run_id is not None else db.latest_run(con, protocol, members)
    prot = con.execute("SELECT name FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    name = prot["name"] if prot else "unknown"
    reason = db.run_predates_v2(con, run)
    if reason:
        raise RuntimeError(f"run {run['id']} (protocol {name}) predates the v2 model: {reason};"
                           f" run `python -m voi_rank.mc --protocol {name}` first")
    labels = db.run_member_labels(run)
    print(f"run {run['id']} (protocol {name}" + (f", members {', '.join(labels)}" if labels else "") + ")")
    return run


def scenario_levels(con) -> dict[int, float]:
    """{scenario_id: attributes.level} for scenarios with a numeric level."""
    out = {}
    for r in con.execute("SELECT * FROM scenarios"):
        lv = db.scenario_attributes(r).get("level")
        if isinstance(lv, (int, float)) and not isinstance(lv, bool):
            out[r["id"]] = float(lv)
    return out


def level_label(lv: float) -> str:
    return str(int(lv)) if float(lv).is_integer() else f"{lv:g}"


def log_axis(ax, axis: str, values) -> None:
    """Log scale on one axis spanning at least one decade around the data
    (so a level-invariant parameter reads as flat, not as a zoomed-in wobble),
    with major decade ticks only."""
    vals = np.asarray([v for v in values if v is not None and np.isfinite(v) and v > 0], dtype=float)
    lo, hi = (vals.min(), vals.max()) if vals.size else (1.0, 10.0)
    span = np.log10(hi / lo)
    if span < 1.0:
        centre = np.sqrt(lo * hi)
        lo, hi = centre / np.sqrt(10.0), centre * np.sqrt(10.0)
    lo, hi = 10.0 ** np.floor(np.log10(lo)), 10.0 ** np.ceil(np.log10(hi))
    getattr(ax, f"set_{axis}scale")("log")
    getattr(ax, f"set_{axis}lim")(lo, hi)
    ax_obj = getattr(ax, f"{axis}axis")
    ax_obj.set_major_locator(matplotlib.ticker.LogLocator(base=10.0, numticks=12))
    ax_obj.set_minor_formatter(matplotlib.ticker.NullFormatter())


def quantiles(vec: np.ndarray, qs=Q3) -> np.ndarray:
    """Quantiles over the finite entries; all-nan when none are finite."""
    finite = np.asarray(vec, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return np.full(len(qs), np.nan)
    return np.quantile(finite, qs)


# --- mixture sampling (mirrors mc.py) ----------------------------------------

def _draw(rng, family: str, params: dict, m: int) -> np.ndarray:
    if family == "lognormal":
        return rng.lognormal(params["mu"], params["sigma"], m)
    if family == "beta":
        return rng.beta(params["alpha"], params["beta"], m)
    if family == "point":
        return np.full(m, float(params["value"]))
    raise ValueError(f"unknown family {family!r}")


def sample_mixture(rng, fits: list[dict], m: int) -> np.ndarray:
    """Equal-weight mixture over fitted distributions (identical to
    mc.sample_mixture so the rng stream is consumed the same way)."""
    if len(fits) == 1:
        return _draw(rng, fits[0]["family"], fits[0]["params"], m)
    idx = rng.integers(0, len(fits), size=m)
    out = np.empty(m)
    for r, f in enumerate(fits):
        mask = idx == r
        out[mask] = _draw(rng, f["family"], f["params"], int(mask.sum()))
    return out


def complete_fits(fits_by_sid: dict[int, dict[str, list[dict]]]) -> dict[int, dict[str, list[dict]]]:
    return {sid: fits for sid, fits in sorted(fits_by_sid.items())
            if all(name in fits and fits[name] for name in db.PARAM_NAMES)}


def unique_fits(fits: list[dict]) -> list[dict]:
    """Fit rows with distinct elicitation ids, first occurrence kept: the
    rungs of a staged protocol share their group's decision fits, which a
    ladder pools once."""
    seen, out = set(), []
    for f in fits:
        if f["elicitation_id"] not in seen:
            seen.add(f["elicitation_id"])
            out.append(f)
    return out


def draw_metrics(rng, fits: dict[str, list[dict]], n: int) -> dict[str, np.ndarray]:
    """One scenario's EVSI / EVPI / C draw vectors from its pooled fits, the
    rng consumed in PARAM_NAMES order."""
    draws = {name: sample_mixture(rng, fits[name], n) for name in db.PARAM_NAMES}
    evsi, evpi = model.voi(draws["p"], draws["s"], draws["t"], draws["B"], draws["K"])
    return {"EVSI": evsi, "EVPI": evpi, "C": draws["C"]}


# --- 1. level uplift ---------------------------------------------------------

def leveled_groups(con) -> dict[str, tuple[list[tuple[float, int]], int]]:
    """{group: ([(level, sid)] sorted by level then id, number of distinct
    (agent, decision, theta_definition) texts)} over scenarios carrying a
    numeric attributes.level."""
    levels = scenario_levels(con)
    text: dict[str, set] = {}
    rungs: dict[str, list] = {}
    for r in con.execute("SELECT * FROM scenarios ORDER BY id"):
        if r["id"] not in levels:
            continue
        g = r["grp"] or "(no group)"
        text.setdefault(g, set()).add((r["agent"], r["decision"], r["theta_definition"]))
        rungs.setdefault(g, []).append((levels[r["id"]], r["id"]))
    return {g: (sorted(v), len(text[g])) for g, v in sorted(rungs.items())}


def leveled_rungs(con, run) -> tuple[dict[str, list[tuple[float, int]]], dict[str, str]]:
    """(ladders, skipped). ladders = {group: [(level, sid), ...]} over the
    groups whose leveled scenarios share one agent / decision / theta text
    (the consistent_groups gate: a step between two different decisions is
    not a marginal of anything) and hold ONE ranked scenario per level (two
    scenarios on one level would make a 'step' between equals, a marginal of
    nothing), restricted to the scenarios ranked in the run; skipped =
    {group: reason} for every other leveled group."""
    ranked = set(metric_rows(con, run["id"], primary_metric(con, run["id"])))
    ladders, skipped = {}, {}
    for g, (rungs, n_text) in leveled_groups(con).items():
        kept = [(lv, sid) for lv, sid in rungs if sid in ranked]
        per_level: dict[float, list[int]] = {}
        for lv, sid in kept:
            per_level.setdefault(lv, []).append(sid)
        crowded = {lv: sids for lv, sids in per_level.items() if len(sids) > 1}
        if n_text > 1:
            skipped[g] = (f"{len(rungs)} leveled scenarios with {n_text} different agent /"
                          " decision / theta texts: not one ladder, steps would compare"
                          " unrelated decisions")
        elif len(per_level) < 2:
            skipped[g] = f"fewer than two ranked levels ({len(kept)} rung(s) in run {run['id']})"
        elif crowded:
            skipped[g] = "; ".join(
                f"level {level_label(lv)} has {len(sids)} scenarios (ids {', '.join(map(str, sids))})"
                for lv, sids in sorted(crowded.items())) + ": not one ladder, a step needs one" \
                " scenario per level"
        else:
            ladders[g] = kept
    return ladders, skipped


def ladder_draws(con, run, rungs: list[tuple[float, int]]) -> dict | None:
    """Common-random-number draws for one ladder: p, B, K (the decision's
    parameters, level-invariant under the shared-decision gate) are drawn ONCE
    from the pooled fits of every rung; s, t, C (the instrument's) per rung
    from that rung's fits. Draw i is then the same decision state for every
    rung, so EVSI[hi] - EVSI[lo] carries the rung's effect and not the repeat
    noise of an independently re-drawn p, B, K. Fresh rng from the run's seed
    and draw count: these are NOT the stored run's draws. Returns {"shared":
    {p, B, K}, "rungs": {sid: {EVSI, EVPI, C, s, t}}}, or None when a rung
    has no complete valid elicitations under the run's protocol."""
    fits_all = run_fits(con, run)
    sids = [sid for _, sid in rungs]
    if any(sid not in fits_all for sid in sids):
        return None
    rng = np.random.default_rng(run["seed"])
    n = run["n_draws"]
    shared = {name: sample_mixture(rng, unique_fits([f for sid in sids for f in fits_all[sid][name]]), n)
              for name in SHARED_PARAMS}
    per_rung = {}
    for sid in sids:
        own = {name: sample_mixture(rng, fits_all[sid][name], n) for name in RUNG_PARAMS}
        evsi, evpi = model.voi(shared["p"], own["s"], own["t"], shared["B"], shared["K"])
        per_rung[sid] = {"EVSI": evsi, "EVPI": evpi, "C": own["C"], "s": own["s"], "t": own["t"]}
    return {"shared": shared, "rungs": per_rung}


def step_stats(lo: dict, hi: dict) -> dict:
    """Marginals of one step from two rungs' aligned draws: medians of dEVSI
    and dC, the marginal efficiency as the RATIO OF MEDIANS median(dEVSI) /
    median(dC) (nan when median dC is 0), P(dC > 0), P(dEVSI > 0) and
    P(dEVSI > dC). Per-draw ratio quantiles are not reported: with dC
    crossing zero on a fraction of draws they have Cauchy-like tails."""
    d_evsi = hi["EVSI"] - lo["EVSI"]
    d_c = hi["C"] - lo["C"]
    evsi_med, c_med = float(np.median(d_evsi)), float(np.median(d_c))
    return {
        "dEVSI_q50": evsi_med, "dC_q50": c_med,
        "meff": evsi_med / c_med if c_med != 0.0 else float("nan"),
        "p_dc_pos": float(np.mean(d_c > 0.0)),
        "p_gain": float(np.mean(d_evsi > 0.0)), "p_pays": float(np.mean(d_evsi > d_c)),
    }


def level_uplift_analysis(con, run) -> dict:
    """{"rungs": {group: [(level, sid)]}, "draws": {group: ladder_draws},
    "steps": {group: [step dict with lo/hi ids and levels]}, "skipped":
    {group: reason}} over the run's ladders."""
    ladders, skipped = leveled_rungs(con, run)
    out = {"rungs": {}, "draws": {}, "steps": {}, "skipped": skipped}
    for g, rungs in ladders.items():
        draws = ladder_draws(con, run, rungs)
        if draws is None:
            skipped[g] = "a rung has no complete valid elicitations under the run's protocol"
            continue
        steps = []
        for (l0, a), (l1, b) in zip(rungs, rungs[1:], strict=False):
            steps.append({"lo_id": a, "hi_id": b, "lo_level": l0, "hi_level": l1,
                          **step_stats(draws["rungs"][a], draws["rungs"][b])})
        out["rungs"][g], out["draws"][g], out["steps"][g] = rungs, draws, steps
    return out


def level_uplift_stats(con, run, analysis: dict | None = None) -> dict[str, list[dict]]:
    """{group: [step dicts]} (see step_stats) per ladder."""
    return (analysis or level_uplift_analysis(con, run))["steps"]


def fig_level_uplift(con, run, out: Path, analysis: dict | None = None) -> bool:
    analysis = analysis or level_uplift_analysis(con, run)
    stats = analysis["steps"]
    if not stats:
        return False
    groups = list(stats)
    fig, axes = plt.subplots(2, len(groups), figsize=(min(6.2, 3.3 * len(groups)), 4.6),
                             squeeze=False, sharex="col")
    for j, g in enumerate(groups):
        top, bot = axes[0][j], axes[1][j]
        rungs = analysis["rungs"][g]
        draws = analysis["draws"][g]["rungs"]
        levels = np.array([lv for lv, _ in rungs])
        for key, color, off in (("EVSI", ACCENT, -0.07), ("C", CATEGORICAL[1], 0.07)):
            q = np.array([quantiles(draws[sid][key]) for _, sid in rungs])
            floored = q[:, 1] < EVSI_FLOOR
            q = np.maximum(q, EVSI_FLOOR)
            top.errorbar(levels + off, q[:, 1], yerr=[q[:, 1] - q[:, 0], q[:, 2] - q[:, 1]],
                         fmt="none", ecolor=color, elinewidth=0.7, alpha=0.8)
            top.plot(levels[~floored] + off, q[~floored, 1], "o", color=color, ms=4,
                     mec="white", mew=0.4, label=key)
            top.plot(levels[floored] + off, q[floored, 1], "o", mfc="white", mec=color, ms=4)
        top.set_yscale("log")
        top.set_title(g, fontsize=9)
        top.tick_params(labelsize=7)
        if j == 0:
            top.set_ylabel("USD (median, q05–q95)", fontsize=8)
            top.legend(fontsize=6.5, frameon=False, loc="upper left")
        steps = stats[g]
        xs = np.array([(s["lo_level"] + s["hi_level"]) / 2 for s in steps])
        med = np.array([s["meff"] for s in steps])
        ok = np.isfinite(med)
        cheaper = np.array([s["dC_q50"] <= 0.0 for s in steps])
        bot.plot(xs[ok & ~cheaper], med[ok & ~cheaper], "o", color=ACCENT, ms=4.5, mec="white",
                 mew=0.4)
        bot.plot(xs[ok & cheaper], med[ok & cheaper], "o", mfc="white", mec=ACCENT, ms=4.5)
        for x, s in zip(xs, steps, strict=True):
            if np.isfinite(s["meff"]):
                bot.annotate(f"{s['p_pays']:.0%}", (x, s["meff"]), textcoords="offset points",
                             xytext=(0, 4), ha="center", fontsize=5.5, color="#555555")
        bot.axhline(1.0, color="#555555", lw=0.8, ls="--")
        bot.set_yscale("symlog", linthresh=0.1)
        bot.set_xticks(levels)
        bot.set_xticklabels([level_label(lv) for lv in levels])
        bot.set_xlabel("level (steps sit between adjacent rungs)", fontsize=8)
        bot.tick_params(labelsize=7)
        if j == 0:
            bot.set_ylabel(r"median $\Delta$EVSI / median $\Delta C$", fontsize=8)
    fig.suptitle("Value and cost per rung (top); marginal efficiency per step, labelled with"
                 " P($\\Delta$EVSI > $\\Delta C$) (bottom); common-random-number draws, one"
                 " decision per ladder", fontsize=7.5)
    fig.savefig(out / "fig_level_uplift.pdf")
    plt.close(fig)
    return True


def write_level_uplift(con, run, out: Path, analysis: dict | None = None) -> bool:
    stats = level_uplift_stats(con, run, analysis)
    if not stats:
        return False
    rows = []
    for g, steps in stats.items():
        rows.append(r"\multicolumn{8}{@{}l}{\emph{" + esc(g) + "}}")
        for s in steps:
            rows.append(
                f"{level_label(s['lo_level'])}$\\to${level_label(s['hi_level'])} &"
                f" {s['lo_id']}$\\to${s['hi_id']} & {money(s['dEVSI_q50'])} & {money(s['dC_q50'])} &"
                f" {num(s['meff'])} & {pct(s['p_dc_pos'])} & {pct(s['p_gain'])} & {pct(s['p_pays'])}")
    header = (r"step & ids & $\Delta$EVSI & $\Delta C$ & $\Delta$EVSI/$\Delta C$ &"
              r" $P(\Delta C>0)$ & $P(\Delta\mathrm{EVSI}>0)$ & $P(\Delta\mathrm{EVSI}>\Delta C)$")
    _write(out, "level_uplift.tex", tabular(
        "@{}llrrrrrr@{}", header, rows,
        "adjacent-rung marginals within one decision (ladders: groups whose rungs share the"
        f" agent, decision and theta text) over {run['n_draws']} common-random-number draws"
        f" seeded like run {run['id']} (p, B, K drawn once per ladder from the pooled rung"
        " fits, s, t, C per rung; not the stored run's draws); medians of dEVSI and dC,"
        " dEVSI/dC is the ratio of those medians"))
    return True


# --- 2. within-group consistency ---------------------------------------------

def consistent_groups(con) -> dict[str, list[tuple[float, int]]]:
    """Groups whose leveled scenarios all share the same agent, decision and
    theta_definition text: {group: [(level, sid)] sorted}. Needs >= 2 levels."""
    return {g: rungs for g, (rungs, n_text) in leveled_groups(con).items()
            if n_text == 1 and len({lv for lv, _ in rungs}) >= 2}


def elicited_points(con, protocol_id: int, sids: list[int],
                    members: list[str] | None = None) -> dict[str, dict[int, list]]:
    """{param: {sid: [(member label, p50), ...]}} over the valid elicitations
    that feed each scenario (of the `members` subset when given; under a
    staged protocol a scenario's p, B, K points are its group's decision
    rows, db.elicited_points)."""
    out: dict[str, dict[int, list]] = {n: {} for n in db.PARAM_NAMES}
    for name in db.PARAM_NAMES:
        for sid in sids:
            pts = db.elicited_points(con, protocol_id, sid, name, members)
            if pts:
                out[name][sid] = pts
    return out


def dispersion(name: str, pooled: list[float]) -> float | None:
    """Coefficient of variation (probabilities) or log10 range (USD) of the
    pooled p50 across levels; None with fewer than two levels."""
    arr = np.asarray(pooled, dtype=float)
    if arr.size < 2:
        return None
    if arr.max() == arr.min():   # level-invariant by construction (a staged protocol): exactly 0
        return 0.0
    if FAMILY_BY_PARAM[name] == "lognormal":
        return float(np.log10(arr.max() / arr.min()))
    mean = float(arr.mean())
    return float(arr.std() / mean) if mean > 0 else None


def cv_ratio(disp: dict[str, float]) -> float | None:
    """CV(p) / mean(CV(s), CV(t)): how much the decision-level prior drifts
    across rungs relative to the instrument-level probabilities. 0 when p is
    flat (a staged protocol elicits it once per group, so 0 by design); None
    when s and t are flat too (0 / 0)."""
    denom = (disp["s"] + disp["t"]) / 2.0
    if denom <= 0.0:
        return None if disp["p"] <= 0.0 else float("inf")
    return disp["p"] / denom


def consistency_analysis(con, run) -> tuple[dict[str, dict], dict[str, str]]:
    """(stats, skipped). stats, per consistent group whose every level holds
    a valid elicitation under the run's protocol: {"levels", "rungs",
    "pooled": {param: [pooled p50 per level]}, "dispersion": {param: cv |
    log-range}, "flat": bool} where flat means p is flatter than s and t, and
    B, K flatter than C. A group with an unelicited level is skipped with its
    reason (the dispersion would silently span fewer levels than the table
    says), as is one whose dispersion is undefined."""
    out, skipped = {}, {}
    for g, rungs in consistent_groups(con).items():
        sids = [sid for _, sid in rungs]
        pts = elicited_points(con, run["protocol_id"], sids, db.run_member_labels(run))
        levels = sorted({lv for lv, _ in rungs})
        pooled: dict[str, list[float]] = {name: [] for name in db.PARAM_NAMES}
        empty = []
        for lv in levels:
            level_sids = [sid for l2, sid in rungs if l2 == lv]
            for name in db.PARAM_NAMES:
                vals = [v for sid in level_sids for _, v in pts[name].get(sid, [])]
                if vals:
                    pooled[name].append(float(np.median(vals)))
            if not any(pts[name].get(sid) for sid in level_sids for name in db.PARAM_NAMES):
                empty.append(lv)
        if empty:
            skipped[g] = (f"level(s) {', '.join(level_label(lv) for lv in empty)} of {len(levels)}"
                          f" have no valid elicitation under the run's protocol")
            continue
        disp = {name: dispersion(name, pooled[name]) for name in db.PARAM_NAMES}
        undefined = [n for n in db.PARAM_NAMES if disp[n] is None]
        if undefined:
            skipped[g] = f"dispersion undefined for {undefined} (pooled p50 of 0 or one level)"
            continue
        flat = (disp["p"] < min(disp["s"], disp["t"])) and (max(disp["B"], disp["K"]) < disp["C"])
        out[g] = {"levels": levels, "rungs": rungs, "pooled": pooled, "dispersion": disp, "flat": flat,
                  "cv_ratio": cv_ratio(disp)}
    return out, skipped


def run_is_staged(con, run) -> bool:
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    return db.protocol_stages(prot) is not None


def consistency_stats(con, run) -> dict[str, dict]:
    return consistency_analysis(con, run)[0]


def fig_within_group_consistency(con, run, out: Path) -> bool:
    """Same groups as the table (consistency_analysis), so a group skipped
    there is not plotted with a missing level either."""
    groups = {g: st["rungs"] for g, st in consistency_stats(con, run).items()}
    if not groups:
        return False
    members = [db.member_label(m) for m in run_members(con, run)]
    multi = len(members) > 1
    colors = group_colors(members) if multi else dict.fromkeys(members, ACCENT)
    rng = np.random.default_rng(0)
    fig, axes = plt.subplots(len(groups), len(db.PARAM_NAMES),
                             figsize=(6.2, 1.55 * len(groups) + 0.7), squeeze=False)
    for i, (g, rungs) in enumerate(groups.items()):
        sids = [sid for _, sid in rungs]
        level_of = {sid: lv for lv, sid in rungs}
        pts = elicited_points(con, run["protocol_id"], sids, db.run_member_labels(run))
        levels = sorted({lv for lv, _ in rungs})
        for j, name in enumerate(db.PARAM_NAMES):
            ax = axes[i][j]
            usd = FAMILY_BY_PARAM[name] == "lognormal"
            pooled = []
            for lv in levels:
                vals = [v for sid in sids if level_of[sid] == lv for _, v in pts[name].get(sid, [])]
                pooled.append(float(np.median(vals)) if vals else np.nan)
            for sid in sids:
                for member, v in pts[name].get(sid, []):
                    ax.plot(level_of[sid] + rng.uniform(-0.18, 0.18), v, ".", ms=3.5, alpha=0.6,
                            color=colors.get(member, "#7f7f7f"), mec="none")
            ax.plot(levels, pooled, "-", color="#333333", lw=1.0)
            if usd:
                log_axis(ax, "y", [v for sid in sids for _, v in pts[name].get(sid, [])])
            else:
                ax.set_ylim(-0.02, 1.02)
            ax.set_xticks(levels)
            ax.set_xticklabels([level_label(lv) for lv in levels])
            ax.tick_params(labelsize=6)
            if i == 0:
                ax.set_title(f"${name}$" + (" (USD)" if usd else ""), fontsize=8)
            if j == 0:
                ax.set_ylabel(g, fontsize=7)
            if i == len(groups) - 1:
                ax.set_xlabel("level", fontsize=7)
    if multi:
        handles = [plt.Line2D([], [], marker="o", ls="", color=colors[m], label=m) for m in members]
        fig.legend(handles=handles, loc="outside lower center", ncol=min(len(members), 3),
                   fontsize=6.5, frameon=False)
    fig.suptitle("Elicited p50 by level, groups sharing one decision (line: pooled median)",
                 fontsize=8)
    fig.savefig(out / "fig_within_group_consistency.pdf")
    plt.close(fig)
    return True


def write_consistency(con, run, out: Path) -> bool:
    stats = consistency_stats(con, run)
    if not stats:
        return False
    rows = []
    for g, st in stats.items():
        d = st["dispersion"]
        cells = " & ".join(num(d[n], "{:.2f}") for n in db.PARAM_NAMES)
        verdict = "yes" if st["flat"] else "no"
        rows.append(f"{esc(g)} & {len(st['levels'])} & {cells} & {num(st['cv_ratio'], '{:.2f}')} & {verdict}")
    header = (r"group & levels & CV $p$ & CV $s$ & CV $t$ & $\log_{10}$ range $B$ &"
              r" $\log_{10}$ range $K$ & $\log_{10}$ range $C$ &"
              r" $\frac{\mathrm{CV}(p)}{\overline{\mathrm{CV}(s,t)}}$ & $p,B,K$ flatter")
    staged = run_is_staged(con, run)
    _write(out, "consistency.tex", tabular(
        "@{}lrrrrrrrrl@{}", header, rows,
        "dispersion of the pooled p50 across levels: coefficient of variation for probabilities,"
        " log10(max/min) for USD; CV(p) / mean(CV(s), CV(t)) is the drift of the decision-level"
        " prior relative to the instrument-level probabilities"
        + (" (0 by design here: this staged protocol elicits p, B, K once per group)" if staged
           else " (a staged protocol, p, B, K elicited once per group, makes it 0 by design)")
        + "; last column: CV(p) < min(CV(s), CV(t)) and max(range(B), range(K)) < range(C)"))
    return True


# --- 3. domain map ------------------------------------------------------------

def scenario_domains(con) -> dict[int, str]:
    out = {}
    for r in con.execute("SELECT * FROM scenarios"):
        d = db.scenario_attributes(r).get("risk_domain")
        if d:
            out[r["id"]] = str(d)
    return out


def percentile_rank(ref, x: float) -> float:
    """Percentile of x within ref (ties count half), 0-100."""
    ref = np.asarray(ref, dtype=float)
    return float(100.0 * (np.sum(ref < x) + 0.5 * np.sum(ref == x)) / ref.size)


def iso_efficiency_lines(ax, xlim, ylim) -> None:
    for k in range(-3, 4):
        ax.plot(xlim, 10.0**k * xlim, ls="--", lw=0.7, color="#c9c9c9", zorder=0)
        x_lab = min(xlim[1] * 0.55, ylim[1] * 0.35 / 10.0**k)
        y_lab = 10.0**k * x_lab
        if xlim[0] * 1.5 < x_lab and ylim[0] * 3 < y_lab < ylim[1] * 0.7:
            p0 = ax.transData.transform((x_lab, y_lab))
            p1 = ax.transData.transform((x_lab * 2, y_lab * 2))
            angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
            ax.text(x_lab, y_lab * 1.25, f"eff $= 10^{{{k}}}$", fontsize=6, color="#8a8a8a",
                    rotation=angle, rotation_mode="anchor")


def pooled_p50(con, protocol_id: int, sid: int, name: str,
               members: list[str] | None = None) -> float | None:
    """Median of the p50 across the valid elicitations of one scenario under a
    protocol (tables.write_catalog's pooled elicited median), every member or
    the `members` subset; None without any."""
    p50s = db.elicited_p50s(con, protocol_id, sid, name, members=members)
    return float(np.median(p50s)) if p50s else None


def pooled_c(con, run, sid: int) -> float | None:
    """Median elicited p50 of C (fallback for pre-v2 runs without a stored C row)."""
    return pooled_p50(con, run["protocol_id"], sid, "C", db.run_member_labels(run))


def fig_domain_map(con, run, out: Path) -> bool:
    domains = scenario_domains(con)
    order = ranked_ids(con, run["id"])
    if not any(s in domains for s in order):
        return False
    evsi_name = evsi_metric(con, run["id"])
    evsi = metric_rows(con, run["id"], evsi_name)
    cost = metric_rows(con, run["id"], "C")
    groups = scenario_groups(con)
    xs = np.array([cost[s]["q50"] if s in cost else pooled_c(con, run, s) for s in order], dtype=float)
    y50 = np.maximum(np.array([evsi[s]["q50"] or 0.0 for s in order]), EVSI_FLOOR)
    lo = np.maximum(np.array([evsi[s]["q05"] or 0.0 for s in order]), EVSI_FLOOR)
    hi = np.maximum(np.array([evsi[s]["q95"] or 0.0 for s in order]), EVSI_FLOOR)
    dom_of = [domains.get(s, "(none)") for s in order]
    grp_of = [groups.get(s) or "(no group)" for s in order]
    dom_names = sorted(set(dom_of))
    grp_names = sorted(set(grp_of))
    colors = group_colors(dom_names)
    marker = {g: MARKERS[i % len(MARKERS)] for i, g in enumerate(grp_names)}

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    ax.vlines(xs, lo, hi, color=INTERVAL, lw=0.6, alpha=0.75, zorder=1)
    for d in dom_names:
        for g in grp_names:
            mask = np.array([(a == d) and (b == g) for a, b in zip(dom_of, grp_of, strict=True)])
            if mask.any():
                ax.plot(xs[mask], y50[mask], marker[g], ls="", color=colors[d], ms=5.5,
                        mec="white", mew=0.5, zorder=3)
    for i, sid in enumerate(order):
        ax.annotate(str(sid), (xs[i], y50[i]), textcoords="offset points",
                    xytext=(4, 3) if i % 2 == 0 else (-4, -8),
                    ha="left" if i % 2 == 0 else "right", fontsize=6, color="#333333", zorder=4)
    ax.set_xscale("log")
    ax.set_yscale("log")
    xlim = np.array([xs.min() / 3, xs.max() * 3])
    ylim = np.array([EVSI_FLOOR / 2, max(hi.max(), EVSI_FLOOR) * 10])
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    iso_efficiency_lines(ax, xlim, ylim)
    handles = [plt.Line2D([], [], marker="o", ls="", color=colors[d], label=d) for d in dom_names]
    handles += [plt.Line2D([], [], marker=marker[g], ls="", color="#555555", label=g)
                for g in grp_names]
    ax.legend(handles=handles, fontsize=6.5, loc="lower right", frameon=False,
              title="colour: risk domain; marker: group", title_fontsize=6.5)
    ax.set_xlabel("median C (run mixture, USD)")
    ax.set_ylabel(f"median {evsi_name} (USD per evaluation)")
    ax.set_title(f"Median {evsi_name} vs median cost by risk domain and group (bars: q05–q95)")
    fig.savefig(out / "fig_domain_map.pdf")
    plt.close(fig)
    return True


def domain_summary(con, run) -> dict:
    """{"by_domain": {d: (n, med, min, max)}, "by_group": {...},
    "reference": label | None, "ranks": [(sid, grp, eff, percentile)]}."""
    domains = scenario_domains(con)
    order = ranked_ids(con, run["id"])
    if not any(s in domains for s in order):
        return {}
    eff = metric_rows(con, run["id"], primary_metric(con, run["id"]))
    med = {s: float(eff[s]["q50"] or 0.0) for s in order}
    grp = scenario_groups(con)
    groups = {s: grp.get(s) or "(no group)" for s in order}

    def block(key_of):
        out = {}
        for s in order:
            out.setdefault(key_of(s), []).append(med[s])
        return {k: (len(v), float(np.median(v)), min(v), max(v)) for k, v in sorted(out.items())}

    by_domain = block(lambda s: domains.get(s, "(none)"))
    by_group = block(lambda s: groups[s])
    reference = REFERENCE_GROUP if REFERENCE_GROUP in by_group else None
    ranks = []
    for s in order:
        if groups[s] == reference:
            continue
        ref = [med[o] for o in order if (groups[o] == reference if reference
                                          else groups[o] != groups[s])]
        if ref:
            ranks.append((s, groups[s], med[s], percentile_rank(ref, med[s])))
    return {"by_domain": by_domain, "by_group": by_group, "reference": reference, "ranks": ranks}


def write_domain_summary(con, run, out: Path) -> bool:
    ds = domain_summary(con, run)
    if not ds:
        return False
    rows = [r"\multicolumn{5}{@{}l}{\emph{by risk domain}}"]
    for key, (n, med, lo, hi) in ds["by_domain"].items():
        rows.append(f"{esc(key)} & {n} & {num(med)} & {num(lo)} & {num(hi)}")
    rows.append(r"\midrule")
    rows.append(r"\multicolumn{5}{@{}l}{\emph{by group}}")
    for key, (n, med, lo, hi) in ds["by_group"].items():
        rows.append(f"{esc(key)} & {n} & {num(med)} & {num(lo)} & {num(hi)}")
    summary = tabular("@{}lrrrr@{}", r" & $n$ & median eff & min & max", rows,
                      f"median efficiency (EVSI/C) per risk domain and group, run {run['id']}")
    ref = ds["reference"] or "the other groups"
    ttl = titles(con)
    rank_rows = [f"{sid} & {esc(ttl[sid][:48])} & {esc(g)} & {num(e)} & {p:.0f}"
                 for sid, g, e, p in ds["ranks"]]
    ranks = tabular("@{}rp{5.2cm}lrr@{}",
                    r"id & scenario & group & median eff & percentile within " + esc(ref),
                    rank_rows or [r"\multicolumn{5}{@{}l}{(no scenario outside the reference group)}"],
                    "percentile rank of each non-reference scenario's median efficiency")
    _write(out, "domain_summary.tex", summary + "\\par\\medskip\n" + ranks)
    return True


# --- 4. member agreement -----------------------------------------------------

def member_fits(fits_all: dict, member: dict) -> dict[int, dict[str, list[dict]]]:
    """One member's valid fits only, restricted to scenarios where that member
    carries every parameter."""
    sub = {}
    for sid, fits in fits_all.items():
        mine = {name: [f for f in rows if f["provider"] == member["provider"]
                       and f["model"] == member["model"]] for name, rows in fits.items()}
        if all(mine.get(name) for name in db.PARAM_NAMES):
            sub[sid] = mine
    return dict(sorted(sub.items()))


def member_pooled_p50(con, protocol_id: int, member: dict, name: str) -> dict[int, float]:
    out = {}
    for (sid,) in con.execute(
            "SELECT DISTINCT scenario_id FROM elicitations WHERE protocol_id=? AND valid=1"
            " AND provider=? AND model=?", (protocol_id, member["provider"], member["model"])):
        p50s = db.elicited_p50s(con, protocol_id, sid, name, member["provider"], member["model"])
        if p50s:
            out[sid] = float(np.median(p50s))
    return out


def member_rankings(con, run) -> dict:
    """Per-member median efficiency from that member's fits alone. The mixture
    is re-drawn locally with the run's seed and n_draws per member (a fresh
    rng per member, scenarios in sorted-id order): these draws are NOT the
    stored run, which pools all members. Returns {"members": [labels],
    "medians": {label: {sid: eff_q50}}, "pooled": {sid: eff_q50 (stored)},
    "matrix": (M+1)x(M+1) Spearman (members then pooled), "top": {label: ids}}."""
    members = run_members(con, run)
    fits_all = run_fits(con, run)
    labels = [db.member_label(m) for m in members]
    medians: dict[str, dict[int, float]] = {}
    for m, label in zip(members, labels, strict=True):
        rng = np.random.default_rng(run["seed"])
        meds = {}
        for sid, fits in member_fits(fits_all, m).items():
            d = draw_metrics(rng, fits, run["n_draws"])
            meds[sid] = float(np.median(d["EVSI"] / d["C"]))
        medians[label] = meds
    pooled = {s: float(r["q50"] or 0.0)
              for s, r in metric_rows(con, run["id"], primary_metric(con, run["id"])).items()}
    series = [medians[label] for label in labels] + [pooled]
    n = len(series)
    matrix = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            shared = sorted(set(series[i]) & set(series[j]))
            if i == j:
                matrix[i, j] = 1.0 if shared else np.nan
            elif len(shared) >= 3:
                rho = spearman([series[i][s] for s in shared], [series[j][s] for s in shared])
                matrix[i, j] = np.nan if rho is None else rho
    top = {label: sorted(medians[label], key=lambda s: (-medians[label][s], s))[:TOP_N_MEMBER]
           for label in labels}
    top["pooled"] = sorted(pooled, key=lambda s: (-pooled[s], s))[:TOP_N_MEMBER]
    return {"members": labels, "medians": medians, "pooled": pooled, "matrix": matrix, "top": top}


def fig_member_agreement(con, run, out: Path) -> bool:
    members = run_members(con, run)
    if len(members) < 2:
        return False
    labels = [db.member_label(m) for m in members]
    pairs = list(combinations(range(len(members)), 2))
    pooled = {(i, name): member_pooled_p50(con, run["protocol_id"], m, name)
              for i, m in enumerate(members) for name in db.PARAM_NAMES}
    fig, axes = plt.subplots(len(pairs), len(db.PARAM_NAMES),
                             figsize=(6.2, 1.25 * len(pairs) + 0.6), squeeze=False)
    for r, (i, j) in enumerate(pairs):
        for c, name in enumerate(db.PARAM_NAMES):
            ax = axes[r][c]
            a, b = pooled[(i, name)], pooled[(j, name)]
            shared = sorted(set(a) & set(b))
            x = np.array([a[s] for s in shared])
            y = np.array([b[s] for s in shared])
            usd = FAMILY_BY_PARAM[name] == "lognormal"
            ax.plot(x, y, "o", color=ACCENT, ms=3, mec="white", mew=0.3, alpha=0.85)
            if usd and shared:
                both = np.concatenate([x, y])
                log_axis(ax, "x", both)
                log_axis(ax, "y", both)
                lim = ax.get_xlim()
            else:
                lim = (0.0, 1.0)
                ax.set_xlim(*lim)
                ax.set_ylim(*lim)
            ax.plot(lim, lim, ls="--", lw=0.6, color="#c9c9c9", zorder=0)
            rho = spearman(x, y) if len(shared) >= 3 else None
            ax.text(0.04, 0.9, f"$\\rho$ = {'--' if rho is None else f'{rho:.2f}'} (n={len(shared)})",
                    transform=ax.transAxes, fontsize=5.5, color="#333333")
            ax.tick_params(labelsize=5)
            if r == 0:
                ax.set_title(f"${name}$" + (" (USD)" if usd else ""), fontsize=8)
            if c == 0:
                ax.set_ylabel(labels[j], fontsize=6)
            if r == len(pairs) - 1:
                ax.set_xlabel(labels[i], fontsize=6)
    fig.suptitle("Cross-member agreement of per-scenario pooled p50 (Spearman over shared scenarios)",
                 fontsize=8)
    fig.savefig(out / "fig_member_agreement.pdf")
    plt.close(fig)
    return True


def write_member_agreement(con, run, out: Path) -> bool:
    if len(run_members(con, run)) < 2:
        return False
    mr = member_rankings(con, run)
    names = mr["members"] + ["pooled (run)"]
    keys = mr["members"] + ["pooled"]
    rows = []
    for i, name in enumerate(names):
        cells = " & ".join("--" if not np.isfinite(v) else f"{v:.2f}" for v in mr["matrix"][i])
        rows.append(f"{esc(name)} & {cells} & " + ", ".join(str(s) for s in mr["top"][keys[i]]))
    header = " & " + " & ".join(esc(n) for n in names) + " & top-5 ids"
    _write(out, "member_agreement.tex", tabular(
        "@{}l" + "r" * len(names) + "l@{}", header, rows,
        "Spearman of median efficiency between per-member rankings (each member's fits pooled"
        f" alone, mixture re-drawn locally with seed {run['seed']} and {run['n_draws']} draws;"
        f" not the stored run) and the pooled run {run['id']}, over shared scenarios"))
    return True


# --- 5. simplicity ------------------------------------------------------------

def global_abs_rho(con, run_id: int, sids: list[int],
                   ) -> tuple[dict[str, float | None], dict[str, int]]:
    """({param: mean |rho|}, {param: scenarios averaged}) over the given
    scenarios. A scenario whose stored rho is NULL for a parameter (its
    efficiency is constant over the draws, e.g. EVSI = 0 on every draw) is
    left out of both, so the count can fall short of len(sids)."""
    vals: dict[str, list[float]] = {n: [] for n in db.PARAM_NAMES}
    if sids:
        marks = ",".join("?" * len(sids))
        for r in con.execute(
                f"SELECT param, spearman FROM sensitivities WHERE run_id=? AND spearman IS NOT NULL"
                f" AND scenario_id IN ({marks})", (run_id, *sids)):
            if r["param"] in vals:
                vals[r["param"]].append(abs(r["spearman"]))
    return ({n: (float(np.mean(v)) if v else None) for n, v in vals.items()},
            {n: len(v) for n, v in vals.items()})


def n_label(counts: dict[str, int]) -> str:
    """The scenarios averaged: one number when every parameter has the same,
    else 'min..max'."""
    lo, hi = min(counts.values()), max(counts.values())
    return str(lo) if lo == hi else f"{lo}..{hi}"


def simplicity_stats(con, run) -> dict | None:
    """Does the EVPI/C ranking reproduce the EVSI/C ranking? Both rankings
    are medians of per-draw ratios stored by the run ('efficiency' and
    'evpi_efficiency'), so the comparison carries no estimator difference
    (a ratio of medians differs from a median of ratios by up to 3x on real
    data). None for a run stored before the evpi_efficiency metric existed."""
    order = ranked_ids(con, run["id"])
    evsi = metric_rows(con, run["id"], "EVSI")
    evpi_rows = metric_rows(con, run["id"], "evpi_efficiency")
    eff = metric_rows(con, run["id"], "efficiency")
    head = metric_rows(con, run["id"], "headroom")
    if set(evpi_rows) != set(order):
        return None
    eff_med = {s: float(eff[s]["q50"] or 0.0) for s in order}
    evpi_eff = {s: float(evpi_rows[s]["q50"] or 0.0) for s in order}
    positive = [s for s in order if (evsi[s]["q50"] or 0.0) > 0.0]

    def rho_over(sids):
        if len(sids) < 3:
            return None
        return spearman([eff_med[s] for s in sids], [evpi_eff[s] for s in sids])

    k = min(TOP_N_OVERLAP, len(order))
    top_simple = sorted(order, key=lambda s: (-evpi_eff[s], s))[:k]
    hv = [head[s]["q50"] for s in order if s in head and head[s]["q50"] is not None]
    hq = quantiles(np.array(hv, dtype=float), (0.25, 0.5, 0.75)) if hv else np.full(3, np.nan)
    top_q = order[:max(1, len(order) // 4)]
    global_all, global_all_n = global_abs_rho(con, run["id"], order)
    global_top, global_top_n = global_abs_rho(con, run["id"], top_q)
    return {
        "n": len(order), "n_pos": len(positive),
        "rho_all": rho_over(order), "rho_pos": rho_over(positive),
        "top_k": k, "top_overlap": len(set(order[:k]) & set(top_simple)),
        "headroom_q25": float(hq[0]), "headroom_med": float(hq[1]), "headroom_q75": float(hq[2]),
        "global_all": global_all, "global_all_n": global_all_n,
        "global_top": global_top, "global_top_n": global_top_n, "n_top": len(top_q),
    }


def write_simplicity(con, run, out: Path) -> bool:
    st = simplicity_stats(con, run)
    if st is None:
        return False
    r_all, r_pos = st["rho_all"], st["rho_pos"]
    rows = [
        r"Spearman $\rho$(EVSI/$C$, EVPI/$C$), all scenarios & "
        f"{num(r_all, '{:.2f}')} ($n$={st['n']})",
        r"Spearman $\rho$(EVSI/$C$, EVPI/$C$), EVSI $>$ 0 & "
        f"{num(r_pos, '{:.2f}')} ($n$={st['n_pos']})",
        f"top-{st['top_k']} overlap & {st['top_overlap']} / {st['top_k']}",
        "headroom EVSI/EVPI, median [IQR] & "
        f"{num(st['headroom_med'], '{:.2f}')} [{num(st['headroom_q25'], '{:.2f}')},"
        f" {num(st['headroom_q75'], '{:.2f}')}]",
    ]
    ranking = tabular("@{}lr@{}", "statistic & value", rows,
                      f"is the simpler EVPI/C ranking enough? run {run['id']}; both rankings are"
                      " medians of the per-draw ratio (stored metrics efficiency and evpi_efficiency)")
    header = " & " + " & ".join(f"${n}$" for n in db.PARAM_NAMES)
    srows = [
        f"mean $|\\rho|$, all scenarios ($n$={n_label(st['global_all_n'])}) & "
        + " & ".join(num(st["global_all"][n], "{:.2f}") for n in db.PARAM_NAMES),
        f"mean $|\\rho|$, top quartile ($n$={n_label(st['global_top_n'])}) & "
        + " & ".join(num(st["global_top"][n], "{:.2f}") for n in db.PARAM_NAMES),
    ]
    sens = tabular("@{}l" + "r" * len(db.PARAM_NAMES) + "@{}", header, srows,
                   "global sensitivity: mean |Spearman rho| of each parameter vs efficiency over"
                   f" the scenarios with a defined rho (n, of {st['n']} ranked and {st['n_top']}"
                   " in the top quartile; a scenario whose efficiency is constant over the draws,"
                   " e.g. EVSI = 0 on every draw, has none)")
    _write(out, "simplicity.tex", ranking + "\\par\\medskip\n" + sens)
    macros = {
        "voiSimpRhoAll": num(r_all, "{:.2f}"),
        "voiSimpRhoPos": num(r_pos, "{:.2f}"),
        "voiSimpN": st["n"],
        "voiSimpNPos": st["n_pos"],
        "voiSimpTopK": st["top_k"],
        "voiSimpTopOverlap": st["top_overlap"],
        "voiHeadroomMed": num(st["headroom_med"], "{:.2f}"),
        "voiHeadroomQlo": num(st["headroom_q25"], "{:.2f}"),
        "voiHeadroomQhi": num(st["headroom_q75"], "{:.2f}"),
    }
    for n in db.PARAM_NAMES:
        macros[f"voiGlobalAll{PARAM_MACRO[n]}"] = num(st["global_all"][n], "{:.2f}")
    write_macros(out, macros)
    return True


# --- 6. protocol noise at matched k --------------------------------------------

def latest_run_per_protocol(con) -> dict[str, int]:
    """{label: run id}: the latest run of every protocol, and of every member
    subset scored under it (label 'p003[opus+sonnet]'), that the v2 analyses
    accept (db.run_predates_v2 is None, the gate select_run applies); a
    protocol whose runs all predate the v2 model is left out rather than
    correlated against v2 runs."""
    out = {}
    for p in con.execute("SELECT * FROM protocols ORDER BY id"):
        seen = set()
        for r in con.execute("SELECT * FROM runs WHERE protocol_id=? ORDER BY id DESC", (p["id"],)):
            key = r["members_json"]
            if key in seen or db.run_predates_v2(con, r) is not None:
                continue
            seen.add(key)
            out[db.run_label(p["name"], db.run_member_labels(r))] = r["id"]
    return dict(sorted(out.items(), key=lambda kv: kv[1]))


def member_repeat_counts(con, protocol_id: int, member: dict) -> dict[int, int]:
    """{scenario_id: valid repeats} one member holds under a protocol: the
    repeats actually pooled, which `elicit --k` can push past the protocol's
    nominal k_repeats (the business p001 was filled from 3 to 5) and an
    invalid slot can pull below it."""
    return {r[0]: r[1] for r in con.execute(
        "SELECT scenario_id, COUNT(*) FROM elicitations WHERE protocol_id=? AND valid=1"
        " AND provider=? AND model=? GROUP BY scenario_id",
        (protocol_id, member["provider"], member["model"]))}


def member_k_used(con, protocol_id: int, member: dict) -> int:
    """Largest valid repeat count one member holds for any scenario."""
    return max(member_repeat_counts(con, protocol_id, member).values(), default=0)


def member_noise(con, protocol_id: int, member: dict, first: int | None) -> tuple[dict, int]:
    """({param: median cross-repeat spread}, n scenarios with >= 2 repeats)
    for one member, optionally truncated to the first `first` valid repeats
    of each scenario (in repeat_ix order)."""
    med, n = {}, 0
    label = [db.member_label(member)]
    for name in db.PARAM_NAMES:
        # the scenarios carrying the parameter for this member (group
        # representatives for a decision-stage parameter of a staged protocol)
        spreads = [sp for sid in db.param_scenario_ids(con, protocol_id, name, label)
                   if (sp := db.elicited_spread(con, protocol_id, sid, name, member["provider"],
                                                member["model"], first)) is not None]
        med[name] = float(np.median(spreads)) if spreads else None
        n = max(n, len(spreads))
    return med, n


def count_label(counts: list[int]) -> str:
    """The count pooled per scenario: one number when every scenario pools
    the same, else 'min..max'."""
    lo, hi = min(counts), max(counts)
    return str(lo) if lo == hi else f"{lo}..{hi}"


def noise_rows(con) -> list[tuple[str, dict, str, int | None]]:
    """(protocol name, member, label, first-n cap) for the noise table: every
    member with at least two valid repeats of some scenario gets a 'first n'
    row (n = min(valid repeats, MATCHED_K) per scenario, the count the row
    pools, not an index cap: a scenario whose repeat 1 ended invalid still
    pools 0, 2, 3) and, when any scenario holds more than MATCHED_K valid
    repeats, an 'all n' row over every valid repeat; labels carry the counts
    actually pooled per scenario (min..max where scenarios differ), never
    the nominal k."""
    rows = []
    for p in con.execute("SELECT * FROM protocols ORDER BY id"):
        if db.protocol_model_kind(p) != db.BINARY_KIND:   # the table's rows are the binary parameters
            continue
        for m in db.protocol_members(p):
            multi = [c for c in member_repeat_counts(con, p["id"], m).values() if c >= 2]
            if not multi:
                continue
            rows.append((p["name"], m, f"first {count_label([min(c, MATCHED_K) for c in multi])}",
                         MATCHED_K))
            if max(multi) > MATCHED_K:
                rows.append((p["name"], m, f"all {count_label(multi)}", None))
    return rows


def rank_corr_between_runs(con, run_a: int, run_b: int) -> tuple[float | None, int]:
    """Each run on its own primary metric ('efficiency' or 'eff_step')."""
    med = {rid: {r["scenario_id"]: r["q50"] for r in con.execute(
        "SELECT scenario_id, q50 FROM results WHERE run_id=? AND metric=?",
        (rid, primary_metric(con, rid)))} for rid in (run_a, run_b)}
    shared = sorted(set(med[run_a]) & set(med[run_b]))
    if len(shared) < 3:
        return None, len(shared)
    return spearman([med[run_a][s] for s in shared], [med[run_b][s] for s in shared]), len(shared)


def write_protocol_noise_matched(con, out: Path) -> bool:
    runs = latest_run_per_protocol(con)
    if not runs:
        return False
    rows = []
    for pname, m, label, cap in noise_rows(con):
        med, n = member_noise(con, db.protocol_by_name(con, pname)["id"], m, cap)
        cells = " & ".join(num(med[name], "{:.2f}") for name in db.PARAM_NAMES)
        rows.append(f"{esc(pname)} & {esc(db.member_label(m))} & {label} & {cells} & {n}")
    if not rows:
        rows.append(r"\multicolumn{" + str(4 + len(db.PARAM_NAMES))
                    + r"}{@{}l}{(no member with two or more valid repeats)}")
    header = ("protocol & member & repeats & " + " & ".join(f"${n}$" for n in db.PARAM_NAMES)
              + " & $n$")
    noise = tabular("@{}lll" + "r" * len(db.PARAM_NAMES) + "r@{}", header, rows,
                    "median over scenarios of the cross-repeat p50 spread (max - min) / pooled p50,"
                    f" per member with repeats, over the first {MATCHED_K} valid repeats (matched k)"
                    " and, where the member holds more on any scenario, over all of them (the"
                    " repeats column is the count pooled per scenario, min..max where scenarios"
                    " differ)")
    names = list(runs)
    crows = []
    for a in names:
        cells = []
        for b in names:
            if a == b:
                cells.append("--")
            else:
                rho, n = rank_corr_between_runs(con, runs[a], runs[b])
                cells.append("n/a" if rho is None else f"{rho:.2f} ({n})")
        crows.append(esc(a) + " & " + " & ".join(cells))
    compare = tabular("@{}l" + "r" * len(names) + "@{}", " & " + " & ".join(esc(n) for n in names),
                      crows, "Spearman of median efficiency between the latest v2 runs of each"
                      " protocol pair over shared scenarios (n); a protocol whose runs all predate"
                      " the v2 model is left out")
    _write(out, "protocol_noise_matched.tex", noise + "\\par\\medskip\n" + compare)
    return True


# --- 7. plug-in vs Monte Carlo ------------------------------------------------

def gate_regime(p: float, s: float, t: float, B: float, K: float) -> str:
    """Where the decision sits at one parameter point: 'in gate' when the
    threshold pi* = K / (B + K) lies strictly between the two posteriors
    pi1 = P(theta=1 | x=1) and pi0 = P(theta=1 | x=0), so the signal can flip
    the action and EVSI > 0; 'always respond' when both posteriors are at or
    above pi*; 'never respond' when both are at or below it. A signal value
    of probability zero leaves the belief at the prior p."""
    P1 = p * s + (1.0 - p) * (1.0 - t)
    P0 = 1.0 - P1
    pi1 = p * s / P1 if P1 > 0.0 else p
    pi0 = p * (1.0 - s) / P0 if P0 > 0.0 else p
    pi_star = K / (B + K)
    lo, hi = min(pi0, pi1), max(pi0, pi1)
    if pi_star <= lo:
        return "always respond"
    if pi_star >= hi:
        return "never respond"
    return "in gate"


def plugin_point(con, run, sid: int) -> dict | None:
    """model.voi at the pooled elicited medians of one scenario: {"medians":
    {p, s, t, B, K, C}, "EVSI", "EVPI", "eff", "regime"}; None when a
    parameter has no valid elicitation under the run's protocol."""
    labels = db.run_member_labels(run)
    med = {name: pooled_p50(con, run["protocol_id"], sid, name, labels) for name in db.PARAM_NAMES}
    if any(v is None for v in med.values()):
        return None
    evsi, evpi = model.voi(med["p"], med["s"], med["t"], med["B"], med["K"])
    return {"medians": med, "EVSI": float(evsi), "EVPI": float(evpi),
            "eff": float(evsi) / med["C"],
            "regime": gate_regime(med["p"], med["s"], med["t"], med["B"], med["K"])}


def replay_run(con, run) -> tuple[dict[int, dict[str, float]] | None, str | None]:
    """The stored run's draws, re-drawn from the DB alone (seed, n_draws and
    fits are persisted; one rng consumed in scenario-id, PARAM_NAMES order as
    mc.iter_scenario_draws does) and verified per scenario against the stored
    efficiency quantiles and P(EVSI > C) within REPLAY_RTOL, as
    mc.replay_efficiency does. Only the two scalars the plug-in table needs
    are kept per scenario, never the draw arrays: ({sid: {"mc_mean": mean
    efficiency, "p_gate": P(EVSI > 0)}}, None), or (None, reason) when the
    valid-elicitation set changed since the run (a scenario added or dropped,
    repeats added under the same protocol)."""
    fits = run_fits(con, run)
    stored = metric_rows(con, run["id"], "efficiency")
    if set(fits) != set(stored):
        return None, (f"elicitations changed since run {run['id']}: {len(fits)} scenarios hold"
                      f" complete valid elicitations now vs {len(stored)} ranked")
    rng = np.random.default_rng(run["seed"])
    replay = {}
    for sid, f in fits.items():
        d = draw_metrics(rng, f, run["n_draws"])
        eff = d["EVSI"] / d["C"]
        if not np.all(np.isfinite(eff)):
            return None, f"replay of run {run['id']} gives a non-finite efficiency draw on scenario {sid}"
        got = dict(zip(RESULT_COLUMNS, (float(v) for v in np.quantile(eff, SUMMARY_QS)), strict=True))
        got["p_positive"] = float(np.mean(d["EVSI"] > d["C"]))
        for col, want in ((c, stored[sid][c]) for c in (*RESULT_COLUMNS, "p_positive")):
            if want is None or abs(got[col] - want) > REPLAY_RTOL * max(1.0, abs(want)):
                return None, (f"replay of run {run['id']} mismatches on scenario {sid}: efficiency"
                              f" {col} {got[col]} vs stored {want}: valid elicitations changed since"
                              " the run (e.g. repeats added under the same protocol)")
        replay[sid] = {"mc_mean": float(np.mean(eff)), "p_gate": float(np.mean(d["EVSI"] > 0.0))}
    return replay, None


def plugin_analysis(con, run) -> tuple[dict | None, str | None]:
    """(stats, None) or (None, reason). stats: {"rows": [per scenario in the
    run's ranking order: sid, rank, medians, EVSI, EVPI, eff (plug-in),
    regime, mc_median, mc_mean, p_positive, p_gate], "rho_plugin_median",
    "rho_plugin_mean", "rho_median_mean" (Spearman over the efficiencies,
    None with fewer than 3 scenarios or a constant ranking), "n_gate"
    (scenarios in gate at the medians), "n_zero_median" (stored median EVSI
    exactly 0), "top_k", "top_overlap" (top-k ids by plug-in efficiency shared
    with the run's top-k)}. mc_mean and p_gate come from the replayed draws
    (replay_run), mc_median and p_positive from the stored results."""
    replay, why = replay_run(con, run)
    if replay is None:
        return None, why
    order = ranked_ids(con, run["id"])
    eff = metric_rows(con, run["id"], "efficiency")
    evsi = metric_rows(con, run["id"], "EVSI")
    rows = []
    for rank, sid in enumerate(order, 1):
        # a verified replay means every ranked scenario has a valid elicitation
        # of every parameter, so plugin_point is never None here
        rows.append({"sid": sid, "rank": rank, **plugin_point(con, run, sid),
                     "mc_median": float(eff[sid]["q50"] or 0.0),
                     "p_positive": float(eff[sid]["p_positive"] or 0.0), **replay[sid]})
    series = {key: [r[key] for r in rows] for key in ("eff", "mc_median", "mc_mean")}

    def rho(a, b):
        return spearman(series[a], series[b]) if len(rows) >= 3 else None

    k = min(TOP_N_PLUGIN, len(rows))
    plug = {r["sid"]: r["eff"] for r in rows}
    top_plugin = sorted(plug, key=lambda s: (-plug[s], s))[:k]
    return {
        "rows": rows,
        "rho_plugin_median": rho("eff", "mc_median"),
        "rho_plugin_mean": rho("eff", "mc_mean"),
        "rho_median_mean": rho("mc_median", "mc_mean"),
        "n_gate": sum(1 for r in rows if r["regime"] == "in gate"),
        "n_zero_median": sum(1 for s in order if float(evsi[s]["q50"] or 0.0) == 0.0),
        "top_k": k, "top_overlap": len(set(order[:k]) & set(top_plugin)),
    }, None


def plugin_stats(con, run) -> dict | None:
    return plugin_analysis(con, run)[0]


def average_ranks(values) -> np.ndarray:
    """Rank 1 = largest; ties share their average rank (what Spearman uses)."""
    return rankdata(-np.asarray(values, dtype=float), method="average")


def fig_plugin(con, run, out: Path, st: dict | None = None) -> bool:
    st = st or plugin_stats(con, run)
    if st is None:
        return False
    rows = st["rows"]
    n = len(rows)
    ranks = {"plugin": average_ranks([r["eff"] for r in rows]),
             "mc_median": average_ranks([r["mc_median"] for r in rows]),
             "mc_mean": average_ranks([r["mc_mean"] for r in rows])}
    rhos = {("plugin", "mc_median"): st["rho_plugin_median"],
            ("plugin", "mc_mean"): st["rho_plugin_mean"],
            ("mc_median", "mc_mean"): st["rho_median_mean"]}
    fig, axes = plt.subplots(1, len(PLUGIN_PANELS), figsize=(6.2, 2.4))
    for ax, (kx, ky) in zip(axes, PLUGIN_PANELS, strict=True):
        x, y = ranks[kx], ranks[ky]
        ax.plot([0.5, n + 0.5], [0.5, n + 0.5], ls="--", lw=0.6, color="#c9c9c9", zorder=0)
        ax.plot(x, y, "o", color=ACCENT, ms=4, mec="white", mew=0.4, alpha=0.85, zorder=3)
        if n <= PLUGIN_ANNOTATE_MAX:
            at: dict[tuple[float, float], list[int]] = {}
            for r, xi, yi in zip(rows, x, y, strict=True):
                at.setdefault((float(xi), float(yi)), []).append(r["sid"])
            for (xi, yi), sids in at.items():
                parts = [", ".join(map(str, sids[i:i + 4])) for i in range(0, len(sids), 4)]
                ax.annotate("\n".join(parts), (xi, yi), textcoords="offset points", xytext=(3, 3),
                            fontsize=5, color="#333333", zorder=4)
        rho = rhos[(kx, ky)]
        ax.set_title(f"Spearman $\\rho$ = {'--' if rho is None else f'{rho:.2f}'} (n={n})",
                     fontsize=7.5)
        ax.set_xlim(n + 0.7, 0.3)
        ax.set_ylim(n + 0.7, 0.3)
        ax.set_xlabel(PLUGIN_AXIS[kx], fontsize=8)
        ax.set_ylabel(PLUGIN_AXIS[ky], fontsize=8)
        ax.tick_params(labelsize=7)
    fig.suptitle("Efficiency rank: plug-in at the pooled medians vs MC median vs MC mean"
                 " (rank 1 top right; ties averaged)", fontsize=7.5)
    fig.savefig(out / "fig_plugin.pdf")
    plt.close(fig)
    return True


def write_plugin(con, run, out: Path, st: dict | None = None) -> bool:
    st = st or plugin_stats(con, run)
    if st is None:
        return False
    rows = []
    for r in st["rows"]:
        rows.append(
            f"{r['rank']} & {r['sid']} & {money(r['medians']['C'])} & {money(r['EVSI'])} &"
            f" {money(r['EVPI'])} & {num(r['eff'])} & {REGIME_CELL[r['regime']]} &"
            f" {num(r['mc_median'])} & {num(r['mc_mean'])} & {pct(r['p_positive'])} & {pct(r['p_gate'])}")
    header = (r"rank & id & $C$ & EVSI & EVPI & eff & regime & $\mathrm{eff}_{q50}$ &"
              r" $\overline{\mathrm{eff}}$ & $P_+$ & $P_\mathrm{gate}$")
    table = longtable(
        "@{}rrrrrrlrrrr@{}", header, rows,
        r"Plug-in vs Monte Carlo per scenario, in the order of the run's median efficiency (rank)."
        r" EVSI, EVPI and eff $=$ EVSI$/C$ are \texttt{model.voi} at the pooled elicited medians"
        r" of $p$, $s$, $t$, $B$, $K$ (the catalog's values) and $C$ (median of the p50 across"
        r" valid elicitations, printed here because the catalog's $C$ is the run's mixture"
        r" median). Regime at the medians from $\pi^* = K/(B+K)$ against the posteriors"
        r" $\pi_1$, $\pi_0$: gate ($\pi^*$ strictly between them, EVSI $>$ 0), always / never"
        r" respond (both posteriors at or above / below $\pi^*$, EVSI $=$ 0)."
        r" $\mathrm{eff}_{q50}$: the run's stored median efficiency; $\overline{\mathrm{eff}}$:"
        f" the mean over the {run['n_draws']} draws of run {run['id']}, replayed from the DB and"
        r" verified against the stored quantiles; $P_+ = P(\mathrm{EVSI} > C)$ stored by the run;"
        r" $P_\mathrm{gate} = P(\mathrm{EVSI} > 0)$ over the replayed draws. USD in $B$, $K$, $C$,"
        r" EVSI, EVPI.", "tab:plugin")
    summary = tabular("@{}lr@{}", "statistic & value", [
        r"Spearman $\rho$(plug-in eff, MC median eff) & " + num(st["rho_plugin_median"], "{:.2f}"),
        r"Spearman $\rho$(plug-in eff, MC mean eff) & " + num(st["rho_plugin_mean"], "{:.2f}"),
        r"Spearman $\rho$(MC median eff, MC mean eff) & " + num(st["rho_median_mean"], "{:.2f}"),
        f"scenarios in gate at the medians & {st['n_gate']} / {len(st['rows'])}",
        f"scenarios with MC median EVSI $= 0$ & {st['n_zero_median']} / {len(st['rows'])}",
        f"top-{st['top_k']} overlap, plug-in vs MC median & {st['top_overlap']} / {st['top_k']}",
    ], "plug-in vs Monte Carlo rankings over the efficiencies of the table above")
    _write(out, "plugin.tex", table + "\\par\\medskip\n" + summary)
    write_macros(out, {
        "voiPluginRhoMedian": num(st["rho_plugin_median"], "{:.2f}"),
        "voiPluginRhoMean": num(st["rho_plugin_mean"], "{:.2f}"),
        "voiMedianMeanRho": num(st["rho_median_mean"], "{:.2f}"),
        "voiPluginInGate": st["n_gate"],
        "voiMcZeroMedian": st["n_zero_median"],
        "voiPluginTopK": st["top_k"],
        "voiPluginTopOverlap": st["top_overlap"],
    }, merge=True)
    return True


# --- driver -------------------------------------------------------------------

# analyses defined on the binary parameters (p, B, K shared per ladder; p50
# dispersion of p, s, t, B, K, C; per-member re-draws through model.voi; the
# EVPI/C ranking; the plug-in point through model.voi): a Gaussian run skips
# them with a printed reason
BINARY_ONLY = ("level_uplift", "consistency", "member_agreement", "simplicity", "plugin")


def skip_reasons(con, run, uplift: dict, plugin: tuple | None = None) -> dict[str, str]:
    """Why an analysis (or one of its ladders) does not apply to this run.
    plugin: the (stats, reason) pair of plugin_analysis, computed here when
    not passed (the replay behind it is the costliest step of the module)."""
    if run_kind(con, run["id"]) == db.GAUSSIAN_KIND:
        reasons = {name: "defined on the binary parameters; the run is a Gaussian-state protocol"
                   for name in BINARY_ONLY}
        if not scenario_domains(con):
            reasons["domain_map"] = "no scenario carries attributes.risk_domain"
        return reasons
    reasons = {f"level_uplift ({g})": why for g, why in uplift["skipped"].items()}
    if not uplift["steps"]:
        reasons["level_uplift"] = "no ladder (a group of >= 2 ranked levels sharing one decision text)"
    stats, cskipped = consistency_analysis(con, run)
    reasons.update({f"consistency ({g})": why for g, why in cskipped.items()})
    if not stats:
        reasons["consistency"] = ("no group of leveled scenarios sharing one decision text"
                                  if not consistent_groups(con) else "every such group was skipped")
    if not scenario_domains(con):
        reasons["domain_map"] = "no scenario carries attributes.risk_domain"
    if len(run_members(con, run)) < 2:
        reasons["member_agreement"] = "the run has one member"
    if simplicity_stats(con, run) is None:
        reasons["simplicity"] = (f"run {run['id']} stores no evpi_efficiency metric (made before"
                                 " it existed): re-run voi_rank.mc")
    _, why = plugin or plugin_analysis(con, run)
    if why:
        reasons["plugin"] = why
    return reasons


def make_all(con, run, out: Path) -> tuple[list[str], list[str]]:
    """Write every analysis that applies. Returns (written file names, skipped
    analysis names); a skipped analysis has its stale outputs removed and its
    reason printed (as is every ladder the level uplift leaves out)."""
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(STYLE)
    binary = run_kind(con, run["id"]) == db.BINARY_KIND
    uplift = level_uplift_analysis(con, run) if binary else {"steps": {}, "skipped": {}}
    plugin = (plugin_analysis(con, run) if binary
              else (None, "defined on the binary parameters; the run is a Gaussian-state protocol"))
    for what, why in skip_reasons(con, run, uplift, plugin).items():
        print(f"{what}: skipped: {why}")
    mr_needed = binary and len(run_members(con, run)) > 1
    # simplicity before plugin: both write MACROS_FILE, the first afresh, the
    # second merging its macros in (so a skipped simplicity leaves the plugin
    # macros alone and a skipped plugin never removes the simplicity ones)
    plan = [
        ("level_uplift", lambda: binary and fig_level_uplift(con, run, out, uplift)
         and write_level_uplift(con, run, out, uplift)),
        ("consistency", lambda: binary and fig_within_group_consistency(con, run, out)
         and write_consistency(con, run, out)),
        ("domain_map", lambda: fig_domain_map(con, run, out) and write_domain_summary(con, run, out)),
        ("member_agreement", lambda: mr_needed and fig_member_agreement(con, run, out)
         and write_member_agreement(con, run, out)),
        ("simplicity", lambda: binary and write_simplicity(con, run, out)),
        ("plugin", lambda: binary and plugin[0] is not None
         and fig_plugin(con, run, out, plugin[0]) and write_plugin(con, run, out, plugin[0])),
        ("protocol_noise_matched", lambda: write_protocol_noise_matched(con, out)),
    ]
    written, skipped = [], []
    for name, make in plan:
        if make():
            written += [f for f in OUTPUTS[name] if (out / f).exists() and f not in written]
        else:
            _unlink(out, [f for f in OUTPUTS[name] if f not in written])
            skipped.append(name)
    return written, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    add_run_args(ap)
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    run = select_run(con, args.run, args.protocol, db.parse_member_labels(args.members))
    written, skipped = make_all(con, run, study.generated_dir)
    for name in written:
        print(f"wrote {study.generated_dir / name}")
    if skipped:
        print("skipped (inputs absent): " + ", ".join(skipped))


if __name__ == "__main__":
    main()
