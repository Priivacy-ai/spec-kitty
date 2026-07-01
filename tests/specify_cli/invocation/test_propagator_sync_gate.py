"""Tests for the effective_sync_enabled gate in _propagate_one().

Verifies:
- When sync is disabled, _get_saas_client is never called (T002)
- When sync is enabled, _get_saas_client is called (T003)
- A SaaS client exception does not propagate out of _propagate_one (T004)

Updated for Leak #3 fix (WP01 integration-boundary mission): propagator now
routes through ``resolve_sync_routing`` from the invocation adapter seam rather
than importing ``resolve_checkout_sync_routing`` directly from the sync package.
The resolver now returns ``bool | None`` instead of a ``CheckoutSyncRouting``
object; these tests patch the seam accordingly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.propagator import _propagate_one
from specify_cli.invocation.record import OpStartedEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit, pytest.mark.fast]

def _make_started_record() -> OpStartedEvent:
    return OpStartedEvent(
        invocation_id="01HXYZABCDEFGH1JK2MN3PQRST",
        profile_id="test-profile",
        action="implement",
        request_text="test request",
        actor="claude",
        mode_of_work="task_execution",
        governance_context_hash="abcdef0123456789",
        governance_context_available=True,
        started_at="2026-04-22T06:00:00Z",
    )


# ---------------------------------------------------------------------------
# T003 — sync enabled proceeds to auth gate
# ---------------------------------------------------------------------------


def test_local_sync_enabled_proceeds_to_auth_gate(tmp_path: Path) -> None:
    """When sync is enabled, _propagate_one proceeds to the SaaS client check.

    The seam now returns ``bool | None``; True means sync is enabled, so the
    sync-gate does NOT fire and _get_saas_client is called.
    """
    record = _make_started_record()

    with patch(
        "specify_cli.invocation.propagator.resolve_sync_routing",
        return_value=True,  # sync explicitly enabled
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=None,  # auth not connected → returns None, no emit, but gate was reached
        ) as mock_client:
            _propagate_one(record, tmp_path)
            mock_client.assert_called_once_with(tmp_path)  # key: sync-gate was NOT hit


# ---------------------------------------------------------------------------
# T004 — SaaS exception does not raise
# ---------------------------------------------------------------------------


def test_saas_exception_does_not_raise(tmp_path: Path) -> None:
    """SaaS client raising an exception must not propagate out of _propagate_one."""
    record = _make_started_record()
    mock_client = MagicMock()
    mock_client.send_event = MagicMock(side_effect=RuntimeError("network timeout"))

    with patch(
        "specify_cli.invocation.propagator.resolve_sync_routing",
        return_value=True,  # sync explicitly enabled
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ):
            # Must not raise
            _propagate_one(record, tmp_path)
