---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Emitter Identity Injection"
phase: "Phase 1 - Core Implementation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Emitter Identity Injection

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

**Goal**: Inject `project_uuid` and `project_slug` into every event envelope in `EventEmitter._emit()`.

**Success Criteria**:
- [ ] All emitted events contain `project_uuid` field
- [ ] Events missing identity are queued locally (not sent via WebSocket)
- [ ] Warning logged when identity is missing
- [ ] Existing tests updated to verify identity presence
- [ ] mypy --strict passes on emitter.py

---

## Context & Constraints

**Target Branch**: 2.x

**Supporting Documents**:
- [plan.md](../plan.md) - Architecture decision AD-3 (Identity Injection)
- [data-model.md](../data-model.md) - EventEnvelope schema
- [contracts/event-envelope.md](../contracts/event-envelope.md) - Updated schema

**Prerequisite**: WP01 (ProjectIdentity module) must be complete.

**Key Constraints**:
- Single injection point in `_emit()` (not in each emit_* method)
- Identity resolution happens once per emitter lifetime
- Must not break existing event flow
- `project_uuid` is required for WebSocket send (queue-only if missing)

---

## Subtasks & Detailed Guidance

### Subtask T007 – Import ProjectIdentity into emitter

**Purpose**: Make identity functions available in emitter module.

**Steps**:
1. Open `src/specify_cli/sync/emitter.py`
2. Add import at top (after existing imports):
   ```python
   from specify_cli.sync.project_identity import ensure_identity, ProjectIdentity
   ```
3. If circular import issues, use lazy import pattern:
   ```python
   def _get_project_identity() -> ProjectIdentity:
       from specify_cli.sync.project_identity import ensure_identity, ProjectIdentity
       from specify_cli.tasks_support import find_repo_root
       try:
           repo_root = find_repo_root()
       except Exception:
           # Non-project context; return empty identity to trigger queue-only
           return ProjectIdentity()
       return ensure_identity(repo_root)
   ```

**Files**:
- `src/specify_cli/sync/emitter.py` (modify, ~10 lines added)

**Notes**:
- Lazy import prevents circular dependency issues
- Cache identity in module-level variable for performance

---

### Subtask T008 – Add identity injection in _emit()

**Purpose**: Add project_uuid and project_slug to every event envelope.

**Steps**:
1. Find the `_emit()` method in `EventEmitter` class
2. Add identity resolution at the start of the method:
   ```python
   def _emit(
       self,
       event_type: str,
       aggregate_id: str,
       aggregate_type: str,
       payload: dict[str, Any],
       causation_id: str | None = None,
   ) -> dict[str, Any] | None:
       try:
           # Get project identity
           identity = self._get_identity()
           
           # ... existing clock tick code ...
           
           # Build event dict (add identity fields)
           event: dict[str, Any] = {
               "event_id": _generate_ulid(),
               "event_type": event_type,
               # ... existing fields ...
               "project_uuid": str(identity.project_uuid) if identity.project_uuid else None,
               "project_slug": identity.project_slug,
           }
   ```
3. Add `_identity` instance variable to cache resolved identity:
   ```python
   @dataclass
   class EventEmitter:
       # ... existing fields ...
       _identity: ProjectIdentity | None = field(default=None, repr=False)
       
       def _get_identity(self) -> ProjectIdentity:
           if self._identity is None:
               self._identity = _get_project_identity()
           return self._identity
   ```
4. Update `_validate_event()` to pass `project_uuid`/`project_slug` into the
   EventModel (once spec-kitty-events is updated), and ensure missing
   `project_uuid` does NOT hard-fail validation (since queue-only is allowed).

**Files**:
- `src/specify_cli/sync/emitter.py` (modify, ~30 lines changed)

**Notes**:
- Cache identity in instance to avoid repeated file I/O
- Convert UUID to string for JSON serialization
- project_slug can be None (optional field)

---

### Subtask T009 – Add validation for missing identity

**Purpose**: Warn and queue-only when project_uuid is missing.

**Steps**:
1. In `_emit()`, after building the event dict, add validation:
   ```python
   # Validate: if project_uuid missing, warn and queue only
   if not event.get("project_uuid"):
       _console.print(
           "[yellow]Warning: Event missing project_uuid; queued locally only[/yellow]"
       )
       # Queue event but skip WebSocket send
       self.queue.queue_event(event)
       return event
   ```
2. This check should come BEFORE the WebSocket send logic
3. Ensure the event is still queued (for later batch sync)

**Files**:
- `src/specify_cli/sync/emitter.py` (modify, ~15 lines added)

**Notes**:
- Events without identity can still be queued for batch sync
- Warning helps users understand why real-time sync isn't working
- This is a graceful degradation, not a hard failure

---

### Subtask T010 – Update get_emitter() for identity

**Purpose**: Ensure identity is resolved when emitter is first accessed.

**Steps**:
1. Find `get_emitter()` function in `sync/events.py`
2. Ensure `ensure_identity()` is called early in the flow:
   ```python
   def get_emitter() -> EventEmitter:
       global _emitter
       if _emitter is None:
           # Ensure identity exists before creating emitter
           from specify_cli.sync.project_identity import ensure_identity
           from specify_cli.tasks_support import find_repo_root
           try:
               repo_root = find_repo_root()
               ensure_identity(repo_root)
           except Exception as e:
               logger.warning(f"Could not ensure identity: {e}")
           
           _emitter = EventEmitter()
       return _emitter
   ```
3. Handle case where repo_root can't be found (non-project context)

**Files**:
- `src/specify_cli/sync/events.py` (modify, ~15 lines)

**Notes**:
- Identity resolution failures should warn, not crash
- Emitter should still work without identity (graceful degradation)

---

### Subtask T011 – Update emission tests with identity verification

**Purpose**: Verify all emitted events contain project_uuid.

**Steps**:
1. Open `tests/sync/test_event_emission.py`
2. Update existing tests to verify identity fields:
   ```python
   def test_planned_to_doing_includes_identity(self, emitter: EventEmitter, temp_queue: OfflineQueue):
       """implement: WP event includes project_uuid."""
       event = emitter.emit_wp_status_changed(
           wp_id="WP01",
           previous_status="planned",
           new_status="doing",
       )
       assert event is not None
       assert "project_uuid" in event
       assert event["project_uuid"] is not None  # Should be valid UUID string
       # project_slug may be None if derived from dir name
   ```
3. Add test for missing identity warning:
   ```python
   def test_missing_identity_queues_only(self, temp_queue: OfflineQueue):
       """Events without identity are queued but not sent via WebSocket."""
       # Create emitter with identity resolution disabled/mocked to return None
       # Verify event is queued
       # Verify warning was logged
   ```

**Files**:
- `tests/sync/test_event_emission.py` (modify, ~50 lines added)

**Test Commands**:
```bash
pytest tests/sync/test_event_emission.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance overhead from identity resolution | Cache identity in emitter instance |
| Circular import | Use lazy import pattern |
| Breaking existing tests | Update test fixtures to mock identity |

---

## Review Guidance

**Reviewers should verify**:
1. Identity injection is in `_emit()` only (not duplicated in emit_* methods)
2. Identity is cached (check `_identity` field usage)
3. Warning is user-visible when identity missing
4. Existing tests still pass

---

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
