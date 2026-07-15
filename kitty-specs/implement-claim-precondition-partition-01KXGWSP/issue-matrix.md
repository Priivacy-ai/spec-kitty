# Issue matrix — implement-claim-precondition-partition-01KXGWSP

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2533 | Bug: PR-bound mission claim aborts on "Planning artifacts not committed" (coord-branch split-brain) | fixed | Read/compare side WP01 (`resolve_precondition_ref`, 3d57d5c50); write-side WP02 (two-transaction partition, 052ab0fa2); move-task regression + docs WP03 (9d53095d1). All WPs approved. PR `Closes #2533`. |
| #2624 | Epic: Root & worktree-path detection — resolution, lane routing, containment discipline | deferred-with-followup | Parent epic (spec.md:5). This mission is one scoped child (the claim-precondition partition); the epic remains open for its other children — not closed by this PR. |
| #2160 | Coord topology: unify artifact authority for task/status surfaces (placement-seam SSOT cluster) | deferred-with-followup | C-004 (spec.md:128) — retiring the bespoke staging path into `commit_router` is explicitly deferred; owned by the #2160 cluster |
| #2602 | Revisit pr_bound⇒coord topology derivation for solo --start-branch missions | deferred-with-followup | C-003 (spec.md:127, :162) — topology-derivation change is out of scope; owned by #2602 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
