"""Monte Carlo over elicitation uncertainty (spec §4).

All seven parameters are drawn independently (stated v1 assumption). When a
scenario has k valid repeats under a protocol, each parameter is drawn from an
equal-weight mixture over the k fitted distributions, so cross-repeat
elicitation noise propagates into the metric intervals.

Usage: python -m core.mc --protocol p001 [--seed 42] [--draws 100000]
"""

from __future__ import annotations

import argparse

import numpy as np

from core import model
from core.sensitivity import rank_stability, spearman
from db import io

METRIC_NAMES = ["EVSI", "EVPI", "efficiency", "margin", "headroom"]
SUMMARY_QS = (0.05, 0.25, 0.50, 0.75, 0.95)
TOP_N_STABILITY = 10


def _draw(rng, family: str, params: dict, m: int) -> np.ndarray:
    if family == "lognormal":
        return rng.lognormal(params["mu"], params["sigma"], m)
    if family == "beta":
        return rng.beta(params["alpha"], params["beta"], m)
    raise ValueError(f"unknown family {family!r}")


def sample_mixture(rng, fits: list[dict], m: int) -> np.ndarray:
    """Equal-weight mixture over the fitted distributions of the valid repeats."""
    if len(fits) == 1:
        return _draw(rng, fits[0]["family"], fits[0]["params"], m)
    idx = rng.integers(0, len(fits), size=m)
    out = np.empty(m)
    for r, f in enumerate(fits):
        mask = idx == r
        out[mask] = _draw(rng, f["family"], f["params"], int(mask.sum()))
    return out


def scenario_metrics(draws: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    evsi, evpi = model.voi(draws["p"], draws["s"], draws["t"], draws["e"],
                           draws["B"], draws["K"])
    C = draws["C"]
    headroom = np.where(evpi > 0.0, evsi / np.where(evpi > 0.0, evpi, 1.0), np.nan)
    return {
        "EVSI": evsi,
        "EVPI": evpi,
        "efficiency": evsi / C,
        "margin": evsi - C,
        "headroom": headroom,
    }


def summarize(vec: np.ndarray) -> dict:
    finite = vec[~np.isnan(vec)]
    if finite.size == 0:
        return {q: None for q in SUMMARY_QS}
    qs = np.quantile(finite, SUMMARY_QS)
    return dict(zip(SUMMARY_QS, (float(v) for v in qs)))


def iter_scenario_draws(con, protocol_id: int, seed: int, n_draws: int):
    """Deterministic generator of (scenario_id, draws dict) for every scenario
    with a complete set of valid elicitations under the protocol. The rng
    stream is consumed in sorted-scenario-id, PARAM_NAMES order, so a replay
    with the same DB state reproduces the run's draws exactly."""
    fits_by_scenario = io.scenario_param_fits(con, protocol_id)
    complete = {
        sid: fits for sid, fits in sorted(fits_by_scenario.items())
        if all(name in fits for name in io.PARAM_NAMES)
    }
    rng = np.random.default_rng(seed)
    for sid, fits in complete.items():
        yield sid, {name: sample_mixture(rng, fits[name], n_draws)
                    for name in io.PARAM_NAMES}


def replay_efficiency(con, run_id: int):
    """Recompute the efficiency draw matrix of a stored run from the DB alone
    (seed, n_draws and fitted params are all persisted). Guards against the
    valid-elicitation set having changed since the run."""
    run = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if run is None:
        raise RuntimeError(f"no run {run_id}")
    ids, effs = [], []
    for sid, draws in iter_scenario_draws(con, run["protocol_id"], run["seed"],
                                          run["n_draws"]):
        ids.append(sid)
        effs.append(scenario_metrics(draws)["efficiency"])
    stored = {r[0] for r in con.execute(
        "SELECT DISTINCT scenario_id FROM results WHERE run_id=?", (run_id,))}
    if set(ids) != stored:
        raise RuntimeError(
            f"run {run_id} replay mismatch: elicitations changed since the run "
            f"({len(ids)} scenarios now vs {len(stored)} stored)")
    return ids, np.vstack(effs)


def run_mc(con, protocol_name: str, seed: int, n_draws: int, quiet: bool = False) -> int:
    """Execute one MC run over all scenarios with valid elicitations under the
    protocol. Writes runs, results (incl. a p_top10 stability row per scenario)
    and sensitivities. Returns the run id."""
    protocol = io.protocol_by_name(con, protocol_name)
    fits = io.scenario_param_fits(con, protocol["id"])
    if not any(all(n in f for n in io.PARAM_NAMES) for f in fits.values()):
        raise RuntimeError(f"no scenarios with complete valid elicitations under {protocol_name}")
    run_id = io.insert_run(con, seed, n_draws, protocol["id"])

    scenario_ids = []
    eff_rows = []
    for sid, draws in iter_scenario_draws(con, protocol["id"], seed, n_draws):
        scenario_ids.append(sid)
        metrics = scenario_metrics(draws)
        p_positive = float(np.mean(metrics["EVSI"] > draws["C"]))
        for metric in METRIC_NAMES:
            io.insert_result(con, run_id, sid, metric, summarize(metrics[metric]), p_positive)
        for name in io.PARAM_NAMES:
            io.insert_sensitivity(con, run_id, sid, name,
                                  spearman(draws[name], metrics["efficiency"]))
        eff_rows.append(metrics["efficiency"])

    p_top = rank_stability(np.vstack(eff_rows), top=TOP_N_STABILITY)
    for i, sid in enumerate(scenario_ids):
        io.insert_result(con, run_id, sid, "p_top10", {}, float(p_top[i]))
    con.commit()

    if not quiet:
        print_ranking(con, run_id)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(io.DEFAULT_DB))
    ap.add_argument("--protocol", required=True, help="protocol name, e.g. p001")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--draws", type=int, default=100_000)
    args = ap.parse_args()
    con = io.connect(args.db)
    run_id = run_mc(con, args.protocol, args.seed, args.draws)
    print(f"\nrun {run_id} complete: protocol={args.protocol} seed={args.seed} draws={args.draws}")


if __name__ == "__main__":
    main()
