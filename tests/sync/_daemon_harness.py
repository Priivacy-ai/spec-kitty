"""Shared live-subprocess harness for sync-daemon integration tests.

This module is intentionally **not** prefixed with ``test_`` so pytest does not
collect it; it is imported by test files that need real loopback daemons.

Usage (shared by WP06, WP07, WP08)::

    from tests.sync._daemon_harness import DaemonHarness, find_free_port_in_range

    harness = DaemonHarness(tmp_path / "sync-daemon")
    port = find_free_port_in_range(9400, 9425)
    proc = harness.spawn_daemon(port, "tok", version="3.2.2")
    ...
    harness.shutdown()  # always call in teardown

Port range convention
---------------------
* WP06 (this suite):  ``[9400, 9425)``
* WP07–WP08:         ``[9375, 9400)``  (reserved for later WPs)
* test_orphan_sweep:  ``[9425, 9450)``  (existing suite)

Never overlap ranges across suites; each must run serially with ``-n0``.
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import textwrap
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

# ---------------------------------------------------------------------------
# Port helpers (re-exposed so callers import from a single location)
# ---------------------------------------------------------------------------


def find_free_port_in_range(start: int, end: int) -> int:
    """Return the first port in ``[start, end)`` that is currently unbound.

    Raises ``RuntimeError`` when no free port exists in the range.
    """
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"no free port in [{start}, {end})")


def wait_until_listening(port: int, timeout_s: float = 10.0) -> bool:
    """Poll ``port`` until something accepts TCP connections, or ``timeout_s`` elapses.

    Returns ``True`` if the port started listening within the deadline.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.05)
    return False


def wait_until_port_free(port: int, timeout_s: float = 8.0) -> bool:
    """Poll ``port`` until it stops listening, or ``timeout_s`` elapses.

    Returns ``True`` if the port became free within the deadline.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return True
        time.sleep(0.05)
    return False


# ---------------------------------------------------------------------------
# Low-level process helpers
# ---------------------------------------------------------------------------

# Note: the daemon argv markers are sourced verbatim from the production
# constants ``DAEMON_SCOPE_ARG_PREFIX`` / ``DAEMON_EXEC_ARG_PREFIX`` (imported
# inside ``spawn_daemon``); the harness keeps no local duplicates of them.


def _build_spawn_script(port: int, token: str) -> str:
    """Return the inline Python snippet passed to ``python -c``."""
    return textwrap.dedent(
        f"""\
        import os
        os.environ["SPEC_KITTY_SYNC_MINIMAL_IMPORT"] = "1"
        from specify_cli.sync.daemon import run_sync_daemon
        run_sync_daemon({port!r}, {token!r})
        """
    )


def _build_wedged_daemon_shape_script(port: int) -> str:
    """Return a spawn-shaped script that listens but never answers health."""
    return textwrap.dedent(
        f"""\
        _spawn_shape_marker = "run_sync_daemon({port!r})"
        import socket
        import threading
        import time

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", {port!r}))
        sock.listen()

        def hold(conn):
            try:
                time.sleep(30)
            finally:
                conn.close()

        while True:
            conn, _addr = sock.accept()
            threading.Thread(target=hold, args=(conn,), daemon=True).start()
        """
    )


def _terminate_proc(proc: subprocess.Popen[bytes]) -> None:
    """Best-effort terminate a ``Popen``, escalating to SIGKILL on timeout."""
    if proc.poll() is not None:
        return
    with contextlib.suppress(Exception):
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
            return
        except subprocess.TimeoutExpired:
            pass
    with contextlib.suppress(Exception):
        proc.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=3.0)


# ---------------------------------------------------------------------------
# Wedged (plain) TCP listener
# ---------------------------------------------------------------------------


class _SilentHandler(BaseHTTPRequestHandler):
    """Accepts connections but never answers ``/api/health`` — simulates a wedged daemon.

    All paths return 200 ``{"ok": true}`` to confirm TCP connectivity while
    giving no Spec Kitty identity signal.
    """

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Suppress logging noise from background threads.
        pass

    def do_GET(self) -> None:  # noqa: N802
        # Return a non-SK body: no ``protocol_version`` / ``package_version`` keys.
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        # Accept but ignore — wedged daemons do not act on shutdown requests.
        self.send_response(200)
        self.end_headers()


# ---------------------------------------------------------------------------
# Public harness class (T026)
# ---------------------------------------------------------------------------


class DaemonHarness:
    """Tracks real subprocess daemons and plain TCP servers for live integration tests.

    Provides:
    * :meth:`spawn_daemon` — real ``run_sync_daemon`` subprocess with optional
      version spoof (``SPEC_KITTY_CLI_VERSION``) and scope isolation (``HOME``).
    * :meth:`spawn_plain` — a plain TCP listener that never identifies as SK.
    * :meth:`write_state_file` — write a canonical four-line daemon state file.
    * :attr:`port_pids` — port-to-PID map for ``psutil``-bypass on macOS.
    * :meth:`shutdown` — escalating terminate→kill for every spawned resource.

    All spawned processes use ``start_new_session=True`` so they are not in
    the test process's session; ``shutdown()`` in ``finally`` / fixture teardown
    prevents leaked daemons after the test.

    macOS note: ``psutil.net_connections`` raises ``AccessDenied`` for sockets
    owned by another UID.  Always use :attr:`port_pids` instead of live
    enumeration in assertions.
    """

    def __init__(self, state_file: Path) -> None:
        self.state_file: Path = state_file
        # Process handle list — every Popen we spawn, in order.
        self._procs: list[subprocess.Popen[bytes]] = []
        # Plain-server list — (HTTPServer, Thread) pairs.
        self._servers: list[tuple[HTTPServer, Thread]] = []
        # port → PID map — populated by spawn_daemon / tracked manually since
        # psutil.net_connections may raise AccessDenied on macOS.
        self.port_pids: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Spawn helpers
    # ------------------------------------------------------------------

    def spawn_daemon(
        self,
        port: int,
        token: str = "test-token-hex",
        *,
        version: str | None = None,
        scope_root: str | None = None,
        home: str | None = None,
    ) -> subprocess.Popen[bytes]:
        """Spawn a real ``run_sync_daemon`` subprocess on ``port``.

        Args:
            port:       loopback port to bind.
            token:      daemon bearer token.
            version:    when set, passed as ``SPEC_KITTY_CLI_VERSION`` so the
                        daemon self-reports this version (DD-04 version spoof).
            scope_root: when set, the ``--spec-kitty-daemon-root=`` argv marker
                        embedded in the daemon's command line, making the reaper
                        treat it as belonging to that scope.  Defaults to
                        the caller's resolved daemon-root (same scope).
            home:       when set, overrides ``HOME`` / ``SPEC_KITTY_HOME`` in the
                        subprocess environment to simulate a cross-home daemon.
        """
        from specify_cli.sync.daemon import (
            DAEMON_EXEC_ARG_PREFIX,
            DAEMON_SCOPE_ARG_PREFIX,
            _daemon_scope_root,
            _spawn_interpreter_identity,
        )

        env: dict[str, str] = {**os.environ}

        # Version spoof: _get_package_version() checks this env var first.
        if version is not None:
            env["SPEC_KITTY_CLI_VERSION"] = version

        # Cross-home scope isolation.
        if home is not None:
            env["HOME"] = home
            env["SPEC_KITTY_HOME"] = home

        # Scope-root marker — must appear in argv for the reaper to match.
        if scope_root is None:
            # Default: same-scope as this process.
            scope_root = _daemon_scope_root()
        scope_marker = DAEMON_SCOPE_ARG_PREFIX + scope_root
        exec_marker = DAEMON_EXEC_ARG_PREFIX + _spawn_interpreter_identity()

        script = _build_spawn_script(port, token)
        proc: subprocess.Popen[bytes] = subprocess.Popen(
            [sys.executable, "-c", script, scope_marker, exec_marker],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )

        if not wait_until_listening(port, timeout_s=10.0):
            proc.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=2.0)
            raise RuntimeError(
                f"daemon on port {port} (version={version!r}) never started listening"
            )

        self._procs.append(proc)
        self.port_pids[port] = proc.pid
        return proc

    def spawn_plain(self, port: int) -> tuple[HTTPServer, Thread]:
        """Bind a plain (non-SK) TCP listener on ``port``.

        The server responds with ``{"ok": true}`` (no SK identity keys) so
        the classifier treats it as ``never_touch`` / ``not_spec_kitty``.
        A listener that accepts but never answers ``/api/health`` is exactly
        the "wedged" scenario described in D-01.
        """
        server = HTTPServer(("127.0.0.1", port), _SilentHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        if not wait_until_listening(port, timeout_s=5.0):
            server.shutdown()
            thread.join(timeout=2.0)
            raise RuntimeError(f"plain server on port {port} never started listening")
        self._servers.append((server, thread))
        return server, thread

    def spawn_wedged_daemon_shape(
        self,
        port: int,
        *,
        scope_root: str | None = None,
    ) -> subprocess.Popen[bytes]:
        """Spawn a scope-marked process that looks like daemon argv but hangs health."""
        from specify_cli.sync.daemon import (
            DAEMON_EXEC_ARG_PREFIX,
            DAEMON_SCOPE_ARG_PREFIX,
            _daemon_scope_root,
            _spawn_interpreter_identity,
        )

        if scope_root is None:
            scope_root = _daemon_scope_root()
        scope_marker = DAEMON_SCOPE_ARG_PREFIX + scope_root
        exec_marker = DAEMON_EXEC_ARG_PREFIX + _spawn_interpreter_identity()

        proc: subprocess.Popen[bytes] = subprocess.Popen(
            [sys.executable, "-c", _build_wedged_daemon_shape_script(port), scope_marker, exec_marker],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, "SPEC_KITTY_SYNC_MINIMAL_IMPORT": "1"},
        )

        if not wait_until_listening(port, timeout_s=10.0):
            proc.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=2.0)
            raise RuntimeError(f"wedged daemon-shaped process on port {port} never listened")

        self._procs.append(proc)
        self.port_pids[port] = proc.pid
        return proc

    def write_state_file(
        self,
        url: str,
        port: int,
        token: str,
        pid: int,
    ) -> None:
        """Write a canonical four-line daemon state file (matches ``_write_daemon_file``).

        Creates parent directories as needed.
        """
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            f"{url}\n{port}\n{token}\n{pid}\n",
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Terminate all spawned resources.

        Escalation order per process: terminate → wait(3 s) → kill → wait(3 s).
        Plain servers are shut down via the stdlib ``server.shutdown()`` API.

        This method is idempotent; calling it twice is safe.
        """
        for proc in self._procs:
            _terminate_proc(proc)
        for server, thread in self._servers:
            with contextlib.suppress(Exception):
                server.shutdown()
            with contextlib.suppress(Exception):
                server.server_close()
            thread.join(timeout=3.0)
        # Clear so a second call is a no-op.
        self._procs.clear()
        self._servers.clear()
