---
work_package_id: WP02
title: Body Queue - SQLite Persistence Layer
lane: "done"
dependencies: [WP01]
base_branch: 047-namespace-aware-artifact-body-sync-WP01
base_commit: 221cac1a3567575e5241d4768086572e970e2e6d
created_at: '2026-03-09T08:23:00.317907+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Foundation
assignee: ''
agent: claude-opus
shell_pid: '50890'
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-03-09T07:09:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs: [FR-007, FR-009, FR-010]
---

# Work Package Prompt: WP02 – Body Queue - SQLite Persistence Layer

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Create `body_upload_queue` SQLite table as a sibling table in the existing queue DB
- Implement `OfflineBodyUploadQueue` class with idempotent enqueue, per-task backoff drain, lifecycle methods, and stats
- Queue survives process restarts (FR-009)
- Idempotent enqueue prevents duplicate tasks for same content+namespace (FR-010)
- Queue capacity bounded to 10,000 tasks (NFR-002)
- Per-task backoff prevents tight-loop retry (NFR-003)
- `pytest tests/specify_cli/sync/test_body_queue.py` passes with 90%+ coverage

## Context & Constraints

- **Spec**: FR-007 (durable queue), FR-009 (survives restart), FR-010 (idempotent), NFR-002 (10K capacity), NFR-003 (per-task backoff 1s→5min)
- **Plan**: Module Responsibilities → `body_queue.py`, Key Design Decisions #4 (per-task backoff via `next_attempt_at`), #6 (idempotent enqueue via 7-field unique constraint)
- **Existing code**: `src/specify_cli/sync/queue.py` — `OfflineQueue` class (pattern reference for SQLite CRUD, schema, stats)
- **Existing schema**: `queue` table uses `event_id TEXT UNIQUE`, `data TEXT`, `timestamp INTEGER`, `retry_count INTEGER`
- **Constraint**: Same DB file as event queue (C-001). Shared `sqlite3.Connection`.
- **Constraint**: Python 3.11+, `mypy --strict`, no new dependencies

**Implementation command**: `spec-kitty implement WP02 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T006 – Add body_upload_queue SQLite Table Schema

- **Purpose**: Define the persistent storage schema for body upload tasks. The table lives alongside the existing `queue` table in the same SQLite DB file.

- **Steps**:
  1. In `src/specify_cli/sync/queue.py`, add a schema migration function that creates the body upload table:
     ```python
     _BODY_QUEUE_SCHEMA = """
     CREATE TABLE IF NOT EXISTS body_upload_queue (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         project_uuid TEXT NOT NULL,
         feature_slug TEXT NOT NULL,
         target_branch TEXT NOT NULL,
         mission_key TEXT NOT NULL,
         manifest_version TEXT NOT NULL,
         artifact_path TEXT NOT NULL,
         content_hash TEXT NOT NULL,
         hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
         content_body TEXT NOT NULL,
         size_bytes INTEGER NOT NULL,
         retry_count INTEGER NOT NULL DEFAULT 0,
         next_attempt_at REAL NOT NULL DEFAULT 0.0,
         created_at REAL NOT NULL,
         last_error TEXT,
         UNIQUE(project_uuid, feature_slug, target_branch, mission_key, manifest_version, artifact_path, content_hash)
     );
     CREATE INDEX IF NOT EXISTS idx_body_queue_next_attempt ON body_upload_queue(next_attempt_at);
     CREATE INDEX IF NOT EXISTS idx_body_queue_namespace ON body_upload_queue(project_uuid, feature_slug, target_branch);
     """
     ```
  2. Add a function `ensure_body_queue_schema(conn: sqlite3.Connection) -> None` that executes the DDL
  3. Call `ensure_body_queue_schema()` from the existing `OfflineQueue._init_db()` method so both tables are created together
  4. Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` — safe to re-run on existing DBs

- **Files**: `src/specify_cli/sync/queue.py` (modify, ~30 additional lines)
- **Parallel?**: No — T007 depends on this schema.
- **Notes**: `next_attempt_at` is a REAL (Unix timestamp with fractional seconds) for per-task backoff scheduling. `content_body` is TEXT (UTF-8 only — binary files are filtered out before enqueue).

### Subtask T007 – Create OfflineBodyUploadQueue Class

- **Purpose**: Encapsulate all body queue operations in a dedicated class, separate from the event `OfflineQueue` but sharing the same DB connection.

- **Steps**:
  1. Create `src/specify_cli/sync/body_queue.py`
  2. Define the class:
     ```python
     from __future__ import annotations
     import sqlite3
     import time
     from dataclasses import dataclass, field
     from pathlib import Path
     from typing import TYPE_CHECKING

     if TYPE_CHECKING:
         from .namespace import NamespaceRef

     MAX_BODY_QUEUE_SIZE = 10_000

     @dataclass
     class BodyUploadTask:
         """A single queued body upload task."""
         row_id: int
         project_uuid: str
         feature_slug: str
         target_branch: str
         mission_key: str
         manifest_version: str
         artifact_path: str
         content_hash: str
         hash_algorithm: str
         content_body: str
         size_bytes: int
         retry_count: int
         next_attempt_at: float
         created_at: float
         last_error: str | None

     class OfflineBodyUploadQueue:
         def __init__(self, db_path: Path | None = None) -> None:
             ...
     ```
  3. In `__init__`, resolve `db_path` using the same scope-aware logic as `OfflineQueue` (default: `~/.spec-kitty/queue.db` or scoped path)
  4. Open SQLite connection with `check_same_thread=False` (same pattern as `OfflineQueue`)
  5. Call `ensure_body_queue_schema(self._conn)` to ensure table exists

- **Files**: `src/specify_cli/sync/body_queue.py` (new, ~50 lines initially)
- **Parallel?**: No — all other subtasks build on this class.

### Subtask T008 – Implement Idempotent enqueue()

- **Purpose**: Add body upload tasks to the queue. The 7-field unique constraint prevents duplicate tasks for the same content in the same namespace (FR-010 idempotency, Design Decision #6).

- **Steps**:
  1. Add method to `OfflineBodyUploadQueue`:
     ```python
     def enqueue(
         self,
         namespace: NamespaceRef,
         artifact_path: str,
         content_hash: str,
         content_body: str,
         size_bytes: int,
         hash_algorithm: str = "sha256",
     ) -> bool:
         """Enqueue a body upload task. Returns True if new, False if duplicate."""
     ```
  2. Check queue size first: `SELECT COUNT(*) FROM body_upload_queue`. If >= `MAX_BODY_QUEUE_SIZE`, log warning and return `False`
  3. Use `INSERT OR IGNORE` with the unique constraint to achieve idempotency:
     ```sql
     INSERT OR IGNORE INTO body_upload_queue
         (project_uuid, feature_slug, target_branch, mission_key, manifest_version,
          artifact_path, content_hash, hash_algorithm, content_body, size_bytes,
          retry_count, next_attempt_at, created_at, last_error)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0.0, ?, NULL)
     ```
  4. Return `cursor.rowcount > 0` to indicate whether a new row was inserted

- **Files**: `src/specify_cli/sync/body_queue.py` (extend, ~30 lines)
- **Parallel?**: No — core CRUD operation.
- **Notes**: `INSERT OR IGNORE` silently skips on unique constraint violation — this is the desired idempotent behavior. Changed content (different hash) creates a new task because hash is part of the unique key.

### Subtask T009 – Implement drain() with Per-Task Backoff

- **Purpose**: Retrieve upload tasks that are ready for delivery (backoff expired). This is the read side of the queue, consumed by `BackgroundSyncService` in WP06.

- **Steps**:
  1. Add method:
     ```python
     def drain(self, limit: int = 100) -> list[BodyUploadTask]:
         """Retrieve tasks ready for delivery (next_attempt_at <= now)."""
     ```
  2. Query:
     ```sql
     SELECT id, project_uuid, feature_slug, target_branch, mission_key, manifest_version,
            artifact_path, content_hash, hash_algorithm, content_body, size_bytes,
            retry_count, next_attempt_at, created_at, last_error
     FROM body_upload_queue
     WHERE next_attempt_at <= ?
     ORDER BY created_at ASC
     LIMIT ?
     ```
  3. Pass `time.time()` as the current timestamp parameter
  4. Map rows to `BodyUploadTask` dataclass instances
  5. Return the list (FIFO order by `created_at`)

- **Files**: `src/specify_cli/sync/body_queue.py` (extend, ~25 lines)
- **Parallel?**: No — sequential after T008.
- **Notes**: The `WHERE next_attempt_at <= ?` filter skips tasks in backoff cooldown. Tasks with `next_attempt_at = 0.0` (never attempted) are always eligible.

### Subtask T010 – Implement mark_uploaded(), mark_failed(), update_backoff()

- **Purpose**: Complete the queue lifecycle — remove successful tasks, update failed tasks with backoff, and handle poison rows.

- **Steps**:
  1. Add `mark_uploaded(row_id: int) -> None`:
     ```sql
     DELETE FROM body_upload_queue WHERE id = ?
     ```
  2. Add `mark_already_exists(row_id: int) -> None`:
     - Same as `mark_uploaded` — remove from queue (successful no-op)
  3. Add `mark_failed_retryable(row_id: int, error: str) -> None`:
     - Calculate next backoff: `min(1.0 * (2 ** retry_count), 300.0)` seconds
     - Update:
       ```sql
       UPDATE body_upload_queue
       SET retry_count = retry_count + 1,
           next_attempt_at = ?,
           last_error = ?
       WHERE id = ?
       ```
     - Pass `time.time() + backoff_seconds` as `next_attempt_at`
  4. Add `mark_failed_permanent(row_id: int, error: str) -> None`:
     - Remove from queue (poison row, non-retryable like `namespace_not_found`)
     ```sql
     DELETE FROM body_upload_queue WHERE id = ?
     ```
  5. Add `remove_stale(max_retry_count: int = 20) -> int`:
     - Remove tasks that have exceeded max retries:
       ```sql
       DELETE FROM body_upload_queue WHERE retry_count > ?
       ```
     - Return number of rows deleted

- **Files**: `src/specify_cli/sync/body_queue.py` (extend, ~50 lines)
- **Parallel?**: No — depends on schema from T006.
- **Notes**: Backoff formula matches NFR-003: exponential starting at 1s, capped at 5 minutes. `retry_count` 0→1s, 1→2s, 2→4s, ... 8→256s, 9+→300s (cap).

### Subtask T011 – Implement Queue Stats

- **Purpose**: Provide diagnostic information about the body queue state for `diagnose.py` integration (WP07).

- **Steps**:
  1. Add a `@dataclass` for stats:
     ```python
     @dataclass
     class BodyQueueStats:
         total_count: int
         ready_count: int           # next_attempt_at <= now
         backoff_count: int         # next_attempt_at > now
         oldest_created_at: float | None
         newest_created_at: float | None
         max_retry_count: int
         retry_histogram: dict[int, int]  # retry_count -> count
     ```
  2. Add method `get_stats() -> BodyQueueStats`:
     ```sql
     SELECT COUNT(*) FROM body_upload_queue;
     SELECT COUNT(*) FROM body_upload_queue WHERE next_attempt_at <= ?;
     SELECT MIN(created_at), MAX(created_at), MAX(retry_count) FROM body_upload_queue;
     SELECT retry_count, COUNT(*) FROM body_upload_queue GROUP BY retry_count;
     ```
  3. Return populated `BodyQueueStats`

- **Files**: `src/specify_cli/sync/body_queue.py` (extend, ~35 lines)
- **Parallel?**: Yes — independent once schema exists.

### Subtask T012 – Write test_body_queue.py

- **Purpose**: Comprehensive tests for the body queue persistence layer.

- **Steps**:
  1. Create `tests/specify_cli/sync/test_body_queue.py`
  2. Use `tmp_path` fixture for isolated SQLite DB per test
  3. Test categories:
     - **Schema**: Table and indexes created on first init
     - **Enqueue**: New task returns True; duplicate returns False; capacity limit enforced
     - **Idempotent enqueue**: Same 7-field key = no duplicate; different hash = new task; different namespace = new task
     - **Drain**: Returns tasks in FIFO order; respects `next_attempt_at` filter; respects limit
     - **Mark uploaded**: Task removed from queue
     - **Mark already_exists**: Task removed from queue
     - **Mark failed retryable**: `retry_count` incremented, `next_attempt_at` set to future, `last_error` updated
     - **Mark failed permanent**: Task removed from queue
     - **Backoff calculation**: Verify exponential progression 1→2→4→8→16→32→64→128→256→300 (cap)
     - **Remove stale**: Tasks beyond max retry removed
     - **Stats**: Correct counts, histogram, age range
     - **Process restart**: Close and reopen queue; data persists
  4. Use `time.time()` mocking (`unittest.mock.patch("time.time")`) for backoff tests

- **Files**: `tests/specify_cli/sync/test_body_queue.py` (new, ~200 lines)
- **Parallel?**: No — needs all methods from T007-T011.

## Risks & Mitigations

- **Risk**: Schema migration breaks existing event queue. **Mitigation**: `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` only; never ALTER/DROP existing tables.
- **Risk**: SQLite concurrent access from background thread. **Mitigation**: `check_same_thread=False` + SQLite WAL mode (already used by OfflineQueue).
- **Risk**: Queue grows unbounded. **Mitigation**: Hard 10K capacity check in `enqueue()` + `remove_stale()` for poison rows.

## Review Guidance

- Verify the 7-field unique constraint matches plan.md Design Decision #6
- Verify backoff formula: `min(1.0 * 2^retry_count, 300.0)` matches NFR-003
- Verify `next_attempt_at` filtering in `drain()` — tasks in backoff must be skipped
- Verify `INSERT OR IGNORE` for idempotency (not `INSERT OR REPLACE` which would reset retry_count)
- Check that `mark_failed_retryable` vs `mark_failed_permanent` distinction is clear
- Run `mypy --strict src/specify_cli/sync/body_queue.py`

## Activity Log

- 2026-03-09T07:09:45Z – system – lane=planned – Prompt created.
- 2026-03-09T08:23:00Z – claude-opus – shell_pid=49905 – lane=doing – Assigned agent via workflow command
- 2026-03-09T08:25:54Z – claude-opus – shell_pid=49905 – lane=for_review – Ready for review: OfflineBodyUploadQueue with 7-field idempotent enqueue, exponential backoff drain, lifecycle methods, stats. 27 tests, all passing.
- 2026-03-09T08:34:30Z – claude-opus – shell_pid=50890 – lane=doing – Started review via workflow command
- 2026-03-09T08:36:08Z – claude-opus – shell_pid=50890 – lane=done – Review passed: Clean implementation of OfflineBodyUploadQueue. 7-field unique constraint, INSERT OR IGNORE idempotency, exponential backoff (1s->300s cap), 10K capacity limit all match spec. Schema safely integrated into OfflineQueue._init_db(). 27/27 tests passing. Only minor: unused pytest import in test file (F401). | Done override: Review approved pre-merge. Branch 047-namespace-aware-artifact-body-sync-WP02 ready for merge to 2.x.
