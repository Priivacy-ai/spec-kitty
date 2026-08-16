"""Narrow consumer of the SaaS-owned project-sync admission contract."""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeAlias, cast

from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.saas_client.errors import SaasAdmissionContractError

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
AdmissionActionValue: TypeAlias = Literal["admit", "revoke"]

_ADMISSION_PATH = "/api/v1/sync/projects/{source_project_uuid}/sync-admission/"
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


class ContractAttestationError(RuntimeError):
    """The explicitly supplied SaaS candidate differs from pinned authority."""


class AdmissionTransportUncertain(RuntimeError):
    """Transport ended without a trustworthy server outcome."""


@dataclass(frozen=True, slots=True)
class SaasContractPin:
    """Sanitized identity of one explicit generated-contract authority."""

    producer_gate: str
    commit: str
    sha256: str
    checkout_label: str


PINNED_SAAS_WP04_CONTRACT = SaasContractPin(
    producer_gate="SaaS WP04",
    commit="4e15aa5cf263d857f6e10541d3f19cc4c993e5c5",
    sha256="57e66b0f3f234c663eb00dffbe04cbcbed3375d8f283875f42e6ff5481022b7b",
    checkout_label="saas-wp04-candidate-4e15aa5c",
)


def _git_output(checkout: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ("git", "-C", str(checkout), *arguments),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ContractAttestationError("candidate checkout is not a readable Git worktree") from exc
    return completed.stdout.strip()


def attest_saas_contract(
    *,
    checkout_path: Path,
    expected_commit: str,
    expected_sha256: str,
    producer_gate: str,
) -> SaasContractPin:
    """Verify an explicit clean checkout, HEAD, and canonical contract digest."""
    checkout = checkout_path.expanduser().resolve(strict=True)
    if not checkout.is_dir():
        raise ContractAttestationError("candidate checkout is not a directory")
    if producer_gate != "SaaS WP04":
        raise ContractAttestationError("canonical admission contract must identify SaaS WP04")
    actual_commit = _git_output(checkout, "rev-parse", "HEAD")
    if actual_commit != expected_commit:
        raise ContractAttestationError("candidate checkout HEAD differs from expected commit")
    if _git_output(checkout, "status", "--porcelain"):
        raise ContractAttestationError("candidate checkout is dirty")
    contract = checkout / "contracts" / "cli-saas-current-api.yaml"
    if not contract.is_file():
        raise ContractAttestationError("canonical generated SaaS contract is missing")
    actual_sha256 = hashlib.sha256(contract.read_bytes()).hexdigest()  # noqa: TID251 - canonical contract file-integrity digest
    if actual_sha256 != expected_sha256:
        raise ContractAttestationError("canonical generated SaaS contract digest differs")
    return SaasContractPin(
        producer_gate=producer_gate,
        commit=actual_commit,
        sha256=actual_sha256,
        checkout_label=checkout.name,
    )


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
class AdmissionHttpRequest:
    method: Literal["GET", "PUT", "DELETE"]
    path: str
    headers: Mapping[str, str]
    json_body: JsonObject | None


@dataclass(frozen=True, slots=True)
class AdmissionHttpResponse:
    status_code: int
    json_body: Mapping[str, object]


class AdmissionHttpTransport(Protocol):
    def send(self, request: AdmissionHttpRequest) -> AdmissionHttpResponse: ...


class SaasAdmissionClient:
    """Build and parse only the generated admission endpoint's stable shapes."""

    def __init__(self, transport: AdmissionHttpTransport) -> None:
        self._transport = transport

    @staticmethod
    def _validate_key(operation_key: str) -> None:
        if not 16 <= len(operation_key) <= 128:
            raise ValueError("Idempotency-Key must contain 16 to 128 characters")

    @staticmethod
    def _path(source_project_uuid: str) -> str:
        project_uuid = CanonicalProjectUUID.parse(source_project_uuid).storage_token
        return _ADMISSION_PATH.format(source_project_uuid=project_uuid)

    def _send(self, request: AdmissionHttpRequest) -> AdmissionResponse:
        try:
            response = self._transport.send(request)
        except (ConnectionError, TimeoutError) as exc:
            raise AdmissionTransportUncertain("admission transport outcome is unknown") from exc
        body = response.json_body
        if 200 <= response.status_code < 300:
            source_project_uuid = CanonicalProjectUUID.parse(cast("str", body.get("source_project_uuid"))).storage_token
            state = body.get("state")
            generation = body.get("generation")
            binding = body.get("binding_audience")
            if state not in {"admitted", "revoked"}:
                raise SaasAdmissionContractError("invalid canonical admission state", response.status_code)
            if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
                raise SaasAdmissionContractError("invalid canonical admission generation", response.status_code)
            if not isinstance(binding, str) or not binding:
                raise SaasAdmissionContractError("invalid canonical binding audience", response.status_code)
            return AdmissionResponse(
                source_project_uuid=source_project_uuid,
                state=state,
                generation=generation,
                binding_audience=binding,
            )
        category = body.get("error_category")
        retryable = body.get("retryable")
        if not isinstance(category, str) or category not in _NONRETRYABLE_CATEGORIES:
            raise SaasAdmissionContractError("invalid canonical admission refusal category", response.status_code)
        if retryable is not False:
            raise SaasAdmissionContractError("canonical admission refusals must be non-retryable", response.status_code)
        current = body.get("current_generation")
        if current is not None and (not isinstance(current, int) or isinstance(current, bool) or current < 1):
            raise SaasAdmissionContractError("invalid canonical current generation", response.status_code)
        return AdmissionResponse.refused(
            error_category=category,
            current_generation=current,
        )

    def execute(self, request: AdmissionRequest) -> AdmissionResponse:
        if request.action == "admit":
            return self.admit(
                source_project_uuid=request.source_project_uuid,
                operation_key=request.operation_key,
                expected_generation=request.expected_generation,
                project_slug=request.project_slug,
            )
        return self.revoke(
            source_project_uuid=request.source_project_uuid,
            operation_key=request.operation_key,
            expected_generation=request.expected_generation,
        )

    def admit(
        self,
        *,
        source_project_uuid: str,
        operation_key: str,
        expected_generation: int | None = None,
        project_slug: str | None = None,
    ) -> AdmissionResponse:
        self._validate_key(operation_key)
        if expected_generation is not None and expected_generation < 1:
            raise ValueError("expected admission generation must be positive")
        headers = {"Idempotency-Key": operation_key}
        if expected_generation is not None:
            headers["If-Match-Admission-Generation"] = str(expected_generation)
        body: JsonObject | None = None
        if project_slug is not None:
            body = {"project_slug": project_slug}
        return self._send(
            AdmissionHttpRequest(
                method="PUT",
                path=self._path(source_project_uuid),
                headers=headers,
                json_body=body,
            )
        )

    def revoke(
        self,
        *,
        source_project_uuid: str,
        operation_key: str,
        expected_generation: int | None,
    ) -> AdmissionResponse:
        self._validate_key(operation_key)
        if expected_generation is None or expected_generation < 1:
            raise ValueError("revocation requires a positive expected admission generation")
        return self._send(
            AdmissionHttpRequest(
                method="DELETE",
                path=self._path(source_project_uuid),
                headers={
                    "Idempotency-Key": operation_key,
                    "If-Match-Admission-Generation": str(expected_generation),
                },
                json_body=None,
            )
        )

    @staticmethod
    def websocket_headers(token: str, *, protocol: str) -> dict[str, str]:
        if not token:
            raise ValueError("WebSocket bearer token is required")
        return {
            "Authorization": f"Bearer {token}",
            "X-Spec-Kitty-Sync-Protocol": protocol,
        }


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
