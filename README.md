# voi-rank

Ranks scenarios by the value of a single measurement sold to a single agent
facing a single binary decision (EVSI / cost), with parameters elicited by
`claude -p` (haiku) and uncertainty propagated by Monte Carlo. See `spec.md`.

## Install

- Requires: Python >= 3.11, [uv](https://docs.astral.sh/uv/), the `claude` CLI
  (authenticated), `latexmk` for the report.
- `uv sync` installs numpy/scipy/matplotlib/pyyaml (+pytest).

## Run order (from this directory)

1. `uv run pytest` — core math acceptance tests.
2. `uv run python -m elicitation.run_elicit --manual` — seed scenarios + hand percentiles.
3. `uv run python -m elicitation.run_propose --n 6` — generate scenarios (needs claude CLI).
4. `uv run python -m elicitation.run_elicit --protocol elicitation/protocols/p001.yaml` — elicit all.
5. `uv run python -m core.mc --protocol p001 --seed 42 --draws 100000` — MC + ranking.
6. `uv run python -m analysis.health --protocol p001 [--compare pXXX]` — health checks.
7. `uv run python -m analysis.figures && uv run python -m analysis.make_tables` — figures/tables from `voi.db`.
8. `cd report && latexmk -pdf main.tex` — compile `report/main.pdf`.

Outputs: `voi.db` (all data + provenance), `report/generated/` (figures,
tables), `report/main.pdf`. Given the committed `voi.db`, steps 5–8 reproduce
every number, figure and table exactly (the stored seed makes the MC
deterministic; a rerun mints a fresh run id and code-hash string in the
report's reproduction appendix). Steps 2–4 call the LLM and are not
bit-reproducible.
