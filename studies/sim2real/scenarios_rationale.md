# sim2real scenarios: ladder mapping and anchors

Study question: does the sim-to-real gap matter for the value of information (VOI) of a robot safety evaluation?

Design: hold the decision fixed and vary only the instrument along the 0-9 sim-to-real ladder. Within a group the `agent`, `decision` and `theta_definition` strings are byte-identical, so any difference in elicited p, s, t, B, K, C and in EVSI is attributable to the instrument (and to elicitation noise). `p`, `B` and `K` should in principle be identical across a group; their spread is a health check on the elicitor.

File: `studies/sim2real/scenarios.json`, 15 scenarios. `attributes = {level, context_group, catalog_keys}`.

## Groups

1. `home manipulator` (levels 0-9, 10 scenarios). Agent: head of safety at a company about to deploy a VLA-based mobile manipulator into customers' homes. theta=1: the deployed policy has an unsafe behaviour mode that would injure a person or cause serious property damage in ordinary home use. Decision: delay the launch and add mitigations vs launch.
2. `AV AEB` (levels 1, 4, 6, 8, 9, 5 scenarios). Agent: an OEM's head of active-safety validation. theta=1: the AEB system has a failure mode in which it does not brake for a crossing pedestrian (adult or child, including a child emerging from behind parked cars) at 20-60 km/h in daylight or darkness. Decision: delay the AEB release and rework vs release. Level 0 (text-only requirement review by an LLM) is not meaningful for a perception-dominated function, so the bottom rung is level 1 image QA.

## Ladder mapping, home manipulator

| level | rung | instrument | primary anchor (catalog key) | supporting keys | cross-rung validity number | cost evidence |
|---|---|---|---|---|---|---|
| 0 | text-only planner QA | SafePlan-style prompt suite to the language planner | `obi2025safeplan` (621 prompts, 127 safe / 494 unsafe) | `sermanet2025asimov` (ASIMOV-Injury text subset), `son2025embodyguard`, `obi2026safegate` | none; SafeGate adds real-robot tests but no text-to-hardware correlation | expert curation only, no figures |
| 1 | static image QA | MSSBench-style image+instruction suite | `zhou2024mssbench` (1,820 pairs, 760 embodied) | `zhang2026guardianbench`, `zhu2024earbench` (judge kappa 0.48-0.85) | none | manual authoring, no figures |
| 2 | video / temporal QA | ASIMOV-Agentic proximity monitoring on 5 s windows | `geminirobotics2026agentic` (FPR <5% costs FNR >40%) | `tian2026badbehavior` (reward models on 723 real rollout videos) | same report: Apollo 2 humanoid lab stop test 99% / 96% | capture rig described, no figures |
| 3 | generated adversarial scenes, open-loop | diffusion-edited camera frames with inserted hazards | `majumdar2025predictive` (RoboART) | `sermanet2025asimov` (ASIMOV-Multimodal), `yin2026roboshackles` | RoboART: Spearman 0.8 and mean gap <0.19 vs 500+ hardware trials (task success, not hazard) | automated, no figures |
| 4 | closed-loop physics sim | SafeVLA-Bench-style STL monitors in RoboCasa (robosuite/MuJoCo) | `fan2026safevlabench` (36-56% of successful RoboCasa-365 rollouts unsafe) | `nasiriany2024robocasa`, `nasiriany2026robocasa365`, `huang2026safemanip`, `lyu2026foresightsafetyvla`, `zhang2025safevla`, `liu2023libero`, `jain2025polaris` | none for safety; LIBERO saturation (scores 90-95% regardless of real performance) as the cautionary number | throughput only (2,000 LIBERO episodes in ~18 min) |
| 5 | photoreal / digital twin | Veo world model or PolaRiS scan-reconstructed twin | `geminirobotics2025veo` (MMRV 0.06 vs 1,600+ real episodes; safety failures reproduced on hardware) | `jain2025polaris` (Pearson 0.90), `wang2026recipe`, `li2024simpler`, `sedlacek2025realm` | Veo safety probes reproduced on ALOHA 2; simulator choice moves Spearman 0.40-0.70 | build time (<1 h per scene) only |
| 6 | hardware-in-the-loop | Real-is-Sim style synchronised twin with real compute/sensors | `abouchakra2025realissim` (Franka, 60 Hz twin, 1 task) | `son2022pgvil`, `kaiser2025coupled` (automotive VIL consistency) | ranking preserved on one task, no coefficient | hardware list only |
| 7 | real robot, lab | RedVLA hazard-object trials plus ISO 10218/TS 15066 contact-force measurement | `zhang2026redvla` (real ASR >80%, 3 tasks x 10 trials) | `peng2026maniguard`, `iso2025iso10218`, `svarny2022skins` (2,250 measurements), `kirschner2022iso15066`, `tri2025lbm` (~50 trials per condition), `zhou2025autoeval` (~850 episodes per 24 h) | sim-found risks reproduce on hardware >80% | trial counts; ISO text USD 244 |
| 8 | real robot, field, humans / surrogates | staged test in furnished real homes with participants and instrumented surrogates | `gervet2023navigating` (6 real homes; sim-to-real rank inversion, 54 pp drop) | `han2024painthresholds` (37 subjects, 121-310 N), `salvini2021safety`, `dilillo2024adas`, `mcity2022rates` | none for home robots | automotive analogues only (USD 3,127 per track day; 8-month, ~1,000-run campaign) |
| 9 | deployment monitoring | monitored pilot in customer homes with black-box logging and incident reporting | `sindhwani2020anomaly` (5,000-mission fleet log monitoring) | `winfield2020accident`, `soc2022amazonprimed`, `jindal2025danger` (NEISS), `nhtsa2021sgo`, `kalra2016driving`, `favaro2023interpreting` | is the ground truth; statistical power limits from RAND | none |

## Ladder mapping, AV AEB

| level | instrument | primary anchor | supporting keys | cross-rung validity number | cost evidence |
|---|---|---|---|---|---|
| 1 | VLM QA on forward-camera frames | `elhafsi2023semantic` (TPR 92% / TNR 78% on 69 CARLA cases) | `ma2025safevl` (76% on Nexar dashcam), `andeol2023confident` (3,414 frames labelled), `foutter2026faithfulness` | none | API calls and manual labelling, no figures |
| 4 | Euro NCAP-style virtual testing of the AEB grid | `euroncap2025virtual` (perfect perception assumed; KPI tolerances) | `euroncap2026vta` (~2,000+ runs by 2026), `feng2021nade`, `ljungbergh2024neuroncap` | procedural spot checks only (>=75% verification pass) | "6 months of physical testing" avoided (search snippet) |
| 6 | vehicle-in-the-loop on proving ground | `son2022pgvil` (NRMSE ~4%, Pearson ~1 vs real, search snippet) | `zhang2025combined` (AEB-specific), `novickineto2023twice`, `kaiser2025coupled`, `euroncap2023aebc2c` (dossier needs HiL/SiL/ViL evidence) | vehicle-dynamics KPIs only | none |
| 8 | IIHS / Euro NCAP track test with pedestrian dummies | `iihs2024paeb` (36 scored runs per vehicle) | `euroncap2024aebvru`, `euroncap2023aebc2c`, `mcity2022rates`, `nhtsa2024fmvss127`, `dilillo2024adas`, `cicchino2022pedestrian` | HLDI: 27-35% lower pedestrian claim frequency; no benefit in unlit dark | several hundreds of thousands of Euros per programme; USD 3,127 per track day |
| 9 | fleet telemetry with crash/claim matching | `cicchino2022pedestrian` (25-27% fewer pedestrian crashes) | `cicchino2018gm`, `iihs2023trucks`, `nhtsa2021sgo`, `kalra2016driving`, `kusano2025comparison`, `dilillo2024swissre`, `koopman2022ul4600` | is the ground truth; 275M miles for a fatality bound | none |

## Placement decisions

- ASIMOV v1 multimodal is at level 3, not level 1: its images are Imagen-3 edits of real frames, which is "generated scenes" on the ladder. The catalogue's level-1 anchor for embodied situational safety is MSSBench, so that is used at level 1. ASIMOV-Injury (text) is cited at level 0.
- RoboART is the level-3 primary anchor because it is the only generated-scene proxy with a measured correlation to hardware, even though it measures task success under distribution shift rather than hazardous behaviour. ROBOSHACKLES and ASIMOV-Multimodal supply the hazard-specific content.
- Level 4 uses RoboCasa (robosuite/MuJoCo) rather than Isaac because the safety-monitored VLA suites in the catalogue (SafeVLA-Bench, SafeManip) run there; Safety-CHORES (AI2-THOR) and ForesightSafety-VLA (RoboTwin) are cited as corroborating closed-loop suites.
- Level 5 pairs the Veo world model (the only level-5 entry with a safety probe validated on hardware) with the PolaRiS scan-to-twin route, because a home-robot deployer would more plausibly reconstruct customer homes than train a video model.
- Level 6 is the emptiest rung for robots (gaps.md section 2). Real-is-Sim is the only non-automotive HIL entry; its validity is one task with no coefficient. The automotive VIL consistency numbers are cited as the best available evidence for what HIL can achieve.
- Level 8 for home robots has no published evaluation with humans or surrogates and a cost figure. The scenario is a composite: the 6-real-homes ObjectNav study for the field-deployment side, the pendulum pain-threshold study for the human-contact side, automotive campaigns for cost. This is stated in the context.
- Level 9 for home robots likewise has no published pilot. The context borrows the fleet-log monitoring recipe (Wing), the ethical black box proposal, and the only deployment-level harm datasets in the catalogue (Amazon OSHA logs, NEISS, NHTSA SGO).
- AV level 4 uses Euro NCAP's own virtual-testing protocol because it is the closed-loop simulation an OEM would actually build for this decision; its "perfect perception assumed" clause is the key validity limitation for a pedestrian-detection failure mode and is spelled out in the context.
- AV level 6 injects virtual pedestrians into the production vehicle's perception. The context states that this bypasses real camera/radar detection, which is the mechanism theta is about.
- SafeVL (catalogue level 5 because of NeuroNCAP) is cited inside the AV level-1 context only for its VLM-on-dashcam accuracy number.

## What each rung can and cannot show (validity chain)

- Levels 0-2 and 4 have judge-vs-human agreement at best; no safety score at these rungs has a published correlation with a higher rung.
- Level 3 (RoboART) and level 5 (Veo, PolaRiS, REALM, SIMPLER) have paired sim/real correlations, almost all for task success; the Veo safety-probe reproduction is the only safety-specific cross-rung result for robots.
- Level 7 (RedVLA) reports that >80% of simulation-found risks reproduce on a Franka.
- Only the automotive chain reaches outcomes: level 8 track ratings to level 9 claim reductions (27-35%), and level 9 evidence forcing protocol changes (night tests, truck and motorcycle targets).
- Level 9 is the ground truth but is statistically weak early (RAND, Waymo credibility paradox) and exposes real users.

## Facts policy

- Every number and named fact in a `context` paragraph is taken from `research/catalog.json`; the keys used are listed in `attributes.catalog_keys`. No web fetches were needed.
- Where the catalogue flags a number as coming from a search snippet rather than a fetched abstract (Kookmin VIL, AB Dynamics 6-month estimate), the context says so.
- Where no cost is published the context says "no published cost figure" rather than guessing.
- Contexts describe the instrument only and never restate the decision (checked by a regex on delay/launch/release wording).

## Assumptions made without input

- The VLA stack is assumed to have a language planner or orchestrator (level 0 target) and a monitoring VLM (level 2 target), as in the Gemini Robotics 2 "system 2" architecture.
- Each instrument's binary signal is defined as "flags if a preset threshold is exceeded" (or, for levels 8-9, "flags if any qualifying event is observed"); thresholds are left to the elicitor.
- The AV scenario class is fixed to crossing pedestrians at 20-60 km/h, day and night, matching the IIHS and FMVSS 127 pedestrian scenarios, so that levels 4, 6 and 8 all test the same grid.
- `C` is build-from-scratch plus one run, as in protocol p001; the contexts give trial counts and hardware where the literature has them.
