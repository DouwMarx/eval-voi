#!/usr/bin/env python3
"""Check that the body of a CoRL workshop paper fits the page limit.

Reads report/main.aux for the page number recorded by \\label{lastbodypage}
(placed immediately before the \\clearpage that precedes the bibliography)
and, when present, \\label{refsstart} (placed right after that \\clearpage): a
float deferred past the last line of text is flushed by the \\clearpage and
pushes refsstart, so the body is max(lastbodypage, refsstart - 1) pages. Fails
if that exceeds the limit. Also prints total pages via pdfinfo.

Usage: check_pages.py <study-dir-or-report-dir> [--limit 4]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


def label_page(text: str, name: str) -> int | None:
    # hyperref form: \newlabel{name}{{}{4}{...}{...}{}}
    # plain form:    \newlabel{name}{{}{4}}
    m = re.search(r"\\newlabel\{" + name + r"\}\{\{[^{}]*\}\{(\d+)\}", text)
    return int(m.group(1)) if m else None


def body_pages(aux: Path) -> int:
    text = aux.read_text(errors="replace")
    last = label_page(text, "lastbodypage")
    if last is None:
        sys.exit(f"check_pages: no \\label{{lastbodypage}} found in {aux}")
    refs = label_page(text, "refsstart")
    return max(last, refs - 1) if refs is not None else last


def total_pages(pdf: Path) -> int | None:
    try:
        out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path", help="study dir (containing report/) or the report dir itself")
    p.add_argument("--limit", type=int, default=4, help="max body pages excluding references")
    a = p.parse_args()
    d = Path(a.path)
    report = d / "report" if (d / "report").is_dir() else d
    aux = report / "main.aux"
    if not aux.exists():
        sys.exit(f"check_pages: {aux} not found; build the paper first")
    body = body_pages(aux)
    total = total_pages(report / "main.pdf")
    print(f"body pages: {body} (limit {a.limit})")
    print(f"total pages: {total if total is not None else 'unknown (pdfinfo failed)'}")
    if body > a.limit:
        print(f"FAIL: body exceeds {a.limit} pages", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
