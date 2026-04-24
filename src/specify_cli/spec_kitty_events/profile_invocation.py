"""Profile invocation event contracts.

Defines event type constants, payload model, and domain schema version
for the profile invocation contract surface (3.1.0).
"""

from __future__ import annotations

from typing import FrozenSet, Optional

from pydantic import BaseModel, ConfigDict, Field

from .mission_next import RuntimeActorIdentity

# ── Section 1: Constants ─────────────────────────────────────────────────────

PROFILE_INVOCATION_SCHEMA_VERSION: str = "3.1.0"

PROFILE_INVOCATION_STARTED: str = "ProfileInvocationStarted"
PROFILE_INVOCATION_COMPLETED: str = "ProfileInvocationCompleted"  # Reserved — payload contract deferred
PROFILE_INVOCATION_FAILED: str = "ProfileInvocationFailed"  # Reserved — payload contract deferred

PROFILE_INVOCATION_EVENT_TYPES: FrozenSet[str] = frozenset({
    PROFILE_INVOCATION_STARTED,
})
"""Validatable event types. Consumers can call validate_event() for these."""

PROFILE_INVOCATION_RESERVED_TYPES: FrozenSet[str] = frozenset({
    PROFILE_INVOCATION_COMPLETED,
    PROFILE_INVOCATION_FAILED,
})
"""Name-reserved types with deferred payload contracts. Not yet validatable."""

# ── Section 2: Payload Models ────────────────────────────────────────────────


class ProfileInvocationStartedPayload(BaseModel):
    """Payload for ProfileInvocationStarted events.

    Emitted when the runtime begins executing a step under a resolved agent profile.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    run_id: str = Field(..., min_length=1, description="Run identifier from MissionRunStarted")
    step_id: str = Field(..., min_length=1, description="Step being executed")
    action: str = Field(..., min_length=1, description="Bound action name")
    profile_slug: str = Field(..., min_length=1, description="Resolved agent profile slug")
    profile_version: Optional[str] = Field(
        None, min_length=1, description="Profile version if versioned profiles are in use"
    )
    actor: RuntimeActorIdentity = Field(..., description="Runtime actor identity")
    governance_scope: Optional[str] = Field(
        None, min_length=1, description="Governance scope identifier"
    )
