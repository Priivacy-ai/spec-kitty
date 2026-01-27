"""Tests for empty branch detection in multi-parent merge.

Verifies that warnings are displayed when dependency branches
have no commits beyond main (empty branches).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.core.multi_parent_merge import create_multi_parent_base


class TestEmptyBranchDetection:
    """Tests for empty branch detection in create_multi_parent_base."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository."""
        repo = tmp_path / "test-repo"
        repo.mkdir()

        # Initialize git repo with explicit branch name
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create initial commit on main
        (repo / "README.md").write_text("# Test Repo\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        return repo

    def test_empty_branch_warning_displayed(self, git_repo: Path, capsys):
        """Should display warning when dependency branch has no commits."""
        # Create first empty branch (points to main)
        subprocess.run(
            ["git", "branch", "017-feature-WP01", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create second branch with commits (needed for multi-parent merge)
        subprocess.run(
            ["git", "checkout", "-b", "017-feature-WP02"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "wp02.txt").write_text("WP02 work\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02 implementation"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Try to create merge-base with one empty dependency and one normal
        result = create_multi_parent_base(
            feature_slug="017-feature",
            wp_id="WP03",
            dependencies=["WP01", "WP02"],
            repo_root=git_repo,
        )

        # Verify warning was printed (to stderr, not stdout)
        captured = capsys.readouterr()
        assert "⚠️  Warning: Dependency branch '017-feature-WP01' has no commits beyond main" in captured.err
        assert "This may indicate incomplete work or uncommitted changes" in captured.err
        assert "The merge-base will not include any work from this branch" in captured.err

        # Result should still succeed (warning is non-blocking)
        assert result.success

    def test_branch_with_commits_no_warning(self, git_repo: Path, capsys):
        """Should not display warning when branches have commits."""
        # Create first branch with commits
        subprocess.run(
            ["git", "checkout", "-b", "017-feature-WP01"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "wp01.txt").write_text("WP01 changes\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01 work"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Switch back to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create second branch with commits
        subprocess.run(
            ["git", "checkout", "-b", "017-feature-WP02"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "wp02.txt").write_text("WP02 changes\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02 work"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Switch back to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create merge-base with both branches
        result = create_multi_parent_base(
            feature_slug="017-feature",
            wp_id="WP03",
            dependencies=["WP01", "WP02"],
            repo_root=git_repo,
        )

        # Verify no warning was printed (check stderr since warnings go there)
        captured = capsys.readouterr()
        assert "⚠️  Warning:" not in captured.err
        assert result.success

    def test_multiple_empty_branches_multiple_warnings(self, git_repo: Path, capsys):
        """Should display warning for each empty branch."""
        # Create three branches: two empty, one with commits
        subprocess.run(
            ["git", "branch", "017-feature-WP01", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "branch", "017-feature-WP02", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # WP03 has commits
        subprocess.run(
            ["git", "checkout", "-b", "017-feature-WP03"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "wp03.txt").write_text("WP03 changes\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP03 work"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create merge-base with all three dependencies
        result = create_multi_parent_base(
            feature_slug="017-feature",
            wp_id="WP04",
            dependencies=["WP01", "WP02", "WP03"],
            repo_root=git_repo,
        )

        # Verify warnings for empty branches only (warnings go to stderr)
        captured = capsys.readouterr()
        assert captured.err.count("⚠️  Warning:") == 2
        assert "017-feature-WP01" in captured.err
        assert "017-feature-WP02" in captured.err
        # WP03 should not have warning (it has commits)
        assert result.success

    def test_empty_branch_merge_still_succeeds(self, git_repo: Path):
        """Merge should succeed even with empty branches (warning only)."""
        # Create empty branch
        subprocess.run(
            ["git", "branch", "017-feature-WP01", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create second branch with commits (needed for multi-parent merge)
        subprocess.run(
            ["git", "checkout", "-b", "017-feature-WP02"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "wp02.txt").write_text("WP02 work\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02 implementation"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create merge-base (should succeed despite warning about WP01)
        result = create_multi_parent_base(
            feature_slug="017-feature",
            wp_id="WP03",
            dependencies=["WP01", "WP02"],
            repo_root=git_repo,
        )

        # Verify success
        assert result.success
        assert result.branch_name == "017-feature-WP03-merge-base"
        assert result.commit_sha is not None
        assert result.error is None

    def test_mixed_empty_and_normal_branches(self, git_repo: Path, capsys):
        """Should handle mix of empty and normal branches correctly."""
        # Create WP01 with commits
        subprocess.run(
            ["git", "checkout", "-b", "017-feature-WP01"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "wp01.txt").write_text("WP01 work\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01 implementation"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create WP02 empty (forgot to commit)
        subprocess.run(
            ["git", "branch", "017-feature-WP02", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create merge-base
        result = create_multi_parent_base(
            feature_slug="017-feature",
            wp_id="WP03",
            dependencies=["WP01", "WP02"],
            repo_root=git_repo,
        )

        # Should succeed with warning for WP02 only (warnings go to stderr)
        captured = capsys.readouterr()
        assert result.success
        assert "017-feature-WP02" in captured.err
        assert captured.err.count("⚠️  Warning:") == 1
