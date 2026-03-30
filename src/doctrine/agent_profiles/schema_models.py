"""Agent-profile schema models.

This module defines the Pydantic model that serves as the single source of
truth for ``agent-profile.schema.yaml``.  It is intentionally **separate**
from the domain model in ``profile.py`` because:

* The schema uses kebab-case field names (``profile-id``, ``agent-profile``),
  while the domain model uses snake_case with aliases.
* The schema includes reference sections (``tactic-references``,
  ``toolguide-references``, ``styleguide-references``, ``self-review-protocol``)
  that the domain model does not carry.
* The domain model has runtime fields (``sentinel``, ``excluding``) that are
  not part of the canonical schema.
* The domain model uses ``BeforeValidator`` / ``Role`` coercion that should
  not leak into schema generation.

The generated schema targets Draft 2020-12 (like all other generated schemas).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class AgentContextSources(BaseModel):
    """Doctrine context sources this agent loads."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    doctrine_layers: list[str] = Field(default_factory=list, alias="doctrine-layers")
    directives: list[str] = Field(default_factory=list)
    tactics: list[str] = Field(default_factory=list)
    toolguides: list[str] = Field(default_factory=list)
    styleguides: list[str] = Field(default_factory=list)
    additional: list[str] = Field(default_factory=list)


class AgentSpecialization(BaseModel):
    """Agent specialization definition."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    primary_focus: str = Field(alias="primary-focus")
    secondary_awareness: str | None = Field(default=None, alias="secondary-awareness")
    avoidance_boundary: str | None = Field(default=None, alias="avoidance-boundary")
    success_definition: str | None = Field(default=None, alias="success-definition")


class AgentCollaboration(BaseModel):
    """Agent collaboration patterns and outputs."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    handoff_to: list[str] = Field(default_factory=list, alias="handoff-to")
    handoff_from: list[str] = Field(default_factory=list, alias="handoff-from")
    works_with: list[str] = Field(default_factory=list, alias="works-with")
    output_artifacts: list[str] = Field(default_factory=list, alias="output-artifacts")
    operating_procedures: list[str] = Field(default_factory=list, alias="operating-procedures")
    canonical_verbs: list[str] = Field(default_factory=list, alias="canonical-verbs")


class AgentModeDefault(BaseModel):
    """Available reasoning mode with description."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    mode: str
    description: str
    use_case: str = Field(alias="use-case")


class AgentSpecializationContext(BaseModel):
    """Declarative conditions defining when a specialist is preferred."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    file_patterns: list[str] = Field(default_factory=list, alias="file-patterns")
    domain_keywords: list[str] = Field(default_factory=list, alias="domain-keywords")
    writing_style: list[str] = Field(default_factory=list, alias="writing-style")
    complexity_preference: list[str] = Field(default_factory=list, alias="complexity-preference")


class AgentDirectiveReference(BaseModel):
    """Reference to a directive with usage rationale."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    name: str
    rationale: str


class AgentTacticReference(BaseModel):
    """Reference to a tactic with usage rationale."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    rationale: str


class AgentToolguideReference(BaseModel):
    """Reference to a toolguide with usage rationale."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    rationale: str


class AgentStyleguideReference(BaseModel):
    """Reference to a styleguide with usage rationale."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    rationale: str


class SelfReviewStep(BaseModel):
    """A single step in the self-review protocol."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    command: str | None = None
    gate: str


class SelfReviewProtocol(BaseModel):
    """Self-review checklist the agent runs before handing off work."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    steps: list[SelfReviewStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level schema model
# ---------------------------------------------------------------------------


class AgentProfileSchema(BaseModel):
    """Rich agent profile schema with 6-section structure.

    This is the **schema-generation** model. For the runtime domain model
    see ``doctrine.agent_profiles.profile.AgentProfile``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    # Core identity
    profile_id: str = Field(alias="profile-id", pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    description: str | None = None
    schema_version: str | None = Field(
        default=None, alias="schema-version", pattern=r"^1\.0$"
    )
    purpose: str
    role: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    specializes_from: str | None = Field(default=None, alias="specializes-from")
    routing_priority: int | None = Field(default=None, alias="routing-priority", ge=0, le=100)
    max_concurrent_tasks: int | None = Field(default=None, alias="max-concurrent-tasks", ge=1)

    # Section 1: Context sources
    context_sources: AgentContextSources | None = Field(default=None, alias="context-sources")

    # Section 2: Specialization
    specialization: AgentSpecialization

    # Section 3: Collaboration contract
    collaboration: AgentCollaboration | None = None

    # Section 4: Mode defaults
    mode_defaults: list[AgentModeDefault] = Field(default_factory=list, alias="mode-defaults")

    # Section 5: Initialization declaration
    initialization_declaration: str | None = Field(default=None, alias="initialization-declaration")

    # Section 6: Specialization context
    specialization_context: AgentSpecializationContext | None = Field(
        default=None, alias="specialization-context"
    )

    # Directive references
    directive_references: list[AgentDirectiveReference] = Field(
        default_factory=list, alias="directive-references"
    )

    # Tactic references
    tactic_references: list[AgentTacticReference] = Field(
        default_factory=list, alias="tactic-references"
    )

    # Toolguide references
    toolguide_references: list[AgentToolguideReference] = Field(
        default_factory=list, alias="toolguide-references"
    )

    # Styleguide references
    styleguide_references: list[AgentStyleguideReference] = Field(
        default_factory=list, alias="styleguide-references"
    )

    # Self-review protocol
    self_review_protocol: SelfReviewProtocol | None = Field(
        default=None, alias="self-review-protocol"
    )
