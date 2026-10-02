#!/usr/bin/env python3
"""Write a review sheet of the scenarios: one entry per evaluation with its
id (as the report's figures label it), title, group, risk domain or fidelity
level, and the three decision fields the decision prompt renders (agent,
decision, theta definition) plus the instrument field of the instrument
prompt. LaTeX source and PDF under <study>/report/scenario_sheet.{tex,pdf}.

Usage: uv run python scripts/scenario_sheet.py [--study studies/safety-evals] [--no-pdf]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # the repo root, for voi_rank

from voi_rank import db  # noqa: E402
from voi_rank.analysis.macros import esc  # noqa: E402
from voi_rank.analysis.summary import DOMAIN_LABEL  # noqa: E402
from voi_rank.study import Study, add_study_arg  # noqa: E402

HEAD = r"""\documentclass[10pt]{article}
\usepackage[a4paper,margin=2cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{enumitem}
\usepackage{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
\begin{document}
"""
TAIL = "\\end{document}\n"


def entry(sid: int | None, sc: dict) -> str:
    a = sc["attributes"]
    where = (f"fidelity level {a['level']}" if sc["group"] == "physical AI" and a.get("level") is not None
             else DOMAIN_LABEL.get(a.get("risk_domain", ""), a.get("risk_domain", "")))
    head = f"{sid}. " if sid is not None else ""
    return "\n".join([
        rf"\subsection*{{{esc(head + sc['title'])}}}",
        rf"\textit{{{esc(sc['group'])}, {esc(where)}; evaluation family: {esc(a.get('eval_family', ''))}}}",
        r"\begin{description}[leftmargin=2.2cm,style=nextline,itemsep=2pt]",
        rf"\item[agent] {esc(sc['agent'])}",
        rf"\item[decision] {esc(sc['decision'])}",
        rf"\item[theta] {esc(sc['theta_definition'])}",
        rf"\item[instrument] {esc(sc['instrument'])}",
        r"\end{description}",
        "",
    ])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_study_arg(ap)
    ap.add_argument("--no-pdf", action="store_true", help="write the .tex only")
    args = ap.parse_args(argv)
    study = Study.resolve(args.study)
    scenarios = json.loads(study.scenarios_json.read_text())
    ids: dict[str, int] = {}
    if study.db.exists():
        con = study.connect_copy()
        ids = {r["title"]: r["id"] for r in con.execute("SELECT id, title FROM scenarios")}
    order = sorted(scenarios, key=lambda sc: (sc["group"] != "LLM", ids.get(sc["title"], 10**6), sc["title"]))
    n_llm = sum(sc["group"] == "LLM" for sc in scenarios)
    intro = "\n".join([
        r"\section*{The evaluations and their release decisions}",
        f"{len(scenarios)} evaluations ({n_llm} LLM, {len(scenarios) - n_llm} physical AI) from "
        rf"\texttt{{{esc(str(study.scenarios_json.relative_to(db.ROOT)))}}}. The id is the one the report's "
        "figures use. The decision prompt renders agent, decision and theta (with the decision facts); the "
        "instrument prompt renders title, agent, decision, theta and instrument (with the instrument facts).",
        "",
    ])
    body = "".join(entry(ids.get(sc["title"]), sc) for sc in order)
    out_dir = study.report_dir
    tex = out_dir / "scenario_sheet.tex"
    tex.write_text(HEAD + intro + body + TAIL)
    print(tex)
    if not args.no_pdf:
        subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-quiet", tex.name], cwd=out_dir,
                       check=True, stdout=subprocess.DEVNULL)
        print(out_dir / "scenario_sheet.pdf")


if __name__ == "__main__":
    main()
