---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "Finalize-Tasks Integration"
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

# Work Package Prompt: WP04 - Finalize-Tasks Integration

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- `spec-kitty agent feature finalize-tasks` emits 1 `FeatureCreated` + N `WPCreated` events (SC-004)
- All batch events share the same `causation_id` for correlation
- `WPCreated` events include dependency information
- `FeatureCreated` includes feature metadata from meta.json

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/028-cli-event-emission-sync/spec.md` - User Story 4
- **Plan**: `kitty-specs/028-cli-event-emission-sync/plan.md` - Batch event pattern
- **Data Model**: `kitty-specs/028-cli-event-emission-sync/data-model.md` - FeatureCreated, WPCreated payloads

### Functional Requirements
- FR-022: `finalize-tasks` MUST emit `FeatureCreated` + `WPCreated` events for all WPs
- FR-029: MUST NOT block CLI command execution when event emission fails

### Dependencies
- WP01 (Event Factory) must be complete
- Import from `specify_cli.sync.events`

---

## Subtasks & Detailed Guidance

### Subtask T018 - FeatureCreated Event Emission

- **Purpose**: Emit FeatureCreated event when feature is finalized
- **Steps**:
  1. Open `src/specify_cli/cli/commands/agent/feature.py`
  2. Locate the `finalize_tasks` command function
  3. Add imports:
     ```python
     from specify_cli.sync.events import (
         emit_feature_created,
         emit_wp_created,
         get_emitter,
     )
     ```
  4. After tasks.md is parsed and WPs are validated:
     ```python
     # Generate causation_id for batch correlation
     causation_id = get_emitter().generate_causation_id()

     try:
         emit_feature_created(
             feature_slug=feature_slug,
             feature_number=feature_number,
             target_branch=target_branch,
             wp_count=len(work_packages),
             causation_id=causation_id,
         )
     except Exception as e:
         console.print(f"[yellow]Warning:[/yellow] FeatureCreated emission failed: {e}")
     ```
- **Files**: `src/specify_cli/cli/commands/agent/feature.py`
- **Parallel?**: No (must emit before WPCreated events)
- **Notes**:
  - FeatureCreated should be emitted FIRST, then WPCreated for each WP
  - This establishes the feature context in the event stream

### Subtask T019 - WPCreated Batch Emission

- **Purpose**: Emit WPCreated event for each work package
- **Steps**:
  1. After FeatureCreated emission, iterate over work packages
  2. Emit WPCreated for each:
     ```python
     for wp in work_packages:
         try:
             emit_wp_created(
                 wp_id=wp.id,
                 title=wp.title,
                 dependencies=wp.dependencies or [],
                 feature_slug=feature_slug,
                 causation_id=causation_id,
             )
         except Exception as e:
             console.print(f"[yellow]Warning:[/yellow] WPCreated emission failed for {wp.id}: {e}")
     ```
  3. Continue iteration even if individual emissions fail
- **Files**: `src/specify_cli/cli/commands/agent/feature.py`
- **Parallel?**: No (sequential emission within batch)
- **Notes**:
  - Do NOT stop batch on individual failures
  - Each WP gets its own event with shared causation_id
  - Lamport clock increments for each event in batch

### Subtask T020 - Shared Causation ID Generation

- **Purpose**: Generate and share causation_id across batch events
- **Steps**:
  1. Add `generate_causation_id()` method to EventEmitter if not exists:
     ```python
     def generate_causation_id(self) -> str:
         """Generate ULID for batch event correlation."""
         return ulid.new().str
     ```
  2. Generate causation_id ONCE at the start of finalize-tasks
  3. Pass same causation_id to all emit functions in the batch
  4. Verify events in queue all have same causation_id
- **Files**: `src/specify_cli/sync/emitter.py`, `src/specify_cli/cli/commands/agent/feature.py`
- **Parallel?**: No (coordination task)
- **Notes**:
  - causation_id links FeatureCreated + all WPCreated as a single logical action
  - Server can use this to group events in the UI

### Subtask T021 - Dependency Information in WPCreated

- **Purpose**: Include WP dependencies in WPCreated payload
- **Steps**:
  1. When parsing tasks.md, extract dependencies for each WP
  2. Dependencies are typically in frontmatter: `dependencies: ["WP01", "WP02"]`
  3. Pass dependencies list to emit_wp_created:
     ```python
     emit_wp_created(
         wp_id=wp.id,
         title=wp.title,
         dependencies=wp.dependencies or [],  # ["WP01", "WP02"]
         feature_slug=feature_slug,
         causation_id=causation_id,
     )
     ```
  4. Verify WPCreated payload schema includes dependencies array
- **Files**: `src/specify_cli/cli/commands/agent/feature.py`
- **Parallel?**: No (part of WPCreated emission)
- **Notes**:
  - Dependencies are WP IDs that must complete before this WP can start
  - Empty list if no dependencies
  - Schema validates dependencies as array of WP ID patterns

### Subtask T022 - Meta.json Extraction for FeatureCreated

- **Purpose**: Extract feature metadata from meta.json for event payload
- **Steps**:
  1. Locate meta.json in feature directory
  2. Parse JSON to extract:
     - `feature_slug` (e.g., "028-cli-event-emission-sync")
     - `feature_number` (e.g., "028")
     - `target_branch` (e.g., "2.x")
  3. Pass to emit_feature_created:
     ```python
     import json
     meta_path = feature_dir / "meta.json"
     with open(meta_path) as f:
         meta = json.load(f)

     emit_feature_created(
         feature_slug=meta["slug"],
         feature_number=meta["feature_number"],
         target_branch=meta["target_branch"],
         wp_count=len(work_packages),
         causation_id=causation_id,
     )
     ```
  4. Handle missing meta.json gracefully (log warning, skip emission)
- **Files**: `src/specify_cli/cli/commands/agent/feature.py`
- **Parallel?**: No (data extraction)
- **Notes**:
  - meta.json should already exist (created during /spec-kitty.specify)
  - Fallback: derive feature_slug from directory name if meta.json missing

---

## Test Strategy

Tests are covered in WP07, but verify manually:
```bash
# Run finalize-tasks on a test feature
spec-kitty agent feature finalize-tasks --feature 028-cli-event-emission-sync

# Check events in queue
python -c "
from specify_cli.sync.queue import OfflineQueue
q = OfflineQueue()
events = q.drain_queue(limit=20)
feature_events = [e for e in events if e['event_type'] in ('FeatureCreated', 'WPCreated')]
print(f'Found {len(feature_events)} feature/WP events')
for e in feature_events:
    print(f\"  {e['event_type']}: {e['aggregate_id']} causation={e.get('causation_id', 'none')[:8]}...\")
"
```

Verify:
1. Exactly 1 FeatureCreated event
2. N WPCreated events (one per WP)
3. All events share same causation_id
4. WPCreated events include dependencies array

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| tasks.md parsing failures | Reuse existing parsing logic, don't reimplement |
| meta.json missing | Graceful degradation with warning |
| Partial batch emission | Continue on individual failures, log each |
| causation_id not shared | Generate once, pass to all emit calls |

---

## Review Guidance

- Verify FeatureCreated emits BEFORE WPCreated events
- Verify all events in batch have same causation_id
- Verify wp_count matches actual number of WPCreated events
- Verify dependencies array is populated correctly for each WP
- Run with --dry-run if available to preview without side effects

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-03T18:58:09Z - system - lane=planned - Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP04 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
