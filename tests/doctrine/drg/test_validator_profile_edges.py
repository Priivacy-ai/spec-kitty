"""Tests for symmetric profile-edge validation (WP09 / FR-009 / #1755).

``validate_profile_edges`` closes the historical asymmetric blind spot: a
``specializes_from`` / ``delegates_to`` edge was only exercised in the
outgoing direction at resolution time, so a profile edge pointing at (or
declared from) a non-profile node, or a lineage cycle, could slip through.
The check inspects both endpoints independently and verifies lineage is a DAG.
"""

from __future__ import annotations

import pytest

from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.validator import validate_graph, validate_profile_edges

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]


def _graph(nodes: list[DRGNode], edges: list[DRGEdge]) -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at="STATIC",
        generated_by="test",
        nodes=nodes,
        edges=edges,
    )


def _profile(pid: str) -> DRGNode:
    return DRGNode(urn=f"agent_profile:{pid}", kind=NodeKind.AGENT_PROFILE)


class TestEndpointKindIntegrity:
    def test_valid_profile_to_profile_lineage_passes(self) -> None:
        graph = _graph(
            [_profile("child"), _profile("parent")],
            [
                DRGEdge(
                    source="agent_profile:child",
                    target="agent_profile:parent",
                    relation=Relation.SPECIALIZES_FROM,
                )
            ],
        )
        assert validate_profile_edges(graph) == []

    def test_valid_delegation_passes(self) -> None:
        graph = _graph(
            [_profile("a"), _profile("b")],
            [
                DRGEdge(
                    source="agent_profile:a",
                    target="agent_profile:b",
                    relation=Relation.DELEGATES_TO,
                )
            ],
        )
        assert validate_profile_edges(graph) == []

    def test_lineage_target_non_profile_is_detected(self) -> None:
        """A profile-edge whose *target* is a tactic must be flagged."""
        graph = _graph(
            [_profile("child"), DRGNode(urn="tactic:tdd", kind=NodeKind.TACTIC)],
            [
                DRGEdge(
                    source="agent_profile:child",
                    target="tactic:tdd",
                    relation=Relation.SPECIALIZES_FROM,
                )
            ],
        )
        errors = validate_profile_edges(graph)
        assert len(errors) == 1
        assert "target" in errors[0]
        assert "tactic:tdd" in errors[0]

    def test_lineage_source_non_profile_is_detected_symmetrically(self) -> None:
        """The *source* endpoint is checked just like the target (symmetry)."""
        graph = _graph(
            [
                DRGNode(urn="directive:DIRECTIVE_001", kind=NodeKind.DIRECTIVE),
                _profile("parent"),
            ],
            [
                DRGEdge(
                    source="directive:DIRECTIVE_001",
                    target="agent_profile:parent",
                    relation=Relation.SPECIALIZES_FROM,
                )
            ],
        )
        errors = validate_profile_edges(graph)
        assert len(errors) == 1
        assert "source" in errors[0]
        assert "directive:DIRECTIVE_001" in errors[0]

    def test_missing_endpoint_not_double_reported(self) -> None:
        """A missing node is dangling (validate_graph's job), not a kind error."""
        graph = _graph(
            [_profile("child")],
            [
                DRGEdge(
                    source="agent_profile:child",
                    target="agent_profile:ghost",
                    relation=Relation.SPECIALIZES_FROM,
                )
            ],
        )
        # validate_profile_edges stays silent about the missing node ...
        assert validate_profile_edges(graph) == []
        # ... validate_graph reports it exactly once, as a dangling target.
        errors = validate_graph(graph)
        assert any("Dangling target" in e for e in errors)

    def test_non_profile_relations_ignored(self) -> None:
        """A requires edge between non-profiles is none of this check's business."""
        graph = _graph(
            [
                DRGNode(urn="directive:DIRECTIVE_001", kind=NodeKind.DIRECTIVE),
                DRGNode(urn="tactic:tdd", kind=NodeKind.TACTIC),
            ],
            [
                DRGEdge(
                    source="directive:DIRECTIVE_001",
                    target="tactic:tdd",
                    relation=Relation.REQUIRES,
                )
            ],
        )
        assert validate_profile_edges(graph) == []


class TestLineageAcyclicity:
    def test_lineage_cycle_is_detected(self) -> None:
        graph = _graph(
            [_profile("a"), _profile("b")],
            [
                DRGEdge(
                    source="agent_profile:a",
                    target="agent_profile:b",
                    relation=Relation.SPECIALIZES_FROM,
                ),
                DRGEdge(
                    source="agent_profile:b",
                    target="agent_profile:a",
                    relation=Relation.SPECIALIZES_FROM,
                ),
            ],
        )
        errors = validate_profile_edges(graph)
        assert any("Cycle in specializes_from lineage" in e for e in errors)

    def test_delegation_cycle_is_allowed(self) -> None:
        """delegates_to is runtime handoff, not lineage; cycles are not flagged."""
        graph = _graph(
            [_profile("a"), _profile("b")],
            [
                DRGEdge(
                    source="agent_profile:a",
                    target="agent_profile:b",
                    relation=Relation.DELEGATES_TO,
                ),
                DRGEdge(
                    source="agent_profile:b",
                    target="agent_profile:a",
                    relation=Relation.DELEGATES_TO,
                ),
            ],
        )
        assert validate_profile_edges(graph) == []


class TestWiredIntoValidateGraph:
    def test_profile_edge_error_surfaces_via_validate_graph(self) -> None:
        graph = _graph(
            [_profile("child"), DRGNode(urn="tactic:tdd", kind=NodeKind.TACTIC)],
            [
                DRGEdge(
                    source="agent_profile:child",
                    target="tactic:tdd",
                    relation=Relation.SPECIALIZES_FROM,
                )
            ],
        )
        errors = validate_graph(graph)
        assert any("must be an agent_profile" in e for e in errors)

    def test_duplicate_edges_are_reported(self) -> None:
        graph = _graph(
            [_profile("child"), _profile("parent")],
            [
                DRGEdge(
                    source="agent_profile:child",
                    target="agent_profile:parent",
                    relation=Relation.REQUIRES,
                ),
                DRGEdge(
                    source="agent_profile:child",
                    target="agent_profile:parent",
                    relation=Relation.REQUIRES,
                ),
            ],
        )
        errors = validate_graph(graph)
        assert any("Duplicate edge" in e for e in errors)

    def test_requires_cycle_is_reported(self) -> None:
        graph = _graph(
            [_profile("a"), _profile("b")],
            [
                DRGEdge(
                    source="agent_profile:a",
                    target="agent_profile:b",
                    relation=Relation.REQUIRES,
                ),
                DRGEdge(
                    source="agent_profile:b",
                    target="agent_profile:a",
                    relation=Relation.REQUIRES,
                ),
            ],
        )
        errors = validate_graph(graph)
        assert any("Cycle in requires" in e for e in errors)

    def test_dangling_source_is_reported(self) -> None:
        graph = _graph(
            [_profile("parent")],
            [
                DRGEdge(
                    source="agent_profile:ghost",
                    target="agent_profile:parent",
                    relation=Relation.REQUIRES,
                )
            ],
        )
        errors = validate_graph(graph)
        assert any("Dangling source" in e for e in errors)
