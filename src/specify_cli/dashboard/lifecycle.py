"""Dashboard lifecycle and health management utilities."""

from __future__ import annotations

import json
import os
import secrets
import signal
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


def _parse_dashboard_file(dashboard_file: Path) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[int]]:
    """Read dashboard metadata from disk.

    Format:
        Line 1: URL (http://127.0.0.1:port)
        Line 2: Port (integer)
        Line 3: Token (optional)
        Line 4: PID (optional, for process tracking)
    """
    try:
        content = dashboard_file.read_text(encoding='utf-8')
    except Exception:
        return None, None, None, None

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return None, None, None, None

    url = lines[0] if lines else None
    port = None
    token = None
    pid = None

    if len(lines) >= 2:
        try:
            port = int(lines[1])
        except ValueError:
            port = None

    if len(lines) >= 3:
        token = lines[2] or None

    if len(lines) >= 4:
        try:
            pid = int(lines[3])
        except ValueError:
            pid = None

    return url, port, token, pid


def _write_dashboard_file(
    dashboard_file: Path,
    url: str,
    port: int,
    token: Optional[str],
    pid: Optional[int] = None,
) -> None:
    """Persist dashboard metadata to disk.

    Args:
        dashboard_file: Path to .dashboard metadata file
        url: Dashboard URL (http://127.0.0.1:port)
        port: Port number
        token: Security token (optional)
        pid: Process ID of background dashboard (optional)
    """
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [url, str(port)]
    if token:
        lines.append(token)
    if pid is not None:
        lines.append(str(pid))
    dashboard_file.write_text("\n".join(lines) + "\n", encoding='utf-8')


def _is_process_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive.

    Uses signal.SIGZERO to check existence without actually sending a signal.
    """
    try:
        os.kill(pid, 0)  # 0 doesn't kill, just checks if process exists
        return True
    except ProcessLookupError:
        # Process doesn't exist
        return False
    except PermissionError:
        # Process exists but we don't have permission to signal it (assume alive)
        return True
    except Exception:
        # Assume it's alive if we can't determine
        return True


def _is_spec_kitty_dashboard(port: int, timeout: float = 0.3) -> bool:
    """Check if the process on the given port is a spec-kitty dashboard.

    Uses health check endpoint fingerprinting to safely identify spec-kitty dashboards.
    Only returns True if we can confirm it's a spec-kitty dashboard.

    Args:
        port: Port number to check
        timeout: Health check timeout in seconds

    Returns:
        True if confirmed to be a spec-kitty dashboard, False otherwise
    """
    health_url = f"http://127.0.0.1:{port}/api/health"
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = response.read()
    except Exception:
        # Can't reach or parse - not a spec-kitty dashboard (or dead)
        return False

    try:
        data = json.loads(payload.decode('utf-8'))
        # Verify this is actually a spec-kitty dashboard by checking for expected fields
        return 'project_path' in data and 'status' in data
    except Exception:
        return False


def _cleanup_orphaned_dashboards_in_range(start_port: int = 9237, port_count: int = 100) -> int:
    """Clean up orphaned spec-kitty dashboard processes in the port range.

    This function safely identifies spec-kitty dashboard processes via health check
    fingerprinting and kills only confirmed spec-kitty processes. This handles orphans
    that have no .dashboard file (e.g., from failed startups or deleted temp projects).

    Args:
        start_port: Starting port number (default: 9237)
        port_count: Number of ports to check (default: 100)

    Returns:
        Number of orphaned processes killed
    """
    import subprocess

    killed_count = 0

    for port in range(start_port, start_port + port_count):
        # Check if port is occupied
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)
                if sock.connect_ex(('127.0.0.1', port)) != 0:
                    # Port is free, skip
                    continue
        except Exception:
            continue

        # Port is occupied - check if it's a spec-kitty dashboard
        if _is_spec_kitty_dashboard(port):
            # It's a spec-kitty dashboard - try to find and kill the process
            try:
                # Use lsof to find PID listening on this port
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}', '-sTCP:LISTEN'],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid.strip()]
                    for pid in pids:
                        try:
                            os.kill(pid, signal.SIGKILL)
                            killed_count += 1
                        except (ProcessLookupError, PermissionError):
                            pass
            except Exception:
                # Can't use lsof or failed to kill - skip this port
                pass

    return killed_count


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

    This function:
    1. Checks if a dashboard is already running (health check)
    2. Cleans up this project's orphaned process if stored PID is dead
    3. If starting new dashboard fails due to port exhaustion, cleans up orphaned
       spec-kitty dashboards across the entire port range and retries
    4. Starts a new dashboard if needed
    5. Stores the PID for future cleanup

    Returns:
        Tuple of (url, port, started) where started is True when a new server was launched.
    """
    project_dir_resolved = project_dir.resolve()
    dashboard_file = project_dir_resolved / '.kittify' / '.dashboard'

    existing_url = None
    existing_port = None
    existing_token = None
    existing_pid = None

    # STEP 1: Check if we have a stale .dashboard file from a dead process
    if dashboard_file.exists():
        existing_url, existing_port, existing_token, existing_pid = _parse_dashboard_file(dashboard_file)

        # First, try health check - if dashboard is healthy, reuse it
        if existing_port is not None and _check_dashboard_health(existing_port, project_dir_resolved, existing_token):
            url = existing_url or f"http://127.0.0.1:{existing_port}"
            return url, existing_port, False

        # Dashboard not responding - clean up orphaned process if we have a PID
        if existing_pid is not None and not _is_process_alive(existing_pid):
            # Process is dead, clean up the metadata file
            dashboard_file.unlink(missing_ok=True)
        elif existing_pid is not None and existing_port is not None:
            # PID is alive but port not responding - kill the orphan
            try:
                os.kill(existing_pid, signal.SIGKILL)
                dashboard_file.unlink(missing_ok=True)
            except (ProcessLookupError, PermissionError):
                # Already dead or can't kill - just clean up metadata
                dashboard_file.unlink(missing_ok=True)
        else:
            # No PID recorded - just clean up metadata file
            dashboard_file.unlink(missing_ok=True)

    # STEP 2: Try to start a new dashboard
    if preferred_port is not None:
        try:
            port_to_use = find_free_port(preferred_port, max_attempts=1)
        except RuntimeError:
            port_to_use = None
    else:
        port_to_use = None

    token = secrets.token_hex(16)

    # Try starting dashboard - if it fails due to port exhaustion, cleanup and retry
    try:
        port, pid = start_dashboard(
            project_dir_resolved,
            port=port_to_use,
            background_process=background_process,
            project_token=token,
        )
    except RuntimeError as e:
        # If port exhaustion, try cleaning up orphaned dashboards and retry once
        if "Could not find free port" in str(e):
            killed = _cleanup_orphaned_dashboards_in_range()
            if killed > 0:
                # Cleanup succeeded, retry starting dashboard
                port, pid = start_dashboard(
                    project_dir_resolved,
                    port=port_to_use,
                    background_process=background_process,
                    project_token=token,
                )
            else:
                # No orphans found or couldn't clean up - re-raise original error
                raise
        else:
            # Different error - re-raise
            raise

    url = f"http://127.0.0.1:{port}"

    # Wait for dashboard to become healthy (20 seconds with exponential backoff)
    # Start with quick checks, then slow down for slower systems
    retry_delays = [0.1] * 10 + [0.25] * 40 + [0.5] * 20  # ~20 seconds total
    for delay in retry_delays:
        if _check_dashboard_health(port, project_dir_resolved, token):
            _write_dashboard_file(dashboard_file, url, port, token, pid)
            return url, port, True
        time.sleep(delay)

    # Dashboard started but never became healthy
    # Check if port has an orphaned dashboard from a different project
    if _is_spec_kitty_dashboard(port):
        # Port has a spec-kitty dashboard but for wrong project - orphan detected
        # Clean up the failed process we just started
        if pid is not None:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

        # Cleanup orphaned dashboards and retry ONCE
        killed = _cleanup_orphaned_dashboards_in_range()
        if killed > 0:
            # Retry starting dashboard after cleanup
            token = secrets.token_hex(16)
            port, pid = start_dashboard(
                project_dir_resolved,
                port=port_to_use,
                background_process=background_process,
                project_token=token,
            )
            url = f"http://127.0.0.1:{port}"

            # Wait for health check again
            for delay in retry_delays:
                if _check_dashboard_health(port, project_dir_resolved, token):
                    _write_dashboard_file(dashboard_file, url, port, token, pid)
                    return url, port, True
                time.sleep(delay)

    # Still failed - clean up and raise error
    if pid is not None:
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    raise RuntimeError(f"Dashboard failed to start on port {port} for project {project_dir_resolved}")


def stop_dashboard(project_dir: Path, timeout: float = 5.0) -> Tuple[bool, str]:
    """
    Attempt to stop the dashboard server for the provided project directory.

    Tries graceful HTTP shutdown first, then falls back to killing by PID if needed.

    Returns:
        Tuple[bool, str]: (stopped, message)
    """
    project_dir_resolved = project_dir.resolve()
    dashboard_file = project_dir_resolved / '.kittify' / '.dashboard'

    if not dashboard_file.exists():
        return False, "No dashboard metadata found."

    _, port, token, pid = _parse_dashboard_file(dashboard_file)
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

    # Try graceful HTTP shutdown first
    ok, error_message = _attempt_get()
    if not ok and error_message is None:
        ok, error_message = _attempt_post()

    # If HTTP shutdown failed but we have a PID, try killing the process
    if not ok and pid is not None:
        try:
            os.kill(pid, signal.SIGTERM)  # Try graceful termination first
            time.sleep(0.5)

            # Check if process died
            if _is_process_alive(pid):
                # Still alive, force kill
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.2)

            dashboard_file.unlink(missing_ok=True)
            return True, f"Dashboard stopped via process kill (PID {pid})."

        except ProcessLookupError:
            # Process doesn't exist anymore
            dashboard_file.unlink(missing_ok=True)
            return True, f"Dashboard was already dead (PID {pid})."
        except PermissionError:
            return False, f"Permission denied to kill dashboard process (PID {pid})."
        except Exception as e:
            return False, f"Failed to kill dashboard process (PID {pid}): {e}"

    if not ok:
        return False, error_message or "Dashboard shutdown failed."

    # Wait for graceful shutdown to complete
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _check_dashboard_health(port, project_dir_resolved, token):
            dashboard_file.unlink(missing_ok=True)
            return True, f"Dashboard stopped and metadata cleared (port {port})."
        time.sleep(0.1)

    # Timeout - try killing by PID as last resort
    if pid is not None:
        try:
            os.kill(pid, signal.SIGKILL)
            dashboard_file.unlink(missing_ok=True)
            return True, f"Dashboard forced stopped (SIGKILL, PID {pid}) after {timeout}s timeout."
        except Exception:
            pass

    return False, f"Dashboard did not stop within {timeout} seconds."
