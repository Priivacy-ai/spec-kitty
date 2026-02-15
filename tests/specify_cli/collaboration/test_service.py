"""Tests for collaboration service core."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import httpx
from specify_cli.collaboration.service import (
    join_mission,
    set_focus,
    set_drive,
    acknowledge_warning,
    _to_focus_target,
)
from specify_cli.collaboration.models import SessionState


def test_to_focus_target_none():
    """Converts None to None."""
    assert _to_focus_target(None) is None


def test_to_focus_target_none_string():
    """Converts 'none' string to None."""
    assert _to_focus_target("none") is None


def test_to_focus_target_work_package():
    """Converts wp:<id> to work_package target."""
    result = _to_focus_target("wp:WP01")
    assert result == {"target_type": "work_package", "target_id": "WP01"}


def test_to_focus_target_step():
    """Converts step:<id> to step target."""
    result = _to_focus_target("step:T015")
    assert result == {"target_type": "step", "target_id": "T015"}


def test_to_focus_target_invalid():
    """Raises ValueError for invalid format."""
    with pytest.raises(ValueError, match="Invalid focus format"):
        _to_focus_target("invalid:format")


def test_join_mission_success():
    """join_mission calls SaaS API and saves session."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "participant_id": "participant-123",
        "mission_run_id": "run-456",
        "session_token": "token-789",
        "display_name": "Test User",
        "session_id": "session-999",
        "auth_principal_id": "auth-111",
    }
    mock_response.raise_for_status = Mock()

    with patch("httpx.post", return_value=mock_response) as mock_post, \
         patch("specify_cli.collaboration.service.save_session_state") as mock_save, \
         patch("specify_cli.collaboration.service.set_active_mission") as mock_set_active, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        result = join_mission(
            mission_id="mission-123",
            role="developer",
            saas_api_url="https://api.example.com",
            auth_token="auth-token",
            node_id="cli-local",
        )

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://api.example.com/api/v1/missions/mission-123/participants" in call_args[0]
        assert call_args[1]["json"] == {"role": "developer"}
        assert call_args[1]["headers"]["Authorization"] == "Bearer auth-token"

        # Verify session saved
        mock_save.assert_called_once()
        saved_state = mock_save.call_args[0][1]
        assert saved_state.participant_id == "participant-123"
        assert saved_state.mission_id == "mission-123"
        assert saved_state.role == "developer"

        # Verify active mission set
        mock_set_active.assert_called_once_with("mission-123")

        # Verify event emitted
        mock_emit.assert_called_once()
        emitted_event = mock_emit.call_args[0][1]
        assert emitted_event.event_type == "ParticipantJoined"

        # Verify return value
        assert result == {"participant_id": "participant-123", "role": "developer"}


def test_join_mission_api_error():
    """join_mission raises HTTPError on API failure."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "403 Forbidden", request=Mock(), response=mock_response
    )

    with patch("httpx.post", return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            join_mission(
                mission_id="mission-123",
                role="invalid-role",
                saas_api_url="https://api.example.com",
                auth_token="auth-token",
            )


def test_set_focus_invalid_format():
    """set_focus raises ValueError for invalid format."""
    with pytest.raises(ValueError, match="Invalid focus format"):
        set_focus("mission-123", "invalid-format")


def test_set_focus_success():
    """set_focus updates session and emits event."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus=None,
    )

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.service.update_session_state") as mock_update, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        set_focus("mission-123", "wp:WP01")

        # Verify session updated
        mock_update.assert_called_once_with("mission-123", focus="wp:WP01")

        # Verify event emitted
        mock_emit.assert_called_once()
        emitted_event = mock_emit.call_args[0][1]
        assert emitted_event.event_type == "FocusChanged"
        assert emitted_event.payload["focus_target"] == {"target_type": "work_package", "target_id": "WP01"}


def test_set_focus_none_string():
    """set_focus('none') clears focus."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus="wp:WP01",
    )

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.service.update_session_state") as mock_update, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        set_focus("mission-123", "none")

        # Verify session updated with None (not "none" string)
        mock_update.assert_called_once_with("mission-123", focus=None)

        # Verify event emitted
        mock_emit.assert_called_once()
        emitted_event = mock_emit.call_args[0][1]
        assert emitted_event.payload["focus_target"] is None


def test_set_focus_idempotent():
    """set_focus is idempotent (no duplicate events for same focus)."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus="wp:WP01",
    )

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.service.update_session_state") as mock_update, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        set_focus("mission-123", "wp:WP01")

        # Should not update or emit (already at wp:WP01)
        mock_update.assert_not_called()
        mock_emit.assert_not_called()


def test_set_focus_none_idempotent():
    """set_focus('none') is idempotent when focus already None."""
    # This tests the fix for issue #3: set_focus("none") not idempotent
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus=None,  # Already no focus
    )

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.service.update_session_state") as mock_update, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        set_focus("mission-123", "none")

        # Should not update or emit (already None)
        mock_update.assert_not_called()
        mock_emit.assert_not_called()


def test_set_drive_invalid_intent():
    """set_drive raises ValueError for invalid intent."""
    with pytest.raises(ValueError, match="Invalid drive state"):
        set_drive("mission-123", "invalid-intent")


def test_set_drive_active_no_collision():
    """set_drive(active) succeeds when no collision detected."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus="wp:WP01",
    )

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.warnings.detect_collision", return_value=None), \
         patch("specify_cli.collaboration.service.update_session_state") as mock_update, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        result = set_drive("mission-123", "active")

        assert result == {"status": "success", "drive_intent": "active"}
        mock_update.assert_called_once_with("mission-123", drive_intent="active")
        mock_emit.assert_called_once()


def test_set_drive_active_with_collision():
    """set_drive(active) returns collision dict when detected."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="inactive",
        focus="wp:WP01",
    )
    mock_collision = {
        "type": "ConcurrentDriverWarning",
        "severity": "high",
        "warning_id": "01HZQW7X9K4QFJP7ZXQM5T8NVW",
        "conflicting_participants": [{"participant_id": "other-1"}],
    }

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.warnings.detect_collision", return_value=mock_collision), \
         patch("specify_cli.collaboration.service.update_session_state") as mock_update, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        result = set_drive("mission-123", "active")

        # Should return collision, not update state
        assert result == {"collision": mock_collision, "action": None}
        mock_update.assert_not_called()
        mock_emit.assert_not_called()


def test_set_drive_inactive():
    """set_drive(inactive) does not run collision check."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP01",
    )

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.warnings.detect_collision") as mock_detect, \
         patch("specify_cli.collaboration.service.update_session_state") as mock_update, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        result = set_drive("mission-123", "inactive")

        # Should not call detect_collision for inactive transition
        mock_detect.assert_not_called()
        mock_update.assert_called_once_with("mission-123", drive_intent="inactive")
        mock_emit.assert_called_once()


def test_set_drive_idempotent():
    """set_drive is idempotent (no duplicate events for same intent)."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP01",
    )

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.service.update_session_state") as mock_update, \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        result = set_drive("mission-123", "active")

        # Should not update or emit (already active)
        assert result == {"status": "success", "drive_intent": "active"}
        mock_update.assert_not_called()
        mock_emit.assert_not_called()


def test_acknowledge_warning_invalid_action():
    """acknowledge_warning raises ValueError for invalid action."""
    with pytest.raises(ValueError, match="Invalid acknowledgement"):
        acknowledge_warning("mission-123", "01HZQW7X9K4QFJP7ZXQM5T8NVW", "invalid-action")


def test_acknowledge_warning_success():
    """acknowledge_warning emits WarningAcknowledged event."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP01",
    )

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        acknowledge_warning("mission-123", "01HZQW7X9K4QFJP7ZXQM5T8NVW", "continue")

        # Verify event emitted
        mock_emit.assert_called_once()
        emitted_event = mock_emit.call_args[0][1]
        assert emitted_event.event_type == "WarningAcknowledged"
        assert emitted_event.payload["warning_id"] == "01HZQW7X9K4QFJP7ZXQM5T8NVW"
        assert emitted_event.payload["acknowledgement"] == "continue"
        assert emitted_event.causation_id == "01HZQW7X9K4QFJP7ZXQM5T8NVW"


def test_acknowledge_warning_all_valid_actions():
    """acknowledge_warning accepts all valid actions."""
    mock_state = SessionState(
        mission_id="mission-123",
        mission_run_id="run-123",
        participant_id="participant-1",
        role="developer",
        joined_at=datetime.now(),
        last_activity_at=datetime.now(),
        drive_intent="active",
        focus="wp:WP01",
    )

    valid_actions = ["continue", "hold", "reassign", "defer"]

    with patch("specify_cli.collaboration.service.ensure_joined", return_value=mock_state), \
         patch("specify_cli.collaboration.service.emit_event") as mock_emit:

        for action in valid_actions:
            mock_emit.reset_mock()
            acknowledge_warning("mission-123", "01HZQW7X9K4QFJP7ZXQM5T8NVW", action)
            mock_emit.assert_called_once()
            emitted_event = mock_emit.call_args[0][1]
            assert emitted_event.payload["acknowledgement"] == action
