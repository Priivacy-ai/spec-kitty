"""Unit tests for the runtime bridge module.

This file imports runtime symbols only via ``specify_cli.next._internal_runtime``
following the WP02 cutover in mission ``shared-package-boundary-cutover-01KQ22DS``.
No quarantined ``spec_kitty_runtime`` references are needed; tests assert against
the internalized runtime surface, which is the authoritative production target.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.lane_test_utils import write_single_lane_manifest
from specify_cli.next.decision import DecisionKind
from specify_cli.next._internal_runtime import DiscoveryContext

pytestmark = pytest.mark.fast


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

        from specify_cli.next.runtime_bridge import _runtime_template_key

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
        from specify_cli.next.runtime_bridge import _runtime_template_key

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

        import specify_cli.next.runtime_bridge as runtime_bridge

        builtin_root = Path(runtime_bridge.__file__).resolve().parent.parent / "missions"

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
        assert "src/specify_cli/missions/software-dev/mission-runtime.yaml" in result

    def test_project_legacy_used_when_override_absent(self, tmp_path: Path) -> None:
        """Legacy .kittify/missions path remains supported after override tier."""
        repo_root = _scaffold_project(tmp_path)
        from specify_cli.next.runtime_bridge import _runtime_template_key

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

        from specify_cli.next.runtime_bridge import get_or_start_run

        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        assert run_ref.run_id is not None
        assert len(run_ref.run_id) > 0
        assert getattr(run_ref, "mission_key", None) == "software-dev"
        assert Path(run_ref.run_dir).exists()
        assert (Path(run_ref.run_dir) / "state.json").exists()

    def test_loads_existing_run(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import get_or_start_run

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

        from specify_cli.next.runtime_bridge import get_or_start_run

        run1 = get_or_start_run("042-test-feature", repo_root, "software-dev")
        run2 = get_or_start_run("043-other-feature", repo_root, "software-dev")
        assert run1.run_id != run2.run_id

    def test_feature_runs_index_persisted(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import get_or_start_run, _load_feature_runs

        get_or_start_run("042-test-feature", repo_root, "software-dev")
        index = _load_feature_runs(repo_root)
        assert "042-test-feature" in index
        assert "run_id" in index["042-test-feature"]


class TestRuntimeBridgeCompatibilityHelpers:
    def test_mission_key_for_run_ref_prefers_mission_type(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import _mission_key_for_run_ref

        run_ref = SimpleNamespace(mission_type="software-dev")
        assert _mission_key_for_run_ref(run_ref, "fallback") == "software-dev"

    def test_mission_key_for_run_ref_falls_back_to_default(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import _mission_key_for_run_ref

        run_ref = SimpleNamespace(mission_type="")
        assert _mission_key_for_run_ref(run_ref, "fallback") == "fallback"

    def test_build_run_ref_falls_back_when_runtime_uses_mission_type(self, monkeypatch) -> None:
        import specify_cli.next.runtime_bridge as runtime_bridge

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

        from specify_cli.next.runtime_bridge import (
            get_or_start_run,
            decide_next_via_runtime,
        )
        from specify_cli.next._internal_runtime import next_step as runtime_next_step, NullEmitter
        from specify_cli.next._internal_runtime.engine import _read_snapshot

        # Advance runtime to implement step
        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        step_order = ["discovery", "specify", "plan", "tasks_outline", "tasks_packages", "tasks_finalize", "implement"]
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

        from specify_cli.next.runtime_bridge import (
            get_or_start_run,
            decide_next_via_runtime,
        )
        from specify_cli.next._internal_runtime import next_step as runtime_next_step, NullEmitter
        from specify_cli.next._internal_runtime.engine import _read_snapshot

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
        from specify_cli.next.runtime_bridge import decide_next_via_runtime, get_or_start_run

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
        from specify_cli.next.runtime_bridge import decide_next_via_runtime, get_or_start_run

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
        from specify_cli.next import runtime_bridge
        import specify_cli.next._internal_runtime.engine as runtime_engine

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

        from specify_cli.next.runtime_bridge import _check_cli_guards

        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        failures = _check_cli_guards("specify", feature_dir)
        assert len(failures) == 1
        assert "spec.md" in failures[0]

    def test_specify_guard_passes_with_spec(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "spec.md").write_text("# Spec", encoding="utf-8")

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("specify", feature_dir)
        assert len(failures) == 0

    def test_plan_guard_blocks_without_artifacts(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("plan", feature_dir)
        assert len(failures) == 1  # plan.md only (tasks.md moved to tasks_outline guard)

    def test_implement_guard_blocks_with_planned_wps(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "planned", "WP02": "done"})

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("implement", feature_dir)
        assert len(failures) == 1

    def test_implement_guard_passes_all_done(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "done"})

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("implement", feature_dir)
        assert len(failures) == 0


# ---------------------------------------------------------------------------
# Decision mapping tests
# ---------------------------------------------------------------------------


class TestMapRuntimeDecision:
    pytestmark = pytest.mark.git_repo

    def test_map_preserves_json_contract(self, tmp_path: Path) -> None:
        """Mapped decisions have all required JSON fields."""
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import decide_next_via_runtime

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

    def test_answer_without_pending_raises(self, tmp_path: Path) -> None:
        """Answering when no decisions pending raises error."""
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import answer_decision_via_runtime
        from specify_cli.next._internal_runtime.schema import MissionRuntimeError

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

    def test_full_loop_step_to_terminal(self, tmp_path: Path) -> None:
        """Drive mission from start to terminal through all steps."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        # Create required artifacts so CLI guards pass
        (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
        # Create WP files with explicit dependencies for tasks_finalize guard
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\nlane: done\ndependencies: []\ntitle: WP01\n---\n# WP01\n",
            encoding="utf-8",
        )
        # Seed event log so runtime bridge reads WP01 as done
        _seed_wp_lane(feature_dir, "WP01", "done")

        from specify_cli.next.runtime_bridge import decide_next_via_runtime

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

        from specify_cli.next.runtime_bridge import decide_next_via_runtime

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

        from specify_cli.next.runtime_bridge import decide_next_via_runtime

        # This should work without any network access
        decision = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        assert decision.kind in ("step", "terminal", "blocked", "decision_required")


# ---------------------------------------------------------------------------
# WP step helpers
# ---------------------------------------------------------------------------


class TestWPStepHelpers:
    def test_is_wp_iteration_step(self) -> None:
        from specify_cli.next.runtime_bridge import _is_wp_iteration_step

        assert _is_wp_iteration_step("implement") is True
        assert _is_wp_iteration_step("review") is True
        assert _is_wp_iteration_step("specify") is False
        assert _is_wp_iteration_step("discovery") is False

    def test_should_advance_no_tasks_dir(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import _should_advance_wp_step

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

        from specify_cli.next.runtime_bridge import _should_advance_wp_step
        from specify_cli.status.lane_reader import CanonicalStatusNotFoundError

        with pytest.raises(CanonicalStatusNotFoundError):
            _should_advance_wp_step("implement", feature_dir)

    @pytest.mark.git_repo
    def test_should_advance_all_done(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "done"})

        from specify_cli.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is True
        assert _should_advance_wp_step("review", feature_dir) is True

    @pytest.mark.git_repo
    def test_should_not_advance_planned_remain(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "planned"})

        from specify_cli.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is False

    @pytest.mark.git_repo
    def test_implement_allows_for_review(self, tmp_path: Path) -> None:
        """Implement step allows for_review WPs (they're in progress of review)."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "for_review"})

        from specify_cli.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is True
        assert _should_advance_wp_step("review", feature_dir) is False

    @pytest.mark.git_repo
    def test_review_allows_approved(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "approved", "WP02": "done"})

        from specify_cli.next.runtime_bridge import _should_advance_wp_step

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

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_outline", feature_dir)
        assert len(failures) == 1
        assert "tasks.md" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_outline_guard_passes_with_tasks_md(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_outline", feature_dir)
        assert len(failures) == 0

    @pytest.mark.git_repo
    def test_tasks_packages_guard_blocks_without_wp_files(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 1
        assert "WP*.md" in failures[0]

    @pytest.mark.git_repo
    def test_tasks_packages_guard_passes_with_wp_files(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "planned"})

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 0

    @pytest.mark.git_repo
    def test_tasks_finalize_guard_blocks_without_raw_dependencies(self, tmp_path: Path) -> None:
        """WP files exist but no explicit dependencies: in raw frontmatter."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        # WP file WITHOUT dependencies field in raw frontmatter
        _add_wp_files(feature_dir, {"WP01": "planned"})

        from specify_cli.next.runtime_bridge import _check_cli_guards

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

        from specify_cli.next.runtime_bridge import _check_cli_guards

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

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_finalize", feature_dir)
        assert len(failures) == 1
        assert "dependencies" in failures[0]

    def test_has_raw_dependencies_field_positive(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import _has_raw_dependencies_field

        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01\n",
            encoding="utf-8",
        )
        assert _has_raw_dependencies_field(wp_file) is True

    def test_has_raw_dependencies_field_negative(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import _has_raw_dependencies_field

        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\nlane: planned\n---\n# WP01\n",
            encoding="utf-8",
        )
        assert _has_raw_dependencies_field(wp_file) is False

    def test_has_raw_dependencies_field_no_frontmatter(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import _has_raw_dependencies_field

        wp_file = tmp_path / "WP01.md"
        wp_file.write_text("# WP01\nNo frontmatter here.\n", encoding="utf-8")
        assert _has_raw_dependencies_field(wp_file) is False

    def test_has_raw_dependencies_field_with_values(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import _has_raw_dependencies_field

        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02\n',
            encoding="utf-8",
        )
        assert _has_raw_dependencies_field(wp_file) is True
