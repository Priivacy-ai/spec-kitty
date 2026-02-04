# Data Model: CLI Event Emission + Sync

**Feature**: 028-cli-event-emission-sync
**Date**: 2026-02-03

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           EventEmitter (Singleton)                       │
│                                                                         │
│  ┌──────────────────┐     ┌──────────────────┐     ┌────────────────┐  │
│  │   LamportClock   │     │    AuthClient    │     │   SyncConfig   │  │
│  │   (clock.json)   │     │   (Feature 027)  │     │                │  │
│  └────────┬─────────┘     └────────┬─────────┘     └───────┬────────┘  │
│           │                        │                       │           │
│           └────────────────────────┼───────────────────────┘           │
│                                    │                                    │
│                          ┌─────────▼─────────┐                         │
│                          │      Event        │                         │
│                          │   (validated)     │                         │
│                          └─────────┬─────────┘                         │
│                                    │                                    │
│              ┌─────────────────────┴─────────────────────┐             │
│              │                                           │             │
│              ▼                                           ▼             │
│  ┌───────────────────────┐                  ┌───────────────────────┐ │
│  │     OfflineQueue      │                  │    WebSocketClient    │ │
│  │      (queue.db)       │                  │      (optional)       │ │
│  └───────────────────────┘                  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Entities

### Event

Base structure for all sync events (from spec-kitty-events).

```python
@dataclass
class Event:
    event_id: str           # ULID - globally unique, time-sortable
    event_type: str         # e.g., "WPStatusChanged", "WPCreated"
    aggregate_id: str       # Entity being modified (e.g., "WP01")
    aggregate_type: str     # "WorkPackage", "Feature"
    payload: dict           # Event-specific data
    node_id: str            # Stable machine identifier
    lamport_clock: int      # Causal ordering
    causation_id: str | None  # Parent event ULID (if caused by another event)
    timestamp: str          # ISO8601 (wall clock, informational only)
    team_slug: str          # Multi-tenant routing
```

**Validation Rules**:
- `event_id`: Must be valid ULID (26 chars, base32)
- `event_type`: Must be one of defined types (see below)
- `aggregate_id`: Non-empty string
- `lamport_clock`: Non-negative integer
- `timestamp`: Valid ISO8601 format
- `team_slug`: Non-empty string (from AuthClient)

### LamportClock

Persistent counter for causal ordering.

```python
@dataclass
class LamportClock:
    value: int = 0
    node_id: str = ""

    def tick(self) -> int:
        """Increment clock for local event emission."""
        self.value += 1
        return self.value

    def receive(self, remote_clock: int) -> int:
        """Update clock based on received event."""
        self.value = max(self.value, remote_clock) + 1
        return self.value
```

**Persistence**: `~/.spec-kitty/clock.json`
```json
{
  "value": 42,
  "node_id": "alice-laptop-abc123"
}
```

### EventEmitter

Singleton managing event creation and dispatch.

```python
@dataclass
class EventEmitter:
    clock: LamportClock
    auth: AuthClient
    config: SyncConfig
    queue: OfflineQueue
    ws_client: WebSocketClient | None = None

    def emit(self, event_type: str, aggregate_id: str, payload: dict) -> Event:
        """Create and dispatch event."""
        ...
```

**Responsibilities**:
- Manage Lamport clock lifecycle
- Check authentication status
- Build event with all metadata
- Validate against schema
- Route to WebSocket or queue

## Event Types

### WPStatusChanged

Work package status transition.

```python
@dataclass
class WPStatusChangedPayload:
    wp_id: str              # "WP01"
    previous_status: str    # "planned", "doing", "for_review", "done"
    new_status: str         # "planned", "doing", "for_review", "done"
    changed_by: str         # "user" or agent name
    feature_slug: str | None  # Optional context
```

**State Transitions**:
```
planned → doing         (implement command)
doing → for_review      (merge command)
for_review → done       (accept command)
for_review → doing      (changes requested)
```

### WPCreated

New work package created.

```python
@dataclass
class WPCreatedPayload:
    wp_id: str              # "WP01"
    title: str              # "Event Factory Module"
    dependencies: list[str] # ["WP01"] (WP IDs this depends on)
    feature_slug: str       # "028-cli-event-emission-sync"
```

### WPAssigned

Agent assigned to work package.

```python
@dataclass
class WPAssignedPayload:
    wp_id: str              # "WP01"
    agent_id: str           # "claude", "codex", "opencode"
    phase: str              # "implementation" or "review"
    retry_count: int        # 0, 1, 2... (for fallback tracking)
```

### FeatureCreated

New feature initialized.

```python
@dataclass
class FeatureCreatedPayload:
    feature_slug: str       # "028-cli-event-emission-sync"
    feature_number: str     # "028"
    target_branch: str      # "2.x"
    wp_count: int           # 7
    created_at: str         # ISO8601
```

### FeatureCompleted

Feature fully implemented.

```python
@dataclass
class FeatureCompletedPayload:
    feature_slug: str       # "028-cli-event-emission-sync"
    completed_at: str       # ISO8601
    total_wps: int          # 7
    total_duration: str | None  # Optional duration
```

### HistoryAdded

History entry added to work package.

```python
@dataclass
class HistoryAddedPayload:
    wp_id: str              # "WP01"
    entry_type: str         # "note", "review", "error"
    entry_content: str      # The actual content
    author: str             # "user" or agent name
```

### ErrorLogged

Error recorded for debugging/learning.

```python
@dataclass
class ErrorLoggedPayload:
    wp_id: str | None       # Optional WP context
    error_type: str         # "validation", "runtime", "network"
    error_message: str      # Human-readable message
    stack_trace: str | None # Optional stack trace
    agent_id: str | None    # Agent that encountered error
```

### DependencyResolved

Dependency between work packages resolved.

```python
@dataclass
class DependencyResolvedPayload:
    wp_id: str              # "WP02" (dependent)
    dependency_wp_id: str   # "WP01" (dependency)
    resolution_type: str    # "completed", "skipped", "merged"
```

## Storage

### Offline Queue Schema (SQLite)

```sql
CREATE TABLE queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    data TEXT NOT NULL,           -- Full JSON event
    timestamp INTEGER NOT NULL,   -- Queue time (epoch seconds)
    retry_count INTEGER DEFAULT 0
);

CREATE INDEX idx_timestamp ON queue(timestamp);
CREATE INDEX idx_retry ON queue(retry_count);
```

**Constraints**:
- Maximum 10,000 events
- Events removed after successful sync
- Retry count incremented on failure (max 5)

### Clock State (JSON)

```json
{
  "value": 42,
  "node_id": "alice-laptop-abc123",
  "updated_at": "2026-02-03T12:00:00Z"
}
```

**Location**: `~/.spec-kitty/clock.json`
**Atomic writes**: Write to temp file, then rename

## Node ID Generation

Stable identifier for the CLI instance.

```python
def generate_node_id() -> str:
    """Generate stable node ID from machine characteristics."""
    hostname = socket.gethostname()
    username = getpass.getuser()
    raw = f"{hostname}:{username}"
    # Hash to anonymize while keeping stability
    return hashlib.sha256(raw.encode()).hexdigest()[:12]
```

**Properties**:
- Same value across CLI restarts
- Different per user on shared machines
- Not PII (hashed)

---

**END OF DATA MODEL**
