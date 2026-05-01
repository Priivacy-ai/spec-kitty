"""Shared pytest fixtures for ``tests/saas/`` — readiness evaluator test layers.

Provides dual-mode rollout fixtures and auth/config/binding factory fixtures
consumed by both ``test_readiness_unit.py`` (stubbed probes) and
``test_readiness_integration.py`` (real evaluator).

Design notes
------------
- ``rollout_disabled`` uses ``monkeypatch.delenv(..., raising=False)`` so it
  safely overrides the global autouse ``_enable_saas_sync_feature_flag`` that
  sets ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` in ``tests/conftest.py:57-60``.
- Auth fixtures monkey-patch ``specify_cli.auth.get_token_manager`` so the
  probe target ``get_token_manager().is_authenticated`` is fully controlled.
  Monkeypatch target: ``specify_cli.auth.get_token_manager``.
- Host-config fixtures drive ``get_saas_base_url()`` through its authoritative
  ``SPEC_KITTY_SAAS_URL`` env-var path per decision D-5.  Do NOT use
  ``SyncConfig.get_server_url()``-based fixtures.
- ``local_http_stub`` binds to ``127.0.0.1:0`` (OS-assigned port) and handles
  HEAD with 200 so reachability tests work without real network access.
"""

from __future__ import annotations

import http.server
import threading
from pathlib import Path
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Rollout gate fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def rollout_disabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Override the global autouse flag — rollout is OFF for this test."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    yield


@pytest.fixture()
def rollout_enabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Ensure the rollout flag is ON for this test (idempotent with autouse)."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    yield


# ---------------------------------------------------------------------------
# Auth fixtures
# ---------------------------------------------------------------------------
#
# Monkeypatch target: ``specify_cli.auth.get_token_manager``
#
# ``get_token_manager()`` is the process-wide factory used by ``_probe_auth``.
# We replace it with a callable that returns a mock ``TokenManager`` whose
# ``is_authenticated`` property is set to True or False as needed.


@pytest.fixture()
def fake_auth_present(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Make the auth probe return True (session present and valid)."""
    mock_tm = MagicMock()
    mock_tm.is_authenticated = True
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: mock_tm)
    yield


@pytest.fixture()
def fake_auth_absent(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Make the auth probe return False (no session)."""
    mock_tm = MagicMock()
    mock_tm.is_authenticated = False
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: mock_tm)
    yield


# ---------------------------------------------------------------------------
# Host-config fixtures
# ---------------------------------------------------------------------------
#
# ``get_saas_base_url()`` reads ``SPEC_KITTY_SAAS_URL`` from the environment.
# These fixtures set/unset that variable so the real helper is exercised.


@pytest.fixture()
def fake_host_config_present(
    monkeypatch: pytest.MonkeyPatch,
    local_http_stub: str,
) -> Generator[str, None, None]:
    """Set ``SPEC_KITTY_SAAS_URL`` to the local HTTP stub URL.

    Returns the URL string so tests can compare it against result fields.
    """
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", local_http_stub)
    yield local_http_stub


@pytest.fixture()
def fake_host_config_absent(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Unset ``SPEC_KITTY_SAAS_URL`` so ``get_saas_base_url()`` raises ``ConfigurationError``."""
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    yield


# ---------------------------------------------------------------------------
# Mission-binding fixtures
# ---------------------------------------------------------------------------
#
# ``_probe_mission_binding`` calls ``load_tracker_config(repo_root).is_configured``.
# These fixtures write (or withhold) a minimal tracker binding in ``tmp_path``.


_FAKE_FEATURE_SLUG = "082-test-feature"


@pytest.fixture()
def fake_mission_binding_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[str, None, None]:
    """Write a minimal tracker binding into ``tmp_path`` and return the feature slug.

    Creates ``.kittify/config.yaml`` with a Linear provider binding so that
    ``load_tracker_config(tmp_path).is_configured`` returns ``True``.
    """
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    config_file = kittify / "config.yaml"
    config_file.write_text(
        "tracker:\n  provider: linear\n  binding_ref: TEST-123\n",
        encoding="utf-8",
    )
    yield _FAKE_FEATURE_SLUG


@pytest.fixture()
def fake_mission_binding_absent(tmp_path: Path) -> Generator[str, None, None]:
    """Return the feature slug but establish NO tracker binding in ``tmp_path``.

    ``load_tracker_config(tmp_path).is_configured`` will return ``False``.
    """
    # Ensure .kittify exists but no tracker section
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    yield _FAKE_FEATURE_SLUG


# ---------------------------------------------------------------------------
# Local HTTP stub (for reachability tests)
# ---------------------------------------------------------------------------


class _HeadOkHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP handler that returns 200 for HEAD requests."""

    def do_HEAD(self) -> None:  # noqa: N802
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Suppress server request logs in test output.
        pass


@pytest.fixture()
def local_http_stub() -> Generator[str, None, None]:
    """Start a local HTTP server bound to ``127.0.0.1:0`` and yield its URL.

    The server handles HEAD requests with 200.  It runs in a daemon thread so
    it is stopped automatically when the test process exits, and is explicitly
    shut down after each test via ``server.shutdown()``.

    Port assignment via ``0`` avoids hardcoded-port conflicts in parallel test
    runs.
    """
    server = http.server.HTTPServer(("127.0.0.1", 0), _HeadOkHandler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield url

    server.shutdown()
    thread.join(timeout=2.0)
