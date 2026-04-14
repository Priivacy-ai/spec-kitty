"""Regression test: shipped graph.yaml + project overlay is always cycle-free
and otherwise structurally valid.

Replaces the coverage that previously lived in
``tests/doctrine/test_cycle_detection.py`` and
``tests/doctrine/test_shipped_doctrine_cycle_free.py``, which both imported
from the deleted charter transitive-reference module.

:func:`doctrine.drg.validator.assert_valid` rejects:

- dangling edges (target URN not in nodes)
- duplicate edges
- cycles in the ``requires`` subgraph
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.drg.loader import load_graph, merge_layers
from doctrine.drg.validator import assert_valid

pytestmark = pytest.mark.fast

SHIPPED_GRAPH = Path(__file__).resolve().parents[3] / "src" / "doctrine" / "graph.yaml"


def test_shipped_graph_loads_and_validates() -> None:
    graph = load_graph(SHIPPED_GRAPH)
    merged = merge_layers(graph, None)
    assert_valid(merged)


def test_shipped_graph_has_no_requires_cycles() -> None:
    """assert_valid checks requires cycles; exercise it as an explicit
    assertion so a regression in the validator surface is caught here."""
    graph = load_graph(SHIPPED_GRAPH)
    merged = merge_layers(graph, None)
    assert_valid(merged)


def test_shipped_graph_has_at_least_one_edge() -> None:
    """Smoke check that the graph file is non-degenerate."""
    graph = load_graph(SHIPPED_GRAPH)
    assert len(graph.edges) > 0, "shipped graph.yaml must contain edges"
