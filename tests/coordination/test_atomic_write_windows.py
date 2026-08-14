"""Windows acceptance tests for the confined coordination writer."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.coordination import atomic_write as aw


pytestmark = pytest.mark.skipif(
    os.name != "nt",
    reason="Windows confined-writer contract",
)


def test_windows_confined_write_atomically_replaces_existing_file(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "kitty-specs" / "mission" / "analysis-report.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before\n")

    written = aw._write_confined_artifact_bytes(
        worktree,
        target,
        b"after\n",
        resolve=aw._resolve_confined_artifact_path,
    )

    assert written == target.resolve()
    assert target.read_bytes() == b"after\n"
    assert list(target.parent.glob(".spec-kitty-*.tmp")) == []


def test_windows_confined_unlink_removes_regular_artifact(tmp_path: Path) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "kitty-specs" / "mission" / "status.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"{}\n")

    aw._unlink_confined_artifact_path(
        worktree,
        target,
        resolve=aw._resolve_confined_artifact_path,
    )

    assert not target.exists()
