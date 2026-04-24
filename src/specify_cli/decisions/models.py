"""Pydantic v2 models and enums for the Decision Moment ledger.

Defines OriginFlow, DecisionStatus, DecisionErrorCode enums and
the frozen IndexEntry / DecisionIndex models used by both the store
and the service layer.  Also defines DecisionOpenResponse and
DecisionTerminalResponse for CLI output contracts.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


__all__ = [
    "OriginFlow",
    "DecisionStatus",
    "DecisionErrorCode",
    "IndexEntry",
    "DecisionIndex",
    "DecisionOpenResponse",
    "DecisionTerminalResponse",
    "logical_key",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OriginFlow(StrEnum):
    """The CLI workflow that opened this decision."""

    CHARTER = "charter"
    SPECIFY = "specify"
    PLAN = "plan"


class DecisionStatus(StrEnum):
    """Lifecycle state of a decision moment."""

    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    CANCELED = "canceled"


class DecisionErrorCode(StrEnum):
    """Machine-readable error codes for decision service failures."""

    MISSING_STEP_OR_SLOT = "DECISION_MISSING_STEP_OR_SLOT"
    ALREADY_CLOSED = "DECISION_ALREADY_CLOSED"
    TERMINAL_CONFLICT = "DECISION_TERMINAL_CONFLICT"
    NOT_FOUND = "DECISION_NOT_FOUND"
    MISSION_NOT_FOUND = "MISSION_NOT_FOUND"
    VERIFY_DRIFT = "DECISION_VERIFY_DRIFT"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class IndexEntry(BaseModel):
    """A single decision moment record as stored in index.json."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    origin_flow: OriginFlow
    step_id: str | None = None
    slot_key: str | None = None
    input_key: Annotated[str, Field(min_length=1)]
    question: Annotated[str, Field(min_length=1)]
    options: tuple[str, ...] = ()
    status: DecisionStatus
    final_answer: str | None = None
    rationale: str | None = None
    other_answer: bool = False
    summary_json: dict[str, str] | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    mission_id: str
    mission_slug: str

    @model_validator(mode="after")
    def _step_or_slot(self) -> IndexEntry:
        """Require at least one of step_id or slot_key."""
        if not self.step_id and not self.slot_key:
            raise ValueError("step_id or slot_key required")
        return self


class DecisionIndex(BaseModel):
    """Container for all IndexEntry records; serializes to index.json."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    mission_id: str
    entries: tuple[IndexEntry, ...] = ()


# ---------------------------------------------------------------------------
# Response models (wire contracts for CLI output)
# ---------------------------------------------------------------------------


class DecisionOpenResponse(BaseModel):
    """Response returned when a decision is opened (or idempotently found)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    idempotent: bool
    mission_id: str
    artifact_path: str
    event_lamport: int | None = None


class DecisionTerminalResponse(BaseModel):
    """Response returned when a decision reaches a terminal state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    status: DecisionStatus
    terminal_outcome: str
    idempotent: bool
    event_lamport: int | None = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def logical_key(entry: IndexEntry) -> tuple[str, str, str | None, str]:
    """Return the idempotency key tuple for an IndexEntry.

    Returns ``(mission_id, origin_flow, step_id_or_slot_key, input_key)``.
    ``step_id`` takes precedence over ``slot_key`` when both are set.
    """
    step_or_slot: str | None = entry.step_id if entry.step_id is not None else entry.slot_key
    return (entry.mission_id, entry.origin_flow, step_or_slot, entry.input_key)
