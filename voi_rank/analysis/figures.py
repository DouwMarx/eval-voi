"""All report figures (spec §8), reading only from a study's voi.db. PDFs land
in <study>/report/generated/ (generated/TAG/ with --tag TAG; study.Study.tagged).

Usage: python -m voi_rank.analysis.figures --study studies/business [--protocol p001] [--run ID]
       [--members claude_cli:sonnet,claude_cli:opus] [--weights equal-member] [--tag NAME]
(default: the latest all-member pooled run of protocol p001; --members selects
the latest run of the protocol that pooled exactly that member subset,
--weights the latest with that mixture weighting (mc --weights); --run
overrides them. Every figure reads the run's members only.)
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import matplotlib.transforms  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import gaussian_kde  # noqa: E402

from voi_rank import db, mc  # noqa: E402
from voi_rank.fit import FAMILY_BY_PARAM, GAUSS_LOG_PARAMS, GAUSS_USD_PARAMS  # noqa: E402
from voi_rank.study import Study, add_study_arg, add_tag_arg  # noqa: E402

ACCENT = "#0072B2"          # single hue for single-series marks
INTERVAL = "#9aa5b1"        # recessive interval lines
# Okabe-Ito, fixed order, CVD-safe (used only where several series need identity)
CATEGORICAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7",
               "#56B4E9", "#F0E442", "#000000"]

FIG_W = 5.5                 # CoRL text width (in): the paper figures are drawn at it, fonts at print size
MIN_FONT = 6.5              # the smallest text of a paper figure (pt)
FLOOR_LABEL = "0"           # tick label of a data-driven floor (data_floor): the zero row
FLOOR_TICK_GAP = 0.2        # inches between the decade labels of a floor axis (floor_axis)

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


# --- shared readers ---------------------------------------------------------

def metric_rows(con, run_id: int, metric: str) -> dict[int, dict]:
    return {r["scenario_id"]: dict(r) for r in con.execute(
        "SELECT * FROM results WHERE run_id=? AND metric=?", (run_id, metric))}


def titles(con) -> dict[int, str]:
    return {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}


def run_kind(con, run_id: int) -> str:
    """Model kind of the protocol behind a run: 'binary' or 'gaussian'."""
    return db.run_model_kind(con, db.get_run(con, run_id))


def run_param_names(con, run_id: int) -> list[str]:
    """The parameter rows the run's protocol stores (db.param_names of its kind)."""
    return db.param_names(run_kind(con, run_id))


def run_sensitivity_names(con, run_id: int) -> list[str]:
    """The parameters the run stores sensitivities for (db.sensitivity_names of
    its kind: the ones that enter its primary metric)."""
    return db.sensitivity_names(run_kind(con, run_id))


def primary_metric(con, run_id: int) -> str:
    """The run's ranking metric: 'efficiency' (binary) or 'eff_step' (gaussian)."""
    return db.primary_metric(run_kind(con, run_id))


def evsi_metric(con, run_id: int) -> str:
    return db.evsi_metric(run_kind(con, run_id))


def log_scale(name: str) -> bool:
    """Parameters plotted on a log axis: USD amounts and the positive
    Gaussian scales (sigma0, x)."""
    return FAMILY_BY_PARAM.get(name) == "lognormal" or name in GAUSS_LOG_PARAMS


def usd_param(name: str) -> bool:
    return FAMILY_BY_PARAM.get(name) == "lognormal" or name in GAUSS_USD_PARAMS


# mathtext labels of the stored parameter names (the binary names are their own)
MATH_LABEL = {
    "g_mu0": r"\mu_0", "g_sigma0": r"\sigma_0", "g_d": "d", "g_x": "x", "g_k": "k", "g_L": "L",
    "g_kappa_sigma0": r"\kappa\sigma_0", "g_B": "B", "g_K": "K", "g_sigma_b_rel": r"\sigma_b/\sigma_0",
}


def esc_math(name: str) -> str:
    return MATH_LABEL.get(name, name)


def ranked_ids(con, run_id: int) -> list[int]:
    """Scenario ids ordered by the run's median primary efficiency (desc),
    tie-break p_positive."""
    eff = metric_rows(con, run_id, primary_metric(con, run_id))
    return sorted(eff, key=lambda s: (-(eff[s]["q50"] or 0.0),
                                      -(eff[s]["p_positive"] or 0.0), s))


def scenario_groups(con) -> dict[int, str | None]:
    return {r["id"]: r["grp"] for r in con.execute("SELECT id, grp FROM scenarios")}


def group_colors(groups: list[str]) -> dict[str, str]:
    return {g: CATEGORICAL[i % len(CATEGORICAL)] for i, g in enumerate(groups)}


def c_quantiles(con, run, sid) -> tuple[float, float, float]:
    """(q05, q50, q95) of C: the run's stored C mixture quantiles (results
    metric 'C'), else, for pre-v2 runs without that row, the pooled elicited
    percentiles (medians of p5/p50/p95 over valid elicitations)."""
    r = con.execute("SELECT q05, q50, q95 FROM results WHERE run_id=? AND scenario_id=?"
                    " AND metric='C'", (run["id"], sid)).fetchone()
    if r is not None:
        return r["q05"], r["q50"], r["q95"]
    rows = con.execute(
        "SELECT p.p5, p.p50, p.p95 FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.scenario_id=? AND e.protocol_id=? AND e.valid=1 AND p.name='C'",
        (sid, run["protocol_id"])).fetchall()
    arr = np.array([[x["p5"], x["p50"], x["p95"]] for x in rows], dtype=float)
    return tuple(float(v) for v in np.median(arr, axis=0))


def run_members(con, run) -> list[dict]:
    """The members the run pooled (the protocol's, or the stored subset)."""
    return db.run_members(con, run)


def add_run_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--protocol", default="p001",
                    help="use the latest run of this protocol (default: p001)")
    ap.add_argument("--run", type=int, default=None, help="explicit run id (overrides --protocol)")
    ap.add_argument("--members", default=None,
                    help="comma-separated provider:model subset: use the latest run of the protocol"
                         " that pooled exactly these members (default: the all-member run)")
    ap.add_argument("--weights", choices=db.WEIGHT_CHOICES, default=db.WEIGHTS_POOLED,
                    help="use the latest run with this mixture weighting (default: pooled)")


def run_description(con, run) -> str:
    """'run <id> (protocol <name>)', plus ', members a, b' for a subset run
    and ', weights equal-member' for an equal-member run."""
    prot = con.execute("SELECT name FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    name = prot["name"] if prot else "unknown"
    labels = db.run_member_labels(run)
    return (f"run {run['id']} (protocol {name}" + (f", members {', '.join(labels)}" if labels else "")
            + (f", weights {db.run_weights(run)}" if db.run_weights(run) else "") + ")")


def select_run(con, run_id: int | None, protocol: str, members: list[str] | None = None,
               weights: str | None = None):
    """The run to analyse: --run when given, else the latest run of the
    protocol that pooled exactly `members` (labels; None = every member)
    with the mixture weighting `weights` (None or 'pooled' = pooled). A
    run made by the v1 model (no data_hash, or sensitivities for the retired
    parameter e) is refused: its numbers contradict the v2 commentary and
    its draws do not replay. Prints 'run <id> (protocol <name>[, members
    ...][, weights ...])'."""
    run = (db.get_run(con, run_id) if run_id is not None
           else db.latest_run(con, protocol, members, weights))
    prot = con.execute("SELECT name FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    name = prot["name"] if prot else "unknown"
    reason = db.run_predates_v2(con, run)
    if reason:
        raise RuntimeError(f"run {run['id']} (protocol {name}) predates the v2 model: {reason};"
                           f" run `python -m voi_rank.mc --protocol {name}` first")
    print(run_description(con, run))
    return run


# --- zero floors and labels (the paper figures) -----------------------------

def data_floor(values) -> float:
    """The log-axis floor at which a figure draws its zero values: the decade
    at or below a tenth of the smallest positive finite value, so one empty
    decade (at least, and less than two) separates the zero row from the
    data; 1.0 when no value is positive. Non-positive, NaN and None values
    are ignored."""
    v = np.concatenate([np.ravel(np.asarray(x, dtype=float)) for x in values if x is not None]
                       or [np.empty(0)])
    v = v[np.isfinite(v) & (v > 0.0)]
    if not v.size:
        return 1.0
    return 10.0 ** (math.floor(math.log10(float(v.min()))) - 1)


class FloorFormatter(matplotlib.ticker.LogFormatterSciNotation):
    """Decade labels, with the floor's tick labelled FLOOR_LABEL."""

    def __init__(self, floor: float, label: str = FLOOR_LABEL):
        super().__init__()
        self.floor, self.label = floor, label

    def __call__(self, x, pos=None):
        return self.label if math.isclose(x, self.floor, rel_tol=1e-9) else super().__call__(x, pos)


def floor_axis(ax, floor: float, axis: str = "y", top: float | None = None) -> None:
    """A log axis whose lowest tick is the zero row at `floor`: the limit
    sits 0.35 decade below it, the tick reads FLOOR_LABEL, and a '//' break
    on the spine in the empty decade above it says the axis is not
    continuous there. `top` sets the upper limit (default: kept). The
    decades above the floor are labelled every `stride` decades, so labels
    stay FLOOR_TICK_GAP inches apart on a short axis (every decade keeps a
    minor tick)."""
    getattr(ax, f"set_{axis}scale")("log")
    lo, hi = getattr(ax, f"get_{axis}lim")()
    hi = hi if top is None else top
    getattr(ax, f"set_{axis}lim")(floor / 10.0**0.35, hi)
    k0, k1 = round(math.log10(floor)) + 1, math.floor(math.log10(hi))
    box = ax.get_position()
    length = (box.height * ax.figure.get_figheight() if axis == "y" else box.width * ax.figure.get_figwidth())
    stride = max(1, math.ceil((k1 - k0 + 1) / max(1, int(length / FLOOR_TICK_GAP))))
    decades = [10.0**k for k in range(k1, k0 - 1, -stride)]   # anchored at the top decade
    ax_obj = getattr(ax, f"{axis}axis")
    ax_obj.set_major_locator(matplotlib.ticker.FixedLocator([floor, *sorted(decades)]))
    ax_obj.set_minor_locator(matplotlib.ticker.FixedLocator([10.0**k for k in range(k0, k1 + 1)]))
    ax_obj.set_major_formatter(FloorFormatter(floor))
    ax_obj.set_minor_formatter(matplotlib.ticker.NullFormatter())
    at = floor * 10.0**0.5
    if axis == "y":
        trans = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)
        xy, mk = (0.0, at), [(-1.0, -0.5), (1.0, 0.5)]
    else:
        trans = matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes)
        xy, mk = (at, 0.0), [(-0.5, -1.0), (0.5, 1.0)]
    for d in (-1.2, 1.2):
        shift = matplotlib.transforms.ScaledTranslation(0.0 if axis == "y" else d / 72.0,
                                                        d / 72.0 if axis == "y" else 0.0,
                                                        ax.figure.dpi_scale_trans)
        ax.plot(*xy, marker=mk, ms=5, mew=0.8, color="#333333", ls="", clip_on=False,
                transform=trans + shift, zorder=5, gid="floor_break")


# candidate label offsets (points) and alignments, tried in order
LABEL_OFFSETS = ((3.5, 2.0, "left", "bottom"), (-3.5, 2.0, "right", "bottom"),
                 (3.5, -2.0, "left", "top"), (-3.5, -2.0, "right", "top"),
                 (0.0, 4.5, "center", "bottom"), (0.0, -4.5, "center", "top"),
                 (5.0, 0.0, "left", "center"), (-5.0, 0.0, "right", "center"),
                 (7.0, 6.0, "left", "bottom"), (-7.0, 6.0, "right", "bottom"),
                 (7.0, -6.0, "left", "top"), (-7.0, -6.0, "right", "top"))


LABEL_PAD = 1.5         # points of clearance around a placed label ('1' touching '5' reads as '15')
LABEL_AMBIGUITY = 0.7   # a label nearer than this ratio to another point than to its own is ambiguous


def place_labels(ax, xy, texts, marker_pt: float = 5.5, others=(), avoid=(), fontsize: float = MIN_FONT,
                 color: str = "#333333", gid: str = "id_label") -> list:
    """Label each data point xy[i] with texts[i] at the candidate offset
    (LABEL_OFFSETS) that overlaps least with every point's marker (a square
    of marker_pt points; `others` adds the data points of other markers),
    the labels placed before it, the extents of the artists in `avoid` and
    the area outside the axes, and that is clearly nearer its own point than
    any other (LABEL_AMBIGUITY; a greedy heuristic, no dependency; the most
    crowded points are labelled first). Call it once the limits, scales and layout are final;
    the labels stay out of the layout. Returns the annotations in the
    order of xy."""
    fig = ax.figure
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    data = np.asarray(xy, dtype=float).reshape(-1, 2)
    pts = ax.transData.transform(data)
    more = ax.transData.transform(np.asarray(others, dtype=float).reshape(-1, 2))
    px = fig.dpi / 72.0
    half = marker_pt / 2.0 * px
    boxes = [np.array([x - half, y - half, x + half, y + half]) for x, y in np.vstack([pts, more])]
    for a in avoid:
        e = a.get_window_extent(renderer)
        boxes.append(np.array([e.x0, e.y0, e.x1, e.y1]))
    fr = ax.get_window_extent(renderer)
    frame = np.array([fr.x0, fr.y0, fr.x1, fr.y1])

    def overlap(b, o):
        return max(0.0, min(b[2], o[2]) - max(b[0], o[0])) * max(0.0, min(b[3], o[3]) - max(b[1], o[1]))

    dist = np.hypot(*(pts[:, None, :] - pts[None, :, :]).transpose(2, 0, 1))
    crowd = (dist < 20.0 * px).sum(axis=1)
    out: list = [None] * len(pts)
    for i in sorted(range(len(pts)), key=lambda k: -crowd[k]):
        ann = ax.annotate(texts[i], tuple(data[i]), textcoords="offset points", xytext=(0, 0),
                          fontsize=fontsize, color=color, zorder=4, gid=gid, annotation_clip=False)
        ann.set_in_layout(False)
        best = None
        for dx, dy, ha, va in LABEL_OFFSETS:
            ann.set_position((dx, dy))
            ann.set_ha(ha)
            ann.set_va(va)
            e = ann.get_window_extent(renderer)
            b = np.array([e.x0, e.y0, e.x1, e.y1])
            area = (b[2] - b[0]) * (b[3] - b[1])
            centre = np.array([(b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0])
            d = np.hypot(*(pts - centre).T)
            ambiguous = bool(len(pts) > 1 and d[i] > LABEL_AMBIGUITY * np.delete(d, i).min())
            cost = (sum(overlap(b, o) for o in boxes) + 4.0 * (area - overlap(b, frame))
                    + 0.5 * area * ambiguous)
            if best is None or cost < best[0] - 1e-9:
                best = (cost, (dx, dy, ha, va), b)
        dx, dy, ha, va = best[1]
        ann.set_position((dx, dy))
        ann.set_ha(ha)
        ann.set_va(va)
        boxes.append(best[2] + np.array([-1.0, -1.0, 1.0, 1.0]) * LABEL_PAD * px)
        out[i] = ann
    return out


# --- figures ----------------------------------------------------------------

def fig_ranking(con, run_id, out: Path):
    """The top 25 by median efficiency with q05-q95 bars; a zero value sits
    in the zero column at the data-driven floor (data_floor of the plotted
    quantiles), a zero median as an open marker."""
    metric = primary_metric(con, run_id)
    eff = metric_rows(con, run_id, metric)
    order = ranked_ids(con, run_id)[:25]
    ttl = titles(con)
    q = np.array([[eff[s][k] or 0.0 for k in ("q05", "q50", "q95")] for s in reversed(order)])
    floor = data_floor(q)
    fig, ax = plt.subplots(figsize=(FIG_W, 0.24 * len(order) + 0.9))
    ys = np.arange(len(order))
    qf = np.maximum(q, floor)
    ax.hlines(ys, qf[:, 0], qf[:, 2], color=INTERVAL, lw=1.4)
    zero = q[:, 1] < floor
    ax.plot(qf[~zero, 1], ys[~zero], "o", color=ACCENT, ms=4.5)
    ax.plot(qf[zero, 1], ys[zero], "o", mfc="white", mec=ACCENT, ms=4.5, mew=0.8)
    ax.axvline(1.0, color="#555555", lw=0.8, ls="--")
    ax.text(1.35, len(order) - 0.35, "EVSI = C", fontsize=MIN_FONT, color="#555555",
            rotation=90, va="top")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{sid} · {ttl[sid][:52]}" for sid in reversed(order)], fontsize=MIN_FONT)
    if (q < floor).any():
        floor_axis(ax, floor, "x", top=max(qf.max(), 1.0) * 3.0)
        ax.axvspan(ax.get_xlim()[0], floor * 10.0**0.5, color="#f3f3f3", lw=0, zorder=0.4)
    else:
        ax.set_xscale("log")
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xlabel(f"{metric} = {evsi_metric(con, run_id)} / C (log scale)", fontsize=8)
    fig.suptitle(f"Ranking by median {metric}" + (" (open: median 0)" if zero.any() else ""), fontsize=8.5)
    ax.grid(axis="y", visible=False)
    fig.savefig(out / "fig_ranking.pdf")
    plt.close(fig)
    return True


def fig_evsi_vs_cost(con, run_id, out: Path):
    """Headline figure: median EVSI vs the run's median C (the same pooled
    cost mixture the efficiency ranking divides by, so the iso-efficiency
    diagonals agree with the ranking table), log-log, with thin q05-q95 EVSI
    bars, points coloured by scenario group when the study has groups,
    iso-efficiency diagonals and the top 10 labelled by id. A zero median
    sits in the zero row at the data-driven floor (data_floor of the plotted
    medians and q05s), as an open marker."""
    evsi_name = evsi_metric(con, run_id)
    evsi = metric_rows(con, run_id, evsi_name)
    order = ranked_ids(con, run_id)
    run = db.get_run(con, run_id)
    groups = scenario_groups(con)
    xs = np.array([c_quantiles(con, run, s)[1] for s in order])
    y50 = np.array([evsi[s]["q50"] or 0.0 for s in order])
    y05 = np.array([evsi[s]["q05"] or 0.0 for s in order])
    y95 = np.array([evsi[s]["q95"] or 0.0 for s in order])
    floor = data_floor([y50, y05])
    floored = y50 < floor
    zero_row = bool((y05 < floor).any())
    y50f = np.maximum(y50, floor)
    lo = np.maximum(y05, floor)
    hi = np.maximum(y95, floor)

    fig, ax = plt.subplots(figsize=(FIG_W, 3.6))
    ax.vlines(xs, lo, hi, color=INTERVAL, lw=0.6, alpha=0.75, zorder=1)
    grp_of = [groups.get(s) for s in order]
    grp_names = sorted({g for g in grp_of if g})
    if grp_names:
        colors = group_colors(grp_names)
        series = [(g, np.array([x == g for x in grp_of]), colors[g]) for g in grp_names]
        rest = np.array([g is None for g in grp_of])
        if rest.any():
            series.append(("(no group)", rest, "#7f7f7f"))
    else:
        series = [(None, np.ones(len(order), dtype=bool), ACCENT)]
    for label, mask, color in series:
        m1 = mask & ~floored
        m0 = mask & floored
        ax.plot(xs[m1], y50f[m1], "o", color=color, ms=5, mec="white", mew=0.5,
                label=label, zorder=3)
        ax.plot(xs[m0], y50f[m0], "o", mfc="white", mec=color, ms=5, mew=0.8, zorder=3)
    ax.set_xscale("log")
    xlim = np.array([xs.min() / 3, xs.max() * 3])
    top = max(hi.max(), floor) * 10.0**1.3
    ax.set_xlim(*xlim)
    if zero_row:
        floor_axis(ax, floor, "y", top=top)
        ax.axhspan(ax.get_ylim()[0], floor * 10.0**0.5, color="#f3f3f3", lw=0, zorder=0.5)
        label_lo = floor * 10.0
    else:
        ax.set_yscale("log")
        label_lo = lo.min() / 10.0**0.5
        ax.set_ylim(label_lo, top)
    ylim = np.array([label_lo, top])
    for k in range(-2, 4):
        ax.plot(xlim, 10.0**k * xlim, ls="--", lw=0.7, color="#c9c9c9", zorder=0)
        x_lab = min(xlim[1] * 0.55, ylim[1] * 0.35 / 10.0**k)
        y_lab = 10.0**k * x_lab
        if xlim[0] * 1.5 < x_lab and ylim[0] * 3 < y_lab < ylim[1] * 0.7:
            p0 = ax.transData.transform((x_lab, y_lab))
            p1 = ax.transData.transform((x_lab * 2, y_lab * 2))
            angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
            ax.text(x_lab, y_lab * 1.25, f"eff $= 10^{{{k}}}$", fontsize=MIN_FONT,
                    color="#8a8a8a", rotation=angle, rotation_mode="anchor")
    arrow = ax.annotate("better\n(more decision value per dollar)",
                        xy=(0.03, 0.97), xytext=(0.12, 0.84),
                        xycoords="axes fraction", textcoords="axes fraction",
                        fontsize=MIN_FONT, color="#333333", ha="left", va="top",
                        arrowprops={"arrowstyle": "-|>", "color": "#333333", "lw": 0.9})
    handles = ax.get_legend_handles_labels()[0] if grp_names else []
    if floored.any():
        handles.append(plt.Line2D([], [], marker="o", ls="", mfc="white", mec="#555555",
                                  label="open: median EVSI = 0"))
    if handles:
        ax.legend(handles=handles, fontsize=MIN_FONT, loc="upper left", bbox_to_anchor=(1.02, 1.0),
                  borderaxespad=0.0, frameon=False, title="group" if grp_names else None,
                  title_fontsize=MIN_FONT, alignment="left")
    ax.set_xlabel("median C (run mixture, USD)", fontsize=8)
    ax.set_ylabel(f"median {evsi_name} (USD)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title(f"Median {evsi_name} vs median cost (bars: q05–q95; top 10 labelled by id)", fontsize=8)
    top10 = min(10, len(order))
    place_labels(ax, np.column_stack([xs[:top10], y50f[:top10]]), [str(s) for s in order[:top10]],
                 marker_pt=5.0, others=np.column_stack([xs[top10:], y50f[top10:]]), avoid=[arrow])
    fig.savefig(out / "fig_evsi_vs_cost.pdf")
    plt.close(fig)
    return True


def param_median_points(con, run, names: list[str], rank_of: dict[int, int]) -> tuple[dict, list[str]]:
    """{param: {member label: [(rank, p50), ...]}} over the valid elicitations
    of the run's members, each at its scenario's rank. Under a staged
    protocol a decision-stage row sits on its group's representative (the
    group's lowest id), which a rename leaves retired without instrument
    rows and so unranked: the row is drawn at the rank of the group's
    lowest-id RANKED scenario instead, so no group's p, B, K vanish from the
    figure. A group none of whose scenarios is ranked is named in the
    returned notes rather than dropped silently."""
    clause, margs = db.member_filter(db.run_member_labels(run))
    rows = con.execute(
        "SELECT e.scenario_id, e.stage, e.provider || ':' || e.model AS member, p.name, p.p50"
        " FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        f" WHERE e.protocol_id=? AND e.valid=1{clause}", (run["protocol_id"], *margs)).fetchall()
    stages = db.protocol_stages(con.execute("SELECT * FROM protocols WHERE id=?",
                                            (run["protocol_id"],)).fetchone())
    gstage = db.group_stage(stages) if stages is not None else None
    anchor: dict[int, int | None] = {}   # representative id -> the group's lowest ranked id
    notes = []
    data: dict[str, dict[str, list]] = {n: {} for n in names}
    for r in rows:
        if r["name"] not in data:
            continue
        sid = r["scenario_id"]
        if gstage is not None and r["stage"] == gstage["name"]:
            if sid not in anchor:
                ranked = [g for g in db.scenario_group_ids(con, gstage["group_key"], sid) if g in rank_of]
                anchor[sid] = ranked[0] if ranked else None
                if not ranked:
                    row = con.execute("SELECT * FROM scenarios WHERE id=?", (sid,)).fetchone()
                    value = db.scenario_group_value(row, gstage["group_key"])
                    notes.append(f"group {value!r} (decision rows on scenario {sid}) has no ranked"
                                 f" scenario: its {', '.join(gstage['params'])} points are not drawn")
            sid = anchor[sid]
        if sid in rank_of:
            data[r["name"]].setdefault(r["member"], []).append((rank_of[sid], r["p50"]))
    return data, notes


def fig_param_medians(con, run_id, out: Path):
    """Six panels, one per parameter: the elicited p50 of every valid
    elicitation of the run's protocol against the scenario's efficiency rank
    (jittered strip; param_median_points places a staged protocol's
    decision rows), coloured by member model when the protocol has several
    members, with a marginal histogram on the right. Reveals round-number
    clustering and cross-model disagreement. USD panels on a log axis."""
    run = db.get_run(con, run_id)
    names = run_param_names(con, run_id)
    order = ranked_ids(con, run_id)
    rank_of = {sid: i + 1 for i, sid in enumerate(order)}
    members = [db.member_label(m) for m in run_members(con, run)]
    clause, margs = db.member_filter(db.run_member_labels(run))
    data, notes = param_median_points(con, run, names, rank_of)
    for note in notes:
        print(f"fig_param_medians: {note}")
    present = [m for m in members if any(m in data[n] for n in names)]
    present += sorted({m for n in names for m in data[n]} - set(present))
    multi = len(present) > 1
    colors = group_colors(present) if multi else {m: ACCENT for m in present}
    rng = np.random.default_rng(0)

    n_rows = (len(names) + 1) // 2
    fig = plt.figure(figsize=(6.2, 2.0 * n_rows + 0.8))
    gs = fig.add_gridspec(n_rows, 4, width_ratios=[4, 1.1, 4, 1.1])
    for i, name in enumerate(names):
        r, c = divmod(i, 2)
        ax = fig.add_subplot(gs[r, 2 * c])
        axh = fig.add_subplot(gs[r, 2 * c + 1], sharey=ax)
        usd = log_scale(name)
        prob = FAMILY_BY_PARAM.get(name) == "beta"
        allv = np.array([v for m in present for _, v in data[name].get(m, [])], dtype=float)
        if allv.size == 0 or (usd and allv.min() <= 0.0):
            ax.set_title(f"${esc_math(name)}$ (no data)")
            continue
        if usd:
            ax.set_yscale("log")
            bins = np.logspace(np.log10(allv.min()) - 0.05, np.log10(allv.max()) + 0.05, 28)
        elif prob:
            bins = np.linspace(0.0, 1.0, 26)
        else:
            # a data-driven linear range; near-constant values (repeats that agree) get a
            # pad of 5% of their magnitude so the axis never falls back to offset notation
            pad = 0.05 * max(allv.max() - allv.min(), 0.1 * float(np.abs(allv).max()), 1e-3)
            bins = np.linspace(allv.min() - pad, allv.max() + pad, 26)
            ax.set_ylim(bins[0], bins[-1])
            ax.ticklabel_format(axis="y", useOffset=False)
        for m in present:
            pts = data[name].get(m, [])
            if not pts:
                continue
            xr = np.array([p[0] for p in pts], dtype=float) + rng.uniform(-0.3, 0.3, len(pts))
            yv = np.array([p[1] for p in pts], dtype=float)
            ax.plot(xr, yv, ".", ms=3, alpha=0.55, color=colors[m], mec="none",
                    label=m if i == 0 else None)
            axh.hist(yv, bins=bins, orientation="horizontal", color=colors[m],
                     alpha=0.45 if multi else 0.8, histtype="stepfilled", lw=0)
        ax.set_title(f"${esc_math(name)}$" + (" (USD)" if usd_param(name) else ""), fontsize=9)
        ax.set_xlim(0.5, len(order) + 0.5)
        if prob:
            ax.set_ylim(-0.02, 1.02)
        if r == n_rows - 1:
            ax.set_xlabel("efficiency rank (best = 1)")
        ax.tick_params(labelsize=7)
        axh.tick_params(labelleft=False, labelbottom=False, length=0)
        axh.grid(visible=False)
        for side in ("top", "right", "bottom", "left"):
            axh.spines[side].set_visible(False)
    if multi:
        handles = [plt.Line2D([], [], marker="o", ls="", color=colors[m], label=m)
                   for m in present]
        fig.legend(handles=handles, loc="outside upper center", ncol=min(len(present), 3),
                   fontsize=7, frameon=False)
    n_elic = con.execute(f"SELECT COUNT(*) FROM elicitations e WHERE protocol_id=? AND valid=1{clause}",
                         (run["protocol_id"], *margs)).fetchone()[0]
    stages = db.protocol_stages(con.execute("SELECT * FROM protocols WHERE id=?",
                                            (run["protocol_id"],)).fetchone())
    staged = ""
    if stages is not None:   # decision rows sit on each group's representative: plotted once per group
        g = db.group_stage(stages)
        staged = (f"; ${', '.join(g['params'])}$ once per group, at the rank of its lowest-id"
                  f" ranked scenario (stage {g['name']})")
    fig.suptitle(f"Elicited medians per parameter, every valid elicitation of the run's members"
                 f" ({n_elic} elicitations{staged})", fontsize=8 if staged else 9)
    fig.savefig(out / "fig_param_medians.pdf")
    plt.close(fig)
    return True


def fig_by_level(con, run_id, out: Path):
    """Median EVSI, efficiency and C against attributes.level, with q05-q95
    intervals, grouped by grp. A panel with zero values draws them in a
    zero row at its data-driven floor (data_floor of the panel's plotted
    quantiles; open markers for a zero median). Skipped silently when no
    scenario carries a numeric level."""
    levels = {}
    for r in con.execute("SELECT * FROM scenarios"):
        lv = db.scenario_attributes(r).get("level")
        if isinstance(lv, (int, float)) and not isinstance(lv, bool):
            levels[r["id"]] = float(lv)
    order = [s for s in ranked_ids(con, run_id) if s in levels]
    if not order:
        return False
    run = db.get_run(con, run_id)
    groups = scenario_groups(con)
    grp_names = sorted({groups[s] or "(no group)" for s in order})
    colors = group_colors(grp_names)
    offsets = np.linspace(-0.18, 0.18, len(grp_names)) if len(grp_names) > 1 else [0.0]
    evsi_name, eff_name = evsi_metric(con, run_id), primary_metric(con, run_id)
    evsi = metric_rows(con, run_id, evsi_name)
    eff = metric_rows(con, run_id, eff_name)
    panels = [
        (f"median {evsi_name} (USD)", lambda s: (evsi[s]["q05"], evsi[s]["q50"], evsi[s]["q95"])),
        (f"{eff_name} = {evsi_name} / C", lambda s: (eff[s]["q05"], eff[s]["q50"], eff[s]["q95"])),
        ("cost C (USD)", lambda s: c_quantiles(con, run, s)),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(FIG_W, 2.3))
    any_open = False
    for ax, (ylabel, q_of) in zip(axes, panels, strict=True):
        q_all = np.nan_to_num(np.array([q_of(s) for s in order], dtype=float), nan=0.0)
        floor = data_floor(q_all)
        zero_row = bool((q_all < floor).any())
        top = float(np.max(q_all))
        for gi, g in enumerate(grp_names):
            sids = [s for s in order if (groups[s] or "(no group)") == g]
            if not sids:
                continue
            x = np.array([levels[s] for s in sids]) + offsets[gi]
            raw = np.nan_to_num(np.array([q_of(s) for s in sids], dtype=float), nan=0.0)
            q = np.maximum(raw, floor)
            ax.vlines(x, q[:, 0], q[:, 2], color=colors[g], lw=0.7, alpha=0.8, zorder=1)
            zero = raw[:, 1] < floor
            any_open |= bool(zero.any())
            ax.plot(x[~zero], q[~zero, 1], "o", ms=3.5, color=colors[g], mec="white", mew=0.4, zorder=3,
                    label=g)
            ax.plot(x[zero], q[zero, 1], "o", ms=3.5, mfc="white", mec=colors[g], mew=0.8, zorder=3)
        if zero_row:
            floor_axis(ax, floor, "y", top=top * 2.0)
            ax.axhspan(floor / 10.0**0.35, floor * 10.0**0.5, color="#f3f3f3", lw=0, zorder=0.4)
        else:
            ax.set_yscale("log")
        ax.set_ylabel(ylabel, fontsize=7)
        ax.set_xlabel("level", fontsize=7)
        ax.set_xticks(sorted(set(levels.values())))
        ax.set_xticklabels([f"{lv:g}" for lv in sorted(set(levels.values()))])
        ax.tick_params(labelsize=MIN_FONT)
    handles = [plt.Line2D([], [], marker="o", ls="-", lw=0.7, color=colors[g], mec="white", label=g)
               for g in grp_names] if len(grp_names) > 1 else []
    if any_open:
        handles.append(plt.Line2D([], [], marker="o", ls="", mfc="white", mec="#555555",
                                  label="open: median 0, in the zero row"))
    if handles:
        fig.legend(handles=handles, loc="outside lower center", ncol=len(handles), fontsize=MIN_FONT,
                   frameon=False)
    fig.suptitle("Decision value, efficiency and cost by scenario level (median, bars: q05–q95)",
                 fontsize=8)
    fig.savefig(out / "fig_by_level.pdf")
    plt.close(fig)
    return True


def fig_sensitivity_heatmap(con, run_id, out: Path):
    order = ranked_ids(con, run_id)
    names = run_sensitivity_names(con, run_id)
    mat = np.full((len(names), len(order)), np.nan)
    for r in con.execute("SELECT * FROM sensitivities WHERE run_id=?", (run_id,)):
        if r["spearman"] is not None and r["scenario_id"] in order and r["param"] in names:
            mat[names.index(r["param"]), order.index(r["scenario_id"])] = abs(r["spearman"])
    vmax = max(0.3, float(np.ceil(np.nanmax(mat) * 10) / 10)) if np.isfinite(mat).any() else 1.0
    fig, ax = plt.subplots(figsize=(6.2, 0.3 * len(names) + 0.9))
    im = ax.imshow(mat, aspect="auto", cmap="Blues", vmin=0, vmax=vmax,
                   interpolation="nearest")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([f"${esc_math(n)}$" for n in names])
    step = max(1, len(order) // 30)
    ax.set_xticks(range(0, len(order), step))
    ax.set_xticklabels([order[i] for i in range(0, len(order), step)], fontsize=5,
                       rotation=90)
    ax.set_xlabel("scenario id, ordered by efficiency rank (best left)")
    ax.set_title("Parameter influence on efficiency: |Spearman ρ| per scenario")
    ax.grid(visible=False)
    fig.colorbar(im, ax=ax, label=r"|Spearman $\rho$|", shrink=0.9)
    fig.savefig(out / "fig_sensitivity_heatmap.pdf")
    plt.close(fig)
    return True


def fig_headroom(con, run_id, out: Path):
    """Binary runs only: a Gaussian run stores no headroom metric (skipped)."""
    head = metric_rows(con, run_id, "headroom")
    if not head:
        return False
    order = ranked_ids(con, run_id)
    ys = [head[s]["q50"] if s in head and head[s]["q50"] is not None else np.nan
          for s in order]
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.plot(range(1, len(order) + 1), ys, "o", color=ACCENT, ms=4, mec="white",
            mew=0.4)
    ax.set_xlabel("efficiency rank (best = 1)")
    ax.set_ylabel("median EVSI / EVPI")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Headroom: how much of the perfect-information value the instrument delivers")
    fig.savefig(out / "fig_headroom.pdf")
    plt.close(fig)
    return True


def fig_rank_stability(con, run_id, out: Path):
    stab = metric_rows(con, run_id, "p_top10")
    order = ranked_ids(con, run_id)
    ys = [stab[s]["p_positive"] if s in stab else 0.0 for s in order]
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.plot(range(1, len(order) + 1), ys, "o", color=ACCENT, ms=4, mec="white",
            mew=0.4)
    for i, sid in enumerate(order[:10]):
        ax.annotate(str(sid), (i + 1, ys[i]), textcoords="offset points",
                    xytext=(3, 4), fontsize=6, color="#333333")
    ax.set_xlabel("efficiency rank by median (best = 1)")
    ax.set_ylabel("P(scenario in top 10)")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Rank stability across MC draws (top 10 labeled by id)")
    fig.savefig(out / "fig_rank_stability.pdf")
    plt.close(fig)
    return True


def noise_units_label(stages: list[dict] | None, sids_of: dict[str, set[int]]) -> str:
    """What the spreads of the noise figure are over: '15 scenarios', or
    under a staged protocol '2 groups for p, B, K; 15 scenarios for s, t, C'
    (a decision-stage spread is one per group, on its representative)."""
    if stages is None:
        return f"{len(set().union(*sids_of.values()))} scenarios"
    g, s = db.group_stage(stages), db.scenario_stage(stages)
    n_g = len(set().union(*(sids_of.get(n, set()) for n in g["params"])))
    n_s = len(set().union(*(sids_of.get(n, set()) for n in s["params"])))
    return f"{n_g} groups for {', '.join(g['params'])}; {n_s} scenarios for {', '.join(s['params'])}"


def fig_elicitation_noise(con, run_id, out: Path):
    run = db.get_run(con, run_id)
    names = run_param_names(con, run_id)
    labels = db.run_member_labels(run)
    stages = db.protocol_stages(con.execute("SELECT * FROM protocols WHERE id=?",
                                            (run["protocol_id"],)).fetchone())
    spreads = {name: [] for name in names}
    sids_of: dict[str, set[int]] = {}
    for name in names:
        # the scenarios carrying the parameter (group representatives for a
        # decision-stage parameter of a staged protocol: one spread per group)
        for sid in db.param_scenario_ids(con, run["protocol_id"], name, labels):
            sids_of.setdefault(name, set()).add(sid)
            sp = db.elicited_spread(con, run["protocol_id"], sid, name, members=labels)
            if sp is not None:
                spreads[name].append(sp)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    data = [spreads[n] for n in names]
    sd_units = [n for n in names if db.spread_label(n)]
    if any(len(d) for d in data):
        ticks = [f"${esc_math(n)}$" + ("*" if n in sd_units else "") for n in names]
        ax.boxplot(data, tick_labels=ticks, showfliers=True,
                   flierprops={"marker": ".", "ms": 3, "mec": INTERVAL},
                   medianprops={"color": ACCENT, "lw": 1.5},
                   boxprops={"color": "#555555"},
                   whiskerprops={"color": "#555555"},
                   capprops={"color": "#555555"})
        ax.set_ylabel("(max − min) / pooled p50 across elicitations"
                      + ("\n* max − min in prior-sd units" if sd_units else ""))
        ax.set_title(f"Cross-elicitation noise per parameter ({noise_units_label(stages, sids_of)})")
    else:
        ax.text(0.5, 0.5, "protocol has k = 1: no repeat noise", ha="center",
                transform=ax.transAxes)
    fig.savefig(out / "fig_elicitation_noise.pdf")
    plt.close(fig)
    return True


def fig_top5_densities(con, run_id, out: Path):
    ids, eff = mc.replay_efficiency(con, run_id)
    order = ranked_ids(con, run_id)[:5]
    ttl = titles(con)
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    for color, sid in zip(CATEGORICAL, order, strict=False):
        draws = eff[ids.index(sid)]
        pos = draws[draws > 0]
        pzero = 1.0 - pos.size / draws.size
        label = f"{sid} · {ttl[sid][:34]} (P=0: {pzero:.0%})"
        if pos.size < 100:
            continue
        sub = np.log10(pos if pos.size <= 20000 else
                       np.random.default_rng(0).choice(pos, 20000, replace=False))
        kde = gaussian_kde(sub)
        grid = np.linspace(sub.min(), sub.max(), 400)
        ax.plot(grid, kde(grid) * (1.0 - pzero), color=color, lw=1.8, label=label)
    ax.set_xlabel(r"$\log_{10}$ efficiency (positive draws; densities scaled by 1 − P(eff = 0))")
    ax.set_ylabel("density")
    ax.axvline(0.0, color="#555555", lw=0.8, ls="--")
    ax.text(0.0, ax.get_ylim()[1] * 0.95, " EVSI = C", fontsize=7, color="#555555")
    ax.legend(fontsize=6.5, loc="upper left", frameon=False)
    ax.set_title("Efficiency densities, top 5 scenarios")
    fig.savefig(out / "fig_top5_densities.pdf")
    plt.close(fig)
    return True


ALL_FIGURES = [fig_evsi_vs_cost, fig_ranking, fig_param_medians, fig_by_level,
               fig_sensitivity_heatmap, fig_headroom, fig_rank_stability,
               fig_elicitation_noise, fig_top5_densities]


def make_all(con, run_id: int, out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(STYLE)
    written = []
    for f in ALL_FIGURES:
        if f(con, run_id, out):
            written.append(f.__name__)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    add_study_arg(ap)
    add_run_args(ap)
    add_tag_arg(ap)
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    out, _ = study.tagged(args.tag)   # figures write no macros
    con = study.connect()
    run_id = select_run(con, args.run, args.protocol, db.parse_member_labels(args.members),
                        args.weights)["id"]
    for name in make_all(con, run_id, out):
        print(f"wrote {out / (name + '.pdf')}")


if __name__ == "__main__":
    main()
