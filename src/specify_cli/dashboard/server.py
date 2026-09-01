"""Dashboard HTTP server bootstrap utilities."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

from specify_cli.core.errors import StructuredError
from specify_cli.core.loopback_http import create_loopback_server, serve_loopback_server

from .handlers.router import DashboardRouter

__all__ = [
    "BackgroundPortReportError",
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


def find_free_port(start_port: int = 9237, max_attempts: int = 100) -> int:
    """
    Find an available port starting from start_port.

    Uses a dual check (connect + bind) to avoid collisions with busy ports.
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(0.1)
            if test_sock.connect_ex(('127.0.0.1', port)) == 0:
                test_sock.close()
                continue
            test_sock.close()
        except OSError:
            pass

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue

    raise PortUnavailableError(f"Could not find free port in range {start_port}-{start_port + max_attempts}")


def _build_handler_class(project_dir: Path, project_token: str | None) -> type[DashboardRouter]:
    return type(
        'DashboardHandler',
        (DashboardRouter,),
        {
            'project_dir': str(project_dir),
            'project_token': project_token,
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


def _background_script(
    project_dir: Path,
    port: int,
    project_token: str | None,
    port_fd: int | None,
) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return textwrap.dedent(
        f"""
        import sys
        from pathlib import Path
        repo_root = Path({repr(str(repo_root))})
        # Always insert at position 0 to ensure correct spec-kitty version takes priority
        # over any other paths in PYTHONPATH or .pth files
        sys.path.insert(0, str(repo_root))
        from specify_cli.dashboard.server import run_dashboard_server
        run_dashboard_server(Path({repr(str(project_dir))}), {port}, {repr(project_token)}, {port_fd!r})
        """
    )


def _background_port_report_error(
    proc: subprocess.Popen[bytes], raw_report: bytes
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
        f"Detached dashboard process failed to report its bound port for port=0 ({detail}; {process_state}).",
        exit_code=exit_code,
    )


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
    """
    if port is None:
        port = find_free_port()

    project_dir_abs = project_dir.resolve()

    if background_process:
        # port=0 asks the OS for an ephemeral port; the detached child binds
        # it, not us, so we can't read it off a socket here. Hand the child
        # the write end of a pipe and block on the read end until it reports
        # back the port it actually bound (mirrors the threaded branch below,
        # which reads server_address[1] instead). A concrete port needs no
        # round trip — it's already known.
        pipe = os.pipe() if port == 0 else None
        port_fd = pipe[1] if pipe is not None else None

        script = _background_script(project_dir_abs, port, project_token, port_fd)
        try:
            proc = subprocess.Popen(
                [sys.executable, '-c', script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                pass_fds=(port_fd,) if port_fd is not None else (),
            )
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
                raise _background_port_report_error(proc, raw_report) from exc

        return port, proc.pid

    handler_class = _build_handler_class(project_dir_abs, project_token)
    server = create_loopback_server(port, handler_class)

    # Read the actually-bound port back off the socket rather than trusting
    # the caller-supplied value: with port=0 the OS assigns the real port at
    # bind time, and echoing the input back would silently report "0".
    actual_port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return actual_port, None
