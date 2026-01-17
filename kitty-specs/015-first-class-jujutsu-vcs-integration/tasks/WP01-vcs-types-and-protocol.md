---
work_package_id: "WP01"
title: "VCS Types and Protocol"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
phase: "Phase 1 - Abstraction Layer"
lane: "done"
priority: "P0"
dependencies: []
assignee: "__AGENT__"
agent: "claude-opus"
shell_pid: "40761"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-17T10:38:23Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – VCS Types and Protocol

## Objectives & Success Criteria

**Goal**: Create the foundational type system and protocol definition for VCS abstraction.

**Success Criteria**:
- All types import without error
- VCSProtocol is runtime-checkable (`@runtime_checkable` decorator)
- All dataclasses serialize/deserialize correctly
- No circular import issues
- Public API exports work from `specify_cli.core.vcs`

## Context & Constraints

**Reference Documents**:
- `kitty-specs/015-first-class-jujutsu-vcs-integration/data-model.md` - Complete entity definitions
- `kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py` - Protocol contract with exact signatures
- `kitty-specs/015-first-class-jujutsu-vcs-integration/plan.md` - Architecture decisions

**Architecture Decisions**:
- Hybrid abstraction: Thin Protocol for core ops, standalone functions for backend-specific features
- New `src/specify_cli/core/vcs/` subpackage for clean separation
- Types must be compatible with existing spec-kitty patterns (dataclasses, Path objects)

**Constraints**:
- Python 3.11+ (use modern type syntax: `list[str]` not `List[str]`)
- No external dependencies beyond stdlib (typing, dataclasses, enum, pathlib, datetime)
- Must work with subprocess for VCS CLI invocation (types should be easily convertible to/from CLI output)

## Subtasks & Detailed Guidance

### Subtask T001 – Create vcs/ package directory structure

**Purpose**: Establish the package structure for VCS abstraction.

**Steps**:
1. Create directory: `src/specify_cli/core/vcs/`
2. Create empty `__init__.py` (will be populated in T005)
3. Verify import path works: `from specify_cli.core.vcs import ...`

**Files**:
- Create: `src/specify_cli/core/vcs/__init__.py`

**Notes**: This must complete before T002-T004 can start.

---

### Subtask T002 – Implement types.py [P]

**Purpose**: Define all enums and dataclasses for VCS operations.

**Steps**:
1. Create `src/specify_cli/core/vcs/types.py`
2. Implement enums:
   - `VCSBackend(str, Enum)`: GIT = "git", JUJUTSU = "jj"
   - `SyncStatus(str, Enum)`: UP_TO_DATE, SYNCED, CONFLICTS, FAILED
   - `ConflictType(str, Enum)`: CONTENT, MODIFY_DELETE, ADD_ADD, RENAME_RENAME, RENAME_DELETE
3. Implement dataclasses (see data-model.md for field details):
   - `VCSCapabilities` (frozen=True)
   - `ChangeInfo`
   - `ConflictInfo`
   - `SyncResult`
   - `WorkspaceInfo`
   - `OperationInfo`
   - `WorkspaceCreateResult`
   - `ProjectVCSConfig`
   - `FeatureVCSConfig`
4. Add constants for default capabilities:
   - `GIT_CAPABILITIES`
   - `JJ_CAPABILITIES`

**Files**:
- Create: `src/specify_cli/core/vcs/types.py`

**Parallel?**: Yes - can proceed alongside T003, T004 after T001

**Notes**:
- Use `from __future__ import annotations` for forward references
- All Path fields should use `pathlib.Path`
- datetime fields should be timezone-aware (UTC)
- Reference `contracts/vcs-protocol.py` for exact field names

---

### Subtask T003 – Implement protocol.py [P]

**Purpose**: Define the VCSProtocol interface that GitVCS and JujutsuVCS will implement.

**Steps**:
1. Create `src/specify_cli/core/vcs/protocol.py`
2. Import types from types.py
3. Define `VCSProtocol` using `typing.Protocol` with `@runtime_checkable`
4. Add all method signatures from contracts/vcs-protocol.py:
   - Properties: `backend`, `capabilities`
   - Workspace operations: `create_workspace`, `remove_workspace`, `get_workspace_info`, `list_workspaces`
   - Sync operations: `sync_workspace`, `is_workspace_stale`
   - Conflict operations: `detect_conflicts`, `has_conflicts`
   - Commit operations: `get_current_change`, `get_changes`, `commit`
   - Repository operations: `init_repo`, `is_repo`, `get_repo_root`

**Files**:
- Create: `src/specify_cli/core/vcs/protocol.py`

**Parallel?**: Yes - can proceed alongside T002, T004 after T001

**Notes**:
- Use `...` (ellipsis) for method bodies (Protocol pattern)
- Add docstrings from contracts/vcs-protocol.py
- Backend-specific functions (jj_get_operation_log, etc.) go in their respective modules, not in protocol

---

### Subtask T004 – Implement exceptions.py [P]

**Purpose**: Define exception hierarchy for VCS operations.

**Steps**:
1. Create `src/specify_cli/core/vcs/exceptions.py`
2. Implement exception classes:
   - `VCSError(Exception)` - Base exception
   - `VCSNotFoundError(VCSError)` - Neither jj nor git available
   - `VCSCapabilityError(VCSError)` - Operation not supported by backend
   - `VCSBackendMismatchError(VCSError)` - Requested backend doesn't match feature's locked VCS
   - `VCSLockError(VCSError)` - Attempted to change VCS mid-feature
   - `VCSConflictError(VCSError)` - Operation blocked due to conflicts
   - `VCSSyncError(VCSError)` - Sync operation failed

**Files**:
- Create: `src/specify_cli/core/vcs/exceptions.py`

**Parallel?**: Yes - can proceed alongside T002, T003 after T001

**Notes**:
- Keep exceptions simple (no complex __init__ unless needed)
- Add brief docstrings explaining when each exception is raised

---

### Subtask T005 – Create __init__.py with public API exports

**Purpose**: Define the public API for the vcs package.

**Steps**:
1. Update `src/specify_cli/core/vcs/__init__.py`
2. Export from types.py:
   - All enums (VCSBackend, SyncStatus, ConflictType)
   - All dataclasses (VCSCapabilities, ChangeInfo, ConflictInfo, etc.)
   - Capability constants (GIT_CAPABILITIES, JJ_CAPABILITIES)
3. Export from protocol.py:
   - VCSProtocol
4. Export from exceptions.py:
   - All exception classes
5. Define `__all__` list

**Files**:
- Modify: `src/specify_cli/core/vcs/__init__.py`

**Notes**:
- This task must complete after T002, T003, T004
- Test import: `from specify_cli.core.vcs import VCSProtocol, VCSBackend, VCSError`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Use `from __future__ import annotations`, import types only |
| Type incompatibility with existing code | Match existing patterns (Path, dataclasses) |
| Protocol not runtime-checkable | Use `@runtime_checkable` decorator |

## Definition of Done Checklist

- [ ] T001: vcs/ package directory created with __init__.py
- [ ] T002: types.py with all enums and dataclasses
- [ ] T003: protocol.py with VCSProtocol definition
- [ ] T004: exceptions.py with exception hierarchy
- [ ] T005: __init__.py with all public exports
- [ ] All types import without error: `from specify_cli.core.vcs import *`
- [ ] VCSProtocol is runtime-checkable: `isinstance(obj, VCSProtocol)` works
- [ ] No circular import issues

## Review Guidance

**Key Checkpoints**:
1. Verify all dataclass fields match data-model.md exactly
2. Verify VCSProtocol methods match contracts/vcs-protocol.py exactly
3. Check Python 3.11+ type syntax (not 3.9 style)
4. Verify __all__ exports match intended public API
5. Test basic import in Python REPL

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-17T10:54:05Z – claude-code – shell_pid=32403 – lane=doing – Started implementation via workflow command
- 2026-01-17T11:44:35Z – __AGENT__ – shell_pid=24045 – lane=planned – Moved to planned
- 2026-01-17T11:48:03Z – __AGENT__ – shell_pid=38749 – lane=doing – Started implementation via workflow command
- 2026-01-17T11:48:21Z – __AGENT__ – shell_pid=38749 – lane=for_review – Ready for review: align VCSCapabilities with spec
- 2026-01-17T11:49:50Z – claude-opus – shell_pid=40761 – lane=doing – Started review via workflow command
- 2026-01-17T11:51:14Z – claude-opus – shell_pid=40761 – lane=done – Review passed: All types, protocol, and exceptions match spec exactly. Previous feedback about supports_operation_undo addressed. Imports verified working.

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-17

**Issue 1**: `VCSCapabilities` includes an extra `supports_operation_undo` field in `src/specify_cli/core/vcs/types.py`, but this field is not in `data-model.md` or `contracts/vcs-protocol.py`. This breaks the “match spec exactly” requirement and forces extra constructor args. Remove the field and its usage in `GIT_CAPABILITIES`/`JJ_CAPABILITIES`, or update the spec/contract if the field is truly required.

