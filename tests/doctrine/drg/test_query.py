"""Unit tests for DRG query primitives (T019 / T021)."""

from __future__ import annotations

import pytest

from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.query import ResolvedContext, resolve_context, walk_edges

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _graph(
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


def _node(urn: str, kind: NodeKind, label: str | None = None) -> DRGNode:
    return DRGNode(urn=urn, kind=kind, label=label)


def _edge(src: str, tgt: str, rel: Relation) -> DRGEdge:
    return DRGEdge(source=src, target=tgt, relation=rel)


# ---------------------------------------------------------------------------
# walk_edges tests
# ---------------------------------------------------------------------------


class TestWalkEdges:
    """Tests for the generic BFS walk_edges function."""

    def test_simple_chain(self) -> None:
        """A -> B -> C via requires; walk from A should reach C."""
        g = _graph(
            nodes=[
                _node("directive:A", NodeKind.DIRECTIVE),
                _node("tactic:B", NodeKind.TACTIC),
                _node("tactic:C", NodeKind.TACTIC),
            ],
            edges=[
                _edge("directive:A", "tactic:B", Relation.REQUIRES),
                _edge("tactic:B", "tactic:C", Relation.REQUIRES),
            ],
        )
        result = walk_edges(g, {"directive:A"}, {Relation.REQUIRES})
        assert result == {"directive:A", "tactic:B", "tactic:C"}

    def test_depth_limit_stops_at_boundary(self) -> None:
        """Walk from A with max_depth=1 should reach B but not C."""
        g = _graph(
            nodes=[
                _node("directive:A", NodeKind.DIRECTIVE),
                _node("tactic:B", NodeKind.TACTIC),
                _node("tactic:C", NodeKind.TACTIC),
            ],
            edges=[
                _edge("directive:A", "tactic:B", Relation.REQUIRES),
                _edge("tactic:B", "tactic:C", Relation.REQUIRES),
            ],
        )
        result = walk_edges(g, {"directive:A"}, {Relation.REQUIRES}, max_depth=1)
        assert result == {"directive:A", "tactic:B"}

    def test_depth_zero_returns_only_start(self) -> None:
        """max_depth=0 should return only start nodes."""
        g = _graph(
            nodes=[
                _node("directive:A", NodeKind.DIRECTIVE),
                _node("tactic:B", NodeKind.TACTIC),
            ],
            edges=[
                _edge("directive:A", "tactic:B", Relation.REQUIRES),
            ],
        )
        result = walk_edges(g, {"directive:A"}, {Relation.REQUIRES}, max_depth=0)
        assert result == {"directive:A"}

    def test_relation_filter(self) -> None:
        """Walk only 'requires' edges, ignoring 'suggests' edges."""
        g = _graph(
            nodes=[
                _node("directive:A", NodeKind.DIRECTIVE),
                _node("tactic:B", NodeKind.TACTIC),
                _node("tactic:C", NodeKind.TACTIC),
            ],
            edges=[
                _edge("directive:A", "tactic:B", Relation.REQUIRES),
                _edge("directive:A", "tactic:C", Relation.SUGGESTS),
            ],
        )
        result = walk_edges(g, {"directive:A"}, {Relation.REQUIRES})
        assert result == {"directive:A", "tactic:B"}
        assert "tactic:C" not in result

    def test_empty_start_set(self) -> None:
        """Empty start set returns empty."""
        g = _graph(
            nodes=[_node("directive:A", NodeKind.DIRECTIVE)],
            edges=[],
        )
        result = walk_edges(g, set(), {Relation.REQUIRES})
        assert result == set()

    def test_no_outgoing_edges(self) -> None:
        """Start node with no outgoing edges returns just the start node."""
        g = _graph(
            nodes=[_node("directive:A", NodeKind.DIRECTIVE)],
            edges=[],
        )
        result = walk_edges(g, {"directive:A"}, {Relation.REQUIRES})
        assert result == {"directive:A"}

    def test_multiple_start_nodes(self) -> None:
        """BFS from multiple starting nodes collects all reachable."""
        g = _graph(
            nodes=[
                _node("directive:A", NodeKind.DIRECTIVE),
                _node("directive:B", NodeKind.DIRECTIVE),
                _node("tactic:C", NodeKind.TACTIC),
                _node("tactic:D", NodeKind.TACTIC),
            ],
            edges=[
                _edge("directive:A", "tactic:C", Relation.REQUIRES),
                _edge("directive:B", "tactic:D", Relation.REQUIRES),
            ],
        )
        result = walk_edges(g, {"directive:A", "directive:B"}, {Relation.REQUIRES})
        assert result == {"directive:A", "directive:B", "tactic:C", "tactic:D"}

    def test_cycle_does_not_loop_forever(self) -> None:
        """Graph with a cycle terminates (BFS visited set prevents loops)."""
        g = _graph(
            nodes=[
                _node("directive:A", NodeKind.DIRECTIVE),
                _node("tactic:B", NodeKind.TACTIC),
            ],
            edges=[
                _edge("directive:A", "tactic:B", Relation.SUGGESTS),
                _edge("tactic:B", "directive:A", Relation.SUGGESTS),
            ],
        )
        result = walk_edges(g, {"directive:A"}, {Relation.SUGGESTS})
        assert result == {"directive:A", "tactic:B"}

    def test_transitive_closure_with_none_depth(self) -> None:
        """max_depth=None walks the entire reachable component."""
        g = _graph(
            nodes=[
                _node("directive:A", NodeKind.DIRECTIVE),
                _node("tactic:B", NodeKind.TACTIC),
                _node("tactic:C", NodeKind.TACTIC),
                _node("tactic:D", NodeKind.TACTIC),
            ],
            edges=[
                _edge("directive:A", "tactic:B", Relation.REQUIRES),
                _edge("tactic:B", "tactic:C", Relation.REQUIRES),
                _edge("tactic:C", "tactic:D", Relation.REQUIRES),
            ],
        )
        result = walk_edges(g, {"directive:A"}, {Relation.REQUIRES}, max_depth=None)
        assert result == {"directive:A", "tactic:B", "tactic:C", "tactic:D"}

    def test_multiple_relations(self) -> None:
        """Walking with multiple relation types follows both."""
        g = _graph(
            nodes=[
                _node("directive:A", NodeKind.DIRECTIVE),
                _node("tactic:B", NodeKind.TACTIC),
                _node("tactic:C", NodeKind.TACTIC),
            ],
            edges=[
                _edge("directive:A", "tactic:B", Relation.REQUIRES),
                _edge("directive:A", "tactic:C", Relation.SUGGESTS),
            ],
        )
        result = walk_edges(
            g, {"directive:A"}, {Relation.REQUIRES, Relation.SUGGESTS}
        )
        assert result == {"directive:A", "tactic:B", "tactic:C"}


# ---------------------------------------------------------------------------
# resolve_context tests
# ---------------------------------------------------------------------------


class TestResolveContext:
    """Tests for the multi-step action context resolution."""

    @pytest.fixture()
    def action_graph(self) -> DRGGraph:
        """Fixture graph with action -> scope/requires/suggests/vocabulary edges."""
        return _graph(
            nodes=[
                _node("action:software-dev/implement", NodeKind.ACTION),
                # Scope targets
                _node("directive:D001", NodeKind.DIRECTIVE),
                _node("tactic:T001", NodeKind.TACTIC),
                # Requires chain from directive
                _node("tactic:T002", NodeKind.TACTIC),
                _node("tactic:T003", NodeKind.TACTIC),
                # Suggests from tactic T001
                _node("styleguide:SG001", NodeKind.STYLEGUIDE),
                _node("toolguide:TG001", NodeKind.TOOLGUIDE),
                # Vocabulary
                _node("glossary_scope:project", NodeKind.GLOSSARY_SCOPE),
            ],
            edges=[
                # Scope edges from action (depth 1)
                _edge("action:software-dev/implement", "directive:D001", Relation.SCOPE),
                _edge("action:software-dev/implement", "tactic:T001", Relation.SCOPE),
                # Requires chain: D001 -> T002 -> T003
                _edge("directive:D001", "tactic:T002", Relation.REQUIRES),
                _edge("tactic:T002", "tactic:T003", Relation.REQUIRES),
                # Suggests from T001 (hop 1: SG001, hop 2: TG001)
                _edge("tactic:T001", "styleguide:SG001", Relation.SUGGESTS),
                _edge("styleguide:SG001", "toolguide:TG001", Relation.SUGGESTS),
                # Vocabulary from D001
                _edge("directive:D001", "glossary_scope:project", Relation.VOCABULARY),
            ],
        )

    def test_artifact_urns_include_scope_targets(self, action_graph: DRGGraph) -> None:
        """Scope targets are included in artifact_urns."""
        result = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        assert "directive:D001" in result.artifact_urns
        assert "tactic:T001" in result.artifact_urns

    def test_artifact_urns_include_requires_transitive(
        self, action_graph: DRGGraph
    ) -> None:
        """Requires edges are followed transitively."""
        result = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        assert "tactic:T002" in result.artifact_urns
        assert "tactic:T003" in result.artifact_urns

    def test_artifact_urns_include_suggests(self, action_graph: DRGGraph) -> None:
        """Suggests edges are followed up to depth."""
        result = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        assert "styleguide:SG001" in result.artifact_urns
        assert "toolguide:TG001" in result.artifact_urns

    def test_suggests_respects_depth_limit(self, action_graph: DRGGraph) -> None:
        """depth=1 limits suggests to one hop -- TG001 (2 hops) excluded."""
        result = resolve_context(action_graph, "action:software-dev/implement", depth=1)
        assert "styleguide:SG001" in result.artifact_urns
        assert "toolguide:TG001" not in result.artifact_urns

    def test_glossary_scopes_from_vocabulary(self, action_graph: DRGGraph) -> None:
        """Vocabulary edges produce glossary_scopes."""
        result = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        assert "glossary_scope:project" in result.glossary_scopes

    def test_action_urn_not_in_artifact_urns(self, action_graph: DRGGraph) -> None:
        """The action node itself should not appear in artifact_urns."""
        result = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        assert "action:software-dev/implement" not in result.artifact_urns

    def test_glossary_scopes_not_in_artifact_urns(
        self, action_graph: DRGGraph
    ) -> None:
        """Glossary scopes should not appear in artifact_urns."""
        result = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        assert "glossary_scope:project" not in result.artifact_urns

    def test_result_uses_frozensets(self, action_graph: DRGGraph) -> None:
        """ResolvedContext fields are frozensets."""
        result = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        assert isinstance(result.artifact_urns, frozenset)
        assert isinstance(result.glossary_scopes, frozenset)

    def test_deterministic_output(self, action_graph: DRGGraph) -> None:
        """Same graph always produces the same result."""
        r1 = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        r2 = resolve_context(action_graph, "action:software-dev/implement", depth=2)
        assert r1 == r2

    def test_nonexistent_action_returns_empty(self) -> None:
        """An action URN not in the graph produces empty results."""
        g = _graph(nodes=[], edges=[])
        result = resolve_context(g, "action:software-dev/nonexistent", depth=2)
        assert result.artifact_urns == frozenset()
        assert result.glossary_scopes == frozenset()

    def test_no_vocabulary_edges_empty_glossary(self) -> None:
        """When no vocabulary edges exist, glossary_scopes is empty."""
        g = _graph(
            nodes=[
                _node("action:software-dev/implement", NodeKind.ACTION),
                _node("directive:D001", NodeKind.DIRECTIVE),
            ],
            edges=[
                _edge("action:software-dev/implement", "directive:D001", Relation.SCOPE),
            ],
        )
        result = resolve_context(g, "action:software-dev/implement", depth=2)
        assert result.glossary_scopes == frozenset()

    def test_resolve_against_valid_fixture(self) -> None:
        """Resolve against the test fixture graph (valid_graph.yaml)."""
        from pathlib import Path

        from doctrine.drg.loader import load_graph

        fixtures_dir = Path(__file__).parent / "fixtures"
        graph = load_graph(fixtures_dir / "valid_graph.yaml")

        result = resolve_context(graph, "action:software-dev/specify", depth=2)
        # The fixture has scope edges: specify -> D001, D002, adr-drafting,
        # kitty-glossary-writing, efficient-local-tooling, release-checklist
        assert "directive:DIRECTIVE_001" in result.artifact_urns
        assert "directive:DIRECTIVE_002" in result.artifact_urns
        assert "tactic:adr-drafting-workflow" in result.artifact_urns
        # D001 requires adr-drafting-workflow and tdd-red-green-refactor
        assert "tactic:tdd-red-green-refactor" in result.artifact_urns
        # D001 has vocabulary -> glossary_scope:project
        assert "glossary_scope:project" in result.glossary_scopes
