"""Render adapter for the ``spec-kitty sync`` command surface (WP04).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``)
relocates the Console-emit + ``--json``-envelope family off the single
``cli/commands/sync.py`` host into this cohesive seam module, behind the reused
:class:`~specify_cli.agent_tasks_ports.Render` port (one adapter per port,
``DIRECTIVE_044`` — the shared port home is
:mod:`specify_cli.agent_tasks_ports`). This is a **pure
move**: every markup token, glyph, and ``json.dumps`` separator is byte-identical
to the inline form it replaces (INV-1). The WP02 golden + the ~60 patch-tests are
the guard.

**Late-bound host access (INV-4 / WP03 convention).** A relocated shell that must
call a monkeypatched ``sync`` seam callee — or reach a shared host helper/constant
that deliberately stays on the host (``_depth_color`` / ``humanize_timedelta`` /
``_render_daemon_team_or_user`` / the per-project-store compute helpers) — reaches
it by ATTRIBUTE ACCESS on the host module object
(``sync_module.<name>``), never by an early-bound
``from ...cli.commands.sync import <name>``. The ``import ... as sync_module`` is
kept FUNCTION-LOCAL so this module has no import-time dependency on the host
(the host imports THIS module from its husk re-export block, so a module-level
back-import would be circular). ``tests/architectural/test_sync_no_early_bind.py``
is the AST guard that fails any early-bind of a seam name.

The ``console`` singleton is imported directly from its stable home
(:mod:`specify_cli.cli.console`) — it is the SAME object the host prints to, so
``console.print`` here is byte-identical to ``console.print`` there.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.console import console
from specify_cli.sync.queue import QueueStats

if TYPE_CHECKING:
    from specify_cli.cli.commands.sync import _EventSyncRuntime
    from specify_cli.delivery.retention import RetentionResult
    from specify_cli.sync.migrate_journal import (
        CleanupResult,
        ConflictResolution,
        MigrationResult,
    )
    from specify_cli.sync.project_identity import IdentityBackfillResult

_LOG = logging.getLogger(__name__)


_DRAIN_BLOCKED_HELP = {
    "ready": "Ready to drain.",
    "saas_disabled": "SaaS sync disabled for this checkout — run `spec-kitty sync opt-in`.",
    "missing_auth": "Not authenticated — run `spec-kitty auth login`.",
    "missing_team": "No Private Teamspace available — refresh membership in dashboard.",
}


def _build_queue_summary_lines(stats: QueueStats) -> list[str]:
    """Build the queue-health summary lines shown in the panel."""
    import specify_cli.cli.commands.sync as sync_module

    summary_lines: list[str] = []
    pct = (stats.total_queued / stats.max_queue_size * 100) if stats.max_queue_size > 0 else 0
    depth_color = sync_module._depth_color(pct)
    summary_lines.append(f"[bold]Queue Depth:[/bold] [{depth_color}]{stats.total_queued:,} / {stats.max_queue_size:,}[/{depth_color}] ({pct:.0f}%)")
    summary_lines.append(f"[bold]Retried:[/bold]    {stats.total_retried:,}")
    if stats.oldest_event_age is not None:
        age_str = sync_module.humanize_timedelta(stats.oldest_event_age)
        summary_lines.append(f"[bold]Oldest Event:[/bold] {age_str} ago")

    if stats.drain_blocked_counts:
        ready = stats.drain_blocked_counts.get("ready", 0)
        blocked = stats.total_queued - ready
        ready_color = "green" if blocked == 0 else "yellow"
        summary_lines.append(f"[bold]Drain Ready:[/bold] [{ready_color}]{ready:,} ready[/{ready_color}] / [yellow]{blocked:,} blocked[/yellow]")
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
            "[yellow]Cleanup blocked[/yellow]: unresolved migration conflicts or source read/import errors remain — resolve them before deleting source queues."
        )
    for source in result.sources:
        if source.error:
            console.print(f"[red]Source {source.digest} failed[/red]: {source.error}")
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
            console.print(f"[red]Cleanup error on source {outcome.digest}[/red]: {outcome.error}")


def _print_resolution_result(resolution: ConflictResolution) -> None:
    """Render keep-journal conflict resolution (#2665)."""
    console.print(
        "Conflict resolution (keep-journal): "
        f"[green]resolved {resolution.resolved_count}[/green] (archived to quarantine)  "
        f"[yellow]skipped {len(resolution.skipped)}[/yellow]  "
        f"already-absent {len(resolution.already_absent)}"
    )
    if resolution.skipped:
        console.print("[yellow]Skipped conflicts are not yet canonical in the journal or their source is gone — left intact.[/yellow]")


def _render_event_sync_status(target_console: Console) -> None:
    """Surface the active mode + a compact event-sync summary in ``sync status``.

    Read-only and best-effort: a failure here must never break ``sync status``.
    """
    import specify_cli.cli.commands.sync as sync_module

    config = sync_module._load_event_sync_config()
    target_console.print("[bold]Event Sync[/bold]")
    target_console.print(f"  Mode                      {config.mode.name}")
    runtime: _EventSyncRuntime | None = None
    try:
        runtime = sync_module._open_event_sync_runtime_readonly()
        report = sync_module._event_sync_report({}, runtime)
    except Exception as exc:  # read-only summary; never fail status rendering
        _LOG.debug("event-sync status summary unavailable: %s", exc)
        return
    finally:
        if runtime is not None:
            runtime.close()
    journal_section = report["event_journal"]
    ledger_section = report["delivery_ledger"]
    failures_section = report["terminal_failures"]
    target_console.print(f"  Retained events           {journal_section['retained_event_count']}")
    target_console.print(f"  Delivered (cur/prev)      {ledger_section['delivered_current_target']}/{ledger_section['delivered_previous_target']}")
    target_console.print(f"  Terminal failures         {failures_section['count']}")
    if journal_section.get("gc_suggested"):
        target_console.print("  [yellow]GC suggested[/yellow]: run `spec-kitty sync gc`")


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

    WP07: split compute. The ``issues``-mutation half (``_per_project_store_issues``
    and the open/group compute) is the pure compute core WP07 extracts to
    ``sync_store_report_core``; it deliberately stays reachable on the host via
    ``sync_module`` here so this WP04 move is render-mechanics only (Pd-2).
    """
    import specify_cli.cli.commands.sync as sync_module
    from specify_cli.delivery.status_report import build_per_project_store_report

    try:
        journal = sync_module._open_journal_readonly()
    except FileNotFoundError as exc:
        # The one benign absence: no journal file has ever been created for this
        # producer scope, so there is genuinely nothing to group. Still printed,
        # because "no journal yet" and "I could not look" must not read alike.
        console_out.print(f"\n[bold]{sync_module._PER_PROJECT_SECTION_TITLE}[/bold]")
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
    finally:
        close = getattr(journal, "close", None)
        if callable(close):
            close()

    console_out.print(f"\n[bold]{sync_module._PER_PROJECT_SECTION_TITLE}[/bold]")
    if report.rows:
        console_out.print(sync_module._per_project_store_table(report))
    else:
        # Asserted-empty, not silently-empty: this line is the difference between
        # a journal that holds nothing and a report that never ran.
        console_out.print(f"  [green]no events retained[/green] [dim](journal count {report.retained_event_count})[/dim]")
    # Unconditionally, including on the empty branch. A journal that cannot answer
    # count() reports -1, which does not reconcile against zero rows — so returning
    # early on `not report.rows` would have rendered an unreadable journal as "no
    # events retained". That is the same three-states-look-alike failure the
    # docstring above is about, one branch further in.
    issues.extend(sync_module._per_project_store_issues(report))


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
    console.print(f"Journal identity: recovered {result.updated}  [dim]unresolvable {result.unresolved}[/dim]")
    if result.unresolved:
        # Not an error, and deliberately not phrased as one: these rows are
        # fail-closed by design (FR-011). What matters is that they are visible.
        console.print(
            f"  [dim]{result.unresolved} row(s) carry no resolvable project "
            "identity in their stored payload; they stay unselectable rather than "
            "being assigned one.[/dim]"
        )


def _emit_project_store_migration_json(payload: object) -> None:
    """Emit one unstyled machine-readable migration value."""
    import json
    import sys

    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    sys.stdout.write("\n")


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

    import specify_cli.cli.commands.sync as sync_module
    from specify_cli.sync.daemon import scan_sync_daemons
    from specify_cli.sync.preflight import build_boundary_failure_set
    from specify_cli.sync.queue import _legacy_queue_db_path

    failure_set = build_boundary_failure_set(repo_root=Path.cwd())
    fg = failure_set.foreground
    record = failure_set.daemon_record

    # Live orphan daemon scan (#1071 failure mode): the on-disk owner-record
    # detection already feeds ``failure_set.orphan_records``; we also probe
    # live processes so an unregistered ``run_sync_daemon`` running outside
    # the singleton fails ``--check`` even when on-disk state is clean.
    daemon_scan_diagnostic: str | None = None
    try:
        live_orphan_report = scan_sync_daemons()
    except Exception as exc:
        live_orphan_report = None
        daemon_scan_diagnostic = f"live daemon scan failed: {str(exc)[:200]}"
    live_orphan_count = int(live_orphan_report.orphan_count) if live_orphan_report is not None else 0

    # FR-004 / contracts/sync-status-output.md: when
    # ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` is set but no authenticated
    # identity is available, the gate exits 2 with ``ok=false`` and the
    # auth-absent reason surfaced in the JSON body. ``auth_required``
    # is True iff the SaaS-sync feature flag is enabled.
    auth_required = sync_module.is_saas_sync_enabled()
    auth_present = fg.server_url is not None and fg.team_or_user is not None

    # Canonical project-store counts are filled from the additive report below.
    # Zero is the honest fallback when the project store is unavailable.
    active_event_count = 0
    active_body_count = 0

    ok = failure_set.ok and (auth_present or not auth_required) and live_orphan_count == 0 and daemon_scan_diagnostic is None
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
        "daemon_scan_diagnostic": daemon_scan_diagnostic,
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
            "source_path": (record.source_checkout_path if record is not None else None),
            "server_url": record.server_url if record is not None else None,
            "team_or_user": (sync_module._render_daemon_team_or_user(record) if record is not None else None),
            "queue_db_path": record.queue_db_path if record is not None else None,
        },
        "active_queue": {
            "path": str(fg.queue_db_path),
            "event_count": active_event_count,
            "body_upload_count": active_body_count,
            "available": failure_set.project_store_diagnostic is None,
            "diagnostic": failure_set.project_store_diagnostic,
        },
        "project_store_diagnostic": failure_set.project_store_diagnostic,
        "legacy_queue": {
            "path": str(_legacy_queue_db_path()),
            "event_count": failure_set.legacy_event_rows,
            "body_upload_count": failure_set.legacy_body_upload_rows,
            "rows_in_scope": failure_set.legacy_rows_for_scope,
            "live_authority": False,
            "inspected": False,
            "diagnostic": ("legacy residue is WP10 migration/quarantine evidence; these compatibility counts are not a physical legacy-store census"),
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
                "team_or_user": sync_module._render_daemon_team_or_user(r),
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
        runtime = sync_module._open_event_sync_runtime_readonly()
        payload = sync_module._event_sync_report(payload, runtime)
        payload["active_queue"]["path"] = str(runtime.store.database_path)
        payload["active_queue"]["event_count"] = int(payload["event_journal"]["retained_event_count"])
        payload["active_queue"]["body_upload_count"] = int(payload["body_upload_compatibility"]["body_upload_queue_count"])
    except Exception as exc:  # additive shape survives; authority fails closed
        from specify_cli.delivery.status_report import default_status_sections

        _LOG.debug("event-sync status sections unavailable: %s", exc)
        payload = {**payload, **default_status_sections()}
        payload["event_sync_status_error"] = str(exc)[:200]
        payload["project_store_diagnostic"] = "project-store status read failed: " + str(exc)[:200]
        payload["active_queue"]["available"] = False
        payload["active_queue"]["diagnostic"] = payload["project_store_diagnostic"]
        payload["ok"] = False
        payload["exit_code"] = 2
        ok = False
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
