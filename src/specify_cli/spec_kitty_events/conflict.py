"""Conflict detection using Lamport clocks."""
from typing import Tuple
from spec_kitty_events.models import Event


def is_concurrent(event1: Event, event2: Event) -> bool:
    """Determine if two events are concurrent (conflicting).

    Two events are concurrent if:
    1. They have the same lamport_clock value
    2. They modify the same aggregate_id
    3. They are not the same event (different event_id)

    Events on different aggregates are NEVER concurrent, even if they have
    the same lamport_clock, because they don't conflict (modify different entities).

    Args:
        event1: First event
        event2: Second event

    Returns:
        True if events are concurrent (conflicting), False otherwise

    Example:
        >>> e1 = Event(event_id="ID1", aggregate_id="WP001", lamport_clock=5, ...)
        >>> e2 = Event(event_id="ID2", aggregate_id="WP001", lamport_clock=5, ...)
        >>> is_concurrent(e1, e2)
        True

        >>> e3 = Event(event_id="ID3", aggregate_id="WP002", lamport_clock=5, ...)
        >>> is_concurrent(e1, e3)  # Different aggregate
        False
    """
    return (
        event1.lamport_clock == event2.lamport_clock
        and event1.aggregate_id == event2.aggregate_id
        and event1.event_id != event2.event_id
    )


def total_order_key(event: Event) -> Tuple[int, str]:
    """Generate sortable key for deterministic total ordering.

    When multiple events have the same lamport_clock (concurrent events),
    we need a deterministic tiebreaker. This function returns a tuple
    of (lamport_clock, node_id) that can be used as a sort key.

    The node_id provides a stable, deterministic tiebreaker (lexicographic order).

    Args:
        event: Event to generate key for

    Returns:
        Tuple of (lamport_clock, node_id) for sorting

    Example:
        >>> events = [event1, event2, event3]
        >>> sorted_events = sorted(events, key=total_order_key)
        # Events are now deterministically ordered by (clock, node_id)
    """
    return (event.lamport_clock, event.node_id)
