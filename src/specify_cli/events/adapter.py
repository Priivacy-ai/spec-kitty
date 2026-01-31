"""
Adapter layer for spec-kitty-events library.

Translates between library types and CLI types, providing loose coupling
for future flexibility.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# Import from vendored spec_kitty_events module
try:
    from specify_cli.spec_kitty_events import (
        Event as LibEvent,
        LamportClock as LibClock,
        InMemoryClockStorage,
    )

    HAS_LIBRARY = True
except ImportError:
    HAS_LIBRARY = False
    LibEvent = None  # type: ignore
    LibClock = None  # type: ignore
    InMemoryClockStorage = None  # type: ignore


@dataclass
class Event:
    """CLI representation of an event (wraps library Event)."""

    event_id: str
    event_type: str
    event_version: int
    lamport_clock: int
    entity_id: str
    entity_type: str
    timestamp: str
    actor: str
    causation_id: str | None
    correlation_id: str | None
    payload: dict[str, Any]

    @classmethod
    def from_lib_event(cls, lib_event: Any) -> "Event":
        """Convert library Event to CLI Event."""
        if not HAS_LIBRARY:
            raise RuntimeError("spec-kitty-events library not installed")

        # Extract fields from library event
        return cls(
            event_id=str(lib_event.event_id),
            event_type=lib_event.event_type,
            event_version=1,  # CLI uses version 1
            lamport_clock=lib_event.clock,
            entity_id=lib_event.entity_id,
            entity_type=lib_event.entity_type,
            timestamp=lib_event.timestamp,
            actor=lib_event.actor,
            causation_id=lib_event.causation_id,
            correlation_id=lib_event.correlation_id,
            payload=lib_event.payload,
        )

    def to_lib_event(self) -> Any:
        """Convert CLI Event to library Event."""
        if not HAS_LIBRARY:
            raise RuntimeError("spec-kitty-events library not installed")

        # Create library event from CLI fields
        return LibEvent(
            event_id=self.event_id,
            event_type=self.event_type,
            clock=self.lamport_clock,
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            timestamp=self.timestamp,
            actor=self.actor,
            causation_id=self.causation_id,
            correlation_id=self.correlation_id,
            payload=self.payload,
        )


@dataclass
class LamportClock:
    """CLI representation of Lamport clock (wraps library LamportClock)."""

    value: int
    last_updated: str

    def tick(self) -> int:
        """Increment clock and return new value."""
        self.value += 1
        self.last_updated = datetime.now(timezone.utc).isoformat()
        return self.value

    def update(self, remote_clock: int) -> int:
        """Update clock to max(local, remote) + 1."""
        self.value = max(self.value, remote_clock) + 1
        self.last_updated = datetime.now(timezone.utc).isoformat()
        return self.value

    @classmethod
    def from_lib_clock(cls, lib_clock: Any) -> "LamportClock":
        """Convert library LamportClock to CLI LamportClock."""
        if not HAS_LIBRARY:
            raise RuntimeError("spec-kitty-events library not installed")

        return cls(
            value=lib_clock.value,
            last_updated=lib_clock.last_updated or datetime.now(timezone.utc).isoformat(),
        )

    def to_lib_clock(self) -> Any:
        """Convert CLI LamportClock to library LamportClock."""
        if not HAS_LIBRARY:
            raise RuntimeError("spec-kitty-events library not installed")

        # Create storage and clock with current value
        storage = InMemoryClockStorage()
        lib_clock = LibClock(node_id="cli", storage=storage)
        lib_clock.value = self.value
        return lib_clock


class EventAdapter:
    """Main adapter for spec-kitty-events library integration."""

    @staticmethod
    def check_library_available() -> bool:
        """Check if spec-kitty-events library is available."""
        return HAS_LIBRARY

    @staticmethod
    def get_missing_library_error() -> str:
        """Get error message for missing library with setup instructions."""
        return (
            "spec-kitty-events library not installed.\n\n"
            "This library is required for event log functionality.\n\n"
            "Setup instructions:\n"
            "1. Ensure you have SSH access to https://github.com/Priivacy-ai/spec-kitty-events\n"
            "2. Run: pip install -e .\n\n"
            "For CI/CD setup, see: docs/development/ssh-deploy-keys.md\n"
        )
