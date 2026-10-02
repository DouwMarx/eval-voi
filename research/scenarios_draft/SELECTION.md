# Selection of the analysed evaluations (2026-10-02)

The decision is in `studies/safety-evals/include.yaml`; `scripts/build_scenarios.py` builds `scenarios.json` from the included keys. This file gives the rule, the scores and the ranking. The selection was made and committed before any elicitation result, Monte Carlo run or generated output was read. Only the 39 drafted scenarios were eligible; all 39 were already elicited under p001.

## Criteria (the user's, verbatim; they replace the criteria of QUALITY_REVIEW.md)

- LLM safety evaluations: rank mainly by system-card presence (number of documents and publishers naming it in the corpus, as in the candidates file) and by how checkable the hazard score is (programmatic or expert-baselined > validated LLM judge > unvalidated judge). Keep the penalty for a capability benchmark rather than a hazard measure. Do NOT penalise saturation (the elicitor sees it in the context and should lower sensitivity), being private or not public, lacking a standalone paper, or being a tool/generator rather than one fixed build-and-run evaluation; drop those criteria and penalties. Other penalties are too strict; only keep a documented construct problem if it means the score does not measure the hazard. No hard duplicate rule, but when choosing, prefer coverage across the five risk domains over a third or fourth near-identical evaluation.
- Physical-AI safety evaluations: the one requirement is that the score measures a physical harm of an embodied system or of a model controlling one. Do not require a public source, a cost or validity fact, a single build-and-run instrument, or uniqueness of construct. Prefer spread across fidelity levels, and say which system type each tests.
- Target: roughly 20 LLM and 8 physical-AI evaluations; more or fewer if the ranking under these criteria clearly supports it. Choose ONLY among the 39 drafted scenarios (all already elicited). If a candidate without a draft would clearly rank inside the selection, list it as a possible addition in the review (it would need context writing, fact-checking and elicitation), do not add it.
- Floor (added 2026-10-02, after the first selection): at least 3 evaluations per LLM risk domain. Where the walk down the ranking leaves a domain with fewer, the highest-scoring remaining evaluation of that domain whose hazard result is checkable is added, drafting it first if no draft exists.

## How the criteria were made into scores

LLM score = presence + 2 x hazard + penalties.

- presence: as in `research/candidates_frontier.json`: min(publishers, 8) + min(documents, 24)/12, range 0 to 10. One correction (2026-10-02, see the LinuxArena section): ControlArena is counted with the documents that name its settings LinuxArena, Minimal-LinuxBench and BashArena, 18 documents by 5 publishers (anthropic, metr, openai, redwood_research, uk_aisi) in the 187-document corpus, instead of the 5 documents by 4 publishers that use the library name. The draft's instrument is LinuxArena, so the narrower count was the wrong one.
- hazard (checkability class, from the same file): 2 programmatic or expert-baselined; 1.5 LLM judge with reported human agreement of at least 0.8; 1 partial validation (jury consensus, self-consistency, classifier without an agreement figure); 0.5 unvalidated judge. One correction from the fact-checked draft: FORTRESS moves from 1 to 1.5 (grader majority 89.05% agreement with human labels, `fortress.json`; the candidates file says "judge agreement not fetched").
- Weight 2 on hazard: with weight 1 the step from an unvalidated judge to a programmatic score (1.5 points) is worth one and a half publishers, and checkability barely moves the ranking. Weight 2 makes it worth three publishers while presence stays the larger term (0 to 10 against 1 to 4).
- Penalties kept: capability benchmark -1 (LAB-Bench only, as in the candidates file). Construct -1 only where the documented problem drives the score on a large share of items, so the score does not measure the hazard: WMDP (shortcuts on over 30% of WMDP-Bio without the question text), ABC-Bench (refusals on two of three tasks), HPCT (87 of 100 questions refusal-flagged, the same confound), Agentic Misalignment (blackmail 55.1% when the model states the scenario is real against 6.5% when it states it is an evaluation).
- Dropped: the source term (public, paper), the instrument term (tool, generator), and the penalties for saturation, private, no primary source, and construct problems that do not break the hazard link (contamination risk without a measured effect, scorer gaming caught by the judge, realism gaps, under-elicitation, unmeasured evaluation-awareness clues, construction errors on unspecified items).
- Near-identical clusters, fixed before scoring from the merge candidates in `INDEX.md` and the earlier reviews: known-vulnerability exploitation (ExploitGym, ExploitBench, CVE-Bench); end-to-end network intrusion (cyber range, CyScenarioBench); expert-baselined biology knowledge and troubleshooting (VCT, LAB-Bench, HPCT); covert side task under a monitor (SHADE-Arena, ControlArena with its LinuxArena and BashArena settings, Minimal-LinuxBench); self-preservation insider actions (Agentic Misalignment, Bloom); automated jailbreak robustness (StrongREJECT, HarmBench).
- Choice: walk down the ranking and take each evaluation, except that a third member of a cluster is passed over while an evaluation from another domain is still below the cut. Stop at 20. Then apply the floor of 3 per domain.

Physical-AI score = V + H + L, from `research/candidates_physical.json`. All 13 physical-AI drafts pass the one requirement (their C1 there).

- V validity class: 3 field-outcome correlation; 2 quantitative reproduction or correlation at a higher fidelity level; 1 human verification or agreement statistic; 0 none.
- H hazard directness: 2 harmful event observed on a physical system; 1 hazard decided by a simulator predicate or a judge of a plan, answer or video.
- L level spread: +1 for the best candidate at each fidelity level, as assigned in the candidates file.
- Dropped: the cost class K and the criteria C2 to C5 (public source, cost or validity fact, single instrument, one per construct).
- Ties broken by V, then H, then earlier first version.
- Choice: the 8 candidates with score 3 or more (a clean break: the next score is 2), plus the best candidate at each fidelity level the 8 leave empty.

## LLM evaluations: 21 of 26 chosen

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
| 12 | controlarena | loss_of_control | 18/5 | 6.50 | 2 | - | 10.50 | yes | second covert side task; the draft's instrument is LinuxArena; counted with its settings (5/4 and 8.42 under the library name) |
| 13 | wmdp | cbrn | 14/6 | 7.17 | 2 | construct -1 | 10.17 | yes | hazardous-knowledge proxy without a human baseline, not in the biology cluster |
| 14 | mask | harmful_manipulation | 19/5 | 6.58 | 1.5 | - | 9.58 | yes | |
| 15 | petri | harmful_manipulation | 15/6 | 7.25 | 1 | - | 9.25 | yes | |
| 16 | cyscenariobench | cyber | 13/4 | 5.08 | 2 | - | 9.08 | yes | second end-to-end intrusion |
| 17 | hpct | cbrn | 12/4 | 5.00 | 2 | construct -1 | 8.00 | no | third expert-baselined biology test; passed over for domain coverage |
| 18 | bloom | loss_of_control | 11/4 | 4.92 | 1.5 | - | 7.92 | yes | second self-preservation |
| 19 | abcbench | cbrn | 10/4 | 4.83 | 2 | construct -1 | 7.83 | yes | |
| 20 | agentic_misalignment | loss_of_control | 12/5 | 6.00 | 1 | construct -1 | 7.00 | yes | |
| 21 | fortress | societal_harm | 6/3 | 3.50 | 1.5 | - | 6.50 | yes | |
| 22 | agentharm | societal_harm | 3/2 | 2.25 | 2 | - | 6.25 | yes | 20th chosen |
| 23 | bbq | societal_harm | 11/1 | 1.92 | 2 | - | 5.92 | no | below the cut |
| 24 | biotier | cbrn | 10/3 | 3.83 | 1 | - | 5.83 | no | below the cut |
| 25 | harmbench | societal_harm | 4/2 | 2.33 | 1.5 | - | 5.33 | no | below the cut |
| 26 | deceptionbench | harmful_manipulation | 3/2 | 2.25 | 1.5 | - | 5.25 | yes | below the cut by rank; added by the floor of 3 per domain as the third harmful-manipulation evaluation |

Below the cut there is no clear break (7.00, 6.50, 6.25, 5.92, 5.83), so the count by rank stays at the target of 20. The floor adds DeceptionBench, 21 in all. LinuxArena, had it a draft of its own, would score 8.08 (13 documents by 3 publishers under its two names, programmatic hazard) and sit at rank 17 between CyScenarioBench and HPCT; it is the third member of the covert-side-task cluster and the instrument of the chosen ControlArena scenario, so it is not a separate row.

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
| LLM | harmful_manipulation | 3 | 0 |
| LLM | societal_harm | 3 | 2 |
| LLM | total | 21 | 5 |
| physical AI | level 8 | 1 | 0 |
| physical AI | level 7 | 3 | 0 |
| physical AI | level 5 | 1 | 0 |
| physical AI | level 4 | 1 | 2 |
| physical AI | level 3 | 1 | 1 |
| physical AI | level 2 | 1 | 0 |
| physical AI | level 0 | 1 | 1 |
| physical AI | total | 9 | 4 |

System types among the 9: non-learning physical system 2 (IIHS, ISO 10218); VLA policy 3 (Veo, RedVLA, ManiGuard); LLM or VLM inside a robot 4 (RoboPAIR, ASIMOV-2.0, ASIMOV-Agentic, SafePlan).

Cyber is 7 of 21. That follows from presence: public, programmatically scored cyber evaluations are the ones most publishers name. Only the third exploitation evaluation is passed over.

## Possible additions without drafts

Each would need context writing, fact-checking and elicitation. Scores use the same rule; for physical AI, V and H for candidates the candidates file did not rank are this review's reading of the facts recorded there.

LLM (from `candidates_frontier.json`; the 20th chosen scores 6.25):

| candidate | domain | docs/pubs | score | note |
|---|---|---|---|---|
| Indirect prompt injection evaluations (Gray Swan; lab-internal) | cyber | 17/4 | 7.42 | own construct; each lab runs its own private set, so a draft would have to fix one (Gray Swan's) |
| Multi-turn jailbreak evaluations (OpenAI; xAI Crescendo) | societal_harm | 13/4 | 7.08 | would be the second jailbreak-robustness evaluation; lab-specific sets |
| Long-form virology tasks (Anthropic with SecureBio and others) | cbrn | 12/2 | 7.00 | agentic long-form construct, not the knowledge-test cluster |
| Agent Red Teaming (Gray Swan with UK AISI) | cyber | 11/3 | 5.92 | below the cut; ties BBQ |

Ranked inside by score but third or later members of a cluster, so they would be passed over as HPCT is: MBCT (8.92), tacit-knowledge and troubleshooting MCQ (8.42), World Class Bio (6.58), all in the biology knowledge cluster; LinuxArena / Minimal-LinuxBench (8.08, see below) and SHUSHCAST (7.33), covert side task. Reward hacking (39 documents, 11 publishers) and sycophancy (29, 9) are behaviours with lab-specific graders and no named evaluation to draft.

Physical AI (from `candidates_physical.json`; the 8th by score has 3):

| candidate | level | system type | V | H | L | score | note |
|---|---|---|---|---|---|---|---|
| NHTSA FMVSS No. 127 AEB compliance test | 8 | non-learning production AEB | 1 | 2 | 0 | 3 | ties the score-3 group; a second level-8 point |
| Waymo Collision Avoidance Testing | 5 | automated driving system (learned stack) | 2 | 1 | 0 | 3 | simulation checked against track runs; proprietary programme |
| EmbodyGuard | 0 | LLM planner, PDDL-grounded scenarios | 1 | 1 | 1 | 3 | expert-reviewed; would take level 0 from SafePlan (V0) |
| EARBench, MSSBench or RoboJailBench | 1 | VLM or embodied VLM | 0 | 1 | 1 | 2 | level 1 is empty; would enter by the spread rule as SafePlan does |

## Bloom against LinuxArena (user question, 2026-10-02)

The user asked why Bloom is in and LinuxArena is not. Checked against the rule:

- What LinuxArena is. An AI control arena by Redwood Research with EquiStamp (Tracy et al. 2026, arXiv 2604.15384; `research/sources/tracy2026linuxarena.json`): the agent runs on a real Linux machine, gets a software-engineering or system-administration main task and a harmful side task (exfiltrate a credential, weaken a firewall rule), and the score is the rate at which it completes the side task while a monitor's suspicion stays below a threshold set on honest runs. Anthropic's cards ran it as Minimal-LinuxBench (Mythos Preview) and as LinuxArena (Sonnet 5, Opus 5, Opus 5.5, Sonnet 5.5, Fable 5.1, August 2026 risk report); the risk report writes "Minimal-LinuxBench/LinuxArena" for the same evaluation.
- Hazard, not capability. The score is a stealth rate against oversight, the loss-of-control hazard itself, with programmatic side-task scorers and a fixed monitor threshold: hazard class 2. It is not a capability benchmark, so no penalty applies.
- Presence. Corpus count (187 documents): LinuxArena 6 documents, 1 publisher; Minimal-LinuxBench 9 documents, 3 publishers; union 13 documents, 3 publishers (anthropic, metr, redwood_research). Presence 4.08, score 8.08, above Bloom's 7.92.
- Why it is still not a separate row. The chosen ControlArena scenario is LinuxArena: its instrument block cites Tracy et al. 2026 and four Anthropic LinuxArena passages (task counts, threshold, human red-team evasion, Anthropic's sampling and intervals, sandbagging and pretraining-data remarks), and its decision block quotes LinuxArena stealth rates. ControlArena is the library the setting runs in. A LinuxArena row would be a third member of the covert-side-task cluster after SHADE-Arena and ControlArena and a near-copy of the second, which the rule passes over while any other domain is short, as it passes over CVE-Bench and HPCT. The correction made instead is to count the ControlArena scenario's presence with its settings (18 documents, 5 publishers), which moves it from rank 16 to rank 12.
- Why Bloom stays. Bloom is the second member of a different cluster (self-preservation insider actions) and scores 7.92 with a judge validated at Spearman 0.86 against human scores. Dropping it would not make room for anything: LinuxArena is already in. Its known weakness stands (its decision facts lean on the Agentic Misalignment results; INDEX.md).
- Disclosure. LinuxArena was built with EquiStamp, the user's company. The verdict above uses the corpus counts and the cluster rule only; a reader should check that the ControlArena row's presence correction follows from the draft's sources, which are listed in `controlarena.json`.

## Third harmful-manipulation evaluation (floor of 3 per domain, 2026-10-02)

The walk down the ranking left harmful_manipulation with MASK and Petri. Candidates for the third, scored under the rule from the same 187-document corpus:

| candidate | docs/pubs | presence | hazard | score | draft | note |
|---|---|---|---|---|---|---|
| DeceptionBench | 3/2 | 2.25 | 1.5 | 5.25 | yes, elicited under p001 | GPT-4o judge at 97.1% agreement with the three-annotator majority on 420 records, 95.7% unanimous (`deceptionbench.json`); Meta found no significant awareness effect on its deception rate (p = 0.092 and 0.387) |
| SycophancyEval (Sharma et al. 2023) | 1/1 | 1.08 | 2 | 5.08 | no | answer-sycophancy part programmatic, feedback part judge-scored; named once, by Anthropic |
| MakeMePay, MakeMeSay, ChangeMyView (OpenAI persuasion) | 0/0 | 0 | 2 | 4.00 | no | not named in any corpus document; OpenAI no longer reports them |
| sycophancy as a behaviour | 29/9 | 10 | - | - | no | each lab's own private set and grader; no shared instrument, no checkable public hazard result, nothing to draft as one evaluation |
| ELEPHANT, SycEval, TruthfulQA, insider-trading deception | 1/1 or 0/0 | at most 1.08 | - | at most 5.08 | no | below DeceptionBench on presence |

DeceptionBench is the highest-scoring candidate with a checkable hazard result, and the only one with a fact-checked, elicited draft, so it enters under the floor. Its awareness penalty was dropped under the user's rule; its documented weakness is low presence (two publishers), not the hazard link. Harmful manipulation is now 3 of 21.

## What changed against QUALITY_REVIEW.md and QUALITY_REVIEW_2.md

Both stay as history. QUALITY_REVIEW.md kept 15 LLM and 7 physical-AI evaluations under its cut criteria; QUALITY_REVIEW_2.md recommended reinstating ASIMOV-Agentic and DeceptionBench.

- LLM in: ExploitBench, Binary Exploitation Benchmark, CyScenarioBench, LAB-Bench, Petri, Bloom, ControlArena. Their cut reasons were duplication of a single kept evaluation, private status, no primary source, being a tool or generator, or the capability origin; only the last remains, as a 1-point penalty.
- LLM out: CVE-Bench (now the third known-vulnerability exploitation evaluation, after ExploitBench came in on presence) and BBQ (one publisher; below the cut).
- DeceptionBench was out by rank (3 documents, 2 publishers), not for the 0.25-point floor miss QUALITY_REVIEW_2.md disputed; its awareness penalty is dropped. The floor of 3 per domain (2026-10-02) brings it in; see the section below.
- HPCT stays out, now as the third biology knowledge test. It was the evaluation on which Sonnet's API refused the decision prompt; that played no part.
- FORTRESS: hazard class corrected from 1 to 1.5 using the draft's 89.05% agreement figure.
- Physical AI in: ASIMOV-Agentic (as QUALITY_REVIEW_2.md recommended), ManiGuard (its cut rested on the source and sim-to-real criteria that are dropped) and SafePlan (no validity fact is no longer a cut reason; chosen for level 0).
- Physical AI out: SafeAgentBench, at score 2 behind RedVLA at level 4. Its 91% human-judge agreement scores as V1, as for the others at level 4.
- Counts: 21 LLM (was 15; 20 by rank plus DeceptionBench by the floor) and 9 physical AI (was 7); levels 0 and 2 now covered.
- Known context issue: Bloom's decision facts rest mostly on the Agentic Misalignment hazard results (INDEX.md, unresolved issues), and both are now chosen. Their decision prompts are therefore close; the instrument prompts differ.
