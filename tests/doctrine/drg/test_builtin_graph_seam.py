"""Unit tests for the canonical built-in-graph seam (WP03, mission #2680).

``load_built_in_graph`` / ``built_in_graph_source`` are the single accessor
every source reader of the shipped DRG must route through. Routing every reader
to the *directory* is what let WP05 delete the ``src/doctrine/graph.yaml``
monolith and flip all consumers to ``*.graph.yaml`` fragments with no
call-site edits — this test locks in the post-flip sharded layout.
"""

from __future__ import annotations

import pytest

from doctrine.drg.loader import (
    built_in_graph_source,
    load_built_in_graph,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_source_points_at_doctrine_root_directory() -> None:
    """The seam yields the doctrine *directory*, not a ``graph.yaml`` file.

    Routing every reader to the directory is what let WP05 delete the monolith
    and flip all consumers to ``*.graph.yaml`` fragments with no further edits.
    """
    source = built_in_graph_source()

    assert source.is_dir()
    assert source.name == "doctrine"
    # Post-flip sharded layout (WP05): the monolith is retired; the built-in DRG
    # ships as per-kind ``*.graph.yaml`` fragments the seam merges on load.
    assert not (source / "graph.yaml").exists()
    assert sorted(source.glob("*.graph.yaml")), "no *.graph.yaml fragments present"


def test_seam_returns_a_populated_graph() -> None:
    """Sanity: the shipped built-in graph is non-empty (nodes and edges)."""
    graph = load_built_in_graph()

    assert graph.nodes, "built-in graph should ship nodes"
    assert graph.edges, "built-in graph should ship edges"
