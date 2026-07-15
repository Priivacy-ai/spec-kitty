"""Acceptance coverage for observable ``move-task --to for_review`` gates."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    CommitStatusResult,
    MissionHandle,
    TasksPorts,
)
from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks import app
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.review import pre_review_gate
from specify_cli.status import Lane, StatusEvent, TransitionRequest
from specify_cli.status.reducer import materialize
from specify_cli.status.store import append_event
from specify_cli.workspace.context import ResolvedWorkspace
from tests.mocked_env import setup_mocked_env
from tests.specify_cli.cli.commands.agent.test_tasks_ports import (
    FakeFsReader,
    FakeGitOps,
    FakeRender,
)

pytestmark = [pytest.mark.git_repo]

_MISSION = "test-pre-review-observability"


@dataclass
class _RecordingCoordRouter:
    write_dir: Path
    status_calls: list[TransitionRequest] = field(default_factory=list)

    def feature_write_dir(self, mission: MissionHandle) -> Path:
        return self.write_dir

    def commit_status(
        self,
        request: TransitionRequest,
        *,
        capability: GuardCapability,
    ) -> CommitStatusResult:
        self.status_calls.append(request)
        return CommitStatusResult(event=None, skipped=False)

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: object,
        message: str,
        *,
        kind: object,
        policy: object,
    ) -> CommitArtifactResult:
        raise AssertionError("auto-commit is disabled in this acceptance test")


def _build_command_fixture(tmp_path: Path) -> tuple[TasksPorts, _RecordingCoordRouter]:
    feature_dir = tmp_path / "kitty-specs" / _MISSION
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tmp_path / ".kittify").mkdir()
    (tasks_dir / "WP01-test.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Observable gate\n"
        "execution_mode: code_change\n"
        "agent: testbot\n"
        "owned_files:\n  - src/example.py\n"
        "authoritative_surface: src/\n"
        "pre_review_test_scope: tests/example\n"
        "---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    append_event(
        feature_dir,
        StatusEvent(
            event_id="test-WP01-in-progress",
            mission_slug=_MISSION,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.IN_PROGRESS,
            at="2026-07-14T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )
    router = _RecordingCoordRouter(write_dir=feature_dir)
    return (
        TasksPorts(
            fs=FakeFsReader(),
            coord=router,
            git=FakeGitOps(),
            render=FakeRender(),
        ),
        router,
    )


def _init_committed_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "mission-target"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture base"], cwd=path, check=True)


def _git_snapshot(path: Path) -> tuple[str, int, tuple[str, ...]]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit_count = int(
        subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    dirty = tuple(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    )
    return head, commit_count, dirty


def _build_residue_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, TasksPorts, _RecordingCoordRouter, ResolvedWorkspace]:
    primary = tmp_path / "primary"
    coordination = tmp_path / "coordination"
    lane = tmp_path / "lane"
    for checkout in (primary, coordination, lane):
        checkout.mkdir()

    primary_feature = primary / "kitty-specs" / _MISSION
    primary_tasks = primary_feature / "tasks"
    primary_tasks.mkdir(parents=True)
    (primary / ".kittify").mkdir()
    wp_path = primary_tasks / "WP01-test.md"
    wp_path.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Residue matrix\n"
        "execution_mode: code_change\n"
        "agent: testbot\n"
        "owned_files:\n  - src/example.py\n"
        "authoritative_surface: src/\n"
        "pre_review_test_scope: tests/example\n"
        "---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    meta = {
        "mission_id": "01KXG2TDVPTZSYY58E578T5RX3",
        "mission_slug": _MISSION,
        "slug": _MISSION,
        "mission_type": "software-dev",
        "target_branch": "mission-target",
        "topology": "single_branch",
        "vcs": "git",
    }
    (primary_feature / "meta.json").write_text(
        json.dumps(meta),
        encoding="utf-8",
    )
    append_event(
        primary_feature,
        StatusEvent(
            event_id="primary-WP01-in-progress",
            mission_slug=_MISSION,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.IN_PROGRESS,
            at="2026-07-14T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )
    materialize(primary_feature)

    coord_feature = coordination / "kitty-specs" / _MISSION
    coord_feature.mkdir(parents=True)
    (coord_feature / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    append_event(
        coord_feature,
        StatusEvent(
            event_id="residue-WP01-in-progress",
            mission_slug=_MISSION,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.IN_PROGRESS,
            at="2026-07-14T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )
    materialize(coord_feature)

    (lane / "src").mkdir()
    (lane / "src" / "example.py").write_text("VALUE = 1\n", encoding="utf-8")
    for checkout in (primary, coordination, lane):
        _init_committed_repo(checkout)

    router = _RecordingCoordRouter(write_dir=coord_feature)
    ports = TasksPorts(
        fs=FakeFsReader(),
        coord=router,
        git=FakeGitOps(),
        render=FakeRender(),
    )
    workspace = ResolvedWorkspace(
        mission_slug=_MISSION,
        wp_id="WP01",
        execution_mode="code_change",
        mode_source="frontmatter",
        resolution_kind="lane_workspace",
        workspace_name="lane-a",
        worktree_path=lane,
        branch_name="mission-target",
        lane_id="lane-a",
        lane_wp_ids=["WP01"],
        context=None,
    )
    return primary, coordination, lane, wp_path, ports, router, workspace


def test_move_task_human_mode_emits_continuing_gate_liveness(tmp_path: Path) -> None:
    """The exact Typer entry point emits more than its one-shot start notice."""
    ports, router = _build_command_fixture(tmp_path)
    fake_clock = iter((0.0, 30.0, 60.0))

    def controlled_gate(
        scope: pre_review_gate.ScopeResult,
        *,
        repo_root: Path,
        baseline: Any,
        timeout: int = 300,
        progress_callback: Any = None,
        monotonic: Any = None,
        wait: Any = None,
    ) -> pre_review_gate.GateVerdict:
        del repo_root, baseline, timeout, wait
        if progress_callback is not None:
            clock = monotonic or (lambda: next(fake_clock))
            progress_callback(clock())
            progress_callback(clock())
        return pre_review_gate.GateVerdict(
            outcome=pre_review_gate.GateOutcome.UNVERIFIED_BASELINE,
            scope=scope,
            reason="controlled acceptance run",
        )

    with (
        setup_mocked_env(
            tmp_path,
            mission_slug=_MISSION,
            extra_patches={
                "_validate_ready_for_review": (True, []),
                "_check_unchecked_subtasks": [],
            },
        ),
        patch.object(tasks_move_task, "_default_move_task_ports", return_value=ports),
        patch.object(pre_review_gate, "evaluate_with_scope", side_effect=controlled_gate),
    ):
        result = CliRunner().invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--mission",
                _MISSION,
                "--no-auto-commit",
            ],
        )

    assert result.exit_code == 0, result.output
    assert len(router.status_calls) == 1
    assert "running scoped tests at head" in result.output
    assert result.output.count("still running") >= 2


@pytest.mark.parametrize(
    ("outcome", "state"),
    [
        (pre_review_gate.GateOutcome.TIMED_OUT, pre_review_gate.HeadRunState.TIMED_OUT),
        (pre_review_gate.GateOutcome.CANCELLED, pre_review_gate.HeadRunState.CANCELLED),
    ],
)
def test_json_interruption_is_singular_and_precedes_every_mutation(
    tmp_path: Path,
    outcome: pre_review_gate.GateOutcome,
    state: pre_review_gate.HeadRunState,
) -> None:
    ports, router = _build_command_fixture(tmp_path)
    feature_dir = tmp_path / "kitty-specs" / _MISSION
    wp_path = feature_dir / "tasks" / "WP01-test.md"
    wp_before = wp_path.read_text(encoding="utf-8")
    events_before = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")
    terminal = pre_review_gate.GateVerdict(
        outcome=outcome,
        scope=pre_review_gate.ScopeResult.from_override(("tests/example",)),
        reason=f"controlled {outcome.value}",
        run_state=state,
    )

    with (
        setup_mocked_env(
            tmp_path,
            mission_slug=_MISSION,
            target_branch="lane-a",
            extra_patches={
                "_check_unchecked_subtasks": [],
            },
        ),
        patch.object(tasks_move_task, "_default_move_task_ports", return_value=ports),
        patch.object(pre_review_gate, "evaluate_with_scope", return_value=terminal),
        patch.object(
            tasks_move_task,
            "_mt_commit_lane_deliverables",
            side_effect=AssertionError("deliverable commit must stay behind the gate"),
        ),
    ):
        result = CliRunner().invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--mission",
                _MISSION,
                "--auto-commit",
                "--json",
            ],
        )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["transition_applied"] is False
    assert payload["pre_review_gate"]["outcome"] == outcome.value
    assert payload["pre_review_gate"]["run_state"] == state.value
    assert router.status_calls == []
    assert wp_path.read_text(encoding="utf-8") == wp_before
    assert (feature_dir / "status.events.jsonl").read_text(encoding="utf-8") == events_before


@pytest.mark.parametrize(
    ("state", "outcome"),
    [
        (pre_review_gate.HeadRunState.TIMED_OUT, pre_review_gate.GateOutcome.TIMED_OUT),
        (pre_review_gate.HeadRunState.CANCELLED, pre_review_gate.GateOutcome.CANCELLED),
    ],
)
def test_exact_entry_interruption_has_zero_owned_residue_across_checkouts(
    tmp_path: Path,
    state: pre_review_gate.HeadRunState,
    outcome: pre_review_gate.GateOutcome,
) -> None:
    (
        primary,
        coordination,
        lane,
        wp_path,
        ports,
        router,
        workspace,
    ) = _build_residue_fixture(tmp_path)
    coord_feature = coordination / "kitty-specs" / _MISSION
    event_path = coord_feature / "status.events.jsonl"
    status_path = coord_feature / "status.json"
    sentinel = lane / "test-owned-sentinel.txt"

    before = {
        "event": event_path.read_bytes(),
        "status": status_path.read_bytes(),
        "primary_event": (primary / "kitty-specs" / _MISSION / "status.events.jsonl").read_bytes(),
        "primary_status": (primary / "kitty-specs" / _MISSION / "status.json").read_bytes(),
        "lane": json.loads(status_path.read_text(encoding="utf-8"))["work_packages"]["WP01"]["lane"],
        "wp": wp_path.read_bytes(),
        "primary_git": _git_snapshot(primary),
        "coord_git": _git_snapshot(coordination),
        "lane_git": _git_snapshot(lane),
    }

    def _terminal_runner(*args: object, **kwargs: object) -> pre_review_gate.HeadRunResult:
        del args, kwargs
        sentinel.write_text("test-owned", encoding="utf-8")
        return pre_review_gate.HeadRunResult(
            ran=False,
            error=f"controlled {state.value}",
            state=state,
        )

    with (
        setup_mocked_env(
            primary,
            mission_slug=_MISSION,
            target_branch="mission-target",
            workspace_resolution=workspace,
            extra_patches={
                "_check_unchecked_subtasks": [],
                "_detect_arbiter_override": False,
            },
        ),
        patch.object(tasks_move_task, "_default_move_task_ports", return_value=ports),
        patch.object(pre_review_gate, "run_scoped_tests_at_head", side_effect=_terminal_runner),
    ):
        result = CliRunner().invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--mission",
                _MISSION,
                "--auto-commit",
                "--json",
            ],
        )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert "pre_review_gate" in payload, payload
    assert payload["pre_review_gate"]["outcome"] == outcome.value
    assert payload["pre_review_gate"]["new_checkout_paths"] == [sentinel.name]
    assert payload["transition_applied"] is False
    assert router.status_calls == []
    assert event_path.read_bytes() == before["event"]
    assert status_path.read_bytes() == before["status"]
    assert (primary / "kitty-specs" / _MISSION / "status.events.jsonl").read_bytes() == before["primary_event"]
    assert (primary / "kitty-specs" / _MISSION / "status.json").read_bytes() == before["primary_status"]
    assert json.loads(status_path.read_text(encoding="utf-8"))["work_packages"]["WP01"]["lane"] == before["lane"]
    assert wp_path.read_bytes() == before["wp"]
    assert _git_snapshot(primary) == before["primary_git"]
    assert _git_snapshot(coordination) == before["coord_git"]
    lane_after = _git_snapshot(lane)
    lane_before = before["lane_git"]
    assert lane_after[:2] == lane_before[:2]
    assert set(lane_after[2]) - {f"?? {sentinel.name}"} == set(lane_before[2])
    assert sentinel.read_text(encoding="utf-8") == "test-owned"


def test_keyboard_interrupt_at_gate_seam_is_a_local_cancellation(tmp_path: Path) -> None:
    ports, router = _build_command_fixture(tmp_path)

    with (
        setup_mocked_env(
            tmp_path,
            mission_slug=_MISSION,
            extra_patches={
                "_validate_ready_for_review": (True, []),
                "_check_unchecked_subtasks": [],
            },
        ),
        patch.object(tasks_move_task, "_default_move_task_ports", return_value=ports),
        patch.object(pre_review_gate, "evaluate_with_scope", side_effect=KeyboardInterrupt),
    ):
        result = CliRunner().invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--mission",
                _MISSION,
                "--no-auto-commit",
                "--json",
            ],
        )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["pre_review_gate"]["outcome"] == "cancelled"
    assert payload["transition_applied"] is False
    assert router.status_calls == []


def test_dirty_deliverables_extend_prospective_scope(
    tmp_path: Path,
) -> None:
    status = subprocess.CompletedProcess(
        args=["git", "status", "--porcelain"],
        returncode=0,
        stdout=" M src/unstaged.py\nM  src/staged.py\n?? tests/new_test.py\n",
        stderr="",
    )
    with (
        patch.object(tasks_move_task, "merge_base_changed_files", return_value=("src/committed.py",)),
        patch("specify_cli.cli.commands.agent.tasks.subprocess.run", return_value=status),
        patch(
            "specify_cli.cli.commands.agent.tasks._filter_runtime_state_paths",
            side_effect=lambda value: value,
        ),
    ):
        changed = tasks_move_task._mt_pre_review_changed_files(tmp_path, "target")

    assert changed == (
        "src/committed.py",
        "src/staged.py",
        "src/unstaged.py",
        "tests/new_test.py",
    )


def test_successful_auto_commit_occurs_only_after_gate(
    tmp_path: Path,
) -> None:
    ports, router = _build_command_fixture(tmp_path)
    order: list[str] = []

    def _validate(*args: object, **kwargs: object) -> tuple[bool, list[str]]:
        order.append("validate")
        return True, []

    with (
        setup_mocked_env(
            tmp_path,
            mission_slug=_MISSION,
            target_branch="lane-a",
            extra_patches={"_check_unchecked_subtasks": []},
        ),
        patch.object(tasks_move_task, "_default_move_task_ports", return_value=ports),
        patch.object(tasks_move_task, "_mt_run_pre_review_gate", side_effect=lambda st: order.append("gate")),
        patch.object(
            tasks_move_task,
            "_mt_commit_lane_deliverables",
            side_effect=lambda st: order.append("commit"),
        ),
        patch("specify_cli.cli.commands.agent.tasks._validate_ready_for_review", side_effect=_validate),
    ):
        result = CliRunner().invoke(
            app,
            [
                "move-task",
                "WP01",
                "--to",
                "for_review",
                "--mission",
                _MISSION,
                "--auto-commit",
            ],
        )

    assert result.exit_code == 0, result.output
    assert order[:3] == ["gate", "commit", "validate"]
    assert len(router.status_calls) == 1


@pytest.mark.parametrize("json_mode", [False, True])
def test_gate_created_path_is_preserved_and_surfaced(
    tmp_path: Path,
    json_mode: bool,
) -> None:
    ports, router = _build_command_fixture(tmp_path)
    sentinel = tmp_path / "test-owned-sentinel.txt"

    def _controlled_timeout(
        *args: object,
        **kwargs: object,
    ) -> pre_review_gate.GateVerdict:
        sentinel.write_text("preserve me", encoding="utf-8")
        return pre_review_gate.GateVerdict(
            outcome=pre_review_gate.GateOutcome.TIMED_OUT,
            scope=pre_review_gate.ScopeResult.from_override(("tests/example",)),
            reason="controlled timeout",
            run_state=pre_review_gate.HeadRunState.TIMED_OUT,
        )

    def _dirty_paths(path: Path) -> tuple[str, ...]:
        del path
        return (sentinel.name,) if sentinel.exists() else ()

    args = [
        "move-task",
        "WP01",
        "--to",
        "for_review",
        "--mission",
        _MISSION,
        "--no-auto-commit",
    ]
    if json_mode:
        args.append("--json")
    with (
        setup_mocked_env(
            tmp_path,
            mission_slug=_MISSION,
            extra_patches={
                "_validate_ready_for_review": (True, []),
                "_check_unchecked_subtasks": [],
            },
        ),
        patch.object(tasks_move_task, "_default_move_task_ports", return_value=ports),
        patch.object(tasks_move_task, "_mt_resolve_pre_review_workspace", return_value=tmp_path),
        patch.object(tasks_move_task, "_mt_pre_review_changed_files", return_value=("src/example.py",)),
        patch.object(tasks_move_task, "_mt_pre_review_dirty_paths", side_effect=_dirty_paths),
        patch.object(pre_review_gate, "evaluate_with_scope", side_effect=_controlled_timeout),
    ):
        result = CliRunner().invoke(app, args)

    assert result.exit_code == 1
    assert sentinel.read_text(encoding="utf-8") == "preserve me"
    assert router.status_calls == []
    if json_mode:
        payload = json.loads(result.stdout)
        assert payload["pre_review_gate"]["new_checkout_paths"] == [sentinel.name]
    else:
        assert "preserved without cleanup" in result.output
        assert sentinel.name in result.output
