"""Tests for lanes.json persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import (
    LANES_FILENAME,
    CorruptLanesError,
    MissingLanesError,
    read_lanes_json,
    require_lanes_json,
    resolve_lanes_dir,
    write_lanes_json,
)

pytestmark = pytest.mark.fast


def _make_manifest() -> LanesManifest:
    return LanesManifest(
        version=1,
        mission_slug="010-feature",
        mission_id="01HTEST_ULID",
        mission_branch="kitty/mission-010-feature",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01", "WP02"),
                write_scope=("src/core/**",),
                predicted_surfaces=("api",),
                depends_on_lanes=(),
                parallel_group=0,
            ),
        ],
        computed_at="2026-04-03T12:00:00+00:00",
        computed_from="dependency_graph+ownership",
    )


def test_write_and_read(tmp_path: Path) -> None:
    manifest = _make_manifest()
    path = write_lanes_json(tmp_path, manifest)
    assert path.exists()
    assert path.name == "lanes.json"

    restored = read_lanes_json(tmp_path)
    assert restored is not None
    assert restored.mission_slug == "010-feature"
    assert len(restored.lanes) == 1
    assert restored.lanes[0].wp_ids == ("WP01", "WP02")


def test_read_missing_returns_none(tmp_path: Path) -> None:
    assert read_lanes_json(tmp_path) is None


def test_read_corrupt_raises(tmp_path: Path) -> None:
    (tmp_path / "lanes.json").write_text("not json", encoding="utf-8")
    with pytest.raises(CorruptLanesError, match="corrupt or malformed"):
        read_lanes_json(tmp_path)


def test_read_invalid_schema_raises(tmp_path: Path) -> None:
    (tmp_path / "lanes.json").write_text('{"foo": "bar"}', encoding="utf-8")
    with pytest.raises(CorruptLanesError, match="corrupt or malformed"):
        read_lanes_json(tmp_path)


def test_read_unreadable_lanes_path_raises_corrupt(tmp_path: Path) -> None:
    (tmp_path / "lanes.json").mkdir()
    with pytest.raises(CorruptLanesError, match="corrupt or malformed"):
        read_lanes_json(tmp_path)


def test_atomic_write_leaves_no_temp_on_success(tmp_path: Path) -> None:
    manifest = _make_manifest()
    write_lanes_json(tmp_path, manifest)
    tmp_files = list(tmp_path.glob(".lanes-*.tmp"))
    assert len(tmp_files) == 0


# ---------------------------------------------------------------------------
# T029 — resolve_lanes_dir seam: coord vs flat placement oracle (FR-008 / C-LANES-1)
# ---------------------------------------------------------------------------


def test_resolve_lanes_dir_returns_lanes_json_name(tmp_path: Path) -> None:
    """resolve_lanes_dir always returns a path whose name is LANES_FILENAME."""
    result = resolve_lanes_dir(tmp_path)
    assert result.name == LANES_FILENAME


def test_resolve_lanes_dir_joins_filename_under_feature_dir(tmp_path: Path) -> None:
    """resolve_lanes_dir(feature_dir) == feature_dir / 'lanes.json' — pure composition."""
    feature_dir = tmp_path / "kitty-specs" / "010-some-mission"
    feature_dir.mkdir(parents=True)
    result = resolve_lanes_dir(feature_dir)
    assert result == feature_dir / LANES_FILENAME


def test_resolve_lanes_dir_coord_path_differs_from_primary_path(tmp_path: Path) -> None:
    """C-LANES-1 / FR-008: coord feature dir and primary feature dir produce
    DISTINCT lanes-json paths — routing to the wrong surface is detectable.

    This is the unit-level placement oracle: the two paths MUST differ so the
    implement.py routing decision (``_lanes_feature_dir = _status_feature_dir``
    vs. ``= feature_dir``) is observable. A test that accepts both would be
    vacuous — this one rejects the primary path when the coord path is correct.
    """
    # Simulate a coord topology: primary in the main checkout, coord in .worktrees.
    primary_feature_dir = tmp_path / "kitty-specs" / "write-side-coord-01kv9w0x"
    coord_feature_dir = (
        tmp_path
        / ".worktrees"
        / "write-side-coord-01kv9w0x-01kv9w0x-coord"
        / "kitty-specs"
        / "write-side-coord-01kv9w0x"
    )
    primary_feature_dir.mkdir(parents=True)
    coord_feature_dir.mkdir(parents=True)

    primary_lanes = resolve_lanes_dir(primary_feature_dir)
    coord_lanes = resolve_lanes_dir(coord_feature_dir)

    # The two paths are distinct — the coord path is under .worktrees.
    assert primary_lanes != coord_lanes
    # Coord path carries .worktrees in its ancestry (it IS the coord authority).
    assert ".worktrees" in coord_lanes.parts
    # Primary path does NOT carry .worktrees (it is the flat/primary surface).
    assert ".worktrees" not in primary_lanes.parts


def test_require_lanes_json_raises_missing_on_absent_file(tmp_path: Path) -> None:
    """require_lanes_json raises MissingLanesError when no lanes.json exists.

    Regression-lock: the C-LANES-1 routing depends on require_lanes_json
    reading from the coord surface. If the coord feature dir does not carry
    lanes.json, a clear MissingLanesError is raised — never a silent fallback.
    """
    with pytest.raises(MissingLanesError, match="lanes.json is required"):
        require_lanes_json(tmp_path)
