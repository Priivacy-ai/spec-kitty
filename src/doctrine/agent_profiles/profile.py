"""
AgentProfile domain model and value objects.

This module defines the rich AgentProfile Pydantic model with all 6-section
structure per the doctrine framework. Profiles define WHO an agent IS:
purpose, specialization boundaries, collaboration contracts, reasoning modes,
and directive adherence.
"""

import warnings
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.functional_validators import BeforeValidator


class Role(StrEnum):
    """Controlled vocabulary for agent roles with custom role support."""

    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    ARCHITECT = "architect"
    DESIGNER = "designer"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CURATOR = "curator"
    MANAGER = "manager"


def _coerce_role(value: Any) -> Role | str | None:
    """Coerce known role strings to Role enum, pass custom roles through."""
    if value is None:
        return None
    if isinstance(value, Role):
        return value
    if isinstance(value, str):
        # Try case-insensitive match
        try:
            return Role(value.lower())
        except ValueError:
            warnings.warn(
                f"Custom role '{value}' not in controlled vocabulary. "
                f"Known roles: {', '.join(r.value for r in Role)}",
                UserWarning,
                stacklevel=2,
            )
            return value
    # Fallback for unexpected types - return as string
    return str(value)


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
    role: Annotated[Role | str, BeforeValidator(_coerce_role)] = Role.IMPLEMENTER
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
    directive_references: list[DirectiveRef] = Field(default_factory=list, alias="directive-references")
    # Supports both forms:
    #   excluding: [field_name]            → removes entire field from resolved result
    #   excluding: {field_name: [value]}   → removes specific values from list field
    excluding: list[str] | dict[str, list[str]] | None = Field(default=None, alias="excluding")

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
    required_role: Annotated[Role | str | None, BeforeValidator(_coerce_role)] = None
    active_tasks: dict[str, int] = Field(default_factory=dict)
    current_workload: int | None = None

    @field_validator("complexity")
    @classmethod
    def validate_complexity(cls, v: str) -> str:
        """Ensure complexity is low/medium/high."""
        if v not in {"low", "medium", "high"}:
            raise ValueError("complexity must be 'low', 'medium', or 'high'")
        return v
