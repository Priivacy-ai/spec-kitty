"""Census readers + store executors for ``spec-kitty sync purge`` (WP06).

The **exec** half of the purge core/exec split (mission
``sync-cli-degod-wave4-01M0B0MX``, WP06). Everything here touches an I/O
boundary — the event journal, the delivery ledger, the body-upload queue, the
checkout-local ``sync-state.json`` frame file, or the operator ``Console`` — and
so it is deliberately kept **out** of the pure
:mod:`specify_cli.sync.sync_purge_core`, which owns the shared census/outcome
shapes and the differential/verdict arithmetic this module imports.

What lives here:

* **Census readers** — ``_purge_journal_census`` / ``_purge_ledger_census`` /
  ``_purge_body_census`` / ``_purge_frames_census`` (plus the id/ghost/selection
  helpers): the CLI's own raw reads of each store, taken independently of the
  purge primitives so the differential can disagree with what a purge reports
  (NFR-006).
* **Store executors** — ``_purge_run_journal_ledger`` / ``_purge_run_body_queue``:
  the thin adapters that invoke the ``delivery/retention.py`` purge primitives
  (selection and deletion stay there, C-003).
* **Refusals + resolution** — ``_purge_usage_error`` /
  ``_purge_validate_invocation`` / ``_purge_resolve_project``: the pre-open
  guards and the ``--project`` selector resolver, all of which report and exit
  through the ``Console`` / ``typer.Exit``.
* **Operator report** — ``_purge_print_verdict`` / ``_purge_render``: the
  ``Console`` emitters that print the plan, the residue and the verdict.

This is a **pure move** (INV-1): every body is byte-identical to the inline form
it replaced in ``cli/commands/sync.py``. The ``@app.command`` ``purge`` shell
stays on the host and reaches these as ``sync.<name>`` module attributes via the
husk re-export block. The WP02 golden + ``test_sync_purge_3030.py`` are the
guard. The total-purge primitives this module invokes
(``purge_all_events`` / ``purge_identity_less_events`` /
``purge_project_body_uploads``) keep their operator-attended-only reachability;
``test_no_unattended_caller_of_the_total_purge_primitives`` allowlists this
module for exactly that reason.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import typer
from rich.table import Table

from specify_cli.cli.console import console
from specify_cli.sync.sync_purge_core import (
    _PURGE_LEDGER,
    _PURGE_NON_ATOMIC_NOTE,
    _PURGE_NULL_KEY,
    _PURGE_STORE_LABELS,
    _PURGE_SYNC_STATE_RELPATH,
    _PurgeStoreOutcome,
    _RawCensus,
)

_LOG = logging.getLogger(__name__)

if TYPE_CHECKING:
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.delivery.retention import ProjectPurgeResult
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.identity.project import ProjectIdentity
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue


def _purge_usage_error(message: str) -> None:
    """Refuse before opening any store. Exit 2: nothing was read, nothing deleted."""
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(2)


def _purge_journal_census(journal: EventJournal) -> _RawCensus:
    """Independent identity projection over one explicit project journal.

    Not ``retention._journal_census``: that one composes ``distinct_project_uuids``
    with the identity projection, which *filters falsy uuids*, so a blank-uuid row
    reaches it only through a derived remainder. For a differential the CLI needs the
    stored values verbatim, blank and whitespace included, each as its own bucket.
    """
    try:
        by_key: dict[str, int] = {}
        rows = journal.read_identity_projection_for_report()
        for row in rows:
            key = _PURGE_NULL_KEY if row.project_uuid is None else str(row.project_uuid)
            by_key[key] = by_key.get(key, 0) + 1
        return _RawCensus(total=len(rows), by_key=by_key)
    except Exception:
        return _RawCensus(unreadable=True)


def _purge_journal_ids(journal: EventJournal, *, project_uuid: str | None, every_row: bool) -> list[str]:
    """The journal ids the selector covers, resolved by the CLI's own raw read.

    ``project_uuid=None`` means ``IS NULL`` (FR-011's population). Used only to
    *measure* the ledger half — the deletion still selects through the primitives.
    """
    try:
        rows = journal.read_identity_projection_for_report()
        return [
            str(row.event_id)
            for row in rows
            if every_row or (project_uuid is None and row.project_uuid is None) or (project_uuid is not None and row.project_uuid == project_uuid)
        ]
    except Exception:
        return []


def _purge_ledger_census(ledger: SqliteDeliveryLedger, event_ids: list[str]) -> _RawCensus:
    """``(total rows, rows for the selected ids)`` — the ledger has no project column.

    Bucketed under one synthetic key because "another project's ledger rows" is not
    directly countable: the ledger is keyed ``(event_id, target_id)``. The change
    outside the selection is therefore derived as *total change minus selected
    change*, from the CLI's own counts.
    """
    try:
        rows = ledger.rows()
        selected_ids = set(event_ids)
        selected = sum(row.event_id in selected_ids for row in rows)
        return _RawCensus(
            total=len(rows),
            by_key={_PURGE_LEDGER: selected},
        )
    except Exception:
        return _RawCensus(unreadable=True)


def _purge_ledger_ghost_count(journal: EventJournal, ledger: SqliteDeliveryLedger) -> int:
    """Ledger rows whose ``event_id`` has no journal row at all.

    Unreachable by any targeted selector, because every targeted selection collects
    its ids *from the journal*. Not a contrived state: ``sync gc`` deletes journal
    payload rows and preserves ledger history by design (FR-010), so every machine
    that has run it holds some. The two stores are separate SQLite files, so this is
    a set difference in Python rather than a join.
    """
    journal_ids = set(_purge_journal_ids(journal, project_uuid=None, every_row=True))
    try:
        return sum(row.event_id not in journal_ids for row in ledger.rows())
    except Exception:
        return 0


def _purge_body_census(queue: OfflineBodyUploadQueue | None) -> _RawCensus:
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



def _purge_resolve_project(
    value: str,
    journal: EventJournal,
    checkout_identity: ProjectIdentity | None,
) -> tuple[str, str | None]:
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

    for row in journal.read_identity_projection_for_report():
        _offer(row.repo_slug, row.project_uuid)
        _offer(row.project_slug, row.project_uuid)
    if checkout_identity is not None:
        _offer(checkout_identity.repo_slug, checkout_identity.project_uuid)
        _offer(checkout_identity.project_slug, checkout_identity.project_uuid)

    matches = sorted(candidates.get(raw.casefold(), set()))
    if not matches:
        known = ", ".join(sorted(candidates)) or "none recorded"
        _purge_usage_error(
            f'No project matches "{raw}". Names the active project journal or '
            "current checkout records "
            f"(repo slugs and project slugs alike): {known}. Pass the project uuid "
            "to purge a project whose rows carry no name."
        )
    if len(matches) > 1:
        _purge_usage_error(f'"{raw}" maps to {len(matches)} project uuids ({", ".join(matches)}); pass the uuid you mean — a purge must not span two projects.')
    return matches[0], raw


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
        _purge_usage_error("Choose exactly one of --project <slug-or-uuid>, --identity-less or --all.")
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
    journal: EventJournal,
    census: _RawCensus,
    *,
    all_events: bool,
    identity_less: bool,
    selector_uuid: str,
) -> tuple[frozenset[str], list[str]]:
    """``(census keys in scope, journal ids in scope)`` for this selector."""
    if all_events:
        return frozenset(census.by_key), _purge_journal_ids(journal, project_uuid=None, every_row=True)
    if identity_less:
        return frozenset({_PURGE_NULL_KEY}), _purge_journal_ids(journal, project_uuid=None, every_row=False)
    return frozenset({selector_uuid}), _purge_journal_ids(journal, project_uuid=selector_uuid, every_row=False)



def _purge_run_journal_ledger(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    *,
    all_events: bool,
    identity_less: bool,
    selector_uuid: str,
    dry_run: bool,
    confirm: str,
) -> ProjectPurgeResult | None:
    """Run the journal+ledger purge primitive for this selector, or ``None``.

    ``None`` when no journal exists: there is nothing to purge, and opening
    ``EventJournal`` would *create* the store — a purge that materialised a store in
    order to report zero rows in it would be reporting on its own side effect.
    """
    from specify_cli.delivery.retention import (
        PurgeNotConfirmedError,
        purge_all_events,
        purge_identity_less_events,
        purge_project_events,
    )

    try:
        if all_events:
            return purge_all_events(journal=journal, ledger=ledger, dry_run=dry_run, confirmation=confirm)
        if identity_less:
            return purge_identity_less_events(journal=journal, ledger=ledger, dry_run=dry_run)
        return purge_project_events(selector_uuid, journal=journal, ledger=ledger, dry_run=dry_run)
    except PurgeNotConfirmedError as exc:
        console.print(f"[red]Refused:[/red] {exc}")
        raise typer.Exit(1) from exc



def _purge_run_body_queue(
    body_queue: OfflineBodyUploadQueue,
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
        purge_project_body_uploads,
    )

    if not all_events:
        result = purge_project_body_uploads(selector_uuid, body_queue=body_queue, dry_run=dry_run)
        return frozenset({selector_uuid}), result.removed

    del confirm
    total = purge_project_body_uploads(
        body_queue.project_uuid,
        body_queue=body_queue,
        dry_run=dry_run,
    )
    return frozenset(census.by_key), total.removed



def _purge_print_verdict(faults: list[str], *, apply: bool, all_events: bool) -> None:
    """State what the measurements support, and never more than that."""
    if apply:
        console.print(f"\n[dim]{_PURGE_NON_ATOMIC_NOTE}[/dim]")
    if faults:
        console.print("\n[bold red]NFR-006 not satisfied[/bold red]")
        for fault in faults:
            console.print(f"  [red]•[/red] {fault}")
        return
    scope_claim = "nothing outside the scope named above changed" if all_events else "0 rows belonging to any other project changed"
    console.print(
        f"\n[green]Differential verified against the stores[/green] (measured by re-reading them, not by summing what the purge reported): {scope_claim}."
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
    removed_total = sum(outcome.removed_observed for outcome in outcomes.values())
    if dry_run:
        header = "[bold yellow]DRY RUN[/bold yellow] — no rows have been deleted"
    elif removed_total:
        header = "[bold red]APPLIED[/bold red] — rows have been deleted"
    else:
        header = "[bold red]APPLIED[/bold red] — no rows matched or were removed"
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
    console.print(f"Delivery state of the events in scope: {states or 'no delivery attempt recorded'}  never-attempted={ledger.never_attempted}")
    if dry_run:
        console.print("[dim]The ledger rows would be deleted by an applied run. Keep this preview (--report writes it as JSON).[/dim]")
    elif ledger.removed_observed:
        console.print("[dim]The ledger rows were deleted, so this breakdown is the only surviving record. Keep it (--report writes it as JSON).[/dim]")

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
