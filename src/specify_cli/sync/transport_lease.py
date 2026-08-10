"""Project-scoped transport/result lease for hosted-sync egress.

The lease is intentionally outside SQLite: :class:`ProjectSyncStore` already owns
the aggregate transaction, while this sibling file lock serializes the final
eligibility check, transport start, and result recording across processes.
"""

from __future__ import annotations

import fcntl
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from specify_cli.sync.project_context import (
    AdmissionState,
    ConsentState,
    ProjectSyncContext,
    TargetAudience,
    _new_project_sync_context,
)
from specify_cli.sync.project_store import ProjectStoreLockedError, ProjectSyncStore, ProjectUnitOfWork


@dataclass(frozen=True, slots=True)
class TransportLeaseContext:
    """One open project transport lease and its non-forgeable identity."""

    store: ProjectSyncStore
    lease_identity: str
    lock_path: Path

    @contextmanager
    def unit_of_work(self) -> Iterator[tuple[ProjectUnitOfWork, ProjectSyncContext]]:
        """Yield one active store unit plus a lease-bound eligibility context."""
        with self.store.unit_of_work() as unit:
            yield unit, _lease_bound_context(unit, self.lease_identity)


@contextmanager
def acquire_project_transport_lease(
    store: ProjectSyncStore,
    *,
    lock_timeout_seconds: float = 5.0,
    lease_identity: str | None = None,
) -> Iterator[TransportLeaseContext]:
    """Acquire the per-project cross-process egress lease.

    The returned context does not by itself authorize transport. Callers must use
    :meth:`TransportLeaseContext.unit_of_work`, which re-reads current consent,
    target, admission, owner, and kill-switch state while the file lock is held.
    """
    if lock_timeout_seconds < 0:
        raise ValueError("lock timeout cannot be negative")
    identity = lease_identity or f"transport-lease:{uuid.uuid4()}"
    if not identity.strip():
        raise ValueError("transport lease identity must be non-empty")

    path = store.egress_lock_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        deadline = time.monotonic() + lock_timeout_seconds
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise ProjectStoreLockedError("project transport lease is locked") from exc
                time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        try:
            yield TransportLeaseContext(store=store, lease_identity=identity, lock_path=path)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _lease_bound_context(unit: ProjectUnitOfWork, lease_identity: str) -> ProjectSyncContext:
    """Rebuild current egress authority from one active unit under the lease."""
    project_uuid = unit.project_uuid.storage_token
    consent_state: ConsentState | None = None
    consent_generation: int | None = None
    epoch_id: int | None = None
    target_audience: TargetAudience | None = None
    admission_state: AdmissionState | None = None
    admission_generation: str | None = None
    binding_audience: str | None = None

    consent_row = unit.execute(
        "SELECT state, generation FROM project_consent_decisions WHERE project_uuid = ?",
        (project_uuid,),
    ).fetchone()
    if consent_row is not None:
        consent_state = ConsentState(str(consent_row[0]))
        consent_generation = int(consent_row[1])

    if consent_state is ConsentState.GRANTED and consent_generation is not None:
        epoch_row = unit.execute(
            "SELECT epoch_id FROM consent_epochs "
            "WHERE project_uuid = ? AND state = 'eligible' AND consent_generation = ? "
            "ORDER BY epoch_id DESC LIMIT 1",
            (project_uuid, consent_generation),
        ).fetchone()
        if epoch_row is not None:
            epoch_id = int(epoch_row[0])

    admission_row = unit.execute(
        "SELECT target_identity, account_identity, private_teamspace_id, "
        "configuration_generation, admission_state, admission_generation, "
        "binding_audience FROM project_target_admissions WHERE project_uuid = ?",
        (project_uuid,),
    ).fetchone()
    if admission_row is not None:
        target_audience = TargetAudience(
            project_uuid=unit.project_uuid,
            target_identity=str(admission_row[0]),
            account_identity=str(admission_row[1]),
            private_teamspace_id=str(admission_row[2]),
            configuration_generation=int(admission_row[3]),
        )
        admission_state = AdmissionState(str(admission_row[4]))
        admission_generation = str(admission_row[5]) if admission_row[5] is not None else None
        binding_audience = str(admission_row[6]) if admission_row[6] is not None else None

    kill_switch_allows = bool(
        consent_state is ConsentState.GRANTED
        and epoch_id is not None
        and admission_state is AdmissionState.ADMITTED
    )
    return _new_project_sync_context(
        store_identity=unit.store_identity,
        consent_state=consent_state,
        consent_generation=consent_generation,
        epoch_id=epoch_id,
        target_audience=target_audience,
        admission_state=admission_state,
        admission_generation=admission_generation,
        binding_audience=binding_audience,
        kill_switch_allows=kill_switch_allows,
        transport_lease_identity=lease_identity if kill_switch_allows else None,
    )


__all__ = [
    "TransportLeaseContext",
    "acquire_project_transport_lease",
]
