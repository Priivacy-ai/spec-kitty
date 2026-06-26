"""Zero-mock unit tests for ``_resolve_lanes_dir`` (WP03 / #2052, updated #2115).

``lanes.json`` is a ``LANE_STATE`` (PRIMARY-partition) artifact: post-#2090 it
lives with finalized tasks on the primary ``target_branch`` for EVERY topology,
not the coordination worktree (#2090 / #2115 — the #2052 coord-read contract is
superseded). So ``_resolve_lanes_dir`` resolves the PRIMARY surface regardless of
whether a coordination worktree is materialised; STATUS reads (the event log) are
what stay on coord.

Verifies:
- Coord topology: returns the PRIMARY surface even when the coord worktree and
  its mission dir are materialised and meta.json declares coordination_branch.
- Flat/legacy topology: returns the primary checkout surface when no
  coordination_branch is declared.

No ``unittest.mock`` — the function is testable with a ``tmp_path`` filesystem
alone (pure path resolution).
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
    """Coord-worktree materialised: ``_resolve_lanes_dir`` returns the PRIMARY dir.

    lanes.json is PRIMARY-partition (#2090/#2115), so even under coord topology
    with a live coord worktree it resolves to the primary surface — never the
    coord worktree (which carries only STATUS artifacts).
    """

    def test_returns_primary_surface_under_coord_topology(
        self, tmp_path: Path
    ) -> None:
        # Slug embeds the mid8 so mid8_from_slug can extract it.
        slug = f"my-mission-{_TEST_MID8}"

        # Primary checkout: meta.json declares coordination_branch.
        primary_dir = tmp_path / KITTY_SPECS_DIR / slug
        _write_meta(primary_dir, coordination_branch=_COORD_BRANCH)

        # Coord worktree materialised (mission dir exists; no meta.json there).
        coord_mission_dir = (
            tmp_path / ".worktrees" / f"{slug}-coord" / KITTY_SPECS_DIR / slug
        )
        coord_mission_dir.mkdir(parents=True)

        result = _resolve_lanes_dir(tmp_path, slug)

        # PRIMARY surface, NOT the coord worktree (lanes.json is LANE_STATE).
        assert result == primary_dir

    def test_does_not_resolve_to_coord_dir(self, tmp_path: Path) -> None:
        slug = f"my-mission-{_TEST_MID8}"

        primary_dir = tmp_path / KITTY_SPECS_DIR / slug
        _write_meta(primary_dir, coordination_branch=_COORD_BRANCH)

        coord_mission_dir = (
            tmp_path / ".worktrees" / f"{slug}-coord" / KITTY_SPECS_DIR / slug
        )
        coord_mission_dir.mkdir(parents=True)

        result = _resolve_lanes_dir(tmp_path, slug)

        assert result == primary_dir
        assert result != coord_mission_dir


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
