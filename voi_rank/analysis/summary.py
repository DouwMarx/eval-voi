"""Every number of the analysis, from a study DB alone (DESIGN section 6).

Input: the latest stored run of a protocol (mc.run_mc), optionally of a
member subset, over the active scenarios only (mc.complete_fits: a retired
scenario, one no longer in scenarios.json, is left out; a run that still
holds one is refused, so the analysis never mixes in a cut scenario).
Per-draw arrays are not stored, so the run's draws are re-drawn with
mc.iter_scenario_draws (same fits, seed and n_draws) and every scenario's
stored eta quantiles and P(EVSI > C) are verified against them, as
mc.replay_efficiency does. --draws N then keeps the first N of the run's
draws (a deterministic subsample, for speed); the verification always runs
on the full set.

decision_from: the decision-level parameters p, B, K come from the valid
decision-stage elicitations of another protocol, the instrument-level ones
(s, t, C_build, C_run) from the analysed run's protocol. No run stores this
combination, so its draws use the run's seed and n_draws and are not
verified, and the eta sensitivities are computed from the draws (as mc
does) instead of read. Unused by the current documents; kept for ablations.

Rankings: for eta and for eta* (eta_ind, EVSI*/C) alike, rank 1 = the
highest value, ties averaged, on every draw and at the central estimate.
The Spearman sensitivities against eta are the run's stored ones; those
against eta* are computed from the re-drawn draws.

Groups: scenarios.grp, "physical AI" or "LLM" (DESIGN section 2); the
drafts' older label "frontier model" reads as "LLM". Every pairwise share
counts ties as one half.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from voi_rank import db, mc, model
from voi_rank.fit import DECISION_PARAMS, FAMILY_BY_PARAM, PARAM_NAMES
from voi_rank.sensitivity import spearman

PHYS, LLM = "physical AI", "LLM"
# display names of the final ensemble's model ids; an id not listed prints as itself without the
# provider prefix (member_name)
MEMBER_NAMES = {"deepseek/deepseek-v4.1-flash": "DeepSeek V4.1 Flash", "z-ai/glm-5.3": "GLM 5.3",
                "xiaomi/mimo-v2.6-flash": "MiMo v2.6 Flash", "openai/gpt-6-luna": "GPT-6 Luna",
                "google/gemini-3.8-flash": "Gemini 3.8 Flash", "x-ai/grok-4.7": "Grok 4.7"}
GROUPS = (PHYS, LLM)
GROUP_ALIASES = {"frontier model": LLM}
ERROR_CLASSES = ("json", "schema", "constraint", "fit", "refusal", "truncated", "cli", "http", "api",
                 "provider", "other")
CURVE_QS = np.arange(101)
QS = (0.05, 0.50, 0.95)
TOP_K = (3, 5)
IQR_QS = (0.25, 0.75)
BEST_TOP = (1, 3, 5, 10)                 # N of the reported P(best physical-AI rank <= N)
ROC_FPR = np.linspace(0.0, 1.0, 101)     # the false-positive grid of the ROC band
ROC_METRICS = ("eta", "eta_ind")
DRAWN = ("EVSI", "EVSI_ind", "C", "eta", "eta_ind", "eta_run", "n_star")
COMPARED = ("eta", "eta_ind", "eta_run")
RANKED = ("eta", "eta_ind")              # per-draw rankings are kept for these
PRIMARY = "eta_ind"                      # the ranking the documents lead with (eta*, EVSI*/C)
LEVEL_METRICS = ("eta", "eta_ind")       # fidelity level against these (central estimates)
# risk domains (scenarios.json attributes.risk_domain) in display order; the physical-AI
# evaluations all carry physical_harm, so the domain doubles as the group there
DOMAINS = ("cyber", "cbrn", "loss_of_control", "harmful_manipulation", "societal_harm", "physical_harm")
DOMAIN_LABEL = {"cyber": "cyber", "cbrn": "CBRN", "loss_of_control": "loss of control",
                "harmful_manipulation": "harmful manipulation", "societal_harm": "societal harm",
                "physical_harm": "physical AI"}
CHUNK = 20_000   # draws per block in the broadcasting comparisons (memory bound)


@dataclass
class Scenario:
    id: int
    title: str
    short: str
    group: str | None
    level: float | None
    domain: str | None
    sources: list[dict] = field(default_factory=list)   # scenarios.json 'sources' (key, kind, role, title)


def scenario_info(row) -> Scenario:
    """Short name: the scenarios.json entry's 'key' (the drafts' slug), else
    attributes.eval_family up to its first ' (', else the title."""
    attrs = db.scenario_attributes(row)
    try:
        raw = json.loads(row["raw_json"] or "{}")
    except ValueError:
        raw = {}
    short = raw.get("key") or (attrs.get("eval_family") or "").split(" (")[0] or row["title"]
    level = attrs.get("level")
    sources = raw.get("sources") if isinstance(raw.get("sources"), list) else []
    return Scenario(id=row["id"], title=row["title"], short=str(short),
                    group=GROUP_ALIASES.get(row["grp"], row["grp"]),
                    level=None if level is None else float(level), domain=attrs.get("risk_domain"),
                    sources=sources)


# --- statistics on arrays (scenarios on axis 0, draws on axis 1) ------------

def pairwise_share(a, b):
    """P(a_i > b_j) over every pair (ties count half): the Mann-Whitney U over
    n_a n_b. 1-D inputs give a float; (n, D) inputs give one value per draw."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    one = a.ndim == 1
    if one:
        a, b = a[:, None], b[:, None]
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return None if one else np.full(a.shape[1], np.nan)
    ranks = stats.rankdata(np.vstack([a, b]), method="average", axis=0)
    u = ranks[:na].sum(axis=0) - na * (na + 1) / 2.0
    out = u / (na * nb)
    return float(out[0]) if one else out


def _above(x, t):
    """1[x > t] + 0.5 1[x == t], broadcast."""
    return (x > t) + 0.5 * (x == t)


def percentile_curve(a, b, qs=CURVE_QS):
    """P(a random member of a exceeds the q-th percentile of b), ties half,
    for each q. 1-D inputs give (Q,); (n, D) inputs give (Q, D)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.ndim == 1:
        return _above(a[None, :], np.percentile(b, qs)[:, None]).mean(axis=1)
    out = np.empty((len(qs), a.shape[1]))
    for lo in range(0, a.shape[1], CHUNK):
        sl = slice(lo, lo + CHUNK)
        thr = np.percentile(b[:, sl], qs, axis=0)                 # (Q, d)
        out[:, sl] = _above(a[None, :, sl], thr[:, None, :]).mean(axis=1)
    return out


def percentile_among(a, b):
    """The percentile (0-100) of each member of a among the members of b,
    ties half. 1-D inputs give (n_a,); (n, D) inputs give (n_a, D)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.ndim == 1:
        return 100.0 * _above(a[:, None], b[None, :]).mean(axis=1)
    out = np.empty(a.shape)
    for lo in range(0, a.shape[1], CHUNK):
        sl = slice(lo, lo + CHUNK)
        out[:, sl] = 100.0 * _above(a[:, None, sl], b[None, :, sl]).mean(axis=1)
    return out


def ranks_desc(x, axis=0):
    """Rank 1 = the largest value, ties averaged."""
    return stats.rankdata(-np.asarray(x, dtype=float), method="average", axis=axis)


def best_rank_curve(ranks, ns):
    """P(min over rows of rank <= N) for each N, over the columns (draws):
    ranks is (n_group, D), the group's ranks among every evaluation."""
    best = np.asarray(ranks, dtype=float).min(axis=0)
    return np.array([(best <= n).mean() for n in ns])


def roc_curve(pos, neg) -> tuple[np.ndarray, np.ndarray]:
    """ROC of 'positive class' given the score, sweeping a threshold from the
    highest value down: (FPR, TPR) vertices from (0, 0) to (1, 1). Values tied
    across the classes enter at one threshold, so the curve runs diagonally
    there and its trapezoid area is pairwise_share(pos, neg) (ties half)."""
    pos, neg = np.asarray(pos, dtype=float), np.asarray(neg, dtype=float)
    lab = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
    _, inv = np.unique(-np.concatenate([pos, neg]), return_inverse=True)   # descending thresholds
    tp = np.bincount(inv, weights=lab)
    fp = np.bincount(inv, weights=1.0 - lab)
    return (np.concatenate([[0.0], np.cumsum(fp) / len(neg)]),
            np.concatenate([[0.0], np.cumsum(tp) / len(pos)]))


def roc_area(fpr, tpr) -> float:
    return float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2.0))


def roc_band(pos, neg, grid=ROC_FPR, qs=QS) -> np.ndarray:
    """Per draw (column), the ROC's TPR linearly interpolated at the FPR grid;
    returns the quantiles over draws, (len(grid), len(qs)). At a vertical
    step the interpolation takes numpy's choice of end; the grid rarely hits
    one exactly."""
    pos, neg = np.asarray(pos, dtype=float), np.asarray(neg, dtype=float)
    tprs = np.empty((pos.shape[1], len(grid)))
    for d in range(pos.shape[1]):
        f, t = roc_curve(pos[:, d], neg[:, d])
        tprs[d] = np.interp(grid, f, t)
    return np.quantile(tprs, qs, axis=0).T


def quantiles(vec, qs=QS) -> list[float | None]:
    """Quantiles over the finite values; None when there is none."""
    v = np.asarray(vec, dtype=float)
    v = v[np.isfinite(v)]
    return [None] * len(qs) if v.size == 0 else [float(x) for x in np.quantile(v, qs)]


def mann_whitney_p(a, b) -> float | None:
    """Exact two-sided Mann-Whitney p-value that holds under ties (many
    central etas are exactly 0; scipy's method='exact' assumes no ties):
    the permutation distribution of a's rank sum under midranks, counted
    exactly (doubled midranks are integers, so a subset-sum count over them
    enumerates every split), two-sided as scipy does (twice the smaller
    tail, capped at 1)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, n = len(a), len(a) + len(b)
    if na == 0 or len(b) == 0:
        return None
    r2 = np.rint(2 * stats.rankdata(np.concatenate([a, b]))).astype(int)
    tot = int(r2.sum())
    f = np.zeros((na + 1, tot + 1), dtype=object)   # f[k, s]: subsets of size k with doubled sum s
    f[0, 0] = 1
    for r in r2:
        f[1:, r:] = f[1:, r:] + f[:-1, :tot + 1 - r]
    d, obs = f[na], int(r2[:na].sum())
    tail = min(sum(d[:obs + 1]), sum(d[obs:]))
    return float(min(1.0, 2 * tail / math.comb(n, na)))


def spearman_or_none(x, y) -> float | None:
    return spearman_test(x, y)[0]


def spearman_test(x, y) -> tuple[float | None, float | None]:
    """Spearman's rho and its two-sided p-value (scipy's t approximation,
    which handles ties); (None, None) below 3 points or on a constant input."""
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None, None
    r = stats.spearmanr(x, y)
    return float(r.statistic), float(r.pvalue)


def member_display(label: str) -> str:
    """A member label for figures and tables: the model id without the
    provider prefix ('claude_cli:haiku' -> 'haiku'). summary.json keeps the
    full label."""
    return label.split(":", 1)[-1]


def member_name(label: str) -> str:
    """'openrouter:openai/gpt-6-luna' -> 'GPT-6 Luna'; unknown ids print as member_display does."""
    model = member_display(label)
    return MEMBER_NAMES.get(model, model)


def error_class(error: str | None, raw: str | None = None) -> str:
    """The class of an invalid attempt: the error's prefix, except that an
    API refusal stored before the provider classified it ('cli: exit 1'
    with stop_reason 'refusal' in the envelope) counts as a refusal."""
    from voi_rank.providers.claude_cli import refusal_envelope
    if refusal_envelope(raw) is not None:
        return "refusal"
    head = (error or "").split(":", 1)[0].strip()
    return head if head in ERROR_CLASSES else "other"


# --- the summary --------------------------------------------------------------

@dataclass
class Summary:
    run: dict
    scenarios: list[Scenario]                # row order of every per-scenario array
    pooled: dict[str, np.ndarray]            # pooled median per parameter
    elicited: dict[str, list[dict[str, list[float]]]]   # param -> per scenario {member: p50s}
    member_labels: list[str]
    central: dict[str, np.ndarray]           # model.metrics at the pooled medians
    draws: dict[str, np.ndarray]             # DRAWN metrics, (S, D)
    sensitivity: np.ndarray                  # (S, len(PARAM_NAMES)) against eta, NaN = undefined
    health: list[dict]
    sensitivity_ind: np.ndarray | None = None   # the same against eta* (from the draws)
    out: dict = field(default_factory=dict)  # every derived number (compute())

    def ids_in(self, group: str) -> np.ndarray:
        return np.array([i for i, s in enumerate(self.scenarios) if s.group == group], dtype=int)


def _protocol_members(con, prot, labels: list[str] | None) -> list[dict]:
    members = db.protocol_members(prot)
    return members if labels is None else [m for m in members if db.member_label(m) in labels]


def _verify(con, run_id: int, sid: int, metrics: dict) -> None:
    """Stored eta quantiles and P(EVSI > C) of one scenario against the re-drawn metrics."""
    got = mc.summarize(metrics[mc.PRIMARY_METRIC])
    row = con.execute("SELECT * FROM results WHERE run_id=? AND scenario_id=? AND metric=?",
                      (run_id, sid, mc.PRIMARY_METRIC)).fetchone()
    if row is None:
        raise RuntimeError(f"run {run_id} replay mismatch: scenario {sid} has no stored eta")
    checks = [(col, got[q], row[col]) for q, col in zip(mc.SUMMARY_QS, mc.RESULT_COLUMNS, strict=True)]
    checks.append(("p_positive", mc.probabilities(metrics)["p_positive"],
                   mc.stored_probability(con, run_id, sid, "p_positive")))
    for label, value, want in checks:
        if want is None or value is None or abs(value - want) > mc.REPLAY_RTOL * max(1.0, abs(want)):
            raise RuntimeError(f"run {run_id} replay mismatch on scenario {sid}: eta {label} {value}"
                               f" vs stored {want}: the valid elicitations changed since the run")


def health_rows(con, sources: list[tuple[int, str | None]], members: list[dict],
                labels: list[str] | None, scenario_ids=None) -> list[dict]:
    """Per member: attempts, valid, invalid by ERROR_CLASSES and USD over the
    elicitation rows of the (protocol id, stage or None = every stage) pairs
    the analysis draws from, on the scenarios `scenario_ids` (None = all; the
    analysis passes the analysed ones, so a retired scenario's attempts do
    not count)."""
    out = {db.member_label(m): {"member": db.member_label(m), "attempts": 0, "valid": 0, "usd": 0.0,
                                **{c: 0 for c in ERROR_CLASSES}} for m in members}
    clause, args = db.member_filter(labels)
    if scenario_ids is not None:
        ids = sorted(int(i) for i in scenario_ids)
        clause += f" AND e.scenario_id IN ({','.join('?' * len(ids))})"
        args = [*args, *ids]
    for pid, stage in sources:
        sclause, sargs = db.stage_clause(stage) if stage is not None else ("", [])
        for r in con.execute("SELECT e.provider, e.model, e.valid, e.error, e.raw_response"
                             f" FROM elicitations e WHERE e.protocol_id=?{sclause}{clause}",
                             (pid, *sargs, *args)):
            label = f"{r['provider']}:{r['model']}"
            h = out.setdefault(label, {"member": label, "attempts": 0, "valid": 0, "usd": 0.0,
                                       **{c: 0 for c in ERROR_CLASSES}})
            h["attempts"] += 1
            h["usd"] += db.envelope_cost(r["raw_response"])
            if r["valid"]:
                h["valid"] += 1
            else:
                h[error_class(r["error"], r["raw_response"])] += 1
    return list(out.values())


def _row_scenarios(con, sources: list[tuple[int, str | None]], ids: list[int]) -> set[int]:
    """The scenarios whose elicitation rows feed the analysed ones: each
    analysed id plus, under a grouped decision stage, its group's rows
    (db.elicited_source_ids of a decision parameter)."""
    out = set(ids)
    for pid, _ in sources:
        for sid in ids:
            for name in DECISION_PARAMS:
                out.update(db.elicited_source_ids(con, pid, sid, name))
    return out


def decision_fits(con, prot, labels: list[str] | None) -> dict[int, dict[str, list[dict]]]:
    """{scenario id: {p|B|K: [fit rows]}} from a protocol's valid decision-stage
    (group-stage) elicitations alone, each group's rows given to every
    scenario of the group, in the order and form of db.scenario_param_fits
    (which only returns scenarios that also have instrument rows)."""
    gstage = db.group_stage(db.protocol_stages(prot))
    clause, args = db.member_filter(labels)
    group_of = {r["id"]: db.scenario_group_value(r, gstage["group_key"])
                for r in con.execute("SELECT * FROM scenarios")}
    by_group: dict[str, dict[str, list[dict]]] = {}
    for r in con.execute(
            "SELECT e.scenario_id, e.provider, e.model, e.id AS elicitation_id, p.name, p.p5, p.p50, p.p95,"
            " p.dist_family, p.fit_params FROM elicitations e JOIN parameters p ON p.elicitation_id = e.id"
            f" WHERE e.protocol_id=? AND e.valid=1 AND e.stage=?{clause}"
            " ORDER BY e.scenario_id, e.provider, e.model, e.repeat_ix, e.id",
            (prot["id"], gstage["name"], *args)):
        if r["name"] not in gstage["params"] or group_of.get(r["scenario_id"]) is None:
            continue
        fit = {"elicitation_id": r["elicitation_id"], "provider": r["provider"], "model": r["model"],
               "family": r["dist_family"], "params": json.loads(r["fit_params"]),
               "fit_params": r["fit_params"], "p5": r["p5"], "p50": r["p50"], "p95": r["p95"]}
        by_group.setdefault(group_of[r["scenario_id"]], {}).setdefault(r["name"], []).append(fit)
    return {sid: by_group[g] for sid, g in group_of.items() if g in by_group}


def load(con, protocol: str, members: list[str] | None = None, draws: int | None = None,
         decision_from: str | None = None) -> Summary:
    """Re-draw and verify the latest run of `protocol` (that pooled exactly
    `members`), read the pooled medians, elicited medians, sensitivities and
    elicitation health; decision_from names the protocol whose decision
    stage supplies p, B, K (module docstring)."""
    run = db.latest_run(con, protocol, members)
    labels = db.run_member_labels(run)
    prot = db.protocol_by_name(con, protocol)
    fits = mc.complete_fits(con, prot["id"], labels)
    source_pid = {name: prot["id"] for name in PARAM_NAMES}
    member_sets = {prot["id"]: _protocol_members(con, prot, labels)}
    stages = db.protocol_stages(prot)
    health_src: list[tuple[int, str | None]] = [(prot["id"], None)]
    if draws is not None and int(draws) < 1:
        raise RuntimeError(f"--draws {draws}: must be at least 1")
    if decision_from:
        mc.replay_efficiency(con, run["id"])   # the headline run still matches the DB
        dprot = db.protocol_by_name(con, decision_from)
        dfits = decision_fits(con, dprot, labels)
        dropped = sorted(sid for sid in fits if not all(dfits.get(sid, {}).get(n) for n in DECISION_PARAMS))
        if dropped:
            print(f"--decision-from {decision_from}: scenarios {dropped} have no complete valid decision"
                  " stage there and are left out of this analysis")
        fits = {sid: {**f, **{n: dfits[sid][n] for n in DECISION_PARAMS}} for sid, f in fits.items()
                if sid not in dropped}
        if not fits:
            raise RuntimeError(f"--decision-from {decision_from}: no scenario of run {run['id']} has"
                               f" valid decision-stage elicitations under {decision_from}")
        source_pid.update({n: dprot["id"] for n in DECISION_PARAMS})
        member_sets[dprot["id"]] = _protocol_members(con, dprot, labels)
        health_src = [(prot["id"], db.scenario_stage(stages)["name"]),
                      (dprot["id"], db.group_stage(db.protocol_stages(dprot))["name"])]
    if not fits:
        raise RuntimeError(f"run {run['id']}: no scenario with complete valid elicitations")

    keep = run["n_draws"] if draws is None else min(int(draws), run["n_draws"])
    ids, drawn, rho = [], {m: [] for m in DRAWN}, []
    stored_ids = {r[0] for r in con.execute(
        "SELECT scenario_id FROM results WHERE run_id=? AND metric=?", (run["id"], mc.PRIMARY_METRIC))}
    if not decision_from and set(fits) != stored_ids:
        retired = sorted(stored_ids - set(fits))
        raise RuntimeError(f"run {run['id']} replay mismatch: {len(fits)} scenarios now vs"
                           f" {len(stored_ids)} stored (elicitations changed since the run"
                           + (f", or scenarios {retired} left scenarios.json and are retired:"
                              " run voi_rank.mc again" if retired else "") + ")")
    rho_ind = []
    for sid, d in mc.iter_scenario_draws(fits, run["seed"], run["n_draws"]):
        m = model.metrics(d)
        if decision_from:
            rho.append([spearman(d[n], m["eta"]) for n in PARAM_NAMES])
        else:
            _verify(con, run["id"], sid, m)
        rho_ind.append([spearman(d[n], m["eta_ind"]) for n in PARAM_NAMES])
        ids.append(sid)
        for name in DRAWN:
            drawn[name].append(m[name][:keep])
    if not decision_from:
        stored = {(r["scenario_id"], r["param"]): r["spearman"] for r in con.execute(
            "SELECT * FROM sensitivities WHERE run_id=?", (run["id"],))}
        rho = [[stored.get((sid, n)) for n in PARAM_NAMES] for sid in ids]
    sens = np.array([[np.nan if v is None else v for v in row] for row in rho], dtype=float)
    sens_ind = np.array([[np.nan if v is None else v for v in row] for row in rho_ind], dtype=float)

    rows = {r["id"]: r for r in con.execute("SELECT * FROM scenarios")}
    scen = [scenario_info(rows[sid]) for sid in ids]
    all_labels = []
    for ms in member_sets.values():
        all_labels += [db.member_label(m) for m in ms if db.member_label(m) not in all_labels]
    elicited: dict[str, list[dict[str, list[float]]]] = {}
    pooled: dict[str, np.ndarray] = {}
    for name in PARAM_NAMES:
        pid = source_pid[name]
        per = [{db.member_label(m): db.elicited_p50s(con, pid, sid, name, provider=m["provider"],
                                                     model=m["model"]) for m in member_sets[pid]}
               for sid in ids]
        elicited[name] = per
        pooled[name] = np.array([float(np.median(sum(d.values(), []))) for d in per])
    central = {k: np.asarray(v, dtype=float) for k, v in model.metrics(pooled).items()}
    run_info = {"id": run["id"], "protocol": protocol, "seed": run["seed"], "n_draws": run["n_draws"],
                "draws_used": keep, "members": db.members_label(labels), "n_members": len(all_labels),
                "code_hash": run["code_hash"], "data_hash": run["data_hash"],
                "decision_from": decision_from, "verified": not decision_from}
    s = Summary(run=run_info, scenarios=scen, pooled=pooled, elicited=elicited, member_labels=all_labels,
                central=central, draws={k: np.vstack(v) for k, v in drawn.items()}, sensitivity=sens,
                health=health_rows(con, health_src, [m for ms in member_sets.values() for m in ms], labels,
                                   scenario_ids=_row_scenarios(con, health_src, ids)),
                sensitivity_ind=sens_ind)
    compute(s)
    return s


def rank_block(s: Summary, metric: str, phys, llm) -> dict:
    """Everything about the ranking by one metric: per-draw ranks, their
    quantiles and interquartile range, P(rank <= k), the central ranks and
    the rank of the best physical-AI evaluation (central and over draws)."""
    ranks = ranks_desc(s.draws[metric], axis=0)
    iq = np.quantile(ranks, IQR_QS, axis=1).T                             # (S, 2)
    out = {"ranks": ranks, "central": ranks_desc(s.central[metric]),
           "q": np.quantile(ranks, QS, axis=1).T,                           # (S, 3)
           "iqr_q": iq, "iqr": iq[:, 1] - iq[:, 0],
           "p_le": {k: (ranks <= k).mean(axis=1) for k in TOP_K}}
    if len(phys) and len(llm):
        ns = np.arange(1, len(s.scenarios) + 1)
        out["best_phys_ns"] = ns
        out["best_phys_curve"] = best_rank_curve(ranks[phys], ns)
        out["best_phys_central"] = float(out["central"][phys].min())
    return out


def domain_block(s: Summary, rank: dict) -> list[dict]:
    """Per risk domain (DOMAINS, in order, those present): the evaluations,
    the median over them of the central eta*, eta and stakes B+K, the median
    central rank by eta* and the median over draws of the domain's mean rank
    by eta*."""
    rows = []
    for dom in DOMAINS:
        idx = np.array([i for i, sc in enumerate(s.scenarios) if sc.domain == dom], dtype=int)
        if not len(idx):
            continue
        rows.append({"domain": dom, "label": DOMAIN_LABEL.get(dom, dom), "ids": idx, "n": int(len(idx)),
                     "med_eta_ind": float(np.median(s.central["eta_ind"][idx])),
                     "med_eta": float(np.median(s.central["eta"][idx])),
                     "med_stakes": float(np.median(s.pooled["B"][idx] + s.pooled["K"][idx])),
                     "med_rank_central": float(np.median(rank["central"][idx])),
                     "mean_rank_q": quantiles(rank["ranks"][idx].mean(axis=0)),
                     "zero_share": float((~(s.central["EVSI"][idx] > 0)).mean())})
    rows.sort(key=lambda r: r["med_rank_central"])
    return rows


def compute(s: Summary) -> dict:
    """Fill s.out with every derived number."""
    out = s.out
    phys, llm = s.ids_in(PHYS), s.ids_in(LLM)
    out["n_scenarios"] = len(s.scenarios)
    out["n_group"] = {PHYS: int(len(phys)), LLM: int(len(llm))}

    out["rank"] = {metric: rank_block(s, metric, phys, llm) for metric in RANKED}

    # the probability of superiority P_S = P(a random physical-AI evaluation scores higher than
    # a random LLM one), ties half: the Mann-Whitney U over the number of pairs
    out["groups"] = {}
    for metric in COMPARED:
        a_c, b_c = s.central[metric][phys], s.central[metric][llm]
        a_d = pairwise_share(s.draws[metric][phys], s.draws[metric][llm])
        out["groups"][metric] = {
            "A_central": pairwise_share(a_c, b_c),
            "A_q": quantiles(a_d) if len(phys) and len(llm) else [None] * 3,
            "mw_p": mann_whitney_p(a_c, b_c)}
    # P_S by eta among the evaluations whose result can change the decision (EVSI > 0, central)
    ch = s.central["EVSI"] > 0
    pc, lc = phys[ch[phys]], llm[ch[llm]]
    out["eta_A_changing"] = {"A": pairwise_share(s.central["eta"][pc], s.central["eta"][lc]),
                             "n_pairs": int(len(pc) * len(lc)), "n_phys": int(len(pc)),
                             "n_llm": int(len(lc))}
    eta = s.draws["eta"]
    if len(phys) and len(llm):
        out["roc"] = {}
        for metric in ROC_METRICS:
            f, t = roc_curve(s.central[metric][phys], s.central[metric][llm])
            out["roc"][metric] = {"fpr": f, "tpr": t, "area": roc_area(f, t),
                                  "band": roc_band(s.draws[metric][phys], s.draws[metric][llm])}
        curve_d = percentile_curve(eta[phys], eta[llm])
        out["curve_central"] = percentile_curve(s.central["eta"][phys], s.central["eta"][llm])
        out["curve_q"] = np.quantile(curve_d, QS, axis=1).T              # (101, 3)
        pct_d = percentile_among(eta[phys], eta[llm])
        out["pct_draws"] = pct_d                                          # (n_phys, D)
        out["pct_central"] = percentile_among(s.central["eta"][phys], s.central["eta"][llm])
        out["pct_q"] = np.quantile(pct_d, QS, axis=1).T
        med = np.percentile(eta[llm], 50, axis=0)
        out["p_beats_median"] = _above(eta[phys], med[None, :]).mean(axis=1)

    # break-even run count n* = C_build / (EVSI - C_run): finite on the draws where one run is
    # worth more than its run cost
    ns = s.draws["n_star"]
    out["nstar_q"] = np.array([quantiles(row) for row in ns], dtype=object)
    out["p_nstar_finite"] = np.isfinite(ns).mean(axis=1)
    out["p_changes"] = (s.draws["EVSI"] > 0).mean(axis=1)
    out["changes_share"] = {g: (float((s.central["EVSI"][idx] > 0).mean()) if len(idx) else None)
                            for g, idx in ((PHYS, phys), (LLM, llm))}
    out["zero_ids"] = {g: [s.scenarios[i].id for i in idx if not s.central["EVSI"][i] > 0]
                       for g, idx in ((PHYS, phys), (LLM, llm))}
    with np.errstate(all="ignore"):
        out["mean_abs_rho"] = {n: (float(np.nanmean(np.abs(s.sensitivity[:, j])))
                                   if np.isfinite(s.sensitivity[:, j]).any() else None)
                               for j, n in enumerate(PARAM_NAMES)}
        si = s.sensitivity_ind
        out["mean_abs_rho_ind"] = {n: (float(np.nanmean(np.abs(si[:, j])))
                                       if si is not None and np.isfinite(si[:, j]).any() else None)
                                   for j, n in enumerate(PARAM_NAMES)}

    lev = [i for i in phys if s.scenarios[i].level is not None]
    out["level_ids"] = np.array(lev, dtype=int)
    J = s.pooled["s"] + s.pooled["t"] - 1.0
    out["youden"] = J
    levels = [s.scenarios[i].level for i in lev]
    # the fidelity question: does a higher level buy more value per dollar? Spearman of
    # level with the central eta and eta*; Youden's index and cost are secondary
    for metric in LEVEL_METRICS:
        out[f"level_rho_{metric}"], out[f"level_p_{metric}"] = spearman_test(
            levels, list(s.central[metric][lev]))
    out["level_rho_J"], out["level_p_J"] = spearman_test(levels, list(J[lev]))
    out["level_rho_C"], out["level_p_C"] = spearman_test(levels, list(s.central["C"][lev]))

    out["domains"] = domain_block(s, out["rank"][PRIMARY])
    out["member_p50"] = member_pooled(s)
    out["member_rho"] = member_agreement(s, out["member_p50"])
    return out


def member_pooled(s: Summary) -> dict[str, dict[str, np.ndarray]]:
    """param -> member -> per-scenario median of that member's elicited p50s (NaN without one)."""
    return {name: {lab: np.array([float(np.median(d[lab])) if d.get(lab) else np.nan
                                  for d in s.elicited[name]]) for lab in s.member_labels}
            for name in PARAM_NAMES}


def member_agreement(s: Summary, mp: dict) -> dict[str, float | None]:
    """Per parameter, the mean over member pairs of the Spearman correlation
    of their per-scenario pooled p50s (scenarios both members answered)."""
    out = {}
    for name in PARAM_NAMES:
        rhos = []
        labs = [lab for lab in s.member_labels if np.isfinite(mp[name][lab]).any()]
        for i, a in enumerate(labs):
            for b in labs[i + 1:]:
                ok = np.isfinite(mp[name][a]) & np.isfinite(mp[name][b])
                r = spearman_or_none(list(mp[name][a][ok]), list(mp[name][b][ok]))
                if r is not None:
                    rhos.append(r)
        out[name] = float(np.mean(rhos)) if rhos else None
    return out


def order(s: Summary, metric: str = PRIMARY) -> list[int]:
    """Row indices by the central rank under `metric` (best first), ties by scenario id."""
    return sorted(range(len(s.scenarios)),
                  key=lambda i: (s.out["rank"][metric]["central"][i], s.scenarios[i].id))


def order_by_median_rank(s: Summary, metric: str = PRIMARY) -> list[int]:
    """Row indices by the median over draws of the rank under `metric` (best
    first), ties by the central rank, then scenario id."""
    r = s.out["rank"][metric]
    return sorted(range(len(s.scenarios)), key=lambda i: (r["q"][i][1], r["central"][i], s.scenarios[i].id))


def log_param(name: str) -> bool:
    return FAMILY_BY_PARAM[name] == "lognormal"


def _plain(v):
    if isinstance(v, np.ndarray):
        return [_plain(x) for x in v.tolist()]
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else float(v)
    if isinstance(v, np.integer):
        return int(v)
    return v


def to_json(s: Summary) -> str:
    """The run, the per-scenario table and the group numbers (no draw arrays)."""
    o = s.out
    per = []
    for i, sc in enumerate(s.scenarios):
        row = {"id": sc.id, "short": sc.short, "group": sc.group, "level": sc.level,
               "domain": sc.domain, "pooled": {n: s.pooled[n][i] for n in PARAM_NAMES},
               "central": {k: v[i] for k, v in s.central.items()},
               "p_changes": o["p_changes"][i], "p_nstar_finite": o["p_nstar_finite"][i],
               "nstar_q": list(o["nstar_q"][i])}
        for metric in RANKED:
            r = o["rank"][metric]
            row[f"rank_{metric}"] = {"central": r["central"][i], "q": r["q"][i],
                                     "p_le": {k: v[i] for k, v in r["p_le"].items()},
                                     "q25_q75": r["iqr_q"][i], "iqr": r["iqr"][i]}
        per.append(row)
    data = {"run": s.run, "n_group": o["n_group"], "groups": o["groups"],
            "changes_share": o["changes_share"], "zero_ids": o["zero_ids"],
            "mean_abs_rho": o["mean_abs_rho"], "mean_abs_rho_ind": o["mean_abs_rho_ind"],
            **{f"level_{k}_{m}": o[f"level_{k}_{m}"]
               for k in ("rho", "p") for m in (*LEVEL_METRICS, "J", "C")},
            "eta_A_changing": o["eta_A_changing"],
            "domains": [{k: v for k, v in d.items() if k != "ids"} for d in o["domains"]],
            "member_rho": o["member_rho"], "health": s.health, "scenarios": per}
    if "curve_q" in o:
        data["curve"] = {"q": CURVE_QS, "central": o["curve_central"], "q05_q50_q95": o["curve_q"]}
        data["physical_percentile"] = [
            {"id": s.scenarios[i].id, "central": o["pct_central"][k], "q05_q50_q95": o["pct_q"][k],
             "p_beats_median": o["p_beats_median"][k]} for k, i in enumerate(s.ids_in(PHYS))]
        data["best_physical_rank"] = {
            metric: {"n": o["rank"][metric]["best_phys_ns"], "p_le": o["rank"][metric]["best_phys_curve"],
                     "central": o["rank"][metric]["best_phys_central"]} for metric in RANKED}
        data["roc"] = {m: {"fpr": r["fpr"], "tpr": r["tpr"], "area": r["area"], "grid": ROC_FPR,
                           "tpr_q05_q50_q95": r["band"]} for m, r in o["roc"].items()}
    return json.dumps(_plain(data), indent=1, sort_keys=True) + "\n"
