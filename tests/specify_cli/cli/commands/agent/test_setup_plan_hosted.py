"""Truth-table tests for setup-plan's hosted assessment adapter."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from itertools import product
from pathlib import Path
import socket
import statistics
import time
from types import SimpleNamespace
from typing import Any, cast

import pytest

from specify_cli.auth.token_manager import SessionAssessment
from specify_cli.cli.commands.agent import setup_plan_hosted as hosted_adapter
from specify_cli.cli.commands.agent.setup_plan_hosted import (
    BoundaryEvaluation,
    BoundaryState,
    HostedSyncDecision,
    HostedSyncDiagnostic,
    acquire_session_assessment,
    decide_hosted_sync,
    evaluate_boundary,
    evaluate_route_availability,
)
from specify_cli.sync.owner import UnreadableOwnerRecord
from specify_cli.sync.preflight import PreflightResult
from specify_cli.sync.routing import CheckoutSyncRouting

pytestmark = pytest.mark.fast


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


def _collect_requested_decision(
    repo_root: Path,
    *,
    assessment: SessionAssessment,
    preflight_probe: Callable[..., PreflightResult],
    route_probe: Callable[[Path], CheckoutSyncRouting | None],
) -> HostedSyncDecision:
    acquired = acquire_session_assessment(
        repo_root,
        token_manager_factory=lambda: type("TM", (), {"session_assessment": assessment})(),
    )
    boundary = evaluate_boundary(repo_root, preflight_probe=preflight_probe)
    route_available, route_reason = evaluate_route_availability(repo_root, route_probe=route_probe)
    return decide_hosted_sync(
        requested=True,
        session_assessment=acquired,
        boundary=boundary,
        route_available=route_available,
        route_reason=route_reason,
    )


def test_disabled_decision_requires_no_acquired_evidence() -> None:
    decision = decide_hosted_sync(requested=False)

    assert decision.requested is False
    assert decision.allow_effects is False
    assert decision.diagnostics == ()
    assert decision.to_dict() == {
        "requested": False,
        "allow_effects": False,
        "diagnostics": [],
    }


def test_requested_decision_without_evidence_fails_closed() -> None:
    decision = decide_hosted_sync(requested=True)

    assert decision.allow_effects is False
    assert [diagnostic.code for diagnostic in decision.diagnostics] == [
        "SAAS_SYNC_AUTH_UNKNOWN",
        "SAAS_SYNC_BOUNDARY_UNSAFE",
        "SAAS_SYNC_ROUTE_UNAVAILABLE",
    ]


def test_all_affirmative_evidence_allows_hosted_effects(tmp_path: Path) -> None:
    decision = _collect_requested_decision(
        tmp_path,
        assessment=SessionAssessment(True, True, "session_usable"),
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
    def broken_auth() -> object:
        raise RuntimeError("secret-token-auth-explosion")

    assessment = acquire_session_assessment(
        tmp_path,
        token_manager_factory=broken_auth,
    )
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=assessment,
        boundary=BoundaryEvaluation(BoundaryState.SAFE),
        route_available=True,
    )

    assert [diagnostic.code for diagnostic in decision.diagnostics] == ["SAAS_SYNC_AUTH_UNKNOWN"]
    assert "secret-token-auth-explosion" not in str(decision.to_dict())


def test_direct_completed_no_session_assessment_remains_logged_out(tmp_path: Path) -> None:
    """No Teamspace/context projection may erase a conclusive no-session verdict."""
    expected = SessionAssessment(True, False, "session_absent")

    actual = acquire_session_assessment(
        tmp_path,
        token_manager_factory=lambda: SimpleNamespace(session_assessment=expected),
    )

    assert actual == expected
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=actual,
        boundary=BoundaryEvaluation(BoundaryState.SAFE),
        route_available=True,
    )
    assert [item.code for item in decision.diagnostics] == ["SAAS_SYNC_UNAUTHENTICATED"]


@pytest.mark.parametrize(
    "assessment",
    (
        SimpleNamespace(completed=1, usable_session=True, reason="session_usable"),
        SimpleNamespace(completed=True, usable_session=1, reason="session_usable"),
        SimpleNamespace(completed=True, usable_session=True, reason=object()),
    ),
)
def test_auth_adapter_requires_exact_typed_affirmative_evidence(
    tmp_path: Path,
    assessment: object,
) -> None:
    actual = acquire_session_assessment(
        tmp_path,
        token_manager_factory=lambda: SimpleNamespace(session_assessment=assessment),
    )
    assert actual == SessionAssessment(False, None, "auth_evaluation_failed")


@pytest.mark.parametrize("faulty_attribute", ("session_assessment", "completed", "usable_session", "reason"))
def test_session_assessment_property_failures_are_stable_unknown(
    tmp_path: Path,
    faulty_attribute: str,
) -> None:
    """Every property-access seam is inside the no-raise auth adapter."""
    class _HostileAssessment:
        def __getattribute__(self, name: str) -> object:
            if name == faulty_attribute:
                raise RuntimeError("token=hostile-auth-property")
            values: dict[str, object] = {
                "completed": True,
                "usable_session": True,
                "reason": "session_usable",
            }
            if name in values:
                return values[name]
            return object.__getattribute__(self, name)

    class _HostileManager:
        @property
        def session_assessment(self) -> object:
            if faulty_attribute == "session_assessment":
                raise RuntimeError("token=hostile-manager-property")
            return _HostileAssessment()

    assessment = acquire_session_assessment(
        tmp_path,
        token_manager_factory=_HostileManager,
    )

    assert assessment == SessionAssessment(False, None, "auth_evaluation_failed")
    assert "hostile" not in str(assessment)


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
        raise RuntimeError("ciphertext=isolated/auth.enc; token=top-secret")

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


def test_preflight_integer_truth_is_not_affirmative(tmp_path: Path) -> None:
    malformed = SimpleNamespace(ok=1, to_dict=lambda: {"ok": 1})
    boundary = evaluate_boundary(
        tmp_path,
        preflight_probe=lambda **_: cast(PreflightResult, malformed),
    )
    assert boundary == BoundaryEvaluation(
        BoundaryState.UNKNOWN,
        "boundary_evaluation_failed",
    )


@pytest.mark.parametrize("failure", ("ok_property", "to_dict", "sanitizer"))
def test_malformed_preflight_objects_fail_closed_across_all_adapter_seams(
    tmp_path: Path,
    failure: str,
) -> None:
    class _HostileMapping(Mapping[str, object]):
        def __getitem__(self, key: str) -> object:
            raise RuntimeError(f"token=mapping-secret:{key}")

        def __iter__(self) -> Iterator[str]:
            return iter(("ok",))

        def __len__(self) -> int:
            return 1

        def get(self, key: str, default: object = None) -> object:
            raise RuntimeError(f"token=sanitizer-secret:{key}")

    class _HostilePreflight:
        @property
        def ok(self) -> bool:
            if failure == "ok_property":
                raise RuntimeError("token=ok-property-secret")
            return False

        def to_dict(self) -> object:
            if failure == "to_dict":
                raise RuntimeError("token=to-dict-secret")
            return _HostileMapping()

    boundary = evaluate_boundary(
        tmp_path,
        preflight_probe=lambda **_: cast(PreflightResult, _HostilePreflight()),
    )

    assert boundary == BoundaryEvaluation(
        BoundaryState.UNKNOWN,
        "boundary_evaluation_failed",
    )
    assert "secret" not in str(boundary)


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
    assert "invalid_json" in payload
    assert "owner.json" not in payload
    assert "JSONDecodeError" not in payload
    assert "filesystem-secret" not in payload
    assert "session-secret" not in payload


def test_project_store_diagnostic_is_replaced_with_stable_classification(tmp_path: Path) -> None:
    preflight = PreflightResult(
        ok=False,
        auth_required=False,
        project_store_diagnostic=(
            "RuntimeError: token=top-secret session=opaque-session "
            "ciphertext=isolated/private/session.enc credential=hunter2"
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
        "isolated/private/session.enc",
        "hunter2",
    ):
        assert secret_fragment not in boundary_payload
        assert secret_fragment not in decision_payload


class _SecretObject:
    def __str__(self) -> str:
        return "RuntimeError token=object-secret ciphertext=isolated/object.session"


@pytest.mark.parametrize(
    "diagnostic",
    [
        decide_hosted_sync(
            requested=True,
            session_assessment=SessionAssessment(
                False,
                None,
                "RuntimeError token=auth-secret ciphertext=isolated/auth.session",
            ),
            boundary=BoundaryEvaluation(BoundaryState.SAFE),
            route_available=True,
        ).diagnostics[0],
        decide_hosted_sync(
            requested=True,
            session_assessment=SessionAssessment(True, True, "session_usable"),
            boundary=BoundaryEvaluation(
                BoundaryState.UNSAFE,
                "RuntimeError token=boundary-reason-secret",
                evidence={
                    "unknown_key": "ciphertext=isolated/evidence.session token=evidence-secret",
                    "unknown_object": _SecretObject(),
                },
            ),
            route_available=True,
        ).diagnostics[0],
        decide_hosted_sync(
            requested=True,
            session_assessment=SessionAssessment(True, True, "session_usable"),
            boundary=BoundaryEvaluation(BoundaryState.SAFE),
            route_available=False,
            route_reason="RuntimeError token=route-secret ciphertext=isolated/route.session",
        ).diagnostics[0],
        HostedSyncDiagnostic(
            code="SAAS_SYNC_BOUNDARY_UNSAFE",
            severity="warning",
            hosted_disposition="refused",
            message="Hosted sync was skipped; local setup-plan continued.",
            details={
                "reason": "RuntimeError token=direct-reason-secret",
                "evidence": {
                    "unknown_key": "ciphertext=isolated/direct.session token=direct-secret",
                    "unknown_object": _SecretObject(),
                },
            },
        ),
    ],
    ids=("session_reason", "boundary_reason_and_evidence", "route_reason", "direct_details"),
)
def test_every_public_detail_seam_drops_arbitrary_strings_and_objects(
    diagnostic: HostedSyncDiagnostic,
) -> None:
    diagnostic_payload = str(diagnostic.to_dict())
    decision_payload = str(HostedSyncDecision(True, False, (diagnostic,)).to_dict())

    for forbidden in (
        "RuntimeError",
        "token=",
        "ciphertext",
        "isolated/",
        "secret",
        "unknown_key",
        "unknown_object",
    ):
        assert forbidden not in diagnostic_payload
        assert forbidden not in decision_payload


def test_safe_classifications_and_primitive_evidence_are_preserved() -> None:
    diagnostic = HostedSyncDiagnostic(
        code="SAAS_SYNC_BOUNDARY_UNSAFE",
        severity="warning",
        hosted_disposition="refused",
        message="Hosted sync was skipped; local setup-plan continued.",
        details={
            "reason": "structural_preflight_failed",
            "evidence": {
                "ok": False,
                "legacy_event_rows": 2,
                "legacy_body_upload_rows": 3,
                "legacy_rows_for_scope": 5,
                "auth_present": True,
                "auth_required": False,
                "project_store_diagnostic": "project_store_unavailable",
                "unknown": "must-not-survive",
            },
        },
    )

    assert diagnostic.to_dict()["details"] == {
        "reason": "structural_preflight_failed",
        "evidence": {
            "ok": False,
            "legacy_event_rows": 2,
            "legacy_body_upload_rows": 3,
            "legacy_rows_for_scope": 5,
            "auth_present": True,
            "auth_required": False,
            "project_store_diagnostic": "project_store_unavailable",
        },
    }


@pytest.mark.parametrize(
    ("assessment", "boundary", "route_available"),
    list(
        product(
            (
                SessionAssessment(True, True, "session_usable"),
                SessionAssessment(True, False, "session_absent"),
                SessionAssessment(False, None, "storage_read_failed"),
            ),
            (
                BoundaryEvaluation(BoundaryState.SAFE),
                BoundaryEvaluation(BoundaryState.UNSAFE, "structural_preflight_failed"),
                BoundaryEvaluation(BoundaryState.UNKNOWN, "boundary_evaluation_failed"),
            ),
            (True, False),
        )
    ),
)
def test_exhaustive_truth_table_keeps_one_allowing_row_and_diagnostic_order(
    assessment: SessionAssessment,
    boundary: BoundaryEvaluation,
    route_available: bool,
) -> None:
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=assessment,
        boundary=boundary,
        route_available=route_available,
    )

    expected_allow = (
        assessment.usable_session is True
        and boundary.state is BoundaryState.SAFE
        and route_available
    )
    assert decision.allow_effects is expected_allow
    expected_order = {
        "SAAS_SYNC_UNAUTHENTICATED": 0,
        "SAAS_SYNC_AUTH_UNKNOWN": 0,
        "SAAS_SYNC_BOUNDARY_UNSAFE": 1,
        "SAAS_SYNC_ROUTE_UNAVAILABLE": 2,
    }
    positions = [expected_order[diagnostic.code] for diagnostic in decision.diagnostics]
    assert positions == sorted(positions)


def test_unavailable_route_is_not_an_auth_failure(tmp_path: Path) -> None:
    decision = _collect_requested_decision(
        tmp_path,
        assessment=SessionAssessment(True, True, "session_usable"),
        preflight_probe=lambda **_: PreflightResult(ok=True, auth_required=False),
        route_probe=lambda _: _routing(tmp_path, available=False),
    )

    assert [diagnostic.code for diagnostic in decision.diagnostics] == ["SAAS_SYNC_ROUTE_UNAVAILABLE"]


def test_route_probe_failure_is_sanitized_and_nonfatal(tmp_path: Path) -> None:
    def broken_route(_: Path) -> CheckoutSyncRouting:
        raise RuntimeError("session-object token=route-secret")

    decision = _collect_requested_decision(
        tmp_path,
        assessment=SessionAssessment(True, True, "session_usable"),
        preflight_probe=lambda **_: PreflightResult(ok=True, auth_required=False),
        route_probe=broken_route,
    )

    assert [diagnostic.code for diagnostic in decision.diagnostics] == ["SAAS_SYNC_ROUTE_UNAVAILABLE"]
    payload = str(decision.to_dict())
    assert "route_evaluation_failed" in payload
    assert "route-secret" not in payload


@pytest.mark.parametrize("faulty_property", ("project_uuid", "effective_sync_enabled"))
def test_route_property_failures_are_sanitized_and_invoked_once(
    tmp_path: Path,
    faulty_property: str,
) -> None:
    calls = 0

    class _HostileRoute:
        def __getattribute__(self, name: str) -> object:
            if name == faulty_property:
                raise RuntimeError("token=route-property-secret")
            values: dict[str, object] = {
                "project_uuid": "project-123",
                "effective_sync_enabled": True,
            }
            if name in values:
                return values[name]
            return object.__getattribute__(self, name)

    def route_probe(_root: Path) -> object:
        nonlocal calls
        calls += 1
        return _HostileRoute()

    available, reason = evaluate_route_availability(
        tmp_path,
        route_probe=cast(Callable[[Path], CheckoutSyncRouting | None], route_probe),
    )

    assert (available, reason) == (False, "route_evaluation_failed")
    assert calls == 1


def test_diagnostic_serialization_totalizes_hostile_mapping_access() -> None:
    class _HostileDetails(Mapping[str, object]):
        def __getitem__(self, key: str) -> object:
            raise RuntimeError(f"token=detail-secret:{key}")

        def __iter__(self) -> Iterator[str]:
            return iter(("reason",))

        def __len__(self) -> int:
            return 1

        def get(self, key: str, default: object = None) -> object:
            raise RuntimeError(f"token=detail-secret:{key}")

    diagnostic = HostedSyncDiagnostic(
        code="SAAS_SYNC_BOUNDARY_UNSAFE",
        severity="malicious",
        hosted_disposition="malicious",
        message="token=message-secret",
        details=_HostileDetails(),
    )

    payload = diagnostic.to_dict()
    assert payload["code"] == "SAAS_SYNC_BOUNDARY_UNSAFE"
    assert payload["severity"] == "warning"
    assert "secret" not in str(payload)


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

    class _TokenManager:
        @property
        def session_assessment(self) -> SessionAssessment:
            calls.append(("auth", "session_assessment"))
            return SessionAssessment(True, True, "session_usable")

    def token_manager_factory() -> _TokenManager:
        calls.append(("auth", "factory"))
        return _TokenManager()

    def preflight_probe(*, repo_root: Path, require_auth: bool) -> PreflightResult:
        calls.append(("preflight", (repo_root, require_auth)))
        return PreflightResult(ok=True, auth_required=require_auth)

    def route_probe(repo_root: Path) -> CheckoutSyncRouting:
        calls.append(("route", repo_root))
        return _routing(repo_root, available=True)

    assessment = acquire_session_assessment(
        tmp_path,
        token_manager_factory=token_manager_factory,
    )
    boundary = evaluate_boundary(tmp_path, preflight_probe=preflight_probe)
    route_available, route_reason = evaluate_route_availability(tmp_path, route_probe=route_probe)
    decision = decide_hosted_sync(
        requested=True,
        session_assessment=assessment,
        boundary=boundary,
        route_available=route_available,
        route_reason=route_reason,
    )

    assert decision.allow_effects is True
    assert calls == [
        ("auth", "factory"),
        ("auth", "session_assessment"),
        ("preflight", (tmp_path, False)),
        ("route", tmp_path),
    ]


def _p95_runtime(probe: Callable[[], object], *, samples: int = 25) -> float:
    """Return a scheduler-tolerant p95 for a small deterministic local probe."""
    probe()  # discard import/cache warm-up
    durations: list[float] = []
    for _ in range(samples):
        started = time.perf_counter()
        probe()
        durations.append(time.perf_counter() - started)
    return statistics.quantiles(durations, n=20, method="inclusive")[18]


def _assert_within_local_assessment_budget(probe: Callable[[], object]) -> None:
    p95 = _p95_runtime(probe)
    assert p95 < 0.100, f"local assessment p95 {p95:.6f}s exceeded 100ms"


def test_local_auth_and_coherent_boundary_meet_nfr_007_without_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """NFR-007: both evidence reads are local and remain below the 100ms budget."""
    network_attempts: list[tuple[object, ...]] = []

    def _forbid_network(*args: object, **_kwargs: object) -> None:
        network_attempts.append(args)
        raise AssertionError("local hosted-readiness assessment attempted network I/O")

    monkeypatch.setattr(socket, "create_connection", _forbid_network)
    manager = type(
        "LocalTokenManager",
        (),
        {"session_assessment": SessionAssessment(True, True, "session_usable")},
    )()
    preflight = PreflightResult(ok=True, auth_required=False)

    _assert_within_local_assessment_budget(
        lambda: acquire_session_assessment(tmp_path, token_manager_factory=lambda: manager)
    )
    _assert_within_local_assessment_budget(
        lambda: evaluate_boundary(tmp_path, preflight_probe=lambda **_: preflight)
    )
    assert network_attempts == []

    # Negative control: prove the no-network sentinel is live.
    with pytest.raises(AssertionError, match="network I/O"):
        socket.create_connection(("example.invalid", 443))


def test_nfr_007_budget_detector_rejects_a_slow_probe() -> None:
    """Negative control: a coherent probe moved beyond 100ms fails the gate."""
    with pytest.raises(AssertionError, match="exceeded 100ms"):
        _assert_within_local_assessment_budget(lambda: time.sleep(0.105))


def test_public_serialization_contains_only_plain_json_values(tmp_path: Path) -> None:
    decision = _collect_requested_decision(
        tmp_path,
        assessment=SessionAssessment(False, None, "auth_evaluation_failed"),
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


_WIRE_REGISTRY_EXPECTATIONS = {
    "SAAS_SYNC_UNAUTHENTICATED": (
        "Hosted sync was skipped because no usable local session is available; local setup-plan continued.",
        ["Log in before retrying hosted sync."],
    ),
    "SAAS_SYNC_AUTH_UNKNOWN": (
        "Hosted sync was skipped because local authentication could not be evaluated; local setup-plan continued.",
        ["Inspect local authentication storage before retrying hosted sync."],
    ),
    "SAAS_SYNC_BOUNDARY_UNSAFE": (
        "Hosted sync was skipped because the structural sync boundary was not safe; local setup-plan continued.",
        ["Resolve the reported sync-boundary condition before retrying hosted sync."],
    ),
    "SAAS_SYNC_ROUTE_UNAVAILABLE": (
        "Hosted sync was skipped because no permitted delivery route was available; local setup-plan continued.",
        ["Verify project identity and hosted-sync consent before retrying."],
    ),
}


@pytest.mark.parametrize(
    ("code", "expected"),
    list(_WIRE_REGISTRY_EXPECTATIONS.items()),
)
def test_registry_reconstructs_every_wire_field_for_both_serializers(
    code: str,
    expected: tuple[str, list[str]],
) -> None:
    sentinel = "RuntimeError token=caller-secret ciphertext=isolated/caller.session"
    diagnostic = HostedSyncDiagnostic(
        code=code,
        severity=sentinel,
        hosted_disposition=sentinel,
        message=sentinel,
        details={"reason": sentinel, "unknown": sentinel},
        remediation=(sentinel,),
    )
    diagnostic_payload = diagnostic.to_dict()
    decision_payload = HostedSyncDecision(True, False, (diagnostic,)).to_dict()
    decision_diagnostics = cast(list[dict[str, object]], decision_payload["diagnostics"])

    for payload in (diagnostic_payload, decision_diagnostics[0]):
        assert payload["code"] == code
        assert payload["severity"] == "warning"
        assert payload["hosted_disposition"] == "refused"
        assert payload["message"] == expected[0]
        assert payload["remediation"] == expected[1]
        assert sentinel not in str(payload)


def test_unknown_diagnostic_code_is_rejected_without_echo() -> None:
    sentinel = "UNKNOWN_TOKEN_top-secret_ciphertext"

    with pytest.raises(ValueError) as raised:
        HostedSyncDiagnostic(
            code=sentinel,
            severity="warning",
            hosted_disposition="refused",
            message="safe",
        )

    assert str(raised.value) == "unsupported hosted sync diagnostic code"
    assert sentinel not in str(raised.value)


def test_allowing_decision_rejects_diagnostics_without_echo() -> None:
    diagnostic = HostedSyncDiagnostic(
        code="SAAS_SYNC_ROUTE_UNAVAILABLE",
        severity="RuntimeError token=decision-secret",
        hosted_disposition="refused",
        message="safe",
    )

    with pytest.raises(ValueError) as raised:
        HostedSyncDecision(True, True, (diagnostic,))

    assert str(raised.value) == "allowing hosted sync decision cannot contain diagnostics"
    assert "decision-secret" not in str(raised.value)


def test_unrequested_decision_cannot_allow_hosted_effects() -> None:
    with pytest.raises(ValueError) as raised:
        HostedSyncDecision(False, True, ())

    assert str(raised.value) == "unrequested hosted sync decision cannot allow effects"


def test_requested_decision_cannot_allow_without_canonical_evidence() -> None:
    direct = HostedSyncDecision(True, True, ())

    assert direct.allow_effects is True
    assert hosted_adapter.is_canonical_hosted_sync_decision(direct) is False


def test_affirmative_authority_is_not_a_copyable_dataclass_field() -> None:
    assert "_authority" not in HostedSyncDecision.__dataclass_fields__
    assert not hasattr(hosted_adapter, "_DECISION_AUTHORITY")
    assert not hasattr(hosted_adapter, "_register_affirmative_decision")


def test_wire_registry_contains_exactly_four_codes() -> None:
    assert set(hosted_adapter._DIAGNOSTIC_REGISTRY) == set(_WIRE_REGISTRY_EXPECTATIONS)

    diagnostics = tuple(
        HostedSyncDiagnostic(
            code=code,
            severity="ignored",
            hosted_disposition="ignored",
            message="ignored",
        )
        for code in _WIRE_REGISTRY_EXPECTATIONS
    )

    wire_diagnostics = cast(
        list[dict[str, object]],
        HostedSyncDecision(True, False, diagnostics).to_dict()["diagnostics"],
    )
    wire_codes = {item["code"] for item in wire_diagnostics}
    assert wire_codes == set(_WIRE_REGISTRY_EXPECTATIONS)


def test_wire_registry_ssot_guard_rejects_temporary_fifth_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mutated_registry = {
        **hosted_adapter._DIAGNOSTIC_REGISTRY,
        "SAAS_SYNC_TEMPORARY_FIFTH": next(iter(hosted_adapter._DIAGNOSTIC_REGISTRY.values())),
    }
    monkeypatch.setattr(hosted_adapter, "_DIAGNOSTIC_REGISTRY", mutated_registry)

    with pytest.raises(AssertionError):
        assert set(hosted_adapter._DIAGNOSTIC_REGISTRY) == set(_WIRE_REGISTRY_EXPECTATIONS)
