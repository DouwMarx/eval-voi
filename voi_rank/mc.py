"""Monte Carlo over elicitation uncertainty (spec §4).

The parameters are drawn independently (stated assumption). Pooling: for
each scenario, ALL valid elicitations under the protocol, over every ensemble
member (provider, model) and every repeat, are pooled into ONE mixture per
parameter. By default ('--weights pooled', stored as runs.weights NULL) the
mixture is equal-weight over the fits, so a member with more valid repeats
carries more weight. '--weights equal-member' (v2.4) makes each member's fits
a sub-mixture and gives the members present equal weight, whatever their
repeat counts (fit i of member m weighs 1 / (members x fits of m)); when
every member holds the same number of fits the two coincide and draw the
same numbers, and a run pooling one member is stored as pooled. The
weighting is stored on the run, covered by data_hash and read back by the
replay. Cross-repeat and cross-model disagreement both widen the metric
intervals. A 'point' family (the derived quantities of the Gaussian
protocol) is drawn as a constant, so its mixture over repeats is the
empirical distribution of the repeat values.

--members provider:model,... (v2.2) pools only those members' valid fits (a
subset of the protocol's members, else the run is refused); the subset is
stored on the run (runs.members_json, NULL = every member) and read back by
the replay and by every analysis that selects the run with the same
--members. A subset naming every member is the ordinary all-member run.

Binary protocol: per scenario the run stores q05/q25/q50/q75/q95 of EVSI,
EVPI, efficiency, margin, headroom, C (the pooled cost mixture) and
evpi_efficiency (EVPI / C per draw, so the simpler perfect-information
ranking is summarised by the same estimator as the EVSI/C ranking),
P(EVSI > C), local Spearman sensitivities against efficiency and P(top 10).

Gaussian protocol (spec v2.1): the same summaries of EVSI_<m>, EVPI_<m>,
eff_<m> for the action models m in quad, kg, step, stepfix, plus R2, d, x, k,
p_derived, s_derived, t_derived and C (voi_rank.gaussian.METRIC_NAMES);
p_positive = P(EVSI_step > C); sensitivities of the quantities that enter
the metrics (db.sensitivity_names: gaussian.METRIC_INPUTS, i.e. every stored
quantity but g_mu0 and g_sigma0, which no action model reads) against
eff_step; P(top 10) on eff_step. The primary metric of a run is
db.primary_metric(kind): 'efficiency' or 'eff_step'.

Provenance: a run stores code_hash (git HEAD of the code paths, '-dirty' when
they have uncommitted changes) and data_hash (sha256 over the sorted
(elicitation id, parameter, fit_params) of every valid elicitation it drew
from). A dirty code tree, or one whose revision git cannot report, is refused
unless --allow-dirty.

Usage: python -m voi_rank.mc --study studies/business --protocol p001 [--seed 42] [--draws 100000]
       [--allow-dirty] [--members claude_cli:sonnet,claude_cli:opus] [--weights equal-member]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np

from voi_rank import db, gaussian, model
from voi_rank.sensitivity import rank_stability, spearman
from voi_rank.study import Study, add_study_arg

METRIC_NAMES = ["EVSI", "EVPI", "efficiency", "margin", "headroom", "C", "evpi_efficiency"]
SUMMARY_QS = (0.05, 0.25, 0.50, 0.75, 0.95)
RESULT_COLUMNS = ("q05", "q25", "q50", "q75", "q95")
REPLAY_RTOL = 1e-9
TOP_N_STABILITY = 10


def metric_names(kind: str) -> list[str]:
    """The metrics a run of this model kind stores (besides p_top10)."""
    return gaussian.METRIC_NAMES if db.normalize_model_kind(kind) == db.GAUSSIAN_KIND else METRIC_NAMES


def _draw(rng, family: str, params: dict, m: int) -> np.ndarray:
    if family == "lognormal":
        return rng.lognormal(params["mu"], params["sigma"], m)
    if family == "beta":
        return rng.beta(params["alpha"], params["beta"], m)
    if family == "point":
        return np.full(m, float(params["value"]))
    raise ValueError(f"unknown family {family!r}")


def member_probs(fits: list[dict]) -> np.ndarray | None:
    """Per-fit mixture probabilities that give every member present the same
    total weight: fit i of member m weighs 1 / (members x fits of m). None
    when every member holds the same number of fits, where they are uniform
    (the pooled mixture, drawn by the same rng calls)."""
    labels = [f"{f['provider']}:{f['model']}" for f in fits]
    counts = Counter(labels)
    if len(set(counts.values())) == 1:
        return None
    return np.array([1.0 / (len(counts) * counts[label]) for label in labels])


def sample_mixture(rng, fits: list[dict], m: int, weights: str | None = None) -> np.ndarray:
    """Mixture over the fitted distributions of all valid (member, repeat)
    elicitations: equal weight per fit (weights None or 'pooled'), or equal
    weight per member ('equal-member', member_probs)."""
    if len(fits) == 1:
        return _draw(rng, fits[0]["family"], fits[0]["params"], m)
    probs = member_probs(fits) if db.normalize_weights(weights) == db.WEIGHTS_EQUAL_MEMBER else None
    idx = rng.integers(0, len(fits), size=m) if probs is None else rng.choice(len(fits), size=m, p=probs)
    out = np.empty(m)
    for r, f in enumerate(fits):
        mask = idx == r
        out[mask] = _draw(rng, f["family"], f["params"], int(mask.sum()))
    return out


def binary_metrics(draws: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    evsi, evpi = model.voi(draws["p"], draws["s"], draws["t"], draws["B"], draws["K"])
    C = draws["C"]
    headroom = np.where(evpi > 0.0, evsi / np.where(evpi > 0.0, evpi, 1.0), np.nan)
    return {
        "EVSI": evsi,
        "EVPI": evpi,
        "efficiency": evsi / C,
        "margin": evsi - C,
        "headroom": headroom,
        "C": C,
        "evpi_efficiency": evpi / C,
    }


def scenario_metrics(draws: dict[str, np.ndarray], kind: str = db.BINARY_KIND) -> dict[str, np.ndarray]:
    """Per-draw metrics of one scenario from its parameter draws, keyed by
    metric_names(kind)."""
    if db.normalize_model_kind(kind) == db.GAUSSIAN_KIND:
        return gaussian.scenario_metrics(draws)
    return binary_metrics(draws)


def summarize(vec: np.ndarray) -> dict:
    finite = vec[~np.isnan(vec)]
    if finite.size == 0:
        return {q: None for q in SUMMARY_QS}
    qs = np.quantile(finite, SUMMARY_QS)
    return dict(zip(SUMMARY_QS, (float(v) for v in qs), strict=True))


def protocol_kind(con, protocol_id: int) -> str:
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()
    if prot is None:
        raise RuntimeError(f"no protocol {protocol_id}")
    return db.protocol_model_kind(prot)


def complete_fits(con, protocol_id: int,
                  members: list[str] | None = None) -> dict[int, dict[str, list[dict]]]:
    """Scenarios with at least one valid elicitation carrying every parameter
    of the protocol's model kind, over every member or the `members` subset
    (labels)."""
    names = db.param_names(protocol_kind(con, protocol_id))
    return {
        sid: fits for sid, fits in sorted(db.scenario_param_fits(con, protocol_id, names, members).items())
        if all(name in fits for name in names)
    }


def data_hash(fits_by_scenario: dict[int, dict[str, list[dict]]], weights: str | None = None) -> str:
    """sha256 over the sorted distinct (elicitation_id, parameter name,
    fit_params) of the fits an MC run draws from: two runs with equal
    data_hash pooled exactly the same valid elicitations (a member subset
    changes it; a fit shared by several scenarios, as the decision stage of
    a staged protocol is, counts once). An equal-member run (weights, the
    stored form) hashes {"weights", "fits"}, so it never shares a hash with
    the pooled run of the same fits; a pooled run's hash is unchanged."""
    rows = sorted({(f["elicitation_id"], name, f["fit_params"])
                   for fits in fits_by_scenario.values()
                   for name, lst in fits.items() for f in lst})
    weights = db.normalize_weights(weights)
    return db.sha256(json.dumps(rows if weights is None else {"weights": weights, "fits": rows}))


def iter_scenario_draws(fits_by_scenario: dict[int, dict[str, list[dict]]], seed: int, n_draws: int,
                        names: list[str] | None = None, weights: str | None = None):
    """Deterministic generator of (scenario_id, draws dict) over a
    complete_fits() dict (sorted by scenario id). The rng stream is consumed
    in scenario-id, parameter-name order (PARAM_NAMES by default, the
    protocol's names otherwise), so a replay with the same DB state and
    weights reproduces the run's draws exactly. run_mc passes the very dict
    its data_hash was computed from, so the hash always describes the fits
    drawn."""
    names = list(db.PARAM_NAMES if names is None else names)
    rng = np.random.default_rng(seed)
    for sid, fits in fits_by_scenario.items():
        yield sid, {name: sample_mixture(rng, fits[name], n_draws, weights) for name in names}


def replay_efficiency(con, run_id: int):
    """Recompute the primary-efficiency draw matrix of a stored run from the
    DB alone (seed, n_draws and fitted params are all persisted): 'efficiency'
    for a binary run, 'eff_step' for a Gaussian one. Guards against the
    valid-elicitation set having changed since the run."""
    run = db.get_run(con, run_id)
    kind = protocol_kind(con, run["protocol_id"])
    metric, evsi_name = db.primary_metric(kind), db.evsi_metric(kind)
    ids, effs, ppos = [], [], []
    fits = complete_fits(con, run["protocol_id"], db.run_member_labels(run))   # the stored subset
    for sid, draws in iter_scenario_draws(fits, run["seed"], run["n_draws"], db.param_names(kind),
                                          db.run_weights(run)):              # and weighting
        ids.append(sid)
        metrics = scenario_metrics(draws, kind)
        effs.append(metrics[metric])
        ppos.append(float(np.mean(metrics[evsi_name] > draws["C"])))  # as run_mc stores it
    eff = np.vstack(effs)
    # any change to the valid-elicitation set since the run (new scenarios OR
    # extra repeats on existing ones) desynchronizes the shared rng stream, so
    # verify the replay against every stored efficiency summary per scenario
    stored = {r["scenario_id"]: r for r in con.execute(
        "SELECT * FROM results WHERE run_id=? AND metric=?", (run_id, metric))}
    if set(ids) != set(stored):
        raise RuntimeError(
            f"run {run_id} replay mismatch: elicitations changed since the run "
            f"({len(ids)} scenarios now vs {len(stored)} stored)")
    for i, sid in enumerate(ids):
        got = summarize(eff[i])
        got["p_positive"] = ppos[i]
        for key, col in (*zip(SUMMARY_QS, RESULT_COLUMNS, strict=True), ("p_positive", "p_positive")):
            want = stored[sid][col]
            if abs(got[key] - want) > REPLAY_RTOL * max(1.0, abs(want)):
                raise RuntimeError(
                    f"run {run_id} replay mismatch on scenario {sid}: {metric} {col} "
                    f"{got[key]} vs stored {want}: valid elicitations changed "
                    "since the run (e.g. repeats added under the same protocol), or the "
                    "run predates the current model (v1 runs included parameter e)")
    return ids, eff


def run_mc(con, protocol_name: str, seed: int, n_draws: int, quiet: bool = False,
           allow_dirty: bool = False, members: list[str] | None = None,
           weights: str | None = None) -> int:
    """Execute one MC run over all scenarios with valid elicitations under the
    protocol. Writes runs, results (incl. a p_top10 stability row per scenario)
    and sensitivities. Returns the run id. Uncommitted changes under
    db.CODE_PATHS, or a code revision that cannot be determined (no git, not
    a repository), are refused unless allow_dirty (then code_hash is stored
    as '<hash>-dirty' or 'unknown' and a warning is printed). members (labels)
    pools only that subset of the protocol's members; a label the protocol
    does not list exits, and a subset naming every member is stored as the
    all-member run (members_json NULL). weights: 'pooled' (None) or
    'equal-member' (sample_mixture), stored on the run (NULL = pooled, and
    pooled for a run of one member) and hashed into data_hash."""
    protocol = db.protocol_by_name(con, protocol_name)
    kind = db.protocol_model_kind(protocol)
    names = db.param_names(kind)
    metric, evsi_name = db.primary_metric(kind), db.evsi_metric(kind)
    try:
        members = db.normalize_run_members(db.protocol_members(protocol), members)
    except ValueError as ex:
        raise SystemExit(f"--members: {ex}") from None
    try:
        weights = db.normalize_run_weights(
            len(db.protocol_members(protocol)) if members is None else len(members), weights)
    except ValueError as ex:
        raise SystemExit(f"--weights: {ex}") from None
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
    run_id = db.insert_run(con, seed, n_draws, protocol["id"], data_hash(fits, weights), code_hash, members,
                           weights)
    if dirty or head == db.UNKNOWN_HEAD:
        print(f"WARNING: {'working tree has uncommitted changes' if dirty else 'code revision unknown'};"
              f" run {run_id} stores code_hash {code_hash} (commit, then re-run for a reproducible hash)")

    scenario_ids = []
    eff_rows = []
    for sid, draws in iter_scenario_draws(fits, seed, n_draws, names, weights):
        scenario_ids.append(sid)
        metrics = scenario_metrics(draws, kind)
        p_positive = float(np.mean(metrics[evsi_name] > draws["C"]))
        for name in metric_names(kind):
            db.insert_result(con, run_id, sid, name, summarize(metrics[name]), p_positive)
        for name in db.sensitivity_names(kind):
            db.insert_sensitivity(con, run_id, sid, name, spearman(draws[name], metrics[metric]))
        eff_rows.append(metrics[metric])

    p_top = rank_stability(np.vstack(eff_rows), top=TOP_N_STABILITY)
    for i, sid in enumerate(scenario_ids):
        db.insert_result(con, run_id, sid, "p_top10", {}, float(p_top[i]))
    con.commit()

    if not quiet:
        print_ranking(con, run_id)
        print(f"\nrun {run_id}: code_hash {code_hash}, data_hash {db.get_run(con, run_id)['data_hash']}"
              f" over {len(scenario_ids)} scenarios, members: {db.members_label(members)},"
              f" weights: {db.weights_label(weights)}")
    return run_id


def print_ranking(con, run_id: int, limit: int = 30):
    run = db.get_run(con, run_id)
    kind = protocol_kind(con, run["protocol_id"])
    metric, evsi_name = db.primary_metric(kind), db.evsi_metric(kind)
    rows = con.execute(
        "SELECT r.scenario_id, s.title, r.q05, r.q50, r.q95, r.p_positive"
        " FROM results r JOIN scenarios s ON s.id = r.scenario_id"
        " WHERE r.run_id=? AND r.metric=? ORDER BY r.q50 DESC LIMIT ?",
        (run_id, metric, limit)).fetchall()
    print(f"\nRanking by median {metric} ({evsi_name}/C), run {run_id}"
          f" (members: {db.members_label(db.run_member_labels(run))}"
          + (f", weights: {db.run_weights(run)}" if db.run_weights(run) else "") + "):")
    print(f"{'rank':>4} {'id':>4} {'eff q50':>10} {'eff q05':>10} {'eff q95':>10} {'P(EVSI>C)':>10}  title")
    for rank, r in enumerate(rows, 1):
        print(f"{rank:>4} {r['scenario_id']:>4} {r['q50']:>10.3g} {r['q05']:>10.3g}"
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
    ap.add_argument("--weights", choices=db.WEIGHT_CHOICES, default=db.WEIGHTS_POOLED,
                    help="pooled: every valid (member, repeat) fit weighs the same (default);"
                         " equal-member: every member weighs the same, whatever its repeat count")
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    members = db.parse_member_labels(args.members)
    run_id = run_mc(con, args.protocol, args.seed, args.draws, allow_dirty=args.allow_dirty,
                    members=members, weights=args.weights)
    run = db.get_run(con, run_id)
    print(f"\nrun {run_id} complete: study={study.name} protocol={args.protocol} "
          f"seed={args.seed} draws={args.draws}"
          f" members={db.members_label(db.run_member_labels(run))}"
          f" weights={db.weights_label(db.run_weights(run))}")


if __name__ == "__main__":
    main()
