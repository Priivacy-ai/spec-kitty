---
work_package_id: "WP04"
title: "SQLite Query Index"
phase: "Phase 1 - Core Event Infrastructure"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP03"]
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
history:
  - timestamp: "2026-01-27T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – SQLite Query Index

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

**Primary Goal**: Implement SQLite index for fast event queries, enabling sub-500ms performance for 1000+ events.

**Success Criteria**:
- ✅ EventIndex class with SQLite schema (events table + 3 indices)
- ✅ `update()` method inserts event metadata into index (idempotent)
- ✅ `query()` method filters by entity_id, event_type, since_clock
- ✅ `rebuild()` method reconstructs index from all JSONL files
- ✅ Index updates integrated into EventStore.emit() (synchronous for MVP)
- ✅ Automatic index rebuild on missing/corrupted database
- ✅ Query performance <500ms for 1000+ events (US3 requirement)

**Priority**: P1 (US3)

**User Story**: US3 - SQLite Query Index for Fast Aggregates

**Independent Test**:
```python
# Generate 1000 events
from specify_cli.events.store import EventStore
from pathlib import Path
import time

store = EventStore(Path("/tmp/perf-test-index"))
for i in range(1000):
    store.emit(
        event_type="WPStatusChanged" if i % 2 == 0 else "SpecCreated",
        entity_id=f"WP{i % 10:02d}",  # 10 different WPs
        entity_type="WorkPackage",
        actor="perf-test",
        payload={"iteration": i}
    )

# Query with filter (should use index)
start = time.time()
events = store.read(entity_id="WP01", event_type="WPStatusChanged")
elapsed_ms = (time.time() - start) * 1000

print(f"Query returned {len(events)} events in {elapsed_ms:.2f}ms")
assert elapsed_ms < 500, f"Query too slow: {elapsed_ms}ms"
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

- **WP03 complete**: EventStore.emit() exists and writes JSONL files
- **Data model**: `kitty-specs/025-cli-event-log-integration/data-model.md` (lines 204-279)
- **Spec**: US3 acceptance scenarios (lines 67-72)

### Architectural Constraints

**From data-model.md (EventIndex)**:
- SQLite schema with columns: event_id (PK), lamport_clock, entity_id, entity_type, event_type, timestamp, date
- Three indices: idx_entity (entity_id, lamport_clock), idx_type (event_type, lamport_clock), idx_date (date)
- Index is derived state (JSONL files are source of truth)
- Rebuild from JSONL on corruption/missing

**From plan.md (Technical Context)**:
- Synchronous index updates for MVP (inline during emit)
- Query performance target: <500ms for 1000+ events
- Index update latency budget: ~5ms (part of 15ms total emit latency)

### Key Technical Decisions

1. **Synchronous Updates** (Planning Q3): Index updates happen inline during emit() (not async background worker)
2. **JSONL Source of Truth** (FR-019): Index can be rebuilt from JSONL if corrupted
3. **Query Optimization** (US3): Use index for filtered queries, read JSONL directly for full scans

---

## Subtasks & Detailed Guidance

### Subtask T019 – Create EventIndex class with SQLite schema (events table + indices)

**Purpose**: Define the SQLite database schema and provide the EventIndex interface.

**Steps**:

1. **Create index module**:
   ```python
   # src/specify_cli/events/index.py (new file)

   from pathlib import Path
   import sqlite3
   from typing import Any
   from specify_cli.events.types import Event


   class EventIndex:
       """
       SQLite query index for fast event filtering.

       Index is derived state - JSONL files are source of truth.
       Can be rebuilt from JSONL at any time.
       """

       def __init__(self, index_db: Path):
           """
           Initialize index with path to SQLite database.

           Args:
               index_db: Path to .kittify/events/index.db
           """
           self.index_db = index_db
           self._ensure_schema()

       def _ensure_schema(self) -> None:
           """Create tables and indices if they don't exist."""
           conn = sqlite3.connect(self.index_db)
           try:
               # Create events table
               conn.execute("""
                   CREATE TABLE IF NOT EXISTS events (
                       event_id TEXT PRIMARY KEY,
                       lamport_clock INTEGER NOT NULL,
                       entity_id TEXT NOT NULL,
                       entity_type TEXT NOT NULL,
                       event_type TEXT NOT NULL,
                       timestamp TEXT NOT NULL,
                       date TEXT NOT NULL
                   )
               """)

               # Create indices for fast queries
               conn.execute("""
                   CREATE INDEX IF NOT EXISTS idx_entity
                   ON events(entity_id, lamport_clock)
               """)

               conn.execute("""
                   CREATE INDEX IF NOT EXISTS idx_type
                   ON events(event_type, lamport_clock)
               """)

               conn.execute("""
                   CREATE INDEX IF NOT EXISTS idx_date
                   ON events(date)
               """)

               conn.commit()
           finally:
               conn.close()

       def _drop_tables(self) -> None:
           """Drop all tables (for rebuild)."""
           conn = sqlite3.connect(self.index_db)
           try:
               conn.execute("DROP TABLE IF EXISTS events")
               conn.commit()
           finally:
               conn.close()

       def exists(self) -> bool:
           """Check if index database exists."""
           return self.index_db.exists()

       def delete(self) -> None:
           """Delete index database (for testing or corruption recovery)."""
           if self.index_db.exists():
               self.index_db.unlink()
   ```

**Files**:
- `src/specify_cli/events/index.py` (new file, ~80 lines)

**Validation**:
- [ ] `_ensure_schema()` creates events table with 7 columns
- [ ] Three indices created: idx_entity, idx_type, idx_date
- [ ] Idempotent: Safe to call _ensure_schema() multiple times
- [ ] Schema matches data-model.md specification (lines 211-225)

**Edge Cases**:
- Database doesn't exist: Created automatically by sqlite3.connect()
- Schema already exists: CREATE IF NOT EXISTS prevents errors
- Parent directory missing: Parent dir should exist from WP02 directory initialization

**Parallel?**: Yes - Can implement in parallel with T020-T022 (separate methods)

---

### Subtask T020 – Implement `update()` method for inline index updates during emit

**Purpose**: Insert event metadata into SQLite index, maintaining idempotency.

**Steps**:

1. **Add update() method to EventIndex**:
   ```python
   # In src/specify_cli/events/index.py (add to EventIndex class)

   def update(self, event: Event) -> None:
       """
       Insert event metadata into index.

       Idempotent: Uses INSERT OR IGNORE to handle duplicate event_id.

       Args:
           event: Event object to index

       Raises:
           sqlite3.DatabaseError: If database write fails
       """
       conn = sqlite3.connect(self.index_db)
       try:
           # Extract date from timestamp (YYYY-MM-DD)
           date = event.timestamp[:10]

           # Insert with IGNORE to make idempotent
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
               date,
           ))

           conn.commit()
       finally:
           conn.close()

       def update_batch(self, events: list[Event]) -> None:
           """
           Insert multiple events in a single transaction (for rebuild).

           Args:
               events: List of events to index

           Raises:
               sqlite3.DatabaseError: If database write fails
           """
           conn = sqlite3.connect(self.index_db)
           try:
               for event in events:
                   date = event.timestamp[:10]
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
                       date,
                   ))

               conn.commit()
           finally:
               conn.close()
   ```

**Files**:
- `src/specify_cli/events/index.py` (modify: add update() and update_batch() methods)

**Validation**:
- [ ] `update()` inserts event metadata into events table
- [ ] Uses `INSERT OR IGNORE` for idempotency (duplicate event_id skipped)
- [ ] Extracts date from timestamp (first 10 characters: YYYY-MM-DD)
- [ ] `update_batch()` wraps multiple inserts in single transaction

**Edge Cases**:
- Duplicate event_id: Silently ignored (idempotent operation)
- Database locked (concurrent access): sqlite3 retries automatically (default timeout: 5 seconds)
- Invalid event data (missing fields): sqlite3 raises DatabaseError (propagated to caller)

**Parallel?**: Yes - Can implement in parallel with T019, T021-T022

---

### Subtask T021 – Implement `query()` method with filters (entity_id, event_type, since_clock)

**Purpose**: Provide fast filtered queries using SQLite indices.

**Steps**:

1. **Add query() method to EventIndex**:
   ```python
   # In src/specify_cli/events/index.py (add to EventIndex class)

   from typing import Any

   def query(
       self,
       entity_id: str | None = None,
       event_type: str | None = None,
       since_clock: int | None = None,
   ) -> list[dict[str, Any]]:
       """
       Query index for events matching filters.

       Returns metadata (not full events - use to identify which JSONL files to read).

       Args:
           entity_id: Filter by entity (e.g., "WP01")
           event_type: Filter by event type (e.g., "WPStatusChanged")
           since_clock: Filter by Lamport clock (events after this value)

       Returns:
           List of dicts with: event_id, lamport_clock, entity_id, event_type, date
       """
       if not self.exists():
           # Index missing - return empty (will trigger rebuild in caller)
           return []

       conn = sqlite3.connect(self.index_db)
       conn.row_factory = sqlite3.Row  # Enable dict-like row access
       try:
           # Build WHERE clause dynamically
           where_clauses = []
           params = []

           if entity_id:
               where_clauses.append("entity_id = ?")
               params.append(entity_id)

           if event_type:
               where_clauses.append("event_type = ?")
               params.append(event_type)

           if since_clock is not None:
               where_clauses.append("lamport_clock > ?")
               params.append(since_clock)

           where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

           # Execute query
           query_sql = f"""
               SELECT event_id, lamport_clock, entity_id, entity_type, event_type, date
               FROM events
               WHERE {where_sql}
               ORDER BY lamport_clock ASC
           """

           cursor = conn.execute(query_sql, params)
           results = [dict(row) for row in cursor.fetchall()]

           return results
       finally:
           conn.close()

   def get_affected_dates(
       self,
       entity_id: str | None = None,
       event_type: str | None = None,
       since_clock: int | None = None,
   ) -> list[str]:
       """
       Get list of dates (YYYY-MM-DD) containing matching events.

       Used to determine which JSONL files to read.

       Returns:
           List of ISO dates (e.g., ["2026-01-27", "2026-01-28"])
       """
       results = self.query(entity_id, event_type, since_clock)
       dates = sorted(set(row["date"] for row in results))
       return dates
   ```

**Files**:
- `src/specify_cli/events/index.py` (modify: add query() and get_affected_dates() methods)

**Validation**:
- [ ] `query()` builds WHERE clause dynamically based on filters
- [ ] Returns results ordered by lamport_clock (causal order)
- [ ] Uses sqlite3.Row for dict-like access
- [ ] `get_affected_dates()` returns unique dates containing matching events
- [ ] Query performance <500ms for 1000+ events (benchmark in independent test)

**Edge Cases**:
- No filters provided: Returns all events (ordered by lamport_clock)
- No matching events: Returns empty list
- Index database missing: Returns empty list (triggers rebuild in caller)
- Multiple filters: Combined with AND logic

**Parallel?**: Yes - Can implement in parallel with T019-T020, T022

---

### Subtask T022 – Implement `rebuild()` method for corruption recovery

**Purpose**: Reconstruct index from all JSONL files when index is missing or corrupted.

**Steps**:

1. **Add rebuild() method to EventIndex**:
   ```python
   # In src/specify_cli/events/index.py (add to EventIndex class)

   import json
   import sys

   def rebuild(self, events_dir: Path) -> int:
       """
       Rebuild index from all JSONL files in events directory.

       Args:
           events_dir: Path to .kittify/events/

       Returns:
           Number of events indexed

       Raises:
           RuntimeError: If rebuild fails
       """
       print("⚙️ Rebuilding event index from JSONL files...", file=sys.stderr)

       # Drop existing tables
       self._drop_tables()

       # Recreate schema
       self._ensure_schema()

       # Scan all JSONL files
       events = []
       jsonl_files = sorted(events_dir.glob("*.jsonl"))

       if not jsonl_files:
           print("No JSONL files found. Index is empty.", file=sys.stderr)
           return 0

       for jsonl_file in jsonl_files:
           try:
               for line_num, line in enumerate(jsonl_file.read_text().splitlines(), 1):
                   if not line.strip():
                       continue  # Skip empty lines

                   try:
                       event = Event.from_json(line)
                       events.append(event)
                   except json.JSONDecodeError as e:
                       # Graceful degradation: skip invalid JSON
                       print(
                           f"⚠️ Skipping invalid JSON in {jsonl_file.name}:{line_num}: {e}",
                           file=sys.stderr
                       )
                       continue
           except Exception as e:
               print(f"⚠️ Failed to read {jsonl_file.name}: {e}", file=sys.stderr)
               continue

       # Batch insert all events
       if events:
           print(f"Indexing {len(events)} events from {len(jsonl_files)} files...", file=sys.stderr)
           self.update_batch(events)

       print(f"✓ Index rebuilt successfully: {len(events)} events indexed", file=sys.stderr)
       return len(events)

   def check_integrity(self) -> bool:
       """
       Check if index database is healthy.

       Returns:
           True if index is valid, False if corrupted
       """
       if not self.exists():
           return False

       try:
           conn = sqlite3.connect(self.index_db)
           conn.execute("SELECT COUNT(*) FROM events")
           conn.close()
           return True
       except sqlite3.DatabaseError:
           return False
   ```

**Files**:
- `src/specify_cli/events/index.py` (modify: add rebuild() and check_integrity() methods)

**Validation**:
- [ ] `rebuild()` drops existing tables and recreates schema
- [ ] Scans all `*.jsonl` files in events_dir
- [ ] Parses each JSON line, creates Event objects
- [ ] Skips invalid JSON lines with warning (graceful degradation)
- [ ] Uses `update_batch()` for efficient insertion
- [ ] Returns count of events indexed
- [ ] `check_integrity()` validates database is readable

**Edge Cases**:
- No JSONL files exist: Returns 0, index is empty (valid state)
- All JSONL files corrupted: Returns 0, logs warnings
- Partial corruption: Indexes valid events, skips corrupted lines
- Rebuild interrupted: Next rebuild will start from scratch (drop + recreate)

**Parallel?**: Yes - Can implement in parallel with T019-T021

---

### Subtask T023 – Integrate index updates into EventStore.emit() (synchronous for MVP)

**Purpose**: Update SQLite index inline during event emission (part of synchronous write flow).

**Steps**:

1. **Modify EventStore to include EventIndex**:
   ```python
   # In src/specify_cli/events/store.py (modify __init__ and emit methods)

   from specify_cli.events.index import EventIndex

   class EventStore:
       def __init__(self, repo_root: Path):
           # ... existing initialization

           # Initialize EventIndex
           self.index_db = self.events_dir / "index.db"
           self.index = EventIndex(self.index_db)

       def emit(self, ...) -> Event:
           """Emit event with automatic clock increment and index update."""
           # ... existing emit logic (clock tick, create event, append JSONL)

           # NEW: Update index (inline, synchronous)
           try:
               self.index.update(event)
           except Exception as e:
               # Log warning but don't block event emission
               import sys
               print(f"⚠️ Failed to update index: {e}", file=sys.stderr)
               print("Event log remains consistent (JSONL is source of truth)", file=sys.stderr)

           # ... existing clock save

           return event
   ```

2. **Add index update after JSONL write** (important: order matters):
   ```python
   # Order in emit():
   # 1. Tick clock
   # 2. Create event
   # 3. Append to JSONL (source of truth)
   # 4. Update index (derived state) ← NEW
   # 5. Save clock

   # This ensures: JSONL always written before index update
   # If index update fails, JSONL is still valid (can rebuild index later)
   ```

**Files**:
- `src/specify_cli/events/store.py` (modify: add EventIndex initialization and update call)

**Validation**:
- [ ] EventIndex initialized in EventStore.__init__()
- [ ] `index.update(event)` called in emit() AFTER JSONL append
- [ ] Index update wrapped in try/except (warning on failure, doesn't block emit)
- [ ] Order preserved: JSONL write → index update → clock save

**Edge Cases**:
- Index update fails (database locked): Warning logged, JSONL remains valid
- Index database corrupted: Warning logged, can be rebuilt later
- Index update adds latency: Measured in T014 benchmark (should be ~2-5ms, within 15ms budget)

**Parallel?**: No - Sequential after T020 (needs EventIndex.update() method)

---

### Subtask T024 – Add automatic index rebuild on missing/corrupted database

**Purpose**: Automatically rebuild index when it's missing or corrupted, ensuring queries always work.

**Steps**:

1. **Add rebuild trigger to EventStore.read()**:
   ```python
   # In src/specify_cli/events/store.py (add read method)

   def read(
       self,
       entity_id: str | None = None,
       event_type: str | None = None,
       since_clock: int | None = None,
   ) -> list[Event]:
       """
       Read events from log, optionally filtered.

       Uses SQLite index if filters provided AND index is healthy.
       Falls back to direct JSONL reading if index missing/corrupted.

       Args:
           entity_id: Filter by entity
           event_type: Filter by event type
           since_clock: Filter by Lamport clock

       Returns:
           List of Event objects, sorted by lamport_clock
       """
       # Check if we should use index (filters provided)
       use_index = bool(entity_id or event_type or since_clock)

       if use_index:
           # Check index health
           if not self.index.check_integrity():
               import sys
               print("⚠️ Index corrupted or missing. Rebuilding...", file=sys.stderr)
               try:
                   self.index.rebuild(self.events_dir)
               except Exception as e:
                   print(f"⚠️ Index rebuild failed: {e}", file=sys.stderr)
                   print("Falling back to direct JSONL reading (slower)", file=sys.stderr)
                   use_index = False

       if use_index and self.index.exists():
           # Query index to get affected dates
           dates = self.index.get_affected_dates(entity_id, event_type, since_clock)

           # Read only JSONL files for those dates
           events = []
           for date in dates:
               jsonl_file = self.events_dir / f"{date}.jsonl"
               if jsonl_file.exists():
                   events.extend(self._read_jsonl_file(jsonl_file))

           # Filter in memory (index gives us dates, still need to filter events)
           events = self._filter_events(events, entity_id, event_type, since_clock)
       else:
           # No filters or index unavailable - read all JSONL files
           events = self._read_all_jsonl()
           events = self._filter_events(events, entity_id, event_type, since_clock)

       # Sort by Lamport clock (causal order)
       events.sort(key=lambda e: e.lamport_clock)

       return events

   def _read_jsonl_file(self, jsonl_file: Path) -> list[Event]:
       """Read events from a single JSONL file."""
       events = []
       for line in jsonl_file.read_text().splitlines():
           if not line.strip():
               continue
           try:
               events.append(Event.from_json(line))
           except json.JSONDecodeError:
               # Graceful degradation: skip invalid lines
               import sys
               print(f"⚠️ Skipping invalid JSON in {jsonl_file.name}", file=sys.stderr)
       return events

   def _read_all_jsonl(self) -> list[Event]:
       """Read events from all JSONL files."""
       events = []
       for jsonl_file in sorted(self.events_dir.glob("*.jsonl")):
           events.extend(self._read_jsonl_file(jsonl_file))
       return events

   def _filter_events(
       self,
       events: list[Event],
       entity_id: str | None,
       event_type: str | None,
       since_clock: int | None,
   ) -> list[Event]:
       """Filter events in memory."""
       filtered = events
       if entity_id:
           filtered = [e for e in filtered if e.entity_id == entity_id]
       if event_type:
           filtered = [e for e in filtered if e.event_type == event_type]
       if since_clock is not None:
           filtered = [e for e in filtered if e.lamport_clock > since_clock]
       return filtered
   ```

**Files**:
- `src/specify_cli/events/store.py` (modify: add read() method and helpers)

**Validation**:
- [ ] `read()` checks index integrity before use
- [ ] Automatically triggers rebuild if index missing/corrupted
- [ ] Falls back to direct JSONL reading if rebuild fails
- [ ] Uses index to identify affected dates (optimization)
- [ ] Filters events in memory after reading JSONL
- [ ] Returns events sorted by lamport_clock

**Edge Cases**:
- Index missing: Rebuilds automatically
- Index corrupted: Rebuilds automatically
- Rebuild fails: Falls back to direct JSONL reading (slower but works)
- No filters provided: Skips index, reads all JSONL directly

**Parallel?**: No - Sequential after T022-T023 (needs rebuild() and update())

---

## Test Strategy

**No separate test files** (constitution: tests not explicitly requested).

**Validation approach**:
1. **T019**: Schema test - Verify tables and indices created
2. **T020**: Insert test - Verify event metadata inserted correctly
3. **T021**: Query test - Verify filtered queries work with indices
4. **T022**: Rebuild test - Delete index, verify rebuild from JSONL
5. **T023**: Integration test - Verify emit() updates index
6. **T024**: Auto-rebuild test - Corrupt index, verify auto-rebuild on read

**Performance benchmark** (US3 requirement):
```python
from specify_cli.events.store import EventStore
from pathlib import Path
import time

# Generate 1000 events across 10 WPs
store = EventStore(Path("/tmp/perf-test-1000"))
for i in range(1000):
    store.emit(
        event_type="WPStatusChanged" if i % 2 == 0 else "SpecCreated",
        entity_id=f"WP{i % 10:02d}",
        entity_type="WorkPackage",
        actor="perf",
        payload={"i": i}
    )

# Benchmark filtered query (should use index)
start = time.time()
events = store.read(entity_id="WP05")
elapsed_ms = (time.time() - start) * 1000

print(f"Filtered query ({len(events)} events): {elapsed_ms:.2f}ms")
assert elapsed_ms < 500, f"Query too slow: {elapsed_ms}ms (target: <500ms)"

# Benchmark full scan (no index)
start = time.time()
all_events = store.read()
elapsed_ms = (time.time() - start) * 1000

print(f"Full scan ({len(all_events)} events): {elapsed_ms:.2f}ms")
# Full scan expected to be slower but should still be reasonable (<2000ms)
```

---

## Risks & Mitigations

### Risk 1: Index updates add >5ms latency to emit()

**Impact**: Total emit latency exceeds 15ms target (violates performance goal)

**Mitigation**:
- T020 uses `INSERT OR IGNORE` (fast, single statement)
- T023 wraps in try/except (warning on failure, doesn't block)
- Benchmark in T014 validates total <15ms

### Risk 2: Index frequently becomes corrupted

**Impact**: Automatic rebuilds add latency to read operations

**Mitigation**:
- T024 checks integrity before rebuild (avoids unnecessary rebuilds)
- Rebuild only triggers on actual corruption (not on every read)
- Fallback to direct JSONL reading if rebuild fails

### Risk 3: Query performance doesn't meet <500ms target

**Impact**: Violates US3 acceptance criteria

**Mitigation**:
- T021 uses SQLite indices (idx_entity, idx_type for fast lookups)
- T024 reads only affected dates (not all JSONL files)
- Performance test validates target before merge

---

## Definition of Done Checklist

- [ ] T019: EventIndex class with SQLite schema (events table + 3 indices)
- [ ] T019: Schema creation is idempotent (safe to call multiple times)
- [ ] T020: `update()` method inserts event metadata (idempotent with INSERT OR IGNORE)
- [ ] T020: `update_batch()` method for efficient batch inserts
- [ ] T021: `query()` method filters by entity_id, event_type, since_clock
- [ ] T021: `get_affected_dates()` returns unique dates containing matching events
- [ ] T022: `rebuild()` method drops tables, recreates schema, scans JSONL files
- [ ] T022: Graceful degradation on invalid JSON lines
- [ ] T023: EventIndex integrated into EventStore.__init__()
- [ ] T023: `index.update()` called in emit() after JSONL write
- [ ] T024: `read()` method checks index integrity before use
- [ ] T024: Automatic rebuild triggers on missing/corrupted index
- [ ] T024: Falls back to direct JSONL reading if index unavailable
- [ ] Performance test passes: Query <500ms for 1000+ events

---

## Review Guidance

**Key Acceptance Checkpoints**:

1. **T019 - Schema Design**:
   - ✓ Events table has 7 columns matching data-model.md
   - ✓ Three indices created for optimization
   - ✓ Idempotent schema creation

2. **T020 - Index Updates**:
   - ✓ `INSERT OR IGNORE` for idempotency
   - ✓ Date extracted from timestamp (YYYY-MM-DD)
   - ✓ Batch insert for rebuild performance

3. **T021 - Query Performance**:
   - ✓ Dynamic WHERE clause based on filters
   - ✓ Results ordered by lamport_clock
   - ✓ Benchmark shows <500ms for 1000+ events

4. **T022 - Rebuild Robustness**:
   - ✓ Drops and recreates schema (clean rebuild)
   - ✓ Skips invalid JSON with warning
   - ✓ Returns count of events indexed

5. **T023 - Integration**:
   - ✓ Index update after JSONL write (order matters)
   - ✓ Wrapped in try/except (best-effort)

6. **T024 - Auto-Rebuild**:
   - ✓ Integrity check before use
   - ✓ Automatic rebuild on corruption
   - ✓ Fallback to direct JSONL reading

**Reviewers should**:
- Run performance benchmark (verify <500ms)
- Test corruption recovery (delete index.db, verify rebuild)
- Check index file size (should be small, ~100KB for 1000 events)

---

## Activity Log

- 2026-01-27T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

## Implementation Command

This WP depends on WP03. Implement from WP03's branch:

```bash
spec-kitty implement WP04 --base WP03
```

This will create workspace: `.worktrees/025-cli-event-log-integration-WP04/` branched from WP03.
