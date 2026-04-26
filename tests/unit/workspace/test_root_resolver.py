"""Unit tests for ``specify_cli.workspace.root_resolver`` (WP03/T013, FR-013).

These tests exercise the canonical-root resolver in four scenarios:

* a regular git repo,
* a git worktree (``.git`` is a file),
* a subdirectory inside the worktree, and
* a directory that is not a git repo at all.

They use real ``git worktree add`` so the ``commondir`` parsing path is
covered, not just mocked-out file layouts.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.workspace.root_resolver import (
    WorkspaceRootNotFound,
    _reset_cache,
    resolve_canonical_root,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure the module-level cache is empty for each test."""
    _reset_cache()
    yield
    _reset_cache()


def _git(cwd: Path, *args: str) -> str:
    """Run a git command, returning stdout. Fails the test on nonzero exit."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "--initial-branch=main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "commit.gpgsign", "false")
    (path / "README.md").write_text("hi\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "init")
    return path.resolve()


@pytest.mark.git_repo
def test_regular_repo_root(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")

    assert resolve_canonical_root(repo) == repo


@pytest.mark.git_repo
def test_subdirectory_of_regular_repo_walks_up(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    sub = repo / "src" / "deep"
    sub.mkdir(parents=True)

    assert resolve_canonical_root(sub) == repo


@pytest.mark.git_repo
def test_worktree_returns_canonical_main_repo(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    worktree = tmp_path / "wt-feature"
    _git(repo, "worktree", "add", "-b", "feature", str(worktree))

    resolved = resolve_canonical_root(worktree)

    assert resolved == repo
    assert resolved != worktree.resolve()


@pytest.mark.git_repo
def test_subdirectory_inside_worktree_returns_canonical(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    worktree = tmp_path / "wt-deep"
    _git(repo, "worktree", "add", "-b", "deep", str(worktree))

    nested = worktree / "src" / "nested" / "deeper"
    nested.mkdir(parents=True)

    assert resolve_canonical_root(nested) == repo


def test_non_git_directory_raises(tmp_path: Path) -> None:
    plain = tmp_path / "no-git"
    plain.mkdir()

    with pytest.raises(WorkspaceRootNotFound) as exc_info:
        resolve_canonical_root(plain)

    assert plain.resolve() == exc_info.value.cwd


@pytest.mark.git_repo
def test_cache_returns_same_object_for_repeated_calls(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    first = resolve_canonical_root(repo)
    second = resolve_canonical_root(repo)

    assert first == second == repo
