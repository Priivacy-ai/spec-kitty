"""No-raise hosted-readiness decision adapter for ``agent setup-plan``.

This module decides whether setup-plan may perform hosted effects; it never
performs those effects.  Its collectors remain separate because setup-plan
acquires authentication before repository resolution, then boundary and route
evidence afterward.  :func:`decide_hosted_sync` is their single composition
authority.  Local setup-plan work remains authoritative when that decision
refuses hosted delivery.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, cast

from specify_cli.auth.token_manager import SessionAssessment
from specify_cli.readiness.coordinator import AuthStatus

if TYPE_CHECKING:
    from specify_cli.sync.preflight import PreflightResult
    from specify_cli.sync.routing import CheckoutSyncRouting

AuthProbe = Callable[..., tuple[AuthStatus, str | None]]
PreflightProbe = Callable[..., "PreflightResult"]
RouteProbe = Callable[[Path], "CheckoutSyncRouting | None"]


class BoundaryState(StrEnum):
    """Setup-plan's structural safety assessment."""

    SAFE = "safe"
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BoundaryEvaluation:
    """Sanitized structural evidence produced by canonical sync preflight."""

    state: BoundaryState
    reason: str | None = None
    evidence: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        """Require a stable reason whenever safety is not affirmative."""
        if self.state is BoundaryState.SAFE and self.reason is not None:
            raise ValueError("safe boundary evaluation cannot have a refusal reason")
        if self.state is not BoundaryState.SAFE and not self.reason:
            raise ValueError("non-safe boundary evaluation requires a reason")


@dataclass(frozen=True, slots=True)
class HostedSyncDiagnostic:
    """A nonfatal, credential-safe explanation for hosted refusal."""

    code: str
    severity: str
    hosted_disposition: str
    message: str
    details: Mapping[str, object] | None = None
    remediation: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a plain JSON-compatible warning mapping."""
        payload: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "hosted_disposition": self.hosted_disposition,
            "message": self.message,
        }
        if self.details is not None:
            payload["details"] = _plain_json_mapping(self.details)
        if self.remediation:
            payload["remediation"] = list(self.remediation)
        return payload


@dataclass(frozen=True, slots=True)
class HostedSyncDecision:
    """Single permission shared by all setup-plan hosted effects."""

    requested: bool
    allow_effects: bool
    diagnostics: tuple[HostedSyncDiagnostic, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a plain JSON-compatible representation."""
        return {
            "requested": self.requested,
            "allow_effects": self.allow_effects,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


def acquire_session_assessment(
    repo_root: Path,
    *,
    auth_probe: AuthProbe | None = None,
) -> SessionAssessment:
    """Project the existing no-raise readiness auth probe into WP01 evidence.

    The projection intentionally does not inspect tokens, session objects, or
    queue scope.  Unexpected invocation or return-value failures fail closed.
    """
    if auth_probe is None:
        from specify_cli.readiness.auth import probe_auth_status  # noqa: PLC0415

        auth_probe = probe_auth_status

    try:
        status, _teamspace = auth_probe(repo_root=repo_root)
    except Exception:  # noqa: BLE001 - command adapter is deliberately no-raise
        return SessionAssessment(False, None, "auth_evaluation_failed")

    if status is AuthStatus.AUTHENTICATED:
        return SessionAssessment(True, True, "session_usable")
    if status in (AuthStatus.LOGGED_OUT_IN_TEAMSPACE, AuthStatus.NOT_IN_TEAMSPACE):
        return SessionAssessment(True, False, "session_absent")
    return SessionAssessment(False, None, "auth_evaluation_failed")


def evaluate_boundary(
    repo_root: Path,
    *,
    preflight_probe: PreflightProbe | None = None,
) -> BoundaryEvaluation:
    """Run canonical structural preflight without allowing it to escape."""
    if preflight_probe is None:
        from specify_cli.sync.preflight import run_preflight  # noqa: PLC0415

        preflight_probe = run_preflight

    try:
        result = preflight_probe(repo_root=repo_root, require_auth=False)
    except Exception:  # noqa: BLE001 - unknown safety must refuse, not abort local work
        return BoundaryEvaluation(
            BoundaryState.UNKNOWN,
            reason="boundary_evaluation_failed",
        )

    if result.ok:
        return BoundaryEvaluation(BoundaryState.SAFE)

    evidence = cast(Mapping[str, object], _sanitize_preflight_evidence(result.to_dict()))
    return BoundaryEvaluation(
        BoundaryState.UNSAFE,
        reason="structural_preflight_failed",
        evidence=evidence,
    )


def evaluate_route_availability(
    repo_root: Path,
    *,
    route_probe: RouteProbe | None = None,
) -> tuple[bool, str | None]:
    """Read canonical route permission and return a sanitized verdict/reason."""
    if route_probe is None:
        from specify_cli.sync.routing import resolve_checkout_sync_routing_readonly  # noqa: PLC0415

        route_probe = resolve_checkout_sync_routing_readonly

    try:
        routing = route_probe(repo_root)
    except Exception:  # noqa: BLE001 - route acquisition is nonfatal to local work
        return (False, "route_evaluation_failed")

    if (
        routing is not None
        and isinstance(routing.project_uuid, str)
        and bool(routing.project_uuid.strip())
        and routing.effective_sync_enabled is True
    ):
        return (True, None)
    return (False, "route_unavailable")


def decide_hosted_sync(
    *,
    requested: bool,
    session_assessment: SessionAssessment | None = None,
    boundary: BoundaryEvaluation | None = None,
    route_available: bool | None = None,
    route_reason: str | None = None,
) -> HostedSyncDecision:
    """Compose independent evidence into one deterministic hosted permission.

    Disabled callers need not acquire or supply evidence.  Requested delivery
    fails closed when any evidence is absent; absence is never an affirmative
    default.
    """
    if not requested:
        return HostedSyncDecision(False, False, ())

    diagnostics: list[HostedSyncDiagnostic] = []
    if session_assessment is None:
        diagnostics.append(_auth_unknown_diagnostic("auth_evidence_unavailable"))
    elif not session_assessment.completed:
        diagnostics.append(_auth_unknown_diagnostic(session_assessment.reason))
    elif session_assessment.usable_session is not True:
        diagnostics.append(_unauthenticated_diagnostic(session_assessment.reason))

    if boundary is None:
        diagnostics.append(
            _boundary_diagnostic(
                BoundaryEvaluation(BoundaryState.UNKNOWN, "boundary_evidence_unavailable")
            )
        )
    elif boundary.state is not BoundaryState.SAFE:
        diagnostics.append(_boundary_diagnostic(boundary))

    if route_available is not True:
        diagnostics.append(_route_diagnostic(route_reason or "route_unavailable"))

    ordered_unique = tuple({diagnostic.code: diagnostic for diagnostic in diagnostics}.values())
    allow_effects = (
        session_assessment is not None
        and session_assessment.completed
        and session_assessment.usable_session is True
        and boundary is not None
        and boundary.state is BoundaryState.SAFE
        and route_available is True
    )
    return HostedSyncDecision(True, allow_effects, ordered_unique)


def _unauthenticated_diagnostic(reason: str) -> HostedSyncDiagnostic:
    return HostedSyncDiagnostic(
        code="SAAS_SYNC_UNAUTHENTICATED",
        severity="warning",
        hosted_disposition="refused",
        message="Hosted sync was skipped because no usable local session is available; local setup-plan continued.",
        details={"reason": reason},
        remediation=("Log in before retrying hosted sync.",),
    )


def _auth_unknown_diagnostic(reason: str) -> HostedSyncDiagnostic:
    return HostedSyncDiagnostic(
        code="SAAS_SYNC_AUTH_UNKNOWN",
        severity="warning",
        hosted_disposition="refused",
        message="Hosted sync was skipped because local authentication could not be evaluated; local setup-plan continued.",
        details={"reason": reason},
        remediation=("Inspect local authentication storage before retrying hosted sync.",),
    )


def _boundary_diagnostic(boundary: BoundaryEvaluation) -> HostedSyncDiagnostic:
    details: dict[str, object] = {"reason": boundary.reason or "boundary_evaluation_failed"}
    if boundary.evidence is not None:
        details["evidence"] = _sanitize_preflight_evidence(boundary.evidence)
    return HostedSyncDiagnostic(
        code="SAAS_SYNC_BOUNDARY_UNSAFE",
        severity="warning",
        hosted_disposition="refused",
        message="Hosted sync was skipped because the structural sync boundary was not safe; local setup-plan continued.",
        details=details,
        remediation=("Resolve the reported sync-boundary condition before retrying hosted sync.",),
    )


def _route_diagnostic(reason: str) -> HostedSyncDiagnostic:
    return HostedSyncDiagnostic(
        code="SAAS_SYNC_ROUTE_UNAVAILABLE",
        severity="warning",
        hosted_disposition="refused",
        message="Hosted sync was skipped because no permitted delivery route was available; local setup-plan continued.",
        details={"reason": reason},
        remediation=("Verify project identity and hosted-sync consent before retrying.",),
    )


def _plain_json_mapping(value: Mapping[str, object]) -> dict[str, object]:
    """Recursively copy a trusted sanitized mapping into JSON primitives."""
    return {str(key): _plain_json_value(item) for key, item in value.items()}


def _sanitize_preflight_evidence(value: Mapping[str, object]) -> dict[str, object]:
    """Preserve structural facts while replacing every free-form diagnostic."""
    evidence = _plain_json_mapping(value)
    owner_fault = evidence.get("unreadable_owner_record")
    if isinstance(owner_fault, dict):
        owner_fault.pop("detail", None)
    if evidence.get("project_store_diagnostic") is not None:
        evidence["project_store_diagnostic"] = "project_store_unavailable"
    return evidence


def _plain_json_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _plain_json_value(item) for key, item in mapping.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json_value(item) for item in value]
    return str(value)


__all__ = [
    "BoundaryEvaluation",
    "BoundaryState",
    "HostedSyncDecision",
    "HostedSyncDiagnostic",
    "acquire_session_assessment",
    "decide_hosted_sync",
    "evaluate_boundary",
    "evaluate_route_availability",
]
