# voi-rank

How much is a safety evaluation worth, per dollar, to the developer who must
decide whether to release? One deployment decision per scenario, the expected
value of sample information (EVSI) of one run of the evaluation, parameters
elicited from an ensemble of language models in two independent prompts,
propagated by Monte Carlo over the pooled belief. `docs/DESIGN.md` is the
authority on the model, the elicitation and the outputs; `LEARNINGS.md` is the
lab notebook.

## Install

- Python >= 3.11, [uv](https://docs.astral.sh/uv/), the `claude` CLI
  (authenticated) for `claude_cli` members, `latexmk` for the report.
- `uv sync` installs numpy, scipy, matplotlib, pyyaml (+ pytest, ruff, poethepoet).
- Optional `.env` (copy `.env.example`, git-ignored): `OPENROUTER_API_KEY` for
  `openrouter` members, `VOI_CLI_TIMEOUT_S`, `VOI_OUTAGE_SLEEP_S`,
  `VOI_OUTAGE_MAX_WAIT_S`.
- `uv run poe test` runs the tests, `uv run poe lint` runs ruff.

## Layout

```
voi_rank/              model, fit, mc, db, study, elicit, validate, sensitivity, dotenv,
                       providers/{claude_cli, openrouter}, analysis/{summary, figures, tables, macros}
studies/safety-evals/  scenarios.json, protocols/, templates/, SCENARIOS_TODO.md (voi.db and report/ later)
research/              literature catalogue, refs.bib, system-card mining
archive/               business/ (the external chapter reads its voi.db) and pilots/ (frozen at tag
                       pilot-2026-09-30; read-only, not re-runnable by the current code)
scripts/               regen.sh, build_paper.sh, check_pages.py
docs/                  DESIGN.md, QUESTIONS.md
```

A study is self-contained: `scenarios.json`, `protocols/` (immutable YAML
files), `templates/` (prompt templates and the files they inline, paths
relative to the study root) and `voi.db` (every scenario, prompt hash, raw
response, fit, run and result). `--study` defaults to `studies/safety-evals`.

`scenarios.json` is a list of objects (DESIGN section 5): `title, agent,
decision, theta_definition, instrument` (required), `group` ("physical AI" |
"frontier model"), `attributes` {risk_domain, level, eval_family, ...},
`sources` (list of {key, kind, ref, role}), `decision_facts`,
`instrument_facts`, `decision_context` (rendered by the decision prompt),
`instrument_context` (rendered as `$context` by the instrument prompt),
`domain_tags`. The whole entry is stored as `raw_json`.

## The model (DESIGN section 3)

Eight elicited parameters: decision level `p, B, K`; instrument level `s, t,
C_build, C_run, n`. Beta fits for `p, s, t`, lognormal for the rest, fitted
once at elicitation time. Per draw: EVSI, EVPI, the indifference value EVSI°
= (B+K) p(1-p)|s+t-1| (an inverted evaluation is read the other way
round, as EVSI is), C = C_build + C_run, eta = EVSI/C, eta° = EVSI°/C,
eta_run = EVSI/C_run, net_n = n EVSI - C_build - n C_run, eta_n = n EVSI /
(C_build + n C_run), the break-even reuse count n* = C_build/(EVSI - C_run)
(infinite where EVSI <= C_run) and pays = 1[n >= n*] (`voi_rank/model.py`).

## Run order (from the repo root)

1. `uv run pytest -q`
2. `uv run python -m voi_rank.elicit --study studies/safety-evals --protocol p001 --dry-run`
   plans on an in-memory copy of the DB: both stages' pending slots per
   member, the cost estimate (from the members' stored attempt costs,
   `unknown` without history) and the first rendered prompt of each stage;
   nothing is called or written, not even `voi.db`. It warns when a planned
   prompt would render an empty scenario field (p001's decision prompt
   renders `decision_context`, empty until `decision_facts` are written:
   `SCENARIOS_TODO.md`). `--stage
   decision|instrument` plans one stage, `--k N` overrides every member's
   repeats, `--members a:b,c:d` restricts the members, `--scenarios
   all|seed|1,2,3` the scenarios.
3. `uv run python -m voi_rank.elicit --study studies/safety-evals --protocol p001 --yes [--workers 8]`
   prints the same plan and cost estimate, refuses a stage whose prompt
   would render an empty scenario field (fill it first: an elicited
   scenario is frozen), checks the members' credentials, then seeds the
   scenarios, registers the protocol and submits. Without
   `--yes` it asks on a TTY and otherwise writes nothing. A slot is (scenario,
   protocol, member, repeat, stage); slots with a valid answer are skipped, so
   a re-run resumes.
4. `uv run python -m voi_rank.mc --study studies/safety-evals --protocol p001 --seed 42 --draws 100000 [--members claude_cli:sonnet]`
   draws the pooled belief and stores the run (refused on uncommitted code
   under `voi_rank/`, `pyproject.toml` or `uv.lock` unless `--allow-dirty`),
   then prints every scenario's eta quantiles ordered by the central
   estimate (the model at the pooled medians, DESIGN section 6; the MC
   median is not a ranking). A usage error (an unregistered protocol, no
   complete fits, uncommitted code) exits with the message.
   `--members` pools one subset of the protocol's members as its own stored
   run (an ablation scores one elicitor); a subset naming every member is the
   ordinary run.
5. `scripts/regen.sh [study-dir]` (env `PROTOCOL`, default p001; `DRAWS`
   to subsample) analyses the latest stored run of the headline protocol:
   `uv run python -m voi_rank.analysis --study studies/safety-evals --protocol p001`
   re-draws the run from the DB, verifies it against the stored quantiles
   and writes `report/generated/`: `fig_*.pdf`, `tab_*.tex`, `macros.tex`
   (every cited number as `\voi...`) and `summary.json`. It reads the DB
   through an in-memory copy and never writes it. The developer-perspective
   ablation (`DEV_PROTOCOL`, default p002, which elicits only the decision
   prompt) runs as `--decision-from p002 --tag dev`: p, B, K from p002, the
   other five parameters from the headline run, written to
   `report/generated/dev/` with macros `\voidev...`; regen skips it while
   p002 has no valid decision elicitations. The report
   (`studies/safety-evals/report/`) does not exist yet.

## Protocols

```yaml
name: p001
stages:
  - name: decision                      # once per scenario group
    template_path: templates/decision.md
    params: [p, B, K]
    group_key: self                     # self | group | attributes.<key>
  - name: instrument                    # once per scenario
    template_path: templates/instrument.md
    params: [s, t, C_build, C_run, n]
template_vars:                          # substituted into both templates
  perspective: society                  # society | developer
  anchors_decision: '@file:templates/anchors_decision.md'   # '@file:' inlines a study file
  anchors_instrument: '@file:templates/anchors_instrument.md'
  context_mode: curated
members:
  - {provider: claude_cli, model: haiku, k_repeats: 3}
  - {provider: openrouter, model: openai/gpt-4o-mini, k_repeats: 3}
scenarios: all                          # optional scope: all | seed | 5,13,22
```

Every protocol has these two stages. The decision prompt renders `$agent
$decision $theta_definition $decision_context` and the template variables,
never the instrument, the title or the instrument context; the instrument
prompt renders `$title $agent $decision $theta_definition $instrument
$context` (the scenario's `instrument_context`) and the template variables. A
template naming anything else is refused; a template variable named
`decision_*` or `anchors_decision` renders only in the decision template,
`instrument_*` or `anchors_instrument` only in the instrument one (the other
names in both). `group_key: self` makes every
scenario its own decision; `group` or `attributes.<key>` elicits the decision
stage once per group of scenarios that share agent, decision, theta and
decision_context text, stored on the group's lowest id. A protocol file is
immutable once registered: both templates, every inlined file, the template
variables, the stage config, the members and the scope are hashed and a
changed file is refused (make a new protocol file). Scenarios are seeded from
`scenarios.json` at every run; a scenario without elicitations is refreshed
in place, an elicited one is frozen (change its title to make a new row; the
old one is retired, kept with its elicitations).

Validation of an answer (DESIGN section 4): strict JSON with exactly the
stage's parameters, each with `reasoning` and `p5 < p50 < p95`;
probabilities in (0, 1), USD and `n` > 0, `n >= 1` at the median, median `s`
> 1 - median `t`, prior median in [0.001, 0.999]; no unit field. Error classes
stored in `elicitations.error`: `json`, `schema`, `constraint`, `fit`,
`refusal` (a plain-text answer that declines, or an OpenRouter
`content_filter` finish), `cli`, `http`, `api`, `provider`. A failed attempt
is retried once (at once for answer failures, after the server's Retry-After
for HTTP 429/5xx, never for a rejected request or an error of the member's
environment, which halts that member). Every attempt is stored with its raw
response and cost. During a claude.ai usage-limit window the CLI's
zero-usage exits are never stored; the harness holds the limited member,
pauses once only held members remain (until the stated reset, else
`VOI_OUTAGE_SLEEP_S`), probes it, and gives up on it after
`VOI_OUTAGE_MAX_WAIT_S` of pausing. Ctrl-C cancels the pending slots, waits
for the running calls and stores them; paid work is never discarded. A DB
write that fails twice spills the slot to `<study>/elicit_unstored.jsonl`.

## What a run stores

`runs`: seed, draw count, `code_hash` (git HEAD of the code paths, `-dirty`
when uncommitted), `data_hash` (digest of the valid elicitations drawn),
`members_json`. `results`: per scenario the q05..q95 of every metric named in
the model section, and the probabilities `p_positive` = P(EVSI > C),
`p_changes` = P(EVSI > 0), `p_pays` = P(n >= n*) and `p_top5` (rank <= 5 by
eta) as their own metric rows with `q50` holding the probability.
`sensitivities`: the Spearman of each parameter's draws against eta.
`mc.replay_efficiency` recomputes a run's eta draws from the DB alone and
refuses when the valid elicitations changed since.

## OpenRouter

Nothing calls OpenRouter unless a protocol lists an `openrouter` member. Set
`OPENROUTER_API_KEY` in the environment or `.env`; the key's presence is
checked before the plan is printed and the key itself is verified with one
free request after the run is confirmed. The test suite monkeypatches the
HTTP layer: no test or default command reaches the network.

## Archived databases

`archive/business/voi.db` and `archive/pilots/*/voi.db` were written by the
retired code (six parameters, single-prompt and Gaussian protocols). The
current code opens them read-only (`db.connect_copy`, used by every dry run)
or migrates a copy in place by adding the new columns; it cannot elicit
their protocols or replay their runs (a dry run of one exits with the
registration's refusal, `mc.replay_efficiency` with a message naming the
run). Never write to a database under
`archive/`: `Study.connect` refuses a study whose path has an `archive`
component (this checkout's or any other's), so `elicit` (the paid path)
and `mc` exit before touching the file; copy the study outside `archive/`
to migrate it.
