"""State-machine merge logic with priority-based conflict resolution."""
from typing import List, Dict
from spec_kitty_events.models import Event, ConflictResolution, ValidationError


def state_machine_merge(
    events: List[Event],
    priority_map: Dict[str, int],
    state_key: str = "state"
) -> ConflictResolution:
    """Merge concurrent state-machine events using priority-based selection.

    When multiple events modify the same state concurrently, selects the event
    with the highest priority state value. Uses node_id as tiebreaker for determinism.

    Args:
        events: List of concurrent events to merge (must have same lamport_clock and aggregate_id)
        priority_map: Mapping of state values to priorities (higher = wins)
        state_key: Key in event.payload where state value is stored (default "state").
                   When using default "state", will fallback to "status" if "state" not found.

    Returns:
        ConflictResolution with:
        - merged_event: Event with highest priority state (or tiebroken by node_id)
        - resolution_note: Explanation of which state won and why
        - requires_manual_review: Always False for MVP (automatic resolution)
        - conflicting_events: All input events

    Raises:
        ValidationError: If state value not in priority_map, or events have different clocks/aggregates

    Example:
        >>> priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}
        >>> e1 = Event(payload={"state": "doing"}, node_id="alice", lamport_clock=5, ...)
        >>> e2 = Event(payload={"state": "done"}, node_id="bob", lamport_clock=5, ...)
        >>> resolution = state_machine_merge([e1, e2], priority_map)
        >>> resolution.merged_event.payload["state"]
        "done"  # Higher priority
    """
    if not events:
        raise ValidationError("Cannot merge empty event list")

    # Validate all events have same lamport_clock and aggregate_id (concurrent)
    first_event = events[0]
    for event in events[1:]:
        if event.lamport_clock != first_event.lamport_clock:
            raise ValidationError(
                f"Events have different lamport_clocks: {event.lamport_clock} != {first_event.lamport_clock}"
            )
        if event.aggregate_id != first_event.aggregate_id:
            raise ValidationError(
                f"Events have different aggregate_ids: {event.aggregate_id} != {first_event.aggregate_id}"
            )

    # Extract state values and validate against priority_map
    event_priorities: List[tuple[int, str, Event]] = []
    for event in events:
        state_value = event.payload.get(state_key)
        # Fallback to "status" if using default "state" key and "state" not found
        if state_value is None and state_key == "state":
            state_value = event.payload.get("status")
        if state_value is None:
            keys_tried = f"'{state_key}' or 'status'" if state_key == "state" else f"'{state_key}'"
            raise ValidationError(f"Event {event.event_id} missing {keys_tried} in payload")
        if state_value not in priority_map:
            raise ValidationError(
                f"State value '{state_value}' not in priority_map. "
                f"Available states: {list(priority_map.keys())}"
            )
        priority = priority_map[state_value]
        event_priorities.append((priority, event.node_id, event))

    # Sort by priority (descending), then node_id (ascending) for deterministic tiebreaker
    event_priorities.sort(key=lambda x: (-x[0], x[1]))

    # Winner is first event after sorting
    winner_priority, winner_node_id, winner_event = event_priorities[0]
    winner_state = winner_event.payload.get(state_key)
    if winner_state is None and state_key == "state":
        winner_state = winner_event.payload.get("status")

    # Build resolution note
    if len(events) == 1:
        resolution_note = f"Single event, no conflict: state={winner_state}"
    else:
        # Extract states with same fallback logic
        all_states = []
        for e in events:
            s = e.payload.get(state_key)
            if s is None and state_key == "state":
                s = e.payload.get("status")
            all_states.append(s)
        unique_states = set(all_states)
        if len(unique_states) == 1:
            resolution_note = f"All events have same state: {winner_state} (tiebroken by node '{winner_node_id}')"
        else:
            resolution_note = (
                f"Selected state '{winner_state}' (priority={winner_priority}) "
                f"from node '{winner_node_id}' over {len(events)-1} conflicting states"
            )

    return ConflictResolution(
        merged_event=winner_event,
        resolution_note=resolution_note,
        requires_manual_review=False,  # Always automatic for MVP
        conflicting_events=list(events)
    )
