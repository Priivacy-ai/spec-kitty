"""Performance gate for ``run_charter_preflight`` (NFR-001).

NFR-001 contract:

* warm path (everything fresh, no refresh needed) → < 300 ms.
* cold path (refresh runs) → < 1 s.  Covered by the integration tests
  which stub the subprocess; the budget here is the warm path only.

We use a simple ``time.monotonic()`` budget rather than ``pytest-benchmark``
to keep the dependency surface minimal — the budget is one order of
magnitude wider than the typical observed runtime (which is ~20–40 ms on
modern laptops) so this is robust against CI noise.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

from specify_cli.charter_runtime.preflight import run_charter_preflight

from tests._perf_helpers import assert_timing_budget

from ._fixtures import make_fresh_repo


pytestmark = [pytest.mark.integration, pytest.mark.timing]


def test_runner_cold_import_under_500ms() -> None:
    """The next hot path must not eagerly load the heavyweight charter package."""
    probe = (
        "import time; "
        "start = time.perf_counter(); "
        "import specify_cli.charter_runtime.preflight.runner; "
        "print((time.perf_counter() - start) * 1000)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
    )
    elapsed_ms = float(completed.stdout.strip())
    assert elapsed_ms < 500.0, (
        f"NFR-001 cold-import budget exceeded: {elapsed_ms:.1f} ms >= 500 ms"
    )

@pytest.mark.integration
def test_warm_path_succeeds(tmp_path: Path) -> None:
    """Fresh-cached repo: ``run_charter_preflight`` succeeds on the warm path."""
    make_fresh_repo(tmp_path)

    # Warm any imports / first-touch caches before the assertion.
    run_charter_preflight(tmp_path, auto_refresh=False)

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert result.passed is True


@pytest.mark.performance
def test_warm_path_under_300ms(tmp_path: Path) -> None:
    """Fresh-cached repo: ``run_charter_preflight`` must complete in <300 ms."""
    make_fresh_repo(tmp_path)

    # Warm any imports / first-touch caches by running once before timing.
    run_charter_preflight(tmp_path, auto_refresh=False)

    start = time.monotonic()
    run_charter_preflight(tmp_path, auto_refresh=False)
    elapsed_ms = (time.monotonic() - start) * 1000.0

    # NFR-001 warm budget.  300 ms is the binding contract; we allow the
    # full budget here because slower CI runners (e.g. shared GitHub
    # Actions) can be noisy.
    assert_timing_budget(elapsed_ms, 300.0, name="NFR-001 warm budget")
