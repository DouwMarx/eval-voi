"""DB migration from the v1 schema, protocol member handling and immutability,
seeding idempotence, retirement, and the pooling of fits over members."""

import json
import shutil
import sqlite3
from pathlib import Path

import pytest
import yaml

from voi_rank import db, mc
from voi_rank.fit import DECISION_PARAMS, INSTRUMENT_PARAMS, fit_param
from voi_rank.study import Study

ARCHIVE = Path(__file__).resolve().parent.parent / "archive"

_REAL_GIT_STATE = db.git_state   # captured before the hermetic fixture replaces it

V1_SCHEMA = """
CREATE TABLE scenarios (id INTEGER PRIMARY KEY, created_at TEXT, title TEXT, agent TEXT,
  decision TEXT, theta_definition TEXT, instrument TEXT, domain_tags TEXT, source TEXT, raw_json TEXT);
CREATE TABLE protocols (id INTEGER PRIMARY KEY, name TEXT, template_path TEXT, template_hash TEXT,
  model_alias TEXT, k_repeats INTEGER, cli_version TEXT, notes TEXT);
CREATE TABLE elicitations (id INTEGER PRIMARY KEY, scenario_id INTEGER, protocol_id INTEGER,
  repeat_ix INTEGER, prompt_hash TEXT, raw_response TEXT, valid INTEGER, error TEXT, created_at TEXT);
CREATE TABLE parameters (id INTEGER PRIMARY KEY, elicitation_id INTEGER, name TEXT, p5 REAL,
  p50 REAL, p95 REAL, unit TEXT, reasoning TEXT, dist_family TEXT, fit_params TEXT, fit_residual REAL,
  fit_warning INTEGER);
CREATE TABLE runs (id INTEGER PRIMARY KEY, created_at TEXT, seed INTEGER, n_draws INTEGER, code_hash TEXT,
  protocol_id INTEGER);
CREATE TABLE results (run_id INTEGER, scenario_id INTEGER, metric TEXT, q05 REAL, q25 REAL, q50 REAL,
  q75 REAL, q95 REAL, p_positive REAL);
CREATE TABLE sensitivities (run_id INTEGER, scenario_id INTEGER, param TEXT, spearman REAL);
"""


def make_v1_db(path):
    con = sqlite3.connect(path)
    con.executescript(V1_SCHEMA)
    con.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats)"
                " VALUES ('p001', 'elicitation/templates/elicitor.md', 'h', 'haiku', 3)")
    con.execute("INSERT INTO scenarios (title, source) VALUES ('S', 'seed')")
    con.execute("INSERT INTO elicitations (scenario_id, protocol_id, repeat_ix, valid)"
                " VALUES (1, 1, 0, 1)")
    con.commit()
    con.close()


def test_connect_migrates_v1_db(tmp_path):
    path = tmp_path / "v1.db"
    make_v1_db(path)
    con = db.connect(path)
    cols = {t: {r[1] for r in con.execute(f"PRAGMA table_info({t})")}
            for t in ("scenarios", "elicitations", "protocols")}
    assert {"context", "grp", "attributes", "decision_context", "instrument_context",
            "sources"} <= cols["scenarios"]
    assert {"provider", "model", "stage"} <= cols["elicitations"]
    assert {"members_json", "stages_json", "template_vars_json"} <= cols["protocols"]
    row = con.execute("SELECT provider, model FROM elicitations").fetchone()
    assert (row["provider"], row["model"]) == ("claude_cli", "haiku")
    # legacy protocol row converts to a single claude_cli member
    prot = con.execute("SELECT * FROM protocols").fetchone()
    assert db.protocol_members(prot) == [{"provider": "claude_cli", "model": "haiku",
                                         "k_repeats": 3}]
    # idempotent
    assert db.migrate(con) == []


def write_protocol(study, name, instrument_text, members, extra=None,
                   decision_text="D $agent $decision_context"):
    """A two-stage protocol file (and its two templates) under `study`."""
    (study / "templates").mkdir(exist_ok=True)
    (study / "protocols").mkdir(exist_ok=True)
    (study / "templates" / f"{name}_decision.md").write_text(decision_text)
    (study / "templates" / f"{name}_instrument.md").write_text(instrument_text)
    cfg = {"name": name, "notes": "", "members": members,
           "stages": [{"name": "decision", "template_path": f"templates/{name}_decision.md",
                       "params": DECISION_PARAMS, "group_key": "self"},
                      {"name": "instrument", "template_path": f"templates/{name}_instrument.md",
                       "params": INSTRUMENT_PARAMS}]}
    cfg.update(extra or {})
    path = study / "protocols" / f"{name}.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_protocol_members_and_immutability(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    members = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 2},
               {"provider": "openrouter", "model": "openai/gpt-4o-mini", "k_repeats": 3}]
    p = write_protocol(tmp_path, "pX", "T $title $context", members=members)
    pid = db.get_or_create_protocol(con, p, tmp_path)
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (pid,)).fetchone()
    assert db.protocol_members(prot) == members
    assert prot["k_repeats"] == 5 and "openrouter:openai/gpt-4o-mini" in prot["model_alias"]
    assert prot["template_path"] == "templates/pX_decision.md + templates/pX_instrument.md"
    # same file again: same id
    assert db.get_or_create_protocol(con, p, tmp_path) == pid
    # changed member list: refused
    write_protocol(tmp_path, "pX", "T $title $context", members=members[:1])
    with pytest.raises(RuntimeError, match="members"):
        db.get_or_create_protocol(con, p, tmp_path)
    # changed template content: refused
    write_protocol(tmp_path, "pX", "T changed", members=members)
    with pytest.raises(RuntimeError, match="template_hash"):
        db.get_or_create_protocol(con, p, tmp_path)


def test_seed_scenarios_idempotent_with_v2_fields(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    scen = tmp_path / "scenarios.json"
    sources = [{"key": "gotting2025vct", "kind": "catalog", "ref": "https://arxiv.org/abs/x", "role": "both"}]
    scen.write_text(json.dumps([{
        "title": "A", "agent": "a", "decision": "d", "theta_definition": "t",
        "instrument": "i", "decision_context": "decision facts", "instrument_context": "instrument facts",
        "decision_facts": "decision facts", "instrument_facts": "instrument facts", "sources": sources,
        "domain_tags": ["x"], "group": "frontier model", "attributes": {"level": 2, "keys": ["k"]},
    }, {"title": "B", "agent": "a", "decision": "d", "theta_definition": "t", "instrument": "i",
        "context": "the pilots' single facts block"}]))
    assert db.seed_scenarios(con, scen) == 2
    assert db.seed_scenarios(con, scen) == 0
    rows = db.get_scenarios(con, "seed")
    assert len(rows) == 2
    a = rows[0]
    assert a["decision_context"] == "decision facts" and a["instrument_context"] == "instrument facts"
    assert json.loads(a["sources"]) == sources and a["context"] is None and a["grp"] == "frontier model"
    assert db.scenario_attributes(a) == {"level": 2, "keys": ["k"]}
    assert json.loads(a["raw_json"])["decision_facts"] == "decision facts"   # raw_json keeps everything
    b = rows[1]
    assert b["context"] == "the pilots' single facts block" and b["decision_context"] is None
    assert b["sources"] is None and b["grp"] is None and db.scenario_attributes(b) == {}


def _store(con, sid, pid, provider, model, rix, names):
    """A valid single-stage (archived shape: stage NULL) elicitation row with
    one parameter row per name; a name outside PARAM_NAMES ('C', 'e') gets a
    lognormal fit under another name."""
    eid = db.insert_elicitation(con, sid, pid, provider, model, rix, "h", "{}", True, None)
    for n in names:
        q = (0.1, 0.3, 0.6) if n in ("p", "s", "t", "e") else (10.0, 100.0, 1000.0)
        fit = fit_param(n if n in db.PARAM_NAMES else ("p" if n == "e" else "C_run"), *q)
        db.insert_parameter(con, eid, n, *q, "r", fit)
    con.commit()


def test_scenario_param_fits_pools_members_and_ignores_unknown_names(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    sid = db.insert_scenario(con, {"title": "S", "agent": "a", "decision": "d",
                                   "theta_definition": "t", "instrument": "i"}, "seed")
    _store(con, sid, 1, "claude_cli", "haiku", 0, db.PARAM_NAMES + ["e", "C"])
    _store(con, sid, 1, "claude_cli", "haiku", 1, db.PARAM_NAMES + ["e", "C"])
    _store(con, sid, 1, "openrouter", "m", 0, db.PARAM_NAMES)
    fits = db.scenario_param_fits(con, 1)
    assert set(fits[sid]) == set(db.PARAM_NAMES)
    assert len(fits[sid]["p"]) == 3 and len(fits[sid]["n"]) == 3
    assert [f["provider"] for f in fits[sid]["p"]] == ["claude_cli", "claude_cli", "openrouter"]
    assert db.valid_repeats(con, sid, 1, "claude_cli", "haiku") == {0, 1}
    assert db.valid_repeats(con, sid, 1, "openrouter", "m") == {0}


def test_envelope_cost_reads_both_provider_shapes():
    assert db.envelope_cost(json.dumps({"total_cost_usd": 0.5})) == 0.5
    assert db.envelope_cost(json.dumps({"usage": {"cost": 0.25}})) == 0.25
    assert db.envelope_cost("not json") == 0.0
    assert db.envelope_cost(json.dumps({"usage": {}})) == 0.0


# --- review fixes -----------------------------------------------------------

def test_git_hash_is_code_scoped_and_marks_dirty_tree(monkeypatch):
    monkeypatch.setattr(db, "git_state", _REAL_GIT_STATE)
    seen = []

    class Out:
        def __init__(self, text):
            self.stdout = text

    def runner(status_text):
        def run(cmd, **kw):
            seen.append(cmd)
            return Out("abc123\n" if cmd[1] == "rev-parse" else status_text)
        return run

    monkeypatch.setattr(db.subprocess, "run", runner(" M voi_rank/db.py\n?? voi_rank/new.py\n"))
    assert db.git_hash() == "abc123-dirty"
    assert db.git_state() == ("abc123", [" M voi_rank/db.py", "?? voi_rank/new.py"])
    # git is asked about the code paths only: a rewritten voi.db or report
    # (frozen by their own hashes) never dirties the code hash; untracked
    # files are listed one by one whatever status.showUntrackedFiles says, so
    # a new uncommitted module under voi_rank/ is never invisible
    assert seen[-1] == ["git", "status", "--porcelain", "--untracked-files=all", "--",
                        "voi_rank", "pyproject.toml", "uv.lock"]
    monkeypatch.setattr(db.subprocess, "run", runner(""))
    assert db.git_hash() == "abc123" and db.git_state() == ("abc123", [])
    assert db.is_dirty_hash("abc123-dirty") and not db.is_dirty_hash("abc123")
    assert not db.is_dirty_hash(None)

    def no_git(cmd, **kw):
        raise FileNotFoundError("git")
    monkeypatch.setattr(db.subprocess, "run", no_git)
    assert db.git_state() == ("unknown", []) and db.git_hash() == "unknown"


def test_duplicate_valid_slots_block_the_index_with_repair_sql(tmp_path):
    path = tmp_path / "v1.db"
    make_v1_db(path)
    con = sqlite3.connect(path)
    con.execute("INSERT INTO elicitations (scenario_id, protocol_id, repeat_ix, valid)"
                " VALUES (1, 1, 0, 1)")   # a second valid row for the same slot
    con.commit()
    con.close()
    with pytest.raises(RuntimeError, match=r"scenario 1 protocol 1 claude_cli:haiku repeat 0: 2 valid"
                                            r" rows \(ids 1,2\)") as ex:
        db.connect(path)
    assert db.DUPLICATE_SLOT_REPAIR_SQL in str(ex.value)
    con = sqlite3.connect(path)
    con.execute(db.DUPLICATE_SLOT_REPAIR_SQL)
    con.commit()
    con.close()
    con = db.connect(path)
    assert [tuple(r) for r in con.execute("SELECT id, valid, error FROM elicitations ORDER BY id")] == \
        [(1, 1, None), (2, 0, "duplicate slot")]
    assert con.execute("SELECT 1 FROM sqlite_master WHERE name='ux_elicitations_valid_slot_stage'").fetchone()


def test_duplicate_members_rejected():
    with pytest.raises(ValueError, match="more than once"):
        db.normalize_members({"members": [
            {"provider": "claude_cli", "model": "haiku", "k_repeats": 1},
            {"provider": "openrouter", "model": "x", "k_repeats": 1},
            {"provider": "claude_cli", "model": "haiku", "k_repeats": 2}]})
    assert db.normalize_members({"model_alias": "haiku", "k_repeats": 1}) == \
        [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]


def test_archived_pilot_db_opens_read_only(tmp_path):
    """A pilot database under archive/ (six parameters, single-prompt and
    Gaussian protocols, pre-restructure columns) opens without a migration
    error: connect_copy never writes the file, connect() on a copy adds the
    new columns, and the scenarios, protocols and elicitations read back.
    Its runs are not replayable by the current model (no C_build, C_run,
    n), so complete_fits is empty and that is all."""
    src = ARCHIVE / "pilots" / "ai-safety-evals" / "voi.db"
    before = src.read_bytes()
    con = db.connect_copy(src)   # the archived file itself, read-only
    assert src.read_bytes() == before
    scen = db.get_scenarios(con)
    assert len(scen) == 15 and {r["grp"] for r in scen} == {"AI safety eval", "robot safety eval"}
    assert all(r["context"] and r["decision_context"] is None and r["sources"] is None for r in scen)
    prots = {r["name"]: r for r in con.execute("SELECT * FROM protocols ORDER BY id")}
    assert {"p001", "p003", "g001"} <= set(prots)
    assert prots["g001"]["model_kind"] == "gaussian" and db.protocol_stages(prots["p003"]) is None
    assert db.protocol_members(prots["p003"]) == [
        {"provider": "claude_cli", "model": m, "k_repeats": 5} for m in ("haiku", "sonnet", "opus")]
    assert db.protocol_template_vars(prots["p003"]) == {}
    n_elic = con.execute("SELECT COUNT(*) FROM elicitations WHERE valid=1").fetchone()[0]
    assert n_elic > 100
    names = {r[0] for r in con.execute("SELECT DISTINCT name FROM parameters")}
    assert {"p", "s", "t", "B", "K", "C"} <= names and "C_build" not in names
    fits = db.scenario_param_fits(con, prots["p003"]["id"], names=["p", "s", "t", "B", "K"])
    assert len(fits) == 15 and all(len(fits[s]["p"]) >= 10 for s in fits)
    assert mc.complete_fits(con, prots["p003"]["id"]) == {}   # no C_build, C_run, n in an archived DB
    assert db.latest_run(con, "p003")["data_hash"]
    con.close()
    # a writable copy migrates in place and stays consistent
    dst = tmp_path / "pilot.db"
    shutil.copy(src, dst)
    con = db.connect(dst)
    cols = {r[1] for r in con.execute("PRAGMA table_info(scenarios)")}
    assert {"decision_context", "instrument_context", "sources"} <= cols
    assert db.migrate(con) == []
    assert con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0] >= n_elic
    con.close()
    assert src.read_bytes() == before


def test_archived_study_is_refused_by_connect_and_mc(tmp_path, monkeypatch):
    """DESIGN section 9: never write to a database under archive/. On a copy
    of a pilot study placed under <root>/archive/ (the repo root redirected
    to tmp_path, so the committed file is never touched), Study.connect and
    mc.main (whose first act is to connect, which would migrate the file in
    place) exit before writing; connect_copy still reads it."""
    src = ARCHIVE / "pilots" / "sim2real" / "voi.db"
    root = tmp_path.resolve()
    study_dir = root / "archive" / "pilots" / "sim2real"
    study_dir.mkdir(parents=True)
    shutil.copy(src, study_dir / "voi.db")
    before = (study_dir / "voi.db").read_bytes()
    monkeypatch.setattr(db, "ROOT", root)
    study = Study.resolve(study_dir)
    assert study.archived
    with pytest.raises(SystemExit, match="archived study .*read-only"):
        mc.main(["--study", str(study_dir), "--protocol", "p004", "--allow-dirty"])
    with pytest.raises(SystemExit, match="archived study"):
        study.connect()
    assert (study_dir / "voi.db").read_bytes() == before
    ro = sqlite3.connect(f"file:{study_dir / 'voi.db'}?mode=ro", uri=True)
    cols = {r[1] for r in ro.execute("PRAGMA table_info(scenarios)")}
    ro.close()
    assert "decision_context" not in cols   # the archived schema, not migrated
    con = study.connect_copy()   # reading stays allowed
    assert db.protocol_by_name(con, "p004")["name"] == "p004"
    con.close()
    assert (study_dir / "voi.db").read_bytes() == before
    # a study elsewhere under the same root is not archived
    other = root / "studies" / "x"
    other.mkdir(parents=True)
    assert not Study.resolve(other).archived
    Study.resolve(other).connect().close()
    assert (other / "voi.db").exists()


def test_unique_index_on_valid_slots(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "ux_elicitations_valid_slot_stage" in names and "ux_elicitations_valid_slot" not in names
    db.insert_elicitation(con, 1, 1, "claude_cli", "haiku", 0, "h", "{}", False, "json: x")
    db.insert_elicitation(con, 1, 1, "claude_cli", "haiku", 0, "h", "{}", False, "json: y")
    db.insert_elicitation(con, 1, 1, "claude_cli", "haiku", 0, "h", "{}", True, None)
    con.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_elicitation(con, 1, 1, "claude_cli", "haiku", 0, "h", "{}", True, None)
    con.rollback()
    # another member or repeat of the same scenario is a different slot
    db.insert_elicitation(con, 1, 1, "openrouter", "haiku", 0, "h", "{}", True, None)
    db.insert_elicitation(con, 1, 1, "claude_cli", "haiku", 1, "h", "{}", True, None)
    con.commit()
    # the v1 migration path creates the index after adding the v2 columns
    v1 = tmp_path / "v1.db"
    make_v1_db(v1)
    con1 = db.connect(v1)
    assert con1.execute("SELECT 1 FROM sqlite_master WHERE name='ux_elicitations_valid_slot_stage'")\
        .fetchone()


def test_protocol_scenario_selector_is_stored_and_immutable(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    members = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]
    p = write_protocol(tmp_path, "pS", "T $title", members=members, extra={"scenarios": [3, 1, 3]})
    pid = db.get_or_create_protocol(con, p, tmp_path)
    assert db.protocol_selector(db.protocol_by_name(con, "pS")) == "1,3"
    assert db.get_or_create_protocol(con, p, tmp_path) == pid
    write_protocol(tmp_path, "pS", "T $title", members=members, extra={"scenarios": "1,2,3"})
    with pytest.raises(RuntimeError, match="scenarios"):
        db.get_or_create_protocol(con, p, tmp_path)
    q = write_protocol(tmp_path, "pA", "T $title", members=members)
    db.get_or_create_protocol(con, q, tmp_path)
    assert db.protocol_selector(db.protocol_by_name(con, "pA")) == "all"
    assert db.normalize_selector(None) == "all"
    assert db.normalize_selector("seed") == "seed"
    assert db.normalize_selector(" 2, 1 ") == "1,2"
    with pytest.raises(ValueError):
        db.normalize_selector("")


def test_seed_refresh_until_elicited(tmp_path, capsys):
    con = db.connect(tmp_path / "voi.db")
    scen = tmp_path / "scenarios.json"
    base = [{"title": "A", "agent": "a", "decision": "d", "theta_definition": "t",
             "instrument": "i", "context": "c1", "group": "g", "attributes": {"level": 1},
             "domain_tags": ["x"]}]
    scen.write_text(json.dumps(base))
    assert db.seed_scenarios(con, scen) == 1
    assert db.seed_scenarios(con, scen) == 0 and "refreshed" not in capsys.readouterr().out
    base[0]["context"] = "c2"
    base[0]["attributes"] = {"level": 2}
    scen.write_text(json.dumps(base))
    assert db.seed_scenarios(con, scen) == 0
    assert "refreshed ['context', 'attributes', 'raw_json']" in capsys.readouterr().out
    row = db.get_scenarios(con, "seed")[0]
    assert row["context"] == "c2" and db.scenario_attributes(row) == {"level": 2}
    assert json.loads(row["raw_json"])["context"] == "c2"
    # key order in the file is not a change
    scen.write_text(json.dumps([dict(reversed(list(base[0].items())))]))
    db.seed_scenarios(con, scen)
    assert "refreshed" not in capsys.readouterr().out
    # once elicited the row is frozen and a differing file is an error
    db.insert_elicitation(con, row["id"], 1, "claude_cli", "haiku", 0, "h", "{}", False, "json: x")
    con.commit()
    base[0]["agent"] = "someone else"
    scen.write_text(json.dumps(base))
    with pytest.raises(RuntimeError, match="frozen"):
        db.seed_scenarios(con, scen)
    assert db.get_scenarios(con, "seed")[0]["agent"] == "a"


def test_seed_retires_rows_whose_title_left_the_file_and_restores_them(tmp_path, capsys):
    con = db.connect(tmp_path / "voi.db")
    scen = tmp_path / "scenarios.json"
    base = [{"title": t, "agent": "a", "decision": "d", "theta_definition": "t", "instrument": "i"}
            for t in ("A", "B")]
    scen.write_text(json.dumps(base))
    assert db.seed_scenarios(con, scen) == 2
    db.insert_elicitation(con, 2, 1, "claude_cli", "haiku", 0, "h", "{}", True, None)
    con.commit()
    # the README's fix for a frozen scenario: a new title makes a new row; the
    # old row is retired (kept with its elicitation), not selected any more
    base[1]["title"] = "B renamed"
    scen.write_text(json.dumps(base))
    assert db.seed_scenarios(con, scen) == 1
    out = capsys.readouterr().out
    assert "scenario 2 'B': retired (title no longer in scenarios.json" in out
    assert [r["id"] for r in db.get_scenarios(con, "all")] == [1, 3]
    assert [r["id"] for r in db.get_scenarios(con, "seed")] == [1, 3]
    assert [r["id"] for r in db.get_scenarios(con, "2,3")] == [2, 3]   # explicit ids: as named
    row = con.execute("SELECT * FROM scenarios WHERE id=2").fetchone()
    assert row["source"] == db.RETIRED_SOURCE and row["title"] == "B"
    assert con.execute("SELECT COUNT(*) FROM elicitations WHERE scenario_id=2").fetchone()[0] == 1
    assert db.seed_scenarios(con, scen) == 0 and "retired" not in capsys.readouterr().out
    # the title comes back: the same row is restored, no duplicate is inserted
    base.append({"title": "B", "agent": "a", "decision": "d", "theta_definition": "t", "instrument": "i"})
    scen.write_text(json.dumps(base))
    assert db.seed_scenarios(con, scen) == 0
    assert "scenario 2 'B': restored" in capsys.readouterr().out
    assert [r["id"] for r in db.get_scenarios(con, "seed")] == [1, 2, 3]
    assert con.execute("SELECT COUNT(*) FROM scenarios WHERE title='B'").fetchone()[0] == 1
    # dry-run tense: the copy is changed, the words say what the real run would do
    base.pop()
    scen.write_text(json.dumps(base))
    db.seed_scenarios(con, scen, dry_run=True)
    assert "scenario 2 'B': would be retired" in capsys.readouterr().out


def test_elicited_p50s_first_n_counts_valid_repeats_not_indices(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    sid = db.insert_scenario(con, {"title": "S", "agent": "a", "decision": "d",
                                   "theta_definition": "t", "instrument": "i"}, "seed")
    for rix in (0, 2, 3, 4):
        _store(con, sid, 1, "claude_cli", "haiku", rix, db.PARAM_NAMES)
    db.insert_elicitation(con, sid, 1, "claude_cli", "haiku", 1, "h", "{}", False, "json: x")
    _store(con, sid, 1, "openrouter", "m", 0, db.PARAM_NAMES)
    con.commit()
    con.execute("UPDATE parameters SET p50=p50 * (1 + (SELECT repeat_ix FROM elicitations e"
                " WHERE e.id=parameters.elicitation_id)) WHERE name='C_run'")
    con.commit()
    # repeat 1 is invalid: 'first 3' is repeats 0, 2, 3 (a count), not repeat_ix <= 2
    assert db.elicited_p50s(con, 1, sid, "C_run", "claude_cli", "haiku", first=3) == [100.0, 300.0, 400.0]
    assert db.elicited_p50s(con, 1, sid, "C_run", "claude_cli", "haiku") == [100.0, 300.0, 400.0, 500.0]
    assert db.elicited_p50s(con, 1, sid, "C_run", "claude_cli", "haiku", first=9) == \
        [100.0, 300.0, 400.0, 500.0]
    # over every member the cap applies per member
    assert db.elicited_p50s(con, 1, sid, "C_run", first=1) == [100.0, 100.0]
