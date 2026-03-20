"""Safe commit helper that preserves staging area.

This module provides utilities for committing only specific files without
capturing unrelated staged changes.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path


def _find_stash_ref(repo_path: Path, stash_message: str) -> str | None:
    """Return the stash ref for a unique stash message, if present."""
    result = subprocess.run(
        ["git", "stash", "list", "--format=%gd\t%s"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        ref, message = line.split("\t", 1)
        if message == stash_message or message.endswith(f": {stash_message}"):
            return ref

    return None


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
            try:  # noqa: SIM105
                file = file.relative_to(repo_path)
            except ValueError:
                # File is not under repo_path, use as-is
                pass
        normalized_files.append(str(file))

    stash_message = f"spec-kitty-safe-commit:{uuid.uuid4()}"

    # Save current staging area (only staged changes, not working tree)
    stash_result = subprocess.run(
        ["git", "stash", "push", "--staged", "--quiet", "-m", stash_message],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    # Track whether we created a stash entry so we only restore our own stash.
    created_stash = stash_result.returncode == 0 and _find_stash_ref(repo_path, stash_message) is not None
    restore_failed = False
    commit_success = False

    try:
        # Stage only the intended files
        for file_path in normalized_files:
            add_result = subprocess.run(
                # Use --force for explicitly-requested files so ignored
                # status files can still be committed intentionally.
                ["git", "add", "--force", "--", file_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if add_result.returncode != 0:
                # Failed to stage file
                commit_success = False
                break
        else:
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
                commit_success = True
            # Check if it was "nothing to commit" scenario
            elif "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
                commit_success = allow_empty
            else:
                # Other error occurred
                commit_success = False

    finally:
        # Restore original staging area if we created a stash entry.
        if created_stash:
            stash_ref = _find_stash_ref(repo_path, stash_message)
            if stash_ref is None:
                restore_failed = True
            else:
                restore_result = subprocess.run(
                    ["git", "stash", "pop", "--index", "--quiet", stash_ref],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                if restore_result.returncode != 0:
                    restore_failed = True

        if restore_failed:
            commit_success = False

    return commit_success
