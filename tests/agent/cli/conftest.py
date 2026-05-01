"""Conftest for agent CLI tests.

WP03 of ``unified-charter-bundle-chokepoint-01KP5Q2G`` routed the charter
CLI handlers and ``build_charter_context`` through the FR-004 chokepoint,
which requires a git repo to resolve the canonical root. CLI tests under
this directory invoke charter handlers and need a git-tracked tmp_path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _git_init_tmp_path(request: pytest.FixtureRequest) -> None:
    if "tmp_path" in request.fixturenames:
        tmp_path: Path = request.getfixturevalue("tmp_path")
        if not (tmp_path / ".git").exists():
            try:
                subprocess.run(
                    ["git", "init", "--quiet", str(tmp_path)],
                    check=False,
                    capture_output=True,
                )
            except (FileNotFoundError, OSError):
                pass
    yield
    try:
        from charter.resolution import resolve_canonical_repo_root

        resolve_canonical_repo_root.cache_clear()
    except Exception:
        pass
