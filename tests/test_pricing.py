"""Per-member OpenRouter request options (protocol YAML -> provider call) and
the plan's cost estimate from catalogue prices (voi_rank.pricing). Offline:
every catalogue fetch is a fake."""

from __future__ import annotations

import json
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from tests.test_staged import StagedFake, build, cfg_of, write_cfg
from voi_rank import db, elicit, pricing
from voi_rank.fit import DECISION_PARAMS, INSTRUMENT_PARAMS

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / "studies" / "safety-evals"
T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
CATALOGUE = {"data": [
    {"id": "z-ai/glm-5.3", "pricing": {"prompt": "0.0000002", "completion": "0.000003"}},
    {"id": "openai/gpt-6-luna", "pricing": {"prompt": "0.0000001", "completion": "0.0000005"}},
]}


def _endpoint(name: str, tag: str, prompt: str, completion: str) -> dict:
    return {"provider_name": name, "tag": tag, "pricing": {"prompt": prompt, "completion": completion}}


GLM_ENDPOINTS = {"data": {"id": "z-ai/glm-5.3", "endpoints": [
    _endpoint("Wafer", "wafer", "0.0000002", "0.000003"),
    _endpoint("Z.AI", "z-ai/fp8", "0.0000014", "0.0000044")]}}
LUNA_ENDPOINTS = {"data": {"id": "openai/gpt-6-luna", "endpoints": [
    _endpoint("OpenAI", "openai/flex", "0.00000005", "0.00000025"),
    _endpoint("OpenAI", "openai", "0.0000001", "0.0000005")]}}


class FakeFetch:
    def __init__(self, fail: bool = False):
        self.urls: list[str] = []
        self.fail = fail

    def __call__(self, url, opener=None):
        self.urls.append(url)
        if self.fail:
            raise urllib.error.URLError("offline")
        if url == pricing.MODELS_URL:
            return CATALOGUE
        if url == pricing.ENDPOINTS_URL.format(model="z-ai/glm-5.3"):
            return GLM_ENDPOINTS
        if url == pricing.ENDPOINTS_URL.format(model="openai/gpt-6-luna"):
            return LUNA_ENDPOINTS
        raise AssertionError(url)


GLM = {"provider": "openrouter", "model": "z-ai/glm-5.3", "k_repeats": 1, "provider_order": ["z-ai/fp8"]}
LUNA = {"provider": "openrouter", "model": "openai/gpt-6-luna", "k_repeats": 1}


# --- member options ------------------------------------------------------------

def test_member_options_are_validated_and_kept_only_when_set():
    plain = {"provider": "openrouter", "model": "m", "k_repeats": 2}
    assert db.normalize_member(plain) == plain   # older protocol rows compare equal
    full = {**plain, "reasoning_effort": "medium", "max_tokens": 32000, "json_mode": False,
            "provider_order": ["xai"], "temperature": 1, "est_output_tokens": 9000}
    got = db.normalize_member(full)
    assert got == {**full, "temperature": 1.0}
    assert db.member_request_options(got) == {"reasoning_effort": "medium", "max_tokens": 32000,
                                              "json_mode": False, "provider_order": ["xai"],
                                              "temperature": 1.0}   # est_output_tokens is not sent
    assert db.member_request_options(plain) == {}
    assert db.normalize_member({**plain, "temperature": "omit"})["temperature"] == "omit"
    for bad, match in (({"reasoning_effort": "xhigh"}, "reasoning_effort must be one of"),
                       ({"max_tokens": 0}, "max_tokens must be a positive integer"),
                       ({"max_tokens": True}, "max_tokens must be a positive integer"),
                       ({"est_output_tokens": 1.5}, "est_output_tokens must be a positive integer"),
                       ({"json_mode": "yes"}, "json_mode must be true or false"),
                       ({"provider_order": "xai"}, "provider_order must be a non-empty list"),
                       ({"provider_order": []}, "provider_order must be a non-empty list"),
                       ({"temperature": 3}, r"temperature must be a number in \[0, 2\] or 'omit'"),
                       ({"temperature": "none"}, "temperature must be a number"),
                       ({"max_token": 5}, "unknown fields"), ):
        with pytest.raises(ValueError, match=match):
            db.normalize_member({**plain, **bad})
    with pytest.raises(ValueError, match="apply to openrouter members only"):
        db.normalize_member({"provider": "claude_cli", "model": "haiku", "k_repeats": 1,
                             "reasoning_effort": "low"})
    with pytest.raises(ValueError, match="lacks"):
        db.normalize_member({"provider": "openrouter", "model": "m"})


class OptionsFake(StagedFake):
    """StagedFake that records the keyword options of every call per model."""

    def __init__(self):
        super().__init__()
        self.options: dict[str, list[dict]] = {}

    def __call__(self, prompt, model, system_prompt, **options):
        self.options.setdefault(model, []).append(options)
        return super().__call__(prompt, model, system_prompt)


def test_protocol_options_reach_the_provider_call(tmp_path, monkeypatch, capsys):
    """A protocol member's request options are stored with the protocol and
    passed to its provider on every call; a member without options is called
    exactly as before (no keywords)."""
    study = build(tmp_path)
    cfg = cfg_of(study, "pS")
    cfg["name"] = "pO"
    cfg["members"] = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1},
                      {**GLM, "reasoning_effort": "low", "max_tokens": 32000}]
    write_cfg(study, cfg)
    fake = OptionsFake()
    monkeypatch.setattr(elicit, "get_provider", lambda name: fake)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--protocol", "pO", "--yes"])
    assert "done: 20/20 slots valid" in capsys.readouterr().out
    assert fake.options["haiku"] == [{}] * 10
    assert fake.options["z-ai/glm-5.3"] == [{"reasoning_effort": "low", "max_tokens": 32000,
                                             "provider_order": ["z-ai/fp8"]}] * 10
    con = study.connect()
    members = db.protocol_members(db.protocol_by_name(con, "pO"))
    assert members[1]["reasoning_effort"] == "low" and members[1]["provider_order"] == ["z-ai/fp8"]
    con.close()


# --- catalogue -------------------------------------------------------------------

def test_catalogue_is_fetched_cached_and_refreshed(tmp_path):
    fetch = FakeFetch()
    cat = pricing.load_catalogue(tmp_path, ["z-ai/glm-5.3"], fetch, now=lambda: T0)
    assert fetch.urls == [pricing.MODELS_URL, pricing.ENDPOINTS_URL.format(model="z-ai/glm-5.3")]
    cache = json.loads((tmp_path / pricing.CACHE_FILE).read_text())
    assert cache["fetched"] == T0.isoformat(timespec="seconds") == cat["fetched"]
    assert cache["models"]["openai/gpt-6-luna"]["completion"] == "0.0000005"
    assert [e["tag"] for e in cache["endpoints"]["z-ai/glm-5.3"]] == ["wafer", "z-ai/fp8"]
    # fresh and complete: no fetch; a pinned model the catalogue lacks does not force one
    fetch.urls.clear()
    later = T0 + timedelta(hours=1)
    pricing.load_catalogue(tmp_path, ["z-ai/glm-5.3", "gone/model"], fetch, now=lambda: later)
    assert fetch.urls == []
    # stale, or missing a pinned model's endpoints: fetched again
    pricing.load_catalogue(tmp_path, [], fetch, now=lambda: T0 + timedelta(hours=25))
    assert fetch.urls == [pricing.MODELS_URL]
    fetch.urls.clear()
    pricing.load_catalogue(tmp_path, ["openai/gpt-6-luna"], fetch, now=lambda: T0 + timedelta(hours=25))
    assert fetch.urls[0] == pricing.MODELS_URL
    # a corrupt cache is ignored; no study root means no cache file at all
    (tmp_path / pricing.CACHE_FILE).write_text("{not json")
    assert pricing.load_catalogue(tmp_path, [], FakeFetch(), now=lambda: T0) is not None
    assert pricing.load_catalogue(None, [], FakeFetch(), now=lambda: T0)["models"]


def test_offline_falls_back_to_the_recorded_prices(tmp_path, capsys):
    member = {"provider": "openrouter", "k_repeats": 1}
    prices = pricing.member_prices(
        [{**member, "model": "z-ai/glm-5.3", "provider_order": ["z-ai"]},
         {**member, "model": "openai/gpt-6-luna"},
         {**member, "model": "deepseek/deepseek-v4.1-flash", "provider_order": ["deepinfra/fp8"]},
         {**member, "model": "nobody/unknown"}],
        tmp_path, FakeFetch(fail=True))
    assert "catalogue fetch failed (URLError" in capsys.readouterr().out
    assert not (tmp_path / pricing.CACHE_FILE).exists()
    recorded = {m["id"]: m for m in json.loads(pricing.FALLBACK_FILE.read_text())["members"]}
    # pinned to the recorded first-party endpoint: its recorded price
    glm, source = prices["z-ai/glm-5.3"]
    want = recorded["z-ai/glm-5.3"]["first_party_endpoint"]["prompt_usd_per_m"] / 1e6
    assert glm["prompt"] == pytest.approx(want) and "first-party endpoint, offline fallback" in source
    # unpinned, or pinned to an endpoint the file does not record: the recorded top-level price
    luna, source = prices["openai/gpt-6-luna"]
    assert luna["completion"] == pytest.approx(recorded["openai/gpt-6-luna"]["completion_usd_per_m"] / 1e6)
    ds, source = prices["deepseek/deepseek-v4.1-flash"]
    want = recorded["deepseek/deepseek-v4.1-flash"]["prompt_usd_per_m"] / 1e6
    assert ds["prompt"] == pytest.approx(want) and source.startswith("top endpoint (pinned endpoint not")
    assert prices["nobody/unknown"] is None


def test_pinned_member_is_priced_at_its_endpoint():
    eps = GLM_ENDPOINTS["data"]["endpoints"]
    assert pricing.match_endpoint(eps, ["z-ai/fp8"])["provider_name"] == "Z.AI"   # exact tag
    assert pricing.match_endpoint(eps, ["z-ai"])["tag"] == "z-ai/fp8"            # base slug
    assert pricing.match_endpoint(eps, ["Z.AI"])["tag"] == "z-ai/fp8"            # provider name
    assert pricing.match_endpoint(eps, ["nobody", "wafer"])["tag"] == "wafer"     # order respected
    assert pricing.match_endpoint(eps, ["nobody"]) is None
    # an exact tag beats a base-slug match listed earlier (openai/flex is half price)
    assert pricing.match_endpoint(LUNA_ENDPOINTS["data"]["endpoints"], ["openai"])["tag"] == "openai"
    prices = pricing.member_prices([GLM, LUNA, {**LUNA, "model": "gone/model"},
                                    {**GLM, "model": "openai/gpt-6-luna", "provider_order": ["nobody"]}],
                                   None, FakeFetch(), now=lambda: T0)
    glm, source = prices["z-ai/glm-5.3"]
    # the pinned endpoint's price, not the catalogue's 0.2 top price
    assert glm == {"prompt": pytest.approx(1.4e-6), "completion": pytest.approx(4.4e-6)}
    assert source.startswith("endpoint z-ai/fp8, catalogue 2026-10-01")
    assert prices["gone/model"] is None
    # the last member (same model as LUNA, pinned to an absent provider) overrides: no price
    assert prices["openai/gpt-6-luna"] is None


def test_estimate_scales_tokens_by_the_output_factors():
    jobs = [{"prompt": "x" * 3996}, {"prompt": "x" * 7996}]   # + 4 system chars: 1000 and 2000 tokens
    per_token = {"prompt": 1e-6, "completion": 2e-6}
    low, mid, high = pricing.estimate(jobs, {"model": "m"}, per_token, "SYS!")
    out = 2 * pricing.DEFAULT_OUTPUT_TOKENS * 2e-6
    assert (low, mid, high) == pytest.approx((3000e-6 + 0.5 * out, 3000e-6 + out, 3000e-6 + 2 * out))
    low2, mid2, high2 = pricing.estimate(jobs, {"model": "m", "est_output_tokens": 100}, per_token, "SYS!")
    assert mid2 == pytest.approx(3000e-6 + 200 * 2e-6)
    assert pricing.DEFAULT_OUTPUT_TOKENS == 6000 and pricing.OUTPUT_FACTORS == (0.5, 1.0, 2.0)


def test_smoke_file_supports_the_default_output_assumption():
    """DEFAULT_OUTPUT_TOKENS is the mean completion length of the answered
    calls in research/smoke_openrouter.json (rounded to 1k)."""
    rows = [r for r in json.loads((ROOT / "research/smoke_openrouter.json").read_text())["rows"]
            if r.get("completion_tokens")]
    mean = sum(r["completion_tokens"] for r in rows) / len(rows)
    assert len(rows) == 19 and round(mean, -3) == pricing.DEFAULT_OUTPUT_TOKENS


# --- the plan --------------------------------------------------------------------

def test_plan_prices_openrouter_members_without_history(tmp_path, monkeypatch, capsys):
    study = build(tmp_path)
    cfg = cfg_of(study, "pS")
    cfg["name"] = "pP"
    cfg["members"] = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1},
                      {**GLM, "est_output_tokens": 10000}, LUNA]
    write_cfg(study, cfg)
    monkeypatch.setattr(pricing, "fetch_json", FakeFetch())
    monkeypatch.setattr(elicit, "get_provider",
                        lambda name: (_ for _ in ()).throw(AssertionError("provider called")))
    elicit.main(["--study", str(study.root), "--protocol", "pP", "--dry-run"])
    out = capsys.readouterr().out
    assert not list(study.root.glob("voi.db*"))
    assert (study.root / pricing.CACHE_FILE).exists()   # the price cache is the only file written
    assert "claude_cli:haiku: 10 slots (decision 5, instrument 5), estimated cost unknown" in out
    line = next(ln for ln in out.splitlines() if ln.startswith("  openrouter:z-ai/glm-5.3:"))
    assert "10 slots (decision 5, instrument 5), estimated cost $" in line
    assert "10,000 output tokens/call at $1.4 / $4.4 per M, endpoint z-ai/fp8, catalogue" in line
    luna = next(ln for ln in out.splitlines() if ln.startswith("  openrouter:openai/gpt-6-luna:"))
    assert "6,000 output tokens/call at $0.1 / $0.5 per M, catalogue" in luna
    total = next(ln for ln in out.splitlines() if ln.startswith("  estimated total:"))
    assert "(low $" in total and total.endswith("+ unknown")
    # the totals are the sums of the member estimates, recomputed here from the jobs
    con = study.connect_copy()
    _, prot, members, jobs = elicit.plan(con, study, elicit.argparse.Namespace(
        protocol="pP", scenarios=None, k=None, members=None, stage=None), preview=True)
    con.close()
    want = [0.0, 0.0, 0.0]
    for m, per_token in ((members[1], {"prompt": 1.4e-6, "completion": 4.4e-6}),
                         (members[2], {"prompt": 1e-7, "completion": 5e-7})):
        mine = [j for j in jobs if j["member"]["model"] == m["model"]]
        want = [w + e for w, e in zip(want, pricing.estimate(mine, m, per_token, elicit.SYSTEM_PROMPT),
                                      strict=True)]
    assert f"estimated total: ${want[1]:.2f} (low ${want[0]:.2f}, high ${want[2]:.2f}) + unknown" in out


def test_stored_attempts_take_precedence_over_catalogue_prices(tmp_path, monkeypatch, capsys):
    study = build(tmp_path)
    cfg = cfg_of(study, "pS")
    cfg["name"] = "pQ"
    cfg["members"] = [{**LUNA, "k_repeats": 1}]
    write_cfg(study, cfg)
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake(cost=0.02))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    elicit.main(["--study", str(study.root), "--protocol", "pQ", "--stage", "decision", "--yes"])
    capsys.readouterr()
    fetch = FakeFetch()
    monkeypatch.setattr(pricing, "fetch_json", fetch)
    elicit.main(["--study", str(study.root), "--protocol", "pQ", "--dry-run"])
    out = capsys.readouterr().out
    assert ("openrouter:openai/gpt-6-luna: 5 slots (decision 0, instrument 5), estimated cost $0.10"
            " (mean $0.0200/attempt over 5 stored attempts)") in out
    assert "estimated total: $0.10\n" in out and fetch.urls == []   # no catalogue needed


# --- the final-run protocol files --------------------------------------------------

FINAL_MODELS = ["deepseek/deepseek-v4.1-flash", "z-ai/glm-5.3", "xiaomi/mimo-v2.6-flash",
                "openai/gpt-6-luna", "google/gemini-3.8-flash", "x-ai/grok-4.7"]


@pytest.mark.parametrize("name, perspective", [("final", "society"), ("final_dev", "developer")])
def test_final_protocols(name, perspective):
    cfg = yaml.safe_load((STUDY / f"protocols/{name}.yaml").read_text())
    p001 = yaml.safe_load((STUDY / "protocols/p001.yaml").read_text())
    assert cfg["name"] == name and cfg["stages"] == p001["stages"]
    assert [s["params"] for s in cfg["stages"]] == [DECISION_PARAMS, INSTRUMENT_PARAMS]
    assert cfg["template_vars"] == {"perspective": perspective, "anchors_decision": "",
                                    "anchors_instrument": "", "context_mode": "curated"}
    members = db.normalize_members(cfg)
    assert [m["model"] for m in members] == FINAL_MODELS
    assert all(m["provider"] == "openrouter" and m["k_repeats"] == 1 and m["provider_order"] for m in members)
    assert not any(m["model"].startswith("anthropic/") for m in members)
    assert len({m["model"].split("/")[0] for m in members}) == 6   # six developers
    effort = {m["model"]: m.get("reasoning_effort") for m in members}
    assert effort["deepseek/deepseek-v4.1-flash"] == effort["z-ai/glm-5.3"] == "low"
    assert {effort[m] for m in FINAL_MODELS[2:]} == {"medium"}


def test_final_and_final_dev_differ_only_in_perspective_and_notes():
    final = yaml.safe_load((STUDY / "protocols/final.yaml").read_text())
    dev = yaml.safe_load((STUDY / "protocols/final_dev.yaml").read_text())
    for cfg in (final, dev):
        cfg.pop("name"), cfg.pop("notes"), cfg["template_vars"].pop("perspective")
    assert final == dev


def test_unbilled_failures_do_not_pull_the_stored_mean_to_zero(tmp_path):
    """A member whose only stored rows are free failures (an unroutable
    endpoint's HTTP 404) has no stored mean, so the catalogue prices it."""
    study = build(tmp_path)
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    pid = db.get_or_create_protocol(con, study.protocol_path("pS"), study.root)
    m = {"provider": "openrouter", "model": "z-ai/glm-5.3"}
    db.insert_elicitation(con, 1, pid, m["provider"], m["model"], 0, "h", '{"error": {"code": 404}}',
                          False, "http: status 404: no endpoints")
    con.commit()
    assert elicit.member_mean_cost(con, m) is None
    db.insert_elicitation(con, 2, pid, m["provider"], m["model"], 0, "h", '{"usage": {"cost": 0.03}}',
                          False, "truncated: finish_reason=length")
    con.commit()
    assert elicit.member_mean_cost(con, m) == (pytest.approx(0.03), 1)
    con.close()


def test_malformed_catalogue_pricing_is_unknown_not_a_crash():
    def fetch(url, opener=None):
        if url == pricing.MODELS_URL:
            return {"data": [{"id": "a/x", "pricing": {"prompt": "1e-6"}},
                             {"id": "z-ai/glm-5.3", "pricing": {"prompt": "1", "completion": "1"}}]}
        return {"data": {"endpoints": [{"tag": "z-ai/fp8", "pricing": None}]}}

    prices = pricing.member_prices([{"model": "a/x"}, GLM], None, fetch, now=lambda: T0)
    assert prices == {"a/x": None, "z-ai/glm-5.3": None}
