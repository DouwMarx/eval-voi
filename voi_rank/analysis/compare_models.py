"""Binary model vs Gaussian-state family on the same scenarios (spec v2.1 §4),
reading only from a study's voi.db. Over the scenarios ranked by both the
latest run of the binary protocol and the latest run of the Gaussian
protocol, writes to <study>/report/generated/:

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
  Gaussian protocol's valid elicitations, the fraction flagged, and their
  Spearman with the cross-repeat spread of the corresponding quantity
  (per-scenario median residual vs db.elicited_spread of the quantity: (max -
  min) / pooled p50 of the repeat values, or max - min for d, which crosses
  zero, as everywhere else).
- macros_compare.tex: \\voiGaussRhoQuad, \\voiGaussRhoKg, \\voiGaussRhoStep,
  \\voiGaussRhoStepfix, \\voiGaussTopOverlapStepfix, \\voiGaussRhoP, \\voiGaussRhoS,
  \\voiGaussRhoT, \\voiGaussGateAgree, \\voiGaussN (+ the run ids).

Usage: python -m voi_rank.analysis.compare_models --study PATH [--binary p001] [--gaussian g001]
       [--members claude_cli:sonnet,claude_cli:opus]
(--members selects, for BOTH protocols, the latest run that pooled exactly
that member subset, so the two framings are compared on the same elicitors;
the derived-vs-elicited panel pools the binary protocol's medians over the
same subset)
"""

from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from voi_rank import db  # noqa: E402
from voi_rank.analysis import figures  # noqa: E402
from voi_rank.analysis.tables import esc, num, pooled_p50  # noqa: E402
from voi_rank.gauss_fit import THRESHOLDS, consistency_score  # noqa: E402
from voi_rank.gaussian import ACTION_MODELS  # noqa: E402
from voi_rank.sensitivity import spearman  # noqa: E402
from voi_rank.study import Study, add_study_arg  # noqa: E402

EVSI_ZERO_USD = 1e-6
TOP_N = 10
MODEL_MACRO = {"quad": "Quad", "kg": "Kg", "step": "Step", "stepfix": "Stepfix"}
# residual-carrying quantities: (stored name, label, spread of which quantity)
RESIDUALS = (("g_sigma0", r"$\theta$ triple asymmetry", "g_sigma0"),
             ("g_d", r"$d$ mismatch (sd units)", "g_d"),
             ("g_x", r"$x$ route spread (log units)", "g_x"),
             ("g_k", r"$k$ mismatch", "g_k"))
OUTPUTS = ("compare_models.tex", "fig_compare_models.pdf", "fig_derived_pst.pdf",
           "consistency_gauss.tex", "macros_compare.tex")


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
    (Gaussian run), "rho", "mad"}} for p, s, t."""
    out = {}
    labels = db.run_member_labels(b_run)
    for name in ("p", "s", "t"):
        der = medians(con, g_run["id"], f"{name}_derived")
        pts = [(pooled_p50(con, b_run["protocol_id"], s, name, labels), der[s]) for s in shared if s in der]
        pts = [(x, y) for x, y in pts if x is not None]
        x = np.array([p[0] for p in pts], dtype=float)
        y = np.array([p[1] for p in pts], dtype=float)
        out[name] = {"x": x, "y": y, "rho": spearman(x, y) if len(pts) >= 3 else None,
                     "mad": float(np.median(np.abs(y - x))) if len(pts) else None, "n": len(pts)}
    return out


def residual_stats(con, g_run) -> dict:
    """Per residual quantity: quantiles over valid elicitations, fraction
    flagged, and the Spearman between the per-scenario median residual and
    the cross-repeat spread of the quantity; plus the consistency-score
    quantiles (max residual / threshold per elicitation)."""
    pid = g_run["protocol_id"]
    rows = con.execute(
        "SELECT e.id AS eid, e.scenario_id, p.name, p.p50, p.fit_residual, p.fit_warning"
        " FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=? AND e.valid=1", (pid,)).fetchall()
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
            spread = db.elicited_spread(con, pid, sid, spread_of)
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


def write_consistency(res: dict, g_run, out: Path) -> None:
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
    lines += [r"\bottomrule", r"\end{tabular}", r"\par\medskip",
              r"\noindent\emph{Over-determination residuals of the Gaussian protocol (run "
              + str(g_run["id"]) + r"), over its valid elicitations: quantiles, the warning"
              r" threshold, the fraction of elicitations flagged, and the Spearman between each"
              r" scenario's median residual and the cross-repeat spread of the quantity the"
              r" residual checks ((max - min) / pooled p50 of the repeat values; max - min"
              r" in sd units for $d$, which crosses zero).}"]
    (out / "consistency_gauss.tex").write_text("\n".join(lines) + "\n")


def write_macros(rs: dict, pst: dict, b_run, g_run, out: Path) -> dict:
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
    (out / "macros_compare.tex").write_text(
        "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in macros.items()) + "\n")
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
        ax.text(0.96, 0.05, f"$\\rho$ = {rho}, med |diff| = {mad} (n={st['n']})",
                transform=ax.transAxes, fontsize=6.5, ha="right")
        ax.tick_params(labelsize=7)
    fig.suptitle("Derived p = Phi(d), s, t (fixed mark at theta_c) vs the binary elicitation", fontsize=8)
    fig.savefig(out / "fig_derived_pst.pdf")
    plt.close(fig)


def make_all(con, b_run, g_run, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(figures.STYLE)
    rs = rank_stats(con, b_run, g_run)
    pst = derived_vs_elicited(con, b_run, g_run, rs["shared"])
    res = residual_stats(con, g_run)
    write_compare(rs, b_run, g_run, out)
    write_consistency(res, g_run, out)
    macros = write_macros(rs, pst, b_run, g_run, out)
    fig_compare(con, rs, out)
    fig_derived(pst, out)
    return {"rank": rs, "pst": pst, "residuals": res, "macros": macros}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    ap.add_argument("--binary", default="p001", help="binary protocol (latest run; default p001)")
    ap.add_argument("--gaussian", default="g001", help="Gaussian protocol (latest run; default g001)")
    ap.add_argument("--members", default=None,
                    help="comma-separated provider:model subset: the latest run of each protocol"
                         " that pooled exactly these members")
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    b_run, g_run = select_runs(con, args.binary, args.gaussian, db.parse_member_labels(args.members))
    result = make_all(con, b_run, g_run, study.generated_dir)
    ag = result["rank"]["agreement"]
    print(f"{len(result['rank']['shared'])} shared scenarios; Spearman binary vs "
          + ", ".join(f"{m} {num(ag[('binary', m)]['rho'], '{:.2f}')}" for m in ACTION_MODELS)
          + f"; gate agreement {100 * result['rank']['gate']['agree']:.0f}%")
    print("wrote " + ", ".join(str(study.generated_dir / f) for f in OUTPUTS))


if __name__ == "__main__":
    main()
