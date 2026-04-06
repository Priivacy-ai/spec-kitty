"""Tests for ownership/workspace_strategy.py.

Verifies that create_planning_workspace() returns repo_root for planning-artifact WPs
and raises ValueError for invalid inputs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.ownership.workspace_strategy import create_planning_workspace


class TestCreatePlanningWorkspace:
    def test_returns_repo_root(self, tmp_path: Path) -> None:
        """Returns repo_root directly."""
        result = create_planning_workspace(
            mission_slug="057-test",
            wp_code="WP01",
            owned_files=["kitty-specs/057-test/spec.md"],
            repo_root=tmp_path,
        )
        assert result == tmp_path

    def test_empty_owned_files(self, tmp_path: Path) -> None:
        """Works with an empty owned_files list."""
        result = create_planning_workspace(
            mission_slug="057-test",
            wp_code="WP01",
            owned_files=[],
            repo_root=tmp_path,
        )
        assert result == tmp_path

    def test_raises_for_nonexistent_repo_root(self, tmp_path: Path) -> None:
        """Raises ValueError when repo_root does not exist."""
        missing = tmp_path / "does-not-exist"
        with pytest.raises(ValueError, match="repo_root does not exist"):
            create_planning_workspace(
                mission_slug="057-test",
                wp_code="WP01",
                owned_files=[],
                repo_root=missing,
            )

    def test_does_not_create_worktree_directory(self, tmp_path: Path) -> None:
        """No additional directories are created inside repo_root."""
        before = set(tmp_path.iterdir())
        create_planning_workspace(
            mission_slug="057-test",
            wp_code="WP01",
            owned_files=[],
            repo_root=tmp_path,
        )
        after = set(tmp_path.iterdir())
        assert before == after, "create_planning_workspace must not create new directories"
