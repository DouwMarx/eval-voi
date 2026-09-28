"""Monte Carlo over elicitation uncertainty (spec §4).

The six parameters are drawn independently (stated assumption). Pooling: for
each scenario, ALL valid elicitations under the protocol, over every ensemble
member (provider, model) and every repeat, are pooled into ONE equal-weight
mixture per parameter. A member with more valid repeats therefore carries
more weight; there is no per-member reweighting. Cross-repeat and cross-model
disagreement both widen the metric intervals.

Per scenario the run stores q05/q25/q50/q75/q95 of EVSI, EVPI, efficiency,
margin, headroom, C (the pooled cost mixture) and evpi_efficiency (EVPI / C
per draw, so the simpler perfect-information ranking is summarised by the
same estimator as the EVSI/C ranking), P(EVSI > C), local Spearman
sensitivities and P(top 10).

Provenance: a run stores code_hash (git HEAD of the code paths, '-dirty' when
they have uncommitted changes) and data_hash (sha256 over the sorted
(elicitation id, parameter, fit_params) of every valid elicitation it drew
from). A dirty code tree, or one whose revision git cannot report, is refused
unless --allow-dirty.

Usage: python -m voi_rank.mc --study studies/business --protocol p001 [--seed 42] [--draws 100000]
       [--allow-dirty]
"""

from __future__ import annotations

import argparse
import json

import numpy as np

from voi_rank import db, model
from voi_rank.sensitivity import rank_stability, spearman
from voi_rank.study import Study, add_study_arg

METRIC_NAMES = ["EVSI", "EVPI", "efficiency", "margin", "headroom", "C", "evpi_efficiency"]
SUMMARY_QS = (0.05, 0.25, 0.50, 0.75, 0.95)
RESULT_COLUMNS = ("q05", "q25", "q50", "q75", "q95")
REPLAY_RTOL = 1e-9
TOP_N_STABILITY = 10


def _draw(rng, family: str, params: dict, m: int) -> np.ndarray:
    if family == "lognormal":
        return rng.lognormal(params["mu"], params["sigma"], m)
    if family == "beta":
        return rng.beta(params["alpha"], params["beta"], m)
    raise ValueError(f"unknown family {family!r}")


def sample_mixture(rng, fits: list[dict], m: int) -> np.ndarray:
    """Equal-weight mixture over the fitted distributions of all valid
    (member, repeat) elicitations."""
    if len(fits) == 1:
        return _draw(rng, fits[0]["family"], fits[0]["params"], m)
    idx = rng.integers(0, len(fits), size=m)
    out = np.empty(m)
    for r, f in enumerate(fits):
        mask = idx == r
        out[mask] = _draw(rng, f["family"], f["params"], int(mask.sum()))
    return out


def scenario_metrics(draws: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
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


def summarize(vec: np.ndarray) -> dict:
    finite = vec[~np.isnan(vec)]
    if finite.size == 0:
        return {q: None for q in SUMMARY_QS}
    qs = np.quantile(finite, SUMMARY_QS)
    return dict(zip(SUMMARY_QS, (float(v) for v in qs), strict=True))


def complete_fits(con, protocol_id: int) -> dict[int, dict[str, list[dict]]]:
    """Scenarios with at least one valid elicitation carrying every parameter."""
    return {
        sid: fits for sid, fits in sorted(db.scenario_param_fits(con, protocol_id).items())
        if all(name in fits for name in db.PARAM_NAMES)
    }


def data_hash(fits_by_scenario: dict[int, dict[str, list[dict]]]) -> str:
    """sha256 over the sorted (elicitation_id, parameter name, fit_params) of
    the fits an MC run draws from: two runs with equal data_hash pooled
    exactly the same valid elicitations."""
    rows = sorted((f["elicitation_id"], name, f["fit_params"])
                  for fits in fits_by_scenario.values()
                  for name, lst in fits.items() for f in lst)
    return db.sha256(json.dumps(rows))


def iter_scenario_draws(fits_by_scenario: dict[int, dict[str, list[dict]]], seed: int, n_draws: int):
    """Deterministic generator of (scenario_id, draws dict) over a
    complete_fits() dict (sorted by scenario id). The rng stream is consumed
    in scenario-id, PARAM_NAMES order, so a replay with the same DB state
    reproduces the run's draws exactly. run_mc passes the very dict its
    data_hash was computed from, so the hash always describes the fits drawn."""
    rng = np.random.default_rng(seed)
    for sid, fits in fits_by_scenario.items():
        yield sid, {name: sample_mixture(rng, fits[name], n_draws)
                    for name in db.PARAM_NAMES}


def replay_efficiency(con, run_id: int):
    """Recompute the efficiency draw matrix of a stored run from the DB alone
    (seed, n_draws and fitted params are all persisted). Guards against the
    valid-elicitation set having changed since the run."""
    run = db.get_run(con, run_id)
    ids, effs, ppos = [], [], []
    for sid, draws in iter_scenario_draws(complete_fits(con, run["protocol_id"]), run["seed"],
                                          run["n_draws"]):
        ids.append(sid)
        metrics = scenario_metrics(draws)
        effs.append(metrics["efficiency"])
        ppos.append(float(np.mean(metrics["EVSI"] > draws["C"])))  # as run_mc stores it
    eff = np.vstack(effs)
    # any change to the valid-elicitation set since the run (new scenarios OR
    # extra repeats on existing ones) desynchronizes the shared rng stream, so
    # verify the replay against every stored efficiency summary per scenario
    stored = {r["scenario_id"]: r for r in con.execute(
        "SELECT * FROM results WHERE run_id=? AND metric='efficiency'", (run_id,))}
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
                    f"run {run_id} replay mismatch on scenario {sid}: efficiency {col} "
                    f"{got[key]} vs stored {want}: valid elicitations changed "
                    "since the run (e.g. repeats added under the same protocol), or the "
                    "run predates the current model (v1 runs included parameter e)")
    return ids, eff


def run_mc(con, protocol_name: str, seed: int, n_draws: int, quiet: bool = False,
           allow_dirty: bool = False) -> int:
    """Execute one MC run over all scenarios with valid elicitations under the
    protocol. Writes runs, results (incl. a p_top10 stability row per scenario)
    and sensitivities. Returns the run id. Uncommitted changes under
    db.CODE_PATHS, or a code revision that cannot be determined (no git, not
    a repository), are refused unless allow_dirty (then code_hash is stored
    as '<hash>-dirty' or 'unknown' and a warning is printed)."""
    protocol = db.protocol_by_name(con, protocol_name)
    fits = complete_fits(con, protocol["id"])
    if not fits:
        raise RuntimeError(f"no scenarios with complete valid elicitations under {protocol_name}")
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
    run_id = db.insert_run(con, seed, n_draws, protocol["id"], data_hash(fits), code_hash)
    if dirty or head == db.UNKNOWN_HEAD:
        print(f"WARNING: {'working tree has uncommitted changes' if dirty else 'code revision unknown'};"
              f" run {run_id} stores code_hash {code_hash} (commit, then re-run for a reproducible hash)")

    scenario_ids = []
    eff_rows = []
    for sid, draws in iter_scenario_draws(fits, seed, n_draws):
        scenario_ids.append(sid)
        metrics = scenario_metrics(draws)
        p_positive = float(np.mean(metrics["EVSI"] > draws["C"]))
        for metric in METRIC_NAMES:
            db.insert_result(con, run_id, sid, metric, summarize(metrics[metric]), p_positive)
        for name in db.PARAM_NAMES:
            db.insert_sensitivity(con, run_id, sid, name,
                                  spearman(draws[name], metrics["efficiency"]))
        eff_rows.append(metrics["efficiency"])

    p_top = rank_stability(np.vstack(eff_rows), top=TOP_N_STABILITY)
    for i, sid in enumerate(scenario_ids):
        db.insert_result(con, run_id, sid, "p_top10", {}, float(p_top[i]))
    con.commit()

    if not quiet:
        print_ranking(con, run_id)
        print(f"\nrun {run_id}: code_hash {code_hash}, data_hash {db.get_run(con, run_id)['data_hash']}"
              f" over {len(scenario_ids)} scenarios")
    return run_id


def print_ranking(con, run_id: int, limit: int = 30):
    rows = con.execute(
        "SELECT r.scenario_id, s.title, r.q05, r.q50, r.q95, r.p_positive"
        " FROM results r JOIN scenarios s ON s.id = r.scenario_id"
        " WHERE r.run_id=? AND r.metric='efficiency' ORDER BY r.q50 DESC LIMIT ?",
        (run_id, limit)).fetchall()
    print(f"\nRanking by median efficiency (EVSI/C), run {run_id}:")
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
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    run_id = run_mc(con, args.protocol, args.seed, args.draws, allow_dirty=args.allow_dirty)
    print(f"\nrun {run_id} complete: study={study.name} protocol={args.protocol} "
          f"seed={args.seed} draws={args.draws}")


if __name__ == "__main__":
    main()
