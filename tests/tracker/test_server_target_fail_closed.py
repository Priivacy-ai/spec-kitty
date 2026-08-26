"""Fail-closed hosted-target tests for the tracker surfaces (#179).

``server_target.DEFAULT_SERVER_URL`` pointed at ``https://spec-kitty-dev.fly.dev``,
a host that no longer exists (Fly hosting left the programme). Deleting the
default means every hosted path fails closed on an unconfigured machine:

* :class:`~specify_cli.tracker.saas_client.SaaSTrackerClient` construction
  raises :class:`ConfigurationError` instead of silently binding a dead host;
* :func:`~specify_cli.tracker.saas_readiness.evaluate_readiness` yields
  ``MISSING_HOST_CONFIG`` (its no-raise representation of the same condition).

Neither case may open a network connection — that is asserted here by arming
the network seams with failures.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.auth.errors import ConfigurationError
from specify_cli.auth.server_target import SAAS_URL_ENV_VAR
from specify_cli.tracker.saas_client import SaaSTrackerClient
from specify_cli.tracker.saas_readiness import ReadinessState, evaluate_readiness

pytestmark = pytest.mark.fast


@pytest.fixture
def unconfigured_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """No env value, no ``config.toml`` — nothing names a server."""
    monkeypatch.delenv(SAAS_URL_ENV_VAR, raising=False)
    home = tmp_path / "empty-home"
    home.mkdir()
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    return tmp_path


def _refuse_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a network call was attempted on an unconfigured machine")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    monkeypatch.setattr(
        "specify_cli.tracker.saas_client.httpx.Client",
        MagicMock(side_effect=_boom),
    )


def test_saas_client_construction_without_host_fails_closed(unconfigured_host: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No env and no config ⇒ ``ConfigurationError``, not a bound dead host."""
    _refuse_network(monkeypatch)

    with pytest.raises(ConfigurationError) as excinfo:
        SaaSTrackerClient(project_root=unconfigured_host / "repo")

    assert SAAS_URL_ENV_VAR in str(excinfo.value)


def test_evaluate_readiness_without_host_yields_missing_host_config(unconfigured_host: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The readiness evaluator translates the same condition into
    ``MISSING_HOST_CONFIG`` (its no-raise contract) without probing the wire."""
    _refuse_network(monkeypatch)
    # Order: rollout gate → auth → host config. Pass the first two so the
    # evaluation actually reaches the host-config check under test.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr("specify_cli.tracker.saas_readiness._probe_auth", lambda _repo_root: True)

    result = evaluate_readiness(
        repo_root=unconfigured_host / "repo",
        probe_reachability=True,
    )

    assert result.state is ReadinessState.MISSING_HOST_CONFIG
    assert not result.is_ready
    assert "SPEC_KITTY_SAAS_URL" in (result.next_action or "")
