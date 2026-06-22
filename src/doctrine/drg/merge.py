"""Canonical three-layer DRG merge (doctrine-owned).

This module owns the **canonical relationship merge** for the Doctrine
Reference Graph (OQ-2(ii) / C-009). It overlays the built-in DRG with
organisation-tier fragments and an optional project-tier graph, producing a
single merged :class:`~doctrine.drg.models.DRGGraph` whose nodes and edges
carry a declared ``provenance`` field.

Relocated from ``charter.drg`` (mission
``org-doctrine-profile-integrity-activation-closure-01KT1TV1`` WP03). The
merge is pure graph logic and depends only on the ``doctrine`` and ``kernel``
layers — it MUST NOT import from ``charter`` or ``specify_cli`` (layer rule,
``tests/architectural/test_layer_rules.py``). Charter retains the
activation-aware filtering/aggregation (``filter_graph_by_activation``) and
re-exports the public names below so existing ``from charter.drg import …``
call sites keep working.

Provenance semantics (data-model.md §2):

* ``"built-in"`` — built-in layer (Mission A);
* ``"org:<pack_name>"`` — contributed by an :class:`OrgDRGFragment`;
* ``"project"`` — contributed by the project layer.

FR-003 (this WP): an org/project fragment edge whose relation label is not a
canonical :class:`Relation` member (or a known alias) now raises a structured
:class:`UnknownRelationError` instead of being silently dropped. This brings
the org-fragment path to parity with the project-fragment Pydantic path, which
already rejects unknown relations loudly. A valid ``specializes_from`` lineage
edge (WP02 added the enum member) resolves identically across shipped, org, and
project tiers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.org_pack_loader import OrgDRGFragment

# WP04 (org-doctrine-profile-integrity-closeout): ``_tag_source`` is generic
# over the concrete frozen-model type so callers (DRGNode / DRGEdge) retain
# their precise type through provenance tagging instead of being widened to
# ``BaseModel`` (which produced 4 ``mypy --strict`` errors at the merge sites).
# Python 3.11 has no PEP 695 inline syntax, so a module-level ``TypeVar`` is used.
_ModelT = TypeVar("_ModelT", bound=BaseModel)

__all__ = [
    "OrgDRGConflict",
    "OrgDRGConflictError",
    "UnknownRelationError",
    "merge_three_layers",
]

_logger = logging.getLogger(__name__)


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
    # ``doctrine.drg.models.NodeKind`` has no ``mission_step`` member yet.
    # Both plural keys are retained so hand-constructed fragments that bypass
    # the loader still mint a valid URN.
    "mission_steps": "mission_step_contract",
    "mission_step_contracts": "mission_step_contract",
}


#: Operator-friendly relation aliases mapping a fragment-authored verb to a
#: canonical :class:`Relation`. ``refines`` is NO LONGER aliased — it is now a
#: first-class ``Relation.REFINES`` (#2079) and resolves via the canonical
#: branch in :func:`_resolve_relation`. ``extends`` is overlay-inheritance
#: language and maps to ``Relation.SPECIALIZES_FROM`` (lineage), NOT to the inert
#: ``Relation.APPLIES`` sink. INVARIANT: an alias MUST NOT map to
#: ``Relation.APPLIES`` — no traversal reads ``APPLIES``, so aliasing an authored
#: relation onto it silently turns the edge into a no-op (the #2079 defect class).
_RELATION_ALIASES: dict[str, Relation] = {
    "extends": Relation.SPECIALIZES_FROM,
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
    * ``org_override`` — a SAME-KIND org node permissibly substitutes a built-in
      node in place (the org value wins, with a WARNING for operator visibility).
      Non-fatal: the merge does NOT raise. Whether a given repo *tolerates* this
      override is a per-repo governance TEST (see
      ``tests/architectural/test_builtin_override_policy.py``), not a merge-time
      prohibition.
    """

    kind: Literal[
        "edge_override", "node_override", "kind_mismatch", "layer_rule_violation"
    ]
    conflicting_layers: list[str]
    target_id: str
    built_in_value: Any | None
    org_value: Any
    project_value: Any | None
    resolution_applied: Literal[
        "hard_fail", "built_in_wins", "project_wins", "org_override"
    ]


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


class UnknownRelationError(Exception):
    """Raised when a fragment edge declares an unrecognised relation label (FR-003).

    Before this WP the org-fragment bridge silently returned ``None`` for an
    unknown relation, dropping the edge without trace, while the project-tier
    Pydantic path rejected the same input loudly. C0.3 normalises the
    asymmetry: an org or project fragment edge whose ``relation`` is neither a
    canonical :class:`Relation` value nor a known alias now fails closed with a
    structured, operator-actionable error that names the offending relation,
    the source fragment, and the valid token set. A valid ``specializes_from``
    lineage edge (and every other canonical relation) is unaffected.
    """

    def __init__(self, relation: str, source_marker: str) -> None:
        self.relation = relation
        self.source_marker = source_marker
        self.valid_relations = sorted(r.value for r in Relation)
        self.valid_aliases = sorted(_RELATION_ALIASES)
        super().__init__(
            f"Unknown DRG relation {relation!r} in fragment {source_marker!r}: "
            f"not a canonical relation and not a known alias. "
            f"Valid relations: {self.valid_relations}. "
            f"Valid aliases: {self.valid_aliases}. "
            "Remediation: use one of the valid relations/aliases, or extend "
            "the Relation enum via a spec-kitty governance proposal."
        )


# ---------------------------------------------------------------------------
# Provenance tagging
# ---------------------------------------------------------------------------


def _tag_source(obj: _ModelT, source: str) -> _ModelT:
    """Return a copy of *obj* with its declared ``provenance`` field set.

    DRGNode / DRGEdge now declare a typed ``provenance: str | None`` field
    (FR-013, D2-revised). Provenance is set via ``model_copy(update=...)`` so
    the field is populated through the model's own validation surface instead
    of the former ``object.__setattr__`` sidecar. Consumers read the field
    directly (``node.provenance``) or, where the graph object is duck-typed,
    via ``getattr(node, "provenance", None)``.

    .. note::
        The field is named ``provenance`` (NOT ``source``) to avoid colliding
        with ``DRGEdge.source``, which is the source-endpoint URN. Using
        ``source`` as the marker name caused an earlier sidecar to silently
        overwrite the endpoint URN on every merged edge (P0 bug, Robert review
        2026-05).
    """
    return obj.model_copy(update={"provenance": source})


# ---------------------------------------------------------------------------
# Layer rule + invariants
# ---------------------------------------------------------------------------


def _violates_layer_rule(node: Any) -> bool:
    """C-001 / FR-005 — an org node reaching across the layer boundary.

    Conservative heuristic: any reference (in ``body_path`` or other text
    fields) to ``src/specify_cli/`` or ``specify_cli.`` is treated as a
    smuggling attempt. False positives surface as operator-actionable
    errors; an org pack should never legitimately reference the runtime layer.
    """
    text_blobs: list[str] = []
    if node.body_path:
        text_blobs.append(node.body_path)
    if node.title:
        text_blobs.append(node.title)
    text_blobs.append(node.id)
    return any(
        "src/specify_cli/" in blob or "specify_cli." in blob for blob in text_blobs
    )


def _built_in_invariant_ids(built_in: DRGGraph) -> frozenset[str]:
    """The set of built-in URNs that an org node may collide with.

    Every built-in node URN is returned. A collision is no longer an automatic
    hard-fail: an org node whose URN matches a built-in URN **and whose kind
    matches** is permitted to override the built-in in place (permitted-but-
    visible — a ``node_override`` conflict with ``resolution_applied =
    "org_override"`` is recorded and a WARNING is emitted). A collision whose
    kind DIFFERS (kind-drift) still hard-fails: an override may replace a
    built-in's content, never its kind. Layer-rule violations also still
    hard-fail.

    Whether a given repo *tolerates* a built-in override is a per-repo
    governance TEST (``tests/architectural/test_builtin_override_policy.py``
    consults ``.kittify/doctrine/replaceable-builtins.yaml``), not a merge-time
    prohibition.
    """
    return frozenset(n.urn for n in built_in.nodes)


# ---------------------------------------------------------------------------
# Fragment → DRG bridging
# ---------------------------------------------------------------------------


def _bridge_org_node_to_drg_node(node: Any, source: str) -> tuple[str, DRGNode]:
    """Mint a URN-shaped :class:`DRGNode` from a fragment-side node.

    URN convention: ``<singular_kind>:<id>`` (e.g. ``directive:sox-controls``).
    The ``source`` is attached via :func:`_tag_source`. Returns ``(urn, drg_node)``.
    """
    singular = _PLURAL_TO_SINGULAR[node.kind]
    urn = f"{singular}:{node.id}"
    drg_node = DRGNode(urn=urn, kind=NodeKind(singular), label=node.title)
    return urn, _tag_source(drg_node, source)


def _resolve_relation(relation_value: str, source_marker: str) -> Relation:
    """Resolve a fragment edge relation label to a canonical :class:`Relation`.

    FR-003: a label that is neither a canonical relation value nor a known
    alias raises :class:`UnknownRelationError` (fail closed) rather than
    dropping the edge silently.
    """
    canonical_relations = {r.value for r in Relation}
    if relation_value in canonical_relations:
        return Relation(relation_value)
    if relation_value in _RELATION_ALIASES:
        return _RELATION_ALIASES[relation_value]
    raise UnknownRelationError(relation_value, source_marker)


def _bridge_org_edge_to_drg_edge(
    edge: Any,
    node_id_to_urn: dict[str, str],
    source: str,
) -> DRGEdge | None:
    """Mint a URN-shaped :class:`DRGEdge` from a fragment-side edge.

    Returns ``None`` only when the source endpoint cannot be resolved to a URN
    in the fragment-local node index (i.e. the org pack wrote an edge whose
    ``source:`` does not name a node it declared). Targets MAY point outside
    the fragment — they typically refer to built-in or project artefacts; in
    that case the bridge synthesises a target URN using the same
    ``<singular_kind>:<id>`` convention, defaulting to the ``directive`` kind
    when the target is not in the fragment-local index.

    FR-003: an unknown relation label raises :class:`UnknownRelationError`
    (via :func:`_resolve_relation`) instead of returning ``None``.
    """
    relation = _resolve_relation(edge.relation, source)

    source_urn = node_id_to_urn.get(edge.source)
    if source_urn is None:
        return None

    target_urn = node_id_to_urn.get(edge.target)
    if target_urn is None:
        # Cross-layer reference: synthesise a URN using the directive default.
        target_urn = f"directive:{edge.target}"

    drg_edge = DRGEdge(source=source_urn, target=target_urn, relation=relation)
    return _tag_source(drg_edge, source)


def _resolve_builtin_collision(
    urn: str,
    org_node: Any,
    drg_node: DRGNode,
    merged_nodes: dict[str, DRGNode],
    conflicts: list[OrgDRGConflict],
    source_marker: str,
) -> None:
    """Resolve an org node whose URN collides with a built-in node.

    Kind-drift (the org node's kind DIFFERS from the built-in node's kind) is a
    ``hard_fail``: an override may replace a built-in's content, never its kind.
    A SAME-KIND collision is PERMITTED — the org node substitutes the built-in
    in place (``merged_nodes[urn] = drg_node``), a ``node_override`` conflict
    with ``resolution_applied = "org_override"`` is recorded, and a WARNING is
    emitted. In-place URN substitution preserves the built-in's inbound and
    outbound edges (no rehoming), mirroring the project-layer override path.
    """
    built_in_node = merged_nodes[urn]
    if drg_node.kind != built_in_node.kind:
        conflicts.append(
            OrgDRGConflict(
                kind="node_override",
                conflicting_layers=["built-in", source_marker],
                target_id=urn,
                built_in_value=built_in_node.model_dump(),
                org_value=org_node.model_dump(),
                project_value=None,
                resolution_applied="hard_fail",
            )
        )
        return
    merged_nodes[urn] = drg_node
    conflicts.append(
        OrgDRGConflict(
            kind="node_override",
            conflicting_layers=["built-in", source_marker],
            target_id=urn,
            built_in_value=built_in_node.model_dump(),
            org_value=org_node.model_dump(),
            project_value=None,
            resolution_applied="org_override",
        )
    )
    _warn_builtin_override(urn, source_marker)


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

    A built-in URN collision is delegated to :func:`_resolve_builtin_collision`:
    a SAME-KIND org node permissibly overrides the built-in in place (a
    ``node_override`` conflict with ``resolution_applied = "org_override"`` plus
    a WARNING); a kind-drift collision still hard-fails. Whether the repo
    tolerates a permitted override is a per-repo governance test, not a merge
    prohibition.
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
            _resolve_builtin_collision(
                urn, node, drg_node, merged_nodes, conflicts, source_marker
            )
            continue
        if urn not in merged_nodes:
            merged_nodes[urn] = drg_node

    for edge in fragment.edges:
        drg_edge = _bridge_org_edge_to_drg_edge(edge, node_id_to_urn, source_marker)
        if drg_edge is not None:
            merged_edges.append(drg_edge)


def _warn_builtin_override(urn: str, source_marker: str) -> None:
    """Emit a WARNING when a same-kind org node overrides a built-in node.

    Mirrors :func:`_warn_project_override`. The override is permitted by the
    merge (kind matches), but is surfaced for operator visibility: a per-repo
    governance test decides whether the override is allowed for this repo.
    """
    _logger.warning(
        "Org doctrine %r overrides built-in node %r (same-kind override). "
        "This is permitted by the merge but visible by design; a per-repo "
        "governance test (replaceable-builtins allowlist) decides whether the "
        "override is sanctioned.",
        source_marker,
        urn,
    )


def _warn_project_override(urn: str, existing_provenance: str) -> None:
    """Emit a WARNING when the project layer overrides a built-in/org node.

    Called from :func:`merge_three_layers` only. Extracted to keep the merge
    function's cyclomatic complexity within the ruff C901 threshold.
    """
    _logger.warning(
        "Project doctrine overrides %s node %r (was provenance=%r). "
        "This is allowed by design (project > org > built-in precedence); "
        "flag here for operator visibility.",
        existing_provenance,
        urn,
        existing_provenance,
    )


# ---------------------------------------------------------------------------
# Canonical merge (FR-001, FR-003, FR-005)
# ---------------------------------------------------------------------------


def merge_three_layers(
    built_in: DRGGraph,
    org_fragments: list[OrgDRGFragment],
    project: DRGGraph | None,
) -> DRGGraph:
    """Overlay built-in → org → project layers (FR-001, FR-003, FR-005).

    Precedence: project > org > built-in. Operator-authored project doctrine
    may override both built-in and org tiers. When the project layer overrides
    a built-in or org node, a ``logging.warning`` is emitted with the URN +
    original layer so the override is visible in operator output but does not
    block the merge. Use :class:`OrgDRGConflict` records to query overrides
    programmatically.

    Org-tier nodes that collide with a built-in node are resolved by kind:

    * **Same-kind** collision — PERMITTED. The org node substitutes the built-in
      in place (preserving the built-in's inbound/outbound edges, mirroring the
      project-layer override), a ``node_override`` conflict with
      ``resolution_applied='org_override'`` is recorded, and a WARNING is
      emitted. The merge does NOT raise. Whether a given repo *tolerates* this
      override is a per-repo governance TEST
      (``tests/architectural/test_builtin_override_policy.py`` consulting
      ``.kittify/doctrine/replaceable-builtins.yaml``), not a merge prohibition.
    * **Kind-drift** collision (org kind DIFFERS from built-in kind) — hard-fails
      with :class:`OrgDRGConflictError` (``resolution_applied='hard_fail'``). An
      override may replace a built-in's content, never its kind.

    Layer-rule violations (org nodes reaching into ``src/specify_cli/``) always
    hard-fail. An org/project fragment edge with an unrecognised relation label
    raises :class:`UnknownRelationError` (FR-003 — no silent drop).

    Every node and edge in the returned graph carries a declared ``provenance``
    field readable via ``node.provenance``:

    * ``"built-in"`` — built-in layer (Mission A);
    * ``"org:<pack_name>"`` — contributed by an :class:`OrgDRGFragment`;
    * ``"project"`` — contributed by the project layer.

    Parameters
    ----------
    built_in:
        The built-in DRG. Treated as the source of truth for invariants.
    org_fragments:
        Loaded org-tier fragments in declaration order. Earlier fragments take
        precedence over later ones for org-vs-org collisions (but a built-in
        node always wins regardless).
    project:
        Optional project-tier DRG (``.kittify/doctrine/graph.yaml`` loaded and
        merged elsewhere). When ``None``, the merge collapses to the
        built-in+org case.

    Returns
    -------
    DRGGraph:
        The merged graph. Nodes and edges carry the declared ``provenance`` field.

    Raises
    ------
    OrgDRGConflictError:
        On a layer-rule violation OR a kind-drift built-in collision (org kind
        differs from the built-in kind). A SAME-KIND built-in override does NOT
        raise (it is recorded as an ``org_override`` conflict). The error
        carries the full conflict list; the caller can inspect ``exc.conflicts``.
    UnknownRelationError:
        On an org/project fragment edge with an unrecognised relation label
        (FR-003).
    """
    conflicts: list[OrgDRGConflict] = []

    # Seed the merged maps with the built-in layer.
    merged_nodes: dict[str, DRGNode] = {
        n.urn: _tag_source(n, "built-in") for n in built_in.nodes
    }
    merged_edges: list[DRGEdge] = [
        _tag_source(e, "built-in") for e in built_in.edges
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
                existing_provenance = merged_nodes[node.urn].provenance or "unknown"
                _warn_project_override(node.urn, existing_provenance)
            merged_nodes[node.urn] = _tag_source(node, "project")
        for edge in project.edges:
            merged_edges.append(_tag_source(edge, "project"))

    return DRGGraph(
        schema_version=built_in.schema_version,
        generated_at=built_in.generated_at,
        generated_by=built_in.generated_by,
        nodes=list(merged_nodes.values()),
        edges=merged_edges,
    )
