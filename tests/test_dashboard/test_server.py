import socket
from pathlib import Path

from specify_cli.dashboard import server


def test_find_free_port_returns_available_port():
    port = server.find_free_port(start_port=15000, max_attempts=50)
    assert isinstance(port, int)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', port))


def test_start_dashboard_background_invokes_subprocess(monkeypatch, tmp_path):
    calls = {}

    class FakeProcess:
        pid = 12345  # Add PID attribute

        def __init__(self, args, **kwargs):
            calls["args"] = args
            calls["kwargs"] = kwargs

    monkeypatch.setattr(server, "subprocess", type("S", (), {"Popen": FakeProcess, "DEVNULL": None}))
    port, pid = server.start_dashboard(tmp_path, port=12345, background_process=True, project_token="abc")
    assert port == 12345
    assert pid == 12345  # Changed from thread to pid
    assert calls["args"][0] == server.sys.executable
    assert calls["args"][1] == "-c"


def test_start_dashboard_foreground_starts_thread(monkeypatch, tmp_path):
    served = {}

    class FakeServer:
        def __init__(self, *_args, **_kwargs):
            served["created"] = True

        def serve_forever(self):
            served["called"] = True

    class FakeThread:
        def __init__(self, target, daemon):
            self._target = target
            self.daemon = daemon
            self.started = False

        def start(self):
            self.started = True
            self._target()

    monkeypatch.setattr(server, "HTTPServer", FakeServer)
    monkeypatch.setattr(server.threading, "Thread", FakeThread)

    port, pid = server.start_dashboard(tmp_path, port=12346, background_process=False)
    assert port == 12346
    assert pid is None  # Changed from thread to pid (None for threaded mode)
    assert served.get("called")
