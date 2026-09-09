"""Dashboard HTTP server bootstrap utilities."""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import IO

from kernel.paths import get_runtime_state_root

from specify_cli.core.atomic import atomic_write
from specify_cli.core.errors import StructuredError
from specify_cli.core.loopback_http import create_loopback_server, serve_loopback_server

from . import _server_main
from .handlers.router import DashboardRouter

__all__ = [
    "BackgroundPortReportError",
    "PortUnavailableError",
    "find_free_port",
    "start_dashboard",
    "run_dashboard_server",
]

#: Module entry point launched for the detached background dashboard child.
#: Launched via ``-m`` (a real module), never ``-c`` codegen — see
#: ``_server_main.py`` module docstring for why (#4125). Referenced via the
#: imported module (not a string literal) so the launch target stays
#: rename-safe and the module is statically wired, not "written but never used".
_BACKGROUND_MODULE = _server_main.__name__

#: How long ``start_dashboard(background_process=True)`` waits for the
#: detached child to actually bind and start accepting connections before
#: giving up and reporting a (typed, log-tail-bearing) failure.
_READY_TIMEOUT_SECONDS = 10.0
_READY_POLL_INTERVAL_SECONDS = 0.05


class PortUnavailableError(StructuredError):
    """Raised when no free port can be found in the scanned range.

    Carries a stable ``error_code`` (NFR-007, #1893) so callers branch on the
    typed value rather than substring-matching the human-readable message.
    """

    error_code: str = "DASHBOARD_PORT_UNAVAILABLE"


class BackgroundPortReportError(StructuredError):
    """Raised when a detached dashboard child does not become ready.

    Covers both failure shapes: the child never reports/binds its port (the
    ``port=0`` ephemeral case) and the child exits, or times out, before its
    socket starts accepting connections (every case, including a concrete
    caller-supplied port). Carries the child's exit status, when known, so
    callers can branch on the typed value and contextual attribute rather
    than parsing the message.
    """

    error_code: str = "DASHBOARD_BACKGROUND_PORT_REPORT_FAILED"

    def __init__(self, message: str, *, exit_code: int | None) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def find_free_port(start_port: int = 9237, max_attempts: int = 100) -> int:
    """
    Find an available port starting from start_port.

    Uses a dual check (connect + bind) to avoid collisions with busy ports.
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(0.1)
            if test_sock.connect_ex(("127.0.0.1", port)) == 0:
                test_sock.close()
                continue
            test_sock.close()
        except OSError:
            pass

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue

    raise PortUnavailableError(f"Could not find free port in range {start_port}-{start_port + max_attempts}")


def _build_handler_class(project_dir: Path, project_token: str | None) -> type[DashboardRouter]:
    return type(
        "DashboardHandler",
        (DashboardRouter,),
        {
            "project_dir": str(project_dir),
            "project_token": project_token,
        },
    )


def run_dashboard_server(
    project_dir: Path,
    port: int,
    project_token: str | None,
    port_report_path: Path | None = None,
) -> None:
    """Run the dashboard server forever (used by detached child processes).

    The dashboard serves local state only; it starts no daemon of its own and
    depends on none.

    ``port_report_path``, when given, names a sidecar file this writes the
    actually-bound port into (atomically) right after bind, before blocking
    in ``serve_forever`` — how a detached child reports an OS-assigned port
    (``port=0``) back to the parent that spawned it (see ``start_dashboard``).
    A plain file replaces the previous ``os.pipe()`` + ``pass_fds`` hand-off:
    ``pass_fds`` raises ``ValueError`` on Windows (numeric fd inheritance is
    POSIX-only), so a filesystem hand-off is used uniformly on every
    platform instead of branching the mechanism itself.
    """
    handler_class = _build_handler_class(project_dir, project_token)

    on_bound = None
    if port_report_path is not None:

        def _report_bound_port(actual_port: int) -> None:
            atomic_write(port_report_path, str(actual_port))

        on_bound = _report_bound_port

    serve_loopback_server(port, handler_class, on_bound=on_bound)


def _dashboard_state_dir() -> Path:
    """Return (creating if needed) the directory for dashboard runtime logs.

    Lives under the shared spec-kitty runtime STATE root (``~/.spec-kitty``
    on POSIX; the platform-equivalent via ``get_runtime_state_root()`` on
    Windows) rather than under the served project directory, so a detached
    child's crash log and ephemeral-port sidecar file persist independent of
    the project that launched it and honour the same per-worker HOME
    isolation as the rest of the test suite.
    """
    state_dir = get_runtime_state_root() / "dashboard" / "logs"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _open_background_log() -> tuple[Path, IO[bytes]]:
    """Open a fresh log file to capture a detached dashboard child's output.

    Previously stdout/stderr were routed to ``DEVNULL``, so a crashing child
    was silently swallowed and the parent had no way to explain a failed
    launch (#4125). Routing both streams to one file under the dashboard
    state dir keeps every launch's output on disk so a future crash is
    diagnosable, and lets a failed readiness wait quote the tail of it.
    """
    state_dir = _dashboard_state_dir()
    fd, raw_path = tempfile.mkstemp(prefix="dashboard-", suffix=".log", dir=str(state_dir))
    return Path(raw_path), os.fdopen(fd, "wb")


def _make_port_report_path() -> Path:
    """Create an empty sidecar file a detached child reports its bound port into.

    Used only for the ``port == 0`` (OS-assigned ephemeral port) case.
    """
    state_dir = _dashboard_state_dir()
    fd, raw_path = tempfile.mkstemp(prefix="dashboard-port-", suffix=".txt", dir=str(state_dir))
    os.close(fd)
    return Path(raw_path)


def _background_launch_argv(
    project_dir: Path,
    port: int,
    project_token: str | None,
    port_report_path: Path | None,
) -> list[str]:
    """Build the detached child's argv.

    Launches a real module entry point
    (``python -m specify_cli.dashboard._server_main``) with plain argv,
    instead of the former ``python -c <codegen>`` string — see
    ``_server_main.py`` for why the ``-c`` form crashed on Windows.
    """
    argv = [
        sys.executable,
        "-m",
        _BACKGROUND_MODULE,
        "--project-dir",
        str(project_dir),
        "--port",
        str(port),
    ]
    if project_token is not None:
        argv += ["--token", project_token]
    if port_report_path is not None:
        argv += ["--port-report-file", str(port_report_path)]
    return argv


def _launch_background_dashboard(
    argv: list[str],
    *,
    log_file: IO[bytes],
    platform: str | None = None,
) -> subprocess.Popen[bytes]:
    """Launch the detached dashboard child using platform-native detachment.

    POSIX: ``start_new_session=True`` puts the child in a new session so it
    survives the parent exiting. Windows: ``start_new_session`` is a no-op
    there, so ``CREATE_NEW_PROCESS_GROUP`` is the equivalent — it detaches
    the child from the parent's console/Ctrl+C signal group. Mirrors
    ``review/pre_review_gate.py::_launch_scoped_process``, the in-repo
    exemplar for this exact platform branch (the sync daemon this pattern
    used to be sourced from was deleted in The Convergence).
    """
    platform = platform or os.name
    if platform == "nt":
        return subprocess.Popen(
            argv,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    return subprocess.Popen(
        argv,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def _read_log_tail(log_path: Path, max_lines: int = 40) -> str:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def _port_is_accepting_connections(port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _read_reported_port(port_report_path: Path) -> int | None:
    try:
        raw = port_report_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _background_ready_error(proc: subprocess.Popen[bytes], log_path: Path, detail: str) -> BackgroundPortReportError:
    exit_code = proc.poll()
    if exit_code is None:
        try:
            exit_code = proc.wait(timeout=0.1)
        except subprocess.TimeoutExpired:
            exit_code = None

    tail = _read_log_tail(log_path)
    message = f"Detached dashboard process failed to start ({detail})."
    message += f" Log tail ({log_path}):\n{tail}" if tail else f" Log file: {log_path}"
    return BackgroundPortReportError(message, exit_code=exit_code)


def _terminate_orphaned_process(proc: subprocess.Popen[bytes]) -> None:
    """Best-effort terminate-then-kill a still-running detached child.

    Called right before ``_await_background_ready`` reports failure (a
    readiness timeout, and defensively on the exited-child path in case the
    process somehow still lives) so a slow-but-live child is never left
    running detached after the parent already reported the launch failed —
    an orphan that could go on to bind the port *after* failure was
    reported (#4125 follow-up). Reaps the process (``wait``) so no zombie is
    left behind, and never lets a ``terminate``/``kill`` error mask the
    caller's original failure — every exception here is swallowed.
    """
    if proc.poll() is not None:
        return  # already exited; nothing to reap here
    with contextlib.suppress(OSError):
        proc.terminate()
    try:
        proc.wait(timeout=2.0)
        return
    except subprocess.TimeoutExpired:
        pass
    except OSError:
        return
    with contextlib.suppress(OSError):
        proc.kill()
    with contextlib.suppress(subprocess.TimeoutExpired, OSError):
        proc.wait(timeout=2.0)


def _await_background_ready(
    proc: subprocess.Popen[bytes],
    *,
    port: int,
    port_report_path: Path | None,
    log_path: Path,
    timeout: float = _READY_TIMEOUT_SECONDS,
    poll_interval: float = _READY_POLL_INTERVAL_SECONDS,
) -> int:
    """Block until the detached dashboard child is actually listening.

    Returns the actually-bound port (equal to ``port`` unless ``port == 0``,
    in which case it is read back from ``port_report_path``). Raises
    ``BackgroundPortReportError`` — carrying the child's exit status and a
    tail of its log — if the child exits before becoming ready or the
    deadline elapses, so a dead or hung child is never reported as a live
    dashboard (closes the gap where ``DEVNULL`` + no probe let a crashed
    child be reported as a healthy start, #4125).

    Liveness is checked FIRST on every iteration, before trusting a TCP
    connect. A probe that only asks "does something answer on this port"
    can be satisfied by a FOREIGN process squatting the exact same port
    after our own child died on a bind conflict (most reachable on the
    concrete-port path: a caller-supplied port, or one from
    ``find_free_port()``, which is inherently check-then-bind racy) — that
    would misreport a dead child as a live dashboard, with the returned URL
    actually pointing at the squatter (#4125 follow-up). On both the
    child-exited and the timeout failure path, an orphaned-but-still-live
    child is terminated (see ``_terminate_orphaned_process``) before the
    error is raised, so a slow child is never left running detached.
    """
    deadline = time.monotonic() + timeout
    actual_port: int | None = None if port == 0 else port

    while True:
        exit_code = proc.poll()
        if exit_code is not None:
            error = _background_ready_error(proc, log_path, f"child exited with status {exit_code} before becoming ready")
            _terminate_orphaned_process(proc)
            raise error

        if actual_port is None and port_report_path is not None:
            actual_port = _read_reported_port(port_report_path)

        if actual_port is not None and _port_is_accepting_connections(actual_port):
            return actual_port

        if time.monotonic() >= deadline:
            error = _background_ready_error(proc, log_path, f"dashboard did not become ready within {timeout}s")
            _terminate_orphaned_process(proc)
            raise error

        time.sleep(poll_interval)


def start_dashboard(
    project_dir: Path,
    port: int | None = None,
    background_process: bool = False,
    project_token: str | None = None,
) -> tuple[int, int | None]:
    """
    Start the dashboard server.

    Returns tuple(port, pid). When background_process=True, pid is the process ID
    of the detached child process. When background_process=False, pid is None.

    Args:
        project_dir: Path to the project directory
        port: Port number (auto-selected if None; pass 0 for an OS-assigned
            ephemeral port)
        background_process: If True, run as detached subprocess; if False, run in thread
        project_token: Security token for the dashboard

    Returns:
        Tuple[port, pid]: Port number and process ID (None if threaded mode)
    """
    if port is None:
        port = find_free_port()

    project_dir_abs = project_dir.resolve()

    if background_process:
        # port=0 asks the OS for an ephemeral port; the detached child binds
        # it, not us, so we can't read it off a socket here. A concrete port
        # needs no round trip -- it's already known -- but every path (both
        # concrete and ephemeral) is verified via a real readiness probe
        # below before this reports success (#4125 item c: the concrete-port
        # path previously had no probe at all).
        port_report_path = _make_port_report_path() if port == 0 else None
        log_path, log_file = _open_background_log()

        argv = _background_launch_argv(project_dir_abs, port, project_token, port_report_path)

        try:
            proc = _launch_background_dashboard(argv, log_file=log_file)
        except Exception:
            log_file.close()
            if port_report_path is not None:
                port_report_path.unlink(missing_ok=True)
            raise
        log_file.close()  # our copy; the child keeps its own handle open

        try:
            actual_port = _await_background_ready(
                proc,
                port=port,
                port_report_path=port_report_path,
                log_path=log_path,
            )
        finally:
            if port_report_path is not None:
                port_report_path.unlink(missing_ok=True)

        # Clean success: the log's only purpose is crash diagnosis on the
        # failure path (already quoted into the raised error's tail there,
        # well before this point). Leaving it on disk after every launch
        # accumulates one file per `start_dashboard(background_process=True)`
        # call forever under the shared runtime state dir (#4125 follow-up);
        # unlink it here so only failed launches leave a log behind.
        with contextlib.suppress(OSError):
            log_path.unlink(missing_ok=True)

        return actual_port, proc.pid

    handler_class = _build_handler_class(project_dir_abs, project_token)
    server = create_loopback_server(port, handler_class)

    # Read the actually-bound port back off the socket rather than trusting
    # the caller-supplied value: with port=0 the OS assigns the real port at
    # bind time, and echoing the input back would silently report "0".
    actual_port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return actual_port, None
