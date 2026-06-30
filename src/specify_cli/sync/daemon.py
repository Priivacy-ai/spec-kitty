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
import importlib
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
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, cast

if sys.platform == "win32":
    import msvcrt
else:  # pragma: no cover - platform-specific
    import fcntl

if TYPE_CHECKING:
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.owner import DaemonOwnerRecord

import psutil

from specify_cli.core.atomic import atomic_write
from specify_cli.core.loopback_http import (
    build_loopback_base_url,
    build_loopback_url,
    create_loopback_server,
)
from specify_cli.paths import get_runtime_root
from specify_cli.sync.diagnostics import SyncDiagnosticCode, emit_sync_diagnostic

logger = logging.getLogger(__name__)


def _spec_kitty_dir() -> Path:
    """Return the runtime state root, honouring ``SPEC_KITTY_HOME`` (WP01).

    Resolved lazily on every call so environment overrides and test ``HOME``
    monkeypatching are honoured (research.md D5). On POSIX this is
    ``~/.spec-kitty`` when ``SPEC_KITTY_HOME`` is unset — byte-identical to the
    retired import-time ``SPEC_KITTY_DIR`` constant it replaces.
    """
    # ``get_runtime_root`` is seen as ``Any`` here because mypy skips imports
    # for ``specify_cli.*`` (follow_imports=skip); coerce at the typed boundary.
    base: Path = get_runtime_root().base
    return base


def _sync_root() -> Path:
    """Return the sync state directory for the current platform.

    On Windows: resolves to ``%LOCALAPPDATA%\\spec-kitty\\sync\\``
    via the unified RuntimeRoot.
    On POSIX: returns ``<runtime root>/sync`` (``~/.spec-kitty/sync`` when
    ``SPEC_KITTY_HOME`` is unset), preserving the existing flat layout.
    """
    if sys.platform == "win32":
        return get_runtime_root().sync_dir
    base: Path = get_runtime_root().base
    return base / "sync"


def _daemon_root() -> Path:
    """Return the daemon state directory for the current platform.

    On Windows: resolves to ``%LOCALAPPDATA%\\spec-kitty\\daemon\\``
    via the unified RuntimeRoot.
    On POSIX: returns the runtime root itself (``~/.spec-kitty`` when
    ``SPEC_KITTY_HOME`` is unset) — daemon state files live directly under the
    flat root on POSIX (research.md D3), never under a ``daemon`` subdir.
    """
    if sys.platform == "win32":
        return get_runtime_root().daemon_dir
    base: Path = get_runtime_root().base
    return base


# Daemon state/log/lock paths are derived lazily from the platform-aware
# ``_daemon_root()`` helper. Resolving them on every access (rather than freezing
# them at import time) is what lets ``SPEC_KITTY_HOME`` — and test ``HOME``
# monkeypatching — take effect even when it is set or changed after this module
# was first imported (#2171, mirrors the ``SPEC_KITTY_DIR`` shim below).
#
# A test (or caller) may still pin an explicit value with
# ``monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", path)``; that binds the name
# as a real module global, which then shadows ``__getattr__`` for lookups. The
# in-module helpers below honor such an override first so production reads and
# patched-out tests agree on a single seam.
_LAZY_PATH_RESOLVERS: dict[str, Callable[[], Path]]  # forward decl for helpers


def _resolve_lazy_path(name: str, resolver: Callable[[], Path]) -> Path:
    """Return an explicitly-pinned module override for ``name`` if present, else
    the lazily-resolved default.

    The four lazy path names are never defined as real module globals (they are
    served by ``__getattr__``), so ``globals().get(name)`` is ``None`` unless a
    caller — typically a test via ``monkeypatch.setattr`` — pinned a value. Any
    such override (a real ``Path`` or a duck-typed test double exposing the
    ``Path`` surface the daemon uses) is honored verbatim; otherwise the
    platform-aware default is resolved fresh on every call.
    """
    override: Any = globals().get(name)
    if override is not None:
        # Production overrides are real Paths; tests may pin a duck-typed double
        # exposing the Path surface the daemon consumes. Either is honored.
        return cast("Path", override)
    return resolver()


def _daemon_state_file() -> Path:
    """Return the daemon singleton state file under the current daemon root."""
    return _resolve_lazy_path("DAEMON_STATE_FILE", lambda: _daemon_root() / "sync-daemon")


def _daemon_log_file() -> Path:
    """Return the daemon log file under the current daemon root."""
    return _resolve_lazy_path("DAEMON_LOG_FILE", lambda: _daemon_root() / "sync-daemon.log")


def _daemon_lock_file() -> Path:
    """Return the daemon advisory-lock file under the current daemon root."""
    return _resolve_lazy_path("DAEMON_LOCK_FILE", lambda: _daemon_root() / "sync-daemon.lock")


_LAZY_PATH_RESOLVERS = {
    "SPEC_KITTY_DIR": _spec_kitty_dir,
    "DAEMON_STATE_FILE": _daemon_state_file,
    "DAEMON_LOG_FILE": _daemon_log_file,
    "DAEMON_LOCK_FILE": _daemon_lock_file,
}


def __getattr__(name: str) -> Path:
    """Lazily resolve path-valued module constants on every access.

    ``SPEC_KITTY_DIR`` and the ``DAEMON_*_FILE`` paths used to be evaluated at
    import time, which froze them to the home directory present when the module
    first loaded and defeated ``SPEC_KITTY_HOME`` / test ``HOME`` monkeypatching
    (research.md D5, #2171). They are now resolved on every access. Kept as
    module-level shims because external importers (and several daemon tests)
    reference the names. NOTE: importers must read them as module attributes
    (``daemon.DAEMON_STATE_FILE``); a ``from daemon import DAEMON_STATE_FILE``
    binds the value once and re-freezes it.
    """
    resolver = _LAZY_PATH_RESOLVERS.get(name)
    if resolver is not None:
        return resolver()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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

# Loopback health-check endpoint path served by the sync daemon.
_HEALTH_ENDPOINT_PATH = "/api/health"

# Keep shutdown latency tight for restart-daemon NFR-002. The default
# ``serve_forever`` poll interval is 0.5s, which is user-visible on restart.
DAEMON_SERVE_FOREVER_POLL_SECONDS: float = 0.05

# Self-retirement tick interval (seconds).  Each running daemon re-checks
# DAEMON_STATE_FILE this often; if the recorded port is held by a different
# live process, the daemon retires itself.  See FR-008 / FR-010.
DAEMON_TICK_SECONDS: int = 30

# Idle self-retirement window (FR-011 / DD-03).  A daemon with no authenticated
# requests and no sync work in flight retires after this many seconds.  The
# constant is module-level so tests can patch it to a low value without
# introducing wall-clock sleeps.
SYNC_DAEMON_IDLE_RETIREMENT_SECONDS: float = 900.0

# Tracks the monotonic time of the last authenticated request received by this
# daemon process.  Initialised to the process start time so a freshly-spawned
# daemon does not immediately retire before its first client connects.
_daemon_last_activity_time: float = time.monotonic()

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
    data = _fetch_health_payload(build_loopback_url(port, _HEALTH_ENDPOINT_PATH), timeout=timeout)
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
    data = _fetch_health_payload(build_loopback_url(port, _HEALTH_ENDPOINT_PATH), timeout=timeout)
    if not data:
        return False
    if data.get("status") != "ok":
        return False
    if expected_token and data.get("token") != expected_token:
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
    daemon_owner_record: DaemonOwnerRecord | None = None

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
        if parsed_path.path == _HEALTH_ENDPOINT_PATH:
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
        from specify_cli.sync.owner import redact_token

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
            # FR-001 / C-001: hard family tag lets a scanner confirm identity
            # from the self-report (defense-in-depth on top of port-range isolation).
            "daemon_family": "sync",
            # Surface the resolved daemon-root scope so scanners can verify
            # singleton_scope_id matches the foreground scope without needing
            # to inspect the process cmdline separately.
            "singleton_scope_id": _daemon_scope_root(),
            "protocol_version": DAEMON_PROTOCOL_VERSION,
            "package_version": _get_package_version(),
            "sync": {
                "running": bool(sync and sync.is_running),
                "last_sync": sync.last_sync.isoformat() if sync and sync.last_sync else None,
                "consecutive_failures": sync.consecutive_failures if sync else 0,
            },
            "websocket_status": websocket_status,
        }
        # Surface this daemon instance's own owner record, not the shared
        # owner.json file that another same-scope daemon may have overwritten.
        owner_view = redact_token(getattr(self, "daemon_owner_record", None))
        if owner_view is not None:
            payload["owner"] = owner_view
        self._send_json(200, payload)

    def handle_sync_trigger(self) -> None:
        if self._require_token() is None:
            return

        _touch_last_activity()
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

        _touch_last_activity()
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

        _touch_last_activity()
        self._send_json(200, {"status": "stopping"})

        def shutdown_server(server: HTTPServer) -> None:
            time.sleep(0.01)
            server.shutdown()

        threading.Thread(target=shutdown_server, args=(self.server,), daemon=True).start()


def _touch_last_activity() -> None:
    """Record that an authenticated request was just received.

    Called from authenticated handler endpoints so the idle-retirement clock
    resets on each real client interaction.  Not called for unauthenticated
    probes (e.g. ``/api/health``), which do not constitute "work".
    """
    global _daemon_last_activity_time
    _daemon_last_activity_time = time.monotonic()


def _should_self_retire(
    *,
    my_port: int,
    parsed_port: int | None,
    parsed_pid: int | None,
    sync_is_running: bool,
    idle_seconds: float,
) -> tuple[bool, str]:
    """Pure retirement predicate — all decisions made here, not in the tick.

    Returns ``(should_retire, reason)`` so callers can log the reason and tests
    can assert on it without mocking ``server.shutdown()``.

    Rules (FR-010 / FR-011):
    - Never retire while sync work is in flight (``sync_is_running``).
    - Retire promptly when superseded: the state file records a different port
      whose PID is still alive, meaning a newer daemon took over.
    - Retire after ``SYNC_DAEMON_IDLE_RETIREMENT_SECONDS`` when no auth/work
      for the full idle window.
    """
    if sync_is_running:
        return False, "sync_in_flight"

    # Superseded check (prompt retirement — no idle wait).
    if parsed_port is not None and parsed_port != my_port and parsed_pid is not None:
        if _is_process_alive(parsed_pid):
            return True, "superseded"

    # General idle timeout (FR-011).
    if idle_seconds >= SYNC_DAEMON_IDLE_RETIREMENT_SECONDS:
        return True, "idle_timeout"

    return False, "active"


def _decide_self_retire(server: HTTPServer, my_port: int) -> None:
    """Inspect ``DAEMON_STATE_FILE`` and retire the running daemon if warranted.

    State-file ownership belongs exclusively to
    ``_ensure_sync_daemon_running_locked``: this function MUST NOT call
    ``_write_daemon_file`` or ``DAEMON_STATE_FILE.unlink``.  When the recorded
    record is missing or malformed we check only the idle timeout.  When the
    recorded port matches our own port we are the singleton and check only the
    idle timeout (we will never be superseded).

    Retirement conditions (delegated to ``_should_self_retire``):
    - **Superseded**: state file records a different port whose PID is alive.
    - **General idle**: no authenticated request for
      ``SYNC_DAEMON_IDLE_RETIREMENT_SECONDS`` and no sync work in flight.
    - **Guard**: never retire while ``sync.is_running`` is True (FR-010).
    """
    try:
        _url, parsed_port, _token, parsed_pid = _parse_daemon_file(_daemon_state_file())
    except Exception:
        logger.debug("self-check tick: parse error, skipping singleton check")
        parsed_port = None
        parsed_pid = None

    # Gather sync-in-flight state without importing the full runtime on the
    # hot path; failure to probe is safe (treated as "not running").
    sync_is_running = False
    try:
        runtime_module = importlib.import_module("specify_cli.sync.runtime")
        _rt = getattr(runtime_module, "_runtime", None)
        if _rt is not None and _rt.background_service is not None:
            sync_is_running = bool(_rt.background_service.is_running)
    except Exception:
        logger.debug("self-check tick: could not probe sync state", exc_info=True)

    idle_seconds = time.monotonic() - _daemon_last_activity_time
    should_retire, reason = _should_self_retire(
        my_port=my_port,
        parsed_port=parsed_port,
        parsed_pid=parsed_pid,
        sync_is_running=sync_is_running,
        idle_seconds=idle_seconds,
    )

    if not should_retire:
        logger.debug("self-check tick: continuing (reason=%s)", reason)
        return

    logger.info("self-retiring (reason=%s, port=%d)", reason, my_port)
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


def _start_runtime_bootstrap_thread(
    port: int,
    daemon_token: str | None,
    handler_class: type[SyncDaemonHandler],
) -> None:
    def _start_runtime_in_background() -> None:
        try:
            time.sleep(_RUNTIME_BACKGROUND_START_DELAY_SECONDS)
            from specify_cli.sync.runtime import get_runtime

            get_runtime()
            owner_record = _write_daemon_owner_record(port, daemon_token, allow_network=True)
            if owner_record is not None:
                handler_class.daemon_owner_record = owner_record
        except Exception:  # noqa: BLE001 — health endpoint stays available
            logger.exception("Failed to start sync runtime")

    threading.Thread(
        target=_start_runtime_in_background,
        name="spec-kitty-sync-runtime-start",
        daemon=True,
    ).start()


def _write_daemon_owner_record(
    port: int, daemon_token: str | None, *, allow_network: bool
) -> DaemonOwnerRecord | None:
    from specify_cli.sync.owner import (
        build_record_for_current_process,
        write_owner_record,
    )

    record = build_record_for_current_process(
        pid=os.getpid(),
        port=port,
        token=daemon_token or "",
        allow_network=allow_network,
    )
    try:
        write_owner_record(record)
    except OSError as exc:  # pragma: no cover - filesystem catastrophe
        logger.warning("Failed to write daemon owner record: %s", exc)
    except Exception:
        if not allow_network:
            raise
        logger.debug("Failed to enrich daemon owner record", exc_info=True)
        return None
    return record


def _register_daemon_owner_cleanup(pid: int, port: int) -> Callable[[], None]:
    import atexit

    from specify_cli.sync.owner import remove_owner_record_if_matches

    def _cleanup_owner_record() -> None:
        try:
            remove_owner_record_if_matches(pid, port)
        except Exception:  # noqa: BLE001
            logger.debug("Owner record cleanup raised; continuing")

    atexit.register(_cleanup_owner_record)
    return _cleanup_owner_record


def _install_daemon_signal_handlers(server: HTTPServer, cleanup_owner_record: Callable[[], None]) -> None:
    import signal as _signal

    def _signal_handler(signum: int, _frame: Any) -> None:
        logger.info("Received signal %d; shutting down daemon", signum)
        cleanup_owner_record()

        def _shutdown_off_thread() -> None:
            try:
                server.shutdown()
            except Exception:  # noqa: BLE001 — best-effort during shutdown
                logger.debug("server.shutdown() raised during signal teardown")

        threading.Thread(target=_shutdown_off_thread, daemon=True).start()

    for sig_name in ("SIGTERM", "SIGINT"):
        sig = getattr(_signal, sig_name, None)
        if sig is None:
            continue
        try:
            _signal.signal(sig, _signal_handler)
        except (ValueError, OSError):  # pragma: no cover - off main thread
            pass


def run_sync_daemon(port: int, daemon_token: str | None) -> None:
    """Run the machine-global sync daemon forever.

    Once the HTTP server is bound, this function writes the canonical
    :class:`DaemonOwnerRecord` to ``<sync_root>/daemon/owner.json`` so the
    foreground can detect ownership mismatches (FR-005/FR-006/FR-007) and
    orphan crashes (FR-010). The record is removed on clean shutdown; if
    the process is killed (SIGKILL, crash, power loss) the file remains
    and orphan detection on the foreground side reconciles it.
    """
    handler_class = type(
        "SyncDaemonRouter",
        (SyncDaemonHandler,),
        {"daemon_token": daemon_token, "daemon_owner_record": None},
    )
    handler_type = cast("type[SyncDaemonHandler]", handler_class)
    server = create_loopback_server(port, handler_class)

    # Bind succeeded — record ownership BEFORE accepting traffic so any
    # health probe that arrives in the first scheduling slice already sees
    # a coherent owner field.
    owner_record = _write_daemon_owner_record(port, daemon_token, allow_network=False)
    handler_type.daemon_owner_record = owner_record
    _start_runtime_bootstrap_thread(port, daemon_token, handler_type)
    cleanup_owner_record = _register_daemon_owner_cleanup(os.getpid(), port)
    _install_daemon_signal_handlers(server, cleanup_owner_record)

    tick = _start_self_check_tick(server, my_port=port)
    try:
        server.serve_forever(poll_interval=DAEMON_SERVE_FOREVER_POLL_SECONDS)
    finally:
        tick.cancel()
        cleanup_owner_record()


def _background_script(port: int, daemon_token: str | None) -> str:
    """Generate the Python script executed by the daemon subprocess.

    Uses ``-m`` style import so the installed package is found via normal
    ``sys.path`` resolution rather than hard-coding a repo checkout path.

    The spawner (``_spawn_sync_daemon_process``) appends the daemon-root
    scope marker (:func:`daemon_scope_marker`) and the spawn-interpreter
    identity marker (:func:`daemon_exec_marker`) as trailing argv elements so
    the canonical reaper can positively attribute the daemon to its state
    root and to the interpreter that spawned it; the script itself never
    reads them.
    """
    return textwrap.dedent(
        f"""\
        import os
        os.environ["SPEC_KITTY_SYNC_MINIMAL_IMPORT"] = "1"
        from specify_cli.sync.daemon import run_sync_daemon
        run_sync_daemon({port}, {repr(daemon_token)})
        """
    )


# argv prefix marking which daemon state root a spawned ``run_sync_daemon``
# process belongs to. The canonical reaper (``owner.reap_orphan_daemons``)
# only reaps processes whose marker matches its own daemon root; processes
# without a recognizable marker are never auto-reaped.
DAEMON_SCOPE_ARG_PREFIX = "--spec-kitty-daemon-root="


def _daemon_scope_root() -> str:
    """Return the canonical (symlink-resolved) daemon state root for this process.

    This is the ``$HOME``-derived scope identity embedded in the spawned
    daemon's argv (:func:`daemon_scope_marker`) and matched by the canonical
    reaper, so a daemon belonging to a different ``$HOME`` / container /
    state root is never reaped.
    """
    root = _daemon_root()
    try:
        return str(root.resolve())
    except (OSError, RuntimeError):
        return str(root)


def daemon_scope_marker() -> str:
    """Return the argv scope-marker element for daemons spawned by this process."""
    return DAEMON_SCOPE_ARG_PREFIX + _daemon_scope_root()


# argv prefix recording the canonical (symlink-resolved) interpreter the
# spawn used. On macOS framework Python the spawned interpreter re-execs the
# ``Resources/Python.app/Contents/MacOS/Python`` stub, rewriting BOTH the
# running daemon's ``Process.exe()`` AND its ``argv[0]`` to the stub path —
# so no live-process identity source can ever equal the foreground's
# canonical ``sys.executable``. The inert argv tail survives the re-exec
# verbatim, so the reaper compares this spawn-recorded identity instead of
# guessing platform rewrites.
DAEMON_EXEC_ARG_PREFIX = "--spec-kitty-daemon-exec="


def _spawn_interpreter_identity() -> str:
    """Return the canonical (symlink-resolved) interpreter spawning daemons.

    Mirrors ``owner._canonical_executable_path(sys.executable)`` without
    importing ``owner`` (which imports this module). Resolve failures fall
    back to the raw ``sys.executable`` string.
    """
    try:
        return str(Path(sys.executable).resolve())
    except (OSError, RuntimeError):
        return str(sys.executable)


def daemon_exec_marker() -> str:
    """Return the argv exec-identity element for daemons spawned by this process."""
    return DAEMON_EXEC_ARG_PREFIX + _spawn_interpreter_identity()


def get_sync_daemon_status(timeout: float = 0.5) -> SyncDaemonStatus:
    """Return health and sync metadata for the machine-global daemon."""
    if not _daemon_state_file().exists():
        return SyncDaemonStatus(healthy=False)

    url, port, token, pid = _parse_daemon_file(_daemon_state_file())
    if port is None:
        return SyncDaemonStatus(healthy=False, url=url, token=token, pid=pid)

    data = _fetch_health_payload(build_loopback_url(port, _HEALTH_ENDPOINT_PATH), timeout=timeout)
    if not data:
        return SyncDaemonStatus(
            healthy=False,
            url=url or build_loopback_base_url(port),
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
        url=url or build_loopback_base_url(port),
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
    _daemon_state_file().unlink(missing_ok=True)


def _daemon_start_skip_reason(
    intent: DaemonIntent,
    policy: object,
) -> str | None:
    from specify_cli.saas.rollout import is_saas_sync_enabled
    from specify_cli.sync.config import BackgroundDaemonPolicy

    if not is_saas_sync_enabled():
        return "rollout_disabled"
    if intent == DaemonIntent.LOCAL_ONLY:
        return "intent_local_only"
    if policy == BackgroundDaemonPolicy.MANUAL:
        return "policy_manual"
    return None


def _acquire_daemon_lock(lock_fd: Any) -> bool:
    for _ in range(100):
        try:
            if sys.platform == "win32":
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError as exc:
            if not _is_daemon_lock_contention(exc):
                raise
            time.sleep(0.1)
    return False


def _release_daemon_lock(lock_fd: Any) -> None:
    if sys.platform == "win32":
        msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)


def _read_daemon_pid() -> int | None:
    if not _daemon_state_file().exists():
        return None
    try:
        _u, _p, _t, pid = _parse_daemon_file(_daemon_state_file())
    except Exception:
        return None
    return pid


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
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig as _SyncConfig

    if config is None:
        config = _SyncConfig()
    policy = config.get_background_daemon()

    skip_reason = _daemon_start_skip_reason(intent, policy)
    if skip_reason is not None:
        return DaemonStartOutcome(started=False, skipped_reason=skip_reason, pid=None)

    # Row 4 & 5: AUTO + REMOTE_REQUIRED — attempt to start
    _daemon_root().mkdir(parents=True, exist_ok=True)

    lock_fd = open(_daemon_lock_file(), "w")  # noqa: SIM115
    acquired = False
    try:
        try:
            acquired = _acquire_daemon_lock(lock_fd)
        except OSError as exc:
            return DaemonStartOutcome(
                started=False,
                skipped_reason=f"start_failed: {exc}",
                pid=None,
            )
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
        pid = _read_daemon_pid()
        return DaemonStartOutcome(started=True, skipped_reason=None, pid=pid)
    finally:
        if acquired:
            _release_daemon_lock(lock_fd)
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
    existing = _reuse_or_cleanup_existing_daemon()
    if existing is not None:
        return existing

    # FR-014b / #1071: before spawning a replacement, reap any stale
    # ``run_sync_daemon`` orphans that belong to THIS scope — same canonical
    # interpreter AND a cmdline daemon-root marker matching THIS daemon state
    # root. This enforces one daemon per daemon-root scope: a leak from two
    # spawners in one ``$HOME`` each recycling the other's recorded PID
    # leaves untracked orphans on fresh ports; the canonical reaper clears
    # them at spawn. A daemon from a different ``$HOME`` / container
    # (different daemon root) or one without a recognizable marker
    # (pre-marker spawns) is never touched (reaper-over-kill guard).
    # Best-effort: a reaper failure must not block the spawn.
    _reap_same_executable_orphans()

    if preferred_port is not None:
        port = preferred_port
    else:
        port = _find_free_port()
    token = secrets.token_hex(16)

    proc = _spawn_sync_daemon_process(port, token)
    url = build_loopback_base_url(port)

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
            _write_daemon_file(_daemon_state_file(), url, port, token, proc.pid)
            return url, port, True
        time.sleep(delay)

    if _is_process_alive(proc.pid):
        _kill_and_cleanup(proc.pid)

    raise RuntimeError(f"Sync daemon failed health check on port {port}")


def _reap_same_executable_orphans() -> None:
    """Reap stale same-scope ``run_sync_daemon`` orphans at spawn time.

    Delegates to the single canonical reaper (``owner.reap_orphan_daemons``),
    scoped by this process's interpreter identity AND its daemon-root scope
    marker (see ``daemon_scope_marker``). Best-effort: any failure is logged
    at DEBUG and swallowed so a reaper hiccup never blocks daemon startup.
    """
    try:
        from specify_cli.sync.owner import reap_orphan_daemons

        result = reap_orphan_daemons()
        if result.reaped:
            logger.info(
                "Reaped %d stale sync-daemon orphan(s) at spawn: %s",
                len(result.reaped),
                result.reaped,
            )
    except Exception:  # noqa: BLE001 — reaping is best-effort on the spawn path.
        logger.debug("Spawn-path orphan reap raised; continuing", exc_info=True)


def _reuse_or_cleanup_existing_daemon() -> tuple[str, int, bool] | None:
    if not _daemon_state_file().exists():
        return None

    existing_url, existing_port, existing_token, existing_pid = _parse_daemon_file(
        _daemon_state_file()
    )
    if existing_port is not None and _check_sync_daemon_health(
        existing_port,
        existing_token,
        timeout=_STARTUP_HEALTH_TIMEOUT_SECONDS,
    ):
        if _daemon_version_matches(
            existing_port,
            existing_token,
            timeout=_STARTUP_HEALTH_TIMEOUT_SECONDS,
        ):
            return existing_url or build_loopback_base_url(existing_port), existing_port, False

        logger.info("Recycling sync daemon (version mismatch)")
        _stop_daemon_by_http(
            existing_url or build_loopback_base_url(existing_port), existing_token
        )
        _kill_and_cleanup(existing_pid)
        return None

    if existing_pid is not None and not _is_process_alive(existing_pid):
        _daemon_state_file().unlink(missing_ok=True)
    elif existing_pid is not None:
        _kill_and_cleanup(existing_pid)
    else:
        _daemon_state_file().unlink(missing_ok=True)
    return None


def _spawn_sync_daemon_process(port: int, token: str) -> subprocess.Popen[str]:
    _daemon_log_file().parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(_daemon_log_file(), "a")  # noqa: SIM115
    proc = subprocess.Popen(
        # The trailing marker argv elements are inert for the script
        # (``python -c`` exposes them only via ``sys.argv``) but let the
        # canonical reaper attribute this daemon to THIS daemon state root
        # and to THIS spawn interpreter (the exec marker is the only identity
        # that survives the macOS framework re-exec, which rewrites exe()
        # and argv[0] to the Python.app stub).
        [
            sys.executable,
            "-c",
            _background_script(port, token),
            daemon_scope_marker(),
            daemon_exec_marker(),
        ],
        stdout=log_fh,
        stderr=log_fh,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        text=True,
        env={**os.environ, "SPEC_KITTY_CLI_VERSION": _get_package_version()},
    )
    log_fh.close()
    return proc


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
    if not _daemon_state_file().exists():
        return False, "No sync daemon metadata found."

    url, port, token, pid = _parse_daemon_file(_daemon_state_file())
    if port is None:
        _daemon_state_file().unlink(missing_ok=True)
        return False, "Sync daemon metadata was invalid and has been cleared."

    if not _check_sync_daemon_health(port, token):
        _kill_and_cleanup(pid)
        if pid is None:
            return True, "Unhealthy sync daemon metadata has been cleared."
        return True, "Unhealthy sync daemon process stopped. Metadata has been cleared."

    _stop_daemon_by_http(url or build_loopback_base_url(port), token)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _check_sync_daemon_health(port, token, timeout=0.2):
            _daemon_state_file().unlink(missing_ok=True)
            return True, "Sync daemon stopped."
        time.sleep(0.05)

    if pid is not None:
        try:
            psutil.Process(pid).kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _daemon_state_file().unlink(missing_ok=True)
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
    state_present = _daemon_state_file().exists()
    if state_present:
        try:
            _, _, _, state_pid = _parse_daemon_file(_daemon_state_file())
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

    Diagnostic surface for ``sync status`` / ``sync doctor``. The actual kill
    escalation delegates to the canonical reaper's single sweep
    (``owner._sweep_daemon_process``) so there is exactly ONE kill path
    host-wide (FR-015 / SC-7). Unlike :func:`reap_orphan_daemons`, this surface
    is *not* executable-scoped: operators running ``sync status`` expect to see
    and clear every leaked ``run_sync_daemon`` they own, regardless of
    interpreter.

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
    from specify_cli.sync.owner import _sweep_daemon_process

    report = scan_sync_daemons()
    killed: list[int] = []
    if dry_run:
        return report, killed

    for orphan in report.orphan_processes:
        reaped, _signal_path, _reason = _sweep_daemon_process(
            orphan.pid,
            terminate_wait_s=timeout,
            kill_wait_s=timeout,
        )
        if reaped:
            killed.append(orphan.pid)
    return report, killed
