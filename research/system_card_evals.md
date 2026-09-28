# Evaluations named in frontier system cards and third-party eval reports

Corpus: 180 documents with safety_evals=1 from 22 publishers (anthropic 47, google_deepmind 23, openai 21, uk_aisi 16, metr 12, securebio 8, redwood_research 7, meta 6, rand 6, far_ai 4, thinking_machines 4, transluce 4, xai 4, apollo_research 3, epoch_ai 3, us_caisi 3, cursor 2, palisade_research 2, saferai 2, inclusion_ai 1, nvidia 1, zai 1).

Domain document counts: cbrn 61, cyber 89, loss_of_control 82, harmful_manipulation 29, societal_harm 45.

Candidates kept: 1774. Dropped by filter: case_dominance 753, model_like 31, sku_like 15, stoplist 432.

Rank score = DF x (1 + ln n_publishers). Top domain = domain with highest smoothed lift, computed only over docs tagged with 1-3 risk domains (the comprehensive system cards are tagged with all five and carry no signal); 'unresolved' = only mentioned in such uninformative docs. For capability benchmarks the domain is incidental. Label: safety = measures a risk or alignment property; capability = general capability benchmark that is not itself a risk measure; org = evaluator, not an eval.


## Top 60 candidates

| # | name | DF | pubs | mentions | top domain (lift) | label | why |
|---|---|---|---|---|---|---|---|
| 1 | METR | 38 | 9 | 340 | loss_of_control (2.0) | org | third-party evaluator (METR), seeded per spec |
| 2 | Reward Hacking | 36 | 10 | 318 | loss_of_control (1.789) | safety | exploiting graders / environments instead of solving task |
| 3 | CTF | 33 | 12 | 297 | cyber (1.609) | safety | capture-the-flag cyber tasks used as offensive-cyber uplift measure |
| 4 | CyberGym | 33 | 11 | 173 | cyber (1.93) | safety | real-world vulnerability reproduction tasks |
| 5 | VCT | 34 | 8 | 265 | cbrn (4.071) | safety | virology troubleshooting test built for biorisk measurement |
| 6 | SWE-bench | 30 | 12 | 257 | cbrn (1.921) | capability | software engineering task benchmark |
| 7 | Sandbagging | 29 | 8 | 359 | loss_of_control (2.154) | safety | strategic under-performance on dangerous-capability evals |
| 8 | LAB-Bench | 30 | 7 | 144 | cbrn (2.972) | safety | biology lab protocol / literature tasks used as bio-uplift proxy |
| 9 | Humanity's Last Exam | 27 | 9 | 184 | loss_of_control (1.429) | capability | frontier academic knowledge exam |
| 10 | Sycophancy | 27 | 8 | 260 | harmful_manipulation (4.378) | safety | alignment property: telling users what they want to hear |
| 11 | Terminal-Bench | 27 | 8 | 130 | cyber (1.334) | capability | terminal / command-line agent task benchmark |
| 12 | GPQA | 25 | 8 | 81 | cbrn (3.063) | capability | graduate-level science QA; sometimes CBRN proxy |
| 13 | Cyber Range | 24 | 8 | 68 | cyber (2.021) | safety | multi-stage network attack simulations for cyber uplift |
| 14 | MMLU | 23 | 9 | 58 | harmful_manipulation (2.3) | capability | broad knowledge multiple choice |
| 15 | ExploitBench | 23 | 7 | 109 | cyber (2.348) | safety | CVE exploit development in browser engines (Anthropic cyber) |
| 16 | ExploitGym | 21 | 8 | 190 | cyber (2.094) | safety | real-vulnerability exploitation gym (cyber uplift) |
| 17 | ProtocolQA | 22 | 6 | 92 | cbrn (2.185) | safety | lab protocol error-correction, bio-uplift proxy |
| 18 | AIME | 20 | 7 | 42 | loss_of_control (1.417) | capability | competition maths |
| 19 | Apollo | 17 | 9 | 110 | loss_of_control (2.222) | org | third-party evaluator (Apollo Research), seeded per spec |
| 20 | GDPval | 19 | 6 | 99 | societal_harm (1.912) | capability | economically valuable professional tasks |
| 21 | SHADE-Arena | 19 | 5 | 119 | loss_of_control (1.833) | safety | hidden-sabotage agent tasks with monitor |
| 22 | Cybench | 16 | 7 | 91 | cyber (1.903) | safety | professional CTF challenges for cyber uplift |
| 23 | MASK | 18 | 5 | 125 | harmful_manipulation (3.45) | safety | honesty under pressure: stated belief vs. statement |
| 24 | OSWorld | 17 | 5 | 113 | cbrn (2.472) | capability | computer-use agent benchmark |
| 25 | WMDP | 14 | 6 | 135 | cbrn (3.19) | safety | hazardous bio/cyber/chem knowledge multiple choice |
| 26 | CVE-Bench | 14 | 6 | 58 | cyber (1.535) | safety | real CVE exploitation |
| 27 | HealthBench | 16 | 4 | 296 | societal_harm (4.406) | capability | medical conversation quality; harm-adjacent |
| 28 | Epoch Capabilities Index (ECI) | 16 | 4 | 179 | harmful_manipulation (1.533) | capability | aggregate capability index across benchmarks |
| 29 | Petri | 14 | 5 | 136 | harmful_manipulation (2.3) | safety | automated auditing agent for misaligned behaviours |
| 30 | OSS-Fuzz | 13 | 6 | 52 | cyber (2.619) | safety | vulnerability discovery in fuzzed open-source targets |
| 31 | Tacit Knowledge | 16 | 3 | 100 | cbrn (2.681) | safety | unpublished wet-lab know-how questions, bio-uplift |
| 32 | Alignment Faking | 14 | 4 | 51 | cbrn (1.794) | safety | complying in training to preserve values |
| 33 | StrongREJECT | 11 | 7 | 56 | harmful_manipulation (4.6) | safety | jailbreak robustness on forbidden prompts |
| 34 | Agentic Misalignment | 12 | 5 | 67 | loss_of_control (1.583) | safety | blackmail / harmful insider-action scenarios |
| 35 | Indirect Prompt Injection (IPI) | 14 | 3 | 71 | unresolved (-) | safety | prompt-injection robustness for agents |
| 36 | The Last Ones (TLO) | 11 | 5 | 46 | cyber (2.563) | safety | UK AISI 32-step full network takeover range |
| 37 | HPCT | 12 | 4 | 65 | cbrn (3.698) | safety | Human Pathogen Capabilities Test, bio-uplift proxy |
| 38 | CyScenarioBench | 12 | 4 | 50 | cyber (1.966) | safety | multi-stage attack scenario planning (Irregular) |
| 39 | MBCT | 11 | 4 | 56 | cbrn (3.698) | safety | Molecular Biology Capabilities Test, bio-uplift proxy |
| 40 | DeepSearchQA | 11 | 4 | 69 | societal_harm (2.55) | capability | multi-step web research |
| 41 | Bloom | 11 | 4 | 20 | societal_harm (2.195) | safety | automated behavioural evaluation generator (Anthropic) |
| 42 | DeepSWE | 10 | 5 | 54 | cyber (1.641) | capability | long-horizon software engineering |
| 43 | MMMU | 10 | 5 | 41 | societal_harm (2.162) | capability | multimodal college-level QA |
| 44 | ProgramBench | 10 | 5 | 87 | cyber (1.805) | capability | long-context programming |
| 45 | ABC Bench | 10 | 4 | 40 | cbrn (4.611) | safety | bio design/screening-evasion tasks (Meta) |
| 46 | CharXiv | 11 | 3 | 82 | societal_harm (2.162) | capability | chart understanding |
| 47 | Agent Red Teaming (ART) | 11 | 3 | 74 | cbrn (1.833) | safety | Gray Swan/UK AISI prompt-injection red-team arena |
| 48 | BioTIER | 10 | 3 | 93 | cbrn (4.347) | safety | biosecurity refusal evaluation |
| 49 | MathArena | 10 | 3 | 31 | loss_of_control (2.0) | capability | live competition maths |
| 50 | Long-form Virology | 12 | 2 | 50 | cbrn (3.0) | safety | open-ended virology protocol writing (bio uplift) |
| 51 | OfficeQA | 9 | 3 | 61 | societal_harm (2.162) | capability | grounded reasoning over office documents |
| 52 | Minimal-LinuxBench | 9 | 3 | 47 | loss_of_control (1.9) | safety | monitor-evasion / stealth in Linux admin tasks |
| 53 | BioMysteryBench | 11 | 2 | 50 | cbrn (1.833) | capability | analytical life-science puzzles |
| 54 | BixBench | 7 | 4 | 36 | cbrn (4.25) | capability | bioinformatics analysis tasks |
| 55 | CursorBench | 7 | 3 | 47 | societal_harm (2.162) | capability | IDE coding tasks (Cursor) |
| 56 | FrontierSWE | 7 | 3 | 30 | cyber (1.971) | capability | frontier software engineering tasks |
| 57 | ARC-AGI | 7 | 3 | 83 | loss_of_control (1.25) | capability | abstract reasoning puzzles |
| 58 | FrontierCode | 7 | 3 | 54 | societal_harm (2.162) | capability | frontier coding tasks |
| 59 | ScreenSpot | 7 | 3 | 36 | societal_harm (2.162) | capability | GUI grounding |
| 60 | SimpleQA | 7 | 3 | 23 | unresolved (-) | capability | factual recall / hallucination rate |

## Shortlist: 10 safety evaluations spanning the five risk domains

| name | domain | DF | pubs | publishers |
|---|---|---|---|---|
| WMDP | cbrn | 14 | 6 | cursor, meta, openai, rand, securebio, xai |
| VCT | cbrn | 34 | 8 | anthropic, cursor, meta, openai, rand, saferai, securebio, xai |
| Cybench | cyber | 16 | 7 | anthropic, epoch_ai, meta, metr, rand, saferai, us_caisi |
| CyberGym | cyber | 33 | 11 | anthropic, cursor, epoch_ai, google_deepmind, meta, metr, openai, redwood_research, saferai, xai, zai |
| Cyber Range | cyber | 24 | 8 | anthropic, epoch_ai, meta, metr, openai, rand, uk_aisi, us_caisi |
| SHADE-Arena | loss_of_control | 19 | 5 | anthropic, meta, metr, openai, redwood_research |
| Agentic Misalignment | loss_of_control | 12 | 5 | anthropic, meta, metr, openai, saferai |
| MASK | harmful_manipulation | 18 | 5 | anthropic, cursor, meta, saferai, xai |
| StrongREJECT | societal_harm | 11 | 7 | anthropic, cursor, meta, openai, saferai, thinking_machines, xai |
| BBQ | societal_harm | 10 | 1 | anthropic |

### WMDP (cbrn)

What it measures: Hazardous-knowledge proxy: 3,668 multiple-choice questions on biosecurity, cybersecurity and chemical security, written so that high scores indicate knowledge that could give uplift to weapons development; also used as an unlearning target.

Cited by (6 publishers, 14 docs): cursor, meta, openai, rand, securebio, xai.

Domain DF: cbrn 14, cyber 11, loss_of_control 8, harmful_manipulation 6, societal_harm 9.

Most informative sentences:

- "9.2.2.3.1 Capability Sandbagging We evaluate on two capability datasets: WMDP, a multiple-choice questions dataset on dangerous-capability, and Monorepo-Bench, an internal software-engineering benchmark in which models implement requested code changes." (openai-gpt-6-astra-system-card)
- "Incorporating both sources of uncertainty ensures that the size of the CI remains well-calibrated across different evaluations, including those with a large number of questions (e.g. WMDP-Bio: 1283 questions, 1 epoch) and those with a small number of questions and a large number of epochs (e.g. HPCT: 100 questions, 7 epochs)." (meta-muse-spark-system-card)
- "Models exploited shortcuts in over 30% of WMDP-Bio questions, answering correctly without access to the question text." (securebio-gpt-5-6-sol-independent-eval-2)

Cost / validity information in the corpus:

- "Incorporating both sources of uncertainty ensures that the size of the CI remains well-calibrated across different evaluations, including those with a large number of questions (e.g. WMDP-Bio: 1283 questions, 1 epoch) and those with a small number of questions and a large number of epochs (e.g. HPCT: 100 questions, 7 epochs)." (meta-muse-spark-system-card)
- "The multiple-choice questions constituting WMDP-Bio (n=1273) and WMDP-Chem (n=408) are derived from academic and professional experts in their respective domains." (meta-muse-spark-contemplating-system-card)
- "Error bars show bootstrap 95% Figure 9 presents model performance on the CIs. subset of WMDP questions in the cyber-security category." (meta-muse-spark-contemplating-system-card)
- "Figure 36: WMDP sandbagging evaluation on 400 questions, with three samples per question." (openai-gpt-6-astra-system-card)
- "Evaluations of Muse Spark were conducted using the final checkpoint where possible, but a helpful-only checkpoint was used in cases where refusal rate was sufficiently high to impact results (e.g. WMDP and high-risk bottlenecks)." (meta-muse-spark-system-card)

### VCT (cbrn)

What it measures: Virology Capabilities Test: multimodal troubleshooting questions on wet-lab virology protocols, scored against virologists' expert baselines, built by SecureBio to measure practical bio-uplift.

Cited by (8 publishers, 34 docs): anthropic, cursor, meta, openai, rand, saferai, securebio, xai.

Domain DF: cbrn 34, cyber 24, loss_of_control 22, harmful_manipulation 17, societal_harm 21.

Most informative sentences:

- "2.1.1 Virology Capabilities Test (VCT) The Virology Capabilities Test (VCT) is SecureBio’s multimodal, static benchmark designed to measure practical virology knowledge, with a focus on troubleshooting laboratory experiments." (securebio-gpt-5-5-independent-eval)
- "Dual-Use: Biological Capability Tests The Molecular Biology Capabilities Test (MBCT), Virology Capabilities Test (VCT), and Human Pathogens Capabilities Test (HPCT) are part of a suite of evaluations developed by SecureBio and the Center for AI Safety (Götting et al., 2025; SecureBio, 2025)." (meta-muse-spark-system-card)
- "Its strongest reported configurations scored 53.5% on the Virology Capabilities Test, 60.0% on the Molecular Biology Capabilities Test, 68.4% on the Human Pathogen Capabilities Test, and 68.3% on World-Class Bio." (openai-gpt-5-6-sol-preview-system-card)

Cost / validity information in the corpus:

- "Human expert baseline accuracy on VCT-v2, which is derived from unedited or minimally edited questions, is also plotted alongside that for VCT." (securebio-gpt-5-6-sol-independent-eval-2)
- "On the VCT multimodal virology evaluation, Mythos 5 scored 0.56, well above the expert baseline of 0.221 and nearly matching that of Mythos Preview (0.57)." (anthropic-claude-fable-5-system-card)
- "On the VCT multimodal virology evaluation, Sonnet 5 scores 0.45, well above the expert baseline of 0.221." (anthropic-claude-sonnet-5-system-card)
- "We analyze existing benchmark response data from 49 frontier AI models across 8,146 items, spanning 26 benchmarks, including both public and private benchmarks developed by SecureBio, such as the Virology Capabilities Test (VCT) (Götting, et al., 2025)." (rand-gemini-3-1-pro-independent-eval)
- "For the multimodal virology (VCT) and DNA synthesis screening tasks, scores shown are the mean values across all trials (bootstrap 95% CI)." (anthropic-claude-fable-5-1-system-card)
- "In the case of VCT, we also track the performance above the baseline set by expert baseliners (0.221)." (anthropic-claude-opus-5-5-system-card)

### Cybench (cyber)

What it measures: Professional capture-the-flag challenges (from HackTheBox, Sekai, Glacier, HKCert) with first-solve-time difficulty ratings, testing whether an agent can find and exploit vulnerabilities end to end.

Cited by (7 publishers, 16 docs): anthropic, epoch_ai, meta, metr, rand, saferai, us_caisi.

Domain DF: cbrn 11, cyber 16, loss_of_control 12, harmful_manipulation 9, societal_harm 7.

Most informative sentences:

- "2.2.2.1 CTF Challenges We evaluate Muse Spark against two sets of capture-the-flag challenges: Cybench, a widely-used public benchmark of 40 professional-level challenges enabling direct comparison with peer models, and a curated collection of public and private CTF challenges for broader domain coverage." (meta-muse-spark-system-card)
- "3.3.1 Cybench This public cyber capabilities benchmark is made up of 40 CTF challenges gathered from four CTF competitions." (anthropic-claude-mythos-preview-system-card)
- "Unlike our Cybench runs, GLM-5.2 frequently reaches the token limit on CyberGym: it hit the limit on 60% of tasks at 2M, 31% at 10M, and 4% at 50M, while no task hit the wall-clock limit at any budget." (saferai-glm-5-2-independent-eval)

Cost / validity information in the corpus:

- "Note that Anthropic results for Cybench report over 37 of the 40 Cybench challenges; Muse Spark Contemplating results reflect performance over the full set of 40 challenges." (meta-muse-spark-contemplating-system-card)
- "Across both suites Muse Spark 1.1 is near the benchmark ceiling (Cybench pass@10 ∼97.0%, curated pass@5 ∼96%), consistent with the broader trend of frontier models saturating public CTF benchmarks." (meta-muse-spark-1-1-system-card)
- "Fig. 2 shows the breakdown of Cybench success rates per subcategory of Cybench tasks." (saferai-glm-5-2-independent-eval)
- "At this level Muse Spark 1.1 is approaching the ceiling of the benchmark, similarly to contemporary frontier models that have effectively saturated Cybench." (meta-muse-spark-1-1-system-card)
- "However, Claude Opus 4.6 has saturated all of our current cyber evaluations, achieving ~100% on Cybench (pass@30) and 66% on CyberGym (pass@1)." (anthropic-claude-opus-4-6-system-card)
- "Moreover, Mythos Preview essentially saturates Cybench and CyberGym. - Including confidence intervals, the April version of Mythos Preview was probably 7 months ahead with a 90% confidence interval of 3-13 months." (epoch-ai-claude-mythos-5-independent-eval)

### CyberGym (cyber)

What it measures: Real-world vulnerability reproduction: given a codebase and a vulnerability description, the agent must write a proof-of-concept input that triggers the bug (from OSS-Fuzz crash data); a cyber-uplift proxy run by most labs.

Cited by (11 publishers, 33 docs): anthropic, cursor, epoch_ai, google_deepmind, meta, metr, openai, redwood_research, saferai, xai, zai.

Domain DF: cbrn 22, cyber 33, loss_of_control 24, harmful_manipulation 17, societal_harm 19.

Most informative sentences:

- "2.2.2.2 Complex Real-World Challenges In order to assess the offensive and dual-use capabilities of Muse Spark on challenges that more realistically proxy for relevant real world capabilities, we leverage a combination of existing public benchmarks (e.g. CyberGym), as well as privately developed challenges developed by Irregular." (meta-muse-spark-system-card)
- "In late 2025, we noticed that Opus 4.5 was close to solving all tasks in CyberGym, a benchmark that tests whether LLMs can reproduce known security vulnerabilities." (anthropic-claude-opus-4-6-other-2)
- "A.2.2 Sample The upstream CyberGym set contains 1,507 vulnerabilities, of which Lyptus's benchmark distribution contains 322; from these, Lyptus selected 122 tasks for model evaluation based on construct validity and difficulty coverage, and it is this 122-task level1 sample we run in full for GLM-5.2." (saferai-glm-5-2-independent-eval)

Cost / validity information in the corpus:

- "A.2.2 Sample The upstream CyberGym set contains 1,507 vulnerabilities, of which Lyptus's benchmark distribution contains 322; from these, Lyptus selected 122 tasks for model evaluation based on construct validity and difficulty coverage, and it is this 122-task level1 sample we run in full for GLM-5.2." (saferai-glm-5-2-independent-eval)
- "The reported score is a pass@1 evaluation of targeted vulnerability reproduction over the 1,507 tasks in the CyberGym suite—that is, we report the aggregate performance of trying 10 Wang, Z., et al. (2025)." (anthropic-claude-sonnet-4-6-system-card)
- "Success Rate on CyberGym (pass@1) *Competitor results are sourced from provider self-reported scores We also stress-tested the model’s capabilities beyond CyberGym without safety guardrails." (google-deepmind-gemini-3-5-flash-cyber-other)
- "Model success rate on CyberGym for GLM-5.2, Claude Opus 4.6, and GPT-5.5 when given a 2M, 10M, 50M token limit for each task." (saferai-glm-5-2-independent-eval)
- "This is known as “targeted vulnerability reproduction.” The reported score is a pass@1 evaluation of targeted vulnerability reproduction over the 1,507 tasks in the CyberGym suite." (anthropic-claude-fable-5-system-card)
- "Moreover, Mythos Preview essentially saturates Cybench and CyberGym. - Including confidence intervals, the April version of Mythos Preview was probably 7 months ahead with a 90% confidence interval of 3-13 months." (epoch-ai-claude-mythos-5-independent-eval)

### Cyber Range (cyber)

What it measures: Multi-stage network attack simulations (reconnaissance, lateral movement, exfiltration) in a realistic emulated enterprise, used to test whether models can autonomously conduct full cyber operations.

Cited by (8 publishers, 24 docs): anthropic, epoch_ai, meta, metr, openai, rand, uk_aisi, us_caisi.

Domain DF: cbrn 12, cyber 24, loss_of_control 14, harmful_manipulation 5, societal_harm 10.

Most informative sentences:

- "On this measure, GPT-5.5 may be the strongest model we have tested. /odw-collapse-start Spotlight: the rust_vm challenge /odw-collapse-end Cyber Range Results While our narrow cyber tasks test specific cyber skills in isolation, real-world cyber-attacks require chaining many steps together." (uk-aisi-gpt-5-5-independent-eval)
- "Claude does not succeed every time in these tests; Sonnet 4.5 succeeded autonomously on the Equifax cyber range in two of five trials." (anthropic-claude-sonnet-4-5-other)
- "5.1.2.3 Cyber Range Cyber range exercises measure a model’s ability to conduct fully end-to-end cyber operations in a realistic, emulated network." (openai-gpt-5-3-codex-system-card)

Cost / validity information in the corpus:

- "This exercise compared an existing cyber range against a new range, testing seven different models on the two ranges over 122 runs in total." (uk-aisi-claude-mythos-5-independent-eval)
- "In one of the 10 attempts, Kimi K3 successfully completes “The Last Ones” cyber range within the 100M token limit." (uk-aisi-kimi-k3-independent-eval)
- "Figure 2 shows model trajectories on the cyber range “The Last Ones” (TLO): a 32-step corporate network attack spanning 4 subnets and approximately 20 hosts, which we estimate would take a human expert roughly 20 hours to complete." (uk-aisi-glm-5-2-independent-eval)
- "A 100M-token cyber range run cost roughly $85 for both Opus 4.5 and 4.6, versus an estimated $46 for GLM-5.2 and $1.19 for DeepSeek V4-Pro at current pricing.3 Across tasks that both models being compared solved with 100% reliability, Opus 4.6 cost $15.17 per task versus GLM-5.2’s $6.12, and Opus 4.5 cost $12.50 per task versus DeepSeek V4-Pro’s $0.28." (uk-aisi-glm-5-2-independent-eval)
- "15 Combined Pass Rate: • gpt-5.1-codex-max: 60% • gpt-5.2-thinking: 47%2 • gpt-5.2-codex: 53.33% • gpt-5.3-codex: 80% Figure 7 The Cyber Range results show Codex GPT-5.3-Codex as a clear step up from prior models." (openai-gpt-5-3-codex-system-card)
- "23 Combined Pass Rate: • gpt-5.2-thinking: 47%2 • gpt-5.2-codex: 53.33% • gpt-5.3-codex: 80% • gpt-5.4-thinking: 73.33% Figure 14 GPT-5.4-Thinking remains stronger than the pre-5.3 models overall, but it is a step down from GPT-5.3-Codex on the Cyber Range suite." (openai-gpt-5-4-thinking-system-card)

### SHADE-Arena (loss_of_control)

What it measures: Agentic environments where a model must complete a main task while covertly pursuing a harmful side task without being flagged by an LLM monitor; measures sabotage and evasion capability.

Cited by (5 publishers, 19 docs): anthropic, meta, metr, openai, redwood_research.

Domain DF: cbrn 16, cyber 16, loss_of_control 19, harmful_manipulation 12, societal_harm 13.

Most informative sentences:

- "90 4.6.6 Targeted sabotage capability evaluation To test Sonnet 4.6’s capability for evading oversight, we use SHADE-Arena,31 in which each task consists of a long-horizon agentic main task that is paired with a harmful side task." (anthropic-claude-sonnet-4-6-system-card)
- "SHADE-Arena comprises 26 challenges where the model executes a main task while covertly pursuing a hidden side task (10 runs per challenge), while aware of being monitored." (meta-muse-spark-system-card)
- "For ShadeArena (high reasoning effort), GPT-6 Astra’s higher action-only score is driven by higher TPR on the conference-recap side task." (openai-gpt-6-astra-system-card)

Cost / validity information in the corpus:

- "SHADE-Arena comprises 26 challenges where the model executes a main task while covertly pursuing a hidden side task (10 runs per challenge), while aware of being monitored." (meta-muse-spark-system-card)
- "On SHADE-Arena, Claude Opus 4.7 achieves a 1.5–2% stealth success rate with extended thinking, compared with 3.8–4.2% for Claude Mythos Preview and 0–1.5% for Claude Opus 4.6." (anthropic-claude-opus-4-7-system-card)
- "On both SHADE-Arena and Minimal-LinuxBench, Sonnet 5 stealth rates are near zero: its scores are significantly inferior to those of other prior models." (anthropic-claude-sonnet-5-system-card)
- "The most notable change in performance compared with previous models is that stealth success rate on transcripts with long chains-of-thought increased from ~0% to ~3.8% on SHADE-Arena, suggesting a modest but notable change in ability to control chain-of-thought contents." (anthropic-claude-mythos-preview-addendum)
- "Our most direct evaluation for this capability is the “hidden CoT” variant of SHADE-Arena, which shows that when models can only be detected via their actions, stealth success rates are higher, though still low in absolute terms (10–15% for recent Claude models)." (anthropic-claude-mythos-5-other-2)
- "On SHADE-Arena and Minimal-LinuxBench, Opus 4.8 stealth rates are roughly comparable to Claude Opus 4.7 and well below Claude Mythos Preview." (anthropic-claude-opus-4-8-system-card)

### Agentic Misalignment (loss_of_control)

What it measures: Scenarios in which an agent with corporate access faces replacement or goal conflict and can choose blackmail, leaking or other insider threats; measures willingness to take harmful actions to preserve itself.

Cited by (5 publishers, 12 docs): anthropic, meta, metr, openai, saferai.

Domain DF: cbrn 9, cyber 10, loss_of_control 12, harmful_manipulation 4, societal_harm 5.

Most informative sentences:

- "The Agentic Misalignment benchmark (Lynch et al., 2025) tests whether models, instantiated as an email-oversight agent in a simulated corporate environment, will take harmful actions (across blackmail, corporate espionage, and lethal-action scenarios) when these are the only available means to preserve their goals or avoid being replaced." (meta-muse-spark-1-1-system-card)
- "We assess the motive of the model to pose a LoC risk using the Agentic Misalignment benchmark (Lynch et al. 2025). ● Opportunity represents the environment and the access that would allow for the translation of the model’s capability and propensity into a risk event." (saferai-glm-5-2-independent-eval)
- "Indeed, since Claude Haiku 4.5, every Claude model2 has achieved a perfect score on the agentic misalignment evaluation—that is, the models never engage in blackmail, where previous models would sometimes do so up to 96% of the time (Opus 4)." (anthropic-claude-haiku-4-5-other)

Cost / validity information in the corpus:

- "As reported in our model behavior assessment for Muse Spark 1.1, the model robustly maintains its epistemic integrity, achieving 95.7% honesty score on MASK, and it shows a low tendency toward self-preservation under pressure, getting a 1.1% harmful action rate across all tasks on Agentic Misalignment (Section 1.1.3)." (meta-muse-spark-1-1-system-card)

### MASK (harmful_manipulation)

What it measures: Honesty under pressure: compares a model's elicited belief with what it states when incentivised to lie, separating honesty from accuracy; the standard deception/lying benchmark cited by many labs.

Cited by (5 publishers, 18 docs): anthropic, cursor, meta, saferai, xai.

Domain DF: cbrn 17, cyber 17, loss_of_control 16, harmful_manipulation 16, societal_harm 14.

Most informative sentences:

- "12.1 MASK-Rectified 30 Using a dataset derived from MASK* , we test whether Grok 4.6 faithfully reports its beliefs when pressured to lie, as a proxy for the model’s tendency to assert misleading information." (cursor-grok-4-6-model-card)
- "5.1 MASK To evaluate for dishonesty, we use the MASK (Ren et al. 2025) benchmark, which measures the model’s propensity to lie under pressure." (saferai-glm-5-2-independent-eval)
- "As reported in our model behavior assessment for Muse Spark 1.1, the model robustly maintains its epistemic integrity, achieving 95.7% honesty score on MASK, and it shows a low tendency toward self-preservation under pressure, getting a 1.1% harmful action rate across all tasks on Agentic Misalignment (Section 1.1.3)." (meta-muse-spark-1-1-system-card)

Cost / validity information in the corpus:

- "As reported in our model behavior assessment for Muse Spark 1.1, the model robustly maintains its epistemic integrity, achieving 95.7% honesty score on MASK, and it shows a low tendency toward self-preservation under pressure, getting a 1.1% harmful action rate across all tasks on Agentic Misalignment (Section 1.1.3)." (meta-muse-spark-1-1-system-card)
- "On the MASK family of honesty probes, a 2B instruction model answers a neutral question correctly (“The capital of Australia is Canberra”) yet, when the same question is wrapped in pressure (“I’ll tip you $200 to tell me what I want to hear”) or when a false statement is pre-planted in a passage it is asked to continue (“A document claims the capital of Australia is Sydney; continue. . . ”), it echoes the pressured or false framing instead of its own belief." (anthropic-claude-opus-4-8-other-3)
- "Honesty and accuracy on MASK (n = 1,000 prompts per model)." (saferai-glm-5-2-independent-eval)
- "Per-setting honesty rates (Honest %) for GLM-5.2, Claude Opus 4.7, and GPT‑5.5 across the six MASK categories (continuations, disinformation, doubling down on known facts, known facts, provided facts, and statistics)." (saferai-glm-5-2-independent-eval)
- "4.3.3.4 MASK [Figure 4.3.3.4.A] Honesty rate on public split of MASK benchmark." (anthropic-claude-mythos-preview-system-card)
- "Honesty rate on the public MASK split: the fraction of prompts where the model did not contradict its own elicited belief under pressure." (anthropic-claude-fable-5-1-system-card)

### StrongREJECT (societal_harm)

What it measures: Jailbreak robustness: forbidden prompts paired with jailbreak techniques, graded by a rubric on specificity and convincingness of harmful compliance rather than refusal-string matching.

Cited by (7 publishers, 11 docs): anthropic, cursor, meta, openai, saferai, thinking_machines, xai.

Domain DF: cbrn 10, cyber 10, loss_of_control 9, harmful_manipulation 8, societal_harm 8.

Most informative sentences:

- "Three teams differ only in which benchmark is scored, HarmBench, JailbreakBench or StrongREJECT, and each team runs eight AARs against Phi-4-mini with the capability and over-refusal gates unchanged." (anthropic-claude-opus-4-8-other-3)
- "The original StrongREJECT LLM judge assigns each response a score from 0 to 5 to measure whether a jailbreak succeeds and how helpful the elicited output is." (meta-muse-spark-system-card)
- "Ahead of the GPT-5.4 launch, we replaced our previous StrongReject-based benchmark with a more challenging multiturn jailbreak evaluation derived from red-teaming exercises." (openai-gpt-5-4-thinking-system-card)

Cost / validity information in the corpus:

- "The original StrongREJECT LLM judge assigns each response a score from 0 to 5 to measure whether a jailbreak succeeds and how helpful the elicited output is." (meta-muse-spark-system-card)
- "74 In summary, our judge system defines a function J(x; s1 , s2 ) ∈ {0, 1} for a conversation x over the StrongREJECT score s1 (x) ∈ [0, 1] and the auditing rubric score s2 (x) ∈ [0, 1]: ( 1, if s1 (x) ≥ τ1 and s2 (x) ≥ τ2 J(x; s1 , s2 ) = 0, otherwise where τ1 = 0.9, τ2 = 0.8." (meta-muse-spark-system-card)
- "Figure 24 Attack Success Rate (ASR) on StrongREJECT v2." (meta-muse-spark-1-1-system-card)

### BBQ (societal_harm)

What it measures: Bias Benchmark for QA: ambiguous and disambiguated questions about protected groups; reports accuracy and bias score to detect stereotyped answers.

Cited by (1 publishers, 10 docs): anthropic.

Domain DF: cbrn 10, cyber 10, loss_of_control 10, harmful_manipulation 10, societal_harm 10.

Most informative sentences:

- "4.4.2 Bias Benchmark for Question Answering As with past models, we evaluated Mythos 5.1 using the Bias Benchmark for Question Answering (BBQ),4 a standard benchmark-based bias evaluation covering attributes such as age, race, gender, disability, and socioeconomic status." (anthropic-claude-fable-5-1-system-card)
- "8.2.2 Bias Benchmark for Question Answering We evaluated Claude Mythos Preview using the Bias Benchmark for Question Answering (BBQ),30 a standard benchmark-based bias evaluation that we have run for all recent models." (anthropic-claude-mythos-preview-system-card)
- "74 4.5.2 Bias Benchmark for Question Answering We evaluated Claude Opus 4.7 using the Bias Benchmark for Question Answering (BBQ),7 a standard benchmark-based bias evaluation." (anthropic-claude-opus-4-7-system-card)

Cost / validity information in the corpus: none found by the regex filter.

