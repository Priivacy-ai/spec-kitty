"""
Directive domain model and value objects.

Defines the Directive Pydantic model with all governance fields including
optional enrichment fields and typed cross-artifact references.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from doctrine.artifact_kinds import ArtifactKind


class Enforcement(StrEnum):
    """Enforcement level for a directive."""

    REQUIRED = "required"
    LENIENT_ADHERENCE = "lenient-adherence"
    ADVISORY = "advisory"


class DirectiveReference(BaseModel):
    """Cross-artifact reference within a directive."""

    model_config = ConfigDict(frozen=True)

    type: ArtifactKind
    id: str


class Directive(BaseModel):
    """
    A constraint-oriented governance rule.

    Directives define WHAT must be done (or avoided) with an enforcement
    level and optional references to tactics that describe HOW.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    # Required fields
    id: str
    schema_version: str = Field(alias="schema_version")
    title: str
    intent: str
    enforcement: Enforcement

    # Optional core field
    tactic_refs: list[str] = Field(default_factory=list, alias="tactic_refs")

    # Optional enrichment fields
    scope: str | None = None
    procedures: list[str] = Field(default_factory=list)
    integrity_rules: list[str] = Field(default_factory=list, alias="integrity_rules")
    validation_criteria: list[str] = Field(
        default_factory=list, alias="validation_criteria"
    )
    explicit_allowances: list[str] = Field(
        default_factory=list, alias="explicit_allowances"
    )
    references: list[DirectiveReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_lenient_adherence(self) -> "Directive":
        if (
            self.enforcement == Enforcement.LENIENT_ADHERENCE
            and not self.explicit_allowances
        ):
            raise ValueError(
                "explicit_allowances must be provided when enforcement is lenient-adherence"
            )
        return self
