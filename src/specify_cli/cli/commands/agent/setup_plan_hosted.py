"""No-raise hosted-readiness decision adapter for ``agent setup-plan``.

This module decides whether setup-plan may perform hosted effects; it never
performs those effects.  Setup-plan invokes its independent collectors only
after producing the authoritative local outcome.  Authentication comes
directly from the canonical ``TokenManager.session_assessment``; structural
and routing evidence remain separate.  :func:`decide_hosted_sync` is their
single composition authority, and every malformed or raising adapter fails
closed without changing the local result.
"""

from __future__ import annotations

import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Protocol, cast

from specify_cli.auth.token_manager import SessionAssessment
if TYPE_CHECKING:
    from specify_cli.sync.preflight import PreflightResult
    from specify_cli.sync.routing import CheckoutSyncRouting

PreflightProbe = Callable[..., "PreflightResult"]
RouteProbe = Callable[[Path], "CheckoutSyncRouting | None"]
DetailsClassifier = Callable[[Mapping[str, object]], dict[str, object] | None]


class _SessionAssessmentLike(Protocol):
    completed: bool
    usable_session: bool | None
    reason: str


class _TokenManagerLike(Protocol):
    @property
    def session_assessment(self) -> _SessionAssessmentLike: ...

_AUTH_UNKNOWN_REASONS = frozenset(
    {
        "auth_evaluation_failed",
        "auth_evidence_unavailable",
        "not_evaluated",
        "session_evaluation_failed",
        "session_materialization_failed",
        "session_materialization_pending",
        "storage_delete_failed",
        "storage_read_failed",
        "storage_write_failed",
    }
)
_UNAUTHENTICATED_REASONS = frozenset(
    {
        "refresh_token_expired",
        "session_absent",
        "session_cleared",
    }
)
_BOUNDARY_REASONS = frozenset(
    {
        "boundary_evaluation_failed",
        "boundary_evidence_unavailable",
        "structural_preflight_failed",
    }
)
_ROUTE_REASONS = frozenset({"route_evaluation_failed", "route_unavailable"})
_MISMATCH_FIELDS = frozenset(
    {
        "daemon_executable_path",
        "daemon_package_version",
        "daemon_queue_db_path",
        "daemon_server_url",
        "daemon_source_path",
        "daemon_team_or_user",
    }
)
_OWNER_FAULT_REASONS = frozenset(
    {"invalid_fields", "invalid_json", "not_an_object", "unreadable_file"}
)
_PREFLIGHT_BOOL_FIELDS = (
    "ok",
    "auth_present",
    "auth_required",
)
_PREFLIGHT_COUNT_FIELDS = (
    "legacy_event_rows",
    "legacy_body_upload_rows",
    "legacy_rows_for_scope",
)


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
class _DiagnosticSpec:
    """Canonical wire contract for one registered hosted diagnostic code."""

    severity: str
    hosted_disposition: str
    message: str
    remediation: tuple[str, ...]
    details_classifier: DetailsClassifier


@dataclass(frozen=True, slots=True)
class HostedSyncDiagnostic:
    """A nonfatal, credential-safe explanation for hosted refusal."""

    code: str
    severity: str
    hosted_disposition: str
    message: str
    details: Mapping[str, object] | None = None
    remediation: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject codes outside the closed wire registry without echoing input."""
        _diagnostic_spec(self.code)

    def to_dict(self) -> dict[str, object]:
        """Reconstruct the complete wire envelope from the closed registry."""
        return _canonical_diagnostic_payload(self.code, self.details)


def _canonical_diagnostic_payload(
    code: str,
    details: Mapping[str, object] | None,
) -> dict[str, object]:
    """Serialize one registered diagnostic without calling public methods."""
    spec = _diagnostic_spec(code)
    payload: dict[str, object] = {
        "code": code,
        "severity": spec.severity,
        "hosted_disposition": spec.hosted_disposition,
        "message": spec.message,
        "remediation": list(spec.remediation),
    }
    try:
        raw_details = details or {}
        if not isinstance(raw_details, Mapping):
            raise TypeError("diagnostic details are not a mapping")
        safe_details = spec.details_classifier(raw_details)
    except Exception:  # noqa: BLE001 - serialization is a fail-closed boundary
        safe_details = spec.details_classifier({})
    if safe_details:
        payload["details"] = safe_details
    return payload


def serialize_hosted_sync_diagnostics(
    diagnostics: tuple[HostedSyncDiagnostic, ...],
) -> list[dict[str, object]]:
    """Totalize the public diagnostic collection at its final wire boundary.

    A patched, subclassed, or otherwise hostile ``to_dict`` implementation
    cannot replace the already-frozen local command outcome.  The fallback is
    reconstructed directly from the closed registry and contains no caller
    exception text.
    """
    serialized: list[dict[str, object]] = []
    for diagnostic in diagnostics:
        try:
            serialized.append(diagnostic.to_dict())
        except Exception:  # noqa: BLE001 - local payload/exit already authoritative
            serialized.append(
                _canonical_diagnostic_payload(
                    "SAAS_SYNC_BOUNDARY_UNSAFE",
                    {"reason": "boundary_evaluation_failed"},
                )
            )
    return serialized


@dataclass(frozen=True, slots=True, weakref_slot=True)
class HostedSyncDecision:
    """Single permission shared by all setup-plan hosted effects."""

    requested: bool
    allow_effects: bool
    diagnostics: tuple[HostedSyncDiagnostic, ...]

    def __post_init__(self) -> None:
        """Forbid internally contradictory decision values."""
        if self.allow_effects and self.diagnostics:
            raise ValueError("allowing hosted sync decision cannot contain diagnostics")
        if self.allow_effects and not self.requested:
            raise ValueError("unrequested hosted sync decision cannot allow effects")

    def to_dict(self) -> dict[str, object]:
        """Return a plain JSON-compatible representation."""
        return {
            "requested": self.requested,
            "allow_effects": self.allow_effects,
            "diagnostics": serialize_hosted_sync_diagnostics(self.diagnostics),
        }


# Identity, rather than dataclass equality or a copyable capability field,
# proves that an affirmative decision came from ``decide_hosted_sync``.  Weak
# references prevent the registry from extending a command decision's lifetime;
# the callback also guards against CPython id reuse.
_AFFIRMATIVE_DECISIONS: dict[int, weakref.ReferenceType[HostedSyncDecision]] = {}


def is_canonical_hosted_sync_decision(decision: HostedSyncDecision) -> bool:
    """Return whether this exact affirmative object was issued canonically."""
    if not decision.allow_effects:
        return False
    reference = _AFFIRMATIVE_DECISIONS.get(id(decision))
    return reference is not None and reference() is decision


def acquire_session_assessment(
    _repo_root: Path,
    *,
    token_manager_factory: Callable[[], _TokenManagerLike] | None = None,
) -> SessionAssessment:
    """Acquire the canonical invocation-local session assessment directly.

    Setup-plan does not need a Teamspace classification to decide whether a
    hosted effect has bearer authority.  Reading that broader readiness probe
    used to couple authentication to route/context discovery and could turn a
    conclusive no-session result into ``UNKNOWN``.  This adapter therefore
    consumes only ``TokenManager.session_assessment`` and validates its runtime
    shape without trusting arbitrary property access.
    """
    if token_manager_factory is None:
        from specify_cli.auth import get_token_manager  # noqa: PLC0415

        token_manager_factory = get_token_manager

    try:
        assessment = token_manager_factory().session_assessment
        completed = assessment.completed
        usable_session = assessment.usable_session
        reason = assessment.reason
    except Exception:  # noqa: BLE001 - hosted evidence must not escape
        return SessionAssessment(False, None, "auth_evaluation_failed")

    if completed is True and usable_session is True and isinstance(reason, str) and reason:
        return SessionAssessment(True, True, reason)
    if completed is True and usable_session is False and isinstance(reason, str) and reason:
        return SessionAssessment(True, False, reason)
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
        ok = result.ok
    except Exception:  # noqa: BLE001 - unknown safety must refuse, not abort local work
        return BoundaryEvaluation(
            BoundaryState.UNKNOWN,
            reason="boundary_evaluation_failed",
        )

    if ok is True:
        return BoundaryEvaluation(BoundaryState.SAFE)

    if ok is not False:
        return BoundaryEvaluation(
            BoundaryState.UNKNOWN,
            reason="boundary_evaluation_failed",
        )
    try:
        raw_evidence = result.to_dict()
        if not isinstance(raw_evidence, Mapping):
            raise TypeError("preflight evidence is not a mapping")
        evidence = cast(
            Mapping[str, object],
            _sanitize_preflight_evidence(cast(Mapping[str, object], raw_evidence)),
        )
    except Exception:  # noqa: BLE001 - serialization/sanitization is evidence acquisition
        return BoundaryEvaluation(
            BoundaryState.UNKNOWN,
            reason="boundary_evaluation_failed",
        )
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
        if routing is None:
            return (False, "route_unavailable")
        project_uuid = routing.project_uuid
        effective_sync_enabled = routing.effective_sync_enabled
    except Exception:  # noqa: BLE001 - route acquisition is nonfatal to local work
        return (False, "route_evaluation_failed")

    if (
        isinstance(project_uuid, str)
        and bool(project_uuid.strip())
        and effective_sync_enabled is True
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
    try:
        assessment_completed = session_assessment.completed if session_assessment is not None else None
        assessment_usable = session_assessment.usable_session if session_assessment is not None else None
        assessment_reason = session_assessment.reason if session_assessment is not None else "auth_evidence_unavailable"
    except Exception:  # noqa: BLE001 - malformed evidence is unknown, never fatal
        assessment_completed = None
        assessment_usable = None
        assessment_reason = "auth_evaluation_failed"

    if session_assessment is None:
        diagnostics.append(_auth_unknown_diagnostic("auth_evidence_unavailable"))
    elif assessment_completed is not True:
        diagnostics.append(_auth_unknown_diagnostic(assessment_reason))
    elif assessment_usable is not True:
        diagnostics.append(_unauthenticated_diagnostic(assessment_reason))

    if boundary is None:
        diagnostics.append(
            _boundary_diagnostic(
                BoundaryEvaluation(BoundaryState.UNKNOWN, "boundary_evidence_unavailable")
            )
        )
    else:
        try:
            boundary_state = boundary.state
        except Exception:  # noqa: BLE001 - malformed evidence is unknown, never fatal
            boundary_state = BoundaryState.UNKNOWN
            boundary = BoundaryEvaluation(BoundaryState.UNKNOWN, "boundary_evaluation_failed")
        if boundary_state is not BoundaryState.SAFE:
            diagnostics.append(_boundary_diagnostic(boundary))

    if route_available is not True:
        diagnostics.append(_route_diagnostic(route_reason or "route_unavailable"))

    ordered_unique = tuple({diagnostic.code: diagnostic for diagnostic in diagnostics}.values())
    allow_effects = (
        session_assessment is not None
        and assessment_completed is True
        and assessment_usable is True
        and boundary is not None
        and boundary_state is BoundaryState.SAFE
        and route_available is True
    )
    decision = HostedSyncDecision(True, allow_effects, ordered_unique)
    if not allow_effects:
        return decision

    identity = id(decision)

    def _discard(reference: weakref.ReferenceType[HostedSyncDecision]) -> None:
        if _AFFIRMATIVE_DECISIONS.get(identity) is reference:
            _AFFIRMATIVE_DECISIONS.pop(identity, None)

    reference = weakref.ref(decision, _discard)
    _AFFIRMATIVE_DECISIONS[identity] = reference
    return decision


def _unauthenticated_diagnostic(reason: str) -> HostedSyncDiagnostic:
    return _registered_diagnostic(
        "SAAS_SYNC_UNAUTHENTICATED",
        details={"reason": reason},
    )


def _auth_unknown_diagnostic(reason: str) -> HostedSyncDiagnostic:
    return _registered_diagnostic(
        "SAAS_SYNC_AUTH_UNKNOWN",
        details={"reason": reason},
    )


def _boundary_diagnostic(boundary: BoundaryEvaluation) -> HostedSyncDiagnostic:
    try:
        reason = boundary.reason or "boundary_evaluation_failed"
        raw_evidence = boundary.evidence
        details: dict[str, object] = {"reason": reason}
        if raw_evidence is not None:
            details["evidence"] = _sanitize_preflight_evidence(raw_evidence)
    except Exception:  # noqa: BLE001 - malformed evidence becomes stable unknown
        details = {"reason": "boundary_evaluation_failed"}
    return _registered_diagnostic(
        "SAAS_SYNC_BOUNDARY_UNSAFE",
        details=details,
    )


def _route_diagnostic(reason: str) -> HostedSyncDiagnostic:
    return _registered_diagnostic(
        "SAAS_SYNC_ROUTE_UNAVAILABLE",
        details={"reason": reason},
    )


def _sanitize_preflight_evidence(value: Mapping[str, object]) -> dict[str, object]:
    """Copy only the closed, credential-safe structural evidence schema."""
    evidence: dict[str, object] = {}
    for key in _PREFLIGHT_BOOL_FIELDS:
        item = value.get(key)
        if isinstance(item, bool):
            evidence[key] = item
    for key in _PREFLIGHT_COUNT_FIELDS:
        item = value.get(key)
        if isinstance(item, int) and not isinstance(item, bool) and item >= 0:
            evidence[key] = item

    mismatches = value.get("mismatches")
    if isinstance(mismatches, (list, tuple)):
        evidence["mismatches"] = _safe_mismatches(mismatches)

    orphan_records = value.get("orphan_records")
    if isinstance(orphan_records, (list, tuple)):
        evidence["orphan_records"] = _safe_orphan_records(orphan_records)

    if "project_store_diagnostic" in value:
        evidence["project_store_diagnostic"] = (
            None
            if value.get("project_store_diagnostic") is None
            else "project_store_unavailable"
        )

    if "unreadable_owner_record" in value:
        owner_fault = value.get("unreadable_owner_record")
        if owner_fault is None:
            evidence["unreadable_owner_record"] = None
        else:
            evidence["unreadable_owner_record"] = _safe_owner_fault(owner_fault)
    return evidence


def _safe_mismatches(values: list[object] | tuple[object, ...]) -> list[dict[str, str]]:
    """Retain only recognized structural field classifications."""
    safe: list[dict[str, str]] = []
    for value in values:
        if not isinstance(value, Mapping):
            continue
        field = value.get("field")
        if isinstance(field, str) and field in _MISMATCH_FIELDS:
            safe.append({"field": field})
    return safe


def _safe_orphan_records(
    values: list[object] | tuple[object, ...],
) -> list[dict[str, int]]:
    """Retain only the primitive PID classification for orphan evidence."""
    safe: list[dict[str, int]] = []
    for value in values:
        if not isinstance(value, Mapping):
            continue
        pid = value.get("pid")
        if isinstance(pid, int) and not isinstance(pid, bool) and pid >= 0:
            safe.append({"pid": pid})
    return safe


def _safe_owner_fault(value: object) -> dict[str, str]:
    """Classify an unreadable owner record without retaining path or detail."""
    if isinstance(value, Mapping):
        raw_reason = value.get("reason")
        if isinstance(raw_reason, str) and raw_reason in _OWNER_FAULT_REASONS:
            return {"reason": raw_reason}
    return {"reason": "owner_record_unreadable"}


def _classify_unauthenticated_details(
    details: Mapping[str, object],
) -> dict[str, object]:
    """Classify confirmed logged-out details."""
    return {
        "reason": _safe_reason(
            details.get("reason"),
            allowed=_UNAUTHENTICATED_REASONS,
            fallback="session_absent",
        )
    }


def _classify_auth_unknown_details(
    details: Mapping[str, object],
) -> dict[str, object]:
    """Classify failed auth-assessment details."""
    return {
        "reason": _safe_reason(
            details.get("reason"),
            allowed=_AUTH_UNKNOWN_REASONS,
            fallback="auth_evaluation_failed",
        )
    }


def _classify_route_details(
    details: Mapping[str, object],
) -> dict[str, object]:
    """Classify route refusal details."""
    return {
        "reason": _safe_reason(
            details.get("reason"),
            allowed=_ROUTE_REASONS,
            fallback="route_evaluation_failed",
        )
    }


def _classify_boundary_details(
    details: Mapping[str, object],
) -> dict[str, object]:
    """Classify structural refusal details and evidence."""

    safe: dict[str, object] = {
        "reason": _safe_reason(
            details.get("reason"),
            allowed=_BOUNDARY_REASONS,
            fallback="boundary_evaluation_failed",
        )
    }
    raw_evidence = details.get("evidence")
    if isinstance(raw_evidence, Mapping):
        safe["evidence"] = _sanitize_preflight_evidence(
            cast(Mapping[str, object], raw_evidence)
        )
    return safe


def _safe_reason(
    value: object,
    *,
    allowed: frozenset[str],
    fallback: str,
) -> str:
    """Return an allowlisted classification without inspecting string content."""
    if isinstance(value, str) and value in allowed:
        return value
    return fallback


_DIAGNOSTIC_REGISTRY: Mapping[str, _DiagnosticSpec] = MappingProxyType(
    {
        "SAAS_SYNC_UNAUTHENTICATED": _DiagnosticSpec(
            severity="warning",
            hosted_disposition="refused",
            message="Hosted sync was skipped because no usable local session is available; local setup-plan continued.",
            remediation=("Log in before retrying hosted sync.",),
            details_classifier=_classify_unauthenticated_details,
        ),
        "SAAS_SYNC_AUTH_UNKNOWN": _DiagnosticSpec(
            severity="warning",
            hosted_disposition="refused",
            message="Hosted sync was skipped because local authentication could not be evaluated; local setup-plan continued.",
            remediation=("Inspect local authentication storage before retrying hosted sync.",),
            details_classifier=_classify_auth_unknown_details,
        ),
        "SAAS_SYNC_BOUNDARY_UNSAFE": _DiagnosticSpec(
            severity="warning",
            hosted_disposition="refused",
            message="Hosted sync was skipped because the structural sync boundary was not safe; local setup-plan continued.",
            remediation=("Resolve the reported sync-boundary condition before retrying hosted sync.",),
            details_classifier=_classify_boundary_details,
        ),
        "SAAS_SYNC_ROUTE_UNAVAILABLE": _DiagnosticSpec(
            severity="warning",
            hosted_disposition="refused",
            message="Hosted sync was skipped because no permitted delivery route was available; local setup-plan continued.",
            remediation=("Verify project identity and hosted-sync consent before retrying.",),
            details_classifier=_classify_route_details,
        ),
    }
)


def _diagnostic_spec(code: str) -> _DiagnosticSpec:
    """Resolve a known wire code or fail without echoing caller input."""
    try:
        return _DIAGNOSTIC_REGISTRY[code]
    except KeyError:
        raise ValueError("unsupported hosted sync diagnostic code") from None


def _registered_diagnostic(
    code: str,
    *,
    details: Mapping[str, object],
) -> HostedSyncDiagnostic:
    """Construct an internal diagnostic from its canonical registry entry."""
    spec = _diagnostic_spec(code)
    return HostedSyncDiagnostic(
        code=code,
        severity=spec.severity,
        hosted_disposition=spec.hosted_disposition,
        message=spec.message,
        details=details,
        remediation=spec.remediation,
    )


__all__ = [
    "HostedSyncDecision",
    "HostedSyncDiagnostic",
    "acquire_session_assessment",
    "decide_hosted_sync",
    "evaluate_boundary",
    "evaluate_route_availability",
    "is_canonical_hosted_sync_decision",
    "serialize_hosted_sync_diagnostics",
]
