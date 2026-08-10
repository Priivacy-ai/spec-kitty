"""Connection-free delivery result repository for one project store."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, cast

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutGenerationAuthority,
    LayoutTestHooks,
    LayoutWritePermit,
)
from specify_cli.sync.project_context import VerifiedProjectStoreIdentity
from specify_cli.sync.project_store import ProjectUnitOfWork
from specify_cli.sync.history_disclosure import (
    HistoryDisclosureCapability,
    revalidate_history_disclosure,
)

LEDGER_TABLE = "delivery_results"
LEDGER_INDEX_NAME = "project_store_delivery_results"

STATUS_SUCCESS = "success"
STATUS_DUPLICATE = "duplicate"
STATUS_PENDING = "pending"
STATUS_REJECTED = "rejected"
STATUS_FAILED_TRANSIENT = "failed_transient"
STATUS_TERMINAL_FAILED = "terminal_failed"
TERMINAL_SUCCESS_STATUSES = frozenset({STATUS_SUCCESS, STATUS_DUPLICATE})
TERMINAL_STATUSES = TERMINAL_SUCCESS_STATUSES | {STATUS_TERMINAL_FAILED}


@dataclass(frozen=True, slots=True)
class _ResultSpec:
    status: str
    set_accepted: bool = False
    set_completed: bool = False
    server_drain_state: str | None = None


_RESULT_STATUS_SPEC = {
    "success": _ResultSpec(STATUS_SUCCESS, set_completed=True),
    "duplicate": _ResultSpec(STATUS_DUPLICATE, set_completed=True),
    "pending": _ResultSpec(STATUS_PENDING, set_accepted=True, server_drain_state="pending"),
    "rejected": _ResultSpec(STATUS_REJECTED),
    "transient": _ResultSpec(STATUS_FAILED_TRANSIENT),
    "failed_transient": _ResultSpec(STATUS_FAILED_TRANSIENT),
    "terminal_failed": _ResultSpec(STATUS_TERMINAL_FAILED, set_completed=True),
    "failed_permanent": _ResultSpec(STATUS_TERMINAL_FAILED, set_completed=True),
}


@dataclass(frozen=True, slots=True)
class LedgerRow:
    event_id: str
    target_id: str
    status: str
    attempt_count: int
    first_attempted_at: str | None
    last_attempted_at: str | None
    accepted_at: str | None
    completed_at: str | None
    server_drain_state: str | None
    last_http_status: int | None
    last_error: str | None
    last_response_json: str | None


def _coerce_result_token(result: object) -> str:
    if isinstance(result, str):
        token = result
    else:
        value = getattr(result, "value", None)
        name = getattr(result, "name", None)
        token = value if isinstance(value, str) else name if isinstance(name, str) else str(result)
    return token.strip().lower().replace("-", "_")


def _result_metadata(result: object) -> dict[str, Any]:
    if isinstance(result, str):
        return {}
    names = ("http_status", "error", "response_json", "server_drain_state", "at")
    return {name: getattr(result, name) for name in names if getattr(result, name, None) is not None}


def _stable_id(kind: str, *parts: str) -> str:
    # Durable database identities are a protocol key, not charter content.
    digest = hashlib.sha256("\0".join(parts).encode()).hexdigest()  # noqa: TID251
    return f"{kind}-{digest}"


def _require_project_destination(permit: LayoutWritePermit) -> None:
    if permit.destination is not LayoutDestination.PROJECT_STORE:
        raise RuntimeError("delivery writes require the project_only layout")


def init_ledger(unit: ProjectUnitOfWork) -> None:
    """Compatibility seam: aggregate schema creation belongs to ProjectSyncStore."""
    del unit


class SqliteDeliveryLedger:
    """Short-lived result adapter over one active project unit of work."""

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

    @contextmanager
    def transaction(self) -> Iterator[SqliteDeliveryLedger]:
        """Group inside the already-active store-owned outer transaction."""
        yield self

    def __enter__(self) -> SqliteDeliveryLedger:
        return self

    def __exit__(self, *exc: object) -> None:
        del exc

    def close(self) -> None:
        """No-op compatibility seam; the repository owns no connection."""

    def _journal_epoch(self, event_id: str) -> int:
        row = self._unit.execute(
            "SELECT epoch_id FROM journal_entries WHERE project_uuid = ? AND entry_id = ?",
            (self.project_uuid, event_id),
        ).fetchone()
        if row is None:
            raise ValueError("delivery result requires an event owned by this project store")
        return int(cast("str | int | float | bytes", row[0]))

    def _attempt_rows(self) -> list[tuple[Any, ...]]:
        return [
            tuple(row)
            for row in self._unit.execute(
                "SELECT attempt_id, epoch_id, target_generation, payload_reference, "
                "state, created_at FROM delivery_attempts WHERE project_uuid = ? "
                "ORDER BY created_at, attempt_id",
                (self.project_uuid,),
            ).fetchall()
        ]

    def _row_from_attempt(self, row: tuple[Any, ...]) -> LedgerRow:
        metadata: Any = json.loads(str(row[3] or "{}"))
        if not isinstance(metadata, dict):
            raise ValueError("delivery attempt metadata is not an object")
        return LedgerRow(
            event_id=str(metadata["event_id"]),
            target_id=str(metadata["target_id"]),
            status=str(metadata["status"]),
            attempt_count=int(metadata["attempt_count"]),
            first_attempted_at=metadata.get("first_attempted_at"),
            last_attempted_at=metadata.get("last_attempted_at"),
            accepted_at=metadata.get("accepted_at"),
            completed_at=metadata.get("completed_at"),
            server_drain_state=metadata.get("server_drain_state"),
            last_http_status=metadata.get("last_http_status"),
            last_error=metadata.get("last_error"),
            last_response_json=metadata.get("last_response_json"),
        )

    def get(self, event_id: str, target_id: str) -> LedgerRow | None:
        for attempt in self._attempt_rows():
            row = self._row_from_attempt(attempt)
            if row.event_id == event_id and row.target_id == target_id:
                return row
        return None

    def _record(
        self,
        event_id: str,
        target_id: str,
        *,
        status: str,
        at: str | None = None,
        http_status: int | None = None,
        error: str | None = None,
        response_json: str | None = None,
        server_drain_state: str | None = None,
        set_accepted: bool = False,
        set_completed: bool = False,
        test_hooks: LayoutTestHooks | None = None,
    ) -> str:
        epoch_id = self._journal_epoch(event_id)
        now = at or now_utc_iso()

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            previous = self.get(event_id, target_id)
            effective_status = status
            if status == STATUS_SUCCESS and previous is not None and previous.status in TERMINAL_SUCCESS_STATUSES:
                effective_status = STATUS_DUPLICATE
            task_row = self._unit.execute(
                "SELECT task_id FROM outbox_tasks WHERE project_uuid = ? AND journal_entry_id = ? AND task_kind = 'event' ORDER BY task_id LIMIT 1",
                (self.project_uuid, event_id),
            ).fetchone()
            task_id = str(task_row[0]) if task_row is not None else f"event:{event_id}"
            if task_row is None:
                self._unit.execute(
                    "INSERT INTO outbox_tasks "
                    "(task_id, project_uuid, epoch_id, journal_entry_id, task_kind, state, "
                    "idempotency_identity, created_at) VALUES (?, ?, ?, ?, 'event', "
                    "'pending', ?, ?)",
                    (task_id, self.project_uuid, epoch_id, event_id, event_id, now),
                )
            attempt_id = _stable_id("attempt", self.project_uuid, event_id, target_id)
            first = previous.first_attempted_at if previous is not None else now
            metadata = {
                "event_id": event_id,
                "target_id": target_id,
                "status": effective_status,
                "attempt_count": (previous.attempt_count if previous is not None else 0) + 1,
                "first_attempted_at": first,
                "last_attempted_at": now,
                "accepted_at": now if set_accepted else previous.accepted_at if previous else None,
                "completed_at": now if set_completed else previous.completed_at if previous else None,
                "server_drain_state": server_drain_state or (previous.server_drain_state if previous else None),
                "last_http_status": http_status if http_status is not None else previous.last_http_status if previous else None,
                "last_error": error if error is not None else previous.last_error if previous else None,
                "last_response_json": response_json if response_json is not None else previous.last_response_json if previous else None,
            }
            reference = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
            attempt_state = "terminal" if effective_status in TERMINAL_STATUSES else effective_status
            self._unit.execute(
                "INSERT INTO delivery_attempts "
                "(attempt_id, project_uuid, epoch_id, outbox_task_id, target_generation, "
                "payload_reference, state, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(attempt_id) DO UPDATE SET payload_reference = excluded.payload_reference, "
                "state = excluded.state, target_generation = excluded.target_generation",
                (
                    attempt_id,
                    self.project_uuid,
                    epoch_id,
                    task_id,
                    target_id,
                    reference,
                    attempt_state,
                    first,
                ),
            )
            result_id = _stable_id("result", attempt_id)
            self._unit.execute(
                "INSERT INTO delivery_results "
                "(result_id, project_uuid, epoch_id, attempt_id, target_generation, "
                "outcome, terminal_refusal_category, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(result_id) DO UPDATE SET outcome = excluded.outcome, "
                "terminal_refusal_category = excluded.terminal_refusal_category, "
                "recorded_at = excluded.recorded_at",
                (
                    result_id,
                    self.project_uuid,
                    epoch_id,
                    attempt_id,
                    target_id,
                    effective_status,
                    error if effective_status == STATUS_TERMINAL_FAILED else None,
                    now,
                ),
            )

        self._authority.execute_write(
            self._authority.issue_write_permit(),
            write,
            test_hooks=test_hooks,
        )
        current = self.get(event_id, target_id)
        if current is None:  # pragma: no cover - transaction invariant
            raise RuntimeError("delivery write completed without a result row")
        return current.status

    def _is_terminal_success(self, event_id: str, target_id: str) -> bool:
        row = self.get(event_id, target_id)
        return row is not None and row.status in TERMINAL_SUCCESS_STATUSES

    def record_success(self, event_id: str, target_id: str, **metadata: Any) -> str:
        return self._record(event_id, target_id, status=STATUS_SUCCESS, set_completed=True, **metadata)

    def record_duplicate(self, event_id: str, target_id: str, **metadata: Any) -> str:
        return self._record(event_id, target_id, status=STATUS_DUPLICATE, set_completed=True, **metadata)

    def record_pending(
        self,
        event_id: str,
        target_id: str,
        *,
        server_drain_state: str = "pending",
        at: str | None = None,
    ) -> str:
        return self._record(
            event_id,
            target_id,
            status=STATUS_PENDING,
            server_drain_state=server_drain_state,
            at=at,
            set_accepted=True,
        )

    def record_rejected(self, event_id: str, target_id: str, **metadata: Any) -> str:
        return self._record(event_id, target_id, status=STATUS_REJECTED, **metadata)

    def record_transient(self, event_id: str, target_id: str, **metadata: Any) -> str:
        return self._record(event_id, target_id, status=STATUS_FAILED_TRANSIENT, **metadata)

    def record_terminal_failed(self, event_id: str, target_id: str, **metadata: Any) -> str:
        return self._record(
            event_id,
            target_id,
            status=STATUS_TERMINAL_FAILED,
            set_completed=True,
            **metadata,
        )

    def record_result(self, *, event_id: str, target_id: str, result: object) -> None:
        token = _coerce_result_token(result)
        spec = _RESULT_STATUS_SPEC.get(token)
        if spec is None:
            raise ValueError(f"unknown delivery result vocabulary: {token!r}")
        metadata = _result_metadata(result)
        self._record(
            event_id,
            target_id,
            status=spec.status,
            set_accepted=spec.set_accepted,
            set_completed=spec.set_completed,
            server_drain_state=spec.server_drain_state,
            **metadata,
        )

    def select_pending(self, *, target_id: str, limit: int) -> Sequence[str]:
        return [
            row.event_id
            for row in (self._row_from_attempt(attempt) for attempt in self._attempt_rows())
            if row.target_id == target_id and row.status not in TERMINAL_STATUSES
        ][:limit]

    def _ordinary_eligible_ids(self, universe: Iterable[str]) -> list[str]:
        wanted = list(universe)
        if not wanted:
            return []
        placeholders = ", ".join("?" for _ in wanted)
        rows = self._unit.execute(
            f"SELECT journal_entries.entry_id FROM journal_entries "  # noqa: S608 - count-derived placeholders only
            "JOIN consent_epochs ON consent_epochs.project_uuid = journal_entries.project_uuid "
            "AND consent_epochs.epoch_id = journal_entries.epoch_id "
            f"WHERE journal_entries.project_uuid = ? AND journal_entries.entry_id IN ({placeholders}) "
            "AND consent_epochs.state = 'eligible' ORDER BY journal_entries.capture_sequence",
            (self.project_uuid, *wanted),
        ).fetchall()
        allowed = {str(row[0]) for row in rows}
        return [event_id for event_id in wanted if event_id in allowed]

    def select_undelivered(
        self,
        *,
        target_id: str,
        event_universe: Iterable[str],
        limit: int | None = None,
        history_action: HistoryDisclosureCapability | None = None,
    ) -> list[str]:
        if history_action is None:
            universe = self._ordinary_eligible_ids(event_universe)
        else:
            capability = revalidate_history_disclosure(self._unit, history_action)
            authorized = set(capability.row_ids)
            universe = [event_id for event_id in event_universe if event_id in authorized]
        terminal_for_target = {
            row.event_id
            for row in (self._row_from_attempt(attempt) for attempt in self._attempt_rows())
            if (row.target_id == target_id and row.status in TERMINAL_SUCCESS_STATUSES) or row.status == STATUS_TERMINAL_FAILED
        }
        selected = [event_id for event_id in universe if event_id not in terminal_for_target]
        return selected if limit is None else selected[:limit]

    def delivered_anywhere(self, event_id: str) -> bool:
        return any(
            self._row_from_attempt(attempt).event_id == event_id and self._row_from_attempt(attempt).status in TERMINAL_SUCCESS_STATUSES
            for attempt in self._attempt_rows()
        )

    def delivered_to_target(self, event_id: str, target_id: str) -> bool:
        row = self.get(event_id, target_id)
        return row is not None and row.status in TERMINAL_SUCCESS_STATUSES

    def rows(self) -> list[LedgerRow]:
        """Return this explicit project's payload-free result projection."""
        return [self._row_from_attempt(attempt) for attempt in self._attempt_rows()]


__all__ = [
    "LEDGER_INDEX_NAME",
    "LEDGER_TABLE",
    "LedgerRow",
    "STATUS_DUPLICATE",
    "STATUS_FAILED_TRANSIENT",
    "STATUS_PENDING",
    "STATUS_REJECTED",
    "STATUS_SUCCESS",
    "STATUS_TERMINAL_FAILED",
    "TERMINAL_STATUSES",
    "TERMINAL_SUCCESS_STATUSES",
    "SqliteDeliveryLedger",
    "init_ledger",
]
