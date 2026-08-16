"""Behavior-parity tests for the unified git-topology primitive.

Mission ``write-path-integrity-01KZZD69`` WP01 (#3373) collapsed four
re-implementations of the git-common-dir / toplevel probe into one primitive
(:mod:`kernel.git_topology`). These tests pin the primitive's own
contract (canonicalization, not-a-repo classification, ``.git``-interior
detection, caching) plus the two cross-site behaviors the consolidation MUST
NOT regress: the charter resolver's caching/classification and the
checkout-ownership NESTED refusal.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kernel.git_topology import (
    GitTopologyUnavailableError,
    NotAGitRepositoryError,
    clear_caches,
    git_common_dir,
    git_toplevel,
)

# Marked like the charter canonical-root suite: real subprocess to git.
pytestmark = [pytest.mark.non_sandbox, pytest.mark.git_repo]


@pytest.fixture(autouse=True)
def _reset_topology_cache() -> None:
    """Reset the shared probe caches so a prior test's path cannot shadow this one."""
    clear_caches()


@pytest.fixture
def fresh_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("gt_repo")
    subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
    clear_caches()
    return root


@pytest.fixture
def repo_with_worktree(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("gt_repo_wt")
    subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
    for key, val in (("user.email", "t@e.com"), ("user.name", "T")):
        subprocess.run(["git", "-C", str(root), "config", key, val], check=True, capture_output=True)
    (root / "README.md").write_text("seed\n")
    subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-m", "seed", "--quiet"], check=True, capture_output=True
    )
    worktree = root.parent / (root.name + "-wt")
    subprocess.run(
        ["git", "-C", str(root), "worktree", "add", "-B", "wt", str(worktree)],
        check=True, capture_output=True,
    )
    clear_caches()
    return root, worktree


# ---------------------------------------------------------------------------
# git_common_dir
# ---------------------------------------------------------------------------


def test_common_dir_of_main_checkout(fresh_repo: Path) -> None:
    assert git_common_dir(fresh_repo) == (fresh_repo / ".git").resolve()


def test_common_dir_from_subdirectory(fresh_repo: Path) -> None:
    sub = fresh_repo / "src" / "nested"
    sub.mkdir(parents=True)
    assert git_common_dir(sub) == (fresh_repo / ".git").resolve()


def test_common_dir_file_input_normalized_to_parent(fresh_repo: Path) -> None:
    f = fresh_repo / "some.txt"
    f.write_text("hi")
    assert git_common_dir(f) == (fresh_repo / ".git").resolve()


def test_common_dir_linked_worktree_shares_main_common(
    repo_with_worktree: tuple[Path, Path],
) -> None:
    main_root, worktree = repo_with_worktree
    # A linked worktree resolves to the SAME shared common dir as the main
    # checkout — the invariant the safe-commit linkage comparator relies on.
    assert git_common_dir(worktree) == git_common_dir(main_root)


def test_common_dir_not_a_repo_raises(tmp_path_factory: pytest.TempPathFactory) -> None:
    not_a_repo = tmp_path_factory.mktemp("gt_bare")
    with pytest.raises(NotAGitRepositoryError):
        git_common_dir(not_a_repo)


def test_common_dir_inside_dot_git_raises(fresh_repo: Path) -> None:
    with pytest.raises(NotAGitRepositoryError):
        git_common_dir(fresh_repo / ".git")


def test_common_dir_missing_binary_raises_unavailable(fresh_repo: Path) -> None:
    with (
        patch("kernel.git_topology.subprocess.run", side_effect=FileNotFoundError("git")),
        pytest.raises(GitTopologyUnavailableError) as excinfo,
    ):
        git_common_dir(fresh_repo)
    assert "binary not found" in str(excinfo.value)


def test_common_dir_corrupt_returncode_raises_unavailable(fresh_repo: Path) -> None:
    fake = MagicMock(returncode=128, stderr="fatal: bad object HEAD\n", stdout="")
    with (
        patch("kernel.git_topology.subprocess.run", return_value=fake),
        pytest.raises(GitTopologyUnavailableError) as excinfo,
    ):
        git_common_dir(fresh_repo)
    assert "bad object" in str(excinfo.value)


# ---------------------------------------------------------------------------
# git_toplevel
# ---------------------------------------------------------------------------


def test_toplevel_of_main_checkout(fresh_repo: Path) -> None:
    assert git_toplevel(fresh_repo) == fresh_repo.resolve()


def test_toplevel_from_subdirectory_returns_root(fresh_repo: Path) -> None:
    sub = fresh_repo / "a" / "b"
    sub.mkdir(parents=True)
    # A subdirectory's toplevel is the repo root, NOT the subdirectory — this is
    # exactly the mismatch the NESTED classifier keys on.
    assert git_toplevel(sub) == fresh_repo.resolve()
    assert git_toplevel(sub) != sub.resolve()


def test_toplevel_of_linked_worktree_is_itself(
    repo_with_worktree: tuple[Path, Path],
) -> None:
    _main, worktree = repo_with_worktree
    assert git_toplevel(worktree) == worktree.resolve()


def test_toplevel_not_a_repo_raises(tmp_path_factory: pytest.TempPathFactory) -> None:
    not_a_repo = tmp_path_factory.mktemp("gt_bare_tl")
    with pytest.raises(NotAGitRepositoryError):
        git_toplevel(not_a_repo)


# ---------------------------------------------------------------------------
# Caching (the charter hot-path invariant)
# ---------------------------------------------------------------------------


def test_warm_common_dir_makes_no_second_invocation(fresh_repo: Path) -> None:
    real_run = subprocess.run
    spy = MagicMock(side_effect=lambda *a, **kw: real_run(*a, **kw))
    with patch("kernel.git_topology.subprocess.run", spy):
        git_common_dir(fresh_repo)
        git_common_dir(fresh_repo)
    assert spy.call_count == 1


def test_clear_caches_forces_reinvocation(fresh_repo: Path) -> None:
    real_run = subprocess.run
    spy = MagicMock(side_effect=lambda *a, **kw: real_run(*a, **kw))
    with patch("kernel.git_topology.subprocess.run", spy):
        git_common_dir(fresh_repo)
        clear_caches()
        git_common_dir(fresh_repo)
    assert spy.call_count == 2


def test_exception_is_not_cached(tmp_path_factory: pytest.TempPathFactory) -> None:
    # A not-a-repo path that later becomes a repo must resolve on the next call
    # (lru_cache never caches the raise).
    path = tmp_path_factory.mktemp("gt_becomes_repo")
    with pytest.raises(NotAGitRepositoryError):
        git_common_dir(path)
    subprocess.run(["git", "init", "--quiet", str(path)], check=True, capture_output=True)
    assert git_common_dir(path) == (path / ".git").resolve()


# ---------------------------------------------------------------------------
# Cross-site parity: charter resolver + checkout-ownership NESTED refusal
# ---------------------------------------------------------------------------


def test_charter_resolver_consumes_primitive(fresh_repo: Path) -> None:
    """The charter canonical-root resolver returns the parent of the primitive's common dir."""
    from charter.resolution import resolve_canonical_repo_root

    resolve_canonical_repo_root.cache_clear()
    assert resolve_canonical_repo_root(fresh_repo) == git_common_dir(fresh_repo).parent
    assert resolve_canonical_repo_root(fresh_repo) == fresh_repo.resolve()


def test_is_worktree_of_toplevel_guard_rejects_subdirectory(fresh_repo: Path) -> None:
    """The safe-commit linkage gate's toplevel guard (T005) rejects a subdirectory.

    A subdirectory shares the repo's common dir but its toplevel is not itself;
    the guard must fold it to ``False`` so the ownership comparator's NESTED
    refusal stays reachable. Deleting the guard would make this return ``True``.
    """
    from specify_cli.git.commit_helpers import is_worktree_of

    sub = fresh_repo / "pkg" / "inner"
    sub.mkdir(parents=True)
    assert is_worktree_of(fresh_repo, sub) is False


def test_ownership_nested_refusal_preserved(
    repo_with_worktree: tuple[Path, Path],
) -> None:
    """A checkout nested inside a linked worktree classifies NESTED (SC-008 parity)."""
    from specify_cli.core.checkout_ownership import (
        OwnershipValidationResult,
        resolve_ownership_claim,
    )

    main_root, worktree = repo_with_worktree
    nested = worktree / "deep" / "nest"
    nested.mkdir(parents=True)
    claim = resolve_ownership_claim(nested, resolved_primary=main_root)
    assert claim.validation_result is OwnershipValidationResult.NESTED
