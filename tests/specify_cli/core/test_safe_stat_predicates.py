"""`#3194` — the shared ``safe_is_dir`` / ``safe_is_file`` helpers.

This generalizes the ``#3111``/``#3177`` fix in ``specify_cli.decisions.ownership``
(``S_ISDIR(resolved.stat().st_mode)`` guarded against absence-like errnos only)
to a shared, reusable pair of predicates: ``Path.is_dir()``, ``Path.is_file()``,
``Path.exists()`` and ``Path.is_symlink()`` all call ``stat()`` and swallow
``OSError`` — but not identically everywhere. Through Python 3.13 only the
absent-like errnos (``ENOENT``/``ENOTDIR``/``EBADF``/``ELOOP``) were swallowed
and ``EACCES`` propagated; 3.14 rewrote the predicates to swallow every
``OSError``, so an unreadable ancestor silently answers ``False`` on 3.14 where
every earlier interpreter raised.

Two test strategies, deliberately both present:

1. Errno-mocked tests (``monkeypatch``-ing ``Path.stat``) — these are
   interpreter-INDEPENDENT: they exercise ``safe_is_dir``/``safe_is_file``'s own
   errno-discrimination logic directly, so they catch a regression in that logic
   on every interpreter this suite runs under, not only on whichever interpreter
   happens to reproduce the native divergence.
2. A real, permission-bits EACCES test, skipped honestly (not vacuously) when
   the current process can read through the locked directory anyway (root, or a
   permission-ignoring filesystem) — mirroring the technique
   ``test_ownership_3111.py`` established for the same class of defect.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from specify_cli.core.utils import safe_is_dir, safe_is_file
from tests._support.eacces import mode_bits_enforced

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_safe_is_dir_true_for_a_real_directory(tmp_path: Path) -> None:
    assert safe_is_dir(tmp_path) is True


def test_safe_is_dir_false_for_a_regular_file(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    assert safe_is_dir(f) is False


def test_safe_is_file_true_for_a_regular_file(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    assert safe_is_file(f) is True


def test_safe_is_file_false_for_a_directory(tmp_path: Path) -> None:
    assert safe_is_file(tmp_path) is False


# ---------------------------------------------------------------------------
# Absence-like errnos: False, not raised — matching Path.is_dir()/is_file()
# on EVERY interpreter for these cases.
# ---------------------------------------------------------------------------


def test_safe_is_dir_false_for_a_missing_path(tmp_path: Path) -> None:
    assert safe_is_dir(tmp_path / "does-not-exist") is False


def test_safe_is_file_false_for_a_missing_path(tmp_path: Path) -> None:
    assert safe_is_file(tmp_path / "does-not-exist") is False


def test_safe_is_dir_false_for_a_dangling_symlink(tmp_path: Path) -> None:
    """ENOENT through the link — the #3177 companion case, generalized.

    A dangling symlink is ABSENT, not unreadable: it must answer ``False``,
    never raise, and never be conflated with a genuine permission denial.
    """
    link = tmp_path / "dangling"
    link.symlink_to(tmp_path / "never-existed")

    assert safe_is_dir(link) is False
    assert safe_is_file(link) is False


def test_safe_is_dir_false_when_a_path_segment_is_not_a_directory(tmp_path: Path) -> None:
    """ENOTDIR: a regular file in the middle of the path."""
    regular = tmp_path / "a-file"
    regular.write_text("x", encoding="utf-8")

    assert safe_is_dir(regular / "nested") is False


@pytest.mark.parametrize(
    "target_errno",
    [errno.ENOENT, errno.ENOTDIR, errno.EBADF, errno.ELOOP],
)
def test_safe_is_dir_swallows_every_absent_errno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_errno: int
) -> None:
    """Errno-mocked, interpreter-independent: pins the exact ``_ABSENT_ERRNOS`` set."""

    def _raise(self: Path) -> os.stat_result:  # type: ignore[no-untyped-def]
        raise OSError(target_errno, os.strerror(target_errno))

    monkeypatch.setattr(Path, "stat", _raise)

    assert safe_is_dir(tmp_path) is False
    assert safe_is_file(tmp_path) is False


# ---------------------------------------------------------------------------
# EACCES (and any other non-absent OSError): RAISES, on every interpreter —
# the one deliberate behaviour change from Path.is_dir()'s NATIVE 3.14 shape,
# and the whole point of the helper.
# ---------------------------------------------------------------------------


def test_safe_is_dir_raises_for_a_non_absent_errno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(self: Path) -> os.stat_result:  # type: ignore[no-untyped-def]
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(Path, "stat", _raise)

    with pytest.raises(OSError) as excinfo:
        safe_is_dir(tmp_path)
    assert excinfo.value.errno == errno.EACCES


def test_safe_is_file_raises_for_a_non_absent_errno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(self: Path) -> os.stat_result:  # type: ignore[no-untyped-def]
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(Path, "stat", _raise)

    with pytest.raises(OSError) as excinfo:
        safe_is_file(tmp_path)
    assert excinfo.value.errno == errno.EACCES


def test_real_eacces_through_a_locked_directory_raises_not_silently_false(
    tmp_path: Path,
) -> None:
    """REGRESSION TEST — the real-permission-bits mirror of the mocked tests above.

    Measured (this module's docstring, and ``specify_cli.decisions.ownership``'s
    before it): on Python 3.14, ``Path.is_dir()``/``Path.exists()`` return
    ``False`` for a target behind an unreadable directory instead of raising —
    the exact silent misclassification this helper exists to remove. This test
    passes today (pre-fix code would have used ``Path.is_dir()`` directly and
    this suite is not gated to 3.14), but is what pins the behaviour for anyone
    running it there, and is the same technique the mocked tests above already
    cover for every interpreter.
    """
    locked = tmp_path / "locked"
    target = locked / "child"
    locked.mkdir()
    target.mkdir()
    canary = locked / "canary"
    canary.write_text("{}", encoding="utf-8")

    os.chmod(locked, 0o000)
    try:
        if not mode_bits_enforced(canary):
            pytest.skip(
                "SKIPPED HONESTLY, not passed: this process can read through a "
                "0o000 directory (running as root, or a filesystem that ignores "
                "mode bits), so the branch cannot be constructed here."
            )
        with pytest.raises(OSError):
            safe_is_dir(target)
        with pytest.raises(OSError):
            safe_is_file(target)
    finally:
        os.chmod(locked, 0o700)
