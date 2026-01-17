---
work_package_id: "WP04"
title: "JujutsuVCS Implementation"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
phase: "Phase 1 - Abstraction Layer"
lane: "planned"
priority: "P1"
dependencies: ["WP01", "WP02"]
assignee: ""
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

# Work Package Prompt: WP04 – JujutsuVCS Implementation

## Objectives & Success Criteria

**Goal**: Implement JujutsuVCS class with full jj CLI integration.

**Success Criteria**:
- All VCSProtocol methods work correctly for jj backend
- jj workspace creation uses colocated mode when git available
- Conflict detection understands jj's conflict-as-data model
- Auto-rebase is leveraged (conflicts don't block sync)
- Change IDs are properly tracked and exposed
- All jj-specific tests pass (require real jj)

**User Stories Addressed**: US1-US9 (P1-P3)
**Requirements**: FR-001, FR-009, FR-011, FR-012, FR-013, FR-016

## Context & Constraints

**Reference Documents**:
- `kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py` - VCSProtocol definition
- `kitty-specs/015-first-class-jujutsu-vcs-integration/spec.md` - jj-specific user stories

**Architecture Decisions**:
- JujutsuVCS implements VCSProtocol
- Use colocated mode by default when git available
- Conflicts are stored (non-blocking) - key differentiator from git
- Use jj JSON output where available for reliable parsing

**Constraints**:
- All tests require real jj installation (no mocking - per FR-024)
- Minimum jj version: 0.20+
- Must handle both colocated and pure jj repos

**jj Key Commands**:
- `jj workspace add <path>` - Create workspace
- `jj workspace forget <name>` - Remove workspace
- `jj workspace list` - List workspaces
- `jj workspace update-stale` - Sync stale workspace
- `jj status` - Show conflicts and changes
- `jj log -T <template>` - Show commit history
- `jj describe -m <message>` - Set commit message
- `jj new` - Create new change
- `jj git init --colocate` - Init colocated repo
- `jj op log` - Operation history
- `jj op undo` - Undo last operation

## Subtasks & Detailed Guidance

### Subtask T018 – Create jujutsu.py with JujutsuVCS class skeleton

**Purpose**: Establish the JujutsuVCS class structure implementing VCSProtocol.

**Steps**:
1. Create `src/specify_cli/core/vcs/jujutsu.py`
2. Create JujutsuVCS class with protocol properties:
   ```python
   class JujutsuVCS:
       @property
       def backend(self) -> VCSBackend:
           return VCSBackend.JUJUTSU

       @property
       def capabilities(self) -> VCSCapabilities:
           return JJ_CAPABILITIES
   ```
3. Add stub methods for all VCSProtocol operations

**Files**:
- Create: `src/specify_cli/core/vcs/jujutsu.py`

---

### Subtask T019 – Implement workspace operations

**Purpose**: Implement jj workspace creation and management.

**Steps**:
1. Implement `create_workspace()`:
   - Use `jj workspace add <path> --name <name>`
   - If base_branch specified, create from that revision
   - Handle colocated mode (both .jj/ and .git/)
2. Implement `remove_workspace()`:
   - Use `jj workspace forget <name>`
   - Remove directory
3. Implement `get_workspace_info()`:
   - Parse `jj workspace list` output
   - Get current change ID from workspace
4. Implement `list_workspaces()`:
   - Use `jj workspace list`

**Files**:
- Modify: `src/specify_cli/core/vcs/jujutsu.py`

**Implementation Details**:
```python
def create_workspace(
    self,
    workspace_path: Path,
    workspace_name: str,
    base_branch: str | None = None,
    base_commit: str | None = None,
) -> WorkspaceCreateResult:
    args = ["jj", "workspace", "add", str(workspace_path), "--name", workspace_name]

    if base_commit:
        args.extend(["--revision", base_commit])
    elif base_branch:
        args.extend(["--revision", base_branch])

    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        return WorkspaceCreateResult(
            success=False,
            workspace=None,
            error=result.stderr.decode(),
        )
    # ... build WorkspaceInfo
```

---

### Subtask T020 – Implement sync operations

**Purpose**: Implement jj workspace synchronization with auto-rebase.

**Steps**:
1. Implement `sync_workspace()`:
   - Use `jj workspace update-stale`
   - Conflicts are stored, not blocking (key difference from git!)
   - Parse output for updated files
   - Check for conflicts using `jj status`
   - Build changes_integrated from rebased commits
2. Implement `is_workspace_stale()`:
   - Run `jj workspace update-stale --dry-run` or check status

**Files**:
- Modify: `src/specify_cli/core/vcs/jujutsu.py`

**Key Difference from Git**:
```python
def sync_workspace(self, workspace_path: Path) -> SyncResult:
    # In jj, update-stale ALWAYS succeeds - conflicts are stored
    result = subprocess.run(
        ["jj", "workspace", "update-stale"],
        cwd=workspace_path,
        capture_output=True,
    )

    # Check for conflicts AFTER successful sync
    conflicts = self.detect_conflicts(workspace_path)

    status = SyncStatus.CONFLICTS if conflicts else SyncStatus.SYNCED
    return SyncResult(
        status=status,
        conflicts=conflicts,
        # ... etc
    )
```

---

### Subtask T021 – Implement conflict operations

**Purpose**: Detect and report jj stored conflicts.

**Steps**:
1. Implement `detect_conflicts()`:
   - Use `jj status` to find conflicted files
   - Parse jj's conflict representation
   - Build ConflictInfo for each (including multi-sided conflicts)
2. Implement `has_conflicts()`:
   - Check `jj status` for conflict indicator

**Files**:
- Modify: `src/specify_cli/core/vcs/jujutsu.py`

**jj Status Parsing**:
```python
def detect_conflicts(self, workspace_path: Path) -> list[ConflictInfo]:
    result = subprocess.run(
        ["jj", "status"],
        cwd=workspace_path,
        capture_output=True,
    )

    conflicts = []
    for line in result.stdout.decode().splitlines():
        if "conflict" in line.lower():
            # Parse conflict info from jj status output
            # jj shows: "C path/to/file" for conflicted files
            pass
    return conflicts
```

**Notes**:
- jj can have 3+ sided conflicts (octopus merges)
- `sides` field in ConflictInfo captures this

---

### Subtask T022 – Implement commit/change operations

**Purpose**: Implement jj commit and change operations.

**Steps**:
1. Implement `get_current_change()`:
   - Use `jj log -r @ -T <template>` for working copy
   - Extract Change ID (stable across rebases)
2. Implement `get_changes()`:
   - Use `jj log -T <template>` with revset
   - Parse Change IDs and commit metadata
3. Implement `commit()`:
   - Use `jj describe -m <message>` (working copy already committed in jj)
   - Use `jj new` to create new change if needed

**Files**:
- Modify: `src/specify_cli/core/vcs/jujutsu.py`

**jj Template for Parsing**:
```python
JJ_LOG_TEMPLATE = 'change_id ++ "|" ++ commit_id ++ "|" ++ description.first_line()'

def get_current_change(self, workspace_path: Path) -> ChangeInfo | None:
    result = subprocess.run(
        ["jj", "log", "-r", "@", "-T", JJ_LOG_TEMPLATE, "--no-graph"],
        cwd=workspace_path,
        capture_output=True,
    )
    # Parse: "abcdef12|fedcba98|Commit message"
```

**Key Difference from Git**:
- In jj, the working copy IS a commit - no staging area
- `jj describe` modifies the current change's message
- `jj new` creates a new empty change on top

---

### Subtask T023 – Implement repository operations

**Purpose**: Implement jj repository initialization with colocated mode.

**Steps**:
1. Implement `init_repo()`:
   - Use `jj git init --colocate` when colocate=True and git available
   - Use `jj init` for pure jj mode
2. Implement `is_repo()`:
   - Check for `.jj` directory
3. Implement `get_repo_root()`:
   - Use `jj workspace root`

**Files**:
- Modify: `src/specify_cli/core/vcs/jujutsu.py`

**Colocated Mode**:
```python
def init_repo(self, path: Path, colocate: bool = True) -> bool:
    if colocate and is_git_available():
        # Colocated: both .jj/ and .git/
        result = subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=path,
        )
    else:
        # Pure jj
        result = subprocess.run(["jj", "init"], cwd=path)
    return result.returncode == 0
```

---

### Subtask T024 – Implement jj-specific standalone functions [P]

**Purpose**: Implement jj-specific functions not in VCSProtocol.

**Steps**:
1. Add to `src/specify_cli/core/vcs/jujutsu.py`:
   ```python
   def jj_get_operation_log(repo_path: Path, limit: int = 20) -> list[OperationInfo]:
       """Get jj operation log."""

   def jj_undo_operation(repo_path: Path, operation_id: str | None = None) -> bool:
       """Undo a jj operation."""

   def jj_get_change_by_id(repo_path: Path, change_id: str) -> ChangeInfo | None:
       """Look up change by stable Change ID."""
   ```
2. Parse `jj op log --limit <n>` for operation history
3. Use `jj op undo` for undo functionality

**Files**:
- Modify: `src/specify_cli/core/vcs/jujutsu.py`

**Parallel?**: Yes - can proceed alongside protocol methods

---

### Subtask T025 – Create test_jujutsu.py [P]

**Purpose**: Test JujutsuVCS implementation with real jj.

**Steps**:
1. Create `tests/specify_cli/core/vcs/test_jujutsu.py`
2. Mark all tests with `@pytest.mark.jj`
3. Test all VCSProtocol methods
4. Test jj-specific functionality (operation log, Change IDs)
5. Test conflict-as-data behavior (sync doesn't fail on conflicts)

**Files**:
- Create: `tests/specify_cli/core/vcs/test_jujutsu.py`

**Test Examples**:
```python
import pytest
from specify_cli.core.vcs import VCSBackend, VCSProtocol
from specify_cli.core.vcs.jujutsu import JujutsuVCS

pytestmark = pytest.mark.jj  # All tests require jj

def test_jujutsu_vcs_backend():
    vcs = JujutsuVCS()
    assert vcs.backend == VCSBackend.JUJUTSU

def test_jujutsu_vcs_capabilities():
    vcs = JujutsuVCS()
    assert vcs.capabilities.supports_auto_rebase is True
    assert vcs.capabilities.supports_conflict_storage is True
    assert vcs.capabilities.supports_change_ids is True

def test_create_workspace_colocated(tmp_path):
    vcs = JujutsuVCS()
    # Init colocated repo
    vcs.init_repo(tmp_path, colocate=True)

    # Create workspace
    result = vcs.create_workspace(
        tmp_path / ".worktrees/test-WP01",
        "test-WP01",
    )
    assert result.success
    # Verify colocated
    assert (tmp_path / ".worktrees/test-WP01/.jj").exists()
    assert (tmp_path / ".worktrees/test-WP01/.git").exists()

def test_sync_with_conflict_succeeds(tmp_path):
    """jj sync should succeed even with conflicts (key differentiator)."""
    # Setup conflicting scenario...
    vcs = JujutsuVCS()
    result = vcs.sync_workspace(workspace_path)

    # In jj, sync ALWAYS succeeds - conflicts are stored
    assert result.status in [SyncStatus.SYNCED, SyncStatus.CONFLICTS]
    # Conflicts are reported but operation succeeded
```

**Parallel?**: Yes - can start once skeleton exists

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| jj CLI output changes | Pin min version 0.20+, use JSON output where available |
| Colocated mode sync issues | Test thoroughly with both git and jj commands |
| jj not installed in CI | All jj tests marked with @pytest.mark.jj, skipable |

## Definition of Done Checklist

- [ ] T018: JujutsuVCS class skeleton with protocol properties
- [ ] T019: Workspace operations (create with colocate, remove, info, list)
- [ ] T020: Sync operations with auto-rebase (conflicts don't block)
- [ ] T021: Conflict detection for stored conflicts
- [ ] T022: Commit/change operations with Change ID support
- [ ] T023: Repository operations with colocated mode
- [ ] T024: jj-specific standalone functions (op log, undo, change lookup)
- [ ] T025: jj-specific tests pass (with real jj)
- [ ] `isinstance(JujutsuVCS(), VCSProtocol)` returns True
- [ ] Sync with conflicts returns CONFLICTS status but succeeds

## Review Guidance

**Key Checkpoints**:
1. Verify all VCSProtocol methods implemented
2. Verify colocated mode creates both .jj/ and .git/
3. Verify sync doesn't fail on conflicts (stores them instead)
4. Verify Change IDs are properly extracted and tracked
5. Run jj tests in environment with jj 0.20+
6. Test operation log and undo functionality

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-17T12:02:33Z – claude-code – shell_pid=65174 – lane=doing – Started implementation via workflow command
- 2026-01-17T12:11:44Z – claude-code – shell_pid=65174 – lane=for_review – Full JujutsuVCS implementation with 36 passing tests. Key jj behaviors implemented: non-blocking conflicts, Change IDs, operation log with undo.
- 2026-01-17T12:12:41Z – __AGENT__ – shell_pid=38749 – lane=doing – Started review via workflow command
- 2026-01-17T12:13:26Z – __AGENT__ – shell_pid=38749 – lane=planned – Moved to planned

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-17

**Issue 1**: `init_repo()` uses `jj git init` even when `colocate=False`. The spec calls for pure jj repos when colocate is false (`jj init`), so this implementation can't create non-colocated repos. Adjust to use `jj init` when `colocate=False` (and `jj git init --colocate` only when colocating).

**Issue 2**: Tests assert a `supports_operation_undo` capability that no longer exists in the data model. This will fail once WP01 removed the field. Update the JJ tests to match the spec-correct `VCSCapabilities` fields and drop the `supports_operation_undo` assertion.

