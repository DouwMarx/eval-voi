#!/usr/bin/env bash
# Build a CoRL report and, for the paper, check the body page limit.
# Usage: scripts/build_paper.sh <dir>
#   <dir> = a study (builds <study>/report/main.tex, the paper: body limit 4 pages), or
#           any directory holding a main.tex (e.g. studies/safety-evals/report/extended,
#           the extended report: no page limit).
# Before LaTeX runs, the report's build_refs.py (if any, in the report dir or its parent)
# rewrites refs.bib from the cited keys and fails on a key without a DOI, arXiv id or URL.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="${1:?usage: build_paper.sh <study-dir | dir with main.tex>}"
if [ -f "$target/report/main.tex" ]; then
    dir="$target/report"; limit=1
elif [ -f "$target/main.tex" ]; then
    dir="$target"; limit=0
else
    echo "no main.tex in $target/report or $target" >&2; exit 1
fi
for refs in "$dir/build_refs.py" "$dir/../build_refs.py"; do
    if [ -f "$refs" ]; then python3 "$refs"; break; fi
done
(cd "$dir" && latexmk -pdf main.tex)
if grep -Eq "(Citation|Reference) .* undefined|There were undefined" "$dir/main.log"; then
    grep -E "(Citation|Reference) .* undefined|There were undefined" "$dir/main.log" >&2
    echo "FAIL: undefined references or citations in $dir/main.log" >&2
    exit 1
fi
if [ "$limit" = 1 ]; then
    python3 "$here/check_pages.py" "$dir"
fi
