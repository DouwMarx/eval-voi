"""LaTeX table fragments + macros (spec §8), reading only from voi.db.
Writes to report/generated/.

Usage: python -m analysis.make_tables [--run ID]   (default: latest run)
"""

from __future__ import annotations

import argparse
import json

import numpy as np
from scipy import stats

from analysis.figures import metric_rows, ranked_ids
from core.sensitivity import repeat_spread
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


PARAM_MACRO = {"p": "P", "s": "S", "t": "T", "e": "E", "B": "B", "K": "K", "C": "C"}


def noise_medians(con, protocol_id: int) -> dict[str, float | None]:
    out = {}
    sids = [r[0] for r in con.execute(
        "SELECT DISTINCT scenario_id FROM elicitations WHERE protocol_id=? AND valid=1",
        (protocol_id,))]
    for name in io.PARAM_NAMES:
        spreads = []
        for sid in sids:
            p50s = [r[0] for r in con.execute(
                "SELECT p.p50 FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
                " WHERE e.scenario_id=? AND e.protocol_id=? AND e.valid=1 AND p.name=?",
                (sid, protocol_id, name))]
            sp = repeat_spread(p50s)
            if sp is not None:
                spreads.append(sp)
        out[name] = float(np.median(spreads)) if spreads else None
    return out


def global_sensitivity(con, run_id: int) -> dict[str, float | None]:
    """Mean |rho| per parameter over the top-quartile scenarios by median
    efficiency (spec §4, global sensitivity)."""
    order = ranked_ids(con, run_id)
    top_q = order[:max(1, len(order) // 4)]
    out = {}
    for name in io.PARAM_NAMES:
        vals = [abs(r[0]) for r in con.execute(
            f"SELECT spearman FROM sensitivities WHERE run_id=? AND param=?"
            f" AND spearman IS NOT NULL AND scenario_id IN"
            f" ({','.join('?' * len(top_q))})", (run_id, name, *top_q))]
        out[name] = float(np.mean(vals)) if vals else None
    return out


def elicitation_cost(con, protocol_id: int) -> float:
    """Sum total_cost_usd over the stored CLI envelopes of a protocol."""
    total = 0.0
    for (raw,) in con.execute(
            "SELECT raw_response FROM elicitations WHERE protocol_id=?", (protocol_id,)):
        try:
            total += float(json.loads(raw).get("total_cost_usd") or 0.0)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
    return total


def rank_corr_between_runs(con, run_a: int, run_b: int) -> tuple[float, int] | None:
    med = {}
    for rid in (run_a, run_b):
        med[rid] = {r["scenario_id"]: r["q50"] for r in con.execute(
            "SELECT scenario_id, q50 FROM results WHERE run_id=? AND metric='efficiency'",
            (rid,))}
    shared = sorted(set(med[run_a]) & set(med[run_b]))
    if len(shared) < 3:
        return None
    rho = stats.spearmanr([med[run_a][s] for s in shared],
                          [med[run_b][s] for s in shared]).statistic
    return float(rho), len(shared)


def write_protocol_compare(con):
    """Pairwise Spearman rank correlation of median efficiency between the
    latest runs of every protocol that has one."""
    prots = [r for r in con.execute("SELECT * FROM protocols ORDER BY id")]
    runs = {}
    for p in prots:
        r = con.execute("SELECT id FROM runs WHERE protocol_id=? ORDER BY id DESC LIMIT 1",
                        (p["id"],)).fetchone()
        if r:
            runs[p["name"]] = r["id"]
    names = list(runs)
    if len(names) < 2:
        (OUT / "protocol_compare.tex").write_text("% fewer than 2 protocols with runs\n")
        return
    lines = [r"\begin{tabular}{@{}l" + "r" * len(names) + r"@{}}", r"\toprule",
             " & " + " & ".join(esc(n) for n in names) + r"\\", r"\midrule"]
    for a in names:
        cells = []
        for b in names:
            if a == b:
                cells.append("--")
            else:
                rc = rank_corr_between_runs(con, runs[a], runs[b])
                cells.append(f"{rc[0]:.2f}" if rc else "n/a")
        lines.append(esc(a) + " & " + " & ".join(cells) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "protocol_compare.tex").write_text("\n".join(lines) + "\n")


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
    fit_warn = con.execute(
        "SELECT COUNT(*) FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=? AND p.fit_warning=1", (run["protocol_id"],)).fetchone()[0]
    macros = {
        "voiRunId": run["id"],
        "voiSeed": run["seed"],
        "voiNDraws": f"{run['n_draws']:,}".replace(",", r"\,"),
        "voiCodeHash": esc(run["code_hash"][:12]),
        "voiProtocol": esc(prot["name"]),
        "voiKRepeats": prot["k_repeats"],
        "voiCliVersion": esc(prot["cli_version"]),
        "voiNScenarios": n_scen,
        "voiNRanked": n_ranked,
        "voiNAttempts": att[0],
        "voiValidityRate": f"{100.0 * (att[1] or 0) / att[0]:.0f}\\%" if att[0] else "--",
        "voiTopScenario": esc(ttl[top][:70]),
        "voiTopEff": num(eff[top]["q50"]),
        "voiTopPpos": num(eff[top]["p_positive"], "{:.2f}"),
        "voiZeroEvsiCount": zero,
        "voiFitWarnings": fit_warn,
        "voiElicitCost": f"{elicitation_cost(con, run['protocol_id']):.2f}",
    }
    for name, val in noise_medians(con, run["protocol_id"]).items():
        macros[f"voiNoise{PARAM_MACRO[name]}"] = num(val, "{:.2f}")
    for name, val in global_sensitivity(con, run["id"]).items():
        macros[f"voiGlobal{PARAM_MACRO[name]}"] = num(val, "{:.2f}")
    gs = global_sensitivity(con, run["id"])
    ranked_params = sorted((n for n in io.PARAM_NAMES if gs[n] is not None),
                           key=lambda n: -gs[n])
    macros["voiGlobalTopParams"] = ", ".join(f"${esc(n)}$" for n in ranked_params[:3])
    manual_run = con.execute(
        "SELECT r.id FROM runs r JOIN protocols p ON p.id=r.protocol_id"
        " WHERE p.name='p000_manual' ORDER BY r.id DESC LIMIT 1").fetchone()
    rc = (rank_corr_between_runs(con, run["id"], manual_run["id"])
          if manual_run and run["id"] != manual_run["id"] else None)
    macros["voiRhoManual"] = f"{rc[0]:.2f}" if rc else "--"
    macros["voiRhoManualN"] = rc[1] if rc else "--"
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
    write_protocol_compare(con)
    print(f"wrote catalog.tex, ranking.tex, macros.tex, protocol_compare.tex"
          f" for run {run['id']}")


if __name__ == "__main__":
    main()
