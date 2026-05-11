# Tasks: Sync Rejection Classification And Queue Retry Hygiene

## Work Packages

| WP | Title | Depends on | Files |
|----|-------|-----------|-------|
| WP01 | Introduce `failed_transient` status + non-mutating queue branch | — | `src/specify_cli/sync/batch.py`, `src/specify_cli/sync/queue.py` |
| WP02 | Wire batch HTTP 401/403/5xx/transport/teamspace-skip paths and add regression tests | WP01 | `src/specify_cli/sync/batch.py`, `tests/sync/test_batch_retry_hygiene.py` |

## Subtasks

### WP01

- T001: Extend `BatchEventResult` docstring with `failed_transient` status value.
- T002: Update `OfflineQueue.process_batch_results` to skip mutation for
  `failed_transient`; preserve transactional semantics for the other branches.
- T003: Update `BatchSyncResult.failed_results` to include `failed_transient`
  so operator summaries continue to surface those events.

### WP02

- T004: Add a transient parameter (or sibling helper) to
  `_record_all_events_failed` so batch-level callers can record
  `failed_transient` while the per-event 400 path still records `rejected`.
- T005: Switch the two inline 401 branches and the generic-HTTP / Timeout /
  ConnectionError branches in `sync_offline_queue_to_server` to record
  `failed_transient`.
- T006: Add regression tests in `tests/sync/test_batch_retry_hygiene.py`:
  401, 403-private-team, 403-generic, 500, pre-flight no-private-team,
  and a happy-path 200-with-per-event-rejection sanity test.

## Acceptance

- `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/test_batch_retry_hygiene.py tests/sync/test_batch_sync.py tests/sync/test_batch_error_surfacing.py -q` passes.
- Full `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/ -q` shows no
  regressions beyond the pre-existing infrastructure-related failures (daemon,
  orphan_sweep, tracker/test_origin_integration).
