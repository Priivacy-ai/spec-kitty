"""Decision Moment V1 shared models and enums (spec-kitty-events 4.0.0)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from .collaboration import ParticipantIdentity

__all__ = [
    "OriginSurface",
    "OriginFlow",
    "TerminalOutcome",
    "SummarySource",
    "WideningChannel",
    "DiscussingSnapshotKind",
    "SummaryBlock",
    "TeamspaceRef",
    "DefaultChannelRef",
    "ThreadRef",
    "ClosureMessageRef",
    "WideningProjection",
]


# ── Enums ─────────────────────────────────────────────────────────────────────


class OriginSurface(str, Enum):
    """Surface that originated the decision point."""

    ADR = "adr"
    PLANNING_INTERVIEW = "planning_interview"


class OriginFlow(str, Enum):
    """Spec-kitty flow that originated the decision point."""

    CHARTER = "charter"
    SPECIFY = "specify"
    PLAN = "plan"


class TerminalOutcome(str, Enum):
    """Terminal resolution outcome for a decision point."""

    RESOLVED = "resolved"
    DEFERRED = "deferred"
    CANCELED = "canceled"


class SummarySource(str, Enum):
    """Provenance of a SummaryBlock."""

    SLACK_EXTRACTION = "slack_extraction"
    MANUAL = "manual"
    MISSION_OWNER_OVERRIDE = "mission_owner_override"


class WideningChannel(str, Enum):
    """Channel used to widen a decision point to external participants."""

    SLACK = "slack"


class DiscussingSnapshotKind(str, Enum):
    """Kind of contribution snapshot in a DecisionPointDiscussing event."""

    PARTICIPANT_CONTRIBUTION = "participant_contribution"
    DIGEST = "digest"
    OWNER_NOTE = "owner_note"


# ── Shared Models ─────────────────────────────────────────────────────────────


class SummaryBlock(BaseModel):
    """Structured summary of a resolved decision with provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(..., min_length=1, description="Summary text (non-empty)")
    source: SummarySource = Field(..., description="Provenance of this summary")
    extracted_at: Optional[datetime] = Field(
        None, description="When the summary was extracted (if from Slack)"
    )
    candidate_answer: Optional[str] = Field(
        None, description="Candidate answer extracted from the summary"
    )


class TeamspaceRef(BaseModel):
    """Reference to a Slack-connected teamspace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    teamspace_id: str = Field(..., min_length=1, description="Teamspace identifier")
    name: Optional[str] = Field(None, description="Human-readable teamspace name")


class DefaultChannelRef(BaseModel):
    """Reference to the default Slack channel for a teamspace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    channel_id: str = Field(..., min_length=1, description="Slack channel identifier")
    name: Optional[str] = Field(None, description="Human-readable channel name")


class ThreadRef(BaseModel):
    """Reference to a Slack thread."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slack_team_id: Optional[str] = Field(
        None, description="Slack workspace team identifier"
    )
    channel_id: str = Field(..., min_length=1, description="Slack channel identifier")
    thread_ts: str = Field(
        ..., min_length=1, description="Thread timestamp (Slack ts format)"
    )
    url: Optional[str] = Field(None, description="Permalink URL to the thread")


class ClosureMessageRef(BaseModel):
    """Reference to a Slack closure message posted when a decision is resolved."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    channel_id: str = Field(..., min_length=1, description="Slack channel identifier")
    thread_ts: str = Field(
        ..., min_length=1, description="Thread timestamp (Slack ts format)"
    )
    message_ts: str = Field(
        ..., min_length=1, description="Message timestamp (Slack ts format)"
    )
    url: Optional[str] = Field(None, description="Permalink URL to the message")


class WideningProjection(BaseModel):
    """Projection of widening state populated on DecisionPointWidened.

    Note: invited_participants uses a string forward reference to
    ParticipantIdentity (from collaboration.py) to avoid circular imports.
    The TYPE_CHECKING guard above provides the type for static analysis only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    channel: WideningChannel = Field(
        ..., description="Channel used for widening"
    )
    teamspace_ref: TeamspaceRef = Field(
        ..., description="Teamspace the widening was sent to"
    )
    default_channel_ref: DefaultChannelRef = Field(
        ..., description="Default channel in the teamspace"
    )
    thread_ref: ThreadRef = Field(
        ..., description="Slack thread created for widening"
    )
    invited_participants: Tuple["ParticipantIdentity", ...] = Field(
        ..., description="Participants invited during widening"
    )
    widened_by: str = Field(
        ..., min_length=1, description="participant_id of mission owner who confirmed widening"
    )
    widened_at: datetime = Field(..., description="When the widening occurred")


# Resolve the forward reference to ParticipantIdentity from collaboration.py.
# This must be called after both modules are importable. Callers that need
# WideningProjection should import both modules, or call model_rebuild() themselves.
# We do a best-effort rebuild here; if collaboration is not yet importable
# (e.g. during isolated unit tests of this module), the rebuild is deferred.
def _rebuild_widening_projection() -> None:
    """Rebuild WideningProjection to resolve the ParticipantIdentity forward ref."""
    try:
        from .collaboration import ParticipantIdentity  # noqa: F401

        WideningProjection.model_rebuild()
    except ImportError as e:
        raise RuntimeError(
            "Failed to rebuild WideningProjection: collaboration module could not be imported. "
            "This indicates a package integrity problem; WideningProjection with invited_participants "
            "cannot be used until resolved."
        ) from e


_rebuild_widening_projection()
