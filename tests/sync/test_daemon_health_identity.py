"""Tests for daemon health identity fields (WP04 / T016 / FR-001 / C-001).

These tests verify that ``/api/health`` returns the ``daemon_family`` and
``singleton_scope_id`` fields added in WP04 and that they carry the correct
values so a scanner can confirm identity from the self-report.

Two levels of coverage are provided:
1. ``TestHandleHealthPayload`` — unit-tests the ``handle_health`` method
   directly (no real port) using a minimal stub of the HTTP handler
   infrastructure.
2. ``TestHealthEndpointLive`` — spins up the real daemon subprocess on a
   free port and fires a real HTTP request.  POSIX-only; skipped on Windows.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.sync import daemon

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unused_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_daemon_health(port: int, proc: subprocess.Popen[str]) -> dict[str, Any]:
    """Poll until the daemon responds on ``/api/health``; return the parsed JSON."""
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + 10.0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stdout, stderr = proc.communicate(timeout=1)
            raise AssertionError(
                f"daemon exited before health check: rc={proc.returncode}\n"
                f"stdout={stdout}\nstderr={stderr}"
            )
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:  # noqa: S310
                if response.status == 200:
                    return dict(json.loads(response.read()))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(0.05)
    raise AssertionError(f"daemon health check timed out: {last_error}")


# ---------------------------------------------------------------------------
# Unit-level: inspect the handler method directly
# ---------------------------------------------------------------------------


class TestHandleHealthPayload:
    """Verify ``handle_health`` includes ``daemon_family`` and ``singleton_scope_id``."""

    def _invoke_handle_health(self, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
        """Return the JSON payload that ``handle_health`` would write to the wire."""
        captured: list[dict[str, Any]] = []

        class _Recorder:
            pass

        # Build a minimal handler instance with the recorder and daemon_token.
        # Use a normal subclass so mypy sees a concrete type; avoids the
        # call-overload error that the dynamic type() form triggers.
        class _StubHandler(daemon.SyncDaemonHandler):
            daemon_token = "test-tok"

        # BaseHTTPRequestHandler.__init__ requires a real request + client tuple;
        # bypass it entirely and just populate the instance surface we need.
        handler = _StubHandler.__new__(_StubHandler)

        def fake_send_json(status_code: int, payload: dict[str, Any]) -> None:
            captured.append(payload)

        monkeypatch.setattr(handler, "_send_json", fake_send_json)

        # Stub the runtime so handle_health does not try to import it for real.
        monkeypatch.setitem(sys.modules, "specify_cli.sync.runtime", MagicMock())

        # Stub the owner record helpers so we do not need a real owner.json.
        fake_owner_mod = MagicMock()
        fake_owner_mod.read_owner_record.return_value = None
        fake_owner_mod.redact_token.return_value = None
        monkeypatch.setitem(sys.modules, "specify_cli.sync.owner", fake_owner_mod)

        handler.handle_health()
        assert captured, "handle_health did not call _send_json"
        return captured[0]

    def test_daemon_family_is_sync(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``daemon_family`` must be the literal string ``"sync"``."""
        payload = self._invoke_handle_health(monkeypatch)
        assert payload.get("daemon_family") == "sync", (
            f"Expected daemon_family='sync', got {payload.get('daemon_family')!r}"
        )

    def test_singleton_scope_id_is_present_and_non_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``singleton_scope_id`` must be a non-empty string."""
        payload = self._invoke_handle_health(monkeypatch)
        scope = payload.get("singleton_scope_id")
        assert isinstance(scope, str) and scope, (
            f"Expected non-empty singleton_scope_id, got {scope!r}"
        )

    def test_singleton_scope_id_matches_daemon_scope_root(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``singleton_scope_id`` in the payload must equal ``_daemon_scope_root()``."""
        payload = self._invoke_handle_health(monkeypatch)
        expected = daemon._daemon_scope_root()
        assert payload.get("singleton_scope_id") == expected, (
            f"scope_id mismatch: payload={payload.get('singleton_scope_id')!r} "
            f"vs _daemon_scope_root()={expected!r}"
        )

    def test_existing_fields_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Additive-only contract: pre-existing keys must still be present."""
        payload = self._invoke_handle_health(monkeypatch)
        for key in ("status", "token", "protocol_version", "package_version", "sync", "websocket_status"):
            assert key in payload, f"Pre-existing key {key!r} missing from health payload"

    def test_token_is_present_in_payload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``token`` must appear (redaction happens on the scanner side, not here)."""
        payload = self._invoke_handle_health(monkeypatch)
        # The handler surfaces the raw token to loopback callers; it is not
        # redacted at the handler level.
        assert "token" in payload

    def test_daemon_family_is_additive_before_owner(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``daemon_family`` appears before the optional ``owner`` block — still present."""
        payload = self._invoke_handle_health(monkeypatch)
        # ``owner`` is absent here (stubbed to None); family must still be present.
        assert "owner" not in payload
        assert payload.get("daemon_family") == "sync"


# ---------------------------------------------------------------------------
# Integration-level: real subprocess + real HTTP
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX daemon subprocess semantics")
class TestHealthEndpointLive:
    """Spin up the real daemon and assert the health endpoint emits the new fields."""

    def test_live_health_includes_daemon_family_and_scope(self, tmp_path: Path) -> None:
        """A real daemon responds with ``daemon_family=="sync"`` on ``/api/health``."""
        port = _unused_local_port()
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        env["LOCALAPPDATA"] = str(tmp_path / "AppData")
        env["SPEC_KITTY_ENABLE_SAAS_SYNC"] = "1"
        src_dir = Path(__file__).resolve().parents[2] / "src"
        env["PYTHONPATH"] = (
            str(src_dir)
            if not env.get("PYTHONPATH")
            else f"{src_dir}{os.pathsep}{env['PYTHONPATH']}"
        )

        script = (
            "from specify_cli.sync.daemon import run_sync_daemon\n"
            f"run_sync_daemon({port}, 'live-tok')\n"
        )
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            data = _wait_for_daemon_health(port, proc)
            assert data.get("daemon_family") == "sync", (
                f"daemon_family missing or wrong: {data}"
            )
            scope = data.get("singleton_scope_id")
            assert isinstance(scope, str) and scope, (
                f"singleton_scope_id missing or empty: {data}"
            )
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.communicate(timeout=5)
