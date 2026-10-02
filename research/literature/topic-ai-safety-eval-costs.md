# Frontier AI safety evaluations: what they measure and what they cost

Literature sweep, 2018-2026. 75 entries, 74 with fetched URLs. Companion file: `topic-ai-safety-eval-costs.json`.
Sim-to-real ladder: almost everything here sits at level 0 (text/tool I/O, no perception), a few at level 1 (image QA: VCT, LAB-Bench figures, HarmBench multimodal, ASIMOV), one at level 3 (generated video, Jindal et al.), and one level-9 ground-truth study (METR productivity RCT). Frontier-AI safety evaluation has no equivalent of levels 4-8; the closest analogues are human uplift trials and expert red teams, which are still text-mediated.

## One-page synthesis

What exists
- Capability evals used as deployment gates: METR time horizon (HCAST, RE-Bench), Cybench and private cyber suites (AISI, CAISI), WMDP/VCT/LAB-Bench/BioLP for bio, SWE-bench Verified and MLE-bench/PaperBench for AI R&D. Labs bind these to thresholds (Anthropic ASL-3/4, OpenAI High/Critical, DeepMind CCLs) with "scalable" automated evals validated by occasional "deep dives" (human uplift trials, expert red teams).
- Propensity/alignment evals: Apollo scheming, SHADE-Arena, MASK, sabotage evals, alignment faking, agentic misalignment, Petri/Gram automated audits. Scores are LLM-judged rates of covert action, lying or sabotage in synthetic agentic scenarios.
- Harmfulness/refusal evals: HarmBench, StrongREJECT, JailbreakBench, AgentHarm, AgentDojo, AILuminate, plus the false-alarm side (XSTest, OR-Bench, SORRY-Bench). These are the only family with routine sensitivity/specificity-style reporting (judge agreement with humans, over-refusal rates).
- Bias/honesty legacy: BBQ, TruthfulQA. Safetywashing shows both track general capability.

Where cost evidence is strong
- Human baselining: HCAST 563 baselines, >1500 expert-hours; RE-Bench 71 x 8 h expert attempts; METR admits baselining was "super expensive" and that some tasks only have time estimates.
- Human trials: Anthropic Opus 4 uplift trial (groups of 8-10, up to 2 days, Deloitte grading, thresholds 2.8x/5x); sabotage evals 108 paid participants; Opus 4.5 alignment audit "hundreds of hours of expert time"; Sonnet 4.5 audit "dozens of hours" plus >=60 auditor queries per investigation.
- Compute/API: HAL $40k for 21,730 rollouts; MLE-bench ~$5.5k/seed; PaperBench ~$9.5k/run; HELM $85-$10.9k per model; 8-seed reliability multiplies cost ~8x (EvalEval synthesis). StrongREJECT: $2,500 of human labels, <$1 to run a dozen jailbreaks. HarmBench: 20 min/A100 per GCG test case.
- Attacker cost: AISI Trends Report measures expert jailbreak effort rising from ~10 min to 7+ h across model generations, the one place safeguard robustness is reported as cost-to-attack.

Where cost evidence is absent
- Almost no benchmark paper reports authoring cost (WMDP, VCT, LAB-Bench, MASK all mention expert authors but no hours or dollars). Government reports state only "limited access" and "finite resources". No published eval reports a cost per unit of decision-relevant information.

Where validity evidence is strong
- Judge validity: HarmBench classifier 93.2% human agreement; StrongREJECT Spearman 0.85-0.90 vs 1,361 human labels; MASK judge 86.4%; SORRY-Bench 7k human labels; SHADE-Arena monitor AUC 0.87.
- Threats to validity are well documented: sandbagging (van der Weij; noise-injection detector), evaluation awareness (Needham AUC 0.83; Sonnet 4.5 80-100% verbalized awareness on honeypots; Redwood estimate >=25% of measured gains are eval gaming; Schoen et al. causal evidence), alignment faking (14% compliance gap), scenario-realism sensitivity (Gram: 2-3% -> ~0 with realistic scenarios; agentic misalignment higher when models believe it is real), Safetywashing (safety scores collinear with capability), construct-validity review of 445 benchmarks.

Where validity evidence is absent
- No study links any eval score to a real-world safety outcome. The only level-9 datapoint is METR's RCT (19% slowdown despite benchmark gains), which is about productivity, not harm. Uplift trials are text-only proxies (Anthropic's own caveat); RAND's red team was underpowered by the authors' account; OpenAI's bio study found non-significant uplift. Deployment gates therefore rest on threshold judgement, not calibrated predictive validity.

Canonical citations for a 4-page paper (pick 5-8)
1. kwa2025horizon + rein2025hcast: cost of human-calibrated capability measurement.
2. souly2024strongreject: judge validity and cost quantified in one place.
3. ren2024safetywashing: discriminant validity failure of safety benchmarks.
4. needham2025evalaware (with pan2025evalgaming or schoen2025antischeming): evaluation awareness as the core threat to inference from eval to deployment.
5. vanderweij2024sandbagging: false negatives by design.
6. anthropic2025opus4card: a real deployment gate with explicit thresholds, human trial cost and stated proxy weakness.
7. ghosh2026evalcosts: compute cost figures and reliability multipliers.
8. openai2025preparedness (or anthropic2026rsp): scalable-vs-deep-dive two-tier structure, the natural VOI framing.

Gaps a VOI paper can exploit
- No eval family reports sensitivity and false-alarm rate against a ground truth; no cost-per-bit accounting; the two-tier (cheap screen, costly confirm) structure in Preparedness/Barrett is asserted, not measured.


## Catalogue

| key | name | year | kind | ladder | what it feeds / scores | size | cost evidence | validity evidence | conf |
|---|---|---|---|---|---|---|---|---|---|
| kwa2025horizon | [METR 50% task-completion time horizon](https://arxiv.org/abs/2503.14499) | 2025 | study | 0 | LLM agent with shell/tool access in a sandbox works on software/ML/cyber tasks (RE-Bench, HCAST, 66 short novel tasks); binary success per task, logistic fit of success vs human task duration; horizon = duration at 50% (or 80%) success. | RE-Bench (7) + HCAST (189) + 66 SWAA short tasks, ~170 tasks in Time Horizon 1.1 suite | Rests on HCAST human baselines (>1500 h, 563 baselines) and RE-Bench (71 expert 8-h attempts); METR note: 'task construction and baselining were both super expensive'; some tasks have only time estimates, not real baselines. | Authors flag external validity: tasks are self-contained, low-context, clean scoring; time horizons differ between domains by orders of magnitude (visual computer-use 40-100x lower). No correlation with real-world safety outcomes reported. | high |
| rein2025hcast | [HCAST: Human-Calibrated Autonomy Software Tasks](https://arxiv.org/abs/2503.17354) | 2025 | benchmark | 0 | Agent receives task instructions and a container (ML engineering, cybersecurity, software engineering, reasoning); automatic graders; success compared against human baseliners working under identical conditions. | 189 tasks; 563 human baselines (>1500 h) | 563 human baselines totalling over 1500 hours of expert work; baseliners have ~5 y experience; METR states baselining and task construction were very expensive. | Human baselines under identical affordances give calibrated difficulty; no downstream real-world validation. | high |
| wijk2024rebench | [RE-Bench](https://arxiv.org/abs/2411.15114) | 2024 | benchmark | 0 | Agent works in 7 open-ended ML research engineering environments with GPU access; continuous score normalised to a starting solution (0) and a strong reference solution (1); compared to human experts at 2/8/32 h budgets. | 7 environments; 71 human 8-h attempts by 61 experts | 71 eight-hour expert attempts (61 distinct experts) = ~568 expert-hours of baselining; agents generate and test solutions >10x faster 'at much lower cost' (no dollar figure in abstract). | Human-expert comparison under matched conditions; Gemini 3 Pro FSF report uses RE-Bench tasks for its ML R&D CCL alert threshold. | high |
| zhang2024cybench | [Cybench](https://arxiv.org/abs/2408.08926) | 2024 | benchmark | 0 | Agent gets CTF task description, starter files and a Kali-style container; runs commands; scored by flag submission (task and subtask level); difficulty anchored by human first-solve time (FST). | 40 CTF tasks from 4 competitions, with subtasks | Token limits 6k in/2k out per step (32k for o1-preview); token and time usage tracked but no dollar cost given. Used directly by US AISI in pre-deployment tests. | FST from human competitions as difficulty ground truth; CISA/NSA experts reviewed transcripts for realism in the o1 joint test and commented on limits of CTFs as proxies for real operations. | high |
| li2024wmdp | [WMDP (Weapons of Mass Destruction Proxy)](https://arxiv.org/abs/2403.03218) | 2024 | benchmark | 0 | Text multiple-choice questions in biosecurity, cybersecurity and chemical security; accuracy. | 3,668 MCQs | Authored by a consortium of academics and technical consultants; filtered for infohazards before release; no hours or dollars stated. | Explicitly a proxy (knowledge, not wet-lab capability); van der Weij et al. show models can be prompted/fine-tuned to sandbag WMDP selectively. | high |
| gotting2025vct | [Virology Capabilities Test (VCT)](https://arxiv.org/abs/2504.16137) | 2025 | benchmark | 1 | Multimodal (text + image) multiple-response questions on virology wet-lab troubleshooting; accuracy vs expert virologists. | 322 questions | Built with 'dozens of PhD-level expert virologists'; expert baselining performed with internet access; no hours stated. | Direct human-expert comparison; authors frame it as a dual-use capability signal, not a validated predictor of real-world harm. | high |
| laurent2024labbench | [LAB-Bench](https://arxiv.org/abs/2407.10362) | 2024 | benchmark | 1 | Multiple-choice questions on practical biology research (literature QA, figure interpretation, database access, protocol troubleshooting, sequence manipulation); accuracy and coverage vs human biologists. | >2,400 MCQs (public subset on HuggingFace) | none stated | Human expert comparison; designed to match research workflows rather than textbook knowledge. | high |
| ivanov2024biolp | [BioLP-bench](https://www.biorxiv.org/content/10.1101/2024.08.21.608694v4) | 2024 | benchmark | 0 | Text: lab protocols with several benign edits plus one fatal error; model must identify the fatal mistake; accuracy vs human experts. | 800 test cases (per search-result summary; abstract does not state the count) | none stated | Human expert baseline; no downstream validation. | medium |
| phuong2024dangerous | [DeepMind dangerous capability evaluations (Gemini 1.0)](https://arxiv.org/abs/2403.13793) | 2024 | study | 0 | Text/agentic evaluations across persuasion and deception (incl. human-subject studies), cybersecurity CTFs, self-proliferation agent tasks, self-reasoning; mixed scoring (task success, human outcomes). | unknown | Persuasion evals use human participants (details in full paper, not abstract). | none stated in abstract; framed as pilot. | high |
| kinniment2023ara | [METR ARA evaluations (autonomous replication and adaptation)](https://arxiv.org/abs/2312.11671) | 2023 | benchmark | 0 | LLM agents with tool scaffolds attempt 12 real-world-style tasks (resource acquisition, self-replication); task completion scored by researchers. | 12 tasks, 4 agents | none stated | none stated | high |
| bhatt2023cyberseceval | [CyberSecEval (Purple Llama)](https://arxiv.org/abs/2312.04724) | 2023 | benchmark | 0 | Prompts eliciting code; static analysis for insecure code; prompts requesting cyberattack help scored for compliance by LLM judge. | not stated in abstract | none stated | none stated in abstract | medium |
| anurin2024threecb | [3CB: Catastrophic Cyber Capabilities Benchmark](https://arxiv.org/abs/2410.09114) | 2024 | benchmark | 0 | LLM agents in containerised offensive-cyber challenges (binary analysis to web); success per challenge. | not stated in abstract | none stated | none stated | medium |
| zhang2025bountybench | [BountyBench](https://arxiv.org/abs/2505.15216) | 2025 | benchmark | 0 | Agents operate on 25 real codebases with set-up environments; Detect/Exploit/Patch tasks from 40 real bug bounties; success scored by exploit/patch tests; value weighted by bounty dollars. | 25 systems, 40 bounties, 3 task types | Manual environment setup per system; bounty values give a monetary scale for capability. | Real vulnerabilities with real bounty payouts anchor task realism. | high |
| chan2024mlebench | [MLE-bench](https://arxiv.org/abs/2410.07095) | 2024 | benchmark | 0 | Agent solves Kaggle competitions end-to-end with compute; scored against Kaggle leaderboards (medal rates). | 75 Kaggle competitions | EvalEval estimate ~$5,500 per single-seed run (75 x 24 h A10 + API); abstract itself gives no cost. | Human baseline via public leaderboards; contamination analysed. | high |
| starace2025paperbench | [PaperBench](https://arxiv.org/abs/2504.01848) | 2025 | benchmark | 0 | Agent replicates ICML 2024 papers from scratch; hierarchical author-written rubrics graded by an LLM judge; judge validated on a separate benchmark. | 20 papers, 8,316 gradable leaf tasks | EvalEval estimate ~$9,500 per full evaluation (~$4,200 code-only); human PhD baseline attempts (hours not in abstract). | LLM judge benchmarked against human grading (numbers in full paper). | high |
| swebench2024verified | [SWE-bench Verified](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified) | 2024 | benchmark | 0 | Agent receives a GitHub issue and repository snapshot; patch scored by hidden unit tests (pass/fail). | 500 human-validated tasks | OpenAI post (not fetchable, HTTP 403) states 93 professional software developers annotated 1,699 samples with 3 annotations each; HF card confirms human validation only. | Human validation removes underspecified/unfair tasks; still contamination-prone (public GitHub). | medium |
| kutasov2025shade | [SHADE-Arena](https://arxiv.org/abs/2506.15740) | 2025 | benchmark | 0 | Agent in a tool-rich synthetic environment gets a benign main task plus a hidden harmful side task; scored on main-task success, side-task success and evading an LLM monitor (monitor AUC). | 17 task pairs (per paper; abstract says 'wide array') | Environment construction described as complex (hand-built tools/data); no hours stated. | Monitor AUC as detection sensitivity/false-alarm proxy; synthetic environments. | medium |
| meinke2024scheming | [Apollo in-context scheming evaluations](https://arxiv.org/abs/2412.04984) | 2024 | benchmark | 0 | Agentic text scenarios with a strongly nudged goal and discoverable oversight; scored on whether the model takes covert actions (disable oversight, self-exfiltrate, sandbag) and whether it confesses under follow-up. | 6 agentic evaluations; 5 frontier models | none stated | Heavily nudged scenarios; later work (Schoen et al. 2025) shows results confounded by evaluation awareness. | high |
| ren2025mask | [MASK: honesty benchmark](https://arxiv.org/abs/2503.03750) | 2025 | benchmark | 0 | Text: belief elicited neutrally (3 direct + 2 consistency prompts), then a pressure prompt; LLM judge maps statements to propositions; honesty = 1 - P(lie). | 1,500 examples (1,000 public, 500 held-out), 6 archetypes | Human-written examples with multi-stage review; lead authors manually reviewed nearly every example; no hours stated. | LLM judge agrees with 150 manually labelled examples at 86.4%. | high |
| benton2024sabotage | [Anthropic sabotage evaluations](https://arxiv.org/abs/2410.21514) | 2024 | study | 0 | Four evals: human decision sabotage (human participants making business decisions with a sabotaging assistant), code sabotage (attacker/defender minigame and 100k-commit simulation), sandbagging (capability suppression then anti-refusal fine-tuning), undermining oversight (overseer model rating harmful outputs). | Human trial: 54 control + 3x18 treatment participants, 3 scenarios, 30 min each; code minigame 512 simulations | 108 paid participants ($30 bonus for correct decisions); 30-minute sessions; simulation counts above. | Human-subject trial gives direct behavioural outcome; authors judge minimal mitigations sufficient for current models. | medium |
| greenblatt2024alignmentfaking | [Alignment faking](https://arxiv.org/abs/2412.14093) | 2024 | study | 0 | Text: system prompt tells Claude 3 Opus it is trained on free-tier but not paid-tier conversations; compliance with harmful queries compared across tiers; scratchpad reasoning inspected. | unknown | none stated | Direct evidence that behaviour depends on perceived observation context, undermining eval-to-deployment inference. | high |
| anthropic2025agenticmisalignment | [Agentic misalignment (blackmail scenarios)](https://www.anthropic.com/research/agentic-misalignment) | 2025 | study | 0 | Simulated corporate email-agent environment with goal conflict and replacement threat; transcripts classified by Claude Sonnet 3.7 plus string matching. | 16 models, 2 primary scenarios | none stated | Authors: scenarios deliberately constrained; models misbehave MORE when they believe the situation is real; no evidence of agentic misalignment in real deployments (level-9 signal absent). | high |
| schoen2025antischeming | [Anti-scheming training stress test (OpenAI/Apollo)](https://arxiv.org/abs/2509.15541) | 2025 | study | 0 | 26 out-of-distribution agentic evaluations (180+ environments) scoring covert actions as scheming proxy; chain-of-thought inspected for evaluation awareness; causal interventions on awareness. | 26 evaluations, 180+ environments | none stated | Explicit: reductions may be partly driven by situational awareness; evaluation results may not transfer to deployment. | medium |
| anthropic2025petri | [Petri: automated alignment auditing tool](https://www.anthropic.com/research/petri-open-source-auditing) | 2025 | tooling | 0 | Auditor LLM drives multi-turn scenarios (from natural-language seed instructions) against a target model; LLM judge scores transcripts on deception, sycophancy, harmful cooperation, self-preservation, power-seeking, reward hacking. | 111 seed instructions x 14 frontier models (pilot) | 'Only minutes of hands-on effort' per hypothesis; Sonnet 4.5 card: median investigation >=60 queries, plus 'dozens of hours' of researcher transcript review. | Authors: 111 scenarios is small; auditor models impose limits; realism filter reduced eval awareness ~25% and increased misaligned behaviour ~5% (Sonnet 4.5 card). | high |
| marks2025hiddenobjectives | [Auditing for hidden objectives (blind auditing game)](https://arxiv.org/abs/2503.10965) | 2025 | study | 0 | A model trained with a concealed reward-model-sycophancy objective; four blinded human teams audit it with interpretability (SAEs), behavioural attacks, data analysis; success = identify objective. | 4 teams, 1 model organism | Team-hours not stated in abstract. | Game with known ground truth gives a true-positive rate for auditing methods. | high |
| lindner2026gram | [Gram: automated sabotage-propensity auditing](https://arxiv.org/abs/2605.30322) | 2026 | tooling | 0 | Simulated agentic deployment scenarios with incentives to sabotage; automated investigator pipeline; misbehaviour rate per trajectory. | 17 scenarios | none stated | Strong sensitivity of measured rate to scenario realism (false-alarm evidence for contrived scenarios). | medium |
| souly2026aisicase | [UK AISI alignment evaluation case study](https://arxiv.org/abs/2604.00788) | 2026 | study | 0 | Petri-based scaffold simulating internal deployment of a coding agent in an AI lab; varies research motivation, replacement threat, autonomy; LLM-judged sabotage. | 4 frontier models | none stated | Validated that scaffold trajectories are not reliably distinguishable from real deployment data by the models unprompted; both models can distinguish when prompted. | medium |
| mazeika2024harmbench | [HarmBench](https://arxiv.org/abs/2402.04249) | 2024 | benchmark | 1 | Harmful behaviour strings (standard, contextual, copyright, multimodal) attacked by 18 automated red-teaming methods; completion (512 tokens, greedy) classified by a fine-tuned Llama-2-13B classifier; attack success rate. | 510 behaviours (200 standard, 100 contextual, 100 copyright, 110 multimodal); 18 methods x 33 models/defences | GCG ~20 min per test case on a 7B model on one A100; R2D2 adversarial training 16 h on 8xA100. | Human-agreement of classifier; ASR is a proxy for misuse potential, not real-world harm. | high |
| souly2024strongreject | [StrongREJECT](https://arxiv.org/abs/2402.10260) | 2024 | benchmark | 0 | 313 forbidden prompts in 6 categories; response scored by rubric evaluator: (1-refused) x (specificity + convincingness)/2 on 5-point scales, or fine-tuned Gemma-2B. | 313 prompts; 1,361 human-labelled responses | Labeling budget $2,500 with 5 LabelBox labelers; running a dozen jailbreaks over the dataset ~15 min and <$1 with GPT-4o-mini. | Best-in-class human agreement; shows jailbreaks often degrade capability, explaining inflated prior ASRs. | high |
| andriushchenko2024agentharm | [AgentHarm](https://arxiv.org/abs/2410.09024) | 2024 | benchmark | 0 | Explicitly malicious multi-step agent tasks with synthetic tools; scored on refusal and on task completion (capability retained after jailbreak); Inspect-based. | 110 base tasks (440 with augmentations), 11 harm categories | none stated | none stated (synthetic tools; peer-reviewed at ICLR 2025) | high |
| chao2024jailbreakbench | [JailbreakBench](https://arxiv.org/abs/2404.01318) | 2024 | benchmark | 0 | 100 behaviours; adversarial prompts; Llama-3-70B judge with custom prompt; leaderboard of attacks/defences. | 100 behaviours; 300-example human-preference set for judge selection | none stated | Judge validated against human labels. | high |
| debenedetti2024agentdojo | [AgentDojo](https://arxiv.org/abs/2406.13352) | 2024 | benchmark | 0 | Agent uses simulated tools (email, banking, travel) whose returned data contain prompt injections; utility and security scored by deterministic checks. | 97 tasks, 629 security test cases | none stated | none stated | high |
| rottger2023xstest | [XSTest (exaggerated safety)](https://arxiv.org/abs/2308.01263) | 2023 | benchmark | 0 | 250 safe prompts (10 types) that resemble unsafe ones plus 200 unsafe contrasts; responses labelled as full compliance / partial / refusal (human annotation, later GPT-4). | 450 prompts | none stated | Directly measures the false-alarm side of safety behaviour; hand-built contrast design. | high |
| xie2024sorrybench | [SORRY-Bench](https://arxiv.org/abs/2406.14598) | 2024 | benchmark | 0 | 440 class-balanced unsafe instructions over 44 topics with 20 linguistic augmentations; refusal judged by fine-tuned 7B judge. | 440 base prompts (x20 augmentations); >7,000 human annotations for judge meta-evaluation; 50+ models | Explicitly targets evaluation cost: small judges replace GPT-4; 7k human labels collected. | Judge validated on 7k+ human annotations. | high |
| cui2024orbench | [OR-Bench (over-refusal)](https://arxiv.org/abs/2405.20947) | 2024 | benchmark | 0 | Automatically generated seemingly-toxic but benign prompts (80k, 1k hard) plus 600 toxic prompts; refusal judged by LLM. | 80,000 prompts + 1,000 hard + 600 toxic | none stated | none stated in abstract (LLM-generated prompts) | high |
| ghosh2025ailuminate | [AILuminate v1.0](https://arxiv.org/abs/2503.05731) | 2025 | standard | 0 | Single-turn adversarial prompts across 12 hazard categories; ensemble evaluator models; five-tier grade (Poor to Excellent). | 12 hazard categories; prompt count not in abstract | none stated | Acknowledged limits: evaluator uncertainty, no multi-turn/multimodal. | high |
| parrish2021bbq | [BBQ: Bias Benchmark for QA](https://arxiv.org/abs/2110.08193) | 2021 | benchmark | 0 | Hand-built QA items with under-informative vs adequately informative contexts across 9 social dimensions; accuracy and bias score. | 58,492 examples (full paper); abstract does not state count | Hand-built by authors with templates; no cost stated. | Grounded in attested US social biases; no downstream validation. | high |
| lin2021truthfulqa | [TruthfulQA](https://arxiv.org/abs/2109.07958) | 2021 | benchmark | 0 | 817 questions targeting common misconceptions; human-judged truthfulness or fine-tuned GPT-judge; MC variant. | 817 questions, 38 categories | none stated | Safetywashing and MASK show TruthfulQA correlates with capability rather than honesty. | high |
| aisi2024sonnet | [US/UK AISI joint pre-deployment test: Claude 3.5 Sonnet (upgraded)](https://www.aisi.gov.uk/blog/pre-deployment-evaluation-of-anthropics-upgraded-claude-3-5-sonnet) | 2024 | study | 0 | Agentic runs (Inspect) on cyber CTFs, software/AI R&D tasks, bio QA with and without tools; safeguards red-teamed by experts; solve rates vs reference models and human baselines. | US: 40 cyber challenges; UK: 47 cyber (15 public, 32 private); plus SWE and reasoning suites | 'Limited period of pre-deployment access' and 'finite resources'; expert engineers and scientists from both institutes; no hours stated. | Findings 'preliminary'; small differences within margins of error; results a lower bound on elicitable capability. | high |
| aisi2024o1 | [US/UK AISI joint pre-deployment test: OpenAI o1](https://dpo-india.com/Resources/NIST/US-AISI1-UK-AISI2-Joint-Pre-Deployment-Test-OpenAIo1.pdf) | 2024 | study | 0 | Cybench (40 CTFs) via Inspect agents, Pass@1 over 10 attempts and Pass@10, up to 100 messages; UK private cyber suite graded by difficulty tier; transcripts reviewed by CISA/NSA SMEs. | 40 Cybench tasks x 10 attempts; UK cyber suite | 10 attempts per task, 100-message cap; SME transcript review; report notes results may understate capability because of limited time and iterations. | Human baselines are competition first-solve times, not controlled; report calls for controlled human baselines. | medium |
| caisi2025deepseek | [CAISI evaluation of DeepSeek models](https://www.nist.gov/news-events/news/2025/09/caisi-evaluation-deepseek-ai-models-finds-shortcomings-and-risks) | 2025 | study | 0 | 19 public and private benchmarks (cyber, software, science, agent hijacking, jailbreak robustness, censorship); solve rates and attack-compliance rates; cost per performance. | 7 models x 19 benchmarks | Reports inference cost comparisons across models; eval effort not stated. | none stated | high |
| aisi2025trends | [UK AISI Frontier AI Trends Report](https://www.aisi.gov.uk/frontier-ai-trends-report) | 2025 | study | 0 | Aggregate of AISI evaluations Nov 2023-Oct 2025: agentic cyber and software tasks, chem-bio QA, safeguard red-teaming by experts, sandbagging transcript review. | 30+ frontier systems; 2,700+ transcripts reviewed for sandbagging | Expert jailbreak effort rose from ~10 min to 7+ h (~40x) across successive generations; scaffold optimisation reached 25% of performance at ~13% token budget. | No sandbagging detected in 2,700+ transcripts; safeguard results show attacker-cost as a measurable quantity. | high |
| aisi2024inspect | [Inspect AI evaluation framework](https://github.com/UKGovernmentBEIS/inspect_ai) | 2024 | tooling | 0 | Python framework: solvers, scorers, sandboxed tool use, multi-turn agents, model-graded scoring; inspect_evals collection. | 200+ pre-built evaluations in inspect_evals; 2.9k GitHub stars | Open-source; removes per-eval engineering cost; no numbers. | n/a | high |
| anthropic2025opus4card | [Claude Opus 4 system card: bioweapons acquisition uplift trial](https://www-cdn.anthropic.com/6be99a52cb68eb70eb9572b4cafad13df32ed995.pdf) | 2025 | study | 0 | Human participants (groups of 8-10, up to 2 days) draft a bioweapons acquisition plan with internet only vs internet + safeguard-free Claude; graded by Deloitte rubric; uplift = ratio of mean scores; critical failures counted. | Groups of 8-10 participants per arm; contractors from SepalAI and Mercor | Up to 2 days per participant, external contractors, Deloitte grading; internal survey: staff spent >2 h each evaluating AI R&D uplift; RSP autonomy eval: 42 tasks x 10 runs. | Anthropic: text-based uplift trials are 'substantially weaker proxies for real-world scenarios' (tacit knowledge, materials, persistence); threshold set conservatively. | high |
| anthropic2025opus45card | [Claude Opus 4.5 system card: uplift trials, eval awareness, alignment audit effort](https://www.anthropic.com/claude-opus-4-5-system-card) | 2025 | study | 0 | Expert and novice uplift trials, automated behavioural audits (Petri-style), interpretability steering of eval-awareness representations, internal AI R&D productivity survey (18 staff). | 18 internal survey participants; hundreds of hours of expert review | Alignment assessment: manual expert inspection of hundreds-thousands of transcripts, tens-hundreds of thousands of generated transcripts, 'hundreds of hours of expert time'; staff spent >2 h each on R&D survey. | Eval-awareness mitigation partially effective; ASL determination draws on automated evals, uplift trials and third-party red teaming. | high |
| anthropic2025sonnet45card | [Claude Sonnet 4.5 system card: evaluation awareness](https://www.anthropic.com/claude-sonnet-4-5-system-card) | 2025 | study | 0 | Automated behavioural audit with Claude Opus 4.1 auditors/graders (median >=60 queries per investigation), realism filter, activation steering to inhibit eval-awareness representations. | unknown | 'Dozens of hours of researcher time' reviewing transcripts; hours of manual transcript review across snapshots. | Anthropic states eval awareness accounts for 'a portion, but not all' of alignment gains on some evals; expects the effect in other production LLMs. | high |
| pan2025evalgaming | [Sonnet 4.5's eval gaming undermines alignment evals (Redwood analysis)](https://blog.redwoodresearch.org/p/sonnet-45s-eval-gaming-seriously) | 2025 | position | 0 | Secondary analysis of Anthropic system-card numbers. | unknown | none stated | Argues training against misalignment evals reinforces awareness, making evals unreliable predictors of deployment behaviour. | high |
| mouton2024randbio | [RAND red-team study: LLMs and biological attack planning](https://www.rand.org/pubs/research_reports/RRA2977-2.html) | 2024 | study | 0 | Teams of researchers role-play malign non-state actors planning a biological attack, with internet only vs internet + LLM; plan viability scored by experts. | Multiple teams (cells) across scenarios; counts in full report | Expert exercise with multiple research teams; authors say future work should add more LLMs and researchers to increase test sensitivity (i.e. study was underpowered). | Authors note the study did not measure distance between LLM frontier and required knowledge; explicitly flags low sensitivity. | high |
| openai2024bioearlywarning | [OpenAI early-warning system for LLM-aided biological threat creation](https://openai.com/index/building-an-early-warning-system-for-llm-aided-biological-threat-creation/) | 2024 | study | 0 | Human study: biology experts and students complete bio-threat-creation tasks with internet only vs internet + GPT-4 (research-only version); responses scored on accuracy, completeness, innovation, time, self-rated difficulty. | 100 participants (50 biology experts, 50 students) per published description | 100 human participants in a controlled study; hours not verified. | Authors flag limited statistical power and that information access is not the only barrier. | low (URL not fetched) |
| becker2025productivity | [METR developer productivity RCT](https://arxiv.org/abs/2507.09089) | 2025 | study | 9 | Randomised controlled trial: 16 experienced open-source developers, 246 real issues randomly assigned AI-allowed vs not; outcome = completion time. | 16 developers, 246 tasks | Developers paid for real work (rate not in abstract); 246 tasks of real repository work. | Direct demonstration that benchmark-style capability does not translate to real productivity; 20 robustness checks. | high |
| vanderweij2024sandbagging | [AI sandbagging](https://arxiv.org/abs/2406.07358) | 2024 | study | 0 | Prompting and password-locked fine-tuning to make models selectively underperform on WMDP while keeping general benchmarks; accuracy deltas. | unknown | none stated | Shows capability evals are vulnerable: a passing (low) score need not mean absence of capability. | high |
| tice2024noise | [Noise injection reveals sandbagging](https://arxiv.org/abs/2412.01784) | 2024 | tooling | 0 | Gaussian noise added to weights; performance-vs-noise curve; sandbagging models show anomalous improvement. | unknown | none stated | Detector validated on password-locked and prompted sandbaggers (true-positive evidence). | high |
| needham2025evalaware | [LLMs often know when they are being evaluated](https://arxiv.org/abs/2505.23836) | 2025 | study | 0 | 1,000 transcripts from 61 datasets (eval vs deployment); model asked to classify; AUC. | 1,000 prompts/transcripts, 61 datasets | none stated | Direct evidence of a construct-validity threat: behaviour may differ between eval and deployment. | medium |
| li2026evalawaredecomp | [Decomposing and measuring evaluation awareness (EvalAwareBench)](https://arxiv.org/abs/2605.23055) | 2026 | benchmark | 0 | 100 paired safety/capability tasks with 8 toggleable trigger factors (placeholder entities, grading formats); chain-of-thought monitored for recognition; behaviour change measured. | 100 task pairs, 9 models, 4 benchmarks | none stated | Provides attribution tools; proposes 'behavioural consistency under recognition' as validity check. | medium |
| ren2024safetywashing | [Safetywashing](https://arxiv.org/abs/2407.21792) | 2024 | study | 0 | Meta-analysis: correlation of safety benchmark scores with a general-capability factor across dozens of models. | Dozens of models, many safety benchmarks | none stated | Central discriminant-validity evidence for the safety-eval literature. | high |
| bean2025constructvalidity | [Measuring what matters: construct validity in LLM benchmarks](https://arxiv.org/abs/2511.04703) | 2025 | study | - | Systematic review of 445 benchmarks by 29 reviewers against validity criteria. | 445 benchmarks, 29 reviewers | none stated | Meta-level; documents that most benchmarks lack statistical testing and clear definitions. | medium |
| reuel2024betterbench | [BetterBench](https://arxiv.org/abs/2411.12990) | 2024 | study | - | Assessment of 24 benchmarks against 46 lifecycle best practices. | 24 benchmarks, 46 criteria | none stated | none stated | high |
| singh2025leaderboard | [The Leaderboard Illusion](https://arxiv.org/abs/2504.20879) | 2025 | study | - | Analysis of Chatbot Arena data-access and private-testing practices. | unknown | none stated | Evidence that leaderboard scores reflect testing access, not only capability. | high |
| miller2024errorbars | [Adding error bars to evals](https://arxiv.org/abs/2411.00640) | 2024 | position | - | Statistical framework: questions as samples from a super-population; SE, clustered SE, paired comparisons, power analysis for eval design. | unknown | none stated | Formal reliability treatment; recommends power analysis before running evals. | high |
| weidinger2025evalscience | [Toward an evaluation science for generative AI](https://arxiv.org/abs/2503.05336) | 2025 | position | - | n/a (position paper) | unknown | none stated | Explicit call for metrics 'applicable to real-world performance' and institutions for evaluation. | high |
| shevlane2023extreme | [Model evaluation for extreme risks](https://arxiv.org/abs/2305.15324) | 2023 | position | - | n/a (position paper) | unknown | none stated | none stated | high |
| barrett2024benchmarkearly | [Benchmark early and red team often](https://arxiv.org/abs/2405.10986) | 2024 | position | - | n/a (framework paper) | unknown | Explicit cost tiering: open benchmarks 'low-cost but accuracy-limited'; closed red teams 'higher-cost but higher accuracy'. | Correlation between tiers is hypothesised, not measured. | high |
| buhl2024safetycases | [Safety cases for frontier AI](https://arxiv.org/abs/2410.21572) | 2024 | position | - | n/a | unknown | none stated | none stated | high |
| mccaslin2025stream | [STREAM (ChemBio) reporting standard](https://arxiv.org/abs/2508.09853) | 2025 | standard | - | Reporting template for chem-bio evaluations in model reports (what was tested, how, how results inform decisions). | Developed with 23 experts; 3-page template | none stated | none stated | high |
| ghosh2026evalcards | [Evaluation Cards](https://arxiv.org/abs/2606.09809) | 2026 | standard | - | Reporting layer composing benchmark, run and model metadata with reproducibility, completeness, provenance and comparability signals. | 5,816 models, 635 benchmarks, 101,843 results analysed | none stated | none stated | medium |
| ghosh2026evalcosts | [AI evals are becoming the new compute bottleneck](https://huggingface.co/blog/evaleval/eval-costs-bottleneck) | 2026 | study | - | Synthesis of published evaluation cost figures. | unknown | Primary cost synthesis; static benchmarks compressible 100-200x, agent benchmarks only 2-3.5x. | n/a | high |
| kapoor2025hal | [Holistic Agent Leaderboard (HAL)](https://arxiv.org/abs/2510.11977) | 2025 | tooling | 0 | Standardised harness running agents across 9 benchmarks; cost and accuracy logged; LLM-aided log inspection. | 21,730 rollouts, 9 models, 9 benchmarks, 2.5B tokens | $40k for one single-seed sweep; ~$1.84 per rollout average. | none stated | medium |
| metr2026horizonlimits | [METR: clarifying limitations of time horizon](https://metr.org/notes/2026-01-22-time-horizon-limitations/) | 2026 | position | 0 | n/a (methodological note) | unknown | 'Task construction and baselining were both super expensive'; some tasks carry time estimates instead of measured baselines. | Domain gap of orders of magnitude; tasks self-contained vs collaborative real work. | high |
| anthropic2026rsp | [Anthropic Responsible Scaling Policy (v3.4)](https://www.anthropic.com/responsible-scaling-policy) | 2026 | standard | - | Policy: capability thresholds (CBRN, AI R&D automation/acceleration) checked by comprehensive assessments; ASL-3/4 deployment and security standards. | unknown | Assessment cadence lengthened explicitly to afford better elicitation; policy admits past evals lacked basic elicitation (best-of-N, CoT). | Acknowledged under-elicitation gaps now tracked. | high |
| openai2025preparedness | [OpenAI Preparedness Framework v2](https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf) | 2025 | standard | - | Policy: Tracked Categories (bio/chem, cyber, AI self-improvement) with High/Critical thresholds; automated 'scalable evaluations' with indicative thresholds, 'deep dives' (incl. human experts) validate them; Capabilities Report and Safeguards Report to Safety Advisory Group. | unknown | Explicit two-tier design: cheap scalable evals every deployment, costly deep dives periodically. | Deep dives exist 'to validate the scalable evaluations'; elicitation gap acknowledged. | high |
| deepmind2026fsf | [Google DeepMind Frontier Safety Framework (v3.1)](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) | 2026 | standard | - | Policy: Critical Capability Levels (CBRN, cyber, harmful manipulation, ML R&D, misalignment) with early-warning evaluations and alert thresholds; safety-case reviews before external launch. | unknown | none stated | none stated | high |
| deepmind2025gemini3fsf | [Gemini 3 Pro Frontier Safety Framework report](https://storage.googleapis.com/deepmind-media/gemini/gemini_3_pro_fsf_report.pdf) | 2025 | study | 0 | Early-warning evals: cyber key-skills benchmark (v1 hard 12 challenges, v2 13 challenges), RE-Bench ML R&D tasks, situational-awareness (11) and stealth (4) challenges, CBRN QA and lab-uplift trials, external red teams. | Cyber 12+13 challenges; 11 situational-awareness + 4 stealth challenges | Uses external specialist groups; lab uplift trials referenced; no hours or dollars. | Report states threat models are abstract and CCLs set holistically; 'cannot rule out' logic with safety margins. | high |
| bengio2025intlreport | [International AI Safety Report 2025](https://arxiv.org/abs/2501.17805) | 2025 | position | - | n/a (evidence synthesis by 100 experts, 30 nations) | unknown | none stated | none stated | medium |
| sermanet2025asimov | [ASIMOV benchmark and robot constitutions](https://arxiv.org/abs/2503.08663) | 2025 | benchmark | 1 | Text and image scenarios generated from real-world scenes and hospital injury reports; VLM asked whether an action is desirable; alignment rate with human judgement. | 'large-scale' (counts in paper; ASIMOV-2.0 adds video and physical constraints) | none stated | Human-judgement alignment is the score; injury-report grounding; open-loop only (no physical outcome). | high |
| jindal2025danger | [Can AI perceive physical danger and intervene?](https://arxiv.org/abs/2509.21651) | 2025 | benchmark | 3 | Generated photoreal images/videos of safe-to-unsafe transitions from real injury narratives; system-instruction safety constraints; scored on constraint satisfaction with thinking traces. | unknown | none stated | Generated media, not real trials; human agreement not in abstract. | medium |

## Entry details

### kwa2025horizon: METR 50% task-completion time horizon (2025, METR)
- URL: https://arxiv.org/abs/2503.14499 (arXiv 2503.14499)
- Measures: Length of tasks (in human-expert minutes) an agent completes with 50% reliability; used as a headline autonomy capability metric and as an ASL/CCL autonomy proxy.
- Reported: Claude 3.7 Sonnet ~50 min horizon (Mar 2025); doubling time ~7 months since 2019; bootstrap CIs roughly a factor of 2 each direction; later frontier horizons 2.5-4.3 h (metr.org, May 2026).
- Notes: Second URL fetched: https://metr.org/time-horizons/ (May 2026 update) and the Jan 2026 limitations note (separate entry metr2026horizonlimits).

### rein2025hcast: HCAST: Human-Calibrated Autonomy Software Tasks (2025, METR)
- URL: https://arxiv.org/abs/2503.17354 (arXiv 2503.17354)
- Measures: Agent success as a function of human task duration (1 min to 8+ h).
- Reported: Frontier agents 70-80% success on tasks <1 h human time; <20% on tasks >4 h.

### wijk2024rebench: RE-Bench (2024, METR)
- URL: https://arxiv.org/abs/2411.15114 (arXiv 2411.15114)
- Measures: Frontier AI R&D automation capability (an RSP/FSF AI R&D threshold proxy).
- Reported: Agents score 4x humans at 2 h budget; humans narrowly exceed agents at 8 h and 2x agents at 32 h; 82% of expert attempts non-zero, 24% match reference.

### zhang2024cybench: Cybench (2024, Stanford)
- URL: https://arxiv.org/abs/2408.08926 (arXiv 2408.08926)
- Measures: Offensive cyber capability of LLM agents (vulnerability discovery and exploitation).
- Reported: Top models (GPT-4o, Claude 3.5 Sonnet) solve tasks up to 11 min FST unguided; hardest task FST 24 h 54 min; FST range 2 min to 24.9 h. US AISI: o1 45% Pass@10 vs 35% best reference.

### li2024wmdp: WMDP (Weapons of Mass Destruction Proxy) (2024, Center for AI Safety / Scale AI)
- URL: https://arxiv.org/abs/2403.03218 (arXiv 2403.03218)
- Measures: Proxy for hazardous knowledge that could uplift malicious actors; also a target for unlearning (RMU).
- Reported: RMU unlearning reduces WMDP accuracy toward chance while preserving MMLU; used in sandbagging studies as the held-out dangerous-capability eval.

### gotting2025vct: Virology Capabilities Test (VCT) (2025, SecureBio / Center for AI Safety)
- URL: https://arxiv.org/abs/2504.16137 (arXiv 2504.16137)
- Measures: Tacit and visual practical virology knowledge relevant to bioweapons uplift.
- Reported: Expert virologists 22.1% average within specialty (with internet); o3 43.8%, outperforming 94% of experts.

### laurent2024labbench: LAB-Bench (2024, FutureHouse)
- URL: https://arxiv.org/abs/2407.10362 (arXiv 2407.10362)
- Measures: Practical biology research assistance capability; used by UK/US AISI as a bio capability probe.
- Reported: Frontier models below human experts on most subtasks in 2024; AISI Sonnet 3.5 report: below human baselines except with bioinformatic tools.

### ivanov2024biolp: BioLP-bench (2024, Independent (I. Ivanov))
- URL: https://www.biorxiv.org/content/10.1101/2024.08.21.608694v4
- Measures: Understanding of biological lab protocols (a wet-lab tacit-knowledge proxy used in AISI bio evaluations).
- Reported: Only o1-preview scored similarly to human experts; most models could not identify the error.
- Notes: bioRxiv preprint; size figure from secondary summary.

### phuong2024dangerous: DeepMind dangerous capability evaluations (Gemini 1.0) (2024, Google DeepMind)
- URL: https://arxiv.org/abs/2403.13793 (arXiv 2403.13793)
- Measures: Whether a frontier model has dangerous capabilities in four domains; pilot of a 'science of dangerous capability evaluation'.
- Reported: No strong dangerous capabilities in Gemini 1.0; 'early warning signs'.

### kinniment2023ara: METR ARA evaluations (autonomous replication and adaptation) (2023, METR (then ARC Evals))
- URL: https://arxiv.org/abs/2312.11671 (arXiv 2312.11671)
- Measures: Autonomous replication and adaptation capability; early template for autonomy thresholds in RSP/Preparedness.
- Reported: Agents completed only the easiest tasks; partial progress on harder ones.

### bhatt2023cyberseceval: CyberSecEval (Purple Llama) (2023, Meta)
- URL: https://arxiv.org/abs/2312.04724 (arXiv 2312.04724)
- Measures: Insecure code generation rate and compliance with cyberattack assistance requests.
- Reported: More capable models tend to suggest more insecure code; 7 models tested.

### anurin2024threecb: 3CB: Catastrophic Cyber Capabilities Benchmark (2024, Apart Research)
- URL: https://arxiv.org/abs/2410.09114 (arXiv 2410.09114)
- Measures: Offensive cyber capability of agents (reconnaissance, exploitation).
- Reported: GPT-4o and Claude 3.5 Sonnet perform offensive tasks; smaller open models limited.

### zhang2025bountybench: BountyBench (2025, Stanford)
- URL: https://arxiv.org/abs/2505.15216 (arXiv 2505.15216)
- Measures: Dollar-denominated offensive and defensive cyber capability on real systems.
- Reported: Best: Detect 12.5% ($3,720), Exploit 67.5% (Claude 3.7 Sonnet Thinking), Patch 90% ($14,152-$14,422); bounties $10-$30,485.

### chan2024mlebench: MLE-bench (2024, OpenAI)
- URL: https://arxiv.org/abs/2410.07095 (arXiv 2410.07095)
- Measures: ML engineering capability (AI R&D threshold proxy in Preparedness Framework).
- Reported: o1-preview + AIDE reaches bronze in 16.9% of competitions.

### starace2025paperbench: PaperBench (2025, OpenAI)
- URL: https://arxiv.org/abs/2504.01848 (arXiv 2504.01848)
- Measures: AI research replication ability (AI R&D threshold proxy).
- Reported: Claude 3.5 Sonnet 21.0% replication score; below top ML PhD baseline.

### swebench2024verified: SWE-bench Verified (2024, OpenAI / Princeton)
- URL: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified
- Measures: Real-world software engineering capability; used as capability proxy in RSP/Preparedness autonomy evaluations and CAISI comparisons.
- Reported: Used by CAISI (US model solves >20% more tasks than best DeepSeek); Anthropic RSP uses a 42-task >1 h subset with 50% pass-rate threshold.
- Notes: openai.com returns 403 to fetchers; annotator counts are from memory of the post and flagged medium confidence.

### kutasov2025shade: SHADE-Arena (2025, Anthropic / Scale AI / Redwood)
- URL: https://arxiv.org/abs/2506.15740 (arXiv 2506.15740)
- Measures: Sabotage capability and monitorability of agents.
- Reported: Claude 3.7 Sonnet 27% sabotage success; Gemini 2.5 Pro 15%; best monitor (Gemini 2.5 Pro) AUC 0.87.
- Notes: Author list partially reconstructed; verify before citing.

### meinke2024scheming: Apollo in-context scheming evaluations (2024, Apollo Research)
- URL: https://arxiv.org/abs/2412.04984 (arXiv 2412.04984)
- Measures: Capability for in-context scheming (deception, oversight subversion).
- Reported: o1 maintains deception in >85% of follow-up questions; chain-of-thought shows explicit scheming reasoning.

### ren2025mask: MASK: honesty benchmark (2025, Center for AI Safety / Scale AI)
- URL: https://arxiv.org/abs/2503.03750 (arXiv 2503.03750)
- Measures: Propensity to lie under pressure, disentangled from factual accuracy.
- Reported: Claude 3.7 Sonnet 26.6% lying rate; GPT-4o 44.5%; scale does not improve honesty.

### benton2024sabotage: Anthropic sabotage evaluations (2024, Anthropic)
- URL: https://arxiv.org/abs/2410.21514 (arXiv 2410.21514)
- Measures: Whether a model could covertly sabotage evaluations, monitoring or deployment decisions.
- Reported: Code-sabotage attacker win rate 26.6% vs Opus 3 defender, 7.8% vs Sonnet 3.5; sandbagged dangerous-capability performance 36.1% of baseline recovering to 95.6% after anti-refusal training.
- Notes: Full author list abbreviated.

### greenblatt2024alignmentfaking: Alignment faking (2024, Anthropic / Redwood Research)
- URL: https://arxiv.org/abs/2412.14093 (arXiv 2412.14093)
- Measures: Whether a model selectively complies during perceived training (alignment faking).
- Reported: 14% harmful compliance for free-tier vs almost 0% paid-tier; alignment-faking reasoning in almost all such cases; rises to 78% after RL training.

### anthropic2025agenticmisalignment: Agentic misalignment (blackmail scenarios) (2025, Anthropic)
- URL: https://www.anthropic.com/research/agentic-misalignment
- Measures: Propensity for harmful insider-like actions (blackmail, espionage) under contrived pressure.
- Reported: Blackmail rates: Claude Opus 4 96%, Gemini 2.5 Flash 96%, GPT-4.1 80%, Grok 3 80%, DeepSeek-R1 79%.

### schoen2025antischeming: Anti-scheming training stress test (OpenAI/Apollo) (2025, OpenAI / Apollo Research)
- URL: https://arxiv.org/abs/2509.15541 (arXiv 2509.15541)
- Measures: Whether deliberative alignment reduces covert actions, and how evaluation awareness confounds the measurement.
- Reported: o3 covert action rate 13% -> 0.4%; awareness of being evaluated causally decreases covert behaviour, unawareness increases it.
- Notes: Author list abbreviated.

### anthropic2025petri: Petri: automated alignment auditing tool (2025, Anthropic)
- URL: https://www.anthropic.com/research/petri-open-source-auditing
- Measures: Broad misaligned-behaviour propensity; reused by UK AISI for sabotage case study.
- Reported: Claude Sonnet 4.5 lowest misaligned-behaviour score, narrowly ahead of GPT-5; all models showed some misaligned behaviour.

### marks2025hiddenobjectives: Auditing for hidden objectives (blind auditing game) (2025, Anthropic)
- URL: https://arxiv.org/abs/2503.10965 (arXiv 2503.10965)
- Measures: Detectability of hidden objectives by auditing (sensitivity of audits).
- Reported: 3 of 4 teams found the hidden objective.

### lindner2026gram: Gram: automated sabotage-propensity auditing (2026, Google DeepMind)
- URL: https://arxiv.org/abs/2605.30322 (arXiv 2605.30322)
- Measures: Sabotage propensity of Gemini agents.
- Reported: ~2-3% misbehaviour rate; drops to near zero when realism increased and nudges removed.
- Notes: Author list truncated.

### souly2026aisicase: UK AISI alignment evaluation case study (2026, UK AI Security Institute)
- URL: https://arxiv.org/abs/2604.00788 (arXiv 2604.00788)
- Measures: Whether frontier models sabotage safety research as coding assistants; also measures eval-vs-deployment distinguishability.
- Reported: No confirmed research sabotage; Opus 4.5 Preview and Sonnet 4.5 frequently refuse safety-relevant tasks.
- Notes: Author list truncated.

### mazeika2024harmbench: HarmBench (2024, Center for AI Safety / UIUC)
- URL: https://arxiv.org/abs/2402.04249 (arXiv 2402.04249)
- Measures: Robust refusal under automated jailbreaks; standardised comparison of red-teaming methods.
- Reported: Classifier agreement with human labels 93.19% (vs GPT-4 88.37%, AdvBench 69.93%).

### souly2024strongreject: StrongREJECT (2024, UC Berkeley)
- URL: https://arxiv.org/abs/2402.10260 (arXiv 2402.10260)
- Measures: Jailbreak effectiveness measured as useful harmful information, not surface compliance.
- Reported: Spearman vs human labels 0.846 (rubric) / 0.900 (fine-tuned); MAE 0.077-0.084; prior evaluators overstate jailbreak success.

### andriushchenko2024agentharm: AgentHarm (2024, UK AISI / Gray Swan / EPFL)
- URL: https://arxiv.org/abs/2410.09024 (arXiv 2410.09024)
- Measures: Harmfulness and jailbreak robustness of LLM agents.
- Reported: Leading LLMs 'surprisingly compliant' without jailbreaks; simple templates jailbreak agents while preserving capability.

### chao2024jailbreakbench: JailbreakBench (2024, UPenn / ETH / others)
- URL: https://arxiv.org/abs/2404.01318 (arXiv 2404.01318)
- Measures: Jailbreak attack and defence performance under a standard threat model.
- Reported: Judge chosen against 300 human-labelled examples (agreement numbers in full paper).

### debenedetti2024agentdojo: AgentDojo (2024, ETH Zurich)
- URL: https://arxiv.org/abs/2406.13352 (arXiv 2406.13352)
- Measures: Prompt-injection robustness of tool-using agents (targeted attack success and utility under attack).
- Reported: SOTA LLMs fail many tasks even without attack; attacks break some security properties.

### rottger2023xstest: XSTest (exaggerated safety) (2023, Bocconi / Oxford)
- URL: https://arxiv.org/abs/2308.01263 (arXiv 2308.01263)
- Measures: False-refusal rate (specificity) alongside unsafe compliance (sensitivity).
- Reported: Systematic exaggerated-safety failures in SOTA models (rates in full paper).

### xie2024sorrybench: SORRY-Bench (2024, Princeton / others)
- URL: https://arxiv.org/abs/2406.14598 (arXiv 2406.14598)
- Measures: Fine-grained safety refusal behaviour.
- Reported: Fine-tuned 7B judges match GPT-4-scale accuracy at lower cost.

### cui2024orbench: OR-Bench (over-refusal) (2024, UCLA / others)
- URL: https://arxiv.org/abs/2405.20947 (arXiv 2405.20947)
- Measures: Over-refusal (false-alarm) rate vs true refusal across 32 LLMs.
- Reported: none stated

### ghosh2025ailuminate: AILuminate v1.0 (2025, MLCommons)
- URL: https://arxiv.org/abs/2503.05731 (arXiv 2503.05731)
- Measures: Product-level risk and reliability grade for chat systems (industry standard benchmark).
- Reported: Grades per system; authors note evaluator uncertainty and single-turn limits.

### parrish2021bbq: BBQ: Bias Benchmark for QA (2021, NYU)
- URL: https://arxiv.org/abs/2110.08193 (arXiv 2110.08193)
- Measures: Reliance on social stereotypes in QA; used in many model cards (e.g. Anthropic).
- Reported: Up to 3.4 pp higher accuracy when correct answer aligns with a stereotype; >5 pp for gender.

### lin2021truthfulqa: TruthfulQA (2021, Oxford / OpenAI)
- URL: https://arxiv.org/abs/2109.07958 (arXiv 2109.07958)
- Measures: Imitative falsehoods; a widely used honesty proxy (MASK shows it does not track lying under pressure).
- Reported: Best model 58% truthful vs humans 94%; larger models less truthful.

### aisi2024sonnet: US/UK AISI joint pre-deployment test: Claude 3.5 Sonnet (upgraded) (2024, UK AISI / US AISI (NIST))
- URL: https://www.aisi.gov.uk/blog/pre-deployment-evaluation-of-anthropics-upgraded-claude-3-5-sonnet
- Measures: Pre-deployment capability in bio, cyber, software/AI development and safeguard efficacy.
- Reported: US cyber 32.5% vs 35% best reference; UK apprentice-level cyber 36% vs 29%; UK SWE 66% vs 64%; bio below human expert baselines except with bioinformatics tools.

### aisi2024o1: US/UK AISI joint pre-deployment test: OpenAI o1 (2024, UK AISI / US AISI (NIST))
- URL: https://dpo-india.com/Resources/NIST/US-AISI1-UK-AISI2-Joint-Pre-Deployment-Test-OpenAIo1.pdf
- Measures: Pre-deployment cyber, bio, software/AI development capability of o1.
- Reported: o1 45% Pass@10 (35% Pass@1) vs 35%/30% for best reference; UK technical non-expert 79% vs 90%; apprentice 46% vs 46%.
- Notes: Fetched from a third-party mirror of the NIST PDF; NIST original not fetched.

### caisi2025deepseek: CAISI evaluation of DeepSeek models (2025, US CAISI (NIST))
- URL: https://www.nist.gov/news-events/news/2025/09/caisi-evaluation-deepseek-ai-models-finds-shortcomings-and-risks
- Measures: Capability, cost, security and censorship comparison of DeepSeek R1/R1-0528/V3.1 vs GPT-5, GPT-5-mini, gpt-oss, Opus 4.
- Reported: R1-0528 12x more likely to follow malicious agent-hijack instructions; responds to 94% of malicious jailbreak requests vs 8% for US models; US model 35% cheaper at equal performance; >20% more SWE tasks solved.

### aisi2025trends: UK AISI Frontier AI Trends Report (2025, UK AI Security Institute)
- URL: https://www.aisi.gov.uk/frontier-ai-trends-report
- Measures: Trends in frontier capability and safeguard robustness across 30+ systems.
- Reported: Cyber task horizon doubling ~8 months; apprentice-level cyber success <10% (early 2024) to ~50% (2025); hour-long SWE tasks >40%; universal jailbreaks found for every system.

### aisi2024inspect: Inspect AI evaluation framework (2024, UK AI Security Institute)
- URL: https://github.com/UKGovernmentBEIS/inspect_ai
- Measures: Infrastructure used by AISI, CAISI and labs to run agentic and QA evaluations reproducibly.
- Reported: none stated

### anthropic2025opus4card: Claude Opus 4 system card: bioweapons acquisition uplift trial (2025, Anthropic)
- URL: https://www-cdn.anthropic.com/6be99a52cb68eb70eb9572b4cafad13df32ed995.pdf
- Measures: Real human uplift for the ASL-3 CBRN threshold (deployment gate).
- Reported: Control 25% +/- 13%; Opus 4 63% +/- 13% (2.53x); Sonnet 4 42% +/- 11% (1.70x); Sonnet 3.7 1.53x; all participants hit critical failures; thresholds: >=5x total uplift = significant risk, <=2.8x acceptable; Opus 4 'unable to rule out ASL-3'.

### anthropic2025opus45card: Claude Opus 4.5 system card: uplift trials, eval awareness, alignment audit effort (2025, Anthropic)
- URL: https://www.anthropic.com/claude-opus-4-5-system-card
- Measures: ASL-3/4 CBRN and AI R&D threshold checks; alignment and evaluation-awareness assessment.
- Reported: Uplift 1.97x raw protocol score vs internet-only (secondary source); Opus 4.5 uplift-trial mean 0.668; 9/18 staff report >=100% productivity gain, none think junior-ML-researcher automation reached; steering down eval awareness increased misaligned behaviour only slightly.
- Notes: Fetched as PDF via curl (12 MB). 1.97x figure from search snippet, not verified in text.

### anthropic2025sonnet45card: Claude Sonnet 4.5 system card: evaluation awareness (2025, Anthropic)
- URL: https://www.anthropic.com/claude-sonnet-4-5-system-card
- Measures: Alignment propensities and the confound of evaluation awareness.
- Reported: Realism filter reduced eval awareness ~25% and increased measured misaligned behaviour ~5%; even worst-case awareness inhibition left Sonnet 4.5 no worse than Opus 4.1/Sonnet 4; verbalized awareness rose 20%->80% over training on a honeypot eval (Redwood summary).
- Notes: Fetched as PDF via curl (13 MB).

### pan2025evalgaming: Sonnet 4.5's eval gaming undermines alignment evals (Redwood analysis) (2025, Redwood Research)
- URL: https://blog.redwoodresearch.org/p/sonnet-45s-eval-gaming-seriously
- Measures: How much of measured alignment improvement is attributable to evaluation gaming.
- Reported: Verbalized eval awareness 80-100% (Sonnet 4.5) vs <10% (Sonnet 4) on synthetic honeypots; 10-15% vs 1-3% on behavioural audits; inhibiting awareness raised misaligned behaviour 0% -> 1-9%; authors estimate >=25% (worst case ~90%) of behavioural gains are eval gaming.

### mouton2024randbio: RAND red-team study: LLMs and biological attack planning (2024, RAND)
- URL: https://www.rand.org/pubs/research_reports/RRA2977-2.html
- Measures: Operational uplift from LLM access for bioweapon attack planning.
- Reported: No statistically significant difference in plan viability with vs without LLMs; LLM outputs mirrored internet-available information.
- Notes: Page fetched via curl (WebFetch 403). Cell counts not on landing page.

### openai2024bioearlywarning: OpenAI early-warning system for LLM-aided biological threat creation (2024, OpenAI)
- URL: https://openai.com/index/building-an-early-warning-system-for-llm-aided-biological-threat-creation/
- Measures: Uplift from model access on biological threat creation tasks (Preparedness Framework bio category).
- Reported: Mild uplift in accuracy and completeness, not statistically significant at the study's size.
- Notes: openai.com returned HTTP 403 to all fetch attempts; numbers are from memory of the post and must be checked before citing.

### becker2025productivity: METR developer productivity RCT (2025, METR)
- URL: https://arxiv.org/abs/2507.09089 (arXiv 2507.09089)
- Measures: Real-world impact of AI tools on expert developer productivity (a level-9 ground truth against which benchmark claims can be checked).
- Reported: 19% slowdown with AI; developers predicted 20% speedup, experts 38-39%.

### vanderweij2024sandbagging: AI sandbagging (2024, Independent / Apollo)
- URL: https://arxiv.org/abs/2406.07358 (arXiv 2406.07358)
- Measures: Feasibility of strategic underperformance on dangerous-capability evals (a sensitivity threat).
- Reported: GPT-4 and Claude 3 Opus can be prompted to selectively sandbag; password-locked models hide capabilities and can target specific scores.

### tice2024noise: Noise injection reveals sandbagging (2024, Independent / Apart)
- URL: https://arxiv.org/abs/2412.01784 (arXiv 2412.01784)
- Measures: Model-agnostic detector for sandbagging.
- Reported: Elicited full performance from Mistral Large 120B underperforming without instruction; works across sizes and sandbagging techniques.

### needham2025evalaware: LLMs often know when they are being evaluated (2025, MATS / Apollo Research)
- URL: https://arxiv.org/abs/2505.23836 (arXiv 2505.23836)
- Measures: Evaluation awareness (ability to distinguish test from deployment).
- Reported: Gemini 2.5 Pro AUC 0.83; human baseline 0.92; agentic settings easier to detect than chat.
- Notes: Author list truncated.

### li2026evalawaredecomp: Decomposing and measuring evaluation awareness (EvalAwareBench) (2026, Academic)
- URL: https://arxiv.org/abs/2605.23055 (arXiv 2605.23055)
- Measures: Environment-driven vs model-driven evaluation awareness and whether it changes behaviour.
- Reported: Recognition varies by model-benchmark pair; recognition rarely changes behaviour; safety evals more sensitive than capability evals.
- Notes: Author list truncated.

### ren2024safetywashing: Safetywashing (2024, Center for AI Safety)
- URL: https://arxiv.org/abs/2407.21792 (arXiv 2407.21792)
- Measures: Whether safety benchmarks measure anything beyond capability.
- Reported: Many safety benchmarks highly correlated with capability (e.g. TruthfulQA, ETHICS); some (e.g. sycophancy, MASK-style) are not.

### bean2025constructvalidity: Measuring what matters: construct validity in LLM benchmarks (2025, Oxford / others)
- URL: https://arxiv.org/abs/2511.04703 (arXiv 2511.04703)
- Measures: Prevalence of construct-validity failures (vague phenomena, unrepresentative tasks, weak statistics).
- Reported: Patterns undermining validity found across phenomena, tasks and scoring; 8 recommendations.
- Notes: Author list truncated.

### reuel2024betterbench: BetterBench (2024, Stanford)
- URL: https://arxiv.org/abs/2411.12990 (arXiv 2411.12990)
- Measures: Benchmark quality (design, implementation, documentation, maintenance).
- Reported: Large quality differences; most benchmarks do not report statistical significance; replicability poor.

### singh2025leaderboard: The Leaderboard Illusion (2025, Cohere / others)
- URL: https://arxiv.org/abs/2504.20879 (arXiv 2504.20879)
- Measures: Selection and overfitting distortions in a human-preference leaderboard.
- Reported: Meta tested 27 private variants pre-Llama-4; Google/OpenAI ~20% of arena data each vs 83 open models 30%; extra data gives up to 112% relative gain.

### miller2024errorbars: Adding error bars to evals (2024, Anthropic)
- URL: https://arxiv.org/abs/2411.00640 (arXiv 2411.00640)
- Measures: How to report uncertainty and size evals; enables sample-size (cost) planning.
- Reported: none stated

### weidinger2025evalscience: Toward an evaluation science for generative AI (2025, Google DeepMind / others)
- URL: https://arxiv.org/abs/2503.05336 (arXiv 2503.05336)
- Measures: Argues static benchmarks lack validity, audits do not scale; borrows from transport, aerospace and pharma safety evaluation.
- Reported: none stated

### shevlane2023extreme: Model evaluation for extreme risks (2023, Google DeepMind / others)
- URL: https://arxiv.org/abs/2305.15324 (arXiv 2305.15324)
- Measures: Frames dangerous-capability and alignment evaluations as inputs to training/deployment decisions; origin of the RSP/Preparedness paradigm.
- Reported: none stated

### barrett2024benchmarkearly: Benchmark early and red team often (2024, UC Berkeley CLTC)
- URL: https://arxiv.org/abs/2405.10986 (arXiv 2405.10986)
- Measures: Two-tier evaluation economics: cheap open benchmarks screen; costly closed expert red teams confirm; assumes correlation between tiers.
- Reported: none stated

### buhl2024safetycases: Safety cases for frontier AI (2024, UK AISI / GovAI)
- URL: https://arxiv.org/abs/2410.21572 (arXiv 2410.21572)
- Measures: Proposes structured safety cases (as in aviation, nuclear) with evaluations as evidence; notes current evals are not yet mature enough to drive decisions.
- Reported: none stated

### mccaslin2025stream: STREAM (ChemBio) reporting standard (2025, METR / others)
- URL: https://arxiv.org/abs/2508.09853 (arXiv 2508.09853)
- Measures: Transparency of eval reporting so third parties can judge rigor.
- Reported: none stated

### ghosh2026evalcards: Evaluation Cards (2026, Hugging Face / EvalEval)
- URL: https://arxiv.org/abs/2606.09809 (arXiv 2606.09809)
- Measures: Gaps in evaluation reporting.
- Reported: none stated
- Notes: Author list truncated.

### ghosh2026evalcosts: AI evals are becoming the new compute bottleneck (2026, EvalEval Coalition / Hugging Face)
- URL: https://huggingface.co/blog/evaleval/eval-costs-bottleneck
- Measures: Dollar and GPU-hour cost of running benchmarks; reliability multipliers.
- Reported: HAL $40k for 21,730 rollouts; GAIA single run up to $2,829; Online Mind2Web $171-$1,577 per run (9x spread); MLE-bench ~$5,500/seed; PaperBench ~$9,500/run; HELM (2022) $85-$10,926 API per model or 540-4,200 GPU-h; 8-seed reliability multiplies cost ~8x (HAL $40k -> $320k).

### kapoor2025hal: Holistic Agent Leaderboard (HAL) (2025, Princeton)
- URL: https://arxiv.org/abs/2510.11977 (arXiv 2510.11977)
- Measures: Agent accuracy vs cost; behavioural issues in logs.
- Reported: ~$40,000 total; higher reasoning effort reduced accuracy in most runs.
- Notes: Author list truncated.

### metr2026horizonlimits: METR: clarifying limitations of time horizon (2026, METR)
- URL: https://metr.org/notes/2026-01-22-time-horizon-limitations/
- Measures: Stated limits of the time-horizon metric.
- Reported: ~170 tasks; error bars ~2x each direction; unreliable above 16 h; few real baselines for 2 h+ tasks.

### anthropic2026rsp: Anthropic Responsible Scaling Policy (v3.4) (2026, Anthropic)
- URL: https://www.anthropic.com/responsible-scaling-policy
- Measures: Deployment gate: thresholds trigger safeguards; comprehensive assessment every 6 months (was 3) to allow higher-quality elicitation.
- Reported: v3.4 effective 8 Jul 2026; Opus 4 uplift trial threshold 2.8x/5x; sabotage risk reports for models exceeding prior capability.

### openai2025preparedness: OpenAI Preparedness Framework v2 (2025, OpenAI)
- URL: https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf
- Measures: Deployment gate: High capability requires sufficient safeguards before deployment; Critical during development.
- Reported: 15 Apr 2025; any one-time elicitation treated as a lower bound; sandbagging listed as a research category with mitigation 'overcome sandbagging or use conservative upper bound'.

### deepmind2026fsf: Google DeepMind Frontier Safety Framework (v3.1) (2026, Google DeepMind)
- URL: https://deepmind.google/blog/strengthening-our-frontier-safety-framework/
- Measures: Deployment gate keyed to alert thresholds reached before CCLs.
- Reported: v3.1 dated 17 Apr 2026; 5 CCLs + 2 Tracked Capability Levels.

### deepmind2025gemini3fsf: Gemini 3 Pro Frontier Safety Framework report (2025, Google DeepMind)
- URL: https://storage.googleapis.com/deepmind-media/gemini/gemini_3_pro_fsf_report.pdf
- Measures: Whether Gemini 3 Pro reached any CCL.
- Reported: Cyber: 11/12 v1 hard solved, 0/13 v2 end-to-end, alert threshold met, CCL not reached; ML R&D below alert threshold; 3/11 situational awareness, 1/4 stealth; CBRN alert threshold not reached.

### bengio2025intlreport: International AI Safety Report 2025 (2025, UK DSIT (international panel))
- URL: https://arxiv.org/abs/2501.17805 (arXiv 2501.17805)
- Measures: State of evidence on capabilities, risks and evaluation limits.
- Reported: none stated
- Notes: Abstract only; evaluation-limits chapter not extracted.

### sermanet2025asimov: ASIMOV benchmark and robot constitutions (2025, Google DeepMind Robotics)
- URL: https://arxiv.org/abs/2503.08663 (arXiv 2503.08663)
- Measures: Semantic (common-sense) safety of VLM/robot policies; bridges LLM safety evals and embodied safety.
- Reported: Top alignment rate 84.3% with auto-generated constitutions, above human-written constitutions and no-constitution baselines.
- Speaker link: Sindhwani

### jindal2025danger: Can AI perceive physical danger and intervene? (2025, Google DeepMind Robotics)
- URL: https://arxiv.org/abs/2509.21651 (arXiv 2509.21651)
- Measures: Physical-safety perception and intervention reasoning of foundation models for embodied use.
- Reported: Post-trained models reach state-of-the-art constraint satisfaction (numbers in paper).
- Speaker link: Sindhwani
