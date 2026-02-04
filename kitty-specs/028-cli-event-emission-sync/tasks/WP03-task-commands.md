---
work_package_id: WP03
title: Task Command Integration
lane: "doing"
dependencies: [WP01]
base_branch: 028-cli-event-emission-sync-WP01
base_commit: 9803132cccfd6602b0c5e16c535bb105439b00ce
created_at: '2026-02-04T11:32:42.132700+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Phase 2 - Command Wiring
assignee: ''
agent: ''
shell_pid: "36901"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T18:58:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 - Task Command Integration

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- `spec-kitty agent tasks move-task WP01 --to for_review` emits `WPStatusChanged` event
- `spec-kitty agent tasks mark-status WP01 --status done` emits `WPStatusChanged` event
- `spec-kitty agent tasks add-history WP01 --note "..."` emits `HistoryAdded` event
- Errors during command execution emit `ErrorLogged` events
- Lamport clock increments correctly across sequential commands (SC-009)

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/028-cli-event-emission-sync/spec.md` - User Story 3
- **Plan**: `kitty-specs/028-cli-event-emission-sync/plan.md` - Command integration patterns
- **Data Model**: `kitty-specs/028-cli-event-emission-sync/data-model.md` - HistoryAdded payload

### Functional Requirements
- FR-019: `move-task` MUST emit `WPStatusChanged` with correct status transition
- FR-020: `mark-status` MUST emit `WPStatusChanged` with new status
- FR-021: `add-history` MUST emit `HistoryAdded` event
- FR-029: MUST NOT block CLI command execution when event emission fails

### Dependencies
- WP01 (Event Factory) must be complete
- Import from `specify_cli.sync.events`

---

## Subtasks & Detailed Guidance

### Subtask T013 - Move-Task Event Emission

- **Purpose**: Emit WPStatusChanged when work package moves between lanes
- **Steps**:
  1. Open `src/specify_cli/cli/commands/agent/tasks.py`
  2. Locate the `move_task` command function
  3. Add import: `from specify_cli.sync.events import emit_wp_status_changed`
  4. Determine previous status from current WP frontmatter before the move
  5. After successful lane update, emit event:
     ```python
     try:
         emit_wp_status_changed(
             wp_id=wp_id,
             previous_status=current_lane,  # before move
             new_status=target_lane,         # --to argument
             changed_by=agent or "user",
             feature_slug=feature_slug,
         )
     except Exception as e:
         console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")
     ```
  6. Extract agent name from context if running as part of orchestration
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py`
- **Parallel?**: No (establishes pattern for T014, T015)
- **Notes**:
  - `current_lane` must be read BEFORE updating frontmatter
  - Lane values: "planned", "doing", "for_review", "done"
  - If agent context is available (e.g., from orchestrator), use it for `changed_by`

### Subtask T014 - Mark-Status Event Emission

- **Purpose**: Emit WPStatusChanged when mark-status command updates WP status
- **Steps**:
  1. In same file `src/specify_cli/cli/commands/agent/tasks.py`
  2. Locate the `mark_status` command function
  3. Read current status before update
  4. After successful status update, emit event:
     ```python
     try:
         emit_wp_status_changed(
             wp_id=wp_id,
             previous_status=current_status,
             new_status=new_status,
             changed_by=agent or "user",
             feature_slug=feature_slug,
         )
     except Exception as e:
         console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")
     ```
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py`
- **Parallel?**: Yes (independent function from T015)
- **Notes**:
  - mark-status may be similar to move-task; verify they have different semantics
  - Both update lane, but through different interfaces

### Subtask T015 - Add-History Event Emission

- **Purpose**: Emit HistoryAdded when history entry is added to work package
- **Steps**:
  1. In same file `src/specify_cli/cli/commands/agent/tasks.py`
  2. Locate the `add_history` command function
  3. Add import: `from specify_cli.sync.events import emit_history_added`
  4. After successful history addition, emit event:
     ```python
     try:
         emit_history_added(
             wp_id=wp_id,
             entry_type=entry_type,  # "note", "review", "error", "comment"
             entry_content=content,
             author=agent or "user",
         )
     except Exception as e:
         console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")
     ```
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py`
- **Parallel?**: Yes (independent function from T014)
- **Notes**:
  - `entry_type` should map to enum: "note", "review", "error", "comment"
  - `author` identifies who added the entry (user or agent)

### Subtask T016 - ErrorLogged Event Emission

- **Purpose**: Emit ErrorLogged event when commands encounter errors
- **Steps**:
  1. Identify error handling points in task commands
  2. Add import: `from specify_cli.sync.events import emit_error_logged`
  3. When catching exceptions that indicate real errors (not just warnings):
     ```python
     try:
         # ... command logic ...
     except ValidationError as e:
         emit_error_logged(
             wp_id=wp_id,
             error_type="validation",
             error_message=str(e),
             agent_id=agent,
         )
         raise  # Re-raise to preserve existing error handling
     except RuntimeError as e:
         emit_error_logged(
             wp_id=wp_id,
             error_type="runtime",
             error_message=str(e),
             stack_trace=traceback.format_exc(),
             agent_id=agent,
         )
         raise
     ```
  4. Map exception types to error_type enum: "validation", "runtime", "network", "auth", "unknown"
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py`
- **Parallel?**: No (cross-cutting concern)
- **Notes**:
  - ErrorLogged emission should NOT fail silently (wrap in try/except)
  - Don't log PII or tokens in error_message
  - stack_trace is optional but helpful for debugging

### Subtask T017 - Lamport Clock Verification

- **Purpose**: Ensure Lamport clock increments correctly for sequential commands
- **Steps**:
  1. Run multiple commands in sequence manually
  2. Inspect emitted events (via queue or logs) to verify clock values
  3. Verify clock is monotonically increasing: event1.clock < event2.clock < event3.clock
  4. Add logging (debug level) showing clock value at emission time:
     ```python
     logger.debug(f"Emitting event with Lamport clock: {clock_value}")
     ```
  5. Verify clock persists across CLI restarts (check `~/.spec-kitty/clock.json`)
- **Files**: `src/specify_cli/sync/emitter.py` (logging), verification script
- **Parallel?**: No (verification task)
- **Notes**:
  - This is primarily a verification task, not new code
  - If clock doesn't increment correctly, bug is in WP01 (LamportClock)
  - Document verification steps in test plan for WP07

---

## Test Strategy

Tests are covered in WP07, but verify manually:
```bash
# Test move-task
spec-kitty agent tasks move-task WP01 --to doing
spec-kitty agent tasks move-task WP01 --to for_review

# Check events in queue
python -c "
from specify_cli.sync.queue import OfflineQueue
q = OfflineQueue()
for e in q.drain_queue(limit=5):
    print(f\"{e['event_type']}: {e['payload']}\")
"

# Verify Lamport clock
cat ~/.spec-kitty/clock.json
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Agent context not available | Default to "user" for changed_by/author |
| Duplicate event emission | Ensure emit happens only once per state change |
| Clock not incrementing | Verify WP01 LamportClock.tick() implementation |
| Error emission failing | Wrap in try/except, don't block on error logging |

---

## Review Guidance

- Verify all three commands (move-task, mark-status, add-history) have event emission
- Verify previous_status is captured BEFORE the state change
- Verify ErrorLogged events include useful context without PII
- Run sequential commands and verify Lamport clock increments
- Check that agent name propagates when running under orchestration

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-03T18:58:09Z - system - lane=planned - Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP03 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
