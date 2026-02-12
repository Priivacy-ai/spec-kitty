---
work_package_id: "WP05"
subtasks:
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Extend sync status with queue health"
phase: "Wave 1 - Independent Fixes"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task WP05 --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-12T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Extend sync status with queue health

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP05
```

No dependencies — branches directly from the 2.x branch.

---

## Objectives & Success Criteria

- `sync status` shows: queue depth, oldest event age, retry-count distribution, top failing event types
- Output formatted with Rich tables/panels matching existing CLI style
- New aggregate query methods added to `queue.py` with tests
- Existing sync tests pass with zero regressions

## Context & Constraints

- **Delivery branch**: 2.x
- **Queue schema**: SQLite with `id`, `data` (JSON), `retry_count`, `created_at`, `last_attempt_at`, `status` (pending/failed/synced)
- **Data model**: See `data-model.md` (QueueStats entity)
- **Current state**: `sync status` on 2.x likely shows only connection/auth health — needs queue health extension
- **Reference**: `spec.md` (User Story 3, FR-006), `plan.md` (WP05)

## Subtasks & Detailed Guidance

### Subtask T020 – Add aggregate query methods to queue.py

- **Purpose**: Provide queue statistics for the extended status display.
- **Steps**:
  1. Read `src/specify_cli/sync/queue.py` on 2.x to understand current structure
  2. Add a `get_queue_stats()` method that returns a `QueueStats` dataclass:
     ```python
     @dataclass
     class QueueStats:
         total_pending: int
         total_failed: int
         oldest_event_age: Optional[timedelta]
         retry_distribution: dict[str, int]  # bucket -> count
         top_event_types: list[tuple[str, int]]  # (event_type, count)
     ```
  3. Implement with SQL queries:
     ```sql
     -- Total pending
     SELECT COUNT(*) FROM events WHERE status = 'pending'

     -- Total failed
     SELECT COUNT(*) FROM events WHERE status = 'failed'

     -- Oldest event age
     SELECT MIN(created_at) FROM events WHERE status IN ('pending', 'failed')

     -- Retry distribution
     SELECT
       CASE
         WHEN retry_count = 0 THEN '0 retries'
         WHEN retry_count BETWEEN 1 AND 3 THEN '1-3 retries'
         ELSE '4+ retries'
       END as bucket,
       COUNT(*) as count
     FROM events WHERE status IN ('pending', 'failed')
     GROUP BY bucket

     -- Top event types (parse from JSON data column)
     SELECT json_extract(data, '$.event_type') as event_type, COUNT(*) as count
     FROM events WHERE status IN ('pending', 'failed')
     GROUP BY event_type ORDER BY count DESC LIMIT 5
     ```
  4. Parse `oldest_event_age` from ISO 8601 string to `timedelta` using `datetime.fromisoformat()`
- **Files**: `src/specify_cli/sync/queue.py` (edit)
- **Parallel?**: No — foundation for T021-T023
- **Notes**: Check the actual table name and column names on 2.x — may differ from documented model.

### Subtask T021 – Group pending events by event_type

- **Purpose**: Show which event types are most common in the queue (indicates failure patterns).
- **Steps**:
  1. The SQL in T020 already extracts `event_type` from JSON
  2. If `json_extract` is not available in the SQLite version, parse events in Python:
     ```python
     import json
     events = cursor.fetchall()
     type_counts = Counter(json.loads(row['data']).get('event_type', 'unknown') for row in events)
     ```
  3. Return as `top_event_types` in QueueStats (top 5 by count, descending)
- **Files**: `src/specify_cli/sync/queue.py` (edit, part of T020's method)
- **Parallel?**: Yes — can be implemented independently of retry distribution logic

### Subtask T022 – Format output with Rich tables/panels

- **Purpose**: Display queue health in a clear, actionable format.
- **Steps**:
  1. Create a formatting function (in the CLI command file or a dedicated formatter):
     ```python
     from rich.table import Table
     from rich.panel import Panel
     from rich.console import Console

     def format_queue_health(stats: QueueStats, console: Console):
         # Summary panel
         panel_text = (
             f"Queue depth: {stats.total_pending + stats.total_failed}\n"
             f"  Pending: {stats.total_pending}\n"
             f"  Failed: {stats.total_failed}\n"
         )
         if stats.oldest_event_age:
             panel_text += f"  Oldest event: {humanize_timedelta(stats.oldest_event_age)}\n"
         console.print(Panel(panel_text, title="Queue Health"))

         # Retry distribution table
         if stats.retry_distribution:
             table = Table(title="Retry Distribution")
             table.add_column("Bucket")
             table.add_column("Count", justify="right")
             for bucket, count in stats.retry_distribution.items():
                 table.add_row(bucket, str(count))
             console.print(table)

         # Top event types table
         if stats.top_event_types:
             table = Table(title="Top Event Types in Queue")
             table.add_column("Event Type")
             table.add_column("Count", justify="right")
             for event_type, count in stats.top_event_types:
                 table.add_row(event_type, str(count))
             console.print(table)
     ```
  2. Add a `humanize_timedelta()` helper:
     ```python
     def humanize_timedelta(td: timedelta) -> str:
         total_seconds = int(td.total_seconds())
         if total_seconds < 60:
             return f"{total_seconds}s ago"
         elif total_seconds < 3600:
             return f"{total_seconds // 60}m ago"
         elif total_seconds < 86400:
             return f"{total_seconds // 3600}h ago"
         else:
             return f"{total_seconds // 86400}d ago"
     ```
- **Files**: CLI command file for sync status, or new formatter module
- **Parallel?**: Yes — can develop independently of T020/T021 (use mock data)

### Subtask T023 – Integrate aggregate data into sync status command

- **Purpose**: Wire the queue stats and formatting into the existing `sync status` output.
- **Steps**:
  1. Find the existing sync status command on 2.x
  2. After the existing connection/auth status output, add the queue health section:
     ```python
     # Existing auth/connection status display...

     # Add queue health
     queue = EventQueue()
     stats = queue.get_queue_stats()

     if stats.total_pending + stats.total_failed > 0:
         format_queue_health(stats, console)
     else:
         console.print("\n[green]Queue empty — all events synced.[/green]")
     ```
  3. Ensure the output flows naturally after the existing auth/connection section
- **Files**: CLI command file for sync status
- **Parallel?**: No — depends on T020 and T022

### Subtask T024 – Write tests for aggregate queries and output

- **Purpose**: Validate SQL queries return correct stats and output is well-formatted.
- **Steps**:
  1. Create or extend tests:
     ```python
     def test_queue_stats_empty():
         """Empty queue returns zero counts and None oldest age."""

     def test_queue_stats_with_events():
         """Queue with events returns correct counts and age."""

     def test_retry_distribution():
         """Events with varying retry counts produce correct histogram."""

     def test_top_event_types():
         """Events of different types return correct top-N ranking."""

     def test_oldest_event_age():
         """Oldest event age computed correctly from created_at."""

     def test_format_queue_health_output(capsys):
         """Formatted output contains expected sections and values."""
     ```
  2. Use a temporary SQLite database for tests:
     ```python
     @pytest.fixture
     def test_queue(tmp_path):
         db_path = tmp_path / "test_queue.db"
         queue = EventQueue(db_path=db_path)
         # Seed with test data
         return queue
     ```
  3. Run: `python -m pytest tests/specify_cli/sync/ -x -v`
- **Files**: `tests/specify_cli/sync/test_queue.py` (extend)
- **Parallel?**: No — depends on T020-T023

## Test Strategy

- **New tests**: ~6 tests for aggregate queries and output formatting
- **Run command**: `python -m pytest tests/specify_cli/sync/ -x -v`
- **Fixtures**: Temporary SQLite database with seeded events

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| SQLite json_extract not available | Fall back to Python-side JSON parsing |
| Queue table schema differs on 2.x | Inspect actual schema before writing SQL |
| Rich output breaks in CI (no terminal) | Use `console.print` which handles non-TTY gracefully |

## Review Guidance

- Verify SQL queries return correct results for edge cases (empty queue, all same retry count, one event type)
- Verify Rich output is readable and well-formatted
- Run `python -m pytest tests/specify_cli/sync/ -x -v` — all tests green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
