"""Core data models for spec-kitty-events library."""
import re

from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

_UUID_HYPHEN_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_UUID_BARE_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)

# Crockford base32 charset used by ULIDs (case-insensitive input,
# canonical output is uppercase). Excludes I, L, O, U.
_CROCKFORD_B32_RE = re.compile(r"^[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$")

# JSON Schema pattern accepting all 3 inbound formats:
# 26-char Crockford base32 ULID, 32-char hex (bare UUID), 36-char hyphenated UUID
_EVENT_ID_PATTERN = (
    r"^[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$"
    r"|^[0-9a-fA-F]{32}$"
    r"|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def normalize_event_id(v: object) -> str:
    """Normalize an event ID to canonical form.

    Accepts:
    - 26-char Crockford base32 ULIDs — validated and uppercased
    - 36-char hyphenated UUIDs — lowercased to canonical form
    - 32-char bare hex UUIDs — hyphenated and lowercased

    Raises:
        ValueError: If the input is not a string or does not match any
            accepted format.
    """
    if not isinstance(v, str):
        raise ValueError(
            f"event_id must be a string; got {type(v).__name__}"
        )
    if len(v) == 26:
        if not _CROCKFORD_B32_RE.match(v):
            raise ValueError(
                f"26-char event_id must be Crockford base32 (ULID); "
                f"got invalid characters in {v!r}"
            )
        return v.upper()
    if len(v) == 36 and _UUID_HYPHEN_RE.match(v):
        return v.lower()
    if len(v) == 32 and _UUID_BARE_RE.match(v):
        h = v.lower()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
    raise ValueError(
        f"event_id must be 26 chars (ULID), 36-char UUID, "
        f"or 32-char hex UUID; got {len(v)} chars"
    )


class Event(BaseModel):
    """Immutable event with causal metadata for distributed conflict detection."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(
        ...,
        min_length=26,
        max_length=36,
        description="Unique event identifier (26-char ULID or UUID accepted)",
        json_schema_extra={"pattern": _EVENT_ID_PATTERN},
    )
    event_type: str = Field(
        ...,
        min_length=1,
        description="Event type identifier (e.g., 'WPStatusChanged', 'TagAdded')"
    )
    aggregate_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the entity this event modifies"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data (opaque to library)"
    )
    timestamp: datetime = Field(
        ...,
        description="Wall-clock timestamp (human-readable, not used for ordering)"
    )
    node_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the node that emitted this event"
    )
    lamport_clock: int = Field(
        ...,
        ge=0,
        description="Lamport logical clock value (monotonically increasing)"
    )
    causation_id: Optional[str] = Field(
        None,
        min_length=26,
        max_length=36,
        description="Event ID of the parent event (26-char ULID or UUID accepted, None for root events)",
        json_schema_extra={"pattern": _EVENT_ID_PATTERN},
    )

    @field_validator("event_id", "causation_id", mode="before")
    @classmethod
    def _normalize_event_id(cls, v: object) -> object:
        if v is None:
            return v
        return normalize_event_id(v)

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"Event(event_id={self.event_id[:8]}..., "
            f"type={self.event_type}, "
            f"aggregate={self.aggregate_id}, "
            f"lamport={self.lamport_clock})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary (for storage)."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Deserialize event from dictionary."""
        return cls(**data)


class ErrorEntry(BaseModel):
    """Record of a failed action for agent learning."""

    timestamp: datetime = Field(
        ...,
        description="When the error occurred (ISO 8601 format)"
    )
    action_attempted: str = Field(
        ...,
        min_length=1,
        description="What the agent/user tried to do"
    )
    error_message: str = Field(
        ...,
        min_length=1,
        description="Error output or exception message"
    )
    resolution: str = Field(
        default="",
        description="How the error was resolved (empty if unresolved)"
    )
    agent: str = Field(
        default="unknown",
        description="Which agent encountered the error"
    )

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"ErrorEntry(timestamp={self.timestamp.isoformat()}, "
            f"action={self.action_attempted[:30]}..., "
            f"agent={self.agent})"
        )


@dataclass
class ConflictResolution:
    """Result of merging concurrent events."""

    merged_event: Event
    resolution_note: str
    requires_manual_review: bool
    conflicting_events: List[Event]

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"ConflictResolution(merged={self.merged_event.event_id[:8]}..., "
            f"conflicts={len(self.conflicting_events)}, "
            f"manual_review={self.requires_manual_review})"
        )


# Custom Exceptions
class SpecKittyEventsError(Exception):
    """Base exception for all library errors."""
    pass


class StorageError(SpecKittyEventsError):
    """Storage adapter failure."""
    pass


class ValidationError(SpecKittyEventsError):
    """Event or ErrorEntry validation failed."""
    pass


class CyclicDependencyError(SpecKittyEventsError):
    """Events form cycle in causation graph."""
    pass
