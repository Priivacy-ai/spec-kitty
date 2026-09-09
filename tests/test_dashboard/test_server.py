import socket
from types import SimpleNamespace

from specify_cli.dashboard import server


import pytest

pytestmark = [pytest.mark.integration]


def test_find_free_port_returns_available_port():
    port = server.find_free_port(start_port=15000, max_attempts=50)
    assert isinstance(port, int)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_start_dashboard_background_invokes_subprocess(monkeypatch, tmp_path):
    calls = {}

    class FakeProcess:
        pid = 12345  # Add PID attribute

        def __init__(self, args, **kwargs):
            calls["args"] = args
            calls["kwargs"] = kwargs

        def poll(self):
            return None

    monkeypatch.setattr(server, "subprocess", type("S", (), {"Popen": FakeProcess, "DEVNULL": None}))
    # The real readiness probe would try to connect to port 12345; the fake
    # child never binds anything, so report the port as reachable.
    monkeypatch.setattr(server, "_port_accepts_connection", lambda _port: True)
    port, pid = server.start_dashboard(tmp_path, port=12345, background_process=True, project_token="abc")
    assert port == 12345
    assert pid == 12345  # Changed from thread to pid
    assert calls["args"][0] == server.sys.executable
    # #4125: the child is spawned via `python -m` of a real module, never
    # `python -c` with a generated script (which leaves `__main__` without a
    # `__file__` attribute and crashes on Windows platform bootstraps).
    assert calls["args"][1] == "-m"
    assert calls["args"][2] == "specify_cli.dashboard._server_main"
    assert calls["args"][3:] == [str(tmp_path.resolve()), "12345", "abc"]
    # Output is piped to the spawn log, not swallowed (#4125).
    assert calls["kwargs"]["stdout"].name == str(server._dashboard_spawn_log_file())
    assert calls["kwargs"]["stderr"].name == str(server._dashboard_spawn_log_file())
    # The child must resolve the same specify_cli the parent is running.
    import_root = str(server.Path(server.__file__).resolve().parents[2])
    assert calls["kwargs"]["env"]["PYTHONPATH"].split(server.os.pathsep)[0] == import_root

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

    monkeypatch.setattr(server, "create_loopback_server", lambda *_args, **_kwargs: FakeServer())
    monkeypatch.setattr(server.threading, "Thread", FakeThread)

    port, pid = server.start_dashboard(tmp_path, port=12346, background_process=False)
    assert port == 12346
    assert pid is None  # Changed from thread to pid (None for threaded mode)
    assert served.get("called")


def test_run_dashboard_server_bootstraps_global_sync_daemon(monkeypatch, tmp_path):
    calls = {}

    def fake_ensure_sync_daemon_running(*, intent):
        calls["daemon"] = True
        calls["intent"] = intent
        return SimpleNamespace(skipped_reason="intent_local_only")

    def fake_serve_loopback_server(port, handler_class, **_kwargs):
        calls["served_port"] = port
        calls["handler_class"] = handler_class

    monkeypatch.setattr(server, "serve_loopback_server", fake_serve_loopback_server)
    monkeypatch.setattr("specify_cli.sync.daemon.ensure_sync_daemon_running", fake_ensure_sync_daemon_running)

    server.run_dashboard_server(tmp_path, 12347, None)

    assert calls["daemon"] is True
    assert calls["intent"].value == "local_only"
    assert calls["served_port"] == 12347
    assert calls["handler_class"] is not None


def test_wait_for_spawn_readiness_raises_with_log_tail_when_child_exits(tmp_path):
    """A child that dies before binding must surface its exit status and log tail (#4125)."""
    log_path = tmp_path / "dashboard-server.log"
    log_path.write_text("Traceback (most recent call last):\nAttributeError: boom\n", encoding="utf-8")

    class FakeProc:
        def poll(self):
            return 3

    with pytest.raises(server.DashboardSpawnError, match="exited with status 3") as exc_info:
        server._wait_for_spawn_readiness(FakeProc(), 19999, log_path, timeout_seconds=1)
    assert exc_info.value.error_code == "DASHBOARD_SPAWN_FAILED"
    assert exc_info.value.exit_code == 3
    assert "AttributeError: boom" in str(exc_info.value)
    assert str(log_path) in str(exc_info.value)


def test_wait_for_spawn_readiness_returns_once_port_binds(monkeypatch, tmp_path):
    class FakeProc:
        def poll(self):
            return None

    monkeypatch.setattr(server, "_port_accepts_connection", lambda _port: True)
    # Returns (no exception) as soon as the port is reachable.
    server._wait_for_spawn_readiness(FakeProc(), 12345, tmp_path / "unused.log", timeout_seconds=1)


def test_wait_for_spawn_readiness_tolerates_alive_but_unbound_child(monkeypatch, tmp_path):
    """A slow-but-alive child is the caller's health-check poll's call, not a spawn failure (#4125)."""

    class FakeProc:
        def poll(self):
            return None

    monkeypatch.setattr(server, "_port_accepts_connection", lambda _port: False)
    monkeypatch.setattr(server, "_SPAWN_READINESS_POLL_SECONDS", 0)
    # No exception: the probe window lapses without a verdict.
    server._wait_for_spawn_readiness(FakeProc(), 12345, tmp_path / "unused.log", timeout_seconds=0.05)
