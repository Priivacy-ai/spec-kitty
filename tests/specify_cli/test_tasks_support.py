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
    """Test find_repo_root follows worktree .git file to main repo.

    find_repo_root detects when .git is a file (worktree pointer) and follows
    the gitdir pointer back to the main repository. This prevents nested
    worktree creation bugs.
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

    # find_repo_root follows the .git file pointer back to main repo
    # This is critical for preventing nested worktree creation
    result = find_repo_root(worktree)
    assert result == main_repo, (
        f"Expected main repo {main_repo}, got {result}. "
        "find_repo_root should follow worktree .git pointer to main repo."
    )


def test_find_repo_root_worktree_with_subdirs(tmp_path):
    """Test find_repo_root walks up from subdirectories and follows to main repo."""
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

    # find_repo_root walks up, finds worktree .git file, follows to main repo
    result = find_repo_root(subdir)
    assert result == main_repo


def test_find_repo_root_no_git(tmp_path):
    """Test find_repo_root raises error when no .git or .kittify found."""
    # Empty directory with no git
    with pytest.raises(TaskCliError, match="Unable to locate repository root"):
        find_repo_root(tmp_path)


def test_find_repo_root_malformed_worktree_git_file(tmp_path):
    """Test find_repo_root continues searching when .git file is malformed.

    find_repo_root now tries to parse .git files to follow worktree pointers.
    If the .git file is malformed, it continues searching upward for a valid
    repo marker (.git directory or .kittify directory).
    """
    # Create worktree with malformed .git file
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    git_file = worktree / ".git"
    git_file.write_text("invalid content\n")

    # find_repo_root tries to parse .git file, fails, continues searching
    # Since there's no valid repo marker above, it should raise TaskCliError
    with pytest.raises(TaskCliError, match="Unable to locate repository root"):
        find_repo_root(worktree)


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
