# Automotive and standards-based physical safety testing: evaluation catalogue

Scope: 2018-2026 (plus two pre-2018 anchors), Euro NCAP / NHTSA / IIHS AEB protocols and their real-world effectiveness, ISO 26262 / ISO 21448 / UL 4600 / ISO 34502 / UN R157, robot safety standards (ISO 10218:2025, ISO/TS 15066, ISO 13482), HIL / VIL / digital-twin platforms, scenario-based and accelerated simulation validation, miles-to-demonstrate statistics and deployment outcome studies. 72 entries, 71 with the primary URL fetched. Companion JSON: `topic-automotive-standards-hil.json`.

## One-page synthesis

What exists
- Outcome (level 9) evidence is unusually rich in this topic: Waymo/SGO crash-rate studies (7.1M and 56.7M miles), Swiss Re liability claims (3.8M and 25.3M miles), IIHS real-world AEB effectiveness (34-53 percent fewer rear-end crashes; 25-27 percent fewer pedestrian crashes, none in unlit darkness), and Euro NCAP star ratings vs injury outcomes. These are the ground truth every cheaper evaluation should be judged against.
- Standardised physical protocols (level 8): Euro NCAP AEB C2C v4.3 and 2026 VTA, FMVSS 127 (7 crash-imminent plus 2 false-activation scenarios, no-contact in every run), IIHS FCP 2.0 and P-AEB v4. All feed a production vehicle real targets (GVT soft car, motorcycle surrogate, real trailer, articulated pedestrian dummies) and score impact-speed reduction or contact/no-contact over a speed x overlap grid.
- HIL / VIL / digital twins (level 6): PG-based VIL (Son 2022), combined virtual-real AEB field experiments (Zhang 2025), VP-AutoTest, dyno-coupled VIL (Wu 2026), coupled cyclist/vehicle-in-the-loop (Kaiser 2025), TWICE test-track twin dataset. They replace the target hardware with injected virtual objects while keeping the real vehicle, sensors or compute.
- Closed-loop and replay simulation (levels 4-5): Waymo CAT (13,000+ scenarios re-simulated from track sensor logs, about 70 reproduced physically per launch), reconstructed fatal crashes (72 crashes, 100 percent avoided as initiator), NADE and D2RL accelerated testing (500x-6,000x fewer simulated tests, 72,000 core-hours for the naturalistic baseline), nuPlan/NAVSIM/NeuroNCAP planner benchmarks, WOSAC agent realism, UN R157 simulation homologation with ConScenD real-data scenarios.
- Standards and frameworks without a score: ISO 34502, PEGASUS, UL 4600 (safety case plus SPIs), ISO 26262-for-ML (Salay), SOTIF quantification (Putze, Betschinske), pass/fail criteria (Myers), criticality-metric reviews (Westhofen, Singh).
- Robot side (level 7): ISO 10218:2025 absorbs ISO/TS 15066 PFL limits; hardware studies show measured impact forces vary >100 percent across the workspace, the analytic limit formula both under- and over-estimates safe speed (up to 4x conservative with padding), and four commercial robots get non-unique verdicts under the standard's own definitions. A 2026 systematic review of 68 biofidelic-instrument studies documents measurement-device variability. ISO 13482 is criticised as not covering public-space hazards. An LLM-planner gate grounded in ISO 13482 (SafeGate) is the one entry that reaches level 0.

Where cost evidence is strong or absent
- Dollar figures exist only at the extremes: Mcity track time $3,127 per day plus $71/h staff (2022); Euro NCAP full programme 'several hundreds of thousands of Euros' and a minimum of six vehicles; FMVSS 127 $354M per year fleet-wide compliance and $550-680k per life saved; ISO 10218 costs $244 to buy. No paper reports the cost of a HIL/VIL rig or of one simulated scenario.
- Time and count proxies are common: Waymo 'thousands of scenarios in hours instead of months', 70 track scenarios per launch; Euro NCAP test-run count grew from a few hundred (2014) to about 2,000 (2026), the stated 'tipping point' that forced virtual testing; RAND 275M failure-free miles (12.5 years for a 100-car fleet) or 8.8B miles to prove a 20 percent improvement; D2RL 72,000 core-hours; 2,250 cobot collision trials; 20 physical field tests from 87 analysed triggering conditions.
- Absent: human labelling cost (perception ground truth is named as the bottleneck by Hoss 2022 but never priced), and per-scenario simulation compute for the industrial toolchains.

Where validity evidence is strong or absent
- Strong, quantitative: open-loop NAVSIM PDMS vs closed-loop Bench2Drive Spearman 0.90 but the collision sub-metric only 0.45 (Wang 2026); nuPlan open-loop and closed-loop objectives misaligned (Dauner 2023, NeuroNCAP); Euro NCAP 5-star vs 2-star cars 10 percent lower injury risk, 68 percent lower fatality (Kullgren); pedestrian AEB 25-27 percent effective by day and 0 in unlit dark (Cicchino 2022); superior-rated AEB 53 percent effective vs cars but 38-41 percent vs trucks and motorcycles (IIHS 2023); old IIHS AEB scenarios covered <3 percent of real rear-end crashes (IIHS 2024); analytic ISO/TS 15066 speed limits are conservative by up to 4x (Svarny 2022) and forces vary >100 percent (Svarny 2020); 8 of 20 analysis-derived triggering conditions produced risky behaviour on the vehicle (Xing 2022); 33 surrogate safety metrics show no empirical consensus (Singh 2023).
- Procedural rather than statistical: Waymo validates simulation by requiring it to be conservative relative to track runs (as many or more simulated collisions, simulated trajectory even with or ahead) with no published coefficient; Euro NCAP 2026 and UN R157 enforce correlation of virtual to physical spot checks but tolerances are not public; Son 2022 VIL consistency (NRMSE about 4 percent, from a snippet) is the only numeric VIL-vs-real figure found and it is not verified in the abstract.
- Absent: no study links a HIL/VIL score, a Euro NCAP AEB grid score or a SOTIF residual-risk estimate to field crash rates; disengagement reports are shown to be driver- and reporting-dependent (>80 percent driver-initiated; 5x more insufficiencies than faults), so they are a weak level-9 proxy; robot-standard verdicts are assessor-dependent (Kirschner 2022).

Canonical entries for a 4-page paper (5-8)
1. kalra2016driving: why level-9 outcome statistics cannot be bought before deployment (275M to 8.8B miles).
2. kusano2022collision (Waymo CAT): the reference industrial allocation of tests across levels 5 and 8, with scenario counts, scoring thresholds and the simulation-conservativeness check.
3. kusano2025comparison plus dilillo2024swissre: the outcome ground truth (56.7M miles; 25.3M miles of claims) that all cheaper evaluations are meant to predict.
4. feng2021nade (and feng2023dense): accelerated simulation with proven unbiasedness and orders-of-magnitude cost reduction; 72,000 core-hour baseline.
5. nhtsa2024fmvss127: a costed level-8 protocol ($354M/yr, 362 lives/yr, no-contact rule) whose benefits are justified by level-9 AEB effectiveness studies.
6. iihs2023trucks with iihs2024fcp2 and cicchino2022pedestrian: documented cases where a saturated level-8 rating stopped predicting field outcomes and the protocol was changed.
7. euroncap2026vta: the regulator-side move from physical to virtual testing with physical spot checks, driven by the test-grid 'tipping point'.
8. wang2026openloop with dauner2023parting: the best quantitative estimate of how well a cheap open-loop score predicts a closed-loop one (rho 0.90 overall, 0.45 for collisions).
Optionally svarny2022skins and kirschner2022iso15066 for the robot-standards lineage, and koopman2022ul4600 for the safety-case/SPI framing.


## Ladder coverage

- Level 0: obi2026safegate
- Level 3: dyro2024realistic
- Level 4: feng2021nade, feng2023dense, yang2022sparse, pegasus2019, unece2021r157, myers2020passfail, euroncap2026vta, wang2026openloop, li2024rigorous
- Level 5: kusano2022collision, scanlon2021waymo, glasmacher2023acquire, tenbrock2021conscend, mcity2024digitaltwin, dauner2023parting, dauner2024navsim, ljungbergh2024neuroncap, montali2023wosac
- Level 6: winkelmann2022transfer, son2022pgvil, zhang2025combined, cui2025vpautotest, wu2026fromcode, kaiser2025coupled, novickineto2023twice
- Level 7: xing2022ontology, iso2025iso10218, hartmann2026biofidelic, kirschner2022iso15066, svarny2020collisionforcemap, svarny2022skins
- Level 8: euroncap2023aebc2c, nhtsa2024fmvss127, iihs2024fcp2, iihs2024paeb, kidd2023characteristics, mcity2022rates, izquierdo2022testing
- Level 9: kalra2016driving, zheng2023planning, kusano2023comparison, kusano2025comparison, dilillo2023comparative, dilillo2024swissre, favaro2023interpreting, chen2024initial, singh2023diversity, betschinske2025towards, koopman2019safety, koopman2020positive, cicchino2018gm, cicchino2019characteristics, cicchino2022pedestrian, iihs2023trucks, kullgren2010comparison, favaro2018disengagements, zhang2021disengagement, fu2024insufficiencies, salvini2021safety
- Level n/a: webb2020waymo, iso2022iso34502, riedmaier2020survey, tang2023survey, westhofen2021criticality, hoss2022review, salay2018using, putze2023quantification, koopman2022ul4600, fraadeblanar2018measuring, hartmann2026evolution

## Entries

| key | name | year | kind | level | speaker | conf | verified |
|---|---|---|---|---|---|---|---|
| kalra2016driving | RAND Driving to Safety (miles to demonstrate reliability) | 2016 | study | 9 | none | high | yes |
| zheng2023planning | Planning Reliability Assurance Tests for AVs | 2023 | study | 9 | none | high | yes |
| webb2020waymo | Waymo Safety Methodologies and Safety Readiness Determinations | 2020 | position | n/a | none | high | yes |
| kusano2022collision | Waymo Collision Avoidance Testing (CAT) | 2022 | benchmark | 5 | none | high | yes |
| scanlon2021waymo | Waymo counterfactual simulation of reconstructed fatal crashes (Chandler) | 2021 | study | 5 | none | high | yes |
| kusano2023comparison | Waymo rider-only crash rates vs human benchmarks (7.1M miles) | 2023 | study | 9 | none | high | yes |
| kusano2025comparison | Waymo rider-only crash rates by crash type (56.7M miles) | 2025 | study | 9 | none | high | yes |
| dilillo2023comparative | Waymo vs human liability claims (Swiss Re, 3.8M rider-only miles) | 2023 | study | 9 | none | high | yes |
| dilillo2024swissre | Waymo vs latest-generation human-driven vehicles: liability claims at 25.3M miles | 2024 | study | 9 | none | medium | yes |
| favaro2023interpreting | Interpreting Safety Outcomes (Waymo credibility paradox) | 2023 | position | 9 | none | high | yes |
| chen2024initial | Initial Indications of Safety of Driverless ADS (SF crash rates) | 2024 | study | 9 | none | high | yes |
| feng2021nade | NADE: Naturalistic and Adversarial Driving Environment | 2021 | benchmark | 4 | none | high | yes |
| feng2023dense | Dense deep reinforcement learning (D2RL) for AV safety validation | 2023 | benchmark | 4 | none | medium | yes |
| yang2022sparse | Adaptive safety evaluation with sparse control variates | 2022 | study | 4 | none | medium | yes |
| winkelmann2022transfer | Transfer Importance Sampling across test setups | 2022 | study | 6 | none | high | yes |
| glasmacher2023acquire | Cost-optimal scenario acquisition framework | 2023 | study | 5 | none | medium | yes |
| pegasus2019 | PEGASUS project (scenario-based validation of highly automated driving) | 2019 | standard | 4 | none | high | yes |
| iso2022iso34502 | ISO 34502:2022 scenario-based safety evaluation framework | 2022 | standard | n/a | none | high | yes |
| unece2021r157 | UN Regulation No. 157 (ALKS) validation regime | 2021 | standard | 4 | none | medium | yes |
| tenbrock2021conscend | ConScenD: concrete R157 scenarios from highD | 2021 | dataset | 5 | none | high | yes |
| riedmaier2020survey | Survey on scenario-based safety assessment of automated vehicles | 2020 | study | n/a | none | high | yes |
| tang2023survey | Survey on ADS testing: landscapes and trends | 2023 | study | n/a | none | high | yes |
| myers2020passfail | Pass-fail criteria for scenario-based ADS testing | 2020 | position | 4 | none | high | yes |
| westhofen2021criticality | Criticality metrics for automated driving: review and suitability analysis | 2021 | study | n/a | none | high | yes |
| singh2023diversity | Diversity analysis of lead-vehicle safety metrics | 2023 | study | 9 | none | high | yes |
| hoss2022review | Review of testing object-based environment perception | 2022 | study | n/a | none | high | yes |
| salay2018using | ISO 26262 process requirements assessed for ML | 2018 | position | n/a | none | high | yes |
| putze2023quantification | On quantification for SOTIF (ISO 21448) validation | 2023 | position | n/a | none | high | yes |
| betschinske2025towards | Efficient quantitative validation of residual risk (FOT reduction approaches) | 2025 | study | 9 | none | high | yes |
| xing2022ontology | Ontology-based identification of perception triggering conditions (SOTIF) | 2022 | study | 7 | none | high | yes |
| koopman2022ul4600 | UL 4600 safety case standard (Koopman overview) | 2022 | standard | n/a | none | high | yes |
| koopman2019safety | Safety argument for public-road testing of AVs | 2019 | position | 9 | none | high | yes |
| koopman2020positive | Positive Trust Balance for self-driving car deployment | 2020 | position | 9 | none | high | yes |
| fraadeblanar2018measuring | RAND Measuring Automated Vehicle Safety: Forging a Framework | 2018 | position | n/a | none | high | yes |
| euroncap2023aebc2c | Euro NCAP AEB Car-to-Car test protocol v4.3 | 2023 | standard | 8 | none | high | yes |
| euroncap2026vta | Euro NCAP 2026 Virtual Test Assessment (VTA) and test-grid growth | 2026 | standard | 4 | none | medium | yes |
| nhtsa2024fmvss127 | FMVSS No. 127 Automatic Emergency Braking rule (May 2024, amended Nov 2024) | 2024 | standard | 8 | none | high | yes |
| iihs2024fcp2 | IIHS Vehicle-to-Vehicle Front Crash Prevention 2.0 test protocol | 2024 | standard | 8 | none | high | yes |
| iihs2024paeb | IIHS Pedestrian AEB test protocol version IV | 2024 | standard | 8 | none | high | yes |
| cicchino2018gm | Real-world effects of GM Forward Collision Alert and Front Automatic Braking | 2018 | study | 9 | none | high | yes |
| cicchino2019characteristics | Characteristics of rear-end crashes involving AEB-equipped vehicles | 2019 | study | 9 | none | high | yes |
| cicchino2022pedestrian | Effects of pedestrian AEB on pedestrian crash risk | 2022 | study | 9 | none | high | yes |
| kidd2023characteristics | AEB response characteristics in IIHS FCP-rated vehicles | 2023 | study | 8 | none | medium | yes |
| iihs2023trucks | IIHS: front crash prevention less effective against trucks and motorcycles | 2023 | study | 9 | none | high | yes |
| kullgren2010comparison | Euro NCAP star ratings vs real-world crash data | 2010 | study | 9 | none | medium | yes |
| mcity2022rates | Mcity Test Facility recharge rates | 2022 | tooling | 8 | none | high | yes |
| mcity2024digitaltwin | Mcity open-source digital twin and TeraSim | 2024 | tooling | 5 | none | medium | yes |
| son2022pgvil | Proving-ground-based Vehicle-in-the-Loop simulation with consistency validation | 2022 | tooling | 6 | none | medium | yes |
| zhang2025combined | Combined virtual-real (digital twin) AEB testing: field experiments | 2025 | study | 6 | none | low | yes |
| cui2025vpautotest | VP-AutoTest virtual-physical fusion testing platform | 2025 | tooling | 6 | none | medium | yes |
| wu2026fromcode | From Code to Road: VIL and digital-twin framework for central car server testing | 2026 | tooling | 6 | none | medium | yes |
| kaiser2025coupled | Coupled cyclist-in-the-loop and vehicle-in-the-loop test environment | 2025 | tooling | 6 | none | medium | yes |
| novickineto2023twice | TWICE dataset: digital twin of test-track scenarios in a HIL lab | 2023 | dataset | 6 | none | high | yes |
| izquierdo2022testing | Testing predictive ADS on proving grounds: lessons learned (BRAVE) | 2022 | position | 8 | none | high | yes |
| dauner2023parting | Parting with Misconceptions (nuPlan open-loop vs closed-loop) | 2023 | benchmark | 5 | none | high | yes |
| dauner2024navsim | NAVSIM: data-driven non-reactive simulation and benchmarking | 2024 | benchmark | 5 | Pavone | high | yes |
| wang2026openloop | Do open-loop metrics predict closed-loop driving? NAVSIM vs Bench2Drive | 2026 | study | 4 | none | high | yes |
| ljungbergh2024neuroncap | NeuroNCAP: photorealistic closed-loop safety testing | 2024 | benchmark | 5 | none | high | yes |
| li2024rigorous | Rigorous simulation-based testing of four open autopilots | 2024 | red-team | 4 | none | high | yes |
| montali2023wosac | Waymo Open Sim Agents Challenge (WOSAC) | 2023 | tooling | 5 | none | high | yes |
| dyro2024realistic | Realistic extreme behavior generation for AV testing | 2024 | red-team | 3 | Pavone | high | yes |
| favaro2018disengagements | AV disengagements: trends, triggers and regulatory limitations | 2018 | study | 9 | none | medium | no |
| zhang2021disengagement | Disengagement cause-and-effect extraction with an NLP pipeline | 2021 | study | 9 | none | high | yes |
| fu2024insufficiencies | Characterization and mitigation of functional insufficiencies in ADS | 2024 | study | 9 | none | high | yes |
| iso2025iso10218 | ISO 10218-1/-2:2025 industrial robot safety (absorbs ISO/TS 15066) | 2025 | standard | 7 | none | high | yes |
| hartmann2026evolution | Evolution of ISO 10218 (2011 vs 2025) and integration of ISO/TS 15066 | 2026 | study | n/a | none | high | yes |
| hartmann2026biofidelic | Systematic review of biofidelic instrumentation for PFL cobot testing | 2026 | study | 7 | none | high | yes |
| kirschner2022iso15066 | ISO/TS 15066: how different interpretations affect risk assessment | 2022 | study | 7 | none | high | yes |
| svarny2020collisionforcemap | 3D collision-force map for safe human-robot collaboration | 2020 | study | 7 | none | high | yes |
| svarny2022skins | Effect of protective soft skins on collision forces (2,250 measurements) | 2022 | study | 7 | none | high | yes |
| salvini2021safety | On the safety of mobile robots in public spaces: gaps in EN ISO 13482 | 2021 | position | 9 | none | high | yes |
| obi2026safegate | SafeGate: ISO 13482-grounded pre-execution safety gate for LLM-controlled robots | 2026 | benchmark | 0 | none | medium | yes |

## Entry details

### kalra2016driving: RAND Driving to Safety (miles to demonstrate reliability) (2016)
- Org: RAND Corporation
- URL: https://www.autosafety.org/wp-content/uploads/2016/04/RAND-AV-Report.pdf
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Statistical analysis (binomial / Poisson confidence bounds) of on-road miles needed to bound AV failure rates; no system under test, the 'evaluation' is naturalistic driving exposure.
- Measures: Miles of failure-free or observed driving needed to demonstrate fatality, injury and crash rates relative to human baselines at given confidence and precision.
- Size: US 2013 baselines: 1.09 fatalities, 77 injuries, 190 crashes per 100M miles
- Reported metrics: 275M failure-free miles to show fatality rate <= 1.09/100M miles at 95% confidence (about 12.5 years for a 100-vehicle fleet 24/7 at 25 mph); about 8.8B miles (about 400 years) to demonstrate a 20% improvement over the human fatality rate.
- Cost evidence: Time cost only: tens to hundreds of years of fleet driving; motivates accelerated, virtual and scenario testing.
- Validity evidence: Level-9 outcome statistics are the ground truth against which every other level is compared; the paper quantifies why they are unattainable pre-deployment.
- Notes: Outside the 2018-2026 window but canonical. rand.org returned HTTP 403; verified via the autosafety.org mirror of the PDF.

### zheng2023planning: Planning Reliability Assurance Tests for AVs (2023)
- Org: Virginia Tech / Univ. of Arizona
- URL: https://arxiv.org/abs/2312.00186 (arXiv 2312.00186)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Statistical test planning: how many AVs to test for how many miles and the pass criterion, using homogeneous and non-homogeneous Poisson process models fitted to California DMV disengagement data; Pareto-front trade-off of test objectives.
- Measures: Required test fleet size, mileage and pass/fail rule for a reliability demonstration test given disengagement-rate priors.
- Size: California DMV disengagement reports
- Reported metrics: none stated
- Cost evidence: Explicitly optimises number of vehicles x miles (the test cost) against demonstration confidence; no dollar figures.
- Validity evidence: Uses disengagements as the reliability proxy; validity of disengagements as a safety proxy is itself contested (see fu2024insufficiencies, zhang2021disengagement).

### webb2020waymo: Waymo Safety Methodologies and Safety Readiness Determinations (2020)
- Org: Waymo
- URL: https://arxiv.org/abs/2011.00054 (arXiv 2011.00054)
- Kind: position; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Describes the portfolio: hazard analysis, scenario-based verification, simulated deployments (large-scale log playback and counterfactual simulation after operator disengage), closed-course and public-road testing, HIL bench tests; no single score.
- Measures: Framework for deciding safety readiness of an L4 ADS across hardware, ADS behaviour and operations layers; ODD-specific.
- Size: Over 20M public-road miles and 'billions of miles' in simulation at time of writing
- Reported metrics: none stated
- Cost evidence: Reports >20M real miles, billions of simulated miles, more than a decade of closed-course testing; no dollar or hour figures.
- Validity evidence: States closed-course testing is used to build and validate elements of simulation and that counterfactual simulation after disengagement has 'very high credibility' because the software drove in real time most of the time; no quantitative agreement numbers.
- Notes: Spans ladder levels 4-9 by construction; level left null.

### kusano2022collision: Waymo Collision Avoidance Testing (CAT) (2022)
- Org: Waymo
- URL: https://arxiv.org/abs/2212.08148 (arXiv 2212.08148)
- Kind: benchmark; ladder level: 5; safety focus: yes; confidence: high; URL verified: yes
- Modality: Scenario-based responder-role tests: the full ADS is fed real sensor logs recorded on a closed test track (increasingly synthetic sensor data), re-simulated closed-loop against new software; scored by collision occurrence and probability of serious injury p(MAIS3+) versus a NIEON (non-impaired, eyes-on) human reference model; a subset of scenarios is physically reproduced on the test track with soft targets and mannequins.
- Measures: Whether the ADS meets or exceeds a competent human reference in urgent collision-avoidance scenarios, aggregated by scenario safety group and road-user group.
- Size: Over 13,000 scenarios for the SF/PHX ODD (48% pedestrian/cyclist conflicts, 52% vehicle); about 70 scenarios reproduced on a test track for each start of fully autonomous operation
- Reported metrics: Serious-injury thresholds p(MAIS3+) >= 5% (vehicle-vehicle), >= 1.5% (child pedestrian), >= 10% (other VRU); NIEON reference prevented 84% of serious-injury risk in reconstructed fatal crashes; release-to-release change in aggregate score 1.5% (collision metric) and 0.6% (serious injury metric); 25% (106) of newly observed on-road events were not covered by the existing database and were added.
- Cost evidence: Simulation evaluates thousands of scenarios 'within hours instead of months or years' on track; track testing limited to about 70 scenarios per launch because of time and hazard to test staff; synthetic scenarios used where track collection is too dangerous or impractical.
- Validity evidence: Simulation-vs-track check: simulations must give a conservative collision count (as many or more simulated collisions than on track) and simulated trajectories must be even with or ahead of track trajectories; qualitative pass only, no correlation coefficient published.
- Notes: Numbers taken from the full PDF text. Track subset is level 8; the bulk is level 5 (real sensor-data replay).

### scanlon2021waymo: Waymo counterfactual simulation of reconstructed fatal crashes (Chandler) (2021)
- Org: Waymo
- URL: https://waymo.com/research/waymo-simulated-driving-behavior-in-reconstructed/
- Kind: study; ladder level: 5; safety focus: yes; confidence: high; URL verified: yes
- Modality: Police-reconstructed fatal crashes converted to synthetic-sensor simulations; the Waymo Driver replaces either the initiator or responder; scored by collision avoided / mitigated / unchanged.
- Measures: Counterfactual collision-avoidance effectiveness of the ADS in every fatal crash in its ODD over 2008-2017.
- Size: 72 fatal crashes, 91 vehicle actors, Chandler AZ 2008-2017
- Reported metrics: 100% of collisions avoided as initiator; as responder 82% avoided, 10% mitigated, 8% unchanged.
- Cost evidence: Reconstruction requires police reports and expert alignment per crash; no hours reported.
- Validity evidence: Anchored to real fatal outcomes, but counterfactual; no independent check that simulated behaviour matches on-road behaviour in these scenes.

### kusano2023comparison: Waymo rider-only crash rates vs human benchmarks (7.1M miles) (2023)
- Org: Waymo
- URL: https://arxiv.org/abs/2312.12675 (arXiv 2312.12675)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Retrospective observational comparison: NHTSA Standing General Order (SGO) crash reports plus company mileage versus human benchmarks matched on vehicle type, road type and geography.
- Measures: Incidents per million miles (IPMM) for any-injury-reported and police-reported crashes, ADS vs human.
- Size: 7.14M rider-only miles (Phoenix, SF, LA) through Oct 2023
- Reported metrics: Any-injury 0.6 vs 2.80 IPMM (80% reduction); police-reported 2.1 vs 4.68 IPMM (55% reduction); statistically significant when pooled.
- Cost evidence: Requires millions of deployed miles; authors caution results are 'directional'.
- Validity evidence: Ground-truth outcome data; caveats on benchmark imprecision and human underreporting.

### kusano2025comparison: Waymo rider-only crash rates by crash type (56.7M miles) (2025)
- Org: Waymo
- URL: https://arxiv.org/abs/2505.01515 (arXiv 2505.01515)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: As kusano2023comparison, disaggregated into 11 crash-type groups; SGO data through Jan 2025.
- Measures: Crashed-vehicle rates for injury-reported and airbag-deployment crashes by crash type versus matched human benchmarks.
- Size: 56.7M rider-only miles
- Reported metrics: Vehicle-to-vehicle intersection crashes: 96% reduction in injury-reported (CI 87-99%) and 91% in airbag-deployment (CI 76-98%); significant reductions for cyclist, motorcycle, pedestrian and single-vehicle groups; no significant disbenefit in any of 11 groups.
- Cost evidence: Tens of millions of deployed miles needed before per-type confidence intervals become informative.
- Validity evidence: Outcome data; the paper is the empirical anchor for what lower-level evaluations should predict.

### dilillo2023comparative: Waymo vs human liability claims (Swiss Re, 3.8M rider-only miles) (2023)
- Org: Swiss Re / Waymo
- URL: https://arxiv.org/abs/2309.01206 (arXiv 2309.01206)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Insurance liability claims frequency (bodily injury, property damage) of the Waymo fleet versus Swiss Re private-passenger baselines calibrated by mileage and zip code.
- Measures: Claims per million miles as a third-party safety outcome metric.
- Size: 3.8M rider-only miles plus 35M+ miles with a safety specialist
- Reported metrics: Rider-only: 0 bodily-injury claims vs 1.11 per million miles baseline; property damage 0.78 vs 3.26 per million miles.
- Cost evidence: Uses existing insurer claims infrastructure; no evaluation cost beyond deployment.
- Validity evidence: Claims are an independent, financially incentivised outcome record; small counts limit precision.

### dilillo2024swissre: Waymo vs latest-generation human-driven vehicles: liability claims at 25.3M miles (2024)
- Org: Swiss Re / Waymo
- URL: https://waymo.com/blog/2024/12/new-swiss-re-study-waymo/
- Kind: study; ladder level: 9; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Liability claims frequency over 25.3M rider-only miles versus Swiss Re baselines from 500k+ claims and 200B+ miles, including a 2018-2021 ADAS-equipped vehicle cohort.
- Measures: Property-damage and bodily-injury claim reductions vs overall population and vs new ADAS-equipped vehicles.
- Size: 25.3M miles; 9 property damage claims, 2 bodily injury claims
- Reported metrics: 88% fewer PD and 92% fewer BI claims vs overall population; 86% and 90% vs 2018-2021 ADAS-equipped vehicles; expected human counts 78 PD and 26 BI.
- Cost evidence: None beyond deployment exposure.
- Validity evidence: Independent insurer data; both BI claims still open at publication.
- Notes: Only the Waymo blog post was fetched; author list from the blog's citation, not the paper page.

### favaro2023interpreting: Interpreting Safety Outcomes (Waymo credibility paradox) (2023)
- Org: Waymo
- URL: https://arxiv.org/abs/2306.14923 (arXiv 2306.14923)
- Kind: position; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Argument paper: observed contact events during fully autonomous operation vs human baselines, framed within a broader readiness determination.
- Measures: How much confidence lagging outcome statistics can carry early in deployment and why they must be complemented by other estimation techniques.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Names the 'credibility paradox': outcome data are the most credible but least available; argues for event-level analysis and continuous confidence updating.

### chen2024initial: Initial Indications of Safety of Driverless ADS (SF crash rates) (2024)
- Org: UC Berkeley PATH
- URL: https://arxiv.org/abs/2403.14648 (arXiv 2403.14648)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Crashes per million miles from public reports: Uber TNC (CPUC 2020), supervised AVs (CA DMV Dec 2020-Nov 2022), driverless Waymo and Cruise (Mar 2022-Aug 2023), San Francisco excluding freeways.
- Measures: Independent (non-company) comparison of driverless and supervised AV crash rates to a human ride-hail baseline.
- Size: not stated
- Reported metrics: Supervised AV about equal to Uber human CPMM; driverless Waymo lower; driverless Cruise higher; samples judged too small for firm conclusions.
- Cost evidence: none stated
- Validity evidence: Highlights that outcome comparisons depend heavily on the baseline and on sample size.

### feng2021nade: NADE: Naturalistic and Adversarial Driving Environment (2021)
- Org: University of Michigan (Henry Liu)
- URL: https://www.nature.com/articles/s41467-021-21007-8
- Kind: benchmark; ladder level: 4; safety focus: yes; confidence: high; URL verified: yes
- Modality: AV decision model driven closed-loop in a highway simulator (and CARLA) whose background vehicles are naturalistic but receive sparse RL-chosen adversarial manoeuvre adjustments; crash rate estimated with importance-sampling weights so the estimate stays unbiased.
- Measures: Unbiased estimate of the AV crash rate per mile with far fewer simulated miles than naturalistic testing.
- Size: Two AV models; five collision types checked for unbiasedness
- Reported metrics: Tests needed: 8.74e4 vs 4.39e7 (about 500x) for AV-I and 2.32e4 vs 1.41e8 (about 6,000x) for AV-II at relative half-width 0.3; only 1.5-1.7% of background manoeuvres adjusted.
- Cost evidence: Orders-of-magnitude reduction in simulated miles; 10M-35M fewer miles per evaluation (paper figures).
- Validity evidence: Weighted crash rates match the naturalistic environment across five collision types (internal consistency); no real-world validation.
- Notes: Fetched via nature.com cookie-redirect URL of the same article.

### feng2023dense: Dense deep reinforcement learning (D2RL) for AV safety validation (2023)
- Org: University of Michigan (Henry Liu)
- URL: https://github.com/michigan-traffic-lab/Dense-Deep-Reinforcement-Learning
- Kind: benchmark; ladder level: 4; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Background agents trained with D2RL (MDP edited to drop non-safety-critical states) drive adversarially in SUMO-based naturalistic traffic; AV under test evaluated closed-loop; crash rate, PET, TTC and bumper distance recorded; importance weights keep the estimate unbiased.
- Measures: Accelerated, unbiased crash-rate estimation of an AV in an intelligent testing environment.
- Size: not stated
- Reported metrics: Paper claims acceleration by multiple orders of magnitude relative to naturalistic driving (abstract).
- Cost evidence: Repository states the naturalistic (NDE) baseline experiment alone required 72,000 core-hours.
- Validity evidence: Unbiasedness shown against the naturalistic environment in simulation; the paper also reports augmented-reality testing at Mcity with a real vehicle (not verified here).
- Notes: nature.com blocked the fetch; verified via the official code repository which cites the paper and gives the 72,000 core-hour figure. Abstract wording from search snippets.

### yang2022sparse: Adaptive safety evaluation with sparse control variates (2022)
- Org: Tsinghua / University of Michigan
- URL: https://arxiv.org/abs/2212.00517 (arXiv 2212.00517)
- Kind: study; ladder level: 4; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Post-test variance reduction: control variates on the few critical scenario variables, stratified, regression-optimised; validated on high-dimensional overtaking scenarios in simulation.
- Measures: Variance of the crash-rate estimate for a given number of simulated tests.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: Claims dramatic variance reduction (fewer tests for same precision); no absolute numbers in abstract.
- Validity evidence: Simulation-internal only.

### winkelmann2022transfer: Transfer Importance Sampling across test setups (2022)
- Org: TU Berlin / Volkswagen
- URL: https://arxiv.org/abs/2204.07619 (arXiv 2204.07619)
- Kind: study; ladder level: 6; safety focus: yes; confidence: high; URL verified: yes
- Modality: Importance-sampling proposal learned in a cheap, scalable setup (simulation) and transferred to a more trustworthy but expensive setup (proving ground / real vehicle) to estimate failure probability with lower variance.
- Measures: Failure-probability estimate that trades bias of the cheap setup against variance of the expensive one.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: Explicit cost framing: virtual tests are cheap and scalable, real tests are trustworthy but expensive; efficiency gain claimed without dollar figures.
- Validity evidence: Formal bias-variance argument; the paper is a template for combining ladder levels rather than a validation study.

### glasmacher2023acquire: Cost-optimal scenario acquisition framework (2023)
- Org: RWTH Aachen (ika)
- URL: https://arxiv.org/abs/2307.11647 (arXiv 2307.11647)
- Kind: study; ladder level: 5; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Meta-model predicting coverage, quality and expense of a hybrid scenario-acquisition pipeline (real-world mining vs generated scenarios) under technical, economic and quality constraints.
- Measures: Cost-optimal mix of real and generated scenarios for scenario-based testing.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: Framework is explicitly about acquisition cost, but the abstract gives no absolute cost figures.
- Validity evidence: none stated

### pegasus2019: PEGASUS project (scenario-based validation of highly automated driving) (2019)
- Org: DLR and 17 partners, BMWi-funded
- URL: https://www.dlr.de/en/ts/research-transfer/projects/pegasus
- Kind: standard; ladder level: 4; safety focus: yes; confidence: high; URL verified: yes
- Modality: Six-layer scenario model; logical scenarios parameterised from naturalistic driving and crash data; tests executed in simulation, test bench and proving ground; pass criteria benchmarked against human performance data.
- Measures: Generally accepted quality criteria, tools and methods to approve a highway-pilot function; replaces distance-based release.
- Size: 17 partners, Jan 2016-Jun 2019
- Reported metrics: none stated
- Cost evidence: Project claims proof of safety 'with an economically justifiable effort'; no figures on the public page.
- Validity evidence: Human-performance benchmarks derived from naturalistic driving studies; no published correlation between the method's verdicts and field outcomes.
- Notes: Level assigned to the simulation core; the method spans 4-8.

### iso2022iso34502: ISO 34502:2022 scenario-based safety evaluation framework (2022)
- Org: ISO/TC 22/SC 33/WG 9 (Japan-led)
- URL: https://www.prostep.org/en/medialibrary/fact-sheets/iso-34502-test-scenarios-for-automated-driving-systems-scenario-based-safety-evaluation-framework
- Kind: standard; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Process standard: critical scenarios built from perception, traffic and vehicle-control disturbances; applies to system analysis, test-scenario development and testing of ADS (initially limited-access highways).
- Measures: Whether an ADS is free of unreasonable risk across a systematically derived critical-scenario set; does not itself define pass thresholds.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: No validity data; it is a process framework.
- Notes: iso.org returned 403; verified via the prostep ivip fact sheet.

### unece2021r157: UN Regulation No. 157 (ALKS) validation regime (2021)
- Org: UNECE WP.29
- URL: https://efs.consulting/en/insights/article/information-security/unece-r157/
- Kind: standard; ladder level: 4; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Type approval of Automated Lane Keeping Systems via Annex 4 audit plus Annex 5 tests: virtual simulation of traffic-critical scenarios (cut-in, cut-out, lead deceleration), critical-scenario test-track runs, and public-road driving; pass criterion is collision avoidance where a competent and careful human driver could avoid it.
- Measures: Regulatory conformity of an L3 highway function; first regulation to admit simulation as type-approval evidence.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: Combines three ladder levels (4, 8, 9) in one homologation; no cost figures.
- Validity evidence: Requires the authority to verify accuracy of the simulation tool against physical results; no public correlation numbers.
- Notes: EUR-Lex fetch returned no text; details verified from a consultancy summary. 60 km/h initially, later 130 km/h.

### tenbrock2021conscend: ConScenD: concrete R157 scenarios from highD (2021)
- Org: RWTH Aachen (ika) / fka
- URL: https://arxiv.org/abs/2103.09772 (arXiv 2103.09772)
- Kind: dataset; ladder level: 5; safety focus: yes; confidence: high; URL verified: yes
- Modality: Real highway trajectories (highD drone data) filtered to the UNECE R157 cut-in/cut-out/deceleration scenario classes and exported as OpenSCENARIO files runnable in CARLA and esmini.
- Measures: Parameterised, real-data-derived test cases for ALKS system-level simulation.
- Size: More than 340 concrete scenarios
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Parameters come from measured traffic, addressing R157's lack of parameterisation; no downstream validation.

### riedmaier2020survey: Survey on scenario-based safety assessment of automated vehicles (2020)
- Org: TU Munich / Kempten
- URL: https://portal.fis.tum.de/en/publications/survey-on-scenario-based-safety-assessment-of-automated-vehicles/
- Kind: study; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Literature survey with a taxonomy of scenario-based assessment (scenario sources, selection, execution in X-in-the-loop, evaluation) and its combination with formal verification.
- Measures: Landscape of methods; does not measure a system.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated

### tang2023survey: Survey on ADS testing: landscapes and trends (2023)
- Org: USTC / Kyushu / NTU and others
- URL: https://arxiv.org/abs/2206.05961 (arXiv 2206.05961)
- Kind: study; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Survey of module-level (sensing, perception, planning, control) and system-level ADS testing, simulator-based vs real-world, with explicit attention to the simulator-to-real gap.
- Measures: Map of testing approaches and open problems.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated

### myers2020passfail: Pass-fail criteria for scenario-based ADS testing (2020)
- Org: Connected Places Catapult (UK)
- URL: https://arxiv.org/abs/2005.09417 (arXiv 2005.09417)
- Kind: position; ladder level: 4; safety focus: yes; confidence: high; URL verified: yes
- Modality: Two scoring families: prescriptive rules (must always hold per test) and risk-based rules (undesirable outcomes that may occur only below a frequency), decided statistically over functional scenario groups.
- Measures: How to turn scenario test outputs into automated type-approval decisions.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Argues single-test pass/fail is impossible for risk-based rules; hypothesis-testing framing.

### westhofen2021criticality: Criticality metrics for automated driving: review and suitability analysis (2021)
- Org: DLR / OFFIS / Bosch / others
- URL: https://arxiv.org/abs/2108.02403 (arXiv 2108.02403)
- Kind: study; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Review of criticality metrics (TTC, PET, required deceleration and many others) with a suitability-analysis procedure for picking metrics per application.
- Measures: Which surrogate-safety metrics are fit for scenario filtering, risk assessment or pass/fail.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Provides the methodical tool but no empirical correlation of metrics with crash outcomes.

### singh2023diversity: Diversity analysis of lead-vehicle safety metrics (2023)
- Org: Transportation Research Center / Ohio State / NHTSA
- URL: https://arxiv.org/abs/2306.14657 (arXiv 2306.14657)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: 33 base metrics (51 variants) from 1967-2022 applied to highway trajectory data and to a high-risk collision/near-miss dataset; agreement between metrics examined.
- Measures: Whether surrogate safety metrics agree on ranking vehicle performance in lead-vehicle interactions.
- Size: 33 base metrics, up to 51 variants; two datasets
- Reported metrics: No dominant empirical consensus among metrics.
- Cost evidence: none stated
- Validity evidence: Direct evidence that the scoring choice, not just the test level, changes verdicts; a false-alarm / sensitivity concern for any metric-based evaluation.

### hoss2022review: Review of testing object-based environment perception (2022)
- Org: RWTH Aachen (ika)
- URL: https://arxiv.org/abs/2102.08460 (arXiv 2102.08460)
- Kind: study; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Review of perception V&V at the perception-planning interface: test criteria/metrics, test scenarios, reference (ground-truth) data; covers safety standards, benchmarking, sensor models.
- Measures: State of safety-aware perception testing; concludes it remains an open issue.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: Reference-data (labelling) cost identified as a central bottleneck.
- Validity evidence: none stated

### salay2018using: ISO 26262 process requirements assessed for ML (2018)
- Org: University of Waterloo
- URL: https://arxiv.org/abs/1808.01614 (arXiv 1808.01614)
- Kind: position; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Clause-by-clause assessment of ISO 26262 Part 6 software process requirements for supervised ML components, with proposed new requirements where gaps exist.
- Measures: Applicability of the functional-safety lifecycle to learned components.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: none stated

### putze2023quantification: On quantification for SOTIF (ISO 21448) validation (2023)
- Org: DLR / OFFIS
- URL: https://arxiv.org/abs/2304.10170 (arXiv 2304.10170)
- Kind: position; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Terminology and risk decomposition enabling quantitative SOTIF acceptance criteria; discusses that ISO 21448 examples simulate triggering conditions without their occurrence probability.
- Measures: How residual risk from functional insufficiencies can be quantified and validated.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Argues that scenario tests without exposure frequencies cannot yield residual-risk numbers.

### betschinske2025towards: Efficient quantitative validation of residual risk (FOT reduction approaches) (2025)
- Org: TU Darmstadt (FZD) / partners
- URL: https://arxiv.org/abs/2506.10363 (arXiv 2506.10363)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Systematic evaluation of reduction approaches for Field Operational Testing (FOT) against quantifiability, validity threats, missing links and black-box compatibility.
- Measures: Whether any method can replace on-road exposure for demonstrating residual risk at higher automation levels.
- Size: not stated
- Reported metrics: Conclusion: no identified alternative can fully replace FOT.
- Cost evidence: Frames FOT effort as impractical at higher automation levels; no numbers in abstract.
- Validity evidence: Catalogues validity threats of each substitute for on-road testing.

### xing2022ontology: Ontology-based identification of perception triggering conditions (SOTIF) (2022)
- Org: Tongji University
- URL: https://arxiv.org/abs/2210.08724 (arXiv 2210.08724)
- Kind: study; ladder level: 7; safety focus: yes; confidence: high; URL verified: yes
- Modality: Ontologies of triggering sources and perception stages generate candidate triggering conditions; a subset is executed with an L3 vehicle in field tests and scored by whether risky behaviour results.
- Measures: Yield of a systematic triggering-condition search in producing real perception insufficiencies.
- Size: 87 triggering conditions identified, 20 field-tested
- Reported metrics: 8 of 20 field-tested conditions triggered risky behaviour (40% hit rate).
- Cost evidence: 20 physical field tests for 87 candidates; a concrete precision figure for an analysis-to-hardware funnel.
- Validity evidence: Analysis-level candidates confirmed on hardware at 40%; the remainder are false alarms at the analysis level or untested.

### koopman2022ul4600: UL 4600 safety case standard (Koopman overview) (2022)
- Org: UL Standards / Edge Case Research / CMU
- URL: https://ia801903.us.archive.org/3/items/l-109-ul-4600/L109-UL4600_updated.pdf
- Kind: standard; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Goal-based standard (issued April 2020): a safety case of claims, arguments and evidence with minimum coverage prompts, Safety Performance Indicators (SPIs) as feedback metrics, and objective assessment criteria; does not prescribe tests.
- Measures: Completeness and well-formedness of a safety case for a fully autonomous product; SPIs measure behaviour rates (e.g. pedestrian standoff violations) and assumption validity (e.g. correlated camera/lidar false negatives).
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: SPIs are designed as leading indicators tied to safety-case assumptions; the standard gives no empirical linkage to outcomes.

### koopman2019safety: Safety argument for public-road testing of AVs (2019)
- Org: CMU / Edge Case Research
- URL: https://saemobilus.sae.org/articles/safety-argument-considerations-public-road-testing-autonomous-vehicles-2019-01-0123
- Kind: position; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Safety-case structure for human-supervised road testing: supervisor alertness and timely response, adequate failure management, and an autonomy failure profile compatible with supervision.
- Measures: Conditions under which level-9 data collection with safety drivers is itself acceptably safe.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Key claim: supervisability degrades nonlinearly as autonomy failure rates fall, so safer systems are harder to supervise.

### koopman2020positive: Positive Trust Balance for self-driving car deployment (2020)
- Org: CMU / Edge Case Research
- URL: https://arxiv.org/abs/2009.05801 (arXiv 2009.05801)
- Kind: position; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Decision framework: deploy on a practicable amount of testing plus engineering rigour and safety culture, conditioned on stringent post-deployment SPI feedback.
- Measures: How to decide deployment when lagging outcome metrics are statistically insufficient.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Explicitly trades pre-deployment confidence for operational monitoring; a VOI-style argument in prose.

### fraadeblanar2018measuring: RAND Measuring Automated Vehicle Safety: Forging a Framework (2018)
- Org: RAND Corporation (for Uber ATG)
- URL: https://trid.trb.org/view/1564626
- Kind: position; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Framework for defining, measuring and communicating AV safety across development stages; discusses proxy measures, closed-course and simulation measurement.
- Measures: Which measures (leading vs lagging, proxies) are usable at each stage.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Notes proprietary restrictions prevent public cross-manufacturer comparison of proxies with outcomes.
- Notes: rand.org returned 403; verified via TRID record.

### euroncap2023aebc2c: Euro NCAP AEB Car-to-Car test protocol v4.3 (2023)
- Org: Euro NCAP
- URL: https://cdn.euroncap.com/cars/assets/euro_ncap_aeb_c2c_test_protocol_v43_1e6ed06def.pdf
- Kind: standard; ladder level: 8; safety focus: yes; confidence: high; URL verified: yes
- Modality: Production vehicle driven by a steering/pedal robot toward a Global Vehicle Target (GVT, radar/lidar/camera-representative soft car) on a dry >0.9 PBC track; scenarios CCRs (stationary), CCRm (moving), CCRb (braking), plus crossing/head-on; scored on impact-speed reduction and FCW timing per speed/overlap grid cell; measurement accuracy 0.1 km/h speed, 0.03 m position.
- Measures: AEB/FCW avoidance and mitigation performance over a speed x overlap grid (CCRs 10-50 km/h AEB, 55-80 km/h FCW; CCRm 30-80 km/h).
- Size: Manufacturer supplies a colour-coded prediction for every grid cell; lab tests all grid points if no prediction is supplied, stepping 10 km/h then 5 km/h around first contact
- Reported metrics: none stated
- Cost evidence: Euro NCAP FAQ: a full test programme 'costs several hundreds of thousands of Euros'; typically a minimum of six test vehicles, one dedicated to ADAS track testing; dummies and targets are expensive and need regular maintenance. Only equipment on the TB029 supplier list may be used. Manufacturer must supply a dossier including HiL/SiL/ViL validation evidence and field false-positive evidence for head-on functions.
- Validity evidence: Grid predictions from the OEM are spot-checked physically (see euroncap2026vta); no published correlation of protocol scores with field crash rates for AEB, only for the older crash-test stars (kullgren2010comparison).
- Notes: Cost statements from https://www.euroncap.com/faq/ (fetched).

### euroncap2026vta: Euro NCAP 2026 Virtual Test Assessment (VTA) and test-grid growth (2026)
- Org: Euro NCAP; IDIADA and MathWorks presentation
- URL: https://in.mathworks.com/content/dam/mathworks/mathworks-dot-com/company/events/conferences/automotive-conference-stuttgart/2026/emea-mac-2026-idiada-euro-ncap-virtual-testing.pdf
- Kind: standard; ladder level: 4; safety focus: yes; confidence: medium; URL verified: yes
- Modality: From 2026 OEMs submit a simulation dossier and virtual results (AEB and lane-support scenarios); OEM qualifies its model in-house with ISO correlation scores and KPIs; Euro NCAP randomly selects grid cells, physically tests them and validates the virtual data before computing acceptance.
- Measures: Same AEB/LSS grid as the physical protocol, but the bulk of cells scored in simulation with physical spot checks.
- Size: IDIADA chart: protocol test-run count rising from a few hundred (2014) to about 2,000+ runs by 2026, labelled the 'tipping point' where proving-ground-only testing is no longer feasible
- Reported metrics: none stated
- Cost evidence: Explicit statement that physical execution of the 2026 grid is infeasible, motivating virtual testing; AB Dynamics blog reports a ~186% scenario increase and about 6 months of full-time physical testing for all combinations (from search snippet, not verified in the fetched page).
- Validity evidence: Validity is enforced procedurally: correlation of virtual to physical results for randomly selected cells using ISO 18571-style metrics; tolerances not public in the fetched material.
- Notes: Official Euro NCAP VTA protocol PDF not fetched; the euroncap.com protocol index page was fetched but lists no file URLs.

### nhtsa2024fmvss127: FMVSS No. 127 Automatic Emergency Braking rule (May 2024, amended Nov 2024) (2024)
- Org: NHTSA
- URL: https://www.govinfo.gov/content/pkg/FR-2024-05-09/html/2024-09054.htm
- Kind: standard; ladder level: 8; safety focus: yes; confidence: high; URL verified: yes
- Modality: Compliance track tests of the production vehicle: three lead-vehicle scenarios (stopped, decelerating, slower-moving) at 10-100 km/h and four pedestrian scenarios (crossing, alongside, standing, obstructed) at 10-73 km/h in daylight and darkness, two false-activation tests (steel trench plate, parked vehicles); pass = no contact with the test device in every run; FCW audible and visual signal required up to 145 km/h.
- Measures: Regulatory minimum AEB/PAEB/FCW performance for all new light vehicles from 1 Sept 2029.
- Size: 7 crash-imminent scenarios plus 2 false-activation scenarios; multiple speeds each
- Reported metrics: Estimated 362 lives saved and 24,321 non-fatal injuries mitigated per year; benefits 17-21x costs.
- Cost evidence: Total annual compliance cost about $354M (2020 dollars), mostly software, radar added on ~5% of fleet; $550k-$680k per life saved; lifetime net benefit $5.82-7.26B. Nov 2024 amendment rejected allowing 5-of-7 run passes and rejected 10 km/h contact tolerance; PAEB no-contact worth about $179.1M vs allowing low-speed contact. Test-house note: high-speed runs need 200-300 m additional track and driving robots, soft targets and launch platforms.
- Validity evidence: Benefit estimates derive from real-world effectiveness studies of existing AEB (cicchino2018gm and others), i.e. level-9 evidence is used to justify a level-8 test; no direct validation of the test's own predictive power.
- Notes: Both the May 2024 rule and Nov 2024 amendment fetched from govinfo. The Final Regulatory Impact Analysis PDF (regulations.gov) returned 403.

### iihs2024fcp2: IIHS Vehicle-to-Vehicle Front Crash Prevention 2.0 test protocol (2024)
- Org: Insurance Institute for Highway Safety
- URL: https://www.iihs.org/media/65d706ca-2986-4b08-8f6b-c19cd6d79762/IlBtnQ/Ratings/Protocols/future%20programs/FCP_test_protocol_Version1_Draft.pdf
- Kind: standard; ladder level: 8; safety focus: yes; confidence: high; URL verified: yes
- Modality: Vehicle approaches stationary Soft Car 360 GVT, a motorcycle surrogate, or a real dry-van trailer at 50, 60 and 70 km/h, centred and offset; scored on FCW timing and speed reduction; rated good/acceptable/marginal/poor.
- Measures: Higher-speed and non-passenger-vehicle front crash prevention, replacing the 2013-2022 test at 20 and 40 km/h.
- Size: not stated
- Reported metrics: Old 20/40 km/h scenarios covered <3% of police-reported front-to-rear crashes; new speeds and targets raise relevance to 36% of rear-end and 43% of fatal rear-end crashes (Kidd 2022); AEB reduces police-reported front-to-rear crashes 34-50% across studies.
- Cost evidence: Requires GVT Rev F, motorcycle surrogate and a real tractor trailer; covered track for night tests; brake conditioning runs before each session.
- Validity evidence: Protocol redesign explicitly driven by level-9 evidence that superior-rated systems still under-perform against trucks and motorcycles (iihs2023trucks).

### iihs2024paeb: IIHS Pedestrian AEB test protocol version IV (2024)
- Org: Insurance Institute for Highway Safety
- URL: https://www.iihs.org/media/f6a24355-fe4b-4d71-bd19-0aab8b39aa7e/zQKIHQ/Ratings/Protocols/current/test_protocol_pedestrian_aeb.pdf
- Kind: standard; ladder level: 8; safety focus: yes; confidence: high; URL verified: yes
- Modality: Articulated adult and child pedestrian dummies: adult crossing at night (20, 40 km/h), child crossing from behind obstruction by day (20, 40 km/h), adult parallel at night (40, 60 km/h); night runs under high and low beams below 1 lux; rated good/acceptable/marginal/poor on speed reduction.
- Measures: Pedestrian AEB avoidance/mitigation including the nighttime conditions where real-world effectiveness was absent.
- Size: 3 scenarios x 2 speeds x beam settings
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Night scenarios added after cicchino2022pedestrian found no effect in unlit darkness; the protocol history is an example of level-9 evidence correcting a level-8 test.

### cicchino2018gm: Real-world effects of GM Forward Collision Alert and Front Automatic Braking (2018)
- Org: Insurance Institute for Highway Safety
- URL: https://www.iihs.org/api/datastoredocument/bibliography/2170
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Poisson regression of police-reported rear-end striking crash involvement rates, MY2013-2015 GM vehicles with vs without optional systems (VIN-matched), controlling for known risk factors.
- Measures: Crash-rate reduction attributable to FCW alone and FCW+AEB.
- Size: not stated
- Reported metrics: AEB+FCW: 43% fewer rear-end striking crashes, 64% fewer with injuries, 68% fewer with third-party injuries; FCW alone: 17%, 30%, 32%.
- Cost evidence: none stated
- Validity evidence: Level-9 outcome evidence that the technology class evaluated by track protocols delivers real reductions; consistent with 27-50% reductions in Volvo/Mazda and multi-make studies cited in the paper.

### cicchino2019characteristics: Characteristics of rear-end crashes involving AEB-equipped vehicles (2019)
- Org: Insurance Institute for Highway Safety
- URL: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1080/15389588.2019.1576172?fields=title,abstract,year,authors,venue,externalIds
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Logistic regression on rear-end crashes from 23 US states (2009-2016) to find situations where AEB-equipped striking vehicles are overrepresented.
- Measures: Residual crash scenarios that AEB fails to prevent.
- Size: not stated
- Reported metrics: AEB-equipped vehicles overrepresented in crashes with turning lead vehicles, lane changes, non-passenger-vehicle partners, snow/ice and higher-speed roads.
- Cost evidence: none stated
- Validity evidence: Shows the test scenarios (stationary target, low speed) miss the residual crash population; motivated the 2024 IIHS protocol change.
- Notes: Publisher page returned 403; verified via Semantic Scholar API record.

### cicchino2022pedestrian: Effects of pedestrian AEB on pedestrian crash risk (2022)
- Org: Insurance Institute for Highway Safety
- URL: https://www.iihs.org/research-areas/bibliography/ref/2243
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Poisson regression and quasi-induced exposure comparing pedestrian crash rates per insured vehicle year for vehicles with and without optional pedestrian AEB.
- Measures: Real-world effectiveness of pedestrian AEB by lighting, speed limit and manoeuvre.
- Size: not stated
- Reported metrics: 25-27% fewer pedestrian crashes, 29-30% fewer pedestrian injury crashes; no evidence of effect in unlit darkness, at speed limits >= 50 mph, or while turning.
- Cost evidence: none stated
- Validity evidence: Directly exposes the domain where daytime track tests overstate protection; led to IIHS night testing (iihs2024paeb) and FMVSS 127 darkness tests.

### kidd2023characteristics: AEB response characteristics in IIHS FCP-rated vehicles (2023)
- Org: Insurance Institute for Highway Safety
- URL: https://api.crossref.org/works/10.1016/j.aap.2023.107150
- Kind: study; ladder level: 8; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Instrumented IIHS track tests: time-to-collision at AEB onset and deceleration profiles compared across superior vs basic/advanced-rated systems.
- Measures: Mechanistic differences (earlier TTC, greater speed-dependent deceleration) behind rating levels.
- Size: not stated
- Reported metrics: Superior-rated systems brake at earlier TTC and with greater deceleration that increases with speed (from search summary).
- Cost evidence: none stated
- Validity evidence: Links the track rating to physical response parameters, not to field outcomes.
- Notes: Only Crossref metadata fetched (no abstract); findings from search snippet.

### iihs2023trucks: IIHS: front crash prevention less effective against trucks and motorcycles (2023)
- Org: IIHS / Transport Canada
- URL: https://www.iihs.org/news/detail/better-detection-of-large-trucks-motorcycles-would-improve-front-crash-prevention
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Crash-data effectiveness by struck-vehicle type plus track tests of five superior-rated vehicles against truck and motorcycle targets.
- Measures: Gap between a top track rating and field effectiveness by partner type.
- Size: not stated
- Reported metrics: Rear-end crash reductions: 53% vs passenger vehicles, 38% vs medium/heavy trucks, 41% vs motorcycles; all five test vehicles were 'superior' in the old test yet alerted later for trucks and motorcycles.
- Cost evidence: none stated
- Validity evidence: Direct evidence that a saturated level-8 rating (everyone superior) stopped discriminating field performance; the 2024 protocol (50/60/70 km/h, new targets) was the response.

### kullgren2010comparison: Euro NCAP star ratings vs real-world crash data (2010)
- Org: Folksam / Swedish Transport Administration
- URL: https://api.crossref.org/works/10.1080/15389588.2010.508804
- Kind: study; ladder level: 9; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Paired-comparison of two-car crashes (controls for crash severity) and police/insurance injury data, grouped by Euro NCAP star rating.
- Measures: Whether the crash-test star rating predicts real injury and fatality risk.
- Size: not stated
- Reported metrics: Later Kullgren et al. (2019, ESV) update: 5-star cars have 10% +/- 2.5% lower injury risk than 2-star cars, 23 +/- 8% lower fatal/serious, 68 +/- 32% lower fatal (from search summary of the 2019 paper).
- Cost evidence: none stated
- Validity evidence: The best-documented case in automotive testing of a standardized physical test correlating with outcomes; note it concerns crashworthiness stars, not AEB.
- Notes: Pre-2018 anchor. 2019 ESV update PDF on cdn.euroncap.com returned 403; only Crossref metadata of the 2010 paper fetched.

### mcity2022rates: Mcity Test Facility recharge rates (2022)
- Org: University of Michigan Mcity
- URL: https://mcity.umich.edu/wp-content/uploads/2022/11/11.1.22_TestFacilityRates-LC.pdf
- Kind: tooling; ladder level: 8; safety focus: yes; confidence: high; URL verified: yes
- Modality: Price sheet for a 32-acre urban/suburban proving ground (no system under test).
- Measures: Direct dollar cost of level-8 track time.
- Size: not stated
- Reported metrics: Whole track $3,127 per full day, $1,563 per half day (Leadership Circle members, Nov 2022; Nov 2021 sheet: $2,931 / $1,465, affiliates $4,396 / $2,198); technician $71/h; test vehicle $537/day; driver $71/h.
- Cost evidence: The only itemised proving-ground price list found: roughly $3-4.5k per track-day before staff, targets and vehicle.
- Validity evidence: none stated

### mcity2024digitaltwin: Mcity open-source digital twin and TeraSim (2024)
- Org: University of Michigan Mcity
- URL: https://www.therobotreport.com/mcity-open-source-digital-twin-enables-cheaper-av-testing/
- Kind: tooling; ladder level: 5; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Digital twin of the physical Mcity track exchanging data with the facility; TeraSim traffic simulator injects pedestrians, cyclists and safety-critical events; remote testing over 5G.
- Measures: Enables millions of simulated miles in a twin of a real track before physical runs.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: $5.1M NSF grant (2022) built the digital infrastructure; claimed 'faster, safer, and less expensive' than physical testing, no numbers.
- Validity evidence: none stated

### son2022pgvil: Proving-ground-based Vehicle-in-the-Loop simulation with consistency validation (2022)
- Org: Kookmin University / Hyundai (Korea)
- URL: https://api.crossref.org/works/10.3390/electronics11244073
- Kind: tooling; ladder level: 6; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Real vehicle drives on a proving ground while virtual roads, traffic and sensor models are injected into its perception; virtual-world and real-vehicle states synchronised; consistency checked against real-vehicle tests across speeds, road types and environments.
- Measures: Whether VIL reproduces real-test vehicle behaviour (longitudinal KPIs) closely enough to substitute for physical scenario reproduction.
- Size: not stated
- Reported metrics: Search snippet: NRMSE of longitudinal KPIs within about 4% on average and Pearson correlation close to 1 versus vehicle tests; relative-speed error <2.5% (not confirmed in the fetched abstract).
- Cost evidence: Motivation: physical scenarios lack reproducibility; VIL removes target hardware.
- Validity evidence: One of the few VIL papers reporting a quantitative VIL-vs-real consistency check.
- Notes: MDPI page returned 403; verified via Crossref record with abstract.

### zhang2025combined: Combined virtual-real (digital twin) AEB testing: field experiments (2025)
- Org: Chang'an University
- URL: https://api.crossref.org/works/10.1016/j.commtr.2025.100216
- Kind: study; ladder level: 6; safety focus: yes; confidence: low; URL verified: yes
- Modality: Ego vehicle with onboard sensors plus injected virtual sensors perceives virtual target vehicles in a digital twin of the proving ground and performs AEB; compared with conventional physical-target proving-ground tests.
- Measures: Efficiency, cost and scenario-coverage gains of virtual-real AEB testing versus proving-ground testing.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: Paper's premise is proving-ground inefficiency and cost; quantitative results not retrieved.
- Validity evidence: Claims agreement with physical tests (search snippet); not verifiable from the fetched metadata.
- Notes: Only Crossref metadata fetched (no abstract); ScienceDirect returned 403.

### cui2025vpautotest: VP-AutoTest virtual-physical fusion testing platform (2025)
- Org: Tongji University
- URL: https://arxiv.org/abs/2512.07507 (arXiv 2512.07507)
- Kind: tooling; ladder level: 6; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Mixed real and virtual vehicles, pedestrians and roadside units on a test field; adversarial scenario generation, multi-vehicle and V2X testing; multidimensional evaluation with AI-driven expert scoring; credibility validated by comparing fusion-test outcomes with real-world results.
- Measures: ADS performance in interactive scenarios that are unsafe or infeasible to stage purely physically.
- Size: Over ten types of virtual and physical elements
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Credibility validation against real-world results claimed, no numbers in abstract.

### wu2026fromcode: From Code to Road: VIL and digital-twin framework for central car server testing (2026)
- Org: TU Munich / industry partners
- URL: https://arxiv.org/abs/2603.05279 (arXiv 2603.05279)
- Kind: tooling; ladder level: 6; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Physical test vehicle on a dynamometer coupled to a synchronised virtual twin; full AD software runs on the vehicle's own compute after simulation, no flashing or intermediate layers.
- Measures: Safe, reproducible, realistic end-to-end validation of centralised vehicle software before road tests.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: Described as cost-effective and reducing need for full hardware integration early; no numbers.
- Validity evidence: none stated

### kaiser2025coupled: Coupled cyclist-in-the-loop and vehicle-in-the-loop test environment (2025)
- Org: TU Berlin
- URL: https://arxiv.org/abs/2507.21859 (arXiv 2507.21859)
- Kind: tooling; ladder level: 6; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Real cyclist on a bike simulator and real automated vehicle on a VIL bench share an Unreal Engine 5 virtual world; vehicle camera sees the rendered cyclist gestures; validated by comparing vehicle trajectories in three manoeuvres (straight stop, circle, double lane change) on the proving ground vs the coupled environment, plus component latencies.
- Measures: AV-cyclist interaction behaviour without exposing a human to a moving vehicle.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Proving-ground vs virtual trajectory comparison performed; numbers not in abstract.

### novickineto2023twice: TWICE dataset: digital twin of test-track scenarios in a HIL lab (2023)
- Org: TH Ingolstadt (CARISSMA)
- URL: https://arxiv.org/abs/2310.03895 (arXiv 2310.03895)
- Kind: dataset; ladder level: 6; safety focus: yes; confidence: high; URL verified: yes
- Modality: Camera, radar, lidar, IMU, GPS recordings of Euro NCAP-inspired scenarios (cars, cyclists, trucks, pedestrians) on a real test track in rain, night and snow, each reproduced as a digital twin in a hardware-in-the-loop lab so real and simulated sensor streams can be compared.
- Measures: Sensor-level sim-to-real gap for the same scenario executed physically and in HIL.
- Size: Over 2 hours, more than 280 GB
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Purpose-built for sim-to-real gap studies; the paper does not itself report gap statistics.

### izquierdo2022testing: Testing predictive ADS on proving grounds: lessons learned (BRAVE) (2022)
- Org: University of Alcala
- URL: https://arxiv.org/abs/2205.10115 (arXiv 2205.10115)
- Kind: position; ladder level: 8; safety focus: yes; confidence: high; URL verified: yes
- Modality: Physical proving-ground tests of predictive (intention/motion anticipation) automated driving functions from the BRAVE project; qualitative lessons.
- Measures: Whether classical certification-style track tests can evaluate predictive behaviour in critical and edge cases.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Conclusion: track-based certification 'do[es] not allow to evaluate safety with real behaviors for critical and edge cases'.

### dauner2023parting: Parting with Misconceptions (nuPlan open-loop vs closed-loop) (2023)
- Org: University of Tuebingen / Bosch
- URL: https://arxiv.org/abs/2306.07962 (arXiv 2306.07962)
- Kind: benchmark; ladder level: 5; safety focus: yes; confidence: high; URL verified: yes
- Modality: Planners fed nuPlan real-log scenes; scored by open-loop displacement error (OLS) and closed-loop scores with non-reactive and reactive agents (CLS-NR, CLS-R) measuring collisions, drivable area, progress, comfort.
- Measures: Alignment between ego-forecasting accuracy and closed-loop driving safety.
- Size: not stated
- Reported metrics: Open-loop and closed-loop objectives are misaligned; a centerline-only rule-based planner (PDM-Closed) won the 2023 nuPlan challenge, beating learned planners in closed loop.
- Cost evidence: Rule-based planner is cheap to run; no explicit numbers.
- Validity evidence: Level-3-style open-loop scores do not predict level-4/5 closed-loop outcomes; canonical negative validity result.

### dauner2024navsim: NAVSIM: data-driven non-reactive simulation and benchmarking (2024)
- Org: Tuebingen / NVIDIA / OpenDriveLab / Stanford
- URL: https://arxiv.org/abs/2406.15349 (arXiv 2406.15349)
- Kind: benchmark; ladder level: 5; safety focus: yes; confidence: high; URL verified: yes
- Modality: Sensor-input planners output a short trajectory on real OpenScene/nuPlan scenes; scored non-reactively with simulation-based sub-metrics (no-collision, drivable area, ego progress, TTC, comfort) aggregated into the PDM Score, avoiding full closed-loop rollout.
- Measures: Planner quality with metrics 'better aligned with closed-loop evaluations than traditional displacement errors'.
- Size: CVPR 2024 challenge: 143 teams, 463 entries
- Reported metrics: none stated
- Cost evidence: Non-reactive scoring is far cheaper than closed-loop; the follow-up pseudo-simulation paper reports about 6x less compute than closed-loop (search snippet).
- Validity evidence: See wang2026openloop for the cross-benchmark correlation (Spearman 0.90 with Bench2Drive closed-loop).
- Speaker link: Pavone
- Notes: Open-loop scoring on real scenes; ladder placement 5 with an open-loop caveat.

### wang2026openloop: Do open-loop metrics predict closed-loop driving? NAVSIM vs Bench2Drive (2026)
- Org: Multiple (Wang et al.)
- URL: https://arxiv.org/abs/2605.00066 (arXiv 2605.00066)
- Kind: study; ladder level: 4; safety focus: yes; confidence: high; URL verified: yes
- Modality: Cross-benchmark rank correlation of published NAVSIM PDMS sub-scores against Bench2Drive closed-loop Driving Score for the same end-to-end planners.
- Measures: Predictive validity of an open-loop safety score for closed-loop outcomes.
- Size: 15 methods evaluated, 8 with complete paired data
- Reported metrics: Spearman rho = 0.90 (PDMS vs Driving Score) but non-monotonic; Ego Progress rho = 0.83 is the best single predictor; No-Collision rho = 0.45; a 3-metric formula matches the 5-metric PDMS; over-cautious planners score high open-loop but underperform closed-loop.
- Cost evidence: none stated
- Validity evidence: The clearest quantitative validity estimate found for a cheap driving evaluation predicting a more expensive one; note the collision sub-metric is the weakest predictor.

### ljungbergh2024neuroncap: NeuroNCAP: photorealistic closed-loop safety testing (2024)
- Org: Zenseact / Linkoping / TU Delft / Lund
- URL: https://arxiv.org/abs/2404.07762 (arXiv 2404.07762)
- Kind: benchmark; ladder level: 5; safety focus: yes; confidence: high; URL verified: yes
- Modality: NeRF reconstruction of real nuScenes logs re-rendered with inserted safety-critical actors (stationary, frontal, side); end-to-end camera planners driven closed-loop; Euro NCAP-inspired 0-5 score from collision avoidance and impact-speed reduction.
- Measures: Collision avoidance of end-to-end planners in NCAP-style critical scenarios with realistic sensor input.
- Size: not stated
- Reported metrics: State-of-the-art end-to-end planners that excel open-loop show critical flaws in closed-loop critical scenarios.
- Cost evidence: none stated
- Validity evidence: Same open-loop vs closed-loop divergence as dauner2023parting, now with photoreal rendering; no real-vehicle check.

### li2024rigorous: Rigorous simulation-based testing of four open autopilots (2024)
- Org: Chinese Academy of Sciences / Verimag
- URL: https://arxiv.org/abs/2405.16914 (arXiv 2405.16914)
- Kind: red-team; ladder level: 4; safety focus: yes; confidence: high; URL verified: yes
- Modality: Autopilots (Apollo, Autoware, CARLA and LGSVL agents) modelled as dynamic systems; scenarios decomposed into simple ones with critical configurations; run in simulation and checked for accidents, software failures and traffic-rule violations.
- Measures: Defects missed by random simulation testing.
- Size: not stated
- Reported metrics: Major defects found in all four stacks; authors conclude ADS 'still have a long way to go before offering acceptable safety guarantees'.
- Cost evidence: none stated
- Validity evidence: none stated (simulation only).

### montali2023wosac: Waymo Open Sim Agents Challenge (WOSAC) (2023)
- Org: Waymo
- URL: https://arxiv.org/abs/2305.12032 (arXiv 2305.12032)
- Kind: tooling; ladder level: 5; safety focus: yes; confidence: high; URL verified: yes
- Modality: Sim agents roll out multi-agent futures on Waymo Open Motion scenes; realism scored against logged behaviour with distributional metrics.
- Measures: Realism of reactive agents used inside closed-loop simulators.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Metrics quantify sim-agent realism vs logs, which conditions the validity of any level-5 closed-loop score.

### dyro2024realistic: Realistic extreme behavior generation for AV testing (2024)
- Org: Stanford ASL / Swiss Re
- URL: https://arxiv.org/abs/2409.10669 (arXiv 2409.10669)
- Kind: red-team; ladder level: 3; safety focus: yes; confidence: high; URL verified: yes
- Modality: Counterfactual collisions generated by perturbing an adversary's predicted trajectory within the data-aligned parameter space of two learned behaviour-prediction models; synthetic scenarios clustered into representative collision cases and run against a baseline AV policy.
- Measures: Interpretable failure modes of an AV collision-avoidance policy under realistic (not arbitrary) adversarial behaviour.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Realism argued via alignment to learned behaviour-model parameters; no field validation.
- Speaker link: Pavone

### favaro2018disengagements: AV disengagements: trends, triggers and regulatory limitations (2018)
- Org: San Jose State University
- URL: https://www.sciencedirect.com/science/article/abs/pii/S0001457517303822
- Kind: study; ladder level: 9; safety focus: yes; confidence: medium; URL verified: no
- Modality: Analysis of California DMV disengagement reports 2014-2017: frequencies, miles per disengagement, triggers and contributory factors.
- Measures: Reliability trends of supervised AV testing and the limits of disengagement reporting as a safety metric.
- Size: not stated
- Reported metrics: Environmental contributors about 10.8% of disengagements (poor lane markings 4.63%, construction 2.20%, pedestrians 2.03%, weather 0.69%) from search summary.
- Cost evidence: none stated
- Validity evidence: Documents inconsistent reporting across manufacturers, undermining disengagements as a comparable safety proxy.
- Notes: ScienceDirect returned 403; not fetched. Included because it is the standard citation on disengagement-report validity.

### zhang2021disengagement: Disengagement cause-and-effect extraction with an NLP pipeline (2021)
- Org: University of Michigan-Dearborn
- URL: https://arxiv.org/abs/2111.03511 (arXiv 2111.03511)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: NLP and transfer learning over 2014-2020 California DMV disengagement reports.
- Measures: Who initiates disengagements and which subsystem causes them.
- Size: not stated
- Reported metrics: Test drivers initiated >80% of disengagements; >75% attributed to perception, localisation/mapping, planning and control errors.
- Cost evidence: none stated
- Validity evidence: Human-initiated disengagements dominate, so the metric measures driver judgement as much as system failure.

### fu2024insufficiencies: Characterization and mitigation of functional insufficiencies in ADS (2024)
- Org: TU Eindhoven / NXP / TNO
- URL: https://arxiv.org/abs/2404.09557 (arXiv 2404.09557)
- Kind: study; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Categorisation of 2021 California DMV disengagements and 10+ hours of road-test video into functional insufficiencies (world model, motion planning, traffic rules, ODD) vs system faults; proposes the Daruma multi-channel architecture.
- Measures: Share of field disengagements due to SOTIF-type insufficiencies vs ISO 26262-type faults.
- Size: not stated
- Reported metrics: Disengagements are five times more often caused by functional insufficiencies than by system faults.
- Cost evidence: none stated
- Validity evidence: Field evidence that SOTIF-style (level 3-5 scenario) testing targets the dominant failure class.

### iso2025iso10218: ISO 10218-1/-2:2025 industrial robot safety (absorbs ISO/TS 15066) (2025)
- Org: ISO/TC 299
- URL: https://www.therobotreport.com/iso-10218-industrial-robot-safety-standard-receives-major-overhaul/
- Kind: standard; ladder level: 7; safety focus: yes; confidence: high; URL verified: yes
- Modality: Design and integration requirements; collaborative-application requirements (power and force limiting, speed and separation monitoring) moved in from ISO/TS 15066; two robot classes; explicit functional-safety and cybersecurity clauses; validation by measurement of contact force/pressure against body-region limits.
- Measures: Conformity of an industrial robot and its application; for PFL, measured transient and quasi-static contact forces and pressures versus biomechanical limits.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: Standard costs $244 (A3 store); revision took about 8 years with experts from 20+ countries; no test-cost data.
- Validity evidence: See svarny2020collisionforcemap and kirschner2022iso15066 for evidence that the limit formulas and definitions give inconsistent verdicts.
- Notes: iso.org returned 403; verified via The Robot Report (Feb 2025) and hartmann2026evolution.

### hartmann2026evolution: Evolution of ISO 10218 (2011 vs 2025) and integration of ISO/TS 15066 (2026)
- Org: VSB Technical University of Ostrava
- URL: https://arxiv.org/abs/2602.17822 (arXiv 2602.17822)
- Kind: study; ladder level: n/a; safety focus: yes; confidence: high; URL verified: yes
- Modality: Comparative document analysis of the two editions: structural, functional-safety, cybersecurity and collaborative-application changes.
- Measures: What the 2025 revision changes for robot safety verification.
- Size: not stated
- Reported metrics: ISO/TS 15066 content elevated from optional guidance to normative requirement.
- Cost evidence: none stated
- Validity evidence: none stated

### hartmann2026biofidelic: Systematic review of biofidelic instrumentation for PFL cobot testing (2026)
- Org: VSB Technical University of Ostrava
- URL: https://api.crossref.org/works?query.title=Design+Validation+and+Metrological+Limits+of+Biofidelic+Instrumentation+in+PFL+Collaborative+Robotics+Systematic+Review&rows=2&select=DOI,title,author,container-title,published,abstract
- Kind: study; ladder level: 7; safety focus: yes; confidence: high; URL verified: yes
- Modality: Systematic review (2011-2026) of pressure and force measurement devices and biofidelic instruments used to certify power-and-force-limited collaborative applications.
- Measures: Metrological limits and trends of the instruments that produce the pass/fail numbers for ISO/TS 15066 and ISO 10218:2025.
- Size: 68 studies
- Reported metrics: Publication peak in impact metrology in 2021, five years after ISO/TS 15066; sensor limitations include nonlinear shock filtering and pressure spikes from rigid test configurations.
- Cost evidence: none stated
- Validity evidence: Documents instrument-induced variability in the certification measurement itself.
- Notes: MDPI page returned 403; verified via Crossref record with abstract.

### kirschner2022iso15066: ISO/TS 15066: how different interpretations affect risk assessment (2022)
- Org: TU Munich (MIRMI, Haddadin)
- URL: https://arxiv.org/abs/2203.02706 (arXiv 2203.02706)
- Kind: study; ladder level: 7; safety focus: yes; confidence: high; URL verified: yes
- Modality: Collision tests on four commercial robot systems interpreted under the conflicting contact-classification definitions of ISO/TS 15066; proposes a decision tree and constrained collision-force maps.
- Measures: Whether the standard yields a unique safe/unsafe verdict for the same measured contact.
- Size: Four commercial robots
- Reported metrics: Logically conflicting definitions mean 'no unique outcome can be expected' from a risk assessment.
- Cost evidence: none stated
- Validity evidence: Evidence of assessor-dependent verdicts (a reliability problem) in a level-7 certification test.

### svarny2020collisionforcemap: 3D collision-force map for safe human-robot collaboration (2020)
- Org: Czech Technical University (Hoffmann)
- URL: https://arxiv.org/abs/2009.01036 (arXiv 2009.01036)
- Kind: study; ladder level: 7; safety focus: yes; confidence: high; URL verified: yes
- Modality: UR10e and KUKA LBR iiwa driven into an impact measuring device at many workspace positions and speeds; measured impact force compared with the ISO/TS 15066 mass-velocity-force formula.
- Measures: Spatial variation of impact force and accuracy of the standard's predictive formula.
- Size: not stated
- Reported metrics: Impact forces vary by more than 100% within the workspace; the ISO/TS 15066 formula both significantly underestimates and overestimates safe speeds; clamping never occurred with the UR10e.
- Cost evidence: none stated
- Validity evidence: The analytical (level-0-like) limit computation is a poor predictor of measured force: both false alarms and misses.

### svarny2022skins: Effect of protective soft skins on collision forces (2,250 measurements) (2022)
- Org: Czech Technical University / Blue Danube Robotics
- URL: https://arxiv.org/abs/2203.09872 (arXiv 2203.09872)
- Kind: study; ladder level: 7; safety focus: yes; confidence: high; URL verified: yes
- Modality: UR10e, KUKA LBR iiwa and KUKA Cybertech with and without AIRSKIN active/passive skin collide with a force measurement device; force evolution recorded across impact direction, velocity, stop settings and reaction strategy.
- Measures: Transient collision force reduction from passive padding and active skin stops, relative to ISO/TS 15066 limits.
- Size: 2,250 collision measurements, three manipulators
- Reported metrics: Passive skin lowers impact forces by about 40%; up to four times the ISO/TS 15066 prescribed velocity can still comply with force limits in some configurations.
- Cost evidence: Trial count (2,250) is the best proxy for the hardware cost of a thorough PFL characterisation.
- Validity evidence: Shows the standard's velocity limits are conservative by up to 4x for padded robots, i.e. a high false-alarm rate of the analytic rule.

### salvini2021safety: On the safety of mobile robots in public spaces: gaps in EN ISO 13482 (2021)
- Org: EPFL LASA
- URL: https://api.crossref.org/works?query.title=On+the+Safety+of+Mobile+Robots+Serving+in+Public+Spaces&rows=2&select=DOI,title,author,container-title,published,abstract
- Kind: position; ladder level: 9; safety focus: yes; confidence: high; URL verified: yes
- Modality: Standards gap analysis for personal-care/service robots deployed among pedestrians: crowds, social norms and proxemics, and people's misbehaviour are not covered by ISO 13482:2014 certification.
- Measures: Adequacy of the ISO 13482 certification regime for public-space deployment.
- Size: not stated
- Reported metrics: none stated
- Cost evidence: none stated
- Validity evidence: Argues certification tests do not cover the hazards that dominate in public deployment; calls for a new standard.
- Notes: ACM page returned 403; verified via Crossref record with abstract. ISO 13482:2014 and ISO/TR 23482-1:2020 (test methods) could not be fetched from iso.org.

### obi2026safegate: SafeGate: ISO 13482-grounded pre-execution safety gate for LLM-controlled robots (2026)
- Org: Purdue University (SMART Lab)
- URL: https://arxiv.org/abs/2604.05427 (arXiv 2604.05427)
- Kind: benchmark; ladder level: 0; safety focus: yes; confidence: medium; URL verified: yes
- Modality: Natural-language commands to an LLM robot controller are parsed into ISO 13482-derived safety properties and passed through a deterministic accept/reject gate plus task safety contracts (invariants, guards, aborts); scored by acceptance of defective vs benign commands on a text benchmark, in AI2-THOR, and on a real robot.
- Measures: Rejection rate of unsafe commands and acceptance rate of benign ones before any physical execution.
- Size: 230 benchmark tasks, 30 AI2-THOR scenarios, real-robot experiments
- Reported metrics: Significantly reduced acceptance of defective commands while keeping high acceptance of benign tasks (numbers not in abstract).
- Cost evidence: none stated
- Validity evidence: Text-level gate checked on simulation and hardware, but no agreement statistics reported in abstract.
- Notes: Spans levels 0, 4 and 7; primary scoring is text-level, hence level 0. Links the physical-safety standard to the LLM-planner end of the ladder.
