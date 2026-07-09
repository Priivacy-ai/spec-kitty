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
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from specify_cli.delivery.config import EventSyncConfig, Mode
    from specify_cli.delivery.dispatcher import DispatchSummary
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.delivery.receivers import DeliveryReceiver
    from specify_cli.delivery.retention import RetentionResult
    from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.sync.migrate_journal import MigrationAudit, MigrationResult
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
from specify_cli.core.time_utils import now_utc_iso
from specify_cli.sync.feature_flags import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

console = Console()

_LOG = logging.getLogger(__name__)

_STATUS_ACCESS_TOKEN_LABEL = "Access token"  # noqa: S105
_STATUS_REFRESH_TOKEN_LABEL = "Refresh token"  # noqa: S105
_STATUS_LAST_SYNC_LABEL = "Last Sync"
_UNAUTHENTICATED_SYNC_NOW_MESSAGE = (
    "not authenticated: no valid access token. Run `spec-kitty auth login`."
)
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
    * Partial progress with a hard terminal failure → exit 1 under ``--strict``.

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
        console.print(f"[yellow]{_UNAUTHENTICATED_SYNC_NOW_MESSAGE}[/yellow]")
        if strict:
            raise typer.Exit(1)
        return

    # Pending work but nothing was even attempted → teamspace-aware recovery.
    work_present = queue_size > 0 or selected > 0
    if work_present and progressed == 0:
        _handle_sync_now_unauthenticated(strict)
        return
    if strict and summary is not None and summary.terminal_failed > 0:
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
    )


def _batch_left_selection_set(summary: DispatchSummary) -> bool:
    terminal = summary.delivered + summary.duplicate + summary.terminal_failed
    return summary.selected > terminal


def _run_dispatch_batches(
    runtime: _EventSyncRuntime,
    receiver: DeliveryReceiver,
    delivery_target: Any,
) -> DispatchSummary:
    from specify_cli.delivery.dispatcher import DispatchSummary, dispatch

    combined = DispatchSummary.empty()
    while True:
        batch = dispatch(
            journal=runtime.journal,
            ledger=runtime.ledger,
            receiver=receiver,
            target=delivery_target,
            limit=_EVENT_SYNC_DISPATCH_BATCH_LIMIT,
        )
        combined = _combine_dispatch_summaries(combined, batch)
        if batch.selected < _EVENT_SYNC_DISPATCH_BATCH_LIMIT:
            break
        if _batch_left_selection_set(batch):
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
    from specify_cli.delivery.receivers import evaluate_gates

    runtime: _EventSyncRuntime | None = None
    try:
        runtime = _open_event_sync_runtime()
        config = _load_event_sync_config()
        auth_token = _event_sync_access_token()
        receiver = _resolve_active_receiver(runtime.target, config, auth_token=auth_token)
        if receiver is None:
            console.print(
                f"[dim]Event sync mode {config.mode.name}: retention only; "
                f"no delivery attempted.[/dim]"
            )
            return DispatchSummary.empty()
        gate_decision = evaluate_gates(
            receiver,
            _event_sync_gate_context(receiver, runtime.target, auth_token=auth_token),
        )
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

    _require_daemon_owner_coherence("spec-kitty sync opt-in")

    if not is_saas_sync_enabled():
        # Non-green + non-zero (#2264 item 3): opt-in cannot take effect while
        # the rollout flag is off, so a dim exit-0 "success" is misleading.
        # Surface the disabled state clearly and exit non-zero.
        console.print(f"[yellow]{saas_sync_disabled_message()}[/yellow]")
        raise typer.Exit(1)

    enforce_teamspace_mission_state_ready(
        console=console,
        command_name="spec-kitty sync opt-in",
    )

    routing = _require_active_checkout()
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


@app.command()
def migrate() -> None:
    """Migrate legacy hash-scoped queue DBs into the append-only event journal.

    Lifts every currently-queued payload from the legacy ``queue.db`` and each
    scoped ``queues/queue-<digest>.db`` into the WP03 event journal, recording
    per-source provenance and quarantining divergent-duplicate collisions into
    the migration-audit store. Source DBs are opened read-only and are never
    modified. Exits non-zero when an unresolved conflict blocks cleanup (SC-011).

    Examples:
        spec-kitty sync migrate
    """
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.migrate_journal import (
        AUDIT_DB_NAME,
        MigrationAudit,
        migrate_queues_to_journal,
    )

    spec_kitty_dir = get_runtime_root().base
    runtime = _open_event_sync_runtime()
    audit = MigrationAudit(spec_kitty_dir / AUDIT_DB_NAME)
    try:
        result = migrate_queues_to_journal(
            spec_kitty_dir,
            journal=runtime.journal,
            audit=audit,
            resolved_target=runtime.target,
        )
    finally:
        with contextlib.suppress(Exception):
            audit.close()
        runtime.close()
    _print_migration_result(result)
    if result.exit_code != 0:
        raise typer.Exit(result.exit_code)


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
            parsed_sync_time = datetime.fromisoformat(daemon_status.last_sync)
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
    from datetime import datetime

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

        now = datetime.now(UTC)

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
