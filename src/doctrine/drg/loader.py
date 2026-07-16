"""Load and merge DRG graph layers from YAML files.

Uses ``ruamel.yaml`` for round-trip safe YAML parsing.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from doctrine.drg.models import DRGGraph, DRGNode

__all__ = [
    "DRGLoadError",
    "built_in_graph_source",
    "has_graph_files",
    "load_built_in_graph",
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


def built_in_graph_source() -> Path:
    """Return the directory that ships the built-in DRG graph source.

    This is the doctrine package root, which holds the per-kind ``*.graph.yaml``
    fragments (mission #2680 sharded the former single ``graph.yaml`` monolith).
    Resolving to the *directory* -- rather than a specific ``graph.yaml`` file --
    is what let :func:`load_built_in_graph` absorb the monolith->fragment
    migration transparently, with no call-site changes, and keeps either layout
    loadable going forward.

    Resolution mirrors the doctrine-local package lookup used elsewhere in this
    package (e.g. ``agent_profiles.repository``). It deliberately does NOT import
    ``charter.catalog.resolve_doctrine_root``: doctrine sits below charter in the
    dependency graph (C-004) and must not import upward. In the dev/editable and
    packaged layouts both resolve to the same ``doctrine`` directory.
    """
    try:
        return Path(str(files("doctrine")))
    except (ModuleNotFoundError, TypeError):
        return Path(__file__).parent.parent


def load_built_in_graph() -> DRGGraph:
    """Load the shipped built-in DRG as a validated ``DRGGraph``.

    Canonical accessor for the built-in graph. Every source reader of the
    shipped graph routes through this one seam, which is what let the
    monolith->fragment migration (mission #2680) be a single change here instead
    of a scattered edit across ~22 call sites. Delegates to
    :func:`load_graph_or_dir` on :func:`built_in_graph_source`, which prefers a
    single ``graph.yaml`` when present and otherwise merges the shipped
    ``*.graph.yaml`` fragments alphabetically.

    Raises :class:`DRGLoadError` when no graph source can be loaded (the callers
    that must degrade rather than crash catch this themselves).
    """
    return load_graph_or_dir(built_in_graph_source())


def merge_layers(
    built_in: DRGGraph,
    project: DRGGraph | None,
) -> DRGGraph:
    """Merge *built_in* and *project* graph layers.

    Semantics (additive only):

    * All nodes from *built_in* are kept.
    * Nodes in *project* with new URNs are added.
    * Nodes in *project* whose URN already exists in *built_in* override the
      label (but kind is retained from built-in).
    * All edges from both layers are combined (additive, no removal).

    Returns a new ``DRGGraph`` (not yet validated -- the caller should run
    ``validate_graph()`` on the result).
    """
    if project is None:
        return built_in

    # Build node index keyed by URN
    node_index: dict[str, DRGNode] = {n.urn: n for n in built_in.nodes}

    for pn in project.nodes:
        if pn.urn in node_index:
            # Override label only -- keep built-in kind
            existing = node_index[pn.urn]
            node_index[pn.urn] = existing.model_copy(
                update={"label": pn.label} if pn.label is not None else {}
            )
        else:
            node_index[pn.urn] = pn

    # Combine edges (additive)
    merged_edges = list(built_in.edges) + list(project.edges)

    return DRGGraph(
        schema_version=built_in.schema_version,
        generated_at=built_in.generated_at,
        generated_by=built_in.generated_by,
        nodes=list(node_index.values()),
        edges=merged_edges,
    )
