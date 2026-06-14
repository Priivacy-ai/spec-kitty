"""Tests for the coordination-topology-aware ``is_committed()`` overload.

Covers:
- Flat topology (no placement): original HEAD-only behaviour preserved.
- Coord topology: file found on coord branch returns True even when absent on HEAD.
- Coord topology: file absent on both coord branch and HEAD returns False.
- Coord topology: coord branch lookup fails gracefully, falls back to HEAD.
- Non-COORDINATION placement kind: HEAD-only check used (FLATTENED / PRIMARY).

Issue #1884 / FR-003 / WP01.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.missions._substantive import is_committed

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(tmp_path: Path) -> str:
    """Set up a minimal git repository with an initial commit.

    Returns the default branch name (``main`` or ``master`` depending on git config).
    """
    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    # Create an initial commit so HEAD exists.
    readme = tmp_path / "README.md"
    readme.write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )
    return "main"


def _commit_file(tmp_path: Path, file_path: Path, message: str) -> None:
    """Stage and commit ``file_path`` in ``tmp_path``."""
    rel = str(file_path.relative_to(tmp_path))
    subprocess.run(["git", "-C", str(tmp_path), "add", rel], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", message],
        check=True,
        capture_output=True,
    )


def _make_commit_target(ref: str, kind_str: str) -> object:
    """Construct a CommitTarget using the mission_runtime dataclass."""
    from mission_runtime import CommitTarget, CommitTargetKind

    kind = CommitTargetKind[kind_str]
    return CommitTarget(ref=ref, kind=kind)


# ---------------------------------------------------------------------------
# Flat-topology (no placement): original HEAD-only behaviour
# ---------------------------------------------------------------------------


def test_no_placement_file_committed_on_head_returns_true(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    assert is_committed(spec, tmp_path) is True


def test_no_placement_file_not_committed_returns_false(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    # Not committed — only written to disk.

    assert is_committed(spec, tmp_path) is False


def test_no_placement_file_outside_repo_returns_false(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    # Use a file that lives outside tmp_path entirely.
    outside = tmp_path.parent / f"outside_{tmp_path.name}.md"
    outside.write_text("x\n", encoding="utf-8")
    try:
        assert is_committed(outside, tmp_path) is False
    finally:
        outside.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Coord-topology: file on coord branch, absent from HEAD
# ---------------------------------------------------------------------------


def test_coord_placement_file_on_coord_branch_returns_true(tmp_path: Path) -> None:
    """Spec committed only to the coordination branch satisfies the gate."""
    _init_repo(tmp_path)

    # Create a coordination branch and commit spec.md there.
    coord_ref = "kitty/mission-test-ABCD1234"
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-b", coord_ref],
        check=True,
        capture_output=True,
    )
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec on coord")

    # Switch back to main so spec.md is NOT on HEAD.
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "main"],
        check=True,
        capture_output=True,
    )
    # Confirm the file is absent from HEAD.
    result = subprocess.run(
        ["git", "-C", str(tmp_path), "cat-file", "-e", "HEAD:spec.md"],
        capture_output=True,
    )
    assert result.returncode != 0, "Precondition: spec.md must NOT be on HEAD"

    placement = _make_commit_target(coord_ref, "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_coord_placement_file_in_coord_worktree_returns_true(tmp_path: Path) -> None:
    """A spec path under .worktrees resolves against the coord branch tree."""
    _init_repo(tmp_path)

    coord_ref = "kitty/mission-test-WORKTREE"
    subprocess.run(
        ["git", "-C", str(tmp_path), "branch", coord_ref, "main"],
        check=True,
        capture_output=True,
    )
    coord_worktree = tmp_path / ".worktrees" / "test-coord"
    coord_worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "worktree", "add", str(coord_worktree), coord_ref],
        check=True,
        capture_output=True,
    )

    spec = coord_worktree / "kitty-specs" / "test" / "spec.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("# Spec\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(coord_worktree), "add", "kitty-specs/test/spec.md"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(coord_worktree), "commit", "-m", "add spec on coord worktree"],
        check=True,
        capture_output=True,
    )

    placement = _make_commit_target(coord_ref, "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_coord_placement_file_on_both_branches_returns_true(tmp_path: Path) -> None:
    """File on HEAD AND coord branch: still True (OR logic)."""
    _init_repo(tmp_path)
    coord_ref = "kitty/mission-test-BBBB2222"

    # Commit spec.md on main (HEAD).
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec on main")

    # Also commit a version on the coord branch.
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-b", coord_ref],
        check=True,
        capture_output=True,
    )
    spec.write_text("# Spec (coord version)\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "update spec on coord")
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "main"],
        check=True,
        capture_output=True,
    )

    placement = _make_commit_target(coord_ref, "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_coord_placement_file_absent_from_both_branches_returns_false(tmp_path: Path) -> None:
    """File absent from both coord branch and HEAD: False."""
    _init_repo(tmp_path)
    coord_ref = "kitty/mission-test-CCCC3333"

    # Create the coord branch without spec.md.
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-b", coord_ref],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "main"],
        check=True,
        capture_output=True,
    )

    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")  # on disk but never committed

    placement = _make_commit_target(coord_ref, "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Coord-topology: invalid / non-existent coord branch falls back to HEAD
# ---------------------------------------------------------------------------


def test_coord_placement_nonexistent_branch_falls_back_to_head(tmp_path: Path) -> None:
    """Non-existent coord branch: cat-file fails, falls back to HEAD check."""
    _init_repo(tmp_path)

    # Commit spec.md to HEAD (no coord branch exists at all).
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    # Reference a branch that does not exist.
    placement = _make_commit_target("kitty/nonexistent-DEADBEEF", "COORDINATION")
    # Falls back to HEAD — spec IS on HEAD, so returns True.
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_coord_placement_nonexistent_branch_file_absent_from_head_returns_false(
    tmp_path: Path,
) -> None:
    """Non-existent coord branch AND file absent from HEAD: False."""
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")  # on disk, not committed

    placement = _make_commit_target("kitty/nonexistent-DEADBEEF", "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Non-COORDINATION placement kinds: HEAD-only check
# ---------------------------------------------------------------------------


def test_flattened_placement_uses_head_check(tmp_path: Path) -> None:
    """FLATTENED placement: coord fast-path is skipped, falls back to HEAD."""
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    placement = _make_commit_target("main", "FLATTENED")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_primary_placement_uses_head_check(tmp_path: Path) -> None:
    """PRIMARY placement: coord fast-path is skipped, falls back to HEAD."""
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    placement = _make_commit_target("main", "PRIMARY")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]
