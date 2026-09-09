"""Regression tests for the path-based confined-write fallback (#3173).

Windows has no ``dir_fd`` support and no ``O_DIRECTORY`` / ``O_NOFOLLOW``, so
the fd-relative confined write in ``specify_cli.coordination.atomic_write``
hard-failed there and every coordination artifact write was unusable. The
fallback routes to a path-based write/unlink that re-verifies containment,
rejects symlinked path components, writes a uniquely named tempfile, and
``os.replace``s it into place.

These tests simulate the Windows capability surface (empty
``os.supports_dir_fd``, no ``O_DIRECTORY`` / ``O_NOFOLLOW``) so the real
dispatch predicate — not a stub of it — selects the fallback.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.coordination.atomic_write import (
    _fd_relative_writes_supported,
    _resolve_confined_artifact_path,
    _unlink_confined_artifact_path,
    _write_confined_artifact_bytes,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture
def simulated_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip the fd-relative capability surface, as on Windows."""
    monkeypatch.setattr(os, "supports_dir_fd", set())
    monkeypatch.delattr(os, "O_DIRECTORY")
    monkeypatch.delattr(os, "O_NOFOLLOW")


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A worktree root whose lexical path already equals its resolved path."""
    root = tmp_path / "wt"
    root.mkdir()
    return root.resolve()


def _real_resolve(worktree_root: Path, path: Path) -> Path:
    return _resolve_confined_artifact_path(worktree_root, path)


def _unresolved_resolve(worktree_root: Path, path: Path) -> Path:
    """Oracle-style resolver that returns the candidate WITHOUT resolving it.

    Mirrors the dependency-injection seam's documented purpose: the resolver
    is patchable, so the fallback must not trust it to have folded symlinks
    away — the component walk is the defense that catches this shape.
    """
    candidate = path if path.is_absolute() else worktree_root / path
    if candidate == worktree_root:
        raise ValueError("target is worktree root")
    return candidate


def _tmp_files(directory: Path) -> list[Path]:
    return sorted(directory.glob(".spec-kitty-*.tmp"))


# ---------------------------------------------------------------------------
# Capability predicate
# ---------------------------------------------------------------------------


def test_capability_predicate_false_without_fd_relative_support(
    simulated_windows: None,
) -> None:
    assert _fd_relative_writes_supported() is False


def test_capability_predicate_true_on_posix() -> None:
    # The suite's reference platforms (Linux/macOS CI) support all three
    # primitives; this pins that the fallback never engages there silently.
    assert _fd_relative_writes_supported() is True


# ---------------------------------------------------------------------------
# Write fallback
# ---------------------------------------------------------------------------


def test_write_falls_back_to_path_based_write(simulated_windows: None, worktree: Path) -> None:
    target = worktree / "kitty-specs" / "demo" / "artifact.json"

    resolved = _write_confined_artifact_bytes(worktree, target, b'{"a": 1}', resolve=_real_resolve)

    assert resolved == target.resolve()
    assert target.read_bytes() == b'{"a": 1}'
    assert _tmp_files(target.parent) == []


def test_write_fallback_preserves_existing_file_mode(simulated_windows: None, worktree: Path) -> None:
    target = worktree / "kitty-specs" / "demo" / "script.sh"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"old\n")
    target.chmod(0o744)

    _write_confined_artifact_bytes(worktree, target, b"new\n", resolve=_real_resolve)

    assert target.read_bytes() == b"new\n"
    assert target.stat().st_mode & 0o777 == 0o744


def test_write_fallback_refuses_parent_outside_worktree(simulated_windows: None, worktree: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    escapee = outside / "artifact.txt"

    def escapee_resolver(_root: Path, _path: Path) -> Path:
        return escapee

    with pytest.raises(ValueError, match="parent resolves outside worktree"):
        _write_confined_artifact_bytes(worktree, escapee, b"bad", resolve=escapee_resolver)

    assert not escapee.exists()


def test_write_fallback_rejects_symlinked_component(simulated_windows: None, worktree: Path) -> None:
    """A symlinked component is refused even when its target stays inside.

    The fd-relative path's ``O_NOFOLLOW`` rejects symlinks regardless of
    where they point; the component walk is the fallback's replacement for
    that guarantee and must behave the same.
    """
    real_dir = worktree / "real"
    real_dir.mkdir()
    link = worktree / "link"
    link.symlink_to(real_dir, target_is_directory=True)
    target = link / "artifact.txt"

    with pytest.raises(ValueError, match="symlinked path component"):
        _write_confined_artifact_bytes(worktree, target, b"bad", resolve=_unresolved_resolve)

    assert not (real_dir / "artifact.txt").exists()
    assert not link.joinpath("artifact.txt").exists()


def test_write_fallback_unlinks_tempfile_on_failure(
    simulated_windows: None,
    worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = worktree / "kitty-specs" / "demo" / "artifact.json"

    def failing_replace(*_args: object, **_kwargs: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", failing_replace)

    with pytest.raises(OSError, match="replace failed"):
        _write_confined_artifact_bytes(worktree, target, b"content", resolve=_real_resolve)

    assert not target.exists()
    assert _tmp_files(target.parent) == []


# ---------------------------------------------------------------------------
# Unlink fallback (the rollback compensator's unlink twin)
# ---------------------------------------------------------------------------


def test_unlink_falls_back_to_path_based_unlink(simulated_windows: None, worktree: Path) -> None:
    target = worktree / "kitty-specs" / "demo" / "artifact.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"stale")

    _unlink_confined_artifact_path(worktree, target, resolve=_real_resolve)
    assert not target.exists()

    # A missing target is a no-op, matching the fd-relative path's
    # FileNotFoundError pass-through.
    _unlink_confined_artifact_path(worktree, target, resolve=_real_resolve)


def test_unlink_fallback_rejects_symlinked_component(simulated_windows: None, worktree: Path) -> None:
    real_dir = worktree / "real"
    real_dir.mkdir()
    stale = real_dir / "artifact.txt"
    stale.write_bytes(b"stale")
    link = worktree / "link"
    link.symlink_to(real_dir, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked path component"):
        _unlink_confined_artifact_path(worktree, link / "artifact.txt", resolve=_unresolved_resolve)

    # The real target was not reached through the symlink.
    assert stale.exists()
