"""Charter facade for DRG (Doctrine Reference Graph) types + org layer (Slice F).

This module is the charter-layer proxy for runtime callers that historically
imported from ``doctrine.drg`` directly. The runtime → charter → doctrine
boundary (ADR 2026-03-27-1, tightened by mission
``charter-mediated-doctrine-selection-01KRTZCA``) requires runtime modules
under ``src/specify_cli/`` to reach doctrine artifacts only through such
charter facades.

This file is partly a pure re-export module — and partly the home of the
Slice F WP06 organisation-tier DRG loader (``load_org_drg``,
``merge_three_layers``, ``OrgDRGConflictError``). The org-DRG additions live
in the charter layer per the architectural constraint that anything new in the
doctrine-overlay space must be reachable by ``specify_cli`` only through
``charter``.

Schema / fragment models live in ``doctrine.drg.org_pack_loader``
(PR #1119 DDD-boundary fix): ``OrgDRGFragment``, ``OrgPackMissingError``.
Charter re-exports them here so existing ``from charter.drg import …`` call
sites remain valid without crossing the layer boundary directly.

Slice F WP06 design notes
-------------------------

The org-DRG fragment schema (``OrgDRGFragment``) intentionally uses a
simpler node/edge shape than ``doctrine.drg.models.DRGNode`` /
``DRGEdge``. The reason is C-009: the contract round-trip gate exercises
the YAML example in
``kitty-specs/<mission>/contracts/org-drg-schema.md`` which uses plural
kinds (``kind: directives``) and human-friendly fields (``id``, ``title``,
``body_path``). The built-in DRGNode uses URNs and singular enum kinds. To
satisfy both surfaces:

* Fragment-side parsing uses private node/edge models declared in
  ``doctrine.drg.org_pack_loader``. Their ``kind`` field is constrained
  to the Mission B 8-kind plural universe (C-009 binding).
* ``merge_three_layers`` bridges fragment nodes onto the built-in DRG by
  minting URNs of the form ``<singular_kind>:<id>`` (e.g. ``directive:sox-controls``).
* Provenance is threaded via the declared ``provenance`` field on the DRG
  models (FR-013, D2-revised). The merge returns a ``DRGGraph`` whose node /
  edge objects carry their ``provenance`` set through ``model_copy``;
  consumers read it directly with ``node.provenance``.

This matches data-model.md §2's stated provenance semantics
(``source: built-in | org:<pack> | project``) while honouring the
contract YAML shape that the FR-140 round-trip gate enforces.
"""

from __future__ import annotations

from pathlib import Path

from charter.pack_context import PackContext
from doctrine.artifact_kinds import ArtifactKind
from doctrine.drg import load_graph, merge_layers
from doctrine.drg.merge import (
    OrgDRGConflict,
    OrgDRGConflictError,
    UnknownRelationError,
    merge_three_layers,
)
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.org_pack_config import load_pack_registry
from doctrine.drg.org_pack_loader import (
    OrgDRGFragment,
    OrgPackMissingError,
    load_org_pack,
)
from doctrine.drg.query import ResolvedContext, resolve_context

# Canonical three-layer merge now lives in ``doctrine.drg.merge`` (WP03,
# mission ``org-doctrine-profile-integrity-activation-closure-01KT1TV1``). The
# merge is pure graph logic and must not depend on charter/specify_cli; this
# module re-exports the public names below so existing
# ``from charter.drg import merge_three_layers`` (and the conflict types) call
# sites keep working without crossing the layer boundary directly. Charter
# retains only the activation-aware filter/aggregation
# (:func:`filter_graph_by_activation`), which is a charter concern.
__all__ = [
    "ArtifactKind",
    "DRGEdge",
    "DRGGraph",
    "DRGNode",
    "NodeKind",
    "OrgDRGConflict",
    "OrgDRGConflictError",
    "OrgDRGFragment",
    "OrgPackMissingError",
    "Relation",
    "ResolvedContext",
    "UnknownRelationError",
    "filter_graph_by_activation",
    "load_graph",
    "load_org_drg",
    "merge_layers",
    "merge_three_layers",
    "resolve_context",
]

# ---------------------------------------------------------------------------
# Loader (FR-001, FR-004, NEW-1)
# ---------------------------------------------------------------------------


def load_org_drg(repo_root: Path) -> list[OrgDRGFragment]:
    """Load all configured org packs from ``.kittify/config.yaml``.

    Returns one :class:`OrgDRGFragment` per pack in declaration order.
    Layer indices are assigned ``1..N``.

    This function is project-config-aware (charter-domain): it reads the
    shared org-pack registry contract from
    :func:`doctrine.drg.org_pack_config.load_pack_registry` and resolves each
    pack's local path relative to *repo_root*. Per-pack schema parsing and
    validation is delegated to :func:`doctrine.drg.org_pack_loader.load_org_pack`.

    Parameters
    ----------
    repo_root:
        Repository root containing ``.kittify/config.yaml``. When the
        config is absent or has no ``doctrine.org`` pack entries, the
        function returns ``[]`` (NFR-001 backward compatibility — repos
        with no org packs behave identically to today).

    Raises
    ------
    OrgPackMissingError:
        When a configured pack's ``path`` does not exist on disk
        (FR-004).
    NotImplementedError:
        When a pack declares ``source: url`` or ``source: package`` —
        only ``local_path`` is shipped in this mission (NEW-1).
    """
    registry = load_pack_registry(repo_root)
    fragments: list[OrgDRGFragment] = []
    for layer_index, pack in enumerate(registry.packs, start=1):
        fragments.append(load_org_pack(pack.name, pack.effective_root(repo_root), layer_index))
    return fragments


# ---------------------------------------------------------------------------
# Merge (relocated to ``doctrine.drg.merge`` — WP03)
# ---------------------------------------------------------------------------
# The canonical three-layer merge (``merge_three_layers`` and its bridging
# helpers, plus ``OrgDRGConflict`` / ``OrgDRGConflictError`` /
# ``UnknownRelationError``) now lives in :mod:`doctrine.drg.merge`. It is pure
# graph logic with no charter/specify_cli dependency. This module imports and
# re-exports those names (see the imports + ``__all__`` above) so existing
# ``from charter.drg import merge_three_layers`` call sites keep working. Only
# the activation-aware filtering below remains charter-owned.


# ---------------------------------------------------------------------------
# Activation filter (FR-006, FR-018, WP11)
# ---------------------------------------------------------------------------
# Mission ``charter-doctrine-mission-type-configuration-01KSWJVX`` WP11.
#
# FR-018 specifies that DRG traversal is activation-filtered: only doctrine
# artifacts that are explicitly activated in the project charter are visible
# to charter-mediated resolution. "Activated" and "registered" are synonyms
# per the data-model. The filter is sourced from ``PackContext``:
#
# * ``PackContext.activated_kinds``           — plural artifact kinds the
#                                                charter has opted in to.
# * ``PackContext.activated_mission_types``   — mission type IDs the charter
#                                                has opted in to.
#
# FR-006's two-tier directive scope is honoured by this filter because
# mission-type-scoped directives (declared via ``governance_refs`` on a
# mission type) only enter the resolved set when that mission type is
# activated. Project-scoped directives (``required_directives`` from the
# top-level charter) are never gated by the activation filter — they apply
# unconditionally to every mission.
#
# CRITICAL INVARIANT (WP11 T069): the activation filter applies ONLY to
# charter-mediated resolution paths. Direct doctrine-API callers
# (``MissionTemplateRepository.get(...)``, ``service.directives.get(...)``,
# etc.) bypass this filter and continue to return non-activated artifacts.
# This is by design: non-activated artifacts are non-canonical for charter
# resolution but remain reachable on operator request.


#: Inverse of :data:`_PLURAL_TO_SINGULAR`, used to map a URN's singular kind
#: prefix (e.g. ``"directive"``) back to its plural form (e.g.
#: ``"directives"``) so the activation filter can check membership in
#: :attr:`PackContext.activated_kinds`.
_SINGULAR_TO_PLURAL: dict[str, str] = {
    "directive": "directives",
    "tactic": "tactics",
    "styleguide": "styleguides",
    "toolguide": "toolguides",
    "paradigm": "paradigms",
    "procedure": "procedures",
    "agent_profile": "agent_profiles",
    "mission_step_contract": "mission_step_contracts",
}


#: Per-kind ``PackContext`` field names for per-artifact-ID gate (FR-038, WP08).
#: Maps a singular URN kind prefix to the corresponding ``PackContext`` attribute
#: that holds the three-state frozenset of activated artifact IDs.
_SINGULAR_TO_PER_KIND_FIELD: dict[str, str] = {
    "directive":             "activated_directives",
    "tactic":                "activated_tactics",
    "styleguide":            "activated_styleguides",
    "toolguide":             "activated_toolguides",
    "paradigm":              "activated_paradigms",
    "procedure":             "activated_procedures",
    "agent_profile":         "activated_agent_profiles",
    "mission_step_contract": "activated_mission_step_contracts",
}


#: URN kind prefixes that represent mission steps. When the filter encounters
#: one of these kinds, it consults ``activated_mission_types`` (via the
#: ``_owning_mission_type`` heuristic below) instead of ``activated_kinds``.
_MISSION_STEP_SINGULAR_KINDS: frozenset[str] = frozenset({"mission_step_contract"})


def _split_urn(urn: str) -> tuple[str, str]:
    """Split ``"<kind>:<id>"`` into ``(kind, id)``.

    Returns ``(urn, "")`` when the URN is malformed (no colon). Defensive
    against hand-constructed graphs that bypass DRGNode validation —
    ``str.partition(":")`` yields ``(whole, "", "")`` in that case so the
    identifier comes back empty and the activation filter routes the node
    through the default-allow branch.
    """
    head, _sep, tail = urn.partition(":")
    return (head, tail)


def _owning_mission_type(urn: str) -> str | None:
    """Best-effort recovery of the mission type ID that owns a mission-step URN.

    Mission-step contract URNs in the doctrine universe encode the owning
    mission type as the first path segment of the identifier portion. The
    runtime layout writes contracts under
    ``doctrine/missions/<mission-type>/mission_step_contracts/...`` and the
    canonical URN form is ``mission_step_contract:<mission-type>/<id>``.

    When the URN is not in that shape (e.g. an org-pack-authored step that
    has not been bound to a built-in mission type), this returns ``None``;
    the activation filter treats such steps as project-scoped and lets them
    through. WP08 / WP09 will tighten the convention once mission-type-owned
    org packs land.
    """
    _kind, identifier = _split_urn(urn)
    if not identifier:
        return None
    head, sep, _ = identifier.partition("/")
    if not sep:
        return None
    return head


def _node_is_activated(
    node_kind: str,
    artifact_id: str,
    pack_context: PackContext,
) -> bool:
    """Return ``True`` when the artifact is visible under the activation filter.

    Parameters
    ----------
    node_kind:
        Singular URN kind prefix (e.g. ``"directive"``, ``"tactic"``).
    artifact_id:
        Identifier portion of the URN (the part after the first ``":"``).
        An empty string (malformed URN) bypasses the per-artifact-ID gate.
    pack_context:
        Activation state from the project charter.

    Decision tree:

    1. Mission-step contract nodes (``mission_step_contract:<owner>/<id>``):
       activated iff the recovered owner mission type is in
       ``activated_mission_types``. Steps that cannot be owner-attributed
       fall through to the kind filter (defensive default-allow).
    2. All other kinds: the singular URN prefix is mapped to its plural form
       and checked against ``activated_kinds``. An unknown kind (e.g. an
       extension kind not yet in :data:`_SINGULAR_TO_PLURAL`) is allowed
       through so the filter never silently swallows new artifact kinds —
       the DRG schema validator is the gatekeeper for kind legality.
    3. Per-artifact-ID gate (FR-038, WP08): after the kind-level check, the
       per-kind ``PackContext`` frozenset is consulted. ``None`` (key absent
       from config) means all IDs are allowed. ``frozenset()`` (explicit
       empty list) blocks all IDs. A non-empty frozenset gates by ID.
       An empty *artifact_id* (malformed URN) bypasses this gate
       (default-allow).
    """
    # Step 1: mission-step contract kind check.
    if node_kind in _MISSION_STEP_SINGULAR_KINDS:
        # Reconstruct the URN to reuse _owning_mission_type which expects a full URN.
        pseudo_urn = f"{node_kind}:{artifact_id}"
        owner = _owning_mission_type(pseudo_urn)
        if owner is not None:
            return owner in pack_context.activated_mission_types
        # Fall through: ownerless step relies on kind filter.

    # Step 2: kind-level gate.
    plural = _SINGULAR_TO_PLURAL.get(node_kind)
    if plural is None:
        return True
    if plural not in pack_context.activated_kinds:
        return False

    # Step 3: per-artifact-ID gate (FR-038, WP08).
    per_kind_field = _SINGULAR_TO_PER_KIND_FIELD.get(node_kind)
    if per_kind_field is not None:
        per_kind_set = getattr(pack_context, per_kind_field, None)
        # artifact_id="" (malformed URN) → bypass (default-allow)
        if per_kind_set is not None and artifact_id and artifact_id not in per_kind_set:
            return False

    return True


def filter_graph_by_activation(
    graph: DRGGraph,
    pack_context: PackContext,
) -> DRGGraph:
    """Return a copy of *graph* limited to artifacts activated in *pack_context*.

    Applies the FR-018 activation filter:

    * Mission-step contract nodes are kept only when their owning mission
      type is in :attr:`PackContext.activated_mission_types`.
    * All other artifact kinds are kept only when their plural kind is in
      :attr:`PackContext.activated_kinds`.
    * Edges are kept only when both endpoints survive node filtering. This
      preserves the graph invariant that an edge always points to a node in
      the same graph; downstream traversal code does not need to special-
      case dangling edges.

    The function never mutates *graph*; it builds a fresh :class:`DRGGraph`.

    See module docstring for the FR-006 / FR-018 binding and the WP11 T069
    invariant: this filter applies only to charter-mediated resolution.
    Direct doctrine-API callers (``DoctrineService.<repo>.get(...)``,
    ``MissionTemplateRepository.get(...)``) are exempt.
    """
    surviving_nodes = [
        n for n in graph.nodes
        if _node_is_activated(*_split_urn(n.urn), pack_context)
    ]
    surviving_urns = {n.urn for n in surviving_nodes}
    surviving_edges = [
        e
        for e in graph.edges
        if e.source in surviving_urns and e.target in surviving_urns
    ]
    # ``model_construct`` skips the URN-prefix validators on each node/edge.
    # The input *graph* was already validated upstream, and we are returning
    # a strict subset of its nodes and edges, so the output is invariant-
    # preserving by construction. Skipping revalidation also keeps the
    # filter agnostic to extension kinds (e.g. mission-step URNs whose
    # singular form may not yet be enumerated in :class:`NodeKind`).
    return DRGGraph.model_construct(
        schema_version=graph.schema_version,
        generated_at=graph.generated_at,
        generated_by=graph.generated_by,
        nodes=surviving_nodes,
        edges=surviving_edges,
    )


# ---------------------------------------------------------------------------
# WP11 T064-drg — PackContext wiring audit
# ---------------------------------------------------------------------------
# WP10 / T063 established that ``_resolve_chain()`` and ``_merge_chain()`` in
# ``specify_cli.doctrine.org_charter`` are config-clean: they operate on the
# ``pack_set`` argument and never read ``.kittify/config.yaml`` directly.
# The single config-reading path is
# ``load_org_charter_policies(repo_root, pack_context=...)``, which already
# accepts a :class:`PackContext` (WP09 T061-sig).
#
# T064-drg asked WP11 to find any ``load_org_charter_policies(repo_root)``
# call inside ``src/charter/drg.py`` and pass a ``PackContext`` to it. After
# audit no such call exists — this module has always loaded its DRG layers
# via :func:`load_graph` (built-in), :func:`load_org_drg` (org packs, which
# already routes through the charter-layer pack registry), and the project
# layer is supplied by the caller. PackContext therefore reaches this module
# only through the :func:`filter_graph_by_activation` surface above, which is
# the FR-018 access point for runtime resolvers.
#
# Layer boundary note: ``src/charter/`` cannot import from
# ``specify_cli.doctrine.*`` (the dependency rule is
# ``kernel <- doctrine <- charter <- specify_cli`` per
# ``docs/architecture/00_landscape/README.md``). Runtime callers that need to
# both filter the graph and load org-charter policies must invoke
# :func:`filter_graph_by_activation` here and
# ``specify_cli.doctrine.org_charter.load_org_charter_policies`` from their
# own (specify_cli-layer) call site, passing the same ``PackContext`` to
# both.
