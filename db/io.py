"""SQLite storage (spec §5). One file, voi.db. Append-only for scenarios and
elicitations: elicited data is never UPDATEd, only superseded by new rows under
a new protocol."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB = ROOT / "voi.db"

PARAM_NAMES = ["p", "s", "t", "e", "B", "K", "C"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def git_hash() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def claude_cli_version() -> str:
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def connect(db_path=DEFAULT_DB) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA_PATH.read_text())
    return con


# --- scenarios -------------------------------------------------------------

def insert_scenario(con, sc: dict, source: str) -> int:
    cur = con.execute(
        "INSERT INTO scenarios (created_at, title, agent, decision, theta_definition,"
        " instrument, domain_tags, source, raw_json) VALUES (?,?,?,?,?,?,?,?,?)",
        (now_iso(), sc["title"], sc["agent"], sc["decision"], sc["theta_definition"],
         sc["instrument"], json.dumps(sc.get("domain_tags", [])), source, json.dumps(sc)),
    )
    con.commit()
    return cur.lastrowid


def get_scenarios(con, selector: str = "all") -> list[sqlite3.Row]:
    """selector: 'all' | 'seed' | comma-separated ids."""
    if selector == "all":
        return con.execute("SELECT * FROM scenarios ORDER BY id").fetchall()
    if selector == "seed":
        return con.execute("SELECT * FROM scenarios WHERE source='seed' ORDER BY id").fetchall()
    ids = [int(x) for x in selector.split(",")]
    marks = ",".join("?" * len(ids))
    return con.execute(f"SELECT * FROM scenarios WHERE id IN ({marks}) ORDER BY id", ids).fetchall()


# --- protocols -------------------------------------------------------------

def get_or_create_protocol(con, yaml_path: str | Path) -> int:
    """Register a protocol YAML. Protocol files are immutable: re-registering a
    name with a changed template hash is an error (make a new protocol file)."""
    yaml_path = Path(yaml_path)
    cfg = yaml.safe_load(yaml_path.read_text())
    template_path = ROOT / cfg["template_path"]
    template_hash = sha256(template_path.read_text())
    row = con.execute("SELECT * FROM protocols WHERE name=?", (cfg["name"],)).fetchone()
    if row:
        if row["template_hash"] != template_hash:
            raise RuntimeError(
                f"protocol {cfg['name']} already registered with a different template hash; "
                "create a new protocol file instead of editing the template")
        return row["id"]
    cur = con.execute(
        "INSERT INTO protocols (name, template_path, template_hash, model_alias,"
        " k_repeats, cli_version, notes) VALUES (?,?,?,?,?,?,?)",
        (cfg["name"], cfg["template_path"], template_hash, cfg["model_alias"],
         int(cfg["k_repeats"]), claude_cli_version(), cfg.get("notes", "")),
    )
    con.commit()
    return cur.lastrowid


def protocol_by_name(con, name: str) -> sqlite3.Row:
    row = con.execute("SELECT * FROM protocols WHERE name=?", (name,)).fetchone()
    if row is None:
        raise RuntimeError(f"protocol {name!r} not registered in DB")
    return row


# --- elicitations and parameters ------------------------------------------

def insert_elicitation(con, scenario_id: int, protocol_id: int, repeat_ix: int,
                       prompt_hash: str, raw_response: str, valid: bool,
                       error: str | None) -> int:
    cur = con.execute(
        "INSERT INTO elicitations (scenario_id, protocol_id, repeat_ix, prompt_hash,"
        " raw_response, valid, error, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (scenario_id, protocol_id, repeat_ix, prompt_hash, raw_response,
         int(valid), error, now_iso()),
    )
    con.commit()
    return cur.lastrowid


def insert_parameter(con, elicitation_id: int, name: str, p5: float, p50: float,
                     p95: float, unit: str, reasoning: str, fit) -> int:
    cur = con.execute(
        "INSERT INTO parameters (elicitation_id, name, p5, p50, p95, unit, reasoning,"
        " dist_family, fit_params, fit_residual, fit_warning) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (elicitation_id, name, p5, p50, p95, unit, reasoning,
         fit.family, fit.params_json(), fit.residual, int(fit.warning)),
    )
    con.commit()
    return cur.lastrowid


def valid_repeat_count(con, scenario_id: int, protocol_id: int) -> int:
    return con.execute(
        "SELECT COUNT(DISTINCT repeat_ix) FROM elicitations"
        " WHERE scenario_id=? AND protocol_id=? AND valid=1",
        (scenario_id, protocol_id)).fetchone()[0]


def scenario_param_fits(con, protocol_id: int) -> dict[int, dict[str, list[dict]]]:
    """{scenario_id: {param_name: [fit rows in (repeat_ix, elicitation_id) order]}}
    over valid elicitations of one protocol. Each fit row carries
    dist_family, fit_params (parsed), p5/p50/p95."""
    rows = con.execute(
        "SELECT e.scenario_id, e.repeat_ix, e.id AS elicitation_id, p.name,"
        " p.p5, p.p50, p.p95, p.dist_family, p.fit_params"
        " FROM elicitations e JOIN parameters p ON p.elicitation_id = e.id"
        " WHERE e.protocol_id=? AND e.valid=1"
        " ORDER BY e.scenario_id, e.repeat_ix, e.id", (protocol_id,)).fetchall()
    out: dict[int, dict[str, list[dict]]] = {}
    for r in rows:
        out.setdefault(r["scenario_id"], {}).setdefault(r["name"], []).append({
            "family": r["dist_family"], "params": json.loads(r["fit_params"]),
            "p5": r["p5"], "p50": r["p50"], "p95": r["p95"],
        })
    return out


# --- runs, results, sensitivities ------------------------------------------

def insert_run(con, seed: int, n_draws: int, protocol_id: int) -> int:
    cur = con.execute(
        "INSERT INTO runs (created_at, seed, n_draws, code_hash, protocol_id)"
        " VALUES (?,?,?,?,?)",
        (now_iso(), seed, n_draws, git_hash(), protocol_id))
    con.commit()
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
        raise RuntimeError("no runs in DB")
    return row
