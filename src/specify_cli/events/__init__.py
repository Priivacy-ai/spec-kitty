"""Event log integration package."""

from .adapter import Event, EventAdapter, HAS_LIBRARY, LamportClock

__all__ = ["Event", "LamportClock", "EventAdapter", "HAS_LIBRARY"]
