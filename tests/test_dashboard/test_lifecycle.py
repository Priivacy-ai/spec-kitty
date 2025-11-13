import json
from pathlib import Path

from specify_cli.dashboard import lifecycle


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
