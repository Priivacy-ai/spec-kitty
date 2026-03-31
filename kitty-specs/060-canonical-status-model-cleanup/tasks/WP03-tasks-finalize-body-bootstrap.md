---
work_package_id: WP03
title: tasks.py Changes
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-007
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T006, T007, T008, T009, T010]
history:
- at: '2026-03-31T06:58:09+00:00'
  actor: planner
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py
---

# WP03: tasks.py Changes

## Objective

Three changes to `tasks.py`: (1) integrate canonical bootstrap into finalize-tasks, (2) remove `lane=` from body-note format strings, (3) delete the move_task bootstrap/sync block and replace with hard-fail.

## Context

- `tasks.py` finalize-tasks is at lines 1621-1747. Currently parses dependencies only.
- Body-note writers at lines 1169 and 1572 append `lane={target_lane}` to activity log entries.
- Bootstrap/sync block at lines 1088-1115 seeds canonical events from frontmatter when canonical state is missing in `move_task()`.

**Sequencing within this WP**: Apply changes in order: (1) add bootstrap, (2) clean body notes, (3) delete bootstrap/sync block. The agent should implement and test in this order.

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

---

## Subtask T006: Integrate Bootstrap + --validate-only

**Purpose**: Mirror WP02's feature.py integration for the tasks.py entrypoint.

**Steps**:
1. Read `finalize_tasks()` in tasks.py around line 1621
2. After dependency parsing + validation, add the same bootstrap call:
   ```python
   from specify_cli.status.bootstrap import bootstrap_canonical_state
   result = bootstrap_canonical_state(feature_dir, feature_slug, dry_run=validate_only)
   ```
3. Note: tasks.py finalize-tasks may not have `--validate-only` yet. Add it if missing (match feature.py's interface).
4. Include bootstrap stats in JSON output

**Files**: `src/specify_cli/cli/commands/agent/tasks.py` (~20 lines added)

---

## Subtask T007: Remove lane= from move_task Body Note

**Location**: `tasks.py` around line 1169

**Steps**:
1. Find the format string that generates the activity log entry in `move_task()`
2. Current pattern: `- {timestamp} – {agent} – {shell_pid_part}lane={target_lane} – {note}`
3. Remove `lane={target_lane}` from the format string
4. Result: `- {timestamp} – {agent} – {shell_pid_part}{note}`

**Files**: `src/specify_cli/cli/commands/agent/tasks.py` (~2 lines changed)

---

## Subtask T008: Remove lane= from add_note Body Note

**Location**: `tasks.py` around line 1572

**Steps**: Same pattern as T007. Remove `lane={current_lane}` from the format string.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py` (~2 lines changed)

---

## Subtask T009: Delete Bootstrap/Sync Block + Hard-Fail

**Location**: `tasks.py` lines 1088-1115

**Steps**:
1. Delete the entire block that checks `current_canonical_lane != "planned"` and emits a bootstrap event from frontmatter
2. Replace with a hard-fail check:
   ```python
   if current_event_lane is None:
       # No canonical state for this WP — finalize-tasks must be run first
       raise RuntimeError(
           f"WP {task_id} has no canonical status in feature {feature_slug}. "
           f"Run `spec-kitty agent feature finalize-tasks --feature {feature_slug}` to initialize."
       )
   ```
3. The `current_event_lane` variable (from the preceding loop that reads events) is already computed — use it directly

**Files**: `src/specify_cli/cli/commands/agent/tasks.py` (~30 lines deleted, ~5 lines added)

---

## Subtask T010: Write Tests

**Steps**:
1. Create `tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py`
2. Tests:
   - finalize-tasks calls `bootstrap_canonical_state()` and includes stats in output
   - move_task body note does NOT contain `lane=`
   - add_note body note does NOT contain `lane=`
   - move_task hard-fails when WP has no canonical event (not bootstrapped)
   - move_task succeeds when WP has canonical event

**Files**: `tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py` (~150 lines)

---

## Definition of Done

- [ ] tasks.py finalize-tasks calls `bootstrap_canonical_state()` with identical behavior to feature.py
- [ ] Body-note format strings no longer include `lane=`
- [ ] Bootstrap/sync block deleted from move_task
- [ ] move_task hard-fails with actionable message when canonical state missing
- [ ] Tests cover all changes
