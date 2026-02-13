"""
Git VCS Implementation
======================

Full implementation of GitVCS that wraps git CLI commands.
Implements VCSProtocol for workspace management, sync operations,
conflict detection, and commit operations.

This module wraps existing git operations from git_ops.py where appropriate
and adds VCS abstraction layer functionality.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import VCSSyncError
from .types import (
    ChangeInfo,
    ConflictInfo,
    ConflictType,
    GIT_CAPABILITIES,
    OperationInfo,
    SyncResult,
    SyncStatus,
    VCSBackend,
    VCSCapabilities,
    WorkspaceCreateResult,
    WorkspaceInfo,
)

# Import existing git helpers where they provide reusable functionality
from ..git_ops import get_current_branch, is_git_repo, run_command


class GitVCS:
    """
    Git VCS implementation.

    Implements VCSProtocol for git repositories, wrapping git CLI commands
    for workspace management, synchronization, conflict detection, and commits.
    """

    @property
    def backend(self) -> VCSBackend:
        """Return which backend this is."""
        return VCSBackend.GIT

    @property
    def capabilities(self) -> VCSCapabilities:
        """Return capabilities of this backend."""
        return GIT_CAPABILITIES

    # =========================================================================
    # Workspace Operations
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
        Create a new git worktree for a work package.

        Args:
            workspace_path: Where to create the workspace
            workspace_name: Name for the workspace branch (e.g., "015-feature-WP01")
            base_branch: Branch to base on (for --base flag)
            base_commit: Specific commit to base on (alternative to branch)
            repo_root: Root of the git repository (auto-detected if not provided)
            sparse_exclude: List of paths to exclude via sparse-checkout (e.g., ["kitty-specs/"])

        Returns:
            WorkspaceCreateResult with workspace info or error
        """
        try:
            # Ensure parent directory exists
            workspace_path.parent.mkdir(parents=True, exist_ok=True)

            # Find repo root to run git commands from
            if repo_root is None:
                repo_root = self.get_repo_root(workspace_path.parent)
                if repo_root is None:
                    return WorkspaceCreateResult(
                        success=False,
                        workspace=None,
                        error="Could not find git repository root",
                    )

            # Build the git worktree add command
            cmd = ["git", "worktree", "add"]

            # Determine the base point for the new branch
            if base_commit:
                # Branch from specific commit
                cmd.extend(["-b", workspace_name, str(workspace_path), base_commit])
            elif base_branch:
                # Branch from specified branch
                cmd.extend(["-b", workspace_name, str(workspace_path), base_branch])
            else:
                # Default: branch from current HEAD
                cmd.extend(["-b", workspace_name, str(workspace_path)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                cwd=str(repo_root),
            )

            if result.returncode != 0:
                return WorkspaceCreateResult(
                    success=False,
                    workspace=None,
                    error=result.stderr.strip() or "Failed to create worktree",
                )

            # Apply sparse-checkout if exclusions specified
            if sparse_exclude:
                sparse_error = self._apply_sparse_checkout(workspace_path, sparse_exclude)
                if sparse_error:
                    # Non-fatal: workspace created but sparse-checkout failed
                    # Log warning but continue
                    pass

            # Add WP status files to .git/info/exclude (Bug #120 fix)
            # Use local git exclude (not .gitignore) to prevent merge pollution
            self._add_wp_status_exclusion(workspace_path)

            # Get workspace info for the newly created workspace
            workspace_info = self.get_workspace_info(workspace_path)

            return WorkspaceCreateResult(
                success=True,
                workspace=workspace_info,
                error=None,
            )

        except subprocess.TimeoutExpired:
            return WorkspaceCreateResult(
                success=False,
                workspace=None,
                error="Worktree creation timed out",
            )
        except OSError as e:
            return WorkspaceCreateResult(
                success=False,
                workspace=None,
                error=f"OS error: {e}",
            )

    def _apply_sparse_checkout(
        self,
        workspace_path: Path,
        exclude_paths: list[str],
    ) -> str | None:
        """
        Apply sparse-checkout to exclude specified paths from worktree.

        This mirrors the logic from implement.py to ensure kitty-specs/
        and other paths can be excluded from worktrees for proper isolation.

        Args:
            workspace_path: Path to the workspace/worktree
            exclude_paths: List of paths to exclude (e.g., ["kitty-specs/"])

        Returns:
            Error message if failed, None if successful
        """
        try:
            # Get sparse-checkout file path via git (works for worktrees)
            sparse_checkout_result = subprocess.run(
                ["git", "rev-parse", "--git-path", "info/sparse-checkout"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )

            if sparse_checkout_result.returncode != 0:
                return "Unable to locate sparse-checkout file"

            sparse_checkout_file = Path(sparse_checkout_result.stdout.strip())

            # Enable sparse-checkout (disable cone mode for exclusion patterns)
            subprocess.run(
                ["git", "config", "core.sparseCheckout", "true"],
                cwd=workspace_path,
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["git", "config", "core.sparseCheckoutCone", "false"],
                cwd=workspace_path,
                capture_output=True,
                timeout=10,
            )

            # Build sparse-checkout patterns
            # Pattern: Include everything (/*), then exclude specified paths
            patterns = ["/*"]
            for path in exclude_paths:
                # Normalize path (remove trailing slash if present)
                normalized = path.rstrip("/")
                patterns.append(f"!/{normalized}/")
                patterns.append(f"!/{normalized}/**")

            # Write sparse-checkout patterns
            sparse_checkout_file.parent.mkdir(parents=True, exist_ok=True)
            sparse_checkout_file.write_text("\n".join(patterns) + "\n", encoding="utf-8")

            # Apply sparse-checkout (updates working tree)
            apply_result = subprocess.run(
                ["git", "read-tree", "-mu", "HEAD"],
                cwd=workspace_path,
                capture_output=True,
                timeout=30,
            )

            if apply_result.returncode != 0:
                return "Failed to apply sparse-checkout patterns"

            # Add excluded paths to .git/info/exclude to prevent manual git add
            # Sparse-checkout only controls checkout, NOT staging
            # Use .git/info/exclude (local, unversioned) instead of .gitignore (fixes #120)
            git_dir = self._get_git_dir(workspace_path)
            if git_dir:
                exclude_file = git_dir / "info" / "exclude"
                exclude_file.parent.mkdir(parents=True, exist_ok=True)

                # Read existing exclude content
                existing_exclude = ""
                if exclude_file.exists():
                    existing_exclude = exclude_file.read_text(encoding="utf-8")

                # Add excluded paths if not already present
                exclude_entries = []
                for path in exclude_paths:
                    normalized = path.rstrip("/")
                    pattern = f"{normalized}/"
                    if pattern not in existing_exclude:
                        exclude_entries.append(f"# Excluded via sparse-checkout\n{pattern}\n")

                if exclude_entries:
                    # Append new entries to existing content
                    new_content = existing_exclude.rstrip() + "\n" + "".join(exclude_entries)
                    exclude_file.write_text(new_content.lstrip(), encoding="utf-8")

            return None

        except subprocess.TimeoutExpired:
            return "Sparse-checkout operation timed out"
        except OSError as e:
            return f"OS error during sparse-checkout: {e}"

    def _get_git_dir(self, workspace_path: Path) -> Path | None:
        """
        Get the .git directory for a workspace (handles worktrees).

        For worktrees, .git is a file pointing to the actual git directory.
        For regular repos, .git is a directory.

        Args:
            workspace_path: Path to the workspace

        Returns:
            Path to git directory, or None if not found
        """
        git_path = workspace_path / ".git"

        if not git_path.exists():
            return None

        # For worktrees, .git is a file with "gitdir: /path/to/git/dir"
        if git_path.is_file():
            try:
                git_content = git_path.read_text().strip()
                if git_content.startswith("gitdir:"):
                    git_dir_str = git_content.split(":", 1)[1].strip()
                    git_dir = Path(git_dir_str)
                    if git_dir.exists():
                        return git_dir
            except (OSError, IndexError):
                return None

        # For regular repos, .git is a directory
        elif git_path.is_dir():
            return git_path

        return None

    def _add_wp_status_exclusion(self, workspace_path: Path) -> None:
        """
        Add WP status files exclusion to .git/info/exclude.

        This prevents WP status files from being accidentally staged in worktrees.
        Uses .git/info/exclude (local, unversioned) instead of .gitignore to
        prevent merge pollution (fixes Bug #120).

        Args:
            workspace_path: Path to the workspace
        """
        git_dir = self._get_git_dir(workspace_path)
        if not git_dir:
            return

        exclude_file = git_dir / "info" / "exclude"
        exclude_file.parent.mkdir(parents=True, exist_ok=True)

        exclude_entry = "# Block WP status files (managed in planning branch, prevents merge conflicts)\n# Research artifacts in kitty-specs/**/research/ are allowed\nkitty-specs/**/tasks/*.md\n"

        # Read existing exclude content
        existing_content = ""
        if exclude_file.exists():
            existing_content = exclude_file.read_text(encoding="utf-8")

        # Only add if not already present
        if "kitty-specs/**/tasks/*.md" not in existing_content:
            new_content = existing_content.rstrip() + "\n" + exclude_entry
            exclude_file.write_text(new_content.lstrip(), encoding="utf-8")

    def remove_workspace(self, workspace_path: Path) -> bool:
        """
        Remove a git worktree.

        Args:
            workspace_path: Path to the workspace to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find repo root to run git commands from
            repo_root = self.get_repo_root(workspace_path)
            if repo_root is None:
                # Try parent directory if workspace_path is the worktree itself
                repo_root = self.get_repo_root(workspace_path.parent)
            if repo_root is None:
                return False

            result = subprocess.run(
                ["git", "worktree", "remove", str(workspace_path), "--force"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(repo_root),
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def get_workspace_info(self, workspace_path: Path) -> WorkspaceInfo | None:
        """
        Get information about a workspace.

        Args:
            workspace_path: Path to the workspace

        Returns:
            WorkspaceInfo or None if not a valid workspace
        """
        workspace_path = workspace_path.resolve()

        if not workspace_path.exists():
            return None

        # Check if it's a worktree
        git_dir = workspace_path / ".git"
        if not git_dir.exists():
            return None

        try:
            # Get current branch using existing helper from git_ops.py
            current_branch = get_current_branch(workspace_path)

            # Get current commit
            commit_result = subprocess.run(
                ["git", "-C", str(workspace_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            current_commit = (
                commit_result.stdout.strip() if commit_result.returncode == 0 else ""
            )

            # Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "-C", str(workspace_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            has_uncommitted = bool(status_result.stdout.strip())

            # Check for conflicts
            has_conflicts = self.has_conflicts(workspace_path)

            # Derive workspace name from path
            workspace_name = workspace_path.name

            # Try to determine base branch from tracking
            base_branch = self._get_tracking_branch(workspace_path)

            return WorkspaceInfo(
                name=workspace_name,
                path=workspace_path,
                backend=VCSBackend.GIT,
                is_colocated=False,
                current_branch=current_branch,
                current_change_id=None,  # Git doesn't have change IDs
                current_commit_id=current_commit,
                base_branch=base_branch,
                base_commit_id=None,  # Would need to track this separately
                is_stale=self.is_workspace_stale(workspace_path),
                has_conflicts=has_conflicts,
                has_uncommitted=has_uncommitted,
            )

        except (subprocess.TimeoutExpired, OSError):
            return None

    def list_workspaces(self, repo_root: Path) -> list[WorkspaceInfo]:
        """
        List all worktrees for a repository.

        Args:
            repo_root: Root of the repository

        Returns:
            List of WorkspaceInfo for all worktrees
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if result.returncode != 0:
                return []

            workspaces = []
            lines = result.stdout.strip().split("\n")
            current_path = None

            for line in lines:
                if line.startswith("worktree "):
                    current_path = Path(line[9:])
                elif line == "" and current_path:
                    # End of entry
                    info = self.get_workspace_info(current_path)
                    if info:
                        workspaces.append(info)
                    current_path = None

            # Don't forget the last entry
            if current_path:
                info = self.get_workspace_info(current_path)
                if info:
                    workspaces.append(info)

            return workspaces

        except (subprocess.TimeoutExpired, OSError):
            return []

    # =========================================================================
    # Sync Operations
    # =========================================================================

    def sync_workspace(self, workspace_path: Path) -> SyncResult:
        """
        Synchronize workspace with upstream changes.

        For git, this fetches and attempts to rebase. Conflicts will
        block the operation (unlike jj where conflicts are stored).

        Args:
            workspace_path: Path to the workspace to sync

        Returns:
            SyncResult with status, conflicts, and changes integrated
        """
        try:
            # 1. Fetch latest
            fetch_result = subprocess.run(
                ["git", "-C", str(workspace_path), "fetch", "--all"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )

            if fetch_result.returncode != 0:
                return SyncResult(
                    status=SyncStatus.FAILED,
                    conflicts=[],
                    files_updated=0,
                    files_added=0,
                    files_deleted=0,
                    changes_integrated=[],
                    message=f"Fetch failed: {fetch_result.stderr.strip()}",
                )

            # 2. Get the base branch to rebase onto
            base_branch = self._get_tracking_branch(workspace_path)
            if not base_branch:
                # Try to find upstream
                base_branch = self._get_upstream_branch(workspace_path)

            if not base_branch:
                return SyncResult(
                    status=SyncStatus.UP_TO_DATE,
                    conflicts=[],
                    files_updated=0,
                    files_added=0,
                    files_deleted=0,
                    changes_integrated=[],
                    message="No upstream branch configured",
                )

            # 3. Check if already up to date
            merge_base_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace_path),
                    "merge-base",
                    "HEAD",
                    base_branch,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            head_result = subprocess.run(
                ["git", "-C", str(workspace_path), "rev-parse", base_branch],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )

            if (
                merge_base_result.returncode == 0
                and head_result.returncode == 0
                and merge_base_result.stdout.strip() == head_result.stdout.strip()
            ):
                return SyncResult(
                    status=SyncStatus.UP_TO_DATE,
                    conflicts=[],
                    files_updated=0,
                    files_added=0,
                    files_deleted=0,
                    changes_integrated=[],
                    message="Already up to date",
                )

            # 4. Get commits that will be integrated
            changes_to_integrate = self._get_commits_between(
                workspace_path, "HEAD", base_branch
            )

            # 4b. Capture HEAD before rebase for stats calculation
            pre_rebase_result = subprocess.run(
                ["git", "-C", str(workspace_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            pre_rebase_head = (
                pre_rebase_result.stdout.strip()
                if pre_rebase_result.returncode == 0
                else None
            )

            # 5. Try rebase
            rebase_result = subprocess.run(
                ["git", "-C", str(workspace_path), "rebase", base_branch],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )

            if rebase_result.returncode != 0:
                # Check for conflicts
                conflicts = self.detect_conflicts(workspace_path)
                if conflicts:
                    return SyncResult(
                        status=SyncStatus.CONFLICTS,
                        conflicts=conflicts,
                        files_updated=0,
                        files_added=0,
                        files_deleted=0,
                        changes_integrated=changes_to_integrate,
                        message="Rebase has conflicts that must be resolved",
                    )
                else:
                    # Abort the failed rebase
                    subprocess.run(
                        ["git", "-C", str(workspace_path), "rebase", "--abort"],
                        capture_output=True,
                        timeout=30,
                    )
                    return SyncResult(
                        status=SyncStatus.FAILED,
                        conflicts=[],
                        files_updated=0,
                        files_added=0,
                        files_deleted=0,
                        changes_integrated=[],
                        message=f"Rebase failed: {rebase_result.stderr.strip()}",
                    )

            # 6. Count changed files by comparing pre/post rebase commits
            files_updated, files_added, files_deleted = (0, 0, 0)
            if pre_rebase_head:
                files_updated, files_added, files_deleted = self._parse_rebase_stats(
                    workspace_path, pre_rebase_head, "HEAD"
                )

            return SyncResult(
                status=SyncStatus.SYNCED,
                conflicts=[],
                files_updated=files_updated,
                files_added=files_added,
                files_deleted=files_deleted,
                changes_integrated=changes_to_integrate,
                message="Successfully rebased onto upstream",
            )

        except subprocess.TimeoutExpired:
            raise VCSSyncError("Sync operation timed out")
        except OSError as e:
            raise VCSSyncError(f"OS error during sync: {e}")

    def is_workspace_stale(self, workspace_path: Path) -> bool:
        """
        Check if workspace needs sync (base has changed).

        Args:
            workspace_path: Path to the workspace

        Returns:
            True if sync is needed, False if up-to-date
        """
        try:
            # Get the tracking branch
            base_branch = self._get_tracking_branch(workspace_path)
            if not base_branch:
                return False

            # Compare HEAD with upstream
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace_path),
                    "rev-list",
                    "--count",
                    f"HEAD..{base_branch}",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if result.returncode != 0:
                return False

            # If there are commits in upstream not in HEAD, we're stale
            count = int(result.stdout.strip()) if result.stdout.strip() else 0
            return count > 0

        except (subprocess.TimeoutExpired, OSError, ValueError):
            return False

    # =========================================================================
    # Conflict Operations
    # =========================================================================

    def detect_conflicts(self, workspace_path: Path) -> list[ConflictInfo]:
        """
        Detect conflicts in a workspace.

        Args:
            workspace_path: Path to the workspace

        Returns:
            List of ConflictInfo for all conflicted files
        """
        try:
            # Get list of conflicted files
            result = subprocess.run(
                ["git", "-C", str(workspace_path), "diff", "--name-only", "--diff-filter=U"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if result.returncode != 0 or not result.stdout.strip():
                # Also check git status for unmerged paths
                status_result = subprocess.run(
                    ["git", "-C", str(workspace_path), "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )

                conflicts = []
                for line in status_result.stdout.strip().split("\n"):
                    if line and line[:2] in ("UU", "AA", "DD", "AU", "UA", "DU", "UD"):
                        file_path = Path(line[3:].strip())
                        conflict_type = self._status_to_conflict_type(line[:2])
                        full_path = workspace_path / file_path

                        line_ranges = None
                        if full_path.exists() and conflict_type == ConflictType.CONTENT:
                            line_ranges = self._parse_conflict_markers(full_path)

                        conflicts.append(
                            ConflictInfo(
                                file_path=file_path,
                                conflict_type=conflict_type,
                                line_ranges=line_ranges,
                                sides=2,
                                is_resolved=False,
                                our_content=None,
                                their_content=None,
                                base_content=None,
                            )
                        )
                return conflicts

            conflicts = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                file_path = Path(line.strip())
                full_path = workspace_path / file_path

                # Parse conflict markers to get line ranges
                line_ranges = None
                if full_path.exists():
                    line_ranges = self._parse_conflict_markers(full_path)

                conflicts.append(
                    ConflictInfo(
                        file_path=file_path,
                        conflict_type=ConflictType.CONTENT,
                        line_ranges=line_ranges,
                        sides=2,
                        is_resolved=False,
                        our_content=None,  # Could extract from markers
                        their_content=None,
                        base_content=None,
                    )
                )

            return conflicts

        except (subprocess.TimeoutExpired, OSError):
            return []

    def has_conflicts(self, workspace_path: Path) -> bool:
        """
        Check if workspace has any unresolved conflicts.

        Args:
            workspace_path: Path to the workspace

        Returns:
            True if conflicts exist, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(workspace_path), "diff", "--name-only", "--diff-filter=U"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if result.returncode == 0 and result.stdout.strip():
                return True

            # Also check git status
            status_result = subprocess.run(
                ["git", "-C", str(workspace_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            for line in status_result.stdout.strip().split("\n"):
                if line and line[:2] in ("UU", "AA", "DD", "AU", "UA", "DU", "UD"):
                    return True

            return False

        except (subprocess.TimeoutExpired, OSError):
            return False

    # =========================================================================
    # Commit/Change Operations
    # =========================================================================

    def get_current_change(self, workspace_path: Path) -> ChangeInfo | None:
        """
        Get info about current working copy commit/change.

        Args:
            workspace_path: Path to the workspace

        Returns:
            ChangeInfo for current HEAD, None if invalid
        """
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace_path),
                    "log",
                    "-1",
                    "--format=%H|%an|%ae|%at|%s|%P|%B",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return None

            return self._parse_log_line(result.stdout.strip())

        except (subprocess.TimeoutExpired, OSError):
            return None

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
            revision_range: Git revision range (e.g., "main..HEAD")
            limit: Maximum number to return

        Returns:
            List of ChangeInfo
        """
        try:
            cmd = [
                "git",
                "-C",
                str(repo_path),
                "log",
                "--format=%H|%an|%ae|%at|%s|%P",
            ]

            if limit:
                cmd.append(f"-{limit}")

            if revision_range:
                cmd.append(revision_range)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )

            if result.returncode != 0:
                return []

            changes = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    change = self._parse_log_line_short(line)
                    if change:
                        changes.append(change)

            return changes

        except (subprocess.TimeoutExpired, OSError):
            return []

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
        """
        try:
            # Stage files
            if paths:
                for path in paths:
                    subprocess.run(
                        ["git", "-C", str(workspace_path), "add", str(path)],
                        capture_output=True,
                        timeout=30,
                    )
            else:
                subprocess.run(
                    ["git", "-C", str(workspace_path), "add", "-A"],
                    capture_output=True,
                    timeout=30,
                )

            # Check if there are staged changes
            status_result = subprocess.run(
                ["git", "-C", str(workspace_path), "diff", "--cached", "--quiet"],
                capture_output=True,
                timeout=30,
            )

            if status_result.returncode == 0:
                # No changes to commit
                return None

            # Commit
            commit_result = subprocess.run(
                ["git", "-C", str(workspace_path), "commit", "-m", message],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )

            if commit_result.returncode != 0:
                return None

            # Return info about the new commit
            return self.get_current_change(workspace_path)

        except (subprocess.TimeoutExpired, OSError):
            return None

    # =========================================================================
    # Repository Operations
    # =========================================================================

    def init_repo(self, path: Path, colocate: bool = True) -> bool:
        """
        Initialize a new git repository.

        Args:
            path: Where to initialize
            colocate: Ignored for git (only relevant for jj)

        Returns:
            True if successful, False otherwise
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "init"],
                cwd=str(path),
                capture_output=True,
                timeout=30,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def is_repo(self, path: Path) -> bool:
        """
        Check if path is inside a git repository.

        Wraps existing is_git_repo from git_ops.py.

        Args:
            path: Path to check

        Returns:
            True if valid git repository
        """
        return is_git_repo(path)

    def get_repo_root(self, path: Path) -> Path | None:
        """
        Get root directory of repository containing path.

        Args:
            path: Path within the repository

        Returns:
            Repository root or None if not in a repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip())
            return None

        except (subprocess.TimeoutExpired, OSError):
            return None

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _get_tracking_branch(self, workspace_path: Path) -> str | None:
        """Get the tracking branch for the current branch."""
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace_path),
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{u}",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, OSError):
            return None

    def _get_upstream_branch(self, workspace_path: Path) -> str | None:
        """Try to find the upstream branch (origin/main or origin/master)."""
        for branch in ["origin/main", "origin/master", "main", "master"]:
            try:
                result = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(workspace_path),
                        "rev-parse",
                        "--verify",
                        branch,
                    ],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    return branch
            except (subprocess.TimeoutExpired, OSError):
                continue
        return None

    def _get_commits_between(
        self, workspace_path: Path, from_ref: str, to_ref: str
    ) -> list[ChangeInfo]:
        """Get commits between two refs."""
        return self.get_changes(workspace_path, f"{from_ref}..{to_ref}")

    def _parse_rebase_stats(
        self,
        workspace_path: Path,
        before_commit: str,
        after_commit: str,
    ) -> tuple[int, int, int]:
        """
        Calculate file statistics from a rebase by diffing before/after commits.

        Git rebase doesn't give detailed stats in machine-readable format during
        the rebase itself, so we compute the diff between the commit before and
        after the rebase to determine files updated/added/deleted.

        Args:
            workspace_path: Path to the workspace
            before_commit: Commit SHA before rebase
            after_commit: Commit SHA after rebase (typically HEAD)

        Returns:
            Tuple of (files_updated, files_added, files_deleted)
        """
        try:
            # Use git diff --name-status to get file changes
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace_path),
                    "diff",
                    "--name-status",
                    before_commit,
                    after_commit,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if result.returncode != 0:
                return (0, 0, 0)

            files_updated = 0
            files_added = 0
            files_deleted = 0

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                # Format: "M\tfilename" or "A\tfilename" or "D\tfilename"
                # Also handles "R100\told\tnew" for renames
                status = line[0]
                if status == "M":
                    files_updated += 1
                elif status == "A":
                    files_added += 1
                elif status == "D":
                    files_deleted += 1
                elif status == "R":
                    # Rename counts as delete + add
                    files_deleted += 1
                    files_added += 1

            return (files_updated, files_added, files_deleted)

        except (subprocess.TimeoutExpired, OSError):
            return (0, 0, 0)

    def _parse_conflict_markers(self, file_path: Path) -> list[tuple[int, int]]:
        """Find line ranges with conflict markers."""
        ranges = []
        in_conflict = False
        start_line = 0

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if line.startswith("<<<<<<<"):
                        in_conflict = True
                        start_line = i
                    elif line.startswith(">>>>>>>") and in_conflict:
                        ranges.append((start_line, i))
                        in_conflict = False
        except OSError:
            pass

        return ranges

    def _status_to_conflict_type(self, status: str) -> ConflictType:
        """Convert git status code to ConflictType."""
        if status == "UU":
            return ConflictType.CONTENT
        elif status == "AA":
            return ConflictType.ADD_ADD
        elif status == "DD":
            return ConflictType.MODIFY_DELETE
        elif status in ("AU", "UA"):
            return ConflictType.MODIFY_DELETE
        elif status in ("DU", "UD"):
            return ConflictType.MODIFY_DELETE
        return ConflictType.CONTENT

    def _parse_log_line(self, line: str) -> ChangeInfo | None:
        """Parse a git log line with full body."""
        try:
            parts = line.split("|", 6)
            if len(parts) < 6:
                return None

            commit_id = parts[0]
            author = parts[1]
            author_email = parts[2]
            timestamp = datetime.fromtimestamp(int(parts[3]), tz=timezone.utc)
            message = parts[4]
            parents = parts[5].split() if parts[5] else []
            message_full = parts[6] if len(parts) > 6 else message

            return ChangeInfo(
                change_id=None,  # Git doesn't have change IDs
                commit_id=commit_id,
                message=message,
                message_full=message_full,
                author=author,
                author_email=author_email,
                timestamp=timestamp,
                parents=parents,
                is_merge=len(parents) > 1,
                is_conflicted=False,
                is_empty=False,
            )
        except (ValueError, IndexError):
            return None

    def _parse_log_line_short(self, line: str) -> ChangeInfo | None:
        """Parse a git log line without full body."""
        try:
            parts = line.split("|", 5)
            if len(parts) < 5:
                return None

            commit_id = parts[0]
            author = parts[1]
            author_email = parts[2]
            timestamp = datetime.fromtimestamp(int(parts[3]), tz=timezone.utc)
            message = parts[4]
            parents = parts[5].split() if len(parts) > 5 and parts[5] else []

            return ChangeInfo(
                change_id=None,
                commit_id=commit_id,
                message=message,
                message_full=message,
                author=author,
                author_email=author_email,
                timestamp=timestamp,
                parents=parents,
                is_merge=len(parents) > 1,
                is_conflicted=False,
                is_empty=False,
            )
        except (ValueError, IndexError):
            return None


# =============================================================================
# Git-Specific Standalone Functions
# =============================================================================


def git_get_reflog(repo_path: Path, limit: int = 20) -> list[OperationInfo]:
    """
    Get git reflog as operation history.

    git-specific: Less powerful than jj operation log, but provides
    some visibility into repository history.

    Args:
        repo_path: Repository path
        limit: Maximum number of entries to return

    Returns:
        List of OperationInfo from reflog
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "reflog",
                f"-{limit}",
                "--format=%H|%gD|%gs|%ci",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        if result.returncode != 0:
            return []

        operations = []
        for i, line in enumerate(result.stdout.strip().split("\n")):
            if not line:
                continue
            try:
                parts = line.split("|", 3)
                if len(parts) < 4:
                    continue

                commit_id = parts[0]
                ref = parts[1]
                description = parts[2]
                timestamp_str = parts[3]

                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_str.replace(" ", "T").replace(" ", "")
                    )
                except ValueError:
                    timestamp = datetime.now(timezone.utc)

                operations.append(
                    OperationInfo(
                        operation_id=f"reflog-{i}",
                        timestamp=timestamp,
                        description=description,
                        heads=[commit_id],
                        working_copy_commit=commit_id,
                        is_undoable=False,  # Git reflog entries aren't truly undoable
                        parent_operation=f"reflog-{i+1}" if i < limit - 1 else None,
                    )
                )
            except (ValueError, IndexError):
                continue

        return operations

    except (subprocess.TimeoutExpired, OSError):
        return []


def git_stash(workspace_path: Path, message: str | None = None) -> bool:
    """
    Stash working directory changes.

    git-specific: jj doesn't need stash (working copy always committed).

    Args:
        workspace_path: Workspace path
        message: Optional stash message

    Returns:
        True if successful
    """
    try:
        cmd = ["git", "-C", str(workspace_path), "stash", "push"]
        if message:
            cmd.extend(["-m", message])

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def git_stash_pop(workspace_path: Path) -> bool:
    """
    Pop stashed changes.

    git-specific: jj doesn't need stash.

    Args:
        workspace_path: Workspace path

    Returns:
        True if successful
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace_path), "stash", "pop"],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
