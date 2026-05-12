"""Preflight helper that asserts the test extra is installed in the active venv.

See: src/specify_cli/cli/commands/review/ERROR_CODES.md for the
MISSION_REVIEW_TEST_EXTRA_MISSING diagnostic body.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class TestExtraMissing(Exception):
    """Raised when `pytest` cannot be imported from the active venv."""

    # Prevent pytest from treating this exception class as a test class.
    __test__ = False


def assert_pytest_available(project_root: Path) -> None:
    """Assert that `python -c 'import pytest'` succeeds in the project venv.

    Raises TestExtraMissing on failure, carrying the
    MISSION_REVIEW_TEST_EXTRA_MISSING diagnostic code in args[0].
    """
    result = subprocess.run(
        [sys.executable, "-c", "import pytest"],
        cwd=project_root,
        capture_output=True,
    )
    if result.returncode != 0:
        raise TestExtraMissing("MISSION_REVIEW_TEST_EXTRA_MISSING")
