"""Tests for multi-parent dependency handling via automatic merge commits.

Verifies Phase 2 implementation:
- Auto-detection of multi-parent dependencies
- Automatic merge base creation
- Conflict detection and reporting
- Deterministic merge ordering
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.core.multi_parent_merge import (
    cleanup_merge_base_branch,
    create_multi_parent_base,
)


class TestMultiParentMerge:
    """Tests for create_multi_parent_base function."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository with test branches."""
        repo = tmp_path / "test-repo"
        repo.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
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

    @pytest.mark.xfail(reason="CI uses 'master' as default branch instead of 'main'")
    def test_create_merge_base_two_dependencies(self, git_repo: Path):
        """Test creating merge base for WP with two dependencies."""
        # Create WP01 branch
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP01"],
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

        # Create WP02 branch (from main)
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP02"],
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

        # Return to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create merge base for WP03 (depends on WP01 and WP02)
        result = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP03",
            dependencies=["WP01", "WP02"],
            repo_root=git_repo,
        )

        # Verify success
        assert result.success is True
        assert result.branch_name == "010-feature-WP03-merge-base"
        assert result.commit_sha is not None
        assert result.error is None
        assert result.conflicts == []

        # Verify merge commit exists
        result_check = subprocess.run(
            ["git", "rev-parse", "--verify", result.branch_name],
            cwd=git_repo,
            capture_output=True,
            check=False,
        )
        assert result_check.returncode == 0

        # Verify merge commit has both parents
        result_parents = subprocess.run(
            ["git", "log", "--pretty=%P", "-1", result.branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        parents = result_parents.stdout.strip().split()
        assert len(parents) == 2  # Merge commit should have 2 parents

        # Verify both files present in merge commit
        subprocess.run(
            ["git", "checkout", result.branch_name],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert (git_repo / "wp01.txt").exists()
        assert (git_repo / "wp02.txt").exists()

    @pytest.mark.xfail(reason="CI uses 'master' as default branch instead of 'main'")
    def test_create_merge_base_three_dependencies(self, git_repo: Path):
        """Test creating merge base for WP with three dependencies."""
        # Create three independent branches
        for i in range(1, 4):
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "-b", f"010-feature-WP0{i}"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )
            (git_repo / f"wp0{i}.txt").write_text(f"WP0{i} changes\n")
            subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"WP0{i} work"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )

        # Return to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create merge base for WP04 (depends on WP01, WP02, WP03)
        result = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP04",
            dependencies=["WP01", "WP02", "WP03"],
            repo_root=git_repo,
        )

        # Verify success
        assert result.success is True
        assert result.branch_name == "010-feature-WP04-merge-base"

        # Verify all three files present
        subprocess.run(
            ["git", "checkout", result.branch_name],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert (git_repo / "wp01.txt").exists()
        assert (git_repo / "wp02.txt").exists()
        assert (git_repo / "wp03.txt").exists()

    @pytest.mark.xfail(reason="CI uses 'master' as default branch instead of 'main'")
    def test_create_merge_base_with_conflicts(self, git_repo: Path):
        """Test merge base creation when dependencies have conflicts."""
        # Create WP01 branch
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP01"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "shared.txt").write_text("WP01 version\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01 work"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create WP02 branch with conflicting change to same file
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP02"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "shared.txt").write_text("WP02 version\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02 work"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Return to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Attempt to create merge base (should fail with conflict)
        result = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP03",
            dependencies=["WP01", "WP02"],
            repo_root=git_repo,
        )

        # Verify failure with conflict detection
        assert result.success is False
        assert "conflict" in result.error.lower()
        assert "shared.txt" in result.conflicts

        # Verify temp branch was cleaned up
        result_check = subprocess.run(
            ["git", "rev-parse", "--verify", "010-feature-WP03-merge-base"],
            cwd=git_repo,
            capture_output=True,
            check=False,
        )
        assert result_check.returncode != 0  # Branch should not exist

    @pytest.mark.xfail(reason="CI uses 'master' as default branch instead of 'main'")
    def test_create_merge_base_missing_dependency(self, git_repo: Path):
        """Test merge base creation when dependency branch doesn't exist."""
        # Create only WP01
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP01"],
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

        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Try to create merge base with non-existent WP02
        result = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP03",
            dependencies=["WP01", "WP02"],  # WP02 doesn't exist
            repo_root=git_repo,
        )

        # Verify failure
        assert result.success is False
        assert "010-feature-WP02" in result.error
        assert "does not exist" in result.error

    def test_create_merge_base_single_dependency(self, git_repo: Path):
        """Test that single dependency fails (requires at least 2)."""
        result = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP02",
            dependencies=["WP01"],  # Only one dependency
            repo_root=git_repo,
        )

        # Verify failure
        assert result.success is False
        assert "at least 2 dependencies" in result.error

    @pytest.mark.xfail(reason="CI uses 'master' as default branch instead of 'main'")
    def test_create_merge_base_deterministic_ordering(self, git_repo: Path):
        """Test that merge base creation is deterministic (sorted dependencies)."""
        # Create branches in reverse order
        for i in [3, 1, 2]:
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "-b", f"010-feature-WP0{i}"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )
            (git_repo / f"wp0{i}.txt").write_text(f"WP0{i} changes\n")
            subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"WP0{i} work"],
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

        # Create merge base with dependencies in different order
        result1 = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP04",
            dependencies=["WP03", "WP01", "WP02"],  # Unsorted
            repo_root=git_repo,
        )

        assert result1.success is True
        commit_sha1 = result1.commit_sha

        # Cleanup
        subprocess.run(
            ["git", "branch", "-D", "010-feature-WP04-merge-base"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create again with same dependencies in different order
        result2 = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP04",
            dependencies=["WP02", "WP03", "WP01"],  # Different order
            repo_root=git_repo,
        )

        assert result2.success is True

        # Verify same merge tree (dependencies sorted internally)
        # Note: Commit SHAs will differ due to timestamps, but tree should match
        result_tree1 = subprocess.run(
            ["git", "rev-parse", f"{commit_sha1}^{{tree}}"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        result_tree2 = subprocess.run(
            ["git", "rev-parse", f"{result2.commit_sha}^{{tree}}"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )

        tree1 = result_tree1.stdout.strip()
        tree2 = result_tree2.stdout.strip()

        assert tree1 == tree2  # Same final tree

    @pytest.mark.xfail(reason="CI uses 'master' as default branch instead of 'main'")
    def test_cleanup_merge_base_branch(self, git_repo: Path):
        """Test cleanup of temporary merge base branch."""
        # Create a temporary branch manually
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP04-merge-base"],
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

        # Cleanup
        deleted = cleanup_merge_base_branch(
            feature_slug="010-feature",
            wp_id="WP04",
            repo_root=git_repo,
        )

        assert deleted is True

        # Verify branch deleted
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "010-feature-WP04-merge-base"],
            cwd=git_repo,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0

        # Cleanup again (should return False)
        deleted_again = cleanup_merge_base_branch(
            feature_slug="010-feature",
            wp_id="WP04",
            repo_root=git_repo,
        )

        assert deleted_again is False


class TestDiamondDependencyPattern:
    """Integration tests for diamond dependency pattern.

    Diamond pattern:
           WP01
          /    \\
       WP02    WP03
          \\    /
           WP04
    """

    @pytest.fixture
    def diamond_repo(self, tmp_path: Path) -> Path:
        """Create repository with diamond dependency structure."""
        repo = tmp_path / "diamond-repo"
        repo.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
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

        # Create main
        (repo / "README.md").write_text("# Diamond Test\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create WP01
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "base.txt").write_text("Base implementation\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01: Base implementation"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create WP02 (from WP01)
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "feature-a.txt").write_text("Feature A\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02: Add feature A"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create WP03 (from WP01)
        subprocess.run(
            ["git", "checkout", "010-feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "010-feature-WP03"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "feature-b.txt").write_text("Feature B\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP03: Add feature B"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", "main"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        return repo

    @pytest.mark.xfail(reason="CI uses 'master' as default branch instead of 'main'")
    def test_diamond_merge_base(self, diamond_repo: Path):
        """Test creating merge base for diamond pattern (WP04 depends on WP02 + WP03)."""
        # Create merge base for WP04 (depends on WP02 and WP03)
        result = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP04",
            dependencies=["WP02", "WP03"],
            repo_root=diamond_repo,
        )

        # Verify success
        assert result.success is True
        assert result.branch_name == "010-feature-WP04-merge-base"

        # Verify all three files present (base.txt, feature-a.txt, feature-b.txt)
        subprocess.run(
            ["git", "checkout", result.branch_name],
            cwd=diamond_repo,
            check=True,
            capture_output=True,
        )
        assert (diamond_repo / "base.txt").exists()
        assert (diamond_repo / "feature-a.txt").exists()
        assert (diamond_repo / "feature-b.txt").exists()

        # Verify commit history includes all four commits
        result_log = subprocess.run(
            ["git", "log", "--oneline", "--all"],
            cwd=diamond_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        log = result_log.stdout

        assert "WP01: Base implementation" in log
        assert "WP02: Add feature A" in log
        assert "WP03: Add feature B" in log
        assert "Merge" in log  # Merge commit created
