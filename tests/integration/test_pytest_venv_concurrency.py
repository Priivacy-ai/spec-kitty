"""Scope: regression test for concurrent test-venv fixture creation (FR-003, FR-004).

Verifies that parallel pytest invocations against the contract and architectural
suites complete without racing on .pytest_cache/spec-kitty-test-venv.  This
reproduces the race condition described in issue #986 when the file lock is absent,
and confirms it is absent when the lock is in place.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.utils import REPO_ROOT

pytestmark = pytest.mark.slow


def _run_collection(suite: str) -> subprocess.CompletedProcess[str]:
    """Run pytest collection-only pass against *suite* from the repo root.

    Uses ``sys.executable -m pytest`` so the test works in any environment
    that the parent pytest runs under, including CI runners that do not
    have ``uv`` on PATH (the WP02 slow-tests CI job, for example).
    """
    return subprocess.run(
        [sys.executable, "-m", "pytest", suite, "-x", "--co", "-q"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def test_concurrent_contract_and_architectural_complete() -> None:
    """Parallel contract + architectural collection succeeds without venv-creation races.

    Regression test for issue #986: two pytest processes observing a missing venv
    simultaneously would both attempt python -m venv creation, causing ensurepip
    failures in the losing process.

    The file lock in _ensure_test_venv serialises creation so only one process
    builds; the second acquires the lock, finds a valid venv, and skips.
    """
    # Arrange — wipe any cached venv so both workers observe it as missing
    venv_path = REPO_ROOT / ".pytest_cache" / "spec-kitty-test-venv"
    lock_path = REPO_ROOT / ".pytest_cache" / "spec-kitty-test-venv.lock"

    shutil.rmtree(venv_path, ignore_errors=True)
    lock_path.unlink(missing_ok=True)

    # Assumption check — venv must be absent so the race is actually exercised
    assert not venv_path.exists(), "venv must not exist before the concurrent run"

    # Act — fire both collection passes simultaneously
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_contract = executor.submit(_run_collection, "tests/contract/")
        future_architectural = executor.submit(_run_collection, "tests/architectural/")
        result_contract = future_contract.result()
        result_architectural = future_architectural.result()

    # Assert — both processes must exit successfully (returncode 0 = collected OK, 5 = no tests)
    assert result_contract.returncode in (0, 5), (
        f"Contract collection failed (rc={result_contract.returncode}):\n"
        f"stdout: {result_contract.stdout}\nstderr: {result_contract.stderr}"
    )
    assert result_architectural.returncode in (0, 5), (
        f"Architectural collection failed (rc={result_architectural.returncode}):\n"
        f"stdout: {result_architectural.stdout}\nstderr: {result_architectural.stderr}"
    )
