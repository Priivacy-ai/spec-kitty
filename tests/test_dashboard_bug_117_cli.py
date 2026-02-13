"""CLI-level tests for Bug #117 - Dashboard error message improvements.

This module tests that the CLI command correctly displays error messages
and actionable guidance for common failure scenarios.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.dashboard import dashboard


runner = CliRunner()


class TestCLIErrorMessages:
    """Test T021-T022: CLI error messages with actionable guidance."""

    def test_missing_kittify_shows_init_suggestion(self, tmp_path: Path, monkeypatch):
        """Test T021: Missing .kittify → CLI shows specific error with init suggestion."""
        project_dir = tmp_path
        # No .kittify directory exists

        # Mock get_project_root_or_exit to return our test path
        monkeypatch.setattr(
            "specify_cli.cli.commands.dashboard.get_project_root_or_exit",
            lambda: project_dir,
        )
        # Mock check_version_compatibility to do nothing
        monkeypatch.setattr(
            "specify_cli.cli.commands.dashboard.check_version_compatibility",
            lambda *args: None,
        )

        with patch("specify_cli.cli.commands.dashboard.ensure_dashboard_running") as mock_ensure:
            # Simulate missing .kittify directory error
            mock_ensure.side_effect = FileNotFoundError("No such file or directory: '.kittify'")

            app = typer.Typer()
            app.command()(dashboard)
            result = runner.invoke(app, [])

            # Should exit with error code
            assert result.exit_code == 1

            output = result.stdout.lower()

            # Should show error message
            assert "❌" in result.stdout or "error" in output

            # Should mention .kittify or metadata
            assert ".kittify" in output or "metadata" in output

            # Should suggest init command
            assert "init" in output
            assert "spec-kitty init" in result.stdout

    def test_port_conflict_shows_specific_error_and_suggestions(self, tmp_path: Path, monkeypatch):
        """Test T022: Port conflict → CLI shows 'Port conflict detected' with suggestions."""
        project_dir = tmp_path
        kittify_dir = project_dir / ".kittify"
        kittify_dir.mkdir()

        mock_port = 9237

        monkeypatch.setattr(
            "specify_cli.cli.commands.dashboard.get_project_root_or_exit",
            lambda: project_dir,
        )
        monkeypatch.setattr(
            "specify_cli.cli.commands.dashboard.check_version_compatibility",
            lambda *args: None,
        )

        with patch("specify_cli.cli.commands.dashboard.ensure_dashboard_running") as mock_ensure:
            # Simulate port conflict
            mock_ensure.side_effect = OSError("Address already in use")

            app = typer.Typer()
            app.command()(dashboard)
            result = runner.invoke(app, ["--port", str(mock_port)])

            # Should exit with error code
            assert result.exit_code == 1

            output = result.stdout.lower()

            # Should show port conflict error
            assert "❌" in result.stdout or "error" in output
            assert "port" in output or "address already in use" in output

            # Should suggest actionable steps
            assert "spec-kitty dashboard" in result.stdout
            # Should suggest either different port or --kill
            has_suggestions = (
                "--port" in result.stdout or
                "--kill" in result.stdout or
                "different port" in output or
                "kill existing" in output
            )
            assert has_suggestions, "Should suggest actionable steps for port conflict"

    def test_generic_error_shows_helpful_message(self, tmp_path: Path, monkeypatch):
        """Test that generic errors show helpful troubleshooting message."""
        project_dir = tmp_path
        kittify_dir = project_dir / ".kittify"
        kittify_dir.mkdir()

        monkeypatch.setattr(
            "specify_cli.cli.commands.dashboard.get_project_root_or_exit",
            lambda: project_dir,
        )
        monkeypatch.setattr(
            "specify_cli.cli.commands.dashboard.check_version_compatibility",
            lambda *args: None,
        )

        with patch("specify_cli.cli.commands.dashboard.ensure_dashboard_running") as mock_ensure:
            # Simulate generic error
            mock_ensure.side_effect = RuntimeError("Something went wrong")

            app = typer.Typer()
            app.command()(dashboard)
            result = runner.invoke(app, [])

            # Should exit with error code
            assert result.exit_code == 1

            output = result.stdout.lower()

            # Should show error message
            assert "❌" in result.stdout or "error" in output or "unable" in output

            # Should show the actual error message
            assert "something went wrong" in output

            # Should suggest troubleshooting (init command)
            assert "spec-kitty" in result.stdout


class TestCLISuccessMessages:
    """Test that CLI shows correct success messages."""

    def test_success_shows_dashboard_url_and_port(self, tmp_path: Path, monkeypatch):
        """Test that successful dashboard start shows URL and port."""
        project_dir = tmp_path
        kittify_dir = project_dir / ".kittify"
        kittify_dir.mkdir()

        mock_port = 9237
        mock_url = f"http://127.0.0.1:{mock_port}"

        monkeypatch.setattr(
            "specify_cli.cli.commands.dashboard.get_project_root_or_exit",
            lambda: project_dir,
        )
        monkeypatch.setattr(
            "specify_cli.cli.commands.dashboard.check_version_compatibility",
            lambda *args: None,
        )

        with patch("specify_cli.cli.commands.dashboard.ensure_dashboard_running") as mock_ensure:
            # Simulate successful start
            mock_ensure.return_value = (mock_url, mock_port, True)

            app = typer.Typer()
            app.command()(dashboard)
            result = runner.invoke(app, ["--port", str(mock_port)])

            # Should succeed
            assert result.exit_code == 0

            output = result.stdout

            # Should show success indicator
            assert "✅" in output or "Status" in output

            # Should show URL and port
            assert mock_url in output
            assert str(mock_port) in output

            # Should indicate new dashboard started
            assert "Started" in output or "new dashboard" in output.lower()
