"""Topological sorting of events by causation relationships."""
from collections import deque
from typing import Deque, List, Dict
from spec_kitty_events.models import Event, CyclicDependencyError


def topological_sort(events: List[Event]) -> List[Event]:
    """Sort events by causation relationships (parent before child).

    Uses Kahn's algorithm to perform topological sort. Events with no parent
    (causation_id = None) come first, followed by their descendants.

    Args:
        events: List of events to sort

    Returns:
        List of events in topological order (parents before children)

    Raises:
        CyclicDependencyError: If events form a cycle in causation graph

    Example:
        >>> e1 = Event(event_id="ID1", causation_id=None, ...)  # Root
        >>> e2 = Event(event_id="ID2", causation_id="ID1", ...)  # Child of e1
        >>> e3 = Event(event_id="ID3", causation_id="ID2", ...)  # Child of e2
        >>> sorted_events = topological_sort([e3, e1, e2])
        >>> # Result: [e1, e2, e3] (parent before child)
    """
    if not events:
        return []

    # Build event lookup and dependency graph
    event_map: Dict[str, Event] = {e.event_id: e for e in events}
    in_degree: Dict[str, int] = {e.event_id: 0 for e in events}
    children: Dict[str, List[str]] = {e.event_id: [] for e in events}

    # Calculate in-degrees (number of parents)
    for event in events:
        if event.causation_id is not None:
            if event.causation_id not in event_map:
                # Parent not in list - treat as external (in-degree remains 0)
                continue
            in_degree[event.event_id] += 1
            children[event.causation_id].append(event.event_id)

    # Kahn's algorithm: start with nodes that have no parents (in-degree = 0)
    queue: Deque[str] = deque(
        eid for eid, degree in in_degree.items() if degree == 0
    )
    result: List[Event] = []

    while queue:
        # Pop event with no remaining dependencies
        current_id = queue.popleft()
        result.append(event_map[current_id])

        # Reduce in-degree for all children
        for child_id in children[current_id]:
            in_degree[child_id] -= 1
            if in_degree[child_id] == 0:
                queue.append(child_id)

    # Check for cycles: if not all events processed, there's a cycle
    if len(result) != len(events):
        raise CyclicDependencyError(
            f"Cyclic dependency detected: {len(events) - len(result)} events "
            "could not be sorted due to circular causation relationships"
        )

    return result
