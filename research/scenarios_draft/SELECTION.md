# Selection of the analysed evaluations (2026-10-02)

The decision is in `studies/safety-evals/include.yaml`; `scripts/build_scenarios.py` builds `scenarios.json` from the included keys. This file gives the rule, the scores and the ranking. The selection was made and committed before any elicitation result, Monte Carlo run or generated output was read. Only the 39 drafted scenarios were eligible; all 39 were already elicited under p001.

## Criteria (the user's, verbatim; they replace the criteria of QUALITY_REVIEW.md)

- LLM safety evaluations: rank mainly by system-card presence (number of documents and publishers naming it in the corpus, as in the candidates file) and by how checkable the hazard score is (programmatic or expert-baselined > validated LLM judge > unvalidated judge). Keep the penalty for a capability benchmark rather than a hazard measure. Do NOT penalise saturation (the elicitor sees it in the context and should lower sensitivity), being private or not public, lacking a standalone paper, or being a tool/generator rather than one fixed build-and-run evaluation; drop those criteria and penalties. Other penalties are too strict; only keep a documented construct problem if it means the score does not measure the hazard. No hard duplicate rule, but when choosing, prefer coverage across the five risk domains over a third or fourth near-identical evaluation.
- Physical-AI safety evaluations: the one requirement is that the score measures a physical harm of an embodied system or of a model controlling one. Do not require a public source, a cost or validity fact, a single build-and-run instrument, or uniqueness of construct. Prefer spread across fidelity levels, and say which system type each tests.
- Target: roughly 20 LLM and 8 physical-AI evaluations; more or fewer if the ranking under these criteria clearly supports it. Choose ONLY among the 39 drafted scenarios (all already elicited). If a candidate without a draft would clearly rank inside the selection, list it as a possible addition in the review (it would need context writing, fact-checking and elicitation), do not add it.

## How the criteria were made into scores

LLM score = presence + 2 x hazard + penalties.

- presence: as in `research/candidates_frontier.json`: min(publishers, 8) + min(documents, 24)/12, range 0 to 10.
- hazard (checkability class, from the same file): 2 programmatic or expert-baselined; 1.5 LLM judge with reported human agreement of at least 0.8; 1 partial validation (jury consensus, self-consistency, classifier without an agreement figure); 0.5 unvalidated judge. One correction from the fact-checked draft: FORTRESS moves from 1 to 1.5 (grader majority 89.05% agreement with human labels, `fortress.json`; the candidates file says "judge agreement not fetched").
- Weight 2 on hazard: with weight 1 the step from an unvalidated judge to a programmatic score (1.5 points) is worth one and a half publishers, and checkability barely moves the ranking. Weight 2 makes it worth three publishers while presence stays the larger term (0 to 10 against 1 to 4).
- Penalties kept: capability benchmark -1 (LAB-Bench only, as in the candidates file). Construct -1 only where the documented problem drives the score on a large share of items, so the score does not measure the hazard: WMDP (shortcuts on over 30% of WMDP-Bio without the question text), ABC-Bench (refusals on two of three tasks), HPCT (87 of 100 questions refusal-flagged, the same confound), Agentic Misalignment (blackmail 55.1% when the model states the scenario is real against 6.5% when it states it is an evaluation).
- Dropped: the source term (public, paper), the instrument term (tool, generator), and the penalties for saturation, private, no primary source, and construct problems that do not break the hazard link (contamination risk without a measured effect, scorer gaming caught by the judge, realism gaps, under-elicitation, unmeasured evaluation-awareness clues, construction errors on unspecified items).
- Near-identical clusters, fixed before scoring from the merge candidates in `INDEX.md` and the earlier reviews: known-vulnerability exploitation (ExploitGym, ExploitBench, CVE-Bench); end-to-end network intrusion (cyber range, CyScenarioBench); expert-baselined biology knowledge and troubleshooting (VCT, LAB-Bench, HPCT); covert side task under a monitor (SHADE-Arena, ControlArena); self-preservation insider actions (Agentic Misalignment, Bloom); automated jailbreak robustness (StrongREJECT, HarmBench).
- Choice: walk down the ranking and take each evaluation, except that a third member of a cluster is passed over while an evaluation from another domain is still below the cut. Stop at 20.

Physical-AI score = V + H + L, from `research/candidates_physical.json`. All 13 physical-AI drafts pass the one requirement (their C1 there).

- V validity class: 3 field-outcome correlation; 2 quantitative reproduction or correlation at a higher fidelity level; 1 human verification or agreement statistic; 0 none.
- H hazard directness: 2 harmful event observed on a physical system; 1 hazard decided by a simulator predicate or a judge of a plan, answer or video.
- L level spread: +1 for the best candidate at each fidelity level, as assigned in the candidates file.
- Dropped: the cost class K and the criteria C2 to C5 (public source, cost or validity fact, single instrument, one per construct).
- Ties broken by V, then H, then earlier first version.
- Choice: the 8 candidates with score 3 or more (a clean break: the next score is 2), plus the best candidate at each fidelity level the 8 leave empty.

## LLM evaluations: 20 of 26 chosen

| rank | key | domain | docs/pubs | presence | hazard | penalties | score | include | reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | cybergym | cyber | 34/11 | 10.00 | 2 | - | 14.00 | yes | |
| 2 | vct | cbrn | 35/8 | 10.00 | 2 | - | 14.00 | yes | |
| 3 | cyber_range | cyber | 24/8 | 10.00 | 2 | - | 14.00 | yes | |
| 4 | exploitgym | cyber | 23/8 | 9.92 | 2 | - | 13.92 | yes | |
| 5 | exploitbench | cyber | 26/7 | 9.00 | 2 | - | 13.00 | yes | second known-vulnerability exploitation |
| 6 | cybench | cyber | 16/7 | 8.33 | 2 | - | 12.33 | yes | |
| 7 | labbench_bio | cbrn | 30/7 | 9.00 | 2 | capability -1 | 12.00 | yes | second expert-baselined biology test |
| 8 | binary_exploitation | cyber | 15/6 | 7.25 | 2 | - | 11.25 | yes | unknown-vulnerability discovery, own construct |
| 9 | cvebench | cyber | 14/6 | 7.17 | 2 | - | 11.17 | no | third known-vulnerability exploitation; passed over for FORTRESS and AgentHarm (societal harm) |
| 10 | strongreject | societal_harm | 12/7 | 8.00 | 1.5 | - | 11.00 | yes | |
| 11 | shade_arena | loss_of_control | 20/5 | 6.67 | 2 | - | 10.67 | yes | |
| 12 | wmdp | cbrn | 14/6 | 7.17 | 2 | construct -1 | 10.17 | yes | hazardous-knowledge proxy without a human baseline, not in the biology cluster |
| 13 | mask | harmful_manipulation | 19/5 | 6.58 | 1.5 | - | 9.58 | yes | |
| 14 | petri | harmful_manipulation | 15/6 | 7.25 | 1 | - | 9.25 | yes | |
| 15 | cyscenariobench | cyber | 13/4 | 5.08 | 2 | - | 9.08 | yes | second end-to-end intrusion |
| 16 | controlarena | loss_of_control | 5/4 | 4.42 | 2 | - | 8.42 | yes | second covert side task |
| 17 | hpct | cbrn | 12/4 | 5.00 | 2 | construct -1 | 8.00 | no | third expert-baselined biology test; passed over for domain coverage |
| 18 | bloom | loss_of_control | 11/4 | 4.92 | 1.5 | - | 7.92 | yes | second self-preservation |
| 19 | abcbench | cbrn | 10/4 | 4.83 | 2 | construct -1 | 7.83 | yes | |
| 20 | agentic_misalignment | loss_of_control | 12/5 | 6.00 | 1 | construct -1 | 7.00 | yes | |
| 21 | fortress | societal_harm | 6/3 | 3.50 | 1.5 | - | 6.50 | yes | |
| 22 | agentharm | societal_harm | 3/2 | 2.25 | 2 | - | 6.25 | yes | 20th chosen |
| 23 | bbq | societal_harm | 11/1 | 1.92 | 2 | - | 5.92 | no | below the cut |
| 24 | biotier | cbrn | 10/3 | 3.83 | 1 | - | 5.83 | no | below the cut |
| 25 | harmbench | societal_harm | 4/2 | 2.33 | 1.5 | - | 5.33 | no | below the cut |
| 26 | deceptionbench | harmful_manipulation | 3/2 | 2.25 | 1.5 | - | 5.25 | no | below the cut |

Below the cut there is no clear break (7.00, 6.50, 6.25, 5.92, 5.83), so the count stays at the target of 20.

## Physical-AI evaluations: 9 of 13 chosen

| rank | key | level | system type | V | H | L | score | include | reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | iihs_paeb | 8 | non-learning production AEB (automatic emergency braking) stack on a vehicle | 3 | 2 | 1 | 6 | yes | |
| 2 | veo_worldmodel | 5 | VLA (vision-language-action) policy, evaluated in a video world model | 2 | 1 | 1 | 4 | yes | |
| 3 | redvla | 4 | VLA policy in simulation, attacks reproduced on hardware | 2 | 1 | 1 | 4 | yes | |
| 4 | robopair | 7 | LLM planner inside a robot (wheeled and legged robots) | 1 | 2 | 1 | 4 | yes | |
| 5 | iso10218_pfl | 7 | non-learning collaborative robot (power and force limiting) | 1 | 2 | 0 | 3 | yes | |
| 6 | maniguard | 7 | VLA manipulation policy, violations scored on hardware | 1 | 2 | 0 | 3 | yes | |
| 7 | asimov2 | 3 | VLM (vision-language model) planner judging danger in images and video | 1 | 1 | 1 | 3 | yes | |
| 8 | asimov_agentic | 2 | embodied-reasoning VLM orchestrating a VLA, on recorded sensor data | 1 | 1 | 1 | 3 | yes | |
| 9 | safeagentbench | 4 | LLM planner inside a simulated household agent | 1 | 1 | 0 | 2 | no | level 4 covered by RedVLA |
| 10 | isbench | 4 | VLM agent in a simulated household | 1 | 1 | 0 | 2 | no | level 4 covered by RedVLA |
| 11 | egosafetybench | 3 | VLM runtime guard on egocentric video | 1 | 1 | 0 | 2 | no | level 3 covered by ASIMOV-2.0 |
| 12 | safeplan | 0 | LLM planner on text commands to a service robot | 0 | 1 | 1 | 2 | yes | best at level 0, which the 8 leave empty |
| 13 | humanoid_orchestrator | 0 | LLM orchestrator of a humanoid, scripted sensor readings | 0 | 1 | 0 | 1 | no | level 0 covered by SafePlan |

Levels 1, 6 and 9 have no draft. SafePlan is the one evaluation chosen out of rank order; without it physical AI has no level-0 point, the level at which most LLM evaluations sit (text questions).

## Chosen counts

| group | stratum | chosen | not chosen |
|---|---|---|---|
| LLM | cyber | 7 | 1 |
| LLM | cbrn | 4 | 2 |
| LLM | loss_of_control | 4 | 0 |
| LLM | harmful_manipulation | 2 | 1 |
| LLM | societal_harm | 3 | 2 |
| LLM | total | 20 | 6 |
| physical AI | level 8 | 1 | 0 |
| physical AI | level 7 | 3 | 0 |
| physical AI | level 5 | 1 | 0 |
| physical AI | level 4 | 1 | 2 |
| physical AI | level 3 | 1 | 1 |
| physical AI | level 2 | 1 | 0 |
| physical AI | level 0 | 1 | 1 |
| physical AI | total | 9 | 4 |

System types among the 9: non-learning physical system 2 (IIHS, ISO 10218); VLA policy 3 (Veo, RedVLA, ManiGuard); LLM or VLM inside a robot 4 (RoboPAIR, ASIMOV-2.0, ASIMOV-Agentic, SafePlan).

Cyber is 7 of 20. That follows from presence: public, programmatically scored cyber evaluations are the ones most publishers name. Only the third exploitation evaluation is passed over.

## Possible additions without drafts

Each would need context writing, fact-checking and elicitation. Scores use the same rule; for physical AI, V and H for candidates the candidates file did not rank are this review's reading of the facts recorded there.

LLM (from `candidates_frontier.json`; the 20th chosen scores 6.25):

| candidate | domain | docs/pubs | score | note |
|---|---|---|---|---|
| Indirect prompt injection evaluations (Gray Swan; lab-internal) | cyber | 17/4 | 7.42 | own construct; each lab runs its own private set, so a draft would have to fix one (Gray Swan's) |
| Multi-turn jailbreak evaluations (OpenAI; xAI Crescendo) | societal_harm | 13/4 | 7.08 | would be the second jailbreak-robustness evaluation; lab-specific sets |
| Long-form virology tasks (Anthropic with SecureBio and others) | cbrn | 12/2 | 7.00 | agentic long-form construct, not the knowledge-test cluster |
| Agent Red Teaming (Gray Swan with UK AISI) | cyber | 11/3 | 5.92 | below the cut; ties BBQ |

Ranked inside by score but third or later members of a cluster, so they would be passed over as HPCT is: MBCT (8.92), tacit-knowledge and troubleshooting MCQ (8.42), World Class Bio (6.58), all in the biology knowledge cluster; Minimal-LinuxBench (7.75) and SHUSHCAST (7.33), covert side task. Reward hacking (39 documents, 11 publishers) and sycophancy (29, 9) are behaviours with lab-specific graders and no named evaluation to draft.

Physical AI (from `candidates_physical.json`; the 8th by score has 3):

| candidate | level | system type | V | H | L | score | note |
|---|---|---|---|---|---|---|---|
| NHTSA FMVSS No. 127 AEB compliance test | 8 | non-learning production AEB | 1 | 2 | 0 | 3 | ties the score-3 group; a second level-8 point |
| Waymo Collision Avoidance Testing | 5 | automated driving system (learned stack) | 2 | 1 | 0 | 3 | simulation checked against track runs; proprietary programme |
| EmbodyGuard | 0 | LLM planner, PDDL-grounded scenarios | 1 | 1 | 1 | 3 | expert-reviewed; would take level 0 from SafePlan (V0) |
| EARBench, MSSBench or RoboJailBench | 1 | VLM or embodied VLM | 0 | 1 | 1 | 2 | level 1 is empty; would enter by the spread rule as SafePlan does |

## What changed against QUALITY_REVIEW.md and QUALITY_REVIEW_2.md

Both stay as history. QUALITY_REVIEW.md kept 15 LLM and 7 physical-AI evaluations under its cut criteria; QUALITY_REVIEW_2.md recommended reinstating ASIMOV-Agentic and DeceptionBench.

- LLM in: ExploitBench, Binary Exploitation Benchmark, CyScenarioBench, LAB-Bench, Petri, Bloom, ControlArena. Their cut reasons were duplication of a single kept evaluation, private status, no primary source, being a tool or generator, or the capability origin; only the last remains, as a 1-point penalty.
- LLM out: CVE-Bench (now the third known-vulnerability exploitation evaluation, after ExploitBench came in on presence) and BBQ (one publisher; below the cut).
- DeceptionBench stays out, now for low presence (3 documents, 2 publishers), not for the 0.25-point floor miss QUALITY_REVIEW_2.md disputed. Its awareness penalty is dropped.
- HPCT stays out, now as the third biology knowledge test. It was the evaluation on which Sonnet's API refused the decision prompt; that played no part.
- FORTRESS: hazard class corrected from 1 to 1.5 using the draft's 89.05% agreement figure.
- Physical AI in: ASIMOV-Agentic (as QUALITY_REVIEW_2.md recommended), ManiGuard (its cut rested on the source and sim-to-real criteria that are dropped) and SafePlan (no validity fact is no longer a cut reason; chosen for level 0).
- Physical AI out: SafeAgentBench, at score 2 behind RedVLA at level 4. Its 91% human-judge agreement scores as V1, as for the others at level 4.
- Counts: 20 LLM (was 15) and 9 physical AI (was 7); levels 0 and 2 now covered.
- Known context issue: Bloom's decision facts rest mostly on the Agentic Misalignment hazard results (INDEX.md, unresolved issues), and both are now chosen. Their decision prompts are therefore close; the instrument prompts differ.
