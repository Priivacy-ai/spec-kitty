"""Unit tests for sync package lazy exports."""

from __future__ import annotations

import pytest

import specify_cli.sync as sync_package
from specify_cli.sync import feature_flags
from specify_cli.sync import events


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_lazy_feature_flag_exports_resolve_to_canonical_symbols() -> None:
    """Package-level feature-flag exports should stay wired to the same module."""
    assert sync_package.SAAS_SYNC_ENV_VAR == feature_flags.SAAS_SYNC_ENV_VAR
    assert sync_package.is_saas_sync_enabled is feature_flags.is_saas_sync_enabled
    assert sync_package.saas_sync_disabled_message is feature_flags.saas_sync_disabled_message


def test_lazy_event_exports_resolve_to_events_module_symbols() -> None:
    """Package-level event exports should continue delegating to events.py."""
    assert sync_package.get_emitter is events.get_emitter
    assert sync_package.reset_emitter is events.reset_emitter
    assert sync_package.emit_wp_status_changed is events.emit_wp_status_changed
    assert sync_package.emit_diff_summary_recorded is events.emit_diff_summary_recorded
    assert sync_package.emit_proof_event is events.emit_proof_event
