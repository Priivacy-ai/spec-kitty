"""Tests for collision detection and warning system."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from specify_cli.collaboration.warnings import detect_collision
from specify_cli.collaboration.models import SessionState


@pytest.fixture
def mock_self_state():
    """Self participant state."""
    return SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="self-participant",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus="wp:WP01",
    )


@pytest.fixture
def mock_other_state_active():
    """Another participant with active drive on same focus."""
    return SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="other-participant",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP01",
    )


def test_detect_collision_no_session(mock_self_state):
    """Returns None if no session loaded."""
    with patch("specify_cli.collaboration.warnings.load_session_state") as mock_load:
        mock_load.return_value = None
        collision = detect_collision("mission-123", "wp:WP01")
        assert collision is None


def test_detect_collision_no_other_drivers(mock_self_state):
    """Returns None if no other active drivers on same focus."""
    with patch("specify_cli.collaboration.warnings.load_session_state") as mock_load, \
         patch("specify_cli.collaboration.warnings.get_mission_roster") as mock_roster:
        mock_load.return_value = mock_self_state
        mock_roster.return_value = [mock_self_state]  # Only self

        collision = detect_collision("mission-123", "wp:WP01")
        assert collision is None


def test_detect_collision_one_active_driver(mock_self_state, mock_other_state_active):
    """Detects one active driver (medium severity)."""
    with patch("specify_cli.collaboration.warnings.load_session_state") as mock_load, \
         patch("specify_cli.collaboration.warnings.get_mission_roster") as mock_roster, \
         patch("specify_cli.collaboration.warnings.emit_event") as mock_emit:
        mock_load.return_value = mock_self_state
        mock_roster.return_value = [mock_self_state, mock_other_state_active]

        collision = detect_collision("mission-123", "wp:WP01")

        assert collision is not None
        assert collision["type"] == "PotentialStepCollisionDetected"
        assert collision["severity"] == "medium"
        assert len(collision["conflicting_participants"]) == 1
        assert collision["conflicting_participants"][0]["participant_id"] == "other-participant"
        assert collision["conflicting_participants"][0]["focus"] == "wp:WP01"

        # Should emit warning event
        mock_emit.assert_called_once()


def test_detect_collision_two_active_drivers(mock_self_state):
    """Detects 2+ active drivers (high severity)."""
    other1 = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="other-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP01",
    )
    other2 = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="other-2",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP01",
    )

    with patch("specify_cli.collaboration.warnings.load_session_state") as mock_load, \
         patch("specify_cli.collaboration.warnings.get_mission_roster") as mock_roster, \
         patch("specify_cli.collaboration.warnings.emit_event") as mock_emit:
        mock_load.return_value = mock_self_state
        mock_roster.return_value = [mock_self_state, other1, other2]

        collision = detect_collision("mission-123", "wp:WP01")

        assert collision is not None
        assert collision["type"] == "ConcurrentDriverWarning"
        assert collision["severity"] == "high"
        assert len(collision["conflicting_participants"]) == 2

        # Should emit warning event
        mock_emit.assert_called_once()


def test_detect_collision_different_focus(mock_self_state):
    """Returns None if other drivers on different focus."""
    other = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="other-participant",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP02",  # Different focus
    )

    with patch("specify_cli.collaboration.warnings.load_session_state") as mock_load, \
         patch("specify_cli.collaboration.warnings.get_mission_roster") as mock_roster:
        mock_load.return_value = mock_self_state
        mock_roster.return_value = [mock_self_state, other]

        collision = detect_collision("mission-123", "wp:WP01")
        assert collision is None


def test_detect_collision_inactive_driver(mock_self_state):
    """Returns None if other participant has inactive drive."""
    other = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="other-participant",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",  # Inactive
        focus="wp:WP01",
    )

    with patch("specify_cli.collaboration.warnings.load_session_state") as mock_load, \
         patch("specify_cli.collaboration.warnings.get_mission_roster") as mock_roster:
        mock_load.return_value = mock_self_state
        mock_roster.return_value = [mock_self_state, other]

        collision = detect_collision("mission-123", "wp:WP01")
        assert collision is None


def test_detect_collision_focus_format_match():
    """Collision detection matches focus format correctly (wp: not work_package:)."""
    # This tests the fix for the focus encoding mismatch bug
    self_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="self-participant",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus="wp:WP01",  # Local session uses wp:
    )
    other = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="other-participant",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP01",  # Roster reconstructs as wp: (after fix)
    )

    with patch("specify_cli.collaboration.warnings.load_session_state") as mock_load, \
         patch("specify_cli.collaboration.warnings.get_mission_roster") as mock_roster, \
         patch("specify_cli.collaboration.warnings.emit_event") as mock_emit:
        mock_load.return_value = self_state
        mock_roster.return_value = [self_state, other]

        collision = detect_collision("mission-123", "wp:WP01")

        # Should detect collision (not false negative due to format mismatch)
        assert collision is not None
        assert collision["type"] == "PotentialStepCollisionDetected"


def test_detect_collision_none_focus(mock_self_state):
    """Handles None focus (no focus set)."""
    mock_self_state.focus = None

    with patch("specify_cli.collaboration.warnings.load_session_state") as mock_load, \
         patch("specify_cli.collaboration.warnings.get_mission_roster") as mock_roster:
        mock_load.return_value = mock_self_state
        mock_roster.return_value = [mock_self_state]

        collision = detect_collision("mission-123", None)
        assert collision is None
