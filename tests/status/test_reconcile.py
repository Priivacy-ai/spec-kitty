"""Tests confirming reconcile.py module was deleted in WP05.

reconcile.py was deleted as part of the canonical state architecture cleanup
(WP05). Cross-repo drift detection and event generation are no longer needed
since the event log is the sole authority.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.fast


def test_reconcile_module_does_not_exist():
    """Verify reconcile.py was deleted and cannot be imported."""
    with pytest.raises(ImportError):
        importlib.import_module("specify_cli.status.reconcile")
