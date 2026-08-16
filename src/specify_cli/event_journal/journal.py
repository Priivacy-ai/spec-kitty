"""Connection-free repository for one UUID-owned event journal.

The live journal is a view over an active :class:`ProjectUnitOfWork`.  It never
resolves a path, opens SQLite, commits, or chooses a legacy destination.  The
store owns the outer transaction; the layout authority revalidates every write
under its machine lock immediately before the repository mutates ``sync.db``.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Protocol, cast

from kernel.clock import now_utc_iso
from specify_cli.paths import get_runtime_root
from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutGenerationAuthority,
    LayoutTestHooks,
    LayoutWritePermit,
)
from specify_cli.sync.project_context import VerifiedProjectStoreIdentity
from specify_cli.sync.project_store import ProjectUnitOfWork

from .models import (
    DRAIN_BLOCKED_MISSING_AUTH,
    DRAIN_BLOCKED_MISSING_TEAM,
    DRAIN_BLOCKED_SAAS_DISABLED,
    Event,
)

JOURNAL_SUBDIR = "event_journal"
ANONYMOUS_PRODUCER = "local"
_PAYLOAD_ENCODING = "base64"


class ProjectLayoutRequiredError(RuntimeError):
    """A live writer received a permit for the retired shared layout."""


@dataclass(frozen=True, slots=True)
class JournalWriteReceipt:
    """Stable owner/ordering identity assigned with a captured payload."""

    event_id: str
    project_uuid: str
    capture_sequence: int
    epoch_id: int
    inserted: bool


@dataclass(frozen=True, slots=True)
class EventIdentityRow:
    """Payload-free identity projection used by consent and diagnostics."""

    event_id: str
    created_at: str
    project_uuid: str | None
    repo_slug: str | None
    drain_blocked_reason: str | None
    project_slug: str | None = None


@dataclass(frozen=True, slots=True)
class CoalesceDecision:
    """A coalescing strategy's decision for one incoming event."""

    store_as_new: bool = True


class CoalesceStrategy(Protocol):
    def __call__(self, journal: EventJournal, event: Event) -> CoalesceDecision: ...


def _no_op_coalesce(journal: EventJournal, event: Event) -> CoalesceDecision:
    del journal, event
    return CoalesceDecision()


_active_coalesce_strategy: CoalesceStrategy = _no_op_coalesce


def register_coalesce_strategy(strategy: CoalesceStrategy) -> None:
    global _active_coalesce_strategy
    _active_coalesce_strategy = strategy


def reset_coalesce_strategy() -> None:
    global _active_coalesce_strategy
    _active_coalesce_strategy = _no_op_coalesce


def _event_document(event: Event) -> str:
    document = asdict(event)
    document["payload"] = base64.b64encode(event.payload).decode("ascii")
    document["payload_encoding"] = _PAYLOAD_ENCODING
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def _event_from_document(document: str) -> Event:
    raw: Any = json.loads(document)
    if not isinstance(raw, dict) or raw.get("payload_encoding") != _PAYLOAD_ENCODING:
        raise ValueError("journal payload document has an unsupported encoding")
    encoded = raw.pop("payload", None)
    raw.pop("payload_encoding", None)
    if not isinstance(encoded, str):
        raise ValueError("journal payload document is missing its payload")
    raw["payload"] = base64.b64decode(encoded, validate=True)
    return Event(**raw)


def _require_project_destination(permit: LayoutWritePermit) -> None:
    if permit.destination is not LayoutDestination.PROJECT_STORE:
        raise ProjectLayoutRequiredError("live payload writes require the project_only layout; legacy state is migration input only")


class EventJournal:
    """Short-lived journal adapter over one active project unit of work."""

    __slots__ = ("_authority", "_unit")

    def __init__(
        self,
        unit: ProjectUnitOfWork,
        authority: LayoutGenerationAuthority,
    ) -> None:
        self._unit = unit
        self._authority = authority

    @property
    def project_uuid(self) -> str:
        return str(self._unit.project_uuid.storage_token)

    @property
    def unit_of_work_identity(self) -> int:
        return int(self._unit.connection_identity)

    @property
    def store_identity(self) -> VerifiedProjectStoreIdentity:
        """Return the opaque identity minted for this repository's active UoW."""
        return self._unit.store_identity

    def _existing_assignment(self, event_id: str) -> JournalWriteReceipt | None:
        row = self._unit.execute(
            "SELECT capture_sequence, epoch_id FROM journal_entries WHERE project_uuid = ? AND entry_id = ?",
            (self.project_uuid, event_id),
        ).fetchone()
        if row is None:
            return None
        return JournalWriteReceipt(
            event_id=event_id,
            project_uuid=self.project_uuid,
            capture_sequence=int(cast("str | int | float | bytes", row[0])),
            epoch_id=int(cast("str | int | float | bytes", row[1])),
            inserted=False,
        )

    def append(
        self,
        event: Event,
        *,
        test_hooks: LayoutTestHooks | None = None,
    ) -> JournalWriteReceipt:
        """Capture one event with owner, sequence, and epoch in the outer UoW."""
        if event.project_uuid != self.project_uuid:
            raise ValueError("event-declared project UUID does not match store owner")
        existing = self._existing_assignment(event.event_id)
        if existing is not None:
            return existing
        decision = _active_coalesce_strategy(self, event)
        if not decision.store_as_new:
            # A strategy that suppresses the incoming identity must leave a prior
            # row. Return that row's assignment when it reused the same id, or a
            # sentinel receipt for the intentionally collapsed incoming event.
            prior = self._existing_assignment(event.event_id)
            return prior or JournalWriteReceipt(
                event_id=event.event_id,
                project_uuid=self.project_uuid,
                capture_sequence=0,
                epoch_id=0,
                inserted=False,
            )

        receipt: JournalWriteReceipt | None = None

        def write(permit: LayoutWritePermit) -> None:
            nonlocal receipt
            _require_project_destination(permit)
            # Local import avoids journal -> consent -> config -> queue -> journal.
            from specify_cli.sync.consent import allocate_capture_sequence

            assignment = allocate_capture_sequence(self._unit)
            self._unit.execute(
                "INSERT INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    self.project_uuid,
                    assignment.epoch_id,
                    assignment.capture_sequence,
                    _event_document(event),
                    event.created_at,
                ),
            )
            receipt = JournalWriteReceipt(
                event_id=event.event_id,
                project_uuid=self.project_uuid,
                capture_sequence=assignment.capture_sequence,
                epoch_id=assignment.epoch_id,
                inserted=True,
            )

        permit = self._authority.issue_write_permit()
        self._authority.execute_write(permit, write, test_hooks=test_hooks)
        if receipt is None:  # pragma: no cover - authority callback invariant
            raise RuntimeError("layout authority returned without executing journal write")
        return receipt

    def record(self, event: Event) -> JournalWriteReceipt:
        return self.append(event)

    @contextmanager
    def transaction(self) -> Iterator[EventJournal]:
        """Compatibility grouping seam; the store already owns the transaction."""
        yield self

    def read_all(self) -> list[Event]:
        rows = self._unit.execute(
            "SELECT payload_json FROM journal_entries WHERE project_uuid = ? ORDER BY capture_sequence, entry_id",
            (self.project_uuid,),
        ).fetchall()
        return [_event_from_document(str(row[0])) for row in rows]

    def read_by_id(self, event_id: str) -> Event | None:
        row = self._unit.execute(
            "SELECT payload_json FROM journal_entries WHERE project_uuid = ? AND entry_id = ?",
            (self.project_uuid, event_id),
        ).fetchone()
        return None if row is None else _event_from_document(str(row[0]))

    def read_by_ids(self, event_ids: Sequence[str]) -> list[Event]:
        if not event_ids:
            return []
        placeholders = ", ".join("?" for _ in event_ids)
        rows = self._unit.execute(
            f"SELECT entry_id, payload_json FROM journal_entries "  # noqa: S608  # nosec B608 - count-derived placeholders only
            f"WHERE project_uuid = ? AND entry_id IN ({placeholders})",
            (self.project_uuid, *event_ids),
        ).fetchall()
        found = {str(row[0]): _event_from_document(str(row[1])) for row in rows}
        return [found[event_id] for event_id in event_ids if event_id in found]

    def read_blocked(self) -> list[Event]:
        return [event for event in self.read_all() if event.drain_blocked_reason is not None]

    def read_identity_projection(
        self,
        *,
        project_uuids: Sequence[str],
    ) -> list[EventIdentityRow]:
        if self.project_uuid not in project_uuids:
            return []
        return [self._identity(event) for event in self.read_all()]

    def read_identity_projection_for_report(self) -> list[EventIdentityRow]:
        """Read the explicit store's payload-free owner projection only."""
        rows = self._unit.execute(
            "SELECT entry_id, created_at, payload_json FROM journal_entries WHERE project_uuid = ? ORDER BY capture_sequence, entry_id",
            (self.project_uuid,),
        ).fetchall()
        projected: list[EventIdentityRow] = []
        for row in rows:
            event = _event_from_document(str(row[2]))
            projected.append(self._identity(event, created_at=str(row[1] or event.created_at)))
        return projected

    @staticmethod
    def _identity(event: Event, *, created_at: str | None = None) -> EventIdentityRow:
        return EventIdentityRow(
            event_id=event.event_id,
            created_at=created_at or event.created_at,
            project_uuid=event.project_uuid,
            project_slug=event.project_slug,
            repo_slug=event.repo_slug,
            drain_blocked_reason=event.drain_blocked_reason,
        )

    def iter_rows_missing_identity(self) -> list[tuple[str, bytes]]:
        return []

    def set_project_identity(
        self,
        entries: list[tuple[str, str | None, str | None, str | None]],
    ) -> int:
        if entries:
            raise ValueError("project-owned journal rows cannot be backfilled with another identity")
        return 0

    def count_missing_identity(self) -> int:
        return 0

    def distinct_project_uuids(self) -> list[str]:
        return [self.project_uuid] if self.count() else []

    def count(self) -> int:
        row = self._unit.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE project_uuid = ?",
            (self.project_uuid,),
        ).fetchone()
        return int(cast("str | int | float | bytes", row[0])) if row is not None else 0

    def owner_consent_projection(self) -> tuple[str | None, int | None]:
        """Return this store owner's payload-free decision on the active UoW."""
        row = self._unit.execute(
            "SELECT state, generation FROM project_consent_decisions WHERE project_uuid = ?",
            (self.project_uuid,),
        ).fetchone()
        if row is None:
            return None, None
        return str(row[0]), int(cast("str | int | float | bytes", row[1]))

    def oldest_created_at(self) -> str | None:
        candidates = [event.created_at for event in self.read_all() if event.archived_at is None]
        return min(candidates) if candidates else None

    def mark_archived(self, event_id: str, at: str) -> None:
        stored = self.read_by_id(event_id)
        if stored is None or stored.archived_at is not None:
            return
        updated = replace(stored, archived_at=at)

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            self._unit.execute(
                "UPDATE journal_entries SET payload_json = ? WHERE project_uuid = ? AND entry_id = ?",
                (_event_document(updated), self.project_uuid, event_id),
            )

        self._authority.execute_write(self._authority.issue_write_permit(), write)

    def purge_events(
        self,
        event_ids: Sequence[str],
        *,
        preserve_delivery_history: bool = False,
    ) -> int:
        """Explicit retention-only deletion inside the store-owned UoW."""
        ids = list(dict.fromkeys(event_ids))
        if not ids:
            return 0
        placeholders = ", ".join("?" for _ in ids)
        before = sum(self.read_by_id(event_id) is not None for event_id in ids)

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            if preserve_delivery_history:
                self._unit.execute(
                    f"UPDATE outbox_tasks SET journal_entry_id = NULL "  # noqa: S608  # nosec B608 - count-derived placeholders only
                    f"WHERE project_uuid = ? AND journal_entry_id IN ({placeholders})",
                    (self.project_uuid, *ids),
                )
            else:
                # Explicit purge removes aggregate evidence children first.
                attempts = self._unit.execute(
                    f"SELECT attempt_id FROM delivery_attempts WHERE project_uuid = ? "  # noqa: S608  # nosec B608 - count-derived placeholders only
                    f"AND outbox_task_id IN (SELECT task_id FROM outbox_tasks WHERE "
                    f"project_uuid = ? AND journal_entry_id IN ({placeholders}))",
                    (self.project_uuid, self.project_uuid, *ids),
                ).fetchall()
                attempt_ids = [str(row[0]) for row in attempts]
                if attempt_ids:
                    attempt_placeholders = ", ".join("?" for _ in attempt_ids)
                    self._unit.execute(
                        f"DELETE FROM delivery_results WHERE project_uuid = ? "  # noqa: S608  # nosec B608 - count-derived placeholders only
                        f"AND attempt_id IN ({attempt_placeholders})",
                        (self.project_uuid, *attempt_ids),
                    )
                    self._unit.execute(
                        f"DELETE FROM delivery_attempts WHERE project_uuid = ? "  # noqa: S608  # nosec B608 - count-derived placeholders only
                        f"AND attempt_id IN ({attempt_placeholders})",
                        (self.project_uuid, *attempt_ids),
                    )
                self._unit.execute(
                    f"DELETE FROM outbox_tasks WHERE project_uuid = ? "  # noqa: S608  # nosec B608 - count-derived placeholders only
                    f"AND journal_entry_id IN ({placeholders})",
                    (self.project_uuid, *ids),
                )
            self._unit.execute(
                f"DELETE FROM journal_entries WHERE project_uuid = ? "  # noqa: S608  # nosec B608 - count-derived placeholders only
                f"AND entry_id IN ({placeholders})",
                (self.project_uuid, *ids),
            )

        self._authority.execute_write(self._authority.issue_write_permit(), write)
        return before

    def replace_undelivered_payload(self, event_id: str, payload: bytes) -> None:
        stored = self.read_by_id(event_id)
        if stored is None:
            raise KeyError(event_id)
        updated = replace(stored, payload=payload)

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            self._unit.execute(
                "UPDATE journal_entries SET payload_json = ? WHERE project_uuid = ? AND entry_id = ?",
                (_event_document(updated), self.project_uuid, event_id),
            )

        self._authority.execute_write(self._authority.issue_write_permit(), write)

    def record_supersede(
        self,
        superseded_event_id: str,
        superseded_by_event_id: str,
        coalesce_key: str,
        at: str,
    ) -> None:
        prior = self._unit.execute(
            "SELECT epoch_id FROM journal_entries WHERE project_uuid = ? AND entry_id = ?",
            (self.project_uuid, superseded_event_id),
        ).fetchone()
        if prior is None:
            raise KeyError(superseded_event_id)
        task_id = f"coalesce:{superseded_event_id}:{superseded_by_event_id}"
        identity = json.dumps(
            {"coalesce_key": coalesce_key, "at": at},
            sort_keys=True,
            separators=(",", ":"),
        )

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            self._unit.execute(
                "INSERT OR IGNORE INTO outbox_tasks "
                "(task_id, project_uuid, epoch_id, journal_entry_id, task_kind, state, "
                "idempotency_identity, created_at) VALUES (?, ?, ?, ?, 'coalesce_supersede', "
                "'recorded', ?, ?)",
                (
                    task_id,
                    self.project_uuid,
                    int(cast("str | int | float | bytes", prior[0])),
                    superseded_event_id,
                    identity,
                    at,
                ),
            )

        self._authority.execute_write(self._authority.issue_write_permit(), write)

    def supersede_rows(self) -> list[tuple[str, str, str | None, str]]:
        rows = self._unit.execute(
            "SELECT task_id, idempotency_identity, created_at FROM outbox_tasks "
            "WHERE project_uuid = ? AND task_kind = 'coalesce_supersede' "
            "ORDER BY created_at, task_id",
            (self.project_uuid,),
        ).fetchall()
        result: list[tuple[str, str, str | None, str]] = []
        for row in rows:
            _, prior, successor = str(row[0]).split(":", 2)
            metadata = json.loads(str(row[1]))
            result.append((prior, successor, metadata.get("coalesce_key"), str(row[2])))
        return result


# Historical type name retained without restoring component transaction control.
JournalTransaction = EventJournal


def resolve_journal_path(*, user_id: str | None = None, team_slug: str | None = None) -> Path:
    """Return a legacy source path for named migration/diagnostics only."""
    del user_id, team_slug
    return Path(get_runtime_root().base) / JOURNAL_SUBDIR / "journal-local.db"


def get_journal(
    *,
    unit: ProjectUnitOfWork,
    authority: LayoutGenerationAuthority,
) -> EventJournal:
    """Construct the live journal only from explicit store-owned capabilities."""
    return EventJournal(unit, authority)


def reset_journal_cache() -> None:
    """Retained as a no-op while callers migrate; live journals are never cached."""


@dataclass(frozen=True, slots=True)
class CaptureGateState:
    saas_enabled: bool
    checkout_enabled: bool
    authenticated: bool
    team_slug: str | None


def classify_drain_blocked_reason(gate: CaptureGateState) -> str | None:
    if not gate.saas_enabled or not gate.checkout_enabled:
        return str(DRAIN_BLOCKED_SAAS_DISABLED)
    if not gate.authenticated:
        return str(DRAIN_BLOCKED_MISSING_AUTH)
    if gate.team_slug is None:
        return str(DRAIN_BLOCKED_MISSING_TEAM)
    return None


class TeamspaceBoundDropError(RuntimeError):
    def __init__(self, *, event_id: str) -> None:
        super().__init__(f"refusing to silently drop Teamspace-bound event {event_id!r}")
        self.event_id = event_id


def capture_teamspace_bound(
    *,
    journal: EventJournal,
    event_id: str,
    event_type: str,
    payload: bytes,
    occurred_at: str,
    gate: CaptureGateState,
    coalesce_key: str | None = None,
    is_teamspace_bound: bool = True,
    skip_journal: bool = False,
    created_at: str | None = None,
    project_uuid: str | None = None,
    project_slug: str | None = None,
    repo_slug: str | None = None,
) -> Event:
    if is_teamspace_bound and skip_journal:
        raise TeamspaceBoundDropError(event_id=event_id)
    event = Event(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        occurred_at=occurred_at,
        created_at=created_at or now_utc_iso(),
        coalesce_key=coalesce_key,
        drain_blocked_reason=classify_drain_blocked_reason(gate),
        project_uuid=project_uuid,
        project_slug=project_slug,
        repo_slug=repo_slug,
    )
    journal.append(event)
    return event


__all__ = [
    "ANONYMOUS_PRODUCER",
    "CaptureGateState",
    "CoalesceDecision",
    "CoalesceStrategy",
    "EventIdentityRow",
    "EventJournal",
    "JOURNAL_SUBDIR",
    "JournalTransaction",
    "TeamspaceBoundDropError",
    "capture_teamspace_bound",
    "classify_drain_blocked_reason",
    "get_journal",
    "register_coalesce_strategy",
    "reset_coalesce_strategy",
    "reset_journal_cache",
    "resolve_journal_path",
]
