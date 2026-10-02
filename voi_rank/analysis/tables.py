"""LaTeX tabulars (booktabs fragments; the document wraps them in a float):
the scenarios, the per-scenario headline numbers and the elicitation
health per member."""

from __future__ import annotations

from pathlib import Path

from voi_rank.analysis.macros import esc, num, pct, rank, usd
from voi_rank.analysis.summary import ERROR_CLASSES, PHYS, PRIMARY, TOP_K, Summary, member_display, order

SMALL_OPEN = r"\begingroup\footnotesize\setlength{\tabcolsep}{3pt}"
SMALL_CLOSE = r"\endgroup"


def tabular(colspec: str, header: list[str], rows: list[list[str]], foot: list[list[str]] = ()) -> str:
    lines = [SMALL_OPEN, rf"\begin{{tabular}}{{{colspec}}}", r"\toprule", " & ".join(header) + r" \\",
             r"\midrule"]
    lines += [" & ".join(r) + r" \\" for r in rows]
    if foot:
        lines.append(r"\midrule")
        lines += [" & ".join(r) + r" \\" for r in foot]
    lines += [r"\bottomrule", r"\end{tabular}", SMALL_CLOSE]
    return "\n".join(lines) + "\n"


def scenarios_table(s: Summary) -> str:
    rows = []
    for sc in sorted(s.scenarios, key=lambda x: x.id):
        where = (f"level {sc.level:g}" if sc.group == PHYS and sc.level is not None
                 else esc((sc.domain or "--").replace("_", " ")))
        rows.append([str(sc.id), esc(sc.short), esc(sc.group or "--"), where])
    return tabular("rlll", ["id", "evaluation", "group", "domain or level"], rows)


def headline_table(s: Summary) -> str:
    """Per evaluation at the central estimate, ordered by eta*: EVSI*, EVSI, C,
    eta*, eta, the rank by eta* (central and 90% interval over draws),
    P(rank by eta* <= k), P(EVSI > 0) and the break-even run count n*."""
    o, c = s.out, s.central
    r = o["rank"][PRIMARY]
    rows = []
    for i in order(s):
        sc = s.scenarios[i]
        lo, _, hi = r["q"][i]
        rows.append([str(sc.id), esc(sc.short), usd(c["EVSI_ind"][i]), usd(c["EVSI"][i]), usd(c["C"][i]),
                     num(c["eta_ind"][i]), num(c["eta"][i]), rank(r["central"][i]), f"{rank(lo)}--{rank(hi)}",
                     *[pct(r["p_le"][k][i]) for k in TOP_K], pct(o["p_changes"][i]), num(c["n_star"][i])])
    header = ["id", "evaluation", r"$\EVSI^*$", "EVSI", "$C$", r"$\eta^*$", r"$\eta$", "rank", "rank 90\\%",
              *[rf"$P(\mathrm{{rank}}\le{k})$" for k in TOP_K], r"$P(\mathrm{EVSI}>0)$", "$n^*$"]
    return tabular("rl" + "r" * (len(header) - 2), header, rows)


def domains_table(s: Summary) -> str:
    """Per risk domain (physical AI counted as one), ordered by the median
    central rank under eta*: evaluations, median rank, median eta*, median
    eta, median stakes B+K and the share whose prior is already decisive."""
    rows = []
    for d in s.out["domains"]:
        rows.append([esc(d["label"]), str(d["n"]), rank(d["med_rank_central"]), num(d["med_eta_ind"]),
                     num(d["med_eta"]), usd(d["med_stakes"]), pct(d["zero_share"])])
    header = ["risk domain", "$n$", r"median rank ($\eta^*$)", r"median $\eta^*$", r"median $\eta$",
              "median $B+K$", r"share with $\EVSI=0$"]
    return tabular("lrrrrrr", header, rows)


def provenance_table(s: Summary) -> str:
    """Per evaluation (by id), the title of its primary source (the first
    source that is not a system card) and whether system cards are among its
    sources. Titles are the drafts' own, so no citation key is invented."""
    rows = []
    for sc in sorted(s.scenarios, key=lambda x: x.id):
        srcs = sc.sources or []
        primary = next((x for x in srcs if x.get("kind") != "system_card"), None)
        cards = any(x.get("kind") == "system_card" for x in srcs)
        title = (primary or {}).get("title") or "--"
        rows.append([str(sc.id), esc(sc.short), esc(title) + (" (and system cards)" if cards else "")])
    return tabular(r"rlp{0.62\linewidth}", ["id", "evaluation", "primary source"], rows)


def health_table(s: Summary) -> str:
    rows, tot = [], {"attempts": 0, "valid": 0, "usd": 0.0, **{k: 0 for k in ERROR_CLASSES}}
    for h in s.health:
        rows.append([esc(member_display(h["member"])), str(h["attempts"]),
                     pct(h["valid"] / h["attempts"] if h["attempts"] else None),
                     *[str(h[k]) for k in ERROR_CLASSES], usd(h["usd"])])
        for k in tot:
            tot[k] += h[k]
    foot = [["all", str(tot["attempts"]), pct(tot["valid"] / tot["attempts"] if tot["attempts"] else None),
             *[str(tot[k]) for k in ERROR_CLASSES], usd(tot["usd"])]]
    header = ["member", "attempts", "valid", *ERROR_CLASSES, "USD"]
    return tabular("l" + "r" * (len(header) - 1), header, rows, foot)


TABLES = {"tab_scenarios.tex": scenarios_table, "tab_headline.tex": headline_table,
          "tab_domains.tex": domains_table, "tab_provenance.tex": provenance_table,
          "tab_health.tex": health_table}


def write_all(s: Summary, out: Path) -> list[Path]:
    paths = []
    for name, fn in TABLES.items():
        path = Path(out) / name
        path.write_text(fn(s))
        paths.append(path)
    return paths
