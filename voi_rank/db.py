"""SQLite storage (spec §5). One file per study, voi.db. Append-only for
scenarios and elicitations: elicited data is never UPDATEd, only superseded by
new rows under a new protocol.

v2 additions: scenarios.context/grp/attributes, elicitations.provider/model,
protocols.members_json/scenario_selector, runs.data_hash, a unique index on
valid slots. connect() migrates pre-v2 databases in place; connect_copy()
prepares an in-memory copy for dry runs.

Provenance of a run: code_hash is the git HEAD of the CODE_PATHS (suffixed
'-dirty' when any of them has uncommitted changes; study inputs are frozen
separately by protocols.template_hash and elicitations.prompt_hash, so a
modified voi.db never dirties the code hash) and data_hash is a digest of
the valid elicitations that fed the run (see mc.data_hash).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import yaml

from voi_rank.fit import GAUSS_PARAM_NAMES, GAUSS_SPREAD_SCALE, PARAM_NAMES
from voi_rank.sensitivity import repeat_spread

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

__all__ = ["GAUSS_PARAM_NAMES", "PARAM_NAMES", "ROOT", "connect"]

# columns added after v1; (table -> {column: type}) checked on every connect
V2_COLUMNS = {
    "scenarios": {"context": "TEXT", "grp": "TEXT", "attributes": "TEXT"},
    "elicitations": {"provider": "TEXT", "model": "TEXT"},
    "protocols": {"members_json": "TEXT", "scenario_selector": "TEXT", "model_kind": "TEXT"},
    "runs": {"data_hash": "TEXT"},
}
# protocol model kinds (v2.1): the binary model of spec §2 (parameters
# PARAM_NAMES, primary metric 'efficiency') and the Gaussian-state family
# (GAUSS_PARAM_NAMES, primary metric 'eff_step'). A protocol row without a
# model_kind (registered before the column) is binary.
BINARY_KIND = "binary"
GAUSSIAN_KIND = "gaussian"
MODEL_KINDS = (BINARY_KIND, GAUSSIAN_KIND)
_PRIMARY_METRIC = {BINARY_KIND: "efficiency", GAUSSIAN_KIND: "eff_step"}
_EVSI_METRIC = {BINARY_KIND: "EVSI", GAUSSIAN_KIND: "EVSI_step"}
_PARAM_NAMES = {BINARY_KIND: PARAM_NAMES, GAUSSIAN_KIND: GAUSS_PARAM_NAMES}


def normalize_model_kind(value) -> str:
    kind = BINARY_KIND if value is None else str(value).strip().lower()
    if kind not in MODEL_KINDS:
        raise ValueError(f"unknown protocol model {value!r}; known: {list(MODEL_KINDS)}")
    return kind


def param_names(kind: str) -> list[str]:
    """The parameter rows a protocol of this model kind stores per elicitation."""
    return _PARAM_NAMES[normalize_model_kind(kind)]


def primary_metric(kind: str) -> str:
    """The stored efficiency metric a run of this kind ranks by."""
    return _PRIMARY_METRIC[normalize_model_kind(kind)]


def evsi_metric(kind: str) -> str:
    """The stored EVSI metric behind primary_metric (p_positive = P(EVSI > C))."""
    return _EVSI_METRIC[normalize_model_kind(kind)]


# paths whose uncommitted changes make a run's code_hash '-dirty'
CODE_PATHS = ("voi_rank", "pyproject.toml", "uv.lock")
LEGACY_PROVIDER = "claude_cli"
# a seed row whose title left scenarios.json: kept (rows are never deleted),
# left out of the 'all' / 'seed' selections, restored when the title returns
RETIRED_SOURCE = "seed:retired"
# git_state's HEAD when git is unavailable or the tree is not a repository
UNKNOWN_HEAD = "unknown"
# hand-entered percentiles: a member label, never a callable provider
MANUAL_PROVIDER = "manual"
MANUAL_PROTOCOL = "p000_manual"
# the business study's p004 was elicited on 17 scenarios before protocols
# carried a scenario selector; its stored row is backfilled once, keyed on the
# frozen template hash so no other study's p004 is touched
BUSINESS_P004_HASH = "25c59b4f6b2afad4c9d50d5af135d99c96ff716b01bf66c7ee607ea0dd930d9e"
BUSINESS_P004_SELECTOR = "5,13,22,31,32,41,42,46,47,48,50,52,53,54,60,61,62"
# the business p000_manual row was registered with the hash of the whole
# scenarios.json; manual protocols now hash only the hand percentiles (so
# metadata edits to un-elicited scenarios do not break --manual). Migrated
# once, keyed on the name AND the old value so nothing else is touched.
BUSINESS_MANUAL_FILE_HASH = "b95b4ac8347981f132af3e2199ac82eacaadde9e09785201eac3cb34c67dee85"
BUSINESS_MANUAL_HASH = "97f35c5b4b31d9d70db088e23919ec6d8ce9c2592bdd40970433e41a2ec745a7"
SCHEMA_INDEX_MARKER = "-- indexes"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def git_state(cwd: str | Path = ROOT) -> tuple[str, list[str]]:
    """(HEAD commit hash, porcelain status lines of CODE_PATHS with
    uncommitted or untracked changes). The status is code-scoped on purpose:
    a study's voi.db and report are rewritten by every migration and run and
    are frozen by their own hashes. Untracked files are listed one by one
    regardless of the user's status.showUntrackedFiles setting, so a new
    uncommitted module under voi_rank/ never passes as clean. ('unknown', [])
    without git."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd,
                              capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--",
                                 *CODE_PATHS], cwd=cwd,
                                capture_output=True, text=True, check=True).stdout
    except Exception:
        return UNKNOWN_HEAD, []
    return head, [line for line in status.splitlines() if line.strip()]


def git_hash(cwd: str | Path = ROOT) -> str:
    """HEAD commit hash, suffixed '-dirty' when a CODE_PATHS entry has
    uncommitted changes, so a stored code_hash never claims a clean commit
    the code did not match."""
    head, dirty = git_state(cwd)
    return f"{head}-dirty" if dirty else head


def is_dirty_hash(code_hash: str | None) -> bool:
    return bool(code_hash) and code_hash.endswith("-dirty")


def claude_cli_version() -> str:
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _prepare(con: sqlite3.Connection) -> sqlite3.Connection:
    """Create missing tables, migrate pre-v2 columns, then create the indexes
    (which reference v2 columns, so they must come after the migration)."""
    con.row_factory = sqlite3.Row
    tables, _, indexes = SCHEMA_PATH.read_text().partition(SCHEMA_INDEX_MARKER)
    con.executescript(tables)
    migrate(con)
    check_duplicate_valid_slots(con)
    con.executescript(indexes)
    return con


def duplicate_valid_slots(con) -> list[sqlite3.Row]:
    """Slots (scenario, protocol, member, repeat) holding more than one valid
    elicitation: possible only in databases written before the unique index."""
    return con.execute(
        "SELECT scenario_id, protocol_id, provider, model, repeat_ix, COUNT(*) AS n,"
        " GROUP_CONCAT(id) AS ids FROM elicitations WHERE valid=1"
        " GROUP BY scenario_id, protocol_id, provider, model, repeat_ix HAVING COUNT(*) > 1"
        " ORDER BY scenario_id, protocol_id, provider, model, repeat_ix").fetchall()


DUPLICATE_SLOT_REPAIR_SQL = (
    "UPDATE elicitations SET valid=0, error='duplicate slot' WHERE valid=1 AND id NOT IN"
    " (SELECT MIN(id) FROM elicitations WHERE valid=1"
    " GROUP BY scenario_id, protocol_id, provider, model, repeat_ix);")


def check_duplicate_valid_slots(con) -> None:
    """Refuse to create the unique valid-slot index over duplicates: the
    error lists every duplicate slot and the SQL that keeps the lowest id
    valid and marks the rest invalid (rows are never deleted)."""
    dups = duplicate_valid_slots(con)
    if not dups:
        return
    listing = "\n".join(
        f"  scenario {d['scenario_id']} protocol {d['protocol_id']} {d['provider']}:{d['model']}"
        f" repeat {d['repeat_ix']}: {d['n']} valid rows (ids {d['ids']})" for d in dups)
    raise RuntimeError(
        f"{len(dups)} slot(s) hold more than one valid elicitation, so the unique valid-slot"
        f" index cannot be created:\n{listing}\nrepair (keeps the lowest id per slot):\n"
        f"  {DUPLICATE_SLOT_REPAIR_SQL}")


def connect(db_path: str | Path) -> sqlite3.Connection:
    return _prepare(sqlite3.connect(db_path))


def connect_copy(db_path: str | Path) -> sqlite3.Connection:
    """An in-memory copy of a study database (empty when the file does not
    exist), prepared like connect(). The file is opened read-only and never
    created, written or migrated: this is what --dry-run works on."""
    mem = sqlite3.connect(":memory:")
    path = Path(db_path)
    if path.exists():
        src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            src.backup(mem)
        finally:
            src.close()
    return _prepare(mem)


def migrate(con) -> list[str]:
    """Add any v2 column missing from a pre-v2 database, then backfill (a) the
    member identity of legacy elicitations (single claude_cli member, model =
    the protocol's model_alias), (b) provider='manual' for rows under a
    LEGACY-SHAPED manual protocol (model_alias 'manual', no members_json: a
    v2 row is never re-tagged, whatever its name), (c) the business p004
    scenario selector and (d) the business p000_manual template hash (whole
    file -> hand percentiles only). Returns the columns added."""
    added = []
    for table, cols in V2_COLUMNS.items():
        have = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        for col, typ in cols.items():
            if col not in have:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
                added.append(f"{table}.{col}")
    con.execute("UPDATE elicitations SET provider=? WHERE provider IS NULL", (LEGACY_PROVIDER,))
    con.execute(
        "UPDATE elicitations SET model=(SELECT model_alias FROM protocols p"
        " WHERE p.id=elicitations.protocol_id) WHERE model IS NULL")
    con.execute(
        "UPDATE elicitations SET provider=? WHERE provider<>? AND protocol_id IN"
        " (SELECT id FROM protocols WHERE model_alias=? AND members_json IS NULL)",
        (MANUAL_PROVIDER, MANUAL_PROVIDER, MANUAL_PROVIDER))
    con.execute(
        "UPDATE protocols SET scenario_selector=? WHERE name='p004' AND template_hash=?"
        " AND scenario_selector IS NULL", (BUSINESS_P004_SELECTOR, BUSINESS_P004_HASH))
    con.execute("UPDATE protocols SET template_hash=? WHERE name=? AND template_hash=?",
                (BUSINESS_MANUAL_HASH, MANUAL_PROTOCOL, BUSINESS_MANUAL_FILE_HASH))
    con.commit()
    return added


# --- scenarios -------------------------------------------------------------

SCENARIO_TEXT_FIELDS = ("title", "agent", "decision", "theta_definition", "instrument")


def insert_scenario(con, sc: dict, source: str, commit: bool = True) -> int:
    """commit=False lets a caller land several scenarios in one transaction
    (the proposer inserts a domain's batch atomically)."""
    attrs = sc.get("attributes")
    cur = con.execute(
        "INSERT INTO scenarios (created_at, title, agent, decision, theta_definition,"
        " instrument, domain_tags, source, raw_json, context, grp, attributes)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (now_iso(), sc["title"], sc["agent"], sc["decision"], sc["theta_definition"],
         sc["instrument"], json.dumps(sc.get("domain_tags", [])), source, json.dumps(sc),
         sc.get("context"), sc.get("group"),
         json.dumps(attrs) if attrs is not None else None),
    )
    if commit:
        con.commit()
    return cur.lastrowid


# scenario columns refreshed from scenarios.json while a seed row has no
# elicitations yet (the title is the identity and is never refreshed)
SEED_MUTABLE = ("agent", "decision", "theta_definition", "instrument", "context",
                "grp", "attributes", "domain_tags", "raw_json")


def _seed_values(sc: dict) -> dict:
    """Column values a scenarios.json entry maps to (the 'manual' key, hand
    percentiles, is not part of the stored scenario)."""
    sc = {k: v for k, v in sc.items() if k != "manual"}
    attrs = sc.get("attributes")
    return {"agent": sc["agent"], "decision": sc["decision"],
            "theta_definition": sc["theta_definition"], "instrument": sc["instrument"],
            "context": sc.get("context"), "grp": sc.get("group"),
            "attributes": json.dumps(attrs) if attrs is not None else None,
            "domain_tags": json.dumps(sc.get("domain_tags", [])), "raw_json": json.dumps(sc)}


def _seed_diff(row, want: dict) -> list[str]:
    """Mutable columns whose stored value differs from scenarios.json (JSON
    columns compared as parsed values, so key order does not count)."""
    diff = []
    for col in SEED_MUTABLE:
        got = row[col]
        if col in ("attributes", "domain_tags", "raw_json"):
            same = (json.loads(got) if got is not None else None) == \
                   (json.loads(want[col]) if want[col] is not None else None)
        else:
            same = got == want[col]
        if not same:
            diff.append(col)
    return diff


def seed_scenarios(con, scenarios_json: Path, dry_run: bool = False) -> int:
    """Insert every scenario of a study's scenarios.json once (idempotent by
    (title, source='seed')). A seed row whose metadata differs from the file
    is refreshed in place while it has no elicitations; once elicited it is
    frozen and a differing file is an error (change the title to make a new
    scenario, or start a new DB). A seed row whose title is no longer in the
    file is retired (source RETIRED_SOURCE: kept with its elicitations, left
    out of the 'all' and 'seed' selections, so the README's rename never
    re-elicits the old row) and restored when the title returns. dry_run
    only changes the printed tense ('would refresh'): the caller's con is
    then an in-memory copy, and the refresh must still happen on it so the
    planned prompt hashes are right. Returns the number inserted."""
    verb = "would refresh" if dry_run else "refreshed"
    tense = "would be " if dry_run else ""
    n = 0
    seeds = json.loads(Path(scenarios_json).read_text())
    for sc in seeds:
        row = con.execute("SELECT * FROM scenarios WHERE title=? AND source IN ('seed', ?)",
                          (sc["title"], RETIRED_SOURCE)).fetchone()
        if row is None:
            insert_scenario(con, {k: v for k, v in sc.items() if k != "manual"}, source="seed")
            n += 1
            continue
        if row["source"] == RETIRED_SOURCE:
            con.execute("UPDATE scenarios SET source='seed' WHERE id=?", (row["id"],))
            con.commit()
            print(f"scenario {row['id']} {sc['title']!r}: {tense}restored"
                  " (its title is back in scenarios.json)")
        want = _seed_values(sc)
        diff = _seed_diff(row, want)
        if not diff:
            continue
        elicited = con.execute("SELECT COUNT(*) FROM elicitations WHERE scenario_id=?",
                               (row["id"],)).fetchone()[0]
        if elicited:
            raise RuntimeError(
                f"scenario {row['id']} {sc['title']!r} differs from scenarios.json in {diff}"
                f" but already has {elicited} elicitation(s): elicited scenarios are frozen."
                " Change the title to make it a new scenario, or start a new voi.db")
        con.execute(f"UPDATE scenarios SET {', '.join(f'{c}=?' for c in SEED_MUTABLE)} WHERE id=?",
                    [want[c] for c in SEED_MUTABLE] + [row["id"]])
        con.commit()
        print(f"scenario {row['id']} {sc['title']!r}: {verb} {diff} from scenarios.json")
    titles = {sc["title"] for sc in seeds}
    stale = [r for r in con.execute("SELECT id, title FROM scenarios WHERE source='seed' ORDER BY id")
             if r["title"] not in titles]
    for r in stale:
        con.execute("UPDATE scenarios SET source=? WHERE id=?", (RETIRED_SOURCE, r["id"]))
        print(f"scenario {r['id']} {r['title']!r}: {tense}retired (title no longer in"
              " scenarios.json; row and elicitations kept, left out of 'all' and 'seed')")
    if stale:
        con.commit()
    return n


def normalize_selector(value) -> str:
    """A protocol's scenario scope as stored: 'all' | 'seed' | sorted
    comma-joined ids. Accepts a YAML string or list of ints; None = 'all'."""
    if value is None:
        return "all"
    if isinstance(value, (list, tuple)):
        ids = [int(x) for x in value]
    else:
        text = str(value).strip()
        if text in ("all", "seed"):
            return text
        ids = [int(x) for x in text.split(",") if x.strip()]
    if not ids:
        raise ValueError(f"empty scenario selector {value!r}")
    return ",".join(str(i) for i in sorted(set(ids)))


def get_scenarios(con, selector: str = "all") -> list[sqlite3.Row]:
    """selector: 'all' | 'seed' | comma-separated ids. 'all' and 'seed' leave
    retired seed rows out; an explicit id list returns whatever it names."""
    if selector == "all":
        return con.execute("SELECT * FROM scenarios WHERE COALESCE(source, '')<>? ORDER BY id",
                           (RETIRED_SOURCE,)).fetchall()
    if selector == "seed":
        return con.execute("SELECT * FROM scenarios WHERE source='seed' ORDER BY id").fetchall()
    ids = [int(x) for x in selector.split(",")]
    marks = ",".join("?" * len(ids))
    return con.execute(f"SELECT * FROM scenarios WHERE id IN ({marks}) ORDER BY id", ids).fetchall()


def scenario_attributes(row) -> dict:
    try:
        return json.loads(row["attributes"]) or {}
    except (TypeError, ValueError, IndexError, KeyError):
        return {}


# --- protocols -------------------------------------------------------------

def normalize_members(cfg: dict) -> list[dict]:
    """Protocol members as [{provider, model, k_repeats}], from either the v2
    'members' list or the legacy 'model_alias' + 'k_repeats' pair (converted
    to a single claude_cli member)."""
    if "members" in cfg:
        members = []
        for m in cfg["members"]:
            members.append({"provider": str(m["provider"]), "model": str(m["model"]),
                            "k_repeats": int(m["k_repeats"])})
        if not members:
            raise ValueError("protocol has an empty members list")
        seen = set()
        for m in members:
            key = (m["provider"], m["model"])
            if key in seen:
                raise ValueError(f"protocol lists member {member_label(m)} more than once")
            seen.add(key)
        return members
    alias = str(cfg["model_alias"])
    provider = MANUAL_PROVIDER if alias == MANUAL_PROVIDER else LEGACY_PROVIDER
    return [{"provider": provider, "model": alias, "k_repeats": int(cfg["k_repeats"])}]


def members_json(members: list[dict]) -> str:
    return json.dumps(members, sort_keys=True)


def protocol_members(row) -> list[dict]:
    """Members of a stored protocol row (legacy rows without members_json are
    converted on the fly)."""
    if row["members_json"]:
        return json.loads(row["members_json"])
    return normalize_members({"model_alias": row["model_alias"], "k_repeats": row["k_repeats"]})


def member_label(m: dict) -> str:
    return f"{m['provider']}:{m['model']}"


def protocol_selector(row) -> str:
    """Scenario scope of a stored protocol row ('all' for rows registered
    before selectors existed)."""
    return row["scenario_selector"] or "all"


def protocol_model_kind(row) -> str:
    """Model kind of a stored protocol row ('binary' for rows registered
    before the column existed)."""
    return normalize_model_kind(row["model_kind"])


def run_model_kind(con, run) -> str:
    """Model kind of the protocol a run was made under."""
    prot = con.execute("SELECT model_kind FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    return protocol_model_kind(prot) if prot else BINARY_KIND


def manual_hash(scenarios_json: str | Path) -> str:
    """Template hash stored when a manual protocol is registered: the hand
    percentiles of scenarios.json ({title: manual}) at that moment. It is a
    snapshot, not part of the immutability check: the numbers are frozen per
    scenario by elicitations.prompt_hash / raw_response (elicit.run_manual
    refuses a loaded scenario whose numbers changed and loads new ones)."""
    seeds = json.loads(Path(scenarios_json).read_text())
    return sha256(json.dumps({sc["title"]: sc["manual"] for sc in seeds if "manual" in sc},
                             sort_keys=True))


def is_manual_protocol(members: list[dict]) -> bool:
    return all(m["provider"] == MANUAL_PROVIDER for m in members)


def get_or_create_protocol(con, yaml_path: str | Path, study_root: str | Path) -> int:
    """Register a protocol YAML (template_path relative to the study root).
    Protocol files are immutable: re-registering a name with a changed
    template hash, member list or scenario scope is an error (make a new
    protocol file). A manual protocol (every member provider 'manual'; the
    only name allowed to be one is MANUAL_PROTOCOL, and that name may be
    nothing else) has scenarios.json as template_path and stores manual_hash
    as a snapshot; its numbers are frozen per scenario, not per file, so new
    hand percentiles can be added later (see manual_hash)."""
    yaml_path = Path(yaml_path)
    cfg = yaml.safe_load(yaml_path.read_text())
    template_path = Path(study_root) / cfg["template_path"]
    members = normalize_members(cfg)
    manual = is_manual_protocol(members)
    kind = normalize_model_kind(cfg.get("model"))
    if cfg["name"] == MANUAL_PROTOCOL and not manual:
        raise RuntimeError(
            f"protocol {MANUAL_PROTOCOL} is reserved for hand percentiles (model_alias: manual);"
            f" its members {[member_label(m) for m in members]} include a callable provider")
    if manual and kind != BINARY_KIND:
        raise RuntimeError(f"protocol {cfg['name']}: hand percentiles are binary-model triples;"
                           f" model {kind!r} is not supported for a manual protocol")
    if manual:
        template_hash = manual_hash(template_path)
    else:
        template_hash = sha256(template_path.read_text())
    selector = normalize_selector(cfg.get("scenarios"))
    row = con.execute("SELECT * FROM protocols WHERE name=?", (cfg["name"],)).fetchone()
    if row:
        changed = [what for what, got, want in (
            ("template_hash", row["template_hash"], row["template_hash"] if manual else template_hash),
            ("members", members_json(protocol_members(row)), members_json(members)),
            ("scenarios", protocol_selector(row), selector),
            ("model", protocol_model_kind(row), kind),
        ) if got != want]
        if changed:
            raise RuntimeError(
                f"protocol {cfg['name']} already registered with different {changed}; "
                "create a new protocol file instead of editing an old one")
        if row["template_path"] != cfg["template_path"]:
            # same content, relocated file (v1 -> v2 study layout): keep the
            # row self-describing
            con.execute("UPDATE protocols SET template_path=? WHERE id=?",
                        (cfg["template_path"], row["id"]))
            con.commit()
        return row["id"]
    cur = con.execute(
        "INSERT INTO protocols (name, template_path, template_hash, model_alias,"
        " k_repeats, cli_version, notes, members_json, scenario_selector, model_kind)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (cfg["name"], cfg["template_path"], template_hash,
         ",".join(member_label(m) for m in members),
         sum(m["k_repeats"] for m in members),
         claude_cli_version(), cfg.get("notes", ""), members_json(members), selector, kind),
    )
    con.commit()
    return cur.lastrowid


def protocol_by_name(con, name: str) -> sqlite3.Row:
    row = con.execute("SELECT * FROM protocols WHERE name=?", (name,)).fetchone()
    if row is None:
        raise RuntimeError(f"protocol {name!r} not registered in DB")
    return row


# --- elicitations and parameters ------------------------------------------

def insert_elicitation(con, scenario_id: int, protocol_id: int, provider: str,
                       model: str, repeat_ix: int, prompt_hash: str,
                       raw_response: str, valid: bool, error: str | None) -> int:
    """No commit here: an elicitation row and its parameter rows must land in
    one transaction (the caller commits), so a crash cannot persist a valid
    row with a partial parameter set that resume logic would then skip."""
    cur = con.execute(
        "INSERT INTO elicitations (scenario_id, protocol_id, provider, model, repeat_ix,"
        " prompt_hash, raw_response, valid, error, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (scenario_id, protocol_id, provider, model, repeat_ix, prompt_hash,
         raw_response, int(valid), error, now_iso()),
    )
    return cur.lastrowid


def insert_parameter(con, elicitation_id: int, name: str, p5: float, p50: float,
                     p95: float, unit: str, reasoning: str, fit) -> int:
    """No commit here: see insert_elicitation."""
    cur = con.execute(
        "INSERT INTO parameters (elicitation_id, name, p5, p50, p95, unit, reasoning,"
        " dist_family, fit_params, fit_residual, fit_warning) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (elicitation_id, name, p5, p50, p95, unit, reasoning,
         fit.family, fit.params_json(), fit.residual, int(fit.warning)),
    )
    return cur.lastrowid


def valid_repeats(con, scenario_id: int, protocol_id: int, provider: str,
                  model: str) -> set[int]:
    """repeat_ix values already holding a valid elicitation for one slot
    family (scenario, protocol, member)."""
    return {r[0] for r in con.execute(
        "SELECT DISTINCT repeat_ix FROM elicitations WHERE scenario_id=? AND protocol_id=?"
        " AND provider=? AND model=? AND valid=1",
        (scenario_id, protocol_id, provider, model))}


def valid_raw_responses(con, scenario_id: int, protocol_id: int, provider: str,
                        model: str) -> list[str]:
    """raw_response of every valid elicitation of one slot family, in
    repeat_ix order (the manual loader compares the stored hand percentiles
    against the file's)."""
    return [r[0] for r in con.execute(
        "SELECT raw_response FROM elicitations WHERE scenario_id=? AND protocol_id=?"
        " AND provider=? AND model=? AND valid=1 ORDER BY repeat_ix, id",
        (scenario_id, protocol_id, provider, model))]


def scenario_param_fits(con, protocol_id: int,
                        names: list[str] | None = None) -> dict[int, dict[str, list[dict]]]:
    """{scenario_id: {param_name: [fit rows]}} over ALL valid elicitations of
    one protocol, every member and repeat pooled, in (provider, model,
    repeat_ix, elicitation_id) order. Only the protocol's parameter names
    (param_names of its model kind, or `names`) are returned (stored rows
    for the retired parameter e are ignored). Each fit row carries
    elicitation_id, provider, model, family, fit_params (the stored JSON
    string), params (parsed), p5/p50/p95."""
    if names is None:
        prot = con.execute("SELECT model_kind FROM protocols WHERE id=?", (protocol_id,)).fetchone()
        names = param_names(protocol_model_kind(prot) if prot else BINARY_KIND)
    rows = con.execute(
        "SELECT e.scenario_id, e.provider, e.model, e.repeat_ix, e.id AS elicitation_id,"
        " p.name, p.p5, p.p50, p.p95, p.dist_family, p.fit_params"
        " FROM elicitations e JOIN parameters p ON p.elicitation_id = e.id"
        " WHERE e.protocol_id=? AND e.valid=1"
        " ORDER BY e.scenario_id, e.provider, e.model, e.repeat_ix, e.id", (protocol_id,)).fetchall()
    out: dict[int, dict[str, list[dict]]] = {}
    for r in rows:
        if r["name"] not in names:
            continue
        out.setdefault(r["scenario_id"], {}).setdefault(r["name"], []).append({
            "elicitation_id": r["elicitation_id"],
            "provider": r["provider"], "model": r["model"],
            "family": r["dist_family"], "params": json.loads(r["fit_params"]),
            "fit_params": r["fit_params"],
            "p5": r["p5"], "p50": r["p50"], "p95": r["p95"],
        })
    return out


def elicited_p50s(con, protocol_id: int, scenario_id: int, name: str,
                  provider: str | None = None, model: str | None = None,
                  first: int | None = None) -> list[float]:
    """p50 of one parameter over the valid elicitations of one scenario under
    a protocol, optionally restricted to one member and/or to the first
    `first` VALID repeats of each member in repeat_ix order (a count, not an
    index cap: a member whose repeat 1 ended invalid still contributes its
    repeats 0, 2, 3 to 'first 3')."""
    sql = ("SELECT e.provider, e.model, p.p50 FROM parameters p"
           " JOIN elicitations e ON e.id=p.elicitation_id"
           " WHERE e.scenario_id=? AND e.protocol_id=? AND e.valid=1 AND p.name=?")
    args: list = [scenario_id, protocol_id, name]
    if provider is not None:
        sql += " AND e.provider=? AND e.model=?"
        args += [provider, model]
    sql += " ORDER BY e.provider, e.model, e.repeat_ix, e.id"
    rows = con.execute(sql, args).fetchall()
    if first is None:
        return [r[2] for r in rows]
    taken: dict[tuple, int] = {}
    out = []
    for prov, mod, p50 in rows:
        if taken.get((prov, mod), 0) < first:
            taken[(prov, mod)] = taken.get((prov, mod), 0) + 1
            out.append(p50)
    return out


def elicited_spread(con, protocol_id: int, scenario_id: int, name: str,
                    provider: str | None = None, model: str | None = None,
                    first: int | None = None) -> float | None:
    """Cross-repeat spread of one stored quantity of one scenario, the one
    statistic every noise table, figure and macro reports:
    sensitivity.repeat_spread over elicited_p50s, relative to the quantity's
    own pooled p50 except for the names in fit.GAUSS_SPREAD_SCALE (d and
    sigma_b / sigma0 as a plain max - min, mu0 divided by the pooled sigma0,
    all in prior-sd units). None with fewer than two repeats."""
    p50s = elicited_p50s(con, protocol_id, scenario_id, name, provider, model, first)
    if name not in GAUSS_SPREAD_SCALE:
        return repeat_spread(p50s)
    by = GAUSS_SPREAD_SCALE[name]
    if by is None:
        return repeat_spread(p50s, scale=1.0)
    ref = elicited_p50s(con, protocol_id, scenario_id, by, provider, model, first)
    if not ref:
        return None
    return repeat_spread(p50s, scale=abs(float(np.median(ref))))


def spread_label(name: str) -> str:
    """Suffix naming the spread statistic of a quantity where it is not the
    default relative one (tables, health, figures print it after the name)."""
    return " (max - min, sd units)" if name in GAUSS_SPREAD_SCALE else ""


def envelope_cost(raw: str) -> float:
    """USD cost recorded in a stored raw response: the claude CLI envelope's
    total_cost_usd, or an OpenRouter body's usage.cost. 0 when absent."""
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return 0.0
    if not isinstance(data, dict):
        return 0.0
    cost = data.get("total_cost_usd")
    if cost is None and isinstance(data.get("usage"), dict):
        cost = data["usage"].get("cost")
    try:
        return float(cost or 0.0)
    except (TypeError, ValueError):
        return 0.0


# --- runs, results, sensitivities ------------------------------------------

def insert_run(con, seed: int, n_draws: int, protocol_id: int, data_hash: str | None = None,
               code_hash: str | None = None) -> int:
    """No commit here: the runs row commits together with its results and
    sensitivities at the end of the MC run, so an interrupted run cannot
    become the (empty) latest run. code_hash defaults to git_hash()."""
    cur = con.execute(
        "INSERT INTO runs (created_at, seed, n_draws, code_hash, protocol_id, data_hash)"
        " VALUES (?,?,?,?,?,?)",
        (now_iso(), seed, n_draws, code_hash or git_hash(), protocol_id, data_hash))
    return cur.lastrowid


def insert_result(con, run_id: int, scenario_id: int, metric: str,
                  qs: dict, p_positive: float | None):
    con.execute(
        "INSERT INTO results (run_id, scenario_id, metric, q05, q25, q50, q75, q95,"
        " p_positive) VALUES (?,?,?,?,?,?,?,?,?)",
        (run_id, scenario_id, metric, qs.get(0.05), qs.get(0.25), qs.get(0.50),
         qs.get(0.75), qs.get(0.95), p_positive))


def insert_sensitivity(con, run_id: int, scenario_id: int, param: str,
                       rho: float | None):
    con.execute(
        "INSERT INTO sensitivities (run_id, scenario_id, param, spearman)"
        " VALUES (?,?,?,?)", (run_id, scenario_id, param, rho))


def latest_run(con, protocol_name: str | None = None) -> sqlite3.Row:
    if protocol_name:
        row = con.execute(
            "SELECT r.* FROM runs r JOIN protocols p ON p.id = r.protocol_id"
            " WHERE p.name=? ORDER BY r.id DESC LIMIT 1", (protocol_name,)).fetchone()
    else:
        row = con.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        raise RuntimeError("no runs in DB" + (f" under protocol {protocol_name!r}" if protocol_name else ""))
    return row


def get_run(con, run_id: int) -> sqlite3.Row:
    row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise RuntimeError(f"no run {run_id}")
    return row


def run_predates_v2(con, run) -> str | None:
    """Why a stored run cannot feed the v2 analyses (None when it can): it
    stores no data_hash (made before provenance was recorded) or its
    sensitivities carry the retired parameter e (made by the v1 model)."""
    if run["data_hash"] is None:
        return "it stores no data_hash"
    if con.execute("SELECT 1 FROM sensitivities WHERE run_id=? AND param='e' LIMIT 1",
                   (run["id"],)).fetchone():
        return "its sensitivities carry the retired v1 parameter e"
    return None


def drop_runs(con, run_ids: list[int]) -> dict[str, int]:
    """Delete the given runs with their results and sensitivities rows in one
    transaction, then VACUUM. Elicitations and parameters are never touched.
    Returns the rows deleted per table."""
    marks = ",".join("?" * len(run_ids))
    counts = {}
    for table, col in (("results", "run_id"), ("sensitivities", "run_id"), ("runs", "id")):
        counts[table] = con.execute(f"DELETE FROM {table} WHERE {col} IN ({marks})", run_ids).rowcount
    con.commit()
    con.execute("VACUUM")
    return counts
