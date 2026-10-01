#!/usr/bin/env bash
# Regenerate every figure, table and macro of a study from its voi.db alone
# (DESIGN section 7). It analyses the latest stored run of the headline
# protocol; the Monte Carlo run is a separate step (README, run order 4).
#
#   headline        generated/            macros \voi...
#   developer       generated/dev/        macros \voidev...  p, B, K from the decision stage
#                                          of $DEV_PROTOCOL, the rest from the headline run;
#                                          skipped while $DEV_PROTOCOL has no valid decision rows
#
# Usage: scripts/regen.sh [study-dir]          (default studies/safety-evals)
# Environment: PROTOCOL (default p001), DEV_PROTOCOL (default p002), DRAWS (default: every draw)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
study="${1:-studies/safety-evals}"
protocol="${PROTOCOL:-p001}"
dev="${DEV_PROTOCOL:-p002}"
draws=()
[ -n "${DRAWS:-}" ] && draws=(--draws "$DRAWS")

uv run python -m voi_rank.analysis --study "$study" --protocol "$protocol" "${draws[@]}"
uv run python -m voi_rank.analysis --study "$study" --protocol "$protocol" "${draws[@]}" \
    --decision-from "$dev" --optional --tag dev
