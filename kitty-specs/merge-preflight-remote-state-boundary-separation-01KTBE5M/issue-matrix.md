# Issue matrix — merge-preflight-remote-state-boundary-separation-01KTBE5M

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1706 | Local merge blocked when local target branch is ahead of origin | fixed | push_preflight.py — `is_safe_to_push` returns True for `ahead`/`behind`/`in_sync`/`no_tracking_branch`; `check_push_safety` only called when `--push` is requested; ATDD test_issue_1706_local_ahead_behind_no_push_does_not_block passes |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`.
