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
    ACTION = "action"
    GLOSSARY_SCOPE = "glossary_scope"
    GLOSSARY = "glossary"           # URN prefix: "glossary:<id>"


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
