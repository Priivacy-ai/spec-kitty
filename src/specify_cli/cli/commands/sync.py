"""Sync commands - workspace synchronization and connection status.

This module provides two groups of sync functionality:
1. Workspace sync: updates workspace with changes from base branch
2. Connection status: shows WebSocket sync connection state
"""

from __future__ import annotations

import contextlib
import logging
import re
import subprocess
from dataclasses import dataclass
from kernel.clock import UTC, now_utc, parse_iso, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import typer
from rich.console import Console
from specify_cli.cli.console import console as console
from rich.table import Table

if TYPE_CHECKING:
    from specify_cli.delivery.dispatcher import DispatchSummary
    from specify_cli.delivery.receivers import DeliveryReceiver
    from specify_cli.delivery.retention import ProjectPurgeResult
    from specify_cli.delivery.status_report import (
        PerProjectStoreReport,
        ProjectStoreRow,
    )
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.sync.history_import import UploadReport
    from specify_cli.sync.project_store import ProjectSyncStore
    from specify_cli.sync.target_authority import ResolvedSyncTarget

from specify_cli.cli.commands._auth_recovery import (
    EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE,
    RecoveryOutcome,
    handle_unauthenticated_with_teamspace,
)
from specify_cli.cli.commands._teamspace_mission_state_gate import (
    enforce_teamspace_mission_state_ready,
)
from specify_cli.core.vcs import (
    ChangeInfo,
    ConflictInfo,
    SyncResult,
    get_vcs,
)

from specify_cli.sync.queue import QueueStats
from specify_cli.sync.http_status import GATEWAY_STATUSES
from specify_cli.auth.config import EXAMPLE_HOSTED_SAAS_URL
from specify_cli.auth.session import (
    TeamSlugResolutionError,
    resolve_team_slug,
)
from specify_cli.core.saas_sync_config import saas_sync_opt_in_recorded_message
from kernel.clock import now_utc_iso
from specify_cli.sync.feature_flags import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled as is_saas_sync_enabled,
    saas_sync_disabled_message,
)
from specify_cli.tracker.egress_verdict import (
    EgressDestination,
    TrackerEgressVerdict,
    tracker_egress_verdict,
)


_LOG = logging.getLogger(__name__)

_STATUS_ACCESS_TOKEN_LABEL = "Access token"  # noqa: S105
_STATUS_REFRESH_TOKEN_LABEL = "Refresh token"  # noqa: S105
# WP09: ``_STATUS_LAST_SYNC_LABEL`` + the ``_BOUNDARY_LABEL_*`` / ``_ABSENT_VALUE``
# / ``_UNSET_VALUE`` / ``_ZERO_STATUS`` / ``_MISMATCHED_FIELDS_LABEL`` display
# constants moved to the pure ``specify_cli.sync.sync_status_core`` seam and are
# re-established as ``sync.<name>`` module attributes by the husk re-export block
# below (the WP06/WP07 relocation pattern).
# WP08: the ``sync now`` dispatch message constants and HTTP-413 markers moved to
# the pure ``specify_cli.sync.sync_dispatch_core`` seam (``_UNAUTHENTICATED_SYNC_NOW_MESSAGE``
# / ``_OVERSIZED_SYNC_NOW_MESSAGE`` / ``_TRANSIENT_SYNC_NOW_MESSAGE`` /
# ``_HTTP_PAYLOAD_TOO_LARGE`` / ``_OVERSIZED_ERROR_MARKER`` / ``_HTTP_AUTH_STATUSES``).
# They are re-established as ``sync.<name>`` module attributes by the husk
# re-export block below so ``_handle_sync_now_unauthenticated`` and the
# ``test_sync_routes`` message assertions still resolve them on this host.
_WARNING_HEADER_STYLE = "bold yellow"
_UNAVAILABLE_VALUE = "[dim]Unavailable[/dim]"


def _string_or(value: object | None, fallback: str) -> str:
    """Return *fallback* when *value* is falsey, otherwise coerce to ``str``."""
    return str(value) if value else fallback


def _depth_color(pct: float) -> str:
    """Return the Rich color token for a queue-depth percentage band.

    Single home for the depth->color mapping duplicated across the queue-health
    panel and the ``doctor`` render (S3358: collapses two byte-identical nested
    ternaries into one shared band lookup).
    """
    if pct >= 100:
        return "red"
    if pct >= 80:
        return "yellow"
    return "green"


def _override_label(value: bool | None) -> str:
    """Render a tri-state sync-override flag: unset / enabled / disabled.

    Flattens the nested ternary the routing table used for the local-override
    and repo-default rows (S3358); the values are byte-identical to the inline
    form it replaces.
    """
    if value is None:
        return "[dim]Not set[/dim]"
    return "enabled" if value else "disabled"


def _selector_kind(project: object | None, identity_less: bool) -> str:
    """Classify a purge/preview selector as project / identity-less / all.

    Flattens the nested ternary in the purge ``--report`` selector envelope
    (S3358); byte-identical to the inline expression it replaces.
    """
    if project is not None:
        return "project"
    return "identity-less" if identity_less else "all"


def _add_boundary_identity_rows(
    table: Table,
    rows: list[tuple[str, object | None]],
    *,
    fallback: str,
) -> None:
    """Render a flat sequence of key/value rows into the boundary table."""
    for label, value in rows:
        table.add_row(label, _string_or(value, fallback))


def _add_boundary_identity_row(
    table: Table,
    label: str,
    value: object | None,
    *,
    fallback: str,
) -> None:
    """Render a single key/value row into the boundary table."""
    table.add_row(label, _string_or(value, fallback))


def humanize_timedelta(td: timedelta) -> str:
    """Convert a timedelta into a concise human-readable string.

    Examples: '2s', '45s', '3m 12s', '2h 5m', '1d 4h', '3d'
    """

    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        return "0s"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days}d"
    if hours > 0:
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    if minutes > 0:
        if seconds > 0:
            return f"{minutes}m {seconds}s"
        return f"{minutes}m"
    return f"{seconds}s"


def _handle_sync_now_unauthenticated(strict: bool) -> None:
    """Route the unauthenticated/blocked ``sync now`` case through recovery.

    Teamspace-aware recovery: TTY operators get an interactive prompt, CI gets a
    structured stderr line + exit code 4. When no teamspace is detected
    (NO_TEAMSPACE / SKIPPED / QUIT) the behaviour is byte-identical to the legacy
    path — the operator message naming ``spec-kitty auth login`` is printed and
    the command exits 1 under ``--strict``.
    """
    outcome = handle_unauthenticated_with_teamspace(
        command_name="sync now",
        console=console,
    )
    if outcome is RecoveryOutcome.EXIT_4:
        raise typer.Exit(EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE)
    if outcome is RecoveryOutcome.LOGGED_IN:
        console.print("[green]Logged in.[/green] Re-run [bold]spec-kitty sync now[/bold] to continue.")
        return
    console.print(f"[yellow]{_UNAUTHENTICATED_SYNC_NOW_MESSAGE}[/yellow]")
    if strict:
        raise typer.Exit(1)


@dataclass(frozen=True)
class _IntentionalNoDelivery:
    """An explicit operator-selected mode that deliberately has no receiver."""

    summary: DispatchSummary


@dataclass(frozen=True)
class _AdmissionGatedNoDelivery:
    """A gate/admission block, carrying the REAL reason (#3620, Finding 2).

    Distinguishes "the receiver's gates refused" or "no ADMITTED delivery
    target" from a genuine 401/403 — see
    ``sync_dispatch_exec._run_event_sync_dispatch`` (the two gate branches)
    and ``sync_dispatch_core.SyncNowExitAction.ADMISSION_BLOCKED``. Without
    this marker the host cannot tell a gate/admission block apart from the
    legacy "nothing attempted" unauthenticated shape, and misreports it as
    "not authenticated" — exactly the bug this type exists to close.
    """

    summary: DispatchSummary
    reason: str


def _enforce_sync_now_exit_from_dispatch(
    strict: bool,
    queue_size: int,
    summary: DispatchSummary | None,
    *,
    retained_work_present: bool = False,
    intentional_no_delivery: bool = False,
    admission_gated: bool = False,
) -> None:
    """Apply the strict ``spec-kitty sync now`` exit contract to the dispatch outcome.

    WP08: this is now a **thin wrapper**. The branchy
    ``DispatchSummary → exit`` mapping — its former cc22 complexity concentration
    — is extracted verbatim into the pure, unit-tested
    :func:`specify_cli.sync.sync_dispatch_core.decide_sync_now_exit`, which
    returns a :class:`SyncNowExitAction` and performs no I/O. The only impure
    steps remain here: apply that decision by printing (``console.print``),
    routing through teamspace-aware recovery
    (:func:`_handle_sync_now_unauthenticated`), or ``raise typer.Exit``. Freezing
    the ``now`` exit-code contract (contract item 5) is now the decision core's
    responsibility; this wrapper is a stable dispatch over five outcomes.
    """
    action = decide_sync_now_exit(
        strict,
        queue_size,
        summary,
        retained_work_present=retained_work_present,
        intentional_no_delivery=intentional_no_delivery,
        admission_gated=admission_gated,
    )
    if action is SyncNowExitAction.NONE:
        return
    if action is SyncNowExitAction.EXIT_STRICT_FAILURE:
        raise typer.Exit(1)
    if action is SyncNowExitAction.ADMISSION_BLOCKED:
        # #3620 Finding 2: the real gate/admission reason was already printed
        # by the exec layer (_run_event_sync_dispatch). Honor --strict without
        # routing through _handle_sync_now_unauthenticated, which would print
        # the misleading "not authenticated" message for a problem that has
        # nothing to do with the local session.
        if strict:
            raise typer.Exit(1)
        return
    if action is SyncNowExitAction.HANDLE_UNAUTHENTICATED:
        _handle_sync_now_unauthenticated(strict)
        return
    # SyncNowExitAction.TRANSIENT_BLOCK: a wholesale-transient drain — print the
    # classified cause, then honor --strict. ``summary`` is never None on this arm
    # (the decision only returns it for a non-None summary with recorded rows).
    if summary is not None:
        console.print(f"[yellow]{_transient_block_message(summary)}[/yellow]")
    if strict:
        raise typer.Exit(1)


def _maybe_write_dispatch_report(report: Path | None, summary: DispatchSummary | None) -> None:
    """Persist a compact per-outcome event-sync report when ``--report`` is given.

    The destructive legacy offline-queue drain (which produced a per-event
    failure report) is gone, so ``--report`` now serialises the dispatcher's
    per-outcome counts — the observable surface of the single delivery path.
    """
    if report is None:
        return
    import json as _json

    now = now_utc_iso()
    if summary is None:
        data: dict[str, Any] = {
            "generated_at": now,
            "dispatched": False,
            "summary": {"total_events": 0, "synced": 0, "failed": 0},
            "failures": [],
        }
    else:
        data = {
            "generated_at": now,
            "dispatched": True,
            "selected": summary.selected,
            "delivered": summary.delivered,
            "duplicate": summary.duplicate,
            "pending": summary.pending,
            "rejected": summary.rejected,
            "transient": summary.transient,
            "terminal_failed": summary.terminal_failed,
            "summary": {
                "total_events": summary.selected,
                "synced": summary.delivered + summary.duplicate,
                "failed": summary.rejected + summary.transient + summary.terminal_failed,
                "selected": summary.selected,
                "delivered": summary.delivered,
                "duplicate": summary.duplicate,
                "pending": summary.pending,
                "rejected": summary.rejected,
                "transient": summary.transient,
                "terminal_failed": summary.terminal_failed,
            },
            "failures": [
                {
                    "event_id": failure.event_id,
                    "outcome": failure.outcome,
                    "http_status": failure.http_status,
                    "error": failure.error,
                }
                for failure in summary.failures
            ],
        }
    report.write_text(_json.dumps(data), encoding="utf-8")
    console.print(f"\n[cyan]Dispatch report written to {report}[/cyan]")


# --------------------------------------------------------------------------- #
# Event-sync wiring (WP12) — THIN glue over WP01/WP07/WP09/WP11 domain modules. #
# Every count/decision is owned by a domain module; this layer only resolves    #
# already-canonical handles and prints/serialises their results (plan IC-08).   #
# --------------------------------------------------------------------------- #

_EVENT_SYNC_DISPATCH_BATCH_LIMIT = 1000


@dataclass(frozen=True)
class _EventSyncScope:
    user_id: str | None = None
    team_slug: str | None = None


def _current_event_sync_scope() -> _EventSyncScope:
    """Resolve the producer scope used by live event capture."""
    try:
        from specify_cli.sync.emitter import EventEmitter

        team_slug = EventEmitter._current_team_slug()
    except Exception as exc:
        _LOG.debug("event-sync team scope unavailable: %s", exc)
        team_slug = None
    return _EventSyncScope(team_slug=team_slug)


def _event_sync_gate_context(receiver: DeliveryReceiver, target: ResolvedSyncTarget, *, auth_token: str) -> Any:
    """Build the explicit receiver-gate context for the active target."""
    from specify_cli.delivery.receivers import GateContext

    return GateContext(
        saas_enabled=is_saas_sync_enabled(),
        private_teamspace=bool(target.team_slug),
        auth_present=bool(auth_token),
        endpoint_configured=bool(getattr(receiver, "endpoint_url", "")),
    )


def _count_retained_events(runtime: _EventSyncRuntime) -> int:
    from specify_cli.event_journal.journal import EventJournal

    with runtime.store.unit_of_work() as unit:
        return int(EventJournal(unit, runtime.store.layout_generation()).count())


def _count_project_retained_events(runtime: _ProjectDispatchRuntime) -> int:
    from specify_cli.event_journal.journal import EventJournal

    with runtime.store.unit_of_work() as unit:
        return int(EventJournal(unit, runtime.store.layout_generation()).count())


def _event_sync_retained_work_present() -> bool:
    """Conservative retained-work probe for strict infrastructure failures."""
    runtime: _EventSyncRuntime | None = None
    try:
        runtime = _open_event_sync_runtime_readonly()
        return _count_retained_events(runtime) > 0
    except FileNotFoundError:
        return False
    except Exception:
        # Corrupt/unreadable/non-PROJECT_ONLY is unknown, never proof of empty.
        return True
    finally:
        if runtime is not None:
            runtime.close()


def _read_migration_conflicts_readonly() -> tuple[Any, ...]:
    """Read legacy conflict evidence without opening a writable audit store."""
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.migrate_journal import AUDIT_DB_NAME, read_migration_conflicts

    audit_path = get_runtime_root().base / AUDIT_DB_NAME
    try:
        return tuple(read_migration_conflicts(audit_path))
    except Exception as exc:  # read-only diagnostic; never fail status on it
        _LOG.debug("migration audit unavailable for status report: %s", exc)
        return ()


#: Opening words of the empty-selection diagnosis. One constant because three tests
#: and two surfaces key on it, and because "nothing was selected" has to be sayable
#: in words — ``(selected 0)`` inside a counts line is not a diagnosis.
_NOTHING_TO_DELIVER = "Nothing to deliver."


def _report_empty_selection(summary: DispatchSummary | None, journal: EventJournal) -> None:
    """Name the cause when a drain selected nothing (FR-005 / T005, SC-003's fifth path).

    Only fires on a genuinely empty selection. A drain that selected rows and failed
    to deliver them has its own reporting and its own exit contract; adding a cause
    line there would compete with a more specific message.

    Never raises: a diagnosis that breaks the command it is explaining would be worse
    than the silence it replaces.
    """
    if summary is None or summary.selected != 0:
        return
    from specify_cli.delivery.status_report import build_per_project_store_report

    try:
        report = build_per_project_store_report(journal)
    except Exception as exc:  # noqa: BLE001 — explanatory only, never fatal
        _LOG.debug("empty-selection diagnosis unavailable: %s", exc)
        console.print(
            f"[yellow]{_NOTHING_TO_DELIVER}[/yellow] The reason could not be "
            f"determined ({str(exc)[:80]}); `spec-kitty sync doctor` reports the "
            "journal's per-project state."
        )
        return
    console.print(f"[yellow]{_NOTHING_TO_DELIVER}[/yellow] {_empty_selection_cause(report)}")


def _print_dispatch_summary(summary: DispatchSummary, mode_name: str) -> None:
    """Render the dispatcher's per-outcome counts (sourced, never recomputed).

    When a protocol-mismatch 412 halted the pass (#1553) the server's own
    upgrade/pin guidance — carried on the summary's failure record — is printed
    right after the counts, so the command that hit the skew tells the operator
    what to do (not a later ``sync status`` they may never run).
    """
    from rich.markup import escape as _escape_markup  # noqa: PLC0415

    console.print(
        f"Event sync ([cyan]{mode_name}[/cyan]): "
        f"[green]delivered {summary.delivered}[/green]  "
        f"[dim]duplicate {summary.duplicate}[/dim]  "
        f"[yellow]pending {summary.pending}[/yellow]  "
        f"rejected {summary.rejected}  transient {summary.transient}  "
        f"[red]terminal-failed {summary.terminal_failed}[/red]  "
        f"(selected {summary.selected})"
    )
    guidance = _protocol_mismatch_guidance(summary)
    if guidance is not None:
        console.print(f"[yellow]{_PROTOCOL_MISMATCH_HALT_NOTICE} {_escape_markup(guidance)}[/yellow]")


# Create a Typer app for sync subcommands
app = typer.Typer(
    help="Synchronization commands",
    no_args_is_help=True,
)


def _require_active_checkout():
    from specify_cli.sync.routing import resolve_checkout_sync_routing

    routing = resolve_checkout_sync_routing()
    if routing is None:
        console.print("[red]Error:[/red] Could not locate the active Spec Kitty checkout.")
        raise typer.Exit(1)
    return routing


def _require_authenticated_session(command_name: str | None = None):
    """Return the active session or exit with appropriate recovery semantics.

    When ``command_name`` is provided and no session exists, this routes through
    ``handle_unauthenticated_with_teamspace`` so connected-teamspace repos get
    interactive recovery (TTY) or a structured stderr line + exit 4 (CI). When
    no teamspace is detected, behavior is byte-identical to the legacy path:
    the legacy red error is printed and the command exits with code 1.
    """
    from specify_cli.auth import get_token_manager

    session = get_token_manager().get_current_session()
    if session is not None:
        return session

    if command_name is not None:
        outcome = handle_unauthenticated_with_teamspace(
            command_name=command_name,
            console=console,
        )
        if outcome is RecoveryOutcome.EXIT_4:
            raise typer.Exit(EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE)
        if outcome is RecoveryOutcome.LOGGED_IN:
            # Re-resolve after a successful login.
            session = get_token_manager().get_current_session()
            if session is not None:
                return session
        # NO_TEAMSPACE / SKIPPED / QUIT all fall through to the legacy
        # exit-1 path below so existing CI and operator expectations are
        # preserved verbatim.

    console.print("[red]Error:[/red] Not authenticated. Run `spec-kitty auth login`.")
    raise typer.Exit(1)


def _private_team_name(session) -> str | None:
    for team in session.teams:
        if team.is_private_teamspace:
            return team.name
    return None


def _materialize_private_source_project() -> None:
    from specify_cli.sync.background import get_sync_service
    from specify_cli.sync.events import get_emitter

    event = get_emitter().emit_build_registered()
    if event is None:
        raise RuntimeError("Could not emit BuildRegistered for this checkout.")
    get_sync_service().sync_now()


_PER_PROJECT_SECTION_TITLE = "Event journal by project"
#: Shown for an unresolved-identity candidate that recorded NO name in any identity
#: column. One constant, because it has to mean exactly that on every surface: the
#: N1-a defect was this label appearing for rows that did carry a name, which makes
#: it untrustworthy precisely when it is the truth (legacy `sync migrate` imports).


def _oldest_age_label(created_at: str | None) -> str:
    """Render an ISO timestamp as an AGE, which is what FR-015 asks an operator for.

    "2026-06-01T00:00:00+00:00" tells an operator nothing about how long a
    project's payloads have been sitting there; "58d ago" does. An unparseable
    value degrades to the raw string rather than to ``n/a`` — losing the only
    timestamp we have would hide the row's age entirely.
    """
    if not created_at:
        return "[dim]n/a[/dim]"
    try:
        parsed = parse_iso(created_at)
    except ValueError:
        return created_at
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return f"{humanize_timedelta(now_utc() - parsed)} ago"


def _project_store_label(row: ProjectStoreRow) -> str:
    """The name an operator recognises, and — load-bearingly — one they can act on.

    ``repo_slug`` leads because it is the name an operator recognises: it is the
    repository in front of them, where ``project_slug`` is a derived form and the
    uuid is unrecognisable. ``project_slug`` is the fallback; the uuid is the last
    resort. The unresolved-identity bucket is labelled as such rather than rendering
    blank — FR-011 exists so that denial is visible.

    **It is not the case that anything is "keyed on" ``repo_slug``.** Consent records
    are keyed on ``project_uuid`` (see :func:`sync.consent.set_project_consent`), and
    ``sync purge --project`` used to key on ``project_slug`` alone — so the earlier
    version of this docstring justified the ordering with a claim that was false on
    both halves, and the report printed names that ``sync purge`` then refused. What
    makes the ordering correct is enforced elsewhere instead of asserted here:
    :func:`_purge_resolve_project` accepts every name in this chain, and
    ``tests/cli/commands/test_sync_report_label_is_a_purge_selector_3030.py`` feeds
    this function's own output to that resolver. Change either end and that pin reds.
    """
    if row.is_unresolved_identity:
        return "[yellow]<identity unresolved>[/yellow]"
    return row.repo_slug or row.project_slug or row.project_uuid or "?"


def _per_project_store_table(report: PerProjectStoreReport) -> Table:
    """The count / oldest-age / consent-state grid FR-015 and SC-004 ask for.

    Folds, never ellipsizes. Rich truncates an over-wide cell by default, and a
    truncated project identity would satisfy the layout while breaking SC-004's
    "names every project" — the operator would be shown a prefix they cannot pass
    to ``sync purge``.
    """
    from specify_cli.delivery.status_report import unresolved_candidate_name

    table = Table(show_header=True, box=None)
    table.add_column("Project", style="dim", overflow="fold")
    table.add_column("Events", justify="right")
    table.add_column("Oldest", overflow="fold")
    table.add_column("Consent", overflow="fold")
    for row in report.rows:
        state = "[green]consented[/green]" if row.consent_granted else f"[red]denied[/red] [dim]({row.consent_level})[/dim]"
        table.add_row(
            _project_store_label(row),
            f"{row.event_count:,}",
            _oldest_age_label(row.oldest_created_at),
            state,
        )
        # The unresolved bucket spans projects, so it gets a sub-row per RECORDED
        # IDENTITY — see `_unresolved_identity_candidates` for why the key is the
        # (repo_slug, project_slug) pair and not the repo slug alone. This is what
        # makes SC-004's "names every project present with count, oldest age and
        # consent state" hold for this population — previously the bucket rendered as
        # one anonymous line and the projects behind it were reachable only by
        # hand-querying SQLite. Consent reads "unknown", not "denied": without a
        # uuid there is nothing to resolve, and claiming a refusal here is the N1
        # false fact.
        for candidate in row.unresolved_candidates:
            name = unresolved_candidate_name(candidate)
            table.add_row(
                f"  [dim]└[/dim] {name or f'[dim]{_NO_RECORDED_NAME}[/dim]'}",
                f"{candidate.event_count:,}",
                _oldest_age_label(candidate.oldest_created_at),
                "[yellow]unknown[/yellow] [dim](identity unresolved)[/dim]",
            )
    return table


# --------------------------------------------------------------------------- #
# Consent-record readability (#3030 FR-020 / FR-027, SC-004)                    #
#                                                                              #
# FR-020 exists because a machine fault read as an ABSENCE: an unreadable       #
# `config.toml` made every project on the machine resolve as never-opted-in,    #
# the drain delivered nothing, doctor looked idle, and the operator was told to #
# record consent they had already recorded. `consent_index_health()` and        #
# `project_local_consent_fault()` keep that distinction alive — and until now   #
# nothing rendered either of them, which SC-004's own note records as owed.     #
# --------------------------------------------------------------------------- #


@contextlib.contextmanager
def _reporting_a_refused_config_write(what: str):
    """Turn a refused write into an actionable message instead of a traceback.

    ``SyncConfig`` refuses to write over a config it cannot read, because the write is
    a whole-file read-modify-write that would rebuild the file from an empty document
    and discard every consent record it holds (#3030). That refusal is a
    ``ConfigNotReadableError``, and FR-023's recorded lesson applies to it directly: *a
    new exception nobody catches is a crash moved, not fixed*, so every caller that
    assumed the write could not raise is audited.

    Three commands write with no handler of their own — ``sync opt-in``,
    ``sync opt-out`` and ``sync server`` — and ``opt-in`` is exactly the command an
    operator reaches for after ``sync doctor`` reports consent as undetermined.
    Measured before this wrapper: exit 1 with **no output at all**, which would have
    replaced one unhelpful answer with another on the path this mission exists to make
    honest.

    The exception's own message already names the file, the kind and the underlying
    error, so it is printed rather than paraphrased — a second wording here is how the
    refusal and the doctor start describing one fault differently (C-003).
    """
    from specify_cli.sync.config import ConfigNotReadableError

    try:
        yield
    except ConfigNotReadableError as exc:
        console.print(f"[red]Error:[/red] {what} was not recorded. {exc}")
        console.print("[dim]Nothing was changed and no records were lost. Run 'spec-kitty sync doctor' for the full consent-readability report.[/dim]")
        raise typer.Exit(1) from exc


_CONSENT_HEALTH_SECTION_TITLE = "Consent record readability"

#: Why one broken file denies more than its own project, and why that is nonetheless
#: a self-inflicted local fault rather than a sibling checkout's doing. Both halves
#: are owed: the first alone would let an operator conclude an unrelated project broke
#: their machine, and the second alone would understate what is currently denied.
_CONSENT_FAULT_REACH = (
    "A read fault cannot be attributed to a project — an unreadable file does not "
    "disclose which project it declares — so while it stands it denies for every "
    "project resolved through this checkout, not only this one. Its reach is narrower "
    "than that sounds: every production caller offers exactly one checkout root, the "
    "current directory's, so the broken file is this checkout's own and no sibling "
    "checkout can have caused it."
)


def _render_consent_fault(
    console_out: Any,
    issues: list[str],
    *,
    scope: str,
    fault: Any,
    consequence: str,
) -> None:
    """Render one fault as an action, a consequence and its own detail.

    The ``issues`` entry and the printed block are built from the same three strings,
    so doctor's summary and this section cannot say different things about one fault.
    """
    view = consent_fault_view(scope=scope, fault=fault, consequence=consequence)

    console_out.print(f"  {scope}  [red]{view.status}[/red] ({view.kind})")
    console_out.print(f"    [bold red]{view.action}[/bold red] — {view.remedy}")
    console_out.print(f"    [dim]{view.detail}[/dim]")
    console_out.print(f"    {view.consequence}")
    console_out.print(f"    [yellow]{_CONSENT_FAULT_NOT_ABSENCE}[/yellow]")
    issues.append(view.issue)


def _render_consent_readability(console_out: Any, issues: list[str]) -> None:
    """Say whether the consent records can be read at all (SC-004, FR-020/FR-027).

    Both surfaces, always printed. "Consent is fine", "I could not read it" and "I
    never looked" must not render identically — that equivalence *is* the incident's
    false-green, and a section that appears only on failure rebuilds it. The healthy
    line also states that a missing record is not a fault, so an operator does not
    set out to repair a file that is simply empty.

    Deliberately reporting only. ``consent_index_health`` is not consulted by
    ``resolve_project_consent`` (a pre-flight readability check followed by a separate
    per-project read is two reads that can disagree), and nothing here changes what
    the drain decides.
    """
    console_out.print(f"\n[bold]{_CONSENT_HEALTH_SECTION_TITLE}[/bold]")

    from specify_cli.core.paths import locate_project_root

    try:
        from specify_cli.sync.consent import consent_index_health

        health = consent_index_health()
    except Exception as exc:  # noqa: BLE001 — a section that vanishes is the defect
        console_out.print(f"  [yellow]![/yellow] the machine-global consent index could not be inspected: {exc}")
        issues.append(
            f"Whether the machine-global consent index is readable could not be "
            f"determined: {exc}. Until it is, treat every consent state reported above "
            "as unproven."
        )
    else:
        if health.fault is None:
            console_out.print("  machine-global consent index  [green]readable[/green]")
        else:
            _render_consent_fault(
                console_out,
                issues,
                scope="machine-global consent index",
                fault=health.fault,
                consequence=("Every project on this machine resolves as UNDETERMINED while this stands, so nothing is delivered."),
            )

    try:
        from specify_cli.sync.consent import project_local_consent_fault

        repo_root = locate_project_root(Path.cwd())
        local_fault = None if repo_root is None else project_local_consent_fault(repo_root)
    except Exception as exc:  # noqa: BLE001 — reported, never silently skipped
        console_out.print(f"  [yellow]![/yellow] this checkout's project config could not be inspected: {exc}")
        issues.append(f"Whether this checkout's own consent record is readable could not be determined: {exc}.")
    else:
        if repo_root is None:
            console_out.print("  this checkout  [dim]not inspected — no Spec Kitty checkout resolved from the current directory[/dim]")
        elif local_fault is None:
            console_out.print("  this checkout  [green]readable[/green]")
        else:
            _render_consent_fault(
                console_out,
                issues,
                scope="this checkout's project config",
                fault=local_fault,
                consequence=_CONSENT_FAULT_REACH,
            )

    console_out.print("  [dim]A missing record is not a fault: it means no consent was recorded, which denies.[/dim]")


_TRACKER_EGRESS_SECTION_TITLE = "Tracker egress"


def _render_tracker_egress_row(
    console_out: Any,
    issues: list[str],
    verdict: TrackerEgressVerdict,
    *,
    binding_present: bool,
) -> None:
    """Render one :class:`EgressDestination` row from an already-computed *verdict*.

    ``binding_present`` gates the ``issues`` append **only** -- never what is printed.
    Both rows always render, including their REFUSED verb, because "tracker egress is
    fine" and "I never looked" must stay distinguishable. But ``issues`` drives
    ``doctor``'s problem summary, and a checkout with **no tracker bound at all** has
    no tracker-egress problem to remediate: absence of both channels refuses a
    transmission nothing is attempting. Reporting it as an issue told every unbound
    project that something was wrong with it, and made this renderer's contribution
    depend on ambient state -- which is how it broke ``test_doctor_healthy``, a
    heavily-mocked unit test that nonetheless resolves the real checkout.

    This reads whether *any* provider is bound, never *which* one, so it does not
    reintroduce the provider-conditional reporting the enclosing renderer's docstring
    forbids: neither destination row is suppressed or altered by it.

    Takes no ``root`` and calls neither :func:`tracker_egress_verdict` nor
    ``load_tracker_config`` -- the two literal verdict calls live in
    :func:`_render_tracker_egress` alone, so this helper does not become a sixth
    enclosing function for WP07's guard G4. Every field printed is read off
    *verdict* and nothing is re-derived or re-classified locally (FR-003): the
    enforced answer and the reported answer are the same object.

    ``verdict.message`` is escaped with :func:`rich.markup.escape` before it reaches
    either ``console_out.print`` here or the ``issues`` entry below (review round 1,
    HIGH-1). C-020 requires it to embed the operator's own ``tracker.egress`` value
    **verbatim** (``repr(raw)``, so it can legally contain ``[`` / ``]``), and this
    is a ``rich`` surface: an unescaped ``'[refused]'`` is read back as a colour tag
    and silently erased (C-020's "verbatim" becomes a false statement about the
    operator's own file), and an unescaped ``'[/bold]'`` is an unmatched closing tag
    that raises ``MarkupError`` out of ``doctor`` entirely -- the exact "reported
    healthy, discover the refusal only by running the failing command" gap FR-014
    exists to close, now reachable through the diagnostic itself. The ``issues``
    entry needs its own escape, not a shared one: it is re-rendered through markup a
    second time, independently, in ``doctor()``'s own summary loop.
    """
    from rich.markup import escape as _escape_markup  # noqa: PLC0415

    verb, colour = ("REFUSED", "red") if verdict.refused else ("permitted", "green")
    console_out.print(f"  {verdict.destination.value}  [{colour}]{verb}[/{colour}]")
    if verdict.refusing_channels:
        channels = ", ".join(sorted(verdict.refusing_channels))
        console_out.print(f"    refusing channel(s): {channels}")
    state_wording = channel1_state_wording(verdict.channel1_state)
    console_out.print(f"    Channel 1: {state_wording}")
    safe_message = _escape_markup(verdict.message)
    console_out.print(f"    {safe_message}")
    for remedy in verdict.remedies:
        console_out.print(f"    remedy: {remedy}")
    row_issue = tracker_egress_row_issue(
        destination_value=verdict.destination.value,
        state_wording=state_wording,
        safe_message=safe_message,
        refused=verdict.refused,
        binding_present=binding_present,
    )
    if row_issue is not None:
        issues.append(row_issue)


def _render_tracker_egress(
    console_out: Any,
    issues: list[str],
    local: TrackerEgressVerdict,
    hosted: TrackerEgressVerdict,
    binding_present: bool,
) -> None:
    """Report the tracker-egress verdict the gates enforce (#3108 FR-014, SC-014).

    One row per :class:`EgressDestination` member -- two rows, always, in every
    checkout, printed unconditionally including the fully-permitted case.
    "Tracker egress is fine" and "I never looked" must not render identically --
    that equivalence is the 2026-07-27 incident's own false-green, and a block
    that only appears on refusal rebuilds it.

    Deliberately beside :func:`_render_consent_readability`, not inside it and
    never routed through :func:`_render_consent_fault`: that helper's contract is
    a *readability* fault over a fixed, pinned kind vocabulary
    (``CONFIG_FAULT_KINDS``, not extended here), and a tracker-egress verdict is
    not a readability fault -- forcing it through that renderer discards the
    refusal text, or announces a correct file as ``UNREADABLE``, or prints
    ``_CONSENT_FAULT_NOT_ABSENCE`` unconditionally, which is false for most of
    this verdict's own states.

    Consumes the ``local``/``hosted`` verdicts and ``binding_present`` already
    computed by :func:`_gather_doctor_facts` (the WP10 gather half) rather than
    recomputing them here. The gate that bounds tracker data-egress verdicts to a
    fixed inventory of call sites (#3108 zero-blast-radius) admits exactly the two
    gather calls; a second, duplicate ``tracker_egress_verdict`` computation in
    this render half both doubled that inventory and read the on-disk tracker
    provider twice in one ``doctor`` run. Those gather calls pass an identical root
    (``locate_project_root(Path.cwd())``) and identical per-transport identifier
    kinds, each with a literal :class:`EgressDestination` member -- never a loop
    over the enum, which would turn ``destination`` into an ``ast.Name`` and red
    WP07's guard G5 -- so the rows this renderer prints are byte-for-byte what the
    old in-place calls produced. ``root=None`` is a specified case, not an error
    path (the verdict function never raises): the gather passes it straight through
    to both destinations, so a directory that resolves no checkout is still
    rendered here, never as if its tracker egress were fine.

    ``binding_present`` -- whether *any* provider is bound, never which one -- gates
    the ``issues`` append only; both rows render regardless. It, too, is resolved
    once in the gather, where the ``load_tracker_config`` read is guarded (that
    config read RAISES on an unparseable ``.kittify/config.yaml``, and ``doctor``
    must stay useful on exactly that checkout).
    """
    console_out.print(f"\n[bold]{_TRACKER_EGRESS_SECTION_TITLE}[/bold]")
    _render_tracker_egress_row(console_out, issues, local, binding_present=binding_present)
    _render_tracker_egress_row(console_out, issues, hosted, binding_present=binding_present)


def _run_consent_index_backfill() -> None:
    """Map path-keyed consent records onto the uuid index (#3030 H4, T016).

    Opt-in via ``sync migrate --backfill-consent-index``, and gated for a specific
    reason rather than caution: the uuid index is consulted at level 2, ABOVE the
    repo default at level 3, so moving a path record into it can change a project's
    effective answer — a project currently denied by a repo default becomes granted.
    A migration that silently flipped delivery on is precisely the invisible consent
    change this mission exists to eliminate, so the operator asks for it and every
    change is named.

    Also the only surface on which WP07's ``unresolved``-consent rows are reachable:
    the result object carries the entries whose checkout no longer resolves to a
    uuid, which is US2 scenario 3's "consented but unresolvable" population.
    """
    from specify_cli.sync.consent import backfill_uuid_consent_index

    console.print()
    console.print("[bold]Consent index backfill[/bold]")
    try:
        result = backfill_uuid_consent_index()
    except Exception as exc:  # noqa: BLE001 — reported, never fatal to the migration
        console.print(f"  [yellow]![/yellow] could not be completed: {exc}. Path-keyed records remain in place and the drain still cannot see them.")
        return

    console.print(f"  mapped {result.mapped}  unresolved {result.unresolved}")
    if result.mapped:
        console.print("  [dim]Consent for these projects is now visible to the drain's uuid-keyed lookup:[/dim]")
        from specify_cli.sync.config import SyncConfig

        for uuid, granted in sorted(SyncConfig().get_all_project_consent().items()):
            state = "[green]consented[/green]" if granted else "[red]opted out[/red]"
            console.print(f"    {uuid}  {state}")
    for entry in result.unresolved_entries:
        # US2 scenario 3: the decision is retained, but the predicate cannot see
        # it, so reported state must not imply it is enforced.
        state = "consented" if entry.enabled else "opted out"
        console.print(
            f"  [yellow]unresolved[/yellow] {entry.path} [dim]({state} here, but "
            "this checkout no longer declares a project uuid, so the drain cannot "
            "apply it)[/dim]"
        )


def _render_migrated_composition(journal: EventJournal, imported_event_ids: list[str]) -> None:
    """Report the per-project composition of what ``sync migrate`` just MOVED (FR-015).

    `sync migrate` is the command that produced the incident's false-green: it
    emptied the legacy queue `doctor` reads while pooling every project's payloads
    into one journal, and it printed only aggregate import/dedupe counts — so the
    operator was never once told *whose* events had just been lifted into a
    machine-global store.

    Restricted to the ids this run imported rather than the whole journal: "what I
    moved" and "what is in here" are different claims, and reporting the latter
    under the former's heading would overstate the migration. Grouping is the same
    WP07 report the other two surfaces use (C-003), so the three cannot disagree.
    """
    from specify_cli.delivery.status_report import build_per_project_store_report

    console.print()
    console.print("[bold]Migrated events by project[/bold]")
    if not imported_event_ids:
        console.print("  [dim]nothing imported on this run[/dim]")
        return
    try:
        report = build_per_project_store_report(journal, event_ids=imported_event_ids)
    except Exception as exc:
        # Named, not swallowed: a migration whose composition cannot be read is a
        # migration whose confidentiality impact is unknown.
        console.print(f"  [yellow]![/yellow] imported {len(imported_event_ids)} event(s) but their per-project composition could not be read: {exc}")
        return
    console.print(_per_project_store_table(report))
    for issue in _per_project_store_issues(report):
        console.print(f"  [yellow]![/yellow] {issue}")


@app.command()
def routes() -> None:
    """Show where the current checkout sends data and which teams it is shared with."""
    from specify_cli.sync.routing import resolve_checkout_sync_routing
    from specify_cli.sync.sharing_client import (
        RepositorySharingClientError,
        list_repository_shares_sync,
    )

    routing = resolve_checkout_sync_routing()
    if routing is None:
        console.print("[red]Error:[/red] Could not locate the active Spec Kitty checkout.")
        raise typer.Exit(1)

    console.print()
    console.print("[cyan]Spec Kitty Teamspace Routing[/cyan]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")
    table.add_row("Repository", routing.repo_slug or _UNAVAILABLE_VALUE)
    table.add_row("Project UUID", routing.project_uuid or _UNAVAILABLE_VALUE)
    table.add_row("Project Slug", routing.project_slug or _UNAVAILABLE_VALUE)
    table.add_row("Build ID", routing.build_id or _UNAVAILABLE_VALUE)
    table.add_row(
        "Checkout Sync",
        "[green]Enabled[/green]" if routing.effective_sync_enabled else "[yellow]Disabled[/yellow]",
    )

    local_value = _override_label(routing.local_sync_enabled)
    table.add_row("Local Override", local_value)

    repo_default = _override_label(routing.repo_default_sync_enabled)
    table.add_row("Future Repo Default", repo_default)

    try:
        session = _require_authenticated_session(command_name="sync routes")
    except typer.Exit as exc:
        if exc.exit_code != 0:
            raise
        console.print(table)
        console.print()
        return

    private_team_name = _private_team_name(session)
    if private_team_name:
        table.add_row("Private Teamspace", private_team_name)

    console.print(table)
    console.print()

    if not is_saas_sync_enabled():
        console.print(f"[yellow]{saas_sync_disabled_message()}[/yellow]")
        console.print()
        return
    if routing.project_uuid is None:
        console.print("[dim]No project UUID for this checkout. Run `spec-kitty init` first.[/dim]")
        console.print()
        return

    enforce_teamspace_mission_state_ready(
        console=console,
        command_name="spec-kitty sync routes",
    )

    try:
        shares = list_repository_shares_sync(source_project_uuid=routing.project_uuid)
    except RepositorySharingClientError as exc:
        console.print(f"[yellow]Could not load share state:[/yellow] {exc}")
        console.print()
        return

    if not shares:
        console.print("[dim]No team shares for this checkout yet.[/dim]")
        console.print()
        return

    shares_table = Table(show_header=True, header_style="bold")
    shares_table.add_column("Team", style="cyan")
    shares_table.add_column("State")
    shares_table.add_column("Sharers", justify="right")
    shares_table.add_column("Project", style="dim")

    for share in shares:
        team = share.get("team") or {}
        shared_project = share.get("shared_project") or {}
        shares_table.add_row(
            str(team.get("name") or team.get("slug") or "Unknown"),
            str(share.get("state") or "unknown"),
            str(share.get("active_sharer_count") or 0),
            str(shared_project.get("project_slug") or "pending"),
        )

    console.print(shares_table)
    console.print()


def _report_team_resolution_error(exc: TeamSlugResolutionError) -> None:
    """Print an actionable recovery message for an unresolved ``sync share`` team.

    Fail-closed rendering for :class:`TeamSlugResolutionError`: the user is told
    why the handle did not resolve and shown the exact slugs they can share into
    (``spec-kitty auth status`` displays the same slugs).
    """
    if exc.reason == "not_shareable":
        console.print(
            f"[red]Error:[/red] Team '{exc.token}' is a private teamspace and "
            "cannot be a share destination."
        )
    elif exc.reason == "ambiguous":
        console.print(
            f"[red]Error:[/red] Team name '{exc.token}' is ambiguous. "
            "Pass the team slug instead."
        )
    else:
        console.print(f"[red]Error:[/red] Unknown team '{exc.token}'.")

    if exc.shareable:
        console.print("  Shareable teams:")
        for team in exc.shareable:
            console.print(f"    - {team.name} [dim]slug: {team.slug}[/dim]")
    else:
        console.print("  No shareable teams are available for this account.")


@app.command()
def share(
    team_slug: str = typer.Argument(
        ...,
        help="Team name or slug to share this repository into "
        "(see `spec-kitty auth status`).",
    ),
) -> None:
    """Share the current repository from Private Teamspace into a team."""
    from specify_cli.sync.sharing_client import RepositorySharingClientError

    _require_daemon_owner_coherence("spec-kitty sync share")

    if not is_saas_sync_enabled():
        console.print(f"[red]{saas_sync_disabled_message()}[/red]")
        raise typer.Exit(1)

    enforce_teamspace_mission_state_ready(
        console=console,
        command_name="spec-kitty sync share",
    )

    routing = _require_active_checkout()
    session = _require_authenticated_session(command_name="sync share")

    try:
        destination_slug = resolve_team_slug(session.teams, team_slug)
    except TeamSlugResolutionError as exc:
        _report_team_resolution_error(exc)
        raise typer.Exit(1) from exc

    if routing.project_uuid is None:
        console.print("[red]Error:[/red] Current checkout has no project UUID. Run `spec-kitty init` first.")
        raise typer.Exit(1)

    # The 404 self-heal (#3564) materializes this checkout in Private Teamspace
    # and retries. The retry can still 404 for a few seconds until the newly
    # emitted BuildRegistered is visible server-side (#3699); that recoverable
    # race must reach the operator as an actionable line, not a raw traceback.
    # The outer ``finally`` runs deterministic teardown on every exit path so a
    # clean ``typer.Exit`` — not an aborted stack unwind — drives the WebSocket
    # disconnect, removing the "Task was destroyed but it is pending!" symptom.
    try:
        try:
            response = request_repository_share(
                source_project_uuid=routing.project_uuid,
                destination_team_slug=destination_slug,
            )
        except RepositorySharingClientError as exc:
            if exc.status_code == 404:
                if not routing.effective_sync_enabled:
                    console.print("[red]Error:[/red] This checkout is opted out of SaaS sync. Run `spec-kitty sync opt-in` first.")
                    raise typer.Exit(1) from None
                try:
                    _materialize_private_source_project()
                except Exception as materialize_error:
                    console.print(f"[red]Error:[/red] Could not materialize this checkout in Private Teamspace: {materialize_error}")
                    raise typer.Exit(1) from materialize_error
                try:
                    response = request_repository_share(
                        source_project_uuid=routing.project_uuid,
                        destination_team_slug=destination_slug,
                    )
                except RepositorySharingClientError as retry_exc:
                    console.print(
                        "[yellow]Registering this project in Private Teamspace.[/yellow] "
                        f"Run [bold]spec-kitty sync share {team_slug}[/bold] again in a moment."
                    )
                    raise typer.Exit(1) from retry_exc
            else:
                console.print(f"[red]Error:[/red] {exc}")
                raise typer.Exit(1) from exc

        share_data = response.get("share") or {}
        share_state = share_data.get("state", "unknown")
        repo_label = routing.repo_slug or routing.project_slug or routing.project_uuid
        if share_state == "shared":
            console.print(f"[green]✓[/green] Shared [cyan]{repo_label}[/cyan] to [cyan]{destination_slug}[/cyan].")
        else:
            console.print(f"[yellow]✓[/yellow] Share request recorded for [cyan]{destination_slug}[/cyan].")

        if response.get("auto_approved"):
            console.print("[dim]Team policy auto-approved the repository share.[/dim]")
        elif share_state == "pending_approval":
            console.print("[dim]Waiting for a team admin to approve the repository.[/dim]")
    finally:
        from specify_cli.sync.runtime import get_runtime

        # Idempotent (no-op when nothing started); awaits the WebSocket
        # disconnect synchronously via ``SyncRuntime.stop`` so teardown never
        # races the interpreter exit. Suppress teardown errors so they can't
        # mask the command's own exit status.
        with contextlib.suppress(Exception):
            get_runtime().stop()


@app.command()
def unshare(
    team_slug: str = typer.Argument(..., help="Team slug to stop sharing this repository into."),
) -> None:
    """Stop sharing the current repository from this developer to one team."""
    from specify_cli.sync.sharing_client import RepositorySharingClientError

    _require_daemon_owner_coherence("spec-kitty sync unshare")

    if not is_saas_sync_enabled():
        console.print(f"[red]{saas_sync_disabled_message()}[/red]")
        raise typer.Exit(1)

    enforce_teamspace_mission_state_ready(
        console=console,
        command_name="spec-kitty sync unshare",
    )

    routing = _require_active_checkout()
    _require_authenticated_session(command_name="sync unshare")

    if routing.project_uuid is None:
        console.print("[red]Error:[/red] Current checkout has no project UUID.")
        raise typer.Exit(1)

    try:
        leave_repository_share(
            source_project_uuid=routing.project_uuid,
            destination_team_slug=team_slug,
        )
    except RepositorySharingClientError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(
        f"[green]✓[/green] Stopped sharing [cyan]{routing.repo_slug or routing.project_slug or routing.project_uuid}[/cyan] "
        f"to [cyan]{team_slug}[/cyan] from this developer."
    )
    console.print("[dim]Private Teamspace data was kept intact.[/dim]")


@app.command(name="opt-out")
def opt_out(
    checkout_only: bool = typer.Option(
        False,
        "--checkout-only",
        help="Disable only this checkout; do not remember the repo default for future checkouts.",
    ),
    delete_private_data: bool = typer.Option(
        False,
        "--delete-private-data",
        help="After disabling sync, offer to delete already-synced private-only SaaS data for this checkout.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Skip the confirmation prompt when used with --delete-private-data.",
    ),
) -> None:
    """Disable SaaS sync for this checkout and purge its pending uploads."""
    from specify_cli.sync.routing import disable_checkout_sync
    from specify_cli.sync.sharing_client import (
        RepositorySharingClientError,
        delete_private_project_sync,
        list_repository_shares_sync,
    )

    _require_daemon_owner_coherence("spec-kitty sync opt-out")

    routing = _require_active_checkout()
    with _reporting_a_refused_config_write("This checkout's opt-out"):
        result = disable_checkout_sync(
            routing.repo_root,
            remember_repo_default=not checkout_only,
        )

    console.print(f"[green]✓[/green] Disabled SaaS sync for this checkout ([cyan]{routing.repo_slug or routing.project_slug or routing.project_uuid}[/cyan]).")
    console.print(f"[dim]Removed {result.removed_events} queued event(s) and {result.removed_body_uploads} queued body upload(s) for this checkout.[/dim]")
    if result.remembered_for_repo:
        console.print("[dim]Future checkouts of this repository will also default to sync disabled.[/dim]")

    if not delete_private_data or not routing.project_uuid:
        return

    if not is_saas_sync_enabled():
        console.print("[yellow]Skipping private-data deletion because SaaS sync is disabled in this shell.[/yellow]")
        return

    try:
        _require_authenticated_session(command_name="sync opt-out")
        shares = list_repository_shares_sync(source_project_uuid=routing.project_uuid)
    except (RepositorySharingClientError, typer.Exit) as exc:
        console.print(f"[yellow]Could not inspect remote share state:[/yellow] {exc}")
        return

    if shares:
        console.print("[yellow]Private data was not deleted because this repository has team share history.[/yellow]")
        return

    confirmed = yes or typer.confirm(
        "Delete already-synced private Teamspace data for this checkout from SaaS?",
        default=False,
    )
    if not confirmed:
        console.print("[dim]Kept private Teamspace data on SaaS.[/dim]")
        return

    try:
        deletion = delete_private_project_sync(source_project_uuid=routing.project_uuid)
    except RepositorySharingClientError as exc:
        console.print(f"[yellow]Private data was not deleted:[/yellow] {exc}")
        return

    console.print(
        f"[green]✓[/green] Deleted private SaaS data for this checkout "
        f"({deletion.get('deleted_event_count', 0)} event(s), "
        f"{deletion.get('deleted_build_count', 0)} build(s))."
    )


def _auto_converge_legacy_on_enable() -> None:
    """Retired compatibility seam; opt-in must never mutate legacy evidence."""
    console.print(
        "[yellow]Automatic legacy convergence is retired.[/yellow] "
        "Use `spec-kitty sync project-store-preview` followed by the explicit "
        "`project-store-migrate` command."
    )


@app.command(name="opt-in")
def opt_in(
    checkout_only: bool = typer.Option(
        False,
        "--checkout-only",
        help="Enable only this checkout; do not update the remembered default for future checkouts.",
    ),
) -> None:
    """Enable SaaS sync for this checkout."""
    from specify_cli.sync.routing import enable_checkout_sync

    if not is_saas_sync_enabled():
        # Non-green + non-zero (#2264 item 3): opt-in cannot take effect while
        # the rollout flag is off, so a dim exit-0 "success" is misleading.
        # Surface the disabled state clearly and exit non-zero.
        console.print(f"[yellow]{saas_sync_disabled_message()}[/yellow]")
        raise typer.Exit(1)

    _require_daemon_owner_coherence("spec-kitty sync opt-in")

    enforce_teamspace_mission_state_ready(
        console=console,
        command_name="spec-kitty sync opt-in",
    )

    routing = _require_active_checkout()
    with _reporting_a_refused_config_write("This checkout's opt-in"):
        refreshed = enable_checkout_sync(
            routing.repo_root,
            remember_repo_default=not checkout_only,
        )

    # Honest confirmation (#2264): opt-in writes LOCAL routing flags only — no
    # auth, no remote round-trip, no history import. The message must not imply
    # remote materialization (the prior "Enabled SaaS sync" wording was the
    # false-green that escalated #2264 to P1).
    scope_label = refreshed.repo_slug or refreshed.project_slug or refreshed.project_uuid
    console.print(f"[green]✓[/green] {saas_sync_opt_in_recorded_message(scope_label)}")
    if not checkout_only and refreshed.repo_slug:
        console.print("[dim]Future checkouts of this repository will also default to this local preference.[/dim]")


def _detect_workspace_context() -> tuple[Path, str | None]:
    """Detect current workspace and feature context.

    Returns:
        Tuple of (workspace_path, mission_slug)
        If not in a workspace, returns (cwd, None)
    """
    cwd = Path.cwd()

    # Check if we're in a .worktrees directory
    parts = cwd.parts
    for i, part in enumerate(parts):
        if part == ".worktrees" and i + 1 < len(parts):
            # Found a worktree path like: /repo/.worktrees/010-feature-lane-a
            workspace_name = parts[i + 1]
            # Extract feature slug from workspace name (###-feature-lane-x)
            match = re.match(r"^(\d{3}-[a-zA-Z0-9-]+)-lane-[a-z]+$", workspace_name)
            if match:
                return cwd, match.group(1)

    # Try to detect from git branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd=cwd,
        )
        if result.returncode == 0:
            branch_name = result.stdout.strip()
            # Route through the canonical dual-era parser: the old legacy-only
            # regex missed every mid8-era lane branch (#1860 class), silently
            # returning no slug. ``parse_mission_slug_from_branch`` accepts both
            # legacy ``NNN-slug`` and ``<human-slug>-<mid8>`` lane branches.
            from specify_cli.lanes.branch_naming import parse_mission_slug_from_branch

            parsed = parse_mission_slug_from_branch(branch_name)
            if parsed is not None and parsed.lane_id is not None:
                return cwd, parsed.slug
    except (FileNotFoundError, OSError):
        pass

    # Not in a recognized workspace
    return cwd, None


def _display_changes_integrated(changes: list[ChangeInfo]) -> None:
    """Display changes that were integrated during sync."""
    if not changes:
        return

    console.print(f"\n[cyan]Changes integrated ({len(changes)}):[/cyan]")
    for change in changes[:5]:  # Show first 5 changes
        short_id = change.commit_id[:7] if change.commit_id else "unknown"
        # Truncate message to 50 chars
        msg = change.message[:50] + "..." if len(change.message) > 50 else change.message
        console.print(f"  • [dim]{short_id}[/dim] {msg}")

    if len(changes) > 5:
        console.print(f"  [dim]... and {len(changes) - 5} more[/dim]")


def _display_conflicts(conflicts: list[ConflictInfo]) -> None:
    """Display conflicts with actionable details.

    Shows:
    - File path
    - Line ranges (if available)
    - Conflict type
    - Resolution hints
    """
    if not conflicts:
        return

    console.print(f"\n[yellow]Conflicts ({len(conflicts)} files):[/yellow]")

    # Create a table for better formatting
    table = Table(show_header=True, header_style=_WARNING_HEADER_STYLE, show_lines=False)
    table.add_column("File", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Lines", style="dim")

    for conflict in conflicts:
        # Format line ranges
        lines = ", ".join(f"{start}-{end}" for start, end in conflict.line_ranges) if conflict.line_ranges else "entire file"

        table.add_row(
            str(conflict.file_path),
            conflict.conflict_type.value,
            lines,
        )

    console.print(table)

    # Show resolution hints
    console.print("\n[dim]To resolve conflicts:[/dim]")
    console.print("[dim]  1. Edit the conflicted files to resolve markers[/dim]")
    console.print("[dim]  2. Commit the resolution (git)[/dim]")


def _git_repair(workspace_path: Path) -> bool:
    """Attempt git workspace recovery.

    This is a best-effort recovery that tries:
    1. Abort any in-progress rebase/merge
    2. Reset to HEAD

    Returns:
        True if recovery succeeded, False otherwise

    Note: This may lose uncommitted work.
    """
    try:
        # First, try to abort any in-progress operations
        for abort_cmd in [
            ["git", "rebase", "--abort"],
            ["git", "merge", "--abort"],
            ["git", "cherry-pick", "--abort"],
        ]:
            subprocess.run(
                abort_cmd,
                cwd=workspace_path,
                capture_output=True,
                check=False,
                timeout=10,
            )

        # Reset to HEAD (keeping changes in working tree)
        result = subprocess.run(
            ["git", "reset", "--mixed", "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, OSError):
        return False


@app.command(name="import-history")
def import_history(
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Step 3: upload the exact Step-2 cohort; requires --history-action-id from --confirm-history.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Step 1: preview the synthesized cohort without staging or uploading (the default).",
    ),
    mission: str | None = typer.Option(
        None,
        "--mission",
        help="Import only this mission (slug / mid8 / ULID); default imports all eligible missions.",
    ),
    history_action_id: str | None = typer.Option(
        None,
        "--history-action-id",
        help="Step-2 action ID consumed by --apply; reuse the same --mission selector.",
    ),
    confirm_history: bool = typer.Option(
        False,
        "--confirm-history",
        help="Step 2: stage and confirm the exact Step-1 cohort locally; performs zero upload.",
    ),
) -> None:
    """Materialize existing local mission/WP history into the SaaS projection (#2262).

    A first sync registers a remote project/build but leaves it with zero
    materialized missions — the SaaS materializer deliberately refuses to
    fabricate a WorkPackage from a status event with no prior create. This
    command emits the missing ``MissionCreated → WPCreated[] → WPStatusChanged[]``
    stream (INV-3) so historical work populates the projection.

    This is an explicit three-step flow using the same ``--mission`` selector:
    (1) ``--dry-run`` previews the synthesized cohort with zero staging/egress;
    (2) ``--confirm-history`` stages and confirms those exact local bytes, prints
    a history action ID, and performs zero egress; (3) ``--apply
    --history-action-id <ID>`` preflights and uploads only that confirmed cohort.
    Skipping Step 2 or changing the cohort/authority fails closed.

    Import is once-and-frozen: each event carries a deterministic id, so
    re-running after the on-disk facts change (e.g. after fixing a malformed WP
    the dry-run flagged as skipped) re-sends the same id and the server drops the
    updated payload as a duplicate rather than overwriting. Resolve any skipped
    or incomplete missions the dry-run reports before the first ``--apply``.
    """
    from specify_cli.migration.mission_state import MissionStateRepairError
    from specify_cli.sync.history_import import (
        ImportAuditBlocked,
        MissionScanError,
        build_import_plan,
        describe_plan,
    )

    selected_actions = sum((bool(apply), bool(dry_run), bool(confirm_history)))
    if selected_actions > 1:
        console.print("[red]Error:[/red] --apply, --dry-run, and --confirm-history are mutually exclusive.")
        raise typer.Exit(2)
    if history_action_id is not None and not apply:
        console.print("[red]Error:[/red] --history-action-id is valid only with --apply.")
        raise typer.Exit(2)

    if apply:
        _run_import_apply(mission, history_action_id=history_action_id)
        return
    if confirm_history:
        _run_import_confirm(mission)
        return

    repo_root = _require_active_checkout().repo_root

    try:
        plan = build_import_plan(repo_root, mission=mission, apply=False)
    except (MissionStateRepairError, MissionScanError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except ImportAuditBlocked as exc:
        console.print(f"[red]Import blocked:[/red] {len(exc.blockers)} audit finding(s) must be resolved first:")
        for blocker in exc.blockers[:20]:
            console.print(f"  [yellow]•[/yellow] {blocker['mission_slug']}: {blocker['message']}")
        raise typer.Exit(1) from exc

    if plan.is_empty:
        console.print("[yellow]No missions found to import.[/yellow]")
        raise typer.Exit(0)

    for line in describe_plan(plan):
        console.print(line)
    console.print("\n[dim]Dry-run: nothing uploaded or staged. Re-run with --confirm-history to record the exact local cohort before --apply.[/dim]")


def _run_import_confirm(mission: str | None) -> None:
    """Stage and confirm one exact synthesized cohort without remote I/O."""
    from specify_cli.core.contract_gate import ContractViolationError
    from specify_cli.migration.mission_state import MissionStateRepairError
    from specify_cli.sync.history_disclosure import HistoryDisclosureError
    from specify_cli.sync.history_import import (
        ImportAuditBlocked,
        ImportIdentityError,
        MissionScanError,
        describe_plan,
    )
    from specify_cli.sync.history_import.pipeline import confirm_import_history

    runtime = _open_project_dispatch_runtime()
    try:
        if runtime.delivery_target is None:
            console.print("[red]History confirmation target is not admitted.[/red] No current project DeliveryTarget is available.")
            raise typer.Exit(1)
        repo_root = _require_active_checkout().repo_root
        try:
            result = confirm_import_history(
                repo_root,
                mission=mission,
                store=runtime.store,
                context=runtime.context,
                account_identity=str(runtime.delivery_target.account_identity),
            )
        except (MissionStateRepairError, MissionScanError) as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        except ImportIdentityError as exc:
            console.print(f"[red]Identity error:[/red] {exc}")
            raise typer.Exit(1) from exc
        except HistoryDisclosureError as exc:
            console.print(f"[red]History confirmation invalid:[/red] {exc}")
            raise typer.Exit(1) from exc
        except ImportAuditBlocked as exc:
            console.print(f"[red]Import blocked:[/red] {len(exc.blockers)} audit finding(s) must be resolved first:")
            for blocker in exc.blockers[:20]:
                console.print(f"  [yellow]•[/yellow] {blocker['mission_slug']}: {blocker['message']}")
            raise typer.Exit(1) from exc
        except ContractViolationError as exc:
            console.print(f"[red]Envelope contract violation:[/red] {exc}")
            raise typer.Exit(1) from exc

        for line in describe_plan(result.plan):
            console.print(line)
        console.print("\n[green]History confirmation recorded locally; nothing uploaded.[/green]")
        console.print(f"History action ID: {result.capability.action_id}")
        from shlex import quote

        mission_option = f" --mission {quote(mission)}" if mission is not None else ""
        console.print(f"Apply with: spec-kitty sync import-history --apply{mission_option} --history-action-id {result.capability.action_id}")
    finally:
        runtime.close()


def _resolve_history_import_receiver(runtime: _EventSyncRuntime | _ProjectDispatchRuntime, *, token: str) -> tuple[DeliveryReceiver, str]:
    """Resolve one gated Teamspace authority for preflight and delivery.

    Fails closed on the operator's *persisted* event-sync mode (#2884 P1):
    import-history uploads a mission's full history, so it must honor
    ``spec-kitty sync mode`` like every other sync surface, not silently
    override it to TEAMSPACE. An operator on EXTERNAL_RECEIVER, LOCAL_RETENTION,
    or OPT_OUT gets a clear refusal instead of an unwanted upload.
    """
    from specify_cli.delivery.config import Mode

    config = _load_event_sync_config()
    if config.mode is not Mode.TEAMSPACE:
        console.print(
            "[red]import-history requires event-sync mode TEAMSPACE;[/red] "
            f"current mode is {config.mode.name}. Run `spec-kitty sync mode TEAMSPACE` "
            "to switch, then retry."
        )
        raise typer.Exit(1)
    receiver, gate_decision = _resolve_gated_receiver(runtime.target, config, auth_token=token)
    if receiver is None or not getattr(receiver, "endpoint_url", ""):
        console.print("[red]Event sync is not configured for this checkout.[/red] Cannot upload.")
        raise typer.Exit(1)
    assert gate_decision is not None  # a resolved receiver always carries a decision
    if gate_decision.blocked:
        names = ", ".join(gate.name for gate in gate_decision.unsatisfied)
        console.print(f"[red]Event sync is gated:[/red] {names}. Cannot upload.")
        raise typer.Exit(1)
    return receiver, runtime.target.resolved_server_url


def _render_upload_report(report: UploadReport) -> bool:
    """Render the partial / pending / rejected tail of an upload report.

    Returns ``True`` when the run is fully clean (no partial delivery, no
    pending events, no rejections) and ``False`` when the caller must exit
    non-zero. The return value mirrors ``UploadReport.ok`` exactly, so the
    exit code the caller raises always agrees with the message just printed.
    """
    if report.partial:
        # Distinct third state: neither success nor total failure. Delivery
        # stopped at the first failed chunk, so everything delivered is a safe
        # ordered prefix of whole missions; the rest was never attempted.
        console.print(
            f"[yellow]Partial upload:[/yellow] delivery stopped at a failed chunk — a safe ordered "
            f"prefix was delivered ({report.delivered_through_chunk} full chunk(s)); "
            f"{report.undelivered_event_count} event(s) not attempted. Fix the failure and re-run "
            "--apply: the server dedups on event_id, so the re-run resumes idempotently."
        )
    if report.pending:
        # Direct import delivery does not journal or ledger pending outcomes,
        # and import event ids are deterministic (frozen at synthesis time), so
        # the server dedups a re-run onto these same ids. That means re-running
        # --apply will report them as `duplicate` and exit 0 regardless of
        # whether they ever materialized in the projection — "pending" can also
        # arise from a 200 response that merely omits an entry, which is not
        # necessarily anything the operator can act on. Never suggest a re-run
        # as the fix; point at the authoritative surface instead.
        console.print(
            f"[yellow]Incomplete:[/yellow] {report.pending} event(s) remain pending and are not "
            "confirmed in the projection. Re-running --apply will report these events as "
            "duplicates (the server dedups on event_id) and exit 0 whether or not they were "
            "ever materialized — verify the outcome in the dashboard/projection instead."
        )
    if not report.ok:
        for sample in report.rejected_samples:
            console.print(f"  [red]✗[/red] {sample}")
        return False
    return True


def _run_import_apply(
    mission: str | None,
    *,
    history_action_id: str | None,
) -> None:
    """The ``import-history --apply`` path: preflight + upload under the real UUID.

    Resolves the authed Teamspace receiver (fail-closed when unauthenticated /
    unconfigured), then delegates to ``apply_import`` which builds the plan with
    the real persisted project UUID, server-preflights the whole stream, and
    uploads it. The server dedups on ``event_id`` so a re-run is idempotent.
    """
    from specify_cli.core.contract_gate import ContractViolationError
    from specify_cli.migration.mission_state import MissionStateRepairError
    from specify_cli.sync.history_import import (
        ImportAuditBlocked,
        ImportIdentityError,
        MissionScanError,
        PreflightRejected,
        apply_import,
        describe_plan,
    )
    from specify_cli.sync.history_disclosure import (
        HistoryDisclosureError,
        consume_history_disclosure,
    )

    token = _event_sync_access_token()
    if not token:
        console.print("[red]Not authenticated.[/red] Run `spec-kitty auth login` before importing with --apply.")
        raise typer.Exit(1)

    action_id = str(history_action_id or "").strip()
    if not action_id:
        console.print("[red]History confirmation required.[/red] Pass --history-action-id for a previously previewed and explicitly confirmed sealed cohort.")
        raise typer.Exit(1)

    runtime = _open_project_dispatch_runtime()
    try:
        if runtime.delivery_target is None:
            console.print("[red]History import target is not admitted.[/red] No current project DeliveryTarget is available.")
            raise typer.Exit(1)
        receiver, server_url = _resolve_history_import_receiver(runtime, token=token)
        repo_root = _require_active_checkout().repo_root

        try:
            capability = consume_history_disclosure(
                runtime.store,
                action_id=action_id,
                context=runtime.context,
            )
            result = apply_import(
                repo_root,
                mission=mission,
                receiver=receiver,
                server_url=server_url,
                auth_token=token,
                project_context=runtime.context,
                target=runtime.delivery_target,
                history_capability=capability,
            )
        except (MissionStateRepairError, MissionScanError) as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        except ImportIdentityError as exc:
            console.print(f"[red]Identity error:[/red] {exc}")
            raise typer.Exit(1) from exc
        except HistoryDisclosureError as exc:
            console.print(f"[red]History confirmation invalid:[/red] {exc}")
            raise typer.Exit(1) from exc
        except ImportAuditBlocked as exc:
            console.print(f"[red]Import blocked:[/red] {len(exc.blockers)} audit finding(s) must be resolved first:")
            for blocker in exc.blockers[:20]:
                console.print(f"  [yellow]•[/yellow] {blocker['mission_slug']}: {blocker['message']}")
            raise typer.Exit(1) from exc
        except ContractViolationError as exc:
            # The offline outbound-envelope gate refused a synthesized envelope
            # before any upload — fail closed with the contract detail (#2884).
            console.print(f"[red]Envelope contract violation:[/red] {exc}")
            raise typer.Exit(1) from exc
        except PreflightRejected as exc:
            console.print(f"[red]Server preflight rejected the import:[/red] {exc}")
            raise typer.Exit(1) from exc

        if result.plan.is_empty:
            console.print("[yellow]No missions found to import.[/yellow]")
            raise typer.Exit(0)

        for line in describe_plan(result.plan):
            console.print(line)
        console.print(f"[dim]Provenance: {len(result.manifest)} envelope(s) hashed into the sha256 import audit manifest.[/dim]")
        report = result.report
        console.print(
            f"\n[green]Imported:[/green] {report.success} created, {report.duplicate} duplicate, "
            f"{report.pending} pending, {report.rejected} rejected ({report.total} total)."
        )
        if not _render_upload_report(report):
            raise typer.Exit(1)
    finally:
        runtime.close()


@app.command(name="workspace")
def sync_workspace(
    repair: bool = typer.Option(
        False,
        "--repair",
        "-r",
        help="Attempt workspace recovery (may lose uncommitted work)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed sync output",
    ),
) -> None:
    """Synchronize workspace with upstream changes.

    Updates the current workspace with changes from its base branch or parent.
    This is equivalent to `git rebase <base-branch>`.

    Sync may FAIL on conflicts (must resolve before continuing).

    Examples:
        # Sync current workspace
        spec-kitty sync workspace

        # Sync with verbose output
        spec-kitty sync workspace --verbose

        # Attempt recovery from broken state
        spec-kitty sync workspace --repair
    """
    console.print()

    # Detect workspace context
    workspace_path, mission_slug = _detect_workspace_context()

    if mission_slug is None:
        for line in NOT_IN_WORKSPACE_LINES:
            console.print(line)
        raise typer.Exit(NOT_IN_WORKSPACE_EXIT)

    console.print(f"[cyan]Workspace:[/cyan] {workspace_path.name}")

    # Get VCS implementation
    try:
        vcs = get_vcs(workspace_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to detect VCS: {e}")
        raise typer.Exit(1) from e

    console.print("[cyan]Backend:[/cyan] git")
    console.print()

    # Handle repair mode
    if repair:
        console.print("[yellow]Attempting workspace recovery...[/yellow]")
        console.print("[dim]Note: This may lose uncommitted work[/dim]")
        console.print()

        success = _git_repair(workspace_path)

        if success:
            console.print("[green]✓ Recovery successful[/green]")
            console.print("Workspace state has been reset.")
        else:
            console.print("[red]✗ Recovery failed[/red]")
            console.print("Manual intervention may be required.")
            console.print()
            console.print("[dim]Try these commands manually:[/dim]")
            console.print("  git status")
            console.print("  git rebase --abort")
            console.print("  git reset --hard HEAD")
            raise typer.Exit(1)

        return

    # Perform sync
    console.print("[cyan]Syncing workspace...[/cyan]")

    result: SyncResult = vcs.sync_workspace(workspace_path)

    # WP11 (A-1 restructure): the status dispatch — the cc-heavy ``if/elif`` chain
    # that mapped each ``SyncResult`` arm to console lines + exit code — moves to the
    # pure ``sync_workspace_core`` (``build_sync_render_plan``). This shell now only
    # gathers I/O (workspace context + vcs above), asks the core to decide the render
    # steps, then emits them. Zero observable change; the WP11 monkeypatch-golden
    # (``test_sync_workspace_render.py``) is the guard.
    plan = build_sync_render_plan(result, verbose=verbose)
    _render_sync_plan(plan, result)

    if plan.exit_code is not None:
        raise typer.Exit(plan.exit_code)

    console.print()


def _render_sync_plan(plan: SyncRenderPlan, result: SyncResult) -> None:
    """Emit a ``build_sync_render_plan`` decision to the console (WP11 render phase).

    Each :class:`RenderLine` is a passthrough ``console.print``; the two table
    markers re-invoke the host's Rich-table helpers over the same ``SyncResult`` the
    core decided against, preserving the pre-restructure interleave byte-for-byte.
    """
    for step in plan.steps:
        if isinstance(step, RenderConflicts):
            _display_conflicts(result.conflicts)
        elif isinstance(step, RenderChanges):
            _display_changes_integrated(result.changes_integrated)
        elif isinstance(step, RenderLine):
            console.print(step.text)


def _gateway_unavailable_note(server_url: str, status_code: int) -> str:
    """Remediation note for a sync server returning a gateway-class status.

    Frames the transient case first (a gateway 5xx is most often a rolling
    deploy or maintenance blip), reassures the operator their queued events are
    retained and will drain on recovery — consistent with the offline queue's
    ``failed_transient`` disposition — and only then offers the repoint recovery
    for the case where the URL is genuinely decommissioned.
    """
    return (
        f"HTTP {status_code} from {server_url} — the sync endpoint is unavailable. "
        "This is often a transient outage (for example a rolling deploy), so your "
        "queued events are kept locally and will drain once it recovers. If instead "
        "you have switched environments and this URL is decommissioned, repoint with "
        f"`spec-kitty sync server <url>` (e.g. {EXAMPLE_HOSTED_SAAS_URL}), then "
        "`spec-kitty auth login --force`."
    )


#: Server-connection verdicts (from :func:`_check_server_connection`) that are
#: healthy or a deliberate non-problem state. "Connected" = the live probe
#: succeeded; "Disabled" = hosted sync is off by design. Any verdict NOT matching
#: one of these is a real fault the ``doctor`` summary must surface rather than
#: swallow behind a green "healthy" (FR-002 of the first-sync preflight, #3406).
_HEALTHY_CONNECTION_MARKERS: tuple[str, ...] = ("Connected", "Disabled")

#: Verdicts the auth/session block of ``doctor`` already reports. The
#: server-reachability block skips these so one authentication fault is not
#: listed twice with two differently-worded remediations.
_AUTH_OWNED_CONNECTION_MARKERS: tuple[str, ...] = ("Not authenticated", "Session expired")


def _check_server_connection(server_url: str) -> tuple[str, str]:
    """Probe sync health using the user's real auth token.

    Returns:
        Tuple of (rich-formatted status string, detail message).
    """
    if not is_saas_sync_enabled():
        return (
            "[dim]Disabled[/dim]",
            saas_sync_disabled_message(),
        )

    import asyncio

    from specify_cli.auth import get_token_manager
    from specify_cli.auth.errors import AuthenticationError
    from specify_cli.auth.http import request_with_fallback_sync
    from specify_cli.auth.errors import NetworkError

    # Step 1: Check if an authenticated session exists.
    tm = get_token_manager()
    if not tm.is_authenticated:
        return (
            "[yellow]Not authenticated[/yellow]",
            "Run `spec-kitty auth login` to connect.",
        )

    # Step 2: Get a valid access token (with auto-refresh if expired) via a
    # short-lived event loop, since this function is synchronous.
    async def _get_token() -> str:
        return await tm.get_access_token()

    access_token: str | None
    try:
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            access_token = new_loop.run_until_complete(_get_token())
        finally:
            with contextlib.suppress(Exception):
                asyncio.set_event_loop(None)
            new_loop.close()
    except AuthenticationError:
        access_token = None
    except Exception as exc:
        return (
            "[red]Error[/red]",
            f"Authentication probe failed: {str(exc)[:80]}",
        )

    if not access_token:
        # Access token expired and refresh also failed
        return (
            "[yellow]Session expired[/yellow]",
            "Run `spec-kitty auth login` to re-authenticate.",
        )

    # Step 3: Probe the authenticated sync health endpoint.
    health_url = f"{server_url.rstrip('/')}/api/v1/sync/health/"
    batch_url = f"{server_url.rstrip('/')}/api/v1/events/batch/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = b'{"events": []}'

    try:
        response = request_with_fallback_sync(
            "GET",
            health_url,
            timeout=5.0,
            headers=headers,
        )

        if response.status_code in {404, 405}:
            response = request_with_fallback_sync(
                "POST",
                batch_url,
                timeout=5.0,
                headers=headers,
                content=payload,
            )
            if response.status_code == 400 and "No events provided" in response.text:
                return (
                    "[green]Connected[/green]",
                    "Server reachable, authentication valid (legacy batch probe).",
                )

        if response.status_code == 200:
            return (
                "[green]Connected[/green]",
                "Server reachable, authentication valid.",
            )
        elif response.status_code == 401:
            return (
                "[yellow]Authentication failed[/yellow]",
                "Run `spec-kitty auth login` to re-authenticate.",
            )
        elif response.status_code == 403:
            return (
                "[yellow]Permission denied[/yellow]",
                "Check team membership for this project.",
            )
        elif response.status_code in GATEWAY_STATUSES:
            # Gateway 5xx = the edge says the endpoint is unavailable (FR-003,
            # #3406). Reclassify out of the generic "Unexpected" branch so a
            # first sync against a stale/decommissioned URL gets an actionable
            # signal, while staying consistent with the queue's transient
            # (never-dead-lettered) disposition — see _gateway_unavailable_note.
            return (
                "[red]Server unavailable[/red]",
                _gateway_unavailable_note(server_url, response.status_code),
            )
        else:
            return (
                "[yellow]Unexpected[/yellow]",
                f"Server returned HTTP {response.status_code}.",
            )
    except NetworkError as exc:
        return (
            "[red]Unreachable[/red]",
            f"{str(exc)[:80]}. Events will be queued for later sync.",
        )
    except Exception as e:
        return (
            "[red]Error[/red]",
            f"Probe failed: {str(e)[:80]}",
        )


@app.command(name="server")
def sync_server(
    url: str | None = typer.Argument(
        None,
        help="Sync server URL to set (HTTPS, or loopback HTTP for local development)",
    ),
) -> None:
    """Show or set sync server URL.

    Examples:
        spec-kitty sync server
        spec-kitty sync server https://spec-kitty-dev.fly.dev
        spec-kitty sync server http://localhost:8000
    """
    from specify_cli.sync.config import SyncConfig

    config = SyncConfig()
    if url is None:
        console.print(f"Server URL: [cyan]{config.get_server_url()}[/cyan]")
        console.print(f"Config File: [dim]{config.config_file}[/dim]")
        return

    normalized_url = url.strip().rstrip("/")
    parsed = urlparse(normalized_url)
    # HTTPS is required for remote targets, but loopback HTTP is a deliberate
    # local-development special case (e.g. http://localhost:8000 against a local
    # Docker SaaS) — don't force HTTPS on loopback.
    host = (parsed.hostname or "").lower()
    is_loopback = host in {"localhost", "127.0.0.1", "::1"}
    scheme_ok = parsed.scheme == "https" or (parsed.scheme == "http" and is_loopback)
    if not scheme_ok or not parsed.netloc:
        console.print(
            "[red]Error:[/red] Invalid server URL. Use a full HTTPS URL "
            "(or http://localhost[:port] for local development), "
            "for example: https://your-teamspace.example.com"
        )
        raise typer.Exit(1)

    with _reporting_a_refused_config_write("The sync server URL"):
        config.set_server_url(normalized_url)
    console.print(f"[green]✓[/green] Sync server set to [cyan]{normalized_url}[/cyan]")
    console.print("[dim]If you switched environments, run 'spec-kitty auth login --force' to refresh credentials.[/dim]")


@app.command()
def now(
    report: Path | None = typer.Option(
        None,
        "--report",
        help="Export per-event failure details to a JSON file",
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="Exit non-zero on sync errors (default: strict)",
    ),
) -> None:
    """Trigger immediate sync of all queued events.

    Drains the offline queue completely, uploading events to the server
    in batches of 1000 until the queue is empty or all remaining events
    have exceeded their retry limit.

    Examples:
        spec-kitty sync now
        spec-kitty sync now --report failures.json
        spec-kitty sync now --no-strict
    """
    from specify_cli.sync.background import get_sync_service
    from specify_cli.sync.preflight import run_preflight

    # T012 / FR-002: gate `sync now` with the structural preflight BEFORE
    # any enqueue, queue read, or SaaS flush. The preflight refuses on
    # daemon-owner mismatch (D-3), orphan owner record, or legacy rows
    # remaining in the current scope — these are coherence failures the
    # operator must resolve before any sync makes sense.
    #
    # ``require_auth=False`` here on purpose: auth-absent has its own
    # graceful UX path (``service.sync_now()`` produces structured
    # unauthenticated errors and a failure report, exiting 1). FR-008's
    # auth-required-and-absent refusal applies to ``setup-plan`` and to
    # ``sync status --check``, not to ``sync now``, where forcing exit 2
    # would clobber the issue #829 report-file flow.
    _preflight_result = run_preflight(repo_root=Path.cwd(), require_auth=False)
    if not _preflight_result.ok:
        console.print("[red]Refusing `spec-kitty sync now`.[/red]")
        _preflight_result.render(console)
        raise typer.Exit(code=2)

    if not is_saas_sync_enabled():
        console.print(f"[yellow]{saas_sync_disabled_message()}[/yellow]")
        console.print(f"[dim]Set {SAAS_SYNC_ENV_VAR}=1 to enable upload.[/dim]")
        return

    enforce_teamspace_mission_state_ready(
        console=console,
        command_name="spec-kitty sync now",
    )

    service = get_sync_service()
    # Pending-work signal for the strict/unauthenticated exit contract (the
    # queued-but-undelivered event count). Read before delivery so a successful
    # drain does not erase the "there was work" signal.
    # The ambient OfflineQueue was retired. Keep zero-or-size only for injected
    # compatibility test services; canonical retained work comes from the routed
    # project journal immediately below.
    queue_size = int(service.queue.size()) if service.queue is not None else 0
    retained_work_present = _event_sync_retained_work_present()

    # Single, non-destructive event-delivery path. The journal-based dispatcher
    # is now the SOLE event drain (FR-001): the retired legacy
    # ``service.sync_now()`` offline-queue drain deleted journal-owned events AND
    # double-POSTed every event the dispatcher also delivers (the dual-drain
    # defect). Body uploads still flush via the body-ONLY entry point so
    # attachments keep working without ever touching the durable event journal
    # (C-006).
    dispatch_outcome = _run_event_sync_dispatch()
    intentional_no_delivery = isinstance(dispatch_outcome, _IntentionalNoDelivery)
    # #3620 Finding 2: a gate/admission block is a distinct marker from the
    # deliberate-retention one above, so the exit decision can tell it apart
    # from a genuine "not authenticated" and surface the real reason instead.
    admission_gated = isinstance(dispatch_outcome, _AdmissionGatedNoDelivery)
    summary = dispatch_outcome.summary if intentional_no_delivery or admission_gated else dispatch_outcome
    service.drain_body_uploads_only()

    # Persist the per-outcome report (if requested) and map the dispatch outcome
    # onto the strict exit contract — preserving the unauthenticated/blocked UX.
    _maybe_write_dispatch_report(report, summary)
    _enforce_sync_now_exit_from_dispatch(
        strict,
        queue_size,
        summary,
        retained_work_present=retained_work_present,
        intentional_no_delivery=intentional_no_delivery,
        admission_gated=admission_gated,
    )


@app.command()
def gc() -> None:
    """Purge event payloads delivered to all known targets (explicit, destructive).

    Deletes journal payload rows only for events with a terminal-success
    delivery to **every** registered target; payloads still owed to any known
    target are kept so the durable, re-drainable copy is never lost (FR-005).
    The delivery ledger is never touched, so delivery history survives (FR-010).
    Runs only on this explicit invocation — never from ``sync now``.

    Examples:
        spec-kitty sync gc
    """
    from specify_cli.delivery.retention import gc_payloads

    runtime = _open_retention_runtime_or_exit()
    try:
        from specify_cli.delivery.ledger import SqliteDeliveryLedger
        from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
        from specify_cli.event_journal.journal import EventJournal

        with runtime.store.unit_of_work() as unit:
            registry = ProjectDeliveryTargetRegistry(runtime.store)
            known_target_ids = [target.target_id for target in registry.list_targets(unit)]
            result = gc_payloads(
                EventJournal(unit, runtime.store.layout_generation()),
                SqliteDeliveryLedger(unit, runtime.store.layout_generation()),
                known_target_ids=known_target_ids,
            )
    finally:
        runtime.close()
    _print_retention_result(result)


@app.command()
def archive() -> None:
    """Archive retained event payloads (explicit, non-destructive).

    Stamps the journal's archive marker so events move off the live retained
    surface without deleting bytes. Idempotent and never touches the delivery
    ledger (FR-010). Runs only on this explicit invocation.

    Examples:
        spec-kitty sync archive
    """
    from specify_cli.delivery.retention import archive_payloads

    runtime = _open_retention_runtime_or_exit()
    try:
        from specify_cli.event_journal.journal import EventJournal

        with runtime.store.unit_of_work() as unit:
            result = archive_payloads(EventJournal(unit, runtime.store.layout_generation()))
    finally:
        runtime.close()
    _print_retention_result(result)


# --------------------------------------------------------------------------- #
# `sync purge` — the operator's remediation path (#3030 WP08 / T022).           #
#                                                                              #
# FR-016 / FR-017 / NFR-006 / C-002. The purge subsystem's differential/verdict #
# arithmetic lives in `specify_cli.sync.sync_purge_core` (pure) and its census  #
# readers / store executors / operator report in                               #
# `specify_cli.sync.sync_purge_exec` (WP06 core/exec split). Both are           #
# re-established as `sync.<name>` module attributes by the husk re-export block  #
# below, so this thin `@app.command` shell — parse -> open ports -> call exec    #
# readers/executors -> call core differentials/verdict -> render — reaches them  #
# by bare name. Selection and deletion stay in `delivery/retention.py` /         #
# `sync/local_commit.py` (C-003).                                                #
# --------------------------------------------------------------------------- #


@app.command()
def purge(
    project: str = typer.Option(
        None,
        "--project",
        help=(
            "Purge one project's rows, by project uuid, project slug or repo slug "
            "— any name `sync doctor` / `sync status` prints for the project. "
            "Dry-run unless --apply is given."
        ),
    ),
    identity_less: bool = typer.Option(
        False,
        "--identity-less",
        help=("Purge journal/ledger rows whose project identity is NULL — permanently undeliverable rows that no project selector can match."),
    ),
    all_events: bool = typer.Option(
        False,
        "--all",
        help=(
            "Purge every row in the active project's journal, delivery ledger and "
            "body-upload queue, plus THIS checkout's queued local-commit frames. "
            "Requires --confirm with the confirmation phrase."
        ),
    ),
    apply: bool = typer.Option(False, "--apply", help="Actually delete. Without it this command only reports."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report only, deleting nothing (this is the default)."),
    confirm: str = typer.Option(
        "",
        "--confirm",
        help=("Confirmation phrase authorising a destructive --all run. Run without it once; the refusal names the exact phrase and deletes nothing."),
    ),
    report: Path = typer.Option(
        None,
        "--report",
        help=("Write the purge report as JSON. Worth doing: the ledger rows this purge deletes are the only durable record of what happened to those events."),
    ),
) -> None:
    """Remove a project's retained event data from every store that holds it (FR-016/FR-017).

    **Dry-run by default.** Reports per-store, per-delivery-state counts and changes
    nothing; what it predicts is exactly what ``--apply`` then deletes. Deletion is
    only ever the operator's explicit act (C-002) — nothing here runs unattended.

    Four stores hold a project's data and all four are covered: the event journal,
    the delivery ledger (removed, not retained — an orphan ledger row can quote the
    project it belonged to), the body-upload queue (verbatim ``spec.md`` /
    ``plan.md`` text, not envelopes), and this checkout's queued local-commit frames
    (whose ``changed_files`` are mission slugs).

    Every count in the differential is measured by re-reading the stores rather than
    by adding up what the purge reports deleting, and the report names the
    populations a targeted purge cannot reach instead of quietly leaving them out.

    ``--all`` is bounded to the active project's routed store and this checkout's
    local-commit frames. Another project store or checkout is neither listed nor
    touched.

    Examples:
        spec-kitty sync purge --project acme-migration
        spec-kitty sync purge --project acme-migration --apply --report purge.json
        spec-kitty sync purge --all
        spec-kitty sync purge --all --apply --confirm "purge all events"
    """
    import json as _json

    from specify_cli.core.paths import locate_project_root
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue
    from specify_cli.sync.local_commit import (
        census_pending_local_commits,
        purge_all_pending_local_commits,
        purge_pending_local_commits,
    )
    from specify_cli.sync.queue import get_max_queue_size

    _purge_validate_invocation(
        project=project,
        identity_less=identity_less,
        all_events=all_events,
        apply=apply,
        dry_run=dry_run,
        confirm=confirm,
        report=report,
    )

    runtime = _open_retention_runtime_or_exit()
    store = runtime.store
    authority = store.layout_generation()
    repo_root = locate_project_root(Path.cwd())
    checkout_identity = runtime.checkout_identity
    body_max_queue_size = get_max_queue_size()
    frames_location = str(repo_root / _PURGE_SYNC_STATE_RELPATH) if repo_root is not None else "no Spec Kitty checkout resolved from the current directory"
    before: dict[str, _RawCensus] = {
        _PURGE_FRAMES: _purge_frames_census(repo_root),
    }
    if apply and before[_PURGE_FRAMES].unreadable:
        _purge_usage_error("checkout-local sync-state.json is unreadable; refusing before any project-store or frame deletion")
    # What the purge's own census sees, taken at the same instant as the CLI's raw
    # read of the same file so the two are comparable. Not decoration:
    # ``load_sync_state`` resets a malformed file to empty and never raises, so a
    # disagreement means the purge is about to act on a picture the file does not
    # support — the case where it reports "0 frames" over a file full of mission
    # slugs, i.e. client engagement names.
    frames_census_reported = sum(census_pending_local_commits(repo_root).values()) if repo_root is not None else 0
    frames_census_disagrees = repo_root is not None and not before[_PURGE_FRAMES].unreadable and frames_census_reported != before[_PURGE_FRAMES].total
    if apply and frames_census_disagrees:
        _purge_usage_error("checkout-local frame census disagrees with sync-state.json; refusing before any project-store or frame deletion")

    selector_uuid = ""
    matched_slug: str | None = None
    result: ProjectPurgeResult | None = None
    body_removed_reported = 0
    body_scope: frozenset[str] = frozenset()
    journal_scope: frozenset[str] = frozenset()
    journal_ids: list[str] = []
    ledger_scope = frozenset({_PURGE_LEDGER})
    ghosts_before = 0
    after: dict[str, _RawCensus] = {}

    # All local payload repositories share this exact project UoW.  The UoW is
    # closed before the checkout-local frame file is read or changed.
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, authority)
        ledger = SqliteDeliveryLedger(unit, authority)
        body_queue = OfflineBodyUploadQueue(
            unit,
            authority,
            max_queue_size=body_max_queue_size,
        )
        before[_PURGE_JOURNAL] = _purge_journal_census(journal)
        before[_PURGE_BODY] = _purge_body_census(body_queue)

        if project is not None:
            selector_uuid, matched_slug = _purge_resolve_project(
                project,
                journal,
                checkout_identity,
            )
            if selector_uuid.strip().lower() != str(store.project_uuid.storage_token):
                _purge_usage_error("--project must identify the active project store; this command never opens or scans another project's physical store")
        elif all_events:
            selector_uuid = str(store.project_uuid.storage_token)

        conflicts = _purge_stored_spelling_conflicts(
            selector_uuid,
            [before[_PURGE_JOURNAL], before[_PURGE_BODY], before[_PURGE_FRAMES]],
        )
        if conflicts:
            _purge_usage_error(f'"{selector_uuid}" is not how these stores spell that project. They hold {", ".join(repr(key) for key in conflicts)}.')

        journal_scope, journal_ids = _purge_journal_selection(
            journal,
            before[_PURGE_JOURNAL],
            all_events=all_events,
            identity_less=identity_less,
            selector_uuid=selector_uuid,
        )
        before[_PURGE_LEDGER] = _purge_ledger_view(
            _purge_ledger_census(ledger, journal_ids),
            all_events=all_events,
        )
        unreadable_project_stores = [_PURGE_STORE_LABELS[name] for name in (_PURGE_JOURNAL, _PURGE_LEDGER, _PURGE_BODY) if before[name].unreadable]
        if apply and unreadable_project_stores:
            _purge_usage_error("project-store census is unreadable for " + ", ".join(unreadable_project_stores) + "; refusing before any deletion")
        ghosts_before = 0 if all_events else _purge_ledger_ghost_count(journal, ledger)
        result = _purge_run_journal_ledger(
            journal,
            ledger,
            all_events=all_events,
            identity_less=identity_less,
            selector_uuid=selector_uuid,
            dry_run=not apply,
            confirm=confirm,
        )
        if not identity_less:
            body_scope, body_removed_reported = _purge_run_body_queue(
                body_queue,
                before[_PURGE_BODY],
                all_events=all_events,
                selector_uuid=selector_uuid,
                dry_run=not apply,
                confirm=confirm,
            )
        after[_PURGE_JOURNAL] = _purge_journal_census(journal)
        after[_PURGE_LEDGER] = _purge_ledger_view(
            _purge_ledger_census(ledger, journal_ids),
            all_events=all_events,
        )
        after[_PURGE_BODY] = _purge_body_census(body_queue)

    frames_result = None
    if repo_root is not None and not identity_less:
        if all_events:
            frames_result = purge_all_pending_local_commits(repo_root, dry_run=not apply)
        else:
            frames_result = purge_pending_local_commits(repo_root, selector_uuid, dry_run=not apply)
    frames_scope = _purge_frames_scope(
        before[_PURGE_FRAMES],
        frames_result,
        all_events=all_events,
        selector_uuid=selector_uuid,
    )

    after[_PURGE_FRAMES] = _purge_frames_census(repo_root)

    scopes = {
        _PURGE_JOURNAL: journal_scope,
        _PURGE_LEDGER: ledger_scope,
        _PURGE_BODY: body_scope,
        _PURGE_FRAMES: frames_scope,
    }
    locations = {
        _PURGE_JOURNAL: str(store.database_path),
        _PURGE_LEDGER: str(store.database_path),
        _PURGE_BODY: str(store.database_path),
        _PURGE_FRAMES: frames_location,
    }
    reported = {
        _PURGE_JOURNAL: None if result is None else result.purged_count,
        _PURGE_LEDGER: None if result is None else result.ledger_rows_removed,
        _PURGE_BODY: body_removed_reported,
        _PURGE_FRAMES: None if frames_result is None else frames_result.removed,
    }

    outcomes = _purge_outcomes(
        before=before,
        after=after,
        scopes=scopes,
        locations=locations,
        reported=reported,
        result=result,
        ghosts_before=ghosts_before,
        identity_less=identity_less,
        in_checkout=repo_root is not None,
        frames_census_reported=frames_census_reported,
    )

    not_reached = _purge_not_reached(
        after=after,
        journal_scope=journal_scope,
        frames_scope=frames_scope,
        body_scope=body_scope,
        ghosts_before=ghosts_before,
        all_events=all_events,
    )

    scope_note = _PURGE_ALL_SCOPE_NOTE.format(frames_path=frames_location) if all_events else None
    selector_line = _purge_selector_line(
        project=project,
        identity_less=identity_less,
        selector_uuid=selector_uuid,
        matched_slug=matched_slug,
    )

    _purge_render(
        selector_line=selector_line,
        dry_run=not apply,
        outcomes=outcomes,
        not_reached=not_reached,
        scope_note=scope_note,
    )

    # ---- the verdict, from the measurements ------------------------------- #
    others_total = sum(outcome.others_delta_observed for outcome in outcomes.values())
    faults = _purge_faults(
        outcomes=outcomes,
        before=before,
        after=after,
        apply=apply,
        others_total=others_total,
        frames_census_reported=frames_census_reported,
        frames_census_disagrees=frames_census_disagrees,
    )

    _purge_print_verdict(faults, apply=apply, all_events=all_events)

    if report is not None:
        payload = {
            "generated_at": now_utc_iso(),
            "selector": {
                "kind": _selector_kind(project, identity_less),
                "project_uuid": selector_uuid or None,
                "matched_slug": matched_slug,
            },
            "dry_run": not apply,
            "applied": bool(apply),
            "stores": {store: outcome.as_dict() for store, outcome in outcomes.items()},
            "others_delta_total": others_total,
            "nfr_006_satisfied": not faults,
            "faults": faults,
            "not_reached": not_reached,
            "scope_note": scope_note,
        }
        report.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[cyan]Purge report written to {report}[/cyan]")

    if faults:
        raise typer.Exit(1)


@app.command()
def project_store_preview(
    source: list[Path] = typer.Option(
        ...,
        "--source",
        help="Explicit legacy SQLite source. Repeat for every shared store.",
    ),
    migration_id: str = typer.Option(..., "--migration-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Inventory immutable legacy sources, including committed WAL content."""
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.project_store_migration import LegacyProjectStoreMigration

    manifest = LegacyProjectStoreMigration(get_runtime_root().base, tuple(source)).preview(migration_id)
    if json_output:
        _emit_project_store_migration_json(manifest.to_dict())
        return
    console.print(
        f"[cyan]Migration {manifest.migration_id}[/cyan]: {manifest.phase.value}; "
        f"{manifest.total_rows} row(s), {len(manifest.partitions)} project(s), "
        f"{len(manifest.quarantine)} quarantined"
    )


@app.command()
def project_store_migrate(
    source: list[Path] = typer.Option(
        ...,
        "--source",
        help="Explicit legacy SQLite source. Repeat for every shared store.",
    ),
    migration_id: str = typer.Option(..., "--migration-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Copy, verify, atomically cut over, and resume one migration."""
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.daemon_protocol import discover_daemon_cutover_protocol
    from specify_cli.sync.project_store_migration import LegacyProjectStoreMigration

    manifest = LegacyProjectStoreMigration(
        get_runtime_root().base,
        tuple(source),
        daemon_protocol=discover_daemon_cutover_protocol(),
    ).migrate(migration_id)
    if json_output:
        _emit_project_store_migration_json(manifest.to_dict())
        return
    console.print(f"[green]Migration {manifest.migration_id}: {manifest.phase.value}[/green]")


@app.command()
def project_store_status(
    migration_id: str = typer.Option(..., "--migration-id"),
    diagnose_residue: bool = typer.Option(
        False,
        "--diagnose-residue",
        help="Compare immutable inventory with current legacy logical rows after cutover.",
    ),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show durable migration phase without opening legacy sources."""
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.project_store_migration import (
        LegacyProjectStoreMigration,
        migration_artifact_path,
    )

    # Status is manifest-only; the constructor still requires the explicit source
    # tuple, so recover it from the governed manifest after resolving its path.
    root = get_runtime_root().base
    try:
        import json

        manifest_path = migration_artifact_path(root, migration_id, "manifest.json")
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        sources = tuple(Path(item["path"]) for item in raw["sources"])
    except (OSError, TypeError, ValueError, KeyError) as exc:
        console.print(f"[red]Migration status unavailable:[/red] {exc}")
        raise typer.Exit(1) from exc
    migration = LegacyProjectStoreMigration(root, sources)
    if diagnose_residue:
        migration.diagnose_residue(migration_id)
    manifest = migration.status(migration_id)
    if json_output:
        _emit_project_store_migration_json(manifest.to_dict())
        return
    console.print(f"Migration {manifest.migration_id}: {manifest.phase.value}")


@app.command()
def project_store_quarantine(
    migration_id: str = typer.Option(..., "--migration-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Inspect permanently non-deliverable migration quarantine records."""
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.project_store_migration import migration_artifact_path

    root = get_runtime_root().base
    try:
        import json

        path = migration_artifact_path(root, migration_id, "quarantine.json")
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        console.print(f"[red]Migration quarantine unavailable:[/red] {exc}")
        raise typer.Exit(1) from exc
    if json_output:
        _emit_project_store_migration_json(raw)
        return
    records = raw if isinstance(raw, list) else []
    console.print(f"Migration {migration_id}: {len(records)} quarantined row(s)")
    for item in records:
        if isinstance(item, dict):
            console.print(f"  {item.get('table')}:{item.get('row_id')} — {item.get('reason')}")


def _migrated_history_envelopes(
    store: ProjectSyncStore,
    row_ids: tuple[str, ...],
) -> list[dict[str, object]]:
    """Load the exact capability cohort from its sealed project-store rows."""
    import json

    if not row_ids:
        return []
    with store.unit_of_work() as unit:
        placeholders = ", ".join("?" for _ in row_ids)
        rows = unit.execute(
            f"SELECT entry_id, payload_json FROM journal_entries WHERE project_uuid = ? AND entry_id IN ({placeholders})",  # noqa: S608  # nosec B608 -- count-derived placeholders; row ids remain bound
            (store.project_uuid.storage_token, *row_ids),
        ).fetchall()
    payloads = {str(row[0]): str(row[1]) for row in rows}
    if tuple(row_id for row_id in row_ids if row_id in payloads) != row_ids:
        raise RuntimeError("confirmed migrated history cohort is incomplete")
    envelopes: list[dict[str, object]] = []
    for row_id in row_ids:
        raw = json.loads(payloads[row_id])
        if not isinstance(raw, dict) or str(raw.get("event_id") or "") != row_id:
            raise RuntimeError(f"migrated history row {row_id!r} is not an exact event envelope")
        envelopes.append({str(key): value for key, value in raw.items()})
    return envelopes


@app.command()
def project_store_history(
    confirm_by: str | None = typer.Option(
        None,
        "--confirm-by",
        help="Explicit operator identity that confirms the displayed sealed cohort.",
    ),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
        help="Stable identity for an explicit confirmation.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Consume a confirmed capability and invoke WP07 preflight/upload.",
    ),
    history_action_id: str | None = typer.Option(
        None,
        "--history-action-id",
        help="Persisted action ID required by --apply.",
    ),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Preview, explicitly confirm, or disclose migrated sealed history."""
    from specify_cli.sync.history_disclosure import (
        HistoryDisclosureError,
        confirm_history_disclosure,
        consume_history_disclosure,
        preview_sealed_history,
    )

    confirming = confirm_by is not None or idempotency_key is not None
    if apply and confirming:
        console.print("[red]--apply and confirmation options are mutually exclusive.[/red]")
        raise typer.Exit(2)
    if confirming and (not str(confirm_by or "").strip() or not str(idempotency_key or "").strip()):
        console.print("[red]Confirmation requires both --confirm-by and --idempotency-key.[/red]")
        raise typer.Exit(2)
    if history_action_id is not None and not apply:
        console.print("[red]--history-action-id is valid only with --apply.[/red]")
        raise typer.Exit(2)

    runtime = _open_project_dispatch_runtime()
    try:
        if apply:
            action_id = str(history_action_id or "").strip()
            if not action_id:
                console.print("[red]--apply requires --history-action-id.[/red]")
                raise typer.Exit(2)
            token = _event_sync_access_token()
            if not token:
                console.print("[red]Not authenticated.[/red] Run `spec-kitty auth login` first.")
                raise typer.Exit(1)
            if runtime.delivery_target is None:
                console.print("[red]No admitted current project delivery target.[/red]")
                raise typer.Exit(1)
            receiver, server_url = _resolve_history_import_receiver(runtime, token=token)
            capability = consume_history_disclosure(
                runtime.store,
                action_id=action_id,
                context=runtime.context,
            )
            envelopes = _migrated_history_envelopes(
                runtime.store,
                capability.row_ids,
            )
            from specify_cli.sync.history_import.upload import run_import_upload

            report = run_import_upload(
                envelopes,
                receiver=receiver,
                server_url=server_url,
                auth_token=token,
                project_context=runtime.context,
                target=runtime.delivery_target,
                history_capability=capability,
            )
            payload = {
                "action_id": capability.action_id,
                "cohort_count": len(envelopes),
                "success": report.success,
                "duplicate": report.duplicate,
                "pending": report.pending,
                "rejected": report.rejected,
                "ok": report.ok,
            }
            if json_output:
                _emit_project_store_migration_json(payload)
            else:
                console.print(f"History action {capability.action_id}: {report.success} delivered, {report.duplicate} duplicate")
            if not report.ok:
                raise typer.Exit(1)
            return

        preview = preview_sealed_history(runtime.store)
        if confirming:
            capability = confirm_history_disclosure(
                runtime.store,
                preview,
                actor=str(confirm_by),
                idempotency_key=str(idempotency_key),
                context=runtime.context,
            )
            payload = {
                "action_id": capability.action_id,
                "project_uuid": capability.project_uuid,
                "row_ids": capability.row_ids,
                "source_epoch_ids": capability.source_epoch_ids,
                "preview_hash": capability.preview_hash,
                "state": "confirmed",
            }
        else:
            payload = {
                "project_uuid": preview.project_uuid,
                "row_ids": preview.row_ids,
                "source_epoch_ids": preview.source_epoch_ids,
                "preview_count": preview.preview_count,
                "preview_hash": preview.preview_hash,
                "state": "preview",
            }
        if json_output:
            _emit_project_store_migration_json(payload)
        else:
            console.print(f"Migrated sealed history: {len(preview.row_ids)} row(s), sha256:{preview.preview_hash}")
            if confirming:
                console.print(f"History action ID: {payload['action_id']}")
            else:
                console.print("Preview only; no confirmation or egress occurred.")
    except (HistoryDisclosureError, RuntimeError, ValueError) as exc:
        console.print(f"[red]Migrated history disclosure refused:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        runtime.close()


@app.command()
def migrate(
    no_cleanup: bool = typer.Option(
        False,
        "--no-cleanup",
        help=(
            "Import into the journal but do NOT delete the migrated rows from the "
            "source queues. Use to inspect the migration before the legacy-row "
            "boundary is converged; re-run `sync migrate` (without the flag) to clean up."
        ),
    ),
    resolve_conflicts: str = typer.Option(
        None,
        "--resolve-conflicts",
        help=(
            "Resolve divergent-duplicate conflicts so the boundary can converge. "
            "Only `keep-journal` is supported: the journal payload is canonical, so "
            "each conflicting source row is archived (quarantined) then removed. "
            "Explicit operator recovery; never overwrites the journal."
        ),
    ),
    backfill_consent_index: bool = typer.Option(
        False,
        "--backfill-consent-index",
        help=(
            "Also map path-keyed consent records onto the uuid-keyed index the "
            "drain reads. WRITES machine-global consent records, and the uuid "
            "index outranks a repo default — so this can change a project's "
            "effective answer. Opt-in for that reason; every change is listed."
        ),
    ),
) -> None:
    """Refuse the retired shared-store migration and point to copy-only cutover."""
    del no_cleanup, resolve_conflicts, backfill_consent_index
    console.print(
        "[red]The shared-store `sync migrate` path is retired.[/red] It could "
        "delete source evidence or promote legacy consent. Use "
        "`spec-kitty sync project-store-preview --source <db> --migration-id <id>` "
        "and then the explicit copy-only `project-store-migrate` command."
    )
    raise typer.Exit(1)


@app.command()
def mode(
    name: str | None = typer.Argument(
        None,
        help="Mode to set: TEAMSPACE | EXTERNAL_RECEIVER | LOCAL_RETENTION | OPT_OUT",
    ),
    endpoint: str | None = typer.Option(
        None,
        "--endpoint",
        help="External receiver endpoint URL (required for EXTERNAL_RECEIVER)",
    ),
) -> None:
    """Show or set the event-sync retention x delivery mode.

    With no argument, prints the current mode. Mode semantics (which receiver,
    whether the journal retains) are owned by the policy layer; the CLI only
    routes the operator token through it (FR-006).

    Examples:
        spec-kitty sync mode
        spec-kitty sync mode LOCAL_RETENTION
        spec-kitty sync mode EXTERNAL_RECEIVER --endpoint https://receiver.example/events
    """
    from specify_cli.delivery.config import EventSyncConfig, EventSyncConfigError, Mode

    if name is None:
        current = _load_event_sync_config()
        console.print(f"Event sync mode: [cyan]{current.mode.name}[/cyan]")
        return

    try:
        resolved_mode = Mode.from_token(name)
        config = EventSyncConfig.from_mode(resolved_mode, external_endpoint=endpoint)
    except EventSyncConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    _write_event_sync_config(config.mode, config.external_endpoint)
    console.print(f"[green]✓[/green] Event sync mode set to [cyan]{config.mode.name}[/cyan]")
    if config.mode is Mode.OPT_OUT:
        console.print(
            "[yellow]Note:[/yellow] OPT_OUT never silently drops Teamspace-bound events (C-008 fail-closed); such families are refused or audited at capture time."
        )


def _build_boundary_check_failures(
    *,
    failure_set: Any = None,
    daemon_mismatched_fields: list[str] | None = None,
    legacy_counts: Any = None,
    legacy_db_path: str | None = None,
    orphan_count: int | None = None,
    stranded_mission_slug: str | None = None,
) -> list[str]:
    """Return human-readable failure lines for the ``sync status --check`` gate.

    WP03 (T010): this function is now a thin renderer over
    :class:`specify_cli.sync.preflight.BoundaryFailureSet` — the single
    source of truth shared with :func:`run_preflight`. The function
    accepts EITHER a pre-computed *failure_set* (preferred) OR the
    legacy positional pieces (kept for callers that already constructed
    them); when only the legacy pieces are passed, the result is still
    derived from them.

    The gate trips (returns non-zero) when ANY of the three FR-009
    conditions hold: foreground/daemon disagree on a D-3 field, the
    legacy DB still has rows in any migration table for the active
    scope, or one or more orphaned daemon records exist.

    The returned list is empty when the boundary is coherent.
    """
    # Preferred path: derive from the structured failure set.
    if failure_set is not None:
        return _failure_lines_from_set(
            failure_set,
            stranded_mission_slug=stranded_mission_slug,
        )

    # Legacy path: compose lines from the previously-passed pieces.
    failures: list[str] = []
    if daemon_mismatched_fields:
        failures.append("foreground/daemon disagree on D-3 field(s): " + ", ".join(daemon_mismatched_fields))
    if legacy_counts:
        total = sum(legacy_counts.values())
        tables = ", ".join(f"{t}={c}" for t, c in sorted(legacy_counts.items()))
        line = f"legacy queue DB {legacy_db_path} has {total} row(s) pending migration ({tables})"
        if stranded_mission_slug:
            # FR-013: tag stranded setup-plan body uploads for the active mission.
            line += f" — setup-plan stranded mission slug {stranded_mission_slug}"
        failures.append(line)
    if orphan_count is not None and orphan_count > 0:
        failures.append(f"{orphan_count} orphan daemon record(s) detected; retire via `spec-kitty sync doctor`")
    return failures


def _failure_lines_from_set(
    failure_set: Any,
    *,
    stranded_mission_slug: str | None = None,
) -> list[str]:
    """Render the structured failure set as human-readable failure lines.

    Lines mirror the legacy ``_build_boundary_check_failures`` output so
    existing tests that grep for substrings keep working.
    """
    from specify_cli.sync.queue import _legacy_queue_db_path

    failures: list[str] = []

    mismatch_fields = [m.field for m in failure_set.mismatches]
    if mismatch_fields:
        # Legacy callers (and tests) expect bare canonical names; strip the
        # ``daemon_`` prefix to keep the on-screen tokens compact and to
        # preserve backwards-compatible substring matching.
        bare_fields = [f.removeprefix("daemon_") for f in mismatch_fields]
        failures.append("foreground/daemon disagree on D-3 field(s): " + ", ".join(bare_fields))

    if failure_set.legacy_rows_for_scope > 0:
        total = failure_set.legacy_rows_for_scope
        parts: list[str] = []
        if failure_set.legacy_event_rows > 0:
            parts.append(f"queue={failure_set.legacy_event_rows}")
        if failure_set.legacy_body_upload_rows > 0:
            parts.append(f"body_upload_queue={failure_set.legacy_body_upload_rows}")
        legacy_path = _legacy_queue_db_path()
        line = f"legacy queue DB {legacy_path} has {total} row(s) pending migration ({', '.join(parts)})"
        if stranded_mission_slug:
            line += f" — setup-plan stranded mission slug {stranded_mission_slug}"
        failures.append(line)

    n_orphans = len(failure_set.orphan_records)
    if n_orphans > 0:
        failures.append(f"{n_orphans} orphan daemon record(s) detected; retire via `spec-kitty sync doctor`")

    if failure_set.project_store_diagnostic is not None:
        failures.append(f"project-store boundary unavailable: {failure_set.project_store_diagnostic}")

    return failures


def _render_daemon_team_or_user(record: Any) -> str | None:
    """Render the daemon's ``team_or_user`` from its split fields.

    The on-disk record splits the identity across ``auth_principal`` and
    ``auth_team``; the canonical mismatch field combines them into a single
    ``team_or_user`` value so the operator sees one row, not two.
    """
    principal = getattr(record, "auth_principal", None)
    team = getattr(record, "auth_team", None)
    if not principal:
        return None
    if team:
        return f"{principal}/{team}"
    return str(principal)


def _print_boundary_section(
    target_console: Console,
    header: str,
    rows: list[tuple[str, str]],
) -> None:
    """WP02 cycle 1 / B-1: emit a boundary section as parser-friendly text.

    Each section in the Identity Boundary view (``Foreground:``,
    ``Daemon owner record:``, ``Active queue:``, ``Legacy queue:``) is
    rendered as:

    1. The section header on its own line, no leading indent, trailing colon.
    2. One row per ``(key, value)`` pair, indented by exactly two spaces,
       with the key and value separated by **two or more spaces** so the
       sibling canary parser's ``_KEY_VALUE_RE`` (``^\\s*(?P<key>\\S.*?)\\s{2,}(?P<value>.+?)\\s*$``)
       matches them as section children.

    The format mirrors the docstring in the sibling parser
    (``spec-kitty-end-to-end-testing/src/spec_kitty_e2e/identity_boundary/
    status_parser.py``) which documents:

        Active queue:
          Path                      <path>
          Event count               <int>

    Rendering uses plain ``Console.print`` with ``soft_wrap=True``,
    ``overflow="ignore"``, ``crop=False`` and ``no_wrap=True`` so long
    path values render verbatim under non-TTY capture (no Rich
    ellipsis), matching the ``--json`` byte-for-byte. The two-space key
    indent + 2+ spaces between key and value is the contract the parser
    enforces; do not collapse to a single separator space.

    Keys are padded to a fixed column so the rendering matches the
    operator-visible layout in the parser docstring, but the parser
    itself tolerates any amount of whitespace >= 2 between key and
    value.
    """
    target_console.print(header, soft_wrap=True, crop=False, highlight=False)
    if not rows:
        return
    # Fixed key column (24 chars after the 2-space indent) gives a
    # consistent, operator-friendly layout. The parser only requires
    # ``\s{2,}`` between key and value; this padding is purely cosmetic
    # but matches the layout sketched in the parser's docstring.
    key_col_width = 24
    for key, value in rows:
        # Right-pad the key so there are always >= 2 spaces before the
        # value (the key column is 24 chars; even a 22-char key still
        # leaves 2 trailing spaces before the value).
        padded_key = key.ljust(key_col_width)
        target_console.print(
            f"  {padded_key}{value}",
            soft_wrap=True,
            overflow="ignore",
            crop=False,
            no_wrap=True,
            highlight=False,
        )


@app.command()
def status(
    check_connection: bool = typer.Option(
        False,
        "--check",
        "-c",
        help=(
            "Test connection to server AND enforce the identity-boundary "
            "coherence gate (FR-009). Exits non-zero when foreground/daemon "
            "disagree, when legacy rows remain in the active scope, or when "
            "any orphan daemon record is present."
        ),
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=(
            "When combined with --check, emit a single JSON object on "
            "stdout matching contracts/sync-status-output.md and suppress "
            "the human-readable block. Exit code 0 if coherent, 2 otherwise."
        ),
    ),
) -> None:
    """Show sync queue status, connection state, and auth info.

    Displays:
    - Offline queue size
    - Connection / emitter status
    - Last sync timestamp
    - Auth status
    - Server URL configuration

    Use --check to test actual connectivity (adds 3s timeout if server unreachable).

    Examples:
        # Show status (fast)
        spec-kitty sync status

        # Test connection to server
        spec-kitty sync status --check
    """
    # T014: --check --json short-circuit. Emits a single JSON object on
    # stdout matching contracts/sync-status-output.md and exits 0/2 based
    # on the structured failure set. Suppresses the human-readable block.
    if check_connection is True and json_output is True:
        _emit_status_check_json()
        return

    # WP09 (A-1 restructure): the cc-90 gather-render interleave — network and
    # daemon I/O that ran BETWEEN row emissions — is now a three-phase shell.
    # Phase 1 gathers ALL I/O up front (``_gather_status_facts``); phase 2 hands
    # the facts to the pure ``sync_status_core`` (``build_status_view`` decides
    # every row/section, ``evaluate_boundary_coherence`` the --check verdict);
    # phase 3 renders. Zero observable change — the WP02 goldens are the guard.
    console.print()
    console.print("[cyan]Spec Kitty Sync Status[/cyan]")
    console.print()

    facts = _gather_status_facts(check_connection)
    view = build_status_view(facts)
    _render_status_body(facts, view)

    # --- --check coherence gate (WP03 / FR-009) ---------------------------
    # Returns non-zero when any FR-009 condition holds; ONLY under --check so the
    # read-only ``sync status`` surface keeps its exit-0 contract. The verdict is
    # assembled by the pure core from the canonical
    # ``_build_boundary_check_failures`` output — boundary logic is REUSED, never
    # re-implemented here (DIRECTIVE_044).
    if check_connection is True:
        fg_id = facts.failure_set.foreground
        verdict = evaluate_boundary_coherence(
            base_failures=_build_boundary_check_failures(
                failure_set=facts.failure_set,
                stranded_mission_slug=facts.stranded_tag,
            ),
            auth_present=fg_id.server_url is not None and fg_id.team_or_user is not None,
            auth_required=is_saas_sync_enabled(),
            orphan_count=(facts.orphan_report.orphan_count if facts.orphan_report is not None else 0),
            orphan_scan_diagnostic=facts.orphan_scan_diagnostic,
        )
        if verdict.failures:
            console.print(
                "[red]Identity boundary check FAILED:[/red]",
                style=None,
            )
            for line in verdict.failures:
                console.print(f"  [red]![/red] {line}")
            console.print()
            raise typer.Exit(verdict.exit_code)

    if facts.auth_recovery_pending:
        outcome = handle_unauthenticated_with_teamspace(
            command_name="sync status",
            console=console,
        )
        if outcome is RecoveryOutcome.EXIT_4:
            raise typer.Exit(EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE)


def _gather_status_facts(check_connection: bool) -> StatusFacts:
    """Phase 1 of the WP09 restructure: perform ALL of ``status``'s data I/O.

    Every network / daemon / runtime-open / token read that the cc-90 body
    interleaved between row emissions is hoisted here (architect finding A-1) so
    the pure ``sync_status_core`` decision functions and the render shell touch
    no I/O. ``scan_sync_daemons`` / ``get_sync_daemon_status`` keep their local
    ``from ... import`` so the WP02 golden's ``sync_daemon.<name>`` stub still
    intercepts; the ``sync``-module seams (``_check_server_connection`` /
    ``_event_sync_report`` / ``is_saas_sync_enabled``) are reached bare-name so a
    ``sync.<name>`` monkeypatch still intercepts (INV-4).
    """
    from specify_cli.auth import get_token_manager
    from specify_cli.auth.verdict import evaluate_auth_verdict
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.daemon import get_sync_daemon_status, scan_sync_daemons
    from specify_cli.sync.owner import (
        compute_foreground_identity,
        list_orphan_records,
        mismatched_fields,
        read_owner_record,
    )
    from specify_cli.sync.preflight import build_boundary_failure_set
    from specify_cli.sync.queue import _legacy_queue_db_path

    # Show the resolved runtime target (SPEC_KITTY_SAAS_URL precedence folded in)
    # — the URL sync actually hits — not the raw config.toml value (#2146).
    config = SyncConfig()
    server_url = config.resolve_runtime_target().resolved_server_url
    saas_enabled = is_saas_sync_enabled()

    local_report: dict[str, Any] | None = None
    try:
        local_runtime = _open_event_sync_runtime_readonly()
        local_report = _event_sync_report({}, local_runtime)
    except Exception as exc:
        _LOG.debug("project-store status unavailable: %s", exc)

    tm = get_token_manager()
    # ``sync status`` is offline (no server probe), so the verdict is derived from
    # the local session + clock: it resolves ``unknown`` — never a false green —
    # when the access token is expired and the refresh chain cannot be proven
    # offline (#3723).
    auth_verdict = evaluate_auth_verdict(tm.get_current_session(), now_utc())
    daemon_status = get_sync_daemon_status()

    queue_size = 0 if local_report is None else int(local_report["event_journal"]["retained_event_count"])
    body_queue_count = 0 if local_report is None else int(local_report["body_upload_compatibility"]["body_upload_queue_count"])

    # Optional --check network probe + live-daemon singleton scan (#829 / #1071).
    connection_status: str | None = None
    connection_note: str | None = None
    orphan_report: Any = None
    orphan_scan_diagnostic: str | None = None
    if check_connection is True:
        connection_status, connection_note = _check_server_connection(server_url)
        try:
            orphan_report = scan_sync_daemons()
        except Exception as exc:
            orphan_report = None
            orphan_scan_diagnostic = f"live daemon scan failed: {str(exc)[:200]}"

    # Identity-boundary facts (WP03 / FR-008): the structured failure set is the
    # single source of truth the boundary block AND the --check gate render from.
    foreground_identity = compute_foreground_identity()
    daemon_record = read_owner_record()
    daemon_mismatched = mismatched_fields(daemon_record, foreground_identity) if daemon_record is not None else []
    failure_set = build_boundary_failure_set(repo_root=Path.cwd())
    daemon_team_or_user = _render_daemon_team_or_user(daemon_record) if daemon_record is not None else None

    return StatusFacts(
        check_connection=check_connection,
        saas_enabled=saas_enabled,
        server_url=server_url,
        config_file=str(config.config_file),
        queue_size=queue_size,
        body_queue_count=body_queue_count,
        auth_verdict=auth_verdict,
        daemon_status=daemon_status,
        connection_status=connection_status,
        connection_note=connection_note,
        orphan_report=orphan_report,
        orphan_scan_diagnostic=orphan_scan_diagnostic,
        failure_set=failure_set,
        daemon_record=daemon_record,
        daemon_team_or_user=daemon_team_or_user,
        daemon_mismatched=daemon_mismatched,
        orphan_record_count=len(list_orphan_records()),
        legacy_db_path=str(_legacy_queue_db_path()),
        # Physical legacy residue is WP10 migration/quarantine evidence, never
        # live status authority; general status derives no stranded mission tag.
        stranded_tag=None,
        auth_recovery_pending=derive_auth_recovery_pending(connection_status),
    )


def _render_status_body(facts: StatusFacts, view: StatusView) -> None:
    """Phase 3 of the WP09 restructure: emit the already-decided view.

    Every ``(label, value)`` row, boundary section, and orphan-detail line is
    decided by ``sync_status_core``; this shell only prints, in the byte-stable
    order the WP02 goldens freeze (main table → orphan detail → queue health →
    per-project store → Identity Boundary → event-sync → hint).
    """
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")
    for row in view.main_rows:
        table.add_row(row.label, row.value)
    console.print(table)
    console.print()

    if view.orphan_detail_lines:
        console.print("[yellow]Other live ``run_sync_daemon`` processes detected outside the registered singleton (#1071):[/yellow]")
        for orphan_line in view.orphan_detail_lines:
            console.print(orphan_line)
        console.print("[dim]Run `spec-kitty sync doctor` for a guided cleanup, or kill the rogue processes manually.[/dim]")
        console.print()

    # --- Queue health section (T022/T023) ---
    if facts.queue_size > 0:
        console.print(f"[yellow]Project event store contains {facts.queue_size} retained event(s).[/yellow]")
        console.print()
    else:
        console.print("[green]Queue empty -- all events synced.[/green]")
        console.print()

    # --- Per-project journal composition (#3030 T021 / FR-015, SC-004) -----
    # ``status`` has no global issues list, so the per-project warnings print
    # inline here (the same placement rationale as ``doctor``).
    journal_issues: list[str] = []
    _render_per_project_store(console, journal_issues)
    for issue in journal_issues:
        console.print(f"  [yellow]![/yellow] {issue}")
    console.print()

    # --- Identity Boundary section (WP03 / FR-008) -------------------------
    # Emitted as plain line-oriented text (not a Rich Table) so canonical file
    # paths render full-width and the cross-repo canary parser can attribute
    # ``Path`` rows to their section headers (WP02 cycle 1 / B-1).
    boundary = view.boundary
    console.print("[bold]Identity Boundary[/bold]")
    _print_boundary_section(console, "Foreground:", boundary.foreground_rows)
    _print_boundary_section(console, "Daemon owner record:", boundary.daemon_rows)
    _print_boundary_section(console, "Active queue:", boundary.active_queue_rows)
    _print_boundary_section(console, "Legacy queue:", boundary.legacy_queue_rows)
    for key, value in boundary.top_level_rows:
        console.print(
            f"{key.ljust(24)}{value}",
            soft_wrap=True,
            overflow="ignore",
            crop=False,
            no_wrap=True,
            highlight=False,
        )
    console.print()
    if boundary.mismatch_rows:
        mismatch_detail = Table(
            title="Mismatch Detail",
            show_header=True,
            header_style="bold",
            box=None,
            expand=False,
        )
        mismatch_detail.add_column("Field", style="bold")
        mismatch_detail.add_column("Foreground")
        mismatch_detail.add_column("Daemon")
        for field_name, foreground_value, daemon_value in boundary.mismatch_rows:
            mismatch_detail.add_row(field_name, foreground_value, daemon_value)
        console.print(mismatch_detail)
        console.print()

    # Event-sync observability (WP12): active retention x delivery mode.
    _render_event_sync_status(console)
    console.print()

    if not facts.check_connection:
        console.print("[dim]Use 'spec-kitty sync status --check' to test connectivity.[/dim]")
        console.print()


@app.command()
def diagnose(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON instead of Rich table",
    ),
) -> None:
    """Validate queued events locally against the event schema.

    Reads all pending events from the offline queue and validates each one
    against the Pydantic Event model and per-event-type payload rules.

    Valid events are reported as passing; malformed events show specific
    field errors grouped by error category.

    Examples:
        spec-kitty sync diagnose
        spec-kitty sync diagnose --json
    """
    import json as json_mod

    from specify_cli.sync.diagnose import diagnose_events
    from specify_cli.sync.queue import OfflineQueue, get_max_queue_size

    try:
        max_queue_size = get_max_queue_size()
        runtime = _open_event_sync_runtime(include_target=False)
        with runtime.store.unit_of_work() as unit:
            queue = OfflineQueue(
                unit,
                runtime.store.layout_generation(),
                max_queue_size=max_queue_size,
            )
            pending = queue.drain_queue(limit=queue.MAX_QUEUE_SIZE)
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        message = f"project event store is unavailable; no queue-health claim was made: {exc}"
        if json_output:
            console.print(
                json_mod.dumps(
                    {"available": False, "error": message, "results": []},
                    sort_keys=True,
                )
            )
        else:
            console.print(f"[red]Unable to diagnose sync queue:[/red] {message}")
        raise typer.Exit(2) from exc

    if not pending:
        if json_output:
            console.print(json_mod.dumps({"total": 0, "valid": 0, "invalid": 0, "results": []}))
        else:
            console.print("[green]No pending events in queue.[/green]")
        return

    # drain_queue returns ProjectOutboxTask rows; the validator consumes the
    # envelope dict each task carries.
    results = diagnose_events([task.event for task in pending])

    valid_count = sum(1 for r in results if r.valid)
    invalid_count = sum(1 for r in results if not r.valid)

    if json_output:
        output = {
            "total": len(results),
            "valid": valid_count,
            "invalid": invalid_count,
            "results": [
                {
                    "event_id": r.event_id,
                    "event_type": r.event_type,
                    "valid": r.valid,
                    "errors": r.errors,
                    "error_category": r.error_category,
                }
                for r in results
            ],
        }
        console.print(json_mod.dumps(output, indent=2))
        return

    # Rich output
    console.print()
    console.print(f"Validated [cyan]{len(results)}[/cyan] event(s): [green]{valid_count} valid[/green], [red]{invalid_count} invalid[/red]")

    # Show valid events (brief)
    for r in results:
        if r.valid:
            console.print(f"  [green]VALID[/green]   {r.event_id} ({r.event_type})")

    # Show invalid events (detailed)
    for r in results:
        if not r.valid:
            category_label = f" [{r.error_category}]" if r.error_category else ""
            console.print(f"\n  [red]INVALID[/red] {r.event_id} ({r.event_type}){category_label}")
            for err in r.errors:
                console.print(f"    - {err}")

    console.print()


@app.command()
def doctor() -> None:
    """Diagnose sync health: queue, auth, and server connectivity.

    Runs a comprehensive check of offline queue state, authentication
    validity, and server reachability, printing actionable remediation
    steps for any issues found.

    Examples:
        spec-kitty sync doctor
    """
    # WP10 (A-1 restructure): the cc-73 gather-render interleave — network,
    # daemon and store I/O that ran BETWEEN issue-accumulating renders — is now a
    # three-phase shell. Phase 1 gathers ALL I/O up front (``_gather_doctor_facts``);
    # phase 2 hands the facts to the pure ``sync_doctor_core`` (``build_doctor_report``
    # decides the ordered issues + healthy/auth-missing verdicts, calling WP07's
    # store/consent/tracker compute halves); phase 3 renders. Zero observable change —
    # the WP02 goldens + the ~60 ``test_sync_doctor*`` patch-tests are the guard.
    facts = _gather_doctor_facts()
    report = build_doctor_report(facts)
    _render_doctor_report(facts, report)


def _gather_doctor_facts() -> DoctorFacts:
    """Phase 1 of the WP10 restructure: perform ALL of ``doctor``'s data I/O.

    Every queue-open, token, server-probe, daemon-scan, journal, consent and
    tracker read the cc-73 body interleaved between issue appends is hoisted here
    (architect finding A-1) so the pure ``sync_doctor_core`` and the render shell
    touch no I/O. Seams keep the exact import shape the ~60 patch-tests bind:
    ``scan_sync_daemons`` / ``_open_journal_readonly`` / ``build_per_project_store_report``
    resolve at their source so a ``sync_module.<name>`` / source-module monkeypatch
    still intercepts (INV-4/C-005), and ``_check_server_connection`` is reached
    bare-name so a ``sync.<name>`` patch still lands.

    The three shared store-report sections are read here for the report's issue
    decision; their render halves re-read (independent scoped read UoWs) purely to
    print, so the summary/verdict and the printed sections stay one truth.
    """
    from specify_cli.auth import get_token_manager
    from specify_cli.core.paths import locate_project_root
    from specify_cli.delivery.status_report import build_per_project_store_report
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.consent import consent_index_health, project_local_consent_fault
    from specify_cli.sync.daemon import scan_sync_daemons
    from specify_cli.sync.diagnose import diagnose_body_queue
    from specify_cli.sync.owner import list_orphan_records, owner_record_path
    from specify_cli.sync.queue import OfflineQueue, get_max_queue_size
    from specify_cli.tracker.config import load_tracker_config
    from specify_cli.tracker.local_service import LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS
    from specify_cli.tracker.saas_client import TRACKER_EGRESS_IDENTIFIER_KINDS

    # --- 1. Queue health ---
    stats: QueueStats | None = None
    body_diagnostics: dict[str, Any] | None = None
    queue_db: str | None = None
    queue_error: str | None = None
    try:
        max_queue_size = get_max_queue_size()
        runtime = _open_event_sync_runtime(include_target=False)
        with runtime.store.unit_of_work() as unit:
            authority = runtime.store.layout_generation()
            queue = OfflineQueue(unit, authority, max_queue_size=max_queue_size)
            body_queue = OfflineBodyUploadQueue(unit, authority, max_queue_size=max_queue_size)
            stats = queue.get_queue_stats()
            body_diagnostics = diagnose_body_queue(body_queue)["body_queue"]
            queue_db = str(runtime.store.database_path)
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        queue_error = str(exc)

    # --- 2. Auth status ---
    config = SyncConfig()
    # Resolved runtime target (env precedence folded in), not the raw config.toml
    # value, so the diagnostics row matches what sync hits (#2146).
    server_url = config.resolve_runtime_target().resolved_server_url
    tm = get_token_manager()
    session = tm.get_current_session()
    now = now_utc()
    if session is None:
        access_token_ok = False
        refresh_token_ok = False
    else:
        access_token_ok, refresh_token_ok = doctor_token_flags(session, now)

    # --- 3. Server reachability ---
    connection_status, connection_note = _check_server_connection(server_url)
    connection_is_healthy = any(marker in connection_status for marker in _HEALTHY_CONNECTION_MARKERS)
    connection_is_auth_owned = any(marker in connection_status for marker in _AUTH_OWNED_CONNECTION_MARKERS)

    # --- 3b. Daemon singleton invariant (spec-kitty#1071) ---
    singleton_report: Any = None
    singleton_scan_diagnostic: str | None = None
    try:
        singleton_report = scan_sync_daemons()
    except Exception as exc:
        singleton_report = None
        singleton_scan_diagnostic = f"live daemon scan failed: {str(exc)[:200]}"

    # --- 3c. Per-project journal composition (#3030 T021 / FR-015) ---
    # Mirrors ``_render_per_project_store``'s open/group I/O so the report can
    # decide the per-project issues; the render half re-reads to print the section.
    per_project_report: Any = None
    per_project_open_error: str | None = None
    per_project_group_error: str | None = None
    try:
        journal = _open_journal_readonly()
    except FileNotFoundError:
        journal = None  # benign absence: no journal yet, no issue
    except Exception as exc:  # noqa: BLE001 — reported as an issue, never swallowed
        per_project_open_error = str(exc)
        journal = None
    if journal is not None:
        try:
            per_project_report = build_per_project_store_report(journal)
        except Exception as exc:  # noqa: BLE001 — reported as an issue, never swallowed
            per_project_group_error = str(exc)
        finally:
            close = getattr(journal, "close", None)
            if callable(close):
                close()

    # --- 3d. Consent-record readability (#3030 FR-020 / FR-027) ---
    consent_index: Any = None
    consent_index_error: str | None = None
    try:
        consent_index = consent_index_health()
    except Exception as exc:  # noqa: BLE001 — a section that vanishes is the defect
        consent_index_error = str(exc)
    consent_local_fault: Any = None
    consent_local_error: str | None = None
    consent_repo_root_present = False
    try:
        consent_repo_root = locate_project_root(Path.cwd())
        consent_repo_root_present = consent_repo_root is not None
        consent_local_fault = None if consent_repo_root is None else project_local_consent_fault(consent_repo_root)
    except Exception as exc:  # noqa: BLE001 — reported, never silently skipped
        consent_local_error = str(exc)

    # --- 3e. Tracker egress (#3108 FR-014) ---
    tracker_root = locate_project_root(Path.cwd())  # may be None; a rendered case
    tracker_local = tracker_egress_verdict(
        tracker_root,
        destination=EgressDestination.LOCAL_SUBPROCESS,
        identifiers=LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS,
    )
    tracker_hosted = tracker_egress_verdict(
        tracker_root,
        destination=EgressDestination.HOSTED_SERVICE,
        identifiers=TRACKER_EGRESS_IDENTIFIER_KINDS,
    )
    tracker_binding_present = False
    if tracker_root is not None:
        try:
            tracker_binding_present = bool(load_tracker_config(tracker_root).provider)
        except Exception:  # noqa: BLE001 — doctor must render on a broken config, not abort
            tracker_binding_present = False

    # --- 4. Orphan daemon owner records (WP03 / FR-010) ---
    orphan_records = list(list_orphan_records())

    return DoctorFacts(
        queue_error=queue_error,
        queue_stats=stats,
        body_diagnostics=body_diagnostics,
        queue_db=queue_db,
        session=session,
        session_present=session is not None,
        access_token_ok=access_token_ok,
        refresh_token_ok=refresh_token_ok,
        server_url=server_url,
        connection_status=connection_status,
        connection_note=connection_note,
        connection_is_healthy=connection_is_healthy,
        connection_is_auth_owned=connection_is_auth_owned,
        singleton_report=singleton_report,
        singleton_scan_diagnostic=singleton_scan_diagnostic,
        per_project_report=per_project_report,
        per_project_open_error=per_project_open_error,
        per_project_group_error=per_project_group_error,
        consent_index_health=consent_index,
        consent_index_error=consent_index_error,
        consent_local_fault=consent_local_fault,
        consent_local_error=consent_local_error,
        consent_repo_root_present=consent_repo_root_present,
        tracker_local_verdict=tracker_local,
        tracker_hosted_verdict=tracker_hosted,
        tracker_binding_present=tracker_binding_present,
        orphan_records=orphan_records,
        orphan_record_count=len(orphan_records),
        owner_record_path=str(owner_record_path()),
    )


def _render_doctor_queue_rows(facts: DoctorFacts, table: Table) -> None:
    """Emit the queue-health rows (or the store-unavailable row) into *table*."""
    if facts.queue_error is not None:
        table.add_row("Project queue", f"[red]Unavailable[/red] ({facts.queue_error})")
        return
    stats = facts.queue_stats
    body_diagnostics = facts.body_diagnostics
    if stats is None or body_diagnostics is None:
        return
    queue_size = stats.total_queued
    max_size = stats.max_queue_size
    pct = (queue_size / max_size * 100) if max_size > 0 else 0
    depth_color = _depth_color(pct)
    table.add_row("Queue size", f"[{depth_color}]{queue_size:,} / {max_size:,} ({pct:.0f}%)[/{depth_color}]")
    if stats.oldest_event_age is not None:
        age_str = humanize_timedelta(stats.oldest_event_age)
        table.add_row("Oldest event", f"{age_str} ago")
    else:
        table.add_row("Oldest event", "[dim]n/a (empty)[/dim]")
    table.add_row("Queue DB", str(facts.queue_db))
    table.add_row(
        "Body uploads",
        f"{body_diagnostics['total_tasks']} queued, {body_diagnostics['recorded_failure_count']} recorded failure(s)",
    )


def _render_doctor_auth_rows(facts: DoctorFacts, table: Table) -> None:
    """Emit the server-URL + token/user/team rows into *table*."""
    table.add_row("Server URL", facts.server_url)
    session = facts.session
    if session is None:
        table.add_row("Auth", "[red]No credentials[/red]")
        return
    access_exp_dt = session.access_token_expires_at
    refresh_exp_dt = session.refresh_token_expires_at
    if facts.access_token_ok:
        table.add_row(_STATUS_ACCESS_TOKEN_LABEL, f"[green]Valid[/green] (expires {access_exp_dt.isoformat()})")
    elif access_exp_dt is not None:
        table.add_row(_STATUS_ACCESS_TOKEN_LABEL, f"[red]Expired[/red] ({access_exp_dt.isoformat()})")
    else:
        table.add_row(_STATUS_ACCESS_TOKEN_LABEL, "[red]Missing[/red]")
    if refresh_exp_dt is None:
        table.add_row(_STATUS_REFRESH_TOKEN_LABEL, "[green]Valid[/green] (no expiry stored)")
    elif facts.refresh_token_ok:
        table.add_row(_STATUS_REFRESH_TOKEN_LABEL, f"[green]Valid[/green] (expires {refresh_exp_dt.isoformat()})")
    else:
        table.add_row(_STATUS_REFRESH_TOKEN_LABEL, f"[red]Expired[/red] ({refresh_exp_dt.isoformat()})")
    username = session.email or session.name
    team_slug: str | None = None
    if session.teams:
        for team in session.teams:
            if team.id == session.default_team_id:
                team_slug = team.id
                break
        if team_slug is None:
            team_slug = session.teams[0].id
    if username:
        table.add_row("User", username)
    if team_slug:
        table.add_row("Team", team_slug)


def _render_doctor_singleton_rows(facts: DoctorFacts, table: Table) -> None:
    """Emit the server + daemon-singleton rows into *table*."""
    table.add_row("Server", facts.connection_status)
    if facts.connection_note:
        table.add_row("", f"[dim]{facts.connection_note}[/dim]")
    if facts.singleton_scan_diagnostic is not None:
        table.add_row("Daemon singleton", f"[red]Unavailable[/red] ({facts.singleton_scan_diagnostic})")
    report = facts.singleton_report
    if report is not None:
        if report.orphan_count == 0:
            table.add_row("Daemon singleton", "[green]OK[/green] (no orphan `run_sync_daemon` processes)")
        else:
            table.add_row("Daemon singleton", f"[yellow]{report.orphan_count} orphan daemon(s)[/yellow]")


def _render_doctor_detail_tables(facts: DoctorFacts) -> None:
    """Emit the optional orphan-process / top-event / body-failure / owner-record tables."""
    report = facts.singleton_report
    if report is not None and report.orphan_count > 0:
        orphan_table = Table(
            title="Orphan run_sync_daemon Processes",
            show_header=True,
            header_style=_WARNING_HEADER_STYLE,
            show_lines=False,
            expand=False,
        )
        orphan_table.add_column("PID", justify="right", style="yellow")
        orphan_table.add_column("Command line", overflow="fold")
        for orphan in report.orphan_processes:
            orphan_table.add_row(str(orphan.pid), " ".join(orphan.cmdline))
        console.print(orphan_table)
        console.print()

    stats = facts.queue_stats
    if stats is not None and stats.top_event_types:
        type_table = Table(
            title="Top Queued Event Types",
            show_header=True,
            header_style="bold",
            show_lines=False,
            expand=False,
        )
        type_table.add_column("Event Type", style="cyan")
        type_table.add_column("Count", justify="right")
        for event_type, count in stats.top_event_types:
            type_table.add_row(event_type, f"{count:,}")
        console.print(type_table)
        console.print()

    recent_failures = facts.body_diagnostics["recent_failures"] if facts.body_diagnostics is not None else []
    if recent_failures:
        failure_table = Table(
            title="Recent Body Upload Failures",
            show_header=True,
            header_style="bold",
            show_lines=False,
            expand=False,
        )
        failure_table.add_column("Artifact", style="cyan")
        failure_table.add_column("Mission", style="dim")
        failure_table.add_column("Count", justify="right")
        failure_table.add_column("Reason")
        for failure in recent_failures:
            failure_table.add_row(
                str(failure["artifact_path"]),
                str(failure["mission_slug"]),
                str(failure["failure_count"]),
                str(failure["failure_reason"]),
            )
        console.print(failure_table)
        console.print()

    if facts.orphan_records:
        orphan_table = Table(
            title="Orphan Daemons",
            show_header=True,
            header_style=_WARNING_HEADER_STYLE,
            show_lines=False,
            expand=False,
        )
        orphan_table.add_column("PID", justify="right", style="yellow")
        orphan_table.add_column("Port", justify="right")
        orphan_table.add_column("Version")
        orphan_table.add_column("Executable", overflow="fold")
        orphan_table.add_column("Started At")
        for record in facts.orphan_records:
            orphan_table.add_row(
                str(record.pid),
                str(record.port),
                record.package_version,
                record.executable_path,
                record.started_at,
            )
        console.print(orphan_table)
        console.print(f"[dim]Retire orphan record(s): rm {facts.owner_record_path}[/dim]")
        console.print()


def _render_doctor_report(facts: DoctorFacts, report: DoctorReport) -> None:
    """Phase 3 of the WP10 restructure: emit the already-decided doctor view.

    Prints the byte-stable Rich table, re-invokes the three shared render halves
    for their printed sections (their issue side effect is discarded — the
    authoritative issues live on ``report``), then the summary and the exit-4
    teamspace-recovery arm exactly as the pre-restructure shell did.
    """
    console.print()
    console.print("[bold cyan]Sync Doctor[/bold cyan]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim", min_width=20)
    table.add_column("Value")
    _render_doctor_queue_rows(facts, table)
    _render_doctor_auth_rows(facts, table)
    _render_doctor_singleton_rows(facts, table)
    console.print(table)
    console.print()

    # The three shared render halves print their sections; ``build_doctor_report``
    # already folded their findings (via WP07's compute halves) into ``report``,
    # so their ``issues`` side effect is intentionally discarded here (Pd-2).
    discard: list[str] = []
    _render_per_project_store(console, discard)
    _render_consent_readability(console, discard)
    _render_tracker_egress(
        console,
        discard,
        facts.tracker_local_verdict,
        facts.tracker_hosted_verdict,
        facts.tracker_binding_present,
    )
    console.print()

    _render_doctor_detail_tables(facts)

    # --- Summary ---
    if report.issues:
        console.print("[bold yellow]Issues found:[/bold yellow]")
        for issue in report.issues:
            console.print(f"  [yellow]![/yellow] {issue}")
        console.print()
    else:
        console.print("[bold green]No issues detected. Sync is healthy.[/bold green]")
        console.print()

    # --- Teamspace-aware recovery (issue #829, Mission 7) ---
    if report.auth_missing:
        outcome = handle_unauthenticated_with_teamspace(
            command_name="sync doctor",
            console=console,
        )
        if outcome is RecoveryOutcome.EXIT_4:
            raise typer.Exit(EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE)


# ─────────────────────────────────────────────────────────────────────────────
# WP03 HUSK COMPAT RE-EXPORT BLOCK — the single canonical seam-preservation door
# for the Wave-4 ``sync.py`` de-god (mission sync-cli-degod-wave4-01M0B0MX).
#
# This module is the durable *host* for the ``spec-kitty sync`` Typer app. As
# WP04→WP12 relocate private bodies out of ``sync.py`` into cohesive
# ``specify_cli.sync.*`` seam modules, each relocated private symbol MUST remain
# reachable as a ``sync.<name>`` MODULE ATTRIBUTE, because ~79 existing tests do
#     monkeypatch.setattr("...cli.commands.sync.<name>", <double>)
# and the deduplicated callee set they bind is the live, executable co-gate
# ``SYNC_MONKEYPATCH_SEAM_NAMES`` in
# ``tests/characterization/test_sync_cli_safe.py`` (27 distinct callees; INV-4,
# C-005). ``test_seam_callees_resolve_on_module`` asserts every one still
# resolves on this module.
#
# HOW LATER WPs USE THIS BLOCK (the runtime_bridge #2531 re-export precedent):
#   * A relocated private ``_foo`` moves to, e.g., ``specify_cli.sync.sync_status``.
#   * That relocation adds exactly ONE line here — the guarded re-import that
#     re-establishes the ``sync.<name>`` attribute on THIS host module:
#         from specify_cli.sync.sync_status import _foo as _foo  # noqa: F401,E402
#     (This is the ALLOWED import direction: relocated seam module -> host. It is
#     NOT an early-bind of a patched name, so it is exempt from the AST guard.)
#   * Nothing is relocated yet, so this block is intentionally empty today; it is
#     the SINGLE place later WPs add such re-imports (do not scatter them).
#
# THE LATE-BIND CALLING CONVENTION (binding for every WP04+ relocation):
#   A relocated *shell* that must call a monkeypatched callee reaches it by
#   ATTRIBUTE ACCESS ON THE HOST MODULE OBJECT — never by an early-bound
#   ``from ...cli.commands.sync import <name>``. Concretely:
#         import specify_cli.cli.commands.sync as sync_module
#         ...
#         sync_module._foo(...)          # or getattr(sync_module, "_foo")
#   Rationale: ``monkeypatch.setattr(sync_module, "_foo", <double>)`` rebinds the
#   MODULE ATTRIBUTE. A module-level ``from ...sync import _foo`` captures the
#   ORIGINAL object into a local name that a post-import ``setattr`` can never
#   see, silently defeating the patch seam. ``tests/architectural/
#   test_sync_no_early_bind.py`` is the AST guard that fails any future WP that
#   early-binds a name in ``SYNC_MONKEYPATCH_SEAM_NAMES`` from this module.
#
# THE ``@app.command`` SHELLS STAY HERE (INV-4 / WP-translation guard #2):
#   Only extracted *logic* relocates. The ``@app.command``/``@app.callback``
#   decorated thin shells remain defined in THIS module — moving a decorated
#   command changes which callable Typer registers and invokes, breaking the
#   golden CLI contract (WP02). Later WPs thin these shells in place; they never
#   move them out.
# ─────────────────────────────────────────────────────────────────────────────

# WP04 — render adapter relocated to ``specify_cli.sync.sync_render`` (the
# Console-emit + ``--json``-envelope family, behind the reused ``Render`` port).
# These re-imports re-establish each relocated symbol as a ``sync.<name>`` MODULE
# ATTRIBUTE so the ~60 patch-tests and every internal bare-name call site still
# resolve. This is the ALLOWED import direction (seam module -> host); none of
# these names are in ``SYNC_MONKEYPATCH_SEAM_NAMES``, so the AST early-bind guard
# does not police them.
from specify_cli.sync.sync_render import (  # noqa: E402
    _build_queue_summary_lines as _build_queue_summary_lines,
    _emit_project_store_migration_json as _emit_project_store_migration_json,
    _emit_status_check_json as _emit_status_check_json,
    _print_cleanup_result as _print_cleanup_result,
    _print_identity_backfill_result as _print_identity_backfill_result,
    _print_migration_result as _print_migration_result,
    _print_resolution_result as _print_resolution_result,
    _print_retention_result as _print_retention_result,
    _render_drain_blockers as _render_drain_blockers,
    _render_event_sync_status as _render_event_sync_status,
    _render_per_project_store as _render_per_project_store,
    _render_retry_distribution as _render_retry_distribution,
    _render_top_event_types as _render_top_event_types,
    format_queue_health as format_queue_health,
)

# WP05 — runtime-open/lifecycle + config-I/O adapters relocated to
# ``specify_cli.sync.sync_runtime`` (the two distinct read/dispatch openers, the
# retention/journal openers, and the event-sync config reader/writer family).
# These re-imports re-establish each relocated symbol as a ``sync.<name>`` MODULE
# ATTRIBUTE so the ~60 patch-tests and every internal bare-name call site (and the
# late-bound ``sync_module.<name>`` accesses in ``sync_render``/``sync_runtime``)
# still resolve. This is the ALLOWED import direction (seam module -> host); the
# seam names among them (``_open_event_sync_runtime``, ``_open_project_dispatch_runtime``,
# ``_open_journal_readonly``, ``_load_event_sync_config``, ``_event_sync_access_token``)
# are re-established here as host attributes, NOT early-bound off the host, so the
# AST early-bind guard does not police them (the host module is exempt).
from specify_cli.sync.sync_runtime import (  # noqa: E402
    _EventSyncRuntime as _EventSyncRuntime,
    _ProjectDispatchRuntime as _ProjectDispatchRuntime,
    _ScopedStatusJournal as _ScopedStatusJournal,
    _event_sync_access_token as _event_sync_access_token,
    _event_sync_config_path as _event_sync_config_path,
    _load_event_sync_config as _load_event_sync_config,
    _open_active_body_queue as _open_active_body_queue,
    _open_event_sync_runtime as _open_event_sync_runtime,
    _open_event_sync_runtime_readonly as _open_event_sync_runtime_readonly,
    _open_journal_readonly as _open_journal_readonly,
    _open_project_dispatch_runtime as _open_project_dispatch_runtime,
    _open_retention_runtime_or_exit as _open_retention_runtime_or_exit,
    _read_event_sync_table as _read_event_sync_table,
    _write_event_sync_config as _write_event_sync_config,
)

# WP06 — the ``sync purge`` subsystem split into a pure core + an I/O exec seam.
# The pure census/outcome shapes, the ``_PURGE_*`` scope constants, and every
# differential/verdict function relocated to ``specify_cli.sync.sync_purge_core``
# (provably ``Console``/filesystem/SQLite-free). These re-imports re-establish
# each relocated symbol as a ``sync.<name>`` MODULE ATTRIBUTE so the ``purge``
# shell's bare-name calls and ``test_the_cli_and_local_commit_agree_on_where_
# frames_live`` (which reads ``sync._PURGE_SYNC_STATE_RELPATH``) still resolve.
# This is the ALLOWED import direction (seam module -> host); none of these names
# are in ``SYNC_MONKEYPATCH_SEAM_NAMES``, so the AST early-bind guard does not
# police them.
from specify_cli.sync.sync_purge_core import (  # noqa: E402
    _PURGE_ALL_SCOPE_NOTE as _PURGE_ALL_SCOPE_NOTE,
    _PURGE_BODY as _PURGE_BODY,
    _PURGE_FRAMES as _PURGE_FRAMES,
    _PURGE_JOURNAL as _PURGE_JOURNAL,
    _PURGE_LEDGER as _PURGE_LEDGER,
    _PURGE_NON_ATOMIC_NOTE as _PURGE_NON_ATOMIC_NOTE,
    _PURGE_NULL_KEY as _PURGE_NULL_KEY,
    _PURGE_STORE_LABELS as _PURGE_STORE_LABELS,
    _PURGE_SYNC_STATE_RELPATH as _PURGE_SYNC_STATE_RELPATH,
    _PurgeStoreOutcome as _PurgeStoreOutcome,
    _purge_differential as _purge_differential,
    _purge_faults as _purge_faults,
    _purge_frames_scope as _purge_frames_scope,
    _purge_ledger_differential as _purge_ledger_differential,
    _purge_ledger_view as _purge_ledger_view,
    _purge_left_behind as _purge_left_behind,
    _purge_not_reached as _purge_not_reached,
    _purge_outcomes as _purge_outcomes,
    _purge_selector_line as _purge_selector_line,
    _purge_stored_spelling_conflicts as _purge_stored_spelling_conflicts,
    _purge_unattributable_keys as _purge_unattributable_keys,
    _RawCensus as _RawCensus,
)

# WP06 — the census readers, store executors, pre-open refusals, ``--project``
# resolver and operator report relocated to ``specify_cli.sync.sync_purge_exec``
# (everything that touches the journal / ledger / body queue / frame file /
# ``Console``). Re-established here as ``sync.<name>`` module attributes for the
# same reason. The total-purge primitives these executors invoke keep their
# operator-attended-only reachability — ``test_no_unattended_caller_of_the_total_
# purge_primitives`` allowlists ``sync/sync_purge_exec.py`` for exactly that.
from specify_cli.sync.sync_purge_exec import (  # noqa: E402
    _purge_body_census as _purge_body_census,
    _purge_frames_census as _purge_frames_census,
    _purge_journal_census as _purge_journal_census,
    _purge_journal_ids as _purge_journal_ids,
    _purge_journal_selection as _purge_journal_selection,
    _purge_ledger_census as _purge_ledger_census,
    _purge_ledger_ghost_count as _purge_ledger_ghost_count,
    _purge_print_verdict as _purge_print_verdict,
    _purge_render as _purge_render,
    _purge_resolve_project as _purge_resolve_project,
    _purge_run_body_queue as _purge_run_body_queue,
    _purge_run_journal_ledger as _purge_run_journal_ledger,
    _purge_usage_error as _purge_usage_error,
    _purge_validate_invocation as _purge_validate_invocation,
)

# WP07 — the pure compute half of the three shared store-report render helpers
# (``_render_per_project_store`` / ``_render_consent_readability`` /
# ``_render_tracker_egress``) plus the already-pure derivations they lean on
# relocated to ``specify_cli.sync.sync_store_report_core`` (provably
# ``Console``-free). Re-established here as ``sync.<name>`` module attributes so a
# late-bound ``sync_module._event_sync_report`` / ``sync_module._per_project_store_issues``
# still resolves (INV-4) and a ``monkeypatch.setattr("...sync._event_sync_report", ...)``
# still intercepts. This is the ALLOWED import direction (seam module -> host);
# none of these names is early-bound off the host module.
# WP07 — the three authority surfaces (READ daemon-owner coherence, WRITE
# repository sharing, delivery-ADMISSION asserts) relocated to
# ``specify_cli.sync.sync_authority``, each a thin delegate to its canonical
# surface (``preflight`` / ``sharing_client`` / ``target_authority``). Re-established
# here as ``sync.<name>`` module attributes so ``sync_runtime._open_project_dispatch_runtime``
# keeps reaching the admission asserts late-bound (``sync_module._assert_*``), a
# ``monkeypatch.setattr("...sync._require_daemon_owner_coherence", ...)`` still
# intercepts (INV-4), and the ``share``/``unshare`` write commands reach the WRITE
# adapters as module globals. ALLOWED import direction (seam module -> host).
from specify_cli.sync.sync_authority import (  # noqa: E402
    _assert_delivery_target_matches_context as _assert_delivery_target_matches_context,
    _assert_event_sync_runtime_authority as _assert_event_sync_runtime_authority,
    _require_daemon_owner_coherence as _require_daemon_owner_coherence,
    leave_repository_share as leave_repository_share,
    request_repository_share as request_repository_share,
)
from specify_cli.sync.sync_store_report_core import (  # noqa: E402
    _CHANNEL1_STATE_WORDING as _CHANNEL1_STATE_WORDING,
    _CONSENT_FAULT_NOT_ABSENCE as _CONSENT_FAULT_NOT_ABSENCE,
    _NO_RECORDED_NAME as _NO_RECORDED_NAME,
    _empty_selection_cause as _empty_selection_cause,
    _event_sync_report as _event_sync_report,
    _per_project_store_issues as _per_project_store_issues,
    channel1_state_wording as channel1_state_wording,
    consent_fault_view as consent_fault_view,
    tracker_egress_row_issue as tracker_egress_row_issue,
)

# WP08 — the ``sync now`` dispatch subsystem split into a pure core + an I/O exec
# seam. The pure ``DispatchSummary`` reductions, the oversized-batch predicate, the
# transient-message builder, the ``_HTTP_*``/message constants, and — the
# load-bearing extraction — the pure ``DispatchSummary → exit`` decision
# (``decide_sync_now_exit`` + ``SyncNowExitAction``) relocated to
# ``specify_cli.sync.sync_dispatch_core`` (provably ``Console``/network-free).
# These re-imports re-establish each relocated symbol as a ``sync.<name>`` MODULE
# ATTRIBUTE so the thinned ``_enforce_sync_now_exit_from_dispatch`` wrapper, the
# ``_handle_sync_now_unauthenticated`` message reference, and the
# ``test_sync_routes`` ``_transient_block_message`` / ``_batch_is_oversized`` /
# message-constant assertions all still resolve on this host. ALLOWED import
# direction (seam module -> host); none of these names is in
# ``SYNC_MONKEYPATCH_SEAM_NAMES``, so the AST early-bind guard does not police them.
from specify_cli.sync.sync_dispatch_core import (  # noqa: E402
    _HTTP_AUTH_STATUSES as _HTTP_AUTH_STATUSES,
    _HTTP_PAYLOAD_TOO_LARGE as _HTTP_PAYLOAD_TOO_LARGE,
    _OVERSIZED_ERROR_MARKER as _OVERSIZED_ERROR_MARKER,
    _OVERSIZED_SYNC_NOW_MESSAGE as _OVERSIZED_SYNC_NOW_MESSAGE,
    _PROTOCOL_MISMATCH_HALT_NOTICE as _PROTOCOL_MISMATCH_HALT_NOTICE,
    _TRANSIENT_SYNC_NOW_MESSAGE as _TRANSIENT_SYNC_NOW_MESSAGE,
    _UNAUTHENTICATED_SYNC_NOW_MESSAGE as _UNAUTHENTICATED_SYNC_NOW_MESSAGE,
    _batch_is_oversized as _batch_is_oversized,
    _combine_dispatch_summaries as _combine_dispatch_summaries,
    _protocol_mismatch_guidance as _protocol_mismatch_guidance,
    _transient_block_message as _transient_block_message,
    SyncNowExitAction as SyncNowExitAction,
    decide_sync_now_exit as decide_sync_now_exit,
)

# WP08 — the SaaSQueue delivery executors relocated to
# ``specify_cli.sync.sync_dispatch_exec`` (receiver resolution, the batch driver,
# and ``_run_event_sync_dispatch`` — everything that touches the journal / ledger /
# receiver / network / ``Console``). Re-established here as ``sync.<name>`` module
# attributes so the ``now`` shell's bare-name ``_run_event_sync_dispatch()`` call,
# the ``import-history`` bare-name ``_resolve_gated_receiver(...)`` call, and every
# ``monkeypatch.setattr("...sync._resolve_active_receiver" / "..._resolve_gated_receiver"
# / "..._run_dispatch_batches" / "..._run_event_sync_dispatch", ...)`` seam still
# resolve on this host (INV-4). ALLOWED import direction (seam module -> host); the
# seam names among them are re-established here as host attributes, NOT early-bound
# off the host, so the AST early-bind guard does not police them.
from specify_cli.sync.sync_dispatch_exec import (  # noqa: E402
    _resolve_active_receiver as _resolve_active_receiver,
    _resolve_gated_receiver as _resolve_gated_receiver,
    _run_dispatch_batches as _run_dispatch_batches,
    _run_event_sync_dispatch as _run_event_sync_dispatch,
)

# WP09 — the ``status`` cc-90 de-god (architect finding A-1): the interleaved
# gather-render is restructured into a ``gather-all-I/O -> pure core -> render``
# shell. The pure decision core (the ``(label, value)`` row + boundary-section
# builders, the ``--check`` verdict assembler, and the display constants moved
# for a single source of truth) relocated to ``specify_cli.sync.sync_status_core``
# (provably ``Console``/print/network/fs-free). These re-imports re-establish each
# symbol as a ``sync.<name>`` MODULE ATTRIBUTE so the thinned ``status`` shell's
# bare-name calls resolve and the moved constants keep their ``sync.<CONST>``
# reachability. ALLOWED import direction (seam module -> host); none of these
# names is in ``SYNC_MONKEYPATCH_SEAM_NAMES``, so the AST early-bind guard does
# not police them.
from specify_cli.sync.sync_status_core import (  # noqa: E402
    _ABSENT_VALUE as _ABSENT_VALUE,
    _BOUNDARY_LABEL_EXECUTABLE_PATH as _BOUNDARY_LABEL_EXECUTABLE_PATH,
    _BOUNDARY_LABEL_PACKAGE_VERSION as _BOUNDARY_LABEL_PACKAGE_VERSION,
    _BOUNDARY_LABEL_QUEUE_DB_PATH as _BOUNDARY_LABEL_QUEUE_DB_PATH,
    _BOUNDARY_LABEL_SERVER_URL as _BOUNDARY_LABEL_SERVER_URL,
    _BOUNDARY_LABEL_SOURCE_PATH as _BOUNDARY_LABEL_SOURCE_PATH,
    _BOUNDARY_LABEL_TEAM_USER as _BOUNDARY_LABEL_TEAM_USER,
    _MISMATCHED_FIELDS_LABEL as _MISMATCHED_FIELDS_LABEL,
    _STATUS_LAST_SYNC_LABEL as _STATUS_LAST_SYNC_LABEL,
    _UNSET_VALUE as _UNSET_VALUE,
    _ZERO_STATUS as _ZERO_STATUS,
    BoundarySections as BoundarySections,
    BoundaryVerdict as BoundaryVerdict,
    StatusFacts as StatusFacts,
    StatusRow as StatusRow,
    StatusView as StatusView,
    build_status_view as build_status_view,
    derive_auth_recovery_pending as derive_auth_recovery_pending,
    evaluate_boundary_coherence as evaluate_boundary_coherence,
)

# WP10 — the pure decision core for ``doctor``: the ``DoctorFacts`` gather bundle,
# the ``DoctorReport`` verdict, ``build_doctor_report`` (which folds WP07's
# store/consent/tracker compute halves into the ordered issues), and the
# ``doctor_token_flags`` helper shared by the gather phase and the render shell.
# Re-established here as ``sync.<name>`` module attributes for the WP06/WP07
# relocation pattern (ALLOWED import direction: seam module -> host).
from specify_cli.sync.sync_doctor_core import (  # noqa: E402
    DoctorFacts as DoctorFacts,
    DoctorReport as DoctorReport,
    build_doctor_report as build_doctor_report,
    doctor_token_flags as doctor_token_flags,
)

# WP11 — the pure decision core for ``sync workspace``: the ``SyncResult`` -> render
# plan mapping (``build_sync_render_plan`` + the ``RenderLine``/``RenderConflicts``/
# ``RenderChanges`` step markers and ``SyncRenderPlan``) and the ``NOT_IN_WORKSPACE_*``
# constants for the ``mission_slug is None`` arm. The status dispatch's cc-heavy
# ``if/elif`` chain relocated here so the ``sync_workspace`` shell (the last
# C901-suppressed site in this module) measures <= 15 with the suppression
# removed. Re-established as ``sync.<name>`` module attributes (ALLOWED import
# direction: seam module -> host).
from specify_cli.sync.sync_workspace_core import (  # noqa: E402
    NOT_IN_WORKSPACE_EXIT as NOT_IN_WORKSPACE_EXIT,
    NOT_IN_WORKSPACE_LINES as NOT_IN_WORKSPACE_LINES,
    RenderChanges as RenderChanges,
    RenderConflicts as RenderConflicts,
    RenderLine as RenderLine,
    SyncRenderPlan as SyncRenderPlan,
    build_sync_render_plan as build_sync_render_plan,
)

__all__ = ["app"]
