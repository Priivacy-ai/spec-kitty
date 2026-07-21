"""
Tactic domain model and value objects.

Defines Tactic, TacticStep, TacticReference Pydantic models and
ReferenceType enum for cross-artifact references.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from doctrine.artifact_kinds import ArtifactKind

_RETIRED_RELATIONSHIP_FIELDS = ("enhances", "overrides")


def _reject_retired_relationship_fields(kind: str, data: Any) -> Any:
    """Raise an actionable error if a retired relationship key is authored.

    The ``enhances``/``overrides`` (and agent-profile ``specializes-from``)
    fields were retired in the FR-028 hard cutover. Relationships are now
    authored exclusively as DRG fragment edges in ``drg/`` fragments (merged
    into ``src/doctrine/*.graph.yaml``), never as inline artifact fields. With
    ``extra="forbid"`` these keys already fail validation; this pre-validator
    upgrades the bare ``extra_forbidden`` error into a message that tells the
    author what to do instead.
    """
    if not isinstance(data, dict):
        return data
    present = [field for field in _RETIRED_RELATIONSHIP_FIELDS if field in data]
    if present:
        keys = ", ".join(repr(field) for field in present)
        raise ValueError(
            f"Retired relationship field(s) {keys} on {kind} are no longer "
            f"accepted (FR-028 hard cutover). Author the relationship as a DRG "
            f"fragment edge in a `drg/` fragment "
            f"(e.g. {{source: <kind>:<id>, target: <kind>:<id>, "
            f"relation: enhances|overrides}}) merged into "
            f"src/doctrine/graph.yaml — not as an inline artifact field."
        )
    return data


class TacticReference(BaseModel):
    """Cross-artifact reference within a tactic or step."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    type: ArtifactKind
    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    when: str


class TacticStep(BaseModel):
    """A single step within a tactic."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    description: str | None = None
    examples: list[str] = Field(default_factory=list)
    references: list[TacticReference] = Field(default_factory=list)


class Tactic(BaseModel):
    """
    A reusable behavior pattern with ordered steps.

    Tactics describe HOW to achieve a goal through concrete,
    ordered steps with optional cross-artifact references.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    schema_version: str = Field(pattern=r"^1\.0$", alias="schema_version")
    name: str
    purpose: str | None = None
    steps: list[TacticStep] = Field(min_length=1)
    failure_modes: list[str] = Field(default_factory=list)
    applies_to_languages: list[str] = Field(default_factory=list)
    references: list[TacticReference] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_retired_relationship_fields(cls, data: Any) -> Any:
        return _reject_retired_relationship_fields("tactic", data)
