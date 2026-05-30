"""Sync daemon lifecycle and localhost control plane.

Scope honesty (see #1071): the singleton is bound to ``DAEMON_STATE_FILE``,
which resolves under the user-scoped runtime root (``~/.spec-kitty/sync-daemon``
on POSIX, ``%LOCALAPPDATA%\\spec-kitty\\daemon`` via the unified RuntimeRoot
on Windows). That means *one daemon per state-file scope*. Different
``$HOME`` values (Conductor workspaces, container mounts, etc.) write to
different state files and therefore each spawn their own daemon, which is
how the cross-checkout leak in #1071 manifests in practice.

The ``scan_sync_daemons`` helper enumerates *every* live ``run_sync_daemon``
process on the host regardless of which state file claimed them, and the
``sync status --check`` / ``sync doctor`` surfaces surface that report so
operators can detect cross-scope orphans. ``ensure_sync_daemon_running``
verifies that any daemon it kills on version-mismatch has actually exited
before clearing the state file (see ``_kill_and_cleanup``).
"""

from __future__ import annotations

import errno
import json
import logging
import os
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
from functools import cache
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Tuple

if sys.platform == "win32":
    import msvcrt
else:  # pragma: no cover - platform-specific
    import fcntl

if TYPE_CHECKING:
    from specify_cli.sync.config import SyncConfig

import psutil  # type: ignore[import-untyped]

from specify_cli.core.atomic import atomic_write
from specify_cli.sync.diagnostics import SyncDiagnosticCode, emit_sync_diagnostic

logger = logging.getLogger(__name__)

_SPEC_KITTY_DIRNAME = ".spec-kitty"


def _sync_root() -> Path:
    """Return the sync state directory for the current platform.

    On Windows: resolves to ``%LOCALAPPDATA%\\spec-kitty\\sync\\``
    via the unified RuntimeRoot.
    On POSIX: returns ``~/.spec-kitty/sync`` unchanged (preserving existing behavior).
    """
    if sys.platform == "win32":
        from specify_cli.paths import get_runtime_root  # noqa: PLC0415
        return get_runtime_root().sync_dir
    return Path.home() / _SPEC_KITTY_DIRNAME / "sync"


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
    return Path.home() / _SPEC_KITTY_DIRNAME


# Module-level path constants derived from platform-aware helpers so that
# existing code referencing these names continues to work unchanged.
SPEC_KITTY_DIR = Path.home() / _SPEC_KITTY_DIRNAME
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

# Keep shutdown latency tight for restart-daemon NFR-002. The default
# ``serve_forever`` poll interval is 0.5s, which is user-visible on restart.
DAEMON_SERVE_FOREVER_POLL_SECONDS: float = 0.05

# Self-retirement tick interval (seconds).  Each running daemon re-checks
# DAEMON_STATE_FILE this often; if the recorded port is held by a different
# live process, the daemon retires itself.  See FR-008 / FR-010.
DAEMON_TICK_SECONDS: int = 30

_RUNTIME_BACKGROUND_START_DELAY_SECONDS: float = 1.0
_STARTUP_HEALTH_TIMEOUT_SECONDS: float = 0.1


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


@cache
def _get_package_version() -> str:
    """Return the installed specify_cli version string."""
    env_version = os.environ.get("SPEC_KITTY_CLI_VERSION")
    if env_version:
        return env_version

    try:
        from importlib.metadata import version

        return version("spec-kitty-cli")
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
        return bool(proc.is_running())
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
        from specify_cli.sync.owner import read_owner_record, redact_token

        sync: Any | None = None
        websocket_status = "Offline"
        try:
            from specify_cli.sync import runtime as runtime_module

            runtime = getattr(runtime_module, "_runtime", None)
            if runtime is not None:
                sync = runtime.background_service
                websocket_status = runtime.get_websocket_status()
        except Exception:
            logger.debug("Could not read sync runtime for health payload", exc_info=True)

        payload: dict[str, Any] = {
            "status": "ok",
            "token": getattr(self, "daemon_token", None),
            "protocol_version": DAEMON_PROTOCOL_VERSION,
            "package_version": _get_package_version(),
            "sync": {
                "running": bool(sync and sync.is_running),
                "last_sync": sync.last_sync.isoformat() if sync and sync.last_sync else None,
                "consecutive_failures": sync.consecutive_failures if sync else 0,
            },
            "websocket_status": websocket_status,
        }
        # Surface the redacted owner record (FR-006). The redactor returns
        # ``None`` when no record exists; we drop the key in that case so
        # the wire shape stays clean.
        owner_view = redact_token(read_owner_record())
        if owner_view is not None:
            payload["owner"] = owner_view
        self._send_json(200, payload)

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
            time.sleep(0.01)
            server.shutdown()

        threading.Thread(target=shutdown_server, args=(self.server,), daemon=True).start()


def _decide_self_retire(server: HTTPServer, my_port: int) -> None:
    """Inspect ``DAEMON_STATE_FILE`` and retire the running daemon if it is no
    longer the recorded singleton.

    State-file ownership belongs exclusively to
    ``_ensure_sync_daemon_running_locked``: this function MUST NOT call
    ``_write_daemon_file`` or ``DAEMON_STATE_FILE.unlink``.  When the recorded
    record is missing, malformed, or matches our own port we simply continue.
    When the recorded port differs and the recorded PID is still alive we are
    by definition the orphan and call ``server.shutdown()``.  When the
    recorded PID is dead, the file is stale; the next ``ensure_running`` call
    will reconcile it, so we keep running.
    """
    try:
        _url, parsed_port, _token, parsed_pid = _parse_daemon_file(DAEMON_STATE_FILE)
    except Exception:
        logger.debug("self-check tick: parse error, skipping")
        return

    if parsed_port is None:
        logger.debug("self-check tick: no recorded port, skipping")
        return

    if parsed_port == my_port:
        logger.debug("self-check tick: port matches (%d), continuing", my_port)
        return

    if parsed_pid is None or not _is_process_alive(parsed_pid):
        logger.debug(
            "self-check tick: recorded port=%d but pid=%s not alive; not retiring",
            parsed_port,
            parsed_pid,
        )
        return

    logger.info(
        "self-retiring (state file points at port=%d, our port=%d)",
        parsed_port,
        my_port,
    )
    server.shutdown()


class _ChainedTimer(threading.Timer):
    """A self-rearming ``threading.Timer`` that retires on ``cancel()``.

    Mirrors ``threading.Timer``'s surface so callers can keep treating the
    return value of ``_start_self_check_tick`` as a ``Timer``.  Each tick
    calls the action and then schedules the next tick; ``cancel()`` flips a
    flag and cancels the currently armed timer, breaking the chain.
    """

    def __init__(self, interval_s: float, action: Any) -> None:
        super().__init__(interval_s, self._fire)
        self.daemon = True
        self._interval_s = interval_s
        self._action = action
        self._chain_lock = threading.Lock()
        self._cancelled = False
        self._next: threading.Timer | None = None

    def _fire(self) -> None:
        if self._cancelled:
            return
        try:
            self._action()
        except Exception:  # pragma: no cover - defensive: never let a tick raise
            logger.exception("self-check tick raised; continuing")
        with self._chain_lock:
            if self._cancelled:
                return
            next_timer = threading.Timer(self._interval_s, self._fire)
            next_timer.daemon = True
            self._next = next_timer
            next_timer.start()

    def cancel(self) -> None:
        with self._chain_lock:
            self._cancelled = True
            if self._next is not None:
                self._next.cancel()
        super().cancel()


def _start_self_check_tick(
    server: HTTPServer,
    my_port: int,
    *,
    interval_s: float = float(DAEMON_TICK_SECONDS),
) -> threading.Timer:
    """Schedule the periodic self-retirement check.

    Returns a ``threading.Timer`` (concretely a ``_ChainedTimer``) whose
    ``.cancel()`` stops the recurring tick.  The underlying timer threads
    are always created with ``daemon=True`` so they cannot block process
    exit.
    """

    def _action() -> None:
        _decide_self_retire(server, my_port)

    timer = _ChainedTimer(interval_s, _action)
    timer.start()
    return timer


def run_sync_daemon(port: int, daemon_token: str | None) -> None:
    """Run the machine-global sync daemon forever.

    Once the HTTP server is bound, this function writes the canonical
    :class:`DaemonOwnerRecord` to ``<sync_root>/daemon/owner.json`` so the
    foreground can detect ownership mismatches (FR-005/FR-006/FR-007) and
    orphan crashes (FR-010). The record is removed on clean shutdown; if
    the process is killed (SIGKILL, crash, power loss) the file remains
    and orphan detection on the foreground side reconciles it.
    """
    import atexit
    import signal as _signal

    from specify_cli.sync.owner import (
        build_record_for_current_process,
        remove_owner_record,
        write_owner_record,
    )

    handler_class = type(
        "SyncDaemonRouter",
        (SyncDaemonHandler,),
        {"daemon_token": daemon_token},
    )
    server = HTTPServer(("127.0.0.1", port), handler_class)  # NOSONAR -- sync daemon control plane binds to localhost only

    # Bind succeeded — record ownership BEFORE accepting traffic so any
    # health probe that arrives in the first scheduling slice already sees
    # a coherent owner field.
    record = build_record_for_current_process(
        pid=os.getpid(),
        port=port,
        token=daemon_token or "",
    )
    try:
        write_owner_record(record)
    except OSError as exc:  # pragma: no cover - filesystem catastrophe
        logger.warning("Failed to write daemon owner record: %s", exc)

    def _start_runtime_in_background() -> None:
        try:
            time.sleep(_RUNTIME_BACKGROUND_START_DELAY_SECONDS)
            from specify_cli.sync.runtime import get_runtime

            get_runtime()
        except Exception:  # noqa: BLE001 — health endpoint stays available
            logger.exception("Failed to start sync runtime")

    threading.Thread(
        target=_start_runtime_in_background,
        name="spec-kitty-sync-runtime-start",
        daemon=True,
    ).start()

    def _cleanup_owner_record() -> None:
        try:
            remove_owner_record()
        # Best-effort cleanup: never block daemon exit on owner-record removal.
        except Exception:  # noqa: BLE001
            logger.debug("Owner record cleanup raised; continuing")

    atexit.register(_cleanup_owner_record)

    def _signal_handler(signum: int, _frame: Any) -> None:
        logger.info("Received signal %d; shutting down daemon", signum)
        _cleanup_owner_record()
        # ``HTTPServer.shutdown()`` blocks until ``serve_forever()`` returns.
        # If we call it on the main thread (where ``serve_forever()`` is
        # blocking), the signal handler deadlocks against the serve loop and
        # the process never exits. Spawn a daemon thread so the signal
        # handler returns immediately and ``serve_forever()`` is free to
        # observe the shutdown flag and unwind.
        def _shutdown_off_thread() -> None:
            try:
                server.shutdown()
            except Exception:  # noqa: BLE001 — best-effort during shutdown
                logger.debug("server.shutdown() raised during signal teardown")

        threading.Thread(target=_shutdown_off_thread, daemon=True).start()

    # Best-effort signal handlers. ``signal.signal`` only works on the main
    # thread, which is where ``run_sync_daemon`` always executes; if we are
    # ever called off-main-thread (tests stubbing this in), we silently
    # skip rather than raising.
    for sig_name in ("SIGTERM", "SIGINT"):
        sig = getattr(_signal, sig_name, None)
        if sig is None:
            continue
        try:
            _signal.signal(sig, _signal_handler)
        except (ValueError, OSError):  # pragma: no cover - off main thread
            pass

    tick = _start_self_check_tick(server, my_port=port)
    try:
        server.serve_forever(poll_interval=DAEMON_SERVE_FOREVER_POLL_SECONDS)
    finally:
        tick.cancel()
        _cleanup_owner_record()


def _background_script(port: int, daemon_token: str | None) -> str:
    """Generate the Python script executed by the daemon subprocess.

    Uses ``-m`` style import so the installed package is found via normal
    ``sys.path`` resolution rather than hard-coding a repo checkout path.
    """
    return textwrap.dedent(
        f"""\
        import os
        os.environ["SPEC_KITTY_SYNC_MINIMAL_IMPORT"] = "1"
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

    raw_sync_data = data.get("sync")
    sync_data: dict[str, object] = raw_sync_data if isinstance(raw_sync_data, dict) else {}
    raw_consecutive_failures = sync_data.get("consecutive_failures")
    websocket_status = str(data.get("websocket_status") or "Offline")
    return SyncDaemonStatus(
        healthy=healthy,
        url=url or f"http://127.0.0.1:{port}",
        port=port,
        token=token,
        pid=pid,
        sync_running=bool(sync_data.get("running")),
        last_sync=str(sync_data.get("last_sync")) if sync_data.get("last_sync") else None,
        consecutive_failures=(
            int(raw_consecutive_failures)
            if isinstance(raw_consecutive_failures, (str, bytes, int))
            else 0
        ),
        websocket_status=websocket_status,
        protocol_version=data.get("protocol_version"),
        package_version=data.get("package_version"),
    )


def _kill_and_cleanup(pid: int | None, *, wait_timeout: float = 2.0) -> None:
    """Kill a daemon process, wait for it to actually exit, and remove the state file.

    The AC for #1071 explicitly requires that ``ensure_sync_daemon_running``
    not leave older daemons alive after starting a replacement for
    version/protocol mismatch. We therefore wait briefly for the killed
    process to exit before unlinking the state file so that the next
    ``ensure_running`` call observes a clean slate rather than racing the
    prior daemon's teardown.
    """
    if pid is not None:
        try:
            proc = psutil.Process(pid)
            proc.kill()
            wait_fn = getattr(proc, "wait", None)
            if callable(wait_fn):
                try:
                    wait_fn(timeout=wait_timeout)
                except psutil.TimeoutExpired:
                    logger.warning(
                        "Daemon pid=%s did not exit within %.1fs after SIGKILL; "
                        "state file will be cleared anyway",
                        pid,
                        wait_timeout,
                    )
                except TypeError:
                    # Some test doubles stub ``wait()`` without a ``timeout``
                    # keyword. Fall back to a positional call and tolerate
                    # any further mismatch silently — the state file is
                    # cleared either way.
                    try:
                        wait_fn(wait_timeout)
                    except Exception:  # noqa: BLE001
                        pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    DAEMON_STATE_FILE.unlink(missing_ok=True)


def ensure_sync_daemon_running(  # noqa: C901 — lifecycle decision matrix plus lock/retry handling.
    *,
    intent: DaemonIntent,
    config: SyncConfig | None = None,
    health_wait_seconds: float | None = None,
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
            emit_sync_diagnostic(
                SyncDiagnosticCode.LOCK_UNAVAILABLE,
                "Could not acquire sync lock within 5 s; skipping final sync. "
                "Queued events will be drained by the daemon.",
            )
            return DaemonStartOutcome(
                started=False,
                skipped_reason="start_failed: could not acquire daemon lock within 10s",
                pid=None,
            )
        try:
            if health_wait_seconds is None:
                _url, _port, _started = _ensure_sync_daemon_running_locked()
            else:
                _url, _port, _started = _ensure_sync_daemon_running_locked(
                    health_wait_seconds=health_wait_seconds
                )
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


def _bounded_retry_delays(
    retry_delays: list[float],
    max_wait_seconds: float | None,
) -> list[float]:
    if max_wait_seconds is None:
        return retry_delays
    bounded: list[float] = []
    total = 0.0
    for delay in retry_delays:
        if total >= max_wait_seconds:
            break
        bounded.append(min(delay, max_wait_seconds - total))
        total += delay
    return bounded


def _ensure_sync_daemon_running_locked(
    preferred_port: int | None = None,
    *,
    health_wait_seconds: float | None = None,
) -> tuple[str, int, bool]:
    """Inner implementation — caller must hold the daemon lock file."""
    if DAEMON_STATE_FILE.exists():
        existing_url, existing_port, existing_token, existing_pid = _parse_daemon_file(DAEMON_STATE_FILE)
        if existing_port is not None and _check_sync_daemon_health(
            existing_port,
            existing_token,
            timeout=_STARTUP_HEALTH_TIMEOUT_SECONDS,
        ):
            # Daemon is healthy — check whether it's running the current version.
            if _daemon_version_matches(
                existing_port,
                existing_token,
                timeout=_STARTUP_HEALTH_TIMEOUT_SECONDS,
            ):
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
        env={**os.environ, "SPEC_KITTY_CLI_VERSION": _get_package_version()},
    )
    log_fh.close()

    url = f"http://127.0.0.1:{port}"

    # Wait up to ~20s for the daemon to become healthy (matching dashboard pattern)
    retry_delays = _bounded_retry_delays(
        [0.1] * 10 + [0.25] * 40 + [0.5] * 20,
        health_wait_seconds,
    )
    for delay in retry_delays:
        if _check_sync_daemon_health(
            port,
            token,
            timeout=_STARTUP_HEALTH_TIMEOUT_SECONDS,
        ):
            _write_daemon_file(DAEMON_STATE_FILE, url, port, token, proc.pid)
            return url, port, True
        time.sleep(delay)

    if _is_process_alive(proc.pid):
        _kill_and_cleanup(proc.pid)

    raise RuntimeError(f"Sync daemon failed health check on port {port}")


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
        _kill_and_cleanup(pid)
        if pid is None:
            return True, "Unhealthy sync daemon metadata has been cleared."
        return True, "Unhealthy sync daemon process stopped. Metadata has been cleared."

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


# ---------------------------------------------------------------------------
# Singleton diagnostics (issue #1071)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrphanDaemonInfo:
    """A live ``run_sync_daemon`` process not represented by the state file."""

    pid: int
    cmdline: tuple[str, ...]


@dataclass(frozen=True)
class DaemonSingletonReport:
    """Snapshot of all live ``run_sync_daemon`` processes on the host.

    Use :func:`scan_sync_daemons` to capture this; use
    :func:`cleanup_orphan_sync_daemons` to terminate orphans. The
    singleton invariant is: at most one live daemon process matches
    the canonical state file's PID; everything else is an orphan that
    leaks ports/sockets and should be reaped.
    """

    state_pid: int | None
    state_file_present: bool
    orphan_processes: tuple[OrphanDaemonInfo, ...]

    @property
    def orphan_count(self) -> int:
        return len(self.orphan_processes)

    @property
    def is_singleton(self) -> bool:
        return self.orphan_count == 0


def _iter_sync_daemon_processes() -> list[psutil.Process]:
    """Yield live processes whose cmdline references ``run_sync_daemon``."""
    matches: list[psutil.Process] = []
    for proc in psutil.process_iter(attrs=["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if not cmdline:
            continue
        if any("run_sync_daemon" in str(part) for part in cmdline):
            matches.append(proc)
    return matches


def scan_sync_daemons() -> DaemonSingletonReport:
    """Inspect the host for live sync-daemon processes.

    Returns a structured report whose ``orphan_processes`` enumerate
    every live ``run_sync_daemon`` process that is *not* the one
    recorded in ``DAEMON_STATE_FILE``. The state-file PID, when
    present and live, is treated as the canonical singleton and is
    excluded from the orphan list.
    """
    state_pid: int | None = None
    state_present = DAEMON_STATE_FILE.exists()
    if state_present:
        try:
            _, _, _, state_pid = _parse_daemon_file(DAEMON_STATE_FILE)
        except Exception:  # noqa: BLE001
            state_pid = None

    orphans: list[OrphanDaemonInfo] = []
    for proc in _iter_sync_daemon_processes():
        try:
            pid = int(proc.pid)
            cmdline_seq = proc.info.get("cmdline") or []
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if state_pid is not None and pid == state_pid:
            continue
        orphans.append(
            OrphanDaemonInfo(
                pid=pid,
                cmdline=tuple(str(part) for part in cmdline_seq),
            )
        )

    return DaemonSingletonReport(
        state_pid=state_pid,
        state_file_present=state_present,
        orphan_processes=tuple(orphans),
    )


def cleanup_orphan_sync_daemons(
    *,
    dry_run: bool = False,
    timeout: float = 1.0,
) -> tuple[DaemonSingletonReport, list[int]]:
    """Terminate orphan sync-daemon processes; return report and PIDs killed.

    Args:
        dry_run: When True, report the orphans without terminating
            anything. Useful for diagnostics and tests.
        timeout: Seconds to wait for graceful termination per orphan
            before falling back to ``kill()``.

    Returns:
        A tuple of ``(report, killed_pids)`` where ``report`` is the
        pre-cleanup snapshot and ``killed_pids`` is the list of PIDs
        that received a kill signal. When ``dry_run`` is True the list
        is always empty.
    """
    report = scan_sync_daemons()
    killed: list[int] = []
    if dry_run:
        return report, killed

    for orphan in report.orphan_processes:
        try:
            proc = psutil.Process(orphan.pid)
        except psutil.NoSuchProcess:
            continue
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        try:
            proc.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        except psutil.NoSuchProcess:
            pass
        killed.append(orphan.pid)
    return report, killed
