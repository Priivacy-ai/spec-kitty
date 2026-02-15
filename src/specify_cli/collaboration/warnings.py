"""Collision detection and warning system for mission collaboration."""

from specify_cli.collaboration.state import get_mission_roster
from specify_cli.collaboration.session import load_session_state
from specify_cli.events.ulid_utils import generate_event_id
from specify_cli.events.lamport import LamportClock
from specify_cli.events.store import emit_event
from specify_cli.spec_kitty_events.models import Event
from datetime import datetime


def _to_focus_target(focus: str | None) -> dict | None:
    """
    Convert focus string to FocusTarget dict.

    Args:
        focus: Focus string (wp:<id>, step:<id>, or None)

    Returns:
        {"target_type": "work_package"|"step", "target_id": str} or None
    """
    if focus is None or focus == "none":
        return None

    if focus.startswith("wp:"):
        return {"target_type": "work_package", "target_id": focus[3:]}
    elif focus.startswith("step:"):
        return {"target_type": "step", "target_id": focus[5:]}
    else:
        raise ValueError(f"Invalid focus format: {focus}")


def detect_collision(mission_id: str, focus: str | None, node_id: str = "cli-local") -> dict | None:
    """
    Detect advisory collision for drive=active transition.

    Args:
        mission_id: Mission identifier
        focus: Current focus target (wp:<id>, step:<id>, or None)
        node_id: CLI node identifier

    Returns:
        Collision dict if detected, None otherwise:
        {
            "type": "ConcurrentDriverWarning" or "PotentialStepCollisionDetected",
            "severity": "high" or "medium",
            "warning_id": str,
            "conflicting_participants": [...]
        }
    """
    # Get current session (self)
    self_state = load_session_state(mission_id)
    if not self_state:
        return None

    # Get mission roster (all participants)
    roster = get_mission_roster(mission_id)

    # Filter active drivers on same focus (excluding self)
    active_drivers = [
        p for p in roster
        if p.participant_id != self_state.participant_id
        and p.focus == focus
        and p.drive_intent == "active"
    ]

    if not active_drivers:
        return None  # No collision

    # Determine collision type and severity
    if len(active_drivers) >= 1:
        collision_type = "ConcurrentDriverWarning" if len(active_drivers) > 1 else "PotentialStepCollisionDetected"
        severity = "high" if len(active_drivers) > 1 else "medium"

        warning_id = generate_event_id()

        # Emit warning event
        clock = LamportClock(node_id)
        import uuid
        event = Event(
            event_id=generate_event_id(),
            event_type=collision_type,
            aggregate_id=f"mission/{mission_id}",
            payload={
                "warning_id": warning_id,
                "mission_id": mission_id,
                "participant_ids": [self_state.participant_id, *[p.participant_id for p in active_drivers]],
                "focus_target": _to_focus_target(focus),
                "severity": severity,
            },
            timestamp=datetime.now(),
            node_id=node_id,
            lamport_clock=clock.increment(),
            causation_id=None,
            project_uuid=uuid.UUID(self_state.mission_run_id) if self_state.mission_run_id else uuid.uuid4(),
            project_slug=mission_id,
            correlation_id=self_state.mission_run_id or generate_event_id(),
            schema_version="1.0.0",
            data_tier=0,
        )
        emit_event(mission_id, event, self_state.saas_api_url, self_state.session_token)

        return {
            "type": collision_type,
            "severity": severity,
            "warning_id": warning_id,
            "conflicting_participants": [
                {
                    "participant_id": p.participant_id,
                    "focus": p.focus,
                    "last_activity_at": p.last_activity_at.isoformat(),
                }
                for p in active_drivers
            ],
        }

    return None
