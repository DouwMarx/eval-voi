"""macros.tex: one \\newcommand per number the paper or the extended report
cites, and the number formats the tables share.

Names are \\voi<Tag><Name> with letters only (LaTeX command names): digits
are spelled out (q10 -> Ten, asimov2 -> AsimovTwo) and a scenario's short
name is camel-cased. Formats: probabilities as percent with 2 significant
figures, USD with 2 (3 when the mantissa reaches 100) and a k/M/B/T suffix,
other numbers with 2 significant figures (a power of ten outside
[1e-3, 1e4)).
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

from voi_rank.analysis.summary import CURVE_QS, ERROR_CLASSES, GROUPS, LLM, PHYS, Summary
from voi_rank.fit import PARAM_NAMES

FILE = "macros.tex"
DIGITS = ("Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine")
QWORDS = {5: "Five", 10: "Ten", 25: "TwentyFive", 50: "Fifty", 75: "SeventyFive", 90: "Ninety",
          95: "NinetyFive"}
CURVE_AT = (10, 25, 50, 75, 90)
LATEX_SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                  "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}"}
GROUP_WORD = {PHYS: "Physical", LLM: "LLM"}


# --- formats -----------------------------------------------------------------

def esc(text) -> str:
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in str(text))


def missing(v) -> bool:
    return v is None or (isinstance(v, (float, np.floating)) and not math.isfinite(v))


def sig(v: float, digits: int = 2) -> str:
    """v rounded to `digits` significant figures, printed without exponent
    (integer digits are kept: 123 stays 123)."""
    if v == 0:
        return "0"
    r = float(f"{v:.{digits}g}")
    if abs(r) >= 10 ** digits:
        r = round(v)
    text = np.format_float_positional(r, trim="-")
    return text


def num(v, digits: int = 2) -> str:
    """2 significant figures; +inf (an n* that never pays) prints as infinity."""
    if v is not None and float(v) == math.inf:
        return r"\ensuremath{\infty}"
    if missing(v):
        return "--"
    v = float(v)
    if v != 0 and not (1e-3 <= abs(v) < 1e4):
        k = math.floor(math.log10(abs(v)))
        m = float(f"{v / 10**k:.{digits}g}")
        if abs(m) >= 10:
            m, k = m / 10, k + 1
        return rf"\ensuremath{{{sig(m, digits)}\times10^{{{k}}}}}"
    return sig(v, digits)


def pct(p, digits: int = 2) -> str:
    """Percent with 2 significant figures; a probability strictly inside
    (0, 1) never prints as 0% or 100% (>99.5% / <0.5% instead)."""
    if missing(p):
        return "--"
    p = float(p)
    if 0.995 <= p < 1.0:
        return r"\ensuremath{>}99.5\%"
    if 0.0 < p < 0.005:
        return r"\ensuremath{<}0.5\%"
    return sig(100.0 * p, digits) + r"\%"


def usd(v) -> str:
    if missing(v):
        return "--"
    v = float(v)
    for scale, suffix in ((1.0, ""), (1e3, "k"), (1e6, "M"), (1e9, "B"), (1e12, "T")):
        m = abs(v) / scale
        text = sig(m, 3 if m >= 100 else 2)
        if float(text) < 1000 or suffix == "T":
            return ("-" if v < 0 else "") + r"\$" + text + suffix
    raise AssertionError("unreachable")


def rank(v) -> str:
    return "--" if missing(v) else (f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}")


# --- names -----------------------------------------------------------------------

def camel(text: str) -> str:
    """Letters only: digits spelled out, words capitalised, the rest dropped."""
    text = re.sub(r"\d", lambda m: " " + DIGITS[int(m.group())] + " ", str(text))
    return "".join(w[:1].upper() + w[1:] for w in re.split(r"[^A-Za-z]+", text) if w)


def scenario_keys(s: Summary) -> list[str]:
    """camel(short name) per scenario; S<id in words> where two would collide."""
    keys = ["Sc" + (camel(sc.short) or camel(str(sc.id))) for sc in s.scenarios]
    return [k if keys.count(k) == 1 else "Sc" + camel(str(sc.id)) for k, sc in zip(keys, s.scenarios,
                                                                              strict=True)]


def prefix(tag: str | None) -> str:
    return "voi" + (camel(tag).lower() if tag else "")


def newcommands(values: dict[str, str], tag: str | None = None) -> list[str]:
    p = prefix(tag)
    return [rf"\newcommand{{\{p}{name}}}{{{value}}}" for name, value in values.items()]


# --- the macros ------------------------------------------------------------------

class Unique(dict):
    """A dict that refuses to overwrite: two macros with one name is a bug."""

    def __setitem__(self, key, value):
        if key in self:
            raise RuntimeError(f"macro name {key!r} defined twice (a scenario short name collides)")
        super().__setitem__(key, value)


def collect(s: Summary) -> dict[str, str]:
    o, m = s.out, Unique()
    keys = scenario_keys(s)
    run = s.run
    m["RunId"] = str(run["id"])
    m["Seed"] = str(run["seed"])
    m["Draws"] = f"{run['n_draws']:,}".replace(",", "{,}")
    m["DrawsUsed"] = f"{run['draws_used']:,}".replace(",", "{,}")
    m["NMembers"] = str(run["n_members"])
    m["CodeHash"] = esc((run["code_hash"] or "unknown")[:7])
    m["NScenarios"] = str(o["n_scenarios"])
    for g in GROUPS:
        m[f"N{GROUP_WORD[g]}"] = str(o["n_group"][g])
    for metric, word in (("eta", "Eta"), ("eta_ind", "EtaInd"), ("eta_run", "EtaRun")):
        g = o["groups"][metric]
        m[f"{word}ACentral"] = pct(g["A_central"])
        for q, v in zip(("Lo", "Med", "Hi"), g["A_q"], strict=True):
            m[f"{word}AQ{q}"] = pct(v)
        m[f"{word}MWp"] = num(g["mw_p"])
    if "curve_q" in o:
        for q in CURVE_AT:
            i = int(np.searchsorted(CURVE_QS, q))
            m[f"CurveCentral{QWORDS[q]}"] = pct(o["curve_central"][i])
            for name, v in zip(("Lo", "Med", "Hi"), o["curve_q"][i], strict=True):
                m[f"Curve{name}{QWORDS[q]}"] = pct(v)
        pb = o["p_beats_median"]
        m["NPhysicalBeatMedian"] = str(int((pb > 0.5).sum()))
        m["PhysicalPctCentralMedian"] = sig(float(np.median(o["pct_central"])))
        for k, i in enumerate(s.ids_in(PHYS)):
            key = keys[i]
            m[f"Pct{key}Central"] = sig(float(o["pct_central"][k]))
            m[f"Pct{key}Med"] = sig(float(o["pct_q"][k][1]))
            m[f"PBeatMedian{key}"] = pct(pb[k])
    for g in GROUPS:
        idx = s.ids_in(g)
        w = GROUP_WORD[g]
        m[f"ChangesShare{w}"] = pct(o["changes_share"][g])
        m[f"NChanges{w}"] = str(int((s.central["EVSI"][idx] > 0).sum()))
        ns = s.central["n_star"][idx]
        fin = ns[np.isfinite(ns)]
        m[f"NstarMedian{w}"] = num(float(np.median(fin)) if fin.size else None)
        m[f"NPays{w}"] = str(int((o["p_pays"][idx] > 0.5).sum()))
        m[f"PPaysMedian{w}"] = pct(float(np.median(o["p_pays"][idx])) if len(idx) else None)
        m[f"EtaMedian{w}"] = num(float(np.median(s.central["eta"][idx])) if len(idx) else None)
    rho = o["mean_abs_rho"]
    for name in PARAM_NAMES:
        m[f"Rho{camel(name)}"] = num(rho[name])
        m[f"MemberRho{camel(name)}"] = num(o["member_rho"][name])
    ranked = sorted((v, k) for k, v in rho.items() if v is not None)
    m["RhoTopParam"] = esc(ranked[-1][1]) if ranked else "--"
    m["LevelRhoJ"] = num(o["level_rho_J"])
    m["LevelRhoC"] = num(o["level_rho_C"])
    m["NLevel"] = str(len(o["level_ids"]))
    top = min(range(len(s.scenarios)), key=lambda i: (o["rank_central"][i], s.scenarios[i].id))
    m["TopShort"] = esc(s.scenarios[top].short)
    m["TopEta"] = num(s.central["eta"][top])
    for i, key in enumerate(keys):
        m[f"Eta{key}"] = num(s.central["eta"][i])
        m[f"PChanges{key}"] = pct(o["p_changes"][i])
        m[f"Nstar{key}"] = num(s.central["n_star"][i])
    att = sum(h["attempts"] for h in s.health)
    m["Attempts"] = str(att)
    m["ValidShare"] = pct(sum(h["valid"] for h in s.health) / att if att else None)
    m["USD"] = usd(sum(h["usd"] for h in s.health))
    for c in ERROR_CLASSES:
        m[f"Invalid{camel(c)}"] = str(sum(h[c] for h in s.health))
    return m


def write(s: Summary, out: Path, tag: str | None = None) -> Path:
    values = collect(s)
    path = Path(out) / FILE
    header = (f"% generated by voi_rank.analysis from run {s.run['id']} (protocol {s.run['protocol']}"
              + (f", decision stage from {s.run['decision_from']}" if s.run["decision_from"] else "")
              + "); do not edit")
    path.write_text("\n".join([header, *newcommands(values, tag)]) + "\n")
    return path
