"""DB migration from the v1 schema, protocol member handling and immutability,
seeding idempotence, and the pooling of fits over members."""

import json
import shutil
import sqlite3
from pathlib import Path

import pytest
import yaml

from voi_rank import db
from voi_rank.fit import fit_param

BUSINESS = Path(__file__).resolve().parent.parent / "archive" / "business"
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
    assert {"context", "grp", "attributes"} <= cols["scenarios"]
    assert {"provider", "model"} <= cols["elicitations"]
    assert "members_json" in cols["protocols"]
    row = con.execute("SELECT provider, model FROM elicitations").fetchone()
    assert (row["provider"], row["model"]) == ("claude_cli", "haiku")
    # legacy protocol row converts to a single claude_cli member
    prot = con.execute("SELECT * FROM protocols").fetchone()
    assert db.protocol_members(prot) == [{"provider": "claude_cli", "model": "haiku",
                                         "k_repeats": 3}]
    # idempotent
    assert db.migrate(con) == []


def write_protocol(study, name, template_text, members=None, legacy=None, extra=None):
    (study / "templates").mkdir(exist_ok=True)
    (study / "protocols").mkdir(exist_ok=True)
    (study / "templates" / f"{name}.md").write_text(template_text)
    cfg = {"name": name, "template_path": f"templates/{name}.md", "notes": ""}
    if members is not None:
        cfg["members"] = members
    else:
        cfg.update(legacy)
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


def test_legacy_yaml_matches_migrated_row_and_relocated_template(tmp_path):
    """A v1 DB row (model_alias/k_repeats, old template_path) accepts the v2
    YAML of the same protocol as long as the template content is unchanged."""
    path = tmp_path / "voi.db"
    make_v1_db(path)
    text = "template body $title"
    p = write_protocol(tmp_path, "p001", text, legacy={"model_alias": "haiku", "k_repeats": 3})
    con = db.connect(path)
    con.execute("UPDATE protocols SET template_hash=? WHERE name='p001'", (db.sha256(text),))
    con.commit()
    pid = db.get_or_create_protocol(con, p, tmp_path)
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (pid,)).fetchone()
    assert prot["template_path"] == "templates/p001.md"
    # k change under the legacy schema is a member change: refused
    write_protocol(tmp_path, "p001", text, legacy={"model_alias": "haiku", "k_repeats": 5})
    with pytest.raises(RuntimeError, match="members"):
        db.get_or_create_protocol(con, p, tmp_path)


def test_seed_scenarios_idempotent_with_v2_fields(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    scen = tmp_path / "scenarios.json"
    scen.write_text(json.dumps([{
        "title": "A", "agent": "a", "decision": "d", "theta_definition": "t",
        "instrument": "i", "context": "facts", "domain_tags": ["x"], "group": "g1",
        "attributes": {"level": 2, "keys": ["k"]}, "manual": {"p": {}},
    }, {"title": "B", "agent": "a", "decision": "d", "theta_definition": "t", "instrument": "i"}]))
    assert db.seed_scenarios(con, scen) == 2
    assert db.seed_scenarios(con, scen) == 0
    rows = db.get_scenarios(con, "seed")
    assert len(rows) == 2
    a = rows[0]
    assert a["context"] == "facts" and a["grp"] == "g1"
    assert db.scenario_attributes(a) == {"level": 2, "keys": ["k"]}
    assert "manual" not in json.loads(a["raw_json"])
    b = rows[1]
    assert b["context"] is None and b["grp"] is None and db.scenario_attributes(b) == {}


def _store(con, sid, pid, provider, model, rix, names):
    eid = db.insert_elicitation(con, sid, pid, provider, model, rix, "h", "{}", True, None)
    for n in names:
        q = (0.1, 0.3, 0.6) if n in ("p", "s", "t", "e") else (10.0, 100.0, 1000.0)
        fam = "beta" if n in ("p", "s", "t", "e") else "lognormal"
        fit = fit_param(n if n != "e" else "p", *q)
        fit.family = fam
        db.insert_parameter(con, eid, n, *q, "u", "r", fit)
    con.commit()


def test_scenario_param_fits_pools_members_and_ignores_e(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    sid = db.insert_scenario(con, {"title": "S", "agent": "a", "decision": "d",
                                   "theta_definition": "t", "instrument": "i"}, "seed")
    _store(con, sid, 1, "claude_cli", "haiku", 0, db.PARAM_NAMES + ["e"])
    _store(con, sid, 1, "claude_cli", "haiku", 1, db.PARAM_NAMES + ["e"])
    _store(con, sid, 1, "openrouter", "m", 0, db.PARAM_NAMES)
    fits = db.scenario_param_fits(con, 1)
    assert set(fits[sid]) == set(db.PARAM_NAMES)
    assert len(fits[sid]["p"]) == 3
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


def test_manual_protocol_hashes_only_the_hand_percentiles(tmp_path):
    con = db.connect(tmp_path / "voi.db")
    (tmp_path / "protocols").mkdir()
    p = tmp_path / "protocols" / "p000_manual.yaml"
    p.write_text(yaml.safe_dump({"name": "p000_manual", "template_path": "scenarios.json",
                                 "model_alias": "manual", "k_repeats": 1}))
    manual = json.loads((BUSINESS / "scenarios.json").read_text())[0]["manual"]
    base = [{"title": "A", "agent": "a", "decision": "d", "theta_definition": "t",
             "instrument": "i", "manual": manual},
            {"title": "B", "agent": "a", "decision": "d", "theta_definition": "t", "instrument": "i"}]
    scen = tmp_path / "scenarios.json"
    scen.write_text(json.dumps(base))
    db.seed_scenarios(con, scen)
    pid = db.get_or_create_protocol(con, p, tmp_path)
    stored = db.protocol_by_name(con, "p000_manual")["template_hash"]
    assert stored == db.manual_hash(scen) != db.sha256(scen.read_text())
    # a metadata refresh of an un-elicited scenario leaves the manual hash
    # alone, so --manual still registers the same protocol
    base[1]["context"] = "new facts"
    scen.write_text(json.dumps(base))
    db.seed_scenarios(con, scen)
    assert db.get_or_create_protocol(con, p, tmp_path) == pid
    # the stored hash is a registration snapshot, not part of the immutability
    # check: the hand percentiles are frozen per scenario by elicit.run_manual
    # (tests/test_pipeline.py), so a changed or added manual block still
    # registers the same protocol row with its original snapshot
    base[0]["manual"]["C"]["p50"] *= 2
    base[1]["manual"] = manual
    scen.write_text(json.dumps(base))
    assert db.get_or_create_protocol(con, p, tmp_path) == pid
    assert db.protocol_by_name(con, "p000_manual")["template_hash"] == stored != db.manual_hash(scen)
    # the reserved name may not carry a callable member
    p.write_text(yaml.safe_dump({"name": "p000_manual", "template_path": "scenarios.json",
                                 "members": [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]}))
    with pytest.raises(RuntimeError, match="reserved for hand percentiles"):
        db.get_or_create_protocol(con, p, tmp_path)
    # a callable-provider protocol still hashes the whole template file
    members = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]
    q = write_protocol(tmp_path, "pT", "T $title", members=members)
    db.get_or_create_protocol(con, q, tmp_path)
    assert db.protocol_by_name(con, "pT")["template_hash"] == db.sha256("T $title")


def test_migrate_moves_the_business_manual_row_to_the_manual_hash(tmp_path):
    path = tmp_path / "v1.db"
    make_v1_db(path)
    con = sqlite3.connect(path)
    con.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats)"
                " VALUES ('p000_manual', 'scenarios.json', ?, 'manual', 1)", (db.BUSINESS_MANUAL_FILE_HASH,))
    con.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats)"
                " VALUES ('p000_manual', 'scenarios.json', 'other', 'manual', 1)")
    con.commit()
    con.close()
    con = db.connect(path)
    hashes = [r[0] for r in con.execute("SELECT template_hash FROM protocols WHERE name='p000_manual'"
                                        " ORDER BY id")]
    assert hashes == [db.BUSINESS_MANUAL_HASH, "other"]
    assert db.manual_hash(BUSINESS / "scenarios.json") == db.BUSINESS_MANUAL_HASH


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
    # the legacy manual alias maps to the manual provider, never claude_cli
    assert db.normalize_members({"model_alias": "manual", "k_repeats": 1}) == \
        [{"provider": "manual", "model": "manual", "k_repeats": 1}]


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


def test_business_db_copy_opens_migrates_and_registers_protocols(tmp_path):
    dst = tmp_path / "biz.db"
    shutil.copy(BUSINESS / "voi.db", dst)
    con = db.connect(dst)
    assert con.execute("SELECT 1 FROM sqlite_master WHERE name='ux_elicitations_valid_slot_stage'").fetchone()
    manual = db.protocol_by_name(con, "p000_manual")
    assert db.protocol_members(manual) == [{"provider": "manual", "model": "manual", "k_repeats": 1}]
    assert {r[0] for r in con.execute("SELECT DISTINCT provider FROM elicitations WHERE protocol_id=?",
                                      (manual["id"],))} == {"manual"}
    p004 = db.protocol_by_name(con, "p004")
    assert db.protocol_selector(p004) == db.BUSINESS_P004_SELECTOR
    elicited = {r[0] for r in con.execute(
        "SELECT DISTINCT scenario_id FROM elicitations WHERE protocol_id=? AND valid=1", (p004["id"],))}
    assert {int(x) for x in db.BUSINESS_P004_SELECTOR.split(",")} == elicited
    assert db.protocol_selector(db.protocol_by_name(con, "p001")) == "all"
    # the committed protocol files still pass the immutability check against the migrated rows
    for name in ("p000_manual", "p001", "p002", "p003", "p004"):
        assert db.get_or_create_protocol(con, BUSINESS / "protocols" / f"{name}.yaml", BUSINESS) \
            == db.protocol_by_name(con, name)["id"]
    assert db.protocol_by_name(con, "p000_manual")["template_hash"] == db.BUSINESS_MANUAL_HASH
    assert "data_hash" in {r[1] for r in con.execute("PRAGMA table_info(runs)")}
    assert db.migrate(con) == []


def test_migrate_backfills_only_the_business_p004(tmp_path):
    path = tmp_path / "v1.db"
    make_v1_db(path)
    con = sqlite3.connect(path)
    con.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats)"
                " VALUES ('p004', 'x', ?, 'haiku', 3)", (db.BUSINESS_P004_HASH,))
    con.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats)"
                " VALUES ('p000_manual', 'scenarios.json', 'h', 'manual', 1)")
    con.execute("INSERT INTO elicitations (scenario_id, protocol_id, repeat_ix, valid)"
                " VALUES (1, 3, 0, 1)")
    con.commit()
    con.close()
    con = db.connect(path)
    sel = {r["name"]: r["scenario_selector"] for r in con.execute("SELECT * FROM protocols")}
    assert sel == {"p001": None, "p004": db.BUSINESS_P004_SELECTOR, "p000_manual": None}
    rows = {r["protocol_id"]: (r["provider"], r["model"]) for r in
            con.execute("SELECT * FROM elicitations")}
    assert rows == {1: ("claude_cli", "haiku"), 3: ("manual", "manual")}
    # a p004 of another study (different template) is left alone
    other = tmp_path / "other.db"
    make_v1_db(other)
    c2 = sqlite3.connect(other)
    c2.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats)"
               " VALUES ('p004', 'x', 'otherhash', 'haiku', 3)")
    c2.commit()
    c2.close()
    c2 = db.connect(other)
    assert db.protocol_by_name(c2, "p004")["scenario_selector"] is None


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
    base[0]["manual"] = {"p": {}}
    scen.write_text(json.dumps(base))
    assert db.seed_scenarios(con, scen) == 0
    assert "refreshed ['context', 'attributes', 'raw_json']" in capsys.readouterr().out
    row = db.get_scenarios(con, "seed")[0]
    assert row["context"] == "c2" and db.scenario_attributes(row) == {"level": 2}
    assert json.loads(row["raw_json"])["context"] == "c2"
    assert "manual" not in json.loads(row["raw_json"])
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


# --- review fixes, round 4 ---------------------------------------------------

def test_migrate_retags_only_legacy_shaped_manual_rows(tmp_path):
    """The provider='manual' backfill is keyed on the legacy row shape
    (model_alias 'manual', no members_json), never on the protocol NAME: a v2
    row named p000_manual with a callable member keeps its rows, so a resume
    still sees them."""
    path = tmp_path / "voi.db"
    con = db.connect(path)
    con.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats,"
                " members_json) VALUES ('p000_manual', 't', 'h', 'claude_cli:haiku', 1, ?)",
                (db.members_json([{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]),))
    con.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats)"
                " VALUES ('pM', 'scenarios.json', 'h', 'manual', 1)")   # legacy shape, other name
    db.insert_elicitation(con, 1, 1, "claude_cli", "haiku", 0, "h", "{}", True, None)
    db.insert_elicitation(con, 1, 2, "claude_cli", "manual", 0, "h", "{}", True, None)
    con.commit()
    con.close()
    con = db.connect(path)
    rows = {r["protocol_id"]: r["provider"] for r in con.execute("SELECT * FROM elicitations")}
    assert rows == {1: "claude_cli", 2: "manual"}
    assert db.valid_repeats(con, 1, 1, "claude_cli", "haiku") == {0}


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
                " WHERE e.id=parameters.elicitation_id)) WHERE name='C'")
    con.commit()
    # repeat 1 is invalid: 'first 3' is repeats 0, 2, 3 (a count), not repeat_ix <= 2
    assert db.elicited_p50s(con, 1, sid, "C", "claude_cli", "haiku", first=3) == [100.0, 300.0, 400.0]
    assert db.elicited_p50s(con, 1, sid, "C", "claude_cli", "haiku") == [100.0, 300.0, 400.0, 500.0]
    assert db.elicited_p50s(con, 1, sid, "C", "claude_cli", "haiku", first=9) == [100.0, 300.0, 400.0, 500.0]
    # over every member the cap applies per member
    assert db.elicited_p50s(con, 1, sid, "C", first=1) == [100.0, 100.0]
