"""Health checks for the iteration protocol (spec §10), per-member checks for
ensembles, and cross-protocol rank comparison. Reads only from a study's
voi.db.

Usage:
  python -m voi_rank.analysis.health --study studies/business --protocol p001
  python -m voi_rank.analysis.health --study studies/business --protocol p002 --compare p001
  python -m voi_rank.analysis.health --study studies/X --protocol p003 \
      --members claude_cli:sonnet,claude_cli:opus
    (--members restricts the per-member tables, the pooled spread and the
    cross-member agreement to that subset and reads the subset's latest run;
    --compare correlates that run with the other protocol's all-member run)
"""

from __future__ import annotations

import argparse
import random

import numpy as np
from scipy import stats

from voi_rank import db
from voi_rank.sensitivity import spearman
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


def noise_table(con, protocol_id: int, member: dict | None = None,
                members: list[str] | None = None) -> dict[str, tuple]:
    """{param: (median spread, n scenarios)} over valid elicitations, all
    members pooled, a subset (`members`, labels) or one member; the spread is
    db.elicited_spread (relative, or max - min in sd units for the signed
    Gaussian quantities)."""
    out = {}
    for name in protocol_names(con, protocol_id):
        spreads = []
        # the scenarios carrying the parameter: the group representatives for
        # a decision-stage parameter of a staged protocol (one spread per group)
        for sid in db.param_scenario_ids(con, protocol_id, name, members):
            sp = db.elicited_spread(con, protocol_id, sid, name,
                                    provider=member["provider"] if member else None,
                                    model=member["model"] if member else None, members=members)
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


def cross_member_agreement(con, protocol_id: int, members: list[dict],
                           names: list[str] | None = None) -> list[tuple]:
    """Spearman of per-scenario pooled p50 between every member pair, per
    parameter (`names`, default all of the protocol's), over shared
    scenarios. Returns (param, a, b, rho, n) rows."""
    rows = []
    for name in names if names is not None else protocol_names(con, protocol_id):
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


def decision_level_agreement(con, protocol_id: int, members: list[dict],
                             stages: list[dict]) -> list[tuple]:
    """Staged protocols: the decision-stage numbers per group and member.
    Returns (param, group, {member label: pooled p50}, cross-member spread)
    rows, the spread being (max - min) / median of the members' pooled p50
    (None with one member). Across the rungs of a group the decision-stage
    spread is zero by construction (one elicitation per group), so this
    per-group agreement is the consistency number of a staged protocol."""
    gstage = db.group_stage(stages)
    rows = []
    groups = db.scenario_groups_by_key(con, gstage["group_key"])
    for name in gstage["params"]:
        for value, sids in sorted(groups.items()):
            pooled = {}
            for m in members:
                p50s = db.elicited_p50s(con, protocol_id, sids[0], name, m["provider"], m["model"])
                if p50s:
                    pooled[db.member_label(m)] = float(np.median(p50s))
            if not pooled:
                continue
            vals = np.array(list(pooled.values()))
            med = float(np.median(vals))
            spread = float((vals.max() - vals.min()) / med) if len(vals) > 1 and med else None
            rows.append((name, value, pooled, spread))
    return rows


def health(con, protocol_name: str, members: list[str] | None = None):
    """The protocol's health checks; `members` (labels) restricts every
    count and table to that subset (a label the protocol does not list
    exits): the attempts by outcome, JSON validity, constraint pass rate and
    slot validity included, so a restricted print is never read as the
    subset's validity when it is every member's; and it reads the subset's
    latest run. A staged protocol gets per-stage validity and spreads (the
    decision stage's over groups) and, since its decision-stage spread across
    rungs is zero by construction, the cross-member decision-level agreement
    per group in place of a per-scenario Spearman on p, B, K."""
    prot = db.protocol_by_name(con, protocol_name)
    all_members = db.protocol_members(prot)
    try:
        labels = db.normalize_run_members(all_members, members)
    except ValueError as ex:
        raise SystemExit(f"--members: {ex}") from None
    members = all_members if labels is None else [m for m in all_members if db.member_label(m) in labels]
    clause, margs = db.member_filter(labels)   # every count below is over the subset's attempts
    rows = con.execute(f"SELECT * FROM elicitations e WHERE protocol_id=?{clause}",
                       (prot["id"], *margs)).fetchall()
    if not rows:
        print(f"no elicitations under {protocol_name}"
              + (f" by {db.members_label(labels)}" if labels else ""))
        return

    print(f"=== health: protocol {protocol_name} ({len(rows)} attempts, "
          f"{len(all_members)} member(s)"
          + (f"; members restricted to {db.members_label(labels)}" if labels else "") + ") ===")
    if labels:
        print("(every count below is over the attempts of the members listed)")
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

    # slot-level validity: fraction of (scenario, member, repeat, stage) slots that ended
    # valid (the stage keeps a decision and an instrument slot of one member and repeat
    # apart on a representative, as the unique valid-slot index does)
    slot_key = ("scenario_id || '/' || provider || '/' || model || '/' || repeat_ix || '/' ||"
                " COALESCE(stage, '')")
    slots = con.execute(
        f"SELECT COUNT(DISTINCT {slot_key}), COUNT(DISTINCT CASE WHEN valid=1 THEN {slot_key} END)"
        f" FROM elicitations e WHERE protocol_id=?{clause}", (prot["id"], *margs)).fetchone()
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

    # staged protocols: validity per stage and member
    stages = db.protocol_stages(prot)
    if stages is not None:
        print("\nper stage: attempts, valid, validity ("
              + ("the members listed" if labels else "all members") + "; then per member)")
        for st in stages:
            sr = [r for r in rows if r["stage"] == st["name"]]
            valid = sum(int(r["valid"] or 0) for r in sr)
            unit = "groups" if "group_key" in st else "scenarios"
            n_units = len({r["scenario_id"] for r in sr if r["valid"]})
            head = f"  stage {st['name']} (params {', '.join(st['params'])}):"
            print(f"{head} {len(sr)} attempts, {valid} valid ({valid/len(sr):.1%}), {n_units} {unit}"
                  " with a valid answer" if sr else f"{head} no attempts")
            for m in members:
                mr = [r for r in sr if r["provider"] == m["provider"] and r["model"] == m["model"]]
                mv = sum(int(r["valid"] or 0) for r in mr)
                print(f"    {db.member_label(m)}: {len(mr)} attempts, {mv} valid"
                      + (f" ({mv/len(mr):.1%})" if mr else ""))

    # cross-elicitation spread of p50 per parameter (median over scenarios; over
    # groups for the decision-stage parameters of a staged protocol)
    spread_of = noise_table(con, prot["id"], members=labels)
    print("\ncross-elicitation p50 spread ((max-min)/pooled p50 unless marked), median over scenarios"
          + (f" (members {db.members_label(labels)})" if labels else "")
          + ("; the decision-stage parameters over groups" if stages else "") + ":")
    for name, (med, cnt) in spread_of.items():
        stage = db.stage_of_param(stages, name)
        unit = "groups" if stage and "group_key" in stage else "scenarios"
        print(f"  {name}{db.spread_label(name)}: {med:.3f}  (n={cnt} {unit})"
              + (f"  [stage {stage['name']}]" if stage else ""))
    if len(members) > 1:
        print("\nper-member cross-repeat p50 spread (median over scenarios):")
        for m in members:
            cells = "  ".join(f"{name} {med:.2f}" for name, (med, _) in
                              noise_table(con, prot["id"], m).items())
            print(f"  {db.member_label(m)}: {cells}")
        scen_names = None if stages is None else db.scenario_stage(stages)["params"]
        print("\ncross-member agreement: Spearman of per-scenario pooled p50 over shared scenarios"
              + (f" ({', '.join(scen_names)}; the decision stage is per group, below)" if stages else "")
              + ":")
        for name, a, b, rho, cnt in cross_member_agreement(con, prot["id"], members, scen_names):
            print(f"  {name}: {a} vs {b}: rho={rho:.3f} (n={cnt})")
    if stages is not None:
        print("\ndecision-level agreement across members (the decision-stage spread across the rungs"
              " of a group is 0 by construction): per group, pooled p50 per member and"
              " (max - min) / median across members:")
        for name, value, pooled, spread in decision_level_agreement(con, prot["id"], members, stages):
            cells = "  ".join(f"{lab} {v:.3g}" for lab, v in pooled.items())
            print(f"  {name} [{value}]: {cells}  spread={'n/a' if spread is None else f'{spread:.2f}'}")

    # fit warnings (for a Gaussian protocol: over-determination residuals past their thresholds)
    names = protocol_names(con, prot["id"])
    fw = con.execute(
        "SELECT COUNT(*) FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=? AND p.fit_warning=1 AND p.name IN"
        f" ({','.join('?' * len(names))}){clause}", (prot["id"], *names, *margs)).fetchone()[0]
    print(f"\nfit warnings: {fw}")

    # fraction of scenarios with median EVSI ~ 0, from the latest run (of the subset)
    try:
        run = db.latest_run(con, protocol_name, labels)
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
        f" WHERE e.protocol_id=? AND e.valid=1{clause}", (prot["id"], *margs)).fetchall()
    if sample:
        rnd = random.Random(0)
        print("\n5 sample reasoning strings (spot-read for unit errors):")
        for r in rnd.sample(sample, min(5, len(sample))):
            print(f"- [{r['title'][:40]}] {r['name']}={r['p50']} {r['unit']}: {r['reasoning'][:200]}")


def compare(con, protocol_a: str, protocol_b: str, members: list[str] | None = None):
    """Spearman rank correlation of median efficiency between the latest runs
    of two protocols, over shared scenarios (`members`: the subset run of
    protocol_a; protocol_b's all-member run)."""
    med = {}
    for name in (protocol_a, protocol_b):
        run = db.latest_run(con, name, members if name == protocol_a else None)
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
    rho = spearman(a, b)   # None when a ranking is constant (e.g. every median EVSI 0)
    print(f"\n=== rank correlation {protocol_a} vs {protocol_b} ===")
    print(f"Spearman rho of median efficiency over {len(shared)} shared scenarios: "
          + ("n/a (a constant ranking)" if rho is None else f"{rho:.3f}"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    add_study_arg(ap)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--compare", default=None, help="second protocol to compare against")
    ap.add_argument("--members", default=None,
                    help="comma-separated provider:model subset of the protocol's members")
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    members = db.parse_member_labels(args.members)
    health(con, args.protocol, members)
    if args.compare:
        compare(con, args.protocol, args.compare, members)


if __name__ == "__main__":
    main()
