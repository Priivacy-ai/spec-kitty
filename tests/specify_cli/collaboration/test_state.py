"""Tests for mission roster state materialized view."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from specify_cli.collaboration.state import get_mission_roster
from specify_cli.collaboration.models import SessionState
from specify_cli.events.models import EventQueueEntry
from specify_cli.spec_kitty_events.models import Event


def test_get_mission_roster_empty_events():
    """Empty event log returns empty roster."""
    with patch("specify_cli.collaboration.state.read_all_events") as mock_read:
        mock_read.return_value = []
        roster = get_mission_roster("mission-123")
        assert roster == []


def test_get_mission_roster_participant_joined():
    """ParticipantJoined event creates roster entry."""
    now = datetime.now()
    event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={
            "participant_id": "participant-1",
            "mission_run_id": "run-123",
            "role": "developer",
        },
        timestamp=now,  # datetime object, not string
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )
    entry = EventQueueEntry(event=event, replay_status="delivered", retry_count=0, last_retry_at=None)

    with patch("specify_cli.collaboration.state.read_all_events") as mock_read:
        mock_read.return_value = [entry]
        roster = get_mission_roster("mission-123")

        assert len(roster) == 1
        state = roster[0]
        assert state.participant_id == "participant-1"
        assert state.role == "developer"
        assert state.mission_id == "mission-123"
        assert state.mission_run_id == "run-123"
        assert state.drive_intent == "inactive"
        assert state.focus is None
        assert state.joined_at == now
        assert state.last_activity_at == now


def test_get_mission_roster_focus_changed_wp_format():
    """FocusChanged event updates roster with wp: format (not work_package:)."""
    now = datetime.now()
    join_event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "participant-1", "mission_run_id": "run-123", "role": "developer"},
        timestamp=now,
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )
    focus_event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV2",
        event_type="FocusChanged",
        aggregate_id="mission/mission-123",
        payload={
            "participant_id": "participant-1",
            "focus_target": {"target_type": "work_package", "target_id": "WP01"},
        },
        timestamp=now,
        node_id="cli-local",
        lamport_clock=2,
        causation_id=None,
    )

    with patch("specify_cli.collaboration.state.read_all_events") as mock_read:
        mock_read.return_value = [
            EventQueueEntry(event=join_event, replay_status="delivered"),
            EventQueueEntry(event=focus_event, replay_status="delivered"),
        ]
        roster = get_mission_roster("mission-123")

        assert len(roster) == 1
        # Should be "wp:WP01", not "work_package:WP01"
        assert roster[0].focus == "wp:WP01"


def test_get_mission_roster_focus_changed_step_format():
    """FocusChanged with step target uses step: prefix."""
    now = datetime.now()
    join_event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "participant-1", "mission_run_id": "run-123", "role": "developer"},
        timestamp=now,
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )
    focus_event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV2",
        event_type="FocusChanged",
        aggregate_id="mission/mission-123",
        payload={
            "participant_id": "participant-1",
            "focus_target": {"target_type": "step", "target_id": "T015"},
        },
        timestamp=now,
        node_id="cli-local",
        lamport_clock=2,
        causation_id=None,
    )

    with patch("specify_cli.collaboration.state.read_all_events") as mock_read:
        mock_read.return_value = [
            EventQueueEntry(event=join_event, replay_status="delivered"),
            EventQueueEntry(event=focus_event, replay_status="delivered"),
        ]
        roster = get_mission_roster("mission-123")

        assert len(roster) == 1
        assert roster[0].focus == "step:T015"


def test_get_mission_roster_focus_cleared():
    """FocusChanged with null target clears focus."""
    now = datetime.now()
    join_event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "participant-1", "mission_run_id": "run-123", "role": "developer"},
        timestamp=now,
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )
    focus_set = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV2",
        event_type="FocusChanged",
        aggregate_id="mission/mission-123",
        payload={
            "participant_id": "participant-1",
            "focus_target": {"target_type": "work_package", "target_id": "WP01"},
        },
        timestamp=now,
        node_id="cli-local",
        lamport_clock=2,
        causation_id=None,
    )
    focus_clear = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV3",
        event_type="FocusChanged",
        aggregate_id="mission/mission-123",
        payload={
            "participant_id": "participant-1",
            "focus_target": None,
        },
        timestamp=now,
        node_id="cli-local",
        lamport_clock=3,
        causation_id=None,
    )

    with patch("specify_cli.collaboration.state.read_all_events") as mock_read:
        mock_read.return_value = [
            EventQueueEntry(event=join_event, replay_status="delivered"),
            EventQueueEntry(event=focus_set, replay_status="delivered"),
            EventQueueEntry(event=focus_clear, replay_status="delivered"),
        ]
        roster = get_mission_roster("mission-123")

        assert len(roster) == 1
        assert roster[0].focus is None


def test_get_mission_roster_drive_intent_set():
    """DriveIntentSet event updates drive_intent in roster."""
    now = datetime.now()
    join_event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "participant-1", "mission_run_id": "run-123", "role": "developer"},
        timestamp=now,
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )
    drive_event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV2",
        event_type="DriveIntentSet",
        aggregate_id="mission/mission-123",
        payload={
            "participant_id": "participant-1",
            "intent": "active",
        },
        timestamp=now,
        node_id="cli-local",
        lamport_clock=2,
        causation_id=None,
    )

    with patch("specify_cli.collaboration.state.read_all_events") as mock_read:
        mock_read.return_value = [
            EventQueueEntry(event=join_event, replay_status="delivered"),
            EventQueueEntry(event=drive_event, replay_status="delivered"),
        ]
        roster = get_mission_roster("mission-123")

        assert len(roster) == 1
        assert roster[0].drive_intent == "active"


def test_get_mission_roster_multiple_participants():
    """Multiple participants create separate roster entries."""
    now = datetime.now()
    join1 = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "participant-1", "mission_run_id": "run-123", "role": "developer"},
        timestamp=now,
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )
    join2 = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV2",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "participant-2", "mission_run_id": "run-123", "role": "reviewer"},
        timestamp=now,
        node_id="cli-local",
        lamport_clock=2,
        causation_id=None,
    )

    with patch("specify_cli.collaboration.state.read_all_events") as mock_read:
        mock_read.return_value = [
            EventQueueEntry(event=join1, replay_status="delivered"),
            EventQueueEntry(event=join2, replay_status="delivered"),
        ]
        roster = get_mission_roster("mission-123")

        assert len(roster) == 2
        assert {p.participant_id for p in roster} == {"participant-1", "participant-2"}


def test_get_mission_roster_timestamp_is_datetime():
    """Handles event.timestamp as datetime object (not string)."""
    # This is the core bug fix - event.timestamp is datetime, not ISO string
    now = datetime.now()
    event = Event(
        event_id="01HZQW7X9K4QFJP7ZXQM5T8NV1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "participant-1", "mission_run_id": "run-123", "role": "developer"},
        timestamp=now,  # datetime object
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )

    with patch("specify_cli.collaboration.state.read_all_events") as mock_read:
        mock_read.return_value = [EventQueueEntry(event=event, replay_status="delivered")]

        # Should not raise TypeError
        roster = get_mission_roster("mission-123")

        assert len(roster) == 1
        assert roster[0].joined_at == now
        assert roster[0].last_activity_at == now
