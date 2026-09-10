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


# ---------------------------------------------------------------------------
# Byte preservation (#4181): the Windows CRT text-mode conversion
# ---------------------------------------------------------------------------

# Every payload shape the fallback must write verbatim: LF must stay LF,
# CRLF must not become CRCRLF, mixed endings survive, empty stays empty, and
# binary bytes (NUL, the 0x1a EOF marker, a high byte) pass through untouched.
BYTE_PRESERVATION_PAYLOADS = [
    b"before\n",
    b"windows\r\n",
    b"mixed\nendings\r\nhere\n",
    b"",
    b"\x00\x1a\xff\n binary \x00\n",
]

_PAYLOAD_IDS = ["lf", "crlf", "mixed", "empty", "binary"]


# The CRT translation is *simulated* by the ``windows_crt_textmode`` fixture
# (this directory's conftest); on native Windows the real CRT does it and the
# unmocked windows_ci tests below cover that path directly.
posix_only = pytest.mark.skipif(
    os.name == "nt",
    reason="CRT text-mode translation is simulated; native coverage is the windows_ci tests",
)


@posix_only
@pytest.mark.parametrize("payload", BYTE_PRESERVATION_PAYLOADS, ids=_PAYLOAD_IDS)
def test_write_fallback_preserves_bytes_in_binary_mode_on_creation(windows_crt_textmode: None, worktree: Path, payload: bytes) -> None:
    """The fallback's tempfile must be opened with O_BINARY (#4181).

    3.2.7 opened it in CRT text mode, so ``b"before\\n"`` landed on disk as
    ``b"before\\r\\n"``. Under the simulated CRT a missing O_BINARY corrupts
    every newline-bearing payload exactly as on native Windows.
    """
    target = worktree / "kitty-specs" / "demo" / "artifact.json"

    _write_confined_artifact_bytes(worktree, target, payload, resolve=_real_resolve)

    assert target.read_bytes() == payload
    assert _tmp_files(target.parent) == []


@posix_only
@pytest.mark.parametrize("payload", BYTE_PRESERVATION_PAYLOADS, ids=_PAYLOAD_IDS)
def test_write_fallback_preserves_bytes_in_binary_mode_on_replacement(windows_crt_textmode: None, worktree: Path, payload: bytes) -> None:
    """Replacing an existing artifact must also write verbatim bytes."""
    target = worktree / "kitty-specs" / "demo" / "artifact.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"old\r\ncontents\n")

    _write_confined_artifact_bytes(worktree, target, payload, resolve=_real_resolve)

    assert target.read_bytes() == payload
    assert _tmp_files(target.parent) == []


@pytest.mark.windows_ci
@pytest.mark.parametrize("payload", BYTE_PRESERVATION_PAYLOADS, ids=_PAYLOAD_IDS)
def test_native_windows_write_preserves_bytes_on_creation(worktree: Path, payload: bytes) -> None:
    """Unmocked #4181 reproduction: artifact bytes land verbatim on win32.

    On native Windows the fallback engages on its own — no capability strip,
    no ``os`` monkeypatch — and the real CRT performs the translation when
    ``O_BINARY`` is missing, so this is the direct acceptance reproduction.
    No POSIX-only assumptions here: no mode-bit equality, no deletion of
    constants Windows lacks, no capability assertion.
    """
    target = worktree / "kitty-specs" / "demo" / "artifact.bin"

    resolved = _write_confined_artifact_bytes(worktree, target, payload, resolve=_real_resolve)

    assert resolved == target.resolve()
    assert target.read_bytes() == payload
    assert _tmp_files(target.parent) == []


@pytest.mark.windows_ci
@pytest.mark.parametrize("payload", BYTE_PRESERVATION_PAYLOADS, ids=_PAYLOAD_IDS)
def test_native_windows_write_preserves_bytes_on_replacement(worktree: Path, payload: bytes) -> None:
    """Unmocked replacement path: existing artifacts are overwritten verbatim."""
    target = worktree / "kitty-specs" / "demo" / "artifact.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"old\r\ncontents\n")

    _write_confined_artifact_bytes(worktree, target, payload, resolve=_real_resolve)

    assert target.read_bytes() == payload
    assert _tmp_files(target.parent) == []
