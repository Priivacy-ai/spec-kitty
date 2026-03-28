"""Migration integration tests — tombstone after WP05 deletion.

specify_cli.status.migrate was deleted as part of the canonical state
architecture cleanup (WP05). Bootstrapping event log from frontmatter
state is no longer needed since the event log is the sole authority.

All tests in this file verify that the migrate module does not exist.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.fast


def test_migrate_module_does_not_exist():
    """Verify specify_cli.status.migrate was deleted and cannot be imported."""
    with pytest.raises(ImportError):
        importlib.import_module("specify_cli.status.migrate")


def test_migrate_feature_not_importable():
    """Verify migrate_feature is not importable from any status sub-module."""
    with pytest.raises((ImportError, ModuleNotFoundError)):
        from specify_cli.status.migrate import migrate_feature  # type: ignore[import]  # noqa: F401
