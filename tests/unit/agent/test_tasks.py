"""Unit tests for agent task workflow commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app

runner = CliRunner()


@pytest.fixture
def mock_task_file(tmp_path: Path) -> Path:
    """Create a mock task file with frontmatter."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .kittify marker
    (repo_root / ".kittify").mkdir()

    # Create feature directory
    feature_dir = repo_root / "kitty-specs" / "008-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create task file
    task_file = tasks_dir / "WP01-test-task.md"
    task_content = """---
work_package_id: "WP01"
title: "Test Task"
lane: "planned"
agent: "claude"
shell_pid: "12345"
---

# Work Package: WP01 - Test Task

Test content here.

## Activity Log

- 2025-01-01T00:00:00Z – system – lane=planned – Initial creation
"""
    task_file.write_text(task_content)

    return task_file


class TestMoveTask:
    """Tests for move-task command."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_task_json_output(
        self, mock_slug: Mock, mock_root: Mock, mock_task_file: Path
    ):
        """Should move task and output JSON."""
        repo_root = mock_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test-feature"

        # Execute
        result = runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--json"]
        )

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["task_id"] == "WP01"
        assert output["old_lane"] == "planned"
        assert output["new_lane"] == "doing"

        # Verify file was updated
        updated_content = mock_task_file.read_text()
        assert 'lane: "doing"' in updated_content
        assert "Moved to doing" in updated_content

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_task_human_output(
        self, mock_slug: Mock, mock_root: Mock, mock_task_file: Path
    ):
        """Should move task and output human-readable format."""
        repo_root = mock_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test-feature"

        # Execute
        result = runner.invoke(
            app, ["move-task", "WP01", "--to", "for_review"]
        )

        # Verify
        assert result.exit_code == 0
        assert "Moved WP01 from planned to for_review" in result.stdout

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_task_with_agent_and_pid(
        self, mock_slug: Mock, mock_root: Mock, mock_task_file: Path
    ):
        """Should update agent and shell_pid when provided."""
        repo_root = mock_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test-feature"

        # Execute
        result = runner.invoke(
            app, [
                "move-task", "WP01", "--to", "doing",
                "--agent", "test-agent",
                "--shell-pid", "99999",
                "--json"
            ]
        )

        # Verify
        assert result.exit_code == 0

        # Check frontmatter was updated
        updated_content = mock_task_file.read_text()
        assert 'agent: "test-agent"' in updated_content
        assert 'shell_pid: "99999"' in updated_content

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    def test_move_task_invalid_lane(self, mock_root: Mock, mock_task_file: Path):
        """Should reject invalid lane values."""
        repo_root = mock_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root

        # Execute
        result = runner.invoke(
            app, ["move-task", "WP01", "--to", "invalid_lane", "--json"]
        )

        # Verify
        assert result.exit_code == 1
        output = json.loads(result.stdout.split('\n')[0])
        assert "error" in output

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    def test_move_task_no_project_root(self, mock_root: Mock):
        """Should error when project root not found."""
        mock_root.return_value = None

        # Execute
        result = runner.invoke(
            app, ["move-task", "WP01", "--to", "doing", "--json"]
        )

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output


class TestMarkStatus:
    """Tests for mark-status command."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_mark_status_done_json(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should mark status as done with JSON output."""
        mock_root.return_value = tmp_path
        mock_slug.return_value = "008-test"
        tasks_dir = tmp_path / "kitty-specs" / "008-test"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / "tasks.md").write_text("- [ ] T001 Initial task\n", encoding="utf-8")

        # Execute
        result = runner.invoke(
            app, ["mark-status", "T001", "--status", "done", "--json"]
        )

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["status"] == "done"

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    def test_mark_status_no_project_root(self, mock_root: Mock):
        """Should error when project root not found."""
        mock_root.return_value = None

        # Execute
        result = runner.invoke(
            app, ["mark-status", "T001", "--status", "done", "--json"]
        )

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_mark_status_pending(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should mark status as pending."""
        mock_root.return_value = tmp_path
        mock_slug.return_value = "008-test"
        tasks_dir = tmp_path / "kitty-specs" / "008-test"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / "tasks.md").write_text("- [x] T002 Initial task\n", encoding="utf-8")

        # Execute
        result = runner.invoke(
            app, ["mark-status", "T002", "--status", "pending"]
        )

        # Verify
        assert result.exit_code == 0
        assert "Marked T002 as pending" in result.stdout

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_mark_status_invalid_status(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should reject invalid status values."""
        mock_root.return_value = tmp_path
        mock_slug.return_value = "008-test"

        # Execute
        result = runner.invoke(
            app, ["mark-status", "T001", "--status", "invalid", "--json"]
        )

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output
        assert "Invalid status" in output["error"]


class TestListTasks:
    """Tests for list-tasks command."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    def test_list_tasks_no_project_root(self, mock_root: Mock):
        """Should error when project root not found."""
        mock_root.return_value = None

        # Execute
        result = runner.invoke(app, ["list-tasks", "--json"])

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_list_tasks_no_tasks_directory(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should error when tasks directory doesn't exist."""
        mock_root.return_value = tmp_path
        mock_slug.return_value = "008-test"

        # Execute (no tasks directory created)
        result = runner.invoke(app, ["list-tasks", "--json"])

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_list_all_tasks_json(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should list all tasks with JSON output."""
        # Setup: Create multiple task files
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "008-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create WP01
        (tasks_dir / "WP01-task-one.md").write_text("""---
work_package_id: "WP01"
title: "Task One"
lane: "planned"
---

Content
""")

        # Create WP02
        (tasks_dir / "WP02-task-two.md").write_text("""---
work_package_id: "WP02"
title: "Task Two"
lane: "doing"
---

Content
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test"

        # Execute
        result = runner.invoke(app, ["list-tasks", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "tasks" in output
        assert output["count"] == 2
        assert output["tasks"][0]["work_package_id"] == "WP01"
        assert output["tasks"][1]["work_package_id"] == "WP02"

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_list_tasks_filter_by_lane(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should filter tasks by lane."""
        # Setup
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "008-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        (tasks_dir / "WP01-planned.md").write_text("""---
work_package_id: "WP01"
title: "Planned"
lane: "planned"
---
Content
""")

        (tasks_dir / "WP02-doing.md").write_text("""---
work_package_id: "WP02"
title: "Doing"
lane: "doing"
---
Content
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test"

        # Execute
        result = runner.invoke(app, ["list-tasks", "--lane", "doing", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["count"] == 1
        assert output["tasks"][0]["work_package_id"] == "WP02"
        assert output["tasks"][0]["lane"] == "doing"

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_list_tasks_human_output(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should list tasks in human-readable format."""
        # Setup
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "008-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        (tasks_dir / "WP01-test.md").write_text("""---
work_package_id: "WP01"
title: "Test Task"
lane: "planned"
---
Content
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test"

        # Execute
        result = runner.invoke(app, ["list-tasks"])

        # Verify
        assert result.exit_code == 0
        assert "WP01" in result.stdout
        assert "Test Task" in result.stdout


class TestAddHistory:
    """Tests for add-history command."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    def test_add_history_no_project_root(self, mock_root: Mock):
        """Should error when project root not found."""
        mock_root.return_value = None

        # Execute
        result = runner.invoke(
            app, ["add-history", "WP01", "--note", "Test", "--json"]
        )

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_add_history_json(
        self, mock_slug: Mock, mock_root: Mock, mock_task_file: Path
    ):
        """Should add history entry with JSON output."""
        repo_root = mock_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test-feature"

        # Execute
        result = runner.invoke(
            app, [
                "add-history", "WP01",
                "--note", "Test note",
                "--json"
            ]
        )

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["note"] == "Test note"

        # Verify file was updated
        updated_content = mock_task_file.read_text()
        assert "Test note" in updated_content

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_add_history_with_agent(
        self, mock_slug: Mock, mock_root: Mock, mock_task_file: Path
    ):
        """Should include agent in history entry."""
        repo_root = mock_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test-feature"

        # Execute
        result = runner.invoke(
            app, [
                "add-history", "WP01",
                "--note", "Custom note",
                "--agent", "test-bot",
                "--shell-pid", "55555",
                "--json"
            ]
        )

        # Verify
        assert result.exit_code == 0

        # Check history entry format
        updated_content = mock_task_file.read_text()
        assert "test-bot" in updated_content
        assert "shell_pid=55555" in updated_content
        assert "Custom note" in updated_content


class TestRollbackTask:
    """Tests for rollback-task command."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    def test_rollback_no_project_root(self, mock_root: Mock):
        """Should error when project root not found."""
        mock_root.return_value = None

        # Execute
        result = runner.invoke(app, ["rollback-task", "WP01", "--json"])

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_rollback_task_json(
        self, mock_slug: Mock, mock_root: Mock, mock_task_file: Path
    ):
        """Should rollback to previous lane."""
        repo_root = mock_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test-feature"

        # First move to doing
        runner.invoke(app, ["move-task", "WP01", "--to", "doing"])

        # Then rollback
        result = runner.invoke(app, ["rollback-task", "WP01", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["new_lane"] == "planned"

        # Verify file was updated
        updated_content = mock_task_file.read_text()
        assert 'lane: "planned"' in updated_content
        assert "Rolled back" in updated_content

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_rollback_insufficient_history(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should error when insufficient history entries."""
        # Create task with only one history entry
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "008-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-test.md"
        task_file.write_text("""---
work_package_id: "WP01"
title: "Test"
lane: "planned"
---

# Test

## Activity Log

- 2025-01-01T00:00:00Z – system – lane=planned – Initial
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test"

        # Execute
        result = runner.invoke(app, ["rollback-task", "WP01", "--json"])

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output
        assert "Need at least 2 history entries" in output["error"]


class TestValidateWorkflow:
    """Tests for validate-workflow command."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    def test_validate_no_project_root(self, mock_root: Mock):
        """Should error when project root not found."""
        mock_root.return_value = None

        # Execute
        result = runner.invoke(app, ["validate-workflow", "WP01", "--json"])

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_validate_valid_task(
        self, mock_slug: Mock, mock_root: Mock, mock_task_file: Path
    ):
        """Should validate task with all required fields."""
        repo_root = mock_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test-feature"

        # Execute
        result = runner.invoke(app, ["validate-workflow", "WP01", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["valid"] is True
        assert output["errors"] == []

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_validate_missing_required_fields(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should detect missing required fields."""
        # Create task with missing fields
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "008-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-incomplete.md"
        task_file.write_text("""---
work_package_id: "WP01"
---

# Test
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test"

        # Execute
        result = runner.invoke(app, ["validate-workflow", "WP01", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["valid"] is False
        assert any("title" in error for error in output["errors"])
        assert any("lane" in error for error in output["errors"])

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_validate_invalid_lane(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should detect invalid lane values."""
        # Create task with invalid lane
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "008-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-bad-lane.md"
        task_file.write_text("""---
work_package_id: "WP01"
title: "Test"
lane: "invalid_lane"
---

# Test
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test"

        # Execute
        result = runner.invoke(app, ["validate-workflow", "WP01", "--json"])

        # Verify - locate_work_package raises when lane is invalid
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_validate_warnings(
        self, mock_slug: Mock, mock_root: Mock, tmp_path: Path
    ):
        """Should detect warnings like missing activity log."""
        # Create task without activity log
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "008-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-no-log.md"
        task_file.write_text("""---
work_package_id: "WP01"
title: "Test"
lane: "planned"
---

# Test

No activity log section.
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "008-test"

        # Execute
        result = runner.invoke(app, ["validate-workflow", "WP01", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["valid"] is True  # Valid but has warnings
        assert any("Activity Log" in warning for warning in output["warnings"])


class TestFindFeatureSlug:
    """Tests for _find_feature_slug helper."""

    @patch("specify_cli.cli.commands.agent.tasks.Path.cwd")
    def test_find_from_cwd_with_kitty_specs(self, mock_cwd: Mock):
        """Should extract feature slug from cwd containing kitty-specs."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug

        mock_cwd.return_value = Path("/repo/.worktrees/008-test/kitty-specs/008-test-feature")

        slug = _find_feature_slug()
        assert slug == "008-test-feature"

    @patch("subprocess.run")
    @patch("specify_cli.cli.commands.agent.tasks.Path.cwd")
    def test_find_from_git_branch(self, mock_cwd: Mock, mock_subprocess: Mock):
        """Should extract feature slug from git branch name."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug

        mock_cwd.return_value = Path("/repo")
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="008-test-feature\n"
        )

        slug = _find_feature_slug()
        assert slug == "008-test-feature"

    @patch("subprocess.run")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks.Path.cwd")
    def test_find_raises_on_failure(self, mock_cwd: Mock, mock_repo: Mock, mock_subprocess: Mock):
        """Should raise typer.Exit when slug cannot be determined."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug
        import subprocess
        from click.exceptions import Exit

        mock_cwd.return_value = Path("/repo")
        mock_repo.return_value = None
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(Exit):
            _find_feature_slug()
