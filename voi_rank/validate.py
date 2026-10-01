"""Validation of elicited payloads (DESIGN section 4) and percentile fitting.

The payload carries exactly the parameters the prompt asked for (`names`:
a stage's subset of PARAM_NAMES; PARAM_NAMES by default): a missing or an
unexpected parameter is a schema error. Per parameter: three numeric
percentiles (plain or scientific notation, as json.loads already reads
them, or a numeric string) with p5 < p50 < p95; probabilities in (0, 1);
USD amounts and n > 0; n >= 1 at p50. Across parameters: median s > 1 -
median t (informativeness; needs both s and t), prior median in [0.001,
0.999] (needs p). There is no unit field: the units are fixed by the
template.
"""

from __future__ import annotations

import math
import re

from voi_rank import fit as fitmod
from voi_rank.fit import PARAM_NAMES

PROB_PARAMS = {"p", "s", "t"}
_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def strip_fences(text: str) -> str:
    text = text.strip()
    m = _FENCE_RE.match(text)
    return m.group(1) if m else text


def _number(value) -> float:
    """A finite float from a JSON number or a numeric string ('1e6',
    '150000'); ValueError otherwise (bool is not a number here)."""
    if isinstance(value, bool) or value is None:
        raise ValueError("not a number")
    x = float(value) if not isinstance(value, str) else float(value.strip().replace(",", ""))
    if not math.isfinite(x):
        raise ValueError("not finite")
    return x


def validate_payload(obj, names: list[str] | None = None) -> tuple[dict | None, str | None]:
    """Schema + constraint checks. Returns (clean_params, None) or (None, error).
    clean_params has exactly the `names` keys (PARAM_NAMES by default, a
    stage's subset of them otherwise), in that order, each {p5, p50, p95,
    reasoning}."""
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
    extra = [k for k in prm if k not in names]
    if extra:
        return None, f"schema: unexpected parameters {extra} (this prompt asks for {names})"
    clean = {}
    for name in names:
        d = prm[name]
        if not isinstance(d, dict):
            return None, f"schema: {name} is not an object"
        try:
            p5, p50, p95 = (_number(d[k]) for k in ("p5", "p50", "p95"))
        except (KeyError, TypeError, ValueError):
            return None, f"schema: {name}: missing or non-numeric percentiles"
        if not (p5 < p50 < p95):
            return None, f"constraint: {name}: percentiles not strictly increasing"
        if name in PROB_PARAMS:
            if not (0.0 < p5 and p95 < 1.0):
                return None, f"constraint: {name}: probabilities must lie in (0,1)"
        elif p5 <= 0.0:
            return None, f"constraint: {name}: must be > 0"
        if name == "n" and p50 < 1.0:
            return None, "constraint: n: the median reuse count must be >= 1"
        clean[name] = {"p5": p5, "p50": p50, "p95": p95, "reasoning": str(d.get("reasoning", ""))}
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
