"""Truth-table tests for setup-plan's hosted assessment adapter."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from specify_cli.auth.token_manager import SessionAssessment
from specify_cli.cli.commands.agent.setup_plan_hosted import (
    BoundaryEvaluation,
    BoundaryState,
    assess_hosted_sync,
    decide_hosted_sync,
    evaluate_boundary,
)
from specify_cli.readiness.coordinator import AuthStatus
from specify_cli.sync.owner import UnreadableOwnerRecord
from specify_cli.sync.preflight import PreflightResult
from specify_cli.sync.routing import CheckoutSyncRouting


def _routing(repo_root: Path, *, available: bool) -> CheckoutSyncRouting:
    return CheckoutSyncRouting(
        repo_root=repo_root,
        project_uuid="project-123" if available else None,
        project_slug="project",
        build_id=None,
        repo_slug="owner/repo",
        local_sync_enabled=None,
        repo_default_sync_enabled=None,
        effective_sync_enabled=available,
    )


def test_disabled_short_circuits_all_probes(tmp_path: Path) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("disabled mode must not invoke hosted-readiness probes")

    decision = assess_hosted_sync(
        requested=False,
        repo_root=tmp_path,
        auth_probe=forbidden,
        preflight_probe=forbidden,
        route_probe=forbidden,
    )

    assert decision.requested is False
    assert decision.allow_effects is False
    assert decision.diagnostics == ()
    assert decision.to_dict() == {
        "requested": False,
        "allow_effects": False,
        "diagnostics": [],
    }


def test_all_affirmative_evidence_allows_hosted_effects(tmp_path: Path) -> None:
    decision = assess_hosted_sync(
        requested=True,
        repo_root=tmp_path,
        auth_probe=lambda **_: (AuthStatus.AUTHENTICATED, None),
        preflight_probe=lambda **_: PreflightResult(ok=True, auth_required=False),
        route_probe=lambda _: _routing(tmp_path, available=True),
    )

    assert decision.allow_effects is True
    assert decision.diagnostics == ()


@pytest.mark.parametrize(
    ("assessment", "expected_code"),
    [
        (SessionAssessment(True, False, "session_absent"), "SAAS_SYNC_UNAUTHENTICATED"),
        (SessionAssessment(False, None, "storage_read_failed"), "SAAS_SYNC_AUTH_UNKNOWN"),
    ],
)
def test_auth_outcomes_remain_distinct(
    assessment: SessionAssessment,
    expected_code: str,
) -> None:
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=assessment,
        boundary=BoundaryEvaluation(BoundaryState.SAFE),
        route_available=True,
    )

    assert decision.allow_effects is False
    assert [diagnostic.code for diagnostic in decision.diagnostics] == [expected_code]


def test_auth_probe_failure_is_unknown_and_never_escapes(tmp_path: Path) -> None:
    def broken_auth(**_: object) -> tuple[AuthStatus, None]:
        raise RuntimeError("secret-token-auth-explosion")

    decision = assess_hosted_sync(
        requested=True,
        repo_root=tmp_path,
        auth_probe=broken_auth,
        preflight_probe=lambda **_: PreflightResult(ok=True, auth_required=False),
        route_probe=lambda _: _routing(tmp_path, available=True),
    )

    assert [diagnostic.code for diagnostic in decision.diagnostics] == ["SAAS_SYNC_AUTH_UNKNOWN"]
    assert "secret-token-auth-explosion" not in str(decision.to_dict())


def test_returned_unsafe_boundary_preserves_sanitized_preflight_evidence(tmp_path: Path) -> None:
    preflight = PreflightResult(ok=False, legacy_event_rows=2, auth_required=False)

    boundary = evaluate_boundary(tmp_path, preflight_probe=lambda **_: preflight)
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=SessionAssessment(True, True, "session_usable"),
        boundary=boundary,
        route_available=True,
    )

    diagnostic = decision.diagnostics[0]
    assert diagnostic.code == "SAAS_SYNC_BOUNDARY_UNSAFE"
    assert diagnostic.details == {
        "reason": "structural_preflight_failed",
        "evidence": preflight.to_dict(),
    }
    assert diagnostic.to_dict()["details"] == diagnostic.details


def test_raised_preflight_becomes_stable_sanitized_boundary_warning(tmp_path: Path) -> None:
    def broken_preflight(**_: object) -> PreflightResult:
        raise RuntimeError("ciphertext=/tmp/auth.enc; token=top-secret")

    boundary = evaluate_boundary(tmp_path, preflight_probe=broken_preflight)
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=SessionAssessment(True, True, "session_usable"),
        boundary=boundary,
        route_available=True,
    )

    assert boundary == BoundaryEvaluation(
        BoundaryState.UNKNOWN,
        reason="boundary_evaluation_failed",
    )
    assert [diagnostic.code for diagnostic in decision.diagnostics] == ["SAAS_SYNC_BOUNDARY_UNSAFE"]
    payload = str(decision.to_dict())
    assert "boundary_evaluation_failed" in payload
    assert "ciphertext" not in payload
    assert "top-secret" not in payload


def test_returned_preflight_evidence_omits_raw_fault_detail(tmp_path: Path) -> None:
    preflight = PreflightResult(
        ok=False,
        auth_required=False,
        unreadable_owner_record=UnreadableOwnerRecord(
            path=tmp_path / "owner.json",
            reason="invalid_json",
            detail="JSONDecodeError: ciphertext=filesystem-secret token=session-secret",
        ),
    )

    boundary = evaluate_boundary(tmp_path, preflight_probe=lambda **_: preflight)

    payload = str(boundary.evidence)
    assert "owner.json" in payload
    assert "invalid_json" in payload
    assert "JSONDecodeError" not in payload
    assert "filesystem-secret" not in payload
    assert "session-secret" not in payload


def test_project_store_diagnostic_is_replaced_with_stable_classification(tmp_path: Path) -> None:
    preflight = PreflightResult(
        ok=False,
        auth_required=False,
        project_store_diagnostic=(
            "RuntimeError: token=top-secret session=opaque-session "
            "ciphertext=/tmp/private/session.enc credential=hunter2"
        ),
    )

    boundary = evaluate_boundary(tmp_path, preflight_probe=lambda **_: preflight)
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=SessionAssessment(True, True, "session_usable"),
        boundary=boundary,
        route_available=True,
    )

    assert boundary.evidence is not None
    assert boundary.evidence["project_store_diagnostic"] == "project_store_unavailable"
    boundary_payload = str(boundary.evidence)
    decision_payload = str(decision.to_dict())
    for secret_fragment in (
        "RuntimeError",
        "top-secret",
        "opaque-session",
        "ciphertext",
        "/tmp/private/session.enc",
        "hunter2",
    ):
        assert secret_fragment not in boundary_payload
        assert secret_fragment not in decision_payload


def test_unavailable_route_is_not_an_auth_failure(tmp_path: Path) -> None:
    decision = assess_hosted_sync(
        requested=True,
        repo_root=tmp_path,
        auth_probe=lambda **_: (AuthStatus.AUTHENTICATED, None),
        preflight_probe=lambda **_: PreflightResult(ok=True, auth_required=False),
        route_probe=lambda _: _routing(tmp_path, available=False),
    )

    assert [diagnostic.code for diagnostic in decision.diagnostics] == ["SAAS_SYNC_ROUTE_UNAVAILABLE"]


def test_route_probe_failure_is_sanitized_and_nonfatal(tmp_path: Path) -> None:
    def broken_route(_: Path) -> CheckoutSyncRouting:
        raise RuntimeError("session-object token=route-secret")

    decision = assess_hosted_sync(
        requested=True,
        repo_root=tmp_path,
        auth_probe=lambda **_: (AuthStatus.AUTHENTICATED, None),
        preflight_probe=lambda **_: PreflightResult(ok=True, auth_required=False),
        route_probe=broken_route,
    )

    assert [diagnostic.code for diagnostic in decision.diagnostics] == ["SAAS_SYNC_ROUTE_UNAVAILABLE"]
    payload = str(decision.to_dict())
    assert "route_evaluation_failed" in payload
    assert "route-secret" not in payload


def test_combined_diagnostics_are_distinct_deduplicated_and_ordered() -> None:
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=SessionAssessment(False, None, "storage_read_failed"),
        boundary=BoundaryEvaluation(BoundaryState.UNSAFE, "structural_preflight_failed"),
        route_available=False,
    )

    assert decision.allow_effects is False
    assert [diagnostic.code for diagnostic in decision.diagnostics] == [
        "SAAS_SYNC_AUTH_UNKNOWN",
        "SAAS_SYNC_BOUNDARY_UNSAFE",
        "SAAS_SYNC_ROUTE_UNAVAILABLE",
    ]
    assert len({diagnostic.code for diagnostic in decision.diagnostics}) == 3
    assert all(diagnostic.severity == "warning" for diagnostic in decision.diagnostics)
    assert all(diagnostic.hosted_disposition == "refused" for diagnostic in decision.diagnostics)


@pytest.mark.parametrize(
    ("assessment", "boundary", "route_available"),
    [
        (SessionAssessment(True, False, "session_absent"), BoundaryEvaluation(BoundaryState.SAFE), True),
        (SessionAssessment(False, None, "storage_read_failed"), BoundaryEvaluation(BoundaryState.SAFE), True),
        (SessionAssessment(True, True, "session_usable"), BoundaryEvaluation(BoundaryState.UNSAFE, "unsafe"), True),
        (SessionAssessment(True, True, "session_usable"), BoundaryEvaluation(BoundaryState.UNKNOWN, "unknown"), True),
        (SessionAssessment(True, True, "session_usable"), BoundaryEvaluation(BoundaryState.SAFE), False),
    ],
)
def test_every_nonaffirmative_input_refuses(
    assessment: SessionAssessment,
    boundary: BoundaryEvaluation,
    route_available: bool,
) -> None:
    assert (
        decide_hosted_sync(
            requested=True,
            session_assessment=assessment,
            boundary=boundary,
            route_available=route_available,
        ).allow_effects
        is False
    )


def test_canonical_collectors_receive_exact_arguments(tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []

    def auth_probe(*, repo_root: Path | None = None) -> tuple[AuthStatus, None]:
        calls.append(("auth", repo_root))
        return (AuthStatus.AUTHENTICATED, None)

    def preflight_probe(*, repo_root: Path, require_auth: bool) -> PreflightResult:
        calls.append(("preflight", (repo_root, require_auth)))
        return PreflightResult(ok=True, auth_required=require_auth)

    def route_probe(repo_root: Path) -> CheckoutSyncRouting:
        calls.append(("route", repo_root))
        return _routing(repo_root, available=True)

    decision = assess_hosted_sync(
        requested=True,
        repo_root=tmp_path,
        auth_probe=auth_probe,
        preflight_probe=preflight_probe,
        route_probe=route_probe,
    )

    assert decision.allow_effects is True
    assert calls == [
        ("auth", tmp_path),
        ("preflight", (tmp_path, False)),
        ("route", tmp_path),
    ]


def test_public_serialization_contains_only_plain_json_values(tmp_path: Path) -> None:
    decision = assess_hosted_sync(
        requested=True,
        repo_root=tmp_path,
        auth_probe=lambda **_: (AuthStatus.UNKNOWN, None),
        preflight_probe=lambda **_: PreflightResult(ok=False, auth_required=False),
        route_probe=lambda _: None,
    )

    def assert_plain(value: Any) -> None:
        if isinstance(value, dict):
            assert all(isinstance(key, str) for key in value)
            for item in value.values():
                assert_plain(item)
        elif isinstance(value, list):
            for item in value:
                assert_plain(item)
        else:
            assert value is None or isinstance(value, (str, int, float, bool))

    assert_plain(decision.to_dict())


def test_test_helpers_are_typed() -> None:
    """Keep Callable imported so strict type checking covers injected seams."""
    def empty_probe() -> None:
        return None

    probe: Callable[..., object] = empty_probe
    assert probe() is None
