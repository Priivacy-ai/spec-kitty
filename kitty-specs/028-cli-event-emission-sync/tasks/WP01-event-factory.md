---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Event Factory Module"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "codex"
shell_pid: "63964"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
dependencies: []
history:
  - timestamp: "2026-02-03T18:58:09Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Event Factory Module

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-03

**Issue 1: ULID generation still not per spec**
Spec requires `ulid.new().str` for event IDs and causation IDs. The new `_generate_ulid()` wrapper still uses `str(ulid.ULID())`. Please update `_generate_ulid()` to use `ulid.new().str` (and handle compatibility if needed), and ensure both `event_id` and `generate_causation_id()` use it.

**Issue 2: Payload validation is still incomplete vs events.schema.json**
The new `_PAYLOAD_RULES` covers only a subset of schema constraints. Missing validations include:
- `WPCreated.dependencies` array items must match `^WP\d{2}$`
- `WPAssigned.retry_count` must be integer >= 0
- `FeatureCreated.created_at` and `FeatureCompleted.completed_at` must be date-time strings when present
- `FeatureCompleted.total_duration` must be string or null
- `ErrorLogged.wp_id/stack_trace/agent_id` must be string or null
- `HistoryAdded.author` should be string when present
Also the envelope fields `event_id` and `causation_id` must match the ULID pattern. Right now the envelope validation only checks length via the vendored `Event` model and misses schema patterns. Please validate the full schema (either via JSON Schema validation using `contracts/events.schema.json` or by expanding `_PAYLOAD_RULES` + envelope rules to match it exactly).


## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Create singleton EventEmitter managing Lamport clock, authentication context, and event routing
- Implement event builders for all 8 event types defined in contracts/events.schema.json
- Events validate against spec-kitty-events library schemas before emission
- Lamport clock persists across CLI restarts via `~/.spec-kitty/clock.json`
- Event emission is non-blocking (failures logged as warnings, never halt calling code)

## Context & Constraints

### Reference Documents
- **Plan**: `kitty-specs/028-cli-event-emission-sync/plan.md` - Architecture and singleton design
- **Data Model**: `kitty-specs/028-cli-event-emission-sync/data-model.md` - Entity definitions
- **Contract**: `kitty-specs/028-cli-event-emission-sync/contracts/events.schema.json` - Event schemas
- **Quickstart**: `kitty-specs/028-cli-event-emission-sync/quickstart.md` - Usage examples

### Architecture Decisions
- **Singleton pattern**: Use double-checked locking for thread-safe lazy initialization
- **Non-blocking**: All emission failures must be caught and logged, never raised
- **Offline-first**: Queue events when WebSocket unavailable or unauthenticated

### Dependencies
- **spec-kitty-events** library (Feature 003) - Import via Git dependency per ADR-11
- **AuthClient** from Feature 027 - For team_slug and authentication status
- **Existing sync module** - OfflineQueue, SyncConfig at `src/specify_cli/sync/`

---

## Subtasks & Detailed Guidance

### Subtask T001 - LamportClock Class with Persistence

- **Purpose**: Implement causal ordering counter with JSON persistence for cross-session consistency
- **Steps**:
  1. Create `src/specify_cli/sync/clock.py`
  2. Implement LamportClock dataclass with `value: int` and `node_id: str`
  3. Implement `tick()` method: increment value, persist, return new value
  4. Implement `receive(remote_clock: int)` method: update value to `max(local, remote) + 1`
  5. Implement `load()` class method: read from `~/.spec-kitty/clock.json`
  6. Implement `save()` method: atomic write (temp file + rename)
- **Files**: `src/specify_cli/sync/clock.py`
- **Parallel?**: No (foundation for other subtasks)
- **Notes**:
  - Use `pathlib.Path.home() / ".spec-kitty" / "clock.json"` for storage path
  - Handle missing file gracefully (initialize with value=0)
  - JSON format: `{"value": 42, "node_id": "hash123", "updated_at": "2026-02-03T..."}`

### Subtask T002 - EventEmitter Singleton Class

- **Purpose**: Create the core class managing event creation and dispatch
- **Steps**:
  1. Create `src/specify_cli/sync/emitter.py`
  2. Define EventEmitter dataclass with: clock, auth, config, queue, ws_client (optional)
  3. Implement `__init__` to initialize dependencies (lazy load AuthClient, SyncConfig)
  4. Implement `emit()` method as the central dispatch point
  5. Implement `get_connection_status()` returning ConnectionStatus enum
  6. Implement `generate_causation_id()` for batch event correlation
- **Files**: `src/specify_cli/sync/emitter.py`
- **Parallel?**: No (required by T003-T007)
- **Notes**:
  - Do NOT make EventEmitter itself a singleton; use get_emitter() pattern instead
  - ConnectionStatus enum: Connected, Reconnecting, Offline, OfflineBatchMode

### Subtask T003 - Module Exports and Convenience Functions

- **Purpose**: Provide public API via `get_emitter()` accessor and type-specific emit helpers
- **Steps**:
  1. Create/update `src/specify_cli/sync/events.py`
  2. Implement `get_emitter()` with thread-safe lazy initialization
  3. Add convenience functions delegating to singleton:
     - `emit_wp_status_changed(wp_id, previous_status, new_status, ...)`
     - `emit_wp_created(wp_id, title, dependencies, feature_slug, ...)`
     - `emit_wp_assigned(wp_id, agent_id, phase, ...)`
     - `emit_feature_created(feature_slug, feature_number, target_branch, wp_count, ...)`
     - `emit_feature_completed(feature_slug, total_wps, ...)`
     - `emit_history_added(wp_id, entry_type, entry_content, ...)`
     - `emit_error_logged(wp_id, error_type, error_message, ...)`
     - `emit_dependency_resolved(wp_id, dependency_wp_id, resolution_type, ...)`
  4. Update `src/specify_cli/sync/__init__.py` to export public API
- **Files**: `src/specify_cli/sync/events.py`, `src/specify_cli/sync/__init__.py`
- **Parallel?**: Yes (after T001, T002 exist)
- **Notes**:
  - Use TYPE_CHECKING import guard to avoid circular imports
  - All convenience functions should have type hints

### Subtask T004 - Node ID Generation

- **Purpose**: Generate stable machine identifier for event provenance
- **Steps**:
  1. Add `generate_node_id()` function to clock.py or a dedicated module
  2. Hash hostname + username for stability across restarts
  3. Return first 12 characters of SHA256 hash
- **Files**: `src/specify_cli/sync/clock.py` (or new `src/specify_cli/sync/identity.py`)
- **Parallel?**: Yes (independent utility)
- **Notes**:
  - Use `socket.gethostname()` and `getpass.getuser()`
  - Hash to anonymize while keeping stability
  - Example: `"alice-laptop"` + `"alice"` -> `hashlib.sha256(...).hexdigest()[:12]`

### Subtask T005 - Event Builders for All 8 Types

- **Purpose**: Implement builder methods creating fully-formed event dicts
- **Steps**:
  1. Add builder methods to EventEmitter class:
     - `emit_wp_status_changed()` - FR-008
     - `emit_wp_created()` - FR-009
     - `emit_wp_assigned()` - FR-010
     - `emit_feature_created()` - FR-011
     - `emit_feature_completed()` - FR-012
     - `emit_history_added()` - FR-013
     - `emit_error_logged()` - FR-014
     - `emit_dependency_resolved()` - FR-015
  2. Each builder should:
     - Generate ULID event_id via python-ulid
     - Tick Lamport clock
     - Get node_id from clock
     - Get team_slug from AuthClient
     - Build payload dict with event-specific fields
     - Call internal _emit() method
- **Files**: `src/specify_cli/sync/emitter.py`
- **Parallel?**: No (depends on T002 structure)
- **Notes**:
  - Payload structures defined in data-model.md
  - Use `ulid.new().str` for event_id generation
  - timestamp should be `datetime.now(timezone.utc).isoformat()`

### Subtask T006 - Event Routing Logic

- **Purpose**: Implement queue vs WebSocket decision logic in emit_event()
- **Steps**:
  1. Implement `_emit(event: dict)` method in EventEmitter
  2. Check if authenticated via `self.auth.is_authenticated()`
  3. Check if WebSocket connected via `self.ws_client.connected` or `self.ws_client.get_status() == ConnectionStatus.CONNECTED` (if ws_client exists)
  4. If authenticated and connected: send via WebSocket
  5. If authenticated but disconnected: queue to OfflineQueue
  6. If not authenticated: queue locally (sync after login)
  7. Wrap entire logic in try/except to ensure non-blocking
  8. Log failures via `console.print("[yellow]Warning: ...[/yellow]")`
- **Files**: `src/specify_cli/sync/emitter.py`
- **Parallel?**: No (integrates T001-T005)
- **Notes**:
  - Never raise exceptions from _emit()
  - Use Rich console for warning output
  - Return success/failure status for callers that want to check

### Subtask T007 - Schema Validation

- **Purpose**: Validate events against spec-kitty-events schemas before emission
- **Steps**:
  1. Import event models from spec-kitty-events library
  2. Add `_validate_event(event: dict)` method to EventEmitter
  3. Validate using Pydantic models or JSON Schema
  4. On validation failure: log warning, discard event (don't queue invalid events)
  5. Call validation in _emit() before routing
- **Files**: `src/specify_cli/sync/emitter.py`
- **Parallel?**: No (final integration step)
- **Notes**:
  - spec-kitty-events provides Pydantic models for validation
  - Invalid events should be logged with details for debugging
  - Don't block on validation failures - just skip the invalid event

---

## Test Strategy

Tests are covered in WP07, but during implementation:
- Run `python -c "from specify_cli.sync.events import get_emitter; print(get_emitter())"` to verify imports
- Manually test clock persistence: emit event, restart Python, verify clock value incremented
- Use `pytest tests/sync/test_events.py -v` once tests exist

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| spec-kitty-events import failures | Verify Git dependency is pinned in pyproject.toml |
| Circular imports | Use TYPE_CHECKING guards, lazy imports |
| Clock file corruption | Use atomic writes (temp file + rename) |
| WebSocketClient not initialized | Handle None ws_client gracefully |

---

## Review Guidance

- Verify singleton pattern uses double-checked locking
- Verify all 8 event types have builders with correct payload fields
- Verify Lamport clock persists correctly (check clock.json after emit)
- Verify non-blocking behavior (intentionally cause failures, verify no exceptions bubble up)
- Verify team_slug is included in all events

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-03T18:58:09Z - system - lane=planned - Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-02-03T19:29:53Z – claude-opus – shell_pid=64523 – lane=doing – Started implementation via workflow command
- 2026-02-03T20:11:43Z – claude-opus – shell_pid=64523 – lane=planned – Moved to planned
- 2026-02-03T20:14:10Z – codex – shell_pid=63964 – lane=doing – Started implementation via workflow command
