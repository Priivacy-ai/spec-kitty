"""WP06 (#2116) — ``move_task`` thin-orchestrator side-effect parity (T029).

The WP06 rewire routes ``move_task``'s execution through the WP02 coord WRITE
capabilities: each lane hop is emitted via ``commit_status`` and the primary
WP-file commit runs via ``commit_artifact``. This module injects the WP02 **Fake**
ports (``ports=`` on the extracted ``_do_move_task`` orchestrator — the C-005
injection seam that never touches the Typer surface) and asserts the executed
side-effects match the pre-rewire behaviour:

* a ``--no-auto-commit`` move records the transition on the ``commit_status`` seam
  ONLY — the primary ``commit_artifact`` seam stays untouched (coord-vs-primary
  disjointness);
* an auto-commit move records the transition on ``commit_status`` AND routes the
  ``WORK_PACKAGE_TASK`` primary commit (with the WP file in the bundle) through
  ``commit_artifact``, and writes the WP file to disk;
* the coord skip-exit-0 arm (``skip_primary``) suppresses the ``commit_artifact``
  call entirely and reports ``wp_file_update="skipped"`` while the transition is
  still emitted on the coord ``commit_status`` seam.

These are the Fake-port projections of the golden coord-topology cases (T004/T007);
they pin the routing without a real git worktree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind

from specify_cli.cli.commands.agent.tasks import _do_move_task, seam_coord_router
from specify_cli.agent_tasks_ports import (
    CommitStatusResult,
    MissionHandle,
    TasksPorts,
)
from specify_cli.missions._read_path_resolver import (
    resolve_feature_dir_for_mission,
    resolve_planning_read_dir,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.mocked_env import setup_mocked_env
from tests.specify_cli.cli.commands.agent.test_tasks_ports import (
    FakeCoordCommitRouter,
    FakeFsReader,
    FakeGitOps,
    FakeRender,
)

pytestmark = pytest.mark.fast

_MISSION = "test-move-task-orchestration"


def _build_wp_file(tmp_path: Path, mission_slug: str, wp_id: str) -> tuple[Path, Path]:
    """Minimal WP + feature structure (mirrors the shared test_tasks helper)."""
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    wp_file = tasks_dir / f"{wp_id}-test.md"
    wp_file.write_text(
        f"---\n"
        f"work_package_id: {wp_id}\n"
        f"title: Test {wp_id}\n"
        f"execution_mode: code_change\n"
        f"agent: testbot\n"
        f"owned_files:\n  - src/{wp_id.lower()}/**\n"
        f"authoritative_surface: src/{wp_id.lower()}/\n"
        f"---\n\n# {wp_id}\n\n## Activity Log\n",
        encoding="utf-8",
    )
    return feature_dir, wp_file


def _seed_wp_event(feature_dir: Path, wp_id: str, to_lane: str) -> None:
    """Seed a WP event so the canonical event log knows the WP exists."""
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"test-{wp_id}-{to_lane}",
            mission_slug=feature_dir.name,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane(to_lane),
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )


def _fake_ports(feature_dir: Path) -> tuple[TasksPorts, FakeCoordCommitRouter]:
    """A WP02 Fake bundle whose coord router resolves the REAL coord husk dir.

    ``feature_write_dir`` must return the on-disk feature dir the orchestrator's
    reads (``_read_transactional_wp_lane`` / pre30 guard) depend on; the two write
    capabilities record calls on their separate logs. ``commit_status`` returns a
    ``skipped=False`` result (event=None) so the emit loop threads through without
    a real event write — the CALL is the observable, not a persisted event.
    """
    coord = FakeCoordCommitRouter(
        write_dir=feature_dir,
        status_result=CommitStatusResult(event=None, skipped=False),
    )
    ports = TasksPorts(
        fs=FakeFsReader(), coord=coord, git=FakeGitOps(), render=FakeRender()
    )
    return ports, coord


def _run_move(
    tmp_path: Path,
    *,
    to: str,
    ports: TasksPorts,
    target_branch: str = "wip-lane",
    auto_commit: bool,
    json_output: bool = True,
    extra_patches: dict[str, object] | None = None,
) -> None:
    with setup_mocked_env(
        tmp_path,
        mission_slug=_MISSION,
        target_branch=target_branch,
        extra_patches={
            "_validate_ready_for_review": (True, []),
            "_check_unchecked_subtasks": [],
            **(extra_patches or {}),
        },
    ):
        _do_move_task(
            task_id="WP01",
            to=to,
            mission=_MISSION,
            agent=None,
            assignee=None,
            shell_pid=None,
            note=None,
            review_feedback_file=None,
            approval_ref=None,
            reviewer=None,
            self_review_fallback=False,
            intended_reviewer=None,
            reviewer_failure_reason=None,
            done_override_reason=None,
            force=False,
            tracker_ref=None,
            skip_review_artifact_check=False,
            auto_commit=auto_commit,
            json_output=json_output,
            ports=ports,
        )


def test_no_auto_commit_move_uses_commit_status_only(tmp_path: Path) -> None:
    """A ``--no-auto-commit`` for_review move emits the hop via ``commit_status``
    and NEVER touches the primary ``commit_artifact`` seam (C-001 disjointness)."""
    feature_dir, _wp = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    ports, coord = _fake_ports(feature_dir)

    _run_move(tmp_path, to="for_review", ports=ports, auto_commit=False)

    # Exactly one lane hop, emitted through the coord status capability.
    assert len(coord.status_calls) == 1
    assert coord.status_calls[0][0] == _MISSION
    # The primary WRITE capability is UNTOUCHED (no auto-commit => no primary commit).
    assert coord.artifact_calls == []


def test_auto_commit_move_routes_primary_write_via_commit_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An auto-commit move emits the hop via ``commit_status`` AND routes the
    ``WORK_PACKAGE_TASK`` primary commit (WP file in the bundle) via
    ``commit_artifact``, writing the WP file to disk."""
    feature_dir, wp_file = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    ports, coord = _fake_ports(feature_dir)

    _run_move(tmp_path, to="for_review", ports=ports, auto_commit=True)

    # Lane hop still on the status seam.
    assert len(coord.status_calls) == 1
    # Primary WP-file commit routed through the artifact seam, keyed WORK_PACKAGE_TASK.
    assert len(coord.artifact_calls) == 1
    slug, paths, message, kind = coord.artifact_calls[0]
    assert slug == _MISSION
    assert kind == MissionArtifactKind.WORK_PACKAGE_TASK
    assert wp_file.resolve() in paths
    assert message.startswith(f"chore: Move WP01 to for_review on spec {_MISSION.split('-')[0]}")
    # The WP file's activity log was updated on disk before the commit.
    assert "Moved to for_review" in wp_file.read_text(encoding="utf-8")

    payload = json.loads(capsys.readouterr().out)
    assert payload["result"] == "success"
    assert payload["new_lane"] == "for_review"
    assert "wp_file_update" not in payload  # non-skip arm: no skip envelope keys


def test_fr010_move_task_coord_status_dir_stays_on_coord_husk(tmp_path: Path) -> None:
    """FR-010 (T027): the coord WRITE port ``move_task`` uses to resolve its shared
    status/event-log dir (``feature_write_dir``) MUST land on the kind-blind coord
    husk (``resolve_feature_dir_for_mission``), NEVER a primary-partition kind.

    ``_mt_resolve_targets`` sets ``mt_feature_dir = ports.coord.feature_write_dir(...)``
    and feeds it to the pre30 guard, the authoritative event-log lane read, and the
    coord override persist. Repointing it to a PRIMARY kind (WORK_PACKAGE_TASK) would
    move the event-log read off the coord husk and reintroduce the split-brain FR-010
    closes. This pins the production router's leg to the coord-husk resolver.
    """
    _build_wp_file(tmp_path, _MISSION, "WP01")
    handle = MissionHandle(repo_root=tmp_path, mission_slug=_MISSION)
    coord_husk = resolve_feature_dir_for_mission(tmp_path, _MISSION)
    # The production move_task router resolves the coord husk for the shared status dir.
    # (constructor-DI collapse: the move_task coord router is now built via
    # ``seam_coord_router(route_emit=True)`` rather than the deleted
    # ``_MoveTaskCoordRouter`` subclass.)
    assert seam_coord_router(route_emit=True).feature_write_dir(handle) == coord_husk
    # A PRIMARY-partition kind would resolve a DIFFERENT dir under coord topology —
    # the status read must never be collapsed onto it (guard against a wholesale
    # repoint). On this flat fixture the STATUS partition stays path-equal to the husk.
    assert (
        resolve_planning_read_dir(
            tmp_path, _MISSION, kind=MissionArtifactKind.STATUS_STATE
        )
        == coord_husk
    )


def test_coord_skip_arm_suppresses_commit_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The coord skip-exit-0 arm (``skip_primary``) emits the hop on ``commit_status``
    but suppresses the primary ``commit_artifact`` call and reports the skip envelope
    — the fall-through control shape, NOT an early exit."""
    feature_dir, wp_file = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    ports, coord = _fake_ports(feature_dir)
    pre_commit_body = wp_file.read_text(encoding="utf-8")

    _run_move(
        tmp_path,
        to="for_review",
        ports=ports,
        auto_commit=True,
        # Force the coord skip decision (protected-primary + coord topology proxy).
        extra_patches={"_skip_target_branch_commit": True},
    )

    # The transition is still emitted on the coord status seam ...
    assert len(coord.status_calls) == 1
    # ... but the primary commit is suppressed (skip arm) and the WP file is not
    # rewritten on the primary partition.
    assert coord.artifact_calls == []
    assert wp_file.read_text(encoding="utf-8") == pre_commit_body

    payload = json.loads(capsys.readouterr().out)
    assert payload["result"] == "success"
    assert payload["wp_file_update"] == "skipped"
    assert "coordination branch" in payload["wp_file_update_reason"]
