"""Unit tests for ``specify_cli.saas.readiness``.

Every prerequisite probe is stubbed so tests are fast and fully isolated.
Each ``ReadinessState`` member has at least one test that produces that state
and asserts the wording byte-for-byte against the contract table.

Test inventory
--------------
- One test per state that reaches that state via minimum-sufficient probe rigging.
- Byte-wise wording assertions for every non-READY state.
- Ordering: combined failures assert the earlier-declared state wins.
- Exception conversion: ``_probe_auth`` raising → ``HOST_UNREACHABLE``, no raise.
- ``probe_reachability=False`` → reachability probe never called.
- ``require_mission_binding=False`` → binding probe never called.
- Parametrize over ``rollout_disabled`` / ``rollout_enabled`` modes for the
  ``ROLLOUT_DISABLED`` path.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.saas.readiness import ReadinessState, evaluate_readiness

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO = Path("/fake/repo")  # never accessed in unit tests — probes are stubbed


def _stub_all_pass(monkeypatch: pytest.MonkeyPatch, *, server_url: str = "http://stub") -> None:
    """Stub all probes to pass (return True / server_url)."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_host_config", lambda: server_url)
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_reachability", lambda *_, **__: True
    )
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_mission_binding", lambda *_: True
    )


# ---------------------------------------------------------------------------
# State: ROLLOUT_DISABLED
# ---------------------------------------------------------------------------

_ROLLOUT_DISABLED_MESSAGE = "Hosted SaaS sync is not enabled on this machine."
_ROLLOUT_DISABLED_NEXT_ACTION = "Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in."


@pytest.mark.parametrize(
    "fixture_name",
    ["rollout_disabled", "rollout_enabled"],
    ids=["rollout_disabled", "rollout_enabled"],
)
def test_rollout_disabled_state(
    fixture_name: str,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ROLLOUT_DISABLED is returned iff the rollout probe fails."""
    # Load the named rollout fixture
    request.getfixturevalue(fixture_name)

    rollout_value = fixture_name == "rollout_enabled"
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: rollout_value)
    # Stub remaining probes as passing so the only variable is rollout.
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_host_config", lambda: "http://x")
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_reachability", lambda *_, **__: True
    )
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_mission_binding", lambda *_: True
    )

    result = evaluate_readiness(repo_root=_REPO)

    if fixture_name == "rollout_disabled":
        assert result.state is ReadinessState.ROLLOUT_DISABLED
        # Byte-wise wording assertions
        assert result.message == _ROLLOUT_DISABLED_MESSAGE
        assert result.next_action == _ROLLOUT_DISABLED_NEXT_ACTION
        assert not result.is_ready
    else:
        assert result.state is ReadinessState.READY
        assert result.is_ready


# ---------------------------------------------------------------------------
# State: MISSING_AUTH
# ---------------------------------------------------------------------------

_MISSING_AUTH_MESSAGE = "No SaaS authentication token is present."
_MISSING_AUTH_NEXT_ACTION = "Run `spec-kitty auth login`."


def test_missing_auth_state(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MISSING_AUTH is returned when rollout passes but auth probe fails."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: False)

    result = evaluate_readiness(repo_root=_REPO)

    assert result.state is ReadinessState.MISSING_AUTH
    assert result.message == _MISSING_AUTH_MESSAGE
    assert result.next_action == _MISSING_AUTH_NEXT_ACTION
    assert not result.is_ready


# ---------------------------------------------------------------------------
# State: MISSING_HOST_CONFIG
# ---------------------------------------------------------------------------

_MISSING_HOST_CONFIG_MESSAGE = "No SaaS host URL is configured."
_MISSING_HOST_CONFIG_NEXT_ACTION = "Set `SPEC_KITTY_SAAS_URL` in your environment."


def test_missing_host_config_state(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MISSING_HOST_CONFIG when rollout+auth pass but host config probe returns None."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_host_config", lambda: None)

    result = evaluate_readiness(repo_root=_REPO)

    assert result.state is ReadinessState.MISSING_HOST_CONFIG
    assert result.message == _MISSING_HOST_CONFIG_MESSAGE
    assert result.next_action == _MISSING_HOST_CONFIG_NEXT_ACTION
    assert not result.is_ready


# ---------------------------------------------------------------------------
# State: HOST_UNREACHABLE
# ---------------------------------------------------------------------------

_HOST_UNREACHABLE_MESSAGE = (
    "The configured SaaS host did not respond within 2 seconds."
)
_HOST_SERVER_URL = "http://stub.example.com"
_HOST_UNREACHABLE_NEXT_ACTION = (
    f"Check network connectivity to `{_HOST_SERVER_URL}` and retry."
)


def test_host_unreachable_state(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HOST_UNREACHABLE when probe_reachability=True and the reachability probe fails."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: True)
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_host_config", lambda: _HOST_SERVER_URL
    )
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_reachability", lambda *_, **__: False
    )

    result = evaluate_readiness(repo_root=_REPO, probe_reachability=True)

    assert result.state is ReadinessState.HOST_UNREACHABLE
    assert result.message == _HOST_UNREACHABLE_MESSAGE
    assert result.next_action == _HOST_UNREACHABLE_NEXT_ACTION
    assert not result.is_ready


# ---------------------------------------------------------------------------
# State: MISSING_MISSION_BINDING
# ---------------------------------------------------------------------------

_MISSING_BINDING_SLUG = "082-test"
_MISSING_BINDING_MESSAGE = f"No tracker binding exists for feature `{_MISSING_BINDING_SLUG}`."
_MISSING_BINDING_NEXT_ACTION = "Run `spec-kitty tracker bind` from this repo."


def test_missing_mission_binding_state(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MISSING_MISSION_BINDING when require_mission_binding=True and probe fails."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: True)
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_host_config", lambda: "http://stub"
    )
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_reachability", lambda *_, **__: True
    )
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_mission_binding", lambda *_: False
    )

    result = evaluate_readiness(
        repo_root=_REPO,
        feature_slug=_MISSING_BINDING_SLUG,
        require_mission_binding=True,
    )

    assert result.state is ReadinessState.MISSING_MISSION_BINDING
    assert result.message == _MISSING_BINDING_MESSAGE
    assert result.next_action == _MISSING_BINDING_NEXT_ACTION
    assert not result.is_ready


# ---------------------------------------------------------------------------
# State: READY
# ---------------------------------------------------------------------------


def test_ready_state(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """READY is returned when all applicable probes pass."""
    _stub_all_pass(monkeypatch)

    result = evaluate_readiness(
        repo_root=_REPO,
        feature_slug="082-some",
        require_mission_binding=True,
        probe_reachability=True,
    )

    assert result.state is ReadinessState.READY
    assert result.is_ready
    assert result.next_action is None
    assert result.message == ""


# ---------------------------------------------------------------------------
# Ordering test
# ---------------------------------------------------------------------------


def test_ordering_auth_beats_host_config(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When auth fails AND host config is absent, MISSING_AUTH wins (earlier)."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: False)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_host_config", lambda: None)

    result = evaluate_readiness(repo_root=_REPO)

    assert result.state is ReadinessState.MISSING_AUTH


def test_ordering_rollout_beats_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When rollout is disabled AND auth fails, ROLLOUT_DISABLED wins (earliest)."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: False)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: False)

    result = evaluate_readiness(repo_root=_REPO)

    assert result.state is ReadinessState.ROLLOUT_DISABLED


# ---------------------------------------------------------------------------
# Exception conversion
# ---------------------------------------------------------------------------


def test_exception_in_probe_yields_host_unreachable_not_raise(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exception inside _probe_auth must NOT propagate — returns HOST_UNREACHABLE."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: True)
    monkeypatch.setattr(
        "specify_cli.saas.readiness._probe_auth",
        lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),  # type: ignore[arg-type]
    )

    # Must not raise
    result = evaluate_readiness(repo_root=_REPO)

    assert result.state is ReadinessState.HOST_UNREACHABLE
    assert result.details.get("error") == "RuntimeError"
    assert not result.is_ready


# ---------------------------------------------------------------------------
# probe_reachability=False → probe never called
# ---------------------------------------------------------------------------


def test_probe_reachability_false_never_calls_probe(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """probe_reachability=False must not invoke _probe_reachability."""
    _stub_all_pass(monkeypatch)

    reachability_mock = MagicMock(return_value=True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_reachability", reachability_mock)

    result = evaluate_readiness(repo_root=_REPO, probe_reachability=False)

    reachability_mock.assert_not_called()
    assert result.state is ReadinessState.READY


# ---------------------------------------------------------------------------
# require_mission_binding=False → binding probe never called
# ---------------------------------------------------------------------------


def test_require_mission_binding_false_never_calls_probe(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """require_mission_binding=False must not invoke _probe_mission_binding."""
    _stub_all_pass(monkeypatch)

    binding_mock = MagicMock(return_value=True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_mission_binding", binding_mock)

    result = evaluate_readiness(repo_root=_REPO, require_mission_binding=False)

    binding_mock.assert_not_called()
    assert result.state is ReadinessState.READY


# ---------------------------------------------------------------------------
# is_ready property
# ---------------------------------------------------------------------------


def test_is_ready_property(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_ready returns True only for READY state."""
    _stub_all_pass(monkeypatch)
    result = evaluate_readiness(repo_root=_REPO)
    assert result.is_ready

    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: False)
    bad_result = evaluate_readiness(repo_root=_REPO)
    assert not bad_result.is_ready


# ---------------------------------------------------------------------------
# details field is empty by default for non-exception results
# ---------------------------------------------------------------------------


def test_non_exception_result_has_empty_details(
    rollout_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-exception failure results should have empty details."""
    monkeypatch.setattr("specify_cli.saas.readiness._probe_rollout", lambda: True)
    monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: False)

    result = evaluate_readiness(repo_root=_REPO)

    assert result.state is ReadinessState.MISSING_AUTH
    assert result.details == {}
