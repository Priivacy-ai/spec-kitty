---
work_package_id: WP06
title: Background Sync & Runtime Integration
lane: "done"
dependencies: [WP02, WP04]
base_branch: 047-namespace-aware-artifact-body-sync-WP06-merge-base
base_commit: 192ee0b889e1235647c4d3c7aac8af04a58cb04f
created_at: '2026-03-09T10:00:57.143960+00:00'
subtasks:
- T028
- T029
- T030
- T031
- T032
- T033
phase: Phase 3 - Integration
assignee: ''
agent: claude-opus
shell_pid: '14904'
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-03-09T07:09:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs: [FR-007, FR-009]
---

# Work Package Prompt: WP06 – Background Sync & Runtime Integration

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Extend `BackgroundSyncService._sync_once()` to drain body queue after event queue (drain ordering invariant)
- Wire `push_content()` into body drain loop with per-task result handling
- Implement per-task exponential backoff (1s → 5min cap) per NFR-003
- Wire `OfflineBodyUploadQueue` into `SyncRuntime` lifecycle (start/stop)
- Body queue shares DB file with event queue (C-001)
- `pytest tests/specify_cli/sync/test_background_body.py` passes with 90%+ coverage

## Context & Constraints

- **Spec**: FR-007 (durable queue replay), FR-009 (survives restarts), NFR-003 (per-task backoff)
- **Plan**: Architecture → drain ordering, Key Design Decision #5 (events first, bodies second), Module Responsibilities → `background.py` (mod), `runtime.py` (mod)
- **Existing code**: `src/specify_cli/sync/background.py` — `BackgroundSyncService` with `_sync_once()`, `_perform_sync()`, `_lock`, `_consecutive_failures`
- **Existing code**: `src/specify_cli/sync/runtime.py` — `SyncRuntime` with `start()`, `stop()`, `attach_emitter()`
- **WP02**: `OfflineBodyUploadQueue` with `drain()`, `mark_uploaded()`, `mark_failed_retryable()`, `mark_failed_permanent()`
- **WP04**: `push_content(task, auth_token, server_url)` returns `UploadOutcome`
- **Constraint**: Thread safety — `_lock` in `BackgroundSyncService` serializes sync cycles

**Implementation command**: `spec-kitty implement WP06 --base WP04`
(Note: also depends on WP02 — if WP02 is on a different branch, merge it first)

## Subtasks & Detailed Guidance

### Subtask T028 – Extend _sync_once() for Body Queue Drain

- **Purpose**: Add body queue drain as the second phase of each sync cycle, after event queue drain. This preserves the invariant that dossier index events reach SaaS before body uploads (Design Decision #5).

- **Steps**:
  1. Read `src/specify_cli/sync/background.py` carefully — understand the existing `_sync_once()` flow
  2. After the existing event batch sync, add body drain:
     ```python
     def _sync_once(self) -> BatchSyncResult:
         """Single sync cycle: drain events, then drain body uploads."""
         # Existing: drain event queue
         result = self._drain_event_queue()

         # NEW: drain body upload queue
         if self._body_queue is not None:
             self._drain_body_queue()

         return result
     ```
  3. Implement `_drain_body_queue()`:
     ```python
     def _drain_body_queue(self) -> None:
         """Drain body upload queue, one task at a time."""
         auth_token = self._auth.get_access_token()
         if auth_token is None:
             logger.debug("No auth token available, skipping body queue drain")
             return

         tasks = self._body_queue.drain(limit=50)
         if not tasks:
             return

         server_url = self._config.server_url
         for task in tasks:
             outcome = push_content(task, auth_token, server_url)
             self._handle_body_outcome(task, outcome)
     ```
  4. The `_lock` already protects the entire `_sync_once()` call — no additional locking needed

- **Files**: `src/specify_cli/sync/background.py` (modify, ~30 lines)
- **Parallel?**: No — core integration.
- **Notes**: Drain limit of 50 per cycle prevents body uploads from blocking the next event drain. If more tasks are queued, they'll be picked up in subsequent cycles.

### Subtask T029 – Wire push_content() into Drain Loop

- **Purpose**: Handle the `UploadOutcome` from each `push_content()` call and update the queue accordingly.

- **Steps**:
  1. Implement `_handle_body_outcome()` in `BackgroundSyncService`:
     ```python
     def _handle_body_outcome(
         self, task: BodyUploadTask, outcome: UploadOutcome,
     ) -> None:
         """Update queue based on upload outcome."""
         if outcome.status == UploadStatus.UPLOADED:
             self._body_queue.mark_uploaded(task.row_id)
             logger.debug("Body uploaded: %s", outcome)

         elif outcome.status == UploadStatus.ALREADY_EXISTS:
             self._body_queue.mark_already_exists(task.row_id)
             logger.debug("Body already exists: %s", outcome)

         elif outcome.status == UploadStatus.FAILED and outcome.retryable:
             self._body_queue.mark_failed_retryable(task.row_id, outcome.reason)
             logger.debug("Body upload retryable failure: %s", outcome)

         elif outcome.status == UploadStatus.FAILED and not outcome.retryable:
             self._body_queue.mark_failed_permanent(task.row_id, outcome.reason)
             logger.warning("Body upload permanent failure: %s", outcome)

         else:
             logger.warning("Unexpected body outcome: %s", outcome)
     ```
  2. Import `push_content` from `body_transport` and `UploadStatus` from `namespace`

- **Files**: `src/specify_cli/sync/background.py` (extend, ~25 lines)
- **Parallel?**: No — depends on T028 drain loop.

### Subtask T030 – Implement Per-Task Exponential Backoff

- **Purpose**: Ensure retryable failures use exponential backoff per NFR-003, preventing tight-loop retry against SaaS.

- **Steps**:
  1. The backoff logic is already in `OfflineBodyUploadQueue.mark_failed_retryable()` (WP02, T010):
     - Formula: `min(1.0 * 2^retry_count, 300.0)` seconds
     - `next_attempt_at = time.time() + backoff_seconds`
  2. Verify the drain query in T009 correctly filters: `WHERE next_attempt_at <= ?`
  3. In `_drain_body_queue()`, add stale task cleanup:
     ```python
     # Remove tasks that have exceeded max retries (prevent unbounded growth)
     removed = self._body_queue.remove_stale(max_retry_count=20)
     if removed > 0:
         logger.info("Removed %d stale body upload tasks", removed)
     ```
  4. Document the backoff progression in a code comment:
     ```python
     # Backoff progression (NFR-003):
     # retry 0 → 1s, retry 1 → 2s, retry 2 → 4s, retry 3 → 8s,
     # retry 4 → 16s, retry 5 → 32s, retry 6 → 64s, retry 7 → 128s,
     # retry 8 → 256s, retry 9+ → 300s (5 min cap)
     ```

- **Files**: `src/specify_cli/sync/background.py` (extend, ~10 lines)
- **Parallel?**: No — part of drain loop.
- **Notes**: Max retry count of 20 means a task survives ~24+ hours of failures before being removed. This is generous enough for temporary SaaS outages.

### Subtask T031 – Wire Body Queue into SyncRuntime Lifecycle

- **Purpose**: Ensure `OfflineBodyUploadQueue` is created during `SyncRuntime.start()` and made available to `BackgroundSyncService`.

- **Steps**:
  1. Read `src/specify_cli/sync/runtime.py` — understand `SyncRuntime` structure
  2. Add `body_queue` attribute to `SyncRuntime`:
     ```python
     @dataclass
     class SyncRuntime:
         background_service: BackgroundSyncService | None = None
         ws_client: WebSocketClient | None = None
         emitter: EventEmitter | None = None
         body_queue: OfflineBodyUploadQueue | None = None  # NEW
         started: bool = False
     ```
  3. In `start()`, create `OfflineBodyUploadQueue` and pass to `BackgroundSyncService`:
     ```python
     from .body_queue import OfflineBodyUploadQueue

     def start(self) -> None:
         # ... existing code ...
         self.body_queue = OfflineBodyUploadQueue(db_path=queue_db_path)
         # Pass to BackgroundSyncService
         if self.background_service is not None:
             self.background_service._body_queue = self.body_queue
     ```
  4. In `stop()`, ensure body queue is cleaned up (close connection if needed)
  5. Add `_body_queue` attribute to `BackgroundSyncService.__init__()`:
     ```python
     def __init__(self, ...):
         # ... existing ...
         self._body_queue: OfflineBodyUploadQueue | None = None
     ```

- **Files**: `src/specify_cli/sync/runtime.py` (modify, ~15 lines), `src/specify_cli/sync/background.py` (modify, ~5 lines)
- **Parallel?**: Yes — can proceed alongside T028-T030.

### Subtask T032 – Ensure Shared DB Connection

- **Purpose**: Body queue and event queue must use the same SQLite DB file (C-001) but can have separate connection objects. The DB path must be scope-aware (same as event queue).

- **Steps**:
  1. Ensure `OfflineBodyUploadQueue` uses the same `db_path` resolution logic as `OfflineQueue`:
     - Unauthenticated: `~/.spec-kitty/queue.db`
     - Authenticated: `~/.spec-kitty/queues/queue-<scope-hash>.db`
  2. In `runtime.py`, pass the resolved DB path to both queue constructors:
     ```python
     # Both queues use the same DB file
     db_path = resolve_queue_db_path()  # or however the existing code resolves it
     self.event_queue = OfflineQueue(db_path=db_path)
     self.body_queue = OfflineBodyUploadQueue(db_path=db_path)
     ```
  3. Verify that `ensure_body_queue_schema()` (from T006) runs on the shared DB — it must create the `body_upload_queue` table in the same file as `queue`
  4. SQLite handles concurrent access from separate `Connection` objects in the same process (WAL mode)

- **Files**: `src/specify_cli/sync/runtime.py` (modify, ~10 lines)
- **Parallel?**: Yes — can proceed alongside T028-T030.
- **Notes**: If the existing `OfflineQueue` doesn't expose its `db_path`, you may need to extract the path resolution logic into a shared function or read it from `SyncConfig`.

### Subtask T033 – Write test_background_body.py

- **Purpose**: Test the background sync body drain integration.

- **Steps**:
  1. Create `tests/specify_cli/sync/test_background_body.py`
  2. Create fixtures:
     - Mock `AuthClient` with `get_access_token()` returning a test token
     - Real `OfflineBodyUploadQueue` with `tmp_path` DB
     - Mock `push_content()` returning configurable `UploadOutcome`
     - `SyncConfig` with test server URL
  3. Test categories:
     - **Drain ordering**: Events drain before bodies (mock event queue, verify call order)
     - **Successful upload**: `push_content` returns UPLOADED → task removed from queue
     - **Already exists**: `push_content` returns ALREADY_EXISTS → task removed from queue
     - **Retryable failure**: `push_content` returns FAILED(retryable=True) → task stays, `retry_count` incremented, `next_attempt_at` in future
     - **Permanent failure**: `push_content` returns FAILED(retryable=False) → task removed (poison row)
     - **No auth token**: `get_access_token()` returns None → body drain skipped entirely
     - **Empty queue**: No tasks → no `push_content` calls
     - **Backoff respected**: Task with `next_attempt_at` in future → not drained
     - **Stale removal**: Tasks with retry_count > 20 → removed
     - **Runtime lifecycle**: `SyncRuntime.start()` creates body queue; `stop()` cleans up
     - **Shared DB path**: Both queues point to same file

- **Files**: `tests/specify_cli/sync/test_background_body.py` (new, ~200 lines)
- **Parallel?**: No — needs all integration code from T028-T032.
- **Notes**: Use `unittest.mock.patch` for `push_content` and event queue drain. Use real `OfflineBodyUploadQueue` with `tmp_path` for persistence tests.

## Risks & Mitigations

- **Risk**: Modifying `BackgroundSyncService` breaks existing event sync. **Mitigation**: Body drain is additive (appended after event drain); guard with `if self._body_queue is not None`.
- **Risk**: Thread contention between body drain and event drain. **Mitigation**: Both run inside the same `_lock` — serialized by design.
- **Risk**: Auth token expires during body drain batch. **Mitigation**: If `push_content` returns 401, the task stays queued with retryable=True. Next cycle will refresh auth.

## Review Guidance

- Verify drain ordering: events ALWAYS before bodies
- Verify `_body_queue` is guarded with `is not None` checks (backward compatible if body queue not initialized)
- Verify backoff formula matches NFR-003: `min(1.0 * 2^retry, 300.0)` seconds
- Verify `mark_uploaded/already_exists` → DELETE, `mark_failed_retryable` → UPDATE, `mark_failed_permanent` → DELETE
- Verify runtime lifecycle: body queue created in `start()`, available in `stop()`
- Verify shared DB path between event queue and body queue
- Run `mypy --strict` on modified files

## Activity Log

- 2026-03-09T07:09:45Z – system – lane=planned – Prompt created.
- 2026-03-09T10:00:57Z – claude-opus – shell_pid=12054 – lane=doing – Assigned agent via workflow command
- 2026-03-09T10:05:54Z – claude-opus – shell_pid=12054 – lane=for_review – Ready for review: background sync body queue drain with drain ordering (events→bodies), per-task outcome handling, stale cleanup, shared DB path (C-001). 13 tests, 110 sync suite pass, ruff clean.
- 2026-03-09T10:06:29Z – claude-opus – shell_pid=14904 – lane=doing – Started review via workflow command
- 2026-03-09T10:07:42Z – claude-opus – shell_pid=14904 – lane=done – Review passed: Drain ordering (events→bodies) correct, all 4 UploadStatus outcomes handled with correct queue operations, _body_queue guarded for backward compat, backoff per NFR-003, stale cleanup at 20 retries, shared DB path (C-001), runtime lifecycle clean. 13 tests + 110 sync suite all pass. Ruff clean. | Done override: Review approved; WP branch not yet merged to 2.x (merge happens at feature completion)
