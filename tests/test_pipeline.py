"""End-to-end on a temporary synthetic two-stage study with fake providers:
the elicitation dry run, elicitation and resume, MC and replay, the paid-run
guards, failure handling and interruption (no CLI, no network)."""

import io
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pytest
import yaml

from voi_rank import db, elicit, mc
from voi_rank.fit import DECISION_PARAMS, INSTRUMENT_PARAMS
from voi_rank.providers import openrouter
from voi_rank.study import Study
from voi_rank.validate import fit_all, validate_payload

ROOT = Path(__file__).resolve().parent.parent
_REAL_GIT_STATE = db.git_state   # captured before the hermetic fixture replaces it
SEED = {
    "p": {"reasoning": "r", "p5": 0.02, "p50": 0.08, "p95": 0.25},
    "s": {"reasoning": "r", "p5": 0.60, "p50": 0.80, "p95": 0.95},
    "t": {"reasoning": "r", "p5": 0.70, "p50": 0.90, "p95": 0.98},
    "B": {"reasoning": "r", "p5": 20e3, "p50": 150e3, "p95": 1.5e6},
    "K": {"reasoning": "r", "p5": 2e3, "p50": 10e3, "p95": 60e3},
    "C_build": {"reasoning": "r", "p5": 5e3, "p50": 20e3, "p95": 100e3},
    "C_run": {"reasoning": "r", "p5": 300, "p50": 1000, "p95": 5000},
    "n": {"reasoning": "r", "p5": 2, "p50": 10, "p95": 50},
}
HAIKU, OR_MEMBER = "claude_cli:haiku", "openrouter:fake/model"
INSTRUMENT = ["--stage", "instrument"]


def _seed_payload() -> dict:
    return json.loads(json.dumps(SEED))


def stage_params(prompt: str) -> list[str]:
    """The parameters the prompt asks for (the fixture's templates carry a
    DECISION-level / INSTRUMENT-level marker)."""
    return DECISION_PARAMS if "DECISION-level" in prompt else INSTRUMENT_PARAMS


def answer(prompt: str, seed: dict | None = None) -> str:
    """The JSON text a fake member answers to `prompt`: the stage's subset of
    the seed payload (the validator refuses any other parameter)."""
    seed = SEED if seed is None else seed
    return json.dumps({"parameters": {k: seed[k] for k in stage_params(prompt)}})


def scenario_list(n: int = 8) -> list[dict]:
    return [{"title": f"Scenario {i} of the synthetic study", "agent": f"Agent {i}",
             "decision": f"Decision {i}", "theta_definition": f"theta=1: condition {i} holds",
             "instrument": f"Instrument {i}", "decision_context": f"Decision facts for scenario {i}.",
             "instrument_context": f"Background for scenario {i}.",
             "group": "even" if i % 2 == 0 else "odd", "attributes": {"level": 1 + i % 3},
             "sources": [{"key": f"src{i}", "kind": "catalog", "ref": "research/catalog.json",
                          "role": "both"}],
             "domain_tags": ["synthetic"]} for i in range(n)]


DECISION_TEMPLATE = ("DECISION-level elicitation from the $perspective perspective.\nAgent: $agent\n"
                     "Decision: $decision\nState: $theta_definition\nFacts: $decision_context\n"
                     "$anchors_decision\n")
INSTRUMENT_TEMPLATE = ("INSTRUMENT-level elicitation.\nTitle: $title\nAgent: $agent\nDecision: $decision\n"
                       "State: $theta_definition\nInstrument: $instrument\nContext: $context\n"
                       "$anchors_instrument\n")


def protocol_cfg(name: str, members: list[dict], **extra) -> dict:
    return {"name": name, "notes": "test",
            "stages": [{"name": "decision", "template_path": "templates/decision.md",
                        "params": DECISION_PARAMS, "group_key": "self"},
                       {"name": "instrument", "template_path": "templates/instrument.md",
                        "params": INSTRUMENT_PARAMS}],
            "template_vars": {"perspective": "society",
                              "anchors_decision": "@file:templates/anchors_decision.md",
                              "anchors_instrument": "Anchor A1: instrument block."},
            "members": members, **extra}


@pytest.fixture
def study(tmp_path):
    root = tmp_path / "tmp_study"
    root.mkdir()
    (root / "scenarios.json").write_text(json.dumps(scenario_list()))
    (root / "protocols").mkdir()
    (root / "templates").mkdir()
    (root / "templates" / "decision.md").write_text(DECISION_TEMPLATE)
    (root / "templates" / "instrument.md").write_text(INSTRUMENT_TEMPLATE)
    (root / "templates" / "anchors_decision.md").write_text("Anchor A1: decision block.\n")
    (root / "protocols" / "p001.yaml").write_text(yaml.safe_dump(protocol_cfg("p001", [
        {"provider": "claude_cli", "model": "haiku", "k_repeats": 2},
        {"provider": "openrouter", "model": "fake/model", "k_repeats": 1}])))
    return Study.resolve(root)


def fake_provider_factory(seeds):
    """{provider name: seed payload}: every call answers its stage's subset."""
    def get_provider(name):
        def call(prompt, model, system_prompt):
            text = answer(prompt, seeds[name])
            return {"result": text, "total_cost_usd": 0.01}, json.dumps({"result": text,
                    "total_cost_usd": 0.01}), None
        return call
    return get_provider


def elicit_haiku(study, monkeypatch, k: int = 1, scenarios: str | None = None, stage: str | None = None):
    """Fill every haiku slot of p001 (k repeats, both stages unless `stage`)
    with the seed payload."""
    monkeypatch.setattr(elicit, "get_provider", fake_provider_factory({"claude_cli": SEED}))
    argv = ["--study", str(study.root), "--protocol", "p001", "--yes", "--members", HAIKU, "--k", str(k)]
    if scenarios:
        argv += ["--scenarios", scenarios]
    if stage:
        argv += ["--stage", stage]
    elicit.main(argv)


def test_study_paths(study):
    assert study.db == study.root / "voi.db"
    assert study.scenarios_json.exists()
    assert study.generated_dir == study.report_dir / "generated"
    assert study.protocol_path("p001") == study.protocols_dir / "p001.yaml"
    assert study.protocol_path("protocols/p001.yaml") == study.protocols_dir / "p001.yaml"
    with pytest.raises(FileNotFoundError):
        Study.resolve(study.root / "missing")


def test_mc_run_results_and_replay(study, monkeypatch):
    elicit_haiku(study, monkeypatch)
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0] == 8
    prot = db.protocol_by_name(con, "p001")
    rows = con.execute("SELECT stage, COUNT(*) AS n FROM elicitations WHERE protocol_id=? AND valid=1"
                       " GROUP BY stage", (prot["id"],)).fetchall()
    assert {r["stage"]: r["n"] for r in rows} == {"decision": 8, "instrument": 8}
    names = {r[0] for r in con.execute("SELECT DISTINCT name FROM parameters")}
    assert names == set(db.PARAM_NAMES)
    assert con.execute("SELECT COUNT(*) FROM parameters WHERE unit IS NOT NULL").fetchone()[0] == 0
    run_id = mc.run_mc(con, "p001", seed=1, n_draws=2000, quiet=True)
    metrics = {r[0] for r in con.execute("SELECT DISTINCT metric FROM results WHERE run_id=?", (run_id,))}
    assert metrics == set(mc.METRIC_NAMES) | set(mc.PROBABILITY_NAMES)
    params = {r[0] for r in con.execute("SELECT DISTINCT param FROM sensitivities WHERE run_id=?", (run_id,))}
    assert params == set(db.PARAM_NAMES)
    # probabilities are rows with q50 holding the value; the archived p_positive column stays NULL
    for name in mc.PROBABILITY_NAMES:
        for r in con.execute("SELECT * FROM results WHERE run_id=? AND metric=?", (run_id, name)):
            assert 0.0 <= r["q50"] <= 1.0 and r["q05"] is None and r["q95"] is None
            assert r["p_positive"] is None
    assert con.execute("SELECT COUNT(*) FROM results WHERE run_id=? AND p_positive IS NOT NULL",
                       (run_id,)).fetchone()[0] == 0
    # the stored quantiles match the model at the draws
    stored = {(r["scenario_id"], r["metric"]): r for r in con.execute(
        "SELECT * FROM results WHERE run_id=?", (run_id,))}
    for sid, draws in mc.iter_scenario_draws(mc.complete_fits(con, prot["id"]), 1, 2000):
        m = mc.scenario_metrics(draws)
        assert stored[(sid, "C")]["q50"] == pytest.approx(float(np.median(m["C"])))
        assert stored[(sid, "p_changes")]["q50"] == pytest.approx(float((m["EVSI"] > 0).mean()))
        assert stored[(sid, "p_pays")]["q50"] == pytest.approx(float(m["pays"].mean()))
        assert stored[(sid, "eta")]["q05"] <= stored[(sid, "eta")]["q50"] <= stored[(sid, "eta")]["q95"]
        finite = m["n_star"][np.isfinite(m["n_star"])]
        assert stored[(sid, "n_star")]["q50"] == pytest.approx(float(np.median(finite)))
    ids, eff = mc.replay_efficiency(con, run_id)
    assert len(ids) == 8 and eff.shape == (8, 2000)
    assert sum(mc.stored_probability(con, run_id, sid, "p_top5") for sid in ids) <= 5.0 + 1e-9
    run = db.get_run(con, run_id)
    assert run["members_json"] is None and db.latest_run(con, "p001")["id"] == run_id


def test_dry_run_calls_nothing_and_writes_nothing(study, monkeypatch, capsys):
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: (_ for _ in ()).throw(AssertionError("provider called")))
    assert not study.db.exists()
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY RUN: protocol p001 (stages decision + instrument, hash" in out
    assert "scenarios all, template_vars ['anchors_decision', 'anchors_instrument', 'perspective'])" in out
    assert "stage decision (template templates/decision.md, params p, B, K, group_key self):" in out
    assert f"member {HAIKU} (k=2): 16 pending slots over 8 groups (1, 2, 3, 4, 5, 6, 7, 8)" in out
    assert "stage instrument (template templates/instrument.md, params s, t, C_build, C_run, n):" in out
    assert f"member {OR_MEMBER} (k=1): 8 pending slots over 8 scenarios (ids 1..8)" in out
    dec, ins = out.split("first pending prompt of stage decision")[1].split(
        "first pending prompt of stage instrument")
    assert "(group '1', representative scenario 1," in dec
    assert "Facts: Decision facts for scenario 0." in dec and "Anchor A1: decision block." in dec
    assert "from the society perspective" in dec and "Instrument 0" not in dec and "Scenario 0" not in dec
    assert "Context: Background for scenario 0." in ins and "Anchor A1: instrument block." in ins
    assert "Decision facts" not in ins
    assert "48 slots would be elicited; no provider was called." in out
    # the plan and its cost estimate (DESIGN section 4), before the prompts
    assert "plan: protocol p001, 48 pending slots" in out
    assert f"{HAIKU}: 32 slots (decision 16, instrument 16), estimated cost unknown" in out
    assert f"{OR_MEMBER}: 16 slots (decision 8, instrument 8), estimated cost unknown" in out
    assert out.index("estimated total: $0.00 + unknown") < out.index("first pending prompt of stage decision")
    # side-effect free: no voi.db (or journal) was created, nothing registered on disk
    assert not list(study.root.glob("voi.db*"))
    # --members filter, --k override (the effective k is printed) and --stage
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run",
                 "--members", OR_MEMBER, "--k", "3", "--stage", "instrument"])
    out = capsys.readouterr().out
    assert "claude_cli" not in out.split("first pending prompt")[0]
    assert "    not planned (--stage instrument)" in out
    assert f"{OR_MEMBER} (k=3 (override of 1)): 24 pending slots over 8 scenarios" in out
    assert "first pending prompt of stage decision" not in out
    assert not study.db.exists()
    with pytest.raises(SystemExit):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run", "--k", "0"])
    # an existing DB is read, but left byte-identical
    elicit_haiku(study, monkeypatch, scenarios="1")
    before = study.db.read_bytes()
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    out = capsys.readouterr().out
    assert f"member {HAIKU} (k=2): 15 pending slots over 8 groups" in out
    assert f"member {HAIKU} (k=2): 15 pending slots over 8 scenarios" in out
    # the estimate uses the two stored haiku attempts ($0.01 each)
    assert (f"{HAIKU}: 30 slots (decision 15, instrument 15), estimated cost $0.30"
            " (mean $0.0100/attempt over 2 stored attempts)") in out
    assert "estimated total: $0.30 + unknown" in out
    assert study.db.read_bytes() == before


def _elicit_two_members(study, monkeypatch):
    """Elicit scenarios 1,2 under the two-member p001 with fake providers."""
    seed = _seed_payload()
    other = json.loads(json.dumps(seed))
    other["C_run"]["p50"] = seed["C_run"]["p50"] * 3   # the second member disagrees on C_run
    monkeypatch.setattr(elicit, "get_provider",
                        fake_provider_factory({"claude_cli": seed, "openrouter": other}))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--scenarios", "1,2",
                 "--workers", "2", "--yes"])
    return study.connect()


def test_fake_elicitation_pools_members_and_resumes(study, monkeypatch):
    con = _elicit_two_members(study, monkeypatch)
    prot = db.protocol_by_name(con, "p001")
    rows = con.execute("SELECT provider, model, repeat_ix, stage, valid FROM elicitations"
                       " WHERE protocol_id=? ORDER BY scenario_id, provider, repeat_ix",
                       (prot["id"],)).fetchall()
    assert len(rows) == 12 and all(r["valid"] for r in rows)
    assert {(r["provider"], r["model"]) for r in rows} == {("claude_cli", "haiku"),
                                                          ("openrouter", "fake/model")}
    assert {r["stage"] for r in rows} == {"decision", "instrument"}
    # pooled: 3 fits per parameter per scenario, both members present, at both stages
    fits = db.scenario_param_fits(con, prot["id"])
    assert len(fits[1]["C_run"]) == 3 and len(fits[1]["p"]) == 3
    assert {f["provider"] for f in fits[1]["C_run"]} == {"claude_cli", "openrouter"}
    # under group_key self a scenario's decision fits are its own, not shared
    assert {f["elicitation_id"] for f in fits[1]["p"]}.isdisjoint({f["elicitation_id"] for f in fits[2]["p"]})
    # resume: nothing pending for the same slots
    _, jobs = elicit.plan_jobs(con, study, prot["id"], "1,2", None, None)
    assert jobs == []
    _, jobs = elicit.plan_jobs(con, study, prot["id"], "1,2", 3, None)
    assert len(jobs) == 2 * 2 * (1 + 2)  # k=3: 1 more claude + 2 more openrouter slots per scenario and stage
    run_id = mc.run_mc(con, "p001", seed=3, n_draws=1000, quiet=True)
    assert con.execute("SELECT COUNT(DISTINCT scenario_id) FROM results WHERE run_id=?",
                       (run_id,)).fetchone()[0] == 2
    # a member subset is its own run: only that member's fits, stored on the run
    sub = mc.run_mc(con, "p001", seed=3, n_draws=1000, quiet=True, members=[OR_MEMBER])
    run = db.get_run(con, sub)
    assert json.loads(run["members_json"]) == [OR_MEMBER]
    assert run["data_hash"] != db.get_run(con, run_id)["data_hash"]
    fits_sub = mc.complete_fits(con, prot["id"], [OR_MEMBER])
    assert all(len(fits_sub[s][n]) == 1 for s in fits_sub for n in db.PARAM_NAMES)
    assert db.latest_run(con, "p001")["id"] == run_id
    assert db.latest_run(con, "p001", [OR_MEMBER])["id"] == sub
    assert db.latest_run(con, "p001", [HAIKU, OR_MEMBER])["id"] == run_id   # every member: the all-member run
    with pytest.raises(SystemExit, match="--members"):
        mc.run_mc(con, "p001", seed=3, n_draws=100, quiet=True, members=["nope:x"])
    with pytest.raises(RuntimeError, match=r"no runs in DB under protocol 'p001' with members \[claude_cli"):
        db.latest_run(con, "p001", [HAIKU])
    ids, eff = mc.replay_efficiency(con, sub)
    assert ids == [1, 2] and eff.shape == (2, 1000)
    assert db.run_members(con, run) == db.protocol_members(prot)[1:]


# --- guards, failure handling, scope -----------------------------------------

def test_paid_run_needs_yes_and_prints_plan(study, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: lambda *a: calls.append(name) or (_ for _ in ()).throw(
                            AssertionError("provider called")))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    with pytest.raises(SystemExit, match="--yes"):  # stdin is not a TTY under pytest
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--scenarios", "1"])
    out = capsys.readouterr().out
    assert "plan: protocol p001, 6 pending slots" in out
    assert f"{HAIKU}: 4 slots (decision 2, instrument 2), estimated cost unknown" in out
    assert f"{OR_MEMBER}: 2 slots (decision 1, instrument 1), estimated cost unknown" in out
    assert "estimated total: $0.00 + unknown" in out
    assert calls == []
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0] == 0
    # with stored attempts the estimate uses the member's mean cost per attempt
    con.close()
    _elicit_two_members(study, monkeypatch)
    capsys.readouterr()
    with pytest.raises(SystemExit, match="--yes"):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--scenarios", "1,2",
                     "--k", "3"])
    out = capsys.readouterr().out
    assert (f"{HAIKU}: 4 slots (decision 2, instrument 2), estimated cost $0.04 (mean $0.0100/attempt over"
            " 8 stored") in out
    assert (f"{OR_MEMBER}: 8 slots (decision 4, instrument 4), estimated cost $0.08 (mean $0.0100/attempt"
            " over 4") in out
    assert "estimated total: $0.12" in out


def test_missing_openrouter_key_aborts_before_any_call(study, monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(openrouter, "ENV_FILE", tmp_path / "absent.env")
    calls = []
    monkeypatch.setattr(elicit, "get_provider", lambda name: lambda *a: calls.append(name))
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes"])
    assert calls == []
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0] == 0
    # a claude_cli-only selection needs no key
    elicit_haiku(study, monkeypatch, scenarios="1")
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1").fetchone()[0] == 2


def test_provider_exception_and_failed_job_do_not_stop_the_run(study, monkeypatch, capsys):
    agents = [sc["agent"] for sc in scenario_list()]

    def get_provider(name):
        def call(prompt, model, system_prompt):
            if name == "openrouter":
                raise ConnectionResetError("peer reset")
            text = answer(prompt)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    real_job = elicit.elicit_job

    def job(call, prompt, model, **kw):
        if f"Agent: {agents[4]}\n" in prompt and model == "haiku":  # scenario 5: the worker itself dies
            raise RuntimeError("worker crashed")
        return real_job(call, prompt, model, **kw)

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setattr(elicit, "elicit_job", job)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--scenarios", "1,5",
                 "--yes", "--workers", "2"])
    con = study.connect()
    rows = con.execute("SELECT scenario_id, provider, valid, error FROM elicitations"
                       " ORDER BY id").fetchall()
    orr = [r for r in rows if r["provider"] == "openrouter"]
    assert len(orr) == 8  # 2 scenarios x 2 stages x (attempt + immediate retry), every one stored
    assert {r["error"] for r in orr} == {"provider: ConnectionResetError: peer reset"}
    cl = [r for r in rows if r["provider"] == "claude_cli"]
    assert sum(r["valid"] for r in cl) == 4 and {r["scenario_id"] for r in cl if r["valid"]} == {1}
    crashed = [r for r in cl if not r["valid"]]
    assert [(r["scenario_id"], r["error"]) for r in crashed] == \
        [(5, "provider: RuntimeError: worker crashed")] * 4
    assert "done: 4/12 slots valid" in capsys.readouterr().out


def test_refusals_are_stored_as_their_own_class(study, monkeypatch, capsys):
    """A plain-text answer that declines is stored as 'refusal: <first 200
    chars>' (retried once, like a JSON failure); an OpenRouter
    content_filter finish is the same class; other non-JSON text stays a
    'json:' failure."""
    texts = {1: "I'm sorry, but I can't help with estimating the likelihood of bioweapon uplift. " * 5,
             2: "I cannot assist with this request.", 3: "Here is my best guess: about ten percent."}

    def get_provider(name):
        def call(prompt, model, system_prompt):
            sid = next(i for i in range(1, 9) if f"Agent: Agent {i - 1}\n" in prompt)
            text = texts.get(sid) or answer(prompt)
            return {"result": text, "total_cost_usd": 0.01}, json.dumps({"result": text}), None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--members", HAIKU, "--k", "1", "--yes",
                 "--scenarios", "1,2,3,4", *INSTRUMENT])
    out = capsys.readouterr().out
    con = study.connect()
    rows = con.execute("SELECT scenario_id, valid, error FROM elicitations ORDER BY id").fetchall()
    by_sid = {}
    for r in rows:
        by_sid.setdefault(r["scenario_id"], []).append(r["error"])
    assert len(by_sid[1]) == 2
    assert all(e.startswith("refusal: I'm sorry, but I can't help") for e in by_sid[1])
    assert all(len(e) <= len("refusal: ") + elicit.REFUSAL_CHARS for e in by_sid[1])
    assert by_sid[2] == ["refusal: I cannot assist with this request."] * 2
    assert all(e.startswith("json: result parse failed") for e in by_sid[3]) and by_sid[4] == [None]
    assert "done: 1/4 slots valid" in out
    assert elicit.refusal("Sorry, this is against my guidelines.") == \
        "refusal: Sorry, this is against my guidelines."
    assert elicit.refusal("I must decline to put numbers on this.").startswith("refusal: I must decline")
    assert elicit.refusal("I’m not able to provide that estimate").startswith("refusal:")
    assert elicit.refusal("content_filter") == "refusal: content_filter"
    assert elicit.refusal("I can help with that: 0.1") is None
    assert elicit.retry_delay("refusal: I cannot assist") == 0.0 and not elicit.halts_member("refusal: x")
    assert elicit.billed([{"error": "refusal: no", "cost": 0.0}])   # the model answered


def test_retry_policy_and_injected_sleep():
    good = json.dumps({"parameters": _seed_payload()})

    def seq(*errs):
        it = iter(errs)

        def call(prompt, model, system_prompt):
            e = next(it)
            return ({"result": good}, good, None) if e is None else (None, "", e)
        return call

    slept = []
    for status in (401, 402, 404):   # auth / credit / unknown model id: the member's environment
        att = elicit.elicit_job(seq(f"http: status {status}: denied", None), "p", "m",
                                sleep=slept.append)
        assert len(att) == 1 and att[0]["error"].startswith(f"http: status {status}")
        assert elicit.halts_member(att[0]["error"])
    # 400/403 are per-request outcomes (OpenRouter: invalid params; permissions,
    # guardrail or moderation flag): no retry, but the member is not halted
    for status in (400, 403):
        err = f"http: status {status}: " + '{"error":{"code":403,"message":"Your input was flagged"}}'
        att = elicit.elicit_job(seq(err, None), "p", "m", sleep=slept.append)
        assert len(att) == 1 and elicit.rejected_request(err) and elicit.retry_delay(err) is None
        assert not elicit.halts_member(err) and not elicit.names_key(err)
    assert elicit.names_key('http: status 403: {"error":{"message":"Insufficient permissions"}}')
    assert elicit.names_key('http: status 403: {"error":{"message":"Invalid API key"}}')
    # the echoed prompt never counts as naming the key
    assert not elicit.names_key('http: status 403: {"error":{"message":"flagged","metadata":'
                                '{"flagged_input":"the agent needs permission to deploy"}}}')
    # a CLI that cannot run at all is an environment error too: no retry, member halted
    for err in ("cli: 'claude' executable not found", "cli: exit 1: Not logged in · Please run /login",
                "cli: exit 1: Invalid API key", "cli: exit 2: authentication_error: expired"):
        att = elicit.elicit_job(seq(err, None), "p", "m", sleep=slept.append)
        assert len(att) == 1 and elicit.halts_member(err) and elicit.retry_delay(err) is None
    # a CLI call that did not finish (timeout, killed by a signal) is not retried
    # either: a hung CLI hangs again, and a killed child means an interrupt
    for err in ("cli: timeout after 600s", "cli: killed by signal 2: ", "cli: killed by signal 9: "):
        att = elicit.elicit_job(seq(err, None), "p", "m", sleep=slept.append)
        assert len(att) == 1 and elicit.retry_delay(err) is None and not elicit.halts_member(err)
    assert elicit.cli_timeout("cli: timeout after 600s") and not elicit.cli_timeout("cli: exit 1: x")
    for err in ("cli: exit 1: some other failure", "cli: is_error: overloaded", "cli: timeout after 600s",
                "http: status 500: x", "http: status 429: x", "refusal: content_filter", None):
        assert not elicit.halts_member(err)
    assert slept == []
    # once the run is interrupted no retry is launched, and a backoff is cut short
    stop = elicit.threading.Event()
    stop.set()
    att = elicit.elicit_job(seq("json: bad", None), "p", "m", sleep=slept.append, stop=stop)
    assert len(att) == 1 and att[0]["error"] == "json: bad"
    att = elicit.elicit_job(seq("http: status 503: down", None), "p", "m", sleep=slept.append, stop=stop)
    assert len(att) == 1 and slept == []
    att = elicit.elicit_job(seq("json: bad", None), "p", "m", sleep=slept.append,
                            stop=elicit.threading.Event())
    assert len(att) == 2 and att[1]["error"] is None
    att = elicit.elicit_job(seq("http: status 429 retry-after 2s: slow", None), "p", "m",
                            sleep=slept.append)
    assert len(att) == 2 and att[1]["error"] is None and slept == [2.0]
    att = elicit.elicit_job(seq("http: status 503: down", None), "p", "m", sleep=slept.append)
    assert len(att) == 2 and slept == [2.0, elicit.TRANSPORT_RETRY_DELAY_S]
    att = elicit.elicit_job(seq("http: <urlopen error timed out>", None), "p", "m",
                            sleep=slept.append)
    assert len(att) == 2 and slept[-1] == elicit.TRANSPORT_RETRY_DELAY_S
    # a huge Retry-After is clamped and the clamp is recorded on the attempt
    att = elicit.elicit_job(seq("http: status 429 retry-after 86400s: slow", None), "p", "m",
                            sleep=slept.append)
    assert slept[-1] == elicit.MAX_RETRY_DELAY_S == 120.0
    assert att[0]["error"] == "http: status 429 retry-after 86400s: slow (retry-after 86400s clamped to 120s)"
    assert att[1]["error"] is None
    assert elicit.retry_delay("http: status 503 retry-after 500s: x") == 120.0
    assert elicit.retry_delay("http: status 503 retry-after 30s: x") == 30.0
    slept.clear()
    for err in ("json: result parse failed", "schema: missing", "constraint: x", "fit: y",
                "refusal: content_filter", "provider: RuntimeError: boom", "http: status 422: bad",
                "cli: exit 1: transient", "cli: is_error: overloaded"):
        att = elicit.elicit_job(seq(err, None), "p", "m", sleep=slept.append)
        assert len(att) == 2 and att[1]["error"] is None
    assert slept == []
    assert elicit.retry_delay(None) is None
    # a call whose provider raises becomes a 'provider:' attempt (retried once)
    def boom(prompt, model, system_prompt):
        raise ValueError("bad key")
    att = elicit.elicit_job(boom, "p", "m", sleep=slept.append)
    assert [a["error"] for a in att] == ["provider: ValueError: bad key"] * 2


def test_protocol_scenario_scope_is_the_default_selection(study, capsys):
    (study.protocols_dir / "p005.yaml").write_text(yaml.safe_dump(protocol_cfg(
        "p005", [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}], scenarios="4,2")))
    elicit.main(["--study", str(study.root), "--protocol", "p005", "--dry-run"])
    out = capsys.readouterr().out
    assert "scenarios 2,4," in out and "2 pending slots over 2 groups (2, 4)" in out
    assert "2 pending slots over 2 scenarios (ids 2..4)" in out and "warning" not in out
    elicit.main(["--study", str(study.root), "--protocol", "p005", "--dry-run",
                 "--scenarios", "seed"])
    out = capsys.readouterr().out
    assert "warning: protocol p005 scopes scenarios to '2,4'; --scenarios 'seed' overrides it" in out
    assert "8 pending slots over 8 scenarios" in out
    # an unscoped protocol narrowed on the CLI is a normal selection, not an override
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run",
                 "--scenarios", "1"])
    assert "warning" not in capsys.readouterr().out


def test_mc_refuses_dirty_code_unless_allowed_and_stores_data_hash(study, monkeypatch, capsys):
    elicit_haiku(study, monkeypatch)
    con = study.connect()
    monkeypatch.setattr(db, "git_state",
                        lambda cwd=None: ("deadbeef", [" M voi_rank/mc.py", "?? voi_rank/new.py"]))
    with pytest.raises(RuntimeError, match=r"uncommitted code changes \(2 path\(s\)\):\n"
                                            r"   M voi_rank/mc.py\n  \?\? voi_rank/new.py\n.*--allow-dirty"):
        mc.run_mc(con, "p001", seed=1, n_draws=500, quiet=True)
    assert con.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    run_id = mc.run_mc(con, "p001", seed=1, n_draws=500, quiet=True, allow_dirty=True)
    assert "WARNING: working tree has uncommitted changes" in capsys.readouterr().out
    run = db.get_run(con, run_id)
    assert run["code_hash"] == "deadbeef-dirty"
    expect = mc.data_hash(mc.complete_fits(con, run["protocol_id"]))
    assert run["data_hash"] == expect and len(expect) == 64
    # the CLI: refused without --allow-dirty, stored and printed with it
    con.close()
    with pytest.raises(RuntimeError, match="--allow-dirty"):
        mc.main(["--study", str(study.root), "--protocol", "p001", "--draws", "200"])
    mc.main(["--study", str(study.root), "--protocol", "p001", "--draws", "200", "--allow-dirty"])
    out = capsys.readouterr().out
    assert f"code_hash deadbeef-dirty, data_hash {expect}" in out and "Ranking by median eta (EVSI/C)" in out
    con = study.connect()
    # same elicitations, other seed: same data_hash; one more valid elicitation changes it
    monkeypatch.setattr(db, "git_state", lambda cwd=None: ("deadbeef", []))
    r2 = mc.run_mc(con, "p001", seed=2, n_draws=500, quiet=True)
    assert db.get_run(con, r2)["data_hash"] == expect and db.get_run(con, r2)["code_hash"] == "deadbeef"
    clean, err = validate_payload({"parameters": {k: SEED[k] for k in INSTRUMENT_PARAMS}}, INSTRUMENT_PARAMS)
    fits, err = fit_all(clean)
    elicit.store_attempts(con, 1, run["protocol_id"], {"provider": "claude_cli", "model": "haiku"}, 1, "h",
                          [{"raw": "{}", "error": None, "clean": clean, "fits": fits, "cost": 0.0}],
                          stage="instrument")
    r3 = mc.run_mc(con, "p001", seed=1, n_draws=500, quiet=True)
    assert db.get_run(con, r3)["data_hash"] != expect
    # the earlier run no longer replays (its valid-elicitation set changed); r3 does,
    # and every stored eta summary and p_positive of r3 is verified
    with pytest.raises(RuntimeError, match="replay mismatch"):
        mc.replay_efficiency(con, run_id)
    mc.replay_efficiency(con, r3)
    for col, metric in (("q95", "eta"), ("q25", "eta"), ("q50", "p_positive")):
        con.execute(f"UPDATE results SET {col}={col}+0.5 WHERE run_id=? AND metric=? AND scenario_id=1",
                    (r3, metric))
        with pytest.raises(RuntimeError, match=f"eta {col if metric == 'eta' else 'p_positive'}"):
            mc.replay_efficiency(con, r3)
        con.execute(f"UPDATE results SET {col}={col}-0.5 WHERE run_id=? AND metric=? AND scenario_id=1",
                    (r3, metric))
    mc.replay_efficiency(con, r3)


# --- interruption, store failures, preflight, dry runs ---------------------------

def _fake_ok_provider(seed, calls, delay=0.0):
    def get_provider(name):
        def call(prompt, model, system_prompt):
            calls.append(name)
            if delay:
                time.sleep(delay)
            text = answer(prompt, seed)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call
    return get_provider


def test_interrupt_keeps_paid_work_and_submits_nothing_more(study, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(elicit, "get_provider", _fake_ok_provider(_seed_payload(), calls, delay=0.03))
    real_store = elicit.store_attempts
    stores = []

    def store(*a, **k):
        stores.append(1)
        if len(stores) == 3:
            raise KeyboardInterrupt  # Ctrl-C lands while the main thread handles the third result
        return real_store(*a, **k)

    monkeypatch.setattr(elicit, "store_attempts", store)
    argv = ["--study", str(study.root), "--protocol", "p001", "--members", HAIKU,
            "--k", "1", "--yes", "--workers", "2", *INSTRUMENT]
    with pytest.raises(KeyboardInterrupt):
        elicit.main(argv)
    out = capsys.readouterr().out
    made = len(calls)
    time.sleep(0.1)
    assert len(calls) == made          # nothing was submitted after the interrupt
    con = study.connect()
    stored = con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0]
    assert stored == made and 3 <= made < 8   # every paid call is stored, the running ones included
    assert "interrupted (KeyboardInterrupt)" in out and "pending slots cancelled" in out
    assert f"{stored} of 8 slots stored" in out and "re-run to resume" in out
    assert not (study.root / elicit.UNSTORED_FILE).exists()
    # resume fills exactly the cancelled slots
    monkeypatch.setattr(elicit, "store_attempts", real_store)
    elicit.main(argv)
    assert "done: " + f"{8 - stored}/{8 - stored} slots valid" in capsys.readouterr().out
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1").fetchone()[0] == 8


def test_store_failure_retries_once_then_spills_and_stops(study, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(elicit, "get_provider", _fake_ok_provider(_seed_payload(), calls, delay=0.05))
    monkeypatch.setattr(elicit, "STORE_RETRY_DELAY_S", 0.0)
    real_store = elicit.store_attempts
    failures = [sqlite3.OperationalError("database is locked")]

    def store(*a, **k):
        if failures:
            raise failures.pop()
        return real_store(*a, **k)

    monkeypatch.setattr(elicit, "store_attempts", store)
    base = ["--study", str(study.root), "--protocol", "p001", "--members", HAIKU,
            "--k", "1", "--yes", "--workers", "1", *INSTRUMENT]
    elicit.main(base + ["--scenarios", "1,2,3,4"])
    out = capsys.readouterr().out
    assert "failed (database is locked); retrying in 0s" in out and "done: 4/4 slots valid" in out
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1").fetchone()[0] == 4
    assert not (study.root / elicit.UNSTORED_FILE).exists()
    # an unrecoverable failure: the attempts go to the spill file, the run stops
    calls.clear()
    failures.append(sqlite3.IntegrityError("UNIQUE constraint failed: elicitations.scenario_id"))
    with pytest.raises(elicit.StoreFailed, match=r"could not store scenario 5 stage instrument"
                                                 r" claude_cli:haiku repeat 0: IntegrityError: UNIQUE"
                                                 r".*elicit_unstored\.jsonl"):
        elicit.main(base + ["--scenarios", "5,6,7,8"])
    out = capsys.readouterr().out
    spilled = [json.loads(line) for line in (study.root / elicit.UNSTORED_FILE).read_text().splitlines()]
    assert len(spilled) == 1 and spilled[0]["scenario_id"] == 5 and spilled[0]["stage"] == "instrument"
    assert spilled[0]["store_error"].startswith("IntegrityError")
    assert spilled[0]["attempts"][0]["error"] is None
    assert json.loads(spilled[0]["attempts"][0]["raw"]) == \
        {"parameters": {k: SEED[k] for k in INSTRUMENT_PARAMS}}
    stored = con.execute("SELECT COUNT(*) FROM elicitations WHERE scenario_id IN (5,6,7,8)").fetchone()[0]
    assert stored + len(spilled) == len(calls) < 4   # paid calls are stored or spilled; the rest never ran
    assert "interrupted (StoreFailed)" in out and "pending slots cancelled" in out


def test_rejected_openrouter_key_aborts_before_any_call(study, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(elicit, "get_provider", lambda name: lambda *a: calls.append(name))
    monkeypatch.setenv("OPENROUTER_API_KEY", "wrong-key-not-real")

    def reject(req, timeout=None):
        assert req.full_url == openrouter.AUTH_URL and req.get_method() == "GET"
        assert req.get_header("Authorization") == "Bearer wrong-key-not-real"
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {},
                                     io.BytesIO(b'{"error": {"message": "User not found."}}'))

    monkeypatch.setattr(urllib.request, "urlopen", reject)
    argv = ["--study", str(study.root), "--protocol", "p001", "--scenarios", "1"]
    with pytest.raises(RuntimeError, match=r"rejected OPENROUTER_API_KEY \(status 401\).*User not found"):
        elicit.main(argv + ["--yes"])
    out = capsys.readouterr().out
    assert "plan: protocol p001" in out and "eliciting" not in out   # after the plan, before any job
    assert calls == []
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0] == 0
    con.close()
    # the preflight never runs on a dry run or without confirmation
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("preflight called")))
    elicit.main(argv + ["--dry-run"])
    with pytest.raises(SystemExit, match="--yes"):
        elicit.main(argv)
    # nor for a claude_cli-only selection
    monkeypatch.setattr(elicit, "get_provider", _fake_ok_provider(_seed_payload(), calls))
    elicit.main(argv + ["--yes", "--members", HAIKU, "--k", "1"])
    assert calls == ["claude_cli"] * 2   # both stages of scenario 1
    # a verified key is reported (label and usage only; the key itself is never printed)
    capsys.readouterr()
    monkeypatch.setattr(urllib.request, "urlopen", _key_ok)
    calls.clear()
    elicit.main(argv + ["--yes", "--k", "1"])
    out = capsys.readouterr().out
    assert "OpenRouter key verified (label 'team', usage $2.5, limit $10)" in out
    assert "wrong-key-not-real" not in out
    assert calls == ["openrouter"] * 2   # the claude_cli slots of scenario 1 were filled above


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _key_ok(req, timeout=None):
    return _Resp(b'{"data": {"label": "team", "usage": 2.5, "limit": 10}}')


def test_member_with_auth_error_is_halted_and_the_rest_continues(study, monkeypatch, capsys):
    calls = {"claude_cli": 0, "openrouter": 0}

    def get_provider(name):
        def call(prompt, model, system_prompt):
            calls[name] += 1
            time.sleep(0.02)   # a call takes time, so the consumer sees each result before the next starts
            if name == "openrouter":
                return None, '{"error": {"message": "Insufficient credits"}}', \
                    "http: status 402: Insufficient credits"
            text = answer(prompt)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--k", "1", "--yes", "--workers", "1"])
    out = capsys.readouterr().out
    assert (f"member {OR_MEMBER}: http: status 402: Insufficient credits: a retry cannot help;"
            " cancelled its 15 pending slots") in out
    assert calls == {"claude_cli": 16, "openrouter": 1}
    assert re.search(r"done: 16/32 slots valid \(50\.0%\), 15 cancelled", out)
    con = study.connect()
    rows = con.execute("SELECT provider, valid, error FROM elicitations ORDER BY id").fetchall()
    assert sum(1 for r in rows if r["provider"] == "openrouter") == 1
    assert sum(r["valid"] for r in rows if r["provider"] == "claude_cli") == 16
    # the cancelled slots are simply pending again
    prot = db.protocol_by_name(con, "p001")
    _, jobs = elicit.plan_jobs(con, study, prot["id"], None, 1, None)
    assert len(jobs) == 16 and {db.member_label(j["member"]) for j in jobs} == {OR_MEMBER}


def test_environment_errors_halt_the_member_without_retry(study, monkeypatch, capsys):
    """An unknown model id (http 404) and a missing claude executable each
    cost one call, not two per slot: the member is halted at once."""
    calls = {"claude_cli": 0, "openrouter": 0}

    def get_provider(name):
        def call(prompt, model, system_prompt):
            calls[name] += 1
            time.sleep(0.02)
            if name == "openrouter":
                return None, '{"error": {"message": "No endpoints found"}}', \
                    "http: status 404: No endpoints found for fake/model"
            return None, "", "cli: 'claude' executable not found"
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--k", "1", "--yes", "--workers", "1"])
    out = capsys.readouterr().out
    # the worker may start the next openrouter slot before the main thread sees
    # the first failure; nothing beyond that runs, and no slot is retried
    assert calls["claude_cli"] == 1 and calls["openrouter"] <= 2
    assert (f"member {HAIKU}: cli: 'claude' executable not found: a retry cannot help;"
            " cancelled its 15 pending slots (fix the key, credits or model id") in out
    assert re.search(rf"member {OR_MEMBER}: http: status 404: No endpoints found for fake/model:"
                     r" a retry cannot help; cancelled its 1[45] pending slots", out)
    stored = calls["claude_cli"] + calls["openrouter"]
    assert re.search(rf"done: 0/32 slots valid \(0\.0%\), {32 - stored} cancelled", out)
    con = study.connect()
    rows = con.execute("SELECT provider, scenario_id, stage, error, COUNT(*) AS n FROM elicitations"
                       " GROUP BY provider, scenario_id, stage").fetchall()
    assert len(rows) == stored and all(r["n"] == 1 and r["error"] for r in rows)   # one attempt per slot


def test_interrupt_after_commit_stores_each_slot_once(study, monkeypatch, capsys):
    """Ctrl-C landing after a slot's commit but before its bookkeeping: the
    salvage recognises the slot in the DB instead of storing it again
    (invalid attempts have no unique index, so a re-store would silently
    duplicate rows and double-count the cost)."""
    calls = []

    def get_provider(name):
        def call(prompt, model, system_prompt):
            calls.append(name)
            time.sleep(0.03)
            raw = json.dumps({"result": "not json", "total_cost_usd": 0.05})
            return json.loads(raw), raw, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    real = elicit.store_or_spill
    stored = []

    def store_or_spill(*a, **k):
        ok = real(*a, **k)
        stored.append(1)
        if len(stored) == 2:
            raise KeyboardInterrupt   # after the commit, before handled.add
        return ok

    monkeypatch.setattr(elicit, "store_or_spill", store_or_spill)
    argv = ["--study", str(study.root), "--protocol", "p001", "--members", HAIKU,
            "--k", "1", "--yes", "--workers", "2", *INSTRUMENT]
    with pytest.raises(KeyboardInterrupt):
        elicit.main(argv)
    out = capsys.readouterr().out
    time.sleep(0.1)
    made = len(calls)
    con = study.connect()
    per_slot = con.execute(
        "SELECT scenario_id, COUNT(*) AS n FROM elicitations GROUP BY scenario_id").fetchall()
    # every paid call is stored exactly once: a slot handled before the
    # interrupt holds attempt + retry, a slot still running at the interrupt
    # launches no retry (1 or 2 attempts), and nothing is stored twice
    assert sum(r["n"] for r in per_slot) == made and all(1 <= r["n"] <= 2 for r in per_slot)
    assert sum(1 for r in per_slot if r["n"] == 2) >= 2   # the two slots stored before the interrupt
    cost = sum(db.envelope_cost(r[0]) for r in con.execute("SELECT raw_response FROM elicitations"))
    assert cost == pytest.approx(0.05 * made)
    assert f"{len(per_slot)} of 8 slots stored" in out and "could not store" not in out
    assert not (study.root / elicit.UNSTORED_FILE).exists()


def test_second_ctrl_c_during_the_wait_is_ignored(study, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(elicit, "get_provider", _fake_ok_provider(_seed_payload(), calls, delay=0.05))
    real_store = elicit.store_attempts
    stores = []

    def store(*a, **k):
        stores.append(1)
        if len(stores) == 1:
            raise KeyboardInterrupt
        return real_store(*a, **k)

    monkeypatch.setattr(elicit, "store_attempts", store)
    real_wait = elicit.cf.wait
    waits = []

    def wait(fs, *a, **k):
        waits.append(1)
        if len(waits) == 1:
            raise KeyboardInterrupt   # the user hits Ctrl-C again while the running calls are awaited
        return real_wait(fs, *a, **k)

    monkeypatch.setattr(elicit.cf, "wait", wait)
    with pytest.raises(KeyboardInterrupt):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--members", HAIKU,
                     "--k", "1", "--yes", "--workers", "2", *INSTRUMENT])
    out = capsys.readouterr().out
    time.sleep(0.1)
    assert len(waits) == 2
    assert "Ctrl-C ignored:" in out and "their results are stored before the run exits" in out
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1").fetchone()[0] == len(calls) >= 1
    assert f"{len(calls)} of 8 slots stored" in out


# --- retirement, dry-run tense, provenance ------------------------------------------

def test_renamed_seed_scenario_is_retired_from_the_plan(study, monkeypatch, capsys):
    """The README's fix for a frozen scenario (change the title) must not
    leave the old row in every later 'all' / 'seed' plan: it is retired,
    kept with its elicitations, and only the new id is pending."""
    elicit_haiku(study, monkeypatch)   # 8 seed rows, each elicited at both stages (frozen)
    scen = json.loads(study.scenarios_json.read_text())
    scen[7]["title"] = "Renamed eighth scenario"
    scen[7]["instrument_context"] = "New background."
    study.scenarios_json.write_text(json.dumps(scen))
    capsys.readouterr()
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    out = capsys.readouterr().out
    assert "scenario 8 " in out and "would be retired" in out
    assert f"{HAIKU} (k=2): 9 pending slots over 8 groups (1, 2, 3, 4, 5, 6, 7, 9)" in out
    assert f"{HAIKU} (k=2): 9 pending slots over 8 scenarios (ids 1..9)" in out
    con = study.connect()   # the dry run changed nothing on disk
    assert [r["id"] for r in db.get_scenarios(con, "all")] == list(range(1, 9))
    con.close()
    (study.protocols_dir / "p005.yaml").write_text(yaml.safe_dump(protocol_cfg(
        "p005", [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}], scenarios="seed")))
    elicit.main(["--study", str(study.root), "--protocol", "p005", "--dry-run"])
    assert "8 pending slots over 8 scenarios (ids 1..9)" in capsys.readouterr().out
    elicit_haiku(study, monkeypatch)   # a real run retires the row and fills the new one
    out = capsys.readouterr().out
    assert "scenario 8 " in out and ": retired (title no longer in scenarios.json" in out
    assert "done: 2/2 slots valid" in out
    con = study.connect()
    pid = db.get_or_create_protocol(con, study.protocol_path("p001"), study.root)
    _, jobs = elicit.plan_jobs(con, study, pid, None, None, None)
    assert sorted({j["scenario_id"] for j in jobs}) == [1, 2, 3, 4, 5, 6, 7, 9]
    assert {db.member_label(j["member"]) for j in jobs} == {HAIKU, OR_MEMBER}
    assert con.execute("SELECT source FROM scenarios WHERE id=8").fetchone()[0] == db.RETIRED_SOURCE
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE scenario_id=8").fetchone()[0] == 2


def test_dry_run_says_would_refresh(study, monkeypatch, capsys):
    elicit_haiku(study, monkeypatch)
    scen = json.loads(study.scenarios_json.read_text())
    scen.append({**scen[0], "title": "Unelicited ninth", "instrument_context": "v1"})
    study.scenarios_json.write_text(json.dumps(scen))
    con = study.connect()   # seed the ninth row on disk
    db.seed_scenarios(con, study.scenarios_json)
    con.close()
    capsys.readouterr()
    scen[8]["instrument_context"] = "v2"
    study.scenarios_json.write_text(json.dumps(scen))
    before = study.db.read_bytes()
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run", "--scenarios", "9"])
    out = capsys.readouterr().out
    assert ("scenario 9 'Unelicited ninth': would refresh ['instrument_context', 'raw_json'] from"
            " scenarios.json") in out
    assert "': refreshed" not in out and "Context: v2" in out   # the planned prompt uses the file
    assert study.db.read_bytes() == before
    con = study.connect()
    assert db.get_scenarios(con, "9")[0]["instrument_context"] == "v1"
    con.close()
    elicit_haiku(study, monkeypatch, scenarios="9")
    out = capsys.readouterr().out
    # the plan preview says 'would refresh', the confirmed run on the real DB 'refreshed'
    assert ("scenario 9 'Unelicited ninth': refreshed ['instrument_context', 'raw_json']"
            in out.split("eliciting")[0])
    con = study.connect()
    assert db.get_scenarios(con, "9")[0]["instrument_context"] == "v2"


def test_mc_refuses_an_unknown_code_revision_unless_allowed(study, monkeypatch, capsys):
    elicit_haiku(study, monkeypatch)
    con = study.connect()
    monkeypatch.setattr(db.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("git")))
    monkeypatch.setattr(db, "git_state", _REAL_GIT_STATE)
    assert db.git_state() == ("unknown", [])
    with pytest.raises(RuntimeError, match="code revision could not be determined .*--allow-dirty"):
        mc.run_mc(con, "p001", seed=1, n_draws=300, quiet=True)
    assert con.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    run_id = mc.run_mc(con, "p001", seed=1, n_draws=300, quiet=True, allow_dirty=True)
    assert "WARNING: code revision unknown" in capsys.readouterr().out
    assert db.get_run(con, run_id)["code_hash"] == "unknown"


def test_mc_draws_from_the_fits_its_data_hash_describes(study, monkeypatch):
    """One complete_fits() read per run: the draws come from the dict the
    data_hash was computed over, so a valid elicitation committed by another
    process between two reads cannot slip into the draws unhashed."""
    elicit_haiku(study, monkeypatch)
    con = study.connect()
    reads = []
    real = mc.complete_fits

    def counted(con_, pid, members=None):
        fits = real(con_, pid, members)
        reads.append(fits)
        return fits

    monkeypatch.setattr(mc, "complete_fits", counted)
    run_id = mc.run_mc(con, "p001", seed=1, n_draws=300, quiet=True)
    assert len(reads) == 1
    assert db.get_run(con, run_id)["data_hash"] == mc.data_hash(reads[0])
    ids, eff = mc.replay_efficiency(con, run_id)
    assert ids == sorted(reads[0]) and eff.shape == (8, 300)


def _fake_claude_bin(tmp_path: Path, envelope: str, sleep_s: float = 2.0) -> tuple[Path, Path]:
    """A `claude` executable for PATH: answers --version, and for a `-p` call
    records its start in <marks>/started.<pid>, sleeps and prints
    `envelope`. Returns (bin dir, marks dir)."""
    bin_dir, marks = tmp_path / "bin", tmp_path / "marks"
    bin_dir.mkdir()
    marks.mkdir()
    (tmp_path / "envelope.json").write_text(envelope)
    script = bin_dir / "claude"
    script.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo "fake-claude 0.0"; exit 0; fi\n'
        f'touch "{marks}/started.$$"\n'
        f"sleep {sleep_s}\n"
        f'cat "{tmp_path / "envelope.json"}"\n')
    script.chmod(0o755)
    return bin_dir, marks


def test_terminal_ctrl_c_reaches_only_the_harness(study, tmp_path):
    """A terminal's Ctrl-C is SIGINT to the whole foreground process group.
    The real claude_cli provider (fake `claude` binary on PATH) runs each
    child in its own session, so os.killpg on the harness's group interrupts
    only the main thread: the two running calls finish, their result is
    stored once with its raw response, and no further call is launched
    (without start_new_session the children die with exit -2 and the harness
    launched a paid retry for each after the interrupt). The driver plans
    the instrument stage of four scenarios."""
    envelope = json.dumps({"result": json.dumps({"parameters": {k: SEED[k] for k in INSTRUMENT_PARAMS}}),
                           "total_cost_usd": 0.01})
    bin_dir, marks = _fake_claude_bin(tmp_path, envelope)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}", "PYTHONPATH": str(ROOT)}
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "tests" / "sigint_driver.py"), str(study.root)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env=env, cwd=str(ROOT), start_new_session=True)
    try:
        deadline = time.time() + 30
        while len(list(marks.glob("started.*"))) < 2:   # both workers have a child running
            assert proc.poll() is None, proc.stdout.read()
            assert time.time() < deadline, "the fake claude never started"
            time.sleep(0.02)
        os.killpg(proc.pid, signal.SIGINT)   # what the terminal does on Ctrl-C
        out, _ = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
    assert proc.returncode == 130, out
    assert ("interrupted (KeyboardInterrupt): 2 pending slots cancelled, waiting for 2 running"
            " call(s) to store their results") in out
    assert "driver: KeyboardInterrupt re-raised" in out and "2 of 4 slots stored" in out
    started = sorted(marks.glob("started.*"))
    assert len(started) == 2   # no call launched after the interrupt (no retry, nothing pending)
    con = study.connect()
    rows = con.execute("SELECT scenario_id, valid, raw_response, error, stage FROM elicitations"
                       " ORDER BY id").fetchall()
    assert len(rows) == 2 and sorted(r["scenario_id"] for r in rows) == [1, 2]
    assert all(r["valid"] == 1 and r["error"] is None and r["raw_response"] == envelope for r in rows)
    assert {r["stage"] for r in rows} == {"instrument"}
    assert "killed by signal" not in out and not (study.root / elicit.UNSTORED_FILE).exists()


def test_declined_plan_writes_nothing_and_keeps_the_template_editable(study, monkeypatch, capsys):
    """A declined (or non-TTY, no --yes) paid plan creates no voi.db and
    registers no protocol, so the study's templates can still be edited;
    the same holds when the DB already exists. The confirmed run then seeds,
    registers and submits on the real DB."""
    calls = []
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: lambda *a: calls.append(name) or (_ for _ in ()).throw(
                            AssertionError("provider called")))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    assert not list(study.root.glob("voi.db*"))
    with pytest.raises(SystemExit, match="--yes.*nothing was written"):
        elicit.main(["--study", str(study.root), "--protocol", "p001"])
    out = capsys.readouterr().out
    assert "plan: protocol p001, 48 pending slots" in out and calls == []
    assert not list(study.root.glob("voi.db*"))   # not even the DB
    template = study.templates_dir / "decision.md"
    template.write_text(template.read_text() + "One more line.\n")   # still editable: no hash frozen
    anchors = study.templates_dir / "anchors_decision.md"
    anchors.write_text("Anchor A1: decision block, revised.\n")
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    assert "48 slots would be elicited" in capsys.readouterr().out
    assert not list(study.root.glob("voi.db*"))
    # an existing DB (seeded, no protocol) is left byte-identical and without the protocol
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    con.close()
    before = study.db.read_bytes()
    capsys.readouterr()
    with pytest.raises(SystemExit, match="--yes"):
        elicit.main(["--study", str(study.root), "--protocol", "p001"])
    assert "plan: protocol p001, 48 pending slots" in capsys.readouterr().out
    assert study.db.read_bytes() == before
    con = study.connect()
    assert [r[0] for r in con.execute("SELECT name FROM protocols")] == []
    con.close()
    # a failed preflight after the confirmation writes nothing either
    monkeypatch.setattr(elicit.claude_cli, "check_auth",
                        lambda: (_ for _ in ()).throw(RuntimeError("claude CLI is not logged in")))
    with pytest.raises(RuntimeError, match="not logged in"):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes"])
    assert study.db.read_bytes() == before and calls == []
    # the confirmed run seeds, registers the (edited) templates and submits
    monkeypatch.setattr(elicit.claude_cli, "check_auth", lambda: "claude CLI preflight: test")
    elicit_haiku(study, monkeypatch, scenarios="1")
    out = capsys.readouterr().out
    assert "claude CLI preflight: test" in out and "done: 2/2 slots valid" in out
    con = study.connect()
    prot = db.protocol_by_name(con, "p001")
    assert db.protocol_stages(prot)[0]["template_hash"] == db.sha256(template.read_text())
    assert db.protocol_template_vars(prot)["anchors_decision"] == "Anchor A1: decision block, revised.\n"
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1 AND provider='claude_cli'"
                       ).fetchone()[0] == 2
    # once registered, an edited anchors file (a template variable) is refused like a template edit
    con.close()
    anchors.write_text("Anchor A1: decision block, revised again.\n")
    with pytest.raises(RuntimeError, match=r"different \['template_hash', 'template_vars'\]"):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])


def test_rejected_request_is_one_slot_until_a_second_scenario(study, monkeypatch, capsys):
    """HTTP 403 (a moderation flag on one prompt) or 400 is a per-request
    outcome: the slot is stored invalid without a retry (unbilled) and the
    member's other slots run. The member is halted when it is rejected on a
    second distinct scenario, or at once when the response names the key."""
    flagged = '{"error":{"code":403,"message":"Your input was flagged","metadata":{"reasons":["cbrn"]}}}'
    reject = {2}
    calls = []
    scenarios = [{"id": i + 1, "title": sc["title"]} for i, sc in enumerate(scenario_list())]

    def get_provider(name):
        def call(prompt, model, system_prompt):
            sid = next(sc["id"] for sc in scenarios if sc["title"] in prompt)
            calls.append((name, sid))
            time.sleep(0.02)
            if name == "openrouter" and sid in reject:
                return None, flagged, f"http: status 403: {flagged}"
            text = answer(prompt)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    base = ["--study", str(study.root), "--protocol", "p001", "--members", OR_MEMBER,
            "--k", "1", "--yes", "--workers", "1", *INSTRUMENT]
    elicit.main(base + ["--scenarios", "1,2,3,4"])
    out = capsys.readouterr().out
    assert [sid for name, sid in calls] == [1, 2, 3, 4]   # one call per slot, no retry, no halt
    assert (f"scenario 2 stage instrument {OR_MEMBER} repeat 0: the request was rejected (http 400/403:"
            " invalid params, guardrail or moderation flag on this prompt, or permissions); stored invalid,"
            " not retried, not billed; the slot is pending on the next run") in out
    assert "cancelled its" not in out and "done: 3/4 slots valid (75.0%), total elicitation cost $0.03" in out
    con = study.connect()
    rows = con.execute("SELECT scenario_id, valid, error FROM elicitations WHERE provider='openrouter'"
                       " ORDER BY id").fetchall()
    assert [(r["scenario_id"], r["valid"]) for r in rows] == [(1, 1), (2, 0), (3, 1), (4, 1)]
    assert rows[1]["error"].startswith("http: status 403")
    # the flagged slot is pending again on the next run (and rejected again)
    calls.clear()
    elicit.main(base + ["--scenarios", "1,2,3,4"])
    assert calls == [("openrouter", 2)] and "done: 0/1 slots valid" in capsys.readouterr().out
    # rejected on a second distinct scenario: the member is halted, the rest cancelled
    reject.update({5, 6, 7, 8})
    calls.clear()
    elicit.main(base + ["--scenarios", "2,5,6,7,8"])
    out = capsys.readouterr().out
    sids = [sid for name, sid in calls]
    assert sids[:2] == [2, 5] and len(sids) <= 3   # the single worker may have started a third
    assert f"member {OR_MEMBER}: http: status 403: " in out
    assert re.search(r": requests rejected on 2 distinct scenarios \[2, 5\]; cancelled its [23] pending"
                     r" slots", out)
    assert re.search(rf"done: 0/5 slots valid \(0\.0%\), {5 - len(sids)} cancelled", out)
    # a 403 whose message blames the key halts at once, like 401
    flagged = '{"error":{"code":403,"message":"This API key has insufficient permissions"}}'
    calls.clear()
    elicit.main(base + ["--scenarios", "5,6,7,8"])
    out = capsys.readouterr().out
    sids = [sid for name, sid in calls]
    assert sids[:1] == [5] and len(sids) <= 2
    assert re.search(r"the response names the key or its permissions; cancelled its [23] pending slots", out)
    # the same member on the other provider was never touched
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE provider='claude_cli'").fetchone()[0] == 0


def test_cli_timeouts_halt_the_member_after_two_in_a_row(study, monkeypatch, capsys):
    """A CLI that hangs (invalid ANTHROPIC_API_KEY: no output, no exit) costs
    one timeout per slot, never a retry, and the member is halted after its
    second consecutive timeout; a finished call in between resets the count."""
    hang = {1, 2, 3, 4}
    calls = []
    scenarios = [{"id": i + 1, "title": sc["title"]} for i, sc in enumerate(scenario_list())]

    def get_provider(name):
        def call(prompt, model, system_prompt):
            sid = next(sc["id"] for sc in scenarios if sc["title"] in prompt)
            calls.append(sid)
            time.sleep(0.02)
            if sid in hang:
                return None, "", "cli: timeout after 1s"
            text = answer(prompt)
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    base = ["--study", str(study.root), "--protocol", "p001", "--members", HAIKU,
            "--k", "1", "--yes", "--workers", "1", *INSTRUMENT]
    elicit.main(base + ["--scenarios", "1,2,3,4"])
    out = capsys.readouterr().out
    # no retry of a timeout; halted on the second in a row (the single worker
    # may have started the third slot before the main thread saw the second)
    assert calls[:2] == [1, 2] and len(calls) <= 3
    assert re.search(rf"member {HAIKU}: cli: timeout after 1s: 2 consecutive timeouts \(the CLI"
                     r" hangs with no output when its API key is invalid\); cancelled its [12] pending slots",
                     out)
    assert re.search(rf"done: 0/4 slots valid \(0\.0%\), {4 - len(calls)} cancelled", out)
    con = study.connect()
    rows = con.execute("SELECT scenario_id, COUNT(*) AS n FROM elicitations WHERE provider='claude_cli'"
                       " GROUP BY scenario_id").fetchall()
    assert [(r["scenario_id"], r["n"]) for r in rows] == [(sid, 1) for sid in calls]   # one attempt each
    # a completed call between two timeouts resets the count: no halt
    hang.clear()
    hang.update({3, 5})
    calls.clear()
    elicit.main(base + ["--scenarios", "3,4,5,6"])
    out = capsys.readouterr().out
    assert calls == [3, 4, 5, 6] and "cancelled its" not in out and "done: 2/4 slots valid" in out


def test_claude_cli_preflight_refuses_a_cli_that_is_not_logged_in(study, monkeypatch, tmp_path, capsys):
    """check_auth runs `claude auth status --json` (free): a missing
    executable, a non-zero exit or loggedIn false aborts the confirmed run
    with zero calls; a logged-in CLI is reported without its e-mail or key."""
    from voi_rank.providers import claude_cli
    monkeypatch.undo()   # the real check_auth, against a fake `claude` on PATH
    monkeypatch.setattr(db, "claude_cli_version", lambda: "test-cli")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "claude"
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")

    def fake(stdout: str, code: int):
        script.write_text(f"#!/bin/sh\nprintf '%s' '{stdout}'\nexit {code}\n")
        script.chmod(0o755)

    fake('{"loggedIn": false, "authMethod": "none"}', 1)   # CLI 2.1.280 with no credentials
    with pytest.raises(RuntimeError, match=r"claude CLI is not logged in \(exit 1, auth none\); run"
                                           r" `claude auth login` \(no elicitation call was made\)"):
        claude_cli.check_auth()
    fake('{"loggedIn": true, "authMethod": "claude.ai", "email": "x@y.z",'
         ' "apiKeySource": "ANTHROPIC_API_KEY"}', 0)
    line = claude_cli.check_auth()
    assert line == ("claude CLI logged in (auth claude.ai, API key source ANTHROPIC_API_KEY; the key itself"
                    " is not verified here)")
    fake("not json", 0)
    with pytest.raises(RuntimeError, match="not logged in"):
        claude_cli.check_auth()
    script.unlink()
    monkeypatch.setenv("PATH", str(bin_dir))
    with pytest.raises(RuntimeError, match="'claude' executable not found"):
        claude_cli.check_auth()
    # the harness: a failed preflight submits nothing and creates no voi.db
    calls = []
    monkeypatch.setattr(elicit, "get_provider", lambda name: lambda *a: calls.append(name))
    with pytest.raises(RuntimeError, match="'claude' executable not found"):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes", "--members", HAIKU])
    assert calls == [] and not list(study.root.glob("voi.db*"))
    assert "eliciting" not in capsys.readouterr().out
    # a claude_cli-free selection never runs the CLI preflight
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    monkeypatch.setattr(urllib.request, "urlopen", _key_ok)
    monkeypatch.setattr(elicit, "get_provider", fake_provider_factory({"openrouter": SEED}))
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes", "--members", OR_MEMBER,
                 "--scenarios", "1"])
    assert "done: 2/2 slots valid" in capsys.readouterr().out


def test_cli_timeout_setting_and_signal_exit(monkeypatch, tmp_path):
    """VOI_CLI_TIMEOUT_S comes from the environment, else .env; a child killed
    by a signal is reported as such (never retried) and the call runs in its
    own session."""
    from voi_rank import dotenv
    from voi_rank.providers import claude_cli
    monkeypatch.delenv("VOI_CLI_TIMEOUT_S", raising=False)
    monkeypatch.setattr(dotenv, "ENV_FILE", tmp_path / "absent.env")
    assert claude_cli.cli_timeout_s() == 600.0
    (tmp_path / "absent.env").write_text("VOI_CLI_TIMEOUT_S=45 # seconds\n")
    assert claude_cli.cli_timeout_s() == 45.0
    monkeypatch.setenv("VOI_CLI_TIMEOUT_S", "2.5")
    assert claude_cli.cli_timeout_s() == 2.5
    for bad in ("0", "-3", "soon"):
        monkeypatch.setenv("VOI_CLI_TIMEOUT_S", bad)
        with pytest.raises(RuntimeError, match="VOI_CLI_TIMEOUT_S"):
            claude_cli.cli_timeout_s()
    monkeypatch.setenv("VOI_CLI_TIMEOUT_S", "0.2")
    seen = {}

    def run(cmd, **kw):
        seen.update(kw)
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, -2, "", "")

    monkeypatch.setattr(claude_cli.subprocess, "run", run)
    env, raw, err = claude_cli.call_claude("prompt", "haiku", "sys")
    assert (env, raw, err) == (None, "", "cli: killed by signal 2: ")
    assert seen["start_new_session"] is True and seen["timeout"] == 0.2
    assert seen["cmd"][:3] == ["claude", "-p", "prompt"] and "--no-session-persistence" in seen["cmd"]
    assert elicit.retry_delay(err) is None and not elicit.halts_member(err)
    def hang(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(claude_cli.subprocess, "run", hang)
    assert claude_cli.call_claude("prompt", "haiku", "sys") == (None, "", "cli: timeout after 0.2s")
