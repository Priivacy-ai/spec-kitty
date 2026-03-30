"""
Tactic domain model and value objects.

Defines Tactic, TacticStep, TacticReference Pydantic models and
ReferenceType enum for cross-artifact references.
"""

from pydantic import BaseModel, ConfigDict, Field

from doctrine.artifact_kinds import ArtifactKind


class TacticReference(BaseModel):
    """Cross-artifact reference within a tactic or step."""

    model_config = ConfigDict(frozen=True)

    name: str
    type: ArtifactKind
    id: str
    when: str


class TacticStep(BaseModel):
    """A single step within a tactic."""

    model_config = ConfigDict(frozen=True)

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

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    schema_version: str = Field(alias="schema_version")
    name: str
    purpose: str | None = None
    steps: list[TacticStep] = Field(min_length=1)
    references: list[TacticReference] = Field(default_factory=list)
