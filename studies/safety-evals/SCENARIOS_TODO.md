# studies/safety-evals: what a later step fills

The 15 scenarios were converted from the pilot (archive/pilots/ai-safety-evals/scenarios.json) to the DESIGN section 5 schema on 2026-10-01. The conversion kept the attributes, moved the pilot's single facts block to `instrument_facts`, built `sources` from `attributes.catalog_keys` (kind `catalog`, ref = the catalogue URL) and `attributes.system_card_snippet_keys` (kind `system_card`, ref = the snippet corpus entry), and set `decision_context` / `instrument_context` equal to the facts fields, since voi_rank/context.py does not exist yet.

## Per scenario: `decision_facts` is empty

Every scenario needs curated decision-level sentences (each ending in a [key] citation to `sources`), none of which may describe the evaluation: the deployment or release at stake and its cadence, the base rate of the hazardous property in comparable releases, the harm if it is present and the release goes ahead (society perspective) and the developer's exposure (liability, recall, reputation, lost revenue, delay), and what responding costs when the property is absent. The sources that back them get `role: decision` (or `both`).

1. Virology Capabilities Test before releasing a frontier model
2. WMDP hazardous-knowledge screen before an open-weights release
3. Cybench CTF suite before deploying a frontier coding agent
4. CyberGym vulnerability reproduction before releasing an agentic model
5. End-to-end cyber range before lifting autonomous cyber-operations restrictions
6. SHADE-Arena sabotage test before autonomous agent deployment
7. Agentic misalignment blackmail scenarios before granting email-agent autonomy
8. MASK honesty-under-pressure benchmark before launching a consumer assistant
9. StrongREJECT jailbreak robustness before public launch
10. BBQ demographic-bias benchmark before deploying an LLM in customer service
11. ASIMOV-2.0 physical-danger perception before shipping a VLM robot planner
12. SafeAgentBench hazardous-task refusal before a home-robot planner launch
13. Veo world-model safety probing before deploying a new VLA checkpoint
14. RoboPAIR jailbreak red-teaming before fielding an LLM-controlled quadruped
15. IIHS pedestrian AEB track protocol before launching a new AEB calibration

## Study-wide

- `instrument_facts` were written for the pilot's six-parameter model: they describe build cost and validity but say nothing about the cost of one run (C_run) or the number of decisions the evaluation informs over its life (n). Add sentences for both, with sources.
- Every source's `role` is `both` for now; split into `decision` / `instrument` once the decision facts exist.
- voi_rank/context.py (DESIGN section 5): build `decision_context` and `instrument_context` from the facts and the fetched sources (research/sources/<key>.json) in the modes curated, abstracts and full; until then the context fields equal the facts fields and protocol p001 declares `context_mode: curated`.
- templates/anchors_instrument.md: the C_build, C_run and n triples of anchors A1 and A2 are stylised placeholders (the pilots' anchors carried one cost C); source them or replace the anchors.
