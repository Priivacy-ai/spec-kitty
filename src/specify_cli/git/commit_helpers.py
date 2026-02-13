"""Safe commit helper that preserves staging area.

This module provides utilities for committing only specific files without
capturing unrelated staged changes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def safe_commit(
    repo_path: Path,
    files_to_commit: list[Path],
    commit_message: str,
    allow_empty: bool = False,
) -> bool:
    """Commit only specified files, preserving existing staging area.

    This function ensures that only the explicitly provided files are committed,
    preventing unrelated staged files from being accidentally included in the commit.

    Strategy:
    1. Save current staging area state (git stash)
    2. Stage only the intended files
    3. Commit those files
    4. Restore original staging area (git stash pop)

    Args:
        repo_path: Path to the git repository root
        files_to_commit: List of file paths to commit (absolute or relative to repo_path)
        commit_message: The commit message to use
        allow_empty: If True, return success even if there's nothing to commit

    Returns:
        True if commit succeeded (or nothing to commit with allow_empty=True),
        False otherwise

    Example:
        >>> from pathlib import Path
        >>> safe_commit(
        ...     repo_path=Path("."),
        ...     files_to_commit=[Path("kitty-specs/038-feature/tasks/WP01.md")],
        ...     commit_message="Update WP01 status to doing",
        ...     allow_empty=False
        ... )
        True
    """
    # Normalize file paths to be relative to repo_path
    normalized_files = []
    for file in files_to_commit:
        if file.is_absolute():
            try:
                file = file.relative_to(repo_path)
            except ValueError:
                # File is not under repo_path, use as-is
                pass
        normalized_files.append(str(file))

    # Save current staging area (only staged changes, not working tree)
    stash_result = subprocess.run(
        ["git", "stash", "push", "--staged", "--quiet"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    # Track if we stashed anything (needed for cleanup)
    stashed_something = stash_result.returncode == 0

    try:
        # Stage only the intended files
        for file_path in normalized_files:
            add_result = subprocess.run(
                ["git", "add", file_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if add_result.returncode != 0:
                # Failed to stage file
                return False

        # Commit the staged files
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        # Check for success
        if commit_result.returncode == 0:
            return True

        # Check if it was "nothing to commit" scenario
        if "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
            return allow_empty

        # Other error occurred
        return False

    finally:
        # Restore original staging area if we stashed anything
        if stashed_something:
            subprocess.run(
                ["git", "stash", "pop", "--index", "--quiet"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
