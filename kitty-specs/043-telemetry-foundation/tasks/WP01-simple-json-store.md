---
work_package_id: WP01
title: SimpleJsonStore — File-Backed EventStore
lane: "done"
dependencies: []
base_branch: 043-telemetry-foundation
base_commit: b7331a9d47b04013dcbdbae3c2a70a7cef0b0f74
created_at: '2026-02-15T20:04:50.279505+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
assignee: ''
agent: copilot
shell_pid: '501650'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T19:43:21Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – SimpleJsonStore — File-Backed EventStore

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies — branches directly from target branch.

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement `SimpleJsonStore` as a JSONL-backed implementation of the `spec_kitty_events.EventStore` ABC
- Complete the missing file persistence layer for the vendored `spec_kitty_events` library
- All three ABC methods work correctly: `save_event()`, `load_events()`, `load_all_events()`
- Idempotent writes (duplicate `event_id` skipped)
- Malformed JSONL lines tolerated (skipped with warning)
- Stream-parsed reads (no full-file memory load)
- 90%+ test coverage for the new `telemetry/` package

## Context & Constraints

- **Spec**: `kitty-specs/043-telemetry-foundation/spec.md` — FR-001, FR-002, FR-011, FR-012
- **Plan**: `kitty-specs/043-telemetry-foundation/plan.md` — AD-2 (separate JSONL), AD-3 (SimpleJsonStore)
- **Data model**: `kitty-specs/043-telemetry-foundation/data-model.md` — SimpleJsonStore entity
- **Research**: `kitty-specs/043-telemetry-foundation/research.md` — R2 (storage decision)
- **ADR**: `architecture/adrs/2026-01-31-1-vendor-spec-kitty-events.md` — Addendum: SimpleJsonStore
- **Constitution**: Python 3.11+, pytest, mypy --strict, 90%+ coverage
- **EventStore ABC**: `src/specify_cli/spec_kitty_events/storage.py` — defines the interface to implement
- **Event model**: `src/specify_cli/spec_kitty_events/models.py` — `Event` Pydantic model with `to_dict()` / `from_dict()`

## Subtasks & Detailed Guidance

### Subtask T001 – Create telemetry package `__init__.py`

- **Purpose**: Establish the `src/specify_cli/telemetry/` package with a clean public API.
- **Steps**:
  1. Create `src/specify_cli/telemetry/__init__.py`
  2. For now, export only what WP01 provides:
     - `SimpleJsonStore` from `.store`
  3. Later WPs will add more exports (emit, query, cost)
  4. Add a module docstring explaining the package purpose
- **Files**: `src/specify_cli/telemetry/__init__.py` (new)
- **Notes**: Keep imports lazy where possible to avoid circular imports with future modules.

### Subtask T002 – Implement SimpleJsonStore core

- **Purpose**: Provide a file-backed `EventStore` that persists `spec_kitty_events.Event` objects as JSONL.
- **Steps**:
  1. Create `src/specify_cli/telemetry/store.py`
  2. Import `EventStore` ABC from `specify_cli.spec_kitty_events.storage`
  3. Import `Event` from `specify_cli.spec_kitty_events.models`
  4. Implement `SimpleJsonStore(EventStore)`:

     ```python
     class SimpleJsonStore(EventStore):
         def __init__(self, file_path: Path) -> None:
             self._file_path = file_path
             self._known_ids: set[str] | None = None  # Lazy-loaded for dedup

         def save_event(self, event: Event) -> None: ...
         def load_events(self, aggregate_id: str) -> list[Event]: ...
         def load_all_events(self) -> list[Event]: ...
     ```

  5. `save_event()`: Create parent dirs, open in append mode, write `json.dumps(event.to_dict(), sort_keys=True) + "\n"`
  6. `load_events(aggregate_id)`: Read all events, filter by `event.aggregate_id == aggregate_id`, sort by `(lamport_clock, node_id)`
  7. `load_all_events()`: Read all events, sort by `(lamport_clock, node_id)`
- **Files**: `src/specify_cli/telemetry/store.py` (new, ~80 lines)
- **Notes**: The `Event.to_dict()` method returns a dict suitable for JSON serialization. `Event.from_dict()` reconstructs from dict. Both are provided by the Pydantic model. The `timestamp` field in Event is a `datetime` object — `to_dict()` handles serialization via Pydantic's `model_dump()`.

### Subtask T003 – Add stream-parsing for large JSONL reads

- **Purpose**: Ensure reads don't load entire files into memory (spec requires handling >100MB files).
- **Steps**:
  1. Implement a private `_read_all_raw(self) -> list[Event]` method that:
     - Opens file with `open(self._file_path, "r", encoding="utf-8")`
     - Iterates line-by-line (Python file iteration is lazy — this IS stream-parsing)
     - Parses each non-empty line with `json.loads(line)`
     - Constructs `Event.from_dict(data)` for each valid line
     - Returns collected events
  2. If file doesn't exist, return empty list (no error)
  3. Both `load_events()` and `load_all_events()` delegate to `_read_all_raw()` then filter/sort
- **Files**: `src/specify_cli/telemetry/store.py` (modify)
- **Notes**: Python's file iterator reads lines lazily from the OS buffer. This is sufficient stream-parsing for JSONL. We collect into a list for sorting, but individual lines are never all in memory simultaneously during parsing.

### Subtask T004 – Add idempotent write semantics

- **Purpose**: Prevent duplicate events when `save_event()` is called with the same `event_id` twice.
- **Steps**:
  1. Add lazy-loaded `_known_ids` set to `SimpleJsonStore`:

     ```python
     def _ensure_known_ids(self) -> set[str]:
         if self._known_ids is None:
             self._known_ids = set()
             if self._file_path.exists():
                 for line in open(self._file_path, "r", encoding="utf-8"):
                     line = line.strip()
                     if line:
                         try:
                             data = json.loads(line)
                             self._known_ids.add(data["event_id"])
                         except (json.JSONDecodeError, KeyError):
                             pass  # Skip corrupt lines during ID scan
         return self._known_ids
     ```

  2. In `save_event()`, check `event.event_id in self._ensure_known_ids()` before writing
  3. After successful write, add `event.event_id` to `_known_ids`
  4. If event_id already exists, return silently (no error, no write)
- **Files**: `src/specify_cli/telemetry/store.py` (modify)
- **Notes**: The lazy load means first write to a pre-existing file scans it once. Subsequent writes use the in-memory cache. This trades O(n) first-write latency for O(1) subsequent writes.

### Subtask T005 – Add malformed-line tolerance

- **Purpose**: Skip corrupted JSONL lines (partial writes from crashes) without failing the entire read.
- **Steps**:
  1. In `_read_all_raw()`, wrap `json.loads(line)` and `Event.from_dict(data)` in try/except:

     ```python
     try:
         data = json.loads(line)
         events.append(Event.from_dict(data))
     except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as e:
         logger.warning("Skipping malformed event line: %s", str(e)[:100])
     ```

  2. Use `logging.getLogger(__name__)` for the warning
  3. Count skipped lines and log a summary if any were skipped
- **Files**: `src/specify_cli/telemetry/store.py` (modify)
- **Notes**: Consistent with `status/store.py`'s `read_events_raw()` which also skips bad lines. Catch `ValidationError` from Pydantic in case `Event.from_dict()` rejects invalid data.

### Subtask T006 – Write unit tests for SimpleJsonStore

- **Purpose**: Achieve 90%+ coverage for the store module.
- **Steps**:
  1. Create `tests/specify_cli/telemetry/__init__.py` (empty)
  2. Create `tests/specify_cli/telemetry/test_store.py`
  3. Test cases:
     - **test_save_and_load_events**: Save 3 events with different aggregate_ids, load by aggregate, verify filtering and sort order
     - **test_save_and_load_all**: Save events, load_all, verify all returned sorted by `(lamport_clock, node_id)`
     - **test_idempotent_save**: Save same event twice, verify only one entry in file
     - **test_empty_file**: Load from non-existent file, verify empty list
     - **test_malformed_line_skipped**: Write a corrupt line + valid event, verify valid event returned and warning logged
     - **test_sort_order**: Save events with various lamport_clock values out of order, verify sorted correctly
     - **test_creates_parent_dirs**: Save to a path with non-existent parent dirs, verify dirs created
     - **test_large_file_performance**: Save 1000 events, verify load completes in <2 seconds
  4. Use `tmp_path` fixture for all file paths
  5. Create helper: `make_event(event_id, aggregate_id, lamport_clock, node_id, event_type, payload)` factory
- **Files**: `tests/specify_cli/telemetry/__init__.py` (new), `tests/specify_cli/telemetry/test_store.py` (new, ~150 lines)
- **Notes**: Import `Event` from `specify_cli.spec_kitty_events.models` for creating test events. Use `python-ulid` to generate valid ULIDs for `event_id`. For the malformed line test, manually write a bad line to the JSONL file before loading.

## Risks & Mitigations

- **Pydantic `Event.from_dict()` may raise unexpected exceptions**: Catch broad `Exception` in malformed-line handler as fallback, but log the specific type for debugging.
- **`event.to_dict()` datetime serialization**: Pydantic's `model_dump()` serializes datetime as ISO string. Verify round-trip in tests (`to_dict()` → JSON → `from_dict()`).
- **File encoding**: Always use `encoding="utf-8"` for reads and writes. The constitution requires cross-platform support.

## Review Guidance

- Verify `SimpleJsonStore` implements all three `EventStore` ABC methods
- Verify idempotency: same event_id saved twice produces one line in file
- Verify corruption tolerance: malformed lines don't crash reads
- Verify sort order matches `InMemoryEventStore` behavior: `(lamport_clock, node_id)`
- Check that no existing tests are broken by the new package
- Run `mypy --strict src/specify_cli/telemetry/` and verify clean

## Activity Log

- 2026-02-15T19:43:21Z – system – lane=planned – Prompt created.
- 2026-02-15T20:04:52Z – claude-opus – shell_pid=497135 – lane=doing – Assigned agent via workflow command
- 2026-02-15T20:12:21Z – claude-opus – shell_pid=497135 – lane=for_review – Ready for review: SimpleJsonStore with 15 tests, 90% coverage, mypy/ruff clean
- 2026-02-15T20:17:37Z – copilot – shell_pid=501650 – lane=doing – Started review via workflow command
- 2026-02-15T20:21:30Z – copilot – shell_pid=501650 – lane=done – Review passed: All 15 tests pass, mypy/ruff clean, no regressions. EventStore ABC fully implemented with idempotent writes, malformed-line tolerance, stream-parsed reads, correct sort order.
