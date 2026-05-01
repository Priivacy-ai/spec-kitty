"""Conftest for dashboard tests.

WP03 routes ``resolve_project_charter_path`` (and through it the dashboard
scanner) through the FR-004 chokepoint. The chokepoint requires a git repo
to resolve the canonical root; pre-WP03 dashboard tests created
``tmp_path`` fixtures without ``git init``. We initialize an empty repo
whenever a dashboard test asks for ``tmp_path`` to honor the new contract
without rewriting every test fixture body, and clear the resolver LRU
between tests.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _git_init_tmp_path(request: pytest.FixtureRequest) -> None:
    if "tmp_path" in request.fixturenames:
        tmp_path: Path = request.getfixturevalue("tmp_path")
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
