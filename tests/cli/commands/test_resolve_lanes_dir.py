"""Zero-mock unit tests for ``_resolve_lanes_dir`` (WP03 / #2052).

Verifies:
- Coord topology: returns the coord-worktree surface when the worktree and
  its mission dir are materialised and meta.json declares coordination_branch.
- Flat/legacy topology: returns the primary checkout surface when no
  coordination_branch is declared.

No ``unittest.mock`` — the point is that the function is testable with a
``tmp_path`` filesystem alone (pure path after coord-worktree materialisation).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.implement import _resolve_lanes_dir
from specify_cli.core.constants import KITTY_SPECS_DIR

pytestmark = pytest.mark.fast


# A Crockford base32 mid8 that ``mid8_from_slug`` will recognise as a valid
# tail when embedded in a slug (8 chars, charset [0-9A-HJKMNP-TV-Z]).
_TEST_MID8 = "01KVN754"
_COORD_BRANCH = "kitty/mission-my-mission-01KVN754"


def _write_meta(feature_dir: Path, *, coordination_branch: str | None = None) -> None:
    """Write a minimal meta.json into *feature_dir*."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "mission_slug": feature_dir.name,
        "mission_id": f"01KVN754TY9CVJ8G10ERT{feature_dir.name[:5].upper()}",
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


class TestResolveLinesDirCoordTopology:
    """Coord-worktree materialised: ``_resolve_lanes_dir`` must return coord dir."""

    def test_returns_coord_surface_when_worktree_and_mission_dir_exist(
        self, tmp_path: Path
    ) -> None:
        # Slug embeds the mid8 so mid8_from_slug can extract it.
        slug = f"my-mission-{_TEST_MID8}"

        # Primary checkout: meta.json declares coordination_branch.
        primary_dir = tmp_path / KITTY_SPECS_DIR / slug
        _write_meta(primary_dir, coordination_branch=_COORD_BRANCH)

        # Coord worktree: mission dir exists (no meta.json — that's on primary).
        coord_worktree_root = tmp_path / ".worktrees" / f"{slug}-coord"
        coord_mission_dir = coord_worktree_root / KITTY_SPECS_DIR / slug
        coord_mission_dir.mkdir(parents=True)

        result = _resolve_lanes_dir(tmp_path, slug)

        assert result == coord_mission_dir

    def test_coord_dir_is_distinct_from_primary_dir(self, tmp_path: Path) -> None:
        slug = f"my-mission-{_TEST_MID8}"

        primary_dir = tmp_path / KITTY_SPECS_DIR / slug
        _write_meta(primary_dir, coordination_branch=_COORD_BRANCH)

        coord_mission_dir = (
            tmp_path / ".worktrees" / f"{slug}-coord" / KITTY_SPECS_DIR / slug
        )
        coord_mission_dir.mkdir(parents=True)

        result = _resolve_lanes_dir(tmp_path, slug)

        assert result != primary_dir


class TestResolveLinesDirFlatTopology:
    """No coord worktree: ``_resolve_lanes_dir`` must return the primary dir."""

    def test_returns_primary_when_no_coordination_branch(
        self, tmp_path: Path
    ) -> None:
        # Flat slug — no mid8 tail; no coord worktree created.
        slug = "my-mission-flat"

        primary_dir = tmp_path / KITTY_SPECS_DIR / slug
        _write_meta(primary_dir)  # no coordination_branch

        result = _resolve_lanes_dir(tmp_path, slug)

        assert result == primary_dir

    def test_returns_primary_when_meta_omits_coordination_branch(
        self, tmp_path: Path
    ) -> None:
        """Explicit check that a meta without coordination_branch → primary."""
        slug = "legacy-mission"

        primary_dir = tmp_path / KITTY_SPECS_DIR / slug
        _write_meta(primary_dir, coordination_branch=None)

        result = _resolve_lanes_dir(tmp_path, slug)

        assert result == primary_dir
