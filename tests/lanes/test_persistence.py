"""Tests for lanes.json persistence."""

import pytest

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import (
    CorruptLanesError,
    read_lanes_json,
    write_lanes_json,
)


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


def test_write_and_read(tmp_path):
    manifest = _make_manifest()
    path = write_lanes_json(tmp_path, manifest)
    assert path.exists()
    assert path.name == "lanes.json"

    restored = read_lanes_json(tmp_path)
    assert restored is not None
    assert restored.mission_slug == "010-feature"
    assert len(restored.lanes) == 1
    assert restored.lanes[0].wp_ids == ("WP01", "WP02")


def test_read_missing_returns_none(tmp_path):
    assert read_lanes_json(tmp_path) is None


def test_read_corrupt_raises(tmp_path):
    (tmp_path / "lanes.json").write_text("not json", encoding="utf-8")
    with pytest.raises(CorruptLanesError, match="corrupt or malformed"):
        read_lanes_json(tmp_path)


def test_read_invalid_schema_raises(tmp_path):
    (tmp_path / "lanes.json").write_text('{"foo": "bar"}', encoding="utf-8")
    with pytest.raises(CorruptLanesError, match="corrupt or malformed"):
        read_lanes_json(tmp_path)


def test_atomic_write_leaves_no_temp_on_success(tmp_path):
    manifest = _make_manifest()
    write_lanes_json(tmp_path, manifest)
    tmp_files = list(tmp_path.glob(".lanes-*.tmp"))
    assert len(tmp_files) == 0
