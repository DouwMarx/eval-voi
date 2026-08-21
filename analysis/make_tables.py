"""LaTeX table fragments + macros (spec §8), reading only from voi.db.
Writes to report/generated/.

Usage: python -m analysis.make_tables [--run ID]   (default: latest run)
"""

from __future__ import annotations

import argparse

import numpy as np

from analysis.figures import metric_rows, ranked_ids
from db import io

OUT = io.ROOT / "report" / "generated"

LATEX_SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
                  "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
                  "^": r"\textasciicircum{}"}


def esc(text: str) -> str:
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in str(text))


def money(v: float) -> str:
    if v is None:
        return "--"
    if v >= 1e6:
        return f"{v/1e6:.3g}M"
    if v >= 1e3:
        return f"{v/1e3:.3g}k"
    return f"{v:.3g}"


def num(v: float, fmt: str = "{:.3g}") -> str:
    return "--" if v is None else fmt.format(v)


def pooled_p50(con, protocol_id: int, sid: int, name: str) -> float | None:
    p50s = [r[0] for r in con.execute(
        "SELECT p.p50 FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.scenario_id=? AND e.protocol_id=? AND e.valid=1 AND p.name=?",
        (sid, protocol_id, name))]
    return float(np.median(p50s)) if p50s else None


def write_catalog(con, run):
    """Scenario catalog with pooled elicited medians for the run's protocol."""
    order = ranked_ids(con, run["id"])
    lines = [
        r"\begin{longtable}{@{}rp{5.6cm}rrrrrrr@{}}",
        r"\caption{Scenario catalog with pooled elicited medians (p50 across valid"
        r" repeats). B, K, C in USD.}\label{tab:catalog}\\",
        r"\toprule",
        r"id & scenario & $p$ & $s$ & $t$ & $e$ & $B$ & $K$ & $C$\\",
        r"\midrule\endfirsthead",
        r"\toprule id & scenario & $p$ & $s$ & $t$ & $e$ & $B$ & $K$ & $C$\\"
        r"\midrule\endhead",
        r"\bottomrule\endfoot",
    ]
    ttl = {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}
    for sid in order:
        vals = {n: pooled_p50(con, run["protocol_id"], sid, n) for n in io.PARAM_NAMES}
        lines.append(
            f"{sid} & {esc(ttl[sid][:70])} & {num(vals['p'], '{:.2f}')} &"
            f" {num(vals['s'], '{:.2f}')} & {num(vals['t'], '{:.2f}')} &"
            f" {num(vals['e'], '{:.2f}')} & {money(vals['B'])} & {money(vals['K'])} &"
            f" {money(vals['C'])}\\\\")
    lines.append(r"\end{longtable}")
    (OUT / "catalog.tex").write_text("\n".join(lines) + "\n")


def top_param(con, run_id: int, sid: int) -> str:
    rows = con.execute(
        "SELECT param, spearman FROM sensitivities WHERE run_id=? AND scenario_id=?"
        " AND spearman IS NOT NULL", (run_id, sid)).fetchall()
    if not rows:
        return "--"
    best = max(rows, key=lambda r: abs(r["spearman"]))
    return f"${esc(best['param'])}$"


def write_ranking(con, run, top_n: int = 25):
    eff = metric_rows(con, run["id"], "efficiency")
    order = ranked_ids(con, run["id"])[:top_n]
    ttl = {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}
    lines = [
        r"\begin{longtable}{@{}rrp{6.0cm}rrrrl@{}}",
        r"\caption{Final ranking by median efficiency (EVSI/C). $P_+$ = P(EVSI $>$ C)"
        r" across draws; last column = parameter with largest $|\rho|$ vs"
        r" efficiency.}\label{tab:ranking}\\",
        r"\toprule",
        r"rank & id & scenario & $\mathrm{eff}_{q05}$ & $\mathrm{eff}_{q50}$ &"
        r" $\mathrm{eff}_{q95}$ & $P_+$ & top\\",
        r"\midrule\endfirsthead",
        r"\toprule rank & id & scenario & $\mathrm{eff}_{q05}$ & $\mathrm{eff}_{q50}$ &"
        r" $\mathrm{eff}_{q95}$ & $P_+$ & top\\\midrule\endhead",
        r"\bottomrule\endfoot",
    ]
    for rank, sid in enumerate(order, 1):
        r = eff[sid]
        lines.append(
            f"{rank} & {sid} & {esc(ttl[sid][:64])} & {num(r['q05'])} &"
            f" {num(r['q50'])} & {num(r['q95'])} & {num(r['p_positive'], '{:.2f}')} &"
            f" {top_param(con, run['id'], sid)}\\\\")
    lines.append(r"\end{longtable}")
    (OUT / "ranking.tex").write_text("\n".join(lines) + "\n")


def write_macros(con, run):
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    n_scen = con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0]
    n_ranked = con.execute(
        "SELECT COUNT(DISTINCT scenario_id) FROM results WHERE run_id=?",
        (run["id"],)).fetchone()[0]
    att = con.execute(
        "SELECT COUNT(*), SUM(valid) FROM elicitations WHERE protocol_id=?",
        (run["protocol_id"],)).fetchone()
    eff = metric_rows(con, run["id"], "efficiency")
    order = ranked_ids(con, run["id"])
    top = order[0]
    ttl = {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}
    zero = sum(1 for s in order
               if (metric_rows(con, run["id"], "EVSI")[s]["q50"] or 0.0) < 1e-6)
    macros = {
        "voiRunId": run["id"],
        "voiSeed": run["seed"],
        "voiNDraws": f"{run['n_draws']:,}".replace(",", r"\,"),
        "voiCodeHash": esc(run["code_hash"][:12]),
        "voiProtocol": esc(prot["name"]),
        "voiKRepeats": prot["k_repeats"],
        "voiNScenarios": n_scen,
        "voiNRanked": n_ranked,
        "voiNAttempts": att[0],
        "voiValidityRate": f"{100.0 * (att[1] or 0) / att[0]:.0f}\\%" if att[0] else "--",
        "voiTopScenario": esc(ttl[top][:70]),
        "voiTopEff": num(eff[top]["q50"]),
        "voiTopPpos": num(eff[top]["p_positive"], "{:.2f}"),
        "voiZeroEvsiCount": zero,
    }
    lines = [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in macros.items()]
    (OUT / "macros.tex").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(io.DEFAULT_DB))
    ap.add_argument("--run", type=int, default=None)
    args = ap.parse_args()
    con = io.connect(args.db)
    run = (con.execute("SELECT * FROM runs WHERE id=?", (args.run,)).fetchone()
           if args.run else io.latest_run(con))
    OUT.mkdir(parents=True, exist_ok=True)
    write_catalog(con, run)
    write_ranking(con, run)
    write_macros(con, run)
    print(f"wrote catalog.tex, ranking.tex, macros.tex for run {run['id']}")


if __name__ == "__main__":
    main()
