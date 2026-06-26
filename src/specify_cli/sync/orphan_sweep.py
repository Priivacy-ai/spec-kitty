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
import urllib.request
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import psutil

from specify_cli.sync import daemon as _daemon
from specify_cli.sync.daemon import (
    DAEMON_PORT_MAX_ATTEMPTS,
    DAEMON_PORT_START,
    _fetch_health_payload,
    _parse_daemon_file,
)

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "OrphanDaemon",
    "SweepReport",
    "enumerate_orphans",
    "sweep_orphans",
]


def __getattr__(name: str) -> Path:
    """Expose ``DAEMON_STATE_FILE`` as a lazy module attribute.

    The singleton state path is owned by :mod:`specify_cli.sync.daemon` and is
    resolved lazily there so ``SPEC_KITTY_HOME`` is honored after import (#2171).
    Re-export it here as a module attribute (rather than an import-time-frozen
    binding) so callers and tests can read ``orphan_sweep.DAEMON_STATE_FILE`` and
    get the current value.
    """
    if name == "DAEMON_STATE_FILE":
        return _daemon.DAEMON_STATE_FILE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _daemon_state_file() -> Path:
    """Return this module's pinned ``DAEMON_STATE_FILE`` override, else the
    canonical lazily-resolved daemon state path.

    Tests isolate the sweep by pinning ``orphan_sweep.DAEMON_STATE_FILE`` with
    ``monkeypatch.setattr``; that override is honored verbatim. Otherwise the
    value flows through from :mod:`specify_cli.sync.daemon`.
    """
    override = globals().get("DAEMON_STATE_FILE")
    if override is not None:
        return cast("Path", override)
    return _daemon.DAEMON_STATE_FILE


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
    """Issue ``GET /api/health`` and return the parsed JSON dict, or ``None`` on any failure.

    Delegates the localhost GET + JSON decode to the canonical
    ``specify_cli.sync.daemon._fetch_health_payload`` (FR-015 / SC-7: one
    localhost health-probe across ``sync/`` + ``dashboard/``).
    """
    payload = _fetch_health_payload(
        f"http://127.0.0.1:{port}/api/health",
        timeout=_HEALTH_PROBE_TIMEOUT_S,
    )
    # Narrow the canonical helper's `Any` (daemon.py is partially typed via a
    # pre-existing Popen issue) back to this function's declared contract.
    return payload if isinstance(payload, dict) else None


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
    state_file = _daemon_state_file()
    if not state_file.exists():
        return None
    _url, port, _token, _pid = _parse_daemon_file(state_file)
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
    """Try to terminate a single port-discovered orphan. Returns ``(swept, reason)``.

    This is the *port-scan* sweep surface (the auth-doctor ``--reset`` path).
    Its success criterion is **port close** (the daemon stops listening), which
    differs from the process-exit criterion of the canonical
    ``owner._sweep_daemon_process``. Escalation order:

    1. HTTP shutdown (POST /api/shutdown, no token). Pre-token daemons may
       comply; modern daemons return 403 and we fall through. (Port-scan only;
       the canonical reaper has no HTTP step.)
    2. Signal escalation (terminate → kill) delegated to the single canonical
       kill path ``owner._sweep_daemon_process`` (FR-015 / SC-7), then confirm
       the port has actually closed.

    If ``orphan.pid`` is ``None``, only step 1 is attempted; a failure reason
    is recorded if the port survives.
    """
    from specify_cli.sync.owner import _sweep_daemon_process

    # Step 1: HTTP shutdown (best-effort, no token) — port-scan-specific.
    _http_shutdown_no_token(orphan.port)
    if _wait_for_port_close(orphan.port, timeout_s=_TERMINATE_WAIT_S):
        return True, None

    # Step 2 requires a PID.
    if orphan.pid is None:
        return False, "no_pid_after_http_shutdown_failed"

    # Signal escalation via the canonical single kill path.
    reaped, reason = _sweep_daemon_process(
        orphan.pid,
        terminate_wait_s=_TERMINATE_WAIT_S,
        kill_wait_s=_KILL_WAIT_S,
    )
    if not reaped:
        # Confirm against the port too: the process may have exited even though
        # the kill path could not prove it (or vice-versa).
        if _wait_for_port_close(orphan.port, timeout_s=_PORT_POLL_INTERVAL_S):
            return True, None
        return False, reason or "port_still_listening_after_kill"

    # Process is gone per the canonical sweep; confirm the listening socket
    # has been released (preserves the port-close success contract).
    if _wait_for_port_close(orphan.port, timeout_s=_KILL_WAIT_S):
        return True, None
    return False, "process_gone_but_port_still_listening"


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
