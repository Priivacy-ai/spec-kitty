---
work_package_id: "WP04"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "SyncRuntime Lazy Singleton"
phase: "Phase 2 - Runtime Bootstrap"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-02-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – SyncRuntime Lazy Singleton

## Implementation Command

```bash
spec-kitty implement WP04 --base WP02
```

---

## Objectives & Success Criteria

**Goal**: Create SyncRuntime with lazy startup on first `get_emitter()` call.

**Success Criteria**:
- [ ] `get_emitter()` auto-starts BackgroundSyncService
- [ ] Runtime starts only once (idempotent)
- [ ] WebSocket connects only if authenticated
- [ ] Process exit triggers graceful shutdown
- [ ] `sync.auto_start: false` disables auto-start
- [ ] All tests pass

---

## Context & Constraints

**Target Branch**: 2.x

**Supporting Documents**:
- [plan.md](../plan.md) - Architecture decision AD-1 (Lazy Singleton)
- [data-model.md](../data-model.md) - SyncRuntime entity

**Prerequisites**: WP02 (emitter identity injection) must be complete.

**Key Constraints**:
- Zero startup overhead for non-event commands
- Must be idempotent (safe to call get_emitter multiple times)
- Graceful shutdown on process exit

---

## Subtasks & Detailed Guidance

### Subtask T016 – Create SyncRuntime dataclass

**Purpose**: Define the runtime state container.

**Steps**:
1. Create new file `src/specify_cli/sync/runtime.py`
2. Define `SyncRuntime` dataclass:
   ```python
   from dataclasses import dataclass, field
   from typing import TYPE_CHECKING
   
   if TYPE_CHECKING:
       from specify_cli.sync.background import BackgroundSyncService
       from specify_cli.sync.client import WebSocketClient
       from specify_cli.sync.emitter import EventEmitter
   
   @dataclass
   class SyncRuntime:
       """Background sync runtime managing WebSocket and queue."""
       
       background_service: "BackgroundSyncService | None" = field(default=None, repr=False)
       ws_client: "WebSocketClient | None" = field(default=None, repr=False)
       emitter: "EventEmitter | None" = field(default=None, repr=False)
       started: bool = False
       
       def start(self) -> None:
           """Start background services (idempotent)."""
           pass  # Implemented in T018
       
       def attach_emitter(self, emitter: "EventEmitter") -> None:
           """Attach emitter so WS client can be injected."""
           self.emitter = emitter
           if self.ws_client is not None:
               self.emitter.ws_client = self.ws_client
       
       def stop(self) -> None:
           """Stop background services."""
           pass  # Implemented in T020
   ```

**Files**:
- `src/specify_cli/sync/runtime.py` (NEW, ~40 lines initial)

---

### Subtask T017 – Implement lazy singleton get_runtime()

**Purpose**: Provide module-level singleton access to runtime.

**Steps**:
1. Add module-level singleton in `sync/runtime.py`:
   ```python
   _runtime: SyncRuntime | None = None
   
   def get_runtime() -> SyncRuntime:
       """Get or create the singleton SyncRuntime instance."""
       global _runtime
       if _runtime is None:
           _runtime = SyncRuntime()
           _runtime.start()
       return _runtime
   ```

2. Wire into `get_emitter()`:
   ```python
   # In sync/events.py
   def get_emitter() -> EventEmitter:
       global _emitter
       if _emitter is None:
           # Start runtime before creating emitter
           from specify_cli.sync.runtime import get_runtime
           runtime = get_runtime()  # Auto-starts
           
           _emitter = EventEmitter()
           runtime.attach_emitter(_emitter)
       return _emitter
   ```

**Files**:
- `src/specify_cli/sync/runtime.py` (append, ~15 lines)
- `src/specify_cli/sync/events.py` (modify, ~5 lines)

**Notes**:
- `get_runtime()` is idempotent - safe to call multiple times
- Runtime starts on first access, not at module import

---

### Subtask T018 – Start BackgroundSyncService unconditionally

**Purpose**: Always start the background service for queue processing.

**Steps**:
1. Implement `SyncRuntime.start()`:
   ```python
   def start(self) -> None:
       """Start background services (idempotent)."""
       if self.started:
           return
       
       # Check config for opt-out (project-level)
       if not _auto_start_enabled():
           logger.info("Sync auto-start disabled via config")
           return
       
       # Start background service (use existing singleton)
       from specify_cli.sync.background import get_sync_service
       self.background_service = get_sync_service()
       
       # WebSocket connection handled in T019
       
       self.started = True
       logger.debug("SyncRuntime started")
   ```

2. Add `_auto_start_enabled()` helper to read `.kittify/config.yaml`:
   - Default to `True` if config missing or invalid
   - Read `sync.auto_start` if present

**Files**:
- `src/specify_cli/sync/runtime.py` (modify start(), ~25 lines)

---

### Subtask T019 – Connect WebSocketClient only if authenticated

**Purpose**: Attempt WebSocket connection only when user is logged in.

**Steps**:
1. Extend `SyncRuntime.start()` to check authentication:
   ```python
   def start(self) -> None:
       # ... existing code from T018 ...
       
       # Connect WebSocket if authenticated
       from specify_cli.sync.auth import AuthClient
       from specify_cli.sync.config import SyncConfig
       auth = AuthClient()
       config = SyncConfig()
       
       if auth.is_authenticated():
           try:
               from specify_cli.sync.client import WebSocketClient
               self.ws_client = WebSocketClient(
                   server_url=config.get_server_url(),
                   auth_client=auth,
               )
               # Non-blocking connect attempt
               import asyncio
               loop = asyncio.get_event_loop()
               if loop.is_running():
                   asyncio.ensure_future(self.ws_client.connect())
               else:
                   loop.run_until_complete(self.ws_client.connect())
               
               # Wire WebSocket to emitter (BackgroundSyncService does not own WS)
               if self.emitter is not None:
                   self.emitter.ws_client = self.ws_client
           except Exception as e:
               logger.warning(f"WebSocket connection failed: {e}")
               logger.info("Events will be queued for batch sync")
       else:
           logger.info("Not authenticated; events queued locally")
           logger.info("Run 'spec-kitty auth login' to enable real-time sync")
       
       self.started = True
   ```

**Files**:
- `src/specify_cli/sync/runtime.py` (extend start(), ~30 lines)

**Notes**:
- WebSocket failure is not fatal - queue still works
- Log helpful message when not authenticated

---

### Subtask T020 – Add atexit handler for graceful shutdown

**Purpose**: Clean up background services on process exit.

**Steps**:
1. Add `stop()` method:
   ```python
   def stop(self) -> None:
       """Stop background services."""
       if not self.started:
           return
       
       if self.ws_client:
           try:
               import asyncio
               loop = asyncio.get_event_loop()
               if loop.is_running():
                   asyncio.ensure_future(self.ws_client.disconnect())
               else:
                   loop.run_until_complete(self.ws_client.disconnect())
           except Exception:
               pass
           self.ws_client = None
       
       if self.background_service:
           self.background_service.stop()
           self.background_service = None
       
       self.started = False
       logger.debug("SyncRuntime stopped")
   ```

2. Register atexit handler:
   - Note: `get_sync_service()` already registers its own atexit; this handler
     ensures WS disconnect and is safe to call even if background_service stops itself.
   ```python
   import atexit
   
   def _shutdown_runtime() -> None:
       global _runtime
       if _runtime is not None:
           _runtime.stop()
   
   atexit.register(_shutdown_runtime)
   ```

**Files**:
- `src/specify_cli/sync/runtime.py` (add stop() and atexit, ~30 lines)

---

### Subtask T021 – Write runtime tests

**Purpose**: Verify runtime lifecycle and singleton behavior.

**Steps**:
1. Create `tests/sync/test_runtime.py`
2. Add tests:
   ```python
   class TestSyncRuntime:
       def test_get_runtime_singleton(self):
           """get_runtime returns same instance."""
           r1 = get_runtime()
           r2 = get_runtime()
           assert r1 is r2
       
       def test_start_idempotent(self):
           """Multiple start() calls are safe."""
           runtime = SyncRuntime()
           runtime.start()
           runtime.start()  # Should not raise
       
       def test_auto_start_disabled(self, monkeypatch):
           """Respects sync.auto_start: false."""
           import specify_cli.sync.runtime as runtime_module
           monkeypatch.setattr(runtime_module, "_auto_start_enabled", lambda: False)
           runtime = SyncRuntime()
           runtime.start()
           assert not runtime.started
       
       def test_unauthenticated_no_websocket(self, mock_auth_unauthenticated):
           """No WebSocket when not authenticated."""
           runtime = SyncRuntime()
           runtime.start()
           assert runtime.ws_client is None
           assert runtime.background_service is not None  # Queue still works
   ```

**Files**:
- `tests/sync/test_runtime.py` (NEW, ~80 lines)

**Test Commands**:
```bash
pytest tests/sync/test_runtime.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Runtime not stopping cleanly | atexit handler + explicit stop() API |
| Startup latency | Keep startup async-light; defer WebSocket |
| Asyncio event loop issues | Handle both running and not-running loop cases |

---

## Review Guidance

**Reviewers should verify**:
1. Singleton pattern is correct (module-level `_runtime`)
2. start() is truly idempotent
3. Async code handles both loop states
4. atexit handler registered

---

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
