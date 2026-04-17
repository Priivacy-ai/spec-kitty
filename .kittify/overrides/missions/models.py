"""Mission schema model.

This module defines the Pydantic model that serves as the single source of
truth for ``mission.schema.yaml``.  The model mirrors the hand-written schema
exactly; it is **not** the runtime domain model used by
``MissionTemplateRepository`` (which operates on raw dicts).

Key design note: the ``states`` array uses a discriminated union—each item
is either a bare string (state id) or a ``MissionStateObject`` with an
explicit ``id`` and optional ``agent_profile``.  JSON Schema represents this
via ``oneOf``; Pydantic via ``str | MissionStateObject``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MissionStateObject(BaseModel):
    """Expanded state with optional agent-profile binding."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str
    agent_profile: str | None = Field(default=None, alias="agent-profile", pattern=r"^[a-z][a-z0-9-]*$")


class MissionTransition(BaseModel):
    """A state transition."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    from_state: str = Field(alias="from")
    to: str
    on: str | None = None
    agent_profile: str | None = Field(default=None, alias="agent-profile", pattern=r"^[a-z][a-z0-9-]*$")


class MissionOrchestration(BaseModel):
    """State-machine definition for the mission."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    states: list[str | MissionStateObject] = Field(min_length=1)
    transitions: list[MissionTransition] = Field(min_length=1)
    guards: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(min_length=1)


class MissionStep(BaseModel):
    """An optional step within the mission."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str
    title: str | None = None
    name: str | None = None
    description: str | None = None
    prompt_template: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    agent_profile: str | None = Field(default=None, alias="agent-profile", pattern=r"^[a-z][a-z0-9-]*$")


class Mission(BaseModel):
    """Top-level mission definition.

    This is the schema-generation model; do not confuse with the runtime
    ``MissionTemplateRepository`` which loads missions from raw YAML.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(pattern=r"^1\.0$")
    key: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    orchestration: MissionOrchestration
    steps: list[MissionStep] = Field(default_factory=list)
