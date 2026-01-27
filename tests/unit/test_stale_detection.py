"""
Unit tests for stale work package detection.

Tests the dynamic default branch detection and staleness checks.
"""

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from specify_cli.core.stale_detection import (
    StaleCheckResult,
    check_wp_staleness,
    get_default_branch,
    get_last_meaningful_commit_time,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repository."""
    repo = tmp_path / "repo"
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

    # Create initial commit
    (repo / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


@pytest.fixture
def git_repo_with_main(git_repo: Path) -> Path:
    """Create a git repository with 'main' as default branch."""
    # Rename to main if not already
    subprocess.run(
        ["git", "branch", "-M", "main"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    return git_repo


@pytest.fixture
def git_repo_with_master(git_repo: Path) -> Path:
    """Create a git repository with 'master' as default branch."""
    # Rename to master
    subprocess.run(
        ["git", "branch", "-M", "master"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    return git_repo


@pytest.fixture
def git_repo_with_develop(git_repo: Path) -> Path:
    """Create a git repository with 'develop' as default branch."""
    # Rename to develop
    subprocess.run(
        ["git", "branch", "-M", "develop"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    return git_repo


def test_get_default_branch_main(git_repo_with_main: Path):
    """Test detecting 'main' as default branch."""
    result = get_default_branch(git_repo_with_main)
    assert result == "main"


def test_get_default_branch_master(git_repo_with_master: Path):
    """Test detecting 'master' as default branch."""
    result = get_default_branch(git_repo_with_master)
    assert result == "master"


def test_get_default_branch_develop(git_repo_with_develop: Path):
    """Test detecting 'develop' as default branch."""
    result = get_default_branch(git_repo_with_develop)
    assert result == "develop"


def test_get_default_branch_with_origin_head(git_repo_with_main: Path):
    """Test detecting default branch from origin HEAD when available."""
    # Create a bare remote repo
    remote = git_repo_with_main.parent / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
    )

    # Add remote and push
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote)],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    # Now origin/HEAD should be set
    result = get_default_branch(git_repo_with_main)
    assert result == "main"


def test_get_default_branch_no_origin(git_repo_with_main: Path):
    """Test fallback when no remote origin exists."""
    # No remote configured - should still detect 'main'
    result = get_default_branch(git_repo_with_main)
    assert result == "main"


def test_get_last_meaningful_commit_time_fresh_worktree_main(git_repo_with_main: Path):
    """Test that fresh worktree with 'main' branch is NOT stale."""
    # Create a feature branch (simulating worktree)
    subprocess.run(
        ["git", "checkout", "-b", "feature-WP01"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    # No commits on this branch yet
    last_commit, has_own_commits = get_last_meaningful_commit_time(git_repo_with_main)

    assert last_commit is None
    assert has_own_commits is False


def test_get_last_meaningful_commit_time_fresh_worktree_master(
    git_repo_with_master: Path,
):
    """Test that fresh worktree with 'master' branch is NOT stale."""
    # Create a feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature-WP01"],
        cwd=git_repo_with_master,
        check=True,
        capture_output=True,
    )

    # No commits on this branch yet
    last_commit, has_own_commits = get_last_meaningful_commit_time(git_repo_with_master)

    assert last_commit is None
    assert has_own_commits is False


def test_get_last_meaningful_commit_time_with_commits_main(git_repo_with_main: Path):
    """Test commit time detection with 'main' branch."""
    # Create a feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature-WP01"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    # Make a commit on the feature branch
    (git_repo_with_main / "feature.txt").write_text("Feature work")
    subprocess.run(
        ["git", "add", "."],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    # Should detect the commit
    last_commit, has_own_commits = get_last_meaningful_commit_time(git_repo_with_main)

    assert last_commit is not None
    assert has_own_commits is True
    assert isinstance(last_commit, datetime)


def test_get_last_meaningful_commit_time_with_commits_master(
    git_repo_with_master: Path,
):
    """Test commit time detection with 'master' branch."""
    # Create a feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature-WP01"],
        cwd=git_repo_with_master,
        check=True,
        capture_output=True,
    )

    # Make a commit
    (git_repo_with_master / "feature.txt").write_text("Feature work")
    subprocess.run(
        ["git", "add", "."],
        cwd=git_repo_with_master,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=git_repo_with_master,
        check=True,
        capture_output=True,
    )

    # Should detect the commit
    last_commit, has_own_commits = get_last_meaningful_commit_time(git_repo_with_master)

    assert last_commit is not None
    assert has_own_commits is True


def test_check_wp_staleness_fresh_worktree(git_repo_with_main: Path):
    """Test that fresh worktree is NOT flagged as stale."""
    # Create a feature branch (no commits)
    subprocess.run(
        ["git", "checkout", "-b", "feature-WP01"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    result = check_wp_staleness("WP01", git_repo_with_main, threshold_minutes=10)

    assert result.wp_id == "WP01"
    assert result.is_stale is False
    assert result.last_commit_time is None
    assert result.worktree_exists is True


def test_check_wp_staleness_old_commit(git_repo_with_main: Path):
    """Test that worktree with old commit IS flagged as stale."""
    import os

    # Create a feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature-WP01"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    # Make an old commit (12 hours ago)
    # Need to set both GIT_AUTHOR_DATE and GIT_COMMITTER_DATE
    (git_repo_with_main / "feature.txt").write_text("Old work")
    subprocess.run(
        ["git", "add", "."],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    # Calculate timestamp 12 hours ago as Unix timestamp
    old_timestamp = str(int((datetime.now(timezone.utc) - timedelta(hours=12)).timestamp()))

    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = f"@{old_timestamp}"
    env["GIT_COMMITTER_DATE"] = f"@{old_timestamp}"

    subprocess.run(
        ["git", "commit", "-m", "Old work"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
        env=env,
    )

    result = check_wp_staleness("WP01", git_repo_with_main, threshold_minutes=10)

    assert result.wp_id == "WP01"
    assert result.is_stale is True
    assert result.last_commit_time is not None
    assert result.minutes_since_commit is not None
    assert result.minutes_since_commit > 10
    assert result.worktree_exists is True


def test_check_wp_staleness_recent_commit(git_repo_with_main: Path):
    """Test that worktree with recent commit is NOT stale."""
    import os

    # Create a feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature-WP01"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    # Make a recent commit (2 minutes ago)
    (git_repo_with_main / "feature.txt").write_text("Recent work")
    subprocess.run(
        ["git", "add", "."],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    # Calculate timestamp 2 minutes ago as Unix timestamp
    recent_timestamp = str(int((datetime.now(timezone.utc) - timedelta(minutes=2)).timestamp()))

    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = f"@{recent_timestamp}"
    env["GIT_COMMITTER_DATE"] = f"@{recent_timestamp}"

    subprocess.run(
        ["git", "commit", "-m", "Recent work"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
        env=env,
    )

    result = check_wp_staleness("WP01", git_repo_with_main, threshold_minutes=10)

    assert result.wp_id == "WP01"
    assert result.is_stale is False
    assert result.last_commit_time is not None
    assert result.minutes_since_commit is not None
    assert result.minutes_since_commit < 10
    assert result.worktree_exists is True


def test_check_wp_staleness_nonexistent_worktree(tmp_path: Path):
    """Test that nonexistent worktree is NOT flagged as stale."""
    nonexistent = tmp_path / "nonexistent"

    result = check_wp_staleness("WP01", nonexistent, threshold_minutes=10)

    assert result.wp_id == "WP01"
    assert result.is_stale is False
    assert result.last_commit_time is None
    assert result.worktree_exists is False


def test_stale_detection_with_master_branch_old_commit(git_repo_with_master: Path):
    """Test stale detection works correctly with 'master' branch and old commit."""
    import os

    # Create feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature-WP01"],
        cwd=git_repo_with_master,
        check=True,
        capture_output=True,
    )

    # Make an old commit (>10 minutes ago)
    (git_repo_with_master / "work.txt").write_text("Old work")
    subprocess.run(
        ["git", "add", "."],
        cwd=git_repo_with_master,
        check=True,
        capture_output=True,
    )

    # Calculate timestamp 15 minutes ago as Unix timestamp
    old_timestamp = str(int((datetime.now(timezone.utc) - timedelta(minutes=15)).timestamp()))

    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = f"@{old_timestamp}"
    env["GIT_COMMITTER_DATE"] = f"@{old_timestamp}"

    subprocess.run(
        ["git", "commit", "-m", "Old work"],
        cwd=git_repo_with_master,
        check=True,
        capture_output=True,
        env=env,
    )

    result = check_wp_staleness("WP01", git_repo_with_master, threshold_minutes=10)

    # Should correctly flag as stale based on actual branch commit
    assert result.is_stale is True
    assert result.minutes_since_commit is not None
    assert result.minutes_since_commit > 10


def test_stale_detection_merge_base_failure_graceful(git_repo_with_main: Path):
    """Test graceful handling when merge-base fails."""
    # Create a detached HEAD scenario
    subprocess.run(
        ["git", "checkout", "--detach"],
        cwd=git_repo_with_main,
        check=True,
        capture_output=True,
    )

    result = check_wp_staleness("WP01", git_repo_with_main, threshold_minutes=10)

    # Should NOT crash, should return not stale
    assert result.wp_id == "WP01"
    assert result.is_stale is False
    assert result.worktree_exists is True
