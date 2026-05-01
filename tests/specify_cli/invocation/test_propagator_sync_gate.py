"""Tests for the effective_sync_enabled gate in _propagate_one() (WP01).

Verifies:
- When sync is disabled, _get_saas_client is never called (T002)
- When sync is enabled, _get_saas_client is called (T003)
- A SaaS client exception does not propagate out of _propagate_one (T004)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


from specify_cli.invocation.propagator import _propagate_one
from specify_cli.invocation.record import InvocationRecord
from specify_cli.sync.routing import CheckoutSyncRouting


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_started_record() -> InvocationRecord:
    return InvocationRecord(
        event="started",
        invocation_id="01HXYZABCDEFGHIJKLMNOPQRST",
        profile_id="test-profile",
        action="implement",
        started_at="2026-04-22T06:00:00Z",
    )


def _make_routing(*, effective_sync_enabled: bool) -> CheckoutSyncRouting:
    return CheckoutSyncRouting(
        repo_root=Path("/fake/repo"),
        project_uuid="fake-uuid",
        project_slug="fake-slug",
        build_id=None,
        repo_slug="fake-repo",
        local_sync_enabled=not effective_sync_enabled,
        repo_default_sync_enabled=None,
        effective_sync_enabled=effective_sync_enabled,
    )


# ---------------------------------------------------------------------------
# T002 — sync disabled suppresses SaaS emit
# ---------------------------------------------------------------------------


def test_local_sync_disabled_suppresses_saas_emit(tmp_path: Path) -> None:
    """When sync is explicitly disabled, _propagate_one must return before touching SaaS client."""
    routing = _make_routing(effective_sync_enabled=False)
    record = _make_started_record()

    with (
        patch(
            "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
            return_value=routing,
        ) as mock_routing,
        patch(
            "specify_cli.invocation.propagator._get_saas_client",
        ) as mock_client,
    ):
        _propagate_one(record, tmp_path)
        mock_routing.assert_called_once_with(tmp_path)
        mock_client.assert_not_called()  # key assertion


# ---------------------------------------------------------------------------
# T003 — sync enabled proceeds to auth gate
# ---------------------------------------------------------------------------


def test_local_sync_enabled_proceeds_to_auth_gate(tmp_path: Path) -> None:
    """When sync is enabled, _propagate_one proceeds to the SaaS client check."""
    routing = _make_routing(effective_sync_enabled=True)
    record = _make_started_record()

    with (
        patch(
            "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
            return_value=routing,
        ),
        patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=None,  # auth not connected → returns None, no emit, but gate was reached
        ) as mock_client,
    ):
        _propagate_one(record, tmp_path)
        mock_client.assert_called_once_with(tmp_path)  # key: gate was NOT hit


# ---------------------------------------------------------------------------
# T004 — SaaS exception does not raise
# ---------------------------------------------------------------------------


def test_saas_exception_does_not_raise(tmp_path: Path) -> None:
    """SaaS client raising an exception must not propagate out of _propagate_one."""
    routing = _make_routing(effective_sync_enabled=True)
    record = _make_started_record()
    mock_client = MagicMock()
    mock_client.send_event = MagicMock(side_effect=RuntimeError("network timeout"))

    with (
        patch(
            "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
            return_value=routing,
        ),
        patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ),
    ):
        # Must not raise
        _propagate_one(record, tmp_path)
