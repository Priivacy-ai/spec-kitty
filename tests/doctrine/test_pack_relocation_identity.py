"""T019 — Full-projection identity of the built-in DRG after relocation (NFR-001).

The relocation mission (``relocate-builtin-doctrine-packs``) moved the shipped
built-in doctrine content out of ``src/doctrine/<kind>/built-in/`` into the flat
pack root ``packs/built-in/<kind>/``. The move MUST be behaviour-preserving: the
graph the loader assembles from the new location has to be byte-for-byte
equivalent — as a *full projection* — to the pre-move baseline captured by WP01
(``tests/doctrine/fixtures/graph-identity.baseline.json``).

Why a full projection rather than a cardinality smoke check: a dropped per-edge
``when`` gate (or a lost ``reason`` / re-labelled node) leaves the 324/892
counts intact while silently changing doctrine behaviour. The counts are asserted
too, but only as a fast-failing smoke check *in addition to* the exact
node/edge projection equality.

Projection shape (matches the baseline fixture element order exactly):

* node -> ``(urn, label, sorted(tags))``
* edge -> ``(source, relation, target, when, reason)``
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from doctrine.drg.loader import load_built_in_graph

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

BASELINE_PATH = Path(__file__).parent / "fixtures" / "graph-identity.baseline.json"

# WP01 baseline cardinality — a *smoke* check only (see module docstring).
EXPECTED_NODE_COUNT = 324
EXPECTED_EDGE_COUNT = 892

NodeProjection = tuple[str, str | None, tuple[str, ...]]
EdgeProjection = tuple[str, str, str, str | None, str | None]


def _load_baseline() -> dict[str, list[list]]:
    with BASELINE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _baseline_nodes(baseline: dict[str, list[list]]) -> list[NodeProjection]:
    return sorted(
        (urn, label, tuple(sorted(tags)))
        for urn, label, tags in baseline["nodes"]
    )


def _baseline_edges(baseline: dict[str, list[list]]) -> list[EdgeProjection]:
    return sorted(
        (source, relation, target, when, reason)
        for source, relation, target, when, reason in baseline["edges"]
    )


def _live_nodes() -> list[NodeProjection]:
    graph = load_built_in_graph()
    return sorted(
        (node.urn, node.label, tuple(sorted(node.tags))) for node in graph.nodes
    )


def _live_edges() -> list[EdgeProjection]:
    graph = load_built_in_graph()
    return sorted(
        (edge.source, edge.relation.value, edge.target, edge.when, edge.reason)
        for edge in graph.edges
    )


def test_baseline_fixture_is_the_expected_cardinality() -> None:
    """Guard the fixture itself so a corrupted baseline cannot green-wash identity."""
    baseline = _load_baseline()
    assert len(baseline["nodes"]) == EXPECTED_NODE_COUNT
    assert len(baseline["edges"]) == EXPECTED_EDGE_COUNT


def test_built_in_graph_cardinality_smoke() -> None:
    """Smoke check: post-move counts still 324/892 (not sufficient on its own)."""
    graph = load_built_in_graph()
    assert len(graph.nodes) == EXPECTED_NODE_COUNT
    assert len(graph.edges) == EXPECTED_EDGE_COUNT


def test_node_projection_matches_baseline_exactly() -> None:
    """Every node's (urn, label, sorted(tags)) equals the WP01 baseline."""
    assert _live_nodes() == _baseline_nodes(_load_baseline())


def test_edge_projection_matches_baseline_exactly() -> None:
    """Every edge's (source, relation, target, when, reason) equals the baseline.

    A dropped ``when`` gate or lost ``reason`` fails HERE while leaving the
    892-edge count intact — which is the whole point of the full projection.
    """
    assert _live_edges() == _baseline_edges(_load_baseline())
