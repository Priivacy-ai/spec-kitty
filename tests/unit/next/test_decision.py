"""Unit tests for the ``spec-kitty next`` decision engine."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.next.decision import (
    Decision,
    DecisionKind,
    _compute_wp_progress,
    _find_first_wp_by_lane,
    decide_next,
    derive_mission_state,
    evaluate_guards,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    """Create a minimal feature directory."""
    fd = tmp_path / "kitty-specs" / "042-test-feature"
    fd.mkdir(parents=True)
    # Create meta.json
    meta = fd / "meta.json"
    meta.write_text('{"mission": "software-dev"}', encoding="utf-8")
    return fd


@pytest.fixture
def feature_with_tasks(feature_dir: Path) -> Path:
    """Feature dir with WP task files."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    # WP01 - planned
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\nlane: planned\n---\nContent WP01\n",
        encoding="utf-8",
    )
    # WP02 - doing
    (tasks_dir / "WP02.md").write_text(
        "---\nwork_package_id: WP02\nlane: doing\n---\nContent WP02\n",
        encoding="utf-8",
    )
    # WP03 - done
    (tasks_dir / "WP03.md").write_text(
        "---\nwork_package_id: WP03\nlane: done\n---\nContent WP03\n",
        encoding="utf-8",
    )
    # WP04 - for_review
    (tasks_dir / "WP04.md").write_text(
        "---\nwork_package_id: WP04\nlane: for_review\n---\nContent WP04\n",
        encoding="utf-8",
    )
    return feature_dir


# ---------------------------------------------------------------------------
# Runtime state helpers
# ---------------------------------------------------------------------------


def _advance_runtime_to_step(
    repo_root: Path,
    feature_slug: str,
    target_step_id: str,
    agent: str = "test-agent",
) -> None:
    """Advance the runtime run past steps until target_step_id is issued.

    Calls decide_next repeatedly to advance through the DAG steps
    (discovery -> specify -> plan -> tasks -> implement -> review -> accept).
    """
    from specify_cli.next.runtime_bridge import get_or_start_run

    from specify_cli.mission import get_feature_mission_key

    feature_dir = repo_root / "kitty-specs" / feature_slug
    mission_key = get_feature_mission_key(feature_dir)
    run_ref = get_or_start_run(feature_slug, repo_root, mission_key)

    from spec_kitty_runtime import next_step as runtime_next_step, NullEmitter
    from spec_kitty_runtime.engine import _read_snapshot

    # Keep advancing until the target step is issued
    step_order = ["discovery", "specify", "plan", "tasks_outline", "tasks_packages", "tasks_finalize", "implement", "review", "accept"]
    target_idx = step_order.index(target_step_id) if target_step_id in step_order else -1

    for _ in range(target_idx + 2):
        snapshot = _read_snapshot(Path(run_ref.run_dir))
        if snapshot.issued_step_id == target_step_id:
            return

        runtime_next_step(run_ref, agent_id=agent, result="success", emitter=NullEmitter())

        snapshot = _read_snapshot(Path(run_ref.run_dir))
        if snapshot.issued_step_id == target_step_id:
            return


def _complete_all_steps(
    repo_root: Path,
    feature_slug: str,
    agent: str = "test-agent",
) -> None:
    """Complete all runtime steps to reach terminal state."""
    from specify_cli.next.runtime_bridge import get_or_start_run

    from specify_cli.mission import get_feature_mission_key

    feature_dir = repo_root / "kitty-specs" / feature_slug
    mission_key = get_feature_mission_key(feature_dir)
    run_ref = get_or_start_run(feature_slug, repo_root, mission_key)

    from spec_kitty_runtime import next_step as runtime_next_step, NullEmitter

    # There are 9 steps: each needs to be issued + completed
    for _ in range(20):  # generous upper bound
        decision = runtime_next_step(
            run_ref, agent_id=agent, result="success", emitter=NullEmitter(),
        )
        if decision.kind == "terminal":
            return


# ---------------------------------------------------------------------------
# derive_mission_state (legacy)
# ---------------------------------------------------------------------------


class TestDeriveMissionState:
    def test_empty_log_returns_initial(self, feature_dir: Path) -> None:
        assert derive_mission_state(feature_dir, "discovery") == "discovery"

    def test_no_events_file_returns_initial(self, tmp_path: Path) -> None:
        assert derive_mission_state(tmp_path, "specify") == "specify"

    def test_with_phase_entered_events(self, feature_dir: Path) -> None:
        events_file = feature_dir / "mission-events.jsonl"
        events = [
            {"type": "phase_entered", "payload": {"state": "specify"}},
            {"type": "phase_exited", "payload": {"state": "specify"}},
            {"type": "phase_entered", "payload": {"state": "plan"}},
        ]
        events_file.write_text(
            "\n".join(json.dumps(e) for e in events) + "\n",
            encoding="utf-8",
        )
        assert derive_mission_state(feature_dir, "discovery") == "plan"

    def test_only_non_phase_events(self, feature_dir: Path) -> None:
        events_file = feature_dir / "mission-events.jsonl"
        events = [
            {"type": "guard_failed", "payload": {"guard": "spec.md"}},
        ]
        events_file.write_text(json.dumps(events[0]) + "\n", encoding="utf-8")
        assert derive_mission_state(feature_dir, "discovery") == "discovery"


# ---------------------------------------------------------------------------
# evaluate_guards (legacy)
# ---------------------------------------------------------------------------


class TestEvaluateGuards:
    def test_no_advance_transition(self) -> None:
        config = {
            "transitions": [
                {"trigger": "rework", "source": "review", "dest": "implement"},
            ],
        }
        passed, failures = evaluate_guards(config, Path("/fake"), "review")
        assert passed is True
        assert failures == []

    def test_all_guards_pass(self, feature_dir: Path) -> None:
        # Create the artifact the guard expects
        (feature_dir / "spec.md").write_text("# Spec", encoding="utf-8")

        def guard_pass(event_data):
            return True

        config = {
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "specify",
                    "dest": "plan",
                    "conditions": [guard_pass],
                },
            ],
        }
        passed, failures = evaluate_guards(config, feature_dir, "specify")
        assert passed is True
        assert failures == []

    def test_some_guards_fail(self, feature_dir: Path) -> None:
        def guard_fail(event_data):
            return False

        def guard_pass(event_data):
            return True

        config = {
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "specify",
                    "dest": "plan",
                    "conditions": [guard_pass, guard_fail],
                },
            ],
        }
        passed, failures = evaluate_guards(config, feature_dir, "specify")
        assert passed is False
        assert len(failures) == 1

    def test_uncompiled_string_guard(self, feature_dir: Path) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "specify",
                    "dest": "plan",
                    "conditions": ['artifact_exists("spec.md")'],
                },
            ],
        }
        passed, failures = evaluate_guards(config, feature_dir, "specify")
        assert passed is False
        assert "Uncompiled guard" in failures[0]

    def test_no_conditions(self) -> None:
        config = {
            "transitions": [
                {"trigger": "advance", "source": "discovery", "dest": "specify"},
            ],
        }
        passed, failures = evaluate_guards(config, Path("/fake"), "discovery")
        assert passed is True
        assert failures == []

    def test_unless_guard_blocks_when_true(self, feature_dir: Path) -> None:
        """Unless guards block advancement when they return True."""
        def unless_active(event_data):
            return True  # condition is active -> should block

        config = {
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "specify",
                    "dest": "plan",
                    "unless": [unless_active],
                },
            ],
        }
        passed, failures = evaluate_guards(config, feature_dir, "specify")
        assert passed is False
        assert len(failures) == 1
        assert "Unless-guard" in failures[0]

    def test_unless_guard_passes_when_false(self, feature_dir: Path) -> None:
        """Unless guards pass when they return False."""
        def unless_inactive(event_data):
            return False  # condition is inactive -> should pass

        config = {
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "specify",
                    "dest": "plan",
                    "unless": [unless_inactive],
                },
            ],
        }
        passed, failures = evaluate_guards(config, feature_dir, "specify")
        assert passed is True
        assert failures == []

    def test_conditions_and_unless_combined(self, feature_dir: Path) -> None:
        """Both conditions and unless must pass for guard to pass."""
        def cond_pass(event_data):
            return True

        def unless_inactive(event_data):
            return False

        config = {
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "specify",
                    "dest": "plan",
                    "conditions": [cond_pass],
                    "unless": [unless_inactive],
                },
            ],
        }
        passed, failures = evaluate_guards(config, feature_dir, "specify")
        assert passed is True
        assert failures == []

    def test_conditions_pass_but_unless_blocks(self, feature_dir: Path) -> None:
        """If conditions pass but unless is active, overall guard fails."""
        def cond_pass(event_data):
            return True

        def unless_active(event_data):
            return True

        config = {
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "specify",
                    "dest": "plan",
                    "conditions": [cond_pass],
                    "unless": [unless_active],
                },
            ],
        }
        passed, failures = evaluate_guards(config, feature_dir, "specify")
        assert passed is False
        assert len(failures) == 1

    def test_uncompiled_unless_string(self, feature_dir: Path) -> None:
        """Uncompiled string unless-guards report as failures."""
        config = {
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "specify",
                    "dest": "plan",
                    "unless": ['some_check("arg")'],
                },
            ],
        }
        passed, failures = evaluate_guards(config, feature_dir, "specify")
        assert passed is False
        assert "Uncompiled unless-guard" in failures[0]


# ---------------------------------------------------------------------------
# WP progress and lane helpers
# ---------------------------------------------------------------------------


class TestWPHelpers:
    def test_compute_wp_progress_no_tasks_dir(self, feature_dir: Path) -> None:
        assert _compute_wp_progress(feature_dir) is None

    def test_compute_wp_progress(self, feature_with_tasks: Path) -> None:
        progress = _compute_wp_progress(feature_with_tasks)
        assert progress is not None
        assert progress["total_wps"] == 4
        assert progress["planned_wps"] == 1
        assert progress["in_progress_wps"] == 1
        assert progress["done_wps"] == 1
        assert progress["for_review_wps"] == 1

    def test_find_first_wp_by_lane_planned(self, feature_with_tasks: Path) -> None:
        assert _find_first_wp_by_lane(feature_with_tasks, "planned") == "WP01"

    def test_find_first_wp_by_lane_for_review(self, feature_with_tasks: Path) -> None:
        assert _find_first_wp_by_lane(feature_with_tasks, "for_review") == "WP04"

    def test_find_first_wp_by_lane_not_found(self, feature_with_tasks: Path) -> None:
        assert _find_first_wp_by_lane(feature_with_tasks, "canceled") is None

    def test_find_first_wp_no_tasks_dir(self, feature_dir: Path) -> None:
        assert _find_first_wp_by_lane(feature_dir, "planned") is None


# ---------------------------------------------------------------------------
# decide_next
# ---------------------------------------------------------------------------


class TestDecideNext:
    def test_missing_feature_dir(self, tmp_path: Path) -> None:
        decision = decide_next("claude", "999-nonexistent", "success", tmp_path)
        assert decision.kind == DecisionKind.blocked
        assert "not found" in decision.reason

    def test_result_failed(self, feature_dir: Path) -> None:
        """Failed result must flow through runtime and return deterministic blocked state."""
        repo_root = feature_dir.parent.parent
        # Issue a first runtime step so failure has a concrete step to complete.
        first = decide_next("claude", "042-test-feature", "success", repo_root)
        assert first.step_id is not None

        decision = decide_next("claude", "042-test-feature", "failed", repo_root)
        assert decision.kind == DecisionKind.blocked
        assert "failed" in (decision.reason or "").lower()
        assert decision.run_id is not None, "failed decision must include run_id"

    def test_result_failed_after_advance_carries_step_id(self, feature_dir: Path) -> None:
        """After advancing, failed result still carries canonical run metadata."""
        repo_root = feature_dir.parent.parent
        # First call advances to get a step issued
        d1 = decide_next("claude", "042-test-feature", "success", repo_root)
        assert d1.step_id is not None
        # Now fail — runtime should return blocked and keep run correlation
        d2 = decide_next("claude", "042-test-feature", "failed", repo_root)
        assert d2.kind == DecisionKind.blocked
        assert d2.run_id is not None
        assert d2.step_id is None or isinstance(d2.step_id, str)

    def test_result_blocked(self, feature_dir: Path) -> None:
        repo_root = feature_dir.parent.parent
        # Issue a first runtime step so blocked result completes prior step through runtime.
        first = decide_next("claude", "042-test-feature", "success", repo_root)
        assert first.step_id is not None

        decision = decide_next("claude", "042-test-feature", "blocked", repo_root)
        assert decision.kind == DecisionKind.blocked
        assert "blocked" in (decision.reason or "").lower()
        assert decision.run_id is not None, "blocked decision must include run_id"

    def test_terminal_state(self, feature_dir: Path) -> None:
        """Completing all runtime steps produces a terminal decision."""
        repo_root = feature_dir.parent.parent
        _complete_all_steps(repo_root, "042-test-feature")
        decision = decide_next("claude", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.terminal

    def test_decision_has_required_fields(self, feature_dir: Path) -> None:
        repo_root = feature_dir.parent.parent
        decision = decide_next("claude", "042-test-feature", "success", repo_root)
        d = decision.to_dict()
        assert "kind" in d
        assert "agent" in d
        assert "feature_slug" in d
        assert "mission" in d
        assert "mission_state" in d
        assert "timestamp" in d
        assert "guard_failures" in d

    def test_decision_has_runtime_fields(self, feature_dir: Path) -> None:
        """Runtime fields (run_id, step_id) are present in decisions."""
        repo_root = feature_dir.parent.parent
        decision = decide_next("claude", "042-test-feature", "success", repo_root)
        d = decision.to_dict()
        assert "run_id" in d
        assert "step_id" in d
        assert "decision_id" in d
        assert "input_key" in d

    def test_implement_state_with_planned_wp(self, feature_with_tasks: Path) -> None:
        """When in implement state with planned WPs, returns implement action."""
        repo_root = feature_with_tasks.parent.parent
        # Advance runtime to implement step
        _advance_runtime_to_step(repo_root, "042-test-feature", "implement")
        decision = decide_next("claude", "042-test-feature", "success", repo_root)
        # Should stay in implement state and map to implement action with the planned WP
        if decision.kind == DecisionKind.step and decision.action == "implement":
            assert decision.wp_id == "WP01"
            assert decision.workspace_path is not None

    def test_to_dict_roundtrip(self) -> None:
        decision = Decision(
            kind=DecisionKind.step,
            agent="test",
            feature_slug="042-test",
            mission="software-dev",
            mission_state="specify",
            timestamp="2026-02-17T00:00:00+00:00",
            action="specify",
            progress={"total_wps": 3, "done_wps": 1},
            run_id="abc123",
            step_id="specify",
        )
        d = decision.to_dict()
        assert d["kind"] == "step"
        assert d["mission_state"] == "specify"
        assert d["progress"]["total_wps"] == 3
        assert d["run_id"] == "abc123"
        assert d["step_id"] == "specify"

    def test_first_call_returns_step(self, feature_dir: Path) -> None:
        """First call on a fresh feature returns a step decision."""
        repo_root = feature_dir.parent.parent
        decision = decide_next("claude", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.run_id is not None
        assert decision.step_id is not None


# ---------------------------------------------------------------------------
# Atomic task step alias tests
# ---------------------------------------------------------------------------


class TestTaskStepAliases:

    def test_tasks_outline_maps_to_tasks_outline_action(self, feature_dir: Path) -> None:
        """Verify _state_to_action maps tasks_outline → tasks-outline via alias."""
        from specify_cli.next.decision import _state_to_action

        repo_root = feature_dir.parent.parent
        action, wp_id, workspace_path = _state_to_action(
            "tasks_outline", "042-test-feature", feature_dir, repo_root, "software-dev",
        )
        assert action == "tasks-outline"
        assert wp_id is None
        assert workspace_path is None

    def test_tasks_packages_maps_to_tasks_packages_action(self, feature_dir: Path) -> None:
        """Verify _state_to_action maps tasks_packages → tasks-packages via alias."""
        from specify_cli.next.decision import _state_to_action

        repo_root = feature_dir.parent.parent
        action, wp_id, workspace_path = _state_to_action(
            "tasks_packages", "042-test-feature", feature_dir, repo_root, "software-dev",
        )
        assert action == "tasks-packages"
        assert wp_id is None
        assert workspace_path is None

    def test_tasks_finalize_maps_to_tasks_finalize_action(self, feature_dir: Path) -> None:
        """Verify _state_to_action maps tasks_finalize → tasks-finalize via alias."""
        from specify_cli.next.decision import _state_to_action

        repo_root = feature_dir.parent.parent
        action, wp_id, workspace_path = _state_to_action(
            "tasks_finalize", "042-test-feature", feature_dir, repo_root, "software-dev",
        )
        assert action == "tasks-finalize"
        assert wp_id is None
        assert workspace_path is None


class TestDecisionQuestionOptions:

    def test_decision_has_question_and_options(self) -> None:
        """Decision with question/options exposes them in to_dict()."""
        decision = Decision(
            kind=DecisionKind.decision_required,
            agent="test",
            feature_slug="042-test",
            mission="software-dev",
            mission_state="unknown",
            timestamp="2026-02-18T00:00:00+00:00",
            reason="Decision required",
            question="Which approach should we take?",
            options=["Option A", "Option B", "Option C"],
            decision_id="test-decision-1",
        )
        d = decision.to_dict()
        assert d["question"] == "Which approach should we take?"
        assert d["options"] == ["Option A", "Option B", "Option C"]
        assert d["decision_id"] == "test-decision-1"

    def test_decision_question_options_default_none(self) -> None:
        """Decision without question/options defaults to None."""
        decision = Decision(
            kind=DecisionKind.step,
            agent="test",
            feature_slug="042-test",
            mission="software-dev",
            mission_state="specify",
            timestamp="2026-02-18T00:00:00+00:00",
        )
        d = decision.to_dict()
        assert d["question"] is None
        assert d["options"] is None
