"""Explicit retention operations over one verified project store."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import cast

from kernel.clock import now_utc_iso
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.event_journal.journal import EventJournal
from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutGenerationAuthority,
    LayoutWritePermit,
)
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.project_store import ProjectUnitOfWork

PURGE_ALL_CONFIRMATION = "purge all events"
IDENTITY_LESS_KEY = ""


class PurgeNotConfirmedError(RuntimeError):
    pass


def _require_project_destination(permit: LayoutWritePermit) -> None:
    if permit.destination is not LayoutDestination.PROJECT_STORE:
        raise RuntimeError("purge requires the project_only layout")


@dataclass(frozen=True, slots=True)
class RetentionResult:
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


@dataclass(frozen=True, slots=True)
class ProjectPayloadPurgeResult:
    project_uuid: str
    dry_run: bool
    target_before: int
    target_after: int
    selected: int
    body_before: int
    body_after: int
    result_before: int
    result_after: int
    other_project_differential: int = 0

    @property
    def is_exact(self) -> bool:
        expected = self.target_before if self.dry_run else 0
        return self.target_after == expected and self.other_project_differential == 0


@dataclass(frozen=True, slots=True)
class BodyQueuePurgeResult:
    project_uuid: str
    dry_run: bool
    removed: int
    before: Mapping[str, int] = field(default_factory=dict)
    after: Mapping[str, int] = field(default_factory=dict)
    all_uploads: bool = False

    @property
    def target_before(self) -> int:
        return sum(self.before.values()) if self.all_uploads else self.before.get(self.project_uuid, 0)

    @property
    def target_after(self) -> int:
        return sum(self.after.values()) if self.all_uploads else self.after.get(self.project_uuid, 0)

    @property
    def other_project_differential(self) -> int:
        if self.all_uploads:
            return 0
        others = (set(self.before) | set(self.after)) - {self.project_uuid}
        return sum(abs(self.after.get(key, 0) - self.before.get(key, 0)) for key in others)

    @property
    def is_exact(self) -> bool:
        expected = self.target_before if self.dry_run else 0
        return self.target_after == expected and self.other_project_differential == 0


@dataclass(frozen=True, slots=True)
class ProjectPurgeResult:
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
    all_events: bool = False

    @property
    def target_before(self) -> int:
        return sum(self.journal_before.values()) if self.all_events else self.journal_before.get(self.selector, 0)

    @property
    def target_after(self) -> int:
        return sum(self.journal_after.values()) if self.all_events else self.journal_after.get(self.selector, 0)

    @property
    def purged_count(self) -> int:
        return len(self.purged_event_ids)

    @property
    def ledger_rows_selected(self) -> int:
        return sum(self.ledger_status_before.values())

    @property
    def never_attempted(self) -> int:
        return max(self.purged_count - self.ledger_rows_selected, 0)

    @property
    def other_project_journal_differential(self) -> int:
        if self.all_events:
            return 0
        others = (set(self.journal_before) | set(self.journal_after)) - {self.selector}
        return sum(abs(self.journal_after.get(key, 0) - self.journal_before.get(key, 0)) for key in others)

    @property
    def other_ledger_differential(self) -> int:
        return abs((self.ledger_total_before - self.ledger_total_after) - self.ledger_rows_removed)

    @property
    def is_exact(self) -> bool:
        expected = self.target_before if self.dry_run else self.target_before - self.purged_count if self.undelivered_only else 0
        return self.target_after == expected and self.other_project_journal_differential == 0 and self.other_ledger_differential == 0


def _payload_bytes(journal: EventJournal, *, live_only: bool) -> int:
    return sum(len(event.payload) for event in journal.read_all() if not live_only or event.archived_at is None)


def archive_payloads(
    journal: EventJournal,
    *,
    event_ids: Sequence[str] | None = None,
    at: str | None = None,
) -> RetentionResult:
    candidates = list(event_ids) if event_ids is not None else [event.event_id for event in journal.read_all() if event.archived_at is None]
    before = _payload_bytes(journal, live_only=True)
    archived: list[str] = []
    skipped: list[str] = []
    timestamp = at or now_utc_iso()
    for event_id in candidates:
        event = journal.read_by_id(event_id)
        if event is None or event.archived_at is not None:
            skipped.append(event_id)
        else:
            journal.mark_archived(event_id, timestamp)
            archived.append(event_id)
    return RetentionResult(
        operation="archive",
        archived=tuple(archived),
        skipped=tuple(skipped),
        journal_size_bytes_before=before,
        journal_size_bytes_after=_payload_bytes(journal, live_only=True),
    )


def gc_payloads(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    *,
    known_target_ids: Sequence[str] = (),
    event_ids: Sequence[str] | None = None,
) -> RetentionResult:
    candidates = list(event_ids) if event_ids is not None else [event.event_id for event in journal.read_all()]
    before = _payload_bytes(journal, live_only=False)
    purged = [event_id for event_id in candidates if known_target_ids and all(ledger.delivered_to_target(event_id, target_id) for target_id in known_target_ids)]
    skipped = [event_id for event_id in candidates if event_id not in purged]
    journal.purge_events(purged, preserve_delivery_history=True)
    return RetentionResult(
        operation="gc",
        purged=tuple(purged),
        skipped=tuple(skipped),
        journal_size_bytes_before=before,
        journal_size_bytes_after=_payload_bytes(journal, live_only=False),
    )


def purge_project_body_uploads(
    project_uuid: str,
    *,
    body_queue: OfflineBodyUploadQueue,
    dry_run: bool = True,
) -> BodyQueuePurgeResult:
    target = project_uuid.strip().lower()
    if not isinstance(body_queue, OfflineBodyUploadQueue):
        raise TypeError("body purge requires a project-store body queue")
    if target != body_queue.project_uuid:
        raise ValueError("body purge selector must match the project store owner")
    before = dict(body_queue.count_by_project())
    removed = 0 if dry_run else body_queue.remove_project_tasks(target)
    after = dict(body_queue.count_by_project())
    return BodyQueuePurgeResult(target, dry_run, removed, before, after)


def _counts(unit: ProjectUnitOfWork) -> tuple[int, int, int]:
    owner = unit.project_uuid.storage_token
    journal = unit.execute("SELECT COUNT(*) FROM journal_entries WHERE project_uuid = ?", (owner,)).fetchone()
    body = unit.execute("SELECT COUNT(*) FROM body_upload_tasks WHERE project_uuid = ?", (owner,)).fetchone()
    results = unit.execute("SELECT COUNT(*) FROM delivery_results WHERE project_uuid = ?", (owner,)).fetchone()
    return (
        int(cast("str | int | float | bytes", journal[0])) if journal is not None else 0,
        int(cast("str | int | float | bytes", body[0])) if body is not None else 0,
        int(cast("str | int | float | bytes", results[0])) if results is not None else 0,
    )


def purge_project_payloads(
    unit: ProjectUnitOfWork,
    authority: LayoutGenerationAuthority,
    *,
    dry_run: bool = False,
) -> ProjectPayloadPurgeResult:
    """Explicitly remove every payload/result row in this one physical store."""
    owner = unit.project_uuid.storage_token
    before = _counts(unit)

    def write(permit: LayoutWritePermit) -> None:
        _require_project_destination(permit)
        for table in (
            "delivery_results",
            "delivery_attempts",
            "outbox_tasks",
            "body_upload_tasks",
            "journal_entries",
        ):
            unit.execute(f"DELETE FROM {table} WHERE project_uuid = ?", (owner,))  # noqa: S608 - fixed table allowlist

    if not dry_run:
        authority.execute_write(authority.issue_write_permit(), write)
    after = _counts(unit)
    return ProjectPayloadPurgeResult(
        project_uuid=owner,
        dry_run=dry_run,
        target_before=before[0],
        target_after=after[0],
        selected=before[0],
        body_before=before[1],
        body_after=after[1],
        result_before=before[2],
        result_after=after[2],
    )


def _journal_census(journal: EventJournal) -> dict[str, int]:
    return {journal.project_uuid: journal.count()} if journal.count() else {}


def purge_project_events(
    project_uuid: str,
    *,
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    dry_run: bool = True,
    undelivered_only: bool = False,
) -> ProjectPurgeResult:
    target = project_uuid.strip().lower()
    if target != journal.project_uuid or target != ledger.project_uuid:
        raise ValueError("purge selector must match the explicit project store owner")
    events = journal.read_all()
    ids = [event.event_id for event in events if not undelivered_only or not ledger.delivered_anywhere(event.event_id)]
    before_rows = ledger.rows()
    status_before: dict[str, int] = {}
    for row in before_rows:
        if row.event_id in ids:
            status_before[row.status] = status_before.get(row.status, 0) + 1
    before = _journal_census(journal)
    if not dry_run:
        journal.purge_events(ids)
    after = _journal_census(journal)
    after_rows = ledger.rows()
    return ProjectPurgeResult(
        selector=target,
        dry_run=dry_run,
        undelivered_only=undelivered_only,
        purged_event_ids=tuple(ids),
        ledger_rows_removed=(len(before_rows) - len(after_rows)) if not dry_run else 0,
        journal_before=before,
        journal_after=after,
        ledger_status_before=status_before,
        ledger_status_after={},
        ledger_total_before=len(before_rows),
        ledger_total_after=len(after_rows),
    )


def purge_identity_less_events(*_args: object, **_kwargs: object) -> ProjectPurgeResult:
    """Project stores cannot contain identity-less rows."""
    return ProjectPurgeResult(IDENTITY_LESS_KEY, True, False)


def purge_all_events(
    *,
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    dry_run: bool = True,
    confirmation: str = "",
) -> ProjectPurgeResult:
    if not dry_run and confirmation != PURGE_ALL_CONFIRMATION:
        raise PurgeNotConfirmedError("destructive total purge requires the confirmation phrase")
    result = purge_project_events(
        journal.project_uuid,
        journal=journal,
        ledger=ledger,
        dry_run=dry_run,
    )
    return replace(result, all_events=True)


def resolve_live_store_paths() -> tuple[None, None]:
    """Refuse the retired global live-store resolver."""
    raise RuntimeError("live stores are selected only by explicit ProjectSyncStore context")


def purge_project_events_from_live_stores(*_args: object, **_kwargs: object) -> ProjectPurgeResult:
    raise RuntimeError("pass an explicit project store and maintenance capability")


__all__ = [
    "BodyQueuePurgeResult",
    "IDENTITY_LESS_KEY",
    "PURGE_ALL_CONFIRMATION",
    "ProjectPayloadPurgeResult",
    "ProjectPurgeResult",
    "PurgeNotConfirmedError",
    "RetentionResult",
    "archive_payloads",
    "gc_payloads",
    "purge_all_events",
    "purge_identity_less_events",
    "purge_project_body_uploads",
    "purge_project_events",
    "purge_project_events_from_live_stores",
    "purge_project_payloads",
    "resolve_live_store_paths",
]
