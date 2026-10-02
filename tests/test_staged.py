"""The two-stage protocol (DESIGN section 4) on a synthetic study with a fake
provider: registration and immutability (stages, template variables and the
files they inline), group_key 'self' against a grouped decision stage, the
dry run listing both stages, elicitation and resume per stage, the assembly
of a scenario's fits from its group's decision rows and its own instrument
rows, MC and replay, the planning checks and the refusal of the archived
protocol forms. No CLI, no network."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest
import yaml

from voi_rank import db, elicit, mc
from voi_rank.fit import DECISION_PARAMS, INSTRUMENT_PARAMS
from voi_rank.study import Study

SEED = {
    "p": (0.02, 0.08, 0.25), "s": (0.60, 0.80, 0.95), "t": (0.70, 0.90, 0.98),
    "B": (20e3, 150e3, 1.5e6), "K": (2e3, 10e3, 60e3), "C_build": (5e3, 20e3, 100e3),
    "C_run": (300.0, 1000.0, 5000.0),
}
HAIKU, SONNET = "claude_cli:haiku", "claude_cli:sonnet"
ARCHIVE_SIM2REAL = Path(__file__).resolve().parent.parent / "archive" / "pilots" / "sim2real"
HOME, AV = "home manipulator", "AV AEB"
MEMBERS = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 2},
           {"provider": "claude_cli", "model": "sonnet", "k_repeats": 2}]
DECISION_TEMPLATE = ("DECISION-level elicitation, $perspective perspective.\nAgent: $agent\n"
                     "Decision: $decision\nState: $theta_definition\n\nFacts:\n$decision_context\n\n"
                     "$anchors_decision\n")
INSTRUMENT_TEMPLATE = ("INSTRUMENT-level elicitation (context mode $context_mode).\nTitle: $title\n"
                       "Agent: $agent\nDecision: $decision\nState: $theta_definition\n"
                       "Instrument: $instrument\n\nFacts:\n$context\n\n$anchors_instrument\n")


class StagedFake:
    """Answers the parameters a stage's prompt asks for (the decision prompt
    names DECISION-level, the instrument prompt INSTRUMENT-level), jittered
    per (prompt, model, call), deterministic across reruns. One instance
    serves every call, so repeats of a slot differ."""

    def __init__(self, cost: float = 0.01):
        self.counts: dict[str, int] = {}
        self.cost = cost

    def __call__(self, prompt, model, system_prompt):
        n = self.counts[prompt] = self.counts.get(prompt, 0) + 1
        rng = np.random.default_rng([int(db.sha256(prompt + model)[:8], 16), n])
        names = DECISION_PARAMS if "DECISION-level" in prompt else INSTRUMENT_PARAMS
        prm = {}
        for name in names:
            f = float(np.exp(rng.normal(0.0, 0.3 if name in ("B", "K", "C_build", "C_run") else 0.08)))
            q = [v * f for v in SEED[name]]
            if name in ("p", "s", "t"):
                q = [float(np.clip(v, 0.005, 0.995)) for v in q]
                if not q[0] < q[1] < q[2]:
                    q = list(SEED[name])
            prm[name] = {"reasoning": f"{name} for {model}", "p5": q[0], "p50": q[1], "p95": q[2]}
        text = json.dumps({"parameters": prm})
        raw = json.dumps({"result": text, "total_cost_usd": self.cost})
        return {"result": text, "total_cost_usd": self.cost}, raw, None


def scenarios(n_home: int = 3, n_av: int = 2) -> list[dict]:
    """A ladder of n_home rungs sharing one decision (group 'home manipulator')
    and n_av rungs of another; decision_context is shared within a group."""
    out = []
    for group, n, agent in ((HOME, n_home, "Robotics product lead"), (AV, n_av, "AV programme manager")):
        for i in range(n):
            out.append({"title": f"{group} rung {i}", "agent": agent, "decision": f"Delay or launch: {group}",
                        "theta_definition": f"theta=1: the {group} system has the hazardous property",
                        "instrument": f"Evaluation at level {i} for {group}",
                        "decision_context": f"Decision facts for {group}.",
                        "instrument_context": f"Instrument facts for {group} rung {i}.",
                        "group": "physical AI", "attributes": {"context_group": group, "level": i}})
    return out


def protocol(name: str, group_key: str, **extra) -> dict:
    return {"name": name, "notes": "test",
            "stages": [{"name": "decision", "template_path": "templates/decision.md",
                        "params": DECISION_PARAMS, "group_key": group_key},
                       {"name": "instrument", "template_path": "templates/instrument.md",
                        "params": INSTRUMENT_PARAMS}],
            "template_vars": {"perspective": "society", "context_mode": "curated",
                              "anchors_decision": "@file:templates/anchors_decision.md",
                              "anchors_instrument": "@file:templates/anchors_instrument.md"},
            "members": MEMBERS, **extra}


def build(tmp_path: Path, scen: list[dict] | None = None) -> Study:
    root = tmp_path / "study"
    root.mkdir(parents=True, exist_ok=True)
    (root / "scenarios.json").write_text(json.dumps(scen if scen is not None else scenarios()))
    (root / "protocols").mkdir()
    (root / "templates").mkdir()
    (root / "templates" / "decision.md").write_text(DECISION_TEMPLATE)
    (root / "templates" / "instrument.md").write_text(INSTRUMENT_TEMPLATE)
    (root / "templates" / "anchors_decision.md").write_text("Anchor A1 (decision half).\n")
    (root / "templates" / "anchors_instrument.md").write_text("Anchor A1 (instrument half).\n")
    (root / "protocols" / "pG.yaml").write_text(yaml.safe_dump(protocol("pG", "attributes.context_group")))
    (root / "protocols" / "pS.yaml").write_text(yaml.safe_dump(protocol("pS", "self")))
    return Study.resolve(root)


def cfg_of(study, name) -> dict:
    return yaml.safe_load(study.protocol_path(name).read_text())


def write_cfg(study, cfg: dict) -> Path:
    path = study.protocol_path(cfg["name"])
    path.write_text(yaml.safe_dump(cfg))
    return path


# --- registration -----------------------------------------------------------------

def test_protocol_registers_stages_and_template_vars_and_is_immutable(tmp_path):
    study = build(tmp_path)
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    pid = db.get_or_create_protocol(con, study.protocol_path("pG"), study.root)
    prot = db.protocol_by_name(con, "pG")
    stages = db.protocol_stages(prot)
    assert [s["name"] for s in stages] == ["decision", "instrument"]
    dec, ins = stages
    assert dec["params"] == DECISION_PARAMS and ins["params"] == INSTRUMENT_PARAMS
    assert dec["group_key"] == "attributes.context_group" and "group_key" not in ins
    assert "decision_contexts" not in dec
    assert dec["template_hash"] == db.sha256(DECISION_TEMPLATE)
    assert ins["template_hash"] == db.sha256(INSTRUMENT_TEMPLATE)
    assert prot["template_path"] == "templates/decision.md + templates/instrument.md"
    tv = db.protocol_template_vars(prot)
    assert tv == {"perspective": "society", "context_mode": "curated",
                  "anchors_decision": "Anchor A1 (decision half).\n",
                  "anchors_instrument": "Anchor A1 (instrument half).\n"}   # files inlined
    assert prot["template_hash"] == db.sha256(db.stages_json(stages) + "\n" + db.template_vars_json(tv))
    assert prot["model_kind"] == "binary"
    assert db.group_stage(stages) == dec and db.scenario_stage(stages) == ins
    assert db.stage_of_param(stages, "B") == dec and db.stage_of_param(stages, "C_run") == ins
    assert db.stage_of_param(stages, "n") is None   # the retired reuse count belongs to no stage
    assert db.stage_of_param(None, "p") is None
    # the same file again: the same id
    assert db.get_or_create_protocol(con, study.protocol_path("pG"), study.root) == pid
    # a changed template variable, inlined file, template or stage config is refused
    cfg = cfg_of(study, "pG")
    cfg["template_vars"]["perspective"] = "developer"
    write_cfg(study, cfg)
    with pytest.raises(RuntimeError, match=r"different \['template_hash', 'template_vars'\]"):
        db.get_or_create_protocol(con, study.protocol_path("pG"), study.root)
    write_cfg(study, protocol("pG", "attributes.context_group"))
    assert db.get_or_create_protocol(con, study.protocol_path("pG"), study.root) == pid
    anchors = study.root / "templates/anchors_decision.md"
    anchors.write_text(anchors.read_text() + "\nOne more sourced number.\n")
    with pytest.raises(RuntimeError, match="template_vars"):
        db.get_or_create_protocol(con, study.protocol_path("pG"), study.root)
    anchors.write_text("Anchor A1 (decision half).\n")
    (study.root / "templates/decision.md").write_text(DECISION_TEMPLATE + "\nOne more line.\n")
    with pytest.raises(RuntimeError, match=r"different \['template_hash', 'stages'\]"):
        db.get_or_create_protocol(con, study.protocol_path("pG"), study.root)
    con.close()


@pytest.mark.parametrize("edit, match", [
    (lambda c: c.update(model="gaussian"), "not supported: only the binary model remains"),
    (lambda c: c.update(template_path="templates/elicitor.md"), "not a template_path"),
    (lambda c: c.pop("stages"), "a protocol lists two stages"),
    (lambda c: c["stages"].pop(), "exactly two stages"),
    (lambda c: c["stages"][1].update(params=["s", "t", "C_build"]), "partition"),
    (lambda c: c["stages"][1].update(params=[*INSTRUMENT_PARAMS, "n"]), "subset of"),
    (lambda c: c["stages"][1].update(params=[*INSTRUMENT_PARAMS, "C"]), "subset of"),
    (lambda c: c["stages"][1].update(group_key="attributes.level"), "exactly one stage"),
    (lambda c: c["stages"][0].update(group_key="attrs.x"), "group_key must be"),
    (lambda c: c["stages"][0].update(name="instrument"), "names must differ"),
    (lambda c: c["stages"][0].update(decision_contexts={HOME: "text"}), "decision_contexts are gone"),
    (lambda c: c.update(template_vars="society"), "template_vars must map"),
    (lambda c: c["template_vars"].update({"two words": "x"}), r"not a valid \$variable name"),
    (lambda c: c["template_vars"].update({"title": "x"}), "is a scenario field"),
    (lambda c: c["template_vars"].update({"anchors_decision": "@file:templates/missing.md"}), "not a file"),
])
def test_bad_protocol_configs_are_refused(tmp_path, edit, match):
    study = build(tmp_path)
    cfg = cfg_of(study, "pS")
    edit(cfg)
    write_cfg(study, cfg)
    con = study.connect()
    with pytest.raises(RuntimeError, match=match):
        db.get_or_create_protocol(con, study.protocol_path("pS"), study.root)
    con.close()


# --- end to end ------------------------------------------------------------------------

def test_self_grouping_elicits_every_scenario_as_its_own_decision(tmp_path, monkeypatch, capsys):
    study = build(tmp_path)
    fake = StagedFake()
    monkeypatch.setattr(elicit, "get_provider", lambda name: fake)
    elicit.main(["--study", str(study.root), "--protocol", "pS", "--dry-run"])
    out = capsys.readouterr().out
    assert "stage decision (template templates/decision.md, params p, B, K, group_key self):" in out
    assert f"member {HAIKU} (k=2): 10 pending slots over 5 groups (1, 2, 3, 4, 5)" in out
    assert f"member {SONNET} (k=2): 10 pending slots over 5 scenarios (ids 1..5)" in out
    assert "first pending prompt of stage decision (group '1', representative scenario 1," in out
    dec, ins = out.split("first pending prompt of stage decision")[1].split(
        "first pending prompt of stage instrument")
    assert "Decision facts for home manipulator." in dec and "Anchor A1 (decision half)." in dec
    assert "society perspective" in dec and "rung" not in dec and "Evaluation at level" not in dec
    assert "Instrument facts for home manipulator rung 0." in ins and "Anchor A1 (instrument half)." in ins
    assert "context mode curated" in ins and "Decision facts" not in ins
    assert "40 slots would be elicited; no provider was called." in out
    assert not list(study.root.glob("voi.db*"))
    elicit.main(["--study", str(study.root), "--protocol", "pS", "--k", "1", "--members", HAIKU, "--yes"])
    assert "done: 10/10 slots valid" in capsys.readouterr().out
    con = study.connect()
    pid = db.protocol_by_name(con, "pS")["id"]
    rows = con.execute("SELECT scenario_id, stage FROM elicitations WHERE protocol_id=? AND valid=1"
                       " ORDER BY id", (pid,)).fetchall()
    assert sorted((r["scenario_id"], r["stage"]) for r in rows) == \
        sorted((sid, st) for sid in range(1, 6) for st in ("decision", "instrument"))
    fits = mc.complete_fits(con, pid)
    assert sorted(fits) == [1, 2, 3, 4, 5]
    # every scenario's decision fits are its own (one elicitation each), unlike a grouped protocol
    dec_ids = [{f["elicitation_id"] for f in fits[s]["p"]} for s in fits]
    assert all(len(ids) == 1 for ids in dec_ids) and len(set.union(*dec_ids)) == 5
    assert db.scenario_group_ids(con, "self", 3) == [3]
    assert db.elicited_source_ids(con, pid, 3, "B") == [3] and db.elicited_source_ids(con, pid, 3, "s") == [3]
    assert db.elicited_p50s(con, pid, 2, "p") != db.elicited_p50s(con, pid, 1, "p")
    run_id = mc.run_mc(con, "pS", seed=3, n_draws=2000, quiet=True)
    ids, eff = mc.replay_efficiency(con, run_id)
    assert ids == [1, 2, 3, 4, 5] and eff.shape == (5, 2000)
    con.close()


def test_grouped_decision_stage_end_to_end(tmp_path, monkeypatch, capsys):
    study = build(tmp_path)
    scen = json.loads(study.scenarios_json.read_text())
    fake = StagedFake()
    monkeypatch.setattr(elicit, "get_provider", lambda name: fake)
    # the dry run lists both stages and renders a prompt of each
    elicit.main(["--study", str(study.root), "--protocol", "pG", "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY RUN: protocol pG (stages decision + instrument, hash" in out
    assert ("stage decision (template templates/decision.md, params p, B, K,"
            " group_key attributes.context_group):") in out
    assert f"member {HAIKU} (k=2): 4 pending slots over 2 groups ({AV}, {HOME})" in out
    assert "stage instrument (template templates/instrument.md, params s, t, C_build, C_run):" in out
    assert f"member {SONNET} (k=2): 10 pending slots over 5 scenarios (ids 1..5)" in out
    assert f"first pending prompt of stage decision (group '{HOME}', representative scenario 1," in out
    assert "first pending prompt of stage instrument (scenario 1," in out
    assert f"{2 * (4 + 10)} slots would be elicited; no provider was called." in out
    dec_prompt, ins_prompt = out.split("first pending prompt of stage decision")[1].split(
        "first pending prompt of stage instrument")
    assert scen[0]["agent"] in dec_prompt and scen[0]["decision_context"] in dec_prompt
    assert scen[0]["instrument"] not in dec_prompt and scen[0]["instrument_context"] not in dec_prompt
    assert scen[0]["instrument"] in ins_prompt and scen[0]["instrument_context"] in ins_prompt
    assert scen[0]["decision_context"] not in ins_prompt and "$decision_context" not in ins_prompt
    assert not list(study.root.glob("voi.db*"))
    # the plan prints the per-stage breakdown (declined without --yes)
    with pytest.raises(SystemExit, match="--yes"):
        elicit.main(["--study", str(study.root), "--protocol", "pG", "--k", "1"])
    out = capsys.readouterr().out
    assert f"{HAIKU}: 7 slots (decision 2, instrument 5), estimated cost" in out
    # the decision stage alone, k = 1
    elicit.main(["--study", str(study.root), "--protocol", "pG", "--stage", "decision", "--k", "1", "--yes"])
    out = capsys.readouterr().out
    assert "done: 4/4 slots valid" in out
    assert f"scenario 1 stage decision (group '{HOME}') {HAIKU} repeat 0: ok" in out
    con = study.connect()
    prot = db.protocol_by_name(con, "pG")
    pid = prot["id"]
    rows = con.execute("SELECT * FROM elicitations WHERE protocol_id=? ORDER BY id", (pid,)).fetchall()
    assert len(rows) == 4 and all(r["stage"] == "decision" and r["valid"] for r in rows)
    assert {r["scenario_id"] for r in rows} == {1, 4}   # the groups' representatives (lowest ids)
    names = {r[0] for r in con.execute(
        "SELECT DISTINCT p.name FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=?", (pid,))}
    assert names == {"p", "B", "K"}
    # resume per stage: the decision stage is done, the instrument stage pending
    elicit.main(["--study", str(study.root), "--protocol", "pG", "--stage", "decision", "--k", "1", "--yes"])
    assert "nothing to do" in capsys.readouterr().out
    _, jobs = elicit.plan_jobs(con, study, pid, None, 1, None)
    assert len(jobs) == 10 and {j["stage"] for j in jobs} == {"instrument"}
    assert all(j["names"] == INSTRUMENT_PARAMS and "group" not in j for j in jobs)
    with pytest.raises(SystemExit, match="--stage 'nope': protocol pG has stages"):
        elicit.plan_jobs(con, study, pid, None, 1, None, stage="nope")
    # incomplete until the instrument stage is in
    assert mc.complete_fits(con, pid) == {}
    elicit.main(["--study", str(study.root), "--protocol", "pG", "--k", "1", "--yes"])
    assert "done: 10/10 slots valid" in capsys.readouterr().out
    # a decision row and an instrument row of one member and repeat share a scenario; a
    # duplicate valid slot within a stage is refused
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE protocol_id=? AND scenario_id=1"
                       " AND provider='claude_cli' AND model='haiku' AND repeat_ix=0 AND valid=1",
                       (pid,)).fetchone()[0] == 2
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_elicitation(con, 1, pid, "claude_cli", "haiku", 0, "h", "{}", True, None, "decision")
    con.rollback()
    # assembly: p, B, K of every scenario of a group are the group's decision fits (same
    # elicitation ids); s, t, C_build, C_run its own instrument fits
    fits = mc.complete_fits(con, pid)
    assert sorted(fits) == [1, 2, 3, 4, 5]
    home = [1, 2, 3]
    dec_ids = {f["elicitation_id"] for f in fits[1]["p"]}
    assert len(dec_ids) == 2 and all({f["elicitation_id"] for f in fits[s]["B"]} == dec_ids for s in home)
    assert {f["elicitation_id"] for f in fits[4]["K"]}.isdisjoint(dec_ids)
    assert all(len(fits[s]["C_run"]) == 2 for s in fits)
    assert fits[1]["p"] == fits[3]["p"] and fits[1]["C_run"] != fits[3]["C_run"]
    assert db.elicited_p50s(con, pid, 3, "p") == db.elicited_p50s(con, pid, 1, "p")
    assert db.elicited_p50s(con, pid, 3, "s") != db.elicited_p50s(con, pid, 1, "s")
    assert db.elicited_p50s(con, pid, 5, "B", "claude_cli", "sonnet") == \
        [f["p50"] for f in fits[5]["B"] if f["model"] == "sonnet"]
    assert db.scenario_group_ids(con, "attributes.context_group", 2) == home
    assert db.scenario_groups_by_key(con, "attributes.context_group") == {AV: [4, 5], HOME: home}
    # a group without a complete decision stage leaves its scenarios incomplete
    con.execute("UPDATE elicitations SET valid=0 WHERE protocol_id=? AND stage='decision' AND scenario_id=4",
                (pid,))
    assert sorted(mc.complete_fits(con, pid)) == home
    con.rollback()
    # MC, data hash (each shared decision fit counted once), replay
    run_id = mc.run_mc(con, "pG", seed=3, n_draws=2000, quiet=True)
    run = db.get_run(con, run_id)
    assert con.execute("SELECT COUNT(DISTINCT scenario_id) FROM results WHERE run_id=?",
                       (run_id,)).fetchone()[0] == 5
    assert run["data_hash"] == mc.data_hash(fits)
    rows_hashed = {(f["elicitation_id"], n, f["fit_params"])
                   for s in fits for n, lst in fits[s].items() for f in lst}
    assert len(rows_hashed) == 4 * 3 + 10 * 4   # 4 decision rows x 3 params, 10 instrument rows x 4
    ids, eff = mc.replay_efficiency(con, run_id)
    assert ids == [1, 2, 3, 4, 5] and eff.shape == (5, 2000)
    # a member subset pools that member's decision and instrument rows
    sub = mc.run_mc(con, "pG", seed=3, n_draws=2000, quiet=True, members=[SONNET])
    fits_sub = mc.complete_fits(con, pid, [SONNET])
    assert sorted(fits_sub) == [1, 2, 3, 4, 5]
    assert all({f["model"] for f in fits_sub[s][n]} == {"sonnet"} for s in fits_sub for n in db.PARAM_NAMES)
    assert db.get_run(con, sub)["data_hash"] == mc.data_hash(fits_sub) != run["data_hash"]
    mc.replay_efficiency(con, sub)
    con.close()


def _edited(tmp_path, edit_scenarios=None, edit_template=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    scen = scenarios()
    if edit_scenarios:
        edit_scenarios(scen)
    study = build(tmp_path, scen)
    if edit_template:
        path = study.root / "templates/decision.md"
        path.write_text(edit_template(path.read_text()))
    return study


def test_planning_checks_groups_and_the_templates(tmp_path, monkeypatch):
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake())
    dry = ["--protocol", "pG", "--dry-run"]

    def drop_group(scen):
        del scen[3]["attributes"]["context_group"]
    study = _edited(tmp_path / "a", edit_scenarios=drop_group)
    with pytest.raises(SystemExit, match=r"scenarios \[4\] carry no attributes.context_group value"):
        elicit.main(["--study", str(study.root), *dry])

    def other_decision(scen):
        scen[2]["decision"] = "A different decision"
    study = _edited(tmp_path / "b", edit_scenarios=other_decision)
    mixed = f"group '{HOME}' .*mixes 2 different agent / decision / theta / decision_context"
    with pytest.raises(SystemExit, match=mixed):
        elicit.main(["--study", str(study.root), *dry])

    def other_context(scen):   # a group shares its decision_context too
        scen[1]["decision_context"] = "Other facts."
    study = _edited(tmp_path / "c", edit_scenarios=other_context)
    with pytest.raises(SystemExit, match=f"group '{HOME}' .*mixes 2 different"):
        elicit.main(["--study", str(study.root), *dry])
    # under group_key self a differing decision_context is just another decision
    elicit.main(["--study", str(study.root), "--protocol", "pS", "--dry-run"])

    study = _edited(tmp_path / "d", edit_template=lambda t: t + "\nInstrument: $instrument\n")
    with pytest.raises(SystemExit, match=r"decision template uses \$instrument: it renders only"):
        elicit.main(["--study", str(study.root), *dry])
    study = _edited(tmp_path / "e", edit_template=lambda t: t + "\nFacts: $context\n")
    with pytest.raises(SystemExit, match=r"uses \$context"):
        elicit.main(["--study", str(study.root), *dry])
    study = _edited(tmp_path / "f", edit_template=lambda t: t + "\nTitle: $title\n")
    with pytest.raises(SystemExit, match=r"uses \$title"):
        elicit.main(["--study", str(study.root), *dry])
    # a shared template variable renders in either template; an undefined one is refused
    study = _edited(tmp_path / "g", edit_template=lambda t: t + "\nContext mode: $context_mode\n")
    elicit.main(["--study", str(study.root), *dry])
    study = _edited(tmp_path / "h", edit_template=lambda t: t + "\n$undefined_var\n")
    with pytest.raises(SystemExit, match=r"decision template uses \$undefined_var: it renders only"):
        elicit.main(["--study", str(study.root), *dry])
    # the instrument template may use every scenario field and template variable, and nothing else
    study = _edited(tmp_path / "i")
    path = study.root / "templates/instrument.md"
    path.write_text(path.read_text() + "\nDecision context: $decision_context\n")
    with pytest.raises(SystemExit, match=r"instrument template uses \$decision_context: it renders only"
                                          r" \$title, \$agent"):
        elicit.main(["--study", str(study.root), *dry])
    assert not list(study.root.glob("voi.db*"))


def test_planner_uses_the_db_group_not_the_selection(tmp_path, monkeypatch, capsys):
    """Decision rows are stored on the group's lowest id in the DB and a
    repeat they fill is done for every selection: a partial --scenarios never
    elicits a second set and a retired representative keeps carrying the
    group's rows."""
    study = build(tmp_path)
    fake = StagedFake()
    monkeypatch.setattr(elicit, "get_provider", lambda name: fake)
    base = ["--study", str(study.root), "--protocol", "pG", "--members", HAIKU, "--k", "2", "--yes"]
    elicit.main([*base, "--stage", "decision", "--scenarios", "5"])
    assert "done: 2/2 slots valid" in capsys.readouterr().out
    con = study.connect()
    pid = db.protocol_by_name(con, "pG")["id"]

    def stored():
        return [r[0] for r in con.execute(
            "SELECT scenario_id FROM elicitations WHERE protocol_id=? AND stage='decision' AND valid=1"
            " ORDER BY id", (pid,))]
    assert stored() == [4, 4]   # the group's lowest id, not the selected 5
    _, jobs = elicit.plan_jobs(con, study, pid, "5", 2, {HAIKU}, stage="decision")
    assert jobs == []
    con.close()
    elicit.main([*base, "--stage", "decision"])
    assert "done: 2/2 slots valid" in capsys.readouterr().out
    con = study.connect()
    assert stored() == [4, 4, 1, 1]
    con.close()
    # the representative leaves scenarios.json (its title changes): the retired row 1 keeps
    # carrying the home group's rows and the decision stage plans nothing
    scen = json.loads(study.scenarios_json.read_text())
    scen[0]["title"] += " (renamed)"
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main([*base, "--dry-run"])
    out = capsys.readouterr().out
    assert "scenario 1 " in out and "would be retired" in out
    assert f"member {HAIKU} (k=2): 0 pending slots over 0 groups" in out
    assert f"member {HAIKU} (k=2): 10 pending slots over 5 scenarios (ids 2..6)" in out
    elicit.main(base)
    assert "done: 10/10 slots valid" in capsys.readouterr().out
    con = study.connect()
    assert stored() == [4, 4, 1, 1]
    fits = mc.complete_fits(con, pid)
    assert sorted(fits) == [2, 3, 4, 5, 6]
    assert len(fits[6]["p"]) == 2 and fits[6]["p"] == fits[2]["p"] and fits[6]["s"] != fits[2]["s"]
    con.close()


def test_plan_refuses_a_decision_text_changed_after_the_decision_stage(tmp_path, monkeypatch, capsys):
    """Between the stages a non-representative scenario holds no rows, so the
    seed refresh accepts a new decision text for it. Every plan, --stage
    instrument included, then refuses the group: a mixed text over the
    group's active scenarios, or (the whole group renamed and changed)
    stored decision rows rendered from another text."""
    study = build(tmp_path)
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake())
    base = ["--study", str(study.root), "--protocol", "pG", "--members", HAIKU, "--k", "1", "--yes"]
    elicit.main([*base, "--stage", "decision"])
    assert "done: 2/2 slots valid" in capsys.readouterr().out
    original = study.scenarios_json.read_text()
    scen = json.loads(original)
    other = "A completely different decision: whether to buy a coffee machine"
    scen[1]["decision"] = other
    study.scenarios_json.write_text(json.dumps(scen))
    for extra_args in (["--stage", "instrument"], ["--stage", "decision"], [],
                       ["--stage", "instrument", "--scenarios", "2"]):
        mixed = (f"stage decision: group '{HOME}' \\(scenarios \\[1, 2, 3\\]\\) mixes 2 different agent"
                 " / decision / theta / decision_context")
        with pytest.raises(SystemExit, match=mixed):
            elicit.main([*base, *extra_args, "--dry-run"])
    # the whole group changes its decision under new titles: the retired representative's
    # rows are another decision's, and it stays in the one-decision check because it holds
    # them, so the plan refuses instead of eliciting beside them
    for sc in scen[:3]:
        sc["title"] += " v2"
        sc["decision"] = other
    study.scenarios_json.write_text(json.dumps(scen))
    refusal = (r"\(scenarios \[1, 6, 7, 8\]\) mixes 2 different agent / decision / theta / decision_context"
               r" texts: not one decision \(scenarios \[1\] are retired rows holding valid elicitations"
               r" under pG; give the changed scenarios a new attributes.context_group value, or start a new"
               r" voi.db\)")
    for extra_args in (["--stage", "decision"], ["--stage", "instrument"]):
        with pytest.raises(SystemExit, match=refusal):
            elicit.main([*base, *extra_args, "--dry-run"])
    # the stored rows' prompt hash is checked as well: decision rows rendered from another
    # text than the group renders now are refused with the same remedy
    study.scenarios_json.write_text(original)
    con = study.connect()
    con.execute("UPDATE elicitations SET prompt_hash=? WHERE stage='decision'", ("0" * 64,))
    con.commit()
    con.close()
    for extra_args in (["--stage", "decision"], ["--stage", "instrument"]):
        stale = (r"holds 1 valid decision row\(s\) elicited for a different agent / decision / theta /"
                 r" decision_context text \(prompt hash 0{12} vs \w{12} now\).*new attributes.context_group"
                 r" value, or start")
        with pytest.raises(SystemExit, match=stale):
            elicit.main([*base, *extra_args, "--dry-run"])
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0] == 2   # nothing written
    assert con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0] == 5
    con.close()
    # under group_key self the remedy names the scenario's title
    elicit.main(["--study", str(study.root), "--protocol", "pS", "--members", HAIKU, "--k", "1", "--yes",
                 "--stage", "decision", "--scenarios", "1"])
    con = study.connect()
    pid = db.protocol_by_name(con, "pS")["id"]
    con.execute("UPDATE elicitations SET prompt_hash=? WHERE protocol_id=?", ("1" * 64, pid))
    con.commit()
    con.close()
    with pytest.raises(SystemExit, match=r"Change the scenario's title \(a new scenario\), or start a new"):
        elicit.main(["--study", str(study.root), "--protocol", "pS", "--dry-run"])


def test_plan_refuses_a_decision_text_changed_after_the_instrument_stage(tmp_path, monkeypatch, capsys):
    """The mirror of the test above: the instrument stage first, then the
    whole home group renamed under a new decision text. No decision rows
    exist, so the prompt-hash check cannot fire; the retired rungs hold
    valid instrument rows elicited for the old decision and stay in the
    one-decision check (elicited_scenario_rows: a valid row at any stage),
    so every plan, the decision stage first of all, refuses instead of
    storing the new decision's p, B, K on the retired representative and
    pooling the retired rungs' instrument rows with them."""
    study = build(tmp_path)
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake())
    base = ["--study", str(study.root), "--protocol", "pG", "--members", HAIKU, "--k", "1", "--yes"]
    elicit.main([*base, "--stage", "instrument"])
    assert "done: 5/5 slots valid" in capsys.readouterr().out
    original = json.loads(study.scenarios_json.read_text())
    scen = json.loads(study.scenarios_json.read_text())
    for sc in scen[:3]:
        sc["title"] += " v2"
        sc["decision"] = "A new decision: whether to ship a coffee machine"
    study.scenarios_json.write_text(json.dumps(scen))
    refusal = (f"stage decision: group '{HOME}' \\(scenarios \\[1, 2, 3, 6, 7, 8\\]\\) mixes 2 different"
               r" agent / decision / theta / decision_context texts: not one decision"
               r" \(scenarios \[1, 2, 3\] are retired rows holding valid elicitations under pG;"
               r" give the changed scenarios a new attributes.context_group value, or start a new voi.db\)")
    for extra_args in (["--stage", "decision"], ["--stage", "instrument"], [],
                       ["--stage", "decision", "--scenarios", "6"]):
        with pytest.raises(SystemExit, match=refusal):
            elicit.main([*base, *extra_args])   # a real run, not a dry run: refused before any write
    con = study.connect()
    pid = db.protocol_by_name(con, "pG")["id"]
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE stage='decision'").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0] == 5   # the plan copy refused first
    assert mc.complete_fits(con, pid) == {}
    con.close()
    # renamed titles alone (the decision text restored) plan: the retired rungs keep their
    # instrument rows and the decision stage stores the group's rows on their representative
    for sc, was in zip(scen[:3], original[:3], strict=True):
        sc["decision"] = was["decision"]
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main([*base, "--stage", "decision", "--dry-run"])
    assert f"member {HAIKU} (k=1 (override of 2)): 2 pending slots over 2 groups" in capsys.readouterr().out


def test_relocated_template_is_a_stage_change(tmp_path):
    """template_path is part of the stage config the protocol hash freezes:
    the same template text under a new path is refused like an edit, and
    the registered row keeps its template_path (there is no relocation
    branch to reach)."""
    study = build(tmp_path)
    con = study.connect()
    pid = db.get_or_create_protocol(con, study.protocol_path("pG"), study.root)
    (study.root / "templates/decision_moved.md").write_text(DECISION_TEMPLATE)
    cfg = cfg_of(study, "pG")
    cfg["stages"][0]["template_path"] = "templates/decision_moved.md"
    write_cfg(study, cfg)
    with pytest.raises(RuntimeError, match=r"different \['template_hash', 'stages'\]"):
        db.get_or_create_protocol(con, study.protocol_path("pG"), study.root)
    prot = db.protocol_by_name(con, "pG")
    assert prot["id"] == pid and prot["template_path"] == "templates/decision.md + templates/instrument.md"
    con.close()


def test_empty_rendered_field_warns_in_the_dry_run_and_refuses_the_paid_stage(tmp_path, monkeypatch, capsys):
    """A scenario field a planned stage's template renders is empty (the
    committed study's decision_context until its decision_facts are
    written): the dry run warns per stage and field, the paid run of a
    stage that renders it is refused before the credentials check and any
    write, the other stage alone still runs, and the field cannot be filled
    afterwards (an elicited scenario is frozen), which is why the refusal
    says to fill it first."""
    scen = scenarios()
    for sc in scen[:3]:   # the home group's shared decision context
        sc["decision_context"] = "  "
    study = build(tmp_path, scen)
    fake, calls = StagedFake(), []
    monkeypatch.setattr(elicit, "get_provider", lambda name: lambda *a: calls.append(a) or fake(*a))
    base = ["--study", str(study.root), "--protocol", "pG", "--members", HAIKU, "--k", "1"]
    elicit.main([*base, "--dry-run"])
    out = capsys.readouterr().out
    assert ("  warning: stage decision: the template renders $decision_context, which is empty for 1 planned"
            " scenario(s) [1]; the paid run of this stage is refused until the field is filled in"
            " scenarios.json") in out
    assert "renders $context" not in out and "7 slots would be elicited" in out
    refusal = (r"stage decision: the template renders \$decision_context, which is empty for 1 planned"
               r" scenario\(s\) \[1\]\nfill the field in scenarios.json first \(an elicited scenario is"
               r" frozen, so it cannot be filled later\); nothing was written")
    for extra_args in ([], ["--stage", "decision"]):
        with pytest.raises(SystemExit, match=refusal):
            elicit.main([*base, "--yes", *extra_args])
    assert calls == [] and not list(study.root.glob("voi.db*"))
    elicit.main([*base, "--yes", "--stage", "instrument"])   # renders $context, filled for every scenario
    assert "done: 5/5 slots valid" in capsys.readouterr().out and len(calls) == 5
    for sc in scen[:3]:
        sc["decision_context"] = f"Decision facts for {HOME}."
    study.scenarios_json.write_text(json.dumps(scen))
    with pytest.raises(SystemExit, match=r"already has 1 elicitation\(s\): elicited scenarios are frozen"):
        elicit.main([*base, "--dry-run"])


@pytest.mark.parametrize("protocol, match", [
    ("p004", r"^protocol p004: stage decision: protocol-level decision_contexts are gone"),
    ("p003", r"^protocol p003: .*single-prompt protocols were retired"),
    ("g001", r"^protocol g001: .*only the binary model remains"),
])
def test_dry_run_of_an_archived_protocol_exits_with_its_message(protocol, match):
    """The documented read of an archived study (README: connect_copy, used
    by every dry run) meets a protocol in one of the retired forms: the
    registration's refusal is the exit message, not a traceback, and the
    frozen file is untouched. Read-only on the committed archive."""
    src = ARCHIVE_SIM2REAL / "voi.db"
    before = src.read_bytes()
    with pytest.raises(SystemExit, match=match):
        elicit.main(["--study", str(ARCHIVE_SIM2REAL), "--protocol", protocol, "--dry-run"])
    assert src.read_bytes() == before


def test_archived_study_dry_runs_but_is_never_elicited(tmp_path, monkeypatch, capsys):
    """A two-stage protocol dropped into a study under archive/ plans on the
    in-memory copy (--dry-run) but the paid path is refused before the
    confirmation, the preflight and the connect that would create or migrate
    voi.db; no provider is called and no file appears."""
    root = tmp_path.resolve()
    monkeypatch.setattr(db, "ROOT", root)
    study = build(root / "archive" / "pilots")   # <root>/archive/pilots/study
    assert study.archived
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: (_ for _ in ()).throw(AssertionError("provider called")))
    elicit.main(["--study", str(study.root), "--protocol", "pS", "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY RUN: protocol pS" in out and "estimated total: $0.00 + unknown" in out
    with pytest.raises(SystemExit, match="archived study .*read-only"):
        elicit.main(["--study", str(study.root), "--protocol", "pS", "--yes"])
    assert not list(study.root.glob("voi.db*"))


def test_archived_single_stage_protocol_cannot_be_elicited(tmp_path):
    """An archived database's single-prompt protocol row (no stages_json) is
    readable but the harness refuses to plan it."""
    study = build(tmp_path)
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    con.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats,"
                " members_json) VALUES ('p001', 'templates/elicitor.md', 'h', 'claude_cli:haiku', 1, ?)",
                (db.members_json(MEMBERS[:1]),))
    con.commit()
    prot = db.protocol_by_name(con, "p001")
    assert db.protocol_stages(prot) is None and db.protocol_template_vars(prot) == {}
    with pytest.raises(SystemExit, match="archived single-prompt protocol"):
        elicit.plan_jobs(con, study, prot["id"], None, None, None)
    con.close()


@pytest.mark.parametrize("stage, var, other", [
    ("instrument", "anchors_decision", "decision"),
    ("instrument", "decision_numbers", "decision"),
    ("decision", "anchors_instrument", "instrument"),
    ("decision", "instrument_notes", "instrument"),
])
def test_template_variables_are_scoped_to_their_prompt(tmp_path, monkeypatch, stage, var, other):
    """DESIGN section 4: the instrument prompt never carries a decision-level
    number, the decision prompt nothing of the instrument. A template
    variable named decision_* or anchors_decision renders only in the
    decision template, instrument_* or anchors_instrument only in the
    instrument one: the other template naming it is refused at planning,
    before any call or write, whatever the variable's text."""
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake())
    study = build(tmp_path)
    cfg = cfg_of(study, "pS")
    cfg["template_vars"][var] = "Anchor: p 0.02 / 0.08 / 0.25, B 1.5e5, K 1e4"
    write_cfg(study, cfg)
    path = study.root / "templates" / f"{stage}.md"
    path.write_text(path.read_text() + f"\n${var}\n")
    refused = (rf"^{stage} template uses \${var}: a template variable named {other}_\* or anchors_{other}"
               rf" renders only in the {other} template")
    with pytest.raises(SystemExit, match=refused):
        elicit.main(["--study", str(study.root), "--protocol", "pS", "--dry-run"])
    assert not list(study.root.glob("voi.db*"))
