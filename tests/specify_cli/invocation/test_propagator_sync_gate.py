"""Tests for the consent gate in _propagate_one() — check ordering and no-raise.

Verifies:
- When consent is granted, _get_saas_client is called (T003)
- A SaaS client exception does not propagate out of _propagate_one (T004)

Updated for Leak #3 fix (WP01 integration-boundary mission): propagator routes
through the invocation adapter seam rather than importing
``resolve_checkout_sync_routing`` directly from the sync package.

Updated again for #3030 FR-025: the seam answers ``EgressConsent`` — "may this
project's data leave" — instead of ``bool | None`` "is sync enabled for this
checkout". The tri-state is gone because the propagator's ``is False`` test read
its ``None`` (no resolver / resolver raised) as permission to send. The verdicts
the *gate* produces are pinned in ``test_propagator_consent_gate_3030.py``,
against the real sync-side resolver; these two patch the seam so they can isolate
the check ORDER, which is a different property.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.adapters import EgressConsent
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
# T003 — granted consent proceeds to the auth gate
# ---------------------------------------------------------------------------


def test_granted_consent_proceeds_to_auth_gate(tmp_path: Path) -> None:
    """When the project consents, _propagate_one proceeds to the SaaS client check.

    GRANTED is the one verdict that does not fire the gate, so _get_saas_client is
    reached. Its converse — that every other verdict stops here — is pinned in
    ``test_propagator_consent_gate_3030.py`` on the payload rather than on this
    call, because a gate can be reached and still send.
    """
    record = _make_started_record()

    with patch(
        "specify_cli.invocation.propagator.resolve_egress_consent",
        return_value=EgressConsent.GRANTED,  # the project consents
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=None,  # auth not connected → returns None, no emit, but gate was reached
        ) as mock_client:
            _propagate_one(record, tmp_path)
            mock_client.assert_called_once_with(tmp_path)  # key: consent gate was NOT hit


# ---------------------------------------------------------------------------
# T004 — SaaS exception does not raise
# ---------------------------------------------------------------------------


def test_saas_exception_does_not_raise(tmp_path: Path) -> None:
    """SaaS client raising an exception must not propagate out of _propagate_one."""
    record = _make_started_record()
    mock_client = MagicMock()
    mock_client.send_event = MagicMock(side_effect=RuntimeError("network timeout"))

    with patch(
        "specify_cli.invocation.propagator.resolve_egress_consent",
        return_value=EgressConsent.GRANTED,  # the project consents
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ):
            # Must not raise
            _propagate_one(record, tmp_path)
