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
