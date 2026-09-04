"""Project-scoped transport/result lease for hosted-sync egress.

The lease is intentionally outside SQLite: :class:`ProjectSyncStore` already owns
the aggregate transaction, while this sibling file lock serializes the final
eligibility check, transport start, and result recording across processes.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from filelock import FileLock

from specify_cli.core.checkout_file_lock import acquire_or_raise

from specify_cli.sync.feature_flags import is_saas_sync_enabled
from specify_cli.sync.project_context import (
    AdmissionState,
    ConsentState,
    ProjectSyncContext,
    TargetAudience,
    _new_project_sync_context,
)
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import (
    ProjectStoreError,
    ProjectStoreLockedError,
    ProjectSyncStore,
    ProjectUnitOfWork,
    _stored_positive_int,
)


@dataclass(frozen=True, slots=True)
class _LiveLeaseRegistration:
    owner_pid: int
    project_uuid: str
    lock_path: Path


_LIVE_LEASES: dict[str, _LiveLeaseRegistration] = {}
_LIVE_LEASES_LOCK = Lock()


@dataclass(frozen=True, slots=True)
class TransportLeaseContext:
    """One open project transport lease and its non-forgeable identity."""

    store: ProjectSyncStore
    lease_identity: str
    lock_path: Path

    @contextmanager
    def unit_of_work(self) -> Iterator[tuple[ProjectUnitOfWork, ProjectSyncContext]]:
        """Yield one active store unit plus a lease-bound eligibility context."""
        if not transport_lease_context_is_live(self):
            raise ProjectStoreError("project transport lease context does not match the live lease")
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
    label = lease_identity or "transport-lease"
    if not label.strip():
        raise ValueError("transport lease identity must be non-empty")
    identity = f"{label}:pid:{os.getpid()}:acquisition:{uuid.uuid4()}"

    path = store.egress_lock_path
    lock = FileLock(path)
    acquire_or_raise(
        lock,
        path,
        timeout_seconds=lock_timeout_seconds,
        build_timeout_error=lambda: ProjectStoreLockedError("project transport lease is locked"),
    )
    try:
        try:
            _register_live_lease(
                identity,
                project_uuid=store.project_uuid,
                lock_path=path,
            )
            yield TransportLeaseContext(store=store, lease_identity=identity, lock_path=path)
        finally:
            _unregister_live_lease(identity)
    finally:
        lock.release()


def transport_lease_is_live(lease_identity: str | None) -> bool:
    """Return whether this process still owns the OS-backed lease identity.

    The durable start/result protocol must not accept a cached
    ``ProjectSyncContext`` after ``acquire_project_transport_lease`` has exited.
    Keeping the liveness registry process-local deliberately makes a copied
    identity useless in another process and after OS lock release.
    """
    if lease_identity is None:
        return False
    with _LIVE_LEASES_LOCK:
        registration = _LIVE_LEASES.get(lease_identity)
    return registration is not None and registration.owner_pid == os.getpid()


def transport_lease_identity_is_live_for_project(
    lease_identity: str | None,
    project_uuid: CanonicalProjectUUID,
) -> bool:
    """Return whether an identity is live and bound to this exact project."""
    if lease_identity is None:
        return False
    with _LIVE_LEASES_LOCK:
        registration = _LIVE_LEASES.get(lease_identity)
    return bool(registration is not None and registration.owner_pid == os.getpid() and registration.project_uuid == project_uuid.storage_token)


def transport_lease_context_is_live(lease: TransportLeaseContext) -> bool:
    """Return whether a context matches its registered project and lock path."""
    with _LIVE_LEASES_LOCK:
        registration = _LIVE_LEASES.get(lease.lease_identity)
    if registration is None or registration.owner_pid != os.getpid():
        return False
    registered_path = registration.lock_path.resolve(strict=False)
    return bool(
        registration.project_uuid == lease.store.project_uuid.storage_token
        and registered_path == lease.lock_path.resolve(strict=False)
        and registered_path == lease.store.egress_lock_path.resolve(strict=False)
    )


def _register_live_lease(
    lease_identity: str,
    *,
    project_uuid: CanonicalProjectUUID,
    lock_path: Path,
) -> None:
    with _LIVE_LEASES_LOCK:
        _LIVE_LEASES[lease_identity] = _LiveLeaseRegistration(
            owner_pid=os.getpid(),
            project_uuid=project_uuid.storage_token,
            lock_path=lock_path.resolve(strict=False),
        )


def _unregister_live_lease(lease_identity: str) -> None:
    with _LIVE_LEASES_LOCK:
        _LIVE_LEASES.pop(lease_identity, None)


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
        # Fail closed identically to create_context_from_unit: a corrupt
        # generation (0, negative, bool) must not pass validation only on the
        # egress-authorizing path.
        consent_generation = _stored_positive_int(consent_row[1], "consent generation")

    if consent_state is ConsentState.GRANTED and consent_generation is not None:
        epoch_row = unit.execute(
            "SELECT epoch_id FROM consent_epochs WHERE project_uuid = ? AND state = 'eligible' AND consent_generation = ? ORDER BY epoch_id DESC LIMIT 1",
            (project_uuid, consent_generation),
        ).fetchone()
        if epoch_row is not None:
            epoch_id = _stored_positive_int(epoch_row[0], "consent epoch id")

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
            configuration_generation=_stored_positive_int(admission_row[3], "configuration generation"),
        )
        admission_state = AdmissionState(str(admission_row[4]))
        admission_generation = str(admission_row[5]) if admission_row[5] is not None else None
        binding_audience = str(admission_row[6]) if admission_row[6] is not None else None

    kill_switch_allows = bool(
        is_saas_sync_enabled() and consent_state is ConsentState.GRANTED and epoch_id is not None and admission_state is AdmissionState.ADMITTED
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
    "transport_lease_context_is_live",
    "transport_lease_identity_is_live_for_project",
]
