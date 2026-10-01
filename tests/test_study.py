"""The committed study studies/safety-evals: the scenario file follows the
DESIGN section 5 schema, the templates respect the two prompts' separation
(DESIGN section 4), and the documented dry run plans both stages and renders
the first prompt of each without a provider call or a voi.db."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from voi_rank import db, elicit
from voi_rank import study as study_mod
from voi_rank.fit import DECISION_PARAMS, INSTRUMENT_PARAMS

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / "studies" / "safety-evals"
SCENARIO_KEYS = {"title", "agent", "decision", "theta_definition", "instrument", "group", "attributes",
                 "sources", "decision_facts", "instrument_facts", "decision_context", "instrument_context",
                 "domain_tags"}


def test_default_study_is_safety_evals():
    assert study_mod.DEFAULT_STUDY == "studies/safety-evals"
    assert study_mod.Study.resolve().root == STUDY.resolve()
    assert not (STUDY / "voi.db").exists()   # no database is committed


def test_scenarios_follow_the_design_schema():
    scen = json.loads((STUDY / "scenarios.json").read_text())
    pilot = json.loads((ROOT / "archive/pilots/ai-safety-evals/scenarios.json").read_text())
    assert len(scen) == 15 and [s["title"] for s in scen] == [s["title"] for s in pilot]
    assert len({s["title"] for s in scen}) == 15
    for sc, old in zip(scen, pilot, strict=True):
        assert set(sc) == SCENARIO_KEYS, sc["title"]
        assert sc["group"] in ("frontier model", "physical AI") and "context" not in sc
        assert sc["attributes"] == old["attributes"]   # kept whole (risk_domain, level, eval_family, keys)
        assert {"risk_domain", "level", "eval_family"} <= set(sc["attributes"])
        assert sc["instrument_facts"] == old["context"] and sc["instrument_facts"]
        assert sc["decision_facts"] == "" and sc["decision_context"] == sc["decision_facts"]
        assert sc["instrument_context"] == sc["instrument_facts"]
        keys = [s["key"] for s in sc["sources"]]
        old_attrs = old["attributes"]
        assert keys == old_attrs.get("catalog_keys", []) + old_attrs.get("system_card_snippet_keys", [])
        for src in sc["sources"]:
            assert set(src) == {"key", "kind", "ref", "role"} and src["role"] == "both"
            assert src["kind"] in ("catalog", "system_card") and src["ref"]
            if src["kind"] == "catalog":
                assert src["ref"].startswith("https://")
            else:
                assert src["ref"] == f"research/system_card_snippets.json#{src['key']}"
    groups = {s["group"] for s in scen}
    assert groups == {"frontier model", "physical AI"}
    assert sum(s["group"] == "physical AI" for s in scen) == 5
    assert all(s["attributes"]["level"] is not None for s in scen if s["group"] == "physical AI")
    # every source key resolves in the research corpus
    catalog = {c["key"] for c in json.loads((ROOT / "research/catalog.json").read_text())}
    snippets = set(json.loads((ROOT / "research/system_card_snippets.json").read_text()))
    for sc in scen:
        for src in sc["sources"]:
            assert src["key"] in (catalog if src["kind"] == "catalog" else snippets), src


def test_templates_keep_the_two_prompts_apart():
    templates = STUDY / "templates"
    decision = (templates / "decision.md").read_text()
    instrument = (templates / "instrument.md").read_text()
    anchors_dec = (templates / "anchors_decision.md").read_text()
    anchors_ins = (templates / "anchors_instrument.md").read_text()
    banned_dec = re.compile(r"\b(?:instrument|evaluation|benchmark|cost)s?\b", re.IGNORECASE)
    for text in (decision, anchors_dec):
        assert banned_dec.findall(text) == []
        assert re.search(r"\$title\b|\$context\b|\$instrument\b", text) is None
    assert "$decision_context" in decision and "$agent" in decision and "$anchors_decision" in decision
    assert "$perspective" in decision and "$context_mode" in decision
    banned_ins = re.compile(r"\bB\b|\bK\b|\bprior\b", re.IGNORECASE)
    for text in (instrument, anchors_ins):
        assert banned_ins.findall(text) == []
    for field in ("$title", "$agent", "$decision", "$theta_definition", "$instrument", "$context",
                  "$anchors_instrument"):
        assert field in instrument
    assert "$decision_context" not in instrument
    # no unit field in either output contract; the stage's parameters, and only those, are listed
    for text, names in ((decision, DECISION_PARAMS), (instrument, INSTRUMENT_PARAMS)):
        assert '"unit"' not in text
        contract = text.split("## Output")[1]
        assert [m for m in re.findall(r'"(\w+)": \{"reasoning"', contract)] == names
    # both anchors appear in both halves, with every parameter of the half
    for text, names in ((anchors_dec, DECISION_PARAMS), (anchors_ins, INSTRUMENT_PARAMS)):
        assert "Anchor A1." in text and "Anchor A2." in text
        for name in names:
            assert text.count(f"- {name}") == 2 or text.count(f"- {name} (") == 2, name


def test_protocol_p001_is_two_stages_with_self_grouping_and_template_vars():
    cfg = yaml.safe_load((STUDY / "protocols/p001.yaml").read_text())
    assert cfg["name"] == "p001"
    dec, ins = cfg["stages"]
    assert (dec["name"], dec["params"], dec["group_key"]) == ("decision", DECISION_PARAMS, "self")
    assert (ins["name"], ins["params"]) == ("instrument", INSTRUMENT_PARAMS) and "group_key" not in ins
    assert cfg["template_vars"] == {"perspective": "society",
                                    "anchors_decision": "@file:templates/anchors_decision.md",
                                    "anchors_instrument": "@file:templates/anchors_instrument.md",
                                    "context_mode": "curated"}
    assert cfg["members"] == [{"provider": "claude_cli", "model": "haiku", "k_repeats": 3},
                              {"provider": "claude_cli", "model": "sonnet", "k_repeats": 3}]
    stages = db.normalize_stages(cfg, STUDY)
    tv = db.normalize_template_vars(cfg, STUDY)
    assert tv["anchors_decision"] == (STUDY / "templates/anchors_decision.md").read_text()
    assert [s["name"] for s in stages] == ["decision", "instrument"]


def test_dry_run_plans_both_stages_and_calls_nothing(monkeypatch, capsys):
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: (_ for _ in ()).throw(AssertionError("provider called")))
    assert not list(STUDY.glob("voi.db*"))
    elicit.main(["--study", "studies/safety-evals", "--protocol", "p001", "--dry-run"])
    out = capsys.readouterr().out
    assert not list(STUDY.glob("voi.db*"))   # the plan ran on an in-memory copy
    assert "DRY RUN: protocol p001 (stages decision + instrument, hash" in out
    assert "stage decision (template templates/decision.md, params p, B, K, group_key self):" in out
    assert "stage instrument (template templates/instrument.md, params s, t, C_build, C_run, n):" in out
    for member in ("claude_cli:haiku", "claude_cli:sonnet"):
        groups = ", ".join(str(i) for i in range(1, 16))
        assert f"member {member} (k=3): 45 pending slots over 15 groups ({groups})" in out
        assert f"member {member} (k=3): 45 pending slots over 15 scenarios (ids 1..15)" in out
    assert "180 slots would be elicited; no provider was called." in out
    assert "plan: protocol p001, 180 pending slots" in out
    for member in ("claude_cli:haiku", "claude_cli:sonnet"):
        assert f"{member}: 90 slots (decision 45, instrument 45), estimated cost unknown" in out
    assert "estimated total: $0.00 + unknown" in out
    scen = json.loads((STUDY / "scenarios.json").read_text())
    dec, ins = out.split("first pending prompt of stage decision")[1].split(
        "first pending prompt of stage instrument")
    assert "(group '1', representative scenario 1," in dec and "(scenario 1," in ins
    assert scen[0]["agent"] in dec and scen[0]["decision"] in dec and scen[0]["theta_definition"] in dec
    assert "from the society perspective" in dec and "Anchor A1." in dec and "context mode: curated" in dec
    assert scen[0]["instrument"] not in dec and scen[0]["title"] not in dec
    assert scen[0]["instrument_facts"][:60] not in dec
    assert re.search(r"\b(?:instrument|evaluation|benchmark|cost)s?\b", dec.split("## Decision to elicit")[0],
                     re.IGNORECASE) is None   # the rendered template text, before the scenario's own words
    assert scen[0]["title"] in ins and scen[0]["instrument"] in ins
    assert scen[0]["instrument_facts"][:60] in ins
    assert "Anchor A1." in ins and "C_build" in ins and "$context" not in ins
    assert re.search(r"\bB\b|\bK\b|\bprior\b", ins.split("## Scenario to elicit")[0], re.IGNORECASE) is None
    # the second stage of the same scenario shares nothing elicited: no decision-level number appears
    assert '"p":' in dec and '"p":' not in ins and '"n":' in ins and '"n":' not in dec


def test_dry_run_from_the_shell_entry_point(tmp_path):
    """The README's command, as a user runs it (a subprocess, the repo root
    as cwd), creates no database."""
    import subprocess
    import sys
    proc = subprocess.run([sys.executable, "-m", "voi_rank.elicit", "--study", "studies/safety-evals",
                           "--protocol", "p001", "--dry-run"], cwd=ROOT, capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "180 slots would be elicited; no provider was called." in proc.stdout
    assert not list(STUDY.glob("voi.db*"))


@pytest.mark.parametrize("name", ["decision.md", "instrument.md", "anchors_decision.md",
                                  "anchors_instrument.md"])
def test_templates_have_no_trailing_whitespace(name):
    text = (STUDY / "templates" / name).read_text()
    assert all(line == line.rstrip() for line in text.splitlines()) and text.endswith("\n")
