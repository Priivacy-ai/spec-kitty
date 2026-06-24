# Issue matrix — decompose-agent-tasks-god-module-01KVWVAR

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1797 | Parent: decompose agent/tasks.py god module | deferred-with-followup | This mission closes the tasks.py child (#2058). Follow-up: #1797 (parent epic) tracks the sibling merge/mission god-module decompositions. |
| #2060 | PR-2060 review: centralize commit routing via commit_for_mission | fixed | WP07 routes all 3 planning-commit tails through commit_for_mission (AST-asserted router-only), output-preserving; FR-007 literal-deletion deferred with reviewer-validated rationale (pre-checks handle the live coord-topology silent-skip, not dead). See acceptance-matrix FR-006/007/008. |
| #2058 | Decompose agent/tasks.py + add #2058 decomposition pointer comment (FR-002/SC-005) | fixed | tasks.py 4633→3346 LOC across 5 cohesive seams; #2058 pointer comment added (WP07); every function maxCC≤15; CLI byte-identical (golden contract green). 515 tests pass on the integrated branch. |
| #2056 | Pointer-comment convention precedent (agent/mission.py) | verified-already-fixed | Referenced in spec.md FR-002 only as a convention precedent; the agent/mission.py pointer comment already exists and was reused verbatim as the style for the #2058 pointer. Not in scope to change here. |
| #1623 | Pointer-comment convention precedent (doctor.py) | verified-already-fixed | Referenced in spec.md FR-002 only as a convention precedent; the doctor.py pointer comment already exists and was reused as the style for the #2058 pointer. Not in scope to change here. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
