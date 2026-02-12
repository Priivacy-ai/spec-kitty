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
- Aggregate query methods are added to `queue.py` with tests
- Existing sync tests pass with zero regressions

## Context & Constraints

- **Delivery branch**: 2.x
- **Actual queue schema**: SQLite table `queue(id, event_id, event_type, data, timestamp, retry_count)`
- **Data model**: See `data-model.md` (QueueStats entity)
- **Current state**: `sync status` on 2.x likely shows only connection/auth health — needs queue health extension
- **Reference**: `spec.md` (User Story 3, FR-006), `plan.md` (WP05)

## Subtasks & Detailed Guidance

### Subtask T020 – Add aggregate query methods to queue.py

- **Purpose**: Provide queue statistics for the extended status display.
- **Steps**:
  1. Read `src/specify_cli/sync/queue.py` on 2.x to confirm current structure
  2. Add `get_queue_stats()` returning a `QueueStats` dataclass:
     ```python
     @dataclass
     class QueueStats:
         total_queued: int
         total_retried: int
         oldest_event_age: Optional[timedelta]
         retry_distribution: dict[str, int]  # bucket -> count
         top_event_types: list[tuple[str, int]]  # (event_type, count)
     ```
  3. Implement with queries over `queue`:
     ```sql
     SELECT COUNT(*) FROM queue;

     SELECT COUNT(*) FROM queue WHERE retry_count > 0;

     SELECT MIN(timestamp) FROM queue;

     SELECT
       CASE
         WHEN retry_count = 0 THEN '0 retries'
         WHEN retry_count BETWEEN 1 AND 3 THEN '1-3 retries'
         ELSE '4+ retries'
       END as bucket,
       COUNT(*) as count
     FROM queue
     GROUP BY bucket;

     SELECT event_type, COUNT(*) as count
     FROM queue
     GROUP BY event_type
     ORDER BY count DESC
     LIMIT 5;
     ```
  4. Convert `MIN(timestamp)` (unix epoch seconds) to `timedelta` using `datetime.now()` minus `datetime.fromtimestamp(...)`
- **Files**: `src/specify_cli/sync/queue.py` (edit)
- **Parallel?**: No — foundation for T021-T023

### Subtask T021 – Group queued events by event_type

- **Purpose**: Show which event types are most common in backlog/retries.
- **Steps**:
  1. Prefer using the `event_type` column directly (no JSON extraction needed)
  2. Return top 5 event types by count in `QueueStats.top_event_types`
  3. If needed for compatibility, fall back to parsing `data` JSON
- **Files**: `src/specify_cli/sync/queue.py` (edit, part of T020)
- **Parallel?**: Yes — can proceed alongside retry histogram logic

### Subtask T022 – Format output with Rich tables/panels

- **Purpose**: Display queue health clearly.
- **Steps**:
  1. Add formatter function for queue stats (summary + retry distribution + top types)
  2. Add `humanize_timedelta()` helper for oldest event age
  3. Keep output non-breaking for non-TTY CI runs
- **Files**: CLI command file for `sync status`, or a small formatter helper module
- **Parallel?**: Yes — can use mocked `QueueStats`

### Subtask T023 – Integrate queue stats into sync status command

- **Purpose**: Wire stats into existing `sync status` command output.
- **Steps**:
  1. Find existing `sync status` command on 2.x
  2. After connection/auth output, append queue health section:
     ```python
     queue = OfflineQueue()
     stats = queue.get_queue_stats()

     if stats.total_queued > 0:
         format_queue_health(stats, console)
     else:
         console.print("\n[green]Queue empty — all events synced.[/green]")
     ```
  3. Ensure output order remains stable for tests
- **Files**: CLI command file for sync status
- **Parallel?**: No — depends on T020 and T022

### Subtask T024 – Write tests for aggregate queries and output

- **Purpose**: Validate aggregate stats and formatting.
- **Steps**:
  1. Extend queue/status tests for:
     - empty queue
     - queue with retried events
     - retry distribution buckets
     - top event-type ranking
     - oldest age calculation from `timestamp`
  2. Use tmp SQLite DB fixture (`OfflineQueue(db_path=...)`)
  3. Run: `python -m pytest tests/sync/ -x -v`
- **Files**: `tests/sync/test_offline_queue.py` (extend), `tests/sync/test_runtime.py` or status-command test file (extend)
- **Parallel?**: No — depends on T020-T023

## Test Strategy

- **New tests**: ~6 tests for aggregate queries and output formatting
- **Run command**: `python -m pytest tests/sync/ -x -v`
- **Fixtures**: Temporary SQLite database with seeded events

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Queue schema assumptions drift | Read actual `queue.py` schema first |
| SQLite features differ in CI | Prefer simple SQL over optional JSON functions |
| Rich output fragile in CI | Assert semantic content, not exact ANSI formatting |

## Review Guidance

- Verify queries use the real `queue` table/columns on 2.x
- Verify oldest age derives from epoch `timestamp`
- Verify Rich output is readable and stable
- Run `python -m pytest tests/sync/ -x -v` — tests green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
