"""Monte Carlo over the pooled belief (DESIGN section 6).

Pooled belief per parameter per scenario: the equal-weight mixture over the
fitted distributions of every valid elicitation under the protocol (all
members, all repeats; the linear opinion pool), so a member with more valid
repeats carries more weight. The eight parameters are drawn independently
(stated assumption), aligned across scenarios by one seeded rng stream.

--members provider:model,... pools only those members' valid fits (a subset
of the protocol's members, else the run is refused); the subset is stored on
the run (runs.members_json, NULL = every member) and read back by the replay.
A subset naming every member is the ordinary all-member run.

Stored per scenario (results rows, one per metric name):
- q05/q25/q50/q75/q95 of every metric of model.METRIC_NAMES: EVSI, EVPI,
  EVSI_ind (EVSI°), C, eta, eta_ind, eta_run, net_n, eta_n, n_star (inf where
  EVSI <= C_run; the quantiles are over the finite draws, NULL when none is)
  and pays;
- the probabilities p_positive = P(EVSI > C), p_changes = P(EVSI > 0),
  p_pays = P(n >= n_star) and p_top5 = P(rank <= 5 by eta, ties at zero
  never counting), each its own metric row with q50 holding the probability
  and the other columns NULL. This keeps one reader for everything a run
  stores (SELECT q50 ... WHERE metric=?); the archived results.p_positive
  column stays NULL for new runs.
Sensitivities: Spearman of each parameter's draws against eta, one row per
(scenario, parameter).

Provenance: a run stores code_hash (git HEAD of the code paths, '-dirty' when
they have uncommitted changes) and data_hash (sha256 over the sorted
(elicitation id, parameter, fit_params) of every valid elicitation it drew
from). A dirty code tree, or one whose revision git cannot report, is refused
unless --allow-dirty.

The console table after a run (print_run_table) lists every scenario ordered
by the central estimate of eta (central_estimate: the model at the pooled
medians, DESIGN section 6) with the run's eta quantiles and P(EVSI > C); the
MC median is not a ranking, so there is no rank column.

Scope: the study's scenarios.json. main() seeds it into voi.db first (as an
elicitation does), which retires every seed row whose title left the file
(db.seed_scenarios); complete_fits then leaves the retired rows out, so their
elicitations stay in the DB but enter no new run.

Usage: python -m voi_rank.mc --study studies/X --protocol p001 [--seed 42] [--draws 100000]
       [--allow-dirty] [--members claude_cli:sonnet,claude_cli:opus]
"""

from __future__ import annotations

import argparse
import json

import numpy as np

from voi_rank import db, model
from voi_rank.model import METRIC_NAMES
from voi_rank.sensitivity import rank_stability, spearman
from voi_rank.study import Study, add_study_arg

PRIMARY_METRIC = "eta"
PROBABILITY_NAMES = ["p_positive", "p_changes", "p_pays", "p_top5"]
SUMMARY_QS = (0.05, 0.25, 0.50, 0.75, 0.95)
RESULT_COLUMNS = ("q05", "q25", "q50", "q75", "q95")
REPLAY_RTOL = 1e-9
TOP_N_STABILITY = 5


def _draw(rng, family: str, params: dict, m: int) -> np.ndarray:
    if family == "lognormal":
        return rng.lognormal(params["mu"], params["sigma"], m)
    if family == "beta":
        return rng.beta(params["alpha"], params["beta"], m)
    raise ValueError(f"unknown family {family!r}")


def sample_mixture(rng, fits: list[dict], m: int) -> np.ndarray:
    """Equal-weight mixture over the fitted distributions of all valid
    (member, repeat) elicitations of one parameter."""
    if len(fits) == 1:
        return _draw(rng, fits[0]["family"], fits[0]["params"], m)
    idx = rng.integers(0, len(fits), size=m)
    out = np.empty(m)
    for r, f in enumerate(fits):
        mask = idx == r
        out[mask] = _draw(rng, f["family"], f["params"], int(mask.sum()))
    return out


def scenario_metrics(draws: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Per-draw metrics of one scenario from its parameter draws (model.metrics)."""
    return model.metrics(draws)


def probabilities(metrics: dict[str, np.ndarray]) -> dict[str, float]:
    """P(EVSI > C), P(EVSI > 0) and P(n >= n*) over the draws of one scenario."""
    return {"p_positive": float(np.mean(metrics["EVSI"] > metrics["C"])),
            "p_changes": float(np.mean(metrics["EVSI"] > 0.0)),
            "p_pays": float(np.mean(metrics["pays"]))}


def summarize(vec: np.ndarray) -> dict:
    """Quantiles over the finite draws (NaN and inf left out; None when none is)."""
    finite = vec[np.isfinite(vec)]
    if finite.size == 0:
        return {q: None for q in SUMMARY_QS}
    qs = np.quantile(finite, SUMMARY_QS)
    return dict(zip(SUMMARY_QS, (float(v) for v in qs), strict=True))


def complete_fits(con, protocol_id: int, members: list[str] | None = None,
                  scenario_ids=None) -> dict[int, dict[str, list[dict]]]:
    """Scenarios with at least one valid elicitation carrying every parameter
    (PARAM_NAMES), over every member or the `members` subset (labels). Only
    the active scenarios count (db.get_scenarios 'all': a retired seed row,
    whose title left scenarios.json, keeps its elicitations but is left
    out), unless `scenario_ids` names the set (a replay of a stored run)."""
    keep = ({r["id"] for r in db.get_scenarios(con, "all")} if scenario_ids is None
            else set(scenario_ids))
    return {
        sid: fits for sid, fits in sorted(db.scenario_param_fits(con, protocol_id, members=members).items())
        if sid in keep and all(name in fits for name in db.PARAM_NAMES)
    }


def data_hash(fits_by_scenario: dict[int, dict[str, list[dict]]]) -> str:
    """sha256 over the sorted distinct (elicitation_id, parameter name,
    fit_params) of the fits an MC run draws from: two runs with equal
    data_hash pooled exactly the same valid elicitations (a member subset
    changes it; a fit shared by several scenarios, as the decision stage of
    a grouped protocol is, counts once)."""
    rows = sorted({(f["elicitation_id"], name, f["fit_params"])
                   for fits in fits_by_scenario.values()
                   for name, lst in fits.items() for f in lst})
    return db.sha256(json.dumps(rows))


def iter_scenario_draws(fits_by_scenario: dict[int, dict[str, list[dict]]], seed: int, n_draws: int):
    """Deterministic generator of (scenario_id, draws dict) over a
    complete_fits() dict (sorted by scenario id). The rng stream is consumed
    in scenario-id, PARAM_NAMES order, so a replay with the same DB state
    reproduces the run's draws exactly. run_mc passes the very dict its
    data_hash was computed from, so the hash always describes the fits
    drawn."""
    rng = np.random.default_rng(seed)
    for sid, fits in fits_by_scenario.items():
        yield sid, {name: sample_mixture(rng, fits[name], n_draws) for name in db.PARAM_NAMES}


def stored_probability(con, run_id: int, scenario_id: int, name: str) -> float | None:
    """A stored probability row (PROBABILITY_NAMES) of one scenario of a run."""
    row = con.execute("SELECT q50 FROM results WHERE run_id=? AND scenario_id=? AND metric=?",
                      (run_id, scenario_id, name)).fetchone()
    return None if row is None else row[0]


def replay_efficiency(con, run_id: int):
    """Recompute the eta draw matrix of a stored run from the DB alone (seed,
    n_draws and fitted params are all persisted). Guards against the
    valid-elicitation set having changed since the run: every stored eta
    quantile and p_positive is verified."""
    run = db.get_run(con, run_id)
    ids, effs, ppos = [], [], []
    stored = {r["scenario_id"]: r for r in con.execute(
        "SELECT * FROM results WHERE run_id=? AND metric=?", (run_id, PRIMARY_METRIC))}
    # the run's own scenarios (retired ones included) and member subset: the rng stream
    # is consumed in their order, so the replay redraws exactly what the run drew
    fits = complete_fits(con, run["protocol_id"], db.run_member_labels(run), scenario_ids=stored)
    if not fits:
        raise RuntimeError(f"run {run_id}: no scenarios with complete valid elicitations under its protocol"
                           " (an archived six-parameter run cannot be replayed by the current code)")
    for sid, draws in iter_scenario_draws(fits, run["seed"], run["n_draws"]):
        ids.append(sid)
        metrics = scenario_metrics(draws)
        effs.append(metrics[PRIMARY_METRIC])
        ppos.append(probabilities(metrics)["p_positive"])
    eff = np.vstack(effs)
    if set(ids) != set(stored):
        raise RuntimeError(
            f"run {run_id} replay mismatch: elicitations changed since the run "
            f"({len(ids)} scenarios now vs {len(stored)} stored)")
    for i, sid in enumerate(ids):
        got = summarize(eff[i])
        checks = [(col, got[q], stored[sid][col]) for q, col in zip(SUMMARY_QS, RESULT_COLUMNS, strict=True)]
        checks.append(("p_positive", ppos[i], stored_probability(con, run_id, sid, "p_positive")))
        for label, value, want in checks:
            if want is None or abs(value - want) > REPLAY_RTOL * max(1.0, abs(want)):
                raise RuntimeError(
                    f"run {run_id} replay mismatch on scenario {sid}: {PRIMARY_METRIC} {label} "
                    f"{value} vs stored {want}: valid elicitations changed "
                    "since the run (e.g. repeats added under the same protocol)")
    return ids, eff


def run_mc(con, protocol_name: str, seed: int, n_draws: int, quiet: bool = False,
           allow_dirty: bool = False, members: list[str] | None = None) -> int:
    """Execute one MC run over all active scenarios (complete_fits) with
    complete valid elicitations under the protocol. Writes runs, results (every metric's quantiles and the
    probability rows, p_top5 included) and sensitivities. Returns the run id.
    Uncommitted changes under db.CODE_PATHS, or a code revision that cannot
    be determined (no git, not a repository), are refused unless allow_dirty
    (then code_hash is stored as '<hash>-dirty' or 'unknown' and a warning is
    printed). members (labels) pools only that subset of the protocol's
    members; a label the protocol does not list exits, and a subset naming
    every member is stored as the all-member run (members_json NULL)."""
    protocol = db.protocol_by_name(con, protocol_name)
    try:
        members = db.normalize_run_members(db.protocol_members(protocol), members)
    except ValueError as ex:
        raise SystemExit(f"--members: {ex}") from None
    fits = complete_fits(con, protocol["id"], members)
    if not fits:
        raise RuntimeError(f"no scenarios with complete valid elicitations under {protocol_name}"
                           + (f" from members [{db.members_label(members)}]" if members else ""))
    head, dirty = db.git_state()
    code_hash = f"{head}-dirty" if dirty else head
    if head == db.UNKNOWN_HEAD and not allow_dirty:
        raise RuntimeError(
            "the code revision could not be determined (git unavailable, or the code is not in"
            " a git repository): run from a git checkout, or pass --allow-dirty to store"
            f" code_hash {code_hash} (not reproducible from any commit)")
    if dirty and not allow_dirty:
        raise RuntimeError(
            f"working tree has uncommitted code changes ({len(dirty)} path(s)):\n  "
            + "\n  ".join(dirty)
            + "\ncommit them, or pass --allow-dirty to store code_hash "
            f"{code_hash} (not reproducible from any commit)")
    run_id = db.insert_run(con, seed, n_draws, protocol["id"], data_hash(fits), code_hash, members)
    if dirty or head == db.UNKNOWN_HEAD:
        print(f"WARNING: {'working tree has uncommitted changes' if dirty else 'code revision unknown'};"
              f" run {run_id} stores code_hash {code_hash} (commit, then re-run for a reproducible hash)")

    scenario_ids = []
    eff_rows = []
    for sid, draws in iter_scenario_draws(fits, seed, n_draws):
        scenario_ids.append(sid)
        metrics = scenario_metrics(draws)
        for name in METRIC_NAMES:
            db.insert_result(con, run_id, sid, name, summarize(metrics[name]))
        for name, value in probabilities(metrics).items():
            db.insert_result(con, run_id, sid, name, {0.50: value})
        for name in db.PARAM_NAMES:
            db.insert_sensitivity(con, run_id, sid, name, spearman(draws[name], metrics[PRIMARY_METRIC]))
        eff_rows.append(metrics[PRIMARY_METRIC])

    p_top = rank_stability(np.vstack(eff_rows), top=TOP_N_STABILITY)
    for i, sid in enumerate(scenario_ids):
        db.insert_result(con, run_id, sid, "p_top5", {0.50: float(p_top[i])})
    con.commit()

    if not quiet:
        print_run_table(con, run_id)
        print(f"\nrun {run_id}: code_hash {code_hash}, data_hash {db.get_run(con, run_id)['data_hash']}"
              f" over {len(scenario_ids)} scenarios, members: {db.members_label(members)}")
    return run_id


def pooled_medians(con, protocol_id: int, scenario_id: int,
                   members: list[str] | None = None) -> dict[str, float]:
    """The pooled median of every parameter of one scenario: the median over
    the valid elicitations under the protocol (the `members` subset, else
    all) of each elicited median (DESIGN section 2)."""
    return {name: float(np.median(db.elicited_p50s(con, protocol_id, scenario_id, name, members=members)))
            for name in db.PARAM_NAMES}


def central_estimate(con, protocol_id: int, scenario_id: int,
                     members: list[str] | None = None) -> dict[str, float]:
    """The central estimate of one scenario: the model at its pooled medians
    (DESIGN section 6: point tables and the headline figure use it; the MC
    median is not a ranking). Every metric of METRIC_NAMES as a float."""
    draws = pooled_medians(con, protocol_id, scenario_id, members)
    return {name: float(value) for name, value in model.metrics(draws).items()}


def print_run_table(con, run_id: int, limit: int = 30):
    """The per-scenario table of a run: the central estimate of eta (the
    ordering), the run's eta quantiles and P(EVSI > C). No rank column: the
    MC median is not a ranking (DESIGN section 6)."""
    run = db.get_run(con, run_id)
    members = db.run_member_labels(run)
    rows = con.execute(
        "SELECT r.scenario_id, s.title, r.q05, r.q50, r.q95,"
        " (SELECT q50 FROM results p WHERE p.run_id=r.run_id AND p.scenario_id=r.scenario_id"
        "  AND p.metric='p_positive') AS p_positive"
        " FROM results r JOIN scenarios s ON s.id = r.scenario_id"
        " WHERE r.run_id=? AND r.metric=? ORDER BY r.scenario_id",
        (run_id, PRIMARY_METRIC)).fetchall()
    central = {r["scenario_id"]: central_estimate(con, run["protocol_id"], r["scenario_id"], members)
               for r in rows}
    rows = sorted(rows, key=lambda r: -central[r["scenario_id"]][PRIMARY_METRIC])[:limit]
    print(f"\nPer-scenario {PRIMARY_METRIC} (EVSI/C) of run {run_id}, ordered by the central estimate"
          f" (model at the pooled medians; members: {db.members_label(members)}):")
    print(f"{'id':>4} {'eta central':>12} {'eta q05':>10} {'eta q50':>10} {'eta q95':>10}"
          f" {'P(EVSI>C)':>10}  title")
    for r in rows:
        c = central[r["scenario_id"]][PRIMARY_METRIC]
        print(f"{r['scenario_id']:>4} {c:>12.3g} {r['q05']:>10.3g} {r['q50']:>10.3g}"
              f" {r['q95']:>10.3g} {r['p_positive']:>10.2f}  {r['title'][:60]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    ap.add_argument("--protocol", required=True, help="protocol name, e.g. p001")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--draws", type=int, default=100_000)
    ap.add_argument("--allow-dirty", action="store_true",
                    help="run with uncommitted code changes (code_hash is stored as <hash>-dirty)")
    ap.add_argument("--members", default=None,
                    help="comma-separated provider:model subset of the protocol's members to pool"
                         " (default: all members)")
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    # seed first, so a scenario that left scenarios.json is retired (kept with its
    # elicitations, left out of the run) and the run covers exactly the file's scenarios
    try:
        db.seed_scenarios(con, study.scenarios_json)
    except RuntimeError as ex:   # an elicited scenario that differs from the file
        raise SystemExit(str(ex)) from None
    members = db.parse_member_labels(args.members)
    try:
        run_id = run_mc(con, args.protocol, args.seed, args.draws, allow_dirty=args.allow_dirty,
                        members=members)
    except RuntimeError as ex:   # an unregistered protocol, a dirty tree, no complete fits: no traceback
        raise SystemExit(str(ex)) from None
    run = db.get_run(con, run_id)
    print(f"\nrun {run_id} complete: study={study.name} protocol={args.protocol} "
          f"seed={args.seed} draws={args.draws}"
          f" members={db.members_label(db.run_member_labels(run))}")


if __name__ == "__main__":
    main()
