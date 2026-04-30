"""Implementation of ``spec-kitty auth doctor`` (WP06).

This module is the user-facing diagnostic surface for the
``cli-session-survival-daemon-singleton`` mission. It assembles a structured
:class:`DoctorReport` from local-only state — encrypted session, refresh-lock
record, daemon state file, and (optionally) 127.0.0.1 health probes for
orphan-daemon detection — and renders it via Rich or as a versioned JSON
payload.

Default invocation contract (FR-015, C-007):

- Reads only local files and 127.0.0.1 ports. NEVER makes outbound network
  calls. NEVER writes, deletes, terminates, or mutates anything.
- Two opt-in repair flags (``--reset`` and ``--unstick-lock``) are independent
  (C-008) and run the underlying repair primitives (``sweep_orphans`` from
  WP05 and ``force_release`` from WP01) only when the corresponding
  finding is present.

The ``--server`` flag (FR-011 through FR-015, FR-017) is an explicit opt-in
network path. It refreshes the access token if needed, then calls
``GET /api/v1/session-status``. C-007 still holds for the default path.

Public API (consumed by ``cli.commands.auth.doctor`` and tests):

- :class:`Finding`, :class:`SessionSummary`, :class:`LockSummary`,
  :class:`DaemonSummary`, :class:`DoctorReport` — frozen dataclasses
  mirroring ``data-model.md`` §"DoctorReport".
- :class:`ServerSessionStatus` — frozen dataclass for the opt-in server check.
- :func:`assemble_report` — pure data gather; no rendering, no mutation.
- :func:`render_report` — Rich rendering of the 7 sections.
- :func:`render_report_json` — ``--json`` payload (datetime → ISO-8601,
  Path → str).
- :func:`compute_exit_code` — 0 / 1 / 2 policy from findings list.
- :func:`doctor_impl` — orchestration entry point invoked by the typer
  shell.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import socket
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Literal

from rich.console import Console
from rich.table import Table

from specify_cli.auth import get_token_manager
from specify_cli.auth.token_manager import _refresh_lock_path
from specify_cli.cli.commands._auth_status import (
    format_duration,
    format_storage_backend,
)
from specify_cli.core.file_lock import (
    LockRecord,
    force_release,
    read_lock_record,
)
from specify_cli.sync.daemon import (
    DAEMON_STATE_FILE,
    SyncDaemonStatus,
    get_sync_daemon_status,
)
from specify_cli.sync.orphan_sweep import (
    OrphanDaemon,
    enumerate_orphans,
    sweep_orphans,
)

__all__ = [
    "DaemonSummary",
    "DoctorReport",
    "Finding",
    "LockSummary",
    "ServerSessionStatus",
    "SessionSummary",
    "assemble_report",
    "compute_exit_code",
    "doctor_impl",
    "render_report",
    "render_report_json",
]

console = Console()

# Schema version for the JSON payload. Bump this only on a breaking schema
# change so consumers can pin their parsers.
_SCHEMA_VERSION: int = 1

# Severity literal used by :class:`Finding`.
Severity = Literal["info", "warn", "critical"]


# ---------------------------------------------------------------------------
# Dataclasses (mirror data-model.md §"DoctorReport")
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A single diagnostic observation with optional remediation guidance.

    ``severity`` ladder:
        - ``info``     — observation, no action required.
        - ``warn``     — action recommended.
        - ``critical`` — action required (drives exit-code 1 unless repaired).
    """

    id: str
    severity: Severity
    summary: str
    remediation_command: str | None = None
    remediation_description: str | None = None


@dataclass(frozen=True)
class SessionSummary:
    """Local-state snapshot of the persisted auth session."""

    present: bool
    session_id: str | None
    user_email: str | None
    access_token_remaining_s: float | None
    refresh_token_remaining_s: float | None
    storage_backend: str | None
    in_memory_drift: bool


@dataclass(frozen=True)
class LockSummary:
    """Local-state snapshot of the machine-wide refresh lock."""

    held: bool
    holder_pid: int | None
    started_at: datetime | None
    age_s: float | None
    stuck: bool
    stuck_threshold_s: float
    holder_host: str | None


@dataclass(frozen=True)
class DaemonSummary:
    """Local-state snapshot of the user-scoped sync daemon."""

    active: bool
    pid: int | None
    port: int | None
    package_version: str | None
    protocol_version: int | None


@dataclass(frozen=True)
class DoctorReport:
    """Structured diagnostic report (versioned, JSON-serialisable)."""

    schema_version: int
    generated_at: datetime
    auth_root: Path
    session: SessionSummary | None
    refresh_lock: LockSummary
    daemon: DaemonSummary | None
    orphans: list[OrphanDaemon] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


@dataclass(frozen=True)
class ServerSessionStatus:
    """Result of an opt-in server-side session check (auth doctor --server).

    ``active=True`` means the server confirms the session is live.
    ``session_id`` is safe to display (not a secret).
    ``error`` is a brief human-readable failure reason; never contains
    raw tokens, token_family_id, is_revoked, or revocation_reason.
    """

    active: bool
    session_id: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers — read-only state gathering
# ---------------------------------------------------------------------------


def _read_session_summary() -> tuple[SessionSummary | None, Any]:
    """Return (summary, raw_session). Both ``None`` when no session present.

    The raw session is returned alongside the summary so downstream callers
    (``render_report``) can reuse identity formatters from
    ``_auth_status.py`` without re-reading state.
    """
    tm = get_token_manager()
    session = tm.get_current_session()
    if session is None:
        return None, None

    now = datetime.now(UTC)
    access_remaining = (session.access_token_expires_at - now).total_seconds()
    refresh_remaining: float | None = (
        None
        if session.refresh_token_expires_at is None
        else (session.refresh_token_expires_at - now).total_seconds()
    )

    in_memory_drift = _detect_persisted_drift(tm, session)

    summary = SessionSummary(
        present=True,
        session_id=session.session_id,
        user_email=session.email,
        access_token_remaining_s=access_remaining,
        refresh_token_remaining_s=refresh_remaining,
        storage_backend=session.storage_backend,
        in_memory_drift=in_memory_drift,
    )
    return summary, session


def _detect_persisted_drift(tm: Any, in_memory: Any) -> bool:
    """Return ``True`` when persisted material differs from in-memory state.

    During an in-flight refresh the persisted session may temporarily be
    ahead of the in-memory copy (or vice-versa). The check is best-effort:
    on any storage error we report ``False`` (no drift) so a transient
    backend hiccup never trips F-006.
    """
    try:
        persisted = tm._storage.read()
    except Exception:
        return False
    if persisted is None:
        return False
    if persisted.session_id != in_memory.session_id:
        return True
    return bool(persisted.refresh_token != in_memory.refresh_token)


def _read_lock_summary(stuck_threshold_s: float) -> LockSummary:
    """Read the refresh lock record and synthesise a :class:`LockSummary`."""
    path = _refresh_lock_path()
    record: LockRecord | None = read_lock_record(path)
    if record is None:
        return LockSummary(
            held=False,
            holder_pid=None,
            started_at=None,
            age_s=None,
            stuck=False,
            stuck_threshold_s=stuck_threshold_s,
            holder_host=None,
        )
    age_s = record.age_s
    return LockSummary(
        held=True,
        holder_pid=record.pid,
        started_at=record.started_at,
        age_s=age_s,
        stuck=age_s > stuck_threshold_s,
        stuck_threshold_s=stuck_threshold_s,
        holder_host=record.host,
    )


def _read_daemon_summary() -> DaemonSummary | None:
    """Return :class:`DaemonSummary` when a daemon state file exists.

    Calls ``get_sync_daemon_status`` which probes 127.0.0.1 — that is a
    *local* probe and explicitly allowed by C-007. When no state file is
    present we return ``None`` (no daemon expected).
    """
    if not DAEMON_STATE_FILE.exists():
        return None

    status: SyncDaemonStatus = get_sync_daemon_status()
    # Even when not healthy, surface the recorded PID/port so the report
    # can communicate "daemon recorded but unreachable".
    return DaemonSummary(
        active=status.healthy,
        pid=status.pid,
        port=status.port,
        package_version=status.package_version,
        protocol_version=status.protocol_version,
    )


def _read_auth_root() -> Path:
    """Return the auth-store directory (parent of the refresh lock)."""
    parent: Path = _refresh_lock_path().parent
    return parent


def _installed_package_version() -> str | None:
    """Return the installed package version for the daemon-mismatch check."""
    try:
        from importlib.metadata import version

        return version("spec-kitty-cli")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Findings + exit-code policy (T025)
# ---------------------------------------------------------------------------


def _compute_findings(
    *,
    session: SessionSummary | None,
    refresh_lock: LockSummary,
    daemon: DaemonSummary | None,
    orphans: list[OrphanDaemon],
) -> list[Finding]:
    """Compute :class:`Finding` list from the read-only state snapshots.

    Order is stable so JSON consumers and humans see the same sequence.
    """
    findings: list[Finding] = []

    # F-001 — no session loaded.
    if session is None:
        findings.append(
            Finding(
                id="F-001",
                severity="critical",
                summary="No active session",
                remediation_command="spec-kitty auth login",
                remediation_description=(
                    "Authenticate with the SaaS to establish a session."
                ),
            )
        )

    # F-002 — orphans present.
    if orphans:
        ports = ", ".join(str(o.port) for o in orphans)
        findings.append(
            Finding(
                id="F-002",
                severity="warn",
                summary=f"{len(orphans)} orphan daemon(s) detected on port(s) {ports}",
                remediation_command="spec-kitty auth doctor --reset",
                remediation_description="Sweep orphan daemons in the reserved port range.",
            )
        )

    # F-003 — refresh lock stuck (age past threshold).
    if refresh_lock.stuck and refresh_lock.age_s is not None:
        findings.append(
            Finding(
                id="F-003",
                severity="critical",
                summary=(
                    f"Refresh lock stuck (age {refresh_lock.age_s:.1f}s > "
                    f"threshold {refresh_lock.stuck_threshold_s:.1f}s)"
                ),
                remediation_command="spec-kitty auth doctor --unstick-lock",
                remediation_description=(
                    "Force-release the refresh lock when its age exceeds the "
                    "stuck threshold."
                ),
            )
        )

    # F-004 — daemon active but version mismatch.
    if daemon is not None and daemon.active and daemon.package_version is not None:
        installed = _installed_package_version()
        if installed is not None and installed != daemon.package_version:
            findings.append(
                Finding(
                    id="F-004",
                    severity="warn",
                    summary=(
                        f"Daemon version mismatch (running={daemon.package_version}, "
                        f"installed={installed})"
                    ),
                    remediation_command="spec-kitty sync restart",
                    remediation_description="Restart the sync daemon to adopt the new package version.",
                )
            )

    # F-005 — daemon expected but not running (informational).
    # We surface this only when rollout is enabled. The rollout module imports
    # are deferred so a missing/disabled SaaS surface never breaks the doctor
    # report.
    rollout_enabled = False
    try:
        from specify_cli.saas.rollout import is_saas_sync_enabled

        rollout_enabled = bool(is_saas_sync_enabled())
    except Exception:
        rollout_enabled = False
    if rollout_enabled and (daemon is None or not daemon.active):
        findings.append(
            Finding(
                id="F-005",
                severity="info",
                summary="Daemon not running; next CLI command will start it.",
                remediation_command=None,
                remediation_description=None,
            )
        )

    # F-006 — persisted/in-memory drift (after no in-flight refresh).
    if (
        session is not None
        and session.in_memory_drift
        and not refresh_lock.held
    ):
        findings.append(
            Finding(
                id="F-006",
                severity="warn",
                summary="Persisted session differs from in-memory state",
                remediation_command="spec-kitty auth doctor",
                remediation_description=(
                    "Re-run after a CLI command to confirm the divergence has "
                    "settled (typical during in-flight refresh)."
                ),
            )
        )

    # F-007 — lock holder is on a different host (NFS scenario).
    if refresh_lock.held and refresh_lock.holder_host is not None:
        local_host = socket.gethostname()
        if refresh_lock.holder_host != local_host:
            findings.append(
                Finding(
                    id="F-007",
                    severity="warn",
                    summary=(
                        f"Lock holder is on a different host "
                        f"(holder={refresh_lock.holder_host}, this={local_host})"
                    ),
                    remediation_command=None,
                    remediation_description=(
                        "Manual investigation required (NFS-shared auth root)."
                    ),
                )
            )

    return findings


def compute_exit_code(findings: list[Finding]) -> int:
    """Map ``findings`` to a process exit code per ``contracts/auth-doctor.md``.

    Exit policy:
        - ``0`` — no critical findings remain (default invocation healthy or
          repairs successfully cleared every critical finding).
        - ``1`` — at least one ``critical`` finding remains.
        - ``2`` — internal exception during diagnostic gathering (handled by
          the typer shell, not by this function).
    """
    for finding in findings:
        if finding.severity == "critical":
            return 1
    return 0


# ---------------------------------------------------------------------------
# Server-session check (T015) — opt-in network path for --server flag
# ---------------------------------------------------------------------------


async def _check_server_session() -> ServerSessionStatus:
    """Refresh token if needed, then GET /api/v1/session-status.

    Returns ServerSessionStatus. Never raises — all errors map to
    active=False with a brief, non-sensitive error description.
    """
    from specify_cli.auth import get_token_manager  # noqa: PLC0415 (avoid circular at module level)
    from specify_cli.auth.config import get_saas_base_url  # noqa: PLC0415
    import httpx  # noqa: PLC0415

    tm = get_token_manager()
    try:
        access_token = await tm.get_access_token()
    except Exception as exc:
        return ServerSessionStatus(active=False, error=f"Could not obtain access token: {type(exc).__name__}")

    try:
        saas_url = get_saas_base_url()
    except Exception:
        return ServerSessionStatus(active=False, error="SaaS URL not configured")

    url = f"{saas_url}/api/v1/session-status"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.RequestError as exc:
        return ServerSessionStatus(active=False, error=f"Network error: {type(exc).__name__}")
    except Exception:
        return ServerSessionStatus(active=False, error="Unexpected error during server check")

    if response.status_code == 200:
        try:
            body = response.json()
            session_id = body.get("session_id")
            return ServerSessionStatus(active=True, session_id=session_id)
        except ValueError:
            return ServerSessionStatus(active=False, error="Invalid response from server")

    if response.status_code == 401:
        return ServerSessionStatus(active=False, error="re-authenticate")

    return ServerSessionStatus(active=False, error=f"Server returned HTTP {response.status_code}")


# ---------------------------------------------------------------------------
# Public assembly + rendering API (T023, T024, T026)
# ---------------------------------------------------------------------------


def assemble_report(*, stuck_threshold_s: float = 60.0) -> DoctorReport:
    """Gather local-only state into a :class:`DoctorReport`. No mutation.

    All inputs are local files or 127.0.0.1 probes (allowed by C-007). The
    function never writes, deletes, terminates, or touches refresh-lock
    files — those mutations are the responsibility of :func:`doctor_impl`
    when the user opts in via ``--reset`` / ``--unstick-lock``.
    """
    session_summary, _raw_session = _read_session_summary()
    refresh_lock = _read_lock_summary(stuck_threshold_s)
    daemon = _read_daemon_summary()
    orphans = enumerate_orphans()

    findings = _compute_findings(
        session=session_summary,
        refresh_lock=refresh_lock,
        daemon=daemon,
        orphans=orphans,
    )

    return DoctorReport(
        schema_version=_SCHEMA_VERSION,
        generated_at=datetime.now(UTC),
        auth_root=_read_auth_root(),
        session=session_summary,
        refresh_lock=refresh_lock,
        daemon=daemon,
        orphans=orphans,
        findings=findings,
    )


def render_report(report: DoctorReport, console: Console, *, show_server_hint: bool = True) -> None:  # noqa: C901, PLR0912 — the 7-section layout is intentionally linear and section-by-section so reviewers can map each block to the contract; splitting it adds indirection without clarity.
    """Render a :class:`DoctorReport` as the 7-section Rich layout."""
    # Section 1 — Identity.
    console.print("[bold]Identity[/bold]")
    if report.session is None:
        console.print("  [red]X Not authenticated[/red]")
        console.print("  Run [bold]spec-kitty auth login[/bold] to authenticate.")
    else:
        console.print(f"  User:           {report.session.user_email}")
        console.print(f"  Session ID:     {report.session.session_id}")
    console.print()

    # Section 2 — Tokens.
    console.print("[bold]Tokens[/bold]")
    if report.session is None:
        console.print("  (no session)")
    else:
        access = report.session.access_token_remaining_s
        if access is not None:
            console.print(f"  Access token:   {format_duration(access)}")
        if report.session.refresh_token_remaining_s is None:
            console.print(
                "  Refresh token:  [dim]server-managed (legacy)[/dim]"
            )
        else:
            console.print(
                f"  Refresh token:  {format_duration(report.session.refresh_token_remaining_s)}"
            )
    console.print()

    # Section 3 — Storage.
    console.print("[bold]Storage[/bold]")
    if report.session is None or report.session.storage_backend is None:
        console.print("  (no session)")
    else:
        console.print(
            f"  Backend:        {format_storage_backend(report.session.storage_backend)}"
        )
        if report.session.in_memory_drift:
            console.print(
                "  [dim]Note: persisted differs from in-memory "
                "(typical during in-flight refresh)[/dim]"
            )
    console.print()

    # Section 4 — Refresh Lock.
    console.print("[bold]Refresh Lock[/bold]")
    lock = report.refresh_lock
    if not lock.held:
        console.print("  unheld")
    else:
        style = "[red]" if lock.stuck else ""
        end_style = "[/red]" if lock.stuck else ""
        console.print(f"  {style}Held by PID:    {lock.holder_pid}{end_style}")
        if lock.started_at is not None:
            console.print(
                f"  Acquired at:    {lock.started_at.isoformat()}"
            )
        if lock.age_s is not None:
            console.print(f"  Age:            {lock.age_s:.1f}s")
        console.print(f"  Host:           {lock.holder_host}")
        if lock.stuck:
            console.print(
                f"  [red]Stuck (age > {lock.stuck_threshold_s:.1f}s)[/red]"
            )
    console.print()

    # Section 5 — Daemon.
    console.print("[bold]Daemon[/bold]")
    if report.daemon is None:
        console.print("  not running")
    elif report.daemon.active:
        console.print("  Active:         yes")
        console.print(f"  PID:            {report.daemon.pid}")
        console.print(f"  Port:           {report.daemon.port}")
        console.print(f"  Package:        {report.daemon.package_version}")
        console.print(f"  Protocol:       {report.daemon.protocol_version}")
    else:
        console.print("  recorded but not healthy")
        if report.daemon.pid is not None:
            console.print(f"  Recorded PID:   {report.daemon.pid}")
        if report.daemon.port is not None:
            console.print(f"  Recorded port:  {report.daemon.port}")
    console.print()

    # Section 6 — Orphans.
    console.print("[bold]Orphans[/bold]")
    if not report.orphans:
        console.print("  (none)")
    else:
        table = Table(show_header=True, header_style="bold")
        table.add_column("PID")
        table.add_column("Port")
        table.add_column("Package version")
        for orphan in report.orphans:
            table.add_row(
                str(orphan.pid) if orphan.pid is not None else "(unknown)",
                str(orphan.port),
                orphan.package_version or "(unknown)",
            )
        console.print(table)
    console.print()

    # Section 7 — Findings & Remediation.
    console.print("[bold]Findings[/bold]")
    if not report.findings:
        console.print("  No problems detected.")
    else:
        severity_color = {
            "info": "cyan",
            "warn": "yellow",
            "critical": "red",
        }
        for finding in report.findings:
            color = severity_color[finding.severity]
            console.print(
                f"  [[{color}]{finding.severity}[/{color}]] "
                f"{finding.id}: {finding.summary}"
            )
            if finding.remediation_command is not None:
                description = (
                    f" — {finding.remediation_description}"
                    if finding.remediation_description
                    else ""
                )
                console.print(f"      Run: {finding.remediation_command}{description}")

    # Always present in offline mode — encourage server-aware check.
    if show_server_hint:
        console.print()
        console.print(
            "[dim]Run [bold]spec-kitty auth doctor --server[/bold] "
            "to verify server session status.[/dim]"
        )


def render_report_json(report: DoctorReport) -> str:
    """Serialise a :class:`DoctorReport` as a JSON string.

    Datetime values are emitted as ISO-8601 strings; :class:`Path` becomes
    its ``str``. The ``schema_version`` field guards against breaking
    consumer upgrades — bump it on any breaking schema change.
    """
    payload: dict[str, Any] = {
        "schema_version": report.schema_version,
        "generated_at": report.generated_at.isoformat(),
        "auth_root": str(report.auth_root),
        "session": (
            None
            if report.session is None
            else dataclasses.asdict(report.session)
        ),
        "refresh_lock": _lock_summary_to_dict(report.refresh_lock),
        "daemon": (
            None if report.daemon is None else dataclasses.asdict(report.daemon)
        ),
        "orphans": [dataclasses.asdict(o) for o in report.orphans],
        "findings": [_finding_to_dict(f) for f in report.findings],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _lock_summary_to_dict(lock: LockSummary) -> dict[str, Any]:
    """Hand-serialise :class:`LockSummary` so ``started_at`` becomes ISO."""
    return {
        "held": lock.held,
        "holder_pid": lock.holder_pid,
        "started_at": (
            lock.started_at.isoformat() if lock.started_at is not None else None
        ),
        "age_s": lock.age_s,
        "stuck": lock.stuck,
        "stuck_threshold_s": lock.stuck_threshold_s,
        "holder_host": lock.holder_host,
    }


def _finding_to_dict(finding: Finding) -> dict[str, Any]:
    """Serialise a :class:`Finding` to the shape in ``data-model.md`` §5."""
    payload: dict[str, Any] = {
        "id": finding.id,
        "severity": finding.severity,
        "summary": finding.summary,
    }
    if finding.remediation_command is not None or finding.remediation_description is not None:
        payload["remediation"] = {
            "command": finding.remediation_command,
            "description": finding.remediation_description,
        }
    else:
        payload["remediation"] = None
    return payload


# ---------------------------------------------------------------------------
# Orchestration entry point (T027)
# ---------------------------------------------------------------------------


def doctor_impl(
    *,
    json_output: bool,
    reset: bool,
    unstick_lock: bool,
    stuck_threshold: float,
    server: bool = False,
) -> int:
    """Top-level dispatch for the ``spec-kitty auth doctor`` command.

    Default invocation (no flags) is read-only: gather state, render, exit.

    ``--reset`` and ``--unstick-lock`` are independent (C-008) and run the
    underlying repair primitive only when the corresponding finding is
    present. After any repair we re-run :func:`assemble_report` so the
    rendered output reflects the post-repair state.

    ``--server`` is an explicit opt-in that refreshes the access token and
    calls ``GET /api/v1/session-status``. The default path (server=False)
    makes ZERO outbound network calls (C-007).
    """
    report = assemble_report(stuck_threshold_s=stuck_threshold)

    repair_messages: list[str] = []

    if reset:
        if any(f.id == "F-002" for f in report.findings):
            sweep = sweep_orphans(list(report.orphans))
            repair_messages.append(
                f"--reset: {len(sweep.swept)} orphan(s) swept, "
                f"{len(sweep.failed)} failed."
            )
            report = assemble_report(stuck_threshold_s=stuck_threshold)
        else:
            repair_messages.append("--reset: no orphans detected; no-op.")

    if unstick_lock:
        if any(f.id == "F-003" for f in report.findings):
            removed = force_release(
                _refresh_lock_path(), only_if_age_s=stuck_threshold
            )
            if removed:
                repair_messages.append("--unstick-lock: stuck lock released.")
            else:
                repair_messages.append(
                    "--unstick-lock: lock not removed (fresh, missing, or unreadable)."
                )
            report = assemble_report(stuck_threshold_s=stuck_threshold)
        else:
            repair_messages.append("--unstick-lock: lock not stuck; no-op.")

    server_status: ServerSessionStatus | None = None
    if server:
        server_status = asyncio.run(_check_server_session())

    if json_output:
        # Repair messages are not part of the JSON schema (`schema_version: 1`);
        # JSON consumers consume the post-repair report state directly.
        payload = json.loads(render_report_json(report))
        if server_status is not None:
            payload["server_session"] = {
                "active": server_status.active,
                "session_id": server_status.session_id,
                "error": server_status.error,
            }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return compute_exit_code(report.findings)

    render_report(report, console, show_server_hint=not server)
    for message in repair_messages:
        console.print(message)

    if server and server_status is not None:
        console.print("[bold]Server Session[/bold]")
        if server_status.active:
            sid = server_status.session_id or "(unknown)"
            console.print(f"  Status:  [green]active[/green] (session: {sid})")
        else:
            reason = server_status.error or "unknown"
            if reason == "re-authenticate":
                console.print(
                    "  Status:  [red]invalid[/red] — "
                    "Run [bold]spec-kitty auth login[/bold] to re-authenticate."
                )
            else:
                console.print(f"  Status:  [yellow]check failed[/yellow] — {reason}")
        console.print()

    return compute_exit_code(report.findings)
