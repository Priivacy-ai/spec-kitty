"""Collaboration service core - domain logic for join, focus, drive, and warnings."""

import httpx
from datetime import datetime
from specify_cli.collaboration.session import (
    save_session_state,
    set_active_mission,
    ensure_joined,
    update_session_state,
)
from specify_cli.collaboration.models import SessionState
from specify_cli.events.store import emit_event
from specify_cli.events.ulid_utils import generate_event_id
from specify_cli.events.lamport import LamportClock
from specify_cli.spec_kitty_events.models import Event


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


def join_mission(
    mission_id: str,
    role: str,
    saas_api_url: str,
    auth_token: str,
    node_id: str = "cli-local",
) -> dict:
    """
    Join mission (SaaS-authoritative).

    Args:
        mission_id: Mission identifier
        role: Join role label (validated by SaaS)
        saas_api_url: SaaS API base URL
        auth_token: Authentication token
        node_id: CLI node identifier

    Returns:
        Dictionary with participant_id and role

    Raises:
        httpx.HTTPError: If SaaS API call fails
    """
    # Call SaaS join API
    endpoint = f"{saas_api_url}/api/v1/missions/{mission_id}/participants"
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    payload = {"role": role}

    response = httpx.post(endpoint, json=payload, headers=headers, timeout=10.0)
    response.raise_for_status()  # Raises on 4xx/5xx

    data = response.json()
    participant_id = data["participant_id"]  # SaaS-minted ULID
    session_token = data.get("session_token", auth_token)

    # Save session state
    now = datetime.now()
    state = SessionState(
        mission_id=mission_id,
        mission_run_id=data.get("mission_run_id", ""),
        participant_id=participant_id,
        role=role,
        joined_at=now,
        last_activity_at=now,
        drive_intent="inactive",
        focus=None,
        session_token=session_token,
        saas_api_url=saas_api_url,
    )
    save_session_state(mission_id, state)

    # Set active mission
    set_active_mission(mission_id)

    # Emit ParticipantJoined event
    clock = LamportClock(node_id)
    import uuid
    event = Event(
        event_id=generate_event_id(),
        event_type="ParticipantJoined",
        aggregate_id=f"mission/{mission_id}",
        payload={
            "participant_id": participant_id,
            "mission_id": mission_id,
            "role": role,  # Include role for event replay
            "participant_identity": {
                "participant_id": participant_id,
                "participant_type": "human",
                "display_name": data.get("display_name"),
                "session_id": data.get("session_id"),
            },
            "auth_principal_id": data.get("auth_principal_id"),
        },
        timestamp=now,
        node_id=node_id,
        lamport_clock=clock.increment(),
        causation_id=None,
        project_uuid=uuid.UUID(data.get("project_uuid", str(uuid.uuid4()))),
        project_slug=data.get("project_slug", mission_id),
        correlation_id=data.get("mission_run_id", generate_event_id()),
        schema_version="1.0.0",
        data_tier=0,
    )
    emit_event(mission_id, event, saas_api_url, session_token)

    return {
        "participant_id": participant_id,
        "role": role,
    }


def set_focus(mission_id: str, focus: str, node_id: str = "cli-local") -> None:
    """
    Set participant focus target.

    Args:
        mission_id: Mission identifier
        focus: Focus target (wp:<id>, step:<id>, or none)
        node_id: CLI node identifier

    Raises:
        ValueError: If not joined or invalid focus format
    """
    # Validate focus format
    if focus != "none" and not (focus.startswith("wp:") or focus.startswith("step:")):
        raise ValueError(f"Invalid focus format: {focus}. Expected wp:<id>, step:<id>, or none")

    # Load session
    state = ensure_joined(mission_id)

    # Idempotent check - normalize "none" to None for comparison
    normalized_focus = None if focus == "none" else focus
    if state.focus == normalized_focus:
        return  # No change

    # Emit FocusChanged event
    clock = LamportClock(node_id)
    import uuid
    event = Event(
        event_id=generate_event_id(),
        event_type="FocusChanged",
        aggregate_id=f"mission/{mission_id}",
        payload={
            "participant_id": state.participant_id,
            "mission_id": mission_id,
            "focus_target": _to_focus_target(focus),
            "previous_focus_target": _to_focus_target(state.focus) if state.focus else None,
        },
        timestamp=datetime.now(),
        node_id=node_id,
        lamport_clock=clock.increment(),
        causation_id=None,
        project_uuid=uuid.UUID(state.mission_run_id) if state.mission_run_id else uuid.uuid4(),
        project_slug=mission_id,
        correlation_id=state.mission_run_id or generate_event_id(),
        schema_version="1.0.0",
        data_tier=0,
    )
    emit_event(mission_id, event, state.saas_api_url, state.session_token)

    # Update session
    update_session_state(mission_id, focus=focus if focus != "none" else None)


def set_drive(mission_id: str, intent: str, node_id: str = "cli-local", bypass_collision: bool = False) -> dict:
    """
    Set drive intent (with pre-execution collision check if setting active).

    Args:
        mission_id: Mission identifier
        intent: Drive state (active, inactive)
        node_id: CLI node identifier
        bypass_collision: If True, skip collision detection (used after acknowledgement)

    Returns:
        Dictionary:
        - If collision: {"collision": {...}, "action": None}
        - If success: {"status": "success", "drive_intent": intent}

    Raises:
        ValueError: If not joined or invalid state
    """
    from specify_cli.collaboration.warnings import detect_collision

    # Validate state
    if intent not in {"active", "inactive"}:
        raise ValueError(f"Invalid drive state: {intent}. Must be 'active' or 'inactive'")

    # Load session
    state = ensure_joined(mission_id)

    # Idempotent check
    if state.drive_intent == intent:
        return {"status": "success", "drive_intent": intent}

    # Pre-execution check (if setting active and not bypassing)
    if intent == "active" and not bypass_collision:
        collision = detect_collision(mission_id, state.focus)
        if collision:
            return {"collision": collision, "action": None}

    # Emit DriveIntentSet event
    clock = LamportClock(node_id)
    import uuid
    event = Event(
        event_id=generate_event_id(),
        event_type="DriveIntentSet",
        aggregate_id=f"mission/{mission_id}",
        payload={
            "participant_id": state.participant_id,
            "mission_id": mission_id,
            "intent": intent,
        },
        timestamp=datetime.now(),
        node_id=node_id,
        lamport_clock=clock.increment(),
        causation_id=None,
        project_uuid=uuid.UUID(state.mission_run_id) if state.mission_run_id else uuid.uuid4(),
        project_slug=mission_id,
        correlation_id=state.mission_run_id or generate_event_id(),
        schema_version="1.0.0",
        data_tier=0,
    )
    emit_event(mission_id, event, state.saas_api_url, state.session_token)

    # Update session
    update_session_state(mission_id, drive_intent=intent)

    return {"status": "success", "drive_intent": intent}


def acknowledge_warning(
    mission_id: str,
    warning_id: str,
    acknowledgement: str,
    node_id: str = "cli-local",
) -> None:
    """
    Acknowledge collision warning.

    Args:
        mission_id: Mission identifier
        warning_id: Event ID of warning event
        acknowledgement: continue, hold, reassign, defer
        node_id: CLI node identifier

    Raises:
        ValueError: If action invalid
    """
    valid_actions = {"continue", "hold", "reassign", "defer"}
    if acknowledgement not in valid_actions:
        raise ValueError(f"Invalid acknowledgement: {acknowledgement}. Must be one of {valid_actions}")

    state = ensure_joined(mission_id)

    # Emit WarningAcknowledged event
    clock = LamportClock(node_id)
    import uuid
    event = Event(
        event_id=generate_event_id(),
        event_type="WarningAcknowledged",
        aggregate_id=f"mission/{mission_id}",
        payload={
            "participant_id": state.participant_id,
            "mission_id": mission_id,
            "warning_id": warning_id,
            "acknowledgement": acknowledgement,
        },
        timestamp=datetime.now(),
        node_id=node_id,
        lamport_clock=clock.increment(),
        causation_id=warning_id,
        project_uuid=uuid.UUID(state.mission_run_id) if state.mission_run_id else uuid.uuid4(),
        project_slug=mission_id,
        correlation_id=state.mission_run_id or generate_event_id(),
        schema_version="1.0.0",
        data_tier=0,
    )
    emit_event(mission_id, event, state.saas_api_url, state.session_token)

    # If action == "reassign", emit CommentPosted with @mention (not implemented S1/M1)
