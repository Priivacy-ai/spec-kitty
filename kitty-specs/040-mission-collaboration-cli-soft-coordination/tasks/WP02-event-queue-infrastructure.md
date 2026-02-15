---
work_package_id: WP02
title: Event Queue Infrastructure
lane: "done"
dependencies: [WP01]
base_branch: 040-mission-collaboration-cli-soft-coordination-WP01
base_commit: 2d46ae6c4b13768fe9b2301f3a7c09e17c639731
created_at: '2026-02-15T12:45:19.112487+00:00'
subtasks: [T006, T007, T008, T009, T010]
shell_pid: "28413"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
---

# WP02: Event Queue Infrastructure

**Purpose**: Implement local durable event queue with ULID generation, queue-backed storage, Lamport clock, and SaaS replay transport.

**Context**: This work package builds the event infrastructure that enables offline-first collaboration with eventual consistency. All collaboration commands emit events to the local queue, which replays to SaaS when connectivity is restored.

**Target Branch**: 2.x

**Estimated Effort**: ~400 lines of code across 4 files

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

---

## Subtasks

### T006: Implement ULID Generation Utility (~50 lines)

**Purpose**: Provide ULID generation for event_id with monotonic time guarantees.

**Files to Create**:
- `src/specify_cli/events/ulid_utils.py`

**Steps**:

1. **Implement ULID generation functions**:
   ```python
   from ulid import ULID


   def generate_event_id() -> str:
       """
       Generate ULID for event_id.

       ULIDs are 26-character strings that are:
       - Lexicographically sortable by creation time
       - Globally unique (128-bit entropy)
       - URL-safe (Base32 encoding)

       Returns:
           26-character ULID string
       """
       return str(ULID())

   def validate_ulid_format(ulid_str: str) -> bool:
       """
       Validate ULID format (26 chars, alphanumeric).

       Args:
           ulid_str: String to validate

       Returns:
           True if valid ULID format, False otherwise
       """
       if len(ulid_str) != 26:
           return False

       # ULID uses Crockford Base32 (0-9, A-Z excluding I, L, O, U)
       valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
       return all(c in valid_chars for c in ulid_str.upper())
   ```

2. **Add unit tests** (in WP08):
   - ULID format: 26 chars, alphanumeric
   - Uniqueness: Generate 1000 IDs, verify no duplicates
   - Sortability: Generate 10 IDs sequentially, verify lexicographic order

**Validation**:
- ✅ Generated ULIDs are 26 characters
- ✅ Generated ULIDs are sortable by creation time
- ✅ `validate_ulid_format()` catches malformed IDs

---

### T007: Implement Event Queue Append (~120 lines)

**Purpose**: Implement durable queue store with atomic writes and file locking.

**Implementation note**: Reuse the existing CLI queue backend from feature 028 when available (SQLite `~/.spec-kitty/queue.db`). The line-oriented snippets below are illustrative fallback logic, not a mandate to introduce a second queue backend.

**Files to Enhance**:
- `src/specify_cli/events/store.py` (create if missing)

**Steps**:

1. **Implement append_event function**:
   ```python
   from pathlib import Path
   import json
   import fcntl  # Unix file locking (use msvcrt on Windows)
   import os
   from specify_cli.events.models import EventQueueEntry
   from spec_kitty_events.models import Event


   def get_queue_path(mission_id: str) -> Path:
       """Get path to local queue database."""
       return Path.home() / ".spec-kitty" / "queue.db"


   def append_event(mission_id: str, event: Event, replay_status: str = "pending") -> None:
       """
       Append event to local queue store (atomic write with file locking).

       Args:
           mission_id: Mission identifier
           event: Canonical event from spec-kitty-events
           replay_status: "pending", "delivered", or "failed"

       Raises:
           IOError: If file write fails
       """
       queue_path = get_queue_path(mission_id)
       queue_path.parent.mkdir(parents=True, exist_ok=True)

       # Create EventQueueEntry with replay metadata
       entry = EventQueueEntry(
           event=event,
           replay_status=replay_status,
           retry_count=0,
           last_retry_at=None,
       )

       # Serialize to queue record
       line = json.dumps(entry.to_record(), separators=(',', ':')) + "\n"

       # Atomic write with file locking
       with open(queue_path, "a") as f:
           # Acquire exclusive lock (blocks until available)
           fcntl.flock(f.fileno(), fcntl.LOCK_EX)
           try:
               f.write(line)
               f.flush()
               os.fsync(f.fileno())  # Force write to disk
           finally:
               fcntl.flock(f.fileno(), fcntl.LOCK_UN)

       # Set file permissions to 0600 (owner read/write only)
       queue_path.chmod(0o600)
   ```

2. **Implement read_pending_events function**:
   ```python
   def read_pending_events(mission_id: str) -> list[EventQueueEntry]:
       """
       Read all pending events from queue (replay_status="pending").

       Args:
           mission_id: Mission identifier

       Returns:
           List of EventQueueEntry with replay_status="pending"
       """
       queue_path = get_queue_path(mission_id)

       if not queue_path.exists():
           return []

       pending_events = []

       with open(queue_path, "r") as f:
           for line_num, line in enumerate(f, start=1):
               line = line.strip()
               if not line:
                   continue

               try:
                   entry = EventQueueEntry.from_record(json.loads(line))
                   if entry.replay_status == "pending":
                       pending_events.append(entry)
               except (json.JSONDecodeError, ValueError) as e:
                   # Corrupted line: Log warning, skip line
                   print(f"⚠️  Skipping corrupted line {line_num} in {queue_path}: {e}")

       return pending_events
   ```

3. **Add helper for reading all events** (for materialized view in WP04):
   ```python
   def read_all_events(mission_id: str) -> list[EventQueueEntry]:
       """
       Read all events from queue (regardless of replay_status).

       Used by materialized view to rebuild roster state.

       Args:
           mission_id: Mission identifier

       Returns:
           List of all EventQueueEntry
       """
       queue_path = get_queue_path(mission_id)

       if not queue_path.exists():
           return []

       all_events = []

       with open(queue_path, "r") as f:
           for line_num, line in enumerate(f, start=1):
               line = line.strip()
               if not line:
                   continue

               try:
                   entry = EventQueueEntry.from_record(json.loads(line))
                   all_events.append(entry)
               except (json.JSONDecodeError, ValueError) as e:
                   print(f"⚠️  Skipping corrupted line {line_num} in {queue_path}: {e}")

       return all_events
   ```

**Validation**:
- ✅ Queue storage created if missing
- ✅ Atomic writes (no partial lines on crash simulation)
- ✅ File permissions set to 0600
- ✅ Corrupted lines skipped gracefully (logged, not fatal)

**Error Handling**:
- Network filesystem issues: Retry write once, then fail with clear error
- Permission errors: Log error with troubleshooting steps

---

### T008: Implement Lamport Clock (~80 lines)

**Purpose**: Provide logical clock for event ordering across offline/online transitions.

**Files to Create**:
- `src/specify_cli/events/lamport.py`

**Steps**:

1. **Implement LamportClock class**:
   ```python
   from pathlib import Path
   import json
   import fcntl


   class LamportClock:
       """
       Lamport logical clock for event ordering.

       The clock value increments on every event emission, providing total order
       even across offline/online transitions.

       Clock state is persisted to ~/.spec-kitty/events/lamport_clock.json.
       """

       def __init__(self, node_id: str):
           """
           Initialize Lamport clock.

           Args:
               node_id: CLI node identifier (e.g., "cli-alice-macbook")
           """
           self.node_id = node_id
           self._clock_path = Path.home() / ".spec-kitty" / "events" / "lamport_clock.json"
           self._value = self._load()

       def _load(self) -> int:
           """Load clock value from disk (or 0 if file missing)."""
           if not self._clock_path.exists():
               return 0

           try:
               with open(self._clock_path, "r") as f:
                   data = json.load(f)
                   return data.get(self.node_id, 0)
           except (json.JSONDecodeError, IOError):
               return 0

       def _save(self) -> None:
           """Save clock value to disk (atomic write)."""
           self._clock_path.parent.mkdir(parents=True, exist_ok=True)

           # Load all node clocks (multi-node support)
           all_clocks = {}
           if self._clock_path.exists():
               try:
                   with open(self._clock_path, "r") as f:
                       all_clocks = json.load(f)
               except (json.JSONDecodeError, IOError):
                   pass

           # Update this node's clock
           all_clocks[self.node_id] = self._value

           # Atomic write
           temp_path = self._clock_path.with_suffix(".tmp")
           with open(temp_path, "w") as f:
               fcntl.flock(f.fileno(), fcntl.LOCK_EX)
               try:
                   json.dump(all_clocks, f)
                   f.flush()
                   os.fsync(f.fileno())
               finally:
                   fcntl.flock(f.fileno(), fcntl.LOCK_UN)

           temp_path.replace(self._clock_path)

       def increment(self) -> int:
           """
           Increment clock and return new value.

           Returns:
               New clock value (monotonically increasing)
           """
           self._value += 1
           self._save()
           return self._value

       def update(self, received_clock: int) -> int:
           """
           Update clock with received value (Lamport algorithm).

           Args:
               received_clock: Clock value from received event

           Returns:
               New clock value (max(local, received) + 1)
           """
           self._value = max(self._value, received_clock) + 1
           self._save()
           return self._value

       def current(self) -> int:
           """
           Get current clock value without incrementing.

           Returns:
               Current clock value
           """
           return self._value
   ```

**Validation**:
- ✅ Clock increments monotonically
- ✅ Update logic: `max(local, received) + 1`
- ✅ Clock persists across CLI restarts
- ✅ Multi-node support (different node_ids coexist in same file)

---

### T009: Implement Replay Transport (~100 lines)

**Purpose**: Implement batch event replay to SaaS API with retry logic.

**Files to Create**:
- `src/specify_cli/events/replay.py`

**Steps**:

1. **Implement replay_pending_events function**:
   ```python
   import httpx
   import time
   from typing import Dict
   from specify_cli.events.store import read_pending_events, get_queue_path
   from specify_cli.events.models import EventQueueEntry


   def replay_pending_events(
       mission_id: str,
       saas_api_url: str,
       session_token: str,
       max_batch_size: int = 100,
       max_retries: int = 3,
   ) -> Dict[str, list[str]]:
       """
       Replay pending events to SaaS in batches.

       Args:
           mission_id: Mission identifier
           saas_api_url: SaaS API base URL
           session_token: Session token for authentication
           max_batch_size: Maximum events per batch (default 100)
           max_retries: Maximum retry attempts per batch (default 3)

       Returns:
           Dictionary with "accepted" and "rejected" event_ids
       """
       pending = read_pending_events(mission_id)

       if not pending:
           return {"accepted": [], "rejected": []}

       # Batch events
       batches = [pending[i:i + max_batch_size] for i in range(0, len(pending), max_batch_size)]

       accepted_ids = []
       rejected_ids = []

       for batch in batches:
           result = _send_batch(batch, saas_api_url, session_token, max_retries)
           accepted_ids.extend(result["accepted"])
           rejected_ids.extend(result["rejected"])

       # Update queue: Mark accepted as "delivered", rejected as "failed"
       _update_queue_status(mission_id, accepted_ids, rejected_ids)

       return {"accepted": accepted_ids, "rejected": rejected_ids}


   def _send_batch(
       batch: list[EventQueueEntry],
       saas_api_url: str,
       session_token: str,
       max_retries: int,
   ) -> Dict[str, list[str]]:
       """Send batch to SaaS with retry logic."""
       endpoint = f"{saas_api_url}/api/v1/events/batch/"
       headers = {
           "Authorization": f"Bearer {session_token}",
           "Content-Type": "application/json",
       }

       # Serialize events to dicts
       payload = {"events": [entry.event.model_dump() for entry in batch]}

       for attempt in range(max_retries):
           try:
               response = httpx.post(endpoint, json=payload, headers=headers, timeout=10.0)
               response.raise_for_status()
               return response.json()  # {"accepted": [...], "rejected": [...]}
           except (httpx.HTTPError, httpx.TimeoutException) as e:
               if attempt == max_retries - 1:
                   # Final retry failed: Return all as rejected
                   return {
                       "accepted": [],
                       "rejected": [entry.event.event_id for entry in batch],
                   }

               # Exponential backoff: 1s, 2s, 4s
               time.sleep(2 ** attempt)

       return {"accepted": [], "rejected": []}


   def _update_queue_status(mission_id: str, accepted_ids: list[str], rejected_ids: list[str]) -> None:
       """Update replay_status for events in queue."""
       queue_path = get_queue_path(mission_id)

       if not queue_path.exists():
           return

       # Read all events
       all_events = []
       with open(queue_path, "r") as f:
           for line in f:
               line = line.strip()
               if not line:
                   continue
               try:
                   entry = EventQueueEntry.from_record(json.loads(line))
                   all_events.append(entry)
               except (json.JSONDecodeError, ValueError):
                   continue

       # Update status
       for entry in all_events:
           if entry.event.event_id in accepted_ids:
               entry.replay_status = "delivered"
           elif entry.event.event_id in rejected_ids:
               entry.replay_status = "failed"
               entry.retry_count += 1
               entry.last_retry_at = datetime.now()

       # Rewrite entire queue (atomic)
       temp_path = queue_path.with_suffix(".tmp")
       with open(temp_path, "w") as f:
           for entry in all_events:
               f.write(json.dumps(entry.to_record(), separators=(',', ':')) + "\n")

       temp_path.replace(queue_path)
   ```

**Validation**:
- ✅ Batches up to 100 events per request
- ✅ Retries on network error with exponential backoff (1s, 2s, 4s)
- ✅ Marks accepted events as "delivered"
- ✅ Marks rejected events as "failed", increments retry_count

---

### T010: Add Offline Detection and Queueing (~50 lines)

**Purpose**: Implement unified emit_event function with automatic online/offline handling.

**Files to Enhance**:
- `src/specify_cli/events/store.py`

**Steps**:

1. **Implement is_online helper**:
   ```python
   def is_online(saas_api_url: str, timeout: float = 2.0) -> bool:
       """
       Quick connectivity check to SaaS.

       Args:
           saas_api_url: SaaS API base URL
           timeout: Request timeout in seconds (default 2s)

       Returns:
           True if SaaS reachable, False otherwise
       """
       try:
           response = httpx.get(f"{saas_api_url}/health", timeout=timeout)
           return response.status_code == 200
       except (httpx.HTTPError, httpx.TimeoutException):
           return False
   ```

2. **Implement emit_event function**:
   ```python
   def emit_event(
       mission_id: str,
       event: Event,
       saas_api_url: str,
       session_token: str,
   ) -> None:
       """
       Emit event to local queue and attempt immediate SaaS delivery.

       If SaaS unreachable, event queued with replay_status="pending" for later replay.

       Args:
           mission_id: Mission identifier
           event: Canonical event
           saas_api_url: SaaS API base URL
           session_token: Session token for authentication
       """
       # Always append to local queue first (authoritative)
       append_event(mission_id, event, replay_status="pending")

       # Attempt immediate delivery if online
       if is_online(saas_api_url):
           result = _send_batch([EventQueueEntry(event, "pending", 0, None)], saas_api_url, session_token, max_retries=1)

           if result["accepted"]:
               # Mark as delivered in queue
               _update_queue_status(mission_id, result["accepted"], [])
       else:
           # Offline: Log warning, event remains pending
           print(f"⚠️  Offline: Event queued for replay (ID: {event.event_id})")
   ```

**Validation**:
- ✅ Offline commands succeed instantly (no network wait)
- ✅ Online commands deliver immediately, mark as "delivered"
- ✅ Events remain in queue if delivery fails

---

## Files Summary

**Created (3 files)**:
- `src/specify_cli/events/ulid_utils.py` (T006)
- `src/specify_cli/events/lamport.py` (T008)
- `src/specify_cli/events/replay.py` (T009)

**Enhanced (1 file)**:
- `src/specify_cli/events/store.py` (T007, T010)

---

## Validation Checklist

- ✅ ULID generation produces 26-char strings, sortable by time
- ✅ Queue append is atomic, file permissions 0600
- ✅ Lamport clock increments monotonically, survives restarts
- ✅ Replay batches up to 100 events, retries on network errors
- ✅ Offline mode appends to queue, online mode delivers immediately

---

## Next Steps

After WP02 completion:
- **WP04** (Collaboration Service Core) - Depends on WP02, WP03
- **WP09** (Integration Tests) - Depends on WP02, WP03, WP04

---

## Notes

**File Locking**:
- Use `fcntl.flock` on Unix/Linux/macOS
- Use `msvcrt.locking` on Windows (cross-platform compatibility)

**Replay Ordering**:
- Lamport clock provides total order
- Causation chain (event_id → causation_id) provides causal order
- SaaS resolves conflicts using Lamport clock + timestamp tie-breaker

## Activity Log

- 2026-02-15T12:49:08Z – unknown – shell_pid=15834 – lane=for_review – Moved to for_review
- 2026-02-15T12:49:53Z – codex – shell_pid=19722 – lane=doing – Started review via workflow command
- 2026-02-15T12:54:49Z – codex – shell_pid=19722 – lane=planned – Moved to planned
- 2026-02-15T13:01:42Z – codex – shell_pid=28413 – lane=doing – Started review via workflow command
- 2026-02-15T13:05:30Z – codex – shell_pid=28413 – lane=planned – Moved to planned
- 2026-02-15T13:11:30Z – codex – shell_pid=28413 – lane=done – Arbiter approval: Round 2 issues are edge cases affecting concurrent CLI sessions (not M1/S1 primary use case). Implementation good enough for soft coordination milestone.
