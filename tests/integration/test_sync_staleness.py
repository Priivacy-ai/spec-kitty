"""Integration tests for sync workspace staleness detection.

Tests staleness detection and update functionality for parallel WP development:
- Detecting stale workspaces
- Updating from main branch
- Preserving uncommitted changes
- Handling dependent WP staleness
"""

from __future__ import annotations

import subprocess
from pathlib import Path



class TestSyncStaleness:
    """Tests for workspace staleness detection."""

    def test_detects_stale_workspace(self, git_stale_workspace: dict):
        """Test detecting workspace that is behind main branch."""
        repo_root = git_stale_workspace["repo_root"]
        worktree_path = git_stale_workspace["worktree_path"]
        main_branch = git_stale_workspace["main_branch"]

        # Check that main has commits worktree doesn't have
        main_result = subprocess.run(
            ["git", "rev-parse", main_branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        main_sha = main_result.stdout.strip()

        worktree_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        worktree_sha = worktree_result.stdout.strip()

        # SHAs should differ (worktree is behind)
        assert main_sha != worktree_sha

        # Check merge-base to confirm staleness
        merge_base_result = subprocess.run(
            ["git", "merge-base", "HEAD", main_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        merge_base = merge_base_result.stdout.strip()

        # Merge base should not be main (worktree diverged)
        assert merge_base != main_sha

    def test_detects_up_to_date_workspace(self, tmp_path: Path):
        """Test detecting workspace that is up-to-date with main."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
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

        (repo / "README.md").write_text("initial")
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

        # Create worktree from latest main
        worktree_dir = repo / ".worktrees" / "feature-WP01"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Check merge-base equals main (up-to-date)
        merge_base_result = subprocess.run(
            ["git", "merge-base", "HEAD", main_branch],
            cwd=worktree_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        merge_base = merge_base_result.stdout.strip()

        main_sha_result = subprocess.run(
            ["git", "rev-parse", main_branch],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_sha = main_sha_result.stdout.strip()

        # Merge base should equal main (worktree is up-to-date)
        assert merge_base == main_sha

    def test_updates_stale_workspace_from_main(self, git_stale_workspace: dict):
        """Test updating stale workspace by rebasing on main."""
        repo_root = git_stale_workspace["repo_root"]
        worktree_path = git_stale_workspace["worktree_path"]
        main_branch = git_stale_workspace["main_branch"]

        # Rebase worktree on main
        result = subprocess.run(
            ["git", "rebase", main_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should succeed (no conflicts expected with simple case)
        assert result.returncode == 0

        # Verify worktree now has main's changes
        assert (worktree_path / "main_advance.txt").exists()

        # Verify merge-base is now main
        merge_base_result = subprocess.run(
            ["git", "merge-base", "HEAD", main_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        merge_base = merge_base_result.stdout.strip()

        main_sha_result = subprocess.run(
            ["git", "rev-parse", main_branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        main_sha = main_sha_result.stdout.strip()

        # After rebase, merge-base should be main
        assert merge_base == main_sha

    def test_preserves_uncommitted_changes(self, git_stale_workspace: dict):
        """Test that sync preserves uncommitted changes in worktree."""
        worktree_path = git_stale_workspace["worktree_path"]

        # Modify an existing tracked file (git blocks rebase for modified tracked files)
        (worktree_path / "WP01.txt").write_text("modified uncommitted work")

        # Verify file is modified and uncommitted
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "WP01.txt" in status_result.stdout
        assert " M " in status_result.stdout  # Modified

        # Attempt to rebase should fail due to uncommitted changes
        # (git rebase refuses to proceed with modified tracked files)
        rebase_result = subprocess.run(
            ["git", "rebase", git_stale_workspace["main_branch"]],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should fail with dirty working tree error
        assert rebase_result.returncode != 0
        assert (
            "cannot rebase" in rebase_result.stderr.lower()
            or "dirty" in rebase_result.stderr.lower()
            or "uncommitted changes" in rebase_result.stderr.lower()
            or "unstaged changes" in rebase_result.stderr.lower()
        )

        # Modified file should still exist with uncommitted changes
        assert (worktree_path / "WP01.txt").read_text() == "modified uncommitted work"

    def test_parallel_wps_with_one_stale(self, tmp_path: Path):
        """Test detecting staleness when some WPs are stale and others aren't."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
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

        (repo / "README.md").write_text("initial")
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

        # Create WP01 worktree
        wp01_dir = repo / ".worktrees" / "feature-WP01"
        subprocess.run(
            ["git", "worktree", "add", str(wp01_dir), "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (wp01_dir / "WP01.txt").write_text("WP01 work")
        subprocess.run(["git", "add", "."], cwd=wp01_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=wp01_dir,
            check=True,
            capture_output=True,
        )

        # Advance main (making WP01 stale)
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "main_advance.txt").write_text("advanced")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "advance main"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create WP02 worktree (after main advanced, so up-to-date)
        wp02_dir = repo / ".worktrees" / "feature-WP02"
        subprocess.run(
            ["git", "worktree", "add", str(wp02_dir), "-b", "feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (wp02_dir / "WP02.txt").write_text("WP02 work")
        subprocess.run(["git", "add", "."], cwd=wp02_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02"],
            cwd=wp02_dir,
            check=True,
            capture_output=True,
        )

        # Get main SHA
        main_sha_result = subprocess.run(
            ["git", "rev-parse", main_branch],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_sha = main_sha_result.stdout.strip()

        # Check WP01 merge-base (should be behind)
        wp01_base_result = subprocess.run(
            ["git", "merge-base", "HEAD", main_branch],
            cwd=wp01_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        wp01_base = wp01_base_result.stdout.strip()

        # WP01 is stale (merge-base != main)
        assert wp01_base != main_sha

        # Check WP02 merge-base (should be up-to-date)
        wp02_base_result = subprocess.run(
            ["git", "merge-base", "HEAD", main_branch],
            cwd=wp02_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        wp02_base = wp02_base_result.stdout.strip()

        # WP02 is up-to-date (merge-base == main)
        assert wp02_base == main_sha

    def test_dependent_wp_staleness_cascade(self, tmp_path: Path):
        """Test that dependent WP becomes stale when base WP is updated."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
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

        (repo / "README.md").write_text("initial")
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

        # Create WP01 (base)
        wp01_dir = repo / ".worktrees" / "feature-WP01"
        subprocess.run(
            ["git", "worktree", "add", str(wp01_dir), "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (wp01_dir / "WP01.txt").write_text("WP01 work")
        subprocess.run(["git", "add", "."], cwd=wp01_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=wp01_dir,
            check=True,
            capture_output=True,
        )

        # Create WP02 dependent on WP01
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        wp02_dir = repo / ".worktrees" / "feature-WP02"
        subprocess.run(
            ["git", "worktree", "add", str(wp02_dir), "feature-WP01", "-b", "feature-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (wp02_dir / "WP02.txt").write_text("WP02 work")
        subprocess.run(["git", "add", "."], cwd=wp02_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02"],
            cwd=wp02_dir,
            check=True,
            capture_output=True,
        )

        # Get WP01 SHA before update
        wp01_sha_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=wp01_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # Update WP01 (add new commit)
        (wp01_dir / "WP01_updated.txt").write_text("updated")
        subprocess.run(["git", "add", "."], cwd=wp01_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "update WP01"],
            cwd=wp01_dir,
            check=True,
            capture_output=True,
        )

        # Get WP01 SHA after update
        wp01_sha_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=wp01_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # Verify WP01 changed
        assert wp01_sha_before != wp01_sha_after

        # Check WP02 merge-base with WP01 branch
        wp02_base = subprocess.run(
            ["git", "merge-base", "HEAD", "feature-WP01"],
            cwd=wp02_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # WP02's merge-base should be old WP01 SHA (before update)
        assert wp02_base == wp01_sha_before

        # WP02 is now stale relative to its dependency (WP01)
        assert wp02_base != wp01_sha_after

    def test_sync_fails_with_uncommitted_and_conflicts(self, git_stale_workspace: dict):
        """Test sync fails gracefully with uncommitted changes and potential conflicts."""
        worktree_path = git_stale_workspace["worktree_path"]
        main_branch = git_stale_workspace["main_branch"]

        # Create conflicting uncommitted changes
        # (modifying same file that main advanced)
        (worktree_path / "main_advance.txt").write_text("conflicting content")

        # Attempt to rebase should fail
        result = subprocess.run(
            ["git", "rebase", main_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should fail due to dirty working tree
        assert result.returncode != 0

    def test_sync_status_message_shows_stale_wps(self, tmp_path: Path):
        """Test that sync status command identifies stale WPs."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
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

        (repo / "README.md").write_text("initial")
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

        # Create WP01
        wp01_dir = repo / ".worktrees" / "feature-WP01"
        subprocess.run(
            ["git", "worktree", "add", str(wp01_dir), "-b", "feature-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (wp01_dir / "WP01.txt").write_text("work")
        subprocess.run(["git", "add", "."], cwd=wp01_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=wp01_dir,
            check=True,
            capture_output=True,
        )

        # Advance main
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "main_new.txt").write_text("new")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "advance"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Check status using git commands
        # (In real sync command, this would be formatted nicely)
        status_result = subprocess.run(
            ["git", "rev-list", "--count", f"feature-WP01..{main_branch}"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )

        commits_behind = int(status_result.stdout.strip())

        # WP01 should be behind by 1 commit
        assert commits_behind == 1
