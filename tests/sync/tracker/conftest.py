"""Shared fixtures for ``tests/sync/tracker/``.

After the WP08 HTTP-transport rewire, ``SaaSTrackerClient`` no longer accepts a
``credential_store`` argument — tokens are fetched through the process-wide
``TokenManager`` via two module-level sync bridges in
``specify_cli.tracker.saas_client``:

* ``_fetch_access_token_sync()``
* ``_current_team_slug_sync()``
* ``_force_refresh_sync()``

Most legacy tests in this directory still carry ``mock_credential_store``
fixtures (with ``get_access_token``/``get_team_slug`` MagicMocks) and pass a
``credential_store=`` kwarg to the client. Rather than rewrite every test
body, we install an autouse fixture that:

1. Patches the three sync bridges so they read from whichever
   ``mock_credential_store`` / stored-value the test sets up, and
2. Monkeypatches ``SaaSTrackerClient.__init__`` to accept and ignore the
   legacy ``credential_store=`` kwarg (stashing it on the instance for tests
   that still poke at ``client._credential_store``).

This keeps the tests focused on contract assertions without forcing a
ground-up rewrite.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.tracker import saas_client as _saas_mod


class _LegacyAuthClientShim:
    """Dummy class exposed on the saas_client module for tracker-test compatibility.

    Older tracker tests historically patched a module-level auth client class and
    asserted that ``refresh_tokens()`` was invoked during 401 recovery. The compat
    ``_force_refresh_sync`` bridge below preserves that behavior by instantiating
    whichever class is currently attached and forwarding to its
    ``refresh_tokens()`` method, turning any ``side_effect`` into the runtime
    error path that the tracker client translates into ``Session expired``.
    """

    credential_store: Any = None
    config: Any = None

    def refresh_tokens(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def _patch_saas_token_bridges(monkeypatch, request):
    """Route the sync token bridges through a test-controlled fake.

    The fake reads from ``mock_credential_store`` if the test defines it as a
    fixture, falling back to sensible defaults. If a test wants dynamic
    behavior (e.g. flipping the token mid-test) it can simply reach into
    ``client._credential_store`` and set new return values — our fake will
    pick them up on the next call.
    """

    # Try to resolve the fixture lazily; not every test file defines it.
    fake_store: Any
    try:
        fake_store = request.getfixturevalue("mock_credential_store")
    except Exception:
        fake_store = MagicMock()
        fake_store.get_access_token.return_value = "test-access-token"
        fake_store.get_team_slug.return_value = "team-acme"
        fake_store.get_refresh_token.return_value = "test-refresh-token"

    # Expose a legacy-compatible auth-client attribute on the module so older
    # tracker tests can still swap in a MagicMock class if needed.
    monkeypatch.setattr(
        _saas_mod, "AuthClient", _LegacyAuthClientShim, raising=False
    )

    def _fetch_access_token_sync() -> str | None:
        try:
            return fake_store.get_access_token()
        except Exception:
            return None

    def _current_team_slug_sync() -> str | None:
        try:
            return fake_store.get_team_slug()
        except Exception:
            return None

    def _force_refresh_sync() -> bool:
        # Honor the currently attached (possibly patched) AuthClient class:
        # instantiate it and call refresh_tokens(). This is the hook that
        # legacy tests use to assert refresh_tokens was called or to inject
        # a ``side_effect`` that should propagate as "Session expired".
        auth_cls = getattr(_saas_mod, "AuthClient", _LegacyAuthClientShim)
        try:
            auth_cls().refresh_tokens()
        except AttributeError:
            pass
        return True

    monkeypatch.setattr(_saas_mod, "_fetch_access_token_sync", _fetch_access_token_sync)
    monkeypatch.setattr(_saas_mod, "_current_team_slug_sync", _current_team_slug_sync)
    monkeypatch.setattr(_saas_mod, "_force_refresh_sync", _force_refresh_sync)

    # Also patch the legacy ``SaaSTrackerClient.__init__`` to accept (and
    # stash) the removed ``credential_store=`` kwarg so older fixtures keep
    # constructing clients the way they used to.
    real_init = _saas_mod.SaaSTrackerClient.__init__

    def _compat_init(
        self,
        sync_config=None,
        *,
        credential_store=None,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> None:
        real_init(self, sync_config=sync_config, timeout=timeout, **kwargs)
        # Legacy tests inspect ``client._credential_store``; preserve that.
        self._credential_store = credential_store if credential_store is not None else fake_store

    monkeypatch.setattr(_saas_mod.SaaSTrackerClient, "__init__", _compat_init)

    yield
