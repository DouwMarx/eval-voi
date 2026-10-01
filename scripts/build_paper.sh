#!/usr/bin/env bash
# Build a study's CoRL report and check the body page limit.
# Usage: scripts/build_paper.sh <study-dir>   e.g. scripts/build_paper.sh studies/safety-evals
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
study="${1:?usage: build_paper.sh <study-dir>}"
report="$study/report"
[ -f "$report/main.tex" ] || { echo "no main.tex in $report" >&2; exit 1; }
(cd "$report" && latexmk -pdf main.tex)
python3 "$here/check_pages.py" "$report"
