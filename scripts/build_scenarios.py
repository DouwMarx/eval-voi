"""Build studies/safety-evals/scenarios.json from the fact-checked drafts in
research/scenarios_draft/*.json (DESIGN section 5).

The facts fields are copied verbatim with their [key] citations; the two
context fields (what the prompts render, context mode `curated`) are the same
text with the citation markers removed. Group "frontier model" becomes "LLM"
(DESIGN section 2) and titles that used "frontier model" are renamed.
Order: the LLM group, then physical AI, each by attributes.candidate_rank.

    uv run python scripts/build_scenarios.py           # write the file
    uv run python scripts/build_scenarios.py --check   # exit 1 if it is stale
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "research" / "scenarios_draft"
OUT = ROOT / "studies" / "safety-evals" / "scenarios.json"

GROUPS = {"frontier model": "LLM", "physical AI": "physical AI"}
GROUP_ORDER = ("LLM", "physical AI")
# DESIGN section 2: "frontier model" is not a group name and is ambiguous
TITLE_FIXES = {
    "ABC-Bench before a frontier model release": "ABC-Bench before an LLM release",
    "Binary Exploitation Benchmark before general release of a frontier model":
        "Binary Exploitation Benchmark before general release of an LLM",
    "Cybench before deploying a frontier agentic coding model":
        "Cybench before deploying an agentic coding LLM",
    "CyScenarioBench multi-stage attack scenarios before a frontier model's general release":
        "CyScenarioBench multi-stage attack scenarios before an LLM's general release",
    "ExploitBench before the general release of a frontier model":
        "ExploitBench before the general release of an LLM",
    "ExploitGym before general release of a frontier agentic model":
        "ExploitGym before general release of an agentic LLM",
    "Human Pathogen Capabilities Test before releasing a frontier model":
        "Human Pathogen Capabilities Test before releasing an LLM",
    "LAB-Bench bio subset before a frontier model release": "LAB-Bench bio subset before an LLM release",
    "Virology Capabilities Test before releasing a frontier model":
        "Virology Capabilities Test before releasing a multimodal LLM",
}
FIELDS = ("title", "agent", "decision", "theta_definition", "instrument", "group", "attributes", "sources",
          "decision_facts", "instrument_facts", "decision_context", "instrument_context")


def strip_citations(text: str, keys: list[str]) -> str:
    """The facts text without its ' [key]' citation markers."""
    pattern = r"\s*\[(?:" + "|".join(re.escape(k) for k in keys) + r")\]"
    return re.sub(pattern, "", text)


def convert(draft: dict) -> dict:
    keys = [s["key"] for s in draft["sources"]]
    sc = {k: draft[k] for k in ("agent", "decision", "theta_definition", "instrument", "attributes",
                                "sources", "decision_facts", "instrument_facts")}
    sc["title"] = TITLE_FIXES.get(draft["title"], draft["title"])
    sc["group"] = GROUPS[draft["group"]]
    sc["decision_context"] = strip_citations(draft["decision_facts"], keys)
    sc["instrument_context"] = strip_citations(draft["instrument_facts"], keys)
    return {k: sc[k] for k in FIELDS}


def build() -> list[dict]:
    scen = [convert(json.loads(p.read_text())) for p in sorted(DRAFTS.glob("*.json"))]
    return sorted(scen, key=lambda s: (GROUP_ORDER.index(s["group"]), s["attributes"]["candidate_rank"]))


def render() -> str:
    return json.dumps(build(), indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    text = render()
    if "--check" in argv:
        stale = not OUT.exists() or OUT.read_text() != text
        print(f"{OUT.relative_to(ROOT)} is {'stale' if stale else 'up to date'}")
        return int(stale)
    OUT.write_text(text)
    print(f"wrote {len(build())} scenarios to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
