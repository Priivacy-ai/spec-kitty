"""
VCS Types Module
================

This module defines all enums and dataclasses for VCS operations.
These types are backend-agnostic and used by both GitVCS and JujutsuVCS.

See kitty-specs/015-first-class-jujutsu-vcs-integration/data-model.md for full documentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal


# =============================================================================
# Enums
# =============================================================================


class VCSBackend(str, Enum):
    """Supported VCS backends."""

    GIT = "git"
    JUJUTSU = "jj"


class SyncStatus(str, Enum):
    """Result status of a sync operation."""

    UP_TO_DATE = "up_to_date"
    SYNCED = "synced"
    CONFLICTS = "conflicts"
    FAILED = "failed"


class ConflictType(str, Enum):
    """Types of file conflicts."""

    CONTENT = "content"  # Both sides modified same lines
    MODIFY_DELETE = "modify_delete"  # One side modified, other deleted
    ADD_ADD = "add_add"  # Both sides added same file differently
    RENAME_RENAME = "rename_rename"  # Both sides renamed differently
    RENAME_DELETE = "rename_delete"  # One renamed, other deleted


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass(frozen=True)
class VCSCapabilities:
    """
    Describes what a VCS backend can do.

    Used for feature detection and capability checking before operations.
    """

    supports_auto_rebase: bool  # jj: True, git: False
    supports_conflict_storage: bool  # jj: True, git: False (conflicts block)
    supports_operation_log: bool  # jj: True, git: partial (reflog)
    supports_change_ids: bool  # jj: True, git: False
    supports_workspaces: bool  # jj: True (native), git: True (worktrees)
    supports_colocated: bool  # jj: True, git: N/A
    supports_operation_undo: bool  # jj: True, git: False


@dataclass
class ChangeInfo:
    """
    Represents a single commit/change with metadata for automation.

    For jj, change_id is stable across rebases. For git, change_id is None.
    """

    # Identity
    change_id: str | None  # jj Change ID (stable across rebases), None for git
    commit_id: str  # Git SHA or jj commit ID

    # Metadata
    message: str  # First line of commit message
    message_full: str  # Full commit message
    author: str  # Author name
    author_email: str  # Author email
    timestamp: datetime  # Commit timestamp (UTC)

    # Relationships
    parents: list[str]  # Parent commit IDs
    is_merge: bool  # True if multiple parents

    # State
    is_conflicted: bool  # True if this commit has stored conflicts (jj)
    is_empty: bool  # True if no file changes


@dataclass
class ConflictInfo:
    """
    Represents a conflict in a file.

    In git, conflicts block operations and must be resolved immediately.
    In jj, conflicts are stored in the commit and can be resolved later.
    """

    file_path: Path  # Relative path from workspace root
    conflict_type: ConflictType  # Type of conflict
    line_ranges: list[tuple[int, int]] | None  # Start/end lines, None if whole-file
    sides: int  # Number of sides (2 for normal, 3+ for octopus in jj)
    is_resolved: bool  # True if conflict markers removed

    # Content (for automation)
    our_content: str | None  # "Ours" side content (abbreviated)
    their_content: str | None  # "Theirs" side content (abbreviated)
    base_content: str | None  # Common ancestor content (if available)


@dataclass
class SyncResult:
    """
    Result of synchronizing a workspace with upstream changes.

    The status field indicates the outcome:
    - UP_TO_DATE: No sync needed
    - SYNCED: Successfully updated, no conflicts
    - CONFLICTS: Updated but has conflicts to resolve
    - FAILED: Sync failed (network, permissions, etc.)
    """

    status: SyncStatus
    conflicts: list[ConflictInfo]
    files_updated: int  # Number of files changed
    files_added: int  # Number of new files
    files_deleted: int  # Number of removed files
    changes_integrated: list[ChangeInfo]  # Commits pulled in during sync
    message: str  # Human-readable summary message


@dataclass
class WorkspaceInfo:
    """
    Represents a VCS workspace (git worktree or jj workspace).

    A workspace is an isolated working directory for a work package.
    """

    # Identity
    name: str  # Workspace name (e.g., "015-feature-WP01")
    path: Path  # Absolute path to workspace directory

    # State
    backend: VCSBackend  # Which VCS backend
    is_colocated: bool  # True if both .jj/ and .git/ present

    # Branch/Change tracking
    current_branch: str | None  # Git branch name, None for detached/jj
    current_change_id: str | None  # jj Change ID of working copy
    current_commit_id: str  # Current HEAD commit

    # Relationship to base
    base_branch: str | None  # Branch this was created from (--base flag)
    base_commit_id: str | None  # Commit this was branched from

    # Health
    is_stale: bool  # True if base has changed (needs sync)
    has_conflicts: bool  # True if workspace has unresolved conflicts
    has_uncommitted: bool  # True if working copy has changes (git only)


@dataclass
class OperationInfo:
    """
    Entry in the operation log (primarily jj, approximated for git).

    jj has full operation log with complete undo capability.
    git approximates via reflog but with limited undo.
    """

    operation_id: str  # jj operation ID or git reflog index
    timestamp: datetime  # When operation occurred
    description: str  # What the operation did
    heads: list[str]  # Commit IDs of all heads after operation
    working_copy_commit: str  # Working copy commit after operation
    is_undoable: bool  # Can this operation be undone?
    parent_operation: str | None  # Previous operation ID


@dataclass
class WorkspaceCreateResult:
    """Result of creating a workspace."""

    success: bool
    workspace: WorkspaceInfo | None
    error: str | None


@dataclass
class ProjectVCSConfig:
    """
    Project-level VCS configuration stored in .kittify/config.yaml.

    Controls default VCS selection and backend-specific settings.
    """

    preferred: Literal["auto", "jj", "git"] = "auto"
    jj_min_version: str = "0.20.0"
    jj_colocate: bool = True


@dataclass
class FeatureVCSConfig:
    """
    Per-feature VCS selection stored in feature's meta.json.

    Once set, vcs cannot be changed (locked at feature creation).
    """

    vcs: VCSBackend
    vcs_locked_at: datetime  # When VCS choice was locked


# =============================================================================
# Capability Constants
# =============================================================================


GIT_CAPABILITIES = VCSCapabilities(
    supports_auto_rebase=False,
    supports_conflict_storage=False,
    supports_operation_log=True,  # via reflog, limited
    supports_change_ids=False,
    supports_workspaces=True,
    supports_colocated=False,
    supports_operation_undo=False,
)

JJ_CAPABILITIES = VCSCapabilities(
    supports_auto_rebase=True,
    supports_conflict_storage=True,
    supports_operation_log=True,
    supports_change_ids=True,
    supports_workspaces=True,
    supports_colocated=True,
    supports_operation_undo=True,
)
