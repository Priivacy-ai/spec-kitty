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

:func:`purge_all_body_uploads` is FR-017's half of the same store, added once the
purge CLI measured that ``--all`` could not empty it: the queue's per-project removal
strips its argument, so a blank or padded ``project_uuid`` was reachable by no
selector at all. It is a separate selector rather than a widening of the per-project
one — see its docstring for the operator decision.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from kernel.clock import now_utc_iso
from specify_cli.delivery.ledger import LEDGER_TABLE
from specify_cli.event_journal.models import COL_EVENT_ID, TABLE_NAME

if TYPE_CHECKING:
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.event_journal import EventJournal
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue

# Built from the journal's own canonical identifiers; ``event_id`` always travels
# via a ``?`` placeholder, so there is no dynamic SQL and no injection surface
# (mirrors the static-identifier pattern in ``event_journal/models.py``).
_PURGE_SQL = f"DELETE FROM {TABLE_NAME} WHERE {COL_EVENT_ID} = ?"  # noqa: S608  # nosec B608 — static module-constant identifiers; value via ?

#: FR-017's own reads. ``--all`` cannot be assembled from the per-project selectors
#: (see :func:`purge_all_events` for the three populations they miss), so it takes the
#: id sets straight from both tables. Ids only — no payload BLOB is decoded, because
#: the whole store is about to be deleted and hydrating it first would be pointless
#: I/O over exactly the confidential text this operation exists to remove.
_ALL_JOURNAL_IDS_SQL = f"SELECT {COL_EVENT_ID} FROM {TABLE_NAME}"  # noqa: S608  # nosec B608 — static module-constant identifiers
_ALL_LEDGER_IDS_SQL = f"SELECT DISTINCT {COL_EVENT_ID} FROM {LEDGER_TABLE}"  # noqa: S608  # nosec B608 — static module-constant identifiers

#: The literal an operator must produce for a destructive ``--all`` run.
#:
#: A phrase and not a boolean, deliberately (**C-002**: deletion is only ever the
#: operator's explicit act). A ``confirm=True`` flag is one keyword away from any
#: unattended code path that already builds its kwargs dynamically; a sentence is not
#: something a scheduler, a retry loop or a default-argument mistake produces. This is
#: also exactly what a CLI prompt can echo back, so the store-level guard and the
#: operator-level guard are the same string rather than two representations of one
#: rule.
PURGE_ALL_CONFIRMATION = "purge all events"


class PurgeNotConfirmedError(RuntimeError):
    """A destructive ``--all`` purge was requested without the confirmation phrase.

    Raised rather than returning a zero-count result. A silent no-op is
    indistinguishable from "there was nothing to purge" — the reporting failure this
    mission keeps finding — and it would let a caller believe it had wiped a store it
    had not touched.
    """


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
    """Observable outcome of one body-queue purge (FR-016, FR-017, NFR-006).

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
    #: ``True`` for FR-017's total purge. A flag rather than a sentinel value in
    #: ``project_uuid``, for the reason :attr:`ProjectPurgeResult.all_events` records:
    #: any sentinel string could in principle collide with a stored ``project_uuid``,
    #: and a census key that sometimes means "one project" and sometimes means "all of
    #: them" is the ambiguity C-003 forbids.
    all_uploads: bool = False

    @property
    def target_before(self) -> int:
        if self.all_uploads:
            return sum(self.before.values())
        return self.before.get(self.project_uuid, 0)

    @property
    def target_after(self) -> int:
        if self.all_uploads:
            return sum(self.after.values())
        return self.after.get(self.project_uuid, 0)

    @property
    def other_project_differential(self) -> int:
        """Total absolute row-count change across every **other** project.

        NFR-006 requires this to be ``0``. Absolute, and over the union of both
        censuses, so a project that *appeared* counts as a difference too — a purge
        must neither remove nor create another project's rows.

        For a total purge (:attr:`all_uploads`) there is no "other": the scope is the
        whole store, so this is ``0`` by definition and carries no information. The
        load-bearing check for that case is ``target_after == 0``, asserted by
        :attr:`is_exact` — the same split :class:`ProjectPurgeResult` makes.
        """
        if self.all_uploads:
            return 0
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


class BodyUploadTotalPurgeTarget(Protocol):
    """What a **total** body-queue purge needs (#3030 FR-017).

    Deliberately not :class:`BodyUploadPurgeTarget` widened with a ``db_path``: the
    per-project purge deletes through the queue's own ``remove_project_tasks`` and has
    no business knowing where the store lives, while the total purge is a write this
    module owns (see :func:`purge_all_body_uploads`). Two different needs, stated
    separately, so neither function advertises a capability it does not use.
    """

    db_path: Path

    def count_by_project(self) -> dict[str, int]: ...


#: The body queue's own table, duplicated from ``sync/body_queue.py``'s schema on the
#: same reasoning ``_PURGE_SQL`` records for the journal: this module is the sanctioned
#: destructive owner and writes the store through its canonical identifier rather than
#: re-deriving one. ``tests/delivery/test_purge_all_body_uploads_3030.py`` pins it
#: against the table the live queue actually creates, so a rename there is a red rather
#: than a purge that silently deletes nothing.
_BODY_QUEUE_TABLE = "body_upload_queue"

#: FR-017's own delete over that store. No ``WHERE``, which is the entire point — see
#: :func:`purge_all_body_uploads` for why this cannot compose from the per-project
#: selector, and why widening that selector instead was rejected.
_PURGE_ALL_BODY_SQL = f"DELETE FROM {_BODY_QUEUE_TABLE}"  # noqa: S608  # nosec B608 — static module-constant identifier, no values interpolated


def _purge_all_body_rows(db_path: Path) -> int:
    """Delete every queued body row. Returns the count. The sole total-purge write.

    A missing DB file removes nothing and is not an error: the queue is created
    lazily, and materialising it in order to report zero rows in it would be
    reporting on this function's own side effect.

    Scoped to one table on purpose. The body queue shares its SQLite file with the
    event offline queue, so dropping the file (or the wrong table) would take a
    different store's rows with it — those are cleared through the journal/ledger
    primitives, under their own selector.
    """
    if not Path(db_path).exists():
        return 0
    connection: Any = sqlite3.connect(str(db_path))
    try:
        cursor = connection.execute(_PURGE_ALL_BODY_SQL)
        connection.commit()
        return max(int(cursor.rowcount), 0)
    finally:
        connection.close()


def purge_all_body_uploads(
    *,
    body_queue: BodyUploadTotalPurgeTarget | None = None,
    dry_run: bool = True,
    confirmation: str = "",
) -> BodyQueuePurgeResult:
    """Remove **every** queued document body — FR-017's fourth store.

    Dry-run by default; a destructive run additionally requires *confirmation* to
    equal :data:`PURGE_ALL_CONFIRMATION` and raises :class:`PurgeNotConfirmedError`
    otherwise (**C-002**), the same gate :func:`purge_all_events` applies to the
    journal and the ledger. Confirmation authorises, it does not trigger: ``dry_run``
    alone decides whether anything is deleted, so a confirmed preview is still a
    preview. The refusal is raised **before** the store is resolved, so a refused run
    cannot even create the queue file.

    **This is deliberately not the union of the per-project selectors**, and that was
    measured rather than assumed. ``remove_project_tasks`` strips its argument and
    returns ``0`` for a falsy one, while ``count_by_project`` groups rows verbatim —
    so a row whose ``project_uuid`` is ``''`` or ``'   '`` appears in the census and
    is removable by no selector at all. Feeding every census key back through the
    per-project purge leaves exactly those rows behind
    (``tests/delivery/test_purge_all_body_uploads_3030.py`` pins it, with the
    attributable rows going as its control).

    **Widening ``remove_project_tasks`` was rejected** (operator decision,
    2026-07-30): it is shared by other callers, and a blank selector that matches
    everything is precisely the hazard the frame purge had to guard against
    (:data:`IDENTITY_LESS_KEY` *is* ``""``, so an unstripped selector would vacuum the
    population at issue). So the total purge gets its own write here, in the module
    that already owns destructive writes over the delivery stores, rather than a
    second meaning for a shared per-project argument.

    The census is taken before and after even on a dry run, for the reason
    :func:`purge_project_body_uploads` records: "nothing changed" is the claim a dry
    run has to earn. ``removed`` is the store's own reported row count, carried so a
    caller can hold it *against* an independently measured differential — never as a
    substitute for one (NFR-006).
    """
    if not dry_run and confirmation != PURGE_ALL_CONFIRMATION:
        raise PurgeNotConfirmedError(
            "Refusing to purge every queued document body: a destructive `--all` run "
            f"requires confirmation={PURGE_ALL_CONFIRMATION!r}. Nothing was deleted. "
            "Run with dry_run=True first — its reported counts are exactly what a "
            "confirmed run will remove."
        )

    queue: BodyUploadTotalPurgeTarget = (
        body_queue if body_queue is not None else _default_body_queue()
    )

    before = dict(queue.count_by_project())
    removed = 0 if dry_run else _purge_all_body_rows(queue.db_path)
    after = dict(queue.count_by_project())

    return BodyQueuePurgeResult(
        project_uuid="all",
        dry_run=dry_run,
        removed=removed,
        before=before,
        after=after,
        all_uploads=True,
    )


#: Census key for rows whose ``project_uuid`` is NULL. Mirrors the body-queue
#: census convention (``count_by_project`` groups blank identity under ``""``), so
#: one purge report can present all three stores without a per-store special case.
IDENTITY_LESS_KEY = ""

_LEDGER_STATUS_CENSUS_SQL = f"SELECT status, COUNT(*) FROM {LEDGER_TABLE} GROUP BY status"  # noqa: S608  # nosec B608 — static module-constant identifier
_LEDGER_TOTAL_SQL = f"SELECT COUNT(*) FROM {LEDGER_TABLE}"  # noqa: S608  # nosec B608 — static module-constant identifier


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
    #: ``True`` for FR-017's total purge. A flag rather than a sentinel value in
    #: ``selector``: any sentinel string could in principle collide with a stored
    #: ``project_uuid``, and a census key that sometimes means "one project" and
    #: sometimes means "all of them" is the ambiguity C-003 forbids.
    all_events: bool = False

    @property
    def target_before(self) -> int:
        if self.all_events:
            return sum(self.journal_before.values())
        return self.journal_before.get(self.selector, 0)

    @property
    def target_after(self) -> int:
        if self.all_events:
            return sum(self.journal_after.values())
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

        For a total purge (:attr:`all_events`) there is no "other": the scope is the
        whole store, so this is ``0`` by definition and carries no information. The
        load-bearing check for that case is ``target_after == 0`` — asserted by
        :attr:`is_exact` — together with :attr:`other_ledger_differential`, which
        stays meaningful because it compares the ledger's *total* change against the
        change this purge accounts for.
        """
        if self.all_events:
            return 0
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
        """Everything selected went, nothing else moved (SC-006 / NFR-006).

        For a total purge the expected end state is simply zero journal rows. It is
        *not* ``target_before - purged_count``: the selection deliberately includes
        ledger-only event ids that were never journal rows, so that arithmetic would
        undershoot by exactly the number of ghost ledger events.
        """
        if self.all_events:
            expected_after = self.target_before if self.dry_run else 0
            return expected_after == self.target_after and self.other_ledger_differential == 0
        expected_after = self.target_before if self.dry_run else self.target_before - self.purged_count
        return (
            self.target_after == expected_after
            and self.other_project_journal_differential == 0
            and self.other_ledger_differential == 0
        )


def _journal_census(journal: EventJournal) -> dict[str, int]:
    """Per-project journal row counts, with unattributable rows under ``""``.

    Composed from the journal's public identity reads (``distinct_project_uuids`` +
    the filtered projection) rather than a GROUP BY of our own: the destructive write
    below is this module's sanctioned business, but a *census* has a public API and
    should not grow a second definition of "which projects does the store hold".

    **Total-preserving, and that is a correctness property rather than a nicety.**
    The unattributable bucket is derived as ``count() - (rows the projection can
    attribute)``, not read from ``count_missing_identity()``. The two differ: a row
    whose ``project_uuid`` is a non-NULL empty string is returned by
    ``distinct_project_uuids()`` (it is not NULL) but dropped by
    ``read_identity_projection``, which filters falsy uuids — and it is not
    ``IS NULL``, so ``count_missing_identity()`` does not see it either. Such a row
    was previously counted **nowhere**, and every NFR-006 differential subtracts this
    census: a population absent from both the before and after censuses has a
    differential of zero by construction, so a purge could move it and still report
    "0% of any other project's rows". Measured on a seeded store: the census summed
    to 5 against ``count() == 6``.

    For the ordinary case — identity either resolved or NULL — the derived number is
    exactly ``count_missing_identity()``, so this changes no existing report.
    """
    census: dict[str, int] = {}
    attributed = 0
    for uuid in journal.distinct_project_uuids():
        rows = len(journal.read_identity_projection(project_uuids=[uuid]))
        if not rows:
            # A uuid the store admits to holding but the projection cannot return:
            # the falsy-uuid case above. Its rows fall into the unattributable
            # remainder rather than being recorded as an empty project.
            continue
        census[uuid] = rows
        attributed += rows
    unattributable = max(journal.count() - attributed, 0)
    if unattributable:
        census[IDENTITY_LESS_KEY] = unattributable
    return census


def _ledger_status_census(
    ledger: SqliteDeliveryLedger, event_ids: Sequence[str]
) -> dict[str, int]:
    """Per-status ledger counts restricted to *event_ids* (the forensic breakdown)."""
    census: dict[str, int] = {}
    for event_id in event_ids:
        for row in ledger.connection.execute(
            f"SELECT status FROM {LEDGER_TABLE} WHERE {COL_EVENT_ID} = ?",  # noqa: S608  # nosec B608 — static module-constant identifiers
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
                f"DELETE FROM {LEDGER_TABLE} WHERE {COL_EVENT_ID} = ?",  # noqa: S608  # nosec B608 — static module-constant identifiers
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
    all_events: bool = False,
) -> ProjectPurgeResult:
    """Shared core: census, (optionally) delete both stores, census again.

    The **only** DELETE path over these two stores; every selector composes onto it
    (C-003). ``all_events`` is carried through purely so the result can interpret its
    own censuses — it changes no behaviour here.
    """
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
        all_events=all_events,
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


def _all_event_ids(journal: EventJournal, ledger: SqliteDeliveryLedger) -> list[str]:
    """Every event id present in **either** store, journal order first then ledger.

    Order matters only for reproducibility of the reported id list; the delete is
    id-keyed and order-independent.
    """
    connection: Any = sqlite3.connect(str(journal.db_path))
    try:
        journal_ids = [str(row[0]) for row in connection.execute(_ALL_JOURNAL_IDS_SQL)]
    finally:
        connection.close()

    seen = set(journal_ids)
    ledger_only = [
        event_id
        for event_id in (
            str(row[0]) for row in ledger.connection.execute(_ALL_LEDGER_IDS_SQL)
        )
        if event_id not in seen
    ]
    return journal_ids + ledger_only


def purge_all_events(
    *,
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    dry_run: bool = True,
    confirmation: str = "",
) -> ProjectPurgeResult:
    """Remove **every** row from the journal and the delivery ledger (FR-017).

    Dry-run by default; a destructive run additionally requires *confirmation* to
    equal :data:`PURGE_ALL_CONFIRMATION` and raises :class:`PurgeNotConfirmedError`
    otherwise (**C-002**). Confirmation authorises, it does not trigger: ``dry_run``
    alone decides whether anything is deleted, so a confirmed preview is still a
    preview.

    **This is deliberately not the union of the per-project selectors**, and that was
    measured rather than assumed. Running every uuid from
    ``journal.distinct_project_uuids()`` through :func:`purge_project_events` and then
    :func:`purge_identity_less_events` leaves three populations behind:

    1. ``project_uuid = ''``. ``distinct_project_uuids()`` returns it (not NULL), but
       ``read_identity_projection`` filters falsy uuids and
       :func:`purge_project_events` blanks a falsy selector to "select nothing";
       ``iter_rows_missing_identity`` matches ``IS NULL`` only. Owned by neither.
    2. ``project_uuid = '   '``. The projection *can* return it, but
       :func:`purge_project_events` strips its selector, so the row is visible in the
       census and unreachable by any purge.
    3. A ledger row whose ``event_id`` has no journal row. The union only ever
       collects ids *from the journal*. Not a contrived state: :func:`gc_payloads` in
       this module deletes journal payload rows and preserves ledger history on
       purpose (FR-010), so every machine that has run ``sync gc`` holds some.

    So the selection is FR-017's own read of both tables — while the *deletion* still
    goes through the one shared :func:`_purge` core, so there is no second DELETE path
    over these stores (C-003). ``tests/delivery/test_purge_all_events_3030.py`` pins
    the non-composability, and fails if a later change makes the union total.

    ``undelivered_only`` is not offered: "purge everything except what already
    shipped" is not FR-017, and a total purge that quietly retained rows would be the
    false-totality claim this function exists to avoid.

    There is intentionally **no** ``purge_all_from_live_stores`` companion to
    :func:`purge_project_events_from_live_stores`. A zero-argument "erase every event
    on this machine" helper is precisely the shape C-002 warns about; resolving the
    live stores for ``--all`` belongs to the confirmed, operator-facing CLI path.
    """
    if not dry_run and confirmation != PURGE_ALL_CONFIRMATION:
        raise PurgeNotConfirmedError(
            "Refusing to purge every event: a destructive `--all` run requires "
            f"confirmation={PURGE_ALL_CONFIRMATION!r}. Nothing was deleted. Run with "
            "dry_run=True first — its reported counts are exactly what a confirmed "
            "run will remove."
        )

    return _purge(
        selector="all",
        event_ids=_all_event_ids(journal, ledger),
        journal=journal,
        ledger=ledger,
        dry_run=dry_run,
        undelivered_only=False,
        all_events=True,
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


def _default_body_queue() -> OfflineBodyUploadQueue:
    """The real body queue, on the DB file it shares with the event offline queue.

    Annotated with the concrete class rather than :class:`BodyUploadPurgeTarget`
    because it backs both body-store purges and they need different members: the
    per-project one deletes through ``remove_project_tasks``, the total one needs
    ``db_path``. Narrowing the default to one protocol would make it unusable as the
    other's default for no benefit — the *parameters* stay protocol-typed, which is
    where the decoupling earns its keep.
    """
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


# The purge surface joins this list now that WP08's ``sync purge`` command imports
# it — the moment these names stopped being aspirational. Advertising them earlier
# would have failed the symbol-level dead-code gate
# (``tests/architectural/test_no_dead_symbols.py``, a shrink-only ratchet over
# ``__all__``) or needed an allowlist entry that outlived its reason.
#
# ``BodyQueuePurgeResult`` / ``BodyUploadPurgeTarget`` / ``BodyUploadTotalPurgeTarget``
# / ``IDENTITY_LESS_KEY`` stay off the list deliberately: the CLI consumes what
# ``purge_project_body_uploads`` and ``purge_all_body_uploads`` return without naming
# their type, and a name in ``__all__`` with no importer is exactly what that gate
# exists to catch. They remain importable for tests and for a future caller that needs
# the annotation.
__all__ = [
    "PURGE_ALL_CONFIRMATION",
    "ProjectPurgeResult",
    "PurgeNotConfirmedError",
    "RetentionResult",
    "archive_payloads",
    "gc_payloads",
    "purge_all_body_uploads",
    "purge_all_events",
    "purge_identity_less_events",
    "purge_project_body_uploads",
    "purge_project_events",
    "purge_project_events_from_live_stores",
    "resolve_live_store_paths",
]
