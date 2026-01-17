---
work_package_id: "WP09"
title: "Integration and Polish"
subtasks:
  - "T051"
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
  - "T057"
  - "T058"
phase: "Phase 3 - Migration"
lane: "doing"
priority: "P3"
dependencies: ["WP05", "WP06", "WP07", "WP08"]
assignee: ""
agent: "__AGENT__"
shell_pid: "28786"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-17T10:38:23Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 – Integration and Polish

## Objectives & Success Criteria

**Goal**: Integrate VCS abstraction across codebase, add merge command, update worktree.py, deprecate direct git calls.

**Success Criteria**:
- New `spec-kitty merge` command completes WP merging workflow
- worktree.py updated to use VCS abstraction
- Direct git calls in commands deprecated with warnings
- Full end-to-end workflow works for both git and jj
- CLAUDE.md updated with jj workflow documentation
- All integration tests pass

**User Stories Addressed**: US2 (P1), US3 (P2), US8 (P3), US9 (P3)
**Requirements**: FR-006, FR-007, FR-010, FR-024

## Context & Constraints

**Reference Documents**:
- `src/specify_cli/core/worktree.py` - Existing worktree management
- `src/specify_cli/cli/commands/` - All command files
- `kitty-specs/015-first-class-jujutsu-vcs-integration/plan.md` - Migration strategy

**Architecture Decisions**:
- Phase 3 focuses on migration and polish
- Deprecation warnings guide users to new abstractions
- Merge command unifies WP completion workflow

**Constraints**:
- Must maintain backward compatibility during transition
- Deprecation period before removing direct git calls
- Full test coverage required for integration

## Subtasks & Detailed Guidance

### Subtask T051 – Create merge.py command

**Purpose**: Implement new merge command for WP completion.

**Steps**:
1. Create `src/specify_cli/cli/commands/merge.py`
2. Implement merge workflow:
   ```python
   import typer
   from rich.console import Console
   from pathlib import Path

   from specify_cli.core.vcs import get_vcs, VCSBackend

   app = typer.Typer()
   console = Console()

   @app.callback(invoke_without_command=True)
   def merge(
       ctx: typer.Context,
       wp_id: str = typer.Argument(..., help="Work package ID to merge (e.g., WP01)"),
       target: str = typer.Option("main", "--target", "-t", help="Target branch to merge into"),
       delete_workspace: bool = typer.Option(True, "--delete/--keep", help="Delete workspace after merge"),
   ):
       """Merge completed work package into target branch."""
       # 1. Validate WP is in done lane
       # 2. Get workspace path
       # 3. Perform merge using VCS abstraction
       # 4. Optionally delete workspace
       pass
   ```
3. Implement VCS-agnostic merge:
   ```python
   def _merge_workspace(workspace_path: Path, target: str) -> bool:
       vcs = get_vcs(workspace_path)

       if vcs.backend == VCSBackend.JUJUTSU:
           # jj: squash into target or create merge commit
           return _jj_merge(workspace_path, target)
       else:
           # git: checkout target, merge branch
           return _git_merge(workspace_path, target)
   ```

**Files**:
- Create: `src/specify_cli/cli/commands/merge.py`

**Notes**:
- Merge strategies may differ between git and jj
- jj supports squash workflow natively
- Consider --squash flag for git

---

### Subtask T052 – Update worktree.py to use VCS abstraction

**Purpose**: Migrate worktree.py from direct git calls to VCS abstraction.

**Steps**:
1. Open `src/specify_cli/core/worktree.py`
2. Replace direct git subprocess calls with VCS abstraction:
   ```python
   # Before:
   subprocess.run(["git", "worktree", "add", ...])

   # After:
   from specify_cli.core.vcs import get_vcs
   vcs = get_vcs(repo_path)
   result = vcs.create_workspace(...)
   ```
3. Update all worktree functions:
   - `create_worktree()` → use `vcs.create_workspace()`
   - `remove_worktree()` → use `vcs.remove_workspace()`
   - `list_worktrees()` → use `vcs.list_workspaces()`
   - `get_worktree_info()` → use `vcs.get_workspace_info()`
4. Add deprecation warnings to old function signatures if needed

**Files**:
- Modify: `src/specify_cli/core/worktree.py`

**Notes**:
- This is critical for full abstraction
- Existing callers should work without changes
- Internal implementation changes only

---

### Subtask T053 – Add deprecation warnings to direct git calls

**Purpose**: Mark direct git calls as deprecated with migration guidance.

**Steps**:
1. Find remaining direct git subprocess calls in commands
2. Add deprecation warnings:
   ```python
   import warnings

   def _legacy_git_operation(...):
       warnings.warn(
           "Direct git calls are deprecated. Use VCS abstraction instead. "
           "See: kitty-specs/015-first-class-jujutsu-vcs-integration/",
           DeprecationWarning,
           stacklevel=2,
       )
       # ... existing implementation
   ```
3. Document migration path in deprecation message

**Files**:
- Modify: Various command files with direct git calls
- Focus on: `implement.py`, `review.py`, `accept.py`

**Notes**:
- Deprecation period allows gradual migration
- Warnings visible to developers
- Full removal in future version

---

### Subtask T054 – Register merge command in CLI

**Purpose**: Add merge command to spec-kitty CLI.

**Steps**:
1. Open `src/specify_cli/cli/main.py`
2. Add merge command:
   ```python
   from specify_cli.cli.commands import merge
   app.add_typer(merge.app, name="merge")
   ```
3. Verify command appears in `spec-kitty --help`

**Files**:
- Modify: `src/specify_cli/cli/main.py`

---

### Subtask T055 – Create integration tests [P]

**Purpose**: End-to-end tests for full workflow with both backends.

**Steps**:
1. Create `tests/specify_cli/test_vcs_integration.py`
2. Add full workflow tests:
   ```python
   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_full_workflow_init_to_merge(tmp_path, backend):
       """Test complete workflow: init → implement → sync → merge."""
       # 1. Init project with VCS
       # 2. Create feature spec
       # 3. Implement WP (creates workspace)
       # 4. Make changes in workspace
       # 5. Sync workspace
       # 6. Merge WP
       # 7. Verify changes in main
       pass

   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_dependent_workspaces(tmp_path, backend):
       """Test --base flag for dependent WPs."""
       # 1. Create WP01 workspace
       # 2. Create WP02 workspace with --base WP01
       # 3. Verify WP02 has WP01 changes
       pass

   @pytest.mark.jj
   def test_jj_conflict_workflow(tmp_path):
       """Test jj-specific conflict handling (conflicts don't block)."""
       # 1. Create conflicting changes
       # 2. Sync workspace
       # 3. Verify sync succeeds with conflicts stored
       # 4. Verify conflicts visible
       pass
   ```

**Files**:
- Create: `tests/specify_cli/test_vcs_integration.py`

**Parallel?**: Yes - can start once commands implemented

---

### Subtask T056 – Update CLAUDE.md with jj workflow

**Purpose**: Document jj workflow for agent users.

**Steps**:
1. Open `/Users/robert/Code/spec-kitty/CLAUDE.md`
2. Add jj-specific section:
   ```markdown
   ## Jujutsu (jj) VCS Integration (0.12.0+)

   **When to use jj**:
   - Multi-agent parallel development (auto-rebase)
   - Complex dependency chains (conflicts don't block)
   - Need operation history with undo

   ### Key Differences from Git

   | Feature | Git | jj |
   |---------|-----|-----|
   | Conflicts | Block operations | Stored, non-blocking |
   | Rebase | Manual | Automatic |
   | Operation undo | Not available | `spec-kitty ops undo` |
   | Change tracking | Branch names | Change IDs |

   ### jj Workflow Commands

   ```bash
   # Init with jj (auto-detected if available)
   spec-kitty init my-project

   # Sync workspace (conflicts stored, not blocking)
   spec-kitty sync

   # View operation history
   spec-kitty ops log

   # Undo last operation (jj only)
   spec-kitty ops undo
   ```

   ### Colocated Mode

   When both git and jj are available, spec-kitty uses colocated mode:
   - Both `.jj/` and `.git/` directories present
   - Can use either tool interchangeably
   - Recommended for teams transitioning to jj
   ```
3. Update existing sections to mention VCS abstraction

**Files**:
- Modify: `CLAUDE.md`

---

### Subtask T057 – Update test_worktree.py [P]

**Purpose**: Update worktree tests for VCS abstraction.

**Steps**:
1. Open `tests/specify_cli/core/test_worktree.py`
2. Add parametrized tests for VCS abstraction:
   ```python
   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_create_worktree_uses_vcs_abstraction(tmp_path, backend):
       # Verify worktree.py uses VCS abstraction
       pass
   ```
3. Update existing tests to work with abstraction

**Files**:
- Modify: `tests/specify_cli/core/test_worktree.py`

**Parallel?**: Yes - can proceed alongside T055

---

### Subtask T058 – Create test_merge.py [P]

**Purpose**: Test merge command for both backends.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_merge.py`
2. Add tests:
   ```python
   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_merge_completed_wp(tmp_path, backend):
       # Setup completed WP
       # Run merge
       # Verify changes in target branch
       pass

   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_merge_deletes_workspace(tmp_path, backend):
       # Setup completed WP
       # Run merge (default: delete workspace)
       # Verify workspace deleted
       pass

   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_merge_keeps_workspace(tmp_path, backend):
       # Setup completed WP
       # Run merge --keep
       # Verify workspace still exists
       pass

   def test_merge_rejects_non_done_wp(tmp_path):
       # Setup WP in 'doing' lane
       # Run merge
       # Verify error message
       pass
   ```

**Files**:
- Create: `tests/specify_cli/cli/commands/test_merge.py`

**Parallel?**: Yes - can start once T051 scaffolded

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing workflows | Deprecation warnings, gradual migration |
| Merge conflicts between backends | Test both backends thoroughly |
| worktree.py regression | Comprehensive test coverage |

## Definition of Done Checklist

- [ ] T051: merge.py command implemented
- [ ] T052: worktree.py uses VCS abstraction
- [ ] T053: Deprecation warnings added to direct git calls
- [ ] T054: merge command registered in CLI
- [ ] T055: Integration tests pass for both backends
- [ ] T056: CLAUDE.md updated with jj workflow
- [ ] T057: worktree tests updated for abstraction
- [ ] T058: merge command tests pass
- [ ] Full workflow works end-to-end for git
- [ ] Full workflow works end-to-end for jj
- [ ] No direct git subprocess calls remain in commands (or deprecated)

## Review Guidance

**Key Checkpoints**:
1. Verify merge command works for both backends
2. Verify worktree.py fully migrated to abstraction
3. Verify deprecation warnings are clear and actionable
4. Run full end-to-end workflow test
5. Verify CLAUDE.md documentation is accurate
6. Run all tests (git and jj markers)

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-17T13:19:13Z – __AGENT__ – shell_pid=28786 – lane=doing – Started implementation via workflow command
