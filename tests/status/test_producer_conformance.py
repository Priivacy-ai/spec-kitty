"""Producer conformance tests for canonical event emission.

Phase 2 of issues Priivacy-ai/spec-kitty#1198 / #1200.

For every SaaS-bound producer surface in the CLI (the lifecycle module's
``emit_*`` helpers and the ``EventEmitter`` class's ``emit_*`` methods),
this test enumerates a minimal valid argument set, captures the resulting
payload, and asserts that the canonical
``spec_kitty_events.conformance.validate_event(..., strict=True)`` passes
with zero ``model_violations`` and zero ``schema_violations``.

The intent: bind every producer's payload shape to the canonical contract
so future drift is an emit-time error caught here in CI, not an RC-canary
failure days later. See start-here.md C-007 and
spec-kitty-mission-workflow.md non-negotiables.
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
    assert not result.model_violations, (
        f"{event_type}: model_violations={[(v.field, v.message) for v in result.model_violations]}"
    )
    assert not result.schema_violations, (
        f"{event_type}: schema_violations={[(v.json_path, v.message) for v in result.schema_violations]}"
    )


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
def test_emit_artifact_phase_started_payload_passes_strict_validation(
    tmp_path: Path, event_type: str
) -> None:
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


# ---------------------------------------------------------------------------
# EventEmitter producers (specify_cli.sync.emitter.EventEmitter)
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_emitter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a fresh EventEmitter against an isolated HOME / queue.

    Uses ``tmp_path`` for HOME and a stubbed OfflineQueue so producer
    conformance never touches the operator's real outbox.
    """
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))

    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.queue import OfflineQueue

    queue = OfflineQueue(db_path=tmp_path / "outbox.sqlite")
    emitter = EventEmitter(queue=queue)
    return emitter


def _payload_of_last_emitted(emitter, event_type: str, **fields: Any) -> dict[str, Any]:
    """Invoke an emitter method by event_type and return its payload."""
    method = {
        "WPStatusChanged": emitter.emit_wp_status_changed,
        "WPCreated": emitter.emit_wp_created,
        "WPAssigned": emitter.emit_wp_assigned,
        "MissionCreated": emitter.emit_mission_created,
        "MissionClosed": emitter.emit_mission_closed,
        "MissionOriginBound": emitter.emit_mission_origin_bound,
        "HistoryAdded": emitter.emit_history_added,
        "ErrorLogged": emitter.emit_error_logged,
        "DependencyResolved": emitter.emit_dependency_resolved,
        "BuildRegistered": emitter.emit_build_registered,
        "BuildHeartbeat": emitter.emit_build_heartbeat,
    }[event_type]
    envelope = method(**fields)
    assert envelope is not None, f"{event_type}: producer returned None"
    return envelope["payload"]


def test_emit_wp_status_changed_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "WPStatusChanged",
        wp_id="WP01",
        from_lane="planned",
        to_lane="claimed",
        actor="cli",
        mission_slug="demo-mission",
        execution_mode="worktree",
    )
    _strict_validate("WPStatusChanged", payload)


def test_emit_wp_status_changed_done_with_evidence_passes_strict_validation(
    isolated_emitter,
) -> None:
    """Done transitions require ``evidence`` per the Phase-1 semantic
    validator. Producer must accept evidence and route through the
    canonical model unchanged."""
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "WPStatusChanged",
        wp_id="WP01",
        from_lane="for_review",
        to_lane="done",
        actor="reviewer",
        mission_slug="demo-mission",
        evidence={
            "review": {
                "reviewer": "reviewer-renata",
                "verdict": "approved",
                "reference": "review:abc",
            },
            "repos": [
                {"repo": "demo/repo", "branch": "main", "commit": "a" * 40}
            ],
        },
    )
    _strict_validate("WPStatusChanged", payload)


def test_emit_wp_created_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "WPCreated",
        wp_id="WP01",
        title="Scaffold project",
        mission_slug="demo-mission",
        dependencies=[],
        actor="cli",
    )
    _strict_validate("WPCreated", payload)


def test_emit_wp_assigned_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "WPAssigned",
        wp_id="WP01",
        agent_id="claude-opus",
        phase="implementation",
        retry_count=0,
    )
    _strict_validate("WPAssigned", payload)


def test_emit_mission_created_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "MissionCreated",
        mission_slug="001-demo",
        mission_number=1,
        target_branch="main",
        wp_count=3,
        mission_type="software-dev",
        mission_id="01ULIDEXAMPLE0000000000001",
        friendly_name="Demo",
        purpose_tldr="demo",
        purpose_context="demo",
        created_at="2026-05-22T00:00:00+00:00",
    )
    _strict_validate("MissionCreated", payload)


def test_emit_mission_closed_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "MissionClosed",
        mission_slug="001-demo",
        total_wps=3,
        mission_id="01ULIDEXAMPLE0000000000002",
        mission_number=1,
        mission_type="software-dev",
    )
    _strict_validate("MissionClosed", payload)


def test_emit_mission_origin_bound_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "MissionOriginBound",
        mission_slug="001-demo",
        provider="linear",
        external_issue_id="123",
        external_issue_key="ORG/repo#123",
        external_issue_url="https://example.test/issues/123",
        title="Demo issue",
        mission_id="01ULIDEXAMPLE0000000000003",
    )
    _strict_validate("MissionOriginBound", payload)


def test_emit_history_added_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "HistoryAdded",
        wp_id="WP01",
        entry_type="note",
        entry_content="Started work",
        author="cli",
    )
    _strict_validate("HistoryAdded", payload)


def test_emit_error_logged_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "ErrorLogged",
        error_type="runtime",
        error_message="something broke",
        wp_id="WP01",
        agent_id="claude-opus",
    )
    _strict_validate("ErrorLogged", payload)


def test_emit_dependency_resolved_payload_passes_strict_validation(isolated_emitter) -> None:
    payload = _payload_of_last_emitted(
        isolated_emitter,
        "DependencyResolved",
        wp_id="WP02",
        dependency_wp_id="WP01",
        resolution_type="merged",
    )
    _strict_validate("DependencyResolved", payload)


# BuildRegistered / BuildHeartbeat: the wire payload retains the legacy
# identity-fat shape (build_id/node_id/project_uuid/…) for SaaS
# materializer compatibility until Phase 3 lands the legacy adapter. The
# canonical Phase-1 payload covers only repo_slug/git_branch/head_commit_sha
# (plus heartbeat extras). We assert producer-time validation runs by
# verifying the producer returns a non-None envelope when the canonical
# fields are populated; full strict conformance on the wire payload will
# arrive with Phase 3.
def test_emit_build_registered_invokes_canonical_validation(isolated_emitter) -> None:
    envelope = isolated_emitter.emit_build_registered()
    assert envelope is not None
    assert envelope["event_type"] == "BuildRegistered"


def test_emit_build_heartbeat_invokes_canonical_validation(isolated_emitter) -> None:
    envelope = isolated_emitter.emit_build_heartbeat(
        remote_head="b" * 40,
        ahead_of_remote=1,
        behind_remote=0,
        recent_commits=["c" * 40],
    )
    assert envelope is not None
    assert envelope["event_type"] == "BuildHeartbeat"
