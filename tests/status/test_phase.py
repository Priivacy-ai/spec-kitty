"""Tests confirming phase.py module was deleted in WP05.

phase.py was deleted as part of the canonical state architecture cleanup
(WP05). The three-phase model (0=hardening, 1=dual-write, 2=read-cutover)
is no longer needed since the event log is the sole authority.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.fast


def test_phase_module_does_not_exist():
    """Verify phase.py was deleted and cannot be imported."""
    with pytest.raises(ImportError):
        importlib.import_module("specify_cli.status.phase")


def test_resolve_phase_not_in_status_init():
    """Verify resolve_phase is not exported from status __init__."""
    import specify_cli.status as status_pkg

    assert not hasattr(status_pkg, "resolve_phase"), (
        "resolve_phase was removed in WP05 (phase.py deleted)"
    )
    assert not hasattr(status_pkg, "DEFAULT_PHASE"), (
        "DEFAULT_PHASE was removed in WP05 (phase.py deleted)"
    )
    assert not hasattr(status_pkg, "VALID_PHASES"), (
        "VALID_PHASES was removed in WP05 (phase.py deleted)"
    )
