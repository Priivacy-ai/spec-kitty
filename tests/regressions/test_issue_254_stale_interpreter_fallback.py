"""Regression test for issue #254: an install-method migration (e.g. pipx ->
uv) moves the interpreter the pre-commit hook pinned at install time. The
next commit then fails at the shell level with a bare "No such file or
directory" naming a path, not a cause.

The fix (``policy/hook_installer.py`` HOOK_TEMPLATE) adds a run-time fallback:
if the pinned interpreter is gone, the hook tries ``spec-kitty`` resolved
fresh off PATH; if that is also unavailable, it fails with a named remedy
(``spec-kitty migrate repin-hooks``) instead of a bare path error.

This module covers the three end-to-end behaviors plus the repair command's
own logic function:

1. Pinned interpreter gone, ``spec-kitty`` on PATH -> commit succeeds via the
   fallback branch.
2. Pinned interpreter gone, ``spec-kitty`` NOT on PATH -> commit fails with
   the named remedy in stderr (not a bare path/126/127 shell error).
3. ``run_repin_hooks_migration`` re-pins a hook to the CURRENT interpreter,
   independent of what it was previously pinned to.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def _init_git(repo: Path) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)


def _install_with_doomed_interpreter(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Install the hook pinned to a copy of the interpreter, then delete the copy.

    Mirrors the real bug: the interpreter existed at install time (e.g. under
    pipx) and is gone by the time someone next commits (e.g. after `uv tool
    install` replaced the pipx install).
    """
    import shutil

    from specify_cli.policy import hook_installer

    doomed = tmp_path / "doomed-interpreter" / Path(sys.executable).name
    doomed.parent.mkdir(parents=True)
    shutil.copy2(sys.executable, doomed)

    with monkeypatch.context() as ctx:
        ctx.setattr(sys, "executable", str(doomed))
        hook_installer.install(repo)

    doomed.unlink()
    assert not doomed.exists()
    return doomed


def _write_fake_spec_kitty(bin_dir: Path, *, marker: Path) -> None:
    """A minimal ``spec-kitty`` shim: recognizes ``commit-guard-hook`` and
    touches ``marker`` to prove the fallback branch actually ran, then exits 0.
    """
    shim = bin_dir / "spec-kitty"
    shim.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "commit-guard-hook" ]; then\n'
        f'    touch "{marker}"\n'
        "    exit 0\n"
        "fi\n"
        "exit 1\n"
    )
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell fallback; bug is POSIX-surfaced")
def test_hook_falls_back_to_path_spec_kitty_when_interpreter_gone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git(repo)
    _install_with_doomed_interpreter(repo, tmp_path, monkeypatch)

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    marker = tmp_path / "fallback-ran"
    _write_fake_spec_kitty(fake_bin, marker=marker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    (repo / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    proc = subprocess.run(
        ["git", "commit", "-m", "fallback-smoke"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )

    assert proc.returncode == 0, (
        f"Commit should succeed via the PATH fallback.\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert marker.exists(), "Fallback branch must actually invoke 'spec-kitty commit-guard-hook'"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell fallback; bug is POSIX-surfaced")
def test_hook_fails_with_named_remedy_when_neither_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git(repo)
    _install_with_doomed_interpreter(repo, tmp_path, monkeypatch)

    # An empty-but-nonempty PATH dir stands in for "no spec-kitty anywhere on
    # PATH" without breaking the 'git'/'sh' lookups the test harness needs.
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    real_path_dirs = [
        d for d in os.environ["PATH"].split(os.pathsep) if not (Path(d) / "spec-kitty").exists()
    ]
    monkeypatch.setenv("PATH", os.pathsep.join([str(empty_bin), *real_path_dirs]))

    (repo / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    proc = subprocess.run(
        ["git", "commit", "-m", "no-remedy-available"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )

    assert proc.returncode != 0, "Commit must be blocked when no entrypoint is reachable"
    assert proc.returncode not in (126, 127), (
        "Failure must come from the hook's own named exit 1, not a shell-level "
        f"not-executable/not-found error. rc={proc.returncode}, stderr={proc.stderr}"
    )
    assert "spec-kitty migrate repin-hooks" in proc.stderr, (
        f"Failure message must name the concrete remedy. stderr={proc.stderr}"
    )


def test_run_repin_hooks_migration_repins_to_current_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.cli.commands.migrate.repin_hooks import run_repin_hooks_migration

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git(repo)
    _install_with_doomed_interpreter(repo, tmp_path, monkeypatch)

    result = run_repin_hooks_migration(repo)

    expected_interpreter = Path(os.path.abspath(sys.executable))
    assert result.interpreter == expected_interpreter
    assert result.hook_path == repo / ".git" / "hooks" / "pre-commit"

    hook_body = result.hook_path.read_text(encoding="utf-8")
    assert str(expected_interpreter) in hook_body
    # The doomed copy's own directory must no longer be referenced.
    assert "doomed-interpreter" not in hook_body


def test_run_repin_hooks_migration_is_idempotent(tmp_path: Path) -> None:
    from specify_cli.cli.commands.migrate.repin_hooks import run_repin_hooks_migration

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git(repo)

    first = run_repin_hooks_migration(repo)
    second = run_repin_hooks_migration(repo)

    assert first.interpreter == second.interpreter
    assert first.hook_path.read_text(encoding="utf-8") == second.hook_path.read_text(
        encoding="utf-8"
    )
