"""Architectural ratchet: no ``.worktrees/`` paths may appear in the git index.

FR-005 / Issue #1887: coordination-worktree artefacts (``.worktrees/<slug>/…``)
were accidentally staged from the primary repo root and committed to
``origin/main``, leaking 26 internal paths. This ratchet ensures the index
stays clean after WP10 removes the already-tracked paths.

WP10 has landed: the 48 tracked ``.worktrees/`` paths have been removed via
``git rm -r --cached .worktrees/``. This ratchet is now a hard-failing guard.
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]


def test_no_worktrees_paths_in_git_index() -> None:
    """No .worktrees/ paths may appear in the git index (``git ls-files``)."""
    result = subprocess.run(
        ["git", "ls-files", ".worktrees/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"git ls-files exited with {result.returncode}: {result.stderr.strip()}"
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert lines == [], (
        f"Found {len(lines)} .worktrees/ path(s) in git index. "
        "Run: git rm -r --cached .worktrees/\n"
        f"Paths: {lines[:5]!r}{'...' if len(lines) > 5 else ''}"
    )
