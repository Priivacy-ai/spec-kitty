"""Direct unit tests for the setup-plan phase helpers (#2056 WP06, T022/T025).

The pre-decomposition ``setup_plan`` was a 507-LOC monolith; WP06 split it into
≤15-CC phase helpers. These tests exercise each helper's branches in isolation:
the SaaS auth refusal + boundary preflight gates, feature-dir resolution, the
spec gate, the plan-template scaffold, the plan-commit branch, the documentation
wiring no-op, and the result emitter. The relocated planning-commit helpers
(``_kind_for_artifact``, ``_artifact_absent_at_placement``, etc.) keep their
existing coverage via ``test_kind_for_artifact.py`` and
``test_agent_mission_commit_to_branch.py``; the end-to-end command stays pinned
by ``test_agent_feature.py``, ``test_mission_planning_entry.py`` and the WP01
golden harness.
"""

from __future__ import annotations

import copy
from io import BytesIO
import json
import os
import pickle
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tarfile
from types import MappingProxyType, SimpleNamespace
from typing import Any, cast

import pytest
import typer
from typer.testing import CliRunner

from charter.activation.mission_type_profiles import ResolvedMissionType
from charter.resolution import ResolutionResult, ResolutionTier
from specify_cli.cli.commands.agent import mission_setup_plan as seam
from specify_cli.cli.commands.agent import setup_plan_hosted_effects as hosted_effects
from specify_cli.cli.commands.agent.setup_plan_hosted import (
    BoundaryEvaluation,
    BoundaryState,
    HostedSyncDecision,
    HostedSyncDiagnostic,
    decide_hosted_sync,
    is_canonical_hosted_sync_decision,
)
from specify_cli.auth.token_manager import SessionAssessment
from specify_cli.core.paths import load_meta_fail_closed as canonical_load_meta_fail_closed
from specify_cli.runtime.resolver import TemplateConfigurationError

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_DEFAULT_TEMPLATE_SET = object()
_PRE_MISSION_GOLDEN = (
    Path(__file__).resolve().parents[4]
    / "fixtures"
    / "setup_plan_pre_mission_d060cff9_payloads.json"
)
_PRE_MISSION_REPLAY = (
    Path(__file__).resolve().parents[4]
    / "fixtures"
    / "setup_plan_pre_mission_replay.py"
)


def _resolved_mission_type(
    *,
    mission_type: str | None = "software-dev",
    template_set: dict[str, str] | None | object = _DEFAULT_TEMPLATE_SET,
) -> ResolvedMissionType:
    mapping = cast(
        dict[str, str] | None,
        {"spec": "spec-template.md", "plan": "mapped-plan.md"} if template_set is _DEFAULT_TEMPLATE_SET else template_set,
    )

    def _template_set() -> MappingProxyType[str, str] | None:
        return None if mapping is None else MappingProxyType(mapping)

    return ResolvedMissionType(
        mission_type=mission_type,
        governance_text="",
        action_sequence=["specify", "plan"],
        provenance="test",
        _template_set_thunk=(None if mission_type is None else _template_set),
    )


def _resolution(path: Path) -> ResolutionResult:
    return ResolutionResult(
        path=path,
        tier=ResolutionTier.OVERRIDE,
        mission="software-dev",
    )


def _diagnostic(code: str) -> HostedSyncDiagnostic:
    """Build one canonical warning through the WP02 decision authority."""
    from specify_cli.auth.token_manager import SessionAssessment
    from specify_cli.cli.commands.agent.setup_plan_hosted import decide_hosted_sync

    assessment = (
        SessionAssessment(False, None, "storage_read_failed")
        if code == "SAAS_SYNC_AUTH_UNKNOWN"
        else SessionAssessment(True, False, "session_absent")
    )
    return decide_hosted_sync(
        requested=True,
        session_assessment=assessment,
        boundary=BoundaryEvaluation(BoundaryState.SAFE),
        route_available=True,
    ).diagnostics[0]


@pytest.mark.parametrize(
    ("payload", "exit_code"),
    [
        ({"result": "success", "phase_complete": True}, 0),
        (
            {
                "result": "success",
                "phase_complete": False,
                "scaffold_only": True,
            },
            0,
        ),
        (
            {
                "result": "blocked",
                "phase_complete": False,
                "blocked_reason": "baseline reason",
            },
            0,
        ),
        ({"error_code": "SPEC_FILE_MISSING", "error": "baseline error"}, 1),
        (
            {
                "result": "error",
                "phase_complete": False,
                "error_code": "TEMPLATE_CONFIGURATION_ERROR",
            },
            1,
        ),
        ({"error": "baseline generic error"}, 1),
    ],
)
def test_local_outcome_reporter_preserves_complete_baseline_payload_and_exit(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    exit_code: int,
) -> None:
    """T013: hosted warnings are the only permitted baseline delta."""
    emitted: list[dict[str, object]] = []
    monkeypatch.setattr(seam, "_emit_json", lambda value: emitted.append(value))
    warning = _diagnostic("SAAS_SYNC_AUTH_UNKNOWN")

    outcome = seam.SetupPlanLocalOutcome(
        payload=payload,
        exit_code=exit_code,
        render_kind="error" if exit_code else "success",
    )
    seam._report_setup_plan_outcome(
        outcome,
        diagnostics=(warning,),
        json_output=True,
    )

    assert len(emitted) == 1
    actual = emitted[0]
    assert {key: value for key, value in actual.items() if key != "warnings"} == payload
    assert actual["warnings"] == [warning.to_dict()]
    assert outcome.exit_code == exit_code


def test_human_outcome_reporter_reconstructs_warning_from_closed_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Human rendering must not trust caller-provided diagnostic prose."""
    sentinel = "RuntimeError token=human-secret ciphertext=isolated/human.session"
    warning = HostedSyncDiagnostic(
        code="SAAS_SYNC_AUTH_UNKNOWN",
        severity=sentinel,
        hosted_disposition=sentinel,
        message=sentinel,
        details={"reason": sentinel, "evidence": sentinel},
        remediation=(sentinel,),
    )
    rendered: list[str] = []
    console = cast(Any, vars(seam)["console"])
    monkeypatch.setattr(console, "print", lambda value: rendered.append(str(value)))

    seam._report_setup_plan_outcome(
        seam.SetupPlanLocalOutcome(
            payload={"result": "success"},
            exit_code=0,
            render_kind="success",
        ),
        diagnostics=(warning,),
        json_output=False,
        human_message="local-result",
    )

    assert rendered == [
        "[yellow]Warning:[/yellow] Hosted sync was skipped because local authentication could not be evaluated; local setup-plan continued.",
        "local-result",
    ]
    assert sentinel not in str(rendered)


def test_hosted_effect_executor_refuses_lifecycle_but_not_local_dossier_capture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """T013/T015: a refused decision dominates hosted fan-out, not local capture.

    Dossier capture is project-isolated LOCAL capture (see
    ``trigger_feature_dossier_sync_if_enabled``'s own contract) and is never
    suppressed by a refused hosted-sync decision.
    """
    calls: list[str] = []
    monkeypatch.setattr(
        hosted_effects,
        "fanout_lifecycle_event_hosted",
        lambda *_a, **_k: calls.append("lifecycle"),
    )
    monkeypatch.setattr(
        hosted_effects,
        "_trigger_dossier_sync",
        lambda *_a, **_k: calls.append("dossier"),
    )
    decision = HostedSyncDecision(
        requested=True,
        allow_effects=False,
        diagnostics=(_diagnostic("SAAS_SYNC_UNAUTHENTICATED"),),
    )
    intent = seam.LifecycleEventIntent(
        envelope={"event_type": "PlanStarted"},
        log_path=tmp_path / "lifecycle.events.jsonl",
    )

    seam._execute_setup_plan_hosted_effects(
        decision,
        lifecycle_intents=(intent,),
        dossier_intent=seam.DossierSyncIntent(tmp_path, "001-demo", tmp_path),
    )

    assert calls == ["dossier"]


def _affirmative_decision() -> HostedSyncDecision:
    return decide_hosted_sync(
        requested=True,
        session_assessment=SessionAssessment(True, True, "session_usable"),
        boundary=BoundaryEvaluation(BoundaryState.SAFE),
        route_available=True,
    )


@pytest.mark.parametrize(
    "reconstruct",
    [
        pytest.param(lambda _decision: HostedSyncDecision(True, True, ()), id="direct"),
        pytest.param(replace, id="dataclasses-replace"),
        pytest.param(copy.copy, id="copy"),
        pytest.param(copy.deepcopy, id="deepcopy"),
        pytest.param(lambda decision: pickle.loads(pickle.dumps(decision)), id="pickle"),
    ],
)
def test_hosted_effect_executor_refuses_reconstructed_affirmative_decisions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reconstruct: Any,
) -> None:
    """Only the exact object issued by the evidence authority may execute
    lifecycle fan-out. Local dossier capture is unaffected by decision
    forgery — it is never gated by the decision at all."""
    calls: list[str] = []
    monkeypatch.setattr(
        hosted_effects,
        "fanout_lifecycle_event_hosted",
        lambda *_a, **_k: calls.append("lifecycle"),
    )
    monkeypatch.setattr(
        hosted_effects,
        "_trigger_dossier_sync",
        lambda *_a, **_k: calls.append("dossier"),
    )
    canonical = _affirmative_decision()
    reconstructed = cast(HostedSyncDecision, reconstruct(canonical))

    assert reconstructed.allow_effects is True
    assert reconstructed is not canonical
    assert is_canonical_hosted_sync_decision(reconstructed) is False

    seam._execute_setup_plan_hosted_effects(
        reconstructed,
        lifecycle_intents=(
            seam.LifecycleEventIntent(
                envelope={"event_type": "PlanStarted"},
                log_path=tmp_path / "lifecycle.events.jsonl",
            ),
        ),
        dossier_intent=seam.DossierSyncIntent(tmp_path, "001-demo", tmp_path),
    )

    assert calls == ["dossier"]


def test_hosted_effect_executor_accepts_exact_canonical_decision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        hosted_effects,
        "fanout_lifecycle_event_hosted",
        lambda *_a, **_k: calls.append("lifecycle"),
    )
    monkeypatch.setattr(
        hosted_effects,
        "_trigger_dossier_sync",
        lambda *_a, **_k: calls.append("dossier"),
    )
    canonical = _affirmative_decision()

    assert is_canonical_hosted_sync_decision(canonical) is True
    seam._execute_setup_plan_hosted_effects(
        canonical,
        lifecycle_intents=(
            seam.LifecycleEventIntent(
                envelope={"event_type": "PlanStarted"},
                log_path=tmp_path / "lifecycle.events.jsonl",
            ),
        ),
        dossier_intent=seam.DossierSyncIntent(tmp_path, "001-demo", tmp_path),
    )

    assert calls == ["lifecycle", "dossier"]


def test_dossier_adapter_always_fires_and_is_exception_safe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Dossier capture is local-only: it is never gated by any decision, and a
    raising sink is swallowed rather than escaping to the caller."""
    calls: list[str] = []
    monkeypatch.setattr(
        hosted_effects,
        "trigger_feature_dossier_sync_if_enabled",
        lambda *_a, **_k: calls.append("dossier"),
    )
    intent = seam.DossierSyncIntent(tmp_path, "001-demo", tmp_path)

    hosted_effects._trigger_dossier_sync(intent)
    assert calls == ["dossier"]

    def _boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("dossier sink failure")

    monkeypatch.setattr(hosted_effects, "trigger_feature_dossier_sync_if_enabled", _boom)
    hosted_effects._trigger_dossier_sync(intent)  # must not raise


def test_collect_hosted_decision_disabled_touches_no_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")
    for name in (
        "acquire_session_assessment",
        "evaluate_boundary",
        "evaluate_route_availability",
    ):
        monkeypatch.setattr(
            seam,
            name,
            lambda *_a, _name=name, **_k: pytest.fail(f"disabled probe touched: {_name}"),
        )

    decision = seam._collect_hosted_sync_decision(tmp_path)

    assert decision.requested is False
    assert decision.allow_effects is False
    assert decision.diagnostics == ()


def test_human_reporter_renders_warning_then_local_result(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seam._report_setup_plan_outcome(
        seam.SetupPlanLocalOutcome(
            payload={"result": "success", "phase_complete": True},
            exit_code=0,
            render_kind="success",
        ),
        diagnostics=(_diagnostic("SAAS_SYNC_UNAUTHENTICATED"),),
        json_output=False,
        human_message="LOCAL RESULT",
    )

    output = capsys.readouterr().out
    assert "Warning:" in output
    assert "Hosted sync was skipped" in output
    assert output.index("Warning:") < output.index("LOCAL RESULT")


def test_real_setup_plan_git_preflight_failure_precedes_and_skips_hosted_assessment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An early local failure keeps its exact payload and never probes hosted state."""
    from specify_cli.cli.commands.agent import mission as mission_mod

    emitted: list[dict[str, object]] = []
    baseline = {
        "result": "error",
        "error_code": "GIT_PREFLIGHT_FAILED",
        "error": "baseline git failure",
        "remediation": ["git worktree prune"],
    }
    monkeypatch.setattr(
        seam,
        "_collect_hosted_sync_decision",
        lambda _root: pytest.fail("hosted assessment ran before local git verification"),
    )
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_emit_json", lambda payload: emitted.append(payload))

    def _git_failure(*_args: object, **_kwargs: object) -> None:
        mission_mod._emit_json(dict(baseline))
        raise typer.Exit(1)

    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", _git_failure)

    with pytest.raises(typer.Exit) as exc_info:
        seam.setup_plan(feature="001-demo", json_output=True)

    assert exc_info.value.exit_code == 1
    assert len(emitted) == 1
    actual = emitted[0]
    assert actual == baseline


_LOCAL_OUTCOME_CASES: dict[str, dict[str, object]] = {
    "substantive_complete": {"plan_substantive": True},
    "pristine_scaffold": {"plan_exists": False},
    "populated_insufficient": {},
    "committed_insufficient": {"plan_committed": True},
    "non_substantive_spec": {"spec_substantive": False},
    "uncommitted_spec": {"spec_committed": False},
    "missing_spec": {"spec_exists": False},
    "template_configuration": {"template_error": "configuration"},
    "missing_template": {"template_error": "missing"},
    "generic_local_exception": {"template_error": "generic"},
    "context_resolution": {"context_error": True},
    "git_preflight": {"git_error": True},
}

_READINESS_VARIANTS = (
    "usable",
    "logged_out",
    "auth_exception",
    "boundary_unsafe",
    "boundary_exception",
    "route_null",
    "route_denied",
    "route_exception",
)


def _seed_local_case(root: Path, case: dict[str, object]) -> tuple[Path, Path]:
    feature_dir = root / "kitty-specs" / "001-matrix"
    feature_dir.mkdir(parents=True, exist_ok=True)
    spec_file = feature_dir / "spec.md"
    plan_file = feature_dir / "plan.md"
    if bool(case.get("spec_exists", True)):
        spec_file.write_text(
            "# Spec\n\n## Functional Requirements\n\n- FR-001: Real content.\n",
            encoding="utf-8",
        )
    else:
        spec_file.unlink(missing_ok=True)
    if bool(case.get("plan_exists", True)):
        plan_file.write_text("# Plan\n\nPopulated but insufficient.\n", encoding="utf-8")
    else:
        plan_file.unlink(missing_ok=True)
    return feature_dir, plan_file


def _patch_readiness_variant(
    mp: pytest.MonkeyPatch,
    variant: str,
) -> None:
    mp.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    if variant == "auth_exception":
        mp.setattr(
            seam,
            "acquire_session_assessment",
            lambda _root: (_ for _ in ()).throw(RuntimeError("auth sentinel")),
        )
    else:
        assessment = (
            SessionAssessment(True, False, "session_absent")
            if variant == "logged_out"
            else SessionAssessment(True, True, "session_usable")
        )
        mp.setattr(seam, "acquire_session_assessment", lambda _root: assessment)

    if variant == "boundary_exception":
        mp.setattr(
            "specify_cli.sync.preflight.run_preflight",
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boundary sentinel")),
        )
    else:
        boundary = (
            BoundaryEvaluation(BoundaryState.UNSAFE, "structural_preflight_failed")
            if variant == "boundary_unsafe"
            else BoundaryEvaluation(BoundaryState.SAFE)
        )
        mp.setattr(seam, "evaluate_boundary", lambda _root: boundary)

    if variant in {"route_null", "route_denied", "route_exception"}:
        def _route_null(_root: Path) -> None:
            return None

        def _route_denied(_root: Path) -> SimpleNamespace:
            return SimpleNamespace(
                project_uuid="",
                effective_sync_enabled=False,
            )

        def _route_exception(_root: Path) -> None:
            raise RuntimeError("route sentinel")

        route_probe: Callable[[Path], object | None]
        if variant == "route_null":
            route_probe = _route_null
        elif variant == "route_denied":
            route_probe = _route_denied
        else:
            route_probe = _route_exception
        mp.setattr(
            "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly",
            route_probe,
        )
    else:
        mp.setattr(seam, "evaluate_route_availability", lambda _root: (True, None))


def _invoke_matrix_case(  # noqa: C901 - acceptance fixture encodes the binding matrix
    mp: pytest.MonkeyPatch,
    root: Path,
    case: dict[str, object],
    readiness: str | None,
    *,
    refused_sink_calls: list[str] | None = None,
    invoke_through_parser: bool = False,
    human_output: bool = False,
) -> tuple[dict[str, object], int, str]:
    from specify_cli.cli.commands.agent import mission as mission_mod

    # Branch-contract timestamps are the only documented volatile fields in the
    # setup-plan envelope. Freeze the shared producer so baseline and readiness
    # variants compare the complete payload rather than racing the wall clock.
    mp.setattr(
        "specify_cli.cli.commands.agent.mission_branch_context._utc_now_iso",
        lambda: "2026-08-23T00:00:00Z",
    )
    feature_dir, plan_file = _seed_local_case(root, case)
    template = root / "plan-template.md"
    template.write_text(
        "# Plan\n\n## Technical Context\n\n**Language/Version**: [NEEDS CLARIFICATION]\n",
        encoding="utf-8",
    )
    emitted: list[dict[str, object]] = []
    if not invoke_through_parser and not human_output:
        mp.setattr(mission_mod, "_emit_json", lambda payload: emitted.append(dict(payload)))
    mp.setattr(mission_mod, "locate_project_root", lambda: root)
    if bool(case.get("git_error")):
        git_payload = {
            "result": "error",
            "error_code": "GIT_PREFLIGHT_FAILED",
            "error": "baseline git failure",
            "remediation": ["git worktree prune"],
        }

        def _git_failure(*_args: object, **_kwargs: object) -> None:
            mission_mod._emit_json(dict(git_payload))
            raise typer.Exit(1)

        mp.setattr(mission_mod, "_enforce_git_preflight", _git_failure)
    else:
        mp.setattr(mission_mod, "_enforce_git_preflight", lambda *_a, **_k: None)
    if bool(case.get("context_error")):
        mp.setattr(
            mission_mod,
            "_find_feature_directory",
            lambda *_a, **_k: (_ for _ in ()).throw(ValueError("context failure")),
        )
    else:
        mp.setattr(mission_mod, "_find_feature_directory", lambda *_a, **_k: feature_dir)
    mp.setattr(mission_mod, "_planning_read_dir", lambda *_a, **_k: feature_dir)
    mp.setattr(mission_mod, "_show_branch_context", lambda *_a, **_k: (root, "main"))
    mp.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    mp.setattr(mission_mod, "_branch_tree_relative_path", lambda path, _root: path.name)
    mp.setattr(
        mission_mod,
        "_commit_to_branch",
        lambda *_a, **_k: seam.CommitToBranchResult(
            status="committed",
            placement_ref="main",
            commit_hash="abc123",
        ),
    )
    mp.setattr(seam, "_resolve_branch_match_operands", lambda *_a, **_k: ("main", "main"))
    mp.setattr(seam, "_run_documentation_wiring", lambda *_a, **_k: (None, []))
    def _record_sink(name: str) -> Any:
        def _record(*_args: object, **_kwargs: object) -> None:
            if refused_sink_calls is not None:
                refused_sink_calls.append(name)

        return _record

    mp.setattr(hosted_effects, "_trigger_dossier_sync", _record_sink("dossier"))
    mp.setattr(
        hosted_effects,
        "fanout_lifecycle_event_hosted",
        _record_sink("lifecycle_fanout"),
    )
    mp.setattr(
        "specify_cli.sync.queue.OfflineQueue.queue_event",
        _record_sink("event_outbox"),
    )
    mp.setattr(
        "specify_cli.sync.body_queue.OfflineBodyUploadQueue.enqueue",
        _record_sink("body_outbox"),
    )
    mp.setattr(
        "specify_cli.sync.events._request_dashboard_sync",
        _record_sink("dashboard_sync"),
    )
    mp.setattr(
        "specify_cli.sync.events._publish_event_via_sync_daemon",
        _record_sink("daemon_publish"),
    )
    mp.setattr("specify_cli.auth.transport.get_client", _record_sink("http_client"))

    template_error = case.get("template_error")
    if template_error == "configuration":
        error = TemplateConfigurationError(
            mission_type="software-dev",
            artifact_kind="plan",
            reason="has no configured template",
        )
        mp.setattr(
            seam,
            "_resolve_plan_template",
            lambda *_a, **_k: (_ for _ in ()).throw(error),
        )
    elif template_error == "missing":
        mp.setattr(
            seam,
            "_resolve_plan_template",
            lambda *_a, **_k: (_ for _ in ()).throw(FileNotFoundError("missing")),
        )
    elif template_error == "generic":
        mp.setattr(
            seam,
            "_resolve_plan_template",
            lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("generic local failure")),
        )
    else:
        mp.setattr(seam, "_resolve_plan_template", lambda *_a, **_k: _resolution(template))

    def _is_substantive(path: Path, artifact_type: str) -> bool:
        if artifact_type == "spec":
            return bool(case.get("spec_substantive", True))
        assert path == plan_file
        return bool(case.get("plan_substantive", False))

    def _is_committed(
        path: Path,
        _root: Path,
        diagnostics: list[str] | None = None,
    ) -> bool:
        if diagnostics is not None:
            diagnostics.append("matrix-surface")
        if path.name == "spec.md":
            return bool(case.get("spec_committed", True))
        return bool(case.get("plan_committed", False))

    mp.setattr("specify_cli.missions._substantive.is_substantive", _is_substantive)
    mp.setattr("specify_cli.missions._substantive.is_committed", _is_committed)
    if readiness is None:
        mp.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")
        for probe in (
            "acquire_session_assessment",
            "evaluate_boundary",
            "evaluate_route_availability",
        ):
            mp.setattr(
                seam,
                probe,
                lambda *_a, _probe=probe, **_k: pytest.fail(
                    f"disabled probe touched: {_probe}"
                ),
            )
    else:
        _patch_readiness_variant(mp, readiness)

    if invoke_through_parser:
        result = CliRunner().invoke(
            mission_mod.app,
            ["setup-plan", "--mission", "001-matrix", "--json"],
        )
        exit_code = result.exit_code
        wire = result.stdout.strip()
    else:
        exit_code = 0
        try:
            seam.setup_plan(feature="001-matrix", json_output=not human_output)
        except typer.Exit as exc:
            exit_code = exc.exit_code
        if human_output:
            return {}, exit_code, ""
        assert len(emitted) == 1
        wire = json.dumps(emitted[0], sort_keys=True)
    decoded, end = json.JSONDecoder().raw_decode(wire)
    assert wire[end:].strip() == ""
    assert isinstance(decoded, dict)
    return decoded, exit_code, wire


@pytest.mark.parametrize("case_name", tuple(_LOCAL_OUTCOME_CASES))
def test_real_setup_plan_preserves_full_local_matrix_across_readiness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_name: str,
) -> None:
    """T013/T017: real entry-point baseline differs only by warnings."""
    case = _LOCAL_OUTCOME_CASES[case_name]
    with monkeypatch.context() as mp:
        baseline, baseline_exit, _wire = _invoke_matrix_case(mp, tmp_path, case, None)

    for variant in _READINESS_VARIANTS:
        with monkeypatch.context() as mp:
            actual, actual_exit, wire = _invoke_matrix_case(mp, tmp_path, case, variant)
        primary = {key: value for key, value in actual.items() if key != "warnings"}
        assert primary == baseline, (case_name, variant, wire)
        assert actual_exit == baseline_exit, (case_name, variant)
        warning_codes = [
            warning["code"]
            for warning in cast(list[dict[str, object]], actual.get("warnings", []))
        ]
        if case_name in {"context_resolution", "git_preflight"} or variant == "usable":
            assert warning_codes == []
        elif variant == "logged_out":
            assert warning_codes == ["SAAS_SYNC_UNAUTHENTICATED"]
        elif variant == "auth_exception":
            assert warning_codes == ["SAAS_SYNC_AUTH_UNKNOWN"]
        elif variant in {"boundary_unsafe", "boundary_exception"}:
            assert warning_codes == ["SAAS_SYNC_BOUNDARY_UNSAFE"]
        else:
            assert warning_codes == ["SAAS_SYNC_ROUTE_UNAVAILABLE"]


def _normalize_golden_root(value: object, root: Path) -> object:
    if isinstance(value, dict):
        return {key: _normalize_golden_root(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_golden_root(item, root) for item in value]
    if isinstance(value, str):
        # macOS resolves /tmp through /private/tmp; normalize both spellings.
        return value.replace(str(root.resolve()), "{{ROOT}}").replace(str(root), "{{ROOT}}")
    return value


@pytest.fixture(scope="module")
def _pre_mission_replay(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Archive and execute the immutable pre-mission implementation tree."""
    repo_root = Path(__file__).resolve().parents[5]
    manifest = json.loads(_PRE_MISSION_GOLDEN.read_text(encoding="utf-8"))
    commit = str(manifest["source_commit"])
    expected_tree = str(manifest["source_tree"])
    actual_tree = subprocess.run(
        ["git", "rev-parse", f"{commit}^{{tree}}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert actual_tree == expected_tree
    archive = subprocess.run(
        ["git", "archive", "--format=tar", commit],
        cwd=repo_root,
        check=True,
        capture_output=True,
    ).stdout
    source_root = tmp_path_factory.mktemp("setup-plan-pinned-source")
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as bundle:
        bundle.extractall(source_root, filter="data")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(source_root / "src")
    replay = subprocess.run(
        [sys.executable, str(_PRE_MISSION_REPLAY), str(source_root)],
        cwd=source_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    document = json.loads(replay.stdout)
    assert document["loaded_module"] == (
        "src/specify_cli/cli/commands/agent/mission_setup_plan.py"
    )
    assert set(document["cases"]) == set(_LOCAL_OUTCOME_CASES)
    return cast(dict[str, object], document)


@pytest.mark.parametrize("case_name", tuple(_LOCAL_OUTCOME_CASES))
def test_real_setup_plan_matches_replayed_pre_mission_payload_and_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_name: str,
    _pre_mission_replay: dict[str, object],
) -> None:
    """Compare HEAD directly with a replay of the pinned source entry point."""
    expected = cast(dict[str, dict[str, object]], _pre_mission_replay["cases"])[case_name]
    with monkeypatch.context() as mp:
        payload, exit_code, _wire = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES[case_name],
            None,
        )

    normalized = _normalize_golden_root(payload, tmp_path)
    assert normalized == expected["payload"]
    assert exit_code == expected["exit_code"]


def test_real_setup_plan_freezes_local_outcome_before_hostile_hosted_assessment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The real entry point proves local result construction happens first."""
    order: list[str] = []
    original_builder = seam._build_setup_plan_result

    def _recording_builder(**kwargs: object) -> seam.SetupPlanLocalOutcome:
        outcome = original_builder(**kwargs)
        order.append("local-outcome")
        return outcome

    def _hostile_assessment(_root: Path) -> seam.HostedSyncDecision:
        order.append("hosted-assessment")
        raise RuntimeError("token=hostile-hosted-assessment")

    with monkeypatch.context() as mp:
        mp.setattr(seam, "_build_setup_plan_result", _recording_builder)
        mp.setattr(seam, "_collect_hosted_sync_decision", _hostile_assessment)
        payload, exit_code, wire = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES["substantive_complete"],
            "logged_out",
        )

    assert order == ["local-outcome", "hosted-assessment"]
    assert exit_code == 0
    assert payload["result"] == "success"
    assert payload["phase_complete"] is True
    assert "hostile-hosted-assessment" not in wire
    assert [warning["code"] for warning in cast(list[dict[str, object]], payload["warnings"])] == [
        "SAAS_SYNC_AUTH_UNKNOWN",
        "SAAS_SYNC_BOUNDARY_UNSAFE",
        "SAAS_SYNC_ROUTE_UNAVAILABLE",
    ]


@pytest.mark.parametrize(
    "case_name",
    ("missing_spec", "template_configuration", "generic_local_exception"),
)
def test_real_setup_plan_local_errors_survive_hostile_hosted_assessment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_name: str,
) -> None:
    """Post-context local errors retain payload/exit and leak no adapter data."""
    sink_calls: list[str] = []
    with monkeypatch.context() as mp:
        baseline, baseline_exit, _ = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES[case_name],
            None,
        )

    def _hostile_assessment(_root: Path) -> HostedSyncDecision:
        raise RuntimeError("token=local-error-secret ciphertext=/private/auth.session")

    with monkeypatch.context() as mp:
        mp.setattr(seam, "_collect_hosted_sync_decision", _hostile_assessment)
        actual, actual_exit, wire = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES[case_name],
            "logged_out",
            refused_sink_calls=sink_calls,
        )

    assert {key: value for key, value in actual.items() if key != "warnings"} == baseline
    assert actual_exit == baseline_exit == 1
    assert "local-error-secret" not in wire
    assert "/private/auth.session" not in wire
    assert sink_calls == []
    assert [warning["code"] for warning in cast(list[dict[str, object]], actual["warnings"])] == [
        "SAAS_SYNC_AUTH_UNKNOWN",
        "SAAS_SYNC_BOUNDARY_UNSAFE",
        "SAAS_SYNC_ROUTE_UNAVAILABLE",
    ]


def test_real_setup_plan_resolves_route_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The real entry point has one routing acquisition for one decision."""
    calls = 0
    original = seam.evaluate_route_availability

    def _counted(root: Path) -> tuple[bool, str | None]:
        nonlocal calls
        calls += 1
        return cast(tuple[bool, str | None], original(root))

    with monkeypatch.context() as mp:
        mp.setattr(seam, "evaluate_route_availability", _counted)
        payload, exit_code, _wire = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES["substantive_complete"],
            "route_null",
        )

    assert exit_code == 0
    assert calls == 1
    assert cast(list[dict[str, object]], payload["warnings"])[0]["code"] == (
        "SAAS_SYNC_ROUTE_UNAVAILABLE"
    )


def _hostile_diagnostic_serializer(mode: str) -> Callable[[HostedSyncDiagnostic], object]:
    def _serialize(_self: HostedSyncDiagnostic) -> object:
        if mode == "raise":
            raise RuntimeError("token=serializer-secret ciphertext=/private/session.enc")
        if mode == "malicious_dict":
            return {
                "code": "EVIL",
                "severity": "fatal",
                "hosted_disposition": "allowed",
                "message": "token=serializer-secret ciphertext=/private/session.enc",
                "remediation": ["exfiltrate secret"],
            }
        return object()

    return _serialize


@pytest.mark.parametrize("serializer_mode", ("raise", "malicious_dict", "non_json"))
def test_real_setup_plan_json_rebuilds_untrusted_diagnostic_serializer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    serializer_mode: str,
) -> None:
    """Raising, malicious, and non-JSON public serializers are never trusted."""
    with monkeypatch.context() as mp:
        baseline, baseline_exit, _ = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES["substantive_complete"],
            None,
        )

    with monkeypatch.context() as mp:
        mp.setattr(
            HostedSyncDiagnostic,
            "to_dict",
            _hostile_diagnostic_serializer(serializer_mode),
        )
        actual, actual_exit, wire = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES["substantive_complete"],
            "logged_out",
        )

    primary = {key: value for key, value in actual.items() if key != "warnings"}
    assert primary == baseline
    assert actual_exit == baseline_exit == 0
    assert "serializer-secret" not in wire
    assert "/private/session.enc" not in wire
    assert '"EVIL"' not in wire
    assert '"fatal"' not in wire
    assert '"allowed"' not in wire
    assert cast(list[dict[str, object]], actual["warnings"])[0]["code"] == (
        "SAAS_SYNC_UNAUTHENTICATED"
    )


@pytest.mark.parametrize("serializer_mode", ("raise", "malicious_dict", "non_json"))
def test_real_setup_plan_human_rebuilds_untrusted_diagnostic_serializer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    serializer_mode: str,
) -> None:
    """Human rendering also ignores every untrusted serializer return shape."""
    with monkeypatch.context() as mp:
        _, baseline_exit, _ = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES["substantive_complete"],
            None,
            human_output=True,
        )
    baseline_output = capsys.readouterr().out

    with monkeypatch.context() as mp:
        mp.setattr(
            HostedSyncDiagnostic,
            "to_dict",
            _hostile_diagnostic_serializer(serializer_mode),
        )
        _, actual_exit, _ = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES["substantive_complete"],
            "logged_out",
            human_output=True,
        )
    actual_output = capsys.readouterr().out

    assert actual_exit == baseline_exit == 0
    assert "serializer-secret" not in actual_output
    assert "/private/session.enc" not in actual_output
    assert "EVIL" not in actual_output
    assert "fatal" not in actual_output
    assert "allowed" not in actual_output
    assert "Plan scaffolded:" in baseline_output
    assert "Plan scaffolded:" in actual_output
    assert "no usable local session is available" in actual_output


def test_real_setup_plan_refusal_persists_local_events_and_touches_no_hosted_sink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """T015/T016: refusal blocks hosted fan-out but cannot suppress local
    persistence — including local dossier capture, which is never gated by
    the hosted-sync decision."""
    from specify_cli.status.lifecycle_events import mission_event_log_path

    sink_calls: list[str] = []
    with monkeypatch.context() as mp:
        payload, exit_code, _wire = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES["substantive_complete"],
            "logged_out",
            refused_sink_calls=sink_calls,
        )

    assert exit_code == 0
    assert payload["result"] == "success"
    assert sink_calls == ["dossier"]
    event_log = mission_event_log_path(tmp_path / "kitty-specs" / "001-matrix")
    assert event_log.is_file()
    assert len(event_log.read_text(encoding="utf-8").splitlines()) >= 3


def test_real_setup_plan_cli_emits_exactly_one_json_object_when_refused(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The real Typer parser emits one parseable object, without trailing JSON."""
    with monkeypatch.context() as mp:
        payload, exit_code, wire = _invoke_matrix_case(
            mp,
            tmp_path,
            _LOCAL_OUTCOME_CASES["substantive_complete"],
            "route_exception",
            invoke_through_parser=True,
        )

    assert exit_code == 0, wire
    assert payload["result"] == "success"
    warnings = cast(list[dict[str, object]], payload["warnings"])
    assert warnings[0]["code"] == "SAAS_SYNC_ROUTE_UNAVAILABLE"


@pytest.mark.parametrize("sync_enabled", ("0", "1"))
def test_real_setup_plan_project_root_failure_is_exact_and_skips_hosted_probes(
    monkeypatch: pytest.MonkeyPatch,
    sync_enabled: str,
) -> None:
    """The earliest local failure remains exact and never requires hosted state."""
    from specify_cli.cli.commands.agent import mission as mission_mod

    emitted: list[dict[str, object]] = []
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", sync_enabled)
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: None)
    monkeypatch.setattr(mission_mod, "_emit_json", lambda payload: emitted.append(payload))
    for probe in (
        "acquire_session_assessment",
        "evaluate_boundary",
        "evaluate_route_availability",
    ):
        monkeypatch.setattr(
            seam,
            probe,
            lambda *_a, _probe=probe, **_k: pytest.fail(
                f"project-root failure touched hosted probe: {_probe}"
            ),
        )

    with pytest.raises(typer.Exit) as exc_info:
        seam.setup_plan(feature="001-matrix", json_output=True)

    assert exc_info.value.exit_code == 1
    assert emitted == [{"error": seam.PROJECT_ROOT_NOT_FOUND_MESSAGE}]


# ---------------------------------------------------------------------------
# _resolve_setup_plan_feature_dir
# ---------------------------------------------------------------------------


def test_resolve_feature_dir_auto_selects_sole(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    monkeypatch.setattr(seam, "_sole_mission_slug_or_none", lambda _r: "001-demo")
    monkeypatch.setattr(mission_mod, "_find_feature_directory", lambda _r, _c, explicit_feature=None: tmp_path / explicit_feature)
    out = seam._resolve_setup_plan_feature_dir(tmp_path, None, json_output=True)
    assert out == tmp_path / "001-demo"


def test_resolve_feature_dir_emits_detection_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    def _boom(*_a: object, **_k: object) -> Path:
        raise ValueError("ambiguous")

    monkeypatch.setattr(seam, "_sole_mission_slug_or_none", lambda _r: None)
    monkeypatch.setattr(mission_mod, "_find_feature_directory", _boom)
    monkeypatch.setattr(seam, "_build_setup_plan_detection_error", lambda *a, **k: {"error": "ambiguous"})
    with pytest.raises(typer.Exit):
        seam._resolve_setup_plan_feature_dir(tmp_path, None, json_output=True)


# ---------------------------------------------------------------------------
# _enforce_spec_gate
# ---------------------------------------------------------------------------


def test_spec_gate_exits_when_spec_missing(tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"  # not created
    with pytest.raises(typer.Exit):
        seam._enforce_spec_gate(
            spec_file,
            feature_dir,
            "001-demo",
            tmp_path,
            target_branch="main",
            current_branch="main",
            json_output=True,
        )


def test_spec_gate_blocks_when_not_substantive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"
    spec_file.write_text("# stub")
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: True)
    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: False)
    blocked = seam._enforce_spec_gate(
        spec_file,
        feature_dir,
        "001-demo",
        tmp_path,
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert blocked is True


def test_spec_gate_passes_when_committed_and_substantive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"
    spec_file.write_text("# real")
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: True)
    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: True)
    blocked = seam._enforce_spec_gate(
        spec_file,
        feature_dir,
        "001-demo",
        tmp_path,
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert blocked is False


# ---------------------------------------------------------------------------
# _scaffold_plan_template
# ---------------------------------------------------------------------------


def test_scaffold_plan_template_noop_when_exists(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("populated")
    template_src = tmp_path / "mapped-plan.md"
    template_src.write_text("TEMPLATE")
    seam._scaffold_plan_template(plan_file, _resolution(template_src))
    assert plan_file.read_text() == "populated"


def test_scaffold_plan_template_copies_mapped_filename(tmp_path: Path) -> None:
    template_src = tmp_path / "non-conventional-plan-source.md"
    template_src.write_text("TEMPLATE")
    plan_file = tmp_path / "plan.md"
    seam._scaffold_plan_template(plan_file, _resolution(template_src))
    assert plan_file.read_text() == "TEMPLATE"


def test_resolve_plan_template_uses_context_and_configured_seam(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission_type":"software-dev"}', encoding="utf-8")
    context = _resolved_mission_type()
    template_src = tmp_path / "non-conventional-plan-source.md"
    template_src.write_text("MAPPED")
    calls: list[tuple[str, Path, ResolvedMissionType]] = []

    monkeypatch.setattr(
        seam,
        "resolve_mission_type_context",
        lambda repo_root, *, mission_type: context,
    )

    def _resolve(artifact_kind: str, project_dir: Path, resolved: ResolvedMissionType) -> ResolutionResult:
        calls.append((artifact_kind, project_dir, resolved))
        return _resolution(template_src)

    monkeypatch.setattr(mission_mod, "resolve_configured_template", _resolve)

    result = seam._resolve_plan_template(tmp_path, feature_dir)

    assert result.path == template_src
    assert calls == [("plan", tmp_path, context)]


def test_resolve_plan_template_rejects_legacy_only_mission_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Legacy-only metadata is typeless post-retirement, not typed configuration.

    rc3 M5 (FR-002, ADR 2026-08-22-1) retires the legacy ``mission`` field from
    every mission-type reader; only the canonical ``mission_type`` field is
    read. A meta.json carrying *only* the legacy ``mission`` key therefore
    resolves to a typeless mission and can no longer reach a configured plan
    template as a resolved legacy type -- it must fail closed with guidance to
    backfill ``mission_type`` (``spec-kitty migrate backfill-mission-type``),
    never silently fall back to a guessed template.
    """
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "001-legacy-meta"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission":"software-dev"}', encoding="utf-8")

    monkeypatch.setattr(
        seam,
        "resolve_mission_type_context",
        lambda *_a, **_k: pytest.fail("typeless legacy-only meta reached mission-type context resolution"),
    )
    monkeypatch.setattr(
        mission_mod,
        "resolve_template",
        lambda *_a, **_k: pytest.fail("typeless legacy-only meta reached the meta-less fallback"),
    )
    monkeypatch.setattr(
        mission_mod,
        "resolve_configured_template",
        lambda *_a, **_k: pytest.fail("typeless legacy-only meta reached the configured resolver"),
    )

    with pytest.raises(TemplateConfigurationError) as exc_info:
        seam._resolve_plan_template(tmp_path, feature_dir)

    assert "non-blank string field 'mission_type'" in str(exc_info.value)
    assert "backfill-mission-type" in str(exc_info.value)


def test_resolve_plan_template_preserves_missing_meta_legacy_boundary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "legacy-mission"
    feature_dir.mkdir(parents=True)
    template_src = tmp_path / "legacy-plan-template.md"
    template_src.write_text("LEGACY")
    legacy_calls: list[tuple[str, Path, str]] = []

    def _legacy_resolve(name: str, project_dir: Path, *, mission: str) -> ResolutionResult:
        legacy_calls.append((name, project_dir, mission))
        return _resolution(template_src)

    monkeypatch.setattr(mission_mod, "resolve_template", _legacy_resolve)
    monkeypatch.setattr(
        mission_mod,
        "resolve_configured_template",
        lambda *_a, **_k: pytest.fail("typeless context reached configured seam"),
    )

    result = seam._resolve_plan_template(tmp_path, feature_dir)

    assert result.path == template_src
    assert not (feature_dir / "meta.json").exists()
    assert not (feature_dir / "meta.json").is_symlink()
    assert legacy_calls == [("plan-template.md", tmp_path, "software-dev")]


@pytest.mark.parametrize(
    ("meta_case", "expected_error"),
    [
        ("malformed", "Malformed JSON"),
        ("unreadable", "Malformed JSON"),
        ("non_object", "Expected JSON object"),
        ("empty_object", "non-blank string field 'mission_type'"),
        ("missing_type", "non-blank string field 'mission_type'"),
        ("null_type", "non-blank string field 'mission_type'"),
        ("numeric_type", "non-blank string field 'mission_type'"),
        ("blank_type", "non-blank string field 'mission_type'"),
        ("whitespace_type", "non-blank string field 'mission_type'"),
        ("broken_symlink", "symlink without readable mission metadata"),
        ("self_loop_symlink", "symlink without readable mission metadata"),
    ],
)
def test_setup_plan_refuses_present_invalid_primary_meta_before_template_or_state_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    meta_case: str,
    expected_error: str,
) -> None:
    """Only absent metadata may enter the temporary #2660 compatibility arm."""
    from specify_cli.cli.commands.agent import mission as mission_mod

    mission_slug = "001-invalid-primary-meta"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("substantive spec", encoding="utf-8")
    meta_path = feature_dir / "meta.json"
    if meta_case == "malformed":
        meta_path.write_text("{", encoding="utf-8")
    elif meta_case == "unreadable":
        meta_path.mkdir()
    elif meta_case == "non_object":
        meta_path.write_text("[]", encoding="utf-8")
    elif meta_case == "broken_symlink":
        meta_path.symlink_to("missing-meta-target.json")
    elif meta_case == "self_loop_symlink":
        meta_path.symlink_to("meta.json")
    else:
        payloads = {
            "empty_object": "{}",
            "missing_type": '{"mission_slug":"001-invalid-primary-meta"}',
            "null_type": '{"mission_type":null}',
            "numeric_type": '{"mission_type":7}',
            "blank_type": '{"mission_type":""}',
            "whitespace_type": '{"mission_type":"  \\t  "}',
        }
        meta_path.write_text(payloads[meta_case], encoding="utf-8")

    template_src = tmp_path / "must-not-be-used.md"
    template_src.write_text("MUST NOT BE USED", encoding="utf-8")
    resolver_calls: list[str] = []
    state_changes: list[str] = []
    emitted: dict[str, object] = {}

    def _unexpected_resolver(name: str, *_args: object, **_kwargs: object) -> ResolutionResult:
        resolver_calls.append(name)
        return _resolution(template_src)

    def _unexpected_plan_commit(*_args: object, **_kwargs: object) -> tuple[None, None, bool]:
        state_changes.append("plan-commit")
        return None, None, True

    monkeypatch.setattr(seam, "_resolve_setup_plan_feature_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(seam, "_evaluate_spec_gate", lambda *a, **k: (None, None))
    monkeypatch.setattr(
        seam,
        "_emit_spec_plan_phase_events",
        lambda *a, **k: state_changes.append("phase-events"),
    )
    monkeypatch.setattr(
        seam,
        "_commit_plan_if_substantive",
        _unexpected_plan_commit,
    )
    monkeypatch.setattr(seam, "_run_documentation_wiring", lambda *a, **k: (None, []))
    monkeypatch.setattr(hosted_effects, "_trigger_dossier_sync", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_emit_setup_plan_result", lambda **_k: None)
    monkeypatch.setattr(seam, "_emit_json", lambda payload: emitted.update(payload))
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", lambda *a, **k: None)
    monkeypatch.setattr(mission_mod, "_show_branch_context", lambda *a, **k: ("main", "main"))
    monkeypatch.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(mission_mod, "_planning_read_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(mission_mod, "resolve_template", _unexpected_resolver)
    monkeypatch.setattr(mission_mod, "resolve_configured_template", _unexpected_resolver)

    with pytest.raises(typer.Exit) as exc_info:
        seam.setup_plan(feature=mission_slug, json_output=True)

    assert exc_info.value.exit_code == 1
    assert expected_error in str(emitted["error"])
    assert str(meta_path) in str(emitted["error"])
    assert resolver_calls == []
    assert state_changes == []
    assert not (feature_dir / "plan.md").exists()


@pytest.mark.parametrize("mutation", ["unlink", "replace"])
def test_setup_plan_uses_single_loaded_meta_snapshot_when_file_changes_after_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation: str,
) -> None:
    """A post-load filesystem race cannot switch a typed mission to legacy."""
    from specify_cli.cli.commands.agent import mission as mission_mod

    mission_slug = "001-meta-snapshot"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("substantive spec", encoding="utf-8")
    meta_path = feature_dir / "meta.json"
    meta_path.write_text('{"mission_type":"software-dev"}', encoding="utf-8")
    # WP04 (C-A1): the provisioned charter is the sole mission-type activation
    # authority, so ``resolve_mission_type_context`` fails closed without this.
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True, exist_ok=True)
    (kittify_dir / "config.yaml").write_text(
        "mission_type_activations:\n  - software-dev\n", encoding="utf-8"
    )
    template_src = tmp_path / "configured-plan.md"
    template_src.write_text("CONFIGURED PLAN", encoding="utf-8")
    load_calls = 0
    configured_calls: list[str | None] = []
    legacy_calls: list[str] = []

    def _load_then_mutate(feature_dir_arg: Path) -> dict[str, Any] | None:
        # FR-007: the seam now reads through ``load_meta_fail_closed`` (one
        # positional arg), so the stub mirrors THAT signature. The test's
        # intent is unchanged: count the reads and mutate the file immediately
        # after, proving the caller uses its single loaded snapshot.
        nonlocal load_calls
        load_calls += 1
        loaded = canonical_load_meta_fail_closed(feature_dir_arg)
        if mutation == "unlink":
            meta_path.unlink()
        else:
            meta_path.write_text('{"mission_type":null}', encoding="utf-8")
        return cast(dict[str, Any] | None, loaded)

    def _configured_resolver(
        _artifact_kind: str,
        _project_dir: Path,
        resolved: ResolvedMissionType,
    ) -> ResolutionResult:
        configured_calls.append(resolved.mission_type)
        return _resolution(template_src)

    def _legacy_resolver(name: str, *_args: object, **_kwargs: object) -> ResolutionResult:
        legacy_calls.append(name)
        return _resolution(template_src)

    monkeypatch.setattr(seam, "load_meta_fail_closed", _load_then_mutate)
    monkeypatch.setattr(seam, "_resolve_setup_plan_feature_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(seam, "_evaluate_spec_gate", lambda *a, **k: (None, None))
    monkeypatch.setattr(seam, "_emit_spec_plan_phase_events", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_commit_plan_if_substantive", lambda *a, **k: (None, None, True))
    monkeypatch.setattr(seam, "_run_documentation_wiring", lambda *a, **k: (None, []))
    monkeypatch.setattr(hosted_effects, "_trigger_dossier_sync", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_emit_setup_plan_result", lambda **_k: None)
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", lambda *a, **k: None)
    monkeypatch.setattr(mission_mod, "_show_branch_context", lambda *a, **k: ("main", "main"))
    monkeypatch.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(mission_mod, "_planning_read_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(mission_mod, "resolve_configured_template", _configured_resolver)
    monkeypatch.setattr(mission_mod, "resolve_template", _legacy_resolver)

    seam.setup_plan(feature=mission_slug, json_output=True)

    assert load_calls == 1
    assert configured_calls == ["software-dev"]
    assert legacy_calls == []
    assert (feature_dir / "plan.md").read_text(encoding="utf-8") == "CONFIGURED PLAN"


def test_setup_plan_resolves_template_context_from_primary_planning_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Coord lifecycle state must not make a typed mission look typeless.

    The coordination directory intentionally has no ``meta.json``.  The primary
    planning directory carries the canonical typed metadata.  Running the real
    ``setup_plan`` body must therefore route through the configured resolver;
    passing the coord directory to ``_resolve_plan_template`` instead makes this
    test enter the guarded legacy resolver and fail.
    """
    from specify_cli.cli.commands.agent import mission as mission_mod

    mission_slug = "001-typed-mission"
    primary_dir = tmp_path / "kitty-specs" / mission_slug
    coord_dir = tmp_path / ".worktrees" / f"{mission_slug}-coord" / "kitty-specs" / mission_slug
    primary_dir.mkdir(parents=True)
    coord_dir.mkdir(parents=True)
    (primary_dir / "meta.json").write_text('{"mission_type":"software-dev"}', encoding="utf-8")
    (primary_dir / "spec.md").write_text("substantive spec", encoding="utf-8")
    # WP04 (C-A1): the provisioned charter is the sole mission-type activation
    # authority, so ``resolve_mission_type_context`` fails closed without this.
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True, exist_ok=True)
    (kittify_dir / "config.yaml").write_text(
        "mission_type_activations:\n  - software-dev\n", encoding="utf-8"
    )
    template_src = tmp_path / "configured-plan.md"
    template_src.write_text("CONFIGURED PLAN", encoding="utf-8")
    configured_calls: list[tuple[str, Path, ResolvedMissionType]] = []

    def _resolve_configured(
        artifact_kind: str,
        project_dir: Path,
        resolved: ResolvedMissionType,
    ) -> ResolutionResult:
        configured_calls.append((artifact_kind, project_dir, resolved))
        return _resolution(template_src)

    monkeypatch.setattr(seam, "_resolve_setup_plan_feature_dir", lambda *a, **k: coord_dir)
    monkeypatch.setattr(seam, "_evaluate_spec_gate", lambda *a, **k: (None, None))
    monkeypatch.setattr(seam, "_emit_spec_plan_phase_events", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_commit_plan_if_substantive", lambda *a, **k: (None, None, True))
    monkeypatch.setattr(seam, "_run_documentation_wiring", lambda *a, **k: (None, []))
    monkeypatch.setattr(hosted_effects, "_trigger_dossier_sync", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_emit_setup_plan_result", lambda **_k: None)
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", lambda *a, **k: None)
    monkeypatch.setattr(mission_mod, "_show_branch_context", lambda *a, **k: ("main", "main"))
    monkeypatch.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(mission_mod, "_planning_read_dir", lambda *a, **k: primary_dir)
    monkeypatch.setattr(mission_mod, "resolve_configured_template", _resolve_configured)
    monkeypatch.setattr(
        mission_mod,
        "resolve_template",
        lambda *a, **k: pytest.fail("typed primary context reached the typeless compatibility resolver"),
    )

    seam.setup_plan(feature=mission_slug, json_output=True)

    assert (primary_dir / "plan.md").read_text(encoding="utf-8") == "CONFIGURED PLAN"
    assert len(configured_calls) == 1
    artifact_kind, project_dir, resolved = configured_calls[0]
    assert artifact_kind == "plan"
    assert project_dir == tmp_path
    assert resolved.mission_type == "software-dev"
    assert coord_dir != primary_dir
    assert not (coord_dir / "meta.json").exists()


@pytest.mark.parametrize(
    ("context", "expected_fragment"),
    [
        (_resolved_mission_type(template_set={}), "missing the requested mapping key"),
        (
            _resolved_mission_type(mission_type="research", template_set=None),
            "has no configured template mapping",
        ),
        (_resolved_mission_type(template_set={"plan": "absent-plan.md"}), "absent-plan.md"),
    ],
)
def test_resolve_plan_template_fails_closed_for_bad_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    context: ResolvedMissionType,
    expected_fragment: str,
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(f'{{"mission_type":"{context.mission_type}"}}', encoding="utf-8")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "empty-home"))
    monkeypatch.setattr(
        seam,
        "resolve_mission_type_context",
        lambda repo_root, *, mission_type: context,
    )

    with pytest.raises(TemplateConfigurationError) as exc_info:
        seam._resolve_plan_template(tmp_path, feature_dir)

    message = str(exc_info.value)
    assert context.mission_type in message
    assert "artifact kind 'plan'" in message
    assert expected_fragment in message


def test_scaffold_and_pristine_compare_share_one_resolution_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission_type":"software-dev"}', encoding="utf-8")
    template_src = tmp_path / "override-winner.md"
    template_src.write_text("OVERRIDE WINNER")
    context = _resolved_mission_type()
    call_count = 0

    monkeypatch.setattr(
        seam,
        "resolve_mission_type_context",
        lambda repo_root, *, mission_type: context,
    )

    def _resolve(*_args: object, **_kwargs: object) -> ResolutionResult:
        nonlocal call_count
        call_count += 1
        return _resolution(template_src)

    monkeypatch.setattr(mission_mod, "resolve_configured_template", _resolve)

    resolution = seam._resolve_plan_template(tmp_path, feature_dir)
    plan_file = feature_dir / "plan.md"
    seam._scaffold_plan_template(plan_file, resolution)

    assert seam._is_plan_pristine(plan_file, resolution) is True
    assert call_count == 1


# ---------------------------------------------------------------------------
# is_pristine_scaffold / _resolve_plan_result_state (T021/T022 direct units,
# #2566 / FR-009)
# ---------------------------------------------------------------------------


def test_is_pristine_scaffold_true_when_byte_equal() -> None:
    from specify_cli.missions._substantive import is_pristine_scaffold

    template = "## Technical Context\n**Language/Version**: [NEEDS CLARIFICATION]\n"
    assert is_pristine_scaffold(template, template) is True


def test_is_pristine_scaffold_false_when_populated_but_insufficient() -> None:
    from specify_cli.missions._substantive import is_pristine_scaffold

    template = "## Technical Context\n**Language/Version**: [NEEDS CLARIFICATION]\n"
    edited = template + "\nAgent started filling this in but not the required fields yet.\n"
    assert is_pristine_scaffold(edited, template) is False


@pytest.mark.parametrize(
    ("is_substantive_flag", "is_pristine", "committed", "expected"),
    [
        # substantive always wins -> success, no flag (regardless of pristine/committed)
        (True, False, False, ("success", False)),
        (True, True, True, ("success", False)),
        # pristine, never committed -> the first happy-path scaffold write
        (False, True, False, ("success", True)),
        # pristine but already committed (edge case) -> falls back to blocked,
        # not a repeated scaffold_only claim
        (False, True, True, ("blocked", False)),
        # populated-but-insufficient (K-1 / NFR-005): edited but not substantive
        (False, False, False, ("blocked", False)),
        (False, False, True, ("blocked", False)),
    ],
)
def test_resolve_plan_result_state(is_substantive_flag: bool, is_pristine: bool, committed: bool, expected: tuple[str, bool]) -> None:
    assert seam._resolve_plan_result_state(is_substantive=is_substantive_flag, is_pristine=is_pristine, committed=committed) == expected


# ---------------------------------------------------------------------------
# _commit_plan_if_substantive (T022: pristine -> scaffold_only, populated
# -but-insufficient -> blocked, substantive -> committed with no flag)
# ---------------------------------------------------------------------------


def test_commit_plan_scaffold_only_when_pristine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    template_src = tmp_path / "tmpl.md"
    template_src.write_text("## Technical Context\n**Language/Version**: [NEEDS CLARIFICATION]\n")
    resolution = _resolution(template_src)

    plan_file = tmp_path / "plan.md"
    plan_file.write_text(template_src.read_text())  # byte-identical, never touched

    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: False)
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: False)

    commit_result, blocked_reason, scaffold_only = seam._commit_plan_if_substantive(
        plan_file,
        tmp_path,
        "001-demo",
        tmp_path,
        target_branch="main",
        json_output=True,
        plan_template=resolution,
    )
    assert commit_result is None
    assert blocked_reason is None
    assert scaffold_only is True


def test_commit_plan_blocked_when_populated_but_insufficient(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    template_src = tmp_path / "tmpl.md"
    template_src.write_text("## Technical Context\n**Language/Version**: [NEEDS CLARIFICATION]\n")
    resolution = _resolution(template_src)

    plan_file = tmp_path / "plan.md"
    plan_file.write_text(template_src.read_text() + "\nStarted editing but Technical Context still isn't real.\n")

    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: False)
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: False)

    commit_result, blocked_reason, scaffold_only = seam._commit_plan_if_substantive(
        plan_file,
        tmp_path,
        "001-demo",
        tmp_path,
        target_branch="main",
        json_output=True,
        plan_template=resolution,
    )
    assert commit_result is None
    assert blocked_reason is not None
    assert scaffold_only is False


def test_commit_plan_substantive_commits_with_no_scaffold_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("## Technical Context\n**Language/Version**: Python 3.12\n**Primary Dependencies**: typer\n")

    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: True)
    monkeypatch.setattr(
        mission_mod,
        "_commit_to_branch",
        lambda *a, **k: seam.CommitToBranchResult(status="committed", placement_ref="main", commit_hash="abc1234"),
    )

    commit_result, blocked_reason, scaffold_only = seam._commit_plan_if_substantive(
        plan_file,
        tmp_path,
        "001-demo",
        tmp_path,
        target_branch="main",
        json_output=True,
        plan_template=_resolution(tmp_path / "unused.md"),
    )
    assert commit_result is not None
    assert commit_result.status == "committed"
    assert blocked_reason is None
    assert scaffold_only is False


# ---------------------------------------------------------------------------
# _run_documentation_wiring (non-doc mission no-op)
# ---------------------------------------------------------------------------


def test_documentation_wiring_noop_for_non_doc_mission(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # read-side-seam-primary-primitive-closure-01KYKMMT WP04: the ``feature_dir``
    # positional argument was dropped -- the function now resolves its own
    # PRIMARY-partition dir through the seam (FR-013, #2886).
    monkeypatch.setattr(seam, "get_mission_type", lambda _fd: "software-dev")
    gap, gens = seam._run_documentation_wiring("001-demo", tmp_path, target_branch="main", json_output=True)
    assert gap is None
    assert gens == []


def test_documentation_wiring_runs_both_documentation_phases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "get_mission_type", lambda _fd: "documentation")
    monkeypatch.setattr(
        seam,
        "_run_documentation_gap_analysis",
        lambda *a, **k: "gap-analysis.md",
    )
    generator = object()
    monkeypatch.setattr(
        seam,
        "_detect_and_configure_generators",
        lambda *a, **k: [generator],
    )

    gap, generators = seam._run_documentation_wiring(
        "001-docs",
        tmp_path,
        target_branch="main",
        json_output=True,
    )

    assert gap == "gap-analysis.md"
    assert generators == [generator]


def test_documentation_wiring_on_coord_husk_writes_gap_analysis_to_primary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T024 (WP04 review, WP08 T039 nice-to-have): a documentation mission whose
    coordination worktree is a HUSK (materialised, no ``meta.json``) still
    anchors ``gap-analysis.md`` on the PRIMARY dir, never the husk.

    read-side-seam-primary-primitive-closure-01KYKMMT WP04 closed the #2886
    one-of-two documentation-wiring hole (both reads route through
    ``placement_seam(...).read_dir(PRIMARY_METADATA)``), but its reviewer
    flagged there was no committed BEHAVIOURAL test: both phase tests above
    monkeypatch the read (``get_mission_type``) so a regression that routed
    only ONE of the two reads back onto the coord husk would still pass them.
    This test drives the REAL seam (no ``placement_seam``/``get_mission_type``
    mock) against a real coord-husk fixture and asserts on the observable
    contract: which directory ``_run_documentation_gap_analysis`` is handed as
    its write target.
    """
    mission_slug = "001-docs-on-husk"
    primary_dir = tmp_path / "kitty-specs" / mission_slug
    coord_dir = tmp_path / ".worktrees" / f"{mission_slug}-coord" / "kitty-specs" / mission_slug
    primary_dir.mkdir(parents=True)
    coord_dir.mkdir(parents=True)  # materialised coord root, but NO meta.json: a husk
    (primary_dir / "meta.json").write_text(
        '{"mission_type": "documentation", "coordination_branch": "kitty/mission-001-docs-on-husk"}',
        encoding="utf-8",
    )
    assert not (coord_dir / "meta.json").exists(), "husk invariant: no coord meta.json"

    captured: dict[str, object] = {}

    def _capture_gap_analysis(
        primary_dir_arg: Path, *args: object, **kwargs: object
    ) -> str:
        captured["primary_dir_arg"] = primary_dir_arg
        return "gap-analysis.md"

    monkeypatch.setattr(seam, "_run_documentation_gap_analysis", _capture_gap_analysis)
    monkeypatch.setattr(seam, "_detect_and_configure_generators", lambda *a, **k: [])

    gap, _generators = seam._run_documentation_wiring(
        mission_slug, tmp_path, target_branch="main", json_output=True
    )

    assert gap == "gap-analysis.md"
    assert captured["primary_dir_arg"] == primary_dir, (
        "gap-analysis.md's write target must be the PRIMARY dir, never the "
        f"coord husk {coord_dir} — got {captured['primary_dir_arg']}"
    )
    assert captured["primary_dir_arg"] != coord_dir


@pytest.mark.parametrize("json_output", [True, False])
def test_setup_plan_renders_configured_template_failure_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    json_output: bool,
) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("spec")
    emitted: dict[str, object] = {}
    error = TemplateConfigurationError(
        mission_type="software-dev",
        artifact_kind="plan",
        mapped_filename="missing-plan.md",
        reason="maps to unresolved filename 'missing-plan.md'",
    )

    monkeypatch.setattr(seam, "_resolve_setup_plan_feature_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(seam, "_evaluate_spec_gate", lambda *a, **k: (None, None))
    monkeypatch.setattr(seam, "_resolve_plan_template", lambda *_a: (_ for _ in ()).throw(error))
    monkeypatch.setattr(seam, "_emit_json", lambda payload: emitted.update(payload))
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", lambda *a, **k: None)
    monkeypatch.setattr(mission_mod, "_show_branch_context", lambda *a, **k: ("main", "main"))
    monkeypatch.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(mission_mod, "_planning_read_dir", lambda *a, **k: feature_dir)

    with pytest.raises(typer.Exit) as exc_info:
        seam.setup_plan(feature="001-demo", json_output=json_output)

    assert exc_info.value.exit_code == 1
    if json_output:
        assert emitted["error_code"] == "TEMPLATE_CONFIGURATION_ERROR"
        assert emitted["mapped_filename"] == "missing-plan.md"
    else:
        output = capsys.readouterr().out
        assert "missing-plan.md" in output
        assert "Traceback" not in output


# ---------------------------------------------------------------------------
# _emit_setup_plan_result
# ---------------------------------------------------------------------------


def test_emit_result_human(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=True,
        plan_blocked_reason=None,
        plan_commit_result=None,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=False,
    )
    assert "Plan scaffolded" in capsys.readouterr().out


def test_emit_result_json_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: dict[str, object] = {}
    monkeypatch.setattr(seam, "_emit_json", lambda p: emitted.update(p))
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=False,
        plan_blocked_reason="not substantive",
        plan_commit_result=None,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert emitted["result"] == "blocked"
    assert emitted["blocked_reason"] == "not substantive"
    assert "branch_context" in emitted


def test_emit_result_json_committed_surfaces_hash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: dict[str, object] = {}
    monkeypatch.setattr(seam, "_emit_json", lambda p: emitted.update(p))
    commit = seam.CommitToBranchResult(status="committed", placement_ref="main", commit_hash="abc1234")
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=True,
        plan_blocked_reason=None,
        plan_commit_result=commit,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert emitted["commit_created"] is True
    assert emitted["commit_hash"] == "abc1234"
    assert emitted["commit_status"] == "committed"


def test_emit_result_json_scaffold_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """FR-009 / #2566: the first happy-path scaffold write is success, not blocked."""
    emitted: dict[str, object] = {}
    monkeypatch.setattr(seam, "_emit_json", lambda p: emitted.update(p))
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=False,
        plan_blocked_reason=None,
        plan_commit_result=None,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=True,
        plan_scaffold_only=True,
    )
    assert emitted["result"] == "success"
    assert emitted["scaffold_only"] is True
    assert emitted["phase_complete"] is False
    assert "blocked_reason" not in emitted
