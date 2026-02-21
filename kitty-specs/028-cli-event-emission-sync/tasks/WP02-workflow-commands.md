---
work_package_id: WP02
title: Workflow Command Integration
lane: "done"
dependencies: [WP01]
base_branch: 028-cli-event-emission-sync-WP01
base_commit: 9803132cccfd6602b0c5e16c535bb105439b00ce
created_at: '2026-02-04T11:10:57.370962+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - Command Wiring
assignee: ''
agent: "codex"
shell_pid: "40826"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-03T18:58:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 - Workflow Command Integration

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-04

**Issue 1**: Dependency check failed. WP02 depends on WP01, but the WP01 base commit `9803132cccfd6602b0c5e16c535bb105439b00ce` is not contained in `2.x` (only in branch `028-cli-event-emission-sync-WP01`). Please merge WP01 to `2.x` and rebase WP02 onto `2.x` (or the merged WP01) before resubmitting for review.

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

- `spec-kitty implement WP01` emits `WPStatusChanged(planned->doing)` event (SC-001)
- `spec-kitty merge` emits `WPStatusChanged(doing->for_review)` event (SC-002)
- `spec-kitty accept` emits `WPStatusChanged(for_review->done)` event (SC-003)
- Event emission is non-blocking - commands succeed even if emission fails (SC-008)
- Failures are logged as warnings visible to users

## Context & Constraints

### Reference Documents

- **Spec**: `kitty-specs/028-cli-event-emission-sync/spec.md` - User stories 1, 3
- **Plan**: `kitty-specs/028-cli-event-emission-sync/plan.md` - Command integration patterns
- **Quickstart**: `kitty-specs/028-cli-event-emission-sync/quickstart.md` - Usage examples

### Functional Requirements

- FR-016: `implement` MUST emit `WPStatusChanged(planned->doing)` after workspace creation
- FR-017: `merge` MUST emit `WPStatusChanged(doing->for_review)` when WP moves to review
- FR-018: `accept` MUST emit `WPStatusChanged(for_review->done)` when WP is accepted
- FR-029: MUST NOT block CLI command execution when event emission fails
- FR-030: MUST log event emission failures as warnings

### Dependencies

- WP01 (Event Factory) must be complete
- Import `emit_wp_status_changed` from `specify_cli.sync.events`

---

## Subtasks & Detailed Guidance

### Subtask T008 - Implement Command Event Emission

- **Purpose**: Emit WPStatusChanged when workspace is created for a work package
- **Steps**:
  1. Open `src/specify_cli/cli/commands/implement.py`
  2. Add import: `from specify_cli.sync.events import emit_wp_status_changed`
  3. Locate the point AFTER workspace creation succeeds
  4. Add event emission call wrapped in try/except:

     ```python
     try:
         emit_wp_status_changed(
             wp_id=wp_id,
             previous_status="planned",
             new_status="doing",
             changed_by="user",
             feature_slug=feature_slug,
         )
     except Exception as e:
         console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")
     ```

  5. Ensure the try/except does NOT affect the return value or flow of the command
- **Files**: `src/specify_cli/cli/commands/implement.py`
- **Parallel?**: No (establishes pattern for T009, T010)
- **Notes**:
  - Extract `feature_slug` from context (meta.json or directory name)
  - `wp_id` is already available as command argument
  - `changed_by` should be "user" for CLI-initiated commands

### Subtask T009 - Merge Command Event Emission

- **Purpose**: Emit WPStatusChanged when merge command completes
- **Steps**:
  1. Open `src/specify_cli/cli/commands/merge.py`
  2. Add import: `from specify_cli.sync.events import emit_wp_status_changed`
  3. Locate the point AFTER successful merge operation
  4. Add event emission using same pattern as T008:

     ```python
     try:
         emit_wp_status_changed(
             wp_id=wp_id,
             previous_status="doing",
             new_status="for_review",
             changed_by="user",
             feature_slug=feature_slug,
         )
     except Exception as e:
         console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")
     ```

  5. Handle case where merge affects multiple WPs (emit for each)
- **Files**: `src/specify_cli/cli/commands/merge.py`
- **Parallel?**: Yes (independent file from T010)
- **Notes**:
  - Merge may process multiple work packages; emit event for each
  - If merge has `--all` flag, iterate and emit for each affected WP

### Subtask T010 - Accept Command Event Emission

- **Purpose**: Emit WPStatusChanged when accept command marks WP as done
- **Steps**:
  1. Open `src/specify_cli/cli/commands/accept.py`
  2. Add import: `from specify_cli.sync.events import emit_wp_status_changed`
  3. Locate the point AFTER successful acceptance
  4. Add event emission using same pattern:

     ```python
     try:
         emit_wp_status_changed(
             wp_id=wp_id,
             previous_status="for_review",
             new_status="done",
             changed_by="user",
             feature_slug=feature_slug,
         )
     except Exception as e:
         console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")
     ```

- **Files**: `src/specify_cli/cli/commands/accept.py`
- **Parallel?**: Yes (independent file from T009)
- **Notes**:
  - Accept command may also emit FeatureCompleted if this is the last WP
  - Check if all WPs are done after acceptance; if so, consider emitting FeatureCompleted

### Subtask T011 - Non-Blocking Try/Except Wrappers

- **Purpose**: Ensure all event emission is wrapped in exception handling
- **Steps**:
  1. Review all three command files (implement, merge, accept)
  2. Verify every `emit_*` call is inside try/except
  3. Verify except block catches `Exception` (broad catch)
  4. Verify except block does NOT re-raise
  5. Verify except block logs a warning but allows command to continue
  6. Consider extracting a helper function if pattern is repeated:

     ```python
     def safe_emit(emit_fn: Callable, *args, **kwargs) -> bool:
         """Emit event safely, logging failures as warnings."""
         try:
             emit_fn(*args, **kwargs)
             return True
         except Exception as e:
             console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")
             return False
     ```

- **Files**: All three command files, optionally `src/specify_cli/sync/events.py`
- **Parallel?**: No (integration task)
- **Notes**:
  - The helper function could live in events.py as a public utility
  - Return value allows callers to check if emission succeeded (optional)

### Subtask T012 - Console Warnings for Failures

- **Purpose**: Ensure users see informative warnings when event emission fails
- **Steps**:
  1. Use Rich console for formatted output
  2. Warning format: `[yellow]Warning:[/yellow] Event emission failed: {error_message}`
  3. Include enough context to debug (event type, WP ID)
  4. Consider adding `--verbose` flag to show full stack trace
  5. Example enhanced warning:

     ```python
     console.print(f"[yellow]Warning:[/yellow] Failed to emit WPStatusChanged for {wp_id}: {e}")
     if verbose:
         console.print_exception()
     ```

- **Files**: All three command files
- **Parallel?**: No (polish task)
- **Notes**:
  - Don't log sensitive data (tokens, full payloads) in warnings
  - Keep warnings concise for normal users, detailed for --verbose

---

## Test Strategy

Tests are covered in WP07, but verify manually:

```bash
# Test implement command
spec-kitty implement WP01 --feature 028-cli-event-emission-sync

# Check queue for event
python -c "from specify_cli.sync.queue import OfflineQueue; q = OfflineQueue(); print(q.size())"

# Test with intentional failure (disconnect auth)
spec-kitty auth logout
spec-kitty implement WP02  # Should show warning but succeed
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Import errors from sync module | Verify WP01 is complete and exports are correct |
| Command flow disruption | Use broad Exception catch, never re-raise |
| Missing feature_slug context | Gracefully handle None (event still valid) |
| Verbose logging in production | Default to concise warnings |

---

## Review Guidance

- Verify each command (implement, merge, accept) has event emission
- Verify try/except wrapping is complete (no emission call outside try block)
- Verify warnings are visible but not alarming (yellow, not red)
- Run each command with auth disabled to verify non-blocking behavior
- Check that events appear in queue when offline

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-03T18:58:09Z - system - lane=planned - Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP02 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

- 2026-02-04T08:29:05Z – test-reviewer – shell_pid=13661 – lane=doing – Started review via workflow command
- 2026-02-04T11:14:31Z – test-reviewer – shell_pid=13661 – lane=for_review – Ready for review: emit WPStatusChanged in implement/merge/accept with safe warnings
- 2026-02-04T11:27:11Z – codex – shell_pid=25757 – lane=doing – Started review via workflow command
- 2026-02-04T11:28:42Z – codex – shell_pid=25757 – lane=planned – Moved to planned
- 2026-02-04T11:31:38Z – claude-opus – shell_pid=36397 – lane=doing – Started implementation via workflow command
- 2026-02-04T11:34:27Z – claude-opus – shell_pid=36397 – lane=for_review – Ready for review: WP01 merged to 2.x, WP02 rebased. Emits WPStatusChanged in implement (planned->doing), merge (doing->for_review), accept (for_review->done). All emissions wrapped in try/except with Rich warnings.
- 2026-02-04T11:35:53Z – codex – shell_pid=40826 – lane=doing – Started review via workflow command
- 2026-02-04T11:37:49Z – codex – shell_pid=40826 – lane=done – Review passed: emit WPStatusChanged in implement/merge/accept with non-blocking warnings
