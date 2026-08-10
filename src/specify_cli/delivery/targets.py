"""Project-owned delivery-target repository; never a connection owner."""

from __future__ import annotations

import hashlib
from urllib.parse import urlsplit, urlunsplit

from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
from specify_cli.sync.project_context import AdmissionState
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork, SQLiteRow
from specify_cli.sync.target_authority import AdmissionAudience

_DEFAULT_PORTS = {"https": 443, "http": 80}


class InvalidTargetUrlError(ValueError):
    """A target URL cannot be normalized safely."""


def canonicalize_url(raw_url: str) -> str:
    """Backward-compatible endpoint canonicalization helper (pure, no I/O)."""
    if not raw_url or not raw_url.strip():
        raise InvalidTargetUrlError("target URL must be a non-empty string")
    parts = urlsplit(raw_url.strip())
    if not parts.scheme or not parts.hostname:
        raise InvalidTargetUrlError("target URL is missing scheme or host")
    scheme = parts.scheme.lower()
    try:
        host = parts.hostname.encode("idna").decode("ascii").lower()
        port = parts.port
    except (UnicodeError, ValueError) as exc:
        raise InvalidTargetUrlError("target URL has an invalid host or port") from exc
    netloc = host
    if port is not None and _DEFAULT_PORTS.get(scheme) != port:
        netloc = f"{host}:{port}"
    return urlunsplit((scheme, netloc, parts.path.rstrip("/"), "", ""))


def compute_url_hash(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()  # noqa: TID251 - target identity digest, not charter freshness


def _target_id(audience: AdmissionAudience) -> str:
    material = "\x00".join(
        (
            audience.target_identity,
            audience.account_identity,
            audience.private_teamspace_id,
            audience.project_uuid.storage_token,
            str(audience.configuration_generation),
        )
    )
    return f"tgt_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:32]}"  # noqa: TID251 - target identity digest, not charter freshness


def _row_to_target(row: SQLiteRow) -> DeliveryTarget:
    values = tuple(row)
    project_uuid = CanonicalProjectUUID.parse(str(values[0]))
    generation = values[6]
    return DeliveryTarget(
        target_id=_target_id(
            AdmissionAudience(
                normalized_server_origin=str(values[1]),
                account_identity=str(values[2]),
                private_teamspace_id=str(values[3]),
                project_uuid=project_uuid,
                configuration_generation=int(values[4]),
            )
        ),
        identity=TargetIdentity(
            target_identity=str(values[1]),
            account_identity=str(values[2]),
            private_teamspace_id=str(values[3]),
            project_uuid=project_uuid,
            configuration_generation=int(values[4]),
        ),
        admission_state=AdmissionState(str(values[5])),
        admission_generation=None if generation is None else int(str(generation)),
        binding_audience=None if values[7] is None else str(values[7]),
        last_error_category=None if values[8] is None else str(values[8]),
    )


class ProjectDeliveryTargetRegistry:
    """Repository over one :class:`ProjectSyncStore` and caller-owned UoW."""

    __slots__ = ("_store",)

    def __init__(self, store: ProjectSyncStore) -> None:
        if not isinstance(store, ProjectSyncStore):
            raise TypeError("delivery target registry requires ProjectSyncStore")
        self._store = store

    def _verify(self, unit: ProjectUnitOfWork, audience: AdmissionAudience | None = None) -> None:
        if unit.project_uuid != self._store.project_uuid:
            raise ValueError("unit of work belongs to another project store")
        if audience is not None and audience.project_uuid != self._store.project_uuid:
            raise ValueError("target audience belongs to another project")

    def get_current(self, unit: ProjectUnitOfWork) -> DeliveryTarget | None:
        self._verify(unit)
        row = unit.execute(
            "SELECT project_uuid, target_identity, account_identity, "
            "private_teamspace_id, configuration_generation, admission_state, "
            "admission_generation, binding_audience, last_error_category "
            "FROM project_target_admissions WHERE project_uuid = ?",
            (self._store.project_uuid.storage_token,),
        ).fetchone()
        return None if row is None else _row_to_target(row)

    def register(
        self,
        unit: ProjectUnitOfWork,
        audience: AdmissionAudience,
    ) -> DeliveryTarget:
        self._verify(unit, audience)
        current = self.get_current(unit)
        if current is not None:
            same_tuple = (
                current.target_identity == audience.target_identity
                and current.account_identity == audience.account_identity
                and current.private_teamspace_id == audience.private_teamspace_id
            )
            if same_tuple and current.configuration_generation == audience.configuration_generation:
                return current
            if audience.configuration_generation <= current.configuration_generation:
                raise ValueError("target configuration generation must advance on audience change")
        unit.execute(
            "INSERT INTO project_target_admissions ("
            "project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, "
            "binding_audience, last_error_category) VALUES (?, ?, ?, ?, ?, 'pending', NULL, NULL, NULL) "
            "ON CONFLICT(project_uuid) DO UPDATE SET "
            "target_identity = excluded.target_identity, "
            "account_identity = excluded.account_identity, "
            "private_teamspace_id = excluded.private_teamspace_id, "
            "configuration_generation = excluded.configuration_generation, "
            "admission_state = 'pending', admission_generation = NULL, "
            "binding_audience = NULL, last_error_category = NULL",
            (
                audience.project_uuid.storage_token,
                audience.target_identity,
                audience.account_identity,
                audience.private_teamspace_id,
                audience.configuration_generation,
            ),
        )
        target = self.get_current(unit)
        if target is None:  # pragma: no cover - INSERT is verified in the same transaction
            raise RuntimeError("target registration did not persist")
        return target

    def list_targets(self, unit: ProjectUnitOfWork) -> list[DeliveryTarget]:
        current = self.get_current(unit)
        return [] if current is None else [current]


# Migration alias: the historical class name now denotes the same connection-free
# project repository. It no longer accepts a path or owns close/commit lifecycle.
SqliteDeliveryTargetRegistry = ProjectDeliveryTargetRegistry


__all__ = [
    "InvalidTargetUrlError",
    "ProjectDeliveryTargetRegistry",
    "SqliteDeliveryTargetRegistry",
    "canonicalize_url",
    "compute_url_hash",
]
