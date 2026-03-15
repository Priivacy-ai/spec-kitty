"""Conftest for the legacy test suite (0.x / 1.x contracts).

All tests under tests/legacy/ are automatically marked:
- ``legacy``: identifies them as 0.x/1.x contract tests
- ``slow``: they are integration-level tests and should not run in the fast gate

These tests are gated by IS_2X_BRANCH in branch_contract.py: on 2.x branches
pytest_ignore_collect in the root conftest.py skips the entire directory,
so they contribute 0 items to the 2.x collection.  They remain in the tree as
a frozen snapshot of the 0.x API contract and are only exercised from the
0.x/1.x maintenance branch.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_LEGACY_DIR = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply 'legacy' and 'slow' markers to all tests under tests/legacy/."""
    for item in items:
        if _LEGACY_DIR in Path(item.fspath).parents:
            item.add_marker(pytest.mark.legacy)
            item.add_marker(pytest.mark.slow)
