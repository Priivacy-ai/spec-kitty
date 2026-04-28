"""Lock the mypy --strict invariant on mission_step_contracts/executor.py.

NFR-001 / WP03: this test makes a regression of strict-typing on the executor
module fail at CI time, not at developer-machine time. See
``kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/tasks/WP03-python-version-and-strict-mypy.md``.

Environment requirement: this test invokes mypy via ``sys.executable -m mypy``,
which requires the ``lint`` extra to be installed in the test env (e.g.
``uv run --extra test --extra lint python -m pytest ...``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = "src/specify_cli/mission_step_contracts/executor.py"


@pytest.mark.slow  # mypy invocation is comparatively expensive
def test_mission_step_contracts_executor_is_mypy_strict_clean() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", TARGET],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "mypy --strict failed on mission_step_contracts/executor.py.\n"
        "stdout:\n"
        + result.stdout
        + "\nstderr:\n"
        + result.stderr
    )
