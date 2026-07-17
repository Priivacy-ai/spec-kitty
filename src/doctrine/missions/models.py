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
from collections.abc import Sequence
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
    "MissionStepTemplateRef",
    "Mission",
    "MissionType",
    "validate_action_sequence",
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


class MissionStepTemplateRef(BaseModel):
    """Reference to the content template a step's authored artifact uses.

    A pure ``(artifact_key, template_file)`` pair — a *reference*, never
    inlined content (C-004). ``artifact_key`` is the key the projected
    ``MissionType.template_set`` dict is keyed on (e.g. ``"spec"``), which
    is **not** necessarily the step id (e.g. step id ``specify`` projects
    ``template_set["spec"]``). ``template_file`` is the template's
    filename within the mission type's template directory (e.g.
    ``"spec-template.md"``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_key: str = Field(pattern=IDENTIFIER_PATTERN)
    template_file: str


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
      **Always required** — a step with no authored prompt yet must
      still point at a real (blank-placeholder) file; the schema does
      not relax to accommodate missing content (see WP05).
    * ``agent_profile`` — optional doctrine agent-profile ID. Also
      serves as the step's advisory recommended-role offer — there is
      no separate ``recommended_role`` field.
    * ``guidance`` — optional short inline guidance.
    * ``delegates_to`` — optional list of doctrine artifact refs for
      governance concretization (defaults to empty list).
    * ``depends_on`` — optional list of step IDs that must complete
      before this step (defaults to empty list).
    * ``sequence_index`` — position of this step within the owning
      mission type's ordered action sequence; ``None`` when the step is
      not part of the sequence. Relocated from the mission-type-level
      ``action_sequence`` list (S-B, FR-006).
    * ``in_action_sequence`` — whether this step is a member of the
      owning mission type's ordered action sequence (default ``False``).
    * ``recommended_model_tier`` — optional advisory model-tier offer,
      read through the charter/runtime override seam (WP08); a
      charter/runtime override always takes precedence (NFR-003).
    * ``template`` — optional :class:`MissionStepTemplateRef` pointing
      at the step's content template; ``None`` for steps with no
      built-in template.
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
    sequence_index: int | None = None
    in_action_sequence: bool = False
    recommended_model_tier: str | None = None
    template: MissionStepTemplateRef | None = None

    @property
    def title(self) -> str:
        """Alias for ``display_name``; satisfies runtime callers that use ``.title``."""
        return self.display_name


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


def validate_action_sequence(action_sequence: Sequence[str]) -> None:
    """Assert the ``action_sequence`` invariant: non-empty, unique step IDs.

    Relocated (S-B, WP01) from a raw-field-only ``MissionType`` validator so
    the same check can run against **either** value surface:

    * the raw, YAML-authored ``MissionType.action_sequence`` field (still
      used while the field remains populated during the S-B transition —
      see :meth:`MissionType._validate_action_sequence`), or
    * the **projected** value the WP02 seam (``project_action_sequence``)
      derives from ``MissionStep.in_action_sequence`` /
      ``sequence_index`` once ``action_sequence`` is no longer authored
      directly in ``mission_types/*.yaml`` (WP07 cutover).

    This is the WP01→WP02 contract: the invariant itself is never dropped,
    only the value surface it is asserted against changes.

    Raises
    ------
    ValueError
        If *action_sequence* is empty or contains duplicate step IDs.
    """
    if not action_sequence:
        raise ValueError("action_sequence must be non-empty")
    if len(action_sequence) != len(set(action_sequence)):
        raise ValueError("action_sequence must contain unique step IDs")


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
        extending type inherits fields that are not overridden.
    action_sequence:
        Ordered list of action step ids.  ``None`` when the mission type
        is authored entirely through ``MissionStep.in_action_sequence`` /
        ``sequence_index`` and the projection seam (WP02+) derives the
        sequence instead (S-B cutover, WP07). While present, it must be
        non-empty and contain no duplicates (:func:`validate_action_sequence`).
    template_set:
        Optional mapping from artifact-type key (e.g. ``"spec"``) to
        template filename (e.g. ``"spec-template.md"``).  ``None`` means
        no built-in templates are declared for this type, **or** that the
        projection seam derives it from ``MissionStep.template`` instead
        (S-B cutover, WP07).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    id: str
    display_name: str
    extends: str | None = None
    action_sequence: list[str] | None = None
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
        # Absence-tolerant (S-B, WP01): a mission type authored without a
        # raw `action_sequence` (post-WP07 cutover) skips this check here —
        # the invariant is asserted on the *projected* value instead (see
        # `validate_action_sequence` docstring). While the field is still
        # populated from YAML during the transition, the same invariant
        # continues to apply to the raw value.
        if self.action_sequence is not None:
            validate_action_sequence(self.action_sequence)
        return self
