"""Machine-global sync daemon lifecycle and localhost control plane."""

from __future__ import annotations

import json
import logging
import secrets
import socket
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional, Tuple

import psutil

from specify_cli.core.atomic import atomic_write

logger = logging.getLogger(__name__)

SPEC_KITTY_DIR = Path.home() / ".spec-kitty"
DAEMON_STATE_FILE = SPEC_KITTY_DIR / "sync-daemon"


@dataclass(frozen=True)
class SyncDaemonStatus:
    """Observed state of the machine-global sync daemon."""

    healthy: bool
    url: Optional[str] = None
    port: Optional[int] = None
    token: Optional[str] = None
    pid: Optional[int] = None
    sync_running: bool = False
    last_sync: Optional[str] = None
    consecutive_failures: int = 0
    websocket_status: str = "Offline"


def _parse_daemon_file(path: Path) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[int]]:
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return None, None, None, None

    if not lines:
        return None, None, None, None

    url = lines[0]
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


def _write_daemon_file(path: Path, url: str, port: int, token: Optional[str], pid: Optional[int]) -> None:
    lines = [url, str(port)]
    if token:
        lines.append(token)
    if pid is not None:
        lines.append(str(pid))
    atomic_write(path, "\n".join(lines) + "\n", mkdir=True)


def _is_process_alive(pid: int) -> bool:
    try:
        proc = psutil.Process(pid)
        return proc.is_running()
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        return True
    except Exception:
        return False


def _find_free_port(start_port: int = 9248, max_attempts: int = 50) -> int:
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

    raise RuntimeError(f"Could not find free sync daemon port in range {start_port}-{start_port + max_attempts}")


def _fetch_health_payload(health_url: str, timeout: float = 0.5) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, socket.error):
        return None
    except Exception:
        return None

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def _check_sync_daemon_health(port: int, expected_token: Optional[str], timeout: float = 0.5) -> bool:
    data = _fetch_health_payload(f"http://127.0.0.1:{port}/api/health", timeout=timeout)
    if not data:
        return False
    if data.get("status") != "ok":
        return False
    remote_token = data.get("token")
    if expected_token:
        return remote_token == expected_token
    return True


class SyncDaemonHandler(BaseHTTPRequestHandler):
    """Localhost-only HTTP control plane for the machine-global sync daemon."""

    daemon_token: Optional[str] = None

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        del format, args

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length") or 0)
        if content_length <= 0:
            return {}
        body = self.rfile.read(content_length)
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    def _extract_token(self) -> Optional[str]:
        if self.command == "POST":
            try:
                payload = self._read_json_body()
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "invalid_payload"})
                return None
            self._cached_payload = payload
            token = payload.get("token")
            return str(token) if token else None

        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)
        values = params.get("token")
        return values[0] if values else None

    def _require_token(self) -> dict[str, Any] | None:
        expected = getattr(self, "daemon_token", None)
        token = self._extract_token()
        if expected and token != expected:
            self._send_json(403, {"error": "invalid_token"})
            return None
        return getattr(self, "_cached_payload", {})

    def do_GET(self) -> None:  # noqa: N802
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/api/health":
            self.handle_health()
            return
        if parsed_path.path == "/api/sync/trigger":
            self.handle_sync_trigger()
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/api/sync/trigger":
            self.handle_sync_trigger()
            return
        if parsed_path.path == "/api/sync/publish":
            self.handle_sync_publish()
            return
        if parsed_path.path == "/api/shutdown":
            self.handle_shutdown()
            return
        self.send_response(404)
        self.end_headers()

    def handle_health(self) -> None:
        from specify_cli.sync.runtime import get_runtime

        runtime = get_runtime()
        sync = runtime.background_service
        self._send_json(
            200,
            {
                "status": "ok",
                "token": getattr(self, "daemon_token", None),
                "sync": {
                    "running": bool(sync and sync.is_running),
                    "last_sync": sync.last_sync.isoformat() if sync and sync.last_sync else None,
                    "consecutive_failures": sync.consecutive_failures if sync else 0,
                },
                "websocket_status": runtime.get_websocket_status(),
            },
        )

    def handle_sync_trigger(self) -> None:
        if self._require_token() is None:
            return

        from specify_cli.sync.runtime import get_runtime

        runtime = get_runtime()
        if runtime.background_service is None:
            self._send_json(503, {"error": "sync_unavailable"})
            return
        runtime.background_service.wake()
        self._send_json(202, {"status": "scheduled"})

    def handle_sync_publish(self) -> None:
        payload = self._require_token()
        if payload is None:
            return

        raw_event = payload.get("event")
        if not isinstance(raw_event, dict):
            self._send_json(400, {"error": "invalid_event"})
            return

        from specify_cli.sync.runtime import get_runtime

        runtime = get_runtime()
        published = runtime.publish_event(raw_event)
        if runtime.background_service is not None:
            runtime.background_service.wake()
        if published:
            self._send_json(200, {"status": "published"})
            return
        self._send_json(202, {"status": "queued"})

    def handle_shutdown(self) -> None:
        if self._require_token() is None:
            return

        self._send_json(200, {"status": "stopping"})

        def shutdown_server(server: HTTPServer) -> None:
            time.sleep(0.05)
            server.shutdown()

        threading.Thread(target=shutdown_server, args=(self.server,), daemon=True).start()


def run_sync_daemon(port: int, daemon_token: Optional[str]) -> None:
    """Run the machine-global sync daemon forever."""
    from specify_cli.sync.runtime import get_runtime

    get_runtime()
    handler_class = type(
        "SyncDaemonRouter",
        (SyncDaemonHandler,),
        {"daemon_token": daemon_token},
    )
    server = HTTPServer(("127.0.0.1", port), handler_class)
    server.serve_forever()


def _background_script(port: int, daemon_token: Optional[str]) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return textwrap.dedent(
        f"""
        import sys
        from pathlib import Path
        repo_root = Path({repr(str(repo_root))})
        sys.path.insert(0, str(repo_root))
        from specify_cli.sync.daemon import run_sync_daemon
        run_sync_daemon({port}, {repr(daemon_token)})
        """
    )


def get_sync_daemon_status(timeout: float = 0.5) -> SyncDaemonStatus:
    """Return health and sync metadata for the machine-global daemon."""
    if not DAEMON_STATE_FILE.exists():
        return SyncDaemonStatus(healthy=False)

    url, port, token, pid = _parse_daemon_file(DAEMON_STATE_FILE)
    if port is None:
        return SyncDaemonStatus(healthy=False, url=url, token=token, pid=pid)

    data = _fetch_health_payload(f"http://127.0.0.1:{port}/api/health", timeout=timeout)
    if not data:
        return SyncDaemonStatus(
            healthy=False,
            url=url or f"http://127.0.0.1:{port}",
            port=port,
            token=token,
            pid=pid,
        )

    healthy = data.get("status") == "ok"
    if healthy and token:
        healthy = data.get("token") == token

    sync_data = data.get("sync") if isinstance(data.get("sync"), dict) else {}
    websocket_status = str(data.get("websocket_status") or "Offline")
    return SyncDaemonStatus(
        healthy=healthy,
        url=url or f"http://127.0.0.1:{port}",
        port=port,
        token=token,
        pid=pid,
        sync_running=bool(sync_data.get("running")),
        last_sync=str(sync_data.get("last_sync")) if sync_data.get("last_sync") else None,
        consecutive_failures=int(sync_data.get("consecutive_failures") or 0),
        websocket_status=websocket_status,
    )


def ensure_sync_daemon_running(preferred_port: Optional[int] = None) -> Tuple[str, int, bool]:
    """Ensure the machine-global sync daemon is running."""
    existing_url = None
    existing_port = None
    existing_token = None
    existing_pid = None

    if DAEMON_STATE_FILE.exists():
        existing_url, existing_port, existing_token, existing_pid = _parse_daemon_file(DAEMON_STATE_FILE)
        if existing_port is not None and _check_sync_daemon_health(existing_port, existing_token):
            return existing_url or f"http://127.0.0.1:{existing_port}", existing_port, False
        if existing_pid is not None and not _is_process_alive(existing_pid):
            DAEMON_STATE_FILE.unlink(missing_ok=True)
        elif existing_pid is not None:
            try:
                psutil.Process(existing_pid).kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            DAEMON_STATE_FILE.unlink(missing_ok=True)
        else:
            DAEMON_STATE_FILE.unlink(missing_ok=True)

    if preferred_port is not None:
        port = preferred_port
    else:
        port = _find_free_port()
    token = secrets.token_hex(16)
    proc = subprocess.Popen(
        [sys.executable, "-c", _background_script(port, token)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    url = f"http://127.0.0.1:{port}"

    retry_delays = [0.1] * 10 + [0.25] * 20
    for delay in retry_delays:
        if _check_sync_daemon_health(port, token):
            _write_daemon_file(DAEMON_STATE_FILE, url, port, token, proc.pid)
            return url, port, True
        time.sleep(delay)

    if _is_process_alive(proc.pid):
        _write_daemon_file(DAEMON_STATE_FILE, url, port, token, proc.pid)
        return url, port, True

    raise RuntimeError(f"Sync daemon failed to start on port {port}")


def stop_sync_daemon(timeout: float = 5.0) -> Tuple[bool, str]:
    """Stop the machine-global sync daemon."""
    if not DAEMON_STATE_FILE.exists():
        return False, "No sync daemon metadata found."

    url, port, token, pid = _parse_daemon_file(DAEMON_STATE_FILE)
    if port is None:
        DAEMON_STATE_FILE.unlink(missing_ok=True)
        return False, "Sync daemon metadata was invalid and has been cleared."

    if not _check_sync_daemon_health(port, token):
        DAEMON_STATE_FILE.unlink(missing_ok=True)
        return False, "Sync daemon was already stopped. Metadata has been cleared."

    request = urllib.request.Request(
        f"{url}/api/shutdown",
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=1.0):
            pass
    except Exception:
        pass

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _check_sync_daemon_health(port, token, timeout=0.2):
            DAEMON_STATE_FILE.unlink(missing_ok=True)
            return True, "Sync daemon stopped."
        time.sleep(0.05)

    if pid is not None:
        try:
            psutil.Process(pid).kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    DAEMON_STATE_FILE.unlink(missing_ok=True)
    return True, "Sync daemon stopped."
