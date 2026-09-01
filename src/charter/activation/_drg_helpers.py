"""Shared DRG graph-load helpers for charter resolver and compiler.

Introduced in WP03 of the
``excise-doctrine-curation-and-inline-references-01KP54J6`` mission so that
``src/charter/activation/resolver.py`` and ``src/charter/activation/compiler.py`` no longer
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

import logging
from pathlib import Path

from charter.offering.drg.loader import (
    has_graph_files,
    load_built_in_graph,
    load_graph_or_dir,
    merge_layers,
)
from charter.offering.drg.merge import merge_three_layers
from charter.offering.drg.models import DRGEdge, DRGGraph
from charter.offering.drg.org_pack_loader import OrgDRGFragment
from charter.offering.drg.validator import assert_valid

_LOGGER = logging.getLogger(__name__)


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
    org_fragments: list[OrgDRGFragment] | None = None,
) -> DRGGraph:
    """Load the built-in + org-chain + project DRG overlay and validate the result.

    Performs a chain-aware merge (#3525 Fold B — the multi-org-pack DRG fix):

    1. **built-in** — bundled graph bundled with the ``doctrine`` package.
    2. **org chain** — zero or more organisation-level snapshots, folded in
       DECLARATION ORDER with later-declared-wins precedence on URN
       collision (``merge_layers`` overrides ``label`` only; ``kind`` is
       retained from the earlier layer — the existing single-org semantics,
       unchanged). This mirrors the repository overlay's established
       precedence (``charter.offering.base._apply_overlay_layer``,
       ``charter.activation.org_expected_artifacts``) rather than the pre-fix
       first-match-wins behaviour that only ever folded pack #1. A root that
       does not exist on disk is silently skipped here; callers that need a
       WARNING per dropped root should pre-filter via
       :func:`charter.offering.drg.org_pack_config.resolve_existing_org_roots` —
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
            :func:`charter.offering.drg.org_pack_config.resolve_existing_org_roots`'s
            result. When *org_roots* is supplied (even as an empty list), it
            takes precedence over *org_root* — passing ``org_roots=[]``
            explicitly means "no org layer", distinct from omitting the
            argument (which falls back to *org_root*).
        org_fragments: The org ``drg/fragment.yaml`` layer, resolved by the
            runtime caller. When supplied, fragment edges are folded through
            :func:`charter.offering.drg.merge.merge_three_layers`; when omitted,
            the legacy two-layer merge is byte-behaviourally unchanged.

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

    root_merged = load_built_in_graph()
    for root in roots:
        # An org root that ships a root-level DRG graph (`graph.yaml` or
        # `*.graph.yaml`) contributes its charter-DRG layer; one that is
        # present-but-malformed still fails loud inside `load_graph_or_dir`.
        if root and root.exists() and has_graph_files(root):
            root_merged = merge_layers(root_merged, load_graph_or_dir(root))
            continue
        # A configured, on-disk org root with NO root-level DRG graph
        # contributes no charter-DRG layer. Degrade it to "no org DRG layer"
        # instead of crashing the whole load with `DRGLoadError: No DRG graph
        # files found`, so cascade activation from a pack that carries only
        # doctrine artifacts still works and one graphless pack no longer takes
        # its healthy sibling roots down. This is the durable per-root-degrade
        # sliver of the superseded #3401, retargeted to the #3387 org model.
        #
        # SCOPE (post DRG read-path bridge). Charter runtime callers can read
        # two org shapes: root-level `*.graph.yaml` here, and
        # `drg/fragment.yaml` edges through `org_fragments` below. A pack
        # shipping only a fragment is not graphless for a caller that supplies
        # that fragment layer; for a caller that omits it, the fragment remains
        # invisible and must still be disclosed.
        #
        # D-005 ("degrade, but never silent"), matching the per-root warning
        # `mission_step_contracts.executor._load_graph_degrading_malformed_org_pack`
        # emits for the same shape. Executor / action-bundle callers pre-filter
        # or never reach this branch, so this does not double-warn them; the
        # `activate` / `deactivate` / `gate_bindings` callers — which do not
        # pre-probe — get their only signal here.
        fragment_exists = bool(root) and root.exists() and (root / "drg" / "fragment.yaml").exists()
        if root and root.exists() and (not fragment_exists or org_fragments is None):
            missing_shape = (
                "and no drg/fragment.yaml"
                if not fragment_exists
                else "but this call supplied no org_fragments layer"
            )
            _LOGGER.warning(
                "Org pack at %s ships no root-level DRG graph "
                "(graph.yaml / *.graph.yaml) %s; it contributes no dependency "
                "graph to cascade and was skipped. Author a root-level "
                "*.graph.yaml, or supply its drg/fragment.yaml through "
                "org_fragments, to contribute requires/suggests edges.",
                root,
                missing_shape,
            )

    project_dir = repo_root / ".kittify" / "doctrine"
    project = (
        load_graph_or_dir(project_dir)
        if has_graph_files(project_dir)
        else None
    )

    merged = _fold_final_layers(root_merged, org_fragments, project)
    assert_valid(merged)
    return merged


def _fold_final_layers(
    root_merged: DRGGraph,
    org_fragments: list[OrgDRGFragment] | None,
    project: DRGGraph | None,
) -> DRGGraph:
    """Fold project and optional org fragments without forking edge identity."""
    if org_fragments:
        merged = merge_three_layers(
            built_in=root_merged, org_fragments=org_fragments, project=project
        )
        return _collapse_duplicate_edge_triples(merged)
    return merge_layers(root_merged, project)


def _collapse_duplicate_edge_triples(graph: DRGGraph) -> DRGGraph:
    """Collapse exact duplicate edges produced by dual root/fragment folding."""
    seen: set[tuple[str, str, str]] = set()
    deduped: list[DRGEdge] = []
    for edge in graph.edges:
        key = (edge.source, edge.target, edge.relation.value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(edge)
    if len(deduped) == len(graph.edges):
        return graph
    return graph.model_copy(update={"edges": deduped})


__all__ = [
    "load_validated_graph",
]
