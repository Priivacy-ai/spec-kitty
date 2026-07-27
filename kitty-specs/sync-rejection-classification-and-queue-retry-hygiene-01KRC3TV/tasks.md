# Tasks: Sync Rejection Classification And Queue Retry Hygiene

## Work Packages

| WP | Title | Depends on | Files |
|----|-------|-----------|-------|
| WP01 | Sync rejection classification and queue retry hygiene | — | `src/specify_cli/sync/batch.py`, `src/specify_cli/sync/queue.py`, `tests/sync/test_batch_retry_hygiene.py` |

Mission 5 is intentionally a single WP because the dataclass contract, the
queue branch, and the batch HTTP wiring are tightly coupled. Any intermediate
split would leave the queue lying about behavior (e.g. status added but unused,
or queue not yet aware of new status).

## WP01 — Sync rejection classification and queue retry hygiene

See `tasks/WP01-failed-transient-queue-contract.md` for the full prompt and
acceptance criteria. Subtasks:

- T001 — Extend `BatchEventResult` docstring with `failed_transient`.
- T002 — `OfflineQueue.process_batch_results` no-op for `failed_transient`.
- T003 — `BatchSyncResult.failed_results` includes `failed_transient`.
- T004 — `_record_all_events_failed(transient=...)` parameter.
- T005 — Wire 401/403/5xx/timeout/connection/teamspace-skip paths.
- T006 — Regression tests in `tests/sync/test_batch_retry_hygiene.py`.

## Acceptance

- `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/test_batch_retry_hygiene.py tests/sync/test_batch_sync.py tests/sync/test_batch_error_surfacing.py -q` is fully green.
- Full `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/ -q` shows no
  regressions beyond the pre-existing infrastructure-related failures.
