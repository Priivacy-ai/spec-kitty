"""Tests for lanes.json persistence."""

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import read_lanes_json, write_lanes_json


def _make_manifest() -> LanesManifest:
    return LanesManifest(
        version=1,
        feature_slug="010-feature",
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
    assert restored.feature_slug == "010-feature"
    assert len(restored.lanes) == 1
    assert restored.lanes[0].wp_ids == ("WP01", "WP02")


def test_read_missing_returns_none(tmp_path):
    assert read_lanes_json(tmp_path) is None


def test_read_corrupt_returns_none(tmp_path):
    (tmp_path / "lanes.json").write_text("not json", encoding="utf-8")
    assert read_lanes_json(tmp_path) is None


def test_read_invalid_schema_returns_none(tmp_path):
    (tmp_path / "lanes.json").write_text('{"foo": "bar"}', encoding="utf-8")
    assert read_lanes_json(tmp_path) is None
