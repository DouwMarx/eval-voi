# Design and working assumptions (2026-10-02)

Authoritative conventions for the code, the paper and the extended report. When the code and this file disagree, fix one of them the same day. Older documents (spec.md, README_methods.md, README_tracks.md, PILOT_ASSESSMENT.md, handover/) describe the pilots and are archived, not maintained.

## 1. What the paper is

One question: are physical-AI safety evaluations worth the money, per dollar, compared with the safety evaluations LLM developers already run before a release? One method: expected value of sample information (EVSI) for one release decision, with parameters elicited from an ensemble of language models, propagated by Monte Carlo. Track 1 of the pilots is the paper. Track 2 (the sim-to-real ladders) is archived; its transferable finding (fidelity level against elicited discriminability and cost) is re-tested inside this study's physical-AI evaluations, which span fidelity levels, and reported as one result paragraph.

The elicitation is a means, not the contribution. The paper states what was used and how well it behaved; the details go to the extended report.

## 2. Terminology (use these words, nothing else)

| use | do not use |
|---|---|
| physical-AI safety evaluation; short: physical-AI evaluation; figure label "physical AI". An evaluation whose hazard is physical harm from an embodied system (robot, vehicle, drone) or from a model controlling one. | robot eval, hardware eval, robotics eval |
| LLM safety evaluation; short: LLM evaluation; label "LLM". An evaluation of a language or agent model, reported in at least one LLM system card, whose hazard is not physical. | AI eval, AI safety eval, software eval, frontier-model evaluation |
| safety evaluation (the genus); "evaluation" once the context is clear | benchmark (only when the source calls itself one) |
| fidelity level 0-9 (text question answering ... deployment data) | rung, ladder |
| the hazard: the state theta=1, in which the hazardous property is present and mitigating is correct. The templates say "the hazard". | the defect, the property, the failure mode (as the state's name) |
| mitigate (a=1: delay the release and reduce the hazard); deploy as planned (a=0) | respond, act, gate, release |
| positive result (x=1, suggests the hazard is present); negative result (x=0) | flag, alarm, fail (as the result's name) |
| the result can change the decision (the condition pi0 < pi* < pi1); decision-changing | gate, gated, in gate, closed gate |
| the prior is already decisive (mitigates regardless / deploys regardless): the prior sits so far past the threshold, for this evaluation's sensitivity and specificity, that neither result moves the belief across it | always respond, never respond, cannot change the decision (as the case's name) |
| EVSI: the expected value of one run of the evaluation, at the elicited prior and threshold | plug-in value, gated value |
| EVSI*: the maximum EVSI over the threshold at fixed stakes, the value to a still undecided decision maker; EVSI* = (B+K) p(1-p)\|s+t-1\|. Reported because today's prior is a snapshot. Code and DB keep the key EVSI_ind; macros carry EtaInd... and the alias EtaStar... | EVSI_max, maximum EVSI (as the name), indifference value, fence value, threshold-free value |
| efficiency eta = EVSI/C; eta* = EVSI*/C (code: eta_ind), the primary ranking metric; run-only efficiency eta_run = EVSI/C_run | eta_max, eff, eff* |
| single estimate: the model with every parameter at its median across the members (the median over valid elicitations of each elicited median) | central estimate, plug-in point, point estimate |
| combined belief: the equal-weight mixture of the fitted distributions of every valid elicitation (the linear opinion pool); Monte Carlo over the combined belief | pooled, pooled belief, bootstrap, replicate |
| probability of superiority P_S: the probability that a random physical-AI evaluation scores higher than a random LLM evaluation, ties counting one half (the Mann-Whitney U over the number of pairs). Reported as median and 90% interval over the draws, plus the exact Mann-Whitney p_MW at the single estimate | A, AUC (as the group statistic's name), common-language effect size (cite it, do not name it so) |
| break-even run count n* = C_build/(EVSI - C_run): the number of runs after which the build is repaid; infinite where EVSI <= C_run | reuse count, break-even reuse count, pays, pay-back probability |
| B and K valued for society: harm avoided and welfare forgone, summed over everyone the release affects | perspective, developer perspective, societal perspective |
| decision prompt, instrument prompt (the two elicitation prompts) | stage (in prose; the code keeps `stage`) |
| the ensemble, the members (elicitors) | judges, experts (for LLMs) |
| Youden's index J = s + t - 1 (define once) | discriminability |
| the main result, the paper's first figure | headline (the code keeps fig_headline and tab_headline) |

Define every acronym at first use: EVSI, EVPI, VOI, MC, LLM, VLM, VLA, AEB, CBRN, IIHS. Prefer "[x]^+ = max(x, 0)" spelled out once. No bold in prose. Short declarative sentences. No metaphors. No em-dashes.

## 3. The decision model

One developer, one release decision: mitigate (delay and reduce the hazard) or deploy as planned. Hidden binary state theta (1 = the hazard is present; mitigating is then correct). One run of the evaluation returns a result x in {0,1} with sensitivity s = P(x=1 | theta=1) and specificity t = P(x=0 | theta=0). Prior p = P(theta=1). Mitigating gains B when theta=1 and costs K when theta=0 (regret form, u(theta,0)=0). Stakes Lambda = B + K, threshold pi* = K/Lambda, V(pi) = Lambda [pi - pi*]^+.

Closed forms (voi_rank/model.py):
- P1 = ps + (1-p)(1-t); pi1 = ps/P1; pi0 = p(1-s)/(1-P1)
- EVSI = P1 V(pi1) + (1-P1) V(pi0) - V(p); EVPI = min(pB, (1-p)K)
- EVSI* = Lambda p(1-p)|s+t-1| (code: EVSI_ind); an inverted evaluation (s+t < 1, which the elicitation rejects but a mixture draw can produce) is read the other way round, as EVSI is.
- EVSI = 0 unless pi0 < pi* < pi1 (the result can change the decision); otherwise the prior is already decisive (pi0 >= pi*: mitigates regardless; pi1 <= pi*: deploys regardless).

Elicited parameters (seven): decision prompt p, B, K; instrument prompt s, t, C_build, C_run.
- B and K are valued for society, in USD, for this one release decision. There is no perspective variable.
- C_build: cost to build the evaluation from scratch (design, data or scenes, hardware, engineering). C_run: cost of one run against one system. C = C_build + C_run.

Derived per draw (voi_rank/model.py METRIC_NAMES): EVSI, EVPI, EVSI*, C, eta = EVSI/C, eta* = EVSI*/C, eta_run = EVSI/C_run, n* = C_build/(EVSI - C_run) when EVSI > C_run else infinity.

Not in the model, stated as limitations or in docs/FUTURE_WORK.md: batteries of evaluations, graded responses, repeated testing, correlation between parameters, growth of the deployed base over time, the number of decisions a built evaluation informs over its life (n* reports the break-even instead), decision makers other than the developer.

## 4. Elicitation

- Two prompts per scenario, rendered from studies/safety-evals/templates/decision.md and instrument.md. The decision prompt renders agent, decision, theta definition and the scenario's `decision_context`; it never mentions the instrument. It asks p, B, K, with B and K valued for society. The instrument prompt renders title, agent, decision, theta definition, instrument and the scenario's `instrument_context` (the agent and decision text fix the release cadence the costs depend on and carry no number); it never mentions B, K, p or the `decision_context`, and tells the member not to let the stakes move its estimate of the evaluation's quality or cost. It asks s, t, C_build, C_run. The two are independent calls (the pilots showed a single prompt lets instrument text move the prior).
- The templates state the model, define each parameter in one line, give the facts block and one sentence on how to use it ("Use these facts. Where they give a quantity, take it as given and reason from it; where they are silent, reason from base rates and typical magnitudes."), then the instructions and the JSON shape. They carry no caps on any parameter, no perspective paragraph, no order-of-magnitude instruction and no list of forbidden quantities.
- Every scenario is its own decision (`group_key: self`). Protocol-level decision contexts are gone.
- Reasoning paragraph before each parameter's three percentiles, asked extremes first: p5 and p95 as exclusion questions ("a value you would be surprised to see the true value fall below / above"), then p50 (research/elicitation_lit.md implication 6). Strict JSON: {"parameters": {"p": {"reasoning": "...", "p5": .., "p95": .., "p50": ..}, ...}}. The prompts ask for plain decimal numbers (implication 5); the parser also reads scientific notation. No unit field: the units are fixed by the template.
- Anchors: both templates keep an optional block (`$anchors_decision`, `$anchors_instrument`: protocol template variables). Both current protocols set them to '' and render none (research/elicitation_lit.md implication 2); the anchor files of the iteration are in archive/iteration-2026-09-30/templates/ and no current protocol inlines them.
- Template variables: the protocol's `template_vars` render in both prompts, except that a name `decision_*` or `anchors_decision` renders only in the decision prompt and `instrument_*` or `anchors_instrument` only in the instrument prompt; the renderer refuses the other template, so no variable carries a decision-level number into the instrument prompt. `context_mode` is `curated` (the facts) or `none` (no facts and no facts heading in either prompt).
- Validation: exact parameter set for the prompt, p5 < p50 < p95, probabilities in (0,1), USD > 0, median s > 1 - median t, prior median in [0.001, 0.999]. One retry. Error classes: json, schema, constraint, fit, refusal (no JSON and the text declines, or finish_reason content_filter), truncated (finish_reason length: the answer hit max_tokens), cli, http, api, provider (an exception escaping a provider call).
- Fitting: Beta for p, s, t; lognormal for B, K, C_build, C_run; least squares on the three quantiles; stored at elicitation time.
- Members: `provider` in {claude_cli, openrouter}, `model`, `k_repeats`, and for OpenRouter the request options (README). The final protocol uses OpenRouter with a dedicated key: six members from six developers, three Chinese and three US, no Anthropic member (two LLM evaluations are Anthropic's own, and the facts were curated by an Anthropic model), k=1 each, `reasoning_effort` medium for every member, one pinned endpoint per member. The iteration runs used claude_cli haiku and sonnet under protocols p001 to p003 (archived). `elicit --dry-run` prints the plan and a cost estimate from stored attempt costs or, for a member with none, from OpenRouter's published prices and a token estimate.
- Prompt caching: the shared prefix (model, scenario, context) comes first, the question last; OpenRouter requests carry one cache_control breakpoint on the user message (Anthropic needs it; others cache automatically), so only an identical prompt (a repeat or a retry) reuses the cache; at k=1 caching saves little, and the cost estimate ignores it.
- Provenance: template hash per prompt, prompt hash per call, raw response stored, cost stored, code hash and data hash per Monte Carlo run.

## 5. Context: what the elicitor reads and where it comes from

Scenario fields: title, agent, decision, theta_definition, instrument, group ("physical AI" | "LLM"), attributes {risk_domain, level (physical AI only), eval_family}, sources (list of {key, kind: arxiv | url | pdf | system_card, ref, role: decision | instrument | both, title}), decision_facts, instrument_facts (curated sentences, each ending in a [key] citation to sources), decision_context, instrument_context (the facts without their markers).

The facts were written and checked by language-model agents from cached primary sources (research/scenarios_draft/PROVENANCE.md; the texts under research/sources/). The planned voi_rank/context.py (modes `abstracts` and `full`) is not written; scripts/build_scenarios.py derives the context fields from the facts, so `curated` and `none` are the implemented modes. The mode is a protocol setting; final_noctx is the `none` ablation.

### Selection

Which of the drafts in research/scenarios_draft/ are analysed is set in studies/safety-evals/include.yaml (one entry per draft, with a reason) and argued in research/scenarios_draft/SELECTION.md, which holds the scores, the ranking and the counts. The rule (2026-10-02), applied without looking at any result:
- LLM: score = system-card presence (publishers and documents naming it) + 2 x hazard checkability (programmatic or expert-baselined > validated LLM judge > partially validated > unvalidated judge) - 1 for a capability benchmark rather than a hazard measure - 1 for a documented construct problem only where it means the score does not measure the hazard. Saturation, private status, no standalone paper, and being a tool or generator are not penalised. Take the top of the ranking to about 20, passing over a third near-identical evaluation in favour of another risk domain. Floor: at least 3 evaluations per LLM risk domain, filled by the highest-scoring remaining evaluation of that domain whose hazard result is checkable.
- Physical AI: the one requirement is that the score measures a physical harm of an embodied system or of a model controlling one. Score = validity class + hazard directness + 1 for the best at its fidelity level; take the top of the ranking to about 8 and the best candidate at each level left empty. Each chosen evaluation states the system type it tests.

## 6. Monte Carlo and summaries

- Combined belief per parameter per scenario: equal-weight mixture over the fitted distributions of every valid elicitation (all members, all repeats). This is the linear opinion pool. Parameters are drawn independently. 100,000 aligned draws per scenario, seed stored (voi_rank/mc.py).
- Single estimate: the model with every parameter at its median across the members. Point tables and the two-panel value-against-cost figure use it. The Monte Carlo median is not a ranking.
- Rankings (voi_rank/analysis/summary.py): by eta* (primary) and by eta, rank 1 = best, ties averaged, on every draw and at the single estimate. From the draws: rank quantiles and the rank interquartile range (q25..q75) per evaluation, with its median over all evaluations and per group; P(rank <= k) for k = 3, 5; per draw the rank of the best-ranked physical-AI evaluation, reported as P(best physical-AI rank <= N) for N = 1..S.
- Group comparison: P_S for eta*, eta and eta_run, each as the value at the single estimate, its median and 90% interval over the draws, and the exact Mann-Whitney p_MW at the single estimate (a permutation count that holds under ties, since many etas are exactly 0). Also P_S by eta among the evaluations whose result can change the decision at the single estimate. The ROC curve of "physical AI" given eta and given eta* (threshold swept over the score, ties entering together, so its area is P_S), at the single estimate and as a pointwise 5-95% band over draws of the TPR at a fixed FPR grid. By eta: the percentile curve P(a random physical-AI evaluation beats the q-th percentile of the LLM evaluations) for q in 0..100, at the single estimate and as a 90% band over draws; per physical-AI evaluation, its percentile among the LLM evaluations and P(it beats the LLM median).
- Per evaluation: P(EVSI > 0), P(EVSI > C), the quantiles of n* over the finite draws and the share of finite draws. Per group: the share of evaluations whose prior is already decisive at the single estimate.
- Per risk domain (cyber, CBRN, loss of control, harmful manipulation, societal harm, physical AI): the evaluations, the median single-estimate eta*, eta and stakes, the median rank by eta* at the single estimate, the median over draws of the domain's mean rank, the share with the prior already decisive.
- Sensitivity: Spearman of each parameter's draws against eta (stored by the run) and against eta* (recomputed from the draws) per scenario; mean |rho| across scenarios.
- Fidelity: Spearman of level with the single-estimate eta, eta*, Youden's index and C over the physical-AI evaluations, with p-values.
- Members: per parameter the mean over member pairs of the Spearman correlation of their per-scenario medians; per member attempts, valid answers, invalid answers by error class and cost.
- Retired: the reuse count n and everything built on it (net_n, eta_n, P(pays)), the developer-perspective ablation (the `--decision-from` option of the analysis stays in the code and is unused by the documents), the bootstrap over elicitations, the MC median as a ranking, member-subset weighting schemes, the Gaussian-state family.

## 7. Outputs

Generated by `scripts/regen.sh` from the database alone (deterministic), into studies/safety-evals/report/generated/: figures, tables, and one macros.tex with every number either document cites. No hand-written numbers file. regen.sh analyses the latest run of PROTOCOL (default final) and, into generated/noctx/ with macros \voinoctx..., the latest run of NOCTX_PROTOCOL (default final_noctx), skipped while that protocol has no stored run. The analysis re-draws the run, verifies every stored eta quantile and P(EVSI > C), and reads the DB through an in-memory copy.

Figures (voi_rank/analysis/figures.py):
- fig_headline: two panels at the single estimate, EVSI* against C for every evaluation and EVSI against C for the evaluations with EVSI > 0, with iso-efficiency lines and id labels (extended report); fig_headline_small: the same without id labels, at the paper's width.
- fig_rows: per evaluation the rank by eta* (q05-q95 thin bar, q25-q75 thick bar) and the break-even n*, rows sorted by median rank, coloured by risk domain, physical-AI rows outlined and bold.
- fig_rank_star, fig_rank_eta: rank intervals by eta* and by eta; fig_best_physical_rank: P(best physical-AI rank <= N); fig_breakeven: n* distributions.
- fig_curve: the percentile curve; fig_percentile_violins: each physical-AI evaluation's percentile among the LLM evaluations; fig_roc: ROC for eta and eta* with bands.
- fig_params: elicited medians per parameter per evaluation, coloured by member, the combined median marked.
- fig_sensitivity (against eta*), fig_sensitivity_eta (against eta): Spearman heatmaps.
- fig_level: fidelity level against eta and eta*, with Youden's index and cost as secondary panels.
- fig_members: cross-member agreement.
- The pipeline diagram is TikZ in report/pipeline.tex.

Tables (voi_rank/analysis/tables.py): tab_scenarios (the evaluations), tab_headline (per evaluation at the single estimate, ordered by eta*), tab_domains (per risk domain), tab_provenance (primary source title per evaluation), tab_health (per member).

Macros (voi_rank/analysis/macros.py), all \voi... (\voinoctx... for the ablation): run facts (RunId, Seed, Draws, NMembers, NScenarios, NPhysical, NLLM); per metric word Eta, EtaInd, EtaRun: <Metric>PS, <Metric>PSQLo/Med/Hi, <Metric>MWp; per ranking metric: <Metric>RankIQRMedian[Physical|LLM], <Metric>PBestPhysicalTopOne/Three/Five/Ten, <Metric>BestPhysicalRankCentral/Short/Value, <Metric>TopShort/Value; group medians Med<Param><Group>, MedStakes<Group>, StakesRatio, EtaIndRatio; ZeroShare<Group>, NZero<Group>, ZeroIds<Group>; Nstar..., PNstarFiniteMedian<Group>; Dom<Domain>N/MedRank/MeanRankMed/MedEtaInd/MedEta/MedStakes/ZeroShare, DomainOrder; Rho<Param>, RhoInd<Param>, Rho[Ind]Top/Second/LowParam/Value; LevelRho...; per evaluation Eta<Key>, EtaInd<Key>, Rank<Key>, PChanges<Key>, Nstar<Key>, Pct<Key>...; health Attempts, Valid, ValidShare, USD, Invalid<Class>. Every macro containing EtaInd is also defined with EtaStar in its place.

Documents: studies/safety-evals/report/main.tex, the paper ("Are physical-AI safety evaluations worth the money? A value-of-information comparison with LLM safety evaluations"; anonymous CoRL template; 4-page body; sections introduction, method, results, limitations and conclusion; no generative-AI disclosure paragraph, the venue takes it in the submission form), and studies/safety-evals/report/extended/main.tex, the extended report (no page limit; the shared sections plus further figures, ablations, elicitation details, the evaluations, the ensemble, the reviewer objections, the pilot findings, future work; no code listings beyond the two templates). The shared sections live in report/sections/ and read report/generated/; the noctx macros are read when present. Every number is a \voi macro; hand-typed sentences whose wording depends on the data are marked % CHECK-DATA and re-read after every regen.

## 8. Repository

```
voi_rank/            model, fit, mc, db, study, elicit, validate, sensitivity, dotenv, pricing,
                     providers/{claude_cli, openrouter}, analysis/{summary, figures, tables, macros}
studies/safety-evals/ scenarios.json, include.yaml, protocols/{final, final_noctx}.yaml,
                     templates/{decision, instrument}.md, voi.db, report/, report/extended/
research/            literature catalogue, refs.bib, system-card mining, scenarios_draft/ (the drafts,
                     SELECTION.md, PROVENANCE.md), sources/ (cached source texts), smoke-test records
archive/             business/ (data the external chapter reads), pilots/ (frozen at tag pilot-2026-09-30),
                     iteration-2026-09-30/ (protocols p001-p003, their templates and anchors)
scripts/             build_scenarios.py, regen.sh, build_paper.sh, check_pages.py
docs/                DESIGN.md, FUTURE_WORK.md, QUESTIONS.md
```

Archive policy: archive/ is a read-only record. A protocol or template that leaves the study moves there with its date; nothing under archive/ is edited, re-run or analysed, and `Study.connect` refuses a database under it. The iteration's elicitations (p001, p002) and its Monte Carlo runs stay in studies/safety-evals/voi.db; they are not analysed, and the archived protocol files describe them. The final run's rows and runs live in the same database under the protocols final and final_noctx.

Deleted (recoverable from git): the reuse count n and its metrics, the perspective template variable and the developer-perspective protocol final_dev.yaml, the Gaussian-state family, the proposer, the manual protocol, the bootstrap, the ladder and level analyses, member-subset weighting, the legacy efficacy macros, spec.md, the pilot READMEs, handover/, the disclosure section of the paper.

## 9. Rules for agents

- No OpenRouter call except the designated smoke tests and the final-run steps, with the dedicated key in OPENROUTER_API_KEY; no paid claude_cli elicitation except the designated run steps. Never read a secret's value (key names only, `cut -d= -f1 .env`).
- Never write to a database under archive/ (`Study.connect` refuses one; `connect_copy` reads it, and `--dry-run` plans on a copy). Never edit a file under archive/.
- Work in the assigned worktree or directory; commit there with the Co-Authored-By trailer the session specifies; never push, never touch main.
- Tests: `uv run pytest -q` and `uv run ruff check .` green before every commit. No test is skipped or weakened to pass.
- Documents: no number typed by hand; a new number is a new macro. Re-read every % CHECK-DATA line after a regen.
