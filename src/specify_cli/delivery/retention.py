"""Explicit GC/archive payload retention (WP11, IC-08; FR-010, contract §3).

These are the **only** destructive payload operations in the event-sync domain
and they run **exclusively under explicit operator action** — the WP12
``sync archive`` / ``sync gc`` commands call them. They are deliberately *not*
wired into ``sync now`` or the dispatcher, so a normal capture+deliver cycle
never deletes a source payload (US4 acceptance scenario 3).

Both operations mutate only journal payload state and **never touch the delivery
ledger**, so the per-event/per-target delivery history and provenance is always
preserved (**FR-010**, contract §3: "``sync gc``/``sync archive`` are the only
destructive payload operations and preserve delivery history/provenance").

* :func:`archive_payloads` is non-destructive: it stamps the journal's archived
  marker through the WP03 public :meth:`EventJournal.mark_archived`, moving
  events off the live "retained" growth surface without deleting bytes. It is
  idempotent — an already-archived event is skipped.
* :func:`gc_payloads` is destructive: it purges (deletes) journal payload rows,
  but **only** for events already delivered to **all known targets**
  (:meth:`SqliteDeliveryLedger.delivered_to_target` for every known target id).
  An event still owed to any not-yet-delivered target is skipped so its payload
  — the only durable copy re-drainable to that target (FR-005) — is never
  silently erased. When no known targets are supplied the operation purges
  nothing (it cannot establish full delivery), and the ledger rows always
  survive.

Per **C-001** this module consumes the WP03 journal + WP05 ledger public
surfaces. The destructive purge writes the journal store directly using the
journal's *own* canonical schema identifiers (:mod:`specify_cli.event_journal.models`)
rather than re-deriving the table name — this module is the sanctioned
destructive owner the journal explicitly defers ``gc``/``archive`` to.

Third store, added by #3030 T026
--------------------------------
:func:`purge_project_body_uploads` extends the same ownership to the **body-upload
queue**. FR-016's ``sync purge --project X`` spans the journal and the delivery
ledger; the body queue is a *third* store holding X's data — and it is the one that
holds verbatim ``spec.md`` / ``plan.md`` / ``tasks/WP*.md`` text, not envelopes. It
lives in the offline-queue DB file (``OfflineBodyUploadQueue(db_path=OfflineQueue().db_path)``),
which a journal+ledger purge never opens, so a purge that omitted it would report
"100% of X removed" while X's documents stayed queued for the next drain — a false
remediation attestation on the exact artefacts the incident leaked.

**WP08 must call it.** NFR-006 ("after purging project X, a differential row count
over all other projects is zero") is only honest if the count covers every store the
project has rows in; :attr:`BodyQueuePurgeResult.other_project_differential` is that
number for this one.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.delivery.ledger import LEDGER_TABLE
from specify_cli.event_journal.models import COL_EVENT_ID, TABLE_NAME

if TYPE_CHECKING:
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.event_journal import EventJournal

# Built from the journal's own canonical identifiers; ``event_id`` always travels
# via a ``?`` placeholder, so there is no dynamic SQL and no injection surface
# (mirrors the static-identifier pattern in ``event_journal/models.py``).
_PURGE_SQL = f"DELETE FROM {TABLE_NAME} WHERE {COL_EVENT_ID} = ?"  # noqa: S608 — static module-constant identifiers; value via ?


@dataclass(frozen=True)
class RetentionResult:
    """Observable outcome of one explicit retention operation (NFR-001).

    ``archived`` / ``purged`` / ``skipped`` carry the affected event ids so WP12
    can print and tests can assert on observable results. The journal payload
    size before/after is always recorded so the bounded-growth surface stays
    visible even for an explicit operation (NFR-004).
    """

    operation: str
    archived: tuple[str, ...] = ()
    purged: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    journal_size_bytes_before: int = 0
    journal_size_bytes_after: int = 0

    @property
    def archived_count(self) -> int:
        return len(self.archived)

    @property
    def purged_count(self) -> int:
        return len(self.purged)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def _retained_payload_bytes(journal: EventJournal) -> int:
    """Live (non-archived) payload volume — the bounded-growth surface."""
    return sum(len(event.payload) for event in journal.read_all() if event.archived_at is None)


def _total_payload_bytes(journal: EventJournal) -> int:
    """Total stored payload volume (all rows) — what GC can reclaim."""
    return sum(len(event.payload) for event in journal.read_all())


def _candidate_ids(journal: EventJournal, event_ids: Sequence[str] | None, *, live_only: bool) -> list[str]:
    """Resolve the operation's candidate event ids (explicit list, or scan)."""
    if event_ids is not None:
        return list(event_ids)
    events = journal.read_all()
    if live_only:
        return [event.event_id for event in events if event.archived_at is None]
    return [event.event_id for event in events]


def archive_payloads(journal: EventJournal, *, event_ids: Sequence[str] | None = None, at: str | None = None) -> RetentionResult:
    """Archive payloads — stamp the journal marker, delete nothing (FR-010).

    Marks each still-live candidate event archived via the WP03 public
    :meth:`EventJournal.mark_archived`. Already-archived or missing events are
    skipped, so the operation is idempotent. The delivery ledger is untouched.
    When *event_ids* is omitted, every currently-retained event is archived.
    """
    timestamp = at or now_utc_iso()
    before = _retained_payload_bytes(journal)
    archived: list[str] = []
    skipped: list[str] = []
    for event_id in _candidate_ids(journal, event_ids, live_only=True):
        stored = journal.read_by_id(event_id)
        if stored is None or stored.archived_at is not None:
            skipped.append(event_id)
            continue
        journal.mark_archived(event_id, timestamp)
        archived.append(event_id)
    return RetentionResult(
        "archive",
        archived=tuple(archived),
        skipped=tuple(skipped),
        journal_size_bytes_before=before,
        journal_size_bytes_after=_retained_payload_bytes(journal),
    )


def _delivered_to_all_known_targets(
    ledger: SqliteDeliveryLedger,
    event_id: str,
    known_target_ids: Sequence[str] | None,
) -> bool:
    """Whether *event_id* reached **every** known target (the purge predicate).

    Returns ``False`` (purge-nothing safe default) when *known_target_ids* is
    falsy/empty: with no target universe the operation cannot establish full
    delivery, so it must not erase a payload that may still be owed to an
    unknown target. Otherwise the event must have a terminal-success delivery to
    every known target before its payload can be reclaimed (FR-005).
    """
    if not known_target_ids:
        return False
    return all(ledger.delivered_to_target(event_id, target_id) for target_id in known_target_ids)


def gc_payloads(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    *,
    event_ids: Sequence[str] | None = None,
    known_target_ids: Sequence[str] | None = None,
) -> RetentionResult:
    """Purge fully-delivered payloads, preserve re-drainable durability + ledger (FR-010).

    Deletes the journal payload row for each candidate event **only** once it has
    a terminal-success delivery to every id in *known_target_ids*
    (:meth:`SqliteDeliveryLedger.delivered_to_target`). An event still owed to any
    not-yet-delivered known target is skipped — its payload is the only durable
    copy re-drainable to that target and must not be erased silently (FR-005). A
    missing event is likewise skipped. When *known_target_ids* is falsy/empty the
    operation purges nothing (it cannot establish full delivery — a safe default
    so existing callers degrade to purge-nothing). The delivery ledger is never
    touched, so history/provenance survives the purge. When *event_ids* is
    omitted, every stored event (live or archived) is a candidate.
    """
    before = _total_payload_bytes(journal)
    purged: list[str] = []
    skipped: list[str] = []
    for event_id in _candidate_ids(journal, event_ids, live_only=False):
        stored = journal.read_by_id(event_id)
        if stored is None or not _delivered_to_all_known_targets(ledger, event_id, known_target_ids):
            skipped.append(event_id)
            continue
        purged.append(event_id)
    _purge_journal_rows(journal.db_path, purged)
    return RetentionResult(
        "gc",
        purged=tuple(purged),
        skipped=tuple(skipped),
        journal_size_bytes_before=before,
        journal_size_bytes_after=_total_payload_bytes(journal),
    )


class BodyUploadPurgeTarget(Protocol):
    """The two body-queue operations a project purge needs (#3030 T026).

    A structural type rather than an import of ``sync.body_queue``: ``delivery/``
    stays free of a hard dependency on the sync package, the same way
    ``delivery/selection.py`` keeps ``sync.consent`` behind a call-time import and a
    ``ConsentPredicate`` alias. The concrete implementation is
    :class:`specify_cli.sync.body_queue.OfflineBodyUploadQueue`.
    """

    def count_by_project(self) -> dict[str, int]: ...

    def remove_project_tasks(self, project_uuid: str) -> int: ...


@dataclass(frozen=True)
class BodyQueuePurgeResult:
    """Observable outcome of one project's body-queue purge (FR-016, NFR-006).

    Carries the **whole census** before and after, not just the target's count, so
    NFR-006's exactness claim is checkable from the result itself rather than
    re-derived by the caller (or by a report that could drift from what ran). A purge
    that reports success while some other project lost rows is the failure this
    record exists to make impossible to state.
    """

    project_uuid: str
    dry_run: bool
    removed: int
    before: Mapping[str, int] = field(default_factory=dict)
    after: Mapping[str, int] = field(default_factory=dict)

    @property
    def target_before(self) -> int:
        return self.before.get(self.project_uuid, 0)

    @property
    def target_after(self) -> int:
        return self.after.get(self.project_uuid, 0)

    @property
    def other_project_differential(self) -> int:
        """Total absolute row-count change across every **other** project.

        NFR-006 requires this to be ``0``. Absolute, and over the union of both
        censuses, so a project that *appeared* counts as a difference too — a purge
        must neither remove nor create another project's rows.
        """
        keys = (set(self.before) | set(self.after)) - {self.project_uuid}
        return sum(abs(self.after.get(key, 0) - self.before.get(key, 0)) for key in keys)

    @property
    def is_exact(self) -> bool:
        """100% of the target removed, 0% of anything else (SC-006)."""
        if self.dry_run:
            return self.target_after == self.target_before and self.other_project_differential == 0
        return self.target_after == 0 and self.other_project_differential == 0


def purge_project_body_uploads(
    project_uuid: str,
    *,
    body_queue: BodyUploadPurgeTarget | None = None,
    dry_run: bool = True,
) -> BodyQueuePurgeResult:
    """Remove *project_uuid*'s queued document bodies — the third purge store (T026).

    Dry-run by **default**, matching FR-016's ``sync purge`` contract: the census is
    still taken, so a dry run reports exactly what a real run would remove without
    removing it. That is the whole point of a dry run on a destructive operation over
    confidential text.

    A blank *project_uuid* removes nothing and is reported as such. Rows whose own
    ``project_uuid`` is blank are grouped under ``""`` by
    :meth:`~specify_cli.sync.body_queue.OfflineBodyUploadQueue.count_by_project` and
    are therefore visible in the census but not purgeable by project — deliberately:
    they cannot be attributed to a project, and deleting unattributable confidential
    text under another project's purge would be a silent overreach. ``sync purge
    --all`` (FR-017) is where they belong.

    *body_queue* defaults to the real queue over the shared offline-queue DB file,
    resolved at call time so ``delivery/`` keeps no import-time dependency on
    ``sync/``.
    """
    queue = body_queue if body_queue is not None else _default_body_queue()
    target = str(project_uuid or "").strip()

    before = dict(queue.count_by_project())
    removed = 0 if (dry_run or not target) else int(queue.remove_project_tasks(target))
    # Re-read even on a dry run rather than copying ``before``. Asserting "nothing
    # changed" is exactly the claim a dry run is supposed to *earn*, and this is the
    # only place a dry run that quietly mutated could still be caught.
    after = dict(queue.count_by_project())

    return BodyQueuePurgeResult(
        project_uuid=target,
        dry_run=dry_run,
        removed=removed,
        before=before,
        after=after,
    )


#: Census key for rows whose ``project_uuid`` is NULL. Mirrors the body-queue
#: census convention (``count_by_project`` groups blank identity under ``""``), so
#: one purge report can present all three stores without a per-store special case.
IDENTITY_LESS_KEY = ""

_LEDGER_STATUS_CENSUS_SQL = f"SELECT status, COUNT(*) FROM {LEDGER_TABLE} GROUP BY status"  # noqa: S608 — static module-constant identifier
_LEDGER_TOTAL_SQL = f"SELECT COUNT(*) FROM {LEDGER_TABLE}"  # noqa: S608 — static module-constant identifier


@dataclass(frozen=True)
class ProjectPurgeResult:
    """Observable outcome of one purge across the journal and the delivery ledger.

    Carries whole **censuses** rather than only the target's numbers, for the same
    reason :class:`BodyQueuePurgeResult` does: NFR-006 is a differential ("0% of any
    other project's rows"), and a result that reports only what it removed cannot
    substantiate that claim. ``ledger_status_before`` is additionally the *forensic*
    record — how many of the project's events had been delivered, rejected or never
    attempted — because the purge removes those rows (see
    :func:`purge_project_events`).
    """

    selector: str
    dry_run: bool
    undelivered_only: bool
    purged_event_ids: tuple[str, ...] = ()
    ledger_rows_removed: int = 0
    journal_before: Mapping[str, int] = field(default_factory=dict)
    journal_after: Mapping[str, int] = field(default_factory=dict)
    ledger_status_before: Mapping[str, int] = field(default_factory=dict)
    ledger_status_after: Mapping[str, int] = field(default_factory=dict)
    ledger_total_before: int = 0
    ledger_total_after: int = 0

    @property
    def target_before(self) -> int:
        return self.journal_before.get(self.selector, 0)

    @property
    def target_after(self) -> int:
        return self.journal_after.get(self.selector, 0)

    @property
    def purged_count(self) -> int:
        return len(self.purged_event_ids)

    @property
    def ledger_rows_selected(self) -> int:
        """Ledger rows the selection covers — what a real run *would* remove.

        Distinct from :attr:`ledger_rows_removed`, which is ``0`` on a dry run
        because a dry run removes nothing. A preview that could only report ``0``
        would tell the operator nothing about the ledger half of the purge.
        """
        return sum(self.ledger_status_before.values())

    @property
    def never_attempted(self) -> int:
        """Selected events with no ledger row at all — never even attempted.

        Part of the forensic breakdown: ``ledger_status_before`` accounts for the
        events that reached a delivery attempt, and this is the remainder.
        """
        return max(self.purged_count - sum(self.ledger_status_before.values()), 0)

    @property
    def other_project_journal_differential(self) -> int:
        """Absolute journal row-count change across every key that is not the target.

        Over the union of both censuses, so a project that *appeared* counts as a
        difference too — a purge must neither remove nor create another project's
        rows. NFR-006 requires ``0``.
        """
        keys = (set(self.journal_before) | set(self.journal_after)) - {self.selector}
        return sum(
            abs(self.journal_after.get(key, 0) - self.journal_before.get(key, 0))
            for key in keys
        )

    @property
    def other_ledger_differential(self) -> int:
        """Ledger rows lost or gained that were **not** the target's.

        The ledger is keyed ``(event_id, target_id)`` and carries no project column,
        so "another project's ledger rows" is not directly countable. It is derivable
        exactly: total change minus the change this purge accounts for. NFR-006
        requires ``0``.
        """
        total_change = self.ledger_total_before - self.ledger_total_after
        return abs(total_change - self.ledger_rows_removed)

    @property
    def is_exact(self) -> bool:
        """Everything selected went, nothing else moved (SC-006 / NFR-006)."""
        expected_after = self.target_before if self.dry_run else self.target_before - self.purged_count
        return (
            self.target_after == expected_after
            and self.other_project_journal_differential == 0
            and self.other_ledger_differential == 0
        )


def _journal_census(journal: EventJournal) -> dict[str, int]:
    """Per-project journal row counts, with identity-less rows under ``""``.

    Composed from the journal's public identity reads (``distinct_project_uuids`` +
    the filtered projection + ``count_missing_identity``) rather than a GROUP BY of
    our own: the destructive write below is this module's sanctioned business, but a
    *census* has a public API and should not grow a second definition of "which
    projects does the store hold".
    """
    census: dict[str, int] = {}
    for uuid in journal.distinct_project_uuids():
        census[uuid] = len(journal.read_identity_projection(project_uuids=[uuid]))
    missing = journal.count_missing_identity()
    if missing:
        census[IDENTITY_LESS_KEY] = missing
    return census


def _ledger_status_census(
    ledger: SqliteDeliveryLedger, event_ids: Sequence[str]
) -> dict[str, int]:
    """Per-status ledger counts restricted to *event_ids* (the forensic breakdown)."""
    census: dict[str, int] = {}
    for event_id in event_ids:
        for row in ledger.connection.execute(
            f"SELECT status FROM {LEDGER_TABLE} WHERE {COL_EVENT_ID} = ?",  # noqa: S608 — static module-constant identifiers
            (event_id,),
        ):
            status = str(row["status"])
            census[status] = census.get(status, 0) + 1
    return census


def _ledger_total(ledger: SqliteDeliveryLedger) -> int:
    row = ledger.connection.execute(_LEDGER_TOTAL_SQL).fetchone()
    return int(row[0]) if row else 0


def _purge_ledger_rows(ledger: SqliteDeliveryLedger, event_ids: Sequence[str]) -> int:
    """Delete every ledger row for *event_ids*, across all targets. Returns the count."""
    if not event_ids:
        return 0
    removed = 0
    with ledger.transaction():
        for event_id in event_ids:
            cursor = ledger.connection.execute(
                f"DELETE FROM {LEDGER_TABLE} WHERE {COL_EVENT_ID} = ?",  # noqa: S608 — static module-constant identifiers
                (event_id,),
            )
            removed += max(int(cursor.rowcount), 0)
    return removed


def _purge(
    *,
    selector: str,
    event_ids: Sequence[str],
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    dry_run: bool,
    undelivered_only: bool,
) -> ProjectPurgeResult:
    """Shared core: census, (optionally) delete both stores, census again."""
    if undelivered_only:
        event_ids = [
            event_id for event_id in event_ids if not ledger.delivered_anywhere(event_id)
        ]

    journal_before = _journal_census(journal)
    ledger_status_before = _ledger_status_census(ledger, event_ids)
    ledger_total_before = _ledger_total(ledger)

    ledger_rows_removed = 0
    if not dry_run and event_ids:
        # Ledger first: a journal row without its ledger rows is merely undelivered
        # (and unselectable, since it is gone from the universe on the next read),
        # whereas a ledger row without its journal row is an unresolvable orphan. If
        # the process dies between the two, the recoverable ordering is this one.
        ledger_rows_removed = _purge_ledger_rows(ledger, event_ids)
        _purge_journal_rows(journal.db_path, event_ids)

    # Re-read both stores even on a dry run. "Nothing changed" is precisely the
    # claim a dry run has to earn, and this is the only place a dry run that
    # quietly mutated could still be caught.
    return ProjectPurgeResult(
        selector=selector,
        dry_run=dry_run,
        undelivered_only=undelivered_only,
        purged_event_ids=tuple(event_ids),
        ledger_rows_removed=ledger_rows_removed,
        journal_before=journal_before,
        journal_after=_journal_census(journal),
        ledger_status_before=ledger_status_before,
        ledger_status_after=_ledger_status_census(ledger, event_ids),
        ledger_total_before=ledger_total_before,
        ledger_total_after=_ledger_total(ledger),
    )


def purge_project_events(
    project_uuid: str,
    *,
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    dry_run: bool = True,
    undelivered_only: bool = False,
) -> ProjectPurgeResult:
    """Remove one project's rows from the journal **and** the delivery ledger (FR-016).

    Dry-run by **default**, at the primitive and not only at a future CLI: this
    deletes confidential payloads, and the per-state breakdown a dry run reports is
    the operator's only chance to record what was there.

    **Research decision 2 (ledger history): removed, not retained.** Three reasons.
    A ledger row that outlives its journal row is an orphan keyed to an event that
    no longer exists — permanently unresolvable, and it inflates every status count
    forever. Its ``last_error`` / ``last_response_json`` can quote the project it
    belongs to, so keeping it would make "100% of X removed" a false attestation of
    exactly the kind that omitting the body-upload store would have produced. And
    the forensic value it carries — *what happened* to those events — is preserved
    as :attr:`ProjectPurgeResult.ledger_status_before` plus
    :attr:`ProjectPurgeResult.never_attempted`, produced by the mandatory-by-default
    dry run *before* anything is deleted. The record moves from a durable row that
    names a purged project to the operator's purge report.

    **Identity-less rows are never matched here.** ``project_uuid IS NULL`` rows
    cannot be attributed to any project, so deleting them under a project's purge
    would be a silent overreach — the same call the body-queue purge makes. They are
    visible in :attr:`ProjectPurgeResult.journal_before` under
    :data:`IDENTITY_LESS_KEY` and are removable through
    :func:`purge_identity_less_events`.

    A blank *project_uuid* selects nothing: it must never degrade into "match every
    row". *undelivered_only* restricts the selection to events with no
    terminal-success delivery anywhere — the scope ``sync opt-out`` uses, which must
    not destroy the record of what already left the machine (C-002).
    """
    target = str(project_uuid or "").strip()
    event_ids = (
        [row.event_id for row in journal.read_identity_projection(project_uuids=[target])]
        if target
        else []
    )
    return _purge(
        selector=target,
        event_ids=event_ids,
        journal=journal,
        ledger=ledger,
        dry_run=dry_run,
        undelivered_only=undelivered_only,
    )


def purge_identity_less_events(
    *,
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    dry_run: bool = True,
) -> ProjectPurgeResult:
    """Remove rows whose project identity is unresolvable (FR-011's population).

    A real and permanent population: the backfill leaves a row NULL when the
    envelope carries no identity anywhere (C-002 forbids deleting it), the consent
    predicate then denies it forever, and FR-011 counts it so the denial is
    observable. Without a selector of their own those rows would be
    *observable but unremovable* — the operator would see a number they could do
    nothing about, which is why a uuid purge deliberately not matching them is only
    defensible alongside this function.

    Dry-run by default, same as :func:`purge_project_events`.
    """
    event_ids = [event_id for event_id, _payload in journal.iter_rows_missing_identity()]
    return _purge(
        selector=IDENTITY_LESS_KEY,
        event_ids=event_ids,
        journal=journal,
        ledger=ledger,
        dry_run=dry_run,
        undelivered_only=False,
    )


#: Layout of the live delivery store under the spec-kitty home. Duplicated from
#: ``cli/commands/sync.py``'s private ``_DELIVERY_SUBDIR`` / ``_LEDGER_DB_NAME``
#: **deliberately and temporarily**: non-CLI callers (``sync/routing.py``'s opt-out
#: purge) need the same path, and the CLI's copies are private to a module another
#: lane owns. ``tests/sync/test_routing.py`` asserts the two agree, so a drift is a
#: red rather than a purge quietly pointed at the wrong file. The CLI's lane should
#: collapse onto this one.
_DELIVERY_SUBDIR = "delivery"
_LEDGER_DB_NAME = "ledger.db"


def resolve_live_store_paths() -> tuple[Path, Path]:
    """Return ``(journal_path, ledger_path)`` for the store the drain actually reads.

    Resolved through the *same* public seams the dispatcher's runtime uses —
    :func:`~specify_cli.event_journal.journal.resolve_journal_path` under the live
    producer scope, and the delivery directory under the spec-kitty home — so a
    purge cannot end up pointed at a differently-scoped twin. That failure mode is
    silent by nature: a purge over an empty journal reports "0 removed", which is
    indistinguishable from "nothing to remove".

    Creates nothing. Callers decide whether an absent file means "no work" (opt-out)
    or an error (a diagnostic read).
    """
    from specify_cli.event_journal.journal import resolve_journal_path
    from specify_cli.paths import get_runtime_root

    journal_path = resolve_journal_path(user_id=None, team_slug=_live_team_slug())
    base: Path = get_runtime_root().base
    return journal_path, base / _DELIVERY_SUBDIR / _LEDGER_DB_NAME


def _live_team_slug() -> str | None:
    """The producer scope live capture writes under, or ``None`` if unresolvable."""
    try:
        from specify_cli.sync.emitter import EventEmitter

        return EventEmitter._current_team_slug()
    except Exception:  # noqa: BLE001 — scope is best-effort; None is the anonymous journal
        return None


def purge_project_events_from_live_stores(
    project_uuid: str,
    *,
    dry_run: bool = True,
    undelivered_only: bool = False,
) -> ProjectPurgeResult | None:
    """Run :func:`purge_project_events` against the live journal + ledger.

    Returns ``None`` when the journal does not exist yet: there is nothing to purge,
    and a routing toggle must not materialise an empty journal/ledger as a side
    effect of reporting zero. ``None`` is deliberately distinct from a result whose
    counts are zero — the caller can tell "no store" from "store, nothing matched".
    """
    journal_path, ledger_path = resolve_live_store_paths()
    if not journal_path.exists():
        return None

    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.event_journal.journal import EventJournal

    journal = EventJournal(journal_path)
    ledger = SqliteDeliveryLedger(str(ledger_path) if ledger_path.exists() else ":memory:")
    try:
        return purge_project_events(
            project_uuid,
            journal=journal,
            ledger=ledger,
            dry_run=dry_run,
            undelivered_only=undelivered_only,
        )
    finally:
        ledger.close()


def _default_body_queue() -> BodyUploadPurgeTarget:
    """The real body queue, on the DB file it shares with the event offline queue."""
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue
    from specify_cli.sync.queue import OfflineQueue

    return OfflineBodyUploadQueue(db_path=OfflineQueue().db_path)


def _purge_journal_rows(db_path: Path, event_ids: Sequence[str]) -> None:
    """Delete the named journal payload rows (the sole destructive write)."""
    if not event_ids:
        return
    connection: Any = sqlite3.connect(str(db_path))
    try:
        connection.executemany(_PURGE_SQL, [(event_id,) for event_id in event_ids])
        connection.commit()
    finally:
        connection.close()


# ``BodyQueuePurgeResult`` / ``purge_project_body_uploads`` / ``BodyUploadPurgeTarget``
# are deliberately NOT advertised yet. The symbol-level dead-code gate
# (``tests/architectural/test_no_dead_symbols.py``) is a shrink-only ratchet over
# ``__all__``, and WP08's ``sync purge`` command — the production caller — is not
# implemented. Advertising them now would either fail that gate or need an allowlist
# entry that outlives the reason for it. They stay importable; WP08 adds them here
# when it wires the CLI, which is also the moment the names stop being aspirational.
__all__ = [
    "RetentionResult",
    "archive_payloads",
    "gc_payloads",
]
