"""Deterministic reducer for status event logs.

Replays a list of StatusEvent records into a StatusSnapshot, applying
deduplication, deterministic sorting, and rollback-aware conflict
resolution for concurrent events from parallel worktrees.

WP03 (additive): Also computes a RetrospectiveSnapshot from retrospective.*
events in the raw event log and attaches it to the StatusSnapshot under the
``retrospective`` field. Existing consumers see no change (default None).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from specify_cli.mission_metadata import resolve_mission_identity

from .models import Lane, RetrospectiveSnapshot, StatusEvent, StatusSnapshot
from .store import read_events, read_events_raw

SNAPSHOT_FILENAME = "status.json"


def _now_utc() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


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
            if current_setter is not None and _is_rollback_event(current_setter) and not _is_rollback_event(new_event):
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

    Empty events returns a snapshot with mission_slug="", all zero
    counts, and no work packages.
    """
    if not events:
        return StatusSnapshot(
            mission_slug="",
            materialized_at="",  # No events → no last-event timestamp; stable empty string
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
    mission_slug = sorted_events[0].mission_slug

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
        mission_slug=mission_slug,
        materialized_at=sorted_events[-1].at,  # Derived from last event; deterministic
        event_count=len(sorted_events),
        last_event_id=sorted_events[-1].event_id,
        work_packages=wp_states,
        summary=summary,
    )


def _reduce_retrospective(raw_events: list[dict[str, Any]]) -> RetrospectiveSnapshot:
    """Compute a RetrospectiveSnapshot from raw event-log entries.

    Scans the raw event list for retrospective.* events (identified by the
    ``event_name`` key) and computes the current snapshot state.

    Logic:
    - absent: no retrospective.* events at all.
    - pending: retrospective.requested or .started seen, but no terminal event.
    - Terminal status (completed/skipped/failed): determined by the latest
      terminal event, sorted by (at, event_id) descending.
    - Proposal counts aggregated from proposal.generated/applied/rejected events.
    - mode: from the most recent retrospective.requested payload.
    - record_path: from the most recent terminal event payload, if present.
    """
    retro_events = [e for e in raw_events if "event_name" in e and str(e.get("event_name", "")).startswith("retrospective.")]

    if not retro_events:
        return RetrospectiveSnapshot(status="absent")

    # Sort all retro events by (at, event_id) ascending
    def _sort_key(e: dict[str, Any]) -> tuple[str, str]:
        return (str(e.get("at", "")), str(e.get("event_id", "")))

    retro_events_sorted = sorted(retro_events, key=_sort_key)

    # Determine terminal status from latest completed/skipped/failed event
    terminal_names = {"retrospective.completed", "retrospective.skipped", "retrospective.failed"}
    terminal_events = [e for e in retro_events_sorted if e.get("event_name") in terminal_names]

    # Determine mode from most recent requested event
    requested_events = [e for e in retro_events_sorted if e.get("event_name") == "retrospective.requested"]
    mode = None
    if requested_events:
        latest_requested = requested_events[-1]
        payload = latest_requested.get("payload") or {}
        mode_data = payload.get("mode")
        if mode_data is not None:
            try:
                from specify_cli.retrospective.schema import Mode
                mode = Mode.model_validate(mode_data)
            except Exception:
                mode = None

    # Determine status
    if terminal_events:
        latest_terminal = terminal_events[-1]
        terminal_name: str = str(latest_terminal.get("event_name", ""))
        if terminal_name == "retrospective.completed":
            status: str = "completed"
        elif terminal_name == "retrospective.skipped":
            status = "skipped"
        else:
            status = "failed"

        # Extract record_path from terminal payload
        record_path: str | None = None
        payload = latest_terminal.get("payload") or {}
        rp = payload.get("record_path")
        if rp is not None:
            record_path = str(rp)
    else:
        # Non-terminal retro events present (requested/started)
        status = "pending"
        record_path = None

    # Proposal counts
    proposals_total = sum(
        1 for e in retro_events if e.get("event_name") == "retrospective.proposal.generated"
    )
    proposals_applied = sum(
        1 for e in retro_events if e.get("event_name") == "retrospective.proposal.applied"
    )
    proposals_rejected = sum(
        1 for e in retro_events if e.get("event_name") == "retrospective.proposal.rejected"
    )
    proposals_pending = max(0, proposals_total - proposals_applied - proposals_rejected)

    return RetrospectiveSnapshot(
        status=status,  # type: ignore[arg-type]
        mode=mode,
        record_path=record_path,
        proposals_total=proposals_total,
        proposals_applied=proposals_applied,
        proposals_rejected=proposals_rejected,
        proposals_pending=proposals_pending,
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

    Skips the write when content is byte-identical to the existing file.
    Writes to a temporary file first, then uses ``os.replace`` for an
    atomic rename to avoid partial writes.

    WP03 (additive): Also scans raw events for retrospective.* entries and
    attaches a RetrospectiveSnapshot to the snapshot under ``retrospective``.
    Default is None for missions with no retrospective events (backwards-compat).

    Returns the materialized snapshot.
    """
    events = read_events(feature_dir)
    snapshot = reduce(events)
    identity = resolve_mission_identity(feature_dir)
    snapshot.mission_number = (
        str(identity.mission_number)
        if identity.mission_number is not None
        else None
    )
    snapshot.mission_type = identity.mission_type

    # Additive WP03: compute RetrospectiveSnapshot from raw events (includes
    # retrospective.* entries that are not StatusEvent objects).
    raw_events = read_events_raw(feature_dir)
    retro_snapshot = _reduce_retrospective(raw_events)
    # Only attach non-absent snapshots to avoid changing serialized output for
    # missions that have no retrospective events at all.
    if retro_snapshot.status != "absent":
        snapshot.retrospective = retro_snapshot

    json_str = materialize_to_json(snapshot)

    out_path = feature_dir / SNAPSHOT_FILENAME
    tmp_path = feature_dir / (SNAPSHOT_FILENAME + ".tmp")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Skip write when content unchanged (FR-001, NFR-001)
    if out_path.exists() and out_path.read_text(encoding="utf-8") == json_str:
        return snapshot

    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(out_path))

    return snapshot
