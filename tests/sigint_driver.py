"""Subprocess driver for test_terminal_ctrl_c_reaches_only_the_harness: runs
elicit.run_jobs over four claude_cli slots with two workers in a process
group of its own, so the test can deliver SIGINT to that group the way a
terminal delivers Ctrl-C (os.killpg). The `claude` on PATH is the test's fake
(a shell script that records its start, sleeps and prints a valid envelope).
Exits 130 on KeyboardInterrupt, as the real harness does when re-raising it.

Usage: python tests/sigint_driver.py <study root>
"""

import sys
from pathlib import Path

from voi_rank import db, elicit
from voi_rank.study import Study


def main():
    study = Study.resolve(Path(sys.argv[1]))
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    pid = db.get_or_create_protocol(con, study.protocol_path("p001"), study.root)
    _, jobs = elicit.plan_jobs(con, study, pid, "1,2,3,4", 1, {"claude_cli:haiku"})
    print(f"driver: {len(jobs)} slots", flush=True)
    try:
        elicit.run_jobs(con, study, pid, jobs, workers=2)
    except KeyboardInterrupt:
        print("driver: KeyboardInterrupt re-raised", flush=True)
        sys.exit(130)
    print("driver: completed without interrupt", flush=True)


if __name__ == "__main__":
    main()
