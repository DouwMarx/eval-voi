"""Staged decision / instrument protocols on temporary copies of the archived
sim2real pilot with a fake provider: registration and immutability with
stages_json, validation of a stage's parameter subset, the dry run listing
both stages, elicitation and resume per stage, the assembly of a scenario's
fits from its group's decision rows and its own instrument rows, MC and
replay. No CLI, no network."""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import pytest
import yaml

from voi_rank import db, elicit, mc
from voi_rank.study import Study
from voi_rank.validate import validate_payload

PILOTS = Path(__file__).resolve().parent.parent / "archive" / "pilots"

SEED = {
    "p": (0.02, 0.08, 0.25), "s": (0.60, 0.80, 0.95), "t": (0.70, 0.90, 0.98),
    "B": (20e3, 150e3, 1.5e6), "K": (2e3, 10e3, 60e3), "C": (300.0, 1000.0, 5000.0),
}
HAIKU, SONNET = "claude_cli:haiku", "claude_cli:sonnet"
HOME, AV = "home manipulator", "AV AEB"


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
        if "DECISION-level" in prompt:
            names = ["p", "B", "K"]
        elif "INSTRUMENT-level" in prompt:
            names = ["s", "t", "C"]
        else:
            names = list(SEED)
        prm = {}
        for name in names:
            f = float(np.exp(rng.normal(0.0, 0.3 if name in ("B", "K", "C") else 0.08)))
            q = [v * f for v in SEED[name]]
            if name in ("p", "s", "t"):
                q = [float(np.clip(v, 0.005, 0.995)) for v in q]
                if not q[0] < q[1] < q[2]:
                    q = list(SEED[name])
            prm[name] = {"reasoning": f"{name} for {model}", "p5": q[0], "p50": q[1], "p95": q[2],
                         "unit": "USD" if name in ("B", "K", "C") else "probability"}
        text = json.dumps({"parameters": prm})
        raw = json.dumps({"result": text, "total_cost_usd": self.cost})
        return {"result": text, "total_cost_usd": self.cost}, raw, None


def copy_study(name: str, tmp_path: Path) -> Study:
    """A writable copy of an archived pilot study (scenarios, protocols and
    templates; never its voi.db), so nothing under archive/ is touched."""
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy(PILOTS / name / "scenarios.json", root / "scenarios.json")
    shutil.copytree(PILOTS / name / "protocols", root / "protocols")
    shutil.copytree(PILOTS / name / "templates", root / "templates")
    return Study.resolve(root)


def p004_cfg(study) -> dict:
    return yaml.safe_load(study.protocol_path("p004").read_text())


def write_p004(study, cfg: dict) -> Path:
    path = study.protocol_path("p004")
    path.write_text(yaml.safe_dump(cfg))
    return path


# --- registration -----------------------------------------------------------------

def test_staged_protocol_registers_stages_and_is_immutable(tmp_path):
    study = copy_study("sim2real", tmp_path)
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    pid = db.get_or_create_protocol(con, study.protocol_path("p004"), study.root)
    prot = db.protocol_by_name(con, "p004")
    stages = db.protocol_stages(prot)
    assert [s["name"] for s in stages] == ["decision", "instrument"]
    dec, ins = stages
    assert dec["params"] == ["p", "B", "K"] and ins["params"] == ["s", "t", "C"]
    assert dec["group_key"] == "attributes.context_group" and "group_key" not in ins
    assert set(dec["decision_contexts"]) == {HOME, AV}
    assert "fleet size" in dec["decision_contexts"][HOME]
    assert "production volume" in dec["decision_contexts"][AV]
    assert dec["template_hash"] == db.sha256((study.root / "templates/decision.md").read_text())
    assert ins["template_hash"] == db.sha256((study.root / "templates/instrument.md").read_text())
    assert prot["template_path"] == "templates/decision.md + templates/instrument.md"
    assert prot["template_hash"] == db.sha256(db.stages_json(stages)) and prot["model_kind"] == "binary"
    assert db.group_stage(stages) == dec and db.scenario_stage(stages) == ins
    assert db.stage_of_param(stages, "B") == dec and db.stage_of_param(stages, "C") == ins
    p003 = db.get_or_create_protocol(con, study.protocol_path("p003"), study.root)
    assert db.stage_of_param(None, "p") is None and p003 != pid
    assert db.protocol_stages(db.protocol_by_name(con, "p003")) is None
    # the same file again: the same id
    assert db.get_or_create_protocol(con, study.protocol_path("p004"), study.root) == pid
    # a changed decision context, template or stage config is refused
    cfg = p004_cfg(study)
    cfg["stages"][0]["decision_contexts"][HOME] += " Extra sentence."
    write_p004(study, cfg)
    with pytest.raises(RuntimeError, match="different \\['template_hash', 'stages'\\]"):
        db.get_or_create_protocol(con, study.protocol_path("p004"), study.root)
    write_p004(study, p004_cfg(study) | {"stages": p004_cfg(study)["stages"]})
    cfg = p004_cfg(study)
    cfg["stages"][0]["decision_contexts"][HOME] = dec["decision_contexts"][HOME]
    write_p004(study, cfg)
    assert db.get_or_create_protocol(con, study.protocol_path("p004"), study.root) == pid
    (study.root / "templates/decision.md").write_text(
        (study.root / "templates/decision.md").read_text() + "\nOne more line.\n")
    with pytest.raises(RuntimeError, match="template_hash"):
        db.get_or_create_protocol(con, study.protocol_path("p004"), study.root)
    con.close()


@pytest.mark.parametrize("edit, match", [
    (lambda c: c.update(model="gaussian"), "not supported: only the binary model remains"),
    (lambda c: c.update(template_path="templates/elicitor.md"), "not a template_path"),
    (lambda c: c["stages"].pop(), "exactly two stages"),
    (lambda c: c["stages"][1].update(params=["s", "t"]), "partition"),
    (lambda c: c["stages"][1].update(params=["s", "t", "C", "e"]), "subset of"),
    (lambda c: c["stages"][1].update(group_key="attributes.level"), "exactly one stage"),
    (lambda c: c["stages"][0].update(group_key="attrs.x"), "group_key must be"),
    (lambda c: c["stages"][0].update(name="instrument"), "names must differ"),
    (lambda c: c["stages"][0].update(decision_contexts="text"), "decision_contexts must map"),
])
def test_bad_stage_configs_are_refused(tmp_path, edit, match):
    study = copy_study("sim2real", tmp_path)
    cfg = p004_cfg(study)
    edit(cfg)
    write_p004(study, cfg)
    con = study.connect()
    with pytest.raises(RuntimeError, match=match):
        db.get_or_create_protocol(con, study.protocol_path("p004"), study.root)
    con.close()


# --- validation of a stage's subset ----------------------------------------------------

def _payload(names):
    return {"parameters": {n: {"reasoning": "r", "p5": SEED[n][0], "p50": SEED[n][1], "p95": SEED[n][2]}
                           for n in names}}


def test_validate_payload_accepts_a_stage_subset():
    clean, err = validate_payload(_payload(["p", "B", "K"]), ["p", "B", "K"])
    assert err is None and list(clean) == ["p", "B", "K"]
    clean, err = validate_payload(_payload(["s", "t", "C"]), ["s", "t", "C"])
    assert err is None and list(clean) == ["s", "t", "C"]
    # the full payload validates against a subset (extra keys ignored), a subset not against the full list
    assert validate_payload(_payload(SEED), ["s", "t", "C"])[1] is None
    assert validate_payload(_payload(["p", "B", "K"]))[1] == "schema: missing parameters ['s', 't', 'C']"
    # informativeness only when both s and t are asked for; the prior check only with p
    bad = _payload(["s", "t", "C"])
    bad["parameters"]["s"] = {"p5": 0.02, "p50": 0.05, "p95": 0.08}
    assert "informativeness" in validate_payload(bad, ["s", "t", "C"])[1]
    assert validate_payload(bad, ["s", "C"])[1] is None
    bad = _payload(["p", "B", "K"])
    bad["parameters"]["p"] = {"p5": 0.0001, "p50": 0.0005, "p95": 0.001}
    assert "degenerate prior" in validate_payload(bad, ["p", "B", "K"])[1]
    assert validate_payload(bad, ["B", "K"])[1] is None
    with pytest.raises(ValueError, match="unknown parameter names"):
        validate_payload(_payload(SEED), ["p", "e"])


# --- end to end ------------------------------------------------------------------------

def test_staged_elicitation_mc_analyses_end_to_end(tmp_path, monkeypatch, capsys):
    study = copy_study("sim2real", tmp_path)
    scen = json.loads(study.scenarios_json.read_text())
    fake = StagedFake()
    monkeypatch.setattr(elicit, "get_provider", lambda name: fake)
    # the dry run lists both stages and renders a prompt of each
    elicit.main(["--study", str(study.root), "--protocol", "p004", "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY RUN: protocol p004 (stages decision + instrument, hash" in out
    assert ("stage decision (template templates/decision.md, params p, B, K,"
            " group_key attributes.context_group):") in out
    assert f"member {HAIKU} (k=5): 10 pending slots over 2 groups ({AV}, {HOME})" in out
    assert "stage instrument (template templates/instrument.md, params s, t, C):" in out
    assert f"member {SONNET} (k=5): 75 pending slots over 15 scenarios (ids 1..15)" in out
    assert f"first pending prompt of stage decision (group '{AV}', representative scenario 11," in out
    assert "first pending prompt of stage instrument (scenario 1," in out
    assert f"{3 * (10 + 75)} slots would be elicited; no provider was called." in out
    dec_prompt, ins_prompt = out.split("first pending prompt of stage decision")[1].split(
        "first pending prompt of stage instrument")
    assert scen[10]["agent"] in dec_prompt and "production volume" in dec_prompt
    assert scen[10]["instrument"] not in dec_prompt and scen[10]["context"][:80] not in dec_prompt
    assert '"s":' not in dec_prompt and '"C":' not in dec_prompt and '"p":' in dec_prompt
    assert scen[0]["instrument"] in ins_prompt and scen[0]["context"][:80] in ins_prompt
    assert '"p":' not in ins_prompt and '"s":' in ins_prompt and "$decision_context" not in ins_prompt
    assert not list(study.root.glob("voi.db*"))
    # the plan prints the per-stage breakdown (declined without --yes)
    with pytest.raises(SystemExit, match="--yes"):
        elicit.main(["--study", str(study.root), "--protocol", "p004", "--k", "2",
                     "--members", f"{HAIKU},{SONNET}"])
    out = capsys.readouterr().out
    assert f"{HAIKU}: 34 slots (decision 4, instrument 30), estimated cost" in out
    # the decision stage alone, two members, k = 2
    elicit.main(["--study", str(study.root), "--protocol", "p004", "--stage", "decision", "--k", "2",
                 "--members", f"{HAIKU},{SONNET}", "--yes"])
    out = capsys.readouterr().out
    assert "done: 8/8 slots valid" in out
    assert f"scenario 1 stage decision (group '{HOME}') {HAIKU} repeat 0: ok" in out
    con = study.connect()
    prot = db.protocol_by_name(con, "p004")
    pid = prot["id"]
    rows = con.execute("SELECT * FROM elicitations WHERE protocol_id=? ORDER BY id", (pid,)).fetchall()
    assert len(rows) == 8 and all(r["stage"] == "decision" and r["valid"] for r in rows)
    assert {r["scenario_id"] for r in rows} == {1, 11}   # the groups' representatives (lowest ids)
    names = {r[0] for r in con.execute(
        "SELECT DISTINCT p.name FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.protocol_id=?", (pid,))}
    assert names == {"p", "B", "K"}
    # resume per stage: the decision stage is done, the instrument stage pending
    elicit.main(["--study", str(study.root), "--protocol", "p004", "--stage", "decision", "--k", "2",
                 "--members", f"{HAIKU},{SONNET}", "--yes"])
    assert "nothing to do" in capsys.readouterr().out
    _, jobs = elicit.plan_jobs(con, study, pid, None, 2, {HAIKU, SONNET})
    assert len(jobs) == 60 and {j["stage"] for j in jobs} == {"instrument"}
    assert all(j["names"] == ["s", "t", "C"] and "group" not in j for j in jobs)
    with pytest.raises(SystemExit, match="--stage 'nope': protocol p004 has stages"):
        elicit.plan_jobs(con, study, pid, None, 2, None, stage="nope")
    p003 = db.get_or_create_protocol(con, study.protocol_path("p003"), study.root)
    with pytest.raises(SystemExit, match="has no stages"):
        elicit.plan_jobs(con, study, p003, None, 2, None, stage="decision")
    # incomplete until the instrument stage is in
    assert mc.complete_fits(con, pid) == {}
    elicit.main(["--study", str(study.root), "--protocol", "p004", "--k", "2",
                 "--members", f"{HAIKU},{SONNET}", "--yes"])
    assert "done: 60/60 slots valid" in capsys.readouterr().out
    # a decision row and an instrument row of one member and repeat share a scenario; a
    # duplicate valid slot within a stage is refused
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE protocol_id=? AND scenario_id=1"
                       " AND provider='claude_cli' AND model='haiku' AND repeat_ix=0 AND valid=1",
                       (pid,)).fetchone()[0] == 2
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_elicitation(con, 1, pid, "claude_cli", "haiku", 0, "h", "{}", True, None, "decision")
    con.rollback()
    # assembly: p, B, K of every scenario of a group are the group's decision fits (same
    # elicitation ids); s, t, C its own instrument fits
    fits = mc.complete_fits(con, pid)
    assert sorted(fits) == list(range(1, 16))
    home = [sc_id for sc_id in range(1, 11)]
    dec_ids = {f["elicitation_id"] for f in fits[1]["p"]}
    assert len(dec_ids) == 4 and all({f["elicitation_id"] for f in fits[s]["B"]} == dec_ids for s in home)
    assert {f["elicitation_id"] for f in fits[11]["K"]}.isdisjoint(dec_ids)
    assert all(len(fits[s]["s"]) == 4 for s in fits)
    assert {f["elicitation_id"] for f in fits[1]["s"]}.isdisjoint({f["elicitation_id"] for f in fits[2]["s"]})
    assert fits[1]["p"] == fits[7]["p"] and fits[1]["C"] != fits[7]["C"]
    assert db.elicited_p50s(con, pid, 5, "p") == db.elicited_p50s(con, pid, 1, "p")
    assert db.elicited_p50s(con, pid, 5, "s") != db.elicited_p50s(con, pid, 1, "s")
    assert db.elicited_p50s(con, pid, 12, "B", "claude_cli", "sonnet") == \
        [f["p50"] for f in fits[12]["B"] if f["model"] == "sonnet"]
    assert db.scenario_group_ids(con, "attributes.context_group", 9) == home
    assert db.scenario_groups_by_key(con, "attributes.context_group") == {AV: list(range(11, 16)), HOME: home}
    # a group without a complete decision stage leaves its scenarios incomplete
    con.execute("UPDATE elicitations SET valid=0 WHERE protocol_id=? AND stage='decision' AND scenario_id=11",
                (pid,))
    assert sorted(mc.complete_fits(con, pid)) == home
    con.rollback()
    # MC, data hash (each shared decision fit counted once), replay
    run_id = mc.run_mc(con, "p004", seed=3, n_draws=2000, quiet=True)
    run = db.get_run(con, run_id)
    assert con.execute("SELECT COUNT(DISTINCT scenario_id) FROM results WHERE run_id=?",
                       (run_id,)).fetchone()[0] == 15
    assert run["data_hash"] == mc.data_hash(fits)
    rows_hashed = {(f["elicitation_id"], n, f["fit_params"])
                   for s in fits for n, lst in fits[s].items() for f in lst}
    assert len(rows_hashed) == 8 * 3 + 60 * 3
    ids, eff = mc.replay_efficiency(con, run_id)
    assert ids == list(range(1, 16)) and eff.shape == (15, 2000)
    # a member subset of the staged protocol pools that member's decision and instrument rows
    sub = mc.run_mc(con, "p004", seed=3, n_draws=2000, quiet=True, members=[SONNET])
    fits_sub = mc.complete_fits(con, pid, [SONNET])
    assert sorted(fits_sub) == list(range(1, 16))
    assert all({f["model"] for f in fits_sub[s][n]} == {"sonnet"} for s in fits_sub for n in db.PARAM_NAMES)
    assert db.get_run(con, sub)["data_hash"] == mc.data_hash(fits_sub) != run["data_hash"]
    ids, eff = mc.replay_efficiency(con, sub)
    assert ids == list(range(1, 16)) and eff.shape == (15, 2000)
    con.close()


def _edited_copy(tmp_path, edit_scenarios=None, edit_cfg=None, edit_template=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    study = copy_study("sim2real", tmp_path)
    if edit_scenarios:
        scen = json.loads(study.scenarios_json.read_text())
        edit_scenarios(scen)
        study.scenarios_json.write_text(json.dumps(scen))
    if edit_cfg:
        cfg = p004_cfg(study)
        edit_cfg(cfg)
        write_p004(study, cfg)
    if edit_template:
        path = study.root / "templates/decision.md"
        path.write_text(edit_template(path.read_text()))
    return study


def test_staged_planning_checks_groups_contexts_and_the_decision_template(tmp_path, monkeypatch):
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake())
    dry = ["--protocol", "p004", "--dry-run"]

    def drop_group(scen):
        del scen[3]["attributes"]["context_group"]
    study = _edited_copy(tmp_path / "a", edit_scenarios=drop_group)
    with pytest.raises(SystemExit, match=r"scenarios \[4\] carry no attributes.context_group value"):
        elicit.main(["--study", str(study.root), *dry])

    def other_decision(scen):
        scen[2]["decision"] = "A different decision"
    study = _edited_copy(tmp_path / "b", edit_scenarios=other_decision)
    with pytest.raises(SystemExit,
                       match=f"group '{HOME}' .*mixes 2 different agent / decision / theta texts"):
        elicit.main(["--study", str(study.root), *dry])

    def drop_context(cfg):
        del cfg["stages"][0]["decision_contexts"][AV]
    study = _edited_copy(tmp_path / "c", edit_cfg=drop_context)
    with pytest.raises(SystemExit, match=f"no decision_contexts entry for group '{AV}'"):
        elicit.main(["--study", str(study.root), *dry])

    study = _edited_copy(tmp_path / "d", edit_template=lambda t: t + "\nInstrument: $instrument\n")
    with pytest.raises(SystemExit, match=r"decision-stage template uses \$instrument"):
        elicit.main(["--study", str(study.root), *dry])
    study = _edited_copy(tmp_path / "e", edit_template=lambda t: t + "\nFacts: $context\n")
    with pytest.raises(SystemExit, match=r"uses \$context"):
        elicit.main(["--study", str(study.root), *dry])
    # the scenario stage template may use every scenario field, and nothing else
    study = _edited_copy(tmp_path / "f")
    elicit.main(["--study", str(study.root), *dry])
    assert not list(study.root.glob("voi.db*"))
    study = _edited_copy(tmp_path / "g")
    path = study.root / "templates/instrument.md"
    path.write_text(path.read_text() + "\nDecision context: $decision_context\n")
    with pytest.raises(SystemExit, match=r"scenario-stage template uses \$decision_context: it renders only"
                                          r" \$title, \$agent"):
        elicit.main(["--study", str(study.root), *dry])


def test_staged_planner_uses_the_db_group_not_the_selection(tmp_path, monkeypatch, capsys):
    """Decision rows are stored on the group's lowest id in the DB and a
    repeat they fill is done for every selection: a partial --scenarios never
    elicits a second set, a retired representative keeps carrying the group's
    rows, and every noise statistic counts a group once even when its rows
    sit on two scenarios."""
    study = copy_study("sim2real", tmp_path)
    fake = StagedFake()
    monkeypatch.setattr(elicit, "get_provider", lambda name: fake)
    base = ["--study", str(study.root), "--protocol", "p004", "--members", HAIKU, "--k", "2", "--yes"]
    elicit.main([*base, "--stage", "decision", "--scenarios", "12"])
    assert "done: 2/2 slots valid" in capsys.readouterr().out
    con = study.connect()
    pid = db.protocol_by_name(con, "p004")["id"]

    def stored():
        return [r[0] for r in con.execute(
            "SELECT scenario_id FROM elicitations WHERE protocol_id=? AND stage='decision' AND valid=1"
            " ORDER BY id", (pid,))]
    assert stored() == [11, 11]   # the group's lowest id, not the selected 12
    # another selection of the same group finds its decision stage done
    _, jobs = elicit.plan_jobs(con, study, pid, "13", 2, {HAIKU}, stage="decision")
    assert jobs == []
    con.close()
    elicit.main([*base, "--stage", "decision", "--scenarios", "13"])
    assert "nothing to do" in capsys.readouterr().out
    elicit.main([*base, "--stage", "decision"])
    assert "done: 2/2 slots valid" in capsys.readouterr().out
    con = study.connect()
    assert stored() == [11, 11, 1, 1]
    con.close()
    # the representative leaves scenarios.json (its title changes): the retired row 1 keeps
    # carrying the home group's rows and the decision stage plans nothing
    scen = json.loads(study.scenarios_json.read_text())
    scen[0]["title"] += " (renamed)"
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main([*base, "--stage", "decision", "--dry-run"])
    out = capsys.readouterr().out
    assert "scenario 1 " in out and "would be retired" in out
    assert f"member {HAIKU} (k=2 (override of 5)): 0 pending slots over 0 groups" in out
    assert "0 slots would be elicited" in out
    elicit.main([*base, "--dry-run"])
    out = capsys.readouterr().out
    assert f"member {HAIKU} (k=2 (override of 5)): 0 pending slots over 0 groups" in out
    assert f"member {HAIKU} (k=2 (override of 5)): 30 pending slots over 15 scenarios (ids 2..16)" in out
    elicit.main(base)
    assert "done: 30/30 slots valid" in capsys.readouterr().out
    con = study.connect()
    assert stored() == [11, 11, 1, 1]
    fits = mc.complete_fits(con, pid)
    assert sorted(fits) == list(range(2, 17))
    assert len(fits[16]["p"]) == 2 and fits[16]["p"] == fits[2]["p"] and fits[16]["s"] != fits[2]["s"]
    # a group whose rows sit on two scenarios (a second representative, as the old planner
    # stored) still feeds every scenario of the group
    eid = con.execute("SELECT id FROM elicitations WHERE protocol_id=? AND scenario_id=1 AND stage='decision'"
                      " ORDER BY id DESC LIMIT 1", (pid,)).fetchone()[0]
    con.execute("UPDATE elicitations SET scenario_id=2 WHERE id=?", (eid,))
    assert len(db.elicited_p50s(con, pid, 16, "p")) == 2
    con.rollback()
    con.close()


def test_staged_plan_refuses_a_decision_text_changed_after_the_decision_stage(tmp_path, monkeypatch, capsys):
    """Between the stages a non-representative scenario holds no rows, so the
    seed refresh accepts a new decision text for it. Every staged plan,
    --stage instrument included, then refuses the group: a mixed text over
    the group's active scenarios, or (the whole group renamed and changed)
    stored decision rows rendered from another text. No instrument row is
    assembled with a p, B, K elicited for another decision."""
    study = copy_study("sim2real", tmp_path)
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake())
    base = ["--study", str(study.root), "--protocol", "p004", "--members", HAIKU, "--k", "1", "--yes"]
    elicit.main([*base, "--stage", "decision"])
    assert "done: 2/2 slots valid" in capsys.readouterr().out
    original = study.scenarios_json.read_text()
    scen = json.loads(original)
    other = "A completely different decision: whether to buy a coffee machine"
    scen[4]["decision"] = other
    study.scenarios_json.write_text(json.dumps(scen))
    ids = "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"
    for extra_args in (["--stage", "instrument"], ["--stage", "decision"], [],
                       ["--stage", "instrument", "--scenarios", "5"]):
        with pytest.raises(SystemExit, match=f"stage decision: group '{HOME}' \\(scenarios {re.escape(ids)}"
                                             "\\) mixes 2 different agent / decision / theta texts"):
            elicit.main([*base, *extra_args, "--dry-run"])
    # the whole group changes its decision under new titles: the retired representative's
    # rows are another decision's, and it stays in the one-decision check because it holds
    # them, so the plan refuses instead of eliciting beside them
    for sc in scen[:10]:
        sc["title"] += " v2"
        sc["decision"] = other
    study.scenarios_json.write_text(json.dumps(scen))
    mixed = str([1] + list(range(16, 26)))
    refusal = (f"\\(scenarios {re.escape(mixed)}\\) mixes 2 different agent / decision / theta texts: not one"
               r" decision \(scenarios \[1\] are retired rows holding valid elicitations under p004; give the"
               r" changed scenarios a new attributes.context_group value, or start a new voi.db\)")
    for extra_args in (["--stage", "decision"], ["--stage", "instrument"]):
        with pytest.raises(SystemExit, match=refusal):
            elicit.main([*base, *extra_args, "--dry-run"])
    # the stored rows' prompt hash is checked as well: decision rows rendered from another
    # text than the group renders now (here a DB whose hashes were edited, since the seed
    # refresh freezes an elicited row's text) are refused with the same remedy
    study.scenarios_json.write_text(original)
    con = study.connect()
    con.execute("UPDATE elicitations SET prompt_hash=? WHERE stage='decision'", ("0" * 64,))
    con.commit()
    con.close()
    for extra_args in (["--stage", "decision"], ["--stage", "instrument"]):
        with pytest.raises(SystemExit, match=r"holds 1 valid decision row\(s\) elicited for a different agent"
                                             r" / decision / theta text \(prompt hash 0{12} vs \w{12} now\)"
                                             r".*new attributes.context_group value, or start a new voi.db"):
            elicit.main([*base, *extra_args, "--dry-run"])
    con = study.connect()
    assert con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0] == 2   # nothing written
    assert con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0] == 15
    con.close()


def test_staged_plan_refuses_a_decision_text_changed_after_the_instrument_stage(tmp_path, monkeypatch,
                                                                                   capsys):
    """The mirror of the test above: the instrument stage first, then the
    whole group renamed under a new decision text. No decision rows exist
    yet, so the prompt-hash check cannot fire; the retired rungs hold valid
    instrument rows elicited for the old decision and stay in the
    one-decision check, so every plan (the decision stage first of all)
    refuses instead of storing the new decision's p, B, K on the retired
    representative and ranking the retired rungs with them."""
    study = copy_study("sim2real", tmp_path)
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake())
    base = ["--study", str(study.root), "--protocol", "p004", "--members", HAIKU, "--k", "1", "--yes"]
    elicit.main([*base, "--stage", "instrument"])
    assert "done: 15/15 slots valid" in capsys.readouterr().out
    original = json.loads(study.scenarios_json.read_text())
    scen = json.loads(study.scenarios_json.read_text())
    for sc in scen[:10]:
        sc["title"] += " v2"
        sc["decision"] = "A new decision: whether to ship a coffee machine"
    study.scenarios_json.write_text(json.dumps(scen))
    mixed = str(list(range(1, 11)) + list(range(16, 26)))
    retired = str(list(range(1, 11)))
    refusal = (f"stage decision: group '{HOME}' \\(scenarios {re.escape(mixed)}\\) mixes 2 different agent"
               r" / decision / theta texts: not one decision"
               f" \\(scenarios {re.escape(retired)} are retired rows holding valid elicitations under p004;"
               r" give the changed scenarios a new attributes.context_group value, or start a new voi.db\)")
    for extra_args in (["--stage", "decision"], ["--stage", "instrument"], [],
                       ["--stage", "decision", "--scenarios", "16"]):
        with pytest.raises(SystemExit, match=refusal):
            elicit.main([*base, *extra_args])   # a real run, not a dry run: refused before any write
    con = study.connect()
    pid = db.protocol_by_name(con, "p004")["id"]
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE stage='decision'").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0] == 15   # the plan copy refused first
    assert mc.complete_fits(con, pid) == {}
    con.close()
    # renamed titles alone (the text unchanged) still plan: the retired rungs keep their
    # instrument rows and the decision stage stores the group's rows on their representative
    for sc, was in zip(scen[:10], original[:10], strict=True):
        sc["decision"] = was["decision"]
    study.scenarios_json.write_text(json.dumps(scen))
    elicit.main([*base, "--stage", "decision", "--dry-run"])
    assert f"member {HAIKU} (k=1 (override of 5)): 2 pending slots over 2 groups" in capsys.readouterr().out


def test_dry_run_of_p004_on_sim2real_renders_every_scenario(tmp_path, monkeypatch):
    """Every scenario of the study belongs to a group with a decision context
    and renders under both stages; ai-safety-evals has no p004 by design."""
    study = copy_study("sim2real", tmp_path)
    monkeypatch.setattr(elicit, "get_provider",
                        lambda n: (_ for _ in ()).throw(AssertionError("provider called")))
    con = study.connect_copy()
    db.seed_scenarios(con, study.scenarios_json)
    pid = db.get_or_create_protocol(con, study.protocol_path("p004"), study.root)
    _, jobs = elicit.plan_jobs(con, study, pid, None, None, None)
    scen = db.get_scenarios(con)
    assert len(jobs) == 3 * (5 * 2 + 5 * len(scen))
    assert {j["scenario_id"] for j in jobs if j["stage"] == "instrument"} == {r["id"] for r in scen}
    assert {j["group"] for j in jobs if j["stage"] == "decision"} == {HOME, AV}
    reps = {j["group"]: j["scenario_id"] for j in jobs if j["stage"] == "decision"}
    groups = db.scenario_groups_by_key(con, "attributes.context_group")
    assert reps == {g: min(ids) for g, ids in groups.items()}
