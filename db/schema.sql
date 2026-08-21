-- voi-rank schema (spec §5). Append-only for scenarios and elicitations.
CREATE TABLE IF NOT EXISTS scenarios (
  id INTEGER PRIMARY KEY, created_at TEXT, title TEXT,
  agent TEXT, decision TEXT, theta_definition TEXT, instrument TEXT,
  domain_tags TEXT, source TEXT, raw_json TEXT
);
CREATE TABLE IF NOT EXISTS protocols (
  id INTEGER PRIMARY KEY, name TEXT, template_path TEXT, template_hash TEXT,
  model_alias TEXT, k_repeats INTEGER, cli_version TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS elicitations (
  id INTEGER PRIMARY KEY, scenario_id INTEGER, protocol_id INTEGER,
  repeat_ix INTEGER, prompt_hash TEXT, raw_response TEXT,
  valid INTEGER, error TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS parameters (
  id INTEGER PRIMARY KEY, elicitation_id INTEGER, name TEXT,
  p5 REAL, p50 REAL, p95 REAL, unit TEXT, reasoning TEXT,
  dist_family TEXT, fit_params TEXT, fit_residual REAL, fit_warning INTEGER
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY, created_at TEXT, seed INTEGER, n_draws INTEGER,
  code_hash TEXT, protocol_id INTEGER
);
CREATE TABLE IF NOT EXISTS results (
  run_id INTEGER, scenario_id INTEGER, metric TEXT,
  q05 REAL, q25 REAL, q50 REAL, q75 REAL, q95 REAL, p_positive REAL
);
CREATE TABLE IF NOT EXISTS sensitivities (
  run_id INTEGER, scenario_id INTEGER, param TEXT, spearman REAL
);
