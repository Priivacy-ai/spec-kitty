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

import logging
from pathlib import Path

from charter.offering.drg.loader import (
    has_graph_files,
    load_built_in_graph,
    load_graph_or_dir,
    merge_layers,
)
from charter.offering.drg.models import DRGGraph
from charter.offering.drg.validator import assert_valid

_LOGGER = logging.getLogger(__name__)


def _resolve_org_root(_repo_root: Path) -> Path | None:
    """Return the configured org doctrine snapshot path, or ``None`` if absent.

    The charter-layer implementation is intentionally inert — it always returns
    ``None``.  The ``repo_root`` parameter is accepted for API compatibility;
    callers in ``specify_cli`` are expected to resolve the org root themselves
    (e.g. via ``specify_cli.charter.offering.config``) and supply it explicitly to
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
       precedence (``charter.offering.base._apply_overlay_layer``,
       ``charter.org_expected_artifacts``) rather than the pre-fix
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
        # An org root that ships a root-level DRG graph (`graph.yaml` or
        # `*.graph.yaml`) contributes its charter-DRG layer; one that is
        # present-but-malformed still fails loud inside `load_graph_or_dir`.
        if root and root.exists() and has_graph_files(root):
            merged = merge_layers(merged, load_graph_or_dir(root))
            continue
        # A configured, on-disk org root with NO root-level DRG graph
        # contributes no charter-DRG layer. Degrade it to "no org DRG layer"
        # instead of crashing the whole load with `DRGLoadError: No DRG graph
        # files found`, so cascade activation from a pack that carries only
        # doctrine artifacts still works and one graphless pack no longer takes
        # its healthy sibling roots down. This is the durable per-root-degrade
        # sliver of the superseded #3401, retargeted to the #3387 org model.
        #
        # SCOPE — do not overstate what cascade sees. Charter cascade reads
        # root-level `*.graph.yaml` ONLY. Edges an org pack authors solely in
        # `drg/fragment.yaml` (the #3387 `OrgDRGFragment` shape) are read only
        # by the separate diagnostic merge path (`load_org_pack` →
        # `merge_three_layers`, surfaced in `doctor doctrine` / `charter list`)
        # and are invisible to cascade — before and after this guard. That
        # `drg/fragment.yaml` gap is NOT flagged by `drg_root_graph_missing`
        # either: that finding globs `drg/*.graph.yaml` (a different shape),
        # not `fragment.yaml`. So the WARNING below is the operator's only
        # signal that a configured pack contributed nothing to cascade.
        #
        # D-005 ("degrade, but never silent"), matching the per-root warning
        # `mission_step_contracts.executor._load_graph_degrading_malformed_org_pack`
        # emits for the same shape. Executor / action-bundle callers pre-filter
        # or never reach this branch, so this does not double-warn them; the
        # `activate` / `deactivate` / `gate_bindings` callers — which do not
        # pre-probe — get their only signal here.
        if root and root.exists():
            _LOGGER.warning(
                "Org pack at %s ships no root-level DRG graph "
                "(graph.yaml / *.graph.yaml); it contributes no doctrine graph "
                "to cascade and was skipped. Any requires/suggests edges "
                "authored only in drg/fragment.yaml are not read by the "
                "cascade path.",
                root,
            )

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
