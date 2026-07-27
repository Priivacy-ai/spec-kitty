# Issue matrix — decompose-mission-god-module-01KVXHF8

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2056 | Decompose `agent/mission.py` god-module (remainder) | fixed | All WP01–WP09 `done`; `mission.py` reduced 4125 → 362 LOC to a thin shim, every cohesive seam extracted (mission_feature_resolution/parsing/record_analysis/branch_context/check_prerequisites/create/setup_plan/accept_merge/finalize; planning-commit residue → commit_router). Golden CLI contract + full mission-touching suite (2429 passed) green; ruff C901≤15 + mypy --strict clean. |
| #2058 | `agent tasks` god-module decomposition (sibling mission) | deferred-with-followup | Out of scope: #2058 is a sibling mission NOT on this base (`c3814ec5a`); see spec.md §A-1. Follow-up: #2058. |
| #1623 | `doctor.py` god-module split | deferred-with-followup | Referenced only as the god-module-pointer convention precedent (spec.md L129); not fixed here. Follow-up: #1623. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
