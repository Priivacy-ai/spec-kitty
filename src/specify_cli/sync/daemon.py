"""Machine-global sync daemon lifecycle and localhost control plane."""

from __future__ import annotations

import errno
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
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Tuple

if sys.platform == "win32":
    import msvcrt
else:  # pragma: no cover - platform-specific
    import fcntl

if TYPE_CHECKING:
    from specify_cli.sync.config import SyncConfig

import psutil

from specify_cli.core.atomic import atomic_write

logger = logging.getLogger(__name__)


def _sync_root() -> Path:
    """Return the sync state directory for the current platform.

    On Windows: resolves to ``%LOCALAPPDATA%\\spec-kitty\\sync\\``
    via the unified RuntimeRoot.
    On POSIX: returns ``~/.spec-kitty/sync`` unchanged (preserving existing behavior).
    """
    if sys.platform == "win32":
        from specify_cli.paths import get_runtime_root  # noqa: PLC0415
        return get_runtime_root().sync_dir
    return Path.home() / ".spec-kitty" / "sync"


def _daemon_root() -> Path:
    """Return the daemon state directory for the current platform.

    On Windows: resolves to ``%LOCALAPPDATA%\\spec-kitty\\daemon\\``
    via the unified RuntimeRoot.
    On POSIX: returns ``~/.spec-kitty`` unchanged (state files live directly
    under ~/.spec-kitty on POSIX, preserving existing behavior).
    """
    if sys.platform == "win32":
        from specify_cli.paths import get_runtime_root  # noqa: PLC0415
        return get_runtime_root().daemon_dir
    return Path.home() / ".spec-kitty"


# Module-level path constants derived from platform-aware helpers so that
# existing code referencing these names continues to work unchanged.
SPEC_KITTY_DIR = Path.home() / ".spec-kitty"
DAEMON_STATE_FILE = _daemon_root() / "sync-daemon"
DAEMON_LOG_FILE = _daemon_root() / "sync-daemon.log"
DAEMON_LOCK_FILE = _daemon_root() / "sync-daemon.lock"


class DaemonIntent(str, Enum):
    """Caller intent for daemon startup — LOCAL_ONLY suppresses auto-start."""

    LOCAL_ONLY = "local_only"
    REMOTE_REQUIRED = "remote_required"


@dataclass(frozen=True)
class DaemonStartOutcome:
    """Structured result from ensure_sync_daemon_running()."""

    started: bool
    skipped_reason: str | None
    pid: int | None

# Port range for the sync daemon — well above the dashboard range (9237-9337)
# to prevent overlap.
DAEMON_PORT_START = 9400
DAEMON_PORT_MAX_ATTEMPTS = 50

# Protocol version — bumped when the daemon's control-plane API or internal
# behaviour changes in a backwards-incompatible way.  ensure_sync_daemon_running
# compares this against the running daemon and restarts it on mismatch.
DAEMON_PROTOCOL_VERSION = 1


def _is_daemon_lock_contention(exc: OSError) -> bool:
    """Return True when a non-blocking lock failed due to normal contention."""
    if isinstance(exc, BlockingIOError):
        return True

    if exc.errno is None:
        return False

    if sys.platform == "win32":
        return exc.errno in {errno.EACCES, errno.EDEADLK}

    # Python documents flock(LOCK_NB) contention as EACCES or EAGAIN,
    # depending on the platform's backend.
    return exc.errno in {errno.EACCES, errno.EAGAIN}


def _get_package_version() -> str:
    """Return the installed specify_cli version string."""
    try:
        from importlib.metadata import version

        return version("specify-cli")
    except Exception:
        return "unknown"


@dataclass(frozen=True)
class SyncDaemonStatus:
    """Observed state of the machine-global sync daemon."""

    healthy: bool
    url: str | None = None
    port: int | None = None
    token: str | None = None
    pid: int | None = None
    sync_running: bool = False
    last_sync: str | None = None
    consecutive_failures: int = 0
    websocket_status: str = "Offline"
    protocol_version: int | None = None
    package_version: str | None = None


def _parse_daemon_file(path: Path) -> tuple[str | None, int | None, str | None, int | None]:
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


def _write_daemon_file(path: Path, url: str, port: int, token: str | None, pid: int | None) -> None:
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


def _find_free_port(start_port: int = DAEMON_PORT_START, max_attempts: int = DAEMON_PORT_MAX_ATTEMPTS) -> int:
    """Find an available port, returning the bound socket alongside the port.

    Uses connect-check then bind-check.  The socket is closed before return
    (the daemon will re-bind it), but the window is very small compared to
    the previous implementation because we no longer do a separate test-bind
    then release cycle.
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

    raise RuntimeError(f"Could not find free sync daemon port in range {start_port}-{start_port + max_attempts}")


def _fetch_health_payload(health_url: str, timeout: float = 0.5) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:  # nosec B310 — health_url is always http://127.0.0.1:<port>/api/health
            if response.status != 200:
                return None
            payload = response.read()
    except Exception:
        return None

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def _check_sync_daemon_health(port: int, expected_token: str | None, timeout: float = 0.5) -> bool:
    data = _fetch_health_payload(f"http://127.0.0.1:{port}/api/health", timeout=timeout)
    if not data:
        return False
    if data.get("status") != "ok":
        return False
    remote_token = data.get("token")
    if expected_token:
        return remote_token == expected_token
    return True


def _daemon_version_matches(port: int, expected_token: str | None, timeout: float = 0.5) -> bool:
    """Return True if the running daemon reports the current protocol + package version."""
    data = _fetch_health_payload(f"http://127.0.0.1:{port}/api/health", timeout=timeout)
    if not data:
        return False
    if data.get("status") != "ok":
        return False
    if expected_token:
        if data.get("token") != expected_token:
            return False
    remote_proto = data.get("protocol_version")
    remote_pkg = data.get("package_version")
    if remote_proto != DAEMON_PROTOCOL_VERSION:
        return False
    if remote_pkg != _get_package_version():
        return False
    return True


# ---------------------------------------------------------------------------
# HTTP control plane
# ---------------------------------------------------------------------------

_SENTINEL_BAD_TOKEN = object()


class SyncDaemonHandler(BaseHTTPRequestHandler):
    """Localhost-only HTTP control plane for the machine-global sync daemon."""

    daemon_token: str | None = None

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
        return dict(json.loads(body.decode("utf-8")))

    def _extract_token_from_query(self) -> str | None:
        """Extract token from query string (for GET requests)."""
        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)
        values = params.get("token")
        return values[0] if values else None

    def _require_token(self) -> dict[str, Any] | None:
        """Authenticate the request and return the parsed JSON body.

        For POST requests the token is read from the JSON body.
        For GET requests the token is read from the query string.
        Returns None (and sends an error response) on auth failure or
        malformed JSON.
        """
        expected = getattr(self, "daemon_token", None)

        if self.command == "POST":
            try:
                payload = self._read_json_body()
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "invalid_payload"})
                return None
            token = payload.get("token")
            token = str(token) if token else None
        else:
            payload = {}
            token = self._extract_token_from_query()

        if expected and token != expected:
            self._send_json(403, {"error": "invalid_token"})
            return None

        return payload

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
                "protocol_version": DAEMON_PROTOCOL_VERSION,
                "package_version": _get_package_version(),
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


def run_sync_daemon(port: int, daemon_token: str | None) -> None:
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


def _background_script(port: int, daemon_token: str | None) -> str:
    """Generate the Python script executed by the daemon subprocess.

    Uses ``-m`` style import so the installed package is found via normal
    ``sys.path`` resolution rather than hard-coding a repo checkout path.
    """
    return textwrap.dedent(
        f"""\
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

    sync_data: dict[str, object] = data.get("sync") if isinstance(data.get("sync"), dict) else {}
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
        protocol_version=data.get("protocol_version"),
        package_version=data.get("package_version"),
    )


def _kill_and_cleanup(pid: int | None) -> None:
    """Best-effort kill a daemon process and remove the state file."""
    if pid is not None:
        try:
            psutil.Process(pid).kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    DAEMON_STATE_FILE.unlink(missing_ok=True)


def ensure_sync_daemon_running(
    *,
    intent: DaemonIntent,
    config: SyncConfig | None = None,
) -> DaemonStartOutcome:
    """Ensure the machine-global sync daemon is running.

    This function is intent-gated: callers must declare whether they require
    remote sync (``REMOTE_REQUIRED``) or only read local state (``LOCAL_ONLY``).
    The ``intent`` parameter is keyword-only and mandatory.

    Decision matrix (first match wins):
    1. Rollout disabled → skipped_reason="rollout_disabled"
    2. intent == LOCAL_ONLY → skipped_reason="intent_local_only"
    3. policy == MANUAL → skipped_reason="policy_manual"
    4. Otherwise → delegate to inner start logic (AUTO policy + REMOTE_REQUIRED intent)

    Uses an advisory file lock (``DAEMON_LOCK_FILE``) to serialise
    concurrent spawn attempts and prevent TOCTOU races.
    """
    from specify_cli.saas.rollout import is_saas_sync_enabled
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig as _SyncConfig

    if config is None:
        config = _SyncConfig()
    policy = config.get_background_daemon()

    # Row 1: rollout disabled
    if not is_saas_sync_enabled():
        return DaemonStartOutcome(started=False, skipped_reason="rollout_disabled", pid=None)

    # Row 2: caller declared local-only intent
    if intent == DaemonIntent.LOCAL_ONLY:
        return DaemonStartOutcome(started=False, skipped_reason="intent_local_only", pid=None)

    # Row 3: operator policy is manual
    if policy == BackgroundDaemonPolicy.MANUAL:
        return DaemonStartOutcome(started=False, skipped_reason="policy_manual", pid=None)

    # Row 4 & 5: AUTO + REMOTE_REQUIRED — attempt to start
    _daemon_root().mkdir(parents=True, exist_ok=True)

    lock_fd = open(DAEMON_LOCK_FILE, "w")  # noqa: SIM115
    try:
        # Use a bounded wait instead of blocking indefinitely (#598).
        # If another process is starting the daemon, we retry for up to
        # ~10 seconds before giving up — the daemon is likely already
        # running and will be reachable on the next CLI call.
        acquired = False
        for _ in range(100):
            try:
                if sys.platform == "win32":
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError as exc:
                if not _is_daemon_lock_contention(exc):
                    return DaemonStartOutcome(
                        started=False,
                        skipped_reason=f"start_failed: {exc}",
                        pid=None,
                    )
                time.sleep(0.1)
        if not acquired:
            return DaemonStartOutcome(
                started=False,
                skipped_reason="start_failed: could not acquire daemon lock within 10s",
                pid=None,
            )
        try:
            _url, _port, _started = _ensure_sync_daemon_running_locked()
        except Exception as exc:
            return DaemonStartOutcome(
                started=False, skipped_reason=f"start_failed: {exc}", pid=None
            )
        # Retrieve the PID from the state file after successful start
        pid: int | None = None
        if DAEMON_STATE_FILE.exists():
            try:
                _u, _p, _t, pid = _parse_daemon_file(DAEMON_STATE_FILE)
            except Exception:
                pid = None
        return DaemonStartOutcome(started=True, skipped_reason=None, pid=pid)
    finally:
        if acquired:
            if sys.platform == "win32":
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _ensure_sync_daemon_running_locked(preferred_port: int | None = None) -> tuple[str, int, bool]:
    """Inner implementation — caller must hold the daemon lock file."""
    if DAEMON_STATE_FILE.exists():
        existing_url, existing_port, existing_token, existing_pid = _parse_daemon_file(DAEMON_STATE_FILE)
        if existing_port is not None and _check_sync_daemon_health(existing_port, existing_token):
            # Daemon is healthy — check whether it's running the current version.
            if _daemon_version_matches(existing_port, existing_token):
                return existing_url or f"http://127.0.0.1:{existing_port}", existing_port, False

            # Stale version — recycle the daemon.
            logger.info("Recycling sync daemon (version mismatch)")
            _stop_daemon_by_http(existing_url or f"http://127.0.0.1:{existing_port}", existing_token)
            _kill_and_cleanup(existing_pid)
        elif existing_pid is not None and not _is_process_alive(existing_pid):
            DAEMON_STATE_FILE.unlink(missing_ok=True)
        elif existing_pid is not None:
            _kill_and_cleanup(existing_pid)
        else:
            DAEMON_STATE_FILE.unlink(missing_ok=True)

    if preferred_port is not None:
        port = preferred_port
    else:
        port = _find_free_port()
    token = secrets.token_hex(16)

    # Redirect daemon output to a log file for diagnostics
    DAEMON_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(DAEMON_LOG_FILE, "a")  # noqa: SIM115

    proc = subprocess.Popen(
        [sys.executable, "-c", _background_script(port, token)],
        stdout=log_fh,
        stderr=log_fh,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    log_fh.close()

    url = f"http://127.0.0.1:{port}"

    # Wait up to ~20s for the daemon to become healthy (matching dashboard pattern)
    retry_delays = [0.1] * 10 + [0.25] * 40 + [0.5] * 20
    for delay in retry_delays:
        if _check_sync_daemon_health(port, token):
            _write_daemon_file(DAEMON_STATE_FILE, url, port, token, proc.pid)
            return url, port, True
        time.sleep(delay)

    if _is_process_alive(proc.pid):
        _write_daemon_file(DAEMON_STATE_FILE, url, port, token, proc.pid)
        return url, port, True

    raise RuntimeError(f"Sync daemon failed to start on port {port}")


def _stop_daemon_by_http(url: str, token: str | None) -> None:
    """Best-effort HTTP shutdown request to a running daemon."""
    request = urllib.request.Request(
        f"{url}/api/shutdown",
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=1.0):  # nosec B310 — request URL is localhost daemon control endpoint
            pass
    except Exception:
        pass


def stop_sync_daemon(timeout: float = 5.0) -> tuple[bool, str]:
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

    _stop_daemon_by_http(url or f"http://127.0.0.1:{port}", token)

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
