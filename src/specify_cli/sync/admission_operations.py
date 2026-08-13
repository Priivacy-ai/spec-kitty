"""Durable project admission control-operation outbox and CAS service."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from kernel.clock import now_utc_iso
from enum import StrEnum
from typing import Literal, Protocol

from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.saas_client.admission import (
    AdmissionRequest,
    AdmissionResponse,
    AdmissionTransportUncertain,
)
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork, SQLiteRow
from specify_cli.sync.target_authority import AdmissionAudience

_PAYLOAD_VERSION = 1
_TERMINAL_STATES = frozenset({"acknowledged", "refused"})


class AdmissionOperationConflictError(RuntimeError):
    """An operation key was reused for different immutable request identity."""


class AdmissionAction(StrEnum):
    ADMIT = "admit"
    REVOKE = "revoke"


class AdmissionOperationState(StrEnum):
    PREPARED = "prepared"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    REFUSED = "refused"
    UNKNOWN = "unknown"


class AdmissionClient(Protocol):
    def execute(self, request: AdmissionRequest) -> AdmissionResponse: ...


@dataclass(frozen=True, slots=True)
class AdmissionOperationRecord:
    operation_key: str
    project_uuid: str
    action: AdmissionAction
    expected_generation: int | None
    audience: AdmissionAudience
    request_payload_hash: str
    request_payload_version: int
    state: AdmissionOperationState
    result_state: str | None
    result_generation: int | None
    binding_audience: str | None
    original_error_category: str | None
    attempts: int
    created_at: str
    updated_at: str


def _row_to_record(row: SQLiteRow) -> AdmissionOperationRecord:
    values = tuple(row)
    audience = AdmissionAudience(
        normalized_server_origin=str(values[4]),
        account_identity=str(values[5]),
        private_teamspace_id=str(values[6]),
        project_uuid=CanonicalProjectUUID.parse(str(values[1])),
        configuration_generation=int(values[7]),
    )
    return AdmissionOperationRecord(
        operation_key=str(values[0]),
        project_uuid=str(values[1]),
        action=AdmissionAction(str(values[2])),
        expected_generation=None if values[3] is None else int(values[3]),
        audience=audience,
        request_payload_hash=str(values[8]),
        request_payload_version=int(values[9]),
        state=AdmissionOperationState(str(values[10])),
        result_state=None if values[11] is None else str(values[11]),
        result_generation=None if values[12] is None else int(values[12]),
        binding_audience=None if values[13] is None else str(values[13]),
        original_error_category=None if values[14] is None else str(values[14]),
        attempts=int(values[15]),
        created_at=str(values[16]),
        updated_at=str(values[17]),
    )


_SELECT_OPERATION = (
    "SELECT operation_key, project_uuid, action, expected_generation, "
    "target_identity, account_identity, private_teamspace_id, "
    "configuration_generation, request_payload_hash, request_payload_version, "
    "state, result_state, result_generation, binding_audience, "
    "original_error_category, attempts, created_at, updated_at "
    "FROM admission_operations WHERE operation_key = ?"
)


def _payload_hash(request: AdmissionRequest, audience: AdmissionAudience) -> str:
    identity = {
        "version": _PAYLOAD_VERSION,
        "action": request.action,
        "source_project_uuid": request.source_project_uuid,
        "operation_key": request.operation_key,
        "expected_generation": request.expected_generation,
        "project_slug": request.project_slug,
        "audience": {
            "target_identity": audience.target_identity,
            "account_identity": audience.account_identity,
            "private_teamspace_id": audience.private_teamspace_id,
            "project_uuid": audience.project_uuid.storage_token,
            "configuration_generation": audience.configuration_generation,
        },
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()  # noqa: TID251 - durable admission request identity, not charter freshness


class AdmissionOperationService:
    """Prepare before I/O, reuse keys after uncertainty, retain first outcome."""

    def __init__(self, store: ProjectSyncStore, client: AdmissionClient) -> None:
        self.store = store
        self.client = client
        self.targets = ProjectDeliveryTargetRegistry(store)

    def _get(self, unit: ProjectUnitOfWork, operation_key: str) -> AdmissionOperationRecord | None:
        row = unit.execute(_SELECT_OPERATION, (operation_key,)).fetchone()
        return None if row is None else _row_to_record(row)

    @staticmethod
    def _same_identity(
        existing: AdmissionOperationRecord,
        *,
        request: AdmissionRequest,
        audience: AdmissionAudience,
        request_hash: str,
    ) -> bool:
        return (
            existing.project_uuid == request.source_project_uuid
            and existing.action.value == request.action
            and existing.expected_generation == request.expected_generation
            and existing.audience == audience
            and existing.request_payload_hash == request_hash
            and existing.request_payload_version == _PAYLOAD_VERSION
        )

    def _prepare(
        self,
        request: AdmissionRequest,
        audience: AdmissionAudience,
        request_hash: str,
    ) -> AdmissionOperationRecord:
        now = now_utc_iso()
        with self.store.unit_of_work() as unit:
            current_target = self.targets.get_current(unit)
            if current_target is None:
                self.targets.register(unit, audience)
            elif current_target.identity != self.targets.register(unit, audience).identity:
                raise AdmissionOperationConflictError("operation audience is not the current target")
            existing = self._get(unit, request.operation_key)
            if existing is not None:
                if not self._same_identity(
                    existing,
                    request=request,
                    audience=audience,
                    request_hash=request_hash,
                ):
                    raise AdmissionOperationConflictError("operation key is already bound to another action, audience, or payload")
                return existing
            unit.execute(
                "INSERT INTO admission_operations ("
                "operation_key, project_uuid, action, expected_generation, "
                "target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, request_payload_hash, request_payload_version, "
                "state, attempts, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'prepared', 0, ?, ?)",
                (
                    request.operation_key,
                    request.source_project_uuid,
                    request.action,
                    request.expected_generation,
                    audience.target_identity,
                    audience.account_identity,
                    audience.private_teamspace_id,
                    audience.configuration_generation,
                    request_hash,
                    _PAYLOAD_VERSION,
                    now,
                    now,
                ),
            )
            created = self._get(unit, request.operation_key)
            if created is None:  # pragma: no cover - insert checked in same UoW
                raise RuntimeError("admission operation did not persist")
            return created

    def _mark_sent(self, operation_key: str) -> AdmissionOperationRecord:
        now = now_utc_iso()
        with self.store.unit_of_work() as unit:
            unit.execute(
                "UPDATE admission_operations SET state = 'sent', attempts = attempts + 1, "
                "updated_at = ? WHERE operation_key = ? AND state NOT IN ('acknowledged', 'refused')",
                (now, operation_key),
            )
            record = self._get(unit, operation_key)
            if record is None:  # pragma: no cover - prepared immediately before
                raise RuntimeError("admission operation disappeared")
            return record

    def _mark_unknown(
        self,
        operation_key: str,
        *,
        action: AdmissionAction,
    ) -> AdmissionOperationRecord:
        now = now_utc_iso()
        with self.store.unit_of_work() as unit:
            unit.execute(
                "UPDATE admission_operations SET state = 'unknown', updated_at = ? WHERE operation_key = ? AND state NOT IN ('acknowledged', 'refused')",
                (now, operation_key),
            )
            if action is AdmissionAction.REVOKE:
                unit.execute(
                    "UPDATE project_target_admissions SET admission_state = 'revocation_pending', "
                    "last_error_category = 'remote_outcome_unknown' WHERE project_uuid = ?",
                    (self.store.project_uuid.storage_token,),
                )
            record = self._get(unit, operation_key)
            if record is None:  # pragma: no cover
                raise RuntimeError("admission operation disappeared")
            return record

    @staticmethod
    def _generation_matches(current: object, expected: int | None) -> bool:
        if current is None:
            return expected is None
        if expected is None:
            return False
        try:
            return int(str(current)) == expected
        except ValueError:
            return False

    def _record_response(
        self,
        operation_key: str,
        response: AdmissionResponse,
    ) -> AdmissionOperationRecord:
        now = now_utc_iso()
        with self.store.unit_of_work() as unit:
            existing = self._get(unit, operation_key)
            if existing is None:  # pragma: no cover
                raise RuntimeError("admission operation disappeared")
            if existing.state.value in _TERMINAL_STATES:
                return existing
            if response.error_category is not None:
                unit.execute(
                    "UPDATE admission_operations SET state = 'refused', "
                    "original_error_category = ?, updated_at = ? WHERE operation_key = ? "
                    "AND state NOT IN ('acknowledged', 'refused')",
                    (response.error_category, now, operation_key),
                )
                if existing.action is AdmissionAction.ADMIT:
                    unit.execute(
                        "UPDATE project_target_admissions SET admission_state = 'refused', "
                        "last_error_category = ? WHERE project_uuid = ? AND "
                        "target_identity = ? AND account_identity = ? AND "
                        "private_teamspace_id = ? AND configuration_generation = ?",
                        (
                            response.error_category,
                            existing.project_uuid,
                            existing.audience.target_identity,
                            existing.audience.account_identity,
                            existing.audience.private_teamspace_id,
                            existing.audience.configuration_generation,
                        ),
                    )
            else:
                if not response.admitted_or_revoked:
                    raise ValueError("admission response is neither success nor typed refusal")
                if response.source_project_uuid != existing.project_uuid:
                    raise ValueError("admission response belongs to another project")
                unit.execute(
                    "UPDATE admission_operations SET state = 'acknowledged', result_state = ?, "
                    "result_generation = ?, binding_audience = ?, updated_at = ? "
                    "WHERE operation_key = ? AND state NOT IN ('acknowledged', 'refused')",
                    (
                        response.state,
                        response.generation,
                        response.binding_audience,
                        now,
                        operation_key,
                    ),
                )
                current = unit.execute(
                    "SELECT target_identity, account_identity, private_teamspace_id, "
                    "configuration_generation, admission_generation "
                    "FROM project_target_admissions WHERE project_uuid = ?",
                    (existing.project_uuid,),
                ).fetchone()
                if current is not None:
                    values = tuple(current)
                    same_audience = values[:4] == (
                        existing.audience.target_identity,
                        existing.audience.account_identity,
                        existing.audience.private_teamspace_id,
                        existing.audience.configuration_generation,
                    )
                    if same_audience and self._generation_matches(values[4], existing.expected_generation):
                        state = "admitted" if response.state == "admitted" else "pending"
                        unit.execute(
                            "UPDATE project_target_admissions SET admission_state = ?, "
                            "admission_generation = ?, binding_audience = ?, "
                            "last_error_category = NULL WHERE project_uuid = ?",
                            (
                                state,
                                response.generation,
                                response.binding_audience,
                                existing.project_uuid,
                            ),
                        )
            recorded = self._get(unit, operation_key)
            if recorded is None:  # pragma: no cover
                raise RuntimeError("admission operation disappeared")
            return recorded

    def perform(
        self,
        *,
        action: AdmissionAction,
        audience: AdmissionAudience,
        operation_key: str,
        expected_generation: int | None = None,
        project_slug: str | None = None,
    ) -> AdmissionOperationRecord:
        if audience.project_uuid != self.store.project_uuid:
            raise ValueError("admission audience belongs to another project")
        if not 16 <= len(operation_key) <= 128:
            raise ValueError("operation key must contain 16 to 128 characters")
        if expected_generation is not None and expected_generation < 1:
            raise ValueError("expected generation must be positive")
        if action is AdmissionAction.REVOKE and expected_generation is None:
            raise ValueError("revocation requires an expected generation")
        request_action: Literal["admit", "revoke"] = "admit" if action is AdmissionAction.ADMIT else "revoke"
        request = AdmissionRequest(
            action=request_action,
            source_project_uuid=self.store.project_uuid.storage_token,
            operation_key=operation_key,
            expected_generation=expected_generation,
            project_slug=project_slug if action is AdmissionAction.ADMIT else None,
        )
        request_hash = _payload_hash(request, audience)
        prepared = self._prepare(request, audience, request_hash)
        if prepared.state in {
            AdmissionOperationState.ACKNOWLEDGED,
            AdmissionOperationState.REFUSED,
        }:
            return prepared
        self._mark_sent(operation_key)
        try:
            response = self.client.execute(request)
        except AdmissionTransportUncertain:
            return self._mark_unknown(operation_key, action=action)
        return self._record_response(operation_key, response)


__all__ = [
    "AdmissionTransportUncertain",
]
