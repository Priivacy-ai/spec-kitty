"""
Event queue infrastructure.

This package provides durable JSONL event storage, Lamport clock management,
ULID generation, and SaaS replay transport.

Storage Format:
- Queue: ~/.spec-kitty/queue.db (newline-delimited JSON)
- Lamport clock: ~/.spec-kitty/events/lamport_clock.json (per-node state)
"""

from .adapter import Event, EventAdapter, HAS_LIBRARY, LamportClock
from .ulid_utils import generate_event_id, validate_ulid_format
from .store import (
    EventStore,
    append_event,
    read_pending_events,
    read_all_events,
    emit_event,
    is_online,
    get_queue_path,
)
from .replay import replay_pending_events
from .lamport import LamportClock as LamportClockImpl

__all__ = [
    "Event",
    "LamportClock",
    "LamportClockImpl",
    "EventAdapter",
    "HAS_LIBRARY",
    "EventStore",
    "generate_event_id",
    "validate_ulid_format",
    "append_event",
    "read_pending_events",
    "read_all_events",
    "emit_event",
    "is_online",
    "get_queue_path",
    "replay_pending_events",
]
