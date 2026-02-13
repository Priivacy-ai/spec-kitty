---
work_package_id: "WP06"
subtasks:
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "Background Sync Service"
phase: "Phase 3 - Infrastructure"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP05"]
history:
  - timestamp: "2026-02-03T18:58:09Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Background Sync Service

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Background service auto-flushes queue periodically (default 5 minutes)
- Exponential backoff on repeated failures (500ms -> 30s)
- Graceful shutdown when CLI session ends
- `spec-kitty sync now` triggers immediate sync
- `spec-kitty sync status` shows queue size, connection state, last sync

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/028-cli-event-emission-sync/spec.md` - User Story 7
- **Plan**: `kitty-specs/028-cli-event-emission-sync/plan.md` - Background sync design
- **Research**: `kitty-specs/028-cli-event-emission-sync/research.md` - Sync strategy decisions

### Functional Requirements
- FR-031: System MUST provide background sync capability
- FR-032: Background sync MUST use exponential backoff on failures
- FR-033: Background sync MUST respect rate limits (1000 events/batch, 1 batch/5 sec)
- FR-034: Background sync MUST authenticate using refresh token flow
- FR-035: Background sync MUST stop gracefully when CLI session ends
- FR-036: System MUST track connection status
- FR-037: Connection status MUST be surfaceable via `spec-kitty sync status`

### Dependencies
- WP05 (Orchestrate) establishes patterns for long-running operations
- Existing `batch_sync()` function in `src/specify_cli/sync/batch.py`
- AuthClient from Feature 027 for token refresh

---

## Subtasks & Detailed Guidance

### Subtask T029 - BackgroundSyncService Class

- **Purpose**: Create the service class managing background sync operations
- **Steps**:
  1. Create `src/specify_cli/sync/background.py`
  2. Define BackgroundSyncService class:
     ```python
     import threading
     from dataclasses import dataclass
     from datetime import datetime, timezone
     from typing import Optional

     @dataclass
     class BackgroundSyncService:
         queue: OfflineQueue
         auth: AuthClient
         config: SyncConfig
         _timer: Optional[threading.Timer] = None
         _running: bool = False
         _backoff_seconds: float = 0.5
         _last_sync: Optional[datetime] = None
         _consecutive_failures: int = 0

         def start(self) -> None:
             """Start the background sync service."""
             self._running = True
             self._schedule_next_sync()

         def stop(self) -> None:
             """Stop the background sync service gracefully."""
             self._running = False
             if self._timer:
                 self._timer.cancel()

         def sync_now(self) -> BatchSyncResult:
             """Trigger immediate sync."""
             return self._perform_sync()

         def _schedule_next_sync(self) -> None:
             """Schedule next sync based on interval or backoff."""
             ...

         def _perform_sync(self) -> BatchSyncResult:
             """Execute batch sync."""
             ...
     ```
  3. Export from `__init__.py`
- **Files**: `src/specify_cli/sync/background.py`
- **Parallel?**: No (foundation for T030-T035)
- **Notes**:
  - Use threading.Timer for periodic execution
  - Consider using daemon thread so it doesn't block CLI exit

### Subtask T030 - Periodic Sync Timer

- **Purpose**: Implement periodic sync with configurable interval
- **Steps**:
  1. Add `sync_interval_seconds` to BackgroundSyncService (default 300 = 5 min)
  2. Implement `_schedule_next_sync()`:
     ```python
     def _schedule_next_sync(self) -> None:
         if not self._running:
             return
         interval = self.sync_interval_seconds
         if self._consecutive_failures > 0:
             interval = min(self._backoff_seconds, 30)  # backoff capped at 30s
         self._timer = threading.Timer(interval, self._on_timer)
         self._timer.daemon = True  # Don't block exit
         self._timer.start()

     def _on_timer(self) -> None:
         if self._running and self.queue.size() > 0:
             self._perform_sync()
         self._schedule_next_sync()
     ```
  3. Allow configuration via SyncConfig or environment variable
- **Files**: `src/specify_cli/sync/background.py`
- **Parallel?**: No (timer implementation)
- **Notes**:
  - Only sync if queue is non-empty
  - Reschedule after each sync attempt

### Subtask T031 - Exponential Backoff

- **Purpose**: Implement exponential backoff on repeated failures
- **Steps**:
  1. Track consecutive failures: `_consecutive_failures`
  2. On success: reset backoff to 0.5s, reset failure count
  3. On failure: double backoff (max 30s), increment failure count
  4. Implementation:
     ```python
     def _perform_sync(self) -> BatchSyncResult:
         try:
             result = batch_sync(
                 queue=self.queue,
                 auth_token=self.auth.get_access_token(),
                 server_url=self.config.get_server_url(),
             )
             self._consecutive_failures = 0
             self._backoff_seconds = 0.5
             self._last_sync = datetime.now(timezone.utc)
             return result
         except Exception as e:
             self._consecutive_failures += 1
             self._backoff_seconds = min(self._backoff_seconds * 2, 30)
             logger.warning(f"Sync failed (attempt {self._consecutive_failures}): {e}")
             return BatchSyncResult(synced_count=0, error_count=1, errors=[str(e)])
     ```
- **Files**: `src/specify_cli/sync/background.py`
- **Parallel?**: No (error handling)
- **Notes**:
  - Backoff sequence: 0.5s, 1s, 2s, 4s, 8s, 16s, 30s (capped)
  - Log warnings on failures for visibility

### Subtask T032 - Graceful Shutdown

- **Purpose**: Ensure service stops cleanly when CLI session ends
- **Steps**:
  1. Register shutdown handler via `atexit`:
     ```python
     import atexit

     _service: Optional[BackgroundSyncService] = None

     def get_sync_service() -> BackgroundSyncService:
         global _service
         if _service is None:
             _service = BackgroundSyncService(...)
             atexit.register(_service.stop)
         return _service
     ```
  2. In `stop()`, cancel timer and optionally flush queue:
     ```python
     def stop(self) -> None:
         self._running = False
         if self._timer:
             self._timer.cancel()
             self._timer = None
         # Optionally attempt final sync
         if self.queue.size() > 0:
             try:
                 self._perform_sync()
             except Exception:
                 pass  # Best effort
     ```
  3. Use daemon threads to avoid blocking
- **Files**: `src/specify_cli/sync/background.py`
- **Parallel?**: No (shutdown handling)
- **Notes**:
  - Daemon threads exit automatically when main thread exits
  - Final sync attempt is best-effort, don't block shutdown

### Subtask T033 - Batch Sync Integration

- **Purpose**: Wire BackgroundSyncService to existing batch_sync function
- **Steps**:
  1. Import `batch_sync` from `specify_cli.sync.batch`
  2. In `_perform_sync()`, call batch_sync with correct parameters:
     ```python
     from .batch import batch_sync, BatchSyncResult

     def _perform_sync(self) -> BatchSyncResult:
         if not self.auth.is_authenticated():
             logger.warning("Not authenticated, skipping sync")
             return BatchSyncResult(synced_count=0, error_count=0)

         result = batch_sync(
             queue=self.queue,
             auth_token=self.auth.get_access_token(),
             server_url=self.config.get_server_url(),
             max_batch_size=1000,
         )
         return result
     ```
  3. Respect rate limits (handled by batch_sync)
  4. Handle 401 errors specially (token expired):
     ```python
     except HTTPStatusError as e:
         if e.response.status_code == 401:
             # Try token refresh
             self.auth.refresh_tokens()
             # Retry once
             ...
     ```
- **Files**: `src/specify_cli/sync/background.py`
- **Parallel?**: No (integration)
- **Notes**:
  - batch_sync likely handles chunking (1000 events per batch)
  - Token refresh is handled by AuthClient from Feature 027

### Subtask T034 - `spec-kitty sync now` Command

- **Purpose**: Add CLI command for immediate sync
- **Steps**:
  1. Create or update `src/specify_cli/cli/commands/sync.py`
  2. Add `sync now` subcommand:
     ```python
     import typer
     from specify_cli.sync.background import get_sync_service

     sync_app = typer.Typer()

     @sync_app.command("now")
     def sync_now():
         """Trigger immediate sync of queued events."""
         service = get_sync_service()
         console.print("Syncing queued events...")
         result = service.sync_now()
         console.print(f"Synced: {result.synced_count}, Errors: {result.error_count}")
         if result.errors:
             for err in result.errors:
                 console.print(f"  [red]Error:[/red] {err}")
     ```
  3. Register with main CLI app
- **Files**: `src/specify_cli/cli/commands/sync.py`, `src/specify_cli/cli/commands/__init__.py`, `src/specify_cli/__init__.py`
- **Parallel?**: Yes (independent from T035)
- **Notes**:
  - Should work even if background service isn't running
  - Show progress for large queues

### Subtask T035 - `spec-kitty sync status` Command

- **Purpose**: Add CLI command to show sync status
- **Steps**:
  1. In same file `src/specify_cli/cli/commands/sync.py`
  2. Add `sync status` subcommand:
     ```python
     @sync_app.command("status")
     def sync_status():
         """Show sync queue status and connection state."""
         from specify_cli.sync.events import get_emitter
         from specify_cli.sync.background import get_sync_service

         emitter = get_emitter()
         service = get_sync_service()

         # Queue info
         queue_size = emitter.queue.size()
         console.print(f"Queue size: {queue_size} events")

         # Connection status
         status = emitter.get_connection_status()
         status_color = "green" if status == "Connected" else "yellow"
         console.print(f"Connection: [{status_color}]{status}[/{status_color}]")

         # Last sync
         if service._last_sync:
             console.print(f"Last sync: {service._last_sync.isoformat()}")
         else:
             console.print("Last sync: Never")

         # Auth status
         auth_status = "Authenticated" if emitter.auth.is_authenticated() else "Not authenticated"
         console.print(f"Auth: {auth_status}")
     ```
  3. Register with main CLI app
- **Files**: `src/specify_cli/cli/commands/sync.py`, `src/specify_cli/cli/commands/__init__.py`, `src/specify_cli/__init__.py`
- **Parallel?**: Yes (independent from T034)
- **Notes**:
  - Show all relevant status in one view
  - Color-code connection status for quick scanning

---

## Test Strategy

Tests are covered in WP07, but verify manually:
```bash
# Check status
spec-kitty sync status

# Trigger sync
spec-kitty sync now

# Test background service (observe logs)
# Run a long operation and watch for periodic sync attempts
```

Verify:
1. `sync status` shows correct queue size
2. `sync now` actually syncs events (check queue size before/after)
3. Background service respects interval (add logging to verify)
4. Shutdown is graceful (no hanging on Ctrl+C)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Thread safety issues | Use locks for queue access |
| Resource leaks | Use daemon threads, register atexit |
| Auth token expiry | Integrate with AuthClient refresh flow |
| Rate limiting | Respect max batch size and interval |

---

## Review Guidance

- Verify exponential backoff sequence is correct
- Verify daemon threads don't block CLI exit
- Verify sync status command shows useful information
- Test sync now when queue is empty vs full
- Verify atexit cleanup runs on Ctrl+C

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-03T18:58:09Z - system - lane=planned - Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP06 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
