"""Elicitation providers. Each exposes call(prompt, model, system_prompt) ->
(envelope | None, raw, error | None), where envelope['result'] is the model's
text answer and envelope['total_cost_usd'] its cost when known, and raw is the
verbatim response body stored in the DB."""

from __future__ import annotations

from collections.abc import Callable

from voi_rank.providers.claude_cli import call_claude
from voi_rank.providers.openrouter import call_openrouter

Provider = Callable[[str, str, str], tuple[dict | None, str, str | None]]

PROVIDERS: dict[str, Provider] = {
    "claude_cli": call_claude,
    "openrouter": call_openrouter,
}


def get_provider(name: str) -> Provider:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValueError(f"unknown provider {name!r}; known: {sorted(PROVIDERS)}") from None
