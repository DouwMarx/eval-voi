# Marco Pavone (Stanford ASL / NVIDIA AV Research): safety-evaluation literature sweep

## Assessment

- Evaluation is central, not incidental, to Pavone's recent work. Since 2021 his group has produced a coherent line on how to evaluate AV/robot safety cheaply and validly: task-aware metrics (2021), perception safety zones (2022), NAVSIM (2024), pseudo-simulation (2025), Sim2Val (2025), X4Val and coverage-aware active evaluation (2026), StressDream (2026, with Bajcsy).
- The Sim2Val / X4Val / coverage-aware trio is the closest existing work to a value-of-information (VOI) framing: it treats cheap proxies (sim, open-loop, old policies) as control variates and quantifies how many real trials they save. Cite these first.
- NAVSIM and pseudo-simulation give the most-cited numbers on proxy validity (PDMS vs closed-loop; R^2 0.7 open-loop, 0.8 pseudo-sim) and cost (13 vs 80 planner calls per scenario; 1-2 GPU-h rendering per scene).
- The Swiss Re / Stanford ADAS campaign (13 vehicles, ~81 track tests each, 8 months) is the group's only fully physical safety evaluation and is the best cost anchor for the expensive end of the sim-to-real ladder.
- Runtime-monitor papers (task-aware risk, SPARQ, FORCE-OPT, Sentinel, martingales, semantic anomaly detection) define reusable monitor-evaluation protocols with TPR/FPR-style numbers, but rarely report cost or field validity.
- Scenario-generation tooling (CTG, CTG++, LCTGen, ProSim, RealGen, BITS, trajdata) is included because it is the substrate of the group's benchmarks; safety_focus is set per entry.
- Not found: any Pavone-authored safety-case methodology paper or hardware-in-the-loop study. NVIDIA world-model simulators (OmniDreams, Cosmos-Drive-Dreams, ReSim) and DriveCritic do not list Pavone as author and are excluded.
- Recommended citations for a VOI-of-safety-evaluation paper: luo2025sim2val, luo2026x4val, parashar2026coverage, cao2025pseudosim, dauner2024navsim, dilillo2024adas, ding2025surprise, seo2026stressdream, luo2021conformal, ivanovic2021planningaware.

sim2real_level scale used: 0 offline logs/QA; 1 offline logs with synthetic edits; 2 abstract/BEV closed-loop sim; 3 sensor-level sim or generative world model; 4 reconstruction/neural sim; 5 sim plus real calibration data; 6 paired sim and real logs; 7 real hardware in lab; 8 real vehicles on closed track/on-water; 9 public-road deployment. null = not applicable.

## Entries (50, all URLs fetched)

### dauner2024navsim: NAVSIM (2024)
- org: Univ. Tübingen / NVIDIA / Stanford (Pavone) | kind: benchmark | sim2real_level: 2 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2406.15349 | arXiv: 2406.15349
- modality: End-to-end driving policy receives real sensor data + ego state from OpenScene/nuPlan; outputs a trajectory; scored by PDM Score (PDMS) computed by non-reactive BEV unrolling over a 4 s horizon at 10 Hz (collision, drivable area, ego progress, TTC, comfort).
- measures: Whether open-loop-style evaluation on real logs can predict closed-loop driving quality; ranks vision-based end-to-end planners on collision/progress/comfort subscores.
- size: navtrain 103k samples, navtest 12k samples (after filtering trivial scenes)
- metrics: PDMS shows higher Spearman correlation with nuPlan closed-loop score than displacement errors; CVPR 2024 challenge: 143 teams, 463 submissions; TransFuser-style methods match UniAD.
- cost: Non-reactive BEV simulation, no sensor rendering; designed to be cheap enough for large-scale benchmarking (thousands of scenes per evaluation).
- validity: Correlation of PDMS with nuPlan closed-loop score reported in-paper; independent 2026 study (arXiv 2605.00066, not Pavone) finds PDMS strongly but non-monotonically correlated with closed-loop Bench2Drive and Spearman 0.90 for a 3-metric variant.
- notes: Pavone is a co-author (NVIDIA). Core citation for cheap-proxy-vs-closed-loop validity.

### cao2025pseudosim: Pseudo-Simulation (NAVSIM v2) (2025)
- org: NVIDIA / Univ. Tübingen / Stanford | kind: benchmark | sim2real_level: 3 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2506.04218 | arXiv: 2506.04218
- modality: Planner is evaluated on real logs augmented with 3D-Gaussian-Splatting synthetic observations (perturbed position/heading/speed); two-stage rollout; scored by Extended PDM Score (EPDMS, nine subscores with multiplicative rule penalties) with proximity-based weighting of synthetic views.
- measures: Error recovery and causal-confusion robustness of end-to-end planners without interactive simulation; correlation with closed-loop outcomes.
- size: navhard: 450 Stage-1 and 5462 Stage-2 observations (~12 synthetic views per real observation); public leaderboard
- metrics: Pearson r=0.89 (R^2=0.8) with closed-loop nuPlan results vs R^2=0.7 for best open-loop; 6x fewer environment interactions than closed-loop (13 vs 80 planner inferences per scenario).
- cost: Neural rendering ~1-2 GPU-hours per scene for synthetic views (one-off, offline); evaluation itself needs 13 planner calls per scenario.
- validity: R^2=0.8 vs closed-loop simulation reported; no correlation to real-world crash outcomes.
- notes: Direct evidence on cost-vs-fidelity trade-off of evaluation paradigms; Pavone co-author.

### luo2025sim2val: Sim2Val (2025)
- org: NVIDIA / Stanford ASL | kind: study | sim2real_level: 6 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2506.20553 | arXiv: 2506.20553
- modality: Paired measurements of the same scenario on a cheap platform (simulator / open-loop playback) and the expensive target platform (closed-loop or real vehicle); real-world metric mean estimated with control variates.
- measures: How many real-world test samples are needed for a confidence bound on a safety/performance metric when correlated cheap proxies exist; variance reduction of the estimator.
- size: nuPlan: 565 real + 1320 surrogate samples; real AV: 138 intersection / 75 curve events paired with 781 / 423 neural-reconstruction sim runs; quadruped: 200 real + 400 sim
- metrics: Variance reduction 22-35% (nuPlan ADE), 82.9% (real AV closest-distance), 5.9% (quadruped, rho=0.07); 51% fewer paired samples for same CI in one domain; sim-real correlation rho>0.9 for AV logs vs 0.07 for quadruped.
- cost: Cost ratios between platforms formalised (budget allocation in appendix); real AV logs and quadruped hardware used; no dollar figures.
- validity: Method's benefit is itself a function of measured sim-to-real correlation; reports rho per platform.
- notes: Closest existing work to a value-of-information framing of evaluation cost; must-cite.

### luo2026x4val: X4Val (2026)
- org: NVIDIA / Stanford ASL | kind: study | sim2real_level: 6 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2606.05159 | arXiv: 2606.05159
- modality: Non-paired heterogeneous evaluation data (simulation, older policy logs, other regions) embedded with DINO features; learned predictor of real-world metric used as a control variate for the target policy's real-world evaluation.
- measures: Variance-reduced estimation of real-world policy metrics when only unpaired auxiliary data exists (e.g. geographic transfer US to Germany, iterative policy versions).
- size: Driving: 200 paired target samples plus 5x1000 samples from earlier policies and 86,848 scenario-only samples; manipulation: 5000 ManiSkill rollouts + 100 real Franka rollouts
- metrics: Up to 38.4% variance reduction (iterative development), 15-20% (geographic transfer); consistent reduction on Franka block stacking.
- cost: Real Franka Panda rollouts (100) vs 5000 sim rollouts; NVIDIA PhysicalAI-AV dataset; no hours or dollars stated.
- validity: Reports variance reduction against Monte Carlo on real data; no external ground truth on safety outcomes.
- notes: Follow-up to Sim2Val; preprint.

### parashar2026coverage: Coverage-Aware Active Evaluation (paired systems) (2026)
- org: MIT / NVIDIA / Stanford | kind: study | sim2real_level: 7 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2608.13719 | arXiv: 2608.13719
- modality: Cheap proxy system (open-loop playback, lower-fidelity sim, related policy) sampled densely; target system (closed-loop sim, second sim, real Unitree Go2, real KITTI) evaluated under a small budget; scenario selection via residual-corrected risk predictor plus support-aware mutual information.
- measures: Number and diversity of severe target-system failures found under a fixed test budget when proxy evaluations are available.
- size: Budgets: nuPlan 170 target evals, SIMPLER 70, quadruped 30 real trials; KITTI perception transfer
- metrics: Up to 2x more failures discovered than random and active-learning baselines, including severe/diverse failures missed by baselines.
- cost: Explicit small target budgets (30-170 evaluations) with proxy evaluations treated as cheap; real Unitree Go2 hardware.
- validity: Failures found on real hardware and real KITTI data, not just sim; no predictive validity vs field incidents.
- notes: Directly about allocating limited real-world test budget; preprint.

### seo2026stressdream: StressDream (2026)
- org: Stanford / NVIDIA / CMU (Bajcsy) | kind: study | sim2real_level: 3 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2606.00267 | arXiv: 2606.00267
- modality: Action-conditioned video world model (Vista for driving, Ctrl-World for DROID manipulation); initial diffusion noise optimised with a VLM semantic objective plus plausibility objective to steer imagined futures toward text-specified failures; policy scored by whether plausible steered futures contain the failure.
- measures: Whether steered world-model imaginations can surface rare high-impact failures of a policy with few samples, and whether that signal improves policies.
- size: Driving: 100 image-action-text pairs in 8 safety-critical categories + 200 imminent-collision examples; manipulation: 100 failure trajectories over 6 tasks
- metrics: Failure recall on manipulation 54% (random sampling) to 94% (StressDream); pi0.5 fine-tuning success 39% to 71%.
- cost: World-model imaginations take several minutes each; noise optimisation adds cost but replaces exhaustive sampling.
- validity: Failure detection recall vs ground-truth failure trajectories; no real-world closed-loop validation of imagined failures.
- notes: Co-authored with Andrea Bajcsy (also a workshop-relevant speaker). World-model-based evaluation.

### dilillo2024adas: Swiss Re / Stanford ADAS proving-ground assessment (2024)
- org: Swiss Re / Stanford (Pavone) | kind: study | sim2real_level: 8 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2409.16942 | arXiv: 2409.16942
- modality: Physical vehicles (12 production models MY2022-23 + 1 prototype) driven on a Euro NCAP-accredited proving ground through safety-critical scenarios selected from insurer accident databases; scored by predicted real-world collision-frequency and impact-energy reduction weighted by scenario relevance; realism metric on tested scenarios.
- measures: Relative real-world safety benefit of collision-prevention systems across vehicles; realism of the scenario protocol.
- size: 13 vehicles; average 81 tests per vehicle (range 41-161; 18-72% of full matrix); 8-month campaign
- metrics: All tested scenarios score as highly realistic (mean realism 0.0024, sd 0.0012 on a nondimensional scale); pre-release prototype outperforms production vehicles in most scenarios.
- cost: Eight-month track campaign at an accredited proving ground in Germany with 13 vehicles; roughly 1000 physical test runs; insurer-funded.
- validity: Scoring explicitly ties to predicted real-world collision frequency; realism metric validates scenario plausibility; no post-hoc comparison to field claims yet.
- notes: Rare example of a costly physical safety evaluation with explicit run counts; strong cost anchor.

### dyro2024extreme: Realistic Extreme Behavior Generation for AV Testing (2024)
- org: Stanford ASL / Swiss Re | kind: red-team | sim2real_level: 2 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2409.10669 | arXiv: 2409.10669
- modality: Collision-free Waymo Open / nuScenes scenes; adversary trajectories perturbed in the parameter space of a learned behaviour model (MTR, Trajectron++) under a data-alignment realism constraint; counterfactual collisions clustered into a test suite; target AV policy run against them.
- measures: Interpretable failure modes of an AV collision-avoidance policy under realistic adversarial counterfactual collisions.
- size: 505 synthetic collisions (MTR) and 174 (Trajectron++); 8 clusters
- metrics: Baseline reactive policy: 100% response to high-speed chasing/side crashes, 55-59% no-response for low-speed lateral crashes.
- cost: Runs on public datasets and learned predictors; no hardware.
- validity: Realism enforced via data-alignment in model parameter space; no real-crash validation.
- notes: ICRA 2025 per ASL page.

### ding2025surprise: Surprise Potential (interactive scenario mining) (2025)
- org: NVIDIA / Univ. Washington | kind: study | sim2real_level: 0 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2502.05677 | arXiv: 2502.05677
- modality: Driving logs (nuScenes) scored by the ego vehicle's surprise potential on other agents (distribution-shift between prediction with and without ego); validated against a reward model trained on human pairwise interactivity preferences; planners evaluated on curated buckets.
- measures: Which logged scenarios are interactive enough to be worth including in an AV benchmark; alignment with human judgement of interactivity.
- size: nuScenes; 5 annotators x 1000 pairwise labels (~5000) for reward model
- metrics: Correlation >0.82 with human-aligned reward; 86% pairwise ranking accuracy; TTC decreases monotonically with surprise bucket.
- cost: ~5000 human pairwise labels; otherwise offline computation.
- validity: Human-preference agreement 0.82; downstream planner TTC trend confirms difficulty.
- notes: Scenario-curation metric for evaluation; directly about making evaluations informative.

### chen2026crashtwin: CrashTwin (physics-grounded world-model benchmark) (2026)
- org: UT Austin / NVIDIA / Stanford | kind: benchmark | sim2real_level: 4 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2606.28757 | arXiv: 2606.28757
- modality: Video world models prompted with multi-agent collision scenes; rollouts reconstructed to 3D kinematics with a calibration-free pipeline; scored on spatio-temporal consistency, momentum/kinetic-energy conservation residuals and world-dynamics integrity.
- measures: Physical trustworthiness of generative world models used as AV simulators in collision scenarios.
- size: 25.6K synthetic (CARLA) + 12.6K real collision sequences; eval sets of 300+44 and 100+16
- metrics: All models (Wan, Cosmos-Predict2, Veo 3.1, Seedance etc.) show high momentum/energy residuals (~0.89 vs ground truth 0.31; post-training 0.65); visual quality masks physics violations.
- cost: API-constrained proprietary models needed a mini eval set; otherwise compute unspecified.
- validity: Human evaluation: physics metrics align better with human realism preference than visual-quality proxies.
- notes: Evaluates the simulator, not the AV; relevant to world-models-for-validation theme.

### gu2025accidentbench: AccidentBench (2025)
- org: UC Berkeley / NVIDIA / Stanford | kind: benchmark | sim2real_level: 0 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2509.26636 | arXiv: 2509.26636
- modality: Multimodal LLMs answer human-annotated QA about accident videos (vehicle, air, water); scored by accuracy across temporal/spatial/intent tasks and difficulty levels.
- measures: Safety-critical video understanding and reasoning of foundation models in accident scenarios.
- size: ~2000 videos, >19,000 QA pairs (~6300 per difficulty level); 83% vehicle accidents
- metrics: GPT-5 37.3% and Gemini 2.5 Pro 31.1% on hard vehicle tasks; ~18% on hardest/longest tasks.
- cost: Human annotation of >19k QA pairs; cost not stated.
- validity: Human-annotated ground truth; no link to closed-loop driving safety.
- notes: Pavone is one of 12 authors; benchmark tests VLMs rather than a control stack.

### ma2025safevl: SafeVL (VLM driving-safety evaluator) (2025)
- org: NVIDIA (ASPIRE) | kind: tooling | sim2real_level: 3 | safety_focus: True | confidence: medium
- url: https://research.nvidia.com/labs/aspire/publication/ma.cao.etal.arxiv2025/
- modality: Driving video fed to a VLM with object-centric chain-of-thought; outputs collision-prone / safe classification; trained with counterfactual unsafe-scenario generation; tested on Nexar collision dataset and as a critic inside UniAD on NeuroNCAP.
- measures: Whether a VLM can serve as a learned safety evaluator of driving scenes and reduce closed-loop collisions when used as a critic.
- size: Nexar collision dataset (size not stated); NeuroNCAP closed-loop benchmark
- metrics: 76% zero-shot accuracy on Nexar (+20% over prior); 8% collision-rate reduction on NeuroNCAP when integrated with UniAD.
- cost: none stated
- validity: Accuracy vs real dashcam collision labels; closed-loop effect on NeuroNCAP.
- notes: No arXiv ID found; PDF via Google Drive on project page safevl.github.io; author list from NVIDIA page.

### foutter2026faithfulness: Pinocchio (faithfulness of embodied CoT) (2026)
- org: Stanford ASL / NVIDIA | kind: study | sim2real_level: 1 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2607.04681 | arXiv: 2607.04681
- modality: Reasoning traces of a driving VLA (Alpamayo-style) rated by humans and by a Gemini judge on observation grounding and stepwise coherence; learned critic used as RL reward; evaluated on held-out US/DE driving scenarios and synthetic counterfactuals.
- measures: Whether verbalized reasoning of a driving VLA faithfully reflects its decisions, and whether faithfulness improves long-tail robustness.
- size: 200-sample human study; 100 traces x 4 annotators for judge validation; ~20k DE and ~15k US held-out scenarios; 66 counterfactual scenes
- metrics: Gemini agrees with human majority 87-95%; human kappa 0.475-0.685; reasoning consistency 27.7% (SFT) to 61.4%; 1.6x causal-alignment gain on counterfactuals.
- cost: Human annotation of 300 traces; large internal driving dataset.
- validity: Human agreement numbers for the judge; inconsistent coupling between reasoning quality and trajectory improvement found.
- notes: Evaluation of reasoning, not of a safety outcome per se.

### han2024euvs: EUVS (Extrapolated Urban View Synthesis Benchmark) (2024)
- org: NYU / NVIDIA / Stanford | kind: benchmark | sim2real_level: 4 | safety_focus: False | confidence: high
- url: https://arxiv.org/abs/2412.05256 | arXiv: 2412.05256
- modality: Neural rendering methods (3DGS/NeRF variants) trained on one traversal and tested on views from other traversals/vehicles/cameras (translation, rotation, both); scored by PSNR/SSIM/LPIPS.
- measures: How much sensor-simulation fidelity degrades when rendering viewpoints outside the training trajectory, i.e. how trustworthy reconstruction-based closed-loop simulators are.
- size: 90,810 frames over 104 cases from nuPlan, Argoverse 2, MARS; 10 methods
- metrics: PSNR drops 23-40% from interpolated to extrapolated views; average degradation >25% across metrics.
- cost: 300+ hours manual traversal selection, 800+ compute hours for COLMAP.
- validity: none stated (image metrics only)
- notes: Simulator-fidelity benchmark; safety_focus false but informs sim2real gap of AV validation.

### fan2024crashevent: CrashEvent / CrashLLM (2024)
- org: UT Austin / NVIDIA / JHU | kind: dataset | sim2real_level: 0 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2406.10789 | arXiv: 2406.10789
- modality: Crash reports converted to text; LLMs fine-tuned to predict crash type, severity, injuries; scored by F1.
- measures: Whether LLMs can predict crash outcomes from contextual factors and support what-if traffic-safety analyses.
- size: 19,340 real-world crash reports (Washington State)
- metrics: Average F1 from 34.9% to 53.8%.
- cost: none stated
- validity: Real crash labels as ground truth.
- notes: Traffic-safety analytics rather than robot evaluation; adjacent.

### patrikar2025negative: Crash-report precedents for reasonable driving (2025)
- org: NVIDIA / CMU | kind: study | sim2real_level: 0 | safety_focus: True | confidence: low
- url: https://arxiv.org/abs/2509.18626 | arXiv: 2509.18626
- modality: Crash narratives normalised to ego-centric language and indexed with driving logs; proposed actions adjudicated by retrieval and counterfactual reasoning; scored by recall of contextually preferred actions on nuScenes.
- measures: Whether negative data (crash reports) improves calibration of driving decisions near safety boundaries.
- size: nuScenes benchmark; crash report corpus size not stated
- metrics: Recall on preferred actions 24% to 53%.
- cost: none stated
- validity: none stated
- notes: Primarily a decision-making method; included because it defines a crash-grounded evaluation of action choices.

### antonante2023taskaware: Task-aware risk estimation of perception failures (2023)
- org: MIT / NVIDIA / Stanford | kind: study | sim2real_level: 2 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2305.01870 | arXiv: 2305.01870
- modality: Perception-monitor-flagged failures used to synthesise alternative plausible scenes; relative risk to the motion plan estimated with copulas (PAC bounds); evaluated on nuPlan; scored by F1/precision/recall of safety-maneuver triggering.
- measures: Whether a perception error matters for the plan (system-level risk), and how well the estimator triggers safety maneuvers.
- size: nuPlan (scenario count not stated)
- metrics: Best F1, about double the best baseline; balanced recall/precision.
- cost: none stated
- validity: none stated (nuPlan offline)
- notes: Runtime-monitor evaluation with clear protocol.

### chakraborty2024sparq: SPARQ (system-level perception-failure safety Q-network) (2024)
- org: USC / NVIDIA / Stanford | kind: study | sim2real_level: 2 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2409.17630 | arXiv: 2409.17630
- modality: Q-network scores whether a planner's proposed trajectory is safe given possible perception failures; recommends corrective plan; evaluated on nuPlan-Vegas; scored by accuracy/recall and runtime.
- measures: Runtime safety assessment of motion plans against overlooked perception failures.
- size: nuPlan-Vegas unseen test set (count not stated)
- metrics: 90% accuracy and recall at 42 Hz; compared with reachability baseline.
- cost: Runs at 42 Hz on unseen test set; no hardware.
- validity: none stated
- notes: ICRA 2025 per NVIDIA page.

### chakraborty2025frs: FORCE-OPT (predictor-based forward reachable sets for plan safety) (2025)
- org: USC / NVIDIA / Stanford | kind: study | sim2real_level: 1 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2507.22389 | arXiv: 2507.22389
- modality: Multimodal trajectory predictor distributions converted to conformally calibrated forward reachable sets; ego plan checked for intersection; Bayesian filter adapts conservativeness; evaluated on nuScenes with synthetic unsafe scenes; scored by coverage, FPR, FNR.
- measures: Soundness and completeness of a plan-level safety monitor for end-to-end stacks.
- size: nuScenes (~15 h); train Singapore, test Singapore (ID) and Boston (OOD)
- metrics: Coverage ~90%; FPR 8.6% (ID) / 5.2% (OOD); FNR 3.0% / 13.0%; 0.022 s per scenario; 7 baselines.
- cost: 0.022 s per scenario compute.
- validity: Unsafe cases are synthetic edits of safe scenes; no real collisions.
- notes: Title literally 'Safety Evaluation of Motion Plans'; runtime monitor with reusable protocol.

### farid2022taskrelevant: Task-relevant failure detection for trajectory predictors (2022)
- org: Princeton / NVIDIA / Stanford | kind: study | sim2real_level: 1 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2207.12380 | arXiv: 2207.12380
- modality: Prediction errors propagated to planning cost; probabilistic runtime detector of harmful mispredictions with data-free calibration; scored by ROC AUC against other detectors.
- measures: Detection of prediction failures that actually harm the plan, with bounds on false-positive and false-negative rates.
- size: not stated
- metrics: Highest AUROC among compared detectors.
- cost: none stated
- validity: none stated
- notes: Related Bajcsy-group regret metric (arXiv 2403.04745) has no Pavone authorship.

### topan2022perceptionzones: Interaction-dynamics-aware perception safety zones (2022)
- org: Stanford / NVIDIA | kind: standard | sim2real_level: 1 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2206.12471 | arXiv: 2206.12471
- modality: Off-the-shelf nuScenes detector's false positives/negatives classified as safety-critical or not using a Hamilton-Jacobi reachability safety zone (ego-obstacle relative state grid); compared against circular-distance baseline.
- measures: A safety-aware evaluation metric for obstacle detection: which perception errors matter.
- size: nuScenes; 4644 false positives analysed; 40x40x20x15x15 state grid
- metrics: HJ zone flags 35 safety-critical FPs (0.75%) vs 305 (6.6%) for circular baseline, 8.7x reduction; 4.5 ms per object online, 228 s offline.
- cost: 228 s offline compute, 28.8 MB memory, 4.5 ms per object.
- validity: none stated (theoretical completeness argument)
- notes: Co-authored with NVIDIA safety team (Nilsson, Cox); kind=standard because it proposes an evaluation metric definition.

### topan2023maneuverzones: Maneuver-based perception safety zones (2023)
- org: Stanford / NVIDIA | kind: standard | sim2real_level: 1 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2308.06337 | arXiv: 2308.06337
- modality: Extension of perception safety zones: temporal-convolution decomposition by ego maneuver to shrink zone volume while retaining completeness; numerical experiments.
- measures: Size of the perception safety-critical region conditioned on ego maneuver.
- size: numerical experiments; not stated
- metrics: Up to 76% zone-volume reduction while maintaining completeness.
- cost: none stated
- validity: none stated
- notes: Incremental follow-up.

### ivanovic2021rethinking: Rethinking Trajectory Forecasting Evaluation (2021)
- org: NVIDIA / Stanford | kind: position | sim2real_level: 0 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2107.10297 | arXiv: 2107.10297
- modality: Argues accuracy-only forecasting metrics (ADE/FDE/NLL) are task-agnostic; proposes planning-aware weighting of prediction errors.
- measures: Whether forecasting metrics reflect downstream planning outcomes.
- size: n/a
- metrics: n/a (position paper with one example metric)
- cost: none stated
- validity: none stated
- notes: Short position paper; superseded by 2110.03270.

### ivanovic2021planningaware: Planning-aware prediction and detection metrics (2021)
- org: NVIDIA / Stanford | kind: standard | sim2real_level: 1 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2110.03270 | arXiv: 2110.03270
- modality: Prediction and detection outputs re-weighted by their effect on a downstream planner (via planner cost sensitivity); validated on an illustrative simulation and real AV data.
- measures: Task-aware metrics for perception and prediction that better estimate closed-loop performance and outcome asymmetry.
- size: illustrative sim + real driving data (nuScenes)
- metrics: Task-aware metrics better estimate closed-loop performance than IoU/ADE (qualitative/relative results).
- cost: none stated
- validity: Compared against closed-loop performance in simulation.
- notes: Foundational for the group's 'task-aware evaluation' line.

### leung2022safetyconcepts: Learning AV safety concepts from demonstrations (2022)
- org: Stanford / NVIDIA | kind: study | sim2real_level: 1 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2210.02761 | arXiv: 2210.02761
- modality: Reasonable-behaviour assumptions learned from highway traffic-weaving demonstrations; safety concept synthesised via HOCBF / HJ reachability; used to evaluate real-world driving logs.
- measures: Which logged interactions violate a data-derived safety concept; comparison with hand-designed concepts (e.g. RSS-like).
- size: highway traffic-weaving demonstrations (count not stated)
- metrics: Learned concept evaluates real driving logs; qualitative comparison to baselines.
- cost: none stated
- validity: none stated
- notes: Venue inferred (ACC 2023) from ASL listing style; verify before citing venue.

### leung2021synthesis: Data-driven synthesis of AV safety concepts (HJ reachability) (2021)
- org: Stanford / UC Berkeley (Bajcsy) | kind: position | sim2real_level: 0 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2107.14412 | arXiv: 2107.14412
- modality: Embeds existing AV safety concepts (RSS etc.) in a Hamilton-Jacobi reachability framework to compare assumptions; proposes data-driven tailoring for responsibility and context.
- measures: A common language for comparing and evaluating AV safety concepts.
- size: n/a
- metrics: n/a
- cost: none stated
- validity: none stated
- notes: Co-authored with Andrea Bajcsy; conceptual, not an experimental evaluation.

### luo2021conformal: Sample-efficient safety assurances via conformal prediction (2021)
- org: Stanford ASL | kind: study | sim2real_level: 5 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2109.14082 | arXiv: 2109.14082
- modality: Warning system + simulator of robot/environment dynamics; conformal prediction tunes alert threshold to a provable false-negative rate; applied to a driver warning system and robotic grasping.
- measures: Guaranteed false-negative rate of unsafe-situation warning systems using as few as 1/epsilon calibration samples.
- size: as few as 1/epsilon data points
- metrics: Empirically achieves guaranteed FNR with low FPR in both applications.
- cost: Sample complexity 1/epsilon explicitly given.
- validity: Provable FNR under exchangeability; empirical confirmation.
- notes: IJRR 2023 per ASL page; directly about how many samples an assurance costs.

### luo2022recency: Online distribution-shift detection via recency prediction (2022)
- org: Stanford ASL | kind: study | sim2real_level: 7 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2211.09916 | arXiv: 2211.09916
- modality: Streaming high-dimensional observations; detector with guaranteed false-positive rate; evaluated in simulation and hardware visual servoing.
- measures: Detection speed and false-positive guarantee of a runtime distribution-shift monitor.
- size: not stated
- metrics: Up to 11x faster detection than prior work; alerts issued before failure on hardware.
- cost: Hardware visual-servoing experiments.
- validity: Alert precedes failure on hardware.
- notes: Venue ICRA 2024 per arXiv comments; runtime-monitor evaluation.

### hindy2024martingales: Diagnostic runtime monitoring with martingales (2024)
- org: Stanford ASL | kind: study | sim2real_level: 7 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2407.21748 | arXiv: 2407.21748
- modality: Multiple stochastic martingales run in parallel on streaming images to diagnose the cause of shift (sensor degradation, new environment, brightness); X-Plane taxiing and free-flyer hardware.
- measures: Speed and accuracy of diagnosing distribution-shift cause so the right intervention can be applied.
- size: X-Plane: 1000 taxi sequences (~30 images each); hardware: 9000 images from 30 episodes
- metrics: Detects cause up to 5x faster than conformal-martingale baseline (e.g. 14.9 vs 38.1 iterations).
- cost: Free-flyer hardware testbed; simulator data.
- validity: none stated
- notes: RSS 2025 per NVIDIA page.

### elhafsi2023semantic: Semantic anomaly detection with LLMs (2023)
- org: Stanford ASL / NASA JPL | kind: study | sim2real_level: 3 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2305.11307 | arXiv: 2305.11307
- modality: Scene converted to text via open-vocabulary detector (OWL-ViT); LLM (text-davinci-003) asked whether the scene is a semantic anomaly; CARLA driving FSM policy and Ravens manipulation policy; scored by TPR/TNR and agreement with humans.
- measures: Whether an LLM monitor catches system-level semantic edge cases (stop signs on billboards, traffic lights on trucks) that component-level OOD detectors miss.
- size: 69 handcrafted CARLA cases in 5 classes; 750 manipulation episodes
- metrics: Driving TPR 92% / TNR 78% (SCOD 30%, Mahalanobis 48%); manipulation detects 86% of semantic distractors vs 100% human.
- cost: OpenAI API calls; CARLA sim.
- validity: Agreement with human reasoning reported on manipulation distractors.
- notes: Clear reusable test-case protocol.

### sinha2024aesop: AESOP (real-time LLM anomaly detection + reactive planning) (2024)
- org: Stanford ASL | kind: study | sim2real_level: 7 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2407.08735 | arXiv: 2407.08735
- modality: Fast binary anomaly classifier in LLM embedding space triggers slow generative-LLM fallback selection inside an MPC with joint-feasibility branches; quadrotor and AV settings, sim and hardware.
- measures: Anomaly-classification accuracy vs GPT-style reasoning and closed-loop safety of the fallback framework.
- size: not stated
- metrics: Fast classifier outperforms autoregressive GPT reasoning even with small LMs.
- cost: Quadrotor hardware; runtime-constrained.
- validity: none stated
- notes: Method paper; evaluation protocol partly reusable.

### ronecker2025vfm: Vision-foundation-model embedding semantic anomaly detection (2025)
- org: TU Graz / Stanford ASL | kind: study | sim2real_level: 3 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2505.07998 | arXiv: 2505.07998
- modality: Runtime images embedded with a vision foundation model (grid or instance-based) and compared to a nominal-scenario database; CARLA-simulated anomalies; compared with GPT-4o.
- measures: Detection and localisation of semantic anomalies for driving.
- size: CARLA anomaly set (count not stated)
- metrics: Instance-based method with filtering comparable to GPT-4o, with localisation.
- cost: none stated
- validity: none stated
- notes: Workshop paper.

### ganai2025fortress: FORTRESS (OOD failure prevention via multimodal reasoning) (2025)
- org: Stanford ASL / Swiss Re | kind: study | sim2real_level: 7 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2505.10547 | arXiv: 2505.10547
- modality: Multimodal foundation models anticipate failure modes and fallback sets at low frequency; runtime monitor triggers fast fallback planning; safety-classification accuracy on synthetic benchmarks and real ANYmal data; quadrotor hardware urban navigation.
- measures: Safety-classification accuracy and closed-loop planning success under OOD events.
- size: synthetic benchmarks + real ANYmal data (counts not stated)
- metrics: Outperforms on-the-fly prompting of slow reasoning models in safety classification; improves safety and success on quadrotor hardware.
- cost: Quadrotor hardware; ANYmal logs.
- validity: none stated
- notes: Method paper with evaluation; CoRL 2025 per ASL page.

### agia2024sentinel: Sentinel (runtime monitoring of generative policies) (2024)
- org: Stanford | kind: study | sim2real_level: 7 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2410.04640 | arXiv: 2410.04640
- modality: Diffusion-policy rollouts monitored by statistical temporal action-consistency (STAC) plus VLM task-progress checks; sim (PushT, Close Box, Cover Object) and real mobile-manipulator Push Chair; scored by TPR/TNR/accuracy and detection latency.
- measures: Failure-detection accuracy and latency for generative policies under OOD conditions.
- size: 50 calibration rollouts per sim task; real: 10 calibration + 10 success + 10 failure episodes
- metrics: Combined detector 91-95% accuracy (TPR 93-100%, TNR 87-93%); 18% more failures than either detector alone; STAC 5-15 s, VLM ~21 s.
- cost: Real mobile manipulator; small episode counts.
- validity: none stated
- notes: Manipulation, not AV; runtime-monitor evaluation protocol reusable.

### sinha2022oodview: A system-level view on OOD data in robotics (2022)
- org: Stanford ASL | kind: position | sim2real_level: None | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2212.14020 | arXiv: 2212.14020
- modality: Position paper: argues OOD should be judged by system-level competence rather than model-level detection; frames research questions on runtime monitoring, fallback and data lifecycle.
- measures: n/a (conceptual framing of what an OOD-robustness evaluation should measure)
- size: n/a
- metrics: n/a
- cost: none stated
- validity: none stated
- notes: Useful framing citation.

### deglurkar2024uq: System-level analysis of module uncertainty quantification (2024)
- org: UC Berkeley / NVIDIA / Boeing | kind: study | sim2real_level: 2 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2410.12019 | arXiv: 2410.12019
- modality: Derives probabilistic specification on a module's uncertainty measure from a system spec and measures system input-output robustness; applied to a nuScenes driving stack (Trajectron++ + planner + MPC) and a Boeing runway-incursion detector/tracker.
- measures: Whether a module's uncertainty estimate is useful to the system and how uncertainty-aware designs compare.
- size: nuScenes; proprietary Boeing landing dataset
- metrics: Uncertainty-aware planners beat baseline on safety and holistic cost; histogram tracker miss rate 0.823 vs FPR 0.169.
- cost: none stated
- validity: none stated
- notes: Evaluation methodology for UQ, adjacent to safety evaluation.

### cao2022advdo: AdvDO (realistic adversarial attacks on trajectory prediction) (2022)
- org: NVIDIA / Univ. Michigan | kind: red-team | sim2real_level: 2 | safety_focus: True | confidence: high
- url: https://arxiv.org/abs/2209.08744 | arXiv: 2209.08744
- modality: Optimisation-based attack with differentiable dynamics generates realistic adversarial agent histories; SOTA predictors benchmarked on general and planning-aware metrics; downstream AV simulated.
- measures: Adversarial robustness of trajectory predictors and its downstream planning consequences.
- size: not stated (nuScenes-scale predictors)
- metrics: Prediction error up +50% (general) and +37% (planning-aware metrics); attacks cause off-road or collisions in simulation.
- cost: none stated
- validity: Downstream planner collisions in sim.
- notes: Red-teaming of a perception/prediction module.

### cao2022robust: Robust trajectory prediction against adversarial attacks (2022)
- org: NVIDIA / Univ. Michigan | kind: red-team | sim2real_level: 2 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2208.00094 | arXiv: 2208.00094
- modality: Adversarial training + domain-specific augmentation; robust model evaluated with a planner for accident rates.
- measures: Robustness gains vs clean-data cost, and downstream collision/off-road rates.
- size: not stated
- metrics: +46% on adversarial data at 3% clean-data cost; +21% adversarial / +9% clean vs prior robust methods; reduced severe accident rates with planner.
- cost: none stated
- validity: Downstream planner accident rates in sim.
- notes: Defense paper; evaluation protocol shared with AdvDO.

### marchiori2025jdapt: J-DAPT (robotic jailbreak detection) (2025)
- org: Univ. Padova / Stanford / UPenn | kind: red-team | sim2real_level: 1 | safety_focus: True | confidence: low
- url: https://arxiv.org/abs/2509.23281 | arXiv: 2509.23281
- modality: Multimodal jailbreak classifier with attention fusion and domain adaptation; evaluated on jailbreak prompts for driving, maritime and quadruped VLM agents; scored by detection accuracy.
- measures: Detection accuracy of jailbreak attempts against robot-embedded VLMs across domains.
- size: not stated
- metrics: Detection accuracy near 100% with minimal overhead.
- cost: none stated
- validity: none stated
- notes: Security defense; only adjacent to physical-safety evaluation.

### christensen2025maritime: Semantic Lookout (maritime VLM hazard detection) (2025)
- org: NTNU / Stanford ASL | kind: study | sim2real_level: 8 | safety_focus: True | confidence: low
- url: https://arxiv.org/abs/2512.24470 | arXiv: 2512.24470
- modality: Camera-only VLM selects a cautious fallback maneuver from water-valid trajectories; 40 harbor scenes scored for scene understanding, latency, agreement with human consensus (majority-of-three), and on-water handover demo.
- measures: Whether VLMs give usable semantic hazard awareness in the IMO MASS alert-to-takeover window.
- size: 40 harbor scenes; one on-water demonstration
- metrics: Sub-10 s models retain most awareness of slower SOTA models; alignment with human consensus reported per model.
- cost: On-water vessel test.
- validity: Human-consensus agreement on 40 scenes.
- notes: Maritime, small n; regulatory (IMO MASS) framing is notable.

### banerjee2022lifecycle: Data lifecycle benchmark for aerospace ML (2022)
- org: Stanford ASL / Aerospace Corp. | kind: benchmark | sim2real_level: 3 | safety_focus: False | confidence: low
- url: https://arxiv.org/abs/2209.06855 | arXiv: 2209.06855
- modality: Satellite pose-estimation model deployed in novel conditions (backgrounds, bad pixels); algorithms select inputs to label and retrain; scored by performance over mission lifetime and cumulative labelling/retraining cost.
- measures: Cost-vs-performance of labelling strategies under evolving input distributions (open-source benchmark).
- size: not stated
- metrics: Proposed selector matches 100%-labelling performance while labelling 50% of inputs.
- cost: Labelling and retraining cost explicitly tracked as a benchmark axis.
- validity: none stated
- notes: Not safety per se; included because it benchmarks labelling cost explicitly.

### zhong2022ctg: CTG (guided conditional diffusion traffic sim) (2022)
- org: NVIDIA / Columbia | kind: tooling | sim2real_level: 2 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2210.17366 | arXiv: 2210.17366
- modality: Diffusion traffic model guided by signal-temporal-logic rules at test time; nuScenes; scored on rule satisfaction vs realism.
- measures: Controllability-realism trade-off of generated traffic for testing.
- size: nuScenes
- metrics: Improves controllability-realism trade-off over baselines.
- cost: none stated
- validity: none stated
- notes: Scenario-generation tooling that feeds evaluations.

### zhong2023ctgpp: CTG++ (language-guided scene-level diffusion) (2023)
- org: NVIDIA / Columbia | kind: tooling | sim2real_level: 2 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2306.06344 | arXiv: 2306.06344
- modality: LLM converts user query to a loss; scene-level diffusion produces query-compliant traffic.
- measures: Realism and query compliance of language-specified traffic scenarios.
- size: not stated
- metrics: Comprehensive evaluation of realism and compliance (relative).
- cost: none stated
- validity: none stated
- notes: CoRL 2023 oral.

### tan2023lctgen: LCTGen (language-conditioned traffic generation) (2023)
- org: UT Austin / NVIDIA | kind: tooling | sim2real_level: 2 | safety_focus: False | confidence: medium
- url: https://arxiv.org/abs/2307.07947 | arXiv: 2307.07947
- modality: LLM + transformer decoder selects map location and initial traffic and dynamics from text.
- measures: Realism/fidelity of generated traffic scenes conditioned on language.
- size: not stated
- metrics: Outperforms prior work on conditional and unconditional generation.
- cost: none stated
- validity: none stated
- notes: Tooling.

### tan2024prosim: ProSim (promptable closed-loop traffic simulation) (2024)
- org: UT Austin / NVIDIA | kind: tooling | sim2real_level: 2 | safety_focus: False | confidence: high
- url: https://arxiv.org/abs/2409.05863 | arXiv: 2409.05863
- modality: Agents receive numerical/categorical/text prompts and roll out closed-loop; ProSim-Instruct-520k dataset; Waymo Sim Agents Challenge metrics.
- measures: Prompt controllability and realism of reactive traffic agents for closed-loop testing.
- size: 520k scenarios, >10M prompts
- metrics: Competitive Waymo Sim Agents performance without prompts; high controllability with prompts.
- cost: none stated
- validity: none stated
- notes: Used by third parties (e.g. arXiv 2506.01199, Frazzoli group) for automated safety-critical test generation.

### ding2023realgen: RealGen (retrieval-augmented scenario generation) (2023)
- org: CMU / NVIDIA | kind: tooling | sim2real_level: 2 | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2312.13303 | arXiv: 2312.13303
- modality: Retrieval-based in-context generation composes behaviours from retrieved scenarios to create edited, composite or critical scenarios.
- measures: Flexibility and controllability of generated safety-critical scenarios.
- size: not stated
- metrics: Qualitative/relative controllability results.
- cost: none stated
- validity: none stated
- notes: Tooling.

### xu2022bits: BITS (bi-level imitation for traffic simulation) + tbsim (2022)
- org: NVIDIA / Stanford | kind: tooling | sim2real_level: 2 | safety_focus: False | confidence: medium
- url: https://arxiv.org/abs/2208.12403 | arXiv: 2208.12403
- modality: Learned traffic agents from driving logs; evaluated on realism, diversity and long-horizon stability with a proposed metric suite; open-source tool converting datasets into interactive sim.
- measures: Behaviour realism of learned traffic agents; introduces evaluation metrics for traffic simulation.
- size: two large driving datasets
- metrics: Balanced realism/diversity/stability (relative).
- cost: none stated
- validity: none stated
- notes: Tooling with metric suite.

### ivanovic2023trajdata: trajdata (2023)
- org: NVIDIA / Univ. Toronto / Stanford | kind: tooling | sim2real_level: 0 | safety_focus: False | confidence: medium
- url: https://arxiv.org/abs/2307.13924 | arXiv: 2307.13924
- modality: Unified API over many trajectory/map datasets; empirical comparison of datasets.
- measures: Dataset statistics and cross-dataset evaluation infrastructure for forecasting.
- size: multiple public datasets
- metrics: n/a
- cost: none stated
- validity: none stated
- notes: Infrastructure.

### gao2025survey: Survey: foundation models for scenario generation and analysis (2025)
- org: TU Munich et al. / Stanford | kind: position | sim2real_level: None | safety_focus: True | confidence: medium
- url: https://arxiv.org/abs/2506.11526 | arXiv: 2506.11526
- modality: Survey (as of May 2025) of LLM/VLM/diffusion/world-model scenario generation, datasets, simulators, benchmark challenges and evaluation metrics for AV testing.
- measures: n/a (taxonomy of evaluation metrics for scenario generation)
- size: n/a
- metrics: n/a
- cost: none stated
- validity: none stated
- notes: Pavone is one of 15 authors.

### han2026wildcity: WildCity (city-scale real-world testbed) (2026)
- org: NYU / NVIDIA / Stanford | kind: dataset | sim2real_level: 4 | safety_focus: False | confidence: low
- url: https://arxiv.org/abs/2607.06838 | arXiv: 2607.06838
- modality: Multimodal fleet data over long urban trajectories; reconstruction baseline converted into a closed-loop simulator; analysis of scalability, extrapolation and uncertainty for digital twins.
- measures: Feasibility of simulation-ready city-scale digital twins for closed-loop testing.
- size: 18 trajectories averaging 83.7 km
- metrics: n/a (analysis)
- cost: none stated
- validity: none stated
- notes: Simulation infrastructure; not a safety eval.
