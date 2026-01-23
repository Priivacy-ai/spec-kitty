"""Unit tests for merge conflict forecasting module.

Tests the conflict prediction logic for merge dry-run:
- Status file pattern matching
- File-to-WP mapping from git diff
- Conflict prediction logic
- ConflictPrediction dataclass
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.merge.forecast import (
    ConflictPrediction,
    build_file_wp_mapping,
    is_status_file,
    predict_conflicts,
)


class TestIsStatusFile:
    """Tests for is_status_file pattern matching."""

    def test_matches_wp_task_file(self):
        """Test matching WP task files in standard structure."""
        assert is_status_file("kitty-specs/017-feature/tasks/WP01.md") is True
        assert is_status_file("kitty-specs/010-workspace/tasks/WP02.md") is True
        assert is_status_file("kitty-specs/005-my-feature/tasks/WP12.md") is True

    def test_matches_main_tasks_file(self):
        """Test matching main tasks.md file."""
        assert is_status_file("kitty-specs/017-feature/tasks.md") is True
        assert is_status_file("kitty-specs/010-workspace/tasks.md") is True

    def test_matches_nested_patterns(self):
        """Test matching nested directory patterns."""
        assert is_status_file("kitty-specs/features/017/tasks/WP01.md") is True
        assert is_status_file("kitty-specs/features/017/tasks.md") is True

    def test_non_status_file_returns_false(self):
        """Test that non-status files return False."""
        assert is_status_file("src/main.py") is False
        assert is_status_file("README.md") is False
        assert is_status_file("kitty-specs/017-feature/spec.md") is False
        assert is_status_file("kitty-specs/017-feature/plan.md") is False
        assert is_status_file("tests/test_something.py") is False


class TestBuildFileWPMapping:
    """Tests for build_file_wp_mapping function."""

    def test_builds_mapping_for_independent_wps(self, tmp_path: Path):
        """Test building mapping when WPs modify different files."""
        # Create git repo
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create initial commit on main
        (repo / "README.md").write_text("main")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # Create WP01 branch modifying file1.txt
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "file1.txt").write_text("WP01 changes")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create WP02 branch modifying file2.txt
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "file2.txt").write_text("WP02 changes")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [
            (repo, "WP01", "feature-WP01"),
            (repo, "WP02", "feature-WP02"),
        ]

        mapping = build_file_wp_mapping(wp_workspaces, main_branch, repo)

        assert "file1.txt" in mapping
        assert mapping["file1.txt"] == ["WP01"]
        assert "file2.txt" in mapping
        assert mapping["file2.txt"] == ["WP02"]

    def test_detects_overlapping_file_modifications(self, tmp_path: Path):
        """Test detecting when multiple WPs modify the same file."""
        # Create git repo
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        (repo / "shared.txt").write_text("original")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # WP01 modifies shared.txt
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "shared.txt").write_text("WP01 changes")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # WP02 also modifies shared.txt
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "shared.txt").write_text("WP02 changes")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [
            (repo, "WP01", "feature-WP01"),
            (repo, "WP02", "feature-WP02"),
        ]

        mapping = build_file_wp_mapping(wp_workspaces, main_branch, repo)

        assert "shared.txt" in mapping
        assert set(mapping["shared.txt"]) == {"WP01", "WP02"}

    def test_handles_wp_with_no_changes(self, tmp_path: Path):
        """Test handling WP branch with no changes."""
        # Create git repo
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        (repo / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # Create empty WP branch
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [(repo, "WP01", "feature-WP01")]

        mapping = build_file_wp_mapping(wp_workspaces, main_branch, repo)

        # Empty branch should produce empty mapping (or not appear)
        assert len(mapping) == 0 or "WP01" not in str(mapping)

    def test_git_diff_failure_skips_wp(self, tmp_path: Path):
        """Test that git diff failure skips the WP gracefully."""
        repo = tmp_path / "repo"
        repo.mkdir()

        # Create git repo but provide invalid branch name
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        (repo / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # Provide non-existent branch
        wp_workspaces = [(repo, "WP01", "nonexistent-branch")]

        mapping = build_file_wp_mapping(wp_workspaces, main_branch, repo)

        # Should return empty mapping without crashing
        assert mapping == {}


class TestPredictConflicts:
    """Tests for predict_conflicts function."""

    def test_no_conflicts_independent_files(self, tmp_path: Path):
        """Test no conflicts predicted when WPs modify different files."""
        # Create git repo with independent WP branches
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        (repo / "README.md").write_text("main")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # WP01 modifies file1.txt
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "file1.txt").write_text("WP01")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # WP02 modifies file2.txt
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "file2.txt").write_text("WP02")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [
            (repo, "WP01", "feature-WP01"),
            (repo, "WP02", "feature-WP02"),
        ]

        predictions = predict_conflicts(wp_workspaces, main_branch, repo)

        assert len(predictions) == 0

    def test_predicts_content_conflicts(self, tmp_path: Path):
        """Test predicting conflicts when multiple WPs modify same file."""
        # Create git repo
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        (repo / "shared.txt").write_text("original")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # WP01 modifies shared.txt
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "shared.txt").write_text("WP01 version")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # WP02 modifies shared.txt
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "shared.txt").write_text("WP02 version")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [
            (repo, "WP01", "feature-WP01"),
            (repo, "WP02", "feature-WP02"),
        ]

        predictions = predict_conflicts(wp_workspaces, main_branch, repo)

        assert len(predictions) == 1
        assert predictions[0].file_path == "shared.txt"
        assert set(predictions[0].conflicting_wps) == {"WP01", "WP02"}

    def test_marks_status_files_auto_resolvable(self, tmp_path: Path):
        """Test that status files are marked as auto-resolvable."""
        # Create git repo
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create initial status file
        status_dir = repo / "kitty-specs" / "017-feature" / "tasks"
        status_dir.mkdir(parents=True)
        (status_dir / "WP01.md").write_text("---\nlane: planned\n---")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # WP01 updates status
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (status_dir / "WP01.md").write_text("---\nlane: doing\n---")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01 status"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # WP02 also updates status (simulating concurrent work)
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (status_dir / "WP01.md").write_text("---\nlane: for_review\n---")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02 status"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [
            (repo, "WP01", "feature-WP01"),
            (repo, "WP02", "feature-WP02"),
        ]

        predictions = predict_conflicts(wp_workspaces, main_branch, repo)

        assert len(predictions) == 1
        pred = predictions[0]
        assert pred.file_path == "kitty-specs/017-feature/tasks/WP01.md"
        assert pred.is_status_file is True
        assert pred.auto_resolvable is True

    def test_confidence_levels(self, tmp_path: Path):
        """Test that predictions have confidence levels."""
        # Create git repo with conflict
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        (repo / "shared.txt").write_text("original")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # Create conflicting WPs
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "shared.txt").write_text("WP01")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "shared.txt").write_text("WP02")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [
            (repo, "WP01", "feature-WP01"),
            (repo, "WP02", "feature-WP02"),
        ]

        predictions = predict_conflicts(wp_workspaces, main_branch, repo)

        assert len(predictions) == 1
        assert predictions[0].confidence in ["certain", "likely", "possible"]


class TestConflictPrediction:
    """Tests for ConflictPrediction dataclass."""

    def test_auto_resolvable_property(self):
        """Test auto_resolvable property for status files."""
        # Status file should be auto-resolvable
        pred1 = ConflictPrediction(
            file_path="kitty-specs/017-feature/tasks/WP01.md",
            conflicting_wps=["WP01", "WP02"],
            is_status_file=True,
            confidence="possible",
        )
        assert pred1.auto_resolvable is True

        # Regular file should not be auto-resolvable
        pred2 = ConflictPrediction(
            file_path="src/main.py",
            conflicting_wps=["WP01", "WP02"],
            is_status_file=False,
            confidence="possible",
        )
        assert pred2.auto_resolvable is False

    def test_prediction_dataclass(self):
        """Test ConflictPrediction dataclass creation."""
        pred = ConflictPrediction(
            file_path="shared.txt",
            conflicting_wps=["WP01", "WP02", "WP03"],
            is_status_file=False,
            confidence="likely",
        )
        assert pred.file_path == "shared.txt"
        assert pred.conflicting_wps == ["WP01", "WP02", "WP03"]
        assert pred.is_status_file is False
        assert pred.confidence == "likely"
        assert pred.auto_resolvable is False
