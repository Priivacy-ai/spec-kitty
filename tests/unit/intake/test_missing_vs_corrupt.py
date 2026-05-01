"""Missing-vs-unreadable distinction in :func:`read_brief` (WP02 T011)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from specify_cli.intake.errors import (
    IntakeFileMissingError,
    IntakeFileUnreadableError,
)
from specify_cli.intake.scanner import read_brief


pytestmark = [pytest.mark.fast]


def test_missing_file_raises_file_missing(tmp_path):
    ghost = tmp_path / "nope.md"
    with pytest.raises(IntakeFileMissingError) as ei:
        read_brief(ghost, cap=1024)
    assert str(ghost) in str(ei.value)
    assert ei.value.detail["path"] == str(ghost)


def test_permission_error_on_stat_raises_unreadable(tmp_path):
    real = tmp_path / "blocked.md"
    real.write_text("hello", encoding="utf-8")

    def _denied(self):  # noqa: ARG001
        raise PermissionError("simulated")

    with (
        patch("pathlib.Path.stat", _denied),
        pytest.raises(IntakeFileUnreadableError) as ei,
    ):
        read_brief(real, cap=1024)

    assert "PermissionError" in str(ei.value)
    # Cause chain is preserved so loggers can render the underlying error.
    assert isinstance(ei.value.__cause__, PermissionError)


def test_io_error_on_open_raises_unreadable(tmp_path):
    real = tmp_path / "ioerr.md"
    real.write_text("hello", encoding="utf-8")

    def _io_fail(self, *args, **kwargs):  # noqa: ARG001
        raise OSError("disk on fire")

    with (
        patch("pathlib.Path.read_text", _io_fail),
        pytest.raises(IntakeFileUnreadableError) as ei,
    ):
        read_brief(real, cap=1024)

    assert "OSError" in str(ei.value) or "disk on fire" in str(ei.value)


def test_decode_error_raises_unreadable(tmp_path):
    real = tmp_path / "bad-utf8.md"
    # Invalid UTF-8 byte sequence.
    real.write_bytes(b"\xff\xfe\xfd valid? no.")

    with pytest.raises(IntakeFileUnreadableError):
        read_brief(real, cap=1024)


def test_existing_file_within_cap_returns_text(tmp_path):
    """Negative control — sanity-check the happy path is not flagged."""
    real = tmp_path / "fine.md"
    real.write_text("# OK", encoding="utf-8")
    assert read_brief(real, cap=1024) == "# OK"
