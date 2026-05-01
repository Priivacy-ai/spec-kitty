"""Regression test for issue #669: hook must preserve venv symlinks in sys.executable.

Pre-fix code called ``Path(sys.executable).resolve(strict=False)``, which follows
symlinks. On pipx (and any symlinked venv), ``sys.executable`` points at
``<venv>/bin/python`` — a symlink to the base interpreter. Resolving the symlink
strips the venv context: the resolved interpreter's ``sys.prefix`` points at the
base install, so the venv's ``site-packages`` is not on ``sys.path`` and
``specify_cli`` cannot be imported from the hook.

The fix uses ``os.path.abspath`` instead of ``Path.resolve``, preserving the
symlink so the hook invokes the venv's python wrapper.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="os.symlink requires admin/dev mode on Windows; bug is POSIX-surfaced",
)
def test_install_preserves_venv_symlink_in_exec_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hook's exec line points at the symlink, not the resolved target (regression #669)."""
    from specify_cli.policy import hook_installer

    fake_venv_bin = tmp_path / "fake-venv" / "bin"
    fake_venv_bin.mkdir(parents=True)
    symlink = fake_venv_bin / "python"
    symlink.symlink_to(sys.executable)

    assert symlink.is_symlink()
    assert os.path.realpath(symlink) != str(symlink)

    monkeypatch.setattr(sys, "executable", str(symlink))

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)

    record = hook_installer.install(repo)

    assert record.interpreter == symlink, f"installer resolved through symlink; expected {symlink}, got {record.interpreter}"

    hook_body = (repo / ".git" / "hooks" / "pre-commit").read_text()
    exec_line = next(line for line in hook_body.splitlines() if line.startswith("exec "))
    assert str(symlink) in exec_line, f"exec line should quote symlink path, got: {exec_line}"
    assert os.path.realpath(symlink) not in exec_line, f"exec line must not quote the resolved target — that breaks venv site.py init. got: {exec_line}"
