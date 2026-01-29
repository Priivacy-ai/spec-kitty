# Quickstart: CLI Event Log Integration

**Target Audience**: Developers implementing event log functionality
**Prerequisites**: spec-kitty 2.x installed, spec-kitty-events library integrated
**Estimated Time**: 15 minutes

## Overview

This quickstart demonstrates how to:
1. Emit events when workflow state changes
2. Read events to reconstruct current state
3. Query event history with filters
4. Handle conflicts and errors

---

## Setup

### Install Dependencies

```bash
# Clone spec-kitty (2.x branch)
git checkout 2.x

# Install with spec-kitty-events dependency
pip install -e .

# Verify installation
spec-kitty --version  # Should show 2.x version
```

### Initialize Project

```bash
# Create new project
mkdir my-project && cd my-project
git init

# Initialize spec-kitty (creates .kittify/ directory)
spec-kitty init

# Verify event log directory created
ls -la .kittify/events/  # Should exist but be empty initially
```

---

## Usage Examples

### Example 1: Emit Event on Status Change

**Scenario**: User moves work package from "planned" to "doing"

**Command**:
```bash
spec-kitty agent tasks move-task WP01 --to doing
```

**What Happens Internally**:
```python
# In src/specify_cli/cli/commands/agent.py

from specify_cli.events.middleware import with_event_store

@with_event_store
def move_task(wp_id: str, lane: str, event_store: EventStore):
    # 1. Load current WP state
    current_status = load_wp_status(wp_id)

    # 2. Validate transition
    if not is_valid_transition(current_status, lane):
        raise ValidationError(f"Cannot transition from {current_status} to {lane}")

    # 3. Update frontmatter (existing logic)
    update_wp_frontmatter(wp_id, status=lane)

    # 4. Emit event (NEW)
    event_store.emit(
        event_type="WPStatusChanged",
        entity_id=wp_id,
        entity_type="WorkPackage",
        actor=get_current_agent(),
        causation_id=f"cmd-{uuid.uuid4()}",
        payload={
            "feature_slug": get_current_feature(),
            "old_status": current_status,
            "new_status": lane,
            "reason": "User requested transition"
        }
    )

    print(f"✓ Moved {wp_id} to {lane}")
```

**Result**:
```bash
# Event appended to .kittify/events/2026-01-27.jsonl
cat .kittify/events/2026-01-27.jsonl
```

```json
{
  "event_id": "01HN3R5K8D1234567890ABCDEF",
  "event_type": "WPStatusChanged",
  "event_version": 1,
  "lamport_clock": 1,
  "entity_id": "WP01",
  "entity_type": "WorkPackage",
  "timestamp": "2026-01-27T10:30:00Z",
  "actor": "claude-implementer",
  "causation_id": "cmd-abc123",
  "correlation_id": null,
  "payload": {
    "feature_slug": "025-cli-event-log-integration",
    "old_status": "planned",
    "new_status": "doing",
    "reason": "User requested transition"
  }
}
```

**Clock State Updated**:
```bash
cat .kittify/clock.json
```

```json
{
  "value": 2,
  "last_updated": "2026-01-27T10:30:00Z"
}
```

---

### Example 2: Read Status from Event Log

**Scenario**: User checks project status

**Command**:
```bash
spec-kitty status
```

**What Happens Internally**:
```python
# In src/specify_cli/cli/commands/status.py

from specify_cli.events.middleware import with_event_store

@with_event_store
def status(feature: str | None, event_store: EventStore):
    # 1. Read all WPStatusChanged events for current feature
    events = event_store.read(
        event_type="WPStatusChanged",
        # entity_id not specified → reads all WPs
    )

    # 2. Reconstruct status for each WP
    wp_statuses = {}
    for event in sorted(events, key=lambda e: e.lamport_clock):
        wp_id = event.entity_id
        new_status = event.payload["new_status"]
        wp_statuses[wp_id] = new_status

    # 3. Display kanban board
    display_kanban(wp_statuses)
```

**Output**:
```
┌─────────────────────────────────────────────────────┐
│ Feature: 025-cli-event-log-integration              │
├─────────────┬─────────────┬─────────────┬───────────┤
│ Planned     │ Doing       │ For Review  │ Done      │
├─────────────┼─────────────┼─────────────┼───────────┤
│ WP02        │ WP01 ← YOU  │ WP03        │           │
│ WP04        │             │             │           │
└─────────────┴─────────────┴─────────────┴───────────┘

Progress: ▓▓▓░░░░░░░ 30% (1/4 WPs doing, 1 for_review)
```

---

### Example 3: Query Event History

**Scenario**: Developer wants to see all events for a specific WP

**Command**:
```bash
# Built-in query (future enhancement)
spec-kitty agent events query --entity WP01 --type WPStatusChanged
```

**Python API** (for programmatic access):
```python
from pathlib import Path
from specify_cli.events.store import EventStore

# Initialize event store
repo_root = Path(".")
event_store = EventStore(repo_root)

# Query events for WP01
events = event_store.read(
    entity_id="WP01",
    event_type="WPStatusChanged"
)

# Display timeline
for event in sorted(events, key=lambda e: e.lamport_clock):
    print(f"Clock {event.lamport_clock}: {event.payload['old_status']} → {event.payload['new_status']}")
```

**Output**:
```
Clock 1: planned → doing
Clock 5: doing → for_review
Clock 8: for_review → done
```

---

### Example 4: Handle Conflict (Concurrent Operations)

**Scenario**: Two agents modify WP status concurrently (simulated)

**Simulation**:
```python
# Agent A (offline, clock=5)
event_a = Event(
    event_id="01HN3R5K8D1111111111111111",
    lamport_clock=5,
    entity_id="WP03",
    event_type="WPStatusChanged",
    payload={"old_status": "doing", "new_status": "for_review"}
)

# Agent B (offline, clock=5 - same clock!)
event_b = Event(
    event_id="01HN3R5K8E2222222222222222",
    lamport_clock=5,
    entity_id="WP03",
    event_type="WPStatusChanged",
    payload={"old_status": "doing", "new_status": "rejected"}
)

# Both events written to log when agents come online
```

**Conflict Detection**:
```python
from specify_cli.events.reader import EventReader

reader = EventReader(repo_root)
events = reader.read(entity_id="WP03", event_type="WPStatusChanged")

# Group by clock
events_by_clock = {}
for event in events:
    clock = event.lamport_clock
    if clock not in events_by_clock:
        events_by_clock[clock] = []
    events_by_clock[clock].append(event)

# Detect conflict
for clock, clock_events in events_by_clock.items():
    if len(clock_events) > 1:
        print(f"⚠️ Conflict detected at clock {clock}!")
        print(f"  Events: {[e.event_id for e in clock_events]}")

        # Apply LWW merge rule
        clock_events.sort(key=lambda e: e.event_id)  # Lexicographic sort of ULIDs
        winning_event = clock_events[-1]

        print(f"  Applying LWW: Event {winning_event.event_id} wins")
        print(f"  Result: WP03 status = {winning_event.payload['new_status']}")
```

**Output**:
```
⚠️ Conflict detected at clock 5!
  Events: ['01HN3R5K8D1111111111111111', '01HN3R5K8E2222222222222222']
  Applying LWW: Event 01HN3R5K8E2222222222222222 wins
  Result: WP03 status = rejected
```

**Status Display** (shows conflict warning):
```bash
spec-kitty status
```

```
⚠️ Conflict resolved for WP03 (clock 5): 2 concurrent status changes detected.
   Applied merge rule: Last-Write-Wins (event 01HN3R5K8E2222222222222222)
   Final status: rejected
```

---

### Example 5: Error Logging (Invalid Transition)

**Scenario**: Agent attempts invalid state transition

**Command** (will fail):
```bash
spec-kitty agent tasks move-task WP01 --to done
```

**Current State**: WP01 is in "planned"
**Requested**: Move to "done"
**Valid Transitions from "planned"**: Only ["doing"]

**What Happens Internally**:
```python
from specify_cli.events.middleware import with_event_store, with_error_storage

@with_event_store
@with_error_storage
def move_task(wp_id: str, lane: str, event_store: EventStore, error_storage: ErrorStorage):
    current_status = load_wp_status(wp_id)

    if not is_valid_transition(current_status, lane):
        # Log error event
        error_storage.log(
            error_type="StateTransitionError",
            entity_id=wp_id,
            attempted_operation=f"move_task {wp_id} --to {lane}",
            reason=f"Cannot transition from '{current_status}' to '{lane}'",
            context={
                "current_status": current_status,
                "requested_status": lane,
                "valid_transitions": get_valid_transitions(current_status)
            }
        )

        # Raise error to user
        raise ValidationError(
            f"Invalid transition: {current_status} → {lane}. "
            f"Valid transitions: {get_valid_transitions(current_status)}"
        )

    # ... rest of logic
```

**Output**:
```
❌ Error: Invalid transition: planned → done
   Valid transitions from 'planned': doing
   Error logged to .kittify/errors/2026-01-27.jsonl
```

**Error Log**:
```bash
cat .kittify/errors/2026-01-27.jsonl
```

```json
{
  "error_id": "01HN3R5K8F9876543210FEDCBA",
  "error_type": "StateTransitionError",
  "entity_id": "WP01",
  "attempted_operation": "move_task WP01 --to done",
  "reason": "Cannot transition from 'planned' to 'done'",
  "timestamp": "2026-01-27T10:45:00Z",
  "context": {
    "current_status": "planned",
    "requested_status": "done",
    "valid_transitions": ["doing"]
  }
}
```

**Manus Pattern** (agent learns from error):
```python
# Future enhancement: Agent reviews error log before operating
def check_past_errors(entity_id: str) -> list[ErrorEvent]:
    """Check if similar errors occurred previously."""
    errors = error_storage.read(entity_id=entity_id, error_type="StateTransitionError")
    if errors:
        print(f"⚠️ Warning: {len(errors)} previous transition errors for {entity_id}")
        for error in errors:
            print(f"  - {error.reason}")
    return errors
```

---

### Example 6: Rebuild Index (Corruption Recovery)

**Scenario**: SQLite index becomes corrupted or out of sync

**Symptoms**:
```bash
spec-kitty status
# Output: ⚠️ Warning: Index out of sync. Rebuilding...
```

**Manual Rebuild**:
```bash
# Delete corrupted index
rm .kittify/events/index.db

# Rebuild from JSONL source of truth
spec-kitty agent events rebuild-index
```

**What Happens Internally**:
```python
from specify_cli.events.index import EventIndex

def rebuild_index(events_dir: Path):
    index = EventIndex(events_dir / "index.db")

    # 1. Drop and recreate tables
    index._drop_tables()
    index._create_tables()

    # 2. Read all JSONL files
    for jsonl_file in sorted(events_dir.glob("*.jsonl")):
        print(f"Processing {jsonl_file.name}...")

        for line in jsonl_file.read_text().splitlines():
            try:
                event = Event.from_json(line)
                index.update(event)
            except json.JSONDecodeError:
                print(f"  ⚠️ Skipping invalid JSON line")
                continue

    print("✓ Index rebuilt successfully")
```

**Output**:
```
Processing 2026-01-25.jsonl... (12 events)
Processing 2026-01-26.jsonl... (27 events)
Processing 2026-01-27.jsonl... (8 events)
✓ Index rebuilt successfully (47 total events)
```

---

## Integration with Existing Commands

### `/spec-kitty.specify` → Emits `SpecCreated`

```bash
/spec-kitty.specify
# Input: Create event log integration feature

# Event emitted:
{
  "event_type": "SpecCreated",
  "entity_id": "025-cli-event-log-integration",
  "entity_type": "FeatureSpec",
  "payload": {
    "title": "CLI Event Log Integration",
    "mission": "software-dev",
    "created_by": "claude-planner"
  }
}
```

### `/spec-kitty.tasks` → Emits `WPCreated` (multiple)

```bash
/spec-kitty.tasks
# Generates WP01, WP02, WP03, ...

# Events emitted (one per WP):
{
  "event_type": "WPCreated",
  "entity_id": "WP01",
  "payload": {
    "work_package_id": "WP01",
    "title": "Implement EventStore adapter",
    "dependencies": []
  }
}
```

### `/spec-kitty.implement` → Emits `WorkspaceCreated`

```bash
spec-kitty implement WP01
# Creates .worktrees/025-cli-event-log-WP01/

# Event emitted:
{
  "event_type": "WorkspaceCreated",
  "entity_id": "WP01",
  "payload": {
    "work_package_id": "WP01",
    "worktree_path": ".worktrees/025-cli-event-log-integration-WP01",
    "branch_name": "025-cli-event-log-integration-WP01"
  }
}
```

---

## Testing Event Integration

### Unit Test Example

```python
# tests/events/test_emitter.py

import pytest
from specify_cli.events.store import EventStore
from pathlib import Path

def test_emit_wp_status_changed(tmp_path: Path):
    """Test event emission for WP status change."""
    # Setup
    event_store = EventStore(tmp_path)

    # Act
    event = event_store.emit(
        event_type="WPStatusChanged",
        entity_id="WP01",
        entity_type="WorkPackage",
        actor="test-agent",
        payload={
            "feature_slug": "test-feature",
            "old_status": "planned",
            "new_status": "doing"
        }
    )

    # Assert
    assert event.event_id  # ULID generated
    assert event.lamport_clock == 1  # First event
    assert event.event_type == "WPStatusChanged"
    assert event.payload["new_status"] == "doing"

    # Verify persisted to JSONL
    jsonl_files = list((tmp_path / ".kittify" / "events").glob("*.jsonl"))
    assert len(jsonl_files) == 1

    # Verify indexed
    events = event_store.read(entity_id="WP01")
    assert len(events) == 1
    assert events[0].event_id == event.event_id
```

### Integration Test Example

```python
# tests/integration/test_event_workflow.py

def test_full_workflow_with_events(tmp_path: Path):
    """Test complete workflow: specify → tasks → implement → status."""
    # 1. Create spec
    run_command(["spec-kitty", "agent", "feature", "setup-spec"])

    # 2. Verify SpecCreated event
    event_store = EventStore(tmp_path)
    events = event_store.read(event_type="SpecCreated")
    assert len(events) == 1

    # 3. Generate tasks
    run_command(["spec-kitty", "agent", "feature", "finalize-tasks"])

    # 4. Verify WPCreated events
    wp_events = event_store.read(event_type="WPCreated")
    assert len(wp_events) > 0

    # 5. Move WP status
    run_command(["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "doing"])

    # 6. Verify WPStatusChanged event
    status_events = event_store.read(entity_id="WP01", event_type="WPStatusChanged")
    assert len(status_events) == 1
    assert status_events[0].payload["new_status"] == "doing"

    # 7. Check status command reads from events
    output = run_command(["spec-kitty", "status"])
    assert "WP01" in output
    assert "Doing" in output
```

---

## Performance Monitoring

### Measure Event Write Latency

```python
import time
from specify_cli.events.store import EventStore

def benchmark_emit():
    event_store = EventStore(Path("."))

    start = time.time()
    for i in range(100):
        event_store.emit(
            event_type="WPStatusChanged",
            entity_id=f"WP{i:02d}",
            entity_type="WorkPackage",
            actor="benchmark",
            payload={"old_status": "planned", "new_status": "doing"}
        )
    end = time.time()

    avg_latency = (end - start) / 100 * 1000  # Convert to ms
    print(f"Average event write latency: {avg_latency:.2f}ms")
    # Target: <15ms
```

### Measure Status Reconstruction Time

```python
def benchmark_status_reconstruction():
    event_store = EventStore(Path("."))

    start = time.time()
    events = event_store.read(event_type="WPStatusChanged")
    wp_statuses = {}
    for event in sorted(events, key=lambda e: e.lamport_clock):
        wp_statuses[event.entity_id] = event.payload["new_status"]
    end = time.time()

    print(f"Status reconstruction time: {(end - start) * 1000:.2f}ms")
    print(f"Events processed: {len(events)}")
    # Target: <50ms for 100 events
```

---

## Troubleshooting

### Problem: Events not appearing in log

**Check**:
```bash
# Verify .kittify/events/ directory exists
ls -la .kittify/events/

# Check file permissions
ls -l .kittify/events/*.jsonl
```

**Solution**: Ensure `.kittify/` directory is initialized:
```bash
spec-kitty init  # Recreates directory structure
```

### Problem: Clock value not incrementing

**Check**:
```bash
# Inspect clock file
cat .kittify/clock.json

# Look for write errors in logs
spec-kitty agent events debug-clock
```

**Solution**: Rebuild clock from event log:
```bash
rm .kittify/clock.json
spec-kitty agent events rebuild-clock
```

### Problem: Status command shows stale state

**Likely Cause**: Index out of sync with JSONL

**Solution**: Rebuild index:
```bash
spec-kitty agent events rebuild-index
```

### Problem: File locking errors (Windows)

**Symptom**: `IOError: [Errno 11] Resource temporarily unavailable`

**Cause**: POSIX file locking not available on this platform

**Solution**: Check WSL availability or disable file locking (development mode only):
```python
# In config
event_store = EventStore(repo_root, use_file_locking=False)
```

---

## Next Steps

After completing this quickstart:

1. **Read data-model.md**: Understand entity relationships and schema
2. **Review contracts/**: Inspect JSON schemas for event validation
3. **Explore spec-kitty-events docs**: Learn about CRDT merge rules, conflict detection
4. **Implement WP integration**: Start with WPStatusChanged event emission in commands
5. **Write tests**: Follow test examples in `tests/events/`

---

## Additional Resources

- **Architecture**: `architecture/adrs/2026-01-27-11-dual-repository-pattern.md` (Git dependency setup)
- **Research**: `kitty-specs/025-cli-event-log-integration/research.md` (design rationale)
- **Constitution**: `.kittify/memory/constitution.md` (spec-kitty-events integration requirements)
- **spec-kitty-events docs**: https://github.com/Priivacy-ai/spec-kitty-events/blob/main/README.md

---

**Questions or Issues?** Open a GitHub issue or check existing discussions.
