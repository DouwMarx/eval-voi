"""Health checks for the iteration protocol (spec §10) and cross-protocol
rank comparison. Reads only from voi.db.

Usage:
  python -m analysis.health --protocol p001
  python -m analysis.health --protocol p002 --compare p001
"""

from __future__ import annotations

import argparse
import random

import numpy as np
from scipy import stats

from core.sensitivity import repeat_spread
from db import io

EVSI_ZERO_USD = 1e-6  # "median EVSI ~ 0" threshold, in USD


def error_class(error: str | None) -> str:
    if error is None:
        return "valid"
    return error.split(":", 1)[0]  # cli | json | schema | constraint | fit


def health(con, protocol_name: str):
    prot = io.protocol_by_name(con, protocol_name)
    rows = con.execute("SELECT * FROM elicitations WHERE protocol_id=?",
                       (prot["id"],)).fetchall()
    if not rows:
        print(f"no elicitations under {protocol_name}")
        return

    print(f"=== health: protocol {protocol_name} ({len(rows)} attempts) ===")
    classes = {}
    for r in rows:
        classes[error_class(r["error"])] = classes.get(error_class(r["error"]), 0) + 1
    n = len(rows)
    json_ok = n - classes.get("cli", 0) - classes.get("json", 0) - classes.get("schema", 0)
    print(f"attempt counts by outcome: {classes}")
    print(f"JSON validity rate (parse+schema): {json_ok}/{n} = {json_ok/n:.1%} (target >= 95%)")
    parsed = json_ok
    passed = classes.get("valid", 0)
    if parsed:
        print(f"constraint pass rate (of parsed): {passed}/{parsed} = {passed/parsed:.1%}")

    # slot-level validity: fraction of (scenario, repeat) slots that ended valid
    slots = con.execute(
        "SELECT COUNT(DISTINCT scenario_id || '/' || repeat_ix),"
        " COUNT(DISTINCT CASE WHEN valid=1 THEN scenario_id || '/' || repeat_ix END)"
        " FROM elicitations WHERE protocol_id=?", (prot["id"],)).fetchone()
    print(f"slot validity (after retry): {slots[1]}/{slots[0]} = {slots[1]/slots[0]:.1%}")

    # cross-repeat spread of p50 per parameter (median over scenarios)
    print("\ncross-repeat p50 spread ((max-min)/pooled p50), median over scenarios:")
    for name in io.PARAM_NAMES:
        spreads = []
        for (sid,) in con.execute(
                "SELECT DISTINCT scenario_id FROM elicitations WHERE protocol_id=? AND valid=1",
                (prot["id"],)):
            p50s = [r[0] for r in con.execute(
                "SELECT p.p50 FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
                " WHERE e.scenario_id=? AND e.protocol_id=? AND e.valid=1 AND p.name=?",
                (sid, prot["id"], name))]
            sp = repeat_spread(p50s)
            if sp is not None:
                spreads.append(sp)
        med = float(np.median(spreads)) if spreads else float("nan")
        print(f"  {name}: {med:.3f}  (n={len(spreads)} scenarios)")

    # fit warnings
    fw = con.execute(
        "SELECT COUNT(*) FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=? AND p.fit_warning=1", (prot["id"],)).fetchone()[0]
    print(f"\nfit warnings: {fw}")

    # fraction of scenarios with median EVSI ~ 0, from the latest run
    try:
        run = io.latest_run(con, protocol_name)
        evsi = con.execute(
            "SELECT q50 FROM results WHERE run_id=? AND metric='EVSI'",
            (run["id"],)).fetchall()
        zero = sum(1 for r in evsi if r["q50"] is not None and r["q50"] < EVSI_ZERO_USD)
        print(f"scenarios with median EVSI ~ 0 (run {run['id']}): {zero}/{len(evsi)}")
    except RuntimeError:
        print("no MC run yet under this protocol")

    # spot-read sample of reasoning strings (seeded for reproducibility)
    sample = con.execute(
        "SELECT s.title, p.name, p.p50, p.unit, p.reasoning FROM parameters p"
        " JOIN elicitations e ON e.id=p.elicitation_id"
        " JOIN scenarios s ON s.id=e.scenario_id"
        " WHERE e.protocol_id=? AND e.valid=1", (prot["id"],)).fetchall()
    if sample:
        rnd = random.Random(0)
        print("\n5 sample reasoning strings (spot-read for unit errors):")
        for r in rnd.sample(sample, min(5, len(sample))):
            print(f"- [{r['title'][:40]}] {r['name']}={r['p50']} {r['unit']}: {r['reasoning'][:200]}")


def compare(con, protocol_a: str, protocol_b: str):
    """Spearman rank correlation of median efficiency between the latest runs
    of two protocols, over shared scenarios."""
    med = {}
    for name in (protocol_a, protocol_b):
        run = io.latest_run(con, name)
        med[name] = {r["scenario_id"]: r["q50"] for r in con.execute(
            "SELECT scenario_id, q50 FROM results WHERE run_id=? AND metric='efficiency'",
            (run["id"],))}
    shared = sorted(set(med[protocol_a]) & set(med[protocol_b]))
    if len(shared) < 3:
        print(f"compare: only {len(shared)} shared scenarios, skipping")
        return
    a = [med[protocol_a][s] for s in shared]
    b = [med[protocol_b][s] for s in shared]
    rho = stats.spearmanr(a, b).statistic
    print(f"\n=== rank correlation {protocol_a} vs {protocol_b} ===")
    print(f"Spearman rho of median efficiency over {len(shared)} shared scenarios: {rho:.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(io.DEFAULT_DB))
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--compare", default=None, help="second protocol to compare against")
    args = ap.parse_args()
    con = io.connect(args.db)
    health(con, args.protocol)
    if args.compare:
        compare(con, args.protocol, args.compare)


if __name__ == "__main__":
    main()
