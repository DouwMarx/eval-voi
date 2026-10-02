export const meta = {
  name: 'voi-scenarios-2026-10-01',
  description: 'Write the 39 study scenarios (26 frontier-model, 13 physical-AI) to the DESIGN section 5 schema with sourced decision and instrument facts, cache the fetched source texts, fact-check each adversarially, fix, then one cross-scenario consistency pass',
  phases: [
    { title: 'Write', detail: 'one writer per evaluation' },
    { title: 'Check', detail: 'adversarial fact-check per scenario, then fix' },
    { title: 'Consistency', detail: 'one pass over all 39' },
  ],
}
const REPO = '<repo>'
const BASE = `Repository ${REPO} (main checkout, branch iteration-2026-09-30; do not touch any worktree under .claude/worktrees). Read docs/DESIGN.md sections 2, 4 and 5 first. Inputs: research/candidates_frontier.json and .md (26 included frontier-model evaluations; each entry has name, domain, primary, decision, theta, cost, validity, problems, corpus counts), research/candidates_physical.json and .md (13 included physical-AI evaluations; catalog_key, level, primary_sources, proposed_decision, theta_definition, cost_facts, validity_facts, system_under_test), the pilot's 15 fact-checked scenarios in studies/ai-safety-evals/scenarios.json (if that path is gone, archive/pilots/ai-safety-evals/scenarios.json) and their factcheck.md, research/catalog.json (443 literature entries with abstracts and notes), research/system_card_snippets.json and the read-only system-card corpus <system-card corpus sqlite> (sqlite3 'file:...?mode=ro', uri=True; tables: inspect with sqlite_master; never write). The internet is available (WebFetch, WebSearch, curl; pdftotext is installed). Never read a secret's value. Do not commit. Your final message is raw data for the orchestrator.`

const SCHEMA_TEXT = `SCENARIO SCHEMA (one JSON object, written to research/scenarios_draft/<slug>.json):
{
 "key": "<slug>",
 "title": "<Evaluation name> before <the release decision>" (under 90 characters),
 "group": "frontier model" | "physical AI",
 "agent": "<Role> at <developer type> who owns the <release/launch> decision" (one sentence, the decision-maker),
 "decision": "Delay the <release> and <concrete mitigation> vs <release> as planned" (respond vs deploy; one sentence),
 "theta_definition": "theta=1: <a checkable hazardous property of the system under test, present or absent>" (one sentence; the property, not the evaluation's score),
 "instrument": "<The evaluation> is built from scratch (<what building involves>) and run once against <the system under test>" (one or two sentences),
 "attributes": {"risk_domain": "cbrn|cyber|loss_of_control|harmful_manipulation|societal_harm|physical_harm", "level": <fidelity level 0-9 for physical AI, null for frontier model>, "eval_family": "<short family name>", "system_under_test": "<LLM | agentic LLM | VLM | VLA policy | LLM or VLM inside a robot | non-learning physical system>", "public": true|false, "candidate_rank": <rank in the candidates file>},
 "sources": [{"key": "<bibkey-like slug>", "kind": "arxiv|url|pdf|system_card", "ref": "<arXiv id | URL | system-card slug>", "role": "decision|instrument|both", "title": "<title>", "fetched": "2026-10-01"}, ...],
 "decision_facts": "<120 to 250 words. What is known about the HAZARD and the STAKES of this release decision: prevalence or base rates, published capability or incident results that bear on how likely the hazardous property is, who is exposed, what a response costs (delay, forgone use) and what a missed hazard costs, documented gating decisions by developers. Every sentence ends with a citation [key] to an entry of sources. Never describes how the evaluation is built, what it costs, or how valid it is; may cite published results as evidence about the hazard without describing the instrument.>",
 "instrument_facts": "<120 to 250 words. How the evaluation is built and run: items or scenarios and their origin, scoring, who authored it, hardware or compute, run count, published cost facts (quote the number and unit; write 'No cost figure is published.' when none exists), published validity facts (judge agreement, expert baselines, correlation with a higher-fidelity evaluation or a field outcome, documented failure modes such as saturation or shortcuts). Every sentence ends with [key]. Never mentions the stakes of the decision, benefits, liabilities or the prior probability of the hazard.>"
}
STYLE: short declarative sentences; facts only, no adjectives of praise; no invented numbers; every number copied from a fetched source with its unit and year; USD figures as published; if the primary source is private or developer-internal say so and rely on system-card sentences; the two facts blocks must each stand alone (the decision prompt never sees instrument_facts and vice versa). Use the terminology of DESIGN section 2 (no 'robot eval', 'AI eval', 'rung', 'gate').
SOURCE CACHE: for every source you fetch, also write research/sources/<key>.json = {"key", "kind", "ref", "url", "title", "fetched": "2026-10-01", "abstract": "<abstract or first 1500 chars>", "text": "<full plain text, pdftotext or HTML stripped, truncated at 300000 chars>", "chars": <length before truncation>}. Skip the cache file if one already exists for that key. For system-card sources, "text" is the concatenation of the corpus sentences that name the evaluation (with document slugs), not the whole card.`

const SCENARIOS = [
  ['cybergym', 'frontier model', 'CyberGym (targeted vulnerability reproduction)'],
  ['exploitgym', 'frontier model', 'ExploitGym (exploit development from known vulnerabilities)'],
  ['vct', 'frontier model', 'Virology Capabilities Test (VCT)'],
  ['cyber_range', 'frontier model', "Cyber range, end-to-end network attack (UK AISI 'The Last Ones'; OpenAI Cyber Range)"],
  ['labbench_bio', 'frontier model', 'LAB-Bench bio subset (ProtocolQA, CloningScenarios, SeqQA, FigQA)'],
  ['strongreject', 'frontier model', 'StrongREJECT (jailbreak robustness)'],
  ['cybench', 'frontier model', 'Cybench (professional CTF suite)'],
  ['cvebench', 'frontier model', 'CVE-Bench (real web-application exploitation)'],
  ['mask', 'frontier model', 'MASK (honesty under pressure)'],
  ['wmdp', 'frontier model', 'WMDP (Weapons of Mass Destruction Proxy)'],
  ['shade_arena', 'frontier model', 'SHADE-Arena (covert sabotage with an LLM monitor)'],
  ['petri', 'frontier model', 'Petri (automated alignment audit with a fixed seed set)'],
  ['exploitbench', 'frontier model', 'ExploitBench (browser-engine exploit development, Anthropic)'],
  ['bloom', 'frontier model', 'Bloom (automated behavioural evaluation generator)'],
  ['controlarena', 'frontier model', 'ControlArena (AI-control settings: side-task success under monitoring)'],
  ['agentic_misalignment', 'frontier model', 'Agentic Misalignment (insider-threat scenarios)'],
  ['abcbench', 'frontier model', 'ABC-Bench (Agentic Bio-Capabilities Benchmark)'],
  ['agentharm', 'frontier model', 'AgentHarm (harmful multi-step agentic tasks)'],
  ['binary_exploitation', 'frontier model', 'Binary Exploitation Benchmark, formerly OSS-Fuzz (Anthropic; CAISI private variant)'],
  ['fortress', 'frontier model', 'FORTRESS (national-security and public-safety adversarial prompts)'],
  ['bbq', 'frontier model', 'BBQ (Bias Benchmark for QA)'],
  ['biotier', 'frontier model', 'BioTIER (biology refusal benchmark)'],
  ['harmbench', 'frontier model', 'HarmBench (automated red teaming and robust refusal)'],
  ['cyscenariobench', 'frontier model', 'CyScenarioBench (Irregular, multi-stage offensive scenarios)'],
  ['hpct', 'frontier model', 'HPCT (Human Pathogen Capabilities Test)'],
  ['deceptionbench', 'frontier model', 'DeceptionBench (assisting user deception of third parties)'],
  ['iihs_paeb', 'physical AI', 'IIHS pedestrian AEB track protocol (Version IV) [iihs2024paeb]'],
  ['robopair', 'physical AI', 'RoboPAIR jailbreak red-teaming of LLM-controlled robots [robey2024robopair]'],
  ['veo_worldmodel', 'physical AI', 'Veo world-model safety probing of VLA checkpoints [geminirobotics2025veo]'],
  ['redvla', 'physical AI', 'RedVLA physical red teaming of VLA policies [zhang2026redvla]'],
  ['iso10218_pfl', 'physical AI', 'ISO 10218:2025 / ISO/TS 15066 power-and-force-limiting contact-force test [iso2025iso10218]'],
  ['maniguard', 'physical AI', 'ManiGuard specification-grounded manipulation safety suite [peng2026maniguard]'],
  ['safeagentbench', 'physical AI', 'SafeAgentBench hazardous-task refusal and execution [yin2024safeagentbench]'],
  ['isbench', 'physical AI', 'IS-Bench interactive safety of VLM-driven household agents [lu2025isbench]'],
  ['asimov2', 'physical AI', 'ASIMOV-2.0 physical-danger perception and constraint following [jindal2025danger]'],
  ['asimov_agentic', 'physical AI', 'ASIMOV-Agentic human-proximity stop and constraint-following [geminirobotics2026agentic]'],
  ['egosafetybench', 'physical AI', 'EgoSafetyBench VLM runtime safety guard on egocentric video [panpatil2026egosafetybench]'],
  ['safeplan', 'physical AI', 'SafePlan prompt suite (with SafeGate follow-up) [obi2025safeplan]'],
  ['humanoid_orchestrator', 'physical AI', 'LLM-orchestrator safety benchmark for human-humanoid collaboration [bajrami2026robotignores]'],
]

const WRITE = { type: 'object', properties: { file: { type: 'string' }, sources_cached: { type: 'array', items: { type: 'string' } }, words_decision: { type: 'integer' }, words_instrument: { type: 'integer' }, open_points: { type: 'array', items: { type: 'string' } } }, required: ['file', 'sources_cached', 'words_decision', 'words_instrument', 'open_points'] }
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['major', 'minor'] }, field: { type: 'string' }, claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'field', 'claim', 'evidence', 'fix'] } }, sentences_checked: { type: 'integer' } }, required: ['findings', 'sentences_checked'] }

phase('Write')
const results = await pipeline(
  SCENARIOS,
  ([slug, group, name]) => agent(`${BASE}
${SCHEMA_TEXT}
TASK: write the scenario for the ${group} evaluation "${name}" as research/scenarios_draft/${slug}.json (key "${slug}", group "${group}"). Find its entry in the candidates file (by name or catalog key) and use its proposed decision, theta, sources, cost and validity facts as the starting point; where a pilot scenario for the same evaluation exists, reuse its fact-checked context sentences (split them into the decision block and the instrument block by the rule above, re-cite each) and its agent/decision/theta wording unless the candidates file improves it. Fetch the primary source(s) (arXiv abstract page and PDF or HTML full text; protocol PDFs; developer pages) and the system-card sentences naming the evaluation, write the source cache files, and write every sentence from what you fetched. Decision facts must give the elicitor what it needs to price the stakes under both the society and the developer perspective (who is exposed, scale of harm, what a delay or restriction forgoes). Make the mitigation in "decision" concrete and appropriate to the hazard. For physical AI set attributes.level from the candidates file (SafePlan and the humanoid orchestrator benchmark are level 0). Report the word counts and any fact you could not source (drop it rather than guess). Create the directories if missing.`, { label: `write:${slug}`, phase: 'Write', effort: 'high', schema: WRITE }),
  async (w, [slug, group, name]) => {
    if (!w) return { slug, written: false }
    const rev = await agent(`${BASE}
${SCHEMA_TEXT}
Adversarial fact-check of research/scenarios_draft/${slug}.json (the ${group} evaluation "${name}"). For every sentence of decision_facts and instrument_facts: locate the cited source (research/sources/<key>.json, else fetch the ref) and confirm the sentence is supported, with the same number, unit and year; flag 'major' for a number, name, date or claim not in the source, a citation key missing from sources, a sentence in decision_facts that describes the instrument's construction, cost or validity, a sentence in instrument_facts that mentions stakes, benefits, liabilities or the prior, a theta that is a score rather than a hazardous property, a decision that is not respond-vs-deploy, or a schema violation (missing field, wrong group label, level missing for physical AI). Flag 'minor' for terminology that breaks DESIGN section 2, word counts outside 120-250, praise adjectives, or an uncited sentence that is common knowledge. Do not fix anything. Report sentences_checked.`, { label: `check:${slug}`, phase: 'Check', effort: 'xhigh', schema: FINDINGS })
    const findings = rev?.findings || []
    if (findings.length) {
      await agent(`${BASE}
${SCHEMA_TEXT}
Fix these verified findings in research/scenarios_draft/${slug}.json (and add any missing research/sources/<key>.json). Majors first: correct the number from the source or delete the sentence; move misplaced sentences to the right block or delete them; add missing source entries. Then minors. Keep every field within the schema and word limits. Final message: JSON {"fixed": [...], "not_fixed": [...]}.
Findings:
${JSON.stringify(findings, null, 1)}`, { label: `fix:${slug}`, phase: 'Check', effort: 'high' })
    }
    return { slug, written: true, words: [w.words_decision, w.words_instrument], findings: findings.length, major: findings.filter(f => f.severity === 'major').length, checked: rev?.sentences_checked, open: w.open_points }
  },
)

phase('Consistency')
const cons = await agent(`${BASE}
${SCHEMA_TEXT}
TASK: a second consistency pass (after the remaining fact-checks and fixes) over all files in research/scenarios_draft/*.json (39 expected); INDEX.md from the first pass exists and must be rewritten. Check and FIX in place: (1) every file parses, has every schema field, group label is exactly 'frontier model' or 'physical AI', physical-AI entries have an integer level and risk_domain 'physical_harm'; (2) decisions all follow the respond-vs-deploy pattern with a concrete mitigation, and the agent is a developer-side decision-maker in every case (note any exception and why it is justified, e.g. an OEM for the AEB protocol); (3) theta definitions are hazardous properties of the system under test (present/absent), not scores; (4) no two scenarios test the same construct for the same kind of system (report candidates for merging, do not merge); (5) every [key] cited in a facts block exists in that file's sources and every sources entry has a research/sources/<key>.json cache file (create a missing cache by fetching; drop a citation only if its source cannot be fetched and say so); (6) terminology of DESIGN section 2 throughout; (7) titles are unique and under 90 characters; (8) the two facts blocks respect the separation rule. Then write research/scenarios_draft/INDEX.md: a table (key, group, risk_domain, level, system under test, title, words decision/instrument, n sources, cost fact present yes/no, validity fact present yes/no) and a list of every edit you made and every unresolved issue. Final message: JSON {"n_files": N, "edits": [...], "unresolved": [...], "merge_candidates": [...]}`, { label: 'consistency', phase: 'Consistency', effort: 'xhigh' })

return { results, consistency: cons }