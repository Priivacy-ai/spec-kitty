"""Immutable operation context and narrow project-store capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from specify_cli.sync.project_identity import CanonicalProjectUUID


class ConsentState(StrEnum):
    """Authoritative project consent states."""

    GRANTED = "granted"
    REFUSED = "refused"


class AdmissionState(StrEnum):
    """SaaS admission states for one exact target audience."""

    PENDING = "pending"
    ADMITTED = "admitted"
    REFUSED = "refused"
    REVOCATION_PENDING = "revocation_pending"


@dataclass(frozen=True, slots=True, init=False)
class VerifiedProjectStoreIdentity:
    """Store owner and version tuple verified during the current open."""

    project_uuid: CanonicalProjectUUID
    database_path: Path
    schema_version: int
    layout_version: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("verified store identities are created by ProjectSyncStore")


@dataclass(frozen=True, slots=True)
class TargetAudience:
    """Exact immutable target/account/Private-Teamspace binding."""

    project_uuid: CanonicalProjectUUID | str
    target_identity: str
    account_identity: str
    private_teamspace_id: str
    configuration_generation: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "project_uuid",
            CanonicalProjectUUID.parse(self.project_uuid),
        )
        if not all(
            value.strip()
            for value in (
                self.target_identity,
                self.account_identity,
                self.private_teamspace_id,
            )
        ):
            raise ValueError("target audience identities must be non-empty")
        if self.configuration_generation < 1:
            raise ValueError("target configuration generation must be positive")


@dataclass(frozen=True, slots=True, init=False)
class ProjectCaptureCapability:
    """Narrow authority to capture locally for this verified project store."""

    project_uuid: CanonicalProjectUUID
    store_identity: VerifiedProjectStoreIdentity
    epoch_id: int | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("capture capabilities are derived from ProjectSyncContext")


@dataclass(frozen=True, slots=True, init=False)
class ProjectStoreMaintenanceCapability:
    """Narrow authority for project-scoped store maintenance."""

    project_uuid: CanonicalProjectUUID
    store_identity: VerifiedProjectStoreIdentity

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("maintenance capabilities are derived from ProjectSyncContext")


@dataclass(frozen=True, slots=True, init=False)
class ProjectSyncContext:
    """Coherent immutable authority snapshot constructed by ProjectSyncStore."""

    project_uuid: CanonicalProjectUUID
    store_identity: VerifiedProjectStoreIdentity
    consent_state: ConsentState | None
    consent_generation: int | None
    epoch_id: int | None
    target_audience: TargetAudience | None
    admission_state: AdmissionState | None
    admission_generation: str | None
    binding_audience: str | None
    kill_switch_allows: bool
    transport_lease_identity: str | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("sync contexts are created by ProjectSyncStore")

    @property
    def egress_eligible(self) -> bool:
        """Evaluate current authority without mutating any decision."""
        return (
            self.consent_state is ConsentState.GRANTED
            and self.consent_generation is not None
            and self.epoch_id is not None
            and self.target_audience is not None
            and self.admission_state is AdmissionState.ADMITTED
            and self.admission_generation is not None
            and self.binding_audience is not None
            and self.kill_switch_allows
            and self.transport_lease_identity is not None
        )

    def capture_capability(self) -> ProjectCaptureCapability:
        """Derive capture authority without introducing a loose UUID/path pair."""
        return _new_capture_capability(
            store_identity=self.store_identity,
            epoch_id=self.epoch_id,
        )

    def maintenance_capability(self) -> ProjectStoreMaintenanceCapability:
        """Derive maintenance authority for this already-verified store."""
        return _new_maintenance_capability(
            store_identity=self.store_identity,
        )


def _new_verified_project_store_identity(
    *,
    project_uuid: CanonicalProjectUUID,
    database_path: Path,
    schema_version: int,
    layout_version: int,
) -> VerifiedProjectStoreIdentity:
    """Construct identity only from the store's verified, active unit of work."""
    identity = object.__new__(VerifiedProjectStoreIdentity)
    values = {
        "project_uuid": project_uuid,
        "database_path": database_path,
        "schema_version": schema_version,
        "layout_version": layout_version,
    }
    for name, value in values.items():
        object.__setattr__(identity, name, value)
    return identity


def _new_capture_capability(
    *,
    store_identity: VerifiedProjectStoreIdentity,
    epoch_id: int | None,
) -> ProjectCaptureCapability:
    """Derive capture authority from one non-forgeable store identity."""
    capability = object.__new__(ProjectCaptureCapability)
    object.__setattr__(capability, "project_uuid", store_identity.project_uuid)
    object.__setattr__(capability, "store_identity", store_identity)
    object.__setattr__(capability, "epoch_id", epoch_id)
    return capability


def _new_maintenance_capability(
    *,
    store_identity: VerifiedProjectStoreIdentity,
) -> ProjectStoreMaintenanceCapability:
    """Derive maintenance authority from one non-forgeable store identity."""
    capability = object.__new__(ProjectStoreMaintenanceCapability)
    object.__setattr__(capability, "project_uuid", store_identity.project_uuid)
    object.__setattr__(capability, "store_identity", store_identity)
    return capability


def _new_project_sync_context(
    *,
    store_identity: VerifiedProjectStoreIdentity,
    consent_state: ConsentState | None,
    consent_generation: int | None,
    epoch_id: int | None,
    target_audience: TargetAudience | None,
    admission_state: AdmissionState | None,
    admission_generation: str | None,
    binding_audience: str | None,
    kill_switch_allows: bool,
    transport_lease_identity: str | None,
) -> ProjectSyncContext:
    """Construct a validated context for the store-owned factory only."""
    project_uuid = store_identity.project_uuid
    if (consent_state is None) != (consent_generation is None):
        raise ValueError("consent state and consent generation must be paired")
    if consent_generation is not None and consent_generation < 1:
        raise ValueError("consent generation must be positive")
    if epoch_id is not None and epoch_id < 1:
        raise ValueError("epoch identity must be positive")
    if target_audience is not None and target_audience.project_uuid != project_uuid:
        raise ValueError("target audience project UUID does not match the store")
    if admission_state is None:
        if admission_generation is not None or binding_audience is not None:
            raise ValueError("admission fields require an admission state")
    else:
        if target_audience is None:
            raise ValueError("admission state requires an exact target audience")
        if admission_state is AdmissionState.ADMITTED and (admission_generation is None or binding_audience is None):
            raise ValueError("admitted authority requires admission generation and binding audience")
    if transport_lease_identity is not None and not transport_lease_identity.strip():
        raise ValueError("transport lease identity must be non-empty")
    lease_authority_complete = (
        consent_state is ConsentState.GRANTED
        and consent_generation is not None
        and epoch_id is not None
        and target_audience is not None
        and admission_state is AdmissionState.ADMITTED
        and admission_generation is not None
        and binding_audience is not None
        and kill_switch_allows
    )
    if transport_lease_identity is not None and not lease_authority_complete:
        raise ValueError("transport lease requires complete eligible authority")

    context = object.__new__(ProjectSyncContext)
    values = {
        "project_uuid": project_uuid,
        "store_identity": store_identity,
        "consent_state": consent_state,
        "consent_generation": consent_generation,
        "epoch_id": epoch_id,
        "target_audience": target_audience,
        "admission_state": admission_state,
        "admission_generation": admission_generation,
        "binding_audience": binding_audience,
        "kill_switch_allows": kill_switch_allows,
        "transport_lease_identity": transport_lease_identity,
    }
    for name, value in values.items():
        object.__setattr__(context, name, value)
    return context


__all__ = [
    "AdmissionState",
    "ConsentState",
    "ProjectCaptureCapability",
    "ProjectStoreMaintenanceCapability",
    "ProjectSyncContext",
    "TargetAudience",
    "VerifiedProjectStoreIdentity",
]
