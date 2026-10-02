#!/usr/bin/env bash
# Regenerate every figure, table and macro of a study from its voi.db alone
# (DESIGN section 7). It analyses the latest stored run of the headline
# protocol; the Monte Carlo run is a separate step (README, run order 4).
#
#   headline        generated/            macros \voi...
#   no-context      generated/noctx/      macros \voinoctx...  the latest run of $NOCTX_PROTOCOL;
#                                          skipped while that protocol has no stored run
#
# Usage: scripts/regen.sh [study-dir]          (default studies/safety-evals)
# Environment: PROTOCOL (default final), NOCTX_PROTOCOL (default final_noctx), DRAWS (default: every draw)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
study="${1:-studies/safety-evals}"
protocol="${PROTOCOL:-final}"
noctx="${NOCTX_PROTOCOL:-final_noctx}"
draws=()
[ -n "${DRAWS:-}" ] && draws=(--draws "$DRAWS")

uv run python -m voi_rank.analysis --study "$study" --protocol "$protocol" "${draws[@]}"
uv run python -m voi_rank.analysis --study "$study" --protocol "$noctx" "${draws[@]}" --tag noctx --optional
