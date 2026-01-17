"""
Jujutsu VCS Implementation (Stub)
=================================

This is a stub implementation for JujutsuVCS that will be fully implemented in WP04.
It provides the minimal implementation needed for get_vcs() factory to work.
"""

from __future__ import annotations

from pathlib import Path

from .types import (
    ChangeInfo,
    ConflictInfo,
    JJ_CAPABILITIES,
    SyncResult,
    VCSBackend,
    VCSCapabilities,
    WorkspaceCreateResult,
    WorkspaceInfo,
)


class JujutsuVCS:
    """
    Jujutsu VCS implementation.

    This is a stub that will be fully implemented in WP04.
    """

    @property
    def backend(self) -> VCSBackend:
        """Return which backend this is."""
        return VCSBackend.JUJUTSU

    @property
    def capabilities(self) -> VCSCapabilities:
        """Return capabilities of this backend."""
        return JJ_CAPABILITIES

    # Workspace operations - stubs
    def create_workspace(
        self,
        workspace_path: Path,
        workspace_name: str,
        base_branch: str | None = None,
        base_commit: str | None = None,
    ) -> WorkspaceCreateResult:
        """Create a new workspace. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.create_workspace not yet implemented")

    def remove_workspace(self, workspace_path: Path) -> bool:
        """Remove a workspace. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.remove_workspace not yet implemented")

    def get_workspace_info(self, workspace_path: Path) -> WorkspaceInfo | None:
        """Get workspace info. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.get_workspace_info not yet implemented")

    def list_workspaces(self, repo_root: Path) -> list[WorkspaceInfo]:
        """List workspaces. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.list_workspaces not yet implemented")

    # Sync operations - stubs
    def sync_workspace(self, workspace_path: Path) -> SyncResult:
        """Sync workspace. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.sync_workspace not yet implemented")

    def is_workspace_stale(self, workspace_path: Path) -> bool:
        """Check if stale. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.is_workspace_stale not yet implemented")

    # Conflict operations - stubs
    def detect_conflicts(self, workspace_path: Path) -> list[ConflictInfo]:
        """Detect conflicts. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.detect_conflicts not yet implemented")

    def has_conflicts(self, workspace_path: Path) -> bool:
        """Check for conflicts. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.has_conflicts not yet implemented")

    # Commit operations - stubs
    def get_current_change(self, workspace_path: Path) -> ChangeInfo | None:
        """Get current change. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.get_current_change not yet implemented")

    def get_changes(
        self,
        repo_path: Path,
        revision_range: str | None = None,
        limit: int | None = None,
    ) -> list[ChangeInfo]:
        """Get changes. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.get_changes not yet implemented")

    def commit(
        self,
        workspace_path: Path,
        message: str,
        paths: list[Path] | None = None,
    ) -> ChangeInfo | None:
        """Commit changes. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.commit not yet implemented")

    # Repository operations - stubs
    def init_repo(self, path: Path, colocate: bool = True) -> bool:
        """Init repo. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.init_repo not yet implemented")

    def is_repo(self, path: Path) -> bool:
        """Check if repo. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.is_repo not yet implemented")

    def get_repo_root(self, path: Path) -> Path | None:
        """Get repo root. Stub - to be implemented in WP04."""
        raise NotImplementedError("JujutsuVCS.get_repo_root not yet implemented")
