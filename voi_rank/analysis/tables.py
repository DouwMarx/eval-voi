"""LaTeX tabulars (booktabs fragments; the document wraps them in a float):
the scenarios, the per-scenario headline numbers and the elicitation
health per member."""

from __future__ import annotations

from pathlib import Path

from voi_rank.analysis.macros import esc, num, pct, rank, usd
from voi_rank.analysis.summary import ERROR_CLASSES, PHYS, Summary, order

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
    o, c = s.out, s.central
    rows = []
    for i in order(s):
        sc = s.scenarios[i]
        lo, _, hi = o["rank_q"][i]
        rows.append([str(sc.id), esc(sc.short), usd(c["EVSI"][i]), usd(c["C"][i]), num(c["eta"][i]),
                     num(c["eta_ind"][i]), rank(o["rank_central"][i]), f"{rank(lo)}--{rank(hi)}",
                     pct(o["p_changes"][i]), num(c["n_star"][i])])
    header = ["id", "evaluation", "EVSI", "$C$", r"$\eta$", r"$\eta^\circ$", "rank", "rank 90\\%",
              r"$P(\mathrm{EVSI}>0)$", "$n^*$"]
    return tabular("rlrrrrrrrr", header, rows)


def health_table(s: Summary) -> str:
    rows, tot = [], {"attempts": 0, "valid": 0, "usd": 0.0, **{k: 0 for k in ERROR_CLASSES}}
    for h in s.health:
        rows.append([esc(h["member"]), str(h["attempts"]),
                     pct(h["valid"] / h["attempts"] if h["attempts"] else None),
                     *[str(h[k]) for k in ERROR_CLASSES], usd(h["usd"])])
        for k in tot:
            tot[k] += h[k]
    foot = [["all", str(tot["attempts"]), pct(tot["valid"] / tot["attempts"] if tot["attempts"] else None),
             *[str(tot[k]) for k in ERROR_CLASSES], usd(tot["usd"])]]
    header = ["member", "attempts", "valid", *ERROR_CLASSES, "USD"]
    return tabular("l" + "r" * (len(header) - 1), header, rows, foot)


TABLES = {"tab_scenarios.tex": scenarios_table, "tab_headline.tex": headline_table,
          "tab_health.tex": health_table}


def write_all(s: Summary, out: Path) -> list[Path]:
    paths = []
    for name, fn in TABLES.items():
        path = Path(out) / name
        path.write_text(fn(s))
        paths.append(path)
    return paths
