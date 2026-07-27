# Issue matrix — coord-write-placement-closure-01KYCF83

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2917 | Runtime-state corpus re-drifts every merge (no birth-cutover) | fixed | WP01 front-load (`3f279a71a`) cleared the red; WP09 (`82eabc02e`) birth-cutover at land closes the drift source; WP10 (`22d22008d`) re-keyed the guard to a non-vacuous event-log birth invariant. All approved. |
| #2874 | Coord-trust write-placement (merged base this mission extends) | verified-already-fixed | PR #2874 merged 2026-07-23; this mission closes its read-side + Gap-2 residual |
| #1716 | `emit` `_current_branch` HEAD-derived fallback fork | fixed | WP04 (`85a59648a`) closed the `_resolve_write_target` HEAD-derived fallback (zero production callers remain) + routes through the placement port. Approved; red-first verified. |
| #2684 | Subtask-completion / claim event-sourcing (InnerStateChanged base) | verified-already-fixed | Base shipped; FR-008 (WP04/WP05) event-sources the two remaining authoring paths |
| #1619 | Runtime/state overhaul epic (parent) | deferred-with-followup | This mission is one slice; broader dual-write retirement stays out of scope (C-002). Follow-up: #1619 (parent epic remains open to track it) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
