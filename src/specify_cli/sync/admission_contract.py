"""Admission wire vocabulary for the sync transport's own remaining consumers.

Moved verbatim out of ``saas_client.admission`` (#3): the CLI→SaaS sync
transport this vocabulary serves is scheduled for deletion (epic E4, issue #5),
and its last importers all live in this package. Nothing outside the sync
transport reads these symbols; when #5 deletes ``sync/`` this file goes with
it. The old-model half that served no consumer at all — ``SaasAdmissionClient``,
the WP04 candidate attestation, the HTTP transport records — was deleted, not
moved.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypeAlias, cast

from .project_identity import CanonicalProjectUUID

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
AdmissionActionValue: TypeAlias = Literal["admit", "revoke"]

_NONRETRYABLE_CATEGORIES = frozenset(
    {
        "invalid_project_uuid",
        "invalid_admission_request",
        "authentication_required",
        "admission_mutation_forbidden",
        "project_sync_admission_not_found",
        "admission_generation_conflict",
        "admission_operation_conflict",
        "project_tombstoned",
    }
)


class AdmissionTransportUncertain(RuntimeError):
    """Transport ended without a trustworthy server outcome."""


@dataclass(frozen=True, slots=True)
class AdmissionRequest:
    """Transport-neutral immutable admission operation request."""

    action: AdmissionActionValue
    source_project_uuid: str
    operation_key: str
    expected_generation: int | None = None
    project_slug: str | None = None


@dataclass(frozen=True, slots=True)
class AdmissionResponse:
    """Success or typed non-retryable refusal from the canonical endpoint."""

    source_project_uuid: str | None = None
    state: str | None = None
    generation: int | None = None
    binding_audience: str | None = None
    error_category: str | None = None
    retryable: bool = False
    current_generation: int | None = None

    @classmethod
    def refused(
        cls,
        *,
        error_category: str,
        current_generation: int | None = None,
    ) -> AdmissionResponse:
        if error_category not in _NONRETRYABLE_CATEGORIES:
            raise ValueError("unknown canonical admission refusal category")
        return cls(
            error_category=error_category,
            retryable=False,
            current_generation=current_generation,
        )

    @property
    def admitted_or_revoked(self) -> bool:
        return self.error_category is None and self.state in {"admitted", "revoked"}


@dataclass(frozen=True, slots=True)
class ProjectWriteAdmissionProof:
    project_uuid: str
    admission_generation: int
    binding_audience: str

    def __post_init__(self) -> None:
        canonical = CanonicalProjectUUID.parse(self.project_uuid).storage_token
        object.__setattr__(self, "project_uuid", canonical)
        if self.admission_generation < 1:
            raise ValueError("admission generation must be positive")
        if not self.binding_audience:
            raise ValueError("binding audience is required")


def attach_admission_proof(
    payload: Mapping[str, object],
    proof: ProjectWriteAdmissionProof,
) -> JsonObject:
    """Return one write item carrying its own exact admission proof."""
    if {"project_uuid", "admission_generation", "binding_audience"} & payload.keys():
        raise ValueError("payload cannot override admission proof")
    return cast(
        "JsonObject",
        {
            **payload,
            "project_uuid": proof.project_uuid,
            "admission_generation": proof.admission_generation,
            "binding_audience": proof.binding_audience,
        },
    )


@dataclass(frozen=True, slots=True)
class ProjectNotAdmitted:
    """Payload-free terminal refusal correlated to exactly one write."""

    write_kind: str
    correlation: tuple[tuple[str, str], ...]
    status: str = "rejected"
    error_category: str = "project_not_admitted"
    retryable: bool = False


def parse_project_not_admitted(
    write_kind: str,
    payload: Mapping[str, object],
    correlation_fields: tuple[str, ...],
) -> ProjectNotAdmitted:
    if payload.get("status") != "rejected":
        raise ValueError("project_not_admitted status must be rejected")
    if payload.get("error_category") != "project_not_admitted":
        raise ValueError("unexpected project write refusal category")
    if payload.get("retryable") is not False:
        raise ValueError("project_not_admitted must be terminal")
    correlation: list[tuple[str, str]] = []
    for field in correlation_fields:
        value = payload.get(field)
        if value is None:
            raise ValueError(f"project_not_admitted is missing correlation field {field}")
        correlation.append((field, str(value)))
    return ProjectNotAdmitted(write_kind=write_kind, correlation=tuple(correlation))


__all__ = [
    "AdmissionRequest",
    "AdmissionResponse",
    "AdmissionTransportUncertain",
    "ProjectWriteAdmissionProof",
    "attach_admission_proof",
    "parse_project_not_admitted",
]
