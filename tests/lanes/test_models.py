"""Tests for ExecutionLane and LanesManifest models."""

import pytest

from specify_cli.lanes.models import CollapseEvent, CollapseReport, ExecutionLane, LanesManifest

pytestmark = pytest.mark.fast


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
        mission_slug="057-feat",
        mission_id="01HXYZ_ULID",
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
    assert restored.mission_slug == manifest.mission_slug
    assert restored.mission_id == "01HXYZ_ULID"
    assert restored.mission_branch == manifest.mission_branch
    assert len(restored.lanes) == 2
    assert restored.lanes[0] == manifest.lanes[0]
    assert restored.lanes[1] == manifest.lanes[1]


def test_lanes_manifest_from_dict_missing_mission_id_falls_back():
    """If lanes.json was written before mission_id was added, fall back to mission_slug."""
    data = {
        "version": 1,
        "mission_slug": "old-feature",
        "mission_branch": "kitty/mission-old-feature",
        "target_branch": "main",
        "lanes": [],
        "computed_at": "2026-04-03T12:00:00+00:00",
        "computed_from": "test",
    }
    manifest = LanesManifest.from_dict(data)
    assert manifest.mission_id == "old-feature"


def test_lane_for_wp():
    manifest = LanesManifest(
        version=1,
        mission_slug="test",
        mission_id="test",
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
        mission_slug="test",
        mission_id="test",
        mission_branch="kitty/mission-test",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01",),
                write_scope=(),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
            ExecutionLane(
                lane_id="lane-b",
                wp_ids=("WP02",),
                write_scope=(),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
            ExecutionLane(
                lane_id="lane-c",
                wp_ids=("WP03",),
                write_scope=(),
                predicted_surfaces=(),
                depends_on_lanes=("lane-a",),
                parallel_group=1,
            ),
        ],
        computed_at="2026-04-03T12:00:00+00:00",
        computed_from="test",
    )
    groups = manifest.parallel_groups()
    assert len(groups[0]) == 2
    assert len(groups[1]) == 1


def test_lanes_manifest_with_collapse_report_round_trip():
    """LanesManifest with a CollapseReport serializes and deserializes correctly."""
    report = CollapseReport(
        events=[
            CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="WP01 depends on WP02"),
            CollapseEvent(wp_a="WP03", wp_b="WP04", rule="write_scope_overlap", evidence="overlapping globs: 'src/**' vs 'src/sub/**'"),
        ],
        independent_wps_collapsed=1,
    )
    manifest = LanesManifest(
        version=1,
        mission_slug="test-feat",
        mission_id="test-feat",
        mission_branch="kitty/mission-test-feat",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01", "WP02"),
                write_scope=("src/**",),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
        ],
        computed_at="2026-04-06T12:00:00+00:00",
        computed_from="dependency_graph+ownership",
        collapse_report=report,
    )
    data = manifest.to_dict()
    # collapse_report should be present (has events)
    assert "collapse_report" in data
    assert data["collapse_report"]["total_merges"] == 2
    assert data["collapse_report"]["independent_wps_collapsed"] == 1
    assert data["collapse_report"]["by_rule"]["dependency"] == 1
    assert data["collapse_report"]["by_rule"]["write_scope_overlap"] == 1

    restored = LanesManifest.from_dict(data)
    assert restored.collapse_report is not None
    assert len(restored.collapse_report.events) == 2
    assert restored.collapse_report.independent_wps_collapsed == 1
    assert restored.collapse_report.events[0].wp_a == "WP01"
    assert restored.collapse_report.events[0].rule == "dependency"
    assert restored.collapse_report.events[1].rule == "write_scope_overlap"


def test_lanes_manifest_empty_collapse_report_not_in_dict():
    """LanesManifest with no collapse events does not include collapse_report in to_dict()."""
    report = CollapseReport(events=[], independent_wps_collapsed=0)
    manifest = LanesManifest(
        version=1,
        mission_slug="test-feat",
        mission_id="test-feat",
        mission_branch="kitty/mission-test-feat",
        target_branch="main",
        lanes=[],
        computed_at="2026-04-06T12:00:00+00:00",
        computed_from="test",
        collapse_report=report,
    )
    data = manifest.to_dict()
    assert "collapse_report" not in data


def test_lanes_manifest_none_collapse_report_not_in_dict():
    """LanesManifest with collapse_report=None does not include collapse_report in to_dict()."""
    manifest = LanesManifest(
        version=1,
        mission_slug="test-feat",
        mission_id="test-feat",
        mission_branch="kitty/mission-test-feat",
        target_branch="main",
        lanes=[],
        computed_at="2026-04-06T12:00:00+00:00",
        computed_from="test",
        collapse_report=None,
    )
    data = manifest.to_dict()
    assert "collapse_report" not in data
