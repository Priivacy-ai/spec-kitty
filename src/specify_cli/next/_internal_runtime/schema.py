"""Core runtime types and YAML mission-template loading."""

# Internalized from spec-kitty-runtime 0.4.3 as part of
# `shared-package-boundary-cutover-01KQ22DS` (mission). See
# `runtime-standalone-package-retirement-01KQ20Z8` for the upstream
# public-API inventory.
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MissionRuntimeError(RuntimeError):
    """Raised for runtime loading/planning errors."""


# ---------------------------------------------------------------------------
# Domain value objects
# ---------------------------------------------------------------------------

from spec_kitty_events.mission_next import RuntimeActorIdentity

ActorIdentity = RuntimeActorIdentity


class CommitContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    head_sha: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)
    dirty: bool = False


class DecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(..., min_length=1)
    step_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    options: list[str] = Field(default_factory=list)
    requested_by: ActorIdentity
    requested_at: datetime


class DecisionAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    answered_by: ActorIdentity
    answered_at: datetime


# ---------------------------------------------------------------------------
# RACI role model types (WP06)
# ---------------------------------------------------------------------------

class RACIRoleBinding(BaseModel):
    """Single actor-role binding in a RACI assignment."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_type: Literal["human", "llm", "service"]
    actor_id: str | None = None


class RACIAssignment(BaseModel):
    """Per-step RACI assignment (explicit or inferred).

    Enforces P0 invariant: accountable must always be human.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    responsible: RACIRoleBinding
    accountable: RACIRoleBinding
    consulted: list[RACIRoleBinding] = Field(default_factory=list)
    informed: list[RACIRoleBinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_p0_accountable_human(self) -> RACIAssignment:
        if self.accountable.actor_type != "human":
            raise ValueError(
                f"P0 invariant violation: accountable must be human, "
                f"got '{self.accountable.actor_type}'"
            )
        return self


class ResolvedRACIBinding(BaseModel):
    """Fully resolved RACI binding with provenance metadata."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    responsible: RACIRoleBinding
    accountable: RACIRoleBinding
    consulted: list[RACIRoleBinding] = Field(default_factory=list)
    informed: list[RACIRoleBinding] = Field(default_factory=list)
    source: Literal["inferred", "explicit"]
    inferred_rule: str | None = None
    override_reason: str | None = None

    @model_validator(mode="after")
    def _validate_provenance(self) -> ResolvedRACIBinding:
        if self.source == "explicit" and not self.override_reason:
            raise ValueError(
                "ResolvedRACIBinding with source='explicit' requires non-empty override_reason"
            )
        if self.source == "inferred" and not self.inferred_rule:
            raise ValueError(
                "ResolvedRACIBinding with source='inferred' requires non-empty inferred_rule"
            )
        if self.source == "inferred" and self.override_reason is not None:
            raise ValueError(
                "ResolvedRACIBinding with source='inferred' must not have override_reason"
            )
        return self


class RACIEscalationPayload(BaseModel):
    """Structured escalation payload for unresolvable RACI roles."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    step_id: str
    decision_id: str | None = None
    unresolved_role: Literal["responsible", "accountable"]
    actor_type_expected: str
    resolution_candidates: list[dict[str, Any]] = Field(default_factory=list)
    reason: str
    resolution_hint: str


# ---------------------------------------------------------------------------
# Context contract types (V1)
# ---------------------------------------------------------------------------

class ContextType(BaseModel):
    """Describes a single context type required, optional, or emitted by a step."""
    model_config = ConfigDict(frozen=True)

    type: str = Field(..., min_length=1, description="Context type name (e.g., 'feature_binding')")
    deterministic: bool = Field(
        default=True,
        description="True if this context resolves deterministically (offline, local-first)"
    )
    cardinality: Literal["one", "many"] = Field(
        default="one",
        description="Expected binding count: 'one' for single binding, 'many' for multiple"
    )
    validation: dict[str, Any] | None = Field(
        default=None,
        description="Validation rules like artifact_exists, path_exists, slug_format"
    )
    resolver_ref: str | None = Field(
        default=None,
        description="Reference to custom resolver for unknown types"
    )

    def validate_binding(self, value: Any) -> tuple[bool, str | None]:
        """Validate a bound value against this context type's rules.

        Delegates to the canonical ``engine.validate_binding`` implementation so
        that ``ContextType.validate_binding()`` and the engine-level
        ``validate_binding()`` always agree on outcomes.

        Args:
            value: The value to validate against validation rules

        Returns:
            (is_valid, error_message) - tuple where is_valid is True if validation passes,
            error_message is None on success or contains the error message on failure
        """
        # Avoid circular import at module level — engine imports schema.
        from specify_cli.next._internal_runtime.engine import validate_binding as _engine_validate
        return _engine_validate(value, self)


class StepContextContract(BaseModel):
    """Contract describing context bindings for a mission step."""
    model_config = ConfigDict(frozen=True)

    requires: list[ContextType] = Field(
        default_factory=list,
        description="Contexts that MUST resolve before step execution"
    )
    optional: list[ContextType] = Field(
        default_factory=list,
        description="Contexts that may enrich step but are not blocking"
    )
    emits: list[ContextType] = Field(
        default_factory=list,
        description="Contexts produced/updated on step completion"
    )

    @field_validator("requires", "optional", "emits")
    @classmethod
    def validate_context_types(cls, v: list[ContextType]) -> list[ContextType]:
        """Schema-level validation of context types at parse-time.

        Enforces that unknown context types have a resolver_ref (or are registered builtins).
        """
        registry = ContextTypeRegistry()
        for ctx_type in v:
            # Check if the type is known (registered or has explicit resolver)
            if not registry.is_registered(ctx_type.type) and not ctx_type.resolver_ref:
                raise ValueError(
                    f"Unknown context type '{ctx_type.type}' - must be registered in ContextTypeRegistry "
                    f"or have resolver_ref provided"
                )
        return v

    def validate_contract(self, context_type_registry: ContextTypeRegistry | None = None) -> tuple[bool, list[str]]:
        """Validate the contract structure and context type definitions.

        Returns:
            (is_valid, error_messages) tuple
        """
        errors: list[str] = []
        registry = context_type_registry or ContextTypeRegistry()

        # Validate all context types
        for ctx_type in self.requires + self.optional + self.emits:
            # Check if type is known (built-in or has resolver_ref)
            if not registry.is_registered(ctx_type.type) and not ctx_type.resolver_ref:
                errors.append(f"Unknown context type '{ctx_type.type}' without resolver_ref")

        # Check for circular dependencies (simplified: A requires output from B, B requires A)
        requires_names = {c.type for c in self.requires}
        emits_names = {c.type for c in self.emits}

        # A step cannot require what it emits (circular in same step)
        overlap = requires_names & emits_names
        if overlap:
            errors.append(f"Step requires and emits same context(s): {overlap}")

        return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Context Type Registry (V1 baseline)
# ---------------------------------------------------------------------------

class ContextTypeRegistry:
    """Registry of built-in and custom context types."""

    # V1 baseline context types
    _BUILTIN_TYPES = {
        "feature_binding": ContextType(
            type="feature_binding",
            deterministic=True,
            cardinality="one"
        ),
        "spec_artifact": ContextType(
            type="spec_artifact",
            deterministic=True,
            cardinality="one",
            validation={"artifact_exists": True}
        ),
        "plan_artifact": ContextType(
            type="plan_artifact",
            deterministic=True,
            cardinality="one",
            validation={"artifact_exists": True}
        ),
        "tasks_artifact": ContextType(
            type="tasks_artifact",
            deterministic=True,
            cardinality="one",
            validation={"artifact_exists": True}
        ),
        "wp_binding": ContextType(
            type="wp_binding",
            deterministic=True,
            cardinality="many"
        ),
        "target_branch": ContextType(
            type="target_branch",
            deterministic=True,
            cardinality="one",
            validation={"slug_format": "[a-z0-9-]+"}
        ),
        "contracts_dir": ContextType(
            type="contracts_dir",
            deterministic=True,
            cardinality="one",
            validation={"path_exists": True}
        ),
        "research_artifact": ContextType(
            type="research_artifact",
            deterministic=True,
            cardinality="one",
            validation={"artifact_exists": True}
        ),
    }

    def __init__(self, custom_types: dict[str, ContextType] | None = None):
        """Initialize registry with optional custom types."""
        self._types = deepcopy(self._BUILTIN_TYPES)
        if custom_types:
            self._types.update(custom_types)

    def get_builtin_type(self, name: str) -> ContextType:
        """Get a built-in context type by name.

        Raises:
            ValueError if type is unknown and has no custom resolver
        """
        if name not in self._types:
            raise ValueError(f"Unknown context type: {name}")
        return self._types[name]

    def is_registered(self, name: str) -> bool:
        """Check if a context type is registered."""
        return name in self._types

    def register_custom_type(self, context_type: ContextType) -> None:
        """Register a custom context type."""
        self._types[context_type.type] = context_type

    def get_all_types(self) -> dict[str, ContextType]:
        """Get all registered types (builtin + custom)."""
        return dict(self._types)


# ---------------------------------------------------------------------------
# Audit types
# ---------------------------------------------------------------------------

class AuditConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    trigger_mode: Literal["manual", "post_merge", "both"]
    enforcement: Literal["advisory", "blocking"]
    label: str | None = None
    metadata: dict[str, Any] | None = None


class SignificanceBlock(BaseModel):
    """Optional significance declaration for an audit step.

    Declares dimension scores and hard-trigger classes that determine
    the routing band (low/medium/high) for the audit gate.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    dimensions: dict[str, int]  # dimension_name → score (0-3)
    hard_triggers: list[str] = Field(default_factory=list)  # hard-trigger class IDs

    @model_validator(mode="after")
    def _validate_dimensions(self) -> SignificanceBlock:
        from specify_cli.next._internal_runtime.significance import validate_dimension_scores, HARD_TRIGGER_REGISTRY
        validate_dimension_scores(self.dimensions)
        for trigger_id in self.hard_triggers:
            if trigger_id not in HARD_TRIGGER_REGISTRY:
                raise ValueError(f"Unknown hard-trigger class: {trigger_id}")
        return self


class AuditStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = ""
    audit: AuditConfig
    significance: SignificanceBlock | None = None
    depends_on: list[str] = Field(default_factory=list)
    raci: RACIAssignment | None = None
    raci_override_reason: str | None = None

    @model_validator(mode="after")
    def _validate_raci_override_reason(self) -> AuditStep:
        if self.raci is not None and not self.raci_override_reason:
            raise ValueError(
                f"Step '{self.id}': explicit raci block requires non-empty raci_override_reason"
            )
        if self.raci is None and self.raci_override_reason is not None:
            raise ValueError(
                f"Step '{self.id}': raci_override_reason provided without raci block"
            )
        return self


# ---------------------------------------------------------------------------
# Mission template types
# ---------------------------------------------------------------------------

class MissionMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    description: str = Field(default="")


class PromptStep(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = Field(default="")
    prompt: str | None = None
    prompt_template: str | None = None
    expected_output: str | None = None
    requires_inputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    raci: RACIAssignment | None = None
    raci_override_reason: str | None = None
    agent_profile: str | None = Field(
        default=None,
        alias="agent-profile",
        description="Profile id used as profile_hint when this step dispatches via composition.",
    )
    contract_ref: str | None = Field(
        default=None,
        description="Optional ID of an existing MissionStepContract; when set, contract_synthesis skips this step.",
    )

    @model_validator(mode="after")
    def _validate_raci_override_reason(self) -> PromptStep:
        if self.raci is not None and not self.raci_override_reason:
            raise ValueError(
                f"Step '{self.id}': explicit raci block requires non-empty raci_override_reason"
            )
        if self.raci is None and self.raci_override_reason is not None:
            raise ValueError(
                f"Step '{self.id}': raci_override_reason provided without raci block"
            )
        return self


class MissionPolicySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    strictness: Literal["off", "medium", "max"] = "medium"
    default_route: str = "same_llm_context"
    extras: dict[str, Any] = Field(default_factory=dict)


class MissionTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    mission: MissionMeta
    steps: list[PromptStep] = Field(default_factory=list)
    audit_steps: list[AuditStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Discovery types
# ---------------------------------------------------------------------------

class DiscoveredMission(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    path: str
    origin: str
    precedence_tier: str
    selected: bool = True


# ---------------------------------------------------------------------------
# Mission pack manifest types
# ---------------------------------------------------------------------------

class MissionPackMeta(BaseModel):
    """Pack-level metadata."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    description: str = Field(default="")


class MissionPackEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)


class MissionPackManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    pack: MissionPackMeta
    missions: list[MissionPackEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Runtime context types
# ---------------------------------------------------------------------------

class StepContextBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    mission_key: str
    step_id: str
    step_title: str
    step_description: str
    expected_output: str | None = None
    policy_snapshot: MissionPolicySnapshot
    actor_context: dict[str, Any] = Field(default_factory=dict)


class NextDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["step", "decision_required", "blocked", "terminal"]
    run_id: str
    mission_key: str
    step_id: str | None = None
    step_title: str | None = None
    prompt: str | None = None
    context: StepContextBundle | None = None
    decision_id: str | None = None      # for decision_required
    input_key: str | None = None        # for input-keyed decisions (requires_inputs)
    question: str | None = None
    options: list[str] | None = None    # suggested answer options
    reason: str | None = None


class MissionRunSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    mission_key: str
    template_path: str                                          # resolved file path for drift detection
    template_hash: str                                          # SHA-256 of frozen YAML
    policy_snapshot: MissionPolicySnapshot = Field(default_factory=MissionPolicySnapshot)
    completed_steps: list[str] = Field(default_factory=list)
    issued_step_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    decisions: dict[str, Any] = Field(default_factory=dict)     # decision_id -> answer data
    pending_decisions: dict[str, Any] = Field(default_factory=dict)  # decision_id -> request data
    blocked_reason: str | None = None


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def load_mission_template_file(path: Path) -> MissionTemplate:
    """Load a mission template from a mission.yaml file."""
    if not path.exists():
        raise MissionRuntimeError(f"Mission template not found: {path}")

    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise MissionRuntimeError(f"Mission template must be a mapping: {path}")

    # Allow lightweight shorthand with top-level key/name/version.
    if "mission" not in raw:
        mission_meta = {
            "key": raw.get("key") or raw.get("name") or path.parent.name,
            "name": raw.get("name") or path.parent.name,
            "version": str(raw.get("version", "1.0.0")),
            "description": raw.get("description", ""),
        }
        raw = {
            "mission": mission_meta,
            "steps": raw.get("steps", []),
            "audit_steps": raw.get("audit_steps", []),
        }

    template = MissionTemplate.model_validate(raw)
    if not template.steps and not template.audit_steps:
        raise MissionRuntimeError(f"Mission template has no steps: {path}")
    return template
