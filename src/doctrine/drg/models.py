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

    Superset of ``ArtifactKind`` -- adds ``ACTION`` and ``GLOSSARY_SCOPE``.
    """

    DIRECTIVE = "directive"
    TACTIC = "tactic"
    PARADIGM = "paradigm"
    STYLEGUIDE = "styleguide"
    TOOLGUIDE = "toolguide"
    PROCEDURE = "procedure"
    AGENT_PROFILE = "agent_profile"
    ACTION = "action"
    GLOSSARY_SCOPE = "glossary_scope"


class Relation(StrEnum):
    """Typed edge relations in the DRG."""

    REQUIRES = "requires"
    SUGGESTS = "suggests"
    APPLIES = "applies"
    SCOPE = "scope"
    VOCABULARY = "vocabulary"
    INSTANTIATES = "instantiates"
    REPLACES = "replaces"
    DELEGATES_TO = "delegates_to"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DRGNode(BaseModel):
    """A single addressable doctrine artifact node."""

    urn: str
    kind: NodeKind
    label: str | None = None

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

    def get_node(self, urn: str) -> DRGNode | None:
        """Look up a node by URN, or ``None`` if not found."""
        for n in self.nodes:
            if n.urn == urn:
                return n
        return None
