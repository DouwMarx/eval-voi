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

from voi_rank.analysis.summary import (
    BEST_TOP,
    CURVE_QS,
    DOMAIN_LABEL,
    DOMAINS,
    ERROR_CLASSES,
    GROUPS,
    LLM,
    PHYS,
    PRIMARY,
    RANKED,
    Summary,
    member_name,
)
from voi_rank.fit import PARAM_NAMES

FILE = "macros.tex"
DIGITS = ("Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine")
QWORDS = {5: "Five", 10: "Ten", 25: "TwentyFive", 50: "Fifty", 75: "SeventyFive", 90: "Ninety",
          95: "NinetyFive"}
CURVE_AT = (10, 25, 50, 75, 90)
TOPWORDS = {1: "One", 3: "Three", 5: "Five", 10: "Ten"}   # keys: summary.BEST_TOP
LATEX_SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                  "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}"}
GROUP_WORD = {PHYS: "Physical", LLM: "LLM"}
# display aliases: the code and the DB keep eta_ind (EtaInd); the documents say eta* (EtaStar)
ALIASES = (("EtaInd", "EtaStar"),)
METRIC_WORD = {"eta": "Eta", "eta_ind": "EtaInd", "eta_run": "EtaRun"}
# the documents' notation; any other name prints as $<name>$
PARAM_TEX = {"C_build": r"$C_\mathrm{b}$", "C_run": r"$C_\mathrm{r}$"}


def param_tex(name: str) -> str:
    """A parameter name as LaTeX text (math mode): C_build -> C sub build in roman, K -> K."""
    return PARAM_TEX.get(name, f"${name}$")


# --- formats -----------------------------------------------------------------

def esc(text) -> str:
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in str(text))


def missing(v) -> bool:
    return v is None or (isinstance(v, (float, np.floating)) and not math.isfinite(v))


def sig(v: float, digits: int = 2) -> str:
    """v rounded to `digits` significant figures, printed without exponent
    (1026 prints as 1000: the inputs are elicited, so more digits are noise)."""
    if v == 0:
        return "0"
    r = float(f"{v:.{digits}g}")
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


# The bib key of an evaluation's primary source: the first source of its draft that is not a
# system card, except where the draft's first source is a paper about the evaluation rather
# than the evaluation itself (title prefix -> (bib key in report/extra.bib, source title)).
BIBKEY_OVERRIDE = {"ISO 10218": ("iso10218_2025", "ISO 10218-1:2025 Robotics -- Safety requirements -- "
                                                  "Part 1: Industrial robots")}


def primary_source(sc) -> tuple[str, str] | None:
    """(bib key, title) of the evaluation's primary source, None without one."""
    for prefix, (key, title) in BIBKEY_OVERRIDE.items():
        if sc.title.startswith(prefix):
            return key, title
    primary = next((x for x in (sc.sources or []) if x.get("kind") != "system_card"), None)
    return (primary["key"], primary.get("title") or "") if primary else None


def bibkey(sc) -> str | None:
    src = primary_source(sc)
    return src[0] if src else None


def citep(keys) -> str:
    keys = [k for k in keys if k]
    return rf"\citep{{{','.join(keys)}}}" if keys else "--"


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


def _median(v) -> float | None:
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else None


def _ratio(a, b) -> float | None:
    return a / b if a is not None and b not in (None, 0.0) else None


def group_medians(s: Summary, m: dict) -> None:
    """Why the groups differ: per group, the median over evaluations of each
    pooled median (Med<Param><Group>), of the stakes B+K, of the stakes per
    dollar (B+K)/C and of eta*; the LLM-to-physical ratios of the last two
    (StakesPerCostRatio, EtaIndRatio: the factor by which physical-AI stakes
    would have to grow to match, since EVSI and EVSI* scale with B+K at a fixed
    threshold K/(B+K)); and the two regimes in which the central estimate's
    result cannot change the decision (NMitigatesRegardless: pi0 >= pi*,
    NDeploysRegardless: pi1 <= pi*). MemberList: the members' model ids."""
    pl = s.pooled
    stakes = pl["B"] + pl["K"]
    per_cost = stakes / s.central["C"]
    p, sens, spec = pl["p"], pl["s"], pl["t"]
    p1 = p * sens + (1 - p) * (1 - spec)
    pi0 = p * (1 - sens) / (1 - p1)
    pistar = pl["K"] / stakes
    zero = ~(s.central["EVSI"] > 0)
    med: dict[str, dict[str, float | None]] = {}
    for g in GROUPS:
        idx = s.ids_in(g)
        w = GROUP_WORD[g]
        med[g] = {"spc": _median(per_cost[idx]), "ind": _median(s.central["eta_ind"][idx])}
        for name in PARAM_NAMES:
            v = _median(pl[name][idx])
            m[f"Med{camel(name)}{w}"] = usd(v) if name in ("B", "K", "C_build", "C_run") else num(v)
        m[f"MedStakes{w}"] = usd(_median(stakes[idx]))
        m[f"MedC{w}"] = usd(_median(s.central["C"][idx]))
        m[f"MedStakesPerCost{w}"] = num(med[g]["spc"])
        m[f"MedEtaInd{w}"] = num(med[g]["ind"])
        m[f"MedEVSIInd{w}"] = usd(_median(s.central["EVSI_ind"][idx]))
        mitigates = zero[idx] & (pi0[idx] >= pistar[idx])
        m[f"NMitigatesRegardless{w}"] = str(int(mitigates.sum()))
        m[f"NDeploysRegardless{w}"] = str(int((zero[idx] & ~mitigates).sum()))   # the zeros partition
    m["StakesPerCostRatio"] = num(_ratio(med[LLM]["spc"], med[PHYS]["spc"]))
    m["StakesRatio"] = num(_ratio(_median(stakes[s.ids_in(LLM)]), _median(stakes[s.ids_in(PHYS)])))
    m["EtaIndRatio"] = num(_ratio(med[LLM]["ind"], med[PHYS]["ind"]))
    m["MemberList"] = esc(", ".join(member_name(lab) for lab in s.member_labels))


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
    # the probability of superiority P_S per metric: <Word>PS (central), <Word>PSQLo/Med/Hi (over
    # draws), <Word>MWp (exact Mann-Whitney p at the central estimate)
    for metric, word in METRIC_WORD.items():
        g = o["groups"][metric]
        m[f"{word}PS"] = pct(g["A_central"])
        for q, v in zip(("Lo", "Med", "Hi"), g["A_q"], strict=True):
            m[f"{word}PSQ{q}"] = pct(v)
        m[f"{word}MWp"] = num(g["mw_p"])
    ac = o["eta_A_changing"]
    m["EtaPSChanging"] = pct(ac["A"])
    m["EtaPSChangingN"] = str(ac["n_pairs"])
    # rankings: per metric, the median rank interquartile range (all, per group), the best
    # physical-AI evaluation's central rank and P(best physical-AI rank <= N) over draws
    for metric in RANKED:
        r, word = o["rank"][metric], METRIC_WORD[metric]
        m[f"{word}RankIQRMedian"] = num(_median(r["iqr"]))
        for g in GROUPS:
            m[f"{word}RankIQRMedian{GROUP_WORD[g]}"] = num(_median(r["iqr"][s.ids_in(g)]))
        if "best_phys_curve" in r:
            curve = r["best_phys_curve"]
            for n in BEST_TOP:   # P(rank <= N) is 1 once N reaches the number of evaluations
                m[f"{word}PBestPhysicalTop{TOPWORDS[n]}"] = pct(curve[min(n, len(curve)) - 1])
            m[f"{word}PBestPhysicalTopHalf"] = pct(curve[len(curve) // 2 - 1])   # rank <= n/2
            m[f"{word}BestPhysicalRankCentral"] = rank(r["best_phys_central"])
            best = min(s.ids_in(PHYS), key=lambda i: (r["central"][i], s.scenarios[i].id))
            m[f"{word}BestPhysicalShort"] = esc(s.scenarios[best].short)
            m[f"{word}BestPhysicalValue"] = num(s.central[metric][best])
        top = min(range(len(s.scenarios)), key=lambda i: (r["central"][i], s.scenarios[i].id))
        m[f"{word}TopShort"] = esc(s.scenarios[top].short)
        m[f"{word}TopValue"] = num(s.central[metric][top])
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
    # zeros (the prior already decisive at the central estimate) and the break-even run count
    # n* = C_build / (EVSI - C_run): per group, the median over evaluations of the median
    # over finite draws, and the median over evaluations of the share of finite draws
    for g in GROUPS:
        idx = s.ids_in(g)
        w = GROUP_WORD[g]
        m[f"ChangesShare{w}"] = pct(o["changes_share"][g])
        m[f"ZeroShare{w}"] = pct(None if o["changes_share"][g] is None else 1.0 - o["changes_share"][g])
        m[f"NChanges{w}"] = str(int((s.central["EVSI"][idx] > 0).sum()))
        m[f"NZero{w}"] = str(len(o["zero_ids"][g]))
        m[f"ZeroIds{w}"] = ", ".join(str(i) for i in o["zero_ids"][g]) or "none"
        ns = s.central["n_star"][idx]
        fin = ns[np.isfinite(ns)]
        m[f"NstarMedian{w}"] = num(float(np.median(fin)) if fin.size else None)
        m[f"NNstarFinite{w}"] = str(int(fin.size))
        meds = [q[1] for q in o["nstar_q"][idx] if q[1] is not None]
        m[f"NstarDrawMedian{w}"] = num(float(np.median(meds)) if meds else None)
        m[f"PNstarFiniteMedian{w}"] = pct(float(np.median(o["p_nstar_finite"][idx])) if len(idx) else None)
        m[f"EtaMedian{w}"] = num(float(np.median(s.central["eta"][idx])) if len(idx) else None)
        # the value of one run in USD, every parameter at its median: over all evaluations of
        # the group and over those whose result can change the decision
        evsi = s.central["EVSI"][idx]
        m[f"MedEVSI{w}"] = usd(_median(evsi))
        m[f"MedEVSIChanging{w}"] = usd(_median(evsi[evsi > 0]) if (evsi > 0).any() else None)
        m[f"MedCbuild{w}"] = usd(_median(s.pooled["C_build"][idx]))
    group_medians(s, m)
    # the evaluations' primary sources: NociteEvaluations is one \nocite per evaluation in id
    # order (with an unsorted bibliography style the reference number then equals the id);
    # CiteAll, CiteLLM, CitePhysical and Cite<Domain> are \citep lists in id order
    order = sorted(range(len(s.scenarios)), key=lambda i: s.scenarios[i].id)
    m["NociteEvaluations"] = "".join(rf"\nocite{{{bibkey(s.scenarios[i])}}}" for i in order
                                     if bibkey(s.scenarios[i]))
    m["CiteAll"] = citep(bibkey(s.scenarios[i]) for i in order)
    for g in GROUPS:
        m[f"Cite{GROUP_WORD[g]}"] = citep(bibkey(s.scenarios[i]) for i in order if s.scenarios[i].group == g)
    for d in DOMAINS:
        in_domain = [i for i in order if s.scenarios[i].domain == d and s.scenarios[i].group != PHYS]
        m[f"Cite{camel(DOMAIN_LABEL[d])}"] = citep(bibkey(s.scenarios[i]) for i in in_domain)
    # risk domains, ordered by the median central rank under eta*: Dom<Camel>N, MedRank, MedEtaInd,
    # MedEta, MedStakes, ZeroShare, plus DomainOrder (the labels in that order)
    for d in o["domains"]:
        key = camel(d["label"])
        m[f"Dom{key}N"] = str(d["n"])
        m[f"Dom{key}MedRank"] = rank(d["med_rank_central"])
        m[f"Dom{key}MeanRankMed"] = rank(d["mean_rank_q"][1])
        m[f"Dom{key}MedEtaInd"] = num(d["med_eta_ind"])
        m[f"Dom{key}MedEta"] = num(d["med_eta"])
        m[f"Dom{key}MedStakes"] = usd(d["med_stakes"])
        m[f"Dom{key}ZeroShare"] = pct(d["zero_share"])
    # ties on the median rank are joined with "and" and marked "(tied)"
    groups: list[list[str]] = []
    for d in o["domains"]:
        previous = o["domains"][sum(len(g) for g in groups) - 1] if groups else None
        if previous is not None and previous["med_rank_central"] == d["med_rank_central"]:
            groups[-1].append(d["label"])
        else:
            groups.append([d["label"]])
    m["DomainOrder"] = esc(", ".join(g[0] if len(g) == 1 else " and ".join(g) + " (tied)" for g in groups))
    m["NDomains"] = str(len(o["domains"]))
    rho, rho_ind = o["mean_abs_rho"], o["mean_abs_rho_ind"]
    for name in PARAM_NAMES:
        m[f"Rho{camel(name)}"] = num(rho[name])
        m[f"RhoInd{camel(name)}"] = num(rho_ind[name])
        m[f"MemberRho{camel(name)}"] = num(o["member_rho"][name])
    for word, r in (("", rho), ("Ind", rho_ind)):
        ranked = sorted((v, k) for k, v in r.items() if v is not None)
        for place, i in (("Top", -1), ("Second", -2), ("Low", 0)):
            ok = len(ranked) > abs(i) - (1 if i < 0 else 0)
            m[f"Rho{word}{place}Param"] = param_tex(ranked[i][1]) if ok else "--"
            m[f"Rho{word}{place}Value"] = num(ranked[i][0]) if ok else "--"
    m["LevelRhoEta"] = num(o["level_rho_eta"])
    m["LevelRhoEtap"] = num(o["level_p_eta"])
    m["LevelRhoEtaInd"] = num(o["level_rho_eta_ind"])   # alias LevelRhoEtaStar
    m["LevelRhoEtaIndp"] = num(o["level_p_eta_ind"])
    m["LevelRhoJ"] = num(o["level_rho_J"])
    m["LevelRhoC"] = num(o["level_rho_C"])
    m["LevelRhoJp"] = num(o["level_p_J"])
    m["LevelRhoCp"] = num(o["level_p_C"])
    m["NLevel"] = str(len(o["level_ids"]))
    lev = o["level_ids"]
    if len(lev):
        levels = sorted({s.scenarios[i].level for i in lev})
        m["LevelMin"] = f"{levels[0]:g}"
        m["LevelMax"] = f"{levels[-1]:g}"
    for i, key in enumerate(keys):
        m[f"Eta{key}"] = num(s.central["eta"][i])
        m[f"EtaInd{key}"] = num(s.central["eta_ind"][i])
        m[f"Rank{key}"] = rank(o["rank"][PRIMARY]["central"][i])
        m[f"PChanges{key}"] = pct(o["p_changes"][i])
        m[f"Nstar{key}"] = num(s.central["n_star"][i])
    att = sum(h["attempts"] for h in s.health)
    m["Attempts"] = str(att)
    m["Valid"] = str(sum(h["valid"] for h in s.health))
    m["ValidShare"] = pct(sum(h["valid"] for h in s.health) / att if att else None)
    m["USD"] = usd(sum(h["usd"] for h in s.health))
    for c in ERROR_CLASSES:
        m[f"Invalid{camel(c)}"] = str(sum(h[c] for h in s.health))
    for old, new in ALIASES:
        for k in [k for k in m if old in k]:
            m[k.replace(old, new)] = m[k]
    return m


def write(s: Summary, out: Path, tag: str | None = None) -> Path:
    values = collect(s)
    path = Path(out) / FILE
    header = (f"% generated by voi_rank.analysis from run {s.run['id']} (protocol {s.run['protocol']}"
              + (f", decision stage from {s.run['decision_from']}" if s.run["decision_from"] else "")
              + "); do not edit")
    path.write_text("\n".join([header, *newcommands(values, tag)]) + "\n")
    return path
