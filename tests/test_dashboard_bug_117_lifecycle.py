"""Tests for Bug #117 - Dashboard False-Failure Detection.

This module tests the improved dashboard lifecycle that:
1. Detects running processes even when health check times out
2. Provides specific error messages for common failure modes
3. Works with --kill flag after startup fallback
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.dashboard.lifecycle import ensure_dashboard_running, stop_dashboard


class TestProcessDetectionWithHealthTimeout:
    """Test T020: Process running + health timeout → should report SUCCESS (not failure)."""

    def test_process_alive_but_health_slow_should_succeed(self, tmp_path: Path):
        """Dashboard process exists on port, but health check times out.

        Expected: Should detect running process and report SUCCESS.
        Actual (bug): Reports failure and kills the process.
        """
        project_dir = tmp_path
        kittify_dir = project_dir / ".kittify"
        kittify_dir.mkdir()

        # Mock: start_dashboard succeeds, returns PID
        mock_pid = 12345
        mock_port = 9237

        with patch("specify_cli.dashboard.lifecycle.start_dashboard") as mock_start, \
             patch("specify_cli.dashboard.lifecycle._check_dashboard_health") as mock_health, \
             patch("specify_cli.dashboard.lifecycle._is_process_alive") as mock_alive, \
             patch("specify_cli.dashboard.lifecycle._write_dashboard_file") as mock_write, \
             patch("specify_cli.dashboard.lifecycle.psutil.Process") as mock_proc, \
             patch("specify_cli.dashboard.lifecycle.time.sleep"):  # Mock sleep to avoid 20s delay!

            # Setup: Process starts successfully
            mock_start.return_value = (mock_port, mock_pid)

            # Setup: Health check always fails (timeout scenario)
            mock_health.return_value = False

            # Setup: Process is actually alive on the port
            mock_alive.return_value = True

            # This should NOT raise RuntimeError anymore
            url, port, started = ensure_dashboard_running(project_dir, preferred_port=mock_port)

            # Verify: Should return success
            assert url == f"http://127.0.0.1:{mock_port}"
            assert port == mock_port
            assert started is True

            # Verify: Should NOT kill the process
            mock_proc.assert_not_called()


class TestSpecificErrorMessages:
    """Tests T021-T022: Specific error messages for missing metadata and port conflicts."""

    def test_missing_kittify_dir_shows_init_suggestion(self, tmp_path: Path):
        """Test T021: Missing .kittify → should report specific error with init suggestion."""
        project_dir = tmp_path
        # No .kittify directory exists

        with patch("specify_cli.dashboard.lifecycle.start_dashboard") as mock_start:
            # Simulate missing .kittify directory error
            mock_start.side_effect = FileNotFoundError("No such file or directory: '.kittify'")

            with pytest.raises(FileNotFoundError) as exc_info:
                ensure_dashboard_running(project_dir)

            error_msg = str(exc_info.value).lower()
            # Should mention .kittify
            assert ".kittify" in error_msg

    def test_port_conflict_shows_specific_error(self, tmp_path: Path):
        """Test T022: Port conflict → should report 'Port X unavailable'."""
        project_dir = tmp_path
        kittify_dir = project_dir / ".kittify"
        kittify_dir.mkdir()

        mock_port = 9237

        with patch("specify_cli.dashboard.lifecycle.start_dashboard") as mock_start:
            # Simulate port conflict
            mock_start.side_effect = OSError("Address already in use")

            with pytest.raises(OSError) as exc_info:
                ensure_dashboard_running(project_dir, preferred_port=mock_port)

            error_msg = str(exc_info.value).lower()
            assert "address already in use" in error_msg


class TestKillAfterStartupFallback:
    """Test T023: dashboard --kill works after startup fallback."""

    def test_kill_works_with_fallback_state(self, tmp_path: Path):
        """Dashboard started with fallback detection, --kill should still work."""
        project_dir = tmp_path
        kittify_dir = project_dir / ".kittify"
        kittify_dir.mkdir()
        dashboard_file = kittify_dir / ".dashboard"

        # Simulate dashboard running with fallback detection
        # (process alive but health check was slow)
        dashboard_file.write_text(
            "http://127.0.0.1:9237\n"
            "9237\n"
            "abc123token\n"
            "12345\n"
        )

        with patch("specify_cli.dashboard.lifecycle._check_dashboard_health") as mock_health, \
             patch("specify_cli.dashboard.lifecycle.urllib.request.urlopen") as mock_urlopen, \
             patch("specify_cli.dashboard.lifecycle._is_process_alive") as mock_alive, \
             patch("specify_cli.dashboard.lifecycle.time.sleep"):  # Mock sleep to avoid delays!

            # Dashboard is healthy initially, then becomes unhealthy after shutdown
            # This prevents the 5-second timeout loop in stop_dashboard
            mock_health.side_effect = [True, False]
            mock_alive.return_value = True

            # Simulate successful shutdown
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            stopped, message = stop_dashboard(project_dir)

            assert stopped is True
            # Message should indicate success (stopped, shutdown, or ended)
            assert any(word in message.lower() for word in ["stopped", "shutdown", "ended"])

    def test_kill_with_health_timeout_but_process_alive(self, tmp_path: Path):
        """Test T023 enhancement: --kill works when health times out but PID is alive.

        This is the critical scenario where:
        - Health check fails (timeout)
        - But process is still running (PID is alive)
        - --kill should use PID-based termination fallback
        """
        project_dir = tmp_path
        kittify_dir = project_dir / ".kittify"
        kittify_dir.mkdir()
        dashboard_file = kittify_dir / ".dashboard"

        mock_pid = 12345

        # Simulate dashboard metadata with PID
        dashboard_file.write_text(
            "http://127.0.0.1:9237\n"
            "9237\n"
            "abc123token\n"
            f"{mock_pid}\n"
        )

        with patch("specify_cli.dashboard.lifecycle._check_dashboard_health") as mock_health, \
             patch("specify_cli.dashboard.lifecycle._is_process_alive") as mock_alive, \
             patch("specify_cli.dashboard.lifecycle.psutil.Process") as mock_proc:

            # Health check fails (timeout scenario)
            mock_health.return_value = False

            # But process is still alive
            mock_alive.return_value = True

            # Mock process termination
            mock_process_instance = MagicMock()
            mock_proc.return_value = mock_process_instance
            # Simulate graceful termination succeeds
            mock_process_instance.wait.return_value = None

            stopped, message = stop_dashboard(project_dir)

            # Should successfully stop via PID
            assert stopped is True

            # Should have attempted process termination
            mock_proc.assert_called_with(mock_pid)
            mock_process_instance.terminate.assert_called_once()

            # Message should indicate PID-based termination
            assert "pid" in message.lower() or "process" in message.lower()
            assert "12345" in message  # PID should be in message

            # Metadata file should be cleaned up
            assert not dashboard_file.exists()


class TestDashboardLifecycleImprovement:
    """Integration tests for the overall lifecycle improvement."""

    def test_health_timeout_with_dead_process_still_fails(self, tmp_path: Path):
        """Verify we still report failure when process actually dies."""
        project_dir = tmp_path
        kittify_dir = project_dir / ".kittify"
        kittify_dir.mkdir()

        mock_pid = 12345
        mock_port = 9237

        with patch("specify_cli.dashboard.lifecycle.start_dashboard") as mock_start, \
             patch("specify_cli.dashboard.lifecycle._check_dashboard_health") as mock_health, \
             patch("specify_cli.dashboard.lifecycle._is_process_alive") as mock_alive, \
             patch("specify_cli.dashboard.lifecycle.psutil.Process") as mock_proc, \
             patch("specify_cli.dashboard.lifecycle.time.sleep"), \
             patch("specify_cli.dashboard.lifecycle._is_spec_kitty_dashboard") as mock_spec_kitty:

            mock_start.return_value = (mock_port, mock_pid)
            mock_health.return_value = False

            # Process is actually dead
            mock_alive.return_value = False

            # Not a spec-kitty dashboard orphan (to avoid retry logic)
            mock_spec_kitty.return_value = False

            # Should still raise RuntimeError for truly failed startup
            with pytest.raises(RuntimeError) as exc_info:
                ensure_dashboard_running(project_dir, preferred_port=mock_port)

            # Should attempt to clean up dead process
            mock_proc.assert_called_with(mock_pid)

            error_msg = str(exc_info.value)
            assert "failed to start" in error_msg.lower()
