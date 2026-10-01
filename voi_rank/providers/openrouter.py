"""OpenRouter chat-completions provider (urllib only, no third-party HTTP
client).

API key: environment variable OPENROUTER_API_KEY, else the KEY=VALUE line of
the repo-root .env file (an optional leading 'export ', surrounding quotes
and a trailing ' # comment' are dropped). The key is never printed; a
missing key raises a clear error from api_key(), which the elicitation
harness calls before printing its plan, and check_key() verifies it against
the free GET /auth/key endpoint once a paid run is confirmed, so a wrong key
never burns a slot. Nothing in the repository calls this provider by
default: it runs only for protocol members declared with provider:
openrouter.

Request shape (request_body), per protocol member (db.MEMBER_OPTIONS; every
field optional): reasoning_effort (sent as reasoning.effort), max_tokens
(default MAX_TOKENS), json_mode (default on: response_format json_object
plus provider.require_parameters, so no endpoint that would ignore a
parameter is picked), provider_order (provider.order with allow_fallbacks
false: the endpoint is pinned, so its price and weights cannot move under a
run) and temperature (default: omitted for openai/* models, which reject it,
else TEMPERATURE; 'omit' sends none, for an endpoint such as Google Vertex
that does not list the parameter, which require_parameters would otherwise
filter out). The user message is one content block carrying an
ephemeral cache_control breakpoint: Anthropic caches only behind such a
marker; the other providers cache automatically and ignore it.

TLS (ssl_context): SSL_CERT_FILE from the environment or .env names the CA
bundle; without it, a default context that loaded no CA certificate (uv's
standalone Python on some Linux systems) also loads SYSTEM_CA_FILE when it
exists.

Error strings (first token is the error class):
  'http: status <code>[ retry-after <n>s]: <body>'  HTTP error response
  'http: <reason>'                                   transport failure
  'api: ...'      top-level error, choices[0].error, finish_reason error
  'truncated: ...' finish_reason length: the answer hit max_tokens. Billed.
                  The harness retries it once with the same cap, as any
                  non-HTTP failure (reasoning length varies from call to
                  call, so the retry usually lands); the class stays
                  countable on its own.
  'refusal: ...'  finish_reason content_filter, a provider safety block
                  included (the first 200 characters of
                  the answer, else the finish reason); the harness classifies
                  a declining plain-text answer the same way (elicit.refusal)
  'json: ...' / 'schema: ...'                        unparseable body
"""

from __future__ import annotations

import http.client
import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from voi_rank.dotenv import ENV_FILE, read_env_file

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
AUTH_URL = "https://openrouter.ai/api/v1/auth/key"
AUTH_TIMEOUT_S = 30
ENV_KEY = "OPENROUTER_API_KEY"
# urllib applies this per blocking socket operation (connect, then each
# read), not as a wall-clock cap on the whole call: a slow but steady stream
# can legitimately exceed it in total.
HTTP_TIMEOUT_S = 600
TEMPERATURE = 1.0
# A cap that should never bind on a normal answer. In the 2026-10-01 smoke
# test (research/smoke_openrouter.json) GLM 5.3 spent all of a 16k cap on
# reasoning and returned no answer; Grok 4.7 and GLM 5.3 Flash used 11k-14k
# reasoning tokens. Length is controlled with reasoning_effort, not the cap.
# A cap is always sent: a provider's own default varies and is not recorded.
MAX_TOKENS = 32000
# models that reject a temperature parameter (OpenAI's reasoning models)
NO_TEMPERATURE_PREFIXES = ("openai/",)
SSL_CERT_ENV = "SSL_CERT_FILE"
SYSTEM_CA_FILE = Path("/etc/ssl/certs/ca-certificates.crt")
# OpenRouter's optional app-attribution headers (shown on their dashboard):
# HTTP-Referer plus X-OpenRouter-Title (X-Title is the legacy spelling, still
# sent for compatibility)
REFERER = "https://voi-rank.invalid"
TITLE = "voi-rank"
REFUSAL_FINISH_REASON = "content_filter"
REFUSAL_CHARS = 200


def _read_env_file(path: Path | None = None) -> dict[str, str]:
    """The .env settings (voi_rank.dotenv); ENV_FILE is read at call time so
    a test can point it elsewhere."""
    return read_env_file(path or ENV_FILE)


def ssl_context(system_ca: Path | None = None) -> ssl.SSLContext:
    """The TLS context of every OpenRouter request: the CA bundle SSL_CERT_FILE
    names (environment, else .env); else Python's default context, plus the
    system bundle (system_ca, default SYSTEM_CA_FILE) when the default
    loaded no CA certificate and the bundle exists."""
    cafile = os.environ.get(SSL_CERT_ENV) or _read_env_file().get(SSL_CERT_ENV)
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    ctx = ssl.create_default_context()
    bundle = system_ca or SYSTEM_CA_FILE
    if not ctx.get_ca_certs() and bundle.exists():
        ctx.load_verify_locations(cafile=str(bundle))
    return ctx


def api_key() -> str:
    key = os.environ.get(ENV_KEY) or _read_env_file().get(ENV_KEY)
    if not key:
        raise RuntimeError(
            f"{ENV_KEY} is not set: export it or put '{ENV_KEY}=...' in {ENV_FILE}"
            " (see .env.example)")
    return key


def check_key(key: str, opener=None, url: str = AUTH_URL) -> dict:
    """Preflight: GET /auth/key with the bearer key (free, no generation).
    Returns the endpoint's 'data' object (label, usage, limit, ...). Raises
    RuntimeError on 401/403 (the key is rejected) and on any other failure
    (the key could not be verified), so the caller submits nothing. opener
    and url are injectable for tests; the default opener is urlopen."""
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"}, method="GET")
    try:
        with opener(req, timeout=AUTH_TIMEOUT_S, context=ssl_context()) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", errors="replace")[:300]
        if ex.code in (401, 403):
            raise RuntimeError(
                f"OpenRouter rejected {ENV_KEY} (status {ex.code}): {body}; fix the key in the"
                f" environment or {ENV_FILE} (no elicitation call was made)") from None
        raise RuntimeError(f"OpenRouter key preflight failed (status {ex.code}): {body}") from None
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as ex:
        raise RuntimeError(f"OpenRouter key preflight failed: {ex}") from None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as ex:
        raise RuntimeError(f"OpenRouter key preflight returned no JSON: {ex}") from None
    info = data.get("data") if isinstance(data, dict) else None
    if not isinstance(info, dict):
        raise RuntimeError(f"OpenRouter key preflight returned an unexpected body: {raw[:300]}")
    return info


def default_temperature(model: str) -> float | None:
    """TEMPERATURE, or None (the parameter is omitted) for a model that rejects it."""
    return None if model.startswith(NO_TEMPERATURE_PREFIXES) else TEMPERATURE


def request_body(prompt: str, model: str, system_prompt: str, *, reasoning_effort: str | None = None,
                 max_tokens: int | None = None, json_mode: bool | None = None,
                 provider_order: list[str] | None = None, temperature: float | str | None = None) -> dict:
    """The chat-completions body of one call. The keywords are a member's
    request options (db.MEMBER_OPTIONS); None means the default."""
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": [
                         {"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}]}],
        "max_tokens": MAX_TOKENS if max_tokens is None else max_tokens,
    }  # usage (incl. cost) is always returned; usage.include is deprecated
    temperature = default_temperature(model) if temperature is None else temperature
    if temperature is not None and temperature != "omit":
        body["temperature"] = temperature
    if reasoning_effort is not None:
        body["reasoning"] = {"effort": reasoning_effort}
    provider: dict = {}
    if json_mode is None or json_mode:
        body["response_format"] = {"type": "json_object"}
        provider["require_parameters"] = True
    if provider_order:
        provider["order"] = list(provider_order)
        provider["allow_fallbacks"] = False
    if provider:
        body["provider"] = provider
    return body


def build_request(prompt: str, model: str, system_prompt: str, key: str,
                  **options) -> urllib.request.Request:
    body = request_body(prompt, model, system_prompt, **options)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": REFERER,
        "X-OpenRouter-Title": TITLE,
        "X-Title": TITLE,
    }
    return urllib.request.Request(OPENROUTER_URL, data=json.dumps(body).encode(),
                                  headers=headers, method="POST")


def retry_after_seconds(headers) -> int | None:
    """Retry-After as delay-seconds; the HTTP-date form is ignored."""
    value = headers.get("Retry-After") if headers is not None else None
    if value is None:
        return None
    value = str(value).strip()
    return int(value) if value.isdigit() else None


def usage_tokens(usage: dict | None) -> dict:
    """{prompt, completion, reasoning, cached} token counts of a response's
    usage object; None where the provider reported none."""
    usage = usage if isinstance(usage, dict) else {}
    pdet = usage.get("prompt_tokens_details")
    cdet = usage.get("completion_tokens_details")
    pdet = pdet if isinstance(pdet, dict) else {}
    cdet = cdet if isinstance(cdet, dict) else {}
    return {"prompt": usage.get("prompt_tokens"), "completion": usage.get("completion_tokens"),
            "reasoning": cdet.get("reasoning_tokens"), "cached": pdet.get("cached_tokens")}


def call_openrouter(prompt: str, model: str, system_prompt: str, **options):
    """Returns (envelope | None, raw_body, error | None), the same triple shape
    as claude_cli.call_claude: envelope = {'result': text, 'total_cost_usd':
    usage.cost or None, 'model', 'id', 'usage', 'tokens' (usage_tokens),
    'finish_reason', 'provider'}; raw_body is the full response body, stored
    verbatim in the DB, so all of these stay recoverable from it. Any error
    on a parsed JSON object ('api:', 'truncated:' or 'schema:') still
    returns the envelope, so a paid failure's usage.cost is recorded by the
    caller exactly as db.envelope_cost reads it back from the stored body.
    options: the member's request options (request_body)."""
    req = build_request(prompt, model, system_prompt, api_key(), **options)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S, context=ssl_context()) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as ex:
        raw = ex.read().decode("utf-8", errors="replace")
        wait = retry_after_seconds(ex.headers)
        tag = f" retry-after {wait}s" if wait is not None else ""
        return None, raw, f"http: status {ex.code}{tag}: {raw[:300]}"
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as ex:
        return None, "", f"http: {ex}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as ex:
        return None, raw, f"json: response parse failed: {ex}"
    if not isinstance(data, dict):
        return None, raw, "json: response is not an object"
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
    envelope = {
        "result": "",
        "total_cost_usd": usage.get("cost") if usage else None,
        "model": data.get("model", model),
        "id": data.get("id"),
        "usage": usage,
        "tokens": usage_tokens(usage),
        "finish_reason": None,
        "provider": data.get("provider"),
    }
    if data.get("error"):
        return envelope, raw, f"api: {json.dumps(data['error'])[:300]}"
    try:
        choice = data["choices"][0]
    except (KeyError, IndexError, TypeError):
        choice = None
    if not isinstance(choice, dict):
        return envelope, raw, "schema: no choices[0] in response"
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    text = message.get("content")
    if text is not None:
        envelope["result"] = text if isinstance(text, str) else json.dumps(text)
    finish = choice.get("finish_reason")
    envelope["finish_reason"] = finish
    # before the choice error: a provider safety block (Gemini: choices[0].error
    # 403 'SAFETY', content_policy_violation) also finishes content_filter
    if finish == REFUSAL_FINISH_REASON:
        text_part = envelope["result"][:REFUSAL_CHARS] or f"finish_reason={finish}"
        return envelope, raw, f"refusal: {text_part}"
    if choice.get("error"):
        return envelope, raw, f"api: choices[0].error: {json.dumps(choice['error'])[:300]}"
    if finish == "error":
        return envelope, raw, f"api: finish_reason={finish}"
    if finish == "length":   # before the content check: a cap spent on reasoning leaves no content
        cap = options.get("max_tokens") or MAX_TOKENS
        return envelope, raw, (f"truncated: finish_reason=length after"
                               f" {envelope['tokens']['completion']} completion tokens (max_tokens {cap})")
    if text is None:
        return envelope, raw, "schema: no choices[0].message.content in response"
    return envelope, raw, None
