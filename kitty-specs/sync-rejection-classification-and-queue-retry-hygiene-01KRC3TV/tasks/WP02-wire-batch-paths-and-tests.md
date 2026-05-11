---
work_package_id: "WP02"
title: "Wire batch HTTP failure paths to failed_transient and add regression tests"
dependencies: ["WP01"]
requirement_refs:
  - "FR-3"
  - "FR-4"
  - "FR-5"
  - "FR-6"
  - "FR-7"
  - "FR-8"
planning_base_branch: "main"
merge_target_branch: "main"
branch_strategy: "Planning artifacts were generated on main; completed changes must merge back into main."
subtasks:
  - "T004"
  - "T005"
  - "T006"
phase: "Phase 2 - Wire + Test"
assignee: ""
agent: ""
shell_pid: ""
history:
  - timestamp: "2026-05-11T18:15:00Z"
    agent: "claude"
    action: "Prompt generated for Mission 5"
---

# Work Package WP02 — Wire batch HTTP error paths to `failed_transient` + regression tests

## Goal

Route every batch-level failure call site in `src/specify_cli/sync/batch.py`
through the new `failed_transient` status so 401/403/5xx/transport/teamspace
outcomes leave `retry_count` untouched. Lock the behavior in with focused
regression tests under `tests/sync/`.

## Files

- `src/specify_cli/sync/batch.py`:
  - Add a `transient: bool = False` kwarg (or sibling helper) to
    `_record_all_events_failed`. When `True`, results use
    `status="failed_transient"` instead of `"rejected"`.
  - Pre-flight `_team_slug is None` path → `transient=True`.
  - HTTP 401 inline blocks (primary + stdlib fallback) → use
    `status="failed_transient"`.
  - The "else" HTTP branch (`_record_all_events_failed`) → pass
    `transient=True`.
  - Timeout, ConnectionError, and stdlib-fallback "else" → pass
    `transient=True`.
  - HTTP 400 path (`_parse_error_response`) remains `rejected` — it is
    per-event.
- `tests/sync/test_batch_retry_hygiene.py` (new):
  - Use `requests.post` mocking patterns from `test_batch_sync.py`
    (`@patch("specify_cli.sync.batch.requests.post")`).
  - Reuse the `populated_queue` fixture pattern (5 events with retry_count=0).
  - Mock `_current_team_slug` to return a non-`None` value via the same
    `_install_private_team_for_tests` helper.

## Test Cases (regression)

1. `test_http_401_does_not_bump_retry_count`: server returns 401; assert all
   events still have `retry_count == 0` and `error_category == "auth_expired"`.
2. `test_http_403_private_team_does_not_bump_retry_count`: 403 body with
   `direct_ingress_missing_private_team`; assert `retry_count == 0` and
   category equals `CATEGORY_MISSING_PRIVATE_TEAM`.
3. `test_http_403_generic_unauthorized_does_not_bump_retry_count`: 403 with
   generic forbidden body; category `unauthorized`; `retry_count == 0`.
4. `test_http_500_does_not_bump_retry_count`: 500 returned; category
   `server_error`; `retry_count == 0`.
5. `test_preflight_no_private_team_does_not_bump_retry_count`: pre-flight
   `_current_team_slug` returns `None`; category equals
   `CATEGORY_MISSING_PRIVATE_TEAM`; `retry_count == 0`.
6. `test_per_event_rejection_still_bumps_retry_count`: 200 response with one
   event marked rejected; assert that single event's `retry_count == 1`,
   others remain `0`.

Each test reads the raw queue via:

```python
import sqlite3
conn = sqlite3.connect(queue.db_path)
rows = list(conn.execute("SELECT event_id, retry_count FROM queue"))
conn.close()
```

## Acceptance

- All 6 new tests pass under `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/test_batch_sync.py tests/sync/test_batch_error_surfacing.py tests/sync/test_batch_retry_hygiene.py -q` is fully green.
- Wider `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/ -q` shows no
  new failures relative to baseline (the 7 pre-existing infra-related failures
  are unchanged and out of scope).

## Implementation Notes

- The existing `_record_all_events_failed` is the single most natural choke
  point for batch-level failure recording. Adding `transient=True` keeps the
  surface area small and the diff readable.
- Be careful with the 401 branches: they construct `BatchEventResult` inline
  (twice), not via `_record_all_events_failed`. Both must change.
- Operator output: keep `print(...)` lines unchanged so the user-facing
  diagnostic text doesn't change.
