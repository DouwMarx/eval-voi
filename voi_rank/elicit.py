"""Elicitation harness (spec §6): renders the protocol's template per scenario
and sends it to every protocol member (provider + model) k_repeats times.

A slot is (scenario, protocol, provider, model, repeat_ix, stage); a slot that
already holds a valid elicitation is skipped, so runs resume per member and
per stage. A staged protocol (db.normalize_stages: a decision stage asking
p, B, K once per scenario group, rendered from the group's shared agent,
decision, theta text and the protocol's decision context and stored on the
group's representative scenario, its lowest id; and an instrument stage
asking s, t, C per scenario, rendered like a single-stage template) plans
both stages at once (--stage NAME restricts to one); the stages are
independent (the instrument prompt carries no decision-level number), so
their calls share one pool. Every attempt
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

Usage-limit outages (v2.3): during a claude.ai usage-limit window the CLI
exits 1 with a zero-usage envelope of API status 429 (no model call,
nothing billed; claude_cli.usage_limit_envelope), classified 'cli:
usage-limit (zero-usage exit 1)'. Such a result is NOT stored as an attempt
(it is not an elicitation attempt: validity and cost statistics stay clean;
the run summary counts it) and its slot is re-planned. The job launches no
retry for it (retry_delay returns OUTAGE_PAUSE). run_jobs tracks outages
PER MEMBER (a model-specific limit holds only that model; a healthy member
is never held back by a limited one): after OUTAGE_STREAK consecutive such
results of one member across workers it stops dispatching that member (its
not-yet-started slots are held back) while the other members go on; once
only held members' slots are left the run pauses, probes each held member
with ONE call and resumes a member when its probe is billed (the answer is
stored like any slot). A pause lasts until OUTAGE_RESET_MARGIN_S after the
reset time the CLI's message names, when that is within one session
window (SESSION_WINDOW_S), else VOI_OUTAGE_SLEEP_S (the shortest over the
held members); once a member has paused VOI_OUTAGE_MAX_WAIT_S since its
last billed result the run gives up on that member with a clear message
(its slots pending for the next run, the other members go on); the budget
restarts at every billed result, so a run spanning several windows waits
out each. Fewer than OUTAGE_STREAK zero-usage results in a row (a blip)
are re-planned at the end of the batch without a pause; only a billed
result of the member (a model answered, or a cost was recorded) resets
its streak, an unbilled failure (http 401, a transport error) leaves it,
and once a member is held a billed answer of its call already in flight
(started before the hold) no longer does. A zero-usage exit of another
API status (an unknown model id, 404) is an ordinary failed attempt
instead.

Usage:
  python -m voi_rank.elicit --study studies/business --protocol p001 \
      [--scenarios all|seed|1,2,3] [--k 3] [--workers 8] \
      [--members claude_cli:haiku,openrouter:openai/gpt-4o-mini] [--stage decision] [--dry-run] [--yes]
  python -m voi_rank.elicit --study studies/business --manual [--dry-run]   # hand percentiles
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import re
import sqlite3
import string
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from voi_rank import db, gauss_fit
from voi_rank.dotenv import seconds_setting
from voi_rank.providers import claude_cli, get_provider, openrouter
from voi_rank.study import Study, add_study_arg
from voi_rank.validate import fit_all, strip_fences, validate_payload

MANUAL_PROTOCOL = db.MANUAL_PROTOCOL
SYSTEM_PROMPT = ("You are an expert decision analyst performing structured "
                 "quantitative elicitation. Follow the instructions exactly. "
                 "Output only what is asked for.")
TEMPLATE_FIELDS = ("title", "agent", "decision", "theta_definition", "instrument", "context")
# a decision-stage template renders the group's shared decision text and the
# protocol's decision context, and nothing of the instrument
DECISION_FIELDS = ("agent", "decision", "theta_definition")
# retry policy (at most one retry per slot)
TRANSPORT_RETRY_DELAY_S = 5.0       # 429 / 5xx without Retry-After, and transport errors
MAX_RETRY_DELAY_S = 120.0           # cap on a server's Retry-After (a worker never sleeps longer)
STORE_RETRY_DELAY_S = 1.0           # one retry of a failed DB write ('database is locked')
CLI_TIMEOUTS_TO_HALT = 2            # consecutive 'cli: timeout' results that halt a member
# usage-limit outage (a zero-usage CLI exit, nothing billed): the streak of
# consecutive such results of one member, across workers, that holds that
# member; a pause lasts until OUTAGE_RESET_MARGIN_S after the reset the CLI's
# message names when that is at most one session window away (a claude.ai
# session limit resets within 5 hours; a later time is a weekly limit, or a
# reset already past), else VOI_OUTAGE_SLEEP_S; the run gives up on a member
# once it has paused VOI_OUTAGE_MAX_WAIT_S since that member's last billed
# result (both from the environment or .env; the default is one session
# window plus margin, per window: a billed result restarts the budget)
OUTAGE_STREAK = 5
OUTAGE_SLEEP_SETTING, DEFAULT_OUTAGE_SLEEP_S = "VOI_OUTAGE_SLEEP_S", 300.0
OUTAGE_MAX_WAIT_SETTING, DEFAULT_OUTAGE_MAX_WAIT_S = "VOI_OUTAGE_MAX_WAIT_S", 6 * 3600.0
OUTAGE_RESET_MARGIN_S = 60.0
SESSION_WINDOW_S = 5 * 3600.0
OUTAGE_PAUSE = float("inf")         # retry_delay's answer for it: no retry in the job, run_jobs pauses
UNSTORED_FILE = "elicit_unstored.jsonl"
_HTTP_ERROR_RE = re.compile(r"^http: status (\d+)(?: retry-after (\d+(?:\.\d+)?)s)?")
# errors of the member's environment, not of one call: a retry cannot help and
# the member's pending slots are cancelled. HTTP 401/402/404 (auth, credit,
# unknown model id), a missing claude executable, a zero-usage CLI exit of
# API status 401/402/403/404 (claude_cli.zero_usage_error: auth, billing,
# permission, unknown model id) or a CLI that exits because it is not logged
# in (claude_cli.AUTH_PATTERN, with or without a zero-usage envelope).
_HALT_MEMBER_RE = re.compile(
    r"^http: status 40[124]\b"
    r"|^cli: 'claude' executable not found"
    r"|^cli: exit \d+ \(zero-usage, api 40[1-4]\)"
    r"|^cli: (?:exit \d+|usage-limit)\b[^:]*: .*(?:" + claude_cli.AUTH_PATTERN + ")",
    re.IGNORECASE | re.DOTALL)
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


def usage_limit(error: str | None) -> bool:
    """A usage-limit outage result (claude_cli.is_usage_limit, the one test
    health and the report macros apply to stored rows too): the CLI exited
    without a model call, nothing was billed. A zero-usage exit of another
    API status, or one that names a login or key problem, is not one."""
    return claude_cli.is_usage_limit(error)


def paid_attempts(attempts: list[dict]) -> list[dict]:
    """The attempts of a slot that are elicitation attempts (a zero-usage
    outage result is not one and is never stored)."""
    return [a for a in attempts if not usage_limit(a["error"])]


# failure classes that never reached a model: at zero recorded cost such a
# result says nothing about the usage limit and does not reset the streak
_UNBILLED_PREFIXES = ("http", "provider", "cli", "api")


def billed(attempts: list[dict]) -> bool:
    """Whether a slot's result came from a model call: an attempt that was
    parsed (valid, or a json/schema/constraint/fit failure: the model
    answered) or that recorded a cost. False for a run of unbilled failures
    (http 401/429/5xx, a transport error, a CLI that did not run)."""
    return any(a["error"] is None or a["cost"] > 0
               or a["error"].split(":", 1)[0] not in _UNBILLED_PREFIXES for a in attempts)


def render_prompt(template: string.Template, sc) -> str:
    """Substitute $title $agent $decision $theta_definition $instrument
    $context (empty string when the scenario has no context). A template
    naming any other field (e.g. $decision_context, which only a
    decision-stage template renders) is refused."""
    fields = {f: (sc[f] if sc[f] is not None else "") for f in TEMPLATE_FIELDS}
    try:
        return template.substitute(fields)
    except KeyError as ex:
        raise SystemExit(f"scenario-stage template uses ${ex.args[0]}: it renders only "
                         f"{', '.join('$' + f for f in TEMPLATE_FIELDS)}") from None


def render_decision_prompt(template: string.Template, sc, decision_context: str) -> str:
    """Substitute $agent $decision $theta_definition $decision_context only:
    a decision-stage template that names the instrument, the scenario
    context or the title is refused, so the decision-level numbers cannot
    be contaminated by the rung."""
    fields = {f: (sc[f] if sc[f] is not None else "") for f in DECISION_FIELDS}
    fields["decision_context"] = decision_context
    try:
        return template.substitute(fields)
    except KeyError as ex:
        raise SystemExit(f"decision-stage template uses ${ex.args[0]}: it renders only "
                         f"{', '.join('$' + f for f in DECISION_FIELDS)} and $decision_context"
                         " (no $instrument, $context or $title)") from None


def prompt_hash(prompt: str) -> str:
    return db.sha256(SYSTEM_PROMPT + "\n---\n" + prompt)


# --- one elicitation job (reject -> one retry -> mark invalid) --------------

def failed_attempt(error: str) -> dict:
    return {"raw": "", "error": error, "clean": None, "fits": None, "cost": 0.0}


def parse_payload(obj, model_kind: str = db.BINARY_KIND,
                  names: list[str] | None = None) -> tuple[dict | None, dict | None, str | None]:
    """Validate and fit one parsed JSON answer under the protocol's model
    kind. Returns (rows, fits, error): rows[name] = {p5, p50, p95, unit,
    reasoning} and fits[name] a FitResult, one per stored parameter of that
    kind (db.param_names, or the stage's `names` under a staged binary
    protocol), in storage order."""
    if db.normalize_model_kind(model_kind) == db.GAUSSIAN_KIND:
        clean, err = gauss_fit.validate_gauss_payload(obj)
        if clean is None:
            return None, None, err
        return gauss_fit.fit_gauss(clean)
    clean, err = validate_payload(obj, names)
    if clean is None:
        return None, None, err
    fits, err = fit_all(clean)
    return (clean, fits, None) if fits is not None else (None, None, err)


def attempt_once(call, prompt: str, model: str, model_kind: str = db.BINARY_KIND,
                 names: list[str] | None = None) -> dict:
    """One provider call, parsed, validated and fitted under the protocol's
    model kind (and the stage's parameter `names`). An exception escaping the
    provider becomes an attempt with error 'provider: <Type>: <msg>', so one
    bad call never aborts the run or discards completed paid work."""
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
            clean, fits, err = parse_payload(obj, model_kind, names)
    # without an envelope (a paid CLI exit 1, e.g. a max-output-tokens stop)
    # the raw response still records the cost
    cost = float(envelope.get("total_cost_usd") or 0.0) if envelope else db.envelope_cost(raw)
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
    timed out or killed by a signal). OUTAGE_PAUSE (infinite): a usage-limit
    outage, no retry in the job either; run_jobs pauses the run and re-plans
    the slot. 0: retry at once (json/schema/constraint/fit failures and
    other provider errors). Positive: http 429, 5xx and transport errors,
    using the server's Retry-After (clamped to MAX_RETRY_DELAY_S) when the
    provider recorded one, else TRANSPORT_RETRY_DELAY_S."""
    if error is None or halts_member(error) or rejected_request(error):
        return None
    if usage_limit(error):
        return OUTAGE_PAUSE
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
               stop: threading.Event | None = None, model_kind: str = db.BINARY_KIND,
               names: list[str] | None = None) -> list[dict]:
    """Up to two attempts through one provider, retried per retry_delay().
    Each attempt dict: raw, error, clean, fits, cost. A clamped Retry-After
    is recorded in the first attempt's error. `stop` (set by run_jobs once
    its main thread is interrupted) skips the retry, and cuts its backoff
    short, so no call is launched after Ctrl-C. model_kind selects the
    validation and fitting of the answer (binary | gaussian); names, the
    parameters a stage of a staged protocol asks for."""
    attempts = [attempt_once(call, prompt, model, model_kind, names)]
    delay = retry_delay(attempts[0]["error"])
    if delay is None or not math.isfinite(delay):   # never, or the run's outage pause
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
    attempts.append(attempt_once(call, prompt, model, model_kind, names))
    return attempts


def store_attempts(con, scenario_id, protocol_id, member, repeat_ix, phash, attempts,
                   stage: str | None = None):
    """Insert every attempt (raw response always kept) and, for a valid one,
    its parameters, in ONE transaction per slot: a failed or interrupted
    write leaves nothing behind and the slot can be stored again. Returns
    True if the slot ended valid. stage: the slot's stage under a staged
    protocol."""
    slot_valid = False
    for att in attempts:
        valid = att["error"] is None
        eid = db.insert_elicitation(con, scenario_id, protocol_id, member["provider"],
                                    member["model"], repeat_ix, phash, att["raw"],
                                    valid, att["error"], stage)
        if valid:
            for name in att["clean"]:   # the protocol's parameter names, in storage order
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
        "stage": job.get("stage"),
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
    label = job_label(job)
    for attempt in (1, 2):
        try:
            return store_attempts(con, job["scenario_id"], protocol_id, job["member"],
                                  job["repeat_ix"], prompt_hash(job["prompt"]), attempts,
                                  job.get("stage"))
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


def job_label(job: dict) -> str:
    """'scenario 3 claude_cli:haiku repeat 1', with the stage (and the group
    of a decision-stage slot) under a staged protocol."""
    where = f"scenario {job['scenario_id']}"
    if job.get("stage"):
        where += f" stage {job['stage']}" + (f" (group {job['group']!r})" if job.get("group") else "")
    return f"{where} {db.member_label(job['member'])} repeat {job['repeat_ix']}"


def n_group_texts(rows) -> int:
    """The number of distinct (agent, decision, theta) texts over scenario
    rows; 1 for one decision."""
    return len({(r["agent"], r["decision"], r["theta_definition"]) for r in rows})


def elicited_scenario_rows(con, protocol_id: int, ids: list[int]) -> dict[int, sqlite3.Row]:
    """{id: scenario row} for the ids that hold a valid elicitation under the
    protocol at any stage (the retired scenarios of a group that the one-
    decision check must include: their text is the one the rows the readers
    pool were elicited for)."""
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    return {r["id"]: r for r in con.execute(
        f"SELECT * FROM scenarios WHERE id IN ({marks}) AND EXISTS (SELECT 1 FROM elicitations e"
        " WHERE e.scenario_id=scenarios.id AND e.protocol_id=? AND e.valid=1)", (*ids, protocol_id))}


def check_group_decision_rows(con, protocol_id: int, gids: list[int], stage: str, value: str,
                              phash: str, key: str) -> None:
    """Refuse a group whose stored valid decision rows (on any of its
    scenarios, retired ones included) were rendered from another prompt than
    the group renders now. The protocol's template and decision contexts are
    immutable, so a different prompt hash means the group's agent, decision
    or theta text changed since: eliciting again would put two decisions'
    rows in one pool (the readers find them by the group)."""
    marks = ",".join("?" * len(gids))
    clause, args = db.stage_clause(stage)
    n, other = con.execute(
        f"SELECT COUNT(*), MIN(prompt_hash) FROM elicitations e WHERE scenario_id IN ({marks})"
        f" AND protocol_id=? AND valid=1 AND prompt_hash<>?{clause}",
        (*gids, protocol_id, phash, *args)).fetchone()
    if n:
        raise SystemExit(
            f"stage {stage}: group {value!r} (scenarios {gids}) already holds {n} valid decision"
            f" row(s) elicited for a different agent / decision / theta text (prompt hash"
            f" {other[:12]} vs {phash[:12]} now): not one decision. Give the changed scenarios a new"
            f" {key} value, or start a new voi.db")


def plan_staged_jobs(con, study: Study, prot, stages: list[dict], members: list[dict], selector: str,
                     k_override: int | None, stage: str | None) -> list[dict]:
    """Pending slots of a staged protocol: the group stage once per scenario
    group, then the scenario stage per scenario. The group is the DB's
    (db.scenario_group_ids: every scenario with the group value, retired ones
    included), not the selection: the decision rows are stored on the
    group's representative (its lowest id) and a repeat they fill is done for
    every selection, so a partial --scenarios or a representative that left
    scenarios.json never elicits a second set. Every staged plan, whichever
    --stage, checks that every selected scenario carries the group_key value,
    that the group's scenarios (its active ones in the DB, the selected ones
    and its retired ones holding a valid elicitation under the protocol at
    either stage, whose text is what those rows were elicited for) share the
    agent, decision and theta text, that the stage's decision_contexts has an
    entry per group and that the decision rows the group already holds were
    rendered from that text (check_group_decision_rows). A whole group
    renamed under a new decision text after either stage is refused: its
    retired rows would otherwise be pooled and ranked with the new decision's
    p, B, K. A job carries its stage and the stage's parameter names;
    stage=NAME plans that stage only."""
    gstage, sstage = db.group_stage(stages), db.scenario_stage(stages)
    if stage is not None and stage not in (gstage["name"], sstage["name"]):
        raise SystemExit(f"--stage {stage!r}: protocol {prot['name']} has stages"
                         f" {[gstage['name'], sstage['name']]}")
    scenarios = db.get_scenarios(con, selector)
    key = gstage["group_key"]
    missing = [sc["id"] for sc in scenarios if db.scenario_group_value(sc, key) is None]
    if missing:
        raise SystemExit(f"staged protocol {prot['name']}: scenarios {missing} carry no {key} value;"
                         " every scenario of a staged protocol must belong to a group")
    groups: dict[str, list] = {}
    for sc in scenarios:
        groups.setdefault(db.scenario_group_value(sc, key), []).append(sc)
    active: dict[str, dict[int, sqlite3.Row]] = {}   # group value -> its active scenarios
    for r in db.get_scenarios(con, "all"):
        value = db.scenario_group_value(r, key)
        if value is not None:
            active.setdefault(value, {})[r["id"]] = r
    template = string.Template((study.root / gstage["template_path"]).read_text())
    contexts = gstage.get("decision_contexts", {})
    jobs = []
    for value, rows in sorted(groups.items()):
        gids = db.scenario_group_ids(con, key, rows[0]["id"])
        checked = {**active.get(value, {}), **{r["id"]: r for r in rows}}
        retired = elicited_scenario_rows(con, prot["id"], [g for g in gids if g not in checked])
        checked.update(retired)
        n_texts = n_group_texts(checked.values())
        if n_texts > 1:
            raise SystemExit(
                f"stage {gstage['name']}: group {value!r} (scenarios {sorted(checked)}) mixes {n_texts}"
                " different agent / decision / theta texts: not one decision"
                + (f" (scenarios {sorted(retired)} are retired rows holding valid elicitations under"
                   f" {prot['name']}; give the changed scenarios a new {key} value, or start a new voi.db)"
                   if retired else ""))
        if value not in contexts:
            raise SystemExit(f"stage {gstage['name']}: no decision_contexts entry for group {value!r}"
                             f" (groups: {sorted(groups)})")
        prompt = render_decision_prompt(template, rows[0], contexts[value])
        check_group_decision_rows(con, prot["id"], gids, gstage["name"], value, prompt_hash(prompt), key)
        if stage not in (None, gstage["name"]):
            continue
        rep_id = min(gids)
        for m in members:
            done = db.valid_repeats(con, gids, prot["id"], m["provider"], m["model"], gstage["name"])
            for rix in range(effective_k(m, k_override)):
                if rix not in done:
                    jobs.append({"scenario_id": rep_id, "member": m, "repeat_ix": rix,
                                 "prompt": prompt, "stage": gstage["name"],
                                 "names": list(gstage["params"]), "group": value})
    if stage in (None, sstage["name"]):
        template = string.Template((study.root / sstage["template_path"]).read_text())
        for sc in scenarios:
            prompt = render_prompt(template, sc)
            for m in members:
                done = db.valid_repeats(con, sc["id"], prot["id"], m["provider"], m["model"], sstage["name"])
                for rix in range(effective_k(m, k_override)):
                    if rix not in done:
                        jobs.append({"scenario_id": sc["id"], "member": m, "repeat_ix": rix,
                                     "prompt": prompt, "stage": sstage["name"],
                                     "names": list(sstage["params"])})
    return jobs


def k_label(member: dict, k_override: int | None) -> str:
    k = effective_k(member, k_override)
    if k == member["k_repeats"]:
        return f"k={k}"
    return f"k={k} (override of {member['k_repeats']})"


def plan_jobs(con, study: Study, protocol_id: int, scenarios: str | None, k_override: int | None,
              members_filter: set[str] | None, warn: bool = True,
              stage: str | None = None) -> tuple[list[dict], list[dict]]:
    """Pending slots for every (selected) member over the selected scenarios.
    scenarios=None uses the protocol's 'scenarios' selector; an explicit
    selector overrides a scoped protocol with a printed warning (warn=False
    keeps the second, real-DB plan of main quiet). Returns (members, jobs);
    a job is {scenario_id, member, repeat_ix, prompt} (+ stage, names and,
    for a decision-stage slot, group under a staged protocol; stage=NAME
    plans one stage of such a protocol)."""
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
    stages = db.protocol_stages(prot)
    if stages is not None:
        return members, plan_staged_jobs(con, study, prot, stages, members, selector, k_override, stage)
    if stage is not None:
        raise SystemExit(f"--stage: protocol {prot['name']} has no stages")
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


def dry_run_staged(prot, stages: list[dict], members, jobs, k_override: int | None = None,
                   stage: str | None = None):
    """The dry run of a staged protocol: pending slots per stage and member
    (over groups for the decision stage, scenarios for the instrument stage)
    and the first pending prompt of each stage; a stage --stage left out is
    marked as not planned."""
    print(f"DRY RUN: protocol {prot['name']} (model {db.protocol_model_kind(prot)}, "
          f"stages {' + '.join(s['name'] for s in stages)}, hash {prot['template_hash'][:12]}, "
          f"scenarios {db.protocol_selector(prot)})")
    for st in stages:
        grouped = "group_key" in st
        sjobs = [j for j in jobs if j["stage"] == st["name"]]
        print(f"  stage {st['name']} (template {st['template_path']}, params {', '.join(st['params'])}"
              + (f", group_key {st['group_key']}" if grouped else "") + "):")
        if stage is not None and st["name"] != stage:
            print(f"    not planned (--stage {stage})")
            continue
        for m in members:
            pending = [j for j in sjobs if db.member_label(j["member"]) == db.member_label(m)]
            if grouped:
                units = sorted({j["group"] for j in pending})
                where = f"{len(units)} groups" + (f" ({', '.join(units)})" if units else "")
            else:
                sids = sorted({j["scenario_id"] for j in pending})
                where = f"{len(sids)} scenarios" + (f" (ids {sids[0]}..{sids[-1]})" if sids else "")
            print(f"    member {db.member_label(m)} ({k_label(m, k_override)}): {len(pending)} pending"
                  f" slots over {where}")
    for st in stages:
        sjobs = [j for j in jobs if j["stage"] == st["name"]]
        if sjobs:
            first = sjobs[0]
            where = (f"group {first['group']!r}, representative scenario {first['scenario_id']}"
                     if first.get("group") else f"scenario {first['scenario_id']}")
            print(f"\nfirst pending prompt of stage {st['name']} ({where}, {len(first['prompt'])} chars,"
                  f" hash {prompt_hash(first['prompt'])[:12]}):\n")
            print(first["prompt"])
    print(f"\n{len(jobs)} slots would be elicited; no provider was called.")


def dry_run(con, prot, members, jobs, k_override: int | None = None, stage: str | None = None):
    """Render prompts and list pending slots per member; call nothing."""
    stages = db.protocol_stages(prot)
    if stages is not None:
        return dry_run_staged(prot, stages, members, jobs, k_override, stage)
    print(f"DRY RUN: protocol {prot['name']} (model {db.protocol_model_kind(prot)}, "
          f"template {prot['template_path']}, hash {prot['template_hash'][:12]}, "
          f"scenarios {db.protocol_selector(prot)})")
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


def member_mean_cost(con, member: dict, kind: str = db.BINARY_KIND) -> tuple[float, int] | None:
    """(mean recorded USD cost per billed attempt, billed attempts) of one
    member over the protocols of the given model kind in the study; None
    when the member has no such attempts. A usage-limit outage row (a
    zero-usage CLI exit stored before v2.3, claude_cli.is_usage_limit) made
    no model call and is left out, as tables.billed_attempts does: counted,
    it understated sim2real's g001 estimates by 13-21%. Kinds are not
    pooled: the Gaussian prompt is twice the binary one and asks for twelve
    reasoned answers, so a binary mean would understate a first g001 batch
    by about half."""
    kind = db.normalize_model_kind(kind)
    rows = con.execute(
        "SELECT e.raw_response, e.error, p.model_kind FROM elicitations e"
        " JOIN protocols p ON p.id=e.protocol_id WHERE e.provider=? AND e.model=?",
        (member["provider"], member["model"])).fetchall()
    rows = [r for r in rows if db.normalize_model_kind(r["model_kind"]) == kind
            and not claude_cli.is_usage_limit(r["error"], r["raw_response"])]
    if not rows:
        return None
    return sum(db.envelope_cost(r["raw_response"]) for r in rows) / len(rows), len(rows)


def print_plan(con, prot, members, jobs):
    """Slots per member and the estimated cost (slots x mean stored cost per
    billed attempt of that member under protocols of the same model kind in
    this study, 'unknown' without such history)."""
    kind = db.protocol_model_kind(prot)
    stages = db.protocol_stages(prot)
    print(f"plan: protocol {prot['name']}, {len(jobs)} pending slots "
          "(one attempt each; a failed attempt is retried once)")
    total, unknown = 0.0, False
    for m in members:
        mine = [j for j in jobs if db.member_label(j["member"]) == db.member_label(m)]
        n = len(mine)
        by_stage = ""
        if stages is not None:
            by_stage = " (" + ", ".join(
                f"{s['name']} {sum(1 for j in mine if j['stage'] == s['name'])}" for s in stages) + ")"
        est = member_mean_cost(con, m, kind)
        if est is None:
            cost, unknown = (f"unknown (no stored attempts of this member under a {kind} protocol"
                             " in this study)"), True
        else:
            total += n * est[0]
            cost = (f"${n * est[0]:.2f} (mean ${est[0]:.4f}/attempt over {est[1]} stored"
                    f" {kind} attempts)")
        print(f"  {db.member_label(m)}: {n} slots{by_stage}, estimated cost {cost}")
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

def utc_now() -> datetime:
    return datetime.now(UTC)


def outage_pause(error: str | None, now: datetime, fixed_s: float) -> tuple[float, str]:
    """(seconds, note) of one usage-limit pause: until OUTAGE_RESET_MARGIN_S
    after the reset the CLI's message names (claude_cli.usage_limit_reset)
    when that is at most SESSION_WINDOW_S away, else fixed_s (no reset time,
    a weekly limit, or a stated reset already past, which reads as
    tomorrow's)."""
    reset = claude_cli.usage_limit_reset(error, now)
    if reset is not None:
        wait = (reset - now).total_seconds()
        if wait <= SESSION_WINDOW_S:
            note = f" until {OUTAGE_RESET_MARGIN_S:g}s after the stated reset ({reset:%H:%M} {reset.tzinfo})"
            return float(round(wait + OUTAGE_RESET_MARGIN_S)), note
    return fixed_s, ""


def outage_summary(outage: dict) -> str:
    """The run summary's clause about usage-limit outages ('' when none)."""
    if not outage["results"]:
        return ""
    text = (f", {outage['results']} zero-usage usage-limit result(s) not stored as attempts"
            f" ({outage['pauses']} pause(s), {outage['waited_s']:g}s paused)")
    if outage["gave_up"]:
        text += (f"; gave up after {outage['pauses']} pauses with {outage['unresolved']} slot(s) still"
                 " pending: re-run to resume")
    return text


def run_jobs(con, study: Study, protocol_id: int, jobs: list[dict], workers: int,
             sleep=None, now=None) -> tuple[int, float, int, dict]:
    """Submit the jobs to a thread pool and store each result as it
    completes. Returns (valid slots, total cost, cancelled slots, outage
    summary {"results": zero-usage results seen, "pauses", "waited_s": the
    seconds paused, "gave_up": the run gave up on at least one member,
    "unresolved": the slots it left pending there}).

    Safety rules: (1) a member has its pending slots cancelled (fix the key,
    credits or model id and re-run to resume) when an attempt ends in an
    error of its environment (halts_member: http 401/402/404, a CLI that
    cannot run, a zero-usage CLI exit of api 401-404), when its rejected
    requests (http 400/403, unbilled, stored invalid without a retry) name
    the key or reach a second distinct scenario, or after
    CLI_TIMEOUTS_TO_HALT consecutive CLI timeouts; (2) a DB write that fails
    is retried once, then the attempts are spilled to
    <study>/elicit_unstored.jsonl and the run stops; (3) on any exception in
    this thread (Ctrl-C included) the pending jobs are cancelled, no retry is
    launched, the running calls are awaited and stored, and the exception is
    re-raised; a further Ctrl-C during that wait or salvage is reported and
    ignored, and the salvage is idempotent (a slot the interrupt caught
    between its commit and its bookkeeping is recognised in the DB by its
    own final attempt, a row holding that raw response and error written
    after its batch was submitted, so a re-planned slot's earlier paid
    failure never masks its re-run). Paid work is never discarded.

    Usage-limit outages (4), per member: a zero-usage result (usage_limit:
    the CLI exited without a model call, nothing billed) is never stored
    and its slot is re-planned. The jobs run in batches: the first batch is
    every job; a batch's re-planned slots form the next one. After
    OUTAGE_STREAK consecutive zero-usage results of one member across
    workers that member is held: its not-yet-started slots are held back
    (cancelled futures, re-planned), its running calls finish, and every
    other member goes on (a model-specific limit, or one limited member
    next to a slower healthy one, never stalls or cancels the others'
    slots). Batches keep running the slots of members not held; once only
    held members' slots are left the run pauses (outage_pause of each held
    member's latest limit message, the shortest: until just after the
    reset the CLI's message names, else VOI_OUTAGE_SLEEP_S; `sleep` and the
    clock `now` are injectable) and probes with a batch of one slot per
    held member, the first in plan order; a billed probe (stored like any
    slot, valid or not) releases that member's slots, a zero-usage probe
    keeps it held and the run pauses again. Each member's wait budget is
    the planned pause time since its last billed result: once it reaches
    VOI_OUTAGE_MAX_WAIT_S the run gives up on that member (its pending
    slots count as cancelled and are pending on the next run; the other
    members go on) and the last pause is cut to what is left. A billed
    result restarts the budget, so one default budget covers every window
    of a long run. The summary's waited_s is the time actually paused (a
    pause cut short by Ctrl-C counts what elapsed). Fewer than
    OUTAGE_STREAK in a row are re-planned at once (each result still counts
    toward the member's streak; only a billed result of that member resets
    it, and after its hold not even that: a call in flight since before
    the hold says nothing about the limit, so a held member always
    pauses). A member halted after a hold has its held-back and re-planned
    slots cancelled, not re-run. `stored` counts the slots whose final
    result is stored: a paid failure stored before a zero-usage retry
    leaves its slot pending."""
    kind = db.protocol_model_kind(
        con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone())
    sleep = sleep or time.sleep   # resolved here, so a test can patch time.sleep for the CLI path
    now = now or utc_now
    fixed_pause_s = seconds_setting(OUTAGE_SLEEP_SETTING, DEFAULT_OUTAGE_SLEEP_S)
    max_wait_s = seconds_setting(OUTAGE_MAX_WAIT_SETTING, DEFAULT_OUTAGE_MAX_WAIT_S)
    stop = threading.Event()   # set on interrupt: a worker then launches no retry
    pool = cf.ThreadPoolExecutor(workers)
    futures: dict = {}       # every future submitted (all batches) -> its job
    id_floor: dict = {}      # future -> the last elicitation id before its batch was submitted
    handled: set = set()     # futures whose attempts are in the DB or spilled (or were zero-usage)
    stored: set = set()      # slot keys whose final result is in the DB or the spill file (a slot once)
    halted: set[str] = set()
    rejected: dict[str, set[int]] = {}   # member -> scenarios whose request was rejected (400/403)
    timeouts: dict[str, int] = {}        # member -> consecutive CLI timeouts
    n_valid, total_cost, n_cancelled, n_done = 0, 0.0, 0, 0
    outage = {"results": 0, "pauses": 0, "waited_s": 0.0, "gave_up": False, "unresolved": 0}
    # usage-limit outages are tracked per member: one member's limit (a model-specific
    # limit, or a slower healthy member next to a limited one) never holds another's slots
    streak: dict[str, int] = {}       # member -> consecutive zero-usage results, across workers
    last_limit: dict[str, str] = {}   # member -> its latest usage-limit error (names the reset)
    waited: dict[str, float] = {}     # member -> seconds paused (planned) since its last billed result
    held: set = set()         # futures cancelled by an outage hold: re-planned, not 'cancelled'
    replan: set = set()       # the batch's futures with a zero-usage result: re-planned
    queue: list[dict] = []    # slots not yet submitted (held for the next batch)

    def slot_key(job: dict) -> tuple:
        return (job["scenario_id"], job["member"]["provider"], job["member"]["model"],
                job["repeat_ix"], job.get("stage") or "")

    def label_of(job: dict) -> str:
        return db.member_label(job["member"])

    def limited(label: str) -> bool:
        """The member is held by an outage: OUTAGE_STREAK zero-usage results
        in a row, no billed result since."""
        return streak.get(label, 0) >= OUTAGE_STREAK

    def submit(batch: list[dict]) -> list:
        # rows above this id are written after the batch was submitted: the salvage
        # uses it to recognise a slot whose commit landed just before an interrupt.
        # One floor per batch (nothing is written between its submissions), and a
        # re-planned slot's earlier batch stored its paid failure below the floor
        floor = con.execute("SELECT COALESCE(MAX(id), 0) FROM elicitations").fetchone()[0]
        new = []
        for j in batch:
            fut = pool.submit(elicit_job, get_provider(j["member"]["provider"]), j["prompt"],
                              j["member"]["model"], stop=stop, model_kind=kind, names=j.get("names"))
            futures[fut] = j
            id_floor[fut] = floor
            new.append(fut)
        return new

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

    def store(fut, attempts, final: bool = True) -> bool:
        # a slot counts as handled once its attempts are in the DB or in the
        # spill file; an interrupt in the middle of the write leaves it
        # unhandled so the salvage below stores it again after the rollback.
        # `stored` counts slots, not writes, and only a final result: a
        # re-planned slot stores its paid failure (final=False: the slot is
        # still pending) and, later, its re-run
        try:
            ok = store_or_spill(con, study.root, protocol_id, futures[fut], attempts)
        except StoreFailed:
            handled.add(fut)
            if final:
                stored.add(slot_key(futures[fut]))   # in the spill file
            raise
        handled.add(fut)
        if final:
            stored.add(slot_key(futures[fut]))
        return ok

    def stored_by_this_run(fut, attempts: list[dict]) -> bool:
        """Whether THIS future's attempts are already in the DB (the interrupt
        landed between its commit and handled.add): a row of its slot written
        after its batch was submitted that holds its final attempt (raw
        response and error). The attempt identity, not the slot key alone: a
        re-planned slot's earlier paid failure (stored by an earlier batch,
        below the floor, and a different response) never masks its re-run."""
        job, last = futures[fut], attempts[-1]
        clause, args = db.stage_clause(job.get("stage"))
        return con.execute(
            "SELECT 1 FROM elicitations e WHERE id>? AND scenario_id=? AND protocol_id=? AND provider=?"
            f" AND model=? AND repeat_ix=? AND prompt_hash=? AND raw_response=? AND error IS ?{clause}"
            " LIMIT 1",
            (id_floor[fut], job["scenario_id"], protocol_id, job["member"]["provider"],
             job["member"]["model"], job["repeat_ix"], prompt_hash(job["prompt"]), last["raw"],
             last["error"], *args)).fetchone() is not None

    def hold_pending(label: str) -> list:
        """An outage hold of one member: cancel its not-yet-started futures
        (their slots are re-planned, not cancelled); the other members'
        futures and the queue are left alone."""
        return [f for f, j in futures.items() if label_of(j) == label and not f.done() and f.cancel()]

    def cancel_pending(member: str | None = None) -> int:
        """Cancel the not-yet-started futures (of one member, or all) and drop
        the same slots from the queue; returns how many slots that was, the
        member's slots awaiting a re-plan (held back by a pause, or with a
        zero-usage result) included: run_batch drops those of a halted
        member. The queue's are counted in n_cancelled here, the futures
        when the batch loop sees them cancelled, the re-plan ones at the
        end of the batch."""
        nonlocal n_cancelled

        def mine(job: dict) -> bool:
            return member is None or db.member_label(job["member"]) == member

        n = sum(1 for f, j in futures.items() if mine(j) and not f.done() and f.cancel())
        kept = [j for j in queue if not mine(j)]
        n_cancelled += len(queue) - len(kept)
        n += len(queue) - len(kept)
        queue[:] = kept
        n += sum(1 for f in held | replan if mine(futures[f]))
        return n

    def salvage() -> int:
        """Store every finished slot not yet handled; a slot this run already
        committed (interrupt between commit and handled.add) is only counted,
        a zero-usage result is counted in the outage summary and never
        stored. Idempotent, so a repeated call after a further Ctrl-C is
        harmless."""
        nonlocal n_valid, total_cost
        con.rollback()
        salvaged = 0
        for f in futures:
            if f.done() and not f.cancelled() and f not in handled:
                result = result_of(f)
                attempts = paid_attempts(result)
                final = not usage_limit(result[-1]["error"])   # else the slot stays pending
                if not final:
                    outage["results"] += 1
                if not attempts:   # a zero-usage outage result: nothing to store
                    handled.add(f)
                    continue
                if stored_by_this_run(f, attempts):
                    handled.add(f)
                    if final:
                        stored.add(slot_key(futures[f]))
                    n_valid += attempts[-1]["error"] is None
                else:
                    try:
                        n_valid += store(f, attempts, final)
                    except StoreFailed as err:
                        print(err)
                    salvaged += 1
                total_cost += sum(a["cost"] for a in attempts)
        return salvaged

    def run_batch(batch: list[dict]) -> list[dict]:
        """Submit one batch and consume its results; returns the slots to
        re-plan (zero-usage results, and the slots held back by an outage
        hold), in plan order, less those of a member halted meanwhile
        (cancelled)."""
        nonlocal n_valid, total_cost, n_cancelled, n_done
        submitted = submit(batch)
        replan.clear()
        held.clear()
        holding: set[str] = set()   # members held in this batch: no later result of theirs resets the streak
        for fut in cf.as_completed(submitted):
            j = futures[fut]
            if fut.cancelled():
                if fut not in held:
                    n_cancelled += 1
                continue
            attempts = result_of(fut)
            paid = paid_attempts(attempts)
            total_cost += sum(a["cost"] for a in paid)
            label = db.member_label(j["member"])
            error = attempts[-1]["error"]
            if usage_limit(error):
                # not an elicitation attempt: never stored, the slot is re-planned; a
                # paid attempt before it (a retry that ran into the outage) is stored
                if paid:
                    store(fut, paid, final=False)
                else:
                    handled.add(fut)
                outage["results"] += 1
                streak[label] = streak.get(label, 0) + 1
                last_limit[label] = error
                replan.add(fut)
                print(f"{job_label(j)}: usage limit ({error[:120]}); nothing billed, not stored,"
                      f" re-planned ({streak[label]} zero-usage result(s) of {label} in a row)")
                if streak[label] == OUTAGE_STREAK:
                    holding.add(label)
                    now_held = hold_pending(label)
                    held.update(now_held)
                    print(f"usage-limit outage: {label}: {streak[label]} consecutive zero-usage results"
                          f" across workers; its dispatching stopped, {len(now_held)} not-yet-started"
                          " slot(s) of it held back for the pause (the other members go on)")
                continue
            # an unbilled failure (http 401, transport) says nothing about the limit, nor
            # does a billed answer of a call in flight since before the member's hold; a
            # billed result ends the member's outage and restarts its wait budget
            if billed(paid) and label not in holding:
                streak.pop(label, None)
                waited.pop(label, None)
            ok = store(fut, paid)
            n_valid += ok
            n_done += 1
            status = "ok" if ok else f"INVALID ({error})"
            print(f"[{n_done}/{len(jobs)}] {job_label(j)}: {status}")
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
        again, dropped = [], 0
        for f in submitted:
            if f in replan or f in held:
                if db.member_label(futures[f]["member"]) in halted:
                    dropped += 1   # halted after the hold: its held-back slots are cancelled
                else:
                    again.append(futures[f])
        n_cancelled += dropped
        replan.clear()
        held.clear()
        return again

    def give_up(label: str) -> None:
        """Cancel the pending slots of a member whose outage has used up its
        wait budget; the other members go on."""
        nonlocal n_cancelled
        mine = [j for j in queue if label_of(j) == label]
        queue[:] = [j for j in queue if label_of(j) != label]
        outage["gave_up"] = True
        outage["unresolved"] += len(mine)
        n_cancelled += len(mine)
        n_stored = sum(1 for k in stored if f"{k[1]}:{k[2]}" == label)
        print(f"usage-limit outage: giving up on {label} after {waited[label]:g}s paused since its last"
              f" billed result ({OUTAGE_MAX_WAIT_SETTING}={max_wait_s:g}), with {streak[label]}"
              f" zero-usage results of it in a row; {n_stored} slot(s) of it stored by this run,"
              f" {len(mine)} still pending: re-run to resume once the limit resets")

    def next_pause(members: list[str]) -> tuple[float, str]:
        """(seconds, note) of the next pause: the shortest of the held
        members' pauses (outage_pause of each one's latest limit message),
        each cut to what is left of that member's wait budget."""
        options = []
        for label in members:
            pause, why = outage_pause(last_limit[label], now(), fixed_pause_s)
            left = max_wait_s - waited.get(label, 0.0)
            if pause > left:
                pause, why = left, f" (cut to what is left of {label}'s wait budget)"
            options.append((pause, why))
        return min(options, key=lambda o: o[0])

    try:
        queue[:] = list(jobs)
        probe = False
        while queue:
            if probe:   # one slot of every held member, the first in plan order
                firsts: dict[str, dict] = {}
                for j in queue:
                    firsts.setdefault(label_of(j), j)
                batch = list(firsts.values())
            else:       # every slot of the members no outage holds
                batch = [j for j in queue if not limited(label_of(j))]
            probe = False
            if batch:
                taken = {id(j) for j in batch}
                queue[:] = [j for j in queue if id(j) not in taken]
                queue[:0] = run_batch(batch)   # the re-planned slots go first
                continue
            # only slots of held members are left: give up on those whose wait budget
            # is spent, pause for the rest, then probe each with one call
            members = sorted({label_of(j) for j in queue})
            for label in members:
                if waited.get(label, 0.0) >= max_wait_s:
                    give_up(label)
            members = [m for m in members if waited.get(m, 0.0) < max_wait_s]
            if not members:
                break
            pause, why = next_pause(members)
            for label in members:
                waited[label] = waited.get(label, 0.0) + pause   # the budget counts the planned pause
            outage["pauses"] += 1
            print(f"usage-limit outage: pausing {pause:g}s{why} (pause {outage['pauses']}; "
                  + ", ".join(f"{m} {waited[m]:g}s of {max_wait_s:g}s" for m in members)
                  + f") with {len(queue)} slot(s) pending, then probing with one call per held member")
            started, finished = time.monotonic(), False
            try:
                sleep(pause)
                finished = True
            finally:   # the summary reports the time paused, a pause cut short by Ctrl-C included
                outage["waited_s"] += pause if finished else round(time.monotonic() - started)
            probe = True
    except BaseException as ex:
        # Ctrl-C, a failed store or any other error here: stop submitting,
        # launch no retry, keep what is paid for
        stop.set()
        pending = cancel_pending()   # the not-yet-started futures and the held-back queue
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
        print(f"{len(stored)} of {len(jobs)} slots stored ({salvaged} after the interruption);"
              " re-run to resume" + outage_summary(outage))
        raise
    pool.shutdown(wait=True)
    return n_valid, total_cost, n_cancelled, outage


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
                              parse_members_filter(args.members), warn=preview, stage=args.stage)
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
    ap.add_argument("--stage", default=None,
                    help="staged protocols: plan and elicit this stage only (default: both)")
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
        dry_run(plan_con, prot, members, jobs, args.k, args.stage)
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

    n_valid, total_cost, n_cancelled, outage = run_jobs(con, study, protocol_id, jobs, args.workers)
    rate = n_valid / len(jobs)
    print(f"\ndone: {n_valid}/{len(jobs)} slots valid ({rate:.1%})"
          + (f", {n_cancelled} cancelled" if n_cancelled else "")
          + f", total elicitation cost ${total_cost:.2f}" + outage_summary(outage))


if __name__ == "__main__":
    main()
