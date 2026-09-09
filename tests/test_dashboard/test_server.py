import contextlib
import os
import socket
import subprocess
import urllib.request
from pathlib import Path

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
    # The real readiness probe would query /api/health on port 12345; the
    # fake child never binds anything, so report the listener as ours.
    monkeypatch.setattr(server, "_port_serves_our_dashboard", lambda _port, _dir, _token: True)
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

        def poll(self):
            return None

    monkeypatch.setattr(server, "subprocess", type("S", (), {"Popen": FakeProcess, "DEVNULL": None}))
    monkeypatch.setattr(server, "_port_serves_our_dashboard", lambda _port, _dir, _token: True)

    port, pid = server.start_dashboard(tmp_path, port=0, background_process=True, project_token="abc")

    assert port == 23456
    assert pid == 54321
    assert calls["kwargs"]["pass_fds"]
    # The pipe fd travels as an explicit --port-fd flag, never as a bare
    # positional that could be misread as the optional token argument.
    assert calls["args"][-2:] == ["--port-fd", str(calls["kwargs"]["pass_fds"][0])]


def test_start_dashboard_background_ephemeral_port_empty_report_names_child_exit(monkeypatch, tmp_path):
    class FakeProcess:
        pid = 54321

        def __init__(self, _args, **_kwargs):
            pass

        def poll(self):
            return 17

    monkeypatch.setattr(server, "subprocess", type("S", (), {"Popen": FakeProcess, "DEVNULL": None}))

    with pytest.raises(
        server.BackgroundPortReportError,
        match="no port report; child exited with status 17",
    ) as exc_info:
        server.start_dashboard(tmp_path, port=0, background_process=True, project_token="abc")
    assert exc_info.value.error_code == "DASHBOARD_BACKGROUND_PORT_REPORT_FAILED"
    assert exc_info.value.exit_code == 17


def test_start_dashboard_background_ephemeral_port_invalid_report_is_contextual(monkeypatch, tmp_path):
    class FakeProcess:
        pid = 54321

        def __init__(self, _args, **kwargs):
            for fd in kwargs.get("pass_fds") or ():
                os.write(fd, b"not-a-port")

        def poll(self):
            return None

        def wait(self, timeout):
            raise server.subprocess.TimeoutExpired("dashboard", timeout)

    monkeypatch.setattr(
        server,
        "subprocess",
        type("S", (), {"Popen": FakeProcess, "DEVNULL": None, "TimeoutExpired": subprocess.TimeoutExpired}),
    )

    with pytest.raises(
        server.BackgroundPortReportError,
        match="invalid port report b'not-a-port'",
    ) as exc_info:
        server.start_dashboard(tmp_path, port=0, background_process=True, project_token="abc")
    assert exc_info.value.error_code == "DASHBOARD_BACKGROUND_PORT_REPORT_FAILED"
    assert exc_info.value.exit_code is None


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


def test_wait_for_spawn_readiness_raises_with_log_tail_when_child_exits(tmp_path):
    """A child that dies before binding must surface its exit status and log tail (#4125)."""
    log_path = tmp_path / "dashboard-server.log"
    log_path.write_text("Traceback (most recent call last):\nAttributeError: boom\n", encoding="utf-8")

    class FakeProc:
        def poll(self):
            return 3

    with pytest.raises(server.DashboardSpawnError, match="exited with status 3") as exc_info:
        server._wait_for_spawn_readiness(FakeProc(), 19999, log_path, tmp_path, None, timeout_seconds=1)
    assert exc_info.value.error_code == "DASHBOARD_SPAWN_FAILED"
    assert exc_info.value.exit_code == 3
    assert "AttributeError: boom" in str(exc_info.value)
    assert str(log_path) in str(exc_info.value)


def test_wait_for_spawn_readiness_returns_once_port_binds(monkeypatch, tmp_path):
    class FakeProc:
        def poll(self):
            return None

    monkeypatch.setattr(server, "_port_serves_our_dashboard", lambda _port, _dir, _token: True)
    # Returns (no exception) as soon as the port serves our project's dashboard.
    server._wait_for_spawn_readiness(FakeProc(), 12345, tmp_path / "unused.log", tmp_path, None, timeout_seconds=1)


def test_wait_for_spawn_readiness_tolerates_alive_but_unbound_child(monkeypatch, tmp_path):
    """A slow-but-alive child is the caller's health-check poll's call, not a spawn failure (#4125)."""

    class FakeProc:
        def poll(self):
            return None

    monkeypatch.setattr(server, "_port_serves_our_dashboard", lambda _port, _dir, _token: False)
    monkeypatch.setattr(server, "_SPAWN_READINESS_POLL_SECONDS", 0)
    # No exception: the probe window lapses without a verdict.
    server._wait_for_spawn_readiness(FakeProc(), 12345, tmp_path / "unused.log", tmp_path, None, timeout_seconds=0.05)


def test_wait_for_spawn_readiness_rejects_foreign_listener_until_child_dies(monkeypatch, tmp_path):
    """A foreign dashboard on the port is not readiness — our child's death must surface (#4125, fix round 2).

    This is the ``find_free_port`` TOCTOU shape the squad reproduced: a foreign
    listener holds the port (so a bare connect-ex probe would report "ready" on
    its first iteration), while our own child dies on bind. The probe must keep
    failing the identity check every iteration until ``poll()`` catches the
    child's exit and raises with the log tail.
    """

    log_path = tmp_path / "dashboard-server.log"
    log_path.write_text("OSError: [Errno 98] Address already in use\n", encoding="utf-8")

    polls = {"count": 0}

    class FakeProc:
        def poll(self):
            polls["count"] += 1
            # Alive for the first two iterations (the foreign listener is
            # being probed), dead from the third — its bind failed.
            return None if polls["count"] < 3 else 1

    identity_checks = {"count": 0}

    def fake_identity_check(_port, _dir, _token):
        identity_checks["count"] += 1
        # The listener answers /api/health — but for a different project.
        return False

    monkeypatch.setattr(server, "_port_serves_our_dashboard", fake_identity_check)
    monkeypatch.setattr(server, "_SPAWN_READINESS_POLL_SECONDS", 0)

    with pytest.raises(server.DashboardSpawnError, match="exited with status 1") as exc_info:
        server._wait_for_spawn_readiness(FakeProc(), 12345, log_path, tmp_path, "token", timeout_seconds=5)
    assert "Address already in use" in str(exc_info.value)
    # The foreign listener was probed (and rejected) before the child's exit
    # was discovered — a bare accept probe would have returned at the first
    # check instead.
    assert identity_checks["count"] >= 2


def _start_foreign_dashboard(project_dir: Path, *, port: int, token: str) -> int:
    (project_dir / ".kittify").mkdir(parents=True, exist_ok=True)
    actual_port, _pid = server.start_dashboard(project_dir, port=port, background_process=False, project_token=token)
    return actual_port


def _stop_foreground_dashboard(port: int, token: str) -> None:
    with contextlib.suppress(Exception):
        urllib.request.urlopen(  # nosec B310 — loopback URL built from the port int above
            f"http://127.0.0.1:{port}/api/shutdown?token={token}", timeout=2
        )


def test_port_serves_our_dashboard_matches_project_and_token(tmp_path):
    """The readiness probe's identity check, against a real dashboard (#4125, fix round 2).

    Same-project+same-token is ours; any other project, or the same project
    with a different token, is a foreign listener and must never satisfy the
    probe.
    """
    our_project = tmp_path / "ours"
    other_project = tmp_path / "theirs"
    port = _start_foreign_dashboard(our_project, port=server.find_free_port(start_port=21500), token="tok-a")
    try:
        assert server._port_serves_our_dashboard(port, our_project, "tok-a") is True
        # Caller holding no token still matches on project identity alone.
        assert server._port_serves_our_dashboard(port, our_project, None) is True
        # A different project's dashboard is foreign, whatever token it holds.
        assert server._port_serves_our_dashboard(port, other_project, "tok-a") is False
        # Same project but a token we never handed out: foreign.
        assert server._port_serves_our_dashboard(port, our_project, "tok-b") is False
    finally:
        _stop_foreground_dashboard(port, "tok-a")


def test_port_serves_our_dashboard_rejects_non_dashboard_listener(tmp_path):
    """A plain TCP listener with no /api/health is not readiness (#4125)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        assert server._port_serves_our_dashboard(port, tmp_path, None) is False


@pytest.mark.regression
@pytest.mark.non_sandbox
def test_start_dashboard_background_raises_when_foreign_dashboard_holds_port(monkeypatch, tmp_path):
    """A foreign dashboard that won the free-port race is not our success (#4125, fix round 2).

    Squad pass-2 reproduction shape, made deterministic: ``find_free_port``
    probe-binds-releases, so two concurrent spawns can be handed the same
    port — the loser's child dies with "Address already in use" while the
    winner's listener makes a bare accept-probe report "ready" on its first
    iteration. The identity-checked probe must instead keep rejecting the
    foreign listener until the child's exit surfaces as ``DashboardSpawnError``
    with its exit status — never a ``started`` return pointing at the other
    project's dashboard.
    """
    foreign_project = tmp_path / "foreign"
    our_project = tmp_path / "ours"
    our_project.mkdir()
    held_port = _start_foreign_dashboard(foreign_project, port=server.find_free_port(start_port=22000), token="foreign-token")
    try:
        # The default production path: port=None resolves through
        # find_free_port, monkeypatched here to lose the race deterministically.
        monkeypatch.setattr(server, "find_free_port", lambda *_a, **_k: held_port)

        with pytest.raises(server.DashboardSpawnError) as exc_info:
            server.start_dashboard(our_project, background_process=True, project_token="our-token")

        assert exc_info.value.error_code == "DASHBOARD_SPAWN_FAILED"
        # The child really died on bind — its exit status is surfaced, not None.
        assert exc_info.value.exit_code is not None
        assert exc_info.value.exit_code != 0
    finally:
        _stop_foreground_dashboard(held_port, "foreign-token")
