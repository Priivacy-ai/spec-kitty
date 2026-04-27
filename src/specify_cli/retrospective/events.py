"""Pydantic v2 payload models for retrospective runtime events.

The event-name registry is imported from ``spec_kitty_events`` when the 4.1+
surface is installed. A local fallback keeps the CLI compatible with the
currently pinned 4.0.x package until the release pin is advanced.

Source-of-truth: kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/retrospective_events_v1.md
"""

from __future__ import annotations

import json
import logging
from importlib import import_module
from datetime import datetime, UTC
from pathlib import Path
from typing import Literal, cast

import ulid as _ulid_mod
from pydantic import BaseModel, ConfigDict

from specify_cli.retrospective.schema import ActorRef, Mode

logger = logging.getLogger(__name__)

try:
    _upstream_retrospective = import_module("spec_kitty_events.retrospective")
    _UPSTREAM_RETROSPECTIVE_EVENT_NAMES = cast(
        "frozenset[str] | None",
        getattr(_upstream_retrospective, "RETROSPECTIVE_EVENT_NAMES", None),
    )
except ImportError:  # pragma: no cover - exercised only with pre-4.1 package pins
    _UPSTREAM_RETROSPECTIVE_EVENT_NAMES = None

# ---------------------------------------------------------------------------
# Stable event name registry
# ---------------------------------------------------------------------------

_LOCAL_RETROSPECTIVE_EVENT_NAMES: frozenset[str] = frozenset(
    [
        "retrospective.requested",
        "retrospective.started",
        "retrospective.completed",
        "retrospective.skipped",
        "retrospective.failed",
        "retrospective.proposal.generated",
        "retrospective.proposal.applied",
        "retrospective.proposal.rejected",
    ]
)

RETROSPECTIVE_EVENT_NAMES: frozenset[str] = (
    _UPSTREAM_RETROSPECTIVE_EVENT_NAMES or _LOCAL_RETROSPECTIVE_EVENT_NAMES
)

# ---------------------------------------------------------------------------
# Payload models
# ---------------------------------------------------------------------------


class RequestedPayload(BaseModel):
    """Payload for retrospective.requested event."""

    model_config = ConfigDict(extra="forbid")

    mode: Mode
    terminus_step_id: str
    requested_by: ActorRef


class StartedPayload(BaseModel):
    """Payload for retrospective.started event."""

    model_config = ConfigDict(extra="forbid")

    facilitator_profile_id: str
    action_id: str


class CompletedPayload(BaseModel):
    """Payload for retrospective.completed event.

    findings_summary is keyed by helped/not_helpful/gaps mapping to int counts.
    """

    model_config = ConfigDict(extra="forbid")

    record_path: str
    record_hash: str
    findings_summary: dict[str, int]
    proposals_count: int


class SkippedPayload(BaseModel):
    """Payload for retrospective.skipped event (HiC-only)."""

    model_config = ConfigDict(extra="forbid")

    record_path: str
    skip_reason: str
    skipped_by: ActorRef


class FailedPayload(BaseModel):
    """Payload for retrospective.failed event."""

    model_config = ConfigDict(extra="forbid")

    failure_code: str
    message: str
    record_path: str | None = None


class ProposalGeneratedPayload(BaseModel):
    """Payload for retrospective.proposal.generated event."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    kind: str
    record_path: str


class ProposalAppliedPayload(BaseModel):
    """Payload for retrospective.proposal.applied event."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    kind: str
    target_urn: str
    provenance_ref: str
    applied_by: ActorRef


class ProposalRejectedPayload(BaseModel):
    """Payload for retrospective.proposal.rejected event."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    kind: str
    reason: Literal["human_decline", "conflict", "stale_evidence", "invalid_payload"]
    detail: str
    rejected_by: ActorRef


# ---------------------------------------------------------------------------
# Emission helper
# ---------------------------------------------------------------------------


def _generate_ulid() -> str:
    """Generate a new ULID string."""
    return str(_ulid_mod.ULID())


def _now_utc() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def emit_retrospective_event(
    *,
    feature_dir: Path,
    mission_slug: str,
    mission_id: str,
    mid8: str,
    actor: ActorRef,
    event_name: str,
    payload: BaseModel,
) -> str:
    """Append a retrospective event to the mission's status.events.jsonl.

    Append-only. Sorted-key JSON. Returns the assigned event_id (ULID).

    Args:
        feature_dir: Path to the kitty-specs feature directory (contains
            status.events.jsonl).
        mission_slug: Human-readable mission slug.
        mission_id: Canonical ULID mission identity.
        mid8: First 8 chars of mission_id (convenience).
        actor: ActorRef identifying who emitted the event.
        event_name: One of RETROSPECTIVE_EVENT_NAMES.
        payload: Pydantic model instance for the event payload.

    Returns:
        The event_id (ULID string) assigned to the new event.

    Raises:
        ValueError: If event_name is not in RETROSPECTIVE_EVENT_NAMES.
    """
    if event_name not in RETROSPECTIVE_EVENT_NAMES:
        raise ValueError(
            f"Unknown retrospective event name {event_name!r}. "
            f"Must be one of: {sorted(RETROSPECTIVE_EVENT_NAMES)}"
        )

    event_id = _generate_ulid()
    at = _now_utc()

    envelope: dict[str, object] = {
        "actor": actor.model_dump(mode="json"),
        "at": at,
        "event_id": event_id,
        "event_name": event_name,
        "mid8": mid8,
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "payload": payload.model_dump(mode="json"),
    }

    events_path = feature_dir / "status.events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(envelope, sort_keys=True)
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    logger.debug("Appended retrospective event %s (%s) to %s", event_id, event_name, events_path)

    return event_id
