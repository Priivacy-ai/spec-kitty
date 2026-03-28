"""Tests confirming migrate.py module was deleted in WP05.

migrate.py was deleted as part of the canonical state architecture cleanup
(WP05). Bootstrapping event log from frontmatter state is no longer needed
since the event log is the sole authority.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.fast


def test_migrate_module_does_not_exist():
    """Verify migrate.py was deleted and cannot be imported."""
    with pytest.raises(ImportError):
        importlib.import_module("specify_cli.status.migrate")
