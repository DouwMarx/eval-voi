"""Proposer: generate scenarios from seed domains (spec §6.5, §7) with the
claude_cli provider, into a study's voi.db.

No dedupe by design: scenario text is its identity; duplicates are acceptable.

A paid run prints its plan (domains x scenarios, calls, estimated cost from
the cost stored on earlier proposed scenarios) and needs --yes, or an
interactive confirmation on a TTY, before any call (same guard as elicit).
The plan is made on an in-memory copy of the study DB, so a declined plan or
--dry-run creates nothing, not even voi.db. Paid work is never discarded: on
Ctrl-C or any error in the main thread the pending domains are cancelled,
the running calls are awaited and their scenarios inserted, and the error is
re-raised (same rule as elicit.run_jobs).

Usage: python -m voi_rank.propose --study studies/business [--n 6] [--model haiku] [--workers 5]
       [--dry-run] --yes
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import string
from pathlib import Path

from voi_rank import db
from voi_rank.elicit import SYSTEM_PROMPT, confirm_interactively
from voi_rank.providers.claude_cli import call_claude
from voi_rank.study import Study, add_study_arg
from voi_rank.validate import strip_fences

DOMAINS = [
    "industrial injury categories",
    "agriculture",
    "construction",
    "medicine",
    "transport",
    "energy",
    "AI and robotics evaluation",
    "finance and credit",
    "environmental monitoring",
    "consumer durables",
]

REQUIRED_FIELDS = ["title", "agent", "decision", "theta_definition", "instrument"]
MAX_ATTEMPTS_PER_DOMAIN = 2
# each proposed scenario records its share of the call's cost here (in
# scenarios.attributes), which is what the plan's estimate is built from
COST_ATTR = "proposer_cost_usd"
# a paid domain the DB refuses during the salvage is appended here, never lost
UNSTORED_FILE = "propose_unstored.jsonl"


def propose_domain(template: string.Template, domain: str, n: int, model: str):
    """Returns (scenarios list, error | None, USD cost of every call made).
    One retry on failure; each returned scenario carries attributes.COST_ATTR
    = its share of the domain's cost."""
    prompt = template.substitute(domain=domain, n=n)
    last_err = None
    cost = 0.0
    for _ in range(MAX_ATTEMPTS_PER_DOMAIN):
        envelope, _raw, err = call_claude(prompt, model, SYSTEM_PROMPT)
        if envelope:
            cost += float(envelope.get("total_cost_usd") or 0.0)
        if err is not None:
            last_err = err
            continue
        try:
            items = json.loads(strip_fences(str(envelope.get("result", ""))))
        except json.JSONDecodeError as ex:
            last_err = f"json: {ex}"
            continue
        if not isinstance(items, list):
            last_err = "schema: not a JSON array"
            continue
        good = [it for it in items
                if isinstance(it, dict)
                and all(isinstance(it.get(f), str) and it[f].strip() for f in REQUIRED_FIELDS)]
        if good:
            for it in good:
                if not isinstance(it.get("domain_tags"), list):
                    it["domain_tags"] = [domain]
                attrs = it.get("attributes") if isinstance(it.get("attributes"), dict) else {}
                attrs[COST_ATTR] = cost / len(good)
                it["attributes"] = attrs
            return good, None, cost
        last_err = "schema: no valid scenario objects in array"
    return [], last_err, cost


def proposer_mean_cost(con) -> tuple[float, int] | None:
    """(mean recorded USD cost per proposed scenario, scenarios) over the
    proposer scenarios of the study that carry a cost; None without any."""
    costs = [db.scenario_attributes(r).get(COST_ATTR) for r in con.execute(
        "SELECT attributes FROM scenarios WHERE source LIKE 'proposer:%'")]
    costs = [float(c) for c in costs if c is not None]
    if not costs:
        return None
    return sum(costs) / len(costs), len(costs)


def print_plan(con, domains: list[str], n: int, model: str):
    """Scenarios and calls the run would make, and the estimated cost
    (scenarios x mean stored cost per proposed scenario, 'unknown' without
    history)."""
    print(f"plan: {len(domains)} domains x {n} scenarios = {len(domains) * n} scenarios, up to"
          f" {MAX_ATTEMPTS_PER_DOMAIN * len(domains)} claude_cli calls (model {model}; a failed"
          " call is retried once)")
    est = proposer_mean_cost(con)
    if est is None:
        print("  estimated cost unknown (no proposer scenarios with a stored cost in this study)")
    else:
        print(f"  estimated cost ${len(domains) * n * est[0]:.2f} (mean ${est[0]:.4f}/scenario over"
              f" {est[1]} stored proposer scenarios)")


def spill_domain(study_root: Path, domain: str, scenarios: list[dict], cost: float,
                 error: Exception) -> Path:
    """Append a paid domain's scenarios to <study>/propose_unstored.jsonl when
    the DB refuses them during the salvage."""
    path = Path(study_root) / UNSTORED_FILE
    record = {"spilled_at": db.now_iso(), "store_error": f"{type(error).__name__}: {error}",
              "domain": domain, "cost": cost, "scenarios": scenarios}
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
    return path


def run_domains(con, study_root: Path, template: string.Template, domains: list[str], n: int,
                model: str, workers: int) -> tuple[int, float]:
    """Propose every domain in a thread pool and insert each domain's
    scenarios (one transaction per domain) as its call completes. Returns
    (scenarios inserted, total cost). On any exception in this thread
    (Ctrl-C included) the pending domains are cancelled, the running calls
    are awaited and their scenarios inserted, and the exception is re-raised;
    a further Ctrl-C during that wait is ignored, and a domain the interrupt
    caught between its commit and its bookkeeping is recognised in the DB,
    not inserted twice. A domain the DB refuses during that salvage (e.g. a
    locked database) is appended to <study>/propose_unstored.jsonl and the
    salvage goes on with the next one, so one failed insert never hides the
    original error or discards another paid call."""
    last_id_before = con.execute("SELECT COALESCE(MAX(id), 0) FROM scenarios").fetchone()[0]
    pool = cf.ThreadPoolExecutor(workers)
    futures = {pool.submit(propose_domain, template, d, n, model): d for d in domains}
    handled: set = set()
    n_inserted, total_cost = 0, 0.0

    def inserted_by_this_run(domain: str) -> bool:
        return con.execute("SELECT 1 FROM scenarios WHERE id>? AND source=? LIMIT 1",
                           (last_id_before, f"proposer:{domain}")).fetchone() is not None

    def outcome(fut) -> tuple[list[dict], str | None, float]:
        try:
            return fut.result()
        except Exception as ex:   # a crashed job never stops the loop
            return [], f"provider: {type(ex).__name__}: {ex}", 0.0

    def insert(fut) -> None:
        nonlocal n_inserted, total_cost
        domain = futures[fut]
        scenarios, err, cost = outcome(fut)
        total_cost += cost
        if err:
            handled.add(fut)
            print(f"domain {domain!r}: FAILED ({err})")
            return
        con.rollback()
        for sc in scenarios:
            db.insert_scenario(con, sc, source=f"proposer:{domain}", commit=False)
        con.commit()
        handled.add(fut)
        n_inserted += len(scenarios)
        print(f"domain {domain!r}: inserted {len(scenarios)} (${cost:.4f})")

    def insert_or_spill(fut) -> None:
        """The salvage's insert: a DB error spills the domain and is reported
        instead of replacing the exception that stopped the run."""
        try:
            insert(fut)
        except Exception as ex:
            con.rollback()
            domain = futures[fut]
            scenarios, _err, cost = outcome(fut)
            path = spill_domain(study_root, domain, scenarios, cost, ex)
            handled.add(fut)
            print(f"domain {domain!r}: could not be stored ({type(ex).__name__}: {ex}); its"
                  f" {len(scenarios)} scenarios were appended to {path}")

    try:
        for fut in cf.as_completed(futures):
            if not fut.cancelled():
                insert(fut)
    except BaseException as ex:
        pending = sum(1 for f in futures if f.cancel())
        pool.shutdown(wait=False, cancel_futures=True)
        running = [f for f in futures if not f.done()]
        print(f"\ninterrupted ({type(ex).__name__}): {pending} pending domain(s) cancelled"
              + (f", waiting for {len(running)} running call(s) to insert their scenarios"
                 if running else ""))
        while True:   # a further Ctrl-C never skips the wait or the salvage
            try:
                cf.wait(running)
                con.rollback()   # a batch the interrupt cut short is discarded, then re-inserted whole
                for f in futures:
                    if f.done() and not f.cancelled() and f not in handled:
                        if inserted_by_this_run(futures[f]):
                            handled.add(f)
                        else:
                            insert_or_spill(f)
                break
            except KeyboardInterrupt:
                left = sum(1 for f in running if not f.done())
                print(f"Ctrl-C ignored: {left} paid call(s) still running; their scenarios are"
                      " inserted before the run exits")
        print(f"{len(handled)} of {len(domains)} domains stored; re-run for the rest")
        raise
    pool.shutdown(wait=True)
    return n_inserted, total_cost


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    ap.add_argument("--n", type=int, default=6, help="scenarios per domain")
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--domains", default=None, help="comma-separated override")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan on an in-memory copy of the DB; call nothing, write nothing")
    ap.add_argument("--yes", action="store_true",
                    help="submit the paid run without the interactive confirmation (required"
                         " when stdin is not a TTY)")
    args = ap.parse_args(argv)

    study = Study.resolve(args.study)
    domains = args.domains.split(",") if args.domains else DOMAINS
    template_path = study.templates_dir / "proposer.md"
    if not template_path.exists():
        raise SystemExit(f"no proposer template at {template_path}: this study does not use the"
                         " proposer (nothing was called or written)")
    template = string.Template(template_path.read_text())
    # the plan is made on an in-memory copy: a declined plan (or --dry-run)
    # creates and migrates no voi.db
    plan_con = study.connect_copy()
    print_plan(plan_con, domains, args.n, args.model)
    plan_con.close()
    if args.dry_run:
        print("DRY RUN: no call was made and nothing was written.")
        return
    if not args.yes and not confirm_interactively():
        raise SystemExit("not submitted: pass --yes, or confirm at the prompt on a TTY")

    con = study.connect()
    n_inserted, total_cost = run_domains(con, study.root, template, domains, args.n, args.model,
                                         args.workers)
    total = con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0]
    print(f"\ninserted {n_inserted} new scenarios; {total} total in DB; cost ${total_cost:.2f}")


if __name__ == "__main__":
    main()
