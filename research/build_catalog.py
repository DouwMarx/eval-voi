"""Merge the literature sweep JSON files into research/catalog.json, catalog.md and refs.bib.

Usage: python3 research/build_catalog.py

Dedup rule: entries are the same paper if they share an arXiv id, a normalised URL,
a DOI, or a bibtex key. The richest record (most text) is kept, notes are unioned,
cost/validity evidence take the most informative variant, speaker links are unioned.

Sim-to-real ladder (integer levels used everywhere):
 0 text-only QA of an LLM planner (no perception)
 1 static image / scene QA with a VLM
 2 video / temporal QA
 3 generated or synthetic adversarial scenes (diffusion / LLM generated), scored open-loop
 4 closed-loop physics simulation (MuJoCo, Isaac, LIBERO-style)
 5 photoreal / digital-twin simulation or real-data replay
 6 hardware-in-the-loop (real compute, controller or sensors; simulated world)
 7 real robot, controlled lab, no humans at risk
 8 real robot, field or track test with humans or human surrogates
 9 deployment monitoring / operational data

The speaker sweeps (Pavone, Sindhwani, Bajcsy, Fel) used their own scales, so their
levels are re-assigned here from the modality descriptions (LEVEL_OVERRIDES). Where
topic sweeps disagree on a duplicate, the override map decides.
"""
import collections
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.join(HERE, "literature")

LADDER = {
    0: "text-only QA of an LLM planner (no perception)",
    1: "static image / scene QA with a VLM",
    2: "video / temporal QA",
    3: "generated or synthetic adversarial scenes, scored open-loop",
    4: "closed-loop physics simulation",
    5: "photoreal / digital-twin simulation or real-data replay",
    6: "hardware-in-the-loop",
    7: "real robot, controlled lab, no humans at risk",
    8: "real robot, field or track test with humans or human surrogates",
    9: "deployment monitoring / operational data",
}

# canonical key -> (level, reason). Applied after merging. None = not on the ladder.
LEVEL_OVERRIDES = {
    # Bajcsy sweep (own scale)
    "seo2026stressdream": (3, "steered world-model imaginations scored open-loop; no real-robot closed loop"),
    "nakamura2024regret": (7, "96 sim scenarios plus LoCoBot hardware re-deployment"),
    "kim2025multisafe": (7, "Franka Research 3 hardware trials (20 per condition)"),
    "tian2026badbehavior": (2, "reward models judge real-robot rollout videos offline (RoboArena)"),
    "wu2025dowhatyousay": (4, "LIBERO simulation"),
    "jeong2026languagepolicy": (7, "LIBERO-OOD plus Franka hardware, 30 rollouts per condition"),
    "seo2025unisafe": (7, "IsaacLab plus Franka Research 3 Jenga hardware"),
    "jeong2025salt": (4, "simulation only (Robosuite, navigation grid) plus user study"),
    "tian2022confidence": (5, "simulated interactions plus replay of real INTERACTION-dataset human pairs"),
    "bajcsy2021analyzing": (None, "analytical reachability tool, no system evaluated"),
    "pandya2025reguard": (4, "simulated planar driving and WebArena closed loop"),
    "lekeufack2024conformal": (5, "replay of Stanford Drone Dataset pedestrians"),
    "bansal2020hjhuman": (7, "simulation plus quadrotor hardware"),
    "nakamura2025latentsafety": (7, "Franka Research 3 hardware"),
    # Fel sweep
    "andeol2023confident": (1, "object detector scored on static real railway frames"),
    "bergen2026monitoring": (0, "text-only LLM coding evals"),
    # Pavone sweep (own scale)
    "dauner2024navsim": (5, "real-log replay with non-reactive BEV unrolling"),
    "cao2025pseudosim": (5, "real logs plus 3DGS synthetic views, open-loop scoring"),
    "luo2025sim2val": (7, "quadruped hardware plus real AV test-fleet logs paired with sim"),
    "luo2026x4val": (7, "100 real Franka rollouts plus real driving logs"),
    "parashar2026coverage": (7, "real Unitree Go2 target evaluations"),
    "dilillo2024adas": (8, "Euro NCAP-accredited proving ground, 13 vehicles"),
    "dyro2024extreme": (3, "generated adversarial counterfactual collisions on real scenes"),
    "ding2025surprise": (5, "nuScenes log scoring and curated-bucket planner evaluation"),
    "chen2026crashtwin": (3, "generated world-model collision videos scored open-loop (evaluates the simulator)"),
    "gu2025accidentbench": (2, "accident-video QA"),
    "ma2025safevl": (5, "Nexar dashcam video plus NeuroNCAP photoreal closed loop"),
    "foutter2026faithfulness": (1, "reasoning traces on driving scenes rated by humans/judge"),
    "han2024euvs": (5, "neural-rendering digital-twin fidelity benchmark (evaluates the simulator)"),
    "fan2024crashevent": (0, "text crash reports"),
    "patrikar2025negative": (0, "text crash narratives with log retrieval"),
    "antonante2023taskaware": (5, "nuPlan replay"),
    "chakraborty2024sparq": (5, "nuPlan-Vegas replay"),
    "chakraborty2025frs": (3, "nuScenes plus synthetic unsafe scenes, open-loop"),
    "farid2022taskrelevant": (5, "real trajectory logs replayed through planner cost"),
    "topan2022perceptionzones": (5, "nuScenes detector outputs classified offline"),
    "topan2023maneuverzones": (None, "numerical reachability experiments, no system evaluated"),
    "ivanovic2021rethinking": (None, "position"),
    "ivanovic2021planningaware": (5, "illustrative simulation plus real AV data"),
    "leung2022safetyconcepts": (5, "real highway driving logs"),
    "leung2021synthesis": (None, "position"),
    "luo2021conformal": (4, "simulated driver-warning and grasping"),
    "luo2022recency": (7, "hardware visual servoing"),
    "hindy2024martingales": (7, "X-Plane plus free-flyer hardware"),
    "elhafsi2023semantic": (1, "scene converted to text, LLM asked about the static scene"),
    "sinha2024aesop": (7, "quadrotor and AV hardware"),
    "ronecker2025vfm": (3, "CARLA-generated anomaly images scored open-loop"),
    "ganai2025fortress": (7, "quadrotor hardware plus ANYmal logs"),
    "agia2024sentinel": (7, "real mobile manipulator"),
    "sinha2022oodview": (None, "position"),
    "deglurkar2024uq": (5, "nuScenes stack replay"),
    "cao2022advdo": (3, "optimisation-generated adversarial histories, downstream AV simulated"),
    "cao2022robust": (3, "adversarial trajectory attacks with simulated planner"),
    "marchiori2025jdapt": (0, "jailbreak-prompt classification"),
    "christensen2025maritime": (1, "40 harbor scenes scored as VLM QA; single on-water demo unscored"),
    "banerjee2022lifecycle": (3, "synthetic satellite-pose conditions scored open-loop"),
    "zhong2022ctg": (3, "diffusion-generated traffic scored on rule satisfaction/realism"),
    "zhong2023ctgpp": (3, "language-guided scene diffusion, open-loop realism scoring"),
    "tan2023lctgen": (3, "language-conditioned traffic generation, open-loop"),
    "tan2024prosim": (4, "closed-loop traffic simulation (abstract BEV)"),
    "ding2023realgen": (3, "retrieval-augmented scenario generation, open-loop"),
    "xu2022bits": (4, "closed-loop learned traffic simulation"),
    "ivanovic2023trajdata": (None, "dataset tooling"),
    "gao2025survey": (None, "survey"),
    "han2026wildcity": (5, "city-scale reconstruction converted to closed-loop simulator"),
    # Sindhwani sweep (own scale)
    "sermanet2025asimov": (3, "generated images plus text QA, scored against human votes"),
    "jindal2025danger": (3, "generated videos and text QA"),
    "sermanet2025scifi": (0, "text only"),
    "majumdar2025predictive": (3, "Imagen-edited observations scored open-loop; validated against 500+ hardware trials"),
    "geminirobotics2025veo": (5, "Veo world-model rollouts; validated against 1600+ real ALOHA 2 episodes"),
    "geminirobotics2026agentic": (2, "offline dataset incl. 5 s stereo video windows of real human approach; humanoid lab stop test reported separately"),
    "geminirobotics2025report": (3, "ASIMOV-Multimodal generated-image QA"),
    "geminirobotics2025report15": (3, "attacker/target/autorater protocol on prompts and edited scenes; numbers withheld"),
    "sindhwani2020anomaly": (9, "5,000 real delivery-drone missions"),
    "varley2024twoarms": (8, "bimanual system operating with humans in proximity"),
    "caluwaerts2023barkour": (7, "physical obstacle course, no humans at risk"),
    # topic-sweep disagreements on duplicates
    "huang2026coordination": (4, "level 4 assumed from 'embodied multi-robot tasks'; simulator not named"),
    "lu2025isbench": (4, "OmniGibson physics simulation"),
    "wang2024exploring": (7, "LIBERO plus 100 real UR10e rollouts"),
    "wang2026openloop": (4, "cross-level validity study; closed-loop Bench2Drive is the ground truth"),
    "obi2026safegate": (7, "text-level scoring plus AI2-THOR and real-robot experiments; highest rung evaluated"),
    "bajrami2026robotignores": (0, "text-level scoring; physical G1 validation ongoing"),
    "chen2026robodojo": (7, "18 real tasks, 180 real trials per policy"),
    "li2024simpler": (5, "digital-twin simulation validated against real"),
    "wang2026simrealrecipe": (5, "sim-real correlation recipe validated against real rollouts"),
}

NONE_RE = re.compile(
    r"^\s*(none|n/?a|not stated|no validity|no cost|claims only|lists validation practices but no numbers|"
    r"team-hours not stated|not quantified|none beyond deployment exposure)", re.I)
COST_QUANT_RE = re.compile(
    r"(\$|usd|eur|dollar|\d+\s*(k|m)?\s*(gpu|cpu|a100|h100|t4)|\bhours?\b|\bh\b|\bmin(ute)?s?\b|\bdays?\b|\bmonths?\b|"
    r"\bweeks?\b|person|annotator|participant|rater|labell?er|trials?|rollouts?|episodes?|miles|runs\b|samples|"
    r"\bsec(ond)?s?\b|\bs\b/|per (task|scenario|rollout|episode|model|run|cell|attack|mesh|query))", re.I)
VALID_QUANT_RE = re.compile(
    r"(\br\s*=|rho|spearman|pearson|correlat|agreement|auc|tpr|fpr|fnr|tnr|precision|recall|f1\b|\d+(\.\d+)?\s*%|"
    r"kappa|mmrv|srcc|rank|ground.truth|human.label|human.vote|crash|incident|claims|field|real-world|hardware|"
    r"paired|validated|calibrat)", re.I)


def norm_url(u):
    if not u:
        return None
    u = u.lower().strip().rstrip("/")
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = re.sub(r"arxiv\.org/(abs|pdf)/", "arxiv:", u)
    u = re.sub(r"v\d+$", "", u)
    u = re.sub(r"\.pdf$", "", u)
    return u


def norm_arxiv(a):
    if not a:
        return None
    a = str(a).lower().replace("arxiv:", "").strip()
    a = re.sub(r"v\d+$", "", a)
    return a or None


def doi_of(u):
    m = re.search(r"10\.\d{4,}/[^\s\"'<>]+", u or "")
    return m.group(0).lower().rstrip(".") if m else None


def has_evidence(s):
    s = (s or "").strip()
    return bool(s) and not NONE_RE.match(s)


def richness(e):
    return sum(len(str(e.get(k) or "")) for k in
               ("modality", "what_it_measures", "size", "reported_metrics", "cost_evidence",
                "validity_evidence", "notes", "bibtex", "org"))


def bib_key(b):
    m = re.search(r"@\w+\s*\{\s*([^,\s]+)\s*,", b or "")
    return m.group(1) if m else None


def set_bib_key(b, key):
    return re.sub(r"(@\w+\s*\{\s*)[^,\s]+(\s*,)", r"\g<1>" + key + r"\g<2>", b, count=1)


def load():
    ents = []
    for f in sorted(glob.glob(os.path.join(LIT, "*.json"))):
        src = os.path.basename(f)[:-5]
        for e in json.load(open(f)):
            e = dict(e)
            e["_src"] = src
            ents.append(e)
    return ents


def group(ents):
    par = list(range(len(ents)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    idx = collections.defaultdict(list)
    for i, e in enumerate(ents):
        for k in (("a", norm_arxiv(e["arxiv"])), ("u", norm_url(e["url"])),
                  ("d", doi_of(e["url"])), ("k", e["key"].lower())):
            if k[1]:
                idx[k].append(i)
    for v in idx.values():
        for i in v[1:]:
            par[find(v[0])] = find(i)
    groups = collections.defaultdict(list)
    for i in range(len(ents)):
        groups[find(i)].append(i)
    return list(groups.values())


def merge(members):
    members = sorted(members, key=richness, reverse=True)
    base = dict(members[0])
    keys = collections.Counter(m["key"] for m in members)
    # canonical key: most frequent across sweeps, tie -> richest record's key
    canon = max(keys, key=lambda k: (keys[k], k == base["key"]))
    out = {k: v for k, v in base.items() if not k.startswith("_")}
    out["key"] = canon
    for m in members[1:]:
        for fld in ("arxiv", "url"):
            if not out.get(fld) and m.get(fld):
                out[fld] = m[fld]
        for fld in ("cost_evidence", "validity_evidence"):
            if has_evidence(m.get(fld)) and (not has_evidence(out.get(fld)) or len(m[fld]) > len(out[fld]) * 1.5):
                out[fld] = m[fld]
        if m.get("verified_url"):
            out["verified_url"] = True
    links = sorted({m["speaker_link"] for m in members if m["speaker_link"] and m["speaker_link"] != "none"})
    out["speaker_link"] = "; ".join(links) if links else "none"
    conf_rank = {"high": 3, "medium": 2, "low": 1}
    out["confidence"] = max((m["confidence"] for m in members), key=lambda c: conf_rank.get(c, 0))
    # union notes
    notes = []
    for m in members:
        n = (m.get("notes") or "").strip()
        if n and n not in notes:
            notes.append(n)
    aliases = sorted(k for k in keys if k != canon)
    if aliases:
        notes.append("Aliases in sweeps: " + ", ".join(aliases) + ".")
    sf = {m["safety_focus"] for m in members}
    if len(sf) > 1:
        notes.append("Sweeps disagreed on safety_focus; kept %s from the richest record." % base["safety_focus"])
    levels = {m["_src"]: m["sim2real_level"] for m in members}
    out["_levels_seen"] = levels
    out["_all_keys"] = sorted(keys)
    out["notes"] = " ".join(notes)
    out["sources"] = sorted({m["_src"] for m in members})
    out["bibtex"] = set_bib_key(base["bibtex"], canon)
    return out


def assign_level(e):
    seen = e.pop("_levels_seen")
    all_keys = e.pop("_all_keys")
    hit = [k for k in all_keys if k in LEVEL_OVERRIDES]
    if hit:
        lvl, why = LEVEL_OVERRIDES[hit[0]]
        old = sorted({str(v) for v in seen.values()})
        if old != [str(lvl)]:
            e["notes"] = (e["notes"] + " Level set to %s on the 0-9 ladder (%s; sweeps had %s)." %
                          (lvl, why, "/".join(old))).strip()
        e["sim2real_level"] = lvl
        return
    topic = {s: l for s, l in seen.items() if s.startswith("topic")}
    vals = set(topic.values()) if topic else set(seen.values())
    if len(vals) > 1:
        raise SystemExit("unresolved level disagreement for %s: %s" % (e["key"], seen))
    e["sim2real_level"] = vals.pop()


def domain_of(e):
    if e["key"] in ("bergen2026monitoring",):
        return "ai"
    if e["sources"] == ["topic-ai-safety-eval-costs"]:
        return "ai"
    if e["sources"] == ["speaker-fel"] and e["sim2real_level"] is None:
        return "other"
    return "robotics"


def one_line(e):
    s = (e.get("what_it_measures") or e.get("name") or "").strip()
    s = re.split(r"(?<=\.)\s", s)[0].rstrip(";: ")
    return (s[:160] + "...") if len(s) > 160 else s


def main():
    ents = load()
    groups = group(ents)
    merged = [merge([ents[i] for i in g]) for g in groups]
    for e in merged:
        assign_level(e)
    merged.sort(key=lambda e: (e["sim2real_level"] if e["sim2real_level"] is not None else 99, e["key"]))
    keys = [e["key"] for e in merged]
    assert len(keys) == len(set(keys)), "duplicate canonical keys"

    json.dump(merged, open(os.path.join(HERE, "catalog.json"), "w"), indent=1, ensure_ascii=False)

    # refs.bib
    with open(os.path.join(HERE, "refs.bib"), "w") as fh:
        fh.write("% Generated by research/build_catalog.py from research/catalog.json. Do not edit by hand.\n\n")
        for e in sorted(merged, key=lambda e: e["key"]):
            b = e["bibtex"].strip()
            fh.write(b + "\n\n")

    # catalog.md
    per_level = collections.Counter(e["sim2real_level"] for e in merged)
    L = []
    L.append("# Literature catalogue: robot and frontier-AI safety evaluations\n")
    L.append("Generated from %d sweep records in `research/literature/*.json`, merged to %d unique papers "
             "(`research/catalog.json`, `research/refs.bib`). Built by `research/build_catalog.py`.\n" % (len(ents), len(merged)))
    L.append("Sim-to-real ladder: " + "; ".join("%d %s" % (k, v) for k, v in LADDER.items()) + ". "
             "Speaker sweeps used their own scales and were re-levelled from the modality text (see notes in catalog.json).\n")
    L.append("Each line: `key` | name | year | one line (what it measures). Markers: [C] quantified cost evidence, [V] quantified validity evidence, [S] safety_focus.\n")

    def fmt(e):
        m = []
        if has_evidence(e["cost_evidence"]) and COST_QUANT_RE.search(e["cost_evidence"]):
            m.append("C")
        if has_evidence(e["validity_evidence"]) and VALID_QUANT_RE.search(e["validity_evidence"]):
            m.append("V")
        if e["safety_focus"]:
            m.append("S")
        tag = (" [" + "".join(m) + "]") if m else ""
        return "- `%s` | %s | %s |%s %s" % (e["key"], e["name"], e["year"], tag, one_line(e))

    L.append("\n## (a) By sim-to-real level\n")
    L.append("| level | rung | count |\n|---|---|---|")
    for k in list(LADDER) + [None]:
        L.append("| %s | %s | %d |" % ("n/a" if k is None else k,
                                        LADDER.get(k, "not on the ladder (position, survey, standard text, tooling)"),
                                        per_level.get(k, 0)))
    for k in list(LADDER) + [None]:
        sub = [e for e in merged if e["sim2real_level"] == k]
        L.append("\n### Level %s: %s (%d)\n" % ("n/a" if k is None else k,
                                                LADDER.get(k, "not on the ladder"), len(sub)))
        L.extend(fmt(e) for e in sub)

    def view(title, pred, sortkey=lambda e: (e["sim2real_level"] if e["sim2real_level"] is not None else 99, e["key"])):
        sub = sorted([e for e in merged if pred(e)], key=sortkey)
        L.append("\n## %s (%d)\n" % (title, len(sub)))
        L.extend(fmt(e) for e in sub)
        return sub

    for e in merged:
        e["_domain"] = domain_of(e)
    view("(b) Safety-focused robotics evaluations",
         lambda e: e["_domain"] == "robotics" and e["safety_focus"] and e["kind"] != "position")
    view("(c) Frontier AI safety evaluations",
         lambda e: e["_domain"] == "ai" and e["kind"] != "position")
    view("(d) Entries with cost evidence",
         lambda e: has_evidence(e["cost_evidence"]))
    view("(e) Entries with validity evidence",
         lambda e: has_evidence(e["validity_evidence"]))
    view("(f) Speaker-linked entries",
         lambda e: e["speaker_link"] != "none",
         sortkey=lambda e: (e["speaker_link"], e["sim2real_level"] if e["sim2real_level"] is not None else 99, e["key"]))
    for e in merged:
        e.pop("_domain")
    open(os.path.join(HERE, "catalog.md"), "w").write("\n".join(L) + "\n")

    summary = {
        "n_before": len(ents),
        "n_after": len(merged),
        "per_level_counts": {("null" if k is None else str(k)): per_level[k] for k in list(LADDER) + [None]},
        "n_cost_evidence": sum(has_evidence(e["cost_evidence"]) for e in merged),
        "n_cost_quantified": sum(bool(has_evidence(e["cost_evidence"]) and COST_QUANT_RE.search(e["cost_evidence"])) for e in merged),
        "n_validity_evidence": sum(has_evidence(e["validity_evidence"]) for e in merged),
        "n_validity_quantified": sum(bool(has_evidence(e["validity_evidence"]) and VALID_QUANT_RE.search(e["validity_evidence"])) for e in merged),
    }
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
