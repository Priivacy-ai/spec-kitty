"""Mission schema models — unified MissionStep + supporting types.

This module defines the canonical Pydantic models for the mission schema.
WP01 (mission ``charter-doctrine-mission-type-configuration-01KSWJVX``)
consolidates two previously-fragmented ``MissionStep`` classes into a
single unified model:

* ``doctrine.missions.models.MissionStep`` (legacy schema-validation shape
  for ``mission.yaml``) — REPLACED by the unified model below.
* ``doctrine.mission_step_contracts.models.MissionStep`` (legacy
  governance-delegation shape for step contracts) — that subpackage is
  retired entirely (T007). The legacy step-contract types (`DelegatesTo`,
  `MissionStepContract`, etc.) relocate to
  :mod:`doctrine.missions.step_contracts` so existing on-disk
  ``*.step-contract.yaml`` files keep loading without behaviour change.

The unified :class:`MissionStep` is the canonical entity owned by a
``MissionType`` (per FR-011). Its identity is the compound key
``(mission_type_id, step_id)`` — two steps with the same ``id`` in
different mission types are independent entities.

``step_type`` is the **executor discriminant** (FR-011):

* ``agent`` → ``Decision.kind = step`` (prompt dispatched to LLM)
* ``human_in_loop`` → ``Decision.kind = decision_required``
* ``integration`` → ``Decision.kind = blocked`` (reserved; no providers
  in this release)

``MissionStep.id`` is validated against :data:`IDENTIFIER_PATTERN`
(ASCII kebab-case, per C-003).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: ASCII kebab-case identifier pattern enforced for all
#: :class:`MissionStep` ``id`` values (C-003).
IDENTIFIER_PATTERN = r"^[a-z][a-z0-9-]*$"
_IDENTIFIER_RE = re.compile(IDENTIFIER_PATTERN)

__all__ = [
    "IDENTIFIER_PATTERN",
    "MissionStateObject",
    "MissionTransition",
    "MissionOrchestration",
    "MissionStep",
    "Mission",
    "MissionType",
]


class MissionStateObject(BaseModel):
    """Expanded state with optional agent-profile binding."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str
    agent_profile: str | None = Field(default=None, alias="agent-profile", pattern=IDENTIFIER_PATTERN)


class MissionTransition(BaseModel):
    """A state transition."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    from_state: str = Field(alias="from")
    to: str
    on: str | None = None
    agent_profile: str | None = Field(default=None, alias="agent-profile", pattern=IDENTIFIER_PATTERN)


class MissionOrchestration(BaseModel):
    """State-machine definition for the mission."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    states: list[str | MissionStateObject] = Field(min_length=1)
    transitions: list[MissionTransition] = Field(min_length=1)
    guards: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(min_length=1)


class MissionStep(BaseModel):
    """Unified mission-step model owned by ``MissionType`` (FR-011).

    Identity is ``(mission_type_id, step_id)``. The ``step_type`` field
    is the executor discriminant used by ``spec-kitty next`` to choose
    the dispatch kind (see module docstring).

    Fields:

    * ``id`` — step ID, unique within owning ``MissionType``;
      validated by :data:`IDENTIFIER_PATTERN`.
    * ``display_name`` — human-readable step name.
    * ``step_type`` — one of ``"agent"``, ``"human_in_loop"``,
      ``"integration"``.
    * ``prompt_template`` — relative path to the Markdown prompt file
      (within the same resolution layer as this step descriptor).
    * ``agent_profile`` — optional doctrine agent-profile ID.
    * ``guidance`` — optional short inline guidance.
    * ``delegates_to`` — optional list of doctrine artifact refs for
      governance concretization (defaults to empty list).
    * ``depends_on`` — optional list of step IDs that must complete
      before this step (defaults to empty list).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(pattern=IDENTIFIER_PATTERN)
    display_name: str
    step_type: Literal["agent", "human_in_loop", "integration"]
    prompt_template: str
    agent_profile: str | None = Field(default=None, alias="agent-profile", pattern=IDENTIFIER_PATTERN)
    guidance: str | None = None
    delegates_to: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class Mission(BaseModel):
    """Top-level mission definition.

    This is the schema-generation model used by
    ``scripts/generate_schemas.py`` to emit
    ``src/doctrine/schemas/mission.schema.yaml``. It is **not** the
    runtime domain model used by
    :class:`doctrine.missions.repository.MissionTemplateRepository`
    (which operates on raw dicts).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(pattern=r"^1\.0$")
    key: str = Field(pattern=IDENTIFIER_PATTERN)
    name: str
    description: str | None = None
    orchestration: MissionOrchestration
    steps: list[MissionStep] = Field(default_factory=list)


class MissionType(BaseModel):
    """Governed descriptor for a built-in or extension mission type.

    Each built-in mission type is stored as a YAML file under
    ``src/doctrine/missions/mission_types/{id}.yaml``.  The ``id`` field
    must match the filename stem; this invariant is enforced by
    ``MissionTypeRepository``, not by the model itself.

    Fields
    ------
    schema_version:
        Monotonically increasing integer; baseline = 1.
    id:
        ASCII kebab-case slug (enforced by ``IDENTIFIER_PATTERN``).
    display_name:
        Human-readable label shown in CLI output.
    extends:
        Optional base mission-type id at the same layer.  When set, the
        extending type inherits governance refs that are not overridden.
    action_sequence:
        Ordered list of action step ids.  Must be non-empty and contain
        no duplicates.
    governance_refs:
        Directive / tactic IDs that govern this mission type.
    template_set:
        Optional mapping from artifact-type key (e.g. ``"spec"``) to
        template filename (e.g. ``"spec-template.md"``).  ``None`` means
        no built-in templates are declared for this type.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    id: str
    display_name: str
    extends: str | None = None
    action_sequence: list[str]
    governance_refs: list[str] = Field(default_factory=list)
    template_set: dict[str, str] | None = None

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not _IDENTIFIER_RE.match(v):
            raise ValueError(
                f"MissionType id {v!r} does not match IDENTIFIER_PATTERN "
                f"{IDENTIFIER_PATTERN!r}"
            )
        return v

    @model_validator(mode="after")
    def _validate_action_sequence(self) -> MissionType:
        if not self.action_sequence:
            raise ValueError("action_sequence must be non-empty")
        if len(self.action_sequence) != len(set(self.action_sequence)):
            raise ValueError("action_sequence must contain unique step IDs")
        return self
