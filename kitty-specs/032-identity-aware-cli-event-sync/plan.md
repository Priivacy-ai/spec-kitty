# Implementation Plan: Identity-Aware CLI Event Sync

**Branch**: `032-identity-aware-cli-event-sync` | **Date**: 2026-02-07 | **Spec**: [spec.md](./spec.md)
**Target Branch**: 2.x
**Input**: Feature specification from `/kitty-specs/032-identity-aware-cli-event-sync/spec.md`

## Summary

Add project identity (`project_uuid`, `project_slug`, `node_id`) to all CLI-emitted events and enable automatic background sync on CLI startup. This enables the SaaS to correctly attribute events to specific projects and removes the friction of manual sync startup.

**Technical Approach**:
- **Lazy Singleton** pattern for runtime bootstrap via `get_emitter()`
- **Graceful Backfill** for config schema (auto-generate missing identity fields)
- **Atomic writes** for config.yaml (temp file + rename)
- **Read-only fallback** to in-memory identity when repo is not writable

## Technical Context

**Language/Version**: Python 3.11+ (per constitution)
**Primary Dependencies**: typer, rich, ruamel.yaml, websockets, ulid (existing)
**Storage**: `.kittify/config.yaml` (YAML frontmatter), offline queue (JSONL)
**Testing**: pytest with 90%+ coverage, mypy --strict
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform CLI)
**Project Type**: Single project (CLI tool)
**Performance Goals**: CLI operations < 2 seconds, sync runtime startup < 100ms
**Constraints**: Must work when unauthenticated (graceful degradation to queue-only)
**Scale/Scope**: Supports 100+ work packages, thousands of events per project

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ | ✅ PASS | All new modules use Python 3.11+ features |
| mypy --strict | ✅ PASS | Type annotations required for all new code |
| 90%+ test coverage | ✅ PASS | Unit tests for identity, integration tests for sync |
| CLI < 2 seconds | ✅ PASS | Lazy singleton avoids startup overhead |
| Target 2.x branch | ✅ PASS | All changes target 2.x, no 1.x compatibility needed |
| spec-kitty-events integration | ✅ PASS | Events lib updated separately (out of scope) |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/032-identity-aware-cli-event-sync/
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal - clear requirements)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (getting started guide)
├── contracts/           # Phase 1 output (event schema updates)
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (on 2.x branch)

```
src/specify_cli/
├── sync/
│   ├── __init__.py           # Exports get_emitter, SyncRuntime
│   ├── project_identity.py   # NEW: ProjectIdentity class, generation, persistence
│   ├── runtime.py            # NEW: SyncRuntime bootstrap, lazy singleton
│   ├── emitter.py            # MODIFY: Inject identity, lazy-start runtime
│   ├── auth.py               # MODIFY: Add get_team_slug(), store on login
│   ├── client.py             # (existing WebSocketClient)
│   ├── queue.py              # (existing OfflineQueue)
│   ├── clock.py              # (existing LamportClock)
│   ├── config.py             # (existing SyncConfig)
│   └── background.py         # (existing BackgroundSyncService)
├── cli/
│   └── commands/
│       ├── implement.py      # MODIFY: Fix duplicate emissions (on 2.x)
│       └── accept.py         # MODIFY: Fix duplicate emissions (on 2.x)
└── ...

tests/
├── sync/
│   ├── test_project_identity.py   # NEW: Unit tests for identity generation
│   ├── test_runtime.py            # NEW: Tests for lazy singleton
│   ├── test_event_emission.py     # MODIFY: Add identity verification
│   └── test_auth.py               # MODIFY: Test get_team_slug()
└── integration/
    └── test_sync_e2e.py           # NEW: End-to-end sync tests
```

**Structure Decision**: Single project structure, all sync code in `src/specify_cli/sync/`.

## Architectural Decisions

### AD-1: Lazy Singleton for Runtime Bootstrap

**Decision**: Start `BackgroundSyncService` lazily on first `get_emitter()` call.

**Rationale**:
- Zero overhead for non-event commands (most planning commands)
- Centralized startup logic in one place
- Idempotent (safe to call get_emitter() multiple times)

**Implementation**:
```python
# sync/runtime.py
_runtime: SyncRuntime | None = None

def get_runtime() -> SyncRuntime:
    global _runtime
    if _runtime is None:
        _runtime = SyncRuntime()
        _runtime.start()  # Idempotent
    return _runtime
```

### AD-2: Graceful Backfill for Config Schema

**Decision**: Auto-generate missing identity fields on first access.

**Rationale**:
- Seamless UX for existing projects
- No migration required
- Handles read-only repos gracefully

**Implementation**:
```python
# sync/project_identity.py
def ensure_identity(config_path: Path) -> ProjectIdentity:
    """Load or generate project identity. Atomic write if generating."""
    identity = load_identity(config_path)
    if identity.is_complete:
        return identity
    
    # Generate missing fields
    identity = identity.with_defaults()
    
    # Atomic persist (if writable)
    if is_writable(config_path):
        atomic_write(config_path, identity)
    else:
        logger.warning("Config not writable; using in-memory identity")
    
    return identity
```

### AD-3: Identity Injection in Event Envelope

**Decision**: Inject `project_uuid` and `project_slug` in `EventEmitter._emit()`.

**Rationale**:
- Single point of injection (all emit_* methods go through _emit)
- Validation before WebSocket send (queue-only if missing)
- Consistent across all event types

**Implementation**:
```python
# In EventEmitter._emit()
identity = get_project_identity()
event["project_uuid"] = str(identity.project_uuid)
event["project_slug"] = identity.project_slug  # Optional

# Validation: if project_uuid missing, queue only
if not event.get("project_uuid"):
    logger.warning("Event missing project_uuid; queued locally only")
    self.queue.queue_event(event)
    return event  # Don't send via WebSocket
```

## Parallel Work Analysis

### Dependency Graph

```
WP01: ProjectIdentity module (foundation)
  ↓
WP02: Emitter identity injection (depends on WP01)
WP03: AuthClient get_team_slug() (parallel with WP02)
  ↓
WP04: SyncRuntime lazy singleton (depends on WP02)
  ↓
WP05: Fix duplicate emissions (depends on WP04, needs 2.x branch)
  ↓
WP06: Integration tests (depends on all above)
```

### Work Distribution

- **Sequential (foundation)**: WP01 must complete before WP02/WP04
- **Parallel streams**: WP02 and WP03 can run simultaneously
- **Sequential (integration)**: WP05 and WP06 depend on prior work

### Coordination Points

- **After WP01**: Identity API frozen, others can depend on it
- **After WP04**: Full runtime available for integration testing
- **Final**: WP06 validates entire feature

## Files Modified (Summary)

| File | Action | Description |
|------|--------|-------------|
| `sync/project_identity.py` | NEW | ProjectIdentity class, generation, atomic persistence |
| `sync/runtime.py` | NEW | SyncRuntime, lazy singleton, startup logic |
| `sync/emitter.py` | MODIFY | Inject identity, lazy-start runtime, validation |
| `sync/auth.py` | MODIFY | Add get_team_slug(), store team_slug on login |
| `sync/events.py` | MODIFY | Update get_emitter() for lazy singleton |
| `cli/commands/implement.py` | MODIFY | Fix duplicate WPStatusChanged emission |
| `cli/commands/accept.py` | MODIFY | Fix duplicate WPStatusChanged emission |
| `tests/sync/test_project_identity.py` | NEW | Unit tests for identity |
| `tests/sync/test_runtime.py` | NEW | Tests for lazy singleton |
| `tests/sync/test_event_emission.py` | MODIFY | Add identity verification |
| `tests/integration/test_sync_e2e.py` | NEW | End-to-end sync tests |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Config.yaml corruption | Atomic writes (temp + rename), validate before persist |
| Read-only repos | Fallback to in-memory identity, clear warning |
| Race conditions | First-write-wins for UUID, Lamport clock for ordering |
| Network failures | Existing BackgroundSyncService handles retries |
| Duplicate emissions | Consolidate to single emission point per command |
