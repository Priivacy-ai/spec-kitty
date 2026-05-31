"""
MissionStepContract domain model.

Defines the structural steps of a mission action without embedding governance.
Each step may delegate concretization to a doctrine artifact (directive, tactic,
paradigm) and/or carry freeform guidance for additional context.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


from doctrine.artifact_kinds import ArtifactKind


class DelegatesTo(BaseModel):
    """Delegation link from a step to doctrine artifacts for concretization.

    The ``kind`` identifies the artifact type (paradigm, tactic, directive, etc.).
    The ``candidates`` list names which artifacts *could* concretize this step —
    the charter's selections determine which one actually applies at runtime.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ArtifactKind
    candidates: list[str] = Field(min_length=1)


class MissionStepInput(BaseModel):
    """Declared runtime input for a command-backed mission step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    flag: str = Field(min_length=1)
    source: str = Field(min_length=1)
    optional: bool = False


class MissionStep(BaseModel):
    """A single structural step within a mission action contract.

    Steps describe *what* must happen, not *how* (governance comes from doctrine).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    description: str
    command: str | None = None
    inputs: list[MissionStepInput] = Field(default_factory=list)
    delegates_to: DelegatesTo | None = None
    guidance: str | None = None


class MissionStepContract(BaseModel):
    """Contract defining the structural steps of a mission action.

    A step contract replaces inline governance prose in command templates with a
    structured, schema-validated sequence of steps. Each step may delegate its
    concretization to doctrine artifacts via ``delegates_to`` and/or carry
    freeform ``guidance`` for step-specific instructions.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    id: str
    schema_version: str = Field(alias="schema_version")
    action: str
    mission: str
    steps: list[MissionStep] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_step_ids(self) -> "MissionStepContract":
        ids = [s.id for s in self.steps]
        duplicates = [sid for sid in ids if ids.count(sid) > 1]
        if duplicates:
            raise ValueError(
                f"duplicate step IDs: {sorted(set(duplicates))}"
            )
        return self
