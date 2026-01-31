"""CRDT merge functions for conflict resolution."""
from typing import List, Set, Any
from spec_kitty_events.models import Event


def merge_gset(events: List[Event]) -> Set[Any]:
    """Merge GSet (grow-only set) from multiple events.

    Extracts tags from event.payload["tags"] and returns the union of all sets.
    This is a CRDT merge: commutative, associative, and idempotent.

    Args:
        events: List of events containing tag sets in payload

    Returns:
        Union of all tag sets

    Example:
        >>> e1 = Event(payload={"tags": {"bug", "urgent"}}, ...)
        >>> e2 = Event(payload={"tags": {"bug", "resolved"}}, ...)
        >>> merge_gset([e1, e2])
        {"bug", "urgent", "resolved"}

    Note:
        - Empty payload or missing "tags" key is treated as empty set
        - Duplicate tags are automatically deduplicated (set semantics)
    """
    merged: Set[Any] = set()
    for event in events:
        tags = event.payload.get("tags", set())
        # Convert to set if needed (handle list/tuple inputs)
        if not isinstance(tags, set):
            tags = set(tags)
        merged.update(tags)
    return merged


def merge_counter(events: List[Event]) -> int:
    """Merge Counter CRDT from multiple events.

    Extracts deltas from event.payload["delta"] and returns the sum,
    with deduplication by event_id (same event counted only once).

    This is a CRDT merge: commutative, associative, and idempotent.

    Args:
        events: List of events containing counter deltas in payload

    Returns:
        Sum of all deltas (deduplicated by event_id)

    Example:
        >>> e1 = Event(event_id="ID1", payload={"delta": 5}, ...)
        >>> e2 = Event(event_id="ID2", payload={"delta": 3}, ...)
        >>> merge_counter([e1, e2])
        8
        >>> merge_counter([e1, e1, e2])  # e1 counted once (idempotent)
        8

    Note:
        - Empty payload or missing "delta" key is treated as 0
        - Deduplication prevents double-counting same event
    """
    seen_ids: Set[str] = set()
    total = 0
    for event in events:
        # Deduplicate by event_id
        if event.event_id in seen_ids:
            continue
        seen_ids.add(event.event_id)

        # Extract delta (default to 0 if missing)
        delta = event.payload.get("delta", 0)
        total += delta
    return total
