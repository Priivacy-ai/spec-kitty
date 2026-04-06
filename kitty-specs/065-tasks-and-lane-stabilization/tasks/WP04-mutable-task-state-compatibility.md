---
work_package_id: WP04
title: Mutable Task-State Compatibility
dependencies: []
requirement_refs:
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T022, T023, T024, T025]
history:
- at: '2026-04-06T13:45:48+00:00'
  actor: claude
  action: Created WP04 prompt during /spec-kitty.tasks
authoritative_surface: tests/git_ops/
execution_mode: code_change
owned_files:
- tests/git_ops/test_atomic_status_commits_unit.py
- tests/git_ops/test_mark_status_pipe_table.py
---

# WP04 — Mutable Task-State Compatibility

## Objective

Add pipe-table row parsing and mutation to `mark-status` so it can update task state in both checkbox (`- [ ] T001`) and pipe-table (`| T001 | desc | WP01 | [P] |`) formatted `tasks.md` files. Standardize future task generation to emit checkbox format exclusively.

This WP addresses issue #438 (format mismatch between task generation and task mutation).

## Context

### Current State

`mark-status` at `tasks.py:1340-1352` uses a single regex:
```python
re.search(rf'-\s*\[[ x]\]\s*{re.escape(task_id)}\b', line)
```
This matches only checkbox format. Pipe-table rows are invisible to the mutator.

Active mission artifacts (e.g., `kitty-specs/063-universal-charter-rename/tasks.md`) use pipe-table format. Agents calling `mark-status` on these artifacts fail with "No task IDs found in tasks.md".

### Target State

- `mark-status` recognizes both checkbox and pipe-table task rows
- Pipe-table: status markers `[P]` → `[D]` (or vice versa)
- Checkbox: `- [ ]` → `- [x]` (existing behavior preserved)
- Future generation standardized to checkbox format
- No format-selection feature. No auto-migration of existing files.

### Design Decision (Confirmed)

- Checkbox is the canonical emitted format for `/spec-kitty.tasks`
- Pipe-table is a backward-compatible input/mutation format
- No user-facing format selection is added (FR-010b)
- Existing pipe-table files remain editable without migration (FR-010a)

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`
- To start implementation: `spec-kitty implement WP04`

**Owned files note**: This WP shares `tasks.py` with WP01. WP01 modifies the `finalize_tasks` function (lines 1626-1768) and dependency parsing. WP04 modifies the `mark_status` function (lines 1272-1421). These are separate functions with no overlap. They share a lane by ownership overlap, which is correct since both modify the same file.

---

## Subtask T022: Add Pipe-Table Row Detection

**Purpose**: `mark-status` must recognize task IDs in pipe-delimited table rows.

**Steps**:

1. Add a helper function near the `mark_status` function in `tasks.py`:
   ```python
   _PIPE_TABLE_TASK_RE = re.compile(r'\|\s*({task_id})\s*\|')

   def _is_pipe_table_task_row(line: str, task_id: str) -> bool:
       """Match a pipe-delimited row containing the task ID."""
       return bool(re.search(
           rf'\|\s*{re.escape(task_id)}\s*\|',
           line,
       ))
   ```

2. The detection must:
   - Match task IDs in any column position (not just the first)
   - Handle whitespace padding around the ID
   - NOT match the header row or separator row (`|---|---|`)
   - NOT match rows where the task ID appears as a substring of a longer token

3. Add a guard against matching header/separator rows:
   ```python
   def _is_pipe_table_task_row(line: str, task_id: str) -> bool:
       if re.match(r'^\s*\|[\s-]+\|', line):  # Separator row
           return False
       return bool(re.search(rf'\|\s*{re.escape(task_id)}\s*\|', line))
   ```

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: `_is_pipe_table_task_row("| T001 | desc | WP01 | [P] |", "T001")` → True. Separator row → False.

---

## Subtask T023: Implement Pipe-Table Status Update Logic

**Purpose**: When a pipe-table task row is found, replace the status marker in-place.

**Steps**:

1. Add a helper function:
   ```python
   def _update_pipe_table_status(line: str, status: str) -> str:
       """Replace status marker in a pipe-table row.

       Recognizes: [P] (planned/pending), [D] (done), [x] (done), [ ] (pending)
       """
       if status == "done":
           # Replace pending markers with done
           line = re.sub(r'\[\s*P\s*\]', '[D]', line)
           line = re.sub(r'\[\s*\]', '[x]', line)  # Also handle [ ] format
       else:  # pending
           # Replace done markers with pending
           line = re.sub(r'\[\s*D\s*\]', '[P]', line)
           line = re.sub(r'\[\s*x\s*\]', '[ ]', line)
       return line
   ```

2. Integrate into the `mark_status` main loop at lines 1340-1352:
   ```python
   for task_id in task_ids:
       task_found = False
       for i, line in enumerate(lines):
           # Strategy 1: Checkbox format (existing)
           if re.search(rf'-\s*\[[ x]\]\s*{re.escape(task_id)}\b', line):
               lines[i] = re.sub(r'-\s*\[[ x]\]', f'- {new_checkbox}', line)
               updated_tasks.append(task_id)
               task_found = True
               break

           # Strategy 2: Pipe-table format (new)
           if _is_pipe_table_task_row(line, task_id):
               lines[i] = _update_pipe_table_status(line, status)
               updated_tasks.append(task_id)
               task_found = True
               break

       if not task_found:
           not_found_tasks.append(task_id)
   ```

3. Checkbox detection must come FIRST (it's the canonical format). Pipe-table is a fallback.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: `| T001 | desc | WP01 | [P] |` with status=done → `| T001 | desc | WP01 | [D] |`

---

## Subtask T024: Standardize Tasks Template to Checkbox Format

**Purpose**: Ensure future `tasks.md` generation uses checkbox format exclusively (FR-010a).

**Steps**:

1. In `src/specify_cli/missions/software-dev/command-templates/tasks.md`, find the task-format instructions section and ensure they explicitly specify checkbox format.

2. If the template currently shows pipe-table as an option or example, replace with checkbox:
   ```markdown
   ### Task Tracking Format

   Use checkbox format for all task rows in tasks.md:

   ```markdown
   - [ ] T001 Description of task (WP01)
   - [ ] T002 Another task (WP01)
   ```

   Do NOT use pipe-table format for new task tracking rows.
   The `mark-status` command supports both formats for backward compatibility,
   but new generation should use checkboxes exclusively.
   ```

3. Search for any other template files that instruct LLMs to generate pipe-table task rows. Check:
   - `src/specify_cli/missions/*/command-templates/tasks.md`
   - `src/specify_cli/templates/tasks-template.md` (if exists)

4. If a `tasks-template.md` exists with pipe-table examples in the "Subtask Index" section, that's a reference table (not a tracking format) and can remain as-is. The key change is in the task tracking rows that `mark-status` mutates.

**Files**: `src/specify_cli/missions/software-dev/command-templates/tasks.md` (and any other mission templates)

**Validation**: Grep all command-templates for pipe-table task tracking examples → none found (reference tables are OK).

---

## Subtask T025: Write Regression Tests

**Purpose**: Cover both checkbox and pipe-table mutation paths.

**Tests to add**:

1. **`tests/git_ops/test_mark_status_pipe_table.py`** (new file):
   - `test_pipe_table_mark_done`: `| T001 | desc | WP01 | [P] |` → `[D]`
   - `test_pipe_table_mark_pending`: `| T001 | desc | WP01 | [D] |` → `[P]`
   - `test_pipe_table_bracket_space_format`: `| T001 | desc | WP01 | [ ] |` → `[x]`
   - `test_pipe_table_separator_row_not_matched`: `|---|---|` → not treated as task row
   - `test_pipe_table_task_id_in_non_first_column`: `| summary | T001 | WP01 |` → found
   - `test_mixed_format_file`: file has both checkbox and pipe-table rows, both updated
   - `test_pipe_table_multiple_tasks`: mark T001 and T003 done in same file

2. **`tests/git_ops/test_atomic_status_commits_unit.py`** (modify):
   - Verify existing checkbox tests still pass (no regression)

3. **Template test** (can be a simple grep-based assertion):
   - `test_template_does_not_instruct_pipe_table_for_tracking`: verify the tasks template mentions checkbox format

**Files**: `tests/git_ops/test_mark_status_pipe_table.py` (new), `tests/git_ops/test_atomic_status_commits_unit.py`

---

## Definition of Done

- [ ] `mark-status` updates checkbox-format task rows (existing behavior preserved)
- [ ] `mark-status` updates pipe-table-format task rows (`[P]` ↔ `[D]`)
- [ ] Mixed-format files work correctly (both formats in one file)
- [ ] Tasks template instructs checkbox format for new generation
- [ ] No auto-migration or format-selection feature added
- [ ] All tests pass, mypy --strict clean on changed files

## Reviewer Guidance

- Test against the real `kitty-specs/063-universal-charter-rename/tasks.md` to verify pipe-table parsing works on actual generated artifacts
- Verify checkbox detection comes before pipe-table detection in the loop (canonical format first)
- Check that pipe-table status update regex doesn't accidentally match non-status cells
