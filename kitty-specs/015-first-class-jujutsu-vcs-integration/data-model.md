# Data Model: First-Class Jujutsu VCS Integration

**Feature**: 015-first-class-jujutsu-vcs-integration
**Created**: 2026-01-17
**Purpose**: Define the data structures for VCS abstraction layer

## Overview

This document defines the data structures used by the VCS abstraction layer to represent version control operations, conflicts, and synchronization results in a backend-agnostic way.

## Core Entities

### VCSBackend (Enum)

Identifies which VCS backend is in use.

```python
class VCSBackend(str, Enum):
    GIT = "git"
    JUJUTSU = "jj"
```

**Usage**: Stored in `meta.json` per-feature, used by factory function to instantiate correct implementation.

---

### VCSCapabilities (Dataclass)

Describes what a VCS backend can do. Used for feature detection.

```python
@dataclass(frozen=True)
class VCSCapabilities:
    supports_auto_rebase: bool      # jj: True, git: False
    supports_conflict_storage: bool  # jj: True, git: False (conflicts block)
    supports_operation_log: bool     # jj: True, git: partial (reflog)
    supports_change_ids: bool        # jj: True, git: False
    supports_workspaces: bool        # jj: True (native), git: True (worktrees)
    supports_colocated: bool         # jj: True, git: N/A
```

**Git capabilities**:

```python
GIT_CAPABILITIES = VCSCapabilities(
    supports_auto_rebase=False,
    supports_conflict_storage=False,
    supports_operation_log=True,  # via reflog, limited
    supports_change_ids=False,
    supports_workspaces=True,
    supports_colocated=False,
)
```

**jj capabilities**:

```python
JJ_CAPABILITIES = VCSCapabilities(
    supports_auto_rebase=True,
    supports_conflict_storage=True,
    supports_operation_log=True,
    supports_change_ids=True,
    supports_workspaces=True,
    supports_colocated=True,
)
```

---

### ChangeInfo (Dataclass)

Represents a single commit/change with metadata for automation.

```python
@dataclass
class ChangeInfo:
    # Identity
    change_id: str | None       # jj Change ID (stable across rebases), None for git
    commit_id: str              # Git SHA or jj commit ID

    # Metadata
    message: str                # First line of commit message
    message_full: str           # Full commit message
    author: str                 # Author name
    author_email: str           # Author email
    timestamp: datetime         # Commit timestamp (UTC)

    # Relationships
    parents: list[str]          # Parent commit IDs
    is_merge: bool              # True if multiple parents

    # State
    is_conflicted: bool         # True if this commit has stored conflicts (jj)
    is_empty: bool              # True if no file changes
```

**Relationships**:

- Many ChangeInfo can reference the same Change ID (jj evolution)
- Parent references form the commit graph

---

### ConflictInfo (Dataclass)

Represents a conflict in a file, whether blocking (git) or stored (jj).

```python
@dataclass
class ConflictInfo:
    file_path: Path                          # Relative path from workspace root
    conflict_type: ConflictType              # Type of conflict
    line_ranges: list[tuple[int, int]] | None  # Start/end lines, None if whole-file
    sides: int                               # Number of sides (2 for normal, 3+ for octopus)
    is_resolved: bool                        # True if conflict markers removed

    # Content (for automation)
    our_content: str | None      # "Ours" side content (abbreviated)
    their_content: str | None    # "Theirs" side content (abbreviated)
    base_content: str | None     # Common ancestor content (if available)


class ConflictType(str, Enum):
    CONTENT = "content"           # Both sides modified same lines
    MODIFY_DELETE = "modify_delete"  # One side modified, other deleted
    ADD_ADD = "add_add"           # Both sides added same file differently
    RENAME_RENAME = "rename_rename"  # Both sides renamed differently
    RENAME_DELETE = "rename_delete"  # One renamed, other deleted
```

**Notes**:

- In git, conflicts block operations and must be resolved immediately
- In jj, conflicts are stored in the commit and can be resolved later
- `sides > 2` only possible in jj (octopus merges)

---

### SyncResult (Dataclass)

Result of synchronizing a workspace with upstream changes.

```python
@dataclass
class SyncResult:
    # Status
    status: SyncStatus

    # Conflicts (if any)
    conflicts: list[ConflictInfo]

    # Statistics
    files_updated: int           # Number of files changed
    files_added: int             # Number of new files
    files_deleted: int           # Number of removed files

    # Changes integrated (for automation)
    changes_integrated: list[ChangeInfo]  # Commits pulled in during sync

    # Human-readable
    message: str                 # Summary message for display


class SyncStatus(str, Enum):
    UP_TO_DATE = "up_to_date"    # No changes needed
    SYNCED = "synced"            # Successfully updated, no conflicts
    CONFLICTS = "conflicts"       # Updated but has conflicts to resolve
    FAILED = "failed"            # Sync failed (network, permissions, etc.)
```

**Relationships**:

- `changes_integrated` contains all ChangeInfo objects for commits merged/rebased
- `conflicts` contains ConflictInfo for each conflicted file

---

### WorkspaceInfo (Dataclass)

Represents a VCS workspace (git worktree or jj workspace).

```python
@dataclass
class WorkspaceInfo:
    # Identity
    name: str                    # Workspace name (e.g., "015-feature-WP01")
    path: Path                   # Absolute path to workspace directory

    # State
    backend: VCSBackend          # Which VCS backend
    is_colocated: bool           # True if both .jj/ and .git/ present

    # Branch/Change tracking
    current_branch: str | None   # Git branch name, None for detached/jj
    current_change_id: str | None  # jj Change ID of working copy
    current_commit_id: str       # Current HEAD commit

    # Relationship to base
    base_branch: str | None      # Branch this was created from (--base flag)
    base_commit_id: str | None   # Commit this was branched from

    # Health
    is_stale: bool               # True if base has changed (needs sync)
    has_conflicts: bool          # True if workspace has unresolved conflicts
    has_uncommitted: bool        # True if working copy has changes (git only, jj always committed)
```

**Relationships**:

- Workspace belongs to one Feature (via naming convention)
- Workspace has one current ChangeInfo
- Workspace may depend on other Workspaces (via base_branch)

---

### OperationInfo (Dataclass)

Represents an entry in the operation log (primarily jj, approximated for git).

```python
@dataclass
class OperationInfo:
    # Identity
    operation_id: str            # jj operation ID or git reflog index

    # Metadata
    timestamp: datetime          # When operation occurred
    description: str             # What the operation did

    # State snapshot
    heads: list[str]             # Commit IDs of all heads after operation
    working_copy_commit: str     # Working copy commit after operation

    # Undo capability
    is_undoable: bool            # Can this operation be undone?
    parent_operation: str | None  # Previous operation ID
```

**Notes**:

- jj has full operation log with complete undo capability
- git approximates via reflog but with limited undo (destructive operations not recoverable)

---

## Configuration Entities

### ProjectVCSConfig

Project-level VCS configuration stored in `.kittify/config.yaml`.

```yaml
# .kittify/config.yaml
vcs:
  preferred: "auto"  # "auto" | "jj" | "git"
  # auto = use jj if available, else git

  jj:
    min_version: "0.20.0"  # Minimum jj version required
    colocate: true         # Use colocated mode when git also available

  git:
    # Git-specific settings (future)
```

**Dataclass representation**:

```python
@dataclass
class ProjectVCSConfig:
    preferred: Literal["auto", "jj", "git"] = "auto"
    jj_min_version: str = "0.20.0"
    jj_colocate: bool = True
```

---

### FeatureVCSConfig

Per-feature VCS selection stored in feature's `meta.json`.

```json
{
  "feature_number": "015",
  "slug": "first-class-jujutsu-vcs-integration",
  "friendly_name": "First-Class Jujutsu VCS Integration",
  "mission": "software-dev",
  "vcs": "jj",
  "vcs_locked_at": "2026-01-17T11:15:00Z",
  "created_at": "2026-01-17T11:15:00Z"
}
```

**Dataclass representation**:

```python
@dataclass
class FeatureVCSConfig:
    vcs: VCSBackend
    vcs_locked_at: datetime  # When VCS choice was locked (feature creation)
```

**Constraints**:

- `vcs` is immutable after feature creation
- Attempting to change raises `VCSLockError`

---

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    Project                                   │
│  ┌─────────────────┐                                        │
│  │ ProjectVCSConfig │ preferred: auto|jj|git                │
│  └────────┬────────┘                                        │
│           │ determines default for                          │
│           ▼                                                 │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │    Feature A    │         │    Feature B    │           │
│  │ vcs: "jj"       │         │ vcs: "git"      │           │
│  └────────┬────────┘         └────────┬────────┘           │
│           │                           │                     │
│           ▼                           ▼                     │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │ WorkspaceInfo   │         │ WorkspaceInfo   │           │
│  │ WP01 (jj)       │         │ WP01 (git)      │           │
│  │ ┌─────────────┐ │         │ ┌─────────────┐ │           │
│  │ │ ChangeInfo  │ │         │ │ ChangeInfo  │ │           │
│  │ │ (current)   │ │         │ │ (current)   │ │           │
│  │ └─────────────┘ │         │ └─────────────┘ │           │
│  └─────────────────┘         └─────────────────┘           │
│           │                           │                     │
│           ▼                           ▼                     │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │ SyncResult      │         │ SyncResult      │           │
│  │ (on sync)       │         │ (on sync)       │           │
│  │ ┌─────────────┐ │         │ ┌─────────────┐ │           │
│  │ │ConflictInfo │ │         │ │ConflictInfo │ │           │
│  │ │(if any)     │ │         │ │(if any)     │ │           │
│  │ └─────────────┘ │         │ └─────────────┘ │           │
│  └─────────────────┘         └─────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Validation Rules

1. **VCS Lock**: Once `meta.json` has `vcs` field, it cannot be changed
2. **Backend Consistency**: All operations on a feature must use the same backend
3. **Capability Checking**: Operations unsupported by backend raise `VCSCapabilityError`
4. **Conflict Resolution Gate**: Review/merge blocked if `has_conflicts == True`
5. **Stale Workspace Warning**: Implement warns if `is_stale == True`, suggests sync
