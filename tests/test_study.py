"""The committed study studies/safety-evals: the scenario file is the build of
the fact-checked drafts that include.yaml keeps and follows the DESIGN section 5 schema, the
templates respect the two prompts' separation (DESIGN section 4), the
protocols are the headline (p001) and the developer-perspective ablation
(p002), and the documented dry run plans both stages and renders the first
prompt of each without a provider call or a voi.db."""

from __future__ import annotations

import importlib.util
import json
import re
import string
from pathlib import Path

import pytest
import yaml

from voi_rank import db, elicit
from voi_rank import study as study_mod
from voi_rank.fit import DECISION_PARAMS, INSTRUMENT_PARAMS

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / "studies" / "safety-evals"
DRAFTS = ROOT / "research" / "scenarios_draft"
SCENARIO_KEYS = {"title", "agent", "decision", "theta_definition", "instrument", "group", "attributes",
                 "sources", "decision_facts", "instrument_facts", "decision_context", "instrument_context"}
# words of the decision-level stakes that the instrument prompt must never carry
STAKES = re.compile(r"\bB\b|\bK\b|\bprior\b|perspective|society|welfare|liability|financial exposure",
                    re.IGNORECASE)
BANNED_DEC = re.compile(r"\b(?:instrument|evaluation|benchmark|cost)s?\b", re.IGNORECASE)

_spec = importlib.util.spec_from_file_location("build_scenarios", ROOT / "scripts" / "build_scenarios.py")
build_scenarios = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_scenarios)


def scenarios() -> list[dict]:
    return json.loads((STUDY / "scenarios.json").read_text())


def protocol(name: str) -> dict:
    return yaml.safe_load((STUDY / "protocols" / f"{name}.yaml").read_text())


def template(name: str) -> string.Template:
    return string.Template((STUDY / "templates" / name).read_text())


def test_default_study_is_safety_evals():
    assert study_mod.DEFAULT_STUDY == "studies/safety-evals"
    assert study_mod.Study.resolve().root == STUDY.resolve()


def test_scenarios_json_is_the_build_of_the_drafts():
    assert (STUDY / "scenarios.json").read_text() == build_scenarios.render()


def include_list() -> dict:
    return yaml.safe_load((STUDY / "include.yaml").read_text())


def test_include_list_names_every_draft_with_a_reason():
    inc = include_list()
    assert set(inc) == {p.stem for p in DRAFTS.glob("*.json")}
    assert all(isinstance(e["include"], bool) and e["reason"].strip() for e in inc.values())
    kept = {json.loads((DRAFTS / f"{k}.json").read_text())["title"] for k, e in inc.items() if e["include"]}
    titles = {build_scenarios.TITLE_FIXES.get(t, t) for t in kept}
    assert titles == {s["title"] for s in scenarios()}


def test_include_list_with_a_missing_or_bad_entry_is_refused(tmp_path):
    inc = include_list()
    bad = dict(inc)
    bad.pop(sorted(inc)[0])
    bad["nonexistent"] = {"include": True, "reason": "x"}
    bad[sorted(inc)[1]] = {"include": "yes", "reason": ""}
    path = tmp_path / "include.yaml"
    path.write_text(yaml.safe_dump(bad))
    with pytest.raises(SystemExit) as ex:
        build_scenarios.build(path)
    msg = str(ex.value)
    assert f"{sorted(inc)[0]}: no entry" in msg and "nonexistent: no draft" in msg
    assert f"{sorted(inc)[1]}: needs include" in msg


def test_scenarios_follow_the_design_schema():
    scen = scenarios()
    drafts = {d["instrument"]: d for d in (json.loads(p.read_text()) for p in DRAFTS.glob("*.json"))}
    kept = [k for k, e in include_list().items() if e["include"]]
    assert len(scen) == len(kept) and len({s["title"] for s in scen}) == len(kept)
    groups = [s["group"] for s in scen]
    n_llm = groups.count("LLM")
    assert groups == ["LLM"] * n_llm + ["physical AI"] * (len(scen) - n_llm)   # LLM first, then physical AI
    for g in ("LLM", "physical AI"):
        ranks = [s["attributes"]["candidate_rank"] for s in scen if s["group"] == g]
        assert ranks == sorted(ranks) and len(set(ranks)) == len(ranks)
    for sc in scen:
        draft = drafts[sc["instrument"]]
        assert set(sc) == SCENARIO_KEYS, sc["title"]
        for key in ("agent", "decision", "theta_definition", "attributes", "sources", "decision_facts",
                    "instrument_facts"):
            assert sc[key] == draft[key], (sc["title"], key)   # verbatim, citations included
        assert {"risk_domain", "level", "eval_family"} <= set(sc["attributes"])
        level = sc["attributes"]["level"]
        if sc["group"] == "physical AI":
            assert isinstance(level, int) and 0 <= level <= 9
            assert sc["attributes"]["risk_domain"] == "physical_harm"
        else:
            assert level is None
        assert not re.search(r"frontier.model", sc["title"] + json.dumps(sc["attributes"]), re.IGNORECASE)
        keys = [s["key"] for s in sc["sources"]]
        for src in sc["sources"]:
            assert src["kind"] in ("arxiv", "url", "pdf", "system_card") and src["ref"]
            assert src["role"] in ("decision", "instrument", "both")
            assert (ROOT / "research" / "sources" / f"{src['key']}.json").is_file(), src["key"]
        for kind in ("decision", "instrument"):
            facts, ctx = f"{kind}_facts", f"{kind}_context"
            cited = re.findall(r"\[([^\]]+)\]", sc[facts])
            assert cited and set(cited) <= set(keys), (sc["title"], facts)
            assert "[" not in sc[ctx] and "]" not in sc[ctx]
            assert sc[ctx] == re.sub(r"\s*\[[^\]]+\]", "", sc[facts]) and sc[ctx]


def test_templates_keep_the_two_prompts_apart():
    templates = STUDY / "templates"
    decision = (templates / "decision.md").read_text()
    instrument = (templates / "instrument.md").read_text()
    anchors_dec = (templates / "anchors_decision.md").read_text()
    anchors_ins = (templates / "anchors_instrument.md").read_text()
    for text in (decision, anchors_dec):
        assert BANNED_DEC.findall(text) == []
        assert re.search(r"\$title\b|\$context\b|\$instrument\b", text) is None
    assert "$decision_context" in decision and "$agent" in decision and "$anchors_decision" in decision
    assert "$perspective" in decision and "$context_mode" in decision
    for text in (instrument, anchors_ins):
        assert re.findall(r"\bB\b|\bK\b|\bprior\b", text, re.IGNORECASE) == []
    assert STAKES.search(instrument) is None and "$perspective" not in instrument
    for field in ("$title", "$agent", "$decision", "$theta_definition", "$instrument", "$context",
                  "$anchors_instrument"):
        assert field in instrument
    assert "$decision_context" not in instrument
    # both perspectives defined in the decision prompt
    assert "- society: the harm avoided and the welfare forgone" in decision
    assert "- developer: only the developer's own financial exposure: liability, recall, reputation," \
           " lost revenue and delay" in decision
    for text, names in ((decision, DECISION_PARAMS), (instrument, INSTRUMENT_PARAMS)):
        assert '"unit"' not in text
        # extremes first (elicitation_lit.md implication 6), plain decimals (implication 5)
        steps = text.split("## Instructions")[1]
        assert steps.index("- p5: a value you would be surprised to see the true value fall below") \
            < steps.index("- p95: a value you would be surprised to see the true value fall above") \
            < steps.index("- p50: your median")
        assert steps.index("reasoning") < steps.index("- p5:")   # reasoning before numbers
        assert "plain decimal number" in steps and "scientific" not in text
        # the stage's parameters, and only those, in p5, p95, p50 order
        contract = text.split("## Output")[1]
        assert re.findall(r'"(\w+)": \{"reasoning"', contract) == names
        assert contract.count('"p5": 0.0, "p95": 0.0, "p50": 0.0') == len(names)
    # the anchor files (an ablation) carry their own heading and both anchors with every parameter
    for text, names in ((anchors_dec, DECISION_PARAMS), (anchors_ins, INSTRUMENT_PARAMS)):
        assert text.startswith("\n## Anchor scenarios")
        assert "Anchor A1." in text and "Anchor A2." in text
        for name in names:
            assert text.count(f"- {name}") == 2 or text.count(f"- {name} (") == 2, name


@pytest.mark.parametrize("anchors", [False, True])
def test_templates_render_cleanly_with_and_without_anchors(anchors):
    sc = scenarios()[0]
    tv = {"perspective": "society", "context_mode": "curated",
          "anchors_decision": (STUDY / "templates/anchors_decision.md").read_text() if anchors else "",
          "anchors_instrument": (STUDY / "templates/anchors_instrument.md").read_text() if anchors else ""}
    dec = elicit.render_decision_prompt(template("decision.md"), sc,
                                        {k: v for k, v in tv.items() if k != "anchors_instrument"})
    ins = elicit.render_prompt(template("instrument.md"), sc,
                               {k: v for k, v in tv.items() if k != "anchors_decision"})
    for text, nxt in ((dec, "## Decision to elicit"), (ins, "## Scenario to elicit")):
        assert ("## Anchor scenarios" in text) is anchors and ("Anchor A1." in text) is anchors
        assert "\n\n\n" not in text and "$" not in text
        assert re.search(r"[a-z]\.\n\n" + nxt, text)   # a sentence, one blank line, the next heading


def test_every_rendered_prompt_keeps_the_two_prompts_apart():
    cfg = protocol("p001")
    tv = db.normalize_template_vars(cfg, STUDY)
    assert tv["anchors_decision"] == "" and tv["anchors_instrument"] == ""
    dec_t, ins_t = template("decision.md"), template("instrument.md")
    for sc in scenarios():
        dec = elicit.render_decision_prompt(dec_t, sc, tv)
        ins = elicit.render_prompt(ins_t, sc, tv)
        assert sc["instrument"] not in dec and sc["instrument_context"] not in dec and sc["title"] not in dec
        assert sc["decision_context"] in dec and "from the society perspective" in dec
        assert sc["instrument_context"] in ins and sc["decision_context"] not in ins
        assert "[" not in dec and "[" not in ins   # no citation markers reach either prompt
        # the instrument prompt carries no stakes words outside the scenario's own text
        own = ins
        for field in ("title", "agent", "decision", "theta_definition", "instrument", "instrument_context"):
            own = own.replace(sc[field], "")
        assert STAKES.search(own) is None, (sc["title"], STAKES.findall(own))
        assert BANNED_DEC.search(dec.split("## Decision to elicit")[0]) is None


def test_protocols_p001_headline_and_p002_developer_ablation():
    cfg = protocol("p001")
    assert cfg["name"] == "p001"
    dec, ins = cfg["stages"]
    assert (dec["name"], dec["params"], dec["group_key"]) == ("decision", DECISION_PARAMS, "self")
    assert (ins["name"], ins["params"]) == ("instrument", INSTRUMENT_PARAMS) and "group_key" not in ins
    assert cfg["template_vars"] == {"perspective": "society", "anchors_decision": "",
                                    "anchors_instrument": "", "context_mode": "curated"}
    assert cfg["members"] == [{"provider": "claude_cli", "model": "haiku", "k_repeats": 2},
                              {"provider": "claude_cli", "model": "sonnet", "k_repeats": 2}]
    assert [s["name"] for s in db.normalize_stages(cfg, STUDY)] == ["decision", "instrument"]
    p2 = protocol("p002")
    assert p2["name"] == "p002" and p2["template_vars"]["perspective"] == "developer"
    assert "--stage decision" in p2["notes"]
    strip = lambda c: {k: v for k, v in c.items() if k not in ("name", "notes")}   # noqa: E731
    p1_rest, p2_rest = strip(cfg), strip(p2)
    p1_rest["template_vars"] = {**cfg["template_vars"], "perspective": "developer"}
    assert p1_rest == p2_rest   # identical except the name and the perspective


@pytest.fixture
def fresh_study(tmp_path):
    """A copy of the study without its voi.db: the dry-run tests check the
    plan from scratch and that a dry run writes no database, whatever the
    real study's elicitation state."""
    import shutil
    dst = tmp_path / "safety-evals"
    dst.mkdir()
    shutil.copy(STUDY / "scenarios.json", dst / "scenarios.json")
    for sub in ("protocols", "templates"):
        shutil.copytree(STUDY / sub, dst / sub)
    return dst


def test_dry_run_plans_both_stages_and_calls_nothing(monkeypatch, capsys, fresh_study):
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: (_ for _ in ()).throw(AssertionError("provider called")))
    assert not list(fresh_study.glob("voi.db*"))
    elicit.main(["--study", str(fresh_study), "--protocol", "p001", "--dry-run"])
    out = capsys.readouterr().out
    assert not list(fresh_study.glob("voi.db*"))   # the plan ran on an in-memory copy
    assert "DRY RUN: protocol p001 (stages decision + instrument, hash" in out
    assert "stage decision (template templates/decision.md, params p, B, K, group_key self):" in out
    assert "stage instrument (template templates/instrument.md, params s, t, C_build, C_run, n):" in out
    n = len(scenarios())
    for member in ("claude_cli:haiku", "claude_cli:sonnet"):
        groups = ", ".join(str(i) for i in range(1, n + 1))
        assert f"member {member} (k=2): {2 * n} pending slots over {n} groups ({groups})" in out
        assert f"member {member} (k=2): {2 * n} pending slots over {n} scenarios (ids 1..{n})" in out
        assert (f"{member}: {4 * n} slots (decision {2 * n}, instrument {2 * n}), estimated cost unknown"
                in out)
    assert f"{8 * n} slots would be elicited; no provider was called." in out
    assert f"plan: protocol p001, {8 * n} pending slots" in out
    assert "estimated total: $0.00 + unknown" in out
    assert "warning" not in out   # every rendered field is filled
    sc = scenarios()[0]
    dec, ins = out.split("first pending prompt of stage decision")[1].split(
        "first pending prompt of stage instrument")
    assert "(group '1', representative scenario 1," in dec and "(scenario 1," in ins
    assert sc["agent"] in dec and sc["decision"] in dec and sc["decision_context"] in dec
    assert "from the society perspective" in dec and "Anchor" not in dec and "context mode: curated" in dec
    assert sc["instrument"] not in dec and sc["title"] not in dec
    assert sc["title"] in ins and sc["instrument"] in ins and sc["instrument_context"] in ins
    assert "Anchor" not in ins and "C_build" in ins and "$context" not in ins
    assert '"p":' in dec and '"p":' not in ins and '"n":' in ins and '"n":' not in dec


def test_dry_run_p002_decision_stage_only(capsys, fresh_study):
    elicit.main(["--study", str(fresh_study), "--protocol", "p002", "--stage", "decision", "--dry-run"])
    out = capsys.readouterr().out
    assert f"plan: protocol p002, {4 * len(scenarios())} pending slots" in out
    assert "not planned (--stage decision)" in out
    assert "from the developer perspective" in out
    assert not list(fresh_study.glob("voi.db*"))


def test_dry_run_from_the_shell_entry_point(fresh_study):
    """The README's command, as a user runs it (a subprocess, the repo root
    as cwd), creates no database."""
    import subprocess
    import sys
    proc = subprocess.run([sys.executable, "-m", "voi_rank.elicit", "--study", str(fresh_study),
                           "--protocol", "p001", "--dry-run"], cwd=ROOT, capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert f"{8 * len(scenarios())} slots would be elicited; no provider was called." in proc.stdout
    assert not list(fresh_study.glob("voi.db*"))


@pytest.mark.parametrize("name", ["decision.md", "instrument.md", "anchors_decision.md",
                                  "anchors_instrument.md"])
def test_templates_have_no_trailing_whitespace(name):
    text = (STUDY / "templates" / name).read_text()
    assert all(line == line.rstrip() for line in text.splitlines()) and text.endswith("\n")
