"""Mypy gate: config-verified redundant cast removed (#2675 / WP07 T062).

``resolve_planning_read_dir`` is defined in the SAME module as its caller
(``_read_path_resolver.py``), so its declared ``-> Path`` return type was
always visible to mypy at the call site inside
``resolve_subtasks_gate_dir`` — unlike the follow_imports=skip cross-module
cases the removed cast's stale rationale comment described. Passing the
source through ``cast(Path, ...)`` was flagged ``redundant-cast`` under the
canonical mypy invocation; T062 dropped the cast, deleted the stale
rationale comment, and removed the now-unused ``cast`` import.

This test pins that the file stays mypy-clean (regression guard against a
reintroduced redundant cast, or an unrelated typing regression at the same
call site).

Environment requirement: this test invokes mypy via ``sys.executable -m
mypy``, which requires the ``lint`` extra to be installed in the test env
(e.g. ``uv run --extra test --extra lint python -m pytest ...``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [pytest.mark.integration]

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = "src/specify_cli/missions/_read_path_resolver.py"


@pytest.mark.slow  # mypy invocation is comparatively expensive
def test_read_path_resolver_is_mypy_clean() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", TARGET],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "mypy failed on _read_path_resolver.py.\n"
        "stdout:\n" + result.stdout + "\nstderr:\n" + result.stderr
    )
    assert "redundant-cast" not in result.stdout, (
        "A redundant-cast error resurfaced in _read_path_resolver.py:\n" + result.stdout
    )
