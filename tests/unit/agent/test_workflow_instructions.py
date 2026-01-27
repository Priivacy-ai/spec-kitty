"""Tests for workflow instruction improvements and pre-flight checks."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import workflow
from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review
from specify_cli.frontmatter import write_frontmatter


def write_tasks_md(feature_dir: Path, wp_id: str, subtasks: list[str], done: bool = True) -> None:
    """Write a minimal tasks.md with checkbox status for a WP."""
    checkbox = "[x]" if done else "[ ]"
    lines = [f"## {wp_id} Test", ""]
    for task_id in subtasks:
        lines.append(f"- {checkbox} {task_id} Placeholder task")
    (feature_dir / "tasks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_wp_file(path: Path, wp_id: str, lane: str) -> None:
    """Create a minimal WP prompt file."""
    frontmatter = {
        "work_package_id": wp_id,
        "subtasks": ["T001"],
        "title": f"{wp_id} Test",
        "phase": "Phase 0",
        "lane": lane,
        "assignee": "",
        "agent": "",
        "shell_pid": "",
        "dependencies": [],
        "history": [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "lane": lane,
                "agent": "system",
                "shell_pid": "",
                "action": "Prompt created",
            }
        ],
    }
    body = f"# {wp_id} Prompt\n\n## Activity Log\n- 2026-01-01T00:00:00Z – system – lane={lane} – Prompt created.\n"
    write_frontmatter(path, frontmatter, body)


@pytest.fixture()
def workflow_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal repo root for workflow tests."""
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    return repo_root


class TestWorkflowImplementInstructions:
    """Test that workflow implement instructions include all required guidance."""

    def test_implement_instructions_include_git_commit_step_1(self, workflow_repo: Path):
        """Verify first instruction block (WHEN YOU'RE DONE) includes git commit."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        write_tasks_md(feature_dir, "WP01", ["T001"], done=True)
        wp_path = tasks_dir / "WP01-test.md"
        write_wp_file(wp_path, "WP01", lane="planned")

        runner = CliRunner()
        result = runner.invoke(workflow.app, ["implement", "WP01", "--feature", feature_slug, "--agent", "test-agent"])
        
        # Should succeed
        assert result.exit_code == 0
        
        # The full prompt is written to system temp directory
        prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
        assert prompt_file.exists(), f"Prompt file not found: {prompt_file}"
        
        prompt_content = prompt_file.read_text(encoding="utf-8")
        
        # Check that prompt includes git commit instructions
        assert "WHEN YOU'RE DONE:" in prompt_content
        assert "1. **Commit your implementation files:**" in prompt_content
        assert "git status" in prompt_content
        assert "git add" in prompt_content
        assert "git commit" in prompt_content
        assert ("feat(WP01):" in prompt_content or "fix(WP01):" in prompt_content)
        assert "git log -1" in prompt_content

    def test_implement_instructions_include_git_commit_step_2(self, workflow_repo: Path):
        """Verify second instruction block includes commit message conventions."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        write_tasks_md(feature_dir, "WP01", ["T001"], done=True)
        wp_path = tasks_dir / "WP01-test.md"
        write_wp_file(wp_path, "WP01", lane="planned")

        runner = CliRunner()
        result = runner.invoke(workflow.app, ["implement", "WP01", "--feature", feature_slug, "--agent", "test-agent"])
        
        assert result.exit_code == 0
        
        # Read the prompt file from system temp
        prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
        assert prompt_file.exists(), f"Prompt file not found: {prompt_file}"
        
        prompt_content = prompt_file.read_text(encoding="utf-8")
        
        # Verify commit message format guidance is present
        assert ("IMPLEMENTATION COMPLETE" in prompt_content or "WHEN YOU'RE DONE" in prompt_content)
        assert ("feat(" in prompt_content or "fix(" in prompt_content)
        assert ("chore:" in prompt_content or "chore(" in prompt_content)
        assert ("docs:" in prompt_content or "docs(" in prompt_content)

    def test_implement_instructions_correct_numbering(self, workflow_repo: Path):
        """Verify instruction steps are numbered 1-2-3 correctly."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        write_tasks_md(feature_dir, "WP01", ["T001"], done=True)
        wp_path = tasks_dir / "WP01-test.md"
        write_wp_file(wp_path, "WP01", lane="planned")

        runner = CliRunner()
        result = runner.invoke(workflow.app, ["implement", "WP01", "--feature", feature_slug, "--agent", "test-agent"])
        
        assert result.exit_code == 0
        
        # Read the prompt file from system temp
        prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
        assert prompt_file.exists(), f"Prompt file not found: {prompt_file}"
        
        prompt_content = prompt_file.read_text(encoding="utf-8")
        
        # Verify the numbering sequence exists
        assert "1. **Commit your implementation files:**" in prompt_content
        assert "2." in prompt_content
        assert "3." in prompt_content


class TestMoveTaskPreflightCheck:
    """Test that move-task command blocks on uncommitted changes."""

    def test_validate_ready_for_review_blocks_on_uncommitted_worktree_changes(
        self, tmp_path
    ):
        """Verify validation blocks when worktree has uncommitted changes."""
        # Create mock directory structure
        feature_slug = "001-test-feature"
        feature_dir = tmp_path / "kitty-specs" / feature_slug
        feature_dir.mkdir(parents=True)
        
        # Create meta.json for software-dev mission
        (feature_dir / "meta.json").write_text('{"mission": "software-dev"}')
        
        # Create worktree directory
        worktree_path = tmp_path / ".worktrees" / f"{feature_slug}-WP01"
        worktree_path.mkdir(parents=True)
        
        # Mock git commands
        with patch("subprocess.run") as mock_run:
            def git_command_side_effect(args, **kwargs):
                # Match different git commands
                if "status" in args and "--porcelain" in args and "kitty-specs" in str(args):
                    # git status for research artifacts in main repo - empty
                    return MagicMock(returncode=0, stdout="", stderr="")
                elif "rev-parse" in args and "--abbrev-ref" in args:
                    # git rev-parse --abbrev-ref HEAD - return branch name (not detached)
                    return MagicMock(returncode=0, stdout=f"feature/{feature_slug}-WP01\n", stderr="")
                elif "rev-parse" in args and "--verify" in args:
                    # git rev-parse --verify for merge/rebase/cherry-pick - not in progress
                    return MagicMock(returncode=1, stdout="", stderr="")
                elif "rev-list" in args and "HEAD..main" in args:
                    # git rev-list HEAD..main - not behind main
                    return MagicMock(returncode=0, stdout="0\n", stderr="")
                elif "status" in args and "--porcelain" in args:
                    # git status for worktree - HAS uncommitted changes
                    return MagicMock(returncode=0, stdout="M  src/test.py\n?? test_new.py\n", stderr="")
                elif "rev-list" in args and "main..HEAD" in args:
                    # git rev-list main..HEAD - has commits
                    return MagicMock(returncode=0, stdout="2\n", stderr="")
                else:
                    # Default
                    return MagicMock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_command_side_effect
            
            is_valid, guidance = _validate_ready_for_review(
                tmp_path, feature_slug, "WP01", False
            )
            
            # Should block
            assert is_valid is False, f"Expected validation to fail"
            assert len(guidance) > 0, "Expected guidance messages"
            # Check for any message about uncommitted/staged/unstaged changes
            assert any(
                any(keyword in line.lower() for keyword in ["uncommitted", "staged", "unstaged"]) 
                for line in guidance
            ), f"No uncommitted/staged message in: {guidance}"
            assert any("git add -A" in line for line in guidance), f"No 'git add -A' in: {guidance}"
            assert any("git commit" in line for line in guidance), f"No 'git commit' in: {guidance}"

    def test_validate_ready_for_review_allows_clean_worktree(self, tmp_path):
        """Verify validation passes when worktree is clean."""
        # Create mock directory structure
        feature_slug = "001-test-feature"
        feature_dir = tmp_path / "kitty-specs" / feature_slug
        feature_dir.mkdir(parents=True)
        
        # Create meta.json for software-dev mission
        (feature_dir / "meta.json").write_text('{"mission": "software-dev"}')
        
        # Create worktree directory
        worktree_path = tmp_path / ".worktrees" / f"{feature_slug}-WP01"
        worktree_path.mkdir(parents=True)
        
        # Mock git commands
        with patch("subprocess.run") as mock_run:
            def git_command_side_effect(args, **kwargs):
                # Match different git commands
                if "status" in args and "--porcelain" in args and "kitty-specs" in str(args):
                    # git status for research artifacts in main repo - empty
                    return MagicMock(returncode=0, stdout="", stderr="")
                elif "rev-parse" in args and "--abbrev-ref" in args:
                    # git rev-parse --abbrev-ref HEAD - return branch name (not detached)
                    return MagicMock(returncode=0, stdout=f"feature/{feature_slug}-WP01\n", stderr="")
                elif "rev-parse" in args and "--verify" in args:
                    # git rev-parse --verify for merge/rebase/cherry-pick - not in progress
                    return MagicMock(returncode=1, stdout="", stderr="")
                elif "rev-list" in args and "HEAD..main" in args:
                    # git rev-list HEAD..main - not behind main
                    return MagicMock(returncode=0, stdout="0\n", stderr="")
                elif "status" in args and "--porcelain" in args:
                    # git status for worktree - clean
                    return MagicMock(returncode=0, stdout="", stderr="")
                elif "rev-list" in args and "main..HEAD" in args:
                    # git rev-list main..HEAD - has commits
                    return MagicMock(returncode=0, stdout="5\n", stderr="")
                else:
                    # Default
                    return MagicMock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_command_side_effect
            
            is_valid, guidance = _validate_ready_for_review(
                tmp_path, feature_slug, "WP01", False
            )
            
            # Should allow
            assert is_valid is True
            assert len(guidance) == 0

    def test_validate_ready_for_review_respects_force_flag(self, tmp_path):
        """Verify --force bypasses validation."""
        # Even with uncommitted changes, force should allow
        is_valid, guidance = _validate_ready_for_review(
            tmp_path, "001-test", "WP01", True  # force=True
        )
        
        assert is_valid is True
        assert len(guidance) == 0
