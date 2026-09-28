"""End-to-end on a temporary study built from the business scenarios: manual
percentiles -> MC -> figures and tables -> replay, plus the elicitation
dry-run and a fake-provider elicitation (no CLI, no network)."""

import argparse
import io
import itertools
import json
import os
import re
import shutil
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

from voi_rank import db, drop_runs, elicit, mc, propose
from voi_rank.analysis import extra, figures, health, tables
from voi_rank.providers import get_provider, openrouter
from voi_rank.study import Study
from voi_rank.validate import fit_all, validate_payload

ROOT = Path(__file__).resolve().parent.parent
BUSINESS = ROOT / "studies" / "business"
_REAL_GIT_STATE = db.git_state   # captured before the hermetic fixture replaces it


@pytest.fixture
def study(tmp_path):
    root = tmp_path / "tmp_study"
    root.mkdir()
    scen = json.loads((BUSINESS / "scenarios.json").read_text())
    for i, sc in enumerate(scen):
        sc["group"] = "even" if i % 2 == 0 else "odd"
        sc["attributes"] = {"level": 1 + i % 3}
        sc["context"] = f"Background for scenario {i}."
    (root / "scenarios.json").write_text(json.dumps(scen))
    (root / "protocols").mkdir()
    (root / "templates").mkdir()
    shutil.copy(BUSINESS / "protocols" / "p000_manual.yaml", root / "protocols")
    (root / "templates" / "elicitor.md").write_text(
        "Title: $title\nAgent: $agent\nDecision: $decision\nState: $theta_definition\n"
        "Instrument: $instrument\nContext: $context\n")
    (root / "protocols" / "p001.yaml").write_text(yaml.safe_dump({
        "name": "p001", "template_path": "templates/elicitor.md",
        "members": [{"provider": "claude_cli", "model": "haiku", "k_repeats": 2},
                    {"provider": "openrouter", "model": "fake/model", "k_repeats": 1}],
        "notes": "test"}))
    return Study.resolve(root)


def test_study_paths(study):
    assert study.db == study.root / "voi.db"
    assert study.scenarios_json.exists()
    assert study.generated_dir == study.report_dir / "generated"
    assert study.protocol_path("p001") == study.protocols_dir / "p001.yaml"
    assert study.protocol_path("protocols/p001.yaml") == study.protocols_dir / "p001.yaml"
    with pytest.raises(FileNotFoundError):
        Study.resolve(study.root / "missing")


def test_manual_mc_figures_tables_replay(study):
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0] == 8
    prot = db.protocol_by_name(con, "p000_manual")
    n_valid = con.execute("SELECT COUNT(*) FROM elicitations WHERE protocol_id=? AND valid=1",
                          (prot["id"],)).fetchone()[0]
    assert n_valid == 8
    # stored parameters are the six v2 ones only (the seed file still carries e)
    names = {r[0] for r in con.execute("SELECT DISTINCT name FROM parameters")}
    assert names == set(db.PARAM_NAMES)

    run_id = mc.run_mc(con, "p000_manual", seed=1, n_draws=2000, quiet=True)
    metrics = {r[0] for r in con.execute("SELECT DISTINCT metric FROM results WHERE run_id=?",
                                          (run_id,))}
    assert metrics == set(mc.METRIC_NAMES) | {"p_top10"} and "evpi_efficiency" in metrics
    params = {r[0] for r in con.execute("SELECT DISTINCT param FROM sensitivities WHERE run_id=?",
                                         (run_id,))}
    assert params == set(db.PARAM_NAMES)
    ids, eff = mc.replay_efficiency(con, run_id)
    assert len(ids) == 8 and eff.shape == (8, 2000)
    # evpi_efficiency is the per-draw EVPI / C, summarised like efficiency
    stored = {r["scenario_id"]: r for r in con.execute(
        "SELECT * FROM results WHERE run_id=? AND metric='evpi_efficiency'", (run_id,))}
    for sid, draws in mc.iter_scenario_draws(mc.complete_fits(con, prot["id"]), 1, 2000):
        m = mc.scenario_metrics(draws)
        assert np.array_equal(m["evpi_efficiency"], m["EVPI"] / m["C"])
        assert stored[sid]["q50"] == pytest.approx(float(np.median(m["evpi_efficiency"])), rel=1e-9)
        assert stored[sid]["q05"] <= stored[sid]["q50"] <= stored[sid]["q95"]

    written = figures.make_all(con, run_id, study.generated_dir)
    assert "fig_evsi_vs_cost" in written and "fig_param_medians" in written
    assert "fig_by_level" in written  # scenarios carry attributes.level
    for name in written:
        assert (study.generated_dir / f"{name}.pdf").stat().st_size > 0
    tables.make_all(con, db.get_run(con, run_id), study.generated_dir)
    macros = (study.generated_dir / "macros.tex").read_text()
    assert r"\newcommand{\voiNMembers}{1}" in macros
    assert r"\voiMemberNameA" in macros and r"\voiMemberValidityA" in macros
    assert r"\voiGlobalE" not in macros and r"\voiNoiseE" not in macros
    catalog = (study.generated_dir / "catalog.tex").read_text()
    assert "$e$" not in catalog
    assert (study.generated_dir / "members.tex").exists()


def test_by_level_skipped_without_levels(tmp_path, study):
    scen = json.loads(study.scenarios_json.read_text())
    for sc in scen:
        sc.pop("attributes")
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    run_id = mc.run_mc(con, "p000_manual", seed=1, n_draws=500, quiet=True)
    assert figures.fig_by_level(con, run_id, study.generated_dir) is False


def test_dry_run_calls_nothing_and_writes_nothing(study, monkeypatch, capsys):
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: (_ for _ in ()).throw(AssertionError("provider called")))
    assert not study.db.exists()
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "scenarios all)" in out
    assert "claude_cli:haiku (k=2): 16 pending slots over 8 scenarios" in out
    assert "openrouter:fake/model (k=1): 8 pending slots over 8 scenarios" in out
    assert "Context: Background for scenario 0." in out  # $context substituted
    assert "24 slots would be elicited; no provider was called." in out
    # side-effect free: no voi.db (or journal) was created, nothing registered on disk
    assert not list(study.root.glob("voi.db*"))
    # --members filter and --k override (the effective k is printed)
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run",
                 "--members", "openrouter:fake/model", "--k", "3"])
    out = capsys.readouterr().out
    assert "claude_cli" not in out.split("first pending prompt")[0]
    assert "openrouter:fake/model (k=3 (override of 1)): 24 pending slots" in out
    assert not study.db.exists()
    with pytest.raises(SystemExit):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run", "--k", "0"])
    # an existing DB is read, but left byte-identical and without the protocol
    elicit.main(["--study", str(study.root), "--manual"])
    before = study.db.read_bytes()
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    out = capsys.readouterr().out
    assert "claude_cli:haiku (k=2): 16 pending slots over 8 scenarios" in out
    assert study.db.read_bytes() == before
    con = study.connect()
    assert [r[0] for r in con.execute("SELECT name FROM protocols")] == ["p000_manual"]
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE provider<>'manual'").fetchone()[0] == 0


def fake_provider_factory(responses):
    def get_provider(name):
        def call(prompt, model, system_prompt):
            text = json.dumps(responses[name])
            return {"result": text, "total_cost_usd": 0.01}, json.dumps({"result": text,
                    "total_cost_usd": 0.01}), None
        return call
    return get_provider


def _elicit_two_members(study, monkeypatch):
    """Elicit scenarios 1,2 under the two-member p001 with fake providers."""
    seed = json.loads(study.scenarios_json.read_text())[0]["manual"]
    other = json.loads(json.dumps(seed))
    other["C"]["p50"] = seed["C"]["p50"] * 3   # the second member disagrees on C
    monkeypatch.setattr(elicit, "get_provider", fake_provider_factory({
        "claude_cli": {"parameters": seed}, "openrouter": {"parameters": other}}))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--scenarios", "1,2",
                 "--workers", "2", "--yes"])
    return study.connect()


def test_fake_elicitation_pools_members_and_resumes(study, monkeypatch):
    con = _elicit_two_members(study, monkeypatch)
    prot = db.protocol_by_name(con, "p001")
    rows = con.execute("SELECT provider, model, repeat_ix, valid FROM elicitations"
                       " WHERE protocol_id=? ORDER BY scenario_id, provider, repeat_ix",
                       (prot["id"],)).fetchall()
    assert len(rows) == 6 and all(r["valid"] for r in rows)
    assert {(r["provider"], r["model"]) for r in rows} == {("claude_cli", "haiku"),
                                                          ("openrouter", "fake/model")}
    # pooled: 3 fits per parameter per scenario, both members present
    fits = db.scenario_param_fits(con, prot["id"])
    assert len(fits[1]["C"]) == 3
    assert {f["provider"] for f in fits[1]["C"]} == {"claude_cli", "openrouter"}
    # resume: nothing pending for the same slots
    _, jobs = elicit.plan_jobs(con, study, prot["id"], "1,2", None, None)
    assert jobs == []
    _, jobs = elicit.plan_jobs(con, study, prot["id"], "1,2", 3, None)
    assert len(jobs) == 2 * (1 + 2)  # k=3 override: 1 more claude slot + 2 more openrouter per scenario
    run_id = mc.run_mc(con, "p001", seed=3, n_draws=1000, quiet=True)
    assert con.execute("SELECT COUNT(DISTINCT scenario_id) FROM results WHERE run_id=?",
                       (run_id,)).fetchone()[0] == 2
    study.generated_dir.mkdir(parents=True)
    figures.plt.rcParams.update(figures.STYLE)
    assert figures.fig_param_medians(con, run_id, study.generated_dir)
    tables.make_all(con, db.get_run(con, run_id), study.generated_dir)
    macros = (study.generated_dir / "macros.tex").read_text()
    assert r"\newcommand{\voiNMembers}{2}" in macros
    assert r"\newcommand{\voiMemberValidityB}{100.0\%}" in macros
    assert r"\newcommand{\voiMemberCostB}{0.02}" in macros  # 2 scenarios x 1 repeat x $0.01
    # the catalog's C is the run's mixture median (what efficiency divides by), not the
    # median of the elicited p50s (the members disagree on C by 3x here)
    catalog = (study.generated_dir / "catalog.tex").read_text()
    c_run = con.execute("SELECT q50 FROM results WHERE run_id=? AND scenario_id=1 AND metric='C'",
                        (run_id,)).fetchone()[0]
    row1 = next(line for line in catalog.splitlines() if line.startswith("1 & "))
    assert row1.endswith(f"& {tables.money(c_run)}\\\\") and "mixture median" in catalog
    # the noise table has one column per member with repeats: only claude_cli (k=2) qualifies
    noise = (study.generated_dir / "protocol_noise.tex").read_text()
    assert "protocol & p001\\\\" in noise and "member & claude\\_cli:haiku\\\\" in noise
    assert "openrouter" not in noise


def test_health_reports_per_member_and_agreement(study, monkeypatch, capsys):
    con = _elicit_two_members(study, monkeypatch)
    capsys.readouterr()
    health.health(con, "p001")
    out = capsys.readouterr().out
    assert "2 member(s)" in out
    assert "claude_cli:haiku (k=2): 4 attempts, 4 valid (100.0%), $0.04" in out
    assert "openrouter:fake/model (k=1): 2 attempts, 2 valid (100.0%), $0.02" in out
    assert "per-member cross-repeat p50 spread" in out
    assert "cross-member agreement" in out
    # identical percentiles for p across members: rho undefined (nan) with n=2 shared -> printed
    assert "C: claude_cli:haiku vs openrouter:fake/model: rho=" in out


# --- review fixes: guards, failure handling, scope, manual ------------------

def _seed_payload():
    return json.loads((BUSINESS / "scenarios.json").read_text())[0]["manual"]


def test_paid_run_needs_yes_and_prints_plan(study, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: lambda *a: calls.append(name) or (_ for _ in ()).throw(
                            AssertionError("provider called")))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    with pytest.raises(SystemExit, match="--yes"):  # stdin is not a TTY under pytest
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--scenarios", "1"])
    out = capsys.readouterr().out
    assert "plan: protocol p001, 3 pending slots" in out
    assert "claude_cli:haiku: 2 slots, estimated cost unknown" in out
    assert "openrouter:fake/model: 1 slots, estimated cost unknown" in out
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
    assert "claude_cli:haiku: 2 slots, estimated cost $0.02 (mean $0.0100/attempt over 4 stored" in out
    assert "openrouter:fake/model: 4 slots, estimated cost $0.04 (mean $0.0100/attempt over 2" in out
    assert "estimated total: $0.06" in out


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
    monkeypatch.setattr(elicit, "get_provider", fake_provider_factory(
        {"claude_cli": {"parameters": _seed_payload()}}))
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes",
                 "--members", "claude_cli:haiku", "--scenarios", "1", "--k", "1"])
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1").fetchone()[0] == 1


def test_provider_exception_and_failed_job_do_not_stop_the_run(study, monkeypatch, capsys):
    seed = _seed_payload()
    titles = [sc["title"] for sc in json.loads(study.scenarios_json.read_text())]

    def get_provider(name):
        def call(prompt, model, system_prompt):
            if name == "openrouter":
                raise ConnectionResetError("peer reset")
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    real_job = elicit.elicit_job

    def job(call, prompt, model, **kw):
        if titles[4] in prompt and model == "haiku":  # scenario 5: the worker itself dies
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
    assert len(orr) == 4  # 2 scenarios x (attempt + immediate retry), every one stored
    assert {r["error"] for r in orr} == {"provider: ConnectionResetError: peer reset"}
    cl = [r for r in rows if r["provider"] == "claude_cli"]
    assert sum(r["valid"] for r in cl) == 2 and {r["scenario_id"] for r in cl if r["valid"]} == {1}
    crashed = [r for r in cl if not r["valid"]]
    assert [(r["scenario_id"], r["error"]) for r in crashed] == \
        [(5, "provider: RuntimeError: worker crashed")] * 2
    assert "done: 2/6 slots valid" in capsys.readouterr().out


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
                "http: status 500: x", "http: status 429: x", "api: content_filter", None):
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
                "api: content_filter", "provider: RuntimeError: boom", "http: status 422: bad",
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


def test_manual_is_graceful_without_percentiles(study, capsys):
    """A study without manual inputs is reported and left unchanged: not even
    voi.db is created (the check runs before any connection)."""
    (study.protocols_dir / "p000_manual.yaml").unlink()
    elicit.main(["--study", str(study.root), "--manual"])
    assert "no manual percentiles in this study" in capsys.readouterr().out
    assert not list(study.root.glob("voi.db*"))
    shutil.copy(BUSINESS / "protocols" / "p000_manual.yaml", study.protocols_dir)
    scen = json.loads(study.scenarios_json.read_text())
    for sc in scen:
        sc.pop("manual", None)
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main(["--study", str(study.root), "--manual"])
    assert "no manual percentiles in this study" in capsys.readouterr().out
    assert not list(study.root.glob("voi.db*"))
    # an existing DB is left byte-identical
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    assert not study.db.exists()
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    con.close()
    before = study.db.read_bytes()
    elicit.main(["--study", str(study.root), "--manual"])
    assert study.db.read_bytes() == before


def test_manual_member_is_provider_manual_and_never_elicited(study):
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    prot = db.protocol_by_name(con, "p000_manual")
    assert db.protocol_members(prot) == [{"provider": "manual", "model": "manual", "k_repeats": 1}]
    assert {r[0] for r in con.execute("SELECT provider FROM elicitations")} == {"manual"}
    with pytest.raises(ValueError):
        get_provider("manual")
    with pytest.raises(SystemExit, match="--manual"):
        elicit.plan_jobs(con, study, prot["id"], None, None, None)


def test_protocol_scenario_scope_is_the_default_selection(study, capsys):
    (study.protocols_dir / "p005.yaml").write_text(yaml.safe_dump({
        "name": "p005", "template_path": "templates/elicitor.md", "scenarios": "4,2",
        "members": [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]}))
    elicit.main(["--study", str(study.root), "--protocol", "p005", "--dry-run"])
    out = capsys.readouterr().out
    assert "scenarios 2,4)" in out and "2 pending slots over 2 scenarios (ids 2..4)" in out
    assert "warning" not in out
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
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    monkeypatch.setattr(db, "git_state",
                        lambda cwd=None: ("deadbeef", [" M voi_rank/mc.py", "?? voi_rank/new.py"]))
    with pytest.raises(RuntimeError, match=r"uncommitted code changes \(2 path\(s\)\):\n"
                                            r"   M voi_rank/mc.py\n  \?\? voi_rank/new.py\n.*--allow-dirty"):
        mc.run_mc(con, "p000_manual", seed=1, n_draws=500, quiet=True)
    assert con.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    run_id = mc.run_mc(con, "p000_manual", seed=1, n_draws=500, quiet=True, allow_dirty=True)
    assert "WARNING: working tree has uncommitted changes" in capsys.readouterr().out
    run = db.get_run(con, run_id)
    assert run["code_hash"] == "deadbeef-dirty"
    expect = mc.data_hash(mc.complete_fits(con, run["protocol_id"]))
    assert run["data_hash"] == expect and len(expect) == 64
    # the report macros keep the suffix and carry the data hash
    tables.make_all(con, run, study.generated_dir)
    macros = (study.generated_dir / "macros.tex").read_text()
    assert r"\newcommand{\voiCodeHash}{deadbeef-dirty}" in macros
    assert f"\\newcommand{{\\voiDataHash}}{{{expect[:12]}}}" in macros
    # the CLI: refused without --allow-dirty, stored and printed with it
    con.close()
    with pytest.raises(RuntimeError, match="--allow-dirty"):
        mc.main(["--study", str(study.root), "--protocol", "p000_manual", "--draws", "200"])
    mc.main(["--study", str(study.root), "--protocol", "p000_manual", "--draws", "200", "--allow-dirty"])
    out = capsys.readouterr().out
    assert f"code_hash deadbeef-dirty, data_hash {expect}" in out
    con = study.connect()
    # same elicitations, other seed: same data_hash; one more valid elicitation changes it
    monkeypatch.setattr(db, "git_state", lambda cwd=None: ("deadbeef", []))
    r2 = mc.run_mc(con, "p000_manual", seed=2, n_draws=500, quiet=True)
    assert db.get_run(con, r2)["data_hash"] == expect and db.get_run(con, r2)["code_hash"] == "deadbeef"
    clean, err = validate_payload({"parameters": _seed_payload()})
    fits, err = fit_all(clean)
    elicit.store_attempts(con, 1, run["protocol_id"], {"provider": "manual", "model": "manual"}, 1, "h",
                          [{"raw": "{}", "error": None, "clean": clean, "fits": fits, "cost": 0.0}])
    r3 = mc.run_mc(con, "p000_manual", seed=1, n_draws=500, quiet=True)
    assert db.get_run(con, r3)["data_hash"] != expect
    # the earlier run no longer replays (its valid-elicitation set changed); r3 does,
    # and every stored efficiency summary of r3 is verified
    with pytest.raises(RuntimeError, match="replay mismatch"):
        mc.replay_efficiency(con, run_id)
    mc.replay_efficiency(con, r3)
    for col in ("q95", "q25", "p_positive"):
        con.execute(f"UPDATE results SET {col}={col}+0.5 WHERE run_id=? AND metric='efficiency'"
                    " AND scenario_id=1", (r3,))
        with pytest.raises(RuntimeError, match=f"efficiency {col}"):
            mc.replay_efficiency(con, r3)
        con.execute(f"UPDATE results SET {col}={col}-0.5 WHERE run_id=? AND metric='efficiency'"
                    " AND scenario_id=1", (r3,))
    mc.replay_efficiency(con, r3)


def test_analysis_cli_selects_run_by_protocol_and_scatter_uses_run_c(study, capsys):
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    r1 = mc.run_mc(con, "p000_manual", seed=1, n_draws=300, quiet=True)
    r2 = mc.run_mc(con, "p000_manual", seed=2, n_draws=300, quiet=True)
    con.close()
    with pytest.raises(RuntimeError, match="p001"):  # default protocol p001 has no run here
        figures.main(["--study", str(study.root)])
    figures.main(["--study", str(study.root), "--protocol", "p000_manual"])
    assert f"run {r2} (protocol p000_manual)" in capsys.readouterr().out
    tables.main(["--study", str(study.root), "--protocol", "p000_manual", "--run", str(r1)])
    out = capsys.readouterr().out
    assert f"run {r1} (protocol p000_manual)" in out and f"for run {r1}" in out
    # the scatter's x is the run's stored C median; pre-v2 runs (no C row) fall back
    # to the pooled elicited p50
    con = study.connect()
    run = db.get_run(con, r1)
    stored = con.execute("SELECT q50 FROM results WHERE run_id=? AND scenario_id=1 AND metric='C'",
                         (r1,)).fetchone()[0]
    assert figures.c_quantiles(con, run, 1)[1] == stored
    con.execute("DELETE FROM results WHERE run_id=? AND metric='C'", (r1,))
    con.commit()
    p50s = db.elicited_p50s(con, run["protocol_id"], 1, "C")
    assert figures.c_quantiles(con, run, 1)[1] == float(np.median(p50s))
    figures.plt.rcParams.update(figures.STYLE)
    assert figures.fig_evsi_vs_cost(con, r1, study.generated_dir)


# --- review fixes, round 2: interruption, store failures, preflight, dry runs ---

def _fake_ok_provider(seed, calls, delay=0.0):
    def get_provider(name):
        def call(prompt, model, system_prompt):
            calls.append(name)
            if delay:
                time.sleep(delay)
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call
    return get_provider


def test_manual_dry_run_writes_nothing(study, capsys):
    assert not study.db.exists()
    elicit.main(["--study", str(study.root), "--manual", "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY RUN: would load 8 manual scenarios under p000_manual" in out
    assert "0 already loaded" in out and "nothing was written" in out
    assert not list(study.root.glob("voi.db*"))
    elicit.main(["--study", str(study.root), "--manual"])
    before = study.db.read_bytes()
    elicit.main(["--study", str(study.root), "--manual", "--dry-run"])
    out = capsys.readouterr().out
    assert "would load 0 manual scenarios" in out and "8 already loaded" in out
    assert study.db.read_bytes() == before


def test_seed_refresh_and_manual_coexist(study, capsys):
    scen = json.loads(study.scenarios_json.read_text())
    for sc in scen[1:]:
        sc.pop("manual")
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main(["--study", str(study.root), "--manual"])
    assert "manual load: 1 scenarios valid" in capsys.readouterr().out
    # the README's refresh of an un-elicited scenario, then --manual again
    scen[1]["context"] = "Refreshed background."
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main(["--study", str(study.root), "--manual"])
    out = capsys.readouterr().out
    assert "refreshed ['context'" in out and "manual load: 0 scenarios valid" in out
    con = study.connect()
    assert db.get_scenarios(con, "2")[0]["context"] == "Refreshed background."
    assert db.protocol_by_name(con, "p000_manual")["template_hash"] == db.manual_hash(study.scenarios_json)


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
    argv = ["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
            "--k", "1", "--yes", "--workers", "2"]
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
    base = ["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
            "--k", "1", "--yes", "--workers", "1"]
    elicit.main(base + ["--scenarios", "1,2,3,4"])
    out = capsys.readouterr().out
    assert "failed (database is locked); retrying in 0s" in out and "done: 4/4 slots valid" in out
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1").fetchone()[0] == 4
    assert not (study.root / elicit.UNSTORED_FILE).exists()
    # an unrecoverable failure: the attempts go to the spill file, the run stops
    calls.clear()
    failures.append(sqlite3.IntegrityError("UNIQUE constraint failed: elicitations.scenario_id"))
    with pytest.raises(elicit.StoreFailed, match=r"could not store scenario 5 claude_cli:haiku repeat 0:"
                                                 r" IntegrityError: UNIQUE.*elicit_unstored\.jsonl"):
        elicit.main(base + ["--scenarios", "5,6,7,8"])
    out = capsys.readouterr().out
    spilled = [json.loads(line) for line in (study.root / elicit.UNSTORED_FILE).read_text().splitlines()]
    assert len(spilled) == 1 and spilled[0]["scenario_id"] == 5
    assert spilled[0]["store_error"].startswith("IntegrityError")
    assert spilled[0]["attempts"][0]["error"] is None
    assert spilled[0]["attempts"][0]["raw"] == json.dumps({"parameters": _seed_payload()})
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
    elicit.main(argv + ["--yes", "--members", "claude_cli:haiku", "--k", "1"])
    assert calls == ["claude_cli"]
    # a verified key is reported (label and usage only; the key itself is never printed)
    capsys.readouterr()
    monkeypatch.setattr(urllib.request, "urlopen", _key_ok)
    calls.clear()
    elicit.main(argv + ["--yes", "--k", "1"])
    out = capsys.readouterr().out
    assert "OpenRouter key verified (label 'team', usage $2.5, limit $10)" in out
    assert "wrong-key-not-real" not in out
    assert calls == ["openrouter"]   # the claude_cli slot of scenario 1 was filled above


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _key_ok(req, timeout=None):
    return _Resp(b'{"data": {"label": "team", "usage": 2.5, "limit": 10}}')


def test_member_with_auth_error_is_halted_and_the_rest_continues(study, monkeypatch, capsys):
    seed = _seed_payload()
    calls = {"claude_cli": 0, "openrouter": 0}

    def get_provider(name):
        def call(prompt, model, system_prompt):
            calls[name] += 1
            time.sleep(0.02)   # a call takes time, so the consumer sees each result before the next starts
            if name == "openrouter":
                return None, '{"error": {"message": "Insufficient credits"}}', \
                    "http: status 402: Insufficient credits"
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--k", "1", "--yes", "--workers", "1"])
    out = capsys.readouterr().out
    assert ("member openrouter:fake/model: http: status 402: Insufficient credits: a retry cannot help;"
            " cancelled its 7 pending slots") in out
    assert calls == {"claude_cli": 8, "openrouter": 1}
    assert re.search(r"done: 8/16 slots valid \(50\.0%\), 7 cancelled", out)
    con = study.connect()
    rows = con.execute("SELECT provider, valid, error FROM elicitations ORDER BY id").fetchall()
    assert sum(1 for r in rows if r["provider"] == "openrouter") == 1
    assert sum(r["valid"] for r in rows if r["provider"] == "claude_cli") == 8
    # the cancelled slots are simply pending again
    prot = db.protocol_by_name(con, "p001")
    _, jobs = elicit.plan_jobs(con, study, prot["id"], None, 1, None)
    assert len(jobs) == 8 and {db.member_label(j["member"]) for j in jobs} == {"openrouter:fake/model"}


def test_protocol_noise_table_is_per_member_at_matched_k(study, monkeypatch):
    seed = _seed_payload()
    counter = itertools.count(1)

    def get_provider(name):
        def call(prompt, model, system_prompt):
            n = next(counter)
            payload = json.loads(json.dumps(seed))
            for q in ("p5", "p50", "p95"):
                payload["C"][q] = seed["C"][q] * (1 + 0.5 * n)   # every call disagrees on C
            text = json.dumps({"parameters": payload})
            return {"result": text, "total_cost_usd": 0.0}, text, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    base = ["--study", str(study.root), "--protocol", "p001", "--scenarios", "1,2", "--yes", "--workers", "1"]
    elicit.main(base + ["--members", "claude_cli:haiku", "--k", "4"])
    elicit.main(base + ["--members", "openrouter:fake/model", "--k", "2"])
    con = study.connect()
    prot = db.protocol_by_name(con, "p001")
    members = db.protocol_members(prot)
    assert tables.repeated_members(con) == [("p001", members[0]), ("p001", members[1])]
    study.generated_dir.mkdir(parents=True)
    tables.write_protocol_noise(con, study.generated_dir)
    tex = (study.generated_dir / "protocol_noise.tex").read_text()
    assert "protocol & p001 & p001\\\\" in tex
    assert "member & claude\\_cli:haiku & openrouter:fake/model\\\\" in tex
    matched = tables.noise_median(con, prot["id"], "C", first=3, member=members[0])
    full = tables.noise_median(con, prot["id"], "C", member=members[0])
    other = tables.noise_median(con, prot["id"], "C", first=3, member=members[1])
    assert full > matched > 0 and other > 0   # first 3 of 4 repeats, per member
    assert f"$C$ & {matched:.2f} & {other:.2f}\\\\" in tex
    # a member with a single repeat has no column
    (study.protocols_dir / "p006.yaml").write_text(yaml.safe_dump({
        "name": "p006", "template_path": "templates/elicitor.md",
        "members": [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]}))
    elicit.main(["--study", str(study.root), "--protocol", "p006", "--scenarios", "1", "--yes"])
    assert [n for n, _ in tables.repeated_members(con)] == ["p001", "p001"]


def test_propose_plan_needs_yes_and_records_cost(study, monkeypatch, capsys):
    (study.templates_dir / "proposer.md").write_text("Domain: $domain, n=$n")
    calls = []
    items = [{"title": f"T{i}", "agent": "a", "decision": "d", "theta_definition": "t",
              "instrument": "i"} for i in (1, 2)]

    def fake_call(prompt, model, system_prompt):
        calls.append(prompt)
        return {"result": json.dumps(items), "total_cost_usd": 0.02}, "raw", None

    monkeypatch.setattr(propose, "call_claude", fake_call)
    argv = ["--study", str(study.root), "--domains", "energy,medicine", "--n", "2"]
    with pytest.raises(SystemExit, match="--yes"):   # stdin is not a TTY under pytest
        propose.main(argv)
    out = capsys.readouterr().out
    assert "plan: 2 domains x 2 scenarios = 4 scenarios, up to 4 claude_cli calls (model haiku" in out
    assert "estimated cost unknown" in out and calls == []
    assert not list(study.root.glob("voi.db*"))   # the plan was made on an in-memory copy
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM scenarios WHERE source LIKE 'proposer:%'").fetchone()[0] == 0
    propose.main(argv + ["--yes"])
    out = capsys.readouterr().out
    assert len(calls) == 2 and "inserted 4 new scenarios" in out and "cost $0.04" in out
    rows = con.execute("SELECT source, attributes FROM scenarios WHERE source LIKE 'proposer:%'").fetchall()
    assert sorted(r["source"] for r in rows) == ["proposer:energy"] * 2 + ["proposer:medicine"] * 2
    assert all(db.scenario_attributes(r)[propose.COST_ATTR] == pytest.approx(0.01) for r in rows)
    # the next plan estimates from the stored cost per proposed scenario
    with pytest.raises(SystemExit):
        propose.main(["--study", str(study.root), "--domains", "transport", "--n", "3"])
    assert "estimated cost $0.03 (mean $0.0100/scenario over 4 stored proposer scenarios)" in \
        capsys.readouterr().out


# --- review fixes, round 3: provenance guards, halts, salvage, propose, drop_runs ---

def test_analysis_refuses_v1_runs(study, capsys):
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    r1 = mc.run_mc(con, "p000_manual", seed=1, n_draws=300, quiet=True)
    con.execute("UPDATE runs SET data_hash=NULL WHERE id=?", (r1,))   # a run stored before provenance
    con.commit()
    assert db.run_predates_v2(con, db.get_run(con, r1)) == "it stores no data_hash"
    con.close()
    for mod in (figures, tables, extra):
        with pytest.raises(RuntimeError, match=rf"run {r1} \(protocol p000_manual\) predates the v2 model:"
                                                r" it stores no data_hash; run `python -m voi_rank.mc"
                                                r" --protocol p000_manual` first"):
            mod.main(["--study", str(study.root), "--protocol", "p000_manual"])
        with pytest.raises(RuntimeError, match="predates the v2 model"):   # an explicit --run too
            mod.main(["--study", str(study.root), "--run", str(r1)])
    assert not (study.generated_dir / "macros.tex").exists()
    con = study.connect()
    r2 = mc.run_mc(con, "p000_manual", seed=2, n_draws=300, quiet=True)
    con.execute("INSERT INTO sensitivities (run_id, scenario_id, param, spearman) VALUES (?, 1, 'e', 0.1)",
                (r2,))   # a v1-model run
    con.commit()
    assert db.run_predates_v2(con, db.get_run(con, r2)) == \
        "its sensitivities carry the retired v1 parameter e"
    r3 = mc.run_mc(con, "p000_manual", seed=3, n_draws=300, quiet=True)
    assert db.run_predates_v2(con, db.get_run(con, r3)) is None
    con.close()
    capsys.readouterr()
    tables.main(["--study", str(study.root), "--protocol", "p000_manual"])
    assert f"run {r3} (protocol p000_manual)" in capsys.readouterr().out
    with pytest.raises(RuntimeError, match=f"run {r2} .*retired v1 parameter e"):
        tables.main(["--study", str(study.root), "--run", str(r2)])


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
    assert ("member claude_cli:haiku: cli: 'claude' executable not found: a retry cannot help;"
            " cancelled its 7 pending slots (fix the key, credits or model id") in out
    assert re.search(r"member openrouter:fake/model: http: status 404: No endpoints found for fake/model:"
                     r" a retry cannot help; cancelled its [67] pending slots", out)
    stored = calls["claude_cli"] + calls["openrouter"]
    assert re.search(rf"done: 0/16 slots valid \(0\.0%\), {16 - stored} cancelled", out)
    con = study.connect()
    rows = con.execute("SELECT provider, scenario_id, error, COUNT(*) AS n FROM elicitations"
                       " GROUP BY provider, scenario_id").fetchall()
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
    argv = ["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
            "--k", "1", "--yes", "--workers", "2"]
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
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
                     "--k", "1", "--yes", "--workers", "2"])
    out = capsys.readouterr().out
    time.sleep(0.1)
    assert len(waits) == 2
    assert "Ctrl-C ignored:" in out and "their results are stored before the run exits" in out
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1").fetchone()[0] == len(calls) >= 1
    assert f"{len(calls)} of 8 slots stored" in out


def test_manual_dry_run_checks_the_frozen_hand_percentiles(study, capsys):
    """Hand percentiles are frozen per scenario: a loaded scenario whose
    numbers changed is refused (dry run and real load alike), while a new
    scenario with a manual block loads under the same p000_manual."""
    elicit.main(["--study", str(study.root), "--manual"])
    scen = json.loads(study.scenarios_json.read_text())
    scen[0]["manual"]["C"]["p50"] *= 2
    study.scenarios_json.write_text(json.dumps(scen))
    before = study.db.read_bytes()
    with pytest.raises(RuntimeError, match=r"1 scenario\(s\) carry hand percentiles that differ from the"
                                            r" numbers loaded under p000_manual:\n  1 '"):
        elicit.main(["--study", str(study.root), "--manual", "--dry-run"])
    assert study.db.read_bytes() == before
    with pytest.raises(RuntimeError, match="frozen"):   # the dry run predicts the real refusal
        elicit.main(["--study", str(study.root), "--manual"])
    # key order in the manual block is not a change
    scen[0]["manual"]["C"]["p50"] /= 2
    scen[0]["manual"] = dict(reversed(list(scen[0]["manual"].items())))
    study.scenarios_json.write_text(json.dumps(scen))
    capsys.readouterr()
    elicit.main(["--study", str(study.root), "--manual"])
    assert "manual load: 0 scenarios valid" in capsys.readouterr().out
    # a ninth scenario with hand percentiles is loaded, the eight stay frozen
    scen.append({**scen[1], "title": "Ninth, hand-entered later"})
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main(["--study", str(study.root), "--manual", "--dry-run"])
    out = capsys.readouterr().out
    assert "would load 1 manual scenarios under p000_manual" in out and "8 already loaded" in out
    elicit.main(["--study", str(study.root), "--manual"])
    assert "manual load: 1 scenarios valid" in capsys.readouterr().out
    con = study.connect()
    prot = db.protocol_by_name(con, "p000_manual")
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE protocol_id=? AND valid=1",
                       (prot["id"],)).fetchone()[0] == 9
    assert mc.run_mc(con, "p000_manual", seed=1, n_draws=300, quiet=True)


def test_propose_dry_run_and_declined_plan_create_no_db(study, monkeypatch, capsys):
    (study.templates_dir / "proposer.md").write_text("Domain: $domain, n=$n")
    monkeypatch.setattr(propose, "call_claude",
                        lambda *a: (_ for _ in ()).throw(AssertionError("provider called")))
    assert not study.db.exists()
    argv = ["--study", str(study.root), "--domains", "energy", "--n", "2"]
    propose.main(argv + ["--dry-run"])
    out = capsys.readouterr().out
    assert "plan: 1 domains x 2 scenarios = 2 scenarios" in out
    assert "DRY RUN: no call was made and nothing was written." in out
    assert not list(study.root.glob("voi.db*"))
    with pytest.raises(SystemExit, match="--yes"):
        propose.main(argv)
    assert not list(study.root.glob("voi.db*"))


def test_propose_interrupt_keeps_paid_work(study, monkeypatch, capsys):
    (study.templates_dir / "proposer.md").write_text("Domain: $domain, n=$n")
    calls = []

    def fake_call(prompt, model, system_prompt):
        calls.append(prompt)
        time.sleep(0.05)
        items = [{"title": f"T {prompt} {i}", "agent": "a", "decision": "d", "theta_definition": "t",
                  "instrument": "i"} for i in range(2)]
        return {"result": json.dumps(items), "total_cost_usd": 0.02}, "raw", None

    monkeypatch.setattr(propose, "call_claude", fake_call)
    real_insert = db.insert_scenario
    inserts = []

    def insert(*a, **k):
        inserts.append(1)
        if len(inserts) == 2:
            raise KeyboardInterrupt   # mid-way through the first domain's batch
        return real_insert(*a, **k)

    monkeypatch.setattr(db, "insert_scenario", insert)
    domains = [f"d{i}" for i in range(6)]
    with pytest.raises(KeyboardInterrupt):
        propose.main(["--study", str(study.root), "--domains", ",".join(domains), "--n", "2",
                      "--workers", "2", "--yes"])
    out = capsys.readouterr().out
    time.sleep(0.15)
    made = len(calls)
    assert 2 <= made < 6 and len(calls) == made   # nothing submitted after the interrupt
    con = study.connect()
    rows = con.execute("SELECT source, title FROM scenarios WHERE source LIKE 'proposer:%'").fetchall()
    assert len(rows) == 2 * made and len({r["title"] for r in rows}) == 2 * made   # every paid call, once
    assert "interrupted (KeyboardInterrupt)" in out and "pending domain(s) cancelled" in out
    assert f"{made} of 6 domains stored; re-run for the rest" in out


def test_drop_runs_cli_deletes_runs_and_vacuums(study, capsys):
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    ids = [mc.run_mc(con, "p000_manual", seed=s, n_draws=300, quiet=True) for s in (1, 2, 3)]
    con.close()
    assert drop_runs.parse_runs("9-11,13") == [9, 10, 11, 13] and drop_runs.parse_runs("3") == [3]
    with pytest.raises(argparse.ArgumentTypeError):
        drop_runs.parse_runs("5-3")
    argv = ["--study", str(study.root), "--runs", f"{ids[0]}-{ids[1]}"]
    with pytest.raises(SystemExit, match="--yes"):   # no TTY: nothing deleted
        drop_runs.main(argv)
    con = study.connect()
    assert [r[0] for r in con.execute("SELECT id FROM runs ORDER BY id")] == ids
    con.close()
    capsys.readouterr()
    drop_runs.main(argv + ["--yes"])
    out = capsys.readouterr().out
    assert f"run {ids[0]} (p000_manual): code_hash test-head, data_hash " in out
    assert f"run {ids[1]} (p000_manual)" in out and f"run {ids[2]}" not in out
    n_res, n_sens = 8 * (len(mc.METRIC_NAMES) + 1), 8 * len(db.PARAM_NAMES)
    assert (f"deleted 2 runs, {2 * n_res} results rows, {2 * n_sens} sensitivities rows; VACUUM done;"
            f" runs left: [{ids[2]}]") in out
    con = study.connect()
    assert [r[0] for r in con.execute("SELECT id FROM runs")] == [ids[2]]
    assert con.execute("SELECT COUNT(*) FROM results WHERE run_id IN (?,?)", ids[:2]).fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM sensitivities WHERE run_id IN (?,?)", ids[:2]).fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM results WHERE run_id=?", (ids[2],)).fetchone()[0] == n_res
    assert con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0] == 8   # never touched
    con.close()
    with pytest.raises(RuntimeError, match=f"no run {ids[0]}"):
        drop_runs.main(argv + ["--yes"])


# --- review fixes, round 4: retirement, dry-run tense, provenance, salvage spill ---

def test_renamed_seed_scenario_is_retired_from_the_plan(study, capsys):
    """The README's fix for a frozen scenario (change the title) must not
    leave the old row in every later 'all' / 'seed' plan: it is retired,
    kept with its elicitations, and only the new id is pending."""
    elicit.main(["--study", str(study.root), "--manual"])   # 8 seed rows, each elicited (frozen)
    scen = json.loads(study.scenarios_json.read_text())
    scen[7]["title"] = "Renamed eighth scenario"
    scen[7]["context"] = "New background."
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    out = capsys.readouterr().out
    assert "scenario 8 " in out and "would be retired" in out
    assert "claude_cli:haiku (k=2): 16 pending slots over 8 scenarios (ids 1..9)" in out
    con = study.connect()   # the dry run changed nothing on disk
    assert [r["id"] for r in db.get_scenarios(con, "all")] == list(range(1, 9))
    con.close()
    (study.protocols_dir / "p005.yaml").write_text(yaml.safe_dump({
        "name": "p005", "template_path": "templates/elicitor.md", "scenarios": "seed",
        "members": [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]}))
    elicit.main(["--study", str(study.root), "--protocol", "p005", "--dry-run"])
    assert "8 pending slots over 8 scenarios (ids 1..9)" in capsys.readouterr().out
    elicit.main(["--study", str(study.root), "--manual"])   # a real run retires the row
    out = capsys.readouterr().out
    assert "scenario 8 " in out and ": retired (title no longer in scenarios.json" in out
    assert "would load 1" not in out and "manual load: 1 scenarios valid" in out
    con = study.connect()
    pid = db.get_or_create_protocol(con, study.protocol_path("p001"), study.root)
    _, jobs = elicit.plan_jobs(con, study, pid, None, None, None)
    assert sorted({j["scenario_id"] for j in jobs}) == [1, 2, 3, 4, 5, 6, 7, 9]
    _, jobs = elicit.plan_jobs(con, study, pid, "seed", None, None)
    assert sorted({j["scenario_id"] for j in jobs}) == [1, 2, 3, 4, 5, 6, 7, 9]
    assert con.execute("SELECT source FROM scenarios WHERE id=8").fetchone()[0] == db.RETIRED_SOURCE
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE scenario_id=8").fetchone()[0] == 1


def test_dry_run_says_would_refresh(study, capsys):
    elicit.main(["--study", str(study.root), "--manual"])
    scen = json.loads(study.scenarios_json.read_text())
    scen.append({**{k: v for k, v in scen[0].items() if k != "manual"}, "title": "Unelicited ninth",
                 "context": "v1"})
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main(["--study", str(study.root), "--manual"])   # seeds the ninth row on disk (no manual key)
    capsys.readouterr()
    scen[8]["context"] = "v2"
    study.scenarios_json.write_text(json.dumps(scen))
    before = study.db.read_bytes()
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run", "--scenarios", "9"])
    out = capsys.readouterr().out
    assert "scenario 9 'Unelicited ninth': would refresh ['context', 'raw_json'] from scenarios.json" in out
    assert "': refreshed" not in out and "Context: v2" in out   # the planned prompt uses the file
    assert study.db.read_bytes() == before
    con = study.connect()
    assert db.get_scenarios(con, "9")[0]["context"] == "v1"
    con.close()
    elicit.main(["--study", str(study.root), "--manual"])
    out = capsys.readouterr().out
    assert "scenario 9 'Unelicited ninth': refreshed ['context', 'raw_json']" in out and "would" not in out
    con = study.connect()
    assert db.get_scenarios(con, "9")[0]["context"] == "v2"


def test_propose_without_a_proposer_template_exits_with_a_message(study, monkeypatch, capsys):
    monkeypatch.setattr(propose, "call_claude",
                        lambda *a: (_ for _ in ()).throw(AssertionError("provider called")))
    assert not (study.templates_dir / "proposer.md").exists()
    with pytest.raises(SystemExit, match=r"no proposer template at .*proposer\.md: this study does not"):
        propose.main(["--study", str(study.root), "--dry-run"])
    with pytest.raises(SystemExit, match="no proposer template"):
        propose.main(["--study", str(study.root), "--yes"])
    assert not list(study.root.glob("voi.db*"))


def test_propose_salvage_spills_a_domain_the_db_refuses(study, monkeypatch, capsys):
    """A DB error while inserting one finished domain during the salvage
    must not replace the original error or lose the other paid domains."""
    (study.templates_dir / "proposer.md").write_text("Domain: $domain, n=$n")

    def fake_call(prompt, model, system_prompt):
        # every call is in flight (paid) before d1 returns first and its insert fails
        time.sleep(0.1 if "d1" in prompt else 0.5)
        items = [{"title": f"T {prompt} {i}", "agent": "a", "decision": "d", "theta_definition": "t",
                  "instrument": "i"} for i in range(2)]
        return {"result": json.dumps(items), "total_cost_usd": 0.02}, "raw", None

    monkeypatch.setattr(propose, "call_claude", fake_call)
    real_insert = db.insert_scenario

    def insert(con, sc, source, **k):
        if source == "proposer:d1":
            raise sqlite3.OperationalError("database is locked")
        return real_insert(con, sc, source, **k)

    monkeypatch.setattr(db, "insert_scenario", insert)
    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        propose.main(["--study", str(study.root), "--domains", "d0,d1,d2", "--n", "2", "--workers", "3",
                      "--yes"])
    out = capsys.readouterr().out
    assert "interrupted (OperationalError)" in out
    assert "domain 'd1': could not be stored (OperationalError: database is locked); its 2 scenarios" \
        " were appended to" in out
    assert "domain 'd0': inserted 2" in out and "domain 'd2': inserted 2" in out
    assert "3 of 3 domains stored; re-run for the rest" in out
    con = study.connect()
    rows = con.execute("SELECT source FROM scenarios WHERE source LIKE 'proposer:%' ORDER BY id").fetchall()
    assert sorted(r[0] for r in rows) == ["proposer:d0"] * 2 + ["proposer:d2"] * 2
    spilled = [json.loads(line) for line in (study.root / propose.UNSTORED_FILE).read_text().splitlines()]
    assert len(spilled) == 1 and spilled[0]["domain"] == "d1" and spilled[0]["cost"] == pytest.approx(0.02)
    assert [sc["title"] for sc in spilled[0]["scenarios"]] == ["T Domain: d1, n=2 0", "T Domain: d1, n=2 1"]
    assert spilled[0]["store_error"] == "OperationalError: database is locked"


def test_mc_refuses_an_unknown_code_revision_unless_allowed(study, monkeypatch, capsys):
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    monkeypatch.setattr(db.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("git")))
    monkeypatch.setattr(db, "git_state", db.git_state.__wrapped__ if hasattr(db.git_state, "__wrapped__")
                        else _REAL_GIT_STATE)
    assert db.git_state() == ("unknown", [])
    with pytest.raises(RuntimeError, match="code revision could not be determined .*--allow-dirty"):
        mc.run_mc(con, "p000_manual", seed=1, n_draws=300, quiet=True)
    assert con.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    run_id = mc.run_mc(con, "p000_manual", seed=1, n_draws=300, quiet=True, allow_dirty=True)
    assert "WARNING: code revision unknown" in capsys.readouterr().out
    assert db.get_run(con, run_id)["code_hash"] == "unknown"


def test_mc_draws_from_the_fits_its_data_hash_describes(study, monkeypatch):
    """One complete_fits() read per run: the draws come from the dict the
    data_hash was computed over, so a valid elicitation committed by another
    process between two reads cannot slip into the draws unhashed."""
    elicit.main(["--study", str(study.root), "--manual"])
    con = study.connect()
    reads = []
    real = mc.complete_fits

    def counted(con_, pid):
        fits = real(con_, pid)
        reads.append(fits)
        return fits

    monkeypatch.setattr(mc, "complete_fits", counted)
    run_id = mc.run_mc(con, "p000_manual", seed=1, n_draws=300, quiet=True)
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
    launched a paid retry for each after the interrupt)."""
    envelope = json.dumps({"result": json.dumps({"parameters": _seed_payload()}), "total_cost_usd": 0.01})
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
    rows = con.execute("SELECT scenario_id, valid, raw_response, error FROM elicitations"
                       " ORDER BY id").fetchall()
    assert len(rows) == 2 and sorted(r["scenario_id"] for r in rows) == [1, 2]
    assert all(r["valid"] == 1 and r["error"] is None and r["raw_response"] == envelope for r in rows)
    assert "killed by signal" not in out and not (study.root / elicit.UNSTORED_FILE).exists()


def test_declined_plan_writes_nothing_and_keeps_the_template_editable(study, monkeypatch, capsys):
    """A declined (or non-TTY, no --yes) paid plan creates no voi.db and
    registers no protocol, so the study's template can still be edited;
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
    assert "plan: protocol p001, 24 pending slots" in out and calls == []
    assert not list(study.root.glob("voi.db*"))   # not even the DB
    template = study.templates_dir / "elicitor.md"
    template.write_text(template.read_text() + "One more line.\n")   # still editable: no hash frozen
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--dry-run"])
    assert "24 slots would be elicited" in capsys.readouterr().out
    assert not list(study.root.glob("voi.db*"))
    # an existing DB is left byte-identical and without the protocol
    elicit.main(["--study", str(study.root), "--manual"])
    before = study.db.read_bytes()
    capsys.readouterr()
    with pytest.raises(SystemExit, match="--yes"):
        elicit.main(["--study", str(study.root), "--protocol", "p001"])
    assert "plan: protocol p001, 24 pending slots" in capsys.readouterr().out
    assert study.db.read_bytes() == before
    con = study.connect()
    assert [r[0] for r in con.execute("SELECT name FROM protocols")] == ["p000_manual"]
    con.close()
    # a failed preflight after the confirmation writes nothing either
    monkeypatch.setattr(elicit.claude_cli, "check_auth",
                        lambda: (_ for _ in ()).throw(RuntimeError("claude CLI is not logged in")))
    with pytest.raises(RuntimeError, match="not logged in"):
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes"])
    assert study.db.read_bytes() == before and calls == []
    # the confirmed run seeds, registers the (edited) template and submits
    monkeypatch.setattr(elicit.claude_cli, "check_auth", lambda: "claude CLI preflight: test")
    monkeypatch.setattr(elicit, "get_provider", fake_provider_factory(
        {"claude_cli": {"parameters": _seed_payload()}}))
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes", "--members",
                 "claude_cli:haiku", "--k", "1", "--scenarios", "1"])
    out = capsys.readouterr().out
    assert "claude CLI preflight: test" in out and "done: 1/1 slots valid" in out
    con = study.connect()
    prot = db.protocol_by_name(con, "p001")
    assert prot["template_hash"] == db.sha256(template.read_text())
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1 AND provider='claude_cli'"
                       ).fetchone()[0] == 1


def test_rejected_request_is_one_slot_until_a_second_scenario(study, monkeypatch, capsys):
    """HTTP 403 (a moderation flag on one prompt) or 400 is a per-request
    outcome: the slot is stored invalid without a retry (unbilled) and the
    member's other slots run. The member is halted when it is rejected on a
    second distinct scenario, or at once when the response names the key."""
    seed = _seed_payload()
    flagged = '{"error":{"code":403,"message":"Your input was flagged","metadata":{"reasons":["cbrn"]}}}'
    reject = {2}
    calls = []

    def get_provider(name):
        def call(prompt, model, system_prompt):
            sid = next(sc["id"] for sc in scenarios if sc["title"] in prompt)
            calls.append((name, sid))
            time.sleep(0.02)
            if name == "openrouter" and sid in reject:
                return None, flagged, f"http: status 403: {flagged}"
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--manual"])
    scenarios = [dict(r) for r in study.connect().execute("SELECT id, title FROM scenarios")]
    base = ["--study", str(study.root), "--protocol", "p001", "--members", "openrouter:fake/model",
            "--k", "1", "--yes", "--workers", "1"]
    elicit.main(base + ["--scenarios", "1,2,3,4"])
    out = capsys.readouterr().out
    assert [sid for name, sid in calls] == [1, 2, 3, 4]   # one call per slot, no retry, no halt
    assert ("scenario 2 openrouter:fake/model: the request was rejected (http 400/403: invalid params,"
            " guardrail or moderation flag on this prompt, or permissions); stored invalid, not retried,"
            " not billed; the slot is pending on the next run") in out
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
    assert "member openrouter:fake/model: http: status 403: " in out
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
    seed = _seed_payload()
    hang = {1, 2, 3, 4}
    calls = []

    def get_provider(name):
        def call(prompt, model, system_prompt):
            sid = next(sc["id"] for sc in scenarios if sc["title"] in prompt)
            calls.append(sid)
            time.sleep(0.02)
            if sid in hang:
                return None, "", "cli: timeout after 1s"
            text = json.dumps({"parameters": seed})
            return {"result": text, "total_cost_usd": 0.01}, text, None
        return call

    monkeypatch.setattr(elicit, "get_provider", get_provider)
    elicit.main(["--study", str(study.root), "--manual"])
    scenarios = [dict(r) for r in study.connect().execute("SELECT id, title FROM scenarios")]
    base = ["--study", str(study.root), "--protocol", "p001", "--members", "claude_cli:haiku",
            "--k", "1", "--yes", "--workers", "1"]
    elicit.main(base + ["--scenarios", "1,2,3,4"])
    out = capsys.readouterr().out
    # no retry of a timeout; halted on the second in a row (the single worker
    # may have started the third slot before the main thread saw the second)
    assert calls[:2] == [1, 2] and len(calls) <= 3
    assert re.search(r"member claude_cli:haiku: cli: timeout after 1s: 2 consecutive timeouts \(the CLI"
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
        elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes", "--members",
                     "claude_cli:haiku"])
    assert calls == [] and not list(study.root.glob("voi.db*"))
    assert "eliciting" not in capsys.readouterr().out
    # a claude_cli-free selection never runs the CLI preflight
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    monkeypatch.setattr(urllib.request, "urlopen", _key_ok)
    monkeypatch.setattr(elicit, "get_provider", fake_provider_factory(
        {"openrouter": {"parameters": _seed_payload()}}))
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--yes", "--members",
                 "openrouter:fake/model", "--scenarios", "1"])
    assert "done: 1/1 slots valid" in capsys.readouterr().out


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
