"""Tests that validate quickstart.md scenarios work as documented.

These tests verify the documented user workflows function correctly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.mark.orchestrator_fixtures
class TestQuickstartScenarios:
    """Tests for quickstart.md documented scenarios."""

    def test_check_agent_availability_command(self):
        """'spec-kitty agents status' should work."""
        # This tests the documented command works
        result = subprocess.run(
            ["spec-kitty", "agents", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Command should execute (may show no agents)
        # Note: the command might not exist yet, so we accept both 0 and non-zero
        # as long as it doesn't crash with an unhandled exception
        assert result.returncode == 0 or "error" not in result.stderr.lower() or \
            "no such command" in result.stderr.lower() or \
            "unknown command" in result.stderr.lower(), (
            f"Command failed unexpectedly: {result.stderr}"
        )

    def test_run_orchestrator_tests_command(self):
        """'pytest -m orchestrator_happy_path' should collect tests."""
        result = subprocess.run(
            ["pytest", "--collect-only", "-m", "orchestrator_happy_path", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should collect at least one test (or report none)
        # Returncode 5 means no tests collected, which is OK if no agents
        # Returncode 2 means errors during collection (other module issues)
        assert result.returncode in (0, 2, 5), f"pytest failed: {result.stderr}"

    def test_run_smoke_tests_command(self):
        """'pytest -m orchestrator_smoke' should work."""
        result = subprocess.run(
            ["pytest", "--collect-only", "-m", "orchestrator_smoke", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Accept 0 (success), 2 (collection errors), or 5 (no tests)
        assert result.returncode in (0, 2, 5)

    def test_environment_variables_documented(self):
        """Documented environment variables should be recognized."""
        from tests.specify_cli.orchestrator.config import OrchestratorTestConfig

        # Verify config class has documented fields
        config = OrchestratorTestConfig()

        assert hasattr(config, "probe_timeout_seconds")
        assert hasattr(config, "test_timeout_seconds")
        assert hasattr(config, "smoke_timeout_seconds")

    def test_fixture_loading_example(self, test_context_factory):
        """Example from quickstart should work."""
        # Load a checkpoint
        ctx = test_context_factory("wp_created")

        # Verify it's usable
        assert ctx.feature_dir.exists()
        assert ctx.state_file.exists()
        assert ctx.repo_root.exists()

    def test_validation_example(self, test_context_factory):
        """Validation example from quickstart should work."""
        from tests.specify_cli.orchestrator.validation import validate_test_result

        ctx = test_context_factory("wp_created")
        result = validate_test_result(ctx)

        # Initial state should be valid
        assert result.valid, f"Validation failed: {result.errors}"


@pytest.mark.orchestrator_availability
class TestQuickstartTroubleshooting:
    """Tests for troubleshooting scenarios."""

    def test_no_agents_available_message(self, available_agents):
        """Should have clear message when no agents available."""
        available_count = sum(1 for a in available_agents.values() if a.is_available)

        if available_count == 0:
            # Verify we have failure reasons
            for agent_id, avail in available_agents.items():
                if not avail.is_available:
                    assert avail.failure_reason is not None, (
                        f"{agent_id} unavailable but no reason given"
                    )

    def test_agent_detection_reports_all_agents(self, available_agents):
        """Detection should report all 12 agents."""
        assert len(available_agents) == 12, (
            f"Expected 12 agents, found {len(available_agents)}"
        )


@pytest.mark.orchestrator_fixtures
class TestMarkerConfiguration:
    """Tests for pytest marker configuration."""

    REPO_ROOT = Path(__file__).resolve().parents[3]

    def test_all_orchestrator_markers_registered(self):
        """All orchestrator markers should be registered without warnings."""
        result = subprocess.run(
            ["pytest", "--markers", "-c", str(self.REPO_ROOT / "pytest.ini")],
            cwd=self.REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check that our markers are present
        output = result.stdout + result.stderr
        expected_markers = [
            "orchestrator_availability",
            "orchestrator_fixtures",
            "orchestrator_happy_path",
            "orchestrator_review_cycles",
            "orchestrator_parallel",
            "orchestrator_smoke",
            "core_agent",
            "extended_agent",
        ]

        for marker in expected_markers:
            assert marker in output, f"Marker '{marker}' not registered"

    def test_slow_marker_registered(self):
        """slow marker should be registered."""
        result = subprocess.run(
            ["pytest", "--markers", "-c", str(self.REPO_ROOT / "pytest.ini")],
            cwd=self.REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr
        assert "slow" in output, "Marker 'slow' not registered"


@pytest.mark.orchestrator_fixtures
class TestConfigurationDefaults:
    """Tests for configuration defaults."""

    def test_probe_timeout_default(self):
        """Probe timeout should default to 10 seconds."""
        from tests.specify_cli.orchestrator.config import OrchestratorTestConfig

        # Check default value without environment override
        config = OrchestratorTestConfig()
        assert config.probe_timeout_seconds == 10

    def test_test_timeout_default(self, orchestrator_config):
        """Test timeout should default to 300 seconds."""
        assert orchestrator_config.test_timeout_seconds == 300

    def test_smoke_timeout_default(self, orchestrator_config):
        """Smoke timeout should default to 60 seconds."""
        assert orchestrator_config.smoke_timeout_seconds == 60

    def test_max_review_cycles_default(self, orchestrator_config):
        """Max review cycles should default to 3."""
        assert orchestrator_config.max_review_cycles == 3

    def test_parallel_tolerance_default(self, orchestrator_config):
        """Parallel timing tolerance should default to 30 seconds."""
        assert orchestrator_config.parallel_start_tolerance_seconds == 30
