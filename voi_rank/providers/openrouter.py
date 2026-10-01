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

Error strings (first token is the error class):
  'http: status <code>[ retry-after <n>s]: <body>'  HTTP error response
  'http: <reason>'                                   transport failure
  'api: ...'      top-level error, choices[0].error, finish_reason error,
                  or a truncated (length) answer
  'refusal: ...'  finish_reason content_filter (the first 200 characters of
                  the answer, else the finish reason); the harness classifies
                  a declining plain-text answer the same way (elicit.refusal)
  'json: ...' / 'schema: ...'                        unparseable body
"""

from __future__ import annotations

import http.client
import json
import os
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
MAX_TOKENS = 4000
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
        with opener(req, timeout=AUTH_TIMEOUT_S) as resp:
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


def build_request(prompt: str, model: str, system_prompt: str, key: str) -> urllib.request.Request:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }  # usage (incl. cost) is always returned; usage.include is deprecated
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


def call_openrouter(prompt: str, model: str, system_prompt: str):
    """Returns (envelope | None, raw_body, error | None), the same triple shape
    as claude_cli.call_claude: envelope = {'result': text, 'total_cost_usd':
    usage.cost or None, 'model', 'id', 'usage'}; raw_body is the full
    response body (stored verbatim in the DB). Any error on a parsed JSON
    object ('api:' or 'schema:') still returns the envelope, so a paid
    failure's usage.cost is recorded by the caller exactly as
    db.envelope_cost reads it back from the stored body."""
    req = build_request(prompt, model, system_prompt, api_key())
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
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
    if choice.get("error"):
        return envelope, raw, f"api: choices[0].error: {json.dumps(choice['error'])[:300]}"
    finish = choice.get("finish_reason")
    if finish == REFUSAL_FINISH_REASON:
        text_part = envelope["result"][:REFUSAL_CHARS] or f"finish_reason={finish}"
        return envelope, raw, f"refusal: {text_part}"
    if finish == "error":
        return envelope, raw, f"api: finish_reason={finish}"
    if text is None:
        return envelope, raw, "schema: no choices[0].message.content in response"
    if finish == "length":
        return envelope, raw, "api: response truncated (finish_reason=length)"
    return envelope, raw, None
