"""Statistical performance guard for ``spec-kitty next`` cold-start (FR-003, #3787).

Off-PR only: ``@pytest.mark.performance`` is auto-skipped by ``tests/conftest.py``
unless ``SPEC_KITTY_RUN_PERFORMANCE=1``, so this runs solely in
``.github/workflows/performance.yml``'s ``next`` domain leg (paths include
``tests/specify_cli/next``) — never on a PR-blocking path (C-002). It is the
non-gating, statistical replacement for the retired single-shot
``scripts/check_nfr_003_latency.py`` wall-clock ceiling.

Each measured round spawns a FRESH ``python -m specify_cli next`` subprocess,
because "cold-start" is a fresh process — the exact cost a real mission-loop
invocation pays. An in-process ``benchmark.pedantic`` call would reuse the warm
interpreter/import cache and measure something structurally faster and
different. The measurement mechanism mirrors the retired gate's
``subprocess.run`` shape (that script is being deleted as a *gate*, but its
measurement shape was correct). ``rounds``/``iterations`` are pinned (not
pytest-benchmark auto-calibration) so a ~1s/round subprocess cannot balloon CI
wall-time.

pytest-benchmark compares the median against the committed per-domain baseline
under ``tests/performance/baselines/`` with ``--benchmark-compare-fail=median:50%``
(a relative delta), so runner variance never false-reds and only a genuine
step-change regression fails. A missing baseline on first run is a pass
(pytest-benchmark exit 4, handled by the workflow); refresh the baseline via the
workflow_dispatch ``update_baseline`` path — the pipeline never auto-commits it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

pytestmark = [pytest.mark.performance, pytest.mark.integration]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "clean_install_fixture_mission"
_MISSION = "clean-install-fixture-01KQ22XX"
_ROUNDS = 5
_WARMUP_ROUNDS = 1


def _run_next_cold() -> None:
    """One cold-start invocation: a fresh interpreter runs the read-only query."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "specify_cli",
            "next",
            "--agent",
            "test",
            "--mission",
            _MISSION,
            "--json",
        ],
        cwd=str(_FIXTURE),
        capture_output=True,
        check=False,
    )
    # A non-zero exit is a real failure of the thing under test, not a perf
    # signal — fail loudly rather than silently benchmarking an error path.
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")


@pytest.mark.performance
@pytest.mark.benchmark(group="next")
def test_next_cold_start_subprocess_benchmark(benchmark: BenchmarkFixture) -> None:
    """FR-003 (#3787): statistical, subprocess-based ``next`` cold-start guard."""
    # pytest-benchmark 5.2.3 ships ``pedantic`` without a typed signature.
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        _run_next_cold,
        rounds=_ROUNDS,
        warmup_rounds=_WARMUP_ROUNDS,
        iterations=1,
    )
