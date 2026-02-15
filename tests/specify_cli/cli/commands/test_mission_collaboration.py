"""Tests for mission collaboration CLI commands (join, focus)."""

from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.mission import app


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


class TestMissionJoin:
    """Tests for spec-kitty mission join command."""

    @patch("specify_cli.cli.commands.mission.join_mission")
    @patch("specify_cli.cli.commands.mission.os.getenv")
    def test_join_success(self, mock_getenv, mock_join_mission, runner):
        """Test successful mission join."""
        # Setup
        mock_getenv.side_effect = lambda key, default="": {
            "SAAS_API_URL": "https://api.test.com",
            "SAAS_AUTH_TOKEN": "test_token",
        }.get(key, default)

        mock_join_mission.return_value = {
            "participant_id": "01HXN7KQGZP8VXZB5RMKY6JTQW",
            "role": "developer",
        }

        # Execute
        result = runner.invoke(app, ["join", "mission-123", "--role", "developer"])

        # Verify
        assert result.exit_code == 0
        assert "Joined mission" in result.stdout
        assert "mission-123" in result.stdout
        assert "developer" in result.stdout
        assert "01HXN7KQGZP8VXZB5RMKY6JTQW" in result.stdout

        mock_join_mission.assert_called_once_with(
            "mission-123", "developer", "https://api.test.com", "test_token"
        )

    @patch("specify_cli.cli.commands.mission.os.getenv")
    def test_join_missing_auth_token(self, mock_getenv, runner):
        """Test join fails when SAAS_AUTH_TOKEN not set."""
        # Setup
        mock_getenv.side_effect = lambda key, default="": {
            "SAAS_API_URL": "https://api.test.com",
            "SAAS_AUTH_TOKEN": "",  # Empty token
        }.get(key, default)

        # Execute
        result = runner.invoke(app, ["join", "mission-123", "--role", "developer"])

        # Verify
        assert result.exit_code == 1
        assert "SAAS_AUTH_TOKEN" in result.stdout
        assert "not set" in result.stdout

    @patch("specify_cli.cli.commands.mission.join_mission")
    @patch("specify_cli.cli.commands.mission.os.getenv")
    def test_join_invalid_role(self, mock_getenv, mock_join_mission, runner):
        """Test join fails with invalid role."""
        # Setup
        mock_getenv.side_effect = lambda key, default="": {
            "SAAS_API_URL": "https://api.test.com",
            "SAAS_AUTH_TOKEN": "test_token",
        }.get(key, default)

        mock_join_mission.side_effect = ValueError("Invalid role: 'invalid_role'")

        # Execute
        result = runner.invoke(app, ["join", "mission-123", "--role", "invalid_role"])

        # Verify
        assert result.exit_code == 1
        assert "Invalid role" in result.stdout

    @patch("specify_cli.cli.commands.mission.join_mission")
    @patch("specify_cli.cli.commands.mission.os.getenv")
    def test_join_network_error(self, mock_getenv, mock_join_mission, runner):
        """Test join handles network errors gracefully."""
        # Setup
        mock_getenv.side_effect = lambda key, default="": {
            "SAAS_API_URL": "https://api.test.com",
            "SAAS_AUTH_TOKEN": "test_token",
        }.get(key, default)

        import httpx

        mock_join_mission.side_effect = httpx.ConnectError("Connection failed")

        # Execute
        result = runner.invoke(app, ["join", "mission-123", "--role", "developer"])

        # Verify
        assert result.exit_code == 1
        assert "Network error" in result.stdout


class TestMissionFocus:
    """Tests for spec-kitty mission focus commands."""

    @patch("specify_cli.cli.commands.mission.set_focus")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_focus_set_wp(self, mock_resolve, mock_set_focus, runner):
        """Test focus set to work package."""
        # Setup
        mock_resolve.return_value = "mission-123"

        # Execute
        result = runner.invoke(app, ["focus", "set", "wp:WP01"])

        # Verify
        assert result.exit_code == 0
        assert "Focus set to" in result.stdout
        assert "wp:WP01" in result.stdout

        mock_resolve.assert_called_once_with(None)
        mock_set_focus.assert_called_once_with("mission-123", "wp:WP01")

    @patch("specify_cli.cli.commands.mission.set_focus")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_focus_set_step(self, mock_resolve, mock_set_focus, runner):
        """Test focus set to step."""
        # Setup
        mock_resolve.return_value = "mission-123"

        # Execute
        result = runner.invoke(app, ["focus", "set", "step:T001"])

        # Verify
        assert result.exit_code == 0
        assert "Focus set to" in result.stdout
        assert "step:T001" in result.stdout

        mock_set_focus.assert_called_once_with("mission-123", "step:T001")

    @patch("specify_cli.cli.commands.mission.set_focus")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_focus_set_none(self, mock_resolve, mock_set_focus, runner):
        """Test focus set to none (clear focus)."""
        # Setup
        mock_resolve.return_value = "mission-123"

        # Execute
        result = runner.invoke(app, ["focus", "set", "none"])

        # Verify
        assert result.exit_code == 0
        assert "Focus set to" in result.stdout
        assert "none" in result.stdout

        mock_set_focus.assert_called_once_with("mission-123", "none")

    @patch("specify_cli.cli.commands.mission.set_focus")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_focus_set_explicit_mission(self, mock_resolve, mock_set_focus, runner):
        """Test focus set with explicit mission ID."""
        # Setup
        mock_resolve.return_value = "mission-456"

        # Execute
        result = runner.invoke(app, ["focus", "set", "wp:WP02", "--mission", "mission-456"])

        # Verify
        assert result.exit_code == 0

        mock_resolve.assert_called_once_with("mission-456")
        mock_set_focus.assert_called_once_with("mission-456", "wp:WP02")

    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_focus_set_no_active_mission(self, mock_resolve, runner):
        """Test focus set fails when no active mission."""
        # Setup
        mock_resolve.side_effect = ValueError("No active mission")

        # Execute
        result = runner.invoke(app, ["focus", "set", "wp:WP01"])

        # Verify
        assert result.exit_code == 1
        assert "No active mission" in result.stdout

    @patch("specify_cli.cli.commands.mission.set_focus")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_focus_set_invalid_format(self, mock_resolve, mock_set_focus, runner):
        """Test focus set fails with invalid format."""
        # Setup
        mock_resolve.return_value = "mission-123"
        mock_set_focus.side_effect = ValueError("Invalid focus format: invalid")

        # Execute
        result = runner.invoke(app, ["focus", "set", "invalid"])

        # Verify
        assert result.exit_code == 1
        assert "Invalid focus format" in result.stdout

    @patch("specify_cli.cli.commands.mission.set_focus")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_focus_set_not_joined(self, mock_resolve, mock_set_focus, runner):
        """Test focus set fails when not joined to mission."""
        # Setup
        mock_resolve.return_value = "mission-123"
        mock_set_focus.side_effect = ValueError("Not joined to mission mission-123")

        # Execute
        result = runner.invoke(app, ["focus", "set", "wp:WP01"])

        # Verify
        assert result.exit_code == 1
        assert "Not joined" in result.stdout


class TestMissionDrive:
    """Tests for spec-kitty mission drive commands."""

    @patch("specify_cli.cli.commands.mission.set_drive")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_drive_set_active_no_collision(self, mock_resolve, mock_set_drive, runner):
        """Test drive set to active with no collision."""
        # Setup
        mock_resolve.return_value = "mission-123"
        mock_set_drive.return_value = {"status": "success", "drive_intent": "active"}

        # Execute
        result = runner.invoke(app, ["drive", "set", "active"])

        # Verify
        assert result.exit_code == 0
        assert "Drive intent set to" in result.stdout
        assert "active" in result.stdout

        mock_resolve.assert_called_once_with(None)
        mock_set_drive.assert_called_once_with("mission-123", "active")

    @patch("specify_cli.cli.commands.mission.acknowledge_warning")
    @patch("specify_cli.cli.commands.mission.set_drive")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_drive_set_collision_continue(
        self, mock_resolve, mock_set_drive, mock_acknowledge, runner
    ):
        """Test drive set handles collision with continue action."""
        # Setup
        mock_resolve.return_value = "mission-123"
        mock_set_drive.side_effect = [
            {
                "collision": {
                    "type": "drive_collision",
                    "severity": "high",
                    "warning_id": "warning-123",
                    "conflicting_participants": [
                        {
                            "participant_id": "participant-456",
                            "focus": "wp:WP01",
                            "last_activity_at": "10:30:00",
                        }
                    ],
                }
            },
            {"status": "success", "drive_intent": "active"},
        ]

        # Execute with simulated user input
        result = runner.invoke(app, ["drive", "set", "active"], input="c\n")

        # Verify
        assert result.exit_code == 0
        assert "Collision Detected" in result.stdout
        assert "collision acknowledged" in result.stdout

        assert mock_set_drive.call_count == 2
        mock_acknowledge.assert_called_once_with("mission-123", "warning-123", "continue")

    @patch("specify_cli.cli.commands.mission.acknowledge_warning")
    @patch("specify_cli.cli.commands.mission.set_drive")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_drive_set_collision_hold(
        self, mock_resolve, mock_set_drive, mock_acknowledge, runner
    ):
        """Test drive set handles collision with hold action."""
        # Setup
        mock_resolve.return_value = "mission-123"
        mock_set_drive.return_value = {
            "collision": {
                "type": "drive_collision",
                "severity": "medium",
                "warning_id": "warning-123",
                "conflicting_participants": [],
            }
        }

        # Execute with simulated user input
        result = runner.invoke(app, ["drive", "set", "active"], input="h\n")

        # Verify
        assert result.exit_code == 0
        assert "Drive remains inactive" in result.stdout

        mock_acknowledge.assert_called_once_with("mission-123", "warning-123", "hold")

    @patch("specify_cli.cli.commands.mission.set_drive")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_drive_set_inactive(self, mock_resolve, mock_set_drive, runner):
        """Test drive set to inactive."""
        # Setup
        mock_resolve.return_value = "mission-123"
        mock_set_drive.return_value = {"status": "success", "drive_intent": "inactive"}

        # Execute
        result = runner.invoke(app, ["drive", "set", "inactive"])

        # Verify
        assert result.exit_code == 0
        assert "Drive intent set to" in result.stdout
        assert "inactive" in result.stdout


class TestMissionStatus:
    """Tests for spec-kitty mission status command."""

    @patch("specify_cli.cli.commands.mission.get_mission_roster")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_status_display(self, mock_resolve, mock_roster, runner):
        """Test status command displays roster."""
        # Setup
        from specify_cli.collaboration.models import SessionState
        from datetime import datetime

        mock_resolve.return_value = "mission-123"
        mock_roster.return_value = [
            SessionState(
                mission_id="mission-123",
                mission_run_id="run-1",
                participant_id="participant-001",
                role="developer",
                joined_at=datetime(2026, 1, 1, 10, 0, 0),
                last_activity_at=datetime(2026, 1, 1, 10, 30, 0),
                drive_intent="active",
                focus="wp:WP01",
            ),
            SessionState(
                mission_id="mission-123",
                mission_run_id="run-1",
                participant_id="participant-002",
                role="reviewer",
                joined_at=datetime(2026, 1, 1, 10, 5, 0),
                last_activity_at=datetime(2026, 1, 1, 10, 25, 0),
                drive_intent="inactive",
                focus=None,
            ),
        ]

        # Execute
        result = runner.invoke(app, ["status"])

        # Verify
        assert result.exit_code == 0
        assert "Mission mission-123" in result.stdout
        assert "DEVELOPER" in result.stdout
        assert "REVIEWER" in result.stdout
        assert "wp:WP01" in result.stdout
        assert "1 active drivers" in result.stdout

    @patch("specify_cli.cli.commands.mission.get_mission_roster")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_status_verbose(self, mock_resolve, mock_roster, runner):
        """Test status command with verbose flag."""
        # Setup
        from specify_cli.collaboration.models import SessionState
        from datetime import datetime

        mock_resolve.return_value = "mission-123"
        mock_roster.return_value = [
            SessionState(
                mission_id="mission-123",
                mission_run_id="run-1",
                participant_id="participant-001-full-id",
                role="developer",
                joined_at=datetime(2026, 1, 1, 10, 0, 0),
                last_activity_at=datetime(2026, 1, 1, 10, 30, 0),
                drive_intent="active",
                focus="wp:WP01",
            ),
        ]

        # Execute
        result = runner.invoke(app, ["status", "--verbose"])

        # Verify
        assert result.exit_code == 0
        assert "participant-001-full-id" in result.stdout


class TestMissionComment:
    """Tests for spec-kitty mission comment command."""

    @patch("specify_cli.cli.commands.mission.generate_event_id")
    @patch("specify_cli.cli.commands.mission.LamportClock")
    @patch("specify_cli.cli.commands.mission.emit_event")
    @patch("specify_cli.cli.commands.mission.ensure_joined")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_comment_with_text(self, mock_resolve, mock_ensure, mock_emit, mock_clock, mock_gen_id, runner):
        """Test comment command with text argument."""
        # Setup
        from specify_cli.collaboration.models import SessionState
        from datetime import datetime

        mock_resolve.return_value = "mission-123"
        mock_ensure.return_value = SessionState(
            mission_id="mission-123",
            mission_run_id="run-1",
            participant_id="participant-001",
            role="developer",
            joined_at=datetime(2026, 1, 1, 10, 0, 0),
            last_activity_at=datetime(2026, 1, 1, 10, 30, 0),
            drive_intent="active",
            focus="wp:WP01",
        )
        mock_gen_id.return_value = "01HXN7KQGZP8VXZB5RMKY6JTQW"
        mock_clock_instance = MagicMock()
        mock_clock_instance.increment.return_value = 1
        mock_clock.return_value = mock_clock_instance

        # Execute
        result = runner.invoke(app, ["comment", "Test comment"])

        # Verify
        assert result.exit_code == 0
        assert "Comment posted" in result.stdout

        mock_emit.assert_called_once()

    @patch("specify_cli.cli.commands.mission.generate_event_id")
    @patch("specify_cli.cli.commands.mission.LamportClock")
    @patch("specify_cli.cli.commands.mission.emit_event")
    @patch("specify_cli.cli.commands.mission.ensure_joined")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_comment_truncates_long_text(self, mock_resolve, mock_ensure, mock_emit, mock_clock, mock_gen_id, runner):
        """Test comment command truncates text over 500 chars."""
        # Setup
        from specify_cli.collaboration.models import SessionState
        from datetime import datetime

        mock_resolve.return_value = "mission-123"
        mock_ensure.return_value = SessionState(
            mission_id="mission-123",
            mission_run_id="run-1",
            participant_id="participant-001",
            role="developer",
            joined_at=datetime(2026, 1, 1, 10, 0, 0),
            last_activity_at=datetime(2026, 1, 1, 10, 30, 0),
            drive_intent="active",
            focus="wp:WP01",
        )
        mock_gen_id.return_value = "01HXN7KQGZP8VXZB5RMKY6JTQW"
        mock_clock_instance = MagicMock()
        mock_clock_instance.increment.return_value = 1
        mock_clock.return_value = mock_clock_instance

        long_text = "x" * 600

        # Execute
        result = runner.invoke(app, ["comment", long_text])

        # Verify
        assert result.exit_code == 0
        assert "Truncating comment to 500 chars" in result.stdout

    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_comment_empty_text(self, mock_resolve, runner):
        """Test comment command rejects empty text."""
        # Setup
        mock_resolve.return_value = "mission-123"

        # Execute
        result = runner.invoke(app, ["comment", "   "])

        # Verify
        assert result.exit_code == 1
        assert "Comment cannot be empty" in result.stdout


class TestMissionDecide:
    """Tests for spec-kitty mission decide command."""

    @patch("specify_cli.cli.commands.mission.generate_event_id")
    @patch("specify_cli.cli.commands.mission.LamportClock")
    @patch("specify_cli.cli.commands.mission.emit_event")
    @patch("specify_cli.cli.commands.mission.ensure_joined")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_decide_with_text(self, mock_resolve, mock_ensure, mock_emit, mock_clock, mock_gen_id, runner):
        """Test decide command with text argument."""
        # Setup
        from specify_cli.collaboration.models import SessionState
        from datetime import datetime

        mock_resolve.return_value = "mission-123"
        mock_ensure.return_value = SessionState(
            mission_id="mission-123",
            mission_run_id="run-1",
            participant_id="participant-001",
            role="developer",
            joined_at=datetime(2026, 1, 1, 10, 0, 0),
            last_activity_at=datetime(2026, 1, 1, 10, 30, 0),
            drive_intent="active",
            focus="wp:WP01",
        )
        mock_gen_id.return_value = "01HXN7KQGZP8VXZB5RMKY6JTQW"
        mock_clock_instance = MagicMock()
        mock_clock_instance.increment.return_value = 1
        mock_clock.return_value = mock_clock_instance

        # Execute
        result = runner.invoke(app, ["decide", "Use PostgreSQL"])

        # Verify
        assert result.exit_code == 0
        assert "Decision captured" in result.stdout

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        event = call_args[0][1]
        assert event.event_type == "DecisionCaptured"
        assert event.payload["chosen_option"] == "Use PostgreSQL"
        assert event.payload["topic"] == "wp:WP01"

    @patch("specify_cli.cli.commands.mission.ensure_joined")
    @patch("specify_cli.cli.commands.mission.resolve_mission_id")
    def test_decide_empty_text(self, mock_resolve, mock_ensure, runner):
        """Test decide command rejects empty text."""
        # Setup
        from specify_cli.collaboration.models import SessionState
        from datetime import datetime

        mock_resolve.return_value = "mission-123"
        mock_ensure.return_value = SessionState(
            mission_id="mission-123",
            mission_run_id="run-1",
            participant_id="participant-001",
            role="developer",
            joined_at=datetime(2026, 1, 1, 10, 0, 0),
            last_activity_at=datetime(2026, 1, 1, 10, 30, 0),
            drive_intent="active",
            focus="wp:WP01",
        )

        # Execute
        result = runner.invoke(app, ["decide", "   "])

        # Verify
        assert result.exit_code == 1
        assert "Decision cannot be empty" in result.stdout
