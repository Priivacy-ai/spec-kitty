"""Unit tests for kernel.atomic — atomic file write utility.

The kernel module is zero-dependency shared infrastructure used by
specify_cli, charter, and doctrine. These tests must remain
independent of all higher-level modules.

Coverage:
- Baseline atomic_write contract (str/bytes/mkdir/atomicity)
- T014: Kill atomic_write mutants (WP03)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from kernel.atomic import atomic_write
import contextlib

pytestmark = pytest.mark.fast


class TestAtomicWriteStr:
    """atomic_write with str content."""

    def test_writes_string_content(self, tmp_path: Path) -> None:
        target = tmp_path / "output.txt"
        atomic_write(target, "hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_encodes_str_to_utf8(self, tmp_path: Path) -> None:
        target = tmp_path / "unicode.txt"
        atomic_write(target, "café ñoño 中文")
        assert target.read_bytes() == "café ñoño 中文".encode()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "file.txt"
        target.write_text("old content", encoding="utf-8")
        atomic_write(target, "new content")
        assert target.read_text(encoding="utf-8") == "new content"

    def test_writes_empty_string(self, tmp_path: Path) -> None:
        target = tmp_path / "empty.txt"
        atomic_write(target, "")
        assert target.exists()
        assert target.read_bytes() == b""


class TestAtomicWriteBytes:
    """atomic_write with bytes content."""

    def test_writes_bytes_content(self, tmp_path: Path) -> None:
        target = tmp_path / "binary.bin"
        atomic_write(target, b"\x00\x01\x02\xff")
        assert target.read_bytes() == b"\x00\x01\x02\xff"

    def test_bytes_written_verbatim(self, tmp_path: Path) -> None:
        target = tmp_path / "raw.bin"
        data = b"raw\nbytes\x00data"
        atomic_write(target, data)
        assert target.read_bytes() == data

    def test_overwrites_with_bytes(self, tmp_path: Path) -> None:
        target = tmp_path / "file.bin"
        target.write_bytes(b"old")
        atomic_write(target, b"new")
        assert target.read_bytes() == b"new"


class TestAtomicWriteMkdir:
    """mkdir=True creates parent directories."""

    def test_creates_missing_parents(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c" / "file.txt"
        atomic_write(target, "content", mkdir=True)
        assert target.read_text(encoding="utf-8") == "content"

    def test_mkdir_false_raises_on_missing_parent(self, tmp_path: Path) -> None:
        target = tmp_path / "missing_dir" / "file.txt"
        with pytest.raises((FileNotFoundError, OSError)):
            atomic_write(target, "content", mkdir=False)

    def test_mkdir_true_is_idempotent_when_dir_exists(self, tmp_path: Path) -> None:
        target = tmp_path / "existing" / "file.txt"
        target.parent.mkdir()
        atomic_write(target, "first", mkdir=True)
        atomic_write(target, "second", mkdir=True)
        assert target.read_text(encoding="utf-8") == "second"


class TestAtomicWriteAtomicity:
    """Atomicity guarantees: no partial writes, temp file cleaned up."""

    def test_no_temp_file_left_on_success(self, tmp_path: Path) -> None:
        target = tmp_path / "file.txt"
        atomic_write(target, "content")
        leftover = list(tmp_path.glob(".atomic-*.tmp"))
        assert leftover == [], f"Unexpected temp files: {leftover}"

    def test_no_temp_file_left_on_write_error(self, tmp_path: Path) -> None:
        target = tmp_path / "file.txt"
        with patch("os.replace", side_effect=OSError("disk full")), pytest.raises(OSError):
            atomic_write(target, "content")
        leftover = list(tmp_path.glob(".atomic-*.tmp"))
        assert leftover == [], f"Temp file not cleaned up: {leftover}"

    def test_temp_file_is_in_same_directory(self, tmp_path: Path) -> None:
        """Temp file must be on same filesystem as target for atomic rename."""
        target = tmp_path / "file.txt"
        created_dirs: list[Path] = []

        real_mkstemp = __import__("tempfile").mkstemp

        def capturing_mkstemp(**kwargs):  # type: ignore[no-untyped-def]
            created_dirs.append(Path(kwargs["dir"]))
            return real_mkstemp(**kwargs)

        with patch("tempfile.mkstemp", side_effect=capturing_mkstemp), contextlib.suppress(Exception):
            atomic_write(target, "content")

        if created_dirs:
            assert created_dirs[0] == tmp_path


class TestAtomicWriteImport:
    """Smoke tests for module imports and re-exports used by other packages."""

    def test_importable_from_kernel(self) -> None:
        from kernel.atomic import atomic_write as aw

        assert callable(aw)

    def test_importable_via_specify_cli_shim(self) -> None:
        from specify_cli.core.atomic import atomic_write as aw

        assert callable(aw)

    def test_importable_via_charter(self) -> None:
        from charter.context import build_charter_context

        assert callable(build_charter_context)


# ---------------------------------------------------------------------------
# T014: Kill atomic_write survivors (WP03)
# ---------------------------------------------------------------------------


def _spy_mkstemp(
    monkeypatch: pytest.MonkeyPatch,
) -> list[dict[str, Any]]:
    """Install a recording spy for tempfile.mkstemp in kernel.atomic.

    Returns a list that accumulates the kwargs of each call. The spy defers
    to the real mkstemp so the rest of atomic_write proceeds normally.
    """
    calls: list[dict[str, Any]] = []
    real_mkstemp = tempfile.mkstemp

    def _recording_mkstemp(*args: Any, **kwargs: Any) -> Any:
        calls.append(dict(kwargs))
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr("kernel.atomic.tempfile.mkstemp", _recording_mkstemp)
    return calls


class TestAtomicWriteMkdirDefault:
    """Pin the mkdir=False default.

    Kills __mutmut_1 (mkdir default flipped to True): with mkdir=True the
    call to a nonexistent parent directory succeeds by creating the tree;
    with the original mkdir=False it must raise because the parent is
    missing.
    """

    def test_default_mkdir_is_false_missing_parent_raises(self, tmp_path: Path) -> None:
        """Calling atomic_write with no mkdir kwarg and a missing parent raises.

        If the default were True (mutant), the parent directory would be
        created and the write would succeed. This test forces the failing
        path so only the original default is consistent with the observable.
        """
        target = tmp_path / "never-created-parent" / "file.txt"
        assert not target.parent.exists()
        with pytest.raises((FileNotFoundError, OSError)):
            # No mkdir kwarg -> must use the default.
            atomic_write(target, "content")
        # And the parent directory must still not exist — a True default
        # would have created it as a side effect.
        assert not target.parent.exists()


class TestAtomicWriteMkstempContract:
    """Pin the exact tempfile.mkstemp call contract in atomic_write.

    A single spy kills the surviving mutants that alter the dir, prefix, or
    suffix keyword argument values or keys.
    """

    def test_mkstemp_dir_is_target_parent(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """The dir kwarg must equal the target file's parent directory.

        Kills __mutmut_13 (dir=None), __mutmut_16 (dir kwarg removed). When
        dir=None is used, mkstemp creates the temp file in the system
        tempdir, which breaks the same-filesystem invariant for atomic
        rename. We assert the spy sees dir=<target parent> exactly.
        """
        calls = _spy_mkstemp(monkeypatch)
        target = tmp_path / "out.txt"
        atomic_write(target, "payload")

        assert len(calls) == 1, f"expected one mkstemp call, got {len(calls)}"
        kwargs = calls[0]
        assert "dir" in kwargs, f"dir kwarg must be explicitly passed; got {kwargs!r}"
        assert kwargs["dir"] == tmp_path
        assert kwargs["dir"] is not None

    def test_mkstemp_prefix_is_dot_atomic_dash(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """The prefix kwarg must equal the exact lowercase '.atomic-' string.

        Kills __mutmut_14 (prefix=None), __mutmut_17 (prefix kwarg removed),
        __mutmut_19 (prefix="XX.atomic-XX"), __mutmut_20 (prefix=".ATOMIC-").
        """
        calls = _spy_mkstemp(monkeypatch)
        target = tmp_path / "out.txt"
        atomic_write(target, "payload")

        kwargs = calls[0]
        assert "prefix" in kwargs, "prefix kwarg must be explicitly passed"
        assert kwargs["prefix"] == ".atomic-"
        # Anti-mutant assertions: none of these variants is acceptable.
        assert kwargs["prefix"] is not None
        assert kwargs["prefix"] != ".ATOMIC-"
        assert "XX" not in kwargs["prefix"]

    def test_mkstemp_suffix_is_dot_tmp(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """The suffix kwarg must equal the exact lowercase '.tmp' string.

        Kills __mutmut_15 (suffix=None), __mutmut_18 (suffix kwarg removed),
        __mutmut_21 (suffix="XX.tmpXX"), __mutmut_22 (suffix=".TMP").
        """
        calls = _spy_mkstemp(monkeypatch)
        target = tmp_path / "out.txt"
        atomic_write(target, "payload")

        kwargs = calls[0]
        assert "suffix" in kwargs, "suffix kwarg must be explicitly passed"
        assert kwargs["suffix"] == ".tmp"
        assert kwargs["suffix"] is not None
        assert kwargs["suffix"] != ".TMP"
        assert "XX" not in kwargs["suffix"]


class TestAtomicWriteCleanupSuppressesOSError:
    """Pin the OSError-suppression contract during failure cleanup.

    Kills __mutmut_34 (contextlib.suppress(OSError) -> suppress(None)):
    with suppress(None) the context manager raises TypeError when it tries
    to evaluate issubclass(exctype, None), clobbering the original OSError
    that callers expect to bubble up.
    """

    def test_cleanup_suppresses_unlink_oserror(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """When rename fails and tmp-file unlink also raises OSError, the
        original rename OSError must propagate — NOT a TypeError.
        """
        target = tmp_path / "out.txt"

        # Force Path.replace() (the rename step) to raise OSError so the
        # except branch runs.
        def _failing_replace(self: Path, other: Any) -> Any:
            raise OSError("forced replace failure")

        monkeypatch.setattr(Path, "replace", _failing_replace)

        # Force Path.unlink() on the temp file to raise OSError so the
        # suppressor is actually exercised.
        def _failing_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
            raise OSError("forced unlink failure during cleanup")

        monkeypatch.setattr(Path, "unlink", _failing_unlink)

        with pytest.raises(OSError, match="forced replace failure"):
            atomic_write(target, "content")
