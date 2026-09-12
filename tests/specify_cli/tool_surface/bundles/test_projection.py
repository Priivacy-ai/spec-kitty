"""Windows-portability tests for the plugin bundle projection helpers.

``read_regular``, ``write_staged_file``, and ``_finalize_staged_directories``
used a bare ``os.O_NOFOLLOW`` / unconditional ``os.fchmod`` that crash on a
platform lacking them (Windows). These tests simulate that platform via
monkeypatching and assert the guarded fallbacks still work, preserving the
no-follow-symlink guarantee where applicable.
"""

from __future__ import annotations

import os
import stat
from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.tool_surface.bundles.projection import (
    OWNER,
    _finalize_staged_directories,
    observe_confined,
    read_regular,
    write_staged_file,
)
from specify_cli.tool_surface.operations import (
    Diagnostic,
    OperationRoot,
    OwnershipProof,
    PhysicalEffect,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_read_regular_windows_no_o_nofollow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulated Windows (no ``os.O_NOFOLLOW``) still reads a regular file.

    Before the fix, the bare ``os.O_NOFOLLOW`` reference raised
    ``AttributeError`` on a platform without the flag.
    """
    monkeypatch.delattr(os, "O_NOFOLLOW", raising=False)
    path = tmp_path / "source.txt"
    path.write_bytes(b"payload")

    assert read_regular(path) == b"payload"


def test_read_regular_windows_rejects_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulated Windows: the pre-open ``is_symlink()`` guard still refuses a link."""
    monkeypatch.delattr(os, "O_NOFOLLOW", raising=False)
    target = tmp_path / "secret.txt"
    target.write_bytes(b"do not disclose")
    link = tmp_path / "source.txt"
    link.symlink_to(target)

    with pytest.raises(ValueError, match="not a regular file"):
        read_regular(link)


def test_write_staged_file_windows_fchmod_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulated Windows (no ``os.fchmod``) still writes bytes and applies mode.

    Before the fix this raised ``AttributeError: module 'os' has no
    attribute 'fchmod'``.
    """
    monkeypatch.delattr(os, "fchmod", raising=False)
    destination = tmp_path / "staged.txt"

    write_staged_file(destination, b"staged content", 0o640)

    assert destination.read_bytes() == b"staged content"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o640


def test_finalize_staged_directories_windows_fchmod_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulated Windows: finalizing a staged directory's mode uses the fallback.

    Before the fix, ``os.fchmod(descriptor, ...)`` raised ``AttributeError``
    on a platform without the syscall.
    """
    monkeypatch.delattr(os, "fchmod", raising=False)
    root = tmp_path
    dest = root / "created_dir"
    dest.mkdir(mode=0o755)

    op_root = OperationRoot("root-id", "project", root)
    created = observe_confined(root, dest)[-1]
    after_state = replace(created.state, mode=0o700)
    effect = PhysicalEffect(
        owner=OWNER,
        phase="surface_repair",
        root=op_root,
        path="created_dir",
        action="chmod",
        before=created.state,
        after=after_state,
        reason="test finalize",
        ownership=(OwnershipProof("canonical_content", "test"),),
        logical_owners=("test",),
    )
    succeeded: list[str] = []
    failed: list[str] = []
    diagnostics: list[Diagnostic] = []

    _finalize_staged_directories([(effect, created)], succeeded, failed, diagnostics)

    assert not failed
    assert not diagnostics
    assert succeeded == [effect.id]
    assert stat.S_IMODE(dest.stat().st_mode) == 0o700
