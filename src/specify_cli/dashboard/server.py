"""Dashboard HTTP server bootstrap utilities.

Hosts the strangler boundary that selects between the legacy
``BaseHTTPServer`` stack (this file's classic implementation) and the new
FastAPI transport at ``src/dashboard/api/`` based on the
``dashboard.transport`` config flag.

See ``architecture/2.x/adr/2026-05-02-2-fastapi-openapi-transport.md`` for
the architectural decision and ``docs/migration/dashboard-fastapi-transport.md``
for the operator runbook.
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import textwrap
import threading
from http.server import HTTPServer
from pathlib import Path
from typing import Literal, Optional, Tuple

from .handlers.router import DashboardRouter

__all__ = [
    "find_free_port",
    "start_dashboard",
    "run_dashboard_server",
    "resolve_transport",
]

Transport = Literal["legacy", "fastapi"]
DEFAULT_TRANSPORT: Transport = "fastapi"

logger = logging.getLogger(__name__)


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


def _build_handler_class(project_dir: Path, project_token: str | None) -> type[DashboardRouter]:
    return type(
        'DashboardHandler',
        (DashboardRouter,),
        {
            'project_dir': str(project_dir),
            'project_token': project_token,
        },
    )


def resolve_transport(
    project_dir: Path,
    cli_override: Transport | None = None,
) -> Transport:
    """Resolve the active dashboard transport.

    Precedence:
        1. Explicit CLI flag (``--transport legacy|fastapi``) wins if set.
        2. ``.kittify/config.yaml`` → ``dashboard.transport`` is read next.
        3. ``DEFAULT_TRANSPORT`` is used when neither source provides a value.

    Args:
        project_dir: project root used to locate ``.kittify/config.yaml``.
        cli_override: value from the ``--transport`` CLI flag, or None.

    Returns:
        ``"legacy"`` or ``"fastapi"``. Unknown values raise ``ValueError``.
    """
    if cli_override is not None:
        if cli_override not in ("legacy", "fastapi"):
            raise ValueError(
                f"Unknown dashboard transport: {cli_override!r}. "
                "Expected 'legacy' or 'fastapi'."
            )
        return cli_override

    config_value = _read_transport_from_config(project_dir)
    if config_value is None:
        return DEFAULT_TRANSPORT
    if config_value not in ("legacy", "fastapi"):
        raise ValueError(
            f"Unknown dashboard.transport value in .kittify/config.yaml: "
            f"{config_value!r}. Expected 'legacy' or 'fastapi'."
        )
    return config_value


def _read_transport_from_config(project_dir: Path) -> str | None:
    """Read ``dashboard.transport`` from ``.kittify/config.yaml`` if present."""
    config_path = project_dir / ".kittify" / "config.yaml"
    if not config_path.exists():
        return None
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:  # pragma: no cover - yaml is a runtime dep
        return None
    try:
        with config_path.open(encoding="utf-8") as fp:
            doc = yaml.safe_load(fp) or {}
    except Exception:  # pragma: no cover - defensive
        return None
    dashboard_section = doc.get("dashboard") if isinstance(doc, dict) else None
    if not isinstance(dashboard_section, dict):
        return None
    transport = dashboard_section.get("transport")
    return transport if isinstance(transport, str) else None


def run_dashboard_server(
    project_dir: Path,
    port: int,
    project_token: str | None,
    transport: Transport | None = None,
) -> None:
    """Run the dashboard server forever (used by detached child processes).

    The ``transport`` argument is resolved via :func:`resolve_transport` if
    not provided explicitly. Pass ``"legacy"`` to force the historical
    BaseHTTPServer path; pass ``"fastapi"`` to force the new transport.
    """
    try:
        from specify_cli.sync.daemon import DaemonIntent, ensure_sync_daemon_running

        # Dashboard reads local state from DAEMON_STATE_FILE; it does not need
        # the sync daemon to boot just because the dashboard process started.
        outcome = ensure_sync_daemon_running(intent=DaemonIntent.LOCAL_ONLY)
        logger.debug("Sync daemon startup skipped: %s", outcome.skipped_reason)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Global sync daemon check failed: %s", exc)

    resolved_transport = transport if transport is not None else resolve_transport(project_dir)

    if resolved_transport == "fastapi":
        _run_fastapi(project_dir, port, project_token)
        return

    handler_class = _build_handler_class(project_dir, project_token)
    server = HTTPServer(('127.0.0.1', port), handler_class)
    server.serve_forever()


def _run_fastapi(project_dir: Path, port: int, project_token: str | None) -> None:
    """Boot the FastAPI app via Uvicorn.

    Stashes the running ``uvicorn.Server`` instance on ``app.state`` so
    ``POST /api/shutdown`` can flip ``server.should_exit = True`` to
    actually terminate the ASGI server (parity with the legacy stack's
    ``server.shutdown()`` path).
    """
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - import is a hard dep
        raise RuntimeError(
            "FastAPI transport requested but uvicorn is not installed. "
            "Run `uv sync --frozen` to install pinned dependencies."
        ) from exc

    from dashboard.api import create_app  # noqa: WPS433 — local import keeps legacy path import-free

    app = create_app(project_dir=project_dir, project_token=project_token)
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level=os.environ.get("SPEC_KITTY_DASHBOARD_LOG_LEVEL", "warning"),
        access_log=False,
    )
    server = uvicorn.Server(config)
    # Stash on app.state so the /api/shutdown route can flip should_exit
    # and actually terminate the ASGI loop (parity with legacy stack).
    app.state.uvicorn_server = server
    server.run()


def _background_script(
    project_dir: Path,
    port: int,
    project_token: str | None,
    transport: Transport | None = None,
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
        run_dashboard_server(
            Path({repr(str(project_dir))}),
            {port},
            {repr(project_token)},
            transport={repr(transport)},
        )
        """
    )


def start_dashboard(
    project_dir: Path,
    port: int | None = None,
    background_process: bool = False,
    project_token: str | None = None,
    transport: Transport | None = None,
) -> tuple[int, int | None]:
    """
    Start the dashboard server.

    Returns tuple(port, pid). When background_process=True, pid is the process ID
    of the detached child process. When background_process=False, pid is None.

    Args:
        project_dir: Path to the project directory
        port: Port number (auto-selected if None)
        background_process: If True, run as detached subprocess; if False, run in thread
        project_token: Security token for the dashboard
        transport: Override for the active transport ("legacy" or "fastapi");
            when None, resolved via .kittify/config.yaml or DEFAULT_TRANSPORT.

    Returns:
        Tuple[port, pid]: Port number and process ID (None if threaded mode)
    """
    if port is None:
        port = find_free_port()

    project_dir_abs = project_dir.resolve()
    resolved_transport = transport if transport is not None else resolve_transport(project_dir_abs)

    if background_process:
        script = _background_script(project_dir_abs, port, project_token, resolved_transport)
        proc = subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return port, proc.pid

    if resolved_transport == "fastapi":
        thread = threading.Thread(
            target=_run_fastapi,
            args=(project_dir_abs, port, project_token),
            daemon=True,
        )
        thread.start()
        return port, None

    handler_class = _build_handler_class(project_dir_abs, project_token)
    server = HTTPServer(('127.0.0.1', port), handler_class)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return port, None
