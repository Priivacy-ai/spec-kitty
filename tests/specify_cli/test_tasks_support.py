"""Tests for tasks_support module, particularly git worktree handling."""

from pathlib import Path
import pytest
from specify_cli.tasks_support import find_repo_root, TaskCliError


def test_find_repo_root_normal_repo(tmp_path):
    """Test find_repo_root in a normal git repository."""
    # Create a normal repo structure
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Should find the repo root
    result = find_repo_root(tmp_path)
    assert result == tmp_path


def test_find_repo_root_with_kittify(tmp_path):
    """Test find_repo_root with .kittify directory."""
    # Create .kittify directory
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    # Should find the repo root via .kittify
    result = find_repo_root(tmp_path)
    assert result == tmp_path


def test_find_repo_root_worktree(tmp_path):
    """Test find_repo_root in a git worktree.

    find_repo_root returns the first directory with .git or .kittify marker.
    In a worktree, this is the worktree directory itself (which has .git file).
    To get the main repo, use _get_main_repo_root() from agent/tasks.py.
    """
    # Set up main repo
    main_repo = tmp_path / "main-repo"
    main_repo.mkdir()
    git_dir = main_repo / ".git"
    git_dir.mkdir()
    worktrees_dir = git_dir / "worktrees"
    worktrees_dir.mkdir()

    # Create worktree structure
    worktree_git_dir = worktrees_dir / "feature-branch"
    worktree_git_dir.mkdir()

    worktree = tmp_path / "worktrees" / "feature-branch"
    worktree.mkdir(parents=True)

    # Create .git file in worktree (points to main repo)
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {worktree_git_dir}\n")

    # Create .kittify in worktree (copied/symlinked from main)
    kittify_worktree = worktree / ".kittify"
    kittify_worktree.mkdir()

    # find_repo_root returns first directory with .git or .kittify
    # In worktree, .git is a file and .kittify exists, so worktree is returned
    result = find_repo_root(worktree)
    assert result == worktree, (
        f"Expected worktree {worktree}, got {result}. "
        "find_repo_root returns first directory with .git/.kittify marker."
    )


def test_find_repo_root_worktree_with_subdirs(tmp_path):
    """Test find_repo_root walks up from subdirectories in worktree."""
    # Set up main repo
    main_repo = tmp_path / "main-repo"
    main_repo.mkdir()
    git_dir = main_repo / ".git"
    git_dir.mkdir()
    worktrees_dir = git_dir / "worktrees"
    worktrees_dir.mkdir()

    # Create worktree structure
    worktree_git_dir = worktrees_dir / "feature-branch"
    worktree_git_dir.mkdir()

    worktree = tmp_path / "worktrees" / "feature-branch"
    worktree.mkdir(parents=True)

    # Create .git file in worktree
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {worktree_git_dir}\n")

    # Create subdirectory in worktree
    subdir = worktree / "src" / "deep" / "path"
    subdir.mkdir(parents=True)

    # find_repo_root walks up and finds first .git/.kittify (the worktree root)
    result = find_repo_root(subdir)
    assert result == worktree


def test_find_repo_root_no_git(tmp_path):
    """Test find_repo_root raises error when no .git or .kittify found."""
    # Empty directory with no git
    with pytest.raises(TaskCliError, match="Unable to locate repository root"):
        find_repo_root(tmp_path)


def test_find_repo_root_malformed_worktree_git_file(tmp_path):
    """Test find_repo_root finds directory with .git file (even if malformed).

    find_repo_root only checks for existence of .git/.kittify, not validity.
    A malformed .git file still counts as a repo marker.
    """
    # Create worktree with malformed .git file
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    git_file = worktree / ".git"
    git_file.write_text("invalid content\n")

    # find_repo_root finds directory with .git (doesn't validate content)
    result = find_repo_root(worktree)
    assert result == worktree


def test_find_repo_root_walks_upward(tmp_path):
    """Test find_repo_root walks upward through parent directories."""
    # Create repo at root
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Create deep subdirectory
    deep_dir = tmp_path / "a" / "b" / "c" / "d"
    deep_dir.mkdir(parents=True)

    # Should find repo root from deep subdirectory
    result = find_repo_root(deep_dir)
    assert result == tmp_path
