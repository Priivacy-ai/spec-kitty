"""Charter facade for DRG (Doctrine Reference Graph) types.

This module is the charter-layer proxy for runtime callers that historically
imported from ``doctrine.drg`` directly. The runtime → charter → doctrine
boundary (ADR 2026-03-27-1, tightened by mission
``charter-mediated-doctrine-selection-01KRTZCA``) requires runtime modules
under ``src/specify_cli/`` to reach doctrine artifacts only through such
charter facades.

This file is a **pure re-export** module — no behaviour, no wrappers, no
type aliases.
"""

from doctrine.artifact_kinds import ArtifactKind
from doctrine.drg import load_graph, merge_layers
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.query import ResolvedContext, resolve_context

__all__ = [
    "ArtifactKind",
    "DRGEdge",
    "DRGGraph",
    "DRGNode",
    "NodeKind",
    "Relation",
    "ResolvedContext",
    "load_graph",
    "merge_layers",
    "resolve_context",
]
