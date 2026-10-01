# archive

Frozen material from before the 2026-09-30 restructure. Nothing here is maintained.

- `business/`: the original v1 study (68 business scenarios, protocols p000_manual to p005 and g001, its voi.db and report). The external chapter (`../chapter/compute.py`) reads `archive/business/voi.db` read-only.
- `pilots/ai-safety-evals/`, `pilots/sim2real/`: the two SPAIS 2026 pilot studies (track 1 and track 2), each with scenarios, protocols, templates, voi.db and report.
- `pilots/PILOT_ASSESSMENT.md`, `pilots/README_methods.md`, `pilots/README_tracks.md`: the pilots' assessment and method notes.

Everything under `archive/` is frozen at the git tag `pilot-2026-09-30`. The code that produced it is the code at that tag (`git checkout pilot-2026-09-30`); the current `voi_rank/` cannot re-run these protocols (single-stage templates, the Gaussian family, the manual protocol and the six-parameter model were removed).

No current code reads anything under `archive/` except the chapter's read of `archive/business/voi.db` and three read-only tests (tests/test_db.py, tests/test_staged.py, tests/test_study.py). Never write to a database here.
