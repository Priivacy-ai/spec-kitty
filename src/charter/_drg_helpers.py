"""Shared DRG graph-load helpers for charter resolver and compiler.

Introduced in WP03 of the
``excise-doctrine-curation-and-inline-references-01KP54J6`` mission so that
``src/charter/resolver.py`` and ``src/charter/compiler.py`` no longer
duplicate the shipped+project merge/validate sequence.
"""

from __future__ import annotations

from pathlib import Path

from charter.catalog import resolve_doctrine_root
from doctrine.drg.loader import load_graph, merge_layers
from doctrine.drg.models import DRGGraph
from doctrine.drg.validator import assert_valid


def load_validated_graph(repo_root: Path) -> DRGGraph:
    """Load the shipped + project DRG overlay and validate the result.

    Args:
        repo_root: Project root; used to locate the optional project
            overlay at ``<repo_root>/.kittify/doctrine/graph.yaml``.

    Returns:
        A validated :class:`DRGGraph`.

    Raises:
        ValueError: If :func:`assert_valid` rejects the merged graph
            (dangling edges, duplicate edges, or ``requires`` cycles).
    """
    doctrine_root = resolve_doctrine_root()
    shipped = load_graph(doctrine_root / "graph.yaml")
    project_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
    project = load_graph(project_path) if project_path.exists() else None
    merged = merge_layers(shipped, project)
    assert_valid(merged)
    return merged


__all__ = ["load_validated_graph"]
