"""Integration tests for ``specify_cli.saas.readiness.evaluate_readiness``.

These tests exercise the **real** evaluator against fixture-backed auth,
config, and binding state.  Probes are NOT stubbed here — the entire call
chain (``_probe_auth`` → ``get_token_manager().is_authenticated``, etc.) runs.

Test cases
----------
1. Happy path (READY): all prerequisites present, ``probe_reachability=True``,
   ``require_mission_binding=True``.
2. MISSING_AUTH: rollout enabled, no auth session.
3. MISSING_HOST_CONFIG: rollout enabled, auth present, SPEC_KITTY_SAAS_URL unset.
4. MISSING_MISSION_BINDING: all earlier prerequisites present, no binding.
5. HOST_UNREACHABLE: port 1 is unreachable within 2 s
   (guarded by ``@pytest.mark.timeout(5)``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.saas.readiness import ReadinessState, evaluate_readiness

# ---------------------------------------------------------------------------
# 1. Happy path — READY
# ---------------------------------------------------------------------------


def test_happy_path_ready(
    rollout_enabled: None,
    fake_auth_present: None,
    fake_host_config_present: str,
    fake_mission_binding_present: str,
    tmp_path: Path,
) -> None:
    """All prerequisites present → READY."""
    result = evaluate_readiness(
        repo_root=tmp_path,
        feature_slug=fake_mission_binding_present,
        require_mission_binding=True,
        probe_reachability=True,
    )

    assert result.state is ReadinessState.READY, f"Unexpected state: {result}"
    assert result.is_ready
    assert result.next_action is None
    assert result.message == ""


# ---------------------------------------------------------------------------
# 2. MISSING_AUTH
# ---------------------------------------------------------------------------

_MISSING_AUTH_MESSAGE = "No SaaS authentication token is present."
_MISSING_AUTH_NEXT_ACTION = "Run `spec-kitty auth login`."


def test_missing_auth(
    rollout_enabled: None,
    fake_auth_absent: None,
    tmp_path: Path,
) -> None:
    """No auth session → MISSING_AUTH with stable wording."""
    result = evaluate_readiness(repo_root=tmp_path)

    assert result.state is ReadinessState.MISSING_AUTH
    assert result.message == _MISSING_AUTH_MESSAGE
    assert result.next_action == _MISSING_AUTH_NEXT_ACTION
    assert not result.is_ready


# ---------------------------------------------------------------------------
# 3. MISSING_HOST_CONFIG
# ---------------------------------------------------------------------------

_MISSING_HOST_CONFIG_MESSAGE = "No SaaS host URL is configured."
_MISSING_HOST_CONFIG_NEXT_ACTION = "Set `SPEC_KITTY_SAAS_URL` in your environment."


def test_missing_host_config(
    rollout_enabled: None,
    fake_auth_present: None,
    fake_host_config_absent: None,
    tmp_path: Path,
) -> None:
    """SPEC_KITTY_SAAS_URL unset → MISSING_HOST_CONFIG with stable wording."""
    result = evaluate_readiness(repo_root=tmp_path)

    assert result.state is ReadinessState.MISSING_HOST_CONFIG
    assert result.message == _MISSING_HOST_CONFIG_MESSAGE
    assert result.next_action == _MISSING_HOST_CONFIG_NEXT_ACTION
    assert not result.is_ready


# ---------------------------------------------------------------------------
# 4. MISSING_MISSION_BINDING
# ---------------------------------------------------------------------------

_MISSING_BINDING_NEXT_ACTION = "Run `spec-kitty tracker bind` from this repo."


def test_missing_mission_binding(
    rollout_enabled: None,
    fake_auth_present: None,
    fake_host_config_present: str,
    fake_mission_binding_absent: str,
    tmp_path: Path,
) -> None:
    """All earlier prerequisites pass but no binding → MISSING_MISSION_BINDING."""
    slug = fake_mission_binding_absent

    result = evaluate_readiness(
        repo_root=tmp_path,
        feature_slug=slug,
        require_mission_binding=True,
    )

    assert result.state is ReadinessState.MISSING_MISSION_BINDING
    assert slug in result.message, f"feature_slug not in message: {result.message!r}"
    assert result.next_action == _MISSING_BINDING_NEXT_ACTION
    assert not result.is_ready


# ---------------------------------------------------------------------------
# 5. HOST_UNREACHABLE (port 1 should be unreachable)
# ---------------------------------------------------------------------------

_HOST_UNREACHABLE_MESSAGE = (
    "The configured SaaS host did not respond within 2 seconds."
)


@pytest.mark.timeout(5)
def test_host_unreachable(
    rollout_enabled: None,
    fake_auth_present: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An unreachable host (port 1) → HOST_UNREACHABLE within the 2 s budget."""
    # Port 1 is reserved and should be unreachable without special privileges.
    unreachable_url = "http://127.0.0.1:1"
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", unreachable_url)

    result = evaluate_readiness(
        repo_root=tmp_path,
        probe_reachability=True,
    )

    assert result.state is ReadinessState.HOST_UNREACHABLE
    assert result.message == _HOST_UNREACHABLE_MESSAGE
    assert not result.is_ready
    # next_action should contain the server URL
    assert result.next_action is not None
    assert "127.0.0.1" in result.next_action
