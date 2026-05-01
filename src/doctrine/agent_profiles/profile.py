"""
AgentProfile domain model and value objects.

This module defines the rich AgentProfile Pydantic model with all 6-section
structure per the doctrine framework. Profiles define WHO an agent IS:
purpose, specialization boundaries, collaboration contracts, reasoning modes,
and directive adherence.
"""

from __future__ import annotations

import warnings
from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.functional_validators import BeforeValidator


class Role(str):
    """Half-open role value object.

    Subclasses ``str`` instead of ``StrEnum`` so that custom roles (e.g.
    ``Role("senior-tech-lead")``) are first-class instances without any code
    change.  Well-known roles are declared as class-level constants and
    listed in ``_KNOWN``.

    Why ``str`` and not ``StrEnum``
    --------------------------------
    ``StrEnum`` seals the set of valid values at class definition time.
    Teams introducing project-specific roles (e.g. ``"retrospective-
    facilitator"`` for Phase 6 WP6.6) would need to fork or monkey-patch
    the library.  A plain ``str`` subclass carries the same
    ``role == "implementer"`` ergonomics via ``str.__eq__`` while remaining
    fully open.

    Distinguishing well-known from custom roles
    -------------------------------------------
    ``Role.is_known(role)`` returns ``True`` iff the value belongs to the
    static constant set shipped with this library.  Use this for
    informational checks (capabilities lookup, DRG annotations); do **not**
    use it as a validity gate — custom roles are intentionally valid.

    Future extension points (do not add without a new spec)
    -------------------------------------------------------
    - ``description: str`` field in ``__init__`` to document role semantics
    - YAML-registry loading at import time (``Role.known_roles()``)
    """

    _KNOWN: ClassVar[frozenset[str]] = frozenset()  # populated after class body

    def __new__(cls, value: str) -> Role:
        if not value:
            raise ValueError("Role value must be a non-empty string")
        return str.__new__(cls, value)

    @classmethod
    def is_known(cls, role: Role | str) -> bool:
        """Return True iff *role* is one of the well-known static constants."""
        return str(role) in cls._KNOWN

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema

        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    # ── Well-known constants ──────────────────────────────────────────────
    IMPLEMENTER: ClassVar[Role]
    REVIEWER: ClassVar[Role]
    ARCHITECT: ClassVar[Role]
    DESIGNER: ClassVar[Role]
    PLANNER: ClassVar[Role]
    RESEARCHER: ClassVar[Role]
    CURATOR: ClassVar[Role]
    MANAGER: ClassVar[Role]


# Assign constants after the class body so __new__ is already defined
Role.IMPLEMENTER = Role("implementer")
Role.REVIEWER = Role("reviewer")
Role.ARCHITECT = Role("architect")
Role.DESIGNER = Role("designer")
Role.PLANNER = Role("planner")
Role.RESEARCHER = Role("researcher")
Role.CURATOR = Role("curator")
Role.MANAGER = Role("manager")

# Populate _KNOWN after constants exist
Role._KNOWN = frozenset(
    {
        str(Role.IMPLEMENTER),
        str(Role.REVIEWER),
        str(Role.ARCHITECT),
        str(Role.DESIGNER),
        str(Role.PLANNER),
        str(Role.RESEARCHER),
        str(Role.CURATOR),
        str(Role.MANAGER),
    }
)


# Value Objects (Section components)


class Specialization(BaseModel):
    """Agent specialization definition - what it focuses on and avoids."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    primary_focus: str = Field(alias="primary-focus")
    secondary_awareness: str = Field(default="", alias="secondary-awareness")
    avoidance_boundary: str = Field(default="", alias="avoidance-boundary")
    success_definition: str = Field(default="", alias="success-definition")


class CollaborationContract(BaseModel):
    """Agent collaboration patterns and outputs."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    handoff_to: list[str] = Field(default_factory=list, alias="handoff-to")
    handoff_from: list[str] = Field(default_factory=list, alias="handoff-from")
    works_with: list[str] = Field(default_factory=list, alias="works-with")
    output_artifacts: list[str] = Field(default_factory=list, alias="output-artifacts")
    operating_procedures: list[str] = Field(default_factory=list, alias="operating-procedures")
    canonical_verbs: list[str] = Field(default_factory=list, alias="canonical-verbs")


class SpecializationContext(BaseModel):
    """Declarative conditions defining when a specialist is preferred."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    file_patterns: list[str] = Field(default_factory=list, alias="file-patterns")
    domain_keywords: list[str] = Field(default_factory=list, alias="domain-keywords")
    writing_style: list[str] = Field(default_factory=list, alias="writing-style")
    complexity_preference: list[str] = Field(default_factory=list, alias="complexity-preference")


class ContextSources(BaseModel):
    """Doctrine context sources this agent loads."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    doctrine_layers: list[str] = Field(default_factory=list, alias="doctrine-layers")
    directives: list[str] = Field(default_factory=list)
    additional: list[str] = Field(default_factory=list)


class ModeDefault(BaseModel):
    """Available reasoning mode with description."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    mode: str
    description: str
    use_case: str = Field(alias="use-case")


class DirectiveRef(BaseModel):
    """Reference to a directive with usage rationale."""

    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    rationale: str


class ArtifactRef(BaseModel):
    """Reference to a doctrine artifact with usage rationale."""

    model_config = ConfigDict(frozen=True)

    id: str
    rationale: str


class SelfReviewStep(BaseModel):
    """A single step in the self-review protocol."""

    model_config = ConfigDict(frozen=True)

    name: str
    command: str | None = None
    gate: str


class SelfReviewProtocol(BaseModel):
    """Checklist an agent runs before handing off work."""

    model_config = ConfigDict(frozen=True)

    steps: list[SelfReviewStep] = Field(default_factory=list)


# Main Domain Model


class AgentProfile(BaseModel):
    """
    Rich agent behavioral identity.

    Defines WHO an agent IS through 6-section structure:
    1. Context Sources - doctrine layers/directives
    2. Purpose - mandate (what it does/doesn't do)
    3. Specialization - focus, awareness, boundaries
    4. Collaboration Contract - handoffs, outputs, verbs
    5. Mode Defaults - available reasoning modes
    6. Initialization Declaration - startup acknowledgment
    """

    model_config = ConfigDict(populate_by_name=True)

    # Frontmatter fields
    profile_id: str = Field(alias="profile-id")
    name: str
    description: str = ""
    schema_version: str = Field(default="1.0", alias="schema-version")
    roles: list[Role] = Field(min_length=1)
    avatar_image: str | None = Field(default=None, alias="avatar-image")
    capabilities: list[str] = Field(default_factory=list)
    specializes_from: str | None = Field(default=None, alias="specializes-from")
    routing_priority: int = Field(default=50, ge=0, le=100, alias="routing-priority")
    max_concurrent_tasks: int = Field(default=5, gt=0, alias="max-concurrent-tasks")

    # 6 sections
    context_sources: ContextSources = Field(default_factory=ContextSources, alias="context-sources")
    purpose: str
    specialization: Specialization
    collaboration: CollaborationContract = Field(default_factory=CollaborationContract)
    mode_defaults: list[ModeDefault] = Field(default_factory=list, alias="mode-defaults")
    initialization_declaration: str = Field(default="", alias="initialization-declaration")

    # Sentinel flag — marks this profile as a workflow routing signal, not an agent identity
    sentinel: bool = Field(default=False, alias="sentinel")

    # Optional fields
    specialization_context: SpecializationContext | None = Field(default=None, alias="specialization-context")
    applies_to_languages: list[str] = Field(default_factory=list)
    directive_references: list[DirectiveRef] = Field(default_factory=list, alias="directive-references")
    tactic_references: list[ArtifactRef] = Field(default_factory=list, alias="tactic-references")
    toolguide_references: list[ArtifactRef] = Field(default_factory=list, alias="toolguide-references")
    styleguide_references: list[ArtifactRef] = Field(default_factory=list, alias="styleguide-references")
    self_review_protocol: SelfReviewProtocol | None = Field(default=None, alias="self-review-protocol")
    # Supports both forms:
    #   excluding: [field_name]            → removes entire field from resolved result
    #   excluding: {field_name: [value]}   → removes specific values from list field
    excluding: list[str] | dict[str, list[str]] | None = Field(default=None, alias="excluding")

    @model_validator(mode="before")
    @classmethod
    def _coerce_scalar_role(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        has_role = "role" in data
        has_roles = "roles" in data
        if has_role and not has_roles:
            value = data["role"]
            norm = value.lower() if isinstance(value, str) else value
            profile_id = data.get("profile-id", "<unknown>")
            warnings.warn(
                f"Profile '{profile_id}': the scalar 'role:' field is deprecated. Replace with: roles: [{norm}]",
                DeprecationWarning,
                stacklevel=2,
            )
            data = {k: v for k, v in data.items() if k != "role"}
            data["roles"] = [norm]
        # if has_roles (with or without stale "role" key), pass through unchanged
        # if neither: Pydantic raises ValidationError via min_length=1 on roles
        return data

    @property
    def role(self) -> Role:
        """Primary role — first entry in ``roles``."""
        return self.roles[0]

    @field_validator("routing_priority")
    @classmethod
    def validate_routing_priority(cls, v: int) -> int:
        """Ensure routing_priority is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError("routing_priority must be between 0 and 100")
        return v

    @field_validator("max_concurrent_tasks")
    @classmethod
    def validate_max_concurrent_tasks(cls, v: int) -> int:
        """Ensure max_concurrent_tasks is positive."""
        if v <= 0:
            raise ValueError("max_concurrent_tasks must be greater than 0")
        return v


# Task Context (input for matching)


class TaskContext(BaseModel):
    """Task context for weighted agent matching."""

    language: str | None = None
    framework: str | None = None
    file_paths: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    complexity: str = "medium"
    required_role: Annotated[
        Role | None,
        BeforeValidator(lambda v: Role(v.lower()) if isinstance(v, str) else v),
    ] = None
    active_tasks: dict[str, int] = Field(default_factory=dict)
    current_workload: int | None = None

    @field_validator("complexity")
    @classmethod
    def validate_complexity(cls, v: str) -> str:
        """Ensure complexity is low/medium/high."""
        if v not in {"low", "medium", "high"}:
            raise ValueError("complexity must be 'low', 'medium', or 'high'")
        return v
