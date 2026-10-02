"""The report figures (DESIGN section 7), PDF, drawn at the CoRL text width
(5.5 in) with no text smaller than 6.5 pt and no titles beyond the panel tags
(captions live in the tex). Two groups: physical AI (triangles) and LLM
(circles); colour is the risk domain (Okabe-Ito, physical AI its own
vermillion, so the colour alone also tells the groups apart). The method
diagram is TikZ in the tex, not here.

Each fig_* takes a Summary and the output directory and returns the path
written, or None with a printed reason when the data cannot support it
(no physical-AI levels, a single member, one group missing)."""

from __future__ import annotations

import logging
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.transforms import offset_copy  # noqa: E402

from voi_rank.analysis.summary import (  # noqa: E402
    BEST_TOP,
    CURVE_QS,
    DOMAIN_LABEL,
    DOMAINS,
    LLM,
    PHYS,
    PRIMARY,
    RANKED,
    ROC_FPR,
    Summary,
    log_param,
    member_name,
    order,
    order_by_median_rank,
)
from voi_rank.fit import PARAM_NAMES  # noqa: E402

logging.getLogger("fontTools").setLevel(logging.ERROR)   # TrueType embedding chatter
FIG_W = 5.5
MIN_FONT = 6.5
COLOR = {PHYS: "#D55E00", LLM: "#0072B2", None: "#7f7f7f"}
MARKER = {PHYS: "^", LLM: "o", None: "s"}
MEMBER_COLORS = ["#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000", "#F0E442"]
# one Okabe-Ito colour per risk domain; physical AI keeps the group's vermillion
DOMAIN_COLOR = {"cyber": "#0072B2", "cbrn": "#009E73", "loss_of_control": "#CC79A7",
                "harmful_manipulation": "#E69F00", "societal_harm": "#56B4E9", "physical_harm": "#D55E00"}
INK, MUTED, GRID = "#333333", "#8a8a8a", "#e3e3e3"
PARAM_LABEL = {"p": "$p$", "s": "$s$", "t": "$t$", "B": "$B$ (USD)", "K": "$K$ (USD)",
               "C_build": r"$C_\mathrm{b}$ (USD)", "C_run": r"$C_\mathrm{r}$ (USD)"}
METRIC_TEX = {"eta": r"$\eta$", "eta_ind": r"$\eta^*$"}
VALUE_TEX = {"EVSI": "EVSI (USD)", "EVSI_ind": r"$\mathrm{EVSI}^*$ (USD)"}
STYLE = {
    "font.family": "serif", "mathtext.fontset": "cm", "font.size": 7,
    "axes.labelsize": 7, "xtick.labelsize": MIN_FONT, "ytick.labelsize": MIN_FONT,
    "legend.fontsize": MIN_FONT, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True,
    "axes.edgecolor": INK, "figure.constrained_layout.use": True, "pdf.fonttype": 42,
}


def pct_text(p: float) -> str:
    """Plain-text percent that never shows 0% or 100% for a probability inside (0, 1)."""
    if 0.995 <= p < 1.0:
        return ">99.5%"
    if 0.0 < p < 0.005:
        return "<0.5%"
    return f"{100 * p:.0f}%"


def color(group) -> str:
    return COLOR.get(group, COLOR[None])


def marker(group) -> str:
    return MARKER.get(group, MARKER[None])


def save(fig, out: Path, name: str) -> Path:
    """Deterministic PDF (no creation date)."""
    path = Path(out) / name
    fig.savefig(path, metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)
    return path


def group_handles(groups) -> list:
    return [plt.Line2D([], [], marker=marker(g), ls="", color=color(g), ms=4, label=g)
            for g in (PHYS, LLM) if g in groups]


def domain_color(domain) -> str:
    return DOMAIN_COLOR.get(domain, COLOR[None])


def domain_handles(s: Summary) -> list:
    """One legend entry per risk domain present, in DOMAINS order, as a filled square."""
    present = {sc.domain for sc in s.scenarios}
    return [plt.Line2D([], [], marker="s", ls="", color=domain_color(d), ms=5, label=DOMAIN_LABEL.get(d, d))
            for d in DOMAINS if d in present]


def domain_group_handles(scenarios, ms: float = 4.5) -> list:
    """One legend entry per (risk domain, group) present, in DOMAINS order: the
    group's marker in the domain's colour, labelled by the domain (and the
    group, where a domain spans both groups)."""
    pairs = {(sc.domain, sc.group) for sc in scenarios}
    handles = []
    for d in DOMAINS:
        groups = [g for g in (PHYS, LLM, None) if (d, g) in pairs]
        for g in groups:
            label = DOMAIN_LABEL.get(d, d) + (f" ({g})" if len(groups) > 1 else "")
            handles.append(plt.Line2D([], [], marker=marker(g), ls="", color=domain_color(d), ms=ms,
                                      mec="white", mew=0.4, label=label))
    return handles


# --- labels ---------------------------------------------------------------------

OFFSETS = ((3.5, 2.0, "left", "bottom"), (-3.5, 2.0, "right", "bottom"), (3.5, -2.0, "left", "top"),
           (-3.5, -2.0, "right", "top"), (0.0, 4.5, "center", "bottom"), (0.0, -4.5, "center", "top"),
           (5.0, 0.0, "left", "center"), (-5.0, 0.0, "right", "center"))
FAR = 2.6           # the second ring of candidates: OFFSETS scaled, with a leader line
FAR_COST = 0.15     # a far label costs this share of its own area (prefer the near ring)
LABEL_PAD_PT = 1.0  # labels closer than this to each other count as overlapping


def place_labels(ax, xy, texts, marker_pt: float = 5.0, avoid=()) -> None:
    """Label each point at the candidate offset that overlaps least with the
    markers, the labels already placed (padded by LABEL_PAD_PT), the `avoid`
    artists and the outside of the axes (greedy, most crowded points first).
    Candidates: OFFSETS, then the same directions FAR times farther with a
    leader line, at a small extra cost. Call once limits and layout are final."""
    fig = ax.figure
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    data = np.asarray(xy, dtype=float).reshape(-1, 2)
    pts = ax.transData.transform(data)
    half = marker_pt / 2.0 * fig.dpi / 72.0
    pad = LABEL_PAD_PT * fig.dpi / 72.0
    boxes = [np.array([x - half, y - half, x + half, y + half]) for x, y in pts]
    for a in avoid:
        e = a.get_window_extent(renderer)
        boxes.append(np.array([e.x0, e.y0, e.x1, e.y1]))
    fr = ax.get_window_extent(renderer)

    def overlap(b, o):
        return max(0.0, min(b[2], o[2]) - max(b[0], o[0])) * max(0.0, min(b[3], o[3]) - max(b[1], o[1]))

    frame = np.array([fr.x0, fr.y0, fr.x1, fr.y1])
    cands = [(dx, dy, ha, va, False) for dx, dy, ha, va in OFFSETS]
    cands += [(FAR * dx, FAR * dy, ha, va, True) for dx, dy, ha, va in OFFSETS]
    crowd = (np.hypot(*(pts[:, None, :] - pts[None, :, :]).transpose(2, 0, 1)) < 20.0).sum(axis=1)
    for i in sorted(range(len(pts)), key=lambda k: (-crowd[k], k)):
        ann = ax.annotate(texts[i], tuple(data[i]), textcoords="offset points", xytext=(0, 0),
                          fontsize=MIN_FONT, color=INK, zorder=4, annotation_clip=False)
        best = None
        for dx, dy, ha, va, far in cands:
            ann.set_position((dx, dy))
            ann.set_ha(ha)
            ann.set_va(va)
            e = ann.get_window_extent(renderer)
            b = np.array([e.x0 - pad, e.y0 - pad, e.x1 + pad, e.y1 + pad])
            area = (b[2] - b[0]) * (b[3] - b[1])
            cost = (sum(overlap(b, o) for o in boxes) + 4.0 * (area - overlap(b, frame))
                    + (FAR_COST * area if far else 0.0))
            if best is None or cost < best[0] - 1e-9:
                best = (cost, (dx, dy, ha, va, far), b)
        ann.remove()
        dx, dy, ha, va, far = best[1]
        lead = {"arrowstyle": "-", "color": MUTED, "lw": 0.4, "shrinkA": 0.5, "shrinkB": 2.5}
        ann = ax.annotate(texts[i], tuple(data[i]), textcoords="offset points", xytext=(dx, dy), ha=ha,
                          va=va, fontsize=MIN_FONT, color=INK, zorder=4, annotation_clip=False,
                          arrowprops=lead if far else None)
        ann.set_in_layout(False)
        boxes.append(best[2])


# --- value against cost -----------------------------------------------------------

def floor_of(values) -> float:
    """The zero row's height: one decade below the smallest positive value."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v) & (v > 0)]
    return 10.0 ** (math.floor(math.log10(v.min())) - 1) if v.size else 1.0


def fan_positions(anchor, widths, lo: float, hi: float, gap: float) -> np.ndarray:
    """Label centres (display units) for labels whose anchors cluster: in
    anchor order, alternating between two rows, consecutive labels one
    pitch apart (pitch = widest label + gap, so neighbours within a row are
    two pitches apart), the run centred on the anchors' mean and shifted to
    stay inside [lo, hi]. Returns one centre per label, in input order."""
    anchor = np.asarray(anchor, dtype=float)
    n = len(anchor)
    if n == 0:
        return np.zeros(0)
    pitch = max(widths) / 2.0 + gap
    span = (n - 1) * pitch
    start = float(anchor.mean()) - span / 2.0
    start = min(max(start, lo + max(widths) / 2.0), hi - max(widths) / 2.0 - span)
    out = np.empty(n)
    out[np.argsort(anchor, kind="stable")] = start + pitch * np.arange(n)
    return out


ARROW_LEN = 0.13   # axes fraction, along (-1, +1)
ARROW_INSET = 0.05


def arrow_corners(band_top: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """(head, tail) in axes fraction for the four corners above the zero
    band, the head always up-left of the tail: direction (-1, +1), which on
    equal decades is orthogonal to the iso-efficiency lines."""
    m, L, b = ARROW_INSET, ARROW_LEN, band_top
    return [((m, 1 - m), (m + L, 1 - m - L)), ((1 - m - L, 1 - m), (1 - m, 1 - m - L)),
            ((m, b + m + L), (m + L, b + m)), ((1 - m - L, b + m + L), (1 - m, b + m))]


def best_corner(ax, obstacles_px: np.ndarray, band_top: float):
    """The corner whose arrow lies farthest (minimum distance, display units)
    from every obstacle point; ties go to the first corner in arrow_corners."""
    best = None
    for head, tail in arrow_corners(band_top):
        seg = ax.transAxes.transform(np.linspace(head, tail, 12))
        d = (np.hypot(*(seg[:, None, :] - obstacles_px[None, :, :]).transpose(2, 0, 1)).min()
             if len(obstacles_px) else math.inf)
        if best is None or d > best[0] + 1e-9:
            best = (d, head, tail)
    return best[1], best[2]


ZERO_ROWS = (0.5, 1.0)   # decades below the zero row: the two staggered rows of its ids
ZERO_BAND = 1.35         # decades from the zero row to the bottom of the axes


VALUE_FONT = 9.0   # the value axes' label: large enough for the star of EVSI* to read


def value_cost_panel(ax, s: Summary, metric: str, ylabel: str, show_zero: bool = True,
                     eta_tex: str = r"\eta", labels: bool = True) -> None:
    """EVSI-type value (y) against C (x) with every parameter at its median, log-log
    with equal decades, iso-efficiency lines, the 'better' arrow along
    (-1, +1) in log space (orthogonal to the iso-lines) in the corner
    farthest from the points, ids as labels; marker = group, colour = risk
    domain (the legend is the caller's, see domain_group_handles). With
    show_zero, zero values sit on a row labelled 0 at their true cost and
    their ids, which would collide (the zeros cluster in cost), fan out below
    in two staggered rows with leader lines, in cost order; without it, the
    zeros are left out (the caption says how many). Set titles before
    calling: the layout must be final when the labels are placed."""
    fig = ax.figure
    x, y = s.central["C"], s.central[metric]
    zero = ~(y > 0)
    if not show_zero:
        keep = ~zero
        if not keep.any():
            ax.text(0.5, 0.5, "every prior already decisive:\nno evaluation with EVSI > 0",
                    transform=ax.transAxes, ha="center", va="center", fontsize=MIN_FONT, color=MUTED)
            ax.set_xlabel("cost $C$ (USD)")
            ax.set_ylabel(ylabel, fontsize=VALUE_FONT)
            return
        x, y, zero = x[keep], y[keep], zero[keep]
        scen = [sc for sc, k in zip(s.scenarios, keep, strict=True) if k]
    else:
        scen = list(s.scenarios)
    floor = floor_of(y)
    lf = math.log10(floor)
    ids = [str(sc.id) for sc in scen]
    zi = np.flatnonzero(zero)
    pos = y[~zero]
    lx = [math.log10(x.min()) - 0.4, math.log10(x.max()) + 0.4]
    ly = [lf - ZERO_BAND if zero.any() else math.log10(pos.min()) - 0.4,
          (math.log10(pos.max()) if pos.size else lf) + 0.6]
    span = max(lx[1] - lx[0], ly[1] - ly[0])
    lx = [(lx[0] + lx[1] - span) / 2, (lx[0] + lx[1] + span) / 2]
    ly = [ly[0], ly[0] + span]
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(10 ** lx[0], 10 ** lx[1])
    ax.set_ylim(10 ** ly[0], 10 ** ly[1])
    ax.set_aspect("equal", adjustable="box")
    for k in range(math.floor(ly[0] - lx[1]) - 1, math.ceil(ly[1] - lx[0]) + 2):
        xs = np.array([10 ** lx[0], 10 ** lx[1]])
        ax.plot(xs, 10.0 ** k * xs, ls="--", lw=0.5, color="#c9c9c9", zorder=0)
        # label where the line leaves the top or right edge, clear of the zero band and the x axis
        xe = min(lx[1], ly[1] - k) - 0.35
        ye = xe + k
        if lx[0] + 0.5 < xe and max(lf + 1.0, ly[0] + 0.4) < ye < ly[1] - 0.05 and k % 2 == 0:
            ax.text(10 ** xe, 10 ** ye, rf"${eta_tex}=10^{{{k}}}$", fontsize=MIN_FONT, color=MUTED,
                    rotation=45, rotation_mode="anchor", ha="right", va="bottom")
    avoid, band_top = [], 0.0
    if zero.any():
        avoid.append(ax.axhspan(10 ** ly[0], floor * 10 ** 0.45, color="#f3f3f3", lw=0, zorder=0.5))
        band_top = (lf + 0.45 - ly[0]) / (ly[1] - ly[0])
        ticks = [10.0 ** k for k in range(math.ceil(lf + 1), math.floor(ly[1]) + 1)]
        ax.yaxis.set_major_locator(mticker.FixedLocator([floor, *ticks]))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: "0" if math.isclose(v, floor) else f"$10^{{{round(math.log10(v))}}}$"))
        ax.yaxis.set_minor_locator(mticker.NullLocator())
    yy = np.where(zero, floor, y)
    keys = [(sc.group, sc.domain) for sc in scen]
    for g, d in sorted(set(keys), key=str):
        m = np.array([k == (g, d) for k in keys])
        ax.plot(x[m & ~zero], yy[m & ~zero], marker(g), ls="", color=domain_color(d), ms=4.5, mec="white",
                mew=0.4, zorder=3)
        ax.plot(x[m & zero], yy[m & zero], marker(g), ls="", mfc="white", mec=domain_color(d), ms=4.5,
                mew=0.8, zorder=3)
    ax.set_xlabel("cost $C$ (USD)")
    ax.set_ylabel(ylabel, fontsize=VALUE_FONT)
    fig.draw_without_rendering()           # final layout: display coordinates are stable from here
    renderer = fig.canvas.get_renderer()
    if len(zi) and labels:
        fr = ax.get_window_extent(renderer)
        probe = ax.text(0, 0, "", fontsize=MIN_FONT)
        widths = []
        for i in zi:
            probe.set_text(ids[i])
            widths.append(probe.get_window_extent(renderer).width)
        probe.remove()
        anchor = ax.transData.transform(np.column_stack([x[zi], yy[zi]]))[:, 0]
        cx = fan_positions(anchor, widths, fr.x0 + 2, fr.x1 - 2, 3.0 * fig.dpi / 72.0)
        row = np.empty(len(zi), dtype=int)
        row[np.argsort(anchor, kind="stable")] = np.arange(len(zi)) % 2
        inv = ax.transData.inverted()
        for k, i in enumerate(zi):
            lx_data = inv.transform((cx[k], 0.0))[0]
            ann = ax.annotate(ids[i], (x[i], floor), xytext=(lx_data, floor * 10.0 ** -ZERO_ROWS[row[k]]),
                              ha="center", va="center", fontsize=MIN_FONT, color=INK, zorder=4,
                              annotation_clip=False,
                              arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.4, "shrinkA": 1.5,
                                          "shrinkB": 2.5})
            ann.set_in_layout(False)
    # the arrow goes to the corner farthest from the points and the iso-line labels
    obst = [ax.transData.transform(np.column_stack([x[~zero], yy[~zero]]))]
    for txt in ax.texts:
        e = txt.get_window_extent(renderer)
        obst.append(np.array([[e.x0, e.y0], [e.x1, e.y1], [e.x0, e.y1], [e.x1, e.y0],
                              [(e.x0 + e.x1) / 2, (e.y0 + e.y1) / 2]]))
    head, tail = best_corner(ax, np.vstack(obst), band_top)
    arrow = ax.annotate("", xy=head, xytext=tail, xycoords="axes fraction", textcoords="axes fraction",
                        arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 0.8})
    mid = ((head[0] + tail[0]) / 2, (head[1] + tail[1]) / 2)
    word = ax.annotate("better", mid, xycoords="axes fraction", textcoords="offset points",
                       xytext=(1.5, 1.5), rotation=-45, rotation_mode="anchor", ha="center", va="bottom",
                       fontsize=MIN_FONT, color=INK)
    for a in (arrow, word):
        a.set_in_layout(False)
    nz = np.flatnonzero(~zero)
    if labels:
        place_labels(ax, np.column_stack([x[nz], yy[nz]]), [ids[i] for i in nz],
                     avoid=[*avoid, arrow, word, *ax.texts])


def curve_panel(ax, s: Summary) -> None:
    o = s.out
    lo, med, hi = o["curve_q"].T
    ax.fill_between(CURVE_QS, lo, hi, color=COLOR[PHYS], alpha=0.25, lw=0, label="90% band over draws")
    ax.plot(CURVE_QS, med, color=COLOR[PHYS], lw=1.2, label="median over draws")
    ax.plot(CURVE_QS, o["curve_central"], color=INK, lw=0.9, ls="--", label="median parameters")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.set_xlabel("percentile $q$ of the LLM evaluations' $\\eta$")
    ax.set_ylabel("P(physical-AI $\\eta$ > $q$-th percentile)")
    ax.legend(loc="upper right", frameon=False)


HEADLINE_W = 1.0   # share of the text width the paper gives the headline figure
HEADLINE_H = 2.2   # its height (inches): two equal-decade panels and a one-column legend at the right
HEADLINE_TITLES = ("(a) $\\mathrm{EVSI}^{*}$: value to an\nundecided developer",
                   "(b) EVSI: value at the\nelicited prior")


def headline_panels(s: Summary, width: float, labels: bool, legend_right: bool = True):
    """(a) EVSI* against C for every evaluation and (b) EVSI against C for
    those whose result can change the decision; the legend (colour = risk
    domain, marker = group) outside the panels: one column at the right
    (the paper, HEADLINE_H tall) or one row on top (the extended report,
    whose id labels need the wider panels). Titles and legend go in first so
    the layout is final when the panels place labels."""
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(width, HEADLINE_H if legend_right else width / 2 + 0.45))
    for a, title in zip((ax, bx), HEADLINE_TITLES, strict=True):
        a.set_title(title, loc="left", fontsize=7.5, pad=4)
    handles = domain_group_handles(s.scenarios)
    if not (s.central["EVSI_ind"] > 0).all():
        handles.append(plt.Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=4,
                                  label="prior already decisive\n(value 0)" if legend_right
                                  else "prior already decisive (value 0)"))
    if legend_right:
        fig.legend(handles=handles, loc="outside right center", ncol=1, frameon=False, fontsize=7,
                   handletextpad=0.4, labelspacing=0.7, borderaxespad=0.2)
    else:
        fig.legend(handles=handles, loc="outside upper center", ncol=len(handles), frameon=False, fontsize=7,
                   handlelength=1.0, handletextpad=0.4, columnspacing=1.0)
    value_cost_panel(ax, s, "EVSI_ind", VALUE_TEX["EVSI_ind"], eta_tex=r"\eta^*", labels=labels)
    value_cost_panel(bx, s, "EVSI", VALUE_TEX["EVSI"], show_zero=False, labels=labels)
    return fig


def fig_headline(s: Summary, out: Path) -> Path | None:
    """Left: EVSI* against C for every evaluation (EVSI* is positive for every
    informative evaluation); right: EVSI against C for the evaluations whose
    result can change the decision (EVSI > 0). Full text width with id labels
    and the room they need (the extended report)."""
    with plt.rc_context(STYLE):
        return save(headline_panels(s, FIG_W, labels=True, legend_right=False), out, "fig_headline.pdf")


def fig_headline_small(s: Summary, out: Path) -> Path | None:
    """The same at the paper's width and height, without id labels (Fig. rows names every evaluation)."""
    with plt.rc_context(STYLE):
        return save(headline_panels(s, HEADLINE_W * FIG_W, labels=False), out, "fig_headline_small.pdf")


def fig_curve(s: Summary, out: Path) -> Path | None:
    """The percentile curve alone (extended report)."""
    if "curve_q" not in s.out:
        print("fig_curve: skipped (needs both groups)")
        return None
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W * 0.6, FIG_W * 0.45))
        curve_panel(ax, s)
        return save(fig, out, "fig_curve.pdf")


# --- distributions per evaluation ------------------------------------------------------

LABEL_CHARS = 30   # row labels longer than this are cut at a word boundary with an ellipsis


def abbreviate(text: str, limit: int = LABEL_CHARS) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(" ", 1)[0] if " " in text[:limit - 1] else text[:limit - 1]
    return cut.rstrip(" -/,:;") + "\u2026"


def scenario_label(s: Summary, i: int) -> str:
    """'[id] short name', the id in brackets as the documents cite it."""
    sc = s.scenarios[i]
    return abbreviate(f"[{sc.id}] {sc.short}")


RANK_BW = 0.7   # rank violins: kernel width in ranks (ranks are integers; a data-driven bandwidth
                # would draw one bump per integer on the narrow rows)


def _violins(ax, data, positions, col, bw=None, alpha: float = 0.55):
    """Horizontal violins, one per row, no edge; bw is a kernel width in data units (None: Scott)."""
    kw = {"bw_method": lambda kde: bw / float(kde.dataset.std())} if bw is not None else {}
    parts = ax.violinplot(data, positions=positions, orientation="horizontal", widths=0.8, showextrema=False,
                          points=120, **kw)
    for b in parts["bodies"]:
        b.set_facecolor(col)
        b.set_edgecolor("none")
        b.set_alpha(alpha)


def row_violin(ax, v, p: float, col: str, bw=None) -> None:
    """One row's distribution: a violin (when the values vary) and its median tick."""
    v = np.asarray(v, dtype=float)
    if v.size >= 2 and np.ptp(v) > 0:
        _violins(ax, [v], [p], col, bw=bw)
    ax.plot(np.median(v), p, "|", color=INK, ms=6, mew=1.0, zorder=4)


def _rows_height(n: int) -> float:
    return max(1.6, 0.16 * n + 0.7)


def fig_percentile_violins(s: Summary, out: Path) -> Path | None:
    if "pct_draws" not in s.out:
        print("fig_percentile_violins: skipped (needs both groups)")
        return None
    o = s.out
    phys = list(s.ids_in(PHYS))
    rows = sorted(range(len(phys)), key=lambda k: (o["pct_q"][k][1], o["pct_central"][k]))
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W, _rows_height(len(phys))))
        pos = np.arange(len(rows))
        data = [o["pct_draws"][k] for k in rows]
        flat = [d if np.ptp(d) > 0 else d + np.array([0.0] * (len(d) - 1) + [1e-6]) for d in data]
        _violins(ax, flat, pos, COLOR[PHYS])
        ax.plot([o["pct_q"][k][1] for k in rows], pos, "|", color=INK, ms=6, label="median over draws")
        ax.plot([o["pct_central"][k] for k in rows], pos, "D", color=INK, mfc="white", ms=3.2,
                label="median parameters")
        ax.axvline(50, color=MUTED, lw=0.6, ls=":")
        ax.set_yticks(pos, [scenario_label(s, phys[k]) for k in rows])
        ax.set_xlim(0, 100)
        ax.set_xlabel("percentile among the LLM evaluations ($\\eta$)")
        ax.legend(loc="lower right", frameon=False)
        return save(fig, out, "fig_percentile_violins.pdf")


def rank_intervals(s: Summary, out: Path, metric: str, name: str) -> Path:
    """Per evaluation, the rank under `metric` over the draws: median (tick),
    interquartile range (thick bar) and 90% interval (thin bar), rows sorted
    by the median rank, coloured by risk domain."""
    r = s.out["rank"][metric]
    idx = order_by_median_rank(s, metric)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W, _rows_height(len(idx))))
        pos = np.arange(len(idx))[::-1]
        for p, i in zip(pos, idx, strict=True):
            col = domain_color(s.scenarios[i].domain)
            lo, med, hi = r["q"][i]
            q25, q75 = r["iqr_q"][i]
            ax.plot([lo, hi], [p, p], color=col, lw=0.9, solid_capstyle="butt", zorder=2)
            ax.plot([q25, q75], [p, p], color=col, lw=3.6, solid_capstyle="butt", zorder=3)
            ax.plot(med, p, "|", color=INK, ms=6, mew=1.1, zorder=4)
        ax.set_yticks(pos, [scenario_label(s, i) for i in idx])
        ax.set_xlim(0.5, len(idx) + 0.5)
        ax.set_xlabel(f"rank by {METRIC_TEX[metric]} over the Monte Carlo draws (1 = best)")
        handles = domain_handles(s)
        handles += [plt.Line2D([], [], color=MUTED, lw=3.6, label="interquartile range"),
                    plt.Line2D([], [], color=MUTED, lw=0.9, label="90% interval"),
                    plt.Line2D([], [], marker="|", ls="", color=INK, ms=6, mew=1.1, label="median")]
        fig.legend(handles=handles, loc="outside upper center", ncol=5, frameon=False,
                   handletextpad=0.4, columnspacing=1.0)
        ax.grid(axis="y", visible=False)
        return save(fig, out, name)


def fig_rank_star(s: Summary, out: Path) -> Path | None:
    return rank_intervals(s, out, "eta_ind", "fig_rank_star.pdf")


def fig_rank_eta(s: Summary, out: Path) -> Path | None:
    return rank_intervals(s, out, "eta", "fig_rank_eta.pdf")


def fig_best_physical_rank(s: Summary, out: Path) -> Path | None:
    """P(the best-ranked physical-AI evaluation has rank <= N) against N, over
    the draws, one curve per ranking metric, with each median-parameter
    best physical-AI rank as a dashed step."""
    o = s.out
    if "best_phys_curve" not in o["rank"][PRIMARY]:
        print("fig_best_physical_rank: skipped (needs both groups)")
        return None
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W, 2.1))
        styles = {"eta_ind": (COLOR[PHYS], "-"), "eta": (INK, ":")}
        for metric in RANKED:
            r = o["rank"][metric]
            ns, curve, c = r["best_phys_ns"], r["best_phys_curve"], r["best_phys_central"]
            col, ls = styles[metric]
            ax.step(ns, curve, where="post", color=col, lw=1.4, ls=ls,
                    label=f"by {METRIC_TEX[metric]} over draws (best rank {c:g} at the median parameters)")
            for n in BEST_TOP:
                if n <= len(ns) and metric == PRIMARY:
                    v = curve[n - 1]
                    ax.plot(n, v, "o", color=col, ms=3.5, mec="white", mew=0.4, zorder=3)
                    first = n == ns[0]
                    ax.annotate(pct_text(v), (n, v), xytext=(2.5 if first else -2.5, 2.5),
                                textcoords="offset points", ha="left" if first else "right",
                                va="bottom", fontsize=MIN_FONT, color=INK, annotation_clip=False)
        ax.set_xlim(0.5, len(ns) + 0.5)
        ax.set_ylim(0, 1.03)
        ax.xaxis.set_major_locator(mticker.FixedLocator([1, *range(5, len(ns) + 1, 5)]))
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.set_xlabel(f"$N$ (rank among all {len(ns)} evaluations, 1 = best)")
        ax.set_ylabel("P(best physical-AI rank $\\leq N$)")
        ax.legend(loc="lower right", frameon=False)
        return save(fig, out, "fig_best_physical_rank.pdf")


ROC_PANELS = (("eta", r"$\eta$"), ("eta_ind", r"$\eta^*$"))


def fig_roc(s: Summary, out: Path) -> Path | None:
    """ROC of 'physical AI' given the score, one panel per metric: the central
    estimate's curve (its area is A) and the pointwise 5-95% band of the
    per-draw curves at a fixed false-positive grid."""
    o = s.out
    if "roc" not in o:
        print("fig_roc: skipped (needs both groups)")
        return None
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, len(ROC_PANELS), figsize=(FIG_W, FIG_W / 2 - 0.05))
        for ax, (metric, name) in zip(axes, ROC_PANELS, strict=True):
            r = o["roc"][metric]
            lo, med, hi = r["band"].T
            ax.fill_between(ROC_FPR, lo, hi, color=COLOR[PHYS], alpha=0.22, lw=0, label="5-95% over draws")
            ax.plot(ROC_FPR, med, color=COLOR[PHYS], lw=1.1, label="median over draws")
            ax.plot(r["fpr"], r["tpr"], color=INK, lw=1.1, label="median parameters")
            ax.plot([0, 1], [0, 1], color=MUTED, lw=0.6, ls=":")
            ax.text(0.04, 0.96, f"threshold on {name}\n$P_S$ at median parameters = {pct_text(r['area'])}",
                    transform=ax.transAxes, ha="left", va="top", fontsize=7, color=INK, linespacing=1.4)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_aspect("equal")
            ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))
            ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
            ax.set_xlabel("share of LLM evaluations above the threshold")
            ax.set_ylabel("share of physical-AI evaluations above it")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="outside upper center", ncol=len(handles), frameon=False)
        return save(fig, out, "fig_roc.pdf")


def nstar_rows(ax, s: Summary, idx, pos, show_share: bool = True) -> bool:
    """The break-even run count n* per row over the finite draws (violin, log10
    x, median tick), coloured by domain; returns whether any row was drawn.
    With show_share, the share of finite draws in the right margin."""
    o = s.out
    drawn = False
    for p, i in zip(pos, idx, strict=True):
        ns = s.draws["n_star"][i]
        v = np.log10(ns[np.isfinite(ns) & (ns > 0)])
        if v.size >= 2 and np.ptp(v) > 0:
            row_violin(ax, v, p, domain_color(s.scenarios[i].domain))
            drawn = True
        if show_share:
            ax.annotate(pct_text(o["p_nstar_finite"][i]), (1.0, p), xycoords=("axes fraction", "data"),
                        xytext=(3, 0), textcoords="offset points", va="center", fontsize=MIN_FONT,
                        color=INK, annotation_clip=False)
    if drawn:
        lo, hi = ax.get_xlim()
        step = max(1, math.ceil((hi - lo) / 6))
        ax.xaxis.set_major_locator(mticker.MultipleLocator(step))
        ax.xaxis.set_minor_locator(mticker.MultipleLocator(1))
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"$10^{{{v:g}}}$"))
        if show_share:
            ax.annotate("share of\ndraws finite", (1.0, 1.0), xycoords="axes fraction", xytext=(3, 1),
                        textcoords="offset points", ha="left", va="bottom", fontsize=MIN_FONT, color=INK,
                        annotation_clip=False, linespacing=1.1)
    return drawn


def rank_rows(ax, s: Summary, metric: str, idx, pos) -> None:
    """The rank under `metric` per row over the draws as a violin (kernel
    width RANK_BW ranks) with its median tick, 1 = best at the left."""
    ranks = s.out["rank"][metric]["ranks"]
    n = len(s.scenarios)
    for p, i in zip(pos, idx, strict=True):
        row_violin(ax, ranks[i], p, domain_color(s.scenarios[i].domain), bw=RANK_BW)
    ax.set_xlim(0.5, n + 0.5)
    ax.xaxis.set_major_locator(mticker.FixedLocator([1, *range(5, n + 1, 5)]))


ROWS_H = 0.14   # inches per row in the paper's combined row figure (MIN_FONT labels need >= 0.1)


def fig_rows(s: Summary, out: Path) -> Path | None:
    """The paper's row figure: rank by eta* (left) and break-even run count
    (right) per evaluation as violins over the draws with median ticks, one
    shared row order (by the median rank), rows labelled '[id] name'."""
    idx = order_by_median_rank(s, PRIMARY)
    with plt.rc_context(STYLE):
        fig, (ax, bx) = plt.subplots(1, 2, sharey=True, figsize=(FIG_W, ROWS_H * len(idx) + 0.7),
                                     width_ratios=[1.0, 0.8])
        pos = np.arange(len(idx))[::-1]
        rank_rows(ax, s, PRIMARY, idx, pos)
        drawn = nstar_rows(bx, s, idx, pos, show_share=False)
        ax.set_yticks(pos, [scenario_label(s, i) for i in idx])
        ax.set_ylim(-0.7, len(idx) - 0.3)
        ax.set_xlabel(f"rank by {METRIC_TEX[PRIMARY]} (1 = best)")
        bx.set_xlabel("break-even run count $n^*$")
        if not drawn:
            bx.text(0.5, 0.5, "no finite break-even draws", transform=bx.transAxes, ha="center", va="center",
                    fontsize=MIN_FONT, color=MUTED)
        handles = domain_handles(s)
        handles.append(plt.Line2D([], [], marker="|", ls="", color=INK, ms=6, mew=1.0, label="median"))
        fig.legend(handles=handles, loc="outside upper center", ncol=len(handles), frameon=False,
                   handlelength=1.0, handletextpad=0.4, columnspacing=0.9)
        for a in (ax, bx):
            a.grid(axis="y", visible=False)
        return save(fig, out, "fig_rows.pdf")


def fig_breakeven(s: Summary, out: Path) -> Path | None:
    """Per evaluation, the break-even run count n* = C_build / (EVSI - C_run)
    over the draws where it is finite (violin, log scale), rows sorted by the
    median finite n* (evaluations with no finite draw last), coloured by risk
    domain; right margin: the share of draws on which n* is finite (one run
    worth more than its run cost)."""
    o = s.out
    med = [q[1] for q in o["nstar_q"]]
    idx = sorted(range(len(s.scenarios)),
                 key=lambda i: (med[i] is None, med[i] if med[i] is not None else 0.0, s.scenarios[i].id))
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W, _rows_height(len(idx))))
        pos = np.arange(len(idx))[::-1]
        if not nstar_rows(ax, s, idx, pos):
            print("fig_breakeven: skipped (no scenario has finite break-even draws)")
            plt.close(fig)
            return None
        ax.set_yticks(pos, [scenario_label(s, i) for i in idx])
        ax.set_ylim(-0.7, len(idx) - 0.3)
        ax.set_xlabel("break-even run count $n^*$ (draws where one run is worth more than its run cost)")
        handles = domain_handles(s)
        handles.append(plt.Line2D([], [], marker="|", ls="", color=INK, ms=6, mew=1.0, label="median"))
        fig.legend(handles=handles, loc="outside upper center", ncol=4, frameon=False,
                   handletextpad=0.4, columnspacing=1.0)
        ax.grid(axis="y", visible=False)
        return save(fig, out, "fig_breakeven.pdf")


# --- inputs --------------------------------------------------------------------------

def decade_ticks(ax, max_ticks: int = 3) -> None:
    """At most max_ticks major ticks on a log x axis, at whole decades
    evenly stepped, labelled 10^k unrotated; minor ticks at every decade."""
    lo, hi = ax.get_xlim()
    k0, k1 = math.ceil(math.log10(lo)), math.floor(math.log10(hi))
    step = max(1, math.ceil((k1 - k0 + 1) / max_ticks))
    ax.xaxis.set_major_locator(mticker.FixedLocator([10.0 ** k for k in range(k0, k1 + 1, step)]))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"$10^{{{round(math.log10(v))}}}$"))
    ax.xaxis.set_minor_locator(mticker.FixedLocator([10.0 ** k for k in range(k0, k1 + 1)]))
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())


def fig_params(s: Summary, out: Path) -> Path | None:
    """One panel per parameter: every member's elicited medians per scenario
    (colour = member) and the median across members (black bar)."""
    idx = order(s)
    pos = np.arange(len(idx))[::-1]
    labs = s.member_labels
    off = {lab: (k - (len(labs) - 1) / 2) * min(0.25, 0.6 / max(1, len(labs))) for k, lab in enumerate(labs)}
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, len(PARAM_NAMES), sharey=True,
                                 figsize=(FIG_W, _rows_height(len(idx)) + 0.3))
        for ax, name in zip(axes, PARAM_NAMES, strict=True):
            for p, i in zip(pos, idx, strict=True):
                for k, lab in enumerate(labs):
                    vals = s.elicited[name][i].get(lab, [])
                    ax.plot(vals, [p + off[lab]] * len(vals), "o", ms=2.2, mew=0,
                            color=MEMBER_COLORS[k % len(MEMBER_COLORS)], alpha=0.85)
                ax.plot(s.pooled[name][i], p, "|", color=INK, ms=5, mew=1.0)
            if log_param(name):
                ax.set_xscale("log")
                decade_ticks(ax, max_ticks=2)
            else:
                ax.set_xlim(0, 1)
                ax.set_xticks([0, 0.5, 1], ["0", "", "1"])
            ax.set_title(PARAM_LABEL[name].replace(" (USD)", ""), fontsize=7)
            ax.grid(axis="y", visible=False)
        axes[0].set_yticks(pos, [scenario_label(s, i) for i in idx])
        axes[0].set_ylim(-0.7, len(idx) - 0.3)
        axes[0].tick_params(axis="y", pad=10)
        for p, i in zip(pos, idx, strict=True):
            g = s.scenarios[i].group
            axes[0].plot([0.0], [p], marker(g), color=color(g), ms=3, clip_on=False,
                         transform=offset_copy(axes[0].get_yaxis_transform(), fig, x=-6, units="points"))
        handles = [plt.Line2D([], [], marker="o", ls="", ms=3, color=MEMBER_COLORS[k % len(MEMBER_COLORS)],
                              label=member_name(lab)) for k, lab in enumerate(labs)]
        handles.append(plt.Line2D([], [], marker="|", ls="", ms=5, color=INK, label="median across members"))
        handles += group_handles({sc.group for sc in s.scenarios})
        fig.legend(handles=handles, loc="outside upper center", ncol=min(len(handles), 5), frameon=False)
        fig.supxlabel("elicited median per valid elicitation (USD for $B$, $K$, $C_\\mathrm{b}$,"
                      " $C_\\mathrm{r}$)", fontsize=7)
        return save(fig, out, "fig_params.pdf")


def sensitivity_heatmap(s: Summary, out: Path, mat_all: np.ndarray, metric: str, name: str) -> Path:
    idx = order(s)
    mat = mat_all[idx]
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W, _rows_height(len(idx))))
        im = ax.imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto", interpolation="nearest")
        for r in range(mat.shape[0]):
            for c in range(mat.shape[1]):
                v = mat[r, c]
                if np.isfinite(v):
                    ax.text(c, r, f"{v:.1f}".replace("-0.0", "0.0"), ha="center", va="center",
                            fontsize=MIN_FONT, color="white" if abs(v) > 0.6 else INK)
        ax.set_xticks(range(len(PARAM_NAMES)), [PARAM_LABEL[n].replace(" (USD)", "") for n in PARAM_NAMES])
        ax.set_yticks(range(len(idx)), [scenario_label(s, i) for i in idx])
        ax.grid(False)
        ax.tick_params(length=0)
        for side in ("left", "bottom"):
            ax.spines[side].set_visible(False)
        cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.01)
        cb.set_label(f"Spearman of the draws with {METRIC_TEX[metric]}")
        cb.outline.set_visible(False)
        return save(fig, out, name)


def fig_sensitivity(s: Summary, out: Path) -> Path | None:
    """Spearman of each parameter's draws with eta* (the documents' primary metric)."""
    if s.sensitivity_ind is None:
        print("fig_sensitivity: skipped (no eta* sensitivities)")
        return None
    return sensitivity_heatmap(s, out, s.sensitivity_ind, "eta_ind", "fig_sensitivity.pdf")


def fig_sensitivity_eta(s: Summary, out: Path) -> Path | None:
    """The same against eta (the run's stored sensitivities)."""
    return sensitivity_heatmap(s, out, s.sensitivity, "eta", "fig_sensitivity_eta.pdf")


def fig_level(s: Summary, out: Path) -> Path | None:
    """Physical-AI evaluations by fidelity level. Top: eta and eta* at the
    median parameters on log axes (a zero, the prior already decisive, sits on the "0"
    row as an open marker), with Spearman's rho and its p-value in the
    title. Bottom, secondary: Youden's index and cost."""
    lev = s.out["level_ids"]
    if len(lev) < 2 or len({s.scenarios[i].level for i in lev}) < 2:
        print("fig_level: skipped (fewer than two physical-AI fidelity levels)")
        return None
    x = np.array([s.scenarios[i].level for i in lev])
    ids = [str(s.scenarios[i].id) for i in lev]
    o = s.out
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(FIG_W, 4.2))
        for a, metric, lab in ((axes[0, 0], "eta", r"$\eta=\mathrm{EVSI}/C$"),
                               (axes[0, 1], "eta_ind", r"$\eta^*=\mathrm{EVSI}^*/C$")):
            y = s.central[metric][lev]
            zero = ~(y > 0)
            floor = floor_of(y)
            yy = np.where(zero, floor, y)
            a.plot(x[~zero], yy[~zero], MARKER[PHYS], ls="", color=COLOR[PHYS], ms=4.5, mec="white", mew=0.4)
            a.plot(x[zero], yy[zero], MARKER[PHYS], ls="", mfc="white", mec=COLOR[PHYS], ms=4.5, mew=0.8)
            a.set_yscale("log")
            if zero.any():
                top = max(float(np.max(yy)), floor * 10)
                lo, hi = math.ceil(math.log10(floor) + 1), math.floor(math.log10(top))
                ticks = [10.0 ** k for k in range(lo, hi + 1)]
                a.yaxis.set_major_locator(mticker.FixedLocator([floor, *ticks]))
                a.yaxis.set_major_formatter(mticker.FuncFormatter(
                    lambda v, _, f=floor: "0" if math.isclose(v, f) else f"$10^{{{round(math.log10(v))}}}$"))
                a.yaxis.set_minor_locator(mticker.NullLocator())
            rho, p = o[f"level_rho_{metric}"], o[f"level_p_{metric}"]
            a.set_title("Spearman " + ("--" if rho is None else f"{rho:.2f}, p = {p:.2g}"), fontsize=MIN_FONT)
            a.set_ylabel(lab)
            place_labels(a, np.column_stack([x, yy]), ids)
        for a, y, lab in ((axes[1, 0], o["youden"][lev], "Youden's index $J=s+t-1$"),
                          (axes[1, 1], s.central["C"][lev], "cost $C$ (USD)")):
            a.plot(x, y, MARKER[PHYS], ls="", color=COLOR[PHYS], ms=4.5, mec="white", mew=0.4)
            a.set_ylabel(lab)
            place_labels(a, np.column_stack([x, y]), ids)
        axes[1, 0].set_ylim(0, 1)
        axes[1, 1].set_yscale("log")
        for a in axes.flat:
            a.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        for a in axes[1]:
            a.set_xlabel("fidelity level")
        return save(fig, out, "fig_level.pdf")


def fig_members(s: Summary, out: Path) -> Path | None:
    """Per parameter: member A's per-scenario median p50 (x) against member
    B's (two members) or against the median of the other members (more)."""
    labs = s.member_labels
    if len(labs) < 2:
        print("fig_members: skipped (one member)")
        return None
    mp = s.out["member_p50"]
    groups = [sc.group for sc in s.scenarios]
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 4, figsize=(FIG_W, 3.0))
        for extra in axes.ravel()[len(PARAM_NAMES):]:
            extra.set_visible(False)
        for ax, name in zip(axes.ravel()[:len(PARAM_NAMES)], PARAM_NAMES, strict=True):
            pairs = []
            if len(labs) == 2:
                pairs.append((labs[0], mp[name][labs[0]], mp[name][labs[1]]))
            else:
                for lab in labs:
                    others = np.vstack([mp[name][o] for o in labs if o != lab])
                    with np.errstate(all="ignore"):
                        pairs.append((lab, mp[name][lab], np.nanmedian(others, axis=0)))
            vals = []
            for k, (_lab, xa, yb) in enumerate(pairs):
                ok = np.isfinite(xa) & np.isfinite(yb)
                for g in sorted(set(groups), key=str):
                    m = ok & np.array([gg == g for gg in groups])
                    ec = MEMBER_COLORS[k % len(MEMBER_COLORS)] if len(pairs) > 1 else "white"
                    ax.plot(xa[m], yb[m], marker(g), ls="", ms=3, color=color(g), mec=ec, mew=0.4)
                vals += [xa[ok], yb[ok]]
            v = np.concatenate(vals) if vals else np.array([])
            if not v.size:
                ax.text(0.5, 0.5, "no scenario\nanswered by both", transform=ax.transAxes, ha="center",
                        va="center", fontsize=MIN_FONT, color=MUTED)
                ax.set_xticks([])
                ax.set_yticks([])
            else:
                if log_param(name):
                    ax.set_xscale("log")
                    ax.set_yscale("log")
                lo, hi = (v.min() / 2, v.max() * 2) if log_param(name) else (0, 1)
                ax.plot([lo, hi], [lo, hi], color=MUTED, lw=0.6, ls=":")
                ax.set_xlim(lo, hi)
                ax.set_ylim(lo, hi)
            ax.set_title(PARAM_LABEL[name].replace(" (USD)", ""), fontsize=7)
        xl = member_name(labs[0]) if len(labs) == 2 else "member"
        yl = member_name(labs[1]) if len(labs) == 2 else "median of the other members"
        fig.supxlabel(f"median of {xl}", fontsize=7)
        fig.supylabel(yl, fontsize=7)
        handles = group_handles(set(groups))
        if len(labs) > 2:
            handles += [plt.Line2D([], [], marker="o", ls="", ms=4, mfc="white", mew=1.0,
                                   mec=MEMBER_COLORS[k % len(MEMBER_COLORS)], label=member_name(lab))
                        for k, lab in enumerate(labs)]
        fig.legend(handles=handles, loc="outside upper center", ncol=min(len(handles), 4), frameon=False)
        return save(fig, out, "fig_members.pdf")


FIGURES = (fig_headline, fig_headline_small, fig_rows, fig_curve, fig_percentile_violins, fig_rank_star,
           fig_rank_eta, fig_best_physical_rank, fig_roc, fig_breakeven, fig_params, fig_sensitivity,
           fig_sensitivity_eta, fig_level, fig_members)


def write_all(s: Summary, out: Path) -> list[Path]:
    return [p for p in (fn(s, out) for fn in FIGURES) if p is not None]
