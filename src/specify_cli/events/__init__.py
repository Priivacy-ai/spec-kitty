"""
Event queue infrastructure.

This package provides durable JSONL event storage, Lamport clock management,
ULID generation, and SaaS replay transport.

Storage Format:
- Queue: ~/.spec-kitty/events/<mission_id>.jsonl (newline-delimited JSON)
- Lamport clock: ~/.spec-kitty/events/lamport_clock.json (per-node state)
"""

from .adapter import Event, EventAdapter, HAS_LIBRARY, LamportClock

__all__ = ["Event", "LamportClock", "EventAdapter", "HAS_LIBRARY"]
