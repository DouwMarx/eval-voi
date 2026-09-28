# SPEC — `voi-rank`

## v2 changes (2026-09-28)

The v1 spec below is kept verbatim as the record of what was built; v2 changes it in five places.

1. **Parameter `e` removed.** The model is `V(pi) = max(0, pi*B - (1-pi)*K)`, `EVPI = min(pB, (1-p)K)`, `voi(p, s, t, B, K)`. Six elicited parameters: `PARAM_NAMES = [p, s, t, B, K, C]`. `e` conflated compliance (part of the decision rule) with efficacy (part of `B`) while discounting only one branch; its global sensitivity in the v1 final run was small (|rho| 0.05 vs 0.40 for `C`). Validation requires exactly the six and silently ignores extra keys, so frozen v1 templates that still emit `e` keep validating; stored `e` rows are ignored by MC and analysis. `B` is now read as the benefit of a response that is actually taken.
2. **Provider ensembles.** A protocol lists `members: [{provider: claude_cli|openrouter, model, k_repeats}]` (legacy `model_alias` + `k_repeats` = one `claude_cli` member). Elicitation slot identity is (scenario, protocol, provider, model, repeat). Immutability compares the template hash and the member list. MC pools ALL valid (member, repeat) fits of a scenario into one equal-weight mixture per parameter (no per-member reweighting). The OpenRouter provider uses `urllib` only, reads `OPENROUTER_API_KEY` from the environment or the repo-root `.env`, and is never called unless a protocol names it.
3. **Study layout.** One study per directory under `studies/<name>/`: `scenarios.json`, `protocols/`, `templates/` (paths in protocol YAML are relative to the study root), `voi.db`, `report/`. Every CLI takes `--study PATH` (default `studies/business`); the v1 repository root layout (§11 below) moved to `studies/business/`, the code to the `voi_rank/` package. The schema gains `scenarios.context/grp/attributes`, `elicitations.provider/model`, `protocols.members_json`; `db.connect()` migrates v1 databases in place and back-fills legacy elicitations as `claude_cli` / the protocol's `model_alias`. `results` additionally stores the quantiles of the pooled `C` mixture.
4. **Context field.** A scenario may carry `context`, a factual background paragraph substituted into the template as `$context` (empty string when absent), plus `group` (figure colouring) and free-form `attributes` (e.g. `level`).
5. **Cost definition for evaluation studies.** In the eval studies (`ai-safety-evals`, `sim2real`) `C` is the total cost to build the evaluation from scratch (design, data or scene collection, hardware, engineering time) and run it once against the system under test; `B` and `K` are defined for the deployment decision. The business study keeps v1's per-measurement cost.

New figures: `fig_evsi_vs_cost` is the headline (q05-q95 EVSI bars, group colours), `fig_param_medians` (every elicited p50 per parameter vs rank, by member), `fig_by_level` (when scenarios carry `attributes.level`). Macros gain member counts and per-member validity and cost; health reports per-member validity, noise and cross-member Spearman agreement.

---

# SPEC — `voi-rank` v1 (as built)

**Audience:** an implementing agent (Claude Code) building this from scratch.
**One-line goal:** rank scenarios by the value of a *single measurement* sold to a *single agent* facing a *single decision*, using the canonical Bayesian decision problem, with all parameters elicited by LLM (Large Language Model) calls and all uncertainty propagated by Monte Carlo (MC).

This spec is intentionally minimal. Do not add features, parameters, or abstractions beyond what is written here. When in doubt, choose the simpler implementation and record the doubt in `LEARNINGS.md`.

---

## 1. Scope: frozen decisions

**Unit of analysis:** one measurement → one agent → one decision. The product is *the piece of information*, not a business.

**In scope (v1):**
- Binary state, binary signal, binary action; 7 elicited parameters per scenario.
- Closed-form EVSI (Expected Value of Sample Information) and EVPI (Expected Value of Perfect Information); MC only over elicitation uncertainty.
- Elicitation via `claude -p` headless with the `haiku` model, k repeats per scenario.
- SQLite storage with full provenance.
- Sensitivity analysis (which parameters drive the ranking).
- A proposer agent that generates many scenarios from seed domains. **No dedupe** — scenario text is its identity; duplicates are acceptable.
- A complete compiled LaTeX report with figures.
- An explicit iteration loop: run batches, analyze, revise prompts, re-run, log learnings.

**Explicitly deferred (do not implement, do not leave hooks beyond a comment):** capture fraction, number of buyers, annualization/recurrence, rivalry, compliance/stamp demand, risk aversion, parameter correlations, retrodiction validation set, POMDPs, multi-valued states or signals, dedupe.

**Interpretation caveat (state it in the report):** with capture and buyer count removed, the ranking measures *per-measurement decision-value density* (how much one observation is worth to one decision-maker per dollar it costs to produce), not business feasibility.

---

## 2. Model

### 2.1 Structure

- Latent state θ ∈ {0, 1}. Convention: **θ = 1 is the state in which responding is the correct action.**
- Signal x ∈ {0, 1} produced by the instrument.
- Action a ∈ {0, 1}: respond / don't respond. The policy is **derived** (argmax over posterior expected utility), never elicited.
- Utilities in the regret parameterization, baseline u(θ, a=0) = 0 for both θ.

### 2.2 The seven elicited parameters

| # | Symbol | Meaning | Support | Distribution family |
|---|--------|---------|---------|---------------------|
| 1 | p | Prior P(θ=1), given everything the agent already knows for free | [0,1] | Beta |
| 2 | s | Sensitivity P(x=1 \| θ=1) | [0,1] | Beta |
| 3 | t | Specificity P(x=0 \| θ=0) | [0,1] | Beta |
| 4 | e | Action efficacy: P(agent acts on the signal) × P(the action works) | [0,1] | Beta |
| 5 | B | Benefit of a correct response, u(1,1) − u(1,0) | USD > 0 | Lognormal |
| 6 | K | False-alarm cost, u(0,0) − u(0,1) | USD > 0 | Lognormal |
| 7 | C | Cost to produce and deliver one measurement | USD > 0 | Lognormal |

Each parameter is elicited as (p5, p50, p95) percentiles plus a short reasoning string and unit.

### 2.3 Closed forms (implement exactly; these are the whole inner model)

```
V(pi)   = max(0, pi*e*B - (1-pi)*K)          # value of acting optimally at belief pi
P1      = p*s + (1-p)*(1-t)                  # P(x=1)
P0      = 1 - P1
pi1     = p*s / P1                           # posterior after x=1
pi0     = p*(1-s) / P0                       # posterior after x=0
EVSI    = P1*V(pi1) + P0*V(pi0) - V(p)
EVPI    = min(p*e*B, (1-p)*K)
```

Guard division by zero (P1 or P0 = 0 → that branch contributes 0).

### 2.4 Derived per-scenario metrics (computed on every MC draw)

- `EVSI` (USD per measurement)
- `EVPI` (USD per measurement)
- `efficiency = EVSI / C` (dimensionless; **primary ranking metric**, ranked by median)
- `evpi_efficiency = EVPI / C` (v2: the simpler perfect-information ranking, summarised by the same per-draw median as `efficiency` so the two rankings compare without an estimator difference)
- `margin = EVSI - C` (USD)
- `p_positive = P(EVSI > C)` across draws (report alongside the ranking; a high-efficiency scenario with low p_positive is fragile)
- `headroom = EVSI / EVPI` where EVPI > 0 (how much of the perfect-information value this instrument delivers; diagnostic for instrument quality)

---

## 3. Distribution fitting (percentiles → distribution)

Input: (q05, q50, q95) with hard validation q05 < q50 < q95.

- **Lognormal** (B, K, C): initialize μ = ln q50, σ = (ln q95 − ln q05) / (2 × 1.6449). Then least-squares refine (μ, σ) against all three quantiles with `scipy.optimize`. If the log-asymmetry |(ln q95 − ln q50) − (ln q50 − ln q05)| / (ln q95 − ln q05) > 0.25, keep the least-squares fit but set a `fit_warning` flag on the elicitation row.
- **Beta** (p, s, t, e): clip quantiles to [1e-6, 1−1e-6]. Initialize (α, β) by method of moments with mean = q50 and sd = (q95 − q05)/3.29 (clip sd to the valid Beta range). Least-squares refine against the three quantiles. Store fit residual; flag if residual > 0.02.

Store fitted parameters and residuals in the DB; never re-fit silently at analysis time.

---

## 4. Monte Carlo and sensitivity

- Default M = 100,000 draws per scenario. All seven parameters drawn **independently** (a stated v1 assumption — note it in the report's limitations).
- Vectorized NumPy; seeded `numpy.random.default_rng(seed)`; the seed is stored in the `runs` table. No sampling libraries needed.
- Per-scenario metric summaries: q05, q25, q50, q75, q95 and `p_positive`, written to `results`.
- **Sensitivity, local:** for each scenario, Spearman rank correlation between each parameter's draw vector and the `efficiency` draw vector. Store all seven ρ values per scenario in `sensitivities`.
- **Sensitivity, global:** aggregate |ρ| over the top-quartile scenarios by median efficiency → "which parameters most control the top of the ranking." This is the target list for prompt refinement in the iteration loop (§10).
- **Rank stability:** using the MC draws directly, compute P(scenario ∈ top 10 by efficiency) by comparing draws across scenarios (align draw indices; with independent scenarios this is a bootstrap over joint draws). Report per scenario.
- **Elicitation noise:** per parameter, the spread of p50 across the k repeats (max−min relative to the pooled p50). Complementary critique-routing signal to Spearman.

---

## 5. Storage: SQLite

One file, `voi.db`. Append-only for `scenarios` and `elicitations` (never UPDATE elicited data; supersede with new rows under a new protocol).

```sql
CREATE TABLE scenarios (
  id INTEGER PRIMARY KEY, created_at TEXT, title TEXT,
  agent TEXT, decision TEXT, theta_definition TEXT, instrument TEXT,
  domain_tags TEXT, source TEXT, raw_json TEXT
);
CREATE TABLE protocols (
  id INTEGER PRIMARY KEY, name TEXT, template_path TEXT, template_hash TEXT,
  model_alias TEXT, k_repeats INTEGER, cli_version TEXT, notes TEXT
);
CREATE TABLE elicitations (
  id INTEGER PRIMARY KEY, scenario_id INTEGER, protocol_id INTEGER,
  repeat_ix INTEGER, prompt_hash TEXT, raw_response TEXT,
  valid INTEGER, error TEXT, created_at TEXT
);
CREATE TABLE parameters (
  id INTEGER PRIMARY KEY, elicitation_id INTEGER, name TEXT,
  p5 REAL, p50 REAL, p95 REAL, unit TEXT, reasoning TEXT,
  dist_family TEXT, fit_params TEXT, fit_residual REAL, fit_warning INTEGER
);
CREATE TABLE runs (
  id INTEGER PRIMARY KEY, created_at TEXT, seed INTEGER, n_draws INTEGER,
  code_hash TEXT, protocol_id INTEGER
);
CREATE TABLE results (
  run_id INTEGER, scenario_id INTEGER, metric TEXT,
  q05 REAL, q25 REAL, q50 REAL, q75 REAL, q95 REAL, p_positive REAL
);
CREATE TABLE sensitivities (
  run_id INTEGER, scenario_id INTEGER, param TEXT, spearman REAL
);
```

`prompt_hash` = SHA-256 of the fully rendered prompt string. `code_hash` = git HEAD of the code paths (`voi_rank/`, `pyproject.toml`, `uv.lock`), suffixed `-dirty` when any of them has uncommitted changes (v2: `mc` refuses such a tree unless `--allow-dirty`; a modified `voi.db` does not count, study inputs being frozen by `template_hash` and `prompt_hash`). `data_hash` (v2 column on `runs`) = SHA-256 over the sorted (elicitation id, parameter name, `fit_params`) of the valid elicitations the run drew from. `cli_version` = output of `claude --version`.

---

## 6. Elicitation harness (`claude -p`, model = haiku)

### 6.1 Invocation

```bash
claude -p "$(python render.py elicitor <scenario_id>)" \
  --bare \
  --model haiku \
  --output-format json \
  --max-turns 2
```

- `--bare` skips loading hooks, skills, `CLAUDE.md`, MCP (Model Context Protocol) servers, etc., so the elicitation prompt is the *only* context — required for reproducibility. If the installed CLI predates `--bare`, run from an empty scratch directory instead and note it in `LEARNINGS.md`.
- Parse the JSON envelope from stdout; the model's answer is in the `result` field; also record `total_cost_usd` and `session_id` when present.
- Verify all flags against `claude --help` before first use; the reference is https://code.claude.com/docs/en/headless. Do not assume flags this spec did not verify.
- Temperature is not controllable from the CLI: **repeats are the noise model.** Default k = 3 repeats per scenario (raise to 5 during protocol experiments).

### 6.2 Templates and protocols

- Prompt templates are plain files: `elicitation/templates/proposer.md`, `elicitation/templates/elicitor.md`. Rendered with Python `string.Template` or f-strings — no template engine dependency.
- A protocol is a YAML file `elicitation/protocols/p001.yaml`: `{name, template_path, model_alias: haiku, k_repeats: 3, notes}`. Every elicitation row references a protocol id; changing a template means a **new** protocol file, never editing an old one.

### 6.3 Elicitor prompt requirements (`elicitor.md`)

Must contain, in order:
1. The model definition of §2 in ~10 lines, including the θ=1 convention and the meaning of each parameter.
2. **Two fully worked anchor scenarios with agreed numbers**, to pin scales across scenarios (a ranking depends on cross-scenario scale consistency far more than on absolute accuracy). Anchor A1, use verbatim:
   - *Scenario:* A plant reliability engineer decides whether to pull a critical gearbox for overhaul. θ=1 = an incipient bearing fault is present. Instrument = one third-party vibration-analysis survey.
   - p: 0.02 / 0.08 / 0.25 — s: 0.60 / 0.80 / 0.95 — t: 0.70 / 0.90 / 0.98 — e: 0.50 / 0.80 / 0.95 — B (avoided unplanned failure minus planned repair): 20e3 / 150e3 / 1.5e6 USD — K (unnecessary teardown + downtime): 2e3 / 10e3 / 6e4 USD — C: 300 / 1e3 / 5e3 USD.
   - Write anchor A2 yourself from a different domain (e.g., a diagnostic lab test) with similarly defended numbers, and keep it fixed across all protocols.
3. The scenario under elicitation (agent, decision, θ definition, instrument).
4. Instructions per parameter: one short paragraph of reasoning **first**, then p5/p50/p95, then unit. Reasoning-before-numbers; percentiles framed as "you'd be surprised if the true value fell outside [p5, p95]."
5. The prior instruction: p must already reflect all information the agent has *without* buying this measurement (free substitutes live inside the prior).
6. Output contract: **strict JSON only, no markdown fences, no prose outside JSON**, matching:

```json
{
  "parameters": {
    "p": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "probability"},
    "s": {}, "t": {}, "e": {},
    "B": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "USD"},
    "K": {}, "C": {}
  }
}
```

### 6.4 Validation of elicitations (reject → one retry → mark invalid)

- Parses as JSON matching the schema (strip markdown fences if present before failing).
- Monotone percentiles for every parameter; probabilities in (0,1); B, K, C > 0.
- Informativeness: median s > 1 − median t (else the signal is useless or the model swapped sensitivity/specificity — the most likely silent-corruption bug).
- Non-degenerate prior: p50 of p in [0.001, 0.999].
Store raw response always, even for invalid rows; store the failure reason in `error`.

### 6.5 Proposer prompt requirements (`proposer.md`)

- Input: a seed domain (see §7) and a count n.
- Output: strict JSON list of scenarios `{title, agent, decision, theta_definition, instrument, domain_tags}`.
- Constraints stated in the prompt: one concrete decision-maker (not "society"); θ must be a binary fact about the world checkable in principle; the instrument must be a purchasable measurement, not advice; vary stakes deliberately from small (hundreds of USD) to catastrophic.
- No dedupe. Insert everything.

---

## 7. Scenario seeding

Hand-write these 8 starter scenarios in `scenarios/seed.json` (they double as smoke tests):
1. Vibration survey before pulling a critical gearbox (= anchor A1).
2. Pre-employment ergonomic screening before hiring a warehouse worker (agent: site manager; θ=1: applicant at high injury risk in this role).
3. Dangerous-capability evaluation of a frontier AI model before deployment (agent: lab deployment lead; θ=1: model materially uplifts bio misuse).
4. Standardized manipulation benchmark of a warehouse robot before a fleet purchase (agent: logistics buyer; θ=1: robot underperforms spec in situ).
5. Soil pathogen assay before planting a high-value crop (agent: farm operator).
6. Structural inspection before purchasing a used mobile crane (agent: plant buyer).
7. Sepsis-risk panel for a newly admitted patient (agent: attending physician; θ=1: early sepsis present).
8. Counterparty credit report before extending 90-day trade credit (agent: CFO of a supplier).

Then use the proposer with seed domains: industrial injury categories, agriculture, construction, medicine, transport, energy, AI/robotics evaluation, finance/credit, environmental monitoring, consumer durables. Target **≥ 50 scenarios** in the first full sweep; more is encouraged — haiku elicitations are cheap and the whole point is breadth.

---

## 8. Analysis and figures

`analysis/figures.py` produces PDF figures via matplotlib (no seaborn), reading only from `voi.db`:

1. `fig_ranking.pdf` — top 25 scenarios by median efficiency; horizontal interval plot (q05–q95), log-scale x.
2. `fig_evsi_vs_cost.pdf` — median EVSI vs median C, log–log scatter, iso-efficiency diagonals, points labeled for the top 10.
3. `fig_sensitivity_heatmap.pdf` — |Spearman ρ|, parameters × scenarios (scenarios ordered by rank).
4. `fig_headroom.pdf` — median EVSI/EVPI per scenario vs rank (where is a better instrument worth building?).
5. `fig_rank_stability.pdf` — P(scenario ∈ top 10) per scenario.
6. `fig_elicitation_noise.pdf` — cross-repeat p50 spread per parameter, aggregated over scenarios.
7. `fig_top5_densities.pdf` — efficiency densities for the top 5 scenarios.

`analysis/make_tables.py` writes LaTeX table fragments to `report/generated/` (scenario catalog with elicited medians; final ranking table with q05/q50/q95, p_positive, top sensitive parameter).

---

## 9. LaTeX report (required deliverable)

`report/main.tex`, compiled with `latexmk -pdf` to `report/main.pdf`. It must compile from a clean checkout after `analysis/figures.py` and `analysis/make_tables.py` have run. Sections:

1. **Introduction** — the framing: information as a product; one measurement, one agent, one decision.
2. **Model** — §2 with a derivation of the EVSI and EVPI closed forms (short; the EVPI = min(peB, (1−p)K) identity deserves its two lines of algebra) and one influence-diagram figure (TikZ: θ → x → a → utility, with e on the a→outcome edge).
3. **Method** — elicitation protocol, anchors, fitting, MC, sensitivity. Include the exact prompt template in an appendix.
4. **Scenario catalog** — generated table.
5. **Results** — ranking figure + table; EVSI-vs-cost scatter; commentary on the top 10 written by inspecting the reasoning strings stored in the DB.
6. **Sensitivity and elicitation quality** — heatmap, noise, rank stability; state which parameters dominate and what that implies for where estimation effort should go next.
7. **Limitations** — independence assumption; per-measurement (not business) interpretation; haiku as elicitor (small-model calibration risk, mitigated by anchors and repeats — show evidence either way); everything in the deferred list of §1.
8. **Learnings** — distilled from `LEARNINGS.md`: what changed across protocol iterations and what effect it had.

No invented numbers anywhere: every figure and table is generated from `voi.db`.

---

## 10. Iteration protocol (this is a first-class requirement, not cleanup)

Experiment heavily. Haiku headless calls are cheap; treat elicitation prompts as the experimental variable and the DB as the lab notebook's data layer.

Loop, repeated at least 3 times before the final report run:
1. Run a batch (all scenarios × k repeats) under protocol pNNN.
2. Compute the health checks: JSON validity rate (target ≥ 95%), constraint pass rate, cross-repeat spread per parameter, fraction of scenarios with median EVSI ≈ 0, count of `fit_warning`s, spot-read 5 reasoning strings for unit errors (the classic failure: B elicited as a total-market number instead of per-decision).
3. Identify the worst problem. Change **one thing** in the template (an instruction, an anchor, the percentile framing). Save as a new protocol file.
4. Re-run the *same* scenario set under the new protocol; compare health checks and rank correlation (Spearman) between protocols — if the ranking is unstable across protocol tweaks, that is itself a headline finding for the report.
5. Append a dated entry to `LEARNINGS.md`: hypothesis → change → observed effect → keep/revert.

Sensitivity-guided deepening: after a healthy full sweep, take the globally most sensitive parameters (§4) among top-quartile scenarios and re-elicit only those with a focused prompt variant; measure whether intervals tighten and ranks stabilize.

---

## 11. Repository layout

```
voi-rank/
  spec.md                      # this file
  core/model.py                # §2 closed forms, vectorized
  core/fit.py                  # §3
  core/mc.py                   # §4 draws + metrics
  core/sensitivity.py          # §4 Spearman, stability, noise
  db/schema.sql                # §5
  db/io.py
  elicitation/templates/{proposer.md, elicitor.md}
  elicitation/protocols/p001.yaml
  elicitation/run_elicit.py    # subprocess claude -p; §6
  elicitation/run_propose.py
  scenarios/seed.json          # §7
  analysis/{figures.py, make_tables.py}
  report/{main.tex, generated/}
  tests/test_model.py
  LEARNINGS.md
  README.md                    # 20 lines: install, run order, where outputs land
```

Dependencies: numpy, scipy, matplotlib, pyyaml, pytest. Nothing else. Python ≥ 3.11. The `claude` CLI must be installed and authenticated in the environment.

---

## 12. Milestones and acceptance criteria

- **M0 — core math.** `tests/test_model.py` passes: closed-form EVSI matches brute-force enumeration over (θ, x) to 1e-12 on 1,000 random parameter draws; EVSI = 0 when s = 1 − t; EVSI = EVPI when s = t = 1; 0 ≤ EVSI ≤ EVPI always.
- **M1 — end-to-end on seeds.** Fit + MC + metrics for the 8 hand-written scenarios using hand-entered percentiles; ranking prints; figures 1–2 render.
- **M2 — elicitation live.** Harness runs haiku on the 8 seeds, k = 3; validity rate ≥ 95%; DB rows carry prompt hashes and raw responses.
- **M3 — sweep.** Proposer generates to ≥ 50 scenarios; full batch elicited and ranked; all figures render.
- **M4 — iteration.** ≥ 3 protocol iterations completed with `LEARNINGS.md` entries and cross-protocol rank correlations recorded.
- **M5 — report.** `report/main.pdf` compiles clean, all figures and tables generated from the DB, limitations and learnings sections substantive.

Definition of done = M5 plus: a fresh clone can reproduce the final run from `README.md` instructions given the DB (elicitations are not expected to be bit-reproducible; everything downstream of the DB is, given the stored seed).
