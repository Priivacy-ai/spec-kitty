"""Tests for lane computation algorithm."""

import pytest

from specify_cli.lanes.compute import (
    compute_lanes,
    find_overlap_pairs,
    infer_surfaces,
)
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest


def _manifest(owned_files: list[str], mode: str = "code_change") -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=ExecutionMode(mode),
        owned_files=tuple(owned_files),
        authoritative_surface=owned_files[0] if owned_files else "",
    )


# ---------------------------------------------------------------------------
# Rule 1: Dependencies → same lane
# ---------------------------------------------------------------------------


class TestDependenciesGrouping:
    def test_sequential_chain_single_lane(self):
        """A→B→C: all three must be in the same lane."""
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["src/c/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 1
        assert result.lanes[0].wp_ids == ("WP01", "WP02", "WP03")

    def test_diamond_dag_single_lane(self):
        """A→B, A→C, B→D, C→D: all connected by deps → single lane."""
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP01"],
            "WP04": ["WP02", "WP03"],
        }
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["src/c/**"]),
            "WP04": _manifest(["src/d/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 1
        assert set(result.lanes[0].wp_ids) == {"WP01", "WP02", "WP03", "WP04"}

    def test_two_independent_chains_two_lanes(self):
        """A→B and C→D with no overlap → two lanes."""
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": [],
            "WP04": ["WP03"],
        }
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["src/c/**"]),
            "WP04": _manifest(["src/d/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 2
        lane_wp_sets = [set(lane.wp_ids) for lane in result.lanes]
        assert {"WP01", "WP02"} in lane_wp_sets
        assert {"WP03", "WP04"} in lane_wp_sets


# ---------------------------------------------------------------------------
# Rule 2: Write-scope overlap → same lane
# ---------------------------------------------------------------------------


class TestWriteScopeGrouping:
    def test_independent_wps_with_overlap_same_lane(self):
        """A, B have no dep but overlapping files → same lane."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["src/core/utils/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 1
        assert set(result.lanes[0].wp_ids) == {"WP01", "WP02"}

    def test_independent_wps_no_overlap_separate_lanes(self):
        """A, B have no dep, no overlap → separate lanes."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["src/merge/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 2

    def test_chain_plus_overlap_merges_all(self):
        """A→B + independent C overlapping B's files → all three in one lane."""
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["src/b/utils/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 1
        assert set(result.lanes[0].wp_ids) == {"WP01", "WP02", "WP03"}


# ---------------------------------------------------------------------------
# Rule 3: Surface overlap → same lane
# ---------------------------------------------------------------------------


class TestSurfaceGrouping:
    def test_shared_surface_same_lane(self):
        """Two independent WPs mentioning 'dashboard' → same lane."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/views/**"]),
            "WP02": _manifest(["src/templates/**"]),
        }
        wp_bodies = {
            "WP01": "Implement the dashboard landing page",
            "WP02": "Create dashboard template components",
        }
        result = compute_lanes(graph, manifests, "test-feat", wp_bodies=wp_bodies)
        assert len(result.lanes) == 1

    def test_different_surfaces_separate_lanes(self):
        """Two independent WPs with different surfaces → separate lanes."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/views/**"]),
            "WP02": _manifest(["src/api/**"]),
        }
        wp_bodies = {
            "WP01": "Implement the dashboard landing page",
            "WP02": "Build the tracker integration",
        }
        result = compute_lanes(graph, manifests, "test-feat", wp_bodies=wp_bodies)
        assert len(result.lanes) == 2


# ---------------------------------------------------------------------------
# Planning artifact exclusion
# ---------------------------------------------------------------------------


class TestPlanningArtifactExclusion:
    def test_planning_artifacts_excluded(self):
        """Planning artifact WPs are not assigned to any lane."""
        graph = {"WP01": [], "WP02": [], "WP03": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["kitty-specs/docs/**"], mode="planning_artifact"),
            "WP03": _manifest(["src/merge/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        # WP02 excluded, WP01 and WP03 are independent → two lanes
        assert len(result.lanes) == 2
        all_wp_ids = set()
        for lane in result.lanes:
            all_wp_ids.update(lane.wp_ids)
        assert "WP02" not in all_wp_ids

    def test_all_planning_artifacts_empty_manifest(self):
        """All WPs are planning artifacts → empty manifest."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["kitty-specs/**"], mode="planning_artifact"),
            "WP02": _manifest(["docs/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 0


# ---------------------------------------------------------------------------
# Lane ordering and parallel groups
# ---------------------------------------------------------------------------


class TestLaneOrdering:
    def test_topo_order_within_lane(self):
        """WPs within a lane are topologically ordered."""
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["src/c/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.lanes[0].wp_ids == ("WP01", "WP02", "WP03")

    def test_parallel_groups_independent_lanes(self):
        """Independent lanes get the same parallel group (0)."""
        graph = {"WP01": [], "WP02": [], "WP03": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["src/c/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 3
        for lane in result.lanes:
            assert lane.parallel_group == 0


# ---------------------------------------------------------------------------
# Lane-level dependencies
# ---------------------------------------------------------------------------


class TestLaneLevelDependencies:
    def test_lane_deps_from_write_scope_grouping(self):
        """Lane B depends on Lane A when a WP in B depends on a WP in A
        and they ended up in different lanes (via write-scope grouping only).

        Note: with rule 1 (deps → same lane), inter-lane deps only arise
        when WPs are in the same lane due to overlap with a THIRD WP,
        creating a scenario where the dep chain crosses lanes indirectly.

        In practice with rule 1, all directly-dependent WPs are in the same
        lane, so lane-level deps are empty unless overlap grouping causes
        indirect separation. This test verifies the no-lane-deps case.
        """
        # A→B, C→D — two independent chains, no overlap
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": [],
            "WP04": ["WP03"],
        }
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["src/c/**"]),
            "WP04": _manifest(["src/d/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 2
        for lane in result.lanes:
            assert lane.depends_on_lanes == ()


# ---------------------------------------------------------------------------
# Manifest metadata
# ---------------------------------------------------------------------------


class TestManifestMetadata:
    def test_mission_branch_naming(self):
        graph = {"WP01": []}
        manifests = {"WP01": _manifest(["src/**"])}
        result = compute_lanes(graph, manifests, "057-my-feature")
        assert result.mission_branch == "kitty/mission-057-my-feature"

    def test_target_branch(self):
        graph = {"WP01": []}
        manifests = {"WP01": _manifest(["src/**"])}
        result = compute_lanes(graph, manifests, "test", target_branch="develop")
        assert result.target_branch == "develop"

    def test_version(self):
        graph = {"WP01": []}
        manifests = {"WP01": _manifest(["src/**"])}
        result = compute_lanes(graph, manifests, "test")
        assert result.version == 1

    def test_computed_from(self):
        graph = {"WP01": []}
        manifests = {"WP01": _manifest(["src/**"])}
        result = compute_lanes(graph, manifests, "test")
        assert result.computed_from == "dependency_graph+ownership"

    def test_empty_graph(self):
        result = compute_lanes({}, {}, "test")
        assert len(result.lanes) == 0
        assert result.mission_branch == "kitty/mission-test"


# ---------------------------------------------------------------------------
# find_overlap_pairs
# ---------------------------------------------------------------------------


class TestFindOverlapPairs:
    def test_overlapping_pair(self):
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["src/core/utils/**"]),
        }
        pairs = find_overlap_pairs(manifests)
        assert ("WP01", "WP02") in pairs

    def test_no_overlap(self):
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["src/merge/**"]),
        }
        pairs = find_overlap_pairs(manifests)
        assert len(pairs) == 0

    def test_multiple_overlaps_deduplicated(self):
        """Multiple overlapping globs between same pair → only one pair entry."""
        manifests = {
            "WP01": _manifest(["src/core/**", "src/core/utils/**"]),
            "WP02": _manifest(["src/core/utils/**", "src/core/models/**"]),
        }
        pairs = find_overlap_pairs(manifests)
        assert pairs.count(("WP01", "WP02")) == 1


# ---------------------------------------------------------------------------
# infer_surfaces
# ---------------------------------------------------------------------------


class TestInferSurfaces:
    def test_dashboard_keyword(self):
        assert "dashboard" in infer_surfaces("Build the dashboard page")

    def test_api_keyword(self):
        assert "api" in infer_surfaces("Create API endpoints")

    def test_legacy_cleanup_keyword(self):
        surfaces = infer_surfaces("Remove legacy fallback pages")
        assert "legacy-cleanup" in surfaces

    def test_no_match(self):
        assert infer_surfaces("Do something generic") == []

    def test_multiple_surfaces(self):
        surfaces = infer_surfaces("Build dashboard API with tracker integration")
        assert "dashboard" in surfaces
        assert "api" in surfaces
        assert "tracker-integration" in surfaces
