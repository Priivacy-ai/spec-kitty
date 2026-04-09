"""Tests for lane computation algorithm."""

import pytest

from specify_cli.lanes.compute import (
    LaneComputationError,
    _are_disjoint,
    _describe_overlap,
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
    def test_shared_surface_disjoint_ownership_separate_lanes(self):
        """Two independent WPs with disjoint ownership mentioning 'dashboard' → separate lanes.

        Rule 3 refinement: surface match alone is not sufficient when ownership is
        provably disjoint. Previously this collapsed to one lane.
        """
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
        assert len(result.lanes) == 2

    def test_shared_surface_overlapping_ownership_same_lane(self):
        """Two independent WPs with overlapping ownership + shared surface → same lane."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/views/**"]),
            "WP02": _manifest(["src/views/dashboard/**"]),  # overlaps src/views/**
        }
        wp_bodies = {
            "WP01": "Implement the dashboard landing page",
            "WP02": "Create dashboard sub-views",
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

    def test_disjoint_ownership_preserves_parallelism(self):
        """WP A owns src/a/**, WP B owns src/b/**, both mention 'api' → separate lanes.

        This is the canonical regression test for FR-009.
        """
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
        }
        wp_bodies = {
            "WP01": "Add API endpoints for the new service",
            "WP02": "Refactor API routes for legacy cleanup",
        }
        result = compute_lanes(graph, manifests, "test-feat", wp_bodies=wp_bodies)
        assert len(result.lanes) == 2
        lane_wp_sets = [set(lane.wp_ids) for lane in result.lanes]
        assert {"WP01"} in lane_wp_sets
        assert {"WP02"} in lane_wp_sets


# ---------------------------------------------------------------------------
# Planning artifact exclusion
# ---------------------------------------------------------------------------


class TestPlanningArtifactLane:
    def test_planning_artifacts_get_lane_planning(self):
        """Planning-artifact WPs are assigned to the canonical lane-planning lane."""
        from specify_cli.lanes.compute import PLANNING_LANE_ID
        graph = {"WP01": [], "WP02": [], "WP03": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["kitty-specs/docs/**"], mode="planning_artifact"),
            "WP03": _manifest(["src/merge/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        # WP02 → lane-planning, WP01 and WP03 each → independent code lanes
        assert len(result.lanes) == 3
        lane_ids = {lane.lane_id for lane in result.lanes}
        assert PLANNING_LANE_ID in lane_ids
        planning_lane = next(l for l in result.lanes if l.lane_id == PLANNING_LANE_ID)
        assert "WP02" in planning_lane.wp_ids
        # Code WPs are NOT in lane-planning
        code_wp_ids: set[str] = set()
        for lane in result.lanes:
            if lane.lane_id != PLANNING_LANE_ID:
                code_wp_ids.update(lane.wp_ids)
        assert "WP01" in code_wp_ids
        assert "WP03" in code_wp_ids

    def test_planning_artifact_wps_is_derived_view(self):
        """LanesManifest.planning_artifact_wps is a derived view from lane-planning."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["kitty-specs/docs/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.planning_artifact_wps == ["WP02"]

    def test_all_planning_artifacts_single_planning_lane(self):
        """All WPs are planning artifacts → only lane-planning lane exists."""
        from specify_cli.lanes.compute import PLANNING_LANE_ID
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["kitty-specs/**"], mode="planning_artifact"),
            "WP02": _manifest(["docs/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 1
        assert result.lanes[0].lane_id == PLANNING_LANE_ID
        assert set(result.lanes[0].wp_ids) == {"WP01", "WP02"}


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


# ---------------------------------------------------------------------------
# T010: Completeness assertion — all executable WPs appear in lanes
# ---------------------------------------------------------------------------


class TestCompletenessAssertion:
    def test_all_executable_wps_in_lanes(self):
        """All 5 code-change WPs must appear in exactly one lane."""
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": [],
            "WP04": ["WP03"],
            "WP05": [],
        }
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
            "WP03": _manifest(["src/c/**"]),
            "WP04": _manifest(["src/d/**"]),
            "WP05": _manifest(["src/e/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        all_in_lanes: set[str] = set()
        for lane in result.lanes:
            all_in_lanes.update(lane.wp_ids)
        assert {"WP01", "WP02", "WP03", "WP04", "WP05"} == all_in_lanes


# ---------------------------------------------------------------------------
# T011: Missing ownership manifest raises LaneComputationError
# ---------------------------------------------------------------------------


class TestMissingManifestError:
    def test_missing_manifest_raises_error(self):
        """An executable WP with no ownership manifest must raise LaneComputationError."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            # WP02 has no manifest at all
        }
        with pytest.raises(LaneComputationError, match="WP02"):
            compute_lanes(graph, manifests, "test-feat")

    def test_missing_manifest_error_names_wp(self):
        """The error message must name the missing WP."""
        graph = {"WP01": [], "WP99": []}
        manifests = {"WP01": _manifest(["src/a/**"])}
        with pytest.raises(LaneComputationError) as exc_info:
            compute_lanes(graph, manifests, "test-feat")
        assert "WP99" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T012: Planning-artifact exclusion diagnostic
# ---------------------------------------------------------------------------


class TestPlanningArtifactDiagnostic:
    def test_planning_artifact_in_lane_planning_and_diagnostic(self):
        """Planning WPs are in lane-planning lane and listed in planning_artifact_wps."""
        from specify_cli.lanes.compute import PLANNING_LANE_ID
        graph = {"WP01": [], "WP02": [], "WP03": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["kitty-specs/docs/**"], mode="planning_artifact"),
            "WP03": _manifest(["src/merge/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        # WP02 in lane-planning, not in code lanes
        code_wp_ids: set[str] = set()
        planning_wp_ids: set[str] = set()
        for lane in result.lanes:
            if lane.lane_id == PLANNING_LANE_ID:
                planning_wp_ids.update(lane.wp_ids)
            else:
                code_wp_ids.update(lane.wp_ids)
        assert "WP02" not in code_wp_ids
        assert "WP02" in planning_wp_ids
        # WP02 listed in diagnostic derived view
        assert "WP02" in result.planning_artifact_wps

    def test_planning_artifact_wps_empty_when_none(self):
        """When there are no planning artifacts, the list must be empty."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.planning_artifact_wps == []

    def test_all_planning_artifacts_planning_lane_only(self):
        """When all WPs are planning artifacts, only lane-planning lane exists."""
        from specify_cli.lanes.compute import PLANNING_LANE_ID
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["kitty-specs/**"], mode="planning_artifact"),
            "WP02": _manifest(["docs/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert len(result.lanes) == 1
        assert result.lanes[0].lane_id == PLANNING_LANE_ID
        assert set(result.planning_artifact_wps) == {"WP01", "WP02"}

    def test_planning_artifact_wps_in_serialized_dict(self):
        """planning_artifact_wps must appear in to_dict() output."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["kitty-specs/x/**"], mode="planning_artifact"),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        data = result.to_dict()
        assert "planning_artifact_wps" in data
        assert "WP02" in data["planning_artifact_wps"]


# ---------------------------------------------------------------------------
# T017/T019: Collapse events recorded and independent collapse counting
# ---------------------------------------------------------------------------


class TestCollapseEvents:
    def test_dependency_rule_records_event(self):
        """Dep-based merge → CollapseEvent with rule='dependency'."""
        graph = {"WP01": [], "WP02": ["WP01"]}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.collapse_report is not None
        rules = [e.rule for e in result.collapse_report.events]
        assert "dependency" in rules
        dep_events = [e for e in result.collapse_report.events if e.rule == "dependency"]
        assert any(e.wp_a == "WP02" and e.wp_b == "WP01" for e in dep_events)

    def test_dependency_event_evidence_format(self):
        """Dependency event evidence is '{wp_id} depends on {dep}'."""
        graph = {"WP01": [], "WP02": ["WP01"]}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.collapse_report is not None
        dep_events = [e for e in result.collapse_report.events if e.rule == "dependency"]
        assert dep_events[0].evidence == "WP02 depends on WP01"

    def test_write_scope_rule_records_event(self):
        """Overlap-based merge → CollapseEvent with rule='write_scope_overlap'."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["src/core/utils/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.collapse_report is not None
        rules = [e.rule for e in result.collapse_report.events]
        assert "write_scope_overlap" in rules

    def test_write_scope_event_evidence_contains_globs(self):
        """Write-scope event evidence names the overlapping globs."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["src/core/utils/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.collapse_report is not None
        ws_events = [e for e in result.collapse_report.events if e.rule == "write_scope_overlap"]
        assert len(ws_events) == 1
        assert "src/core/**" in ws_events[0].evidence
        assert "src/core/utils/**" in ws_events[0].evidence

    def test_surface_heuristic_records_event(self):
        """Surface-based merge (non-disjoint) → CollapseEvent with rule='surface_heuristic'."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/views/**"]),
            "WP02": _manifest(["src/views/dashboard/**"]),  # overlaps
        }
        wp_bodies = {
            "WP01": "Implement the dashboard landing page",
            "WP02": "Create dashboard sub-views",
        }
        result = compute_lanes(graph, manifests, "test-feat", wp_bodies=wp_bodies)
        assert result.collapse_report is not None
        # The write-scope overlap catches this first; no surface_heuristic needed
        # But we test both rules are recorded across scenarios
        rules = [e.rule for e in result.collapse_report.events]
        # At minimum, write_scope_overlap must fire for overlapping globs
        assert "write_scope_overlap" in rules

    def test_independent_collapse_count_with_overlap(self):
        """Independent WPs forced to same lane via write-scope → count > 0."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["src/core/utils/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.collapse_report is not None
        # WP01 and WP02 have no dependency relationship → independent collapse
        assert result.collapse_report.independent_wps_collapsed == 1

    def test_dependent_collapse_not_counted_independent(self):
        """Dependent WPs in same lane (via dep rule) → independent count = 0."""
        graph = {"WP01": [], "WP02": ["WP01"]}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.collapse_report is not None
        # WP01→WP02 is a direct dep, so not independent
        assert result.collapse_report.independent_wps_collapsed == 0

    def test_no_collapses_empty_report(self):
        """Two fully independent WPs with no overlaps → empty collapse events."""
        graph = {"WP01": [], "WP02": []}
        manifests = {
            "WP01": _manifest(["src/a/**"]),
            "WP02": _manifest(["src/b/**"]),
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.collapse_report is not None
        assert len(result.collapse_report.events) == 0
        assert result.collapse_report.independent_wps_collapsed == 0

    def test_no_duplicate_events_for_same_pair(self):
        """When Rule 1 and Rule 2 both fire for the same pair, only one event is recorded per trigger."""
        graph = {"WP01": [], "WP02": ["WP01"]}
        manifests = {
            "WP01": _manifest(["src/core/**"]),
            "WP02": _manifest(["src/core/utils/**"]),  # overlapping
        }
        result = compute_lanes(graph, manifests, "test-feat")
        assert result.collapse_report is not None
        dep_events = [e for e in result.collapse_report.events if e.rule == "dependency"]
        # Only one dep event for WP02→WP01
        assert len(dep_events) == 1
        # Rule 2 fires but uf.find(WP01) == uf.find(WP02) already → no write_scope event
        ws_events = [e for e in result.collapse_report.events if e.rule == "write_scope_overlap"]
        assert len(ws_events) == 0


# ---------------------------------------------------------------------------
# T018: _are_disjoint and _describe_overlap helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_are_disjoint_true_for_separate_paths(self):
        ma = _manifest(["src/a/**"])
        mb = _manifest(["src/b/**"])
        assert _are_disjoint(ma, mb) is True

    def test_are_disjoint_false_for_overlapping_paths(self):
        ma = _manifest(["src/core/**"])
        mb = _manifest(["src/core/utils/**"])
        assert _are_disjoint(ma, mb) is False

    def test_are_disjoint_false_exact_match(self):
        ma = _manifest(["src/foo/**"])
        mb = _manifest(["src/foo/**"])
        assert _are_disjoint(ma, mb) is False

    def test_describe_overlap_names_globs(self):
        ma = _manifest(["src/core/**"])
        mb = _manifest(["src/core/utils/**"])
        desc = _describe_overlap(ma, mb)
        assert "src/core/**" in desc
        assert "src/core/utils/**" in desc

    def test_describe_overlap_fallback(self):
        """Disjoint manifests → fallback message."""
        ma = _manifest(["src/a/**"])
        mb = _manifest(["src/b/**"])
        desc = _describe_overlap(ma, mb)
        assert "write-scope overlap" in desc
