"""Tests for the local-first canonical lifecycle event writer.

Covers issue #1067 (project + mission lifecycle events), #1068
(WPCreated immediate persistence), and the diagnostic
``has_non_bootstrap_status_history`` helper consumed by the merge
gate added for #1069.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.lifecycle_events import (
    LIFECYCLE_EVENT_TYPES,
    MISSION_CREATED,
    PROJECT_INITIALIZED,
    SPECIFY_COMPLETED,
    TASKS_COMPLETED,
    WP_CREATED,
    append_lifecycle_event,
    emit_artifact_phase,
    emit_mission_created_local,
    emit_project_initialized,
    emit_wp_created_local,
    has_lifecycle_event,
    has_non_bootstrap_status_history,
    mission_event_log_path,
    project_event_log_path,
    read_lifecycle_events,
)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / ".kittify").mkdir()
    return tmp_path


@pytest.fixture()
def feature_dir(tmp_path: Path) -> Path:
    fd = tmp_path / "kitty-specs" / "demo-mission"
    fd.mkdir(parents=True)
    return fd


# ---------------------------------------------------------------------------
# ProjectInitialized
# ---------------------------------------------------------------------------


def test_project_initialized_persists_and_dedupes(repo: Path) -> None:
    env1 = emit_project_initialized(
        repo,
        project_uuid="proj-123",
        project_slug="demo",
        actor="test",
    )
    env2 = emit_project_initialized(
        repo,
        project_uuid="proj-123",
        project_slug="demo",
        actor="test",
    )

    log = project_event_log_path(repo)
    assert log.exists(), "project event log was not created"
    assert env1 is not None and env1["event_type"] == PROJECT_INITIALIZED
    assert env2 is None, "duplicate ProjectInitialized for the same UUID must be skipped"

    entries = read_lifecycle_events(log)
    assert len(entries) == 1
    payload = entries[0]["payload"]
    assert payload["project_uuid"] == "proj-123"
    assert payload["project_slug"] == "demo"
    assert payload["actor"] == "test"


def test_project_initialized_writes_canonical_jsonl(repo: Path) -> None:
    emit_project_initialized(repo, project_uuid="abc", project_slug="x", actor="t")
    log = project_event_log_path(repo)
    raw = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(raw) == 1
    payload = json.loads(raw[0])
    assert payload["event_type"] == PROJECT_INITIALIZED
    assert payload["aggregate_type"] == "Project"


# ---------------------------------------------------------------------------
# MissionCreated
# ---------------------------------------------------------------------------


def test_mission_created_local_appended_before_any_saas_fan_out(
    feature_dir: Path,
) -> None:
    envelope = emit_mission_created_local(
        feature_dir,
        mission_slug="demo-mission",
        mission_id="01ULID",
        mission_number=None,
        target_branch="main",
        actor="test",
    )

    assert envelope is not None
    log = mission_event_log_path(feature_dir)
    entries = read_lifecycle_events(log)
    assert len(entries) == 1
    assert entries[0]["event_type"] == MISSION_CREATED
    assert entries[0]["aggregate_id"] == "01ULID"


def test_mission_created_dedupe_on_mission_slug(feature_dir: Path) -> None:
    emit_mission_created_local(
        feature_dir,
        mission_slug="demo-mission",
        mission_id=None,
        mission_number=None,
        target_branch="main",
    )
    second = emit_mission_created_local(
        feature_dir,
        mission_slug="demo-mission",
        mission_id=None,
        mission_number=None,
        target_branch="main",
    )
    assert second is None
    entries = read_lifecycle_events(mission_event_log_path(feature_dir))
    assert len(entries) == 1


# ---------------------------------------------------------------------------
# Artifact phases (Specify / Plan / Tasks)
# ---------------------------------------------------------------------------


def test_artifact_phase_completed_dedupes_on_artifact_path(feature_dir: Path) -> None:
    e1 = emit_artifact_phase(
        feature_dir,
        event_type=SPECIFY_COMPLETED,
        mission_slug="demo-mission",
        actor="test",
        artifact_path="kitty-specs/demo-mission/spec.md",
    )
    e2 = emit_artifact_phase(
        feature_dir,
        event_type=SPECIFY_COMPLETED,
        mission_slug="demo-mission",
        actor="test",
        artifact_path="kitty-specs/demo-mission/spec.md",
    )
    assert e1 is not None
    assert e2 is None


def test_artifact_phase_rejects_unknown_event_type(feature_dir: Path) -> None:
    with pytest.raises(ValueError):
        emit_artifact_phase(
            feature_dir,
            event_type="NotARealPhase",
            mission_slug="demo-mission",
        )


# ---------------------------------------------------------------------------
# WPCreated
# ---------------------------------------------------------------------------


def test_wp_created_persists_immediately_and_dedupes(feature_dir: Path) -> None:
    env1 = emit_wp_created_local(
        feature_dir,
        mission_slug="demo-mission",
        wp_id="WP01",
        wp_title="Set up scaffolding",
        depends_on=[],
    )
    env2 = emit_wp_created_local(
        feature_dir,
        mission_slug="demo-mission",
        wp_id="WP01",
        wp_title="Set up scaffolding",
        depends_on=[],
    )
    assert env1 is not None
    assert env2 is None  # idempotent on (mission_slug, wp_id)

    entries = read_lifecycle_events(mission_event_log_path(feature_dir))
    assert [e["event_type"] for e in entries] == [WP_CREATED]
    assert entries[0]["aggregate_id"] == "WP01"


def test_wp_created_full_roster_writes_one_event_per_wp(feature_dir: Path) -> None:
    for wp_id, title in [("WP01", "Alpha"), ("WP02", "Beta"), ("WP03", "Gamma")]:
        emit_wp_created_local(
            feature_dir,
            mission_slug="demo-mission",
            wp_id=wp_id,
            wp_title=title,
        )
    entries = [
        e
        for e in read_lifecycle_events(mission_event_log_path(feature_dir))
        if e["event_type"] == WP_CREATED
    ]
    assert sorted(e["aggregate_id"] for e in entries) == ["WP01", "WP02", "WP03"]


# ---------------------------------------------------------------------------
# Merge guard: has_non_bootstrap_status_history
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in entries) + "\n",
        encoding="utf-8",
    )


def test_has_non_bootstrap_status_history_false_when_only_bootstrap(
    feature_dir: Path,
) -> None:
    log = mission_event_log_path(feature_dir)
    _write_jsonl(
        log,
        [
            {
                "event_id": "01H1",
                "wp_id": "WP01",
                "from_lane": None,
                "to_lane": "planned",
                "force": True,
                "actor": "finalize-tasks",
                "at": "2026-01-01T00:00:00Z",
                "mission_slug": "demo-mission",
            },
            {
                "event_id": "01H2",
                "wp_id": "WP02",
                "from_lane": "planned",
                "to_lane": "planned",
                "force": True,
                "actor": "finalize-tasks",
                "at": "2026-01-01T00:00:01Z",
                "mission_slug": "demo-mission",
            },
        ],
    )
    assert has_non_bootstrap_status_history(feature_dir) is False


def test_has_non_bootstrap_status_history_true_for_real_transition(
    feature_dir: Path,
) -> None:
    log = mission_event_log_path(feature_dir)
    _write_jsonl(
        log,
        [
            {
                "event_id": "01H1",
                "wp_id": "WP01",
                "from_lane": None,
                "to_lane": "planned",
                "force": True,
                "actor": "finalize-tasks",
            },
            {
                "event_id": "01H2",
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "force": False,
                "actor": "claude",
            },
        ],
    )
    assert has_non_bootstrap_status_history(feature_dir) is True


def test_has_non_bootstrap_status_history_true_when_lifecycle_event_present(
    feature_dir: Path,
) -> None:
    emit_mission_created_local(
        feature_dir,
        mission_slug="demo-mission",
        mission_id=None,
        mission_number=None,
        target_branch="main",
    )
    assert has_non_bootstrap_status_history(feature_dir) is True


def test_has_non_bootstrap_status_history_false_when_log_absent(
    tmp_path: Path,
) -> None:
    assert has_non_bootstrap_status_history(tmp_path / "absent") is False


# ---------------------------------------------------------------------------
# Sanity checks on the public surface
# ---------------------------------------------------------------------------


def test_lifecycle_event_types_complete() -> None:
    assert {
        PROJECT_INITIALIZED,
        MISSION_CREATED,
        SPECIFY_COMPLETED,
        TASKS_COMPLETED,
        WP_CREATED,
    } <= LIFECYCLE_EVENT_TYPES


def test_has_lifecycle_event_matches_dedup_keys(feature_dir: Path) -> None:
    log = mission_event_log_path(feature_dir)
    append_lifecycle_event(
        log,
        WP_CREATED,
        {
            "mission_slug": "demo-mission",
            "wp_id": "WP07",
            "wp_title": "demo",
            "depends_on": [],
            "actor": "test",
        },
        aggregate_id="WP07",
        aggregate_type="WorkPackage",
        dedup_keys={"mission_slug": "demo-mission", "wp_id": "WP07"},
    )
    assert has_lifecycle_event(
        log, event_type=WP_CREATED, dedup_keys={"mission_slug": "demo-mission", "wp_id": "WP07"}
    )
    assert not has_lifecycle_event(
        log, event_type=WP_CREATED, dedup_keys={"mission_slug": "demo-mission", "wp_id": "WP99"}
    )
