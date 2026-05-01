"""RACI inference and resolution engine.

Provides deterministic RACI role assignment for mission steps.
All operations are local-only, offline, and deterministic.
"""

# Internalized from spec-kitty-runtime 0.4.3 as part of
# `shared-package-boundary-cutover-01KQ22DS` (mission). See
# `runtime-standalone-package-retirement-01KQ20Z8` for the upstream
# public-API inventory.
from __future__ import annotations

from typing import Any, Literal, cast

from specify_cli.next._internal_runtime.schema import (
    AuditStep,
    MissionPolicySnapshot,
    MissionRuntimeError,
    PromptStep,
    RACIAssignment,
    RACIEscalationPayload,
    RACIRoleBinding,
    ResolvedRACIBinding,
)


def infer_raci(
    step: PromptStep | AuditStep,
    mission_policy: MissionPolicySnapshot,
) -> ResolvedRACIBinding:
    """Infer default RACI bindings from step type.

    Deterministic rules:
    - PromptStep → R:llm, A:human (mission_owner) — rule: "prompt_default"
    - AuditStep (blocking) → R:human, A:human — rule: "audit_blocking"
    - AuditStep (advisory) → R:llm, A:human — rule: "audit_advisory"

    Args:
        step: The mission step to infer RACI for.
        mission_policy: Current mission policy snapshot.

    Returns:
        ResolvedRACIBinding with source="inferred" and the applicable rule name.
    """
    if isinstance(step, AuditStep):
        if step.audit.enforcement == "blocking":
            return ResolvedRACIBinding(
                step_id=step.id,
                responsible=RACIRoleBinding(actor_type="human"),
                accountable=RACIRoleBinding(actor_type="human"),
                source="inferred",
                inferred_rule="audit_blocking",
            )
        else:
            # advisory
            return ResolvedRACIBinding(
                step_id=step.id,
                responsible=RACIRoleBinding(actor_type="llm"),
                accountable=RACIRoleBinding(actor_type="human"),
                source="inferred",
                inferred_rule="audit_advisory",
            )
    else:
        # PromptStep
        return ResolvedRACIBinding(
            step_id=step.id,
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
            source="inferred",
            inferred_rule="prompt_default",
        )


def validate_raci_assignment(
    assignment: RACIAssignment,
    step: PromptStep | AuditStep,
) -> tuple[bool, list[str]]:
    """Validate RACI assignment against P0 invariants.

    Checks:
    - Accountable must be human
    - For blocking audit steps: responsible must be human
    - LLM never in R/A for blocking audit decisions

    Args:
        assignment: The RACI assignment to validate.
        step: The step this assignment applies to.

    Returns:
        (is_valid, error_messages) tuple.
    """
    errors: list[str] = []

    # P0: accountable must always be human
    if assignment.accountable.actor_type != "human":
        errors.append(f"P0 invariant violation: accountable must be human, got '{assignment.accountable.actor_type}'")

    # For blocking audit: responsible must be human
    if isinstance(step, AuditStep) and step.audit.enforcement == "blocking" and assignment.responsible.actor_type != "human":
        errors.append(f"Blocking audit step '{step.id}': responsible must be human, got '{assignment.responsible.actor_type}'")

    return (len(errors) == 0, errors)


def resolve_raci(
    step: PromptStep | AuditStep,
    inputs: dict[str, Any],
    mission_policy: MissionPolicySnapshot,
) -> ResolvedRACIBinding:
    """Resolve RACI to concrete actors using runtime inputs.

    Resolution order:
    1. If step has explicit raci block → use it (source="explicit")
    2. Otherwise → infer defaults (source="inferred")

    Actor ID resolution:
    - actor_type="human" with no actor_id → resolved from inputs["mission_owner_id"]
    - actor_type="llm" with no actor_id → resolved from inputs.get("agent_id")
    - actor_type="service" with no actor_id → resolved from inputs.get("service_id")

    Fail-closed: unresolvable R/A roles raise MissionRuntimeError with
    RACIEscalationPayload.

    Args:
        step: The mission step to resolve RACI for.
        inputs: Runtime inputs dict (mission_owner_id, agent_id, etc.).
        mission_policy: Current mission policy snapshot.

    Returns:
        ResolvedRACIBinding with concrete actor IDs where possible.

    Raises:
        MissionRuntimeError: When a required role (R/A) cannot be resolved.
    """
    if step.raci is not None:
        # Explicit override path
        assignment = step.raci
        override_reason = step.raci_override_reason  # guaranteed non-None by schema validator

        # Validate the explicit assignment
        is_valid, errors = validate_raci_assignment(assignment, step)
        if not is_valid:
            raise MissionRuntimeError(f"Invalid explicit RACI for step '{step.id}': {'; '.join(errors)}")

        responsible = _resolve_actor(assignment.responsible, "responsible", step.id, inputs)
        accountable = _resolve_actor(assignment.accountable, "accountable", step.id, inputs)
        consulted = [_resolve_actor_optional(c, inputs) for c in assignment.consulted]
        informed = [_resolve_actor_optional(i, inputs) for i in assignment.informed]

        return ResolvedRACIBinding(
            step_id=step.id,
            responsible=responsible,
            accountable=accountable,
            consulted=consulted,
            informed=informed,
            source="explicit",
            override_reason=override_reason,
        )
    else:
        # Inferred path
        inferred = infer_raci(step, mission_policy)

        responsible = _resolve_actor(inferred.responsible, "responsible", step.id, inputs)
        accountable = _resolve_actor(inferred.accountable, "accountable", step.id, inputs)
        consulted = [_resolve_actor_optional(c, inputs) for c in inferred.consulted]
        informed = [_resolve_actor_optional(i, inputs) for i in inferred.informed]

        return ResolvedRACIBinding(
            step_id=step.id,
            responsible=responsible,
            accountable=accountable,
            consulted=consulted,
            informed=informed,
            source="inferred",
            inferred_rule=inferred.inferred_rule,
        )


def _resolve_actor(
    binding: RACIRoleBinding,
    role_name: str,
    step_id: str,
    inputs: dict[str, Any],
) -> RACIRoleBinding:
    """Resolve a required actor binding to a concrete actor ID.

    Fail-closed: raises MissionRuntimeError if the actor cannot be resolved.
    """
    if binding.actor_id is not None:
        return binding

    resolved_id = _lookup_actor_id(binding.actor_type, inputs)
    if resolved_id is None:
        input_key = _actor_type_to_input_key(binding.actor_type)
        escalation = RACIEscalationPayload(
            run_id=inputs.get("run_id", "unknown"),
            step_id=step_id,
            unresolved_role=cast(
                Literal["responsible", "accountable"],
                role_name if role_name in ("responsible", "accountable") else "responsible",
            ),
            actor_type_expected=binding.actor_type,
            reason=f"Cannot resolve {role_name} actor: '{input_key}' not found in inputs",
            resolution_hint=f"Provide '{input_key}' in mission inputs",
        )
        raise MissionRuntimeError(f"RACI escalation for step '{step_id}': {escalation.reason}")

    return RACIRoleBinding(actor_type=binding.actor_type, actor_id=resolved_id)


def _resolve_actor_optional(
    binding: RACIRoleBinding,
    inputs: dict[str, Any],
) -> RACIRoleBinding:
    """Resolve an optional actor binding (C/I roles).

    Non-blocking: returns the binding as-is if actor_id cannot be resolved.
    """
    if binding.actor_id is not None:
        return binding

    resolved_id = _lookup_actor_id(binding.actor_type, inputs)
    if resolved_id is not None:
        return RACIRoleBinding(actor_type=binding.actor_type, actor_id=resolved_id)
    return binding


def _lookup_actor_id(actor_type: str, inputs: dict[str, Any]) -> str | None:
    """Look up actor ID from inputs based on actor type."""
    key = _actor_type_to_input_key(actor_type)
    value = inputs.get(key)
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return None


def _actor_type_to_input_key(actor_type: str) -> str:
    """Map actor type to the expected input key."""
    mapping = {
        "human": "mission_owner_id",
        "llm": "agent_id",
        "service": "service_id",
    }
    return mapping.get(actor_type, actor_type)
