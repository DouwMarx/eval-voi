-- voi-rank schema (spec §5, v2 columns marked). Append-only for scenarios and
-- elicitations. db.connect() adds the v2 columns to pre-v2 databases, then
-- runs everything below the index marker line (indexes reference v2 columns).
CREATE TABLE IF NOT EXISTS scenarios (
  id INTEGER PRIMARY KEY, created_at TEXT, title TEXT,
  agent TEXT, decision TEXT, theta_definition TEXT, instrument TEXT,
  domain_tags TEXT, source TEXT, raw_json TEXT,
  context TEXT, grp TEXT, attributes TEXT              -- v2
);
CREATE TABLE IF NOT EXISTS protocols (
  id INTEGER PRIMARY KEY, name TEXT, template_path TEXT, template_hash TEXT,
  model_alias TEXT, k_repeats INTEGER, cli_version TEXT, notes TEXT,
  members_json TEXT,                                   -- v2: [{provider, model, k_repeats}]
  scenario_selector TEXT,                              -- v2: 'all' | 'seed' | '1,2,3'
  model_kind TEXT                                      -- v2.1: 'binary' | 'gaussian' (NULL = binary)
);
CREATE TABLE IF NOT EXISTS elicitations (
  id INTEGER PRIMARY KEY, scenario_id INTEGER, protocol_id INTEGER,
  repeat_ix INTEGER, prompt_hash TEXT, raw_response TEXT,
  valid INTEGER, error TEXT, created_at TEXT,
  provider TEXT, model TEXT                            -- v2: ensemble member identity
);
CREATE TABLE IF NOT EXISTS parameters (
  id INTEGER PRIMARY KEY, elicitation_id INTEGER, name TEXT,
  p5 REAL, p50 REAL, p95 REAL, unit TEXT, reasoning TEXT,
  dist_family TEXT, fit_params TEXT, fit_residual REAL, fit_warning INTEGER
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY, created_at TEXT, seed INTEGER, n_draws INTEGER,
  code_hash TEXT, protocol_id INTEGER,
  data_hash TEXT                                       -- v2: digest of the valid elicitations used
);
CREATE TABLE IF NOT EXISTS results (
  run_id INTEGER, scenario_id INTEGER, metric TEXT,
  q05 REAL, q25 REAL, q50 REAL, q75 REAL, q95 REAL, p_positive REAL
);
CREATE TABLE IF NOT EXISTS sensitivities (
  run_id INTEGER, scenario_id INTEGER, param TEXT, spearman REAL
);
-- indexes
-- one valid elicitation per slot (scenario, protocol, member, repeat)
CREATE UNIQUE INDEX IF NOT EXISTS ux_elicitations_valid_slot
  ON elicitations (scenario_id, protocol_id, provider, model, repeat_ix) WHERE valid=1;
