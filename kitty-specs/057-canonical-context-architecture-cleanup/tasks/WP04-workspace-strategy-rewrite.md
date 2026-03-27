---
work_package_id: WP04
title: Workspace Strategy Rewrite
lane: planned
dependencies: [WP03]
requirement_refs:
- FR-006
- FR-007
- NFR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
phase: Phase A - Foundation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-27T17:23:39Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Workspace Strategy Rewrite

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- Workspace creation routes by `execution_mode` from the ownership manifest.
- `planning_artifact` WPs work directly in-repo or in a normal worktree without sparse checkout.
- `code_change` WPs create standard worktrees (unchanged except sparse checkout removal).
- All sparse checkout policy code is deleted from the codebase.
- No kitty-specs/ special-case handling remains in worktree code.

## Context & Constraints

- **Spec**: FR-006 (planning-artifact workspace), FR-007 (remove sparse checkout), NFR-006 (backward deletion)
- **Plan**: Move 2 — Workspace Strategy section
- **Key files**: `src/specify_cli/core/worktree.py` (~496 lines), `src/specify_cli/core/vcs/git.py`
- **Key constraint**: Sparse checkout is entirely removed, not made optional.

## Subtasks & Detailed Guidance

### Subtask T018 – Update worktree.py for execution_mode routing

- **Purpose**: Make workspace creation aware of execution mode.
- **Steps**:
  1. Read `src/specify_cli/core/worktree.py` thoroughly — understand `create_feature_worktree()` and WP workspace creation flow
  2. At the point where a workspace is created for a WP:
     - Read the WP's `execution_mode` from frontmatter (via ownership module)
     - If `code_change`: proceed with standard worktree creation (existing path minus sparse checkout)
     - If `planning_artifact`: call the new planning workspace strategy (T019)
  3. Import `ExecutionMode` from `ownership/models.py`
  4. Import `OwnershipManifest.from_frontmatter()` for reading WP metadata
- **Files**: `src/specify_cli/core/worktree.py` (modify, ~20 lines changed)

### Subtask T019 – Implement planning-artifact workspace strategy

- **Purpose**: Planning-artifact WPs must not go through sparse checkout. They work directly in-repo or in a dedicated planning worktree.
- **Steps**:
  1. Create `src/specify_cli/ownership/workspace_strategy.py` (or add to existing worktree.py)
  2. Implement `create_planning_workspace(feature_slug: str, wp_code: str, owned_files: list[str], repo_root: Path) -> Path`:
     - Option A (preferred for simplicity): return `repo_root` — work directly in-repo, no worktree
     - Option B (for isolation): create a standard git worktree at `.worktrees/<slug>-<wp_code>/` with NO sparse checkout
     - The choice should be configurable but default to Option A for planning artifacts
  3. Ensure all files in `owned_files` are accessible in the workspace
  4. Record workspace path in WorkspaceContext (`.kittify/runtime/workspaces/`)
- **Files**: `src/specify_cli/ownership/workspace_strategy.py` (new, ~60 lines)
- **Notes**: The key point is: NO sparse checkout. Planning-artifact WPs see the full repo or a full worktree.

### Subtask T020 – Delete sparse checkout from vcs/git.py

- **Purpose**: Remove `sparse_exclude` parameter and all sparse checkout logic from the VCS layer.
- **Steps**:
  1. Read `src/specify_cli/core/vcs/git.py` — find all sparse checkout references
  2. Remove `sparse_exclude` parameter from `create_workspace()` and any other methods
  3. Remove sparse checkout setup code (git sparse-checkout set/add/disable)
  4. Remove any sparse checkout repair or recovery logic
  5. Update method signatures and all callers
  6. Grep for `sparse` across the entire codebase to catch any remaining references
- **Files**: `src/specify_cli/core/vcs/git.py` (modify, ~30-50 lines removed)

### Subtask T021 – Delete kitty-specs special cases in worktree code

- **Purpose**: Remove special handling that treats kitty-specs/ differently during worktree creation.
- **Steps**:
  1. Search `src/specify_cli/core/worktree.py` for any `kitty-specs` references
  2. Remove conditional logic that excludes or includes kitty-specs/ during worktree setup
  3. Search migrations for worktree-related kitty-specs special cases
  4. Grep for `kitty.specs.*sparse\|sparse.*kitty.specs` across codebase
- **Files**: `src/specify_cli/core/worktree.py` (modify), possibly migration files

### Subtask T022 – Tests for workspace strategy changes

- **Purpose**: Verify routing works correctly for both execution modes.
- **Steps**:
  1. Update `tests/specify_cli/core/test_worktree.py`
  2. Test: `code_change` WP creates standard worktree (no sparse checkout)
  3. Test: `planning_artifact` WP works in-repo (returns repo_root)
  4. Test: No sparse checkout configuration is applied in either mode
  5. Test: WorkspaceContext is recorded correctly for both modes
  6. Delete any existing sparse checkout tests
- **Files**: `tests/specify_cli/core/test_worktree.py` (modify, ~50 lines changed)
- **Parallel?**: Yes

## Risks & Mitigations

- **In-repo planning workspace conflicts**: Multiple planning WPs editing the same files. Mitigated by owned_files overlap validation in WP03.
- **Breaking existing worktree tests**: Tests may assert sparse checkout behavior. Delete those assertions.

## Review Guidance

- `grep -r "sparse" src/` must return zero results (except comments explaining removal)
- Verify planning-artifact WPs can see all kitty-specs/ files
- Verify code_change WPs still create worktrees normally

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
