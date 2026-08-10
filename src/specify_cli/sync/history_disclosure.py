"""Preview, confirm, and consume immutable sealed-history disclosure authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from .project_context import AdmissionState, ConsentState, ProjectSyncContext
from .project_store import ProjectSyncStore, ProjectUnitOfWork


class HistoryDisclosureError(RuntimeError):
    """A history preview, confirmation, or authority revalidation failed closed."""


@dataclass(frozen=True, slots=True)
class HistoryDisclosurePreview:
    """Exact local cohort shown to an operator before confirmation."""

    project_uuid: str
    row_ids: tuple[str, ...]
    source_epoch_ids: tuple[int, ...]
    preview_count: int
    preview_hash: str


@dataclass(frozen=True, slots=True, init=False)
class HistoryDisclosureCapability:
    """Persisted, revalidated authority to process one exact sealed cohort."""

    action_id: str
    project_uuid: str
    row_ids: tuple[str, ...]
    source_epoch_ids: tuple[int, ...]
    preview_hash: str
    consent_generation: int
    target_generation: int
    admission_generation: str
    binding_audience: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("history capabilities are created by explicit confirmation")


def _new_capability(
    *,
    action_id: str,
    project_uuid: str,
    row_ids: tuple[str, ...],
    source_epoch_ids: tuple[int, ...],
    preview_hash: str,
    consent_generation: int,
    target_generation: int,
    admission_generation: str,
    binding_audience: str,
) -> HistoryDisclosureCapability:
    capability = object.__new__(HistoryDisclosureCapability)
    values: dict[str, object] = {
        "action_id": action_id,
        "project_uuid": project_uuid,
        "row_ids": row_ids,
        "source_epoch_ids": source_epoch_ids,
        "preview_hash": preview_hash,
        "consent_generation": consent_generation,
        "target_generation": target_generation,
        "admission_generation": admission_generation,
        "binding_audience": binding_audience,
    }
    for name, value in values.items():
        object.__setattr__(capability, name, value)
    return capability


def _cohort_rows(
    unit: ProjectUnitOfWork,
    *,
    source_epoch_ids: tuple[int, ...] | None = None,
) -> list[tuple[str, int, str]]:
    rows = unit.execute(
        "SELECT j.entry_id, j.epoch_id, j.payload_json "
        "FROM journal_entries AS j JOIN consent_epochs AS e "
        "ON e.project_uuid = j.project_uuid AND e.epoch_id = j.epoch_id "
        "WHERE j.project_uuid = ? AND e.state = 'sealed' "
        "AND NOT EXISTS (SELECT 1 FROM outbox_tasks AS o "
        "WHERE o.project_uuid = j.project_uuid "
        "AND o.journal_entry_id = j.entry_id "
        "AND o.state IN ('complete', 'terminal_refused', 'purged', 'canceled')) "
        "ORDER BY j.capture_sequence, j.entry_id",
        (unit.project_uuid.storage_token,),
    ).fetchall()
    selected_epochs = frozenset(source_epoch_ids) if source_epoch_ids is not None else None
    return [(str(row[0]), int(row[1]), str(row[2])) for row in rows if selected_epochs is None or int(row[1]) in selected_epochs]


def _preview_from_rows(
    project_uuid: str,
    rows: list[tuple[str, int, str]],
) -> HistoryDisclosurePreview:
    identities = [
        {
            # FR-028 binds the preview to exact row-content SHA-256 identities.
            "content_hash": hashlib.sha256(payload.encode()).hexdigest(),  # noqa: TID251
            "row_id": row_id,
        }
        for row_id, _epoch_id, payload in rows
    ]
    # FR-028 requires a stable SHA-256 aggregate for the exact preview cohort.
    preview_hash = hashlib.sha256(  # noqa: TID251
        json.dumps(
            identities,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    ).hexdigest()
    return HistoryDisclosurePreview(
        project_uuid=project_uuid,
        row_ids=tuple(row[0] for row in rows),
        source_epoch_ids=tuple(sorted({row[1] for row in rows})),
        preview_count=len(rows),
        preview_hash=preview_hash,
    )


def preview_sealed_history(store: ProjectSyncStore) -> HistoryDisclosurePreview:
    """Compute a stable exact cohort without persisting or widening eligibility."""
    with store.unit_of_work() as unit:
        rows = _cohort_rows(unit)
    return _preview_from_rows(store.project_uuid.storage_token, rows)


def _require_current_authority(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
) -> tuple[int, int, str, str]:
    canonical = unit.project_uuid.storage_token
    if context.project_uuid.storage_token != canonical:
        raise HistoryDisclosureError("history authority belongs to another project")
    if (
        context.consent_state is not ConsentState.GRANTED
        or context.consent_generation is None
        or context.target_audience is None
        or context.admission_state is not AdmissionState.ADMITTED
        or context.admission_generation is None
        or context.binding_audience is None
    ):
        raise HistoryDisclosureError("history confirmation requires current consent, target, and admission")
    consent_row = unit.execute(
        "SELECT state, generation FROM project_consent_decisions WHERE project_uuid = ?",
        (canonical,),
    ).fetchone()
    target_row = unit.execute(
        "SELECT configuration_generation, admission_state, admission_generation, binding_audience FROM project_target_admissions WHERE project_uuid = ?",
        (canonical,),
    ).fetchone()
    if consent_row != (ConsentState.GRANTED.value, context.consent_generation):
        raise HistoryDisclosureError("consent generation changed; preview again")
    expected_target = (
        context.target_audience.configuration_generation,
        AdmissionState.ADMITTED.value,
        context.admission_generation,
        context.binding_audience,
    )
    if target_row != expected_target:
        raise HistoryDisclosureError("target or admission generation changed; preview again")
    return (
        context.consent_generation,
        context.target_audience.configuration_generation,
        context.admission_generation,
        context.binding_audience,
    )


def _assert_preview_unchanged(
    unit: ProjectUnitOfWork,
    preview: HistoryDisclosurePreview,
) -> None:
    current = _preview_from_rows(
        unit.project_uuid.storage_token,
        _cohort_rows(unit, source_epoch_ids=preview.source_epoch_ids),
    )
    if current != preview:
        raise HistoryDisclosureError("history cohort changed after preview; inspect local rows and preview again")


def confirm_history_disclosure(
    store: ProjectSyncStore,
    preview: HistoryDisclosurePreview,
    *,
    actor: str,
    idempotency_key: str,
    context: ProjectSyncContext,
) -> HistoryDisclosureCapability:
    """Persist explicit confirmation for exactly the previewed sealed cohort."""
    if preview.project_uuid != store.project_uuid.storage_token:
        raise HistoryDisclosureError("history preview belongs to another project")
    provenance = actor.strip()
    key = idempotency_key.strip()
    if not provenance or not key:
        raise ValueError("history actor and idempotency key must be non-empty")
    # FR-028 requires stable action identity for the explicit idempotency key.
    action_id = (
        "history-"
        + hashlib.sha256(  # noqa: TID251
            f"{preview.project_uuid}\0{key}".encode()
        ).hexdigest()
    )
    with store.unit_of_work() as unit:
        _assert_preview_unchanged(unit, preview)
        consent_generation, target_generation, admission_generation, binding = _require_current_authority(unit, context)
        existing = unit.execute(
            "SELECT action_id, source_epoch_ids_json, row_ids_json, preview_count, "
            "preview_hash, confirmed_by, consent_generation, target_generation, "
            "admission_generation, binding_audience, state "
            "FROM history_disclosure_actions WHERE project_uuid = ? "
            "AND idempotency_key = ?",
            (preview.project_uuid, key),
        ).fetchone()
        expected = (
            action_id,
            json.dumps(preview.source_epoch_ids, separators=(",", ":")),
            json.dumps(preview.row_ids, separators=(",", ":")),
            preview.preview_count,
            preview.preview_hash,
            provenance,
            consent_generation,
            target_generation,
            admission_generation,
            binding,
            "confirmed",
        )
        if existing is not None and tuple(existing) != expected:
            raise HistoryDisclosureError("history idempotency key already names a different confirmation")
        if existing is None:
            unit.execute(
                "INSERT INTO history_disclosure_actions "
                "(action_id, project_uuid, idempotency_key, source_epoch_ids_json, "
                "row_ids_json, preview_count, preview_hash, confirmed_by, "
                "confirmed_at, consent_generation, target_generation, "
                "admission_generation, binding_audience, state) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed')",
                (
                    action_id,
                    preview.project_uuid,
                    key,
                    expected[1],
                    expected[2],
                    preview.preview_count,
                    preview.preview_hash,
                    provenance,
                    datetime.now(UTC).isoformat(),
                    consent_generation,
                    target_generation,
                    admission_generation,
                    binding,
                ),
            )
    return _new_capability(
        action_id=action_id,
        project_uuid=preview.project_uuid,
        row_ids=preview.row_ids,
        source_epoch_ids=preview.source_epoch_ids,
        preview_hash=preview.preview_hash,
        consent_generation=consent_generation,
        target_generation=target_generation,
        admission_generation=admission_generation,
        binding_audience=binding,
    )


def consume_history_disclosure(
    store: ProjectSyncStore,
    *,
    action_id: str,
    context: ProjectSyncContext,
) -> HistoryDisclosureCapability:
    """Revalidate persisted cohort and authority before returning a capability."""
    with store.unit_of_work() as unit:
        current_authority = _require_current_authority(unit, context)
        row = unit.execute(
            "SELECT source_epoch_ids_json, row_ids_json, preview_count, preview_hash, "
            "consent_generation, target_generation, admission_generation, "
            "binding_audience, state FROM history_disclosure_actions "
            "WHERE project_uuid = ? AND action_id = ?",
            (store.project_uuid.storage_token, action_id),
        ).fetchone()
        if row is None or str(row[8]) != "confirmed":
            raise HistoryDisclosureError("history action is absent or no longer confirmed; preview again")
        try:
            source_epochs = tuple(int(value) for value in json.loads(str(row[0])))
            row_ids = tuple(str(value) for value in json.loads(str(row[1])))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HistoryDisclosureError("history action cohort is incompatible") from exc
        preview = HistoryDisclosurePreview(
            project_uuid=store.project_uuid.storage_token,
            row_ids=row_ids,
            source_epoch_ids=source_epochs,
            preview_count=int(row[2]),
            preview_hash=str(row[3]),
        )
        _assert_preview_unchanged(unit, preview)
        persisted_authority = (int(row[4]), int(row[5]), str(row[6]), str(row[7]))
        if persisted_authority != current_authority:
            raise HistoryDisclosureError("history action authority is stale; preview and confirm again")
    return _new_capability(
        action_id=action_id,
        project_uuid=preview.project_uuid,
        row_ids=preview.row_ids,
        source_epoch_ids=preview.source_epoch_ids,
        preview_hash=preview.preview_hash,
        consent_generation=persisted_authority[0],
        target_generation=persisted_authority[1],
        admission_generation=persisted_authority[2],
        binding_audience=persisted_authority[3],
    )


def revalidate_history_disclosure(
    unit: ProjectUnitOfWork,
    capability: HistoryDisclosureCapability,
) -> HistoryDisclosureCapability:
    """Revalidate a persisted capability inside the caller's active store UoW."""
    if not isinstance(capability, HistoryDisclosureCapability):
        raise TypeError("history disclosure capability must come from explicit confirmation")
    project_uuid = unit.project_uuid.storage_token
    if capability.project_uuid != project_uuid:
        raise HistoryDisclosureError("history disclosure capability belongs to another project")
    row = unit.execute(
        "SELECT source_epoch_ids_json, row_ids_json, preview_count, preview_hash, "
        "consent_generation, target_generation, admission_generation, "
        "binding_audience, state FROM history_disclosure_actions "
        "WHERE project_uuid = ? AND action_id = ?",
        (project_uuid, capability.action_id),
    ).fetchone()
    if row is None or str(row[8]) != "confirmed":
        raise HistoryDisclosureError("history action is absent or no longer confirmed; preview again")
    try:
        source_epochs = tuple(int(value) for value in json.loads(str(row[0])))
        row_ids = tuple(str(value) for value in json.loads(str(row[1])))
        preview_count = int(row[2])
        persisted_authority = (
            int(row[4]),
            int(row[5]),
            str(row[6]),
            str(row[7]),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HistoryDisclosureError("history action cohort is incompatible") from exc
    expected_capability = (
        row_ids,
        source_epochs,
        str(row[3]),
        *persisted_authority,
    )
    actual_capability = (
        capability.row_ids,
        capability.source_epoch_ids,
        capability.preview_hash,
        capability.consent_generation,
        capability.target_generation,
        capability.admission_generation,
        capability.binding_audience,
    )
    if actual_capability != expected_capability:
        raise HistoryDisclosureError("history disclosure capability does not match its persisted action")
    consent_row = unit.execute(
        "SELECT state, generation FROM project_consent_decisions WHERE project_uuid = ?",
        (project_uuid,),
    ).fetchone()
    target_row = unit.execute(
        "SELECT configuration_generation, admission_state, admission_generation, binding_audience FROM project_target_admissions WHERE project_uuid = ?",
        (project_uuid,),
    ).fetchone()
    if consent_row != (ConsentState.GRANTED.value, capability.consent_generation) or target_row != (
        capability.target_generation,
        AdmissionState.ADMITTED.value,
        capability.admission_generation,
        capability.binding_audience,
    ):
        raise HistoryDisclosureError("history disclosure authority is stale; preview and confirm again")
    preview = HistoryDisclosurePreview(
        project_uuid=project_uuid,
        row_ids=row_ids,
        source_epoch_ids=source_epochs,
        preview_count=preview_count,
        preview_hash=str(row[3]),
    )
    _assert_preview_unchanged(unit, preview)
    return capability


__all__ = [
    "HistoryDisclosureCapability",
    "HistoryDisclosureError",
    "HistoryDisclosurePreview",
    "confirm_history_disclosure",
    "consume_history_disclosure",
    "preview_sealed_history",
    "revalidate_history_disclosure",
]
