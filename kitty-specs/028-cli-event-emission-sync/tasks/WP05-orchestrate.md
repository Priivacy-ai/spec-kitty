---
work_package_id: "WP05"
subtasks:
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "Orchestrate Integration"
phase: "Phase 2 - Command Wiring"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-03T18:58:09Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Orchestrate Integration

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- `spec-kitty orchestrate` emits `WPAssigned` events when agents are assigned (SC-005)
- WPAssigned includes `phase` (implementation/review) and `agent_id`
- Fallback agent assignments include `retry_count`
- `FeatureCompleted` emits when all WPs reach done status
- `DependencyResolved` emits when WP completes and unblocks dependents

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/028-cli-event-emission-sync/spec.md` - User Story 5
- **Plan**: `kitty-specs/028-cli-event-emission-sync/plan.md` - Orchestration events
- **Data Model**: `kitty-specs/028-cli-event-emission-sync/data-model.md` - WPAssigned, FeatureCompleted, DependencyResolved

### Functional Requirements
- FR-023: `orchestrate` MUST emit `WPAssigned` events when agents are assigned to WPs

### Dependencies
- WP01 (Event Factory) must be complete
- Import from `specify_cli.sync.events`

---

## Subtasks & Detailed Guidance

### Subtask T023 - WPAssigned on Agent Assignment

- **Purpose**: Emit WPAssigned event when orchestrator assigns agent to work package
- **Steps**:
  1. Open `src/specify_cli/cli/commands/orchestrate.py`
  2. Add import:
     ```python
     from specify_cli.sync.events import (
         emit_wp_assigned,
         emit_feature_completed,
         emit_dependency_resolved,
     )
     ```
  3. Locate the point where orchestrator assigns an agent to a WP
  4. Emit event after assignment decision:
     ```python
     try:
         emit_wp_assigned(
             wp_id=wp_id,
             agent_id=agent_name,  # "claude", "codex", "opencode"
             phase="implementation",  # or "review"
             retry_count=0,
         )
     except Exception as e:
         console.print(f"[yellow]Warning:[/yellow] WPAssigned emission failed: {e}")
     ```
- **Files**: `src/specify_cli/cli/commands/orchestrate.py`
- **Parallel?**: No (establishes pattern for T024-T028)
- **Notes**:
  - Orchestrator manages the agent lifecycle, so it knows assignment details
  - agent_id should match the agent's canonical name

### Subtask T024 - Phase=Implementation Tracking

- **Purpose**: Emit WPAssigned with phase=implementation when implementation starts
- **Steps**:
  1. Identify the point where implementation agent is selected
  2. Emit event with `phase="implementation"`:
     ```python
     emit_wp_assigned(
         wp_id=wp_id,
         agent_id=impl_agent,
         phase="implementation",
         retry_count=retry_count,
     )
     ```
  3. Ensure this happens BEFORE the agent starts actual work
- **Files**: `src/specify_cli/cli/commands/orchestrate.py`
- **Parallel?**: No (part of assignment flow)
- **Notes**:
  - Implementation phase is when agent writes code
  - This event lets dashboard show "WP01: claude implementing"

### Subtask T025 - Phase=Review Tracking

- **Purpose**: Emit WPAssigned with phase=review when review agent is assigned
- **Steps**:
  1. Identify the point where review agent is selected
  2. Emit event with `phase="review"`:
     ```python
     emit_wp_assigned(
         wp_id=wp_id,
         agent_id=review_agent,
         phase="review",
         retry_count=0,
     )
     ```
  3. This typically happens after implementation is complete and WP moves to for_review
- **Files**: `src/specify_cli/cli/commands/orchestrate.py`
- **Parallel?**: Yes (independent from T024 logic path)
- **Notes**:
  - Review phase is when a different agent validates the work
  - Same WP may have multiple WPAssigned events (impl, then review)

### Subtask T026 - Retry Count Tracking

- **Purpose**: Include retry_count when fallback agents are used
- **Steps**:
  1. Orchestrator tracks retries when primary agent fails
  2. On first assignment: `retry_count=0`
  3. On fallback assignment: `retry_count=1`, `retry_count=2`, etc.
  4. Pass retry_count to emit_wp_assigned:
     ```python
     emit_wp_assigned(
         wp_id=wp_id,
         agent_id=fallback_agent,
         phase=phase,
         retry_count=current_retry_count,
     )
     ```
  5. Dashboard can use this to show "WP01: opencode (retry 2)"
- **Files**: `src/specify_cli/cli/commands/orchestrate.py`
- **Parallel?**: No (cross-cutting tracking)
- **Notes**:
  - Retry count helps identify problematic WPs that keep failing
  - Orchestrator likely already tracks this for its own logic

### Subtask T027 - FeatureCompleted Emission

- **Purpose**: Emit FeatureCompleted when all WPs reach done status
- **Steps**:
  1. After each WP completes, check if ALL WPs are done
  2. If all done, emit FeatureCompleted:
     ```python
     if all_wps_done(feature_slug):
         try:
             emit_feature_completed(
                 feature_slug=feature_slug,
                 total_wps=total_wp_count,
                 completed_at=datetime.now(timezone.utc).isoformat(),
                 total_duration=calculate_duration(start_time),  # optional
             )
         except Exception as e:
             console.print(f"[yellow]Warning:[/yellow] FeatureCompleted emission failed: {e}")
     ```
  3. This should only emit ONCE per feature
- **Files**: `src/specify_cli/cli/commands/orchestrate.py`
- **Parallel?**: No (final event in lifecycle)
- **Notes**:
  - FeatureCompleted signals the feature is ready for merge to main
  - total_duration is optional; calculate if orchestrator tracks start time

### Subtask T028 - DependencyResolved Emission

- **Purpose**: Emit DependencyResolved when WP completes and unblocks dependents
- **Steps**:
  1. When a WP reaches done status, find WPs that depend on it
  2. For each dependent WP, emit DependencyResolved:
     ```python
     for dependent_wp in get_dependents(completed_wp_id):
         try:
             emit_dependency_resolved(
                 wp_id=dependent_wp,
                 dependency_wp_id=completed_wp_id,
                 resolution_type="completed",
             )
         except Exception as e:
             console.print(f"[yellow]Warning:[/yellow] DependencyResolved emission failed: {e}")
     ```
  3. resolution_type values: "completed", "skipped", "merged"
- **Files**: `src/specify_cli/cli/commands/orchestrate.py`
- **Parallel?**: Yes (can emit multiple in parallel conceptually)
- **Notes**:
  - This helps dashboard show "WP02 unblocked by WP01 completion"
  - Use existing dependency graph logic from workspace-per-WP feature

---

## Test Strategy

Tests are covered in WP07, but verify manually:
```bash
# Run orchestrate on a test feature
spec-kitty orchestrate --feature 028-cli-event-emission-sync --dry-run

# Check events in queue
python -c "
from specify_cli.sync.queue import OfflineQueue
q = OfflineQueue()
events = q.drain_queue(limit=30)
assign_events = [e for e in events if e['event_type'] == 'WPAssigned']
print(f'Found {len(assign_events)} WPAssigned events')
for e in assign_events:
    p = e['payload']
    print(f\"  {p['wp_id']}: {p['agent_id']} phase={p['phase']} retry={p.get('retry_count', 0)}\")
"
```

Verify:
1. WPAssigned events emitted for each agent assignment
2. phase field correctly distinguishes implementation vs review
3. retry_count increments on fallback assignments
4. FeatureCompleted emits once at the end (if running to completion)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Orchestrate complexity | Instrument carefully, don't disrupt core logic |
| Missing dependency info | Use existing DependencyGraph from WP feature |
| Double FeatureCompleted | Add flag to prevent multiple emissions |
| Agent ID mismatch | Use canonical agent names consistently |

---

## Review Guidance

- Verify WPAssigned emits at assignment time, not at completion
- Verify phase field is set correctly (implementation vs review)
- Verify retry_count increments on fallbacks
- Run orchestrate on a small feature to see full event flow
- Check FeatureCompleted only emits once

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-03T18:58:09Z - system - lane=planned - Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP05 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
