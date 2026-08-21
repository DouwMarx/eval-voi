"""All report figures (spec §8), reading only from voi.db. PDFs land in
report/generated/.

Usage: python -m analysis.figures [--run ID]   (default: latest run)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

from core import mc
from core.sensitivity import repeat_spread
from db import io

OUT = io.ROOT / "report" / "generated"

ACCENT = "#0072B2"          # single hue for single-series marks
INTERVAL = "#9aa5b1"        # recessive interval lines
# Okabe-Ito, fixed order, CVD-safe (used only where several series need identity)
CATEGORICAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7"]

EFF_FLOOR = 1e-3            # log-axis floor for zero medians/quantiles
EVSI_FLOOR = 1e-2           # USD floor for the log-log scatter

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


def metric_rows(con, run_id: int, metric: str) -> dict[int, dict]:
    return {r["scenario_id"]: dict(r) for r in con.execute(
        "SELECT * FROM results WHERE run_id=? AND metric=?", (run_id, metric))}


def titles(con) -> dict[int, str]:
    return {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}


def ranked_ids(con, run_id: int) -> list[int]:
    """Scenario ids ordered by median efficiency (desc), tie-break p_positive."""
    eff = metric_rows(con, run_id, "efficiency")
    return sorted(eff, key=lambda s: (-(eff[s]["q50"] or 0.0),
                                      -(eff[s]["p_positive"] or 0.0), s))


def fig_ranking(con, run_id):
    eff = metric_rows(con, run_id, "efficiency")
    order = ranked_ids(con, run_id)[:25]
    ttl = titles(con)
    fig, ax = plt.subplots(figsize=(6.2, 0.26 * len(order) + 1.0))
    for y, sid in enumerate(reversed(order)):
        r = eff[sid]
        lo = max(r["q05"] or 0.0, EFF_FLOOR)
        hi = max(r["q95"] or 0.0, EFF_FLOOR)
        ax.hlines(y, lo, hi, color=INTERVAL, lw=1.4)
        q50 = r["q50"] or 0.0
        if q50 >= EFF_FLOOR:
            ax.plot(q50, y, "o", color=ACCENT, ms=4.5)
        else:
            ax.plot(EFF_FLOOR, y, "o", mfc="white", mec=ACCENT, ms=4.5)
    ax.axvline(1.0, color="#555555", lw=0.8, ls="--")
    ax.text(1.35, 0.1, "EVSI = C", fontsize=6.5, color="#555555", rotation=90,
            va="bottom")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{sid} · {ttl[sid][:52]}" for sid in reversed(order)], fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("efficiency = EVSI / C (log scale)")
    ax.set_title("Ranking by median efficiency")
    ax.grid(axis="y", visible=False)
    fig.savefig(OUT / "fig_ranking.pdf")
    plt.close(fig)


def fig_evsi_vs_cost(con, run_id):
    evsi = metric_rows(con, run_id, "EVSI")
    eff_order = ranked_ids(con, run_id)
    # median C comes from the parameters table (pooled p50 across valid repeats)
    run = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    c_med = {}
    for sid in eff_order:
        p50s = [r[0] for r in con.execute(
            "SELECT p.p50 FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
            " WHERE e.scenario_id=? AND e.protocol_id=? AND e.valid=1 AND p.name='C'",
            (sid, run["protocol_id"]))]
        c_med[sid] = float(np.median(p50s))
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    xs = np.array([c_med[s] for s in eff_order])
    ys = np.array([evsi[s]["q50"] or 0.0 for s in eff_order])
    floored = ys < EVSI_FLOOR
    ax.plot(xs[~floored], ys[~floored], "o", color=ACCENT, ms=5, mec="white", mew=0.5)
    ax.plot(xs[floored], np.full(floored.sum(), EVSI_FLOOR), "o",
            mfc="white", mec=ACCENT, ms=5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    xlim = np.array([xs.min() / 3, xs.max() * 3])
    ylim = np.array([EVSI_FLOOR / 2, max(ys.max(), EVSI_FLOOR) * 30])
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    for k in range(-2, 4):
        ax.plot(xlim, 10.0**k * xlim, ls="--", lw=0.7, color="#c9c9c9", zorder=0)
        x_lab = min(xlim[1] * 0.55, ylim[1] * 0.35 / 10.0**k)
        y_lab = 10.0**k * x_lab
        if xlim[0] * 1.5 < x_lab and ylim[0] * 3 < y_lab < ylim[1] * 0.7:
            p0 = ax.transData.transform((x_lab, y_lab))
            p1 = ax.transData.transform((x_lab * 2, y_lab * 2))
            angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
            ax.text(x_lab, y_lab * 1.25, f"eff $= 10^{{{k}}}$", fontsize=6,
                    color="#8a8a8a", rotation=angle, rotation_mode="anchor")
    for sid in eff_order[:10]:
        y = max(evsi[sid]["q50"] or 0.0, EVSI_FLOOR)
        ax.annotate(str(sid), (c_med[sid], y), textcoords="offset points",
                    xytext=(4, 4), fontsize=7, color="#333333")
    ax.set_xlabel("median measurement cost C (USD, pooled elicited p50)")
    ax.set_ylabel("median EVSI (USD per measurement)")
    ax.set_title("Median EVSI vs median cost (top 10 labeled by id)")
    fig.savefig(OUT / "fig_evsi_vs_cost.pdf")
    plt.close(fig)


def fig_sensitivity_heatmap(con, run_id):
    order = ranked_ids(con, run_id)
    mat = np.full((len(io.PARAM_NAMES), len(order)), np.nan)
    for r in con.execute("SELECT * FROM sensitivities WHERE run_id=?", (run_id,)):
        if r["spearman"] is not None and r["scenario_id"] in order:
            mat[io.PARAM_NAMES.index(r["param"]), order.index(r["scenario_id"])] = \
                abs(r["spearman"])
    vmax = max(0.3, float(np.ceil(np.nanmax(mat) * 10) / 10)) if np.isfinite(mat).any() else 1.0
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    im = ax.imshow(mat, aspect="auto", cmap="Blues", vmin=0, vmax=vmax,
                   interpolation="nearest")
    ax.set_yticks(range(len(io.PARAM_NAMES)))
    ax.set_yticklabels(io.PARAM_NAMES)
    step = max(1, len(order) // 30)
    ax.set_xticks(range(0, len(order), step))
    ax.set_xticklabels([order[i] for i in range(0, len(order), step)], fontsize=5,
                       rotation=90)
    ax.set_xlabel("scenario id, ordered by efficiency rank (best left)")
    ax.set_title("Parameter influence on efficiency: |Spearman ρ| per scenario")
    ax.grid(visible=False)
    fig.colorbar(im, ax=ax, label=r"|Spearman $\rho$|", shrink=0.9)
    fig.savefig(OUT / "fig_sensitivity_heatmap.pdf")
    plt.close(fig)


def fig_headroom(con, run_id):
    head = metric_rows(con, run_id, "headroom")
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
    fig.savefig(OUT / "fig_headroom.pdf")
    plt.close(fig)


def fig_rank_stability(con, run_id):
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
    fig.savefig(OUT / "fig_rank_stability.pdf")
    plt.close(fig)


def fig_elicitation_noise(con, run_id):
    run = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    spreads = {name: [] for name in io.PARAM_NAMES}
    sids = [r[0] for r in con.execute(
        "SELECT DISTINCT scenario_id FROM elicitations WHERE protocol_id=? AND valid=1",
        (run["protocol_id"],))]
    for name in io.PARAM_NAMES:
        for sid in sids:
            p50s = [r[0] for r in con.execute(
                "SELECT p.p50 FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
                " WHERE e.scenario_id=? AND e.protocol_id=? AND e.valid=1 AND p.name=?",
                (sid, run["protocol_id"], name))]
            sp = repeat_spread(p50s)
            if sp is not None:
                spreads[name].append(sp)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    data = [spreads[n] for n in io.PARAM_NAMES]
    if any(len(d) for d in data):
        ax.boxplot(data, tick_labels=io.PARAM_NAMES, showfliers=True,
                   flierprops={"marker": ".", "ms": 3, "mec": INTERVAL},
                   medianprops={"color": ACCENT, "lw": 1.5},
                   boxprops={"color": "#555555"},
                   whiskerprops={"color": "#555555"},
                   capprops={"color": "#555555"})
        ax.set_ylabel("(max − min) / pooled p50 across repeats")
        ax.set_title(f"Cross-repeat elicitation noise per parameter ({len(sids)} scenarios)")
    else:
        ax.text(0.5, 0.5, "protocol has k = 1: no repeat noise", ha="center",
                transform=ax.transAxes)
    fig.savefig(OUT / "fig_elicitation_noise.pdf")
    plt.close(fig)


def fig_top5_densities(con, run_id):
    ids, eff = mc.replay_efficiency(con, run_id)
    order = ranked_ids(con, run_id)[:5]
    ttl = titles(con)
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    for color, sid in zip(CATEGORICAL, order):
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
    fig.savefig(OUT / "fig_top5_densities.pdf")
    plt.close(fig)


ALL_FIGURES = [fig_ranking, fig_evsi_vs_cost, fig_sensitivity_heatmap,
               fig_headroom, fig_rank_stability, fig_elicitation_noise,
               fig_top5_densities]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(io.DEFAULT_DB))
    ap.add_argument("--run", type=int, default=None, help="run id (default: latest)")
    args = ap.parse_args()
    con = io.connect(args.db)
    run_id = args.run if args.run is not None else io.latest_run(con)["id"]
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(STYLE)
    for f in ALL_FIGURES:
        f(con, run_id)
        print(f"wrote {OUT / (f.__name__ + '.pdf')}")


if __name__ == "__main__":
    main()
