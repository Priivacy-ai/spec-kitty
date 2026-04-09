"""Regression tests for planning-artifact WP lane assignment (T010, FR-101..FR-106).

These tests verify that planning-artifact WPs are first-class lane-owned entities
assigned to the canonical ``lane-planning`` lane instead of being filtered out.
"""

from __future__ import annotations

import pytest

from specify_cli.lanes.compute import PLANNING_LANE_ID, compute_lanes
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest


def _manifest(owned_files: list[str], mode: str = "code_change") -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=ExecutionMode(mode),
        owned_files=tuple(owned_files),
        authoritative_surface=owned_files[0] if owned_files else "",
    )


class TestPlanningArtifactWPsIncludedInLanes:
    """T2.1 — compute_lanes() produces lane-planning for planning-artifact WPs."""

    def test_planning_artifact_wps_are_included_in_lanes(self):
        """compute_lanes() with one code WP and one planning_artifact WP should
        produce a lane-planning lane containing the planning-artifact WP."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["kitty-specs/079-feature/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "079-test")
        lane_ids = [lane.lane_id for lane in result.lanes]
        assert PLANNING_LANE_ID in lane_ids, (
            f"Expected lane-planning in {lane_ids!r} but it was absent"
        )
        planning_lane = next(l for l in result.lanes if l.lane_id == PLANNING_LANE_ID)
        assert "WP02" in planning_lane.wp_ids

    def test_code_wp_is_in_different_lane(self):
        """Code WP should be in a non-planning lane, not in lane-planning."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["kitty-specs/079-feature/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "079-test")
        code_lane = next(l for l in result.lanes if l.lane_id != PLANNING_LANE_ID)
        assert "WP01" in code_lane.wp_ids
        # WP02 must NOT be in any code lane
        assert "WP02" not in code_lane.wp_ids


class TestPlanningLaneHasCanonicalId:
    """T2.2 — The planning-artifact lane has exactly 'lane-planning' as its lane_id."""

    def test_lane_planning_has_canonical_id(self):
        """The planning-artifact lane_id must equal PLANNING_LANE_ID exactly."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["kitty-specs/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "079-test")
        planning_lane = next(
            (l for l in result.lanes if "WP02" in l.wp_ids), None
        )
        assert planning_lane is not None, "WP02 not found in any lane"
        assert planning_lane.lane_id == "lane-planning"
        assert planning_lane.lane_id == PLANNING_LANE_ID

    def test_planning_lane_id_constant_is_lane_planning(self):
        """PLANNING_LANE_ID must be the string 'lane-planning'."""
        assert PLANNING_LANE_ID == "lane-planning"


class TestCodeWPsStillGetNormalLanes:
    """T2.6 — Code WPs still get lane-a/lane-b style assignments."""

    def test_code_wps_still_get_normal_lanes(self):
        """Code WPs must receive lane-a/lane-b style IDs, not lane-planning."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "079-test")
        for lane in result.lanes:
            assert lane.lane_id != PLANNING_LANE_ID
            assert lane.lane_id.startswith("lane-")
            assert lane.lane_id != "lane-planning"

    def test_code_wps_with_planning_wps_get_normal_lane_ids(self):
        """Code WPs mixed with planning-artifact WPs still get lane-a style IDs."""
        graph = {"WP01": [], "WP02": [], "WP03": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["kitty-specs/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "079-test")
        code_lanes = [l for l in result.lanes if l.lane_id != PLANNING_LANE_ID]
        assert len(code_lanes) == 2
        code_lane_ids = {l.lane_id for l in code_lanes}
        assert "lane-a" in code_lane_ids
        assert "lane-b" in code_lane_ids

    def test_code_lane_has_non_empty_write_scope(self):
        """Code lanes must carry their owned_files in write_scope."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["kitty-specs/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "079-test")
        code_lane = next(l for l in result.lanes if l.lane_id != PLANNING_LANE_ID)
        assert "src/a/**" in code_lane.write_scope


class TestPlanningArtifactWPsIsDerivedView:
    """T2.1 (derived view) — planning_artifact_wps is populated from lane-planning."""

    def test_planning_artifact_wps_list_is_derived_view(self):
        """LanesManifest.planning_artifact_wps matches lane-planning wp_ids."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["kitty-specs/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "079-test")
        assert result.planning_artifact_wps == ["WP02"]

    def test_planning_artifact_wps_matches_lane_planning_wp_ids(self):
        """planning_artifact_wps and lane-planning.wp_ids must agree."""
        graph = {"WP01": [], "WP02": [], "WP03": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["kitty-specs/spec1/**"], mode="planning_artifact"),
            "WP03": _manifest(["kitty-specs/spec2/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "079-test")
        planning_lane = next(l for l in result.lanes if l.lane_id == PLANNING_LANE_ID)
        assert set(result.planning_artifact_wps) == set(planning_lane.wp_ids)

    def test_planning_lane_write_scope_is_union_of_owned_files(self):
        """lane-planning.write_scope should be union of owned_files for all planning WPs."""
        graph = {"WP01": [], "WP02": [], "WP03": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["kitty-specs/spec1/**"], mode="planning_artifact"),
            "WP03": _manifest(["kitty-specs/spec2/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "079-test")
        planning_lane = next(l for l in result.lanes if l.lane_id == PLANNING_LANE_ID)
        assert "kitty-specs/spec1/**" in planning_lane.write_scope
        assert "kitty-specs/spec2/**" in planning_lane.write_scope

    def test_no_planning_lane_when_no_planning_artifact_wps(self):
        """When there are no planning-artifact WPs, no lane-planning lane is added."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "079-test")
        lane_ids = [l.lane_id for l in result.lanes]
        assert PLANNING_LANE_ID not in lane_ids
        assert result.planning_artifact_wps == []
