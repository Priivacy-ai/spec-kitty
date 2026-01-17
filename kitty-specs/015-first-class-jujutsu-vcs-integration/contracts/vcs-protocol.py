"""
VCS Protocol Contract
=====================

This file defines the interface contract for VCS backends in spec-kitty.
It serves as the specification for both GitVCS and JujutsuVCS implementations.

This is a CONTRACT file - it defines the expected interface, not the implementation.
The actual implementation will be in src/specify_cli/core/vcs/protocol.py

Usage:
    from specify_cli.core.vcs import get_vcs, VCSProtocol

    vcs = get_vcs(feature_path)  # Returns GitVCS or JujutsuVCS
    result = vcs.sync_workspace(workspace_path)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable


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
    CONTENT = "content"
    MODIFY_DELETE = "modify_delete"
    ADD_ADD = "add_add"
    RENAME_RENAME = "rename_rename"
    RENAME_DELETE = "rename_delete"


# =============================================================================
# Data Classes (see data-model.md for full documentation)
# =============================================================================

@dataclass
class VCSCapabilities:
    """Describes what a VCS backend can do."""
    supports_auto_rebase: bool
    supports_conflict_storage: bool
    supports_operation_log: bool
    supports_change_ids: bool
    supports_workspaces: bool
    supports_colocated: bool


@dataclass
class ChangeInfo:
    """Represents a single commit/change."""
    change_id: str | None  # jj only
    commit_id: str
    message: str
    message_full: str
    author: str
    author_email: str
    timestamp: datetime
    parents: list[str]
    is_merge: bool
    is_conflicted: bool
    is_empty: bool


@dataclass
class ConflictInfo:
    """Represents a conflict in a file."""
    file_path: Path
    conflict_type: ConflictType
    line_ranges: list[tuple[int, int]] | None
    sides: int
    is_resolved: bool
    our_content: str | None
    their_content: str | None
    base_content: str | None


@dataclass
class SyncResult:
    """Result of synchronizing a workspace."""
    status: SyncStatus
    conflicts: list[ConflictInfo]
    files_updated: int
    files_added: int
    files_deleted: int
    changes_integrated: list[ChangeInfo]
    message: str


@dataclass
class WorkspaceInfo:
    """Represents a VCS workspace."""
    name: str
    path: Path
    backend: VCSBackend
    is_colocated: bool
    current_branch: str | None
    current_change_id: str | None
    current_commit_id: str
    base_branch: str | None
    base_commit_id: str | None
    is_stale: bool
    has_conflicts: bool
    has_uncommitted: bool


@dataclass
class OperationInfo:
    """Entry in the operation log."""
    operation_id: str
    timestamp: datetime
    description: str
    heads: list[str]
    working_copy_commit: str
    is_undoable: bool
    parent_operation: str | None


@dataclass
class WorkspaceCreateResult:
    """Result of creating a workspace."""
    success: bool
    workspace: WorkspaceInfo | None
    error: str | None


# =============================================================================
# VCS Protocol (Interface Contract)
# =============================================================================

@runtime_checkable
class VCSProtocol(Protocol):
    """
    Interface contract for VCS backends.

    Both GitVCS and JujutsuVCS must implement this protocol.
    Operations not supported by a backend should raise VCSCapabilityError.
    """

    @property
    def backend(self) -> VCSBackend:
        """Return which backend this is."""
        ...

    @property
    def capabilities(self) -> VCSCapabilities:
        """Return capabilities of this backend."""
        ...

    # =========================================================================
    # Workspace Operations (Core - Required)
    # =========================================================================

    def create_workspace(
        self,
        workspace_path: Path,
        workspace_name: str,
        base_branch: str | None = None,
        base_commit: str | None = None,
    ) -> WorkspaceCreateResult:
        """
        Create a new workspace for a work package.

        Args:
            workspace_path: Where to create the workspace
            workspace_name: Name for the workspace (e.g., "015-feature-WP01")
            base_branch: Branch to base on (for --base flag)
            base_commit: Specific commit to base on (alternative to branch)

        Returns:
            WorkspaceCreateResult with workspace info or error

        Implementation notes:
            - Git: Uses `git worktree add`
            - jj: Uses `jj workspace add`
        """
        ...

    def remove_workspace(self, workspace_path: Path) -> bool:
        """
        Remove a workspace and clean up.

        Returns:
            True if successful, False otherwise

        Implementation notes:
            - Git: Uses `git worktree remove`
            - jj: Uses `jj workspace forget` + directory removal
        """
        ...

    def get_workspace_info(self, workspace_path: Path) -> WorkspaceInfo | None:
        """
        Get information about a workspace.

        Returns:
            WorkspaceInfo or None if not a valid workspace
        """
        ...

    def list_workspaces(self, repo_root: Path) -> list[WorkspaceInfo]:
        """
        List all workspaces for a repository.

        Returns:
            List of WorkspaceInfo for all workspaces
        """
        ...

    # =========================================================================
    # Synchronization Operations (Core - Required)
    # =========================================================================

    def sync_workspace(self, workspace_path: Path) -> SyncResult:
        """
        Synchronize workspace with upstream changes.

        This is the key operation that differs between backends:
        - Git: Fetch + rebase, conflicts block
        - jj: update-stale, conflicts stored

        Returns:
            SyncResult with status, conflicts, and changes integrated
        """
        ...

    def is_workspace_stale(self, workspace_path: Path) -> bool:
        """
        Check if workspace needs sync (base has changed).

        Returns:
            True if sync is needed
        """
        ...

    # =========================================================================
    # Conflict Operations (Core - Required)
    # =========================================================================

    def detect_conflicts(self, workspace_path: Path) -> list[ConflictInfo]:
        """
        Detect conflicts in a workspace.

        Returns:
            List of ConflictInfo for all conflicted files

        Implementation notes:
            - Git: Parse conflict markers in working tree
            - jj: Query jj status for conflict state
        """
        ...

    def has_conflicts(self, workspace_path: Path) -> bool:
        """
        Check if workspace has any unresolved conflicts.

        Returns:
            True if conflicts exist
        """
        ...

    # =========================================================================
    # Commit/Change Operations (Core - Required)
    # =========================================================================

    def get_current_change(self, workspace_path: Path) -> ChangeInfo | None:
        """
        Get info about current working copy commit/change.

        Returns:
            ChangeInfo for current HEAD/working copy
        """
        ...

    def get_changes(
        self,
        repo_path: Path,
        revision_range: str | None = None,
        limit: int | None = None,
    ) -> list[ChangeInfo]:
        """
        Get list of changes/commits.

        Args:
            repo_path: Repository path
            revision_range: Git revision range or jj revset
            limit: Maximum number to return

        Returns:
            List of ChangeInfo
        """
        ...

    def commit(
        self,
        workspace_path: Path,
        message: str,
        paths: list[Path] | None = None,
    ) -> ChangeInfo | None:
        """
        Create a commit with current changes.

        Args:
            workspace_path: Workspace to commit in
            message: Commit message
            paths: Specific paths to commit (None = all)

        Returns:
            ChangeInfo for new commit, None if nothing to commit

        Implementation notes:
            - Git: git add + git commit
            - jj: jj describe (working copy already committed)
        """
        ...

    # =========================================================================
    # Repository Operations (Core - Required)
    # =========================================================================

    def init_repo(
        self,
        path: Path,
        colocate: bool = True,
    ) -> bool:
        """
        Initialize a new repository.

        Args:
            path: Where to initialize
            colocate: If jj, whether to colocate with git

        Returns:
            True if successful
        """
        ...

    def is_repo(self, path: Path) -> bool:
        """
        Check if path is inside a repository of this backend type.

        Returns:
            True if valid repository
        """
        ...

    def get_repo_root(self, path: Path) -> Path | None:
        """
        Get root directory of repository containing path.

        Returns:
            Repository root or None if not in a repo
        """
        ...


# =============================================================================
# Backend-Specific Functions (Standalone, Not Part of Protocol)
# =============================================================================

# These functions provide backend-specific features that don't have
# equivalents in the other backend. They are NOT part of VCSProtocol.

# --- jj-specific (in jujutsu.py) ---

def jj_get_operation_log(repo_path: Path, limit: int = 20) -> list[OperationInfo]:
    """
    Get jj operation log.

    jj-specific: No git equivalent (reflog is partial approximation).

    Raises:
        VCSCapabilityError if called on git backend
    """
    ...


def jj_undo_operation(repo_path: Path, operation_id: str | None = None) -> bool:
    """
    Undo a jj operation.

    Args:
        repo_path: Repository path
        operation_id: Specific operation to undo (None = most recent)

    jj-specific: Git reflog doesn't support true undo.

    Raises:
        VCSCapabilityError if called on git backend
    """
    ...


def jj_get_change_by_id(repo_path: Path, change_id: str) -> ChangeInfo | None:
    """
    Look up a change by its stable Change ID.

    jj-specific: Git has no stable identity across rebases.

    Raises:
        VCSCapabilityError if called on git backend
    """
    ...


# --- git-specific (in git.py) ---

def git_get_reflog(repo_path: Path, limit: int = 20) -> list[OperationInfo]:
    """
    Get git reflog (approximation of operation log).

    git-specific: Less powerful than jj operation log.
    """
    ...


def git_stash(workspace_path: Path, message: str | None = None) -> bool:
    """
    Stash working directory changes.

    git-specific: jj doesn't need stash (working copy always committed).
    """
    ...


def git_stash_pop(workspace_path: Path) -> bool:
    """
    Pop stashed changes.

    git-specific: jj doesn't need stash.
    """
    ...


# =============================================================================
# Factory Function Contract
# =============================================================================

def get_vcs(
    path: Path,
    backend: VCSBackend | None = None,
    prefer_jj: bool = True,
) -> VCSProtocol:
    """
    Factory function to get appropriate VCS implementation.

    Args:
        path: Path within a repository or feature directory
        backend: Explicit backend choice (None = auto-detect)
        prefer_jj: If auto-detecting, prefer jj over git when both available

    Returns:
        VCSProtocol implementation (GitVCS or JujutsuVCS)

    Raises:
        VCSNotFoundError: Neither jj nor git available
        VCSBackendMismatchError: Requested backend doesn't match feature's locked VCS

    Detection order:
        1. If backend specified, use that
        2. If path is in a feature, read meta.json for locked VCS
        3. If jj available and prefer_jj=True, use jj
        4. If git available, use git
        5. Raise VCSNotFoundError
    """
    ...


def detect_available_backends() -> list[VCSBackend]:
    """
    Detect which VCS tools are installed and available.

    Returns:
        List of available backends, in preference order
    """
    ...


def is_jj_available() -> bool:
    """Check if jj is installed and working."""
    ...


def is_git_available() -> bool:
    """Check if git is installed and working."""
    ...


def get_jj_version() -> str | None:
    """Get installed jj version, or None if not installed."""
    ...


def get_git_version() -> str | None:
    """Get installed git version, or None if not installed."""
    ...


# =============================================================================
# Exceptions
# =============================================================================

class VCSError(Exception):
    """Base exception for VCS operations."""
    pass


class VCSNotFoundError(VCSError):
    """Neither jj nor git is available."""
    pass


class VCSCapabilityError(VCSError):
    """Operation not supported by this backend."""
    pass


class VCSBackendMismatchError(VCSError):
    """Requested backend doesn't match feature's locked VCS."""
    pass


class VCSLockError(VCSError):
    """Attempted to change VCS for a feature after it was locked."""
    pass


class VCSConflictError(VCSError):
    """Operation blocked due to unresolved conflicts."""
    pass


class VCSSyncError(VCSError):
    """Sync operation failed."""
    pass
