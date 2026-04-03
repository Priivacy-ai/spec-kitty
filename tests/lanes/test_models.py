"""Tests for ExecutionLane and LanesManifest models."""

from specify_cli.lanes.models import ExecutionLane, LanesManifest


def test_execution_lane_round_trip():
    lane = ExecutionLane(
        lane_id="lane-a",
        wp_ids=("WP01", "WP02"),
        write_scope=("src/core/**",),
        predicted_surfaces=("api",),
        depends_on_lanes=(),
        parallel_group=0,
    )
    data = lane.to_dict()
    restored = ExecutionLane.from_dict(data)
    assert restored == lane


def test_execution_lane_from_dict_defaults():
    data = {"lane_id": "lane-a", "wp_ids": ["WP01"]}
    lane = ExecutionLane.from_dict(data)
    assert lane.write_scope == ()
    assert lane.predicted_surfaces == ()
    assert lane.depends_on_lanes == ()
    assert lane.parallel_group == 0


def test_lanes_manifest_round_trip():
    manifest = LanesManifest(
        version=1,
        feature_slug="057-feat",
        mission_branch="kitty/mission-057-feat",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01", "WP02"),
                write_scope=("src/**",),
                predicted_surfaces=("api",),
                depends_on_lanes=(),
                parallel_group=0,
            ),
            ExecutionLane(
                lane_id="lane-b",
                wp_ids=("WP03",),
                write_scope=("tests/**",),
                predicted_surfaces=("tests",),
                depends_on_lanes=("lane-a",),
                parallel_group=1,
            ),
        ],
        computed_at="2026-04-03T12:00:00+00:00",
        computed_from="dependency_graph+ownership",
    )
    data = manifest.to_dict()
    restored = LanesManifest.from_dict(data)
    assert restored.version == manifest.version
    assert restored.feature_slug == manifest.feature_slug
    assert restored.mission_branch == manifest.mission_branch
    assert len(restored.lanes) == 2
    assert restored.lanes[0] == manifest.lanes[0]
    assert restored.lanes[1] == manifest.lanes[1]


def test_lane_for_wp():
    manifest = LanesManifest(
        version=1,
        feature_slug="test",
        mission_branch="kitty/mission-test",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01", "WP02"),
                write_scope=(),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
            ExecutionLane(
                lane_id="lane-b",
                wp_ids=("WP03",),
                write_scope=(),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
        ],
        computed_at="2026-04-03T12:00:00+00:00",
        computed_from="test",
    )
    assert manifest.lane_for_wp("WP01").lane_id == "lane-a"
    assert manifest.lane_for_wp("WP02").lane_id == "lane-a"
    assert manifest.lane_for_wp("WP03").lane_id == "lane-b"
    assert manifest.lane_for_wp("WP99") is None


def test_parallel_groups():
    manifest = LanesManifest(
        version=1,
        feature_slug="test",
        mission_branch="kitty/mission-test",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a", wp_ids=("WP01",), write_scope=(),
                predicted_surfaces=(), depends_on_lanes=(), parallel_group=0,
            ),
            ExecutionLane(
                lane_id="lane-b", wp_ids=("WP02",), write_scope=(),
                predicted_surfaces=(), depends_on_lanes=(), parallel_group=0,
            ),
            ExecutionLane(
                lane_id="lane-c", wp_ids=("WP03",), write_scope=(),
                predicted_surfaces=(), depends_on_lanes=("lane-a",), parallel_group=1,
            ),
        ],
        computed_at="2026-04-03T12:00:00+00:00",
        computed_from="test",
    )
    groups = manifest.parallel_groups()
    assert len(groups[0]) == 2
    assert len(groups[1]) == 1
