# Issue matrix — implement-review-loop-recovery-01KXG2TD

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2573 | move-task --to for_review runs a synchronous multi-minute pre-review gate that reads as a hang | fixed | dedicated RED regression-test commit and final GREEN implementation commit; WP01 cycle-2 review: 80 focused tests passed |
| #2549 | move-task --force routes placement-partition status to the wrong branch | verified-already-fixed | `spec.md:114`; planning-base delivery `8612ee788` and green routing tests |
| #2570 | Multi-lane implement-loop friction | verified-already-fixed | `spec.md:115`; planning-base deliveries `e7cab2693` and `dd83e5b6f` |
| #2626 | Lane-transition auto-commit fails when the lane worktree is missing | deferred-with-followup | `spec.md:116`; retained as reproduction-first follow-up issue #2626 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
