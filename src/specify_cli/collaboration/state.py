"""Materialized view of mission state from event replay."""

from specify_cli.events.store import read_all_events
from specify_cli.collaboration.models import SessionState
from datetime import datetime


def get_mission_roster(mission_id: str) -> list[SessionState]:
    """
    Build mission roster by replaying events (materialized view).

    Args:
        mission_id: Mission identifier

    Returns:
        List of SessionState for all participants
    """
    events = read_all_events(mission_id)

    # Roster: participant_id -> SessionState
    roster = {}

    for entry in events:
        event = entry.event
        event_type = event.event_type
        payload = event.payload

        participant_id = payload.get("participant_id")
        if not participant_id:
            continue

        # Initialize participant if not in roster
        if participant_id not in roster and event_type == "ParticipantJoined":
            # event.timestamp is already a datetime object, not a string
            timestamp = event.timestamp if isinstance(event.timestamp, datetime) else datetime.fromisoformat(event.timestamp)
            roster[participant_id] = SessionState(
                mission_id=mission_id,
                mission_run_id=payload.get("mission_run_id", ""),
                participant_id=participant_id,
                role=payload.get("role", "participant"),
                joined_at=timestamp,
                last_activity_at=timestamp,
                drive_intent="inactive",
                focus=None,
            )

        # Update participant state based on event type
        if participant_id in roster:
            state = roster[participant_id]
            # event.timestamp is already a datetime object
            state.last_activity_at = event.timestamp if isinstance(event.timestamp, datetime) else datetime.fromisoformat(event.timestamp)

            if event_type == "FocusChanged":
                target = payload.get("focus_target")
                if target:
                    # Map "work_package" -> "wp" to match local session format
                    target_type = target['target_type']
                    if target_type == "work_package":
                        target_type = "wp"
                    state.focus = f"{target_type}:{target['target_id']}"
                else:
                    state.focus = None

            elif event_type == "DriveIntentSet":
                state.drive_intent = payload["intent"]

    return list(roster.values())
