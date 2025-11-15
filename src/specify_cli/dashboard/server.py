"""Dashboard HTTP server bootstrap utilities."""

from __future__ import annotations

import socket
import subprocess
import sys
import textwrap
import threading
from http.server import HTTPServer
from pathlib import Path
from typing import Optional, Tuple

from .handlers.router import DashboardRouter

__all__ = ["find_free_port", "start_dashboard", "run_dashboard_server"]


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

    raise RuntimeError(f"Could not find free port in range {start_port}-{start_port + max_attempts}")


def _build_handler_class(project_dir: Path, project_token: Optional[str]) -> type[DashboardRouter]:
    return type(
        'DashboardHandler',
        (DashboardRouter,),
        {
            'project_dir': str(project_dir),
            'project_token': project_token,
        },
    )


def run_dashboard_server(project_dir: Path, port: int, project_token: Optional[str]) -> None:
    """Run the dashboard server forever (used by detached child processes)."""
    handler_class = _build_handler_class(project_dir, project_token)
    server = HTTPServer(('127.0.0.1', port), handler_class)
    server.serve_forever()


def _background_script(project_dir: Path, port: int, project_token: Optional[str]) -> str:
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
        run_dashboard_server(Path({repr(str(project_dir))}), {port}, {repr(project_token)})
        """
    )


def start_dashboard(
    project_dir: Path,
    port: Optional[int] = None,
    background_process: bool = False,
    project_token: Optional[str] = None,
) -> Tuple[int, Optional[int]]:
    """
    Start the dashboard server.

    Returns tuple(port, pid). When background_process=True, pid is the process ID
    of the detached child process. When background_process=False, pid is None.

    Args:
        project_dir: Path to the project directory
        port: Port number (auto-selected if None)
        background_process: If True, run as detached subprocess; if False, run in thread
        project_token: Security token for the dashboard

    Returns:
        Tuple[port, pid]: Port number and process ID (None if threaded mode)
    """
    if port is None:
        port = find_free_port()

    project_dir_abs = project_dir.resolve()

    if background_process:
        script = _background_script(project_dir_abs, port, project_token)
        proc = subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return port, proc.pid

    handler_class = _build_handler_class(project_dir_abs, project_token)
    server = HTTPServer(('127.0.0.1', port), handler_class)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return port, None
