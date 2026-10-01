"""OpenRouter provider, fully offline: urllib.request.urlopen is monkeypatched.
No test here (or anywhere) reaches the network."""

import http.client
import io
import json
import urllib.error
import urllib.request

import pytest

from voi_rank import elicit
from voi_rank.providers import get_provider, openrouter


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _ok_body(text="{\"parameters\": {}}", cost=0.0123, finish="stop"):
    return json.dumps({
        "id": "gen-1", "model": "openai/gpt-4o-mini",
        "choices": [{"message": {"role": "assistant", "content": text},
                     "finish_reason": finish}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": cost},
    })


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")


def test_get_provider_names():
    assert get_provider("openrouter") is openrouter.call_openrouter
    assert callable(get_provider("claude_cli"))
    with pytest.raises(ValueError):
        get_provider("nope")


def test_request_shape_and_envelope(monkeypatch, key):
    captured = {}

    def fake_urlopen(req, timeout=None, context=None):
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        captured["body"] = json.loads(req.data.decode())
        captured["method"] = req.get_method()
        return FakeResponse(_ok_body().encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    env, raw, err = openrouter.call_openrouter("PROMPT", "openai/gpt-4o-mini", "SYS")
    assert err is None
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["method"] == "POST"
    assert captured["headers"]["authorization"] == "Bearer test-key-not-real"
    assert captured["headers"]["content-type"] == "application/json"
    assert "http-referer" in captured["headers"]
    assert captured["headers"]["x-openrouter-title"] == captured["headers"]["x-title"] == "voi-rank"
    body = captured["body"]
    assert "usage" not in body  # usage.include is deprecated; cost is always returned
    assert body["model"] == "openai/gpt-4o-mini"
    # the user message is one block with an ephemeral cache breakpoint
    assert body["messages"] == [{"role": "system", "content": "SYS"},
                                {"role": "user", "content": [{"type": "text", "text": "PROMPT",
                                                              "cache_control": {"type": "ephemeral"}}]}]
    # defaults: the high cap, JSON mode with require_parameters, no temperature for openai/*,
    # no reasoning setting and no pinned endpoint
    assert body["max_tokens"] == 32000 and "temperature" not in body
    assert body["response_format"] == {"type": "json_object"}
    assert body["provider"] == {"require_parameters": True}
    assert "reasoning" not in body
    assert env["finish_reason"] == "stop"
    assert env["result"] == "{\"parameters\": {}}"
    assert env["total_cost_usd"] == pytest.approx(0.0123)
    assert env["model"] == "openai/gpt-4o-mini" and env["id"] == "gen-1"
    assert env["usage"]["completion_tokens"] == 5
    assert json.loads(raw)["choices"][0]["finish_reason"] == "stop"


def test_missing_key_raises_only_on_call(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(openrouter, "ENV_FILE", tmp_path / ".env")  # absent
    called = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        openrouter.call_openrouter("x", "m", "s")
    assert not called


def test_key_from_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nOTHER=1\nOPENROUTER_API_KEY=\"from-file\"\n")
    monkeypatch.setattr(openrouter, "ENV_FILE", env_file)
    assert openrouter.api_key() == "from-file"


def test_http_error_returns_triple(monkeypatch, key):
    def fake_urlopen(req, timeout=None, context=None):
        raise urllib.error.HTTPError(req.full_url, 402, "Payment Required", {},
                                     io.BytesIO(b'{"error": {"message": "no credits"}}'))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    env, raw, err = openrouter.call_openrouter("x", "m", "s")
    assert env is None and "no credits" in raw and err.startswith("http: status 402")


def test_api_error_body(monkeypatch, key):
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, **kw: FakeResponse(
                            b'{"error": {"code": 400, "message": "bad model"}}'))
    env, raw, err = openrouter.call_openrouter("x", "m", "s")
    assert err.startswith("api:") and "bad model" in err
    assert env["result"] == "" and env["total_cost_usd"] is None   # a parsed body keeps its envelope


def test_truncated_response_is_flagged(monkeypatch, key):
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, **kw: FakeResponse(_ok_body(finish="length").encode()))
    env, raw, err = openrouter.call_openrouter("x", "m", "s")
    assert env is not None and "truncated" in err


def test_choice_error_and_error_finish_reasons_are_api_errors(monkeypatch, key):
    body = json.loads(_ok_body())
    body["choices"][0]["error"] = {"code": 502, "message": "upstream failed",
                                   "metadata": {"error_type": "provider"}}
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, **kw: FakeResponse(json.dumps(body).encode()))
    env, raw, err = openrouter.call_openrouter("x", "m", "s")
    assert err.startswith("api: choices[0].error") and "upstream failed" in err
    assert env["total_cost_usd"] == pytest.approx(0.0123)  # a paid failure keeps its cost
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, **kw: FakeResponse(_ok_body(finish="error").encode()))
    assert openrouter.call_openrouter("x", "m", "s")[2] == "api: finish_reason=error"
    # a content_filter finish is a refusal: the first 200 characters of the answer, else the reason
    long_text = "I cannot help with this request because it concerns pathogens. " * 10
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, **kw: FakeResponse(_ok_body(text=long_text,
                                                                        finish="content_filter").encode()))
    env, raw, err = openrouter.call_openrouter("x", "m", "s")
    assert err == "refusal: " + long_text[:200] and env["total_cost_usd"] == pytest.approx(0.0123)
    # a provider safety block carries a choice error and a content_filter finish: a refusal
    blocked = json.loads(_ok_body(text="Partial answer", finish="content_filter"))
    blocked["choices"][0]["error"] = {"code": 403, "message": "SAFETY",
                                      "metadata": {"error_type": "content_policy_violation"}}
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, **kw: FakeResponse(json.dumps(blocked).encode()))
    assert openrouter.call_openrouter("x", "m", "s")[2] == "refusal: Partial answer"
    empty = _ok_body(text="", finish="content_filter").encode()
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, **kw: FakeResponse(empty))
    assert openrouter.call_openrouter("x", "m", "s")[2] == "refusal: finish_reason=content_filter"
    assert elicit.retry_delay("refusal: finish_reason=content_filter") == 0.0
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, **kw: FakeResponse(b'{"choices": [{"message": {}}]}'))
    assert openrouter.call_openrouter("x", "m", "s")[2].startswith("schema:")


def test_retry_after_header_is_recorded_in_the_error(monkeypatch, key):
    def raiser(headers):
        def fake_urlopen(req, timeout=None, context=None):
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", headers,
                                         io.BytesIO(b'{"error": {"message": "slow down"}}'))
        return fake_urlopen

    monkeypatch.setattr(urllib.request, "urlopen", raiser({"Retry-After": "7"}))
    env, raw, err = openrouter.call_openrouter("x", "m", "s")
    assert env is None and err.startswith("http: status 429 retry-after 7s:") and "slow down" in err
    assert elicit.retry_delay(err) == 7.0
    monkeypatch.setattr(urllib.request, "urlopen",
                        raiser({"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}))
    err = openrouter.call_openrouter("x", "m", "s")[2]
    assert err.startswith("http: status 429: ") and elicit.retry_delay(err) == elicit.TRANSPORT_RETRY_DELAY_S
    monkeypatch.setattr(urllib.request, "urlopen", raiser(None))
    assert openrouter.call_openrouter("x", "m", "s")[2].startswith("http: status 429: ")


def test_env_file_parser_handles_export_quotes_and_comments(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("export OPENROUTER_API_KEY=abc # my key\n"
                        "QUOTED=\"v # not a comment\"\nSINGLE='x'\nPLAIN=y\n# c\n"
                        "export  Z = z  \nNOEQ\n"
                        "QC=\"sk-or-abc\" # my key\nQS='sk-abc' #k\nEMPTY=\nNOSPACE=a#b\n"
                        "MIXED=\"it's\" # q\n")
    assert openrouter._read_env_file(env_file) == {
        "OPENROUTER_API_KEY": "abc", "QUOTED": "v # not a comment", "SINGLE": "x",
        "PLAIN": "y", "Z": "z", "QC": "sk-or-abc", "QS": "sk-abc", "EMPTY": "",
        "NOSPACE": "a#b", "MIXED": "it's"}
    # the quoted-with-comment form yields a working bearer key
    monkeypatch_env = tmp_path / "k.env"
    monkeypatch_env.write_text("OPENROUTER_API_KEY=\"from-file\" # comment\n")
    assert openrouter._read_env_file(monkeypatch_env)["OPENROUTER_API_KEY"] == "from-file"


def test_transport_exceptions_are_http_errors_with_backoff(monkeypatch, key):
    for exc in (http.client.IncompleteRead(b"abc"), http.client.RemoteDisconnected("closed"),
                TimeoutError("timed out"), urllib.error.URLError("no route")):
        def raiser(req, timeout=None, context=None, e=exc):
            raise e
        monkeypatch.setattr(urllib.request, "urlopen", raiser)
        env, raw, err = openrouter.call_openrouter("x", "m", "s")
        assert env is None and raw == "" and err.startswith("http: "), err
        assert elicit.retry_delay(err) == elicit.TRANSPORT_RETRY_DELAY_S


def test_check_key_preflight(monkeypatch):
    seen = {}

    def ok(req, timeout=None, context=None):
        seen.update(url=req.full_url, method=req.get_method(),
                    auth=req.get_header("Authorization"))
        return FakeResponse(b'{"data": {"label": "lab", "usage": 1.5, "limit": null}}')

    info = openrouter.check_key("k-not-real", opener=ok, url="https://example.invalid/auth")
    assert info == {"label": "lab", "usage": 1.5, "limit": None}
    assert seen == {"url": "https://example.invalid/auth", "method": "GET", "auth": "Bearer k-not-real"}

    def http_error(code):
        def opener(req, timeout=None, context=None):
            raise urllib.error.HTTPError(req.full_url, code, "x", {},
                                         io.BytesIO(b'{"error": {"message": "User not found."}}'))
        return opener

    for code in (401, 403):
        with pytest.raises(RuntimeError,
                           match=rf"rejected OPENROUTER_API_KEY \(status {code}\).*User not found"):
            openrouter.check_key("k", opener=http_error(code))
    with pytest.raises(RuntimeError, match=r"preflight failed \(status 500\)"):
        openrouter.check_key("k", opener=http_error(500))

    def down(req, timeout=None, context=None):
        raise urllib.error.URLError("no route")
    with pytest.raises(RuntimeError, match="preflight failed: <urlopen error no route>"):
        openrouter.check_key("k", opener=down)
    with pytest.raises(RuntimeError, match="no JSON"):
        openrouter.check_key("k", opener=lambda req, **kw: FakeResponse(b"nope"))
    with pytest.raises(RuntimeError, match="unexpected body"):
        openrouter.check_key("k", opener=lambda req, **kw: FakeResponse(b'{"x": 1}'))
    # the default opener is urlopen (which the conftest fakes for the auth URL)
    assert openrouter.check_key("k")["label"] == "test" and openrouter.AUTH_URL.endswith("/auth/key")


def test_paid_response_without_content_keeps_its_cost(monkeypatch, key):
    """A body with usage.cost but no choices[0].message.content is a schema
    error whose envelope still carries the cost, so attempt_once's printed
    total matches what db.envelope_cost reads back from the stored body."""
    from voi_rank import db
    body = json.dumps({"choices": [{"message": {"role": "assistant"}, "finish_reason": "stop"}],
                       "usage": {"cost": 0.05}})
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, **kw: FakeResponse(body.encode()))
    env, raw, err = openrouter.call_openrouter("x", "m", "s")
    assert err == "schema: no choices[0].message.content in response"
    assert env["total_cost_usd"] == pytest.approx(0.05) and env["result"] == ""
    att = elicit.attempt_once(openrouter.call_openrouter, "x", "m")
    assert att["cost"] == pytest.approx(db.envelope_cost(att["raw"])) == pytest.approx(0.05)
    # no choices at all, and a top-level error: same rule
    for text in ('{"usage": {"cost": 0.02}}', '{"error": {"code": 500}, "usage": {"cost": 0.02}}'):
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, t=text, **kw: FakeResponse(t.encode()))
        env, raw, err = openrouter.call_openrouter("x", "m", "s")
        assert err is not None and env["total_cost_usd"] == pytest.approx(0.02)


def test_member_request_options_shape_the_body():
    body = openrouter.request_body("P", "z-ai/glm-5.3", "S", reasoning_effort="low", max_tokens=1234,
                                   provider_order=["z-ai/fp8"])
    assert body["reasoning"] == {"effort": "low"} and body["max_tokens"] == 1234
    assert body["temperature"] == 1.0   # not an openai/* model: the harness default
    assert body["response_format"] == {"type": "json_object"}
    assert body["provider"] == {"require_parameters": True, "order": ["z-ai/fp8"], "allow_fallbacks": False}
    # json_mode false drops response_format and require_parameters; a pinned order stays pinned
    body = openrouter.request_body("P", "x-ai/grok-4.7", "S", json_mode=False, provider_order=["xai"])
    assert "response_format" not in body
    assert body["provider"] == {"order": ["xai"], "allow_fallbacks": False}
    assert "provider" not in openrouter.request_body("P", "m", "S", json_mode=False)
    # an explicit temperature is sent even to an openai/* model; 0 is a value, not a default
    assert openrouter.request_body("P", "openai/gpt-6-luna", "S", temperature=0.0)["temperature"] == 0.0
    assert "temperature" not in openrouter.request_body("P", "openai/gpt-6-luna", "S")
    gemini = openrouter.request_body("P", "google/gemini-3.8-flash", "S", temperature="omit")
    assert "temperature" not in gemini


def test_options_reach_the_wire_and_usage_is_extracted(monkeypatch, key):
    seen = {}
    body = json.loads(_ok_body())
    body["provider"] = "Z.AI"
    body["usage"].update(prompt_tokens_details={"cached_tokens": 1500},
                         completion_tokens_details={"reasoning_tokens": 4000})

    def fake_urlopen(req, timeout=None, context=None):
        seen.update(body=json.loads(req.data.decode()), context=context)
        return FakeResponse(json.dumps(body).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    env, raw, err = openrouter.call_openrouter("P", "z-ai/glm-5.3", "S", reasoning_effort="low",
                                               provider_order=["z-ai/fp8"])
    assert err is None and seen["body"]["reasoning"] == {"effort": "low"}
    assert seen["body"]["provider"]["order"] == ["z-ai/fp8"]
    assert isinstance(seen["context"], openrouter.ssl.SSLContext)   # the TLS context is always passed
    assert env["tokens"] == {"prompt": 10, "completion": 5, "reasoning": 4000, "cached": 1500}
    assert env["provider"] == "Z.AI" and env["finish_reason"] == "stop"
    assert openrouter.usage_tokens(None) == {"prompt": None, "completion": None, "reasoning": None,
                                             "cached": None}


def test_length_finish_is_its_own_billed_error_class_retried_once(monkeypatch, key):
    """A cap spent on reasoning returns no content and finish_reason length:
    'truncated:', not a schema error; billed (the cost is kept) and retried
    once like any non-HTTP failure."""
    body = json.dumps({"choices": [{"message": {"role": "assistant", "content": None},
                                    "finish_reason": "length"}],
                       "usage": {"completion_tokens": 32000, "cost": 0.14}})
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, **kw: FakeResponse(body.encode()))
    env, raw, err = openrouter.call_openrouter("x", "m", "s")
    assert err == "truncated: finish_reason=length after 32000 completion tokens (max_tokens 32000)"
    assert env["total_cost_usd"] == pytest.approx(0.14) and env["finish_reason"] == "length"
    err = openrouter.call_openrouter("x", "m", "s", max_tokens=500)[2]
    assert err.endswith("(max_tokens 500)")
    assert elicit.retry_delay(err) == 0.0 and not elicit.halts_member(err)
    calls = []

    def call(prompt, model, system_prompt, **options):
        calls.append(options)
        return openrouter.call_openrouter(prompt, model, system_prompt, **options)

    atts = elicit.elicit_job(call, "x", "m", sleep=lambda s: None, options={"max_tokens": 500})
    assert [a["error"].split(":")[0] for a in atts] == ["truncated", "truncated"]
    assert calls == [{"max_tokens": 500}] * 2   # both attempts carry the member's options
    assert elicit.billed(atts) and sum(a["cost"] for a in atts) == pytest.approx(0.28)


class FakeContext:
    def __init__(self, cafile=None, n_certs=0):
        self.cafile, self.n_certs, self.loaded = cafile, n_certs, []

    def get_ca_certs(self):
        return [{}] * self.n_certs

    def load_verify_locations(self, cafile=None):
        self.loaded.append(cafile)


def test_ssl_context_honours_ssl_cert_file_then_the_system_bundle(monkeypatch, tmp_path):
    def factory(n_certs):
        return lambda cafile=None: FakeContext(cafile, n_certs)

    env_file = tmp_path / ".env"
    monkeypatch.setattr(openrouter, "ENV_FILE", env_file)
    bundle = tmp_path / "ca.crt"
    bundle.write_text("not read by the fake")
    monkeypatch.setattr(openrouter.ssl, "create_default_context", factory(0))
    # the environment wins
    monkeypatch.setenv("SSL_CERT_FILE", "/env/ca.pem")
    ctx = openrouter.ssl_context(system_ca=bundle)
    assert ctx.cafile == "/env/ca.pem" and ctx.loaded == []
    # else .env
    monkeypatch.delenv("SSL_CERT_FILE")
    env_file.write_text("SSL_CERT_FILE=/dotenv/ca.pem\n")
    assert openrouter.ssl_context(system_ca=bundle).cafile == "/dotenv/ca.pem"
    # else the default context, plus the system bundle when it loaded no CA and the bundle exists
    env_file.write_text("")
    ctx = openrouter.ssl_context(system_ca=bundle)
    assert ctx.cafile is None and ctx.loaded == [str(bundle)]
    assert openrouter.ssl_context(system_ca=tmp_path / "absent.crt").loaded == []
    monkeypatch.setattr(openrouter.ssl, "create_default_context", factory(3))
    assert openrouter.ssl_context(system_ca=bundle).loaded == []   # a default with CAs is kept as is
    assert str(openrouter.SYSTEM_CA_FILE) == "/etc/ssl/certs/ca-certificates.crt"
