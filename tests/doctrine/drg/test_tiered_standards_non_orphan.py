"""Non-orphan test for the tiered-standards styleguide DRG node.

Asserts that:
1. The ``styleguide:tiered-standards`` node exists in the shipped graph.
2. The node has a specific inbound edge from ``directive:DIRECTIVE_030``
   (Test and Typecheck Quality Gate) with relation ``suggests``.

Rationale: orphan doctrine nodes (registered but unreachable from any other
artifact) are permitted structurally but provide no navigational value.
The inbound edge from DIRECTIVE_030 ensures the tiered-standards styleguide
is reachable from a code-quality gate directive (#1843 / #2096, WP04).

If the edge is removed this test must turn RED — the assertion is on the
specific source node, not merely ``len(inbound) >= 1``, so a throwaway
self-edge or unrelated edge will not satisfy it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.drg.loader import load_graph, merge_layers
from doctrine.drg.models import Relation

pytestmark = pytest.mark.fast

SHIPPED_GRAPH = Path(__file__).resolve().parents[3] / "src" / "doctrine" / "graph.yaml"

_STYLEGUIDE_URN = "styleguide:tiered-standards"
_SOURCE_DIRECTIVE_URN = "directive:DIRECTIVE_030"
_EXPECTED_RELATION = Relation.SUGGESTS


def test_tiered_standards_node_exists() -> None:
    """The tiered-standards styleguide node must be present in the shipped graph."""
    graph = load_graph(SHIPPED_GRAPH)
    merged = merge_layers(graph, None)
    node_urns = {node.urn for node in merged.nodes}
    assert _STYLEGUIDE_URN in node_urns, (
        f"Node {_STYLEGUIDE_URN!r} not found in shipped graph.yaml. "
        "Run 'spec-kitty doctrine regenerate-graph' to refresh."
    )


def test_tiered_standards_has_inbound_edge_from_directive_030() -> None:
    """The tiered-standards styleguide must have an inbound edge from DIRECTIVE_030.

    This test proves the styleguide is non-orphan via a *specific* source node —
    not a weak ``len(inbound) >= 1`` check.  Removing the ``references`` entry
    for ``tiered-standards`` in
    ``src/doctrine/directives/built-in/030-test-and-typecheck-quality-gate.directive.yaml``
    and regenerating graph.yaml will make this test fail.
    """
    graph = load_graph(SHIPPED_GRAPH)
    merged = merge_layers(graph, None)

    inbound_from_directive_030 = [
        edge
        for edge in merged.edges
        if edge.target == _STYLEGUIDE_URN
        and edge.source == _SOURCE_DIRECTIVE_URN
        and edge.relation == _EXPECTED_RELATION
    ]

    assert inbound_from_directive_030, (
        f"Expected an inbound '{_EXPECTED_RELATION}' edge from "
        f"{_SOURCE_DIRECTIVE_URN!r} to {_STYLEGUIDE_URN!r} in shipped graph.yaml, "
        "but none was found. "
        "Ensure DIRECTIVE_030 has a references entry for 'tiered-standards' and "
        "run 'spec-kitty doctrine regenerate-graph'."
    )
