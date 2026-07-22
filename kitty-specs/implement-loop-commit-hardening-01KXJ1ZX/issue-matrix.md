# Issue matrix — implement-loop-commit-hardening-01KXJ1ZX

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2647 | move-task fails from a lane-worktree cwd | fixed | WP06 commit 9409d4c07 — write-side #2453 fix; test_tasks_move_task_cwd.py |
| #2648 | Delete the 767 divert; narrow-triple fail-close | fixed | WP01 commit 1800a925c |
| #2649 | Sonar degod (implement.py + tasks_move_task.py) | fixed | WP02+WP03 (implement.py) + WP07 (tasks_move_task.py) |
| #2650 | Consolidate the three partition-decision sites | fixed | WP04 (gate + cli ref-unif) + WP05 (commit_router classifier swap) |
| #2453 | Write-side cwd from_lane re-derivation for coordination-less missions | fixed | WP06 commit 9409d4c07 — route modern coordination-less to repo_root; ratchet updated |
| #2604 | _mt_commit_wp_file complexity | fixed | folded into WP07 (helper extractions) |
| #2160 | Implement-loop coord-authority split-brain (parent epic) | deferred-with-followup | this mission closes sub-issues #2647/#2648/#2649/#2650/#2453; epic continues with other slices |
| #2533 | Solo PR-bound coord claim precondition (regression guard) | verified-already-fixed | merged predecessor (ac2250f); its regression guard kept green by WP01/WP04/WP05 |
| #2463 | placement_ref None-overload disambiguation (context) | verified-already-fixed | embodied by WP01 narrow-triple + WP04 INV-7 characterization |
| #2576 | rollback_uncheck_error dual-handler (contract) | verified-already-fixed | dual-handler preserved by WP07 (C-001) |
| #2639 | draft PR adds a param to _do_move_task (landing note) | deferred-with-followup | not landed; WP07 param-object (_MoveTaskArgs, 2 params) leaves headroom for it |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
