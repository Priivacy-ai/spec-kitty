# Issue matrix — tasks-py-degod-01KWF08S

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2116 | Decompose agent tasks.py god-command | fixed | Decision logic extracted to 4 pure tested cores (tasks_transition_core/mapping_core/status_view/ports); all 5 fat bodies thinned ≤150 LOC; byte-identical (golden 42). Whole-file shim relocation is a tracked follow-up mission (spec Deferred + docs/plans/tasks-py-degod-followup-mission-debrief.md). |
| #2173 | Infra-logic separation (ports) | deferred-with-followup | Epic — mission delivers the reference port set (FsReader + two-capability CoordCommitRouter) the epic's Phase-2 MissionResolver generalizes; epic remains open. |
| #2300 | Skip-vs-refuse commit divergence | deferred-with-followup | Deliberately PRESERVED by NFR-001 (frozen in WP01 T005, not reconciled); reconciliation is a behavior change deferred to the #2300 follow-up. |
| #2056 | tasks.py maintainability debt | fixed | The interleaved decision/IO/render logic is separated into pure cores behind injected ports; the #1 change-magnet's decision logic is now isolated + tested. |
| #2114 | agent tasks --help/__init__ CLI contract harness | fixed | WP01 EXTENDED the #2114 harness with the coord-topology fixture + the mutating-command + all-move_task-branch freeze it previously punted (42 golden cases). |
| #2160 | Coord-authority commit routing | deferred-with-followup | Mission delivers the structural form (CoordRead≠CoordWrite two-capability port; coord skip-exit-0 + partial-write timing preserved); the broader coord-authority line continues. |
| #2072 | Test-suite friction / characterization coverage | deferred-with-followup | Mission contributes the golden characterization harness + per-core --cov-branch gates; #2072's composite-key re-key (predecessor) enabled it; broader friction epic continues. |
| #2294 | tasks.py decomposition follow-through | verified-already-fixed | Wave 0 (#2294) landed before this mission; its CI-suite-marker binding is the NFR-002 enabler and is in place. |
| #2299 | move_task decision-branch extraction safety | fixed | WP01 froze every named move_task decision branch (T006) with a from-harness branch-cov gate, so WP03's extraction was guarded; verified across the rewire WPs. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
