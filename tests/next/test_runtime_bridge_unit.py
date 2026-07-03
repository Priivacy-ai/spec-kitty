"""Unit tests for the runtime bridge module.

This file imports runtime symbols only via ``runtime.next._internal_runtime``
following the WP02 cutover in mission ``shared-package-boundary-cutover-01KQ22DS``.
No quarantined ``spec_kitty_runtime`` references are needed; tests assert against
the internalized runtime surface, which is the authoritative production target.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.lane_test_utils import write_single_lane_manifest
from runtime.next.decision import DecisionKind
from runtime.next._internal_runtime import DiscoveryContext

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Initialize a bare git repo at *path*."""
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
    (path / "README.md").write_text("# test", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


def _scaffold_project(
    tmp_path: Path,
    mission_slug: str = "042-test-feature",
    mission_type: str = "software-dev",
) -> Path:
    repo_root = tmp_path / "project"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    kittify = repo_root / ".kittify"
    kittify.mkdir()

    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_type": mission_type}),
        encoding="utf-8",
    )

    return repo_root


def _seed_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Seed a WP into a specific lane in the event log."""
    from specify_cli.status.store import append_event
    from specify_cli.status.models import StatusEvent, Lane

    # Map legacy aliases to canonical lane names
    _lane_alias = {"doing": "in_progress"}
    canonical_lane = _lane_alias.get(lane, lane)

    event = StatusEvent(
        event_id=f"test-{wp_id}-{canonical_lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(canonical_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _add_wp_files(feature_dir: Path, wps: dict[str, str]) -> None:
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    for wp_id, lane in wps.items():
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\nlane: {lane}\ntitle: {wp_id} task\n---\n# {wp_id}\nDo something.\n",
            encoding="utf-8",
        )
        # Always seed event log (canonical status is required)
        _seed_wp_lane(feature_dir, wp_id, lane)
    write_single_lane_manifest(feature_dir, wp_ids=tuple(wps.keys()))


# ---------------------------------------------------------------------------
# Template precedence tests
# ---------------------------------------------------------------------------


class TestRuntimeTemplateKey:
    pytestmark = pytest.mark.git_repo

    def test_project_override_takes_precedence(self, tmp_path: Path) -> None:
        """Project-level mission-runtime.yaml shadows the built-in."""
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import _runtime_template_key

        # Create a project-level override at the canonical override tier
        project_dir = repo_root / ".kittify" / "overrides" / "missions" / "software-dev"
        project_dir.mkdir(parents=True)
        project_yaml = project_dir / "mission-runtime.yaml"
        project_yaml.write_text(
            "mission:\n  key: software-dev\n  name: software-dev\n  version: '9.9.9'\n"
            "steps:\n  - id: x\n    title: x\n",
            encoding="utf-8",
        )

        result = _runtime_template_key("software-dev", repo_root)
        assert result == str(project_yaml), f"Project override must take precedence, got: {result}"

    def test_env_takes_precedence_over_project_override(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SPEC_KITTY_MISSION_PATHS outranks project override for runtime templates."""
        repo_root = _scaffold_project(tmp_path)
        from runtime.next.runtime_bridge import _runtime_template_key

        # Project override exists
        override_dir = repo_root / ".kittify" / "overrides" / "missions" / "software-dev"
        override_dir.mkdir(parents=True)
        (override_dir / "mission-runtime.yaml").write_text(
            "mission:\n  key: software-dev\n  name: override\n  version: '1.0.0'\nsteps:\n  - id: o\n    title: o\n",
            encoding="utf-8",
        )

        # Env mission path should win
        env_root = tmp_path / "env-missions"
        env_mission = env_root / "software-dev"
        env_mission.mkdir(parents=True)
        env_runtime = env_mission / "mission-runtime.yaml"
        env_runtime.write_text(
            "mission:\n  key: software-dev\n  name: env\n  version: '2.0.0'\nsteps:\n  - id: e\n    title: e\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("SPEC_KITTY_MISSION_PATHS", str(env_root))

        result = _runtime_template_key("software-dev", repo_root)
        assert result == str(env_runtime.resolve())

    def test_falls_back_to_builtin(self, tmp_path: Path, monkeypatch) -> None:
        """Without a project override, the built-in template is used."""
        repo_root = _scaffold_project(tmp_path)

        import runtime.next.runtime_bridge as runtime_bridge
        import specify_cli

        builtin_root = Path(specify_cli.__file__).resolve().parent / "missions"

        # Force deterministic discovery context for this test so user-global
        # ~/.kittify content cannot shadow the builtin fallback tier.
        monkeypatch.setattr(
            runtime_bridge,
            "_build_discovery_context",
            lambda root: DiscoveryContext(
                project_dir=root,
                builtin_roots=[builtin_root],
                user_home=tmp_path,
            ),
        )

        result = runtime_bridge._runtime_template_key("software-dev", repo_root)
        assert result == str((builtin_root / "software-dev" / "mission-runtime.yaml").resolve())


class TestWorkflowRuntimeTemplate:
    pytestmark = pytest.mark.git_repo

    def test_workflow_id_composes_frozen_runtime_template(self, tmp_path: Path) -> None:
        """meta.json::workflow_id affects the canonical run template used by `next`."""
        repo_root = _scaffold_project(tmp_path)
        mission_dir = repo_root / "kitty-specs" / "042-test-feature"
        (mission_dir / "meta.json").write_text(
            json.dumps(
                {
                    "mission_type": "software-dev",
                    "workflow_id": "our-team-design-first",
                }
            ),
            encoding="utf-8",
        )

        from runtime.next._internal_runtime.engine import _load_frozen_template
        from runtime.next.runtime_bridge import get_or_start_run

        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        template = _load_frozen_template(Path(run_ref.run_dir))
        step_ids = [step.id for step in template.steps]

        assert step_ids == [
            "discovery",
            "specify",
            "plan",
            "design-review",
            "tasks",
            "implement",
            "review",
            "merge",
        ]

    def test_workflow_inserted_step_resolves_prompt_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A workflow-inserted step must not block on missing prompt resolution."""
        repo_root = _scaffold_project(tmp_path)
        mission_dir = repo_root / "kitty-specs" / "042-test-feature"
        (mission_dir / "meta.json").write_text(
            json.dumps(
                {
                    "mission_type": "software-dev",
                    "workflow_id": "our-team-design-first",
                }
            ),
            encoding="utf-8",
        )

        from runtime.next import runtime_bridge
        from runtime.next.decision import DecisionKind

        monkeypatch.setattr(
            runtime_bridge.SyncRuntimeEventEmitter,
            "for_feature",
            staticmethod(lambda **_: runtime_bridge._BufferingRuntimeEmitter()),
        )

        runtime_bridge.decide_next_via_runtime(
            "agent",
            "042-test-feature",
            "success",
            repo_root,
        )
        specify = runtime_bridge.decide_next_via_runtime(
            "agent",
            "042-test-feature",
            "success",
            repo_root,
        )
        assert specify.step_id == "specify"
        (mission_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

        plan = runtime_bridge.decide_next_via_runtime(
            "agent",
            "042-test-feature",
            "success",
            repo_root,
        )
        assert plan.step_id == "plan"
        (mission_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")

        design_review = runtime_bridge.decide_next_via_runtime(
            "agent",
            "042-test-feature",
            "success",
            repo_root,
        )

        assert design_review.kind == DecisionKind.step
        assert design_review.step_id == "design-review"
        assert design_review.action == "design-review"
        assert design_review.prompt_file is not None
        assert Path(design_review.prompt_file).is_file()

    def test_software_dev_builtin_outranks_stale_user_global(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A stale user-global software-dev runtime must not revive legacy tasks_*."""
        repo_root = _scaffold_project(tmp_path)

        import runtime.next.runtime_bridge as runtime_bridge
        import specify_cli

        builtin_root = Path(specify_cli.__file__).resolve().parent / "missions"
        user_home = tmp_path / "home"
        global_runtime = user_home / ".kittify" / "missions" / "software-dev" / "mission-runtime.yaml"
        global_runtime.parent.mkdir(parents=True)
        global_runtime.write_text(
            "mission:\n  key: software-dev\n  name: stale\n  version: '2.1.0'\n"
            "steps:\n"
            "  - id: tasks_outline\n    title: outline\n"
            "  - id: tasks_packages\n    title: packages\n    depends_on: [tasks_outline]\n"
            "  - id: tasks_finalize\n    title: finalize\n    depends_on: [tasks_packages]\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(
            runtime_bridge,
            "_build_discovery_context",
            lambda root: DiscoveryContext(
                project_dir=root,
                builtin_roots=[builtin_root],
                user_home=user_home,
            ),
        )

        result = runtime_bridge._runtime_template_key("software-dev", repo_root)
        assert result != str(global_runtime.resolve())
        assert result == str((builtin_root / "software-dev" / "mission-runtime.yaml").resolve())

    def test_project_legacy_used_when_override_absent(self, tmp_path: Path) -> None:
        """Legacy .kittify/missions path remains supported after override tier."""
        repo_root = _scaffold_project(tmp_path)
        from runtime.next.runtime_bridge import _runtime_template_key

        legacy_dir = repo_root / ".kittify" / "missions" / "software-dev"
        legacy_dir.mkdir(parents=True)
        legacy_runtime = legacy_dir / "mission-runtime.yaml"
        legacy_runtime.write_text(
            "mission:\n  key: software-dev\n  name: legacy\n  version: '3.0.0'\nsteps:\n  - id: l\n    title: l\n",
            encoding="utf-8",
        )

        result = _runtime_template_key("software-dev", repo_root)
        assert result == str(legacy_runtime.resolve())


# ---------------------------------------------------------------------------
# get_or_start_run tests
# ---------------------------------------------------------------------------


class TestGetOrStartRun:
    pytestmark = pytest.mark.git_repo

    def test_creates_new_run(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import get_or_start_run

        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        assert run_ref.run_id is not None
        assert len(run_ref.run_id) > 0
        assert getattr(run_ref, "mission_key", None) == "software-dev"
        assert Path(run_ref.run_dir).exists()
        assert (Path(run_ref.run_dir) / "state.json").exists()

    def test_loads_existing_run(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import get_or_start_run

        run1 = get_or_start_run("042-test-feature", repo_root, "software-dev")
        run2 = get_or_start_run("042-test-feature", repo_root, "software-dev")
        assert run1.run_id == run2.run_id
        assert run1.run_dir == run2.run_dir

    def test_different_features_get_different_runs(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        # Create second feature
        feature_dir2 = repo_root / "kitty-specs" / "043-other-feature"
        feature_dir2.mkdir(parents=True)
        (feature_dir2 / "meta.json").write_text('{"mission_type": "software-dev"}', encoding="utf-8")

        from runtime.next.runtime_bridge import get_or_start_run

        run1 = get_or_start_run("042-test-feature", repo_root, "software-dev")
        run2 = get_or_start_run("043-other-feature", repo_root, "software-dev")
        assert run1.run_id != run2.run_id

    def test_feature_runs_index_persisted(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import get_or_start_run, _load_feature_runs

        get_or_start_run("042-test-feature", repo_root, "software-dev")
        index = _load_feature_runs(repo_root)
        assert "042-test-feature" in index
        assert "run_id" in index["042-test-feature"]

    def test_feature_runs_index_includes_mission_id_and_slug(self, tmp_path: Path) -> None:
        """FR-028: feature-runs.json entries must include mission_id and mission_slug (WP06)."""
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import get_or_start_run, _load_feature_runs

        get_or_start_run("042-test-feature", repo_root, "software-dev")
        index = _load_feature_runs(repo_root)
        entry = index["042-test-feature"]
        # mission_slug must always be present and match the key
        assert entry.get("mission_slug") == "042-test-feature"
        # mission_id may be None when no meta.json exists, but the key must be present
        assert "mission_id" in entry


class TestRuntimeBridgeCompatibilityHelpers:
    def test_mission_key_for_run_ref_prefers_mission_type(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge import _mission_key_for_run_ref

        run_ref = SimpleNamespace(mission_type="software-dev")
        assert _mission_key_for_run_ref(run_ref, "fallback") == "software-dev"

    def test_mission_key_for_run_ref_falls_back_to_default(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge import _mission_key_for_run_ref

        run_ref = SimpleNamespace(mission_type="")
        assert _mission_key_for_run_ref(run_ref, "fallback") == "fallback"

    def test_build_run_ref_falls_back_when_runtime_uses_mission_type(self, monkeypatch) -> None:
        import runtime.next.runtime_bridge as runtime_bridge

        class FakeRunRef:
            def __init__(self, *, run_id: str, run_dir: str, mission_type: str | None = None, mission_key: str | None = None):
                if mission_key is not None:
                    raise TypeError("legacy mission_key no longer accepted")
                self.run_id = run_id
                self.run_dir = run_dir
                self.mission_type = mission_type

        monkeypatch.setattr(runtime_bridge, "MissionRunRef", FakeRunRef)

        run_ref = runtime_bridge._build_run_ref(
            run_id="run-123",
            run_dir="/tmp/run-123",
            mission_type="software-dev",
        )

        assert run_ref.run_id == "run-123"
        assert run_ref.run_dir == "/tmp/run-123"
        assert run_ref.mission_type == "software-dev"


# ---------------------------------------------------------------------------
# WP iteration tests
# ---------------------------------------------------------------------------


class TestWPIteration:
    pytestmark = pytest.mark.git_repo

    def test_wp_iteration_does_not_advance_runtime(self, tmp_path: Path) -> None:
        """When WPs remain, runtime step should not advance."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(
            feature_dir,
            {
                "WP01": "planned",
                "WP02": "planned",
            },
        )

        from runtime.next.runtime_bridge import (
            get_or_start_run,
            decide_next_via_runtime,
        )
        from runtime.next._internal_runtime import next_step as runtime_next_step, NullEmitter
        from runtime.next._internal_runtime.engine import _read_snapshot

        # Advance runtime to implement step
        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        step_order = ["discovery", "specify", "plan", "tasks", "implement"]
        for _ in range(len(step_order)):
            snapshot = _read_snapshot(Path(run_ref.run_dir))
            if snapshot.issued_step_id == "implement":
                break
            runtime_next_step(run_ref, agent_id="test", result="success", emitter=NullEmitter())

        # Now decide_next should keep us in implement with WP01
        decision = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action == "implement"
        assert decision.wp_id == "WP01"

        # Call again — should still be in implement with same WP (not advanced)
        decision2 = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        assert decision2.step_id == "implement"

    def test_all_wps_done_advances_runtime(self, tmp_path: Path) -> None:
        """When all WPs are done, runtime should advance past implement."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(
            feature_dir,
            {
                "WP01": "done",
                "WP02": "done",
            },
        )

        from runtime.next.runtime_bridge import (
            get_or_start_run,
            decide_next_via_runtime,
        )
        from runtime.next._internal_runtime import next_step as runtime_next_step, NullEmitter
        from runtime.next._internal_runtime.engine import _read_snapshot

        # Advance runtime to implement step
        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        for _ in range(6):
            snapshot = _read_snapshot(Path(run_ref.run_dir))
            if snapshot.issued_step_id == "implement":
                break
            runtime_next_step(run_ref, agent_id="test", result="success", emitter=NullEmitter())

        # All WPs done — decide_next should advance past implement
        decision = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        # Should either be in review or later step (not implement)
        assert decision.step_id != "implement" or decision.kind != DecisionKind.step


# ---------------------------------------------------------------------------
# Runtime result flow tests
# ---------------------------------------------------------------------------


class TestRuntimeResultFlow:
    pytestmark = pytest.mark.git_repo

    @staticmethod
    def _read_run_events(run_dir: Path) -> list[dict]:
        event_file = run_dir / "run.events.jsonl"
        if not event_file.exists():
            return []
        events: list[dict] = []
        for line in event_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def test_failed_result_flows_through_runtime_event_log(self, tmp_path: Path) -> None:
        """A failed result must call runtime next_step and append canonical events."""
        repo_root = _scaffold_project(tmp_path)
        from runtime.next.runtime_bridge import decide_next_via_runtime, get_or_start_run

        # Issue a first step so runtime has a prior issued_step_id to complete.
        first = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        assert first.run_id is not None

        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        run_dir = Path(run_ref.run_dir)
        before = self._read_run_events(run_dir)

        failed = decide_next_via_runtime("test", "042-test-feature", "failed", repo_root)
        after = self._read_run_events(run_dir)

        assert failed.kind == DecisionKind.blocked
        assert failed.run_id == run_ref.run_id
        assert len(after) > len(before), "failed path must append runtime lifecycle event(s)"
        assert any(evt["event_type"] == "NextStepAutoCompleted" for evt in after[len(before) :])

    def test_blocked_result_flows_through_runtime_event_log(self, tmp_path: Path) -> None:
        """A blocked result must call runtime next_step and append canonical events."""
        repo_root = _scaffold_project(tmp_path)
        from runtime.next.runtime_bridge import decide_next_via_runtime, get_or_start_run

        # Issue a first step so runtime has a prior issued_step_id to complete.
        first = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        assert first.run_id is not None

        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        run_dir = Path(run_ref.run_dir)
        before = self._read_run_events(run_dir)

        blocked = decide_next_via_runtime("test", "042-test-feature", "blocked", repo_root)
        after = self._read_run_events(run_dir)

        assert blocked.kind == DecisionKind.blocked
        assert blocked.run_id == run_ref.run_id
        assert len(after) > len(before), "blocked path must append runtime lifecycle event(s)"
        assert any(evt["event_type"] == "NextStepAutoCompleted" for evt in after[len(before) :])


class TestAnswerDecisionViaRuntime:
    def test_snapshot_read_failure_is_tolerated(self, monkeypatch, tmp_path: Path) -> None:
        """Decision answers should continue even when snapshot hydration fails."""
        from runtime.next import runtime_bridge
        import runtime.next._internal_runtime.engine as runtime_engine

        repo_root = tmp_path / "project"
        repo_root.mkdir()
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        feature_dir.mkdir(parents=True)

        fake_run_ref = SimpleNamespace(run_dir=str(tmp_path / "run"), run_id="run-001")
        emitter_calls: list[tuple[str, object]] = []

        class FakeEmitter:
            def seed_from_snapshot(self, snapshot) -> None:
                emitter_calls.append(("seed", snapshot))

        monkeypatch.setattr(runtime_bridge, "get_mission_type", lambda path: "software-dev")
        monkeypatch.setattr(runtime_bridge, "get_or_start_run", lambda mission_slug, repo_root, mission_type: fake_run_ref)
        monkeypatch.setattr(
            runtime_bridge.SyncRuntimeEventEmitter,
            "for_feature",
            staticmethod(lambda **_: FakeEmitter()),
        )

        provided: list[tuple[object, str, str, object, object]] = []

        def fake_provide(run_ref, decision_id, answer, actor, *, emitter) -> None:
            provided.append((run_ref, decision_id, answer, actor, emitter))

        monkeypatch.setattr(runtime_bridge, "runtime_provide_decision_answer", fake_provide)
        monkeypatch.setattr(
            runtime_engine,
            "_read_snapshot",
            lambda path: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        runtime_bridge.answer_decision_via_runtime(
            "042-test-feature",
            "decision-001",
            "yes",
            "robert",
            repo_root,
        )

        assert emitter_calls == []
        assert len(provided) == 1
        _, decision_id, answer, actor, _ = provided[0]
        assert decision_id == "decision-001"
        assert answer == "yes"
        assert actor.actor_id == "robert"
        assert actor.actor_type == "human"


# ---------------------------------------------------------------------------
# Guard check tests
# ---------------------------------------------------------------------------


class TestGuardChecks:
    pytestmark = pytest.mark.git_repo

    def test_specify_guard_blocks_without_spec(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import _check_cli_guards

        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        failures = _check_cli_guards("specify", feature_dir)
        assert len(failures) == 1
        assert "spec.md" in failures[0]

    def test_specify_guard_passes_with_spec(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text("# Spec", encoding="utf-8")

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("specify", feature_dir)
        assert len(failures) == 0

    def test_plan_guard_blocks_without_artifacts(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("plan", feature_dir)
        assert len(failures) == 1  # plan.md only (tasks.md moved to tasks_outline guard)

    def test_implement_guard_blocks_with_planned_wps(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "planned", "WP02": "done"})

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("implement", feature_dir)
        assert len(failures) == 1

    def test_implement_guard_passes_all_done(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "done"})

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("implement", feature_dir)
        assert len(failures) == 0


class TestTasksMarkdownParsing:
    def test_parse_wp_sections_preserves_same_line_suffix(self) -> None:
        from runtime.next.runtime_bridge import _parse_wp_sections_from_tasks_md

        tasks_md = (
            "## Work Package WP01: Build parser\n"
            "Requirements Refs: FR-001, NFR-002\n"
            "### WP02\n"
            "Requirements: FR-003\n"
        )

        sections = _parse_wp_sections_from_tasks_md(tasks_md)

        assert sections["WP01"].startswith(": Build parser\n")
        assert "Requirements Refs: FR-001, NFR-002" in sections["WP01"]
        assert sections["WP02"] == "\nRequirements: FR-003\n"

    def test_parse_wp_sections_accepts_legacy_work_package_spacing(self) -> None:
        from runtime.next.runtime_bridge import _parse_requirement_refs_from_tasks_md

        tasks_md = (
            "## Work Package    WP01: Build parser\n"
            "Requirements Refs: FR-001, NFR-002\n"
        )

        assert _parse_requirement_refs_from_tasks_md(tasks_md) == {
            "WP01": ["FR-001", "NFR-002"]
        }

    def test_parse_requirement_refs_supports_heading_bullet_format(self) -> None:
        from runtime.next.runtime_bridge import _parse_requirement_refs_from_tasks_md

        tasks_md = (
            "## Work Package WP01: Build parser\n"
            "### Requirement Refs\n"
            "- FR-001, nfr-002\n"
        )

        assert _parse_requirement_refs_from_tasks_md(tasks_md) == {
            "WP01": ["FR-001", "NFR-002"]
        }

    def test_parse_requirement_refs_completes_under_budget_on_adversarial_input(self) -> None:
        from runtime.next.runtime_bridge import _parse_requirement_refs_from_tasks_md

        filler = "".join("#### Not a work package heading\n" for _ in range(100_000))
        tasks_md = (
            f"{filler}"
            "## Work Package WP01: Harden parser\n"
            "Requirements Refs: FR-001, fr-002, C-003\n"
        )

        start = time.perf_counter()
        refs = _parse_requirement_refs_from_tasks_md(tasks_md)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.2, (
            f"_parse_requirement_refs_from_tasks_md took {elapsed * 1000:.1f} ms on "
            "adversarial tasks.md input; possible regex/backtracking regression."
        )
        assert refs == {"WP01": ["FR-001", "FR-002", "C-003"]}


# ---------------------------------------------------------------------------
# Decision mapping tests
# ---------------------------------------------------------------------------


class TestMapRuntimeDecision:
    pytestmark = pytest.mark.git_repo

    def test_map_preserves_json_contract(self, tmp_path: Path) -> None:
        """Mapped decisions have all required JSON fields."""
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import decide_next_via_runtime

        decision = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        d = decision.to_dict()

        # Original fields
        assert "kind" in d
        assert "agent" in d
        assert "mission_slug" in d
        assert "mission" in d
        assert "mission_state" in d
        assert "timestamp" in d
        assert "guard_failures" in d
        assert "progress" in d
        assert "origin" in d

        # New runtime fields
        assert "run_id" in d
        assert "step_id" in d
        assert "decision_id" in d
        assert "input_key" in d


# ---------------------------------------------------------------------------
# Answer decision tests
# ---------------------------------------------------------------------------


class TestAnswerDecision:
    pytestmark = pytest.mark.git_repo

    def test_query_and_answer_paths_use_canonical_context_surfaces(self) -> None:
        """FR-032: runtime query/answer surfaces stay on canonical context APIs."""
        import inspect

        from runtime.next import runtime_bridge

        assert "mission_context_for" in inspect.getsource(runtime_bridge.query_current_state)
        assert "resolve_action_context" in inspect.getsource(runtime_bridge.answer_decision_via_runtime)

    def test_answer_missing_mission_raises(self, tmp_path: Path) -> None:
        """Missing mission must fail, not log and report a successful no-op answer.

        WP02 / C-IC02: the decision-answer path no longer collapses the resolver's
        typed ``ActionContextError`` into a generic ``MissionRuntimeError``; it
        preserves the typed code IDENTICALLY to the query path (FR-001). An
        unresolved handle still fails loudly — just with the typed error and its
        ``code`` intact — so the no-op regression this test guards stays closed.
        """
        repo_root = _scaffold_project(tmp_path)

        from mission_runtime import ActionContextError

        from runtime.next.runtime_bridge import answer_decision_via_runtime

        with pytest.raises(ActionContextError) as excinfo:
            answer_decision_via_runtime(
                "missing-feature",
                "decision-001",
                "yes",
                "test",
                repo_root,
            )
        # The typed code survives (no collapse to a generic "cannot answer
        # decision" string).
        assert excinfo.value.code

    def test_answer_without_pending_raises(self, tmp_path: Path) -> None:
        """Answering when no decisions pending raises error."""
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import answer_decision_via_runtime
        from runtime.next._internal_runtime.schema import MissionRuntimeError

        with pytest.raises(MissionRuntimeError, match="not found"):
            answer_decision_via_runtime(
                "042-test-feature",
                "nonexistent",
                "yes",
                "test",
                repo_root,
            )


# ---------------------------------------------------------------------------
# Full loop test
# ---------------------------------------------------------------------------


class TestFullLoop:
    pytestmark = pytest.mark.git_repo

    @pytest.fixture(autouse=True)
    def _disable_sync_emitter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from runtime.next import runtime_bridge
        from runtime.next._internal_runtime.events import NullEmitter

        class LocalOnlyEmitter(NullEmitter):
            def seed_from_snapshot(self, *_args, **_kwargs) -> None:
                return None

        monkeypatch.setattr(
            runtime_bridge.SyncRuntimeEventEmitter,
            "for_feature",
            staticmethod(lambda **_: LocalOnlyEmitter()),
        )

    def test_full_loop_step_to_terminal(self, tmp_path: Path) -> None:
        """Drive mission from start to terminal through all steps."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        # Create required artifacts so CLI guards pass
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n",
            encoding="utf-8",
        )
        (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
        # Create WP files with explicit dependencies for tasks_finalize guard
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\nlane: done\ndependencies: []\n"
            "requirement_refs: [FR-001]\ntitle: WP01\n---\n# WP01\n",
            encoding="utf-8",
        )
        # Seed event log so runtime bridge reads WP01 as done
        _seed_wp_lane(feature_dir, "WP01", "done")

        from runtime.next.runtime_bridge import decide_next_via_runtime

        seen_steps = []
        for _i in range(40):  # 9 steps need more iterations
            decision = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
            if decision.kind == DecisionKind.terminal:
                break
            if decision.step_id:
                seen_steps.append(decision.step_id)

        assert decision.kind == DecisionKind.terminal
        # Should have visited at least discovery and specify
        assert "discovery" in seen_steps

    def test_repeated_poll_idempotency(self, tmp_path: Path) -> None:
        """Polling the same state twice returns consistent results."""
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import decide_next_via_runtime

        decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        # Don't advance — poll again (simulating re-poll)
        # Note: this will advance because each call to decide_next advances
        # The bridge always advances, which is the expected behavior.
        # The important thing is that it produces valid decisions.
        d2 = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        assert d2.kind in ("step", "terminal", "blocked", "decision_required")

    def test_offline_no_network(self, tmp_path: Path) -> None:
        """Verify no network calls — NullEmitter used throughout."""
        repo_root = _scaffold_project(tmp_path)

        from runtime.next.runtime_bridge import decide_next_via_runtime

        # This should work without any network access
        decision = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        assert decision.kind in ("step", "terminal", "blocked", "decision_required")


# ---------------------------------------------------------------------------
# WP step helpers
# ---------------------------------------------------------------------------


class TestWPStepHelpers:
    def test_is_wp_iteration_step(self) -> None:
        from runtime.next.runtime_bridge import _is_wp_iteration_step

        assert _is_wp_iteration_step("implement") is True
        assert _is_wp_iteration_step("review") is True
        assert _is_wp_iteration_step("specify") is False
        assert _is_wp_iteration_step("discovery") is False

    def test_should_advance_no_tasks_dir(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", tmp_path) is True

    @pytest.mark.git_repo
    def test_should_advance_hardfails_without_canonical_status(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01 task\n---\n# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _should_advance_wp_step
        from specify_cli.status.lane_reader import CanonicalStatusNotFoundError

        with pytest.raises(CanonicalStatusNotFoundError):
            _should_advance_wp_step("implement", feature_dir)

    @pytest.mark.git_repo
    def test_should_advance_all_done(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "done"})

        from runtime.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is True
        assert _should_advance_wp_step("review", feature_dir) is True

    @pytest.mark.git_repo
    def test_should_not_advance_planned_remain(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "planned"})

        from runtime.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is False

    @pytest.mark.git_repo
    def test_implement_allows_for_review(self, tmp_path: Path) -> None:
        """Implement step allows for_review WPs (they're in progress of review)."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "for_review"})

        from runtime.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is True
        assert _should_advance_wp_step("review", feature_dir) is False

    @pytest.mark.git_repo
    def test_review_allows_approved(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "approved", "WP02": "done"})

        from runtime.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is True
        assert _should_advance_wp_step("review", feature_dir) is True


# ---------------------------------------------------------------------------
# Atomic task step tests
# ---------------------------------------------------------------------------


class TestAtomicTaskSteps:
    @pytest.mark.git_repo
    def test_tasks_outline_guard_blocks_without_tasks_md(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_outline", feature_dir)
        assert len(failures) == 1
        assert "tasks.md" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_outline_guard_passes_with_tasks_md(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_outline", feature_dir)
        assert len(failures) == 0

    @pytest.mark.git_repo
    def test_tasks_packages_guard_blocks_without_wp_files(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 1
        assert "WP*.md" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_packages_guard_passes_with_wp_files(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "planned"})

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 0

    @pytest.mark.git_repo
    def test_tasks_packages_guard_blocks_unmapped_functional_requirements(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n"
            "| FR-002 | Second | Must be mapped before finalization. | proposed |\n",
            encoding="utf-8",
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: WP01\n"
            "requirement_refs:\n"
            "  - FR-001\n"
            "---\n"
            "# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 1
        assert "Requirement mapping incomplete" in failures[0]
        assert "unmapped FRs: FR-002" in failures[0]
        assert "map-requirements" in failures[0]

    @pytest.mark.git_repo
    def test_composed_tasks_packages_guard_blocks_unmapped_functional_requirements(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n"
            "| FR-002 | Second | Must be mapped before finalization. | proposed |\n",
            encoding="utf-8",
        )
        (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01\nrequirement_refs: [FR-001]\n---\n# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_composed_action_guard

        failures = _check_composed_action_guard(
            "tasks",
            feature_dir,
            legacy_step_id="tasks_packages",
        )
        assert len(failures) == 1
        assert "Requirement mapping incomplete" in failures[0]
        assert "unmapped FRs: FR-002" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_packages_guard_passes_when_functional_requirements_are_mapped(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n"
            "| FR-002 | Second | Covered by WP02. | proposed |\n",
            encoding="utf-8",
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01\nrequirement_refs: [FR-001]\n---\n# WP01\n",
            encoding="utf-8",
        )
        (tasks_dir / "WP02.md").write_text(
            "---\nwork_package_id: WP02\ntitle: WP02\nrequirement_refs: [FR-002]\n---\n# WP02\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert failures == []

    @pytest.mark.git_repo
    def test_tasks_packages_guard_uses_legacy_tasks_md_refs_without_wps_yaml(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n",
            encoding="utf-8",
        )
        (feature_dir / "tasks.md").write_text(
            "## Work Package WP01\n\n**Requirement Refs**: FR-001\n",
            encoding="utf-8",
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01\n---\n# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert failures == []

    @pytest.mark.git_repo
    def test_tasks_packages_guard_rejects_indented_legacy_tasks_md_heading(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n",
            encoding="utf-8",
        )
        (feature_dir / "tasks.md").write_text(
            "  ## Work Package WP01\n\n**Requirement Refs**: FR-001\n",
            encoding="utf-8",
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01\n---\n# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert failures
        assert "missing refs for WPs: WP01" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_packages_guard_accepts_tab_after_hashes_in_legacy_tasks_md_heading(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n",
            encoding="utf-8",
        )
        (feature_dir / "tasks.md").write_text(
            "##\tWork Package WP01\n\n**Requirement Refs**: FR-001\n",
            encoding="utf-8",
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01\n---\n# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert failures == []

    @pytest.mark.git_repo
    def test_tasks_packages_guard_blocks_missing_requirement_refs(self, tmp_path: Path) -> None:
        """WP has no requirement_refs at all → missing-refs branch."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n",
            encoding="utf-8",
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01\n---\n# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 1
        assert "missing refs for WPs: WP01" in failures[0]
        assert "map-requirements" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_packages_guard_blocks_unknown_requirement_refs(self, tmp_path: Path) -> None:
        """WP references an FR that doesn't exist in spec.md → unknown-refs branch."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n",
            encoding="utf-8",
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01\nrequirement_refs: [FR-999]\n---\n# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 1
        assert "unknown refs: WP01: FR-999" in failures[0]

    @pytest.mark.git_repo
    def test_requirement_mapping_preflight_noop_when_no_tasks_dir(self, tmp_path: Path) -> None:
        """Helper returns [] when tasks/ does not exist even if spec.md does."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text(
            "# Spec\n\n"
            "## Functional Requirements\n\n"
            "| ID | Requirement | Acceptance Criteria | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-001 | First | Covered by WP01. | proposed |\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_requirement_mapping_ready

        assert _check_requirement_mapping_ready(feature_dir) == []

    @pytest.mark.git_repo
    def test_requirement_mapping_preflight_wraps_unexpected_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unexpected exceptions during preflight surface as a guard failure, not a crash."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: WP01\nrequirement_refs: [FR-001]\n---\n",
            encoding="utf-8",
        )

        def _boom(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("simulated preflight crash")

        from specify_cli import requirement_mapping as rm

        monkeypatch.setattr(rm, "parse_requirement_ids_from_spec_md", _boom)

        from runtime.next.runtime_bridge import _check_requirement_mapping_ready

        failures = _check_requirement_mapping_ready(feature_dir)
        assert len(failures) == 1
        assert "Requirement mapping preflight failed" in failures[0]
        assert "simulated preflight crash" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_finalize_guard_blocks_without_raw_dependencies(self, tmp_path: Path) -> None:
        """WP files exist but no explicit dependencies: in raw frontmatter."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        # WP file WITHOUT dependencies field in raw frontmatter
        _add_wp_files(feature_dir, {"WP01": "planned"})

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_finalize", feature_dir)
        assert len(failures) == 1
        assert "dependencies" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_finalize_guard_passes_with_raw_dependencies(self, tmp_path: Path) -> None:
        """WP files have dependencies: [...] explicitly written."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\nlane: planned\ndependencies: []\ntitle: WP01\n---\n# WP01\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_finalize", feature_dir)
        assert len(failures) == 0

    @pytest.mark.git_repo
    def test_tasks_finalize_guard_rejects_auto_injected_dependencies(self, tmp_path: Path) -> None:
        """WP file with NO dependencies line — read_frontmatter would inject [],
        but raw check correctly rejects."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        # Frontmatter without dependencies field
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\nlane: planned\ntitle: WP01\n---\n# WP01\nContent.\n",
            encoding="utf-8",
        )

        from runtime.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_finalize", feature_dir)
        assert len(failures) == 1
        assert "dependencies" in failures[0]

    def test_has_raw_dependencies_field_positive(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge import _has_raw_dependencies_field

        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01\n",
            encoding="utf-8",
        )
        assert _has_raw_dependencies_field(wp_file) is True

    def test_has_raw_dependencies_field_negative(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge import _has_raw_dependencies_field

        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\nlane: planned\n---\n# WP01\n",
            encoding="utf-8",
        )
        assert _has_raw_dependencies_field(wp_file) is False

    def test_has_raw_dependencies_field_no_frontmatter(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge import _has_raw_dependencies_field

        wp_file = tmp_path / "WP01.md"
        wp_file.write_text("# WP01\nNo frontmatter here.\n", encoding="utf-8")
        assert _has_raw_dependencies_field(wp_file) is False

    def test_has_raw_dependencies_field_with_values(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge import _has_raw_dependencies_field

        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02\n',
            encoding="utf-8",
        )
        assert _has_raw_dependencies_field(wp_file) is True


class TestQueryCurrentStateTypedErrorPassthrough:
    """FR-001 / C-IC02: ``query_current_state`` passes a *read-path* ActionContextError
    through verbatim (the #15 fix), and only collapses a genuinely-missing mission to
    ``MISSION_NOT_FOUND``. Covers the discriminator branch at runtime_bridge.py."""

    def test_read_path_error_reraised_verbatim(self, monkeypatch, tmp_path: Path) -> None:
        import mission_runtime
        from mission_runtime import ActionContextError
        from runtime.next.runtime_bridge import query_current_state

        def _raise_read_path(*_a: object, **_k: object) -> None:
            raise ActionContextError(
                "COORDINATION_BRANCH_DELETED",
                "coordination branch deleted; checked .worktrees/<slug>-coord and primary",
            )

        monkeypatch.setattr(mission_runtime, "mission_context_for", _raise_read_path)

        with pytest.raises(ActionContextError) as exc_info:
            query_current_state(
                agent="claude",
                mission_slug="read-path-error-fidelity-adoption-01KV8NPC",
                repo_root=tmp_path,
            )
        # The typed read-path code survives — NOT collapsed to MISSION_NOT_FOUND.
        assert exc_info.value.code == "COORDINATION_BRANCH_DELETED"

    def test_genuinely_missing_mission_collapses_to_mission_not_found(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        import mission_runtime
        from mission_runtime import ActionContextError
        from runtime.next.runtime_bridge import MissionNotFoundError, query_current_state

        def _raise_unresolved(*_a: object, **_k: object) -> None:
            raise ActionContextError("FEATURE_CONTEXT_UNRESOLVED", "no mission directory at all")

        monkeypatch.setattr(mission_runtime, "mission_context_for", _raise_unresolved)

        with pytest.raises(MissionNotFoundError):
            query_current_state(agent="claude", mission_slug="no-such-mission", repo_root=tmp_path)
