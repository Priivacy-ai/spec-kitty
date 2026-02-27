"""Unit tests for path resolution utilities."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.core.paths import (
    locate_project_root,
    is_worktree_context,
    resolve_with_context,
    check_broken_symlink,
)


def test_locate_project_root_from_main(mock_main_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test path resolution from main repository."""
    # Change to main repo directory
    monkeypatch.chdir(mock_main_repo)

    # Call path resolution
    repo_root = locate_project_root()

    # Assert correct root found
    assert repo_root == mock_main_repo
    assert (repo_root / ".kittify").exists()


def test_locate_project_root_from_worktree(mock_worktree: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    """Test path resolution from worktree directory."""
    # Change to worktree directory
    monkeypatch.chdir(mock_worktree["worktree_path"])

    # Call path resolution
    repo_root = locate_project_root()

    # Assert walks up to main repo root
    assert repo_root == mock_worktree["repo_root"]
    assert (repo_root / ".kittify").exists()


def test_locate_project_root_with_env_var(mock_main_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test path resolution using SPECIFY_REPO_ROOT environment variable."""
    # Set environment variable
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(mock_main_repo))

    # Change to a different directory
    different_dir = mock_main_repo / "some" / "nested" / "dir"
    different_dir.mkdir(parents=True)
    monkeypatch.chdir(different_dir)

    # Call path resolution - should use env var
    repo_root = locate_project_root()

    # Assert env var was used
    assert repo_root == mock_main_repo


def test_locate_project_root_from_nested_dir(mock_main_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test path resolution from deeply nested directory."""
    # Create nested directory structure
    nested = mock_main_repo / "kitty-specs" / "001-feature" / "deep" / "nested"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    # Call path resolution
    repo_root = locate_project_root()

    # Assert walks up to root
    assert repo_root == mock_main_repo


def test_is_worktree_context(mock_worktree: dict[str, Path]) -> None:
    """Test worktree context detection via .worktrees path heuristic."""
    # Test worktree path
    assert is_worktree_context(mock_worktree["worktree_path"]) is True

    # Test repo root (not in worktree)
    assert is_worktree_context(mock_worktree["repo_root"]) is False

    # Test feature dir (within worktree)
    assert is_worktree_context(mock_worktree["feature_dir"]) is True


def test_is_worktree_context_external_worktree(tmp_path: Path) -> None:
    """Test worktree context detection via .git file with gitdir pointer.

    Simulates an external worktree (e.g. under /tmp) where .git is a file
    pointing to the main repo, NOT under a .worktrees directory.
    """
    # Create a fake external worktree directory (no .worktrees in path)
    external_wt = tmp_path / "external-worktree"
    external_wt.mkdir()

    # Write .git file with gitdir pointer (what git worktree add creates)
    git_file = external_wt / ".git"
    git_file.write_text("gitdir: /some/repo/.git/worktrees/external-worktree\n")

    assert is_worktree_context(external_wt) is True

    # A subdirectory inside the external worktree should also be detected
    nested = external_wt / "src" / "deep"
    nested.mkdir(parents=True)
    assert is_worktree_context(nested) is True


def test_is_worktree_context_bare_repo_worktree(tmp_path: Path) -> None:
    """Bare-repo worktree (gitdir: /path/repo.git/worktrees/<wt>) IS a worktree."""
    bare_wt = tmp_path / "bare-worktree"
    bare_wt.mkdir()

    # Write .git file with gitdir pointer to a bare repo topology
    git_file = bare_wt / ".git"
    git_file.write_text("gitdir: /srv/repos/myproject.git/worktrees/bare-worktree\n")

    assert is_worktree_context(bare_wt) is True

    # Nested path inside the bare-repo worktree
    nested = bare_wt / "src" / "lib"
    nested.mkdir(parents=True)
    assert is_worktree_context(nested) is True


def test_is_worktree_context_main_repo(tmp_path: Path) -> None:
    """Test that a main repo with .git directory is NOT detected as worktree."""
    # Create a fake main repo with .git directory
    main_repo = tmp_path / "main-repo"
    main_repo.mkdir()
    (main_repo / ".git").mkdir()

    assert is_worktree_context(main_repo) is False

    # Nested path inside main repo
    nested = main_repo / "src" / "lib"
    nested.mkdir(parents=True)
    assert is_worktree_context(nested) is False


def test_is_worktree_context_submodule_gitdir(tmp_path: Path) -> None:
    """Submodule .git file (gitdir: ../.git/modules/foo) must NOT be a worktree."""
    sub = tmp_path / "parent-repo" / "sub"
    sub.mkdir(parents=True)

    git_file = sub / ".git"
    git_file.write_text("gitdir: ../.git/modules/sub\n")

    assert is_worktree_context(sub) is False

    # Nested path inside the submodule
    nested = sub / "src" / "lib"
    nested.mkdir(parents=True)
    assert is_worktree_context(nested) is False


def test_is_worktree_context_separate_git_dir(tmp_path: Path) -> None:
    """Separate-git-dir clone (gitdir: /some/external/dir) must NOT be a worktree."""
    repo = tmp_path / "my-clone"
    repo.mkdir()

    external_gitdir = tmp_path / "external-gitdirs" / "my-clone.git"
    external_gitdir.mkdir(parents=True)

    git_file = repo / ".git"
    git_file.write_text(f"gitdir: {external_gitdir}\n")

    assert is_worktree_context(repo) is False

    nested = repo / "src"
    nested.mkdir()
    assert is_worktree_context(nested) is False


def test_resolve_with_context_main_repo(mock_main_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test combined resolution from main repo."""
    monkeypatch.chdir(mock_main_repo)

    root, in_worktree = resolve_with_context()

    assert root == mock_main_repo
    assert in_worktree is False


def test_resolve_with_context_worktree(mock_worktree: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    """Test combined resolution from worktree."""
    monkeypatch.chdir(mock_worktree["worktree_path"])

    root, in_worktree = resolve_with_context()

    assert root == mock_worktree["repo_root"]
    assert in_worktree is True


def test_broken_symlink_handling(tmp_path: Path) -> None:
    """Test graceful handling of broken symlinks."""
    # Create broken symlink
    target = tmp_path / "nonexistent"
    link = tmp_path / "broken_link"
    link.symlink_to(target)

    # Verify is_symlink() returns True
    assert link.is_symlink()
    # Verify exists() returns False
    assert not link.exists()

    # Test check_broken_symlink helper
    assert check_broken_symlink(link) is True

    # Test with valid symlink
    valid_target = tmp_path / "valid_target"
    valid_target.mkdir()
    valid_link = tmp_path / "valid_link"
    valid_link.symlink_to(valid_target)
    assert check_broken_symlink(valid_link) is False

    # Test with regular file
    regular_file = tmp_path / "regular.txt"
    regular_file.write_text("content")
    assert check_broken_symlink(regular_file) is False


def test_locate_project_root_no_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test path resolution when no .kittify marker exists."""
    # Create directory without .kittify
    no_marker = tmp_path / "no-marker-dir"
    no_marker.mkdir()
    monkeypatch.chdir(no_marker)

    # Call path resolution
    repo_root = locate_project_root()

    # Should return None
    assert repo_root is None


def test_locate_project_root_with_broken_symlink_kittify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test path resolution gracefully handles broken .kittify symlink."""
    # Create directory with broken .kittify symlink
    test_dir = tmp_path / "test-dir"
    test_dir.mkdir()
    kittify_link = test_dir / ".kittify"
    kittify_link.symlink_to(tmp_path / "nonexistent")

    monkeypatch.chdir(test_dir)

    # Should skip the broken symlink and return None (or continue searching)
    repo_root = locate_project_root()
    assert repo_root is None or repo_root != test_dir
