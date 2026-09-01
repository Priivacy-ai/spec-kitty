"""Regression tests for the shared bounded-directory writer."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

import pytest

from specify_cli.core.utils import write_text_within_directory

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_write_text_replaces_windows_read_only_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A managed read-only target can be replaced and stays read-only.

    POSIX allows replacing a read-only file when its directory is writable, so
    this test intercepts ``os.replace`` and enforces the Windows ``WinError 5``
    behavior reported upstream: replacing a read-only destination is denied
    until its write attribute is cleared.
    """
    target = tmp_path / "SKILL.md"
    target.write_text("old content\n", encoding="utf-8")
    target.chmod(0o444)

    original_replace = os.replace

    def windows_read_only_replace(source: Any, destination: Any) -> Any:
        destination_path = Path(destination)
        if destination_path.is_file() and destination_path.stat().st_mode & 0o222 == 0:
            raise PermissionError(5, "Access is denied (simulated Windows read-only target)")
        return original_replace(source, destination)

    monkeypatch.setattr(os, "replace", windows_read_only_replace)

    write_text_within_directory(target, "new content\n", root=tmp_path)

    assert target.read_text(encoding="utf-8") == "new content\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o444
