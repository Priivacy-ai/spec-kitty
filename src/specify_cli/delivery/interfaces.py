"""Connection-free delivery seams and project-owned target values."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from specify_cli.sync.project_context import AdmissionState
from specify_cli.sync.project_identity import CanonicalProjectUUID

if TYPE_CHECKING:
    from specify_cli.delivery.consent_gate import ConsentedBatch
    from specify_cli.sync.project_store import ProjectUnitOfWork
    from specify_cli.sync.target_authority import AdmissionAudience


@dataclass(frozen=True, slots=True)
class TargetIdentity:
    """Exact target/account/Private-Teamspace/project/configuration tuple."""

    target_identity: str
    account_identity: str
    private_teamspace_id: str
    project_uuid: CanonicalProjectUUID
    configuration_generation: int


@dataclass(frozen=True, slots=True)
class DeliveryTarget:
    """Current project-owned target and its separately scoped remote admission."""

    target_id: str
    identity: TargetIdentity
    admission_state: AdmissionState
    admission_generation: int | None
    binding_audience: str | None
    last_error_category: str | None

    @property
    def target_identity(self) -> str:
        return self.identity.target_identity

    @property
    def account_identity(self) -> str:
        return self.identity.account_identity

    @property
    def private_teamspace_id(self) -> str:
        return self.identity.private_teamspace_id

    @property
    def project_uuid(self) -> CanonicalProjectUUID:
        return self.identity.project_uuid

    @property
    def configuration_generation(self) -> int:
        return self.identity.configuration_generation


@runtime_checkable
class DeliveryTargetRegistry(Protocol):
    """Repository whose caller supplies the project-owned unit of work."""

    def register(
        self,
        unit: ProjectUnitOfWork,
        audience: AdmissionAudience,
    ) -> DeliveryTarget: ...

    def get_current(self, unit: ProjectUnitOfWork) -> DeliveryTarget | None: ...

    def list_targets(self, unit: ProjectUnitOfWork) -> list[DeliveryTarget]: ...


class DeliveryLedger(Protocol):
    def record_result(self, *, event_id: str, target_id: str, result: object) -> None: ...

    def select_pending(self, *, target_id: str, limit: int) -> Sequence[str]: ...

    def delivered_anywhere(self, event_id: str) -> bool: ...


class DeliveryReceiver(Protocol):
    @property
    def endpoint_url(self) -> str: ...

    def auth_headers(self) -> Mapping[str, str]: ...

    def gates_satisfied(self) -> bool: ...

    def deliver(self, batch: ConsentedBatch) -> Sequence[object]: ...


class Dispatcher(Protocol):
    def dispatch(
        self,
        *,
        target: DeliveryTarget,
        receiver: DeliveryReceiver,
        ledger: DeliveryLedger,
    ) -> object: ...


__all__ = [
    "DeliveryLedger",
    "DeliveryReceiver",
    "DeliveryTarget",
    "DeliveryTargetRegistry",
    "Dispatcher",
    "TargetIdentity",
]
