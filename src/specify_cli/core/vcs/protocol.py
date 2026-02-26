"""
VCS Protocol Module
===================

This module defines the VCSProtocol interface that GitVCS and JujutsuVCS implement.
The protocol uses Python's typing.Protocol for structural subtyping.

See kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py
for the complete interface contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from .types import (
    ChangeInfo,
    ConflictInfo,
    SyncResult,
    VCSBackend,
    VCSCapabilities,
    WorkspaceCreateResult,
    WorkspaceInfo,
)


@runtime_checkable
class VCSProtocol(Protocol):
    """
    Interface contract for VCS backends.

    Both GitVCS and JujutsuVCS must implement this protocol.
    Operations not supported by a backend should raise VCSCapabilityError.

    This protocol is runtime-checkable, so you can use:
        isinstance(obj, VCSProtocol)
    to verify an object implements the interface.
    """

    @property
    def backend(self) -> VCSBackend:
        """Return which backend this is (GIT or JUJUTSU)."""
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
        repo_root: Path | None = None,
        sparse_exclude: list[str] | None = None,
    ) -> WorkspaceCreateResult:
        """
        Create a new workspace for a work package.

        Args:
            workspace_path: Where to create the workspace
            workspace_name: Name for the workspace (e.g., "015-feature-WP01")
            base_branch: Branch to base on (for --base flag)
            base_commit: Specific commit to base on (alternative to branch)
            repo_root: Repository root for command execution when caller already knows it
            sparse_exclude: Optional checkout exclusions for backends that support sparse mode

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

        Args:
            workspace_path: Path to the workspace to remove

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

        Args:
            workspace_path: Path to the workspace

        Returns:
            WorkspaceInfo or None if not a valid workspace
        """
        ...

    def list_workspaces(self, repo_root: Path) -> list[WorkspaceInfo]:
        """
        List all workspaces for a repository.

        Args:
            repo_root: Root of the repository

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
        - Git: Fetch + rebase, conflicts block the operation
        - jj: update-stale, conflicts are stored (non-blocking)

        Args:
            workspace_path: Path to the workspace to sync

        Returns:
            SyncResult with status, conflicts, and changes integrated
        """
        ...

    def is_workspace_stale(self, workspace_path: Path) -> bool:
        """
        Check if workspace needs sync (base has changed).

        Args:
            workspace_path: Path to the workspace

        Returns:
            True if sync is needed, False if up-to-date
        """
        ...

    # =========================================================================
    # Conflict Operations (Core - Required)
    # =========================================================================

    def detect_conflicts(self, workspace_path: Path) -> list[ConflictInfo]:
        """
        Detect conflicts in a workspace.

        Args:
            workspace_path: Path to the workspace

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

        Args:
            workspace_path: Path to the workspace

        Returns:
            True if conflicts exist, False otherwise
        """
        ...

    # =========================================================================
    # Commit/Change Operations (Core - Required)
    # =========================================================================

    def get_current_change(self, workspace_path: Path) -> ChangeInfo | None:
        """
        Get info about current working copy commit/change.

        Args:
            workspace_path: Path to the workspace

        Returns:
            ChangeInfo for current HEAD/working copy, None if invalid
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
            True if successful, False otherwise
        """
        ...

    def is_repo(self, path: Path) -> bool:
        """
        Check if path is inside a repository of this backend type.

        Args:
            path: Path to check

        Returns:
            True if valid repository of this backend type
        """
        ...

    def get_repo_root(self, path: Path) -> Path | None:
        """
        Get root directory of repository containing path.

        Args:
            path: Path within the repository

        Returns:
            Repository root or None if not in a repo
        """
        ...
