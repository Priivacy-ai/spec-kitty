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
    # NOTE: agent is empty to allow tests to set it without ownership conflict
    task_file = tasks_dir / "WP01-test-task.md"
    task_content = """---
work_package_id: "WP01"
title: "Test Task"
lane: "planned"
agent: ""
shell_pid: ""
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


class TestValidateReadyForReview:
    """Tests for _validate_ready_for_review helper."""

    def test_force_bypasses_validation(self, tmp_path: Path):
        """Should skip all checks when force=True."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        # Don't need to set up anything - force should bypass all checks
        is_valid, guidance = _validate_ready_for_review(
            tmp_path, "008-test", "WP01", force=True
        )

        assert is_valid is True
        assert guidance == []

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key")
    @patch("subprocess.run")
    def test_research_uncommitted_artifacts_blocks_review(
        self, mock_run: Mock, mock_mission_key: Mock, mock_main_root: Mock, tmp_path: Path
    ):
        """Should detect uncommitted research artifacts and provide actionable guidance."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        # Setup mocks
        mock_main_root.return_value = tmp_path
        mock_mission_key.return_value = "research"

        # Create feature directory
        feature_dir = tmp_path / "kitty-specs" / "008-research"
        feature_dir.mkdir(parents=True)

        # Simulate uncommitted research artifacts
        mock_run.return_value = Mock(
            returncode=0,
            stdout=" M kitty-specs/008-research/data-model.md\n M kitty-specs/008-research/research/evidence-log.csv\n"
        )

        is_valid, guidance = _validate_ready_for_review(
            tmp_path, "008-research", "WP01", force=False
        )

        assert is_valid is False
        assert len(guidance) > 0
        # Check actionable guidance is present
        guidance_text = "\n".join(guidance)
        assert "uncommitted" in guidance_text.lower()
        assert "git add" in guidance_text
        assert "git commit" in guidance_text
        assert "research(WP01)" in guidance_text  # Research-specific commit format

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key")
    @patch("subprocess.run")
    def test_research_committed_artifacts_allows_review(
        self, mock_run: Mock, mock_mission_key: Mock, mock_main_root: Mock, tmp_path: Path
    ):
        """Should pass when research artifacts are committed."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        # Setup mocks
        mock_main_root.return_value = tmp_path
        mock_mission_key.return_value = "research"

        # Create feature directory
        feature_dir = tmp_path / "kitty-specs" / "008-research"
        feature_dir.mkdir(parents=True)

        # Simulate no uncommitted changes
        mock_run.return_value = Mock(returncode=0, stdout="")

        is_valid, guidance = _validate_ready_for_review(
            tmp_path, "008-research", "WP01", force=False
        )

        assert is_valid is True
        assert guidance == []

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key")
    @patch("subprocess.run")
    def test_softwaredev_uncommitted_worktree_blocks_review(
        self, mock_run: Mock, mock_mission_key: Mock, mock_main_root: Mock, tmp_path: Path
    ):
        """Should detect uncommitted implementation changes in worktree."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        # Setup mocks
        mock_main_root.return_value = tmp_path
        mock_mission_key.return_value = "software-dev"

        # Create feature and worktree directories
        feature_dir = tmp_path / "kitty-specs" / "008-feature"
        feature_dir.mkdir(parents=True)
        worktree_path = tmp_path / ".worktrees" / "008-feature-WP01"
        worktree_path.mkdir(parents=True)

        # Simulate: main clean, worktree has uncommitted changes
        def subprocess_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            cwd = kwargs.get("cwd", tmp_path)

            if "status" in cmd and "--porcelain" in cmd:
                if cwd == worktree_path:
                    return Mock(returncode=0, stdout=" M src/main.py\n")
                else:
                    return Mock(returncode=0, stdout="")  # Main repo clean
            elif "rev-parse" in cmd and "--verify" in cmd:
                # No in-progress operations (MERGE_HEAD, REBASE_HEAD, etc. don't exist)
                return Mock(returncode=1, stdout="")
            elif "rev-list" in cmd and "HEAD..main" in cmd:
                # Not behind main
                return Mock(returncode=0, stdout="0\n")
            elif "rev-list" in cmd:
                # Has implementation commits
                return Mock(returncode=0, stdout="5\n")
            return Mock(returncode=0, stdout="")

        mock_run.side_effect = subprocess_side_effect

        is_valid, guidance = _validate_ready_for_review(
            tmp_path, "008-feature", "WP01", force=False
        )

        assert is_valid is False
        guidance_text = "\n".join(guidance)
        assert "uncommitted" in guidance_text.lower()
        assert "worktree" in guidance_text.lower()
        assert "git add" in guidance_text

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key")
    @patch("subprocess.run")
    def test_softwaredev_no_commits_blocks_review(
        self, mock_run: Mock, mock_mission_key: Mock, mock_main_root: Mock, tmp_path: Path
    ):
        """Should detect when worktree has no implementation commits."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        # Setup mocks
        mock_main_root.return_value = tmp_path
        mock_mission_key.return_value = "software-dev"

        # Create feature and worktree directories
        feature_dir = tmp_path / "kitty-specs" / "008-feature"
        feature_dir.mkdir(parents=True)
        worktree_path = tmp_path / ".worktrees" / "008-feature-WP01"
        worktree_path.mkdir(parents=True)

        # Simulate: main clean, worktree clean, but no commits beyond main
        def subprocess_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            cwd = kwargs.get("cwd", tmp_path)

            if "status" in cmd and "--porcelain" in cmd:
                return Mock(returncode=0, stdout="")  # Both clean
            elif "rev-parse" in cmd and "--verify" in cmd:
                # No in-progress operations
                return Mock(returncode=1, stdout="")
            elif "rev-list" in cmd:
                return Mock(returncode=0, stdout="0\n")  # No commits beyond main
            return Mock(returncode=0, stdout="")

        mock_run.side_effect = subprocess_side_effect

        is_valid, guidance = _validate_ready_for_review(
            tmp_path, "008-feature", "WP01", force=False
        )

        assert is_valid is False
        guidance_text = "\n".join(guidance)
        assert "no implementation commits" in guidance_text.lower()

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key")
    @patch("subprocess.run")
    def test_filters_out_wp_status_files(
        self, mock_run: Mock, mock_mission_key: Mock, mock_main_root: Mock, tmp_path: Path
    ):
        """Should ignore WP status files in tasks/ (auto-committed by move-task)."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        # Setup mocks
        mock_main_root.return_value = tmp_path
        mock_mission_key.return_value = "research"

        # Create feature directory
        feature_dir = tmp_path / "kitty-specs" / "008-research"
        feature_dir.mkdir(parents=True)

        # Simulate only WP status files modified (should be filtered out)
        mock_run.return_value = Mock(
            returncode=0,
            stdout=" M kitty-specs/008-research/tasks/WP01-task.md\n"
        )

        is_valid, guidance = _validate_ready_for_review(
            tmp_path, "008-research", "WP01", force=False
        )

        # Should pass - WP status files are filtered out
        assert is_valid is True
        assert guidance == []


class TestFindFeatureSlug:
    """Tests for _find_feature_slug helper."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks.Path.cwd")
    def test_find_from_cwd_with_kitty_specs(self, mock_cwd: Mock, mock_root: Mock, tmp_path: Path):
        """Should extract feature slug from cwd containing kitty-specs."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug

        # Setup: cwd is in kitty-specs/feature-slug directory
        feature_dir = tmp_path / "kitty-specs" / "008-test-feature"
        feature_dir.mkdir(parents=True)

        mock_cwd.return_value = feature_dir
        mock_root.return_value = tmp_path

        with patch("specify_cli.core.feature_detection._get_main_repo_root") as mock_main:
            mock_main.return_value = tmp_path

            slug = _find_feature_slug()
            assert slug == "008-test-feature"

    @patch("subprocess.run")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks.Path.cwd")
    def test_find_from_git_branch(self, mock_cwd: Mock, mock_root: Mock, mock_subprocess: Mock, tmp_path: Path):
        """Should extract feature slug from git branch name."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug

        mock_cwd.return_value = Path("/repo")
        mock_root.return_value = tmp_path
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="008-test-feature\n"
        )

        # Create kitty-specs directory to validate the slug
        (tmp_path / "kitty-specs" / "008-test-feature").mkdir(parents=True)

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
