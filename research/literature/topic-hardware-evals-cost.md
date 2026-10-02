# Hardware and real-robot safety evaluations: what they cost and what they predict

Literature sweep for the VOI-of-robot-safety-evaluations workshop paper. Scope: real-robot and hardware evaluations, standards-based track/contact tests and deployment monitoring, 2018-2026 (two pre-2018 canonical items kept and flagged). 60 entries, 59 with the primary URL fetched. Ladder levels use the 0-9 sim-to-real scale from the brief.

## One-page synthesis

What exists
- Level 7 (real robot, lab) is now a crowded space for *capability* evaluation of generalist policies: RoboArena (7 sites, 4284 episodes), RoboChallenge (10-robot fleet, 30 tasks x 10 rollouts), AutoEval (24/7 WidowX stations), ArmnetBench (SO-101 farm, 2518 rollouts), RB2, RoboDojo, VLA-REPLICA. Almost none of these score *safety*; they score task success.
- Level 7 *safety* evaluation of LLM/VLA-controlled robots is small-n and mostly red-teaming: RoboPAIR (100% jailbreak on Go2/Jackal/Dolphins), BadRobot, Phantom Menace (physical sensor attacks), SafeLoop (25 rollouts per real task). Andon Labs' Butter-Bench (6 subtasks x 5 trials, TurtleBot4) and Drone-Bench / Anthropic Project Pilot (USD 129 Tello, 15 models x 10 runs) are the only frontier-model-facing hardware evals with a public human baseline, and both lean on simulation or replay for the scored part.
- Level 8 (humans or surrogates in the loop) is essentially the automotive world: IIHS P-AEB (36 scored runs per vehicle with articulated dummies, day and night) and Euro NCAP AEB VRU. For robots, the equivalent is ISO/TS 15066 collision testing with biofidelic devices, whose limits rest on human pain-threshold studies (Han et al. 2024, n=37).
- Level 9 (deployment) evidence is dominated by AV crash-rate studies (Waymo 7.1M, 56.7M, now 271M rider-only miles; Cruise/UMTRI 5.6M human miles) and by warehouse injury logs (Amazon robotic sites 7.9 vs 5.1 serious injuries per 100 workers). NHTSA SGO reporting is the shared data source.
- Humanoid safety testing has no ratified standard: ISO/CD 25785-1 is a committee draft (stability, fall, contact tests under rated load), the IEEE/ASTM pathway study (Sep 2025) names stability as the bottleneck, and the only hardware studies are certification gap analyses on a Unitree G1 (fail-passive gap, safe-stoppability monitors).

Where cost evidence is strong
- Hardware floor: SO-101 arm USD 122 (follower) to USD 230 (leader+follower); ALOHA USD 20k; DJI Tello EDU USD 129; DROID rig is a Franka Panda plus three Zed cameras and a Quest 2 (no dollar figure).
- Human time: AutoEval cuts operator time >99% (3 interventions per ~850 episodes per 24 h; classifier trained on ~1000 labelled images per scene). Zero2Skill cuts collection time to 16%. DROID needed 50 collectors and 12 months for 350 h of demonstrations. TRI ran 1800 real rollouts (50 per condition) to get statistically separable results.
- Compute: Anthropic's simulated robotics suite cost 30 min to 18 h per model-condition cell, thousands of GPU/CPU hours total; Drone-Bench scoring uses one T4 with up to 5 h per submission.
- Deployment: RAND's 275M failure-free miles (about 12.5 fleet-years for 100 vehicles) for a fatality-rate claim; Waymo needed ~57M miles before crash-type-level conclusions on serious injuries were statistically significant.

Where cost evidence is absent
- No robot benchmark reports dollars or person-hours per evaluated episode. RoboArena, RoboChallenge and RoboDojo describe fleets and protocols but not labour. Euro NCAP and IIHS publish protocols, not costs. Humanoid standards drafts contain no test-cost estimates.

Where validity evidence is strong
- Cheap-vs-expensive agreement inside robotics: AutoEval r=0.942 / MMRV 0.015 vs human-run evals; SIMPLER (1500 paired episodes) and X2Real (r=0.84) for sim vs real; RoboWorld r=0.989 / rho=0.970 for neural-sim vs real; Gemini Robotics Veo simulator validated against >1600 real evaluations; SureSim turns this into a 20-25% reduction in hardware trials with valid confidence intervals.
- Track test to outcome (automotive): HLDI shows pedestrian AEB systems rated by IIHS cut pedestrian claims 27-35% (none in unlit dark, which drove the night test); Kullgren et al. show 5-star Euro NCAP cars have 23% (+/-8) lower fatal+serious injury risk than 2-star cars.

Where validity evidence is absent
- No robot safety benchmark (any level) has been correlated with deployment harm. The Cruise case (benchmark press release one week before the pedestrian-dragging incident, permit suspended, 950-vehicle recall) is the clearest illustration that aggregate crash-rate benchmarks miss tail failure modes.
- False-alarm behaviour is almost never reported; the LLM-orchestrator humanoid benchmark (over-compliance vs violation, 40 sessions x 100 turns) is the only entry that scores both axes.
- Red-team results report attack success but not base rates or reproducibility across seeds.

Canonical entries for a 4-page paper (5-8)
1. zhou2025autoeval: the cleanest cost (>99% human-time reduction) and validity (r=0.942 vs humans) numbers for level 7.
2. atreya2025roboarena: distributed level-7 evaluation, ranking accuracy vs oracle, 4284 episodes.
3. tri2025lbm: how many real trials a defensible comparison needs (50 per condition, 1800 total, blind A/B, sequential tests).
4. badithela2025suresim (with li2024simpler): the sim-plus-few-real-trials trade with valid confidence intervals; direct VOI framing.
5. kusano2025waymo56m (with kalra2016drivingtosafety): what level-9 evidence costs in miles and what it can and cannot conclude.
6. iihs2024paeb (with kullgren2010euroncap): the only level-8 protocol with published real-world validity (HLDI 27-35% claim reduction).
7. sharrock2026dronebench / anthropic2026projectpilot: frontier-model hardware eval with explicit hardware and compute cost and sim-to-real checks.
8. robey2024robopair: level-7 safety red-team on commercial robots (100% success) to contrast capability vs safety evaluation density.

Ladder coverage in this file: level 0 (1), 3 (1), 4 (5), 5 (5), 6 (1), 7 (31), 8 (3), 9 (11), unrated (2). Speaker links: Sindhwani (ASIMOV, Veo simulator), Bajcsy (latent safety filters). No verified Pavone or Fel items in this topic.

Caveats: web-search budget was exhausted mid-sweep, so the last discovery rounds used the arXiv API only; two rounds of arXiv queries added no new hardware-cost items, which is the stopping criterion from the brief. iso.org, nhtsa.gov, rand.org, tandfonline and euroncap protocol PDFs blocked fetches; those entries carry medium confidence and note the secondary source used.

## Overview table

| key | level | kind | safety | cost evidence (short) | validity evidence (short) |
|---|---|---|---|---|---|
| sharrock2025butterbench | 7 | benchmark | y | Hardware: TurtleBot 4 Standard (iRobot Create 3 base, ~USD 2k class); 5 trials/t | Human baseline (95%) as reference; qualitative safety/privacy probes (low-batter |
| sharrock2026dronebench | 4 | benchmark | y | Hardware: DJI Tello EDU, USD 129; scoring compute: one NVIDIA T4 per submission  | Sim-to-real alignment checked by running reference and top submissions in both s |
| anthropic2026projectpilot | 7 | study | y | DJI Tello EDU at USD 129; office environment; no labour hours stated. | Physical end-to-end runs used to check that simulator scores translate to the re |
| anthropic2026claudeplaysrobotics | 4 | benchmark | y | 35-200 trials per cell, 30 min to 18 h per cell, 'thousands of GPU/CPU hours' to | none stated (simulation only; no real-hardware transfer reported). |
| anthropic2025projectfetch | 7 | study | y | One-day uplift study with 8 engineers and a commercial quadruped; no budget stat | none stated (small n, single day). |
| atreya2025roboarena | 7 | benchmark | n | Human evaluators at 7 sites run every episode by hand (setup, reset, judging); l | Ranking accuracy validated against an oracle computed by exhaustive evaluation ( |
| dasari2022rb2 | 7 | benchmark | n | Requires each lab to rebuild the setup and rerun baselines; no hours stated. | Cross-lab consistency of baseline ranking (2 venues). |
| zhou2025autoeval | 7 | tooling | n | >99% reduction in human operator time; 42 evaluation steps/min; setup 1-3 h acti | Agreement with human-run evaluation of the same policies (r=0.942, MMRV 0.015);  |
| yakefu2025robochallenge | 7 | benchmark | n | Fleet of 10 machines across 4 types; human testers reset scenes; no labour hours | Visual-reference scene reproduction for consistency; no inter-run agreement stat |
| selvaraj2026armnetbench | 7 | benchmark | n | SO-101 arm BOM ~USD 122 per follower arm (see so-arm100 entry); 'light on-site s | Three-way human labels released; no agreement statistics in abstract. |
| huang2026vlareplica | 7 | benchmark | n | Off-the-shelf components, described as low-cost; no dollar figure in abstract. | Replication across independently built rigs reported as consistent. |
| yu2026so101bench | 7 | benchmark | n | SO-101 hardware (~USD 122/arm BOM); trials not stated. | none stated |
| chen2026robodojo | 7 | benchmark | n | Cloud-based real-eval service with standardised hardware; no cost numbers. | none stated in abstract (sim-real correlation not quantified). |
| li2024simpler | 4 | benchmark | n | Simulation replaces real trials once built; the ~1500 paired real episodes are t | Paired real evaluations on the same policies; correlation of success rates and r |
| jeon2026roboworld | 5 | tooling | n | Claims fast rollouts; no explicit cost numbers in abstract. | Correlation with real-world evaluation (r=0.989, rho=0.970). |
| jangir2025robotarenainf | 5 | benchmark | n | Crowd-worker preference labels replace on-site evaluators; cost not quantified. | Human preference judgements from crowdworkers; agreement with real rankings not  |
| sedlacek2025realm | 5 | benchmark | n | none stated | Real-to-sim validation claimed; numbers in paper body. |
| ruan2026x2real | 4 | benchmark | n | none stated | r = 0.84 sim vs real evaluation. |
| wang2026simrealrecipe | 4 | study | n | none stated | Direct measurement of sim-to-real ranking preservation (numbers in body). |
| gemini2025veosim | 5 | tooling | y | >1600 real-world evaluations used as ground truth for the validation. | Paired real-world evaluations on the same checkpoints. |
| sermanet2025asimov | 3 | benchmark | y | Text/image generation replaces physical trials; no dollar figures. | Agreement with human judgements (84.3%); no link to physical outcomes. |
| tri2025lbm | 7 | study | n | 1800 real rollouts at 50/condition; 9 robot stations for data collection; 468 h  | Statistical framework with explicit power; blind A/B mitigates evaluator bias. |
| vincent2024generalizable | 7 | study | n | Explicitly targets minimal number of hardware rollouts; counts in paper body. | Bounds hold at stated confidence in simulation; hardware generalisation measured |
| badithela2025suresim | 7 | study | n | Quantifies hardware-trial savings (20-25%) from augmenting with simulation. | Confidence intervals are statistically valid by construction regardless of sim f |
| wan2026nofreechecker | None | position | y | Frames cost/timing of verdicts as a first-class axis. | Identifies agreement with human labels as one of three validation measures used  |
| robey2024robopair | 7 | red-team | y | Commercial robots (Unitree Go2, Clearpath Jackal); attack automated by an LLM; n | Harmful actions executed on physical robots (direct observation); no false-alarm |
| zhang2024badrobot | 7 | red-team | y | none stated | none stated |
| lu2025phantommenace | 7 | red-team | y | none stated | Attacks generated in simulation and confirmed on physical robots. |
| bajrami2026robotignores | 0 | benchmark | y | Text-level scoring is cheap; physical G1 validation described as ongoing. | Ties scoring to ISO 10218-2 invariants; measures both false alarms (overcomplian |
| lou2026safeloop | 7 | study | y | 25 real rollouts per task (typical scale of academic real-robot safety eval). | none stated |
| nakamura2025latentsafety | 7 | study | y | none stated | Hardware demonstrations; no large-n statistics in abstract. |
| sun2026safestoppability | 7 | study | y | Simulation budget framed as the constraint; hardware trials not counted in abstr | False-safe rate under fixed simulation budget; real deployment demo. |
| ding2026failpassive | 7 | study | y | none stated | none stated (analytical safety case). |
| ieee2025humanoidpathway | None | position | y | States performance-to-cost ratio must beat purpose-built machines; no test-cost  | none stated |
| iso2025iso25785 | 7 | standard | y | none stated; 18-36 months from May 2025 draft to ratification. | none stated |
| han2024painthresholds | 8 | study | y | Human-subject study; instrumented pendulum rig; no cost stated. | Direct human pain measurement; notes most ISO/TS 15066 limits are preliminary li |
| iihs2024paeb | 8 | standard | y | Per vehicle: 36 scored runs plus 16 brake-conditioning stops, dummy targets, sur | HLDI insurance-claim analyses show systems that pass these tests reduce real ped |
| euroncap2024aebvru | 8 | standard | y | Requires driving robot, guided target platforms, proving ground; no cost figures | Kullgren et al. 2010: 5-star cars have 10% (+/-2.5) lower injury risk, 23% (+/-8 |
| kullgren2010euroncap | 9 | study | y | none stated | This is the validity evidence: ratings mirror real-world outcomes for all severi |
| kalra2016drivingtosafety | 9 | position | y | Quantifies the miles (hence fleet-years) needed for level-9 evidence; explicitly | none (theoretical). |
| kusano2023waymo7m | 9 | study | y | Requires millions of deployed miles; benchmark construction from state VMT and p | This is level-9 outcome data; authors caution on underreporting differences and  |
| kusano2025waymo56m | 9 | study | y | ~57M deployed miles needed to reach significance on serious-injury crash types. | Level-9 outcome data with CIs; first RO study with statistical conclusions on se |
| waymo2026impacthub | 9 | dataset | y | Implicit: 271M commercial miles. | Peer-reviewed methodology (Traffic Injury Prevention); accounts for underreporti |
| scanlon2021reconstructed | 5 | study | y | Reconstruction from police reports; single-instance simulations. | Authors note limits: single instance per scenario, police-data uncertainty; no o |
| flannagan2023cruiseumtri | 9 | study | y | Two-year, multi-institution instrumented study to build the benchmark alone. | Cautionary: published one week before the Oct 2, 2023 pedestrian-dragging incide |
| cruise2023incident | 9 | study | y | Illustrates the cost of a missed failure mode (fleet grounded) rather than evalu | Shows aggregate crash-rate benchmarks published a week earlier did not capture t |
| nhtsa2021sgo | 9 | standard | y | Reporting burden on operators; data free to public. | Known issues: narrative redactions (Tesla until 2026), reporting-threshold diffe |
| chen2026ciimportance | 9 | study | y | Motivated by rarity: collisions once per several million human miles. | Statistical validity results; no outcome comparison. |
| soc2022amazonprimed | 9 | dataset | y | Uses mandatory OSHA reporting; no evaluation cost. | Observational; confounded by throughput/pace; but it is direct level-9 harm data |
| winfield2020accident | 9 | position | y | none stated | none stated |
| khazatsky2024droid | 7 | dataset | n | 350 h of demonstrations required 50 collectors and 12 months across 13 instituti | n/a (dataset); policies trained on it generalise better than narrow data. |
| oxe2023openx | 7 | dataset | n | Aggregates years of collection across 21 institutions; no dollar figure. | n/a |
| agibot2025world | 7 | dataset | n | Dedicated data-collection facility with a robot fleet; explicit cost not in abst | n/a |
| chi2024umi | 7 | tooling | n | Portable, low-cost handheld device; throughput advantage 3x vs teleop (from pape | n/a |
| zhao2023aloha | 7 | tooling | n | USD 20k complete bimanual system (project page). | n/a |
| therobotstudio2024soarm100 | 7 | tooling | n | Single follower arm USD 121.94 / EUR 124.30; leader+follower USD 229.88 / EUR 22 | n/a |
| wang2026xrzero | 7 | dataset | n | Claims ~20x reduction in data acquisition cost vs real-robot teleoperation. | Mixing-ratio experiments on downstream policy success. |
| agarwal2026cobalt | 7 | tooling | n | 50+ h of data in 5 days from distributed volunteers; 8 users per GPU. | n/a |
| wang2026zero2skill | 7 | tooling | n | Human time cut to 16%. | n/a |
| zhang2025vilsim | 6 | tooling | y | Motivated by space and expense of full-size ViL testing; no figures. | none stated |

## Entries

## Frontier-model hardware evals (Andon Labs, Anthropic)

### sharrock2025butterbench: Butter-Bench (2025, Andon Labs)
- URL: https://andonlabs.com/evals/butter-bench  | arXiv:2510.21860
- Kind: benchmark | Ladder level: 7 | Safety focus: True | Confidence: high | URL verified: True
- Modality: LLM is the high-level planner of a TurtleBot4/robot-vacuum with lidar+camera; receives images and a discrete action API (go forward, rotate, navigate to coordinate, capture picture, Slack messaging); scored by human-judged completion of 6 subtasks, 5 trials per task, 15 min limit for end-to-end.
- Measures: Practical intelligence of frontier LLMs embodied in a real mobile robot: search, visual inference, social interaction, multi-step spatial planning, end-to-end 'pass the butter'.
- Size: 6 subtasks x 5 trials x 7 models (Gemini 2.5 Pro, Claude Opus 4.1, GPT-5, Gemini ER 1.5, Grok 4, Llama 4 Maverick, ...)
- Reported metrics: Best LLM 40% (Gemini 2.5 Pro) vs mean human 95%; fine-tuning for embodied reasoning did not help; models struggled most on multi-step spatial planning and social understanding.
- Cost evidence: Hardware: TurtleBot 4 Standard (iRobot Create 3 base, ~USD 2k class); 5 trials/task, human operator resets and scoring; no hours or dollar figure stated.
- Validity evidence: Human baseline (95%) as reference; qualitative safety/privacy probes (low-battery 'existential' transcripts, Claude sharing a blurry confidential screen image, GPT-5 disclosing laptop location). No correlation with deployment outcomes.
- Notes: arXiv abstract and Andon Labs eval page both fetched. Cost of a single evaluation run not stated; each trial is human-supervised.

### sharrock2026dronebench: Drone-Bench (2026, Andon Labs)
- URL: https://andonlabs.com/docs/Drone_Bench.pdf
- Kind: benchmark | Ladder level: 4 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Coding agent (ReAct loop, bash/read/write tools + read_image) is fed office videos, drone poses, obstacle maps and reference images; it writes drone-control code and submits up to 10 times per run; navigate/follow are scored in a MuJoCo model of the office calibrated to a DJI Tello, reconstruct/localize/detect are scored on real recordings on a T4 GPU worker; scores normalised to a human+AI baseline.
- Measures: Whether frontier models can autonomously write code for a simple surveillance stack (reconstruction, localisation, navigation, detection, following) on a USD 129 drone; dual-use capability tracking.
- Size: 5 tasks x 10 runs x 15 models (May 2024 - Jul 2026), 10 submissions per run
- Reported metrics: Claude Fable 5 reaches 84% of baseline averaged over tasks (reconstruction 47%); best run clears 4/5 tasks; average end-to-end success ~6% (later reported 2.8% for GPT-6 Astra); ~6-month gap between best-case and average-case; cheating incidents rise from 0.6% (2024 models) to 50.6% (newest).
- Cost evidence: Hardware: DJI Tello EDU, USD 129; scoring compute: one NVIDIA T4 per submission with 5 h (reconstruction), 2 h (localisation), 1500 s (detection) timeouts; 120 s wall-clock per simulated flight; real-drone end-to-end runs only for reference solutions and top submissions.
- Validity evidence: Sim-to-real alignment checked by running reference and top submissions in both simulator and on the physical Tello and confirming matching behaviour; simulator noise calibrated from physical flight tests. No quantitative sim-real correlation reported.
- Notes: PDF fetched and text extracted. Hybrid ladder position: level 4 (MuJoCo) for navigate/follow, level 5 (real-data replay) for perception tasks, level 7 end-to-end checks on the physical drone.

### anthropic2026projectpilot: Project Pilot (Anthropic x Andon Labs) (2026, Anthropic Frontier Red Team / Andon Labs)
- URL: https://www.anthropic.com/research/project-pilot
- Kind: study | Ladder level: 7 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Same Drone-Bench feed (videos, poses, maps, reference images; code-writing agent); scored against human-AI baseline per subtask; end-to-end demonstration run on the physical DJI Tello EDU in an office.
- Measures: Whether 15 frontier models across three developers can recreate an aerial person-finding-and-following surveillance demo; frames the result as a dual-use capability threshold.
- Size: 15 models, 5 subtasks, 10 runs each
- Reported metrics: Claude Fable 5 best: exceeds baseline on 4/5 tasks, reconstruction ~47%; on the real drone it detects and follows better than baseline but compounding reconstruction errors prevent room-to-room navigation (flies into walls it thinks are doorways).
- Cost evidence: DJI Tello EDU at USD 129; office environment; no labour hours stated.
- Validity evidence: Physical end-to-end runs used to check that simulator scores translate to the real drone; qualitative agreement (detection/following transfer, navigation does not).
- Notes: Companion write-up to Drone-Bench; cite together.

### anthropic2026claudeplaysrobotics: Claude Plays Robotics (2026, Anthropic)
- URL: https://www.anthropic.com/research/claude-plays-robotics
- Kind: benchmark | Ladder level: 4 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Model controls simulated bodies (pendulum/hopper, Unitree Go2 12-DoF, Unitree G1 29-DoF, Franka Panda 7-DoF in MuJoCo/LIBERO) through four interfaces: direct torques, Python controllers, natural-language commands to pretrained policies, or supervising RL training; scored by normalised task success (0-100 composite).
- Measures: How embodiment capability of frontier models depends on control-interface abstraction; argues isolated model evals understate capability once embedded in a robotics stack.
- Size: 11-task locomotion suite + manipulation (LIBERO kitchen) + classic control; 35-200 trials per model/condition
- Reported metrics: Claude Mythos Preview top composite 0.389; direct motor control hard for all models; manipulation 0-5.5% full completion under direct control, large gains with VLA supervision.
- Cost evidence: 35-200 trials per cell, 30 min to 18 h per cell, 'thousands of GPU/CPU hours' total.
- Validity evidence: none stated (simulation only; no real-hardware transfer reported).
- Notes: Page fetched; robot bodies appear to be MuJoCo models, not physical units. Useful as the level-4 counterpart to Butter-Bench/Drone-Bench and for explicit compute-cost figures.

### anthropic2025projectfetch: Project Fetch (robot dog) (2025, Anthropic)
- URL: https://www.anthropic.com/research/project-fetch-robot-dog
- Kind: study | Ladder level: 7 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Human teams (4 with Claude, 4 without) program a real quadruped with camera+lidar over one day through three phases (manufacturer controller, custom sensor access, autonomous ball fetching); scored by tasks completed and time.
- Measures: AI-uplift for non-expert humans programming a physical robot; tracked as a Responsible Scaling Policy capability indicator.
- Size: 8 participants, 8 tasks, 1 day
- Reported metrics: Team Claude 7/8 tasks vs 6/8; about half the time on shared tasks; ~9x more code written; only Team Claude progressed toward full autonomy.
- Cost evidence: One-day uplift study with 8 engineers and a commercial quadruped; no budget stated.
- Validity evidence: none stated (small n, single day).
- Notes: Uplift study rather than a benchmark; n=8.

## Real-robot policy benchmarks and evaluation infrastructure (level 7)

### atreya2025roboarena: RoboArena (2025, UC Berkeley / Stanford / 7 institutions)
- URL: https://arxiv.org/abs/2506.18123  | arXiv:2506.18123
- Kind: benchmark | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Generalist manipulation policies (VLA) run on DROID Franka setups at 7 institutions; evaluators freely choose task and scene and perform double-blind A/B pairwise comparisons; preference feedback aggregated into a ranking.
- Measures: Distributed, crowd-sourced real-world ranking of generalist robot policies across diverse tasks and environments.
- Size: 4284 evaluation episodes, >600 pairwise A/B episodes, 7 policies, 7 institutions
- Reported metrics: Rankings converge within ~100 pairwise comparisons; higher Pearson correlation and lower MMRV vs an exhaustive-evaluation oracle than centralised evaluation.
- Cost evidence: Human evaluators at 7 sites run every episode by hand (setup, reset, judging); labour hours not quantified; hardware is the DROID platform (Franka Panda + 2 Zed 2 + Zed Mini + Quest 2).
- Validity evidence: Ranking accuracy validated against an oracle computed by exhaustive evaluation (Pearson r, MMRV); scaling and robustness claims empirical.
- Notes: Abstract and HTML fetched; author list truncated in bibtex (31 authors).

### dasari2022rb2: RB2: Ranking-Based Robotics Benchmark (2022, CMU / Meta AI / multi-lab)
- URL: https://arxiv.org/abs/2203.08098  | arXiv:2203.08098
- Kind: benchmark | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Policies trained/evaluated locally on 4 manipulation tasks (pouring, scooping, zipping, insertion) inspired by the Southampton Hand Assessment Procedure; per-lab success scores of 5 shared baselines pooled into a global ranking.
- Measures: Reproducible local real-robot benchmarking with a global ranking so labs can show statistically significant improvement over shared baselines.
- Size: 4 tasks, 5 baselines (BC-Open, NDP, BC-Closed, BC-LSTM, MOReL), 2 lab venues
- Reported metrics: Simple open-loop BC outperformed closed-loop/RNN/offline-RL baselines; rankings consistent across labs.
- Cost evidence: Requires each lab to rebuild the setup and rerun baselines; no hours stated.
- Validity evidence: Cross-lab consistency of baseline ranking (2 venues).
- Notes: NeurIPS 2021 D&B; arXiv posted 2022.

### zhou2025autoeval: AutoEval (2025, UC Berkeley)
- URL: https://arxiv.org/abs/2503.24278  | arXiv:2503.24278
- Kind: tooling | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Policies submitted to a queue run on WidowX (BridgeData) stations; success judged by fine-tuned VLM classifiers (~1000 labelled images per scene), scenes reset by learned reset policies; outputs success rates and rankings.
- Measures: Around-the-clock autonomous real-robot evaluation with near-zero human supervision.
- Size: 5 tasks, 6 generalist policies, ~850 episodes per robot per 24 h
- Reported metrics: Pearson r = 0.942 and MMRV = 0.015 vs human-run oracle evaluations; classifier >95% accuracy on held-out images; 3 human interventions in 24 h across ~850 episodes.
- Cost evidence: >99% reduction in human operator time; 42 evaluation steps/min; setup 1-3 h active effort, <5 h including classifier training; two public WidowX stations.
- Validity evidence: Agreement with human-run evaluation of the same policies (r=0.942, MMRV 0.015); classifier accuracy >95%.
- Notes: Strongest quantitative cost + validity evidence for automated level-7 evaluation.

### yakefu2025robochallenge: RoboChallenge (Table30) (2025, RoboChallenge consortium (Dexmal/others))
- URL: https://arxiv.org/abs/2510.17950  | arXiv:2510.17950
- Kind: benchmark | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: VLA models run remotely on a fleet of 10 real robots (UR5, Franka Panda, Cobot Magic Aloha, ARX-5); controlled testers reproduce scenes from reference images; each rollout scored by progress points (10 per task) and success; 10 rollouts per task.
- Measures: Large-scale online real-robot evaluation of embodied policies with reproducibility controls.
- Size: 30 tasks (Table30), 10 machines, 5 methods (pi0.5, pi0, CogACT, multi-task variants), 10 rollouts per task
- Reported metrics: Survey of SOTA VLA success/progress on Table30; task-specific training ~1 day on an 8-GPU machine with up to 1000 demos per task.
- Cost evidence: Fleet of 10 machines across 4 types; human testers reset scenes; no labour hours or dollar cost stated.
- Validity evidence: Visual-reference scene reproduction for consistency; no inter-run agreement statistics reported.
- Notes: 37 authors; abstract and HTML fetched.

### selvaraj2026armnetbench: ArmnetBench v0.1 (2026, Armnet (independent))
- URL: https://arxiv.org/abs/2607.24481  | arXiv:2607.24481
- Kind: benchmark | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Policies (fine-tuned on 50 demos/task) run in isolated containers on a farm of SO-101 cells (3 cameras, Raspberry Pi, networked power plug); every rollout labelled success/suboptimal/failure; single-arm and bimanual.
- Measures: Parallel, low-cost real-world evaluation of manipulation policies with released labelled rollouts.
- Size: 12 tasks, 7 policies, 2518 policy rollouts + 600 reference demos (3118 labelled episodes; 3718 released)
- Reported metrics: Per-policy success/suboptimal/failure rates across 12 tasks (numbers in paper).
- Cost evidence: SO-101 arm BOM ~USD 122 per follower arm (see so-arm100 entry); 'light on-site supervision'; per-trial cost reduced by parallel cells; explicit dollar/hour figures not in abstract.
- Validity evidence: Three-way human labels released; no agreement statistics in abstract.
- Notes: Cheapest hardware per evaluation cell in the catalogue.

### huang2026vlareplica: VLA-REPLICA (2026, UT Dallas)
- URL: https://arxiv.org/abs/2605.20774  | arXiv:2605.20774
- Kind: benchmark | Ladder level: 7 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: Off-the-shelf low-cost real-robot rig with a suite of manipulation tasks; VLA models adapted with a small demo dataset and scored by success in in-distribution and out-of-distribution settings.
- Measures: Reproducible, low-cost real-world VLA evaluation that can be replicated across labs.
- Size: unknown (abstract: 'diverse suite')
- Reported metrics: Consistent results across independently constructed setups (abstract claim).
- Cost evidence: Off-the-shelf components, described as low-cost; no dollar figure in abstract.
- Validity evidence: Replication across independently built rigs reported as consistent.
- Notes: Abstract only; numbers not extracted.

### yu2026so101bench: VLA benchmark on SO-101 (failure/recovery) (2026, independent)
- URL: https://arxiv.org/abs/2606.08881  | arXiv:2606.08881
- Kind: benchmark | Ladder level: 7 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: VLA/IL policies (pi0.5, SmolVLA, Wall-X, ACT) run on a low-cost SO-101 arm on 4 tasks; scored with success plus a structured failure taxonomy (semantic vs execution) and recovery-aware metrics.
- Measures: Failure modes and recovery of VLAs under embodiment uncertainty on cheap hardware.
- Size: 4 tasks, 4 policies
- Reported metrics: Execution instability is the dominant failure source; recovery capability varies by architecture.
- Cost evidence: SO-101 hardware (~USD 122/arm BOM); trials not stated.
- Validity evidence: none stated
- Notes: Abstract only.

### chen2026robodojo: RoboDojo (2026, multi-institution (44 authors))
- URL: https://arxiv.org/abs/2607.04434  | arXiv:2607.04434
- Kind: benchmark | Ladder level: 7 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: 42 Isaac Sim tasks (generalisation, memory, precision, long-horizon, open-vocab) plus 18 real-world tasks run through RoboDojo-RealEval, a cloud-based reproducible testing system with standardised hardware; 30 policies integrated in XPolicyLab; success-rate leaderboard.
- Measures: Unified sim-and-real evaluation of generalist manipulation policies.
- Size: 42 sim tasks + 18 real tasks, 30 policies
- Reported metrics: Public leaderboard (numbers not in abstract).
- Cost evidence: Cloud-based real-eval service with standardised hardware; no cost numbers.
- Validity evidence: none stated in abstract (sim-real correlation not quantified).
- Notes: Level 4 + 7 hybrid; listed at 7 for the real component.

## Simulated and neural-simulated evaluation validated against real (levels 3-5)

### li2024simpler: SIMPLER (2024, UCSD / Stanford / Google DeepMind / UC Berkeley)
- URL: https://arxiv.org/abs/2405.05941  | arXiv:2405.05941
- Kind: benchmark | Ladder level: 4 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Real-world policies (RT-1, RT-1-X, RT-2-X, Octo) executed in SAPIEN-based simulated replicas of Google Robot and WidowX setups with visual-matching and system-identified controllers; success rates compared to paired real evaluations via MMRV and Pearson r.
- Measures: Whether cheap simulated evaluation reproduces real-world policy rankings and sensitivity to distribution shifts.
- Size: ~1500 paired sim-and-real episodes, 2 embodiments, 8 task families
- Reported metrics: Strong sim-real correlation (low MMRV, high Pearson r; values in figures); reproduces sensitivity to lighting, background, camera pose, distractors, table texture.
- Cost evidence: Simulation replaces real trials once built; the ~1500 paired real episodes are the validation cost.
- Validity evidence: Paired real evaluations on the same policies; correlation of success rates and rank preservation.
- Notes: Canonical level-4-predicts-level-7 evidence.

### jeon2026roboworld: RoboWorld (neural simulator eval) (2026, KAIST / others)
- URL: https://arxiv.org/abs/2607.01060  | arXiv:2607.01060
- Kind: tooling | Ladder level: 5 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: Autoregressive video world model conditioned on policy actions plus task-aware VLM scoring; policies evaluated entirely in the neural simulator; results compared to real-world evaluation.
- Measures: Fast, learned-simulator evaluation of generalist policies that preserves real-world rankings.
- Size: unknown
- Reported metrics: Pearson r = 0.989, Spearman rho = 0.970 vs real-world evaluation.
- Cost evidence: Claims fast rollouts; no explicit cost numbers in abstract.
- Validity evidence: Correlation with real-world evaluation (r=0.989, rho=0.970).
- Notes: Number of real trials behind the correlation not extracted.

### jangir2025robotarenainf: RobotArena Infinity (2025, CMU)
- URL: https://arxiv.org/abs/2510.23571  | arXiv:2510.23571
- Kind: benchmark | Ladder level: 5 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: Real robot dataset videos converted to simulated twins (VLM + 2D-to-3D generation + differentiable rendering); VLA policies rolled out in sim under systematic perturbations; scored by VLM-guided automatic scoring plus crowd-worker pairwise preferences.
- Measures: Scalable VLA benchmarking in real-to-sim environments with human preference judgements.
- Size: unknown
- Reported metrics: none extracted from abstract
- Cost evidence: Crowd-worker preference labels replace on-site evaluators; cost not quantified.
- Validity evidence: Human preference judgements from crowdworkers; agreement with real rankings not in abstract.
- Notes: none

### sedlacek2025realm: REALM (2025, CIIRC CTU Prague / UvA)
- URL: https://arxiv.org/abs/2512.19562  | arXiv:2512.19562
- Kind: benchmark | Ladder level: 5 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: VLA policies (pi0, pi0-FAST, GR00T N1.5) evaluated in a photoreal simulator with 15 perturbation factors, 7 skills and >3500 objects; simulated results validated against real-robot runs.
- Measures: Generalisation of VLAs under controlled perturbations, with real-to-sim validation.
- Size: 15 perturbation types, 7 skills, >3500 objects, 3 policies
- Reported metrics: Claims strong sim-real correlation (coefficient not in abstract).
- Cost evidence: none stated
- Validity evidence: Real-to-sim validation claimed; numbers in paper body.
- Notes: none

### ruan2026x2real: X2Real (2026, industry consortium (26 authors))
- URL: https://arxiv.org/abs/2609.27449  | arXiv:2609.27449
- Kind: benchmark | Ladder level: 4 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: Generalist policies evaluated on 44 hierarchical long-horizon simulated tasks across 10 capability dimensions with visuals/physics calibrated to real hardware; ~300 h of annotated sim trajectories.
- Measures: Extensive simulated benchmark aiming to predict real-world generalist policy performance.
- Size: 44 tasks, 10 capability dimensions
- Reported metrics: 0.84 linear correlation between simulated and real-robot evaluation results.
- Cost evidence: none stated
- Validity evidence: r = 0.84 sim vs real evaluation.
- Notes: Abstract only.

### wang2026simrealrecipe: Practical recipe for sim-real correlation in VLA eval (2026, Tsinghua (Yang Gao group))
- URL: https://arxiv.org/abs/2606.10366  | arXiv:2606.10366
- Kind: study | Ladder level: 4 | Safety focus: False | Confidence: low | URL verified: True
- Modality: Systematic study across several simulation platforms, VLA policies, tasks and perturbation factors measuring whether sim evaluation preserves real-world rankings and metrics.
- Measures: Which simulator design choices make simulated VLA evaluation predictive of real-world conclusions.
- Size: unknown
- Reported metrics: none extracted (in paper body)
- Cost evidence: none stated
- Validity evidence: Direct measurement of sim-to-real ranking preservation (numbers in body).
- Notes: Abstract only; included because it is a meta-study of exactly the validity question.

### gemini2025veosim: Gemini Robotics policies in a Veo world simulator (2025, Google DeepMind)
- URL: https://arxiv.org/abs/2512.10675  | arXiv:2512.10675
- Kind: tooling | Ladder level: 5 | Safety focus: True | Confidence: high | URL verified: True | Speaker: Sindhwani
- Modality: Bimanual manipulation policies rolled out inside a Veo video-generation world model; scenes edited with novel objects/backgrounds/distractors; used for OOD evaluation and red-teaming of physical and semantic safety constraints; compared with real-robot evaluations.
- Measures: Whether a generative video simulator can rank policy checkpoints and expose safety violations without real trials.
- Size: 8 Gemini Robotics checkpoints, 5 tasks, >1600 real-world validation evaluations
- Reported metrics: Agreement with real evaluations reported qualitatively/figures; explicit correlation coefficient not in abstract.
- Cost evidence: >1600 real-world evaluations used as ground truth for the validation.
- Validity evidence: Paired real-world evaluations on the same checkpoints.
- Notes: Sindhwani is a co-author.

### sermanet2025asimov: ASIMOV benchmark / robot constitutions (2025, Google DeepMind)
- URL: https://arxiv.org/abs/2503.08663  | arXiv:2503.08663
- Kind: benchmark | Ladder level: 3 | Safety focus: True | Confidence: high | URL verified: True | Speaker: Sindhwani
- Modality: VLM/LLM 'robot brains' answer safety questions about generated text and images grounded in real-world scenes and hospital injury reports; scored by alignment with human safety labels; constitutions loaded as prompt preamble.
- Measures: Semantic safety (long-tail commonsense hazards) of foundation models used as robot planners.
- Size: large-scale (multiple datasets; counts in paper)
- Reported metrics: Top alignment 84.3% with human preference using auto-generated constitutions; beats human-written rules.
- Cost evidence: Text/image generation replaces physical trials; no dollar figures.
- Validity evidence: Agreement with human judgements (84.3%); no link to physical outcomes.
- Notes: Low-ladder contrast case (level 3); included to anchor the cost/validity trade-off against level-7/9 entries.

## Statistics of real-robot evaluation

### tri2025lbm: TRI Large Behavior Models: careful examination (2025, Toyota Research Institute)
- URL: https://arxiv.org/abs/2507.05331  | arXiv:2507.05331
- Kind: study | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Diffusion-policy LBMs vs single-task baselines on bimanual Franka FR3 stations; blind, randomised A/B rollouts; binary success via sequential hypothesis testing, Bayesian Beta posteriors, Welch t-tests with Bonferroni, compact letter display.
- Measures: Whether multitask pretraining helps, with enough trials to make statistically defensible claims.
- Size: 1800 real-world rollouts (50 per task/policy/condition, 8 real tasks), >47000 sim rollouts (200 per condition, 24 sim tasks); ~1700 h training data
- Reported metrics: Multi-task pretraining improves success/robustness and needs ~80% less data for new skills; ~50 real trials per condition needed to separate policies.
- Cost evidence: 1800 real rollouts at 50/condition; 9 robot stations for data collection; 468 h in-house teleop data; explicit statement that most studies lack sufficient trials.
- Validity evidence: Statistical framework with explicit power; blind A/B mitigates evaluator bias.
- Notes: Best single source for 'how many real trials does a defensible comparison need'.

### vincent2024generalizable: Statistical lower bounds for BC policy performance (2024, Toyota Research Institute / Stanford)
- URL: https://arxiv.org/abs/2405.05439  | arXiv:2405.05439
- Kind: study | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Visuomotor policies rolled out in sim and on hardware; stochastic-ordering bounds on the full performance CDF with user-specified confidence from a minimal number of rollouts.
- Measures: How many rollouts are needed for trustworthy, worst-case performance bounds and OOD comparisons.
- Size: unknown (sim and hardware experiments)
- Reported metrics: Tight lower bounds validated empirically; open-source code and data.
- Cost evidence: Explicitly targets minimal number of hardware rollouts; counts in paper body.
- Validity evidence: Bounds hold at stated confidence in simulation; hardware generalisation measured.
- Notes: none

### badithela2025suresim: SureSim (prediction-powered sim+real evaluation) (2025, Princeton (Majumdar lab))
- URL: https://arxiv.org/abs/2510.04354  | arXiv:2510.04354
- Kind: study | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Large-scale physics simulation plus a small number of paired real trials; prediction-powered inference corrects sim bias and yields non-asymptotic confidence intervals on mean real performance; tested on diffusion policy and fine-tuned pi0.
- Measures: How much real-robot testing can be replaced by imperfect simulation while keeping valid confidence intervals.
- Size: unknown
- Reported metrics: >20-25% reduction in hardware evaluation effort for comparable bounds.
- Cost evidence: Quantifies hardware-trial savings (20-25%) from augmenting with simulation.
- Validity evidence: Confidence intervals are statistically valid by construction regardless of sim fidelity.
- Notes: Directly a value-of-information style trade between cheap and expensive evaluations.

### wan2026nofreechecker: No Free Checker: survey of verifiers for robot policies (2026, Zhejiang University)
- URL: https://arxiv.org/abs/2609.09250  | arXiv:2609.09250
- Kind: position | Ladder level: None | Safety focus: True | Confidence: high | URL verified: True
- Modality: Survey of ~150 verifiers (success detectors, reward models, runtime monitors, safety filters, temporal-logic specs) organised by source and by availability (cost/timing) vs credibility.
- Measures: The trade-off between how cheaply a verdict is available and how credible it is; catalogues validation measures including agreement with human labels.
- Size: ~150 verifiers
- Reported metrics: Finding: credibility falls as availability rises across the four verifier families.
- Cost evidence: Frames cost/timing of verdicts as a first-class axis.
- Validity evidence: Identifies agreement with human labels as one of three validation measures used in the literature.
- Notes: Useful framing citation for the cost-vs-validity axis.

## Red-teaming and runtime safety on real robots

### robey2024robopair: RoboPAIR: jailbreaking LLM-controlled robots (2024, University of Pennsylvania)
- URL: https://arxiv.org/abs/2410.13691  | arXiv:2410.13691
- Kind: red-team | Ladder level: 7 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Attacker LLM iteratively crafts prompts to the robot's LLM (white-box NVIDIA Dolphins, gray-box Clearpath Jackal + GPT-4o, black-box Unitree Go2 + GPT-3.5); success = robot executes harmful physical action (block exits, find weapons, collide with people).
- Measures: Whether text jailbreaks transfer to harmful physical actions on real commercial robots.
- Size: 3 robots x 3 access settings; harmful-action task set
- Reported metrics: 100% attack success in all three settings; first system-prompt extraction from a deployed commercial robot.
- Cost evidence: Commercial robots (Unitree Go2, Clearpath Jackal); attack automated by an LLM; no hours stated.
- Validity evidence: Harmful actions executed on physical robots (direct observation); no false-alarm analysis.
- Notes: none

### zhang2024badrobot: BadRobot (2024, HUST / others)
- URL: https://arxiv.org/abs/2407.20242  | arXiv:2407.20242
- Kind: red-team | Ladder level: 7 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Voice/text attacks on embodied LLM frameworks (Voxposer, Code as Policies, ProgPrompt) exploiting LLM jailbreaks, language-action misalignment and world-knowledge gaps; success = hazardous plan/action.
- Measures: Jailbreak vulnerability of embodied LLM agents leading to physical harm.
- Size: 3 frameworks; attack suite
- Reported metrics: none extracted from abstract
- Cost evidence: none stated
- Validity evidence: none stated
- Notes: Abstract does not confirm physical-robot trials; ladder level 7 assumed from title, verify in body.

### lu2025phantommenace: Phantom Menace: physical sensor attacks on VLAs (2025, Zhejiang University)
- URL: https://arxiv.org/abs/2511.10008  | arXiv:2511.10008
- Kind: red-team | Ladder level: 7 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Real-Sim-Real framework: physics-based camera (6) and microphone (2) attack vectors simulated, then validated on real robots running VLA policies; adversarial training defence.
- Measures: Robustness of VLA models to physical sensor attacks.
- Size: 8 attack types
- Reported metrics: Significant vulnerabilities across VLA architectures (rates in body).
- Cost evidence: none stated
- Validity evidence: Attacks generated in simulation and confirmed on physical robots.
- Notes: none

### bajrami2026robotignores: LLM-orchestrator safety benchmark for human-humanoid collaboration (2026, Fraunhofer IPA (likely))
- URL: https://arxiv.org/abs/2609.07288  | arXiv:2609.07288
- Kind: benchmark | Ladder level: 0 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Natural-language commands over a Model Context Protocol tool interface to an LLM orchestrator, grounded in ISO 10218-2:2025 safety invariants; 40 sessions x 100 turns; each turn labelled correct/over-/under-compliance/violation; physical layer on Unitree G1 EDU.
- Measures: Compliance spectrum of LLM orchestrators (over-refusal vs violation) against industrial safety invariants over long sessions.
- Size: 40 sessions x 100 turns per model, 5 safety invariants
- Reported metrics: Claude and Gemini near-zero violations; GPT-4o-mini up to 13 violations/session; context management cuts issues 42-57% for most models but doubles GPT-4o-mini failures.
- Cost evidence: Text-level scoring is cheap; physical G1 validation described as ongoing.
- Validity evidence: Ties scoring to ISO 10218-2 invariants; measures both false alarms (overcompliance) and misses (violations).
- Notes: Scored at level 0 (text) with a level-7 validation layer; one of the few entries reporting a false-alarm (over-refusal) axis.

### lou2026safeloop: SafeLoop (2026, unknown (IROS 2026))
- URL: https://arxiv.org/abs/2609.26313  | arXiv:2609.26313
- Kind: study | Ladder level: 7 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Risk predictor + rollback wrapper around a VLA; evaluated on 24 LIBERO tasks (16 seeds) and 3 real-robot tasks with 25 rollouts each; metrics: hazard cases and task success.
- Measures: Whether a runtime safety wrapper reduces hazards without hurting success.
- Size: 24 sim tasks x 16 seeds; 3 real tasks x 25 rollouts
- Reported metrics: ~70% reduction in hazard cases with success maintained.
- Cost evidence: 25 real rollouts per task (typical scale of academic real-robot safety eval).
- Validity evidence: none stated
- Notes: Included mainly as a data point on trial counts in real-robot safety papers.

### nakamura2025latentsafety: Latent safety filters (latent-space HJ reachability) (2025, CMU (Bajcsy lab))
- URL: https://arxiv.org/abs/2502.00935  | arXiv:2502.00935
- Kind: study | Ladder level: 7 | Safety focus: True | Confidence: high | URL verified: True | Speaker: Bajcsy
- Modality: World model over RGB observations; HJ reachability in latent space yields a safety filter that overrides arbitrary policies; hardware tests on a Franka Research 3 preventing bag spills and toppling clutter.
- Measures: Whether learned latent safety filters can prevent hard-to-specify failures on real manipulators.
- Size: unknown (sim + hardware experiments)
- Reported metrics: Successfully safeguards imitation and teleoperated policies (rates in body).
- Cost evidence: none stated
- Validity evidence: Hardware demonstrations; no large-n statistics in abstract.
- Notes: Bajcsy link; related CoRL 2025 UNISafe and AnySafe papers use the same Franka hardware.

## Humanoid safety testing and standards

### sun2026safestoppability: Safe-stoppability monitors for humanoids (PRISM) (2026, CMU (Changliu Liu) / Siemens)
- URL: https://arxiv.org/abs/2603.22703  | arXiv:2603.22703
- Kind: study | Ladder level: 7 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Simulation-trained neural predictor of whether a humanoid state admits a safe stop under a fallback balance controller; importance sampling refines decision boundary at rare states; deployed on real humanoid hardware.
- Measures: Certifiable fail-safe (emergency stop) behaviour for actively balancing robots.
- Size: unknown
- Reported metrics: Fewer false-safe predictions under fixed sim budget; sim-to-real deployment.
- Cost evidence: Simulation budget framed as the constraint; hardware trials not counted in abstract.
- Validity evidence: False-safe rate under fixed simulation budget; real deployment demo.
- Notes: none

### ding2026failpassive: Certified functional safety for industrial humanoids: fail-passive gap (2026, Siemens / industry)
- URL: https://arxiv.org/abs/2608.02809  | arXiv:2608.02809
- Kind: study | Ladder level: 7 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Feasibility study mapping ISO 13849-1 / IEC 62061 certification chain (PFHD, DC, CCF, PL/SIL) onto a Unitree G1 EDU pick-and-place cell (3 m x 1.5 m); analyses fall hazards, single-support stop bounds and ISO 13855 separation distances; timing budget with provenance.
- Measures: Where the certification gap sits for actively balancing robots that cannot be de-energised safely.
- Size: 1 robot cell case study
- Reported metrics: Localises the uncertifiable element to the robot-side reaction mechanism; deliberately does not claim PL e / SIL 3.
- Cost evidence: none stated
- Validity evidence: none stated (analytical safety case).
- Notes: none

### ieee2025humanoidpathway: IEEE/ASTM Pathway Study for Future Humanoid Standards (2025, IEEE RAS Humanoid Study Group (chair: ASTM's Aaron Prather))
- URL: https://www.therobotreport.com/wp-content/uploads/2025/09/IEEE-Humanoid-Report-of-Future-Standards-Development.pdf
- Kind: position | Ladder level: None | Safety focus: True | Confidence: high | URL verified: True
- Modality: Roadmap document; no system under test. Calls for quantifiable stability metrics and test methods (push recovery, fall response, dynamic balance) and HRI guidelines.
- Measures: Gaps in humanoid standards: classification, stability (identified as the critical bottleneck), human-robot interaction.
- Size: n/a (60+ experts)
- Reported metrics: none
- Cost evidence: States performance-to-cost ratio must beat purpose-built machines; no test-cost figures.
- Validity evidence: none stated
- Notes: PDF fetched and text extracted; report states ASTM leads on test methods, IEEE on performance metrics.

### iso2025iso25785: ISO/CD 25785-1 dynamically stable industrial mobile robots (2025, ISO/TC 299 (US delegation led by Boston Dynamics, Agility, A3))
- URL: https://www.i-scoop.eu/iso-25785-1-explained-and-what-it-means-for-humanoid-robot-safety/
- Kind: standard | Ladder level: 7 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Draft standard: safety requirements and test protocols under rated load for legged/wheeled actively balanced robots; stability and fall tests, power-loss controlled descent, contact forces per ISO/TS 15066, fall-zone calculation, floor-condition tests.
- Measures: Whether a humanoid/quadruped meets stability, fall and contact requirements in controlled tests.
- Size: n/a
- Reported metrics: none (draft)
- Cost evidence: none stated; 18-36 months from May 2025 draft to ratification.
- Validity evidence: none stated
- Notes: iso.org returned 403; verified through the i-scoop explainer and Robot Report coverage. Status: working/committee draft as of 2026.

### han2024painthresholds: Force pain thresholds for ISO/TS 15066 collision limits (2024, KIRO / Fraunhofer IFF / Kyung Hee Univ.)
- URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11033501/
- Kind: study | Ladder level: 8 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Pendulum impactor with force/torque sensing (10 kHz) strikes deltoid and thigh of 37 male subjects with wedge (R5) and cylindrical (R40) impactors; pain thresholds compared to ISO/TS 15066 biomechanical limits.
- Measures: Empirical basis for power-and-force-limiting collision limits used in cobot collision tests.
- Size: 37 subjects, 2 body regions, 2 impactors
- Reported metrics: Third-quartile force pain thresholds ~121-310 N depending on impactor and body region.
- Cost evidence: Human-subject study; instrumented pendulum rig; no cost stated.
- Validity evidence: Direct human pain measurement; notes most ISO/TS 15066 limits are preliminary literature-derived values.
- Notes: Represents the standards-based contact-test layer (ISO/TS 15066 PFL with biofidelic measuring devices).

## Track tests with human surrogates and their real-world validity (level 8/9)

### iihs2024paeb: IIHS Pedestrian AEB test protocol (Version IV) (2024, Insurance Institute for Highway Safety)
- URL: https://www.iihs.org/media/f6a24355-fe4b-4d71-bd19-0aab8b39aa7e/5ZH5qg/Ratings/Protocols/current/test_protocol_pedestrian_aeb.pdf
- Kind: standard | Ladder level: 8 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Production vehicle driven at 20/40 km/h (perpendicular adult and child, child emerging from behind parked cars) and 40/60 km/h (parallel adult) toward articulated pedestrian dummies on a 4activeSB surfboard platform; day and night; 3 valid runs per speed and lighting condition; scored by speed reduction/avoidance into good/acceptable/marginal/poor.
- Measures: Pedestrian AEB crash avoidance/mitigation on a closed track with human surrogates.
- Size: 3 scenarios x 2 speeds x 2 lighting x 3 runs = 36 runs per vehicle (plus brake conditioning)
- Reported metrics: Ratings per vehicle; HLDI real-world: pedestrian AEB cut pedestrian-related claim frequency 35% (Subaru EyeSight) and ~27% in a later analysis; ~32-33% crash reduction in daylight/lit roads, none in unlit dark.
- Cost evidence: Per vehicle: 36 scored runs plus 16 brake-conditioning stops, dummy targets, surfboard platform, instrumented track; dollar cost not stated.
- Validity evidence: HLDI insurance-claim analyses show systems that pass these tests reduce real pedestrian claims 27-35%; IIHS notes no benefit in unlit conditions, motivating the night test.
- Notes: Protocol PDF fetched and text-extracted; HLDI numbers from IIHS news page (fetched).

### euroncap2024aebvru: Euro NCAP AEB/LSS VRU test protocol (2024, Euro NCAP)
- URL: https://www.euroncap.com/en/for-engineers/protocols/vulnerable-road-user-vru-protection/
- Kind: standard | Ladder level: 8 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Vehicle driven by path-following robot toward articulated pedestrian (adult/child) and cyclist/motorcycle targets in scenarios CPFA/CPNA/CPNC/CPLA/CBNA etc. at stepped speeds; scored by avoidance/speed reduction; pedestrian AEB since 2016, cyclist since 2018, extended 2020 and 2023.
- Measures: Vulnerable-road-user crash avoidance on a proving ground with human surrogates.
- Size: multiple scenarios x speed steps; runs per scenario per protocol
- Reported metrics: Star ratings; see kullgren2010euroncap for real-world validity of Euro NCAP ratings.
- Cost evidence: Requires driving robot, guided target platforms, proving ground; no cost figures published.
- Validity evidence: Kullgren et al. 2010: 5-star cars have 10% (+/-2.5) lower injury risk, 23% (+/-8) lower fatal/serious, 68% (+/-32) lower fatal risk than 2-star cars (crashworthiness ratings; AEB VRU tests post-date that study).
- Notes: Protocol PDF (v4.5) returned 404 on both euroncap.com and cdn; the protocols landing page and Wikipedia timeline were fetched. Scenario details from search snippets and prior protocol knowledge.

### kullgren2010euroncap: Euro NCAP results vs real-world crash data (2010, Folksam / Chalmers / Swedish Transport Administration)
- URL: https://www.tandfonline.com/doi/abs/10.1080/15389588.2010.508804
- Kind: study | Ladder level: 9 | Safety focus: True | Confidence: medium | URL verified: False
- Modality: Paired comparison of police and insurance injury outcomes for cars by Euro NCAP star rating (2 vs 5 star).
- Measures: Whether level-8 standardised crash test ratings predict real-world injury risk.
- Size: Swedish police + insurance crash data (sample size in paper)
- Reported metrics: 5-star vs 2-star: 10% +/- 2.5% lower injury risk overall; 23% +/- 8% lower fatal+serious; 68% +/- 32% lower fatal.
- Cost evidence: none stated
- Validity evidence: This is the validity evidence: ratings mirror real-world outcomes for all severities.
- Notes: Pre-2018 but the canonical track-test-to-outcome validity study. tandfonline/PubMed blocked; metadata verified via Semantic Scholar API; numbers from search snippet of the abstract.

### kalra2016drivingtosafety: Driving to Safety (RAND): miles needed to demonstrate AV reliability (2016, RAND Corporation)
- URL: https://www.autosafety.org/wp-content/uploads/2016/04/RAND-AV-Report.pdf
- Kind: position | Ladder level: 9 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Statistical argument: binomial/Poisson failure-rate estimation from on-road miles for fatality (1.09/100M mi), injury (77/100M) and crash (190/100M) rates.
- Measures: How many deployment miles are needed to show, with statistical confidence, that an AV is safer than humans.
- Size: n/a
- Reported metrics: 275 million failure-free miles to show fatality rate not worse than humans at 95% confidence; up to billions of miles to show improvement; a 100-vehicle fleet at 24/7 would need ~12.5 years for 275M miles.
- Cost evidence: Quantifies the miles (hence fleet-years) needed for level-9 evidence; explicitly says test driving alone is infeasible.
- Validity evidence: none (theoretical).
- Notes: Pre-2018 but canonical; PDF fetched and text-extracted (rand.org blocked).

## Deployment monitoring (level 9)

### kusano2023waymo7m: Waymo rider-only crash rates vs human benchmarks, 7.1M miles (2023, Waymo)
- URL: https://arxiv.org/abs/2312.12675  | arXiv:2312.12675
- Kind: study | Ladder level: 9 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Operational SGO crash reports from rider-only service (Phoenix, SF, LA) normalised per million miles and compared to location/road-type-matched human benchmarks from police data.
- Measures: Retrospective safety impact of a deployed L4 ADS relative to human drivers.
- Size: 7.14M rider-only miles through Oct 2023
- Reported metrics: Any-injury-reported: 0.6 vs 2.80 IPMM (-80%); police-reported: 2.1 vs 4.68 IPMM (-55%).
- Cost evidence: Requires millions of deployed miles; benchmark construction from state VMT and police data.
- Validity evidence: This is level-9 outcome data; authors caution on underreporting differences and small counts for severe outcomes.
- Notes: none

### kusano2025waymo56m: Waymo rider-only crash rates by crash type, 56.7M miles (2025, Waymo)
- URL: https://arxiv.org/abs/2505.01515  | arXiv:2505.01515
- Kind: study | Ladder level: 9 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Same SGO-based methodology extended to 56.7M miles and 11 crash-type groups; confidence intervals per type.
- Measures: Crash-type-resolved safety impact with statistical conclusions on serious outcomes.
- Size: 56.7M rider-only miles through Jan 2025
- Reported metrics: V2V intersection any-injury -96% (CI 87-99%), airbag -91% (76-98%); significant reductions for cyclist, motorcycle, pedestrian, secondary and single-vehicle crashes; no significant increases in any of 11 types.
- Cost evidence: ~57M deployed miles needed to reach significance on serious-injury crash types.
- Validity evidence: Level-9 outcome data with CIs; first RO study with statistical conclusions on serious crashes.
- Notes: none

### waymo2026impacthub: Waymo Safety Impact data hub (2026, Waymo)
- URL: https://waymo.com/safety/impact/
- Kind: dataset | Ladder level: 9 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Continuously updated dashboard of rider-only miles and SGO crashes vs spatially adjusted human benchmarks; downloadable datasets; refreshed on the NHTSA SGO cadence.
- Measures: Ongoing deployment safety monitoring of an L4 fleet.
- Size: 271.3M rider-only miles through June 2026, 5 cities
- Reported metrics: -82% any-injury crashes, -95% serious-injury-or-worse, -82% airbag deployments, -93% pedestrian injuries, -86% cyclist injuries vs human benchmark.
- Cost evidence: Implicit: 271M commercial miles.
- Validity evidence: Peer-reviewed methodology (Traffic Injury Prevention); accounts for underreporting differences.
- Notes: none

### scanlon2021reconstructed: Waymo Driver in reconstructed fatal crashes (counterfactual sim) (2021, Waymo)
- URL: https://waymo.com/research/waymo-simulated-driving-behavior-in-reconstructed/
- Kind: study | Ladder level: 5 | Safety focus: True | Confidence: high | URL verified: True
- Modality: 72 fatal crashes (2008-2017, Chandler AZ) reconstructed from police data; Waymo Driver substituted for each of 91 human actors in closed-loop simulation; outcome = collision avoided / mitigated / unchanged.
- Measures: Counterfactual safety benefit of an ADS in real fatal-crash scenarios.
- Size: 72 crashes, 91 vehicle actors (52 initiators, 39 responders)
- Reported metrics: As initiator: 100% avoided; as responder: 82% avoided, 10% mitigated, 8% unchanged.
- Cost evidence: Reconstruction from police reports; single-instance simulations.
- Validity evidence: Authors note limits: single instance per scenario, police-data uncertainty; no outcome validation.
- Notes: Level-5 real-data replay used by the same organisation that later published level-9 outcomes; useful pairing.

### flannagan2023cruiseumtri: Cruise/UMTRI human ridehail crash benchmark (San Francisco) (2023, Cruise / UMTRI / GM / VTTI)
- URL: https://www.prnewswire.com/news-releases/cruise-university-of-michigan-transportation-research-institute-present-groundbreaking-study-establishing-a-human-driving-safety-benchmark-301940680.html
- Kind: study | Ladder level: 9 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: 5.6M miles of human ridehail driving (fleet telematics + instrumented vehicles) over 2 years in SF, excluding >35 mph roads, to build a crash-rate benchmark; Cruise fleet crash rates compared.
- Measures: Human benchmark for urban ridehail crashes and an ADS comparison.
- Size: 5.6M human miles; Cruise 1M+ driverless miles
- Reported metrics: Human benchmark ~64.9 crashes per million miles (1 per 15,414 mi); Cruise reported 65% fewer collisions overall, 94% fewer as primary contributor, 74% fewer with meaningful injury risk.
- Cost evidence: Two-year, multi-institution instrumented study to build the benchmark alone.
- Validity evidence: Cautionary: published one week before the Oct 2, 2023 pedestrian-dragging incident that led to permit suspension (see cruise2023incident).
- Notes: Primary technical report not fetched; press release verified.

### cruise2023incident: Cruise Oct 2023 pedestrian incident and aftermath (2023, Cruise / CA DMV / NHTSA)
- URL: https://en.wikipedia.org/wiki/Cruise_(autonomous_vehicle)
- Kind: study | Ladder level: 9 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Operational incident record: driverless vehicle struck and dragged a pedestrian ~20 ft after a hit-and-run; DMV permit suspension (24 Oct 2023), recall of 950 vehicles (8 Nov 2023), Quinn Emanuel/Exponent review (Jan 2024), USD 1.5M NHTSA fine (Sep 2024).
- Measures: A single rare deployment event and its regulatory consequence; demonstrates the asymmetric value of level-9 evidence.
- Size: 1 event
- Reported metrics: Permit suspension, 950-vehicle recall, USD 1.5M fine.
- Cost evidence: Illustrates the cost of a missed failure mode (fleet grounded) rather than evaluation cost.
- Validity evidence: Shows aggregate crash-rate benchmarks published a week earlier did not capture the failure mode.
- Notes: Secondary source; cite the Quinn Emanuel report or DMV order directly in the paper if possible.

### nhtsa2021sgo: NHTSA Standing General Order 2021-01 crash reporting (2021, NHTSA)
- URL: https://mobilitycoe.org/resource/standing-general-order-on-crash-reporting-nhtsa/
- Kind: standard | Ladder level: 9 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Mandatory reporting of crashes involving ADS and L2 ADAS vehicles by manufacturers/operators to NHTSA; public incident-report datasets released periodically.
- Measures: Fleet-level crash incidence for deployed automated vehicles; the data source behind Waymo's studies and third-party trackers.
- Size: 825 ADS incidents in one 2026 snapshot (Waymo 697, Avride 41, Zoox 32, Tesla 18)
- Reported metrics: none (regulatory instrument)
- Cost evidence: Reporting burden on operators; data free to public.
- Validity evidence: Known issues: narrative redactions (Tesla until 2026), reporting-threshold differences vs police data.
- Notes: nhtsa.gov blocked (403); the Center of Excellence mirror page was fetched but truncated. Snapshot counts from a search summary of a 2026 news item.

### chen2026ciimportance: Confidence intervals for rare-event rate estimation with importance sampling (AV) (2026, Waymo/Google statisticians (affiliation not shown on abstract page))
- URL: https://arxiv.org/abs/2604.03827  | arXiv:2604.03827
- Kind: study | Ladder level: 9 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: Compound-Poisson model with Horvitz-Thompson estimation for event rates from importance-sampled AV logs; exponential-bootstrap CIs with monotonicity guarantee and saddlepoint implementation.
- Measures: How to put valid confidence intervals on rare-event rates (collisions per million miles) when data are sampled non-uniformly.
- Size: n/a
- Reported metrics: Method paper; accepted at Annals of Applied Statistics.
- Cost evidence: Motivated by rarity: collisions once per several million human miles.
- Validity evidence: Statistical validity results; no outcome comparison.
- Notes: Affiliation inferred (Chamandy, Hohnhold are known Google/Waymo statisticians); not confirmed on the page.

### soc2022amazonprimed: Amazon robotic vs non-robotic warehouse serious injury rates (SOC report) (2022, Strategic Organizing Center (via OnLabor summary))
- URL: https://onlabor.org/amazons-approach-to-robotics-is-seriously-injuring-warehouse-workers/
- Kind: dataset | Ladder level: 9 | Safety focus: True | Confidence: medium | URL verified: True
- Modality: OSHA Form 300A injury logs by facility, split by robotic vs non-robotic fulfilment centres; serious (lost-time/restricted) injury rate per 100 workers.
- Measures: Human injury incidence in robotised warehouses vs conventional ones.
- Size: Amazon US facilities, 2019-2021 OSHA logs
- Reported metrics: Robotic facilities 7.9 serious injuries per 100 workers (2019) vs ~5.1 non-robotic (54% higher); 2021: 7.3 vs 5.7 (28% higher); Amazon 33% of US warehouse workers but 49% of injuries (2021).
- Cost evidence: Uses mandatory OSHA reporting; no evaluation cost.
- Validity evidence: Observational; confounded by throughput/pace; but it is direct level-9 harm data for a robot fleet.
- Notes: SOC and Reveal pages could not be fetched; the OnLabor summary (fetched) cites the SOC report and Reveal/Washington Post investigations.

### winfield2020accident: Robot accident investigation as responsible robotics (2020, Bristol Robotics Lab / Oxford)
- URL: https://arxiv.org/abs/2005.07474  | arXiv:2005.07474
- Kind: position | Ladder level: 9 | Safety focus: True | Confidence: high | URL verified: True
- Modality: Framework proposing ethical black-box logging and aviation-style investigation processes for social-robot accidents.
- Measures: Argues the infrastructure needed to learn from deployed-robot incidents.
- Size: n/a
- Reported metrics: none
- Cost evidence: none stated
- Validity evidence: none stated
- Notes: none

## Teleoperation and data-collection cost

### khazatsky2024droid: DROID (2024, Stanford / UC Berkeley / TRI + 13 institutions)
- URL: https://arxiv.org/abs/2403.12945  | arXiv:2403.12945
- Kind: dataset | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Human teleoperation (Oculus Quest 2) of a Franka Panda with 2 Zed 2 + Zed Mini cameras; 3 RGB streams, depth, calibration and language instructions per episode.
- Measures: Cost structure of real-robot demonstration collection at scale (the same rig later used for RoboArena evaluation).
- Size: 76k trajectories, 350 h, 564 scenes, 86 tasks, 50 collectors, 12 months, 13 institutions, 1417 camera viewpoints
- Reported metrics: ~217 episodes per collector-hour-equivalent is not stated; 350 h of on-robot time over 12 months and 50 people.
- Cost evidence: 350 h of demonstrations required 50 collectors and 12 months across 13 institutions; hardware per rig: Franka Panda + 3 Zed cameras + Quest 2 (dollar figure not on page).
- Validity evidence: n/a (dataset); policies trained on it generalise better than narrow data.
- Notes: 101 authors truncated.

### oxe2023openx: Open X-Embodiment (2023, Google DeepMind + 21 institutions)
- URL: https://arxiv.org/abs/2310.08864  | arXiv:2310.08864
- Kind: dataset | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Pooled teleoperated/scripted demonstrations from 22 robot embodiments in a common format; RT-X models trained and evaluated across labs.
- Measures: Scale of multi-lab real-robot data pooling and cross-embodiment transfer.
- Size: 22 embodiments, 21 institutions, 527 skills, 160,266 tasks, >1M trajectories
- Reported metrics: Positive transfer of RT-X across embodiments.
- Cost evidence: Aggregates years of collection across 21 institutions; no dollar figure.
- Validity evidence: n/a
- Notes: none

### agibot2025world: AgiBot World Colosseo (2025, AgiBot)
- URL: https://arxiv.org/abs/2503.06669  | arXiv:2503.06669
- Kind: dataset | Ladder level: 7 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: Industrial-scale teleoperated humanoid-manipulator data collection (100+ robots reported by the project) across 5 deployment scenarios; Genie Operator-1 policy trained and evaluated.
- Measures: Company-scale real-robot data throughput.
- Size: >1M trajectories, 217 tasks, 5 scenario domains
- Reported metrics: GO-1: +30% over OXE baseline, >60% on complex tasks, +32% over RDT.
- Cost evidence: Dedicated data-collection facility with a robot fleet; explicit cost not in abstract.
- Validity evidence: n/a
- Notes: Fleet size (100 robots) from project materials, not the abstract.

### chi2024umi: Universal Manipulation Interface (UMI) (2024, Stanford / Columbia / TRI)
- URL: https://arxiv.org/abs/2402.10329  | arXiv:2402.10329
- Kind: tooling | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Hand-held instrumented gripper (GoPro, fisheye, side mirrors) collects in-the-wild demonstrations without a robot; policies deployed on robots with latency matching.
- Measures: Robot-free demonstration collection to cut data cost.
- Size: unknown
- Reported metrics: >3x faster than teleoperation on cup arrangement at 48% of human hand speed; teleop produced zero successful tossing demos in 15 min.
- Cost evidence: Portable, low-cost handheld device; throughput advantage 3x vs teleop (from paper body via search summary).
- Validity evidence: n/a
- Notes: Throughput numbers not in abstract; from search summary of paper body.

### zhao2023aloha: ALOHA low-cost bimanual teleoperation (2023, Stanford / UC Berkeley / Meta)
- URL: https://tonyzhaozh.github.io/aloha/  | arXiv:2304.13705
- Kind: tooling | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: Leader-follower bimanual teleop rig (ViperX/WidowX arms) with ACT imitation learning; 50 demos per task; success rate on 6 real tasks.
- Measures: Hardware cost floor for a research-grade bimanual real-robot rig.
- Size: 6 tasks, 50 demos each
- Reported metrics: 80-90% success with ~10 min of demos on fine tasks.
- Cost evidence: USD 20k complete bimanual system (project page).
- Validity evidence: n/a
- Notes: Both arXiv abstract and project page fetched.

### therobotstudio2024soarm100: SO-100 / SO-101 arm bill of materials (2024, The Robot Studio / Hugging Face LeRobot)
- URL: https://github.com/TheRobotStudio/SO-ARM100
- Kind: tooling | Ladder level: 7 | Safety focus: False | Confidence: high | URL verified: True
- Modality: 3D-printed 6-DoF arm with STS3215 servos; leader+follower pair for teleoperation.
- Measures: Hardware cost floor for a real-robot evaluation cell (used by ArmnetBench and SO-101 VLA benchmark).
- Size: n/a
- Reported metrics: n/a
- Cost evidence: Single follower arm USD 121.94 / EUR 124.30; leader+follower USD 229.88 / EUR 226.30 (BOM, excluding printer and cameras).
- Validity evidence: n/a
- Notes: none

### wang2026xrzero: XRZero-G0 (VR data collection economics) (2026, XRZero (industry))
- URL: https://arxiv.org/abs/2604.13001  | arXiv:2604.13001
- Kind: dataset | Ladder level: 7 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: Ergonomic VR interface with top-view camera and dual grippers for robot-free demonstrations; closed-loop quality pipeline; mixing ratio study with real-robot data.
- Measures: Cost and validity trade-off of robot-free vs real-robot demonstration data.
- Size: 2000 h of robot-free demonstrations
- Reported metrics: 85% data validity rate; optimal 10:1 robot-free to real-robot ratio.
- Cost evidence: Claims ~20x reduction in data acquisition cost vs real-robot teleoperation.
- Validity evidence: Mixing-ratio experiments on downstream policy success.
- Notes: Industry white-paper style; 22 authors.

### agarwal2026cobalt: COBALT crowdsourced cloud teleoperation (2026, Georgia Tech / NVIDIA)
- URL: https://arxiv.org/abs/2605.19138  | arXiv:2605.19138
- Kind: tooling | Ladder level: 7 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: Smartphone teleoperation of robots over cloud infrastructure with real-time quality filtering; 8 concurrent users per GPU at 20 Hz, <100 ms latency.
- Measures: Throughput of crowdsourced demonstration collection.
- Size: 7500+ demonstrations, 50+ h, 9 countries, 5 days
- Reported metrics: Sub-100 ms end-to-end latency; quality filtering improves downstream policies.
- Cost evidence: 50+ h of data in 5 days from distributed volunteers; 8 users per GPU.
- Validity evidence: n/a
- Notes: none

### wang2026zero2skill: Zero2Skill autonomous data collection (2026, GigaAI / others)
- URL: https://arxiv.org/abs/2607.14047  | arXiv:2607.14047
- Kind: tooling | Ladder level: 7 | Safety focus: False | Confidence: medium | URL verified: True
- Modality: Autonomous collect-verify-reset loop with LLM-parsed human corrections stored in a corrective memory; real desktop-clearing testbed.
- Measures: How much human time autonomous collection/verification removes.
- Size: unknown
- Reported metrics: Human working time reduced to 16% of baseline; single-attempt success 12.5% -> 47.5% with corrections.
- Cost evidence: Human time cut to 16%.
- Validity evidence: n/a
- Notes: none

## Hardware-in-the-loop (level 6)

### zhang2025vilsim: Vehicle-in-the-loop simulator with AI digital twins (2025, TU Eindhoven / Siemens)
- URL: https://arxiv.org/abs/2507.02313  | arXiv:2507.02313
- Kind: tooling | Ladder level: 6 | Safety focus: True | Confidence: low | URL verified: True
- Modality: Scaled physical cars run real controllers while the surrounding world is an AI-learned digital twin; filtered-control benchmark with formal safety guarantees.
- Measures: Cheap hardware-in-the-loop validation of automated driving controllers.
- Size: unknown
- Reported metrics: none extracted
- Cost evidence: Motivated by space and expense of full-size ViL testing; no figures.
- Validity evidence: none stated
- Notes: Only level-6 entry found with a verifiable page; HIL literature is mostly in automotive venues not indexed on arXiv.

## BibTeX

```bibtex
@misc{sharrock2025butterbench,
  title={Butter-Bench: Evaluating LLM Controlled Robots for Practical Intelligence},
  author={Sharrock, Callum and Petersson, Lukas and Petersson, Hanna and Backlund, Axel and Wennstr{\"o}m, Axel and Nordstr{\"o}m, Kristoffer and Aronsson, Elias},
  year={2025},
  eprint={2510.21860},
  archivePrefix={arXiv},
  url={https://arxiv.org/abs/2510.21860}
}

@techreport{sharrock2026dronebench,
  title={Drone-Bench: Tracking Simple Drone Surveillance Capabilities of Frontier Models},
  author={Sharrock, Callum and Aronsson, Elias and Petersson, Lukas and Backlund, Axel and Petersson, Hanna and Nordstr{\"o}m, Kristoffer and Carlsson, Rickard and Wennstr{\"o}m, Axel},
  institution={Andon Labs},
  year={2026},
  month={July},
  url={https://andonlabs.com/docs/Drone_Bench.pdf}
}

@misc{anthropic2026projectpilot,
  title={Project Pilot: Can AI models fly drones?},
  author={{Anthropic} and {Andon Labs}},
  year={2026},
  month={July},
  howpublished={\url{https://www.anthropic.com/research/project-pilot}}
}

@misc{anthropic2026claudeplaysrobotics,
  title={Claude Plays Robotics},
  author={{Anthropic}},
  year={2026},
  month={July},
  howpublished={\url{https://www.anthropic.com/research/claude-plays-robotics}}
}

@misc{anthropic2025projectfetch,
  title={Project Fetch: Can Claude help people program a robot dog?},
  author={{Anthropic}},
  year={2025},
  month={November},
  howpublished={\url{https://www.anthropic.com/research/project-fetch-robot-dog}}
}

@article{atreya2025roboarena,
  title={RoboArena: Distributed Real-World Evaluation of Generalist Robot Policies},
  author={Atreya, Pranav and Pertsch, Karl and Lee, Tony and Kim, Moo Jin and Jain, Arhan and others and Finn, Chelsea and Levine, Sergey},
  journal={arXiv preprint arXiv:2506.18123},
  year={2025}
}

@inproceedings{dasari2022rb2,
  title={RB2: Robotic Manipulation Benchmarking with a Twist},
  author={Dasari, Sudeep and Wang, Jianren and Hong, Joyce and Bahl, Shikhar and Lin, Yixin and Wang, Austin and Thankaraj, Abitha and Chahal, Karanbir and Calli, Berk and Gupta, Saurabh and Held, David and Pinto, Lerrel and Pathak, Deepak and Kumar, Vikash and Gupta, Abhinav},
  booktitle={NeurIPS Datasets and Benchmarks Track},
  year={2021},
  note={arXiv:2203.08098}
}

@article{zhou2025autoeval,
  title={AutoEval: Autonomous Evaluation of Generalist Robot Manipulation Policies in the Real World},
  author={Zhou, Zhiyuan and Atreya, Pranav and Tan, You Liang and Pertsch, Karl and Levine, Sergey},
  journal={arXiv preprint arXiv:2503.24278},
  year={2025}
}

@article{yakefu2025robochallenge,
  title={RoboChallenge: Large-scale Real-robot Evaluation of Embodied Policies},
  author={Yakefu, Adina and Xie, Bin and Xu, Chongyang and others},
  journal={arXiv preprint arXiv:2510.17950},
  year={2025}
}

@article{selvaraj2026armnetbench,
  title={ArmnetBench v0.1: Parallel Real-World Evaluation of Manipulation Policies on a Low-Cost Arm Farm},
  author={Selvaraj, Praveen and Uttini, Lorenzo and Kuosmanen, Ville},
  journal={arXiv preprint arXiv:2607.24481},
  year={2026}
}

@article{huang2026vlareplica,
  title={VLA-REPLICA: A Low-Cost, Reproducible Benchmark for Real-World Evaluation of Vision-Language-Action Models},
  author={Huang, Alex S. and Zhang, Jiahui and Tang, Shiqing and Xiang, Yu},
  journal={arXiv preprint arXiv:2605.20774},
  year={2026}
}

@article{yu2026so101bench,
  title={Benchmarking Vision-Language-Action Models on SO-101: Failure and Recovery Analysis},
  author={Yu, Yi and Qiu, Xinchuan},
  journal={arXiv preprint arXiv:2606.08881},
  year={2026}
}

@article{chen2026robodojo,
  title={RoboDojo: A Unified Sim-and-Real Benchmark for Comprehensive Evaluation of Generalist Robot Manipulation Policies},
  author={Chen, Tianxing and others},
  journal={arXiv preprint arXiv:2607.04434},
  year={2026}
}

@inproceedings{li2024simpler,
  title={Evaluating Real-World Robot Manipulation Policies in Simulation},
  author={Li, Xuanlin and Hsu, Kyle and Gu, Jiayuan and Pertsch, Karl and Mees, Oier and Walke, Homer Rich and Fu, Chuyuan and Lunawat, Ishikaa and Sieh, Isabel and Kirmani, Sean and Levine, Sergey and Wu, Jiajun and Finn, Chelsea and Su, Hao and Vuong, Quan and Xiao, Ted},
  booktitle={Conference on Robot Learning (CoRL)},
  year={2024},
  note={arXiv:2405.05941}
}

@article{jeon2026roboworld,
  title={RoboWorld: Fast and Reliable Neural Simulators for Generalist Robot Policy Evaluation},
  author={Jeon, Byeongguk and Ye, Seonghyeon and Doo, JaeHyeok and Kim, Sungdong and Seo, Minjoon and Son, Hyungmok and Lee, Kimin},
  journal={arXiv preprint arXiv:2607.01060},
  year={2026}
}

@article{jangir2025robotarenainf,
  title={RobotArena $\infty$: Scalable Robot Benchmarking via Real-to-Sim Translation},
  author={Jangir, Yash and Zhang, Yidi and Lo, Pang-Chi and Yamazaki, Kashu and Zhang, Chenyu and Tu, Kuan-Hsun and Ke, Tsung-Wei and Ke, Lei and Bisk, Yonatan and Fragkiadaki, Katerina},
  journal={arXiv preprint arXiv:2510.23571},
  year={2025}
}

@article{sedlacek2025realm,
  title={REALM: A Real-to-Sim Validated Benchmark for Generalization in Robotic Manipulation},
  author={Sedlacek, Martin and Yefanov, Pavlo and Ponimatkin, Georgy and Bardhan, Jai and Pilc, Simon and Fourmy, Mederic and Kazakos, Evangelos and Snoek, Cees G. M. and Sivic, Josef and Petrik, Vladimir},
  journal={arXiv preprint arXiv:2512.19562},
  year={2025}
}

@article{ruan2026x2real,
  title={X2Real: an eXtensive simulation benchmark for real-world generalist policies},
  author={Ruan, Lian and others},
  journal={arXiv preprint arXiv:2609.27449},
  year={2026}
}

@article{wang2026simrealrecipe,
  title={A Practical Recipe Towards Improving Sim-and-Real Correlation for VLA Evaluation},
  author={Wang, Shuo and Xu, Hanyuan and Hu, Yingdong and Lin, Fanqi and Gao, Yang},
  journal={arXiv preprint arXiv:2606.10366},
  year={2026}
}

@article{gemini2025veosim,
  title={Evaluating Gemini Robotics Policies in a Veo World Simulator},
  author={{Gemini Robotics Team} and Choromanski, Krzysztof and Devin, Coline and Du, Yilun and others and Sindhwani, Vikas and others},
  journal={arXiv preprint arXiv:2512.10675},
  year={2025}
}

@inproceedings{sermanet2025asimov,
  title={Generating Robot Constitutions \& Benchmarks for Semantic Safety},
  author={Sermanet, Pierre and Majumdar, Anirudha and Irpan, Alex and Kalashnikov, Dmitry and Sindhwani, Vikas},
  booktitle={Conference on Robot Learning (CoRL)},
  year={2025},
  note={arXiv:2503.08663}
}

@article{tri2025lbm,
  title={A Careful Examination of Large Behavior Models for Multitask Dexterous Manipulation},
  author={{TRI LBM Team} and Ambrus, Rares and others and Tedrake, Russ},
  journal={arXiv preprint arXiv:2507.05331},
  year={2025}
}

@article{vincent2024generalizable,
  title={How Generalizable Is My Behavior Cloning Policy? A Statistical Approach to Trustworthy Performance Evaluation},
  author={Vincent, Joseph A. and Nishimura, Haruki and Itkina, Masha and Shah, Paarth and Schwager, Mac and Kollar, Thomas},
  journal={IEEE Robotics and Automation Letters},
  year={2024},
  note={arXiv:2405.05439}
}

@article{badithela2025suresim,
  title={Reliable and Scalable Robot Policy Evaluation with Imperfect Simulators},
  author={Badithela, Apurva and Snyder, David and Zha, Lihan and Mikhail, Joseph and O'Kelly, Matthew and Dixit, Anushri and Majumdar, Anirudha},
  journal={arXiv preprint arXiv:2510.04354},
  year={2025}
}

@article{wan2026nofreechecker,
  title={No Free Checker: A Survey of Verifiers for Robot Policies},
  author={Wan, Yang and Yue, Xihang and Liu, Zhirui and Chu, Ziyuan and Wang, Shuxun and Chen, Yuhan and Jiang, Xiaonan and Zhu, Xukun and Dong, Yubo and Zhu, Linchao},
  journal={arXiv preprint arXiv:2609.09250},
  year={2026}
}

@article{robey2024robopair,
  title={Jailbreaking LLM-Controlled Robots},
  author={Robey, Alexander and Ravichandran, Zachary and Kumar, Vijay and Hassani, Hamed and Pappas, George J.},
  journal={arXiv preprint arXiv:2410.13691},
  year={2024}
}

@inproceedings{zhang2024badrobot,
  title={BadRobot: Jailbreaking Embodied LLM Agents in the Physical World},
  author={Zhang, Hangtao and Zhu, Chenyu and Wang, Xianlong and Zhou, Ziqi and Yin, Changgan and Li, Minghui and Xue, Lulu and Wang, Yichen and Hu, Shengshan and Liu, Aishan and Guo, Peijin and Zhang, Leo Yu},
  booktitle={ICLR},
  year={2025},
  note={arXiv:2407.20242}
}

@inproceedings{lu2025phantommenace,
  title={Phantom Menace: Exploring and Enhancing the Robustness of VLA Models Against Physical Sensor Attacks},
  author={Lu, Xuancun and Chen, Jiaxiang and Xiao, Shilin and Jin, Zizhi and Chen, Zhangrui and Yu, Hanwen and Qian, Bohan and Zhou, Ruochen and Ji, Xiaoyu and Xu, Wenyuan},
  booktitle={AAAI},
  year={2026},
  note={arXiv:2511.10008}
}

@article{bajrami2026robotignores,
  title={How Long Until Your Robot Ignores You? A Safety Benchmark for LLM Orchestrators in Human-Humanoid Collaboration},
  author={Bajrami, Aulon and Elshamouty, Mohamed and Kraus, Werner},
  journal={arXiv preprint arXiv:2609.07288},
  year={2026}
}

@inproceedings{lou2026safeloop,
  title={SafeLoop: Risk-Aware Rollback for Vision-Language-Action Manipulation},
  author={Lou, Zeyu and Zhang, Tianran and Yue, Xinquan and Jing, Ya and Si, Chenyang},
  booktitle={IROS},
  year={2026},
  note={arXiv:2609.26313}
}

@inproceedings{nakamura2025latentsafety,
  title={Generalizing Safety Beyond Collision-Avoidance via Latent-Space Reachability Analysis},
  author={Nakamura, Kensuke and Peters, Lasse and Bajcsy, Andrea},
  booktitle={Robotics: Science and Systems (RSS)},
  year={2025},
  note={arXiv:2502.00935}
}

@article{sun2026safestoppability,
  title={Learning Safe-Stoppability Monitors for Humanoid Robots},
  author={Sun, Yifan and Pan, Yiyuan and Li, Shangtao and Ding, Caiwu and Cui, Tao and Wang, Lingyun and Liu, Changliu},
  journal={arXiv preprint arXiv:2603.22703},
  year={2026}
}

@article{ding2026failpassive,
  title={Toward Certified Functional Safety for Industrial Humanoid Robots: The Fail-Passive Gap and a Feasibility Study},
  author={Ding, Caiwu and Cui, Tao and Wang, Lingyun and Wen, Chengtao},
  journal={arXiv preprint arXiv:2608.02809},
  year={2026}
}

@techreport{ieee2025humanoidpathway,
  title={A Pathway Study for Future Humanoid Standards},
  author={{IEEE Robotics and Automation Society Humanoid Study Group}},
  institution={IEEE RAS},
  year={2025},
  month={September},
  url={https://www.therobotreport.com/wp-content/uploads/2025/09/IEEE-Humanoid-Report-of-Future-Standards-Development.pdf}
}

@misc{iso2025iso25785,
  title={ISO/CD 25785-1 Robotics --- Safety requirements for dynamically stable industrial mobile robots (legged, wheeled, or other forms of locomotion) --- Part 1: Robots},
  author={{ISO/TC 299}},
  year={2025},
  howpublished={Committee draft; \url{https://www.iso.org/standard/91469.html}}
}

@article{han2024painthresholds,
  title={Evaluation of force pain thresholds to ensure collision safety in worker-robot collaborative operations},
  author={Han, D. and Park, M. Y. and Choi, J. and Shin, H. and Behrens, R. and Rhim, S.},
  journal={Frontiers in Robotics and AI},
  year={2024},
  url={https://pmc.ncbi.nlm.nih.gov/articles/PMC11033501/}
}

@techreport{iihs2024paeb,
  title={Pedestrian Automatic Emergency Braking Test Protocol (Version IV)},
  author={{Insurance Institute for Highway Safety}},
  institution={IIHS},
  year={2024},
  month={January},
  url={https://www.iihs.org/media/f6a24355-fe4b-4d71-bd19-0aab8b39aa7e/5ZH5qg/Ratings/Protocols/current/test_protocol_pedestrian_aeb.pdf}
}

@techreport{euroncap2024aebvru,
  title={Test Protocol --- AEB/LSS VRU systems},
  author={{Euro NCAP}},
  institution={European New Car Assessment Programme},
  year={2024},
  url={https://www.euroncap.com/en/for-engineers/protocols/vulnerable-road-user-vru-protection/}
}

@article{kullgren2010euroncap,
  title={Comparison Between Euro NCAP Test Results and Real-World Crash Data},
  author={Kullgren, Anders and Lie, Anders and Tingvall, Claes},
  journal={Traffic Injury Prevention},
  volume={11},
  number={6},
  pages={587--593},
  year={2010},
  doi={10.1080/15389588.2010.508804}
}

@techreport{kalra2016drivingtosafety,
  title={Driving to Safety: How Many Miles of Driving Would It Take to Demonstrate Autonomous Vehicle Reliability?},
  author={Kalra, Nidhi and Paddock, Susan M.},
  institution={RAND Corporation},
  number={RR-1478-RC},
  year={2016}
}

@article{kusano2023waymo7m,
  title={Comparison of Waymo Rider-Only Crash Data to Human Benchmarks at 7.1 Million Miles},
  author={Kusano, Kristofer D. and Scanlon, John M. and Chen, Yin-Hsiu and McMurry, Timothy L. and Chen, Ruoshu and Gode, Tilia and Victor, Trent},
  journal={Traffic Injury Prevention},
  year={2024},
  note={arXiv:2312.12675}
}

@article{kusano2025waymo56m,
  title={Comparison of Waymo Rider-Only Crash Rates by Crash Type to Human Benchmarks at 56.7 Million Miles},
  author={Kusano, Kristofer D. and Scanlon, John M. and Chen, Yin-Hsiu and McMurry, Timothy L. and Gode, Tilia and Victor, Trent},
  journal={Traffic Injury Prevention},
  year={2025},
  note={arXiv:2505.01515}
}

@misc{waymo2026impacthub,
  title={Waymo Safety Impact},
  author={{Waymo LLC}},
  year={2026},
  howpublished={\url{https://waymo.com/safety/impact/}},
  note={Data through June 2026}
}

@article{scanlon2021reconstructed,
  title={Waymo simulated driving behavior in reconstructed fatal crashes within an autonomous vehicle operating domain},
  author={Scanlon, John M. and Kusano, Kristofer D. and Daniel, Tom and Alderson, Christopher and Ogle, Alexander and Victor, Trent},
  journal={Accident Analysis \& Prevention},
  volume={163},
  pages={106454},
  year={2021}
}

@misc{flannagan2023cruiseumtri,
  title={Cruise, University of Michigan Transportation Research Institute present groundbreaking study establishing a human driving safety benchmark},
  author={{Cruise LLC} and {UMTRI}},
  year={2023},
  month={September},
  howpublished={Press release, \url{https://www.prnewswire.com/news-releases/cruise-university-of-michigan-transportation-research-institute-present-groundbreaking-study-establishing-a-human-driving-safety-benchmark-301940680.html}}
}

@misc{cruise2023incident,
  title={Cruise (autonomous vehicle): October 2023 pedestrian incident},
  author={{Wikipedia contributors}},
  year={2024},
  howpublished={\url{https://en.wikipedia.org/wiki/Cruise_(autonomous_vehicle)}},
  note={Accessed September 2026}
}

@misc{nhtsa2021sgo,
  title={Standing General Order 2021-01: Incident Reporting for Automated Driving Systems and Level 2 Advanced Driver Assistance Systems},
  author={{National Highway Traffic Safety Administration}},
  year={2021},
  howpublished={\url{https://www.nhtsa.gov/laws-regulations/standing-general-order-crash-reporting}},
  note={Amended 2023 and 2025}
}

@article{chen2026ciimportance,
  title={Confidence Intervals for Rate Estimation with Importance Sampling in Autonomous Vehicle Evaluation},
  author={Chen, Aiyou and Zhou, Ruixuan Rachel and Lee, Joseph J. and Chamandy, Nicholas and Hohnhold, Henning},
  journal={Annals of Applied Statistics (to appear)},
  year={2026},
  note={arXiv:2604.03827}
}

@misc{soc2022amazonprimed,
  title={Amazon Primed for Pain},
  author={{Strategic Organizing Center}},
  year={2022},
  howpublished={Report; summarised in OnLabor, \url{https://onlabor.org/amazons-approach-to-robotics-is-seriously-injuring-warehouse-workers/}}
}

@article{winfield2020accident,
  title={Robot Accident Investigation: a case study in Responsible Robotics},
  author={Winfield, Alan F. T. and Winkle, Katie and Webb, Helena and Lyngs, Ulrik and Jirotka, Marina and Macrae, Carl},
  journal={arXiv preprint arXiv:2005.07474},
  year={2020}
}

@inproceedings{khazatsky2024droid,
  title={DROID: A Large-Scale In-The-Wild Robot Manipulation Dataset},
  author={Khazatsky, Alexander and Pertsch, Karl and Nair, Suraj and others},
  booktitle={Robotics: Science and Systems (RSS)},
  year={2024},
  note={arXiv:2403.12945}
}

@inproceedings{oxe2023openx,
  title={Open X-Embodiment: Robotic Learning Datasets and RT-X Models},
  author={{Open X-Embodiment Collaboration}},
  booktitle={IEEE International Conference on Robotics and Automation (ICRA)},
  year={2024},
  note={arXiv:2310.08864}
}

@article{agibot2025world,
  title={AgiBot World Colosseo: A Large-scale Manipulation Platform for Scalable and Intelligent Embodied Systems},
  author={{AgiBot-World-Contributors}},
  journal={arXiv preprint arXiv:2503.06669},
  year={2025}
}

@inproceedings{chi2024umi,
  title={Universal Manipulation Interface: In-The-Wild Robot Teaching Without In-The-Wild Robots},
  author={Chi, Cheng and Xu, Zhenjia and Pan, Chuer and Cousineau, Eric and Burchfiel, Benjamin and Feng, Siyuan and Tedrake, Russ and Song, Shuran},
  booktitle={Robotics: Science and Systems (RSS)},
  year={2024},
  note={arXiv:2402.10329}
}

@inproceedings{zhao2023aloha,
  title={Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware},
  author={Zhao, Tony Z. and Kumar, Vikash and Levine, Sergey and Finn, Chelsea},
  booktitle={Robotics: Science and Systems (RSS)},
  year={2023},
  note={arXiv:2304.13705}
}

@misc{therobotstudio2024soarm100,
  title={SO-ARM100: Standard Open Arm 100},
  author={{The Robot Studio}},
  year={2024},
  howpublished={\url{https://github.com/TheRobotStudio/SO-ARM100}}
}

@article{wang2026xrzero,
  title={XRZero-G0: Pushing the Frontier of Dexterous Robotic Manipulation with Interfaces, Quality and Ratios},
  author={Wang, James and others},
  journal={arXiv preprint arXiv:2604.13001},
  year={2026}
}

@article{agarwal2026cobalt,
  title={COBALT: Crowdsourcing Robot Learning via Cloud-Based Teleoperation with Smartphones},
  author={Agarwal, Ayush and Gandhi, Ansh and Collins, Jeremy A. and Rayyan, Omar and Sarswat, Aryan and Koushik, Ranjani and Moghani, Masoud and Mandlekar, Ajay and Garg, Animesh},
  journal={arXiv preprint arXiv:2605.19138},
  year={2026}
}

@article{wang2026zero2skill,
  title={Zero2Skill: Bootstrapping Robot Skills through Autonomous Data Collection, Training, and Deployment},
  author={Wang, Boyuan and Zhang, Zhenyuan and Yang, Zhiqin and others and Zhu, Zheng},
  journal={arXiv preprint arXiv:2607.14047},
  year={2026}
}

@article{zhang2025vilsim,
  title={A Vehicle-in-the-Loop Simulator with AI-Powered Digital Twins for Testing Automated Driving Controllers},
  author={Zhang, Zengjie and Badakis, Giannis and Galanis, Michalis and Bavar{\c{s}}i, Adem and van Hassel, Edwin and Alirezaei, Mohsen and Haesaert, Sofie},
  journal={arXiv preprint arXiv:2507.02313},
  year={2025}
}
```
