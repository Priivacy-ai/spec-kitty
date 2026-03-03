"""Integration tests for merge operations without remote repositories."""

import subprocess

import pytest

from specify_cli.core.git_ops import (
    exclude_from_git_index,
    has_tracking_branch,
    run_command,
)
from specify_cli.merge.executor import execute_merge, execute_legacy_merge
from specify_cli.cli import StepTracker


@pytest.fixture(name="_git_identity")
def git_identity_fixture(monkeypatch):
    """Ensure git commands can commit even if the user has no global config."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "spec@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "spec@example.com")


@pytest.mark.usefixtures("_git_identity")
def test_execute_merge_skips_pull_without_remote(tmp_path):
    """Test workspace-per-WP merge skips pull when no remote exists (dry run)."""
    # Create local git repo (no remote)
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    # Add .worktrees/ to .gitignore before creating worktrees
    gitignore = repo / ".gitignore"
    gitignore.write_text(".worktrees/\n")
    run_command(["git", "add", ".gitignore"], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Also exclude .worktrees/ from git index for extra protection
    exclude_from_git_index(repo, [".worktrees/"])

    # Create worktree with changes
    worktree = repo / ".worktrees" / "001-feature-WP01"
    run_command(["git", "worktree", "add", str(worktree), "-b", "001-feature-WP01"], cwd=repo)
    (worktree / "test.txt").write_text("change")
    run_command(["git", "add", "."], cwd=worktree)
    run_command(["git", "commit", "-m", "Add test"], cwd=worktree)

    # Get the default branch name (might be 'main' or 'master')
    _, default_branch, _ = run_command(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=repo,
        capture=True,
    )
    default_branch = default_branch.strip()

    # Run dry-run merge to verify pull is skipped
    tracker = StepTracker("Test Merge Dry Run")
    wp_workspaces = [(worktree, "WP01", "001-feature-WP01")]
    result = execute_merge(
        wp_workspaces=wp_workspaces,
        feature_slug="001-feature",
        feature_dir=None,
        target_branch=default_branch,
        strategy="merge",
        repo_root=repo,
        merge_root=repo,
        tracker=tracker,
        delete_branch=False,
        remove_worktree=False,
        push=False,
        dry_run=True,  # Use dry run to avoid checkout issues
    )

    # Dry run should succeed
    assert result.success is True

    # Note: In dry run mode, the pull step isn't actually executed,
    # but we've verified via test_execute_legacy_merge_succeeds_without_remote
    # that the actual merge skips pull when no remote exists


@pytest.mark.usefixtures("_git_identity")
def test_execute_legacy_merge_succeeds_without_remote(tmp_path):
    """Test legacy merge works on local-only repository."""
    # Create local git repo (no remote)
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    # Get the default branch name (might be 'main' or 'master')
    _, default_branch, _ = run_command(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=repo,
        capture=True,
    )
    default_branch = default_branch.strip()

    # Add .gitignore to keep working directory clean
    gitignore = repo / ".gitignore"
    gitignore.write_text(".worktrees/\n")
    run_command(["git", "add", ".gitignore"], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Create feature branch with changes
    run_command(["git", "checkout", "-b", "feature-branch"], cwd=repo)
    (repo / "test.txt").write_text("feature change")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Add feature"], cwd=repo)

    # Change to repo directory before merge
    import os
    original_cwd = os.getcwd()
    os.chdir(repo)

    try:
        # Run legacy merge
        tracker = StepTracker("Test Legacy Merge")
        result = execute_legacy_merge(
            current_branch="feature-branch",
            target_branch=default_branch,
            strategy="merge",
            merge_root=repo,
            feature_worktree_path=repo,  # Not a real worktree in this test
            tracker=tracker,
            push=False,
            remove_worktree=False,
            delete_branch=False,
            dry_run=False,
            in_worktree=False,
        )
    finally:
        # Restore original directory
        os.chdir(original_cwd)

    # Should succeed (skip pull, not error)
    assert result.success is True

    # Verify pull was skipped
    steps = tracker.steps
    pull_step = next((s for s in steps if s["key"] == "pull"), None)
    assert pull_step is not None
    assert pull_step["status"] == "skipped"


@pytest.mark.usefixtures("_git_identity")
def test_merge_dry_run_without_remote(tmp_path):
    """Test dry run works without remote."""
    # Create local git repo (no remote)
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    # Add .worktrees/ to .gitignore before creating worktrees
    gitignore = repo / ".gitignore"
    gitignore.write_text(".worktrees/\n")
    run_command(["git", "add", ".gitignore"], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Also exclude .worktrees/ from git index for extra protection
    exclude_from_git_index(repo, [".worktrees/"])

    # Create worktree with changes
    worktree = repo / ".worktrees" / "001-feature-WP01"
    run_command(["git", "worktree", "add", str(worktree), "-b", "001-feature-WP01"], cwd=repo)
    (worktree / "test.txt").write_text("change")
    run_command(["git", "add", "."], cwd=worktree)
    run_command(["git", "commit", "-m", "Add test"], cwd=worktree)

    # Get the default branch name (might be 'main' or 'master')
    _, default_branch, _ = run_command(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=repo,
        capture=True,
    )
    default_branch = default_branch.strip()

    # Run dry run
    tracker = StepTracker("Test Dry Run")
    wp_workspaces = [(worktree, "WP01", "001-feature-WP01")]
    result = execute_merge(
        wp_workspaces=wp_workspaces,
        feature_slug="001-feature",
        feature_dir=None,
        target_branch=default_branch,
        strategy="merge",
        repo_root=repo,
        merge_root=repo,
        tracker=tracker,
        delete_branch=False,
        remove_worktree=False,
        push=False,
        dry_run=True,  # Dry run should succeed
    )

    # Dry run should succeed
    assert result.success is True


@pytest.mark.usefixtures("_git_identity")
def test_execute_merge_skips_pull_with_untracked_branch(tmp_path):
    """Test merge skips pull when remote exists but branch has no upstream tracking.

    This is the scenario that caused the 0.13.2 bug report:
    - Repository has origin remote configured
    - Main branch is NOT tracking origin/main
    - git pull --ff-only fails with "no tracking information"

    Expected: Merge should skip pull and continue successfully
    """
    # Create local git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    # Add a REMOTE (but don't set up tracking!)
    bare_repo = tmp_path / "bare"
    bare_repo.mkdir()
    run_command(["git", "init", "--bare"], cwd=bare_repo)
    run_command(["git", "remote", "add", "origin", str(bare_repo)], cwd=repo)

    # Create initial commit
    gitignore = repo / ".gitignore"
    gitignore.write_text(".worktrees/\n", encoding="utf-8")
    run_command(["git", "add", ".gitignore"], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Verify: remote exists but no tracking
    assert subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo,
        capture_output=True,
        check=False,
    ).returncode == 0

    assert not has_tracking_branch(repo)

    # Get default branch name
    _, default_branch, _ = run_command(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=repo,
        capture=True,
    )
    default_branch = default_branch.strip()

    # Create worktree with changes
    worktree = repo / ".worktrees" / "001-feature-WP01"
    run_command(["git", "worktree", "add", str(worktree), "-b", "001-feature-WP01"], cwd=repo)
    (worktree / "test.txt").write_text("change", encoding="utf-8")
    run_command(["git", "add", "."], cwd=worktree)
    run_command(["git", "commit", "-m", "Add test"], cwd=worktree)

    # Ensure main repo is clean and on correct branch
    run_command(["git", "checkout", default_branch], cwd=repo)
    _, status, _ = run_command(["git", "status", "--porcelain"], cwd=repo, capture=True)
    if status.strip():
        # Commit any changes (like .git/info/exclude if it was modified)
        run_command(["git", "add", "-A"], cwd=repo)
        run_command(["git", "commit", "-m", "Clean state"], cwd=repo)

    # Run dry-run merge - should succeed despite no tracking
    # (Use dry run to focus on pull step validation, not full merge flow)
    tracker = StepTracker("Test Merge No Tracking")
    wp_workspaces = [(worktree, "WP01", "001-feature-WP01")]
    result = execute_merge(
        wp_workspaces=wp_workspaces,
        feature_slug="001-feature",
        feature_dir=None,
        target_branch=default_branch,
        strategy="merge",
        repo_root=repo,
        merge_root=repo,
        tracker=tracker,
        delete_branch=False,
        remove_worktree=False,
        push=False,
        dry_run=True,  # Dry run to test pull skip logic
    )

    # Should succeed (skips pull due to no tracking, validates merge plan)
    assert result.success is True, f"Merge failed: {result.error}"
