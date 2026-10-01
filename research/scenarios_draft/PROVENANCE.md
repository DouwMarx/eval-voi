# How the scenario contexts were produced

The decision and instrument contexts the elicitors read were written and checked by language-model agents, not by hand. This file records exactly how, so a reader can audit or reproduce the curation.

Model: Claude Fable 5.1 (claude-fable-5-1), run as Claude Code subagents on 2026-09-30 and 2026-10-01. The agents could fetch web pages and read the repository; they had no access to the elicitation results, which did not exist yet.

Pipeline (the exact prompts are in `curation_workflow.js`, an orchestration script whose agent() calls each received the quoted prompt verbatim):
1. Candidate selection. `../research_workflow.js`, sweeps "frontier_candidates" and "physical_candidates", ranked the candidate evaluations by stated rules and wrote `../candidates_frontier.*` and `../candidates_physical.*`. A second agent verified every citation and number against the fetched source; a third fixed what it found.
2. Writing. One agent per evaluation (prompt "TASK: write the scenario for ...", with the shared SCHEMA_TEXT) fetched the primary sources, cached their full text in `../sources/<key>.json`, and wrote `<key>.json` with a cited decision block and a cited instrument block of 120 to 250 words each.
3. Checking. A separate agent per evaluation (prompt "Adversarial fact-check of ...") checked every sentence against the cached source text and the separation rule (no instrument facts in the decision block, no stakes in the instrument block). A third agent fixed its findings.
4. Consistency. One agent checked all 39 files together and wrote `INDEX.md`. It ran twice: the first pass ran while some checks were still unfinished because of network outages, and the script was edited (the consistency prompt now says "a second consistency pass") so the pass reran after every check and fix had completed.
5. Assembly. `scripts/build_scenarios.py` turns the drafts into `studies/safety-evals/scenarios.json` deterministically, removing the [key] citation markers from the text the elicitors see.

What this does and does not guarantee: every sentence the elicitors read traces to a cached source text, and a second model checked it. It does not guarantee that the selection of facts is neutral: an agent chose which facts to include within the word limit. Using no Anthropic model in the final elicitation ensemble keeps the curating model's developer out of the elicitation.
