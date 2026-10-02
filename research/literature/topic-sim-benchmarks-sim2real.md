# Simulation benchmarks and sim-to-real evaluation validity (2018-2026)

Literature sweep for a workshop paper on the value of information (VOI) of robot safety evaluations. 67 entries, all URLs fetched and verified. Companion data: `topic-sim-benchmarks-sim2real.json`.

## One-page synthesis

### What exists

- Physics sim benchmarks (ladder level 4): LIBERO, RoboCasa/RoboCasa365, BEHAVIOR-1K, RoboTwin 2.0, RLBench, COLOSSEUM, Habitat 2.0/3.0, RoboVerse, Bench2Drive; engines ManiSkill3, Isaac Gym/Lab. Cheap and reproducible, but their scores are now known to saturate (LIBERO 90-95% for policies spanning the full real-world range) and to collapse under mild perturbation (LIBERO-PRO 90% to 0%; LIBERO-Plus 95% to <30%).
- Real-to-sim digital twins (level 5): SIMPLER, PolaRiS, REALM, RoboLab, SimFoundry, digital cousins, Gaussian-splatting soft-body twins, JoyAI-Sim, RobotArena Infinity, R2S-Eval. These are where the paired sim/real correlation evidence lives (Pearson 0.78-0.98, MMRV 0.015-0.06 when built carefully).
- Learned world-model evaluators (also placed at level 5, but with no physics engine): WorldGym (r=0.78), WorldEval (r=0.94), Veo world simulator (r=0.86 OOD, red-teaming), RoboWorld (r=0.99), GigaWorld-1/WMBench (rho=0.61 baseline), Ctrl-World (MMRV 0.22 per PolaRiS), dWorldEval, Interactive World Simulator.
- Real-robot evaluation infrastructure (level 7): RoboArena (4,284 episodes, 7 sites), AutoEval (850 episodes/day/cell, >99% less human time), RoboChallenge (10 machines, 30 tasks), ArmnetBench ($359-477 per cell), PhAIL, RoboDojo real leaderboard, TRI LBM (1,800 real rollouts).
- Statistics of evaluation: Kress-Gazit et al. best practices, Vincent et al. distribution bounds, Snyder et al. sequential tests (up to 32% and 70% fewer trials), SureSim prediction-powered inference (20-25% fewer real trials), betting estimators, active factor-based evaluation (20-40% fewer trials).
- Autonomous driving analogues: nuPlan, NAVSIM (Pavone co-author), Bench2Drive, DriveE2E, WOSAC realism metric, plus two validity studies (Dauner 2023; Wang 2026: open-loop PDMS vs closed-loop Spearman 0.90 but non-monotonic).
- Standards: Euro NCAP virtual testing protocol v1.00 (2025) codifies sim-vs-physical acceptance (ISO 18571 score >= 0.5, TTC tolerance +-0.2 s, 75% of verification cells must pass).

### Where cost evidence is strong

- AutoEval: <$3,500 hardware, ~850 episodes per 24 h, 3 human interventions per day, 1-3 h to build a cell.
- ArmnetBench: $359 / $477 per cell, ~10 s operator time per rollout.
- PolaRiS: 2-5 min scan, <1 h per environment, <25 min co-training; 20 real rollouts per policy-environment as ground truth.
- SIMPLER: 3.5k steps/s, 7x faster than real; ~1,500 real episodes used to validate.
- SureSim, Snyder 2025/2026, Liao 2026: quantified reductions in real trials (14-70%) for the same statistical conclusion.
- PhAIL survey: modal practice is 10-20 real rollouts per condition with no confidence intervals; Kress-Gazit shows 150+ trials are needed to separate close policies.

### Where validity evidence is strong or absent

- Strong (paired sim/real, multiple policies and tasks): SIMPLER, PolaRiS, REALM, Wang 2026 cross-simulator recipe, WorldEval, Veo, Gaussian-splat twins, SimFoundry, digital cousins, AutoEval (vs human eval), RoboArena (vs held-out real eval).
- Cautionary (sim mis-ranks real): Kadian 2020 (SRCC 0.18 before tuning), Gervet 2023 (end-to-end 77% sim vs 23% real, rank inversion), BEHAVIOR-1K (40% sim vs 0-22% real), LIBERO family, RoboTwin as evaluator (r=0.41), Ctrl-World (MMRV 0.22), SIMPLER on 2026 VLAs (rho=0.40).
- Absent: almost no entry links sim scores to real-world safety outcomes (collisions, harm). Safety appears only as red-teaming (Veo), unsafe-action flagging (WorldEval), human-proximity tasks (Habitat 3.0), AV collision sub-metrics (NAVSIM) and the Euro NCAP protocol. No study reports sensitivity or false-alarm rates of a sim evaluation as a safety test; the closest are VLM-judge confusion rates (WorldGym GPT-4o TPR 0.81 / FPR 0.03; GigaWorld 87.8% exact agreement; R2S-Eval 91.9% agreement).
- Speaker links: Pavone (NAVSIM), Sindhwani (Veo world simulator). No Bajcsy or Fel entries surfaced in this topic.

### Canonical entries for a 4-page paper

1. li2024simpler: the reference real-to-sim evaluation with Pearson/MMRV reporting.
2. kadian2020sim2real: origin of the sim-vs-real correlation coefficient and the first documented mis-ranking.
3. atreya2025roboarena: real-world ground-truth ranking at scale, and the reference other proxies are judged against.
4. jain2025polaris: cost per environment plus r=0.90 and the LIBERO-saturation result in one paper.
5. wang2026recipe: head-to-head validity of three simulators on the same 1,115 real rollouts.
6. badithela2025suresim: formal trade-off between sim rollouts and real trials with valid confidence intervals (VOI-adjacent).
7. zhou2025autoeval: hard numbers for the cost of real evaluation and its agreement with human evaluation.
8. gemini2025veo: only entry with safety red-teaming validated on hardware (1,600+ real episodes; Sindhwani link).

### Ladder caveat

World-model evaluators (WorldGym, WorldEval, Veo, RoboWorld, GigaWorld-1, Ctrl-World, dWorldEval, Interactive World Simulator) are placed at level 5 because they are closed-loop, photoreal and built from real data, but they have no physics engine; a paper may prefer to flag them as a distinct rung between 3 and 5. Level null is used for methods papers with no hardware component or for studies comparing two levels.

## Catalogue table

| key | name | year | kind | level | safety | validity (headline) | cost (headline) |
|---|---|---|---|---|---|---|---|
| mahboob2026betting | Betting for Sim-to-Real Performance Evaluation | 2026 | study | None | no | none stated | none stated |
| wan2026nofreechecker | No Free Checker: survey of verifiers | 2026 | study | None | yes | Meta-level: catalogues how verifiers are validated (human agreement etc.). | none stated |
| wang2026openloop | Do Open-Loop Metrics Predict Closed-Loop Driving? | 2026 | study | None | yes | Direct cross-level validity study (level 5 replay vs level 4 closed-loop); ADE/FDE previously shown to have... | none stated |
| liu2026mdpgap | Sim-to-Real Gap of Foundation Model Agents (MDP view) | 2026 | position | 0 | no | none stated | none stated |
| james2019rlbench | RLBench | 2019 | benchmark | 4 | no | none stated | none stated |
| szot2021habitat2 | Habitat 2.0 / Home Assistant Benchmark | 2021 | benchmark | 4 | no | none stated | 25,000+ sim steps/s (850x real-time) on an 8-GPU node. |
| makoviychuk2021isaacgym | Isaac Gym | 2021 | tooling | 4 | no | none stated | 2-3 orders of magnitude speedup over CPU-sim + GPU-NN pipelines on a single GPU. |
| liu2023libero | LIBERO | 2023 | benchmark | 4 | no | Negative evidence from others: PolaRiS finds LIBERO scores cluster at 90-95% regardless of real performance... | vla-eval (2026) runs 2,000 LIBERO episodes in ~18 min parallel vs 14 h sequential. |
| puig2023habitat3 | Habitat 3.0 | 2023 | benchmark | 4 | yes | Reports that automated-humanoid evaluation trends carry over to human-in-the-loop evaluation (qualitative i... | none stated |
| pumacay2024colosseum | THE COLOSSEUM | 2024 | benchmark | 4 | no | Moderate R^2=0.614 between sim and real perturbation sensitivities. | Real validation: 4 tasks, 5 demos each, 2 alternate variations per factor, 10 episodes x 3 runs. |
| nasiriany2024robocasa | RoboCasa | 2024 | benchmark | 4 | no | Sim data transfers (training utility) but no sim-vs-real evaluation correlation reported. | Real experiments: Franka Panda on mobile base, 3 tasks, 50 trials per task across 5 scenes. |
| li2024behavior1k | BEHAVIOR-1K / OmniGibson | 2024 | benchmark | 4 | no | Direct evidence of a large sim-real gap; failure modes differ (sim: wrong primitive; real: 40% grasp failur... | Real study: 1 activity, 27 + 26 real runs on a bimanual mobile manipulator. |
| tao2024maniskill3 | ManiSkill3 | 2024 | tooling | 4 | no | none stated | 10-1000x faster with 2-3x less GPU memory than other platforms; up to 30,000+ FPS with rendering. |
| jia2024bench2drive | Bench2Drive | 2024 | benchmark | 4 | yes | Argues open-loop L2 and collision rate cannot reflect driving performance; no on-road validation. | none stated |
| zhou2025liberopro | LIBERO-PRO | 2025 | benchmark | 4 | no | Shows in-distribution sim success has near-zero predictive value for even mild distribution shift; no real-... | none stated |
| fei2025liberoplus | LIBERO-Plus | 2025 | benchmark | 4 | no | No real-robot data; demonstrates false-confidence of nominal benchmark scores. | none stated |
| chen2025robotwin2 | RoboTwin 2.0 | 2025 | benchmark | 4 | no | Training transfer only. WorldEval reports RoboTwin-based real-to-sim evaluation at Pearson 0.411 / MMRV 0.2... | none stated |
| geng2025roboverse | RoboVerse / MetaSim | 2025 | tooling | 4 | no | Sim-to-real transfer experiments reported; no correlation coefficient in abstract. | none stated |
| mittal2025isaaclab | Isaac Lab | 2025 | tooling | 4 | no | none stated | none stated |
| euroncap2025virtual | Euro NCAP Safe Driving & Crash Avoidance Virtual Testing protocol v1.00 | 2025 | standard | 4 | yes | Codified sim-vs-physical agreement criteria (ISO 18571 time-series score and KPI tolerances) rather than st... | Physical verification limited to randomly selected grid cells; re-simulation required if validation fails. |
| nasiriany2026robocasa365 | RoboCasa365 | 2026 | benchmark | 4 | no | none stated | none stated |
| gao2026isaacsim | NVIDIA Isaac Sim survey | 2026 | study | 4 | no | none stated | none stated |
| choi2026vlaeval | vla-eval harness | 2026 | tooling | 4 | no | Reproducibility evidence: benchmark scores are fragile to evaluation-harness parameters. | 2,000 LIBERO episodes in ~18 min (47x speedup vs 14 h sequential); env throughput 11.2 to 364.6 obs/s. |
| chen2026robodojo | RoboDojo | 2026 | benchmark | 4 | no | Sim-real correlation not extracted (truncated); large absolute gap noted. | 180 real trials per policy for 10 policies. |
| kadian2020sim2real | Sim2Real Predictivity (Habitat, SRCC) | 2020 | study | 5 | no | Direct: low sim-real correlation traced to agents exploiting simulator collision physics (sliding); predict... | Required 3D scanning of the physical lab and parallel real-robot runs of 9 models; trial counts not stated ... |
| caesar2021nuplan | nuPlan | 2021 | benchmark | 5 | yes | none stated | none stated |
| dauner2023parting | Parting with Misconceptions (nuPlan) | 2023 | study | 5 | yes | Shows open-loop metrics reward behaviour that is unsafe in closed loop. | none stated |
| montali2023wosac | Waymo Open Sim Agents Challenge (WOSAC) | 2023 | benchmark | 5 | no | Distribution-matching against real logs; does not test whether AV rankings transfer to road. | none stated |
| li2024simpler | SIMPLER (SimplerEnv) | 2024 | benchmark | 5 | no | Paired sim/real evaluation of 6 policies: strong Pearson correlation and low rank violation; sim reproduces... | ~1,500 real-world evaluation episodes used as ground truth; single env renders 3.5k sim steps/s on RTX 4090... |
| dauner2024navsim | NAVSIM | 2024 | benchmark | 5 | yes | Internal correlation to closed-loop sim; external cross-benchmark study (Wang 2026) finds Spearman 0.90 wit... | none stated |
| jain2025polaris | PolaRiS | 2025 | benchmark | 5 | no | Paired real/sim evaluation across 6 environments; explicitly shows LIBERO saturation gives near-zero discri... | 20 real rollouts per policy per environment; 50 sim rollouts per task; scene scan 2-5 min, environment buil... |
| sedlacek2025realm | REALM | 2025 | benchmark | 5 | no | Paired real-to-sim validation on unseen scenes; independently confirmed as the best-correlating of three si... | ~800 paired real/sim rollouts for validation; system identification of 14 parameters. |
| zhang2025gaussian | Real-to-sim eval with Gaussian splatting (soft bodies) | 2025 | benchmark | 5 | no | Paired real/sim success across 4 architectures and 3 tasks; r>0.9 in all tasks. | xArm 7 with two RealSense cameras; 39-60 teleoperated demos per task; simulator several times faster than r... |
| jangir2025robotarenainf | RobotArena Infinity | 2025 | benchmark | 5 | no | VLM-vs-human ranking agreement only; sim-vs-real quantified on a single task qualitatively. Weak on real-wo... | 8,749 crowdworker preference pairs; written justification improved annotation accuracy; per-scene reconstru... |
| yang2025benchmarking | Robot Policy Evaluation for Sim-to-Real Transfer: A Benchmarking Perspective | 2025 | position | 5 | no | none stated | none stated |
| quevedo2025worldgym | WorldGym | 2025 | benchmark | 5 | no | Paired real evaluation r=0.78; object-interaction realism remains a limitation. | All rollouts under one hour on a single GPU; world model trained 300k steps on 2x A100 80GB. |
| li2025worldeval | WorldEval / Policy2Vec | 2025 | benchmark | 5 | yes | Paired real evaluation; 6x better correlation than a physics real-to-sim baseline on the same policies. | 1,000+ real trials as ground truth. |
| gemini2025veo | Gemini Robotics policies in a Veo world simulator | 2025 | red-team | 5 | yes | Paired real evaluation of 8 checkpoints; red-team findings reproduced on hardware. | 1,600+ real episodes for validation; all scoring by human raters; per-rollout compute not stated. |
| guo2025ctrlworld | Ctrl-World | 2025 | tooling | 5 | no | External: PolaRiS reports MMRV 0.22 for Ctrl-World-based evaluation, i.e. notable mis-rankings. | none stated |
| yu2025drivee2e | DriveE2E | 2025 | benchmark | 5 | yes | none stated | none stated |
| wang2026recipe | Sim-and-real correlation recipe for VLA evaluation | 2026 | study | 5 | no | Head-to-head comparison of three simulators against the same real data; shows simulator choice changes rank... | 1,115 real rollouts (about 55 real trials and 2,020 sim rollouts per policy-task-perturbation cell). |
| wang2026r2seval | R2S-Eval | 2026 | benchmark | 5 | no | Ranking correlation with hardware and VLM-human agreement both reported. | Operator time in conventional evaluation grows ~linearly with trials; R2S-Eval needs hardware only for init... |
| ranawaka2026simfoundry | SimFoundry | 2026 | tooling | 5 | no | Paired sim/real evaluation across 7 tasks and 5 architectures. | none stated |
| lu2026seeing | From Seeing to Simulating (digital cousins, WorldComposer) | 2026 | tooling | 5 | no | Paired evaluation r=0.91; sim failures reported as reliable predictors of real failures. | 50 automated trajectories in ~30 min on one RTX 4090, 6 GB VRAM; 20 real trials per configuration. |
| liu2026joyaisim | JoyAI-Sim | 2026 | tooling | 5 | no | Paired checkpoint evaluation; replay consistency 90%. | 8 GPUs, 64 concurrent envs, 128 evaluation episodes per hour. |
| yang2026robolab | RoboLab / RoboLab-120 | 2026 | benchmark | 5 | no | Ranking preserved for 4 policies against RoboArena; small n. | none stated |
| jeon2026roboworld | RoboWorld | 2026 | benchmark | 5 | no | Reported correlation only; sample size unknown. | none stated |
| gigaworld2026roadmap | GigaWorld-1 / WMBench | 2026 | benchmark | 5 | no | Largest paired real/world-model dataset found; VLM-human agreement quantified. | 32 NVIDIA H20 GPUs for training; 100+ challenge teams. |
| li2026dworldeval | dWorldEval | 2026 | benchmark | 5 | no | Claims only; numbers not in abstract. | none stated |
| wang2026interactive | Interactive World Simulator | 2026 | tooling | 5 | no | Qualitative: if one policy substantially outperforms another in the simulator it likely does in real; biase... | 15 FPS on a single RTX 4090, stable >10 min. |
| huang2026cimse | Critical Interval MSE | 2026 | study | 5 | no | Correlation with real closed-loop success; PolaRiS reports plain MSE as a low-correlation baseline. | none stated |
| abouchakra2025realissim | Real-is-Sim | 2025 | tooling | 6 | no | Qualitative ranking preservation on one task only; weak. | Franka Emika, RTX 6000 Ada, 3 RealSense D455 at 90 fps; 30 real + 30 sim-augmented demos. |
| gervet2023navigating | Navigating to Objects in the Real World | 2023 | study | 7 | no | Direct evidence of sim-real rank inversion; causes: image domain gap and mismatched failure modes. | none stated |
| kressgazit2024empirical | Robot Learning as an Empirical Science | 2024 | position | 7 | no | Statistical argument; no sim-real component. | Implicit: separating close policies requires >100 real trials per policy. |
| vincent2024generalizable | How Generalizable Is My Behavior Cloning Policy? | 2024 | study | 7 | no | Bounds validated empirically in sim and hardware. | none stated |
| atreya2025roboarena | RoboArena | 2025 | benchmark | 7 | no | Ground truth is a large held-out real evaluation; RoboArena rankings track it better than centralized evals... | 4,284 real episodes across 7 sites; human evaluator per episode; no per-episode time reported. |
| zhou2025autoeval | AutoEval | 2025 | tooling | 7 | no | Paired against manual evaluation on the same policies. | ~850 episodes per 24 h per cell; >99% reduction in human time; 3 interventions per 24 h; new cell in 1-3 h ... |
| yakefu2025robochallenge | RoboChallenge / Table30 | 2025 | benchmark | 7 | no | Reproducibility via visual overlay protocol; intentional environmental variation. | Manual scheduling and prop preparation, wait time hours to days; all trajectories, videos and logs released. |
| zhang2025experiences | Experiences from Benchmarking VLA Models | 2025 | study | 7 | no | none stated | none stated |
| snyder2025stopping | Policy comparison with near-optimal stopping | 2025 | study | 7 | no | none stated | Trial savings quantified; adopted by the TRI LBM study. |
| badithela2025suresim | SureSim | 2025 | study | 7 | no | Formal guarantee: intervals remain valid regardless of simulator bias. | Explicit hardware-trial savings as a function of sim-real correlation. |
| tri2025lbm | A Careful Examination of Large Behavior Models | 2025 | study | 7 | no | Notes sim-real discrepancies without quantifying correlation. | 50 real rollouts per condition considered necessary; 1,800 real rollouts total. |
| selvaraj2026armnetbench | ArmnetBench v0.1 | 2026 | benchmark | 7 | no | No inter-rater agreement reported (single operator). | Cell cost $359 (single) / $477 (bimanual); ~10 s active operator time per rollout; one operator supervises ... |
| arkhangelskiy2026phail | PhAIL | 2026 | benchmark | 7 | no | Statistical-power evidence: binary success at N<=25 cannot separate close policies. | Survey of 13 real-robot VLA papers (2023-2025): modal 10-20 rollouts per condition, none report CIs or pair... |
| jin2026grounding | Grounding Sim-to-Real Generalization (VLA empirical study) | 2026 | study | 7 | no | Large-N factor study of sim-to-real transfer (training side). | 10,000+ real trials; platform and protocol released. |
| liao2026active | Active Real-World Factor-Based Evaluation | 2026 | study | 7 | no | none stated | 2,331 real-world evaluations. |
| snyder2026beyond | Beyond Binary Success (SAVI policy comparison) | 2026 | study | 7 | no | none stated | Trial-count reductions quantified. |

## Entries

### li2024simpler: SIMPLER (SimplerEnv) (2024)

- Org: UC San Diego / Stanford / UC Berkeley / Google DeepMind. Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2405.05941 (arXiv 2405.05941)
- Modality: Closed-loop manipulation policy (RT-1, RT-1-X, RT-2-X, Octo) receives simulated RGB observations from SAPIEN/ManiSkill2 with real-to-sim visual matching (real background overlay, texture tuning) or variant aggregation; scored by binary task success.
- Measures: Whether simulated success rates and rankings of real-world manipulation policies track their real-robot success rates on Google Robot and WidowX/Bridge tasks.
- Size: 2 robot setups; Google Robot: pick coke can, move near, open/close drawer; BridgeData V2 tasks; 6 policy checkpoints
- Reported metrics: Google Robot: Pearson r=0.924 avg (0.976 pick coke, 0.855 move near, 0.942 drawer); MMRV 0.056 avg; Bridge MMRV 0.143 avg.
- Cost evidence: ~1,500 real-world evaluation episodes used as ground truth; single env renders 3.5k sim steps/s on RTX 4090, quoted as 7x speedup over real eval.
- Validity evidence: Paired sim/real evaluation of 6 policies: strong Pearson correlation and low rank violation; sim reproduces real behaviour modes such as sensitivity to distribution shift. Later work (Wang et al. 2026 recipe) measured SIMPLER at Spearman 0.40 / Pearson 0.40 on newer VLAs, so validity degrades off the original policy set.
- Notes: Canonical real-to-sim evaluation paper. MMRV = mean maximum rank violation.

### kadian2020sim2real: Sim2Real Predictivity (Habitat, SRCC) (2020)

- Org: Facebook AI Research / Georgia Tech. Kind: study. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/1912.06321 (arXiv 1912.06321)
- Modality: PointGoal navigation agents receive simulated RGB-D from a 3D-scanned replica of a lab in Habitat; same code runs on a LoCoBot via the Habitat-PyRobot bridge; scored by success and SPL in both.
- Measures: Introduces the Sim-vs-Real Correlation Coefficient (SRCC): how well ranking of navigation agents in simulation predicts their real-robot ranking.
- Size: 9 navigation models tested in parallel in sim and on a LoCoBot in a scanned lab
- Reported metrics: SRCC for success under CVPR19 Habitat challenge settings = 0.18; after disabling sliding-along-walls and tuning sim parameters SRCC = 0.844.
- Cost evidence: Required 3D scanning of the physical lab and parallel real-robot runs of 9 models; trial counts not stated in abstract.
- Validity evidence: Direct: low sim-real correlation traced to agents exploiting simulator collision physics (sliding); predictivity restored by simulator tuning. Earliest quantitative evidence that sim leaderboards can mis-rank real systems.
- Notes: Navigation, not manipulation, but the SRCC concept is the ancestor of MMRV/Pearson reporting in later work.

### jain2025polaris: PolaRiS (2025)

- Org: UW / Stanford / UC Berkeley / TRI / Physical Intelligence. Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2512.16881 (arXiv 2512.16881)
- Modality: DROID-trained VLAs act closed-loop in interactive sim environments reconstructed (neural reconstruction) from 2-5 minute video scans of real scenes; rollouts scored by humans with the same rubric used for real rollouts.
- Measures: Whether real-to-sim environments plus a light co-training recipe give simulated scores that track real-world generalist policy performance across unseen scenes.
- Size: 6 paired real/sim environments, 6 tasks, 4 policies (pi0, pi0-FAST, PaliGemma-binning, pi0.5); 15 held-out co-training scenes
- Reported metrics: Pearson r=0.90 avg with real performance, worst-case r=0.81; r=0.98 vs RoboArena scores; LIBERO scores of the same policies cluster at 90-95% regardless of real performance; Ctrl-World video-model eval MMRV 0.22.
- Cost evidence: 20 real rollouts per policy per environment; 50 sim rollouts per task; scene scan 2-5 min, environment build under 1 hour (30 min training + 20 min composition); co-training <25 min, ~350 demos.
- Validity evidence: Paired real/sim evaluation across 6 environments; explicitly shows LIBERO saturation gives near-zero discriminative power on real-world ranking, while PolaRiS preserves ranking.
- Notes: Strong cost and validity evidence in one place.

### wang2026recipe: Sim-and-real correlation recipe for VLA evaluation (2026)

- Org: Tsinghua University (Yang Gao group). Kind: study. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2606.10366 (arXiv 2606.10366)
- Modality: Five VLAs (pi0, pi0-FAST, pi0.5, GR00T N1.6, N1.7) run closed-loop in three simulators (VLA-Arena/MuJoCo, SIMPLER/SAPIEN, REALM/Isaac Sim) on 9 tabletop tasks aligned with real tasks; sim success compared to real success.
- Measures: Which simulators and which simulated signals preserve real-world policy rankings, and whether simulator co-training improves correlation.
- Size: 9 aligned tasks, 5 policies, 3 simulators; 11,800 sim rollouts and 1,115 real rollouts
- Reported metrics: Before post-training: VLA-Arena Spearman 0.575 / Pearson 0.725 / MMRV 0.060; SIMPLER 0.400 / 0.402 / 0.128; REALM 0.700 / 0.785 / 0.030. After sim post-training (REALM): Spearman 0.875, Pearson 0.878, MMRV 0.015.
- Cost evidence: 1,115 real rollouts (about 55 real trials and 2,020 sim rollouts per policy-task-perturbation cell).
- Validity evidence: Head-to-head comparison of three simulators against the same real data; shows simulator choice changes rank correlation from 0.40 to 0.70, and photoreal Isaac-based REALM outperforms SIMPLER on current VLAs.
- Notes: Most direct cross-simulator validity comparison found.

### sedlacek2025realm: REALM (2025)

- Org: CIIRC CTU Prague / University of Amsterdam. Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2512.19562 (arXiv 2512.19562)
- Modality: DROID-embodiment VLAs (pi0, pi0-FAST, GR00T N1.5) run closed-loop in Isaac Sim with system-identified friction/armature (14 parameters); 15 perturbation factors (6 visual, 8 semantic, 7 behavioural); binary success.
- Measures: Generalization and robustness of VLAs under controlled perturbations, with real-to-sim validation of the simulator as a proxy.
- Size: 7 skills, 2 task sets, 3,500+ objects, 15 perturbation factors; ~800 paired real/sim rollouts for validation
- Reported metrics: Sim/real datapoints close to identity, low MMRV, p<0.001; attention-map cosine similarity 0.85 between real and sim frames for pi0. Independent measurement (Wang et al. 2026): Spearman 0.70, Pearson 0.785, MMRV 0.030.
- Cost evidence: ~800 paired real/sim rollouts for validation; system identification of 14 parameters.
- Validity evidence: Paired real-to-sim validation on unseen scenes; independently confirmed as the best-correlating of three simulators by Wang et al. 2026.

### zhang2025gaussian: Real-to-sim eval with Gaussian splatting (soft bodies) (2025)

- Org: Columbia University / UIUC. Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2511.04665 (arXiv 2511.04665)
- Modality: Policies (ACT, Diffusion Policy, pi0, SmolVLA) act closed-loop in GPU digital twins built from real videos with 3D Gaussian splatting and learned soft-body dynamics; binary success on deformable tasks.
- Measures: Whether simulated success on deformable-object tasks (toy packing, rope routing, T-block pushing) predicts real success across policy architectures.
- Size: 3 tasks, 4 policies; eval sets 20 / 27 / 16 configurations
- Reported metrics: Pearson r = 0.944 (toy packing), 0.901 (rope routing), 0.915 (T-block pushing).
- Cost evidence: xArm 7 with two RealSense cameras; 39-60 teleoperated demos per task; simulator several times faster than real execution via GPU parallelism.
- Validity evidence: Paired real/sim success across 4 architectures and 3 tasks; r>0.9 in all tasks.

### abouchakra2025realissim: Real-is-Sim (2025)

- Org: Robotics and AI Institute (RAI) / QUT. Kind: tooling. Ladder level: 6. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2504.03597 (arXiv 2504.03597)
- Modality: Behaviour-cloning policy acts in an Embodied-Gaussians digital twin kept synchronized with the real robot at 60 Hz; can run virtual-only (offline) or hardware-in-the-loop; scored by success on long-horizon PushT.
- Measures: Whether checkpoint rankings from virtual-only rollouts in a dynamic digital twin match real-world rankings.
- Size: 1 task (PushT); 4 checkpoints (10k-50k steps); 60 evaluations per success rate (20 poses x 3)
- Reported metrics: Relative ordering of checkpoints preserved between virtual and real; absolute rates differ slightly (numbers in Fig. 7, no coefficient stated).
- Cost evidence: Franka Emika, RTX 6000 Ada, 3 RealSense D455 at 90 fps; 30 real + 30 sim-augmented demos.
- Validity evidence: Qualitative ranking preservation on one task only; weak.
- Notes: Level 6 assigned because the twin runs with real hardware in the loop; virtual-only mode is level 5.

### jangir2025robotarenainf: RobotArena Infinity (2025)

- Org: Carnegie Mellon University. Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2510.23571 (arXiv 2510.23571)
- Modality: VLAs act closed-loop in ~100 sim environments auto-reconstructed from demonstration videos (BridgeSim, DROIDSim, RH20TSim) plus perturbations; scored by Gemini 2.5 Pro task-progress on frames + sim state, and by crowdsourced pairwise human preferences.
- Measures: Scalable ranking of generalist policies via real-to-sim translation, with VLM progress scores validated against human preferences.
- Size: ~100 nominal environments (70 BridgeSim) with hundreds of perturbations; 6 VLAs; 8,749 human pairwise preferences
- Reported metrics: Human and VLM policy rankings match exactly (6 policies); one task recreated in real to check consistency (qualitative).
- Cost evidence: 8,749 crowdworker preference pairs; written justification improved annotation accuracy; per-scene reconstruction cost not stated.
- Validity evidence: VLM-vs-human ranking agreement only; sim-vs-real quantified on a single task qualitatively. Weak on real-world validity.

### wang2026r2seval: R2S-Eval (2026)

- Org: not stated (Chinese academic/industry group). Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2609.03276 (arXiv 2609.03276)
- Modality: Policies rolled out in real-to-sim calibrated scenes; rollout videos judged pairwise by a VLM; preferences aggregated into rankings.
- Measures: Whether VLM pairwise judgment of calibrated-sim rollouts reproduces hardware policy rankings while cutting hardware effort.
- Size: 6 policies (pi0, pi0.5, OpenVLA, NORA-Long, SmolVLA, X-VLA); 7 real tasks; 20 real trials/task; 200 sim trials/task
- Reported metrics: Spearman 0.957 and Pearson 0.978 between sim-VLM ranking and hardware ranking; VLM-human agreement 91.9% (real-to-sim) and 82.9% (LIBERO).
- Cost evidence: Operator time in conventional evaluation grows ~linearly with trials; R2S-Eval needs hardware only for initial calibration.
- Validity evidence: Ranking correlation with hardware and VLM-human agreement both reported.
- Notes: Very recent preprint (Sept 2026); org unverified.

### ranawaka2026simfoundry: SimFoundry (2026)

- Org: NVIDIA / Stanford / UT Austin. Kind: tooling. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2606.28276 (arXiv 2606.28276)
- Modality: Zero-shot real-to-sim scene construction from a video; digital twins and edited variants used for policy training and closed-loop evaluation; success rate.
- Measures: Fidelity of automatically generated digital twins as evaluation proxies and as training data.
- Size: 7 manipulation tasks, 5 policy architectures
- Reported metrics: Mean Pearson r=0.911 sim-vs-real; MMRV 0.018; cousin-scene training gains 17-40%.
- Cost evidence: none stated
- Validity evidence: Paired sim/real evaluation across 7 tasks and 5 architectures.
- Notes: Real trial counts not extracted.

### lu2026seeing: From Seeing to Simulating (digital cousins, WorldComposer) (2026)

- Org: Peking University and collaborators. Kind: tooling. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2604.15805 (arXiv 2604.15805)
- Modality: Real panoramas mapped to Isaac Sim scenes plus semantically/geometrically edited cousin scenes; policies (ACT, DP, SmolVLA, pi0) evaluated closed-loop; success rate.
- Measures: Sim-to-real correlation of generated scenes and value of cousin-scene data for generalization.
- Size: 6 tasks (rigid, articulated, deformable/fluid), 4 policies, 20 real trials per configuration
- Reported metrics: Pearson r=0.91 sim vs real success; 50 real + 100 sim trajectories reach 0.57 vs 0.33 real-only on unseen scenes.
- Cost evidence: 50 automated trajectories in ~30 min on one RTX 4090, 6 GB VRAM; 20 real trials per configuration.
- Validity evidence: Paired evaluation r=0.91; sim failures reported as reliable predictors of real failures.

### liu2026joyaisim: JoyAI-Sim (2026)

- Org: JD.com (JoyAI). Kind: tooling. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2606.16776 (arXiv 2606.16776)
- Modality: Real tabletop tasks reconstructed as calibrated Isaac Sim digital twins; policy checkpoints evaluated closed-loop; human embodied inspection of motion naturalness.
- Measures: Sim-real consistency of digital-twin evaluation for long-horizon tidy-up tasks and a bidirectional robot-sim-human data pipeline.
- Size: 2 tidy-up scenarios; 100 matched real trajectories replayed
- Reported metrics: Pearson r=0.89, Spearman 0.78 sim vs real success; ~90% of replays reproduce real object-placement outcomes.
- Cost evidence: 8 GPUs, 64 concurrent envs, 128 evaluation episodes per hour.
- Validity evidence: Paired checkpoint evaluation; replay consistency 90%.
- Notes: 37 authors; industrial system, limited external replication.

### yang2026robolab: RoboLab / RoboLab-120 (2026)

- Org: NVIDIA. Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2604.09860 (arXiv 2604.09860)
- Modality: DROID-configuration policies act closed-loop in Isaac Lab photoreal scenes; 120 pick-and-place tasks over visual/procedural/relational axes at 3 difficulty levels; 10 trials per policy per task.
- Measures: Competency-axis analysis of generalist policies and whether sim scores proxy real-world quality (compared to RoboArena Elo).
- Size: 120 tasks; 5 policies; 4 with real (RoboArena) scores
- Reported metrics: Spearman rho=1.00 and Pearson r=0.68 between RoboLab-120 success and RoboArena Elo (n=4 policies).
- Cost evidence: none stated
- Validity evidence: Ranking preserved for 4 policies against RoboArena; small n.

### yang2025benchmarking: Robot Policy Evaluation for Sim-to-Real Transfer: A Benchmarking Perspective (2025)

- Org: NVIDIA. Kind: position. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2508.11117 (arXiv 2508.11117)
- Modality: Position paper: proposes high-visual-fidelity sim, graded task complexity and perturbation, and explicit quantification of sim-real performance alignment.
- Measures: Argues how sim benchmarks should be built so that scores align with real deployment.
- Size: n/a
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated

### pumacay2024colosseum: THE COLOSSEUM (2024)

- Org: University of Washington / USC. Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2402.08191 (arXiv 2402.08191)
- Modality: Manipulation models act closed-loop in RLBench/CoppeliaSim on 20 tasks under 14 perturbation axes (colour, texture, size, lighting, distractors, camera pose, physics); binary success.
- Measures: Generalization degradation under controlled environmental perturbations, with a real-world check of perturbation effects.
- Size: 20 tasks x 14 perturbation axes; 5 models; real: 4 tasks on Franka Panda, 10 episodes x 3 runs per factor
- Reported metrics: Success drops 30-50% per perturbation, >=75% with combined perturbations; sim-real correlation of perturbation effects R^2 = 0.614.
- Cost evidence: Real validation: 4 tasks, 5 demos each, 2 alternate variations per factor, 10 episodes x 3 runs.
- Validity evidence: Moderate R^2=0.614 between sim and real perturbation sensitivities.

### liu2023libero: LIBERO (2023)

- Org: UT Austin. Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2306.03310 (arXiv 2306.03310)
- Modality: Language-conditioned manipulation policies act closed-loop in robosuite/MuJoCo; 130 tasks in suites (Spatial, Object, Goal, Long/100); binary success from state predicates; human teleop demos for all tasks.
- Measures: Knowledge transfer in lifelong robot learning; de-facto VLA leaderboard.
- Size: 130 tasks, 4 suites; 50 demos per task
- Reported metrics: Sequential finetuning beats lifelong methods on forward transfer; no single visual encoder best.
- Cost evidence: vla-eval (2026) runs 2,000 LIBERO episodes in ~18 min parallel vs 14 h sequential.
- Validity evidence: Negative evidence from others: PolaRiS finds LIBERO scores cluster at 90-95% regardless of real performance; LIBERO-PRO shows 90%+ collapsing to 0% under object/instruction perturbation; LIBERO-Plus 95% to <30% under camera/initial-state shifts; vla-eval shows single undocumented parameters move scores by up to 55 pp.
- Notes: Saturated; useful mainly as the cautionary example.

### zhou2025liberopro: LIBERO-PRO (2025)

- Org: not stated (Lichao Sun group, Lehigh). Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2510.03827 (arXiv 2510.03827)
- Modality: Same LIBERO closed-loop sim with perturbations of manipulated objects, initial states, instructions and environments; binary success.
- Measures: Whether high LIBERO scores reflect task understanding or memorized trajectories.
- Size: 4 perturbation dimensions over LIBERO tasks
- Reported metrics: Models >90% on standard LIBERO drop to 0.0% under perturbation; models continue executing after object substitution or corrupted instructions.
- Cost evidence: none stated
- Validity evidence: Shows in-distribution sim success has near-zero predictive value for even mild distribution shift; no real-robot data.

### fei2025liberoplus: LIBERO-Plus (2025)

- Org: Fudan University (OpenMOSS). Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2510.13626 (arXiv 2510.13626)
- Modality: LIBERO closed-loop sim with 7 perturbation dimensions (layout, camera viewpoint, robot initial state, language, lighting, background texture, sensor noise); binary success.
- Measures: Robustness of VLAs and sensitivity to each perturbation dimension.
- Size: 7 perturbation dimensions; multiple SOTA VLAs
- Reported metrics: 95% to below 30% under modest camera/initial-state perturbations; models largely ignore language instructions.
- Cost evidence: none stated
- Validity evidence: No real-robot data; demonstrates false-confidence of nominal benchmark scores.

### nasiriany2024robocasa: RoboCasa (2024)

- Org: UT Austin / NVIDIA. Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2406.02523 (arXiv 2406.02523)
- Modality: Mobile-manipulation policies act closed-loop in robosuite/MuJoCo kitchens (120 scenes, 2,509 objects, generative-AI textures); 100 tasks (25 atomic, 75 LLM-composed); success from predicates.
- Measures: Scaling of imitation learning with synthetic data; sim data usefulness for real deployment.
- Size: 120 scenes, 2,509 objects / 153 categories, 100 tasks, 100K+ trajectories
- Reported metrics: Real robot: real-only 13.6% vs real+sim co-training 24.4% on seen objects (2.6% vs 9.3% unseen).
- Cost evidence: Real experiments: Franka Panda on mobile base, 3 tasks, 50 trials per task across 5 scenes.
- Validity evidence: Sim data transfers (training utility) but no sim-vs-real evaluation correlation reported.

### nasiriany2026robocasa365: RoboCasa365 (2026)

- Org: UT Austin. Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2603.04356 (arXiv 2603.04356)
- Modality: Household mobile manipulation in RoboCasa sim; 365 tasks across 2,500 kitchens; success from predicates.
- Measures: Reproducible large-scale benchmark for generalist household robots; effect of task diversity, data scale, environment variation.
- Size: 365 tasks, 2,500 kitchens, 600+ h human demos, 1,600+ h synthetic demos
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated
- Notes: No sim-to-real validity evidence found in abstract.

### li2024behavior1k: BEHAVIOR-1K / OmniGibson (2024)

- Org: Stanford. Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2403.09227 (arXiv 2403.09227)
- Modality: Embodied agents act closed-loop in OmniGibson (Isaac Sim based; rigid, deformable, liquids); 1,000 activities specified in predicate logic with initial/goal conditions; success from goal predicates.
- Measures: Long-horizon household activity completion; includes a sim-to-real calibration study.
- Size: 1,000 activities, 50 scenes, 9,000+ objects
- Reported metrics: CollectTrash transfer on Tiago: sim ~40% (50 runs) vs real with oracle perception ~22% (27 runs) vs real with trained vision policy 0% (26 runs).
- Cost evidence: Real study: 1 activity, 27 + 26 real runs on a bimanual mobile manipulator.
- Validity evidence: Direct evidence of a large sim-real gap; failure modes differ (sim: wrong primitive; real: 40% grasp failures, 44% perception errors).

### chen2025robotwin2: RoboTwin 2.0 (2025)

- Org: HKU / SJTU and collaborators. Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2506.18088 (arXiv 2506.18088)
- Modality: Bimanual policies act closed-loop in SAPIEN-based sim with domain randomization over clutter, lighting, background, table height, language; 50 tasks, 5 embodiments; binary success.
- Measures: Robust bimanual manipulation and the training value of randomized synthetic data.
- Size: 50 tasks, 731 objects / 147 categories, 5 embodiments
- Reported metrics: VLA with synthetic + 10 real demos: +367% relative over 10-demo baseline; zero-shot synthetic-only: +228%.
- Cost evidence: none stated
- Validity evidence: Training transfer only. WorldEval reports RoboTwin-based real-to-sim evaluation at Pearson 0.411 / MMRV 0.261 against real success, i.e. weak evaluation validity.

### geng2025roboverse: RoboVerse / MetaSim (2025)

- Org: UC Berkeley / PKU and collaborators. Kind: tooling. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2504.18904 (arXiv 2504.18904)
- Modality: Simulator-agnostic configuration (MetaSim) running tasks across multiple physics engines and renderers; benchmarks graded by generalization level and sim-to-real transferability; success rate.
- Measures: Unified platform, dataset and benchmark protocol; claims improved sim-to-real transfer.
- Size: 1,000+ tasks, 10M+ transitions (from search summary; not in abstract page)
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Sim-to-real transfer experiments reported; no correlation coefficient in abstract.

### james2019rlbench: RLBench (2019)

- Org: Imperial College London. Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/1909.12271 (arXiv 1909.12271)
- Modality: Policies act closed-loop in CoppeliaSim/PyRep with RGB-D-segmentation from shoulder stereo and wrist cameras; 100 hand-designed tasks; infinite planner demos; binary success.
- Measures: Multi-task manipulation learning; base of COLOSSEUM and PerAct-style evaluation.
- Size: 100 tasks
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated
- Notes: Included as the substrate of COLOSSEUM; no sim-to-real validity evidence.

### szot2021habitat2: Habitat 2.0 / Home Assistant Benchmark (2021)

- Org: Meta AI (FAIR). Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2106.14405 (arXiv 2106.14405)
- Modality: Mobile manipulation agents act closed-loop in ReplicaCAD apartments (artist-authored, matching real spaces) with articulated objects; tasks tidy house, prepare groceries, set table; success from state.
- Measures: Rearrangement capability; throughput of physics-enabled sim.
- Size: 3 HAB task suites; ReplicaCAD apartments
- Reported metrics: none stated
- Cost evidence: 25,000+ sim steps/s (850x real-time) on an 8-GPU node.
- Validity evidence: none stated

### puig2023habitat3: Habitat 3.0 (2023)

- Org: Meta AI (FAIR). Kind: benchmark. Ladder level: 4. Safety focus: True. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2310.13724 (arXiv 2310.13724)
- Modality: Robot policies act closed-loop alongside simulated humanoids or real humans controlling avatars via keyboard/VR; Social Navigation and Social Rearrangement tasks; success and efficiency metrics.
- Measures: Human-robot collaboration in homes, including safe following of humans; human-in-the-loop evaluation of learned policies.
- Size: 2 collaborative tasks; humanoid avatars
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Reports that automated-humanoid evaluation trends carry over to human-in-the-loop evaluation (qualitative in abstract).
- Notes: safety_focus true because of human-proximity tasks; venue ICLR 2024 per common citation, not confirmed on abstract page.

### tao2024maniskill3: ManiSkill3 (2024)

- Org: UC San Diego (Hao Su lab). Kind: tooling. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2410.00425 (arXiv 2410.00425)
- Modality: GPU-parallel SAPIEN simulation and rendering; 12 task domains incl. digital-twin scenes; underlying engine of SIMPLER.
- Measures: Simulation throughput and breadth; not itself a validity study.
- Size: 12 domains; millions of demo frames
- Reported metrics: none stated
- Cost evidence: 10-1000x faster with 2-3x less GPU memory than other platforms; up to 30,000+ FPS with rendering.
- Validity evidence: none stated

### mittal2025isaaclab: Isaac Lab (2025)

- Org: NVIDIA. Kind: tooling. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2511.04831 (arXiv 2511.04831)
- Modality: GPU-parallel physics + photoreal rendering with actuator models, multi-rate sensors, domain randomization for RL/IL; successor of Isaac Gym.
- Measures: Simulation infrastructure; used by RoboLab and REALM-style evaluations.
- Size: n/a (105 authors)
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated

### makoviychuk2021isaacgym: Isaac Gym (2021)

- Org: NVIDIA. Kind: tooling. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2108.10470 (arXiv 2108.10470)
- Modality: GPU-resident physics with tensors passed directly to PyTorch; RL training platform.
- Measures: Throughput for RL policy training in simulation.
- Size: unknown
- Reported metrics: none stated
- Cost evidence: 2-3 orders of magnitude speedup over CPU-sim + GPU-NN pipelines on a single GPU.
- Validity evidence: none stated

### gao2026isaacsim: NVIDIA Isaac Sim survey (2026)

- Org: UNSW Sydney. Kind: study. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: low.
- URL: https://arxiv.org/abs/2606.03551 (arXiv 2606.03551)
- Modality: Survey of Isaac Sim usage patterns, limitations, and synthetic-data generation across 5 domains.
- Measures: Characterises architecture and usability constraints of the simulator used by REALM, RoboLab, JoyAI-Sim.
- Size: unknown
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated
- Notes: Marginal relevance; secondary survey.

### choi2026vlaeval: vla-eval harness (2026)

- Org: Allen Institute for AI / Yonsei. Kind: tooling. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2603.13966 (arXiv 2603.13966)
- Modality: Docker-isolated benchmarks talk to model servers over WebSocket+msgpack; 14 sim benchmarks, 6 model servers; reproduces published success rates with fixed seeds.
- Measures: Reproducibility and throughput of simulated VLA evaluation.
- Size: 14 benchmarks, 6 codebases, 657 published results aggregated
- Reported metrics: Reproductions within ~2 pp; single undocumented settings shift results massively: X-VLA proprio bug 97.8% to 42%; action-mode mismatch 97% to 0%; OpenVLA-OFT quaternion normalization 95% to 56% (LIBERO-Long).
- Cost evidence: 2,000 LIBERO episodes in ~18 min (47x speedup vs 14 h sequential); env throughput 11.2 to 364.6 obs/s.
- Validity evidence: Reproducibility evidence: benchmark scores are fragile to evaluation-harness parameters.

### quevedo2025worldgym: WorldGym (2025)

- Org: Stanford / NYU / Google DeepMind (Sherry Yang). Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2506.00613 (arXiv 2506.00613)
- Modality: Policy actions fed to an autoregressive action-conditioned video world model from an initial frame; Monte Carlo rollouts scored by GPT-4o as reward; success rate.
- Measures: Whether success in a learned world model predicts real success and preserves policy rankings.
- Size: 17 Bridge tasks, 3 policies (RT-1-X, Octo, OpenVLA); 510 real trials (10 per task per policy)
- Reported metrics: Pearson r=0.78 with real success; mean success differs by 3.3%; GPT-4o judge TPR 0.81, TNR 0.97, FPR 0.03.
- Cost evidence: All rollouts under one hour on a single GPU; world model trained 300k steps on 2x A100 80GB.
- Validity evidence: Paired real evaluation r=0.78; object-interaction realism remains a limitation.
- Notes: World-model evaluators placed at level 5 (learned photoreal simulator, closed-loop, no physics engine); see synthesis for the ladder caveat.

### li2025worldeval: WorldEval / Policy2Vec (2025)

- Org: Midea Group / East China Normal University. Kind: benchmark. Ladder level: 5. Safety focus: True. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2505.19017 (arXiv 2505.19017)
- Modality: Policy latent actions drive a video generation model; generated rollout videos scored for success; also detects unsafe/irregular actions (video collapse).
- Measures: Ranking of real-world policies via world-model rollouts; unsafe-action flagging.
- Size: 5 tasks, 4 policies (DP, OpenVLA, DexVLA, pi0); 1,000+ real trials; 1,400 training trajectories
- Reported metrics: Pearson r=0.942 avg (0.958 / 0.887 / 0.980 per task), MMRV 0.044; RoboTwin real-to-sim baseline: Pearson 0.411, MMRV 0.261.
- Cost evidence: 1,000+ real trials as ground truth.
- Validity evidence: Paired real evaluation; 6x better correlation than a physics real-to-sim baseline on the same policies.

### gemini2025veo: Gemini Robotics policies in a Veo world simulator (2025)

- Org: Google DeepMind (Gemini Robotics Team). Kind: red-team. Ladder level: 5. Safety focus: True. Speaker link: Sindhwani. Confidence: high.
- URL: https://arxiv.org/abs/2512.10675 (arXiv 2512.10675)
- Modality: Bimanual (ALOHA 2) policy actions conditioned into the Veo video model with multi-view consistency; generative image editing creates novel objects, backgrounds, distractors; 8-second rollouts scored binary by human raters; red-teaming for physical and semantic safety violations.
- Measures: Nominal and OOD relative policy performance and safety red-teaming, validated against real evaluations.
- Size: 8 policy checkpoints, 5 tasks, 80 scene-instruction combinations; 1,600+ real-world evaluations
- Reported metrics: OOD single-policy: Pearson 0.86, MMRV 0.06; strong linear correlation in nominal setting; unsafe behaviours (contact with human hand, damaging laptop) found in sim and replicated in real.
- Cost evidence: 1,600+ real episodes for validation; all scoring by human raters; per-rollout compute not stated.
- Validity evidence: Paired real evaluation of 8 checkpoints; red-team findings reproduced on hardware.
- Notes: Vikas Sindhwani is a co-author. Only entry in this sweep with explicit safety red-teaming validated on hardware.

### guo2025ctrlworld: Ctrl-World (2025)

- Org: Stanford / Tsinghua. Kind: tooling. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2510.10125 (arXiv 2510.10125)
- Modality: Multi-view action-conditioned world model trained on DROID (95k trajectories, 564 scenes); pose-conditioned memory; used to rank policies and synthesize fine-tuning data.
- Measures: Policy ranking without real rollouts; data synthesis for policy improvement.
- Size: DROID 95k trajectories, 564 scenes; 20+ s consistent rollouts
- Reported metrics: +44.7% success after SFT on synthesized data; ranking accuracy claimed (PolaRiS measured Ctrl-World eval MMRV 0.22).
- Cost evidence: none stated
- Validity evidence: External: PolaRiS reports MMRV 0.22 for Ctrl-World-based evaluation, i.e. notable mis-rankings.

### jeon2026roboworld: RoboWorld (2026)

- Org: KAIST. Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2607.01060 (arXiv 2607.01060)
- Modality: Fast autoregressive video world model with Step Forcing; rollouts scored by a task-progress-aware VLM.
- Measures: Correlation of neural-simulator evaluation with real policy performance.
- Size: unknown
- Reported metrics: Pearson r=0.989, Spearman 0.970 with real evaluation (policy/task counts not in abstract).
- Cost evidence: none stated
- Validity evidence: Reported correlation only; sample size unknown.

### gigaworld2026roadmap: GigaWorld-1 / WMBench (2026)

- Org: GigaAI (Open GigaAI). Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2607.02642 (arXiv 2607.02642)
- Modality: Video world models act as surrogate evaluators; WMBench pairs world-model rollouts with real executions and scores outcome with a VLM; 8 task families.
- Measures: How well world models rank policies vs real, and what drives evaluator quality (long-horizon action-faithful consistency over visual realism).
- Size: 7 world models, 4 action representations, 324k+ rollouts, 2,989 paired real/sim trajectories, 12k+ h video
- Reported metrics: Ranking correlation rho=0.61 for Cosmos-Predict2.5 baseline; GigaWorld-1 +14.9% on alignment metric; VLM outcome judge vs human: 87.8% exact agreement, Spearman 0.757.
- Cost evidence: 32 NVIDIA H20 GPUs for training; 100+ challenge teams.
- Validity evidence: Largest paired real/world-model dataset found; VLM-human agreement quantified.

### li2026dworldeval: dWorldEval (2026)

- Org: Midea Group (inferred from WorldEval lineage). Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: low.
- URL: https://arxiv.org/abs/2604.22152 (arXiv 2604.22152)
- Modality: Discrete diffusion world model over unified vision/language/action tokens with a progress token that auto-declares success.
- Measures: Scalable policy evaluation across LIBERO, RoboTwin and real tasks; claims to outperform WorldEval, Ctrl-World, WorldGym.
- Size: unknown
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Claims only; numbers not in abstract.

### wang2026interactive: Interactive World Simulator (2026)

- Org: Columbia / UIUC / TRI. Kind: tooling. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2603.08546 (arXiv 2603.08546)
- Modality: Consistency-model world simulator from robot interaction data; policies (DP, ACT, pi0, pi0.5) evaluated closed-loop; 4 tasks incl. deformables and piles.
- Measures: Whether world-model evaluation preserves policy ordering; training value of generated data.
- Size: 4 tasks, 4 policies, 10 real trials per policy-task, 20 initial configs per task
- Reported metrics: Strong positive correlation (coefficients not stated); policies trained on WM data match real-data-trained policies.
- Cost evidence: 15 FPS on a single RTX 4090, stable >10 min.
- Validity evidence: Qualitative: if one policy substantially outperforms another in the simulator it likely does in real; biased absolute rates.

### atreya2025roboarena: RoboArena (2025)

- Org: UC Berkeley / Stanford / 7 institutions. Kind: benchmark. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2506.18123 (arXiv 2506.18123)
- Modality: Real DROID robots at 7 institutions; evaluators choose task and scene, run double-blind A/B rollouts of two policies, give 0-100 progress, binary preference and free-text; Bradley-Terry with task-difficulty parameters fit by EM.
- Measures: Real-world ranking of generalist policies with decentralized, unstandardized tasks.
- Size: 7 policies, 612 pairwise comparisons, 4,284 episodes, 7 institutions
- Reported metrics: Ranking Pearson r=0.94 (vs 0.69 centralized) and MMRV 0.023 (vs 0.141); accurate rankings within ~100 pairwise comparisons; under task-distribution shift r=0.838 vs 0.692.
- Cost evidence: 4,284 real episodes across 7 sites; human evaluator per episode; no per-episode time reported.
- Validity evidence: Ground truth is a large held-out real evaluation; RoboArena rankings track it better than centralized evals. Used as reference by PolaRiS (r=0.98) and RoboLab.

### zhou2025autoeval: AutoEval (2025)

- Org: UC Berkeley / NVIDIA. Kind: tooling. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2503.24278 (arXiv 2503.24278)
- Modality: Real WidowX cells run policies around the clock; learned success classifier (trained on ~1,000 labeled images) scores episodes; learned reset policy (~100 demos) restores scenes; job-queue interface.
- Measures: Whether autonomous real-robot evaluation matches human-conducted evaluation at a fraction of human time.
- Size: 3 cells (drawer, sink, cloth), 5 tasks, 6 policies (OpenVLA, Octo, Open-pi0, MiniVLA, SuSIE variants)
- Reported metrics: Pearson 0.942 and MMRV 0.015 vs human ground truth; success classifier >95% accurate.
- Cost evidence: ~850 episodes per 24 h per cell; >99% reduction in human time; 3 interventions per 24 h; new cell in 1-3 h active effort (<5 h total); WidowX hardware <$3,500.
- Validity evidence: Paired against manual evaluation on the same policies.
- Notes: Best hard cost numbers for real-robot evaluation in the sweep.

### yakefu2025robochallenge: RoboChallenge / Table30 (2025)

- Org: Dexmal / MEGVII and collaborators. Kind: benchmark. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2510.17950 (arXiv 2510.17950)
- Modality: Online remote real-robot evaluation on 10 machines of 4 types (UR5, Franka, Cobot Magic Aloha, ARX-5); 30 tabletop tasks; 10 rollouts per task; staged progress score (100 per task, -0.5 per retry) plus success rate; scene reproduced via reference-episode overlays.
- Measures: Standardized, reproducible large-scale real-robot leaderboard for VLAs.
- Size: 30 tasks, 10 machines, 5 methods at launch
- Reported metrics: none stated
- Cost evidence: Manual scheduling and prop preparation, wait time hours to days; all trajectories, videos and logs released.
- Validity evidence: Reproducibility via visual overlay protocol; intentional environmental variation.
- Notes: 37 alphabetical authors; org inferred from robochallenge.ai.

### selvaraj2026armnetbench: ArmnetBench v0.1 (2026)

- Org: independent (Armnet). Kind: benchmark. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2607.24481 (arXiv 2607.24481)
- Modality: Fleet of low-cost SO-101 arm cells; 7 policies on 12 tasks; single operator labels each rollout successful / suboptimal / failure and resets the scene.
- Measures: Parallel real-world evaluation throughput and quality labels at very low hardware cost.
- Size: 3 cells, 12 tasks, 7 policies, 3,118 episodes (2,518 rollouts + 600 demos)
- Reported metrics: none stated
- Cost evidence: Cell cost $359 (single) / $477 (bimanual); ~10 s active operator time per rollout; one operator supervises 3 cells.
- Validity evidence: No inter-rater agreement reported (single operator).

### arkhangelskiy2026phail: PhAIL (2026)

- Org: independent. Kind: benchmark. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2605.29710 (arXiv 2605.29710)
- Modality: Franka FR3 bin-to-bin picking of 4 object categories; time-to-success CDFs scored as Human-Relative Throughput with bootstrap CIs and Kolmogorov-Smirnov tests; 396 human teleop reference episodes.
- Measures: Distributional (time-to-success) evaluation of VLAs versus a human baseline, and adequacy of standard N<=25 practice.
- Size: ~995 episodes; 4 VLAs; 26-46 rollouts per condition
- Reported metrics: Best VLA ~7x slower than human per operation; KS test resolved 2 of 3 close comparisons at <=30 rollouts where binary metrics failed.
- Cost evidence: Survey of 13 real-robot VLA papers (2023-2025): modal 10-20 rollouts per condition, none report CIs or paired tests (LBM the exception at N=50-200).
- Validity evidence: Statistical-power evidence: binary success at N<=25 cannot separate close policies.
- Notes: Single-author preprint.

### chen2026robodojo: RoboDojo (2026)

- Org: HKU / Berkeley / MIT and 40+ collaborators. Kind: benchmark. Ladder level: 4. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2607.04434 (arXiv 2607.04434)
- Modality: 42 sim tasks over 5 dimensions (generalization, memory, precision, long-horizon, open-vocabulary) plus 18 real tasks on ARX X5, Piper, Piper X; 10 real trials per task.
- Measures: Unified sim-and-real leaderboard for generalist manipulation policies.
- Size: 42 sim tasks, 18 real tasks, 30 policies in sim, 10 in real (180 real trials per policy)
- Reported metrics: Best real policy pi0.5 at 12.8% overall real success, far below sim.
- Cost evidence: 180 real trials per policy for 10 policies.
- Validity evidence: Sim-real correlation not extracted (truncated); large absolute gap noted.

### zhang2025experiences: Experiences from Benchmarking VLA Models (2025)

- Org: Macquarie University. Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2511.11298 (arXiv 2511.11298)
- Modality: ACT, OpenVLA-OFT, RDT-1B, pi0 evaluated in simulation and on ALOHA Mobile across accuracy/efficiency, distribution shift and instruction following.
- Measures: Practical trade-offs and recurring failure modes (near-miss grasps, premature release, state drift).
- Size: 4 models; sim + real ALOHA Mobile
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated

### jin2026grounding: Grounding Sim-to-Real Generalization (VLA empirical study) (2026)

- Org: CUHK Shenzhen (inferred). Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2603.22876 (arXiv 2603.22876)
- Modality: VLAs trained in simulation (Cobot Magic) with varying domain randomization, rendering fidelity, physics fidelity and RL fine-tuning; tested on a real Piper arm with one RealSense D435.
- Measures: Which simulation design factors actually move real-world success.
- Size: 10,000+ real-world trials
- Reported metrics: Table-height randomization 2.7% to 36.9% real success; spatial+appearance 49.7%; RL fine-tune 5.6% to 33.4% (42.8% with DR); photoreal gains diminish beyond medium fidelity.
- Cost evidence: 10,000+ real trials; platform and protocol released.
- Validity evidence: Large-N factor study of sim-to-real transfer (training side).

### gervet2023navigating: Navigating to Objects in the Real World (2023)

- Org: CMU / Meta AI. Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2212.00922 (arXiv 2212.00922)
- Modality: Classical, modular and end-to-end ObjectNav policies deployed in 6 real homes without maps; success compared to Habitat simulation.
- Measures: Whether sim ObjectNav rankings hold in real homes.
- Size: 6 homes; 3 method families
- Reported metrics: Modular learning 90% real success; end-to-end 77% in sim but 23% in real (54 pp drop); ranking between methods inverts sim to real.
- Cost evidence: none stated
- Validity evidence: Direct evidence of sim-real rank inversion; causes: image domain gap and mismatched failure modes.

### liao2026active: Active Real-World Factor-Based Evaluation (2026)

- Org: University of Minnesota (inferred). Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2607.14439 (arXiv 2607.14439)
- Modality: Probabilistic surrogate over task factors (object pose, camera viewpoint); sequential experimental design picks real-robot evaluation configurations by information gain.
- Measures: Sample-efficient characterization of a policy's performance distribution and failure regions in real hardware evaluation.
- Size: 2,331 real evaluations, 3 tasks, 3 factors
- Reported metrics: 20-40% fewer trials than random testing for the same characterization.
- Cost evidence: 2,331 real-world evaluations.
- Validity evidence: none stated
- Notes: Directly a value-of-information style approach to evaluation design.

### kressgazit2024empirical: Robot Learning as an Empirical Science (2024)

- Org: Toyota Research Institute / Cornell. Kind: position. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2409.09491 (arXiv 2409.09491)
- Modality: Best-practice guidance demonstrated on Franka Panda (single and bimanual) tasks: push bowl (6 policies), flip pancake (3), fold shirt (2); Bayesian Beta posteriors on success.
- Measures: Argues success-rate point estimates without conditions, CIs and failure analysis are uninformative.
- Size: 3 real tasks, up to 6 policies
- Reported metrics: Illustration: 5-6 trials give heavily overlapping posteriors; 18-20 tighten; 150+ needed to separate similar policies.
- Cost evidence: Implicit: separating close policies requires >100 real trials per policy.
- Validity evidence: Statistical argument; no sim-real component.

### vincent2024generalizable: How Generalizable Is My Behavior Cloning Policy? (2024)

- Org: Stanford / Toyota Research Institute. Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2405.05439 (arXiv 2405.05439)
- Modality: Stochastic-ordering bounds on the full performance distribution from a minimal number of rollouts; validated in sim and hardware manipulation.
- Measures: Worst-case distributional performance bounds at user-specified confidence with few rollouts.
- Size: unknown
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Bounds validated empirically in sim and hardware.

### snyder2025stopping: Policy comparison with near-optimal stopping (2025)

- Org: Princeton / Toyota Research Institute. Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2503.10966 (arXiv 2503.10966)
- Modality: Sequential hypothesis test for comparing two imitation policies from binary outcomes; adaptive stopping without p-hacking.
- Measures: Minimal number of real trials to decide which of two policies is better with controlled error.
- Size: unknown
- Reported metrics: Up to 32% fewer trials than baselines; >160 sim rollouts saved in a multi-task case.
- Cost evidence: Trial savings quantified; adopted by the TRI LBM study.
- Validity evidence: none stated

### snyder2026beyond: Beyond Binary Success (SAVI policy comparison) (2026)

- Org: Princeton / UPenn / Toyota Research Institute. Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2603.13616 (arXiv 2603.13616)
- Modality: Safe anytime-valid inference for sequential policy comparison on binary, partial-credit, reward and smoothness metrics; sim and real data.
- Measures: Evaluation burden reduction from fine-grained metrics and sequential testing.
- Size: unknown
- Reported metrics: Up to 70% fewer trials than batch testing; up to 50% fewer than binary sequential methods.
- Cost evidence: Trial-count reductions quantified.
- Validity evidence: none stated

### badithela2025suresim: SureSim (2025)

- Org: Princeton / Toyota Research Institute. Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2510.04354 (arXiv 2510.04354)
- Modality: Prediction-powered inference: many ManiSkill3 sim rollouts plus a small paired set of real rollouts yield non-asymptotic confidence intervals on real mean performance.
- Measures: How much real hardware testing an imperfect simulator can replace while keeping valid CIs on real success.
- Size: Diffusion policy: 60 paired trials + up to 700 sims; pi0: 60 paired + up to 2,100 sims; ~120 real objects, 2,100 sim objects
- Reported metrics: CI width 0.16 vs 0.187 classical (-14.4%); >25% hardware savings at moderate sim-real correlation, >20% fewer real trials on average; CIs do not collapse when sim is uninformative.
- Cost evidence: Explicit hardware-trial savings as a function of sim-real correlation.
- Validity evidence: Formal guarantee: intervals remain valid regardless of simulator bias.
- Notes: Closest existing formalization of 'value of a sim trial vs a real trial'.

### mahboob2026betting: Betting for Sim-to-Real Performance Evaluation (2026)

- Org: Iowa State University. Kind: study. Ladder level: None. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2604.24018 (arXiv 2604.24018)
- Modality: Betting-based estimator combining simulation and limited physical tests; theory on when it beats Monte Carlo; synthetic and simulated pick-and-place demo.
- Measures: Sample-efficiency of sim-assisted estimation of real performance under a testing budget.
- Size: unknown
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated
- Notes: Level null: no hardware experiments in abstract.

### tri2025lbm: A Careful Examination of Large Behavior Models (2025)

- Org: Toyota Research Institute. Kind: study. Ladder level: 7. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2507.05331 (arXiv 2507.05331)
- Modality: Blind randomized real and sim rollouts of multitask diffusion policies; sequential tests with Bonferroni, Welch t-tests, Bayesian posteriors, compact letter display at 95%.
- Measures: Effect of multitask pretraining with statistical confidence; sets the high-water mark for evaluation rigor.
- Size: ~1,800 real rollouts (50 per task-policy-condition, 8 real tasks); 200 sim rollouts per condition, 24 sim tasks
- Reported metrics: Pretraining improves success and robustness; some tasks better in real than sim (no systematic correlation reported).
- Cost evidence: 50 real rollouts per condition considered necessary; 1,800 real rollouts total.
- Validity evidence: Notes sim-real discrepancies without quantifying correlation.

### wan2026nofreechecker: No Free Checker: survey of verifiers (2026)

- Org: Zhejiang University. Kind: study. Ladder level: None. Safety focus: True. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2609.09250 (arXiv 2609.09250)
- Modality: Survey of ~150 verifiers (success detectors, reward models, runtime monitors, safety filters, formal specs) along availability (cost, latency, frequency) and credibility (agreement with human labels, downstream performance, reward-hacking robustness).
- Measures: Trade-off between cheap/frequent verdicts and reliable verdicts; proposes 9 metrics for verifier claims.
- Size: ~150 verifiers
- Reported metrics: Finding: credibility falls as availability rises across all four verifier families.
- Cost evidence: none stated
- Validity evidence: Meta-level: catalogues how verifiers are validated (human agreement etc.).

### huang2026cimse: Critical Interval MSE (2026)

- Org: Tsinghua University. Kind: study. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2606.29898 (arXiv 2606.29898)
- Modality: Offline open-loop validation on held-out real demonstrations: action MSE restricted to task-critical segments after alignment; compared to closed-loop success over many checkpoints.
- Measures: Whether an offline metric can rank checkpoints without rollouts.
- Size: unknown
- Reported metrics: Spearman -0.87 with closed-loop success vs -0.61 for raw MSE.
- Cost evidence: none stated
- Validity evidence: Correlation with real closed-loop success; PolaRiS reports plain MSE as a low-correlation baseline.
- Notes: Level 5 as open-loop replay of real data; arguably lower than closed-loop levels.

### liu2026mdpgap: Sim-to-Real Gap of Foundation Model Agents (MDP view) (2026)

- Org: Arizona State University. Kind: position. Ladder level: 0. Safety focus: False. Speaker link: none. Confidence: low.
- URL: https://arxiv.org/abs/2606.07017 (arXiv 2606.07017)
- Modality: Position: frames LLM/FM agent benchmark-vs-deployment gap as observation/action/transition/reward gaps and imports robotics sim-to-real methods.
- Measures: Conceptual mapping; no experiments.
- Size: unknown
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated
- Notes: Marginal; included because it links ladder level 0 to the sim-to-real vocabulary.

### dauner2024navsim: NAVSIM (2024)

- Org: University of Tuebingen / NVIDIA / OpenDriveLab. Kind: benchmark. Ladder level: 5. Safety focus: True. Speaker link: Pavone. Confidence: high.
- URL: https://arxiv.org/abs/2406.15349 (arXiv 2406.15349)
- Modality: Planner outputs a trajectory from real sensor logs (OpenScene/nuPlan); non-reactive pseudo-simulation computes PDM Score = (no collision x drivable area) x weighted(ego progress 5, TTC 5, comfort 2).
- Measures: Safety-aware open-loop proxy for closed-loop driving performance on real data.
- Size: navtrain 103k, navtest 12k, navmini 396 scenarios; 143 teams / 463 entries at CVPR 2024
- Reported metrics: PDMS correlates better with closed-loop scores than displacement metrics (Spearman/Pearson, values in paper); constant-velocity baseline 79% unfiltered vs 22% filtered; human 95%.
- Cost evidence: none stated
- Validity evidence: Internal correlation to closed-loop sim; external cross-benchmark study (Wang 2026) finds Spearman 0.90 with Bench2Drive but non-monotonic with rank inversions.
- Notes: Marco Pavone is a co-author.

### wang2026openloop: Do Open-Loop Metrics Predict Closed-Loop Driving? (2026)

- Org: not stated. Kind: study. Ladder level: None. Safety focus: True. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2605.00066 (arXiv 2605.00066)
- Modality: Cross-references published NAVSIM (open-loop PDMS sub-metrics) and Bench2Drive (closed-loop CARLA driving score) results for 15 methods (8 with complete pairs).
- Measures: Predictive validity of safety-aware open-loop metrics for closed-loop outcomes.
- Size: 15 methods, 8 fully paired
- Reported metrics: Spearman 0.90 PDMS vs driving score but non-monotonic with ranking inversions; ego progress is the strongest single predictor, beating collision metrics; a 3-metric formula matches the 5-metric one.
- Cost evidence: none stated
- Validity evidence: Direct cross-level validity study (level 5 replay vs level 4 closed-loop); ADE/FDE previously shown to have no reliable correlation.
- Notes: Level null because it compares two levels.

### dauner2023parting: Parting with Misconceptions (nuPlan) (2023)

- Org: University of Tuebingen. Kind: study. Ladder level: 5. Safety focus: True. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2306.07962 (arXiv 2306.07962)
- Modality: Rule-based and learned planners evaluated on nuPlan open-loop (ego forecasting) and closed-loop (reactive/non-reactive) metrics.
- Measures: Misalignment between open-loop forecasting metrics and closed-loop planning quality.
- Size: unknown
- Reported metrics: Centerline-only context gives best open-loop score while ignoring agents; simple rule-based PDM planner won the nuPlan 2023 challenge.
- Cost evidence: none stated
- Validity evidence: Shows open-loop metrics reward behaviour that is unsafe in closed loop.

### jia2024bench2drive: Bench2Drive (2024)

- Org: Shanghai Jiao Tong University. Kind: benchmark. Ladder level: 4. Safety focus: True. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2406.03877 (arXiv 2406.03877)
- Modality: End-to-end driving models act closed-loop in CARLA v2 over 220 routes with 44 interactive scenarios, 23 weathers, 12 towns; Driving Score and Success Rate.
- Measures: Multi-ability closed-loop driving performance; alternative to open-loop L2/collision metrics.
- Size: 220 routes, 44 scenarios, 2M annotated training frames, 13,638 clips
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Argues open-loop L2 and collision rate cannot reflect driving performance; no on-road validation.

### caesar2021nuplan: nuPlan (2021)

- Org: Motional. Kind: benchmark. Ladder level: 5. Safety focus: True. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2106.11810 (arXiv 2106.11810)
- Modality: Planners evaluated in closed-loop replay of 1,500 h real logs (4 cities) with reactive or non-reactive agents; planning-specific metrics beyond L2.
- Measures: Closed-loop planning quality on real-world scenario distribution.
- Size: 1,500 h driving, 4 cities, 70+ scenario types
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated
- Notes: Org is Motional (fetch summary misattributed).

### yu2025drivee2e: DriveE2E (2025)

- Org: AIR, Tsinghua University. Kind: benchmark. Ladder level: 5. Safety focus: True. Speaker link: none. Confidence: medium.
- URL: https://arxiv.org/abs/2509.23922 (arXiv 2509.23922)
- Modality: Real intersection traffic (100 h infrastructure video, 15 intersections) replayed as 800 dynamic scenarios inside CARLA digital twins; closed-loop end-to-end driving evaluation.
- Measures: Closed-loop driving on real-derived scenario distributions instead of hand-authored CARLA scenarios.
- Size: 800 scenarios, 15 intersections, 100 h video
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated

### montali2023wosac: Waymo Open Sim Agents Challenge (WOSAC) (2023)

- Org: Waymo. Kind: benchmark. Ladder level: 5. Safety focus: False. Speaker link: none. Confidence: high.
- URL: https://arxiv.org/abs/2305.12032 (arXiv 2305.12032)
- Modality: Sim agents produce 32 joint rollouts of 8 s for up to 128 agents from 1.1 s context on Waymo Open Motion Data; realism scored by approximate NLL of logged human trajectories under kinematic, interaction and map-based metrics.
- Measures: Realism of simulated traffic agents relative to logged real behaviour (a validity metric for the simulator itself).
- Size: WOMD scenarios; yearly challenge since 2023
- Reported metrics: 2024 winner BehaviorGPT realism 0.7473 (from search summary).
- Cost evidence: none stated
- Validity evidence: Distribution-matching against real logs; does not test whether AV rankings transfer to road.

### euroncap2025virtual: Euro NCAP Safe Driving & Crash Avoidance Virtual Testing protocol v1.00 (2025)

- Org: Euro NCAP. Kind: standard. Ladder level: 4. Safety focus: True. Speaker link: none. Confidence: high.
- URL: https://cdn.euroncap.com/cars/assets/euro_ncap_supporting_protocol_safe_driving_crash_avoidance_virtual_testing_v10_bb5738fef8.pdf
- Modality: OEM simulates AEB/FCW/ELK grid cells (CCR, CCFtap, CPNA, CPNCO, ELK road edge) with perfect perception assumed and sensors placed as physical; outputs 100 Hz ISO-MME channels; Euro NCAP physically spot-tests randomly selected grid cells and compares.
- Measures: Whether an OEM's virtual test results may substitute for physical Euro NCAP track tests (level 8) in rating predictions.
- Size: Scenario clusters: Frontal-Longitudinal, Frontal-Turning, Frontal-Crossing, Lane-ELK; corner cases plus 3-5 additional cells per cluster
- Reported metrics: Acceptance: >=75% of verification tests per cluster must pass; ISO TS 18571 score on longitudinal acceleration >= [0.5]; KPI tolerances TTC_AEB +-0.2 s (+-0.25 s crossing), TTC_FCW +-0.2/0.5 s, impact speed +-1.0 m/s, remaining distance +-1.0 m, DTLE_ELK +-0.2 m.
- Cost evidence: Physical verification limited to randomly selected grid cells; re-simulation required if validation fails.
- Validity evidence: Codified sim-vs-physical agreement criteria (ISO 18571 time-series score and KPI tolerances) rather than statistical correlation.
- Notes: Read from the downloaded PDF; bracketed values are provisional per the document.
