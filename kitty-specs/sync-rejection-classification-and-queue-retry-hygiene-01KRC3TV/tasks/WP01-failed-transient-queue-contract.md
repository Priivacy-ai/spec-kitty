---
work_package_id: WP01
title: Sync rejection classification and queue retry hygiene
dependencies: []
requirement_refs:
- FR-1
- FR-2
- FR-3
- FR-4
- FR-5
- FR-6
- FR-7
- FR-8
- FR-9
- FR-10
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Implementation
assignee: ''
agent: ''
history:
- timestamp: '2026-05-11T18:15:00Z'
  agent: claude
  action: Prompt generated for Mission 5
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/batch.py
- src/specify_cli/sync/queue.py
- tests/sync/test_batch_retry_hygiene.py
tags: []
---

# Work Package WP01 — Sync rejection classification and queue retry hygiene

## Goal

Add a new `BatchEventResult.status` value, `"failed_transient"`, teach
`OfflineQueue.process_batch_results` to treat it as a no-op (no DELETE, no
retry_count bump), and route every batch-level failure call site in
`src/specify_cli/sync/batch.py` through that new status. Lock the behavior in
with focused regression tests under `tests/sync/test_batch_retry_hygiene.py`.

The single WP scope is intentional: the dataclass contract, the queue branch,
and the batch HTTP wiring are tightly coupled — splitting them would force the
intermediate commit to either lie about behavior (status added but unused) or
to break tests temporarily.

## Subtasks

- **T001** — Extend `BatchEventResult` docstring/comments in
  `src/specify_cli/sync/batch.py` to declare the new status value
  `failed_transient` and explain it (batch-level, non-mutating).
- **T002** — Update `OfflineQueue.process_batch_results` in
  `src/specify_cli/sync/queue.py`:
  - `success` / `duplicate` / `failed_permanent` → DELETE (unchanged).
  - `rejected` → UPDATE retry_count = retry_count + 1 (unchanged).
  - `failed_transient` → no mutation (new branch).
  - Preserve transactional semantics (single commit / rollback).
- **T003** — Update `BatchSyncResult.failed_results` to include
  `failed_transient`, so the operator summary still enumerates them by
  category.
- **T004** — Add a `transient: bool = False` kwarg to
  `_record_all_events_failed`. When `True`, results are constructed with
  `status="failed_transient"` instead of `"rejected"`.
- **T005** — Switch the following call sites in `sync_offline_queue_to_server`
  to record `failed_transient`:
  - Pre-flight `_current_team_slug is None` (category
    `direct_ingress_missing_private_team`).
  - Two inline 401 branches (primary + stdlib fallback): `auth_expired`.
  - HTTP "else" branch (`_record_all_events_failed`): transient=True.
  - Timeout fallback's "else" branch: transient=True.
  - ConnectionError path: transient=True.
  - Per-event 400 path (`_parse_error_response`) stays `rejected` — it is
    per-event content rejection.
- **T006** — Add `tests/sync/test_batch_retry_hygiene.py` with these tests
  (all under `SPEC_KITTY_ENABLE_SAAS_SYNC=1`):
  1. `test_http_401_does_not_bump_retry_count`
  2. `test_http_403_private_team_does_not_bump_retry_count`
  3. `test_http_403_generic_unauthorized_does_not_bump_retry_count`
  4. `test_http_500_does_not_bump_retry_count`
  5. `test_preflight_no_private_team_does_not_bump_retry_count`
  6. `test_per_event_rejection_still_bumps_retry_count` (sanity check that
     `rejected` still mutates).
  Each test mocks `requests.post` and `_current_team_slug` (where needed)
  and verifies `retry_count` directly via SQLite:
  ```python
  import sqlite3
  conn = sqlite3.connect(queue.db_path)
  rows = list(conn.execute("SELECT event_id, retry_count FROM queue"))
  conn.close()
  ```

## Acceptance

- `BatchEventResult` docstring mentions `failed_transient` with intent.
- `process_batch_results` is a 4-way switch (success/duplicate/failed_permanent
  → DELETE; rejected → UPDATE; failed_transient → no-op).
- All 6 new tests in `tests/sync/test_batch_retry_hygiene.py` pass.
- `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/test_batch_sync.py tests/sync/test_batch_error_surfacing.py tests/sync/test_batch_retry_hygiene.py -q` is fully green.
- Wider `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/ -q` shows no
  new failures relative to baseline (7 pre-existing daemon / orphan_sweep /
  tracker.origin_integration failures unchanged and out of scope).

## Out of Scope

- Body queue (`body_queue.py`) retry semantics — different module, separate
  daemon path.
- Daemon scheduling / backoff for transient failures (queue rows remain in
  place, daemon retries naturally on its next tick).
- Categorization keyword lists or operator-facing summary text.

## Implementation Notes

- Keep the `process_batch_results` transaction structure exactly as today.
- Be careful with the 401 branches — they construct `BatchEventResult` inline
  (twice), not via `_record_all_events_failed`. Both must change.
- Operator output: keep `print(...)` lines unchanged so user-facing diagnostic
  text doesn't change.
