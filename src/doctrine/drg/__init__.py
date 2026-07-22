"""Doctrine Reference Graph (DRG) -- schema, loader, and validation.

Public API:

    from doctrine.drg import (
        NodeKind, Relation,
        DRGNode, DRGEdge, DRGGraph,
        load_graph, load_graph_or_dir, merge_layers, DRGLoadError,
        validate_graph, assert_valid, DRGValidationError,
    )
"""

from __future__ import annotations

from doctrine.drg.loader import (
    DRGLoadError,
    built_in_graph_source,
    has_graph_files,
    load_built_in_graph,
    load_graph,
    load_graph_or_dir,
    merge_layers,
)
from doctrine.drg.models import (
    DRGEdge,
    DRGGraph,
    DRGNode,
    NodeKind,
    Relation,
)
from doctrine.drg.query import ResolvedContext, resolve_context, walk_edges
from doctrine.drg.validator import DRGValidationError, assert_valid, validate_graph

__all__ = [
    "NodeKind",
    "Relation",
    "DRGNode",
    "DRGEdge",
    "DRGGraph",
    "built_in_graph_source",
    "has_graph_files",
    "load_built_in_graph",
    "load_graph",
    "load_graph_or_dir",
    "merge_layers",
    "DRGLoadError",
    "validate_graph",
    "assert_valid",
    "DRGValidationError",
    "walk_edges",
    "resolve_context",
    "ResolvedContext",
]
