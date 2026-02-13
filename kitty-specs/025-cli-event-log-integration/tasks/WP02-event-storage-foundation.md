---
work_package_id: WP02
title: Event Storage Foundation (Entities & File I/O)
lane: "done"
dependencies: []
base_branch: 2.x
base_commit: 3b415176a6615d2626900cab184d6d2e8307b36b
created_at: '2026-01-30T10:20:52.401966+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Core Event Infrastructure
assignee: ''
agent: "codex"
shell_pid: "14744"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-27T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Event Storage Foundation (Entities & File I/O)

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you start addressing feedback.
- **Report progress**: Update the Activity Log as you address each feedback item.

---

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-30

# WP02 Review Feedback - Round 2

**Reviewer**: claude-reviewer-2
**Date**: 2026-01-30
**Status**: ❌ Changes Requested

## Issue: Incomplete Migration - Missing Essential Methods

**Problem**: The architectural fix (moving from types.py to adapter.py) was done correctly in terms of file structure and imports, BUT the essential methods from the original types.py classes were not added to the adapter classes.

**Missing from Event class in adapter.py**:
1. `to_json()` method - used by file_io.py line 36
2. `from_json()` classmethod - needed for deserialization
3. `__post_init__()` validation - validates event fields

**Missing from LamportClock class in adapter.py**:
1. `initialize()` method - sets clock to 1
2. `to_dict()` method - used by ClockStorage for JSON serialization
3. `from_dict()` classmethod - used by ClockStorage for deserialization
4. `__post_init__()` validation - validates clock value >= 1

**Evidence of breakage**:
```
$ python3 -c "from specify_cli.events import Event, generate_ulid; e = Event(...); e.to_json()"
AttributeError: 'Event' object has no attribute 'to_json'
```

The integration test fails at file_io.py:36 because `event.to_json()` doesn't exist.

---

## How to Fix

Add the missing methods to adapter.py. Here's what needs to be added:

### For Event class (add after `to_lib_event()` method):

```python
def to_json(self) -> str:
    """Serialize event to JSON (for JSONL file)."""
    from dataclasses import asdict
    import json
    return json.dumps(asdict(self), ensure_ascii=False)

@classmethod
def from_json(cls, json_str: str) -> "Event":
    """Deserialize event from JSON."""
    import json
    data = json.loads(json_str)
    return cls(**data)

def __post_init__(self) -> None:
    """Validate event after creation."""
    if not self.event_id:
        raise ValueError("event_id cannot be empty")
    if not self.event_type:
        raise ValueError("event_type cannot be empty")
    if not self.entity_id:
        raise ValueError("entity_id cannot be empty")
    if self.lamport_clock < 1:
        raise ValueError(f"lamport_clock must be >= 1, got {self.lamport_clock}")
```

### For LamportClock class (add after `update()` method):

```python
def initialize(self) -> int:
    """Initialize clock to 1 and return initial value."""
    self.value = 1
    self.last_updated = datetime.now(timezone.utc).isoformat()
    return self.value

def to_dict(self) -> dict[str, Any]:
    """Serialize clock to dict (for JSON persistence)."""
    return {"value": self.value, "last_updated": self.last_updated}

@classmethod
def from_dict(cls, data: dict[str, Any]) -> "LamportClock":
    """Deserialize clock from dict."""
    return cls(value=data["value"], last_updated=data["last_updated"])

def __post_init__(self) -> None:
    """Validate clock after creation."""
    if self.value < 1:
        raise ValueError(f"Clock value must be >= 1, got {self.value}")
```

### Verification

After adding these methods, run this test to verify everything works:

```bash
python3 << 'ENDPY'
import sys
sys.path.insert(0, 'src')

from specify_cli.events import Event, LamportClock, generate_ulid
from datetime import datetime, timezone

# Test Event serialization
event = Event(
    event_id=generate_ulid(),
    event_type="Test",
    event_version=1,
    lamport_clock=1,
    entity_id="WP01",
    entity_type="WorkPackage",
    timestamp=datetime.now(timezone.utc).isoformat(),
    actor="test",
    causation_id=None,
    correlation_id=None,
    payload={}
)

json_str = event.to_json()
event2 = Event.from_json(json_str)
assert event.event_id == event2.event_id
print("✓ Event to_json/from_json works")

# Test LamportClock serialization
clock = LamportClock(value=5, last_updated=datetime.now(timezone.utc).isoformat())
clock_dict = clock.to_dict()
clock2 = LamportClock.from_dict(clock_dict)
assert clock.value == clock2.value
print("✓ LamportClock to_dict/from_dict works")

# Test initialize
clock.initialize()
assert clock.value == 1
print("✓ LamportClock initialize() works")

print("\nAll methods verified!")
ENDPY
```

---

## What's Working

**Good news**: The architectural structure is now correct!
- ✅ types.py deleted (duplicate removed)
- ✅ Imports updated to use adapter
- ✅ generate_ulid() moved to adapter
- ✅ __init__.py exports correct

The ONLY issue is that the methods weren't copied over when migrating from types.py to adapter.py.

---

## Root Cause Analysis

This happened because:
1. Original types.py had complete Event/LamportClock implementations
2. When deleting types.py, the implementer correctly updated imports
3. BUT forgot that adapter.py's Event/LamportClock were originally just adapter stubs
4. The adapter classes only had `from_lib_event()` and `to_lib_event()` methods
5. They never had the serialization, validation, and utility methods

**Solution**: Copy the missing methods from the deleted types.py into adapter.py.

---

## Dependent WP Warning

WP03 depends on WP02. Once this is fixed, ensure WP03 implementers know that:
- Event has `to_json()`, `from_json()`, `__post_init__()`
- LamportClock has `initialize()`, `to_dict()`, `from_dict()`, `__post_init__()`
- All imports should be from `specify_cli.events.adapter`


## Critical Issue: Architectural Violation - Duplicate Event/LamportClock Classes

**Problem**: WP02 created a new `types.py` module with Event and LamportClock classes, but WP01 already provides these through `adapter.py`. This creates two different class hierarchies and violates the adapter pattern established in WP01.

**Evidence**:
```python
# These are TWO DIFFERENT classes (not the same object):
from specify_cli.events.adapter import Event as AdapterEvent
from specify_cli.events.types import Event as TypesEvent

# AdapterEvent is not TypesEvent  <-- Different classes!
```

**Import confusion**:
- `__init__.py` exports Event from `adapter`
- `clock_storage.py` and `file_io.py` import Event from `types`
- This means different parts of the codebase use incompatible Event objects

**Why this violates the architecture**:
1. WP01 established the adapter pattern for loose coupling with spec-kitty-events library
2. All CLI code should use `specify_cli.events.adapter.Event` and `LamportClock`
3. Creating parallel `types.py` classes bypasses the adapter layer without justification
4. Creates maintenance burden (two places to update if Event schema changes)

**How to fix**:

1. **Delete the duplicate types module**:
   ```bash
   rm src/specify_cli/events/types.py
   ```

2. **Move generate_ulid() to adapter.py**:
   - Add `generate_ulid()` function and `_encode_base32()` helper to `adapter.py`
   - These are utilities, not types, so they belong with the adapter

3. **Update all imports**:
   ```python
   # In clock_storage.py and file_io.py, change:
   from specify_cli.events.types import Event, LamportClock  # ❌ DELETE THIS
   
   # To:
   from specify_cli.events.adapter import Event, LamportClock, generate_ulid  # ✅ USE THIS
   ```

4. **Verify no import errors**:
   ```bash
   python3 -c "from specify_cli.events import Event, LamportClock, generate_ulid; print('OK')"
   ```

**Functional note**: All 12 subtasks (T006-T012) are functionally complete. The ONLY issue is this architectural violation. Once fixed, WP02 will be ready for approval.

**Dependent WP warning**: WP03 depends on WP02. Once this is fixed and merged, WP03 implementers should ensure they use `specify_cli.events.adapter.Event`, not a non-existent `types.Event`.

---

## Implementation Quality (Otherwise Excellent)

**What's working well**:
- ✅ All 11 Event fields match data-model.md specification
- ✅ ULID generation produces valid 26-character identifiers
- ✅ LamportClock implements tick(), update(), initialize() correctly
- ✅ ClockStorage uses atomic writes (temp file + rename)
- ✅ POSIX file locking implemented with fcntl.flock()
- ✅ Windows fallback (best-effort without locking)
- ✅ Daily rotation works (events go to YYYY-MM-DD.jsonl files)
- ✅ Clock recovery scans event log and returns max+1 correctly
- ✅ Directory initialization is idempotent
- ✅ Integration test passes (events written, clock persisted, recovery works)

**Code quality**:
- Clean, readable implementation
- Proper error handling
- Good docstrings
- Follows Python conventions

**Test results**:
- Integration test passes (5 events emitted, clock persistence verified)
- Clock recovery test passes (value=7 is correct: max_clock=6, recovery=6+1=7)
- ULID generation produces valid identifiers

Once the architectural issue is resolved, this will be an excellent implementation.


## Objectives & Success Criteria

**Primary Goal**: Implement core entities (Event, LamportClock, ClockStorage) and JSONL file operations with atomic writes.

**Success Criteria**:
- ✅ Event dataclass matches schema in data-model.md (ULID, Lamport clock, entity metadata)
- ✅ LamportClock provides tick() operation with persistence
- ✅ JSONL append uses POSIX file locking (atomic writes, no race conditions)
- ✅ Daily file rotation creates new YYYY-MM-DD.jsonl files automatically
- ✅ Clock corruption recovery rebuilds from event log max + 1
- ✅ `.kittify/events/` and `.kittify/errors/` directories initialized on first use

**Priority**: P1 (US1 dependency)

**User Story**: US1 - Event Emission on Workflow State Changes (partial - storage layer)

**Independent Test**:
```python
from specify_cli.events.types import Event, LamportClock
from specify_cli.events.file_io import append_event_to_jsonl
from pathlib import Path

# Create test event
clock = LamportClock(value=1, last_updated="2026-01-27T10:00:00Z")
event = Event(
    event_id="01HN3R5K8D1234567890ABCDEF",
    event_type="WPStatusChanged",
    event_version=1,
    lamport_clock=clock.tick(),
    entity_id="WP01",
    entity_type="WorkPackage",
    timestamp="2026-01-27T10:00:00Z",
    actor="test",
    causation_id="test-cmd",
    correlation_id=None,
    payload={"old_status": "planned", "new_status": "doing"}
)

# Append to JSONL
test_dir = Path("/tmp/test-events")
append_event_to_jsonl(event, test_dir)

# Verify file created
assert (test_dir / "2026-01-27.jsonl").exists()
print("✓ Event written successfully")
```

---

## Context & Constraints

### ⚠️ CRITICAL: Target Branch

**This work package MUST be implemented on the `2.x` branch (NOT main).**

Verify you're on 2.x:
```bash
git branch --show-current  # Must output: 2.x
```

If you're not on 2.x, the implementation command at the bottom will create the worktree from the wrong branch. **Stop and switch to 2.x before running `spec-kitty implement WP02 --base WP01`.**

### Prerequisites

- **WP01 complete**: spec-kitty-events library installed and adapter layer available
- **Data model**: `kitty-specs/025-cli-event-log-integration/data-model.md`
- **JSON schemas**: `kitty-specs/025-cli-event-log-integration/contracts/EventV1.json`
- **Quickstart guide**: Examples in `kitty-specs/025-cli-event-log-integration/quickstart.md`

### Architectural Constraints

**From data-model.md (lines 19-76)**:
- Events are immutable (append-only)
- JSONL files are source of truth (not SQLite index)
- Lamport clocks provide causal ordering (not wall-clock timestamps)
- Daily file rotation (YYYY-MM-DD.jsonl format)

**From plan.md (Technical Context)**:
- POSIX file locking required for atomic appends
- Synchronous writes prioritized (15ms overhead acceptable)
- Cross-platform support (Linux, macOS, Windows WSL)

### Key Technical Decisions

1. **File Locking** (FR-008): Use `fcntl.flock()` on POSIX systems
2. **Daily Rotation** (US5): Check current date vs filename, create new file if different
3. **Clock Recovery** (FR-007): Rebuild from max(event_log.lamport_clock) + 1

---

## Subtasks & Detailed Guidance

### Subtask T006 – Create Event dataclass with ULID, Lamport clock, entity metadata

**Purpose**: Define the core Event type matching the schema in data-model.md and contracts/EventV1.json.

**Steps**:

1. **Create types module**:
   ```python
   # src/specify_cli/events/types.py (new file)

   from dataclasses import dataclass, asdict
   from typing import Any
   import json

   @dataclass
   class Event:
       """
       Immutable record of state change with causal ordering metadata.

       Schema matches data-model.md (lines 28-42) and contracts/EventV1.json.
       """
       event_id: str            # ULID (lexicographically sortable)
       event_type: str          # "WPStatusChanged", "SpecCreated", etc.
       event_version: int       # Schema version (starts at 1)
       lamport_clock: int       # Logical clock for causal ordering
       entity_id: str           # Entity affected (e.g., "WP01")
       entity_type: str         # "WorkPackage", "FeatureSpec", "Subtask"
       timestamp: str           # ISO 8601 UTC (human readability, NOT ordering)
       actor: str               # Agent/user that caused event
       causation_id: str | None   # Command ID (idempotency check)
       correlation_id: str | None # Session ID (tracing)
       payload: dict[str, Any]    # Event-specific data

       def to_json(self) -> str:
           """Serialize event to JSON (for JSONL file)."""
           return json.dumps(asdict(self), ensure_ascii=False)

       @classmethod
       def from_json(cls, json_str: str) -> "Event":
           """Deserialize event from JSON."""
           data = json.loads(json_str)
           return cls(**data)

       def __post_init__(self):
           """Validate event after creation."""
           # Ensure required fields are non-empty
           if not self.event_id:
               raise ValueError("event_id cannot be empty")
           if not self.event_type:
               raise ValueError("event_type cannot be empty")
           if not self.entity_id:
               raise ValueError("entity_id cannot be empty")
           if self.lamport_clock < 1:
               raise ValueError(f"lamport_clock must be >= 1, got {self.lamport_clock}")
   ```

2. **Add ULID generation utility**:
   ```python
   # In src/specify_cli/events/types.py (add to bottom)

   import time
   import random
   import string

   def generate_ulid() -> str:
       """
       Generate ULID (Universally Unique Lexicographically Sortable Identifier).

       Format: 26 characters (10 timestamp + 16 random)
       Timestamp-embedded for sortability.

       Note: For production, consider using python-ulid library.
       This is a minimal implementation.
       """
       # Timestamp part (48 bits, base32 encoded -> 10 chars)
       timestamp_ms = int(time.time() * 1000)
       timestamp_chars = _encode_base32(timestamp_ms, 10)

       # Random part (80 bits, base32 encoded -> 16 chars)
       random_value = random.getrandbits(80)
       random_chars = _encode_base32(random_value, 16)

       return timestamp_chars + random_chars

   def _encode_base32(value: int, length: int) -> str:
       """Encode integer as Crockford base32."""
       ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32
       result = []
       for _ in range(length):
           result.append(ALPHABET[value % 32])
           value //= 32
       return "".join(reversed(result))
   ```

**Files**:
- `src/specify_cli/events/types.py` (new file, ~100 lines)

**Validation**:
- [ ] Event dataclass has all 11 fields from data-model.md
- [ ] `to_json()` and `from_json()` methods for serialization
- [ ] `generate_ulid()` produces 26-character alphanumeric IDs
- [ ] `__post_init__` validates required fields and clock >= 1
- [ ] Import succeeds: `from specify_cli.events.types import Event, generate_ulid`

**Edge Cases**:
- Empty `event_id`: Raises ValueError
- Negative `lamport_clock`: Raises ValueError
- Missing payload keys: Tolerated (weak schema - payload is flexible dict)

**Parallel?**: Yes - can implement in parallel with T007-T008

---

### Subtask T007 – Create LamportClock dataclass with tick() and persistence methods

**Purpose**: Implement logical clock providing causal ordering without wall-clock dependency.

**Steps**:

1. **Add LamportClock to types module**:
   ```python
   # In src/specify_cli/events/types.py (add after Event class)

   from datetime import datetime, timezone

   @dataclass
   class LamportClock:
       """
       Logical clock for causal ordering (no wall-clock dependency).

       Schema matches data-model.md (lines 86-91).
       """
       value: int               # Current clock value (monotonically increasing)
       last_updated: str        # ISO 8601 timestamp of last increment (metadata)

       def tick(self) -> int:
           """
           Increment clock by 1 and return new value.

           This is the PRIMARY operation for event emission.
           """
           self.value += 1
           self.last_updated = datetime.now(timezone.utc).isoformat()
           return self.value

       def update(self, remote_clock: int) -> int:
           """
           Update clock to max(local, remote) + 1.

           Used for sync protocol (Phase 2 - CLI ↔ Django).
           Ensures causal ordering when merging concurrent operations.
           """
           self.value = max(self.value, remote_clock) + 1
           self.last_updated = datetime.now(timezone.utc).isoformat()
           return self.value

       def initialize(self) -> int:
           """
           Initialize clock to 1 (for new projects).

           Returns initial value.
           """
           self.value = 1
           self.last_updated = datetime.now(timezone.utc).isoformat()
           return self.value

       def to_dict(self) -> dict[str, Any]:
           """Serialize clock to dict (for JSON persistence)."""
           return {
               "value": self.value,
               "last_updated": self.last_updated
           }

       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> "LamportClock":
           """Deserialize clock from dict."""
           return cls(
               value=data["value"],
               last_updated=data["last_updated"]
           )

       def __post_init__(self):
           """Validate clock after creation."""
           if self.value < 1:
               raise ValueError(f"Clock value must be >= 1, got {self.value}")
   ```

**Files**:
- `src/specify_cli/events/types.py` (modify: add LamportClock class, ~60 lines)

**Validation**:
- [ ] `tick()` increments value by 1 and updates timestamp
- [ ] `update(remote)` sets clock to max(local, remote) + 1
- [ ] `initialize()` sets clock to 1 with current timestamp
- [ ] Serialization: `to_dict()` and `from_dict()` roundtrip correctly
- [ ] Validation: Clock value cannot be < 1

**Edge Cases**:
- Multiple rapid ticks: Each tick increments by exactly 1 (monotonic)
- Concurrent ticks from multiple processes: File locking handles (see T009)
- Clock value reaches MAX_INT: Unlikely in practice (Python ints unbounded)

**Parallel?**: Yes - can implement in parallel with T006, T008

---

### Subtask T008 – Implement ClockStorage for loading/saving clock state to JSON

**Purpose**: Persist Lamport clock state to `.kittify/clock.json` for durability across CLI invocations.

**Steps**:

1. **Create clock_storage module**:
   ```python
   # src/specify_cli/events/clock_storage.py (new file)

   from pathlib import Path
   import json
   from specify_cli.events.types import LamportClock
   from datetime import datetime, timezone

   class ClockStorage:
       """
       Persistence adapter for Lamport clock state.

       Stores clock in .kittify/clock.json with atomic writes.
       """

       def __init__(self, clock_file: Path):
           """
           Initialize storage with path to clock file.

           Args:
               clock_file: Path to .kittify/clock.json
           """
           self.clock_file = clock_file

       def load(self) -> LamportClock:
           """
           Load clock from file.

           Returns default (value=1) if file doesn't exist.
           """
           if not self.clock_file.exists():
               # Initialize new clock
               clock = LamportClock(
                   value=1,
                   last_updated=datetime.now(timezone.utc).isoformat()
               )
               return clock

           try:
               data = json.loads(self.clock_file.read_text())
               return LamportClock.from_dict(data)
           except (json.JSONDecodeError, KeyError, ValueError) as e:
               # Clock file corrupted - will trigger recovery in T011
               raise RuntimeError(
                   f"Clock file corrupted: {self.clock_file}. "
                   f"Run recovery to rebuild from event log. Error: {e}"
               )

       def save(self, clock: LamportClock) -> None:
           """
           Save clock to file with atomic write.

           Uses temp file + rename for atomicity (POSIX guarantees).
           """
           # Ensure parent directory exists
           self.clock_file.parent.mkdir(parents=True, exist_ok=True)

           # Write to temp file
           temp_file = self.clock_file.with_suffix(".tmp")
           temp_file.write_text(json.dumps(clock.to_dict(), indent=2))

           # Atomic rename (POSIX guarantees)
           temp_file.rename(self.clock_file)

       def exists(self) -> bool:
           """Check if clock file exists."""
           return self.clock_file.exists()

       def delete(self) -> None:
           """Delete clock file (for testing or recovery)."""
           if self.clock_file.exists():
               self.clock_file.unlink()
   ```

**Files**:
- `src/specify_cli/events/clock_storage.py` (new file, ~70 lines)

**Validation**:
- [ ] `load()` returns LamportClock(value=1) if file doesn't exist
- [ ] `load()` raises RuntimeError if file corrupted (invalid JSON)
- [ ] `save()` writes clock to `.kittify/clock.json`
- [ ] `save()` uses atomic write (temp file + rename)
- [ ] `save()` creates parent directory if missing

**Edge Cases**:
- File doesn't exist: Returns default clock (value=1)
- File corrupted (invalid JSON): Raises RuntimeError with helpful message
- Parent directory missing: `save()` creates it automatically
- Concurrent saves: Temp file + rename prevents corruption (atomic operation)

**Parallel?**: Yes - can implement in parallel with T006-T007

---

### Subtask T009 – Implement JSONL append with POSIX file locking (atomic writes)

**Purpose**: Provide atomic append operations to JSONL files using file locking to prevent concurrent write corruption.

**Steps**:

1. **Create file_io module**:
   ```python
   # src/specify_cli/events/file_io.py (new file)

   from pathlib import Path
   import fcntl
   import sys
   from specify_cli.events.types import Event

   class JSONLFileWriter:
       """
       Atomic JSONL file writer with POSIX file locking.

       Ensures concurrent writes don't corrupt the file.
       """

       def __init__(self, events_dir: Path):
           """
           Initialize writer with events directory.

           Args:
               events_dir: Path to .kittify/events/
           """
           self.events_dir = events_dir

       def append_event(self, event: Event) -> Path:
           """
           Append event to daily JSONL file with atomic write.

           Returns path to the file that was written.

           Uses POSIX advisory file locking (fcntl.flock) to ensure
           atomic appends when multiple processes write simultaneously.
           """
           # Ensure events directory exists
           self.events_dir.mkdir(parents=True, exist_ok=True)

           # Determine filename from timestamp (YYYY-MM-DD)
           date_str = event.timestamp[:10]  # Extract "YYYY-MM-DD"
           jsonl_file = self.events_dir / f"{date_str}.jsonl"

           # Serialize event to JSON line
           json_line = event.to_json() + "\n"

           # Append with file locking
           if sys.platform == "win32" and not self._is_wsl():
               # Windows (non-WSL) - best-effort without locking
               self._append_without_lock(jsonl_file, json_line)
           else:
               # POSIX (Linux, macOS, WSL) - use fcntl.flock
               self._append_with_lock(jsonl_file, json_line)

           return jsonl_file

       def _append_with_lock(self, file_path: Path, content: str) -> None:
           """Append content with POSIX file locking."""
           with open(file_path, "a", encoding="utf-8") as f:
               # Acquire exclusive lock (blocks if another process holds lock)
               fcntl.flock(f.fileno(), fcntl.LOCK_EX)
               try:
                   f.write(content)
                   f.flush()  # Ensure written to disk
               finally:
                   # Release lock
                   fcntl.flock(f.fileno(), fcntl.LOCK_UN)

       def _append_without_lock(self, file_path: Path, content: str) -> None:
           """Best-effort append without locking (Windows fallback)."""
           with open(file_path, "a", encoding="utf-8") as f:
               f.write(content)
               f.flush()

       def _is_wsl(self) -> bool:
           """Check if running under WSL (Windows Subsystem for Linux)."""
           try:
               with open("/proc/version", "r") as f:
                   return "microsoft" in f.read().lower()
           except FileNotFoundError:
               return False

   def append_event_to_jsonl(event: Event, events_dir: Path) -> Path:
       """
       Convenience function to append event to JSONL file.

       Args:
           event: Event to append
           events_dir: Path to .kittify/events/

       Returns:
           Path to the JSONL file that was written
       """
       writer = JSONLFileWriter(events_dir)
       return writer.append_event(event)
   ```

**Files**:
- `src/specify_cli/events/file_io.py` (new file, ~100 lines)

**Validation**:
- [ ] `append_event()` creates `.kittify/events/YYYY-MM-DD.jsonl` if missing
- [ ] Uses `fcntl.flock()` on POSIX systems (Linux, macOS, WSL)
- [ ] Falls back to best-effort on Windows (non-WSL)
- [ ] Appends JSON line with newline (`event.to_json() + "\n"`)
- [ ] Lock is acquired exclusively (blocks concurrent writes)
- [ ] Lock is released even if write fails (try/finally)

**Edge Cases**:
- Parent directory missing: `mkdir(parents=True)` creates it
- Concurrent writes: File locking serializes writes (no corruption)
- Windows non-WSL: Best-effort without locking (warn user if in multi-process setup)
- Lock timeout: `fcntl.flock()` blocks indefinitely (acceptable for CLI use case)

**Parallel?**: No - Sequential after T006 (needs Event dataclass)

---

### Subtask T010 – Implement daily file rotation logic (YYYY-MM-DD.jsonl)

**Purpose**: Ensure events are written to daily files (one file per day) for Git merge-friendliness.

**Steps**:

1. **Verify T009 implementation**:
   The daily rotation logic is already embedded in T009's `append_event()` method:
   ```python
   # Extract date from event.timestamp
   date_str = event.timestamp[:10]  # "2026-01-27T10:00:00Z" -> "2026-01-27"
   jsonl_file = self.events_dir / f"{date_str}.jsonl"
   ```

2. **Add explicit rotation test**:
   ```python
   # Test daily rotation
   from specify_cli.events.file_io import append_event_to_jsonl
   from specify_cli.events.types import Event, generate_ulid
   from pathlib import Path
   from datetime import datetime, timezone, timedelta

   events_dir = Path("/tmp/test-rotation")
   events_dir.mkdir(exist_ok=True)

   # Event for 2026-01-27
   event1 = Event(
       event_id=generate_ulid(),
       event_type="Test",
       event_version=1,
       lamport_clock=1,
       entity_id="test",
       entity_type="Test",
       timestamp="2026-01-27T10:00:00Z",
       actor="test",
       causation_id=None,
       correlation_id=None,
       payload={}
   )
   append_event_to_jsonl(event1, events_dir)

   # Event for 2026-01-28 (next day)
   event2 = Event(
       event_id=generate_ulid(),
       event_type="Test",
       event_version=1,
       lamport_clock=2,
       entity_id="test",
       entity_type="Test",
       timestamp="2026-01-28T10:00:00Z",
       actor="test",
       causation_id=None,
       correlation_id=None,
       payload={}
   )
   append_event_to_jsonl(event2, events_dir)

   # Verify two files created
   assert (events_dir / "2026-01-27.jsonl").exists()
   assert (events_dir / "2026-01-28.jsonl").exists()
   print("✓ Daily rotation working")
   ```

3. **Document behavior**:
   Add docstring comment in `file_io.py`:
   ```python
   def append_event(self, event: Event) -> Path:
       """
       Append event to daily JSONL file with atomic write.

       File naming: Events are written to files named YYYY-MM-DD.jsonl
       based on the event's timestamp (not system clock).

       Daily rotation happens automatically:
       - Events with timestamp 2026-01-27T*:*:*Z go to 2026-01-27.jsonl
       - Events with timestamp 2026-01-28T*:*:*Z go to 2026-01-28.jsonl

       This enables:
       - Git-friendly merging (append-only files per day)
       - Manageable file sizes (1 day of events per file)
       - Easy archival (delete old JSONL files)
       """
   ```

**Files**:
- `src/specify_cli/events/file_io.py` (modify: add docstring, already implemented)

**Validation**:
- [ ] Events with different dates go to different files
- [ ] Filename format is ISO date: `YYYY-MM-DD.jsonl`
- [ ] Date extracted from `event.timestamp` field (first 10 characters)
- [ ] New files created automatically when date changes

**Edge Cases**:
- Date boundary during event emission: Events use their timestamp, not system clock
- Clock skew (system time wrong): Not an issue (Lamport clock provides ordering)
- Year rollover (2026-12-31 → 2027-01-01): Works correctly (date extracted from timestamp)

**Parallel?**: No - Enhancement of T009 (must run after T009 complete)

---

### Subtask T011 – Add clock corruption recovery (rebuild from event log max)

**Purpose**: Recover Lamport clock state if `.kittify/clock.json` is corrupted or deleted.

**Steps**:

1. **Add recovery function to clock_storage.py**:
   ```python
   # In src/specify_cli/events/clock_storage.py (add new function)

   from specify_cli.events.types import Event

   def recover_clock_from_events(events_dir: Path) -> LamportClock:
       """
       Rebuild clock from event log when clock.json is corrupted.

       Scans all JSONL files in events_dir, finds max lamport_clock,
       returns new LamportClock with value = max + 1.

       Args:
           events_dir: Path to .kittify/events/

       Returns:
           Recovered LamportClock with value = max(event_clocks) + 1
       """
       max_clock = 0

       # Scan all JSONL files
       if events_dir.exists():
           for jsonl_file in sorted(events_dir.glob("*.jsonl")):
               try:
                   for line in jsonl_file.read_text().splitlines():
                       if not line.strip():
                           continue  # Skip empty lines

                       try:
                           event = Event.from_json(line)
                           max_clock = max(max_clock, event.lamport_clock)
                       except json.JSONDecodeError:
                           # Skip invalid JSON lines (graceful degradation)
                           continue
               except Exception as e:
                   # Log warning but continue scanning other files
                   import sys
                   print(f"Warning: Failed to read {jsonl_file}: {e}", file=sys.stderr)
                   continue

       # Return clock with value = max + 1
       recovered_value = max_clock + 1
       return LamportClock(
           value=recovered_value,
           last_updated=datetime.now(timezone.utc).isoformat()
       )
   ```

2. **Integrate recovery into ClockStorage.load()**:
   ```python
   # Modify ClockStorage.load() in clock_storage.py

   def load(self, events_dir: Path | None = None) -> LamportClock:
       """
       Load clock from file with automatic recovery on corruption.

       Args:
           events_dir: Optional path to events directory for recovery

       Returns:
           LamportClock (loaded from file, or recovered, or default=1)
       """
       if not self.clock_file.exists():
           # No clock file - return default
           return LamportClock(
               value=1,
               last_updated=datetime.now(timezone.utc).isoformat()
           )

       try:
           data = json.loads(self.clock_file.read_text())
           return LamportClock.from_dict(data)
       except (json.JSONDecodeError, KeyError, ValueError) as e:
           # Clock file corrupted
           import sys
           print(f"⚠️ Clock file corrupted: {self.clock_file}", file=sys.stderr)

           if events_dir and events_dir.exists():
               # Attempt recovery from event log
               print("Attempting recovery from event log...", file=sys.stderr)
               try:
                   recovered_clock = recover_clock_from_events(events_dir)
                   print(f"✓ Clock recovered: value={recovered_clock.value}", file=sys.stderr)

                   # Save recovered clock
                   self.save(recovered_clock)

                   return recovered_clock
               except Exception as recovery_error:
                   print(f"✗ Recovery failed: {recovery_error}", file=sys.stderr)

           # Fallback to default
           print("Falling back to default clock (value=1)", file=sys.stderr)
           return LamportClock(value=1, last_updated=datetime.now(timezone.utc).isoformat())
   ```

**Files**:
- `src/specify_cli/events/clock_storage.py` (modify: add recovery, ~50 lines)

**Validation**:
- [ ] `recover_clock_from_events()` scans all JSONL files in events_dir
- [ ] Finds max `lamport_clock` value across all events
- [ ] Returns LamportClock with value = max + 1
- [ ] Gracefully skips invalid JSON lines (doesn't crash)
- [ ] `ClockStorage.load()` triggers recovery if clock.json corrupted
- [ ] Recovered clock is saved back to clock.json

**Edge Cases**:
- No events exist yet: Returns LamportClock(value=1)
- Events directory doesn't exist: Returns LamportClock(value=1)
- All JSONL files corrupted: Returns LamportClock(value=1)
- Recovery fails: Falls back to LamportClock(value=1) and logs warning

**Parallel?**: No - Enhancement of T008 (must run after ClockStorage exists)

---

### Subtask T012 – Create `.kittify/events/` and `.kittify/errors/` directory initialization

**Purpose**: Ensure event storage directories are created automatically on first use.

**Steps**:

1. **Add directory initialization utility**:
   ```python
   # In src/specify_cli/events/file_io.py (add new function)

   def initialize_event_directories(repo_root: Path) -> None:
       """
       Initialize event storage directories if they don't exist.

       Creates:
       - .kittify/events/ (for event JSONL files)
       - .kittify/errors/ (for error JSONL files)

       Safe to call multiple times (idempotent).
       """
       kittify_dir = repo_root / ".kittify"
       events_dir = kittify_dir / "events"
       errors_dir = kittify_dir / "errors"

       # Create directories (parents=True, exist_ok=True)
       events_dir.mkdir(parents=True, exist_ok=True)
       errors_dir.mkdir(parents=True, exist_ok=True)

       # Optionally create .gitignore to exclude index.db (if large)
       gitignore = events_dir / ".gitignore"
       if not gitignore.exists():
           gitignore.write_text("index.db\n")
   ```

2. **Call initialization in JSONLFileWriter constructor**:
   ```python
   # Modify JSONLFileWriter.__init__() in file_io.py

   def __init__(self, events_dir: Path):
       """Initialize writer and ensure events directory exists."""
       self.events_dir = events_dir
       self.events_dir.mkdir(parents=True, exist_ok=True)
   ```

3. **Add initialization to spec-kitty init command** (optional):
   ```python
   # In src/specify_cli/cli/commands/init.py (if exists)

   from specify_cli.events.file_io import initialize_event_directories

   def init_project(repo_root: Path):
       # ... existing init logic
       initialize_event_directories(repo_root)
       print("✓ Event log directories initialized")
   ```

**Files**:
- `src/specify_cli/events/file_io.py` (modify: add initialization function)
- `src/specify_cli/cli/commands/init.py` (optional: integrate into init command)

**Validation**:
- [ ] `initialize_event_directories()` creates `.kittify/events/`
- [ ] `initialize_event_directories()` creates `.kittify/errors/`
- [ ] Function is idempotent (safe to call multiple times)
- [ ] `.gitignore` created in events/ directory (excludes index.db)
- [ ] Directories created automatically on first event write

**Edge Cases**:
- Directories already exist: No-op (exist_ok=True)
- Parent directories missing: Created automatically (parents=True)
- Permission denied: Raises PermissionError (expected, user must fix permissions)

**Parallel?**: No - Integrates with T009 (must run after file_io.py exists)

---

## Test Strategy

**No separate test files** (constitution: tests not explicitly requested).

**Validation approach**:
1. **T006**: Import test - `from specify_cli.events.types import Event, generate_ulid`
2. **T007**: Unit test - `clock.tick()` increments value, `to_dict()` roundtrip
3. **T008**: File test - Save/load clock to/from `.kittify/clock.json`
4. **T009**: Append test - Write event, verify JSONL file created
5. **T010**: Rotation test - Events on different dates go to different files
6. **T011**: Recovery test - Delete clock.json, verify recovery from event log
7. **T012**: Init test - Verify directories created automatically

**Integration test** (covers all subtasks):
```python
from specify_cli.events.types import Event, LamportClock, generate_ulid
from specify_cli.events.clock_storage import ClockStorage, recover_clock_from_events
from specify_cli.events.file_io import append_event_to_jsonl, initialize_event_directories
from pathlib import Path
from datetime import datetime, timezone

# Setup
repo_root = Path("/tmp/test-events-integration")
initialize_event_directories(repo_root)

# Create clock
clock_file = repo_root / ".kittify" / "clock.json"
storage = ClockStorage(clock_file)
clock = storage.load()

# Emit events
events_dir = repo_root / ".kittify" / "events"
for i in range(5):
    event = Event(
        event_id=generate_ulid(),
        event_type="Test",
        event_version=1,
        lamport_clock=clock.tick(),
        entity_id=f"WP{i:02d}",
        entity_type="WorkPackage",
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor="test",
        causation_id=f"cmd-{i}",
        correlation_id=None,
        payload={"test": True}
    )
    append_event_to_jsonl(event, events_dir)
    storage.save(clock)

# Verify
jsonl_files = list(events_dir.glob("*.jsonl"))
assert len(jsonl_files) > 0, "No JSONL files created"
assert clock_file.exists(), "Clock file not created"
print(f"✓ Integration test passed: {len(jsonl_files)} files, clock value={clock.value}")

# Test recovery
clock_file.unlink()  # Delete clock
recovered_clock = recover_clock_from_events(events_dir)
assert recovered_clock.value == 6, f"Expected clock=6, got {recovered_clock.value}"
print("✓ Clock recovery test passed")
```

---

## Risks & Mitigations

### Risk 1: File locking not available on Windows (non-WSL)

**Impact**: Concurrent writes may corrupt JSONL files

**Mitigation**:
- T009 detects Windows and uses best-effort (no locking)
- Document Windows WSL recommendation for multi-agent setups
- Single-agent CLI use (majority) unaffected

### Risk 2: Clock corruption occurs frequently

**Impact**: Recovery process runs often, adds latency

**Mitigation**:
- T008 uses atomic write (temp file + rename) to prevent corruption
- T011 recovery is fast (single pass through event log)
- Corrupted clock.json is unlikely in practice (atomic writes)

### Risk 3: Daily rotation creates too many files

**Impact**: Git repo grows large with many JSONL files

**Mitigation**:
- Daily rotation keeps individual files small (<1MB typically)
- Users can archive/delete old files (events are immutable)
- Future enhancement: Automatic archival after 90 days

---

## Definition of Done Checklist

- [ ] T006: Event dataclass implemented with all 11 fields
- [ ] T006: `generate_ulid()` produces valid 26-character IDs
- [ ] T007: LamportClock implements tick(), update(), initialize()
- [ ] T008: ClockStorage loads/saves clock to `.kittify/clock.json`
- [ ] T008: Atomic write using temp file + rename
- [ ] T009: JSONL append uses file locking (POSIX systems)
- [ ] T009: Falls back to best-effort on Windows
- [ ] T010: Events go to daily files (YYYY-MM-DD.jsonl)
- [ ] T011: Clock recovery scans event log and finds max + 1
- [ ] T011: ClockStorage.load() triggers recovery on corruption
- [ ] T012: `.kittify/events/` and `.kittify/errors/` created automatically
- [ ] Integration test passes (emit events, verify files + clock)

---

## Review Guidance

**Key Acceptance Checkpoints**:

1. **T006 - Event Schema**:
   - ✓ All 11 fields match data-model.md
   - ✓ `to_json()` produces valid JSON (no Python-specific types)
   - ✓ `from_json()` roundtrips correctly
   - ✓ ULID generation works (26 characters, alphanumeric)

2. **T007 - Lamport Clock**:
   - ✓ `tick()` increments by exactly 1
   - ✓ `update(remote)` uses max(local, remote) + 1 formula
   - ✓ Clock value is never < 1

3. **T008 - Clock Persistence**:
   - ✓ Atomic write (temp file + rename)
   - ✓ Graceful handling of missing/corrupted file

4. **T009 - File Locking**:
   - ✓ Uses `fcntl.flock()` on POSIX systems
   - ✓ Lock acquired exclusively (LOCK_EX)
   - ✓ Lock released in finally block

5. **T010 - Daily Rotation**:
   - ✓ Date extracted from timestamp (not system clock)
   - ✓ Filename format is ISO date (YYYY-MM-DD.jsonl)

6. **T011 - Clock Recovery**:
   - ✓ Scans all JSONL files
   - ✓ Finds max clock value
   - ✓ Returns max + 1

7. **T012 - Directory Init**:
   - ✓ Creates both events/ and errors/ directories
   - ✓ Idempotent (safe to call multiple times)

**Reviewers should**:
- Run integration test (verify events written + clock persisted)
- Test recovery (delete clock.json, verify recovery from events)
- Check file locking on POSIX system (concurrent writes don't corrupt)

---

## Activity Log

- 2026-01-27T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---
- 2026-01-30T10:16:44Z – unknown – shell_pid=28472 – lane=planned – Reset to planned - starting fresh from clean 2.x branch
- 2026-01-30T10:31:59Z – unknown – shell_pid=49716 – lane=for_review – Ready for review: implemented event storage foundation (Event/LamportClock types, ULID generator), clock persistence + recovery, JSONL append with POSIX locking + daily rotation, and event/error directory initialization.
- 2026-01-30T10:32:37Z – claude-reviewer – shell_pid=55140 – lane=doing – Started review via workflow command
- 2026-01-30T10:36:10Z – claude-reviewer – shell_pid=55140 – lane=planned – Moved to planned
- 2026-01-30T10:36:59Z – codex – shell_pid=14744 – lane=doing – Started implementation via workflow command
- 2026-01-30T10:38:48Z – codex – shell_pid=14744 – lane=doing – Acknowledged review feedback: remove duplicate types module, use adapter Event/LamportClock, move ULID generator to adapter.
- 2026-01-30T10:39:32Z – codex – shell_pid=14744 – lane=for_review – Ready for review: removed duplicate types module, moved ULID generator to adapter, and aligned storage/file IO imports to adapter Event/LamportClock.
- 2026-01-30T10:44:37Z – claude-reviewer-2 – shell_pid=60293 – lane=doing – Started review via workflow command
- 2026-01-30T10:46:31Z – claude-reviewer-2 – shell_pid=60293 – lane=planned – Moved to planned
- 2026-01-30T10:47:19Z – claude-implementer – shell_pid=61314 – lane=doing – Started implementation via workflow command
- 2026-01-30T10:49:03Z – claude-implementer – shell_pid=61314 – lane=for_review – Review feedback addressed: Added all missing methods (to_json, from_json, __post_init__, initialize, to_dict, from_dict) to Event and LamportClock classes in adapter.py. All integration tests pass.
- 2026-01-30T10:50:37Z – codex – shell_pid=14744 – lane=doing – Started review via workflow command
- 2026-01-30T10:51:39Z – codex – shell_pid=14744 – lane=done – Review passed: adapter Event/LamportClock now include serialization/validation methods, ULID generator exported, storage/file IO use adapter types; verification snippet passes.

## Implementation Command

This WP depends on WP01. Implement from WP01's branch:

```bash
spec-kitty implement WP02 --base WP01
```

This will create workspace: `.worktrees/025-cli-event-log-integration-WP02/` branched from WP01's branch.
