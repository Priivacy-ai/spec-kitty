"""Event log integration package.

Public API:
    sanitize_event_for_log: Strip PII fields from an event envelope dict.
    Event: CLI representation of an event (wraps library Event).
    LamportClock: CLI representation of Lamport clock.
    EventAdapter: Adapter for spec-kitty-events library integration.
    HAS_LIBRARY: Whether the optional spec-kitty-events library is installed.
"""

from .adapter import Event, EventAdapter, HAS_LIBRARY, LamportClock
from .sanitizer import sanitize_event_for_log

__all__ = [
    "Event",
    "EventAdapter",
    "HAS_LIBRARY",
    "LamportClock",
    "sanitize_event_for_log",
]
