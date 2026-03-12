"""Conftest for upgrade tests."""

import pytest
from pathlib import Path

_THIS_DIR = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark all tests in this directory as fast."""
    for item in items:
        if _THIS_DIR in Path(item.fspath).parents:
            item.add_marker(pytest.mark.fast)
