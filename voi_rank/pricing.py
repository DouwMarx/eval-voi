"""Cost estimate of an OpenRouter member without stored attempts (the plan and
the dry run print it; elicit.print_plan).

Prices: the public catalogue GET /api/v1/models (no key), plus GET
/api/v1/models/<id>/endpoints for a member with provider_order (its pinned
endpoint's price, which can differ from the catalogue's top endpoint
several-fold: DeepSeek V4.1 Flash 0.03 vs 0.15 USD per million input tokens
on 2026-10-01). Both are cached in <study>/CACHE_FILE with the fetch time
and reused for CACHE_MAX_AGE_S; offline, the prices recorded in
research/ensemble_members.json (FALLBACK_FILE) are used and the source is
printed.

Tokens per call: input = (system prompt + rendered prompt) characters /
CHARS_PER_TOKEN; output = the member's est_output_tokens, else
DEFAULT_OUTPUT_TOKENS. The default is the mean completion length (answer
plus reasoning) over the 19 answered calls of the 2026-10-01 smoke test
(research/smoke_openrouter.json): 5.9k, median 3.5k, range 1.3k (Claude
Sonnet, no reasoning) to 14.4k (Grok 4.7). Low / central / high scale the
output by OUTPUT_FACTORS (0.5, 1, 2), roughly the spread between members in that
test. Caching is ignored (a k=1 run sends each prompt once per member, so
there is nothing to reuse) and so is the one retry of a failed attempt.
"""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from voi_rank.dotenv import ROOT
from voi_rank.providers import openrouter

MODELS_URL = "https://openrouter.ai/api/v1/models"
ENDPOINTS_URL = "https://openrouter.ai/api/v1/models/{model}/endpoints"
CACHE_FILE = ".openrouter_models.json"
CACHE_MAX_AGE_S = 24 * 3600.0
FETCH_TIMEOUT_S = 30
FALLBACK_FILE = ROOT / "research" / "ensemble_members.json"
DEFAULT_OUTPUT_TOKENS = 6000
CHARS_PER_TOKEN = 4
OUTPUT_FACTORS = (0.5, 1.0, 2.0)   # low, central, high
_NETWORK_ERRORS = (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError)


def fetch_json(url: str, opener=None) -> dict:
    """GET a public OpenRouter JSON document (no key)."""
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with opener(req, timeout=FETCH_TIMEOUT_S, context=openrouter.ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _per_token(pricing) -> dict | None:
    """{prompt, completion} USD per token from an OpenRouter pricing object;
    None when it is missing or malformed (the plan prints 'unknown')."""
    try:
        return {"prompt": float(pricing["prompt"]), "completion": float(pricing["completion"])}
    except (KeyError, TypeError, ValueError):
        return None


def _priced(pricing, source: str) -> tuple[dict, str] | None:
    per_token = _per_token(pricing)
    return None if per_token is None else (per_token, source)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _read_cache(path: Path) -> dict | None:
    try:
        cache = json.loads(path.read_text())
        datetime.fromisoformat(cache["fetched"])
        if isinstance(cache.get("models"), dict) and isinstance(cache.get("endpoints"), dict):
            return cache
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def load_catalogue(study_root: Path | None, pinned: list[str], fetch=None,
                   now=_utc_now) -> dict | None:
    """{'fetched', 'models': {id: pricing}, 'endpoints': {id: [endpoint]}} from
    the cache when it is younger than CACHE_MAX_AGE_S and holds the endpoint
    lists of every model in `pinned`, else fetched (and the cache rewritten;
    a cache that cannot be written is skipped). None when the fetch fails
    (offline)."""
    fetch = fetch or fetch_json
    path = study_root / CACHE_FILE if study_root is not None else None
    cache = _read_cache(path) if path is not None and path.exists() else None
    if cache is not None:
        age = (now() - datetime.fromisoformat(cache["fetched"])).total_seconds()
        if age <= CACHE_MAX_AGE_S and all(m in cache["endpoints"] or m not in cache["models"]
                                          for m in pinned):
            return cache
    try:
        data = fetch(MODELS_URL)["data"]
        models = {m["id"]: m["pricing"] for m in data if isinstance(m, dict) and "pricing" in m}
        endpoints = {}
        for model in pinned:
            if model in models:
                eps = fetch(ENDPOINTS_URL.format(model=model))["data"]["endpoints"]
                endpoints[model] = [{"provider_name": e.get("provider_name"), "tag": e.get("tag"),
                                     "pricing": e.get("pricing")} for e in eps]
    except _NETWORK_ERRORS + (KeyError, TypeError) as ex:
        print(f"  note: OpenRouter catalogue fetch failed ({type(ex).__name__}: {ex});"
              f" using the prices in {FALLBACK_FILE.relative_to(ROOT)}")
        return None
    cache = {"fetched": now().isoformat(timespec="seconds"), "source": MODELS_URL,
             "models": models, "endpoints": endpoints}
    if path is not None:
        try:
            path.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n")
        except OSError:
            pass
    return cache


def match_endpoint(endpoints: list[dict], order: list[str]) -> dict | None:
    """The endpoint provider.order picks first: per entry in order, an exact
    tag match ('z-ai/fp8'), else the provider's base slug or name ('xai',
    'xAI')."""
    for name in order:
        low = name.lower()
        for e in endpoints:
            if (e.get("tag") or "").lower() == low:
                return e
        for e in endpoints:
            tag = (e.get("tag") or "").lower()
            if tag.split("/")[0] == low or (e.get("provider_name") or "").lower() == low:
                return e
    return None


def _fallback_prices() -> dict:
    """{id: (top-level per-token prices, the recorded first-party endpoint
    {tag, provider_name, pricing} | None)}
    from FALLBACK_FILE; {} when absent."""
    try:
        members = json.loads(FALLBACK_FILE.read_text())["members"]
    except (OSError, ValueError, KeyError):
        return {}
    out = {}
    for m in members:
        top = {"prompt": m["prompt_usd_per_m"] / 1e6, "completion": m["completion_usd_per_m"] / 1e6}
        fp = m.get("first_party_endpoint")
        first = ({"tag": fp.get("tag"), "provider_name": fp.get("provider_name"),
                  "pricing": {"prompt": fp["prompt_usd_per_m"] / 1e6,
                              "completion": fp["completion_usd_per_m"] / 1e6}}
                 if isinstance(fp, dict) else None)
        out[m["id"]] = (top, first)
    return out


def member_prices(members: list[dict], study_root: Path | None, fetch=None,
                  now=_utc_now) -> dict[str, tuple[dict, str] | None]:
    """{model id: ({prompt, completion} USD per token, source text) | None} for
    the given openrouter members: the pinned endpoint's price for a member
    with provider_order, else the catalogue's (top endpoint) price."""
    pinned = [m["model"] for m in members if m.get("provider_order")]
    cat = load_catalogue(study_root, pinned, fetch, now)
    fallback = _fallback_prices() if cat is None else {}
    out: dict[str, tuple[dict, str] | None] = {}
    for m in members:
        model, order = m["model"], m.get("provider_order")
        if cat is not None:
            if model not in cat["models"]:
                out[model] = None
                continue
            when = f"catalogue {cat['fetched']}"
            if order:
                e = match_endpoint(cat["endpoints"].get(model, []), order)
                out[model] = (_priced(e.get("pricing"), f"endpoint {e.get('tag')}, {when}")
                              if e is not None else None)
            else:
                out[model] = _priced(cat["models"][model], when)
            continue
        if model not in fallback:
            out[model] = None
            continue
        top, first = fallback[model]
        if order and first is not None and match_endpoint([first], order) is not None:
            out[model] = (first["pricing"], f"first-party endpoint, offline fallback {FALLBACK_FILE.name}")
        elif order:   # pinned elsewhere: only the top endpoint's price is recorded
            out[model] = (top, f"top endpoint (pinned endpoint not recorded), offline fallback"
                               f" {FALLBACK_FILE.name}")
        else:
            out[model] = (top, f"offline fallback {FALLBACK_FILE.name}")
    return out


def input_tokens(prompt: str, system_prompt: str) -> float:
    return (len(system_prompt) + len(prompt)) / CHARS_PER_TOKEN


def output_tokens(member: dict) -> int:
    return int(member.get("est_output_tokens") or DEFAULT_OUTPUT_TOKENS)


def estimate(jobs: list[dict], member: dict, prices: dict, system_prompt: str) -> tuple[float, ...]:
    """(low, central, high) USD of a member's pending jobs at `prices` (USD per
    token): the input tokens of each rendered prompt plus the member's
    output assumption scaled by OUTPUT_FACTORS."""
    n_in = sum(input_tokens(j["prompt"], system_prompt) for j in jobs)
    n_out = output_tokens(member) * len(jobs)
    return tuple(n_in * prices["prompt"] + f * n_out * prices["completion"] for f in OUTPUT_FACTORS)
