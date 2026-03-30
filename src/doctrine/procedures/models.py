"""
Procedure domain model and value objects.

A Procedure is a reusable, stateful workflow with defined entry/exit
conditions, sequential or branching steps, and explicit actor roles.
Unlike tactics (small composable techniques), procedures orchestrate
multi-step flows that can be paused, resumed, and validated.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from doctrine.artifact_kinds import ArtifactKind


class ActorRole(StrEnum):
    """Who performs a procedure step."""

    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class ProcedureAntiPattern(BaseModel):
    """A named anti-pattern to avoid when following a procedure."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class ProcedureReference(BaseModel):
    """Cross-artifact reference within a procedure."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: ArtifactKind
    id: str
    reason: str | None = None


class ProcedureStep(BaseModel):
    """A single step within a procedure."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    description: str | None = None
    actor: ActorRole = ActorRole.AGENT
    tactic_refs: list[str] = Field(default_factory=list)
    on_success: str | None = None
    on_failure: str | None = None


class Procedure(BaseModel):
    """
    A reusable orchestrated workflow with entry/exit conditions.

    Procedures describe multi-step flows that can be paused, resumed,
    and validated. They coordinate actors (human, agent, system) and
    reference tactics for individual steps.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_version: str = Field(pattern=r"^1\.0$")
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    purpose: str
    entry_condition: str
    exit_condition: str
    steps: list[ProcedureStep] = Field(min_length=1)
    anti_patterns: list[ProcedureAntiPattern] = Field(default_factory=list)
    notes: str | None = None
    references: list[ProcedureReference] = Field(default_factory=list)
