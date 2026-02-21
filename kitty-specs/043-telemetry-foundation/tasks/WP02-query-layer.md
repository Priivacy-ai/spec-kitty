---
work_package_id: WP02
title: Query Layer
lane: "done"
dependencies: [WP01]
base_branch: feature/doctrine-kitty-2x
base_commit: a3505ae86accdeb8991e664f58da7942909cc00f
created_at: '2026-02-15T20:23:35.097466+00:00'
subtasks:
- T007
- T008
- T009
- T010
phase: Phase 1 - Foundation
assignee: ''
agent: copilot
shell_pid: '503425'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T19:43:21Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Query Layer

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (SimpleJsonStore).

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Provide filtered, typed queries over execution event JSONL logs
- Support single-feature and project-wide (cross-feature) queries
- Filter by: `event_type`, `wp_id`, `agent`, `model`, timeframe (`since`/`until`), `success`
- Empty/missing files return empty results (no errors)
- Cross-feature queries skip missing directories gracefully
- 90%+ test coverage

## Context & Constraints

- **Spec**: FR-008 through FR-012 (query layer requirements)
- **Plan**: AD-2 (per-feature files), AD-3 (SimpleJsonStore)
- **Data model**: `EventFilter` entity, `query_execution_events()`, `query_project_events()`
- **WP01 provides**: `SimpleJsonStore` with `load_events()` and `load_all_events()`
- **Event payload fields**: `wp_id`, `agent`, `model`, `success` accessed via `event.payload.get()`
- **Timestamp**: `event.timestamp` is a `datetime` object from Pydantic

## Subtasks & Detailed Guidance

### Subtask T007 – Create EventFilter dataclass

- **Purpose**: Define a typed filter object for query parameters, avoiding loose kwargs.
- **Steps**:
  1. Create `src/specify_cli/telemetry/query.py`
  2. Define `EventFilter` as a frozen dataclass:

     ```python
     @dataclass(frozen=True)
     class EventFilter:
         event_type: str | None = None
         wp_id: str | None = None
         agent: str | None = None
         model: str | None = None
         since: datetime | None = None
         until: datetime | None = None
         success: bool | None = None
     ```

  3. Add a `matches(self, event: Event) -> bool` method that checks each non-None field:
     - `event_type`: compare to `event.event_type`
     - `wp_id`: compare to `event.payload.get("wp_id")`
     - `agent`: compare to `event.payload.get("agent")`
     - `model`: compare to `event.payload.get("model")`
     - `success`: compare to `event.payload.get("success")`
     - `since`: compare `event.timestamp >= self.since`
     - `until`: compare `event.timestamp <= self.until`
  4. All conditions are ANDed — event must match all non-None filters
- **Files**: `src/specify_cli/telemetry/query.py` (new, ~60 lines)
- **Notes**: The `matches()` method encapsulates filter logic, keeping query functions clean. Datetime comparison requires both sides to be timezone-aware or both naive — the `Event.timestamp` from Pydantic is timezone-aware (UTC).

### Subtask T008 – Implement query_execution_events()

- **Purpose**: Filtered reads over a single feature's `execution.events.jsonl`.
- **Steps**:
  1. In `query.py`, implement:

     ```python
     def query_execution_events(
         feature_dir: Path,
         filters: EventFilter | None = None,
     ) -> list[Event]:
     ```

  2. Instantiate `SimpleJsonStore(feature_dir / "execution.events.jsonl")`
  3. Call `store.load_all_events()` to get all events sorted by `(lamport_clock, node_id)`
  4. If `filters` is not None, filter with `[e for e in events if filters.matches(e)]`
  5. Return the filtered, sorted list
  6. If file doesn't exist: `SimpleJsonStore` already returns empty list — propagate
- **Files**: `src/specify_cli/telemetry/query.py` (modify)
- **Notes**: Default filter (None) returns all events. The constant `EXECUTION_EVENTS_FILE = "execution.events.jsonl"` should be defined at module level.

### Subtask T009 – Implement query_project_events()

- **Purpose**: Cross-feature queries iterating over all `kitty-specs/*/execution.events.jsonl` files.
- **Steps**:
  1. In `query.py`, implement:

     ```python
     def query_project_events(
         repo_root: Path,
         filters: EventFilter | None = None,
     ) -> list[Event]:
     ```

  2. Glob for `repo_root / "kitty-specs" / "*" / EXECUTION_EVENTS_FILE`
  3. For each file found, instantiate `SimpleJsonStore` and load events
  4. Merge all events into a single list
  5. Apply filters if provided
  6. Sort merged list by `(lamport_clock, node_id)` (re-sort after merge since events from different features may interleave)
  7. Skip directories without the events file silently
  8. If no events files found, return empty list
- **Files**: `src/specify_cli/telemetry/query.py` (modify, ~30 lines added)
- **Notes**: Use `Path.glob()` for directory iteration. This is O(features × events) but acceptable for typical projects (10-50 features, <1000 events each).

### Subtask T010 – Write unit tests for query layer

- **Purpose**: Verify filtering, empty results, cross-feature iteration.
- **Steps**:
  1. Create `tests/specify_cli/telemetry/test_query.py`
  2. Test cases:
     - **test_query_no_filter**: Load all events from a feature, verify all returned
     - **test_query_by_event_type**: Filter by `event_type="ExecutionEvent"`, verify only matching events
     - **test_query_by_wp_id**: Filter by `wp_id="WP02"`, verify payload filtering works
     - **test_query_by_agent**: Filter by `agent="claude"`, verify correct results
     - **test_query_by_timeframe**: Filter with `since` and `until`, verify temporal filtering
     - **test_query_combined_filters**: Multiple filters ANDed together
     - **test_query_empty_file**: Query non-existent file, verify empty list
     - **test_query_project_events**: Create 3 feature dirs with events, query project-wide, verify merged and sorted
     - **test_query_project_missing_features**: Some feature dirs missing events file, verify no error
  3. Helper: Create a `seed_events(feature_dir, events)` function that writes events to JSONL via `SimpleJsonStore`
  4. Use `tmp_path` for all file system operations
- **Files**: `tests/specify_cli/telemetry/test_query.py` (new, ~120 lines)
- **Notes**: For timeframe tests, create events with known timestamps spanning a range, then filter with `since`/`until` to verify boundary behavior (inclusive).

## Risks & Mitigations

- **Datetime timezone handling**: `Event.timestamp` is timezone-aware. Ensure `EventFilter.since`/`until` are also timezone-aware (UTC). Add a guard in `matches()` that converts naive datetimes to UTC.
- **Large project-wide queries**: Iterating 50+ feature dirs is acceptable. If performance becomes an issue later, add a centralized index (out of scope for 043).

## Review Guidance

- Verify `EventFilter.matches()` correctly ANDs all non-None conditions
- Verify `query_project_events()` merges and re-sorts correctly across features
- Verify empty/missing files produce empty results (no exceptions)
- Verify timeframe boundaries are inclusive
- Run `mypy --strict src/specify_cli/telemetry/query.py`

## Activity Log

- 2026-02-15T19:43:21Z – system – lane=planned – Prompt created.
- 2026-02-15T20:23:35Z – copilot – shell_pid=503425 – lane=doing – Assigned agent via workflow command
- 2026-02-15T20:55:16Z – copilot – shell_pid=503425 – lane=for_review – Implementation complete: EventFilter, query_execution_events, query_project_events, 11 tests
- 2026-02-15T21:16:04Z – copilot – shell_pid=503425 – lane=done – Review passed: timezone-naive comparison bug fixed, 27 tests pass
