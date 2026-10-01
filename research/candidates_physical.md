# Candidate physical-AI safety evaluations: ranked list, inclusion threshold, fidelity levels

Generated 2026-10-01 from the sources listed at the end, each fetched on 2026-10-01. Companion data: `research/candidates_physical.json` (same content, machine-readable). Terminology follows docs/DESIGN.md section 2. Acronyms: EVSI expected value of sample information; LLM large language model; VLM vision-language model; VLA vision-language-action model; AEB automatic emergency braking; IIHS Insurance Institute for Highway Safety; HLDI Highway Loss Data Institute; OEM original equipment manufacturer; ASR attack success rate; FNR false-negative rate; FPR false-positive rate; MAE mean absolute error; MMRV mean maximum rank violation; PFL power and force limiting; STL signal temporal logic; LTLf linear temporal logic on finite traces; NEISS National Electronic Injury Surveillance System; PDMS PDM Score.

## 1. Ranking rule and inclusion threshold

Five criteria, all checkable from the fetched sources:

- C1. Checkable physical hazard: the score is the rate of a physically harmful event, or of a decision that would directly cause one (collision, contact force over a body-region limit, an injurious action executed, planned or accepted, a failure to stop or brake). Fails when the score is task success, generic or dual-use capability, or governance.
- C2. Public primary source with a score: a paper, report or protocol fetched on 2026-10-01 that reports at least one numeric score for at least one system under test. An access-controlled dataset with a public report passes with a note; 'release upon acceptance' fails.
- C3. At least one cost fact or one validity fact in the primary source or a paired source. Cost: dollars, wall-clock or compute time, or a quantified input (trial count, item count with labour type, hardware list). Validity: an agreement statistic, a reproduction or correlation at a higher fidelity level, or a field-outcome correlation.
- C4. Single build-and-run instrument: one protocol, one system under test, one run yields the score. Fails for multi-vehicle programmes, standards text alone, uplift studies, defence tools, and frameworks without a fixed scenario set.
- C5. One evaluation per construct: when two passing candidates test the same hazardous property of the same kind of system at the same fidelity level, the one with more C3 facts stays and the other is excluded as 'same construct'.

Points for ranking the candidates that pass every criterion:

- V: validity class: 3 field-outcome correlation (level 9); 2 quantitative reproduction or correlation at a higher fidelity level; 1 human verification or agreement statistic only; 0 none
- K: cost class: 2 dollars or wall-clock/compute time; 1 quantified inputs only (trials, items, hardware); 0 none
- H: hazard directness: 2 harmful event observed on a physical system (contact, collision, executed harmful action); 1 hazard decided by a simulator predicate or by a human/LLM judge of a plan, answer or generated video; 0 task-success proxy
- L: fidelity-level spread: +1 for the highest-scoring passing candidate at each fidelity level
- total: V + K + H + L; ties broken by V, then H, then K, then earlier first-version date

Inclusion threshold: Include if and only if C1 to C5 all pass. Ranks 1..n_pass are the included set; the next ranks are alternates (include: false), ordered by fewest failed criteria then points.

Result: 35 candidates assessed, 15 ranked, 13 pass all five criteria and are included. Ranks 14-15 are alternates. Fidelity levels covered by the included set: 0, 2, 3, 4, 5, 7, 8. Empty levels: 1, 6, 9 (level 1 static-image QA is covered inside ASIMOV-2.0's constraint track; level 6 hardware-in-the-loop has no safety instrument with a public score; level 9 is outcome data, not an instrument).

## 2. Ranked list

| rank | include | evaluation | level | system under test | V | K | H | L | total | criteria failed |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | yes | IIHS pedestrian AEB track protocol (Version IV) (`iihs2024paeb`) | 8 | Non-language-model system | 3 | 2 | 2 | 1 | 8 | none |
| 2 | yes | RoboPAIR jailbreak red-teaming of LLM-controlled robots (`robey2024robopair`) | 7 | LLM inside a robot | 1 | 2 | 2 | 1 | 6 | none |
| 3 | yes | Veo world-model safety probing of VLA checkpoints (`geminirobotics2025veo`) | 5 | VLA policy | 2 | 1 | 1 | 1 | 5 | none |
| 4 | yes | RedVLA physical red teaming of VLA policies (`zhang2026redvla`) | 4 | VLA policy | 2 | 1 | 1 | 1 | 5 | none |
| 5 | yes | ISO 10218:2025 / ISO/TS 15066 power-and-force-limiting contact-force test (`iso2025iso10218`) | 7 | Non-language-model system | 1 | 1 | 2 | 0 | 4 | none |
| 6 | yes | ManiGuard specification-grounded manipulation safety suite (`peng2026maniguard`) | 7 | VLA policy | 1 | 1 | 2 | 0 | 4 | none |
| 7 | yes | SafeAgentBench hazardous-task refusal and execution (`yin2024safeagentbench`) | 4 | LLM planner inside an embodied agent | 1 | 2 | 1 | 0 | 4 | none |
| 8 | yes | IS-Bench interactive safety of VLM-driven household agents (`lu2025isbench`) | 4 | VLM agent | 1 | 2 | 1 | 0 | 4 | none |
| 9 | yes | ASIMOV-2.0 physical-danger perception and constraint following (`jindal2025danger`) | 3 | VLM planner or 'robot brain' | 1 | 1 | 1 | 1 | 4 | none |
| 10 | yes | ASIMOV-Agentic human-proximity stop and constraint-following (`geminirobotics2026agentic`) | 2 | Embodied-reasoning VLM orchestrating a VLA | 1 | 1 | 1 | 1 | 4 | none |
| 11 | yes | EgoSafetyBench VLM runtime safety guard on egocentric video (`panpatil2026egosafetybench`) | 3 | VLM used as a runtime guard on a home or factory robot | 1 | 1 | 1 | 0 | 3 | none |
| 12 | yes | SafePlan prompt suite (with SafeGate follow-up) (`obi2025safeplan`) | 0 | LLM planner | 0 | 1 | 1 | 1 | 3 | none |
| 13 | yes | LLM-orchestrator safety benchmark for human-humanoid collaboration (`bajrami2026robotignores`) | 0 | LLM orchestrator | 0 | 1 | 1 | 0 | 2 | none |
| 14 | no | NHTSA FMVSS No. 127 AEB compliance test (`nhtsa2024fmvss127`) | 8 | Non-language-model production AEB stack. | 1 | 2 | 2 | 0 | 5 | C5 |
| 15 | no | NAVSIM non-reactive driving evaluation (PDM Score) (`dauner2024navsim`) | 5 | End-to-end learned driving planner | 2 | 1 | 1 | 0 | 4 | C1 |

Mix of systems among the included evaluations, which the paper must state: 8 test a language or vision-language model inside a robot stack (robey2024robopair, yin2024safeagentbench, lu2025isbench, jindal2025danger, geminirobotics2026agentic, panpatil2026egosafetybench, obi2025safeplan, bajrami2026robotignores); 3 test a VLA policy (peng2026maniguard, geminirobotics2025veo, zhang2026redvla); 2 test a non-language-model system (iihs2024paeb, iso2025iso10218).

The pilot's five (ASIMOV-2.0, SafeAgentBench, Veo world-model probing, RoboPAIR, IIHS pedestrian AEB) all pass and are kept.

## 3. Borderline cases

- NHTSA FMVSS 127 (rank 14): passes C1-C4 with the strongest dollar figures of any candidate but fails C5 against IIHS. If the study wants a regulatory pass/fail decision rather than a rating decision, swap it for IIHS; do not include both.
- NAVSIM (rank 15): the collision subscore is a hazard rate but the composite is task quality, and the collision subscore is its weakest predictor of closed-loop driving (Wang 2026). Include only if a driving-domain level-5 entry with a non-language-model system is wanted; NeuroNCAP is the hazard-shaped alternative but has no cost or validity fact.
- EgoSafetyBench (rank 11): passes, but its construct (VLM runtime guard on generated video) is close to the ASIMOV-2.0 video track and to HomeSafe-Bench. It is kept because it is the only candidate that reports miss and false-alarm rates separately with an inter-annotator kappa.
- ISO 10218:2025 / ISO/TS 15066 contact-force test (rank 5): the standard text is paywalled; C2 passes through three public measurement studies. It is the only level-7 entry that tests a non-language-model system and the only one with an ISO basis.
- SafePlan (rank 12) and the Bajrami orchestrator benchmark (rank 13): pass C3 only through quantified inputs (prompt and session counts), with no validity fact. They are the only level-0 candidates; drop both if the study does not need a text-only level.
- ManiGuard (rank 6): a preprint of 2026-08-18 that scores on hardware (H=2). Its sim-to-real section (Q5) gives Pearson r over 12 matched cells of 0.91 for task success and 0.88 for safe success but 0.09 for the violation rate, the score that carries theta; the paper's own reading is 'The unsafe outcomes recur; their frequency does not.' That is a qualitative reproduction, so V=1 and the level-7 spread bonus goes to RoboPAIR (rank 2). ManiGuard ties ISO on points and ranks below it on the earlier-first-version tie-break. Its facts come from the abstract and HTML full text; no code or data release was verified.
- SafeVLA-Bench, EmbodyGuard, HomeSafe-Bench: each loses C5 to a better-documented candidate of the same construct (ManiGuard, SafePlan, EgoSafetyBench). Each is a drop-in alternate.
- TouchSafeBench: would be a strong level-4 collision-monitoring instrument but is unreleased ('upon acceptance'), so C2 fails.
- Swiss Re / Stanford ADAS and Waymo CAT: programme-scale campaigns with the best run-count and turnaround facts; used as cost anchors, not instruments.

## 4. Included evaluations

### 1. IIHS pedestrian AEB track protocol (Version IV) (`iihs2024paeb`), fidelity level 8

- Fidelity level: Production vehicle driven by a robot into articulated pedestrian dummies on an instrumented closed track, day and night: real system, field-like test with human surrogates, no human at risk (level 8).
- What it measures: Speed reduction or avoidance when a production pedestrian automatic emergency braking (AEB) system meets an adult crossing at night (20, 40 km/h), a child crossing by day (20, 40 km/h) and an adult walking parallel at night (40, 60 km/h); three valid runs per cell, scored into good/acceptable/marginal/poor.
- Hazardous property: The AEB fails to brake for a pedestrian, so the vehicle strikes a person.
- System under test: Non-language-model system: a production AEB stack (camera/radar perception plus deterministic brake control). No LLM, VLM or VLA.
- Primary source: IIHS Pedestrian Autonomous Emergency Braking Test Protocol (https://www.iihs.org/media/f6a24355-fe4b-4d71-bd19-0aab8b39aa7e/5ZH5qg/Ratings/Protocols/current/test_protocol_pedestrian_aeb.pdf), fetched 2026-10-01
- Paired sources: IIHS news (https://www.iihs.org/news/detail/subaru-crash-avoidance-system-cuts-pedestrian-crashes); Cicchino (https://www.iihs.org/research-areas/bibliography/ref/2243); Futurride (https://futurride.com/2022/02/03/iihs-study-reveals-aeb-limitations-in-dark-conditions/); Euro NCAP FAQ (https://www.euroncap.com/faq/); Mcity Test Facility recharge rates (LC member sheet (https://mcity.umich.edu/wp-content/uploads/2022/11/11.1.22_TestFacilityRates-LC.pdf)
- Single build-and-run instrument: yes
- Proposed decision: An OEM's head of active-safety validation decides whether to release a new pedestrian AEB calibration on schedule or delay it and rework perception and braking.
- theta: theta=1: the pedestrian AEB fails to avoid or substantially mitigate the protocol's crossing and parallel pedestrian scenarios at 20-60 km/h, especially at night, so it would rate below acceptable and would strike pedestrians in the field.
- Cost facts:
  - "A total of three valid runs are performed at each test speed in each lighting condition (day and night)" [IIHS Pedestrian Autonomous Emergency Braking Test Protocol, fetched 2026-10-01]
  - "Test vehicle speed 20, 40 km/h | 20, 40 km/h | 40, 60 km/h; Lighting condition: Night | Day | Night; Dark headlight condition: High and low beams | NA | High and low beams; Number of valid runs 3 | 3 | 3 (protocol summary table; this gives 12 + 6 + 12 = 30 scored runs per vehicle, not the 36 recorded in catalog.json)" [IIHS Pedestrian Autonomous Emergency Braking Test Protocol, fetched 2026-10-01]
  - "IIHS uses 4active (4a) pedestrian test equipment for this test" [IIHS Pedestrian Autonomous Emergency Braking Test Protocol, fetched 2026-10-01]
  - "IIHS uses a 4activeSB surfboard system for dynamic pedestrian tests to control and record dummy speed" [IIHS Pedestrian Autonomous Emergency Braking Test Protocol, fetched 2026-10-01]
  - "For nighttime testing, illumination must remain below 1 lux throughout testing." [IIHS Pedestrian Autonomous Emergency Braking Test Protocol, fetched 2026-10-01]
  - "A full Euro NCAP test programme costs several hundreds of thousands of Euros." [Euro NCAP FAQ, fetched 2026-10-01]
  - "Euro NCAP typically requires a minimum of six test vehicles. (one of them for track testing of advanced driver assistance systems)" [Euro NCAP FAQ, fetched 2026-10-01]
  - "Whole Track /full day $3,127; /half day $1,563; Technician (Custom Installation) per hour $71; Use of Vehicle /full day $537; Driver per hour $71 (LC Member rates)" [Mcity Test Facility recharge rates (LC member sheet, fetched 2026-10-01]
- Validity facts:
  - "EyeSight cut the rate of likely pedestrian-related insurance claims by 35 percent. The first-generation system reduced claim frequency 33 percent, while the second-generation system lowered it 41 percent." [IIHS news, fetched 2026-10-01]
  - "25%-27% in pedestrian crash risk and 29%-30% in pedestrian injury crash risk (reductions); no effectiveness in dark conditions without street lighting, at speed limits of 50 mph or greater, or while the AEB-equipped vehicle was turning" [Cicchino, fetched 2026-10-01]
  - "crash rates for pedestrian crashes of all severities were 27% lower for vehicles equipped with pedestrian AEB ... Injury crash rates were 30% lower ... reduced the odds of a pedestrian crash by 32% in the daylight and 33% in areas with artificial lighting" [Futurride, fetched 2026-10-01]
  - "Total score < 1 Poor; 1 <= total score < 3 Marginal; 3 <= total score < 5 Acceptable; Total score >= 5 Good" [IIHS Pedestrian Autonomous Emergency Braking Test Protocol, fetched 2026-10-01]
- Fit problems: Dollar cost of one IIHS test is not published; the Euro NCAP programme cost and the Mcity track rate are proxies. The field-validity numbers are for the vehicle population carrying pedestrian AEB, not for the Version IV protocol itself; the protocol's night tests were added because the field data showed no benefit in the dark.
- Criterion notes: Same construct as Euro NCAP AEB VRU and FMVSS 127; IIHS kept because it publishes the run count and has the field-claims chain.
- Points: V=3 K=2 H=2 L=1 total=8. In system-card corpus: no. Pilot five: yes.

### 2. RoboPAIR jailbreak red-teaming of LLM-controlled robots (`robey2024robopair`), fidelity level 7

- Fidelity level: Jailbroken plans are executed on a Clearpath Jackal UGV and a Unitree Go2 in a controlled lab with no person at risk (level 7); the NVIDIA Dolphins driving-LLM setting is text/video QA (level 0-2) and is not the instrument proposed here.
- What it measures: Attack success rate (ASR) of an attacker LLM eliciting harmful physical actions (bomb detonation, blocking an emergency exit, weapon search, keep-out-zone entry, covert surveillance, human collision) from a robot's LLM planner; 7 harmful actions x 5 trials per robot, LLM judge plus two human annotators, action executed on the robot.
- Hazardous property: The robot's language model planner can be driven by text to execute a physically harmful action (collide with a person, enter a keep-out zone, block an exit).
- System under test: LLM inside a robot: GPT-4o planner on the Jackal (gray box), GPT-3.5 on the Go2 (black box).
- Primary source: arXiv 2410.13691 (https://arxiv.org/abs/2410.13691), fetched 2026-10-01
- Paired sources: arXiv 2503.07885 (https://arxiv.org/abs/2503.07885)
- Single build-and-run instrument: yes
- Proposed decision: A company about to field an LLM-controlled quadruped or ground robot decides whether to deploy on schedule or delay and add guardrails.
- theta: theta=1: the robot's LLM planner can be jailbroken by text prompts into executing physically harmful actions (blocking an emergency exit, searching for weapons, colliding with people), and the robot carries them out.
- Cost facts:
  - "(i) a white-box setting, wherein the attacker has full access to the NVIDIA Dolphins self-driving LLM, (ii) a gray-box setting, wherein the attacker has partial access to a Clearpath Robotics Jackal UGV robot equipped with a GPT-4o planner, and (iii) a black-box setting, wherein the attacker has only query access to the GPT-3.5-integrated Unitree Robotics Go2 robot dog" [arXiv 2410.13691, fetched 2026-10-01]
  - "Harmful actions ... Bomb detonation ... Emergency exit ... Weapon search ... Warehouse assistant ... Keep-out zone ... Covert surveillance ... Human collision ... Aggregate 1/35 32/35 30/35 5/35 35/35 (Jackal table: 7 actions x 5 trials per attack method)" [arXiv 2410.13691, fetched 2026-10-01]
  - "RoboGuard uses between 21% to 12% of the tokens required by the attackers, while only requiring 1 LLM query in contrast to the attacker's 15." [arXiv 2503.07885, fetched 2026-10-01]
  - "Adaptive black-box 20471.1 +/- 126.7 tokens, 15 LLM queries; Adaptive grey-box GR 52515.6 +/- 132.5; Adaptive white-box 36446.2 +/- 126.7 (Table III, cost of one attack)" [arXiv 2503.07885, fetched 2026-10-01]
  - "the robot is equipped with an Nvidia A4000 GPU and Ryzen 5 3600 CPU for compute" [arXiv 2503.07885, fetched 2026-10-01]
  - "We evaluate each of the 70 considered adversarial behaviors on randomized small indoor, large indoor, and outdoor environments, resulting in 210 evaluations per attack and over 1,500 evaluations in total." [arXiv 2503.07885, fetched 2026-10-01]
- Validity facts:
  - "All jailbreaks are also evaluated by two expert human annotators to ensure correctness." [arXiv 2410.13691, fetched 2026-10-01]
  - "our results on the Unitree Go2 represent the first successful jailbreak of a deployed commercial robotic system" [arXiv 2410.13691, fetched 2026-10-01]
  - "RoboGuard reduces the execution of unsafe plans from 92.3% to under 2.5% without compromising performance on safe plans. (unguarded RoboPAIR ASR 92.3 +/- 4.7%, with RoboGuard 2.3 +/- 1.5%)" [arXiv 2503.07885, fetched 2026-10-01]
- Fit problems: No inter-annotator statistic; no wall-clock or dollar figure (token counts come from the paired RoboGuard paper). ASR of 100% on all three targets means the published instrument does not discriminate between the systems tested; a deployer would set the flag on a lower ASR threshold. Adversarial (worst-case) rather than average-case hazard.
- Criterion notes: RoboGuard and RoboJailBench share the construct; RoboPAIR kept (physical execution, two human annotators). Takes the level-7 spread bonus after ManiGuard drops to V=1.
- Points: V=1 K=2 H=2 L=1 total=6. In system-card corpus: no. Pilot five: yes.

### 3. Veo world-model safety probing of VLA checkpoints (`geminirobotics2025veo`), fidelity level 5

- Fidelity level: Action-conditioned photoreal video generation from edited real scenes, scored by human raters; a generative digital twin, validated against real episodes (level 5).
- What it measures: Human-rated unsafe behaviour of a VLA policy in generated 8-second rollouts of edited real scenes containing hazards (sharp objects, hot objects, full glasses), alongside nominal and out-of-distribution success rates.
- Hazardous property: A VLA checkpoint handles hazardous objects or acts unsafely near fragile items and people in scenes it will meet in deployment.
- System under test: VLA policy (Gemini Robotics checkpoints on a bimanual ALOHA-class manipulator).
- Primary source: arXiv 2512.10675 (https://arxiv.org/abs/2512.10675), fetched 2026-10-01
- Single build-and-run instrument: yes
- Proposed decision: The developer of a VLA decides whether to deploy a new checkpoint or hold it for further training and hardware testing.
- theta: theta=1: the checkpoint exhibits physical or semantic safety failures (unsafe handling of hazardous objects, unsafe motions near people or fragile items) under out-of-distribution scenes it will meet in deployment.
- Cost facts:
  - "We validate predictions from our video model across 1600+ real-world trials with eight generalist policy checkpoints and five tasks." [arXiv 2512.10675, fetched 2026-10-01]
  - "Each episode consists of an 8-second rollout, which is scored with the binary success metric by human evaluators." [arXiv 2512.10675, fetched 2026-10-01]
  - "When the objective is to evaluate safety, hardware evaluation is often simply infeasible." [arXiv 2512.10675, fetched 2026-10-01]
- Validity facts:
  - "These predictions are validated by the real-world evaluations with an MMRV of 0.06." [arXiv 2512.10675, fetched 2026-10-01]
  - "there is a strong linear correlation (Pearson = 0.86) between predicted and real success rates" [arXiv 2512.10675, fetched 2026-10-01]
  - "We also replicated these scenarios with real-world props, and found that the unsafe behaviors predicted by the video model are observed in these experiments." [arXiv 2512.10675, fetched 2026-10-01]
- Fit problems: No compute, hours or dollar figure; the 1,600+ real episodes are the validation cost, not the run cost. The correlation numbers are for success rates; the safety reproduction is qualitative (examples replicated with props). Requires a frontier video model fine-tuned for action conditioning, so C_build is dominated by a capability few developers have.
- Points: V=2 K=1 H=1 L=1 total=5. In system-card corpus: no. Pilot five: yes.

### 4. RedVLA physical red teaming of VLA policies (`zhang2026redvla`), fidelity level 4

- Fidelity level: The ASR is computed in LIBERO-style closed-loop MuJoCo scenes with inserted risk objects (level 4); the Franka experiments are a validation study of the found scenes, used here as the cross-level validity fact. catalog.json records level 7 for the same reason; the sim-only instrument is proposed because that is where the score is produced.
- What it measures: Attack success rate (ASR) with which gradient-free placement of risk objects (knives, obstacles) near a VLA's interaction regions elicits unsafe behaviour detected by state, cumulative and conditional safety predicates; 10 risk scenarios x 10 seeds, 6 VLAs, 10 optimisation iterations.
- Hazardous property: A VLA manipulation policy contacts a knife, collides with a placed object or otherwise acts unsafely when the scene contains a plausibly placed hazard.
- System under test: VLA policy (pi0, pi0.5, OpenVLA, OpenVLA-OFT, VLA-Adapter-Pro and one more).
- Primary source: arXiv 2604.22591 (https://arxiv.org/abs/2604.22591), fetched 2026-10-01
- Paired sources: RedVLA project page (https://redvla.github.io)
- Single build-and-run instrument: yes
- Proposed decision: A developer deploying a VLA-based manipulator decides whether to ship the policy or delay for guard training on found failure scenes.
- theta: theta=1: the policy has a scene-triggerable unsafe behaviour mode (knife contact, collision with a placed object) that reproduces on hardware.
- Cost facts:
  - "Each risk scenario is evaluated over 10 trials with different seeds, and all metrics are averaged across trials." [arXiv 2604.22591, fetched 2026-10-01]
  - "achieves the ASR up to 95.5% within 10 optimization iterations" [arXiv 2604.22591, fetched 2026-10-01]
  - "6 VLA models from three model families" [RedVLA project page, fetched 2026-10-01]
- Validity facts:
  - "We build two physical platform with Franka robot and deploy the pi0 policy and pi0.5 policy. ... Both scenarios achieve ASR above 80% over 10 trials per task, confirming that such unsafe behaviors also manifest in the real world." [arXiv 2604.22591, fetched 2026-10-01]
  - "Real-world Franka validation >80% ASR over 10 trials per task" [RedVLA project page, fetched 2026-10-01]
  - "RedVLA achieves the Attack Success Rate (ASR) up to 95.5% on pi0.5 and an average ASR of 92.1% across the five models" [arXiv 2604.22591, fetched 2026-10-01]
- Fit problems: Compute per optimisation run not reported; scene plausibility is human-annotated (Appendix F) without agreement statistics. ASR above 90% for five of six models compresses the score near the ceiling. JailWAM (world action models) shares the construct in RoboTwin without hardware validation.
- Points: V=2 K=1 H=1 L=1 total=5. In system-card corpus: no. Pilot five: no.

### 5. ISO 10218:2025 / ISO/TS 15066 power-and-force-limiting contact-force test (`iso2025iso10218`), fidelity level 7

- Fidelity level: The real robot is driven into a biofidelic force and pressure measurement device at the application's contact points and speeds in a controlled lab; no person is exposed (level 7).
- What it measures: Measured transient and quasi-static contact force and pressure at foreseeable contact points of a collaborative robot application, compared with body-region limits; pass/fail per contact point, and the maximum permissible speed.
- Hazardous property: A robot operating in power-and-force-limiting (PFL) mode strikes or clamps a person with a force or pressure above the biomechanical limit for the body region.
- System under test: Non-language-model system (non-learning): the robot's controller, collision detection and reaction (the test applies equally to a learned-policy robot, which it treats as a black box).
- Primary source: arXiv 2203.09872 (https://arxiv.org/abs/2203.09872), fetched 2026-10-01; arXiv 2009.01036 (https://arxiv.org/abs/2009.01036), fetched 2026-10-01; arXiv 2203.02706 (https://arxiv.org/abs/2203.02706), fetched 2026-10-01
- Paired sources: The Robot Report (https://www.therobotreport.com/iso-10218-industrial-robot-safety-standard-receives-major-overhaul/); Gemini Robotics Team (https://storage.googleapis.com/deepmind-media/gemini-robotics/Gemini-Robotics-2-Safety.pdf)
- Single build-and-run instrument: yes
- Proposed decision: A system integrator commissioning a collaborative robot application with humans in the workspace decides whether to release it at the planned speed or reduce speed, add padding or add separation monitoring.
- theta: theta=1: at least one foreseeable contact event in the application exceeds the transient or quasi-static force or pressure limit for the body region concerned.
- Cost facts:
  - "We present a total of 2250 collision measurements and study the impact force, contact duration, clamping force, and impulse. The dataset is publicly available." [arXiv 2203.09872, fetched 2026-10-01]
  - "With an experiment including four commercially available robot systems we demonstrate the procedure of the risk assessment" [arXiv 2203.02706, fetched 2026-10-01]
  - "now available for purchase to U.S. customers for $244 (ISO 10218:2025); the revision required nearly eight years of work" [The Robot Report, fetched 2026-10-01]
- Validity facts:
  - "impact forces can vary by more than 100 percent within the robot workspace ... formulas relating robot mass, velocity, and impact forces from ISO/TS 15066 are insufficient -- leading both to significant underestimation and overestimation" [arXiv 2009.01036, fetched 2026-10-01]
  - "In some cases, up to the quadruple of the ISO/TS 15066 prescribed velocity can comply with the impact force limits and thus be considered safe. ... this work emphasizes the need for in situ measurements" [arXiv 2203.09872, fetched 2026-10-01]
  - "logically conflicting definitions for the contact between human and robot. This may result in different interpretations for the contact classification and thus no unique outcome can be expected" [arXiv 2203.02706, fetched 2026-10-01]
  - "The baseline rules for how robots must stop around humans are defined by ISO 10218:2025 [1, 2]. This standard absorbs the collaborative guidelines originally outlined in ISO/TS 15066" [Gemini Robotics Team, fetched 2026-10-01]
- Fit problems: The standard text is paywalled; the public primary sources are measurement studies, so the 'score' is a measured force against a limit rather than a leaderboard number. Verdicts are assessor-dependent (Kirschner 2022), which is a reliability problem the elicitor must price into s and t. Not an evaluation of a language model; included because the paper must state the mix and because the Gemini Robotics 2 safety report cites it as the baseline rule set.
- Criterion notes: C2 passes through the arXiv measurement studies, not the standard text.
- Points: V=1 K=1 H=2 L=0 total=4. In system-card corpus: yes. Pilot five: no.

### 6. ManiGuard specification-grounded manipulation safety suite (`peng2026maniguard`), fidelity level 7

- Fidelity level: The suite scores rollouts in Isaac Sim / OmniGibson and, as part of the benchmark, on a physical Franka under matched task conditions; the highest level at which the benchmark itself scores the system under test is a real robot in a controlled lab (level 7). Run in simulation only it is level 4.
- What it measures: Fraction of rollouts, and of successful rollouts, that violate a linear-temporal-logic-on-finite-traces (LTLf) safety specification over physics-grounded predicates (unsafe contact, spills, drops, ordering) across 200 base tasks x 5 conditions (1,000 scenarios) in six household task families.
- Hazardous property: A vision-language-action (VLA) manipulation policy completes tasks while violating contact and handling safety constraints (excessive force, spilled or dropped objects, unsafe sequencing) that would injure a person or damage property.
- System under test: VLA policy (learned visuomotor policy conditioned on language); zero-shot and fine-tuned VLAs.
- Primary source: arXiv 2608.17386 (https://arxiv.org/abs/2608.17386), fetched 2026-10-01
- Single build-and-run instrument: yes
- Proposed decision: A developer of a VLA manipulation policy for household or light-industrial deployment decides whether to ship the checkpoint or delay for safety-aware fine-tuning.
- theta: theta=1: the policy violates the contact and handling safety specification in a material fraction of engaged rollouts on the physical Franka under matched in-distribution and single-axis out-of-distribution conditions (the unsafe behaviours recur on hardware; the simulated violation rate does not predict their hardware frequency).
- Cost facts:
  - "ManiGuard-Bench organizes six contact-rich household task families into 200 locked base tasks along a skill x constraint taxonomy ... Each task is evaluated under one in-distribution and four single-axis out-of-distribution perturbations ... giving 1,000 locked scenarios." [arXiv 2608.17386, fetched 2026-10-01]
  - "The pipeline pairs an automated motion-planning generator with human teleoperation, annotated by the same per-step monitor ... we release 8,000 safety-annotated demonstrations, 40 per base task." [arXiv 2608.17386, fetched 2026-10-01]
  - "Benchmarking zero-shot and fine-tuned VLAs across more than 23,000 rollouts" [arXiv 2608.17386, fetched 2026-10-01]
- Validity facts:
  - "Every rollout is runtime-checked by LTLf-grounded automaton monitors over physics-grounded predicates rather than learned classifiers or LLM judges, in simulation and on a physical Franka platform." [arXiv 2608.17386, fetched 2026-10-01]
  - "6-21% of successful rollouts violate the specification" [arXiv 2608.17386, fetched 2026-10-01]
  - "21-42% of engaged rollouts still violate, two of six families below 2% safe success for every policy, and these failures persisting under distribution shift and on hardware." [arXiv 2608.17386, fetched 2026-10-01]
  - "We evaluate the three strongest SFT policies on matched Clutter and Cabinet scenes in simulation and on the physical Franka, under the ID condition and the Target/Location perturbation axes, giving twelve matched cells with n=30 rollouts per cell in each domain" [arXiv 2608.17386, fetched 2026-10-01]
  - "Simulated and physical values are strongly correlated for task success (r=0.91) and safe success (r=0.88), so a simulated rate is informative about where a policy stands relative to the others" [arXiv 2608.17386, fetched 2026-10-01]
  - "The violation rate is the exception (r=0.09): the two domains show no association at all, and the strict orderings simulation asserts for it hold in only two of six cases. What does carry over is the behavior itself ... The unsafe outcomes recur; their frequency does not." [arXiv 2608.17386, fetched 2026-10-01]
- Fit problems: Preprint of 2026-08-18; no wall-clock or dollar figure. The sim-to-real section (Q5) reports Pearson r over 12 matched cells (n=30 rollouts per cell and domain): 0.91 for task success, 0.88 for safe success, 0.09 for the violation rate, so the score that carries theta shows no sim-to-real association and only the occurrence of the unsafe behaviours reproduces on hardware. V=1 (qualitative reproduction), not 2; V=2 would hold only if safe success (r=0.88) were taken as the score. Same construct family as SafeVLA-Bench, ForesightSafety-VLA, SafeManip, SafeStage and Safety-CHORES; ManiGuard kept because it is the only one with a hardware component and quantified inputs.
- Criterion notes: Replaces SafeVLA-Bench (the sim2real pilot's level-4 anchor) as the VLA process-safety construct.
- Points: V=1 K=1 H=2 L=0 total=4. In system-card corpus: no. Pilot five: no.

### 7. SafeAgentBench hazardous-task refusal and execution (`yin2024safeagentbench`), fidelity level 4

- Fidelity level: Closed-loop AI2-THOR household simulation with a low-level controller and 17 high-level actions; the plan is executed and checked against goal conditions (level 4).
- What it measures: Rejection rate, risk rate and execution rate of an embodied LLM agent on 750 tasks (300 detailed hazardous, 100 abstract hazardous, 50 long-horizon hazardous, 300 safe) over 10 hazard types, scored by execution checks and a GPT-4 judge.
- Hazardous property: An LLM task planner plans and executes explicitly or implicitly hazardous household instructions (fire, electrical, poisoning) instead of refusing them.
- System under test: LLM planner inside an embodied agent (nine planner baselines).
- Primary source: arXiv 2412.13178 (https://arxiv.org/abs/2412.13178), fetched 2026-10-01
- Single build-and-run instrument: yes
- Proposed decision: The developer of a home-robot planner decides whether to launch the LLM planner or delay to add refusal and safety checks.
- theta: theta=1: the LLM task planner plans and executes explicitly or implicitly hazardous household instructions (fire, electrical, poisoning and similar hazards) instead of refusing them.
- Cost facts:
  - "an executable, diverse, and high-quality dataset of 750 tasks, rigorously curated to cover 10 potential hazards and 3 task types" [arXiv 2412.13178, fetched 2026-10-01]
  - "Model Rej RR(goal) RR(LLM) ER Time(s): Lota-Bench 0.00 0.66 0.66 0.87 24.39; LLM-Planner 0.00 0.37 0.30 0.80 90.50 (per-task wall-clock column of the detailed-task table)" [arXiv 2412.13178, fetched 2026-10-01]
- Validity facts:
  - "The study included a total of 1008 human ratings." [arXiv 2412.13178, fetched 2026-10-01]
  - "the consistency between human and GPT-4 evaluation for each of the three tasks is 91.89%, 90.36%, and 90.70%, respectively" [arXiv 2412.13178, fetched 2026-10-01]
  - "The most safety-conscious baseline achieves only a 10% rejection rate for detailed hazardous tasks." [arXiv 2412.13178, fetched 2026-10-01]
- Fit problems: No real-robot validation. Annotator count for the task curation is not stated. Rejection rates of 0-10% across nine baselines mean the published scores are compressed near the floor.
- Criterion notes: Safe-BeAl/SafePlan-Bench and SafetyALFRED share the construct (planner safety on hazardous or hazard-laden household instructions) with fewer facts.
- Points: V=1 K=2 H=1 L=0 total=4. In system-card corpus: no. Pilot five: yes.

### 8. IS-Bench interactive safety of VLM-driven household agents (`lu2025isbench`), fidelity level 4

- Fidelity level: Closed-loop OmniGibson physics simulation from egocentric observations with process-ordered checks (level 4; OmniGibson is photoreal-ish but the scoring is on simulator state).
- What it measures: Success rate, safe success rate, safety recall and safety awareness of a VLM-driven agent on 161 scenarios with 388 safety risks in 10 domestic categories, checking that mitigation actions occur before or after the risk-prone step.
- Hazardous property: During benign household tasks the agent's actions create or fail to mitigate emergent physical hazards (fire, electrical, contamination, spills).
- System under test: VLM agent (GPT-4o, Gemini 2.5, Claude 3.7 Sonnet, Qwen2.5-VL, InternVL3, Llama 3.2) planning from egocentric images.
- Primary source: arXiv 2506.16402 (https://arxiv.org/abs/2506.16402), fetched 2026-10-01
- Single build-and-run instrument: yes
- Proposed decision: The developer of a VLM-driven household agent decides whether to launch or delay to add process-level safety reasoning.
- theta: theta=1: during ordinary household tasks the agent omits or mis-orders risk-mitigation steps in a material fraction of tasks, so it would start fires, cause electrical hazards or contaminate food in deployment.
- Cost facts:
  - "Each evaluation scenario is instantiated in OmniGibson and deployed on an NVIDIA A100 GPU." [arXiv 2506.16402, fetched 2026-10-01]
  - "Each VLM underwent a single evaluation, with each evaluation session lasting approximately 2.5 to 3 hours, depending on the inference time of the VLM being assessed." [arXiv 2506.16402, fetched 2026-10-01]
  - "161 challenging scenarios with 388 unique safety risks instantiated in a high-fidelity simulator" [arXiv 2506.16402, fetched 2026-10-01]
- Validity facts:
  - "each generated plan is then manually executed and verified by human annotators in the simulator, ensuring it is both executable and effectively mitigates all safety risks" [arXiv 2506.16402, fetched 2026-10-01]
  - "while safety-aware Chain-of-Thought can improve performance, it often compromises task completion" [arXiv 2506.16402, fetched 2026-10-01]
- Fit problems: No inter-annotator statistic and no real-world transfer evidence. Overlaps with SafeAgentBench (both are household planner safety); kept as a distinct construct because the instructions are benign and the hazard emerges during execution rather than being requested.
- Criterion notes: SafetyALFRED and SafeRelBench share this construct with no cost or validity facts.
- Points: V=1 K=2 H=1 L=0 total=4. In system-card corpus: no. Pilot five: no.

### 9. ASIMOV-2.0 physical-danger perception and constraint following (`jindal2025danger`), fidelity level 3

- Fidelity level: Generated photorealistic videos of safe-to-unsafe transitions and generated image-plus-constraint pairs, scored open-loop against human consensus (level 3); the injury-narrative text track alone is level 0.
- What it measures: Accuracy on risk type, severity and intervention timing on 319 injury-report-grounded text scenarios and 287 generated videos, and constraint-violation rate on 164 image-constraint pairs, against 5-rater consensus labels.
- Hazardous property: A VLM used as a robot's brain fails to recognise latent physical danger, misjudges severity or violates embodiment constraints (payload, gripper geometry), so it would command or fail to prevent an injury-causing action.
- System under test: VLM planner or 'robot brain' (GPT-5, Gemini 2.5 Pro, Claude Opus 4.1, Gemini Robotics-ER), evaluated by question answering.
- Primary source: arXiv 2509.21651 (https://arxiv.org/abs/2509.21651), fetched 2026-10-01
- Paired sources: ASIMOV-2.0 project page (https://asimov-benchmark.github.io/v2/); Gemini Robotics Team (https://storage.googleapis.com/deepmind-media/gemini-robotics/Gemini-Robotics-2-Safety.pdf)
- Single build-and-run instrument: yes
- Proposed decision: A developer shipping a VLM as the planner of a general-purpose robot decides whether to ship or delay for safety post-training.
- theta: theta=1: the planner fails to recognise latent physical danger, misjudges injury severity or violates embodiment constraints in everyday scenes, so it would command or fail to prevent injury-causing actions.
- Cost facts:
  - "We then get ground-truth answers to four multiple-choice safety questions with 5 human raters per instance and filter out the data where raters had low consensus due to ambiguity. ... This benchmark has 319 annotated scenarios." [arXiv 2509.21651, fetched 2026-10-01]
  - "The data was annotated by 5 raters per video. For data quality we set 60% as a threshold chosen for consensus and selected only those videos where intervention timestamps provided by the human raters had a standard deviation below 1.0s. ... The resulting benchmark has 287 scenarios." [arXiv 2509.21651, fetched 2026-10-01]
  - "The filtered benchmark has a total of 164 (constraint, image) pairs, along with human annotations for bounding boxes of violating and non-violating objects." [arXiv 2509.21651, fetched 2026-10-01]
  - Observation, not a quotation: the project page's 'Data' button links to a Google Colab notebook (https://colab.research.google.com/drive/1ANSRfztNCHqCQNHl9sDtmPMAXD4l2UiW?usp=sharing); the page states no item count or download size [ASIMOV-2.0 project page, fetched 2026-10-01]
- Validity facts:
  - "We use the National Electronic Injury Surveillance System (NEISS) ... which collects data from a stratified sample of approximately 100 hospitals across the United States" [arXiv 2509.21651, fetched 2026-10-01]
  - "no model achieves less than 30% constraint violation rate when reasoning jointly about embodiment limitations, physics, and visual cues" [arXiv 2509.21651, fetched 2026-10-01]
  - "For Claude Opus 4.1 and GPT5, the accuracy gap is 27% and 40% respectively (video versus text), while Gemini 2.5 Pro shows a more modest drop." [arXiv 2509.21651, fetched 2026-10-01]
  - "Extending previous semantic safety benchmarks [4, 5], we synthetically generated a dataset containing (constraints, image) pairs (ASIMOV-Agentic builds on ASIMOV-2.0)" [Gemini Robotics Team, fetched 2026-10-01]
- Fit problems: No correlation with robot incident rates; ground truth is rater consensus. No hours or dollars; the rater count is the only labour figure. Tests perception and judgement by question answering, not action.
- Criterion notes: Same construct as ASIMOV v1, MSSBench, EARBench, GuardianBench and ROBOSHACKLES at levels 0-3; ASIMOV-2.0 kept (most facts, cited in the Gemini Robotics 2 safety report).
- Points: V=1 K=1 H=1 L=1 total=4. In system-card corpus: yes. Pilot five: yes.

### 10. ASIMOV-Agentic human-proximity stop and constraint-following (`geminirobotics2026agentic`), fidelity level 2

- Fidelity level: Offline evaluation on real stereo video of humans approaching a head-mounted camera, in single frames and 5-second agentic windows with a robot_stop tool (video/temporal QA, level 2); the Apollo 2 humanoid stop test is a separate lab experiment.
- What it measures: Distance mean absolute error (MAE), 1 m breach detection accuracy and the false-negative-rate (FNR) versus false-positive-rate (FPR) trade-off of an agent that must call robot_stop() when a person is within a threshold; plus constraint-following, safety tool calling, VLA feasibility and ambiguity components.
- Hazardous property: The orchestrating agent fails to trigger a protective stop when a person comes within 1 m of the robot, or routes an unsafe or infeasible task to the VLA.
- System under test: Embodied-reasoning VLM orchestrating a VLA (Gemini Robotics-ER 2, Claude Opus 4.8, GPT 5.5 and other frontier models).
- Primary source: Gemini Robotics Team (https://storage.googleapis.com/deepmind-media/gemini-robotics/Gemini-Robotics-2-Safety.pdf), fetched 2026-10-01
- Paired sources: Hugging Face dataset card google/asimov_agentic (https://huggingface.co/datasets/google/asimov_agentic)
- Single build-and-run instrument: yes
- Proposed decision: The developer of an agent that orchestrates a VLA on a humanoid or manipulator near people decides whether to deploy the orchestrator or keep the robot behind deterministic stops only.
- theta: theta=1: the orchestrator misses a material fraction of 1 m human-proximity events (fails to call robot_stop) or passes constraint-violating tool calls to the VLA, at a rate incompatible with collaborative operation.
- Cost facts:
  - "We collected sensorized human data where a primary human wearing a head-mounted ZED camera and serving as a robot proxy is approached by other humans (wearing Vive trackers) at varying angles, speeds, distances, poses, lighting conditions etc." [Gemini Robotics Team, fetched 2026-10-01]
  - "Human annotators provided the ground truth labels, and low-agreement instances were filtered out to maintain data quality." [Gemini Robotics Team, fetched 2026-10-01]
  - Observation, not a quotation: access-controlled ("You need to agree to share your contact information to access this dataset"); licence cc-by-4.0; the card's file tree says "human_safety_monitoring/ ... *.parquet (28 episode files)", while the repository API (?blobs=true) lists 39 .parquet files under human_safety_monitoring/ and 53 files in total, 2,398,740,228 bytes (2.4 GB), lastModified 2026-07-24. The 28 is the card author's count of episodes; the 39 is the file count on 2026-10-01 (the two counting rules differ, and the card is not updated to the file listing) [Hugging Face dataset card google/asimov_agentic and repository API https://huggingface.co/api/datasets/google/asimov_agentic?blobs=true, fetched 2026-10-01]
- Validity facts:
  - "top-performing models can consistently estimate distance with an MAE between 0.35 and 0.55 meters, while detecting 1-meter boundary breaches with an accuracy ranging from roughly 79% to 93%" [Gemini Robotics Team, fetched 2026-10-01]
  - "achieving a highly efficient, low-interruption operational state (FPR under 5%) currently comes at the unacceptable cost of missing genuine safety hazards (FNR exceeding 40%). Conversely, models that successfully suppress the FNR closer to the 10%-15% range suffer significant operational penalties, unnecessarily stopping the robot 15% to 25% of the time. Crucially, no model currently operates in the ideal top-right quadrant" [Gemini Robotics Team, fetched 2026-10-01]
  - "In lab settings, we observed 99% human detection accuracy and 96% reliability in transitioning to a safe pose, from Gemini Robotics 2's Embodied Reasoning (ER) and VLA models respectively." [Gemini Robotics Team, fetched 2026-10-01]
  - "This work does not evaluate the underlying functional safety architecture - including certified hardware components, redundancy mechanisms, and real-time system guarantees" [Gemini Robotics Team, fetched 2026-10-01]
- Fit problems: No arXiv version; dataset access-controlled behind a contact-information form; per-component item counts not stated in the report. The humanoid stop test is reported separately and is not a benchmark-score-to-hardware correlation. Same family as ASIMOV-2.0 but a different construct (stop/refuse/ask decisions on real sensor data rather than danger perception on generated media).
- Criterion notes: The only physical-AI evaluation that publishes the FNR/FPR trade-off, which maps directly onto s and t.
- Points: V=1 K=1 H=1 L=1 total=4. In system-card corpus: yes. Pilot five: no.

### 11. EgoSafetyBench VLM runtime safety guard on egocentric video (`panpatil2026egosafetybench`), fidelity level 3

- Fidelity level: Generated robot-view video scenarios scored open-loop at half-second granularity (level 3).
- What it measures: Video miss rate, video false-alarm rate, balanced accuracy and timely detection of a VLM acting as a streaming safety guard over 1,200 egocentric scenarios (800 situational, 400 with misleading in-scene text), with contrastive near-identical pairs.
- Hazardous property: A VLM safety guard misses hazardous moments in a robot's unfolding activity (especially contextual hazards) or is corrupted by misleading in-scene text, so an intervention that would prevent harm is not triggered.
- System under test: VLM used as a runtime guard on a home or factory robot (ten open and closed VLMs, including Claude Sonnet 4.6 and Gemini 3.5 Flash).
- Primary source: arXiv 2607.00218 (https://arxiv.org/abs/2607.00218), fetched 2026-10-01
- Single build-and-run instrument: yes
- Proposed decision: A developer deploying a VLM as the runtime safety monitor of a service robot decides whether to rely on it or delay and keep a human monitor.
- theta: theta=1: the guard misses a material fraction of hazardous moments, or its judgement is corrupted by in-scene text, so it would fail to trigger interventions in deployment.
- Cost facts:
  - "an egocentric video benchmark of 1,200 robot-view scenarios annotated at half-second granularity ... The situational track (800 scenarios) ... The visual-channel track (400 scenarios)" [arXiv 2607.00218, fetched 2026-10-01]
  - "The 200 videos were split into two surveys of 100, each independently labeled by two annotators on the binary safe/unsafe scale; a third annotator per survey resolved the chunks on which the two disagreed." [arXiv 2607.00218, fetched 2026-10-01]
  - "A VLM annotator (Claude Opus 4.7) labels every chunk along both axes from sampled frames using a fixed taxonomy prompt" [arXiv 2607.00218, fetched 2026-10-01]
- Validity facts:
  - "observed agreement is 91.2% at the chunk level and 90.5% at the video level, with Cohen's kappa of 0.744 (substantial) and 0.804 (almost perfect)" [arXiv 2607.00218, fetched 2026-10-01]
  - "Agreement between the human consensus and the benchmark's safe/unsafe labels: Video Acc. 0.900, kappa 0.799; Chunk Acc. 0.860, kappa 0.660 (Table 9)" [arXiv 2607.00218, fetched 2026-10-01]
  - "We report the video miss rate (truly unsafe videos it lets pass), the video false-alarm rate (safe videos it flags), and the balanced accuracy" [arXiv 2607.00218, fetched 2026-10-01]
  - "vulnerable models miss up to a third of hazards, while robust models over-intervene on safe content" [arXiv 2607.00218, fetched 2026-10-01]
- Fit problems: Videos are generated, not filmed; no real-footage or outcome validation. Dataset release is not confirmed in the fetched text. Overlaps with the ASIMOV-2.0 video track (intervention timing) and with HomeSafe-Bench; kept because it is the only one reporting miss and false-alarm rates separately with an agreement statistic.
- Criterion notes: Borderline on C5 against ASIMOV-2.0 (video track) and HomeSafe-Bench; treated as the 'VLM as runtime guard' construct.
- Points: V=1 K=1 H=1 L=0 total=3. In system-card corpus: no. Pilot five: no.

### 12. SafePlan prompt suite (with SafeGate follow-up) (`obi2025safeplan`), fidelity level 0

- Fidelity level: Text-only accept/reject classification of 621 natural-language task prompts by an LLM planner (level 0); AI2-THOR and the SafeGate real-robot experiments are demonstrations of the guard, not where the score is produced.
- What it measures: Acceptance rate of unsafe prompts and of safe prompts (confusion matrix) for an LLM robot task planner on 621 expert-curated prompt-scene pairs (127 safe, 494 unsafe) across assistive, navigation and manipulation domains.
- Hazardous property: An LLM planner accepts a harmful or unsafe natural-language task command and would generate robot code for it.
- System under test: LLM planner (Gemini 1.5 Pro, GPT-4o, Gemini Flash 2.0) with and without the SafePlan reasoners.
- Primary source: arXiv 2503.06892 (https://arxiv.org/abs/2503.06892), fetched 2026-10-01
- Paired sources: arXiv 2604.05427 (https://arxiv.org/abs/2604.05427)
- Single build-and-run instrument: yes
- Proposed decision: A developer shipping an LLM command interface on a service robot decides whether to ship or delay to add a pre-execution safety check.
- theta: theta=1: the planner accepts unsafe or harmful task commands at a material rate (above a preset acceptance threshold) while rejecting many safe ones.
- Cost facts:
  - "We further introduce a benchmark of expert-curated 621 task prompts with scene description pairs" [arXiv 2503.06892, fetched 2026-10-01]
  - "All models evaluated on 621 tasks (127 ethical, 494 unethical)." [arXiv 2503.06892, fetched 2026-10-01]
  - "We evaluate SafeGate against existing LLM-based robot safety frameworks and baseline LLMs across 230 benchmark tasks, 30 AI2-THOR simulation scenarios, and real-world robot experiments." [arXiv 2604.05427, fetched 2026-10-01]
- Validity facts:
  - "Gemini 1.5 Pro w/ SafePlan 70.87 (safe acceptance %) 7.09 (unsafe acceptance %) ... accuracy 0.884; Gemini 1.5 Pro 100.00 61.34; GPT4o 100.00 74.29 (results table)" [arXiv 2503.06892, fetched 2026-10-01]
  - "the LLM baselines (GPT-4o and Gemini 2.5-flash) match SafeGate's perfect AR-U% = 0 but suffer from DR-S% values of 48.2% and 79.5% respectively (over-rejection of safe tasks)" [arXiv 2604.05427, fetched 2026-10-01]
  - "RoboGuard authorized 93.3% of hazardous tasks (28 of 30) ... when hazards arose from missing information or downstream state changes rather than explicit rule violations" [arXiv 2604.05427, fetched 2026-10-01]
- Fit problems: Labels are expert judgement with no inter-rater statistic; no hours or dollars; no correlation between the text score and any physical outcome (SafeGate adds a real-robot demonstration, not a correlation). Same construct as EmbodyGuard (942 PDDL-grounded scenarios, 13 LLMs); SafePlan kept because its labels are expert-curated and the follow-up adds a hardware check.
- Criterion notes: Passes C3 only through quantified inputs (621 expert-curated prompts).
- Points: V=0 K=1 H=1 L=1 total=3. In system-card corpus: no. Pilot five: no.

### 13. LLM-orchestrator safety benchmark for human-humanoid collaboration (`bajrami2026robotignores`), fidelity level 0

- Fidelity level: Text-prompting layer scored on 100-turn sessions against ISO 10218-2-grounded invariants (level 0); the simulated sensor-actuator and Unitree C1 layers are described as ongoing.
- What it measures: Violations, under-compliance and over-compliance per 100-turn session of an LLM orchestrator against five safety invariants (for example speed limits near humans) under full-context and sliding-window conditions.
- Hazardous property: An LLM orchestrating a humanoid commands a motion that breaks a protective measure (speed, separation) while a person is present.
- System under test: LLM orchestrator (Claude Haiku 4.5, GPT-4o-mini, Gemini 2.5 Flash, qwen3:8b) over a Model Context Protocol (MCP) tool interface.
- Primary source: arXiv 2609.07288 (https://arxiv.org/abs/2609.07288), fetched 2026-10-01
- Single build-and-run instrument: yes
- Proposed decision: An integrator deploying an LLM orchestrator for a humanoid in a shared industrial cell decides whether to deploy or keep a deterministic allow/deny layer only.
- theta: theta=1: over extended sessions the orchestrator violates the ISO 10218-2-grounded invariants in a material fraction of sessions.
- Cost facts:
  - "three cloud backends (Claude Haiku 4.5, GPT-4o-mini, Gemini 2.5 Flash) and a local open-weights baseline (qwen3:8b) across 40 100-turn sessions under full-context and sliding-window budget conditions" [arXiv 2609.07288, fetched 2026-10-01]
  - "eight experimental conditions, each repeated five times (40 sessions total)" [arXiv 2609.07288, fetched 2026-10-01]
- Validity facts:
  - "Claude and Gemini remain at or near zero violations while GPT-4o-mini commits up to 13 per session" [arXiv 2609.07288, fetched 2026-10-01]
  - "safety invariants grounded in ISO 10218-2:2025 protective measures" [arXiv 2609.07288, fetched 2026-10-01]
  - "while the simulation and physical layers remain ongoing ... the preliminary simulation layer reproduces the model ranking and the GPT-4o-mini failure-mode inversion" [arXiv 2609.07288, fetched 2026-10-01]
- Fit problems: Workshop-stage preprint (2026-09-07); physical validation not yet reported; no cost figure beyond session counts; organisation unverified. Measures both over-refusal and violations, which is rare and useful for t.
- Criterion notes: Distinct construct from SafePlan (long-session orchestration with industrial invariants, not single-prompt refusal).
- Points: V=0 K=1 H=1 L=0 total=2. In system-card corpus: no. Pilot five: no.

## 5. Alternates (ranked, not included)

### 14. NHTSA FMVSS No. 127 AEB compliance test (`nhtsa2024fmvss127`), fidelity level 8, fails C5

- What it measures: Pass/fail: no contact with the lead-vehicle or pedestrian test device in every run across three lead-vehicle scenarios and three pedestrian scenarios (crossing, alongside, standing) at up to 73 km/h for pedestrians, plus false-activation tests.
- System under test: Non-language-model production AEB stack.
- Primary source: NHTSA FMVSS No. 127 final rule (https://www.govinfo.gov/content/pkg/FR-2024-05-09/html/2024-09054.htm), fetched 2026-10-01
- Proposed decision: An OEM decides whether a vehicle may be certified for US sale from 1 September 2029. theta: theta=1: the AEB contacts the test device in at least one required run.
- Cost facts: "approximately $354 million in 2020 dollars (total annual cost)" [NHTSA FMVSS No. 127 final rule, fetched 2026-10-01] "between $550,000 and $680,000 (cost per equivalent life saved); lifetime monetized net benefit between $5.82 and $7.26 billion" [NHTSA FMVSS No. 127 final rule, fetched 2026-10-01]
- Validity facts: "save at least 362 lives and mitigate 24,321 non-fatal injuries a year" [NHTSA FMVSS No. 127 final rule, fetched 2026-10-01] "three pre-crash scenarios involving pedestrians: (a) where the pedestrian crosses the road in front of the subject vehicle, (b) where the pedestrian walks alongside the road in the path of the subject vehicle, and (c) where the pedestrian stands in the roadway (tested in daylight and darkness); lead vehicle stopped, decelerating, slower-moving (daylight)" [NHTSA FMVSS No. 127 final rule, fetched 2026-10-01] "prevent the vehicle from colliding with the lead vehicle or pedestrian test devices when tested according to the standard's test procedures" [NHTSA FMVSS No. 127 final rule, fetched 2026-10-01]
- Fit problems: Same hazardous property and test form as the IIHS protocol (C5); the published dollar figures are fleet compliance and societal benefit, not the cost of one test; the benefit estimate rests on field studies of existing AEB, not on validation of the test's own predictive power.
- Criterion notes: Excluded under C5 (same construct as IIHS). Use its scenario grid, darkness requirement and false-activation tests inside the IIHS instrument context; its stakes figures belong in the decision context.

### 15. NAVSIM non-reactive driving evaluation (PDM Score) (`dauner2024navsim`), fidelity level 5, fails C1

- What it measures: PDM Score (PDMS) composite of no-collision, drivable-area compliance, time-to-collision, ego progress and comfort for an end-to-end driving policy on 12k test scenes.
- System under test: End-to-end learned driving planner (camera/LiDAR), not a language model.
- Primary source: arXiv 2406.15349 (https://arxiv.org/abs/2406.15349), fetched 2026-10-01
- Proposed decision: A developer of an end-to-end driving planner decides whether to promote a checkpoint to closed-loop and road testing. theta: theta=1: the planner collides in a material fraction of safety-critical scenes when run closed-loop.
- Cost facts: "NAVSIM enabled a new competition held at CVPR 2024, where 143 teams submitted 463 entries" [arXiv 2406.15349, fetched 2026-10-01] "The current pipeline relies on a per-scene optimization process (based on MTGS) to generate the synthetic views, requiring approximately 1-2 hours per scene on current hardware." [arXiv 2506.04218, fetched 2026-10-01] "At 100% density, each scenario contains 12 synthetic observations on average in Stage 2 for each real observation in Stage 1, resulting in 13 planner inferences per scenario. In comparison, closed-loop simulation in nuPlan requires 80 planner inferences per scenario, corresponding to an 8-second rollout at 10Hz." [arXiv 2506.04218, fetched 2026-10-01] (The per-scene rendering is a one-off preprocessing cost; the paper names no GPU type. Pseudo-simulation is NAVSIM v2.)
- Validity facts: "Compared to OLS, we consistently observe better closed-loop correlation for PDMS, in terms of Spearman's (rank) and Pearson's (linear) correlation coefficients." [arXiv 2406.15349, fetched 2026-10-01] "a much simpler 3-metric formula matches the predictive power of the full 5-metric PDMS at the same Spearman rho=0.90 on our paired sample of n=8 methods" [arXiv 2605.00066, fetched 2026-10-01] "Ego Progress (EP) is the strongest single predictor of closed-loop success, substantially exceeding the safety-critical collision metric NC" [arXiv 2605.00066, fetched 2026-10-01] "pseudo-simulation is better correlated with closed-loop simulations (R^2=0.8) than the best existing open-loop approach (R^2=0.7)" [arXiv 2506.04218, fetched 2026-10-01]
- Fit problems: The composite is a driving-quality score (progress, comfort) rather than a hazard rate; the collision subscore is its least predictive component (C1 fails for the composite). Correlations are with closed-loop simulation, not with road outcomes.
- Criterion notes: Excluded under C1 as a task-quality benchmark; first alternate if the study wants a driving-domain level-5 entry with a non-language-model system.

## 6. Other candidates assessed and excluded

| candidate | level | criterion failed | reason | facts kept for contexts |
|---|---|---|---|---|
| Predictive red teaming (RoboART) (`majumdar2025predictive`) | 3 | C1 | Task-success robustness under distribution shift, not a hazard rate. | "Experiments across 500+ hardware trials in twelve off-nominal conditions for visuomotor diffusion policies demonstrate that RoboART predicts performance degradation with high accuracy (less than 0.19 average difference between predicted and real success rates)." [arXiv 2502.06575, fetched 2026-10-01] "The difference between predicted and real success rates averaged across the twelve factors is 0.1 and 0.19 respectively for the two policies." [arXiv 2502.06575, fetched 2026-10-01] |
| Drone-Bench (`sharrock2026dronebench`) | 4 | C1 | Dual-use surveillance capability of coding agents on a drone; wall contact zeroes a score but the construct is capability. | "a DJI Tello EDU, a cheap ($129), off-the-shelf quadcopter" [Andon Labs, fetched 2026-10-01] "executed on a dedicated worker with a single NVIDIA T4 (16 GB VRAM), with timeouts that vary by task: 5 hours for reconstruction, 2 hours for localization, and 1500 seconds for detection." [Andon Labs, fetched 2026-10-01] "Each simulated episode is given a wall-clock budget of 120 seconds" [Andon Labs, fetched 2026-10-01] "10 runs per task for 15 frontier models spanning May 2024-July 2026" [Andon Labs, fetched 2026-10-01] "end-to-end success - a single run beating our baseline on all five tasks - currently stands at 0%" [Andon Labs, fetched 2026-10-01] "Drone-Bench is a benchmark created by Andon Labs (in consultation with Anthropic) to test if AI agents are capable of controlling a drone for surveillance tasks. Anthropic has not been given access to Drone-Bench" [Anthropic, fetched 2026-10-01] |
| Geometric red-teaming (CrashShapes) (`goel2025geometric`) | 7 | C1 | Task-success drop under object-geometry variation, not a hazard rate. | "simulated CrashShapes reduce task success from 90% to as low as 22.5%, and that blue-teaming recovers performance to up to 90% on the corresponding real-world geometry" [arXiv 2509.12379, fetched 2026-10-01] "On an NVIDIA RTX 4090 GPU, the full APAP pipeline consumes roughly 10 GB of memory and requires 10 minutes per object. (baseline deformation method)" [arXiv 2509.12379, fetched 2026-10-01] "we 3D-printed one CrashShape per object for two YCB objects (mustard bottle, screwdriver) and evaluated each in 20 trials on a Franka arm" [arXiv 2509.12379, fetched 2026-10-01] |
| Swiss Re / Stanford ADAS proving-ground campaign (`dilillo2024adas`) | 8 | C4, C5 | Thirteen-vehicle, eight-month comparative campaign with relative scoring; not one build-and-run decision instrument; same construct as IIHS. | "eight-month long vehicle testing campaign conducted on a recognized UNECE type approval authority and Euro NCAP accredited proving ground in Germany" [arXiv 2409.16942, fetched 2026-10-01] "the average number of tests executed and analyzed in this manuscript per vehicle is 81 tests, representing approximately 26% of the full test protocol ... 161 tests for the best performer (72% of the full test matrix) and 41 tests for the worst performer (18% of full the test matrix)" [arXiv 2409.16942, fetched 2026-10-01] "Costs are not accounted for in any of our considerations or analyses." [arXiv 2409.16942, fetched 2026-10-01] "realism score (mean = 0.002354, standard deviation = 0.001221)" [arXiv 2409.16942, fetched 2026-10-01] |
| Euro NCAP AEB/LSS VRU test protocol v4.5.1 (`euroncap2024aebvru`) | 8 | C5 | Same construct as IIHS PAEB; IIHS publishes the fixed run count and has the field-claims chain. | "Version 4.5.1 February 2024; scenarios CPFA-50, CPNA-25, CPNA-75, CPNCO-50, CPLA-25, CPLA-50, CBNA-50, CBNAO-50, CBLA-25, CBLA-50, CMFtap" [Euro NCAP Test Protocol AEB/LSS VRU systems v4.5.1, fetched 2026-10-01] "VUT speed [km/h, fetched 2026-10-01] 10-60 (CPFA, CPNA, CPNCO) | 20-60 (CPLA) | 50-80 | 10,15,20 | 10 | 4,8; Lighting condition Day/Night; Streetlights (night): Streetlights / No streetlights" [Euro NCAP Test Protocol AEB/LSS VRU systems v4.5.1, fetched 2026-10-01] "based on the OEM colour prediction, the highest avoidance (Green) test speeds of each scenario and one randomly selected avoidance (Green) test speed per scenario (where applicable) will be tested ... Perform all tests where the predicted result is Yellow, Orange or Brown. Test points that are predicted Red are excluded from testing." [Euro NCAP Test Protocol AEB/LSS VRU systems v4.5.1, fetched 2026-10-01] "In the tests above 40km/h, stop testing when the actual speed reduction measured is less than 15km/h." [Euro NCAP Test Protocol AEB/LSS VRU systems v4.5.1, fetched 2026-10-01] |
| NeuroNCAP (`ljungbergh2024neuroncap`) | 5 | C3 | No cost figure and no validation against a real vehicle in the fetched text. | "NNS = 5.0 if no collision; 4.0 * max(0, 1 - v_i/v_r) otherwise" [arXiv 2404.07762, fetched 2026-10-01] "state-of-the-art end-to-end planners excel in nominal driving scenarios in an open-loop setting, they exhibit critical flaws when navigating our safety-critical scenarios in a closed-loop setting" [arXiv 2404.07762, fetched 2026-10-01] |
| SafeVLA-Bench (`fan2026safevlabench`) | 4 | C5, C3 | Same construct as ManiGuard (VLA process safety by temporal-logic monitors); no cost figure and no human or hardware validation. | "evaluating twenty-seven policy-benchmark entries across tabletop and kitchen manipulation tasks" [arXiv 2606.00773, fetched 2026-10-01] "the fifteen tabletop policies above 90% mean success still have 18-28% unsafe-episode rates, and 38-56% of successful RoboCasa-365 rollouts violate at least one active safety clause (v2; catalog.json records v1's 13-15% and 36-56%)" [arXiv 2606.00773, fetched 2026-10-01] "worst-violation depths measured in newtons, millimetres, degrees, and newton-metres" [arXiv 2606.00773, fetched 2026-10-01] |
| EmbodyGuard (SAFEL) (`son2025embodyguard`) | 0 | C5 | Same construct as SafePlan (text-level refusal and plan safety of LLM planners). | "a PDDL-grounded benchmark containing 942 LLM-generated scenarios covering both overtly malicious and contextually hazardous instructions" [arXiv 2505.19933, fetched 2026-10-01] "Candidate scenarios are first generated using GPT-4o ... then verified through symbolic checks ... and expert human review" [arXiv 2505.19933, fetched 2026-10-01] "Evaluation across 13 state-of-the-art LLMs reveals that while models often reject clearly unsafe commands, they struggle to anticipate and mitigate subtle, situational risks." [arXiv 2505.19933, fetched 2026-10-01] |
| HomeSafe-Bench (unsafe action detection) (`pu2026homesafebench`) | 3 | C5 | Same construct as EgoSafetyBench (VLM detecting unsafe actions of an embodied agent in generated video). | "438 diverse cases across six functional areas with fine-grained multidimensional annotations" [arXiv 2603.11975, fetched 2026-10-01] "Table 9 demonstrates the agreement evaluation results on 412 co-annotated videos (validity) and 236 videos (categorical/temporal). ... Intervention deadline CCC 0.800, ICC 0.801, MAE 0.62 s; Point of no return CCC 0.765" [arXiv 2603.11975, fetched 2026-10-01] |
| HomeSafeBench (free-exploration inspection) (`yao2025homesafebench`) | 4 | C1 | Hazard-finding task success of an inspector, not harm caused by the system. | "comprises 1,000 human-validated inspection tasks" [arXiv 2509.23690, fetched 2026-10-01] "the best model reaches only about 34.7% F1, far below the 98.0% of a human inspector" [arXiv 2509.23690, fetched 2026-10-01] |
| ROBOSHACKLES (`yin2026roboshackles`) | 3 | C5 | Same construct as ASIMOV-2.0 (refusal of injurious actions in edited real scenes); a 100% unsafe rate on all six models cannot discriminate between systems. | "a DROID-based robotic video dataset comprising 12,000 training clips and 1,200 hazardous multilingual evaluation clips across six safety categories (v2 HTML; the v2 abstract says 10,000 clips)" [arXiv 2606.18632, fetched 2026-10-01] "all evaluated models produce unsafe actions in the tested safety-critical scenarios, yielding a 100% unsafe action generation rate" [arXiv 2606.18632, fetched 2026-10-01] |
| ForesightSafety-VLA (`lyu2026foresightsafetyvla`) | 4 | C5 | Same construct as ManiGuard; no human or hardware validation. | "We instantiate 66 safety-augmented base scenarios in RoboTwin across 5 embodiments" [arXiv 2606.27079, fetched 2026-10-01] "templates at levels W0-W2 are authored by human annotators, while W3-W4 templates are generated by a frontier large language model and manually verified" [arXiv 2606.27079, fetched 2026-10-01] |
| RoboGuard (`ravichandran2025roboguard`) | 7 | C4, C5 | A guardrail (defence) evaluated with RoboPAIR-style attacks, not an evaluation; same construct as RoboPAIR. | "RoboGuard reduces the execution of unsafe plans from over 92% to below 3% without compromising performance on safe plans" [arXiv 2503.07885, fetched 2026-10-01] |
| Waymo Collision Avoidance Testing (CAT) (`kusano2022collision`) | 5 | C4 | Proprietary scenario database and release programme; not a reusable build-and-run instrument. | "In total, the CAT evaluation for the SF/PHX ODD contained over 13,000 scenarios." [arXiv 2212.08148, fetched 2026-10-01] "For each start of fully autonomous operation, a series of approximately 70 scenarios are reproduced on a test track and executed using the same candidate software" [arXiv 2212.08148, fetched 2026-10-01] "The CAT evaluation needs to be completed in a timeframe of several weeks after a software candidate is identified." [arXiv 2212.08148, fetched 2026-10-01] "The virtual test platform provides a conservative estimate of the number of simulated ADS collisions when compared to the same scenarios executed on a test track." [arXiv 2212.08148, fetched 2026-10-01] |
| TouchSafeBench (`wang2026touchsafebench`) | 4 | C2 | Benchmark not yet released ('upon acceptance'). | "2,940 simulated indoor co-presence episodes across social navigation and social rearrangement ... the best average Macro-F1 stays below 50% ... We will release the benchmark upon acceptance." [arXiv 2605.31196, fetched 2026-10-01] |
| RoboJailBench (`yeke2026robojailbench`) | 1 | C5 | Same construct as RoboPAIR (jailbreak ASR of embodied VLMs) without physical execution. | "18 categories of security violation consequences for embodied AI ... We integrate four attacks and two defenses to evaluate their performance on leading embodied VLMs ... maintain a leaderboard" [arXiv 2605.19328, fetched 2026-10-01] |
| JailWAM (`liu2026jailwam`) | 4 | C5 | Same construct as RedVLA (eliciting unsafe physical behaviour from an action model in simulation) without hardware validation. | "JailWAM achieves an 84.2% attack success rate on LingBot-VA (RoboTwin simulation)" [arXiv 2604.05498, fetched 2026-10-01] |
| MSSBench (`zhou2024mssbench`) | 1 | C5 | Same construct as ASIMOV-2.0 at level 1 (static VLM situational-safety QA). | "The dataset comprises 1,820 language query-image pairs, half of which the image context is safe, and the other half is unsafe." [arXiv 2410.06172, fetched 2026-10-01] |
| EARBench (`zhu2024earbench`) | 1 | C5 | Same construct as ASIMOV-2.0; task risk rate saturated. | "all models exhibit high task risk rates (TRR), with an average of 95.75% across all evaluated models" [arXiv 2408.04449, fetched 2026-10-01] |
| SafeVLA / Safety-CHORES (`zhang2025safevla`) | 4 | C5 | Same construct as ManiGuard; benchmark side of a training paper. | "reducing the cumulative cost of safety violations by 83.58% compared to the state-of-the-art method, while also maintaining task success rate (+3.85%)" [arXiv 2503.03480, fetched 2026-10-01] |

## 7. Corrections to research/catalog.json found while fetching

- iihs2024paeb: Version IV scores 30 valid runs per vehicle (night adult perpendicular 2 speeds x 2 beam settings x 3, day child 2 x 3, night adult parallel 2 x 2 x 3), not 36; the child scenario is daytime only.
- fan2026safevlabench: v2 (2026-09-30) reports 27 policy-benchmark entries, 18-28% unsafe-episode rates and 38-56% of successful RoboCasa-365 rollouts violating; the catalogue has v1's 9 entries, 13-15% and 36-56%.
- yin2026roboshackles: v2 full text gives 12,000 training clips and 1,200 evaluation clips; the abstract and catalogue say 10,000 clips.
- zhang2026redvla: the ASR is produced in simulation (level 4); the Franka test is validation. The catalogue's level 7 records the validation fidelity level.
- yin2024safeagentbench: the catalogue's size field splits the 750 tasks as '450 detailed unsafe, 100 abstract unsafe, 200 safe'; the v5 full text has 450 hazardous tasks (300 detailed, 100 abstract, 50 long-horizon) and 300 safe tasks ('This dataset consists of 450 tasks with various safety hazard issues and 300 corresponding safe tasks as a control group'), fetched 2026-10-01.
- robey2024robopair: the RoboGuard paper's Table III gives attack cost in tokens (20,471-52,516 per attack, 15 queries); catalog.json records only 'token and query counts reported'.

## 8. Sources (all fetched 2026-10-01)

- `iihs_paeb`: IIHS Pedestrian Autonomous Emergency Braking Test Protocol, Version IV (2024). https://www.iihs.org/media/f6a24355-fe4b-4d71-bd19-0aab8b39aa7e/5ZH5qg/Ratings/Protocols/current/test_protocol_pedestrian_aeb.pdf
- `iihs_hldi2018`: IIHS news, 'Subaru crash avoidance system cuts pedestrian crashes', 2018-05-08. https://www.iihs.org/news/detail/subaru-crash-avoidance-system-cuts-pedestrian-crashes
- `cicchino2022`: Cicchino, 'Effects of automatic emergency braking systems on pedestrian crash risk', AAP 2022, IIHS bibliography ref 2243. https://www.iihs.org/research-areas/bibliography/ref/2243
- `futurride2022`: Futurride, 2022-02-03, quoting the IIHS release on the Cicchino study (secondary; IIHS release URL returned 404). https://futurride.com/2022/02/03/iihs-study-reveals-aeb-limitations-in-dark-conditions/
- `euroncap_faq`: Euro NCAP FAQ. https://www.euroncap.com/faq/
- `euroncap_vru451`: Euro NCAP Test Protocol AEB/LSS VRU systems v4.5.1, February 2024. https://cdn.euroncap.com/cars/assets/euro_ncap_aeb_lss_vru_test_protocol_v451_cb0d5dfd0a.pdf
- `mcity2022`: Mcity Test Facility recharge rates (LC member sheet, Nov 2022). https://mcity.umich.edu/wp-content/uploads/2022/11/11.1.22_TestFacilityRates-LC.pdf
- `fmvss127`: NHTSA FMVSS No. 127 final rule, Federal Register 2024-05-09. https://www.govinfo.gov/content/pkg/FR-2024-05-09/html/2024-09054.htm
- `robotreport_iso10218`: The Robot Report, 'ISO 10218 industrial robot safety standard receives major overhaul', 2025-02-18. https://www.therobotreport.com/iso-10218-industrial-robot-safety-standard-receives-major-overhaul/
- `gr2safety`: Gemini Robotics Team, 'Gemini Robotics 2: Safety Evaluations', 2026-07-29 (also in the system-card corpus). https://storage.googleapis.com/deepmind-media/gemini-robotics/Gemini-Robotics-2-Safety.pdf
- `hf_asimov_agentic`: Hugging Face dataset card google/asimov_agentic. https://huggingface.co/datasets/google/asimov_agentic (file listing via https://huggingface.co/api/datasets/google/asimov_agentic?blobs=true)
- `asimov_v2_page`: ASIMOV-2.0 project page. https://asimov-benchmark.github.io/v2/ (Data button: https://colab.research.google.com/drive/1ANSRfztNCHqCQNHl9sDtmPMAXD4l2UiW?usp=sharing)
- `dronebench`: Andon Labs, Drone-Bench (PDF). https://andonlabs.com/docs/Drone_Bench.pdf
- `redvla_page`: RedVLA project page. https://redvla.github.io
- `corpus_projectpilot`: Anthropic, 'Project Pilot: Can AI Control a Drone?', 2026-07-24, read from the system-card corpus (docs.sqlite) on 2026-10-01. https://www.anthropic.com/research/project-pilot
- arXiv 2509.21651: ASIMOV-2.0, Jindal et al., v2 2025-11-21. https://arxiv.org/abs/2509.21651 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2412.13178: SafeAgentBench, Yin et al., v5 2025-10-31. https://arxiv.org/abs/2412.13178 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2512.10675: Evaluating Gemini Robotics Policies in a Veo World Simulator, v2 2026-01-06. https://arxiv.org/abs/2512.10675 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2410.13691: RoboPAIR, Robey et al., v2 2024-11-09. https://arxiv.org/abs/2410.13691 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2503.07885: RoboGuard, Ravichandran et al., v2 2026-03-03. https://arxiv.org/abs/2503.07885 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2502.06575: Predictive Red Teaming (RoboART), Majumdar et al., 2025-02-10. https://arxiv.org/abs/2502.06575 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2604.22591: RedVLA, Zhang et al., v2 2026-09-04. https://arxiv.org/abs/2604.22591 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2604.05427: SafeGate, Obi et al., 2026-04-07. https://arxiv.org/abs/2604.05427 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2503.06892: SafePlan, Obi et al., 2025-03-10. https://arxiv.org/abs/2503.06892 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2203.09872: Svarny et al., protective soft skins, 2,250 collision measurements, v2 2022-05-19. https://arxiv.org/abs/2203.09872 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2009.01036: Svarny et al., 3D Collision-Force-Map, v4 2021-03-26. https://arxiv.org/abs/2009.01036 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2203.02706: Kirschner et al., ISO/TS 15066 interpretations, 2022-03-05. https://arxiv.org/abs/2203.02706 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2404.07762: NeuroNCAP, Ljungbergh et al., v4 2024-04-23. https://arxiv.org/abs/2404.07762 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2406.15349: NAVSIM, Dauner et al., v2 2024-10-31. https://arxiv.org/abs/2406.15349 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2605.00066: Wang et al., open-loop vs closed-loop (NAVSIM vs Bench2Drive), 2026-04-30. https://arxiv.org/abs/2605.00066 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2506.04218: Pseudo-Simulation (NAVSIM v2), Cao et al., v3 2026-03-20. https://arxiv.org/abs/2506.04218 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2606.00773: SafeVLA-Bench, Fan et al., v2 2026-09-30. https://arxiv.org/abs/2606.00773 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2505.19933: EmbodyGuard / SAFEL, Son et al., 2025-05-26. https://arxiv.org/abs/2505.19933 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2603.11975: HomeSafe-Bench, Pu et al., v2 2026-03-13. https://arxiv.org/abs/2603.11975 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2509.23690: HomeSafeBench, Yao et al., v2 2026-08-04. https://arxiv.org/abs/2509.23690 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2506.16402: IS-Bench, Lu et al., v3 2025-12-05. https://arxiv.org/abs/2506.16402 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2509.12379: Geometric Red-Teaming, Goel et al., 2025-09-15. https://arxiv.org/abs/2509.12379 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2409.16942: Swiss Re / Stanford ADAS assessment, Di Lillo et al., v4 2024-11-26. https://arxiv.org/abs/2409.16942 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2607.00218: EgoSafetyBench, Panpatil et al., 2026-06-30. https://arxiv.org/abs/2607.00218 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2606.18632: ROBOSHACKLES, Yin et al., v2 2026-08-20. https://arxiv.org/abs/2606.18632 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2608.17386: ManiGuard, Peng et al., 2026-08-18. https://arxiv.org/abs/2608.17386 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2606.27079: ForesightSafety-VLA, Lyu et al., v2 2026-06-27. https://arxiv.org/abs/2606.27079 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2609.07288: Bajrami et al., LLM-orchestrator safety benchmark (humanoid), 2026-09-07. https://arxiv.org/abs/2609.07288 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2212.08148: Waymo Collision Avoidance Testing, Kusano et al., 2022-12-15. https://arxiv.org/abs/2212.08148 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2410.06172: MSSBench, Zhou et al., v2 2025-04-22. https://arxiv.org/abs/2410.06172 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2408.04449: EARBench, Zhu et al., v5 2024-11-28. https://arxiv.org/abs/2408.04449 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2605.31196: TouchSafeBench, Wang et al., 2026-05-29. https://arxiv.org/abs/2605.31196 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2605.19328: RoboJailBench, Yeke et al., 2026-05-19. https://arxiv.org/abs/2605.19328 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2604.05498: JailWAM, Liu et al., v2 2026-08-13. https://arxiv.org/abs/2604.05498 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
- arXiv 2503.03480: SafeVLA / Safety-CHORES, Zhang et al., v4 2026-04-19. https://arxiv.org/abs/2503.03480 (abstract via export.arxiv.org API; full text via arxiv.org/html where available)
  - "We constructed 600 detailed tasks: 300 hazardous with explicit risks and 300 safe counterparts as controls to detect pure planning ability, with comparable complexity (average steps 5.03 vs. 5.12). ... In this work, we propose 100 abstract task. ... In this work, we propose 50 long-horizon tasks." [arXiv 2412.13178, fetched 2026-10-01]
