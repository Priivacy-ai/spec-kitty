"""Integration tests for worktree exclusion from git index."""

import subprocess

import pytest

from specify_cli.core.git_ops import exclude_from_git_index, run_command


@pytest.fixture(name="_git_identity")
def git_identity_fixture(monkeypatch):
    """Ensure git commands can commit even if the user has no global config."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "spec@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "spec@example.com")


@pytest.mark.usefixtures("_git_identity")
def test_worktree_excluded_from_git(tmp_path):
    """Test .worktrees/ is excluded from git index after exclusion."""
    # Setup git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    run_command(["git", "commit", "--allow-empty", "-m", "Initial"], cwd=repo)

    # Add exclusion
    exclude_from_git_index(repo, [".worktrees/"])

    # Create worktree
    worktree = repo / ".worktrees" / "001-test"
    run_command(["git", "worktree", "add", str(worktree), "-b", "001-test"], cwd=repo)

    # Add a file in the worktree
    (worktree / "test.txt").write_text("test content")
    run_command(["git", "add", "."], cwd=worktree)
    run_command(["git", "commit", "-m", "Add test file"], cwd=worktree)

    # Try explicit add from main repo (should be ignored due to exclusion)
    subprocess.run(
        ["git", "add", ".worktrees/"],
        cwd=repo,
        capture_output=True,
        check=False,
    )

    # Verify .worktrees/ is not staged in main repo
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    # The status output should not show .worktrees/ as staged
    # (worktrees show up as gitlinks if accidentally added)
    assert ".worktrees/" not in status.stdout or "M .worktrees/" not in status.stdout


@pytest.mark.usefixtures("_git_identity")
def test_worktree_exclusion_prevents_gitlink(tmp_path):
    """Test that exclusion prevents worktree from being added as gitlink."""
    # Setup git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    run_command(["git", "commit", "--allow-empty", "-m", "Initial"], cwd=repo)

    # Add exclusion BEFORE creating worktree
    exclude_from_git_index(repo, [".worktrees/"])

    # Create worktree
    worktree = repo / ".worktrees" / "001-test"
    run_command(["git", "worktree", "add", str(worktree), "-b", "001-test"], cwd=repo)

    # Try to add the worktree directory
    subprocess.run(
        ["git", "add", ".worktrees/"],
        cwd=repo,
        capture_output=True,
        check=False,
    )

    # Check if anything was staged
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    # Should not stage .worktrees/ directory
    assert ".worktrees" not in result.stdout


@pytest.mark.usefixtures("_git_identity")
def test_exclusion_file_created_correctly(tmp_path):
    """Test that .git/info/exclude is created with correct format."""
    # Setup git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    # Add exclusions
    exclude_from_git_index(repo, [".worktrees/", ".build/", "*.tmp"])

    # Verify exclusion file exists and has correct content
    exclude_file = repo / ".git" / "info" / "exclude"
    assert exclude_file.exists()

    content = exclude_file.read_text()
    lines = content.splitlines()

    # Check all patterns are present
    assert ".worktrees/" in lines
    assert ".build/" in lines
    assert "*.tmp" in lines

    # Check marker comment is present
    assert "# Added by spec-kitty (local exclusions)" in content


@pytest.mark.usefixtures("_git_identity")
def test_multiple_exclusion_calls_dont_duplicate(tmp_path):
    """Test that calling exclusion multiple times doesn't create duplicates."""
    # Setup git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    # Add exclusions multiple times
    exclude_from_git_index(repo, [".worktrees/"])
    exclude_from_git_index(repo, [".worktrees/", ".build/"])
    exclude_from_git_index(repo, [".worktrees/"])

    # Verify patterns appear only once each
    exclude_file = repo / ".git" / "info" / "exclude"
    content = exclude_file.read_text()

    assert content.count(".worktrees/") == 1
    assert content.count(".build/") == 1
