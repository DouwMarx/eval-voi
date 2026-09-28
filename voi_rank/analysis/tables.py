"""LaTeX table fragments + macros (spec §8), reading only from a study's
voi.db. Writes to <study>/report/generated/.

Usage: python -m voi_rank.analysis.tables --study studies/business [--protocol p001] [--run ID]
       [--members claude_cli:sonnet,claude_cli:opus]
(default: the latest all-member run of protocol p001; --members selects the
latest run that pooled exactly that subset; --run overrides. The catalog's
pooled medians, the member table, the attempt, validity, cost and noise
macros describe the run's members; \voiRunMembers names them.)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy import stats

from voi_rank import db
from voi_rank.analysis.figures import (
    MATH_LABEL,
    add_run_args,
    c_quantiles,
    evsi_metric,
    metric_rows,
    primary_metric,
    ranked_ids,
    run_kind,
    run_sensitivity_names,
    select_run,
)
from voi_rank.study import Study, add_study_arg

LATEX_SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
                  "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
                  "^": r"\textasciicircum{}"}
# macro name suffix per stored parameter (binary and Gaussian names)
PARAM_MACRO = {"p": "P", "s": "S", "t": "T", "B": "B", "K": "K", "C": "C",
               "g_mu0": "GMuZero", "g_sigma0": "GSigmaZero", "g_d": "GD", "g_x": "GX",
               "g_k": "GKexp", "g_L": "GL", "g_kappa_sigma0": "GKappa", "g_B": "GB", "g_K": "GK",
               "g_sigma_b_rel": "GSigmaB"}
LEGACY_PARAM = "e"   # v1 parameter, retired in v2; still present in old DB rows
MEMBER_LETTERS = "ABCDEFGHIJ"


def esc(text: str) -> str:
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in str(text))


def tex_param(name: str) -> str:
    """LaTeX math label of a stored parameter name."""
    return f"${MATH_LABEL.get(name, esc(name))}$"


def protocol_param_names(con, protocol_id: int) -> list[str]:
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()
    return db.param_names(db.protocol_model_kind(prot))


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


def pooled_p50(con, protocol_id: int, sid: int, name: str,
               members: list[str] | None = None) -> float | None:
    """Median of the p50 over the valid elicitations of one scenario (every
    member, or the `members` subset)."""
    p50s = db.elicited_p50s(con, protocol_id, sid, name, members=members)
    return float(np.median(p50s)) if p50s else None


def write_gauss_catalog(con, run, out: Path):
    """Gaussian run: pooled medians of the derived quantities d, x, k, L,
    kappa sigma0, B, K (median of the repeat values) and the run's mixture
    median for C."""
    order = ranked_ids(con, run["id"])
    cols = ["g_d", "g_x", "g_k", "g_L", "g_kappa_sigma0", "g_B", "g_K"]
    head = " & ".join(tex_param(n) for n in cols)
    lines = [
        r"\begin{longtable}{@{}rp{4.6cm}rrrrrrrr@{}}",
        r"\caption{Scenario catalog (Gaussian-state protocol). $d$, $x$, $k$, $L$,"
        r" $\kappa\sigma_0$, $B$, $K$: pooled medians of the derived quantities across valid"
        r" elicitations; $C$: the run's mixture median. $L$, $\kappa\sigma_0$, $B$, $K$, $C$"
        r" in USD.}\label{tab:catalog}\\",
        r"\toprule",
        f"id & scenario & {head} & $C$\\\\",
        r"\midrule\endfirsthead",
        f"\\toprule id & scenario & {head} & $C$\\\\" r"\midrule\endhead",
        r"\bottomrule\endfoot",
    ]
    ttl = {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}
    labels = db.run_member_labels(run)
    for sid in order:
        vals = {n: pooled_p50(con, run["protocol_id"], sid, n, labels) for n in cols}
        cells = [num(vals["g_d"], "{:.2f}"), num(vals["g_x"], "{:.2f}"), num(vals["g_k"], "{:.1f}"),
                 money(vals["g_L"]), money(vals["g_kappa_sigma0"]), money(vals["g_B"]),
                 money(vals["g_K"]), money(c_quantiles(con, run, sid)[1])]
        lines.append(f"{sid} & {esc(ttl[sid][:60])} & " + " & ".join(cells) + r"\\")
    lines.append(r"\end{longtable}")
    (out / "catalog.tex").write_text("\n".join(lines) + "\n")


def write_catalog(con, run, out: Path):
    """Scenario catalog: pooled elicited medians for p, s, t, B, K under the
    run's protocol, and the run's mixture median for C (the quantity the
    efficiency column divides by; for a pre-v2 run without a stored C row
    c_quantiles falls back to the pooled elicited median). A Gaussian run
    gets the derived-quantity catalog instead."""
    if run_kind(con, run["id"]) == db.GAUSSIAN_KIND:
        return write_gauss_catalog(con, run, out)
    order = ranked_ids(con, run["id"])
    lines = [
        r"\begin{longtable}{@{}rp{6.2cm}rrrrrr@{}}",
        r"\caption{Scenario catalog. $p$, $s$, $t$, $B$, $K$: pooled elicited medians"
        r" (median of the p50 across valid elicitations); $C$: the run's mixture median"
        r" (q50 of the pooled cost draws), the same $C$ the efficiency column divides by."
        r" $B$, $K$, $C$ in USD.}\label{tab:catalog}\\",
        r"\toprule",
        r"id & scenario & $p$ & $s$ & $t$ & $B$ & $K$ & $C$\\",
        r"\midrule\endfirsthead",
        r"\toprule id & scenario & $p$ & $s$ & $t$ & $B$ & $K$ & $C$\\"
        r"\midrule\endhead",
        r"\bottomrule\endfoot",
    ]
    ttl = {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}
    labels = db.run_member_labels(run)
    for sid in order:
        vals = {n: pooled_p50(con, run["protocol_id"], sid, n, labels) for n in db.PARAM_NAMES}
        vals["C"] = c_quantiles(con, run, sid)[1]
        lines.append(
            f"{sid} & {esc(ttl[sid][:70])} & {num(vals['p'], '{:.2f}')} &"
            f" {num(vals['s'], '{:.2f}')} & {num(vals['t'], '{:.2f}')} &"
            f" {money(vals['B'])} & {money(vals['K'])} & {money(vals['C'])}\\\\")
    lines.append(r"\end{longtable}")
    (out / "catalog.tex").write_text("\n".join(lines) + "\n")


def top_param(con, run_id: int, sid: int) -> str:
    names = run_sensitivity_names(con, run_id)
    rows = [r for r in con.execute(
        "SELECT param, spearman FROM sensitivities WHERE run_id=? AND scenario_id=?"
        " AND spearman IS NOT NULL", (run_id, sid)) if r["param"] in names]
    if not rows:
        return "--"
    best = max(rows, key=lambda r: abs(r["spearman"]))
    return tex_param(best["param"])


def write_ranking(con, run, out: Path, top_n: int = 25):
    metric, evsi_name = primary_metric(con, run["id"]), evsi_metric(con, run["id"])
    eff = metric_rows(con, run["id"], metric)
    order = ranked_ids(con, run["id"])[:top_n]
    ttl = {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}
    lines = [
        r"\begin{longtable}{@{}rrp{6.0cm}rrrrl@{}}",
        f"\\caption{{Final ranking by median {esc(metric)} ({esc(evsi_name)}/C). $P_+$ ="
        f" P({esc(evsi_name)} $>$ C)"
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
    (out / "ranking.tex").write_text("\n".join(lines) + "\n")


# --- statistics behind macros ----------------------------------------------

def noise_median(con, protocol_id: int, name: str, first: int | None = None,
                 member: dict | None = None, members: list[str] | None = None) -> float | None:
    """Median over scenarios of the cross-elicitation p50 spread of one
    parameter (db.elicited_spread: relative, or max - min in sd units for the
    signed Gaussian quantities). first truncates to the first `first` valid repeats of each
    member (a count in repeat_ix order, so an invalid middle repeat does not
    shrink the pool; range statistics grow with the count, so cross-protocol
    comparisons need matched k); member restricts to one (provider, model),
    members to a subset (labels)."""
    clause, margs = db.member_filter(members)
    sids = [r[0] for r in con.execute(
        f"SELECT DISTINCT scenario_id FROM elicitations e WHERE protocol_id=? AND valid=1{clause}",
        (protocol_id, *margs))]
    spreads = []
    for sid in sids:
        sp = db.elicited_spread(con, protocol_id, sid, name,
                                provider=member["provider"] if member else None,
                                model=member["model"] if member else None, first=first,
                                members=members)
        if sp is not None:
            spreads.append(sp)
    return float(np.median(spreads)) if spreads else None


def noise_medians(con, protocol_id: int, first: int | None = None,
                  member: dict | None = None, members: list[str] | None = None) -> dict:
    return {n: noise_median(con, protocol_id, n, first, member, members)
            for n in protocol_param_names(con, protocol_id)}


def global_sensitivity_param(con, run_id: int, name: str) -> float | None:
    """Mean |rho| of one parameter over the top-quartile scenarios by median
    efficiency (spec §4, global sensitivity)."""
    order = ranked_ids(con, run_id)
    top_q = order[:max(1, len(order) // 4)]
    vals = [abs(r[0]) for r in con.execute(
        f"SELECT spearman FROM sensitivities WHERE run_id=? AND param=?"
        f" AND spearman IS NOT NULL AND scenario_id IN"
        f" ({','.join('?' * len(top_q))})", (run_id, name, *top_q))]
    return float(np.mean(vals)) if vals else None


def global_sensitivity(con, run_id: int) -> dict[str, float | None]:
    """Over the parameters the run stores sensitivities for (a Gaussian run
    emits no voiGlobalGMuZero / voiGlobalGSigmaZero macro: those enter no metric)."""
    return {n: global_sensitivity_param(con, run_id, n) for n in run_sensitivity_names(con, run_id)}


def member_stats(con, protocol_id: int, member: dict) -> dict:
    """Attempts, valid attempts and summed cost of one member's elicitations."""
    rows = con.execute(
        "SELECT valid, raw_response FROM elicitations WHERE protocol_id=? AND provider=?"
        " AND model=?", (protocol_id, member["provider"], member["model"])).fetchall()
    return {
        "attempts": len(rows),
        "valid": sum(int(r["valid"] or 0) for r in rows),
        "cost": sum(db.envelope_cost(r["raw_response"]) for r in rows),
    }


def elicitation_cost(con, protocol_id: int, members: list[str] | None = None) -> float:
    """Sum of the recorded per-call cost over every stored response of a
    protocol (every member, or the subset)."""
    clause, margs = db.member_filter(members)
    return sum(db.envelope_cost(r[0]) for r in con.execute(
        f"SELECT raw_response FROM elicitations e WHERE protocol_id=?{clause}", (protocol_id, *margs)))


def rank_corr_between_runs(con, run_a: int, run_b: int) -> tuple[float, int] | None:
    """Spearman of median efficiency over shared scenarios, each run on its
    own primary metric ('efficiency' or 'eff_step'), so a binary and a
    Gaussian run compare on their own rankings."""
    med = {}
    for rid in (run_a, run_b):
        med[rid] = {r["scenario_id"]: r["q50"] for r in con.execute(
            "SELECT scenario_id, q50 FROM results WHERE run_id=? AND metric=?",
            (rid, primary_metric(con, rid)))}
    shared = sorted(set(med[run_a]) & set(med[run_b]))
    if len(shared) < 3:
        return None
    rho = stats.spearmanr([med[run_a][s] for s in shared],
                          [med[run_b][s] for s in shared]).statistic
    if np.isnan(rho):   # a constant ranking (every median EVSI zero): undefined, printed as n/a
        return None
    return float(rho), len(shared)


def latest_run_per_protocol(con, subsets: bool = True) -> dict[str, int]:
    """{label: run id}: the latest all-member run of every protocol that has
    one (label = the protocol name) and, with subsets, the latest run of
    every member subset scored under it (label 'p003[opus+sonnet]')."""
    out = {}
    for label, run in db.latest_runs_by_subset(con):
        if subsets or db.run_member_labels(run) is None:
            out[label] = run["id"]
    return out


def write_protocol_compare(con, out: Path):
    """Pairwise Spearman rank correlation of median efficiency between the
    latest runs of every protocol that has one, subset runs as their own
    columns."""
    runs = latest_run_per_protocol(con)
    names = list(runs)
    if len(names) < 2:
        (out / "protocol_compare.tex").write_text("% fewer than 2 protocols with runs\n")
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
    (out / "protocol_compare.tex").write_text("\n".join(lines) + "\n")


def full_sweep_runs(con, min_scenarios: int = 60) -> dict[str, int]:
    """Latest run id per protocol, restricted to full-sweep protocols (>=
    min_scenarios ranked scenarios; excludes the manual baseline and focused
    subset protocols)."""
    out = {}
    for name, rid in latest_run_per_protocol(con, subsets=False).items():
        n = con.execute("SELECT COUNT(DISTINCT scenario_id) FROM results WHERE run_id=?",
                        (rid,)).fetchone()[0]
        if n >= min_scenarios:
            out[name] = rid
    return out


MATCHED_K = 3   # repeats per member the cross-protocol noise table is truncated to


def repeated_members(con, kind: str = db.BINARY_KIND) -> list[tuple[str, dict]]:
    """(protocol name, member) for every member with at least two valid
    repeats of some scenario, in protocol then member order, over the
    protocols of one model kind (their parameter rows are the table's rows):
    the columns of the protocol noise table."""
    out = []
    for p in con.execute("SELECT * FROM protocols ORDER BY id"):
        if db.protocol_model_kind(p) != kind:
            continue
        repeated = {(r[0], r[1]) for r in con.execute(
            "SELECT provider, model, COUNT(DISTINCT repeat_ix) AS k FROM elicitations"
            " WHERE protocol_id=? AND valid=1 GROUP BY provider, model HAVING k > 1", (p["id"],))}
        out += [(p["name"], m) for m in db.protocol_members(p)
                if (m["provider"], m["model"]) in repeated]
    return out


def write_protocol_noise(con, out: Path, kind: str = db.BINARY_KIND):
    """Median cross-repeat p50 spread per parameter, one column per (protocol,
    member) with repeats among the protocols of the run's model kind, each
    truncated to its first MATCHED_K valid repeats so every column pools the
    same count (range statistics grow with it)."""
    cols = repeated_members(con, kind)
    if not cols:
        (out / "protocol_noise.tex").write_text("% no multi-repeat protocols yet\n")
        return
    prots = {name: con.execute("SELECT id FROM protocols WHERE name=?", (name,)).fetchone()[0]
             for name, _ in cols}
    lines = [r"\begin{tabular}{@{}l" + "r" * len(cols) + r"@{}}", r"\toprule",
             "protocol & " + " & ".join(esc(name) for name, _ in cols) + r"\\",
             "member & " + " & ".join(esc(db.member_label(m)) for _, m in cols) + r"\\",
             r"\midrule"]
    per_col = [noise_medians(con, prots[name], first=MATCHED_K, member=m) for name, m in cols]
    for name in db.param_names(kind):
        cells = [num(col[name], "{:.2f}") for col in per_col]
        label = tex_param(name) + esc(db.spread_label(name)).replace(" - ", " $-$ ")
        lines.append(f"{label} & " + " & ".join(cells) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "protocol_noise.tex").write_text("\n".join(lines) + "\n")


def write_members(con, run, out: Path, members: list[dict]):
    """Per-member table: provider, model, nominal k, attempts, validity, cost."""
    lines = [r"\begin{tabular}{@{}llrrrr@{}}", r"\toprule",
             r"provider & model & $k$ & attempts & valid & cost (USD)\\", r"\midrule"]
    for m in members:
        st = member_stats(con, run["protocol_id"], m)
        rate = f"{100.0 * st['valid'] / st['attempts']:.1f}\\%" if st["attempts"] else "--"
        lines.append(f"{esc(m['provider'])} & {esc(m['model'])} & {m['k_repeats']} &"
                     f" {st['attempts']} & {rate} & {st['cost']:.2f}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "members.tex").write_text("\n".join(lines) + "\n")


def _k_used(con, protocol_id: int, members: list[str] | None = None):
    """Median number of valid elicitations pooled per scenario (the run's
    members and all repeats; can exceed the nominal k when elicitation ran
    with --k)."""
    clause, margs = db.member_filter(members)
    counts = [r[0] for r in con.execute(
        f"SELECT COUNT(*) FROM elicitations e WHERE protocol_id=? AND valid=1{clause}"
        " GROUP BY scenario_id", (protocol_id, *margs))]
    return int(np.median(counts)) if counts else "--"


def legacy_e_macros(con, run) -> dict:
    """Numbers about the retired v1 parameter e, from the last run of the same
    protocol that still carried it (used by the business report to justify
    dropping e). All '--' when the DB never had e."""
    old = con.execute(
        "SELECT r.id FROM runs r WHERE r.protocol_id=? AND r.id<>? AND EXISTS"
        " (SELECT 1 FROM sensitivities s WHERE s.run_id=r.id AND s.param=?)"
        " ORDER BY r.id DESC LIMIT 1", (run["protocol_id"], run["id"], LEGACY_PARAM)).fetchone()
    keys = ("voiLegacyRunId", "voiLegacyGlobalE", "voiLegacyNoiseE", "voiLegacyGlobalMax",
            "voiLegacyGlobalMaxParam", "voiLegacyRho", "voiLegacyRhoN", "voiLegacyTopTenShared")
    if old is None:
        return dict.fromkeys(keys, "--")
    gs = {n: global_sensitivity_param(con, old["id"], n) for n in db.PARAM_NAMES + [LEGACY_PARAM]}
    best = max((n for n in gs if gs[n] is not None), key=lambda n: gs[n])
    rc = rank_corr_between_runs(con, run["id"], old["id"])
    shared_top = len(set(ranked_ids(con, run["id"])[:10]) & set(ranked_ids(con, old["id"])[:10]))
    return {
        "voiLegacyRunId": old["id"],
        "voiLegacyGlobalE": num(gs[LEGACY_PARAM], "{:.2f}"),
        "voiLegacyNoiseE": num(noise_median(con, run["protocol_id"], LEGACY_PARAM), "{:.2f}"),
        "voiLegacyGlobalMax": num(gs[best], "{:.2f}"),
        "voiLegacyGlobalMaxParam": f"${esc(best)}$",
        "voiLegacyRho": f"{rc[0]:.3f}" if rc else "--",
        "voiLegacyRhoN": rc[1] if rc else "--",
        "voiLegacyTopTenShared": shared_top,
    }


def short_code_hash(code_hash: str) -> str:
    """First 12 hex digits, keeping the '-dirty' suffix of a run made from
    uncommitted code so the report never presents it as a clean revision."""
    return code_hash.removesuffix("-dirty")[:12] + ("-dirty" if db.is_dirty_hash(code_hash) else "")


def write_macros(con, run, out: Path):
    """The run's macros. Members, attempts, validity, cost, k used, fit
    warnings and noise describe the members the run pooled (every member of
    the protocol, or its stored subset; \voiRunMembers says which)."""
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    labels = db.run_member_labels(run)
    members = db.run_members(con, run)
    clause, margs = db.member_filter(labels)
    n_scen = con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0]
    n_ranked = con.execute(
        "SELECT COUNT(DISTINCT scenario_id) FROM results WHERE run_id=?",
        (run["id"],)).fetchone()[0]
    att = con.execute(
        f"SELECT COUNT(*), SUM(valid) FROM elicitations e WHERE protocol_id=?{clause}",
        (run["protocol_id"], *margs)).fetchone()
    kind = run_kind(con, run["id"])
    names = db.param_names(kind)
    eff = metric_rows(con, run["id"], db.primary_metric(kind))
    evsi = metric_rows(con, run["id"], db.evsi_metric(kind))
    order = ranked_ids(con, run["id"])
    top = order[0]
    ttl = {r["id"]: r["title"] for r in con.execute("SELECT id, title FROM scenarios")}
    zero = sum(1 for s in order if (evsi[s]["q50"] or 0.0) < 1e-6)
    above_one_q05 = sum(1 for s in order if (eff[s]["q05"] or 0.0) > 1.0)
    fit_warn = con.execute(
        "SELECT COUNT(*) FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=? AND p.fit_warning=1 AND p.name IN"
        f" ({','.join('?' * len(names))}){clause}",
        (run["protocol_id"], *names, *margs)).fetchone()[0]
    macros = {
        "voiRunId": run["id"],
        "voiRunMembers": esc(db.members_label(labels)),
        "voiModelKind": esc(kind),
        "voiSeed": run["seed"],
        "voiNDraws": f"{run['n_draws']:,}".replace(",", r"\,"),
        "voiCodeHash": esc(short_code_hash(run["code_hash"])),
        "voiDataHash": esc(run["data_hash"][:12]) if run["data_hash"] else "--",
        "voiProtocol": esc(prot["name"]),
        "voiKRepeats": prot["k_repeats"],
        "voiKUsed": _k_used(con, run["protocol_id"], labels),
        "voiNMembers": len(members),
        "voiMembers": ", ".join(esc(db.member_label(m)) for m in members),
        "voiCliVersion": esc(prot["cli_version"]),
        "voiNScenarios": n_scen,
        "voiNRanked": n_ranked,
        "voiNAttempts": att[0],
        "voiValidityRate": f"{100.0 * (att[1] or 0) / att[0]:.1f}\\%" if att[0] else "--",
        "voiTopScenario": esc(ttl[top][:70]),
        "voiTopId": top,
        "voiTopEff": num(eff[top]["q50"]),
        "voiTopEffQlo": num(eff[top]["q05"]),
        "voiTopPpos": num(eff[top]["p_positive"], "{:.2f}"),
        "voiZeroEvsiCount": zero,
        "voiAboveOneQloCount": above_one_q05,
        "voiFitWarnings": fit_warn,
        "voiElicitCost": f"{elicitation_cost(con, run['protocol_id'], labels):.2f}",
    }
    for i, m in enumerate(members[:len(MEMBER_LETTERS)]):
        st = member_stats(con, run["protocol_id"], m)
        L = MEMBER_LETTERS[i]
        macros[f"voiMemberName{L}"] = esc(db.member_label(m))
        macros[f"voiMemberK{L}"] = m["k_repeats"]
        macros[f"voiMemberAttempts{L}"] = st["attempts"]
        macros[f"voiMemberValidity{L}"] = (f"{100.0 * st['valid'] / st['attempts']:.1f}\\%"
                                           if st["attempts"] else "--")
        macros[f"voiMemberCost{L}"] = f"{st['cost']:.2f}"
    for name, val in noise_medians(con, run["protocol_id"], members=labels).items():
        macros[f"voiNoise{PARAM_MACRO[name]}"] = num(val, "{:.2f}")
    gs = global_sensitivity(con, run["id"])
    for name, val in gs.items():
        macros[f"voiGlobal{PARAM_MACRO[name]}"] = num(val, "{:.2f}")
    ranked_params = sorted((n for n in gs if gs[n] is not None), key=lambda n: -gs[n])
    macros["voiGlobalTopParams"] = ", ".join(tex_param(n) for n in ranked_params[:3])
    macros.update(legacy_e_macros(con, run))
    manual_run = con.execute(
        "SELECT r.id FROM runs r JOIN protocols p ON p.id=r.protocol_id"
        " WHERE p.name='p000_manual' ORDER BY r.id DESC LIMIT 1").fetchone()
    rc = (rank_corr_between_runs(con, run["id"], manual_run["id"])
          if manual_run and run["id"] != manual_run["id"] else None)
    macros["voiRhoManual"] = f"{rc[0]:.2f}" if rc else "--"
    macros["voiRhoManualN"] = rc[1] if rc else "--"
    sweeps = full_sweep_runs(con)
    rhos = []
    names = list(sweeps)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pc = rank_corr_between_runs(con, sweeps[a], sweeps[b])
            if pc:
                rhos.append(pc[0])
    macros["voiRhoProtoMin"] = f"{min(rhos):.2f}" if rhos else "--"
    macros["voiRhoProtoMax"] = f"{max(rhos):.2f}" if rhos else "--"
    macros["voiNProtocols"] = len(names)
    lines = [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in macros.items()]
    (out / "macros.tex").write_text("\n".join(lines) + "\n")
    write_members(con, run, out, members)
    return macros


def make_all(con, run, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    write_catalog(con, run, out)
    write_ranking(con, run, out)
    write_macros(con, run, out)
    write_protocol_compare(con, out)
    write_protocol_noise(con, out, run_kind(con, run["id"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    add_study_arg(ap)
    add_run_args(ap)
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    run = select_run(con, args.run, args.protocol, db.parse_member_labels(args.members))
    make_all(con, run, study.generated_dir)
    print(f"wrote catalog.tex, ranking.tex, macros.tex, members.tex, protocol_compare.tex,"
          f" protocol_noise.tex for run {run['id']} in {study.generated_dir}")


if __name__ == "__main__":
    main()
