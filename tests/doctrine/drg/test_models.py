"""Unit tests for DRG Pydantic models (T005, T006)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from doctrine.drg.models import (
    DRGEdge,
    DRGGraph,
    DRGNode,
    NodeKind,
    Relation,
)


# ---------------------------------------------------------------------------
# NodeKind / Relation enums
# ---------------------------------------------------------------------------


class TestNodeKind:
    def test_all_nine_kinds_exist(self) -> None:
        assert len(NodeKind) == 9

    def test_values_are_lowercase(self) -> None:
        for kind in NodeKind:
            assert kind.value == kind.value.lower()

    def test_specific_members(self) -> None:
        assert NodeKind.DIRECTIVE == "directive"
        assert NodeKind.ACTION == "action"
        assert NodeKind.GLOSSARY_SCOPE == "glossary_scope"
        assert NodeKind.AGENT_PROFILE == "agent_profile"


class TestRelation:
    def test_all_eight_relations_exist(self) -> None:
        assert len(Relation) == 8

    def test_specific_members(self) -> None:
        assert Relation.REQUIRES == "requires"
        assert Relation.DELEGATES_TO == "delegates_to"
        assert Relation.REPLACES == "replaces"


# ---------------------------------------------------------------------------
# DRGNode
# ---------------------------------------------------------------------------


class TestDRGNode:
    def test_valid_node(self) -> None:
        node = DRGNode(urn="directive:DIRECTIVE_001", kind=NodeKind.DIRECTIVE, label="Test")
        assert node.urn == "directive:DIRECTIVE_001"
        assert node.kind == NodeKind.DIRECTIVE
        assert node.label == "Test"

    def test_label_optional(self) -> None:
        node = DRGNode(urn="tactic:test-tactic", kind=NodeKind.TACTIC)
        assert node.label is None

    def test_malformed_urn_rejected(self) -> None:
        with pytest.raises(ValidationError, match="URN"):
            DRGNode(urn="bad urn!", kind=NodeKind.DIRECTIVE)

    def test_urn_with_spaces_rejected(self) -> None:
        with pytest.raises(ValidationError, match="URN"):
            DRGNode(urn="directive:has space", kind=NodeKind.DIRECTIVE)

    def test_kind_urn_mismatch_rejected(self) -> None:
        with pytest.raises(ValidationError, match="does not match kind"):
            DRGNode(urn="directive:DIRECTIVE_001", kind=NodeKind.TACTIC)

    def test_urn_with_slash(self) -> None:
        node = DRGNode(urn="action:software-dev/specify", kind=NodeKind.ACTION)
        assert node.urn == "action:software-dev/specify"

    def test_urn_with_dots(self) -> None:
        node = DRGNode(urn="tactic:v1.2.3-workflow", kind=NodeKind.TACTIC)
        assert node.urn == "tactic:v1.2.3-workflow"

    def test_agent_profile_urn(self) -> None:
        node = DRGNode(urn="agent_profile:implementer", kind=NodeKind.AGENT_PROFILE)
        assert node.kind == NodeKind.AGENT_PROFILE

    def test_glossary_scope_urn(self) -> None:
        node = DRGNode(urn="glossary_scope:project", kind=NodeKind.GLOSSARY_SCOPE)
        assert node.kind == NodeKind.GLOSSARY_SCOPE


# ---------------------------------------------------------------------------
# DRGEdge
# ---------------------------------------------------------------------------


class TestDRGEdge:
    def test_valid_edge(self) -> None:
        edge = DRGEdge(
            source="directive:DIRECTIVE_001",
            target="tactic:some-tactic",
            relation=Relation.REQUIRES,
        )
        assert edge.source == "directive:DIRECTIVE_001"
        assert edge.when is None
        assert edge.reason is None

    def test_edge_with_when(self) -> None:
        edge = DRGEdge(
            source="tactic:a",
            target="tactic:b",
            relation=Relation.SUGGESTS,
            when="Writing code",
        )
        assert edge.when == "Writing code"

    def test_edge_with_reason(self) -> None:
        edge = DRGEdge(
            source="paradigm:a",
            target="paradigm:b",
            relation=Relation.REPLACES,
            reason="Superseded by new approach",
        )
        assert edge.reason == "Superseded by new approach"

    def test_malformed_source_rejected(self) -> None:
        with pytest.raises(ValidationError, match="source"):
            DRGEdge(
                source="bad urn!",
                target="tactic:ok",
                relation=Relation.REQUIRES,
            )

    def test_malformed_target_rejected(self) -> None:
        with pytest.raises(ValidationError, match="target"):
            DRGEdge(
                source="tactic:ok",
                target="bad urn!",
                relation=Relation.REQUIRES,
            )

    def test_invalid_relation_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DRGEdge(
                source="tactic:a",
                target="tactic:b",
                relation="not_a_relation",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# DRGGraph
# ---------------------------------------------------------------------------


class TestDRGGraph:
    @pytest.fixture()
    def simple_graph(self) -> DRGGraph:
        return DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[
                DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE),
                DRGNode(urn="tactic:B", kind=NodeKind.TACTIC),
                DRGNode(urn="tactic:C", kind=NodeKind.TACTIC),
            ],
            edges=[
                DRGEdge(source="directive:A", target="tactic:B", relation=Relation.REQUIRES),
                DRGEdge(source="directive:A", target="tactic:C", relation=Relation.SUGGESTS),
            ],
        )

    def test_schema_version_must_be_1_0(self) -> None:
        with pytest.raises(ValidationError, match="schema_version"):
            DRGGraph(
                schema_version="2.0",
                generated_at="2026-04-13T10:00:00+00:00",
                generated_by="test",
                nodes=[],
                edges=[],
            )

    def test_empty_graph_valid(self) -> None:
        g = DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[],
            edges=[],
        )
        assert g.node_urns() == set()

    def test_node_urns(self, simple_graph: DRGGraph) -> None:
        assert simple_graph.node_urns() == {"directive:A", "tactic:B", "tactic:C"}

    def test_edges_from_all(self, simple_graph: DRGGraph) -> None:
        edges = simple_graph.edges_from("directive:A")
        assert len(edges) == 2

    def test_edges_from_filtered(self, simple_graph: DRGGraph) -> None:
        edges = simple_graph.edges_from("directive:A", relation=Relation.REQUIRES)
        assert len(edges) == 1
        assert edges[0].target == "tactic:B"

    def test_edges_from_no_match(self, simple_graph: DRGGraph) -> None:
        edges = simple_graph.edges_from("tactic:B")
        assert edges == []

    def test_get_node_found(self, simple_graph: DRGGraph) -> None:
        node = simple_graph.get_node("directive:A")
        assert node is not None
        assert node.kind == NodeKind.DIRECTIVE

    def test_get_node_not_found(self, simple_graph: DRGGraph) -> None:
        assert simple_graph.get_node("directive:NONEXISTENT") is None
