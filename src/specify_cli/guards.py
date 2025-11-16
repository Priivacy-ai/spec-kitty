"""Shared pre-flight validation utilities for Spec Kitty CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import re
import subprocess


class GuardValidationError(Exception):
    """Raised when pre-flight validation fails."""


@dataclass
class WorktreeValidationResult:
    """Result of worktree location validation."""

    current_branch: str
    is_feature_branch: bool
    is_main_branch: bool
    worktree_path: Optional[Path]
    errors: List[str]

    @property
    def is_valid(self) -> bool:
        """Return True when validation passed."""
        if self.errors:
            return False
        if not self.current_branch:
            return True
        return self.is_feature_branch and not self.is_main_branch

    def format_error(self) -> str:
        """Format error message for display."""
        if not self.errors:
            return ""

        output = ["Location Pre-flight Check Failed:", ""]
        for error in self.errors:
            output.append(f"  {error}")

        if self.is_main_branch:
            output.extend(
                [
                    "",
                    "You are on the 'main' branch. Commands must run from feature worktrees.",
                    "",
                    "Available worktrees:",
                    "  $ ls .worktrees/",
                    "",
                    "Navigate to worktree:",
                    "  $ cd .worktrees/<feature-name>",
                    "",
                    "Verify branch:",
                    "  $ git branch --show-current",
                ]
            )

        return "\n".join(output)


def validate_worktree_location(project_root: Optional[Path] = None) -> WorktreeValidationResult:
    """Validate that commands run from a feature worktree."""
    project_root = Path(project_root) if project_root is not None else Path.cwd()

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GuardValidationError("git executable not found") from exc

    if result.returncode != 0:
        return WorktreeValidationResult(
            current_branch="unknown",
            is_feature_branch=False,
            is_main_branch=False,
            worktree_path=None,
            errors=["Not a git repository"],
        )

    current_branch = result.stdout.strip()
    is_main_branch = current_branch in {"main", "master"}
    is_feature_branch = bool(re.match(r"^\d{3}-[\w-]+$", current_branch))

    errors: List[str] = []
    if not current_branch:
        errors.append("Unable to determine current git branch.")
    elif is_main_branch:
        errors.append("Command must run from feature worktree, not main branch.")
    elif not is_feature_branch:
        errors.append(
            f"Unexpected branch '{current_branch}'. Commands must run from feature worktrees."
        )

    worktree_path = project_root if is_feature_branch and not errors else None

    return WorktreeValidationResult(
        current_branch=current_branch or "unknown",
        is_feature_branch=is_feature_branch,
        is_main_branch=is_main_branch,
        worktree_path=worktree_path,
        errors=errors,
    )


def validate_git_clean(project_root: Optional[Path] = None) -> WorktreeValidationResult:
    """Validate git repository has no uncommitted changes."""
    project_root = Path(project_root) if project_root is not None else Path.cwd()

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GuardValidationError("git executable not found") from exc

    errors: List[str] = []
    if result.returncode != 0:
        errors.append("Unable to read git status.")
    else:
        status_lines = [line for line in result.stdout.splitlines() if line.strip()]
        if status_lines:
            errors.append(
                f"Uncommitted changes detected ({len(status_lines)} files). "
                "Commit or stash changes before switching missions."
            )

    return WorktreeValidationResult(
        current_branch="",
        is_feature_branch=not errors,
        is_main_branch=False,
        worktree_path=None,
        errors=errors,
    )
