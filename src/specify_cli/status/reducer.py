"""Deterministic reducer for status event logs.

Replays a list of StatusEvent records into a StatusSnapshot, applying
deduplication, deterministic sorting, and rollback-aware conflict
resolution for concurrent events from parallel worktrees.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Lane, StatusEvent, StatusSnapshot
from .store import read_events

SNAPSHOT_FILENAME = "status.json"


def _now_utc() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _is_rollback_event(event: StatusEvent) -> bool:
    """Check if an event represents a reviewer rollback.

    A rollback is a transition from for_review back to in_progress
    with a review reference (indicating a reviewer requested changes).
    """
    return event.from_lane == Lane.FOR_REVIEW and event.to_lane == Lane.IN_PROGRESS and event.review_ref is not None


def _wp_state_from_event(
    event: StatusEvent,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a WP state dict from an event, optionally carrying forward
    the force_count from the previous state.
    """
    prior_force_count = 0
    if previous is not None:
        prior_force_count = previous.get("force_count", 0)

    return {
        "lane": str(event.to_lane),
        "actor": event.actor,
        "last_transition_at": event.at,
        "last_event_id": event.event_id,
        "force_count": prior_force_count + (1 if event.force else 0),
    }


def _should_apply_event(
    current_state: dict[str, Any] | None,
    new_event: StatusEvent,
    all_events: list[StatusEvent],
) -> bool:
    """Determine whether new_event should be applied given the current state.

    Implements rollback-aware precedence: if the current state was set by
    a forward transition and a concurrent rollback event exists for the
    same WP, the rollback wins.

    If there is no current state, the event always applies.
    If events are not concurrent (different timestamps), the later one
    wins naturally through sort order.
    """
    if current_state is None:
        return True

    current_event_id = current_state.get("last_event_id")
    current_timestamp = current_state.get("last_transition_at")

    # If this event has the same timestamp as the current state's event,
    # they are concurrent. Check rollback precedence.
    if current_timestamp == new_event.at:
        # If the new event is a rollback, it beats a forward transition
        if _is_rollback_event(new_event):
            # Check if the current state was set by a non-rollback event
            current_setter = None
            for ev in all_events:
                if ev.event_id == current_event_id:
                    current_setter = ev
                    break
            if current_setter is not None and not _is_rollback_event(current_setter):
                return True  # Rollback beats forward

        # If the current state was set by a rollback, don't let a
        # concurrent forward event override it
        if current_event_id is not None:
            current_setter = None
            for ev in all_events:
                if ev.event_id == current_event_id:
                    current_setter = ev
                    break
            if current_setter is not None and _is_rollback_event(current_setter):
                if not _is_rollback_event(new_event):
                    return False  # Forward does not beat rollback

    # Default: apply the event (later in sort order wins)
    return True


def reduce(events: list[StatusEvent]) -> StatusSnapshot:
    """Deterministically reduce a list of events into a snapshot.

    Algorithm:
    1. Deduplicate by event_id (keep first occurrence)
    2. Sort by (at, event_id) ascending
    3. Iterate and track current lane per WP
    4. Apply rollback-aware precedence for concurrent events
    5. Build summary counts for all 7 lanes

    Empty events returns a snapshot with feature_slug="", all zero
    counts, and no work packages.
    """
    if not events:
        return StatusSnapshot(
            feature_slug="",
            materialized_at=_now_utc(),
            event_count=0,
            last_event_id=None,
            work_packages={},
            summary={lane.value: 0 for lane in Lane},
        )

    # Step 1: Deduplicate by event_id (keep first occurrence)
    seen_ids: set[str] = set()
    unique_events: list[StatusEvent] = []
    for event in events:
        if event.event_id not in seen_ids:
            seen_ids.add(event.event_id)
            unique_events.append(event)

    # Step 2: Sort by (at, event_id) ascending
    sorted_events = sorted(unique_events, key=lambda e: (e.at, e.event_id))

    # Step 3 & 4: Iterate and apply events with rollback-aware precedence
    wp_states: dict[str, dict[str, Any]] = {}
    feature_slug = sorted_events[0].feature_slug

    for event in sorted_events:
        current = wp_states.get(event.wp_id)
        if _should_apply_event(current, event, sorted_events):
            wp_states[event.wp_id] = _wp_state_from_event(event, current)

    # Step 5: Build summary counts
    summary: dict[str, int] = {lane.value: 0 for lane in Lane}
    for wp_state in wp_states.values():
        lane_val = wp_state["lane"]
        if lane_val in summary:
            summary[lane_val] += 1

    return StatusSnapshot(
        feature_slug=feature_slug,
        materialized_at=_now_utc(),
        event_count=len(sorted_events),
        last_event_id=sorted_events[-1].event_id,
        work_packages=wp_states,
        summary=summary,
    )


def materialize_to_json(snapshot: StatusSnapshot) -> str:
    """Serialize a snapshot to a deterministic JSON string.

    Uses ``sort_keys=True``, ``indent=2``, and ``ensure_ascii=False``
    for human-readable, byte-identical output across platforms.
    Returns the JSON string with a trailing newline.
    """
    return (
        json.dumps(
            snapshot.to_dict(),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def materialize(feature_dir: Path) -> StatusSnapshot:
    """Read events, reduce to snapshot, and write status.json atomically.

    Writes to a temporary file first, then uses ``os.replace`` for an
    atomic rename to avoid partial writes.

    Returns the materialized snapshot.
    """
    events = read_events(feature_dir)
    snapshot = reduce(events)
    json_str = materialize_to_json(snapshot)

    out_path = feature_dir / SNAPSHOT_FILENAME
    tmp_path = feature_dir / (SNAPSHOT_FILENAME + ".tmp")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(out_path))

    return snapshot
