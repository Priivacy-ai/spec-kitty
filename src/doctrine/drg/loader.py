"""Load and merge DRG graph layers from YAML files.

Uses ``ruamel.yaml`` for round-trip safe YAML parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from doctrine.drg.models import DRGGraph, DRGNode


class DRGLoadError(Exception):
    """Raised when a graph YAML file cannot be loaded or validated."""


def load_graph(path: Path) -> DRGGraph:
    """Read *path* as YAML and return a validated ``DRGGraph``.

    Raises :class:`DRGLoadError` on missing file, YAML parse error, or
    Pydantic validation error.
    """
    if not path.exists():
        raise DRGLoadError(f"File not found: {path}")

    yaml = YAML(typ="safe")
    try:
        data: Any = yaml.load(path)
    except YAMLError as exc:
        raise DRGLoadError(f"YAML parse error in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise DRGLoadError(f"Expected a YAML mapping at top level in {path}")

    try:
        return DRGGraph.model_validate(data)
    except ValidationError as exc:
        raise DRGLoadError(
            f"Validation error in {path}: {exc}"
        ) from exc


def merge_layers(
    shipped: DRGGraph,
    project: DRGGraph | None,
) -> DRGGraph:
    """Merge *shipped* and *project* graph layers.

    Semantics (additive only):

    * All nodes from *shipped* are kept.
    * Nodes in *project* with new URNs are added.
    * Nodes in *project* whose URN already exists in *shipped* override the
      label (but kind is retained from shipped).
    * All edges from both layers are combined (additive, no removal).

    Returns a new ``DRGGraph`` (not yet validated -- the caller should run
    ``validate_graph()`` on the result).
    """
    if project is None:
        return shipped

    # Build node index keyed by URN
    node_index: dict[str, DRGNode] = {n.urn: n for n in shipped.nodes}

    for pn in project.nodes:
        if pn.urn in node_index:
            # Override label only -- keep shipped kind
            existing = node_index[pn.urn]
            node_index[pn.urn] = existing.model_copy(
                update={"label": pn.label} if pn.label is not None else {}
            )
        else:
            node_index[pn.urn] = pn

    # Combine edges (additive)
    merged_edges = list(shipped.edges) + list(project.edges)

    return DRGGraph(
        schema_version=shipped.schema_version,
        generated_at=shipped.generated_at,
        generated_by=shipped.generated_by,
        nodes=list(node_index.values()),
        edges=merged_edges,
    )
