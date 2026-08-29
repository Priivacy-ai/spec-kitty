"""Pure decision core for ``spec-kitty sync status`` (WP09).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``)
restructures the cc-90 ``status`` command from an *interleaved* gather-render —
where network + daemon I/O ran **between** row emissions — into a three-phase
``gather-all-I/O -> pure core -> render`` shell (architect finding A-1). This
module is the **pure core**: it receives the already-gathered facts
(:class:`StatusFacts`) and *decides* the display tuples plus the
identity-boundary verdict. It is **I/O-free** — no ``Console``, no ``print``, no
network, no filesystem, no SQLite. The reviewer co-gate greps this module for
``Console`` / ``print`` / ``scan_sync_daemons`` / ``_check_server_connection``;
any hit is a reject.

Two functions are the load-bearing extractions (each unit-tested against every
branch):

* :func:`build_status_rows` — the main status-table ``(label, value)`` rows
  (queue / SaaS / daemon / auth / server / ping / singleton), decided from the
  gathered connection + daemon + store facts.
* :func:`evaluate_boundary_coherence` — the ``--check`` identity-boundary gate.
  It does **not** re-implement boundary logic (DIRECTIVE_044): the caller feeds
  it the output of the canonical ``build_boundary_failure_set`` /
  ``_build_boundary_check_failures`` pair, and this function only *assembles* the
  final verdict (layering the auth-required, live-orphan, and scan-diagnostic
  lines exactly as the pre-restructure shell did) and decides the 0/2 exit code.

The remaining pure helpers (:func:`build_boundary_sections`,
:func:`build_orphan_detail_lines`, :func:`derive_auth_recovery_pending`) carry
the rest of the interleaved decision logic out of the shell so it measures
genuinely ``<= 15`` complexity with the ``# noqa: C901`` retired. The byte-stable
observable contract is guarded by the WP02 goldens
(``test_status_full_human_render_frozen`` + ``status --check`` arms).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kernel.clock import parse_iso

from specify_cli.auth.verdict import HealthVerdict
from specify_cli.core.saas_sync_config import SAAS_SYNC_ENV_VAR

# ---------------------------------------------------------------------------
# Display constants (canonical home; re-exported onto the ``sync`` host module
# so any ``sync.<CONST>`` access and the main-table / boundary rows share ONE
# source of truth — the WP06/WP07 relocation pattern).
# ---------------------------------------------------------------------------
_STATUS_LAST_SYNC_LABEL = "Last Sync"
_ABSENT_VALUE = "<absent>"
_UNSET_VALUE = "<unset>"
_ZERO_STATUS = "[green]0[/green]"
_BOUNDARY_LABEL_PACKAGE_VERSION = "  Package version"
_BOUNDARY_LABEL_EXECUTABLE_PATH = "  Executable path"
_BOUNDARY_LABEL_SOURCE_PATH = "  Source path"
_BOUNDARY_LABEL_SERVER_URL = "  Server URL"
_BOUNDARY_LABEL_TEAM_USER = "  Team/User"
_BOUNDARY_LABEL_QUEUE_DB_PATH = "  Queue DB path"
_MISMATCHED_FIELDS_LABEL = "Mismatched fields"


@dataclass(frozen=True)
class StatusRow:
    """A single ``(label, value)`` row of the main status table.

    ``value`` already carries any Rich markup; the render shell adds each row to
    an identically-configured ``Table`` so the output is byte-stable.
    """

    label: str
    value: str


@dataclass(frozen=True)
class BoundarySections:
    """Row data for the plain-text Identity Boundary block.

    Each section list is a list of ``(key, value)`` tuples emitted by
    ``_print_boundary_section`` on the host; ``mismatch_rows`` is
    ``(field, foreground_value, daemon_value)`` and drives the optional
    ``Mismatch Detail`` table.
    """

    foreground_rows: list[tuple[str, str]]
    daemon_rows: list[tuple[str, str]]
    active_queue_rows: list[tuple[str, str]]
    legacy_queue_rows: list[tuple[str, str]]
    top_level_rows: list[tuple[str, str]]
    mismatch_rows: list[tuple[str, str, str]]


@dataclass(frozen=True)
class StatusView:
    """The fully-decided, render-ready view produced from :class:`StatusFacts`."""

    main_rows: list[StatusRow]
    orphan_detail_lines: list[str]
    boundary: BoundarySections


@dataclass(frozen=True)
class BoundaryVerdict:
    """The ``--check`` identity-boundary gate outcome.

    ``failures`` is empty iff the boundary is coherent; ``exit_code`` is 0 when
    coherent and 2 otherwise (the pre-restructure ``raise typer.Exit(2)`` arm).
    """

    failures: list[str]
    exit_code: int


@dataclass(frozen=True)
class StatusFacts:
    """All facts gathered by the shell's up-front I/O phase.

    Host-owned duck-typed objects (``daemon_status``, ``failure_set``,
    ``daemon_record``, ``orphan_report``) are typed ``Any`` — every value read
    off them is absorbed into a correctly-typed ``str`` / ``int`` before it
    leaves the core, per the mypy-strict-quarantine guardrail.
    """

    check_connection: bool
    saas_enabled: bool
    server_url: str
    config_file: str
    queue_size: int
    body_queue_count: int
    auth_verdict: HealthVerdict
    daemon_status: Any
    connection_status: str | None
    connection_note: str | None
    orphan_report: Any
    orphan_scan_diagnostic: str | None
    failure_set: Any
    daemon_record: Any
    daemon_team_or_user: str | None
    daemon_mismatched: list[str]
    orphan_record_count: int
    legacy_db_path: str
    stranded_tag: str | None
    auth_recovery_pending: bool


def _queue_and_saas_rows(facts: StatusFacts) -> list[StatusRow]:
    """Queue-size + SaaS-sync feature-flag rows."""
    queue_color = "green" if facts.queue_size == 0 else "yellow"
    rows = [StatusRow("Queue", f"[{queue_color}]{facts.queue_size} event(s)[/{queue_color}]")]
    if facts.saas_enabled:
        rows.append(StatusRow("SaaS Sync", "[green]Enabled[/green]"))
    else:
        rows.append(StatusRow("SaaS Sync", f"[yellow]Disabled[/yellow] ({SAAS_SYNC_ENV_VAR}=1)"))
    return rows


def _daemon_rows(daemon_status: Any) -> list[StatusRow]:
    """Daemon / transport / last-sync / failure rows."""
    daemon_text = "[green]Running[/green]" if daemon_status.healthy else "[dim]Stopped[/dim]"
    rows = [StatusRow("Daemon", daemon_text)]
    if daemon_status.url:
        rows.append(StatusRow("Daemon URL", daemon_status.url))
    if daemon_status.pid is not None:
        rows.append(StatusRow("Daemon PID", str(daemon_status.pid)))
    if daemon_status.port is not None:
        rows.append(StatusRow("Daemon Port", str(daemon_status.port)))

    sync_mode = "[green]Global daemon[/green]" if daemon_status.sync_running else "[yellow]Queue only[/yellow]"
    rows.append(StatusRow("Sync Mode", sync_mode))
    websocket_color = "green" if daemon_status.websocket_status == "Connected" else "yellow"
    rows.append(StatusRow("WebSocket", f"[{websocket_color}]{daemon_status.websocket_status}[/{websocket_color}]"))

    if daemon_status.last_sync:
        try:
            parsed_sync_time = parse_iso(daemon_status.last_sync)
            rows.append(StatusRow(_STATUS_LAST_SYNC_LABEL, parsed_sync_time.strftime("%Y-%m-%d %H:%M:%S UTC")))
        except ValueError:
            rows.append(StatusRow(_STATUS_LAST_SYNC_LABEL, str(daemon_status.last_sync)))
    else:
        rows.append(StatusRow(_STATUS_LAST_SYNC_LABEL, "[dim]Never[/dim]"))

    if daemon_status.consecutive_failures > 0:
        rows.append(StatusRow("Failures", f"[yellow]{daemon_status.consecutive_failures} consecutive[/yellow]"))
    return rows


#: Colour per verdict state — the row can never read green while the verdict is
#: not ``ok`` (#3723 rule 3: the row is derived from the verdict, not asserted).
_VERDICT_COLOR: dict[str, str] = {"ok": "green", "unknown": "yellow", "fail": "red"}


def _auth_and_server_rows(facts: StatusFacts) -> list[StatusRow]:
    """Auth-state, resolved server URL, and config-file rows.

    The Auth row is rendered from ``facts.auth_verdict``: its headline is derived
    from the verdict state and always followed by the verdict's evidence, so the
    row can never claim ``Authenticated`` without naming why (#3723 rules 1 & 3).
    """
    if facts.saas_enabled:
        verdict = facts.auth_verdict
        color = _VERDICT_COLOR[verdict.state]
        auth_text = f"[{color}]{verdict.headline}[/{color}] ({verdict.evidence})"
    else:
        auth_text = "[dim]Disabled by feature flag[/dim]"
    return [
        StatusRow("Auth", auth_text),
        StatusRow(_BOUNDARY_LABEL_SERVER_URL.strip(), facts.server_url),
        StatusRow("Config File", facts.config_file),
    ]


def _connection_rows(facts: StatusFacts) -> list[StatusRow]:
    """Ping + singleton rows, emitted only under ``--check``.

    Mirrors the pre-restructure ``check_connection`` block: a live-scan failure
    surfaces the ``Singleton`` *Unavailable* row (from ``orphan_scan_diagnostic``);
    otherwise a successful scan surfaces the OK / orphan-count row.
    """
    if not facts.check_connection:
        return []
    rows = [StatusRow("Ping", facts.connection_status or "")]
    if facts.connection_note:
        rows.append(StatusRow("", f"[dim]{facts.connection_note}[/dim]"))
    if facts.orphan_scan_diagnostic is not None:
        rows.append(StatusRow("Singleton", f"[red]Unavailable[/red] ({facts.orphan_scan_diagnostic})"))
    elif facts.orphan_report is not None:
        if facts.orphan_report.orphan_count == 0:
            rows.append(StatusRow("Singleton", "[green]OK[/green] (no orphan daemons detected)"))
        else:
            rows.append(
                StatusRow("Singleton", f"[yellow]{facts.orphan_report.orphan_count} orphan daemon(s) detected[/yellow]")
            )
    return rows


def build_status_rows(facts: StatusFacts) -> list[StatusRow]:
    """Decide the full main status-table row set from the gathered facts.

    Row order (byte-stable vs the pre-restructure ``Table``): queue, SaaS,
    daemon block, auth / server / config, then — under ``--check`` — ping +
    singleton.
    """
    rows: list[StatusRow] = []
    rows.extend(_queue_and_saas_rows(facts))
    rows.extend(_daemon_rows(facts.daemon_status))
    rows.extend(_auth_and_server_rows(facts))
    rows.extend(_connection_rows(facts))
    return rows


def build_orphan_detail_lines(orphan_report: Any) -> list[str]:
    """Return the per-process ``PID ...`` detail lines for live orphan daemons.

    Empty when there is no report or no orphan process (the pre-restructure block
    only prints when ``orphan_count > 0``).
    """
    if orphan_report is None or orphan_report.orphan_count <= 0:
        return []
    return [f"  PID {orphan.pid}: {' '.join(orphan.cmdline)}" for orphan in orphan_report.orphan_processes]


def _foreground_boundary_rows(fg: Any) -> list[tuple[str, str]]:
    return [
        (_BOUNDARY_LABEL_PACKAGE_VERSION.strip(), str(fg.package_version or "-")),
        (_BOUNDARY_LABEL_EXECUTABLE_PATH.strip(), str(fg.executable_path or "-")),
        (_BOUNDARY_LABEL_SOURCE_PATH.strip(), str(fg.source_path or "-")),
        (_BOUNDARY_LABEL_SERVER_URL.strip(), fg.server_url if fg.server_url else _UNSET_VALUE),
        (_BOUNDARY_LABEL_TEAM_USER.strip(), fg.team_or_user if fg.team_or_user else _UNSET_VALUE),
        (_BOUNDARY_LABEL_QUEUE_DB_PATH.strip(), str(fg.queue_db_path or "-")),
    ]


def _daemon_boundary_rows(
    daemon_record: Any,
    daemon_status_label: str,
    daemon_team_or_user: str | None,
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [("Status", daemon_status_label)]
    if daemon_record is None:
        rows.extend(
            [
                ("PID", _ABSENT_VALUE),
                ("Port", _ABSENT_VALUE),
                (_BOUNDARY_LABEL_PACKAGE_VERSION.strip(), _ABSENT_VALUE),
                (_BOUNDARY_LABEL_EXECUTABLE_PATH.strip(), _ABSENT_VALUE),
                (_BOUNDARY_LABEL_SOURCE_PATH.strip(), _ABSENT_VALUE),
                (_BOUNDARY_LABEL_SERVER_URL.strip(), _ABSENT_VALUE),
                (_BOUNDARY_LABEL_TEAM_USER.strip(), _ABSENT_VALUE),
                (_BOUNDARY_LABEL_QUEUE_DB_PATH.strip(), _ABSENT_VALUE),
            ]
        )
    else:
        rows.extend(
            [
                ("PID", str(daemon_record.pid)),
                ("Port", str(daemon_record.port)),
                (_BOUNDARY_LABEL_PACKAGE_VERSION.strip(), daemon_record.package_version or _ABSENT_VALUE),
                (_BOUNDARY_LABEL_EXECUTABLE_PATH.strip(), daemon_record.executable_path or _ABSENT_VALUE),
                (_BOUNDARY_LABEL_SOURCE_PATH.strip(), daemon_record.source_checkout_path or _ABSENT_VALUE),
                (_BOUNDARY_LABEL_SERVER_URL.strip(), daemon_record.server_url or _ABSENT_VALUE),
                (
                    _BOUNDARY_LABEL_TEAM_USER.strip(),
                    daemon_team_or_user if daemon_team_or_user else _ABSENT_VALUE,
                ),
                (_BOUNDARY_LABEL_QUEUE_DB_PATH.strip(), daemon_record.queue_db_path or _ABSENT_VALUE),
            ]
        )
    return rows


def _mismatched_fields_value(failure_set: Any, daemon_mismatched: list[str]) -> str:
    if failure_set.mismatches:
        mismatch_field_names = [m.field for m in failure_set.mismatches]
        return f"[red]{', '.join(mismatch_field_names)}[/red]"
    if daemon_mismatched:
        return f"[red]{', '.join(daemon_mismatched)}[/red]"
    return "[green]none[/green]"


def build_boundary_sections(facts: StatusFacts) -> BoundarySections:
    """Decide every row of the plain-text Identity Boundary block (FR-005/FR-008).

    Pure assembly over the already-computed ``failure_set`` + gathered facts; the
    host's ``_print_boundary_section`` emits the returned rows verbatim.
    """
    failure_set = facts.failure_set
    fg = failure_set.foreground

    foreground_rows = _foreground_boundary_rows(fg)
    daemon_rows = _daemon_boundary_rows(facts.daemon_record, failure_set.daemon_status, facts.daemon_team_or_user)

    active_queue_rows: list[tuple[str, str]] = [
        ("Path", str(fg.queue_db_path or "-")),
        ("Event count", f"{facts.queue_size}"),
        ("Body upload cnt", f"{facts.body_queue_count}"),
    ]

    legacy_queue_rows: list[tuple[str, str]] = [
        ("Path", str(facts.legacy_db_path)),
        ("Event count", f"{failure_set.legacy_event_rows}"),
        ("Body upload cnt", f"{failure_set.legacy_body_upload_rows}"),
        ("Rows in scope", f"{failure_set.legacy_rows_for_scope}"),
    ]
    if facts.stranded_tag:
        legacy_queue_rows.append(("Stranded mission", f"setup-plan stranded mission slug {facts.stranded_tag}"))

    n_mismatches = len(failure_set.mismatches)
    mismatches_value = f"[red]{n_mismatches}[/red]" if n_mismatches else _ZERO_STATUS
    orphan_value = f"[yellow]{facts.orphan_record_count}[/yellow]" if facts.orphan_record_count else _ZERO_STATUS
    mismatched_fields_value = _mismatched_fields_value(failure_set, facts.daemon_mismatched)

    legacy_event_count = failure_set.legacy_event_rows
    legacy_body_count = failure_set.legacy_body_upload_rows
    legacy_line = f"{legacy_event_count} event(s), {legacy_body_count} body upload(s)"
    if facts.stranded_tag:
        legacy_line += f" — setup-plan stranded mission slug {facts.stranded_tag}"

    top_level_rows: list[tuple[str, str]] = [
        ("Mismatches", mismatches_value),
        ("Orphan records", orphan_value),
        ("Legacy queue rows", legacy_line),
        (_MISMATCHED_FIELDS_LABEL, mismatched_fields_value),
        ("Orphan daemon records", orphan_value),
    ]

    mismatch_rows: list[tuple[str, str, str]] = [
        (m.field, m.foreground_value or _UNSET_VALUE, m.daemon_value or _UNSET_VALUE) for m in failure_set.mismatches
    ]

    return BoundarySections(
        foreground_rows=foreground_rows,
        daemon_rows=daemon_rows,
        active_queue_rows=active_queue_rows,
        legacy_queue_rows=legacy_queue_rows,
        top_level_rows=top_level_rows,
        mismatch_rows=mismatch_rows,
    )


def build_status_view(facts: StatusFacts) -> StatusView:
    """Compose the render-ready :class:`StatusView` from the gathered facts."""
    return StatusView(
        main_rows=build_status_rows(facts),
        orphan_detail_lines=build_orphan_detail_lines(facts.orphan_report),
        boundary=build_boundary_sections(facts),
    )


def derive_auth_recovery_pending(connection_status: str | None) -> bool:
    """Whether the ``--check`` probe surfaced a recoverable auth-missing state.

    Mirrors the pre-restructure substring test on the ``Ping`` status string
    (issue #829): a not-authenticated / expired / failed probe schedules the
    teamspace-aware recovery offer once the table is rendered.
    """
    if not connection_status:
        return False
    return (
        "Not authenticated" in connection_status
        or "Session expired" in connection_status
        or "Authentication failed" in connection_status
    )


def evaluate_boundary_coherence(
    *,
    base_failures: list[str],
    auth_present: bool,
    auth_required: bool,
    orphan_count: int,
    orphan_scan_diagnostic: str | None,
) -> BoundaryVerdict:
    """Assemble the ``--check`` boundary verdict from canonical failure output.

    ``base_failures`` is the output of the canonical
    ``_build_boundary_check_failures`` (itself a renderer over
    ``build_boundary_failure_set``) — this function does **not** re-derive it
    (DIRECTIVE_044). It only layers the three environmental failure lines the
    pre-restructure shell added (auth-required, live orphan daemons, scan
    diagnostic) and decides the 0/2 exit code.
    """
    failures = list(base_failures)
    if auth_required and not auth_present:
        failures.append(
            "Hosted SaaS sync is enabled but no authenticated identity is available — run `spec-kitty auth login`."
        )
    if orphan_count > 0:
        failures.append(
            f"{orphan_count} live `run_sync_daemon` "
            "process(es) detected outside the registered singleton — "
            "run `spec-kitty sync doctor` for guided cleanup (#1071)."
        )
    if orphan_scan_diagnostic is not None:
        failures.append(orphan_scan_diagnostic + " — retry the scan or run `spec-kitty sync doctor`.")
    return BoundaryVerdict(failures=failures, exit_code=2 if failures else 0)


__all__ = [
    "BoundarySections",
    "BoundaryVerdict",
    "StatusFacts",
    "StatusRow",
    "StatusView",
    "build_status_view",
    "derive_auth_recovery_pending",
    "evaluate_boundary_coherence",
]
