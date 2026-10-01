-- voi-rank schema. Append-only for scenarios and elicitations. db.connect()
-- adds any column below that an older database lacks (db.V2_COLUMNS), then
-- runs everything below the index marker line (indexes reference added
-- columns). Columns marked "archived" hold values written by retired code and
-- are read, never written, by the current code.
CREATE TABLE IF NOT EXISTS scenarios (
  id INTEGER PRIMARY KEY, created_at TEXT, title TEXT,
  agent TEXT, decision TEXT, theta_definition TEXT, instrument TEXT,
  domain_tags TEXT, source TEXT, raw_json TEXT,       -- raw_json: the whole scenarios.json entry
  context TEXT,                                        -- archived: the single-prompt pilots' facts
  grp TEXT, attributes TEXT,
  decision_context TEXT,                               -- rendered by the decision prompt
  instrument_context TEXT,                             -- rendered as $context by the instrument prompt
  sources TEXT                                         -- JSON list of {key, kind, ref, role}
);
CREATE TABLE IF NOT EXISTS protocols (
  id INTEGER PRIMARY KEY, name TEXT, template_path TEXT, template_hash TEXT,
  model_alias TEXT, k_repeats INTEGER, cli_version TEXT, notes TEXT,
  members_json TEXT,                                   -- [{provider, model, k_repeats}]
  scenario_selector TEXT,                              -- 'all' | 'seed' | '1,2,3'
  model_kind TEXT,                                     -- archived: 'binary' | 'gaussian' (NULL = binary)
  stages_json TEXT,                                    -- the two stages with their template hashes
  template_vars_json TEXT                              -- the resolved template variables
);
CREATE TABLE IF NOT EXISTS elicitations (
  id INTEGER PRIMARY KEY, scenario_id INTEGER, protocol_id INTEGER,
  repeat_ix INTEGER, prompt_hash TEXT, raw_response TEXT,
  valid INTEGER, error TEXT, created_at TEXT,
  provider TEXT, model TEXT,                           -- ensemble member identity
  stage TEXT                                           -- stage name (NULL in archived single-stage rows)
);
CREATE TABLE IF NOT EXISTS parameters (
  id INTEGER PRIMARY KEY, elicitation_id INTEGER, name TEXT,
  p5 REAL, p50 REAL, p95 REAL,
  unit TEXT,                                           -- archived: the units are fixed by the template now
  reasoning TEXT,
  dist_family TEXT, fit_params TEXT, fit_residual REAL, fit_warning INTEGER
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY, created_at TEXT, seed INTEGER, n_draws INTEGER,
  code_hash TEXT, protocol_id INTEGER,
  data_hash TEXT,                                      -- digest of the valid elicitations used
  members_json TEXT,                                   -- pooled member subset (NULL = all)
  weights TEXT                                         -- archived: 'equal-member' (NULL = pooled)
);
CREATE TABLE IF NOT EXISTS results (
  run_id INTEGER, scenario_id INTEGER, metric TEXT,
  q05 REAL, q25 REAL, q50 REAL, q75 REAL, q95 REAL,
  p_positive REAL                                      -- archived: new runs store probabilities as rows
);
CREATE TABLE IF NOT EXISTS sensitivities (
  run_id INTEGER, scenario_id INTEGER, param TEXT, spearman REAL
);
-- indexes
-- one valid elicitation per slot (scenario, protocol, member, repeat, stage);
-- the older index without the stage is replaced (a staged protocol stores a
-- decision and an instrument row of one member and repeat on one scenario)
DROP INDEX IF EXISTS ux_elicitations_valid_slot;
CREATE UNIQUE INDEX IF NOT EXISTS ux_elicitations_valid_slot_stage
  ON elicitations (scenario_id, protocol_id, provider, model, repeat_ix, COALESCE(stage, ''))
  WHERE valid=1;
