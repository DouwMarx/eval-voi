# Scenario drafts: consistency pass (2026-10-01)

39 files in research/scenarios_draft/. Checks: schema and parsing; group labels; physical-AI level and risk_domain; respond-vs-deploy decisions with a developer-side agent; theta as a hazardous property; construct overlap; citation and source-cache integrity; DESIGN section 2 terminology; title uniqueness and length; separation of the two facts blocks.

Cost fact: yes = a USD or hour figure for building or running the evaluation; partial = only a time, hardware, token or relative-cost figure; no = the block states that no cost figure is published. Validity fact: yes = at least one judge-agreement, human-baseline, correlation, saturation, shortcut, contamination or documented-failure-mode statement.

| key | group | risk_domain | level | system under test | title | words decision/instrument | n sources | cost fact | validity fact |
|---|---|---|---|---|---|---|---|---|---|
| abcbench | frontier model | cbrn |  | agentic LLM | ABC-Bench before a frontier model release | 249/250 | 7 | yes | yes |
| agentharm | frontier model | societal_harm |  | agentic LLM | AgentHarm before the tool-calling API launch | 242/250 | 6 | yes | yes |
| agentic_misalignment | frontier model | loss_of_control |  | agentic LLM | Agentic Misalignment before the autonomous email-agent release | 244/248 | 12 | no | yes |
| asimov2 | physical AI | physical_harm | 3 | LLM or VLM inside a robot | ASIMOV-2.0 before shipping a VLM robot planner | 244/250 | 5 | no | yes |
| asimov_agentic | physical AI | physical_harm | 2 | LLM or VLM inside a robot | ASIMOV-Agentic before the humanoid orchestrator release | 248/245 | 10 | no | yes |
| bbq | frontier model | societal_harm |  | LLM | BBQ demographic-bias evaluation before releasing a general-purpose assistant model | 250/249 | 9 | yes | yes |
| binary_exploitation | frontier model | cyber |  | agentic LLM | Binary Exploitation Benchmark before general release of a frontier model | 247/250 | 10 | no | yes |
| biotier | frontier model | cbrn |  | LLM | BioTIER before the general-access launch of a biology-capable assistant | 249/250 | 7 | no | yes |
| bloom | frontier model | loss_of_control |  | agentic LLM | Bloom self-preservation evaluation before an autonomous-agent release | 249/246 | 12 | no | yes |
| controlarena | frontier model | loss_of_control |  | agentic LLM | ControlArena before the privileged internal agent deployment | 249/240 | 12 | partial | yes |
| cvebench | frontier model | cyber |  | agentic LLM | CVE-Bench before releasing an agentic coding model | 248/248 | 9 | yes | yes |
| cybench | frontier model | cyber |  | agentic LLM | Cybench before deploying a frontier agentic coding model | 240/248 | 12 | no | yes |
| cyber_range | frontier model | cyber |  | agentic LLM | End-to-end cyber range before lifting autonomous cyber-operations restrictions | 249/247 | 15 | yes | yes |
| cybergym | frontier model | cyber |  | agentic LLM | CyberGym vulnerability reproduction before the general release of an agentic model | 250/250 | 15 | yes | yes |
| cyscenariobench | frontier model | cyber |  | agentic LLM | CyScenarioBench multi-stage attack scenarios before a frontier model's general release | 246/231 | 15 | partial | yes |
| deceptionbench | frontier model | harmful_manipulation |  | LLM | DeceptionBench third-party deception before a consumer assistant launch | 236/247 | 8 | no | yes |
| egosafetybench | physical AI | physical_harm | 3 | LLM or VLM inside a robot | EgoSafetyBench before the VLM safety-guard release | 247/247 | 8 | no | yes |
| exploitbench | frontier model | cyber |  | agentic LLM | ExploitBench before the general release of a frontier model | 247/249 | 16 | yes | yes |
| exploitgym | frontier model | cyber |  | agentic LLM | ExploitGym before general release of a frontier agentic model | 247/248 | 8 | yes | yes |
| fortress | frontier model | societal_harm |  | LLM | FORTRESS before the flagship chat model launch | 248/250 | 10 | yes | yes |
| harmbench | frontier model | societal_harm |  | LLM | HarmBench before the public chat model launch | 212/250 | 5 | partial | yes |
| hpct | frontier model | cbrn |  | LLM | Human Pathogen Capabilities Test before releasing a frontier model | 248/247 | 9 | no | yes |
| humanoid_orchestrator | physical AI | physical_harm | 0 | LLM or VLM inside a robot | LLM-orchestrator safety evaluation before deploying a humanoid in a shared cell | 237/250 | 6 | partial | yes |
| iihs_paeb | physical AI | physical_harm | 8 | non-learning physical system | IIHS pedestrian AEB track protocol before releasing a new AEB calibration | 249/246 | 11 | yes | yes |
| isbench | physical AI | physical_harm | 4 | LLM or VLM inside a robot | IS-Bench interactive household safety before the home-robot assistant launch | 246/248 | 7 | partial | yes |
| iso10218_pfl | physical AI | physical_harm | 7 | non-learning physical system | ISO 10218 power-and-force-limiting contact test before releasing a collaborative cell | 246/250 | 10 | yes | yes |
| labbench_bio | frontier model | cbrn |  | LLM | LAB-Bench bio subset before a frontier model release | 250/245 | 8 | yes | yes |
| maniguard | physical AI | physical_harm | 7 | VLA policy | ManiGuard-Bench before a household VLA manipulation policy release | 243/242 | 8 | partial | yes |
| mask | frontier model | harmful_manipulation |  | LLM | MASK honesty under pressure before launching a consumer assistant | 249/248 | 7 | no | yes |
| petri | frontier model | harmful_manipulation |  | LLM | Petri alignment audit before the consumer assistant launch | 244/249 | 11 | partial | yes |
| redvla | physical AI | physical_harm | 4 | VLA policy | RedVLA physical red teaming before a VLA manipulation policy release | 240/250 | 8 | partial | yes |
| robopair | physical AI | physical_harm | 7 | LLM or VLM inside a robot | RoboPAIR jailbreak red-teaming before the LLM voice-command release | 245/249 | 9 | partial | yes |
| safeagentbench | physical AI | physical_harm | 4 | LLM or VLM inside a robot | SafeAgentBench before a home-robot LLM planner launch | 250/250 | 7 | partial | yes |
| safeplan | physical AI | physical_harm | 0 | LLM or VLM inside a robot | SafePlan prompt suite before launching an LLM command interface on a service robot | 249/249 | 8 | no | yes |
| shade_arena | frontier model | loss_of_control |  | agentic LLM | SHADE-Arena before the autonomous agent launch | 249/249 | 11 | partial | yes |
| strongreject | frontier model | societal_harm |  | LLM | StrongREJECT before the public chat model launch | 247/250 | 9 | yes | yes |
| vct | frontier model | cbrn |  | VLM | Virology Capabilities Test before releasing a frontier model | 246/249 | 5 | yes | yes |
| veo_worldmodel | physical AI | physical_harm | 5 | VLA policy | Veo world-model safety probing before releasing a VLA checkpoint | 241/250 | 7 | no | yes |
| wmdp | frontier model | cbrn |  | LLM | WMDP hazardous-knowledge screen before an open-weights release | 246/245 | 14 | yes | yes |

## Results of the checks

1. All 39 files parse, carry every schema field, and use the group labels 'frontier model' (26) or 'physical AI' (13). Every physical-AI entry has an integer level in 0-8 and risk_domain physical_harm; every frontier-model entry has level null.
2. Every decision starts with 'Delay ...' and names a concrete mitigation before 'vs <release> as planned'. The agent is a developer-side decision-maker in 36 of 39 scenarios. Exceptions: humanoid_orchestrator (head of robotics engineering at a system integrator) and iso10218_pfl (safety engineer at a robot system integrator): ISO 10218-2:2025 places the application-level release decision and the power-and-force-limiting assessment on the integrator, not on the robot or LLM developer, so the integrator is the party who can delay. iihs_paeb names a vehicle manufacturer: the OEM develops and releases the AEB calibration, so it is the developer of the system under test.
3. Every theta_definition states a present-or-absent hazardous property of the system under test, not a score. petri's property is defined relative to the developer's current production model (a rate 'materially above' it); this is still a property of the candidate, kept as is.
4. Construct overlap: see merge candidates below. No merges were made.
5. Every [key] cited in a facts block exists in that file's sources; every sources entry has research/sources/<key>.json with key, kind, ref, url, title, fetched, abstract, text and chars, and text longer than 200 characters. Every source is cited at least once. No citation was dropped.
6. Terminology: prose uses of 'benchmark', 'gate', 'gated' and 'rung' were replaced (list below). Remaining occurrences are inside source titles and URLs (paper titles such as 'ExploitBench: A Capability Ladder Benchmark', 'Pre-Execution Safety Gate', securebio.org/benchmarks/...) and the proper name 'Binary Exploitation Benchmark', which Anthropic uses as the evaluation's name.
7. All 39 titles are unique and under 90 characters (longest: 84).
8. Separation rule: one violation found and fixed (harmbench decision_facts described item construction). Decision blocks that quote mitigation costs (classifier overhead, refusal increases, monitoring cost) were kept: they describe the cost of responding, which the decision prompt needs. Instrument blocks that quote model scores were kept: they are run results, not stakes.

## Edits made

- asimov_agentic: instrument_facts: 'benchmarks' -> 'evaluations'
- asimov_agentic: instrument_facts: 'gated' -> 'access-restricted'
- asimov_agentic: source title: 'gated' -> 'access-restricted'
- biotier: decision_facts: 'gate on' -> 'condition releases on'
- biotier: instrument_facts: 'benchmark-aware' -> 'evaluation-aware'
- bloom: instrument_facts: 'benchmark' -> 'evaluation'
- bloom: instrument_facts: 'benchmarks' -> 'evaluations'
- agentic_misalignment: decision_facts: 'benchmark archive' -> 'evaluation-data archive'
- binary_exploitation: instrument_facts: 'benchmark' -> 'evaluation'
- egosafetybench: instrument_facts: 'benchmark labels' -> 'dataset labels'
- egosafetybench: instrument_facts: 'gated access' -> 'access-restricted download'
- exploitbench: instrument_facts: 'benchmark' -> 'evaluation'
- exploitgym: instrument_facts: 'benchmark' -> 'evaluation'
- harmbench: instrument_facts: 'benchmarks' -> 'evaluations'
- hpct: instrument_facts: 'benchmark' -> 'evaluation'
- humanoid_orchestrator: title: 'benchmark' -> 'evaluation'
- humanoid_orchestrator: instrument: 'benchmark' -> 'evaluation'
- humanoid_orchestrator: instrument_facts: 'benchmark' -> 'evaluation'
- humanoid_orchestrator: decision_facts: 'US $13.5K' -> 'USD 13.5K'
- labbench_bio: eval_family: 'benchmark' -> 'evaluation'
- safeplan: instrument_facts: 'benchmark' -> 'prompt suite'
- safeplan: instrument_facts: 'benchmark' -> 'command set'
- safeplan: instrument_facts: 'benchmark' -> 'set'
- strongreject: instrument_facts: 'benchmark' -> 'evaluation'
- wmdp: instrument: 'benchmark' -> 'evaluation'
- wmdp: instrument_facts: 'benchmarks' -> 'question sets'
- controlarena: decision_facts trimmed 256 -> <=250 words (shortened Greenblatt sentence)
- controlarena: instrument_facts trimmed 259 -> <=250 words (dropped BashArena trajectory-length/score-resolution sentence)
- cyber_range: instrument_facts trimmed (dropped artefact-density clause)
- cyber_range: instrument_facts trimmed 256 -> <=250 words (compressed OpenAI Cyber Range sentence)
- cyscenariobench: instrument_facts trimmed 254 -> <=250 words (dropped score-span sentence duplicated in decision_facts)
- harmbench: decision_facts: removed sentence describing item construction/validity (Google-search solvability of contextual behaviours); moved to instrument_facts
- harmbench: instrument_facts: added the Google-search item-validity fact
- harmbench: instrument_facts: dropped R2D2 training-time clause (not the evaluation) to stay within 250 words
- agentic_misalignment: 2 '$N' figure(s) rewritten as 'USD N'
- bbq: 2 '$N' figure(s) rewritten as 'USD N'
- cvebench: 3 '$N' figure(s) rewritten as 'USD N'
- cybergym: 6 '$N' figure(s) rewritten as 'USD N'
- deceptionbench: 4 '$N' figure(s) rewritten as 'USD N'
- iihs_paeb: 6 '$N' figure(s) rewritten as 'USD N'
- safeagentbench: 3 '$N' figure(s) rewritten as 'USD N'
- safeplan: 2 '$N' figure(s) rewritten as 'USD N'
- wmdp: 2 '$N' figure(s) rewritten as 'USD N'
- bbq: trimmed to <=250 words: annotator-pay sentence
- bbq: trimmed to <=250 words: Anthropic BBQ-run sentence
- biotier: trimmed to <=250 words: 'condition releases on' -> 'respond to'
- biotier: trimmed to <=250 words: EU AI Act sentence
- controlarena: trimmed to <=250 words: opening sentence
- cvebench: trimmed to <=250 words: cost sentence
- cvebench: trimmed to <=250 words: limitations sentence
- cvebench: trimmed to <=250 words: OpenAI run sentence
- cybergym: trimmed to <=250 words: Fable 5 sentence
- cybergym: trimmed to <=250 words: Glasswing sentence
- cybergym: trimmed to <=250 words: Glasswing update sentence
- cybergym: trimmed to <=250 words: description-precision sentence
- cybergym: trimmed to <=250 words: harness revision sentence
- cybergym: trimmed to <=250 words: cutoff sentence
- harmbench: trimmed to <=250 words: repository sentence
- harmbench: trimmed to <=250 words: metric sentence
- harmbench: trimmed to <=250 words: Anthropic judge sentence
- iihs_paeb: trimmed to <=250 words: FMVSS 127 cost sentence
- iihs_paeb: trimmed to <=250 words: IIHS night ratings sentence
- iihs_paeb: trimmed to <=250 words: Mcity sentence
- iihs_paeb: trimmed to <=250 words: Euro NCAP sentence
- safeplan: trimmed to <=250 words: 1X NEO sentence
- safeplan: trimmed to <=250 words: annotator sentence
- safeplan: trimmed to <=250 words: SafeGate sentence
- cybergym: trimmed to <=250 words: 'GPU hours' -> 'GPU-hours'
- iihs_paeb: instrument_facts had no validity fact; replaced 'The protocol cites field studies of similar systems' and the duplicated 23-vehicle night-rating sentence with a field-outcome sentence citing cicchino2022 (role decision -> both); iihs_night2022 role both -> decision (now cited only in decision_facts)

## Unresolved issues

- Agent is a deployer rather than a developer in humanoid_orchestrator and iso10218_pfl (justified above); the protocol's `developer` perspective for B and K should be read as the integrator's exposure in those two scenarios.
- 13 scenarios have no published cost figure at all (agentic_misalignment, asimov2, asimov_agentic, binary_exploitation, biotier, bloom, cybench, deceptionbench, egosafetybench, hpct, mask, safeplan, veo_worldmodel); 11 more have only time, hardware, token or relative-cost figures. Elicitors will estimate C_build and C_run without an anchor in those cases.
- bloom's decision_facts rests almost entirely on the Agentic Misalignment hazard results that agentic_misalignment also uses; if both scenarios are kept, bloom needs hazard facts of its own.
- Primary sources are private or developer-internal for binary_exploitation, cyber_range (TLO), cyscenariobench, hpct, vct and veo_worldmodel; their instrument blocks rely on system-card sentences and third-party posts, as the schema allows.
- exploitbench decision_facts quotes the Fable 5.1 API price (USD 10 / 50 per million tokens); it is kept as a revenue-stakes fact but is the weakest-fitting sentence in that block.
- Three unedited files end with a trailing newline and the rest do not; cosmetic, untouched.

## Merge candidates (same construct, same kind of system; not merged)

1. agentic_misalignment and bloom: both test an agentic LLM for self-preservation actions (blackmail, data leaks) under replacement threat; bloom's instrument is a generator seeded with an Agentic Misalignment transcript and its hazard facts are the same study. Strongest candidate.
2. harmbench and strongreject: both test a chat LLM's robustness to standard jailbreak attacks with an LLM or classifier judge; thetas differ only in attack family wording.
3. cyber_range and cyscenariobench: both test whether an agentic LLM completes an end-to-end multi-stage network intrusion in an emulated enterprise network (UK AISI TLO vs Irregular's attack-tree scenarios).
4. exploitbench and exploitgym: both test N-day exploit development to code execution by an agentic LLM; ExploitGym's 185 V8 instances cover ExploitBench's whole target class.
5. hpct and vct: both test expert-level practical virology knowledge against PhD virologist baselines, built by SecureBio; they differ in modality (text vs image items) and pathogen scope.
6. controlarena and shade_arena: both test covert side-task completion by an agentic LLM while an LLM monitor's suspicion stays below threshold; they differ in setting (privileged sysadmin vs user-facing agent).
7. asimov_agentic and humanoid_orchestrator: both test an LLM orchestrator on a humanoid for protective-stop behaviour near people; they differ in fidelity (real sensor recordings, level 2, vs scripted synthetic sensor readings, level 0).
8. safeagentbench and safeplan: both test whether an LLM robot planner accepts hazardous natural-language commands instead of refusing; they differ in fidelity (executed in AI2-THOR, level 4, vs text classification, level 0).
9. redvla and veo_worldmodel: both test a VLA policy's unsafe handling of inserted hazard objects (knife grasps, contact with hands or fragile items); they differ in evaluator (simulator plus physical reproduction vs generative video world model).

Related but distinct (kept): asimov2 vs asimov_agentic (semantic QA vs orchestration); binary_exploitation vs cybergym (unknown-vulnerability discovery vs described-vulnerability reproduction); isbench vs safeagentbench (implicit process hazards vs explicit hazardous instructions); redvla vs maniguard (adversarial insertion vs nominal specification violations); deceptionbench vs mask (deceiving third parties vs lying about own beliefs); fortress vs harmbench (human-written national-security prompts with safeguards on vs automated attacks).
