"""Integration tests verifying telemetry emission hooks in the orchestrator.

These tests mock heavily to isolate the emission call-site from the full
orchestrator machinery.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from specify_cli.orchestrator.agents.base import InvocationResult


# ── Helpers ────────────────────────────────────────────────────────────


def _make_result(**overrides) -> InvocationResult:
    """Build an InvocationResult with sensible defaults."""
    defaults = dict(
        success=True,
        exit_code=0,
        stdout="ok",
        stderr="",
        duration_seconds=1.5,
        files_modified=[],
        commits_made=[],
        errors=[],
        warnings=[],
        model="claude-sonnet-4",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.01,
    )
    defaults.update(overrides)
    return InvocationResult(**defaults)


# ── T018: Integration tests ───────────────────────────────────────────


def test_implementation_emits_event(tmp_path: Path) -> None:
    """process_wp_implementation fires emit_execution_event after execution."""
    feature_dir = tmp_path / "kitty-specs" / "043-feat"
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01-setup.md").write_text("implement this")

    result = _make_result()

    with (
        patch(
            "specify_cli.orchestrator.integration.transition_wp_lane",
            new_callable=AsyncMock,
        ),
        patch("specify_cli.orchestrator.integration.save_state"),
        patch("specify_cli.orchestrator.integration.get_worktree_path", return_value=tmp_path),
        patch("specify_cli.orchestrator.integration.get_invoker", return_value=MagicMock()),
        patch("specify_cli.orchestrator.integration.get_log_path", return_value=tmp_path / "log.txt"),
        patch(
            "specify_cli.orchestrator.integration.execute_with_retry",
            new_callable=AsyncMock,
            return_value=result,
        ),
        patch("specify_cli.orchestrator.integration.update_wp_progress"),
        patch("specify_cli.orchestrator.integration.is_success", return_value=True),
        patch("specify_cli.orchestrator.integration.emit_wp_assigned"),
        patch("specify_cli.orchestrator.integration.build_dependency_graph", return_value={}),
        patch(
            "specify_cli.telemetry.emit.emit_execution_event"
        ) as mock_emit,
    ):
        from specify_cli.orchestrator.integration import process_wp_implementation
        from specify_cli.orchestrator.state import OrchestrationRun, WPExecution

        state = MagicMock(spec=OrchestrationRun)
        wp = MagicMock(spec=WPExecution)
        wp.implementation_retries = 0
        wp.fallback_agents_tried = []
        wp.review_feedback = None
        state.work_packages = {"WP01": wp}

        config = MagicMock()
        config.global_timeout = 300

        asyncio.run(
            process_wp_implementation(
                wp_id="WP01",
                state=state,
                config=config,
                feature_dir=feature_dir,
                repo_root=tmp_path,
                agent_id="claude",
                console=MagicMock(),
            )
        )

        mock_emit.assert_called_once()
        call_kwargs = mock_emit.call_args
        # Verify key arguments
        assert call_kwargs.kwargs.get("role") == "implementer" or (
            len(call_kwargs.args) >= 5 and call_kwargs.args[4] == "implementer"
        )


def test_review_emits_event(tmp_path: Path) -> None:
    """process_wp_review fires emit_execution_event with role='reviewer'."""
    feature_dir = tmp_path / "kitty-specs" / "043-feat"
    feature_dir.mkdir(parents=True)

    result = _make_result()

    with (
        patch(
            "specify_cli.orchestrator.integration.transition_wp_lane",
            new_callable=AsyncMock,
        ),
        patch("specify_cli.orchestrator.integration.save_state"),
        patch("specify_cli.orchestrator.integration.get_worktree_path", return_value=tmp_path),
        patch("specify_cli.orchestrator.integration.get_invoker", return_value=MagicMock()),
        patch("specify_cli.orchestrator.integration.get_log_path", return_value=tmp_path / "log.txt"),
        patch(
            "specify_cli.orchestrator.integration.execute_with_retry",
            new_callable=AsyncMock,
            return_value=result,
        ),
        patch("specify_cli.orchestrator.integration.update_wp_progress"),
        patch("specify_cli.orchestrator.integration.parse_review_outcome", return_value=MagicMock(outcome="approved")),
        patch("specify_cli.orchestrator.integration.emit_wp_assigned"),
        patch(
            "specify_cli.telemetry.emit.emit_execution_event"
        ) as mock_emit,
    ):
        from specify_cli.orchestrator.integration import process_wp_review
        from specify_cli.orchestrator.state import OrchestrationRun, WPExecution

        state = MagicMock(spec=OrchestrationRun)
        wp = MagicMock(spec=WPExecution)
        wp.review_retries = 0
        state.work_packages = {"WP01": wp}

        config = MagicMock()
        config.global_timeout = 300

        asyncio.run(
            process_wp_review(
                wp_id="WP01",
                state=state,
                config=config,
                feature_dir=feature_dir,
                repo_root=tmp_path,
                agent_id="claude",
                console=MagicMock(),
            )
        )

        mock_emit.assert_called_once()
        call_kwargs = mock_emit.call_args
        assert call_kwargs.kwargs.get("role") == "reviewer" or (
            len(call_kwargs.args) >= 5 and call_kwargs.args[4] == "reviewer"
        )


def test_emission_failure_does_not_block(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """If emit_execution_event raises, process_wp_implementation still succeeds."""
    feature_dir = tmp_path / "kitty-specs" / "043-feat"
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01-setup.md").write_text("implement this")

    result = _make_result()

    with (
        patch(
            "specify_cli.orchestrator.integration.transition_wp_lane",
            new_callable=AsyncMock,
        ),
        patch("specify_cli.orchestrator.integration.save_state"),
        patch("specify_cli.orchestrator.integration.get_worktree_path", return_value=tmp_path),
        patch("specify_cli.orchestrator.integration.get_invoker", return_value=MagicMock()),
        patch("specify_cli.orchestrator.integration.get_log_path", return_value=tmp_path / "log.txt"),
        patch(
            "specify_cli.orchestrator.integration.execute_with_retry",
            new_callable=AsyncMock,
            return_value=result,
        ),
        patch("specify_cli.orchestrator.integration.update_wp_progress"),
        patch("specify_cli.orchestrator.integration.is_success", return_value=True),
        patch("specify_cli.orchestrator.integration.emit_wp_assigned"),
        patch("specify_cli.orchestrator.integration.build_dependency_graph", return_value={}),
        patch(
            "specify_cli.telemetry.emit.emit_execution_event",
            side_effect=RuntimeError("boom"),
        ),
    ):
        from specify_cli.orchestrator.integration import process_wp_implementation
        from specify_cli.orchestrator.state import OrchestrationRun, WPExecution

        state = MagicMock(spec=OrchestrationRun)
        wp = MagicMock(spec=WPExecution)
        wp.implementation_retries = 0
        wp.fallback_agents_tried = []
        wp.review_feedback = None
        state.work_packages = {"WP01": wp}

        config = MagicMock()
        config.global_timeout = 300

        with caplog.at_level(logging.WARNING):
            ok = asyncio.run(
                process_wp_implementation(
                    wp_id="WP01",
                    state=state,
                    config=config,
                    feature_dir=feature_dir,
                    repo_root=tmp_path,
                    agent_id="claude",
                    console=MagicMock(),
                )
            )

        # Implementation should still succeed
        assert ok is True
        assert any("Telemetry emission failed" in r.message for r in caplog.records)


def test_missing_telemetry_fields() -> None:
    """InvocationResult telemetry fields default to None."""
    result = InvocationResult(
        success=True,
        exit_code=0,
        stdout="",
        stderr="",
        duration_seconds=1.0,
    )
    assert result.model is None
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.cost_usd is None
