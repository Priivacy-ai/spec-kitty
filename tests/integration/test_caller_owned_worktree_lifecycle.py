"""Production CLI coverage for caller-owned linked-worktree Missions."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.context import app as context_app
from specify_cli.cli.commands.agent.mission import app as mission_app
from specify_cli.cli.commands.agent.status import app as status_app
from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.cli.commands.agent.workflow import app as workflow_app
from specify_cli.cli.commands import accept as accept_cmd
from specify_cli.cli.commands import next_cmd


pytestmark = [pytest.mark.integration]

_MISSION_ID = "01AAAAAAAAAAAAAAAAAAAAAAAB"
_MISSION_SLUG = "caller-mission-01AAAAAA"
_TARGET_BRANCH = "codex/caller-mission"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _repo_with_caller_mission(tmp_path: Path) -> tuple[Path, Path, Path]:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(repository_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(repository_root, "config", "user.email", "tests@example.invalid")
    _git(repository_root, "config", "user.name", "Spec Kitty Tests")
    (repository_root / ".kittify").mkdir()
    (repository_root / ".kittify" / "config.yaml").write_text(
        "project:\n"
        "  name: caller-owned-test\n"
        "mission_type_activations:\n"
        "  - software-dev\n",
        encoding="utf-8",
    )
    (repository_root / "README.md").write_text("primary\n", encoding="utf-8")
    _git(repository_root, "add", ".")
    _git(repository_root, "commit", "-q", "-m", "test: initialize repository")

    caller = tmp_path / "caller-owned"
    _git(
        repository_root,
        "worktree",
        "add",
        "-q",
        "-b",
        _TARGET_BRANCH,
        str(caller),
    )
    mission_dir = caller / "kitty-specs" / _MISSION_SLUG
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mission_slug": _MISSION_SLUG,
                "target_branch": _TARGET_BRANCH,
                "planning_base_branch": _TARGET_BRANCH,
                "topology": "single_branch",
                "mission_type": "software-dev",
            }
        ),
        encoding="utf-8",
    )
    (mission_dir / "spec.md").write_text("# Caller Mission\n", encoding="utf-8")
    (mission_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    return repository_root, caller, mission_dir


def _primary_snapshot(repository_root: Path) -> tuple[str, str, str]:
    return (
        _git(repository_root, "branch", "--show-current"),
        _git(repository_root, "rev-parse", "HEAD"),
        _git(repository_root, "status", "--porcelain"),
    )


def test_tasks_legacy_fallback_runs_canonical_context_resolver_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from specify_cli.cli import selector_resolution
    from specify_cli.cli.commands.agent import tasks

    repository_root, caller, _mission_dir = _repo_with_caller_mission(tmp_path)
    legacy_slug = "legacy-without-meta"
    (repository_root / "kitty-specs" / legacy_slug).mkdir(parents=True)
    observed: list[tuple[Path, str, Path | None]] = []
    resolve_operation = selector_resolution.resolve_mission_operation_context_cli

    def traced_resolve_operation(
        project_root: Path,
        handle: str,
        **kwargs: object,
    ) -> object:
        cwd = kwargs.get("cwd")
        observed.append(
            (
                project_root,
                handle,
                cwd if isinstance(cwd, Path) else None,
            )
        )
        return resolve_operation(project_root, handle, **kwargs)

    monkeypatch.setattr(
        selector_resolution,
        "resolve_mission_operation_context_cli",
        traced_resolve_operation,
    )
    monkeypatch.chdir(caller)

    assert (
        tasks._find_mission_slug(
            explicit_mission=legacy_slug,
            repo_root=repository_root,
        )
        == legacy_slug
    )
    assert observed == [(repository_root, legacy_slug, caller)]


def test_context_cli_resolves_caller_owned_mission_without_touching_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, mission_dir = _repo_with_caller_mission(tmp_path)
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)

    result = CliRunner().invoke(
        context_app,
        [
            "--action",
            "status",
            "--mission",
            _MISSION_ID,
            "--json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["mission_slug"] == _MISSION_SLUG
    assert Path(payload["feature_dir"]) == mission_dir
    assert _primary_snapshot(repository_root) == before


def test_two_caller_worktrees_resolve_only_their_own_missions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, first, _mission_dir = _repo_with_caller_mission(tmp_path)
    second = tmp_path / "second-caller"
    _git(repository_root, "worktree", "add", "-q", "-b", "codex/second", str(second))
    second_id = "01BBBBBBBBBBBBBBBBBBBBBBBB"
    second_slug = "second-mission-01BBBBBBBBBBBBBBBBBBBBBBBB"
    second_dir = second / "kitty-specs" / second_slug
    second_dir.mkdir(parents=True)
    (second_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": second_id,
                "mission_slug": second_slug,
                "target_branch": "codex/second",
                "topology": "single_branch",
                "mission_type": "software-dev",
            }
        ),
        encoding="utf-8",
    )
    (second_dir / "spec.md").write_text("# Second\n", encoding="utf-8")
    (second_dir / "status.events.jsonl").write_text("", encoding="utf-8")

    for cwd, mission_id, expected_dir in (
        (first, _MISSION_ID, first / "kitty-specs" / _MISSION_SLUG),
        (second, second_id, second_dir),
    ):
        monkeypatch.chdir(cwd)
        result = CliRunner().invoke(
            context_app,
            ["--action", "status", "--mission", mission_id, "--json"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert Path(json.loads(result.stdout)["feature_dir"]) == expected_dir


def test_status_cli_reads_caller_surface_and_keeps_primary_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, _mission_dir = _repo_with_caller_mission(tmp_path)
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)

    result = CliRunner().invoke(
        status_app,
        ["validate", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["mission_slug"] == _MISSION_SLUG
    assert payload["passed"] is True
    assert _primary_snapshot(repository_root) == before


def test_context_cli_fails_closed_on_caller_primary_identity_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, _mission_dir = _repo_with_caller_mission(tmp_path)
    primary_mission = repository_root / "kitty-specs" / _MISSION_SLUG
    primary_mission.mkdir(parents=True)
    (primary_mission / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01BBBBBBBBBBBBBBBBBBBBBBBB",
                "mission_slug": _MISSION_SLUG,
            }
        ),
        encoding="utf-8",
    )
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)

    result = CliRunner().invoke(
        context_app,
        ["--action", "status", "--mission", _MISSION_SLUG, "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 2
    payload = json.loads(result.stderr)
    assert payload["error"] == "MISSION_SURFACE_CONFLICT"
    assert len(payload["candidates"]) == 2
    assert _primary_snapshot(repository_root) == before


def test_operation_context_overhead_p95_under_fifty_ms_with_one_hundred_missions(
    tmp_path: Path,
) -> None:
    repository_root, caller, _mission_dir = _repo_with_caller_mission(tmp_path)
    for index in range(99):
        mission_id = f"01{index:024d}"
        mission_dir = caller / "kitty-specs" / f"benchmark-{index:03d}"
        mission_dir.mkdir(parents=True)
        (mission_dir / "meta.json").write_text(
            json.dumps(
                {
                    "mission_id": mission_id,
                    "mission_slug": mission_dir.name,
                }
            ),
            encoding="utf-8",
        )

    from specify_cli.context.mission_resolver import resolve_mission
    from specify_cli.missions.operation_context import resolve_mission_operation_context

    selector = "benchmark-098"
    resolve_mission(selector, caller)
    resolve_mission_operation_context(repository_root, selector, cwd=caller)
    overhead_ms: list[float] = []
    for _ in range(100):
        started = time.perf_counter()
        resolve_mission(selector, caller)
        baseline_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        resolve_mission_operation_context(repository_root, selector, cwd=caller)
        operation_ms = (time.perf_counter() - started) * 1000
        overhead_ms.append(max(0.0, operation_ms - baseline_ms))

    p95_ms = sorted(overhead_ms)[94]
    assert p95_ms <= 50.0, f"operation-context p95 overhead={p95_ms:.2f}ms"


def test_operation_context_indexes_each_candidate_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, _mission_dir = _repo_with_caller_mission(tmp_path)

    from specify_cli.context.mission_resolver import FsMissionResolver
    from specify_cli.missions.operation_context import resolve_mission_operation_context

    indexed_roots: list[Path] = []
    original = FsMissionResolver.all_missions

    def recording_all_missions(self: FsMissionResolver):
        indexed_roots.append(self._repo_root.resolve())
        return original(self)

    monkeypatch.setattr(FsMissionResolver, "all_missions", recording_all_missions)

    context = resolve_mission_operation_context(
        repository_root,
        _MISSION_SLUG,
        cwd=caller,
    )

    assert context.mission_anchor_root == caller.resolve()
    assert indexed_roots == [caller.resolve(), repository_root.resolve()]


def test_setup_plan_scaffolds_in_caller_worktree_not_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, mission_dir = _repo_with_caller_mission(tmp_path)
    (mission_dir / "spec.md").write_text(
        """# Spec — Caller Mission

## Functional Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Linked lifecycle | Continue the mission in its caller-owned linked worktree. | High | Open |
""",
        encoding="utf-8",
    )
    _git(caller, "add", ".")
    _git(caller, "commit", "-q", "-m", "test: add caller mission")
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)

    result = CliRunner().invoke(
        mission_app,
        ["setup-plan", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["mission_slug"] == _MISSION_SLUG
    assert Path(payload["feature_dir"]) == mission_dir
    assert Path(payload["plan_file"]) == mission_dir / "plan.md"
    assert (mission_dir / "plan.md").is_file()
    assert not (repository_root / "kitty-specs" / _MISSION_SLUG).exists()
    assert _primary_snapshot(repository_root) == before


def test_tasks_status_reads_caller_planning_and_status_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, mission_dir = _repo_with_caller_mission(tmp_path)
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(
        """---
work_package_id: WP01
title: Caller work
dependencies: []
agent: codex
assignee: codex
---

# WP01 — Caller work
""",
        encoding="utf-8",
    )
    from specify_cli.status import bootstrap_canonical_state

    bootstrap_canonical_state(mission_dir, _MISSION_SLUG)
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)

    result = CliRunner().invoke(
        tasks_app,
        ["status", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["mission_slug"] == _MISSION_SLUG
    assert payload["total_wps"] == 1
    assert _primary_snapshot(repository_root) == before


def test_tasks_finalize_validates_caller_planning_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, mission_dir = _repo_with_caller_mission(tmp_path)
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Caller work\n---\n\n# WP01\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text(
        "# Work Packages\n\n## WP01 - caller work\n- [ ] T001 verify\n",
        encoding="utf-8",
    )
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)

    result = CliRunner().invoke(
        tasks_app,
        ["finalize-tasks", "--mission", _MISSION_ID, "--json", "--validate-only"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["result"] == "validation_passed"
    assert payload["dependencies"] == {"WP01": []}
    assert _primary_snapshot(repository_root) == before


@dataclass(frozen=True)
class _QueryDecision:
    mission: str

    def to_dict(self) -> dict[str, object]:
        return {"kind": "state", "mission": self.mission, "action": "plan"}


def test_next_query_uses_caller_anchor_and_keeps_primary_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, _mission_dir = _repo_with_caller_mission(tmp_path)
    before = _primary_snapshot(repository_root)
    observed: dict[str, Path] = {}

    def query_current_state(
        _agent: str | None,
        mission_slug: str,
        repo_root: Path,
    ) -> _QueryDecision:
        observed["repo_root"] = Path(repo_root)
        return _QueryDecision(mission_slug)

    fake_bridge = SimpleNamespace(
        QueryModeValidationError=RuntimeError,
        query_current_state=query_current_state,
    )
    monkeypatch.setattr(next_cmd, "_runtime_bridge_module", lambda: fake_bridge)
    monkeypatch.setattr(next_cmd, "_run_charter_preflight_for_next", lambda *args, **kwargs: None)
    monkeypatch.chdir(caller)
    app = typer.Typer()
    app.command(name="next")(next_cmd.next_step)

    result = CliRunner().invoke(
        app,
        ["--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["mission"] == _MISSION_SLUG
    assert observed["repo_root"] == caller
    assert _primary_snapshot(repository_root) == before


def test_accept_diagnose_and_no_commit_use_caller_without_touching_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, mission_dir = _repo_with_caller_mission(tmp_path)
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Caller work\n"
        "lane: done\n"
        "assignee: codex\n"
        "agent: codex\n"
        "shell_pid: '12345'\n"
        "subtasks: []\n"
        "---\n\n# WP01\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text(
        "# Work Packages\n\n## WP01 - caller work\n- [x] T001 verify\n",
        encoding="utf-8",
    )
    (mission_dir / "plan.md").write_text("# Plan\n\nDone.\n", encoding="utf-8")
    (mission_dir / "contracts").mkdir()
    for required in ("src", "tests", "docs"):
        directory = caller / required
        directory.mkdir()
        (directory / ".gitkeep").write_text("", encoding="utf-8")
    meta = json.loads((mission_dir / "meta.json").read_text(encoding="utf-8"))
    meta.update(
        {
            "mission_number": "001",
            "slug": _MISSION_SLUG,
            "friendly_name": "Caller Mission",
            "created_at": "2026-08-13T00:00:00Z",
        }
    )
    (mission_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n",
        encoding="utf-8",
    )

    from specify_cli.acceptance.matrix import (
        AcceptanceCriterion,
        AcceptanceMatrix,
        write_acceptance_matrix,
    )
    from specify_cli.lanes.models import ExecutionLane, LanesManifest
    from specify_cli.lanes.persistence import write_lanes_json
    from specify_cli.status.emit import build_claim_policy_metadata
    from specify_cli.status.models import Lane, StatusEvent
    from specify_cli.status.reducer import materialize
    from specify_cli.status.store import append_event

    append_event(
        mission_dir,
        StatusEvent(
            event_id="01CCCCCCCCCCCCCCCCCCCCCCCD",
            mission_slug=_MISSION_SLUG,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-08-13T00:00:00+00:00",
            actor="codex",
            force=False,
            execution_mode="direct_repo",
            policy_metadata=build_claim_policy_metadata(
                shell_pid=12345,
                shell_pid_created_at="2026-08-13T00:00:00+00:00",
                agent="codex",
            ),
        ),
    )
    append_event(
        mission_dir,
        StatusEvent(
            event_id="01CCCCCCCCCCCCCCCCCCCCCCCE",
            mission_slug=_MISSION_SLUG,
            wp_id="WP01",
            from_lane=Lane.CLAIMED,
            to_lane=Lane.DONE,
            at="2026-08-13T00:01:00+00:00",
            actor="codex",
            force=True,
            reason="test fixture",
            execution_mode="direct_repo",
        ),
    )
    materialize(mission_dir)
    write_lanes_json(
        mission_dir,
        LanesManifest(
            version=1,
            mission_slug=_MISSION_SLUG,
            mission_id=_MISSION_ID,
            mission_branch=_TARGET_BRANCH,
            target_branch=_TARGET_BRANCH,
            lanes=[
                ExecutionLane(
                    lane_id="lane-a",
                    wp_ids=("WP01",),
                    write_scope=("src/**",),
                    predicted_surfaces=("caller",),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
            computed_at="2026-08-13T00:00:00Z",
            computed_from="test",
        ),
    )
    write_acceptance_matrix(
        mission_dir,
        AcceptanceMatrix(
            mission_slug=_MISSION_SLUG,
            criteria=[
                AcceptanceCriterion(
                    criterion_id="AC1",
                    description="caller lifecycle works",
                    proof_type="automated_test",
                    pass_fail="pass",
                )
            ],
        ),
    )
    _git(caller, "add", ".")
    _git(caller, "commit", "-q", "-m", "test: prepare caller acceptance")
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)
    app = typer.Typer()
    app.command(name="accept")(accept_cmd.accept)

    result = CliRunner().invoke(
        app,
        ["--mission", _MISSION_ID, "--diagnose", "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["mission_slug"] == _MISSION_SLUG
    assert payload["diagnose"] is True
    assert _primary_snapshot(repository_root) == before

    no_commit = CliRunner().invoke(
        app,
        ["--mission", _MISSION_ID, "--no-commit", "--json"],
        catch_exceptions=False,
    )
    assert no_commit.exit_code == 0, no_commit.output
    assert _primary_snapshot(repository_root) == before


def test_action_implement_claims_planning_wp_in_caller_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, caller, mission_dir = _repo_with_caller_mission(tmp_path)
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01-caller.md").write_text(
        """---
work_package_id: WP01
title: Caller work
dependencies: []
execution_mode: planning_artifact
owned_files:
  - README.md
agent: codex
---

# WP01 — Caller work

## Activity Log
""",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text(
        "# Work Packages\n\n## WP01 - caller work\n- [ ] T001 verify\n",
        encoding="utf-8",
    )
    (mission_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (mission_dir / "lanes.json").write_text(
        json.dumps(
            {
                "version": 1,
                "mission_slug": _MISSION_SLUG,
                "mission_id": _MISSION_ID,
                "mission_branch": _TARGET_BRANCH,
                "target_branch": _TARGET_BRANCH,
                "lanes": [
                    {
                        "lane_id": "lane-planning",
                        "wp_ids": ["WP01"],
                        "write_scope": ["README.md"],
                        "predicted_surfaces": [],
                        "depends_on_lanes": [],
                        "parallel_group": 0,
                    }
                ],
                "computed_at": "2026-08-13T00:00:00+00:00",
                "computed_from": "caller-worktree-test",
                "planning_artifact_wps": ["WP01"],
            }
        ),
        encoding="utf-8",
    )
    from specify_cli.analysis_report import write_analysis_report
    from specify_cli.status import bootstrap_canonical_state, read_events, reduce
    from specify_cli.status.models import Lane, StatusEvent
    from specify_cli.status.store import append_event
    from kernel.clock import now_utc_iso

    bootstrap_canonical_state(mission_dir, _MISSION_SLUG)
    write_analysis_report(
        feature_dir=mission_dir,
        repo_root=caller,
        body="# Specification Analysis Report\n\nNo blocking findings.\n",
        analyzer_agent="codex",
    )
    _git(caller, "add", ".")
    _git(caller, "commit", "-q", "-m", "test: prepare caller lifecycle")
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)

    result = CliRunner().invoke(
        workflow_app,
        ["implement", "WP01", "--mission", _MISSION_ID, "--agent", "codex"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "Baseline artifact commit failed" not in result.output
    snapshot = reduce(read_events(mission_dir))
    assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
    assert _primary_snapshot(repository_root) == before

    append_event(
        mission_dir,
        StatusEvent(
            event_id="01CCCCCCCCCCCCCCCCCCCCCCCC",
            mission_slug=_MISSION_SLUG,
            wp_id="WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
            at=now_utc_iso(),
            actor="fixture",
            force=True,
            execution_mode="direct_repo",
        ),
    )
    _git(caller, "add", ".")
    _git(caller, "commit", "-q", "-m", "test: ready caller review")

    review_result = CliRunner().invoke(
        workflow_app,
        ["review", "WP01", "--mission", _MISSION_ID, "--agent", "reviewer"],
        catch_exceptions=False,
    )

    assert review_result.exit_code == 0, review_result.output
    review_snapshot = reduce(read_events(mission_dir))
    assert review_snapshot.work_packages["WP01"]["lane"] == "in_review"
    assert _primary_snapshot(repository_root) == before


def test_complete_caller_owned_cli_lifecycle_keeps_primary_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run one created Mission through every required production CLI family."""
    repository_root, caller, mission_dir = _repo_with_caller_mission(tmp_path)
    shutil.rmtree(mission_dir)
    from specify_cli.cli import selector_resolution as selector_module

    operation_roots: list[tuple[Path, Path]] = []
    original_operation_resolver = getattr(
        selector_module,
        "resolve_mission_operation_context",
        None,
    )
    if original_operation_resolver is not None:

        def recording_operation_resolver(*args, **kwargs):
            context = original_operation_resolver(*args, **kwargs)
            operation_roots.append(
                (context.repository_root, context.mission_anchor_root)
            )
            return context

        monkeypatch.setattr(
            selector_module,
            "resolve_mission_operation_context",
            recording_operation_resolver,
        )
    before = _primary_snapshot(repository_root)
    monkeypatch.chdir(caller)
    runner = CliRunner()

    from ulid import ULID

    monkeypatch.setattr(
        "specify_cli.core.mission_creation.ULID",
        lambda: ULID.from_str(_MISSION_ID),
    )
    create_result = runner.invoke(
        mission_app,
        [
            "create",
            "caller-mission",
            "--mission-type",
            "software-dev",
            "--topology",
            "single_branch",
            "--target-branch",
            _TARGET_BRANCH,
            "--json",
        ],
        catch_exceptions=False,
    )
    assert create_result.exit_code == 0, create_result.output
    create_payload = json.loads(create_result.stdout)
    assert create_payload["mission_id"] == _MISSION_ID
    assert Path(create_payload["feature_dir"]) == mission_dir
    created_meta = json.loads(
        (mission_dir / "meta.json").read_text(encoding="utf-8")
    )
    assert created_meta["target_branch"] == _TARGET_BRANCH, created_meta
    (mission_dir / "spec.md").write_text(
        """# Spec — Caller Mission

## Functional Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Linked lifecycle | Continue the Mission in this worktree. | High | Open |
""",
        encoding="utf-8",
    )
    _git(caller, "add", ".")
    _git(caller, "commit", "-q", "-m", "test: create caller-owned mission")

    context_result = runner.invoke(
        context_app,
        ["--action", "status", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )
    assert context_result.exit_code == 0, context_result.output
    assert Path(json.loads(context_result.stdout)["feature_dir"]) == mission_dir

    materialize_result = runner.invoke(
        status_app,
        ["materialize", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )
    assert materialize_result.exit_code == 0, materialize_result.output

    status_result = runner.invoke(
        status_app,
        ["validate", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )
    assert status_result.exit_code == 0, status_result.output


    plan_result = runner.invoke(
        mission_app,
        ["setup-plan", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )
    assert plan_result.exit_code == 0, plan_result.output
    assert (mission_dir / "plan.md").is_file()

    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    wp_path = tasks_dir / "WP01-caller.md"
    wp_path.write_text(
        """---
work_package_id: WP01
title: Caller work
dependencies: []
execution_mode: planning_artifact
owned_files:
  - README.md
agent: codex
assignee: codex
shell_pid: '12345'
subtasks:
  - T001
---

# WP01 — Caller work
""",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text(
        "# Work Packages\n\n## WP01 - caller work\n- [ ] T001 verify\n",
        encoding="utf-8",
    )
    (mission_dir / "lanes.json").write_text(
        json.dumps(
            {
                "version": 1,
                "mission_slug": _MISSION_SLUG,
                "mission_id": _MISSION_ID,
                "mission_branch": _TARGET_BRANCH,
                "target_branch": _TARGET_BRANCH,
                "lanes": [
                    {
                        "lane_id": "lane-planning",
                        "wp_ids": ["WP01"],
                        "write_scope": ["README.md"],
                        "predicted_surfaces": [],
                        "depends_on_lanes": [],
                        "parallel_group": 0,
                    }
                ],
                "computed_at": "2026-08-13T00:00:00+00:00",
                "computed_from": "caller-lifecycle-acceptance",
                "planning_artifact_wps": ["WP01"],
            }
        ),
        encoding="utf-8",
    )

    from specify_cli.analysis_report import write_analysis_report
    from specify_cli.status import read_events, reduce

    write_analysis_report(
        feature_dir=mission_dir,
        repo_root=caller,
        body="# Specification Analysis Report\n\nNo blocking findings.\n",
        analyzer_agent="codex",
    )
    _git(caller, "add", ".")
    _git(caller, "commit", "-q", "-m", "test: prepare planning lifecycle")

    tasks_status = runner.invoke(
        tasks_app,
        ["status", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )
    assert tasks_status.exit_code == 0, tasks_status.output
    assert json.loads(tasks_status.stdout)["total_wps"] == 1

    tasks_finalize = runner.invoke(
        tasks_app,
        [
            "finalize-tasks",
            "--mission",
            _MISSION_ID,
            "--json",
        ],
        catch_exceptions=False,
    )
    assert tasks_finalize.exit_code == 0, tasks_finalize.output

    implement_result = runner.invoke(
        workflow_app,
        ["implement", "WP01", "--mission", _MISSION_ID, "--agent", "codex"],
        catch_exceptions=False,
    )
    assert implement_result.exit_code == 0, implement_result.output
    assert reduce(read_events(mission_dir)).work_packages["WP01"]["lane"] == "in_progress"

    (caller / "README.md").write_text("caller implementation\n", encoding="utf-8")
    _git(caller, "add", "README.md")
    _git(caller, "commit", "-q", "-m", "test: implement caller work")

    mark_result = runner.invoke(
        tasks_app,
        ["mark-status", "T001", "--status", "done", "--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )
    assert mark_result.exit_code == 0, mark_result.output
    marked = json.loads((mission_dir / "status.json").read_text(encoding="utf-8"))
    assert marked["work_packages"]["WP01"]["subtasks"]["T001"] == "done"

    for_review_result = runner.invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--mission",
            _MISSION_ID,
            "--agent",
            "codex",
            "--skip-pre-review-gate",
            "--no-auto-commit",
            "--json",
        ],
        catch_exceptions=False,
    )
    assert for_review_result.exit_code == 0, for_review_result.output
    assert reduce(read_events(mission_dir)).work_packages["WP01"]["lane"] == "for_review"

    review_result = runner.invoke(
        workflow_app,
        ["review", "WP01", "--mission", _MISSION_ID, "--agent", "reviewer"],
        catch_exceptions=False,
    )
    assert review_result.exit_code == 0, review_result.output
    assert reduce(read_events(mission_dir)).work_packages["WP01"]["lane"] == "in_review"

    observed: dict[str, Path] = {}

    def query_current_state(
        _agent: str | None,
        mission_slug: str,
        repo_root: Path,
    ) -> _QueryDecision:
        observed["repo_root"] = Path(repo_root)
        return _QueryDecision(mission_slug)

    monkeypatch.setattr(
        next_cmd,
        "_runtime_bridge_module",
        lambda: SimpleNamespace(
            QueryModeValidationError=RuntimeError,
            query_current_state=query_current_state,
        ),
    )
    monkeypatch.setattr(
        next_cmd,
        "_run_charter_preflight_for_next",
        lambda *args, **kwargs: None,
    )
    next_app = typer.Typer()
    next_app.command(name="next")(next_cmd.next_step)
    next_result = runner.invoke(
        next_app,
        ["--mission", _MISSION_ID, "--json"],
        catch_exceptions=False,
    )
    assert next_result.exit_code == 0, next_result.output
    assert observed["repo_root"] == caller

    review_dir = mission_dir / "tasks" / "WP01-caller"
    review_dir.mkdir(exist_ok=True)
    review_path = review_dir / "review-cycle-1.md"
    review_path.write_text(
        "---\n"
        "cycle_number: 1\n"
        f"mission_slug: {_MISSION_SLUG}\n"
        "reviewed_at: '2026-08-13T12:00:00Z'\n"
        "reviewer_agent: reviewer\n"
        "verdict: approved\n"
        "wp_id: WP01\n"
        "---\n\nIndependent approval.\n",
        encoding="utf-8",
    )
    _git(caller, "add", ".")
    _git(caller, "commit", "-q", "-m", "test: record caller review")
    approval_ref = (
        f"review-cycle://{_MISSION_SLUG}/WP01-caller/review-cycle-1.md"
    )

    approved_result = runner.invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "approved",
            "--mission",
            _MISSION_ID,
            "--reviewer",
            "reviewer",
            "--approval-ref",
            approval_ref,
            "--note",
            "caller-owned lifecycle approved",
            "--no-auto-commit",
            "--json",
        ],
        catch_exceptions=False,
    )
    assert approved_result.exit_code == 0, approved_result.output
    assert reduce(read_events(mission_dir)).work_packages["WP01"]["lane"] == "approved"

    meta = json.loads((mission_dir / "meta.json").read_text(encoding="utf-8"))
    meta.update(
        {
            "mission_number": "001",
            "slug": _MISSION_SLUG,
            "friendly_name": "Caller Mission",
            "created_at": "2026-08-13T00:00:00Z",
        }
    )
    (mission_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n",
        encoding="utf-8",
    )
    (mission_dir / "contracts").mkdir(exist_ok=True)
    for required in ("src", "tests", "docs"):
        directory = caller / required
        directory.mkdir(exist_ok=True)
        (directory / ".gitkeep").write_text("", encoding="utf-8")

    from specify_cli.acceptance.matrix import (
        AcceptanceCriterion,
        AcceptanceMatrix,
        write_acceptance_matrix,
    )

    write_acceptance_matrix(
        mission_dir,
        AcceptanceMatrix(
            mission_slug=_MISSION_SLUG,
            criteria=[
                AcceptanceCriterion(
                    criterion_id="AC1",
                    description="caller lifecycle works",
                    proof_type="automated_test",
                    pass_fail="pass",
                )
            ],
        ),
    )
    _git(caller, "add", ".")
    _git(caller, "commit", "-q", "-m", "test: complete caller lifecycle")

    accept_app = typer.Typer()
    accept_app.command(name="accept")(accept_cmd.accept)
    accept_result = runner.invoke(
        accept_app,
        ["--mission", _MISSION_ID, "--no-commit", "--json"],
        catch_exceptions=False,
    )
    assert accept_result.exit_code == 0, accept_result.output
    assert len(operation_roots) == 13
    assert all(
        repository == repository_root.resolve() and anchor == caller.resolve()
        for repository, anchor in operation_roots
    )
    assert _primary_snapshot(repository_root) == before
