"""Integration tests for task workflow commands.

These tests verify end-to-end task workflow operations with real file system.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app

runner = CliRunner()


def _parse_json_output(stdout: str) -> dict:
    """Extract and parse JSON from CLI output that may have prefix lines."""
    for line in stdout.strip().split('\n'):
        line = line.strip()
        if line.startswith('{'):
            return json.loads(line)
    raise ValueError(f"No JSON found in output: {stdout!r}")


@pytest.fixture
def task_repo(tmp_path: Path) -> Path:
    """Create a temporary repository with task structure."""
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create .kittify marker
    (repo / ".kittify").mkdir()

    # Create feature structure
    feature_dir = repo / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create initial task file
    task_file = tasks_dir / "WP01-test-task.md"
    task_file.write_text("""---
work_package_id: "WP01"
title: "Test Task"
lane: "planned"
subtasks: ["T001", "T002"]
phase: "Phase 1"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
---

# Work Package: WP01 - Test Task

Test implementation content.

## Activity Log

- 2025-01-01T00:00:00Z – system – lane=planned – Initial creation
""")

    # Create spec.md
    (feature_dir / "spec.md").write_text("# Spec")

    # Git commit
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


class TestFullWorkflow:
    """Integration tests for complete task workflow."""

    def test_full_lane_progression(self, task_repo: Path, monkeypatch):
        """Should support full workflow: planned → doing → for_review → done."""
        monkeypatch.chdir(task_repo)

        # Start in planned
        result1 = runner.invoke(
            app, ["list-tasks", "--lane", "planned", "--feature", "001-test-feature", "--json"]
        )
        assert result1.exit_code == 0
        output1 = _parse_json_output(result1.stdout)
        assert output1["count"] == 1

        # Move to doing (resolves to in_progress in canonical model)
        result2 = runner.invoke(
            app, [
                "move-task", "WP01", "--to", "doing",
                "--feature", "001-test-feature",
                "--agent", "test-agent",
                "--shell-pid", "12345",
                "--json"
            ]
        )
        assert result2.exit_code == 0, f"stdout: {result2.stdout}"
        output2 = _parse_json_output(result2.stdout)
        assert output2["old_lane"] == "planned"
        assert output2["new_lane"] == "in_progress"

        # Verify moved to in_progress
        result3 = runner.invoke(
            app, ["list-tasks", "--lane", "in_progress", "--feature", "001-test-feature", "--json"]
        )
        assert result3.exit_code == 0
        output3 = _parse_json_output(result3.stdout)
        assert output3["count"] == 1
        assert output3["tasks"][0]["lane"] == "in_progress"

        # Move to for_review
        result4 = runner.invoke(
            app, [
                "move-task", "WP01", "--to", "for_review",
                "--feature", "001-test-feature",
                "--json"
            ]
        )
        assert result4.exit_code == 0, f"stdout: {result4.stdout}"
        output4 = _parse_json_output(result4.stdout)
        assert output4["new_lane"] == "for_review"

        # Move to done
        result5 = runner.invoke(
            app, [
                "move-task", "WP01", "--to", "done",
                "--done-override-reason", "Integration test finalization without merge step",
                "--feature", "001-test-feature",
                "--json"
            ]
        )
        assert result5.exit_code == 0, f"stdout: {result5.stdout}"
        output5 = _parse_json_output(result5.stdout)
        assert output5["new_lane"] == "done"

        # Verify final state
        result6 = runner.invoke(
            app, ["list-tasks", "--lane", "done", "--feature", "001-test-feature", "--json"]
        )
        assert result6.exit_code == 0
        output6 = _parse_json_output(result6.stdout)
        assert output6["count"] == 1

    def test_workflow_with_history_tracking(self, task_repo: Path, monkeypatch):
        """Should track history through lane transitions."""
        monkeypatch.chdir(task_repo)

        # Move task through workflow
        runner.invoke(
            app, [
                "move-task", "WP01", "--to", "doing",
                "--feature", "001-test-feature",
                "--agent", "agent-1",
                "--note", "Starting work"
            ]
        )

        # Add custom history entry
        runner.invoke(
            app, [
                "add-history", "WP01",
                "--feature", "001-test-feature",
                "--note", "Completed implementation",
                "--agent", "agent-1"
            ]
        )

        # Move to for_review
        runner.invoke(
            app, [
                "move-task", "WP01", "--to", "for_review",
                "--feature", "001-test-feature",
                "--note", "Ready for review"
            ]
        )

        # Read task file and verify history
        task_file = task_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test-task.md"
        content = task_file.read_text()

        # Should have multiple history entries
        assert "Starting work" in content
        assert "Completed implementation" in content
        assert "Ready for review" in content
        assert "agent-1" in content

    def test_validation_workflow(self, task_repo: Path, monkeypatch):
        """Should validate tasks at different workflow stages."""
        monkeypatch.chdir(task_repo)

        # Validate initial state
        result1 = runner.invoke(
            app, ["validate-workflow", "WP01", "--feature", "001-test-feature", "--json"]
        )
        assert result1.exit_code == 0
        output1 = json.loads(result1.stdout)
        assert output1["valid"] is True

        # Move to doing
        runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature"]
        )

        # Validate after move
        result2 = runner.invoke(
            app, ["validate-workflow", "WP01", "--feature", "001-test-feature", "--json"]
        )
        assert result2.exit_code == 0
        output2 = _parse_json_output(result2.stdout)
        assert output2["valid"] is True
        assert output2["lane"] == "in_progress"

    def test_reject_planned_rollback_without_feedback_file(self, task_repo: Path, monkeypatch):
        """Should strictly require review feedback file when moving back to planned."""
        monkeypatch.chdir(task_repo)

        # planned -> doing -> for_review
        result1 = runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature", "--json"]
        )
        assert result1.exit_code == 0
        result2 = runner.invoke(
            app, ["move-task", "WP01", "--to", "for_review", "--feature", "001-test-feature", "--json"]
        )
        assert result2.exit_code == 0

        # for_review -> planned must include --review-feedback-file
        result3 = runner.invoke(
            app, ["move-task", "WP01", "--to", "planned", "--feature", "001-test-feature", "--json"]
        )
        assert result3.exit_code == 1
        output3 = _parse_json_output(result3.stdout)
        assert "requires review feedback" in output3["error"]

    def test_reject_planned_rollback_with_force_without_feedback_file(self, task_repo: Path, monkeypatch):
        """--force must not bypass review feedback file requirement for planned rollbacks."""
        monkeypatch.chdir(task_repo)

        # planned -> doing -> for_review
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "for_review", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0

        # for_review -> planned with --force still requires --review-feedback-file
        result = runner.invoke(
            app,
            ["move-task", "WP01", "--to", "planned", "--feature", "001-test-feature", "--force", "--json"],
        )
        assert result.exit_code == 1
        output = _parse_json_output(result.stdout)
        assert "requires review feedback" in output["error"]

    def test_persist_feedback_content_and_feedback_file_path(self, task_repo: Path, monkeypatch):
        """Should persist feedback text and source file path deterministically."""
        monkeypatch.chdir(task_repo)

        # planned -> doing -> for_review
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "for_review", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0

        # Simulate `workflow review` claiming review (lane becomes doing/in_progress in frontmatter).
        task_file = task_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test-task.md"
        task_file.write_text(
            task_file.read_text(encoding="utf-8").replace('lane: "for_review"', 'lane: "in_progress"'),
            encoding="utf-8",
        )

        feedback_file = task_repo / "feedback.md"
        feedback_file.write_text("**Issue 1**: deterministic feedback persistence\n", encoding="utf-8")
        resolved_feedback = str(feedback_file.resolve())

        result = runner.invoke(
            app,
            [
                "move-task", "WP01", "--to", "planned",
                "--feature", "001-test-feature",
                "--review-feedback-file", str(feedback_file),
                "--json",
            ],
        )
        assert result.exit_code == 0, f"stdout: {result.stdout}"
        output = _parse_json_output(result.stdout)
        assert output["new_lane"] == "planned"

        content = task_file.read_text(encoding="utf-8")
        assert "## Review Feedback" in content
        assert "**Issue 1**: deterministic feedback persistence" in content
        assert f"**Feedback file**: `{resolved_feedback}`" in content
        assert f'review_feedback_file: "{resolved_feedback}"' in content


class TestReviewRejectToPlanned:
    """Integration tests for the for_review -> planned reject flow (issue #223).

    Verifies that the exact reject command shown in review templates works
    end-to-end: spec-kitty agent tasks move-task WP## --to planned --review-feedback-file <file>
    """

    def test_for_review_to_planned_with_feedback_file(self, task_repo: Path, monkeypatch):
        """Should allow for_review -> planned when review feedback file is provided."""
        monkeypatch.chdir(task_repo)

        # planned -> doing -> for_review
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "for_review", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0

        # Create review feedback file (simulates reviewer writing feedback)
        feedback_file = task_repo / "review-feedback.md"
        feedback_file.write_text(
            "## Review Feedback\n\n"
            "**Issue 1**: Missing error handling in edge case\n"
            "**Issue 2**: Test coverage insufficient for new path\n",
            encoding="utf-8",
        )

        # Execute the exact reject command from the review template
        result = runner.invoke(
            app,
            [
                "move-task", "WP01", "--to", "planned",
                "--feature", "001-test-feature",
                "--review-feedback-file", str(feedback_file),
                "--json",
            ],
        )
        assert result.exit_code == 0, f"stdout: {result.stdout}"
        output = _parse_json_output(result.stdout)
        assert output["new_lane"] == "planned"

    def test_for_review_to_planned_without_feedback_file_rejected(self, task_repo: Path, monkeypatch):
        """Should reject for_review -> planned when no feedback file is provided."""
        monkeypatch.chdir(task_repo)

        # planned -> doing -> for_review
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "for_review", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0

        # Attempt to move to planned without feedback file
        result = runner.invoke(
            app,
            ["move-task", "WP01", "--to", "planned", "--feature", "001-test-feature", "--json"],
        )
        assert result.exit_code == 1
        output = _parse_json_output(result.stdout)
        assert "requires review feedback" in output["error"]

    def test_for_review_to_planned_force_still_requires_feedback(self, task_repo: Path, monkeypatch):
        """--force must not bypass feedback file requirement for for_review -> planned."""
        monkeypatch.chdir(task_repo)

        # planned -> doing -> for_review
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "for_review", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0

        # --force without --review-feedback-file must still fail
        result = runner.invoke(
            app,
            ["move-task", "WP01", "--to", "planned", "--feature", "001-test-feature", "--force", "--json"],
        )
        assert result.exit_code == 1
        output = _parse_json_output(result.stdout)
        assert "requires review feedback" in output["error"]

    def test_for_review_to_planned_persists_feedback(self, task_repo: Path, monkeypatch):
        """Should persist review feedback content in the WP file body and frontmatter."""
        monkeypatch.chdir(task_repo)

        # planned -> doing -> for_review
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0
        assert runner.invoke(
            app, ["move-task", "WP01", "--to", "for_review", "--feature", "001-test-feature", "--json"]
        ).exit_code == 0

        # Create feedback file
        feedback_file = task_repo / "reject-feedback.md"
        feedback_file.write_text(
            "**Critical**: The implementation does not handle the null case.\n",
            encoding="utf-8",
        )
        resolved_path = str(feedback_file.resolve())

        # Move to planned with feedback
        result = runner.invoke(
            app,
            [
                "move-task", "WP01", "--to", "planned",
                "--feature", "001-test-feature",
                "--review-feedback-file", str(feedback_file),
                "--json",
            ],
        )
        assert result.exit_code == 0, f"stdout: {result.stdout}"

        # Verify feedback persisted in WP file
        task_file = task_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test-task.md"
        content = task_file.read_text(encoding="utf-8")
        assert "## Review Feedback" in content
        assert "does not handle the null case" in content
        assert f'review_feedback_file: "{resolved_path}"' in content


class TestLocationIndependence:
    """Tests for running commands from different locations."""

    def test_commands_from_main_repo(self, task_repo: Path, monkeypatch):
        """Should run commands successfully from main repository."""
        monkeypatch.chdir(task_repo)

        # List tasks
        result1 = runner.invoke(
            app, ["list-tasks", "--feature", "001-test-feature", "--json"]
        )
        assert result1.exit_code == 0

        # Move task
        result2 = runner.invoke(
            app, [
                "move-task", "WP01", "--to", "doing",
                "--feature", "001-test-feature",
                "--json"
            ]
        )
        assert result2.exit_code == 0

        # Validate
        result3 = runner.invoke(
            app, ["validate-workflow", "WP01", "--feature", "001-test-feature", "--json"]
        )
        assert result3.exit_code == 0

    def test_commands_from_worktree(self, task_repo: Path, monkeypatch):
        """Should run commands successfully from worktree."""
        # Create worktree
        worktree_path = task_repo / ".worktrees" / "001-test-feature"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "001-test-feature"],
            cwd=task_repo,
            check=True,
            capture_output=True,
        )

        # Change to worktree
        monkeypatch.chdir(worktree_path)

        # List tasks
        result1 = runner.invoke(
            app, ["list-tasks", "--feature", "001-test-feature", "--json"]
        )
        assert result1.exit_code == 0

        # Move task
        result2 = runner.invoke(
            app, [
                "move-task", "WP01", "--to", "doing",
                "--feature", "001-test-feature",
                "--json"
            ]
        )
        assert result2.exit_code == 0

        # Validate
        result3 = runner.invoke(
            app, [
                "validate-workflow", "WP01",
                "--feature", "001-test-feature",
                "--json"
            ]
        )
        assert result3.exit_code == 0

    def test_auto_detect_feature_from_worktree_branch(self, task_repo: Path, monkeypatch):
        """Should auto-detect feature slug from worktree branch name."""
        # Create worktree
        worktree_path = task_repo / ".worktrees" / "001-test-feature"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "001-test-feature"],
            cwd=task_repo,
            check=True,
            capture_output=True,
        )

        monkeypatch.chdir(worktree_path)

        # Should auto-detect feature from branch name
        result = runner.invoke(app, ["list-tasks", "--json"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "tasks" in output


class TestMultipleTasksWorkflow:
    """Tests for workflows with multiple tasks."""

    def test_list_multiple_tasks_by_lane(self, task_repo: Path, monkeypatch):
        """Should list and filter multiple tasks by lane."""
        monkeypatch.chdir(task_repo)

        # Create additional tasks
        tasks_dir = task_repo / "kitty-specs" / "001-test-feature" / "tasks"

        (tasks_dir / "WP02-second-task.md").write_text("""---
work_package_id: "WP02"
title: "Second Task"
lane: "doing"
---

# WP02

Content
""")

        (tasks_dir / "WP03-third-task.md").write_text("""---
work_package_id: "WP03"
title: "Third Task"
lane: "planned"
---

# WP03

Content
""")

        # List all tasks
        result1 = runner.invoke(
            app, ["list-tasks", "--feature", "001-test-feature", "--json"]
        )
        assert result1.exit_code == 0
        output1 = json.loads(result1.stdout)
        assert output1["count"] == 3

        # List only planned tasks
        result2 = runner.invoke(
            app, ["list-tasks", "--lane", "planned", "--feature", "001-test-feature", "--json"]
        )
        assert result2.exit_code == 0
        output2 = json.loads(result2.stdout)
        assert output2["count"] == 2  # WP01 and WP03

        # List only doing tasks
        result3 = runner.invoke(
            app, ["list-tasks", "--lane", "doing", "--feature", "001-test-feature", "--json"]
        )
        assert result3.exit_code == 0
        output3 = json.loads(result3.stdout)
        assert output3["count"] == 1
        assert output3["tasks"][0]["work_package_id"] == "WP02"

    def test_move_multiple_tasks_independently(self, task_repo: Path, monkeypatch):
        """Should move multiple tasks through workflow independently."""
        monkeypatch.chdir(task_repo)

        # Create second task
        tasks_dir = task_repo / "kitty-specs" / "001-test-feature" / "tasks"
        (tasks_dir / "WP02-second.md").write_text("""---
work_package_id: "WP02"
title: "Second"
lane: "planned"
---

# WP02

## Activity Log

- 2025-01-01T00:00:00Z – system – lane=planned – Initial
""")

        # Move WP01 to doing
        result1 = runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature", "--json"]
        )
        assert result1.exit_code == 0

        # Move WP02 to for_review
        result2 = runner.invoke(
            app, ["move-task", "WP02", "--to", "for_review", "--feature", "001-test-feature", "--json"]
        )
        assert result2.exit_code == 0

        # Verify both in different lanes
        result3 = runner.invoke(
            app, ["list-tasks", "--feature", "001-test-feature", "--json"]
        )
        assert result3.exit_code == 0
        output3 = json.loads(result3.stdout)

        wp01 = next(t for t in output3["tasks"] if t["work_package_id"] == "WP01")
        wp02 = next(t for t in output3["tasks"] if t["work_package_id"] == "WP02")

        assert wp01["lane"] == "in_progress"
        assert wp02["lane"] == "for_review"


class TestErrorHandling:
    """Tests for error handling in task commands."""

    def test_move_nonexistent_task(self, task_repo: Path, monkeypatch):
        """Should error when trying to move nonexistent task."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app, ["move-task", "WP99", "--to", "doing", "--json"]
        )

        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output

    def test_validate_nonexistent_task(self, task_repo: Path, monkeypatch):
        """Should error when validating nonexistent task."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(app, ["validate-workflow", "WP99", "--json"])

        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output


class TestHumanOutputFormats:
    """Tests for human-readable output formats."""

    def test_move_task_human_output(self, task_repo: Path, monkeypatch):
        """Should display readable output for task moves."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--feature", "001-test-feature"]
        )

        assert result.exit_code == 0
        assert "Moved WP01" in result.stdout
        assert "planned" in result.stdout
        assert "in_progress" in result.stdout

    def test_list_tasks_human_output(self, task_repo: Path, monkeypatch):
        """Should display readable task list."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app, ["list-tasks", "--feature", "001-test-feature"]
        )

        assert result.exit_code == 0
        assert "WP01" in result.stdout
        assert "Test Task" in result.stdout

    def test_validate_human_output(self, task_repo: Path, monkeypatch):
        """Should display readable validation results."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app, ["validate-workflow", "WP01", "--feature", "001-test-feature"]
        )

        assert result.exit_code == 0
        assert "validation passed" in result.stdout

    def test_human_error_output(self, task_repo: Path, monkeypatch):
        """Should display readable error messages."""
        monkeypatch.chdir(task_repo)

        result = runner.invoke(
            app, ["move-task", "WP99", "--to", "doing", "--feature", "001-test-feature"]
        )

        assert result.exit_code == 1
        assert "Error:" in result.stdout
