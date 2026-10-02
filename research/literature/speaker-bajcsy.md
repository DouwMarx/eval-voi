# Andrea Bajcsy (CMU IntentLab): safety-evaluation literature sweep

## Assessment

- Evaluation is a secondary but growing thread in Bajcsy's work. The core is safety synthesis (HJ reachability, latent safety filters, conformal calibration, policy steering), and most papers use evaluation as a means.
- No standalone robot-safety benchmark or red-teaming suite comes from the group as of Sept 2026. Do not cite her as a benchmark author.
- Three items are genuinely about evaluation and should be cited by a value-of-information paper: StressDream (2026, world-model stress testing as a cheap proxy for real safety testing, with Pavone), Not All Errors Are Made Equal (2024, a calibrated metric that decides which predictor errors matter for closed-loop safety and shows 23% of data carries the signal), and Good Embodied Reward Models Need Bad Behavior Data (ICML 2026, audit of learned evaluators against human labels on 723 RoboArena tasks).
- Rethinking Safety for Generalist Robots (Sept 2026, with Sinha/Dixit/Majumdar) is the quotable position: real-world safety testing is "unsafe by definition, time-consuming, and costly", so safety cases must mix offline tests with limited rigorous hardware trials. This is the closest statement of the workshop paper's premise from the speaker herself.
- Supporting items with reusable protocols: MultiSafe diagnostics (offline test of whether a sensing suite can observe/predict a safety constraint), UNISafe and SALT (monitor-as-classifier TPR/TNR protocols), the confidence-aware BRT evaluated on 200 INTERACTION-dataset pairs (conservatism vs real human margins), and the AV safety-concepts paper with Pavone (safety-critical dataset construction under a labelling budget).
- Validity evidence is thin across the board: hardware trials are 20-100 per condition, and only the regret paper links an offline metric to re-deployment outcomes. Cost is rarely quantified (exceptions: ReGuard GPU hours, Do What You Say training/inference cost, StressDream minutes-per-imagination).
- Two speaker links cross: StressDream and the AV safety-concepts paper are co-authored with Marco Pavone.

## Entries (17, all URLs fetched)

| key | year | kind | name | core numbers |
|---|---|---|---|---|
| seo2026stressdream | 2026 | tooling | StressDream: steered video world models for policy evaluation | failure recall 54% to 94%; VLA success 39% to 71% after robust fine-tuning; no real-robot validation |
| nakamura2024regret | 2024 | study | Regret metric for system-level prediction failures | 96 sim scenarios + LoCoBot; 23% high-regret data matches full fine-tuning; -65% collision cost |
| kim2025multisafe | 2025 | study | MultiSafe: observability/predictability diagnostics for latent WMs | Franka RS3; RGB-only 15% vs multimodal 100% safe lifts (20 trials); MI diagnostics predict this |
| tian2026badbehavior | 2026 | position | Reward models need bad behavior data (RoboArena audit) | 723 tasks; preference accuracy 0.72-0.77 easy, 0.52-0.62 tool use; +10% with bad data in-context |
| sinha2026rethinking | 2026 | position | Rethinking Safety for Generalist Robots | taxonomy + agenda; calls for severity-stratified offline metrics, continuous eval, robotics red-teaming |
| wu2025dowhatyousay | 2025 | benchmark | LIBERO-100-R / LIBERO-10-R OOD suite | 4 perturbation types, 50 trials/task; 20 h on 8 A100; released on GitHub/HF |
| jeong2026languagepolicy | 2026 | study | Conformalized language steering, LIBERO-OOD harm-rate protocol | 200 combos x 50 rollouts; harmful-intervention FPR 61% to 2% on hardware |
| seo2025unisafe | 2025 | study | UNISafe OOD-failure evaluation of latent safety filters | 1000 IsaacLab initial conditions; 50 hardware failure replays; safe-success 0.72 vs 0.58 unfiltered |
| jeong2025salt | 2025 | study | SALT monitor-as-classifier evaluation + 20-person study | TPR 37% vs ensemble 2%; 70-100% human alignment on alternatives |
| leung2021safetyconcepts | 2021 | position | HJ unification of AV safety concepts (with Pavone) | no numbers; safety-critical dataset construction under labelling budget |
| tian2022confidence | 2022 | study | Confidence-aware BRT monitor on INTERACTION data | 200 real pairs; ~20% fewer interventions; +27.75% reward vs full BRT |
| bajcsy2021analyzing | 2021 | tooling | Reachability analysis of online-adapting human models | 4 sim domains; best/worst-case learning times; low-dim only |
| bajcsy2024humanai | 2024 | position | Human-AI Safety (control-systems view) | framing only |
| pandya2025reguard | 2025 | study | ReGuard guardrails vs refusal (LLM agents, sim) | 77.3% vs 44.4% success; 66-150 GPU hours training per domain |
| lekeufack2024conformal | 2024 | study | Conformal Decision Theory on Stanford Drone Dataset | 0 violations at 2 m; 29% faster than ACI; single scene |
| bansal2020hjhuman | 2020 | study | HJ analysis of prior misspecification in human prediction | qualitative; sim + quadrotor |
| nakamura2025latentsafety | 2025 | study | Latent Safety Filters (RSS 2025) hardware protocol | context only |

## Excluded after reading abstracts (method papers without a reusable evaluation protocol)

AnySafe (2509.19555), LatentCBF (2511.18606), FOREWARN (2502.01828), UPS (2602.22474), ELASTIC (2606.31132), ViTaL (2606.14981), WEAVER (2606.13672), ReOI (2506.16565), Adapting by Analogy (2506.12678), Conformalized Interactive IL (2410.08852), Conformalized Teleoperation (2406.07767), Deception Game (2309.01267), Safe Influence (2409.12153), Language-informed safety representations (2409.14580), ICL-BRT (2501.15618), Coordinated Diffusion (2605.11485), Agent-to-Sim (2410.16259), pre-2019 pHRI and reachability work. "On the Fine-Grained Planning Abilities of VLM Web Agents" (EMNLP Findings 2025) is a web-agent benchmark, not embodied. "What Does Safety Mean for Generalist Robots?" is a Georgia Tech seminar (Aug 2026), not a paper.

## Sources swept

CMU IntentLab publications page (60 items), arXiv API au:Bajcsy_Andrea (50 items), Semantic Scholar author 47370841 (70 items), Google Scholar profile LUe32ToAAAAJ (recent 20), plus targeted web searches. Abstracts read via arXiv API; details via arXiv HTML/PDF and project pages.
