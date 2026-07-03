# Issue matrix — tasks-py-degod-wave2-01KWH9EQ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2305 | Follow-up: finish tasks.py degod — Render seam unification + whole-file shim relocation (Wave 2, #2173) | in-mission | Primary mission scope: Stream A = FR-005/FR-006/FR-007 (Render seam + AST gate); Stream B = FR-001..FR-004 + FR-008 (relocation + LOC gate). |
| #2173 | Epic: Infrastructure-to-logic separation | deferred-with-followup | Parent epic — this mission executes its Wave 2 tasks.py slice under C-004 seam discipline (one production adapter per port, builder/shell injection); the epic's Phase 1/2 port work remains open. |
| #2034 | CI gates select tests by marker; no gate selects `unit` or `contract` | in-mission | Domain-matched slice only: FR-009 makes the tasks-domain test surface gate-visible; FR-010 refreshes the issue with the 2026-07-02 re-census (257/26,612 marker-invisible; original failure list largely fixed/re-marked). Repo-wide structural fix stays open upstream. |
| #2300 | Unify the coord+protected skip-vs-refuse behavior | deferred-with-followup | Deliberately NOT touched (C-001): divergence preserved verbatim; reconciliation is #2300's own behavior-change mission. |
| #2116 | Decompose agent tasks.py god-command | in-mission | Wave 1 closed the body-thinning portion; this mission delivers the remaining whole-file registration-shim state (FR-001..FR-004). |
| #2306 | test_untrusted_path_containment RED on main (inventory.md 1325→1326 off-by-one from Wave 1) | in-mission | Domain-matched campsite fold (pre-plan squad L1): 1-line inventory correction pre-step + inventory row moves with the move_task family relocation (FR-001/FR-002 seam checklist). Filed per C-007 before absorbing as baseline. |
| #2031 | Stale-assertion analyzer lacks cross-file move detection | deferred-with-followup | Reference only: Wave 2's ~40-symbol relocation will trigger a large false-positive storm from the post-merge analyzer at every WP merge (witnessed 280+ on a single-module extraction). Review artifacts must expect noise and cross-check against the FR-002 seam checklists; the analyzer fix is #2031's own work. |
| #2283 | Test-delivery topology: CI-only shards invisible pre-PR | deferred-with-followup | Structural parent of #2034. FR-009 closes its cause (a) marker-gate divergence for the tasks domain only; causes (b) venv skew and (c) producer-conformance sweep remain #2283's scope. FR-010's census comment references it. |
| #2295 | Triage the 17 CI-quarantined tests (Wave-0 orphan binding) | deferred-with-followup | Reference only: defines the current `_gate_coverage_baseline.json` floor (4 orphan paths, none in the tasks domain). FR-009's baseline-growth prohibition is measured against this floor. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
