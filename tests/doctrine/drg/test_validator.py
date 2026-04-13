"""Unit tests for DRG validator (T008)."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.drg.loader import load_graph
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.validator import DRGValidationError, assert_valid, validate_graph


def _make_graph(
    nodes: list[DRGNode],
    edges: list[DRGEdge],
) -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-04-13T10:00:00+00:00",
        generated_by="test",
        nodes=nodes,
        edges=edges,
    )


class TestValidateGraph:
    def test_valid_graph_has_no_errors(self, valid_graph_path: Path) -> None:
        graph = load_graph(valid_graph_path)
        errors = validate_graph(graph)
        assert errors == []

    def test_empty_graph_is_valid(self) -> None:
        graph = _make_graph([], [])
        assert validate_graph(graph) == []

    def test_dangling_source_detected(self) -> None:
        graph = _make_graph(
            nodes=[DRGNode(urn="tactic:B", kind=NodeKind.TACTIC)],
            edges=[
                DRGEdge(
                    source="directive:MISSING",
                    target="tactic:B",
                    relation=Relation.REQUIRES,
                ),
            ],
        )
        errors = validate_graph(graph)
        assert len(errors) == 1
        assert "Dangling source" in errors[0]
        assert "directive:MISSING" in errors[0]

    def test_dangling_target_detected(self) -> None:
        graph = _make_graph(
            nodes=[DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE)],
            edges=[
                DRGEdge(
                    source="directive:A",
                    target="tactic:MISSING",
                    relation=Relation.REQUIRES,
                ),
            ],
        )
        errors = validate_graph(graph)
        assert len(errors) == 1
        assert "Dangling target" in errors[0]
        assert "tactic:MISSING" in errors[0]

    def test_dangling_ref_fixture(self, dangling_ref_graph_path: Path) -> None:
        graph = load_graph(dangling_ref_graph_path)
        errors = validate_graph(graph)
        assert any("Dangling target" in e for e in errors)

    def test_duplicate_edge_detected(self) -> None:
        graph = _make_graph(
            nodes=[
                DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE),
                DRGNode(urn="tactic:B", kind=NodeKind.TACTIC),
            ],
            edges=[
                DRGEdge(source="directive:A", target="tactic:B", relation=Relation.REQUIRES),
                DRGEdge(source="directive:A", target="tactic:B", relation=Relation.REQUIRES),
            ],
        )
        errors = validate_graph(graph)
        assert any("Duplicate edge" in e for e in errors)

    def test_duplicate_edge_fixture(self, duplicate_edge_graph_path: Path) -> None:
        graph = load_graph(duplicate_edge_graph_path)
        errors = validate_graph(graph)
        assert any("Duplicate edge" in e for e in errors)

    def test_same_endpoints_different_relations_not_duplicate(self) -> None:
        graph = _make_graph(
            nodes=[
                DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE),
                DRGNode(urn="tactic:B", kind=NodeKind.TACTIC),
            ],
            edges=[
                DRGEdge(source="directive:A", target="tactic:B", relation=Relation.REQUIRES),
                DRGEdge(source="directive:A", target="tactic:B", relation=Relation.SUGGESTS),
            ],
        )
        errors = validate_graph(graph)
        assert errors == []

    def test_requires_cycle_detected(self) -> None:
        graph = _make_graph(
            nodes=[
                DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE),
                DRGNode(urn="directive:B", kind=NodeKind.DIRECTIVE),
                DRGNode(urn="directive:C", kind=NodeKind.DIRECTIVE),
            ],
            edges=[
                DRGEdge(source="directive:A", target="directive:B", relation=Relation.REQUIRES),
                DRGEdge(source="directive:B", target="directive:C", relation=Relation.REQUIRES),
                DRGEdge(source="directive:C", target="directive:A", relation=Relation.REQUIRES),
            ],
        )
        errors = validate_graph(graph)
        assert any("Cycle in requires" in e for e in errors)

    def test_requires_cycle_fixture(self, cyclic_requires_graph_path: Path) -> None:
        graph = load_graph(cyclic_requires_graph_path)
        errors = validate_graph(graph)
        assert any("Cycle in requires" in e for e in errors)

    def test_suggests_cycle_is_allowed(self) -> None:
        """Cycles in non-requires edges must NOT be flagged."""
        graph = _make_graph(
            nodes=[
                DRGNode(urn="tactic:A", kind=NodeKind.TACTIC),
                DRGNode(urn="tactic:B", kind=NodeKind.TACTIC),
            ],
            edges=[
                DRGEdge(source="tactic:A", target="tactic:B", relation=Relation.SUGGESTS),
                DRGEdge(source="tactic:B", target="tactic:A", relation=Relation.SUGGESTS),
            ],
        )
        errors = validate_graph(graph)
        assert errors == []

    def test_replaces_cycle_is_allowed(self) -> None:
        """Cycles in replaces edges must NOT be flagged."""
        graph = _make_graph(
            nodes=[
                DRGNode(urn="paradigm:A", kind=NodeKind.PARADIGM),
                DRGNode(urn="paradigm:B", kind=NodeKind.PARADIGM),
            ],
            edges=[
                DRGEdge(source="paradigm:A", target="paradigm:B", relation=Relation.REPLACES),
                DRGEdge(source="paradigm:B", target="paradigm:A", relation=Relation.REPLACES),
            ],
        )
        errors = validate_graph(graph)
        assert errors == []


class TestAssertValid:
    def test_raises_on_errors(self) -> None:
        graph = _make_graph(
            nodes=[DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE)],
            edges=[
                DRGEdge(
                    source="directive:A",
                    target="tactic:MISSING",
                    relation=Relation.REQUIRES,
                ),
            ],
        )
        with pytest.raises(DRGValidationError) as exc_info:
            assert_valid(graph)
        assert len(exc_info.value.errors) > 0

    def test_passes_on_valid(self, valid_graph_path: Path) -> None:
        graph = load_graph(valid_graph_path)
        assert_valid(graph)  # should not raise

    def test_passes_on_empty(self) -> None:
        graph = _make_graph([], [])
        assert_valid(graph)  # should not raise
