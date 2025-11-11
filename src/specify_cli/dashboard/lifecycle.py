"""Dashboard lifecycle and health management utilities."""

from __future__ import annotations

import json
import secrets
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from .server import find_free_port, start_dashboard

__all__ = [
    "ensure_dashboard_running",
    "stop_dashboard",
    "_parse_dashboard_file",
    "_write_dashboard_file",
    "_check_dashboard_health",
]


def _parse_dashboard_file(dashboard_file: Path) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Read dashboard metadata from disk."""
    try:
        content = dashboard_file.read_text(encoding='utf-8')
    except Exception:
        return None, None, None

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return None, None, None

    url = lines[0] if lines else None
    port = None
    token = None

    if len(lines) >= 2:
        try:
            port = int(lines[1])
        except ValueError:
            port = None

    if len(lines) >= 3:
        token = lines[2] or None

    return url, port, token


def _write_dashboard_file(dashboard_file: Path, url: str, port: int, token: Optional[str]) -> None:
    """Persist dashboard metadata to disk."""
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [url, str(port)]
    if token:
        lines.append(token)
    dashboard_file.write_text("\n".join(lines) + "\n", encoding='utf-8')


def _check_dashboard_health(
    port: int,
    project_dir: Path,
    expected_token: Optional[str],
    timeout: float = 0.5,
) -> bool:
    """Verify that the dashboard on the port belongs to the provided project."""
    health_url = f"http://127.0.0.1:{port}/api/health"
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, socket.error):
        return False
    except Exception:
        return False

    try:
        data = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False

    remote_path = data.get('project_path')
    if not remote_path:
        return False

    try:
        remote_resolved = str(Path(remote_path).resolve())
    except Exception:
        remote_resolved = str(remote_path)

    try:
        expected_path = str(project_dir.resolve())
    except Exception:
        expected_path = str(project_dir)

    if remote_resolved != expected_path:
        return False

    remote_token = data.get('token')
    if expected_token:
        return remote_token == expected_token

    return True


def ensure_dashboard_running(
    project_dir: Path,
    preferred_port: Optional[int] = None,
    background_process: bool = True,
) -> Tuple[str, int, bool]:
    """
    Ensure a dashboard server is running for the provided project directory.

    Returns:
        Tuple of (url, port, started) where started is True when a new server was launched.
    """
    project_dir_resolved = project_dir.resolve()
    dashboard_file = project_dir_resolved / '.kittify' / '.dashboard'

    existing_url = None
    existing_port = None
    existing_token = None

    if dashboard_file.exists():
        existing_url, existing_port, existing_token = _parse_dashboard_file(dashboard_file)
        if existing_port is not None and _check_dashboard_health(existing_port, project_dir_resolved, existing_token):
            url = existing_url or f"http://127.0.0.1:{existing_port}"
            return url, existing_port, False

    if preferred_port is not None:
        try:
            port_to_use = find_free_port(preferred_port, max_attempts=1)
        except RuntimeError:
            port_to_use = None
    else:
        port_to_use = None

    token = secrets.token_hex(16)
    port, _ = start_dashboard(
        project_dir_resolved,
        port=port_to_use,
        background_process=background_process,
        project_token=token,
    )
    url = f"http://127.0.0.1:{port}"

    for _ in range(40):
        if _check_dashboard_health(port, project_dir_resolved, token):
            _write_dashboard_file(dashboard_file, url, port, token)
            return url, port, True
        time.sleep(0.25)

    raise RuntimeError(f"Dashboard failed to start on port {port} for project {project_dir_resolved}")


def stop_dashboard(project_dir: Path, timeout: float = 5.0) -> Tuple[bool, str]:
    """
    Attempt to stop the dashboard server for the provided project directory.

    Returns:
        Tuple[bool, str]: (stopped, message)
    """
    project_dir_resolved = project_dir.resolve()
    dashboard_file = project_dir_resolved / '.kittify' / '.dashboard'

    if not dashboard_file.exists():
        return False, "No dashboard metadata found."

    _, port, token = _parse_dashboard_file(dashboard_file)
    if port is None:
        dashboard_file.unlink(missing_ok=True)
        return False, "Dashboard metadata was invalid and has been cleared."

    if not _check_dashboard_health(port, project_dir_resolved, token):
        dashboard_file.unlink(missing_ok=True)
        return False, "Dashboard was already stopped. Metadata has been cleared."

    shutdown_url = f"http://127.0.0.1:{port}/api/shutdown"

    def _attempt_get() -> Tuple[bool, Optional[str]]:
        params = {}
        if token:
            params['token'] = token
        query = urllib.parse.urlencode(params)
        request_url = f"{shutdown_url}?{query}" if query else shutdown_url
        try:
            urllib.request.urlopen(request_url, timeout=1)
            return True, None
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                return False, "Dashboard refused shutdown (token mismatch)."
            if exc.code in (404, 405, 501):
                return False, None
            return False, f"Dashboard shutdown failed with HTTP {exc.code}."
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.error) as exc:
            return False, f"Dashboard shutdown request failed: {exc}"
        except Exception as exc:
            return False, f"Unexpected error during shutdown: {exc}"

    def _attempt_post() -> Tuple[bool, Optional[str]]:
        payload = json.dumps({'token': token}).encode('utf-8')
        request = urllib.request.Request(
            shutdown_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            urllib.request.urlopen(request, timeout=1)
            return True, None
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                return False, "Dashboard refused shutdown (token mismatch)."
            if exc.code == 501:
                return False, "Dashboard does not support remote shutdown (upgrade required)."
            return False, f"Dashboard shutdown failed with HTTP {exc.code}."
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.error) as exc:
            return False, f"Dashboard shutdown request failed: {exc}"
        except Exception as exc:
            return False, f"Unexpected error during shutdown: {exc}"

    ok, error_message = _attempt_get()
    if not ok and error_message is None:
        ok, error_message = _attempt_post()
    if not ok:
        return False, error_message or "Dashboard shutdown failed."

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _check_dashboard_health(port, project_dir_resolved, token):
            dashboard_file.unlink(missing_ok=True)
            return True, f"Dashboard stopped and metadata cleared (port {port})."
        time.sleep(0.1)

    return False, f"Dashboard did not stop within {timeout} seconds."
