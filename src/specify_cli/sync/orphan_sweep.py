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

WP03 upgrade (port-scan classification + reset reporting):
- ``enumerate_identity_records`` builds a full ``DaemonIdentityRecord`` per
  in-range listener via the WP01 classifier.
- ``reset_orphans`` returns a structured ``ResetResult`` with per-entry
  ``swept``/``skipped``/``failed`` arrays and ``cleanup_path`` provenance.
- Hard in-range + family guard protects every ``_sweep_daemon_process`` call
  (NFR-001, C-002, C-004).
- ``enumerate_orphans``/``sweep_orphans`` remain as un-exported back-compat
  definitions for the legacy ``tests/sync/test_orphan_sweep.py`` suite only
  (WP05 migrated the production callers onto the classified API above).
"""

from __future__ import annotations

import json
import logging
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil

from specify_cli.sync import daemon as _daemon
from specify_cli.sync.classification import (
    CandidateProbe,
    CleanupClass,
    DaemonIdentityRecord,
    ForegroundScope,
    HealthProbe,
    SingletonRef,
    classify_candidate,
)
from specify_cli.sync.daemon import (
    DAEMON_PORT_MAX_ATTEMPTS,
    DAEMON_PORT_START,
    _fetch_health_payload,
    _parse_daemon_file,
)

logger = logging.getLogger(__name__)

# ``__all__`` declares the *public* API. The legacy port-scan trio
# (``OrphanDaemon`` / ``enumerate_orphans`` / ``sweep_orphans``) is intentionally
# omitted: WP05 migrated ``_auth_doctor.py`` onto ``enumerate_identity_records`` /
# ``reset_orphans``, leaving the trio with no ``src/`` caller. The definitions
# remain below purely so the legacy ``tests/sync/test_orphan_sweep.py`` end-to-end
# suite can import them by name, but they are no longer part of the exported
# surface (closes the dead-``__all__``-symbol gate without dropping that coverage).
__all__ = [
    "FailedEntry",
    "ResetResult",
    "SkippedEntry",
    "SweepReport",
    "SweptEntry",
    "enumerate_identity_records",
    "reset_orphans",
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
    override: Path | None = globals().get("DAEMON_STATE_FILE")
    if override is not None:
        return override
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

# Hard port-range boundaries (NFR-001, C-002): sweep calls must never escape
# the sync-daemon reserved range or touch a process from a different family.
_SYNC_FAMILY: str = "sync"
_DAEMON_PORT_END: int = DAEMON_PORT_START + DAEMON_PORT_MAX_ATTEMPTS


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
# Structured ResetResult (WP03 / FR-005)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SweptEntry:
    """Per-entry record for a successfully swept daemon (FR-005).

    ``cleanup_path`` records which escalation step closed the port:
    ``http_shutdown`` | ``terminate`` | ``kill``.
    """

    pid: int | None
    port: int
    package_version: str | None
    protocol_version: int | None
    cleanup_path: str
    reason: str


@dataclass(frozen=True)
class SkippedEntry:
    """Per-entry record for a skipped daemon (FR-005).

    Daemons are skipped when ``cleanup_class`` is ``operator_required`` and
    ``include_operator_required=False`` (the default), or when the entry is
    ``never_touch``.
    """

    pid: int | None
    port: int
    cleanup_class: str
    skip_reason: str | None


@dataclass(frozen=True)
class FailedEntry:
    """Per-entry record for a daemon that survived every escalation step (FR-005)."""

    pid: int | None
    port: int
    failure_reason: str


@dataclass(frozen=True)
class ResetResult:
    """Structured outcome of ``auth doctor --reset`` (FR-005).

    ``swept``:   daemons whose port closed (any escalation path).
    ``skipped``: daemons not attempted (``operator_required`` without force,
                 or ``never_touch``).
    ``failed``:  daemons that survived every escalation step.
    """

    swept: list[SweptEntry] = field(default_factory=list)
    skipped: list[SkippedEntry] = field(default_factory=list)
    failed: list[FailedEntry] = field(default_factory=list)


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


def _read_singleton_ref() -> SingletonRef:
    """Return the ``SingletonRef`` (pid, port) from ``DAEMON_STATE_FILE``.

    Returns ``SingletonRef(pid=None, port=None)`` when the file is absent or
    cannot be parsed.
    """
    state_file = _daemon_state_file()
    if not state_file.exists():
        return SingletonRef(pid=None, port=None)
    _url, port, _token, pid = _parse_daemon_file(state_file)
    return SingletonRef(
        pid=int(pid) if pid is not None else None,
        port=int(port) if port is not None else None,
    )


def _build_health_probe(
    payload: dict[str, Any] | None, port: int, pid: int | None
) -> HealthProbe:
    """Build a ``HealthProbe`` from a raw ``/api/health`` payload dict.

    Sets ``responded=False`` when ``payload is None`` (no response / timeout),
    which the classifier maps to ``operator_required / unresponsive`` (D-01).
    """
    del port, pid
    if payload is None:
        return HealthProbe(
            responded=False,
            status=None,
            protocol_version=None,
            package_version=None,
            daemon_family=None,
            owner_pid=None,
            owner_port=None,
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
        )

    # Extract the ``owner`` block that carries the daemon's self-reported
    # pid/port (used for pid_port_mismatch detection in the classifier).
    owner_block = payload.get("owner") or {}
    raw_owner_pid = owner_block.get("pid") if isinstance(owner_block, dict) else None
    raw_owner_port = owner_block.get("port") if isinstance(owner_block, dict) else None

    protocol_version_raw = payload.get("protocol_version")
    package_version_raw = payload.get("package_version")
    daemon_family_raw = payload.get("daemon_family")

    return HealthProbe(
        responded=True,
        status=str(payload.get("status", "ok")),
        protocol_version=int(protocol_version_raw) if isinstance(protocol_version_raw, int) else None,
        package_version=str(package_version_raw) if isinstance(package_version_raw, str) else None,
        daemon_family=str(daemon_family_raw) if isinstance(daemon_family_raw, str) else None,
        owner_pid=int(raw_owner_pid) if isinstance(raw_owner_pid, int) else None,
        owner_port=int(raw_owner_port) if isinstance(raw_owner_port, int) else None,
        queue_db_path=str(payload["queue_db_path"]) if isinstance(payload.get("queue_db_path"), str) else None,
        auth_scope=str(payload["auth_scope"]) if isinstance(payload.get("auth_scope"), str) else None,
        server_url=str(payload["server_url"]) if isinstance(payload.get("server_url"), str) else None,
    )


def _get_pid_cmdline(pid: int | None) -> list[str]:
    """Return the cmdline argv for ``pid``, or ``[]`` when unavailable."""
    if pid is None:
        return []
    try:
        proc = psutil.Process(pid)
        return list(proc.cmdline())
    except (psutil.Error, OSError):
        return []


def _derive_singleton_scope_id(cmdline: list[str]) -> str | None:
    """Extract the daemon-root scope marker from ``cmdline``, or ``None``."""
    from specify_cli.sync.owner import _cmdline_daemon_root_marker

    return _cmdline_daemon_root_marker(cmdline)


def _derive_spawn_shape_ok(cmdline: list[str]) -> bool:
    """Return True when ``cmdline`` has the production daemon spawn shape."""
    from specify_cli.sync.owner import _cmdline_has_daemon_spawn_signature

    return _cmdline_has_daemon_spawn_signature(cmdline)


def _derive_executable_summary(pid: int | None, cmdline: list[str]) -> str | None:
    """Return a digest of the process executable/argv0, or ``None``."""
    if pid is None:
        return None
    try:
        proc = psutil.Process(pid)
        from specify_cli.sync.owner import _process_executable_scopes

        scopes = _process_executable_scopes(proc, cmdline)
        if scopes:
            return next(iter(sorted(scopes)))
    except (psutil.Error, OSError):
        pass
    return None


def _foreground_scope() -> ForegroundScope:
    """Return the ``ForegroundScope`` for the current CLI process.

    The scope ID is the resolved daemon state root; the executable scope is
    the canonical interpreter path; the singleton is read from the state file.
    """
    from specify_cli.sync.daemon import _daemon_scope_root
    from specify_cli.sync.owner import canonical_executable_scope

    return ForegroundScope(
        scope_id=_daemon_scope_root(),
        executable_scope=canonical_executable_scope(),
        singleton=_read_singleton_ref(),
    )


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


def enumerate_identity_records() -> list[DaemonIdentityRecord]:
    """Scan the reserved daemon port range and return a classified identity record per orphan.

    Builds a full ``DaemonIdentityRecord`` per in-range listener by:

    1. Probing each port with a TCP connect-check (50 ms) and ``GET /api/health``
       (500 ms), constructing a ``HealthProbe`` (``responded=False`` when the
       health endpoint does not answer — wedged listeners).
    2. Resolving the listener PID via ``psutil``/``lsof`` and reading its cmdline
       to extract the daemon-root scope marker, spawn-shape flag, and executable
       summary.
    3. Calling ``classify_candidate`` to produce the verdict
       (``safe_auto`` / ``operator_required`` / ``never_touch``).

    Records with ``cleanup_class == never_touch`` (out-of-range, third-party,
    dashboard-family) are excluded from the result — callers never see them
    and cannot act on them (C-004).

    The ``is_recorded_singleton`` path yields records excluded from cleanup
    (they describe the live daemon), also excluded from this result.

    Replaces the legacy ``enumerate_orphans`` scan path for callers that need
    full identity and cleanup classification.
    """
    foreground = _foreground_scope()
    records: list[DaemonIdentityRecord] = []

    end_port = DAEMON_PORT_START + DAEMON_PORT_MAX_ATTEMPTS
    for port in range(DAEMON_PORT_START, end_port):
        if not _port_is_listening(port):
            continue

        payload = _probe_health(port)
        # Build HealthProbe regardless — responded=False when no payload.
        pid = _lookup_listening_pid(port)
        health = _build_health_probe(payload, port, pid)

        # Skip ports with no SK identity signal at all (neither health keys
        # nor spawn shape) — we need at least one signal to call the classifier.
        if payload is None or not _is_spec_kitty_daemon(payload):
            cmdline = _get_pid_cmdline(pid)
            if not _derive_spawn_shape_ok(cmdline):
                # No SK identity whatsoever — will be never_touch; skip entirely.
                continue

        cmdline = _get_pid_cmdline(pid)
        singleton_scope_id = _derive_singleton_scope_id(cmdline)
        spawn_shape_ok = _derive_spawn_shape_ok(cmdline)
        executable_summary = _derive_executable_summary(pid, cmdline)

        probe = CandidateProbe(
            port=port,
            listener_pid=pid,
            health=health,
            singleton_scope_id=singleton_scope_id,
            spawn_shape_ok=spawn_shape_ok,
            executable_summary=executable_summary,
            owner_present=False,  # owner.json lookup deferred to WP05 if needed
        )

        record = classify_candidate(probe, foreground)

        # Exclude never_touch (third-party / out-of-range) and singletons.
        if record.cleanup_class == CleanupClass.NEVER_TOUCH:
            continue
        if record.is_recorded_singleton:
            continue

        records.append(record)

    return records


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

    This is the stable backward-compatible accessor consumed by the existing
    ``_auth_doctor.py`` surface (WP05 will migrate it to
    ``enumerate_identity_records``).
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


def _assert_safe_to_sweep(record: DaemonIdentityRecord) -> None:
    """Hard guard: raise ``RuntimeError`` when ``record`` must not be swept.

    Enforces NFR-001 (in-range invariant), C-002 (sync-family only), and
    C-004 (never_touch must never be killed).

    The in-range check and family check are belt-and-suspenders enforcement
    at the call site — the classifier also refuses to produce safe_auto/
    operator_required for out-of-range or non-sync records.
    """
    if not (DAEMON_PORT_START <= record.port < _DAEMON_PORT_END):
        raise RuntimeError(
            f"BUG: attempted sweep of out-of-range port {record.port} "
            f"(expected [{DAEMON_PORT_START}, {_DAEMON_PORT_END}))"
        )
    if record.daemon_family != _SYNC_FAMILY:
        raise RuntimeError(
            f"BUG: attempted sweep of non-sync daemon_family={record.daemon_family!r} "
            f"on port {record.port}"
        )
    if record.cleanup_class == CleanupClass.NEVER_TOUCH:
        raise RuntimeError(
            f"BUG: attempted sweep of never_touch record on port {record.port} "
            f"(skip_reason={record.skip_reason!r})"
        )
    if not record.spawn_shape_ok:
        raise RuntimeError(
            f"BUG: attempted sweep of record without production spawn shape "
            f"on port {record.port}"
        )


def _sweep_one_with_path(record: DaemonIdentityRecord) -> tuple[bool, str, str | None]:
    """Try to terminate a single classified orphan daemon.

    Returns ``(swept, cleanup_path, failure_reason)``.

    ``cleanup_path`` is one of ``http_shutdown`` | ``terminate`` | ``kill``
    and records which escalation step closed the port (FR-005).

    ``failure_reason`` is ``None`` on success.

    Precondition: ``_assert_safe_to_sweep(record)`` must have been called.
    """
    from specify_cli.sync.owner import _sweep_daemon_process

    port = record.port
    pid = record.pid

    # Step 1: HTTP shutdown (best-effort, no token) — port-scan-specific.
    _http_shutdown_no_token(port)
    if _wait_for_port_close(port, timeout_s=_TERMINATE_WAIT_S):
        return True, "http_shutdown", None

    # Step 2 requires a PID.
    if pid is None:
        return False, "http_shutdown", "no_pid_after_http_shutdown_failed"

    # Signal escalation via the canonical single kill path.
    reaped, signal_path, reason = _sweep_daemon_process(
        pid,
        terminate_wait_s=_TERMINATE_WAIT_S,
        kill_wait_s=_KILL_WAIT_S,
    )
    if not reaped:
        # Confirm against the port too: the process may have exited even though
        # the kill path could not prove it (or vice-versa).
        if _wait_for_port_close(port, timeout_s=_PORT_POLL_INTERVAL_S):
            return True, "kill", None
        return False, "kill", reason or "port_still_listening_after_kill"

    # Process is gone per the canonical sweep; confirm the listening socket
    # has been released (preserves the port-close success contract).
    cleanup_path = signal_path or "terminate"
    if _wait_for_port_close(port, timeout_s=_KILL_WAIT_S):
        return True, cleanup_path, None
    return False, cleanup_path, "process_gone_but_port_still_listening"


def reset_orphans(
    records: list[DaemonIdentityRecord],
    *,
    include_operator_required: bool = False,
) -> ResetResult:
    """Sweep classified orphan daemons and return a structured ``ResetResult``.

    Default behaviour (``include_operator_required=False``):
    - ``safe_auto`` records are swept (HTTP shutdown → terminate → kill).
    - ``operator_required`` records appear in ``skipped`` with their
      ``cleanup_class`` / ``skip_reason`` (D-02).
    - ``never_touch`` records are never swept and never appear in the result
      (callers must not pass them here; ``_assert_safe_to_sweep`` enforces this).

    With ``include_operator_required=True`` (``--force`` path from WP05):
    - ``operator_required`` records are also attempted; successes → ``swept``,
      survivors → ``failed``.

    ``cleanup_path`` in each ``SweptEntry`` records which escalation step closed
    the port: ``http_shutdown`` | ``terminate`` | ``kill`` (FR-005).
    """
    swept: list[SweptEntry] = []
    skipped: list[SkippedEntry] = []
    failed: list[FailedEntry] = []

    for record in records:
        # Determine actionability.
        is_safe_auto = record.cleanup_class == CleanupClass.SAFE_AUTO
        is_operator_required = record.cleanup_class == CleanupClass.OPERATOR_REQUIRED

        if not is_safe_auto and not is_operator_required:
            # never_touch — callers should not pass these, but skip gracefully.
            logger.warning(
                "reset_orphans: skipping never_touch record on port %d "
                "(skip_reason=%s)",
                record.port,
                record.skip_reason,
            )
            continue

        if is_operator_required and not include_operator_required:
            skipped.append(
                SkippedEntry(
                    pid=record.pid,
                    port=record.port,
                    cleanup_class=record.cleanup_class.value,
                    skip_reason=record.skip_reason.value if record.skip_reason is not None else None,
                )
            )
            continue

        # Hard guard before any signal (NFR-001, C-002, C-004).
        _assert_safe_to_sweep(record)

        ok, cleanup_path, failure_reason = _sweep_one_with_path(record)
        if ok:
            reason_str = (
                f"{record.cleanup_class.value} stale-version"
                if record.package_version is not None
                else record.cleanup_class.value
            )
            swept.append(
                SweptEntry(
                    pid=record.pid,
                    port=record.port,
                    package_version=record.package_version,
                    protocol_version=record.protocol_version,
                    cleanup_path=cleanup_path,
                    reason=reason_str,
                )
            )
        else:
            failed.append(
                FailedEntry(
                    pid=record.pid,
                    port=record.port,
                    failure_reason=failure_reason or "unknown_failure",
                )
            )

    return ResetResult(swept=swept, skipped=skipped, failed=failed)


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
    reaped, _signal_path, reason = _sweep_daemon_process(
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

    This is the stable backward-compatible sweep for the existing
    ``_auth_doctor.py`` surface. New code should use ``reset_orphans`` with
    classified ``DaemonIdentityRecord`` inputs (WP05 migration target).
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
