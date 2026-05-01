import json
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.dashboard import lifecycle

pytestmark = pytest.mark.fast


def test_parse_and_write_dashboard_file_roundtrip(tmp_path):
    dashboard_file = tmp_path / ".kittify" / ".dashboard"
    lifecycle._write_dashboard_file(dashboard_file, "http://127.0.0.1:9999", 9999, "token123", pid=12345)
    url, port, token, pid = lifecycle._parse_dashboard_file(dashboard_file)
    assert url == "http://127.0.0.1:9999"
    assert port == 9999
    assert token == "token123"
    assert pid == 12345


def test_ensure_dashboard_running_writes_state(monkeypatch, tmp_path):
    project_dir = tmp_path
    dashboard_meta = project_dir / ".kittify" / ".dashboard"
    (project_dir / ".kittify").mkdir()

    check_calls = {"count": 0}

    def fake_check(port, proj_dir, token):
        check_calls["count"] += 1
        return check_calls["count"] > 1

    monkeypatch.setattr(lifecycle, "_check_dashboard_health", fake_check)
    monkeypatch.setattr(lifecycle, "start_dashboard", lambda *args, **kwargs: (34567, None))
    class EnsureTime:
        value = 0.0

        @classmethod
        def monotonic(cls):
            current = cls.value
            cls.value += 0.05
            return current

        @staticmethod
        def sleep(_value):
            return None

    monkeypatch.setattr(lifecycle, "time", EnsureTime)

    url, port, started = lifecycle.ensure_dashboard_running(project_dir, preferred_port=34567, background_process=False)
    assert started
    assert port == 34567
    assert url.startswith("http://127.0.0.1:")
    assert dashboard_meta.exists()


def test_stop_dashboard_sends_shutdown(monkeypatch, tmp_path):
    project_dir = tmp_path
    dashboard_file = project_dir / ".kittify" / ".dashboard"
    dashboard_file.parent.mkdir(parents=True)
    lifecycle._write_dashboard_file(dashboard_file, "http://127.0.0.1:12345", 12345, "secret", pid=99999)

    calls = {"health": 0, "shutdown": 0}

    def fake_health(port, project_dir_resolved, token):
        calls["health"] += 1
        return calls["health"] == 1

    def fake_urlopen(request, timeout=1):  # noqa: ARG001
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                payload = {
                    "status": "ok",
                    "project_path": str(project_dir),
                }
                return json.dumps(payload).encode('utf-8')

        if isinstance(request, str) and "/api/shutdown" in request:
            calls["shutdown"] += 1
            return Response()
        if isinstance(request, str) and "/api/health" in request:
            return Response()
        if hasattr(request, "full_url") and "/api/shutdown" in request.full_url:
            calls["shutdown"] += 1
            return Response()
        return Response()

    class StopTime:
        value = 0.0

        @classmethod
        def monotonic(cls):
            current = cls.value
            cls.value += 0.05
            return current

        @staticmethod
        def sleep(_value):
            return None

    monkeypatch.setattr(lifecycle, "_check_dashboard_health", fake_health)
    monkeypatch.setattr(lifecycle.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(lifecycle, "time", StopTime)

    stopped, message = lifecycle.stop_dashboard(project_dir, timeout=0.1)
    assert stopped
    assert "stopped" in message.lower()
    assert calls["shutdown"] >= 1


def test_get_dashboard_status_reads_sync_metadata(monkeypatch, tmp_path):
    project_dir = tmp_path
    dashboard_file = project_dir / ".kittify" / ".dashboard"
    dashboard_file.parent.mkdir(parents=True)
    lifecycle._write_dashboard_file(dashboard_file, "http://127.0.0.1:12345", 12345, "secret", pid=99999)

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
                    "project_path": str(project_dir.resolve()),
                    "token": "secret",
                    "websocket_status": "Connected",
                    "sync": {
                        "running": True,
                        "last_sync": "2026-04-04T12:00:00+00:00",
                        "consecutive_failures": 2,
                    },
                }
                return json.dumps(payload).encode("utf-8")

        return Response()

    monkeypatch.setattr(lifecycle.urllib.request, "urlopen", fake_urlopen)

    status = lifecycle.get_dashboard_status(project_dir)

    assert status.healthy is True
    assert status.sync_running is True
    assert status.last_sync == "2026-04-04T12:00:00+00:00"
    assert status.consecutive_failures == 2
    assert status.websocket_status == "Connected"


def test_ensure_dashboard_running_restarts_stale_reused_daemon(monkeypatch, tmp_path):
    project_dir = tmp_path
    dashboard_meta = project_dir / ".kittify" / ".dashboard"
    dashboard_meta.parent.mkdir(parents=True)
    lifecycle._write_dashboard_file(
        dashboard_meta,
        "http://127.0.0.1:9238",
        9238,
        "staletoken",
        pid=4242,
    )

    killed = {"count": 0}

    class FakeProc:
        def kill(self):
            killed["count"] += 1

    monkeypatch.setattr(
        lifecycle,
        "_check_dashboard_bootstrap",
        lambda port, proj_dir, token: False,
    )
    monkeypatch.setattr(
        lifecycle,
        "_check_dashboard_health",
        lambda port, proj_dir, token: token == "fresh-token",
    )
    monkeypatch.setattr(lifecycle, "_is_process_alive", lambda pid: pid == 4242)
    monkeypatch.setattr(lifecycle.psutil, "Process", lambda pid: FakeProc())
    monkeypatch.setattr(lifecycle, "start_dashboard", lambda *args, **kwargs: (9345, 5151))
    monkeypatch.setattr(lifecycle.secrets, "token_hex", lambda _size: "fresh-token")

    url, port, started = lifecycle.ensure_dashboard_running(project_dir, background_process=False)

    assert started is True
    assert port == 9345
    assert url == "http://127.0.0.1:9345"
    assert killed["count"] == 1

    _, stored_port, stored_token, stored_pid = lifecycle._parse_dashboard_file(dashboard_meta)
    assert stored_port == 9345
    assert stored_token == "fresh-token"
    assert stored_pid == 5151
