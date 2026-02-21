"""Integration tests for ExecutionEvent emission during task lane transitions.

This test suite verifies that moving tasks through lanes (via move-task command)
properly emits ExecutionEvents to the telemetry system for cost tracking.

Bug context: ExecutionEvents were only emitted when using the orchestrator,
not when using manual task lane transitions (spec-kitty agent tasks move-task).
This meant human-in-the-loop workflows had no cost tracking.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.telemetry.query import query_execution_events

runner = CliRunner()


@pytest.fixture
def project_with_feature(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal project with a feature and work package."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .kittify marker
    (repo_root / ".kittify").mkdir()

    # Initialize git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=repo_root, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )

    # Create feature directory
    feature_slug = "999-telemetry-test"
    feature_dir = repo_root / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create meta.json
    meta_json = feature_dir / "meta.json"
    meta_json.write_text(
        json.dumps(
            {
                "feature_slug": feature_slug,
                "title": "Telemetry Test Feature",
                "target_branch": "main",
                "created_at": "2026-02-16T00:00:00+00:00",
            }
        )
    )

    # Create task file
    task_file = tasks_dir / "WP01-test-implementation.md"
    task_content = """---
work_package_id: "WP01"
title: "Test Implementation"
lane: "planned"
agent: ""
shell_pid: ""
dependencies: []
---

# Work Package: WP01 - Test Implementation

Test content here.

## Subtasks
- [x] T001 Implement feature

## Activity Log

- 2026-02-16T00:00:00Z – system – lane=planned – Initial creation
"""
    task_file.write_text(task_content)

    # Commit initial state
    subprocess.run(["git", "add", "."], cwd=repo_root, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )

    return repo_root, feature_dir


def _invoke_move_task(
    repo_root: Path,
    args: list[str],
) -> object:
    """Invoke move-task command with mocked repo root."""
    with patch(
        "specify_cli.cli.commands.agent.tasks.locate_project_root",
        return_value=repo_root,
    ):
        with patch(
            "specify_cli.cli.commands.agent.tasks._find_feature_slug",
            return_value="999-telemetry-test",
        ):
            with patch(
                "specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out",
                return_value=(repo_root, "main"),
            ):
                return runner.invoke(app, args)


class TestExecutionEventEmissionOnLaneTransition:
    """Test that ExecutionEvents are emitted when moving tasks through lanes."""

    def test_move_to_for_review_emits_execution_event(self, project_with_feature: tuple[Path, Path]) -> None:
        """Moving a task to for_review should emit an ExecutionEvent for implementation.

        This test documents the BUG: ExecutionEvents are NOT currently emitted.
        After the fix, this test should pass.
        """
        repo_root, feature_dir = project_with_feature

        # Move from planned -> in_progress (no ExecutionEvent expected yet)
        result = _invoke_move_task(
            repo_root,
            [
                "move-task",
                "WP01",
                "--to",
                "in_progress",
                "--agent",
                "claude",
                "--no-auto-commit",
                "--force",
            ],
        )
        assert result.exit_code == 0, (
            f"Exit code: {result.exit_code}\nstdout: {result.stdout}\nstderr: {getattr(result, 'stderr', 'N/A')}"
        )

        # Move from in_progress -> for_review (ExecutionEvent SHOULD be emitted)
        result = _invoke_move_task(
            repo_root,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--agent",
                "claude",
                "--no-auto-commit",
                "--force",
            ],
        )
        assert result.exit_code == 0, (
            f"Exit code: {result.exit_code}\nstdout: {result.stdout}\nstderr: {getattr(result, 'stderr', 'N/A')}"
        )

        # Query ExecutionEvents from the feature directory
        events = list(query_execution_events(feature_dir))

        # BUG VERIFICATION: This assertion SHOULD FAIL with current code
        # Expected: At least 1 ExecutionEvent for the implementation work
        # Actual: 0 ExecutionEvents (none emitted)
        assert len(events) >= 1, (
            f"BUG CONFIRMED: Expected at least 1 ExecutionEvent after moving to for_review, "
            f"but found {len(events)}. ExecutionEvents are not being emitted by move-task command."
        )

    def test_move_to_done_emits_execution_event(self, project_with_feature: tuple[Path, Path]) -> None:
        """Moving a task to done should emit an ExecutionEvent for review."""
        repo_root, feature_dir = project_with_feature

        # Setup: Move to for_review first
        _invoke_move_task(
            repo_root,
            [
                "move-task",
                "WP01",
                "--to",
                "in_progress",
                "--agent",
                "claude",
                "--no-auto-commit",
                "--force",
            ],
        )
        _invoke_move_task(
            repo_root,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--agent",
                "claude",
                "--no-auto-commit",
                "--force",
            ],
        )

        # Move from for_review -> done (ExecutionEvent SHOULD be emitted for review)
        result = _invoke_move_task(
            repo_root,
            [
                "move-task",
                "WP01",
                "--to",
                "done",
                "--agent",
                "codex",
                "--model",
                "gpt-4.1",
                "--reviewer",
                "Test Reviewer",
                "--no-auto-commit",
                "--force",
            ],
        )
        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Query ExecutionEvents
        events = query_execution_events(feature_dir)

        # BUG: This assertion currently FAILS
        # Expected: 2 ExecutionEvents (1 for implementation, 1 for review)
        # Actual: 0 ExecutionEvents
        assert len(events) >= 2, f"Expected at least 2 ExecutionEvents after moving to done, but found {len(events)}"

        # Verify review event structure
        review_event = [e for e in events if e.payload.get("role") == "reviewer"]
        assert len(review_event) >= 1, "Expected at least 1 review ExecutionEvent"
        assert review_event[0].payload["wp_id"] == "WP01"
        assert review_event[0].payload["agent"] == "codex"
        assert review_event[0].payload["model"] == "gpt-4.1"

    def test_execution_event_cost_tracking(self, project_with_feature: tuple[Path, Path]) -> None:
        """ExecutionEvents should include cost tracking data when provided."""
        repo_root, feature_dir = project_with_feature

        # Move to for_review with cost data
        result = _invoke_move_task(
            repo_root,
            [
                "move-task",
                "WP01",
                "--to",
                "in_progress",
                "--agent",
                "claude",
                "--no-auto-commit",
                "--force",
            ],
        )
        result = _invoke_move_task(
            repo_root,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--agent",
                "claude",
                "--model",
                "claude-sonnet-4.5",
                "--input-tokens",
                "5000",
                "--output-tokens",
                "2000",
                "--cost-usd",
                "0.0425",
                "--duration-ms",
                "12500",
                "--no-auto-commit",
                "--force",
            ],
        )
        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Query ExecutionEvents
        events = query_execution_events(feature_dir)

        # BUG: This assertion currently FAILS
        assert len(events) >= 1, "Expected ExecutionEvent with cost data"

        event = events[0]
        assert event.payload.get("input_tokens") == 5000
        assert event.payload.get("output_tokens") == 2000
        assert event.payload.get("cost_usd") == 0.0425
        assert event.payload.get("duration_ms") == 12500
