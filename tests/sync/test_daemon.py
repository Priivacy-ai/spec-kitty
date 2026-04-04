"""Focused tests for the machine-global sync daemon lifecycle."""

from __future__ import annotations

import json

import pytest

from specify_cli.sync import daemon

pytestmark = pytest.mark.fast


def test_get_sync_daemon_status_reads_health_metadata(monkeypatch, tmp_path):
    daemon_file = tmp_path / "sync-daemon"
    monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", daemon_file)
    daemon._write_daemon_file(daemon_file, "http://127.0.0.1:9248", 9248, "secret", 4321)

    def fake_urlopen(_request, timeout=0.5):  # noqa: ARG001
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                payload = {
                    "status": "ok",
                    "token": "secret",
                    "sync": {
                        "running": True,
                        "last_sync": "2026-04-04T12:00:00+00:00",
                        "consecutive_failures": 1,
                    },
                    "websocket_status": "Connected",
                }
                return json.dumps(payload).encode("utf-8")

        return Response()

    monkeypatch.setattr(daemon.urllib.request, "urlopen", fake_urlopen)

    status = daemon.get_sync_daemon_status()

    assert status.healthy is True
    assert status.url == "http://127.0.0.1:9248"
    assert status.sync_running is True
    assert status.last_sync == "2026-04-04T12:00:00+00:00"
    assert status.consecutive_failures == 1
    assert status.websocket_status == "Connected"
