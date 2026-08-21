"""Elicitation harness: headless `claude -p` calls (spec §6).

Deviations from spec §6.1, verified against `claude --help` on CLI 2.1.220 and
recorded in LEARNINGS.md:
- `--bare` exists but restricts Anthropic auth to ANTHROPIC_API_KEY, which is
  absent under OAuth login. Context is instead isolated with `--tools ""`,
  `--setting-sources ""` and an explicit `--system-prompt`; verified
  empirically to exclude CLAUDE.md / user settings (227 input tokens).
- `--max-turns` no longer exists; with all tools disabled the call is
  single-turn by construction.

Usage:
  python -m elicitation.run_elicit --protocol elicitation/protocols/p001.yaml \
      [--scenarios all|seed|1,2,3] [--k 3] [--workers 8]
  python -m elicitation.run_elicit --manual   # hand-entered seed percentiles
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import string
import subprocess
from pathlib import Path

from core import fit as fitmod
from db import io

ROOT = io.ROOT
SEED_JSON = ROOT / "scenarios" / "seed.json"
MANUAL_PROTOCOL = ROOT / "elicitation" / "protocols" / "p000_manual.yaml"

SYSTEM_PROMPT = ("You are an expert decision analyst performing structured "
                 "quantitative elicitation. Follow the instructions exactly. "
                 "Output only what is asked for.")
PROB_PARAMS = {"p", "s", "t", "e"}
CLI_TIMEOUT_S = 600
_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


# --- CLI call ---------------------------------------------------------------

def call_claude(prompt: str, model_alias: str):
    """Returns (envelope | None, raw_stdout, error | None). raw_stdout is the
    full JSON envelope as printed by the CLI (stored verbatim in the DB)."""
    cmd = ["claude", "-p", prompt,
           "--model", model_alias, "--output-format", "json",
           "--tools", "", "--setting-sources", "", "--no-session-persistence",
           "--system-prompt", SYSTEM_PROMPT]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None, "", f"cli: timeout after {CLI_TIMEOUT_S}s"
    raw = proc.stdout
    if proc.returncode != 0:
        return None, raw or proc.stderr, f"cli: exit {proc.returncode}: {proc.stderr[-300:]}"
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as ex:
        return None, raw, f"json: envelope parse failed: {ex}"
    if envelope.get("is_error"):
        return envelope, raw, f"cli: is_error: {str(envelope.get('result'))[:300]}"
    return envelope, raw, None


def strip_fences(text: str) -> str:
    text = text.strip()
    m = _FENCE_RE.match(text)
    return m.group(1) if m else text


# --- validation (spec §6.4) -------------------------------------------------

def validate_payload(obj) -> tuple[dict | None, str | None]:
    """Schema + constraint checks. Returns (clean_params, None) or (None, error)."""
    if not isinstance(obj, dict) or not isinstance(obj.get("parameters"), dict):
        return None, "schema: missing 'parameters' object"
    prm = obj["parameters"]
    missing = [n for n in io.PARAM_NAMES if n not in prm]
    if missing:
        return None, f"schema: missing parameters {missing}"
    clean = {}
    for name in io.PARAM_NAMES:
        d = prm[name]
        if not isinstance(d, dict):
            return None, f"schema: {name} is not an object"
        try:
            p5, p50, p95 = float(d["p5"]), float(d["p50"]), float(d["p95"])
        except (KeyError, TypeError, ValueError):
            return None, f"schema: {name}: missing or non-numeric percentiles"
        if not (p5 < p50 < p95):
            return None, f"constraint: {name}: percentiles not strictly increasing"
        if name in PROB_PARAMS:
            if not (0.0 < p5 and p95 < 1.0):
                return None, f"constraint: {name}: probabilities must lie in (0,1)"
        elif p5 <= 0.0:
            return None, f"constraint: {name}: must be > 0"
        clean[name] = {"p5": p5, "p50": p50, "p95": p95,
                       "unit": str(d.get("unit", "")),
                       "reasoning": str(d.get("reasoning", ""))}
    if clean["s"]["p50"] <= 1.0 - clean["t"]["p50"]:
        return None, "constraint: informativeness: median s <= 1 - median t"
    if not (0.001 <= clean["p"]["p50"] <= 0.999):
        return None, "constraint: degenerate prior: p50 of p outside [0.001, 0.999]"
    return clean, None


def fit_all(clean: dict) -> tuple[dict | None, str | None]:
    try:
        return {name: fitmod.fit_param(name, d["p5"], d["p50"], d["p95"])
                for name, d in clean.items()}, None
    except Exception as ex:
        return None, f"fit: {ex}"


# --- one elicitation job (reject -> one retry -> mark invalid) --------------

def elicit_job(prompt: str, model_alias: str) -> list[dict]:
    """Up to two attempts. Each attempt dict: raw, error, clean, fits, cost."""
    attempts = []
    for _ in range(2):
        envelope, raw, err = call_claude(prompt, model_alias)
        clean = fits = None
        if err is None:
            payload = strip_fences(str(envelope.get("result", "")))
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError as ex:
                err = f"json: result parse failed: {ex}"
            else:
                clean, err = validate_payload(obj)
                if clean is not None:
                    fits, err = fit_all(clean)
        cost = float(envelope.get("total_cost_usd") or 0.0) if envelope else 0.0
        attempts.append({"raw": raw, "error": err, "clean": clean,
                         "fits": fits, "cost": cost})
        if err is None:
            break
    return attempts


def store_attempts(con, scenario_id, protocol_id, repeat_ix, prompt_hash, attempts):
    """Insert every attempt (raw response always kept); parameters only for a
    valid attempt. Returns True if the slot ended valid."""
    slot_valid = False
    for att in attempts:
        valid = att["error"] is None
        eid = io.insert_elicitation(con, scenario_id, protocol_id, repeat_ix,
                                    prompt_hash, att["raw"], valid, att["error"])
        if valid:
            for name in io.PARAM_NAMES:
                d = att["clean"][name]
                io.insert_parameter(con, eid, name, d["p5"], d["p50"], d["p95"],
                                    d["unit"], d["reasoning"], att["fits"][name])
            slot_valid = True
        con.commit()  # one transaction per attempt: row + all 7 params, atomically
    return slot_valid


# --- scenario seeding -------------------------------------------------------

def ensure_seed_scenarios(con):
    """Insert the 8 hand-written scenarios once (idempotent by title+source)."""
    seeds = json.loads(SEED_JSON.read_text())
    for sc in seeds:
        row = con.execute("SELECT id FROM scenarios WHERE title=? AND source='seed'",
                          (sc["title"],)).fetchone()
        if row is None:
            io.insert_scenario(con, {k: v for k, v in sc.items() if k != "manual"},
                               source="seed")


def run_manual(con):
    """Load the hand-entered seed percentiles under the manual protocol (M1)."""
    protocol_id = io.get_or_create_protocol(con, MANUAL_PROTOCOL)
    seeds = json.loads(SEED_JSON.read_text())
    n_ok = 0
    for sc in seeds:
        row = con.execute("SELECT id FROM scenarios WHERE title=? AND source='seed'",
                          (sc["title"],)).fetchone()
        sid = row["id"]
        if io.valid_repeat_count(con, sid, protocol_id) > 0:
            continue
        clean, err = validate_payload({"parameters": sc["manual"]})
        if err is None:
            fits, err = fit_all(clean)
        raw = json.dumps(sc["manual"])
        eid = io.insert_elicitation(con, sid, protocol_id, 0, io.sha256(raw), raw,
                                    err is None, err)
        if err is None:
            for name in io.PARAM_NAMES:
                d = clean[name]
                io.insert_parameter(con, eid, name, d["p5"], d["p50"], d["p95"],
                                    d["unit"], d["reasoning"], fits[name])
            n_ok += 1
        else:
            print(f"manual seed {sc['title']!r} INVALID: {err}")
        con.commit()
    print(f"manual load: {n_ok} scenarios valid under p000_manual")


# --- main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(io.DEFAULT_DB))
    ap.add_argument("--protocol", default="elicitation/protocols/p001.yaml",
                    help="path to protocol YAML")
    ap.add_argument("--scenarios", default="all", help="'all' | 'seed' | ids '1,2,3'")
    ap.add_argument("--k", type=int, default=None, help="override protocol k_repeats")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--manual", action="store_true",
                    help="load hand-entered seed percentiles (protocol p000_manual)")
    args = ap.parse_args()

    con = io.connect(args.db)
    ensure_seed_scenarios(con)
    if args.manual:
        run_manual(con)
        return

    protocol_id = io.get_or_create_protocol(con, ROOT / args.protocol)
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()
    k = args.k or prot["k_repeats"]
    template = string.Template((ROOT / prot["template_path"]).read_text())

    jobs = []
    for sc in io.get_scenarios(con, args.scenarios):
        done = {r["repeat_ix"] for r in con.execute(
            "SELECT repeat_ix FROM elicitations WHERE scenario_id=? AND protocol_id=?"
            " AND valid=1", (sc["id"], protocol_id))}
        for rix in range(k):
            if rix in done:
                continue
            prompt = template.substitute(
                title=sc["title"], agent=sc["agent"], decision=sc["decision"],
                theta_definition=sc["theta_definition"], instrument=sc["instrument"])
            jobs.append((sc["id"], rix, prompt))

    if not jobs:
        print("nothing to do: all requested slots already have valid elicitations")
        return
    print(f"eliciting {len(jobs)} slots under {prot['name']} "
          f"(model={prot['model_alias']}, workers={args.workers})")

    n_valid = 0
    total_cost = 0.0
    with cf.ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(elicit_job, prompt, prot["model_alias"]): (sid, rix, prompt)
                   for sid, rix, prompt in jobs}
        for i, fut in enumerate(cf.as_completed(futures), 1):
            sid, rix, prompt = futures[fut]
            attempts = fut.result()
            prompt_hash = io.sha256(SYSTEM_PROMPT + "\n---\n" + prompt)
            ok = store_attempts(con, sid, protocol_id, rix, prompt_hash, attempts)
            n_valid += ok
            total_cost += sum(a["cost"] for a in attempts)
            status = "ok" if ok else f"INVALID ({attempts[-1]['error']})"
            print(f"[{i}/{len(jobs)}] scenario {sid} repeat {rix}: {status}")

    rate = n_valid / len(jobs)
    print(f"\ndone: {n_valid}/{len(jobs)} slots valid ({rate:.1%}), "
          f"total elicitation cost ${total_cost:.2f}")


if __name__ == "__main__":
    main()
