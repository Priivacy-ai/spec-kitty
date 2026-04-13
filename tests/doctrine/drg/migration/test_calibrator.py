"""Tests for doctrine.drg.migration.calibrator."""

from __future__ import annotations

from doctrine.drg.migration.calibrator import calibrate_surfaces, measure_surface
from doctrine.drg.models import DRGEdge, DRGNode, NodeKind, Relation


def _make_action_node(action: str) -> DRGNode:
    return DRGNode(
        urn=f"action:software-dev/{action}",
        kind=NodeKind.ACTION,
        label=action,
    )


def _make_directive_node(num: int) -> DRGNode:
    return DRGNode(
        urn=f"directive:DIRECTIVE_{num:03d}",
        kind=NodeKind.DIRECTIVE,
    )


def _make_tactic_node(name: str) -> DRGNode:
    return DRGNode(
        urn=f"tactic:{name}",
        kind=NodeKind.TACTIC,
    )


def _scope_edge(action: str, target_urn: str) -> DRGEdge:
    return DRGEdge(
        source=f"action:software-dev/{action}",
        target=target_urn,
        relation=Relation.SCOPE,
    )


# ---------------------------------------------------------------------------
# measure_surface
# ---------------------------------------------------------------------------


class TestMeasureSurface:
    def test_counts_scope_edges(self) -> None:
        edges = [
            _scope_edge("implement", "directive:DIRECTIVE_001"),
            _scope_edge("implement", "tactic:tdd"),
            _scope_edge("review", "directive:DIRECTIVE_001"),
        ]
        assert measure_surface("action:software-dev/implement", edges) == 2
        assert measure_surface("action:software-dev/review", edges) == 1

    def test_no_scope_edges(self) -> None:
        edges = [
            DRGEdge(
                source="directive:DIRECTIVE_001",
                target="tactic:tdd",
                relation=Relation.REQUIRES,
            )
        ]
        assert measure_surface("action:software-dev/implement", edges) == 0

    def test_deduplicates_targets(self) -> None:
        edges = [
            _scope_edge("implement", "directive:DIRECTIVE_001"),
            _scope_edge("implement", "directive:DIRECTIVE_001"),  # duplicate
        ]
        assert measure_surface("action:software-dev/implement", edges) == 1


# ---------------------------------------------------------------------------
# calibrate_surfaces
# ---------------------------------------------------------------------------


class TestCalibrateSurfaces:
    def test_no_calibration_needed(self) -> None:
        """When review >= 80% of implement, no edges are added."""
        nodes = [
            _make_action_node("implement"),
            _make_action_node("review"),
            _make_directive_node(1),
            _make_directive_node(2),
            _make_directive_node(3),
            _make_directive_node(4),
            _make_directive_node(5),
        ]
        edges = [
            _scope_edge("implement", "directive:DIRECTIVE_001"),
            _scope_edge("implement", "directive:DIRECTIVE_002"),
            _scope_edge("implement", "directive:DIRECTIVE_003"),
            _scope_edge("implement", "directive:DIRECTIVE_004"),
            _scope_edge("implement", "directive:DIRECTIVE_005"),
            # review has 4/5 = 80% -- exactly at threshold
            _scope_edge("review", "directive:DIRECTIVE_001"),
            _scope_edge("review", "directive:DIRECTIVE_002"),
            _scope_edge("review", "directive:DIRECTIVE_003"),
            _scope_edge("review", "directive:DIRECTIVE_004"),
        ]
        result = calibrate_surfaces(nodes, edges)
        assert len(result) == len(edges)  # no new edges

    def test_calibration_adds_edges(self) -> None:
        """When review < 80% of implement, edges are added from implement."""
        nodes = [
            _make_action_node("implement"),
            _make_action_node("review"),
            _make_directive_node(1),
            _make_directive_node(2),
            _make_directive_node(3),
            _make_directive_node(4),
            _make_directive_node(5),
            _make_directive_node(6),
            _make_directive_node(7),
            _make_directive_node(8),
            _make_directive_node(9),
            _make_directive_node(10),
        ]
        edges = [
            # implement has 10 scope edges
            _scope_edge("implement", f"directive:DIRECTIVE_{i:03d}")
            for i in range(1, 11)
        ] + [
            # review has 2 -- only 20%, well below 80%
            _scope_edge("review", "directive:DIRECTIVE_001"),
            _scope_edge("review", "directive:DIRECTIVE_002"),
        ]
        result = calibrate_surfaces(nodes, edges)
        review_size = measure_surface("action:software-dev/review", result)
        # Must be >= 80% of 10 = 8
        assert review_size >= 8
        # New edges should all be scope edges
        new_edges = result[len(edges):]
        for edge in new_edges:
            assert edge.relation == Relation.SCOPE
            assert edge.source == "action:software-dev/review"

    def test_only_adds_scope_edges(self) -> None:
        """Calibrator should never add non-scope edges."""
        nodes = [
            _make_action_node("implement"),
            _make_action_node("review"),
            _make_directive_node(1),
            _make_directive_node(2),
            _make_directive_node(3),
        ]
        edges = [
            _scope_edge("implement", "directive:DIRECTIVE_001"),
            _scope_edge("implement", "directive:DIRECTIVE_002"),
            _scope_edge("implement", "directive:DIRECTIVE_003"),
            # Non-scope edge (should not be affected)
            DRGEdge(
                source="directive:DIRECTIVE_001",
                target="directive:DIRECTIVE_002",
                relation=Relation.REQUIRES,
            ),
            # review has 0 scope edges
        ]
        result = calibrate_surfaces(nodes, edges)
        for edge in result:
            if edge not in edges:
                assert edge.relation == Relation.SCOPE

    def test_no_implement_action(self) -> None:
        """When there's no implement action, calibration is a no-op."""
        nodes = [_make_action_node("review"), _make_directive_node(1)]
        edges = [_scope_edge("review", "directive:DIRECTIVE_001")]
        result = calibrate_surfaces(nodes, edges)
        assert result == edges

    def test_no_review_action(self) -> None:
        """When there's no review action, calibration is a no-op."""
        nodes = [_make_action_node("implement"), _make_directive_node(1)]
        edges = [_scope_edge("implement", "directive:DIRECTIVE_001")]
        result = calibrate_surfaces(nodes, edges)
        assert result == edges

    def test_empty_implement(self) -> None:
        """When implement has zero scope, calibration is a no-op."""
        nodes = [
            _make_action_node("implement"),
            _make_action_node("review"),
        ]
        result = calibrate_surfaces(nodes, [])
        assert result == []
