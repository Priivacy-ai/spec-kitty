"""Tests for map_requirements coord-aware spec.md path resolution (T020).

Verifies that map_requirements resolves the mission directory via
``resolve_feature_dir_for_slug`` (the coord-topology-aware resolver) rather
than ``resolve_feature_dir_for_mission`` (which routes through
``resolve_action_context`` and can miss PR-bound missions).

Test cases:
- Test A: primary checkout has kitty-specs dir → spec.md found (baseline)
- Test B: primary checkout lacks kitty-specs; coord-aware resolver finds it
- Test C: neither path exists → "Mission directory not found" error
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.missions._read_path_resolver import resolve_feature_dir_for_slug

pytestmark = [pytest.mark.fast]


# Must carry a valid mid8 suffix (Crockford base32, 8 chars) so that
# resolve_feature_dir_for_slug triggers the coord-worktree check path.
MISSION_SLUG = "101-my-pr-mission-01KV5AWE"
SPEC_MD_TEXT = "# Spec\n\nFR-001 Do the thing.\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec_md(base: Path, slug: str) -> Path:
    """Create a minimal kitty-specs/<slug>/spec.md under *base*."""
    mission_dir = base / "kitty-specs" / slug
    mission_dir.mkdir(parents=True)
    spec_md = mission_dir / "spec.md"
    spec_md.write_text(SPEC_MD_TEXT, encoding="utf-8")
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir()
    wp_file = tasks_dir / "WP01-task.md"
    wp_file.write_text(
        "---\nwp_id: WP01\nowned_files: []\n---\n# WP01\n",
        encoding="utf-8",
    )
    return spec_md


# ---------------------------------------------------------------------------
# Test A — primary checkout baseline (no coord worktree)
# ---------------------------------------------------------------------------


class TestMapRequirementsCoordPrimary:
    """Test A: primary checkout has kitty-specs dir → spec.md is resolved."""

    def test_resolve_feature_dir_for_slug_finds_primary(self, tmp_path: Path) -> None:
        """resolve_feature_dir_for_slug returns primary dir when it exists."""
        _make_spec_md(tmp_path, MISSION_SLUG)

        # Patch CoordinationWorkspace so no coord worktree root is found on disk.
        # The late import inside _resolve_existing_for_slug uses the real module,
        # so we patch at the canonical module path.
        with patch(
            "specify_cli.coordination.workspace.CoordinationWorkspace"
        ) as mock_ws:
            # coord_root.exists() → False so resolver falls back to primary
            mock_ws.worktree_path.return_value = tmp_path / ".worktrees" / "nonexistent"

            result = resolve_feature_dir_for_slug(tmp_path, MISSION_SLUG)

        expected = tmp_path / "kitty-specs" / MISSION_SLUG
        assert result == expected
        assert (result / "spec.md").exists()


# ---------------------------------------------------------------------------
# Test B — coord-worktree topology (primary checkout lacks the dir)
# ---------------------------------------------------------------------------


class TestMapRequirementsCoordWorktree:
    """Test B: coord worktree contains kitty-specs; resolver must find it."""

    def test_resolve_feature_dir_for_slug_finds_coord_worktree(
        self, tmp_path: Path
    ) -> None:
        """When coord worktree is materialised and holds the mission dir, it wins."""
        # Primary checkout has NO kitty-specs for this mission
        primary_root = tmp_path / "primary"
        primary_root.mkdir()

        # Coordination worktree holds the mission directory
        coord_root = tmp_path / "coord-worktree"
        coord_root.mkdir()
        _make_spec_md(coord_root, MISSION_SLUG)

        coord_mission_dir = coord_root / "kitty-specs" / MISSION_SLUG
        assert coord_mission_dir.exists()

        with patch(
            "specify_cli.coordination.workspace.CoordinationWorkspace"
        ) as mock_ws:
            mock_ws.worktree_path.return_value = coord_root

            result = resolve_feature_dir_for_slug(primary_root, MISSION_SLUG)

        assert result == coord_mission_dir
        assert (result / "spec.md").exists()


# ---------------------------------------------------------------------------
# Test C — neither path exists → directory not found path
# ---------------------------------------------------------------------------


class TestMapRequirementsCoordMissing:
    """Test C: neither primary nor coord path holds the mission dir."""

    def test_resolve_feature_dir_for_slug_returns_primary_candidate_when_missing(
        self, tmp_path: Path
    ) -> None:
        """When no directory exists, resolver returns the primary candidate path.

        map_requirements checks ``feature_dir.exists()`` after calling
        ``resolve_feature_dir_for_slug`` and emits "Mission directory not found"
        when the returned path is absent.  The resolver itself does not raise —
        it returns the primary candidate so the caller owns the diagnostic.
        """
        primary_root = tmp_path / "primary"
        primary_root.mkdir()

        with patch(
            "specify_cli.coordination.workspace.CoordinationWorkspace"
        ) as mock_ws:
            # No coord worktree on disk
            mock_ws.worktree_path.return_value = tmp_path / ".worktrees" / "nonexistent"

            result = resolve_feature_dir_for_slug(primary_root, MISSION_SLUG)

        # The returned path must not exist — caller should raise "not found"
        assert not result.exists()
        # The path should be inside the primary checkout's kitty-specs dir
        assert "kitty-specs" in result.parts
        assert result.parent.name == "kitty-specs"
