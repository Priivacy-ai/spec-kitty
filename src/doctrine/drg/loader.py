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

__all__ = [
    "DRGLoadError",
    "has_graph_files",
    "load_graph",
    "load_graph_or_dir",
    "merge_layers",
]


class DRGLoadError(Exception):
    """Raised when a graph YAML file cannot be loaded or validated."""


def has_graph_files(path: Path) -> bool:
    """Return True iff *path* contains a graph file the DRG loader recognises.

    The DRG loader treats either ``graph.yaml`` (single-file layout) or
    one or more ``*.graph.yaml`` fragments as a valid graph source. A
    directory that exists but contains only sub-trees (eg ``overlays/``)
    is NOT a valid graph source and ``load_graph_or_dir`` would raise
    ``DRGLoadError`` on it. Callers that treat a project overlay as
    optional should guard with this helper.
    """
    if not path.is_dir():
        return False
    if (path / "graph.yaml").is_file():
        return True
    return any(path.glob("*.graph.yaml"))


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


def load_graph_or_dir(path: Path) -> DRGGraph:
    """Load a ``DRGGraph`` from a file or directory.

    If *path* is a file, delegates to :func:`load_graph`.
    If *path* is a directory, loads ``graph.yaml`` when present for backward
    compatibility; otherwise, loads ``*.graph.yaml`` fragments alphabetically
    and merges them left-to-right with :func:`merge_layers`.

    Raises :class:`DRGLoadError` if the path does not exist, is not a file or
    directory, or if no graph file can be found in a directory.
    """
    if path.is_file():
        return load_graph(path)

    if not path.exists():
        raise DRGLoadError(f"Path not found: {path}")

    if not path.is_dir():
        raise DRGLoadError(f"Path is not a file or directory: {path}")

    single_graph = path / "graph.yaml"
    if single_graph.is_file():
        return load_graph(single_graph)

    fragment_paths = sorted(path.glob("*.graph.yaml"))
    if not fragment_paths:
        raise DRGLoadError(f"No DRG graph files found in directory: {path}")

    graph = load_graph(fragment_paths[0])
    for fragment_path in fragment_paths[1:]:
        graph = merge_layers(graph, load_graph(fragment_path))
    return graph


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
