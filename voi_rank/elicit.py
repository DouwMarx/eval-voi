"""Elicitation harness (spec §6): renders the protocol's template per scenario
and sends it to every protocol member (provider + model) k_repeats times.

A slot is (scenario, protocol, provider, model, repeat_ix); a slot that already
holds a valid elicitation is skipped, so runs resume per member. Every attempt
(valid or not) is stored with its raw response. The plan (pending slots and
estimated cost per member) is made on an in-memory copy of the study DB, so
--dry-run and a declined plan write nothing, not even voi.db, and register no
protocol; a paid run needs --yes, or an interactive confirmation on a TTY.
Once confirmed, the preflight checks the members' credentials (a logged-in
claude CLI, an OpenRouter key the free /auth/key accepts) and only then the
real DB is opened, seeded, the protocol registered and the jobs submitted.

Paid work is never discarded: an interrupted run (Ctrl-C, a failed DB write,
any error in the main thread) cancels the pending slots, launches no retry,
waits for the running calls and stores their results before it exits (a
further Ctrl-C during that wait is reported and ignored; claude CLI children
run in their own session so the terminal's SIGINT never reaches them); a
result the DB refuses is appended to <study>/elicit_unstored.jsonl.

Usage:
  python -m voi_rank.elicit --study studies/business --protocol p001 \
      [--scenarios all|seed|1,2,3] [--k 3] [--workers 8] \
      [--members claude_cli:haiku,openrouter:openai/gpt-4o-mini] [--dry-run] [--yes]
  python -m voi_rank.elicit --study studies/business --manual [--dry-run]   # hand percentiles
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import sqlite3
import string
import sys
import threading
import time
from pathlib import Path

from voi_rank import db
from voi_rank.providers import claude_cli, get_provider, openrouter
from voi_rank.study import Study, add_study_arg
from voi_rank.validate import fit_all, strip_fences, validate_payload

MANUAL_PROTOCOL = db.MANUAL_PROTOCOL
SYSTEM_PROMPT = ("You are an expert decision analyst performing structured "
                 "quantitative elicitation. Follow the instructions exactly. "
                 "Output only what is asked for.")
TEMPLATE_FIELDS = ("title", "agent", "decision", "theta_definition", "instrument", "context")
# retry policy (at most one retry per slot)
TRANSPORT_RETRY_DELAY_S = 5.0       # 429 / 5xx without Retry-After, and transport errors
MAX_RETRY_DELAY_S = 120.0           # cap on a server's Retry-After (a worker never sleeps longer)
STORE_RETRY_DELAY_S = 1.0           # one retry of a failed DB write ('database is locked')
CLI_TIMEOUTS_TO_HALT = 2            # consecutive 'cli: timeout' results that halt a member
UNSTORED_FILE = "elicit_unstored.jsonl"
_HTTP_ERROR_RE = re.compile(r"^http: status (\d+)(?: retry-after (\d+(?:\.\d+)?)s)?")
# errors of the member's environment, not of one call: a retry cannot help and
# the member's pending slots are cancelled. HTTP 401/402/404 (auth, credit,
# unknown model id), a missing claude executable or a CLI that exits because
# it is not logged in.
_HALT_MEMBER_RE = re.compile(
    r"^http: status 40[124]\b"
    r"|^cli: 'claude' executable not found"
    r"|^cli: exit \d+: .*(?:not logged in|invalid api key|authentication)", re.IGNORECASE | re.DOTALL)
# a request the server rejected, unbilled: HTTP 400 (invalid params) or 403
# (OpenRouter: 'insufficient permissions, guardrail block, or moderation
# flag', so one flagged prompt). Per-request outcomes in OpenRouter's error
# reference: the slot is stored invalid without a retry and the member goes
# on, unless the response names the key or its permissions, or the member is
# rejected on a second scenario (then the request shape or the key is wrong).
_REJECTED_REQUEST_RE = re.compile(r"^http: status 40[03]\b")
_KEY_MESSAGE_RE = re.compile(r'"message"\s*:\s*"[^"]*(?:api.?key|permission|unauthori[sz]ed)',
                             re.IGNORECASE)
# a CLI call that did not finish: cut by the timeout or killed by a signal.
# Not retried (a hung CLI hangs again; the slot is pending on the next run);
# CLI_TIMEOUTS_TO_HALT consecutive timeouts halt the member (an invalid
# ANTHROPIC_API_KEY makes the CLI wait for ever with no output).
_UNFINISHED_CLI_RE = re.compile(r"^cli: (?:timeout|killed by signal)\b")
_CLI_TIMEOUT_RE = re.compile(r"^cli: timeout\b")


def halts_member(error: str | None) -> bool:
    return bool(error) and _HALT_MEMBER_RE.match(error) is not None


def rejected_request(error: str | None) -> bool:
    """HTTP 400/403: this request was refused (unbilled); no retry, and the
    member goes on unless run_jobs escalates (see _REJECTED_REQUEST_RE)."""
    return bool(error) and _REJECTED_REQUEST_RE.match(error) is not None


def names_key(error: str | None) -> bool:
    """The rejected request's error message blames the key or permissions
    (matched inside the JSON 'message' field only, never the echoed prompt)."""
    return bool(error) and _KEY_MESSAGE_RE.search(error) is not None


def cli_timeout(error: str | None) -> bool:
    return bool(error) and _CLI_TIMEOUT_RE.match(error) is not None


def render_prompt(template: string.Template, sc) -> str:
    """Substitute $title $agent $decision $theta_definition $instrument
    $context (empty string when the scenario has no context)."""
    fields = {f: (sc[f] if sc[f] is not None else "") for f in TEMPLATE_FIELDS}
    return template.substitute(fields)


def prompt_hash(prompt: str) -> str:
    return db.sha256(SYSTEM_PROMPT + "\n---\n" + prompt)


# --- one elicitation job (reject -> one retry -> mark invalid) --------------

def failed_attempt(error: str) -> dict:
    return {"raw": "", "error": error, "clean": None, "fits": None, "cost": 0.0}


def attempt_once(call, prompt: str, model: str) -> dict:
    """One provider call, parsed, validated and fitted. An exception escaping
    the provider becomes an attempt with error 'provider: <Type>: <msg>', so
    one bad call never aborts the run or discards completed paid work."""
    try:
        envelope, raw, err = call(prompt, model, SYSTEM_PROMPT)
    except Exception as ex:
        return failed_attempt(f"provider: {type(ex).__name__}: {ex}")
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
    return {"raw": raw, "error": err, "clean": clean, "fits": fits, "cost": cost}


def retry_after_requested(error: str | None) -> float | None:
    """The Retry-After seconds a provider recorded in an http error, if any."""
    m = _HTTP_ERROR_RE.match(error or "")
    return float(m.group(2)) if m and m.group(2) else None


def retry_delay(error: str | None) -> float | None:
    """Seconds to wait before the single retry. None: do not retry (the attempt
    is valid; an error of the member's environment that halts_member: http
    401/402/404, a CLI that cannot run; a rejected request, http 400/403,
    which the same prompt would get again; a CLI call that did not finish,
    timed out or killed by a signal). 0: retry at once (json/schema/
    constraint/fit failures and other provider errors). Positive: http 429,
    5xx and transport errors, using the server's Retry-After (clamped to
    MAX_RETRY_DELAY_S) when the provider recorded one, else
    TRANSPORT_RETRY_DELAY_S."""
    if error is None or halts_member(error) or rejected_request(error):
        return None
    if _UNFINISHED_CLI_RE.match(error):
        return None
    if not error.startswith("http:"):
        return 0.0
    m = _HTTP_ERROR_RE.match(error)
    if m is None:
        return TRANSPORT_RETRY_DELAY_S
    status = int(m.group(1))
    if status == 429 or status >= 500:
        return min(float(m.group(2)), MAX_RETRY_DELAY_S) if m.group(2) else TRANSPORT_RETRY_DELAY_S
    return 0.0


def elicit_job(call, prompt: str, model: str, sleep=time.sleep,
               stop: threading.Event | None = None) -> list[dict]:
    """Up to two attempts through one provider, retried per retry_delay().
    Each attempt dict: raw, error, clean, fits, cost. A clamped Retry-After
    is recorded in the first attempt's error. `stop` (set by run_jobs once
    its main thread is interrupted) skips the retry, and cuts its backoff
    short, so no call is launched after Ctrl-C."""
    attempts = [attempt_once(call, prompt, model)]
    delay = retry_delay(attempts[0]["error"])
    if delay is None:
        return attempts
    if delay > 0:
        requested = retry_after_requested(attempts[0]["error"])
        if requested is not None and requested > delay:
            attempts[0]["error"] += f" (retry-after {requested:g}s clamped to {delay:g}s)"
        if stop is None:
            sleep(delay)
        elif stop.wait(delay):
            return attempts
    if stop is not None and stop.is_set():
        return attempts
    attempts.append(attempt_once(call, prompt, model))
    return attempts


def store_attempts(con, scenario_id, protocol_id, member, repeat_ix, phash, attempts):
    """Insert every attempt (raw response always kept) and, for a valid one,
    its parameters, in ONE transaction per slot: a failed or interrupted
    write leaves nothing behind and the slot can be stored again. Returns
    True if the slot ended valid."""
    slot_valid = False
    for att in attempts:
        valid = att["error"] is None
        eid = db.insert_elicitation(con, scenario_id, protocol_id, member["provider"],
                                    member["model"], repeat_ix, phash, att["raw"],
                                    valid, att["error"])
        if valid:
            for name in db.PARAM_NAMES:
                d = att["clean"][name]
                db.insert_parameter(con, eid, name, d["p5"], d["p50"], d["p95"],
                                    d["unit"], d["reasoning"], att["fits"][name])
            slot_valid = True
    con.commit()
    return slot_valid


class StoreFailed(RuntimeError):
    """The DB refused a slot's attempts; they were spilled to UNSTORED_FILE."""


def spill_attempts(study_root: Path, protocol_id: int, job: dict, attempts: list[dict],
                   error: Exception) -> Path:
    """Append a slot's attempts (raw response, error, cost) to
    <study>/elicit_unstored.jsonl so a paid response survives a DB failure."""
    path = Path(study_root) / UNSTORED_FILE
    record = {
        "spilled_at": db.now_iso(), "store_error": f"{type(error).__name__}: {error}",
        "scenario_id": job["scenario_id"], "protocol_id": protocol_id,
        "provider": job["member"]["provider"], "model": job["member"]["model"],
        "repeat_ix": job["repeat_ix"], "prompt_hash": prompt_hash(job["prompt"]),
        "attempts": [{"raw": a["raw"], "error": a["error"], "cost": a["cost"]} for a in attempts],
    }
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
    return path


def store_or_spill(con, study_root: Path, protocol_id: int, job: dict, attempts: list[dict],
                   sleep=time.sleep) -> bool:
    """store_attempts with one retry after STORE_RETRY_DELAY_S on
    sqlite3.OperationalError (e.g. 'database is locked'). A second failure,
    or any other exception (e.g. the unique-slot index when another process
    stored the slot first), spills the attempts to UNSTORED_FILE and raises
    StoreFailed so the caller stops the run. Returns True if the slot ended
    valid."""
    label = f"scenario {job['scenario_id']} {db.member_label(job['member'])} repeat {job['repeat_ix']}"
    for attempt in (1, 2):
        try:
            return store_attempts(con, job["scenario_id"], protocol_id, job["member"],
                                  job["repeat_ix"], prompt_hash(job["prompt"]), attempts)
        except sqlite3.OperationalError as ex:
            con.rollback()
            error = ex
            if attempt == 1:
                print(f"store of {label} failed ({ex}); retrying in {STORE_RETRY_DELAY_S:g}s")
                sleep(STORE_RETRY_DELAY_S)
        except Exception as ex:
            con.rollback()
            error = ex
            break
    path = spill_attempts(study_root, protocol_id, job, attempts, error)
    raise StoreFailed(f"could not store {label}: {type(error).__name__}: {error};"
                      f" its attempts were appended to {path}")


# --- planning ---------------------------------------------------------------

def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not an integer") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"k must be >= 1, got {value}")
    return value


def parse_members_filter(spec: str | None) -> set[str] | None:
    if not spec:
        return None
    return {m.strip() for m in spec.split(",") if m.strip()}


def effective_k(member: dict, k_override: int | None) -> int:
    return member["k_repeats"] if k_override is None else k_override


def k_label(member: dict, k_override: int | None) -> str:
    k = effective_k(member, k_override)
    if k == member["k_repeats"]:
        return f"k={k}"
    return f"k={k} (override of {member['k_repeats']})"


def plan_jobs(con, study: Study, protocol_id: int, scenarios: str | None, k_override: int | None,
              members_filter: set[str] | None, warn: bool = True) -> tuple[list[dict], list[dict]]:
    """Pending slots for every (selected) member over the selected scenarios.
    scenarios=None uses the protocol's 'scenarios' selector; an explicit
    selector overrides a scoped protocol with a printed warning (warn=False
    keeps the second, real-DB plan of main quiet). Returns (members, jobs);
    a job is {scenario_id, member, repeat_ix, prompt}."""
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()
    members = db.protocol_members(prot)
    manual = [db.member_label(m) for m in members if m["provider"] == db.MANUAL_PROVIDER]
    if manual:
        raise SystemExit(f"protocol {prot['name']} has manual member(s) {manual}: hand "
                         "percentiles are loaded with --manual, not elicited")
    if members_filter is not None:
        unknown = members_filter - {db.member_label(m) for m in members}
        if unknown:
            raise SystemExit(f"--members names members not in protocol {prot['name']}: "
                             f"{sorted(unknown)}; protocol has "
                             f"{[db.member_label(m) for m in members]}")
        members = [m for m in members if db.member_label(m) in members_filter]
    scope = db.protocol_selector(prot)
    if scenarios is None:
        selector = scope
    else:
        selector = db.normalize_selector(scenarios)
        if scope != "all" and selector != scope and warn:
            print(f"warning: protocol {prot['name']} scopes scenarios to {scope!r}; "
                  f"--scenarios {selector!r} overrides it")
    template = string.Template((study.root / prot["template_path"]).read_text())
    jobs = []
    for sc in db.get_scenarios(con, selector):
        prompt = render_prompt(template, sc)
        for m in members:
            done = db.valid_repeats(con, sc["id"], protocol_id, m["provider"], m["model"])
            for rix in range(effective_k(m, k_override)):
                if rix not in done:
                    jobs.append({"scenario_id": sc["id"], "member": m,
                                 "repeat_ix": rix, "prompt": prompt})
    return members, jobs


def dry_run(con, prot, members, jobs, k_override: int | None = None):
    """Render prompts and list pending slots per member; call nothing."""
    print(f"DRY RUN: protocol {prot['name']} (template {prot['template_path']}, "
          f"hash {prot['template_hash'][:12]}, scenarios {db.protocol_selector(prot)})")
    by_member = {}
    for j in jobs:
        by_member.setdefault(db.member_label(j["member"]), []).append(j)
    for m in members:
        pending = by_member.get(db.member_label(m), [])
        sids = sorted({j["scenario_id"] for j in pending})
        print(f"  member {db.member_label(m)} ({k_label(m, k_override)}): {len(pending)} pending "
              f"slots over {len(sids)} scenarios"
              + (f" (ids {sids[0]}..{sids[-1]})" if sids else ""))
    if jobs:
        first = jobs[0]
        print(f"\nfirst pending prompt (scenario {first['scenario_id']}, "
              f"{len(first['prompt'])} chars, hash {prompt_hash(first['prompt'])[:12]}):\n")
        print(first["prompt"])
    print(f"\n{len(jobs)} slots would be elicited; no provider was called.")


# --- paid-run guard ---------------------------------------------------------

def check_credentials(members: list[dict]) -> None:
    """Fail fast before the plan is even printed: a missing OpenRouter key
    aborts with zero calls made (no network here)."""
    if any(m["provider"] == "openrouter" for m in members):
        openrouter.api_key()


def preflight(members: list[dict], opener=None) -> None:
    """After the run is confirmed, before voi.db is touched and the first
    paid call: a claude_cli member needs a logged-in CLI (`claude auth
    status`, free; it does not verify an API key, whose hang the timeout
    halt in run_jobs catches), an openrouter member a key the free GET
    /auth/key accepts. Any failure raises, with zero elicitation calls made.
    Only a confirmed run reaches this; --dry-run never does."""
    if any(m["provider"] == "claude_cli" for m in members):
        print(claude_cli.check_auth())
    if not any(m["provider"] == "openrouter" for m in members):
        return
    info = openrouter.check_key(openrouter.api_key(), opener=opener)
    limit = info.get("limit")
    print(f"OpenRouter key verified (label {info.get('label')!r}, usage ${info.get('usage', 0)},"
          f" limit {'none' if limit is None else f'${limit}'})")


def member_mean_cost(con, member: dict) -> tuple[float, int] | None:
    """(mean recorded USD cost per stored attempt, attempts) of one member over
    every protocol in the study; None when the member has no stored attempts."""
    rows = con.execute("SELECT raw_response FROM elicitations WHERE provider=? AND model=?",
                       (member["provider"], member["model"])).fetchall()
    if not rows:
        return None
    return sum(db.envelope_cost(r[0]) for r in rows) / len(rows), len(rows)


def print_plan(con, prot, members, jobs):
    """Slots per member and the estimated cost (slots x mean stored cost per
    attempt of that member in this study, 'unknown' without history)."""
    print(f"plan: protocol {prot['name']}, {len(jobs)} pending slots "
          "(one attempt each; a failed attempt is retried once)")
    total, unknown = 0.0, False
    for m in members:
        n = sum(1 for j in jobs if db.member_label(j["member"]) == db.member_label(m))
        est = member_mean_cost(con, m)
        if est is None:
            cost, unknown = "unknown (no stored attempts of this member in this study)", True
        else:
            total += n * est[0]
            cost = f"${n * est[0]:.2f} (mean ${est[0]:.4f}/attempt over {est[1]} stored attempts)"
        print(f"  {db.member_label(m)}: {n} slots, estimated cost {cost}")
    print(f"  estimated total: ${total:.2f}" + (" + unknown" if unknown else ""))


def confirm_interactively(prompt: str = "submit this run? [y/N] ") -> bool:
    """True only when stdin is a TTY and the user answers yes."""
    if not sys.stdin.isatty():
        return False
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


# --- the consumer loop ------------------------------------------------------

def run_jobs(con, study: Study, protocol_id: int, jobs: list[dict], workers: int) -> tuple[int, float, int]:
    """Submit every job to a thread pool and store each result as it
    completes. Returns (valid slots, total cost, cancelled slots).

    Safety rules: (1) a member has its pending slots cancelled (fix the key,
    credits or model id and re-run to resume) when an attempt ends in an
    error of its environment (halts_member: http 401/402/404, a CLI that
    cannot run), when its rejected requests (http 400/403, unbilled, stored
    invalid without a retry) name the key or reach a second distinct
    scenario, or after CLI_TIMEOUTS_TO_HALT consecutive CLI timeouts; (2) a
    DB write that fails is retried once, then the attempts are spilled to
    <study>/elicit_unstored.jsonl and the run stops; (3) on any exception in
    this thread (Ctrl-C included) the pending jobs are cancelled, no retry is
    launched, the running calls are awaited and stored, and the exception is
    re-raised; a further Ctrl-C during that wait or salvage is reported and
    ignored, and the salvage is idempotent (a slot the interrupt caught
    between its commit and its bookkeeping is recognised in the DB, not
    stored twice). Paid work is never discarded."""
    # elicitation ids above this one were written by this run: the salvage
    # uses it to recognise a slot whose commit landed just before an interrupt
    last_id_before = con.execute("SELECT COALESCE(MAX(id), 0) FROM elicitations").fetchone()[0]
    stop = threading.Event()   # set on interrupt: a worker then launches no retry
    pool = cf.ThreadPoolExecutor(workers)
    futures = {pool.submit(elicit_job, get_provider(j["member"]["provider"]),
                           j["prompt"], j["member"]["model"], stop=stop): j for j in jobs}
    handled: set = set()     # futures whose attempts are in the DB or spilled
    halted: set[str] = set()
    rejected: dict[str, set[int]] = {}   # member -> scenarios whose request was rejected (400/403)
    timeouts: dict[str, int] = {}        # member -> consecutive CLI timeouts
    n_valid, total_cost, n_cancelled = 0, 0.0, 0

    def halt_reason(label: str, scenario_id: int, error: str | None) -> str | None:
        """Why this result cancels the member's pending slots; None to go on."""
        if halts_member(error):
            return "a retry cannot help"
        if cli_timeout(error):
            timeouts[label] = timeouts.get(label, 0) + 1
            if timeouts[label] >= CLI_TIMEOUTS_TO_HALT:
                return (f"{timeouts[label]} consecutive timeouts (the CLI hangs with no output"
                        " when its API key is invalid)")
            return None
        timeouts[label] = 0
        if rejected_request(error):
            sids = rejected.setdefault(label, set())
            sids.add(scenario_id)
            if names_key(error):
                return "the response names the key or its permissions"
            if len(sids) >= 2:
                return f"requests rejected on {len(sids)} distinct scenarios {sorted(sids)}"
        return None

    def result_of(fut) -> list[dict]:
        try:
            return fut.result()
        except Exception as ex:  # one failed job never stops the loop
            return [failed_attempt(f"provider: {type(ex).__name__}: {ex}")]

    def store(fut, attempts) -> bool:
        # a slot counts as handled once its attempts are in the DB or in the
        # spill file; an interrupt in the middle of the write leaves it
        # unhandled so the salvage below stores it again after the rollback
        try:
            ok = store_or_spill(con, study.root, protocol_id, futures[fut], attempts)
        except StoreFailed:
            handled.add(fut)
            raise
        handled.add(fut)
        return ok

    def stored_by_this_run(job: dict) -> bool:
        return con.execute(
            "SELECT 1 FROM elicitations WHERE id>? AND scenario_id=? AND protocol_id=? AND provider=?"
            " AND model=? AND repeat_ix=? AND prompt_hash=? LIMIT 1",
            (last_id_before, job["scenario_id"], protocol_id, job["member"]["provider"],
             job["member"]["model"], job["repeat_ix"], prompt_hash(job["prompt"]))).fetchone() is not None

    def cancel_pending(member: str | None = None) -> int:
        return sum(1 for f, j in futures.items()
                   if (member is None or db.member_label(j["member"]) == member) and f.cancel())

    def salvage() -> int:
        """Store every finished slot not yet handled; a slot this run already
        committed (interrupt between commit and handled.add) is only counted.
        Idempotent, so a repeated call after a further Ctrl-C is harmless."""
        nonlocal n_valid, total_cost
        con.rollback()
        salvaged = 0
        for f in futures:
            if f.done() and not f.cancelled() and f not in handled:
                attempts = result_of(f)
                if stored_by_this_run(futures[f]):
                    handled.add(f)
                    n_valid += attempts[-1]["error"] is None
                else:
                    try:
                        n_valid += store(f, attempts)
                    except StoreFailed as err:
                        print(err)
                    salvaged += 1
                total_cost += sum(a["cost"] for a in attempts)
        return salvaged

    try:
        for i, fut in enumerate(cf.as_completed(futures), 1):
            j = futures[fut]
            if fut.cancelled():
                n_cancelled += 1
                continue
            attempts = result_of(fut)
            ok = store(fut, attempts)
            n_valid += ok
            total_cost += sum(a["cost"] for a in attempts)
            label = db.member_label(j["member"])
            error = attempts[-1]["error"]
            status = "ok" if ok else f"INVALID ({error})"
            print(f"[{i}/{len(jobs)}] scenario {j['scenario_id']} {label} repeat {j['repeat_ix']}: {status}")
            if rejected_request(error):
                print(f"scenario {j['scenario_id']} {label}: the request was rejected (http 400/403:"
                      " invalid params, guardrail or moderation flag on this prompt, or permissions);"
                      " stored invalid, not retried, not billed; the slot is pending on the next run")
            if label in halted:
                continue
            why = halt_reason(label, j["scenario_id"], error)
            if why:
                halted.add(label)
                n = cancel_pending(label)
                print(f"member {label}: {(error or '')[:160]}: {why}; cancelled its {n} pending"
                      " slots (fix the key, credits or model id, then re-run to resume)")
    except BaseException as ex:
        # Ctrl-C, a failed store or any other error here: stop submitting,
        # launch no retry, keep what is paid for
        stop.set()
        pending = cancel_pending()
        pool.shutdown(wait=False, cancel_futures=True)
        running = [f for f in futures if not f.done()]
        print(f"\ninterrupted ({type(ex).__name__}): {pending} pending slots cancelled"
              + (f", waiting for {len(running)} running call(s) to store their results"
                 if running else ""))
        salvaged = 0
        while True:   # a further Ctrl-C never skips the wait or the salvage
            try:
                cf.wait(running)
                salvaged += salvage()
                break
            except KeyboardInterrupt:
                left = sum(1 for f in running if not f.done())
                print(f"Ctrl-C ignored: {left} paid call(s) still running; their results are"
                      " stored before the run exits")
        print(f"{len(handled)} of {len(jobs)} slots stored ({salvaged} after the interruption);"
              " re-run to resume")
        raise
    pool.shutdown(wait=True)
    return n_valid, total_cost, n_cancelled


# --- manual (hand-entered) percentiles --------------------------------------

def manual_missing(study: Study) -> str | None:
    """Why --manual has nothing to load (None when it has): the manual
    protocol file or a 'manual' key on some scenario is absent. main() asks
    before connecting, so such a study never gets a voi.db from --manual."""
    path = study.protocol_path(MANUAL_PROTOCOL)
    seeds = json.loads(study.scenarios_json.read_text())
    if not path.exists() or not any("manual" in sc for sc in seeds):
        return (f"no manual percentiles in this study (needs protocols/{MANUAL_PROTOCOL}.yaml "
                "and a 'manual' key on at least one scenario in scenarios.json); nothing written")
    return None


def run_manual(con, study: Study, dry_run: bool = False):
    """Load the hand-entered 'manual' percentiles of scenarios.json under the
    manual protocol (M1 smoke test). Scenarios without a 'manual' key are
    skipped. The numbers are frozen PER SCENARIO: a scenario already loaded
    is skipped when the file's manual block equals the stored one and refused
    when it differs (change the title to make a new scenario); a scenario
    whose manual block is new loads at any time. The caller checks
    manual_missing() first. dry_run prints what would be loaded, and refuses
    what the real load would refuse, writing nothing."""
    path = study.protocol_path(MANUAL_PROTOCOL)
    seeds = json.loads(study.scenarios_json.read_text())
    # registers the protocol (or checks its members); under --dry-run con is
    # the in-memory copy, so this is side-effect free
    protocol_id = db.get_or_create_protocol(con, path, study.root)
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()
    member = db.protocol_members(prot)[0]
    if member["provider"] != db.MANUAL_PROVIDER:
        raise SystemExit(f"{MANUAL_PROTOCOL} must declare model_alias: manual "
                         f"(got member {db.member_label(member)})")
    pending, loaded, changed = [], 0, []
    for sc in seeds:
        if "manual" not in sc:
            continue
        sid = con.execute("SELECT id FROM scenarios WHERE title=? AND source='seed'",
                          (sc["title"],)).fetchone()["id"]
        stored = db.valid_raw_responses(con, sid, protocol_id, member["provider"], member["model"])
        if not stored:
            pending.append((sid, sc))
        elif all(json.loads(raw) == sc["manual"] for raw in stored):
            loaded += 1
        else:
            changed.append(f"  {sid} {sc['title']!r}")
    if changed:
        raise RuntimeError(
            f"{len(changed)} scenario(s) carry hand percentiles that differ from the numbers"
            f" loaded under {MANUAL_PROTOCOL}:\n" + "\n".join(changed)
            + "\nloaded numbers are frozen (elicitations.prompt_hash); change the title to make"
            " a new scenario, or start a new voi.db")
    if dry_run:
        print(f"DRY RUN: would load {len(pending)} manual scenarios under {MANUAL_PROTOCOL}"
              f" (hash {prot['template_hash'][:12]}; {loaded} already loaded):")
        for sid, sc in pending:
            print(f"  {sid} {sc['title']}")
        print("nothing was written.")
        return
    n_ok = 0
    for sid, sc in pending:
        clean, err = validate_payload({"parameters": sc["manual"]})
        if err is None:
            fits, err = fit_all(clean)
        raw = json.dumps(sc["manual"])
        eid = db.insert_elicitation(con, sid, protocol_id, member["provider"], member["model"],
                                    0, db.sha256(raw), raw, err is None, err)
        if err is None:
            for name in db.PARAM_NAMES:
                d = clean[name]
                db.insert_parameter(con, eid, name, d["p5"], d["p50"], d["p95"],
                                    d["unit"], d["reasoning"], fits[name])
            n_ok += 1
        else:
            print(f"manual seed {sc['title']!r} INVALID: {err}")
        con.commit()
    print(f"manual load: {n_ok} scenarios valid under {MANUAL_PROTOCOL}")


# --- main -------------------------------------------------------------------

def plan(con, study: Study, args, preview: bool):
    """Seed the scenarios, register the protocol and plan the pending slots
    on `con` (idempotent: once on the in-memory copy as the preview, whose
    seeding prints 'would refresh' and whose scope warning is printed, then
    quietly on the real DB once the run is confirmed). Returns
    (protocol_id, prot, members, jobs)."""
    db.seed_scenarios(con, study.scenarios_json, dry_run=preview)
    protocol_id = db.get_or_create_protocol(con, study.protocol_path(args.protocol), study.root)
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()
    members, jobs = plan_jobs(con, study, protocol_id, args.scenarios, args.k,
                              parse_members_filter(args.members), warn=preview)
    return protocol_id, prot, members, jobs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    ap.add_argument("--protocol", default="p001",
                    help="protocol name (protocols/<name>.yaml) or YAML path")
    ap.add_argument("--scenarios", default=None,
                    help="'all' | 'seed' | ids '1,2,3' (default: the protocol's 'scenarios'"
                         " selector, else all)")
    ap.add_argument("--k", type=positive_int, default=None,
                    help="override every member's k_repeats (>= 1)")
    ap.add_argument("--members", default=None,
                    help="comma-separated provider:model filter (default: all members)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true",
                    help="plan on an in-memory copy of the DB, render prompts and list pending"
                         " slots; call no provider and write nothing")
    ap.add_argument("--yes", action="store_true",
                    help="submit the paid run without the interactive confirmation (required"
                         " when stdin is not a TTY)")
    ap.add_argument("--manual", action="store_true",
                    help="load hand-entered percentiles (protocol p000_manual)")
    args = ap.parse_args(argv)

    study = Study.resolve(args.study)
    if args.manual:
        why = manual_missing(study)
        if why:   # before any connection: a study without manual inputs gets no voi.db
            print(why)
            return
        con = study.connect_copy() if args.dry_run else study.connect()
        db.seed_scenarios(con, study.scenarios_json, dry_run=args.dry_run)
        run_manual(con, study, dry_run=args.dry_run)
        return

    # the plan is made on an in-memory copy (seeded and with the protocol
    # registered there only): a dry run or a declined plan creates nothing,
    # not even voi.db, and freezes no template hash
    plan_con = study.connect_copy()
    _, prot, members, jobs = plan(plan_con, study, args, preview=True)
    if args.dry_run:
        dry_run(plan_con, prot, members, jobs, args.k)
        return
    if not jobs:
        print("nothing to do: all requested slots already have valid elicitations (nothing written)")
        return
    check_credentials(members)
    print_plan(plan_con, prot, members, jobs)
    plan_con.close()
    if not args.yes and not confirm_interactively():
        raise SystemExit("not submitted: pass --yes, or confirm at the prompt on a TTY"
                         " (nothing was written)")
    preflight(members)
    # only now the real DB: seeded, protocol registered, the same plan again
    con = study.connect()
    protocol_id, prot, members, real_jobs = plan(con, study, args, preview=False)
    if len(real_jobs) != len(jobs):
        print(f"note: {len(real_jobs)} slots pending now (the plan listed {len(jobs)})")
    jobs = real_jobs
    if not jobs:   # another process filled the plan meanwhile
        print("nothing to do: all requested slots already have valid elicitations")
        return
    print(f"eliciting {len(jobs)} slots under {prot['name']} "
          f"(members={[db.member_label(m) for m in members]}, workers={args.workers})")

    n_valid, total_cost, n_cancelled = run_jobs(con, study, protocol_id, jobs, args.workers)
    rate = n_valid / len(jobs)
    print(f"\ndone: {n_valid}/{len(jobs)} slots valid ({rate:.1%})"
          + (f", {n_cancelled} cancelled" if n_cancelled else "")
          + f", total elicitation cost ${total_cost:.2f}")


if __name__ == "__main__":
    main()
