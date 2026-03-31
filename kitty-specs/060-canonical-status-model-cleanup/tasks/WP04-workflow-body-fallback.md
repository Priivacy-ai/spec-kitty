---
work_package_id: WP04
title: workflow.py Changes
dependencies: []
requirement_refs:
- FR-007
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: bc4a356816f2c05aa92b24918b87d4bfd3e93764
created_at: '2026-03-31T07:14:34.858146+00:00'
subtasks: [T011, T012, T013, T014, T015]
shell_pid: "83373"
history:
- at: '2026-03-31T06:58:09+00:00'
  actor: planner
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/workflow.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py
---

# WP04: workflow.py Changes

## Objective

Remove `lane=` from implement/review body notes and remove frontmatter-lane fallback from both commands. Add hard-fail when canonical state is missing.

## Context

- workflow.py `implement` command: body note at line 476 writes `lane=doing`, frontmatter fallback at line 390
- workflow.py `review` command: body note at line 1010 writes `lane=...`, frontmatter fallback at line 954
- Both commands have identical fallback patterns: try event log, fall back to `extract_scalar(wp.frontmatter, "lane")`

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

---

## Subtask T011: Remove lane= from Implement Body Note

**Location**: workflow.py around line 476
**Change**: Remove `lane=doing` from the history entry format string. Keep timestamp, agent, shell_pid, action.

---

## Subtask T012: Remove lane= from Review Body Note

**Location**: workflow.py around line 1010
**Change**: Same as T011 — remove `lane=...` from the review history entry format string.

---

## Subtask T013: Remove Implement Frontmatter Fallback + Hard-Fail

**Location**: workflow.py around line 390

**Steps**:
1. Find the code that reads lane: event log first, then `extract_scalar(wp.frontmatter, "lane")`
2. Remove the frontmatter fallback branch
3. If event log has no state for this WP, raise with guidance:
   ```python
   raise RuntimeError(
       f"WP {wp_id} has no canonical status. "
       f"Run `spec-kitty agent feature finalize-tasks --feature {feature_slug}` to initialize."
   )
   ```
4. Use `get_wp_lane()` from `status/lane_reader.py` for the canonical read

---

## Subtask T014: Remove Review Frontmatter Fallback + Hard-Fail

**Location**: workflow.py around line 954
**Steps**: Same pattern as T013 — remove frontmatter fallback, add hard-fail, use `get_wp_lane()`.

---

## Subtask T015: Write Tests

**Steps**:
1. Create `tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py`
2. Tests:
   - implement body note does NOT contain `lane=`
   - review body note does NOT contain `lane=`
   - implement hard-fails when no canonical state for WP
   - review hard-fails when no canonical state for WP
   - implement succeeds when canonical state exists
   - review succeeds when canonical state exists

---

## Definition of Done

- [ ] Neither implement nor review body notes contain `lane=`
- [ ] Neither command reads lane from WP frontmatter
- [ ] Both commands hard-fail with actionable guidance when canonical state missing
- [ ] Both use `get_wp_lane()` or reducer state for canonical reads
- [ ] Tests cover all changes
