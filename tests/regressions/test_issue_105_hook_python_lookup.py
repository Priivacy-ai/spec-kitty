"""Regression test for issue #105: hook fails when python/python3/py not on PATH (T038).

Pre-fix code used ``python -m specify_cli.policy.commit_guard_hook`` in the hook body,
which fails on Windows (and on any system where the Python launcher is not on PATH).

The fix pins ``sys.executable`` at install time so the hook works regardless of PATH.
"""

import os
import subprocess
from pathlib import Path

import pytest

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: trampoline bug: subprocess
pytestmark = pytest.mark.non_sandbox


@pytest.mark.windows_ci
def test_hook_executes_with_python_stripped_from_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hook runs even when python/python3/py are absent from PATH (regression #105).

    This test reproduces the exact failure mode: strip all python launchers from
    PATH, run git commit, assert the hook did not fail with 126 or 127.
    """
    from specify_cli.policy.hook_installer import install

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    install(repo)

    # Strip python launchers from PATH
    orig_path = os.environ.get("PATH", "")
    cleaned = os.pathsep.join(
        p for p in orig_path.split(os.pathsep) if not any(Path(p).joinpath(name + ext).is_file() for name in ("python", "python3", "py") for ext in ("", ".exe"))
    )
    env = {**os.environ, "PATH": cleaned}

    (repo / "file.txt").write_text("regression-105")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    proc = subprocess.run(
        ["git", "commit", "-m", "regression-105"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode not in (126, 127), (
        f"Regression of #105: hook fails when python/python3/py not on PATH. rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
