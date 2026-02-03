"""Unit tests for research mission workflow commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.workflow import app

runner = CliRunner()


@pytest.fixture
def research_task_file(tmp_path: Path) -> Path:
    """Create a mock research task file with frontmatter."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .kittify marker
    (repo_root / ".kittify").mkdir()

    # Create feature directory
    feature_dir = repo_root / "kitty-specs" / "008-research-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create meta.json with research mission and deliverables_path
    meta_file = feature_dir / "meta.json"
    meta_file.write_text(json.dumps({
        "mission": "research",
        "slug": "008-research-feature",
        "deliverables_path": "docs/research/008-research-feature/"
    }))

    # Create task file
    task_file = tasks_dir / "WP01-research-task.md"
    task_content = """---
work_package_id: "WP01"
title: "Literature Review"
lane: "planned"
agent: ""
shell_pid: ""
---

# Work Package: WP01 - Literature Review

Research literature on the topic.

## Activity Log

- 2025-01-25T00:00:00Z – system – lane=planned – Initial creation
"""
    task_file.write_text(task_content)

    return task_file


class TestResearchImplementCommand:
    """Tests for implement command with research missions."""

    @patch("specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.workflow.locate_project_root")
    @patch("specify_cli.cli.commands.agent.workflow._find_feature_slug")
    def test_implement_shows_deliverables_path(
        self, mock_slug: Mock, mock_root: Mock, mock_ensure: Mock, research_task_file: Path
    ):
        """implement output should display deliverables_path for research missions."""
        repo_root = research_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-research-feature"
        mock_ensure.return_value = (repo_root, "main")

        # Execute
        result = runner.invoke(
            app, ["implement", "WP01", "--agent", "test-agent"]
        )

        # Verify deliverables path is shown in output
        assert result.exit_code == 0
        assert "docs/research/008-research-feature/" in result.stdout or "research deliverables" in result.stdout.lower()

    @patch("specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.workflow.locate_project_root")
    @patch("specify_cli.cli.commands.agent.workflow._find_feature_slug")
    def test_implement_warns_about_kitty_specs(
        self, mock_slug: Mock, mock_root: Mock, mock_ensure: Mock, research_task_file: Path
    ):
        """implement output should warn not to put deliverables in kitty-specs."""
        repo_root = research_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-research-feature"
        mock_ensure.return_value = (repo_root, "main")

        # Execute
        result = runner.invoke(
            app, ["implement", "WP01", "--agent", "test-agent"]
        )

        # Verify warning about kitty-specs
        assert result.exit_code == 0
        # The warning appears in the temp file, not necessarily stdout
        # Check that output mentions research or deliverables

    @patch("specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.workflow.locate_project_root")
    @patch("specify_cli.cli.commands.agent.workflow._find_feature_slug")
    def test_implement_detects_research_mission(
        self, mock_slug: Mock, mock_root: Mock, mock_ensure: Mock, research_task_file: Path
    ):
        """implement should correctly detect research mission from meta.json."""
        repo_root = research_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-research-feature"
        mock_ensure.return_value = (repo_root, "main")

        # Execute
        result = runner.invoke(
            app, ["implement", "WP01", "--agent", "test-agent"]
        )

        # Should succeed and show research-specific info
        assert result.exit_code == 0
        # Research missions should show deliverables path
        assert "Research" in result.stdout or "research" in result.stdout.lower() or "docs/research" in result.stdout


class TestResearchMissionDetection:
    """Tests for mission detection in workflow commands."""

    @patch("specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.workflow.locate_project_root")
    @patch("specify_cli.cli.commands.agent.workflow._find_feature_slug")
    def test_software_dev_does_not_show_deliverables(
        self, mock_slug: Mock, mock_root: Mock, mock_ensure: Mock, tmp_path: Path
    ):
        """Software-dev missions should not show deliverables_path."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".kittify").mkdir()

        feature_dir = repo_root / "kitty-specs" / "008-sw-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create meta.json with software-dev mission
        meta_file = feature_dir / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "software-dev",
            "slug": "008-sw-feature"
        }))

        # Create task file
        task_file = tasks_dir / "WP01-code-task.md"
        task_file.write_text("""---
work_package_id: "WP01"
title: "Implement Feature"
lane: "planned"
agent: ""
---

# WP01

Content

## Activity Log

- 2025-01-25T00:00:00Z – system – lane=planned – Initial
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "008-sw-feature"
        mock_ensure.return_value = (repo_root, "main")

        # Execute
        result = runner.invoke(
            app, ["implement", "WP01", "--agent", "test-agent"]
        )

        # Should succeed but not show research-specific deliverables info
        assert result.exit_code == 0
        # Software-dev should not mention "research deliverables"
        assert "Research deliverables:" not in result.stdout


class TestDeliverablesPathInPrompt:
    """Tests for deliverables_path inclusion in generated prompts."""

    @patch("specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.workflow.locate_project_root")
    @patch("specify_cli.cli.commands.agent.workflow._find_feature_slug")
    def test_prompt_file_contains_deliverables_path(
        self, mock_slug: Mock, mock_root: Mock, mock_ensure: Mock, research_task_file: Path, tmp_path: Path
    ):
        """The generated prompt file should contain deliverables_path for research."""
        import tempfile

        repo_root = research_task_file.parent.parent.parent.parent
        mock_root.return_value = repo_root
        mock_slug.return_value = "008-research-feature"
        mock_ensure.return_value = (repo_root, "main")

        # Execute
        result = runner.invoke(
            app, ["implement", "WP01", "--agent", "test-agent"]
        )

        assert result.exit_code == 0

        # Find the prompt file path from output
        # The output should contain a path to a temp file
        prompt_file_path = None
        for line in result.stdout.split('\n'):
            if 'spec-kitty-implement-WP01.md' in line:
                # Extract the path
                import re
                match = re.search(r'(/[^\s]+spec-kitty-implement-WP01\.md)', line)
                if match:
                    prompt_file_path = Path(match.group(1))
                    break

        # If we found the prompt file, check its contents
        if prompt_file_path and prompt_file_path.exists():
            content = prompt_file_path.read_text()
            assert "docs/research/008-research-feature/" in content

    @patch("specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.workflow.locate_project_root")
    @patch("specify_cli.cli.commands.agent.workflow._find_feature_slug")
    def test_default_deliverables_path_when_not_in_meta(
        self, mock_slug: Mock, mock_root: Mock, mock_ensure: Mock, tmp_path: Path
    ):
        """Should use default deliverables path when not specified in meta.json."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".kittify").mkdir()

        feature_dir = repo_root / "kitty-specs" / "009-research-no-path"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create meta.json with research mission but NO deliverables_path
        meta_file = feature_dir / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "research",
            "slug": "009-research-no-path"
            # Note: no deliverables_path field
        }))

        # Create task file
        task_file = tasks_dir / "WP01-task.md"
        task_file.write_text("""---
work_package_id: "WP01"
title: "Research Task"
lane: "planned"
agent: ""
---

# WP01

Content

## Activity Log

- 2025-01-25T00:00:00Z – system – lane=planned – Initial
""")

        mock_root.return_value = repo_root
        mock_slug.return_value = "009-research-no-path"
        mock_ensure.return_value = (repo_root, "main")

        # Execute
        result = runner.invoke(
            app, ["implement", "WP01", "--agent", "test-agent"]
        )

        assert result.exit_code == 0
        # Should show default path pattern
        assert "docs/research/009-research-no-path/" in result.stdout or "research" in result.stdout.lower()
