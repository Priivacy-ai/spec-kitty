"""Tests confirming legacy_bridge module was deleted in WP05.

legacy_bridge.py was deleted as part of the canonical state architecture
cleanup (WP05). The event log is now the sole authority; no frontmatter
dual-write paths remain.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.fast


def test_legacy_bridge_module_does_not_exist():
    """Verify legacy_bridge was deleted and cannot be imported."""
    with pytest.raises(ImportError):
        importlib.import_module("specify_cli.status.legacy_bridge")


def test_update_all_views_not_in_status_init():
    """Verify update_all_views is not exported from status __init__."""
    import specify_cli.status as status_pkg

    assert not hasattr(status_pkg, "update_all_views"), (
        "update_all_views was removed in WP05 (legacy_bridge deleted)"
    )
    assert not hasattr(status_pkg, "update_frontmatter_views"), (
        "update_frontmatter_views was removed in WP05 (legacy_bridge deleted)"
    )
    assert not hasattr(status_pkg, "update_tasks_md_views"), (
        "update_tasks_md_views was removed in WP05 (legacy_bridge deleted)"
    )
