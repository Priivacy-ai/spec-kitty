"""WP01/T005 — Dependent-WP scheduler regression pin (FR-005).

A WP that depends on another WP must land in a lane whose base contains the
dependency, OR sequentially in the same lane. The simplest correct rule is:
if WPb has any depends_on entry, place it in the lane that already holds the
latest dependency, sequentially after that dependency.

These tests pin that contract against ``compute_lanes`` so a future refactor
cannot quietly fan out a dependent WP into a parallel lane whose base does not
contain the dependency.

Negative case: every dependency edge of every WP must live in the same
ExecutionLane as that WP — no cross-lane dependency edges are tolerated for
code WPs. (Lane-planning lanes are intentionally separate; they only carry
planning-artifact WPs and never appear as dependencies of code WPs in fixtures
that use this contract.)
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
    """The planner must place WPb in the same lane as its dependency WPa."""

    def test_simple_dependency_lands_in_same_lane(self):
        """WPa -> WPb: planner must place them in the same lane in dep order.

        This is the core contract of FR-005. Dependent WPs cannot be split
        across lanes whose bases do not include each other.
        """
        graph = {"WPa": [], "WPb": ["WPa"]}
        manifests = {
            "WPa": _manifest(["src/a/**"]),
            "WPb": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")

        wp_to_lane = _wp_to_lane(result)
        assert wp_to_lane["WPa"] == wp_to_lane["WPb"], (
            f"WPb depends on WPa but landed in a different lane "
            f"({wp_to_lane['WPa']!r} vs {wp_to_lane['WPb']!r}). "
            "This regresses FR-005."
        )

        same_lane = next(ln for ln in result.lanes if ln.lane_id == wp_to_lane["WPa"])
        assert same_lane.wp_ids.index("WPa") < same_lane.wp_ids.index("WPb"), (
            "Dependency order must be preserved within the lane "
            f"(got: {same_lane.wp_ids})."
        )

    def test_dependency_chain_lands_in_one_lane(self):
        """WPa -> WPb -> WPc: a transitive chain stays in a single lane."""
        graph = {"WPa": [], "WPb": ["WPa"], "WPc": ["WPb"]}
        manifests = {
            "WPa": _manifest(["src/a/**"]),
            "WPb": _manifest(["src/b/**"]),
            "WPc": _manifest(["src/c/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        wp_to_lane = _wp_to_lane(result)
        assert wp_to_lane["WPa"] == wp_to_lane["WPb"] == wp_to_lane["WPc"]

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

    def test_no_cross_lane_dependency_edges(self):
        """For every WP, every dependency must be in the same lane.

        This is the *negative* case from the WP description: the planner must
        never place a dependent WP into a lane whose base does not contain its
        dependency. Because ``compute_lanes`` materializes lanes from a single
        target_branch, the only way to honor "lane(b)'s base contains lane(a)'s
        tip" is to put them in the same lane. We assert that invariant here.
        """
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

        for wp_id, deps in graph.items():
            for dep in deps:
                assert wp_to_lane[wp_id] == wp_to_lane[dep], (
                    f"Cross-lane dependency edge: {wp_id} (lane {wp_to_lane[wp_id]}) "
                    f"depends on {dep} (lane {wp_to_lane[dep]}). The planner must "
                    "place dependent WPs in the same lane to satisfy FR-005."
                )

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
