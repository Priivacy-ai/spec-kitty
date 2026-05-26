"""
Tactic domain model and value objects.

Defines Tactic, TacticStep, TacticReference Pydantic models and
ReferenceType enum for cross-artifact references.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from doctrine.artifact_kinds import ArtifactKind
from doctrine.shared.models import Contradiction


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
    overrides: str | None = Field(
        default=None,
        description="ID of a built-in tactic this artifact replaces in full.",
    )
    enhances: str | None = Field(
        default=None,
        description="ID of a built-in tactic this artifact augments via field-merge.",
    )
    purpose: str | None = None
    steps: list[TacticStep] = Field(min_length=1)
    failure_modes: list[str] = Field(default_factory=list)
    applies_to_languages: list[str] = Field(default_factory=list)
    references: list[TacticReference] = Field(default_factory=list)
    opposed_by: list[Contradiction] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _augmentation_intent_is_exclusive(self) -> Self:
        if self.overrides is not None and self.enhances is not None:
            raise ValueError(
                f"overrides and enhances are mutually exclusive on tactic {self.id}"
            )
        return self
