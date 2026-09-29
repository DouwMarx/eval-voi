# Methods shared by the two SPAIS papers

Written 2026-09-29 against code revision `98af5ee` (`git rev-parse HEAD` in `voi-rank/`), CLI `2.1.280 (Claude Code)` for the eval studies and `2.1.220` for the business v1 batches (`protocols.cli_version`). Every number below carries the query, script or macro that reproduces it. Studies: `studies/business` (68 scenarios), `studies/ai-safety-evals` (track 1, 15), `studies/sim2real` (track 2, 15). The business `g001` elicitation was still being filled by the operator while this was written; its counts are timestamped and it has no run.

## 0. How to reproduce a number

Three kinds of reference are used.

- `[sql]` blocks open the study database read-only. Pattern, run from the repo root with `uv run python`:

```python
import sqlite3
from voi_rank import db          # only pure helpers are used: db.envelope_cost, db.PARAM_NAMES
con = sqlite3.connect('file:studies/<study>/voi.db?mode=ro', uri=True); con.row_factory = sqlite3.Row
```

- `[copy]` blocks run a package CLI (`health`, `compare_models`, `tables` helpers). `db.connect()` migrates a database in place, so they run on a copy of the study, never on `studies/<name>` itself:

```bash
T=/tmp/voi_methods
for s in business ai-safety-evals sim2real; do
  mkdir -p $T/$s && cp -r studies/$s/protocols studies/$s/templates studies/$s/scenarios.json $T/$s/
  python3 -c "import sqlite3; s=sqlite3.connect('file:studies/$s/voi.db?mode=ro', uri=True); d=sqlite3.connect('$T/$s/voi.db'); s.backup(d)"
done
uv run python -m voi_rank.analysis.health --study $T/<study> --protocol <p> [--members claude_cli:sonnet,claude_cli:opus]
```

  `health` prints: attempt counts by outcome, JSON validity, slot validity, per-member attempts / valid / cost, the cross-elicitation p50 spread per parameter (median over scenarios), per-member spreads, cross-member Spearman of pooled p50, fit warnings, and the zero-median count of the protocol's latest run (of the subset when `--members` is given). Below, `[health <study> <protocol> [members]]` names that print.

- `[macro]` names a `\newcommand` in `studies/<study>/report/generated/{macros,macros_extra,macros_compare}.tex` or a cell of a generated table there. The eval studies' generated directories currently hold `macros.tex` from the `p001` run (run 1) and `plugin.tex`, `simplicity.tex`, `member_agreement.tex` from the sonnet+opus subset runs (run 5 of p003 for ai-safety-evals, run 12 of p004 for sim2real), while `macros_compare.tex` and `compare_models.tex` come from runs 5 vs 6 (p003 vs g001, sonnet+opus) in both (`\voiGaussBinaryRunId`, `\voiGaussRunId`): a paper must not cite `\voiRunId` and `\voiPluginInGate` as one run.

Chapter references are to `../chapter/main.tex` (next to `voi-rank/`) by label: `sec:binary` (line 189), `sec:gate` (235), `sec:fence` (282), `sec:limits` (340), `sec:gauss` (512), `sec:action` (608), `sec:protocol` (683); `grep -n 'label{sec:' ../chapter/main.tex`.

## 1. The model

### 1.1 Six parameters, closed forms, efficiency

One agent, one binary decision (respond `a=1` or not), one hidden binary state `theta` (`theta=1` is the state in which responding is correct), one purchasable binary signal `x`. Regret form: `u(theta,0)=0`, `u(1,1)=B`, `u(0,1)=-K`. Six elicited parameters, each as `(p5, p50, p95)` with a reasoning string (`voi_rank/fit.py: FAMILY_BY_PARAM`):

| symbol | meaning | support | fitted family |
|---|---|---|---|
| p | prior P(theta=1) given everything the agent knows for free | (0,1) | Beta |
| s | sensitivity P(x=1 given theta=1) | (0,1) | Beta |
| t | specificity P(x=0 given theta=0) | (0,1) | Beta |
| B | benefit of a correct response, USD, one decision | >0 | lognormal |
| K | cost of a false-alarm response, USD, one decision | >0 | lognormal |
| C | cost of the measurement, USD | >0 | lognormal |

Closed forms (`voi_rank/model.py: voi`, chapter eq. `evsi_binary`, `evpi_binary`):

```
V(pi)  = max(0, pi B - (1-pi) K) = Lam [pi - pi*]^+,   Lam = B + K,  pi* = K / Lam
P1     = p s + (1-p)(1-t),  P0 = 1 - P1,  pi1 = p s / P1,  pi0 = p (1-s) / P0
EVSI   = P1 V(pi1) + P0 V(pi0) - V(p)
EVPI   = min(p B, (1-p) K)
eff    = EVSI / C              (primary ranking metric; chapter eq. eff)
```

`eff = (Lam / C) g(p, pi*, s, t)`: five dimensionless quantities decide the order, the absolute dollar scale never enters (chapter `sec:dimensionless`). The v1 efficacy multiplier `e` is gone (section 3.1).

`C` in the eval studies is the total cost to build the evaluation from scratch and run it once against the system under test (design, data or scene collection, hardware, engineering time), not the marginal cost of a repeat (template `studies/ai-safety-evals/templates/elicitor.md`, parameter list and "Remember for C"; `spec.md` v2 item 5). The business study keeps v1's cost per delivered measurement (`studies/business/templates/elicitor.md`). `B` and `K` in the eval studies are defined for the deployment decision (delay / gate / mitigate against deploy as planned).

Monte Carlo (`voi_rank/mc.py`): each parameter of a scenario is an equal-weight mixture over the fitted distributions of every valid (member, repeat) elicitation (`sample_mixture`), drawn independently, 100,000 draws, seed 42; per-draw metrics `EVSI, EVPI, efficiency, margin, headroom, C, evpi_efficiency` summarised by q05..q95 and `p_positive = P(EVSI > C)`; Spearman of each parameter's draws against `efficiency` per scenario (local sensitivity); `p_top10` over aligned draws.

### 1.2 The gate

For an informative sensor (`s + t > 1`) the posteriors bracket the prior, `pi0 < p < pi1`, and EVSI is positive only when the threshold sits strictly between them, `pi0 < pi* < pi1`; otherwise the agent takes the same action whatever the reading and EVSI is exactly zero (chapter `sec:gate`, three cases). Inside the gate there are two regimes: `p <= pi*` (default is not to respond) gives `EVSI = p s B - (1-p)(1-t) K` (eq. `regA`); `p >= pi*` gives `EVSI = (1-p) t K - p (1-s) B` (eq. `regB`). The gate is a yes/no question that needs no numbers ("would a positive reading make the agent respond and a negative one hold off?") and it is where every zero of the study comes from: 13 of 68 business scenarios have median EVSI 0 (`[macro] \voiZeroEvsiCount`, run 18), 9/15 and 11/15 in the haiku `p001` runs of the eval studies (`[macro] \voiZeroEvsiCount` in each study). Because EVSI is not monotone in `p`, `B` or `K` (chapter, Proposition "Not monotone"), a small shift of a prior nobody can pin to a factor of two flips a draw out of the gate, which makes the MC median knife-edged near it (chapter `sec:limits`, items 1 and 2).

### 1.3 The buyer on the fence

Hold the stakes `Lam` fixed and vary the threshold `pi*`, that is, how the stakes split between `B` and `K`. EVSI is maximised at `pi* = p`, with value `EVSI* = Lam p (1-p) (s + t - 1)` (chapter Proposition `prop:fence`, eq. `fence`): stakes times the Bernoulli variance of the state times Youden's index. It is smooth in every input, strictly positive whenever the sensor is informative, additive in logs, removes `pi*` from the elicitation, and is the economically relevant number when the measurement is sold to whichever buyer values it most. It is also an upper bound: `EVSI <= 2 EVSI*` for every `pi*` (Proposition `prop:bounds`). The code carries it as `voi_rank/model.py: voi_fence` (with `|s + t - 1|` so an inverted mixture draw is read the other way round, as `voi` does), the plug-in table prints `EVSI*`, `eff* = EVSI*/C` and the share `EVSI/EVSI*` at the pooled medians (`plugin.tex`), and `\voiFenceRhoPlugin` / `\voiFenceTopOverlap` in `macros_extra.tex` compare the fence ranking with the gated one. Where the decision is on the fence the MC median is zero while the plug-in, the mean and `EVSI*` are not: sim2real `p003` (LEARNINGS iteration 2, corrected entry) is the case in point.

## 2. The elicitation pipeline

### 2.1 Templates and anchors

- One prompt per (scenario, member, repeat), rendered from the protocol's template with Python `string.Template` (`voi_rank/elicit.py: render_prompt`; fields `title, agent, decision, theta_definition, instrument, context`). A fixed system prompt (`elicit.SYSTEM_PROMPT`) and the CLI isolation flags `--tools "" --setting-sources "" --no-session-persistence` keep the prompt the only context (`voi_rank/providers/claude_cli.py: ISOLATION`; `--bare` is unusable under OAuth login, LEARNINGS 2026-08-21).
- The binary template (`studies/<study>/templates/elicitor.md`) contains: the model definition, two fully worked anchors that pin scales across scenarios (A1 gearbox vibration survey: `p 0.02/0.08/0.25, s 0.60/0.80/0.95, t 0.70/0.90/0.98, B 20e3/150e3/1.5e6, K 2e3/10e3/60e3, C 300/1e3/5e3` USD; A2 rapid strep test: `p 0.05/0.15/0.35, s 0.70/0.85/0.95, t 0.90/0.95/0.99, B 50/300/3000, K 20/100/1000, C 5/15/50`), the scenario, the eval studies' background-facts block (`$context`, "your numbers must not contradict them"), reasoning-before-numbers with surprise-framed percentiles, and a strict-JSON output contract. The business and eval templates differ in the `e` lines, the `$context` block, the `C` definition and the evaluation / deployment-decision wording of the `p, s, t, B, K` definitions and reminders (`diff studies/business/templates/elicitor.md studies/ai-safety-evals/templates/elicitor.md`).
- The Gaussian template (`templates/elicitor_gauss.md`, section 4) re-expresses the same two anchors as Gaussian answers.
- The staged templates of `sim2real/p004` (`templates/decision.md`, `templates/instrument.md`) split the same anchors and instructions by stage; the decision template is refused if it names `$instrument`, `$context` or `$title` (`elicit.render_decision_prompt`).

### 2.2 Validation, retry, resume, provenance

- Validation (`voi_rank/validate.py: validate_payload`, `voi_rank/gauss_fit.py: validate_gauss_payload`): JSON (markdown fences stripped first), the exact parameter set, `p5 < p50 < p95`, probabilities in (0,1), USD > 0, informativeness `median s > 1 - median t` (a swapped s/t is rejected, never silently flipped), non-degenerate prior `p50 in [0.001, 0.999]`. Failures are stored with the class prefix `json: | schema: | constraint: | fit: | cli: | http: | api: | provider:` in `elicitations.error`.
- Fitting (`voi_rank/fit.py`): Beta by method of moments then least squares on the three quantiles (warning if residual > 0.02); lognormal by least squares on log quantiles (warning if log asymmetry > 0.25). Fits are stored (`parameters.dist_family, fit_params, fit_residual, fit_warning`) and never redone at analysis time.
- Retry (`elicit.retry_delay`): one retry, at once for json/schema/constraint/fit and other provider errors, after `Retry-After` (else 5 s, cap 120 s) for HTTP 429/5xx and transport errors, never for a rejected request (400/403), an environment error (401/402/404, missing or logged-out CLI) or a CLI call that did not finish (timeout, signal). A member is halted after two consecutive CLI timeouts or a second rejected scenario (`elicit.run_jobs: halt_reason`).
- Resume: a slot is `(scenario, protocol, provider, model, repeat, stage)`; slots with a valid row are skipped (unique partial index `ux_elicitations_valid_slot_stage`), so re-running step 5 fills only what is missing. The plan is made on an in-memory copy of the DB and printed with the estimated cost before anything is submitted (`--dry-run`, `--yes`).
- Provenance: `elicitations.prompt_hash = sha256(system prompt + rendered prompt)`; `raw_response` holds the whole CLI JSON envelope (cost in `total_cost_usd`) or OpenRouter body (`usage.cost`); `protocols.template_hash` freezes each template (a changed template needs a new protocol file); `runs.code_hash` is the git HEAD of `voi_rank/, pyproject.toml, uv.lock`, suffixed `-dirty` when uncommitted (step 6 refuses a dirty tree unless `--allow-dirty`); `runs.data_hash` is the sha256 over the sorted distinct `(elicitation_id, parameter, fit_params)` a run drew from (`mc.data_hash`); the replay guard re-verifies the stored quantiles (`mc.replay_efficiency`). Every figure and table reads only `voi.db`.

### 2.3 Protocol iteration discipline

One change per protocol file, the same scenario set re-run, health checks and the cross-protocol Spearman of median efficiency compared, keep or revert recorded in `LEARNINGS.md` (spec section 10). Range statistics grow with the number of repeats, so cross-protocol noise is compared at matched k (`protocol_noise_matched.tex`, first 3 valid repeats; LEARNINGS 2026-08-22 "deepening result"). Pooling incoherent ensemble members is scored per member subset (section 7).

### 2.4 Protocols run, per study

Cross-repeat spread = `(max - min) / pooled p50` of the elicited p50 over every valid repeat of every member, median over scenarios (`db.elicited_spread`, `sensitivity.repeat_spread`); the `[health]` print. Slots and cost from `[sql: slots]` below. Zero-median counts are the `[health]` last line for the protocol's latest run.

Business (68 scenarios, haiku, CLI 2.1.220 for p000-p004):

| protocol | members x k | scenarios | one change | attempts | valid slots / slots | USD | spread p / s / t / B / K / C | fit warn | median EVSI = 0 (run) |
|---|---|---|---|---|---|---|---|---|---|
| p000_manual | manual x 1 | 8 seeds | hand percentiles | 8 | 8/8 | 0 | n/a (one repeat) | 0 | 4/8 (14) |
| p001 | haiku x 3, later 5 | 68 | baseline (report run) | 341 | 340/340 | 17.35 | 0.575 / 0.065 / 0.057 / 1.871 / 1.800 / 1.175 | 86 | 13/68 (18) |
| p002 | haiku x 3 | 68 | anchor-ratio sentence before B, K, C | 205 | 204/204 | 11.86 | 0.333 / 0.043 / 0.044 / 1.600 / 1.343 / 0.793 | 34 | 7/68 (15) |
| p003 | haiku x 3 | 68 | Fermi decomposition of B, K, C | 204 | 204/204 | 12.75 | 0.400 / 0.055 / 0.044 / 1.483 / 1.155 / 0.764 | 84 | 11/68 (16) |
| p004 | haiku x 3 | 17 (top quartile) | focused C and B guidance | 52 | 51/51 | 3.16 | 0.371 / 0.043 / 0.042 / 0.875 / 1.250 / 0.833 | 6 | 1/17 (17) |
| g001 | haiku, sonnet, opus x 5 | 68 | Gaussian family | in progress, see section 5 | 678/1020 at 03:54Z | 99.22 so far | see `[health business g001]` | 236 | no run |

At matched k = 3 the business spreads are p001 `0.41 / 0.06 / 0.03 / 1.33 / 1.17 / 0.77`, p002 `0.33 / 0.04 / 0.04 / 1.60 / 1.34 / 0.79`, p003 `0.40 / 0.05 / 0.04 / 1.48 / 1.15 / 0.76`, p004 `0.37 / 0.04 / 0.04 / 0.88 / 1.25 / 0.83` (`[macro] studies/business/report/generated/protocol_noise_matched.tex`, rows `first 3`). Cross-protocol Spearman of median efficiency: p001 vs p002 0.58, vs p003 0.45, vs p004 0.74 (17); p002 vs p003 0.68 (`protocol_compare.tex`; `[macro] \voiRhoProtoMin 0.45`, `\voiRhoProtoMax 0.68`).

ai-safety-evals (15 scenarios: 10 AI safety evaluations, 5 robot safety evaluations; CLI 2.1.280):

| protocol | members x k | one change | attempts | valid slots / slots | USD | spread p / s / t / B / K / C | fit warn | median EVSI = 0 (run) |
|---|---|---|---|---|---|---|---|---|
| p001 | haiku x 5 | baseline, `$context`, C = build + run once | 78 | 75/75 | 5.75 | 0.667 / 0.125 / 0.093 / 5.500 / 6.647 / 2.125 | 10 | 9/15 (1) |
| p002 | haiku x 5 | log-decade framing of B, K, C | 76 | 75/75 | 5.06 | 0.921 / 0.125 / 0.106 / 11.880 / 5.700 / 1.833 | 10 | 6/15 (2) |
| p003 | haiku, sonnet, opus x 5 | ensemble, p001 template | 229 | 225/225 | 15.17 | pooled 1.000 / 0.176 / 0.200 / 2.900 / 4.900 / 2.317 | 17 | 11/15 (3); subsets: sonnet+opus 13/15 (5), haiku 6/15 (8), opus 13/15 (10) |
| g001 | haiku, sonnet, opus x 5 | Gaussian family | 314 (80 in the outage) | 223/225 | 45.51 | section 4 | 123 | EVSI_step: 0/15 in runs 4, 6, 7, 9 |

Per-member B / K / C spread under p003, all 5 repeats: haiku `5.14 / 4.83 / 2.00`, sonnet `1.25 / 1.17 / 1.00`, opus `0.67 / 0.75 / 0.53` (`[health ai-safety-evals p003]`, per-member block). Cross-member Spearman of pooled p50, sonnet vs opus: p 0.886, s 0.765, t 0.830, B 0.938, K 0.919, C 0.900; haiku vs opus on B / K / C: 0.546 / 0.553 / 0.288 (same print). Spearman p001 vs p002 0.42; p003 pooled vs its own subsets: haiku 0.27, opus+sonnet 0.26, opus 0.33; opus+sonnet vs opus 0.99 (`protocol_compare.tex` matrix in `protocol_noise_matched.tex`).

sim2real (15 scenarios: home manipulator ladder L0-L9, AV AEB ladder L1, 4, 6, 8, 9; CLI 2.1.280):

| protocol | members x k | one change | attempts | valid slots / slots | USD | spread p / s / t / B / K / C | fit warn | median EVSI = 0 (run) |
|---|---|---|---|---|---|---|---|---|
| p001 | haiku x 5 | baseline | 78 | 75/75 | 5.87 | 0.682 / 0.154 / 0.090 / 4.400 / 4.333 / 1.680 | 25 | 11/15 (1) |
| p002 | haiku x 5 | log-decade B, K, C | 77 | 75/75 | 5.81 | 0.667 / 0.139 / 0.115 / 4.000 / 3.900 / 2.083 | 15 | 10/15 (2) |
| p003 | haiku, sonnet, opus x 5 | ensemble | 236 | 224/225 | 16.12 | pooled 1.400 / 0.538 / 0.250 / 6.600 / 11.800 / 2.200 | 13 | 15/15 (3); sonnet+opus 14/15 (5), haiku 12/15 (8), opus 15/15 (10) |
| g001 | haiku, sonnet, opus x 5 | Gaussian family | 279 (54 in the outage) | 223/225 | 41.83 | section 4 | 109 | EVSI_step: 0/15 in runs 4, 6, 7, 9 |
| p004 | haiku, sonnet, opus x 5, staged | p, B, K once per decision group; s, t, C per rung | 255 (30 decision + 225 instrument) | 255/255 | 13.77 | p 1.750 (2 groups) / s 0.500 / t 0.250 / B 13.194 (2 groups) / K 3.650 (2 groups) / C 2.143 | 6 | 15/15 (11); sonnet+opus 15/15 (12), opus 15/15 (13), haiku 13/15 (14) |

Per-member B / K / C spread under p003: haiku `5.98 / 7.47 / 1.65`, sonnet `1.00 / 0.88 / 0.83`, opus `0.67 / 0.80 / 0.50`; under p004 haiku's decision-level B spread is `113.00`, the median of its two groups (AEB 224.6, home manipulator 1.4; sonnet 0.76, opus 1.04) (`[health sim2real p003]`, `[health sim2real p004]`). Decision-level pooled p50 under p004 (`[health sim2real p004]`, decision-level block): p home manipulator haiku 0.20 / sonnet 0.35 / opus 0.30, AV AEB 0.08 / 0.12 / 0.15; B AEB 4e6 / 4e7 / 6e7; K AEB 1e7 / 8e6 / 1.2e7; B home 4e5 / 2e6 / 4e6; K home 5e5 / 4e5 / 1.2e6. Spearman p001 vs p002 -0.17; every all-member p003 and p004 ranking is constant (15 zero medians, `n/a`); p001 vs p003[opus+sonnet] 0.56 (`protocol_noise_matched.tex` matrix).

`[sql: slots]`, the query behind attempts, slots, valid slots and cost of every table above (run per study):

```python
import sqlite3
from voi_rank import db
con = sqlite3.connect('file:studies/<study>/voi.db?mode=ro', uri=True); con.row_factory = sqlite3.Row
stage = "COALESCE(stage,'')" if 'stage' in [r[1] for r in con.execute("pragma table_info(elicitations)")] else "''"
slot = f"e.scenario_id||'/'||e.provider||'/'||e.model||'/'||e.repeat_ix||'/'||{stage}"
for r in con.execute(f"""SELECT p.name, e.provider||':'||e.model AS member, COUNT(*) AS attempts, SUM(e.valid) AS valid,
    COUNT(DISTINCT {slot}) AS slots, COUNT(DISTINCT CASE WHEN e.valid=1 THEN {slot} END) AS valid_slots
    FROM elicitations e JOIN protocols p ON p.id=e.protocol_id GROUP BY p.name, member ORDER BY p.id"""):
    cost = sum(db.envelope_cost(x[0]) for x in con.execute(
        "SELECT raw_response FROM elicitations e JOIN protocols p ON p.id=e.protocol_id"
        " WHERE p.name=? AND e.provider||':'||e.model=?", (r['name'], r['member'])))
    print(dict(r) | {'cost_usd': round(cost, 2)})
for p in con.execute("SELECT id, name FROM protocols ORDER BY id"):     # error classes
    cls = {}
    for (err,) in con.execute("SELECT error FROM elicitations WHERE protocol_id=?", (p['id'],)):
        k = 'valid' if err is None else err.split(':', 1)[0]; cls[k] = cls.get(k, 0) + 1
    print(p['name'], cls)
```

Error classes it prints: business p001 `{valid 340, json 1}`, p002 `{valid 204, constraint 1}`, p003 `{valid 204}`, p004 `{valid 51, schema 1}`; ai-safety-evals p001 `{valid 75, schema 3}`, p002 `{valid 75, schema 1}`, p003 `{valid 225, json 4}`, g001 `{valid 223, constraint 3, json 7, cli 81}`; sim2real p001 `{valid 75, schema 2, json 1}`, p002 `{valid 75, schema 2}`, p003 `{valid 224, constraint 4, json 4, schema 4}`, g001 `{valid 223, cli 56}`, p004 `{valid 255}`. Per binary batch, JSON validity (parse + schema) is 96.2 to 100 %, per-member attempt validity 94.9 to 100 %, and slot validity after the one retry 99.6 to 100 % (`[health]` lines 2 to 4 and the per-member block of every binary protocol).

## 3. Model choice

### 3.1 Why `e` was dropped

v1 carried `e` (P(agent acts on the signal) x P(the action works)) as a multiplier on `B` only. Three reasons (chapter `sec:binary`, footnote; `spec.md` v2 item 1): it conflates compliance (part of the decision rule) with efficacy (part of `B`); it discounts the benefit branch and not the false-alarm branch; and it was among the least influential parameters. Numbers, business run 7 (v1, with `e`) against run 18 (v2, same elicitations, `e` ignored; run 13 is the same run scored from an uncommitted tree, identical rows):

- Global sensitivity (mean |Spearman| against efficiency over the 17 top-quartile scenarios), run 7: `C 0.40, B 0.33, K 0.23, p 0.20, s 0.14, t 0.13, e 0.05`; run 18: `C 0.41, K 0.30, B 0.28, p 0.16, s 0.15, t 0.12` (`[macro] \voiLegacyGlobalE 0.05`, `\voiLegacyGlobalMax 0.40`, `\voiGlobalC 0.41`, `\voiGlobalK`, `\voiGlobalB`).
- Cross-repeat spread of `e` under p001: 0.14 (`[macro] \voiLegacyNoiseE`).
- Spearman of median efficiency, run 18 vs run 7: 0.996 over 68 scenarios; top-10 overlap 9/10 (`[macro] \voiLegacyRho`, `\voiLegacyTopTenShared`); zero-median scenarios 12 (run 7) to 13 (runs 13 and 18).

```python
# [copy] business
from voi_rank import db
from voi_rank.analysis import tables
con = db.connect('/tmp/voi_methods/business/voi.db')
print(tables.legacy_e_macros(con, db.get_run(con, 18)))
print({n: round(tables.global_sensitivity_param(con, 7, n), 2) for n in db.PARAM_NAMES + ['e']})
print({n: round(v, 2) for n, v in tables.global_sensitivity(con, 18).items()})
print(tables.rank_corr_between_runs(con, 18, 7))
for rid in (7, 13, 18):
    print(rid, con.execute("SELECT COUNT(*) FROM results WHERE run_id=? AND metric='EVSI' AND q50 < 1e-6", (rid,)).fetchone()[0])
```

### 3.2 The simplicity test: does EVPI/C reproduce EVSI/C?

Two identities (scratchpad draft `model_simplicity_draft.md`): `EVSI(p,s,t,B,K) = K f(p,s,t,B/K)` and the ratio `B/K` only sets `pi*`. Dropping `(s, t)` collapses the ranking to `EVPI/C = min(pB, (1-p)K)/C`. The test is the Spearman between the two rankings.

Stored-run version (medians of the per-draw ratios `efficiency` and `evpi_efficiency`; `simplicity.tex`, `macros_extra.tex`):

| study, run | rho all scenarios | rho over EVSI > 0 | top-10 overlap | headroom EVSI/EVPI median [IQR] |
|---|---|---|---|---|
| business, run 18 (p001) | 0.59 (n=68) | 0.89 (n=55) | 6/10 | 0.47 [0.20, 0.61] |
| ai-safety-evals, run 5 (p003, sonnet+opus) | 0.20 (n=15) | undefined (n=2) | 9/10 | 0.00 |
| sim2real, run 12 (p004, sonnet+opus) | undefined (15 zero medians) | undefined (n=0) | 9/10 | 0.00 |

(`[macro] \voiSimpRhoAll, \voiSimpRhoPos, \voiSimpN, \voiSimpNPos, \voiSimpTopOverlap, \voiHeadroomMed, \voiHeadroomQlo, \voiHeadroomQhi` in each study's `macros_extra.tex`.) The MC median is a fragility diagnostic on the eval studies, so the plug-in version at the pooled elicited medians is the readable one:

| study, protocol [members] | n | rho all | n with EVSI > 0 | rho over EVSI > 0 | top-10 overlap | headroom median |
|---|---|---|---|---|---|---|
| business p001 | 68 | 0.87 | 63 | 0.97 | 8 | 0.69 |
| ai-safety-evals p001 (haiku) | 15 | 0.84 | 14 | 0.91 | 8 | 0.52 |
| ai-safety-evals p003 [sonnet+opus] | 15 | 0.08 | 9 | 0.80 | 6 | 0.53 |
| ai-safety-evals p003 [opus] | 15 | 0.00 | 7 | 0.96 | 7 | 0.50 |
| sim2real p001 (haiku) | 15 | 0.60 | 9 | 0.83 | 8 | 0.46 |
| sim2real p003 [sonnet+opus] | 15 | 0.81 | 15 | 0.81 | 8 | 0.19 |
| sim2real p004 [sonnet+opus] | 15 | 0.44 | 6 | 0.89 | 9 | 0.28 |
| sim2real p004 (all members) | 15 | 0.41 | 13 | 0.82 | 7 | 0.19 |

```python
# [copy] plug-in simplicity test at the pooled medians (median of p50 over the valid elicitations of the members)
import numpy as np
from scipy import stats
from voi_rank import db, model
def plugin(study, protocol, members=None, topk=10):
    con = db.connect(f'/tmp/voi_methods/{study}/voi.db')
    prot = db.protocol_by_name(con, protocol)
    labels = db.normalize_run_members(db.protocol_members(prot), members)
    rows = {}
    for sc in db.get_scenarios(con, 'all'):
        med = {}
        for n in db.PARAM_NAMES:
            p50s = db.elicited_p50s(con, prot['id'], sc['id'], n, members=labels)
            if not p50s: break
            med[n] = float(np.median(p50s))
        if len(med) < 6: continue
        evsi, evpi = model.voi(med['p'], med['s'], med['t'], med['B'], med['K'])
        rows[sc['id']] = (float(evsi) / med['C'], float(evpi) / med['C'], float(evsi), float(evpi))
    ids = sorted(rows); pos = [i for i in ids if rows[i][2] > 0]
    rho_all = stats.spearmanr([rows[i][0] for i in ids], [rows[i][1] for i in ids]).statistic
    rho_pos = stats.spearmanr([rows[i][0] for i in pos], [rows[i][1] for i in pos]).statistic if len(pos) >= 3 else None
    top = lambda j: set(sorted(ids, key=lambda i: -rows[i][j])[:topk])
    head = np.median([rows[i][2] / rows[i][3] for i in pos if rows[i][3] > 0])
    print(study, protocol, labels, len(ids), round(rho_all, 2), len(pos), rho_pos and round(rho_pos, 2), len(top(0) & top(1)), round(head, 2))
plugin('business', 'p001'); plugin('ai-safety-evals', 'p001')
plugin('ai-safety-evals', 'p003', ['claude_cli:sonnet', 'claude_cli:opus']); plugin('ai-safety-evals', 'p003', ['claude_cli:opus'])
plugin('sim2real', 'p001'); plugin('sim2real', 'p003', ['claude_cli:sonnet', 'claude_cli:opus'])
plugin('sim2real', 'p004', ['claude_cli:sonnet', 'claude_cli:opus']); plugin('sim2real', 'p004')
```

Reading: inside the gate the two rankings agree (0.80 to 0.97); across the whole set they agree only where nearly every scenario is in the gate (business 63/68, haiku track 1 14/15) and fall to 0.00 to 0.44 where the larger models put decisions outside it (track 1 sonnet+opus 9/15, p004 6/15). What `(s, t)` add is the gate, not the order within it; headroom varies 0.19 to 0.69 across designs, so it is not a constant either.

### 3.3 What to add next

- The reuse count `n`: the number of decisions an evaluation informs once built (model versions, releases, robots). With `C` defined as build plus one run, `C` is mostly a fixed cost and EVSI a per-decision quantity; the natural objective is `n EVSI - C_build - n C_run` and the ranking `n EVSI / (C_build + n C_run)`, which reorders cheap-to-run, expensive-to-build instruments (simulation suites) against expensive-to-run ones (track tests). The staged protocol (`sim2real/p004`, `spec.md` v2.2 item 2, `db.normalize_stages`) is the place for it: `C_build`, `C_run` and `n` belong to the instrument stage next to `s, t`, the decision stage stays `p, B, K`; `n = 1` reproduces the current metric, so the ablation is one flag. No protocol asks it yet (`grep -l 'C_build\|reuse' studies/*/templates/*.md` finds nothing).
- Second: a continuous score with a decision-optimal cutoff (the chapter's `sec:step`, "pass/fail at a cutoff chosen for this decision"), which the Gaussian family already computes as `step` and which removes the fixed-mark gate. Third: adversarial degradation of `s` for AI evaluations (eval awareness, sandbagging), track 1 only.
- Not needed: exposure and severity are inside `B`; splitting them is an elicitation aid, and the Fermi decomposition (business p003) did not reduce dollar noise (`B 1.48` vs `1.33`, matched k).

### 3.4 The case against removing `s, t`

- The zeros are theirs. The gate condition `pi0 < pi* < pi1` moves with `s` and `t` (chapter `sec:gate`); 13/68 business scenarios (`\voiZeroEvsiCount`) and 6/15 always-respond decisions at the track-1 sonnet+opus medians (`plugin.tex`, `regime` column: ids 3, 1, 5, 14, 2, 11 read `always`; 9/15 `gate`, `\voiPluginInGate`) have no counterpart in `EVPI/C`.
- Per-draw Spearman understates a discontinuous effect: the global mean |rho| of `s`, `t` (business 0.16, 0.14 all scenarios) is small because the elicited values sit in a narrow band (business p001 p50s: `s` 0.68 to 0.96, `t` 0.55 to 0.98; 5th to 95th percentile 0.77 to 0.95 and 0.80 to 0.96), yet a threshold crossing is what the gate does (`simplicity.tex`, global sensitivity block).
- Track 2 holds the decision fixed, so `s, t, C` are the only things that differ between rungs; under `p004` they are the only elicited differences by construction (`consistency.tex`: CV(p) = 0, log10 range of B, K = 0 in both groups, range of C 1.97 and 1.38 decades). Per rung at the sonnet+opus pooled medians `s` runs 0.35 to 0.78 and `t` 0.50 to 0.87 under `p004`, 0.45 to 0.82 and 0.48 to 0.90 under `p003` (a smaller drop than LEARNINGS iteration 3 first stated against a different protocol; commit `f695db7` corrected that entry to "within replicate noise per member"):

```python
# [copy] sim2real, pooled p50 of s and t per scenario, sonnet+opus
import numpy as np
from voi_rank import db
con = db.connect('/tmp/voi_methods/sim2real/voi.db'); labels = ['claude_cli:opus', 'claude_cli:sonnet']
for prot in ('p003', 'p004'):
    pid = db.protocol_by_name(con, prot)['id']
    for n in ('s', 't'):
        vals = [float(np.median(db.elicited_p50s(con, pid, sid, n, members=labels))) for sid in range(1, 16)]
        print(prot, n, round(min(vals), 2), round(max(vals), 2))
```

- The fence value keeps them too: `EVSI* = Lam p(1-p)(s + t - 1)` is linear in Youden's index, so even the threshold-free ranking is driven by `s + t` (chapter eq. `fence`).

## 4. The Gaussian family as a sanity check

### 4.1 What it elicits

Protocol `g001` in every study (`model: gaussian`, haiku, sonnet, opus, k = 5; `studies/<study>/protocols/g001.yaml`), template `templates/elicitor_gauss.md`. The elicitor first names the continuous state variable and its unit with bad-is-high (a bad-is-low variable must be negated; `bad_is_high: false` is a schema error), then answers eight over-determined questions with reasoning before numbers (chapter `sec:protocol`, Table `tab:protocol`; template lines 69 to 76 in the eval studies, 63 to 70 in business):

- Q1 `theta` p5 / p50 / p95 gives `mu0 = p50`, `sigma0 = (p95 - p5) / 3.29`; residual = asymmetry.
- Q2a `theta_c` and Q2b `P(theta > theta_c)` give two values of `d = (mu0 - theta_c) / sigma0`; stored `d` is their mean, residual `|d_a - d_b|` in prior-sd units.
- Q3a test-retest width `W_rr`, Q3b the 90 % width after one result `W1`, Q3c the probability `c` that the result moves the estimate by more than half the prior half-width: three routes to the relative sensor error `x = sqrt(r) / sigma0`, pooled by the median of their logs; residual = std of the logs; route c dropped when `c > 0.40` (Gaussian bound 0.4108).
- Q4 four loss numbers (under- and over-response by one and two `sigma0`) give the exponent `k = mean(log2(L2/L1))` per side, clipped to [0.5, 4], and `L`, the minimal expected loss under the prior (`gaussian.min_expected_loss`, bounded Brent over the action shift); residual `|k_m - k_p|`.
- Q5 `kappa sigma0`, Q6 `B, K` (single values), Q7 `sigma_b` (a systematic error repeats would not reveal), Q8 `C` p5 / p50 / p95 (lognormal, as in the binary protocol).

Anchors are the binary anchors re-expressed: A1 as bearing-fault vibration severity, `theta 1.5/3.1/4.8 mm/s, theta_c 4.5, P 0.08`, fitted `x = 0.41 (R^2 0.86, 0.83 after the sigma_b correction), d = -1.40, k = 2, L = 9,570 USD`, derived pass/fail `s, t = 0.78, 0.96`; A2 as log10 copies per swab, `0.0/2.4/5.0, theta_c 4.0, P 0.15, x = 0.35 (0.89 / 0.88), d = -1.04, L = 66.5`, derived `0.82, 0.95` (template "Implied" lines 34 and 45; `tests/test_gaussian.py` derives them from the listed answers and checks the two Implied lines of every study's template).

### 4.2 The four action models

On every MC draw, from the same state and sensor quantities (`voi_rank/gaussian.py: scenario_metrics`; `R^2 = 1 / (1 + x^2 + (sigma_b/sigma0)^2 (1 - 2/pi))`, `r2_effective`):

| model | decision | EVSI | EVPI | chapter |
|---|---|---|---|---|
| quad | graded response, loss `c abs(a - theta)^k` | `L (1 - (1 - R^2)^(k/2))` | `L` | eq. `lossfamily` |
| kg | respond or not, payoff linear in `theta - theta_c` | `kappa sigtilde Psi(d / R)`, `Psi(z) = phi(z) - abs(z) Phi(-abs(z))` | `kappa sigma0 Psi(d)` | eq. `kg` |
| step | respond or not, step payoff `B / -K`, continuous reading | binary closed form at the orthant probabilities of the decision-optimal cutoff `ybar* = mu0 + (theta_c + sigma1 Phi^-1(pi*) - mu0) / R^2` (exact; the design's 64-node Gauss-Hermite quadrature misses up to 1.6 % of `B + K` at `R^2 = 0.99`, kept as `voi_step_gh` for the test) | `min(pB, (1-p)K)`, `p = Phi(d)` | eq. `stepcont`, `sec:step` |
| stepfix | the same with a pass/fail report at the fixed mark `theta_c` | `model.voi(p, s, t, B, K)` with `s, t` the orthant probabilities at `theta_c` (Owen's T; a 1-D tail integral beyond `abs(d) = 5`) | as step | `sec:step`, "fixed mark" |

`eff_<m> = EVSI_<m> / C`; the primary metric of a Gaussian run is `eff_step`; `stepfix` is the model that maps one-to-one onto the binary protocol, and it is the only one with a gate.

### 4.3 How it was fitted

`voi_rank/gauss_fit.py: derive` (quoted verbatim in `spec.md` v2.1 item 2). Stored per valid elicitation as `point` rows (`fit_params {"value": v}`, `p5 = p50 = p95 = v`): `g_mu0, g_sigma0, g_d, g_x, g_k, g_L, g_kappa_sigma0, g_B, g_K, g_sigma_b_rel`, plus `C` lognormal. `fit_residual` carries the over-determination residual of the questions behind each row and `fit_warning` fires past the thresholds `0.25` (asymmetry), `0.5` sd (d mismatch), `0.5` log units (x route spread), `1.0` (k mismatch) or when route c was dropped (`gauss_fit.THRESHOLDS, C_MOVE_DROP`). The consistency score (max residual / threshold) is derived at analysis time (`consistency_gauss.tex`).

Residuals over the sonnet+opus elicitations (`consistency_gauss.tex`, from `compare_models --members claude_cli:sonnet,claude_cli:opus`, runs 5 vs 6):

| residual | ai-safety-evals (n=149): q50, flagged | sim2real (n=150): q50, flagged |
|---|---|---|
| theta triple asymmetry (0.25) | 0.053, 15 % | 0.019, 10 % |
| d mismatch, sd units (0.5) | 0.016, 1 % | 0.009, 0 % |
| x route spread, log units (0.5) | 0.049, 13 % | 0.028, 9 % |
| k mismatch (1.0) | 0, 1 % | 0, 1 % |
| consistency score > 1 | 0.641, 30 % | 0.50, 19 % |

Fit-warning rows over all members: 123 (ai-safety-evals), 109 (sim2real) (`[health <study> g001]`, "fit warnings"). Per-member cross-repeat spread (`[health <study> g001]`, per-member block; `d`, `sigma_b/sigma0`, `mu0` as max - min in prior-sd units):

| quantity | ai-safety-evals haiku / sonnet / opus | sim2real haiku / sonnet / opus |
|---|---|---|
| L | 1.62 / 1.71 / 1.39 | 5.93 / 1.46 / 1.09 |
| d (sd units) | 1.34 / 1.09 / 0.42 | 1.21 / 0.57 / 0.35 |
| x | 0.88 / 0.30 / 0.38 | 0.72 / 0.72 / 0.49 |
| B | 3.00 / 1.70 / 0.75 | 4.90 / 2.20 / 1.20 |
| C | 2.25 / 1.13 / 0.50 | 2.40 / 0.92 / 0.62 |

The dollar noise ordering of the binary family (haiku > sonnet > opus) reproduces in the Gaussian one, except `L` on ai-safety-evals (sonnet 1.71 above haiku 1.62).

### 4.4 Agreement numbers available so far

Spearman of median efficiency between the binary ranking and each action model over the 15 shared scenarios, gate agreement (share of scenarios on the diagonal of binary median EVSI = 0 against stepfix median EVSI = 0), and the derived-vs-elicited `p = Phi(d)`, `s`, `t` (`compare_models`; `[macro] macros_compare.tex` of each study holds the sonnet+opus row):

| study | pair (runs) | quad | kg | step | stepfix | gate agree | rho p (MAD) | rho s (MAD) | rho t (MAD) |
|---|---|---|---|---|---|---|---|---|---|
| ai-safety-evals | p001 vs g001, all members (1 vs 4) | -0.58 | -0.55 | -0.51 | 0.03 | 60 % | 0.73 (0.14) | 0.41 (0.05) | -0.15 (0.05) |
| ai-safety-evals | p003 vs g001, sonnet+opus (5 vs 6) | 0.12 | 0.02 | 0.38 | 0.56 | 47 % | 0.81 (0.12) | 0.87 (0.04) | -0.05 (0.10) |
| ai-safety-evals | opus only (10 vs 9) | 0.02 | -0.02 | 0.21 | 0.26 | 40 % | 0.92 (0.11) | 0.85 (0.04) | -0.12 (0.11) |
| ai-safety-evals | haiku only (8 vs 7) | -0.03 | -0.09 | -0.01 | -0.14 | 53 % | 0.57 (0.10) | 0.39 (0.05) | 0.00 (0.02) |
| sim2real | p001 vs g001, all members (1 vs 4) | 0.00 | -0.04 | -0.03 | -0.06 | 33 % | 0.71 (0.05) | -0.09 (0.05) | 0.45 (0.03) |
| sim2real | p003 vs g001, sonnet+opus (5 vs 6) | -0.19 | -0.31 | -0.19 | 0.06 | 7 % | 0.64 (0.03) | 0.39 (0.14) | 0.39 (0.10) |
| sim2real | opus only (10 vs 9) | undefined (binary ranking constant) | | | | 0 % | 0.31 (0.07) | 0.03 (0.21) | 0.30 (0.12) |
| sim2real | haiku only (8 vs 7) | 0.18 | 0.27 | 0.19 | 0.10 | 33 % | 0.11 (0.07) | -0.05 (0.05) | 0.43 (0.05) |
| sim2real | p004 vs g001, sonnet+opus (12 vs 6) | undefined (binary ranking constant) | | | | 0 % | 0.75 (0.13) | 0.32 (0.18) | 0.42 (0.09) |
| business | pending: g001 in progress, no run | | | | | | | | |

```bash
# [copy] the rows above; each call writes macros_compare.tex into $T/<study>/report/generated
uv run python -m voi_rank.analysis.compare_models --study $T/<study> --binary p001 --gaussian g001
uv run python -m voi_rank.analysis.compare_models --study $T/<study> --binary p003 --gaussian g001 --members claude_cli:sonnet,claude_cli:opus
uv run python -m voi_rank.analysis.compare_models --study $T/<study> --binary p003 --gaussian g001 --members claude_cli:opus
uv run python -m voi_rank.analysis.compare_models --study $T/<study> --binary p003 --gaussian g001 --members claude_cli:haiku
uv run python -m voi_rank.analysis.compare_models --study $T/sim2real --binary p004 --gaussian g001 --members claude_cli:sonnet,claude_cli:opus
```

Among the four action models (Spearman of median `eff_<m>`, all 15 scenarios):

| study, run | quad-kg | quad-step | kg-step | step-stepfix | quad-stepfix | kg-stepfix |
|---|---|---|---|---|---|---|
| ai-safety-evals run 4 (all) | 0.91 | 0.63 | 0.72 | 0.38 | -0.25 | -0.29 |
| ai-safety-evals run 6 (sonnet+opus) | 0.91 | 0.64 | 0.74 | 0.56 | -0.15 | -0.11 |
| sim2real run 4 (all) | 0.94 | 0.92 | 0.89 | 0.84 | 0.66 | 0.54 |
| sim2real run 6 (sonnet+opus) | 0.92 | 0.84 | 0.77 | 0.85 | 0.55 | 0.42 |

Gaussian rankings (median `eff_step`, `P(EVSI_step > C)` of the top): ai-safety-evals run 4 puts StrongREJECT (id 9) first at 5.72 (P+ 0.88), then agentic misalignment 0.79, Cybench 0.71, ASIMOV-2.0 0.55, ... , Veo 0.04 last; run 6 StrongREJECT 5.2 (0.88), CyberGym 1.53, ASIMOV-2.0 1.46. sim2real run 4 falls along the ladder: L1 camera-frame VLM QA 5.38 (P+ 0.73), L0 SafePlan 1.83, L6 VIL AEB 1.63, L1 MSSBench 1.36, ... , L8 staged field test 0.19, L9 monitored pilot 0.14; run 6 13.46, 4.78, 2.56, ... , 0.27. No Gaussian run has a zero median (`[health <study> g001 ...]`: "median EVSI_step ~ 0: 0/15"), which is the chapter's prediction for a continuous signal.

```python
# [sql] among-model agreement and the eff_step ranking of a Gaussian run
import sqlite3, numpy as np
from scipy import stats
con = sqlite3.connect('file:studies/<study>/voi.db?mode=ro', uri=True); con.row_factory = sqlite3.Row
rid = 4   # or 6
med = {m: {r['scenario_id']: r['q50'] for r in con.execute("SELECT scenario_id, q50 FROM results WHERE run_id=? AND metric=?", (rid, m))}
       for m in ('eff_quad', 'eff_kg', 'eff_step', 'eff_stepfix')}
ids = sorted(med['eff_step']); ms = list(med)
print({(a, b): round(stats.spearmanr([med[a][i] for i in ids], [med[b][i] for i in ids]).statistic, 2) for a in ms for b in ms if a < b})
title = {r['id']: r['title'] for r in con.execute("SELECT id, title FROM scenarios")}
pp = {r['scenario_id']: r['p_positive'] for r in con.execute("SELECT scenario_id, p_positive FROM results WHERE run_id=? AND metric='EVSI_step'", (rid,))}
print([(i, title[i][:30], round(med['eff_step'][i], 2), round(pp[i], 2)) for i in sorted(ids, key=lambda i: -med['eff_step'][i])])
```

Reading: member-matched, track 1 agrees between the binary ranking and its Gaussian twin `stepfix` at 0.56 (top-10 overlap 7) and with the continuous `step` at 0.38; the derived prior agrees with the elicited one at 0.81 to 0.92 with a median absolute difference of 0.11 to 0.12, the derived `s` at 0.87 (MAD 0.04) and `t` not at all (the sonnet+opus pooled elicited `t` spans 0.64 to 0.91 across the 15 scenarios, `s` 0.60 to 0.91). On track 2 the binary side is gate-dominated (14 or 15 zero medians), so the MC-median comparison is undefined or near zero and the plug-in comparison is the one that would be fair; it does not exist yet (LEARNINGS iteration 3, "next code round"). Within the Gaussian family the smooth models agree with each other (0.63 to 0.94; 0.77 to 0.94 on sim2real) and `stepfix` sits apart on track 1 (its gate), together on track 2.

## 5. Cost of the campaign

USD from the stored envelopes (`db.envelope_cost` over `elicitations.raw_response`; the claude CLI's `total_cost_usd`); `[sql: slots]` above, per-member rows summed per protocol. Cost per attempt is cost / attempts.

| study | protocol | members | attempts | USD | USD per attempt |
|---|---|---|---|---|---|
| business | p001 | haiku | 341 | 17.35 | 0.051 |
| business | p002 | haiku | 205 | 11.86 | 0.058 |
| business | p003 | haiku | 204 | 12.75 | 0.063 |
| business | p004 | haiku | 52 | 3.16 | 0.061 |
| business | g001 (in progress) | haiku / sonnet / opus | 649 / 645 / 646 | 26.44 / 52.72 / 20.06 | 0.041 / 0.082 / 0.031 (1257 outage attempts included, 1256 of them at zero cost) |
| ai-safety-evals | p001 | haiku | 78 | 5.75 | 0.074 |
| ai-safety-evals | p002 | haiku | 76 | 5.06 | 0.067 |
| ai-safety-evals | p003 | haiku / sonnet / opus | 75 / 78 / 76 | 4.81 / 6.55 / 3.81 | 0.064 / 0.084 / 0.050 |
| ai-safety-evals | g001 | haiku / sonnet / opus | 95 / 108 / 111 | 10.79 / 25.02 / 9.69 | 0.114 / 0.232 / 0.087 |
| sim2real | p001 | haiku | 78 | 5.87 | 0.075 |
| sim2real | p002 | haiku | 77 | 5.81 | 0.075 |
| sim2real | p003 | haiku / sonnet / opus | 79 / 79 / 78 | 5.44 / 5.91 / 4.77 | 0.069 / 0.075 / 0.061 |
| sim2real | g001 | haiku / sonnet / opus | 89 / 95 / 95 | 10.77 / 23.57 / 7.49 | 0.121 / 0.248 / 0.079 |
| sim2real | p004 | haiku / sonnet / opus | 85 / 85 / 85 | 4.38 / 5.34 / 4.05 | 0.052 / 0.063 / 0.048 |

Totals: business p000-p004 45.12 USD (`\voiElicitCost 17.35` is p001 alone); ai-safety-evals 71.48 USD over 697 attempts; sim2real 83.40 USD over 925 attempts; business g001 99.22 USD over 1940 attempts at 2026-09-29T03:54:06Z (678 of 1020 slots valid, 1257 outage attempts, 1256 of them at zero cost; the run is still filling, `runs` has no g001 row). Everything elicited so far: about 299 USD. The Gaussian prompt (13.6k to 14.3k characters rendered in the eval studies, 10.7k to 10.9k in business; 13 reasoning strings: the state block and 12 answers) costs roughly twice the binary one per attempt; sonnet is the most expensive member on it, opus the cheapest (median output tokens on `g001`: opus 3.0k, haiku 23.7k to 25.2k, sonnet 27.4k to 28.4k; the "about 1k" of LEARNINGS iteration 2 is opus on the binary prompt, median 1.2k). MC and analysis cost nothing (no network).

```python
# [sql] timestamped snapshot of the in-progress business g001
import sqlite3, datetime
from voi_rank import db
con = sqlite3.connect('file:studies/business/voi.db?mode=ro', uri=True)
print(datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'))
by = {}
for m, raw, valid, err in con.execute("SELECT provider||':'||model, raw_response, valid, error FROM elicitations"
                                      " WHERE protocol_id=(SELECT id FROM protocols WHERE name='g001')"):
    d = by.setdefault(m, [0, 0, 0.0, 0]); d[0] += 1; d[1] += valid or 0; d[2] += db.envelope_cost(raw); d[3] += (err or '').startswith('cli:')
print({m: (a, v, round(c, 2), cli) for m, (a, v, c, cli) in by.items()}, con.execute("SELECT COUNT(*) FROM runs WHERE protocol_id=(SELECT id FROM protocols WHERE name='g001')").fetchone())
```

## 6. Research inputs

- Literature catalogue: 512 sweep records in 10 JSON files (`ls research/literature/*.json | wc -l`; `research/catalog.md` line 3) merged to 443 unique papers (`python3 -c "import json; print(len(json.load(open('research/catalog.json'))))"`), built by `python3 research/build_catalog.py` (deterministic; it rewrites `research/catalog.{json,md}` and `refs.bib`, so run it in a copy). Views and their sizes from the generated headings (`grep -n '^## ' research/catalog.md`): (b) safety-focused robotics evaluations 249, (c) frontier-AI evaluation records 66 (position papers excluded from both), (d) entries with cost evidence 238, (e) with validity evidence 266, (f) speaker-linked 89; by ladder level 0..9: 71, 17, 3, 24, 77, 54, 11, 86, 13, 30, plus 57 off the ladder (`grep -n '^### Level' research/catalog.md`). 334 of 443 carry `safety_focus`.
- Gap counts (`research/gaps.md`, regex-flagged then hand-checked, "treat as +/- a few"): 117 of 249 robotics safety evaluations state no cost, 70 neither cost nor validity, 102 no validity evidence; 30 of 66 frontier-AI records state no cost; 9 of the 10 shortlisted system-card evaluations have at most four sentences touching cost or validity (`grep -n '117 of 249\|102 of 249\|30 of 66\|9 of the 10' research/gaps.md`). The literature supplies a cost per trial for roughly 10 % of evaluations and a likelihood ratio for roughly 5 %.
- System-card mining (`research/mine_system_cards.py`, deterministic, 36 s on a re-run; input `/home/douwm/projects/ais/system_card_db/data/docs.sqlite`, present, 5,554,176 bytes, modified 2026-09-29T07:46Z, after this was written: a re-run into a scratch directory reproduces every count below and the snippets, and one row of the top-60 table moved (METR DF 38 to 37); only documents with `safety_evals = 1`): 180 documents from 22 publishers (anthropic 47, google_deepmind 23, openai 21, uk_aisi 16, metr 12, ...), domain document counts cbrn 61, cyber 89, loss_of_control 82, harmful_manipulation 29, societal_harm 45; 1774 candidates kept after the filters, dropped case_dominance 753, model_like 31, sku_like 15, stoplist 432; a top-60 table with capability / safety / org labels; a hand-curated shortlist of 10 safety evaluations spanning the five risk domains (WMDP, VCT, Cybench, CyberGym, Cyber Range, SHADE-Arena, Agentic Misalignment, MASK, StrongREJECT, BBQ; `research/system_card_evals.md` lines 77 to 90); 5 verbatim snippets per shortlisted evaluation (`python3 -c "import json; d=json.load(open('research/system_card_evals.json')); print(d['n_docs'], len(d['publishers']), d['domain_doc_counts'], d['dropped_by_filter'], len(d['candidates']))"`; `python3 -c "import json; print({k: len(v) for k, v in json.load(open('research/system_card_snippets.json')).items()})"`).
- Scenario construction: track 1 takes the 10-item shortlist plus one robot evaluation per ladder rung 3, 4, 5, 7, 8 (`studies/ai-safety-evals/scenarios_rationale.md`); track 2 maps two decisions onto the ladder, home manipulator L0-L9 and AV AEB L1, 4, 6, 8, 9, with the primary and supporting catalogue keys per rung in `attributes.catalog_keys` (`studies/sim2real/scenarios_rationale.md`). Every context fact carries its catalogue key or snippet source.
- Fact-check: track 1, 208 claims checked, 28 claim-level corrections in 24 text edits, 1 unverifiable claim removed, 7 of the 28 refuting a published number or attribution (`sed -n 5p studies/ai-safety-evals/factcheck.md`); track 2, 177 claims checked, 40 edits (35 corrections or precision fixes, 5 removals) (`sed -n 5p studies/sim2real/factcheck.md`). Titles and scenario counts unchanged by both. The VCT fee schedule found there contradicts `gaps.md` section 1 ("authoring cost ... never reported") and `catalog.json: gotting2025vct.cost_evidence`, both left as they were (factcheck.md, VCT item 2).
- Tests: 200 collected, hermetic (`uv run pytest --collect-only -q | tail -1`; `tests/conftest.py` blocks `claude`, `git` and every URL but the OpenRouter auth preflight).

## 7. Harness lessons

- Usage-limit outage. From 2026-09-29T00:03:55Z to 00:12:21Z the CLI returned exit 1 with a zero-usage envelope (`total_cost_usd 0`, `duration_api_ms 0`) on all but three calls of three concurrent g001 batches: 80 such attempts in ai-safety-evals (its 81st `cli:` row is a timeout at 02:46Z), 54 in sim2real, 1257 in business, all stored invalid and their slots pending again; 1388 of the 1391 cost nothing, the three calls in flight when the limit hit (two in sim2real, one in business) cost 0.17 to 0.18 USD each; a `cli: exit 1` is retried at once, so each pending slot burnt two such attempts (one business slot burnt one). The resume filled the eval studies to 223/225 slots each; the two still pending per study ended in `cli: timeout` during the resume (not retried by design) or a repeated JSON failure (`[sql: outage]` below). LEARNINGS iteration 3 says the harness "now gets a pause rule"; no such rule exists in the code (`grep -n 'usage\|pause' voi_rank/elicit.py voi_rank/providers/claude_cli.py` finds only the OpenRouter key print), so a repeat of the outage costs nothing but re-fills a batch with invalid rows and `health`'s JSON validity line (72 % and 80 % for the eval g001) counts them as failures; slot validity (99.1 %) is the number to read.
- Interruption safety. `claude -p` runs in its own session (`start_new_session=True`), so a terminal Ctrl-C reaches only the harness; on any exception in the main thread the pending slots are cancelled, a stop event blocks every retry and cuts backoffs short, the running calls are awaited and stored in one transaction per slot, a slot committed just before the interrupt is recognised by its id and not stored twice, a failed DB write is retried once then spilled to `<study>/elicit_unstored.jsonl` (`elicit.run_jobs`, `store_or_spill`; LEARNINGS review rounds 2 and 5). Paid work is never discarded; before the fix every in-flight call died with `killed by signal 2` and was re-launched paid.
- Member subsets. Pooling incoherent members yields a ranking that belongs to nobody: on track 1 the pooled p003 ranking correlates 0.27 / 0.26 / 0.33 with its haiku / opus+sonnet / opus subsets while sonnet and opus agree with each other at 0.75 per member and 0.99 as a pair against opus alone (`protocol_noise_matched.tex` matrix, `member_agreement.tex`). `mc --members` scores a subset as its own run (`runs.members_json`, sorted labels, NULL for all), `data_hash` covers exactly the fits drawn, every analysis takes the same `--members` and never crosses subsets, and the cross-protocol matrices carry `p003[opus+sonnet]` as its own column. The headline elicitor is sonnet+opus; haiku is the noisy baseline (dollar spread eightfold larger: B 5.14 against 0.67 on track 1).
- Matched comparisons and one change at a time. Range statistics grow with k (business p001 B spread 1.33 over the first 3 repeats, 1.87 over 5), so noise is compared at matched k; a protocol changes one thing (p002 anchor ratios, p003 Fermi decomposition, eval p002 log decades: all reverted on the target metric), and the hierarchy (p004) is a protocol, not a code path, so it is compared against p003 on the same members. Three prompt interventions on haiku failed to move the dollar spread; a larger elicitor did.
- Provenance guards. Runs 9 to 13 of the business study were scored from an uncommitted tree stamped with a clean hash and had to be dropped and re-made (`drop_runs`; runs 14 to 18 are byte-identical in results), which is why `mc` now refuses a dirty tree, stores `data_hash`, and the reproduction appendix prints both hashes; a declined or non-TTY plan writes nothing (in-memory copy), the preflight checks credentials before the first paid call, and a halted member costs at most one call per worker.

```python
# [sql: outage] per study
import sqlite3
from voi_rank import db
con = sqlite3.connect('file:studies/<study>/voi.db?mode=ro', uri=True); con.row_factory = sqlite3.Row
for r in con.execute("""SELECT p.name, substr(e.error,1,12) AS err, COUNT(*) AS n, MIN(e.created_at) AS first, MAX(e.created_at) AS last
    FROM elicitations e JOIN protocols p ON p.id=e.protocol_id WHERE e.error LIKE 'cli:%' GROUP BY p.name, err"""): print(dict(r))
print(sum(1 for (raw,) in con.execute("SELECT raw_response FROM elicitations WHERE error LIKE 'cli: exit 1%'") if db.envelope_cost(raw) == 0.0))
gid = con.execute("SELECT id FROM protocols WHERE name='g001'").fetchone()[0]     # slots still without a valid row
print(con.execute("""SELECT provider||':'||model, scenario_id, repeat_ix, error FROM elicitations e WHERE protocol_id=? AND NOT EXISTS
    (SELECT 1 FROM elicitations v WHERE v.protocol_id=e.protocol_id AND v.scenario_id=e.scenario_id AND v.provider=e.provider
     AND v.model=e.model AND v.repeat_ix=e.repeat_ix AND v.valid=1) GROUP BY scenario_id, provider, model, repeat_ix""", (gid,)).fetchall())
```

## 8. Open items found while writing this

- The business `g001` batch is in progress (section 5 snapshot) and unscored; the on-disk business `voi.db` has since been migrated (a read-only backup at 07:37Z carries `runs.members_json` and `protocols.stages_json`; the copy committed at `HEAD` does not).
- Two `g001` slots per eval study are pending (ai-safety-evals: opus scenario 5 repeat 0, haiku 14/4; sim2real: haiku 14/0 and 15/1). A re-run of step 5 fills them for under 1 USD and changes the `data_hash` of every g001 run that pools a filled member (all four g001 runs in ai-safety-evals; in sim2real the all-member run 4 and the haiku run 7, not runs 6 and 9).
- Resolved after writing: LEARNINGS iteration 3 said 7/15 track-1 decisions are "always respond" at the sonnet+opus medians; `plugin.tex` (run 5) shows 6 (Veo, id 13, is in the gate at eff 0.0195); commit `f695db7` corrected the entry to 6/15.
- The eval studies' generated directories mix runs (section 0, third bullet).
- The binary-vs-Gaussian plug-in comparison and the reuse count `n` are not implemented.

## Fact-check log

Checked 2026-09-29 07:37Z to 07:55Z at `HEAD` `f695db7` (a LEARNINGS-only commit after `98af5ee`). Eval databases opened with `mode=ro`; business read through a `sqlite3.backup` copy taken at 07:37Z, with the g001 snapshot re-cut at `created_at <= '2026-09-29T03:54:06+00:00'` (`created_at` is the store time, `db.insert_elicitation`). `[copy]` commands (`health`, `compare_models`, the plug-in and s,t snippets, section 3.1) ran on backups in a scratch directory. 181 claim units checked (a table row or a sentence carrying numbers, about 1,250 values): 25 corrected, 0 removed. Every other number reproduced exactly.

1. Section 0, chapter references. Before: `chapter/main.tex`, lines 188, 234, 281, 339, 511, 607, 682. After: `../chapter/main.tex`, lines 189, 235, 282, 340, 512, 608, 683. Evidence: `grep -n 'label{sec:' ../chapter/main.tex`; the old numbers are the `\section` lines one above each label, and `chapter/` does not exist inside `voi-rank/`.
2. Section 2.1, template diff. Before: business and eval templates "differ only in the `e` lines, the `$context` block and the `C` definition". After: also the evaluation / deployment-decision wording of `p, s, t, B, K`. Evidence: `diff studies/business/templates/elicitor.md studies/ai-safety-evals/templates/elicitor.md` (hunks 7,15c7,14 and 56,57c59,61).
3. Section 2.4, business g001 fit warnings. Before: 230. After: 236. Evidence: fit-warning rows of g001 with `created_at <= 03:54:06Z` = 236; the count was 230 between 03:45:44Z and 03:49:14Z, so the old cell came from an earlier moment than the 678/1020 and 99.22 USD cells, which reproduce at 03:54:06Z.
4. Section 2.4, ai-safety-evals g001 outage attempts. Before: "314 (81 in the outage)". After: 80. Evidence: `[sql: outage]` gives `cli: exit 1` n=80 (00:03:55Z to 00:06:04Z, all zero cost) and `cli: timeout` n=1 at 02:46:51Z.
5. Section 2.4, haiku decision-level B spread under p004. Before: "`113.00` (the AEB group; ...)". After: the median of its two groups, AEB 224.6, home manipulator 1.4. Evidence: per-group (max - min) / median of haiku's five decision-stage B p50s: AEB [1.5e6, 2e6, 4e6, 5e7, 9e8] gives 224.6, home [1.5e5 .. 7e5] gives 1.375; (224.6 + 1.4) / 2 = 113.0; sonnet 0.76 and opus 1.04 are the same two-group medians.
6. Section 3.4, business s, t band. Before: "`0.6 to 0.95`". After: s 0.68 to 0.96, t 0.55 to 0.98; 5th to 95th percentile 0.77 to 0.95 and 0.80 to 0.96. Evidence: `db.elicited_p50s` over the 340 valid p001 elicitations.
7. Section 3.4, LEARNINGS reference. Before: "a smaller drop than LEARNINGS iteration 3 states". After: first stated, corrected in `f695db7`. Evidence: `git show f695db7 -- LEARNINGS.md`. The p004 and p003 ranges themselves (0.35 to 0.78, 0.50 to 0.87; 0.45 to 0.82, 0.48 to 0.90) reproduce.
8. Section 4.1, question lines. Before: "template lines 69 to 76". After: 69 to 76 in the eval studies, 63 to 70 in business. Evidence: `grep -n '^- Q' studies/*/templates/elicitor_gauss.md`.
9. Section 4.3, noise ordering. Before: haiku > sonnet > opus "reproduces in the Gaussian one". After: except `L` on ai-safety-evals. Evidence: the table two lines above, L 1.62 / 1.71 / 1.39.
10. Section 4.4 reading, prior MAD. Before: 0.11 to 0.14. After: 0.11 to 0.12. Evidence: the member-matched rows with rho 0.81 to 0.92 carry MAD 0.12 (sonnet+opus) and 0.11 (opus); 0.14 is the p001-vs-g001 all-member row, which is not member-matched.
11. Section 4.4 reading, elicited t. Before: "the elicited `t` clusters on 0.85 to 0.95". After: sonnet+opus pooled t spans 0.64 to 0.91, s 0.60 to 0.91. Evidence: pooled p50 medians of run 5's members per scenario; only 6 of 15 lie in 0.85 to 0.95, so the narrow-band explanation does not hold for this comparison (it describes haiku p001, 0.80 to 0.95).
12. Section 4.4 reading, smooth-model agreement. Before: 0.77 to 0.94. After: 0.63 to 0.94 (0.77 to 0.94 on sim2real). Evidence: the among-model table above: quad-step 0.63 (ai run 4) and 0.64 (ai run 6).
13. Section 5 totals, outage cost. Before: "1257 zero-cost outage attempts". After: 1257 outage attempts, 1256 at zero cost (as the table row already said). Evidence: `[sql: outage]` on the business backup at the 03:54:06Z cut.
14. Section 5, Gaussian prompt size. Before: 10.3k characters. After: 13.6k to 14.3k rendered in the eval studies, 10.7k to 10.9k in business. Evidence: `len(elicit.render_prompt(...))` over every scenario; the eval template alone is 11,268 characters.
15. Section 5, reasoning strings. Before: 12. After: 13 (the state block and 12 answers). Evidence: the output contract at the end of `templates/elicitor_gauss.md`.
16. Section 5, opus output length. Before: "opus answers in about 1k output tokens". After: g001 medians opus 3.0k, haiku 23.7k to 25.2k, sonnet 27.4k to 28.4k; 1.2k is opus on the binary p003 prompt. Evidence: median `usage.output_tokens` of valid rows' `raw_response` per member and protocol in both eval databases.
17. Section 6, mining runtime. Before: about 15 s. After: 36 s on a re-run. Evidence: `time uv run python research/mine_system_cards.py --top 60 --out-dir <scratch>` (load average about 2.5).
18. Section 6, mining input. Before: "present, 5.4 MB, dated 2026-09-28". After: 5,554,176 bytes, modified 2026-09-29T07:46Z; the re-run reproduces 180 documents, 22 publishers, the domain counts, the filter drops, 1774 candidates and the snippets, and one top-60 row moved (METR DF 38 to 37). Evidence: `stat`, and `cmp` of the re-run outputs against `research/` (snippets identical, `system_card_evals.{json,md}` differ in that row). The original size and date cannot be checked any more.
19. Section 7, ai-safety-evals outage attempts. Before: 81. After: 80, the 81st `cli:` row being a timeout at 02:46Z. Evidence: as item 4.
20. Section 7, outage cost. Before: "all stored invalid at zero cost". After: 1388 of 1391 at zero cost; three calls in flight (two sim2real at 00:07:18Z and 00:08:52Z, one business at 00:05:03Z) cost 0.17 to 0.18 USD. Evidence: `db.envelope_cost` per `cli: exit 1` row; the three carry "You've hit your session limit" and nonzero `duration_api_ms`.
21. Section 7, "on every call". After: on all but three calls. Evidence: as item 20.
22. Section 7, two attempts per slot. After: one business slot burnt one. Evidence: per-slot count of outage attempts: ai {2: 40}, sim2real {2: 27}, business {2: 628, 1: 1}.
23. Section 8, business migration. Before: the on-disk business `voi.db` "predates the `runs.members_json` / `protocols.stages_json` migration". After: since migrated. Evidence: `pragma table_info` on `studies/business/voi.db` (read-only) lists both columns; `git show HEAD:studies/business/voi.db` lacks them.
24. Section 8, data_hash scope. Before: filling the pending slots "changes every g001 `data_hash`". After: every g001 run pooling a filled member (all four in ai-safety-evals; runs 4 and 7 in sim2real, not 6 and 9). Evidence: the pending sim2real slots are both haiku (14/0, 15/1), and runs 6 and 9 pool opus+sonnet and opus.
25. Section 8, the 7/15 item. Before: "LEARNINGS iteration 3 says 7/15". After: said 7/15, corrected to 6/15 in `f695db7`. Evidence: `git show f695db7`; at the sonnet+opus pooled medians `pi* <= pi0` holds for ids 1, 2, 3, 5, 11, 14 only (for example id 1: `pi*` 0.115, `pi0` 0.131), 9 are in the gate.

Checked and left unchanged, for the reader of the snapshot:

- Business g001 has moved on since 03:54Z: at 07:37Z 2402 attempts, 907/1020 valid slots, 135.25 USD, and a second zero-cost `cli: exit 1` burst of 232 attempts between 04:55Z and 04:58Z. The section 5 numbers stay as a timestamped snapshot.
- "Always respond" (section 3.4) and "on the fence" (section 1.3) follow from the medians: the six track-1 ids above have `pi* <= pi0`; sim2real p003 has all 15 rungs in the gate at the pooled medians with `|p - pi*|` 0.01 to 0.11.
- Every rank correlation is over the n stated (15, 17, 55 or 68).
