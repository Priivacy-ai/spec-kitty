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
from dataclasses import dataclass, field
from kernel.clock import UTC, now_utc, parse_iso, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import urlparse

import typer
from rich.console import Console
from specify_cli.cli.console import console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from specify_cli.delivery.config import EventSyncConfig, Mode
    from specify_cli.delivery.dispatcher import DispatchSummary
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.delivery.receivers import DeliveryReceiver, GateDecision
    from specify_cli.delivery.retention import RetentionResult
    from specify_cli.delivery.status_report import (
        PerProjectStoreReport,
        ProjectStoreRow,
        UnresolvedIdentityCandidate,
    )
    from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.sync.history_import import UploadReport
    from specify_cli.sync.project_identity import IdentityBackfillResult
    from specify_cli.sync.migrate_journal import (
        CleanupResult,
        ConflictResolution,
        ConvergeResult,
        MigrationAudit,
        MigrationResult,
    )
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
    SyncStatus,
    get_vcs,
)

from specify_cli.sync.queue import QueueStats
from specify_cli.core.saas_sync_config import saas_sync_opt_in_recorded_message
from kernel.clock import now_utc_iso
from specify_cli.sync.feature_flags import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)
from specify_cli.tracker.egress_verdict import (
    CHANNEL1_GRANTED,
    CHANNEL1_NOT_CONSENTABLE,
    CHANNEL1_NO_RECORD,
    CHANNEL1_RECORDED_REFUSAL,
    CHANNEL1_UNCLASSIFIED,
    CHANNEL1_UNDETERMINED,
    EgressDestination,
    TrackerEgressVerdict,
    tracker_egress_verdict,
)


_LOG = logging.getLogger(__name__)

_STATUS_ACCESS_TOKEN_LABEL = "Access token"  # noqa: S105
_STATUS_REFRESH_TOKEN_LABEL = "Refresh token"  # noqa: S105
_STATUS_LAST_SYNC_LABEL = "Last Sync"
_UNAUTHENTICATED_SYNC_NOW_MESSAGE = (
    "not authenticated: no valid access token. Run `spec-kitty auth login`."
)
_OVERSIZED_SYNC_NOW_MESSAGE = (
    "sync batch exceeded the server size limit; the CLI retried with smaller "
    "batches. Re-run `spec-kitty sync now` if events remain."
)
_TRANSIENT_SYNC_NOW_MESSAGE = (
    "sync delivery failed transiently; no events were lost. Re-run "
    "`spec-kitty sync now` (see `--report` for per-event detail)."
)
# HTTP 413 is how the SaaS sync ingress (Fly proxy + edge) rejects an
# over-cap batch; see apps/sync/limits.py (512 KiB decompressed ceiling).
_HTTP_PAYLOAD_TOO_LARGE = 413
_OVERSIZED_ERROR_MARKER = "retry with a smaller batch"
_HTTP_AUTH_STATUSES = frozenset({401, 403})
_WARNING_HEADER_STYLE = "bold yellow"
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


def _string_or(value: object | None, fallback: str) -> str:
    """Return *fallback* when *value* is falsey, otherwise coerce to ``str``."""
    return str(value) if value else fallback


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


_DRAIN_BLOCKED_HELP = {
    "ready": "Ready to drain.",
    "sync_disabled": "SaaS sync disabled for this checkout — run `spec-kitty sync opt-in`.",
    "no_auth": "Not authenticated — run `spec-kitty auth login`.",
    "no_team": "No Private Teamspace available — refresh membership in dashboard.",
}


def _build_queue_summary_lines(stats: QueueStats) -> list[str]:
    """Build the queue-health summary lines shown in the panel."""
    summary_lines: list[str] = []
    pct = (stats.total_queued / stats.max_queue_size * 100) if stats.max_queue_size > 0 else 0
    depth_color = "red" if pct >= 100 else ("yellow" if pct >= 80 else "green")
    summary_lines.append(
        f"[bold]Queue Depth:[/bold] [{depth_color}]{stats.total_queued:,} / {stats.max_queue_size:,}[/{depth_color}] "
        f"({pct:.0f}%)"
    )
    summary_lines.append(f"[bold]Retried:[/bold]    {stats.total_retried:,}")
    if stats.oldest_event_age is not None:
        age_str = humanize_timedelta(stats.oldest_event_age)
        summary_lines.append(f"[bold]Oldest Event:[/bold] {age_str} ago")

    if stats.drain_blocked_counts:
        ready = stats.drain_blocked_counts.get("ready", 0)
        blocked = stats.total_queued - ready
        ready_color = "green" if blocked == 0 else "yellow"
        summary_lines.append(
            f"[bold]Drain Ready:[/bold] [{ready_color}]{ready:,} ready[/{ready_color}]"
            f" / [yellow]{blocked:,} blocked[/yellow]"
        )
    return summary_lines


def _render_drain_blockers(stats: QueueStats, target_console: Console) -> None:
    """Render the drain-blocker breakdown when blocked items exist."""
    blocked_only = {k: v for k, v in stats.drain_blocked_counts.items() if k != "ready" and v > 0}
    if not blocked_only:
        return

    block_table = Table(
        title="Drain Blockers",
        show_header=True,
        header_style="bold",
        show_lines=False,
        expand=False,
    )
    block_table.add_column("Reason", style="yellow")
    block_table.add_column("Count", justify="right")
    block_table.add_column("Remediation", style="dim")
    for reason, count in sorted(blocked_only.items(), key=lambda kv: -kv[1]):
        block_table.add_row(
            reason,
            str(count),
            _DRAIN_BLOCKED_HELP.get(reason, ""),
        )
    target_console.print(block_table)


def _render_retry_distribution(stats: QueueStats, target_console: Console) -> None:
    """Render retry buckets when queue retry stats are present."""
    if not stats.retry_distribution:
        return

    retry_table = Table(
        title="Retry Distribution",
        show_header=True,
        header_style="bold",
        show_lines=False,
        expand=False,
    )
    retry_table.add_column("Bucket", style="dim")
    retry_table.add_column("Count", justify="right")

    for bucket in ("0 retries", "1-3 retries", "4+ retries"):
        if bucket in stats.retry_distribution:
            retry_table.add_row(bucket, str(stats.retry_distribution[bucket]))

    target_console.print(retry_table)


def _render_top_event_types(stats: QueueStats, target_console: Console) -> None:
    """Render the top event types table when data is available."""
    if not stats.top_event_types:
        return

    type_table = Table(
        title="Top Event Types",
        show_header=True,
        header_style="bold",
        show_lines=False,
        expand=False,
    )
    type_table.add_column("Event Type", style="cyan")
    type_table.add_column("Count", justify="right")

    for event_type, count in stats.top_event_types:
        type_table.add_row(event_type, str(count))

    target_console.print(type_table)


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
        console.print(
            "[green]Logged in.[/green] Re-run "
            "[bold]spec-kitty sync now[/bold] to continue."
        )
        return
    console.print(f"[yellow]{_UNAUTHENTICATED_SYNC_NOW_MESSAGE}[/yellow]")
    if strict:
        raise typer.Exit(1)


def _enforce_sync_now_exit_from_dispatch(
    strict: bool,
    queue_size: int,
    summary: DispatchSummary | None,
    *,
    retained_work_present: bool = False,
) -> None:
    """Apply the strict ``spec-kitty sync now`` exit contract to the dispatch outcome.

    The journal-based dispatcher is now the sole event-delivery path, so the
    legacy ``_enforce_sync_now_exit`` semantics are mapped onto its
    :class:`DispatchSummary` plus the pending-work signal. The base code drew a
    deliberate line between two unauthenticated shapes and this mapping keeps it:

    * The dispatcher *selected* events and attempted delivery but none
      progressed (every selected event came back rejected / transient /
      terminal-failed — a logged-out 401 maps the whole batch to ``transient``;
      see :mod:`specify_cli.delivery.receivers`). This is the dispatch analogue
      of the legacy per-event ``unauthenticated`` result (the old
      ``error_count > 0`` shape) → the *graceful* "unauthenticated / sync-blocked"
      report with exit 1 (Issue #829). It must NOT be reclassified as the
      "nothing attempted / blocked" teamspace-recovery case below.
    * There is pending work (a non-empty legacy queue, or events selected) but
      the dispatcher attempted *nothing* — the dispatch analogue of the legacy
      "queue non-empty but all-zero result". This is routed through the
      teamspace-aware recovery so the unauthenticated UX (interactive login,
      structured exit 4, legacy exit 1) is preserved regardless of ``--strict``.
    * Partial progress with any rejected, transient, or terminal failure → exit
      1 under ``--strict``.

    A ``None`` summary means dispatch infrastructure was unavailable. Under
    ``--strict`` that is a failure only when retained or legacy work exists.
    """
    if summary is None:
        if strict and (queue_size > 0 or retained_work_present):
            raise typer.Exit(1)
        return

    selected = summary.selected if summary is not None else 0
    progressed = (
        summary.delivered + summary.duplicate + summary.pending if summary is not None else 0
    )

    # Selected work made no durable progress. A pure gate/auth block records no
    # rows, so route it through teamspace-aware recovery; transport/content
    # failures still use the legacy strict exit.
    if selected > 0 and progressed == 0 and summary.recorded == 0:
        _handle_sync_now_unauthenticated(strict)
        return
    if selected > 0 and progressed == 0 and summary.transient > 0:
        console.print(f"[yellow]{_transient_block_message(summary)}[/yellow]")
        if strict:
            raise typer.Exit(1)
        return
    if selected > 0 and progressed == 0 and summary.recorded > 0:
        # Rejected and terminal-failed rows are concrete delivery outcomes, not
        # evidence that authentication blocked the attempt. The dispatch
        # summary already exposes their counts; preserve --strict semantics
        # without sending the operator through auth recovery.
        if strict:
            raise typer.Exit(1)
        return

    # Pending work but nothing was even attempted → teamspace-aware recovery.
    work_present = queue_size > 0 or selected > 0
    if work_present and progressed == 0:
        _handle_sync_now_unauthenticated(strict)
        return
    errors = summary.rejected + summary.transient + summary.terminal_failed
    if strict and errors > 0:
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


def format_queue_health(stats: QueueStats, target_console: Console) -> None:
    """Render queue health metrics as Rich panels/tables.

    Displays:
    - Summary panel with queue depth, retried count, and oldest event age
    - Retry distribution table (bucketed)
    - Top event types table (up to 5)
    - Drain-blocker breakdown (issue #1075) — only when non-empty.

    Args:
        stats: Aggregate queue statistics from OfflineQueue.get_queue_stats()
        target_console: Rich Console to print to (allows testing with captured output)
    """
    summary_lines = _build_queue_summary_lines(stats)
    target_console.print(
        Panel(
            "\n".join(summary_lines),
            title="Queue Health",
            border_style="cyan",
            expand=False,
        )
    )

    _render_drain_blockers(stats, target_console)
    _render_retry_distribution(stats, target_console)
    _render_top_event_types(stats, target_console)


# --------------------------------------------------------------------------- #
# Event-sync wiring (WP12) — THIN glue over WP01/WP07/WP09/WP11 domain modules. #
# Every count/decision is owned by a domain module; this layer only resolves    #
# already-canonical handles and prints/serialises their results (plan IC-08).   #
# --------------------------------------------------------------------------- #

_DELIVERY_SUBDIR = "delivery"
_LEDGER_DB_NAME = "ledger.db"
_REGISTRY_DB_NAME = "targets.db"

# Operator event-sync mode is persisted under a dedicated config.toml table so
# it never collides with the [sync] target-authority keys (FR-016 / C-007).
_EVENT_SYNC_TABLE = "event_sync"
_EVENT_SYNC_MODE_KEY = "mode"
_EVENT_SYNC_ENDPOINT_KEY = "external_endpoint"
_EVENT_SYNC_DISPATCH_BATCH_LIMIT = 1000


def _delivery_dir() -> Path:
    """The spec-kitty-home directory that holds the ledger + target registry."""
    from specify_cli.paths import get_runtime_root

    base: Path = get_runtime_root().base
    return base / _DELIVERY_SUBDIR


def _ledger_db_path() -> Path:
    """Canonical on-disk path of the WP05 delivery ledger."""
    return _delivery_dir() / _LEDGER_DB_NAME


def _registry_db_path() -> Path:
    """Canonical on-disk path of the WP04 delivery-target registry."""
    return _delivery_dir() / _REGISTRY_DB_NAME


@dataclass
class _EventSyncRuntime:
    """The already-resolved domain handles the thin CLI hands to the dispatcher
    / status-report / retention modules. The CLI never derives scope or URLs
    itself — it only opens these and passes them through (contract §1)."""

    target: ResolvedSyncTarget
    journal: EventJournal
    ledger: SqliteDeliveryLedger
    registry: SqliteDeliveryTargetRegistry

    def close(self) -> None:
        # Closing the diagnostic SQLite handles must never mask the primary
        # result, so a close failure is intentionally swallowed.
        with contextlib.suppress(Exception):
            self.ledger.close()
        with contextlib.suppress(Exception):
            self.registry.close()


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


def _open_event_sync_runtime(*, create: bool = True) -> _EventSyncRuntime:
    """Resolve the WP01 target and open the journal/ledger/registry handles.

    Uses the same producer scope as live capture so ``sync now`` drains the
    journal that emitters actually write. ``create=False`` is for read-only
    diagnostics: it refuses absent DB files instead of creating schemas.
    """
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
    from specify_cli.event_journal.journal import EventJournal, resolve_journal_path
    from specify_cli.sync.target_authority import resolve_sync_target

    scope = _current_event_sync_scope()
    target = resolve_sync_target(user_id=scope.user_id, team_slug=scope.team_slug)
    journal_path = resolve_journal_path(
        user_id=scope.user_id, team_slug=scope.team_slug
    )
    ledger_path = _ledger_db_path()
    registry_path = _registry_db_path()
    if create:
        _delivery_dir().mkdir(parents=True, exist_ok=True)
    else:
        if not journal_path.exists():
            raise FileNotFoundError(f"event-sync journal DB absent: {journal_path}")
    journal = EventJournal(journal_path)
    ledger = SqliteDeliveryLedger(
        str(ledger_path) if create or ledger_path.exists() else ":memory:"
    )
    registry = SqliteDeliveryTargetRegistry(
        str(registry_path) if create or registry_path.exists() else ":memory:"
    )
    return _EventSyncRuntime(target=target, journal=journal, ledger=ledger, registry=registry)


def _open_event_sync_runtime_readonly() -> _EventSyncRuntime:
    """Open runtime handles only when DBs already exist."""
    try:
        return _open_event_sync_runtime(create=False)
    except TypeError:
        # Compatibility for tests that monkeypatch the opener with a no-arg callable.
        return _open_event_sync_runtime()


def _event_sync_config_path() -> Path:
    from specify_cli.sync.config import SyncConfig

    return Path(SyncConfig().config_file)


def _read_event_sync_table() -> dict[str, Any]:
    """Best-effort read of the ``[event_sync]`` config table (empty when absent)."""
    import toml

    path = _event_sync_config_path()
    if not path.exists():
        return {}
    try:
        data = toml.load(path)
    except (toml.TomlDecodeError, OSError):
        return {}
    table = data.get(_EVENT_SYNC_TABLE)
    return table if isinstance(table, dict) else {}


def _load_event_sync_config() -> EventSyncConfig:
    """Reconstruct the persisted :class:`EventSyncConfig` (defaults to TEAMSPACE).

    Mode semantics are owned by WP09 — the CLI only stores/reads the token and
    rebuilds the config through ``EventSyncConfig.from_mode``.
    """
    from specify_cli.delivery.config import EventSyncConfig, EventSyncConfigError, Mode

    table = _read_event_sync_table()
    token = table.get(_EVENT_SYNC_MODE_KEY)
    if not token:
        return EventSyncConfig.from_mode(Mode.TEAMSPACE)
    endpoint = table.get(_EVENT_SYNC_ENDPOINT_KEY)
    try:
        return EventSyncConfig.from_mode(
            Mode.from_token(str(token)),
            external_endpoint=str(endpoint) if endpoint else None,
        )
    except EventSyncConfigError as exc:
        # A corrupt persisted token must not break read paths (status/now).
        _LOG.debug("event-sync mode %r unusable, defaulting to TEAMSPACE: %s", token, exc)
        return EventSyncConfig.from_mode(Mode.TEAMSPACE)


def _write_event_sync_config(mode: Mode, external_endpoint: str | None) -> None:
    """Persist the operator's event-sync mode token (and optional endpoint)."""
    import toml

    from specify_cli.core.atomic import atomic_write

    path = _event_sync_config_path()
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = toml.load(path)
        except (toml.TomlDecodeError, OSError):
            data = {}
    table = data.get(_EVENT_SYNC_TABLE)
    if not isinstance(table, dict):
        table = {}
        data[_EVENT_SYNC_TABLE] = table
    table[_EVENT_SYNC_MODE_KEY] = mode.value
    if external_endpoint:
        table[_EVENT_SYNC_ENDPOINT_KEY] = external_endpoint
    else:
        table.pop(_EVENT_SYNC_ENDPOINT_KEY, None)
    atomic_write(path, toml.dumps(data), mkdir=True)


def _event_sync_access_token() -> str:
    """Best-effort Bearer token for the Teamspace receiver (empty when absent).

    The dispatcher never POSTs an empty selection, so an absent token degrades
    safely to no delivery rather than an error.
    """
    import asyncio

    from specify_cli.auth import get_token_manager

    try:
        token_manager = get_token_manager()
        if not token_manager.is_authenticated:
            return ""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            token = loop.run_until_complete(token_manager.get_access_token())
        finally:
            with contextlib.suppress(Exception):
                asyncio.set_event_loop(None)
            loop.close()
        return token or ""
    except Exception as exc:  # best-effort credential read; never block a drain
        _LOG.debug("event-sync access token unavailable: %s", exc)
        return ""


def _resolve_active_receiver(
    target: ResolvedSyncTarget, config: EventSyncConfig, *, auth_token: str | None = None
) -> DeliveryReceiver | None:
    """Resolve the WP06 receiver for the active mode via WP09 (or ``None``).

    Mode→receiver resolution is owned by ``EventSyncConfig.resolve``; the CLI
    only supplies the Teamspace Bearer token to the default factory.
    """
    from specify_cli.delivery.config import DefaultReceiverFactory

    token = _event_sync_access_token() if auth_token is None else auth_token
    factory = DefaultReceiverFactory(teamspace_auth_token=token)
    policy = config.resolve(resolved_target=target, receiver_factory=factory)
    return policy.receiver


def _event_sync_gate_context(
    receiver: DeliveryReceiver, target: ResolvedSyncTarget, *, auth_token: str
) -> Any:
    """Build the explicit receiver-gate context for the active target."""
    from specify_cli.delivery.receivers import GateContext

    return GateContext(
        saas_enabled=is_saas_sync_enabled(),
        private_teamspace=bool(target.team_slug),
        auth_present=bool(auth_token),
        endpoint_configured=bool(getattr(receiver, "endpoint_url", "")),
    )


def _resolve_gated_receiver(
    target: ResolvedSyncTarget, config: EventSyncConfig, *, auth_token: str
) -> tuple[DeliveryReceiver | None, GateDecision | None]:
    """Resolve the active receiver and evaluate its gates — data only, no policy.

    Shared by ``sync now`` (:func:`_run_event_sync_dispatch`) and
    ``import-history --apply`` (:func:`_resolve_history_import_receiver`); the
    two callers previously duplicated this resolve+evaluate sequence and had
    already diverged (#2884 P2). Returns ``(None, None)`` when the mode has no
    receiver (retention-only). Otherwise returns the receiver and its
    :class:`GateDecision` — each caller decides what a blocked decision means:
    ``sync now`` degrades to a dim best-effort notice, ``import-history`` fails
    closed with ``typer.Exit(1)``. Neither policy lives here.
    """
    from specify_cli.delivery.receivers import evaluate_gates

    receiver = _resolve_active_receiver(target, config, auth_token=auth_token)
    if receiver is None:
        return None, None
    gate_decision = evaluate_gates(
        receiver, _event_sync_gate_context(receiver, target, auth_token=auth_token)
    )
    return receiver, gate_decision


def _count_retained_events(runtime: _EventSyncRuntime) -> int:
    with contextlib.suppress(Exception):
        return len(runtime.journal.read_all())
    return 0


def _event_sync_retained_work_present() -> bool:
    """Best-effort retained-work probe for strict infrastructure failures."""
    runtime: _EventSyncRuntime | None = None
    try:
        runtime = _open_event_sync_runtime_readonly()
        return _count_retained_events(runtime) > 0
    except Exception:
        from specify_cli.event_journal.journal import resolve_journal_path

        scope = _current_event_sync_scope()
        path = resolve_journal_path(
            user_id=scope.user_id,
            team_slug=scope.team_slug,
        )
        return path.exists() and path.stat().st_size > 0
    finally:
        if runtime is not None:
            runtime.close()


def _combine_dispatch_summaries(
    left: DispatchSummary, right: DispatchSummary
) -> DispatchSummary:
    from specify_cli.delivery.dispatcher import DispatchSummary

    return DispatchSummary(
        target_id=left.target_id or right.target_id,
        selected=left.selected + right.selected,
        delivered=left.delivered + right.delivered,
        duplicate=left.duplicate + right.duplicate,
        pending=left.pending + right.pending,
        rejected=left.rejected + right.rejected,
        transient=left.transient + right.transient,
        terminal_failed=left.terminal_failed + right.terminal_failed,
        failures=(*left.failures, *right.failures),
        retryable_event_ids=(
            *left.retryable_event_ids,
            *right.retryable_event_ids,
        ),
    )


def _batch_is_oversized(summary: DispatchSummary) -> bool:
    """Whether a batch was rejected wholesale for exceeding the server size cap.

    The count-based batch limit cannot see decompressed byte size, so a backlog
    whose events fit the 1000-event limit can still crowd the SaaS 512 KiB
    ceiling (apps/sync/limits.py). The edge proxy answers HTTP 413 and the WP06
    receiver maps that to a batch-wide ``transient`` carrying the oversized
    error (``_BATCH_OVERSIZED_ERROR`` = "retry with a smaller batch"). This is
    the signal that we should honor that documented contract and shrink.
    """
    failures = summary.failures
    is_wholesale_transient = (
        summary.selected > 0
        and summary.transient == summary.selected
        and len(failures) == summary.selected
    )
    return is_wholesale_transient and all(
        failure.outcome == "transient"
        and (
            failure.http_status == _HTTP_PAYLOAD_TOO_LARGE
            or (
                failure.error is not None
                and _OVERSIZED_ERROR_MARKER in failure.error.lower()
            )
        )
        for failure in failures
    )


def _transient_block_message(summary: DispatchSummary) -> str:
    """Explain a wholesale-transient drain accurately instead of always blaming auth.

    The legacy heuristic reported every all-transient batch as "not
    authenticated", which mislabels a 413 (batch too large) or a 5xx as a
    logged-out session and sends operators chasing auth. Classify by the actual
    failure status instead.
    """
    statuses = {f.http_status for f in summary.failures if f.http_status is not None}
    if _HTTP_PAYLOAD_TOO_LARGE in statuses:
        return _OVERSIZED_SYNC_NOW_MESSAGE
    if statuses & _HTTP_AUTH_STATUSES:
        return _UNAUTHENTICATED_SYNC_NOW_MESSAGE
    return _TRANSIENT_SYNC_NOW_MESSAGE


def _run_dispatch_batches(
    runtime: _EventSyncRuntime,
    receiver: DeliveryReceiver,
    delivery_target: Any,
) -> DispatchSummary:
    from specify_cli.delivery.dispatcher import DispatchSummary, dispatch

    combined = DispatchSummary.empty()
    limit = _EVENT_SYNC_DISPATCH_BATCH_LIMIT
    skip: set[str] = set()
    while True:
        batch = dispatch(
            journal=runtime.journal,
            ledger=runtime.ledger,
            receiver=receiver,
            target=delivery_target,
            limit=limit,
            exclude=frozenset(skip),
        )
        # Honor the documented "retry with a smaller batch" contract: a
        # byte-oversized batch (HTTP 413, nothing delivered) is halved and
        # retried rather than surrendered as transient. dispatch() leaves those
        # events undelivered, so the smaller re-selection picks the same events
        # up. A single oversized event is terminal-failed by the receiver (not
        # transient), so limit==1 can never loop forever.
        if limit > 1 and batch.delivered == 0 and _batch_is_oversized(batch):
            limit = max(1, limit // 2)
            continue
        combined = _combine_dispatch_summaries(combined, batch)
        # Advance past retryable events that made no terminal-success this pass
        # (pending, content rejection, persistent transient). Skipping them for
        # the REST OF THIS PASS lets deliverable events behind them drain
        # instead of a poison batch halting the loop; the ledger keeps them
        # selectable for the next `sync now`, so retryability is preserved.
        before = len(skip)
        skip.update(batch.retryable_event_ids)
        terminal_progress = (
            batch.delivered + batch.duplicate + batch.terminal_failed
        ) > 0
        # Grow a shrunk limit back after terminal progress. A single event over
        # the server byte cap forces `limit` down to 1 and is parked
        # (terminal_failed); without recovery the entire *healthy* tail would
        # then drain one-event-per-POST for the rest of the pass -- correct but
        # a throughput cliff. Multiplicative increase mirrors the halving and is
        # capped at the count default, so throughput recovers within a few
        # batches while the per-batch byte contract is still honored: an
        # over-grown batch simply 413s and re-halves, which is bounded.
        if terminal_progress and limit < _EVENT_SYNC_DISPATCH_BATCH_LIMIT:
            limit = min(_EVENT_SYNC_DISPATCH_BATCH_LIMIT, limit * 2)
        advanced = terminal_progress or len(skip) > before
        if batch.selected == 0 or not advanced:
            break
    return combined


def _open_active_body_queue() -> Any:
    """Open the body-upload queue for the WP11 ``body_upload_compatibility``
    section, or ``None`` when it cannot be read (the section then reports zeros)."""
    try:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue
        from specify_cli.sync.queue import OfflineQueue

        return OfflineBodyUploadQueue(db_path=OfflineQueue().db_path)
    except Exception as exc:  # read-only diagnostic; never fail status on it
        _LOG.debug("body-upload queue unavailable for status report: %s", exc)
        return None


def _open_migration_audit_readonly() -> MigrationAudit | None:
    """Open the WP10 migration-audit store best-effort (or ``None``).

    Only opens when the audit DB already exists on disk so that a status read
    never *creates* the migration store as a side effect. Any failure degrades
    to ``None`` (debug-logged) so the ``migration_conflicts`` section falls back
    to its empty default instead of breaking the status surface.
    """
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.migrate_journal import AUDIT_DB_NAME, MigrationAudit

    audit_path = get_runtime_root().base / AUDIT_DB_NAME
    if not audit_path.exists():
        return None
    try:
        return MigrationAudit(audit_path)
    except Exception as exc:  # read-only diagnostic; never fail status on it
        _LOG.debug("migration audit unavailable for status report: %s", exc)
        return None


def _event_sync_report(base: dict[str, Any], runtime: _EventSyncRuntime) -> dict[str, Any]:
    """Merge the seven WP11 additive sections onto *base* (CLI serialises only).

    Opens the WP10 migration-audit store (read-only, best-effort) so the
    ``migration_conflicts`` section surfaces real divergent-duplicate conflicts
    that block cleanup (SC-011) rather than always reporting an empty set.
    """
    from specify_cli.delivery.status_report import build_status_report

    audit = _open_migration_audit_readonly()
    try:
        return build_status_report(
            resolved_target=runtime.target,
            journal=runtime.journal,
            ledger=runtime.ledger,
            target_registry=runtime.registry,
            migration_audit=audit,
            body_upload_queue=_open_active_body_queue(),
            base=base,
        )
    finally:
        if audit is not None:
            with contextlib.suppress(Exception):
                audit.close()


#: Opening words of the empty-selection diagnosis. One constant because three tests
#: and two surfaces key on it, and because "nothing was selected" has to be sayable
#: in words — ``(selected 0)`` inside a counts line is not a diagnosis.
_NOTHING_TO_DELIVER = "Nothing to deliver."


def _empty_selection_cause(report: PerProjectStoreReport) -> str:
    """Explain WHY a drain selected nothing, using only what the report can prove.

    FR-005 asks the drain to "report the real cause". Before this, `sync now` printed
    an all-zero counts line ending ``(selected 0)`` and stopped, which collapses four
    situations that need four different actions:

    * the journal is empty — nothing to do, and emphatically not a consent problem;
    * no project has consented — the operator's data will never ship until they act,
      which is the incident's own shape and the only one that is urgent;
    * every row's identity is unresolved — recoverable, and H4 wired the remedy;
    * a consented project's rows exist but none is selectable right now.

    That last branch is deliberately the weakest claim. Distinguishing "already
    delivered" from "terminally drain-blocked" needs ledger state the report does not
    carry, so it names both possibilities instead of asserting one. Guessing here
    would recreate exactly the wrong-and-actionable diagnosis the no-Private-Teamspace
    message was: an operator told the wrong cause acts on the wrong thing.

    Sourced entirely from :func:`build_per_project_store_report` — the same grouping
    that backs `doctor`, `status` and `migrate`, so the four surfaces cannot disagree
    about who is in the store (C-003). No second classifier.
    """
    if not report.rows:
        return (
            "The event journal is empty — no events have been captured for this "
            "producer scope yet, so there is nothing to send."
        )

    total = report.counted_event_total
    if report.unresolved_identity_count >= total > 0:
        return (
            f"All {total} retained event(s) have no stored project identity, so none "
            "of them can be selected for delivery. Run `spec-kitty sync migrate` to "
            "recover the identity of any whose stored payload still carries it."
        )

    if not any(row.consent_granted for row in report.rows):
        named = ", ".join(
            (row.repo_slug or row.project_slug or row.project_uuid or "<unnamed>")
            for row in report.named_non_consenting_rows
        )
        detail = f": {named}" if named else ""
        return (
            f"No project in the event journal has consented to hosted sync{detail}. "
            f"Its {total} retained event(s) stay on this machine and will never be "
            "delivered until consent is recorded — run `spec-kitty sync enable` in "
            "the project that should ship, or `spec-kitty sync doctor` for the full "
            "per-project breakdown."
        )

    return (
        "Every consented project's retained events have already been delivered to "
        "this target, or are terminally drain-blocked. Nothing is being withheld "
        "for lack of consent; `spec-kitty sync doctor` shows the per-project state."
    )


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
    except Exception as exc:  # noqa: BLE001 - explanatory only, never fatal
        _LOG.debug("empty-selection diagnosis unavailable: %s", exc)
        console.print(
            f"[yellow]{_NOTHING_TO_DELIVER}[/yellow] The reason could not be "
            f"determined ({str(exc)[:80]}); `spec-kitty sync doctor` reports the "
            "journal's per-project state."
        )
        return
    console.print(f"[yellow]{_NOTHING_TO_DELIVER}[/yellow] {_empty_selection_cause(report)}")


def _print_dispatch_summary(summary: DispatchSummary, mode_name: str) -> None:
    """Render the dispatcher's per-outcome counts (sourced, never recomputed)."""
    console.print(
        f"Event sync ([cyan]{mode_name}[/cyan]): "
        f"[green]delivered {summary.delivered}[/green]  "
        f"[dim]duplicate {summary.duplicate}[/dim]  "
        f"[yellow]pending {summary.pending}[/yellow]  "
        f"rejected {summary.rejected}  transient {summary.transient}  "
        f"[red]terminal-failed {summary.terminal_failed}[/red]  "
        f"(selected {summary.selected})"
    )


def _print_retention_result(result: RetentionResult) -> None:
    """Render a WP11 retention result (counts owned by ``RetentionResult``)."""
    console.print(
        f"{result.operation}: "
        f"archived {result.archived_count}  purged {result.purged_count}  "
        f"skipped {result.skipped_count}  "
        f"(journal {result.journal_size_bytes_before} -> "
        f"{result.journal_size_bytes_after} bytes)"
    )


def _print_migration_result(result: MigrationResult) -> None:
    """Render a WP10 queue→journal migration result (counts owned by the result)."""
    console.print(
        "Queue migration: "
        f"[green]imported {len(result.imported_event_ids)}[/green]  "
        f"[dim]deduped {len(result.deduped)}[/dim]  "
        f"[red]conflicts {len(result.conflicts)}[/red]  "
        f"[red]source_errors {sum(1 for source in result.sources if source.error)}[/red]  "
        f"(exit_code {result.exit_code})"
    )
    if result.cleanup_blocked:
        console.print(
            "[yellow]Cleanup blocked[/yellow]: unresolved migration conflicts or "
            "source read/import errors remain — resolve them before deleting source queues."
        )
    for source in result.sources:
        if source.error:
            console.print(
                f"[red]Source {source.digest} failed[/red]: {source.error}"
            )
    console.print(f"[dim]{result.note}[/dim]")


def _print_cleanup_result(cleanup: CleanupResult) -> None:
    """Render the post-migration source-queue cleanup (#2665)."""
    if not cleanup.ran:
        return
    console.print(
        "Source cleanup: "
        f"[green]deleted {cleanup.total_deleted}[/green] migrated row(s) "
        f"from {cleanup.sources_cleaned} source queue(s) "
        "(boundary now converges; sync now / opt-in no longer refuse)."
    )
    for outcome in cleanup.outcomes:
        if outcome.error:
            console.print(
                f"[red]Cleanup error on source {outcome.digest}[/red]: {outcome.error}"
            )


def _print_resolution_result(resolution: ConflictResolution) -> None:
    """Render keep-journal conflict resolution (#2665)."""
    console.print(
        "Conflict resolution (keep-journal): "
        f"[green]resolved {resolution.resolved_count}[/green] (archived to quarantine)  "
        f"[yellow]skipped {len(resolution.skipped)}[/yellow]  "
        f"already-absent {len(resolution.already_absent)}"
    )
    if resolution.skipped:
        console.print(
            "[yellow]Skipped conflicts are not yet canonical in the journal or their "
            "source is gone — left intact.[/yellow]"
        )


def _run_event_sync_dispatch() -> DispatchSummary | None:
    """Drive the WP07 dispatcher over the resolved active target.

    This is the SOLE event-delivery path for ``sync now`` (the destructive
    legacy offline-queue event drain is retired). Returns the
    :class:`DispatchSummary` so the caller can derive the strict exit code; any
    infrastructure failure degrades to a dim notice and ``None`` rather than
    crashing the command (NFR-006). Non-delivering modes return an empty summary.
    Delivery outcomes surface via the printed summary; the journal is never
    deleted on success (FR-001).
    """
    if not is_saas_sync_enabled():
        from specify_cli.delivery.dispatcher import DispatchSummary

        return DispatchSummary.empty()
    from specify_cli.delivery.dispatcher import DispatchSummary

    runtime: _EventSyncRuntime | None = None
    try:
        runtime = _open_event_sync_runtime()
        config = _load_event_sync_config()
        auth_token = _event_sync_access_token()
        receiver, gate_decision = _resolve_gated_receiver(
            runtime.target, config, auth_token=auth_token
        )
        if receiver is None:
            console.print(
                f"[dim]Event sync mode {config.mode.name}: retention only; "
                f"no delivery attempted.[/dim]"
            )
            return DispatchSummary.empty()
        if gate_decision is None:
            # Invariant: a resolved (non-None) receiver always carries a
            # decision from _resolve_gated_receiver. An explicit raise (not
            # assert) keeps this guard live under `python -O`; the
            # surrounding `except Exception` still degrades it to a dim
            # notice + None, same as before (this function must never break
            # the command — NFR-006).
            raise RuntimeError("resolved receiver carries no gate decision")
        if gate_decision.blocked:
            names = ", ".join(gate.name for gate in gate_decision.unsatisfied)
            console.print(f"[dim]Event sync gated: {names}[/dim]")
            return DispatchSummary(
                target_id=None,
                selected=_count_retained_events(runtime),
                delivered=0,
                duplicate=0,
                pending=0,
                rejected=0,
                transient=0,
                terminal_failed=0,
            )
        delivery_target = runtime.registry.register_from_resolved(runtime.target)
        summary = _run_dispatch_batches(runtime, receiver, delivery_target)
        _print_dispatch_summary(summary, config.mode.name)
        # FR-005/T005: an all-zero summary is four different situations with four
        # different remedies. Reported from HERE, while `runtime` is still open, so
        # the diagnosis reads the exact journal the drain just selected from rather
        # than re-resolving a scope and possibly describing a different store.
        _report_empty_selection(summary, runtime.journal)
        return summary
    except Exception as exc:  # additive drain must never break the command
        _LOG.debug("event-sync dispatch skipped: %s", exc)
        console.print(f"[dim]Event sync unavailable: {str(exc)[:80]}[/dim]")
        return None
    finally:
        if runtime is not None:
            runtime.close()


def _render_event_sync_status(target_console: Console) -> None:
    """Surface the active mode + a compact event-sync summary in ``sync status``.

    Read-only and best-effort: a failure here must never break ``sync status``.
    """
    config = _load_event_sync_config()
    target_console.print("[bold]Event Sync[/bold]")
    target_console.print(f"  Mode                      {config.mode.name}")
    runtime: _EventSyncRuntime | None = None
    try:
        runtime = _open_event_sync_runtime_readonly()
        report = _event_sync_report({}, runtime)
    except Exception as exc:  # read-only summary; never fail status rendering
        _LOG.debug("event-sync status summary unavailable: %s", exc)
        return
    finally:
        if runtime is not None:
            runtime.close()
    journal_section = report["event_journal"]
    ledger_section = report["delivery_ledger"]
    failures_section = report["terminal_failures"]
    target_console.print(
        f"  Retained events           {journal_section['retained_event_count']}"
    )
    target_console.print(
        "  Delivered (cur/prev)      "
        f"{ledger_section['delivered_current_target']}/"
        f"{ledger_section['delivered_previous_target']}"
    )
    target_console.print(
        f"  Terminal failures         {failures_section['count']}"
    )
    if journal_section.get("gc_suggested"):
        target_console.print(
            "  [yellow]GC suggested[/yellow]: run `spec-kitty sync gc`"
        )


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


def _require_daemon_owner_coherence(command_name: str | None = None) -> None:
    """FR-007 precondition gate for sync mutating commands.

    Refuses to act when the foreground CLI's identity (package version,
    executable path, server URL, auth scope, queue DB path) does not match
    the registered daemon owner record on any D-3 field. The refusal
    message names the mismatched field(s) so the operator knows which fix
    is needed.

    WP03: thin wrapper over :func:`run_preflight`. ``require_auth`` is
    ``False`` because individual SaaS-producing call sites (``sync now``,
    ``setup-plan``) enforce auth-required explicitly; the generic gate
    only enforces the structural boundary (mismatches, orphans, legacy
    rows in scope).

    No-op when the boundary is coherent. Exits with code 2 otherwise.
    """
    from specify_cli.sync.preflight import run_preflight

    result = run_preflight(repo_root=Path.cwd(), require_auth=False)
    if result.ok:
        return
    label = f" `{command_name}`" if command_name else ""
    if label:
        console.print(f"[red]Refusing{label}.[/red]")
    result.render(console)
    raise typer.Exit(code=2)


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
_NO_RECORDED_NAME = "<no name recorded>"


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


def _per_project_store_issues(report: PerProjectStoreReport) -> list[str]:
    """The operator-actionable warnings a per-project breakdown implies.

    Kept separate from the rendering so ``doctor``'s "Issues found" list and
    ``status``'s warnings cannot say different things about the same report.
    """
    issues: list[str] = []
    # Reconciliation is the load-bearing check: a table that omits rows is the
    # incident's false-green with a nicer layout.
    if not report.reconciles:
        issues.append(
            f"Per-project totals ({report.counted_event_total}) do not reconcile "
            f"against the journal's retained count ({report.retained_event_count}). "
            "The report is incomplete — do not trust it."
        )
    if report.unresolved_identity_count:
        # Deliberately not "permanently undeliverable", and no longer pointing at
        # `purge` as the only remedy. Since #3030 H4 wired the identity backfill
        # into `sync migrate`, rows whose stored envelope carries a resolvable uuid
        # ARE recoverable, and for the operator's own consenting project that is the
        # difference between their history shipping and being stranded forever.
        # Sending them to `purge` would destroy recoverable data. What is permanent
        # is only that a NULL row cannot be SELECTED (FR-011, fail-closed).
        issues.append(
            f"{report.unresolved_identity_count} journal event(s) have no stored "
            "project identity, so they cannot be selected for delivery. Run "
            "`spec-kitty sync migrate` to recover the identity of any whose stored "
            "payload still carries it; whatever remains is retained locally and "
            "removable only with `spec-kitty sync purge`."
            + _unresolved_origin_clause(report)
        )
    # NAMED refusals only. The unresolved-identity bucket is also
    # `consent_granted=False`, but its consent could not be resolved at all — see
    # `named_non_consenting_rows`. Naming one of its member repos here told the
    # operator that repo had refused and should be purged; purging it leaves the
    # bucket's other repos on disk while the report reads clean.
    non_consenting = report.named_non_consenting_rows
    if non_consenting:
        named = ", ".join(
            (r.repo_slug or r.project_slug or r.project_uuid or "<unnamed>")
            for r in non_consenting
        )
        issues.append(
            f"{len(non_consenting)} project(s) in the journal have not consented to "
            f"hosted sync: {named}. Their events are retained locally and never "
            "delivered; `spec-kitty sync purge --project <slug>` removes them."
        )
    return issues


def _unresolved_origin_clause(report: PerProjectStoreReport) -> str:
    """Name the repos the unresolved rows appear to come from, with counts (SC-004).

    Without this an operator is told a number and nothing else, and has to open
    SQLite to learn which repos are involved — even though the slugs are already on
    the rows and in the identity projection. Worded as *appear to come from*: with
    no uuid these rows' consent cannot be resolved, so this is provenance, never a
    statement about what any of those projects decided.
    """
    candidates: tuple[UnresolvedIdentityCandidate, ...] = tuple(
        candidate
        for row in report.rows
        if row.is_unresolved_identity
        for candidate in row.unresolved_candidates
    )
    if not candidates:
        return ""
    from specify_cli.delivery.status_report import unresolved_candidate_name

    named = ", ".join(
        f"{unresolved_candidate_name(candidate) or _NO_RECORDED_NAME} "
        f"({candidate.event_count})"
        for candidate in candidates
    )
    return (
        f" They appear to come from: {named}. Consent for these rows cannot be "
        "resolved without a project identity, so this is where they were captured, "
        "not what those projects decided."
    )


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
        state = (
            "[green]consented[/green]"
            if row.consent_granted
            else f"[red]denied[/red] [dim]({row.consent_level})[/dim]"
        )
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


def _open_journal_readonly() -> EventJournal:
    """Open ONLY the journal for the current producer scope, read-only (#3030 T021).

    Deliberately not ``_open_event_sync_runtime_readonly``, which also resolves the
    delivery target and opens the ledger and target registry. A "whose data is in
    here?" read needs none of those, and sharing that opener meant any
    target-resolution failure was reported as "the event journal could not be
    read" — the wrong diagnosis, naming the wrong store, in the one section whose
    job is to be trustworthy about which store it read.

    Raises ``FileNotFoundError`` when this scope has no journal file yet, which the
    caller renders as the benign absence it is.
    """
    from specify_cli.event_journal.journal import EventJournal, resolve_journal_path

    scope = _current_event_sync_scope()
    path = resolve_journal_path(user_id=scope.user_id, team_slug=scope.team_slug)
    if not path.exists():
        raise FileNotFoundError(f"event-sync journal DB absent: {path}")
    return EventJournal(path)


def _render_per_project_store(console_out: Any, issues: list[str]) -> None:
    """Render the journal's per-project composition with consent state (#3030 T021).

    Sits beside doctor's queue-health block deliberately rather than replacing it.
    That block reads ``OfflineQueue().get_queue_stats()``, which is EMPTY after
    ``sync migrate`` — the source of the incident's false-green, where the operator
    saw "Queue size 0" while 9,133 events sat in the journal. This section answers
    "whose data is actually in here?" from the journal itself, so the two cannot
    disagree silently.

    **Every exit path from this function is observable.** The first cut returned
    silently on an unopenable runtime, on a failed grouping, and on an empty
    report, which made three very different states — "nothing is in the journal",
    "I could not read the journal", and "I never looked" — render identically:
    doctor's usual healthy table with no journal section and exit 0. That is the
    incident's false-green rebuilt inside the fix for it. A failure now names what
    could not be read, and the empty case says so out loud.
    """
    from specify_cli.delivery.status_report import build_per_project_store_report

    try:
        journal = _open_journal_readonly()
    except FileNotFoundError as exc:
        # The one benign absence: no journal file has ever been created for this
        # producer scope, so there is genuinely nothing to group. Still printed,
        # because "no journal yet" and "I could not look" must not read alike.
        console_out.print(f"\n[bold]{_PER_PROJECT_SECTION_TITLE}[/bold]")
        console_out.print(f"  [dim]no journal for this scope yet ({exc})[/dim]")
        return
    except Exception as exc:
        issues.append(
            f"The event journal could not be opened, so this run cannot say which "
            f"projects have data in it: {exc}. Until this is resolved, treat a "
            "clean queue-health block as unproven — it reads a different store."
        )
        return
    try:
        report = build_per_project_store_report(journal)
    except Exception as exc:
        issues.append(
            f"The event journal opened but its rows could not be grouped by "
            f"project: {exc}. Whose data is in the journal is currently UNKNOWN; "
            "the queue-health block above does not answer it."
        )
        return

    console_out.print(f"\n[bold]{_PER_PROJECT_SECTION_TITLE}[/bold]")
    if report.rows:
        console_out.print(_per_project_store_table(report))
    else:
        # Asserted-empty, not silently-empty: this line is the difference between
        # a journal that holds nothing and a report that never ran.
        console_out.print(
            f"  [green]no events retained[/green] "
            f"[dim](journal count {report.retained_event_count})[/dim]"
        )
    # Unconditionally, including on the empty branch. A journal that cannot answer
    # count() reports -1, which does not reconcile against zero rows — so returning
    # early on `not report.rows` would have rendered an unreadable journal as "no
    # events retained". That is the same three-states-look-alike failure the
    # docstring above is about, one branch further in.
    issues.extend(_per_project_store_issues(report))


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
        console.print(
            "[dim]Nothing was changed and no records were lost. "
            "Run 'spec-kitty sync doctor' for the full consent-readability report.[/dim]"
        )
        raise typer.Exit(1) from exc


_CONSENT_HEALTH_SECTION_TITLE = "Consent record readability"

#: Every ``ConfigReadFault.kind`` mapped to **the operator action that resolves it**,
#: never to a restatement of the kind. That is the whole requirement: the defect
#: FR-020 exists to remove is an operator being told "no consent record for this
#: project" when the truth is "your index is unreadable", which sends them to record
#: consent they already recorded — and on the machine index that write *destroys the
#: other projects' records* (see :data:`_CONSENT_FAULT_NOT_ABSENCE`).
#:
#: Four kinds. FR-027 added ``unusable`` — a present-but-uninterpretable value —
#: alongside the file-level kinds, and it is the one most easily mistaken for absence
#: because the file looks perfectly fine.
#:
#: **The wording narrows because the vocabulary was unified.** Until 2026-07-30 the two
#: file-level tokens did not mean the same thing to both producers: ``sync/config.py``
#: called a TOML *syntax* error ``unparseable`` and an ``OSError`` ``unreadable``, while
#: ``sync/consent.py`` called an open-*or*-parse failure ``unreadable`` and a non-mapping
#: top level ``unparseable``. One kind-keyed string therefore had to span both readings
#: — "either its syntax does not parse, or its top level is not a mapping" — which meant
#: telling every reader one true thing and one false one. ``sync/consent.py`` now splits
#: cannot-open from cannot-parse and mints ``wrong_shape`` for a non-mapping top level
#: (see ``sync.config.CONFIG_FAULT_KINDS``), so each entry below names one state and one
#: remedy. Pinned by ``test_the_action_is_true_for_both_producers_of_the_same_kind``,
#: which now asserts the two producers agree rather than that the advice hedges.
#:
#: The first element of each triple is the status word printed beside the scope, so a
#: field-level fault is no longer announced as an unreadable file.
_CONSENT_FAULT_ACTIONS: dict[str, tuple[str, str, str]] = {
    "unreadable": (
        "UNREADABLE",
        "MAKE THE FILE READABLE",
        "It could not be opened at all — a permission or ownership problem. Fix the "
        "file's mode or its owner; the error in brackets says which applies.",
    ),
    "unparseable": (
        "UNPARSEABLE",
        "REPAIR THE FILE'S SYNTAX",
        "The file was opened and its syntax does not parse. Repair the error quoted in "
        "the detail — it names the line the parser stopped on.",
    ),
    "wrong_shape": (
        "WRONG SHAPE",
        "MAKE THE DOCUMENT A MAPPING",
        "The file parsed cleanly; its top level is simply not a set of keys. A list, a "
        "bare scalar or a leftover merge-conflict marker does this. Do not go looking "
        "for a syntax error — there is none.",
    ),
    "unusable": (
        "UNUSABLE VALUE",
        "CORRECT THE FIELD VALUE NAMED IN THE DETAIL",
        "The file parsed and its shape is fine, but a field holds a value that cannot "
        'be understood as that field. Only a real boolean records a consent decision, so '
        '`sync.enabled: "false"` is a quoted string that records nothing, and `enabled: no` '
        "is the string \"no\" (ruamel is YAML 1.2). A `project.uuid` that is not a uuid "
        "names no project.",
    ),
}

#: The fallback for a kind this build does not recognise. Not defensive padding: this
#: mission added a kind once already, and a kind-keyed table that renders nothing for
#: an unrecognised key would turn the next addition into an invisible fault — the
#: exact defect shape this section exists to close.
_CONSENT_FAULT_UNKNOWN_ACTION = (
    "UNREADABLE",
    "REPAIR THE FILE NAMED IN THE DETAIL",
    "This build has no specific advice for that fault kind; the detail below is the "
    "whole of what is known about it.",
)

#: Printed for every fault, on both surfaces. The second half is measured, not
#: reasoned — and it was **rewritten on 2026-07-30 because the hazard it described was
#: fixed**, which is the only honest reason to change operator advice. It used to read
#: "a write rewrites the file from an empty document when it cannot be read, discarding
#: every other project's record", and that was true: every `SyncConfig` setter was a
#: whole-file read-modify-write over `_load()`, which answers `{}` for an unreadable
#: file. Seven of the eight destroyed a bystander project's grant, and the same
#: destruction was reachable from a plain *read* via `consent._reconcile_index`.
#:
#: A write over an unreadable config is now refused
#: (`sync.config.ConfigNotReadableError`), so the records survive. Leaving the old
#: sentence standing would have been the same defect this section exists to remove, one
#: turn later: advice that was true when written and is false when read.
#: ``tests/cli/commands/test_sync_doctor_consent_health_3030.py`` pins both halves.
_CONSENT_FAULT_NOT_ABSENCE = (
    "This is NOT a missing consent record. Recording consent again will not clear it: "
    "a write over a config that cannot be read is refused, so your other projects' "
    "records are safe, but nothing is delivered until the file itself is repaired."
)

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
    kind = str(getattr(fault, "kind", "") or "unknown")
    status, action, remedy = _CONSENT_FAULT_ACTIONS.get(kind, _CONSENT_FAULT_UNKNOWN_ACTION)
    detail = str(getattr(fault, "detail", "") or "no detail recorded")

    console_out.print(f"  {scope}  [red]{status}[/red] ({kind})")
    console_out.print(f"    [bold red]{action}[/bold red] — {remedy}")
    console_out.print(f"    [dim]{detail}[/dim]")
    console_out.print(f"    {consequence}")
    console_out.print(f"    [yellow]{_CONSENT_FAULT_NOT_ABSENCE}[/yellow]")
    issues.append(f"{scope} ({kind}): {action}. {detail} {consequence} {_CONSENT_FAULT_NOT_ABSENCE}")


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
        console_out.print(
            f"  [yellow]![/yellow] the machine-global consent index could not be "
            f"inspected: {exc}"
        )
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
                consequence=(
                    "Every project on this machine resolves as UNDETERMINED while this "
                    "stands, so nothing is delivered."
                ),
            )

    try:
        from specify_cli.sync.consent import project_local_consent_fault

        repo_root = locate_project_root(Path.cwd())
        local_fault = None if repo_root is None else project_local_consent_fault(repo_root)
    except Exception as exc:  # noqa: BLE001 — reported, never silently skipped
        console_out.print(
            f"  [yellow]![/yellow] this checkout's project config could not be "
            f"inspected: {exc}"
        )
        issues.append(
            f"Whether this checkout's own consent record is readable could not be "
            f"determined: {exc}."
        )
    else:
        if repo_root is None:
            console_out.print(
                "  this checkout  [dim]not inspected — no Spec Kitty checkout resolved "
                "from the current directory[/dim]"
            )
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

    console_out.print(
        "  [dim]A missing record is not a fault: it means no consent was recorded, "
        "which denies.[/dim]"
    )


_TRACKER_EGRESS_SECTION_TITLE = "Tracker egress"

#: Wording for every reachable :attr:`TrackerEgressVerdict.channel1_state` value
#: (#3108 FR-014). Rendered from the *field*, never parsed out of ``message`` --
#: at ``HOSTED_SERVICE`` all three refusal states share one message (FR-016's
#: byte-identity carve-out, ``decisions/DM-FR016-hosted-byte-identity.md``), and
#: this dict is the only place that distinction still reaches an operator.
#: Deliberately exhaustive over the closed six-member state set so a state this
#: build fails to recognise renders its own name rather than nothing (the
#: ``.get(..., state)`` fallback in :func:`_render_tracker_egress_row`).
_CHANNEL1_STATE_WORDING: Final[dict[str, str]] = {
    CHANNEL1_GRANTED: "hosted-sync consent is granted for this project",
    CHANNEL1_NO_RECORD: "no record of hosted-sync consent exists for this project",
    CHANNEL1_RECORDED_REFUSAL: "a refusal is recorded for this project",
    CHANNEL1_NOT_CONSENTABLE: "not consentable, no project identity resolved",
    CHANNEL1_UNCLASSIFIED: "refuses, but the specific reason could not be classified",
    CHANNEL1_UNDETERMINED: "undetermined -- this directory is not inside a checkout",
}


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
    state_wording = _CHANNEL1_STATE_WORDING.get(verdict.channel1_state, verdict.channel1_state)
    console_out.print(f"    Channel 1: {state_wording}")
    safe_message = _escape_markup(verdict.message)
    console_out.print(f"    {safe_message}")
    for remedy in verdict.remedies:
        console_out.print(f"    remedy: {remedy}")
    if verdict.refused and binding_present:
        issues.append(
            f"tracker egress to {verdict.destination.value} is refused "
            f"(Channel 1: {state_wording}): {safe_message}"
        )


def _render_tracker_egress(console_out: Any, issues: list[str]) -> None:
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

    Never consults the on-disk tracker provider to decide what to show: ``--provider``
    overrides it in memory only (``TrackerService._resolve_saas_backend_for_provider``),
    so a provider-conditional block would misreport one destination while saying
    nothing about the other. Two written-out calls below, each with a literal
    :class:`EgressDestination` member -- never a loop over the enum, which would
    turn the ``destination`` argument into an ``ast.Name`` and red WP07's guard G5.

    Resolves its own root with ``locate_project_root(Path.cwd())``, exactly as the
    sibling readability block does, so both sections in one ``doctor`` run describe
    the same checkout -- the signature deliberately takes no ``root`` parameter so
    ``doctor()`` keeps calling both renderers identically. ``root=None`` is a
    specified case, not an error path (the verdict function never raises): passed
    straight through to both calls rather than guarded behind
    ``if repo_root is not None:``, so a directory that resolves no checkout is never
    rendered as if its tracker egress were fine.
    """
    from specify_cli.core.paths import locate_project_root
    from specify_cli.tracker.config import load_tracker_config

    # Each row passes the fragment its **owning transport** passes at that destination --
    # ``local_service.py`` for ``LOCAL_SUBPROCESS`` and ``tracker/saas_client.py`` for
    # ``HOSTED_SERVICE`` -- rather than a fragment of ``doctor``'s own. ``doctor`` reports;
    # it does not transmit, so it has no identifier set to declare. Its contract is that
    # "the enforced answer and the reported answer cannot disagree" (``egress_verdict.py``
    # module docstring, the stated reason that module exists), and the refusal text an
    # operator reads here is rendered from ``identifiers``. Passing anything else -- a
    # doctor-local fragment, or one transport's fragment for both rows -- would print a
    # refusal that differs from the one the gate actually raises, which is the exact
    # divergence the single-function design was built to prevent. Imported locally, as the
    # two imports above are, so the hosted client and its HTTP stack load only when
    # ``doctor`` runs.
    from specify_cli.tracker.local_service import LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS
    from specify_cli.tracker.saas_client import TRACKER_EGRESS_IDENTIFIER_KINDS

    console_out.print(f"\n[bold]{_TRACKER_EGRESS_SECTION_TITLE}[/bold]")
    root = locate_project_root(Path.cwd())  # may be None; that is a rendered case
    local = tracker_egress_verdict(
        root,
        destination=EgressDestination.LOCAL_SUBPROCESS,
        identifiers=LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS,
    )
    hosted = tracker_egress_verdict(
        root,
        destination=EgressDestination.HOSTED_SERVICE,
        identifiers=TRACKER_EGRESS_IDENTIFIER_KINDS,
    )
    # Whether *any* provider is bound -- never which one. Gates the `issues` append
    # only; both rows render regardless. See `_render_tracker_egress_row`.
    #
    # Guarded, and the guard is load-bearing: `load_tracker_config` RAISES on an
    # unparseable `.kittify/config.yaml`, and `doctor`'s whole job is to be useful on
    # exactly that checkout. Unguarded, this read aborted the command mid-render --
    # measured as the `REPAIR THE FILE'S SYNTAX` count dropping 4 -> 2, because every
    # line after this block stopped printing. `tracker_egress_verdict` is defended
    # against this internally (NFR-003, "never raises"); a second, direct config read
    # is not, and reintroduced the same defect one level up. An unreadable config means
    # no binding is *knowable*, so no issue is claimed -- the sibling readability
    # renderer already reports the unparseable file as its own issue, and the two rows
    # below still print their refusal either way.
    binding_present = False
    if root is not None:
        try:
            binding_present = bool(load_tracker_config(root).provider)
        except Exception:  # noqa: BLE001 - doctor must render on a broken config, not abort
            binding_present = False
    _render_tracker_egress_row(console_out, issues, local, binding_present=binding_present)
    _render_tracker_egress_row(console_out, issues, hosted, binding_present=binding_present)


def _print_identity_backfill_result(result: IdentityBackfillResult | None) -> None:
    """Report what convergence recovered into the identity columns (#3030 H4).

    Printed unconditionally, including the zero case, because "nothing needed
    recovering" and "the backfill did not run" must not look alike — that
    equivalence is what let the backfill sit unwired with every test green.
    """
    if result is None:
        console.print(
            "[yellow]![/yellow] The journal identity backfill could not run, so "
            "rows with no stored identity remain unselectable. Re-run "
            "`spec-kitty sync migrate`; if it persists, `spec-kitty sync doctor` "
            "reports how many rows are affected."
        )
        return
    console.print(
        f"Journal identity: recovered {result.updated}  "
        f"[dim]unresolvable {result.unresolved}[/dim]"
    )
    if result.unresolved:
        # Not an error, and deliberately not phrased as one: these rows are
        # fail-closed by design (FR-011). What matters is that they are visible.
        console.print(
            f"  [dim]{result.unresolved} row(s) carry no resolvable project "
            "identity in their stored payload; they stay unselectable rather than "
            "being assigned one.[/dim]"
        )


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
    except Exception as exc:  # noqa: BLE001 - reported, never fatal to the migration
        console.print(
            f"  [yellow]![/yellow] could not be completed: {exc}. Path-keyed "
            "records remain in place and the drain still cannot see them."
        )
        return

    console.print(f"  mapped {result.mapped}  unresolved {result.unresolved}")
    if result.mapped:
        console.print(
            "  [dim]Consent for these projects is now visible to the drain's "
            "uuid-keyed lookup:[/dim]"
        )
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


def _render_migrated_composition(
    journal: EventJournal, imported_event_ids: list[str]
) -> None:
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
        console.print(
            f"  [yellow]![/yellow] imported {len(imported_event_ids)} event(s) but "
            f"their per-project composition could not be read: {exc}"
        )
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
    table.add_row("Repository", routing.repo_slug or "[dim]Unavailable[/dim]")
    table.add_row("Project UUID", routing.project_uuid or "[dim]Unavailable[/dim]")
    table.add_row("Project Slug", routing.project_slug or "[dim]Unavailable[/dim]")
    table.add_row("Build ID", routing.build_id or "[dim]Unavailable[/dim]")
    table.add_row(
        "Checkout Sync",
        "[green]Enabled[/green]" if routing.effective_sync_enabled else "[yellow]Disabled[/yellow]",
    )

    local_value = (
        "[dim]Not set[/dim]"
        if routing.local_sync_enabled is None
        else ("enabled" if routing.local_sync_enabled else "disabled")
    )
    table.add_row("Local Override", local_value)

    repo_default = (
        "[dim]Not set[/dim]"
        if routing.repo_default_sync_enabled is None
        else ("enabled" if routing.repo_default_sync_enabled else "disabled")
    )
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


@app.command()
def share(
    team_slug: str = typer.Argument(..., help="Team slug to share this repository into."),
) -> None:
    """Share the current repository from Private Teamspace into a team."""
    from specify_cli.sync.sharing_client import (
        RepositorySharingClientError,
        request_repository_share_sync,
    )

    _require_daemon_owner_coherence("spec-kitty sync share")

    if not is_saas_sync_enabled():
        console.print(f"[red]{saas_sync_disabled_message()}[/red]")
        raise typer.Exit(1)

    enforce_teamspace_mission_state_ready(
        console=console,
        command_name="spec-kitty sync share",
    )

    routing = _require_active_checkout()
    _require_authenticated_session(command_name="sync share")

    if routing.project_uuid is None:
        console.print(
            "[red]Error:[/red] Current checkout has no project UUID. "
            "Run `spec-kitty init` first."
        )
        raise typer.Exit(1)

    try:
        response = request_repository_share_sync(
            source_project_uuid=routing.project_uuid,
            destination_team_slug=team_slug,
        )
    except RepositorySharingClientError as exc:
        if exc.status_code == 404:
            if not routing.effective_sync_enabled:
                console.print(
                    "[red]Error:[/red] This checkout is opted out of SaaS sync. "
                    "Run `spec-kitty sync opt-in` first."
                )
                raise typer.Exit(1) from None
            try:
                _materialize_private_source_project()
            except Exception as materialize_error:
                console.print(
                    "[red]Error:[/red] Could not materialize this checkout in Private Teamspace: "
                    f"{materialize_error}"
                )
                raise typer.Exit(1) from materialize_error
            response = request_repository_share_sync(
                source_project_uuid=routing.project_uuid,
                destination_team_slug=team_slug,
            )
        else:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    share_data = response.get("share") or {}
    share_state = share_data.get("state", "unknown")
    if share_state == "shared":
        console.print(
            f"[green]✓[/green] Shared [cyan]{routing.repo_slug or routing.project_slug or routing.project_uuid}[/cyan] "
            f"to [cyan]{team_slug}[/cyan]."
        )
    else:
        console.print(
            f"[yellow]✓[/yellow] Share request recorded for [cyan]{team_slug}[/cyan]."
        )

    if response.get("auto_approved"):
        console.print("[dim]Team policy auto-approved the repository share.[/dim]")
    elif share_state == "pending_approval":
        console.print("[dim]Waiting for a team admin to approve the repository.[/dim]")


@app.command()
def unshare(
    team_slug: str = typer.Argument(..., help="Team slug to stop sharing this repository into."),
) -> None:
    """Stop sharing the current repository from this developer to one team."""
    from specify_cli.sync.sharing_client import (
        RepositorySharingClientError,
        leave_repository_share_sync,
    )

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
        leave_repository_share_sync(
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

    console.print(
        f"[green]✓[/green] Disabled SaaS sync for this checkout "
        f"([cyan]{routing.repo_slug or routing.project_slug or routing.project_uuid}[/cyan])."
    )
    console.print(
        f"[dim]Removed {result.removed_events} queued event(s) and "
        f"{result.removed_body_uploads} queued body upload(s) for this checkout.[/dim]"
    )
    if result.remembered_for_repo:
        console.print("[dim]Future checkouts of this repository will also default to sync disabled.[/dim]")

    if not delete_private_data or not routing.project_uuid:
        return

    if not is_saas_sync_enabled():
        console.print(
            "[yellow]Skipping private-data deletion because SaaS sync is disabled in this shell.[/yellow]"
        )
        return

    try:
        _require_authenticated_session(command_name="sync opt-out")
        shares = list_repository_shares_sync(source_project_uuid=routing.project_uuid)
    except (RepositorySharingClientError, typer.Exit) as exc:
        console.print(f"[yellow]Could not inspect remote share state:[/yellow] {exc}")
        return

    if shares:
        console.print(
            "[yellow]Private data was not deleted because this repository has team share history.[/yellow]"
        )
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
    """Converge any legacy queue residue into the journal when enabling sync (#2665).

    Turning sync on for a checkout should make it coherent, not refuse. Runs the
    clean-path convergence (import + cleanup) so the legacy-row boundary clears.
    Divergent-duplicate conflicts are deliberately NOT auto-resolved here (that
    would discard superseded source data, even if quarantined) — they are
    surfaced with the explicit ``sync migrate --resolve-conflicts keep-journal``
    recovery, and the coherence gate that follows still refuses until they are
    resolved. Idempotent and lossless: a no-op on an already-converged runtime.
    Any failure opening the runtime OR converging is swallowed so the coherence
    gate that follows handles it, rather than aborting opt-in with a traceback.
    """
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.migrate_journal import (
        AUDIT_DB_NAME,
        MigrationAudit,
        converge_legacy_runtime,
    )

    spec_kitty_dir = get_runtime_root().base
    try:
        runtime = _open_event_sync_runtime()
    except Exception:  # runtime unavailable — let the coherence gate report it
        return
    audit = MigrationAudit(spec_kitty_dir / AUDIT_DB_NAME)
    try:
        converge = converge_legacy_runtime(
            spec_kitty_dir,
            journal=runtime.journal,
            audit=audit,
            resolved_target=runtime.target,
            resolve_conflicts=False,
            cleanup=True,
        )
    except Exception:  # converge failed — let the coherence gate report it
        return
    finally:
        with contextlib.suppress(Exception):
            audit.close()
        with contextlib.suppress(Exception):
            runtime.close()

    deleted = converge.cleanup.total_deleted if converge.cleanup is not None else 0
    if deleted:
        console.print(
            f"[green]✓[/green] Converged {deleted} legacy queue row(s) into the event journal."
        )
    if converge.blocked_conflicts:
        console.print(
            f"[yellow]{converge.blocked_conflicts} divergent-duplicate conflict(s) remain. "
            "Run `spec-kitty sync migrate --resolve-conflicts keep-journal` to resolve them, "
            "then re-run opt-in.[/yellow]"
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

    # Turning sync on converges any legacy queue residue into the journal so the
    # boundary is coherent instead of refusing (#2665). Conservative: clean-path
    # only; divergent-duplicate conflicts are surfaced for an explicit
    # `sync migrate --resolve-conflicts keep-journal` before opt-in can proceed.
    _auto_converge_legacy_on_enable()

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
        console.print(
            "[dim]Future checkouts of this repository will also default to this local preference.[/dim]"
        )


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
        lines = (
            ", ".join(f"{start}-{end}" for start, end in conflict.line_ranges)
            if conflict.line_ranges
            else "entire file"
        )

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
        help="Materialize the selected missions into the SaaS projection (default is a dry-run plan).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what would be imported without emitting anything (this is the default).",
    ),
    mission: str | None = typer.Option(
        None,
        "--mission",
        help="Import only this mission (slug / mid8 / ULID); default imports all eligible missions.",
    ),
) -> None:
    """Materialize existing local mission/WP history into the SaaS projection (#2262).

    A first sync registers a remote project/build but leaves it with zero
    materialized missions — the SaaS materializer deliberately refuses to
    fabricate a WorkPackage from a status event with no prior create. This
    command emits the missing ``MissionCreated → WPCreated[] → WPStatusChanged[]``
    stream (INV-3) so historical work populates the projection.

    Dry-run (default) runs the full read-only pipeline — SELECT → AUDIT
    (fail-closed) → SCAN → IDENTITY → SYNTHESIZE — and previews the envelope
    stream that would be materialized. ``--apply`` additionally attaches
    provenance, server-preflights the whole stream (fail-closed), and uploads it
    in chunks to the SaaS projection under the real persisted project UUID.

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

    if apply and dry_run:
        console.print("[red]Error:[/red] --apply and --dry-run are mutually exclusive.")
        raise typer.Exit(2)

    if apply:
        _run_import_apply(mission)
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
    console.print("\n[dim]Dry-run: nothing uploaded. Re-run with --apply to materialize.[/dim]")


def _resolve_history_import_receiver(
    runtime: _EventSyncRuntime, *, token: str
) -> tuple[DeliveryReceiver, str]:
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


def _run_import_apply(mission: str | None) -> None:
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

    token = _event_sync_access_token()
    if not token:
        console.print(
            "[red]Not authenticated.[/red] Run `spec-kitty auth login` before importing with --apply."
        )
        raise typer.Exit(1)

    runtime = _open_event_sync_runtime()
    try:
        receiver, server_url = _resolve_history_import_receiver(runtime, token=token)
        repo_root = _require_active_checkout().repo_root

        try:
            result = apply_import(
                repo_root,
                mission=mission,
                receiver=receiver,
                server_url=server_url,
                auth_token=token,
            )
        except (MissionStateRepairError, MissionScanError) as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        except ImportIdentityError as exc:
            console.print(f"[red]Identity error:[/red] {exc}")
            raise typer.Exit(1) from exc
        except ImportAuditBlocked as exc:
            console.print(
                f"[red]Import blocked:[/red] {len(exc.blockers)} audit finding(s) must be resolved first:"
            )
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
        console.print(
            f"[dim]Provenance: {len(result.manifest)} envelope(s) hashed into the sha256 import "
            "audit manifest.[/dim]"
        )
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
def sync_workspace(  # noqa: C901
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
        console.print("[yellow]⚠ Not in a recognized workspace[/yellow]")
        console.print("Run this command from a worktree directory:")
        console.print("  cd .worktrees/<feature>-lane-a/")
        raise typer.Exit(1)

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

    # Display result based on status
    if result.status == SyncStatus.UP_TO_DATE:
        console.print("\n[green]✓ Already up to date[/green]")
        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

    elif result.status == SyncStatus.SYNCED:
        stats_parts = []
        if result.files_updated > 0:
            stats_parts.append(f"{result.files_updated} updated")
        if result.files_added > 0:
            stats_parts.append(f"{result.files_added} added")
        if result.files_deleted > 0:
            stats_parts.append(f"{result.files_deleted} deleted")

        stats = ", ".join(stats_parts) if stats_parts else "no file changes"
        console.print(f"\n[green]✓ Synced[/green] - {stats}")

        if verbose:
            _display_changes_integrated(result.changes_integrated)

        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

    elif result.status == SyncStatus.CONFLICTS:
        console.print("\n[yellow]⚠ Synced with conflicts[/yellow]")
        console.print("[dim]You must resolve conflicts before continuing.[/dim]")

        _display_conflicts(result.conflicts)

        if verbose:
            _display_changes_integrated(result.changes_integrated)

    elif result.status == SyncStatus.FAILED:
        console.print("\n[red]✗ Sync failed[/red]")
        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

        # Show conflicts if any
        if result.conflicts:
            _display_conflicts(result.conflicts)

        console.print()
        console.print("[dim]Try:[/dim]")
        console.print("  spec-kitty sync workspace --repair")
        raise typer.Exit(1)

    console.print()


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
    console.print(
        "[dim]If you switched environments, run "
        "'spec-kitty auth login --force' to refresh credentials.[/dim]"
    )


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
    queue_size = service.queue.size()
    retained_work_present = _event_sync_retained_work_present()

    # Single, non-destructive event-delivery path. The journal-based dispatcher
    # is now the SOLE event drain (FR-001): the retired legacy
    # ``service.sync_now()`` offline-queue drain deleted journal-owned events AND
    # double-POSTed every event the dispatcher also delivers (the dual-drain
    # defect). Body uploads still flush via the body-ONLY entry point so
    # attachments keep working without ever touching the durable event journal
    # (C-006).
    summary = _run_event_sync_dispatch()
    service.drain_body_uploads_only()

    # Persist the per-outcome report (if requested) and map the dispatch outcome
    # onto the strict exit contract — preserving the unauthenticated/blocked UX.
    _maybe_write_dispatch_report(report, summary)
    _enforce_sync_now_exit_from_dispatch(
        strict,
        queue_size,
        summary,
        retained_work_present=retained_work_present,
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

    runtime = _open_event_sync_runtime()
    try:
        known_target_ids = [target.target_id for target in runtime.registry.list_targets()]
        result = gc_payloads(
            runtime.journal, runtime.ledger, known_target_ids=known_target_ids
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

    runtime = _open_event_sync_runtime()
    try:
        result = archive_payloads(runtime.journal)
    finally:
        runtime.close()
    _print_retention_result(result)


# --------------------------------------------------------------------------- #
# `sync purge` — the operator's remediation path (#3030 WP08 / T022)            #
#                                                                              #
# FR-016 / FR-017 / NFR-006 / C-002. `sync gc` only reclaims payloads already   #
# delivered to every known target, so it cannot clear the retained rows the     #
# 2026-07-27 incident left on disk. This command is the only path that can, and #
# it composes the four stores' purge primitives rather than re-deriving any of   #
# them: `delivery/retention.py` owns the journal, the delivery ledger and the   #
# body-upload queue; `sync/local_commit.py` owns the per-checkout               #
# `pending_local_commits` queue. Selection and deletion stay there (C-003);     #
# what lives here is the operator surface, the differential, and the honesty    #
# about scope.                                                                  #
# --------------------------------------------------------------------------- #

#: Census key for a ``NULL`` project identity. Deliberately distinct from ``""``:
#: a NULL row and a non-NULL blank row are different populations reachable by
#: different selectors, and a census that folded them together is exactly what
#: made an NFR-006 differential vacuous earlier in this mission (a population
#: counted in no bucket has a differential of zero by construction).
_PURGE_NULL_KEY = "<null>"

_PURGE_JOURNAL = "event_journal"
_PURGE_LEDGER = "delivery_ledger"
_PURGE_BODY = "body_upload_queue"
_PURGE_FRAMES = "local_commit_frames"

_PURGE_STORE_LABELS = {
    _PURGE_JOURNAL: "event journal",
    _PURGE_LEDGER: "delivery ledger",
    _PURGE_BODY: "body-upload queue",
    # The scope is part of the name because it is not the same as the other three.
    _PURGE_FRAMES: "local-commit frames (this checkout only)",
}

#: Where a checkout keeps its queued ``LocalCommit`` frames. Duplicated from
#: ``sync/local_commit.py``'s private ``_sync_state_path`` on the same reasoning
#: ``delivery/retention.py`` records for ``_DELIVERY_SUBDIR``: this module needs the
#: path to *report* it and to read it independently, and reaching into another
#: module's private helper is the worse coupling. ``tests/cli/commands/
#: test_sync_purge_3030.py`` asserts the two agree, so a relocation is a red rather
#: than a purge report pointed at a file nobody writes.
_PURGE_SYNC_STATE_RELPATH = Path(".kittify") / "sync-state.json"

#: How `--all` is described, in one place, because the wording is a decision and
#: not a flourish (operator decision, 2026-07-30). The journal, the ledger and the
#: body queue are machine-global; ``pending_local_commits`` is per-checkout
#: ``LOCAL_RUNTIME`` state and there is no registry that could enumerate the other
#: checkouts' files. A registry was rejected as new state to keep correct, and a
#: filesystem scan because it can never prove completeness — which would leave the
#: erasure claim unprovable while sounding total. So the command must not present
#: `--all` as machine-wide erasure: "erased" that silently means "erased here" is
#: the same class of defect as a gate reporting success for having done nothing.
_PURGE_ALL_SCOPE_NOTE = (
    "Scope of --all: this machine's event journal, delivery ledger and body-upload "
    "queue, plus the queued local-commit frames of THIS CHECKOUT ONLY ({frames_path}). "
    "Other checkouts on this machine keep their own queued frames in their own "
    "sync-state.json; there is no registry of checkouts, so they cannot be listed and "
    "this run has not touched them. Re-run this command from each checkout you need "
    "cleared."
)

#: Printed on every destructive run. The ledger delete commits before the journal
#: delete and they are not one transaction, so an interruption leaves the ledger
#: purged with the journal intact — the recoverable direction, from which a re-run
#: converges. A report that implied atomicity would leave the operator with no
#: reason to re-run.
_PURGE_NON_ATOMIC_NOTE = (
    "The delivery ledger is deleted before the journal and the two are not one "
    "transaction. If a run is interrupted the ledger delete may have committed with "
    "the journal untouched; re-run the same command — it converges."
)


@dataclass(frozen=True)
class _RawCensus:
    """One store's row counts, grouped by the raw identity value it stores.

    Taken by the CLI itself and **not** through the domain censuses the purge
    primitives report from (NFR-006). Two properties matter:

    * **Total-preserving by construction.** Every row lands in exactly one bucket
      and ``NULL`` / ``""`` / ``"   "`` are three distinct buckets, so no population
      can be missing from both the before and after picture — the shape that let a
      purge move rows and still report "0% of any other project's" truthfully by its
      own arithmetic.
    * **Independent of the purge's own reads.** The differential below is measured
      from two of these snapshots, so it can disagree with what the primitive claims
      to have deleted. A check whose operands both come from the thing under test
      was already rejected on this mission, having produced zero failures over 200
      randomized cases.
    """

    total: int = 0
    by_key: dict[str, int] = field(default_factory=dict)
    unreadable: bool = False

    def count(self, keys: frozenset[str]) -> int:
        return sum(self.by_key.get(key, 0) for key in keys)

    @property
    def unbucketed(self) -> int:
        """Rows the grouping could not account for. Must be ``0``; reported if not."""
        return self.total - sum(self.by_key.values())


@dataclass
class _PurgeStoreOutcome:
    """What one store contributed to the purge, as measured rather than as claimed."""

    store: str
    location: str
    in_scope: int = 0
    removed_observed: int = 0
    removed_reported: int | None = None
    others_delta_observed: int = 0
    total_after: int = 0
    left_behind: dict[str, int] = field(default_factory=dict)
    states: dict[str, int] = field(default_factory=dict)
    never_attempted: int = 0
    unreadable: bool = False
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "location": self.location,
            "in_scope": self.in_scope,
            "removed_observed": self.removed_observed,
            "removed_reported": self.removed_reported,
            "others_delta_observed": self.others_delta_observed,
            "total_after": self.total_after,
            "left_behind": dict(self.left_behind),
            "unreadable": self.unreadable,
        }
        if self.store == _PURGE_LEDGER:
            data["states"] = dict(self.states)
            data["never_attempted"] = self.never_attempted
        if self.note:
            data["note"] = self.note
        return data


def _purge_usage_error(message: str) -> None:
    """Refuse before opening any store. Exit 2: nothing was read, nothing deleted."""
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(2)


def _purge_journal_census(journal_path: Path) -> _RawCensus:
    """Raw ``GROUP BY project_uuid`` over the journal — the CLI's own read.

    Not ``retention._journal_census``: that one composes ``distinct_project_uuids``
    with the identity projection, which *filters falsy uuids*, so a blank-uuid row
    reaches it only through a derived remainder. For a differential the CLI needs the
    stored values verbatim, blank and whitespace included, each as its own bucket.
    """
    import sqlite3

    from specify_cli.event_journal.models import COL_PROJECT_UUID, TABLE_NAME

    if not journal_path.exists():
        return _RawCensus()
    try:
        connection: Any = sqlite3.connect(str(journal_path))
    except sqlite3.Error:
        return _RawCensus(unreadable=True)
    try:
        # Static module-constant identifiers, no interpolated values.
        total_row = connection.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()  # noqa: S608  # nosec B608 — static module-constant identifiers
        by_key: dict[str, int] = {}
        for raw, count in connection.execute(
            f"SELECT {COL_PROJECT_UUID}, COUNT(*) FROM {TABLE_NAME} GROUP BY {COL_PROJECT_UUID}"  # noqa: S608  # nosec B608 — static module-constant identifiers
        ):
            by_key[_PURGE_NULL_KEY if raw is None else str(raw)] = int(count)
    except sqlite3.Error:
        return _RawCensus(unreadable=True)
    finally:
        connection.close()
    return _RawCensus(total=int(total_row[0]) if total_row else 0, by_key=by_key)


def _purge_journal_ids(journal_path: Path, *, project_uuid: str | None, every_row: bool) -> list[str]:
    """The journal ids the selector covers, resolved by the CLI's own raw read.

    ``project_uuid=None`` means ``IS NULL`` (FR-011's population). Used only to
    *measure* the ledger half — the deletion still selects through the primitives.
    """
    import sqlite3

    from specify_cli.event_journal.models import COL_EVENT_ID, COL_PROJECT_UUID, TABLE_NAME

    if not journal_path.exists():
        return []
    if every_row:
        sql = f"SELECT {COL_EVENT_ID} FROM {TABLE_NAME}"  # noqa: S608  # nosec B608 — static module-constant identifiers
        params: tuple[Any, ...] = ()
    elif project_uuid is None:
        sql = f"SELECT {COL_EVENT_ID} FROM {TABLE_NAME} WHERE {COL_PROJECT_UUID} IS NULL"  # noqa: S608  # nosec B608 — static module-constant identifiers
        params = ()
    else:
        sql = f"SELECT {COL_EVENT_ID} FROM {TABLE_NAME} WHERE {COL_PROJECT_UUID} = ?"  # noqa: S608  # nosec B608 — static module-constant identifiers
        params = (project_uuid,)
    try:
        connection: Any = sqlite3.connect(str(journal_path))
    except sqlite3.Error:
        return []
    try:
        return [str(row[0]) for row in connection.execute(sql, params)]
    except sqlite3.Error:
        return []
    finally:
        connection.close()


def _purge_ledger_census(ledger_path: Path, event_ids: list[str]) -> _RawCensus:
    """``(total rows, rows for the selected ids)`` — the ledger has no project column.

    Bucketed under one synthetic key because "another project's ledger rows" is not
    directly countable: the ledger is keyed ``(event_id, target_id)``. The change
    outside the selection is therefore derived as *total change minus selected
    change*, from the CLI's own counts.
    """
    import sqlite3

    from specify_cli.delivery.ledger import LEDGER_TABLE
    from specify_cli.event_journal.models import COL_EVENT_ID

    if not ledger_path.exists():
        return _RawCensus()
    try:
        connection: Any = sqlite3.connect(str(ledger_path))
    except sqlite3.Error:
        return _RawCensus(unreadable=True)
    try:
        total_row = connection.execute(f"SELECT COUNT(*) FROM {LEDGER_TABLE}").fetchone()  # noqa: S608  # nosec B608 — static module-constant identifiers
        selected = 0
        for event_id in event_ids:
            row = connection.execute(
                f"SELECT COUNT(*) FROM {LEDGER_TABLE} WHERE {COL_EVENT_ID} = ?",  # noqa: S608  # nosec B608 — static module-constant identifiers
                (event_id,),
            ).fetchone()
            selected += int(row[0]) if row else 0
    except sqlite3.Error:
        return _RawCensus(unreadable=True)
    finally:
        connection.close()
    total = int(total_row[0]) if total_row else 0
    return _RawCensus(total=total, by_key={_PURGE_LEDGER: selected})


def _purge_ledger_ghost_count(journal_path: Path, ledger_path: Path) -> int:
    """Ledger rows whose ``event_id`` has no journal row at all.

    Unreachable by any targeted selector, because every targeted selection collects
    its ids *from the journal*. Not a contrived state: ``sync gc`` deletes journal
    payload rows and preserves ledger history by design (FR-010), so every machine
    that has run it holds some. The two stores are separate SQLite files, so this is
    a set difference in Python rather than a join.
    """
    import sqlite3

    from specify_cli.delivery.ledger import LEDGER_TABLE
    from specify_cli.event_journal.models import COL_EVENT_ID

    if not ledger_path.exists():
        return 0
    journal_ids = set(_purge_journal_ids(journal_path, project_uuid=None, every_row=True))
    try:
        connection: Any = sqlite3.connect(str(ledger_path))
    except sqlite3.Error:
        return 0
    try:
        return sum(
            int(count)
            for event_id, count in connection.execute(
                f"SELECT {COL_EVENT_ID}, COUNT(*) FROM {LEDGER_TABLE} GROUP BY {COL_EVENT_ID}"  # noqa: S608  # nosec B608 — static module-constant identifiers
            )
            if str(event_id) not in journal_ids
        )
    except sqlite3.Error:
        return 0
    finally:
        connection.close()


def _purge_body_census(queue: Any | None) -> _RawCensus:
    """``count_by_project`` for the buckets, ``size`` for the total.

    Two different reads on purpose: the total cannot be affected by the attribution
    the buckets depend on, so a population the grouping fails to return shows up as
    ``unbucketed`` instead of vanishing from the differential.
    """
    if queue is None:
        return _RawCensus()
    try:
        by_key = {str(key): int(value) for key, value in queue.count_by_project().items()}
        total = int(queue.size())
    except Exception:  # noqa: BLE001 — an unreadable store is reported, never assumed empty
        return _RawCensus(unreadable=True)
    return _RawCensus(total=total, by_key=by_key)


def _purge_frames_census(repo_root: Path | None) -> _RawCensus:
    """Count queued frames by reading ``sync-state.json`` directly.

    Independent of ``census_pending_local_commits`` for a concrete reason, not a
    theoretical one: ``load_sync_state`` resets a malformed file to an empty state
    and never raises, so the primitive would report "0 frames" over a file still
    holding mission slugs — client engagement names. Read here, an unparseable file
    is a reported fault instead of a silent zero.
    """
    import json as _json

    if repo_root is None:
        return _RawCensus()
    path = repo_root / _PURGE_SYNC_STATE_RELPATH
    if not path.exists():
        return _RawCensus()
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
        frames = data["pending_local_commits"] if isinstance(data, dict) else None
        if not isinstance(frames, list):
            raise ValueError("pending_local_commits is not a list")
    except Exception as exc:  # noqa: BLE001 — the fault is the finding
        _LOG.debug("sync-state.json unreadable at %s: %s", path, exc)
        return _RawCensus(unreadable=True)
    by_key: dict[str, int] = {}
    for frame in frames:
        raw = frame.get("project_uuid") if isinstance(frame, dict) else None
        key = _PURGE_NULL_KEY if raw is None else str(raw)
        by_key[key] = by_key.get(key, 0) + 1
    return _RawCensus(total=len(frames), by_key=by_key)


def _purge_unattributable_keys(census: _RawCensus) -> frozenset[str]:
    """Census keys that name no project: ``NULL``, ``""``, and whitespace-only."""
    return frozenset(key for key in census.by_key if key == _PURGE_NULL_KEY or not key.strip())


def _purge_left_behind(census: _RawCensus) -> dict[str, int]:
    """The unattributable residue of one store, as two named counts."""
    null_rows = census.by_key.get(_PURGE_NULL_KEY, 0)
    blank_rows = sum(count for key, count in census.by_key.items() if key != _PURGE_NULL_KEY and not key.strip())
    residue: dict[str, int] = {}
    if null_rows:
        residue["identity_null"] = null_rows
    if blank_rows:
        residue["identity_blank"] = blank_rows
    return residue


def _purge_differential(before: _RawCensus, after: _RawCensus, scope: frozenset[str]) -> tuple[int, int]:
    """``(rows removed inside scope, absolute change outside it)``, both measured.

    Absolute and over the union of both censuses, so a key that *appeared* counts as
    a change too: a purge must neither remove nor create another project's rows, and
    a concurrent writer is exactly as much of a finding as an over-reaching selector.
    """
    removed = before.count(scope) - after.count(scope)
    keys = (set(before.by_key) | set(after.by_key)) - scope
    others = sum(abs(after.by_key.get(key, 0) - before.by_key.get(key, 0)) for key in keys)
    return removed, others


def _purge_ledger_differential(before: _RawCensus, after: _RawCensus) -> tuple[int, int]:
    """The ledger's ``(removed, changed outside the selection)``, derived not grouped.

    The ledger is keyed ``(event_id, target_id)`` and carries no project column, so
    "another project's ledger rows" cannot be grouped for. It *is* exactly derivable:
    total change minus the change the selection accounts for. Both operands come from
    the CLI's own two reads, so the answer can disagree with what the purge reported —
    which is the whole point of measuring it here (NFR-006).
    """
    removed = before.by_key.get(_PURGE_LEDGER, 0) - after.by_key.get(_PURGE_LEDGER, 0)
    return removed, abs((before.total - after.total) - removed)


def _purge_stored_spelling_conflicts(selector: str, censuses: list[_RawCensus]) -> list[str]:
    """Stored keys that mean the same project as *selector* but are spelled differently.

    A real cross-store hazard rather than pedantry: the journal matches a
    ``project_uuid`` by exact string equality, while the frame purge compares
    case-insensitively. So an upper-cased or dash-less selector would clear a
    checkout's frames while leaving every journal row in place, and report "0 journal
    rows in scope" — indistinguishable from a project that was already clean.
    """
    from uuid import UUID

    try:
        wanted: UUID | None = UUID(selector)
    except (ValueError, AttributeError, TypeError):
        wanted = None
    conflicts: set[str] = set()
    for census in censuses:
        for key in census.by_key:
            if key in (selector, _PURGE_NULL_KEY) or not key.strip():
                continue
            same = key.strip().casefold() == selector.strip().casefold()
            if not same and wanted is not None:
                try:
                    same = UUID(key.strip()) == wanted
                except (ValueError, AttributeError, TypeError):
                    same = False
            if same:
                conflicts.add(key)
    return sorted(conflicts)


def _purge_resolve_project(value: str, journal_path: Path, repo_root: Path | None) -> tuple[str, str | None]:
    """Resolve ``--project`` (a uuid *or* either recorded name) to ``(uuid, matched)``.

    A uuid is taken verbatim, including one no store holds: an operator must be able
    to purge a project whose rows survive only in the body queue. A name is resolved
    against the journal's own identity projection plus the invoking checkout's
    declared identity, and an unknown or ambiguous name is **refused** rather than
    run — "0 rows removed" is indistinguishable from "wrong selector", and this
    command's report is the only record left after a purge.

    **Both name columns are selectors, and that is the whole point (#3030 WP07).**
    This resolver used to key on ``project_slug`` alone while
    ``_project_store_label`` and ``_per_project_store_issues`` lead their label with
    ``repo_slug`` — so ``sync doctor`` printed

        ``2 project(s) ... have not consented ...: acme/app, beta/svc.``
        ``... `spec-kitty sync purge --project <slug>` removes them.``

    and the very next command refused the names it had just recommended:
    ``No project matches slug "acme/app"``. The operator running the incident's own
    remediation was handed a name the tool would not accept, which is exactly the
    hand-written-SQLite detour SC-004 exists to remove. Rather than stop printing the
    name an operator recognises, the resolver now accepts every name the report can
    print, so the whole label chain ``repo_slug -> project_slug -> project_uuid`` is
    copy-pasteable into the command the report recommends.

    Collisions are the cost, and they are already paid: two projects can share a repo
    slug, and a repo slug can even collide with another project's project slug. Both
    land in the same ``name -> {uuid}`` map, so both take the existing ambiguity
    refusal below — a purge must not span two projects, and refusing is the only safe
    answer to a selector that means two things.
    """
    from uuid import UUID

    raw = str(value or "").strip()
    if not raw:
        _purge_usage_error("--project needs a project uuid or name; a blank selector matches nothing.")
    try:
        UUID(raw)
    except (ValueError, AttributeError, TypeError):
        pass
    else:
        return raw, None

    candidates: dict[str, set[str]] = {}

    def _offer(name: str | None, uuid: str | None) -> None:
        """Record *name* as a selector for *uuid*, if both were recorded.

        The uuid guard is deliberately plain truthiness and NOT ``.strip()`` —
        matching what this function did before repo slugs were added. Whether a
        whitespace-only ``project_uuid`` is identity-less is a live question being
        settled in ``delivery/status_report.py``; tightening it here as a side
        effect of a naming change would decide it by accident, in the wrong module.
        The name guard does strip, because a whitespace-only name would otherwise
        key the map on ``""`` and answer for every unnamed row.
        """
        if name and name.strip() and uuid:
            candidates.setdefault(name.strip().casefold(), set()).add(str(uuid))

    if journal_path.exists():
        from specify_cli.event_journal.journal import EventJournal

        for row in EventJournal(journal_path).read_identity_projection_for_report():
            _offer(row.repo_slug, row.project_uuid)
            _offer(row.project_slug, row.project_uuid)
    if repo_root is not None:
        from specify_cli.identity.project import load_identity

        identity = load_identity(repo_root / ".kittify" / "config.yaml")
        _offer(identity.repo_slug, identity.project_uuid)
        _offer(identity.project_slug, identity.project_uuid)

    matches = sorted(candidates.get(raw.casefold(), set()))
    if not matches:
        known = ", ".join(sorted(candidates)) or "none recorded"
        _purge_usage_error(
            f'No project matches "{raw}". Names this machine has a record of '
            f"(repo slugs and project slugs alike): {known}. Pass the project uuid "
            "to purge a project whose rows carry no name."
        )
    if len(matches) > 1:
        _purge_usage_error(
            f'"{raw}" maps to {len(matches)} project uuids ({", ".join(matches)}); pass the uuid you mean — a purge must not span two projects.'
        )
    return matches[0], raw


def _purge_open_body_queue(queue_path: Path) -> Any | None:
    """The real body queue, only when its DB already exists.

    Constructing it creates the file and the schema, and a purge that *materialised*
    a store in order to report zero rows in it would be reporting on its own side
    effect.
    """
    if not queue_path.exists():
        return None
    try:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        return OfflineBodyUploadQueue(db_path=queue_path)
    except Exception as exc:  # noqa: BLE001 — reported as unreadable, never as empty
        _LOG.debug("body-upload queue unavailable for purge: %s", exc)
        return None


def _purge_validate_invocation(
    *,
    project: str | None,
    identity_less: bool,
    all_events: bool,
    apply: bool,
    dry_run: bool,
    confirm: str,
    report: Path | None,
) -> None:
    """Refuse a malformed or unauthorised invocation before any store is opened."""
    from specify_cli.delivery.retention import PURGE_ALL_CONFIRMATION

    if report is not None:
        # Checked before anything is deleted, not at write time. The ledger rows this
        # command removes are the only durable record of what happened to those
        # events, so discovering an unwritable report path *after* the delete would
        # destroy the record and the report of it in one run.
        try:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.touch()
        except OSError as exc:
            _purge_usage_error(f"--report path is not writable ({report}): {exc}")

    if apply and dry_run:
        _purge_usage_error("--apply and --dry-run are mutually exclusive.")
    selectors = [project is not None, identity_less, all_events]
    if not any(selectors):
        _purge_usage_error(
            "Choose exactly one of --project <slug-or-uuid>, --identity-less or --all."
        )
    if sum(1 for chosen in selectors if chosen) > 1:
        _purge_usage_error("--project, --identity-less and --all are mutually exclusive.")

    # The confirmation phrase gates the destructive `--all` run before anything is
    # opened. `purge_all_events` enforces the same phrase — that check is the pinned
    # one and it still runs — but it can only speak for the journal and the ledger,
    # while the body queue and the frame queue have no gate of their own. One phrase,
    # one constant, authorising all four stores (C-002, FR-017).
    if all_events and apply and confirm != PURGE_ALL_CONFIRMATION:
        console.print(
            "[red]Refused:[/red] a destructive --all run requires "
            f'--confirm "{PURGE_ALL_CONFIRMATION}". Nothing was deleted. Run without '
            "--apply first — its reported counts are exactly what a confirmed run removes."
        )
        raise typer.Exit(1)


def _purge_journal_selection(
    journal_path: Path,
    census: _RawCensus,
    *,
    all_events: bool,
    identity_less: bool,
    selector_uuid: str,
) -> tuple[frozenset[str], list[str]]:
    """``(census keys in scope, journal ids in scope)`` for this selector."""
    if all_events:
        return frozenset(census.by_key), _purge_journal_ids(
            journal_path, project_uuid=None, every_row=True
        )
    if identity_less:
        return frozenset({_PURGE_NULL_KEY}), _purge_journal_ids(
            journal_path, project_uuid=None, every_row=False
        )
    return frozenset({selector_uuid}), _purge_journal_ids(
        journal_path, project_uuid=selector_uuid, every_row=False
    )


def _purge_ledger_view(census: _RawCensus, *, all_events: bool) -> _RawCensus:
    """The ledger census as the selector sees it.

    ``--all`` covers the ledger's own rows — including the ghosts whose journal row
    ``sync gc`` already removed, which no journal-derived id list can name — so the
    selected count is the whole table.
    """
    if not all_events:
        return census
    return _RawCensus(
        total=census.total,
        by_key={_PURGE_LEDGER: census.total},
        unreadable=census.unreadable,
    )


def _purge_run_journal_ledger(
    journal_path: Path,
    ledger_path: Path,
    *,
    all_events: bool,
    identity_less: bool,
    selector_uuid: str,
    dry_run: bool,
    confirm: str,
) -> Any | None:
    """Run the journal+ledger purge primitive for this selector, or ``None``.

    ``None`` when no journal exists: there is nothing to purge, and opening
    ``EventJournal`` would *create* the store — a purge that materialised a store in
    order to report zero rows in it would be reporting on its own side effect.
    """
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.delivery.retention import (
        PurgeNotConfirmedError,
        purge_all_events,
        purge_identity_less_events,
        purge_project_events,
    )
    from specify_cli.event_journal.journal import EventJournal

    if not journal_path.exists():
        return None
    journal = EventJournal(journal_path)
    ledger = SqliteDeliveryLedger(str(ledger_path) if ledger_path.exists() else ":memory:")
    try:
        if all_events:
            return purge_all_events(
                journal=journal, ledger=ledger, dry_run=dry_run, confirmation=confirm
            )
        if identity_less:
            return purge_identity_less_events(
                journal=journal, ledger=ledger, dry_run=dry_run
            )
        return purge_project_events(
            selector_uuid, journal=journal, ledger=ledger, dry_run=dry_run
        )
    except PurgeNotConfirmedError as exc:
        console.print(f"[red]Refused:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        ledger.close()


def _purge_frames_scope(
    census: _RawCensus, frames_result: Any | None, *, all_events: bool, selector_uuid: str
) -> frozenset[str]:
    """The frame-census keys this run claims, as the primitive itself scoped them."""
    if all_events:
        return frozenset(census.by_key)
    if frames_result is None:
        return frozenset()
    if frames_result.unattributed_in_scope:
        # This checkout declares the target as its own project, so its unattributable
        # frames are its own content and are in scope — the pre-fix population the
        # incident actually produced, which carries no `project_uuid` at all.
        return frozenset({selector_uuid}) | _purge_unattributable_keys(census)
    return frozenset({selector_uuid})


def _purge_selector_line(
    *, project: str | None, identity_less: bool, selector_uuid: str, matched_slug: str | None
) -> str:
    if project is not None:
        matched = f' (matched slug "{matched_slug}")' if matched_slug else ""
        return f"Selector: project [bold]{selector_uuid}[/bold]{matched}"
    if identity_less:
        return "Selector: journal rows with no project identity (NULL)"
    return "Selector: [bold]every event[/bold] in the stores named below"


def _purge_run_body_queue(
    body_queue: Any,
    census: _RawCensus,
    *,
    all_events: bool,
    selector_uuid: str,
    dry_run: bool,
    confirm: str,
) -> tuple[frozenset[str], int]:
    """``(census keys in scope, rows the primitive reports removing)`` for this store.

    Two selectors, one per primitive, and the total one is **not** the union of the
    per-project one. ``remove_project_tasks`` strips its argument and returns 0 for a
    falsy one, so a row whose ``project_uuid`` is blank or padded is reachable by no
    project value at all — which is why fanning ``--all`` out over the census keys
    (what this did before ``purge_all_body_uploads`` existed) could not empty the
    store and had to report those rows as reachable by nothing.

    The returned count is what the primitive *claims*; the differential the operator
    is shown is measured separately from this module's own two censuses (NFR-006).
    """
    from specify_cli.delivery.retention import (
        PurgeNotConfirmedError,
        purge_all_body_uploads,
        purge_project_body_uploads,
    )

    if not all_events:
        result = purge_project_body_uploads(
            selector_uuid, body_queue=body_queue, dry_run=dry_run
        )
        return frozenset({selector_uuid}), result.removed

    try:
        total = purge_all_body_uploads(
            body_queue=body_queue, dry_run=dry_run, confirmation=confirm
        )
    except PurgeNotConfirmedError as exc:
        console.print(f"[red]Refused:[/red] {exc}")
        raise typer.Exit(1) from exc
    return frozenset(census.by_key), total.removed


def _purge_outcomes(
    *,
    before: dict[str, _RawCensus],
    after: dict[str, _RawCensus],
    scopes: dict[str, frozenset[str]],
    locations: dict[str, str],
    reported: dict[str, int | None],
    result: Any | None,
    ghosts_before: int,
    identity_less: bool,
    in_checkout: bool,
    frames_census_reported: int,
) -> dict[str, _PurgeStoreOutcome]:
    """Assemble the per-store outcome from the two independent censuses.

    ``removed_reported`` is carried alongside ``removed_observed`` rather than instead
    of it: the report shows what the purge said *and* what the stores show, so a
    disagreement is visible instead of averaged away.
    """
    outcomes: dict[str, _PurgeStoreOutcome] = {}
    for store in (_PURGE_JOURNAL, _PURGE_LEDGER, _PURGE_BODY, _PURGE_FRAMES):
        if store == _PURGE_LEDGER:
            removed, others = _purge_ledger_differential(before[store], after[store])
        else:
            removed, others = _purge_differential(before[store], after[store], scopes[store])
        outcomes[store] = _PurgeStoreOutcome(
            store=store,
            location=locations[store],
            in_scope=before[store].count(scopes[store]),
            removed_observed=removed,
            removed_reported=reported[store],
            others_delta_observed=others,
            total_after=after[store].total,
            left_behind=_purge_left_behind(after[store]),
            unreadable=before[store].unreadable or after[store].unreadable,
        )

    ledger = outcomes[_PURGE_LEDGER]
    ledger.left_behind = {"without_journal_row": ghosts_before} if ghosts_before else {}
    if result is not None:
        ledger.states = {
            str(name): int(count) for name, count in result.ledger_status_before.items()
        }
        ledger.never_attempted = result.never_attempted

    if identity_less:
        note = (
            "not spanned by --identity-less: unattributable rows here cannot be "
            "attributed to any project, and only --all reaches them"
        )
        outcomes[_PURGE_BODY].note = note
        outcomes[_PURGE_FRAMES].note = note
    if not in_checkout:
        outcomes[_PURGE_FRAMES].note = (
            "no checkout resolved from the current directory, so no local-commit queue "
            "was inspected — re-run from inside the checkout"
        )
    elif before[_PURGE_FRAMES].unreadable:
        outcomes[_PURGE_FRAMES].note = (
            f"the purge's own census reads {frames_census_reported} queued frame(s) from "
            "a file this command could not parse, so that number is not evidence of "
            "what the file holds — repair or remove the file and re-run"
        )
    return outcomes


def _purge_not_reached(
    *,
    after: dict[str, _RawCensus],
    journal_scope: frozenset[str],
    frames_scope: frozenset[str],
    body_scope: frozenset[str],
    ghosts_before: int,
    all_events: bool,
) -> list[dict[str, Any]]:
    """Name every population this run leaves behind, with its count and its selector.

    A residue nobody names is the same defect as a report that overstates. All five
    are real rather than hypothetical: the NULL-identity rows the backfill must not
    delete (C-002), the non-NULL blank and whitespace-only uuids that are visible in
    the census and reachable by no targeted selector, the ledger rows whose journal row
    ``sync gc`` already removed (so every machine that has run it holds some), the
    body-upload rows no *project* selector reaches, and the pre-fix frames of a
    checkout that vouches for nothing.

    Every population is filtered against the scope this run actually claimed, so a
    row the current selector already covers is not also listed as left behind.
    """
    rows: list[dict[str, Any]] = []

    def add(
        population: str, description: str, count: int | None, reachable_by: str, text: str
    ) -> None:
        rows.append(
            {
                "population": population,
                "description": description,
                "count": count,
                "reachable_by": reachable_by,
                "reachable_by_text": text,
            }
        )

    journal = after[_PURGE_JOURNAL]
    null_left = journal.by_key.get(_PURGE_NULL_KEY, 0)
    if null_left and _PURGE_NULL_KEY not in journal_scope:
        add(
            "journal_identity_null",
            "journal rows with a NULL project identity",
            null_left,
            "--identity-less",
            "permanently undeliverable and matchable by no project; run "
            "`sync purge --identity-less`",
        )
    blank_left = sum(
        count
        for key, count in journal.by_key.items()
        if key != _PURGE_NULL_KEY and not key.strip() and key not in journal_scope
    )
    if blank_left:
        add(
            "journal_identity_blank",
            "journal rows whose project_uuid is blank or whitespace-only",
            blank_left,
            "--all",
            "visible in the census and selectable by nothing else: a project purge "
            "blanks a falsy selector and the identity-less selector is NULL-only, so "
            "only `sync purge --all` reaches them",
        )
    if ghosts_before:
        add(
            "ledger_without_journal_row",
            "delivery-ledger rows whose journal row is already gone",
            ghosts_before,
            "--all",
            "every targeted selection collects its ids from the journal, and `sync gc` "
            "removes journal rows while preserving ledger history by design",
        )
    body_blank = sum(
        count
        for key, count in after[_PURGE_BODY].by_key.items()
        if (not key or key != key.strip()) and key not in body_scope
    )
    if body_blank:
        add(
            "body_uploads_identity_blank",
            "queued document bodies whose project_uuid is blank or padded",
            body_blank,
            "--all",
            "the queue's per-project removal strips its argument and refuses a falsy "
            "one, so no --project value reaches these rows; `sync purge --all` clears "
            "the store outright and is the only selector that does",
        )
    frames_unattributed = sum(
        count
        for key, count in after[_PURGE_FRAMES].by_key.items()
        if (key == _PURGE_NULL_KEY or not key.strip()) and key not in frames_scope
    )
    if frames_unattributed:
        add(
            "local_commit_frames_unattributed",
            "queued local-commit frames carrying no project_uuid",
            frames_unattributed,
            "--all",
            "this checkout does not declare the purged project as its own, so it "
            "vouches for nothing; `sync purge --all` run from the owning checkout "
            "reaches them",
        )
    if all_events:
        add(
            "local_commit_frames_other_checkouts",
            "other checkouts' queued local-commit frames",
            None,
            "run this command from each checkout",
            "per-checkout state with no registry to enumerate it — deliberately not "
            "counted, because a count that cannot be proven complete would be worse "
            "than none",
        )
    return rows


def _purge_faults(
    *,
    outcomes: dict[str, _PurgeStoreOutcome],
    before: dict[str, _RawCensus],
    after: dict[str, _RawCensus],
    apply: bool,
    others_total: int,
    frames_census_reported: int,
    frames_census_disagrees: bool,
) -> list[str]:
    """Everything the measurements say went wrong. Empty means NFR-006 held.

    Each entry is a disagreement between two independently obtained numbers, never a
    restatement of one of them: the stores' own before/after against what the purge
    reported, and the purge's census of the frame file against the file itself.
    """
    faults: list[str] = []
    if frames_census_disagrees:
        faults.append(
            f"{_PURGE_STORE_LABELS[_PURGE_FRAMES]}: the purge's census reads "
            f"{frames_census_reported} queued frame(s) where the file holds "
            f"{before[_PURGE_FRAMES].total} — the purge is not acting on the file's "
            "actual contents."
        )
    if apply:
        faults.extend(
            f"{_PURGE_STORE_LABELS[store]}: unreadable, so a destructive run cannot "
            "claim to have cleared it."
            for store, outcome in outcomes.items()
            if outcome.unreadable
        )
    if others_total:
        faults.append(
            f"{others_total} row(s) outside the selection changed. Either the purge "
            "over-reached or another writer (a running sync daemon, a concurrent "
            "capture) touched a store during the run — stop the daemon and re-measure "
            "before trusting this report."
        )
    for store, outcome in outcomes.items():
        expected = outcome.in_scope if apply else 0
        if outcome.removed_observed != expected:
            faults.append(
                f"{_PURGE_STORE_LABELS[store]}: expected {expected} row(s) to go, "
                f"measured {outcome.removed_observed}."
            )
        # The journal's reported count is not comparable under `--all`: that selection
        # deliberately includes ledger-only ids that were never journal rows.
        if (
            apply
            and store != _PURGE_JOURNAL
            and outcome.removed_reported is not None
            and outcome.removed_reported != outcome.removed_observed
        ):
            faults.append(
                f"{_PURGE_STORE_LABELS[store]}: the purge reported "
                f"{outcome.removed_reported} removed, the store shows "
                f"{outcome.removed_observed}."
            )
        # The ledger census is deliberately partial — one synthetic bucket for the
        # selection, because the store has no project column to group by — so its
        # totality is enforced by `_purge_ledger_differential`'s derivation instead.
        if store != _PURGE_LEDGER and (before[store].unbucketed or after[store].unbucketed):
            faults.append(
                f"{_PURGE_STORE_LABELS[store]}: rows exist that the per-project census "
                "cannot account for, so this store's differential is not trustworthy."
            )
    return faults


def _purge_print_verdict(faults: list[str], *, apply: bool, all_events: bool) -> None:
    """State what the measurements support, and never more than that."""
    if apply:
        console.print(f"\n[dim]{_PURGE_NON_ATOMIC_NOTE}[/dim]")
    if faults:
        console.print("\n[bold red]NFR-006 not satisfied[/bold red]")
        for fault in faults:
            console.print(f"  [red]•[/red] {fault}")
        return
    scope_claim = (
        "nothing outside the scope named above changed"
        if all_events
        else "0 rows belonging to any other project changed"
    )
    console.print(
        "\n[green]Differential verified against the stores[/green] (measured by "
        f"re-reading them, not by summing what the purge reported): {scope_claim}."
    )


def _purge_render(
    *,
    selector_line: str,
    dry_run: bool,
    outcomes: dict[str, _PurgeStoreOutcome],
    not_reached: list[dict[str, Any]],
    scope_note: str | None,
) -> None:
    """Print the operator's report: the plan, the residue, and the scope."""
    header = (
        "[bold yellow]DRY RUN[/bold yellow] — no rows have been deleted"
        if dry_run
        else "[bold red]APPLIED[/bold red] — rows have been deleted"
    )
    console.print(f"\n[bold]Purge[/bold] {header}")
    console.print(selector_line)

    table = Table(show_header=True, header_style="bold cyan", box=None, pad_edge=False)
    table.add_column("Store")
    table.add_column("Location", overflow="fold")
    table.add_column("In scope", justify="right")
    table.add_column("Removed", justify="right")
    table.add_column("Store total after", justify="right")
    for store, outcome in outcomes.items():
        table.add_row(
            _PURGE_STORE_LABELS[store],
            outcome.location,
            str(outcome.in_scope),
            str(outcome.removed_observed),
            str(outcome.total_after),
        )
    console.print(table)

    ledger = outcomes[_PURGE_LEDGER]
    states = "  ".join(f"{name}={count}" for name, count in sorted(ledger.states.items()))
    console.print(
        "Delivery state of the events in scope: "
        f"{states or 'no delivery attempt recorded'}"
        f"  never-attempted={ledger.never_attempted}"
    )
    console.print(
        "[dim]The ledger rows are deleted, so this breakdown is the only surviving "
        "record of what happened to those events. Keep it (--report writes it as "
        "JSON).[/dim]"
    )

    for outcome in outcomes.values():
        if outcome.unreadable:
            console.print(
                f"[yellow]Warning:[/yellow] the {_PURGE_STORE_LABELS[outcome.store]} store "
                f"could not be read ({outcome.location}). Its rows are NOT accounted for "
                "above — treat this purge as incomplete until the store is readable."
            )
        if outcome.note:
            console.print(f"[dim]{_PURGE_STORE_LABELS[outcome.store]}: {outcome.note}[/dim]")

    if all(outcome.in_scope == 0 for outcome in outcomes.values()):
        # "0 rows removed" and "wrong selector" look identical in a count, and this
        # report is the operator's only record. Say which one it is.
        console.print(
            "[yellow]Nothing matched this selector in any store.[/yellow] If rows were "
            "expected, check the value: these stores are keyed by project uuid, and "
            "`spec-kitty sync doctor` lists the projects the journal actually holds."
        )

    if not_reached:
        console.print("\n[bold]Not reached by this purge[/bold]")
        for row in not_reached:
            count = "unknown" if row["count"] is None else str(row["count"])
            console.print(f"  • {row['description']}: {count} — {row['reachable_by_text']}")

    if scope_note:
        console.print(f"\n[bold yellow]{scope_note}[/bold yellow]")


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
        help=(
            "Purge journal/ledger rows whose project identity is NULL — permanently "
            "undeliverable rows that no project selector can match."
        ),
    ),
    all_events: bool = typer.Option(
        False,
        "--all",
        help=(
            "Purge every row of this machine's journal, delivery ledger and "
            "body-upload queue, plus THIS checkout's queued local-commit frames. "
            "Requires --confirm with the confirmation phrase."
        ),
    ),
    apply: bool = typer.Option(
        False, "--apply", help="Actually delete. Without it this command only reports."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Report only, deleting nothing (this is the default)."
    ),
    confirm: str = typer.Option(
        "",
        "--confirm",
        help=(
            "Confirmation phrase authorising a destructive --all run. Run without it "
            "once; the refusal names the exact phrase and deletes nothing."
        ),
    ),
    report: Path = typer.Option(
        None,
        "--report",
        help=(
            "Write the purge report as JSON. Worth doing: the ledger rows this purge "
            "deletes are the only durable record of what happened to those events."
        ),
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

    ``--all`` is per-checkout for the local-commit frames and the report says so:
    the other three stores are machine-global, but there is no registry of checkouts,
    so another checkout's queued frames are neither listed nor touched.

    Examples:
        spec-kitty sync purge --project acme-migration
        spec-kitty sync purge --project acme-migration --apply --report purge.json
        spec-kitty sync purge --all
        spec-kitty sync purge --all --apply --confirm "purge all events"
    """
    import json as _json

    from specify_cli.core.paths import locate_project_root
    from specify_cli.delivery.retention import (
        ProjectPurgeResult,
        resolve_live_store_paths,
    )
    from specify_cli.sync.local_commit import (
        census_pending_local_commits,
        purge_all_pending_local_commits,
        purge_pending_local_commits,
    )
    from specify_cli.sync.queue import default_queue_db_path

    _purge_validate_invocation(
        project=project,
        identity_less=identity_less,
        all_events=all_events,
        apply=apply,
        dry_run=dry_run,
        confirm=confirm,
        report=report,
    )

    journal_path, ledger_path = resolve_live_store_paths()
    queue_path = default_queue_db_path()
    repo_root = locate_project_root(Path.cwd())
    frames_location = str(repo_root / _PURGE_SYNC_STATE_RELPATH) if repo_root is not None else "no Spec Kitty checkout resolved from the current directory"

    body_queue = _purge_open_body_queue(queue_path)
    before = {
        _PURGE_JOURNAL: _purge_journal_census(journal_path),
        _PURGE_BODY: _purge_body_census(body_queue),
        _PURGE_FRAMES: _purge_frames_census(repo_root),
    }
    # What the purge's own census sees, taken at the same instant as the CLI's raw
    # read of the same file so the two are comparable. Not decoration:
    # ``load_sync_state`` resets a malformed file to empty and never raises, so a
    # disagreement means the purge is about to act on a picture the file does not
    # support — the case where it reports "0 frames" over a file full of mission
    # slugs, i.e. client engagement names.
    frames_census_reported = sum(census_pending_local_commits(repo_root).values()) if repo_root is not None else 0
    frames_census_disagrees = repo_root is not None and not before[_PURGE_FRAMES].unreadable and frames_census_reported != before[_PURGE_FRAMES].total

    selector_uuid = ""
    matched_slug: str | None = None
    if project is not None:
        selector_uuid, matched_slug = _purge_resolve_project(project, journal_path, repo_root)
        conflicts = _purge_stored_spelling_conflicts(selector_uuid, [before[_PURGE_JOURNAL], before[_PURGE_BODY], before[_PURGE_FRAMES]])
        if conflicts:
            _purge_usage_error(
                f'"{selector_uuid}" is not how these stores spell that project. They hold '
                f"{', '.join(repr(key) for key in conflicts)}. Re-run with the stored "
                "spelling: the journal matches a uuid exactly while the frame queue "
                "compares case-insensitively, so a mixed selector would clear one store "
                "and silently miss the other."
            )

    # ---- selection scopes, expressed as census keys ------------------------ #
    journal_scope, journal_ids = _purge_journal_selection(
        journal_path,
        before[_PURGE_JOURNAL],
        all_events=all_events,
        identity_less=identity_less,
        selector_uuid=selector_uuid,
    )
    before[_PURGE_LEDGER] = _purge_ledger_view(
        _purge_ledger_census(ledger_path, journal_ids), all_events=all_events
    )
    ledger_scope = frozenset({_PURGE_LEDGER})
    ghosts_before = 0 if all_events else _purge_ledger_ghost_count(journal_path, ledger_path)

    # ---- run the primitives ----------------------------------------------- #
    result: ProjectPurgeResult | None = _purge_run_journal_ledger(
        journal_path,
        ledger_path,
        all_events=all_events,
        identity_less=identity_less,
        selector_uuid=selector_uuid,
        dry_run=not apply,
        confirm=confirm,
    )

    body_removed_reported = 0
    body_scope: frozenset[str] = frozenset()
    if body_queue is not None and not identity_less:
        body_scope, body_removed_reported = _purge_run_body_queue(
            body_queue,
            before[_PURGE_BODY],
            all_events=all_events,
            selector_uuid=selector_uuid,
            dry_run=not apply,
            confirm=confirm,
        )

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

    # ---- measure again, independently ------------------------------------- #
    after = {
        _PURGE_JOURNAL: _purge_journal_census(journal_path),
        _PURGE_LEDGER: _purge_ledger_view(
            _purge_ledger_census(ledger_path, journal_ids), all_events=all_events
        ),
        _PURGE_BODY: _purge_body_census(body_queue),
        _PURGE_FRAMES: _purge_frames_census(repo_root),
    }

    scopes = {
        _PURGE_JOURNAL: journal_scope,
        _PURGE_LEDGER: ledger_scope,
        _PURGE_BODY: body_scope,
        _PURGE_FRAMES: frames_scope,
    }
    locations = {
        _PURGE_JOURNAL: str(journal_path),
        _PURGE_LEDGER: str(ledger_path),
        _PURGE_BODY: str(queue_path),
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
                "kind": "project" if project is not None else ("identity-less" if identity_less else "all"),
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
    """Migrate legacy hash-scoped queue DBs into the append-only event journal.

    Lifts every currently-queued payload from the legacy ``queue.db`` and each
    scoped ``queues/queue-<digest>.db`` into the WP03 event journal, recording
    per-source provenance and quarantining divergent-duplicate collisions into
    the migration-audit store. Import opens source DBs read-only.

    On a clean migration (no conflicts, no source errors) the migrated rows are
    then deleted from their source queues so the legacy-row boundary converges
    and ``sync now`` / ``sync opt-in`` stop refusing (#2665). Pass
    ``--no-cleanup`` to skip that step and inspect first.

    Divergent-duplicate conflicts (same ``event_id``, different payload than the
    journal) block cleanup by default. Pass ``--resolve-conflicts keep-journal``
    to resolve them journal-wins: each conflicting source payload is archived to
    the audit quarantine and the source row removed, so the boundary can
    converge. The journal is never overwritten. Exits non-zero when unresolved
    conflicts still block cleanup (SC-011).

    Convergence also projects each row's stored identity into the journal's
    ``project_uuid``/``project_slug``/``repo_slug`` columns (#3030 H4). A row with a
    NULL ``project_uuid`` is permanently unselectable, so before this ran every
    pre-mission row — including the operator's own consenting project's history —
    was undeliverable forever. Identity is only recovered from the row's own stored
    envelope, never invented, so a row that carries none stays NULL and stays
    unselectable.

    ``--backfill-consent-index`` additionally maps path-keyed consent records onto
    the uuid index. That one is opt-in because it writes machine-global consent
    state and the uuid index outranks a repo default, so it can flip a project from
    denied to delivering; every mapped project and every unresolvable record is
    listed.

    Examples:
        spec-kitty sync migrate
        spec-kitty sync migrate --no-cleanup
        spec-kitty sync migrate --resolve-conflicts keep-journal
    """
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.migrate_journal import (
        AUDIT_DB_NAME,
        MigrationAudit,
        converge_legacy_runtime,
    )

    if resolve_conflicts is not None and resolve_conflicts != "keep-journal":
        console.print(
            f"[red]Unknown --resolve-conflicts strategy '{resolve_conflicts}'. "
            "Only 'keep-journal' is supported.[/red]"
        )
        raise typer.Exit(2)

    spec_kitty_dir = get_runtime_root().base
    runtime = _open_event_sync_runtime()
    audit = MigrationAudit(spec_kitty_dir / AUDIT_DB_NAME)
    try:
        converge: ConvergeResult = converge_legacy_runtime(
            spec_kitty_dir,
            journal=runtime.journal,
            audit=audit,
            resolved_target=runtime.target,
            resolve_conflicts=(resolve_conflicts == "keep-journal"),
            cleanup=not no_cleanup,
        )
        # FR-015: captured inside the try so the journal handle and the imported-id
        # list are taken from the same runtime that performed the migration, then
        # rendered below as a breakdown of the aggregate counts.
        moved_event_ids = converge.migration.imported_event_ids
        moved_journal = runtime.journal
    finally:
        with contextlib.suppress(Exception):
            audit.close()
        runtime.close()
    _print_migration_result(converge.migration)
    _print_identity_backfill_result(converge.identity_backfill)
    if backfill_consent_index:
        _run_consent_index_backfill()
    _render_migrated_composition(moved_journal, moved_event_ids)
    if converge.resolution is not None:
        _print_resolution_result(converge.resolution)
    if converge.cleanup is not None:
        _print_cleanup_result(converge.cleanup)
    if converge.migration.exit_code != 0:
        raise typer.Exit(converge.migration.exit_code)


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
    console.print(
        f"[green]✓[/green] Event sync mode set to [cyan]{config.mode.name}[/cyan]"
    )
    if config.mode is Mode.OPT_OUT:
        console.print(
            "[yellow]Note:[/yellow] OPT_OUT never silently drops Teamspace-bound "
            "events (C-008 fail-closed); such families are refused or audited at "
            "capture time."
        )


def _count_legacy_body_uploads_for_mission(mission_slug: str | None) -> int:
    """Return the number of legacy ``body_upload_queue`` rows tagged for *mission_slug*.

    Best-effort: returns 0 when the legacy DB does not exist, when the
    ``body_upload_queue`` table is missing, or when ``mission_slug`` is
    ``None``. The query is read-only — it never mutates the legacy DB.

    Used by FR-013 to tag the legacy-queue diagnostic when setup-plan
    body uploads from the active mission are still stranded in the
    pre-scoped queue file.
    """
    if not mission_slug:
        return 0
    import sqlite3 as _sqlite3

    from specify_cli.sync.queue import _legacy_queue_db_path

    legacy_db = _legacy_queue_db_path()
    if not legacy_db.exists():
        return 0
    try:
        conn = _sqlite3.connect(legacy_db)
    except _sqlite3.Error:
        return 0
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='body_upload_queue'"
        )
        if cur.fetchone() is None:
            return 0
        row = conn.execute(
            "SELECT COUNT(*) FROM body_upload_queue WHERE mission_slug = ?",
            (mission_slug,),
        ).fetchone()
        return int(row[0]) if row else 0
    except _sqlite3.Error:
        return 0
    finally:
        conn.close()


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
        failures.append(
            "foreground/daemon disagree on D-3 field(s): "
            + ", ".join(daemon_mismatched_fields)
        )
    if legacy_counts:
        total = sum(legacy_counts.values())
        tables = ", ".join(f"{t}={c}" for t, c in sorted(legacy_counts.items()))
        line = (
            f"legacy queue DB {legacy_db_path} has {total} row(s) pending "
            f"migration ({tables})"
        )
        if stranded_mission_slug:
            # FR-013: tag stranded setup-plan body uploads for the active mission.
            line += f" — setup-plan stranded mission slug {stranded_mission_slug}"
        failures.append(line)
    if orphan_count is not None and orphan_count > 0:
        failures.append(
            f"{orphan_count} orphan daemon record(s) detected; retire via "
            "`spec-kitty sync doctor`"
        )
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
        failures.append(
            "foreground/daemon disagree on D-3 field(s): "
            + ", ".join(bare_fields)
        )

    if failure_set.legacy_rows_for_scope > 0:
        total = failure_set.legacy_rows_for_scope
        parts: list[str] = []
        if failure_set.legacy_event_rows > 0:
            parts.append(f"queue={failure_set.legacy_event_rows}")
        if failure_set.legacy_body_upload_rows > 0:
            parts.append(f"body_upload_queue={failure_set.legacy_body_upload_rows}")
        legacy_path = _legacy_queue_db_path()
        line = (
            f"legacy queue DB {legacy_path} has {total} row(s) pending "
            f"migration ({', '.join(parts)})"
        )
        if stranded_mission_slug:
            line += (
                f" — setup-plan stranded mission slug {stranded_mission_slug}"
            )
        failures.append(line)

    n_orphans = len(failure_set.orphan_records)
    if n_orphans > 0:
        failures.append(
            f"{n_orphans} orphan daemon record(s) detected; retire via "
            "`spec-kitty sync doctor`"
        )

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


def _emit_status_check_json() -> None:
    """T014: emit a single JSON object on stdout per the status-output contract.

    The shape matches ``contracts/sync-status-output.md`` exactly:

    - ``ok`` / ``exit_code``
    - ``foreground`` (package_version, executable_path, source_path,
      server_url, team_or_user, queue_db_path, pid)
    - ``daemon_owner_record`` (status, pid, port, package_version,
      executable_path, source_path, server_url, team_or_user,
      queue_db_path)
    - ``active_queue`` (path, event_count, body_upload_count)
    - ``legacy_queue`` (path, event_count, body_upload_count,
      rows_in_scope)
    - ``mismatches`` (list of {field, foreground_value, daemon_value,
      remediation_hint})
    - ``orphan_records`` (list)

    Exit code: 0 if the structured failure set reports ``ok``, else 2.
    """
    import json as _json
    import sys as _sys

    from specify_cli.sync.daemon import scan_sync_daemons
    from specify_cli.sync.preflight import build_boundary_failure_set
    from specify_cli.sync.queue import OfflineQueue, _legacy_queue_db_path

    failure_set = build_boundary_failure_set(repo_root=Path.cwd())
    fg = failure_set.foreground
    record = failure_set.daemon_record

    # Live orphan daemon scan (#1071 failure mode): the on-disk owner-record
    # detection already feeds ``failure_set.orphan_records``; we also probe
    # live processes so an unregistered ``run_sync_daemon`` running outside
    # the singleton fails ``--check`` even when on-disk state is clean.
    try:
        live_orphan_report = scan_sync_daemons()
    except Exception:
        live_orphan_report = None
    live_orphan_count = (
        int(live_orphan_report.orphan_count) if live_orphan_report is not None else 0
    )

    # FR-004 / contracts/sync-status-output.md: when
    # ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` is set but no authenticated
    # identity is available, the gate exits 2 with ``ok=false`` and the
    # auth-absent reason surfaced in the JSON body. ``auth_required``
    # is True iff the SaaS-sync feature flag is enabled.
    auth_required = is_saas_sync_enabled()
    auth_present = fg.server_url is not None and fg.team_or_user is not None

    # Active queue counts. Best-effort: never raise from a JSON path.
    queue = OfflineQueue()
    active_event_count = 0
    try:
        active_event_count = int(queue.size())
    except Exception:
        active_event_count = 0
    active_body_count = 0
    try:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue
        import sqlite3 as _sqlite3

        active_body_queue = OfflineBodyUploadQueue(db_path=queue.db_path)
        _conn = _sqlite3.connect(active_body_queue.db_path)
        try:
            active_body_count = int(
                _conn.execute(
                    "SELECT COUNT(*) FROM body_upload_queue"
                ).fetchone()[0]
            )
        finally:
            _conn.close()
    except Exception:
        active_body_count = 0

    ok = (
        failure_set.ok
        and (auth_present or not auth_required)
        and live_orphan_count == 0
    )
    payload: dict[str, Any] = {
        "ok": ok,
        "exit_code": 0 if ok else 2,
        "auth_required": auth_required,
        "auth_present": auth_present,
        # Remote/import honesty (#2264). ``ok`` stays boundary/transport
        # coherence ONLY — it never reflects remote materialization. These typed
        # fields carry remote-project + historical-import state so a consumer
        # asserting SaaS population reads THESE, not ``ok``. Honest ``unknown``
        # until the import engine (#2262) populates them.
        "remote_sync": {
            "remote_project_state": "unknown",
            "materialized_at": None,
            "historical_import_state": "unknown",
            "last_blocker_sample": None,
        },
        "live_orphan_daemon_count": live_orphan_count,
        "foreground": {
            "package_version": fg.package_version,
            "executable_path": str(fg.executable_path),
            "source_path": str(fg.source_path),
            "server_url": fg.server_url,
            "team_or_user": fg.team_or_user,
            "queue_db_path": str(fg.queue_db_path),
            "pid": fg.pid,
        },
        "daemon_owner_record": {
            "status": failure_set.daemon_status,
            "pid": record.pid if record is not None else None,
            "port": record.port if record is not None else None,
            "package_version": record.package_version if record is not None else None,
            "executable_path": record.executable_path if record is not None else None,
            "source_path": (
                record.source_checkout_path if record is not None else None
            ),
            "server_url": record.server_url if record is not None else None,
            "team_or_user": (
                _render_daemon_team_or_user(record) if record is not None else None
            ),
            "queue_db_path": record.queue_db_path if record is not None else None,
        },
        "active_queue": {
            "path": str(fg.queue_db_path),
            "event_count": active_event_count,
            "body_upload_count": active_body_count,
        },
        "legacy_queue": {
            "path": str(_legacy_queue_db_path()),
            "event_count": failure_set.legacy_event_rows,
            "body_upload_count": failure_set.legacy_body_upload_rows,
            "rows_in_scope": failure_set.legacy_rows_for_scope,
        },
        "mismatches": [
            {
                "field": m.field,
                "foreground_value": m.foreground_value,
                "daemon_value": m.daemon_value,
                "remediation_hint": m.remediation_hint,
            }
            for m in failure_set.mismatches
        ],
        "orphan_records": [
            {
                "pid": r.pid,
                "port": r.port,
                "package_version": r.package_version,
                "executable_path": r.executable_path,
                "source_path": r.source_checkout_path,
                "server_url": r.server_url,
                "team_or_user": _render_daemon_team_or_user(r),
                "queue_db_path": r.queue_db_path,
                "started_at": r.started_at,
            }
            for r in failure_set.orphan_records
        ],
    }

    # Additive WP11 sections (FR-019, SC-010): merge the seven event-sync
    # sections onto the legacy payload — every pre-existing top-level field is
    # preserved. Best-effort: the additive sections must never break the legacy
    # ``--check --json`` gate (NFR-006). On any failure we still merge the seven
    # sections in their empty/default shape so the additive surface is ALWAYS
    # present (every consumer can read all seven keys regardless of runtime
    # health), and stamp an ``event_sync_status_error`` marker for diagnosis.
    runtime: _EventSyncRuntime | None = None
    try:
        runtime = _open_event_sync_runtime_readonly()
        payload = _event_sync_report(payload, runtime)
    except Exception as exc:  # legacy --check contract must survive any failure
        from specify_cli.delivery.status_report import default_status_sections

        _LOG.debug("event-sync status sections unavailable: %s", exc)
        payload = {**payload, **default_status_sections()}
        payload["event_sync_status_error"] = str(exc)[:200]
    finally:
        if runtime is not None:
            runtime.close()

    # Write directly to ``sys.stdout`` (not Rich) so the output is one
    # JSON object with no markup, panels, or wrapping.
    _sys.stdout.write(_json.dumps(payload))
    _sys.stdout.write("\n")
    _sys.stdout.flush()

    if not ok:
        raise typer.Exit(2)


@app.command()
def status(  # noqa: C901
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
    from specify_cli.auth import get_token_manager
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.daemon import get_sync_daemon_status, scan_sync_daemons
    from specify_cli.sync.queue import OfflineQueue

    # T014: --check --json short-circuit. Emits a single JSON object on
    # stdout matching contracts/sync-status-output.md and exits 0/2 based
    # on the structured failure set. Suppresses the human-readable block.
    if check_connection is True and json_output is True:
        _emit_status_check_json()
        return

    console.print()
    console.print("[cyan]Spec Kitty Sync Status[/cyan]")
    console.print()

    # Load configuration
    config = SyncConfig()
    # Show the resolved runtime target (SPEC_KITTY_SAAS_URL precedence folded
    # in) — the URL sync actually hits — not the raw config.toml value (#2146).
    server_url = config.resolve_runtime_target().resolved_server_url
    saas_enabled = is_saas_sync_enabled()
    queue = OfflineQueue()
    tm = get_token_manager()
    daemon_status = get_sync_daemon_status()

    # Display status
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")

    # Queue size
    queue_size = queue.size()
    queue_color = "green" if queue_size == 0 else "yellow"
    table.add_row("Queue", f"[{queue_color}]{queue_size} event(s)[/{queue_color}]")

    # Feature flag
    if saas_enabled:
        table.add_row("SaaS Sync", "[green]Enabled[/green]")
    else:
        table.add_row("SaaS Sync", f"[yellow]Disabled[/yellow] ({SAAS_SYNC_ENV_VAR}=1)")

    # Daemon / transport status
    daemon_text = "[green]Running[/green]" if daemon_status.healthy else "[dim]Stopped[/dim]"
    table.add_row("Daemon", daemon_text)
    if daemon_status.url:
        table.add_row("Daemon URL", daemon_status.url)
    if daemon_status.pid is not None:
        table.add_row("Daemon PID", str(daemon_status.pid))
    if daemon_status.port is not None:
        table.add_row("Daemon Port", str(daemon_status.port))

    sync_mode = "[green]Global daemon[/green]" if daemon_status.sync_running else "[yellow]Queue only[/yellow]"
    table.add_row("Sync Mode", sync_mode)
    websocket_color = "green" if daemon_status.websocket_status == "Connected" else "yellow"
    table.add_row("WebSocket", f"[{websocket_color}]{daemon_status.websocket_status}[/{websocket_color}]")

    # Last sync
    if daemon_status.last_sync:
        try:
            parsed_sync_time = parse_iso(daemon_status.last_sync)
            table.add_row(
                _STATUS_LAST_SYNC_LABEL,
                parsed_sync_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            )
        except ValueError:
            table.add_row(_STATUS_LAST_SYNC_LABEL, daemon_status.last_sync)
    else:
        table.add_row(_STATUS_LAST_SYNC_LABEL, "[dim]Never[/dim]")

    if daemon_status.consecutive_failures > 0:
        table.add_row("Failures", f"[yellow]{daemon_status.consecutive_failures} consecutive[/yellow]")

    # Auth status
    if saas_enabled:
        auth_ok = tm.is_authenticated
        auth_text = "[green]Authenticated[/green]" if auth_ok else "[yellow]Not authenticated[/yellow]"
    else:
        auth_text = "[dim]Disabled by feature flag[/dim]"
    table.add_row("Auth", auth_text)

    # Server URL
    table.add_row(_BOUNDARY_LABEL_SERVER_URL.strip(), server_url)
    table.add_row("Config File", str(config.config_file))

    # Optionally test connection if --check flag is provided.
    # Guard against the function being invoked directly in tests (without Typer
    # parsing), where ``check_connection`` would be a ``typer.OptionInfo``
    # instance rather than a real bool. We only treat ``True`` as opt-in.
    auth_recovery_pending = False
    orphan_report = None
    if check_connection is True:
        connection_status, connection_note = _check_server_connection(server_url)
        table.add_row("Ping", connection_status)
        if connection_note:
            table.add_row("", f"[dim]{connection_note}[/dim]")
        # If the connection probe surfaced an auth-missing / expired state,
        # remember to offer teamspace-aware recovery once the table is rendered
        # (issue #829, Mission 7).
        auth_recovery_pending = (
            "Not authenticated" in connection_status
            or "Session expired" in connection_status
            or "Authentication failed" in connection_status
        )

        # Surface daemon-singleton honesty: scan for stale `run_sync_daemon`
        # processes that are not the one recorded in DAEMON_STATE_FILE.
        # Multiple co-existing daemons (across checkouts / Conductor workspaces /
        # bleed-through restarts) are how the regression in #1071 manifests in
        # practice; report them here so operators see the divergence without
        # having to grep ``ps`` themselves.
        try:
            orphan_report = scan_sync_daemons()
        except Exception:
            orphan_report = None
        if orphan_report is not None:
            if orphan_report.orphan_count == 0:
                table.add_row(
                    "Singleton",
                    "[green]OK[/green] (no orphan daemons detected)",
                )
            else:
                table.add_row(
                    "Singleton",
                    f"[yellow]{orphan_report.orphan_count} orphan daemon(s) detected[/yellow]",
                )

    console.print(table)
    console.print()

    if orphan_report is not None and orphan_report.orphan_count > 0:
        console.print(
            "[yellow]Other live ``run_sync_daemon`` processes detected outside the "
            "registered singleton (#1071):[/yellow]"
        )
        for orphan in orphan_report.orphan_processes:
            console.print(f"  PID {orphan.pid}: {' '.join(orphan.cmdline)}")
        console.print(
            "[dim]Run `spec-kitty sync doctor` for a guided cleanup, or kill the "
            "rogue processes manually.[/dim]"
        )
        console.print()

    # --- Queue health section (T022/T023) ---
    queue_stats = queue.get_queue_stats()
    if queue_stats.total_queued > 0:
        format_queue_health(queue_stats, console)
        console.print()
    else:
        console.print("[green]Queue empty -- all events synced.[/green]")
        console.print()

    # --- Per-project journal composition (#3030 T021 / FR-015, SC-004) -----
    # Placed immediately after the queue-health block for the same reason as in
    # `doctor`: "Queue empty -- all events synced" is read off the legacy
    # `OfflineQueue`, which `sync migrate` empties. Left alone it is the sentence
    # that made the 2026-07-27 incident invisible for weeks. `status` has no
    # global issues list, so the warnings are printed inline here.
    journal_issues: list[str] = []
    _render_per_project_store(console, journal_issues)
    for issue in journal_issues:
        console.print(f"  [yellow]![/yellow] {issue}")
    console.print()

    # --- Identity Boundary section (WP03 / FR-008) -------------------------
    # The boundary view answers: "who do I think I am, who does the recorded
    # daemon think it is, and what state is sitting in the legacy/scoped
    # queue files right now?" We render the foreground identity, the
    # active scoped queue, the legacy queue, the recorded daemon owner,
    # the D-3 mismatched fields, and the orphan-record count.
    #
    # T010 / T013: drive the boundary block from the single-source-of-truth
    # `BoundaryFailureSet` so this view never drifts from the --check gate
    # or the preflight. Full FR-005 fields are rendered.
    from specify_cli.sync.owner import (
        compute_foreground_identity,
        list_orphan_records,
        mismatched_fields,
        read_owner_record,
    )
    from specify_cli.sync.preflight import build_boundary_failure_set
    from specify_cli.sync.queue import (
        _legacy_queue_db_path,
        detect_legacy_rows_for_scope,
    )

    foreground_identity = compute_foreground_identity()
    daemon_record = read_owner_record()
    daemon_mismatched: list[str] = []
    if daemon_record is not None:
        daemon_mismatched = mismatched_fields(daemon_record, foreground_identity)
    orphan_records = list_orphan_records()
    orphan_record_count = len(orphan_records)

    # Structured failure set — single source of truth for --check / preflight.
    failure_set = build_boundary_failure_set(repo_root=Path.cwd())

    active_scope = foreground_identity.get("auth_scope")
    # WP02: ``detect_legacy_rows_for_scope`` now returns a structured
    # ``LegacyRowCounts`` value that still acts like a per-table mapping
    # (so the existing ``legacy_counts.get("body_upload_queue", 0)`` /
    # ``sum(legacy_counts.values())`` / ``sorted(legacy_counts.items())``
    # sites keep working) while exposing named subtotals to callers that
    # want them (preflight uses those).
    legacy_counts = detect_legacy_rows_for_scope(
        active_scope if isinstance(active_scope, str) else ""
    )
    legacy_db_path = _legacy_queue_db_path()

    # FR-013: detect setup-plan body uploads stranded in the legacy DB
    # for the current mission slug. Best-effort — when the active mission
    # cannot be derived from cwd (e.g. operator running from the repo
    # root), we omit the tag.
    _workspace_path, active_mission_slug = _detect_workspace_context()
    stranded_count = _count_legacy_body_uploads_for_mission(active_mission_slug)
    stranded_tag = active_mission_slug if stranded_count > 0 else None

    # Active-queue diagnostics on the foreground queue.
    body_queue_count = 0
    try:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        active_body_queue = OfflineBodyUploadQueue(db_path=queue.db_path)
        import sqlite3 as _sqlite3

        _conn = _sqlite3.connect(active_body_queue.db_path)
        try:
            body_queue_count = int(
                _conn.execute("SELECT COUNT(*) FROM body_upload_queue").fetchone()[0]
            )
        finally:
            _conn.close()
    # Read-only diagnostic: never let status rendering fail on queue inspection.
    except Exception:
        body_queue_count = 0

    # Legacy body-upload count (read-only).
    legacy_body_count = legacy_counts.get("body_upload_queue", 0)
    legacy_event_count = legacy_counts.get("queue", 0)

    # WP02 (#1123) + WP02 cycle 1 (B-1): the entire Identity Boundary
    # view is now rendered as plain ``Console.print`` line output rather
    # than a Rich ``Table``. This satisfies two contracts simultaneously:
    #
    # 1. FR-005 path-verbatim: every canonical file path renders
    #    full-width, single-line, no Rich ellipsis (`…`), under non-TTY
    #    capture or narrow terminals.
    # 2. Cross-repo canary parser contract: the sibling canary at
    #    ``spec-kitty-end-to-end-testing/src/spec_kitty_e2e/
    #    identity_boundary/status_parser.py`` walks rows under section
    #    headers (``Foreground:``, ``Daemon owner record:``,
    #    ``Active queue:``, ``Legacy queue:``) and requires the
    #    queue-section child key to be literally ``Path`` (not
    #    ``Active queue path``). Each section's rows must be indented and
    #    follow the section header in line order.
    #
    # We keep the row data in plain ``list[tuple[str, str]]`` lists per
    # section, then emit them via ``_print_boundary_section`` which
    # writes the section header followed by indented ``  Key  Value``
    # rows separated by 2+ spaces (the parser's ``_KEY_VALUE_RE``
    # contract).
    #
    # The canonical path fields per ``contracts/sync-status-check-rendering.md``
    # are:
    #   - Foreground.executable_path / source_path / queue_db_path
    #   - Daemon owner record.executable_path / source_path / queue_db_path
    #   - Active queue.path
    #   - Legacy queue.path
    # All of them flow through this same indented-row pathway and inherit
    # the no-ellipsis guarantee from ``soft_wrap=True``/``overflow="ignore"``.

    fg = failure_set.foreground
    daemon_status_label = failure_set.daemon_status

    # ---- Foreground section ------------------------------------------------
    foreground_rows: list[tuple[str, str]] = [
        (_BOUNDARY_LABEL_PACKAGE_VERSION.strip(), str(fg.package_version or "-")),
        (_BOUNDARY_LABEL_EXECUTABLE_PATH.strip(), str(fg.executable_path or "-")),
        (_BOUNDARY_LABEL_SOURCE_PATH.strip(), str(fg.source_path or "-")),
        (_BOUNDARY_LABEL_SERVER_URL.strip(), fg.server_url if fg.server_url else _UNSET_VALUE),
        (_BOUNDARY_LABEL_TEAM_USER.strip(), fg.team_or_user if fg.team_or_user else _UNSET_VALUE),
        (_BOUNDARY_LABEL_QUEUE_DB_PATH.strip(), str(fg.queue_db_path or "-")),
    ]

    # ---- Daemon owner record section --------------------------------------
    daemon_rows: list[tuple[str, str]] = [("Status", daemon_status_label)]
    if daemon_record is None:
        daemon_rows.extend(
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
        # Render daemon team_or_user as "principal[/team]" to match the
        # canonical contract field.
        daemon_team_or_user = _render_daemon_team_or_user(daemon_record)
        daemon_rows.extend(
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

    # ---- Active queue section ---------------------------------------------
    # Parser-critical: child key MUST be ``Path`` (not ``Active queue path``).
    active_queue_rows: list[tuple[str, str]] = [
        ("Path", str(fg.queue_db_path or "-")),
        ("Event count", f"{queue_size}"),
        ("Body upload cnt", f"{body_queue_count}"),
    ]

    # ---- Legacy queue section ---------------------------------------------
    # Parser-critical: child key MUST be ``Path`` (not ``Legacy queue path``).
    legacy_queue_rows: list[tuple[str, str]] = [
        ("Path", str(legacy_db_path)),
        ("Event count", f"{failure_set.legacy_event_rows}"),
        ("Body upload cnt", f"{failure_set.legacy_body_upload_rows}"),
        ("Rows in scope", f"{failure_set.legacy_rows_for_scope}"),
    ]
    if stranded_tag:
        legacy_queue_rows.append(
            (
                "Stranded mission",
                f"setup-plan stranded mission slug {stranded_tag}",
            )
        )

    # ---- Top-level scalar rows (Mismatches / Orphan records / etc.) -------
    # These appear UNINDENTED (no leading 2-space indent) so the parser
    # treats them as terminators of the preceding section. The parser
    # picks them up from the top-level row stream by exact key match.
    n_mismatches = len(failure_set.mismatches)
    mismatches_value = (
        f"[red]{n_mismatches}[/red]" if n_mismatches else _ZERO_STATUS
    )
    orphan_value = (
        f"[yellow]{orphan_record_count}[/yellow]"
        if orphan_record_count
        else _ZERO_STATUS
    )
    if failure_set.mismatches:
        mismatch_field_names = [m.field for m in failure_set.mismatches]
        mismatched_fields_value = (
            f"[red]{', '.join(mismatch_field_names)}[/red]"
        )
    elif daemon_mismatched:
        mismatched_fields_value = f"[red]{', '.join(daemon_mismatched)}[/red]"
    else:
        mismatched_fields_value = "[green]none[/green]"

    # Preserve backward-compatible legacy-event/body summary line so
    # operator workflows that grep for ``body_upload_queue`` keep matching.
    legacy_line = (
        f"{legacy_event_count} event(s), {legacy_body_count} body upload(s)"
    )
    if stranded_tag:
        legacy_line += f" — setup-plan stranded mission slug {stranded_tag}"

    top_level_rows: list[tuple[str, str]] = [
        ("Mismatches", mismatches_value),
        ("Orphan records", orphan_value),
        ("Legacy queue rows", legacy_line),
        (_MISMATCHED_FIELDS_LABEL, mismatched_fields_value),
        ("Orphan daemon records", orphan_value),
    ]

    # When the canonical mismatch list is non-empty, render the detail
    # block per contract (foreground vs daemon vs remediation hint).
    if failure_set.mismatches:
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
        for m in failure_set.mismatches:
            mismatch_detail.add_row(
                m.field,
                m.foreground_value or _UNSET_VALUE,
                m.daemon_value or _UNSET_VALUE,
            )

    # WP02 cycle 1 (B-1): emit the Identity Boundary view as plain
    # line-oriented text so the cross-repo canary parser can attribute
    # ``Path`` rows to their preceding section headers. Each
    # ``_print_boundary_section`` call writes the header followed by
    # 2-space-indented ``Key  Value`` rows separated by 2+ spaces.
    # Top-level scalars (Mismatches / Orphan records / etc.) print
    # without leading indent so the parser treats them as section
    # terminators.
    console.print("[bold]Identity Boundary[/bold]")
    _print_boundary_section(console, "Foreground:", foreground_rows)
    _print_boundary_section(console, "Daemon owner record:", daemon_rows)
    _print_boundary_section(console, "Active queue:", active_queue_rows)
    _print_boundary_section(console, "Legacy queue:", legacy_queue_rows)
    # Top-level scalars: unindented ``Key  Value`` rows.
    for key, value in top_level_rows:
        # Pad key to a fixed column width matching the section rows so
        # values line up visually. The parser only requires >=2 spaces
        # between key and value at any indent (incl. zero indent).
        console.print(
            f"{key.ljust(24)}{value}",
            soft_wrap=True,
            overflow="ignore",
            crop=False,
            no_wrap=True,
            highlight=False,
        )
    console.print()
    if failure_set.mismatches:
        console.print(mismatch_detail)
        console.print()

    # Event-sync observability (WP12): the active retention x delivery mode
    # plus a compact, read-only summary of the journal/ledger state.
    _render_event_sync_status(console)
    console.print()

    if not check_connection:
        console.print("[dim]Use 'spec-kitty sync status --check' to test connectivity.[/dim]")
        console.print()

    # --- --check coherence gate (WP03 / FR-009) ---------------------------
    # Returns non-zero when any of the three FR-009 conditions hold. The
    # gate ONLY trips under --check so the read-only ``sync status``
    # surface keeps its existing exit-0 contract. T010: derived from the
    # structured failure set so it never drifts from `run_preflight`.
    #
    # FR-004 / contracts/sync-status-output.md: under --check, when
    # ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` is set but no authenticated
    # identity is available, the gate exits 2 (NOT 4 via the
    # ``auth_recovery_pending`` connected-teamspace recovery path).
    # We layer the auth-required failure into the boundary gate so the
    # exit code matches the documented status-output contract.
    if check_connection is True:
        failures = _build_boundary_check_failures(
            failure_set=failure_set,
            stranded_mission_slug=stranded_tag,
        )
        fg_id = failure_set.foreground
        auth_present_check = (
            fg_id.server_url is not None and fg_id.team_or_user is not None
        )
        auth_required_check = is_saas_sync_enabled()
        if auth_required_check and not auth_present_check:
            failures.append(
                "Hosted SaaS sync is enabled but no authenticated identity "
                "is available — run `spec-kitty auth login`."
            )
        # Live orphan daemon scan (#1071 failure mode): when ``scan_sync_daemons``
        # finds ``run_sync_daemon`` processes outside the registered singleton,
        # the boundary is incoherent regardless of whether auth and queue state
        # otherwise look healthy. The earlier render block (line ~1734) already
        # printed details to the operator; here we make ``--check`` reflect that
        # by adding a failure line so the gate exits 2 instead of 0.
        if orphan_report is not None and orphan_report.orphan_count > 0:
            failures.append(
                f"{orphan_report.orphan_count} live `run_sync_daemon` "
                "process(es) detected outside the registered singleton — "
                "run `spec-kitty sync doctor` for guided cleanup (#1071)."
            )
        if failures:
            console.print(
                "[red]Identity boundary check FAILED:[/red]",
                style=None,
            )
            for line in failures:
                console.print(f"  [red]![/red] {line}")
            console.print()
            raise typer.Exit(2)

    if auth_recovery_pending:
        outcome = handle_unauthenticated_with_teamspace(
            command_name="sync status",
            console=console,
        )
        if outcome is RecoveryOutcome.EXIT_4:
            raise typer.Exit(EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE)


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
    from specify_cli.sync.queue import OfflineQueue

    queue = OfflineQueue()
    pending = queue.drain_queue(limit=queue.MAX_QUEUE_SIZE)

    if not pending:
        if json_output:
            console.print(json_mod.dumps({"total": 0, "valid": 0, "invalid": 0, "results": []}))
        else:
            console.print("[green]No pending events in queue.[/green]")
        return

    results = diagnose_events(pending)

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
    console.print(
        f"Validated [cyan]{len(results)}[/cyan] event(s): "
        f"[green]{valid_count} valid[/green], "
        f"[red]{invalid_count} invalid[/red]"
    )

    # Show valid events (brief)
    for r in results:
        if r.valid:
            console.print(f"  [green]VALID[/green]   {r.event_id} ({r.event_type})")

    # Show invalid events (detailed)
    for r in results:
        if not r.valid:
            category_label = f" [{r.error_category}]" if r.error_category else ""
            console.print(
                f"\n  [red]INVALID[/red] {r.event_id} ({r.event_type}){category_label}"
            )
            for err in r.errors:
                console.print(f"    - {err}")

    console.print()


@app.command()
def doctor() -> None:  # noqa: C901
    """Diagnose sync health: queue, auth, and server connectivity.

    Runs a comprehensive check of offline queue state, authentication
    validity, and server reachability, printing actionable remediation
    steps for any issues found.

    Examples:
        spec-kitty sync doctor
    """
    from specify_cli.auth import get_token_manager
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.diagnose import diagnose_body_queue
    from specify_cli.sync.queue import OfflineQueue

    console.print()
    console.print("[bold cyan]Sync Doctor[/bold cyan]")
    console.print()

    issues: list[str] = []

    # --- 1. Queue health ---
    queue = OfflineQueue()
    stats = queue.get_queue_stats()
    body_queue = OfflineBodyUploadQueue(db_path=queue.db_path)
    body_diagnostics = diagnose_body_queue(body_queue)["body_queue"]
    queue_size = stats.total_queued
    max_size = stats.max_queue_size
    pct = (queue_size / max_size * 100) if max_size > 0 else 0

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim", min_width=20)
    table.add_column("Value")

    depth_color = "red" if pct >= 100 else ("yellow" if pct >= 80 else "green")
    table.add_row("Queue size", f"[{depth_color}]{queue_size:,} / {max_size:,} ({pct:.0f}%)[/{depth_color}]")

    if stats.oldest_event_age is not None:
        age_str = humanize_timedelta(stats.oldest_event_age)
        table.add_row("Oldest event", f"{age_str} ago")
    else:
        table.add_row("Oldest event", "[dim]n/a (empty)[/dim]")

    table.add_row("Queue DB", str(queue.db_path))
    table.add_row(
        "Body uploads",
        f"{body_diagnostics['total_tasks']} queued, "
        f"{body_diagnostics['recorded_failure_count']} recorded failure(s)",
    )

    if pct >= 100:
        issues.append(
            "Queue is FULL -- oldest events are being evicted to make room for new ones. "
            "Run `spec-kitty sync now` after fixing auth/connectivity."
        )
    elif pct >= 80:
        issues.append(
            f"Queue is {pct:.0f}% full. Consider syncing soon with `spec-kitty sync now`."
        )
    if body_diagnostics["recorded_failure_count"] > 0:
        issues.append(
            "Body upload failures were recorded. Review the recent body upload failures below "
            "and fix the underlying artifact or contract mismatch."
        )

    # --- 2. Auth status ---
    config = SyncConfig()
    # Resolved runtime target (env precedence folded in), not the raw
    # config.toml value, so the diagnostics row matches what sync hits (#2146).
    server_url = config.resolve_runtime_target().resolved_server_url
    table.add_row("Server URL", server_url)

    tm = get_token_manager()
    session = tm.get_current_session()
    if session is None:
        table.add_row("Auth", "[red]No credentials[/red]")
        issues.append("Not authenticated. Run `spec-kitty auth login`.")
    else:
        access_exp_dt = session.access_token_expires_at
        refresh_exp_dt = session.refresh_token_expires_at

        now = now_utc()

        access_ok = access_exp_dt is not None and access_exp_dt > now
        refresh_ok = (
            refresh_exp_dt is None  # no stored refresh expiry → treat as valid
            or refresh_exp_dt > now
        )

        if access_ok:
            table.add_row(
                _STATUS_ACCESS_TOKEN_LABEL,
                f"[green]Valid[/green] (expires {access_exp_dt.isoformat()})",
            )
        elif access_exp_dt is not None:
            table.add_row(
                _STATUS_ACCESS_TOKEN_LABEL,
                f"[red]Expired[/red] ({access_exp_dt.isoformat()})",
            )
        else:
            table.add_row(_STATUS_ACCESS_TOKEN_LABEL, "[red]Missing[/red]")

        if refresh_exp_dt is None:
            table.add_row(
                _STATUS_REFRESH_TOKEN_LABEL,
                "[green]Valid[/green] (no expiry stored)",
            )
        elif refresh_ok:
            table.add_row(
                _STATUS_REFRESH_TOKEN_LABEL,
                f"[green]Valid[/green] (expires {refresh_exp_dt.isoformat()})",
            )
        else:
            table.add_row(
                _STATUS_REFRESH_TOKEN_LABEL,
                f"[red]Expired[/red] ({refresh_exp_dt.isoformat()})",
            )

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

        if not access_ok and not refresh_ok:
            issues.append(
                "Both access and refresh tokens are expired. "
                "Run `spec-kitty auth login` to re-authenticate."
            )
        elif not access_ok and refresh_ok:
            issues.append(
                "Access token expired but refresh token is still valid. "
                "Token will auto-refresh on next sync attempt."
            )

    # --- 3. Server reachability ---
    connection_status, connection_note = _check_server_connection(server_url)
    table.add_row("Server", connection_status)
    if connection_note:
        table.add_row("", f"[dim]{connection_note}[/dim]")

    if "Unreachable" in connection_status or "Error" in connection_status:
        issues.append(
            f"Cannot reach server at {server_url}. "
            "Events will continue to queue locally."
        )

    # --- 3b. Daemon singleton invariant (spec-kitty#1071) ---
    # Inspect for live `run_sync_daemon` processes that are not the registered
    # singleton. Multiple co-existing daemons (across checkouts, workspaces, or
    # bleed-through restarts) are the exact failure mode that #1071 surfaced
    # during the canonical status investigation. Report them honestly here.
    from specify_cli.sync.daemon import scan_sync_daemons

    try:
        singleton_report = scan_sync_daemons()
    except Exception:
        singleton_report = None

    if singleton_report is not None:
        if singleton_report.orphan_count == 0:
            table.add_row(
                "Daemon singleton",
                "[green]OK[/green] (no orphan `run_sync_daemon` processes)",
            )
        else:
            table.add_row(
                "Daemon singleton",
                f"[yellow]{singleton_report.orphan_count} orphan daemon(s)[/yellow]",
            )
            issues.append(
                f"{singleton_report.orphan_count} live `run_sync_daemon` process(es) "
                f"are not the registered singleton. Multiple daemons make queue state "
                f"ambiguous (spec-kitty#1071). Kill the orphans manually or run "
                f"`spec-kitty sync stop` and a clean `spec-kitty sync now`."
            )

    console.print(table)
    console.print()

    # --- 3c. Per-project journal composition (#3030 T021 / FR-015, SC-004) ---
    # Deliberately rendered right below the queue-health rows it contradicts.
    # "Queue size 0" above comes from `OfflineQueue().get_queue_stats()`, which
    # `sync migrate` empties; this section reads the journal those events actually
    # live in. Throughout the 2026-07-27 incident the block above said healthy
    # while 9,133 journal events — 1,322 from projects that never opted in — sat
    # on disk, and the contamination was only found by hand-querying SQLite.
    _render_per_project_store(console, issues)
    # --- 3d. Can those consent states be trusted at all? (#3030 FR-020, SC-004) ---
    # Directly below the table whose "Consent" column it qualifies. Every state in
    # that column comes from a read that can fault, and a fault reads as ABSENCE
    # unless something says otherwise — which is the whole of FR-020.
    _render_consent_readability(console, issues)
    # --- 3e. Is tracker egress refused, and by which channel? (#3108 FR-014, SC-014) ---
    # Beside the readability block, not inside it: that section's contract is
    # readability, not verdict. Two rows, always -- one per EgressDestination --
    # because the on-disk provider does not determine the destination.
    _render_tracker_egress(console, issues)
    console.print()

    if singleton_report is not None and singleton_report.orphan_count > 0:
        orphan_table = Table(
            title="Orphan run_sync_daemon Processes",
            show_header=True,
            header_style="bold yellow",
            show_lines=False,
            expand=False,
        )
        orphan_table.add_column("PID", justify="right", style="yellow")
        orphan_table.add_column("Command line", overflow="fold")
        for orphan in singleton_report.orphan_processes:
            orphan_table.add_row(str(orphan.pid), " ".join(orphan.cmdline))
        console.print(orphan_table)
        console.print()

    # --- 4. Top event types (if queue non-empty) ---
    if stats.top_event_types:
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

    recent_failures = body_diagnostics["recent_failures"]
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

    # --- 4b. Orphan daemon records (WP03 / FR-010) ------------------------
    # The owner-record registry (WP02) may carry records whose recorded PID
    # is dead or whose executable has gone missing. List them here with a
    # copy-pasteable retirement hint so operators can clean up without
    # grepping the daemon directory.
    #
    # T015: this routes through ``list_orphan_records()`` — the SAME entry
    # point used by ``run_preflight`` and ``sync status --check`` — so the
    # three surfaces never disagree on what is orphaned. (Cross-file note
    # for WP04: ``doctor orphan-daemons`` in ``cli/commands/doctor.py``
    # must also call ``list_orphan_records()``.)
    from specify_cli.sync.owner import list_orphan_records, owner_record_path

    orphan_records = list_orphan_records()
    if orphan_records:
        issues.append(
            f"{len(orphan_records)} orphan daemon owner record(s) on disk; "
            f"retire via `rm {owner_record_path()}`."
        )
        orphan_table = Table(
            title="Orphan Daemons",
            show_header=True,
            header_style="bold yellow",
            show_lines=False,
            expand=False,
        )
        orphan_table.add_column("PID", justify="right", style="yellow")
        orphan_table.add_column("Port", justify="right")
        orphan_table.add_column("Version")
        orphan_table.add_column("Executable", overflow="fold")
        orphan_table.add_column("Started At")
        for record in orphan_records:
            orphan_table.add_row(
                str(record.pid),
                str(record.port),
                record.package_version,
                record.executable_path,
                record.started_at,
            )
        console.print(orphan_table)
        console.print(
            f"[dim]Retire orphan record(s): rm {owner_record_path()}[/dim]"
        )
        console.print()

    # --- 5. Summary ---
    if issues:
        console.print("[bold yellow]Issues found:[/bold yellow]")
        for issue in issues:
            console.print(f"  [yellow]![/yellow] {issue}")
        console.print()
    else:
        console.print("[bold green]No issues detected. Sync is healthy.[/bold green]")
        console.print()

    # --- 6. Teamspace-aware recovery (issue #829, Mission 7) ---
    # If we surfaced an auth-missing or token-expired issue AND the repo was
    # previously connected to a teamspace, offer interactive recovery (TTY) or
    # emit a structured stderr line + exit 4 (CI). When no teamspace is
    # detected, behavior is byte-identical to the existing doctor output.
    auth_missing = (
        session is None
        or any("auth login" in issue or "expired" in issue for issue in issues)
    )
    if auth_missing:
        outcome = handle_unauthenticated_with_teamspace(
            command_name="sync doctor",
            console=console,
        )
        if outcome is RecoveryOutcome.EXIT_4:
            raise typer.Exit(EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE)


__all__ = ["app"]
