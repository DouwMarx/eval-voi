# SPEC — `voi-rank`

## v2 changes (2026-09-28)

The v1 spec below is kept verbatim as the record of what was built; v2 changes it in five places.

1. **Parameter `e` removed.** The model is `V(pi) = max(0, pi*B - (1-pi)*K)`, `EVPI = min(pB, (1-p)K)`, `voi(p, s, t, B, K)`. Six elicited parameters: `PARAM_NAMES = [p, s, t, B, K, C]`. `e` conflated compliance (part of the decision rule) with efficacy (part of `B`) while discounting only one branch; its global sensitivity in the v1 final run was small (|rho| 0.05 vs 0.40 for `C`). Validation requires exactly the six and silently ignores extra keys, so frozen v1 templates that still emit `e` keep validating; stored `e` rows are ignored by MC and analysis. `B` is now read as the benefit of a response that is actually taken.
2. **Provider ensembles.** A protocol lists `members: [{provider: claude_cli|openrouter, model, k_repeats}]` (legacy `model_alias` + `k_repeats` = one `claude_cli` member). Elicitation slot identity is (scenario, protocol, provider, model, repeat). Immutability compares the template hash and the member list. MC pools ALL valid (member, repeat) fits of a scenario into one equal-weight mixture per parameter (no per-member reweighting). The OpenRouter provider uses `urllib` only, reads `OPENROUTER_API_KEY` from the environment or the repo-root `.env`, and is never called unless a protocol names it.
3. **Study layout.** One study per directory under `studies/<name>/`: `scenarios.json`, `protocols/`, `templates/` (paths in protocol YAML are relative to the study root), `voi.db`, `report/`. Every CLI takes `--study PATH` (default `studies/business`); the v1 repository root layout (§11 below) moved to `studies/business/`, the code to the `voi_rank/` package. The schema gains `scenarios.context/grp/attributes`, `elicitations.provider/model`, `protocols.members_json`; `db.connect()` migrates v1 databases in place and back-fills legacy elicitations as `claude_cli` / the protocol's `model_alias`. `results` additionally stores the quantiles of the pooled `C` mixture.
4. **Context field.** A scenario may carry `context`, a factual background paragraph substituted into the template as `$context` (empty string when absent), plus `group` (figure colouring) and free-form `attributes` (e.g. `level`).
5. **Cost definition for evaluation studies.** In the eval studies (`ai-safety-evals`, `sim2real`) `C` is the total cost to build the evaluation from scratch (design, data or scene collection, hardware, engineering time) and run it once against the system under test; `B` and `K` are defined for the deployment decision. The business study keeps v1's per-measurement cost.

New figures: `fig_evsi_vs_cost` is the headline (q05-q95 EVSI bars, group colours), `fig_param_medians` (every elicited p50 per parameter vs rank, by member), `fig_by_level` (when scenarios carry `attributes.level`). Macros gain member counts and per-member validity and cost; health reports per-member validity, noise and cross-member Spearman agreement.

## v2.1: Gaussian-state family (2026-09-28)

A second protocol family, from the chapter (`chapter/main.tex`, sections "The linear-Gaussian model: sensors, estimation and control", "Action models: one state, one sensor, three decisions" and "An elicitation protocol for the Gaussian-state model"). Its purpose is an independent framing of EVSI on the same scenarios, as a sanity check on the binary model; the rank correlation between the two framings is the reported outcome. It changes nothing in the binary family.

1. **Model.** Continuous state `theta ~ N(mu0, sigma0^2)` in the expert's own unit, bad is high (the elicitor names the variable and unit and negates a bad-is-low variable). Sensor `y = theta + v`, `v ~ N(0, r)`; `x = sqrt(r)/sigma0`, `R^2 = 1/(1 + x^2)`, `sigma1^2 = sigma0^2 (1 - R^2)`, `sigtilde^2 = sigma0^2 R^2` (chapter eq. posterior, prepost). A half-normal common-mode bias `sigma_b` adds `sigma_b^2 (1 - 2/pi)` to `r` (chapter, "What monotonicity buys"), applied to every action model. Threshold `theta_c`, `d = (mu0 - theta_c)/sigma0`, `p = Phi(d)`. Loss exponent `k`, `L = c_k sigma0^k` = the minimal expected loss of acting on the prior alone (eq. lossfamily), i.e. under the optimal action, which asymmetric costs shift by a fixed multiple of `sigma0`. Four action models on every MC draw, all from the same draw of the state and sensor quantities: `quad` (`EVPI = L`, `EVSI = L (1 - (1 - R^2)^(k/2))`, eq. lossfamily, with the elicited `k`), `kg` (`EVSI = kappa sigtilde Psi(d/R)`, `EVPI = kappa sigma0 Psi(d)`, `Psi(z) = phi(z) - |z| Phi(-|z|)`, eq. kg), `step` (continuous signal, eq. stepcont, `EVPI = min(pB, (1-p)K)`) and `stepfix` (pass/fail at the fixed mark `theta_c`: `s = P(y > theta_c | theta > theta_c)`, `t = P(y <= theta_c | theta <= theta_c)`, bivariate-normal orthant probabilities with correlation `R` by Owen's T function, then the binary closed form `model.voi(p, s, t, B, K)`). Efficiency `eff_<m> = EVSI_<m>/C`; the primary metric is `eff_step`.
   *Deviation from the design:* `step` was specified as a 64-node Gauss-Hermite quadrature over `mu1 ~ N(mu0, sigtilde^2)`. The integrand `(Phi((mu1 - theta_c)/sigma1) - pi*)^+` tends to a step as `R^2 -> 1` and 64 nodes miss the integral by up to `1.8e-3 (B + K)` at `R^2 = 0.9`, `1.6e-2 (B + K)` (67% of the value) at `0.99` and `4.3e-2 (B + K)` (almost all of the value) at `0.999` (max over `d` in [-4, 4] at 0.005 steps; the error is spiky in `d`). The stored `EVSI_step` therefore uses the chapter's own identity that a pass/fail report at the decision-optimal cutoff `ybar* = mu0 + (theta_c + sigma1 Phi^-1(pi*) - mu0)/R^2` loses nothing: `EVSI_step` is the binary closed form at the orthant probabilities of that cutoff, exact to machine precision (`tests/test_gaussian.py` checks it against brute-force integration over `y` to `1e-8 (B + K)` and measures the quadrature's error). The quadrature stays as `gaussian.voi_step_gh` for the test.
2. **Questions** (template `templates/elicitor_gauss.md`, protocol `g001` in every study, reasoning before numbers, two anchors that are the binary anchors re-expressed as Gaussian answers). Q1 `theta` p5/p50/p95 -> `mu0 = p50`, `sigma0 = (p95 - p5)/3.29`, residual = asymmetry `|(p95-p50) - (p50-p5)|/(p95-p5)`. Q2a `theta_c`, Q2b `P(theta > theta_c)` -> `d` = mean of the two implied `d`'s, residual `|d_a - d_b|` in prior-sd units (a probability-scale residual is blind to a tail disagreement: `Q2b = 0.05` against a `theta_c` six sd out is 0.05 in probability but 4.4 sd, review round 2; `Q2b - Phi(d_a)` is written into the `g_d` reasoning for the spot-read). Q3a test-retest `W_rr` -> `r_a = (W_rr/(1.645 sqrt 2))^2`; Q3b width after the result `W1`, from the random error alone -> `sigma1 = W1/3.29`, `r_b = sigma0^2 sigma1^2/(sigma0^2 - sigma1^2)` (validation rejects `sigma1 >= sigma0`); Q3c probability `c` that the random error of the result moves the estimate by more than `U/2`, `U = 1.645 sigma0` -> `sigtilde = (U/2)/Phi^-1(1 - c/2)`, `r_c = sigma0^2 (sigma0^2/sigtilde^2 - 1)` (a Gaussian sensor bounds `c` below `C_MOVE_MAX = 2 (1 - Phi(1.645/2)) = 0.4108`, where `sigtilde = sigma0`; the route is dropped with a warning when `c > C_MOVE_DROP = 0.40`, since within 0.01 of the bound a two-decimal `c` no longer resolves `x`: `x_c` = 0.22 at 0.40, 0.06 at 0.41); `x = exp(median log(sqrt(r_i)/sigma0))` over the valid routes (the mean of two), so one coarse route cannot move `x` alone; residual = std of the log `x`'s. All three routes estimate the same random error `r`: the template tells the elicitor to leave the systematic error out of `W1` and `c` (it is Q7), so `sigma_b` enters once, through `R^2 = 1/(1 + x^2 + (sigma_b/sigma0)^2 (1 - 2/pi))`, and is not counted again inside `r_b`, `r_c` (review round 2; the chapter says only that route a is blind to it). Q4 `L1m, L2m` (under-response by 1 and 2 `sigma0`), `L1p, L2p` (over-response) -> `k_side = log2(L2/L1)`, `k` = mean clipped to `[0.5, 4]`, residual `|k_m - k_p|`, `L = min over m of [L1m M_k(m) + L1p M_k(-m)]` with `M_k(m) = E[(z - m)^+^k] = Gamma(k+1) exp(-m^2/4) D_{-(k+1)}(m)/sqrt(2 pi)` (`gaussian.min_expected_loss`, one bounded scalar minimisation per elicitation; `L1m = c_- sigma0^k`, `L1p = c_+ sigma0^k`, so `L = c_k sigma0^k` is the chapter's minimal loss and `EVPI_quad`; it reduces to `0.5 (L1m + L1p) E|z|^k`, the loss of acting at the mean, only for symmetric costs, and the optimal shift `m*` is written into the `g_L` reasoning). Q5 `kappa sigma0` (USD). Q6 `B`, `K` (USD, single values). Q7 `sigma_b` (state unit, 0 allowed) -> `sigma_b/sigma0`. Q8 `C` p5/p50/p95 (lognormal). Validation (`gauss_fit.validate_gauss_payload`, errors prefixed `schema:` / `constraint:` / `fit:`): a `state` block with non-empty `variable`, `unit` and `bad_is_high: true`; theta triple strictly increasing; Q2b and `c` in (0.001, 0.999); `W_rr`, `W1 > 0`; `W1 < p95 - p5`; the four losses > 0 with `L2 >= L1` per side; `kappa sigma0`, `B`, `K > 0`; `sigma_b >= 0`; `C` triple increasing and > 0.
3. **Storage.** Protocol YAML gains `model: binary | gaussian` (default binary), stored in `protocols.model_kind` (added by the `V2_COLUMNS` migration, NULL = binary) and part of the immutability check. Per valid elicitation the `parameters` table holds `GAUSS_PARAM_NAMES = [g_mu0, g_sigma0, g_d, g_x, g_k, g_L, g_kappa_sigma0, g_B, g_K, g_sigma_b_rel, C]`: the first ten with `dist_family = 'point'`, `fit_params {"value": v}`, `p5 = p50 = p95 = v`, `fit_residual` = the residual of the questions behind the row (asymmetry on `g_mu0`/`g_sigma0`, `d` mismatch on `g_d`, route spread on `g_x`, `k` mismatch on `g_k`/`g_L`, 0 elsewhere) and `fit_warning` when it exceeds its threshold (0.25, 0.5 in prior-sd units, 0.5 in log units, 1.0) or a route was dropped; `C` as the usual lognormal. The per-elicitation consistency score (max residual / threshold) is derived at analysis time (`gauss_fit.consistency_score`), not stored. `PARAM_NAMES` stays the binary list; `db.param_names(kind)`, `db.primary_metric(kind)` (`efficiency` / `eff_step`) and `db.evsi_metric(kind)` dispatch. `mc.sample_mixture` draws a `point` family as a constant (the mixture over repeats is the empirical distribution of the repeat values); `data_hash` and the replay guard are unchanged in form and use `eff_step` for a Gaussian run.
4. **Metrics** (`gaussian.METRIC_NAMES`): `EVSI_<m>`, `EVPI_<m>`, `eff_<m>` for `m` in quad, kg, step, stepfix; `R2, d, x, k, p_derived, s_derived, t_derived, C`; `p_positive = P(EVSI_step > C)`; sensitivities = Spearman against `eff_step` of every quantity that enters the metrics (`gaussian.METRIC_INPUTS` via `db.sensitivity_names`: all but `g_mu0` and `g_sigma0`, which no action model reads, so their rho would be sampling noise or NULL; the two stay in the noise and catalog tables); `p_top10` on `eff_step`. `figures`/`tables` run on a Gaussian run with the run's primary metric and parameter names (`fig_headroom` is skipped, the catalog lists the derived quantities); `extra` skips its binary-only analyses (level uplift, within-group consistency, member agreement, simplicity) with a printed reason and restricts the matched-k noise table to binary protocols; the cross-protocol Spearman matrices correlate each run on its own primary metric.
5. **Comparison** (`voi_rank.analysis.compare_models --study PATH [--binary p001] [--gaussian g001]`, over the scenarios ranked by both latest runs): `compare_models.tex` (Spearman and Kendall of median efficiency, binary vs each action model and among the four, top-10 overlaps; the gate-agreement confusion table between binary median EVSI = 0 and stepfix median EVSI = 0), `fig_compare_models.pdf` (binary vs stepfix efficiency, log-log, iso line, by group), `fig_derived_pst.pdf` (derived `p = Phi(d)`, `s`, `t` vs the binary protocol's pooled elicited p50 with Spearman and median absolute difference), `consistency_gauss.tex` (residual quantiles per quantity, fraction flagged, Spearman with the cross-repeat spread of the quantity checked, the consistency-score distribution) and `macros_compare.tex` (`\voiGaussRhoQuad`, `\voiGaussRhoKg`, `\voiGaussRhoStep`, `\voiGaussRhoStepfix`, `\voiGaussTopOverlapStepfix`, `\voiGaussRhoP`, `\voiGaussRhoS`, `\voiGaussRhoT`, `\voiGaussGateAgree`, `\voiGaussN`, plus the Kendall and top-overlap macros of the other models and the run ids).

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
