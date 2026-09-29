"""Eval-study analyses beyond figures.py / tables.py, reading only from a
study's voi.db. Outputs land in <study>/report/generated/ (generated/TAG/
with --tag TAG, the macros then named \\voiTAG...; study.Study.tagged):

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
   draws (fresh rng from the run's seed and draw count). Per step the table
   adds three more marginals: the MEAN-based ones (means of dEVSI and dC over
   the same draws and their ratio), the PLUG-IN ones (differences of the
   per-rung plug-in values: model.voi at the ladder's pooled medians of p, B,
   K and the rung's medians of s, t, C, and the rung's median C) and the
   FENCE ones (differences of the per-rung fence value EVSI* = Lambda p (1 -
   p) (s + t - 1) at the same medians, over the plug-in dC), and for the
   plug-in marginal the q05-q95 of dEVSI / dC and P(dEVSI > dC) under the
   bootstrap over elicitations (item 9; a staged ladder's rungs share one
   decision resample per replicate; a dagger where dC takes each sign in at
   least 5% of the replicates with dC != 0). Three footnotesize tabulars:
   the CRN medians and probabilities, the CRN means, the plug-in (with the
   bootstrap) and fence marginals. The figure's bottom panel shows the
   plug-in (bar: its bootstrap q05-q95) and fence marginal efficiencies per
   step, with the CRN median ratio and P(dEVSI > dC) as a label.
1b. fig_level_fence.pdf: per group of leveled scenarios, EVSI* (fence), EVSI
   (plug-in) and C at each scenario's pooled medians against its level.
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
   run, whose mixture pools all members) with a Spearman matrix and top-5 ids
   against the stored run (labelled 'run', 'run/equal' when equal-member).
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
7. plugin.tex + plugin_mc.tex + fig_plugin.pdf + macros in macros_extra.tex:
   the plug-in summary (plugin.tex, a footnotesize longtable) with its
   bootstrap intervals (item 9) and the plug-in EVPI with the Monte Carlo
   summary (plugin_mc.tex, a second longtable in the same row order), like
   catalog.tex. Per scenario (in the run's median efficiency order): EVSI,
   EVPI and efficiency from model.voi at the pooled elicited medians of p,
   s, t, B, K, C (median of the p50 across valid elicitations, as
   tables.write_catalog defines them for p, s, t, B, K, whose values the
   catalog already lists and this table does not repeat; for C too, NOT the
   catalog's mixture median, so C is printed here), the gate regime at the medians (in gate / always
   respond / never respond, from the threshold pi* = K / (B + K) against the
   posteriors pi1, pi0), the run's median and MEAN efficiency (the mean over
   the run's draws, replayed from the DB and verified against the stored
   quantiles), P(EVSI > C) and P(EVSI > 0) over the draws (P_gate, not the
   bootstrap's P_boot(gate), which resamples elicitations). The figure
   compares the three rankings pairwise (rank scatter, Spearman annotated).
   The elicited stakes vary several-fold across repeats, so the mixture can
   close the gate in more than half the draws (median EVSI 0) where the
   medians sit inside it; this table shows that side by side. The fence
   value EVSI* = (B + K) p (1 - p) (s + t - 1) at the same medians (chapter,
   "The buyer on the fence": the maximum of EVSI over the threshold at fixed
   stakes), eff* = EVSI* / C and the ratio EVSI / EVSI* (0 when EVSI = 0)
   stand next to them; \voiFenceRhoPlugin is the Spearman of eff* against
   the plug-in eff over the scenarios with EVSI > 0 and \voiFenceTopOverlap
   the top-k overlap of the two rankings.
8. fig_plugin_map.pdf: the headline map at the pooled medians, plug-in
   EVSI against the pooled-median C (log-log), coloured by group, shaped
   by attributes.risk_domain when present; scenarios outside the gate at
   the y floor (open), the fence value EVSI* on a thin stem above each
   point (decision value against fence value), iso-efficiency diagonals,
   and the bootstrap q05-q95 of the plug-in EVSI (vertical) and of C
   (horizontal) as light bars. Needs no replay. Binary runs only.
9. plugin_ranks.tex + the \voiBoot* macros: the bootstrap over elicitations
   (bootstrap_draws). One replicate resamples every scenario's valid
   elicitations of the run's members with replacement within each member
   (each member keeps its count), recomputes the pooled median of every
   parameter (pooled_p50's rule) and the plug-in EVSI, EVPI, eff, EVSI*,
   eff* and regime at them; a staged protocol's decision stage is resampled
   once per group and replicate and read by every scenario of the group.
   N_BOOT = 2000 replicates (--boot), seed run seed + BOOT_SEED_OFFSET, one
   generator per unit (unit_rng). plugin.tex gains the q05-q95 of eff and
   eff* and P_boot(gate); plugin_ranks.tex gives per scenario the point,
   median and q05-q95 of its replicate rank by plug-in eff and by fence
   eff* and P(rank <= 3); \voiBootN, \voiBootTopOneId,
   \voiBootTopOneStable (share of replicates in which the point top-1 by
   plug-in eff stays top-1), \voiBootRhoEff and \voiBootRhoFence (median
   over replicates of the Spearman between the replicate and the point
   ranking). The point of every replicate statistic is plugin_point
   exactly. Needs no replay.

Usage: python -m voi_rank.analysis.extra --study PATH [--protocol p001] [--run ID]
       [--members claude_cli:sonnet,claude_cli:opus] [--weights equal-member] [--tag NAME] [--boot N]
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

Helpers duplicated from figures.py / tables.py (style constants, run
selection, LaTeX escaping) are copied here on purpose; the mixture sampler
is mc.sample_mixture itself, so the weighting rule of a run (mc --weights)
lives in one place and every re-draw here consumes the rng as mc does.
--weights selects the run by its mixture weighting as --members does by
its subset; the ladder draws and the replay honour the run's weighting, the
plug-in point and the bootstrap (medians of the elicited p50s) do not
depend on it.
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

from voi_rank import db, mc, model  # noqa: E402
from voi_rank.analysis.tables import money, plain  # noqa: E402  (one formatter for both modules)
from voi_rank.fit import FAMILY_BY_PARAM  # noqa: E402
from voi_rank.sensitivity import spearman  # noqa: E402
from voi_rank.study import (  # noqa: E402
    MACRO_PREFIX,
    Study,
    add_study_arg,
    add_tag_arg,
    newcommands,
    tex_label,
)

# --- style (mirrors figures.py) --------------------------------------------

ACCENT = "#0072B2"
INTERVAL = "#9aa5b1"
BOOT_BAR = "#d3d9df"          # the bootstrap bars of the plug-in map: light, behind the stems
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
# fig_level_uplift: x offset of the plug-in (left) and fence (right) marginals around a step's midpoint
STEP_OFFSET = 0.08
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
    "level_fence": ("fig_level_fence.pdf",),
    "consistency": ("fig_within_group_consistency.pdf", "consistency.tex"),
    "domain_map": ("fig_domain_map.pdf", "domain_summary.tex"),
    "member_agreement": ("fig_member_agreement.pdf", "member_agreement.tex"),
    "simplicity": ("simplicity.tex", "macros_extra.tex"),
    "plugin": ("fig_plugin.pdf", "plugin.tex", "plugin_mc.tex", "macros_extra.tex"),
    "plugin_map": ("fig_plugin_map.pdf",),
    "plugin_ranks": ("plugin_ranks.tex", "macros_extra.tex"),
    "protocol_noise_matched": ("protocol_noise_matched.tex",),
}
MACROS_FILE = "macros_extra.tex"


# --- LaTeX helpers (mirror tables.py; money and plain are tables.py's) ------

def esc(text) -> str:
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in str(text))


def num(v, fmt: str = "{:.3g}") -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "--"
    return fmt.format(v + 0.0 if v == 0 else v)   # never '-0'


def pct(v) -> str:
    return "--" if v is None or not np.isfinite(v) else f"{100.0 * v:.0f}\\%"


# footnotesize with a 2pt tabcolsep (4pt between columns), in a group: a table too wide for
# the CoRL text width otherwise (plugin.tex with real-width cells needs the 2pt)
SMALL_OPEN, SMALL_CLOSE = r"\begingroup\footnotesize\setlength{\tabcolsep}{2pt}", r"\endgroup"


def tabular(colspec: str, header: str, rows: list[str], caption: str | None = None,
            small: bool = False) -> str:
    """A booktabs tabular fragment (rows already joined with &, no \\\\);
    small sets it in SMALL_OPEN ... SMALL_CLOSE, as longtable does."""
    lines = [SMALL_OPEN] if small else []
    lines += [r"\begin{tabular}{" + colspec + "}", r"\toprule", header + r"\\", r"\midrule"]
    lines += [r if r.startswith(r"\midrule") else r + r"\\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}"] + ([SMALL_CLOSE] if small else [])
    text = "\n".join(lines) + "\n"
    return (f"% {caption}\n" + text) if caption else text


def longtable(colspec: str, header: str, rows: list[str], caption: str, label: str,
              small: bool = False) -> str:
    """A booktabs longtable fragment with the head and foot of
    tables.write_catalog (rows already joined with &, no \\\\); the caption is
    part of the fragment, so the report inputs it outside any float. small
    sets it (caption included) in SMALL_OPEN ... SMALL_CLOSE."""
    lines = [SMALL_OPEN] if small else []
    lines += [r"\begin{longtable}{" + colspec + "}",
             r"\caption{" + caption + r"}\label{" + label + r"}\\",
             r"\toprule", header + r"\\", r"\midrule\endfirsthead",
             r"\toprule " + header + r"\\\midrule\endhead", r"\bottomrule\endfoot"]
    lines += [r + r"\\" for r in rows]
    lines.append(r"\end{longtable}")
    if small:
        lines.append(SMALL_CLOSE)
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


def write_macros(out: Path, macros: dict, merge: bool = False, prefix: str = MACRO_PREFIX) -> Path:
    """\\newcommand lines in MACROS_FILE, each voi<Name> key written as
    <prefix><Name> (study.newcommands). merge=True keeps the other analyses'
    macros already in the file and replaces those with the same name, so the
    file is never left with a duplicate \\newcommand (a LaTeX error)."""
    path = out / MACROS_FILE
    new = newcommands(macros, prefix)
    keep = []
    if merge and path.exists():
        names = {line.split("}", 1)[0] + "}" for line in new}
        keep = [line for line in path.read_text().splitlines()
                if line.strip() and not any(line.startswith(n) for n in names)]
    lines = keep + new
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
    ap.add_argument("--weights", choices=db.WEIGHT_CHOICES, default=db.WEIGHTS_POOLED,
                    help="use the latest run with this mixture weighting (default: pooled)")


def select_run(con, run_id: int | None, protocol: str, members: list[str] | None = None,
               weights: str | None = None):
    """As figures.select_run: a v1 run (no data_hash, or sensitivities for
    the retired parameter e) is refused."""
    run = (db.get_run(con, run_id) if run_id is not None
           else db.latest_run(con, protocol, members, weights))
    prot = con.execute("SELECT name FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    name = prot["name"] if prot else "unknown"
    reason = db.run_predates_v2(con, run)
    if reason:
        raise RuntimeError(f"run {run['id']} (protocol {name}) predates the v2 model: {reason};"
                           f" run `python -m voi_rank.mc --protocol {name}` first")
    labels = db.run_member_labels(run)
    print(f"run {run['id']} (protocol {name}" + (f", members {', '.join(labels)}" if labels else "")
          + (f", weights {db.run_weights(run)}" if db.run_weights(run) else "") + ")")
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


# --- mixture sampling (mc's sampler) -------------------------------------------

sample_mixture = mc.sample_mixture


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


def draw_metrics(rng, fits: dict[str, list[dict]], n: int,
                 weights: str | None = None) -> dict[str, np.ndarray]:
    """One scenario's EVSI / EVPI / C draw vectors from its pooled fits
    (mixture weighting `weights`, None = pooled), the rng consumed in
    PARAM_NAMES order."""
    draws = {name: sample_mixture(rng, fits[name], n, weights) for name in db.PARAM_NAMES}
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
    n, weights = run["n_draws"], db.run_weights(run)
    shared = {name: sample_mixture(rng, unique_fits([f for sid in sids for f in fits_all[sid][name]]), n,
                                   weights)
              for name in SHARED_PARAMS}
    per_rung = {}
    for sid in sids:
        own = {name: sample_mixture(rng, fits_all[sid][name], n, weights) for name in RUNG_PARAMS}
        evsi, evpi = model.voi(shared["p"], own["s"], own["t"], shared["B"], shared["K"])
        per_rung[sid] = {"EVSI": evsi, "EVPI": evpi, "C": own["C"], "s": own["s"], "t": own["t"]}
    return {"shared": shared, "rungs": per_rung}


def _ratio(num: float, den: float) -> float:
    return num / den if den != 0.0 else float("nan")


def step_stats(lo: dict, hi: dict) -> dict:
    """Marginals of one step from two rungs' aligned draws: medians of dEVSI
    and dC, the marginal efficiency as the RATIO OF MEDIANS median(dEVSI) /
    median(dC) (nan when median dC is 0), P(dC > 0), P(dEVSI > 0) and
    P(dEVSI > dC), plus the MEAN-based marginals (mean dEVSI, mean dC and
    their ratio over the same draws). Per-draw ratio quantiles are not
    reported: with dC crossing zero on a fraction of draws they have
    Cauchy-like tails."""
    d_evsi = hi["EVSI"] - lo["EVSI"]
    d_c = hi["C"] - lo["C"]
    evsi_med, c_med = float(np.median(d_evsi)), float(np.median(d_c))
    evsi_mean, c_mean = float(np.mean(d_evsi)), float(np.mean(d_c))
    return {
        "dEVSI_q50": evsi_med, "dC_q50": c_med, "meff": _ratio(evsi_med, c_med),
        "p_dc_pos": float(np.mean(d_c > 0.0)),
        "p_gain": float(np.mean(d_evsi > 0.0)), "p_pays": float(np.mean(d_evsi > d_c)),
        "dEVSI_mean": evsi_mean, "dC_mean": c_mean, "meff_mean": _ratio(evsi_mean, c_mean),
    }


def plugin_step_stats(lo: dict, hi: dict) -> dict:
    """The plug-in and fence marginals of one step from two rungs' plug-in
    points (ladder_plugin): differences of the per-rung EVSI, EVSI* and C at
    the medians, the plug-in ratio dEVSI / dC and the fence ratio dEVSI* /
    dC (nan when dC is 0)."""
    d_evsi, d_star, d_c = hi["EVSI"] - lo["EVSI"], hi["EVSI_star"] - lo["EVSI_star"], hi["C"] - lo["C"]
    return {"dEVSI_plug": d_evsi, "dC_plug": d_c, "meff_plug": _ratio(d_evsi, d_c),
            "dEVSI_star": d_star, "meff_star": _ratio(d_star, d_c)}


def ladder_plugin(con, run, rungs: list[tuple[float, int]]) -> dict[int, dict] | None:
    """Per rung, the plug-in point of the ladder: p, B, K at the pooled
    elicited medians over EVERY rung's elicitations, each elicitation once
    (the decision is shared, as the CRN draws share them; under a staged
    protocol the rungs of one group read the same decision rows, taken once
    per group, as ladder_draws takes each fit once and ladder_bootstrap each
    unit once, so a ladder spanning two groups weighs their rows alike), s,
    t, C at the rung's own medians: {sid: {"medians", "EVSI", "EVPI",
    "EVSI_star", "C"}}; None when a rung lacks a parameter."""
    labels = db.run_member_labels(run)
    pid = run["protocol_id"]
    shared = {}
    for name in SHARED_PARAMS:
        sources: dict[tuple, int] = {}
        for _, sid in rungs:
            sources.setdefault(tuple(db.elicited_source_ids(con, pid, sid, name)), sid)
        p50s = [v for sid in sources.values() for v in db.elicited_p50s(con, pid, sid, name, members=labels)]
        if not p50s:
            return None
        shared[name] = float(np.median(p50s))
    out = {}
    for _, sid in rungs:
        own = {name: pooled_p50(con, pid, sid, name, labels) for name in RUNG_PARAMS}
        if any(v is None for v in own.values()):
            return None
        med = {**shared, **own}
        evsi, evpi = model.voi(med["p"], med["s"], med["t"], med["B"], med["K"])
        star = model.voi_fence(med["p"], med["s"], med["t"], med["B"], med["K"])
        out[sid] = {"medians": med, "EVSI": float(evsi), "EVPI": float(evpi),
                    "EVSI_star": float(star), "C": med["C"]}
    return out


def level_uplift_analysis(con, run, boot: dict | None = None) -> dict:
    """{"rungs": {group: [(level, sid)]}, "draws": {group: ladder_draws},
    "plugin": {group: ladder_plugin}, "boot": {group: ladder_bootstrap},
    "steps": {group: [step dict with lo/hi ids and levels]}, "skipped":
    {group: reason}} over the run's ladders. boot: the bootstrap_draws of
    the run (drawn here when not passed); each step carries the bootstrap
    interval of its plug-in marginal (boot_step_stats)."""
    ladders, skipped = leveled_rungs(con, run)
    out = {"rungs": {}, "draws": {}, "plugin": {}, "boot": {}, "steps": {}, "skipped": skipped}
    if ladders and boot is None:
        boot = bootstrap_draws(con, run)
    if boot is not None:
        out["n_boot"] = boot["n_boot"]
    for g, rungs in ladders.items():
        draws = ladder_draws(con, run, rungs)
        plug = ladder_plugin(con, run, rungs)
        if draws is None or plug is None:
            skipped[g] = "a rung has no complete valid elicitations under the run's protocol"
            continue
        lb = ladder_bootstrap(boot, rungs)
        steps = []
        for (l0, a), (l1, b) in zip(rungs, rungs[1:], strict=False):
            steps.append({"lo_id": a, "hi_id": b, "lo_level": l0, "hi_level": l1,
                          **step_stats(draws["rungs"][a], draws["rungs"][b]),
                          **plugin_step_stats(plug[a], plug[b]),
                          **(boot_step_stats(lb[a], lb[b]) if lb is not None else BOOT_STEP_NAN)})
        out["rungs"][g], out["draws"][g], out["plugin"][g], out["steps"][g] = rungs, draws, plug, steps
        out["boot"][g] = lb
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
        # plug-in (differences of the per-rung values at the medians) with its
        # bootstrap q05-q95 as a bar, fence (dEVSI* over the plug-in dC) and
        # the CRN ratio of medians, side by side; a step whose dC is not
        # positive gets an open marker
        series = (("meff_plug", "dC_plug", "o", ACCENT, "plug-in (bar: bootstrap q05-q95)", -STEP_OFFSET),
                  ("meff_star", "dC_plug", "^", CATEGORICAL[2], "fence EVSI*", STEP_OFFSET),
                  ("meff", "dC_q50", "s", "#7f7f7f", "CRN median ratio", 0.0))
        lo = np.array([s["meff_plug_q05"] for s in steps])
        hi = np.array([s["meff_plug_q95"] for s in steps])
        ok = np.isfinite(lo) & np.isfinite(hi)
        bot.vlines(xs[ok] - STEP_OFFSET, lo[ok], hi[ok], color=ACCENT, lw=0.8, alpha=0.45, zorder=1,
                   gid="boot_meff")
        for key, dc_key, marker, color, label, off in series:
            vals = np.array([s[key] for s in steps])
            ok = np.isfinite(vals)
            cheaper = np.array([s[dc_key] <= 0.0 for s in steps])
            bot.plot(xs[ok & ~cheaper] + off, vals[ok & ~cheaper], marker, color=color, ms=4.5,
                     mec="white", mew=0.4, label=label if j == 0 else None)
            bot.plot(xs[ok & cheaper] + off, vals[ok & cheaper], marker, mfc="white", mec=color, ms=4.5)
        for x, s in zip(xs, steps, strict=True):
            y = s["meff_plug"] if np.isfinite(s["meff_plug"]) else s["meff"]
            if np.isfinite(y):
                bot.annotate(f"{s['p_pays']:.0%}", (x - STEP_OFFSET, y), textcoords="offset points",
                             xytext=(0, 5), ha="center", fontsize=5.5, color="#555555")
        bot.axhline(1.0, color="#555555", lw=0.8, ls="--")
        bot.set_yscale("symlog", linthresh=0.1)
        bot.set_xticks(levels)
        bot.set_xticklabels([level_label(lv) for lv in levels])
        bot.set_xlabel("level (steps sit between adjacent rungs)", fontsize=8)
        bot.tick_params(labelsize=7)
        if j == 0:
            bot.set_ylabel(r"marginal efficiency $\Delta$EVSI / $\Delta C$", fontsize=8)
    handles, labels_ = axes[1][0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc="outside lower center", ncol=3, fontsize=6.5, frameon=False)
    fig.suptitle("Top: value and cost per rung (CRN draws: median, q05-q95). Bottom: marginal efficiency"
                 " per step:\nplug-in dEVSI/dC of the per-rung values at the pooled medians (bar: its"
                 " bootstrap q05-q95),\nfence dEVSI*/dC with EVSI* = (B+K) p (1-p) (s+t-1), and the CRN"
                 " ratio of medians;\nlabels: CRN P(dEVSI > dC); open markers: dC <= 0", fontsize=7)
    fig.savefig(out / "fig_level_uplift.pdf")
    plt.close(fig)
    return True


def write_level_uplift(con, run, out: Path, analysis: dict | None = None) -> bool:
    """level_uplift.tex: three tabulars over the same steps, each in
    footnotesize (tabular small) within the CoRL text width (the compile test
    prints real-width values): the CRN medians and probabilities, the CRN
    means, and the plug-in marginals with their bootstrap interval next to
    the fence marginals (the last two at the ladder-pooled p, B, K)."""
    analysis = analysis or level_uplift_analysis(con, run)
    stats = analysis["steps"]
    if not stats:
        return False
    rows, rows_mean, rows_plug = [], [], []
    for g, steps in stats.items():
        rows.append(r"\multicolumn{8}{@{}l}{\emph{" + esc(g) + "}}")
        rows_mean.append(r"\multicolumn{5}{@{}l}{\emph{" + esc(g) + "}}")
        rows_plug.append(r"\multicolumn{9}{@{}l}{\emph{" + esc(g) + "}}")
        for s in steps:
            step = (f"{level_label(s['lo_level'])}$\\to${level_label(s['hi_level'])} &"
                    f" {s['lo_id']}$\\to${s['hi_id']}")
            rows.append(
                f"{step} & {money(s['dEVSI_q50'])} & {money(s['dC_q50'])} &"
                f" {num(s['meff'])} & {pct(s['p_dc_pos'])} & {pct(s['p_gain'])} & {pct(s['p_pays'])}")
            rows_mean.append(
                f"{step} & {money(s['dEVSI_mean'])} & {money(s['dC_mean'])} & {num(s['meff_mean'])}")
            boot_ci = interval((s["meff_plug_q05"], s["meff_plug_q95"])) + (
                r"$^\dagger$" if sign_unstable(s) else "")
            rows_plug.append(
                f"{step} & {money(s['dEVSI_plug'])} & {money(s['dC_plug'])} & {num(s['meff_plug'])} &"
                f" {boot_ci} & {pct(s['p_pays_plug'])} & {money(s['dEVSI_star'])} & {num(s['meff_star'])}")
    header = (r"step & ids & $\Delta$EVSI & $\Delta C$ & $\Delta$EVSI/$\Delta C$ &"
              r" $P(\Delta C>0)$ & $P(\Delta\mathrm{EVSI}>0)$ & $P(\Delta\mathrm{EVSI}>\Delta C)$")
    crn = tabular(
        "@{}llrrrrrr@{}", header, rows,
        "adjacent-rung marginals within one decision (ladders: groups whose rungs share the"
        f" agent, decision and theta text) over {run['n_draws']} common-random-number draws"
        f" seeded like run {run['id']} (p, B, K drawn once per ladder from the pooled rung"
        " fits, s, t, C per rung; not the stored run's draws); medians of dEVSI and dC,"
        " dEVSI/dC is the ratio of those medians", small=True)
    means = tabular(
        "@{}llrrr@{}",
        r"step & ids & $\overline{\Delta\mathrm{EVSI}}$ & $\overline{\Delta C}$ &"
        r" $\overline{\Delta\mathrm{EVSI}}/\overline{\Delta C}$", rows_mean,
        "the same steps by the mean-based marginals: means of dEVSI and dC over the same"
        " common-random-number draws and their ratio", small=True)
    header_plug = (r"step & ids & $\Delta$EVSI$_\mathrm{pi}$ & $\Delta C_\mathrm{pi}$ &"
                   r" $\Delta$EVSI$_\mathrm{pi}/\Delta C_\mathrm{pi}$ & [q05, q95] &"
                   r" \begin{tabular}[b]{@{}r@{}}$P_\mathrm{boot}$\\(pays)\end{tabular} &"
                   r" $\Delta$EVSI$^\star$ & $\Delta$EVSI$^\star/\Delta C_\mathrm{pi}$")
    plug = tabular(
        "@{}llrrrrrrr@{}", header_plug, rows_plug,
        "the same steps by the plug-in marginals (pi: differences of the per-rung values at the"
        " pooled medians, p, B, K pooled over the ladder, s, t, C per rung, EVSI from model.voi,"
        " C the rung's median) with the bootstrap over elicitations"
        f" ({analysis.get('n_boot', N_BOOT)} replicates seeded from the run's seed: each rung's"
        " valid elicitations resampled within each member, p, B, K pooled over the resampled"
        " rungs, a staged protocol's decision stage resampled once per replicate for the whole"
        " group): [q05, q95] of dEVSI_pi / dC_pi over the replicates with dC_pi != 0, rounded"
        " outward to two significant digits (a dagger marks a step whose dC_pi takes each sign in"
        f" at least {BOOT_SIGN_FLAG:.0%} of them, where the ratio straddles its pole) and"
        " P_boot (pays) = P_boot(dEVSI_pi > dC_pi), the share of replicates in which the step pays"
        " (not plugin.tex's P_boot (gate)); and the fence"
        " marginals (differences of the per-rung EVSI* = (B + K) p (1 - p) (s + t - 1) at the"
        " same medians, over the plug-in dC). Both use p, B, K pooled over the ladder, as the"
        " CRN draws do; fig_level_fence and the EVSI* column of plugin.tex use each scenario's"
        " own medians, so their per-rung values (and the sign of a step) can differ where a"
        " single-stage protocol's p, B, K move across rungs", small=True)
    _write(out, "level_uplift.tex", "\\par\\medskip\n".join((crn, means, plug)))
    return True


def fig_level_fence(con, run, out: Path) -> bool:
    """Per group of leveled scenarios ranked in the run: the fence value
    EVSI*, the plug-in EVSI and C, each at the scenario's own pooled
    medians, against the level (log y). Skipped without a leveled ranked
    scenario with a complete plug-in point."""
    levels = scenario_levels(con)
    groups = scenario_groups(con)
    order = [s for s in ranked_ids(con, run["id"]) if s in levels]
    pts = {s: plugin_point(con, run, s) for s in order}
    order = [s for s in order if pts[s] is not None]
    if not order:
        return False
    names = sorted({groups[s] or "(no group)" for s in order})
    fig, axes = plt.subplots(1, len(names), figsize=(min(6.2, 3.3 * len(names)), 2.9),
                             squeeze=False, sharey=True)
    series = (("EVSI_star", "^", CATEGORICAL[2], "EVSI* (fence)"), ("EVSI", "o", ACCENT, "EVSI (plug-in)"),
              ("C", "s", CATEGORICAL[1], "C"))
    for ax, g in zip(axes[0], names, strict=True):
        sids = sorted((s for s in order if (groups[s] or "(no group)") == g), key=lambda s: (levels[s], s))
        x = np.array([levels[s] for s in sids])
        for key, marker, color, label in series:
            y = np.array([pts[s][key] for s in sids], dtype=float)
            floored = y < EVSI_FLOOR
            y = np.maximum(y, EVSI_FLOOR)
            ax.plot(x[~floored], y[~floored], marker, color=color, ms=4.5, mec="white", mew=0.4,
                    label=label if g == names[0] else None, ls="-", lw=0.7, alpha=0.9)
            ax.plot(x[floored], y[floored], marker, mfc="white", mec=color, ms=4.5)
        ax.set_yscale("log")
        ax.set_title(g, fontsize=9)
        ax.set_xticks(sorted(set(x)))
        ax.set_xticklabels([level_label(lv) for lv in sorted(set(x))])
        ax.set_xlabel("level", fontsize=8)
        ax.tick_params(labelsize=7)
    axes[0][0].set_ylabel("USD at the pooled medians", fontsize=8)
    axes[0][0].legend(fontsize=6, frameon=False, loc="best")
    fig.suptitle("Fence value EVSI* = (B+K) p (1-p) (s+t-1), plug-in EVSI and cost C at each scenario's"
                 f" pooled medians,\nagainst its level (open markers: below {EVSI_FLOOR:g} USD; the"
                 " level-uplift marginals pool p, B, K over the ladder instead)",
                 fontsize=7.5)
    fig.savefig(out / "fig_level_fence.pdf")
    plt.close(fig)
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


def member_agreement_names(con, protocol_id: int) -> list[str]:
    """The parameters fig_member_agreement correlates per scenario: all six,
    or the scenario-stage ones of a staged protocol (its decision-stage
    values are one number per group, so a per-scenario Spearman on them
    would rank two distinct values over every rung; health prints the
    per-group decision-level agreement instead)."""
    stages = db.protocol_stages(con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone())
    return list(db.PARAM_NAMES) if stages is None else list(db.scenario_stage(stages)["params"])


def fig_member_agreement(con, run, out: Path) -> bool:
    members = run_members(con, run)
    if len(members) < 2:
        return False
    labels = [db.member_label(m) for m in members]
    names = member_agreement_names(con, run["protocol_id"])
    pairs = list(combinations(range(len(members)), 2))
    pooled = {(i, name): member_pooled_p50(con, run["protocol_id"], m, name)
              for i, m in enumerate(members) for name in names}
    fig, axes = plt.subplots(len(pairs), len(names),
                             figsize=(6.2, 1.25 * len(pairs) + 0.6), squeeze=False)
    for r, (i, j) in enumerate(pairs):
        for c, name in enumerate(names):
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
    staged = "" if len(names) == len(db.PARAM_NAMES) else (
        f"\n${', '.join(names)}$ only: the decision stage is one number per group,"
        " see health's decision-level agreement")
    fig.suptitle("Cross-member agreement of each member's per-scenario median p50 (Spearman over"
                 f" shared scenarios){staged}", fontsize=8)
    fig.savefig(out / "fig_member_agreement.pdf")
    plt.close(fig)
    return True


def write_member_agreement(con, run, out: Path) -> bool:
    if len(run_members(con, run)) < 2:
        return False
    mr = member_rankings(con, run)
    # the stored run: 'run', 'run/equal' for an equal-member run (db.run_label); never 'pooled',
    # which also names a weighting; the caption spells the weighting out
    weights = db.weights_label(db.run_weights(run))
    names = mr["members"] + [db.run_label("run", None, db.run_weights(run))]
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
        f" not the stored run) and the stored run {run['id']} ({weights}), over shared scenarios"))
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


def write_simplicity(con, run, out: Path, prefix: str = MACRO_PREFIX) -> bool:
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
    write_macros(out, macros, prefix=prefix)
    return True


# --- 6. protocol noise at matched k --------------------------------------------

def latest_run_per_protocol(con) -> dict[str, int]:
    """{label: run id}: the latest run of every protocol, and of every member
    subset and weighting scored under it (label 'p003[opus+sonnet]',
    'p003/equal'), that the v2 analyses
    accept (db.run_predates_v2 is None, the gate select_run applies); a
    protocol whose runs all predate the v2 model is left out rather than
    correlated against v2 runs."""
    out = {}
    for p in con.execute("SELECT * FROM protocols ORDER BY id"):
        latest: dict[tuple, int] = {}
        for r in con.execute("SELECT * FROM runs WHERE protocol_id=? ORDER BY id DESC", (p["id"],)):
            key = (r["members_json"], db.run_weights(r))
            if key not in latest and db.run_predates_v2(con, r) is None:
                latest[key] = r["id"]
        # protocol order, the all-member run first, then its subsets (pooled, then equal-member)
        for key in sorted(latest, key=db.run_key_order):
            out[db.run_label(p["name"], json.loads(key[0]) if key[0] else None, key[1])] = latest[key]
    return out


def member_repeat_counts(con, protocol_id: int, member: dict) -> dict[int, int]:
    """{scenario_id: valid repeats} one member holds under a protocol: the
    repeats actually pooled, which `elicit --k` can push past the protocol's
    nominal k_repeats (the business p001 was filled from 3 to 5) and an
    invalid slot can pull below it. Counted per slot family (scenario,
    stage): under a staged protocol a representative's decision and
    instrument rows are two families of k, not one of 2k, and the scenario
    reports the larger."""
    out: dict[int, int] = {}
    for sid, n in con.execute(
            "SELECT scenario_id, COUNT(*) FROM elicitations WHERE protocol_id=? AND valid=1"
            " AND provider=? AND model=? GROUP BY scenario_id, COALESCE(stage, '')",
            (protocol_id, member["provider"], member["model"])):
        out[sid] = max(out.get(sid, 0), n)
    return out


def member_k_used(con, protocol_id: int, member: dict) -> int:
    """Largest valid repeat count one member holds for any scenario."""
    return max(member_repeat_counts(con, protocol_id, member).values(), default=0)


def member_noise(con, protocol_id: int, member: dict, first: int | None,
                 names: list[str] | None = None) -> tuple[dict, dict]:
    """({param: median cross-repeat spread}, {param: n units with >= 2
    repeats}) for one member over `names` (the binary parameters by
    default; a Gaussian protocol's quantities when given), optionally
    truncated to the first `first` valid repeats of each unit (in repeat_ix
    order). A unit is a scenario, or a group for a decision-stage parameter
    of a staged protocol (its rows sit once per group, on the
    representative), so the counts differ per parameter there: p, B, K over
    2 groups, s, t, C over 15 scenarios."""
    med, n = {}, {}
    label = [db.member_label(member)]
    for name in db.PARAM_NAMES if names is None else names:
        # the scenarios carrying the parameter for this member (group
        # representatives for a decision-stage parameter of a staged protocol)
        spreads = [sp for sid in db.param_scenario_ids(con, protocol_id, name, label)
                   if (sp := db.elicited_spread(con, protocol_id, sid, name, member["provider"],
                                                member["model"], first)) is not None]
        med[name] = float(np.median(spreads)) if spreads else None
        n[name] = len(spreads)
    return med, n


def noise_n_label(counts: dict[str, int], stages: list[dict] | None) -> str:
    """The n column of the matched-k noise table: one count for a
    single-stage protocol (every parameter's), 'groups / scenarios' for a
    staged one, whose decision-stage cells are medians over groups."""
    if stages is None:
        return str(max(counts.values(), default=0))
    g, s = db.group_stage(stages), db.scenario_stage(stages)
    n_g = max((counts[n] for n in g["params"] if n in counts), default=0)
    n_s = max((counts[n] for n in s["params"] if n in counts), default=0)
    return f"{n_g} / {n_s}"


def staged_noise_note(staged: list[str]) -> str:
    """Caption clause for a noise table that lists a staged protocol: its
    decision-stage cells are medians over groups, not scenarios."""
    if not staged:
        return ""
    return (f"; under a staged protocol ({', '.join(esc(p) for p in staged)}) the decision-stage"
            " cells are medians over groups (one elicitation set per group, on its"
            " representative) and n reads groups / scenarios")


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
    rows, staged = [], []
    for pname, m, label, cap in noise_rows(con):
        prot = db.protocol_by_name(con, pname)
        stages = db.protocol_stages(prot)
        if stages is not None and pname not in staged:
            staged.append(pname)
        med, counts = member_noise(con, prot["id"], m, cap)
        cells = " & ".join(num(med[name], "{:.2f}") for name in db.PARAM_NAMES)
        rows.append(f"{esc(pname)} & {esc(db.member_label(m))} & {label} & {cells}"
                    f" & {noise_n_label(counts, stages)}")
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
                    " differ)" + staged_noise_note(staged))
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

# regime code (gate_regime_codes) -> gate_regime's label
REGIMES = ("in gate", "always respond", "never respond")


def gate_regime_codes(p, s, t, B, K) -> np.ndarray:
    """gate_regime over arrays: 0 in gate, 1 always respond, 2 never respond
    (REGIMES), by the same float operations as the scalar rule."""
    p, s, t, B, K = np.broadcast_arrays(*(np.asarray(v, dtype=float) for v in (p, s, t, B, K)))
    P1 = p * s + (1.0 - p) * (1.0 - t)
    P0 = 1.0 - P1
    with np.errstate(divide="ignore", invalid="ignore"):
        pi1 = np.where(P1 > 0.0, p * s / P1, p)
        pi0 = np.where(P0 > 0.0, p * (1.0 - s) / P0, p)
    pi_star = K / (B + K)
    lo, hi = np.minimum(pi0, pi1), np.maximum(pi0, pi1)
    return np.where(pi_star <= lo, 1, np.where(pi_star >= hi, 2, 0))


def gate_regime(p: float, s: float, t: float, B: float, K: float) -> str:
    """Where the decision sits at one parameter point: 'in gate' when the
    threshold pi* = K / (B + K) lies strictly between the two posteriors
    pi1 = P(theta=1 | x=1) and pi0 = P(theta=1 | x=0), so the signal can flip
    the action and EVSI > 0; 'always respond' when both posteriors are at or
    above pi*; 'never respond' when both are at or below it. A signal value
    of probability zero leaves the belief at the prior p."""
    return REGIMES[int(gate_regime_codes(p, s, t, B, K))]


def plugin_values(med: dict) -> dict:
    """The plug-in point at one set of medians {p, s, t, B, K, C}: {"medians",
    "EVSI", "EVPI", "eff", "regime", "EVSI_star", "eff_star", "C",
    "fence_ratio"} (plugin_point, and the bootstrap's point estimate)."""
    evsi, evpi = model.voi(med["p"], med["s"], med["t"], med["B"], med["K"])
    star = float(model.voi_fence(med["p"], med["s"], med["t"], med["B"], med["K"]))
    return {"medians": med, "EVSI": float(evsi), "EVPI": float(evpi),
            "eff": float(evsi) / med["C"],
            "regime": gate_regime(med["p"], med["s"], med["t"], med["B"], med["K"]),
            "EVSI_star": star, "eff_star": star / med["C"], "C": med["C"],
            "fence_ratio": (float(evsi) / star if star > 0.0 else float("nan")) if evsi > 0.0 else 0.0}


def plugin_point(con, run, sid: int) -> dict | None:
    """model.voi at the pooled elicited medians of one scenario
    (plugin_values); None when a parameter has no valid elicitation under
    the run's protocol."""
    labels = db.run_member_labels(run)
    med = {name: pooled_p50(con, run["protocol_id"], sid, name, labels) for name in db.PARAM_NAMES}
    if any(v is None for v in med.values()):
        return None
    return plugin_values(med)


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
        d = draw_metrics(rng, f, run["n_draws"], db.run_weights(run))   # the run's mixture weighting
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
    star = {r["sid"]: r["eff_star"] for r in rows}
    top_star = sorted(star, key=lambda s: (-star[s], s))[:k]
    positive = [r for r in rows if r["EVSI"] > 0.0]
    return {
        "rows": rows,
        "rho_plugin_median": rho("eff", "mc_median"),
        "rho_plugin_mean": rho("eff", "mc_mean"),
        "rho_median_mean": rho("mc_median", "mc_mean"),
        "n_gate": sum(1 for r in rows if r["regime"] == "in gate"),
        "n_zero_median": sum(1 for s in order if float(evsi[s]["q50"] or 0.0) == 0.0),
        "top_k": k, "top_overlap": len(set(order[:k]) & set(top_plugin)),
        # the fence ranking against the plug-in one: Spearman over the scenarios inside the
        # gate at the medians (EVSI > 0; outside it the plug-in eff is 0 and ranks nothing)
        "fence_rho": (spearman([r["eff_star"] for r in positive], [r["eff"] for r in positive])
                      if len(positive) >= 3 else None),
        "fence_n": len(positive),
        "fence_top_overlap": len(set(top_plugin) & set(top_star)),
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


def write_plugin(con, run, out: Path, st: dict | None = None, prefix: str = MACRO_PREFIX,
                 pb: dict | None = None) -> bool:
    """plugin.tex (the plug-in and fence values with their bootstrap
    intervals, pb = plugin_bootstrap, drawn here when not passed, then the
    summary of the three rankings) and plugin_mc.tex (the plug-in EVPI and
    the Monte Carlo summaries of the same scenarios in the same order): two
    longtables within the CoRL text width (plugin.tex in footnotesize, the
    compile test prints real-width values). The plug-in macros go to
    macros_extra.tex (merged)."""
    st = st or plugin_stats(con, run)
    if st is None:
        return False
    pb = pb or plugin_bootstrap(con, run)
    boot = pb["rows"] if pb is not None else {}
    undefined = (float("nan"),) * 3
    rows, mc_rows = [], []
    for r in st["rows"]:
        b = boot.get(r["sid"], {})
        rows.append(
            f"{r['rank']} & {r['sid']} & {money(r['medians']['C'])} & {money(r['EVSI'])} &"
            f" {money(r['EVSI_star'])} & {num(r['eff'])} &"
            f" {interval(b.get('eff_q', undefined))} & {num(r['eff_star'])} &"
            f" {interval(b.get('eff_star_q', undefined))} & {num(r['fence_ratio'], '{:.2f}')} &"
            f" {REGIME_CELL[r['regime']]} & {pct(b.get('p_gate', float('nan')))}")
        mc_rows.append(
            f"{r['rank']} & {r['sid']} & {money(r['EVPI'])} & {num(r['eff'])} & {num(r['mc_median'])} &"
            f" {num(r['mc_mean'])} & {pct(r['p_positive'])} & {pct(r['p_gate'])}")
    header = (r"rank & id & $C$ & EVSI & EVSI$^\star$ & eff & [q05, q95] & eff$^\star$ & [q05, q95] &"
              r" \begin{tabular}[b]{@{}r@{}}EVSI/\\EVSI$^\star$\end{tabular} & regime &"
              r" \begin{tabular}[b]{@{}r@{}}$P_\mathrm{boot}$\\(gate)\end{tabular}")
    replicates = (f"{pb['n_boot']} replicates (seed {pb['seed']})" if pb is not None
                  else "no replicates")
    table = longtable(
        "@{}rrrrrrrrrrlr@{}", header, rows,
        r"Plug-in values per scenario, in the order of the run's median efficiency (rank; the"
        r" plug-in EVPI and the Monte Carlo summaries of the same rows, in the same order, are a"
        r" companion table). EVSI and eff $=$ EVSI$/C$ are \texttt{model.voi} at the pooled"
        r" elicited medians of $p$, $s$, $t$, $B$, $K$ (the catalog's values) and $C$ (median of"
        r" the p50 across valid elicitations, printed here because the catalog's $C$ is the run's mixture"
        r" median). EVSI$^\star = (B+K)\,p(1-p)(s+t-1)$ at the same medians is the fence value,"
        r" the maximum of EVSI over the threshold $\pi^*$ at fixed stakes (the buyer on the"
        r" fence, $\pi^* = p$); eff$^\star = $ EVSI$^\star/C$; EVSI/EVSI$^\star$ is the share of"
        r" it this buyer obtains (0 outside the gate)."
        r" Regime at the medians from $\pi^* = K/(B+K)$ against the posteriors"
        r" $\pi_1$, $\pi_0$: gate ($\pi^*$ strictly between them, EVSI $>$ 0), always / never"
        r" respond (both posteriors at or above / below $\pi^*$, EVSI $=$ 0)."
        r" [q05, q95] after eff and eff$^\star$ and $P_\mathrm{boot}(\mathrm{gate})$"
        r" come from the bootstrap over elicitations, " + replicates + r", each resampling every"
        r" scenario's valid elicitations of the run's members with replacement within each member"
        r" (keeping each member's count; a staged protocol's decision stage once per group) and"
        r" recomputing the pooled medians and the values at them: the interval over the"
        r" replicates, and the share of replicates in the gate; the interval is rounded outward"
        r" to two significant digits. USD in $C$, EVSI, EVSI$^\star$.",
        tex_label("tab:plugin", prefix), small=True)
    mc_header = (r"rank & id & EVPI & eff & $\mathrm{eff}_{q50}$ & $\overline{\mathrm{eff}}$ & $P_+$ &"
                 r" $P_\mathrm{gate}$")
    _write(out, "plugin_mc.tex", longtable(
        "@{}rrrrrrrr@{}", mc_header, mc_rows,
        r"Plug-in EVPI and Monte Carlo summaries per scenario, in the order of the run's median"
        r" efficiency (rank), next to the plug-in eff of the companion plug-in table (same rows"
        r" and order). EVPI $= \min(pB, (1-p)K)$ (USD) at the same pooled elicited medians, the"
        r" \texttt{model.voi} bound on EVSI."
        r" $\mathrm{eff}_{q50}$: the run's stored median efficiency; $\overline{\mathrm{eff}}$:"
        f" the mean over the {run['n_draws']} draws of run {run['id']}, replayed from the DB and"
        r" verified against the stored quantiles; $P_+ = P(\mathrm{EVSI} > C)$ stored by the run;"
        r" $P_\mathrm{gate} = P(\mathrm{EVSI} > 0)$ over the replayed draws (the Monte Carlo"
        r" draws, not the bootstrap's elicitation resamples behind"
        r" $P_\mathrm{boot}(\mathrm{gate})$).", tex_label("tab:plugin-mc", prefix)))
    summary = tabular("@{}lr@{}", "statistic & value", [
        r"Spearman $\rho$(plug-in eff, MC median eff) & " + num(st["rho_plugin_median"], "{:.2f}"),
        r"Spearman $\rho$(plug-in eff, MC mean eff) & " + num(st["rho_plugin_mean"], "{:.2f}"),
        r"Spearman $\rho$(MC median eff, MC mean eff) & " + num(st["rho_median_mean"], "{:.2f}"),
        r"Spearman $\rho$(fence eff$^\star$, plug-in eff), EVSI $>$ 0 & "
        + num(st["fence_rho"], "{:.2f}") + f" ($n$={st['fence_n']})",
        f"scenarios in gate at the medians & {st['n_gate']} / {len(st['rows'])}",
        f"scenarios with MC median EVSI $= 0$ & {st['n_zero_median']} / {len(st['rows'])}",
        f"top-{st['top_k']} overlap, plug-in vs MC median & {st['top_overlap']} / {st['top_k']}",
        f"top-{st['top_k']} overlap, fence vs plug-in & {st['fence_top_overlap']} / {st['top_k']}",
    ], "plug-in, fence and Monte Carlo rankings over the efficiencies of the table above")
    _write(out, "plugin.tex", table + "\\par\\medskip\n" + summary)
    write_macros(out, {
        "voiPluginRhoMedian": num(st["rho_plugin_median"], "{:.2f}"),
        "voiPluginRhoMean": num(st["rho_plugin_mean"], "{:.2f}"),
        "voiMedianMeanRho": num(st["rho_median_mean"], "{:.2f}"),
        "voiPluginInGate": st["n_gate"],
        "voiMcZeroMedian": st["n_zero_median"],
        "voiPluginTopK": st["top_k"],
        "voiPluginTopOverlap": st["top_overlap"],
        "voiFenceRhoPlugin": num(st["fence_rho"], "{:.2f}"),
        "voiFenceN": st["fence_n"],
        "voiFenceTopOverlap": st["fence_top_overlap"],
    }, merge=True, prefix=prefix)
    return True


# --- 8. the plug-in map --------------------------------------------------------------

def plugin_map_points(con, run) -> list[dict]:
    """Per ranked scenario with a complete plug-in point, in the run's
    order: {"sid", "grp", "domain" (attributes.risk_domain or None), "C",
    "EVSI", "EVSI_star", "regime"}, all from plugin_point (the pooled
    medians of the run's members)."""
    groups, domains = scenario_groups(con), scenario_domains(con)
    rows = []
    for sid in ranked_ids(con, run["id"]):
        pt = plugin_point(con, run, sid)
        if pt is not None:
            rows.append({"sid": sid, "grp": groups.get(sid), "domain": domains.get(sid),
                         **{key: pt[key] for key in ("C", "EVSI", "EVSI_star", "regime")}})
    return rows


def fig_plugin_map(con, run, out: Path, rows: list[dict] | None = None, pb: dict | None = None) -> bool:
    """fig_plugin_map.pdf, the headline map at the pooled medians: plug-in
    EVSI (y, log) against the pooled-median C (x, log), one point per
    scenario, coloured by group and shaped by attributes.risk_domain when
    any scenario has one. A scenario outside the gate (always / never
    respond, EVSI = 0) sits at the y floor as an open marker. The fence
    value EVSI* at the same medians is a small hollow marker on a thin
    dotted stem from the plug-in point: decision value against fence
    value. Thin grey bars give the q05-q95 of the plug-in EVSI (vertical)
    and of C (horizontal) under the bootstrap over elicitations (pb =
    plugin_bootstrap, drawn here when not passed; floored like the points).
    Iso-efficiency diagonals and the 'better' arrow as in
    figures.fig_evsi_vs_cost; every id labelled. Artists carry gid
    'plugin' / 'fence' / 'stem' / 'boot_evsi' / 'boot_c' (the test reads
    the plotted values back)."""
    rows = plugin_map_points(con, run) if rows is None else rows
    if not rows:
        return False
    pb = pb or plugin_bootstrap(con, run)
    xs = np.array([r["C"] for r in rows])
    evsi = np.array([r["EVSI"] for r in rows])
    star = np.array([r["EVSI_star"] for r in rows])
    floored = evsi < EVSI_FLOOR
    y = np.maximum(evsi, EVSI_FLOOR)
    ystar = np.maximum(star, EVSI_FLOOR)
    grp_of = [r["grp"] or "(no group)" for r in rows]
    grp_names = sorted(set(grp_of))
    colors = group_colors([g for g in grp_names if g != "(no group)"])
    colors["(no group)"] = "#7f7f7f" if len(grp_names) > 1 else ACCENT
    has_domain = any(r["domain"] for r in rows)
    dom_of = [r["domain"] or "(none)" for r in rows]
    dom_names = sorted(set(dom_of))
    marker = {d: MARKERS[i % len(MARKERS)] if has_domain else "o" for i, d in enumerate(dom_names)}

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    boot_at = [(i, pb["rows"][r["sid"]]) for i, r in enumerate(rows)
               if pb is not None and r["sid"] in pb["rows"]]
    e_hi = c_lo = c_hi = np.array([])
    if boot_at:
        at = np.array([i for i, _ in boot_at])
        e_lo, e_hi = (np.maximum([b["EVSI_q"][k] for _, b in boot_at], EVSI_FLOOR) for k in (0, 2))
        c_lo, c_hi = (np.array([b["C_q"][k] for _, b in boot_at]) for k in (0, 2))
        ax.vlines(xs[at], e_lo, e_hi, color=BOOT_BAR, lw=1.6, zorder=0.9, gid="boot_evsi")
        ax.hlines(y[at], c_lo, c_hi, color=BOOT_BAR, lw=1.6, zorder=0.9, gid="boot_c")
    ax.vlines(xs, y, ystar, color="#6f7a86", lw=0.6, ls=(0, (1, 1.5)), zorder=1, gid="stem")
    for g in grp_names:
        for d in dom_names:
            mask = np.array([a == g and b == d for a, b in zip(grp_of, dom_of, strict=True)])
            if not mask.any():
                continue
            c, mk = colors[g], marker[d]
            ax.plot(xs[mask], ystar[mask], mk, ls="", mfc="white", mec=c, ms=3.2, mew=0.7, zorder=2,
                    gid="fence")
            ax.plot(xs[mask & ~floored], y[mask & ~floored], mk, ls="", color=c, ms=5.5, mec="white",
                    mew=0.5, zorder=3, gid="plugin")
            ax.plot(xs[mask & floored], y[mask & floored], mk, ls="", mfc="white", mec=c, ms=5.5,
                    mew=0.9, zorder=3, gid="plugin")
    for i, r in enumerate(rows):
        ax.annotate(str(r["sid"]), (xs[i], y[i]), textcoords="offset points",
                    xytext=(4, 3) if i % 2 == 0 else (-4, -8),
                    ha="left" if i % 2 == 0 else "right", fontsize=6, color="#333333", zorder=4)
    ax.set_xscale("log")
    ax.set_yscale("log")
    xlim = np.array([min(xs.min(), *c_lo) / 3, max(xs.max(), *c_hi) * 3])
    # the floor only when a point sits on it; 1.5 decades of headroom keep the arrow clear
    ylim = np.array([EVSI_FLOOR / 2 if floored.any() else y.min() / 30,
                     max(ystar.max(), *e_hi, EVSI_FLOOR) * 30])
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    iso_efficiency_lines(ax, xlim, ylim)
    ax.annotate("better (more decision value per dollar)",
                xy=(0.03, 0.97), xytext=(0.13, 0.87),
                xycoords="axes fraction", textcoords="axes fraction",
                fontsize=7, color="#333333", ha="left", va="center",
                arrowprops={"arrowstyle": "-|>", "color": "#333333", "lw": 0.9})
    handles = []
    if len(grp_names) > 1:
        handles += [plt.Line2D([], [], marker="o", ls="", color=colors[g], label=g) for g in grp_names]
    if has_domain:
        handles += [plt.Line2D([], [], marker=marker[d], ls="", color="#555555", label=d) for d in dom_names]
    if floored.any():
        handles.append(plt.Line2D([], [], marker="o", ls="", mfc="white", mec="#555555",
                                  label="EVSI = 0 (at floor)"))
    handles.append(plt.Line2D([], [], marker="o", ls=(0, (1, 1.5)), lw=0.6, color="#6f7a86", mfc="white",
                              mec="#555555", ms=3.2, label="fence EVSI$^\\star$"))
    if boot_at:
        handles.append(plt.Line2D([], [], ls="-", lw=1.6, color=BOOT_BAR,
                                  label=f"bootstrap q05-q95 ({pb['n_boot']} replicates)"))
    title = ("colour: group; marker: risk domain" if len(grp_names) > 1 and has_domain
             else "colour: group" if len(grp_names) > 1 else "marker: risk domain" if has_domain else None)
    ax.legend(handles=handles, fontsize=6, loc="lower right", frameon=False, title=title, title_fontsize=6)
    ax.set_xlabel("pooled median C (USD)")
    ax.set_ylabel("plug-in EVSI (USD per measurement)")
    ax.set_title("Plug-in EVSI vs cost at the pooled medians; stems up to the fence value EVSI$^\\star$",
                 fontsize=9)
    fig.savefig(out / "fig_plugin_map.pdf")
    plt.close(fig)
    return True


# --- 9. bootstrap over elicitations ------------------------------------------------

N_BOOT = 2000                 # replicates (extra --boot overrides)
BOOT_SEED_OFFSET = 1_000_003  # the bootstrap's seed: run seed + this, one stream per unit (unit_rng)
BOOT_TOP_K = 3                # P(rank <= BOOT_TOP_K) in plugin_ranks.tex
# a step's bootstrap ratio dEVSI/dC is flagged when dC takes each sign in at
# least this share of the replicates with dC != 0 (those the ratio's q05-q95
# are taken over): the ratio then straddles its pole and its q05-q95 are not
# an interval of anything (P(dEVSI > dC) still is)
BOOT_SIGN_FLAG = 0.05


def bootstrap_units(con, run) -> tuple[dict, dict[int, dict[str, tuple]]]:
    """The resampling units of the run's valid elicitations (the run's
    members only): ({key: {"names": [params], "members": [(label, n)],
    "base": (N, k) p50 matrix, rows grouped by member in label order, then
    repeat and id}}, {sid: {param: key}}). Single-stage protocol: one unit
    per scenario, key ('scenario', sid), with its six parameters. Staged
    protocol: the group stage's rows form one unit per group, key ('group',
    value), whichever scenario of the group holds them (as db._elicited_rows
    reads them, retired scenarios included), and the scenario stage's rows
    one unit per scenario. A column holds exactly the p50s that pooled_p50
    takes the median of; a parameter missing from an elicitation is NaN.
    Scenarios whose every parameter has a unit with a value are mapped (the
    ones plugin_point is defined for)."""
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    stages = db.protocol_stages(prot)
    clause, margs = db.member_filter(db.run_member_labels(run))
    rows = con.execute(
        "SELECT e.id, e.scenario_id, e.stage, e.provider || ':' || e.model AS member, e.repeat_ix,"
        " p.name, p.p50 FROM elicitations e JOIN parameters p ON p.elicitation_id = e.id"
        f" WHERE e.protocol_id=? AND e.valid=1{clause}", (run["protocol_id"], *margs)).fetchall()
    group_of: dict[int, str | None] = {}
    if stages is not None:
        gstage, sstage = db.group_stage(stages), db.scenario_stage(stages)
        group_of = {r["id"]: db.scenario_group_value(r, gstage["group_key"])
                    for r in con.execute("SELECT * FROM scenarios")}

    def unit_of(r) -> tuple | None:
        if stages is None:
            return ("scenario", r["scenario_id"]) if r["name"] in db.PARAM_NAMES else None
        if r["stage"] == gstage["name"] and r["name"] in gstage["params"]:
            value = group_of.get(r["scenario_id"])
            return None if value is None else ("group", value)
        if r["stage"] == sstage["name"] and r["name"] in sstage["params"]:
            return ("scenario", r["scenario_id"])
        return None

    elic: dict[tuple, dict[int, dict]] = {}
    for r in rows:
        key = unit_of(r)
        if key is not None:
            e = elic.setdefault(key, {}).setdefault(
                r["id"], {"member": r["member"], "repeat": r["repeat_ix"], "p50": {}})
            e["p50"][r["name"]] = float(r["p50"])
    units = {}
    for key, by_id in elic.items():
        names = [n for n in db.PARAM_NAMES
                 if (stages is None or n in (gstage if key[0] == "group" else sstage)["params"])]
        order = sorted(by_id, key=lambda i: (by_id[i]["member"], by_id[i]["repeat"], i))
        base = np.array([[by_id[i]["p50"].get(n, np.nan) for n in names] for i in order], dtype=float)
        counts: dict[str, int] = {}
        for i in order:
            counts[by_id[i]["member"]] = counts.get(by_id[i]["member"], 0) + 1
        units[key] = {"names": names, "members": list(counts.items()), "base": base}
    of = {}
    for sid in ranked_ids(con, run["id"]):
        if stages is None:
            keys = dict.fromkeys(db.PARAM_NAMES, ("scenario", sid))
        else:
            keys = {n: ("group", group_of.get(sid)) for n in gstage["params"]}
            keys.update({n: ("scenario", sid) for n in sstage["params"]})
        if all(k in units and np.isfinite(units[k]["base"][:, units[k]["names"].index(n)]).any()
               for n, k in keys.items()):
            of[sid] = keys
    return units, of


def resample_indices(rng, counts: list[int], n_boot: int) -> np.ndarray:
    """(n_boot, sum(counts)) row indices into a unit's base matrix,
    stratified by member: column block m (after the blocks of the members
    before it) draws counts[m] indices with replacement from member m's own
    rows, so every replicate keeps each member's count."""
    blocks, offset = [], 0
    for n in counts:
        blocks.append(offset + rng.integers(0, n, size=(n_boot, n)))
        offset += n
    return np.concatenate(blocks, axis=1)


def _median(values: np.ndarray, axis: int) -> np.ndarray:
    """np.median (pooled_p50's rule), np.nanmedian only where a parameter is
    missing from an elicitation."""
    return (np.nanmedian if np.isnan(values).any() else np.median)(values, axis=axis)


def unit_rng(seed: int, key: tuple) -> np.random.Generator:
    """The generator of one resampling unit: SeedSequence(seed) spawned by
    the unit key, (0, sid) for a scenario and (1, the UTF-8 bytes of the
    value) for a group, so a unit's resample depends on the seed and its own
    rows only, not on which other units the run's protocol holds (a valid
    elicitation added to another scenario, ranked or not, leaves it
    unchanged)."""
    kind, value = key
    spawn = (0, int(value)) if kind == "scenario" else (1, *str(value).encode())
    return np.random.default_rng(np.random.SeedSequence(seed, spawn_key=spawn))


def bootstrap_draws(con, run, n_boot: int = N_BOOT) -> dict:
    """The bootstrap over elicitations of a binary run. One replicate
    resamples, for every unit of bootstrap_units, its valid elicitations with
    replacement within each member of the run (keeping each member's
    count), and takes the pooled median of every parameter over the
    resample. A staged protocol's decision stage is one unit per group, so a
    replicate resamples it once and every scenario of the group reads the
    same resample. Seed = run seed + BOOT_SEED_OFFSET; each unit draws from
    its own generator (unit_rng), members in label order: deterministic for
    a unit's rows, whatever the other units hold. Returns {"n_boot",
    "seed", "units" (each with "idx", the (n_boot, N) resample, "boot", the
    (n_boot, k) replicate medians, and "point", the (k,) medians of all
    rows), "of" ({sid: {param: key}}), "sids" (in the run's ranking
    order)}."""
    units, of = bootstrap_units(con, run)
    seed = int(run["seed"]) + BOOT_SEED_OFFSET
    for key, u in units.items():
        u["idx"] = resample_indices(unit_rng(seed, key), [n for _, n in u["members"]], n_boot)
        u["boot"] = _median(u["base"][u["idx"]], axis=1)
        u["point"] = _median(u["base"], axis=0)
    return {"n_boot": n_boot, "seed": seed, "units": units, "of": of, "sids": list(of)}


def boot_params(draws: dict, sid: int) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    """({param: (n_boot,) replicate medians}, {param: point median}) of one
    scenario; under a staged protocol the decision parameters of every
    scenario of a group are the group unit's arrays."""
    reps, point = {}, {}
    for name, key in draws["of"][sid].items():
        u = draws["units"][key]
        j = u["names"].index(name)
        reps[name], point[name] = u["boot"][:, j], float(u["point"][j])
    return reps, point


def replicate_values(prm: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """plugin_values over arrays of replicate medians: EVSI, EVPI, eff,
    EVSI*, eff*, C and the regime code (gate_regime_codes)."""
    evsi, evpi = model.voi(prm["p"], prm["s"], prm["t"], prm["B"], prm["K"])
    star = model.voi_fence(prm["p"], prm["s"], prm["t"], prm["B"], prm["K"])
    return {"EVSI": evsi, "EVPI": evpi, "eff": evsi / prm["C"], "EVSI_star": star,
            "eff_star": star / prm["C"], "C": prm["C"],
            "regime": gate_regime_codes(prm["p"], prm["s"], prm["t"], prm["B"], prm["K"])}


def rank_replicates(values: np.ndarray, point: np.ndarray) -> dict:
    """Ranks (1 = largest, ties averaged, as average_ranks) of every
    replicate row of values (n_boot, n) and of the point (n,), and the
    per-replicate Spearman with the point ranking (the Pearson correlation of
    the average ranks; NaN for a constant replicate)."""
    ranks = rankdata(-values, axis=1, method="average")
    pranks = average_ranks(point)
    rc = ranks - ranks.mean(axis=1, keepdims=True)
    pc = pranks - pranks.mean()
    den = np.sqrt((rc**2).sum(axis=1) * (pc**2).sum())
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = np.where(den > 0.0, (rc @ pc) / den, np.nan)
    return {"ranks": ranks, "point": pranks, "rho": rho}


def plugin_bootstrap(con, run, n_boot: int = N_BOOT, draws: dict | None = None) -> dict | None:
    """Intervals for the plug-in point from the bootstrap over elicitations
    (bootstrap_draws; the draws are passed in when another analysis shares
    them). Per scenario (the run's ranking order, those with a complete
    plug-in point): "point" (plugin_values at the pooled medians, equal to
    plugin_point), q05/q50/q95 of EVSI, C, eff and eff* over the replicates
    (quantiles, over finite values), "p_gate" (P_boot(gate): the share of
    replicates in the gate), and per ranking ("eff" plug-in, "eff_star"
    fence) the point rank and the median, q05 and q95 of the replicate rank
    (observed ranks, inverted_cdf) and P(rank <= BOOT_TOP_K). Headline:
    "top1" (the unique largest point eff, None when absent or tied),
    "top1_stable" (share of replicates where it ranks 1), "rho_eff" /
    "rho_fence" (median over replicates of the Spearman between the
    replicate ranking and the point ranking; None when undefined). None
    when no scenario has a complete plug-in point."""
    draws = draws or bootstrap_draws(con, run, n_boot)
    sids = draws["sids"]
    if not sids:
        return None
    rows, reps = {}, {"eff": [], "eff_star": []}
    for sid in sids:
        prm, med = boot_params(draws, sid)
        rv = replicate_values(prm)
        rows[sid] = {"point": plugin_values(med), "p_gate": float(np.mean(rv["regime"] == 0))}
        for key in ("EVSI", "C", "eff", "eff_star"):
            rows[sid][f"{key}_q"] = quantiles(rv[key])
        for key in reps:
            reps[key].append(rv[key])
    out = {"n_boot": draws["n_boot"], "seed": draws["seed"], "sids": sids, "rows": rows, "draws": draws}
    for key in ("eff", "eff_star"):
        point = np.array([rows[s]["point"][key] for s in sids])
        rr = rank_replicates(np.column_stack(reps[key]), point)
        for i, sid in enumerate(sids):
            col = rr["ranks"][:, i]
            q05, q50, q95 = np.quantile(col, Q3, method="inverted_cdf")   # observed ranks
            rows[sid][f"rank_{key}"] = {"point": float(rr["point"][i]), "q05": float(q05),
                                        "q50": float(q50), "q95": float(q95),
                                        "p_top": float(np.mean(col <= BOOT_TOP_K))}
        rho = rr["rho"][np.isfinite(rr["rho"])]
        out["rho_fence" if key == "eff_star" else "rho_eff"] = (
            float(np.median(rho)) if len(sids) >= 3 and rho.size and np.ptp(point) > 0.0 else None)
        if key == "eff":
            top = [i for i, v in enumerate(point) if v == point.max()]
            out["top1"] = sids[top[0]] if point.max() > 0.0 and len(top) == 1 else None
            out["top1_stable"] = (float(np.mean(rr["ranks"][:, top[0]] == 1.0))
                                  if out["top1"] is not None else None)
    return out


INTERVAL_DIGITS = 2           # significant digits of a printed bootstrap interval (the point carries 3)


def round_outward(v: float, digits: int, up: bool) -> float:
    """v rounded to `digits` significant digits toward +inf (up) or -inf."""
    if v == 0.0:
        return 0.0
    e = math.floor(math.log10(abs(v))) - digits + 1
    scaled = round(v * 10 ** -e if e < 0 else v / 10 ** e, 9)   # 5.9 / 0.1 is 59.000000000000007
    return float(f"{math.ceil(scaled) if up else math.floor(scaled)}e{e}")


def interval(q) -> str:
    """'[q05, q95]' of a quantile triple (quantiles), '--' when undefined:
    INTERVAL_DIGITS significant digits, q05 rounded down and q95 up so the
    printed interval contains the computed one, without exponent notation
    at any magnitude (plain)."""
    lo, hi = q[0], q[-1]
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return "--"
    return (f"[{plain(round_outward(float(lo), INTERVAL_DIGITS, up=False))},"
            f" {plain(round_outward(float(hi), INTERVAL_DIGITS, up=True))}]")


def rank_cell(v: float) -> str:
    return f"{v:g}"


def write_plugin_ranks(con, run, out: Path, pb: dict | None = None, prefix: str = MACRO_PREFIX) -> bool:
    """plugin_ranks.tex (a longtable, label tab:plugin-ranks, plus a summary
    tabular) and the \\voiBoot* macros in macros_extra.tex (merged)."""
    pb = pb or plugin_bootstrap(con, run)
    if pb is None:
        return False
    rows = pb["rows"]
    order = sorted(pb["sids"], key=lambda s: (rows[s]["rank_eff"]["point"],
                                              rows[s]["rank_eff_star"]["point"], s))
    lines = []
    for sid in order:
        cells = [str(sid)]
        for key in ("rank_eff", "rank_eff_star"):
            r = rows[sid][key]
            cells += [rank_cell(r["point"]), rank_cell(r["q50"]),
                      f"[{rank_cell(r['q05'])}, {rank_cell(r['q95'])}]", num(r["p_top"], "{:.2f}")]
        lines.append(" & ".join(cells))
    k = BOOT_TOP_K
    header = (r" & \multicolumn{4}{c}{plug-in eff} & \multicolumn{4}{c}{fence eff$^\star$}\\"
              r" \cmidrule(lr){2-5}\cmidrule(lr){6-9}"
              + " id" + f" & point & median & [q05, q95] & $P(\\le {k})$" * 2)
    table = longtable(
        "@{}rrrrrrrrr@{}", header, lines,
        r"Rank stability of the plug-in and fence rankings under the bootstrap over elicitations:"
        f" {pb['n_boot']} replicates (seed {pb['seed']}, the run's seed $+$ {BOOT_SEED_OFFSET:,}"
        r"), each resampling every scenario's valid elicitations of the run's members with"
        r" replacement within each member (keeping each member's count; a staged protocol's"
        r" decision stage once per group, shared by the group's scenarios) and recomputing the"
        r" pooled medians, EVSI and EVSI$^\star$ at them. Per ranking (rank 1 the largest,"
        r" ties averaged): the rank at the point (the pooled medians of all elicitations), the"
        r" median and q05--q95 of the replicate rank, and the share of replicates in which the"
        f" scenario ranks in the top {k}. Rows in the point plug-in order.",
        tex_label("tab:plugin-ranks", prefix))
    top = pb["top1"]
    summary = tabular("@{}lr@{}", "statistic & value", [
        f"bootstrap replicates (seed) & {pb['n_boot']} ({pb['seed']})",
        "top-1 by plug-in eff stays top-1 & "
        + ("--" if top is None else f"{num(pb['top1_stable'], '{:.2f}')} (id {top})"),
        r"median Spearman $\rho$(replicate, point), plug-in eff & " + num(pb["rho_eff"], "{:.2f}"),
        r"median Spearman $\rho$(replicate, point), fence eff$^\star$ & " + num(pb["rho_fence"], "{:.2f}"),
    ], "bootstrap over elicitations: stability of the point rankings of the table above")
    _write(out, "plugin_ranks.tex", table + "\\par\\medskip\n" + summary)
    write_macros(out, {
        "voiBootN": pb["n_boot"],
        "voiBootTopOneId": "--" if top is None else top,
        "voiBootTopOneStable": num(pb["top1_stable"], "{:.2f}"),
        "voiBootRhoEff": num(pb["rho_eff"], "{:.2f}"),
        "voiBootRhoFence": num(pb["rho_fence"], "{:.2f}"),
    }, merge=True, prefix=prefix)
    return True


def ladder_bootstrap(draws: dict, rungs: list[tuple[float, int]]) -> dict[int, dict] | None:
    """ladder_plugin per bootstrap replicate: p, B, K the median over the
    resampled rows of the rungs' distinct units, each once (a staged
    protocol's rungs share their group's decision unit, so they read one
    resample per replicate, and a ladder spanning two groups pools the two
    groups' resamples; a single-stage ladder pools the rungs' own resamples,
    as ladder_plugin pools their elicitations), s, t, C the rung's own
    resampled median.
    {sid: {"EVSI", "C"}: (n_boot,) arrays, "point": {"EVSI", "C"} at the
    rows themselves, equal to ladder_plugin's}; None when a rung has no
    complete plug-in point."""
    sids = [sid for _, sid in rungs]
    if any(sid not in draws["of"] for sid in sids):
        return None
    shared, shared_pt = {}, {}
    for name in SHARED_PARAMS:
        keys = list(dict.fromkeys(draws["of"][sid][name] for sid in sids))
        cols, pts = [], []
        for key in keys:
            u = draws["units"][key]
            j = u["names"].index(name)
            cols.append(u["base"][:, j][u["idx"]])
            pts.append(u["base"][:, j])
        shared[name] = _median(np.concatenate(cols, axis=1), axis=1)
        shared_pt[name] = float(_median(np.concatenate(pts), axis=0))
    out = {}
    for sid in sids:
        prm, med = boot_params(draws, sid)
        evsi, _ = model.voi(shared["p"], prm["s"], prm["t"], shared["B"], shared["K"])
        pt, _ = model.voi(shared_pt["p"], med["s"], med["t"], shared_pt["B"], shared_pt["K"])
        out[sid] = {"EVSI": evsi, "C": prm["C"], "point": {"EVSI": float(pt), "C": med["C"]}}
    return out


def boot_step_stats(lo: dict, hi: dict) -> dict:
    """Bootstrap of one step's plug-in marginal: q05/q95 of dEVSI / dC over
    the replicates with dC != 0, P(dEVSI > dC), P(dC > 0) and P(dC < 0)
    (over all replicates; the medians of few elicitations tie, so dC == 0
    takes the rest)."""
    d_evsi, d_c = hi["EVSI"] - lo["EVSI"], hi["C"] - lo["C"]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(d_c != 0.0, d_evsi / d_c, np.nan)
    q = quantiles(ratio)
    return {"meff_plug_q05": float(q[0]), "meff_plug_q95": float(q[2]),
            "p_pays_plug": float(np.mean(d_evsi > d_c)), "p_dc_pos_plug": float(np.mean(d_c > 0.0)),
            "p_dc_neg_plug": float(np.mean(d_c < 0.0))}


BOOT_STEP_NAN = dict.fromkeys(("meff_plug_q05", "meff_plug_q95", "p_pays_plug", "p_dc_pos_plug",
                               "p_dc_neg_plug"), float("nan"))


def sign_unstable(step: dict) -> bool:
    """dC takes each sign in at least BOOT_SIGN_FLAG of the replicates with
    dC != 0 (the ones the ratio's q05-q95 are taken over); a tie dC == 0
    counts as neither sign."""
    pos, neg = step["p_dc_pos_plug"], step["p_dc_neg_plug"]
    nonzero = pos + neg
    return bool(np.isfinite(nonzero) and nonzero > 0.0 and min(pos, neg) / nonzero >= BOOT_SIGN_FLAG)


# --- driver -------------------------------------------------------------------

# analyses defined on the binary parameters (p, B, K shared per ladder; p50
# dispersion of p, s, t, B, K, C; per-member re-draws through model.voi; the
# EVPI/C ranking; the plug-in point through model.voi): a Gaussian run skips
# them with a printed reason
BINARY_ONLY = ("level_uplift", "level_fence", "consistency", "member_agreement", "simplicity", "plugin",
               "plugin_map", "plugin_ranks")
NOT_BINARY = "defined on the binary parameters; the run is a Gaussian-state protocol"
NO_PLUGIN_POINT = "no ranked scenario has a valid elicitation of every parameter"


def skip_reasons(con, run, uplift: dict, plugin: tuple | None = None) -> dict[str, str]:
    """Why an analysis (or one of its ladders) does not apply to this run.
    plugin: the (stats, reason) pair of plugin_analysis, computed here when
    not passed (the replay behind it is the costliest step of the module).
    plugin_map and plugin_ranks need a ranked scenario with a complete
    plug-in point (the bootstrap is defined exactly there)."""
    if run_kind(con, run["id"]) == db.GAUSSIAN_KIND:
        reasons = dict.fromkeys(BINARY_ONLY, NOT_BINARY)
        if not scenario_domains(con):
            reasons["domain_map"] = "no scenario carries attributes.risk_domain"
        return reasons
    reasons = {f"level_uplift ({g})": why for g, why in uplift["skipped"].items()}
    if not uplift["steps"]:
        reasons["level_uplift"] = "no ladder (a group of >= 2 ranked levels sharing one decision text)"
    if not any(s in scenario_levels(con) for s in ranked_ids(con, run["id"])):
        reasons["level_fence"] = "no ranked scenario carries a numeric attributes.level"
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
    if not plugin_map_points(con, run):
        reasons["plugin_map"] = reasons["plugin_ranks"] = NO_PLUGIN_POINT
    return reasons


def make_all(con, run, out: Path, prefix: str = MACRO_PREFIX,
             n_boot: int = N_BOOT) -> tuple[list[str], list[str]]:
    """Write every analysis that applies, macros under `prefix`, the
    bootstrap over elicitations drawn once with n_boot replicates and shared
    by plugin.tex, plugin_ranks.tex, the plug-in map and the level uplift.
    Returns (written file names, skipped analysis names); a skipped analysis
    has its stale outputs removed and its reason printed (as is every ladder
    the level uplift leaves out)."""
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(STYLE)
    binary = run_kind(con, run["id"]) == db.BINARY_KIND
    draws = bootstrap_draws(con, run, n_boot) if binary else None
    pb = plugin_bootstrap(con, run, draws=draws) if binary else None
    uplift = level_uplift_analysis(con, run, draws) if binary else {"steps": {}, "skipped": {}}
    plugin = plugin_analysis(con, run) if binary else (None, NOT_BINARY)
    for what, why in skip_reasons(con, run, uplift, plugin).items():
        print(f"{what}: skipped: {why}")
    mr_needed = binary and len(run_members(con, run)) > 1
    # simplicity before plugin: both write MACROS_FILE, the first afresh, the
    # second merging its macros in (so a skipped simplicity leaves the plugin
    # macros alone and a skipped plugin never removes the simplicity ones)
    plan = [
        ("level_uplift", lambda: binary and fig_level_uplift(con, run, out, uplift)
         and write_level_uplift(con, run, out, uplift)),
        ("level_fence", lambda: binary and fig_level_fence(con, run, out)),
        ("consistency", lambda: binary and fig_within_group_consistency(con, run, out)
         and write_consistency(con, run, out)),
        ("domain_map", lambda: fig_domain_map(con, run, out) and write_domain_summary(con, run, out)),
        ("member_agreement", lambda: mr_needed and fig_member_agreement(con, run, out)
         and write_member_agreement(con, run, out)),
        ("simplicity", lambda: binary and write_simplicity(con, run, out, prefix)),
        ("plugin", lambda: binary and plugin[0] is not None
         and fig_plugin(con, run, out, plugin[0]) and write_plugin(con, run, out, plugin[0], prefix, pb)),
        ("plugin_map", lambda: binary and fig_plugin_map(con, run, out, pb=pb)),
        ("plugin_ranks", lambda: pb is not None and write_plugin_ranks(con, run, out, pb, prefix)),
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


def boot_count(text: str) -> int:
    """--boot: a replicate count of at least 2 (a quantile over one replicate
    is not an interval)."""
    try:
        n = int(text)
    except ValueError:
        n = 0
    if n < 2:
        raise argparse.ArgumentTypeError(f"--boot takes an integer >= 2, got {text!r}")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    add_run_args(ap)
    add_tag_arg(ap)
    ap.add_argument("--boot", type=boot_count, default=N_BOOT,
                    help=f"replicates of the bootstrap over elicitations (default {N_BOOT})")
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    out, prefix = study.tagged(args.tag)
    con = study.connect()
    run = select_run(con, args.run, args.protocol, db.parse_member_labels(args.members), args.weights)
    written, skipped = make_all(con, run, out, prefix, args.boot)
    for name in written:
        print(f"wrote {out / name}")
    if skipped:
        print("skipped (inputs absent): " + ", ".join(skipped))


if __name__ == "__main__":
    main()
