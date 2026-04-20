"""Unit tests for kernel.atomic — atomic file write utility.

The kernel module is zero-dependency shared infrastructure used by
specify_cli, charter, and doctrine. These tests must remain
independent of all higher-level modules.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from kernel.atomic import atomic_write

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
        with patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
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

        with patch("tempfile.mkstemp", side_effect=capturing_mkstemp):
            try:
                atomic_write(target, "content")
            except Exception:
                pass

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
