"""Pydantic v2 models for the Doctrine Reference Graph (DRG).

Defines ``NodeKind``, ``Relation`` enums and ``DRGNode``, ``DRGEdge``,
``DRGGraph`` models with URN validation and graph convenience methods.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# URN regex -- anchored, no spaces, only lower-alpha + underscore for kind
# ---------------------------------------------------------------------------

_URN_RE = re.compile(r"^[a-z_]+:[A-Za-z0-9_/.\-]+$")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NodeKind(StrEnum):
    """Canonical DRG node kinds.

    Superset of ``ArtifactKind`` plus action and glossary node kinds.
    """

    DIRECTIVE = "directive"
    TACTIC = "tactic"
    PARADIGM = "paradigm"
    STYLEGUIDE = "styleguide"
    TOOLGUIDE = "toolguide"
    PROCEDURE = "procedure"
    AGENT_PROFILE = "agent_profile"
    MISSION_STEP_CONTRACT = "mission_step_contract"
    TEMPLATE = "template"
    ASSET = "asset"
    ACTION = "action"
    GLOSSARY_SCOPE = "glossary_scope"
    GLOSSARY = "glossary"           # URN prefix: "glossary:<id>"
    MISSION_TYPE = "mission_type"   # URN prefix: "mission_type:<id>"; carries `requires` edges to its action_sequence steps
    # URN prefix: "anti_pattern:<id>"; `rejects` targets only (D2) -- never
    # activated as a live rule; finer marking (e.g. "smell") lives in
    # `DRGNode.tags`, not a second `NodeKind` member.
    ANTI_PATTERN = "anti_pattern"


class Relation(StrEnum):
    """Typed edge relations in the DRG.

    Lineage vs. delegation vs. augmentation are three distinct concepts and
    MUST NOT be conflated (FR-001, FR-002):

    - ``SPECIALIZES_FROM`` (lineage): a profile/artifact derives from a parent,
      narrowing or extending it. This is a *static composition* relation used
      for inheritance/specialization (FR-001). It is deliberately separate from
      ``DELEGATES_TO`` so lineage never leaks into runtime handoff traversal.
    - ``DELEGATES_TO`` (delegation): a *runtime handoff* relation -- one agent
      hands work to another at execution time (FR-002). It is never inferred
      from lineage.
    - ``ENHANCES`` / ``OVERRIDES`` (augmentation pair, FR-014, mission
      ``charter-ux-and-org-pack-vocabulary-01KSAF14``): a pack artifact declares
      ``enhances: <id>`` to field-merge into a built-in, or ``overrides: <id>``
      to declare a full replacement.
    - ``REPLACES`` is retained for backward compatibility with existing
      hand-authored fragments (R-2).
    - ``REFINES`` (refinement, #2079): an artifact narrows or sharpens the
      applicability or meaning of the target (a parent or built-in) without
      replacing it. It is distinct from ``APPLIES`` (an action applies a
      directive/tactic) and from ``SPECIALIZES_FROM`` (static profile/artifact
      lineage): a refinement is a first-class, traversable relation, never a
      synonym for ``APPLIES``. Previously the org→DRG bridge silently downgraded
      ``refines`` to ``APPLIES`` (a dead sink); it is now preserved end-to-end.
    - ``IN_TENSION_WITH`` / ``RECONCILES_TENSION`` / ``REJECTS`` (tension
      vocabulary, mission ``doctrine-tension-edges-01KY1WPC``, FR-001/002/003):
      three distinct relations that must not be confused with each other or
      with the relations above.

      - ``IN_TENSION_WITH`` is **symmetric and non-transitive**: two co-valid,
        co-activatable artefacts compete on the same decision, and neither is
        deprecated by the other. It is stored as a single canonical edge
        (lexicographically-smaller URN as source, C-002) and queried from
        either endpoint via :meth:`DRGGraph.edges_from`/:meth:`DRGGraph.edges_to`.
        It must NOT be confused with ``REPLACES``/supersession -- tension does
        not mean one side wins or is retired.
      - ``RECONCILES_TENSION`` is **directional**, from an active
        reconciliation artefact to one side of a tension pair. A pair counts
        as resolved only when an active artefact carries this edge to BOTH
        sides; a single edge to one side leaves the pair "half-reconciled"
        and still flagged (FR-002). It is never synthesized from
        ``IN_TENSION_WITH`` -- it must be authored explicitly.
      - ``REJECTS`` is **directional**, from a good artefact to a marked
        anti-pattern/smell node (``NodeKind.ANTI_PATTERN``). Unlike
        ``IN_TENSION_WITH`` the target is not a competing equal -- it is a
        named bad practice, not a co-valid rule -- and unlike ``REPLACES`` the
        target was never a valid rule the rejecting artefact supersedes.
    """

    REQUIRES = "requires"
    SUGGESTS = "suggests"
    APPLIES = "applies"
    SCOPE = "scope"
    VOCABULARY = "vocabulary"
    INSTANTIATES = "instantiates"
    REPLACES = "replaces"
    DELEGATES_TO = "delegates_to"
    SPECIALIZES_FROM = "specializes_from"
    ENHANCES = "enhances"
    OVERRIDES = "overrides"
    REFINES = "refines"
    IN_TENSION_WITH = "in_tension_with"
    RECONCILES_TENSION = "reconciles_tension"
    REJECTS = "rejects"


#: Canonical relation-description registry (single authority, FR-012/A2).
#: Scope for this mission is deliberately the three new relations only --
#: backfilling descriptions for the other twelve pre-existing relations is an
#: explicit non-goal (spec.md Assumption A2). This is the ONE seam that both
#: a future ``describe(relation)`` call site and the WP08 doc-parity check
#: (``docs/architecture/doctrine-relationships.md``) read from -- do not
#: duplicate this mapping anywhere else.
RELATION_DESCRIPTIONS: dict[Relation, str] = {
    Relation.IN_TENSION_WITH: (
        "Marks two co-valid, co-activatable artefacts that compete on the "
        "same decision. The relation is symmetric and non-transitive: it is "
        "stored as a single canonical edge (lexicographically-smaller URN as "
        "source) and is queryable from either endpoint. It does not imply "
        "that either side is deprecated, superseded, or wrong -- both remain "
        "valid rules until an operator deactivates one side or activates a "
        "reconciler."
    ),
    Relation.RECONCILES_TENSION: (
        "Links an active reconciliation artefact to one side of a declared "
        "tension pair. A tension pair is treated as resolved only when an "
        "active artefact carries this edge to BOTH sides of the pair -- an "
        "edge to just one side leaves the pair half-reconciled and still "
        "flagged. It is authored explicitly and is never inferred from an "
        "``in_tension_with`` edge."
    ),
    Relation.REJECTS: (
        "A directional edge from a good artefact to a marked anti-pattern or "
        "smell node (``NodeKind.ANTI_PATTERN``), expressing rejection of a "
        "named bad practice. It is distinct from ``in_tension_with`` -- the "
        "target is not a competing equal, it is a bad practice -- and from "
        "``replaces``/supersession, since the target was never a valid rule "
        "to begin with."
    ),
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DRGNode(BaseModel):
    """A single addressable doctrine artifact node."""

    urn: str
    kind: NodeKind
    label: str | None = None
    # Merge-time provenance marker ("built-in" | "org:<pack>" | "project").
    # Declared optional field (FR-013, D2-revised) replacing the former
    # ``object.__setattr__`` sidecar. ``None`` for nodes that never pass
    # through the three-layer merge (e.g. the extractor-built shipped graph),
    # so the field is excluded from ``graph.yaml`` serialisation by the
    # extractor's explicit field-by-field writer — graph output stays stable.
    provenance: str | None = None
    # Free-form markers (e.g. ["smell"]) for finer-grained distinctions within
    # a single NodeKind -- e.g. NodeKind.ANTI_PATTERN nodes use this to
    # distinguish "smell" from a bare anti-pattern without a second NodeKind
    # member. Explicitly modelled (not left to Pydantic v2's extra="ignore"
    # default) so an authored `tags: [...]` key round-trips instead of being
    # silently dropped on load.
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_urn(self) -> Self:
        if not _URN_RE.match(self.urn):
            raise ValueError(
                f"URN {self.urn!r} does not match pattern "
                f"{_URN_RE.pattern}"
            )
        prefix = self.urn.split(":", 1)[0]
        if prefix != self.kind.value:
            raise ValueError(
                f"URN prefix {prefix!r} does not match kind {self.kind.value!r}"
            )
        return self


class DRGEdge(BaseModel):
    """A typed, directed relationship between two nodes."""

    source: str
    target: str
    relation: Relation
    when: str | None = None
    reason: str | None = None
    # Merge-time provenance marker; see ``DRGNode.provenance``. Named
    # ``provenance`` (NOT ``source``) to avoid colliding with the source
    # endpoint URN above.
    provenance: str | None = None

    @model_validator(mode="after")
    def _validate_urns(self) -> Self:
        for field_name in ("source", "target"):
            value = getattr(self, field_name)
            if not _URN_RE.match(value):
                raise ValueError(
                    f"Edge {field_name} {value!r} does not match URN pattern "
                    f"{_URN_RE.pattern}"
                )
        return self


class DRGGraph(BaseModel):
    """Top-level DRG graph document (``graph.yaml``)."""

    schema_version: str = Field(pattern=r"^1\.0$")
    generated_at: str
    generated_by: str
    nodes: list[DRGNode]
    edges: list[DRGEdge]

    # -- Convenience methods (efficient lookups) ----------------------------

    def node_urns(self) -> set[str]:
        """Return the set of all node URNs in the graph."""
        return {n.urn for n in self.nodes}

    def edges_from(
        self,
        urn: str,
        relation: Relation | None = None,
    ) -> list[DRGEdge]:
        """Return outgoing edges from *urn*, optionally filtered by *relation*."""
        return [
            e
            for e in self.edges
            if e.source == urn and (relation is None or e.relation == relation)
        ]

    def edges_to(
        self,
        urn: str,
        relation: Relation | None = None,
    ) -> list[DRGEdge]:
        """Return incoming edges to *urn*, optionally filtered by *relation*.

        Reverse-adjacency mirror of :meth:`edges_from`: an edge is incoming when
        its ``target`` equals *urn*. Used by cascade traversal (e.g. Wave 3
        deactivation) that needs to find every node pointing *at* a given URN.

        Implemented as an O(E) scan for parity with :meth:`edges_from`; no
        reverse index is pre-built.
        """
        return [
            e
            for e in self.edges
            if e.target == urn and (relation is None or e.relation == relation)
        ]

    def get_node(self, urn: str) -> DRGNode | None:
        """Look up a node by URN, or ``None`` if not found."""
        for n in self.nodes:
            if n.urn == urn:
                return n
        return None
