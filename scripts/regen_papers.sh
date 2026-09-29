#!/usr/bin/env bash
# Regenerate every figure, table and macro file the two workshop papers input,
# from the committed study databases (deterministic: stored seeds, no LLM calls).
#
# Layout written (report/generated/ is git-ignored):
#   studies/<study>/report/generated/            headline run (untagged macros \voi...)
#   studies/<study>/report/generated/<tag>/      side runs (macros \voi<tag>...)
#
# usage: scripts/regen_papers.sh            (from the repo root)
set -euo pipefail
cd "$(dirname "$0")/.."

SO="claude_cli:opus,claude_cli:sonnet"   # the coherent elicitor pair (LEARNINGS 2026-09-28, iteration 2)
run() { echo "+ $*"; uv run python -m "$@" > /dev/null; }

regen() {  # regen STUDY PROTOCOL [--members M] [--tag T]: figures, tables, extra
  local study=$1 prot=$2; shift 2
  local m
  for m in voi_rank.analysis.figures voi_rank.analysis.tables voi_rank.analysis.extra; do
    run "$m" --study "studies/$study" --protocol "$prot" "$@"
  done
}

# --- track 1: studies/ai-safety-evals ---------------------------------------
T1=ai-safety-evals
rm -rf "studies/$T1/report/generated" && mkdir -p "studies/$T1/report/generated" && touch "studies/$T1/report/generated/.gitkeep"
regen $T1 p003 --members $SO                               # headline: sonnet+opus
regen $T1 p001 --tag base                                  # haiku baseline
regen $T1 p003 --tag allm                                  # all three members (member agreement)
run voi_rank.analysis.figures --study studies/$T1 --protocol g001 --members $SO --tag gauss
run voi_rank.analysis.tables  --study studies/$T1 --protocol g001 --members $SO --tag gauss
run voi_rank.analysis.compare_models --study studies/$T1 --binary p003 --gaussian g001 --members $SO

# --- track 2: studies/sim2real -----------------------------------------------
T2=sim2real
rm -rf "studies/$T2/report/generated" && mkdir -p "studies/$T2/report/generated" && touch "studies/$T2/report/generated/.gitkeep"
regen $T2 p004 --members $SO                               # headline: staged, sonnet+opus
regen $T2 p003 --members $SO --tag single                  # single-prompt comparison
regen $T2 p001 --tag base                                  # haiku baseline
regen $T2 p004 --tag allm                                  # all three members
run voi_rank.analysis.figures --study studies/$T2 --protocol g001 --members $SO --tag gauss
run voi_rank.analysis.tables  --study studies/$T2 --protocol g001 --members $SO --tag gauss
run voi_rank.analysis.compare_models --study studies/$T2 --binary p004 --gaussian g001 --members $SO
run voi_rank.analysis.compare_models --study studies/$T2 --binary p003 --gaussian g001 --members $SO --tag cmpsingle

# --- business, cross-family sanity check on 68 scenarios (tag biz) ------------
run voi_rank.analysis.compare_models --study studies/business --binary p005 --gaussian g001 --members $SO --tag biz
run voi_rank.analysis.extra --study studies/business --protocol p005 --members $SO --tag biz

echo "done"
