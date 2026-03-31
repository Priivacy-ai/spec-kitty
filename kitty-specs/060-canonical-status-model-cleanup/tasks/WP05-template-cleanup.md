---
work_package_id: WP05
title: Template Cleanup
dependencies: []
requirement_refs:
- FR-004
- FR-006
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T016, T017, T018, T019, T020]
history:
- at: '2026-03-31T06:58:09+00:00'
  actor: planner
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/missions/
execution_mode: code_change
owned_files:
- src/specify_cli/missions/software-dev/templates/tasks-template.md
- src/specify_cli/missions/software-dev/templates/task-prompt-template.md
- src/specify_cli/missions/research/templates/task-prompt-template.md
- src/specify_cli/missions/documentation/templates/task-prompt-template.md
- src/specify_cli/missions/software-dev/command-templates/tasks.md
- src/specify_cli/missions/software-dev/command-templates/tasks-packages.md
- src/doctrine/templates/task-prompt-template.md
- src/doctrine/missions/software-dev/templates/task-prompt-template.md
- src/doctrine/missions/research/templates/task-prompt-template.md
- src/doctrine/missions/documentation/templates/task-prompt-template.md
- tests/specify_cli/test_template_lane_guard.py
---

# WP05: Template Cleanup

## Objective

Remove all lane-related content from active template files across specify_cli missions and doctrine. After this WP, no template generates WP frontmatter with `lane:`, no template teaches `lane=` activity log entries, and no template includes `history[].lane`.

## Context

- 10 template files across two active surfaces: specify_cli missions (6 files) and doctrine (4 files)
- These templates are used by `/spec-kitty.tasks` and doctrine workflows to generate WP prompt files
- The templates currently teach the abandoned frontmatter-lane model
- This is purely text editing — no Python code changes, no runtime behavior changes

## Implementation Command

```bash
spec-kitty implement WP05
```

---

## Subtask T016: Clean specify_cli Mission Templates (4 files)

**Purpose**: Remove lane from the 4 task-prompt templates across all missions.

**Files**:
- `src/specify_cli/missions/software-dev/templates/task-prompt-template.md`
- `src/specify_cli/missions/research/templates/task-prompt-template.md`
- `src/specify_cli/missions/documentation/templates/task-prompt-template.md`
- `src/specify_cli/missions/software-dev/templates/tasks-template.md`

**Changes in each task-prompt-template.md**:
1. Remove `lane: "planned"` (or any lane value) from frontmatter examples
2. Remove `review_status`, `reviewed_by`, `review_feedback`, `progress` from frontmatter examples
3. Remove `lane=<lane>` from activity log format string examples
4. Remove `history[].lane` from history entry examples — keep `at`, `actor`, `action` only
5. Where templates document "valid lane values" or "lane field", remove those sections or replace with: "Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task` to change WP status."

**Changes in tasks-template.md**:
1. Remove `lane: planned|doing|for_review|done` from frontmatter documentation
2. Replace with note that status lives in canonical event log

---

## Subtask T017: Clean specify_cli Command Templates (2 files)

**Files**:
- `src/specify_cli/missions/software-dev/command-templates/tasks.md`
- `src/specify_cli/missions/software-dev/command-templates/tasks-packages.md`

**Changes**: Remove `lane: "planned"` from WP frontmatter examples. Remove any lane-bearing history examples. Keep all other frontmatter fields (work_package_id, title, dependencies, subtasks, etc.).

---

## Subtask T018: Clean Doctrine Root Template

**File**: `src/doctrine/templates/task-prompt-template.md`

**Changes**: Same pattern as T016 — remove lane from frontmatter guidance, activity log format, and history examples.

---

## Subtask T019: Clean Doctrine Mission Templates (3 files)

**Files**:
- `src/doctrine/missions/software-dev/templates/task-prompt-template.md`
- `src/doctrine/missions/research/templates/task-prompt-template.md`
- `src/doctrine/missions/documentation/templates/task-prompt-template.md`

**Changes**: Same pattern as T016.

---

## Subtask T020: Add Regression Test

**Purpose**: Prevent reintroduction of lane in active templates.

**File**: `tests/specify_cli/test_template_lane_guard.py` (new)

**Test**: Scan all `.md` files under `src/specify_cli/missions/` and `src/doctrine/` for:
- `^lane:` in YAML frontmatter position (between `---` markers)
- `lane=` in activity log format strings
- `history[].lane` patterns

Fail if any match found. This is a cheap grep-based guard, not a YAML parser.

---

## Definition of Done

- [ ] No active template file contains `lane:` in frontmatter examples
- [ ] No active template teaches `lane=` in activity log format strings
- [ ] No active template includes `history[].lane`
- [ ] Templates describe status as living in `status.events.jsonl`
- [ ] Regression test catches any reintroduction
- [ ] All 10 template files updated consistently

## Reviewer Guidance

- Verify ALL 10 template files were updated (easy to miss one)
- Verify the regression test actually finds lane: if reintroduced (not just a pass-everything stub)
- Check that operational metadata (agent, assignee, shell_pid) is preserved — only status fields removed
