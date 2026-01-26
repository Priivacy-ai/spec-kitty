import os
import sys
from pathlib import Path

import pytest

from specify_cli.core.git_ops import (
    exclude_from_git_index,
    get_current_branch,
    has_remote,
    init_git_repo,
    is_git_repo,
    run_command,
)


def test_run_command_captures_stdout():
    code, stdout, stderr = run_command(
        [sys.executable, "-c", "print('hello world')"],
        capture=True,
    )
    assert code == 0
    assert stdout == "hello world"
    assert stderr == ""


def test_run_command_allows_nonzero_when_not_checking():
    code, stdout, stderr = run_command(
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        check_return=False,
    )
    assert code == 3
    assert stdout == ""
    assert stderr == ""


@pytest.mark.usefixtures("_git_identity")
def test_git_repo_lifecycle(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "README.md").write_text("hello", encoding="utf-8")

    assert is_git_repo(project) is False
    assert init_git_repo(project, quiet=True) is True
    assert is_git_repo(project) is True

    branch = get_current_branch(project)
    assert branch


@pytest.fixture(name="_git_identity")
def git_identity_fixture(monkeypatch):
    """Ensure git commands can commit even if the user has no global config."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "spec@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "spec@example.com")


@pytest.mark.usefixtures("_git_identity")
def test_has_remote_with_origin(tmp_path):
    """Test has_remote returns True when origin exists."""
    # Setup git repo with remote
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    run_command(["git", "remote", "add", "origin", "https://example.com/repo.git"], cwd=repo)

    assert has_remote(repo) is True


@pytest.mark.usefixtures("_git_identity")
def test_has_remote_without_origin(tmp_path):
    """Test has_remote returns False when no remote exists."""
    # Setup git repo without remote
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    assert has_remote(repo) is False


def test_has_remote_nonexistent_repo(tmp_path):
    """Test has_remote returns False for non-git directory."""
    non_repo = tmp_path / "not-a-repo"
    non_repo.mkdir()

    assert has_remote(non_repo) is False


@pytest.mark.usefixtures("_git_identity")
def test_exclude_from_git_index(tmp_path):
    """Test exclude_from_git_index adds patterns to .git/info/exclude."""
    # Setup git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    # Add exclusions
    exclude_from_git_index(repo, [".worktrees/", ".build/"])

    # Verify exclusions were added
    exclude_file = repo / ".git" / "info" / "exclude"
    content = exclude_file.read_text()
    assert ".worktrees/" in content
    assert ".build/" in content
    assert "# Added by spec-kitty" in content


@pytest.mark.usefixtures("_git_identity")
def test_exclude_from_git_index_duplicate(tmp_path):
    """Test exclude_from_git_index doesn't duplicate existing patterns."""
    # Setup git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    # Add exclusions twice
    exclude_from_git_index(repo, [".worktrees/"])
    exclude_from_git_index(repo, [".worktrees/"])

    # Verify pattern appears only once
    exclude_file = repo / ".git" / "info" / "exclude"
    content = exclude_file.read_text()
    assert content.count(".worktrees/") == 1


def test_exclude_from_git_index_non_git_repo(tmp_path):
    """Test exclude_from_git_index silently skips non-git directories."""
    non_repo = tmp_path / "not-a-repo"
    non_repo.mkdir()

    # Should not raise an error
    exclude_from_git_index(non_repo, [".worktrees/"])

    # Verify no .git directory was created
    assert not (non_repo / ".git").exists()


def test_has_tracking_branch_with_tracking(tmp_path, _git_identity):
    """Test has_tracking_branch returns True when branch tracks remote."""
    # Create bare repo (remote)
    bare = tmp_path / "bare"
    bare.mkdir()
    run_command(["git", "init", "--bare"], cwd=bare)

    # Create local repo with tracking
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    run_command(["git", "remote", "add", "origin", str(bare)], cwd=repo)

    # Create initial commit and push
    (repo / "test.txt").write_text("test", encoding="utf-8")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Get branch name
    _, branch, _ = run_command(["git", "branch", "--show-current"], cwd=repo, capture=True)
    branch = branch.strip()

    # Push and set up tracking
    run_command(["git", "push", "-u", "origin", branch], cwd=repo)

    # Should have tracking now
    from specify_cli.core.git_ops import has_tracking_branch
    assert has_tracking_branch(repo) is True


def test_has_tracking_branch_without_tracking(tmp_path, _git_identity):
    """Test has_tracking_branch returns False when branch doesn't track remote."""
    # Create repo with remote but NO tracking
    bare = tmp_path / "bare"
    bare.mkdir()
    run_command(["git", "init", "--bare"], cwd=bare)

    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    run_command(["git", "remote", "add", "origin", str(bare)], cwd=repo)

    # Create commit but DON'T push with -u
    (repo / "test.txt").write_text("test", encoding="utf-8")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Should NOT have tracking
    from specify_cli.core.git_ops import has_tracking_branch
    assert has_tracking_branch(repo) is False


def test_has_tracking_branch_no_remote(tmp_path, _git_identity):
    """Test has_tracking_branch returns False when no remote exists."""
    # Create local-only repo
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)

    (repo / "test.txt").write_text("test", encoding="utf-8")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Should NOT have tracking (no remote)
    from specify_cli.core.git_ops import has_tracking_branch
    assert has_tracking_branch(repo) is False
