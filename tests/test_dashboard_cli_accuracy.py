"""Tests for dashboard CLI command status reporting accuracy.

Detects the bug where spec-kitty dashboard CLI command reports error
even though the dashboard actually starts successfully.

Bug Report: findings/0.5.1/2025-11-13_24_dashboard_cli_false_error.md

Problem:
- CLI shows: "❌ Unable to start or locate the dashboard"
- Reality: Dashboard IS running on the specified port
- Impact: Misleading error message, user thinks it failed

These tests validate that CLI status reporting matches actual dashboard state.
"""

import pytest
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory
import signal
import os
from urllib.request import urlopen
from urllib.error import URLError
import json


def is_dashboard_accessible(port: int, timeout: float = 2.0) -> bool:
    """Check if dashboard is accessible on the given port.

    Args:
        port: Port number to check
        timeout: Timeout in seconds

    Returns:
        True if dashboard responds, False otherwise
    """
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/features", timeout=timeout) as response:
            return response.status == 200
    except (URLError, OSError, Exception):
        return False


def kill_dashboard_process(port: int):
    """Kill any dashboard process running on the given port."""
    try:
        # Find process using the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    time.sleep(0.5)  # Give it time to shut down
                except:
                    pass
    except Exception:
        pass


def kill_all_spec_kitty_dashboards():
    """Kill all spec-kitty dashboard processes (test cleanup)."""
    try:
        # Find all Python processes running run_dashboard_server
        result = subprocess.run(
            ["pgrep", "-f", "run_dashboard_server"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except:
                    pass
            time.sleep(1)  # Give processes time to die
    except Exception:
        pass


class TestDashboardCLIStatusReporting:
    """Test CLI command accurately reports dashboard status."""

    def test_cli_reports_success_when_dashboard_starts(self):
        """CRITICAL: Verify CLI reports success when dashboard actually starts.

        This test detects the bug in v0.5.1 where CLI shows error even
        though dashboard starts successfully.
        """
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create minimal spec-kitty project structure
            (tmpdir / ".kittify").mkdir()
            kitty_specs = tmpdir / "kitty-specs"
            kitty_specs.mkdir()

            # Create a test feature
            feature_dir = kitty_specs / "001-test-feature"
            feature_dir.mkdir()
            (feature_dir / "spec.md").write_text("# Test Feature")
            (feature_dir / "plan.md").write_text("# Test Plan")

            # Initialize git (required for spec-kitty)
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            # Use a unique port for this test
            test_port = 9999

            # Clean up any existing dashboard on this port
            kill_dashboard_process(test_port)
            time.sleep(1)

            # Run dashboard command
            result = subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            # Give dashboard time to start
            time.sleep(2)

            # Check if dashboard is actually accessible
            dashboard_running = is_dashboard_accessible(test_port, timeout=3.0)

            try:
                if dashboard_running:
                    # BUG DETECTION: If dashboard is running, CLI should have reported success
                    assert result.returncode == 0, \
                        f"CLI should report success (exit 0) when dashboard starts, " \
                        f"got exit code {result.returncode}.\n" \
                        f"Dashboard IS accessible on port {test_port}.\n" \
                        f"CLI output: {result.stdout}\n" \
                        f"CLI stderr: {result.stderr}"

                    # Should show success message
                    output = result.stdout + result.stderr
                    assert "✅" in output or "success" in output.lower() or "running" in output.lower(), \
                        f"CLI should show success message when dashboard starts.\n" \
                        f"Dashboard IS accessible on port {test_port}.\n" \
                        f"Got: {output}"

                    # Should NOT show error message
                    assert "❌" not in output and "Unable to start" not in output, \
                        f"CLI should NOT show error when dashboard is running.\n" \
                        f"Dashboard IS accessible on port {test_port}.\n" \
                        f"Got: {output}"
                else:
                    # Dashboard not running - CLI should report error
                    assert result.returncode != 0, \
                        f"CLI should report error when dashboard doesn't start"

            finally:
                # Cleanup: Kill the dashboard
                kill_dashboard_process(test_port)

    def test_cli_reports_error_when_dashboard_fails(self):
        """Verify CLI reports error when dashboard genuinely fails to start."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create INVALID project structure (missing .kittify)
            # This should cause dashboard to fail

            # Try to start dashboard in non-spec-kitty project
            result = subprocess.run(
                ["spec-kitty", "dashboard"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            # Should report error
            assert result.returncode != 0, \
                "CLI should exit with error when project not initialized"

            output = result.stdout + result.stderr

            # Should show error message
            assert "❌" in output or "error" in output.lower() or "Unable" in output, \
                f"CLI should show error message when dashboard fails. Got: {output}"

    def test_dashboard_accessibility_matches_cli_status(self):
        """Verify CLI status matches whether dashboard is actually accessible."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create valid project
            (tmpdir / ".kittify").mkdir()
            (tmpdir / "kitty-specs").mkdir()

            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            test_port = 9998
            kill_dashboard_process(test_port)
            time.sleep(1)

            # Run dashboard
            result = subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            time.sleep(2)

            # Check actual state
            is_accessible = is_dashboard_accessible(test_port, timeout=3.0)
            cli_reported_success = result.returncode == 0

            try:
                # This is the key assertion - they should match
                assert is_accessible == cli_reported_success, \
                    f"CLI status (exit {result.returncode}) should match dashboard accessibility ({is_accessible}).\n" \
                    f"Dashboard accessible: {is_accessible}\n" \
                    f"CLI reported success: {cli_reported_success}\n" \
                    f"CLI output: {result.stdout}\n" \
                    f"CLI stderr: {result.stderr}"
            finally:
                kill_dashboard_process(test_port)


class TestDashboardProcessLifecycle:
    """Test dashboard process management and lifecycle."""

    def test_dashboard_process_actually_starts(self):
        """Verify dashboard process is created and running."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / ".kittify").mkdir()
            (tmpdir / "kitty-specs").mkdir()

            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            test_port = 9997
            kill_dashboard_process(test_port)
            time.sleep(1)

            # Start dashboard
            subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            time.sleep(2)

            # Check if process exists
            ps_result = subprocess.run(
                ["lsof", "-ti", f":{test_port}"],
                capture_output=True,
                text=True
            )

            try:
                has_process = bool(ps_result.stdout.strip())

                assert has_process, \
                    f"Dashboard process should exist on port {test_port} after command runs"

                # Verify it's accessible
                assert is_dashboard_accessible(test_port), \
                    f"Dashboard should be accessible on port {test_port}"
            finally:
                kill_dashboard_process(test_port)

    def test_dashboard_kill_flag_works(self):
        """Verify --kill flag stops the dashboard."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / ".kittify").mkdir()
            (tmpdir / "kitty-specs").mkdir()

            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            test_port = 9996
            kill_dashboard_process(test_port)
            time.sleep(1)

            # Start dashboard
            subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            time.sleep(2)

            # Verify it's running
            if is_dashboard_accessible(test_port):
                # Kill it
                kill_result = subprocess.run(
                    ["spec-kitty", "dashboard", "--kill"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                time.sleep(1)

                # Should not be accessible anymore
                still_accessible = is_dashboard_accessible(test_port, timeout=1.0)
                assert not still_accessible, \
                    f"Dashboard should be stopped after --kill, but still accessible on {test_port}"

                # Kill command should report success
                output = kill_result.stdout + kill_result.stderr
                assert "✅" in output or "stopped" in output.lower() or "killed" in output.lower(), \
                    f"--kill should report success. Got: {output}"


class TestDashboardErrorMessages:
    """Test dashboard error message quality."""

    def test_error_message_helpful_when_not_initialized(self):
        """Verify helpful error when project not initialized."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Don't create .kittify (not initialized)

            result = subprocess.run(
                ["spec-kitty", "dashboard"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            # Should fail
            assert result.returncode != 0, "Should fail when project not initialized"

            output = result.stdout + result.stderr

            # Should mention init or project setup
            assert "init" in output.lower() or "project" in output.lower() or ".kittify" in output.lower(), \
                f"Error should suggest initialization or mention project. Got: {output}"

            # Should mention project or worktree
            assert "project" in output.lower() or "worktree" in output.lower(), \
                f"Error should mention project or worktree. Got: {output}"


class TestDashboardAPIVerification:
    """Test dashboard API endpoint verification."""

    def test_api_features_endpoint_returns_data(self):
        """Verify /api/features endpoint works when dashboard running."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create valid project with feature
            (tmpdir / ".kittify").mkdir()
            kitty_specs = tmpdir / "kitty-specs"
            kitty_specs.mkdir()

            feature_dir = kitty_specs / "001-test"
            feature_dir.mkdir()
            (feature_dir / "spec.md").write_text("# Test Spec")

            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            test_port = 9995
            kill_dashboard_process(test_port)
            time.sleep(1)

            # Start dashboard
            subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            time.sleep(2)

            try:
                # Test API endpoint
                if is_dashboard_accessible(test_port):
                    with urlopen(f"http://127.0.0.1:{test_port}/api/features", timeout=3.0) as response:
                        assert response.status == 200, \
                            "API should return 200 when dashboard running"

                        data = json.loads(response.read().decode())
                        assert "features" in data, \
                            f"API should return features list. Got: {data}"

                        # Should have features array
                        assert len(data["features"]) >= 0, \
                            "Should return features array (may be empty)"
            finally:
                kill_dashboard_process(test_port)

    def test_api_returns_valid_json(self):
        """Verify API returns valid JSON structure."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / ".kittify").mkdir()
            (tmpdir / "kitty-specs").mkdir()

            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            test_port = 9994
            kill_dashboard_process(test_port)
            time.sleep(1)

            subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            time.sleep(2)

            try:
                if is_dashboard_accessible(test_port):
                    with urlopen(f"http://127.0.0.1:{test_port}/api/features", timeout=3.0) as response:
                        data = json.loads(response.read().decode())

                        # Should have required fields
                        assert isinstance(data, dict), "Response should be dict"
                        assert "features" in data, "Should have features field"
                        assert isinstance(data["features"], list), "Features should be list"
            finally:
                kill_dashboard_process(test_port)


class TestDashboardRaceConditions:
    """Test for race conditions in dashboard startup."""

    def test_cli_waits_for_dashboard_to_start(self):
        """Verify CLI doesn't report error if dashboard takes time to start."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / ".kittify").mkdir()
            kitty_specs = tmpdir / "kitty-specs"
            kitty_specs.mkdir()

            # Create multiple features (slower startup)
            for i in range(1, 4):
                feature_dir = kitty_specs / f"00{i}-test"
                feature_dir.mkdir()
                (feature_dir / "spec.md").write_text(f"# Feature {i}")
                (feature_dir / "plan.md").write_text(f"# Plan {i}")

            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            test_port = 9993
            kill_dashboard_process(test_port)
            time.sleep(1)

            # Run dashboard
            result = subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=10  # Allow more time
            )

            # Wait for dashboard
            time.sleep(3)

            try:
                # Check if actually accessible
                is_accessible = is_dashboard_accessible(test_port, timeout=5.0)

                if is_accessible:
                    # Dashboard started - CLI should not have reported error
                    output = result.stdout + result.stderr

                    # This test will catch race conditions where dashboard starts
                    # but CLI reports error due to timing
                    assert result.returncode == 0 or "running" in output.lower(), \
                        f"CLI should indicate success if dashboard is accessible.\n" \
                        f"Dashboard IS running on port {test_port}.\n" \
                        f"CLI exit code: {result.returncode}\n" \
                        f"CLI output: {output}"
            finally:
                kill_dashboard_process(test_port)


class TestDashboardCleanup:
    """Test dashboard cleanup and process management."""

    def test_no_orphaned_processes_after_kill(self):
        """Verify --kill actually terminates dashboard process."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / ".kittify").mkdir()
            (tmpdir / "kitty-specs").mkdir()

            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            test_port = 9992
            kill_dashboard_process(test_port)
            time.sleep(1)

            # Start dashboard
            subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )

            time.sleep(2)

            # Get process ID
            ps_before = subprocess.run(
                ["lsof", "-ti", f":{test_port}"],
                capture_output=True,
                text=True
            )

            if ps_before.stdout.strip():
                # Kill dashboard
                subprocess.run(
                    ["spec-kitty", "dashboard", "--kill"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                time.sleep(2)

                # Check process is gone
                ps_after = subprocess.run(
                    ["lsof", "-ti", f":{test_port}"],
                    capture_output=True,
                    text=True
                )

                assert not ps_after.stdout.strip(), \
                    f"Dashboard process should be terminated after --kill.\n" \
                    f"Process still running: {ps_after.stdout}"

                # Verify not accessible
                assert not is_dashboard_accessible(test_port, timeout=1.0), \
                    "Dashboard should not be accessible after --kill"


# Module-level cleanup: Kill ALL orphaned dashboards before and after entire test module
@pytest.fixture(autouse=True, scope="module")
def cleanup_all_dashboards_module():
    """Cleanup all spec-kitty dashboard processes before and after test module."""
    # Before all tests: kill any existing orphaned dashboards
    kill_all_spec_kitty_dashboards()

    yield

    # After all tests: kill any remaining dashboards
    kill_all_spec_kitty_dashboards()


# Per-test cleanup: Kill dashboards on specific test ports
@pytest.fixture(autouse=True, scope="function")
def cleanup_test_dashboards():
    """Cleanup any test dashboard processes after each test."""
    yield

    # Cleanup test ports (expanded range to catch all test dashboards)
    # Includes both default port range (9237-9290) and explicit test ports (9992-9999)
    for port in range(9237, 10000):
        kill_dashboard_process(port)


def test_dashboard_with_symlinked_kitty_specs():
    """Test dashboard works with symlinked kitty-specs directory (worktree structure).

    This tests the scenario from the bug report where kitty-specs is a symlink
    to a worktree directory, which was causing false error reporting.
    """
    with TemporaryDirectory() as tmpdir:
        test_project = Path(tmpdir) / "test_project"
        test_project.mkdir()

        # Create .kittify directory (required by dashboard)
        kittify_dir = test_project / ".kittify"
        kittify_dir.mkdir()

        # Initialize git repo (required by dashboard)
        subprocess.run(["git", "init"], cwd=test_project, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=test_project,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=test_project,
            check=True,
            capture_output=True
        )

        # Create a worktree structure
        worktrees_dir = test_project / ".worktrees"
        worktrees_dir.mkdir()

        # Create worktree with kitty-specs
        worktree_feature = worktrees_dir / "001-test-feature"
        worktree_feature.mkdir()
        worktree_kitty_specs = worktree_feature / "kitty-specs"
        worktree_kitty_specs.mkdir()
        feature_dir = worktree_kitty_specs / "001-test-feature"
        feature_dir.mkdir()

        # Create spec.md and plan.md
        (feature_dir / "spec.md").write_text("# Test Feature\n\nA test feature.")
        (feature_dir / "plan.md").write_text("# Implementation Plan\n\n## Overview\nTest plan.")

        # Create symlink to worktree kitty-specs (this is the key test scenario)
        kitty_specs = test_project / "kitty-specs"
        kitty_specs.symlink_to(worktree_kitty_specs, target_is_directory=True)

        # Verify symlink structure
        assert kitty_specs.is_symlink(), "kitty-specs should be a symlink"
        assert (kitty_specs / "001-test-feature" / "spec.md").exists(), \
            "Should access spec.md through symlink"

        try:
            # Run dashboard command
            test_port = 9998
            result = subprocess.run(
                ["spec-kitty", "dashboard", "--port", str(test_port)],
                cwd=test_project,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Wait a bit for dashboard to fully start
            time.sleep(2)

            # Dashboard should start successfully
            if is_dashboard_accessible(test_port):
                assert result.returncode == 0, \
                    f"CLI should report success when dashboard accessible.\n" \
                    f"Exit code: {result.returncode}\n" \
                    f"Stdout: {result.stdout}\n" \
                    f"Stderr: {result.stderr}"

                assert "✅" in result.stdout or "started" in result.stdout.lower(), \
                    f"CLI should show success message when dashboard running.\n" \
                    f"Stdout: {result.stdout}"
            else:
                # If dashboard not accessible, error is acceptable
                assert result.returncode != 0, \
                    "CLI should report error when dashboard not accessible"

        finally:
            # Cleanup
            kill_dashboard_process(test_port)
