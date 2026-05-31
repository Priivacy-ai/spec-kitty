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
* Provenance is threaded by attaching a ``provenance`` sidecar attribute to
  each merged node/edge. Because the built-in models are frozen
  ``BaseModel`` instances, the merge returns a ``DRGGraph`` whose node /
  edge objects carry a ``provenance`` attribute monkey-set after
  construction; consumers read it with ``getattr(node, 'provenance', None)``.

This matches data-model.md §2's stated provenance semantics
(``source: built-in | org:<pack> | project``) while honouring the
contract YAML shape that the FR-140 round-trip gate enforces.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from charter.pack_context import PackContext
from doctrine.artifact_kinds import ArtifactKind
from doctrine.drg import load_graph, merge_layers
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.org_pack_config import load_pack_registry
from doctrine.drg.org_pack_loader import (
    OrgDRGFragment,
    OrgPackMissingError,
    load_org_pack,
)
from doctrine.drg.query import ResolvedContext, resolve_context

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
    "PackContext",
    "Relation",
    "ResolvedContext",
    "filter_graph_by_activation",
    "load_graph",
    "load_org_drg",
    "merge_layers",
    "merge_three_layers",
    "resolve_context",
]

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# C-009: 8-kind plural universe inherited from Mission B
# ---------------------------------------------------------------------------
# Byte-identical to ``charter.activations._ALLOWED_KINDS`` and to
# ``doctrine.drg.org_pack_loader._ORG_DRG_CANONICAL_KINDS``. We re-declare
# rather than import to keep ``charter.drg`` free of intra-package import
# fan-out; the contract test sweep enforces drift detection between the
# two declarations (see C-009 binding).

_ORG_DRG_CANONICAL_KINDS: frozenset[str] = frozenset(
    {
        "directives",
        "tactics",
        "styleguides",
        "toolguides",
        "paradigms",
        "procedures",
        "agent_profiles",
        "mission_steps",
        # Backward-compat alias retained for one release; pre-WP01 packs used
        # ``mission_step_contracts`` (see mission
        # ``charter-doctrine-mission-type-configuration-01KSWJVX`` WP01/WP11).
        "mission_step_contracts",
    }
)


# Singular form for URN minting at merge time. Mirrors
# ``doctrine.artifact_kinds._PLURALS`` in inverse direction.
_PLURAL_TO_SINGULAR: dict[str, str] = {
    "directives": "directive",
    "tactics": "tactic",
    "styleguides": "styleguide",
    "toolguides": "toolguide",
    "paradigms": "paradigm",
    "procedures": "procedure",
    "agent_profiles": "agent_profile",
    # Canonical post-WP01 plural → existing singular ``mission_step_contract``.
    # The doctrine.drg.org_pack_loader validator resolves the legacy
    # ``mission_step_contracts`` alias to ``mission_steps`` on parse. We keep
    # the singular as ``mission_step_contract`` here because
    # ``doctrine.drg.models.NodeKind`` has no ``mission_step`` member yet;
    # extending NodeKind is out of WP11's scope. Both plural keys are
    # retained so hand-constructed fragments that bypass the loader still
    # mint a valid URN.
    "mission_steps": "mission_step_contract",
    "mission_step_contracts": "mission_step_contract",
}


# ---------------------------------------------------------------------------
# Conflict reporting (FR-004, FR-005)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrgDRGConflict:
    """A typed conflict report for built-in/org/project layer disagreements.

    Per data-model §3:

    * ``edge_override`` — an org fragment edge collides with a built-in edge.
    * ``node_override`` — an org fragment node collides with a built-in node.
    * ``kind_mismatch`` — an org fragment node declares a kind not in the
      8-kind universe (in practice this is caught at validation time by
      ``_OrgDRGNode`` in ``doctrine.drg.org_pack_loader``).
    * ``layer_rule_violation`` — a node body_path / import reaches across
      the architectural layer boundary (C-001 binding).

    ``resolution_applied`` values:

    * ``hard_fail`` — the merge raises :class:`OrgDRGConflictError`.
    * ``built_in_wins`` — silent precedence (the built-in value is retained).
    * ``project_wins`` — silent precedence (the project value is retained).
    """

    kind: Literal[
        "edge_override", "node_override", "kind_mismatch", "layer_rule_violation"
    ]
    conflicting_layers: list[str]
    target_id: str
    built_in_value: Any | None
    org_value: Any
    project_value: Any | None
    resolution_applied: Literal["hard_fail", "built_in_wins", "project_wins"]


class OrgDRGConflictError(Exception):
    """Raised when an org-DRG fragment violates the layer rule or
    overrides a built-in invariant in a non-recoverable way.

    Carries one or more :class:`OrgDRGConflict` records. The message is
    operator-actionable and lists each conflict's kind, target, layers,
    and applied resolution.
    """

    def __init__(self, conflicts: list[OrgDRGConflict]):
        self.conflicts = list(conflicts)
        super().__init__(self._format_message(self.conflicts))

    @staticmethod
    def _format_message(conflicts: list[OrgDRGConflict]) -> str:
        lines = [f"{len(conflicts)} org-DRG conflict(s):"]
        for c in conflicts:
            lines.append(
                f"  - kind={c.kind}, target_id={c.target_id}, "
                f"layers={c.conflicting_layers}, resolution={c.resolution_applied}"
            )
        lines.append(
            "Remediation: remove the override from the org pack, OR escalate "
            "the built-in invariant change via a spec-kitty governance proposal."
        )
        return "\n".join(lines)


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
        configured_path = pack.local_path
        if not configured_path.is_absolute():
            configured_path = (repo_root / configured_path).resolve()
        # Delegate all per-pack schema parsing to the doctrine layer.
        fragments.append(load_org_pack(pack.name, configured_path, layer_index))
    return fragments


# ---------------------------------------------------------------------------
# Merge (FR-001, FR-005)
# ---------------------------------------------------------------------------


def _tag_source(obj: BaseModel, source: str) -> BaseModel:
    """Attach a ``provenance`` sidecar attribute to a frozen Pydantic model.

    DRGNode / DRGEdge are :class:`BaseModel` instances with no native
    ``provenance`` field. We need to thread provenance through the merged
    graph without changing the built-in model shape, so we monkey-set a
    plain attribute. Consumers read with ``getattr(node, 'provenance', None)``.

    .. note::
        The attribute is named ``provenance`` (NOT ``source``) to avoid
        colliding with ``DRGEdge.source``, which is the source-endpoint URN
        declared in the Pydantic model. Using ``source`` as the sidecar name
        caused ``_tag_source`` to silently overwrite the endpoint URN on every
        merged edge (P0 bug, Robert review 2026-05).

    The Pydantic v2 ``object.__setattr__`` workaround is needed because
    BaseModel restricts attribute assignment to declared fields by
    default.
    """
    object.__setattr__(obj, "provenance", source)
    return obj


def _merge_org_fragment(
    fragment: OrgDRGFragment,
    merged_nodes: dict[str, DRGNode],
    merged_edges: list[DRGEdge],
    invariant_urns: frozenset[str],
    conflicts: list[OrgDRGConflict],
) -> None:
    """Merge one org-DRG fragment into *merged_nodes* / *merged_edges*.

    Extracted from :func:`merge_three_layers` to keep its cyclomatic
    complexity within the ruff C901 limit (15).
    """
    source_marker = f"org:{fragment.pack_name}"
    surviving_nodes: list[Any] = []
    for node in fragment.nodes:
        if _violates_layer_rule(node):
            conflicts.append(
                OrgDRGConflict(
                    kind="layer_rule_violation",
                    conflicting_layers=[source_marker],
                    target_id=node.id,
                    built_in_value=None,
                    org_value=node.model_dump(),
                    project_value=None,
                    resolution_applied="hard_fail",
                )
            )
            continue
        surviving_nodes.append(node)

    node_id_to_urn: dict[str, str] = {}
    for node in surviving_nodes:
        urn, drg_node = _bridge_org_node_to_drg_node(node, source_marker)
        node_id_to_urn[node.id] = urn
        if urn in invariant_urns:
            conflicts.append(
                OrgDRGConflict(
                    kind="node_override",
                    conflicting_layers=["built-in", source_marker],
                    target_id=urn,
                    built_in_value=merged_nodes[urn].model_dump(),
                    org_value=node.model_dump(),
                    project_value=None,
                    resolution_applied="hard_fail",
                )
            )
            continue
        if urn not in merged_nodes:
            merged_nodes[urn] = drg_node

    for edge in fragment.edges:
        drg_edge = _bridge_org_edge_to_drg_edge(edge, node_id_to_urn, source_marker)
        if drg_edge is not None:
            merged_edges.append(drg_edge)


def _warn_project_override(urn: str, existing_provenance: str) -> None:
    """Emit a WARNING when the project layer overrides a built-in/org node.

    Called from :func:`merge_three_layers` only.  Extracted to keep the
    merge function's cyclomatic complexity within the ruff C901 threshold.
    """
    _logger.warning(
        "Project doctrine overrides %s node %r (was provenance=%r). "
        "This is allowed by design (project > org > built-in precedence); "
        "flag here for operator visibility.",
        existing_provenance,
        urn,
        existing_provenance,
    )


def _violates_layer_rule(node: Any) -> bool:
    """C-001 / FR-005 — an org node reaching across the layer boundary.

    Conservative heuristic: any reference (in ``body_path`` or other text
    fields) to ``src/specify_cli/`` or ``specify_cli.`` is treated as a
    smuggling attempt. False positives surface as operator-actionable
    errors; an org pack should never legitimately reference the runtime
    layer.
    """
    text_blobs: list[str] = []
    if node.body_path:
        text_blobs.append(node.body_path)
    if node.title:
        text_blobs.append(node.title)
    text_blobs.append(node.id)
    return any(
        "src/specify_cli/" in blob or "specify_cli." in blob
        for blob in text_blobs
    )


def _built_in_invariant_ids(built_in: DRGGraph) -> frozenset[str]:
    """The set of URNs that org packs cannot override.

    Mission policy (FR-005): every built-in node is treated as an
    invariant. Org packs may only add new nodes or refine relations; they
    may not collide with built-in node URNs. Refining over time is fine
    (this set is intentionally broad), and an operator who needs to
    override a built-in invariant must escalate via a governance proposal
    rather than ship a silently-overriding org pack.
    """
    return frozenset(n.urn for n in built_in.nodes)


def _bridge_org_node_to_drg_node(
    node: Any, source: str
) -> tuple[str, DRGNode]:
    """Mint a URN-shaped :class:`DRGNode` from a fragment-side node.

    URN convention: ``<singular_kind>:<id>`` (e.g. ``directive:sox-controls``).
    The ``source`` attribute is attached via :func:`_tag_source`.

    Returns ``(urn, drg_node)``.
    """
    singular = _PLURAL_TO_SINGULAR[node.kind]
    urn = f"{singular}:{node.id}"
    drg_node = DRGNode(urn=urn, kind=NodeKind(singular), label=node.title)
    _tag_source(drg_node, source)
    return urn, drg_node


#: Default relation used when a fragment edge labels its relation with a
#: refinement verb that is not (yet) in the canonical :class:`Relation`
#: enum. ``refines`` is a common operator-friendly synonym for
#: ``Relation.APPLIES`` in advisory contexts; the lint pipeline (WP07)
#: surfaces unrecognised relations as advisory findings.
_RELATION_ALIASES: dict[str, Relation] = {
    "refines": Relation.APPLIES,
    "extends": Relation.APPLIES,
}


def _bridge_org_edge_to_drg_edge(
    edge: Any, node_id_to_urn: dict[str, str], source: str
) -> DRGEdge | None:
    """Mint a URN-shaped :class:`DRGEdge` from a fragment-side edge.

    Returns ``None`` only when the source endpoint cannot be resolved to a
    URN in the fragment-local node index (i.e. the org pack wrote an edge
    whose ``source:`` does not name a node it declared). Targets MAY point
    outside the fragment — they typically refer to built-in or project
    artefacts. In that case the bridge synthesises a target URN using the
    same ``<singular_kind>:<id>`` convention, defaulting to the
    ``directive`` kind when the target is not in the fragment-local index.

    Unknown relation labels are translated via ``_RELATION_ALIASES`` where
    possible; truly unknown labels return ``None`` (the lint pipeline
    later surfaces them as advisory findings).
    """
    relation_value = edge.relation
    canonical_relations = {r.value for r in Relation}
    if relation_value in canonical_relations:
        relation = Relation(relation_value)
    elif relation_value in _RELATION_ALIASES:
        relation = _RELATION_ALIASES[relation_value]
    else:
        return None

    source_urn = node_id_to_urn.get(edge.source)
    if source_urn is None:
        return None

    target_urn = node_id_to_urn.get(edge.target)
    if target_urn is None:
        # Cross-layer reference: synthesise a URN using the directive
        # default. The lint pipeline (WP07) advises operators when the
        # target cannot be resolved against any layer.
        target_urn = f"directive:{edge.target}"

    drg_edge = DRGEdge(source=source_urn, target=target_urn, relation=relation)
    _tag_source(drg_edge, source)
    return drg_edge


def merge_three_layers(
    built_in: DRGGraph,
    org_fragments: list[OrgDRGFragment],
    project: DRGGraph | None,
) -> DRGGraph:
    """Overlay built-in → org → project layers (FR-001, FR-005).

    Precedence: project > org > built-in. Operator-authored project doctrine
    may override both built-in and org tiers. When the project layer overrides
    a built-in or org node, a ``logging.warning`` is emitted with the URN +
    original layer so the override is visible in operator output but does
    not block the merge. Use :class:`OrgDRGConflict` records to query overrides
    programmatically.

    Org-tier nodes that collide with a built-in node raise
    :class:`OrgDRGConflictError` (``resolution_applied='hard_fail'``). Layer-rule
    violations (org nodes reaching into ``src/specify_cli/``) always hard-fail.

    Every node and edge in the returned graph carries a ``provenance``
    sidecar attribute readable via ``getattr(node, 'provenance', None)``:

    * ``"built-in"`` — built-in layer (Mission A);
    * ``"org:<pack_name>"`` — contributed by an :class:`OrgDRGFragment`;
    * ``"project"`` — contributed by the project layer.

    Parameters
    ----------
    built_in:
        The built-in DRG. Treated as the source of truth for
        invariants.
    org_fragments:
        Loaded org-tier fragments in declaration order. Earlier
        fragments take precedence over later ones for org-vs-org
        collisions (but a built-in node always wins regardless).
    project:
        Optional project-tier DRG (``.kittify/doctrine/graph.yaml`` loaded
        and merged elsewhere). When ``None``, the merge collapses to the
        built-in+org case.

    Returns
    -------
    DRGGraph:
        The merged graph. Nodes and edges carry the ``provenance`` sidecar
        attribute described above.

    Raises
    ------
    OrgDRGConflictError:
        On layer-rule violation OR built-in invariant override. The error
        carries the full conflict list; the caller can inspect
        ``exc.conflicts``.
    """
    conflicts: list[OrgDRGConflict] = []

    # Seed the merged maps with the built-in layer.
    merged_nodes: dict[str, DRGNode] = {
        n.urn: _tag_source(n.model_copy(), "built-in") for n in built_in.nodes
    }
    merged_edges: list[DRGEdge] = [
        _tag_source(e.model_copy(), "built-in") for e in built_in.edges
    ]

    invariant_urns = _built_in_invariant_ids(built_in)

    for fragment in org_fragments:
        _merge_org_fragment(
            fragment, merged_nodes, merged_edges, invariant_urns, conflicts
        )

    if any(c.resolution_applied == "hard_fail" for c in conflicts):
        raise OrgDRGConflictError(conflicts)

    if project is not None:
        for node in project.nodes:
            if node.urn in merged_nodes:
                existing_provenance = getattr(
                    merged_nodes[node.urn], "provenance", "unknown"
                )
                _warn_project_override(node.urn, existing_provenance)
            merged_nodes[node.urn] = _tag_source(node.model_copy(), "project")
        for edge in project.edges:
            merged_edges.append(_tag_source(edge.model_copy(), "project"))

    return DRGGraph(
        schema_version=built_in.schema_version,
        generated_at=built_in.generated_at,
        generated_by=built_in.generated_by,
        nodes=list(merged_nodes.values()),
        edges=merged_edges,
    )


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
    "mission_step_contract": "mission_steps",
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


def _node_is_activated(node: DRGNode, pack_context: PackContext) -> bool:
    """Return ``True`` when *node* is visible under the activation filter.

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
    """
    singular, _ = _split_urn(node.urn)
    if singular in _MISSION_STEP_SINGULAR_KINDS:
        owner = _owning_mission_type(node.urn)
        if owner is not None:
            return owner in pack_context.activated_mission_types
        # Fall through: ownerless step relies on kind filter.
    plural = _SINGULAR_TO_PLURAL.get(singular)
    if plural is None:
        return True
    return plural in pack_context.activated_kinds


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
    surviving_nodes = [n for n in graph.nodes if _node_is_activated(n, pack_context)]
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
# ``architecture/2.x/00_landscape/README.md``). Runtime callers that need to
# both filter the graph and load org-charter policies must invoke
# :func:`filter_graph_by_activation` here and
# ``specify_cli.doctrine.org_charter.load_org_charter_policies`` from their
# own (specify_cli-layer) call site, passing the same ``PackContext`` to
# both.
