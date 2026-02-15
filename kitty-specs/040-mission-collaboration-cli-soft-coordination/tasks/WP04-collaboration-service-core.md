---
work_package_id: WP04
title: Collaboration Service Core
lane: "done"
dependencies: [WP02, WP03]
base_branch: 040-mission-collaboration-cli-soft-coordination-WP03
base_commit: 912014a3789215bc7927451d95e2a08c2945a284
created_at: '2026-02-15T13:31:06.134957+00:00'
subtasks: [T015, T016, T017, T018, T019, T020]
shell_pid: "57638"
agent: "codex"
review_status: "acknowledged"
reviewed_by: "Robert Douglass"
---

# WP04: Collaboration Service Core

**Purpose**: Implement domain logic for join, focus, drive, collision detection, warnings, and state materialized view.

**Context**: This work package contains the core business logic for mission collaboration. All CLI commands delegate to these use-cases.

**Target Branch**: 2.x

**Estimated Effort**: ~450 lines of code across 3 files

---

## Implementation Command

```bash
# WP04 depends on both WP02 and WP03 (multi-parent dependency)
# Branch from WP03, then merge WP02 manually

spec-kitty implement WP04 --base WP03
cd .worktrees/040-mission-collaboration-cli-soft-coordination-WP04/
git merge 040-mission-collaboration-cli-soft-coordination-WP02
```

---

## Subtasks

### T015: Implement Join Mission Use-Case (~90 lines)

**Purpose**: Implement join_mission use-case with SaaS API call and event emission.

**Files to Create**:
- `src/specify_cli/collaboration/service.py`

**Implementation**:
```python
import httpx
from datetime import datetime
from specify_cli.collaboration.session import save_session_state, set_active_mission
from specify_cli.collaboration.models import SessionState
from specify_cli.events.store import emit_event
from specify_cli.events.ulid_utils import generate_event_id
from specify_cli.events.lamport import LamportClock
from spec_kitty_events.models import Event


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
    )
    save_session_state(mission_id, state)

    # Set active mission
    set_active_mission(mission_id)

    # Emit ParticipantJoined event
    clock = LamportClock(node_id)
    event = Event(
        event_id=generate_event_id(),
        event_type="ParticipantJoined",
        aggregate_id=f"mission/{mission_id}",
        payload={
            "participant_id": participant_id,
            "mission_id": mission_id,
            "participant_identity": {
                "participant_id": participant_id,
                "participant_type": "human",
                "display_name": data.get("display_name"),
                "session_id": data.get("session_id"),
            },
            "auth_principal_id": data.get("auth_principal_id"),
        },
        timestamp=now.isoformat(),
        node_id=node_id,
        lamport_clock=clock.increment(),
        correlation_id=data.get("mission_run_id"),
        causation_id=None,
    )
    emit_event(mission_id, event, saas_api_url, session_token)

    return {
        "participant_id": participant_id,
        "role": role,
    }
```

**Validation**:
- ✅ Calls SaaS API with correct payload
- ✅ Uses SaaS as role validation authority
- ✅ Saves session state with participant_id
- ✅ Emits canonical `ParticipantJoined` event

---

### T016: Implement Set Focus Use-Case (~70 lines)

**Purpose**: Implement set_focus use-case with format validation.

**Implementation** (in `service.py`):
```python
from specify_cli.collaboration.session import ensure_joined, update_session_state


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

    # Idempotent check
    if state.focus == focus:
        return  # No change

    # Emit FocusChanged event
    clock = LamportClock(node_id)
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
        timestamp=datetime.now().isoformat(),
        node_id=node_id,
        lamport_clock=clock.increment(),
        correlation_id=state.mission_run_id,
        causation_id=None,
    )
    emit_event(mission_id, event, "", "")  # Will use stored session_token

    # Update session
    update_session_state(mission_id, focus=focus if focus != "none" else None)
```

**Validation**:
- ✅ Validates focus format
- ✅ Idempotent (no duplicate events)
- ✅ Updates session state

---

### T017: Implement Set Drive Use-Case (~80 lines)

**Purpose**: Implement set_drive use-case with pre-execution collision check.

**Implementation** (in `service.py`):
```python
from specify_cli.collaboration.warnings import detect_collision


def set_drive(mission_id: str, intent: str, node_id: str = "cli-local") -> dict:
    """
    Set drive intent (with pre-execution collision check if setting active).

    Args:
        mission_id: Mission identifier
        intent: Drive state (active, inactive)
        node_id: CLI node identifier

    Returns:
        Dictionary:
        - If collision: {"collision": {...}, "action": None}
        - If success: {"status": "success", "drive_intent": intent}

    Raises:
        ValueError: If not joined or invalid state
    """
    # Validate state
    if intent not in {"active", "inactive"}:
        raise ValueError(f"Invalid drive state: {intent}. Must be 'active' or 'inactive'")

    # Load session
    state = ensure_joined(mission_id)

    # Idempotent check
    if state.drive_intent == intent:
        return {"status": "success", "drive_intent": intent}

    # Pre-execution check (if setting active)
    if intent == "active":
        collision = detect_collision(mission_id, state.focus)
        if collision:
            return {"collision": collision, "action": None}

    # Emit DriveIntentSet event
    clock = LamportClock(node_id)
    event = Event(
        event_id=generate_event_id(),
        event_type="DriveIntentSet",
        aggregate_id=f"mission/{mission_id}",
        payload={
            "participant_id": state.participant_id,
            "mission_id": mission_id,
            "intent": intent,
        },
        timestamp=datetime.now().isoformat(),
        node_id=node_id,
        lamport_clock=clock.increment(),
        correlation_id=state.mission_run_id,
        causation_id=None,
    )
    emit_event(mission_id, event, "", "")

    # Update session
    update_session_state(mission_id, drive_intent=intent)

    return {"status": "success", "drive_intent": intent}
```

**Validation**:
- ✅ Runs collision check on active transition
- ✅ Returns collision dict if detected
- ✅ Updates session state on success

---

### T018: Implement Collision Detection (~100 lines)

**Purpose**: Implement advisory collision detection.

**Files to Create**:
- `src/specify_cli/collaboration/warnings.py`

**Implementation**:
```python
from specify_cli.collaboration.state import get_mission_roster
from specify_cli.collaboration.session import load_session_state
from specify_cli.events.ulid_utils import generate_event_id
from specify_cli.events.lamport import LamportClock
from specify_cli.events.store import emit_event
from spec_kitty_events.models import Event
from datetime import datetime


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

        # Emit warning event
        clock = LamportClock(node_id)
        event = Event(
            event_id=generate_event_id(),
            event_type=collision_type,
            aggregate_id=f"mission/{mission_id}",
            payload={
                "warning_id": generate_event_id(),
                "mission_id": mission_id,
                "participant_ids": [self_state.participant_id, *[p.participant_id for p in active_drivers]],
                "focus_target": _to_focus_target(focus),
                "severity": severity,
            },
            timestamp=datetime.now().isoformat(),
            node_id=node_id,
            lamport_clock=clock.increment(),
            correlation_id=self_state.mission_run_id,
            causation_id=None,
        )
        emit_event(mission_id, event, "", "")

        return {
            "type": collision_type,
            "severity": severity,
            "warning_id": event.payload["warning_id"],
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
```

**Validation**:
- ✅ Detects 2+ drivers on same focus (high severity)
- ✅ Detects 1 driver (medium severity)
- ✅ Returns None if no collision
- ✅ Emits warning event

---

### T019: Implement State Materialized View (~80 lines)

**Purpose**: Implement roster cache from event replay.

**Files to Create**:
- `src/specify_cli/collaboration/state.py`

**Implementation**:
```python
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
            roster[participant_id] = SessionState(
                mission_id=mission_id,
                mission_run_id=event.correlation_id or "",
                participant_id=participant_id,
                role=payload.get("role", "participant"),
                joined_at=datetime.fromisoformat(event.timestamp),
                last_activity_at=datetime.fromisoformat(event.timestamp),
                drive_intent="inactive",
                focus=None,
            )

        # Update participant state based on event type
        if participant_id in roster:
            state = roster[participant_id]
            state.last_activity_at = datetime.fromisoformat(event.timestamp)

            if event_type == "FocusChanged":
                target = payload["focus_target"]
                state.focus = f"{target['target_type']}:{target['target_id']}"

            elif event_type == "DriveIntentSet":
                state.drive_intent = payload["intent"]

    return list(roster.values())
```

**Validation**:
- ✅ Replays events to build roster
- ✅ Handles ParticipantJoined, FocusChanged, DriveIntentSet
- ✅ Returns list of SessionState

---

### T020: Implement Warning Acknowledgement Flow (~30 lines)

**Purpose**: Implement acknowledge_warning use-case.

**Implementation** (in `service.py`):
```python
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
        timestamp=datetime.now().isoformat(),
        node_id=node_id,
        lamport_clock=clock.increment(),
        correlation_id=state.mission_run_id,
        causation_id=warning_id,
    )
    emit_event(mission_id, event, "", "")

    # If action == "reassign", emit CommentPosted with @mention (not implemented S1/M1)
```

**Validation**:
- ✅ Validates action in {continue, hold, reassign, defer}
- ✅ Emits WarningAcknowledged event
- ✅ Sets causation_id to warning_id

---

## Files Summary

**Created (3 files)**:
- `src/specify_cli/collaboration/service.py` (T015, T016, T017, T020)
- `src/specify_cli/collaboration/warnings.py` (T018)
- `src/specify_cli/collaboration/state.py` (T019)

---

## Validation Checklist

- ✅ Join calls SaaS API, stores participant_id, emits event
- ✅ Focus validates format, emits event, updates session
- ✅ Drive runs collision check before active transition
- ✅ Collision detection identifies 2+ drivers on same focus
- ✅ Materialized view replays events to build roster cache

---

## Notes

**Multi-Parent Dependency**:
- WP04 depends on both WP02 (events) and WP03 (session)
- Branch from WP03, manually merge WP02 after workspace creation

**Event Emission**:
- All use-cases emit events via `emit_event()` (from WP02)
- Events include Lamport clock, ULID event_id, causation_id

## Activity Log

- 2026-02-15T13:31:11Z – claude – shell_pid=45781 – lane=doing – Assigned agent via workflow command
- 2026-02-15T13:35:39Z – claude – shell_pid=45781 – lane=for_review – Ready for review: Implemented collaboration service core with join_mission, set_focus, set_drive, detect_collision, get_mission_roster, and acknowledge_warning use-cases. All functions emit canonical events, perform validation, and integrate with session state. Collision detection identifies 2+ active drivers (high severity) or 1 active driver (medium severity) on same focus. Materialized view replays events to build roster cache. All tests passing.
- 2026-02-15T13:36:08Z – codex – shell_pid=49108 – lane=doing – Started review via workflow command
- 2026-02-15T13:40:53Z – codex – shell_pid=49108 – lane=planned – Moved to planned
- 2026-02-15T13:49:29Z – codex – shell_pid=49108 – lane=for_review – Moved to for_review
- 2026-02-15T13:50:02Z – codex – shell_pid=57638 – lane=doing – Started review via workflow command
- 2026-02-15T13:56:08Z – codex – shell_pid=57638 – lane=done – Codex approval round 2: All blocking issues fixed. Implementation matches WP04 requirements. 36/36 collaboration tests passing.
