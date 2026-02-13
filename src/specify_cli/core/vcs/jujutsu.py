"""
Jujutsu VCS Implementation
==========================

Full implementation of JujutsuVCS that wraps jj CLI commands.
Implements VCSProtocol for workspace management, sync operations,
conflict detection, and commit operations.

Key differences from Git:
- Conflicts are stored in commits (non-blocking) instead of blocking operations
- Working copy is always a commit (no staging area)
- Change IDs are stable across rebases
- Full operation log with undo capability
- Native workspace support
"""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import VCSSyncError
from .types import (
    ChangeInfo,
    ConflictInfo,
    ConflictType,
    JJ_CAPABILITIES,
    OperationInfo,
    SyncResult,
    SyncStatus,
    VCSBackend,
    VCSCapabilities,
    WorkspaceCreateResult,
    WorkspaceInfo,
)


# Known benign stderr patterns from jj that should NOT be treated as errors
# These are info messages, hints, and warnings that jj prints to stderr
JJ_BENIGN_STDERR_PATTERNS = [
    "Reset the working copy parent to",
    "Done importing changes from the underlying Git repo",
    "Created workspace in",
    "Working copy",
    "Parent commit",
    "Added ",
    "Warning:",
    "Hint:",
    "Concurrent modification detected, resolving automatically",
]


def _extract_jj_error(stderr: str) -> str | None:
    """
    Extract actual error message from jj stderr output.

    jj prints various informational messages to stderr (hints, warnings,
    status updates) even during successful operations. This function
    filters out benign messages and extracts only actual errors.

    Actual jj errors start with "Error:" at the beginning of a line.

    Args:
        stderr: Raw stderr output from jj command

    Returns:
        Error message if found, None if no actual error
    """
    if not stderr:
        return None

    lines = stderr.strip().split("\n")
    error_lines = []

    for line in lines:
        stripped = line.strip()

        # Actual jj errors start with "Error:"
        if stripped.startswith("Error:"):
            error_lines.append(stripped)
        # Also capture "Caused by:" lines that follow errors
        elif stripped.startswith("Caused by:") and error_lines:
            error_lines.append(stripped)
        # Skip benign patterns
        elif any(pattern in stripped for pattern in JJ_BENIGN_STDERR_PATTERNS):
            continue
        # Skip empty lines
        elif not stripped:
            continue

    if error_lines:
        return " ".join(error_lines)

    return None


class JujutsuVCS:
    """
    Jujutsu VCS implementation.

    Implements VCSProtocol for jj repositories, wrapping jj CLI commands
    for workspace management, synchronization, conflict detection, and commits.

    jj differs from git in key ways:
    - Conflicts don't block operations - they're stored in commits
    - Working copy is always a commit (use `jj describe` to set message)
    - Change IDs are stable across rebases
    - Full operation log with undo capability
    """

    @property
    def backend(self) -> VCSBackend:
        """Return which backend this is."""
        return VCSBackend.JUJUTSU

    @property
    def capabilities(self) -> VCSCapabilities:
        """Return capabilities of this backend."""
        return JJ_CAPABILITIES

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
    ) -> WorkspaceCreateResult:
        """
        Create a new jj workspace.

        Args:
            workspace_path: Where to create the workspace
            workspace_name: Name for the workspace
            base_branch: Branch/revision to base on
            base_commit: Specific commit/change to base on
            repo_root: Root of the jj repository (auto-detected if not provided)

        Returns:
            WorkspaceCreateResult with workspace info or error
        """
        try:
            # Ensure parent directory exists
            workspace_path.parent.mkdir(parents=True, exist_ok=True)

            # Find repo root to run jj commands from
            if repo_root is None:
                repo_root = self.get_repo_root(workspace_path.parent)
                if repo_root is None:
                    return WorkspaceCreateResult(
                        success=False,
                        workspace=None,
                        error="Could not find jj repository root",
                    )

            # Build the jj workspace add command
            cmd = ["jj", "workspace", "add", str(workspace_path), "--name", workspace_name]

            # Add revision if specified
            if base_commit:
                cmd.extend(["--revision", base_commit])
            elif base_branch:
                cmd.extend(["--revision", base_branch])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                cwd=str(repo_root),
            )

            # jj has quirky error handling - sometimes returns exit 0 with "Error:" in stderr
            # Check for actual errors in stderr even if returncode is 0
            jj_error = _extract_jj_error(result.stderr)

            if result.returncode != 0:
                # Prefer extracted error over raw stderr
                error_msg = jj_error or result.stderr.strip() or "Failed to create workspace"
                return WorkspaceCreateResult(
                    success=False,
                    workspace=None,
                    error=error_msg,
                )

            # Even with returncode 0, jj might have printed "Error:" to stderr
            if jj_error:
                return WorkspaceCreateResult(
                    success=False,
                    workspace=None,
                    error=jj_error,
                )

            # Create a bookmark pointing to the workspace's current revision
            # This is necessary because dependent WPs need to reference this
            # workspace by name (e.g., "001-feature-WP01" as a base revision)
            # Unlike git worktree which auto-creates branches, jj workspace add
            # does NOT create bookmarks.
            bookmark_result = subprocess.run(
                ["jj", "bookmark", "create", workspace_name, "-r", "@"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(workspace_path),  # Run from new workspace
            )

            # Check for bookmark creation errors
            bookmark_error = _extract_jj_error(bookmark_result.stderr)
            if bookmark_result.returncode != 0 or bookmark_error:
                # Workspace was created but bookmark failed - clean up and report
                error_msg = bookmark_error or bookmark_result.stderr.strip() or "Failed to create bookmark"
                # Try to clean up the workspace
                try:
                    subprocess.run(
                        ["jj", "workspace", "forget", workspace_name],
                        capture_output=True,
                        timeout=30,
                        cwd=str(repo_root),
                    )
                    shutil.rmtree(workspace_path, ignore_errors=True)
                except Exception:
                    pass
                return WorkspaceCreateResult(
                    success=False,
                    workspace=None,
                    error=f"Workspace created but bookmark failed: {error_msg}",
                )

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
                error="Workspace creation timed out",
            )
        except OSError as e:
            return WorkspaceCreateResult(
                success=False,
                workspace=None,
                error=f"OS error: {e}",
            )

    def remove_workspace(self, workspace_path: Path) -> bool:
        """
        Remove a jj workspace.

        Uses `jj workspace forget` to unregister the workspace,
        then removes the directory.

        Args:
            workspace_path: Path to the workspace to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            # First, find repo root and workspace name
            repo_root = self.get_repo_root(workspace_path)
            if repo_root is None:
                return False

            # Get workspace name from the directory
            workspace_name = workspace_path.name

            # Use jj workspace forget to unregister
            result = subprocess.run(
                ["jj", "workspace", "forget", workspace_name],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(repo_root),
            )

            # Also delete the associated bookmark (created during create_workspace)
            subprocess.run(
                ["jj", "bookmark", "delete", workspace_name],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(repo_root),
            )

            # Remove the directory even if forget failed
            if workspace_path.exists():
                shutil.rmtree(workspace_path)

            return True
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

        # Check if it's a jj repo (has .jj directory)
        jj_dir = workspace_path / ".jj"
        if not jj_dir.exists():
            return None

        try:
            # Check for colocated mode
            git_dir = workspace_path / ".git"
            is_colocated = git_dir.exists()

            # Get current change info using jj log
            log_result = subprocess.run(
                [
                    "jj",
                    "log",
                    "-r",
                    "@",
                    "--no-graph",
                    "-T",
                    'change_id ++ "|" ++ commit_id ++ "|" ++ description.first_line() ++ "|" ++ if(conflict, "conflict", "") ++ "\n"',
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=str(workspace_path),
            )

            if log_result.returncode != 0:
                return None

            # Parse the log output
            line = log_result.stdout.strip().split("\n")[0] if log_result.stdout.strip() else ""
            parts = line.split("|") if line else []

            current_change_id = parts[0] if len(parts) > 0 else None
            current_commit_id = parts[1] if len(parts) > 1 else ""
            has_conflicts = len(parts) > 3 and parts[3] == "conflict"

            # Check for uncommitted changes (in jj, working copy is always committed)
            status_result = subprocess.run(
                ["jj", "status"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=str(workspace_path),
            )

            has_uncommitted = "Working copy changes:" in status_result.stdout

            # Derive workspace name from path
            workspace_name = workspace_path.name

            return WorkspaceInfo(
                name=workspace_name,
                path=workspace_path,
                backend=VCSBackend.JUJUTSU,
                is_colocated=is_colocated,
                current_branch=None,  # jj doesn't use branches the same way
                current_change_id=current_change_id,
                current_commit_id=current_commit_id,
                base_branch=None,
                base_commit_id=None,
                is_stale=self.is_workspace_stale(workspace_path),
                has_conflicts=has_conflicts,
                has_uncommitted=has_uncommitted,
            )

        except (subprocess.TimeoutExpired, OSError):
            return None

    def list_workspaces(self, repo_root: Path) -> list[WorkspaceInfo]:
        """
        List all workspaces for a repository.

        Args:
            repo_root: Root of the repository

        Returns:
            List of WorkspaceInfo for all workspaces
        """
        try:
            result = subprocess.run(
                ["jj", "workspace", "list"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(repo_root),
            )

            if result.returncode != 0:
                return []

            workspaces = []
            # Parse output like: "default: xvsrlyox 66070197 (no description set)"
            for line in result.stdout.strip().split("\n"):
                if not line or ":" not in line:
                    continue

                workspace_name = line.split(":")[0].strip()

                # For default workspace, the path is repo_root
                if workspace_name == "default":
                    workspace_path = repo_root
                else:
                    # For other workspaces, we need to find them
                    # jj workspace list doesn't show paths, so we check common locations
                    potential_paths = [
                        repo_root.parent / workspace_name,
                        repo_root / ".worktrees" / workspace_name,
                    ]
                    workspace_path = None
                    for path in potential_paths:
                        if path.exists() and (path / ".jj").exists():
                            workspace_path = path
                            break

                    if workspace_path is None:
                        continue

                info = self.get_workspace_info(workspace_path)
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

        Key difference from git: jj sync ALWAYS succeeds - conflicts are stored
        in the commit rather than blocking the operation. This allows work to
        continue even with conflicts present.

        Args:
            workspace_path: Path to the workspace to sync

        Returns:
            SyncResult with status, conflicts, and changes integrated
        """
        try:
            # For colocated repos, fetch from git first
            if (workspace_path / ".git").exists():
                subprocess.run(
                    ["jj", "git", "fetch"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                    cwd=str(workspace_path),
                )

            # Update stale workspace - this always succeeds in jj!
            result = subprocess.run(
                ["jj", "workspace", "update-stale"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                cwd=str(workspace_path),
            )

            # Check for conflicts AFTER successful sync
            conflicts = self.detect_conflicts(workspace_path)

            if result.returncode != 0:
                return SyncResult(
                    status=SyncStatus.FAILED,
                    conflicts=conflicts,
                    files_updated=0,
                    files_added=0,
                    files_deleted=0,
                    changes_integrated=[],
                    message=f"Sync failed: {result.stderr.strip()}",
                )

            # Determine status based on output and conflicts
            if "Nothing to do" in result.stdout or "already up to date" in result.stdout.lower():
                status = SyncStatus.UP_TO_DATE
            elif conflicts:
                status = SyncStatus.CONFLICTS
            else:
                status = SyncStatus.SYNCED

            # Parse file changes from output (if available)
            files_updated, files_added, files_deleted = self._parse_sync_stats(result.stdout)

            return SyncResult(
                status=status,
                conflicts=conflicts,
                files_updated=files_updated,
                files_added=files_added,
                files_deleted=files_deleted,
                changes_integrated=[],
                message=result.stdout.strip() or "Workspace synchronized",
            )

        except subprocess.TimeoutExpired:
            raise VCSSyncError("Sync operation timed out")
        except OSError as e:
            raise VCSSyncError(f"OS error during sync: {e}")

    def is_workspace_stale(self, workspace_path: Path) -> bool:
        """
        Check if workspace needs sync (underlying revisions have changed).

        Args:
            workspace_path: Path to the workspace

        Returns:
            True if sync is needed, False if up-to-date
        """
        try:
            # Check if workspace needs update
            result = subprocess.run(
                ["jj", "workspace", "update-stale", "--dry-run"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(workspace_path),
            )

            # If there's output about updating, it's stale
            if result.returncode == 0:
                return "Nothing to do" not in result.stdout

            # Also check via status
            status_result = subprocess.run(
                ["jj", "status"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=str(workspace_path),
            )

            return "stale" in status_result.stdout.lower()

        except (subprocess.TimeoutExpired, OSError):
            return False

    # =========================================================================
    # Conflict Operations
    # =========================================================================

    def detect_conflicts(self, workspace_path: Path) -> list[ConflictInfo]:
        """
        Detect conflicts in a workspace.

        In jj, conflicts are stored in commits rather than blocking operations.
        This method parses `jj status` to find conflicted files.

        Args:
            workspace_path: Path to the workspace

        Returns:
            List of ConflictInfo for all conflicted files
        """
        try:
            result = subprocess.run(
                ["jj", "status"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(workspace_path),
            )

            if result.returncode != 0:
                return []

            conflicts = []
            # Parse jj status output
            # Conflicted files show as "C path/to/file"
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line.startswith("C "):
                    file_path = Path(line[2:].strip())
                    conflicts.append(
                        ConflictInfo(
                            file_path=file_path,
                            conflict_type=ConflictType.CONTENT,
                            line_ranges=None,
                            sides=2,  # Default, could be more in octopus merges
                            is_resolved=False,
                            our_content=None,
                            their_content=None,
                            base_content=None,
                        )
                    )

            # Also check the log for conflict indicator
            log_result = subprocess.run(
                ["jj", "log", "-r", "@", "--no-graph", "-T", 'if(conflict, "conflict", "") ++ "\n"'],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=str(workspace_path),
            )

            if log_result.returncode == 0 and "conflict" in log_result.stdout:
                # Current commit has conflicts
                # If we didn't find specific files, add a generic indicator
                if not conflicts:
                    conflicts.append(
                        ConflictInfo(
                            file_path=Path("."),
                            conflict_type=ConflictType.CONTENT,
                            line_ranges=None,
                            sides=2,
                            is_resolved=False,
                            our_content=None,
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
            # Check current commit for conflict marker
            result = subprocess.run(
                ["jj", "log", "-r", "@", "--no-graph", "-T", 'if(conflict, "yes", "no") ++ "\n"'],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=str(workspace_path),
            )

            if result.returncode == 0 and "yes" in result.stdout:
                return True

            # Also check status for conflicted files
            status_result = subprocess.run(
                ["jj", "status"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=str(workspace_path),
            )

            # Look for conflict indicator in status
            for line in status_result.stdout.split("\n"):
                if line.strip().startswith("C "):
                    return True

            return False

        except (subprocess.TimeoutExpired, OSError):
            return False

    # =========================================================================
    # Commit/Change Operations
    # =========================================================================

    def get_current_change(self, workspace_path: Path) -> ChangeInfo | None:
        """
        Get info about current working copy change.

        In jj, the working copy is always a commit.

        Args:
            workspace_path: Path to the workspace

        Returns:
            ChangeInfo for current working copy, None if invalid
        """
        try:
            # Use a comprehensive template
            template = (
                'change_id ++ "|" ++ '
                'commit_id ++ "|" ++ '
                'description.first_line() ++ "|" ++ '
                'author.name() ++ "|" ++ '
                'author.email() ++ "|" ++ '
                'author.timestamp().format("%Y-%m-%dT%H:%M:%S%:z") ++ "|" ++ '
                'parents.map(|p| p.commit_id()).join(",") ++ "|" ++ '
                'if(conflict, "conflict", "") ++ "|" ++ '
                'if(empty, "empty", "") ++ "|" ++ '
                'description ++ "\n"'
            )

            result = subprocess.run(
                ["jj", "log", "-r", "@", "--no-graph", "-T", template],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(workspace_path),
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
            revision_range: jj revset expression (e.g., "::@", "main..@")
            limit: Maximum number to return

        Returns:
            List of ChangeInfo
        """
        try:
            template = (
                'change_id ++ "|" ++ '
                'commit_id ++ "|" ++ '
                'description.first_line() ++ "|" ++ '
                'author.name() ++ "|" ++ '
                'author.email() ++ "|" ++ '
                'author.timestamp().format("%Y-%m-%dT%H:%M:%S%:z") ++ "|" ++ '
                'parents.map(|p| p.commit_id()).join(",") ++ "|" ++ '
                'if(conflict, "conflict", "") ++ "|" ++ '
                'if(empty, "empty", "") ++ "\n"'
            )

            cmd = ["jj", "log", "--no-graph", "-T", template]

            if revision_range:
                cmd.extend(["-r", revision_range])
            else:
                cmd.extend(["-r", "::@"])

            if limit:
                cmd.extend(["--limit", str(limit)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                cwd=str(repo_path),
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
        Set the commit message for the current change.

        In jj, the working copy is always a commit. This method:
        1. Sets the description on the current change with `jj describe`
        2. Creates a new empty change on top with `jj new`

        Args:
            workspace_path: Workspace to commit in
            message: Commit message
            paths: Ignored in jj (working copy is always committed)

        Returns:
            ChangeInfo for the commit that was described
        """
        try:
            # First, describe the current change
            describe_result = subprocess.run(
                ["jj", "describe", "-m", message],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(workspace_path),
            )

            if describe_result.returncode != 0:
                return None

            # Get info about the described commit before creating new
            change = self.get_current_change(workspace_path)

            # Create a new empty change on top
            subprocess.run(
                ["jj", "new"],
                capture_output=True,
                timeout=30,
                cwd=str(workspace_path),
            )

            return change

        except (subprocess.TimeoutExpired, OSError):
            return None

    # =========================================================================
    # Repository Operations
    # =========================================================================

    def init_repo(self, path: Path, colocate: bool = True) -> bool:
        """
        Initialize a new jj repository.

        Note: In jj 0.30+, colocate is the default. All jj repos use the Git backend.

        Args:
            path: Where to initialize
            colocate: If True, create colocated repo (default behavior in jj 0.30+)

        Returns:
            True if successful, False otherwise
        """
        try:
            path.mkdir(parents=True, exist_ok=True)

            # In jj 0.30+, colocate is the default
            # Use --colocate flag explicitly for clarity
            if colocate:
                result = subprocess.run(
                    ["jj", "git", "init", "--colocate"],
                    cwd=str(path),
                    capture_output=True,
                    timeout=30,
                )
            else:
                # Non-colocated mode: .jj/ only (git backend still used)
                result = subprocess.run(
                    ["jj", "git", "init"],
                    cwd=str(path),
                    capture_output=True,
                    timeout=30,
                )

            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def is_repo(self, path: Path) -> bool:
        """
        Check if path is inside a jj repository.

        Args:
            path: Path to check

        Returns:
            True if valid jj repository
        """
        if not path.exists():
            return False

        # Check for .jj directory
        jj_dir = path / ".jj"
        if jj_dir.exists():
            return True

        # Also check if we're inside a jj repo
        try:
            result = subprocess.run(
                ["jj", "workspace", "root"],
                cwd=str(path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            return result.returncode == 0 and result.stdout.strip() != ""
        except (subprocess.TimeoutExpired, OSError):
            return False

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
                ["jj", "workspace", "root"],
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

    def _parse_sync_stats(self, output: str) -> tuple[int, int, int]:
        """Parse sync output for file statistics."""
        # jj doesn't give detailed stats in a standard format
        # Return zeros for now
        return (0, 0, 0)

    def _parse_log_line(self, line: str) -> ChangeInfo | None:
        """Parse a jj log line with full description."""
        try:
            parts = line.split("|", 9)
            if len(parts) < 9:
                return None

            change_id = parts[0]
            commit_id = parts[1]
            message = parts[2]
            author = parts[3]
            author_email = parts[4]
            timestamp_str = parts[5]
            parents_str = parts[6]
            is_conflict = parts[7] == "conflict"
            is_empty = parts[8] == "empty"
            message_full = parts[9] if len(parts) > 9 else message

            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                timestamp = datetime.now(timezone.utc)

            # Parse parents
            parents = [p for p in parents_str.split(",") if p]

            return ChangeInfo(
                change_id=change_id,
                commit_id=commit_id,
                message=message,
                message_full=message_full,
                author=author,
                author_email=author_email,
                timestamp=timestamp,
                parents=parents,
                is_merge=len(parents) > 1,
                is_conflicted=is_conflict,
                is_empty=is_empty,
            )
        except (ValueError, IndexError):
            return None

    def _parse_log_line_short(self, line: str) -> ChangeInfo | None:
        """Parse a jj log line without full description."""
        try:
            parts = line.split("|", 8)
            if len(parts) < 8:
                return None

            change_id = parts[0]
            commit_id = parts[1]
            message = parts[2]
            author = parts[3]
            author_email = parts[4]
            timestamp_str = parts[5]
            parents_str = parts[6]
            is_conflict = parts[7] == "conflict"
            is_empty = len(parts) > 8 and parts[8] == "empty"

            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                timestamp = datetime.now(timezone.utc)

            # Parse parents
            parents = [p for p in parents_str.split(",") if p]

            return ChangeInfo(
                change_id=change_id,
                commit_id=commit_id,
                message=message,
                message_full=message,
                author=author,
                author_email=author_email,
                timestamp=timestamp,
                parents=parents,
                is_merge=len(parents) > 1,
                is_conflicted=is_conflict,
                is_empty=is_empty,
            )
        except (ValueError, IndexError):
            return None


# =============================================================================
# jj-Specific Standalone Functions
# =============================================================================


def jj_get_operation_log(repo_path: Path, limit: int = 20) -> list[OperationInfo]:
    """
    Get jj operation log.

    jj has a full operation log that records every change to the repository.
    Unlike git's reflog, this includes all operations (not just ref changes)
    and supports full undo.

    Args:
        repo_path: Repository path
        limit: Maximum number of entries to return

    Returns:
        List of OperationInfo from operation log
    """
    try:
        result = subprocess.run(
            ["jj", "op", "log", "--limit", str(limit)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=str(repo_path),
        )

        if result.returncode != 0:
            return []

        operations = []
        lines = result.stdout.strip().split("\n")

        # Parse op log output
        # Format: "@  abc123def robert@host 5 seconds ago, lasted 1ms"
        #         "│  description of operation"
        current_op = None
        for line in lines:
            # Operation header line
            if re.match(r"^[@○◆●]?\s*\S+\s+\S+@", line):
                if current_op:
                    operations.append(current_op)

                # Parse the line
                parts = line.split()
                if len(parts) >= 4:
                    # Remove the graph character if present
                    start_idx = 0
                    if parts[0] in ("@", "○", "◆", "●", "│"):
                        start_idx = 1

                    op_id = parts[start_idx] if start_idx < len(parts) else ""

                    # Try to parse timestamp from "X ago" format
                    timestamp = datetime.now(timezone.utc)

                    current_op = OperationInfo(
                        operation_id=op_id,
                        timestamp=timestamp,
                        description="",
                        heads=[],
                        working_copy_commit="",
                        is_undoable=True,  # jj ops are always undoable
                        parent_operation=None,
                    )

            # Description line
            elif current_op and line.strip().startswith("│"):
                desc = line.strip().lstrip("│").strip()
                if desc:
                    current_op = OperationInfo(
                        operation_id=current_op.operation_id,
                        timestamp=current_op.timestamp,
                        description=desc,
                        heads=current_op.heads,
                        working_copy_commit=current_op.working_copy_commit,
                        is_undoable=current_op.is_undoable,
                        parent_operation=current_op.parent_operation,
                    )

        # Don't forget the last one
        if current_op:
            operations.append(current_op)

        return operations

    except (subprocess.TimeoutExpired, OSError):
        return []


def jj_undo_operation(repo_path: Path, operation_id: str | None = None) -> bool:
    """
    Undo a jj operation.

    jj has full undo capability - any operation can be undone,
    restoring the repository to its previous state.

    Args:
        repo_path: Repository path
        operation_id: Specific operation to undo to, None = undo last

    Returns:
        True if successful
    """
    try:
        cmd = ["jj", "op", "undo"]
        if operation_id:
            cmd.extend(["--what", operation_id])

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
            cwd=str(repo_path),
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def jj_get_change_by_id(repo_path: Path, change_id: str) -> ChangeInfo | None:
    """
    Look up a change by its stable Change ID.

    jj Change IDs are stable across rebases, unlike git commit SHAs.
    This makes them ideal for tracking work across operations.

    Args:
        repo_path: Repository path
        change_id: The Change ID to look up

    Returns:
        ChangeInfo for the change, None if not found
    """
    try:
        template = (
            'change_id ++ "|" ++ '
            'commit_id ++ "|" ++ '
            'description.first_line() ++ "|" ++ '
            'author.name() ++ "|" ++ '
            'author.email() ++ "|" ++ '
            'author.timestamp().format("%Y-%m-%dT%H:%M:%S%:z") ++ "|" ++ '
            'parents.map(|p| p.commit_id()).join(",") ++ "|" ++ '
            'if(conflict, "conflict", "") ++ "|" ++ '
            'if(empty, "empty", "") ++ "|" ++ '
            'description ++ "\n"'
        )

        result = subprocess.run(
            ["jj", "log", "-r", change_id, "--no-graph", "-T", template],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=str(repo_path),
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        # Parse the log line
        vcs = JujutsuVCS()
        return vcs._parse_log_line(result.stdout.strip())

    except (subprocess.TimeoutExpired, OSError):
        return None
