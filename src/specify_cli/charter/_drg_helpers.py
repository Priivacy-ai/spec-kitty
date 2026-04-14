"""Shared DRG graph-load helpers (``specify_cli`` twin).

Mirrors :mod:`charter._drg_helpers` for lockstep with the twin charter
package (plan D-3 of the
``excise-doctrine-curation-and-inline-references-01KP54J6`` mission). The
twin currently has no in-package caller but the helper exists here so any
future ``src/specify_cli/charter/`` code that needs the merged+validated
DRG uses the same entry point.
"""

from __future__ import annotations

from pathlib import Path

from doctrine.drg.loader import load_graph, merge_layers
from doctrine.drg.models import DRGGraph
from doctrine.drg.validator import assert_valid
from specify_cli.charter.catalog import resolve_doctrine_root


def load_validated_graph(repo_root: Path) -> DRGGraph:
    """Load shipped + project merged DRG and validate it."""
    doctrine_root = resolve_doctrine_root()
    shipped = load_graph(doctrine_root / "graph.yaml")
    project_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
    project = load_graph(project_path) if project_path.exists() else None
    merged = merge_layers(shipped, project)
    assert_valid(merged)
    return merged


__all__ = ["load_validated_graph"]
