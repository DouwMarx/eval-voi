"""Delete stored MC runs (their runs, results and sensitivities rows) from a
study's voi.db and VACUUM, e.g. runs whose provenance is wrong (made from an
uncommitted tree but stamped with the clean HEAD hash). Elicitations and
parameters are never touched; a deleted run is re-made by voi_rank.mc.

Prints every run with its protocol, code hash and row counts, then asks for
confirmation on a TTY unless --yes.

Usage: python -m voi_rank.drop_runs --study studies/business --runs 9-13 [--yes]
       (--runs takes ids and ranges: 9-13, 3,7, 9-11,13)
"""

from __future__ import annotations

import argparse

from voi_rank import db
from voi_rank.elicit import confirm_interactively
from voi_rank.study import Study, add_study_arg


def parse_runs(spec: str) -> list[int]:
    """'9-13' | '3,7' | '9-11,13' -> sorted distinct ids."""
    ids: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            if hi < lo:
                raise argparse.ArgumentTypeError(f"empty range {part!r}")
            ids.update(range(lo, hi + 1))
        else:
            ids.add(int(part))
    if not ids:
        raise argparse.ArgumentTypeError(f"no run ids in {spec!r}")
    return sorted(ids)


def describe_runs(con, run_ids: list[int]) -> list[dict]:
    """One dict per run (id, protocol, code_hash, data_hash, results,
    sensitivities); an id that is not a run is an error."""
    out = []
    for rid in run_ids:
        run = db.get_run(con, rid)
        prot = con.execute("SELECT name FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
        out.append({
            "id": rid, "protocol": prot["name"] if prot else "unknown",
            "code_hash": run["code_hash"], "data_hash": run["data_hash"],
            "results": con.execute("SELECT COUNT(*) FROM results WHERE run_id=?", (rid,)).fetchone()[0],
            "sensitivities": con.execute("SELECT COUNT(*) FROM sensitivities WHERE run_id=?",
                                         (rid,)).fetchone()[0],
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    ap.add_argument("--runs", type=parse_runs, required=True, help="run ids, e.g. 9-13 or 3,7")
    ap.add_argument("--yes", action="store_true", help="delete without the interactive confirmation")
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    con = study.connect()
    rows = describe_runs(con, args.runs)
    print(f"runs to delete from {study.db}:")
    for r in rows:
        print(f"  run {r['id']} ({r['protocol']}): code_hash {r['code_hash']}, data_hash"
              f" {r['data_hash'] or 'NULL'}, {r['results']} results rows, {r['sensitivities']}"
              " sensitivities rows")
    if not args.yes and not confirm_interactively("delete these runs? [y/N] "):
        raise SystemExit("nothing deleted: pass --yes, or confirm at the prompt on a TTY")
    counts = db.drop_runs(con, args.runs)
    left = [r[0] for r in con.execute("SELECT id FROM runs ORDER BY id")]
    print(f"deleted {counts['runs']} runs, {counts['results']} results rows,"
          f" {counts['sensitivities']} sensitivities rows; VACUUM done; runs left: {left}")


if __name__ == "__main__":
    main()
