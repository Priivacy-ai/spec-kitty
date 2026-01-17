---
work_package_id: "WP03"
title: "GitVCS Implementation"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
phase: "Phase 1 - Abstraction Layer"
lane: "done"
priority: "P1"
dependencies: ["WP01", "WP02"]
assignee: "__AGENT__"
agent: "__AGENT__"
shell_pid: "38749"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-17T10:38:23Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – GitVCS Implementation

## Objectives & Success Criteria

**Goal**: Implement GitVCS class wrapping existing git operations.

**Success Criteria**:
- All VCSProtocol methods work correctly for git backend
- Existing git worktree functionality is preserved
- Conflict detection parses git conflict markers accurately
- SyncResult captures rebase output correctly
- GitVCS passes runtime_checkable isinstance test

**User Stories Addressed**: US1 (P1), US2 (P1), US3 (P2), US6 (P2)
**Requirements**: FR-001, FR-010, FR-013

## Context & Constraints

**Reference Documents**:
- `kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py` - VCSProtocol definition
- `src/specify_cli/core/git_ops.py` - Existing git operations to wrap
- `src/specify_cli/core/worktree.py` - Existing worktree functions

**Architecture Decisions**:
- Wrap existing git_ops.py functions, don't modify them
- GitVCS implements VCSProtocol
- For git, conflicts block operations (unlike jj)

**Constraints**:
- Must maintain backward compatibility with existing git workflow
- Conflict detection requires parsing file content for markers
- Git doesn't have Change IDs - use branch name as approximation

## Subtasks & Detailed Guidance

### Subtask T010 – Create git.py with GitVCS class skeleton

**Purpose**: Establish the GitVCS class structure implementing VCSProtocol.

**Steps**:
1. Create `src/specify_cli/core/vcs/git.py`
2. Create GitVCS class with protocol properties:
   ```python
   class GitVCS:
       @property
       def backend(self) -> VCSBackend:
           return VCSBackend.GIT

       @property
       def capabilities(self) -> VCSCapabilities:
           return GIT_CAPABILITIES
   ```
3. Add stub methods for all VCSProtocol operations (return NotImplemented or raise)

**Files**:
- Create: `src/specify_cli/core/vcs/git.py`

---

### Subtask T011 – Implement workspace operations

**Purpose**: Wrap git worktree commands for workspace management.

**Steps**:
1. Implement `create_workspace()`:
   - Use `git worktree add <path> -b <branch>`
   - Handle `--base` by branching from specified commit/branch
   - Apply sparse-checkout for kitty-specs/ exclusion
2. Implement `remove_workspace()`:
   - Use `git worktree remove <path>`
3. Implement `get_workspace_info()`:
   - Parse `git worktree list --porcelain`
   - Build WorkspaceInfo from output
4. Implement `list_workspaces()`:
   - Call `git worktree list --porcelain`
   - Return list of WorkspaceInfo

**Files**:
- Modify: `src/specify_cli/core/vcs/git.py`

**Reference**: See `src/specify_cli/cli/commands/implement.py` lines 580-670 for existing worktree creation logic.

**Notes**:
- Sparse-checkout is critical for workspace isolation
- Handle Windows symlink limitations (existing code does this)

---

### Subtask T012 – Implement sync operations

**Purpose**: Implement workspace synchronization for git.

**Steps**:
1. Implement `sync_workspace()`:
   - Fetch latest from remote
   - Attempt rebase onto base branch
   - If conflicts, return SyncResult with CONFLICTS status
   - Parse rebase output for changed files
   - Build changes_integrated from commit log
2. Implement `is_workspace_stale()`:
   - Compare current HEAD with base branch tip
   - Return True if base has commits not in workspace

**Files**:
- Modify: `src/specify_cli/core/vcs/git.py`

**Implementation Details**:
```python
def sync_workspace(self, workspace_path: Path) -> SyncResult:
    # 1. Fetch
    subprocess.run(["git", "-C", str(workspace_path), "fetch"], check=True)

    # 2. Get base branch
    base = self._get_base_branch(workspace_path)

    # 3. Try rebase
    result = subprocess.run(
        ["git", "-C", str(workspace_path), "rebase", base],
        capture_output=True,
    )

    if result.returncode != 0:
        # Check for conflicts
        conflicts = self.detect_conflicts(workspace_path)
        return SyncResult(
            status=SyncStatus.CONFLICTS,
            conflicts=conflicts,
            files_updated=0,
            files_added=0,
            files_deleted=0,
            changes_integrated=[],
            message="Rebase has conflicts",
        )
    # ... success case
```

---

### Subtask T013 – Implement conflict operations

**Purpose**: Detect and report git merge conflicts.

**Steps**:
1. Implement `detect_conflicts()`:
   - Use `git diff --name-only --diff-filter=U` to find conflicted files
   - For each file, parse conflict markers to get line ranges
   - Build ConflictInfo for each
2. Implement `has_conflicts()`:
   - Check if any files in conflicted state

**Files**:
- Modify: `src/specify_cli/core/vcs/git.py`

**Conflict Marker Parsing**:
```python
def _parse_conflict_markers(self, file_path: Path) -> list[tuple[int, int]]:
    """Find line ranges with conflict markers."""
    ranges = []
    in_conflict = False
    start_line = 0

    with open(file_path) as f:
        for i, line in enumerate(f, 1):
            if line.startswith("<<<<<<<"):
                in_conflict = True
                start_line = i
            elif line.startswith(">>>>>>>") and in_conflict:
                ranges.append((start_line, i))
                in_conflict = False

    return ranges
```

---

### Subtask T014 – Implement commit/change operations

**Purpose**: Implement git commit and log operations.

**Steps**:
1. Implement `get_current_change()`:
   - Use `git log -1 --format=...`
   - Build ChangeInfo (change_id=None for git)
2. Implement `get_changes()`:
   - Use `git log --format=...`
   - Parse revision_range parameter
   - Build list of ChangeInfo
3. Implement `commit()`:
   - Use `git add` for specified paths (or all)
   - Use `git commit -m <message>`
   - Return ChangeInfo for new commit

**Files**:
- Modify: `src/specify_cli/core/vcs/git.py`

**Notes**:
- Git format string: `--format=%H|%an|%ae|%at|%s|%P`
- change_id is always None for git

---

### Subtask T015 – Implement repository operations

**Purpose**: Implement git repository initialization and detection.

**Steps**:
1. Implement `init_repo()`:
   - Use `git init` (colocate parameter ignored for git)
2. Implement `is_repo()`:
   - Check for `.git` directory or file (worktree)
3. Implement `get_repo_root()`:
   - Use `git rev-parse --show-toplevel`

**Files**:
- Modify: `src/specify_cli/core/vcs/git.py`

---

### Subtask T016 – Implement git-specific standalone functions [P]

**Purpose**: Implement git-specific functions not in VCSProtocol.

**Steps**:
1. Add to `src/specify_cli/core/vcs/git.py`:
   ```python
   def git_get_reflog(repo_path: Path, limit: int = 20) -> list[OperationInfo]:
       """Get git reflog as operation history."""

   def git_stash(workspace_path: Path, message: str | None = None) -> bool:
       """Stash working directory changes."""

   def git_stash_pop(workspace_path: Path) -> bool:
       """Pop stashed changes."""
   ```
2. Parse `git reflog --format=...` for operation log

**Files**:
- Modify: `src/specify_cli/core/vcs/git.py`

**Parallel?**: Yes - can proceed alongside protocol methods

---

### Subtask T017 – Create test_git.py [P]

**Purpose**: Test GitVCS implementation.

**Steps**:
1. Create `tests/specify_cli/core/vcs/test_git.py`
2. Test all VCSProtocol methods:
   - Workspace creation/removal
   - Sync operations (mock/real scenarios)
   - Conflict detection
   - Commit operations
3. Use tmp_path fixture for isolated test repos

**Files**:
- Create: `tests/specify_cli/core/vcs/test_git.py`

**Test Examples**:
```python
def test_git_vcs_backend(self):
    vcs = GitVCS()
    assert vcs.backend == VCSBackend.GIT

def test_git_vcs_capabilities(self):
    vcs = GitVCS()
    assert vcs.capabilities.supports_auto_rebase is False
    assert vcs.capabilities.supports_workspaces is True

def test_create_workspace(self, tmp_path):
    # Setup git repo
    subprocess.run(["git", "init"], cwd=tmp_path)
    # ... create initial commit ...

    vcs = GitVCS()
    result = vcs.create_workspace(
        tmp_path / ".worktrees/test-WP01",
        "test-WP01",
    )
    assert result.success
    assert (tmp_path / ".worktrees/test-WP01").exists()
```

**Parallel?**: Yes - can start once skeleton exists

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing git workflow | Wrap don't modify git_ops.py |
| Conflict marker parsing edge cases | Test with various conflict scenarios |
| Sparse-checkout complexity | Reuse existing implement.py logic |

## Definition of Done Checklist

- [ ] T010: GitVCS class skeleton with protocol properties
- [ ] T011: Workspace operations (create, remove, info, list)
- [ ] T012: Sync operations (sync_workspace, is_stale)
- [ ] T013: Conflict operations (detect, has_conflicts)
- [ ] T014: Commit/change operations
- [ ] T015: Repository operations
- [ ] T016: Git-specific standalone functions
- [ ] T017: Git-specific tests pass
- [ ] `isinstance(GitVCS(), VCSProtocol)` returns True
- [ ] Existing implement command still works with git

## Review Guidance

**Key Checkpoints**:
1. Verify all VCSProtocol methods implemented
2. Verify conflict detection parses markers correctly
3. Verify SyncResult includes changes_integrated
4. Verify sparse-checkout applied on workspace creation
5. Run existing implement tests to verify no regression

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-17T11:54:03Z – claude-code – shell_pid=41909 – lane=doing – Started implementation via workflow command
- 2026-01-17T12:01:50Z – claude-code – shell_pid=41909 – lane=for_review – Ready for review: Full GitVCS implementation with all VCSProtocol methods, 36 tests passing
- 2026-01-17T12:02:18Z – __AGENT__ – shell_pid=38749 – lane=doing – Started review via workflow command
- 2026-01-17T12:04:09Z – __AGENT__ – shell_pid=38749 – lane=planned – Moved to planned
- 2026-01-17T12:08:24Z – claude-opus – shell_pid=67058 – lane=doing – Started implementation via workflow command
- 2026-01-17T12:15:04Z – claude-opus – shell_pid=67058 – lane=for_review – Fixed all 3 review issues: sparse-checkout in create_workspace, wrapped git_ops.py helpers, implemented _parse_rebase_stats. 68 VCS tests passing.
- 2026-01-17T12:17:58Z – __AGENT__ – shell_pid=38749 – lane=doing – Started review via workflow command
- 2026-01-17T12:19:45Z – __AGENT__ – shell_pid=38749 – lane=planned – Moved to planned
- 2026-01-17T12:24:40Z – __AGENT__ – shell_pid=38749 – lane=done – Review passed - all 3 issues addressed

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-17

**Issue 1**: `create_workspace()` only applies sparse-checkout when `sparse_exclude` is explicitly passed, but the protocol signature doesn’t expose this argument and the requirements call for always excluding `kitty-specs/`. Apply sparse-checkout by default (e.g., default to `["kitty-specs/"]` or unconditionally apply it) to preserve existing worktree isolation behavior.

