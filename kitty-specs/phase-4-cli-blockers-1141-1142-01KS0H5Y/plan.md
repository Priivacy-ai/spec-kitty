# Plan — phase-4-cli-blockers-1141-1142-01KS0H5Y

## Approach

Single PR, two surgical fixes, one test file per issue. Code changes are
contained to `src/specify_cli/audit/shape_registry.py` (#1142) and
`src/specify_cli/status/adapters.py` (#1141, defensive logging only).
The unit test for #1141 lives under `tests/status/` and exercises the
full canonical-emit → fan-out → offline-queue path.

## Architecture

No new modules. No package-boundary changes. No new dependencies.

```
src/specify_cli/audit/shape_registry.py     (modify is_mission_lifecycle_row)
src/specify_cli/status/adapters.py          (instrument fire_saas_fanout)
tests/audit/test_detectors_row_family.py    (extend existing)
tests/status/test_emit_backward_transition.py  (NEW — unit test)
```

## Sequencing

The two fixes are independent. We land them as a single WP because the
patch size is tiny and the operator brief requires one PR.

| Step | Action |
|---|---|
| 1 | Read `is_mission_lifecycle_row`, identify all callers via grep. |
| 2 | Broaden the predicate to accept the 4-aggregate-type set; update both docstrings to reference `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/contracts/audit-row-family.md`. |
| 3 | Extend `tests/audit/test_detectors_row_family.py` (or add a peer file if the existing one is closed) with parametrized cases for each new aggregate type AND a negative case (`aggregate_type == "Foo"`). |
| 4 | Add an `INFO`-level logging breadcrumb at `fire_saas_fanout` entry that includes `wp_id`, `from_lane`, `to_lane`, `force`. Keep the existing `WARNING` log on handler failure. |
| 5 | Write `tests/status/test_emit_backward_transition.py`: register a fake SaaS fan-out handler that records every call into a list; call `emit_status_transition` to drive `planned → claimed → in_progress → for_review → in_review`, then a forced backward `in_review → planned` with `reason="review_rejected"`; assert the handler captured 5 calls in order; assert the last call has `from_lane="in_review"`, `to_lane="planned"`, `force=True`. |
| 6 | Run targeted tests: `tests/audit`, `tests/status`, `tests/sync`. Fix anything red. |
| 7 | Run ruff + mypy on the three packages. |
| 8 | Commit, push, open the PR. |

## Risks

| Risk | Mitigation |
|---|---|
| Broadening the predicate hides a real bug elsewhere where `aggregate_type=Project` should have been `Mission`. | Negative case test (`Foo` aggregate type) confirms the predicate still rejects unknown values. The four accepted values are explicitly enumerated; no wildcard. |
| The unit test passes locally but the canary still fails because the real bug is downstream of `emit_status_transition`. | The breadcrumb log surfaces silent handler failures so a follow-up bisect on a trusted-runner workstation can localize the next root cause. Document this fallback in the PR body. |
| Test doubles for `fire_saas_fanout` don't catch the actual canary failure because the issue may be in `emit_wp_status_changed` → `OfflineQueue.queue_event`. | If the unit-test scaffolding can stand up a real `OfflineQueue` per the existing patterns in `tests/sync/test_offline_queue.py`, peek the queue directly. Otherwise, the fake-handler assertion is sufficient as a regression guard for the emit-path layer. |

## Out-of-scope

- Events-package contract changes.
- SaaS materializer or readiness logic.
- Canary harness changes (different repo).
- Release tagging / version bump.
- Refactoring `emit_status_transition` or `OfflineQueue` beyond the
  minimum needed.
