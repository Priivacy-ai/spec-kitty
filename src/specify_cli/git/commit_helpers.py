"""Safe commit helper that preserves staging area.

This module provides utilities for committing only specific files without
capturing unrelated staged changes.

It also installs a commit-layer data-loss backstop: every ``safe_commit`` call
asserts that the staging area contains exactly the paths the caller requested
before the commit is created. If any unexpected path is staged (for example, a
phantom deletion produced by a sparse-checkout filter interacting with
``git stash pop``), the commit is aborted with ``SafeCommitBackstopError``. The
backstop is unconditional and cannot be bypassed via any ``--force`` code path
--- see Priivacy-ai/spec-kitty#588 for the cascade it defends against.
"""

from __future__ import annotations

import subprocess
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UnexpectedStagedPath:
    """A path that appeared in the staging area but was not on the caller's expected list."""

    path: str  # Path as reported by git porcelain (POSIX separators)
    status_code: str  # First two characters of git status --porcelain (e.g. "D ", "M ", "A ")


class SafeCommitBackstopError(RuntimeError):
    """Raised by safe_commit when staged paths do not match files_to_commit.

    The backstop fires BEFORE the commit is created, so the commit does not exist.
    Callers should treat this as a data-loss-prevention signal and abort.
    """

    def __init__(
        self,
        unexpected: tuple[UnexpectedStagedPath, ...],
        requested: tuple[str, ...],
    ) -> None:
        self.unexpected = unexpected
        self.requested = requested
        message_lines = [
            "Commit aborted: staging area contains unexpected paths.",
            "",
            "Requested paths (what safe_commit was told to commit):",
        ]
        for p in requested:
            message_lines.append(f"  {p}")
        message_lines.append("")
        message_lines.append("Unexpected paths staged (would have been committed):")
        for p in unexpected:
            message_lines.append(f"  {p.status_code} {p.path}")
        message_lines.append("")
        message_lines.append("This usually means the working tree is behind HEAD.")
        message_lines.append("Investigate before committing:")
        message_lines.append("  git diff --cached")
        message_lines.append("  git status")
        message_lines.append("  git checkout HEAD -- <unexpected-paths>")
        message_lines.append("")
        message_lines.append("The backstop cannot be bypassed by --force.")
        super().__init__("\n".join(message_lines))


def assert_staging_area_matches_expected(
    repo_path: Path,
    expected_paths: Sequence[str],
) -> None:
    """Compare staged paths to ``expected_paths``; raise on mismatch.

    Reads ``git diff --cached --name-status`` at ``repo_path`` and collects all
    currently-staged paths. Any path that is staged but not in
    ``expected_paths`` is a backstop violation and will raise
    ``SafeCommitBackstopError``.

    This function is pure (aside from the ``git`` subprocess probe) --- it does
    not mutate the staging area. It returns ``None`` on success.

    Args:
        repo_path: The repository the stage applies to (worktree root).
        expected_paths: The paths safe_commit was asked to commit, normalized
            to POSIX separators for the compare.

    Raises:
        SafeCommitBackstopError: When any staged path is not in
            ``expected_paths``, or when the ``git diff --cached`` probe fails.
    """
    # git diff --cached --name-status outputs one line per staged path:
    #   "D\tdocs/runbooks/file.md"
    #   "M\tscripts/agents/AGENTS.md"
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        # Staging-area probe failed. Raise to abort the commit; caller handles.
        raise SafeCommitBackstopError(
            unexpected=(UnexpectedStagedPath(path="<probe-failed>", status_code="??"),),
            requested=tuple(expected_paths),
        )

    expected_set = {str(p).replace("\\", "/") for p in expected_paths}
    unexpected: list[UnexpectedStagedPath] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status_code, staged_path = parts
        normalized = staged_path.replace("\\", "/")
        if normalized not in expected_set:
            unexpected.append(
                UnexpectedStagedPath(path=normalized, status_code=f"{status_code} "),
            )

    if unexpected:
        raise SafeCommitBackstopError(
            unexpected=tuple(unexpected),
            requested=tuple(expected_set),
        )


def _stage_requested_files(repo_path: Path, normalized_files: list[str]) -> bool:
    """Stage each requested file via ``git add --force``. Returns False on failure."""
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
            return False
    return True


def _run_commit(repo_path: Path, commit_message: str, allow_empty: bool) -> bool:
    """Run ``git commit`` and classify its result."""
    commit_result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", commit_message],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if commit_result.returncode == 0:
        return True
    if "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
        return allow_empty
    return False


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
    3. Assert the staging area contains only the intended files (backstop)
    4. Commit those files
    5. Restore original staging area (git stash pop)

    Step 3 is the commit-layer data-loss backstop: if ``git stash pop`` or any
    other git operation smuggles unexpected paths (e.g. sparse-checkout phantom
    deletions) into the staging area between steps 2 and 4, the commit is
    aborted with ``SafeCommitBackstopError``. The backstop is unconditional ---
    it cannot be disabled by any ``--force`` path.

    Args:
        repo_path: Path to the git repository root
        files_to_commit: List of file paths to commit (absolute or relative to repo_path)
        commit_message: The commit message to use
        allow_empty: If True, return success even if there's nothing to commit

    Returns:
        True if commit succeeded (or nothing to commit with allow_empty=True),
        False otherwise

    Raises:
        SafeCommitBackstopError: If the staging area contains paths outside of
            ``files_to_commit`` at commit time (data-loss prevention). The
            prior-staging-area cleanup still runs before the error propagates.

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
    backstop_error: SafeCommitBackstopError | None = None

    try:
        # Stage only the intended files
        if not _stage_requested_files(repo_path, normalized_files):
            commit_success = False
        else:
            # Backstop: assert the staging area now contains ONLY the
            # caller's requested paths before we commit. This catches
            # phantom-deletion cascades (see Priivacy-ai/spec-kitty#588).
            # The assertion is unconditional --- no bypass exists.
            try:
                assert_staging_area_matches_expected(repo_path, normalized_files)
            except SafeCommitBackstopError as exc:
                # Capture and re-raise AFTER the finally block runs the
                # stash-pop cleanup so the caller's original staging area is
                # restored before the exception propagates.
                backstop_error = exc
                commit_success = False
            else:
                commit_success = _run_commit(repo_path, commit_message, allow_empty)

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

    # Propagate backstop error AFTER stash cleanup has run.
    if backstop_error is not None:
        raise backstop_error

    return commit_success
