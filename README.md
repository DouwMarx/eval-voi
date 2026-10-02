# voi-rank

Are physical-AI safety evaluations worth the money? One release decision per
evaluation, the expected value of sample information (EVSI) of one run,
seven parameters elicited from an ensemble of language models in two
independent prompts, propagated by Monte Carlo over the combined belief, and
compared with the LLM safety evaluations that system cards report.
`docs/DESIGN.md` is the authority on the model, the terminology, the
elicitation and the outputs.

## Install

- Python >= 3.11, [uv](https://docs.astral.sh/uv/), `latexmk` for the
  reports; the `claude` CLI (authenticated) only for `claude_cli` members,
  which the current protocols do not use.
- `uv sync` installs numpy, scipy, matplotlib, pyyaml (+ pytest, ruff, poethepoet).
- `.env` (copy `.env.example`, git-ignored): `OPENROUTER_API_KEY`, the
  dedicated key of the final run. Optional: `SSL_CERT_FILE`,
  `VOI_CLI_TIMEOUT_S`, `VOI_OUTAGE_SLEEP_S`, `VOI_OUTAGE_MAX_WAIT_S`.
- Tests: `uv run pytest -q`. Lint: `uv run ruff check .`. No test or default
  command reaches the network.

## Layout

```
voi_rank/              model, fit, mc, db, study, elicit, validate, sensitivity, dotenv, pricing,
                       providers/{claude_cli, openrouter}, analysis/{summary, figures, tables, macros}
studies/safety-evals/  scenarios.json, include.yaml, protocols/, templates/, voi.db, report/
research/              literature catalogue, refs.bib, system-card mining, scenarios_draft/ (the
                       fact-checked drafts, SELECTION.md), sources/ (cached source texts)
archive/               iteration-2026-09-30/ (the iteration's protocols p001-p003 and templates);
                       read-only, never analysed
scripts/               build_scenarios.py, regen.sh, build_paper.sh, check_pages.py
docs/                  DESIGN.md, FUTURE_WORK.md
```

A study is self-contained: `scenarios.json`, `protocols/` (immutable YAML
files), `templates/` (the two prompt templates) and `voi.db` (every
scenario, prompt hash, raw response, fit, run and result). `--study` defaults
to `studies/safety-evals`.

`scenarios.json` is generated: `uv run python scripts/build_scenarios.py`
rebuilds it from `research/scenarios_draft/*.json`, keeping the drafts that
`studies/safety-evals/include.yaml` marks `include: true` (every draft listed
once, with a reason; the selection rule, scores and counts are in
`research/scenarios_draft/SELECTION.md`). Each entry carries `title, agent,
decision, theta_definition, instrument` (required), `group` ("physical AI" |
"LLM"), `attributes` {risk_domain, level, eval_family}, `sources`,
`decision_facts`, `instrument_facts` (curated sentences with [key] citations)
and the two context fields the prompts render, which are the facts without
their markers. Edit the drafts or the include list, not the file.

## The model (DESIGN section 3)

Seven elicited parameters. Decision prompt: prior `p`, gain `B` from
mitigating when the hazard is present, loss `K` from mitigating when it is
absent, `B` and `K` valued for society. Instrument prompt: sensitivity `s`,
specificity `t`, build cost `C_build`, run cost `C_run`. Beta fits for `p, s,
t`, lognormal for the rest, fitted once at elicitation time. Per draw
(`voi_rank/model.py`): EVSI, EVPI, EVSI* = (B+K) p(1-p)|s+t-1| (the maximum
EVSI over the threshold at fixed stakes; code key `EVSI_ind`), C = C_build +
C_run, eta = EVSI/C, eta* = EVSI*/C (code key `eta_ind`, the primary ranking
metric), eta_run = EVSI/C_run, and the break-even run count n* = C_build /
(EVSI - C_run), infinite where EVSI <= C_run.

## Run order from a clean clone

1. `uv run python scripts/build_scenarios.py` writes `studies/safety-evals/scenarios.json`.
2. `uv run python -m voi_rank.elicit --study studies/safety-evals --protocol final --dry-run`
   plans on an in-memory copy of the DB: the pending slots per member and
   prompt, the cost estimate (stored attempt costs, else OpenRouter catalogue
   prices, else `unknown`) and the first rendered prompt of each kind. No
   provider is called and nothing is written but the price cache. It warns
   when a prompt would render an empty scenario field. `--stage
   decision|instrument`, `--k N`, `--members a:b,c:d` and `--scenarios
   all|seed|1,2,3` narrow the plan.
3. `uv run python -m voi_rank.elicit --study studies/safety-evals --protocol final --yes --workers 8`
   prints the same plan, refuses a prompt that would render an empty field,
   checks the key, then seeds the scenarios, registers the protocol and
   submits. A slot is (scenario, protocol, member, repeat, prompt); slots
   with a valid answer are skipped, so a re-run resumes. Then the same with
   `--protocol final_noctx` (the no-context ablation).
4. Commit: `voi_rank.mc` refuses uncommitted code under `voi_rank/`,
   `pyproject.toml` or `uv.lock` unless `--allow-dirty`.
5. `uv run python -m voi_rank.mc --study studies/safety-evals --protocol final`
   (`--seed 42 --draws 100000` by default) draws the combined belief, stores
   the run and prints every scenario's eta quantiles ordered by the single
   estimate. Then the same with `--protocol final_noctx`.
6. `scripts/regen.sh` analyses the latest run of `PROTOCOL` (default
   `final`) into `report/generated/` and of `NOCTX_PROTOCOL` (default
   `final_noctx`, skipped without a run) into `report/generated/noctx/`:
   `fig_*.pdf`, `tab_*.tex`, `macros.tex` (every cited number as `\voi...`,
   `\voinoctx...` for the ablation) and `summary.json`. It re-draws each run
   and verifies it against the stored quantiles; it never writes the DB.
   `DRAWS=N` subsamples for speed.
7. `scripts/build_paper.sh studies/safety-evals` builds the paper
   (`report/main.pdf`, fails on an undefined reference or a body over 4
   pages); `scripts/build_paper.sh studies/safety-evals/report/extended`
   builds the extended report. `report/build_refs.py` rewrites `refs.bib`
   from the cited keys first and fails on a key without a DOI, arXiv id or
   URL. The PDFs are build products and are not committed.

If HTTPS to OpenRouter fails with a certificate error under uv's Python,
set `SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt` in `.env`.

## Protocols

`protocols/final.yaml` is the final run: OpenRouter, six members from six
developers, `k_repeats: 1`, `reasoning_effort: medium` for every member, one
pinned endpoint each, curated context. `protocols/final_noctx.yaml` is
identical except `context_mode: none`: neither prompt carries the curated
facts or their heading. Each registers only when named with `--protocol`.

```yaml
name: final
stages:
  - name: decision                      # once per scenario
    template_path: templates/decision.md
    params: [p, B, K]
    group_key: self                     # self | group | attributes.<key>
  - name: instrument                    # once per scenario
    template_path: templates/instrument.md
    params: [s, t, C_build, C_run]
template_vars:                          # substituted into the templates
  anchors_decision: ''                  # '@file:<study path>' would inline a file; '' = none
  anchors_instrument: ''
  context_mode: curated                 # curated | none
members:
  - {provider: openrouter, model: openai/gpt-6-luna, k_repeats: 1, reasoning_effort: medium, provider_order: [azure]}
scenarios: all                          # optional scope: all | seed | 5,13,22
```

The decision prompt renders `$agent $decision $theta_definition
$decision_context` and the template variables, never the instrument, the
title or the instrument context; the instrument prompt renders `$title
$agent $decision $theta_definition $instrument $context` (the scenario's
`instrument_context`) and the template variables. A template naming anything
else is refused; a variable named `decision_*` or `anchors_decision` renders
only in the decision template, `instrument_*` or `anchors_instrument` only in
the instrument one. A protocol file is immutable once registered: both
templates, every inlined file, the template variables, the stages, the
members and the scope are hashed and a changed file is refused (make a new
protocol file). Scenarios are seeded from `scenarios.json` at every run; a
scenario without elicitations is refreshed in place, an elicited one is
frozen (change its title to make a new row; the old one is retired, kept
with its elicitations). `voi_rank.mc` seeds too, so a scenario cut from
`scenarios.json` is retired by the next Monte Carlo run; runs and the
analysis use active scenarios only.

Validation of an answer (DESIGN section 4): strict JSON with exactly the
prompt's parameters, each with `reasoning` and `p5 < p50 < p95`;
probabilities in (0, 1), USD > 0, median `s` > 1 - median `t`, prior median
in [0.001, 0.999]. Error classes in `elicitations.error`: `json`, `schema`,
`constraint`, `fit`, `refusal`, `truncated`, `cli`, `http`, `api`,
`provider`. A failed attempt is retried once (at once for answer failures,
after Retry-After for HTTP 429/5xx, never for a rejected request or an error
of the member's environment, which halts that member). Every attempt is
stored with its raw response and cost. Ctrl-C cancels the pending slots,
waits for the running calls and stores them; paid work is never discarded.
A DB write that fails twice spills the slot to `<study>/elicit_unstored.jsonl`.

## What a run stores

`runs`: seed, draw count, `code_hash` (git HEAD of the code paths, `-dirty`
when uncommitted), `data_hash` (digest of the valid elicitations drawn),
`members_json`. `results`: per scenario the q05..q95 of every metric of the
model section, and the probabilities `p_positive` = P(EVSI > C), `p_changes`
= P(EVSI > 0) and `p_top5` (rank <= 5 by eta) as their own rows with `q50`
holding the probability. `sensitivities`: the Spearman of each parameter's
draws against eta. `mc.replay_efficiency` recomputes a run's eta draws from
the DB alone and refuses when the valid elicitations changed since.

`voi.db` also holds the iteration's rows (protocols p001 and p002 and three
p001 runs, elicited with claude_cli). They are not analysed; the archived
protocol files describe them.

## OpenRouter

Nothing calls OpenRouter unless a protocol lists an `openrouter` member. The
key's presence is checked before the plan is printed and the key itself is
verified with one free request after the run is confirmed.

Each `openrouter` member may set request options next to `provider`,
`model` and `k_repeats` (all optional):

| field | default | sent as |
|---|---|---|
| `reasoning_effort` | none | `reasoning.effort` (low, medium, high) |
| `max_tokens` | 32000 | `max_tokens` (high on purpose: reasoning models spend many thousands of tokens; length is set with `reasoning_effort`) |
| `json_mode` | true | `response_format: json_object` plus `provider.require_parameters` |
| `provider_order` | none | `provider.order` with `allow_fallbacks: false` (endpoint tags from `GET /api/v1/models/<id>/endpoints`) |
| `temperature` | omitted for `openai/*`, else 1.0 | `temperature`; `omit` sends none (an endpoint without the parameter) |
| `est_output_tokens` | 6000 | not sent: the cost estimate's output tokens per call |

The user message carries an ephemeral `cache_control` breakpoint (Anthropic
needs it; other providers ignore it). An answer cut at `max_tokens` is error
class `truncated` and retried once. The plan prints a cost per member: the
mean stored cost of its past attempts, else catalogue prices (`GET
/api/v1/models` and the pinned endpoint's price, cached in
`<study>/.openrouter_models.json` for 24 h; offline, the prices in
`research/ensemble_members.json`) times the prompt length / 4 input tokens
and `est_output_tokens` output tokens, as low / central / high with output
x0.5 / x1 / x2.

## Archive

`archive/iteration-2026-09-30/` holds the protocols and templates of the
iteration runs whose rows remain in `studies/safety-evals/voi.db` (protocols
p001 and p002; not analysed). The two pilot studies that preceded this one
and the earlier business-decision study are kept outside the repository.
Never write to a database under `archive/`: `Study.connect` refuses a study
whose path has an `archive` component, so `elicit` and `mc` exit before
touching the file.
