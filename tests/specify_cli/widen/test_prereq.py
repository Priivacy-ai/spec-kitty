"""Tests for ``specify_cli.widen.prereq``.

Stubs — full test suite implemented in WP10.
"""

from __future__ import annotations

from unittest.mock import MagicMock


from specify_cli.saas_client import SaasClientError
from specify_cli.widen.models import PrereqState
from specify_cli.widen.prereq import check_prereqs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(token: str = "tok", integrations: list[str] | None = None, health: bool = True) -> MagicMock:
    """Return a mock SaasClient with configurable behaviour."""
    client = MagicMock()
    # Use has_token property (public API) rather than the private _token attribute.
    client.has_token = bool(token)
    if integrations is not None:
        client.get_team_integrations.return_value = integrations
    else:
        client.get_team_integrations.return_value = []
    client.health_probe.return_value = health
    return client


# ---------------------------------------------------------------------------
# check_prereqs — all satisfied
# ---------------------------------------------------------------------------


def test_all_satisfied_when_token_slack_health_ok() -> None:
    client = _make_client(token="valid-token", integrations=["slack", "github"], health=True)
    state = check_prereqs(client, "my-team")
    assert state.all_satisfied is True
    assert state.teamspace_ok is True
    assert state.slack_ok is True
    assert state.saas_reachable is True


# ---------------------------------------------------------------------------
# check_prereqs — token absent
# ---------------------------------------------------------------------------


def test_all_false_when_token_absent() -> None:
    """C-009: returns PrereqState(all_satisfied=False) when token is absent."""
    client = _make_client(token="", integrations=["slack"], health=True)
    state = check_prereqs(client, "my-team")
    assert state.all_satisfied is False
    assert state.teamspace_ok is False
    # slack_ok skipped because teamspace_ok is False
    assert state.slack_ok is False


# ---------------------------------------------------------------------------
# check_prereqs — slack missing
# ---------------------------------------------------------------------------


def test_all_satisfied_false_when_slack_not_in_integrations() -> None:
    client = _make_client(token="valid-token", integrations=["github"], health=True)
    state = check_prereqs(client, "my-team")
    assert state.all_satisfied is False
    assert state.slack_ok is False


# ---------------------------------------------------------------------------
# check_prereqs — SaaS unreachable
# ---------------------------------------------------------------------------


def test_all_satisfied_false_when_health_probe_fails() -> None:
    client = _make_client(token="valid-token", integrations=["slack"], health=False)
    state = check_prereqs(client, "my-team")
    assert state.all_satisfied is False
    assert state.saas_reachable is False


# ---------------------------------------------------------------------------
# check_prereqs — never raises even when client blows up
# ---------------------------------------------------------------------------


def test_check_prereqs_never_raises_on_client_error() -> None:
    client = MagicMock()
    client.has_token = True
    client.get_team_integrations.side_effect = SaasClientError("boom")
    client.health_probe.return_value = False
    # Should not raise
    state = check_prereqs(client, "my-team")
    assert isinstance(state, PrereqState)
    assert state.slack_ok is False


def test_check_prereqs_never_raises_on_unexpected_exception() -> None:
    client = MagicMock()
    # Simulate has_token access raising
    type(client).has_token = property(lambda self: (_ for _ in ()).throw(RuntimeError("unexpected")))
    client.health_probe.return_value = False
    state = check_prereqs(client, "my-team")
    assert isinstance(state, PrereqState)
    assert state.teamspace_ok is False


# ---------------------------------------------------------------------------
# PrereqState.all_satisfied is a property, not a field
# ---------------------------------------------------------------------------


def test_prereq_state_all_satisfied_is_property() -> None:
    """Reviewer requirement: all_satisfied must be @property, not a field."""
    import dataclasses

    fields = {f.name for f in dataclasses.fields(PrereqState)}
    assert "all_satisfied" not in fields, "all_satisfied must be a @property, not a dataclass field"


# ---------------------------------------------------------------------------
# Stub markers for WP10 expansion
# ---------------------------------------------------------------------------


def test_check_slack_with_empty_team_slug_stub() -> None:
    """_check_slack returns False when team_slug is empty string (SaasNotFoundError)."""
    from specify_cli.saas_client import SaasNotFoundError

    client = MagicMock()
    client.has_token = True
    # Empty team_slug → 404 from SaaS
    client.get_team_integrations.side_effect = SaasNotFoundError("not found", status_code=404)
    client.health_probe.return_value = True
    state = check_prereqs(client, "")
    assert state.slack_ok is False
    assert state.all_satisfied is False


def test_check_health_probe_timeout_stub() -> None:
    """health_probe timeout is absorbed by client.health_probe() returning False."""
    client = MagicMock()
    client.has_token = True
    client.get_team_integrations.return_value = ["slack"]
    # health_probe never raises — it swallows timeouts and returns False
    client.health_probe.return_value = False
    state = check_prereqs(client, "my-team")
    assert state.saas_reachable is False
    assert state.all_satisfied is False
