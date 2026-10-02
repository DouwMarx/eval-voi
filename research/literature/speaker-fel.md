# Thomas Fel (Goodfire, Harvard Kempner) - literature sweep for SPAIS 2026

## Assessment

- Evaluation of robots, AVs or embodied systems is absent from Fel's record. Full arXiv author listing (54 entries, 2020-2026), Semantic Scholar (40 papers), Goodfire research page and the SPAIS speaker page were checked. Zero papers define or run a safety evaluation of a robot, vehicle or embodied agent.
- His work is vision-model interpretability: attribution methods (Sobol, HSIC, EVA), concept extraction (CRAFT, Holistic/Lens), sparse autoencoders (Archetypal SAE, MP-SAE, block-sparse featurizers), human-alignment of vision models (Harmonizer), and neural geometry.
- Evaluation appears in two secondary strands: (1) meta-evaluation of interpretability tools, including large human psychophysics studies (n=1150, n=481) and metric-validity critiques; (2) one DEEL/SNCF study on conformal risk control for railway signal detection, the only safety-critical perception evaluation with Fel as coauthor.
- Goodfire-era work adds one safety-monitoring paper (reward hacking monitors during LLM evals, Fel 15th of 18 authors) and one world-model physics probe study. Neither is embodied.
- Expect his SPAIS talk to be about SAEs / concept geometry for vision and VLA-style models, not about evaluation protocols.
- For a VOI-of-robot-safety-evals paper, cite: colin2021what (proxy metrics carry little or no information about the target quantity; human labelling cost), picard2025baseline (benchmark design choices flip rankings), andeol2023confident (cost of a real-data guaranteed-coverage eval: 3.4k hand-labelled frames, alpha=0.1), and biecek2026model (position against benchmark-only evaluation). bergen2026monitoring is the natural link between his interpretability line and runtime monitoring.
- Do not cite Fel for benchmarks, red-teaming or sim2real work; there are none.

## Entries (13, all URLs fetched)

| key | year | kind | safety | one line |
|---|---|---|---|---|
| andeol2023confident | 2023 | study | yes | Conformal prediction / risk control for railway signal detection on a new 3414-image SNCF-view dataset; alpha=0.1; metrics: coverage and box stretch. Companion: AI and Ethics 4:157-161, arXiv:2301.11136. |
| colin2021what | 2022 | benchmark | no | Human-centered Utility benchmark for attribution methods, n=1150 AMT; faithfulness metrics do not predict human usefulness. |
| fel2020how | 2022 | study | no | MeGe / ReCo algorithmic-stability metrics for explanations; 1-Lipschitz nets score better. |
| fel2022xplique | 2022 | tooling | no | Xplique toolbox: 26 attribution methods, 15 evaluation metrics; built in DEEL certifiable-AI program. |
| picard2025baseline | 2025 | study | no | Baseline choice in Insertion/Deletion metrics changes which attribution method wins. |
| fel2023holistic | 2023 | study | no | Unified concept-extraction framework with new evaluation metrics (NeurIPS 2023). |
| fel2025archetypal | 2025 | benchmark | no | Archetypal SAE plus plausibility and identifiability benchmarks for SAE dictionaries (ICML 2025). |
| costa2025evaluating | 2025 | study | no | Controlled MNIST-scale evaluation showing shallow SAEs miss correlated features; MP-SAE. |
| colin2024choosing | 2024 | study | no | 481-participant psychophysics: dictionary bases more interpretable than neurons. |
| bergen2026monitoring | 2026 | study | yes | Difference-of-means activation monitors for reward hacking in LLM evals; hack rates 57-73% on coding benchmarks. |
| joseph2026interpreting | 2026 | study | no | Physics Emergence Zone in video world-model encoders; probe study. |
| biecek2026model | 2026 | position | no | Model Science: Verify / Explore / Steer / Refine, beyond benchmarking. |
| bohacek2025blindspots | 2025 | study | no | 32k-concept SAE audit of conceptual blindspots in 4 text-to-image models. |

## Considered and excluded (verified, not evaluation work)

- Don't Lie to Me / EVA (CVPR 2023, arXiv:2202.07728): attribution method with verified-perturbation guarantee; a method, not an evaluation protocol.
- Adversarial alignment (arXiv:2306.03229): robustness vs human-alignment trade-off; not an eval of an embodied system.
- SparKer anomaly detection (arXiv:2511.03095): open-world novelty detection across scientific domains; no robot or monitoring benchmark.
- DEEL White Paper on ML in Certified Systems (arXiv:2103.10529): Fel is not an author.
- Assessing Trustworthiness of Autonomous Systems (arXiv:2305.03411): Fel is not an author.
- Interpreto library (arXiv:2512.09730): surfaced by search; Fel not in the arXiv author listing.

## Sources checked

- arXiv API au:Fel_Thomas (54 results, two pages fetched)
- Semantic Scholar author 1935310411 (40 papers)
- https://www.goodfire.com/research (Fel on one post: block-sparse featurizers)
- https://spais-ws.org/ (speaker list; no talk titles)
- https://github.com/deel-ai/xplique
- https://proceedings.mlr.press/v204/andeol23a.html and the PMLR PDF (dataset table, splits, alpha)
- arXiv abstract pages for every entry above
- thomasfel.me and thomasfel.me/publications returned empty / 404
