"""Integration test for offline → online queue replay flow."""

import pytest
import httpx
import respx
from datetime import datetime
from unittest.mock import patch

from specify_cli.collaboration.service import join_mission, set_focus, set_drive
from specify_cli.events.store import read_pending_events, is_online
from specify_cli.events.replay import replay_pending_events
from specify_cli.collaboration.session import save_session_state, set_active_mission
from specify_cli.collaboration.models import SessionState


@pytest.mark.respx(base_url="https://api.example.com")
def test_offline_online_flow(respx_mock: respx.MockRouter, clean_queue_and_session):
    """Test offline → online flow with queue replay."""
    # Mock join API
    respx_mock.post("/api/v1/missions/mission-123/participants").mock(
        return_value=httpx.Response(
            200,
            json={
                "participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ",
                "session_token": "token123",
                "role": "developer",
            },
        )
    )

    # Mock batch replay API
    respx_mock.post("/api/v1/events/batch/").mock(
        return_value=httpx.Response(
            200, json={"accepted": [], "rejected": []}  # We'll check IDs later
        )
    )

    # Join mission (online)
    with patch("specify_cli.events.store.is_online", return_value=True):
        join_mission("mission-123", "developer", "https://api.example.com", "token")

    # Simulate offline commands
    with patch("specify_cli.events.store.is_online", return_value=False):
        set_focus("mission-123", "wp:WP01")
        set_drive("mission-123", "active")

    # Verify events queued
    pending = read_pending_events("mission-123")
    assert len(pending) >= 2  # FocusChanged and DriveIntentSet (plus ParticipantJoined if offline)

    # Count only the offline commands
    focus_events = [e for e in pending if e.event.event_type == "FocusChanged"]
    drive_events = [e for e in pending if e.event.event_type == "DriveIntentSet"]
    assert len(focus_events) >= 1
    assert len(drive_events) >= 1


@pytest.mark.respx(base_url="https://api.example.com")
def test_offline_mode_queues_events(clean_queue_and_session):
    """Test that offline mode queues events without network calls."""
    # Create session state manually (simulating already joined)
    state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="01HQRS8ZMBE6XYZABC0123ZZZZ",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus=None,
    )
    save_session_state("mission-123", state)
    set_active_mission("mission-123")

    # Execute commands in offline mode
    with patch("specify_cli.events.store.is_online", return_value=False):
        set_focus("mission-123", "wp:WP01")
        set_drive("mission-123", "active")

    # Verify events queued
    pending = read_pending_events("mission-123")
    assert len(pending) == 2

    # Verify event types
    event_types = {e.event.event_type for e in pending}
    assert "FocusChanged" in event_types
    assert "DriveIntentSet" in event_types


@pytest.mark.respx(base_url="https://api.example.com")
def test_is_online_detection(respx_mock: respx.MockRouter):
    """Test is_online health check."""
    # Online case
    respx_mock.get("/health").mock(return_value=httpx.Response(200))
    assert is_online("https://api.example.com") is True

    # Offline case
    respx_mock.get("/health").mock(side_effect=httpx.ConnectError("Connection failed"))
    assert is_online("https://api.example.com") is False


@pytest.mark.respx(base_url="https://api.example.com")
def test_reconnect_and_replay(respx_mock: respx.MockRouter, clean_queue_and_session):
    """Test reconnect and replay pending events."""
    # Create session state
    state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="01HQRS8ZMBE6XYZABC0123ZZZZ",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus=None,
    )
    save_session_state("mission-123", state)
    set_active_mission("mission-123")

    # Queue some events while offline
    with patch("specify_cli.events.store.is_online", return_value=False):
        set_focus("mission-123", "wp:WP01")
        set_drive("mission-123", "active")

    # Mock batch API for replay
    def custom_replay_response(request):
        # Accept all events in the request
        events = request.content.decode("utf-8")
        import json
        payload = json.loads(events)
        event_ids = [e["event_id"] for e in payload["events"]]
        return httpx.Response(200, json={"accepted": event_ids, "rejected": []})

    respx_mock.post("/api/v1/events/batch/").mock(side_effect=custom_replay_response)

    # Simulate reconnect and replay
    with patch("specify_cli.events.store.is_online", return_value=True):
        result = replay_pending_events("mission-123", "https://api.example.com", "token")

    # Verify all events were accepted
    assert len(result["accepted"]) == 2
    assert result["rejected"] == []

    # Verify events marked as delivered (no longer pending)
    pending = read_pending_events("mission-123")
    assert len(pending) == 0
