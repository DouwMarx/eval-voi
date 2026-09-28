"""Health checks for the iteration protocol (spec §10), per-member checks for
ensembles, and cross-protocol rank comparison. Reads only from a study's
voi.db.

Usage:
  python -m voi_rank.analysis.health --study studies/business --protocol p001
  python -m voi_rank.analysis.health --study studies/business --protocol p002 --compare p001
"""

from __future__ import annotations

import argparse
import random

import numpy as np
from scipy import stats

from voi_rank import db
from voi_rank.study import Study, add_study_arg

EVSI_ZERO_USD = 1e-6  # "median EVSI ~ 0" threshold, in USD


def error_class(error: str | None) -> str:
    if error is None:
        return "valid"
    return error.split(":", 1)[0]  # provider | cli | http | api | json | schema | constraint | fit


def protocol_names(con, protocol_id: int) -> list[str]:
    """The parameter rows a protocol stores (its model kind's names)."""
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()
    return db.param_names(db.protocol_model_kind(prot))


def noise_table(con, protocol_id: int, member: dict | None = None) -> dict[str, tuple]:
    """{param: (median spread, n scenarios)} over valid elicitations, all
    members pooled or one member; the spread is db.elicited_spread (relative,
    or max - min in sd units for the signed Gaussian quantities)."""
    sids = [r[0] for r in con.execute(
        "SELECT DISTINCT scenario_id FROM elicitations WHERE protocol_id=? AND valid=1",
        (protocol_id,))]
    out = {}
    for name in protocol_names(con, protocol_id):
        spreads = []
        for sid in sids:
            sp = db.elicited_spread(con, protocol_id, sid, name,
                                    provider=member["provider"] if member else None,
                                    model=member["model"] if member else None)
            if sp is not None:
                spreads.append(sp)
        out[name] = (float(np.median(spreads)) if spreads else float("nan"), len(spreads))
    return out


def member_pooled_p50(con, protocol_id: int, member: dict, name: str) -> dict[int, float]:
    """{scenario_id: median p50 over one member's valid repeats}."""
    out = {}
    for (sid,) in con.execute(
            "SELECT DISTINCT scenario_id FROM elicitations WHERE protocol_id=? AND valid=1"
            " AND provider=? AND model=?", (protocol_id, member["provider"], member["model"])):
        p50s = db.elicited_p50s(con, protocol_id, sid, name, member["provider"], member["model"])
        if p50s:
            out[sid] = float(np.median(p50s))
    return out


def cross_member_agreement(con, protocol_id: int, members: list[dict]) -> list[tuple]:
    """Spearman of per-scenario pooled p50 between every member pair, per
    parameter, over shared scenarios. Returns (param, a, b, rho, n) rows."""
    rows = []
    for name in protocol_names(con, protocol_id):
        pooled = {db.member_label(m): member_pooled_p50(con, protocol_id, m, name)
                  for m in members}
        labels = list(pooled)
        for i, a in enumerate(labels):
            for b in labels[i + 1:]:
                shared = sorted(set(pooled[a]) & set(pooled[b]))
                if len(shared) < 3:
                    rows.append((name, a, b, float("nan"), len(shared)))
                    continue
                rho = stats.spearmanr([pooled[a][s] for s in shared],
                                      [pooled[b][s] for s in shared]).statistic
                rows.append((name, a, b, float(rho), len(shared)))
    return rows


def health(con, protocol_name: str):
    prot = db.protocol_by_name(con, protocol_name)
    members = db.protocol_members(prot)
    rows = con.execute("SELECT * FROM elicitations WHERE protocol_id=?",
                       (prot["id"],)).fetchall()
    if not rows:
        print(f"no elicitations under {protocol_name}")
        return

    print(f"=== health: protocol {protocol_name} ({len(rows)} attempts, "
          f"{len(members)} member(s)) ===")
    classes = {}
    for r in rows:
        classes[error_class(r["error"])] = classes.get(error_class(r["error"]), 0) + 1
    n = len(rows)
    json_ok = n - sum(classes.get(c, 0) for c in ("provider", "cli", "http", "api", "json", "schema"))
    print(f"attempt counts by outcome: {classes}")
    print(f"JSON validity rate (parse+schema): {json_ok}/{n} = {json_ok/n:.1%} (target >= 95%)")
    passed = classes.get("valid", 0)
    if json_ok:
        print(f"constraint pass rate (of parsed): {passed}/{json_ok} = {passed/json_ok:.1%}")

    # slot-level validity: fraction of (scenario, member, repeat) slots that ended valid
    slots = con.execute(
        "SELECT COUNT(DISTINCT scenario_id || '/' || provider || '/' || model || '/' || repeat_ix),"
        " COUNT(DISTINCT CASE WHEN valid=1 THEN"
        "   scenario_id || '/' || provider || '/' || model || '/' || repeat_ix END)"
        " FROM elicitations WHERE protocol_id=?", (prot["id"],)).fetchone()
    print(f"slot validity (after retry): {slots[1]}/{slots[0]} = {slots[1]/slots[0]:.1%}")

    # per-member validity and cost
    print("\nper member (provider:model): attempts, valid, validity, cost USD")
    for m in members:
        mr = [r for r in rows if r["provider"] == m["provider"] and r["model"] == m["model"]]
        valid = sum(int(r["valid"] or 0) for r in mr)
        cost = sum(db.envelope_cost(r["raw_response"]) for r in mr)
        rate = f"{valid/len(mr):.1%}" if mr else "n/a"
        print(f"  {db.member_label(m)} (k={m['k_repeats']}): {len(mr)} attempts, "
              f"{valid} valid ({rate}), ${cost:.2f}")

    # cross-elicitation spread of p50 per parameter (median over scenarios)
    print("\ncross-elicitation p50 spread ((max-min)/pooled p50 unless marked), median over scenarios:")
    for name, (med, cnt) in noise_table(con, prot["id"]).items():
        print(f"  {name}{db.spread_label(name)}: {med:.3f}  (n={cnt} scenarios)")
    if len(members) > 1:
        print("\nper-member cross-repeat p50 spread (median over scenarios):")
        for m in members:
            cells = "  ".join(f"{name} {med:.2f}" for name, (med, _) in
                              noise_table(con, prot["id"], m).items())
            print(f"  {db.member_label(m)}: {cells}")
        print("\ncross-member agreement: Spearman of per-scenario pooled p50 over shared scenarios:")
        for name, a, b, rho, cnt in cross_member_agreement(con, prot["id"], members):
            print(f"  {name}: {a} vs {b}: rho={rho:.3f} (n={cnt})")

    # fit warnings (for a Gaussian protocol: over-determination residuals past their thresholds)
    names = protocol_names(con, prot["id"])
    fw = con.execute(
        "SELECT COUNT(*) FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=? AND p.fit_warning=1 AND p.name IN"
        f" ({','.join('?' * len(names))})", (prot["id"], *names)).fetchone()[0]
    print(f"\nfit warnings: {fw}")

    # fraction of scenarios with median EVSI ~ 0, from the latest run
    try:
        run = db.latest_run(con, protocol_name)
        evsi_name = db.evsi_metric(db.protocol_model_kind(prot))
        evsi = con.execute(
            "SELECT q50 FROM results WHERE run_id=? AND metric=?",
            (run["id"], evsi_name)).fetchall()
        zero = sum(1 for r in evsi if r["q50"] is not None and r["q50"] < EVSI_ZERO_USD)
        print(f"scenarios with median {evsi_name} ~ 0 (run {run['id']}): {zero}/{len(evsi)}")
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
        run = db.latest_run(con, name)
        metric = db.primary_metric(db.run_model_kind(con, run))   # each run's own efficiency
        med[name] = {r["scenario_id"]: r["q50"] for r in con.execute(
            "SELECT scenario_id, q50 FROM results WHERE run_id=? AND metric=?",
            (run["id"], metric))}
    shared = sorted(set(med[protocol_a]) & set(med[protocol_b]))
    if len(shared) < 3:
        print(f"compare: only {len(shared)} shared scenarios, skipping")
        return
    a = [med[protocol_a][s] for s in shared]
    b = [med[protocol_b][s] for s in shared]
    rho = stats.spearmanr(a, b).statistic
    print(f"\n=== rank correlation {protocol_a} vs {protocol_b} ===")
    print(f"Spearman rho of median efficiency over {len(shared)} shared scenarios: {rho:.3f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    add_study_arg(ap)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--compare", default=None, help="second protocol to compare against")
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    health(con, args.protocol)
    if args.compare:
        compare(con, args.protocol, args.compare)


if __name__ == "__main__":
    main()
