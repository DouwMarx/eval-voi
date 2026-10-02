# Design and working assumptions (2026-09-30)

Authoritative conventions for the code, the paper and the extended report. When the code and this file disagree, fix one of them the same day. Older documents (spec.md, README_methods.md, README_tracks.md, PILOT_ASSESSMENT.md, handover/) describe the pilots and are archived, not maintained.

## 1. What the paper is

One question: how much is a safety evaluation of a physical-AI system worth, per dollar, compared with the safety evaluations LLM developers already run before a release? One method: expected value of sample information (EVSI) for one deployment decision, with parameters elicited from an ensemble of language models, propagated by Monte Carlo. Track 1 of the pilots is the paper. Track 2 (the sim-to-real ladders) is archived; its transferable finding (fidelity level against elicited discriminability and cost) is re-tested inside this study's physical-AI evaluations, which span fidelity levels, and reported as one discussion point.

The elicitation is a means, not the contribution. The paper states what was used and how well it behaved; the details go to the appendix and the extended report.

## 2. Terminology (use these words, nothing else)

| use | do not use |
|---|---|
| physical-AI safety evaluation; short: physical-AI evaluation; figure label "physical AI". An evaluation whose hazard is physical harm from an embodied system (robot, vehicle, drone) or from a model controlling one. | robot eval, hardware eval, robotics eval |
| LLM safety evaluation; short: LLM evaluation; label "LLM". An evaluation of a language or agent model, reported in at least one LLM system card, whose hazard is not physical. (Changed 2026-10-01 from "frontier-model", which is ambiguous: robotics companies can be frontier too.) | AI eval, AI safety eval, software eval, frontier-model evaluation |
| safety evaluation (the genus); "evaluation" once the context is clear | benchmark (only when the source calls itself one) |
| fidelity level 0-9 (text question answering ... deployment data) | rung, ladder |
| the result can change the decision (the condition pi0 < pi* < pi1); decision-changing | gate, gated, in gate, closed gate |
| the prior is already decisive (responds regardless / deploys regardless): the prior sits so far past the threshold, for this evaluation's sensitivity and specificity, that neither result moves the belief across it; replaces "cannot change the decision" as the name of the case, the phrase "the result can change the decision" stays for the condition | always respond, never respond, cannot change the decision (as the case's name) |
| EVSI: the developer's expected value of one run of the evaluation, at the elicited prior and threshold | plug-in value, gated value |
| maximum EVSI EVSI_max, the value to a developer on the fence (prior equal to the threshold); replaces "indifference value" (2026-10-01). EVSI's maximum over the threshold at fixed stakes; EVSI_max = (B+K) p(1-p)|s+t-1|. Reported because today's prior is a snapshot: EVSI_max is the value to any developer still undecided. Code and DB keep the name EVSI_ind / eta_ind; macros carry both EtaInd... and the display alias EtaMax... | indifference value, EVSI°, fence value, threshold-free value, EVSI* |
| efficiency eta = EVSI/C; eta_max = EVSI_max/C; run-only efficiency eta_run = EVSI/C_run | eff, eff*, eta° |
| central estimate: the model evaluated at the pooled medians (the median over valid elicitations of each elicited median) | plug-in point, plug-in |
| Monte Carlo over the pooled belief: draws from the equal-weight mixture of the fitted elicitation distributions | bootstrap, replicate (both retired) |
| reuse count n; break-even reuse count n* | |
| decision prompt, instrument prompt (the two elicitation prompts) | stage (in prose; the code keeps `stage`) |
| the evaluation ensemble, the members (elicitors) | judges, experts (for LLMs) |
| Youden's index J = s + t - 1 (define once) | discriminability |

Define every acronym at first use: EVSI, EVPI, VOI, MC, LLM, VLM, VLA, AEB, CBRN, IIHS. Prefer "[x]^+ = max(x, 0)" spelled out once. No bold in prose. Short declarative sentences. No metaphors.

## 3. The decision model

One developer, one release decision: respond (delay and mitigate) or deploy as planned. Hidden binary state theta (1 = the hazardous property is present; responding is then correct). One run of the evaluation returns a flag x in {0,1} with sensitivity s = P(x=1 | theta=1) and specificity t = P(x=0 | theta=0). Prior p = P(theta=1). Responding gains B when theta=1 and costs K when theta=0 (regret form, u(theta,0)=0). Stakes Lambda = B + K, threshold pi* = K/Lambda, V(pi) = Lambda [pi - pi*]^+.

Closed forms (voi_rank/model.py):
- P1 = ps + (1-p)(1-t); pi1 = ps/P1; pi0 = p(1-s)/(1-P1)
- EVSI = P1 V(pi1) + (1-P1) V(pi0) - V(p); EVPI = min(pB, (1-p)K)
- EVSI_max = Lambda p(1-p)|s+t-1| (code: EVSI_ind); an inverted evaluation (s+t < 1, which the elicitation rejects but a mixture draw can produce) is read the other way round, as EVSI is.
- EVSI = 0 unless pi0 < pi* < pi1 (the result can change the decision); otherwise the prior is already decisive (pi0 >= pi*: responds regardless; pi1 <= pi*: deploys regardless).

Elicited parameters (eight): decision level p, B, K; instrument level s, t, C_build, C_run, n.
- C_build: cost to build the evaluation from scratch (design, data or scenes, hardware, engineering). C_run: cost of one run against one system. C = C_build + C_run.
- n: number of distinct deployment decisions the built evaluation will inform over its useful life (model releases, product versions, calibrations); n >= 1, lognormal.
- Perspective of B and K: `society` (all parties' welfare: harm avoided, benefits forgone) or `developer` (the developer's own financial exposure: liability, recall, reputation, lost revenue, delay). The headline uses `society`; `developer` is an ablation. The perspective is a template variable set by the protocol, never hard-coded in a template.

Derived per draw (voi_rank/mc.py): EVSI, EVPI, EVSI_max, C, eta = EVSI/C, eta_max = EVSI_max/C, eta_run = EVSI/C_run, net_n = n EVSI - C_build - n C_run, eta_n = n EVSI/(C_build + n C_run), n* = C_build/(EVSI - C_run) when EVSI > C_run else infinity, pays = 1[n >= n*].

Not in the model, stated as limitations: batteries of evaluations, graded responses, repeated testing, correlation between parameters, growth of the deployed base over time (n partly absorbs it), whose utility the developer maximises beyond the two perspectives.

## 4. Elicitation

- Two prompts per scenario. The decision prompt renders agent, decision, theta definition and the scenario's `decision_context`; it never mentions the instrument. It asks p, B, K under the protocol's perspective. The instrument prompt renders title, agent, decision, theta definition, instrument and the scenario's `instrument_context` (the agent and decision text fix the release cadence that n and the costs depend on and carry no number); it never mentions B, K, p or the `decision_context`. It asks s, t, C_build, C_run, n. The two are independent calls (the pilots showed a single prompt lets instrument text move the prior).
- Every scenario is its own decision (stage group = the scenario). Protocol-level decision contexts are gone.
- Reasoning paragraph before each parameter's three percentiles, asked extremes first: p5 and p95 as exclusion questions ("a value you would be surprised to see the true value fall below / above"), then p50 (research/elicitation_lit.md implication 6). Strict JSON: {"parameters": {"p": {"reasoning": "...", "p5": .., "p95": .., "p50": ..}, ...}}. The prompts ask for plain decimal numbers (implication 5); the parser also reads scientific notation. No unit field: the units are fixed by the template.
- Anchors: an optional template block per prompt (`$anchors_decision`, `$anchors_instrument`: protocol template variables), kept for an ablation. The headline protocol p001 sets both to '' and renders no anchors (research/elicitation_lit.md implication 2); the anchor file carries its own heading, so an empty block leaves none. The instrument anchors' C_build, C_run and n triples are stylised, not sourced.
- Template variables: the protocol's `template_vars` render in both prompts, except that a name `decision_*` or `anchors_decision` renders only in the decision prompt and `instrument_*` or `anchors_instrument` only in the instrument prompt; the renderer refuses the other template, so no variable carries a decision-level number into the instrument prompt.
- Validation: exact parameter set for the stage, p5 < p50 < p95, probabilities in (0,1), USD and n > 0, n >= 1 at p50, median s > 1 - median t, prior median in [0.001, 0.999]. One retry. Error classes: json, schema, constraint, fit, refusal (no JSON and the text declines, or finish_reason content_filter), truncated (finish_reason length: the answer hit max_tokens), cli, http, api, provider (an exception escaping a provider call).
- Fitting: Beta for p, s, t; lognormal for B, K, C_build, C_run, n; least squares on the three quantiles; stored at elicitation time.
- Members: `provider` in {claude_cli, openrouter}, `model`, `k_repeats`. Iteration runs use claude_cli haiku and sonnet. The final run uses OpenRouter with a dedicated key; the members and k are in the protocol file; `elicit --dry-run` prints the plan and a cost estimate from stored attempt costs or, for a member with none, from OpenRouter's published prices and a token estimate.
- Prompt caching: the shared prefix (model, scenario, context) comes first, the stage question last; OpenRouter requests carry one cache_control breakpoint on the user message (Anthropic needs it; others cache automatically), so only an identical prompt (a repeat or a retry) reuses the cache; at k=1 caching saves little, and the cost estimate ignores it.
- Provenance: template hash per stage, prompt hash per call, raw response stored, cost stored, code hash and data hash per Monte Carlo run.

## 5. Context: what the elicitor reads and where it comes from

Scenario fields: title, agent, decision, theta_definition, instrument, group ("physical AI" | "LLM"), attributes {risk_domain, level (physical AI only), eval_family}, sources (list of {key, kind: arxiv | url | pdf | system_card, ref, role: decision | instrument | both}), decision_facts, instrument_facts (curated sentences, each ending in a [key] citation to sources).

voi_rank/context.py builds the two context blocks from three reproducible inputs: (1) source texts fetched programmatically by key and cached under research/sources/<key>.json (fetch date, URL, text; committed), (2) system-card sentences that name the evaluation, from the corpus already in research/, (3) the curated facts. Modes: `curated` (facts only), `abstracts` (facts plus source abstracts), `full` (facts plus full source text, truncated to a token budget). The prompt states which mode produced its context. The mode is a protocol setting; an ablation compares them.

### Selection

Which of the drafts in research/scenarios_draft/ are analysed is set in studies/safety-evals/include.yaml (one entry per draft, with a reason) and argued in research/scenarios_draft/SELECTION.md. The rule (2026-10-02), applied without looking at any result:
- LLM: score = system-card presence (publishers and documents naming it) + 2 x hazard checkability (programmatic or expert-baselined > validated LLM judge > partially validated > unvalidated judge) - 1 for a capability benchmark rather than a hazard measure - 1 for a documented construct problem only where it means the score does not measure the hazard. Saturation, private status, no standalone paper, and being a tool or generator are not penalised. Take the top of the ranking to about 20, passing over a third near-identical evaluation in favour of another risk domain.
- Physical AI: the one requirement is that the score measures a physical harm of an embodied system or of a model controlling one. Score = validity class + hazard directness + 1 for the best at its fidelity level; take the top of the ranking to about 8 and the best candidate at each level left empty. Each chosen evaluation states the system type it tests.

## 6. Monte Carlo and summaries

- Pooled belief per parameter per scenario: equal-weight mixture over the fitted distributions of every valid elicitation (all members, all repeats). This is the linear opinion pool. Parameters are drawn independently. 100,000 aligned draws per scenario, seed stored.
- Central estimate: model at pooled medians. Point tables and the headline figure use it.
- From the draws: per-scenario quantiles of every metric; P(EVSI > 0); P(EVSI > C); rank quantiles by eta (rank 1 = best, ties averaged) and the rank interquartile range (q25..q75) per evaluation, with its median over all evaluations and per group; P(rank <= k) (extended report only); per draw the rank of the best-ranked physical-AI evaluation among all evaluations, reported as P(best physical-AI rank <= N) for N = 1..S; the ROC curve of "physical AI" given eta and given eta_max (threshold swept over the score, ties entering together, so its area is A), at the central estimate and as a pointwise 5-95% band over draws of the TPR at a fixed FPR grid; pairwise P(eta_i > eta_j); group comparison A = P(eta of a random physical-AI evaluation > eta of a random LLM evaluation); the percentile curve P(eta of a random physical-AI evaluation > q-th percentile of the LLM evaluations' eta) for q in 0..100, per draw, with a 90% band, as the central-estimate value and as its distribution over draws; per physical-AI evaluation, the distribution of its percentile among the LLM evaluations; break-even n* distribution and P(pays). Exact Mann-Whitney on the central estimates is the frequentist companion.
- Sensitivity: Spearman of each parameter's draws against eta per scenario; mean |rho| across scenarios.
- Retired: the bootstrap over elicitations, the MC median as a ranking, the linear-pool developer, member-subset weighting schemes, the Gaussian-state family.

## 7. Outputs

Generated by `scripts/regen.sh` from the database alone (deterministic), into studies/safety-evals/report/generated/: figures, tables, and one macros.tex with every number either document cites. No hand-written numbers file.

Figures: F1 pipeline diagram (TikZ, in the tex) plus EVSI against C with iso-efficiency lines, two groups; F2 the same for EVSI_max; F3 elicited parameters per evaluation (one panel per parameter, pooled mixture shown as a strip of elicited medians with the pooled median marked); F4 percentile of each physical-AI evaluation among the LLM evaluations (violins); F5 rank intervals (q05-q95 thin bar, q25-q75 thick bar); F5b P(best physical-AI rank <= N); F5c ROC curves for eta and eta_max; F6 break-even reuse count distributions with the elicited n; F7 sensitivity heatmap; F8 fidelity level against eta and eta_max (central estimates, Spearman with p-value), with Youden's index and cost as secondary panels; F9 cross-member agreement; F10 ablations (perspective, anchors, context mode, number of evaluations).

Documents: studies/safety-evals/report/main.tex (4-page body plus appendices, anonymous CoRL 2026 template) and studies/safety-evals/report/extended/main.tex (no page limit; every alternative figure, the ablations, the pilot findings, the reviewer objections section; no code listings).

## 8. Repository after the cleanup

```
voi_rank/            model, fit, mc, db, study, elicit, context, validate, providers/{claude_cli, openrouter},
                     analysis/{summary, figures, tables, macros}
studies/safety-evals/ scenarios.json, protocols/, templates/, voi.db, report/, report/extended/
research/            literature catalogue, refs.bib, system-card mining, sources/ (fetched texts), candidate lists, notes
archive/             business/ (data the external chapter reads), pilots/ (ai-safety-evals, sim2real: frozen at tag pilot-2026-09-30)
scripts/             regen.sh, build_paper.sh, check_pages.py
docs/                DESIGN.md, QUESTIONS.md
```

Status (2026-10-01): voi_rank/context.py is not written; the context fields equal the facts fields without their [key] markers (scripts/build_scenarios.py), so `curated` and `none` (no facts; protocol p003) are the implemented modes. The fetched source texts are cached in research/sources/. Analysis, regen.sh, the catalogue-price cost estimate and the cache_control breakpoint exist. Everything else in this section exists.

Deleted (recoverable from git): the Gaussian-state family, the proposer, the manual protocol, the bootstrap, the ladder and level analyses, member-subset weighting, the legacy efficacy macros, spec.md, the pilot READMEs, handover/.

## 9. Rules for agents

- No OpenRouter call except the designated smoke test with PERSONAL_OPENROUTER_API_KEY; no paid claude_cli elicitation except the designated run steps.
- Never write to a database under archive/ (`Study.connect` refuses one; `connect_copy` reads it, and `--dry-run` plans a two-stage protocol file on a copy: the archived protocols exit with the registration's message). Never read a secret's value (key names only).
- Work in the assigned worktree or directory; commit there with the Co-Authored-By trailer the session specifies; never push, never touch master.
- Tests: `uv run pytest -q` and `uv run ruff check .` green before every commit. No test is skipped or weakened to pass.
