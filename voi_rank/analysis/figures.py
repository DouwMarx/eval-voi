"""All report figures (spec §8), reading only from a study's voi.db. PDFs land
in <study>/report/generated/.

Usage: python -m voi_rank.analysis.figures --study studies/business [--protocol p001] [--run ID]
(default: the latest run of protocol p001; --run overrides)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import gaussian_kde  # noqa: E402

from voi_rank import db, mc  # noqa: E402
from voi_rank.fit import FAMILY_BY_PARAM, GAUSS_LOG_PARAMS, GAUSS_USD_PARAMS  # noqa: E402
from voi_rank.sensitivity import repeat_spread  # noqa: E402
from voi_rank.study import Study, add_study_arg  # noqa: E402

ACCENT = "#0072B2"          # single hue for single-series marks
INTERVAL = "#9aa5b1"        # recessive interval lines
# Okabe-Ito, fixed order, CVD-safe (used only where several series need identity)
CATEGORICAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7",
               "#56B4E9", "#F0E442", "#000000"]

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
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    return db.protocol_members(prot)


def add_run_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--protocol", default="p001",
                    help="use the latest run of this protocol (default: p001)")
    ap.add_argument("--run", type=int, default=None, help="explicit run id (overrides --protocol)")


def select_run(con, run_id: int | None, protocol: str):
    """The run to analyse: --run when given, else the latest run of the
    protocol. A run made by the v1 model (no data_hash, or sensitivities for
    the retired parameter e) is refused: its numbers contradict the v2
    commentary and its draws do not replay. Prints 'run <id> (protocol <name>)'."""
    run = db.get_run(con, run_id) if run_id is not None else db.latest_run(con, protocol)
    prot = con.execute("SELECT name FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    name = prot["name"] if prot else "unknown"
    reason = db.run_predates_v2(con, run)
    if reason:
        raise RuntimeError(f"run {run['id']} (protocol {name}) predates the v2 model: {reason};"
                           f" run `python -m voi_rank.mc --protocol {name}` first")
    print(f"run {run['id']} (protocol {name})")
    return run


# --- figures ----------------------------------------------------------------

def fig_ranking(con, run_id, out: Path):
    metric = primary_metric(con, run_id)
    eff = metric_rows(con, run_id, metric)
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
    ax.text(1.35, len(order) - 0.35, "EVSI = C", fontsize=6.5, color="#555555",
            rotation=90, va="top")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{sid} · {ttl[sid][:52]}" for sid in reversed(order)], fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel(f"{metric} = {evsi_metric(con, run_id)} / C (log scale)")
    ax.set_title(f"Ranking by median {metric}")
    ax.grid(axis="y", visible=False)
    fig.savefig(out / "fig_ranking.pdf")
    plt.close(fig)
    return True


def fig_evsi_vs_cost(con, run_id, out: Path):
    """Headline figure: median EVSI vs the run's median C (the same pooled
    cost mixture the efficiency ranking divides by, so the iso-efficiency
    diagonals agree with the ranking table), log-log, with thin q05-q95 EVSI
    bars, points coloured by scenario group when the study has groups,
    iso-efficiency diagonals and the top 10 labelled by id."""
    evsi_name = evsi_metric(con, run_id)
    evsi = metric_rows(con, run_id, evsi_name)
    order = ranked_ids(con, run_id)
    run = db.get_run(con, run_id)
    groups = scenario_groups(con)
    xs = np.array([c_quantiles(con, run, s)[1] for s in order])
    y50 = np.array([evsi[s]["q50"] or 0.0 for s in order])
    y05 = np.array([evsi[s]["q05"] or 0.0 for s in order])
    y95 = np.array([evsi[s]["q95"] or 0.0 for s in order])
    floored = y50 < EVSI_FLOOR
    y50f = np.maximum(y50, EVSI_FLOOR)
    lo = np.maximum(y05, EVSI_FLOOR)
    hi = np.maximum(y95, EVSI_FLOOR)

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
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
        ax.plot(xs[m0], y50f[m0], "o", mfc="white", mec=color, ms=5, zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    xlim = np.array([xs.min() / 3, xs.max() * 3])
    ylim = np.array([EVSI_FLOOR / 2, max(hi.max(), EVSI_FLOOR) * 10])
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
    for i, sid in enumerate(order[:10]):
        ax.annotate(str(sid), (xs[i], y50f[i]), textcoords="offset points",
                    xytext=(4, 4) if i % 2 == 0 else (-4, -9),
                    ha="left" if i % 2 == 0 else "right",
                    fontsize=7, color="#333333", zorder=4)
    ax.annotate("better\n(more decision value per dollar)",
                xy=(0.03, 0.97), xytext=(0.16, 0.80),
                xycoords="axes fraction", textcoords="axes fraction",
                fontsize=7, color="#333333", ha="left", va="top",
                arrowprops={"arrowstyle": "-|>", "color": "#333333", "lw": 0.9})
    if grp_names:
        ax.legend(fontsize=6.5, loc="lower right", frameon=False, title="group",
                  title_fontsize=6.5)
    ax.set_xlabel("median C (run mixture, USD)")
    ax.set_ylabel(f"median {evsi_name} (USD per measurement)")
    ax.set_title(f"Median {evsi_name} vs median cost (bars: q05–q95; top 10 labelled by id)")
    fig.savefig(out / "fig_evsi_vs_cost.pdf")
    plt.close(fig)
    return True


def fig_param_medians(con, run_id, out: Path):
    """Six panels, one per parameter: the elicited p50 of every valid
    elicitation of the run's protocol against the scenario's efficiency rank
    (jittered strip), coloured by member model when the protocol has several
    members, with a marginal histogram on the right. Reveals round-number
    clustering and cross-model disagreement. USD panels on a log axis."""
    run = db.get_run(con, run_id)
    names = run_param_names(con, run_id)
    order = ranked_ids(con, run_id)
    rank_of = {sid: i + 1 for i, sid in enumerate(order)}
    members = [db.member_label(m) for m in run_members(con, run)]
    rows = con.execute(
        "SELECT e.scenario_id, e.provider || ':' || e.model AS member, p.name, p.p50"
        " FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=? AND e.valid=1", (run["protocol_id"],)).fetchall()
    data: dict[str, dict[str, list]] = {n: {} for n in names}
    for r in rows:
        if r["name"] in data and r["scenario_id"] in rank_of:
            data[r["name"]].setdefault(r["member"], []).append((rank_of[r["scenario_id"]], r["p50"]))
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
    n_elic = con.execute("SELECT COUNT(*) FROM elicitations WHERE protocol_id=? AND valid=1",
                         (run["protocol_id"],)).fetchone()[0]
    fig.suptitle(f"Elicited medians per parameter, every valid elicitation ({n_elic} elicitations)",
                 fontsize=9)
    fig.savefig(out / "fig_param_medians.pdf")
    plt.close(fig)
    return True


def fig_by_level(con, run_id, out: Path):
    """Median EVSI, efficiency and C against attributes.level, with q05-q95
    intervals, grouped by grp. Skipped silently when no scenario carries a
    numeric level."""
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
        (f"median {evsi_name} (USD)", lambda s: (evsi[s]["q05"], evsi[s]["q50"], evsi[s]["q95"]),
         EVSI_FLOOR),
        (f"{eff_name} = {evsi_name} / C", lambda s: (eff[s]["q05"], eff[s]["q50"], eff[s]["q95"]),
         EFF_FLOOR),
        ("cost C (USD)", lambda s: c_quantiles(con, run, s), 1.0),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(6.2, 2.7))
    for ax, (ylabel, q_of, floor) in zip(axes, panels, strict=True):
        for gi, g in enumerate(grp_names):
            sids = [s for s in order if (groups[s] or "(no group)") == g]
            if not sids:
                continue
            x = np.array([levels[s] for s in sids]) + offsets[gi]
            q = np.array([q_of(s) for s in sids], dtype=float)
            q = np.maximum(np.nan_to_num(q, nan=0.0), floor)
            ax.errorbar(x, q[:, 1], yerr=[q[:, 1] - q[:, 0], q[:, 2] - q[:, 1]],
                        fmt="o", ms=3.5, color=colors[g], ecolor=colors[g], alpha=0.85,
                        elinewidth=0.6, capsize=0, mec="white", mew=0.4, label=g)
        ax.set_yscale("log")
        ax.set_ylabel(ylabel, fontsize=8)
        ax.set_xlabel("level", fontsize=8)
        ax.set_xticks(sorted(set(levels.values())))
        ax.tick_params(labelsize=7)
    if len(grp_names) > 1:
        axes[0].legend(fontsize=6, frameon=False, loc="best")
    fig.suptitle("Decision value, efficiency and cost by scenario level (bars: q05–q95)",
                 fontsize=9)
    fig.savefig(out / "fig_by_level.pdf")
    plt.close(fig)
    return True


def fig_sensitivity_heatmap(con, run_id, out: Path):
    order = ranked_ids(con, run_id)
    names = run_param_names(con, run_id)
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


def fig_elicitation_noise(con, run_id, out: Path):
    run = db.get_run(con, run_id)
    names = run_param_names(con, run_id)
    spreads = {name: [] for name in names}
    sids = [r[0] for r in con.execute(
        "SELECT DISTINCT scenario_id FROM elicitations WHERE protocol_id=? AND valid=1",
        (run["protocol_id"],))]
    for name in names:
        for sid in sids:
            sp = repeat_spread(db.elicited_p50s(con, run["protocol_id"], sid, name))
            if sp is not None:
                spreads[name].append(sp)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    data = [spreads[n] for n in names]
    if any(len(d) for d in data):
        ax.boxplot(data, tick_labels=[f"${esc_math(n)}$" for n in names], showfliers=True,
                   flierprops={"marker": ".", "ms": 3, "mec": INTERVAL},
                   medianprops={"color": ACCENT, "lw": 1.5},
                   boxprops={"color": "#555555"},
                   whiskerprops={"color": "#555555"},
                   capprops={"color": "#555555"})
        ax.set_ylabel("(max − min) / pooled p50 across elicitations")
        ax.set_title(f"Cross-elicitation noise per parameter ({len(sids)} scenarios)")
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
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    run_id = select_run(con, args.run, args.protocol)["id"]
    for name in make_all(con, run_id, study.generated_dir):
        print(f"wrote {study.generated_dir / (name + '.pdf')}")


if __name__ == "__main__":
    main()
