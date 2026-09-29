"""Harness pause on usage-limit outages (spec v2.3, feature E). During a
claude.ai usage-limit window the CLI exits 1 with a zero-usage envelope
(no model call, nothing billed): the provider classifies it, the job never
retries it, run_jobs stores nothing for it, pauses after OUTAGE_STREAK such
results in a row, probes with one call and resumes, or gives up after
OUTAGE_MAX_PAUSES; health and the report macros read legacy rows of that
kind as outages. Fake providers, injected sleep, no CLI, no network."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import threading
import time

import pytest

from tests.test_pipeline import _seed_payload, study  # noqa: F401  (the temporary study fixture)
from voi_rank import db, elicit
from voi_rank.analysis import health, tables
from voi_rank.providers import claude_cli

# the envelope the CLI printed during the 2026-09-29 outage (LEARNINGS), verbatim in shape
LIMIT_ENVELOPE = {"type": "result", "subtype": "success", "is_error": True, "duration_ms": 467,
                  "num_turns": 1, "total_cost_usd": 0, "usage": {"input_tokens": 0, "output_tokens": 0},
                  "result": "You've hit your session limit · resets 4:30am (Europe/Brussels)"}
LIMIT_RAW = json.dumps(LIMIT_ENVELOPE)
LIMIT_ERROR = ("cli: usage-limit (zero-usage exit 1): You've hit your session limit · resets 4:30am"
               " (Europe/Brussels)")
EMPTY_RAW = json.dumps({**LIMIT_ENVELOPE, "result": ""})
PAID_RAW = json.dumps({"result": "", "total_cost_usd": 0.02,
                       "usage": {"input_tokens": 500, "output_tokens": 0}})


# --- classification --------------------------------------------------------------

def test_call_claude_classifies_a_zero_usage_exit(monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        code, out, err = script.pop(0)
        return subprocess.CompletedProcess(cmd, code, out, err)

    monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)
    script = [(1, LIMIT_RAW, ""), (1, EMPTY_RAW, "some stderr"), (1, PAID_RAW, "boom"),
              (1, "", "Not logged in"), (1, "garbage", "x"), (0, LIMIT_RAW, "")]
    envelope, raw, err = claude_cli.call_claude("p", "haiku", "sys")
    assert err == LIMIT_ERROR and raw == LIMIT_RAW and envelope == LIMIT_ENVELOPE
    envelope, raw, err = claude_cli.call_claude("p", "haiku", "sys")   # an empty result, stderr instead
    assert err == "cli: usage-limit (zero-usage exit 1): some stderr" and envelope["result"] == ""
    _, raw, err = claude_cli.call_claude("p", "haiku", "sys")          # billed tokens: an ordinary exit 1
    assert err == "cli: exit 1: boom" and raw == PAID_RAW
    _, raw, err = claude_cli.call_claude("p", "haiku", "sys")
    assert err == "cli: exit 1: Not logged in" and raw == "Not logged in"
    _, _, err = claude_cli.call_claude("p", "haiku", "sys")
    assert err == "cli: exit 1: x"
    envelope, _, err = claude_cli.call_claude("p", "haiku", "sys")     # exit 0 with is_error: as before
    assert err.startswith("cli: is_error: You've hit your session limit")
    assert len(calls) == 6 and all(c[:2] == ["claude", "-p"] for c in calls)
    # the helpers behind it
    assert claude_cli.zero_usage_envelope(LIMIT_RAW) == LIMIT_ENVELOPE
    assert claude_cli.zero_usage_envelope(PAID_RAW) is None
    assert claude_cli.zero_usage_envelope('{"result": "", "total_cost_usd": 0}') is None   # no usage block
    assert claude_cli.zero_usage_envelope("") is None and claude_cli.zero_usage_envelope(None) is None
    assert claude_cli.is_usage_limit(LIMIT_ERROR) and claude_cli.is_usage_limit("cli: exit 1: ", LIMIT_RAW)
    assert not claude_cli.is_usage_limit("cli: exit 1: ", PAID_RAW)
    assert not claude_cli.is_usage_limit("cli: exit 1: ", "")
    assert not claude_cli.is_usage_limit(None, LIMIT_RAW)
    assert not claude_cli.is_usage_limit("json: result parse failed", LIMIT_RAW)


def test_retry_policy_for_a_usage_limit_result():
    good = json.dumps({"parameters": _seed_payload()})
    slept = []

    def seq(*errs):
        it = iter(errs)

        def call(prompt, model, system_prompt):
            e = next(it)
            return ({"result": good}, good, None) if e is None else (LIMIT_ENVELOPE, LIMIT_RAW, e)
        return call

    assert elicit.usage_limit(LIMIT_ERROR) and elicit.retry_delay(LIMIT_ERROR) == elicit.OUTAGE_PAUSE
    assert elicit.OUTAGE_PAUSE == float("inf") and not elicit.halts_member(LIMIT_ERROR)
    assert not elicit.rejected_request(LIMIT_ERROR) and not elicit.cli_timeout(LIMIT_ERROR)
    att = elicit.elicit_job(seq(LIMIT_ERROR, None), "p", "m", sleep=slept.append)
    assert len(att) == 1 and att[0]["error"] == LIMIT_ERROR and att[0]["cost"] == 0.0 and slept == []
    assert att[0]["raw"] == LIMIT_RAW
    assert elicit.paid_attempts(att) == []
    # a paid failure whose retry runs into the outage: the paid attempt is kept
    att = elicit.elicit_job(seq("json: bad", LIMIT_ERROR), "p", "m", sleep=slept.append)
    assert [a["error"] for a in att] == ["json: bad", LIMIT_ERROR]
    assert [a["error"] for a in elicit.paid_attempts(att)] == ["json: bad"]
    # a zero-usage exit that names a login problem is the member's environment error, not an outage
    login = "cli: usage-limit (zero-usage exit 1): Not logged in · Please run /login"
    assert elicit.halts_member(login) and not elicit.usage_limit(login) and elicit.retry_delay(login) is None
    assert not elicit.usage_limit("cli: exit 1: ") and not elicit.usage_limit(None)
    assert elicit.outage_summary({"results": 0, "pauses": 0, "gave_up": False, "unresolved": 0}) == ""


# --- run_jobs ----------------------------------------------------------------------

class Outage:
    """A claude_cli fake for a usage-limit window: every call ends in the
    zero-usage exit while the outage is active (until the harness sleeps,
    which is when the window ends here, or for the first `fail_calls` calls,
    or for ever), the rest answer validly. `sleep` is the injected pause."""

    def __init__(self, seed: dict, fail_calls: int | None = None, ends_on_sleep: bool = True):
        self.seed, self.fail_calls, self.ends_on_sleep = seed, fail_calls, ends_on_sleep
        self.calls: list[str] = []
        self.slept: list[float] = []
        self.active = True
        self.lock = threading.Lock()

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        if self.ends_on_sleep:
            self.active = False

    def get_provider(self, name):
        def call(prompt, model, system_prompt):
            with self.lock:
                self.calls.append(prompt)
                n = len(self.calls)
                limited = self.active if self.fail_calls is None else n <= self.fail_calls
            if limited:
                return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
            text = json.dumps({"parameters": self.seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call


def plan(st, k: int = 1, scenarios: str = "1,2,3,4,5,6,7,8"):
    con = st.connect()
    db.seed_scenarios(con, st.scenarios_json)
    pid = db.get_or_create_protocol(con, st.protocol_path("p001"), st.root)
    _, jobs = elicit.plan_jobs(con, st, pid, scenarios, k, {"claude_cli:haiku"})
    return con, pid, jobs


def rows_of(con) -> list:
    return con.execute("SELECT scenario_id, valid, error FROM elicitations ORDER BY id").fetchall()


def test_outage_pauses_after_the_streak_probes_and_resumes(study, monkeypatch, capsys):  # noqa: F811
    """Zero-usage results until the harness sleeps (the window ends there):
    the fifth in a row holds the not-yet-started slots back, the calls in
    flight finish (zero-usage too), the run sleeps once, the probe is billed
    and the rest follows; every slot ends valid and nothing of the outage
    is stored."""
    outage = Outage(_seed_payload())
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    con, pid, jobs = plan(study)
    assert len(jobs) == 8
    n_valid, cost, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=2,
                                                          sleep=outage.sleep)
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled) == (8, 0) and cost == pytest.approx(0.08)
    # the fifth zero-usage result triggers the hold; the calls already running (or, with an
    # instant fake, already finished) add up to three more, all zero-usage, before the pause
    assert 5 <= summary["results"] <= 8 and summary["pauses"] == 1 and not summary["gave_up"]
    assert summary["unresolved"] == 0 and outage.slept == [elicit.OUTAGE_SLEEP_S] == [300.0]
    assert len(outage.calls) == summary["results"] + 8
    rows = rows_of(con)
    assert len(rows) == 8 and all(r["valid"] == 1 and r["error"] is None for r in rows)
    assert sorted(r["scenario_id"] for r in rows) == list(range(1, 9))
    assert out.count("nothing billed, not stored, re-planned") == summary["results"]
    assert re.search(r"usage-limit outage: 5 consecutive zero-usage results across workers; dispatching"
                     r" stopped, [0-3] not-yet-started slot\(s\) held back for the pause", out)
    assert re.search(r"usage-limit outage: pausing 300s \(pause 1/12\) with 8 slot\(s\) pending, then probing"
                     r" with one call", out)
    assert out.count("usage-limit outage: pausing") == 1 and "giving up" not in out
    assert re.search(r"\[8/8\] scenario \d claude_cli:haiku repeat 0: ok", out) and "[9/8]" not in out
    assert elicit.outage_summary(summary) == (f", {summary['results']} zero-usage usage-limit result(s) not"
                                              " stored as attempts (1 pause(s) of 300s)")
    # the resumed run has nothing left to do
    _, _, again = plan(study)
    assert again == []
    con.close()


def test_a_blip_below_the_streak_is_replanned_without_a_pause(study, monkeypatch, capsys):  # noqa: F811
    outage = Outage(_seed_payload(), fail_calls=2)
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    con, pid, jobs = plan(study)
    n_valid, _, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=2, sleep=outage.sleep)
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled) == (8, 0) and outage.slept == [] and len(outage.calls) == 10
    assert summary == {"results": 2, "pauses": 0, "gave_up": False, "unresolved": 0}
    assert len(rows_of(con)) == 8 and "dispatching stopped" not in out and "pausing" not in out
    assert out.count("nothing billed, not stored, re-planned") == 2
    con.close()


def test_outage_gives_up_after_max_pauses_with_everything_stored(study, monkeypatch, capsys):  # noqa: F811
    seed = _seed_payload()
    outage = Outage(seed, ends_on_sleep=False)   # the window never ends
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    con, pid, jobs = plan(study)
    n_valid, cost, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=3,
                                                          sleep=outage.sleep)
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled, cost) == (0, 8, 0.0)
    # the batch's zero-usage results (5 to 8: the fifth holds the rest back) plus one probe per pause
    assert summary["pauses"] == 12 and summary["gave_up"] and summary["unresolved"] == 8
    assert 5 + 12 <= summary["results"] <= 8 + 12 and len(outage.calls) == summary["results"]
    assert outage.slept == [300.0] * 12
    assert rows_of(con) == []                                              # nothing billed, nothing stored
    assert re.search(r"usage-limit outage: giving up after 12 pauses of 300s \(\d+ zero-usage results in a"
                     r" row\); 0 slot\(s\) of this run stored, 8 still pending: re-run to resume once the"
                     r" limit resets", out)
    assert out.count("usage-limit outage: pausing") == 12
    assert elicit.outage_summary(summary).endswith("; gave up after 12 pauses with 8 slot(s) still pending:"
                                                   " re-run to resume")
    # the limit lifts: the next run fills every slot, through main and its summary line
    fine = Outage(seed, fail_calls=0)
    monkeypatch.setattr(elicit, "get_provider", fine.get_provider)
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
                 "--k", "1", "--scenarios", "1,2,3,4,5,6,7,8", "--yes", "--workers", "3"])
    out = capsys.readouterr().out
    assert "done: 8/8 slots valid (100.0%), total elicitation cost $0.08\n" in out
    assert len(rows_of(con)) == 8 and len(fine.calls) == 8
    con.close()


def test_main_summary_counts_the_outage_and_stores_paid_attempts_before_it(study, monkeypatch, capsys):  # noqa: F811
    """The CLI path (OUTAGE_SLEEP_S is a module constant, 0 here): the first
    call is a paid JSON failure whose immediate retry runs into the outage;
    the paid attempt is stored, the zero-usage results are not, the summary
    line counts them, and health sees no outage row."""
    seed = _seed_payload()
    outage = Outage(seed)
    inner = outage.get_provider("claude_cli")
    monkeypatch.setattr(elicit, "OUTAGE_SLEEP_S", 0.0)
    monkeypatch.setattr(elicit.time, "sleep", outage.sleep)
    calls = []

    def get_provider(name):
        def call(prompt, model, system_prompt):
            calls.append(prompt)
            if len(calls) == 1:
                return {"result": "not json", "total_cost_usd": 0.03}, '{"result": "not json"}', None
            return inner(prompt, model, system_prompt)
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
                 "--k", "1", "--scenarios", "1,2,3,4,5,6,7,8", "--yes", "--workers", "1"])
    out = capsys.readouterr().out
    assert re.search(r"done: 8/8 slots valid \(100\.0%\), total elicitation cost \$0\.11, [5-8] zero-usage"
                     r" usage-limit result\(s\) not stored as attempts \(1 pause\(s\) of 0s\)", out)
    assert outage.slept == [0.0]
    con = study.connect()
    rows = rows_of(con)
    assert len(rows) == 9 and sum(r["valid"] for r in rows) == 8
    assert [r["error"] for r in rows if not r["valid"]] == ["json: result parse failed: Expecting value:"
                                                             " line 1 column 1 (char 0)"]
    assert "usage-limit" not in "".join(r["error"] or "" for r in rows)
    capsys.readouterr()
    health.health(con, "p001")
    out = capsys.readouterr().out
    counts = [ln for ln in out.splitlines() if ln.startswith("attempt counts by outcome:")][0]
    assert "'valid': 8" in counts and "'json': 1" in counts and "outage" not in counts
    assert "usage-limit outage rows" not in out
    con.close()


def test_interrupt_during_the_pause_cancels_the_held_slots(study, monkeypatch, capsys):  # noqa: F811
    outage = Outage(_seed_payload(), ends_on_sleep=False)
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    con, pid, jobs = plan(study)

    def ctrl_c(seconds):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        elicit.run_jobs(con, study, pid, jobs, workers=2, sleep=ctrl_c)
    out = capsys.readouterr().out
    assert "interrupted (KeyboardInterrupt): 8 pending slots cancelled\n" in out
    assert ("0 of 8 slots stored (0 after the interruption); re-run to resume, 8 zero-usage usage-limit"
            " result(s) not stored as attempts (1 pause(s) of 300s)") in out
    assert rows_of(con) == [] and len(outage.calls) == 8
    con.close()


# --- review round 1: a re-planned slot's re-run, halts after a hold, the pause budget ------

def replanned_provider(seed: dict, calls: list, lock: threading.Lock, on_call: int | None = None):
    """Call 1: a paid JSON failure on the first slot, whose immediate retry
    (call 2) runs into the outage, so the paid attempt is stored and the
    slot re-planned; every later call answers validly. Call `on_call`
    sends the process SIGINT (a terminal Ctrl-C) while it is in flight."""
    def get_provider(name):
        def call(prompt, model, system_prompt):
            with lock:
                calls.append(prompt)
                n = len(calls)
            if n == 1:
                return {"result": "not json", "total_cost_usd": 0.03}, '{"result": "not json"}', None
            if n == 2:
                return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
            if n == on_call:
                os.kill(os.getpid(), signal.SIGINT)
                time.sleep(0.5)   # the main thread handles the interrupt and waits for this call
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call
    return get_provider


def assert_replanned_slot_kept(con, out: str) -> None:
    rows = [(r["scenario_id"], r["valid"], r["error"]) for r in rows_of(con)]
    assert rows[:2] == [(1, 0, "json: result parse failed: Expecting value: line 1 column 1 (char 0)"),
                        (2, 1, None)]
    assert rows[2] == (1, 1, None), "the re-planned slot's paid valid answer was discarded by the salvage"
    assert len(rows) == 3
    assert "2 of 2 slots stored (1 after the interruption); re-run to resume, 1 zero-usage" in out
    assert "3 of 2" not in out


def test_ctrl_c_during_the_replanned_slots_paid_call_keeps_its_answer(study, monkeypatch, capsys):  # noqa: F811
    """Batch 1: a paid JSON failure on slot 1 whose retry is a zero-usage
    exit (the failure is stored, the slot re-planned); batch 2: the re-run's
    paid valid answer, with Ctrl-C while it is in flight. The salvage
    recognised the slot's EARLIER paid failure (a row above the run-wide id
    floor) as the re-run's commit and skipped the store, losing the answer.
    The check is keyed on the future's own final attempt now: the answer is
    stored exactly once."""
    calls, lock = [], threading.Lock()
    monkeypatch.setattr(elicit, "get_provider", replanned_provider(_seed_payload(), calls, lock, on_call=4))
    con, pid, jobs = plan(study, scenarios="1,2")
    assert len(jobs) == 2
    with pytest.raises(KeyboardInterrupt):
        elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=lambda s: None)
    out = capsys.readouterr().out
    assert len(calls) == 4
    assert ("interrupted (KeyboardInterrupt): 0 pending slots cancelled, waiting for 1 running call(s)"
            " to store their results") in out
    assert_replanned_slot_kept(con, out)
    assert plan(study, scenarios="1,2")[2] == []   # nothing pending: the slot is not paid for twice
    con.close()


def test_ctrl_c_inside_the_replanned_slots_db_write_keeps_its_answer(study, monkeypatch, capsys):  # noqa: F811
    calls, lock = [], threading.Lock()
    monkeypatch.setattr(elicit, "get_provider", replanned_provider(_seed_payload(), calls, lock))
    con, pid, jobs = plan(study, scenarios="1,2")
    real, seen = elicit.store_attempts, []

    def store_attempts(con_, scenario_id, *a, **kw):
        seen.append(scenario_id)
        if seen.count(scenario_id) == 2:
            raise KeyboardInterrupt   # inside the re-run's write, before its commit
        return real(con_, scenario_id, *a, **kw)

    monkeypatch.setattr(elicit, "store_attempts", store_attempts)
    with pytest.raises(KeyboardInterrupt):
        elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=lambda s: None)
    out = capsys.readouterr().out
    assert len(calls) == 4 and seen == [1, 2, 1, 1]
    assert "interrupted (KeyboardInterrupt): 0 pending slots cancelled\n" in out
    assert_replanned_slot_kept(con, out)
    con.close()


def test_salvage_ignores_a_foreign_row_of_the_same_slot(study, monkeypatch, capsys):  # noqa: F811
    """Another process writes an (invalid) row for slot 1 after this run's
    batch was submitted, and the interrupt lands inside this run's write of
    its own answer to that slot. A row of the slot above the floor is not
    this future's attempt: the salvage stores the answer instead of
    counting the foreign row as its commit."""
    calls, lock = [], threading.Lock()
    monkeypatch.setattr(elicit, "get_provider", _fake_ok(_seed_payload(), calls, lock))
    con, pid, jobs = plan(study, scenarios="1")
    job = jobs[0]
    real, seen = elicit.store_attempts, []

    def store_attempts(con_, scenario_id, *a, **kw):
        seen.append(scenario_id)
        if len(seen) == 1:
            other = study.connect()   # the other process: its own connection and commit
            db.insert_elicitation(other, job["scenario_id"], pid, job["member"]["provider"],
                                  job["member"]["model"], job["repeat_ix"], elicit.prompt_hash(job["prompt"]),
                                  "{}", False, "json: from another process", job.get("stage"))
            other.commit()
            other.close()
            raise KeyboardInterrupt
        return real(con_, scenario_id, *a, **kw)

    monkeypatch.setattr(elicit, "store_attempts", store_attempts)
    with pytest.raises(KeyboardInterrupt):
        elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=lambda s: None)
    out = capsys.readouterr().out
    assert seen == [1, 1] and len(calls) == 1
    assert [(r["valid"], r["error"]) for r in rows_of(con)] == [(0, "json: from another process"), (1, None)]
    assert "1 of 1 slots stored (1 after the interruption)" in out
    con.close()


def _fake_ok(seed: dict, calls: list, lock: threading.Lock):
    def get_provider(name):
        def call(prompt, model, system_prompt):
            with lock:
                calls.append(prompt)
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call
    return get_provider


OR_MEMBER = "openrouter:fake/model"


def test_member_halted_after_the_hold_has_its_held_slots_cancelled(study, monkeypatch, capsys):  # noqa: F811
    """haiku's fifth zero-usage result holds the not-yet-started slots back
    (openrouter's second among them) while openrouter's first call is in
    flight; it then returns 401 and halts the member. Its held-back slot is
    cancelled, not re-submitted with the next batch, and the unbilled 401
    does not reset the streak (one pause, not two)."""
    seed = _seed_payload()
    state = {"active": True}
    calls = {"claude_cli": [], "openrouter": []}
    lock = threading.Lock()

    def get_provider(name):
        def call(prompt, model, system_prompt):
            with lock:
                calls[name].append(prompt)
            if name == "openrouter":
                time.sleep(0.5)   # in flight when the fifth zero-usage result lands
                return None, "", "http: status 401 unauthorized"
            time.sleep(0.05)
            if state["active"]:
                return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    def sleep(seconds):
        state["active"] = False   # the window ends during the pause

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    pid = db.get_or_create_protocol(con, study.protocol_path("p001"), study.root)
    _, planned = elicit.plan_jobs(con, study, pid, "1,2,3,4,5,6,7,8", 1, {"claude_cli:haiku", OR_MEMBER})
    by = {(db.member_label(j["member"]), j["scenario_id"]): j for j in planned}
    jobs = ([by[("claude_cli:haiku", s)] for s in (1, 2, 3, 4)] + [by[(OR_MEMBER, 1)]]
            + [by[("claude_cli:haiku", s)] for s in (5, 6, 7, 8)] + [by[(OR_MEMBER, 2)]])
    n_valid, cost, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=2, sleep=sleep)
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled) == (8, 1) and cost == pytest.approx(0.08)
    assert summary["pauses"] == 1 and out.count("usage-limit outage: pausing") == 1
    assert re.search(r"dispatching stopped, [1-4] not-yet-started slot\(s\) held back", out)
    assert (f"member {OR_MEMBER}: http: status 401 unauthorized: a retry cannot help; cancelled its 1"
            " pending slots") in out
    assert out.count(f"{OR_MEMBER} repeat 0: INVALID (http: status 401 unauthorized)") == 1
    assert len(calls["openrouter"]) == 1, "the halted member's held-back slot was re-submitted"
    rows = rows_of(con)
    assert [(r["scenario_id"], r["valid"], r["error"]) for r in rows if r["error"]] == \
        [(1, 0, "http: status 401 unauthorized")]
    assert sorted(r["scenario_id"] for r in rows if r["valid"]) == list(range(1, 9))
    # the streak resets on a billed result only
    assert not elicit.billed([elicit.failed_attempt("http: status 401 unauthorized")])
    assert not elicit.billed([elicit.failed_attempt("provider: OSError: unreachable")])
    assert not elicit.billed([elicit.failed_attempt("cli: timeout after 600s")])
    assert elicit.billed([{"error": "json: result parse failed", "cost": 0.0}])
    assert elicit.billed([{"error": "cli: exit 1: boom", "cost": 0.02}])
    assert elicit.billed([{"error": None, "cost": 0.0}])
    con.close()


def test_the_pause_budget_counts_every_window_of_the_run(study, monkeypatch, capsys):  # noqa: F811
    """Two outage windows in one run: the first ends at its pause and its
    probe is billed; the second never ends. The run gives up after
    OUTAGE_MAX_PAUSES pauses in total (1 + 11), not 12 per window."""
    seed = _seed_payload()
    state = {"active": True, "billed": 0}
    lock = threading.Lock()

    def get_provider(name):
        def call(prompt, model, system_prompt):
            with lock:
                if state["active"]:
                    return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
                state["billed"] += 1
                if state["billed"] == 2:
                    state["active"] = True   # the second window opens after two billed answers
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    slept = []

    def sleep(seconds):
        slept.append(seconds)
        if len(slept) == 1:
            state["active"] = False   # only the first window ends

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    con, pid, jobs = plan(study)
    n_valid, cost, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=sleep)
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled) == (2, 6) and cost == pytest.approx(0.02)
    assert summary["pauses"] == 12 and summary["gave_up"] and summary["unresolved"] == 6
    assert len(slept) == 12
    assert "usage-limit outage: pausing 300s (pause 1/12) with 8 slot(s) pending" in out
    assert "usage-limit outage: pausing 300s (pause 2/12) with 6 slot(s) pending" in out
    assert re.search(r"giving up after 12 pauses of 300s \(\d+ zero-usage results in a row\); 2 slot\(s\)"
                     r" of this run stored, 6 still pending", out)
    assert len(rows_of(con)) == 2 and all(r["valid"] for r in rows_of(con))
    con.close()


# --- health and the report macros on legacy rows -------------------------------------

def test_health_and_macros_show_legacy_zero_usage_rows_as_outage(study, monkeypatch, capsys):  # noqa: F811
    seed = _seed_payload()
    monkeypatch.setattr(elicit, "get_provider", Outage(seed, fail_calls=0).get_provider)
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
                 "--k", "1", "--scenarios", "1,2,3,4", "--yes"])
    study.generated_dir.mkdir(parents=True, exist_ok=True)
    con = study.connect()
    pid = db.protocol_by_name(con, "p001")["id"]
    # three rows as the pre-v2.3 harness stored them during the outage, plus one real JSON failure
    for sid in (1, 2, 3):
        db.insert_elicitation(con, sid, pid, "claude_cli", "haiku", 5, "h", LIMIT_RAW, False, "cli: exit 1: ")
    db.insert_elicitation(con, 4, pid, "claude_cli", "haiku", 5, "h",
                          '{"result": "x", "total_cost_usd": 0.02}', False, "json: result parse failed: x")
    con.commit()
    assert health.error_class("cli: exit 1: ", LIMIT_RAW) == "outage"
    assert health.error_class(LIMIT_ERROR) == "outage"
    assert health.error_class("cli: exit 1: ", PAID_RAW) == "cli"
    assert health.error_class(None) == "valid" and health.error_class("json: x") == "json"
    capsys.readouterr()
    health.health(con, "p001")
    out = capsys.readouterr().out
    assert "=== health: protocol p001 (8 rows, 3 usage-limit outage, 5 attempts, 2 member(s)) ===" in out
    assert "attempt counts by outcome: {'valid': 4, 'outage': 3, 'json': 1}" in out
    # the plan's cost estimate averages over the billed attempts only (the fake stores no cost,
    # the JSON failure $0.02: 0.02 / 5, not 0.02 / 8)
    assert elicit.member_mean_cost(con, {"provider": "claude_cli", "model": "haiku"}, "binary") == \
        (pytest.approx(0.004), 5)
    assert ("usage-limit outage rows (zero-usage CLI exits, no model call, unbilled): 3; left out of the"
            " 5 attempts the rates below are over") in out
    assert "JSON validity rate (parse+schema): 4/5 = 80.0%" in out
    assert "constraint pass rate (of parsed): 4/4 = 100.0%" in out
    assert "slot validity (after retry): 4/5 = 80.0%" in out
    assert "claude_cli:haiku (k=2): 5 attempts, 4 valid (80.0%), $0.02" in out   # the fake stores no cost
    # the report macros and the member table count billed attempts only
    assert tables.member_stats(con, pid, {"provider": "claude_cli", "model": "haiku"}) == \
        {"attempts": 5, "valid": 4, "cost": pytest.approx(0.02)}
    assert len(tables.billed_attempts(con, pid)) == 5
    assert len(tables.billed_attempts(con, pid, ["claude_cli:haiku"])) == 5
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(db, "git_state", lambda cwd=None: ("test-head", []))
        from voi_rank import mc
        run = db.get_run(con, mc.run_mc(con, "p001", seed=1, n_draws=200, quiet=True))
    macros = tables.write_macros(con, run, study.generated_dir)
    assert macros["voiNAttempts"] == 5 and macros["voiValidityRate"] == "80.0\\%"
    assert macros["voiMemberAttemptsA"] == 5 and macros["voiMemberValidityA"] == "80.0\\%"
    con.close()
