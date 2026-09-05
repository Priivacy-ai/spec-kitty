"""Producer conformance tests for canonical event emission.

Phase 2 of issues Priivacy-ai/spec-kitty#1198 / #1200.

For every SaaS-bound producer surface in the CLI (the lifecycle module's
``emit_*`` helpers), this test enumerates a minimal valid argument set,
captures the resulting payload, and asserts that the canonical
``spec_kitty_events.conformance.validate_event(..., strict=True)`` passes
with zero ``model_violations`` and zero ``schema_violations``.

(The former second section pinned the sync ``EventEmitter``'s ``emit_*``
methods; that producer died with the sync transport, issue #5. When epic E3
wires a real emitter at ``runtime.next.event_emitter`` its payloads belong
back in this file.)

The intent: bind every producer's payload shape to the canonical contract
so future drift is an emit-time error caught here in CI, not an RC-canary
failure days later. See start-here.md C-007 and
docs/architecture/spec-kitty-mission-workflow.md non-negotiables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Lifecycle-module producers (specify_cli.status.lifecycle_events)
# ---------------------------------------------------------------------------


def _strict_validate(event_type: str, payload: dict[str, Any]) -> None:
    """Strict canonical validation; fails the test on any violation."""
    from spec_kitty_events.conformance import validate_event

    result = validate_event(payload, event_type, strict=True)
    assert not result.model_violations, f"{event_type}: model_violations={[(v.field, v.message) for v in result.model_violations]}"
    assert not result.schema_violations, f"{event_type}: schema_violations={[(v.json_path, v.message) for v in result.schema_violations]}"


def _strict_validate_saas_projection(event_type: str, payload: dict[str, Any]) -> None:
    from specify_cli.status.lifecycle_events import _canonical_lifecycle_payload_for_saas

    _strict_validate(event_type, _canonical_lifecycle_payload_for_saas(event_type, payload))


def test_emit_project_initialized_payload_passes_strict_validation(tmp_path: Path) -> None:
    from specify_cli.status.lifecycle_events import emit_project_initialized

    envelope = emit_project_initialized(
        tmp_path,
        project_uuid="00000000-0000-0000-0000-000000000001",
        project_slug="demo",
        actor="cli",
        runtime_version="3.2.0rc23",
    )
    assert envelope is not None
    _strict_validate("ProjectInitialized", envelope["payload"])


def test_emit_mission_created_local_payload_passes_strict_validation(tmp_path: Path) -> None:
    from specify_cli.status.lifecycle_events import emit_mission_created_local

    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)

    envelope = emit_mission_created_local(
        feature_dir,
        mission_slug="demo-mission",
        mission_id="01ULIDEXAMPLE0000000000000",
        mission_number=None,
        mission_type="software-dev",
        target_branch="main",
        wp_count=3,
        friendly_name="Demo Mission",
        purpose_tldr="A demo mission",
        purpose_context="Used for conformance test.",
    )
    assert envelope is not None
    _strict_validate("MissionCreated", envelope["payload"])


@pytest.mark.parametrize(
    "event_type",
    ["SpecifyStarted", "PlanStarted", "TasksStarted"],
)
def test_emit_artifact_phase_started_payload_passes_strict_validation(tmp_path: Path, event_type: str) -> None:
    from specify_cli.status.lifecycle_events import emit_artifact_phase

    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)

    envelope = emit_artifact_phase(
        feature_dir,
        event_type=event_type,
        mission_slug="demo-mission",
        mission_number=1,
        actor="cli",
    )
    assert envelope is not None
    _strict_validate_saas_projection(event_type, envelope["payload"])


def test_emit_artifact_phase_specify_completed_payload_passes_strict_validation(
    tmp_path: Path,
) -> None:
    from specify_cli.status.lifecycle_events import emit_artifact_phase

    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)

    envelope = emit_artifact_phase(
        feature_dir,
        event_type="SpecifyCompleted",
        mission_slug="demo-mission",
        actor="cli",
        artifact_path="kitty-specs/demo-mission/spec.md",
        summary="initial spec",
    )
    assert envelope is not None
    _strict_validate("SpecifyCompleted", envelope["payload"])


def test_emit_artifact_phase_plan_completed_payload_passes_strict_validation(
    tmp_path: Path,
) -> None:
    from specify_cli.status.lifecycle_events import emit_artifact_phase

    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)

    envelope = emit_artifact_phase(
        feature_dir,
        event_type="PlanCompleted",
        mission_slug="demo-mission",
        actor="cli",
        artifact_path="kitty-specs/demo-mission/plan.md",
    )
    assert envelope is not None
    _strict_validate("PlanCompleted", envelope["payload"])


def test_emit_artifact_phase_tasks_completed_payload_passes_strict_validation(
    tmp_path: Path,
) -> None:
    from specify_cli.status.lifecycle_events import emit_artifact_phase

    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)

    envelope = emit_artifact_phase(
        feature_dir,
        event_type="TasksCompleted",
        mission_slug="demo-mission",
        actor="cli",
        artifact_path="kitty-specs/demo-mission/tasks.md",
        wp_count=3,
        summary="3 WPs",
    )
    assert envelope is not None
    _strict_validate("TasksCompleted", envelope["payload"])


def test_emit_artifact_phase_started_keeps_local_artifact_path_but_saas_projection_is_strict(
    tmp_path: Path,
) -> None:
    """Started events keep local artifact metadata without leaking it to SaaS."""
    from specify_cli.status.lifecycle_events import emit_artifact_phase

    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)

    envelope = emit_artifact_phase(
        feature_dir,
        event_type="SpecifyStarted",
        mission_slug="demo-mission",
        actor="cli",
        artifact_path="kitty-specs/demo-mission/spec.md",
    )
    assert envelope is not None
    assert envelope["payload"]["artifact_path"] == "kitty-specs/demo-mission/spec.md"
    _strict_validate_saas_projection("SpecifyStarted", envelope["payload"])


def test_emit_wp_created_local_payload_passes_strict_validation(tmp_path: Path) -> None:
    from specify_cli.status.lifecycle_events import emit_wp_created_local

    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)

    envelope = emit_wp_created_local(
        feature_dir,
        mission_slug="demo-mission",
        wp_id="WP01",
        wp_title="Scaffold project",
        wp_path="kitty-specs/demo-mission/tasks/WP01.md",
        depends_on=[],
        actor="cli",
    )
    assert envelope is not None
    _strict_validate("WPCreated", envelope["payload"])
