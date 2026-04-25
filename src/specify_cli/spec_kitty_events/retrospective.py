"""Retrospective event contracts.

Defines event type constants, payload models, and domain schema version
for the retrospective contract surface (3.1.0).

Retrospective events are terminal signals — no reducer or state machine
is defined. A mission either has a RetrospectiveCompleted, a
RetrospectiveSkipped, or neither.
"""
from __future__ import annotations

from datetime import datetime
from typing import FrozenSet, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .dossier import ProvenanceRef

# ── Section 1: Schema Version ─────────────────────────────────────────────────

RETROSPECTIVE_SCHEMA_VERSION: str = "3.1.0"

# ── Section 2: Event Type Constants ──────────────────────────────────────────

RETROSPECTIVE_COMPLETED: str = "RetrospectiveCompleted"
RETROSPECTIVE_SKIPPED: str = "RetrospectiveSkipped"

RETROSPECTIVE_EVENT_TYPES: FrozenSet[str] = frozenset({
    RETROSPECTIVE_COMPLETED,
    RETROSPECTIVE_SKIPPED,
})

# ── Section 3: Type Aliases ──────────────────────────────────────────────────

TriggerSourceT = Literal["runtime", "operator", "policy"]

# ── Section 4: Payload Models ────────────────────────────────────────────────


def _assert_iso8601_timestamp(value: object) -> object:
    """Validate an ISO 8601 timestamp across supported Python runtimes.

    Python 3.10's ``datetime.fromisoformat`` rejects a trailing ``Z`` even
    though the fixtures and contract use the RFC 3339 UTC form. Normalize that
    case to ``+00:00`` before parsing.
    """

    if isinstance(value, str):
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
        datetime.fromisoformat(normalized)
    return value


class RetrospectiveCompletedPayload(BaseModel):
    """Payload for RetrospectiveCompleted events.

    Emitted when a retrospective step runs and produces a durable outcome.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    actor: str = Field(..., min_length=1, description="Actor who triggered the retrospective")
    trigger_source: TriggerSourceT = Field(
        ..., description="What initiated the retrospective"
    )
    artifact_ref: Optional[ProvenanceRef] = Field(
        None, description="Reference to retro artifact if one was produced"
    )
    completed_at: str = Field(
        ..., min_length=1, description="ISO 8601 completion timestamp"
    )

    @field_validator("completed_at", mode="before")
    @classmethod
    def _validate_completed_at_iso8601(cls, v: object) -> object:
        return _assert_iso8601_timestamp(v)


class RetrospectiveSkippedPayload(BaseModel):
    """Payload for RetrospectiveSkipped events.

    Emitted when a retrospective step is explicitly skipped.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    actor: str = Field(..., min_length=1, description="Actor who decided to skip")
    trigger_source: TriggerSourceT = Field(
        ..., description="What would have initiated the retrospective"
    )
    skip_reason: str = Field(
        ..., min_length=1, description="Why the retrospective was skipped"
    )
    skipped_at: str = Field(
        ..., min_length=1, description="ISO 8601 skip decision timestamp"
    )

    @field_validator("skipped_at", mode="before")
    @classmethod
    def _validate_skipped_at_iso8601(cls, v: object) -> object:
        return _assert_iso8601_timestamp(v)
