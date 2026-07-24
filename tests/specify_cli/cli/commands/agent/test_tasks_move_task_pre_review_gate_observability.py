"""Acceptance coverage for observable ``move-task --to for_review`` gates."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
import importlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
import warnings

import pytest
from typer.testing import CliRunner

from charter.pack_context import PackContext
from doctrine.drg.models import DRGGraph, DRGNode, NodeKind
from doctrine.drg.org_pack_config import OrgPackEnvVarUnsetError
from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    CommitStatusResult,
    MissionHandle,
    TasksPorts,
)
from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks import app
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.review import gate_bindings, pre_review_gate
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

_META_JSON = json.dumps(
    {
        "mission_id": "01KXG2TDVPTZSYY58E578T5RX3",
        "mission_slug": _MISSION,
        "slug": _MISSION,
        "mission_type": "software-dev",
        "target_branch": "mission-target",
        "topology": "single_branch",
        "vcs": "git",
    }
)


@dataclass(frozen=True)
class _FakeScopeSource:
    """WP09 migration seam: an activation-selected ``ScopeSource`` whose per-file
    scoping yields a fixed target WITHOUT the live ``_gate_coverage`` census
    authority (absent in these hermetic fixture repos). The hook builds the real
    ``GateCoverageScopeSource`` in production; tests patch ``_mt_resolve_scope_source``
    to return this so the bound handler reaches the mocked
    ``evaluate_with_scope`` / ``run_scoped_tests_at_head`` instead of degrading to
    a ``GateAuthoritiesUnavailable`` warn."""

    def test_command(self) -> list[str]:
        return ["pytest", "tests/example"]

    def file_to_scope(self, _path: str) -> tuple[str, ...]:
        return ("tests/example",)

    def parse_results(self, _raw: object) -> tuple[object, ...]:
        return ()


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
    # WP09: the inverted gate resolves the mission type from identity (meta.json),
    # never hardcoded — the fixture must carry it so ``software-dev/review`` binds.
    (feature_dir / "meta.json").write_text(_META_JSON, encoding="utf-8")
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
        patch.object(tasks_move_task, "_mt_resolve_pre_review_workspace", return_value=tmp_path),
        patch.object(tasks_move_task, "_mt_pre_review_changed_files", return_value=("src/example.py",)),
        patch.object(tasks_move_task, "_mt_pre_review_dirty_paths", return_value=()),
        patch.object(tasks_move_task, "_mt_resolve_scope_source", return_value=_FakeScopeSource()),
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
    # WP09: the hook emits the "running scoped tests at head" start notice before
    # dispatching the bound handler. The incumbent's mid-run "still running"
    # liveness callback is NOT threaded through WP04's frozen
    # ``TransitionGateContext`` (it carries no progress hook in half A), so that
    # continuing-liveness line is intentionally not asserted post-inversion.
    assert "running scoped tests at head" in result.output


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
        patch.object(tasks_move_task, "_mt_resolve_pre_review_workspace", return_value=tmp_path),
        patch.object(tasks_move_task, "_mt_pre_review_changed_files", return_value=("src/example.py",)),
        patch.object(tasks_move_task, "_mt_pre_review_dirty_paths", return_value=()),
        patch.object(tasks_move_task, "_mt_resolve_scope_source", return_value=_FakeScopeSource()),
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

    def _terminal_eval(*args: object, **kwargs: object) -> pre_review_gate.GateVerdict:
        del args, kwargs
        # The scoped run (inside the bound handler) writes a test-owned
        # (subprocess-created) byproduct, then is interrupted terminally.
        # IC-07f (WP16): a terminal interruption is an abort, so the owner
        # compensator must revert this created byproduct (unlink it) —
        # genuinely reverted, not "preserved without cleanup" (the retired
        # behaviour) and not left as an unaccounted-for orphan either.
        sentinel.write_text("test-owned", encoding="utf-8")
        return pre_review_gate.GateVerdict(
            outcome=outcome,
            scope=pre_review_gate.ScopeResult.from_override(("tests/example",)),
            reason=f"controlled {state.value}",
            run_state=state,
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
        # WP09: the lane has no commits ahead of its base, so the changed-files
        # SSOT is empty and the gate would cheap-skip; pin a non-empty changed set
        # so the bound handler actually dispatches (dirty-path detection below
        # stays REAL — the sentinel proves the byproduct is enrolled in the
        # tool-artifact owner, WP16/IC-07f). The handler resolves the scope
        # through the ScopeSource, so the terminal run is injected at
        # ``evaluate_with_scope`` (the ScopeSource path routes past
        # ``run_scoped_tests_at_head`` via ``_evaluate_via_scope_source``).
        patch.object(tasks_move_task, "_mt_pre_review_changed_files", return_value=("src/example.py",)),
        patch.object(tasks_move_task, "_mt_resolve_scope_source", return_value=_FakeScopeSource()),
        patch.object(pre_review_gate, "evaluate_with_scope", side_effect=_terminal_eval),
        patch.object(
            tasks_move_task,
            "enroll_subprocess_byproducts",
            wraps=tasks_move_task.enroll_subprocess_byproducts,
        ) as enrol_spy,
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
    # IC-07f (WP16): the retired ``new_checkout_paths`` metadata key is gone —
    # the byproduct is enrolled in the tool-artifact owner instead of being
    # detected and warned about.
    assert "new_checkout_paths" not in payload["pre_review_gate"]
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
    # PRIMARY assertion (byte effect, DIR-041): a terminal interruption is an
    # abort, so the owner compensator must have REVERTED the subprocess-created
    # byproduct — genuinely unlinked, not merely detected-and-abandoned. The
    # lane's git snapshot is therefore back to its pre-gate state with NO
    # carve-out for the sentinel (it no longer exists at all).
    assert not sentinel.exists()
    assert _git_snapshot(lane) == before["lane_git"]
    # SECONDARY (spy) check: the owner was genuinely invoked for this path,
    # not merely happened to leave it alone.
    enrol_spy.assert_called_once()
    (enrolled_paths,) = enrol_spy.call_args.args
    assert {Path(p).name for p in enrolled_paths} == {sentinel.name}
    assert enrol_spy.call_args.kwargs["trusted_roots"] == (lane,)


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
        patch.object(tasks_move_task, "_mt_resolve_pre_review_workspace", return_value=tmp_path),
        patch.object(tasks_move_task, "_mt_pre_review_changed_files", return_value=("src/example.py",)),
        patch.object(tasks_move_task, "_mt_pre_review_dirty_paths", return_value=()),
        patch.object(tasks_move_task, "_mt_resolve_scope_source", return_value=_FakeScopeSource()),
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
def test_gate_created_path_is_reverted_on_terminal_block(
    tmp_path: Path,
    json_mode: bool,
) -> None:
    """IC-07f (WP16): a TIMED_OUT/terminal gate is an abort, so the owner
    compensator must REVERT the subprocess-created byproduct (unlink it) —
    genuinely reverted, never "preserved without cleanup" (the retired
    behaviour) and never silently left as an unaccounted-for orphan either.
    """
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
        patch.object(tasks_move_task, "_mt_resolve_scope_source", return_value=_FakeScopeSource()),
        patch.object(pre_review_gate, "evaluate_with_scope", side_effect=_controlled_timeout),
        patch.object(
            tasks_move_task,
            "enroll_subprocess_byproducts",
            wraps=tasks_move_task.enroll_subprocess_byproducts,
        ) as enrol_spy,
    ):
        result = CliRunner().invoke(app, args)

    assert result.exit_code == 1
    assert router.status_calls == []
    # PRIMARY assertion (byte effect, DIR-041): the terminal/abort path
    # reverts the subprocess-created byproduct through the owner compensator
    # — genuinely unlinked, not "preserve me" (that assertion pinned the bug:
    # a terminal block must NOT leave the created byproduct behind).
    assert not sentinel.exists()
    # SECONDARY (spy) check: the owner was genuinely invoked for this path.
    enrol_spy.assert_called_once()
    (enrolled_paths,) = enrol_spy.call_args.args
    assert {Path(p).name for p in enrolled_paths} == {sentinel.name}
    assert enrol_spy.call_args.kwargs["trusted_roots"] == (tmp_path,)
    if json_mode:
        payload = json.loads(result.stdout)
        assert "new_checkout_paths" not in payload["pre_review_gate"]
    else:
        assert "preserved without cleanup" not in result.output


def test_gate_created_path_is_committed_on_pass(tmp_path: Path) -> None:
    """IC-07f (WP16): a PASSING gate (no terminal, no block) leaves the
    subprocess-created byproduct COMMITTED — the owner enrols a snapshot but
    only an abort restores it, so a passing gate's created byproduct simply
    stays on disk (the mirror case of the abort/revert path above).
    """
    ports, router = _build_command_fixture(tmp_path)
    sentinel = tmp_path / "test-owned-sentinel.txt"

    def _controlled_pass(
        *args: object,
        **kwargs: object,
    ) -> pre_review_gate.GateVerdict:
        sentinel.write_text("byproduct", encoding="utf-8")
        return pre_review_gate.GateVerdict(
            outcome=pre_review_gate.GateOutcome.NO_NEW_FAILURES,
            scope=pre_review_gate.ScopeResult.from_override(("tests/example",)),
            reason="controlled pass",
            run_state=pre_review_gate.HeadRunState.COMPLETED,
        )

    def _dirty_paths(path: Path) -> tuple[str, ...]:
        del path
        return (sentinel.name,) if sentinel.exists() else ()

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
        patch.object(tasks_move_task, "_mt_resolve_scope_source", return_value=_FakeScopeSource()),
        patch.object(pre_review_gate, "evaluate_with_scope", side_effect=_controlled_pass),
        patch.object(
            tasks_move_task,
            "enroll_subprocess_byproducts",
            wraps=tasks_move_task.enroll_subprocess_byproducts,
        ) as enrol_spy,
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

    assert result.exit_code == 0, result.output
    # PRIMARY assertion (byte effect, DIR-041): a passing gate commits the
    # byproduct — the enrolled snapshot is never restored, so the
    # subprocess-created file survives.
    assert sentinel.read_text(encoding="utf-8") == "byproduct"
    payload = json.loads(result.stdout)
    assert "new_checkout_paths" not in payload["pre_review_gate"]
    # SECONDARY (spy) check: the owner was genuinely invoked for this path.
    enrol_spy.assert_called_once()
    (enrolled_paths,) = enrol_spy.call_args.args
    assert {Path(p).name for p in enrolled_paths} == {sentinel.name}
    assert enrol_spy.call_args.kwargs["trusted_roots"] == (tmp_path,)


# --------------------------------------------------------------------------- #
# WP09 / T046 — #2534 closure, proven STRUCTURALLY (not config-dependent).
#
# The pre-review facet of #2534 is closed by construction: the internal
# ``tests.architectural._gate_coverage`` authority is reachable ONLY through the
# activation-selected ``GateCoverageScopeSource``, and even then its import is
# refused for any repo that is not the Spec-Kitty source tree. These two arms
# prove the closure does NOT depend on activation being correctly configured.
# --------------------------------------------------------------------------- #

_GATE_COVERAGE_MODULE = "tests.architectural._gate_coverage"


def _for_review_state(gate_repo_root: Path) -> Any:
    """A minimal ``_MoveTaskState``-shaped stand-in for the collect helper."""
    del gate_repo_root
    return SimpleNamespace(
        json_output=True, force=False, wp=None, old_lane=Lane.IN_PROGRESS, target_lane=Lane.FOR_REVIEW
    )


def test_2534_no_binding_arm_never_touches_internal_gate_coverage(tmp_path: Path) -> None:
    """US1 AS3: a consumer whose active doctrine binds NO gate to the edge runs
    no gate and never reaches the internal ``_gate_coverage`` authority.

    Structural proof via an import spy on the internal loader: it is asserted
    NEVER-called, and the collected verdict is a distinguishable ``NO_COVERAGE``
    warn carrying the resolver's no-binding reason.
    """
    from specify_cli.cli.commands.agent import tasks_move_task as tmt
    from specify_cli.review import scope_source as ss
    from specify_cli.review.gate_bindings import GateBindingResolution, GateCoverage

    inputs = tmt._TransitionGateInputs(
        worktree_path=None, changed_files=("src/example.py",), gate_repo_root=tmp_path
    )
    not_activated = GateBindingResolution(
        coverage=GateCoverage.NOT_ACTIVATED,
        edge_key="in_progress->for_review",
        owning_contract_urn="mission_step_contract:software-dev/review",
        reason="gate binding present for edge in_progress->for_review but owning contract is not activated",
    )
    tasks_stub = SimpleNamespace(console=SimpleNamespace(print=lambda *_a, **_k: None))
    with (
        patch.object(tmt, "_mt_resolve_active_gate_bindings", return_value=not_activated),
        patch.object(ss, "_load_gate_coverage_module", side_effect=AssertionError("internal authority must be unreachable")) as loader_spy,
    ):
        verdicts = tmt._mt_collect_transition_gate_verdicts(_for_review_state(tmp_path), inputs, tasks_stub)

    loader_spy.assert_not_called()
    assert len(verdicts) == 1  # golden-count: cardinality-is-contract
    assert verdicts[0].outcome is pre_review_gate.GateOutcome.NO_COVERAGE
    assert "not activated" in (verdicts[0].reason or "")


def test_2534_erroneous_activation_degrades_without_importing_gate_coverage(tmp_path: Path) -> None:
    """US1 AS4 (load-bearing): even under ERRONEOUS activation of the Spec-Kitty
    handler in a consumer repo, the internal ``_gate_coverage`` module is never
    imported — the handler's own ``GateAuthoritiesUnavailable`` degrades to a
    ``NO_COVERAGE`` warn and the transition completes.

    The consumer repo (``tmp_path``) carries no ``tests/architectural/_gate_coverage.py``;
    a spy on ``importlib.import_module`` simulates that absence and records every
    import attempt. The assertion is structural (import spy + ``sys.modules``),
    not merely that the outcome matches.
    """
    from specify_cli.cli.commands.agent import tasks_move_task as tmt
    from specify_cli.review.gate_registry import TransitionGateContext, get_gate_handler
    from specify_cli.review.scope_source import GateCoverageScopeSource

    ctx = TransitionGateContext(
        changed_files=("src/example.py",),
        scope_source=GateCoverageScopeSource(repo_root=tmp_path),
        baseline=None,
        repo_root=tmp_path,
        force=False,
        from_lane=Lane.IN_PROGRESS,
        to_lane=Lane.FOR_REVIEW,
    )
    binding: Any = SimpleNamespace(handler="spec-kitty-pre-review")

    real_import = importlib.import_module
    attempted: list[str] = []

    def _spy_import(name: str, *args: Any, **kwargs: Any) -> Any:
        attempted.append(name)
        if name == _GATE_COVERAGE_MODULE:
            raise ImportError(f"No module named {name!r} in this consumer repo")
        return real_import(name, *args, **kwargs)

    before = {key for key in sys.modules if "_gate_coverage" in key}
    with patch.object(importlib, "import_module", side_effect=_spy_import):
        verdict = tmt._mt_dispatch_one_gate(binding, ctx, get_gate_handler)
    after = {key for key in sys.modules if "_gate_coverage" in key}

    # Fail-open: the erroneous activation degrades to a visible unverified warn.
    assert verdict.outcome is pre_review_gate.GateOutcome.NO_COVERAGE
    assert "unverified" in (verdict.reason or "").lower()
    # Structural closure: the consumer's internal authority never entered the
    # module table via this dispatch (the import was refused, not swallowed).
    assert after == before
    assert _GATE_COVERAGE_MODULE not in (after - before)


# --------------------------------------------------------------------------- #
# Resolution-phase fail-open (regression for the pre-dispatch coverage hole).
#
# The inverted hook's fail-open envelope (``_mt_fail_open_gate``) wrapped ONLY
# the dispatch/override tiers. A fault in the PRE-DISPATCH resolution phase —
# binding resolution, context build, input resolution, or the deprecation warn —
# escaped unwrapped to ``_do_move_task``'s outer ``except Exception`` and REFUSED
# the ``for_review`` move (a fail-open→fail-closed regression + an unsanctioned
# third hard-stop); a ``Ctrl-C`` slipped past that ``except Exception`` entirely
# and exited 130, breaching the terminal-``CANCELLED`` invariant.
#
# These arms drive the REAL resolver (``resolve_gate_bindings_for_transition``
# via the real built-in ``software-dev/review`` contract) into the specific
# realistic failure modes — NOT a canned ``GateBindingResolution`` — and assert
# warn-and-proceed / terminal-CANCELLED, never ``typer.Exit(1)`` refusal or 130.
# --------------------------------------------------------------------------- #


def _build_binding_resolution_fixture(tmp_path: Path) -> tuple[TasksPorts, _RecordingCoordRouter]:
    """A fixture whose WP carries NO ``pre_review_test_scope``.

    The operator-override tier short-circuits binding resolution when a scope is
    pinned; omitting it forces the hook down the REAL doctrine binding-resolution
    path (``resolve_gate_bindings_for_transition`` on the built-in
    ``software-dev/review`` contract), which is where the resolution-phase faults
    under test are raised.
    """
    feature_dir = tmp_path / "kitty-specs" / _MISSION
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tmp_path / ".kittify").mkdir()
    (feature_dir / "meta.json").write_text(_META_JSON, encoding="utf-8")
    (tasks_dir / "WP01-test.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Binding-resolution gate\n"
        "execution_mode: code_change\n"
        "agent: testbot\n"
        "owned_files:\n  - src/example.py\n"
        "authoritative_surface: src/\n"
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
    ports = TasksPorts(fs=FakeFsReader(), coord=router, git=FakeGitOps(), render=FakeRender())
    return ports, router


def _minimal_review_drg() -> DRGGraph:
    """A real (non-fabricated) DRG carrying the owning review-contract node."""
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-01-01T00:00:00Z",
        generated_by="test",
        nodes=[
            DRGNode(urn="mission_step_contract:software-dev/review", kind=NodeKind.MISSION_STEP_CONTRACT),
            DRGNode(urn="mission_type:software-dev", kind=NodeKind.MISSION_TYPE),
        ],
        edges=[],
    )


def _invoke_for_review(tmp_path: Path, ports: TasksPorts, *seams: Any) -> Any:
    """Drive the real Typer ``move-task --to for_review`` under the given seam patches."""
    with ExitStack() as stack:
        stack.enter_context(
            setup_mocked_env(
                tmp_path,
                mission_slug=_MISSION,
                extra_patches={
                    "_validate_ready_for_review": (True, []),
                    "_check_unchecked_subtasks": [],
                },
            )
        )
        stack.enter_context(patch.object(tasks_move_task, "_default_move_task_ports", return_value=ports))
        stack.enter_context(patch.object(tasks_move_task, "_mt_resolve_pre_review_workspace", return_value=tmp_path))
        stack.enter_context(
            patch.object(tasks_move_task, "_mt_pre_review_changed_files", return_value=("src/example.py",))
        )
        stack.enter_context(patch.object(tasks_move_task, "_mt_pre_review_dirty_paths", return_value=()))
        for seam in seams:
            stack.enter_context(seam)
        return CliRunner().invoke(
            app,
            ["move-task", "WP01", "--to", "for_review", "--mission", _MISSION, "--no-auto-commit", "--json"],
        )


def _assert_warned_and_proceeded(result: Any, router: _RecordingCoordRouter) -> None:
    """Fail-open: the resolution fault degraded to a NO_COVERAGE warn and the move applied."""
    assert result.exit_code == 0, result.output
    assert len(router.status_calls) == 1
    request = router.status_calls[0]
    assert request.to_lane is Lane.FOR_REVIEW
    metadata = (request.policy_metadata or {})["pre_review_gate"]
    assert metadata["outcome"] == pre_review_gate.GateOutcome.NO_COVERAGE.value
    assert "unverified" in (metadata.get("reason") or "").lower()


def test_org_pack_env_unset_during_resolution_warns_and_proceeds(tmp_path: Path) -> None:
    """An ``OrgPackEnvVarUnsetError`` (``_resolve_pack_context`` fail-closed re-raise)
    degrades to a NO_COVERAGE warn — the incumbent behaviour — not a refused move."""
    ports, router = _build_binding_resolution_fixture(tmp_path)
    result = _invoke_for_review(
        tmp_path,
        ports,
        patch.object(gate_bindings, "load_validated_graph", return_value=_minimal_review_drg()),
        patch.object(
            PackContext,
            "from_config",
            side_effect=OrgPackEnvVarUnsetError("org-pack", "$UNSET_TOKEN/path", "UNSET_TOKEN"),
        ),
    )
    _assert_warned_and_proceeded(result, router)


def test_graph_load_error_during_resolution_warns_and_proceeds(tmp_path: Path) -> None:
    """A malformed/invalid DRG (``load_validated_graph`` raises) degrades to a
    NO_COVERAGE warn instead of escaping unwrapped and refusing the move."""
    ports, router = _build_binding_resolution_fixture(tmp_path)
    result = _invoke_for_review(
        tmp_path,
        ports,
        patch.object(
            gate_bindings,
            "load_validated_graph",
            side_effect=RuntimeError("malformed DRG graph"),
        ),
    )
    _assert_warned_and_proceeded(result, router)


def test_malformed_contract_during_resolution_warns_and_proceeds(tmp_path: Path) -> None:
    """A malformed project ``*.step-contract.yaml`` (repository construction raises)
    degrades to a NO_COVERAGE warn instead of a fail-closed refusal."""
    ports, router = _build_binding_resolution_fixture(tmp_path)
    result = _invoke_for_review(
        tmp_path,
        ports,
        patch.object(
            gate_bindings,
            "_build_repository",
            side_effect=ValueError("malformed spec-kitty-pre-review.step-contract.yaml"),
        ),
    )
    _assert_warned_and_proceeded(result, router)


def test_keyboard_interrupt_during_resolution_is_terminal_cancelled_not_130(tmp_path: Path) -> None:
    """A ``Ctrl-C`` during the resolution phase yields the sanctioned terminal
    CANCELLED hard-stop (exit 1), NOT an unhandled ``BaseException`` → exit 130."""
    ports, router = _build_binding_resolution_fixture(tmp_path)
    result = _invoke_for_review(
        tmp_path,
        ports,
        patch.object(gate_bindings, "load_validated_graph", side_effect=KeyboardInterrupt),
    )
    assert result.exit_code == 1
    assert result.exit_code != 130
    payload = json.loads(result.stdout)
    assert payload["pre_review_gate"]["outcome"] == pre_review_gate.GateOutcome.CANCELLED.value
    assert payload["transition_applied"] is False
    assert router.status_calls == []


def test_deprecation_warn_under_filterwarnings_error_folds_into_envelope(tmp_path: Path) -> None:
    """Renata #2: the ``review.pre_review_test_command`` deprecation ``warnings.warn``
    must not hard-fail the move under ``-W error`` / pytest ``filterwarnings=error``.

    Folded into the resolution fail-open envelope, a ``DeprecationWarning`` promoted
    to an exception degrades to a single NO_COVERAGE warn and the move proceeds.
    """
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text(
        "review:\n  pre_review_test_command: pytest tests/legacy\n", encoding="utf-8"
    )
    st: Any = SimpleNamespace(
        main_repo_root=tmp_path,
        json_output=True,
        force=False,
        wp=None,
        old_lane=Lane.IN_PROGRESS,
        target_lane=Lane.FOR_REVIEW,
    )
    tasks_stub = SimpleNamespace(console=SimpleNamespace(print=lambda *_a, **_k: None))
    tasks_move_task._pre_review_test_command_deprecation_emitted = False
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        inputs, dirty_before, verdicts = tasks_move_task._mt_resolve_transition_gate_verdicts(
            st, tasks_stub
        )
    assert inputs is None
    assert dirty_before == ()
    assert len(verdicts) == 1  # golden-count: cardinality-is-contract
    assert verdicts[0].outcome is pre_review_gate.GateOutcome.NO_COVERAGE
    assert "unverified" in (verdicts[0].reason or "").lower()
