"""Regression test for issue #1981.

map-requirements must resolve spec.md from the primary checkout even
when a coordination worktree exists for the mission.
"""
from __future__ import annotations

from pathlib import Path

from specify_cli.missions.feature_dir_resolver import primary_feature_dir_for_mission


def test_primary_feature_dir_is_not_coord_worktree(tmp_path: Path) -> None:
    """primary_feature_dir_for_mission returns primary-checkout path, not coord path."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    mission_slug = "my-mission-01ABCDEF"

    # Simulate coord worktree existing on disk
    coord_root = repo_root / ".worktrees" / "my-mission-01ABCDEF-coord"
    coord_root.mkdir(parents=True)
    coord_spec = coord_root / "kitty-specs" / mission_slug
    coord_spec.mkdir(parents=True)

    # Call the primary resolver (topology-blind)
    result = primary_feature_dir_for_mission(repo_root, mission_slug)

    # Result must be under the primary checkout, not the coord worktree
    assert ".worktrees" not in str(result), (
        f"primary_feature_dir_for_mission returned a path under .worktrees/: {result}. "
        "map-requirements spec.md lookup will fail when the coord dir lacks spec.md."
    )
    assert str(result).startswith(str(repo_root)), (
        f"Expected path under {repo_root}, got {result}"
    )
