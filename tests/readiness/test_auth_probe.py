"""Unit tests for the readiness auth probe (WS2, issue #1094).

Asserts that each producible ``AuthStatus`` value is reachable from
``probe_auth_status``, including the ``UNKNOWN`` exception fallback.

The probe is gated by the coordinator behind ``is_saas_sync_enabled()``;
these tests exercise the probe directly so they do not depend on the
``SPEC_KITTY_ENABLE_SAAS_SYNC`` env var.
"""

from __future__ import annotations

import pytest

from specify_cli.readiness import auth as auth_module
from specify_cli.readiness.auth import probe_auth_status
from specify_cli.readiness.coordinator import AuthStatus


pytestmark = [pytest.mark.unit, pytest.mark.fast]


class _FakeTokenManager:
    def __init__(self, authenticated: bool, raise_on_authenticated: bool = False) -> None:
        self._authenticated = authenticated
        self._raise = raise_on_authenticated

    @property
    def is_authenticated(self) -> bool:
        if self._raise:
            raise RuntimeError("synthetic token-manager failure")
        return self._authenticated


def _patch_token_manager(monkeypatch: pytest.MonkeyPatch, tm: _FakeTokenManager) -> None:
    # The probe imports lazily via ``from specify_cli.auth import get_token_manager``.
    import specify_cli.auth as auth_pkg

    monkeypatch.setattr(auth_pkg, "get_token_manager", lambda: tm)


def _patch_detector(monkeypatch: pytest.MonkeyPatch, return_value: str | None) -> None:
    # The probe imports the helper lazily from ``_auth_recovery``.
    import specify_cli.cli.commands._auth_recovery as recovery_mod

    monkeypatch.setattr(
        recovery_mod,
        "detect_logged_out_with_connected_teamspace",
        lambda repo_root=None: return_value,
    )


def test_probe_authenticated_returns_authenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_token_manager(monkeypatch, _FakeTokenManager(authenticated=True))
    # Detector should not be consulted when authenticated; if it is, fail loudly.
    _patch_detector(monkeypatch, "should-not-be-read")

    status, handle = probe_auth_status()

    assert status == AuthStatus.AUTHENTICATED
    assert handle is None


def test_probe_logged_out_with_teamspace_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_token_manager(monkeypatch, _FakeTokenManager(authenticated=False))
    _patch_detector(monkeypatch, "acme-team")

    status, handle = probe_auth_status()

    assert status == AuthStatus.LOGGED_OUT_IN_TEAMSPACE
    assert handle == "acme-team"


def test_probe_logged_out_with_whitespace_handle_is_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_token_manager(monkeypatch, _FakeTokenManager(authenticated=False))
    _patch_detector(monkeypatch, "   acme-team   ")

    status, handle = probe_auth_status()

    assert status == AuthStatus.LOGGED_OUT_IN_TEAMSPACE
    assert handle == "acme-team"


def test_probe_logged_out_with_empty_handle_is_not_in_teamspace(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_token_manager(monkeypatch, _FakeTokenManager(authenticated=False))
    _patch_detector(monkeypatch, "   ")

    status, handle = probe_auth_status()

    assert status == AuthStatus.NOT_IN_TEAMSPACE
    assert handle is None


def test_probe_not_in_teamspace_when_helper_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_token_manager(monkeypatch, _FakeTokenManager(authenticated=False))
    _patch_detector(monkeypatch, None)

    status, handle = probe_auth_status()

    assert status == AuthStatus.NOT_IN_TEAMSPACE
    assert handle is None


def test_probe_unknown_on_token_manager_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate the lazy ``from specify_cli.auth import get_token_manager`` blowing up
    # by monkeypatching the attribute to a sentinel that raises on access.
    import specify_cli.auth as auth_pkg

    def _boom() -> object:
        raise RuntimeError("synthetic import failure")

    monkeypatch.setattr(auth_pkg, "get_token_manager", _boom)

    status, handle = probe_auth_status()

    assert status == AuthStatus.UNKNOWN
    assert handle is None


def test_probe_unknown_on_token_manager_is_authenticated_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # ``is_authenticated`` raises. Probe should not treat it as "authenticated"; it
    # should swallow the exception and fall through to the detector. With the
    # detector returning None we expect NOT_IN_TEAMSPACE (defensive fall-through),
    # not UNKNOWN — UNKNOWN is reserved for the catastrophic failure path.
    _patch_token_manager(
        monkeypatch,
        _FakeTokenManager(authenticated=False, raise_on_authenticated=True),
    )
    _patch_detector(monkeypatch, None)

    status, handle = probe_auth_status()

    assert status == AuthStatus.NOT_IN_TEAMSPACE
    assert handle is None


def test_probe_unknown_on_detector_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_token_manager(monkeypatch, _FakeTokenManager(authenticated=False))

    import specify_cli.cli.commands._auth_recovery as recovery_mod

    def _boom(repo_root=None):  # noqa: ANN001
        raise RuntimeError("synthetic detector failure")

    monkeypatch.setattr(recovery_mod, "detect_logged_out_with_connected_teamspace", _boom)

    status, handle = probe_auth_status()

    assert status == AuthStatus.UNKNOWN
    assert handle is None


def test_probe_module_exports() -> None:
    assert hasattr(auth_module, "probe_auth_status")
    assert callable(auth_module.probe_auth_status)
    assert auth_module.__all__ == ["probe_auth_status"]
