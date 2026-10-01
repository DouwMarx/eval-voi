"""The report figures (DESIGN section 7), PDF, drawn at the CoRL text width
(5.5 in) with no text smaller than 6.5 pt and no titles (captions live in
the tex). Two groups: physical AI (vermillion triangles) and LLM (blue
circles), Okabe-Ito colours, the marker shape a second encoding. The
pipeline diagram (F1's first panel) is TikZ in the tex, not here.

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

from voi_rank.analysis.summary import CURVE_QS, LLM, PHYS, Summary, log_param, order  # noqa: E402
from voi_rank.fit import PARAM_NAMES  # noqa: E402

logging.getLogger("fontTools").setLevel(logging.ERROR)   # TrueType embedding chatter
FIG_W = 5.5
FLOOR_STAGGER = (0.0, 0.3, -0.3)   # decades: the sub-rows of the zero row
MIN_FONT = 6.5
COLOR = {PHYS: "#D55E00", LLM: "#0072B2", None: "#7f7f7f"}
MARKER = {PHYS: "^", LLM: "o", None: "s"}
MEMBER_COLORS = ["#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000", "#F0E442"]
INK, MUTED, GRID = "#333333", "#8a8a8a", "#e3e3e3"
PARAM_LABEL = {"p": "$p$", "s": "$s$", "t": "$t$", "B": "$B$ (USD)", "K": "$K$ (USD)",
               "C_build": r"$C_\mathrm{build}$ (USD)", "C_run": r"$C_\mathrm{run}$ (USD)", "n": "$n$"}
STYLE = {
    "font.family": "serif", "mathtext.fontset": "cm", "font.size": 7,
    "axes.labelsize": 7, "xtick.labelsize": MIN_FONT, "ytick.labelsize": MIN_FONT,
    "legend.fontsize": MIN_FONT, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True,
    "axes.edgecolor": INK, "figure.constrained_layout.use": True, "pdf.fonttype": 42,
}


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


# --- labels ---------------------------------------------------------------------

OFFSETS = ((3.5, 2.0, "left", "bottom"), (-3.5, 2.0, "right", "bottom"), (3.5, -2.0, "left", "top"),
           (-3.5, -2.0, "right", "top"), (0.0, 4.5, "center", "bottom"), (0.0, -4.5, "center", "top"),
           (5.0, 0.0, "left", "center"), (-5.0, 0.0, "right", "center"))


def place_labels(ax, xy, texts, marker_pt: float = 5.0, avoid=()) -> None:
    """Label each point at the candidate offset that overlaps least with the
    markers, the labels already placed, the `avoid` artists and the outside
    of the axes (greedy, most crowded points first). Call once limits and
    layout are final."""
    fig = ax.figure
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    data = np.asarray(xy, dtype=float).reshape(-1, 2)
    pts = ax.transData.transform(data)
    half = marker_pt / 2.0 * fig.dpi / 72.0
    boxes = [np.array([x - half, y - half, x + half, y + half]) for x, y in pts]
    for a in avoid:
        e = a.get_window_extent(renderer)
        boxes.append(np.array([e.x0, e.y0, e.x1, e.y1]))
    fr = ax.get_window_extent(renderer)

    def overlap(b, o):
        return max(0.0, min(b[2], o[2]) - max(b[0], o[0])) * max(0.0, min(b[3], o[3]) - max(b[1], o[1]))

    frame = np.array([fr.x0, fr.y0, fr.x1, fr.y1])
    crowd = (np.hypot(*(pts[:, None, :] - pts[None, :, :]).transpose(2, 0, 1)) < 20.0).sum(axis=1)
    for i in sorted(range(len(pts)), key=lambda k: (-crowd[k], k)):
        ann = ax.annotate(texts[i], tuple(data[i]), textcoords="offset points", xytext=(0, 0),
                          fontsize=MIN_FONT, color=INK, zorder=4, annotation_clip=False)
        ann.set_in_layout(False)
        best = None
        for dx, dy, ha, va in OFFSETS:
            ann.set_position((dx, dy))
            ann.set_ha(ha)
            ann.set_va(va)
            e = ann.get_window_extent(renderer)
            b = np.array([e.x0, e.y0, e.x1, e.y1])
            area = (b[2] - b[0]) * (b[3] - b[1])
            cost = sum(overlap(b, o) for o in boxes) + 4.0 * (area - overlap(b, frame))
            if best is None or cost < best[0] - 1e-9:
                best = (cost, (dx, dy, ha, va), b)
        dx, dy, ha, va = best[1]
        ann.set_position((dx, dy))
        ann.set_ha(ha)
        ann.set_va(va)
        boxes.append(best[2])


# --- value against cost -----------------------------------------------------------

def floor_of(values) -> float:
    """The zero row's height: one decade below the smallest positive value."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v) & (v > 0)]
    return 10.0 ** (math.floor(math.log10(v.min())) - 1) if v.size else 1.0


def value_cost_panel(ax, s: Summary, metric: str, ylabel: str) -> None:
    """EVSI-type value (y) against C (x) at the central estimate, log-log
    with equal decades, iso-efficiency lines, the 'better' arrow along
    (-1, +1) in log space (orthogonal to the iso-lines), zero values on a
    floor row labelled 0, ids as labels."""
    x, y = s.central["C"], s.central[metric]
    zero = ~(y > 0)
    floor = floor_of(y)
    # the zero row, staggered over three sub-rows (by cost order) so its labels have room
    stagger = np.zeros(len(y))
    zi = np.flatnonzero(zero)
    stagger[zi[np.argsort(x[zi], kind="stable")]] = np.resize(FLOOR_STAGGER, len(zi))
    yy = np.where(zero, floor * 10.0 ** stagger, y)
    lx = [math.log10(x.min()) - 0.4, math.log10(x.max()) + 0.4]
    ly = [math.log10(floor) - 0.5 if zero.any() else math.log10(yy.min()) - 0.4,
          math.log10(yy.max()) + 0.6]
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
        # label where the line leaves the top or right edge
        xe = min(lx[1], ly[1] - k) - 0.35
        ye = xe + k
        if lx[0] + 0.5 < xe and ly[0] + 0.8 < ye < ly[1] - 0.05 and k % 2 == 0:
            ax.text(10 ** xe, 10 ** ye, rf"$\eta=10^{{{k}}}$", fontsize=MIN_FONT, color=MUTED,
                    rotation=45, rotation_mode="anchor", ha="right", va="bottom")
    if zero.any():
        ax.axhspan(10 ** ly[0], floor * 10 ** 0.45, color="#f3f3f3", lw=0, zorder=0.5)
        ticks = [10.0 ** k for k in range(math.ceil(math.log10(floor) + 1), math.floor(ly[1]) + 1)]
        ax.yaxis.set_major_locator(mticker.FixedLocator([floor, *ticks]))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: "0" if math.isclose(v, floor) else f"$10^{{{round(math.log10(v))}}}$"))
        ax.yaxis.set_minor_locator(mticker.NullLocator())
    groups = [sc.group for sc in s.scenarios]
    for g in sorted(set(groups), key=str):
        m = np.array([gg == g for gg in groups])
        ax.plot(x[m & ~zero], yy[m & ~zero], marker(g), ls="", color=color(g), ms=4.5, mec="white",
                mew=0.4, zorder=3)
        ax.plot(x[m & zero], yy[m & zero], marker(g), ls="", mfc="white", mec=color(g), ms=4.5,
                mew=0.8, zorder=3)
    arrow = ax.annotate("better", xy=(0.06, 0.94), xytext=(0.22, 0.78), xycoords="axes fraction",
                        textcoords="axes fraction", fontsize=MIN_FONT, color=INK, ha="left", va="top",
                        arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 0.8})
    ax.set_xlabel("cost $C$ (USD)")
    ax.set_ylabel(ylabel)
    handles = group_handles(groups)
    if zero.any():
        handles.append(plt.Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=4,
                                  label="cannot change the decision (value 0)"))
    ax.figure.legend(handles=handles, loc="outside upper center", ncol=len(handles), frameon=False,
                     handletextpad=0.3)
    place_labels(ax, np.column_stack([x, yy]), [str(sc.id) for sc in s.scenarios], avoid=[arrow])


def curve_panel(ax, s: Summary) -> None:
    o = s.out
    lo, med, hi = o["curve_q"].T
    ax.fill_between(CURVE_QS, lo, hi, color=COLOR[PHYS], alpha=0.25, lw=0, label="90% band over draws")
    ax.plot(CURVE_QS, med, color=COLOR[PHYS], lw=1.2, label="median over draws")
    ax.plot(CURVE_QS, o["curve_central"], color=INK, lw=0.9, ls="--", label="central estimate")
    ax.plot([0, 100], [1, 0], color=MUTED, lw=0.6, ls=":", label="same distribution as LLM")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.set_xlabel("percentile $q$ of the LLM evaluations' $\\eta$")
    ax.set_ylabel("P(physical-AI $\\eta$ > $q$-th percentile)")
    ax.legend(loc="upper right", frameon=False)


def fig_headline(s: Summary, out: Path) -> Path | None:
    with plt.rc_context(STYLE):
        if "curve_q" not in s.out:
            fig, ax = plt.subplots(figsize=(FIG_W / 2, FIG_W / 2 + 0.3))
            value_cost_panel(ax, s, "EVSI", "EVSI (USD)")
        else:
            fig, (ax, bx) = plt.subplots(1, 2, figsize=(FIG_W, FIG_W / 2 + 0.2))
            value_cost_panel(ax, s, "EVSI", "EVSI (USD)")
            curve_panel(bx, s)
        return save(fig, out, "fig_headline.pdf")


def fig_indifference(s: Summary, out: Path) -> Path | None:
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W * 0.6, FIG_W * 0.6 + 0.3))
        value_cost_panel(ax, s, "EVSI_ind", r"indifference value EVSI$^\circ$ (USD)")
        return save(fig, out, "fig_indifference.pdf")


# --- distributions per evaluation ------------------------------------------------------

def scenario_label(s: Summary, i: int) -> str:
    sc = s.scenarios[i]
    return f"{sc.id} {sc.short}"


def _violins(ax, data, positions, col):
    parts = ax.violinplot(data, positions=positions, orientation="horizontal", widths=0.8, showextrema=False,
                          points=120)
    for b in parts["bodies"]:
        b.set_facecolor(col)
        b.set_edgecolor("none")
        b.set_alpha(0.55)


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
                label="central estimate")
        ax.axvline(50, color=MUTED, lw=0.6, ls=":")
        ax.set_yticks(pos, [scenario_label(s, phys[k]) for k in rows])
        ax.set_xlim(0, 100)
        ax.set_xlabel("percentile among the LLM evaluations ($\\eta$)")
        ax.legend(loc="lower right", frameon=False)
        return save(fig, out, "fig_percentile_violins.pdf")


def fig_rank_intervals(s: Summary, out: Path) -> Path | None:
    o = s.out
    idx = order(s)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W, _rows_height(len(idx))))
        pos = np.arange(len(idx))[::-1]
        for p, i in zip(pos, idx, strict=True):
            g = s.scenarios[i].group
            lo, med, hi = o["rank_q"][i]
            ax.plot([lo, hi], [p, p], color=color(g), lw=2.0, alpha=0.6, solid_capstyle="round")
            ax.plot(o["rank_central"][i], p, marker(g), color=color(g), ms=4, mec="white", mew=0.4)
            ax.plot(med, p, "|", color=INK, ms=5)
        ax.set_yticks(pos, [scenario_label(s, i) for i in idx])
        ax.set_xlim(0.5, len(idx) + 0.5)
        ax.set_xlabel("rank by $\\eta$ (1 = best; bar: 90% interval over draws, |: median)")
        ax.legend(handles=group_handles({sc.group for sc in s.scenarios}), loc="lower right", frameon=False)
        ax.grid(axis="y", visible=False)
        return save(fig, out, "fig_rank_intervals.pdf")


def fig_breakeven(s: Summary, out: Path) -> Path | None:
    o = s.out
    idx = order(s)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(FIG_W, _rows_height(len(idx))))
        pos = np.arange(len(idx))[::-1]
        drawn = False
        for p, i in zip(pos, idx, strict=True):
            ns = s.draws["n_star"][i]
            v = np.log10(ns[np.isfinite(ns) & (ns > 0)])
            if v.size >= 2 and np.ptp(v) > 0:
                _violins(ax, [v], [p], color(s.scenarios[i].group))
                drawn = True
            ax.plot(math.log10(s.pooled["n"][i]), p, "x", color=INK, ms=4, mew=0.9)
            ax.annotate(f"{100 * o['p_pays'][i]:.0f}%", (1.0, p), xycoords=("axes fraction", "data"),
                        xytext=(3, 0), textcoords="offset points", va="center", fontsize=MIN_FONT,
                        color=INK, annotation_clip=False)
        if not drawn:
            print("fig_breakeven: skipped (no scenario has finite break-even draws)")
            plt.close(fig)
            return None
        ax.set_yticks(pos, [scenario_label(s, i) for i in idx])
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"$10^{{{v:g}}}$"))
        ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
        ax.set_xlabel("break-even reuse count $n^*$ (violin: finite draws; x: elicited $n$;"
                      " right: P(pays))")
        ax.legend(handles=group_handles({sc.group for sc in s.scenarios}), loc="lower right", frameon=False)
        ax.grid(axis="y", visible=False)
        return save(fig, out, "fig_breakeven.pdf")


# --- inputs --------------------------------------------------------------------------

def fig_params(s: Summary, out: Path) -> Path | None:
    """One panel per parameter: every member's elicited medians per scenario
    (colour = member) and the pooled median (black bar)."""
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
                lo, hi = ax.get_xlim()
                k0, k1 = math.ceil(math.log10(lo)), math.floor(math.log10(hi))
                step = max(1, math.ceil((k1 - k0 + 1) / 3))
                ax.xaxis.set_major_locator(mticker.FixedLocator([10.0 ** k for k in range(k0, k1 + 1, step)]))
                ax.xaxis.set_minor_locator(mticker.NullLocator())
                ax.tick_params(axis="x", labelrotation=90)
            else:
                ax.set_xlim(0, 1)
                ax.set_xticks([0, 0.5, 1], ["0", ".5", "1"])
            ax.set_title(PARAM_LABEL[name].replace(" (USD)", ""), fontsize=7)
            ax.grid(axis="y", visible=False)
        axes[0].set_yticks(pos, [scenario_label(s, i) for i in idx])
        axes[0].tick_params(axis="y", pad=10)
        for p, i in zip(pos, idx, strict=True):
            g = s.scenarios[i].group
            axes[0].plot([0.0], [p], marker(g), color=color(g), ms=3, clip_on=False,
                         transform=offset_copy(axes[0].get_yaxis_transform(), fig, x=-6, units="points"))
        handles = [plt.Line2D([], [], marker="o", ls="", ms=3, color=MEMBER_COLORS[k % len(MEMBER_COLORS)],
                              label=lab) for k, lab in enumerate(labs)]
        handles.append(plt.Line2D([], [], marker="|", ls="", ms=5, color=INK, label="pooled median"))
        handles += group_handles({sc.group for sc in s.scenarios})
        fig.legend(handles=handles, loc="outside upper center", ncol=min(len(handles), 5), frameon=False)
        fig.supxlabel("elicited median per valid elicitation (USD for $B$, $K$, $C_\\mathrm{build}$,"
                      " $C_\\mathrm{run}$)", fontsize=7)
        return save(fig, out, "fig_params.pdf")


def fig_sensitivity(s: Summary, out: Path) -> Path | None:
    idx = order(s)
    mat = s.sensitivity[idx]
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
        cb.set_label("Spearman of the draws with $\\eta$")
        cb.outline.set_visible(False)
        return save(fig, out, "fig_sensitivity.pdf")


def fig_level(s: Summary, out: Path) -> Path | None:
    lev = s.out["level_ids"]
    if len(lev) < 2 or len({s.scenarios[i].level for i in lev}) < 2:
        print("fig_level: skipped (fewer than two physical-AI fidelity levels)")
        return None
    x = np.array([s.scenarios[i].level for i in lev])
    with plt.rc_context(STYLE):
        fig, (ax, bx) = plt.subplots(1, 2, figsize=(FIG_W, 2.2))
        for a, y, lab in ((ax, s.out["youden"][lev], "Youden's index $J=s+t-1$"),
                          (bx, s.central["C"][lev], "cost $C$ (USD)")):
            a.plot(x, y, MARKER[PHYS], ls="", color=COLOR[PHYS], ms=4.5, mec="white", mew=0.4)
            a.set_xlabel("fidelity level")
            a.set_ylabel(lab)
            a.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.set_ylim(0, 1)
        bx.set_yscale("log")
        for a, y in ((ax, s.out["youden"][lev]), (bx, s.central["C"][lev])):
            place_labels(a, np.column_stack([x, y]), [str(s.scenarios[i].id) for i in lev])
        return save(fig, out, "fig_level.pdf")


def fig_members(s: Summary, out: Path) -> Path | None:
    """Per parameter: member A's per-scenario pooled p50 (x) against member
    B's (two members) or against the median of the other members (more)."""
    labs = s.member_labels
    if len(labs) < 2:
        print("fig_members: skipped (one member)")
        return None
    mp = s.out["member_p50"]
    groups = [sc.group for sc in s.scenarios]
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 4, figsize=(FIG_W, 3.0))
        for ax, name in zip(axes.ravel(), PARAM_NAMES, strict=True):
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
        xl = labs[0] if len(labs) == 2 else "member"
        yl = labs[1] if len(labs) == 2 else "median of the other members"
        fig.supxlabel(f"pooled median of {xl}", fontsize=7)
        fig.supylabel(yl, fontsize=7)
        handles = group_handles(set(groups))
        if len(labs) > 2:
            handles += [plt.Line2D([], [], marker="o", ls="", ms=4, mfc="white", mew=1.0,
                                   mec=MEMBER_COLORS[k % len(MEMBER_COLORS)], label=lab)
                        for k, lab in enumerate(labs)]
        fig.legend(handles=handles, loc="outside upper center", ncol=min(len(handles), 4), frameon=False)
        return save(fig, out, "fig_members.pdf")


FIGURES = (fig_headline, fig_indifference, fig_percentile_violins, fig_rank_intervals, fig_breakeven,
           fig_params, fig_sensitivity, fig_level, fig_members)


def write_all(s: Summary, out: Path) -> list[Path]:
    return [p for p in (fn(s, out) for fn in FIGURES) if p is not None]
