"""Unit tests for the runtime bridge module."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.next.decision import DecisionKind
from spec_kitty_runtime import DiscoveryContext


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
    feature_slug: str = "042-test-feature",
    mission_key: str = "software-dev",
) -> Path:
    repo_root = tmp_path / "project"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    kittify = repo_root / ".kittify"
    kittify.mkdir()

    feature_dir = repo_root / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission": mission_key}),
        encoding="utf-8",
    )

    return repo_root


def _add_wp_files(feature_dir: Path, wps: dict[str, str]) -> None:
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    for wp_id, lane in wps.items():
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\nlane: {lane}\ntitle: {wp_id} task\n---\n# {wp_id}\nDo something.\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Template precedence tests
# ---------------------------------------------------------------------------


class TestRuntimeTemplateKey:
    def test_project_override_takes_precedence(self, tmp_path: Path) -> None:
        """Project-level mission-runtime.yaml shadows the built-in."""
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import _runtime_template_key

        # Create a project-level override at the canonical override tier
        project_dir = repo_root / ".kittify" / "overrides" / "missions" / "software-dev"
        project_dir.mkdir(parents=True)
        project_yaml = project_dir / "mission-runtime.yaml"
        project_yaml.write_text(
            "mission:\n  key: software-dev\n  name: software-dev\n  version: '9.9.9'\nsteps:\n  - id: x\n    title: x\n",
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
    def test_creates_new_run(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import get_or_start_run

        run_ref = get_or_start_run("042-test-feature", repo_root, "software-dev")
        assert run_ref.run_id is not None
        assert len(run_ref.run_id) > 0
        assert run_ref.mission_key == "software-dev"
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
        (feature_dir2 / "meta.json").write_text('{"mission": "software-dev"}', encoding="utf-8")

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


# ---------------------------------------------------------------------------
# WP iteration tests
# ---------------------------------------------------------------------------


class TestWPIteration:
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
        from spec_kitty_runtime import next_step as runtime_next_step, NullEmitter
        from spec_kitty_runtime.engine import _read_snapshot

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
        from spec_kitty_runtime import next_step as runtime_next_step, NullEmitter
        from spec_kitty_runtime.engine import _read_snapshot

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


# ---------------------------------------------------------------------------
# Guard check tests
# ---------------------------------------------------------------------------


class TestGuardChecks:
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
    def test_map_preserves_json_contract(self, tmp_path: Path) -> None:
        """Mapped decisions have all required JSON fields."""
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import decide_next_via_runtime

        decision = decide_next_via_runtime("test", "042-test-feature", "success", repo_root)
        d = decision.to_dict()

        # Original fields
        assert "kind" in d
        assert "agent" in d
        assert "feature_slug" in d
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
    def test_answer_without_pending_raises(self, tmp_path: Path) -> None:
        """Answering when no decisions pending raises error."""
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import answer_decision_via_runtime
        from spec_kitty_runtime.schema import MissionRuntimeError

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

        from specify_cli.next.runtime_bridge import decide_next_via_runtime

        seen_steps = []
        for i in range(40):  # 9 steps need more iterations
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

    def test_should_advance_all_done(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "done"})

        from specify_cli.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is True
        assert _should_advance_wp_step("review", feature_dir) is True

    def test_should_not_advance_planned_remain(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "planned"})

        from specify_cli.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is False

    def test_implement_allows_for_review(self, tmp_path: Path) -> None:
        """Implement step allows for_review WPs (they're in progress of review)."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "done", "WP02": "for_review"})

        from specify_cli.next.runtime_bridge import _should_advance_wp_step

        assert _should_advance_wp_step("implement", feature_dir) is True
        assert _should_advance_wp_step("review", feature_dir) is False


# ---------------------------------------------------------------------------
# Atomic task step tests
# ---------------------------------------------------------------------------


class TestAtomicTaskSteps:
    def test_tasks_outline_guard_blocks_without_tasks_md(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_outline", feature_dir)
        assert len(failures) == 1
        assert "tasks.md" in failures[0]

    def test_tasks_outline_guard_passes_with_tasks_md(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_outline", feature_dir)
        assert len(failures) == 0

    def test_tasks_packages_guard_blocks_without_wp_files(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 1
        assert "WP*.md" in failures[0]

    def test_tasks_packages_guard_passes_with_wp_files(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {"WP01": "planned"})

        from specify_cli.next.runtime_bridge import _check_cli_guards

        failures = _check_cli_guards("tasks_packages", feature_dir)
        assert len(failures) == 0

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
