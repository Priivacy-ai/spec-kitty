"""Orphan daemon enumeration and sweep for the machine-global sync daemon.

Implements FR-009 of the CLI session-survival / daemon singleton mission.

A "Spec Kitty sync daemon port" is any TCP port in the reserved range
``[DAEMON_PORT_START, DAEMON_PORT_START + DAEMON_PORT_MAX_ATTEMPTS)`` (i.e.
``9400..9450``). Within that range the *singleton* is the daemon whose port
matches the value recorded in ``DAEMON_STATE_FILE``. Anything else that
identifies itself as a Spec Kitty daemon is an *orphan* and is eligible for
the sweep.

Identity probe (R4 / non-clobber guarantee): a remote process is classified
as a Spec Kitty daemon **only** when its ``GET /api/health`` response
contains BOTH the ``protocol_version`` and ``package_version`` keys. Any
other process listening on the reserved range is left alone.
"""

from __future__ import annotations

import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import psutil  # type: ignore[import-untyped]

from specify_cli.sync.daemon import (
    DAEMON_PORT_MAX_ATTEMPTS,
    DAEMON_PORT_START,
    DAEMON_STATE_FILE,
    _parse_daemon_file,
)

__all__ = [
    "OrphanDaemon",
    "SweepReport",
    "enumerate_orphans",
    "sweep_orphans",
]


# Per-port budgets. The 50 ms TCP connect-check is the dominant filter for
# closed ports — each closed port costs at most ~50 ms wall-time on the scan
# path. Keeping this small is what lets the full 50-port enumeration finish
# inside the NFR-006 budget of 3 seconds even when nothing is listening.
_CONNECT_PROBE_TIMEOUT_S: float = 0.05
_HEALTH_PROBE_TIMEOUT_S: float = 0.5

# Per-step waits used during sweep escalation. Each escalation step waits up
# to one second for the port to free before falling through to the next step.
_TERMINATE_WAIT_S: float = 1.0
_KILL_WAIT_S: float = 1.0
_PORT_POLL_INTERVAL_S: float = 0.05


@dataclass(frozen=True)
class OrphanDaemon:
    """A Spec Kitty sync daemon listening on a port other than the recorded singleton.

    ``pid`` is ``None`` when neither ``psutil.net_connections`` nor the
    platform fallback can identify the listener. Sweep can still attempt HTTP
    shutdown without a PID, but escalation to ``terminate``/``kill`` is recorded
    as a failure in that case.
    """

    port: int
    pid: int | None = None
    package_version: str | None = None
    protocol_version: int | None = None


@dataclass(frozen=True)
class SweepReport:
    """Outcome of a sweep over a list of orphan daemons.

    ``swept`` lists orphans whose port stopped listening before the sweep
    returned (HTTP shutdown, terminate, or kill — any successful path).
    ``failed`` lists orphans that survived every escalation step, along
    with a short human-readable reason.
    ``duration_s`` is the wall-clock time of the sweep call.
    """

    swept: list[OrphanDaemon] = field(default_factory=list)
    failed: list[tuple[OrphanDaemon, str]] = field(default_factory=list)
    duration_s: float = 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _port_is_listening(port: int, *, timeout_s: float = _CONNECT_PROBE_TIMEOUT_S) -> bool:
    """Cheap TCP connect-check: True iff something accepts a connection on 127.0.0.1:port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout_s)
        return sock.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def _probe_health(port: int) -> dict[str, Any] | None:
    """Issue ``GET /api/health`` and return the parsed JSON dict, or ``None`` on any failure."""
    url = f"http://127.0.0.1:{port}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=_HEALTH_PROBE_TIMEOUT_S) as response:  # nosec B310 - URL is always 127.0.0.1 in the reserved daemon range.
            if response.status != 200:
                return None
            payload = response.read()
    except (urllib.error.URLError, OSError, TimeoutError):
        return None
    except Exception:
        return None

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def _is_spec_kitty_daemon(payload: dict[str, Any]) -> bool:
    """R4 identity rule: payload MUST carry both ``protocol_version`` AND ``package_version``."""
    return "protocol_version" in payload and "package_version" in payload


def _lookup_listening_pid(port: int) -> int | None:
    """Return the PID of the process listening on ``127.0.0.1:port``, or ``None``.

    Uses ``psutil.net_connections(kind="tcp")`` first and falls back to
    ``lsof`` when psutil cannot expose listener ownership. macOS frequently
    withholds PIDs from ``psutil.net_connections`` for subprocess sockets, while
    ``lsof`` can still resolve the listener owned by the current user.
    """
    try:
        conns = psutil.net_connections(kind="tcp")
    except psutil.AccessDenied:
        return _lookup_listening_pid_with_lsof(port)
    except (psutil.Error, OSError):
        return _lookup_listening_pid_with_lsof(port)

    for conn in conns:
        laddr = getattr(conn, "laddr", None)
        if laddr is None:
            continue
        # ``laddr`` may be a namedtuple with ``port`` or an empty tuple.
        conn_port = getattr(laddr, "port", None)
        if conn_port != port:
            continue
        if conn.status != psutil.CONN_LISTEN:
            continue
        pid = conn.pid
        if pid is None:
            return _lookup_listening_pid_with_lsof(port)
        return int(pid)

    return _lookup_listening_pid_with_lsof(port)


def _lookup_listening_pid_with_lsof(port: int) -> int | None:
    """Resolve a local listener PID with ``lsof`` when psutil cannot.

    The port value is an integer drawn from the fixed Spec Kitty daemon range,
    so it is safe to pass as an argument without shell interpolation.
    """
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            check=False,
            capture_output=True,
            text=True,
            timeout=0.75,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        if pid > 0:
            return pid
    return None


def _read_singleton_port() -> int | None:
    """Return the port recorded in ``DAEMON_STATE_FILE``, or ``None`` if absent/malformed."""
    if not DAEMON_STATE_FILE.exists():
        return None
    _url, port, _token, _pid = _parse_daemon_file(DAEMON_STATE_FILE)
    if port is None:
        return None
    return int(port)


def _wait_for_port_close(port: int, *, timeout_s: float) -> bool:
    """Poll the port until it stops listening, or ``timeout_s`` elapses.

    Returns True if the port is no longer listening.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not _port_is_listening(port):
            return True
        time.sleep(_PORT_POLL_INTERVAL_S)
    return not _port_is_listening(port)


def _http_shutdown_no_token(port: int) -> None:
    """Best-effort POST /api/shutdown without a token. Pre-token daemons may comply.

    Any exception is swallowed — this is the gentlest escalation step and
    failures are expected (modern daemons return 403 here).
    """
    url = f"http://127.0.0.1:{port}/api/shutdown"
    request = urllib.request.Request(
        url,
        data=json.dumps({}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=1.0):  # nosec B310 - request URL is 127.0.0.1 in the reserved daemon range.
            return
    except Exception:
        return


def _port_closed_after_process_disappeared(port: int) -> tuple[bool, str | None]:
    """Handle races where the process exits between discovery and escalation."""
    if _wait_for_port_close(port, timeout_s=_TERMINATE_WAIT_S):
        return True, None
    return False, "process_gone_but_port_still_listening"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enumerate_orphans() -> list[OrphanDaemon]:
    """Scan the reserved daemon port range and return Spec Kitty daemons that are not the singleton.

    Algorithm:

    1. Read ``DAEMON_STATE_FILE`` once to capture the recorded singleton port.
    2. For each port in ``[DAEMON_PORT_START, DAEMON_PORT_START + DAEMON_PORT_MAX_ATTEMPTS)``:

       1. Cheap TCP connect-check — skip closed ports immediately.
       2. ``GET /api/health`` — skip non-200 / non-JSON / unreachable.
       3. Identity probe — payload MUST carry both ``protocol_version`` AND
          ``package_version`` keys (R4). Otherwise skip — never classify a
          third-party process as a Spec Kitty daemon.
       4. Skip the singleton port.
       5. Look up PID via ``psutil.net_connections``; PID may be ``None``
          on macOS without elevated privileges.

    The 50-port scan is bounded by the per-port budgets above and finishes
    well under the NFR-006 3-second wall-clock budget for closed-range scans.
    """
    singleton_port = _read_singleton_port()
    orphans: list[OrphanDaemon] = []

    end_port = DAEMON_PORT_START + DAEMON_PORT_MAX_ATTEMPTS
    for port in range(DAEMON_PORT_START, end_port):
        if not _port_is_listening(port):
            continue

        payload = _probe_health(port)
        if payload is None:
            continue
        if not _is_spec_kitty_daemon(payload):
            continue
        if singleton_port is not None and port == singleton_port:
            continue

        protocol_version_raw = payload.get("protocol_version")
        package_version_raw = payload.get("package_version")
        protocol_version = (
            int(protocol_version_raw)
            if isinstance(protocol_version_raw, int)
            else None
        )
        package_version = (
            str(package_version_raw) if isinstance(package_version_raw, str) else None
        )

        pid = _lookup_listening_pid(port)
        orphans.append(
            OrphanDaemon(
                port=port,
                pid=pid,
                package_version=package_version,
                protocol_version=protocol_version,
            )
        )

    return orphans


def _sweep_one(orphan: OrphanDaemon) -> tuple[bool, str | None]:
    """Try to terminate a single orphan. Returns ``(swept, failure_reason)``.

    Escalation order:

    1. HTTP shutdown (POST /api/shutdown, no token). Pre-token daemons may
       comply; modern daemons return 403 and we fall through.
    2. ``psutil.Process(pid).terminate()`` — wait up to 1 s for the port to free.
    3. ``psutil.Process(pid).kill()``      — wait up to 1 s for the port to free.

    If ``orphan.pid`` is ``None``, only step 1 is attempted; failure reason
    is recorded if the port survives.
    """
    # Step 1: HTTP shutdown (best-effort, no token).
    _http_shutdown_no_token(orphan.port)
    if _wait_for_port_close(orphan.port, timeout_s=_TERMINATE_WAIT_S):
        return True, None

    # Steps 2 & 3 require a PID.
    if orphan.pid is None:
        return False, "no_pid_after_http_shutdown_failed"

    try:
        proc = psutil.Process(orphan.pid)
    except psutil.NoSuchProcess:
        # Process vanished between health-probe and now; the port may already
        # be free (race with self-retirement tick).
        return _port_closed_after_process_disappeared(orphan.port)
    except psutil.AccessDenied:
        return False, "access_denied_opening_process"

    # Step 2: SIGTERM via psutil.
    try:
        proc.terminate()
    except psutil.NoSuchProcess:
        return _port_closed_after_process_disappeared(orphan.port)
    except psutil.AccessDenied:
        return False, "access_denied_on_terminate"

    if _wait_for_port_close(orphan.port, timeout_s=_TERMINATE_WAIT_S):
        return True, None

    # Step 3: SIGKILL via psutil.
    try:
        proc.kill()
    except psutil.NoSuchProcess:
        return _port_closed_after_process_disappeared(orphan.port)
    except psutil.AccessDenied:
        return False, "access_denied_on_kill"

    if _wait_for_port_close(orphan.port, timeout_s=_KILL_WAIT_S):
        return True, None

    return False, "port_still_listening_after_kill"


def sweep_orphans(
    orphans: list[OrphanDaemon],
    *,
    timeout_s: float = 5.0,
) -> SweepReport:
    """Escalate-and-shut down each orphan, returning a structured report.

    ``timeout_s`` bounds the overall sweep wall-clock; the individual escalation
    waits are unchanged but the loop stops early when the deadline is reached.
    Worst-case per orphan is ~3 seconds (HTTP wait + terminate wait + kill wait).
    """
    started_at = time.monotonic()
    deadline = started_at + max(timeout_s, 0.0) * max(len(orphans), 1)

    swept: list[OrphanDaemon] = []
    failed: list[tuple[OrphanDaemon, str]] = []

    for orphan in orphans:
        if time.monotonic() >= deadline:
            failed.append((orphan, "sweep_deadline_exceeded"))
            continue

        ok, reason = _sweep_one(orphan)
        if ok:
            swept.append(orphan)
        else:
            failed.append((orphan, reason or "unknown_failure"))

    duration_s = time.monotonic() - started_at
    return SweepReport(swept=swept, failed=failed, duration_s=duration_s)
