# Plan: Sync Rejection Classification And Queue Retry Hygiene

## Architecture

```
src/specify_cli/sync/
├── batch.py        # WP01 + WP02: new "failed_transient" status; rewire 401/403/5xx call sites
└── queue.py        # WP01: process_batch_results respects failed_transient (no mutation)

tests/sync/
└── test_batch_retry_hygiene.py   # WP02: regression tests for FR-3..FR-9
```

The contract change is intentionally minimal: one new value for
`BatchEventResult.status` (`"failed_transient"`) and one new branch in
`OfflineQueue.process_batch_results` that does nothing for that status.

## Implementation Approach

### WP01 — Queue + result-shape contract change

1. Extend the `BatchEventResult` docstring/attribute set to declare a fifth
   status value, `"failed_transient"`.
2. Update `OfflineQueue.process_batch_results` to:
   - keep DELETE for `success` / `duplicate` / `failed_permanent`;
   - keep UPDATE retry+=1 for `rejected`;
   - take no action for `failed_transient`.
3. Keep the transaction wrapper exactly as today (`commit` / `rollback`).
4. Leave `BatchSyncResult.failed_results` returning both `rejected` and
   `failed_permanent` (operator summary). Add `failed_transient` into that
   property so summaries continue to surface those events with category
   counts, while the queue still leaves them alone.

### WP02 — Wire batch HTTP error paths to the new status

For every site in `batch.py` that currently writes
`status="rejected"` for a *batch-level* failure, switch to
`status="failed_transient"`. Affected sites:

- `_record_all_events_failed(...)` — generic helper called for HTTP "else",
  Timeout-stdlib-fallback "else", ConnectionError, and the
  `_current_team_slug() is None` skip path. This helper becomes the single
  place where transient batch-level failures get recorded; we add a parameter
  (or split helpers) so callers indicate whether the failure is transient.
- The two inline 401 branches in `sync_offline_queue_to_server` (primary path
  and stdlib-fallback path) currently build `BatchEventResult(..., status="rejected", error_category="auth_expired")` — flip to `failed_transient`.
- The `_team_slug` pre-flight skip path uses `_record_all_events_failed(...)`
  with category `CATEGORY_MISSING_PRIVATE_TEAM`; switch via the new transient
  parameter.

The 400-path (`_parse_error_response`) is per-event and remains `rejected`.

## Decisions

- **New status value vs. category gate**: We pick a new status value
  (`failed_transient`) rather than gating on category inside
  `process_batch_results`. Rationale: keeps the queue layer ignorant of HTTP
  category strings; semantics live in the producer (`batch.py`).
- **Don't requeue / re-insert**: We never removed transient events from SQLite
  in the first place — `drain_queue` reads but only deletion happens via
  `process_batch_results`. So leaving them untouched is the correct
  non-mutating behavior.
- **Operator output**: Continue to print the category summary so operators see
  e.g. "auth_expired: 7" — this is unchanged.

## Test Plan

New tests under `tests/sync/test_batch_retry_hygiene.py` use the existing
`temp_queue` / `populated_queue` fixtures from `test_batch_sync.py`. For each
HTTP status mocked via `requests.post`:

1. 401 → assert all event rows have `retry_count == 0` after sync.
2. 403 + private-team body → same.
3. 403 + generic forbidden body → same.
4. 500 → same.
5. Pre-flight `_current_team_slug() is None` → same.
6. 200 + per-event rejection → assert affected row has `retry_count == 1`
   (existing behavior preserved).

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing tests assert `status="rejected"` for 401/403/5xx | Audit and update those assertions; the contract change is intentional |
| Callers of `BatchEventResult` outside `sync/` | grep shows none — the dataclass is only consumed inside `sync/` |
| `format_sync_summary` references `failed_results` | Property updated to include `failed_transient` so the human-readable summary still lists them |
