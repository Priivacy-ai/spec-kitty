"""Dependent-WP lane dependency regression pins.

A WP that depends on another WP must either share a lane because their write
scopes overlap, or carry an explicit lane-level dependency when their write
scopes are disjoint.

These tests pin that contract against ``compute_lanes`` so a future refactor
cannot quietly fan out a dependent WP into a parallel lane whose base does not
contain the dependency.

Negative case: every cross-lane WP dependency must be represented in
``depends_on_lanes`` so the downstream lane cannot run before its upstreams.
"""

from __future__ import annotations

import pytest

from specify_cli.lanes.compute import LaneComputationError, compute_lanes
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest


pytestmark = pytest.mark.fast


def _manifest(owned_files: list[str], mode: str = "code_change") -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=ExecutionMode(mode),
        owned_files=tuple(owned_files),
        authoritative_surface=owned_files[0] if owned_files else "",
    )


def _wp_to_lane(result) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for lane in result.lanes:
        for wp in lane.wp_ids:
            mapping[wp] = lane.lane_id
    return mapping


class TestDependentWpScheduler:
    """The planner must sequence dependent lanes without unnecessary collapse."""

    def test_simple_dependency_creates_lane_dependency(self):
        """WPa -> WPb with disjoint ownership: separate lanes, ordered by dep."""
        graph = {"WPa": [], "WPb": ["WPa"]}
        manifests = {
            "WPa": _manifest(["src/a/**"]),
            "WPb": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")

        wp_to_lane = _wp_to_lane(result)
        assert wp_to_lane["WPa"] != wp_to_lane["WPb"]
        wpb_lane = next(ln for ln in result.lanes if ln.lane_id == wp_to_lane["WPb"])
        assert wpb_lane.depends_on_lanes == (wp_to_lane["WPa"],)
        assert wpb_lane.parallel_group == 1

    def test_dependency_chain_creates_ordered_lanes(self):
        """WPa -> WPb -> WPc with disjoint ownership: depth 0, 1, 2."""
        graph = {"WPa": [], "WPb": ["WPa"], "WPc": ["WPb"]}
        manifests = {
            "WPa": _manifest(["src/a/**"]),
            "WPb": _manifest(["src/b/**"]),
            "WPc": _manifest(["src/c/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        wp_to_lane = _wp_to_lane(result)
        assert wp_to_lane["WPa"] != wp_to_lane["WPb"] != wp_to_lane["WPc"]
        by_lane = {lane.lane_id: lane for lane in result.lanes}
        assert by_lane[wp_to_lane["WPb"]].depends_on_lanes == (wp_to_lane["WPa"],)
        assert by_lane[wp_to_lane["WPc"]].depends_on_lanes == (wp_to_lane["WPb"],)
        assert by_lane[wp_to_lane["WPc"]].parallel_group == 2

    def test_independent_wps_can_fan_out(self):
        """WPa and WPb with no dep relationship and disjoint scopes → parallel."""
        graph = {"WPa": [], "WPb": []}
        manifests = {
            "WPa": _manifest(["src/a/**"]),
            "WPb": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        wp_to_lane = _wp_to_lane(result)
        # Independent WPs SHOULD land in different lanes — this guards against
        # an over-aggressive fix that serializes everything.
        assert wp_to_lane["WPa"] != wp_to_lane["WPb"], (
            "Independent WPs with disjoint owned_files must remain in parallel "
            "lanes — fixing dependent-WP placement must NOT collapse the parallel "
            "fan-out for genuinely independent work."
        )

    def test_cross_lane_dependency_edges_are_explicit(self):
        """For every cross-lane WP dependency, the lane has a dependency edge."""
        graph = {
            "WPa": [],
            "WPb": ["WPa"],
            "WPc": [],  # independent
            "WPd": ["WPc"],
        }
        manifests = {
            "WPa": _manifest(["src/a/**"]),
            "WPb": _manifest(["src/b/**"]),
            "WPc": _manifest(["src/c/**"]),
            "WPd": _manifest(["src/d/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        wp_to_lane = _wp_to_lane(result)
        lanes_by_id = {lane.lane_id: lane for lane in result.lanes}

        for wp_id, deps in graph.items():
            for dep in deps:
                if wp_to_lane[wp_id] == wp_to_lane[dep]:
                    continue
                assert wp_to_lane[dep] in lanes_by_id[wp_to_lane[wp_id]].depends_on_lanes

        # And the two independent chains should still fan out.
        assert wp_to_lane["WPa"] != wp_to_lane["WPc"], (
            "Two independent chains should land in different lanes."
        )

    def test_planner_rejects_orphan_executable_wp(self):
        """A code WP with no ownership manifest must hard-fail rather than land
        in a lane with the wrong base. This is the contract that prevents the
        original "dependent WP without source files" failure mode.
        """
        graph = {"WPa": [], "WPb": ["WPa"]}
        manifests = {"WPa": _manifest(["src/a/**"])}  # WPb missing
        with pytest.raises(LaneComputationError, match="WPb"):
            compute_lanes(graph, manifests, "test-feat")
