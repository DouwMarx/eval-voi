"""Harness pause on usage-limit outages. During a claude.ai usage-limit
window the CLI exits 1 with a zero-usage envelope (no model call, nothing
billed): the provider classifies it, the job never retries it, run_jobs
stores nothing for it, holds a member after OUTAGE_STREAK such results of
it in a row while the others go on, pauses once only held members are
left, probes each with one call and resumes it, or gives up on it once it
has paused VOI_OUTAGE_MAX_WAIT_S since its last billed result; the plan's
cost estimate reads legacy rows of that kind as outages. A zero-usage exit
of another API status (an unknown model id) is an ordinary attempt that
halts the member. Fake providers, injected sleep and clock, no CLI, no
network."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import threading
import time
from datetime import UTC, datetime

import pytest

from tests.test_pipeline import (  # noqa: F401  (the temporary study fixture)
    INSTRUMENT,
    OR_MEMBER,
    _seed_payload,
    answer,
    protocol_cfg,
    study,
)
from voi_rank import db, dotenv, elicit
from voi_rank.providers import claude_cli

# the envelope the CLI printed during the 2026-09-29 outage (LEARNINGS), verbatim in shape
# (every one of the 1,620 stored rows carries api_error_status 429)
LIMIT_ENVELOPE = {"type": "result", "subtype": "success", "is_error": True, "duration_ms": 467,
                  "num_turns": 1, "api_error_status": 429, "terminal_reason": "api_error",
                  "total_cost_usd": 0, "usage": {"input_tokens": 0, "output_tokens": 0},
                  "result": "You've hit your session limit · resets 4:30am (Europe/Brussels)"}
LIMIT_RAW = json.dumps(LIMIT_ENVELOPE)
# CLI 2.1.280, verbatim stdout of `claude -p 'say hi' --model claude-nonexistent-model-xyz
# --output-format json --tools '' --setting-sources '' --no-session-persistence` (exit 1, unbilled)
NOTFOUND_RAW = (
    '{"duration_api_ms":0,"stop_reason":"stop_sequence","session_id":"dab68a72-36fb-4b96-b3a8-c701dbd24010",'
    '"total_cost_usd":0,"usage":{"output_tokens_details":{"thinking_tokens":0},"input_tokens":0,'
    '"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":'
    '{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":'
    '{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"inference_geo":"","iterations":[],'
    '"speed":"standard"},"modelUsage":{},"permission_denials":[],"terminal_reason":"api_error",'
    '"fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":'
    '{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,'
    '"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,'
    '"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},'
    '"is_error":true,"num_turns":1,"subtype":"success","api_error_status":404,"result":"There\'s an issue'
    ' with the selected model (claude-nonexistent-model-xyz). It may not exist or you may not have access'
    ' to it. Run --model to pick a different model.","type":"result","duration_ms":794,"uuid":'
    '"9e6fc5e1-510d-4479-b2ce-3dc1ec716d84","queued_turn_count":0,"result_index":0}')
NOTFOUND_STDERR = ('[claude-code:unrecognized_model] {"model":"claude-nonexistent-model-xyz",'
                   '"query_source":"sdk"}')
NOTFOUND_ERROR = ("cli: exit 1 (zero-usage, api 404): There's an issue with the selected model"
                  " (claude-nonexistent-model-xyz). It may not exist or you may not have access to it."
                  " Run --model to pick a different model.")
# the fake clock: 14:00 in Brussels, so the stated 4:30am reset is 14.5 h away (more than a
# session window) and a pause lasts the fixed VOI_OUTAGE_SLEEP_S
NOON = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def outage_settings(monkeypatch, tmp_path):
    """The default outage settings (no VOI_OUTAGE_* in the environment or
    .env) and the fixed clock NOON, on the run_jobs and the main() path."""
    for name in (elicit.OUTAGE_SLEEP_SETTING, elicit.OUTAGE_MAX_WAIT_SETTING):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(dotenv, "ENV_FILE", tmp_path / "no.env")
    monkeypatch.setattr(elicit, "utc_now", lambda: NOON)
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
    # a CLI that reports no api_error_status: the zero-usage envelope alone decides, as before
    no_status = {k: v for k, v in LIMIT_ENVELOPE.items() if k != "api_error_status"}
    assert claude_cli.usage_limit_envelope(no_status)
    assert claude_cli.is_usage_limit("cli: exit 1: ", json.dumps(no_status))


def test_a_zero_usage_exit_of_another_api_status_is_not_an_outage(monkeypatch):
    """Review round 3: every non-zero exit with a zero-usage envelope was
    read as a usage-limit outage. The real CLI's answer to an unknown model
    id (captured verbatim, api_error_status 404) became 'cli: usage-limit
    ...', so the run paused for an hour, stored nothing and told the operator
    to wait for a limit reset. Only status 429 (or none) is an outage now;
    404 (and 401/402/403) is an ordinary attempt that halts the member, and
    a zero-usage login failure is one too, for every reader."""
    script = [(1, NOTFOUND_RAW, NOTFOUND_STDERR),
              (1, json.dumps({**LIMIT_ENVELOPE, "api_error_status": 401,
                              "result": "Invalid API key · Fix external API key"}), ""),
              (1, json.dumps({k: v for k, v in LIMIT_ENVELOPE.items() if k != "api_error_status"}
                             | {"result": "Not logged in · Please run /login"}), ""),
              (1, json.dumps({**LIMIT_ENVELOPE, "api_error_status": 529, "result": "Overloaded"}), ""),
              (1, json.dumps({k: v for k, v in LIMIT_ENVELOPE.items() if k != "api_error_status"}
                             | {"result": ""}), "Not logged in")]
    monkeypatch.setattr(claude_cli.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, *script.pop(0)))
    envelope, raw, err = claude_cli.call_claude("p", "claude-nonexistent-model-xyz", "sys")
    assert err == NOTFOUND_ERROR and raw == NOTFOUND_RAW and envelope["api_error_status"] == 404
    assert not elicit.usage_limit(err) and elicit.halts_member(err) and elicit.retry_delay(err) is None
    assert not claude_cli.is_usage_limit(err, raw)
    _, _, err = claude_cli.call_claude("p", "haiku", "sys")
    assert err == "cli: exit 1 (zero-usage, api 401): Invalid API key · Fix external API key"
    assert elicit.halts_member(err) and not elicit.usage_limit(err)
    _, raw, err = claude_cli.call_claude("p", "haiku", "sys")
    assert err == "cli: exit 1 (zero-usage, api none): Not logged in · Please run /login"
    assert elicit.halts_member(err) and not elicit.usage_limit(err)
    _, raw, err = claude_cli.call_claude("p", "haiku", "sys")   # a server error: retried once at once
    assert err == "cli: exit 1 (zero-usage, api 529): Overloaded"
    assert not elicit.halts_member(err) and not elicit.usage_limit(err) and elicit.retry_delay(err) == 0.0
    _, raw, err = claude_cli.call_claude("p", "haiku", "sys")   # an empty result, the login text on stderr
    assert err == "cli: exit 1 (zero-usage, api none): Not logged in" and elicit.halts_member(err)
    assert not claude_cli.is_usage_limit(err, raw)
    # legacy rows ('cli: exit 1' with the envelope) are read the same way
    assert not claude_cli.is_usage_limit("cli: exit 1: ", NOTFOUND_RAW)
    assert claude_cli.is_usage_limit("cli: exit 1: ", LIMIT_RAW)
    login = "cli: usage-limit (zero-usage exit 1): Not logged in · Please run /login"
    assert not claude_cli.is_usage_limit(login)


def test_an_unknown_model_halts_the_member_without_a_pause(study, monkeypatch, capsys):  # noqa: F811
    """The captured 404 exit through run_jobs: stored as an invalid attempt,
    the member halted at once, no pause (on the old classification: 12
    pauses of 300 s, nothing stored, 'once the limit resets')."""
    def run(cmd, **kw):
        time.sleep(0.1)   # the main thread sees the first result while the next call runs
        return subprocess.CompletedProcess(cmd, 1, NOTFOUND_RAW, NOTFOUND_STDERR)

    monkeypatch.setattr(claude_cli.subprocess, "run", run)
    monkeypatch.setattr(elicit, "get_provider", lambda name: claude_cli.call_claude)
    slept = []
    con, pid, jobs = plan(study)
    n_valid, cost, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=1,
                                                          sleep=slept.append)
    out = capsys.readouterr().out
    rows = rows_of(con)
    assert slept == [] and summary == {"results": 0, "pauses": 0, "waited_s": 0.0, "gave_up": False,
                                       "unresolved": 0}
    assert 1 <= len(rows) <= 2 and all((r["valid"], r["error"]) == (0, NOTFOUND_ERROR) for r in rows)
    assert (n_valid, cost, n_cancelled) == (0, 0.0, 8 - len(rows))
    assert f"member claude_cli:haiku: {NOTFOUND_ERROR[:160]}: a retry cannot help; cancelled its" in out
    assert "usage-limit" not in out
    con.close()


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
            text = answer(prompt, self.seed)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call


def plan(st, k: int = 1, scenarios: str = "1,2,3,4,5,6,7,8"):
    """The instrument-stage slots of haiku over the scenarios (one per scenario at k=1)."""
    con = st.connect()
    db.seed_scenarios(con, st.scenarios_json)
    pid = db.get_or_create_protocol(con, st.protocol_path("p001"), st.root)
    _, jobs = elicit.plan_jobs(con, st, pid, scenarios, k, {"claude_cli:haiku"}, stage="instrument")
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
    assert summary["unresolved"] == 0 and outage.slept == [elicit.DEFAULT_OUTAGE_SLEEP_S] == [300.0]
    assert summary["waited_s"] == 300.0
    assert len(outage.calls) == summary["results"] + 8
    rows = rows_of(con)
    assert len(rows) == 8 and all(r["valid"] == 1 and r["error"] is None for r in rows)
    assert sorted(r["scenario_id"] for r in rows) == list(range(1, 9))
    assert out.count("nothing billed, not stored, re-planned") == summary["results"]
    assert re.search(r"usage-limit outage: claude_cli:haiku: 5 consecutive zero-usage results across"
                     r" workers; its dispatching stopped, [0-3] not-yet-started slot\(s\) of it held back for"
                     r" the pause \(the other members go on\)", out)
    assert ("usage-limit outage: pausing 300s (pause 1; claude_cli:haiku 300s of 21600s) with 8 slot(s)"
            " pending, then probing with one call per held member") in out
    assert out.count("usage-limit outage: pausing") == 1 and "giving up" not in out
    assert re.search(r"\[8/8\] scenario \d stage instrument claude_cli:haiku repeat 0: ok", out)
    assert "[9/8]" not in out
    assert elicit.outage_summary(summary) == (f", {summary['results']} zero-usage usage-limit result(s) not"
                                              " stored as attempts (1 pause(s), 300s paused)")
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
    assert summary == {"results": 2, "pauses": 0, "waited_s": 0.0, "gave_up": False, "unresolved": 0}
    assert len(rows_of(con)) == 8 and "dispatching stopped" not in out and "pausing" not in out
    assert out.count("nothing billed, not stored, re-planned") == 2
    con.close()


def test_outage_gives_up_after_the_wait_budget_with_everything_stored(study, monkeypatch, capsys):  # noqa: F811
    seed = _seed_payload()
    outage = Outage(seed, ends_on_sleep=False)   # the window never ends
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    monkeypatch.setenv("VOI_OUTAGE_MAX_WAIT_S", "3600")
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
    assert re.search(r"usage-limit outage: giving up on claude_cli:haiku after 3600s paused since its last"
                     r" billed result \(VOI_OUTAGE_MAX_WAIT_S=3600\), with \d+ zero-usage results of it in a"
                     r" row; 0 slot\(s\) of it stored by this run, 8 still pending: re-run to resume once the"
                     r" limit resets", out)
    assert out.count("usage-limit outage: pausing") == 12
    assert elicit.outage_summary(summary).endswith("; gave up after 12 pauses with 8 slot(s) still pending:"
                                                   " re-run to resume")
    # the limit lifts: the next run fills every slot, through main and its summary line
    fine = Outage(seed, fail_calls=0)
    monkeypatch.setattr(elicit, "get_provider", fine.get_provider)
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
                 "--k", "1", "--scenarios", "1,2,3,4,5,6,7,8", "--yes", "--workers", "3", *INSTRUMENT])
    out = capsys.readouterr().out
    assert "done: 8/8 slots valid (100.0%), total elicitation cost $0.08\n" in out
    assert len(rows_of(con)) == 8 and len(fine.calls) == 8
    con.close()


def test_main_summary_counts_the_outage_and_stores_paid_attempts_before_it(study, monkeypatch, capsys):  # noqa: F811
    """The CLI path (time.sleep patched): the first
    call is a paid JSON failure whose immediate retry runs into the outage;
    the paid attempt is stored, the zero-usage results are not, the summary
    line counts them, and health sees no outage row."""
    seed = _seed_payload()
    outage = Outage(seed)
    inner = outage.get_provider("claude_cli")
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
                 "--k", "1", "--scenarios", "1,2,3,4,5,6,7,8", "--yes", "--workers", "1", *INSTRUMENT])
    out = capsys.readouterr().out
    assert re.search(r"done: 8/8 slots valid \(100\.0%\), total elicitation cost \$0\.11, [5-8] zero-usage"
                     r" usage-limit result\(s\) not stored as attempts \(1 pause\(s\), 300s paused\)", out)
    assert outage.slept == [300.0]
    con = study.connect()
    rows = rows_of(con)
    assert len(rows) == 9 and sum(r["valid"] for r in rows) == 8
    assert [r["error"] for r in rows if not r["valid"]] == ["json: result parse failed: Expecting value:"
                                                             " line 1 column 1 (char 0)"]
    assert "usage-limit" not in "".join(r["error"] or "" for r in rows)
    con.close()


def test_interrupt_during_the_pause_cancels_the_held_slots(study, monkeypatch, capsys):  # noqa: F811
    """Ctrl-C about 1 s into a 300 s pause. Review round 3 (2): the summary
    added the planned pause before sleeping and reported '300s paused'; it
    reports the time that elapsed."""
    outage = Outage(_seed_payload(), ends_on_sleep=False)
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    con, pid, jobs = plan(study)

    def ctrl_c(seconds):
        time.sleep(1.2)
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        elicit.run_jobs(con, study, pid, jobs, workers=2, sleep=ctrl_c)
    out = capsys.readouterr().out
    assert "interrupted (KeyboardInterrupt): 8 pending slots cancelled\n" in out
    assert ("0 of 8 slots stored (0 after the interruption); re-run to resume, 8 zero-usage usage-limit"
            " result(s) not stored as attempts (1 pause(s), 1s paused)") in out
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
            text = answer(prompt, seed)
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
            text = answer(prompt, seed)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call
    return get_provider


def test_member_halted_after_the_hold_has_its_held_slots_cancelled(study, monkeypatch, capsys):  # noqa: F811
    """haiku's first call is slow and ends in a login error (the member's
    environment); meanwhile the other worker's calls hit the limit, and
    the fifth zero-usage result holds haiku's not-yet-started slots back.
    The login error then halts haiku: its held-back and re-planned slots
    are cancelled, not re-submitted, and the run never pauses."""
    calls, lock = [], threading.Lock()

    def get_provider(name):
        def call(prompt, model, system_prompt):
            with lock:
                calls.append(prompt)
                first = len(calls) == 1
            if first:
                time.sleep(0.5)   # in flight when the fifth zero-usage result lands
                return None, "Not logged in", "cli: exit 1: Not logged in"
            time.sleep(0.05)
            return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
        return call

    slept = []
    monkeypatch.setattr(elicit, "get_provider", get_provider)
    con, pid, jobs = plan(study)
    n_valid, cost, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=2,
                                                          sleep=slept.append)
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled, cost) == (0, 7, 0.0) and slept == [] and summary["pauses"] == 0
    assert re.search(r"its dispatching stopped, [1-3] not-yet-started slot\(s\) of it held back", out)
    assert re.search(r"member claude_cli:haiku: cli: exit 1: Not logged in: a retry cannot help; cancelled"
                     r" its 7 pending slots", out)
    assert len(calls) in (6, 7), "the halted member's held-back slots were re-submitted"
    assert [(r["scenario_id"], r["valid"], r["error"]) for r in rows_of(con)] == \
        [(1, 0, "cli: exit 1: Not logged in")]
    # the streak resets on a billed result only
    assert not elicit.billed([elicit.failed_attempt("http: status 401 unauthorized")])
    assert not elicit.billed([elicit.failed_attempt("provider: OSError: unreachable")])
    assert not elicit.billed([elicit.failed_attempt("cli: timeout after 600s")])
    assert elicit.billed([{"error": "json: result parse failed", "cost": 0.0}])
    assert elicit.billed([{"error": "cli: exit 1: boom", "cost": 0.02}])
    assert elicit.billed([{"error": None, "cost": 0.0}])
    con.close()


def test_the_wait_budget_restarts_at_every_billed_result(study, monkeypatch, capsys):  # noqa: F811
    """Two outage windows in one run: the first ends at its pause and its
    probe is billed; the second never ends. Review round 3 (2): the budget
    was one per run, so two real windows (8,823 s + 9,312 s of the default
    21,600 s) left 58 minutes for a third. A billed result restarts it: the
    second window gets the full VOI_OUTAGE_MAX_WAIT_S (3600 s here: 12
    pauses of 300 s after the first window's one)."""
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
            text = answer(prompt, seed)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    slept = []

    def sleep(seconds):
        slept.append(seconds)
        if len(slept) == 1:
            state["active"] = False   # only the first window ends

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("VOI_OUTAGE_MAX_WAIT_S", "3600")
    con, pid, jobs = plan(study)
    n_valid, cost, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=sleep)
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled) == (2, 6) and cost == pytest.approx(0.02)
    assert summary["pauses"] == 13 and summary["gave_up"] and summary["unresolved"] == 6
    assert slept == [300.0] * 13 and summary["waited_s"] == 3900.0
    assert "usage-limit outage: pausing 300s (pause 1; claude_cli:haiku 300s of 3600s) with 8 slot(s)" in out
    assert "usage-limit outage: pausing 300s (pause 2; claude_cli:haiku 300s of 3600s) with 6 slot(s)" in out
    assert "(pause 13; claude_cli:haiku 3600s of 3600s)" in out
    assert re.search(r"giving up on claude_cli:haiku after 3600s paused since its last billed result"
                     r" \(VOI_OUTAGE_MAX_WAIT_S=3600\), with \d+ zero-usage results of it in a row;"
                     r" 2 slot\(s\) of it stored by this run, 6 still pending", out)
    assert len(rows_of(con)) == 2 and all(r["valid"] for r in rows_of(con))
    con.close()


PROTOCOL_3 = protocol_cfg("p007", [{"provider": "claude_cli", "model": m, "k_repeats": 1}
                                   for m in ("haiku", "sonnet", "opus")])


def test_one_members_limit_never_holds_the_other_members(study, monkeypatch, capsys):  # noqa: F811
    """Review round 3 (2): the streak, hold and probe were run-wide. With
    haiku, sonnet and opus at k=5 (plan order per scenario: haiku x5,
    sonnet x5, opus x5) and only opus limited (a model-specific limit),
    opus's fifth zero-usage result held every later slot of haiku and
    sonnet too, the probe was always the same opus slot, and at give-up
    their slots were cancelled without ever being called (11 of 45 slots
    stored, 34 cancelled, on the old code). The outage is per member now:
    haiku and sonnet run every slot before the first pause, the probe is an
    opus call, and the give-up cancels opus's slots only."""
    import yaml

    (study.protocols_dir / "p007.yaml").write_text(yaml.safe_dump(PROTOCOL_3))   # two stages, three members
    seed = _seed_payload()
    state = {"opus_limited": True}
    calls, lock = [], threading.Lock()

    def get_provider(name):
        def call(prompt, model, system_prompt):
            with lock:
                calls.append(model)
            time.sleep(0.01)   # a call takes time: the hold catches not-yet-started slots
            if model == "opus" and state["opus_limited"]:
                return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
            text = answer(prompt, seed)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    def plan3():
        con = study.connect()
        db.seed_scenarios(con, study.scenarios_json)
        pid = db.get_or_create_protocol(con, study.protocol_path("p007"), study.root)
        _, jobs = elicit.plan_jobs(con, study, pid, "1,2,3", 5, None, stage="instrument")
        return con, pid, jobs

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    con, pid, jobs = plan3()
    assert len(jobs) == 45
    assert [j["member"]["model"] for j in jobs[:15]] == ["haiku"] * 5 + ["sonnet"] * 5 + ["opus"] * 5
    # the window never ends: a 900 s budget (3 pauses), then the run gives up on opus alone
    monkeypatch.setenv("VOI_OUTAGE_MAX_WAIT_S", "900")
    at_sleep = []
    n_valid, cost, n_cancelled, summary = elicit.run_jobs(
        con, study, pid, jobs, workers=1, sleep=lambda s: at_sleep.append(list(calls)))
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled) == (30, 15) and cost == pytest.approx(0.30)
    assert summary["pauses"] == 3 and summary["gave_up"] and summary["unresolved"] == 15
    before = at_sleep[0]
    assert before.count("haiku") == before.count("sonnet") == 15, "a healthy member was held back"
    # after each pause one call only, opus's probe
    assert [len(c) for c in at_sleep[1:]] == [len(before) + 1, len(before) + 2]
    assert calls[len(before):] == ["opus"] * 3
    assert "usage-limit outage: claude_cli:opus: 5 consecutive zero-usage results" in out
    assert "(pause 1; claude_cli:opus 300s of 900s) with 15 slot(s) pending" in out
    assert re.search(r"giving up on claude_cli:opus after 900s paused since its last billed result"
                     r" \(VOI_OUTAGE_MAX_WAIT_S=900\), with \d+ zero-usage results of it in a row;"
                     r" 0 slot\(s\) of it stored by this run, 15 still pending", out)
    rows = con.execute("SELECT model, COUNT(*) AS n FROM elicitations WHERE valid=1"
                       " GROUP BY model").fetchall()
    assert {r["model"]: r["n"] for r in rows} == {"haiku": 15, "sonnet": 15}
    # the limit lifts at the pause: the probe is opus's, and every slot is filled
    calls.clear()
    monkeypatch.delenv("VOI_OUTAGE_MAX_WAIT_S")
    _, _, jobs = plan3()
    assert len(jobs) == 15

    def lift(seconds):
        at_sleep.append(list(calls))
        state["opus_limited"] = False

    at_sleep.clear()
    state["opus_limited"] = True
    n_valid, _, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=lift)
    assert (n_valid, n_cancelled, summary["pauses"]) == (15, 0, 1)
    assert calls[len(at_sleep[0])] == "opus" and plan3()[2] == []
    con.close()


def test_a_limited_member_never_stalls_a_slower_healthy_one(study, monkeypatch, capsys):  # noqa: F811
    """The reviewers' second replay: haiku limited, a healthy but slower
    OpenRouter member, the default 8 workers. Half of OpenRouter's slots
    were held by haiku's streak and cancelled at give-up without a call;
    every one is called and stored now."""
    seed = _seed_payload()
    calls = {"claude_cli": 0, "openrouter": 0}
    lock = threading.Lock()

    def get_provider(name):
        def call(prompt, model, system_prompt):
            with lock:
                calls[name] += 1
            if name == "claude_cli":
                return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
            time.sleep(0.2)
            text = answer(prompt, seed)
            return {"choices": [{"message": {"content": text}}], "result": text}, text, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("VOI_OUTAGE_MAX_WAIT_S", "600")
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    pid = db.get_or_create_protocol(con, study.protocol_path("p001"), study.root)
    _, jobs = elicit.plan_jobs(con, study, pid, "1,2,3,4,5,6,7,8", 1, {"claude_cli:haiku", OR_MEMBER},
                               stage="instrument")
    n_valid, _, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=8,
                                                       sleep=lambda s: None)
    out = capsys.readouterr().out
    assert calls["openrouter"] == 8 and (n_valid, n_cancelled) == (8, 8)
    assert summary["unresolved"] == 8 and "giving up on claude_cli:haiku" in out
    assert "giving up on openrouter" not in out
    rows = con.execute("SELECT provider, valid FROM elicitations").fetchall()
    assert [(r["provider"], r["valid"]) for r in rows] == [("openrouter", 1)] * 8
    con.close()


# --- the plan's cost estimate on legacy rows -----------------------------------------

def test_cost_estimate_leaves_legacy_zero_usage_rows_out(study, monkeypatch, capsys):  # noqa: F811
    seed = _seed_payload()
    monkeypatch.setattr(elicit, "get_provider", Outage(seed, fail_calls=0).get_provider)
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
                 "--k", "1", "--scenarios", "1,2,3,4", "--yes", *INSTRUMENT])
    con = study.connect()
    pid = db.protocol_by_name(con, "p001")["id"]
    # three rows as the pre-v2.3 harness stored them during the outage, plus one real JSON failure
    for sid in (1, 2, 3):
        db.insert_elicitation(con, sid, pid, "claude_cli", "haiku", 5, "h", LIMIT_RAW, False, "cli: exit 1: ")
    db.insert_elicitation(con, 4, pid, "claude_cli", "haiku", 5, "h",
                          '{"result": "x", "total_cost_usd": 0.02}', False, "json: result parse failed: x")
    con.commit()
    # the estimate averages over the billed attempts only (the fake's raw response records no
    # cost, the JSON failure $0.02: 0.02 / 5, not 0.02 / 8)
    assert elicit.member_mean_cost(con, {"provider": "claude_cli", "model": "haiku"}) == \
        (pytest.approx(0.004), 5)
    assert elicit.member_mean_cost(con, {"provider": "claude_cli", "model": "opus"}) is None
    con.close()


# --- review round 3: the pause length and budget, a held batch, slot counts, paid exit 1 ------

def test_usage_limit_reset_reads_the_stated_time():
    """The two windows of 2026-09-29 (CEST, UTC+2): the first message at
    00:03:55Z says 'resets 4:30am (Europe/Brussels)', 02:30Z; the second at
    04:55:48Z says 'resets 9:30am', 07:30Z. A time already past is
    tomorrow's; no time, an unknown zone or a dated (weekly) reset is None."""
    first = datetime(2026, 9, 29, 0, 3, 55, tzinfo=UTC)
    reset = claude_cli.usage_limit_reset(LIMIT_ERROR, first)
    assert reset == datetime(2026, 9, 29, 2, 30, tzinfo=UTC) and str(reset.tzinfo) == "Europe/Brussels"
    second = datetime(2026, 9, 29, 4, 55, 48, tzinfo=UTC)
    msg = ("cli: usage-limit (zero-usage exit 1): You've hit your session limit · resets 9:30am"
           " (Europe/Brussels)")
    assert claude_cli.usage_limit_reset(msg, second) == datetime(2026, 9, 29, 7, 30, tzinfo=UTC)
    assert claude_cli.usage_limit_reset("resets 9pm (UTC)", first) == datetime(2026, 9, 29, 21, tzinfo=UTC)
    assert claude_cli.usage_limit_reset("resets 12am (UTC)", first) == datetime(2026, 9, 30, tzinfo=UTC)
    assert claude_cli.usage_limit_reset(LIMIT_ERROR, NOON) == datetime(2026, 9, 30, 2, 30, tzinfo=UTC)
    for text in ("You've hit your session limit", "resets 4:30am (Mars/Olympus)", "resets 13:00pm (UTC)",
                 "resets Oct 3, 5pm (Europe/Brussels)", None):
        assert claude_cli.usage_limit_reset(text, first) is None, text
    # the pause: until 60 s after a reset at most one session window away, else the fixed pause
    assert elicit.outage_pause(LIMIT_ERROR, first, 300.0) == (
        8825.0, " until 60s after the stated reset (04:30 Europe/Brussels)")   # 2 h 26 min 05 s + 60 s
    assert elicit.outage_pause(LIMIT_ERROR, NOON, 300.0) == (300.0, "")         # 14.5 h away: past, or weekly
    assert elicit.outage_pause("cli: usage-limit (zero-usage exit 1): ", first, 450.0) == (450.0, "")


def test_the_pause_lasts_until_the_stated_reset(study, monkeypatch, capsys):  # noqa: F811
    """Review round 3: the fixed budget (12 x 300 s) gave up about 85
    minutes before either 2026-09-29 window reset. At the first window's
    clock the run now sleeps once, until just after the stated reset, and
    resumes."""
    outage = Outage(_seed_payload())
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    con, pid, jobs = plan(study)
    clock = datetime(2026, 9, 29, 0, 3, 55, tzinfo=UTC)
    n_valid, _, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=2, sleep=outage.sleep,
                                                       now=lambda: clock)
    out = capsys.readouterr().out
    assert (n_valid, n_cancelled) == (8, 0) and outage.slept == [8825.0]
    assert summary["pauses"] == 1 and summary["waited_s"] == 8825.0 and not summary["gave_up"]
    assert ("usage-limit outage: pausing 8825s until 60s after the stated reset (04:30 Europe/Brussels)"
            " (pause 1; claude_cli:haiku 8825s of 21600s) with 8 slot(s) pending, then probing with one"
            " call per held member") in out
    # review round 3 (2): a pause cut to the budget still named the reset it no longer reaches
    monkeypatch.setenv("VOI_OUTAGE_MAX_WAIT_S", "600")
    outage = Outage(_seed_payload(), ends_on_sleep=False)
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    clock = datetime(2026, 9, 29, 0, 10, tzinfo=UTC)
    elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=outage.sleep, now=lambda: clock)
    out = capsys.readouterr().out
    assert outage.slept == [600.0] and "stated reset" not in out
    assert ("pausing 600s (cut to what is left of claude_cli:haiku's wait budget) (pause 1;"
            " claude_cli:haiku 600s of 600s)") in out
    con.close()


def test_outage_settings_come_from_the_environment_or_env(study, monkeypatch, tmp_path, capsys):  # noqa: F811
    """VOI_OUTAGE_SLEEP_S and VOI_OUTAGE_MAX_WAIT_S (environment, else
    .env); the last pause is cut to what is left of the budget. The default
    budget covers one 5-hour session window (72 fixed pauses)."""
    assert elicit.DEFAULT_OUTAGE_MAX_WAIT_S >= elicit.SESSION_WINDOW_S == 5 * 3600
    (tmp_path / "no.env").write_text("VOI_OUTAGE_SLEEP_S=600  # seconds\nVOI_OUTAGE_MAX_WAIT_S=1500\n")
    outage = Outage(_seed_payload(), ends_on_sleep=False)
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    con, pid, jobs = plan(study)
    _, _, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=outage.sleep)
    out = capsys.readouterr().out
    assert outage.slept == [600.0, 600.0, 300.0] and summary["waited_s"] == 1500.0 and summary["gave_up"]
    assert "giving up on claude_cli:haiku after 1500s paused since its last billed result" \
           " (VOI_OUTAGE_MAX_WAIT_S=1500)" in out
    assert ("pausing 300s (cut to what is left of claude_cli:haiku's wait budget) (pause 3;"
            " claude_cli:haiku 1500s of 1500s)") in out
    monkeypatch.setenv("VOI_OUTAGE_MAX_WAIT_S", "900")   # the environment wins over .env
    outage = Outage(_seed_payload(), ends_on_sleep=False)
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=outage.sleep)
    assert outage.slept == [600.0, 300.0]
    (tmp_path / "no.env").unlink()
    monkeypatch.delenv("VOI_OUTAGE_MAX_WAIT_S")
    outage = Outage(_seed_payload(), ends_on_sleep=False)
    monkeypatch.setattr(elicit, "get_provider", outage.get_provider)
    elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=outage.sleep)
    assert outage.slept == [300.0] * 72 and sum(outage.slept) == elicit.DEFAULT_OUTAGE_MAX_WAIT_S
    for bad in ("0", "-5", "soon", "inf"):
        monkeypatch.setenv("VOI_OUTAGE_SLEEP_S", bad)
        with pytest.raises(RuntimeError, match="VOI_OUTAGE_SLEEP_S"):
            elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=outage.sleep)
    assert rows_of(con) == []
    con.close()


def test_a_billed_answer_in_flight_since_before_the_hold_does_not_skip_the_pause(study, monkeypatch,  # noqa: F811
                                                                                  capsys):
    """Review round 3: slot 1 is a slow billed call started before the
    window; the other worker's calls hit the limit at once. Its answer
    arrived after the hold, reset the streak, and every held slot was
    re-dispatched at once with no pause (two holds before the first pause).
    A held batch now always pauses."""
    seed = _seed_payload()
    state = {"active": True, "calls": 0}
    lock = threading.Lock()

    def get_provider(name):
        def call(prompt, model, system_prompt):
            with lock:
                state["calls"] += 1
                first = state["calls"] == 1
            text = answer(prompt, seed)
            if first:
                time.sleep(0.6)
                return {"result": text, "total_cost_usd": 0.01}, text, None
            time.sleep(0.02)
            if state["active"]:
                return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    def sleep(seconds):
        slept.append(seconds)
        state["active"] = False

    slept = []
    monkeypatch.setattr(elicit, "get_provider", get_provider)
    con, pid, jobs = plan(study)
    n_valid, _, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=2, sleep=sleep)
    out = capsys.readouterr().out
    before = out[:out.index("usage-limit outage: pausing")]
    assert before.count("dispatching stopped") == 1
    # the fifth zero-usage result holds the batch; at most one more was in flight on the other worker
    assert before.count("nothing billed, not stored, re-planned") <= elicit.OUTAGE_STREAK + 1
    assert (n_valid, n_cancelled) == (8, 0) and slept == [300.0] and summary["pauses"] == 1
    con.close()


def test_a_replanned_slot_is_never_counted_as_stored_and_pending(study, monkeypatch, capsys):  # noqa: F811
    """Review round 3: a paid JSON failure whose retry hit the outage put its
    slot in `stored` while the slot was re-planned, so the give-up line read
    '1 slot(s) of this run stored, 8 still pending' of 8 slots. The paid
    failure is stored and the slot counts as pending only; the interrupt
    line counts the same way."""
    calls = []

    def get_provider(name):
        def call(prompt, model, system_prompt):
            calls.append(prompt)
            if len(calls) == 1:
                return {"result": "not json", "total_cost_usd": 0.03}, '{"result": "not json"}', None
            return LIMIT_ENVELOPE, LIMIT_RAW, LIMIT_ERROR
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("VOI_OUTAGE_MAX_WAIT_S", "3600")
    con, pid, jobs = plan(study)
    _, cost, n_cancelled, summary = elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=lambda s: None)
    out = capsys.readouterr().out
    assert "; 0 slot(s) of it stored by this run, 8 still pending: re-run to resume" in out
    assert summary["unresolved"] == n_cancelled == 8 and cost == pytest.approx(0.03)
    assert [(r["valid"], r["error"][:5]) for r in rows_of(con)] == [(0, "json:")]
    calls.clear()

    def ctrl_c(seconds):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        elicit.run_jobs(con, study, pid, jobs, workers=1, sleep=ctrl_c)
    out = capsys.readouterr().out
    assert "0 of 8 slots stored (0 after the interruption)" in out
    assert len(rows_of(con)) == 2
    con.close()


def test_a_paid_cli_exit_records_its_cost_and_counts_as_billed():
    """Review round 3: attempt_once took cost 0 whenever call_claude gave no
    envelope, so a billed CLI exit 1 (sim2real g001 rows 638 and 642: 32,000
    output tokens, $0.177 and $0.167) did not reset the zero-usage streak
    and was left out of the run's total cost."""
    raw = json.dumps({**LIMIT_ENVELOPE, "total_cost_usd": 0.1774131,
                      "usage": {"input_tokens": 9, "output_tokens": 32000}})
    att = elicit.attempt_once(lambda p, m, s: (None, raw, "cli: exit 1: "), "p", "m")
    assert att["cost"] == pytest.approx(0.1774131) and elicit.billed([att])
    assert not claude_cli.is_usage_limit("cli: exit 1: ", raw)
    att = elicit.attempt_once(lambda p, m, s: (None, "Not logged in", "cli: exit 1: Not logged in"), "p", "m")
    assert att["cost"] == 0.0 and not elicit.billed([att])
