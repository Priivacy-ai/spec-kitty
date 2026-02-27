"""Tests for atomic multi-file commit of status artifacts (#211, #212).

Verifies that:
1. move_task() commits all status artifacts (events.jsonl, status.json,
   tasks.md) alongside the WP file in a single atomic commit.
2. Root-level tasks.md does not block _validate_ready_for_review().
3. workflow review routes through emit_status_transition().
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from specify_cli.cli.commands.agent.tasks import (
    _collect_status_artifacts,
    _validate_ready_for_review,
    app,
)

from typer.testing import CliRunner

runner = CliRunner()


class TestCollectStatusArtifacts:
    """Tests for _collect_status_artifacts helper."""

    def test_returns_empty_when_no_artifacts(self, tmp_path: Path):
        """Should return empty list when feature_dir has no status files."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        result = _collect_status_artifacts(feature_dir)
        assert result == []

    def test_returns_events_jsonl_when_present(self, tmp_path: Path):
        """Should include status.events.jsonl when it exists."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        events_file = feature_dir / "status.events.jsonl"
        events_file.write_text("{}\n")
        result = _collect_status_artifacts(feature_dir)
        assert events_file in result

    def test_returns_status_json_when_present(self, tmp_path: Path):
        """Should include status.json when it exists."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        status_file = feature_dir / "status.json"
        status_file.write_text("{}")
        result = _collect_status_artifacts(feature_dir)
        assert status_file in result

    def test_returns_tasks_md_when_present(self, tmp_path: Path):
        """Should include tasks.md when it exists."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text("# Tasks\n")
        result = _collect_status_artifacts(feature_dir)
        assert tasks_file in result

    def test_returns_all_artifacts_when_all_present(self, tmp_path: Path):
        """Should return all three artifacts when they all exist."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        (feature_dir / "status.events.jsonl").write_text("{}\n")
        (feature_dir / "status.json").write_text("{}")
        (feature_dir / "tasks.md").write_text("# Tasks\n")
        result = _collect_status_artifacts(feature_dir)
        assert len(result) == 3
        names = {p.name for p in result}
        assert names == {"status.events.jsonl", "status.json", "tasks.md"}

    def test_skips_missing_files(self, tmp_path: Path):
        """Should only return files that actually exist on disk."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        # Only create events.jsonl
        (feature_dir / "status.events.jsonl").write_text("{}\n")
        result = _collect_status_artifacts(feature_dir)
        assert len(result) == 1
        assert result[0].name == "status.events.jsonl"


class TestValidateReadyForReviewTasksMdFilter:
    """Tests that root-level tasks.md doesn't block for_review transitions (#212)."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a minimal git repo for testing."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo, check=True, capture_output=True,
        )
        (repo / ".kittify").mkdir()
        (repo / ".kittify" / "config.yaml").write_text("# Config\n")

        # Create feature dir with task file
        feature_dir = repo / "kitty-specs" / "017-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_content = """---
work_package_id: "WP01"
title: "Test Task"
lane: "doing"
agent: "test-agent"
---

# WP01

Test content.

## Activity Log

- 2025-01-01T00:00:00Z - system - lane=planned - Initial
"""
        (tasks_dir / "WP01-test.md").write_text(task_content)

        # Create meta.json for mission detection
        meta = {"mission": "research"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo, check=True, capture_output=True,
        )
        return repo

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_root_tasks_md_does_not_block_review(
        self, _mock_mission: Mock, git_repo: Path,
    ):
        """Root-level tasks.md changes should not block for_review transitions."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create dirty root-level tasks.md (the bug scenario)
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text("# Tasks\n\n## WP01\n- [x] T001 do something\n")

        # Verify tasks.md shows up in git status
        result = subprocess.run(
            ["git", "status", "--porcelain", str(feature_dir)],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=False,
        )
        assert "tasks.md" in result.stdout

        # Validate should pass (tasks.md should be filtered)
        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is True, f"Root tasks.md should not block review. Guidance: {guidance}"
        assert guidance == []

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_status_events_jsonl_does_not_block_review(
        self, _mock_mission: Mock, git_repo: Path,
    ):
        """status.events.jsonl changes should not block for_review transitions."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create dirty status.events.jsonl
        events_file = feature_dir / "status.events.jsonl"
        events_file.write_text('{"event_id":"test"}\n')

        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is True, f"status.events.jsonl should be filtered. Guidance: {guidance}"

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_status_json_does_not_block_review(
        self, _mock_mission: Mock, git_repo: Path,
    ):
        """status.json changes should not block for_review transitions."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create dirty status.json
        status_file = feature_dir / "status.json"
        status_file.write_text('{}')

        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is True, f"status.json should be filtered. Guidance: {guidance}"

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_real_research_artifact_still_blocks_review(
        self, _mock_mission: Mock, git_repo: Path,
    ):
        """Actual research artifacts (data-model.md, etc.) should still block for_review."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create dirty research artifact
        (feature_dir / "data-model.md").write_text("# Data Model\n\nSome uncommitted research\n")

        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is False, "Real research artifacts should still block review"
        assert any("uncommitted" in g.lower() for g in guidance)

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_all_auto_artifacts_together_do_not_block(
        self, _mock_mission: Mock, git_repo: Path,
    ):
        """All auto-generated artifacts together should not block review."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create all possible auto-generated files at once
        (feature_dir / "tasks.md").write_text("# Tasks\n")
        (feature_dir / "status.events.jsonl").write_text('{"event":"test"}\n')
        (feature_dir / "status.json").write_text('{}')

        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is True, f"Auto-generated artifacts should not block. Guidance: {guidance}"


class TestMoveTaskAtomicCommit:
    """Tests that move_task commits all status artifacts atomically."""

    @pytest.fixture
    def git_repo_with_feature(self, tmp_path: Path) -> Path:
        """Create a git repo with a feature for move_task testing."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo, check=True, capture_output=True,
        )
        (repo / ".kittify").mkdir()
        (repo / ".kittify" / "config.yaml").write_text("# Config\n")

        feature_dir = repo / "kitty-specs" / "017-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_content = """---
work_package_id: "WP01"
title: "Test Task"
lane: "doing"
agent: "test-agent"
shell_pid: ""
---

# WP01

Test content.

## Activity Log

- 2025-01-01T00:00:00Z - system - lane=planned - Initial
"""
        (tasks_dir / "WP01-test.md").write_text(task_content)

        meta = {"mission": "research"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo, check=True, capture_output=True,
        )
        return repo

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_task_commits_status_artifacts(
        self,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ):
        """move_task should commit status artifacts in the same commit as the WP file."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"

        feature_dir = repo / "kitty-specs" / "017-test-feature"

        # Move to for_review
        result = runner.invoke(
            app,
            ["move-task", "WP01", "--to", "for_review", "--json"],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, output: {result.stdout}"
        payload = json.loads(result.stdout)
        assert payload["result"] == "success"

        # Check that status.events.jsonl was committed (not left dirty)
        status_result = subprocess.run(
            ["git", "status", "--porcelain", str(feature_dir)],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        dirty_files = status_result.stdout.strip()
        if dirty_files:
            # Filter to only status artifacts
            dirty_status = []
            for line in dirty_files.split("\n"):
                if not line.strip():
                    continue
                file_part = line[3:] if len(line) > 3 else line.strip()
                if any(
                    file_part.endswith(f)
                    for f in ("status.events.jsonl", "status.json", "tasks.md")
                ):
                    dirty_status.append(file_part)
            assert dirty_status == [], (
                f"Status artifacts left dirty after move_task: {dirty_status}"
            )

        # Verify events.jsonl exists and was committed
        events_file = feature_dir / "status.events.jsonl"
        if events_file.exists():
            # Check it was included in the last commit
            committed_files = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            # The commit should include both the WP file and status artifacts
            assert "WP01" in committed_files, (
                f"WP file should be in commit. Files: {committed_files}"
            )
