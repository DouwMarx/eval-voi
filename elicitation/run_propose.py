"""Proposer: generate scenarios from seed domains (spec §6.5, §7).

No dedupe by design: scenario text is its identity; duplicates are acceptable.

Usage: python -m elicitation.run_propose [--n 6] [--model haiku] [--workers 5]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import string

from db import io
from elicitation.run_elicit import call_claude, strip_fences

ROOT = io.ROOT
TEMPLATE_PATH = ROOT / "elicitation" / "templates" / "proposer.md"

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


def propose_domain(template: string.Template, domain: str, n: int, model: str):
    """Returns (scenarios list, error | None). One retry on failure."""
    prompt = template.substitute(domain=domain, n=n)
    last_err = None
    for _ in range(2):
        envelope, _raw, err = call_claude(prompt, model)
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
            return good, None
        last_err = "schema: no valid scenario objects in array"
    return [], last_err


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(io.DEFAULT_DB))
    ap.add_argument("--n", type=int, default=6, help="scenarios per domain")
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--domains", default=None, help="comma-separated override")
    args = ap.parse_args()

    domains = args.domains.split(",") if args.domains else DOMAINS
    con = io.connect(args.db)
    template = string.Template(TEMPLATE_PATH.read_text())

    n_inserted = 0
    with cf.ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(propose_domain, template, d, args.n, args.model): d
                   for d in domains}
        for fut in cf.as_completed(futures):
            domain = futures[fut]
            scenarios, err = fut.result()
            if err:
                print(f"domain {domain!r}: FAILED ({err})")
                continue
            for sc in scenarios:
                io.insert_scenario(con, sc, source=f"proposer:{domain}")
            n_inserted += len(scenarios)
            print(f"domain {domain!r}: inserted {len(scenarios)}")

    total = con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0]
    print(f"\ninserted {n_inserted} new scenarios; {total} total in DB")


if __name__ == "__main__":
    main()
