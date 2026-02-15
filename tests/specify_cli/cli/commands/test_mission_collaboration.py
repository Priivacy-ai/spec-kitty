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
