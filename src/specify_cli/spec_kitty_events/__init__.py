"""
spec-kitty-events: Event log library with Lamport clocks and systematic error tracking.

This library provides primitives for building distributed event-sourced systems
with causal metadata (Lamport clocks), conflict detection, and CRDT/state-machine
merge rules.

Example:
    >>> from spec_kitty_events import Event, LamportClock, InMemoryClockStorage
    >>> storage = InMemoryClockStorage()
    >>> clock = LamportClock(node_id="alice", storage=storage)
    >>> clock.tick()
    1
"""

__version__ = "0.1.0-alpha"

# Core data models
from spec_kitty_events.models import (
    Event,
    ErrorEntry,
    ConflictResolution,
    SpecKittyEventsError,
    StorageError,
    ValidationError,
    CyclicDependencyError,
)

# Storage abstractions
from spec_kitty_events.storage import (
    EventStore,
    ClockStorage,
    ErrorStorage,
    InMemoryEventStore,
    InMemoryClockStorage,
    InMemoryErrorStorage,
)

# Lamport clock
from spec_kitty_events.clock import LamportClock

# Conflict detection
from spec_kitty_events.conflict import (
    is_concurrent,
    total_order_key,
)

# Topological sorting
from spec_kitty_events.topology import topological_sort

# CRDT merge functions
from spec_kitty_events.crdt import (
    merge_gset,
    merge_counter,
)

# State-machine merge
from spec_kitty_events.merge import state_machine_merge

# Error logging
from spec_kitty_events.error_log import ErrorLog

# Public API (controls what's exported with "from spec_kitty_events import *")
__all__ = [
    # Version
    "__version__",
    # Models
    "Event",
    "ErrorEntry",
    "ConflictResolution",
    # Exceptions
    "SpecKittyEventsError",
    "StorageError",
    "ValidationError",
    "CyclicDependencyError",
    # Storage
    "EventStore",
    "ClockStorage",
    "ErrorStorage",
    "InMemoryEventStore",
    "InMemoryClockStorage",
    "InMemoryErrorStorage",
    # Clock
    "LamportClock",
    # Conflict detection
    "is_concurrent",
    "total_order_key",
    "topological_sort",
    # Merge functions
    "merge_gset",
    "merge_counter",
    "state_machine_merge",
    # Error logging
    "ErrorLog",
]
