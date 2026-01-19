"""Tests for orchestrator integration module.

Tests T043-T046 implementation:
- T043: Main orchestration loop
- T044: Progress display
- T045: Summary report
- T046: Edge case handling
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from specify_cli.orchestrator.config import (
    AgentConfig,
    OrchestrationStatus,
    OrchestratorConfig,
    WPStatus,
)
from specify_cli.orchestrator.integration import (
    CircularDependencyError,
    NoAgentsError,
    ValidationError,
    create_live_display,
    create_progress_panel,
    create_status_table,
    validate_agents,
    validate_feature,
)
from specify_cli.orchestrator.state import OrchestrationRun, WPExecution


# =============================================================================
# T046: Edge Case Tests - Validation
# =============================================================================


class TestValidateFeature:
    """Tests for validate_feature edge case handling."""

    def test_missing_feature_directory(self) -> None:
        """Should raise ValidationError for non-existent directory."""
        with pytest.raises(ValidationError, match="Feature directory not found"):
            validate_feature(Path("/nonexistent/path"))

    def test_missing_tasks_directory(self, tmp_path: Path) -> None:
        """Should raise ValidationError when tasks/ doesn't exist."""
        feature_dir = tmp_path / "test-feature"
        feature_dir.mkdir()

        with pytest.raises(ValidationError, match="No tasks directory found"):
            validate_feature(feature_dir)

    def test_empty_tasks_directory(self, tmp_path: Path) -> None:
        """Should raise ValidationError when no WPs found."""
        feature_dir = tmp_path / "test-feature"
        feature_dir.mkdir()
        (feature_dir / "tasks").mkdir()

        with pytest.raises(ValidationError, match="No work packages found"):
            validate_feature(feature_dir)


class TestValidateAgents:
    """Tests for validate_agents edge case handling."""

    def test_no_agents_enabled(self) -> None:
        """Should raise NoAgentsError when all agents disabled."""
        config = OrchestratorConfig(
            agents={
                "claude-code": AgentConfig(agent_id="claude-code", enabled=False),
                "codex": AgentConfig(agent_id="codex", enabled=False),
            },
            defaults={"implementation": [], "review": []},
        )

        with pytest.raises(NoAgentsError, match="No agents available"):
            validate_agents(config)

    def test_no_agents_configured(self) -> None:
        """Should raise NoAgentsError when agents dict is empty."""
        config = OrchestratorConfig(
            agents={},
            defaults={"implementation": [], "review": []},
        )

        with pytest.raises(NoAgentsError, match="No agents available"):
            validate_agents(config)


# =============================================================================
# T044: Progress Display Tests
# =============================================================================


class TestProgressDisplay:
    """Tests for progress display functions."""

    @pytest.fixture
    def mock_state(self) -> OrchestrationRun:
        """Create a mock orchestration state for testing."""
        return OrchestrationRun(
            run_id="test-run",
            feature_slug="test-feature",
            started_at=datetime.now(timezone.utc),
            status=OrchestrationStatus.RUNNING,
            wps_total=4,
            wps_completed=1,
            wps_failed=0,
            work_packages={
                "WP01": WPExecution(wp_id="WP01", status=WPStatus.COMPLETED),
                "WP02": WPExecution(wp_id="WP02", status=WPStatus.IMPLEMENTATION),
                "WP03": WPExecution(wp_id="WP03", status=WPStatus.REVIEW),
                "WP04": WPExecution(wp_id="WP04", status=WPStatus.PENDING),
            },
        )

    def test_create_status_table(self, mock_state: OrchestrationRun) -> None:
        """Should create a Rich Table with WP status."""
        table = create_status_table(mock_state)

        assert table is not None
        assert table.title is not None
        assert "test-feature" in str(table.title)
        assert table.row_count == 4

    def test_create_progress_panel(self, mock_state: OrchestrationRun) -> None:
        """Should create a Rich Panel with progress info."""
        panel = create_progress_panel(mock_state)

        assert panel is not None
        assert panel.border_style == "blue"

    def test_create_live_display(self, mock_state: OrchestrationRun) -> None:
        """Should create combined live display."""
        display = create_live_display(mock_state)

        assert display is not None
        # The display should have caption with progress
        assert display.caption is not None


# =============================================================================
# T045: Summary Report Tests
# =============================================================================


class TestSummaryReport:
    """Tests for summary report function."""

    @pytest.fixture
    def completed_state(self) -> OrchestrationRun:
        """Create a completed orchestration state."""
        state = OrchestrationRun(
            run_id="test-run",
            feature_slug="test-feature",
            started_at=datetime.now(timezone.utc),
            status=OrchestrationStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            wps_total=3,
            wps_completed=3,
            wps_failed=0,
            parallel_peak=2,
            total_agent_invocations=6,
            work_packages={
                "WP01": WPExecution(
                    wp_id="WP01",
                    status=WPStatus.COMPLETED,
                    implementation_agent="claude-code",
                    review_agent="codex",
                ),
                "WP02": WPExecution(
                    wp_id="WP02",
                    status=WPStatus.COMPLETED,
                    implementation_agent="claude-code",
                    review_agent="codex",
                ),
                "WP03": WPExecution(
                    wp_id="WP03",
                    status=WPStatus.COMPLETED,
                    implementation_agent="claude-code",
                    review_agent="claude-code",
                ),
            },
        )
        return state

    def test_print_summary_imports(self) -> None:
        """Should be able to import print_summary."""
        from specify_cli.orchestrator.integration import print_summary

        assert callable(print_summary)

    def test_print_summary_no_error(
        self, completed_state: OrchestrationRun, capsys
    ) -> None:
        """Should print summary without errors."""
        from rich.console import Console

        from specify_cli.orchestrator.integration import print_summary

        console = Console(force_terminal=True, width=80)
        print_summary(completed_state, console)

        # Should not raise any exceptions
        # Output is to Rich console, not captured by capsys


# =============================================================================
# T043: Main Loop Integration Tests (Minimal)
# =============================================================================


class TestOrchestrationLoop:
    """Tests for main orchestration loop."""

    def test_run_orchestration_loop_import(self) -> None:
        """Should be able to import run_orchestration_loop."""
        from specify_cli.orchestrator.integration import run_orchestration_loop

        assert callable(run_orchestration_loop)

    def test_process_wp_import(self) -> None:
        """Should be able to import process_wp."""
        from specify_cli.orchestrator.integration import process_wp

        assert callable(process_wp)
