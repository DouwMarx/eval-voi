"""SQLite storage. One file per study, voi.db. Append-only for scenarios and
elicitations: elicited data is never UPDATEd, only superseded by new rows
under a new protocol.

connect() adds any column an older database lacks (V2_COLUMNS) and backfills
the member identity of pre-v2 elicitations; connect_copy() prepares an
in-memory copy for dry runs and for reading an archived database. Protocol
rows carry members_json, scenario_selector, stages_json (the two stages: a
decision stage elicited once per scenario group and an instrument stage per
scenario, see "staged protocols" below) and template_vars_json (the
resolved template variables); runs carry members_json (the member subset a
run pooled, NULL = every member). The protocols.model_kind and runs.weights
columns stay in the schema for archived databases; every protocol is the
binary model now, a protocol file that sets another model is refused, and
every run pools its fits with equal weight.

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

import yaml

from voi_rank.fit import PARAM_NAMES

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

__all__ = ["PARAM_NAMES", "ROOT", "connect"]

# columns added after v1; (table -> {column: type}) checked on every connect
V2_COLUMNS = {
    "scenarios": {"context": "TEXT", "grp": "TEXT", "attributes": "TEXT", "decision_context": "TEXT",
                  "instrument_context": "TEXT", "sources": "TEXT"},
    "elicitations": {"provider": "TEXT", "model": "TEXT", "stage": "TEXT"},
    "protocols": {"members_json": "TEXT", "scenario_selector": "TEXT", "model_kind": "TEXT",
                  "stages_json": "TEXT", "template_vars_json": "TEXT"},
    "runs": {"data_hash": "TEXT", "members_json": "TEXT", "weights": "TEXT"},
}
# the one model kind the code knows; the column keeps the value of archived rows
BINARY_KIND = "binary"
# paths whose uncommitted changes make a run's code_hash '-dirty'
CODE_PATHS = ("voi_rank", "pyproject.toml", "uv.lock")
LEGACY_PROVIDER = "claude_cli"
# a seed row whose title left scenarios.json: kept (rows are never deleted),
# left out of the 'all' / 'seed' selections, restored when the title returns
RETIRED_SOURCE = "seed:retired"
# git_state's HEAD when git is unavailable or the tree is not a repository
UNKNOWN_HEAD = "unknown"
SCHEMA_INDEX_MARKER = "-- indexes"


def check_model(value) -> str:
    """The protocol's 'model' key: absent or 'binary'. Anything else (the
    retired Gaussian-state family included) is refused."""
    kind = BINARY_KIND if value is None else str(value).strip().lower()
    if kind != BINARY_KIND:
        raise ValueError(f"protocol model {value!r} is not supported: only the binary model remains"
                         " (the Gaussian-state family was retired on 2026-09-30; its protocols and data"
                         " are under archive/, frozen at tag pilot-2026-09-30)")
    return kind


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
    """Create missing tables, add missing columns, then create the indexes
    (which reference added columns, so they must come after the migration)."""
    con.row_factory = sqlite3.Row
    tables, _, indexes = SCHEMA_PATH.read_text().partition(SCHEMA_INDEX_MARKER)
    con.executescript(tables)
    migrate(con)
    check_duplicate_valid_slots(con)
    con.executescript(indexes)
    return con


def duplicate_valid_slots(con) -> list[sqlite3.Row]:
    """Slots (scenario, protocol, member, repeat, stage) holding more than one
    valid elicitation: possible only in databases written before the unique
    index."""
    return con.execute(
        "SELECT scenario_id, protocol_id, provider, model, repeat_ix, COUNT(*) AS n,"
        " GROUP_CONCAT(id) AS ids FROM elicitations WHERE valid=1"
        " GROUP BY scenario_id, protocol_id, provider, model, repeat_ix, COALESCE(stage, '')"
        " HAVING COUNT(*) > 1"
        " ORDER BY scenario_id, protocol_id, provider, model, repeat_ix").fetchall()


DUPLICATE_SLOT_REPAIR_SQL = (
    "UPDATE elicitations SET valid=0, error='duplicate slot' WHERE valid=1 AND id NOT IN"
    " (SELECT MIN(id) FROM elicitations WHERE valid=1"
    " GROUP BY scenario_id, protocol_id, provider, model, repeat_ix, COALESCE(stage, ''));")


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
    created, written or migrated: this is what --dry-run works on, and how
    an archived database is read."""
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
    """Add any column of V2_COLUMNS missing from an older database, then
    backfill the member identity of pre-v2 elicitations (a single claude_cli
    member, model = the protocol's model_alias). Returns the columns added."""
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
    con.commit()
    return added


# --- scenarios -------------------------------------------------------------

# scenario columns refreshed from scenarios.json while a seed row has no
# elicitations yet (the title is the identity and is never refreshed)
SEED_MUTABLE = ("agent", "decision", "theta_definition", "instrument", "context",
                "decision_context", "instrument_context", "sources",
                "grp", "attributes", "domain_tags", "raw_json")
JSON_COLUMNS = ("attributes", "domain_tags", "raw_json", "sources")


def _json_or_none(value) -> str | None:
    return None if value is None else json.dumps(value)


def _seed_values(sc: dict) -> dict:
    """Column values a scenarios.json entry maps to (raw_json keeps the whole
    entry; the archived 'context' column is filled only by an entry that
    still carries that key)."""
    return {"agent": sc["agent"], "decision": sc["decision"],
            "theta_definition": sc["theta_definition"], "instrument": sc["instrument"],
            "context": sc.get("context"), "decision_context": sc.get("decision_context"),
            "instrument_context": sc.get("instrument_context"), "sources": _json_or_none(sc.get("sources")),
            "grp": sc.get("group"), "attributes": _json_or_none(sc.get("attributes")),
            "domain_tags": json.dumps(sc.get("domain_tags", [])), "raw_json": json.dumps(sc)}


def insert_scenario(con, sc: dict, source: str) -> int:
    values = _seed_values(sc)
    cols = ("created_at", "title", "source", *SEED_MUTABLE)
    cur = con.execute(
        f"INSERT INTO scenarios ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        (now_iso(), sc["title"], source, *(values[c] for c in SEED_MUTABLE)))
    con.commit()
    return cur.lastrowid


def _seed_diff(row, want: dict) -> list[str]:
    """Mutable columns whose stored value differs from scenarios.json (JSON
    columns compared as parsed values, so key order does not count)."""
    diff = []
    for col in SEED_MUTABLE:
        got = row[col]
        if col in JSON_COLUMNS:
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
            insert_scenario(con, sc, source="seed")
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

# Optional per-member fields of an openrouter member. All but est_output_tokens
# are request options (providers.openrouter.request_body); est_output_tokens
# is the cost estimate's output assumption (voi_rank.pricing). A member keeps
# only the fields its YAML sets, so a member without options stores exactly
# {provider, model, k_repeats} and older protocol rows compare equal.
REASONING_EFFORTS = ("low", "medium", "high")
MEMBER_REQUEST_OPTIONS = ("reasoning_effort", "max_tokens", "json_mode", "provider_order", "temperature")
MEMBER_OPTIONS = (*MEMBER_REQUEST_OPTIONS, "est_output_tokens")
MEMBER_REQUIRED = ("provider", "model", "k_repeats")


def _member_option(name: str, value):
    """A validated member option value; ValueError names the field."""
    if name == "reasoning_effort":
        if value not in REASONING_EFFORTS:
            raise ValueError(f"reasoning_effort must be one of {list(REASONING_EFFORTS)}, got {value!r}")
        return value
    if name in ("max_tokens", "est_output_tokens"):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer, got {value!r}")
        return value
    if name == "json_mode":
        if not isinstance(value, bool):
            raise ValueError(f"json_mode must be true or false, got {value!r}")
        return value
    if name == "provider_order":
        if (not isinstance(value, list) or not value
                or not all(isinstance(v, str) and v.strip() for v in value)):
            raise ValueError(f"provider_order must be a non-empty list of provider names, got {value!r}")
        return [v.strip() for v in value]
    if name == "temperature":   # 'omit': send none (an endpoint that rejects the parameter)
        if value == "omit":
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 2:
            raise ValueError(f"temperature must be a number in [0, 2] or 'omit', got {value!r}")
        return float(value)
    raise ValueError(f"unknown member field {name!r}")


def normalize_member(m: dict) -> dict:
    """{provider, model, k_repeats} plus the optional fields the YAML sets
    (MEMBER_OPTIONS, openrouter members only); unknown fields are refused."""
    missing = [f for f in MEMBER_REQUIRED if f not in m]
    if missing:
        raise ValueError(f"member {m!r} lacks {missing}")
    out = {"provider": str(m["provider"]), "model": str(m["model"]), "k_repeats": int(m["k_repeats"])}
    extra = [f for f in m if f not in MEMBER_REQUIRED]
    unknown = [f for f in extra if f not in MEMBER_OPTIONS]
    if unknown:
        raise ValueError(f"member {member_label(out)}: unknown fields {unknown}"
                         f" (optional fields: {list(MEMBER_OPTIONS)})")
    if extra and out["provider"] != "openrouter":
        raise ValueError(f"member {member_label(out)}: {extra} apply to openrouter members only")
    for f in MEMBER_OPTIONS:
        if f in m:
            try:
                out[f] = _member_option(f, m[f])
            except ValueError as ex:
                raise ValueError(f"member {member_label(out)}: {ex}") from None
    return out


def member_request_options(member: dict) -> dict:
    """The request options a member sets (keyword arguments of its provider
    call); {} for a member without any."""
    return {f: member[f] for f in MEMBER_REQUEST_OPTIONS if f in member}


def normalize_members(cfg: dict) -> list[dict]:
    """Protocol members as [{provider, model, k_repeats, <options>}], from
    either the 'members' list or the legacy 'model_alias' + 'k_repeats' pair
    of a pre-v2 row (a single claude_cli member)."""
    if "members" in cfg:
        members = [normalize_member(m) for m in cfg["members"]]
        if not members:
            raise ValueError("protocol has an empty members list")
        seen = set()
        for m in members:
            key = (m["provider"], m["model"])
            if key in seen:
                raise ValueError(f"protocol lists member {member_label(m)} more than once")
            seen.add(key)
        return members
    return [{"provider": LEGACY_PROVIDER, "model": str(cfg["model_alias"]),
             "k_repeats": int(cfg["k_repeats"])}]


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


# --- member subsets ---------------------------------------------------------
# A run may pool a SUBSET of the protocol's members (mc --members); the subset
# is stored on the run as a sorted JSON list of member labels, NULL meaning
# every member. Every reader of a run's elicitations (fits, pooled medians,
# counts) takes the same `members` argument: a list of labels, or None for
# all. Pooling incoherent members yields a ranking that belongs to nobody
# (LEARNINGS, eval studies iteration 2), so an ablation scores one elicitor
# as its own stored run.

def parse_member_labels(spec: str | None) -> list[str] | None:
    """'a:b,c:d' -> sorted distinct labels; None or '' -> None (all members)."""
    if not spec:
        return None
    labels = sorted({m.strip() for m in spec.split(",") if m.strip()})
    return labels or None


def normalize_run_members(protocol_members: list[dict], labels: list[str] | None) -> list[str] | None:
    """The stored subset for a run: None when `labels` is None or names every
    member of the protocol (the canonical 'all members' run), else the sorted
    labels. A label the protocol does not list raises ValueError."""
    if labels is None:
        return None
    have = [member_label(m) for m in protocol_members]
    unknown = sorted(set(labels) - set(have))
    if unknown:
        raise ValueError(f"members {unknown} are not members of the protocol (it has {have})")
    labels = sorted(set(labels))
    return None if set(labels) == set(have) else labels


def run_members_json(labels: list[str] | None) -> str | None:
    return None if labels is None else json.dumps(sorted(labels))


def run_member_labels(run) -> list[str] | None:
    """The member subset a stored run pooled (None = every member)."""
    try:
        raw = run["members_json"]
    except (IndexError, KeyError):
        return None
    return json.loads(raw) if raw else None


def run_members(con, run) -> list[dict]:
    """The members a run pooled, as protocol member dicts in protocol order:
    every member, or the stored subset."""
    prot = con.execute("SELECT * FROM protocols WHERE id=?", (run["protocol_id"],)).fetchone()
    members = protocol_members(prot)
    labels = run_member_labels(run)
    if labels is None:
        return members
    return [m for m in members if member_label(m) in labels]


def members_label(labels: list[str] | None) -> str:
    """Printable form of a subset: 'all members' or the labels joined."""
    return "all members" if labels is None else ", ".join(labels)


def member_filter(labels: list[str] | None, alias: str = "e") -> tuple[str, list]:
    """SQL fragment (" AND (alias.provider || ':' || alias.model) IN (?,..)", params)
    restricting elicitation rows to a member subset; ('', []) for all."""
    if labels is None:
        return "", []
    marks = ",".join("?" * len(labels))
    return f" AND ({alias}.provider || ':' || {alias}.model) IN ({marks})", list(labels)


def protocol_selector(row) -> str:
    """Scenario scope of a stored protocol row ('all' for rows registered
    before selectors existed)."""
    return row["scenario_selector"] or "all"


# --- staged protocols -------------------------------------------------------
# Every protocol has two stages (DESIGN section 4): a GROUP stage (name
# 'decision' by convention) elicited once per scenario group and stored on
# the group's representative scenario (its lowest id) with
# elicitations.stage = the stage name, and a SCENARIO stage ('instrument')
# elicited per scenario. Protocol YAML:
#   stages:
#     - {name: decision, template_path: templates/decision.md, params: [p, B, K], group_key: self}
#     - {name: instrument, template_path: templates/instrument.md,
#        params: [s, t, C_build, C_run]}
#   template_vars: {context_mode: curated, anchors_decision: ''}
# group_key 'self' makes every scenario its own group (the representative is
# the scenario itself); 'group' or 'attributes.<key>' groups scenarios that
# share one decision (and the same agent, decision, theta and
# decision_context text). template_vars are substituted into both templates;
# a value '@file:<path relative to the study root>' inlines that file.
# Stored as protocols.stages_json (with each stage's template hash) and
# protocols.template_vars_json (resolved); both are part of the template hash
# and of the immutability check. scenario_param_fits assembles a scenario's
# fits from its group's decision rows and its own instrument rows.

STAGE_GROUP_PREFIX = "attributes."
SELF_GROUP = "self"
FILE_VAR_PREFIX = "@file:"
# the fields the templates render from the scenario row; a template variable
# may not take one of these names
SCENARIO_FIELDS = ("title", "agent", "decision", "theta_definition", "instrument", "context",
                   "decision_context")


def normalize_stages(cfg: dict, study_root: str | Path) -> list[dict]:
    """The stored form of a protocol's 'stages': [{name, template_path,
    template_hash, params, group_key?}]. Exactly two stages, one with a
    group_key (the group stage) and one without, whose params partition
    PARAM_NAMES. A protocol without stages, or with a template_path or
    decision_contexts (the pilots' single-prompt and protocol-level context
    forms), is refused."""
    raw = cfg.get("stages")
    if raw is None:
        raise ValueError("a protocol lists two stages (a decision stage and an instrument stage);"
                         " single-prompt protocols were retired on 2026-09-30")
    if cfg.get("template_path") is not None:
        raise ValueError("a staged protocol names its templates per stage, not a template_path")
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError("stages must list exactly two stages (a group stage and a scenario stage)")
    stages, seen_params = [], []
    for st in raw:
        if not isinstance(st, dict) or not st.get("name") or not st.get("template_path"):
            raise ValueError("every stage needs a name and a template_path")
        params = [str(p) for p in st.get("params") or []]
        unknown = [p for p in params if p not in PARAM_NAMES]
        if not params or unknown:
            raise ValueError(f"stage {st['name']}: params must be a non-empty subset of {PARAM_NAMES}"
                             f" (got {params})")
        if st.get("decision_contexts") is not None:
            raise ValueError(f"stage {st['name']}: protocol-level decision_contexts are gone; the decision"
                             " prompt renders each scenario's own decision_context field")
        path = Path(study_root) / str(st["template_path"])
        out = {"name": str(st["name"]), "template_path": str(st["template_path"]),
               "template_hash": sha256(path.read_text()), "params": params}
        if st.get("group_key") is not None:
            key = str(st["group_key"])
            if key not in (SELF_GROUP, "group") and not key.startswith(STAGE_GROUP_PREFIX):
                raise ValueError(f"stage {st['name']}: group_key must be 'self', 'group' or"
                                 " 'attributes.<key>'")
            out["group_key"] = key
        stages.append(out)
        seen_params += params
    if len({s["name"] for s in stages}) != 2:
        raise ValueError("stage names must differ")
    if sorted(seen_params) != sorted(PARAM_NAMES):
        raise ValueError(f"the stages' params must partition {PARAM_NAMES} (got {seen_params})")
    if sum("group_key" in s for s in stages) != 1:
        raise ValueError("exactly one stage (the decision stage) takes a group_key")
    return stages


def normalize_template_vars(cfg: dict, study_root: str | Path) -> dict[str, str]:
    """The protocol's 'template_vars' as substituted into both templates: a
    mapping of identifiers to strings, a value '@file:<path>' replaced by
    that file's text (path relative to the study root). A name of a scenario
    field is refused."""
    raw = cfg.get("template_vars") or {}
    if not isinstance(raw, dict):
        raise ValueError("template_vars must map variable names to strings")
    out = {}
    for key, value in raw.items():
        name = str(key)
        if not name.isidentifier():
            raise ValueError(f"template_vars: {name!r} is not a valid $variable name")
        if name in SCENARIO_FIELDS:
            raise ValueError(f"template_vars: {name!r} is a scenario field, which the templates render"
                             " from the scenario; choose another name")
        text = str(value)
        if text.startswith(FILE_VAR_PREFIX):
            path = Path(study_root) / text[len(FILE_VAR_PREFIX):]
            if not path.is_file():
                raise ValueError(f"template_vars: {name} points at {text!r}, which is not a file"
                                 f" under the study root")
            text = path.read_text()
        out[name] = text
    return out


def template_vars_json(template_vars: dict[str, str]) -> str:
    return json.dumps(template_vars, sort_keys=True)


def protocol_template_vars(row) -> dict[str, str]:
    """The resolved template variables of a stored protocol row ({} for a
    row registered before the column existed)."""
    try:
        raw = row["template_vars_json"]
    except (IndexError, KeyError):
        return {}
    return json.loads(raw) if raw else {}


def stages_json(stages: list[dict] | None) -> str | None:
    return None if stages is None else json.dumps(stages, sort_keys=True)


def protocol_stages(row) -> list[dict] | None:
    """The stored stages of a protocol row (None for an archived single-stage
    one, or for a missing row)."""
    if row is None:
        return None
    try:
        raw = row["stages_json"]
    except (IndexError, KeyError):
        return None
    return json.loads(raw) if raw else None


def group_stage(stages: list[dict]) -> dict:
    return next(s for s in stages if "group_key" in s)


def scenario_stage(stages: list[dict]) -> dict:
    return next(s for s in stages if "group_key" not in s)


def stage_of_param(stages: list[dict] | None, name: str) -> dict | None:
    if stages is None:
        return None
    return next((s for s in stages if name in s["params"]), None)


def scenario_group_value(row, group_key: str) -> str | None:
    """The group a scenario row belongs to under a stage's group_key ('self'
    -> the scenario's own id, 'group' -> the grp column, 'attributes.<key>'
    -> that attribute), as a string; None when absent."""
    if group_key == SELF_GROUP:
        value = row["id"]
    elif group_key == "group":
        value = row["grp"]
    else:
        value = scenario_attributes(row).get(group_key[len(STAGE_GROUP_PREFIX):])
    return None if value is None else str(value)


def scenario_groups_by_key(con, group_key: str, selector: str = "all") -> dict[str, list[int]]:
    """{group value: sorted scenario ids} over get_scenarios(con, selector);
    scenarios without a value are left out (the caller checks)."""
    out: dict[str, list[int]] = {}
    for r in get_scenarios(con, selector):
        value = scenario_group_value(r, group_key)
        if value is not None:
            out.setdefault(value, []).append(r["id"])
    return {g: sorted(ids) for g, ids in out.items()}


def scenario_group_ids(con, group_key: str, scenario_id: int) -> list[int]:
    """Every scenario (retired ones included, so a representative that left
    scenarios.json keeps carrying its group's decision rows) in the same
    group as scenario_id, sorted; [scenario_id] when it has no group value
    (or under group_key 'self')."""
    if group_key == SELF_GROUP:
        return [scenario_id]
    row = con.execute("SELECT * FROM scenarios WHERE id=?", (scenario_id,)).fetchone()
    value = scenario_group_value(row, group_key) if row else None
    if value is None:
        return [scenario_id]
    return sorted(r["id"] for r in con.execute("SELECT * FROM scenarios")
                  if scenario_group_value(r, group_key) == value)


def _protocol_row(con, protocol_id: int):
    return con.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()


def stage_clause(stage: str | None, alias: str = "e") -> tuple[str, list]:
    """SQL fragment restricting elicitation rows to one stage (NULL = the
    single stage of an unstaged protocol)."""
    return f" AND COALESCE({alias}.stage, '')=?", [stage or ""]


def get_or_create_protocol(con, yaml_path: str | Path, study_root: str | Path) -> int:
    """Register a protocol YAML (template paths relative to the study root).
    Protocol files are immutable: re-registering a name with a changed
    template (either stage's file, or a file a template variable inlines),
    template variable, member list, scenario scope or stage config (a
    template's path included) is an error (make a new protocol file)."""
    yaml_path = Path(yaml_path)
    cfg = yaml.safe_load(yaml_path.read_text())
    try:
        members = normalize_members(cfg)
        kind = check_model(cfg.get("model"))
        stages = normalize_stages(cfg, study_root)
        template_vars = normalize_template_vars(cfg, study_root)
    except ValueError as ex:
        raise RuntimeError(f"protocol {cfg['name']}: {ex}") from None
    # the row's template columns describe both stages; stages_json is authoritative
    template_path_text = " + ".join(s["template_path"] for s in stages)
    # covers both templates, the stage config and the resolved template variables
    template_hash = sha256(stages_json(stages) + "\n" + template_vars_json(template_vars))
    selector = normalize_selector(cfg.get("scenarios"))
    row = con.execute("SELECT * FROM protocols WHERE name=?", (cfg["name"],)).fetchone()
    if row:
        changed = [what for what, got, want in (
            ("template_hash", row["template_hash"], template_hash),
            ("members", members_json(protocol_members(row)), members_json(members)),
            ("scenarios", protocol_selector(row), selector),
            ("model", row["model_kind"] or BINARY_KIND, kind),
            ("stages", stages_json(protocol_stages(row)), stages_json(stages)),
            ("template_vars", template_vars_json(protocol_template_vars(row)),
             template_vars_json(template_vars)),
        ) if got != want]
        if changed:
            raise RuntimeError(
                f"protocol {cfg['name']} already registered with different {changed}; "
                "create a new protocol file instead of editing an old one")
        return row["id"]
    cur = con.execute(
        "INSERT INTO protocols (name, template_path, template_hash, model_alias,"
        " k_repeats, cli_version, notes, members_json, scenario_selector, model_kind, stages_json,"
        " template_vars_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (cfg["name"], template_path_text, template_hash,
         ",".join(member_label(m) for m in members),
         sum(m["k_repeats"] for m in members),
         claude_cli_version(), cfg.get("notes", ""), members_json(members), selector, kind,
         stages_json(stages), template_vars_json(template_vars)),
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
                       raw_response: str, valid: bool, error: str | None,
                       stage: str | None = None) -> int:
    """No commit here: an elicitation row and its parameter rows must land in
    one transaction (the caller commits), so a crash cannot persist a valid
    row with a partial parameter set that resume logic would then skip.
    stage: the stage name under a staged protocol (NULL otherwise)."""
    cur = con.execute(
        "INSERT INTO elicitations (scenario_id, protocol_id, provider, model, repeat_ix,"
        " prompt_hash, raw_response, valid, error, created_at, stage) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (scenario_id, protocol_id, provider, model, repeat_ix, prompt_hash,
         raw_response, int(valid), error, now_iso(), stage),
    )
    return cur.lastrowid


def insert_parameter(con, elicitation_id: int, name: str, p5: float, p50: float,
                     p95: float, reasoning: str, fit) -> int:
    """No commit here: see insert_elicitation. The archived unit column stays
    NULL: the units are fixed by the template."""
    cur = con.execute(
        "INSERT INTO parameters (elicitation_id, name, p5, p50, p95, reasoning,"
        " dist_family, fit_params, fit_residual, fit_warning) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (elicitation_id, name, p5, p50, p95, reasoning,
         fit.family, fit.params_json(), fit.residual, int(fit.warning)),
    )
    return cur.lastrowid


def valid_repeats(con, scenario_id, protocol_id: int, provider: str,
                  model: str, stage: str | None = None) -> set[int]:
    """repeat_ix values already holding a valid elicitation for one slot
    family (scenario, protocol, member, stage). scenario_id may be a list of
    ids (a group's, for the decision stage whose rows sit on the group's
    representative scenario)."""
    ids = list(scenario_id) if isinstance(scenario_id, (list, tuple, set)) else [scenario_id]
    marks = ",".join("?" * len(ids))
    clause, args = stage_clause(stage)
    return {r[0] for r in con.execute(
        f"SELECT DISTINCT repeat_ix FROM elicitations e WHERE scenario_id IN ({marks}) AND protocol_id=?"
        f" AND provider=? AND model=? AND valid=1{clause}",
        (*ids, protocol_id, provider, model, *args))}


def scenario_param_fits(con, protocol_id: int, names: list[str] | None = None,
                        members: list[str] | None = None) -> dict[int, dict[str, list[dict]]]:
    """{scenario_id: {param_name: [fit rows]}} over ALL valid elicitations of
    one protocol, every member and repeat pooled (or the `members` subset, a
    list of labels), in (provider, model, repeat_ix, elicitation_id) order.
    Only the parameter names asked for (PARAM_NAMES by default) are
    returned; stored rows of other names (an archived database's retired
    parameters) are ignored. An archived single-stage protocol (stages
    None) reads every row from the scenario itself. Each fit row carries
    elicitation_id, provider, model, family, fit_params (the stored JSON
    string), params (parsed), p5/p50/p95."""
    prot = _protocol_row(con, protocol_id)
    names = list(PARAM_NAMES if names is None else names)
    stages = protocol_stages(prot) if prot else None
    clause, args = member_filter(members)
    rows = con.execute(
        "SELECT e.scenario_id, e.provider, e.model, e.repeat_ix, e.id AS elicitation_id, e.stage,"
        " p.name, p.p5, p.p50, p.p95, p.dist_family, p.fit_params"
        " FROM elicitations e JOIN parameters p ON p.elicitation_id = e.id"
        f" WHERE e.protocol_id=? AND e.valid=1{clause}"
        " ORDER BY e.scenario_id, e.provider, e.model, e.repeat_ix, e.id", (protocol_id, *args)).fetchall()
    out: dict[int, dict[str, list[dict]]] = {}
    by_group: dict[str, dict[str, list[dict]]] = {}   # staged: the decision rows per group value
    group_of: dict[int, str | None] = {}
    if stages is not None:
        gstage, sstage = group_stage(stages), scenario_stage(stages)
        group_of = {r["id"]: scenario_group_value(r, gstage["group_key"])
                    for r in con.execute("SELECT * FROM scenarios")}
    for r in rows:
        if r["name"] not in names:
            continue
        fit = {"elicitation_id": r["elicitation_id"],
               "provider": r["provider"], "model": r["model"],
               "family": r["dist_family"], "params": json.loads(r["fit_params"]),
               "fit_params": r["fit_params"],
               "p5": r["p5"], "p50": r["p50"], "p95": r["p95"]}
        if stages is None:
            out.setdefault(r["scenario_id"], {}).setdefault(r["name"], []).append(fit)
        elif r["stage"] == gstage["name"] and r["name"] in gstage["params"]:
            value = group_of.get(r["scenario_id"])
            if value is not None:
                by_group.setdefault(value, {}).setdefault(r["name"], []).append(fit)
        elif r["stage"] == sstage["name"] and r["name"] in sstage["params"]:
            out.setdefault(r["scenario_id"], {}).setdefault(r["name"], []).append(fit)
    if stages is not None:
        # a scenario takes its group's decision fits (the same fit rows, hence
        # the same elicitation ids, for every scenario of the group); a group
        # without a complete decision stage leaves its scenarios incomplete
        for sid, fits in out.items():
            shared = by_group.get(group_of.get(sid), {})
            for name in gstage["params"]:
                if name in names and shared.get(name):
                    fits[name] = shared[name]
    return out


def elicited_source_ids(con, protocol_id: int, scenario_id: int, name: str) -> list[int]:
    """The scenario ids whose elicitation rows feed one parameter of one
    scenario under a protocol: [scenario_id], or under a staged protocol, for
    a group-stage parameter (p, B, K), every scenario of its group
    (scenario_group_ids). Two scenarios with the same list read the same
    rows."""
    stages = protocol_stages(_protocol_row(con, protocol_id))
    stage = stage_of_param(stages, name)
    if stage is not None and "group_key" in stage:
        return scenario_group_ids(con, stage["group_key"], scenario_id)
    return [scenario_id]


def _elicited_rows(con, protocol_id: int, scenario_id: int, name: str,
                   provider: str | None = None, model: str | None = None,
                   members: list[str] | None = None) -> list[sqlite3.Row]:
    """(provider, model, p50) of one parameter over the valid elicitations
    that feed one scenario under a protocol, in (provider, model, repeat_ix,
    id) order. Under a staged protocol a group-stage parameter (p, B, K) is
    read from the scenario's group (the rows on its representative), the
    scenario-stage ones from the scenario's own rows of that stage."""
    stages = protocol_stages(_protocol_row(con, protocol_id))
    ids = elicited_source_ids(con, protocol_id, scenario_id, name)
    sclause, sargs = "", []
    if stages is not None:
        stage = stage_of_param(stages, name)
        sclause, sargs = stage_clause(stage["name"] if stage else None)
    clause, margs = member_filter(members)
    marks = ",".join("?" * len(ids))
    sql = ("SELECT e.provider, e.model, p.p50 FROM parameters p"
           " JOIN elicitations e ON e.id=p.elicitation_id"
           f" WHERE e.scenario_id IN ({marks}) AND e.protocol_id=? AND e.valid=1 AND p.name=?"
           f"{sclause}{clause}")
    args: list = [*ids, protocol_id, name, *sargs, *margs]
    if provider is not None:
        sql += " AND e.provider=? AND e.model=?"
        args += [provider, model]
    sql += " ORDER BY e.provider, e.model, e.repeat_ix, e.id"
    return con.execute(sql, args).fetchall()


def elicited_p50s(con, protocol_id: int, scenario_id: int, name: str,
                  provider: str | None = None, model: str | None = None,
                  first: int | None = None, members: list[str] | None = None) -> list[float]:
    """p50 of one parameter over the valid elicitations of one scenario under
    a protocol (its group's decision rows for a group-stage parameter of a
    staged protocol), optionally restricted to one member (provider, model),
    to a member subset (`members`, a list of labels) and/or to the first
    `first` VALID repeats of each member in repeat_ix order (a count, not an
    index cap: a member whose repeat 1 ended invalid still contributes its
    repeats 0, 2, 3 to 'first 3')."""
    rows = _elicited_rows(con, protocol_id, scenario_id, name, provider, model, members)
    if first is None:
        return [r[2] for r in rows]
    taken: dict[tuple, int] = {}
    out = []
    for prov, mod, p50 in rows:
        if taken.get((prov, mod), 0) < first:
            taken[(prov, mod)] = taken.get((prov, mod), 0) + 1
            out.append(p50)
    return out


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
               code_hash: str | None = None, members: list[str] | None = None) -> int:
    """No commit here: the runs row commits together with its results and
    sensitivities at the end of the MC run, so an interrupted run cannot
    become the (empty) latest run. code_hash defaults to git_hash(); members
    is the pooled subset (labels), None for every member."""
    cur = con.execute(
        "INSERT INTO runs (created_at, seed, n_draws, code_hash, protocol_id, data_hash, members_json)"
        " VALUES (?,?,?,?,?,?,?)",
        (now_iso(), seed, n_draws, code_hash or git_hash(), protocol_id, data_hash,
         run_members_json(members)))
    return cur.lastrowid


def insert_result(con, run_id: int, scenario_id: int, metric: str, qs: dict):
    """One results row: a metric's quantiles ({0.05: .., ..., 0.95: ..}), or a
    probability ({0.5: value}, the other columns NULL). The archived
    p_positive column is left NULL."""
    con.execute(
        "INSERT INTO results (run_id, scenario_id, metric, q05, q25, q50, q75, q95)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (run_id, scenario_id, metric, qs.get(0.05), qs.get(0.25), qs.get(0.50),
         qs.get(0.75), qs.get(0.95)))


def insert_sensitivity(con, run_id: int, scenario_id: int, param: str,
                       rho: float | None):
    con.execute(
        "INSERT INTO sensitivities (run_id, scenario_id, param, spearman)"
        " VALUES (?,?,?,?)", (run_id, scenario_id, param, rho))


def latest_run(con, protocol_name: str | None = None,
               members: list[str] | None = None) -> sqlite3.Row:
    """The latest run, of one protocol when named, that pooled exactly the
    member subset `members` (labels; None = every member, which is also what
    a subset naming every protocol member means). A run is never selected
    across subsets: a subset run is not 'the latest p003 run'."""
    if protocol_name:
        prot = protocol_by_name(con, protocol_name)
        try:
            members = normalize_run_members(protocol_members(prot), members)
        except ValueError as ex:
            raise RuntimeError(f"protocol {protocol_name!r}: {ex}") from None
    elif members is not None:
        members = sorted(set(members))
    want = run_members_json(members)
    clause = " AND r.members_json IS NULL" if want is None else " AND r.members_json=?"
    args: list = [] if want is None else [want]
    if protocol_name:
        row = con.execute(
            "SELECT r.* FROM runs r JOIN protocols p ON p.id = r.protocol_id"
            f" WHERE p.name=?{clause} ORDER BY r.id DESC LIMIT 1", (protocol_name, *args)).fetchone()
    else:
        row = con.execute(f"SELECT r.* FROM runs r WHERE 1=1{clause} ORDER BY r.id DESC LIMIT 1",
                          args).fetchone()
    if row is None:
        raise RuntimeError("no runs in DB" + (f" under protocol {protocol_name!r}" if protocol_name else "")
                           + (f" with members [{members_label(members)}]" if members is not None else ""))
    return row


def get_run(con, run_id: int) -> sqlite3.Row:
    row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise RuntimeError(f"no run {run_id}")
    return row
