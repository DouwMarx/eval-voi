# voi-rank

Ranks scenarios by the value of a single measurement sold to a single agent
facing a single binary decision: expected value of sample information (EVSI)
per dollar of measurement cost. Parameters are elicited from LLMs under
frozen prompt protocols (optionally an ensemble of models), fitted to
distributions, and propagated by Monte Carlo. See `spec.md` for the model and
`LEARNINGS.md` for the lab notebook.

## Install

- Requires Python >= 3.11, [uv](https://docs.astral.sh/uv/), `latexmk` for
  reports, and the `claude` CLI (authenticated) for `claude_cli` elicitation.
- `uv sync` installs numpy, scipy, matplotlib, pyyaml (+ pytest, ruff, poethepoet).
- Optional `.env` settings (copy `.env.example`, git-ignored): `OPENROUTER_API_KEY` and
  `VOI_CLI_TIMEOUT_S` (wall-clock cap per `claude -p` call, default 600 s).
- `uv run poe test` runs the tests, `uv run poe lint` runs ruff.

## Layout

```
voi_rank/                 library: model, fit, mc, sensitivity, db, study, elicit, propose,
                          drop_runs, validate, providers/{claude_cli,openrouter},
                          gaussian, gauss_fit (the Gaussian-state family, see below),
                          analysis/{figures,tables,extra,health,compare_models}
tests/
studies/<name>/           one study = scenarios.json, protocols/, templates/, voi.db, report/
  business/               the original v1 study (68 business scenarios, protocols p000..p004)
  ai-safety-evals/        track 1
  sim2real/               track 2
templates/corl_2026/      conference template
research/                 shared literature and system-card mining
```

A study is self-contained: `scenarios.json` (the scenario list), `protocols/`
(immutable YAML protocol files), `templates/` (prompt templates referenced by
protocols, paths relative to the study root), `voi.db` (every scenario,
prompt hash, raw response, fit, run, result) and `report/` (LaTeX, with
`report/generated/` written by the analysis scripts).

`scenarios.json` is a list of objects: `title, agent, decision,
theta_definition, instrument` (required), `context` (factual background
substituted into the template as `$context`), `domain_tags`, `group` (short
label for figure colouring), `attributes` (free JSON, e.g. `level`), and
optionally `manual` (hand percentiles for the `p000_manual` protocol).

## Run order (from the repo root; `--study` defaults to `studies/business`)

1. `uv run pytest`
2. `uv run python -m voi_rank.elicit --study studies/X --manual [--dry-run]` (optional: hand percentiles; `--dry-run` lists what would be loaded and writes nothing; a study without `protocols/p000_manual.yaml` or without any `manual` key is reported and gets no `voi.db`)
3. `uv run python -m voi_rank.propose --study studies/X --n 6 --yes [--dry-run]` (optional: generate scenarios via claude_cli; needs `templates/proposer.md` in the study, else it exits with a message; prints the plan, calls and estimated cost first and needs `--yes` or a TTY confirmation like step 5; the plan is made on an in-memory copy, so a declined plan or `--dry-run` creates nothing, not even `voi.db`)
4. `uv run python -m voi_rank.elicit --study studies/X --protocol p001 --dry-run` (plan on an in-memory copy of the DB: render prompts, list pending slots per member with the effective k, call nothing, write nothing, not even `voi.db`)
5. `uv run python -m voi_rank.elicit --study studies/X --protocol p001 --yes [--k 5] [--members claude_cli:haiku]` (prints the plan and estimated cost, then submits; without `--yes` it asks for confirmation on a TTY and aborts otherwise; the plan is made on an in-memory copy, so a declined plan writes nothing, not even `voi.db`, and registers no protocol; only a confirmed run whose preflight passed opens the real DB)
6. `uv run python -m voi_rank.mc --study studies/X --protocol p001 --seed 42 --draws 100000` (refuses to run with uncommitted changes under `voi_rank/`, `pyproject.toml` or `uv.lock`, or when git cannot report the revision at all, unless `--allow-dirty`, which stores `code_hash` as `<hash>-dirty` or `unknown`)
7. `uv run python -m voi_rank.analysis.health --study studies/X --protocol p001 [--compare p002]`
8. `uv run python -m voi_rank.analysis.figures --study studies/X --protocol p001` and `uv run python -m voi_rank.analysis.tables --study studies/X --protocol p001` (the latest run of that protocol, default `p001`; `--run ID` overrides; both print `run <id> (protocol <name>)`; a run made by the v1 model, without a `data_hash` or with sensitivities for the retired parameter `e`, is refused: re-run step 6)
9. `uv run python -m voi_rank.analysis.extra --study studies/X --protocol p001` (same run selection; the eval-study analyses, each skipped with a printed reason when its inputs are absent and its stale outputs removed): `fig_level_uplift.pdf` + `level_uplift.tex` (adjacent-rung marginals within one decision, for groups whose leveled scenarios share the agent, decision and theta text: common-random-number draws, p, B, K once per ladder, s, t, C per rung, marginal efficiency as median dEVSI / median dC with P(dC > 0), P(dEVSI > 0) and P(dEVSI > dC)), `fig_within_group_consistency.pdf` + `consistency.tex` (same groups: is the elicited p, B, K flat across levels while s, t, C move), `fig_domain_map.pdf` + `domain_summary.tex` (needs `attributes.risk_domain`), `fig_member_agreement.pdf` + `member_agreement.tex` (protocols with more than one member), `simplicity.tex` + `macros_extra.tex` (does the EVPI/C ranking reproduce the EVSI/C ranking, both as medians of the per-draw ratio the run stores; needs a run with the `evpi_efficiency` metric; the global |rho| rows count the scenarios with a defined rho) and `protocol_noise_matched.tex` (cross-repeat spread per member over the first 3 valid repeats and, where a member holds more on any scenario, over all of them, labelled with the count pooled per scenario, `min..max` where scenarios differ; the compare matrix takes each protocol's latest run the v2 analyses accept). Nothing here replays the run, so repeats added after it never abort an analysis.
10. `cd studies/X/report && latexmk -pdf main.tex`

Elicitation resumes: a slot is (scenario, protocol, provider, model,
repeat) and slots with a valid response are skipped, so re-running step 5
only fills what is missing. Before submitting, step 5 checks that every
selected provider has its credentials (a missing OpenRouter key aborts with
zero calls made) and prints the plan: pending slots per member and the
estimated cost (slots times the member's mean stored cost per attempt under
protocols of the same model kind in this study, or `unknown`; a first `g001`
batch has no history to quote). Once confirmed, and before `voi.db` is touched, a
run with a `claude_cli` member checks `claude auth status` (free; a CLI that
is not logged in aborts with zero calls; the CLI does not verify an
`ANTHROPIC_API_KEY`, see the timeout rule below) and a run with an
OpenRouter member verifies the key against the free `GET /api/v1/auth/key`
endpoint; a rejected (401/403) or unverifiable key aborts before the first
paid call. A failed attempt is retried once: at once for
json/schema/constraint/fit failures, after the server's `Retry-After` (else
5 s, capped at 120 s and the cap recorded in the attempt's error) for HTTP
429/5xx and transport errors, and never for a rejected request (HTTP
400/403: invalid params, or a guardrail / moderation flag on that one
prompt; the slot is stored invalid, unbilled, and pending again on the next
run), for an error of the member's environment (HTTP 401/402/404: auth,
credit, unknown model id; a `claude` executable missing or not logged in)
or for a CLI call that did not finish (timeout, killed by a signal). Every
attempt is stored with its raw response; a provider exception or a crashed
job is stored as an invalid attempt and the run continues. A member has its
pending slots cancelled on an environment error, when its rejected requests
name the key or permissions or reach a second distinct scenario, or after
two consecutive CLI timeouts (an invalid `ANTHROPIC_API_KEY` makes the CLI
hang with no output; the cap per call is `VOI_CLI_TIMEOUT_S`, default 600 s,
from the environment or `.env`). The cancellation happens as soon as the
main thread sees the result; with `--workers N` up to N of its calls can
already be in flight, so it costs at most one call per worker (these errors
are not billed; the slots are pending again on the next run).

Paid work is never discarded: on Ctrl-C or any error in the main thread the
pending slots are cancelled, no retry is launched (a retry's backoff is cut
short), the running calls are awaited and their results stored, and the
error is re-raised (re-run to resume). `claude -p` children run in their own
session, so the terminal's Ctrl-C (SIGINT to the foreground process group)
reaches only the harness and the running calls finish; a harness killed
with SIGKILL leaves them to finish unobserved. A further Ctrl-C during the
wait is reported and ignored, and a slot the interrupt caught between its
commit and its bookkeeping is recognised in the DB, never stored twice. A DB write that fails is retried once after 1 s; if it still
fails, the slot's attempts are appended to `<study>/elicit_unstored.jsonl`,
the path is printed and the run stops. `propose` follows the same rule
(running calls are awaited and their scenarios inserted; a domain the DB
refuses during that salvage is appended to `<study>/propose_unstored.jsonl`
and the others are still inserted).

Scenarios come from `scenarios.json` at every run: a seed row whose text or
metadata changed is refreshed in place while it has no elicitations, and is
frozen (a differing file is an error) once it has any. To change a frozen
scenario, give it a new title: the new row is seeded and the old one is
retired (kept with its elicitations, printed as `retired`, left out of the
`all` and `seed` selections, restored if its title returns). A dry run
reports these as `would refresh` / `would be retired` and changes nothing.

## Protocols and ensembles

A protocol YAML is immutable once registered (template hash, member list,
scenario scope and model kind are checked; change something, make a new
file):

```yaml
name: p001
model: binary                             # optional: binary (default) | gaussian
template_path: templates/elicitor.md      # relative to the study root
members:
  - {provider: claude_cli, model: haiku, k_repeats: 5}
  - {provider: openrouter, model: openai/gpt-4o-mini, k_repeats: 3}
scenarios: all                            # optional scope: all | seed | 5,13,22
notes: one change per protocol
```

The legacy form `model_alias: haiku` + `k_repeats: 3` is read as a single
`claude_cli` member (`model_alias: manual` is the hand-percentile member of
`p000_manual`, never a callable provider, and that name takes no other
member). Hand percentiles are frozen per scenario, not per file: a loaded
scenario whose `manual` block changed is refused by `--manual`, a scenario
with a new `manual` block loads under the same `p000_manual` at any time,
and metadata edits to un-elicited scenarios still refresh. `scenarios` scopes the protocol
(stored, part of the immutability check) and is the default selection of
step 4/5; `--scenarios` overrides it with a printed warning. Monte Carlo
pools every valid (member, repeat) elicitation of a scenario into one
equal-weight mixture per parameter, so a member with more valid repeats
carries more weight. `--k N` (N >= 1) overrides every member's `k_repeats`;
`--members a:b,c:d` restricts a run to those members.

## Gaussian-state family (protocols with `model: gaussian`)

A second framing of the same scenarios, from the chapter sections "The
linear-Gaussian model", "Action models: one state, one sensor, three
decisions" and "An elicitation protocol for the Gaussian-state model". The
state is continuous, `theta ~ N(mu0, sigma0^2)` in the expert's own unit with
bad-is-high; the instrument reports `y = theta + v`, `v ~ N(0, r)`, so one
number `x = sqrt(r)/sigma0` replaces `(s, t)` and `R^2 = 1/(1 + x^2)` is the
fraction of prior variance one measurement removes (a common-mode bias
`sigma_b` that repeats would not reveal adds `sigma_b^2 (1 - 2/pi)` to `r`).
A threshold `theta_c` gives `d = (mu0 - theta_c)/sigma0` and `p = Phi(d)`.
From one elicitation four action models are computed on every MC draw
(`voi_rank/gaussian.py`, each formula annotated with its chapter equation):

- `quad`: graded response, loss `c |a - theta|^k`: `EVPI = L`,
  `EVSI = L (1 - (1 - R^2)^(k/2))` (`L R^2` at `k = 2`), with `L = c_k sigma0^k`
  the minimal expected loss under the prior (the optimal action shifts by a
  fixed multiple of `sigma0` under asymmetric costs; `gaussian.min_expected_loss`).
- `kg`: respond or not, payoff linear in `theta - theta_c`:
  `EVSI = kappa sigtilde Psi(d/R)`, `EVPI = kappa sigma0 Psi(d)`,
  `Psi(z) = phi(z) - |z| Phi(-|z|)`.
- `step`: respond or not with the step payoff `B` / `-K`, the agent sees the
  continuous reading: the chapter's one-dimensional integral, evaluated
  exactly through the decision-optimal cutoff (the binary closed form at the
  orthant probabilities of correlation `R`; the 64-node Gauss-Hermite
  quadrature of the design is kept as `voi_step_gh` for the tests only, it
  misses up to 1.6% of `B + K` at `R^2 = 0.99` and 4% at `R^2 = 0.999`). The primary ranking metric
  of a Gaussian run is `eff_step = EVSI_step / C`.
- `stepfix`: the same decision with a pass/fail report at the fixed mark
  `theta_c`: `s, t` derived from `(d, R)`, then `voi_rank.model.voi(p, s, t, B, K)`.
  This is the model that maps one-to-one onto the binary protocol.

The elicitor (`templates/elicitor_gauss.md`, protocol `g001` in every study)
first names the continuous state variable and its unit, then answers eight
over-determined questions with reasoning before numbers: the `p5/p50/p95`
of `theta`; `theta_c` and `P(theta > theta_c)` (must equal `Phi(d)`); three
routes to `x` (test-retest width `W_rr`, the 90% width after the result
`W1`, the probability `c` that the result moves the estimate by more than
half the prior half-width); four loss numbers (under- and over-response by
one and two `sigma0`, giving the exponent `k` per side and, by minimising
the expected loss over the action, `L`; `x` pools its routes by the median
of their logs); `kappa
sigma0`; `B`, `K`; `sigma_b`; and the `C` triple. The two anchors are the
binary anchors re-expressed as Gaussian answers (`p = Phi(d)` reproduces
their `p50` of `p`). `voi_rank/gauss_fit.py` validates the JSON (errors
`schema:` / `constraint:` / `fit:` as for the binary payload) and stores
`g_mu0, g_sigma0, g_d, g_x, g_k, g_L, g_kappa_sigma0, g_B, g_K,
g_sigma_b_rel` as `point` rows (`fit_params {"value": v}`, MC draws them as
constants, so the mixture over repeats is the empirical distribution of the
repeat values) and `C` as the usual lognormal; `fit_residual` carries the
over-determination residual of the questions behind each row (theta
asymmetry, `d` mismatch, `x` route spread in log units, `k` mismatch) and
`fit_warning` flags a residual past its threshold (0.25, 0.5 prior sd, 0.5, 1.0) or
a `c` route too close to the Gaussian bound to resolve `x` (`c > 0.40`; the
bound is 0.4108). Cross-repeat noise is `(max - min) / pooled p50` per
quantity except `d`, `sigma_b/sigma0` and `mu0`, which are reported as a
`max - min` in prior-sd units (`fit.GAUSS_SPREAD_SCALE`), since `d` crosses
zero exactly where EVSI is largest.

Run order, per study (steps 1, 6 to 9 of the main run order apply unchanged;
the binary-only analyses of `extra` are skipped with a printed reason):

1. `uv run python -m voi_rank.elicit --study studies/X --protocol g001 --dry-run`
2. `uv run python -m voi_rank.elicit --study studies/X --protocol g001 --yes`
3. `uv run python -m voi_rank.mc --study studies/X --protocol g001` (stores
   `EVSI_<m>`, `EVPI_<m>`, `eff_<m>` for `m` in quad, kg, step, stepfix, plus
   `R2, d, x, k, p_derived, s_derived, t_derived, C`; `p_positive =
   P(EVSI_step > C)`; sensitivities against `eff_step` of the quantities
   that enter the metrics, i.e. all but `g_mu0` and `g_sigma0`; `p_top10`
   on `eff_step`)
4. `health`, `figures`, `tables`, `extra` with `--protocol g001`
5. `uv run python -m voi_rank.analysis.compare_models --study studies/X [--binary p001] [--gaussian g001]`
   writes `compare_models.tex` (Spearman and Kendall of median efficiency,
   binary vs each action model and among them, top-10 overlaps, and the
   gate-agreement confusion table between binary median EVSI = 0 and
   stepfix median EVSI = 0), `fig_compare_models.pdf` (binary vs stepfix
   efficiency, log-log, by group), `fig_derived_pst.pdf` (derived vs
   elicited `p, s, t`), `consistency_gauss.tex` (the residual distributions
   and their Spearman with the cross-repeat spread of the quantity they
   check) and `macros_compare.tex` (`\voiGaussRhoQuad`, `\voiGaussRhoKg`,
   `\voiGaussRhoStep`, `\voiGaussRhoStepfix`, `\voiGaussTopOverlapStepfix`,
   `\voiGaussRhoP/S/T`, `\voiGaussGateAgree`, `\voiGaussN`).

## OpenRouter

Nothing calls OpenRouter unless a protocol lists an `openrouter` member.
Then set `OPENROUTER_API_KEY` in the environment or copy `.env.example` to
`.env` (git-ignored; quoted values and trailing `# comments` are handled)
and fill it in. The key's presence is checked before the plan is printed and
the key itself is verified with one free request after the run is confirmed,
so a wrong key costs nothing; it is read only for the calls and never printed.
Calls go through `urllib` to
`https://openrouter.ai/api/v1/chat/completions` with temperature 1.0 and the
full response body (which always carries `usage.cost`) stored as the raw
elicitation record. The test suite monkeypatches the HTTP layer; no test or
default command reaches the network.

## Reproduction

Given a study's committed `voi.db`, steps 6 to 9 reproduce every number,
figure and table exactly (the stored seed makes the MC deterministic; a rerun
mints a fresh run id in the report's reproduction appendix). Each run stores
two provenance hashes: `code_hash`, the git HEAD of the code paths
(`voi_rank/`, `pyproject.toml`, `uv.lock`), suffixed `-dirty` when they have
uncommitted changes (step 6 refuses such a tree unless `--allow-dirty`; a
rewritten `voi.db` or report never dirties it, since study inputs are frozen
by the protocol template hashes and prompt hashes), and `data_hash`, the
SHA-256 over the sorted (elicitation id, parameter, fitted parameters) of the
valid elicitations the run drew from (equal hashes mean the same inputs).
The report macros carry both (`\voiCodeHash`, `\voiDataHash`) and the
reproduction appendix prints them. A run whose provenance is wrong (made
from an uncommitted tree before the dirty check existed) is removed with
`uv run python -m voi_rank.drop_runs --study studies/X --runs 9-13 [--yes]`
(prints each run's protocol, hashes and row counts, asks for confirmation,
deletes its runs/results/sensitivities rows and VACUUMs; elicitations are
never touched) and re-made by step 6. Steps 2, 3 and 5 call an LLM and are
not bit-reproducible; their outputs are stored in the DB with prompt hashes
and raw responses. Databases created by v1 are
migrated in place on first connect (new columns added, legacy elicitations
tagged as `claude_cli` / the protocol's model; a v1 database holding two
valid rows for one slot is refused with the repair SQL printed).
