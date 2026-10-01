"""Validation of elicited payloads and percentile fitting.

The payload must carry the parameters (PARAM_NAMES), or the subset a stage
of a staged protocol asks for (`names`); any other key inside "parameters"
is ignored. The informativeness check needs both s and t, the prior check
p: each applies only when its parameters are asked for.
"""

from __future__ import annotations

import re

from voi_rank import fit as fitmod
from voi_rank.fit import PARAM_NAMES

PROB_PARAMS = {"p", "s", "t"}
_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def strip_fences(text: str) -> str:
    text = text.strip()
    m = _FENCE_RE.match(text)
    return m.group(1) if m else text


def validate_payload(obj, names: list[str] | None = None) -> tuple[dict | None, str | None]:
    """Schema + constraint checks. Returns (clean_params, None) or (None, error).
    clean_params has exactly the `names` keys (PARAM_NAMES by default, a
    stage's subset of them otherwise), in that order."""
    names = list(PARAM_NAMES if names is None else names)
    unknown = [n for n in names if n not in PARAM_NAMES]
    if unknown:
        raise ValueError(f"unknown parameter names {unknown}; known: {PARAM_NAMES}")
    if not isinstance(obj, dict) or not isinstance(obj.get("parameters"), dict):
        return None, "schema: missing 'parameters' object"
    prm = obj["parameters"]
    missing = [n for n in names if n not in prm]
    if missing:
        return None, f"schema: missing parameters {missing}"
    clean = {}
    for name in names:
        d = prm[name]
        if not isinstance(d, dict):
            return None, f"schema: {name} is not an object"
        try:
            p5, p50, p95 = float(d["p5"]), float(d["p50"]), float(d["p95"])
        except (KeyError, TypeError, ValueError):
            return None, f"schema: {name}: missing or non-numeric percentiles"
        if not (p5 < p50 < p95):
            return None, f"constraint: {name}: percentiles not strictly increasing"
        if name in PROB_PARAMS:
            if not (0.0 < p5 and p95 < 1.0):
                return None, f"constraint: {name}: probabilities must lie in (0,1)"
        elif p5 <= 0.0:
            return None, f"constraint: {name}: must be > 0"
        clean[name] = {"p5": p5, "p50": p50, "p95": p95,
                       "unit": str(d.get("unit", "")),
                       "reasoning": str(d.get("reasoning", ""))}
    if "s" in clean and "t" in clean and clean["s"]["p50"] <= 1.0 - clean["t"]["p50"]:
        return None, "constraint: informativeness: median s <= 1 - median t"
    if "p" in clean and not (0.001 <= clean["p"]["p50"] <= 0.999):
        return None, "constraint: degenerate prior: p50 of p outside [0.001, 0.999]"
    return clean, None


def fit_all(clean: dict) -> tuple[dict | None, str | None]:
    try:
        return {name: fitmod.fit_param(name, d["p5"], d["p50"], d["p95"])
                for name, d in clean.items()}, None
    except Exception as ex:
        return None, f"fit: {ex}"
