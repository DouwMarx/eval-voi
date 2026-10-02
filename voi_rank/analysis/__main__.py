"""Write every figure, table and macro of a stored run into
<study>/report/generated/ (generated/<tag>/ with --tag, whose macros read
\\voi<tag>...), plus summary.json (the numbers, machine-readable).

Usage: uv run python -m voi_rank.analysis --study studies/safety-evals --protocol p001
       [--members a:b,c:d] [--tag NAME] [--draws N] [--decision-from p002 [--optional]]

--members selects the latest run of the protocol that pooled exactly that
subset. --draws keeps the first N of the run's draws after verification.
--decision-from takes p, B, K from another protocol's decision stage
(summary module docstring). --optional skips with a message instead of an
error when the analysed protocol has no stored run, or when --decision-from
names a protocol that is not registered or has no valid decision
elicitations (scripts/regen.sh uses it for ablations that may not exist yet).
"""

from __future__ import annotations

import argparse
import re

from voi_rank import db
from voi_rank.analysis import figures, macros, summary, tables
from voi_rank.study import Study, add_study_arg


def output_dir(study: Study, tag: str | None):
    out = study.generated_dir / tag if tag else study.generated_dir
    out.mkdir(parents=True, exist_ok=True)
    return out


def has_run(con, name: str) -> bool:
    row = con.execute("SELECT id FROM protocols WHERE name=?", (name,)).fetchone()
    return row is not None and con.execute("SELECT COUNT(*) FROM runs WHERE protocol_id=?",
                                           (row["id"],)).fetchone()[0] > 0


def has_decision_rows(con, name: str) -> bool:
    row = con.execute("SELECT id, stages_json FROM protocols WHERE name=?", (name,)).fetchone()
    if row is None or not row["stages_json"]:
        return False
    stage = db.group_stage(db.protocol_stages(row))["name"]
    return con.execute("SELECT COUNT(*) FROM elicitations WHERE protocol_id=? AND valid=1 AND stage=?",
                       (row["id"], stage)).fetchone()[0] > 0


def run(study: Study, protocol: str, members=None, tag=None, draws=None, decision_from=None) -> list:
    """Load, verify and write every output; returns the paths written."""
    con = study.connect_copy()   # read-only: the analysis never writes the study DB
    # seed the copy, so a scenario that left scenarios.json is retired here even when no
    # elicitation or MC run has seeded the real DB since (a run that holds it is refused)
    db.seed_scenarios(con, study.scenarios_json, dry_run=True)
    s = summary.load(con, protocol, members=members, draws=draws, decision_from=decision_from)
    out = output_dir(study, tag)
    paths = figures.write_all(s, out) + tables.write_all(s, out) + [macros.write(s, out, tag)]
    path = out / "summary.json"
    path.write_text(summary.to_json(s))
    return [*paths, path]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    ap.add_argument("--protocol", required=True, help="the protocol whose latest run is analysed")
    ap.add_argument("--members", default=None, help="comma-separated provider:model subset of the run")
    ap.add_argument("--tag", default=None, help="write to generated/TAG/ with macros \\voiTAG... (letters)")
    ap.add_argument("--draws", type=int, default=None, help="keep the first N draws (default: all)")
    ap.add_argument("--decision-from", default=None, help="protocol whose decision stage supplies p, B, K")
    ap.add_argument("--optional", action="store_true",
                    help="skip quietly when the protocol has no stored run (or --decision-from has no"
                         " valid decision elicitations)")
    args = ap.parse_args(argv)
    if args.tag and not re.fullmatch(r"[A-Za-z]+", args.tag):
        raise SystemExit(f"--tag {args.tag!r}: letters only (it becomes part of LaTeX macro names)")
    study = Study.resolve(args.study)
    if args.optional and not has_run(study.connect_copy(), args.protocol):
        print(f"skipped: protocol {args.protocol} has no stored Monte Carlo run in {study.db}")
        return
    if (args.decision_from and args.optional
            and not has_decision_rows(study.connect_copy(), args.decision_from)):
        print(f"skipped: protocol {args.decision_from} has no valid decision elicitations in {study.db}")
        return
    try:
        paths = run(study, args.protocol, db.parse_member_labels(args.members), args.tag, args.draws,
                    args.decision_from)
    except RuntimeError as ex:
        raise SystemExit(str(ex)) from None
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
