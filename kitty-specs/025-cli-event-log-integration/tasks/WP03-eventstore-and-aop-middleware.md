---
work_package_id: "WP03"
title: "EventStore & AOP Middleware"
phase: "Phase 1 - Core Event Infrastructure"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
history:
  - timestamp: "2026-01-27T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – EventStore & AOP Middleware

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

**Primary Goal**: Implement EventStore adapter and AOP decorators for transparent event emission across CLI commands.

**Success Criteria**:
- ✅ EventStore class wraps spec-kitty-events library with clean API
- ✅ `emit()` method handles clock increment, JSONL write, and clock persistence
- ✅ `@with_event_store` decorator provides dependency injection to commands
- ✅ `spec-kitty agent tasks move-task` emits `WPStatusChanged` events
- ✅ `spec-kitty agent feature setup-spec` emits `SpecCreated` events
- ✅ `spec-kitty agent feature finalize-tasks` emits `WPCreated` events (one per WP)
- ✅ Event emission adds <15ms latency (performance goal met)

**Priority**: P1 (US1 core capability)

**User Story**: US1 - Event Emission on Workflow State Changes (complete)

**Independent Test**:
```bash
# Fresh project setup
cd /tmp/test-project
spec-kitty init

# Move WP to doing (should emit event)
spec-kitty agent tasks move-task WP01 --to doing

# Verify event emitted
cat .kittify/events/$(date +%Y-%m-%d).jsonl | jq .
# Should show WPStatusChanged event with old_status="planned", new_status="doing"
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

- **WP02 complete**: Event, LamportClock, ClockStorage, file_io modules available
- **Data model**: `kitty-specs/025-cli-event-log-integration/data-model.md` (lines 117-181)
- **Quickstart**: `kitty-specs/025-cli-event-log-integration/quickstart.md` (lines 58-92 for emit example)
- **Plan decision**: Synchronous writes (15ms overhead acceptable per planning Q3)

### Architectural Constraints

**From plan.md (lines 9-13)**:
- AOP-style middleware for event emission integration
- AOP decorator pattern for EventStore dependency injection (`@with_event_store`)
- Events-only on 2.x branch (no YAML logs)

**From data-model.md (EventStore)**:
- Emit operation: tick clock → create event → append JSONL → update index → save clock
- Read operation: query index (if filters) or read all JSONL files
- Wraps spec-kitty-events library via adapter (from WP01)

### Key Technical Decisions

1. **AOP Pattern** (Planning Q1): Non-invasive decorator for event emission
2. **Synchronous Writes** (Planning Q3): JSONL + clock save in single emit() call
3. **Integration Points**: Wrap existing commands, preserve original behavior

---

## Subtasks & Detailed Guidance

### Subtask T013 – Create EventStore class wrapping spec-kitty-events library

**Purpose**: Provide the main interface for event emission and reading, wrapping the adapter layer from WP01.

**Steps**:

1. **Create store module**:
   ```python
   # src/specify_cli/events/store.py (new file)

   from pathlib import Path
   from datetime import datetime, timezone
   from typing import Any

   from specify_cli.events.types import Event, LamportClock, generate_ulid
   from specify_cli.events.clock_storage import ClockStorage
   from specify_cli.events.file_io import JSONLFileWriter, initialize_event_directories
   from specify_cli.events.adapter import EventAdapter


   class EventStore:
       """
       Storage adapter for persisting events to JSONL files.

       Wraps spec-kitty-events library and provides clean API for CLI.
       Handles: clock management, file I/O, directory initialization.
       """

       def __init__(self, repo_root: Path):
           """
           Initialize EventStore for a repository.

           Args:
               repo_root: Path to project root (contains .kittify/)

           Raises:
               RuntimeError: If spec-kitty-events library not available
           """
           if not EventAdapter.check_library_available():
               raise RuntimeError(EventAdapter.get_missing_library_error())

           self.repo_root = repo_root
           self.kittify_dir = repo_root / ".kittify"
           self.events_dir = self.kittify_dir / "events"
           self.clock_file = self.kittify_dir / "clock.json"

           # Initialize directories
           initialize_event_directories(repo_root)

           # Load Lamport clock
           clock_storage = ClockStorage(self.clock_file)
           self.clock = clock_storage.load(events_dir=self.events_dir)
           self.clock_storage = clock_storage

           # Initialize file writer
           self.file_writer = JSONLFileWriter(self.events_dir)

       def emit(
           self,
           event_type: str,
           entity_id: str,
           entity_type: str,
           actor: str,
           payload: dict[str, Any],
           causation_id: str | None = None,
           correlation_id: str | None = None,
       ) -> Event:
           """
           Emit event with automatic Lamport clock increment.

           This is the PRIMARY method for event emission.

           Args:
               event_type: Event type (e.g., "WPStatusChanged")
               entity_id: Entity affected (e.g., "WP01")
               entity_type: Entity type (e.g., "WorkPackage")
               actor: Agent/user that caused event
               payload: Event-specific data (flexible dict)
               causation_id: Optional command ID (for idempotency)
               correlation_id: Optional session ID (for tracing)

           Returns:
               The persisted Event object

           Raises:
               IOError: If JSONL write fails
               ValueError: If event validation fails
           """
           # 1. Increment Lamport clock
           lamport_clock = self.clock.tick()

           # 2. Create event object
           event = Event(
               event_id=generate_ulid(),
               event_type=event_type,
               event_version=1,
               lamport_clock=lamport_clock,
               entity_id=entity_id,
               entity_type=entity_type,
               timestamp=datetime.now(timezone.utc).isoformat(),
               actor=actor,
               causation_id=causation_id,
               correlation_id=correlation_id,
               payload=payload,
           )

           # 3. Append to JSONL file (with file locking)
           self.file_writer.append_event(event)

           # 4. Persist clock state (after successful write)
           self.clock_storage.save(self.clock)

           return event

       def get_current_clock_value(self) -> int:
           """Get current Lamport clock value (for debugging/inspection)."""
           return self.clock.value
   ```

**Files**:
- `src/specify_cli/events/store.py` (new file, ~120 lines)

**Validation**:
- [ ] `__init__()` initializes directories, loads clock, creates file writer
- [ ] `emit()` ticks clock, creates event, writes JSONL, saves clock
- [ ] Returns Event object with correct fields (event_id ULID, lamport_clock incremented)
- [ ] Raises RuntimeError if spec-kitty-events library missing
- [ ] Import succeeds: `from specify_cli.events.store import EventStore`

**Edge Cases**:
- First event (clock.json missing): Initializes clock to 1
- JSONL write fails: IOError propagated (clock not saved, ensuring consistency)
- Idempotency check: Not implemented in emit() (delegated to calling code via causation_id)

**Parallel?**: No - Depends on T006-T012 (WP02 complete)

---

### Subtask T014 – Implement `emit()` method with automatic clock increment and JSONL write

**Purpose**: This subtask is mostly covered in T013. The focus here is on performance validation.

**Steps**:

1. **Add performance benchmarking**:
   ```python
   # In src/specify_cli/events/store.py (add method)

   import time

   def benchmark_emit(self, num_events: int = 100) -> dict[str, float]:
       """
       Benchmark event emission performance.

       Args:
           num_events: Number of events to emit for benchmarking

       Returns:
           Dict with avg_ms (average latency) and total_ms (total time)
       """
       start_time = time.time()

       for i in range(num_events):
           self.emit(
               event_type="Benchmark",
               entity_id=f"test-{i}",
               entity_type="Test",
               actor="benchmark",
               payload={"iteration": i},
           )

       end_time = time.time()
       total_ms = (end_time - start_time) * 1000
       avg_ms = total_ms / num_events

       return {
           "num_events": num_events,
           "total_ms": round(total_ms, 2),
           "avg_ms": round(avg_ms, 2),
       }
   ```

2. **Test performance**:
   ```bash
   # Test performance in Python REPL
   from specify_cli.events.store import EventStore
   from pathlib import Path

   store = EventStore(Path("/tmp/perf-test"))
   result = store.benchmark_emit(100)
   print(f"Average emit latency: {result['avg_ms']}ms")
   # Target: <15ms per event
   ```

**Files**:
- `src/specify_cli/events/store.py` (modify: add benchmark_emit method)

**Validation**:
- [ ] `emit()` completes in <15ms on average (performance goal)
- [ ] Latency breakdown: clock tick (<1ms) + JSONL write (5-10ms) + clock save (2-3ms)
- [ ] Benchmark utility available for profiling

**Edge Cases**:
- First emit slower (directory creation overhead): Expected, subsequent emits faster
- Large payloads (>1KB): Latency increases linearly (acceptable)
- Concurrent emits: File locking serializes (still <15ms per emit due to fast lock acquisition)

**Parallel?**: No - Extension of T013 (same file)

---

### Subtask T015 – Create `@with_event_store` AOP decorator for dependency injection

**Purpose**: Provide clean dependency injection so commands can access EventStore without manual initialization.

**Steps**:

1. **Create middleware module**:
   ```python
   # src/specify_cli/events/middleware.py (new file)

   from functools import wraps
   from pathlib import Path
   from typing import Callable, Any

   from specify_cli.events.store import EventStore
   from specify_cli.core.repo import get_repo_root  # Assume this exists


   def with_event_store(func: Callable) -> Callable:
       """
       AOP decorator for injecting EventStore into CLI commands.

       Usage:
           @with_event_store
           def move_task(wp_id: str, lane: str, event_store: EventStore):
               # event_store parameter automatically injected
               event_store.emit(...)

       The decorator:
       1. Detects repo root from current directory
       2. Initializes EventStore(repo_root)
       3. Injects as 'event_store' keyword argument

       If EventStore initialization fails (library missing), error is raised
       with clear message (handled by EventStore.__init__).
       """
       @wraps(func)
       def wrapper(*args, **kwargs):
           # Detect repo root
           repo_root = get_repo_root()  # Assumes spec-kitty has this utility

           # Initialize EventStore
           event_store = EventStore(repo_root)

           # Inject into kwargs
           kwargs["event_store"] = event_store

           # Call original function
           return func(*args, **kwargs)

       return wrapper


   def with_error_storage(func: Callable) -> Callable:
       """
       AOP decorator for injecting ErrorStorage (Phase 2 - WP07).

       Stub for now - will be implemented in WP07.
       """
       @wraps(func)
       def wrapper(*args, **kwargs):
           # TODO: Implement in WP07
           return func(*args, **kwargs)
       return wrapper
   ```

2. **Handle repo root detection** (if get_repo_root doesn't exist):
   ```python
   # In src/specify_cli/core/repo.py (create if missing)

   from pathlib import Path
   import subprocess

   def get_repo_root() -> Path:
       """
       Get repository root (directory containing .git/).

       Returns:
           Path to repository root

       Raises:
           RuntimeError: If not in a git repository
       """
       try:
           result = subprocess.run(
               ["git", "rev-parse", "--show-toplevel"],
               capture_output=True,
               text=True,
               check=True,
           )
           return Path(result.stdout.strip())
       except (subprocess.CalledProcessError, FileNotFoundError):
           raise RuntimeError(
               "Not in a git repository. "
               "Run 'spec-kitty init' to initialize a project."
           )
   ```

**Files**:
- `src/specify_cli/events/middleware.py` (new file, ~60 lines)
- `src/specify_cli/core/repo.py` (create if missing, ~25 lines)

**Validation**:
- [ ] `@with_event_store` decorator injects EventStore as keyword argument
- [ ] Decorated function receives `event_store` parameter automatically
- [ ] Repo root detected via `git rev-parse --show-toplevel`
- [ ] Clear error if not in git repository

**Edge Cases**:
- Not in git repository: RuntimeError with clear message
- EventStore initialization fails (library missing): Propagates error from EventStore.__init__
- Multiple decorators: Order matters (`@with_error_storage @with_event_store` injects both)

**Parallel?**: Yes - Can implement in parallel with T013-T014

---

### Subtask T016 – Integrate event emission into `move_task` command (WPStatusChanged)

**Purpose**: Emit `WPStatusChanged` events when work packages transition between lanes.

**Steps**:

1. **Locate move_task command**:
   ```bash
   # Find the command implementation
   find src -name "*tasks*" -type f | xargs grep -l "move_task"
   # Likely in: src/specify_cli/cli/commands/agent/tasks.py
   ```

2. **Add event emission to move_task**:
   ```python
   # In src/specify_cli/cli/commands/agent/tasks.py (modify)

   from specify_cli.events.middleware import with_event_store
   from specify_cli.events.store import EventStore

   @with_event_store
   def move_task(
       wp_id: str,
       to: str,  # Target lane (doing, for_review, done)
       event_store: EventStore,  # Injected by decorator
   ):
       """
       Move work package to a different lane.

       Emits WPStatusChanged event after successful transition.
       """
       # 1. Load current WP state (existing logic)
       feature_dir = get_current_feature_dir()
       wp_file = find_wp_file(feature_dir, wp_id)
       frontmatter = load_wp_frontmatter(wp_file)
       current_lane = frontmatter.get("lane", "planned")

       # 2. Validate transition (existing logic)
       if not is_valid_transition(current_lane, to):
           raise ValueError(
               f"Invalid transition: {current_lane} → {to}. "
               f"Valid transitions: {get_valid_transitions(current_lane)}"
           )

       # 3. Update frontmatter (existing logic)
       update_wp_frontmatter(wp_file, lane=to)

       # 4. Emit event (NEW)
       try:
           event_store.emit(
               event_type="WPStatusChanged",
               entity_id=wp_id,
               entity_type="WorkPackage",
               actor=get_current_agent(),  # Assumes agent detection utility exists
               causation_id=f"move-task-{wp_id}-{int(time.time())}",
               payload={
                   "feature_slug": get_current_feature_slug(),
                   "old_status": current_lane,
                   "new_status": to,
                   "reason": "User requested transition",
               },
           )
       except Exception as e:
           # Log warning but don't block command
           import sys
           print(f"Warning: Failed to emit event: {e}", file=sys.stderr)

       # 5. Display success message (existing logic)
       print(f"✓ Moved {wp_id} from {current_lane} to {to}")
   ```

3. **Add agent detection utility** (if missing):
   ```python
   # In src/specify_cli/core/agent.py (create if missing)

   import os

   def get_current_agent() -> str:
       """
       Detect current agent (for event actor field).

       Returns:
           Agent name (e.g., "claude", "copilot", "user")
       """
       # Check environment variable (set by agent tooling)
       agent = os.getenv("SPECIFY_AGENT")
       if agent:
           return agent

       # Check if running in known agent contexts
       # (Add detection heuristics as needed)

       # Default to "user"
       return "user"
   ```

**Files**:
- `src/specify_cli/cli/commands/agent/tasks.py` (modify: add @with_event_store and emit() call)
- `src/specify_cli/core/agent.py` (create if missing: agent detection utility)

**Validation**:
- [ ] `move_task` decorated with `@with_event_store`
- [ ] Event emitted AFTER successful frontmatter update
- [ ] Payload includes: feature_slug, old_status, new_status, reason
- [ ] Event emission failure logged but doesn't block command
- [ ] Test: Run `spec-kitty agent tasks move-task WP01 --to doing`, verify event in JSONL

**Edge Cases**:
- Invalid transition: ValidationError raised BEFORE event emission (correct)
- Event emission fails: Warning logged, command succeeds (best-effort)
- Agent detection fails: Defaults to "user"

**Parallel?**: No - Sequential after T015 (needs decorator)

---

### Subtask T017 – Integrate event emission into `setup-spec` command (SpecCreated)

**Purpose**: Emit `SpecCreated` events when new feature specifications are created.

**Steps**:

1. **Locate setup-spec command**:
   ```bash
   find src -name "*feature*" -type f | xargs grep -l "setup-spec"
   # Likely in: src/specify_cli/cli/commands/agent/feature.py
   ```

2. **Add event emission to setup-spec**:
   ```python
   # In src/specify_cli/cli/commands/agent/feature.py (modify)

   from specify_cli.events.middleware import with_event_store
   from specify_cli.events.store import EventStore

   @with_event_store
   def setup_spec(
       feature_slug: str | None,
       event_store: EventStore,  # Injected
   ):
       """
       Create feature specification scaffold.

       Emits SpecCreated event after spec.md is written.
       """
       # 1. Determine feature slug (existing logic)
       if not feature_slug:
           feature_slug = prompt_for_feature_slug()

       # 2. Create spec.md (existing logic)
       feature_dir = create_feature_directory(feature_slug)
       spec_file = feature_dir / "spec.md"
       write_spec_template(spec_file)

       # 3. Emit event (NEW)
       try:
           event_store.emit(
               event_type="SpecCreated",
               entity_id=feature_slug,
               entity_type="FeatureSpec",
               actor=get_current_agent(),
               causation_id=f"setup-spec-{feature_slug}",
               payload={
                   "title": extract_spec_title(spec_file),  # Parse from spec.md
                   "mission": "software-dev",  # Or detect from context
                   "created_by": get_current_agent(),
               },
           )
       except Exception as e:
           import sys
           print(f"Warning: Failed to emit event: {e}", file=sys.stderr)

       # 4. Display success message (existing logic)
       print(f"✓ Created feature specification: {feature_slug}")
   ```

**Files**:
- `src/specify_cli/cli/commands/agent/feature.py` (modify: add event emission)

**Validation**:
- [ ] `setup_spec` decorated with `@with_event_store`
- [ ] Event emitted AFTER spec.md created
- [ ] Payload includes: title (from spec.md), mission, created_by
- [ ] Test: Run `spec-kitty agent feature setup-spec`, verify SpecCreated event

**Edge Cases**:
- Title extraction fails: Use placeholder "Untitled Feature"
- Mission not specified: Default to "software-dev"
- Event emission fails: Warning logged, command succeeds

**Parallel?**: Yes - Can implement in parallel with T016 (both modify different files)

---

### Subtask T018 – Integrate event emission into `finalize-tasks` command (WPCreated events)

**Purpose**: Emit `WPCreated` events for each work package when tasks are finalized.

**Steps**:

1. **Locate finalize-tasks command**:
   ```bash
   find src -name "*feature*" -type f | xargs grep -l "finalize-tasks"
   # Likely in: src/specify_cli/cli/commands/agent/feature.py
   ```

2. **Add event emission to finalize-tasks**:
   ```python
   # In src/specify_cli/cli/commands/agent/feature.py (modify)

   @with_event_store
   def finalize_tasks(
       feature_dir: Path | None,
       event_store: EventStore,  # Injected
   ):
       """
       Finalize tasks: parse dependencies, update frontmatter, commit.

       Emits WPCreated event for each work package file.
       """
       # 1. Detect feature directory (existing logic)
       if not feature_dir:
           feature_dir = get_current_feature_dir()

       # 2. Parse tasks.md for dependencies (existing logic)
       tasks_file = feature_dir / "tasks.md"
       dependencies = parse_dependencies_from_tasks(tasks_file)

       # 3. Update WP frontmatter with dependencies (existing logic)
       wp_files = list((feature_dir / "tasks").glob("WP*.md"))
       for wp_file in wp_files:
           wp_id = extract_wp_id(wp_file.name)
           update_wp_frontmatter(wp_file, dependencies=dependencies.get(wp_id, []))

           # 4. Emit WPCreated event for this WP (NEW)
           try:
               frontmatter = load_wp_frontmatter(wp_file)
               event_store.emit(
                   event_type="WPCreated",
                   entity_id=wp_id,
                   entity_type="WorkPackage",
                   actor=get_current_agent(),
                   causation_id=f"finalize-tasks-{wp_id}",
                   payload={
                       "work_package_id": wp_id,
                       "title": frontmatter.get("title", "Untitled"),
                       "dependencies": frontmatter.get("dependencies", []),
                       "subtasks": frontmatter.get("subtasks", []),
                       "feature_slug": feature_dir.name,
                   },
               )
           except Exception as e:
               import sys
               print(f"Warning: Failed to emit event for {wp_id}: {e}", file=sys.stderr)

       # 5. Validate dependencies (existing logic)
       validate_dependencies(dependencies)

       # 6. Commit to main (existing logic)
       commit_tasks_to_main(feature_dir)

       print(f"✓ Finalized {len(wp_files)} work packages with dependency tracking")
   ```

**Files**:
- `src/specify_cli/cli/commands/agent/feature.py` (modify: add event emission loop)

**Validation**:
- [ ] `finalize_tasks` decorated with `@with_event_store`
- [ ] Event emitted for EACH work package file
- [ ] Payload includes: work_package_id, title, dependencies, subtasks
- [ ] Test: Run `spec-kitty agent feature finalize-tasks`, verify N WPCreated events (N = WP count)

**Edge Cases**:
- No WP files found: No events emitted (expected)
- WP frontmatter parsing fails: Skip that WP, log warning, continue
- Event emission fails for one WP: Log warning, continue with remaining WPs

**Parallel?**: Yes - Can implement in parallel with T016-T017 (different integration points)

---

## Test Strategy

**No separate test files** (constitution: tests not explicitly requested).

**Validation approach**:
1. **T013-T014**: Unit test - `store.emit()` creates event, writes JSONL, saves clock
2. **T015**: Decorator test - `@with_event_store` injects EventStore parameter
3. **T016**: Integration test - `move_task` emits `WPStatusChanged` event
4. **T017**: Integration test - `setup_spec` emits `SpecCreated` event
5. **T018**: Integration test - `finalize_tasks` emits multiple `WPCreated` events

**End-to-end integration test**:
```bash
# Setup fresh project
cd /tmp/test-e2e
git init
spec-kitty init

# Create feature
spec-kitty agent feature setup-spec --slug 999-test-feature

# Generate tasks (stub WP files for testing)
mkdir -p kitty-specs/999-test-feature/tasks
echo "---\nwork_package_id: WP01\ntitle: Test WP\n---" > kitty-specs/999-test-feature/tasks/WP01-test.md

# Finalize tasks
spec-kitty agent feature finalize-tasks

# Move WP
cd kitty-specs/999-test-feature
spec-kitty agent tasks move-task WP01 --to doing

# Verify events
cat ../../.kittify/events/$(date +%Y-%m-%d).jsonl | jq '.event_type'
# Should show: "SpecCreated", "WPCreated", "WPStatusChanged"

echo "✓ End-to-end test passed: All events emitted"
```

---

## Risks & Mitigations

### Risk 1: Event emission adds >15ms latency

**Impact**: Violates performance goal (FR-043: CLI < 2 seconds)

**Mitigation**:
- T014 benchmark validates <15ms target
- Synchronous write prioritizes reliability (validated in planning)
- 15ms overhead is 0.75% of 2-second budget (acceptable)

### Risk 2: EventStore initialization fails in commands

**Impact**: Commands crash with cryptic errors

**Mitigation**:
- T013 raises RuntimeError with clear message if library missing
- T015 decorator propagates error immediately (early failure)
- T016-T018 wrap emit() in try/except (log warning, continue)

### Risk 3: Integration breaks existing command behavior

**Impact**: Commands fail after adding event emission

**Mitigation**:
- T016-T018 use best-effort pattern (warning on failure, don't crash)
- Event emission happens AFTER state change (doesn't block operation)
- Integration test validates commands still work end-to-end

---

## Definition of Done Checklist

- [ ] T013: EventStore class implemented with emit() method
- [ ] T013: Initialization handles directories, clock, file writer
- [ ] T014: emit() ticks clock, writes JSONL, saves clock, returns Event
- [ ] T014: Benchmark shows <15ms average latency
- [ ] T015: `@with_event_store` decorator injects EventStore parameter
- [ ] T015: Repo root detection via git rev-parse
- [ ] T016: `move_task` emits WPStatusChanged events
- [ ] T016: Event payload includes old_status and new_status
- [ ] T017: `setup_spec` emits SpecCreated events
- [ ] T017: Event payload includes title and mission
- [ ] T018: `finalize_tasks` emits WPCreated event for each WP
- [ ] T018: Event payload includes dependencies and subtasks
- [ ] End-to-end test passes (SpecCreated → WPCreated → WPStatusChanged)

---

## Review Guidance

**Key Acceptance Checkpoints**:

1. **T013-T014 - EventStore API**:
   - ✓ `emit()` method signature matches data-model.md spec
   - ✓ Clock incremented before event creation
   - ✓ JSONL written before clock saved (consistency)
   - ✓ Performance benchmark shows <15ms

2. **T015 - AOP Decorator**:
   - ✓ Decorator injects `event_store` keyword argument
   - ✓ Works with Typer CLI framework
   - ✓ Clear error if not in git repository

3. **T016 - move_task Integration**:
   - ✓ Event emitted AFTER frontmatter update
   - ✓ Payload matches WPStatusChangedPayload.json schema
   - ✓ Best-effort pattern (warning on failure)

4. **T017 - setup_spec Integration**:
   - ✓ Event emitted AFTER spec.md created
   - ✓ Title extracted from spec.md (or placeholder)

5. **T018 - finalize_tasks Integration**:
   - ✓ Event emitted for EACH work package
   - ✓ Dependencies included in payload
   - ✓ Failures don't block finalization

**Reviewers should**:
- Run end-to-end test (verify all 3 event types emitted)
- Check JSONL files (verify correct JSON structure)
- Measure latency (verify <15ms average)

---

## Activity Log

- 2026-01-27T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

## Implementation Command

This WP depends on WP02. Implement from WP02's branch:

```bash
spec-kitty implement WP03 --base WP02
```

This will create workspace: `.worktrees/025-cli-event-log-integration-WP03/` branched from WP02.
