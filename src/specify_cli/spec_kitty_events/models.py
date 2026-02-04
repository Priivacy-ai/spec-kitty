"""Core data models for spec-kitty-events library."""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


class Event(BaseModel):
    """Immutable event with causal metadata for distributed conflict detection."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(
        ...,
        min_length=26,
        max_length=26,
        description="Unique event identifier (ULID format)"
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
        max_length=26,
        description="Event ID of the parent event (None for root events)"
    )

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
