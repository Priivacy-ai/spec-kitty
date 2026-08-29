"""Action-doctrine bundle resolution (WP06 T029, #2532).

Relocated verbatim from ``charter.activation.context`` (single-owner, no-net-growth for
that file). Resolves DRG-backed action doctrine artifacts for a given
``(action, mission_type/feature_dir)`` pair into an :class:`_ActionDoctrineBundle`
— the payload both the bootstrap-text renderer and the ``--json`` entrypoint
consume.

Cycle note: ``_build_doctrine_service`` and ``_normalize_directive_id`` are
imported function-locally / from their sibling homes respectively; the
former stays routed through ``charter.activation.context`` (the single test-patchable
seam every other builder-consuming module already uses — see
``context_renderers/compact_governance.py``'s cycle note for the
established precedent) rather than importing
``charter.activation.doctrine_service_builder`` directly, so patching
``charter.activation.context._build_doctrine_service`` continues to redirect every
caller, moved or not.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from charter.activation.pack_context import PackContext
    from charter.offering.drg.models import DRGGraph
    import charter.offering.service as _doctrine_service_module

from charter.activation.org_pack_discovery import _load_doctrine_selection
from charter.activation.profile_resolution import _normalize_directive_id

__all__ = [
    "_ActionDoctrineBundle",
    "_load_action_doctrine_bundle",
    "_resolve_action_bundle",
]


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ActionDoctrineBundle:
    """Resolved action doctrine artifacts for bootstrap rendering.

    ``procedure_ids``/``asset_ids`` are WP10 additions (FR-009/FR-011); ``mission``
    and ``service`` are kept though the contract sketch omits them.
    """

    mission: str
    directive_ids: list[str]
    tactic_ids: list[str]
    styleguide_ids: list[str]
    toolguide_ids: list[str]
    procedure_ids: list[str]
    asset_ids: list[str]
    service: _doctrine_service_module.DoctrineService
    # WP15 (progressive disclosure, out-of-map): the resolved DRG and the
    # traversal roots, carried so the JSON entrypoint can render each artefact's
    # ``references[]`` and split the requires-eager / suggests-linked cadence
    # without re-loading and re-filtering the graph.
    merged: DRGGraph | None = None
    roots: tuple[str, ...] = ()
    # WP15/D2a: every URN actually visited while resolving the action node
    # (``resolve_context``'s raw ``artifact_urns``, before the NodeKind
    # delivery table drops never-delivered kinds like ``paradigm``). Carried
    # separately from ``roots`` so progressive disclosure can use excluded-kind
    # pass-through hops as reference sources without widening the
    # requires-eager/inline set (see ``progressive_disclosure.link_references``
    # ``bridge_urns``).
    bridge_urns: tuple[str, ...] = ()


def _resolve_action_bundle(
    repo_root: Path,
    *,
    action: str,
    effective_depth: int,
    org_root: Path | None,
    mission_type: str | None,
    feature_dir: Path | None,
) -> _ActionDoctrineBundle:
    """Resolve the action doctrine bundle with the WP06 org-root fallback
    (extracted WP11/T060 so every-load delivery computes it once, before the
    depth-tier branch, without growing ``build_charter_context``).

    #3525 Fold B: when the caller does not supply an explicit *org_root*
    override, the fallback now resolves the FULL declaration-ordered chain
    of existing org packs (not just the first) and threads it through as
    *org_roots* — closing the same first-match-wins gap fixed in
    ``mission_step_contracts/executor.py``. An explicit *org_root* override
    (e.g. a ``--org-root``-driven single-path caller) is honoured verbatim
    and does not widen into the chain.
    """
    effective_org_root = org_root
    effective_org_roots: list[Path] | None = None
    if effective_org_root is None:
        from charter.offering.drg.org_pack_config import resolve_existing_org_roots  # noqa: PLC0415

        effective_org_roots = resolve_existing_org_roots(repo_root)
        if effective_org_roots:
            # Legacy single-root field, kept for org_root-only callers/back-compat
            # (e.g. any consumer of ``_ActionDoctrineBundle`` that still expects a
            # single representative root); the DRG merge itself uses the full
            # ``effective_org_roots`` chain below, not this single value.
            effective_org_root = effective_org_roots[0]

    from charter.activation.pack_context import PackContext as _PackContext  # noqa: PLC0415

    return _load_action_doctrine_bundle(
        repo_root=repo_root,
        action=action,
        effective_depth=effective_depth,
        org_root=effective_org_root,
        org_roots=effective_org_roots,
        pack_context=_PackContext.from_config(repo_root),
        mission_type=mission_type,
        feature_dir=feature_dir,
    )


def _load_action_doctrine_bundle(
    *,
    repo_root: Path,
    action: str,
    effective_depth: int,
    org_root: Path | None = None,
    org_roots: list[Path] | None = None,
    pack_context: PackContext | None = None,
    mission_type: str | None = None,
    feature_dir: Path | None = None,
) -> _ActionDoctrineBundle:
    """Load DRG-backed action doctrine artifacts for bootstrap rendering.

    The mission type keying off which the ``action:<mission_type>/<action>``
    node is resolved comes from ``meta.json`` (via ``feature_dir``) or an
    explicit ``mission_type`` argument — NEVER from the project-level
    ``template_set`` (the #883 leak, WP04 / FR-002).  ``template_set`` is
    retained solely for template-file selection (C-004) and no longer proxies
    the mission type on this governance path.

    A typeless mission (no ``mission_type`` and no ``meta.json`` type — the
    genuinely mission-less callers) degrades to an EMPTY action bundle; it is
    never resolved as software-dev (FR-003a).

    #3525 Fold B: *org_roots*, when supplied, carries the full
    declaration-ordered org-pack chain and is threaded straight through to
    :func:`charter.activation._drg_helpers.load_validated_graph` (which prefers it over
    *org_root*) AND to the ``DoctrineService`` built below — both halves now
    see every configured pack, not just *org_root*'s single representative
    entry. Callers that only ever supplied *org_root* (no chain resolved)
    keep the pre-fix single-root behaviour byte-identical.
    """
    from charter.activation._drg_helpers import load_validated_graph
    from charter.activation.context import _build_doctrine_service  # noqa: PLC0415
    from charter.activation.context_renderers.delivery_table import _classify_artifact_urns
    from charter.drg import filter_graph_by_activation
    from charter.activation.mission_type_profiles import resolve_mission_type_key
    from charter.offering.drg.loader import DRGLoadError
    from charter.offering.drg.query import resolve_context

    doctrine_selection = _load_doctrine_selection(repo_root)
    resolved_type = resolve_mission_type_key(
        mission_type=mission_type, feature_dir=feature_dir
    )
    project_directives = {_normalize_directive_id(d) for d in doctrine_selection.selected_directives}
    selected_tactics = {t for t in doctrine_selection.selected_tactics if t}
    selected_paradigms = {p for p in doctrine_selection.selected_paradigms if p}

    # The DRG load honours the built-in + org + project three-layer overlay
    # (WP07 T034; charter-internal callers pass org_root=None for two layers).
    # A project authoring a doctrine artifact without a sibling ``*.graph.yaml``
    # raises ``DRGLoadError``; that is orthogonal to charter-level selection
    # rendering, so we collapse it to an empty bundle and log a WARNING (WP04).
    ids_by_slot: Mapping[str, tuple[str, ...]] = {}
    merged_graph: DRGGraph | None = None
    roots: tuple[str, ...] = ()
    bridge_urns: tuple[str, ...] = ()
    # A typeless mission has no action:<type>/<action> node to resolve; skip the
    # DRG action resolution entirely so no doctrine is inferred (FR-003a).
    if resolved_type is not None:
        try:
            merged = load_validated_graph(repo_root, org_root=org_root, org_roots=org_roots)
            # FR-032, FR-035 (WP08): apply activation filter before resolving context.
            if pack_context is not None:
                merged = filter_graph_by_activation(merged, pack_context)
            action_urn = f"action:{resolved_type}/{action}"
            resolved = resolve_context(merged, action_urn, depth=effective_depth)
            ids_by_slot = _classify_artifact_urns(
                resolved.artifact_urns,
                merged,
                project_directives,
                selected_tactics,
                selected_paradigms,
            )
            # WP15: carry the graph + traversal roots for progressive disclosure.
            # Roots mirror ``_classify_artifact_urns``: the action node plus the
            # project/selected start URNs whose requires-closure is delivered eager.
            merged_graph = merged
            roots = (
                action_urn,
                *(f"directive:{d}" for d in project_directives),
                *(f"tactic:{t}" for t in selected_tactics),
                *(f"paradigm:{p}" for p in selected_paradigms),
            )
            # D2a: ``resolve_context``'s raw ``artifact_urns`` can reach a
            # delivered (slotted) artefact only through a node of an
            # excluded kind (e.g. ``paradigm:brownfield-onboarding``
            # ``suggests``-> ``tactic:test-to-system-reconstruction``, with no
            # paradigm selected). ``_classify_artifact_urns`` correctly never
            # delivers the paradigm itself, but that leaves it out of both
            # ``roots`` and ``delivered`` — so ``link_references`` can never
            # walk its outbound edge and the tactic ends up delivered yet
            # neither inlined nor named, silently. Carrying the raw resolved
            # set as bridge URNs restores it as a reference source without
            # making it delivered or inline.
            bridge_urns = tuple(resolved.artifact_urns)
        except DRGLoadError as exc:
            _LOGGER.warning(
                "DRG action resolution skipped for %s/%s: %s. "
                "Charter-level selections still render.",
                resolved_type,
                action,
                exc,
            )

    return _ActionDoctrineBundle(
        mission=resolved_type or "",
        directive_ids=list(ids_by_slot.get("directives", ())),
        tactic_ids=list(ids_by_slot.get("tactics", ())),
        styleguide_ids=list(ids_by_slot.get("styleguides", ())),
        toolguide_ids=list(ids_by_slot.get("toolguides", ())),
        procedure_ids=list(ids_by_slot.get("procedures", ())),
        asset_ids=list(ids_by_slot.get("assets", ())),
        service=_build_doctrine_service(
            repo_root,
            org_roots=org_roots if org_roots else ([org_root] if org_root else None),
        ),
        merged=merged_graph,
        roots=roots,
        bridge_urns=bridge_urns,
    )
