# Data Model: CLI Event Log Integration

**Phase**: Planning Phase 1
**Date**: 2026-01-27
**Status**: Design Complete

## Overview

This feature integrates event sourcing into the CLI using the spec-kitty-events library. The data model consists of core entities for event storage, clock management, and query optimization.

**Design Principles**:
- Events are immutable (append-only)
- JSONL files are source of truth
- SQLite index is derived state (rebuilds from JSONL)
- Lamport clocks provide causal ordering
- Entity-level LWW for conflict resolution

---

## Core Entities

### 1. Event

**Purpose**: Immutable record of state change with causal ordering metadata

**Storage**: JSONL files (`.kittify/events/YYYY-MM-DD.jsonl`)

**Schema**:
```python
@dataclass
class Event:
    event_id: str            # ULID (lexicographically sortable, timestamp-embedded)
    event_type: str          # "WPStatusChanged", "SpecCreated", "WPCreated", etc.
    event_version: int       # Schema version (starts at 1, enables evolution)
    lamport_clock: int       # Logical clock for causal ordering
    entity_id: str           # Entity affected (e.g., "WP01", "025-cli-event-log")
    entity_type: str         # "WorkPackage", "FeatureSpec", "Subtask"
    timestamp: str           # ISO 8601 UTC (for human readability, NOT ordering)
    actor: str               # Agent/user that caused event (e.g., "claude-implementer")
    causation_id: str | None # Command/operation that caused event (for idempotency)
    correlation_id: str | None # Workflow/session ID (for tracing)
    payload: dict            # Event-specific data (flexible JSON)
```

**Example** (WP status change):
```json
{
  "event_id": "01HN3R5K8D1234567890ABCDEF",
  "event_type": "WPStatusChanged",
  "event_version": 1,
  "lamport_clock": 42,
  "entity_id": "WP03",
  "entity_type": "WorkPackage",
  "timestamp": "2026-01-27T10:30:00Z",
  "actor": "claude-implementer",
  "causation_id": "cmd-abc123",
  "correlation_id": "session-xyz789",
  "payload": {
    "feature_slug": "025-cli-event-log-integration",
    "old_status": "doing",
    "new_status": "for_review",
    "reason": "Implementation complete"
  }
}
```

**Constraints**:
- `event_id` must be globally unique (ULID guarantees)
- `lamport_clock` must be monotonically increasing within project
- `event_type` must match registered type (validation on write)
- `payload` structure varies by event_type (weak schema, tolerate missing fields)

**Relationships**:
- `entity_id` references WorkPackage, FeatureSpec, or Subtask (polymorphic)
- `causation_id` enables idempotency check (reject duplicate command IDs)
- `correlation_id` groups related events (e.g., all events in implement session)

---

### 2. LamportClock

**Purpose**: Logical clock providing causal ordering without wall-clock dependency

**Storage**: JSON file (`.kittify/clock.json`)

**Schema**:
```python
@dataclass
class LamportClock:
    value: int               # Current clock value (monotonically increasing)
    last_updated: str        # ISO 8601 timestamp of last increment (metadata only)
```

**Example**:
```json
{
  "value": 42,
  "last_updated": "2026-01-27T10:30:00Z"
}
```

**Operations**:
- `tick()`: Increment clock by 1, return new value
- `update(remote_clock: int)`: Set clock to max(local_clock, remote_clock) + 1 (for sync protocol)
- `initialize()`: Set clock to 1 (on first event or corruption recovery)

**Persistence Strategy**:
- Write to file after every event emission (durability)
- Read on CLI startup (cache in memory during command execution)
- Reinitialize from max(event log clocks) + 1 if file corrupted

**Constraints**:
- Clock value must never decrease
- Clock increments are atomic (file locking during write)

---

### 3. EventStore

**Purpose**: Storage adapter for persisting events to JSONL files

**Responsibility**: Append events to daily JSONL file with atomic writes

**Implementation** (wraps spec-kitty-events library):
```python
class EventStore:
    def __init__(self, repo_root: Path):
        self.events_dir = repo_root / ".kittify" / "events"
        self.clock_file = repo_root / ".kittify" / "clock.json"
        self.clock = self._load_clock()

    def emit(self, event_type: str, entity_id: str, payload: dict, **metadata) -> Event:
        """
        Emit event with automatic Lamport clock increment.

        Returns: Persisted Event object
        Raises: IOError if write fails, ValidationError if event invalid
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
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
            **metadata
        )

        # 3. Append to JSONL file (with file locking)
        self._append_to_jsonl(event)

        # 4. Update SQLite index (inline, not async for MVP)
        self._update_index(event)

        # 5. Persist clock state
        self._save_clock()

        return event

    def read(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        since_clock: int | None = None
    ) -> list[Event]:
        """
        Read events from log, optionally filtered.

        Uses SQLite index if filters provided, otherwise reads JSONL directly.
        Returns events sorted by Lamport clock (causal order).
        """
        if entity_id or event_type or since_clock:
            return self._query_index(entity_id, event_type, since_clock)
        else:
            return self._read_all_jsonl()
```

**File Operations**:
- Daily rotation: Events append to `YYYY-MM-DD.jsonl`
- Atomic appends: POSIX advisory lock (`fcntl.flock`) during write
- Error handling: Skip invalid JSON lines with warning, continue processing

**Integration with spec-kitty-events**:
```python
# EventStore wraps library's core types
from spec_kitty_events import Event as LibEvent, LamportClock as LibClock

# Adapter pattern: translate between library and CLI types
event = LibEvent(
    clock=self.clock.tick(),
    entity_id=entity_id,
    type=event_type,
    data=payload
)
```

---

### 4. EventIndex

**Purpose**: SQLite query index for fast event filtering

**Storage**: SQLite database (`.kittify/events/index.db`)

**Schema** (SQL):
```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    lamport_clock INTEGER NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    date TEXT NOT NULL,  -- ISO date (YYYY-MM-DD) for file lookup

    INDEX idx_entity ON events(entity_id, lamport_clock),
    INDEX idx_type ON events(event_type, lamport_clock),
    INDEX idx_date ON events(date)
);
```

**Operations**:
```python
class EventIndex:
    def update(self, event: Event):
        """Insert event into index. Idempotent (ON CONFLICT IGNORE)."""
        conn = sqlite3.connect(self.index_db)
        conn.execute("""
            INSERT OR IGNORE INTO events
            (event_id, lamport_clock, entity_id, entity_type, event_type, timestamp, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.lamport_clock,
            event.entity_id,
            event.entity_type,
            event.event_type,
            event.timestamp,
            event.timestamp[:10]  # Extract YYYY-MM-DD
        ))
        conn.commit()

    def query(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        since_clock: int | None = None
    ) -> list[str]:
        """
        Query index for event IDs matching filters.
        Returns list of JSONL file dates containing matching events.
        """
        # Build WHERE clause dynamically based on filters
        # Return list of dates to load JSONL files from

    def rebuild(self, events_dir: Path):
        """Rebuild index from all JSONL files (corruption recovery)."""
        self._drop_tables()
        self._create_tables()
        for jsonl_file in sorted(events_dir.glob("*.jsonl")):
            for line in jsonl_file.read_text().splitlines():
                event = Event.from_json(line)
                self.update(event)
```

**Index Update Strategy**:
- **MVP (Phase 1)**: Synchronous (inline during emit)
- **Phase 2**: Asynchronous (background worker)

**Rebuild Triggers**:
- Index file missing: Rebuild on first read
- Index corruption detected: Delete and rebuild
- Manual rebuild: `spec-kitty agent events rebuild-index`

---

### 5. ClockStorage

**Purpose**: Persistence adapter for Lamport clock state

**Storage**: JSON file (`.kittify/clock.json`)

**Operations**:
```python
class ClockStorage:
    def load(self, clock_file: Path) -> LamportClock:
        """Load clock from file. Returns default (1) if missing."""
        if not clock_file.exists():
            return LamportClock(value=1, last_updated=now())

        data = json.loads(clock_file.read_text())
        return LamportClock(**data)

    def save(self, clock: LamportClock, clock_file: Path):
        """Save clock to file (atomic write via temp file + rename)."""
        temp_file = clock_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(asdict(clock)))
        temp_file.rename(clock_file)  # Atomic on POSIX
```

**Corruption Recovery**:
```python
def recover_clock(events_dir: Path) -> LamportClock:
    """Rebuild clock from max value in event log."""
    max_clock = 0
    for jsonl_file in events_dir.glob("*.jsonl"):
        for line in jsonl_file.read_text().splitlines():
            event = Event.from_json(line)
            max_clock = max(max_clock, event.lamport_clock)

    return LamportClock(value=max_clock + 1, last_updated=now())
```

---

### 6. ErrorStorage

**Purpose**: Storage adapter for error events (Manus pattern - learning from failures)

**Storage**: JSONL files (`.kittify/errors/YYYY-MM-DD.jsonl`)

**Schema**:
```python
@dataclass
class ErrorEvent:
    error_id: str            # ULID
    error_type: str          # "ValidationError", "GateFailure", "StateTransitionError"
    entity_id: str           # Entity that triggered error
    attempted_operation: str # What the agent/user tried to do
    reason: str              # Why it failed (human-readable)
    timestamp: str           # ISO 8601 UTC
    context: dict            # Additional debugging info
```

**Example** (invalid state transition):
```json
{
  "error_id": "01HN3R5K8E9876543210FEDCBA",
  "error_type": "StateTransitionError",
  "entity_id": "WP03",
  "attempted_operation": "move_task WP03 --to done",
  "reason": "Cannot transition from 'planned' to 'done' (must go through 'doing' and 'for_review')",
  "timestamp": "2026-01-27T10:30:00Z",
  "context": {
    "current_status": "planned",
    "requested_status": "done",
    "valid_transitions": ["doing"]
  }
}
```

**Usage**:
- Agent reviews error log before attempting operations (learn from past mistakes)
- Dashboard displays recent errors for debugging
- Analytics: Track most common error types

---

## Event Types

### Workflow State Events

| Event Type | Emitted When | Payload Schema |
|------------|--------------|----------------|
| `WPStatusChanged` | Work package moves between lanes | `{feature_slug, old_status, new_status, reason}` |
| `SpecCreated` | Feature specification created | `{feature_slug, title, mission}` |
| `WPCreated` | Work package generated | `{work_package_id, title, dependencies}` |
| `WorkspaceCreated` | Worktree initialized for WP | `{work_package_id, worktree_path, branch_name}` |
| `SubtaskCompleted` | Subtask checked off | `{work_package_id, subtask_index, subtask_text}` |

### Gate Events

| Event Type | Emitted When | Payload Schema |
|------------|--------------|----------------|
| `GateCreated` | Gate registered for WP | `{work_package_id, gate_type, gate_id}` |
| `GateResultChanged` | Gate status updated | `{gate_id, old_status, new_status, result_data}` |

### Future Events (Phase 2 - CLI ↔ Django Sync)

| Event Type | Emitted When | Payload Schema |
|------------|--------------|----------------|
| `EventSyncedToServer` | Event successfully uploaded | `{event_ids: list[str], sync_timestamp}` |
| `ConflictDetected` | Concurrent modification detected | `{entity_id, local_clock, remote_clock, merge_strategy}` |
| `ConflictResolved` | Merge rule applied | `{entity_id, resolution, winning_event_id}` |

---

## State Reconstruction

**Current State = Replay All Events in Causal Order**

```python
def reconstruct_wp_status(wp_id: str, event_store: EventStore) -> str:
    """Derive current WorkPackage status from event history."""
    events = event_store.read(
        entity_id=wp_id,
        event_type="WPStatusChanged"
    )

    # Sort by Lamport clock (causal order)
    events.sort(key=lambda e: e.lamport_clock)

    # Replay events to derive current state
    current_status = "planned"  # Default initial state
    for event in events:
        current_status = event.payload["new_status"]

    return current_status
```

**Optimization (Phase 2 - Snapshotting)**:
```python
def reconstruct_wp_status_optimized(wp_id: str, event_store: EventStore) -> str:
    """Use snapshot + replay events since snapshot."""
    snapshot = load_snapshot(wp_id)
    if snapshot:
        events = event_store.read(
            entity_id=wp_id,
            since_clock=snapshot.lamport_clock
        )
        current_status = snapshot.status
    else:
        events = event_store.read(entity_id=wp_id)
        current_status = "planned"

    for event in events:
        if event.event_type == "WPStatusChanged":
            current_status = event.payload["new_status"]

    return current_status
```

---

## Conflict Resolution

**Scenario**: Two agents concurrently change WP status (offline operations)

```python
def detect_and_resolve_conflict(event_store: EventStore):
    """Apply LWW merge rule for concurrent WPStatusChanged events."""
    events = event_store.read(entity_id="WP03", event_type="WPStatusChanged")

    # Group events by Lamport clock
    events_by_clock = {}
    for event in events:
        clock = event.lamport_clock
        if clock not in events_by_clock:
            events_by_clock[clock] = []
        events_by_clock[clock].append(event)

    # Check for concurrent events (same clock value)
    for clock, clock_events in events_by_clock.items():
        if len(clock_events) > 1:
            # Conflict detected!
            # Apply LWW: Latest event_id wins (lexicographic sort of ULIDs)
            clock_events.sort(key=lambda e: e.event_id)
            winning_event = clock_events[-1]

            logger.warning(
                f"Conflict detected for WP03 at clock {clock}. "
                f"Applying LWW: event {winning_event.event_id} wins."
            )

            # Use winning event's payload for state
            return winning_event.payload["new_status"]
```

**Note**: Conflicts are rare in CLI use case (single user per project). This logic is foundation for Phase 2 sync protocol.

---

## Entity Relationships

```
┌─────────────────┐
│   EventStore    │
│                 │
│  - events_dir   │◄───┐
│  - clock        │    │
└────────┬────────┘    │
         │             │
         │ emits       │ queries
         │             │
         ▼             │
┌─────────────────┐    │
│      Event      │────┘
│                 │
│  - event_id     │
│  - lamport_clock│──────┐
│  - entity_id    │      │
│  - payload      │      │ indexes
└─────────────────┘      │
                         ▼
                  ┌─────────────────┐
                  │   EventIndex    │
                  │  (SQLite)       │
                  │                 │
                  │  - event_id PK  │
                  │  - entity_id    │
                  │  - lamport_clock│
                  └─────────────────┘

┌─────────────────┐
│  LamportClock   │
│                 │
│  - value        │◄─── persisted by ─── ClockStorage
└─────────────────┘

┌─────────────────┐
│  ErrorStorage   │
│                 │
│  - errors_dir   │─── emits ───► ErrorEvent
└─────────────────┘
```

---

## Validation Rules

### Event Validation (on emit)
- `event_id` must be valid ULID format
- `event_type` must be registered type (validate against enum)
- `entity_id` must not be empty
- `lamport_clock` must be > previous max
- `payload` must be valid JSON (no circular references)

### State Transition Validation (before emit)
- Valid transitions defined per entity type (e.g., WP: planned → doing → for_review → done)
- Dependencies checked (Validator pattern from Jira research)
- Gates checked (e.g., CI must pass before for_review → done)

### Index Integrity
- All events in JSONL must have corresponding index entry
- Index rebuild available if mismatch detected: `spec-kitty agent events rebuild-index`

---

## Performance Characteristics

**Write Performance**:
- Event emission: ~10-15ms (JSONL write 5-10ms + SQLite index 2-5ms)
- Lamport clock persist: ~1-2ms (small JSON file)
- Daily file rotation: ~0ms (just change filename)

**Read Performance**:
- Query with index: <100ms for 1000 events (SQLite indexed query)
- Full replay without index: ~500ms for 1000 events (read all JSONL)
- Status reconstruction: ~50ms (read + replay for single WP)

**Storage Growth**:
- Event size: ~300-500 bytes per event (JSON overhead)
- Expected volume: 100-500 events per feature (spec → tasks → review → done)
- Annual growth: ~10-50MB for active project (100-500 events/month)

**Scalability Limits** (Phase 1):
- Up to 10,000 events before index queries degrade (SQLite limit)
- Up to 1,000 events per WP before snapshotting needed (replay time)
- Daily JSONL files up to 1MB each (Git merge-friendly)

---

## Migration Notes

**From 1.x YAML logs → 2.x event logs** (deferred to future feature):

1. Parse YAML activity logs (`.kittify/activity.yaml`)
2. Generate synthetic events with retroactive Lamport clocks
3. Write to JSONL files with `migrated: true` flag in metadata
4. Rebuild SQLite index from migrated events
5. Archive YAML logs (don't delete - audit trail)

**Event Schema Evolution** (when V2 needed):

1. Add new event_version=2 with updated payload schema
2. Write upcaster function: `V1Event → V2Event`
3. Read path handles both versions (weak schema tolerance)
4. Gradually migrate events on read (lazy migration)

---

## Testing Strategy

### Unit Tests
- Event serialization/deserialization (JSON round-trip)
- Lamport clock increment atomicity
- JSONL append with file locking
- SQLite index queries (filtered reads)
- Conflict detection logic

### Integration Tests
- End-to-end: `move_task` command emits event → status reads event → kanban board updated
- Corruption recovery: Delete clock.json → rebuild from event log
- Index rebuild: Delete index.db → rebuild from JSONL files
- Daily rotation: Emit events across simulated day boundary

### Performance Tests
- Benchmark event write latency (target: <15ms)
- Benchmark status reconstruction (target: <50ms for 100 events)
- Benchmark index query (target: <100ms for 1000 events)

---

## Security & Privacy

**Event Immutability**: Events are append-only. No updates or deletes (prevents audit trail tampering).

**Sensitive Data**: Events should NOT contain:
- Credentials or secrets
- PII (personally identifiable information)
- API keys or tokens

**Access Control**: File permissions (`.kittify/` directory):
- Owner: Read/write
- Group: Read-only (for team collaboration)
- Other: No access

**Future (Phase 2 - Server Sync)**: Events synced to server are encrypted at rest (server-side responsibility).

---

## Summary

This data model provides a robust foundation for event sourcing in the CLI:
- ✅ Immutable event log with causal ordering (Lamport clocks)
- ✅ Query optimization via SQLite index (derived state)
- ✅ Corruption recovery (rebuild from JSONL source of truth)
- ✅ Conflict detection for concurrent operations (foundation for sync protocol)
- ✅ Error logging for agent learning (Manus pattern)

**Next Steps**: Create event schema contracts in `contracts/` directory.
