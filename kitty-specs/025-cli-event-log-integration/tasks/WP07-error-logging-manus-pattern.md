---
work_package_id: WP07
title: Error Logging (Manus Pattern)
lane: "done"
dependencies: [WP03]
base_branch: 2.x
base_commit: cdc7ce25582e38fd92ff031df28c89b9f62e49d7
created_at: '2026-01-30T16:05:13.107798+00:00'
subtasks:
- T036
- T037
- T038
- T039
- T040
phase: Phase 2 - Advanced Features & Edge Cases
assignee: ''
agent: "claude-wp07-final-reviewer"
shell_pid: "27285"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-27T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Error Logging (Manus Pattern)

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you start.
- **Report progress**: Update Activity Log as you address feedback items.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate if work needs changes.]*

---

## Objectives & Success Criteria

**Primary Goal**: Implement error event logging for agent learning and debugging (Manus pattern - learning from failures).

**Success Criteria**:
- ✅ ErrorEvent dataclass with error_id ULID, error_type, entity_id, reason, context
- ✅ ErrorStorage class with daily JSONL logging (parallel structure to EventStore)
- ✅ `@with_error_storage` AOP decorator for dependency injection
- ✅ Error logging integrated into validation failures (state transition errors)
- ✅ Best-effort error handling (operations not blocked if error log fails)
- ✅ Errors logged to `.kittify/errors/YYYY-MM-DD.jsonl`

**Priority**: P3 (US7 - nice-to-have learning capability)

**User Story**: US7 - Error Logging with Manus Pattern

**Independent Test**:
```bash
# Trigger invalid state transition
cd /tmp/test-error-logging
spec-kitty init

# Create stub WP file
mkdir -p kitty-specs/test-feature/tasks
echo '---
work_package_id: WP01
lane: planned
---
# Test WP' > kitty-specs/test-feature/tasks/WP01-test.md

# Try invalid transition (planned → done)
spec-kitty agent tasks move-task WP01 --to done 2>&1

# Should fail with error AND log to .kittify/errors/
cat .kittify/errors/$(date +%Y-%m-%d).jsonl | jq .
# Should show: error_type="StateTransitionError", entity_id="WP01"
```

---

## Context & Constraints

### ⚠️ CRITICAL: Target Branch

**This work package MUST be implemented on the `2.x` branch (NOT main).**

Verify you're on 2.x:
```bash
git branch --show-current  # Must output: 2.x
```

### Prerequisites

- **WP03 complete**: AOP pattern established (can reuse for error storage)
- **Data model**: ErrorEvent and ErrorStorage (lines 321-360)
- **Spec**: US7 acceptance scenarios (lines 137-141)
- **Quickstart**: Error logging example (lines 221-285)

### Architectural Constraints

**From data-model.md (ErrorStorage)**:
- Daily JSONL files (`.kittify/errors/YYYY-MM-DD.jsonl`)
- Parallel structure to EventStore (same file rotation, append pattern)
- ErrorEvent schema: error_id, error_type, entity_id, attempted_operation, reason, timestamp, context

**From spec.md (FR-025 to FR-027)**:
- Must log validation errors (state transitions, gate failures)
- Must include error context (error_type, entity_id, operation, reason)
- Must NOT block operations if error logging fails (best-effort)

### Key Technical Decisions

1. **Best-Effort Logging** (FR-027): Wrap error logging in try/except, don't block operations
2. **Daily Rotation** (US7): Same pattern as event log (YYYY-MM-DD.jsonl)
3. **Manus Pattern**: Future agents can review error log to learn from past mistakes

---

## Subtasks & Detailed Guidance

### Subtask T036 – Create ErrorEvent dataclass (error_id ULID, error_type, entity_id, reason, context)

**Purpose**: Define the error event structure for logging validation failures.

**Steps**:

1. **Add ErrorEvent to types module**:
   ```python
   # In src/specify_cli/events/types.py (add after Event and LamportClock)

   from dataclasses import dataclass, asdict
   from typing import Any
   import json

   @dataclass
   class ErrorEvent:
       """
       Error event for validation failures and operational errors.

       Schema matches data-model.md (lines 327-338).
       Used for Manus pattern (agent learning from failures).
       """
       error_id: str            # ULID (globally unique)
       error_type: str          # "ValidationError", "StateTransitionError", "GateFailure"
       entity_id: str           # Entity that triggered error (e.g., "WP01")
       attempted_operation: str # Command that failed (e.g., "move_task WP01 --to done")
       reason: str              # Human-readable explanation
       timestamp: str           # ISO 8601 UTC
       context: dict[str, Any]  # Additional debugging metadata

       def to_json(self) -> str:
           """Serialize error event to JSON (for JSONL file)."""
           return json.dumps(asdict(self), ensure_ascii=False)

       @classmethod
       def from_json(cls, json_str: str) -> "ErrorEvent":
           """Deserialize error event from JSON."""
           data = json.loads(json_str)
           return cls(**data)

       def __post_init__(self):
           """Validate error event after creation."""
           if not self.error_id:
               raise ValueError("error_id cannot be empty")
           if not self.error_type:
               raise ValueError("error_type cannot be empty")
           if not self.entity_id:
               raise ValueError("entity_id cannot be empty")
   ```

**Files**:
- `src/specify_cli/events/types.py` (modify: add ErrorEvent dataclass, ~40 lines)

**Validation**:
- [ ] ErrorEvent has all 7 fields from data-model.md
- [ ] `to_json()` and `from_json()` methods for serialization
- [ ] `__post_init__` validates required fields
- [ ] Import succeeds: `from specify_cli.events.types import ErrorEvent`

**Edge Cases**:
- Empty error_id: Raises ValueError
- Missing context keys: Tolerated (context is flexible dict)
- Large context (>1KB): Tolerated (JSON serialization handles)

**Parallel?**: Yes - Can implement in parallel with T037-T038

---

### Subtask T037 – Create ErrorStorage class with daily JSONL logging (parallel to EventStore)

**Purpose**: Provide storage adapter for error events, mirroring EventStore's structure.

**Steps**:

1. **Create error_storage module**:
   ```python
   # src/specify_cli/events/error_storage.py (new file)

   from pathlib import Path
   from datetime import datetime, timezone
   from typing import Any

   from specify_cli.events.types import ErrorEvent, generate_ulid


   class ErrorStorage:
       """
       Storage adapter for error events (Manus pattern).

       Structure mirrors EventStore but for error logging.
       """

       def __init__(self, repo_root: Path):
           """
           Initialize ErrorStorage for a repository.

           Args:
               repo_root: Path to project root (contains .kittify/)
           """
           self.repo_root = repo_root
           self.errors_dir = repo_root / ".kittify" / "errors"

           # Ensure directory exists
           self.errors_dir.mkdir(parents=True, exist_ok=True)

       def log(
           self,
           error_type: str,
           entity_id: str,
           attempted_operation: str,
           reason: str,
           context: dict[str, Any] | None = None,
       ) -> ErrorEvent | None:
           """
           Log error event to daily JSONL file.

           Best-effort: Returns None if logging fails (doesn't raise exception).

           Args:
               error_type: Error type (e.g., "StateTransitionError")
               entity_id: Entity affected (e.g., "WP01")
               attempted_operation: Command that failed
               reason: Human-readable explanation
               context: Optional debugging metadata

           Returns:
               ErrorEvent if successful, None if logging failed
           """
           try:
               # Create error event
               error_event = ErrorEvent(
                   error_id=generate_ulid(),
                   error_type=error_type,
                   entity_id=entity_id,
                   attempted_operation=attempted_operation,
                   reason=reason,
                   timestamp=datetime.now(timezone.utc).isoformat(),
                   context=context or {},
               )

               # Determine filename from current date
               date_str = datetime.now(timezone.utc).date().isoformat()  # YYYY-MM-DD
               jsonl_file = self.errors_dir / f"{date_str}.jsonl"

               # Append to JSONL (best-effort, no file locking)
               json_line = error_event.to_json() + "\n"
               with open(jsonl_file, "a", encoding="utf-8") as f:
                   f.write(json_line)
                   f.flush()

               return error_event

           except Exception as e:
               # Best-effort: log warning but don't raise
               import sys
               print(f"⚠️ Failed to log error: {e}", file=sys.stderr)
               return None

       def read(
           self,
           entity_id: str | None = None,
           error_type: str | None = None,
       ) -> list[ErrorEvent]:
           """
           Read error events from log.

           Args:
               entity_id: Filter by entity
               error_type: Filter by error type

           Returns:
               List of ErrorEvent objects
           """
           errors = []

           # Read all error JSONL files
           for jsonl_file in sorted(self.errors_dir.glob("*.jsonl")):
               try:
                   for line in jsonl_file.read_text().splitlines():
                       if not line.strip():
                           continue

                       try:
                           error = ErrorEvent.from_json(line)

                           # Apply filters
                           if entity_id and error.entity_id != entity_id:
                               continue
                           if error_type and error.error_type != error_type:
                               continue

                           errors.append(error)
                       except (json.JSONDecodeError, ValueError):
                           # Skip invalid lines
                           continue
               except Exception:
                   # Skip files that can't be read
                   continue

           return errors
   ```

**Files**:
- `src/specify_cli/events/error_storage.py` (new file, ~120 lines)

**Validation**:
- [ ] `log()` creates `.kittify/errors/YYYY-MM-DD.jsonl`
- [ ] Uses daily file rotation (same pattern as EventStore)
- [ ] Best-effort: Returns None on failure (doesn't raise exception)
- [ ] `read()` filters by entity_id and error_type
- [ ] Graceful degradation (skips invalid JSON lines)

**Edge Cases**:
- Errors directory missing: Created automatically (mkdir parents=True)
- Log write fails: Warning logged, returns None (doesn't crash operation)
- No errors logged yet: read() returns empty list

**Parallel?**: Yes - Can implement in parallel with T036, T038

---

### Subtask T038 – Create `@with_error_storage` AOP decorator

**Purpose**: Provide dependency injection for ErrorStorage (mirrors @with_event_store pattern).

**Steps**:

1. **Add decorator to middleware module**:
   ```python
   # In src/specify_cli/events/middleware.py (modify)

   from specify_cli.events.error_storage import ErrorStorage

   def with_error_storage(func: Callable) -> Callable:
       """
       AOP decorator for injecting ErrorStorage into CLI commands.

       Usage:
           @with_error_storage
           def move_task(wp_id: str, lane: str, error_storage: ErrorStorage):
               # error_storage parameter automatically injected
               error_storage.log(...)

       Mirrors @with_event_store pattern for consistency.
       """
       @wraps(func)
       def wrapper(*args, **kwargs):
           # Detect repo root
           repo_root = get_repo_root()

           # Initialize ErrorStorage
           error_storage = ErrorStorage(repo_root)

           # Inject into kwargs
           kwargs["error_storage"] = error_storage

           # Call original function
           return func(*args, **kwargs)

       return wrapper


   def with_event_and_error_storage(func: Callable) -> Callable:
       """
       Combined decorator for both EventStore and ErrorStorage.

       Usage:
           @with_event_and_error_storage
           def move_task(wp_id: str, lane: str, event_store: EventStore, error_storage: ErrorStorage):
               # Both injected
               pass

       Convenience decorator to avoid stacking @with_event_store @with_error_storage.
       """
       @wraps(func)
       def wrapper(*args, **kwargs):
           repo_root = get_repo_root()

           # Initialize both storages
           event_store = EventStore(repo_root)
           error_storage = ErrorStorage(repo_root)

           # Inject both
           kwargs["event_store"] = event_store
           kwargs["error_storage"] = error_storage

           return func(*args, **kwargs)

       return wrapper
   ```

**Files**:
- `src/specify_cli/events/middleware.py` (modify: add @with_error_storage and combined decorator)

**Validation**:
- [ ] `@with_error_storage` injects ErrorStorage parameter
- [ ] `@with_event_and_error_storage` injects both EventStore and ErrorStorage
- [ ] Mirrors @with_event_store pattern (consistent API)
- [ ] Test: Decorate function, verify error_storage parameter injected

**Edge Cases**:
- ErrorStorage initialization fails: RuntimeError propagated (expected)
- Multiple decorators: Combined decorator preferred (cleaner)

**Parallel?**: Yes - Can implement in parallel with T036-T037, T039

---

### Subtask T039 – Integrate error logging into validation failures (state transition errors)

**Purpose**: Log error events when validation fails (invalid state transitions, dependency violations, etc.).

**Steps**:

1. **Modify move_task to log transition errors**:
   ```python
   # In src/specify_cli/cli/commands/agent/tasks.py (modify)

   from specify_cli.events.middleware import with_event_and_error_storage
   from specify_cli.events.error_storage import ErrorStorage

   @with_event_and_error_storage  # Injects both storages
   def move_task(
       wp_id: str,
       to: str,
       event_store: EventStore,
       error_storage: ErrorStorage,  # NEW parameter
   ):
       """Move work package with error logging."""
       # ... existing logic to load current state

       # Validate transition
       if not is_valid_transition(current_lane, to):
           # Log error (NEW)
           error_storage.log(
               error_type="StateTransitionError",
               entity_id=wp_id,
               attempted_operation=f"move_task {wp_id} --to {to}",
               reason=f"Cannot transition from '{current_lane}' to '{to}'",
               context={
                   "current_status": current_lane,
                   "requested_status": to,
                   "valid_transitions": get_valid_transitions(current_lane),
                   "feature_slug": get_current_feature_slug(),
               },
           )

           # Raise error (existing behavior)
           raise ValueError(
               f"Invalid transition: {current_lane} → {to}. "
               f"Valid transitions: {get_valid_transitions(current_lane)}"
           )

       # ... existing logic to update frontmatter and emit event
   ```

2. **Add error logging to dependency validation**:
   ```python
   # If dependency validation exists in move_task or elsewhere

   def validate_dependencies(wp_id: str, dependencies: list[str]) -> None:
       """Validate dependencies are complete before transition."""
       for dep_id in dependencies:
           dep_status = get_wp_status(dep_id)
           if dep_status != "done":
               # Log error
               error_storage.log(
                   error_type="DependencyValidationError",
                   entity_id=wp_id,
                   attempted_operation=f"move_task {wp_id} --to doing",
                   reason=f"Dependency {dep_id} is not complete (status: {dep_status})",
                   context={
                       "dependency_id": dep_id,
                       "dependency_status": dep_status,
                       "required_status": "done",
                   },
               )

               raise ValueError(f"Dependency {dep_id} not complete")
   ```

**Files**:
- `src/specify_cli/cli/commands/agent/tasks.py` (modify: add error logging to validation)

**Validation**:
- [ ] `move_task` uses `@with_event_and_error_storage` decorator
- [ ] Error logged BEFORE raising ValidationError (capture attempted operation)
- [ ] Error context includes: current_status, requested_status, valid_transitions
- [ ] Test: Trigger invalid transition, verify error in `.kittify/errors/*.jsonl`

**Edge Cases**:
- Error logging fails: Warning logged, operation still raises ValidationError
- Multiple validation failures: Each logs separate error event
- Error storage not available: Best-effort wrapper catches, continues

**Parallel?**: No - Sequential after T038 (needs decorator)

---

### Subtask T040 – Add best-effort error handling (don't block operations if error log fails)

**Purpose**: Ensure error logging failures don't prevent normal operations from completing.

**Steps**:

1. **Verify best-effort in ErrorStorage.log()**:
   ```python
   # In src/specify_cli/events/error_storage.py
   # Should already wrap in try/except from T037

   def log(...) -> ErrorEvent | None:
       """Log error with best-effort pattern."""
       try:
           # ... create and write error event
           return error_event
       except Exception as e:
           # Best-effort: log warning but don't raise
           import sys
           print(f"⚠️ Failed to log error: {e}", file=sys.stderr)
           return None  # Signal failure without blocking
   ```

2. **Add defensive error handling in decorator**:
   ```python
   # In src/specify_cli/events/middleware.py
   # Modify @with_error_storage decorator

   def with_error_storage(func: Callable) -> Callable:
       @wraps(func)
       def wrapper(*args, **kwargs):
           try:
               repo_root = get_repo_root()
               error_storage = ErrorStorage(repo_root)
               kwargs["error_storage"] = error_storage
           except Exception as e:
               # If ErrorStorage initialization fails, inject None
               import sys
               print(f"⚠️ Error storage unavailable: {e}", file=sys.stderr)
               kwargs["error_storage"] = None

           return func(*args, **kwargs)
       return wrapper
   ```

3. **Handle None error_storage in move_task**:
   ```python
   # In src/specify_cli/cli/commands/agent/tasks.py
   # Modify validation error logging from T039

   # Log error (if error_storage available)
   if error_storage:
       error_storage.log(...)
   # If None, skip logging (best-effort)
   ```

**Files**:
- `src/specify_cli/events/error_storage.py` (verify: best-effort exists from T037)
- `src/specify_cli/events/middleware.py` (modify: defensive error handling)
- `src/specify_cli/cli/commands/agent/tasks.py` (modify: check if error_storage is None)

**Validation**:
- [ ] `ErrorStorage.log()` returns None on failure (doesn't raise)
- [ ] Decorator injects None if ErrorStorage init fails
- [ ] Commands check if error_storage is None before logging
- [ ] Operations complete successfully even if error logging fails

**Edge Cases**:
- Errors directory not writable: log() returns None, operation continues
- Disk full: log() returns None, operation continues
- Concurrent error writes: No file locking (best-effort, race conditions tolerated)

**Parallel?**: No - Enhancement of T037 (must run after ErrorStorage exists)

---

## Test Strategy

**No separate test files** (constitution: tests not explicitly requested).

**Validation approach**:
1. **T036**: Unit test - Create ErrorEvent, serialize/deserialize
2. **T037**: Unit test - Log error, verify JSONL file created
3. **T038**: Decorator test - Verify error_storage injected
4. **T039**: Integration test - Trigger invalid transition, verify error logged
5. **T040**: Best-effort test - Simulate error log failure, verify operation continues

**Error logging test**:
```bash
# Setup project
cd /tmp/test-error-logging
spec-kitty init

# Create WP file in planned state
mkdir -p kitty-specs/test/tasks
cat > kitty-specs/test/tasks/WP01-test.md << 'EOF'
---
work_package_id: WP01
lane: planned
---
# Test WP
EOF

# Trigger invalid transition (planned → done)
spec-kitty agent tasks move-task WP01 --to done 2>&1

# Should fail with clear error
# Should log to .kittify/errors/YYYY-MM-DD.jsonl

# Verify error logged
errors=$(cat .kittify/errors/$(date +%Y-%m-%d).jsonl)
echo "$errors" | jq -r '.error_type'  # Should be "StateTransitionError"
echo "$errors" | jq -r '.reason'      # Should explain invalid transition

# Verify error includes context
echo "$errors" | jq '.context.current_status'      # Should be "planned"
echo "$errors" | jq '.context.requested_status'    # Should be "done"
echo "$errors" | jq '.context.valid_transitions'   # Should be ["doing"]

echo "✓ Error logging test passed"
```

**Best-effort test**:
```bash
# Make errors directory read-only (simulate failure)
chmod 444 /tmp/test-error-logging/.kittify/errors

# Trigger error (should still work despite logging failure)
spec-kitty agent tasks move-task WP01 --to done 2>&1
# Should show: "⚠️ Failed to log error: ..." (warning)
# Should show: "Invalid transition: planned → done" (original error)
# Should NOT crash or hang

# Restore permissions
chmod 755 /tmp/test-error-logging/.kittify/errors

echo "✓ Best-effort test passed (operation continued despite log failure)"
```

---

## Risks & Mitigations

### Risk 1: Error logging adds latency to failing operations

**Impact**: Validation failures take longer to report

**Mitigation**:
- Best-effort pattern (T040) doesn't block on error write
- Error logging is fast (single JSONL append, no index update)
- Validation errors are rare (users learn valid transitions quickly)

### Risk 2: Error logs grow unbounded

**Impact**: `.kittify/errors/` directory becomes large over time

**Mitigation**:
- Daily rotation keeps individual files manageable
- Users can delete old error logs (not used for state reconstruction)
- Future enhancement: Auto-archive errors >90 days old

### Risk 3: Concurrent error writes corrupt files

**Impact**: Error log has invalid JSON lines

**Mitigation**:
- Best-effort (no file locking) tolerates corruption
- Error log is not critical path (used for debugging only)
- Graceful degradation (skip invalid lines) in read()

---

## Definition of Done Checklist

- [ ] T036: ErrorEvent dataclass with 7 fields (error_id, error_type, entity_id, etc.)
- [ ] T036: Serialization methods (to_json, from_json)
- [ ] T037: ErrorStorage class with log() and read() methods
- [ ] T037: Daily JSONL files (YYYY-MM-DD.jsonl in .kittify/errors/)
- [ ] T037: Best-effort pattern (returns None on failure)
- [ ] T038: `@with_error_storage` decorator injects ErrorStorage
- [ ] T038: `@with_event_and_error_storage` combined decorator
- [ ] T039: move_task logs StateTransitionError on invalid transitions
- [ ] T039: Error context includes current_status, requested_status, valid_transitions
- [ ] T040: ErrorStorage.log() doesn't raise on failure
- [ ] T040: Decorator handles ErrorStorage init failure (injects None)
- [ ] T040: Commands check if error_storage is None
- [ ] Error logging test passes (invalid transition logged)
- [ ] Best-effort test passes (operation continues despite log failure)

---

## Review Guidance

**Key Acceptance Checkpoints**:

1. **T036 - ErrorEvent Schema**:
   - ✓ All 7 fields match data-model.md
   - ✓ Validation in __post_init__

2. **T037 - ErrorStorage**:
   - ✓ Daily file rotation (YYYY-MM-DD.jsonl)
   - ✓ Best-effort (try/except, returns None)
   - ✓ read() method filters by entity_id and error_type

3. **T038 - Decorator**:
   - ✓ Injects error_storage parameter
   - ✓ Combined decorator available

4. **T039 - Integration**:
   - ✓ Logs StateTransitionError on validation failure
   - ✓ Context includes debugging metadata

5. **T040 - Best-Effort**:
   - ✓ Operations continue if error log fails
   - ✓ Warning logged (not silent failure)

**Reviewers should**:
- Test invalid transition (verify error logged)
- Test best-effort (make errors dir read-only, verify operation continues)
- Check error context (verify useful debugging info)

---

## Activity Log

- 2026-01-27T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---
- 2026-01-30T16:10:55Z – unknown – shell_pid=22633 – lane=for_review – Ready for review: Implemented error logging with Manus pattern. All 5 subtasks complete (T036-T040). ErrorEvent dataclass, ErrorStorage with daily JSONL files, AOP decorators, and error logging integrated into move_task validation failures. Best-effort pattern ensures operations not blocked if logging fails.
- 2026-01-30T16:31:06Z – claude-wp07-final-reviewer – shell_pid=27285 – lane=doing – Started review via workflow command
- 2026-01-30T16:31:49Z – claude-wp07-final-reviewer – shell_pid=27285 – lane=done – Review passed: ErrorEvent dataclass implemented, ErrorStorage with daily JSONL logging, AOP decorators for error storage, validation error logging integrated into move-task. Manus pattern complete. Final WP approved!

## Implementation Command

This WP depends on WP03 (EventStore and AOP pattern). Implement from WP03's branch:

```bash
spec-kitty implement WP07 --base WP03
```

**Note**: WP07 can be implemented in parallel with WP04-WP05-WP06 (independent paths).

This will create workspace: `.worktrees/025-cli-event-log-integration-WP07/` branched from WP03.
