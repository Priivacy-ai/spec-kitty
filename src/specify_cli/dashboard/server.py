"""Dashboard HTTP server bootstrap utilities."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from specify_cli.core.errors import StructuredError
from specify_cli.core.loopback_http import create_loopback_server, serve_loopback_server
from specify_cli.paths import get_runtime_root

from .handlers.router import DashboardRouter

__all__ = [
    "BackgroundPortReportError",
    "DashboardSpawnError",
    "PortUnavailableError",
    "find_free_port",
    "start_dashboard",
    "run_dashboard_server",
]


class PortUnavailableError(StructuredError):
    """Raised when no free port can be found in the scanned range.

    Carries a stable ``error_code`` (NFR-007, #1893) so callers branch on the
    typed value rather than substring-matching the human-readable message.
    """

    error_code: str = "DASHBOARD_PORT_UNAVAILABLE"


class BackgroundPortReportError(StructuredError):
    """Raised when a detached dashboard child does not report a valid bound port.

    Carries the child's exit status when it is known so callers can branch on
    the typed value and contextual attribute rather than parsing the message.
    """

    error_code: str = "DASHBOARD_BACKGROUND_PORT_REPORT_FAILED"

    def __init__(self, message: str, *, exit_code: int | None) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class DashboardSpawnError(StructuredError):
    """Raised when the detached dashboard child dies before its port is reachable.

    Carries the child's exit status and a log tail in the message so the crash
    that killed it is diagnosable at the call site instead of vanishing into a
    detached process's discarded output (#4125).
    """

    error_code: str = "DASHBOARD_SPAWN_FAILED"

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
    port_fd: int | None = None,
) -> None:
    """Run the dashboard server forever (used by detached child processes).

    The dashboard serves local state only; it starts no daemon of its own and
    depends on none.

    ``port_fd``, when given, is an inherited pipe write-end this writes the
    actually-bound port to (and closes) right after bind, before blocking in
    ``serve_forever`` — how a detached child reports an OS-assigned port
    (``port=0``) back to the parent that spawned it (see ``start_dashboard``).
    """
    handler_class = _build_handler_class(project_dir, project_token)

    on_bound = None
    if port_fd is not None:
        fd = port_fd

        def _report_bound_port(actual_port: int) -> None:
            os.write(fd, str(actual_port).encode())
            os.close(fd)

        on_bound = _report_bound_port

    serve_loopback_server(port, handler_class, on_bound=on_bound)


# Detached children are spawned as ``python -m`` of this module, never via
# ``python -c`` with a generated script: ``-c`` leaves ``__main__`` without a
# ``__file__`` attribute, which a Windows-platform transitive import in the
# server import chain reads, killing the child before it binds (#4125).
_SPAWN_MODULE = "specify_cli.dashboard._server_main"
_SPAWN_READINESS_TIMEOUT_SECONDS = 10.0
_SPAWN_READINESS_POLL_SECONDS = 0.1
_SPAWN_LOG_TAIL_BYTES = 4096


def _dashboard_spawn_log_file() -> Path:
    """Log file detached dashboard children's stdout/stderr are piped to.

    Mirrors the former sync daemon's ``~/.spec-kitty/sync-daemon.log``
    observability pattern: a detached child's output must land somewhere a
    human can read after the fact, or the next spawn-path crash is
    undiagnosable (#4125).
    """
    runtime_base: Path = get_runtime_root().base
    return runtime_base / "dashboard-server.log"


def _spawn_child_env() -> dict[str, str]:
    """Child env with this checkout's import root prepended to ``PYTHONPATH``.

    The parent of the running ``specify_cli`` package directory, prepended to
    ``PYTHONPATH``, makes the ``-m`` child resolve the same spec-kitty the
    parent is running — taking priority over any other paths in ``PYTHONPATH``
    or ``.pth`` files — regardless of the child interpreter's own
    site-packages.
    """
    import_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(import_root) if not existing else os.pathsep.join([str(import_root), existing])
    return env


def _read_spawn_log_tail(log_path: Path) -> str:
    """Return the last ``_SPAWN_LOG_TAIL_BYTES`` of the spawn log, '' if empty."""
    try:
        with open(log_path, "rb") as log_fh:
            log_fh.seek(0, os.SEEK_END)
            size = log_fh.tell()
            log_fh.seek(max(0, size - _SPAWN_LOG_TAIL_BYTES))
            return log_fh.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _spawn_log_detail(log_path: Path) -> str:
    tail = _read_spawn_log_tail(log_path)
    if tail:
        return f"\nLog tail ({log_path}):\n{tail}"
    return f"\nLog file is empty ({log_path})."


def _spawn_dashboard_process(
    project_dir: Path,
    port: int,
    project_token: str | None,
    port_fd: int | None,
) -> tuple[subprocess.Popen[bytes], Path]:
    """Spawn the detached dashboard child via ``python -m`` and return it.

    Output goes to the spawn log (never DEVNULL), stdin is closed, and the
    child is detached per platform: a new session on POSIX, the
    ``DETACHED_PROCESS`` creation flag on Windows (where ``start_new_session``
    is inert).
    """
    argv = [sys.executable, "-m", _SPAWN_MODULE, str(project_dir), str(port)]
    if project_token is not None:
        argv.append(project_token)
    if port_fd is not None:
        argv.extend(["--port-fd", str(port_fd)])

    log_path = _dashboard_spawn_log_file()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(log_path, "a")  # noqa: SIM115 — the child inherits the fd across Popen; the parent copy is closed immediately after
    try:
        # DETACHED_PROCESS exists only on Windows; getattr keeps this importable
        # (and this function unit-testable with a stubbed subprocess) elsewhere.
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) if sys.platform == "win32" else 0
        proc = subprocess.Popen(
            argv,
            stdout=log_fh,
            stderr=log_fh,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            creationflags=creationflags,
            env=_spawn_child_env(),
            pass_fds=(port_fd,) if port_fd is not None else (),
        )
    finally:
        log_fh.close()
    return proc, log_path


def _port_accepts_connection(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False


def _wait_for_spawn_readiness(
    proc: subprocess.Popen[bytes],
    port: int,
    log_path: Path,
    *,
    timeout_seconds: float = _SPAWN_READINESS_TIMEOUT_SECONDS,
) -> None:
    """Poll until the detached child's port is reachable; raise on early exit.

    A child that dies before binding used to leave the caller reporting a
    started dashboard that silently wasn't there (#4125). Now its exit status
    and log tail surface here. A child still alive but not bound within the
    window is left to the caller's (longer) health-check poll rather than
    failed here — a slow-but-healthy spawn is not an error.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        exit_code = proc.poll()
        if exit_code is not None:
            raise DashboardSpawnError(
                f"Detached dashboard process exited with status {exit_code} before binding port {port}.{_spawn_log_detail(log_path)}",
                exit_code=exit_code,
            )
        if _port_accepts_connection(port):
            return
        time.sleep(_SPAWN_READINESS_POLL_SECONDS)


def _background_port_report_error(
    proc: subprocess.Popen[bytes],
    raw_report: bytes,
    log_path: Path,
) -> BackgroundPortReportError:
    exit_code = proc.poll()
    if exit_code is None:
        try:
            exit_code = proc.wait(timeout=0.1)
        except subprocess.TimeoutExpired:
            exit_code = None

    process_state = f"child exited with status {exit_code}" if exit_code is not None else "child is still running but closed the reporting pipe"
    detail = f"invalid port report {raw_report!r}" if raw_report else "no port report"
    return BackgroundPortReportError(
        f"Detached dashboard process failed to report its bound port for port=0 ({detail}; {process_state}).{_spawn_log_detail(log_path)}",
        exit_code=exit_code,
    )


def _start_background_dashboard(
    project_dir_abs: Path,
    port: int,
    project_token: str | None,
) -> tuple[int, int]:
    # port=0 asks the OS for an ephemeral port; the detached child binds
    # it, not us, so we can't read it off a socket here. Hand the child
    # the write end of a pipe and block on the read end until it reports
    # back the port it actually bound (mirrors the threaded branch below,
    # which reads server_address[1] instead). A concrete port needs no
    # round trip — it's already known.
    pipe = os.pipe() if port == 0 else None
    port_fd = pipe[1] if pipe is not None else None

    try:
        proc, log_path = _spawn_dashboard_process(project_dir_abs, port, project_token, port_fd)
    except Exception:
        if pipe is not None:
            os.close(pipe[0])
            os.close(pipe[1])
        raise

    if pipe is not None:
        read_fd, write_fd = pipe
        os.close(write_fd)  # our copy; the child's own copy keeps the pipe open until it reports back
        chunks = []
        try:
            while chunk := os.read(read_fd, 32):
                chunks.append(chunk)
        finally:
            os.close(read_fd)

        raw_report = b"".join(chunks)
        try:
            port = int(raw_report.decode())
        except (UnicodeDecodeError, ValueError) as exc:
            raise _background_port_report_error(proc, raw_report, log_path) from exc

    _wait_for_spawn_readiness(proc, port, log_path)
    return port, proc.pid


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
            ephemeral port bound atomically with no separate probe step)
        background_process: If True, run as detached subprocess; if False, run in thread
        project_token: Security token for the dashboard

    Returns:
        Tuple[port, pid]: Port number and process ID (None if threaded mode)

    Raises:
        DashboardSpawnError: the detached child exited before its port was
            reachable (the message carries the child's log tail, #4125)
    """
    if port is None:
        port = find_free_port()

    project_dir_abs = project_dir.resolve()

    if background_process:
        return _start_background_dashboard(project_dir_abs, port, project_token)

    handler_class = _build_handler_class(project_dir_abs, project_token)
    server = create_loopback_server(port, handler_class)

    # Read the actually-bound port back off the socket rather than trusting
    # the caller-supplied value: with port=0 the OS assigns the real port at
    # bind time, and echoing the input back would silently report "0".
    actual_port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return actual_port, None
