import os
import socket

from specify_cli.dashboard import server


import pytest

pytestmark = [pytest.mark.integration]

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


def test_start_dashboard_background_ephemeral_port_reads_back_actual_port(monkeypatch, tmp_path):
    """port=0 + background_process=True must report the real OS-assigned port.

    Regression for issue #98: the background branch echoed the caller-supplied
    `port` straight back, so `port=0` (ephemeral) reported the dashboard was
    on port 0 while the detached child actually bound a different port —
    the same silent-wrong-port shape issue #66 pinned for threaded mode.
    """
    calls = {}

    class FakeProcess:
        pid = 54321

        def __init__(self, args, **kwargs):
            calls["args"] = args
            calls["kwargs"] = kwargs
            # Stand in for the detached child: report the port it "bound"
            # back over the inherited pipe, without closing our fd copy —
            # there's no real subprocess here, so the parent's own close of
            # its fd copy is what should surface EOF to the reader.
            for fd in kwargs.get("pass_fds") or ():
                os.write(fd, b"23456")

    monkeypatch.setattr(server, "subprocess", type("S", (), {"Popen": FakeProcess, "DEVNULL": None}))

    port, pid = server.start_dashboard(tmp_path, port=0, background_process=True, project_token="abc")

    assert port == 23456
    assert pid == 54321
    assert calls["kwargs"]["pass_fds"]


def test_start_dashboard_foreground_starts_thread(monkeypatch, tmp_path):
    served = {}

    class FakeServer:
        def __init__(self, *_args, **_kwargs):
            served["created"] = True
            self.server_address = ("127.0.0.1", 12346)

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


def test_start_dashboard_foreground_reports_os_assigned_port(monkeypatch, tmp_path):
    """port=0 must report the real OS-assigned port, not the literal 0 passed in.

    Regression for issue #66's CI-runner repro: the previous implementation
    echoed the caller-supplied `port` straight back, so a caller requesting
    an ephemeral port via `port=0` (the only race-free way to avoid the
    check-then-bind TOCTOU in `find_free_port()`) got told the dashboard was
    on port 0.
    """
    served = {}

    class FakeServer:
        def __init__(self, *_args, **_kwargs):
            self.server_address = ("127.0.0.1", 54321)

        def serve_forever(self):
            served["called"] = True

    class FakeThread:
        def __init__(self, target, daemon):
            self._target = target
            self.daemon = daemon

        def start(self):
            self._target()

    monkeypatch.setattr(server, "create_loopback_server", lambda *_args, **_kwargs: FakeServer())
    monkeypatch.setattr(server.threading, "Thread", FakeThread)

    port, pid = server.start_dashboard(tmp_path, port=0, background_process=False)
    assert port == 54321
    assert pid is None
    assert served.get("called")


def test_run_dashboard_server_serves_loopback_only(monkeypatch, tmp_path):
    """The dashboard serves local state only, via the loopback server.

    Formerly also guarded against probing the sync daemon on boot
    (planning epic #4); that daemon and its module died with the sync
    transport (issue #5), so there is nothing left to probe.
    """
    calls = {}

    def fake_serve_loopback_server(port, handler_class, **_kwargs):
        calls["served_port"] = port
        calls["handler_class"] = handler_class

    monkeypatch.setattr(server, "serve_loopback_server", fake_serve_loopback_server)

    server.run_dashboard_server(tmp_path, 12347, None)

    assert calls["served_port"] == 12347
    assert calls["handler_class"] is not None
