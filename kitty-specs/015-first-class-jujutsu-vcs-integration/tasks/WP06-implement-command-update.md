---
work_package_id: "WP06"
title: "Implement Command Update"
subtasks:
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
phase: "Phase 2 - Command Updates"
lane: "done"
priority: "P1"
dependencies: ["WP03", "WP04"]
assignee: "__AGENT__"
agent: "__AGENT__"
shell_pid: "16163"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-17T10:38:23Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Implement Command Update

## Objectives & Success Criteria

**Goal**: Update `spec-kitty implement` to use VCS abstraction for workspace creation.

**Success Criteria**:
- `spec-kitty implement WP01` creates jj workspace when feature uses jj
- `spec-kitty implement WP01` creates git worktree when feature uses git
- VCS selection stored and locked in meta.json on first workspace creation
- `--base` flag works for both VCS backends
- Stale workspace detection works for both backends
- Existing git workflow continues working

**User Stories Addressed**: US2 (P1), US3 (P2)
**Requirements**: FR-006, FR-007, FR-009, FR-010, FR-011, FR-012

## Context & Constraints

**Reference Documents**:
- `src/specify_cli/cli/commands/implement.py` - Existing implement command (745 lines)
- `kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py` - VCS interface

**Architecture Decisions**:
- VCS abstraction used for all workspace operations
- VCS locked in meta.json at feature creation
- Colocated mode for jj when git available

**Constraints**:
- Must maintain full backward compatibility with git workflow
- VCS lock prevents changing VCS mid-feature
- Sparse-checkout behavior may differ between git and jj

**Key Code Locations in implement.py**:
- Workspace creation: lines 580-670
- --base flag handling: lines 394-442
- Stale detection: lines 203-297
- Sparse-checkout setup: lines 614-672

## Subtasks & Detailed Guidance

### Subtask T032 – Import VCS abstraction in implement.py

**Purpose**: Add VCS abstraction imports.

**Steps**:
1. Open `src/specify_cli/cli/commands/implement.py`
2. Add imports:
   ```python
   from specify_cli.core.vcs import (
       get_vcs,
       VCSBackend,
       VCSProtocol,
       VCSLockError,
   )
   ```

**Files**:
- Modify: `src/specify_cli/cli/commands/implement.py`

---

### Subtask T033 – Modify workspace creation to use vcs.create_workspace()

**Purpose**: Replace direct git commands with VCS abstraction.

**Steps**:
1. Find workspace creation code (~line 580-670)
2. Replace git worktree commands with VCS abstraction:
   ```python
   # Before:
   subprocess.run(["git", "worktree", "add", ...])

   # After:
   vcs = get_vcs(feature_path)
   result = vcs.create_workspace(
       workspace_path=worktree_path,
       workspace_name=workspace_name,
       base_branch=base_branch,
       base_commit=base_commit,
   )
   if not result.success:
       console.print(f"[red]Failed to create workspace: {result.error}[/red]")
       raise typer.Exit(1)
   ```
3. Update success messages to be VCS-agnostic

**Files**:
- Modify: `src/specify_cli/cli/commands/implement.py`

**Notes**:
- Keep existing error handling patterns
- VCS abstraction handles sparse-checkout internally (for git)

---

### Subtask T034 – Add VCS selection to meta.json

**Purpose**: Store and lock VCS choice in feature metadata.

**Steps**:
1. Add VCS detection during feature creation:
   ```python
   def _ensure_vcs_in_meta(feature_dir: Path) -> VCSBackend:
       meta_path = feature_dir / "meta.json"
       meta = json.loads(meta_path.read_text())

       if "vcs" in meta:
           # Already locked
           return VCSBackend(meta["vcs"])

       # Detect and lock
       vcs = get_vcs(feature_dir)
       meta["vcs"] = vcs.backend.value
       meta["vcs_locked_at"] = datetime.utcnow().isoformat() + "Z"
       meta_path.write_text(json.dumps(meta, indent=2))
       return vcs.backend
   ```
2. Call this during first implement for a feature

**Files**:
- Modify: `src/specify_cli/cli/commands/implement.py`

**Notes**:
- VCS locked on first workspace creation, not feature creation
- Allows changing VCS before first implement (if needed)

---

### Subtask T035 – Implement --base flag handling for both VCS backends

**Purpose**: Ensure --base flag works with both git and jj.

**Steps**:
1. Find --base handling (~lines 394-442)
2. Update to use VCS abstraction:
   ```python
   if base_wp:
       # Validate base workspace exists
       base_workspace = vcs.get_workspace_info(base_worktree_path)
       if base_workspace is None:
           console.print(f"[red]Base workspace {base_wp} does not exist[/red]")
           raise typer.Exit(1)

       # Create dependent workspace
       result = vcs.create_workspace(
           workspace_path=worktree_path,
           workspace_name=workspace_name,
           base_branch=base_workspace.current_branch,
       )
   ```

**Files**:
- Modify: `src/specify_cli/cli/commands/implement.py`

---

### Subtask T036 – Update sparse-checkout logic for jj workspaces

**Purpose**: Handle workspace isolation for jj.

**Steps**:
1. Review sparse-checkout code (~lines 614-672)
2. For git: Keep existing sparse-checkout (exclude kitty-specs/)
3. For jj: Research if similar isolation needed
   - jj workspaces may handle this differently
   - May not need sparse-checkout equivalent
4. Implement backend-specific isolation:
   ```python
   if vcs.backend == VCSBackend.GIT:
       _setup_sparse_checkout(worktree_path)
   elif vcs.backend == VCSBackend.JUJUTSU:
       # jj may not need sparse-checkout
       # Research: Does jj have equivalent isolation mechanism?
       pass
   ```

**Files**:
- Modify: `src/specify_cli/cli/commands/implement.py`

**Notes**:
- This may require research into jj's workspace model
- Document findings in implementation

---

### Subtask T037 – Add stale workspace detection using VCS abstraction

**Purpose**: Detect when workspace needs sync.

**Steps**:
1. Find stale detection code (~lines 203-297)
2. Update to use VCS abstraction:
   ```python
   def _check_workspace_stale(workspace_path: Path) -> bool:
       vcs = get_vcs(workspace_path)
       return vcs.is_workspace_stale(workspace_path)

   # In implement workflow:
   if _check_workspace_stale(worktree_path):
       console.print("[yellow]Warning: Workspace is stale. Base branch has changed.[/yellow]")
       console.print("Run [bold]spec-kitty sync[/bold] to update.")
   ```

**Files**:
- Modify: `src/specify_cli/cli/commands/implement.py`

---

### Subtask T038 – Update implement command tests [P]

**Purpose**: Test implement command with both VCS backends.

**Steps**:
1. Update `tests/specify_cli/cli/commands/test_implement.py`
2. Add parametrized tests:
   ```python
   @pytest.mark.parametrize("backend", [
       "git",
       pytest.param("jj", marks=pytest.mark.jj),
   ])
   def test_implement_creates_workspace(tmp_path, backend):
       # Setup feature with specified backend
       # Run implement
       # Verify workspace created correctly
   ```
3. Test VCS locking in meta.json
4. Test --base flag for both backends
5. Test stale workspace detection

**Files**:
- Modify: `tests/specify_cli/cli/commands/test_implement.py`

**Parallel?**: Yes - can start once T032-T037 scaffolded

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing git workflow | Extensive testing with git backend |
| VCS lock confusion | Clear error messages when lock violated |
| Sparse-checkout differences | Research jj isolation, document findings |

## Definition of Done Checklist

- [ ] T032: VCS imports added to implement.py
- [ ] T033: Workspace creation uses vcs.create_workspace()
- [ ] T034: VCS stored and locked in meta.json
- [ ] T035: --base flag works for both backends
- [ ] T036: Workspace isolation handled for both backends
- [ ] T037: Stale detection uses VCS abstraction
- [ ] T038: Parametrized tests for both backends pass
- [ ] `spec-kitty implement WP01` works with git
- [ ] `spec-kitty implement WP01` works with jj
- [ ] Existing implement tests still pass

## Review Guidance

**Key Checkpoints**:
1. Verify git workflow unchanged (backward compatible)
2. Verify jj workspace creation is colocated
3. Verify VCS lock in meta.json works
4. Verify --base flag creates correct dependencies
5. Verify stale detection works for both backends
6. Run full implement test suite

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-17T12:38:00Z – __AGENT__ – shell_pid=98628 – lane=doing – Started implementation via workflow command
- 2026-01-17T12:50:08Z – __AGENT__ – shell_pid=98628 – lane=for_review – VCS abstraction integrated into implement command - all 833 tests pass
- 2026-01-17T12:51:15Z – __AGENT__ – shell_pid=9401 – lane=doing – Started review via workflow command
- 2026-01-17T12:54:11Z – __AGENT__ – shell_pid=9401 – lane=planned – Moved to planned
- 2026-01-17T12:56:42Z – __AGENT__ – shell_pid=9401 – lane=doing – Started implementation via workflow command
- 2026-01-17T12:58:56Z – __AGENT__ – shell_pid=9401 – lane=for_review – Ready for review: fix jj --base revision handling, use VCS validation, restore symlink check, update tests
- 2026-01-17T13:04:44Z – __AGENT__ – shell_pid=16163 – lane=doing – Started review via workflow command
- 2026-01-17T13:08:15Z – __AGENT__ – shell_pid=16163 – lane=done – Review passed: VCS abstraction correctly integrated - git backward compatible, jj workspace creation supported, meta.json locking works, --base flag handles both backends, stale detection via VCS abstraction, 24 tests passing
