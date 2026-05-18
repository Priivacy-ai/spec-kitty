"""Charter facade for DRG (Doctrine Reference Graph) types + org layer (Slice F).

This module is the charter-layer proxy for runtime callers that historically
imported from ``doctrine.drg`` directly. The runtime → charter → doctrine
boundary (ADR 2026-03-27-1, tightened by mission
``charter-mediated-doctrine-selection-01KRTZCA``) requires runtime modules
under ``src/specify_cli/`` to reach doctrine artifacts only through such
charter facades.

This file is partly a pure re-export module — and partly the home of the
Slice F WP06 organisation-tier DRG loader (``OrgDRGFragment``,
``load_org_drg``, ``merge_three_layers``, ``OrgDRGConflictError``,
``OrgPackMissingError``). The org-DRG additions live in the charter layer
per the architectural constraint that anything new in the doctrine-overlay
space must be reachable by ``specify_cli`` only through ``charter``.

Slice F WP06 design notes
-------------------------

The org-DRG fragment schema (``OrgDRGFragment``) intentionally uses a
simpler node/edge shape than ``doctrine.drg.models.DRGNode`` /
``DRGEdge``. The reason is C-009: the contract round-trip gate exercises
the YAML example in
``kitty-specs/<mission>/contracts/org-drg-schema.md`` which uses plural
kinds (``kind: directives``) and human-friendly fields (``id``, ``title``,
``body_path``). The shipped DRGNode uses URNs and singular enum kinds. To
satisfy both surfaces:

* Fragment-side parsing uses the private ``_OrgDRGNode`` / ``_OrgDRGEdge``
  models declared below. Their ``kind`` field is constrained to the
  Mission B 8-kind plural universe (C-009 binding).
* ``merge_three_layers`` bridges fragment nodes onto the shipped DRG by
  minting URNs of the form ``<singular_kind>:<id>`` (e.g. ``directive:sox-controls``).
* Provenance is threaded by attaching a ``source`` sidecar attribute to
  each merged node/edge. Because the shipped models are frozen
  ``BaseModel`` instances, the merge returns a ``DRGGraph`` whose node /
  edge objects carry a ``source`` attribute monkey-set after
  construction; consumers read it with ``getattr(node, 'source', None)``.

This matches data-model.md §2's stated provenance semantics
(``source: built-in | org:<pack> | project``) while honouring the
contract YAML shape that the FR-140 round-trip gate enforces.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from doctrine.artifact_kinds import ArtifactKind
from doctrine.drg import load_graph, merge_layers
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
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
    "Relation",
    "ResolvedContext",
    "load_graph",
    "load_org_drg",
    "merge_layers",
    "merge_three_layers",
    "resolve_context",
]


# ---------------------------------------------------------------------------
# C-009: 8-kind plural universe inherited from Mission B
# ---------------------------------------------------------------------------
# Byte-identical to ``charter.activations._ALLOWED_KINDS``. We re-declare
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
    "mission_step_contracts": "mission_step_contract",
}


# ---------------------------------------------------------------------------
# Private fragment-side node / edge models (contract YAML shape)
# ---------------------------------------------------------------------------


class _OrgDRGNode(BaseModel):
    """One node in an organisation-tier DRG fragment.

    Shape matches the contract YAML example: ``id`` + plural ``kind`` +
    ``title`` + optional ``body_path``. Distinct from
    ``doctrine.drg.models.DRGNode`` (URN-based). The merge bridges the two
    by minting URNs at merge time.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    title: str | None = None
    body_path: str | None = None

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, value: str) -> str:
        if value not in _ORG_DRG_CANONICAL_KINDS:
            # "unknown kind" wording is binding per the contract example
            # at kitty-specs/.../contracts/contract-round-trip-frontmatter.md
            # (expect_message substring); do not weaken without updating
            # the contract.
            raise ValueError(
                f"unknown kind {value!r}: not in canonical 8-kind universe "
                f"(C-009 binding): {sorted(_ORG_DRG_CANONICAL_KINDS)}"
            )
        return value


class _OrgDRGEdge(BaseModel):
    """One typed edge in an organisation-tier DRG fragment.

    Mirrors the contract YAML example shape: ``source`` + ``target`` +
    ``relation`` (free-form string label; the merge bridges to
    ``doctrine.drg.models.Relation`` when possible).
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    relation: str


# ---------------------------------------------------------------------------
# Public fragment schema (FR-001)
# ---------------------------------------------------------------------------


class OrgDRGFragment(BaseModel):
    """A loaded organisation-tier DRG fragment with provenance metadata.

    One instance per configured ``organisation_packs:`` entry. The loader
    (``load_org_drg``) produces them in declaration order with
    ``layer_index`` 1..N. ``provenance_marker`` is the fixed string
    ``"org"`` — every node and edge from this fragment is tagged
    ``source: org:<pack_name>`` in the resolved DRG (see ``merge_three_layers``).
    """

    model_config = ConfigDict(extra="forbid")

    pack_name: str
    source_kind: Literal["local_path", "url", "package"]
    source_ref: str
    layer_index: int = Field(ge=1)
    provenance_marker: Literal["org"] = "org"
    nodes: list[_OrgDRGNode] = Field(default_factory=list)
    edges: list[_OrgDRGEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Conflict reporting (FR-004, FR-005)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrgDRGConflict:
    """A typed conflict report for shipped/org/project layer disagreements.

    Per data-model §3:

    * ``edge_override`` — an org fragment edge collides with a shipped edge.
    * ``node_override`` — an org fragment node collides with a shipped node.
    * ``kind_mismatch`` — an org fragment node declares a kind not in the
      8-kind universe (in practice this is caught at validation time by
      :class:`_OrgDRGNode`).
    * ``layer_rule_violation`` — a node body_path / import reaches across
      the architectural layer boundary (C-001 binding).

    ``resolution_applied`` values:

    * ``hard_fail`` — the merge raises :class:`OrgDRGConflictError`.
    * ``shipped_wins`` — silent precedence (the shipped value is retained).
    * ``project_wins`` — silent precedence (the project value is retained).
    """

    kind: Literal[
        "edge_override", "node_override", "kind_mismatch", "layer_rule_violation"
    ]
    conflicting_layers: list[str]
    target_id: str
    shipped_value: Any | None
    org_value: Any
    project_value: Any | None
    resolution_applied: Literal["hard_fail", "shipped_wins", "project_wins"]


class OrgDRGConflictError(Exception):
    """Raised when an org-DRG fragment violates the layer rule or
    overrides a shipped invariant in a non-recoverable way.

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
            "the shipped invariant change via a spec-kitty governance proposal."
        )
        return "\n".join(lines)


class OrgPackMissingError(Exception):
    """Raised when a configured org pack's ``local_path`` does not exist (FR-004).

    Mirrors Mission B FR-015 — missing org packs hard-fail at load time
    with an operator-actionable error. No silent fallback.
    """

    REMEDIATION: ClassVar[str] = (
        "Either fetch the pack (`spec-kitty doctrine fetch --pack <name>`) "
        "or remove the entry from `.kittify/config.yaml`."
    )

    def __init__(self, pack_name: str, configured_path: str | Path):
        self.pack_name = pack_name
        self.configured_path = str(configured_path)
        super().__init__(
            f"Org pack {pack_name!r} configured at {self.configured_path!r} "
            f"not found. {self.REMEDIATION}"
        )


# ---------------------------------------------------------------------------
# Loader (FR-001, FR-004, NEW-1)
# ---------------------------------------------------------------------------


def load_org_drg(repo_root: Path) -> list[OrgDRGFragment]:
    """Load all configured org packs from ``.kittify/config.yaml``.

    Returns one :class:`OrgDRGFragment` per pack in declaration order.
    Layer indices are assigned ``1..N``.

    Parameters
    ----------
    repo_root:
        Repository root containing ``.kittify/config.yaml``. When the
        config is absent or has no ``organisation_packs:`` key, the
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
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return []
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return []
    packs_config = raw.get("organisation_packs") or []
    if not isinstance(packs_config, list):
        return []

    fragments: list[OrgDRGFragment] = []
    for layer_index, entry in enumerate(packs_config, start=1):
        if not isinstance(entry, dict):
            continue
        name = entry["name"]
        source = entry.get("source", "local_path")
        if source != "local_path":
            raise NotImplementedError(
                f"Org pack source {source!r} not yet implemented "
                f"(see Slice F follow-up tracker for `url` / `package` "
                f"sources). Use `source: local_path` for now."
            )
        configured_path = Path(str(entry["path"])).expanduser()
        if not configured_path.is_absolute():
            configured_path = (repo_root / configured_path).resolve()
        if not configured_path.is_dir():
            raise OrgPackMissingError(name, configured_path)
        fragment_yaml = configured_path / "drg" / "fragment.yaml"
        if not fragment_yaml.exists():
            raise OrgPackMissingError(name, fragment_yaml)
        fragment_data = yaml.safe_load(fragment_yaml.read_text(encoding="utf-8")) or {}
        # Operator-side authoritative fields override pack-side declarations.
        # This is intentional: the loader knows the canonical pack name,
        # source kind, source_ref, and layer_index from the operator
        # configuration; the pack-side fragment.yaml's copies are advisory
        # and would be wrong if the operator renamed or relocated the pack.
        fragment_data["pack_name"] = name
        fragment_data["source_kind"] = "local_path"
        fragment_data["source_ref"] = str(configured_path)
        fragment_data["layer_index"] = layer_index
        fragments.append(OrgDRGFragment.model_validate(fragment_data))
    return fragments


# ---------------------------------------------------------------------------
# Merge (FR-001, FR-005)
# ---------------------------------------------------------------------------


def _tag_source(obj: BaseModel, source: str) -> BaseModel:
    """Attach a ``source`` sidecar attribute to a frozen Pydantic model.

    DRGNode / DRGEdge are :class:`BaseModel` instances with no native
    ``source`` field. We need to thread provenance through the merged
    graph without changing the shipped model shape, so we monkey-set a
    plain attribute. Consumers read with ``getattr(node, 'source', None)``.

    The Pydantic v2 ``object.__setattr__`` workaround is needed because
    BaseModel restricts attribute assignment to declared fields by
    default.
    """
    object.__setattr__(obj, "source", source)
    return obj


def _violates_layer_rule(node: _OrgDRGNode) -> bool:
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


def _shipped_invariant_ids(shipped: DRGGraph) -> frozenset[str]:
    """The set of URNs that org packs cannot override.

    Mission policy (FR-005): every shipped node is treated as an
    invariant. Org packs may only add new nodes or refine relations; they
    may not collide with shipped node URNs. Refining over time is fine
    (this set is intentionally broad), and an operator who needs to
    override a shipped invariant must escalate via a governance proposal
    rather than ship a silently-overriding org pack.
    """
    return frozenset(n.urn for n in shipped.nodes)


def _bridge_org_node_to_drg_node(
    node: _OrgDRGNode, source: str
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
    edge: _OrgDRGEdge, node_id_to_urn: dict[str, str], source: str
) -> DRGEdge | None:
    """Mint a URN-shaped :class:`DRGEdge` from a fragment-side edge.

    Returns ``None`` only when the source endpoint cannot be resolved to a
    URN in the fragment-local node index (i.e. the org pack wrote an edge
    whose ``source:`` does not name a node it declared). Targets MAY point
    outside the fragment — they typically refer to shipped or project
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
    shipped: DRGGraph,
    org_fragments: list[OrgDRGFragment],
    project: DRGGraph | None,
) -> DRGGraph:
    """Overlay shipped → org → project layers (FR-001, FR-005).

    Precedence: shipped invariants always win. Org-tier nodes that
    collide with a shipped node raise :class:`OrgDRGConflictError`
    (``resolution_applied='hard_fail'``). Layer-rule violations (org
    nodes reaching into ``src/specify_cli/``) always hard-fail.

    Every node and edge in the returned graph carries a ``source``
    sidecar attribute readable via ``getattr(node, 'source', None)``:

    * ``"built-in"`` — shipped layer (Mission A);
    * ``"org:<pack_name>"`` — contributed by an :class:`OrgDRGFragment`;
    * ``"project"`` — contributed by the project layer.

    Parameters
    ----------
    shipped:
        The shipped (built-in) DRG. Treated as the source of truth for
        invariants.
    org_fragments:
        Loaded org-tier fragments in declaration order. Earlier
        fragments take precedence over later ones for org-vs-org
        collisions (but a shipped node always wins regardless).
    project:
        Optional project-tier DRG (``.kittify/doctrine/graph.yaml`` loaded
        and merged elsewhere). When ``None``, the merge collapses to the
        shipped+org case.

    Returns
    -------
    DRGGraph:
        The merged graph. Nodes and edges carry the ``source`` sidecar
        attribute described above.

    Raises
    ------
    OrgDRGConflictError:
        On layer-rule violation OR shipped-invariant override. The error
        carries the full conflict list; the caller can inspect
        ``exc.conflicts``.
    """
    conflicts: list[OrgDRGConflict] = []

    # Seed the merged maps with the shipped layer.
    merged_nodes: dict[str, DRGNode] = {
        n.urn: _tag_source(n.model_copy(), "built-in") for n in shipped.nodes
    }
    merged_edges: list[DRGEdge] = [
        _tag_source(e.model_copy(), "built-in") for e in shipped.edges
    ]

    invariant_urns = _shipped_invariant_ids(shipped)

    for fragment in org_fragments:
        source_marker = f"org:{fragment.pack_name}"
        # Two-pass: detect layer-rule violations first (always hard_fail),
        # then bridge surviving nodes and detect shipped-invariant
        # collisions.
        surviving_nodes: list[_OrgDRGNode] = []
        for node in fragment.nodes:
            if _violates_layer_rule(node):
                conflicts.append(
                    OrgDRGConflict(
                        kind="layer_rule_violation",
                        conflicting_layers=[source_marker],
                        target_id=node.id,
                        shipped_value=None,
                        org_value=node.model_dump(),
                        project_value=None,
                        resolution_applied="hard_fail",
                    )
                )
                continue
            surviving_nodes.append(node)

        # If any layer-rule violations fired in this fragment, fail-fast
        # before doing more work — the operator must fix the pack first.
        if conflicts and any(
            c.resolution_applied == "hard_fail" for c in conflicts
        ):
            # Defer raising until all fragments have been scanned so the
            # operator sees the full conflict report. We continue
            # scanning subsequent fragments below.
            pass

        # Track fragment-local id→urn so edges can resolve their endpoints.
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
                        shipped_value=merged_nodes[urn].model_dump(),
                        org_value=node.model_dump(),
                        project_value=None,
                        resolution_applied="hard_fail",
                    )
                )
                continue
            # Org-vs-org collision: earlier fragment wins (shipped_wins
            # semantic mirrored to first-fragment-wins). Silent.
            if urn in merged_nodes and not hasattr(merged_nodes[urn], "source"):
                # Shouldn't happen since shipped nodes are always tagged.
                pass
            if urn not in merged_nodes:
                merged_nodes[urn] = drg_node

        for edge in fragment.edges:
            drg_edge = _bridge_org_edge_to_drg_edge(
                edge, node_id_to_urn, source_marker
            )
            if drg_edge is not None:
                merged_edges.append(drg_edge)

    if any(c.resolution_applied == "hard_fail" for c in conflicts):
        raise OrgDRGConflictError(conflicts)

    if project is not None:
        for node in project.nodes:
            merged_nodes[node.urn] = _tag_source(node.model_copy(), "project")
        for edge in project.edges:
            merged_edges.append(_tag_source(edge.model_copy(), "project"))

    return DRGGraph(
        schema_version=shipped.schema_version,
        generated_at=shipped.generated_at,
        generated_by=shipped.generated_by,
        nodes=list(merged_nodes.values()),
        edges=merged_edges,
    )
