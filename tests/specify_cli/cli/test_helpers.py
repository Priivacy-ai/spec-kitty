"""Integration tests for specify_cli.cli.helpers — T007.

Verifies that get_project_root_or_exit correctly resolves the main repo root
when called from a git worktree, exercising the real delegation chain through
the project_resolver shim → paths.locate_project_root (no mocking of the
resolver).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.helpers import get_project_root_or_exit

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_get_project_root_or_exit_succeeds_in_worktree(tmp_path: Path) -> None:
    """get_project_root_or_exit returns main repo root when called from a git worktree."""
    main_repo = tmp_path / "main_repo"
    (main_repo / ".kittify").mkdir(parents=True)
    worktrees_dir = main_repo / ".git" / "worktrees" / "test_lane"
    worktrees_dir.mkdir(parents=True)

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {worktrees_dir}\n")

    result = get_project_root_or_exit(start=worktree)
    assert result == main_repo
