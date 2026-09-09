import contextlib
import os
import socket
import subprocess
from pathlib import Path

from specify_cli.dashboard import server


import pytest

pytestmark = [pytest.mark.integration]


def test_find_free_port_returns_available_port():
    port = server.find_free_port(start_port=15000, max_attempts=50)
    assert isinstance(port, int)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_background_launch_argv_uses_module_entrypoint_never_dash_c(tmp_path):
    """#4125: the detached child is launched as a real module, never `-c` codegen.

    A `-c` child has no `__main__.__file__`, which crashed on Windows when a
    transitive import read it.
    """
    argv = server._background_launch_argv(tmp_path, 12345, "tok", None)

    assert argv[0] == server.sys.executable
    assert argv[1] == "-m"
    assert argv[2] == "specify_cli.dashboard._server_main"
    assert "-c" not in argv
    assert "--project-dir" in argv
    assert str(tmp_path) in argv
    assert "--port" in argv
    assert "12345" in argv
    assert "--token" in argv
    assert "tok" in argv
    assert "--port-report-file" not in argv


def test_background_launch_argv_includes_port_report_file_when_given(tmp_path):
    report_path = tmp_path / "port-report.txt"
    argv = server._background_launch_argv(tmp_path, 0, None, report_path)

    assert "--port-report-file" in argv
    assert str(report_path) in argv
    # project_token=None must not add a bare "--token" flag with no value.
    assert "--token" not in argv


def test_launch_background_dashboard_windows_omits_pass_fds_uses_process_group(monkeypatch, tmp_path):
    """Unit test (#4125): argv never uses `-c`, and `pass_fds` is never passed
    on Windows (`os.name == 'nt'`) — `pass_fds` raises `ValueError` there.

    Exercised via the injectable `platform` seam rather than monkeypatching
    the real ``os.name`` attribute: mutating that process-wide mid-test makes
    every subsequent real ``pathlib.Path(...)`` construction (including
    pytest's own failure-reporting machinery) try to build a ``WindowsPath``
    on this POSIX test host and raise ``NotImplementedError`` — the platform
    seam gets the same coverage without that collateral damage.
    """
    calls = {}

    class FakeProcess:
        pid = 777

    def fake_popen(argv, **kwargs):
        calls["argv"] = argv
        calls["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(server.subprocess, "Popen", fake_popen)

    log_path = tmp_path / "dash.log"
    with open(log_path, "wb") as log_file:
        proc = server._launch_background_dashboard(
            [server.sys.executable, "-m", "specify_cli.dashboard._server_main"],
            log_file=log_file,
            platform="nt",
        )

    assert proc.pid == 777
    assert calls["argv"][1] == "-m"
    assert calls["argv"][2] == "specify_cli.dashboard._server_main"
    assert "-c" not in calls["argv"]
    assert "pass_fds" not in calls["kwargs"]
    assert "creationflags" in calls["kwargs"]
    assert "start_new_session" not in calls["kwargs"]


def test_launch_background_dashboard_posix_uses_start_new_session_no_pass_fds(monkeypatch, tmp_path):
    calls = {}

    class FakeProcess:
        pid = 778

    def fake_popen(argv, **kwargs):
        calls["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(server.subprocess, "Popen", fake_popen)

    log_path = tmp_path / "dash.log"
    with open(log_path, "wb") as log_file:
        proc = server._launch_background_dashboard(
            [server.sys.executable, "-m", "specify_cli.dashboard._server_main"],
            log_file=log_file,
            platform="posix",
        )

    assert proc.pid == 778
    assert "pass_fds" not in calls["kwargs"]
    assert calls["kwargs"].get("start_new_session") is True
    assert "creationflags" not in calls["kwargs"]


def test_start_dashboard_background_ephemeral_port_reads_back_actual_port(monkeypatch, tmp_path):
    """port=0 + background_process=True must report the real OS-assigned port.

    Regression for issue #98: the background branch echoed the caller-supplied
    `port` straight back, so `port=0` (ephemeral) reported the dashboard was
    on port 0 while the detached child actually bound a different port —
    the same silent-wrong-port shape issue #66 pinned for threaded mode.

    The ephemeral round trip now goes through a sidecar file (Windows-safe)
    instead of `os.pipe()` + `pass_fds` (POSIX-only) — see #4125.
    """
    calls = {}

    class FakeProcess:
        pid = 54321

        def poll(self):
            return None

    def fake_launch(argv, *, log_file, platform=None):
        calls["argv"] = argv
        # Stand in for the detached child: report the port it "bound" via
        # the sidecar file passed on argv — mirrors run_dashboard_server's
        # on_bound callback, which fires right after bind.
        report_index = argv.index("--port-report-file") + 1
        Path(argv[report_index]).write_text("23456", encoding="utf-8")
        return FakeProcess()

    monkeypatch.setattr(server, "_launch_background_dashboard", fake_launch)
    monkeypatch.setattr(server, "_port_is_accepting_connections", lambda port, timeout=0.2: True)

    port, pid = server.start_dashboard(tmp_path, port=0, background_process=True, project_token="abc")

    assert port == 23456
    assert pid == 54321
    assert "--port-report-file" in calls["argv"]
    assert "-c" not in calls["argv"]


def test_start_dashboard_background_dead_child_is_surfaced_not_reported_success(monkeypatch, tmp_path):
    """A child that exits before becoming ready must raise, never report success.

    Regression for #4125 item (b): routing stdout/stderr to DEVNULL with no
    readiness probe let a crashed child be reported as a live dashboard.
    """

    class FakeProcess:
        pid = 54321

        def poll(self):
            return 17

        def wait(self, timeout):
            return 17

    monkeypatch.setattr(server, "_launch_background_dashboard", lambda argv, *, log_file, platform=None: FakeProcess())
    monkeypatch.setattr(server, "_port_is_accepting_connections", lambda port, timeout=0.2: False)

    with pytest.raises(
        server.BackgroundPortReportError,
        match="child exited with status 17",
    ) as exc_info:
        server.start_dashboard(tmp_path, port=12345, background_process=True, project_token="abc")

    assert exc_info.value.error_code == "DASHBOARD_BACKGROUND_PORT_REPORT_FAILED"
    assert exc_info.value.exit_code == 17


def test_start_dashboard_background_dead_child_error_quotes_log_tail(monkeypatch, tmp_path):
    """The failure surfaces the child's captured stdout/stderr, not silence."""
    logged = {}

    def fake_open_log():
        log_path = tmp_path / "dash.log"
        log_path.write_text("Traceback (most recent call last):\nBOOM\n", encoding="utf-8")
        logged["path"] = log_path
        return log_path, open(log_path, "ab")

    class FakeProcess:
        pid = 999

        def poll(self):
            return 1

        def wait(self, timeout):
            return 1

    monkeypatch.setattr(server, "_open_background_log", fake_open_log)
    monkeypatch.setattr(server, "_launch_background_dashboard", lambda argv, *, log_file, platform=None: FakeProcess())
    monkeypatch.setattr(server, "_port_is_accepting_connections", lambda port, timeout=0.2: False)

    with pytest.raises(server.BackgroundPortReportError, match="BOOM"):
        server.start_dashboard(tmp_path, port=12345, background_process=True, project_token="abc")


def test_await_background_ready_raises_on_timeout_with_log_tail(monkeypatch, tmp_path):
    class FakeProcess:
        pid = 1

        def poll(self):
            return None  # never exits, never binds

        def wait(self, timeout):
            raise subprocess.TimeoutExpired("dashboard", timeout)

        def terminate(self):
            pass

        def kill(self):
            pass

    log_path = tmp_path / "dash.log"
    log_path.write_text("still starting up\n", encoding="utf-8")
    monkeypatch.setattr(server, "_port_is_accepting_connections", lambda port, timeout=0.2: False)

    with pytest.raises(server.BackgroundPortReportError, match="did not become ready"):
        server._await_background_ready(
            FakeProcess(),
            port=12345,
            port_report_path=None,
            log_path=log_path,
            timeout=0.05,
            poll_interval=0.01,
        )


def test_await_background_ready_dead_child_not_masked_by_foreign_listener(tmp_path):
    """A FOREIGN listener occupying the target port must not mask a dead child.

    Regression for #4125 follow-up: on the concrete-port path (a
    caller-supplied port, or one from the inherently check-then-bind-racy
    ``find_free_port()``), if our child dies on a bind conflict while
    another process already occupies that exact port, a TCP-connect-first
    probe would succeed against the squatter and report the dead child as a
    live dashboard, with the returned URL actually pointing at the
    squatter. Uses a real bound+listening socket (not a mock) so the port
    genuinely answers connections, proving liveness is checked first.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as squatter:
        squatter.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        squatter.bind(("127.0.0.1", 0))
        squatter.listen(1)
        occupied_port = squatter.getsockname()[1]

        class DeadProcess:
            pid = 4242

            def poll(self):
                return 13  # already dead, e.g. lost the bind race

            def wait(self, timeout):
                return 13

        log_path = tmp_path / "dash.log"
        log_path.write_text("bind: address already in use\n", encoding="utf-8")

        with pytest.raises(server.BackgroundPortReportError, match="child exited with status 13"):
            server._await_background_ready(
                DeadProcess(),
                port=occupied_port,
                port_report_path=None,
                log_path=log_path,
                timeout=0.5,
                poll_interval=0.01,
            )


def test_await_background_ready_timeout_terminates_orphaned_child(monkeypatch, tmp_path):
    """A readiness timeout must not orphan a still-running detached child.

    Regression for #4125 follow-up: previously the deadline path raised
    without ever touching ``proc``, leaving a slow-but-live child running
    detached (and free to bind the port *after* the parent had already
    reported failure). Uses a fake process whose ``wait`` always times out,
    so the terminate attempt must fall through to ``kill``.
    """
    calls: list[str] = []

    class NeverReadyProcess:
        pid = 999

        def poll(self):
            return None  # always alive; never binds

        def terminate(self):
            calls.append("terminate")

        def kill(self):
            calls.append("kill")

        def wait(self, timeout):
            raise subprocess.TimeoutExpired("dashboard", timeout)

    log_path = tmp_path / "dash.log"
    log_path.write_text("still starting up\n", encoding="utf-8")
    monkeypatch.setattr(server, "_port_is_accepting_connections", lambda port, timeout=0.2: False)

    with pytest.raises(server.BackgroundPortReportError, match="did not become ready"):
        server._await_background_ready(
            NeverReadyProcess(),
            port=12345,
            port_report_path=None,
            log_path=log_path,
            timeout=0.05,
            poll_interval=0.01,
        )

    assert calls == ["terminate", "kill"]


def test_start_dashboard_background_success_cleans_up_log_file(monkeypatch, tmp_path):
    """A clean, successful background launch must not leave a log file behind.

    Regression for #4125 follow-up: every prior successful
    ``start_dashboard(background_process=True)`` call left a
    ``dashboard-*.log`` under the shared runtime state dir forever, growing
    unbounded. The log's only purpose is diagnosing a *failed* launch, so a
    confirmed-ready launch should unlink it.
    """
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    monkeypatch.setattr(server, "_dashboard_state_dir", lambda: state_dir)

    class FakeProcess:
        pid = 24680

        def poll(self):
            return None

    monkeypatch.setattr(server, "_launch_background_dashboard", lambda argv, *, log_file, platform=None: FakeProcess())
    monkeypatch.setattr(server, "_port_is_accepting_connections", lambda port, timeout=0.2: True)

    port, pid = server.start_dashboard(tmp_path, port=15200, background_process=True, project_token="tok")

    assert port == 15200
    assert pid == 24680
    assert list(state_dir.glob("dashboard-*.log")) == []


def test_start_dashboard_background_failure_leaves_log_file_for_diagnosis(monkeypatch, tmp_path):
    """A failed background launch must still leave its log file on disk.

    Regression for #4125 follow-up: only a *clean, successful* start
    unlinks the log — a failed one needs the file to stay put, both for the
    tail already quoted into the raised error and for a human to inspect
    afterwards.
    """
    log_path = tmp_path / "dash.log"

    def fake_open_log():
        log_path.write_text("Traceback (most recent call last):\nBOOM\n", encoding="utf-8")
        return log_path, open(log_path, "ab")

    class FakeProcess:
        pid = 998

        def poll(self):
            return 1

        def wait(self, timeout):
            return 1

    monkeypatch.setattr(server, "_open_background_log", fake_open_log)
    monkeypatch.setattr(server, "_launch_background_dashboard", lambda argv, *, log_file, platform=None: FakeProcess())
    monkeypatch.setattr(server, "_port_is_accepting_connections", lambda port, timeout=0.2: False)

    with pytest.raises(server.BackgroundPortReportError, match="BOOM"):
        server.start_dashboard(tmp_path, port=12345, background_process=True, project_token="abc")

    assert log_path.exists()
    assert "BOOM" in log_path.read_text(encoding="utf-8")


def test_start_dashboard_background_real_process_becomes_reachable(tmp_path):
    """The background dashboard must actually come up and accept connections.

    Regression for #4125: this is the check the previous suite lacked — every
    prior background-mode test mocked ``subprocess.Popen`` entirely, so a
    Windows-only crash in the real detached child was invisible to CI.
    """
    port = server.find_free_port(start_port=15100, max_attempts=100)

    dashboard_port, pid = server.start_dashboard(
        tmp_path,
        port=port,
        background_process=True,
        project_token="tok",
    )
    try:
        assert dashboard_port == port
        assert pid is not None
        with socket.create_connection(("127.0.0.1", dashboard_port), timeout=2):
            pass
    finally:
        if pid is not None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, 15)  # SIGTERM


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


def test_run_dashboard_server_reports_bound_port_via_sidecar_file(monkeypatch, tmp_path):
    """`port_report_path` replaces the old inherited-pipe-fd hand-off (#4125)."""
    report_path = tmp_path / "port-report.txt"

    def fake_serve_loopback_server(port, handler_class, *, on_bound=None):
        assert on_bound is not None
        on_bound(45678)

    monkeypatch.setattr(server, "serve_loopback_server", fake_serve_loopback_server)

    server.run_dashboard_server(tmp_path, 0, None, port_report_path=report_path)

    assert report_path.read_text(encoding="utf-8").strip() == "45678"
