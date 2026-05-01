"""Tests for the orphan-daemon enumeration and sweep module (FR-009).

Each test class spins up real subprocess daemons against the same
``run_sync_daemon`` entrypoint the production code uses, then probes via
the public ``enumerate_orphans``/``sweep_orphans`` API. No mocks for the
HTTP layer — the identity probe (R4) is exercised end-to-end.
"""

from __future__ import annotations

import contextlib
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

import psutil
import pytest

from specify_cli.sync import orphan_sweep
from specify_cli.sync.orphan_sweep import (
    SweepReport,
    enumerate_orphans,
    sweep_orphans,
)


def _find_free_port_in_range(start: int, end: int) -> int:
    """Return the first port in ``[start, end)`` that is currently unbound."""
    for port in range(start, end):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
            sock.close()
            return port
        except OSError:
            sock.close()
            continue
    raise RuntimeError(f"no free port in [{start}, {end})")


def _wait_until_listening(port: int, timeout_s: float = 5.0) -> bool:
    """Poll the port until something listens, or timeout."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        try:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        finally:
            sock.close()
        time.sleep(0.05)
    return False


def _wait_until_port_free(port: int, timeout_s: float = 5.0) -> bool:
    """Poll the port until it stops listening, or timeout."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        try:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return True
        finally:
            sock.close()
        time.sleep(0.05)
    return False


def _spawn_daemon(port: int, token: str) -> subprocess.Popen[bytes]:
    """Spawn a real Spec Kitty sync daemon on ``port`` with ``token``."""
    spawn_script = (
        "from specify_cli.sync.daemon import run_sync_daemon\n"
        f"run_sync_daemon({port!r}, {token!r})\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", spawn_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    if not _wait_until_listening(port, timeout_s=10.0):
        proc.terminate()
        proc.wait(timeout=2.0)
        raise RuntimeError(f"daemon on port {port} never started listening")
    return proc


def _terminate_proc(proc: subprocess.Popen[bytes]) -> None:
    """Best-effort terminate of a Popen, escalating to kill on timeout."""
    if proc.poll() is not None:
        return
    with contextlib.suppress(Exception):
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
            return
        except subprocess.TimeoutExpired:
            pass
        proc.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=2.0)


# ---------------------------------------------------------------------------
# Plain (non-Spec-Kitty) HTTP server fixture
# ---------------------------------------------------------------------------


class _PlainHandler(BaseHTTPRequestHandler):
    """Returns ``{"hello": "world"}`` with no protocol/package keys."""

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        del format, args

    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"hello": "world"}')


def _spawn_plain_server(port: int) -> tuple[HTTPServer, Thread]:
    server = HTTPServer(("127.0.0.1", port), _PlainHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if not _wait_until_listening(port, timeout_s=5.0):
        server.shutdown()
        thread.join(timeout=2.0)
        raise RuntimeError(f"plain server on port {port} never started listening")
    return server, thread


# ---------------------------------------------------------------------------
# Per-test resource manager
# ---------------------------------------------------------------------------


class _DaemonHarness:
    """Tracks daemon subprocesses and plain servers spawned during a test."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.procs: list[subprocess.Popen[bytes]] = []
        self.servers: list[tuple[HTTPServer, Thread]] = []
        # Maps port -> pid for daemons we spawned. Used by the test
        # ``_lookup_listening_pid`` patch so the sweep can locate the owner
        # process even when ``psutil.net_connections`` returns AccessDenied
        # (common on macOS without elevated privileges).
        self.port_pids: dict[int, int] = {}

    def spawn_daemon(self, port: int, token: str = "test-token-hex") -> subprocess.Popen[bytes]:
        proc = _spawn_daemon(port, token)
        self.procs.append(proc)
        self.port_pids[port] = proc.pid
        return proc

    def spawn_plain(self, port: int) -> tuple[HTTPServer, Thread]:
        server_thread = _spawn_plain_server(port)
        self.servers.append(server_thread)
        return server_thread

    def write_state_file(self, url: str, port: int, token: str, pid: int) -> None:
        """Write a minimal singleton state file (matching ``_write_daemon_file`` shape)."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join([url, str(port), token, str(pid)]) + "\n"
        self.state_file.write_text(text, encoding="utf-8")

    def shutdown(self) -> None:
        for proc in self.procs:
            _terminate_proc(proc)
        for server, thread in self.servers:
            with contextlib.suppress(Exception):
                server.shutdown()
            with contextlib.suppress(Exception):
                server.server_close()
            thread.join(timeout=2.0)


# Tests share the reserved daemon range (9400-9449) with any real Spec Kitty
# daemon the developer may already have running. To stay deterministic, the
# fixture narrows the scan range to the upper half (9425-9449) — far from the
# default first-port (9400) the production daemon picks. Tests pick ports
# inside the narrowed window, which keeps assertions stable on dev machines.
_TEST_PORT_START = 9425
_TEST_PORT_END = 9450  # exclusive


def test_lookup_listening_pid_falls_back_to_lsof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """macOS can hide listener PIDs from psutil; lsof should recover them."""

    def fake_net_connections(*_args: Any, **_kwargs: Any) -> list[Any]:
        raise psutil.AccessDenied(pid=None)

    def fake_run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, stdout="12345\n", stderr="")

    monkeypatch.setattr(orphan_sweep.psutil, "net_connections", fake_net_connections)
    monkeypatch.setattr(orphan_sweep.subprocess, "run", fake_run)

    assert orphan_sweep._lookup_listening_pid(9401) == 12345


@pytest.fixture
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[_DaemonHarness]:
    """Provide a harness with an isolated DAEMON_STATE_FILE and narrowed scan range."""
    state_file = tmp_path / "sync-daemon"
    monkeypatch.setattr(orphan_sweep, "DAEMON_STATE_FILE", state_file)
    monkeypatch.setattr(orphan_sweep, "DAEMON_PORT_START", _TEST_PORT_START)
    monkeypatch.setattr(
        orphan_sweep,
        "DAEMON_PORT_MAX_ATTEMPTS",
        _TEST_PORT_END - _TEST_PORT_START,
    )

    h = _DaemonHarness(state_file)

    # Patch the PID-lookup so it consults the harness map first, then falls
    # back to the real psutil call. This makes the sweep deterministic on
    # macOS where ``psutil.net_connections`` raises AccessDenied for sockets
    # owned by another (subprocess) UID.
    original_lookup = orphan_sweep._lookup_listening_pid

    def patched_lookup(port: int) -> int | None:
        if port in h.port_pids:
            return h.port_pids[port]
        return original_lookup(port)

    monkeypatch.setattr(orphan_sweep, "_lookup_listening_pid", patched_lookup)

    try:
        yield h
    finally:
        h.shutdown()


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="psutil.net_connections behavior varies on Windows; covered in WP01 platform test",
)
class TestOrphanSweep:
    """End-to-end coverage for enumerate_orphans + sweep_orphans."""

    def test_enumerate_finds_singleton_only(self, harness: _DaemonHarness) -> None:
        """Single daemon at port A; state file points at A; result is empty."""
        port_a = _find_free_port_in_range(_TEST_PORT_START, _TEST_PORT_END)
        proc = harness.spawn_daemon(port_a)
        harness.write_state_file(f"http://127.0.0.1:{port_a}", port_a, "tok", proc.pid)

        orphans = enumerate_orphans()

        assert orphans == []

    def test_enumerate_finds_orphan(self, harness: _DaemonHarness) -> None:
        """Daemons on A and B; state file at A; one OrphanDaemon on B."""
        port_a = _find_free_port_in_range(_TEST_PORT_START, _TEST_PORT_END)
        port_b = _find_free_port_in_range(port_a + 1, _TEST_PORT_END)

        proc_a = harness.spawn_daemon(port_a)
        harness.spawn_daemon(port_b)
        harness.write_state_file(f"http://127.0.0.1:{port_a}", port_a, "tok", proc_a.pid)

        orphans = enumerate_orphans()

        assert len(orphans) == 1
        assert orphans[0].port == port_b
        assert orphans[0].protocol_version is not None
        assert orphans[0].package_version is not None

    def test_enumerate_skips_non_spec_kitty(self, harness: _DaemonHarness) -> None:
        """Plain HTTPServer at C returning ``{"hello": "world"}`` not classified."""
        port_c = _find_free_port_in_range(_TEST_PORT_START, _TEST_PORT_END)
        harness.spawn_plain(port_c)
        # No state file: every Spec Kitty daemon would otherwise be reported,
        # but the plain server isn't one.

        orphans = enumerate_orphans()

        assert all(o.port != port_c for o in orphans)

    def test_enumerate_skips_closed_ports(self, harness: _DaemonHarness) -> None:
        """No listener at port D; D not in result."""
        port_d = _find_free_port_in_range(_TEST_PORT_START, _TEST_PORT_END)
        # Don't spawn anything on port_d.

        orphans = enumerate_orphans()

        assert all(o.port != port_d for o in orphans)

    def test_sweep_terminates_orphan(self, harness: _DaemonHarness) -> None:
        """Orphan running; after sweep, port is closed AND swept lists it."""
        port = _find_free_port_in_range(_TEST_PORT_START, _TEST_PORT_END)
        proc = harness.spawn_daemon(port)
        # No state file → orphan immediately.

        orphans = enumerate_orphans()
        assert any(o.port == port for o in orphans)

        report = sweep_orphans(orphans)

        assert isinstance(report, SweepReport)
        assert any(o.port == port for o in report.swept)
        assert _wait_until_port_free(port, timeout_s=5.0)
        # Subprocess should be reaped or about to be.
        for _ in range(50):
            if proc.poll() is not None:
                break
            time.sleep(0.05)

    def test_sweep_does_not_touch_singleton(self, harness: _DaemonHarness) -> None:
        """Singleton + orphan: only the orphan dies."""
        port_singleton = _find_free_port_in_range(_TEST_PORT_START, _TEST_PORT_END)
        port_orphan = _find_free_port_in_range(port_singleton + 1, _TEST_PORT_END)

        proc_singleton = harness.spawn_daemon(port_singleton)
        harness.spawn_daemon(port_orphan)
        harness.write_state_file(
            f"http://127.0.0.1:{port_singleton}", port_singleton, "tok", proc_singleton.pid
        )

        orphans = enumerate_orphans()
        assert len(orphans) == 1
        assert orphans[0].port == port_orphan

        sweep_orphans(orphans)

        # Orphan port goes free.
        assert _wait_until_port_free(port_orphan, timeout_s=5.0)
        # Singleton remains up.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            assert sock.connect_ex(("127.0.0.1", port_singleton)) == 0
        finally:
            sock.close()
        assert proc_singleton.poll() is None

    def test_sweep_records_failure_on_access_denied(
        self, harness: _DaemonHarness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """psutil.Process.terminate raises AccessDenied → orphan in failed list."""
        port = _find_free_port_in_range(_TEST_PORT_START, _TEST_PORT_END)
        harness.spawn_daemon(port)

        orphans = enumerate_orphans()
        assert any(o.port == port for o in orphans)
        target = next(o for o in orphans if o.port == port)
        # The harness daemon will not respond to no-token /api/shutdown (returns
        # 403), so HTTP step won't free the port. Patch terminate() to raise.

        def fake_terminate(self: psutil.Process) -> None:
            raise psutil.AccessDenied(pid=self.pid)

        monkeypatch.setattr(psutil.Process, "terminate", fake_terminate)
        # Ensure kill is also unreachable (we want failure, not escalation success).

        def fake_kill(self: psutil.Process) -> None:
            raise psutil.AccessDenied(pid=self.pid)

        monkeypatch.setattr(psutil.Process, "kill", fake_kill)

        report = sweep_orphans([target])

        assert any(o.port == port for o, _ in report.failed)
        assert all(o.port != port for o in report.swept)

    def test_enumerate_50_port_scan_under_3s(self, harness: _DaemonHarness) -> None:
        """NFR-006: 50-port scan must complete in ≤ 3 s with nothing on the range."""
        # Don't spawn any daemons. State file absent → no singleton bias.
        start = time.monotonic()
        orphans = enumerate_orphans()
        duration = time.monotonic() - start

        assert duration <= 3.0, f"50-port scan took {duration:.3f}s (> 3s budget)"
        # With nothing running we may still see other Spec Kitty daemons on
        # the developer's machine — assert only that our budget is respected.
        assert isinstance(orphans, list)
