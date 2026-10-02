# Vikas Sindhwani (Google DeepMind): safety-evaluation literature

## Assessment

- Evaluation is central to Sindhwani's 2025-2026 work. He is last author on the ASIMOV benchmark line (v1 constitutions, v2 physical danger, Agentic in the Gemini Robotics 2 safety report) and on Predictive Red Teaming, and a listed author on the Veo world-simulator evaluation study and both Gemini Robotics tech reports.
- His group's evals sit at two levels: offline semantic-safety benchmarks scored by human labels (ASIMOV v1/v2, SciFi-Benchmark), and prediction-of-real-performance studies validated with hardware trials (Predictive Red Teaming: 500+ trials, Spearman 0.8; Veo simulator: 1600+ trials, MMRV 0.06).
- Before 2025 his safety work is control theory (stability certificates, safe learning of dynamics) plus one real-fleet runtime-monitoring paper (drone anomaly detection, 2020). None of those define reusable safety evals except the drone paper.
- For a paper on value of information (VOI) of robot safety evaluations, cite: (1) Predictive Red Teaming as the cleanest example of a cheap proxy eval whose predictive validity vs hardware is quantified; (2) the Veo world-simulator study for sim-vs-real rank agreement; (3) ASIMOV-2.0 for the human-labelling cost model (5 raters per item, consensus filtering) and for the text-vs-video capability gap; (4) ASIMOV-Agentic for the explicit FNR/FPR trade-off in human-proximity stopping and the 99%/96% humanoid lab numbers.
- Gaps to exploit: none of the offline benchmarks report correlation with deployed-robot incidents; ART red-teaming numbers are withheld; no cost (hours, dollars, compute) is quantified anywhere.
- Sim2real scale used below: 0 = text thought experiments, 3 = generated images/video, 6 = proxy eval validated against hardware, 9 = real deployment data.

## Entries (11, all URLs fetched)

| key | year | kind | s2r | one line |
|---|---|---|---|---|
| sermanet2025asimov | 2025 | benchmark | 2 | ASIMOV v1: image/text action desirability vs human votes; 84.3% top alignment with generated constitutions. CoRL 2025. |
| jindal2025danger | 2025 | benchmark | 3 | ASIMOV-2.0: 319 text, 287 video, 164 constraint items from NEISS injuries; 27-40% video-vs-text gap; violation rates 38.6-75%. |
| sermanet2025scifi | 2025 | benchmark | 0 | SciFi-Benchmark: 9,056 questions from 824 works; constitutions lift alignment 79.4% to 95.8%. Text only. |
| majumdar2025predictive | 2025 | red-team | 6 | Predictive Red Teaming: Imagen-edited observations + embedding anomaly detector predict real success; 500+ hardware trials, Spearman 0.8, gap < 0.19. CoRL 2025. |
| geminirobotics2025veo | 2025 | study | 6 | Veo world simulator as policy evaluator; 8 checkpoints, 5 tasks, 1600+ real episodes; MMRV 0.06; safety failures reproduced on robot. |
| geminirobotics2026agentic | 2026 | benchmark | 4 | ASIMOV-Agentic (GR2 safety report, July 2026): refusal, human-proximity stop, feasibility, ambiguity; FPR<5% costs FNR>40%; humanoid 99%/96%. |
| geminirobotics2025report | 2025 | study | 3 | Gemini Robotics tech report safety section; 96% vs 20% rejection of bias-inducing pointing. |
| geminirobotics2025report15 | 2025 | red-team | 4 | Gemini Robotics 1.5: Auto-Red-Teaming attacker/target/autorater protocol; ASIMOV-2.0 results qualitative only. |
| sindhwani2020anomaly | 2020 | study | 9 | Drone fleet anomaly detection on 5,000 real missions, 100M+ measurements. Adjacent. |
| varley2024twoarms | 2024 | study | 8 | Bimanual system with compliant control near humans; IROS 2024 safety-paper nomination; not a reusable eval. Adjacent. |
| caluwaerts2023barkour | 2023 | benchmark | 9 | Barkour physical agility course; not safety; evidence of hardware-benchmark design. |

## Excluded after checking

- Safely Learning Dynamical Systems (2020, 2023/24 FoCM), Learning Stability Certificates from Data (CoRL 2020), Teleoperator Imitation with Continuous-time Safety (RSS 2019): theory or method papers, no reusable evaluation protocol.
- Gemini 2.5 tech report: no robot safety evaluation.
- Rethinking Safety for Generalist Robots (Sinha, Dixit, Tian, Majumdar, Bajcsy, Sept 2026): position paper, Sindhwani not an author; relevant to the Bajcsy sweep.
- Robots That Ask For Help (KnowNo, 2023): Sindhwani not an author.

## Sources verified

- Speaker pages: https://vikas.sindhwani.org/safety.html and https://vikas.sindhwani.org/publications.html
- arXiv author query au:Sindhwani (66 entries), Semantic Scholar author 1808676 (168 papers)
- Project pages: asimov-benchmark.github.io/v1, /v2, predictive-red-team.github.io, scifi-benchmark.github.io, huggingface.co/datasets/google/asimov_agentic
- DeepMind: responsibly-advancing-ai-and-robotics page, Gemini Robotics 2 blog (30 July 2026), Gemini-Robotics-2-Safety.pdf (29 July 2026)
- SPAIS site confirms Sindhwani as invited speaker.
