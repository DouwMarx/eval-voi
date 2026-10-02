"""The committed study studies/safety-evals: the scenario file is the build of
the fact-checked drafts that include.yaml keeps and follows the DESIGN section 5 schema, the
templates respect the two prompts' separation (DESIGN section 4), the
protocols are the final run (final) and its no-context ablation
(final_noctx), and the documented dry run plans both stages and renders the
first prompt of each without a provider call or a voi.db."""

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
# the one sentence of the decision prompt that names the evaluation, to say that none is described
DEC_DISCLAIMER = ("No evaluation is described here; estimate the decision from what the developer already"
                  " knows.")
TEMPLATES = sorted(p.name for p in (ROOT / "studies" / "safety-evals" / "templates").glob("*"))

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
    assert TEMPLATES == ["decision.md", "instrument.md"]   # the anchors files are archived, not in the study
    decision = template("decision.md").template
    instrument = template("instrument.md").template
    assert DEC_DISCLAIMER in decision
    assert BANNED_DEC.findall(decision.replace(DEC_DISCLAIMER, "")) == []
    assert re.search(r"\$title\b|\$context\b|\$instrument\b", decision) is None
    assert "$decision_context" in decision and "$agent" in decision and "$anchors_decision" in decision
    assert "$context_mode" in decision and "$perspective" not in decision
    assert re.findall(r"\bB\b|\bK\b|\bprior\b", instrument, re.IGNORECASE) == []
    assert STAKES.search(instrument) is None and "$perspective" not in instrument
    for field in ("$title", "$agent", "$decision", "$theta_definition", "$instrument", "$context",
                  "$anchors_instrument"):
        assert field in instrument
    assert "$decision_context" not in instrument
    # one perspective, society, stated in the decision prompt's text; no developer alternative
    assert "Value B and K for society: the harm avoided and the welfare forgone" in decision
    assert "valued for society" in decision and "developer:" not in decision
    for text in (decision, instrument):
        # the action is mitigate, never respond; nothing is flagged
        assert re.search(r"\brespond", text, re.IGNORECASE) is None
        assert re.search(r"\bflag", text, re.IGNORECASE) is None
        assert re.search(r"\bmitigat", text) is not None
    for text, names in ((decision, DECISION_PARAMS), (instrument, INSTRUMENT_PARAMS)):
        assert '"unit"' not in text
        # extremes first (the elicitation literature review, implication 6), plain decimals (implication 5)
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
    assert "three decision parameters" in decision and "four instrument parameters" in instrument
    assert re.search(r"\bn\b: ", decision + instrument) is None   # no reuse count asked anywhere


ANCHORS = "\n## Anchor scenarios\n\nAnchor A1. A worked example.\n"


@pytest.mark.parametrize("anchors", [False, True])
def test_templates_render_cleanly_with_and_without_anchors(anchors):
    """The protocols set both anchors variables to ''; the placeholders still
    render an inline anchors block cleanly (the archived ablation's form)."""
    sc = scenarios()[0]
    tv = {"context_mode": "curated",
          "anchors_decision": ANCHORS if anchors else "", "anchors_instrument": ANCHORS if anchors else ""}
    dec = elicit.render_decision_prompt(template("decision.md"), sc,
                                        {k: v for k, v in tv.items() if k != "anchors_instrument"})
    ins = elicit.render_prompt(template("instrument.md"), sc,
                               {k: v for k, v in tv.items() if k != "anchors_decision"})
    for text, nxt in ((dec, "## Decision to elicit"), (ins, "## Scenario to elicit")):
        assert ("## Anchor scenarios" in text) is anchors and ("Anchor A1." in text) is anchors
        assert "\n\n\n" not in text and "$" not in text
        assert re.search(r"[a-z]\.\n\n" + nxt, text)   # a sentence, one blank line, the next heading


def test_every_rendered_prompt_keeps_the_two_prompts_apart():
    cfg = protocol("final")
    tv = db.normalize_template_vars(cfg, STUDY)
    assert tv == {"anchors_decision": "", "anchors_instrument": "", "context_mode": "curated"}
    dec_t, ins_t = template("decision.md"), template("instrument.md")
    for sc in scenarios():
        dec = elicit.render_decision_prompt(dec_t, sc, tv)
        ins = elicit.render_prompt(ins_t, sc, tv)
        assert sc["instrument"] not in dec and sc["instrument_context"] not in dec and sc["title"] not in dec
        assert sc["decision_context"] in dec and "valued for society" in dec
        assert sc["instrument_context"] in ins and sc["decision_context"] not in ins
        assert "[" not in dec and "[" not in ins   # no citation markers reach either prompt
        # the instrument prompt carries no stakes words outside the scenario's own text
        own = ins
        for field in ("title", "agent", "decision", "theta_definition", "instrument", "instrument_context"):
            own = own.replace(sc[field], "")
        assert STAKES.search(own) is None, (sc["title"], STAKES.findall(own))
        assert BANNED_DEC.search(dec.split("## Decision to elicit")[0].replace(DEC_DISCLAIMER, "")) is None


def protocol_names() -> list[str]:
    return sorted(p.stem for p in (STUDY / "protocols").glob("*.yaml"))


def test_protocols_final_and_final_noctx():
    assert protocol_names() == ["final", "final_noctx"]   # p001-p003 and final_dev are archived or gone
    cfg = protocol("final")
    assert cfg["name"] == "final"
    dec, ins = cfg["stages"]
    assert (dec["name"], dec["params"], dec["group_key"]) == ("decision", DECISION_PARAMS, "self")
    assert (ins["name"], ins["params"]) == ("instrument", INSTRUMENT_PARAMS) and "group_key" not in ins
    assert cfg["template_vars"] == {"anchors_decision": "", "anchors_instrument": "",
                                    "context_mode": "curated"}
    assert "perspective" not in cfg["template_vars"]
    members = db.normalize_members(cfg)
    assert len(members) == 6 and all(m["provider"] == "openrouter" and m["k_repeats"] == 1 for m in members)
    assert {m["reasoning_effort"] for m in members} == {"medium"}
    assert [s["name"] for s in db.normalize_stages(cfg, STUDY)] == ["decision", "instrument"]
    assert "--protocol final" in cfg["notes"] and "seven-parameter" in cfg["notes"]
    noctx = protocol("final_noctx")
    assert noctx["name"] == "final_noctx" and noctx["template_vars"]["context_mode"] == "none"
    assert "--protocol final_noctx" in noctx["notes"] and "--tag noctx" in noctx["notes"]
    strip = lambda c: {k: v for k, v in c.items() if k not in ("name", "notes")}   # noqa: E731
    final_rest, noctx_rest = strip(cfg), strip(noctx)
    final_rest["template_vars"] = {**cfg["template_vars"], "context_mode": "none"}
    assert final_rest == noctx_rest   # identical except the name, the notes and the context mode


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


FINAL_MEMBERS = ["openrouter:deepseek/deepseek-v4.1-flash", "openrouter:z-ai/glm-5.3",
                 "openrouter:xiaomi/mimo-v2.6-flash", "openrouter:openai/gpt-6-luna",
                 "openrouter:google/gemini-3.8-flash", "openrouter:x-ai/grok-4.7"]


def test_dry_run_plans_both_stages_and_calls_nothing(monkeypatch, capsys, fresh_study):
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: (_ for _ in ()).throw(AssertionError("provider called")))
    assert not list(fresh_study.glob("voi.db*"))
    elicit.main(["--study", str(fresh_study), "--protocol", "final", "--dry-run"])
    out = capsys.readouterr().out
    assert not list(fresh_study.glob("voi.db*"))   # the plan ran on an in-memory copy
    assert "DRY RUN: protocol final (stages decision + instrument, hash" in out
    assert "template_vars ['anchors_decision', 'anchors_instrument', 'context_mode'])" in out
    assert "stage decision (template templates/decision.md, params p, B, K, group_key self):" in out
    assert "stage instrument (template templates/instrument.md, params s, t, C_build, C_run):" in out
    n = len(scenarios())
    assert [m["model"] for m in db.normalize_members(protocol("final"))] == [m.split(":", 1)[1]
                                                                             for m in FINAL_MEMBERS]
    for member in FINAL_MEMBERS:
        groups = ", ".join(str(i) for i in range(1, n + 1))
        assert f"member {member} (k=1): {n} pending slots over {n} groups ({groups})" in out
        assert f"member {member} (k=1): {n} pending slots over {n} scenarios (ids 1..{n})" in out
        assert f"{member}: {2 * n} slots (decision {n}, instrument {n}), estimated cost" in out
    # two stages x six members x one repeat per scenario
    assert f"{12 * n} slots would be elicited; no provider was called." in out
    assert f"plan: protocol final, {12 * n} pending slots" in out
    assert out.index("estimated total: $") < out.index("first pending prompt of stage decision")
    assert "warning" not in out   # every rendered field is filled
    sc = scenarios()[0]
    dec, ins = out.split("first pending prompt of stage decision")[1].split(
        "first pending prompt of stage instrument")
    assert "(group '1', representative scenario 1," in dec and "(scenario 1," in ins
    assert sc["agent"] in dec and sc["decision"] in dec and sc["decision_context"] in dec
    assert "valued for society" in dec and "Anchor" not in dec and "context mode: curated" in dec
    assert sc["instrument"] not in dec and sc["title"] not in dec
    assert sc["title"] in ins and sc["instrument"] in ins and sc["instrument_context"] in ins
    assert "Anchor" not in ins and "C_build" in ins and "$context" not in ins
    assert '"p":' in dec and '"p":' not in ins and '"C_run":' in ins and '"C_run":' not in dec
    assert '"n":' not in dec and '"n":' not in ins   # no reuse count asked
    assert "perspective" not in dec and "perspective" not in ins


def test_dry_run_final_noctx_decision_stage_only(capsys, fresh_study):
    elicit.main(["--study", str(fresh_study), "--protocol", "final_noctx", "--stage", "decision",
                 "--dry-run"])
    out = capsys.readouterr().out
    assert f"plan: protocol final_noctx, {6 * len(scenarios())} pending slots" in out
    assert "not planned (--stage decision)" in out
    assert "first pending prompt of stage decision" in out
    assert "first pending prompt of stage instrument" not in out
    assert "Background facts" not in out and "valued for society" in out
    assert not list(fresh_study.glob("voi.db*"))


def test_dry_run_from_the_shell_entry_point(fresh_study):
    """The README's command, as a user runs it (a subprocess, the repo root
    as cwd), creates no database."""
    import subprocess
    import sys
    proc = subprocess.run([sys.executable, "-m", "voi_rank.elicit", "--study", str(fresh_study),
                           "--protocol", "final", "--dry-run"], cwd=ROOT, capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert f"{12 * len(scenarios())} slots would be elicited; no provider was called." in proc.stdout
    assert not list(fresh_study.glob("voi.db*"))


@pytest.mark.parametrize("name", TEMPLATES)
def test_templates_have_no_trailing_whitespace(name):
    text = (STUDY / "templates" / name).read_text()
    assert all(line == line.rstrip() for line in text.splitlines()) and text.endswith("\n")


def test_final_noctx_renders_no_context_and_no_context_heading(capsys, fresh_study):
    """The no-context ablation: final_noctx equals final but for context_mode
    none, and its dry run renders neither prompt's facts nor the facts
    heading, while the rest of each prompt is final's."""
    sc = scenarios()[0]
    out = {}
    for name in ("final", "final_noctx"):
        elicit.main(["--study", str(fresh_study), "--protocol", name, "--dry-run"])
        text = capsys.readouterr().out
        dec, ins = text.split("first pending prompt of stage decision")[1].split(
            "first pending prompt of stage instrument")
        out[name] = (dec, ins)
    dec, ins = out["final_noctx"]
    assert sc["decision_context"] not in dec and sc["instrument_context"] not in ins
    assert "Background facts" not in dec and "Background facts" not in ins and "context mode" not in dec
    assert sc["agent"] in dec and sc["decision"] in dec and sc["theta_definition"] in dec
    assert sc["title"] in ins and sc["instrument"] in ins and "## Instructions" in ins
    assert "warning" not in dec
    d1, i1 = out["final"]
    assert sc["decision_context"] in d1 and "## Decision to elicit" in dec and "## Output" in dec
    assert len(dec) < len(d1) and len(ins) < len(i1)
    # the ablation's prompts are final's with the facts section cut out, nothing else
    for cut, full in ((dec, d1), (ins, i1)):
        body = lambda t: t.split("\n", 1)[1]   # noqa: E731  (drop the size-and-hash header line)
        head, _, tail = body(full).partition("\n## Background facts")
        _, _, tail = tail.partition("## Instructions")
        assert body(cut) == head + "\n## Instructions" + tail


def test_unknown_context_mode_is_refused():
    with pytest.raises(SystemExit, match="implemented modes"):
        elicit.context_off({"context_mode": "full"})
