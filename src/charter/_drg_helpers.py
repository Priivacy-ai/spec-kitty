"""Shared DRG graph-load helpers for charter resolver and compiler.

Introduced in WP03 of the
``excise-doctrine-curation-and-inline-references-01KP54J6`` mission so that
``src/charter/resolver.py`` and ``src/charter/compiler.py`` no longer
duplicate the built-in+project merge/validate sequence.

Updated in WP03 of ``layered-doctrine-org-layer-01KRNPEE`` to add
``_resolve_org_root()`` and perform three-layer (built-in → org → project)
DRG merging in ``load_validated_graph()``.

Architectural note
------------------
``charter`` sits below ``specify_cli`` in the dependency hierarchy::

    kernel (root) <- doctrine <- charter <- specify_cli

``_resolve_org_root()`` therefore cannot import ``specify_cli`` directly.  The
charter-layer implementation always returns ``None`` (no-config fallback).
Callers in ``specify_cli`` that need config-aware org-root resolution should
resolve the path themselves and pass it explicitly as the *org_root* argument
to :func:`load_validated_graph`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from doctrine.drg.loader import (
    DRGLoadError,
    has_graph_files,
    load_built_in_graph,
    load_graph_or_dir,
    merge_layers,
)
from doctrine.drg.models import DRGEdge, DRGGraph
from doctrine.drg.validator import assert_valid, duplicate_edge_triples


class OrgDRGFragmentError(Exception):
    """Raised when org-layer DRG content (root graph or drg/ fragment) is
    malformed.

    Deliberately NOT a ``DRGLoadError`` subclass, so it is left uncaught by
    the existing wide ``except DRGLoadError`` in
    ``charter.action_doctrine_bundle._load_action_doctrine_bundle`` and
    propagates to the CLI's generic exception boundary (``charter context``'s
    ``except Exception``), which already reports it as a structurally
    distinguishable failure. Scoped strictly to the org branch (root graph or
    ``drg/`` fragment, loaded by :func:`_load_org_layer`) -- the project-layer
    ``.kittify/doctrine`` load elsewhere in :func:`load_validated_graph` is
    unaffected and continues to raise (and be swallowed as) plain
    ``DRGLoadError``.
    """


def _load_org_root_graph(org_root: Path) -> DRGGraph:
    """Load the root-level org graph, wrapping a malformed load in
    :class:`OrgDRGFragmentError` (IC-03)."""
    try:
        return load_graph_or_dir(org_root)
    except DRGLoadError as exc:
        raise OrgDRGFragmentError(
            f"Malformed org DRG root graph at {org_root}: {exc}"
        ) from exc


def _load_org_drg_fragment(drg_dir: Path) -> DRGGraph:
    """Load the ``drg/`` org fragment, wrapping a malformed load in
    :class:`OrgDRGFragmentError` (IC-03)."""
    try:
        return load_graph_or_dir(drg_dir)
    except DRGLoadError as exc:
        raise OrgDRGFragmentError(
            f"Malformed org DRG drg/ fragment at {drg_dir}: {exc}"
        ) from exc


def _edge_triple(edge: DRGEdge) -> tuple[str, str, str]:
    """The ``(source, target, relation)`` identity :func:`duplicate_edge_triples`
    (C-001) groups edges by -- factored out so :func:`_dedup_org_layer_edges`
    can re-key ``graph.edges`` by the same triple without re-deriving it."""
    return (edge.source, edge.target, edge.relation.value)


def _group_edges_by_triple(
    edges: Sequence[DRGEdge],
) -> dict[tuple[str, str, str], list[DRGEdge]]:
    """Group *edges* by :func:`_edge_triple` in a single pass, preserving each
    triple's occurrences in their original relative order -- the single-scan
    replacement for repeatedly re-filtering ``graph.edges`` per duplicated
    triple (PR-FRESH2-001: that re-filter made the org-layer merge O(n^2))."""
    grouped: dict[tuple[str, str, str], list[DRGEdge]] = {}
    for edge in edges:
        grouped.setdefault(_edge_triple(edge), []).append(edge)
    return grouped


def _dedup_org_layer_edges(
    graph: DRGGraph,
    *,
    root_edges: Sequence[DRGEdge],
    drg_edges: Sequence[DRGEdge],
) -> DRGGraph:
    """Collapse a (source, target, relation) triple to one retained edge ONLY
    when it appears EXACTLY ONCE in each org-layer source (the root graph and
    the ``drg/`` fragment) -- a genuine cross-source overlap (FR-003).

    Required semantics (pinned by the PR-FRESH-001 regression tests in
    ``tests/charter/test_org_root_graph_guard.py``):

    - If **any single source** contains the triple **two or more times**, it
      is a within-source authoring bug -- possibly alongside an unrelated
      single occurrence in the other source. Every occurrence of that triple
      is left alone, so it keeps reaching the final
      ``assert_valid``/``DRGValidationError`` exactly as it did before this
      mission. Collapsing it here would silently absorb a real defect
      (this was the FRESH-001 bug: classifying by comparison to the FIRST
      occurrence's source alone treated every later occurrence -- including
      a same-source duplicate -- as "cross-source" the moment it differed
      from that first source, so 1x root + 2x drg/ dropped BOTH drg/
      copies instead of leaving them for validation).
    - Only when each source has **at most one** occurrence AND the triple
      appears in **both** sources does it collapse to exactly one retained
      edge.

    *root_edges*/*drg_edges* are the edge lists of the two pre-merge source
    graphs. :func:`~doctrine.drg.loader.merge_layers` combines edges via
    plain list concatenation (no copying), so every edge object in *graph*
    is identity-preserved from one of these two lists -- used here only to
    classify which source a given edge came from, not to redefine what
    counts as a duplicate triple.

    Reuses the canonical :func:`duplicate_edge_triples` definition of
    "duplicate" (C-001) to find every triple with a 2nd+ occurrence; the
    per-source occurrence count is a provenance check layered on top of that
    result, not a redefinition of it.

    Filters by object identity (``id(e)``), not value/triple equality:
    ``DRGEdge`` has no custom ``__eq__``, so two identical-triple edges with
    unset ``when``/``reason``/``provenance`` are pydantic-value-equal to each
    other -- a value-equality filter would drop *both* copies, leaving zero
    retained edges instead of the required exactly one.
    """
    root_ids = frozenset(id(edge) for edge in root_edges)
    drg_ids = frozenset(id(edge) for edge in drg_edges)

    def _source_of(edge: DRGEdge) -> str:
        if id(edge) in root_ids:
            return "root"
        if id(edge) in drg_ids:
            return "drg"
        raise AssertionError(  # pragma: no cover -- see docstring: unreachable
            f"edge {edge!r} is not identity-present in either org-layer source"
        )

    duplicated_triples = {_edge_triple(edge) for edge in duplicate_edge_triples(graph)}
    edges_by_triple = _group_edges_by_triple(graph.edges)

    edges_dropped_by_id: set[int] = set()
    for triple in duplicated_triples:
        occurrences = edges_by_triple[triple]
        sources = [_source_of(edge) for edge in occurrences]
        if sources.count("root") == 1 and sources.count("drg") == 1:
            # Exactly one occurrence in each source: a genuine cross-source
            # overlap. Collapse to exactly one retained edge by dropping the
            # drg/ occurrence (matches the pre-existing root-authoritative
            # retention behaviour for this case).
            drg_occurrence = occurrences[sources.index("drg")]
            edges_dropped_by_id.add(id(drg_occurrence))
        # Otherwise a source has >=2 occurrences (a within-source authoring
        # bug) -- leave every occurrence alone so it still reaches the final
        # assert_valid.

    deduped_edges = [edge for edge in graph.edges if id(edge) not in edges_dropped_by_id]
    return graph.model_copy(update={"edges": deduped_edges})


def _load_org_layer(org_root: Path) -> DRGGraph | None:
    """Load org-pack DRG content from *org_root* and/or *org_root*/drg/.

    Returns ``None`` when neither location has a recognisable graph file
    (the "no org DRG layer" case). Guards the FR-001 P0 zeroing: today's
    unconditional ``load_graph_or_dir(org_root)`` raises ``DRGLoadError``
    on a directory with no root-level graph, even when a guide-compliant
    ``drg/*.graph.yaml`` fragment sits alongside it.

    When both a root-level graph and a ``drg/`` fragment are present, they
    are merged via :func:`merge_layers` (root as ``built_in``, ``drg/`` as
    ``project`` -- ``drg/`` wins on same-URN node-label conflicts) and any
    edge triple duplicated identically across the two sources (one
    occurrence in the root graph, one in the ``drg/`` fragment) is collapsed
    to exactly one retained copy via :func:`_dedup_org_layer_edges` (FR-003,
    IC-02). A triple duplicated within a single source is a same-file
    authoring bug, not a cross-source merge artifact -- it is left alone
    here and still raises ``DRGValidationError`` at the final
    ``assert_valid`` in :func:`load_validated_graph`, exactly as it did
    before this mission.

    Malformed content (invalid YAML or schema-invalid) at either location
    raises :class:`OrgDRGFragmentError` (FR-004, IC-03). The root-level load
    and the ``drg/``-level load are each wrapped *independently* -- via the
    two single-purpose helpers below, never a shared ``try`` block -- so a
    malformed root graph does not take a valid, loadable sibling ``drg/``
    fragment down with it.
    """
    drg_dir = org_root / "drg"
    has_root_graph = has_graph_files(org_root)
    has_drg_layer = has_graph_files(drg_dir)

    if not has_root_graph and not has_drg_layer:
        return None
    if not has_drg_layer:
        return _load_org_root_graph(org_root)
    if not has_root_graph:
        return _load_org_drg_fragment(drg_dir)
    root_graph = _load_org_root_graph(org_root)
    drg_graph = _load_org_drg_fragment(drg_dir)
    merged_org = merge_layers(root_graph, drg_graph)
    return _dedup_org_layer_edges(
        merged_org, root_edges=root_graph.edges, drg_edges=drg_graph.edges
    )


def _resolve_org_root(_repo_root: Path) -> Path | None:
    """Return the configured org doctrine snapshot path, or ``None`` if absent.

    The charter-layer implementation is intentionally inert — it always returns
    ``None``.  The ``repo_root`` parameter is accepted for API compatibility;
    callers in ``specify_cli`` are expected to resolve the org root themselves
    (e.g. via ``specify_cli.doctrine.config``) and supply it explicitly to
    :func:`load_validated_graph`.

    This design keeps the ``charter`` package free of ``specify_cli`` imports,
    satisfying the architectural boundary enforced by
    ``tests/architectural/test_layer_rules.py``.
    """
    return None


def load_validated_graph(
    repo_root: Path,
    org_root: Path | None = None,
    *,
    org_roots: list[Path] | None = None,
) -> DRGGraph:
    """Load the built-in + org-chain + project DRG overlay and validate the result.

    Performs a chain-aware merge (#3525 Fold B — the multi-org-pack DRG fix):

    1. **built-in** — bundled graph bundled with the ``doctrine`` package.
    2. **org chain** — zero or more organisation-level snapshots, folded in
       DECLARATION ORDER with later-declared-wins precedence on URN
       collision (``merge_layers`` overrides ``label`` only; ``kind`` is
       retained from the earlier layer — the existing single-org semantics,
       unchanged). This mirrors the repository overlay's established
       precedence (``doctrine.base._apply_overlay_layer``,
       ``charter.org_expected_artifacts``) rather than the pre-fix
       first-match-wins behaviour that only ever folded pack #1. A root that
       does not exist on disk is silently skipped here; callers that need a
       WARNING per dropped root should pre-filter via
       :func:`doctrine.drg.org_pack_config.resolve_existing_org_roots` —
       every production caller now does.
    3. **project** — optional per-project overlay at
       ``<repo_root>/.kittify/doctrine``.

    Args:
        repo_root: Project root; used to locate the project overlay at
            ``<repo_root>/.kittify/doctrine``.
        org_root: Back-compat single-root override. When *org_roots* is not
            supplied, this is normalised to a one-element list (or the
            no-config fallback via :func:`_resolve_org_root`, which the
            charter-layer implementation always resolves to ``None``).
            Charter-build-time callers (``compiler.py``, ``consistency_check.py``,
            ``reference_resolver.py``, ``glossary/drg_builder.py``,
            ``invocation_context.py``) pass neither *org_root* nor
            *org_roots* — they stay intentionally org-inert (charter build/
            validation is not runtime org overlay), so they compile and run
            unchanged against this signature.
        org_roots: The full, declaration-ordered chain of configured org
            doctrine roots (#3525). Preferred over *org_root* for every
            caller that resolves the project's configured org packs — pass
            :func:`doctrine.drg.org_pack_config.resolve_existing_org_roots`'s
            result. When *org_roots* is supplied (even as an empty list), it
            takes precedence over *org_root* — passing ``org_roots=[]``
            explicitly means "no org layer", distinct from omitting the
            argument (which falls back to *org_root*).

    Returns:
        A validated :class:`DRGGraph`.

    Raises:
        ValueError: If :func:`assert_valid` rejects the merged graph
            (dangling edges, duplicate edges, or ``requires`` cycles).
    """
    if org_roots is not None:
        roots = org_roots
    else:
        if org_root is None:
            org_root = _resolve_org_root(repo_root)
        roots = [org_root] if org_root else []

    merged = load_built_in_graph()
    for root in roots:
        if not root or not root.exists():
            continue
        # Rebase resolution (#3401 x #3520): the chain loop is #3520's, the
        # per-root guard is this branch's. `_load_org_layer` returns None for a
        # root with no recognisable graph in either `<root>/` or `<root>/drg/`,
        # so a pack that ships artifacts but no graph degrades to "no org DRG
        # layer" instead of raising DRGLoadError -- applied to EVERY root in the
        # chain, not just the first.
        org_layer = _load_org_layer(root)
        if org_layer is not None:
            merged = merge_layers(merged, org_layer)

    project_dir = repo_root / ".kittify" / "doctrine"
    project = (
        load_graph_or_dir(project_dir)
        if has_graph_files(project_dir)
        else None
    )

    merged = merge_layers(merged, project)
    assert_valid(merged)
    return merged


__all__ = [
    "load_validated_graph",
]
