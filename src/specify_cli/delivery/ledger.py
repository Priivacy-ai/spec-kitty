"""Connection-free delivery result repository for one project store."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, cast

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.delivery.receivers import TERMINAL_REJECTION_CATEGORIES
from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutGenerationAuthority,
    LayoutTestHooks,
    LayoutWritePermit,
)
from specify_cli.sync.project_context import VerifiedProjectStoreIdentity
from specify_cli.sync.project_store import ProjectUnitOfWork
from specify_cli.sync.transport_attempts import DeliveryAttemptProjection, list_delivery_attempt_projections
from specify_cli.sync.history_disclosure import (
    HistoryDisclosureCapability,
    revalidate_history_disclosure,
)

LEDGER_TABLE = "delivery_results"
LEDGER_INDEX_NAME = "project_store_delivery_results"
_LOG = logging.getLogger(__name__)

STATUS_SUCCESS = "success"
STATUS_DUPLICATE = "duplicate"
STATUS_PENDING = "pending"
STATUS_REJECTED = "rejected"
STATUS_FAILED_TRANSIENT = "failed_transient"
STATUS_TERMINAL_FAILED = "terminal_failed"
TERMINAL_SUCCESS_STATUSES = frozenset({STATUS_SUCCESS, STATUS_DUPLICATE})
TERMINAL_STATUSES = TERMINAL_SUCCESS_STATUSES | {STATUS_TERMINAL_FAILED}
_DISPATCHER_WRITE_KIND = "dispatcher_http_event"
_EVENT_WRITE_KIND = "event"
_DISPATCHER_REFERENCE_SCHEMA = "spec-kitty.dispatcher.v1"
# ``refused`` is the compatibility repository's pre-typed historical token.
# Every live server category comes from the receiver mapper's one vocabulary so
# selection cannot drift when the wire contract gains another terminal policy
# refusal (as happened with ``project_refused``).
_GLOBAL_TERMINAL_REFUSAL_CATEGORIES = frozenset({"refused", *TERMINAL_REJECTION_CATEGORIES})
_WP06_OUTCOME_STATUS = {
    "delivered": STATUS_SUCCESS,
    "duplicate": STATUS_DUPLICATE,
    "pending": STATUS_PENDING,
    "retryable_no_effect": STATUS_FAILED_TRANSIENT,
    "refused": STATUS_TERMINAL_FAILED,
    "terminal_unknown": STATUS_TERMINAL_FAILED,
    "unknown": STATUS_FAILED_TRANSIENT,
}


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
        savepoint = f"delivery_ledger_{id(self):x}"
        with self._unit.savepoint(savepoint):
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

    def _attempt_rows(self) -> list[DeliveryAttemptProjection]:
        rows: list[DeliveryAttemptProjection] = list_delivery_attempt_projections(self._unit)
        return rows

    def _result_for_attempt(self, attempt_id: str) -> tuple[str | None, str | None, str | None]:
        rows = self._unit.execute(
            "SELECT outcome, terminal_refusal_category, recorded_at FROM delivery_results "
            "WHERE project_uuid = ? AND attempt_id = ? ORDER BY recorded_at DESC, result_id DESC",
            (self.project_uuid, attempt_id),
        ).fetchall()
        if not rows:
            return None, None, None
        terminal = {
            (str(row[0]), str(row[1]) if row[1] is not None else None) for row in rows if str(row[0]) in {"delivered", "duplicate", "refused", "terminal_unknown"}
        }
        if len(terminal) > 1:
            raise ValueError("dispatcher delivery attempt has conflicting result history")
        if terminal:
            for row in rows:
                key = (str(row[0]), str(row[1]) if row[1] is not None else None)
                if key in terminal:
                    return (
                        str(row[0]) if row[0] is not None else None,
                        str(row[1]) if row[1] is not None else None,
                        str(row[2]) if row[2] is not None else None,
                    )
        row = rows[0]
        return (
            str(row[0]) if row[0] is not None else None,
            str(row[1]) if row[1] is not None else None,
            str(row[2]) if row[2] is not None else None,
        )

    def _row_from_dispatcher_attempt(self, attempt: DeliveryAttemptProjection) -> LedgerRow:
        if attempt.event_id is None or attempt.target_id is None or attempt.state is None:
            raise ValueError("dispatcher delivery attempt projection is missing event/target correlation")
        outcome, refusal, recorded_at = self._result_for_attempt(attempt.attempt_id)
        status = _WP06_OUTCOME_STATUS.get(str(outcome), STATUS_FAILED_TRANSIENT) if outcome is not None else STATUS_FAILED_TRANSIENT
        created_at = attempt.created_at
        completed_at = recorded_at if status in TERMINAL_STATUSES else None
        return LedgerRow(
            event_id=attempt.event_id,
            target_id=attempt.target_id,
            status=status,
            attempt_count=1,
            first_attempted_at=created_at,
            last_attempted_at=recorded_at or created_at,
            accepted_at=None,
            completed_at=completed_at,
            server_drain_state=None if status in TERMINAL_STATUSES else attempt.state.value,
            last_http_status=None,
            last_error=refusal,
            last_response_json=None,
        )

    def _row_from_attempt(self, attempt: DeliveryAttemptProjection) -> LedgerRow | None:
        if attempt.write_kind in {_DISPATCHER_WRITE_KIND, _EVENT_WRITE_KIND}:
            return self._row_from_dispatcher_attempt(attempt)
        metadata = attempt.legacy_metadata
        if metadata is None:
            return None
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
        matches: list[LedgerRow] = []
        for attempt in self._attempt_rows():
            row = self._row_from_attempt(attempt)
            if row is not None and row.event_id == event_id and row.target_id == target_id:
                matches.append(row)
        for row in matches:
            if row.status in TERMINAL_STATUSES:
                return row
        return matches[0] if matches else None

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
            if row is not None
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
        recovery_event_ids: frozenset[str] = frozenset(),
    ) -> list[str]:
        del recovery_event_ids
        if history_action is None:
            universe = self._ordinary_eligible_ids(event_universe)
        else:
            capability = revalidate_history_disclosure(self._unit, history_action)
            authorized = set(capability.row_ids)
            universe = [event_id for event_id in event_universe if event_id in authorized]
        terminal_for_target: set[str] = set()
        globally_parked: set[str] = set()
        for attempt in self._attempt_rows():
            row = self._row_from_attempt(attempt)
            if row is None:
                continue
            # A project-policy refusal is an event-level safety decision, not
            # evidence that one particular destination received the event. Keep
            # it parked when a later configuration resolves another target.
            # Other permanent delivery failures (notably a target-specific 413),
            # success, and duplicate remain target-scoped so retained history may
            # be deliberately re-delivered to another compatible destination.
            refusal_category = (row.last_error or "").strip().lower()
            if row.status == STATUS_TERMINAL_FAILED and refusal_category in _GLOBAL_TERMINAL_REFUSAL_CATEGORIES:
                globally_parked.add(row.event_id)
                continue
            if row.target_id != target_id:
                continue
            if row.status in TERMINAL_STATUSES:
                terminal_for_target.add(row.event_id)
                continue
            if row.server_drain_state == "retryable_no_effect":
                from specify_cli.sync.transport_attempts import RecoveryAction, plan_delivery_attempt_recovery

                try:
                    decision = plan_delivery_attempt_recovery(self._unit, attempt_id=attempt.attempt_id)
                except Exception:
                    terminal_for_target.add(row.event_id)
                    continue
                if decision.action is RecoveryAction.RETRY_NATIVE_IDENTITY and decision.may_resend:
                    continue
                terminal_for_target.add(row.event_id)
                continue
            if row.server_drain_state in {"in_flight", "pending_remote", "retryable_no_effect", "unknown"}:
                terminal_for_target.add(row.event_id)
        selected = [event_id for event_id in universe if event_id not in globally_parked and event_id not in terminal_for_target]
        return selected if limit is None else selected[:limit]

    def retryable_recovery_event_ids(
        self,
        *,
        target_id: str,
        event_universe: Iterable[str],
    ) -> frozenset[str]:
        """Return selected dispatcher events whose durable plan authorizes retry."""
        wanted = set(event_universe)
        recovery: set[str] = set()
        for attempt in self._attempt_rows():
            row = self._row_from_attempt(attempt)
            if row is None or row.target_id != target_id or row.event_id not in wanted:
                continue
            if row.server_drain_state != "retryable_no_effect":
                continue
            from specify_cli.sync.transport_attempts import RecoveryAction, plan_delivery_attempt_recovery

            try:
                decision = plan_delivery_attempt_recovery(self._unit, attempt_id=attempt.attempt_id)
            except Exception as exc:
                _LOG.debug("dispatcher retryable recovery planning failed for %s", row.event_id, exc_info=exc)
                continue
            if decision.action is RecoveryAction.RETRY_NATIVE_IDENTITY and decision.may_resend:
                recovery.add(row.event_id)
        return frozenset(recovery)

    def delivered_anywhere(self, event_id: str) -> bool:
        return any(
            row is not None and row.event_id == event_id and row.status in TERMINAL_SUCCESS_STATUSES
            for row in (self._row_from_attempt(attempt) for attempt in self._attempt_rows())
        )

    def delivered_to_target(self, event_id: str, target_id: str) -> bool:
        row = self.get(event_id, target_id)
        return row is not None and row.status in TERMINAL_SUCCESS_STATUSES

    def rows(self) -> list[LedgerRow]:
        """Return this explicit project's payload-free result projection."""
        return [row for row in (self._row_from_attempt(attempt) for attempt in self._attempt_rows()) if row is not None]


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
