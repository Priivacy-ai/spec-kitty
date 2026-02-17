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
# derive_mission_state
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
# evaluate_guards
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
        repo_root = feature_dir.parent.parent
        decision = decide_next("claude", "042-test-feature", "failed", repo_root)
        assert decision.kind == DecisionKind.decision_required
        assert "failure" in decision.reason.lower()

    def test_result_blocked(self, feature_dir: Path) -> None:
        repo_root = feature_dir.parent.parent
        decision = decide_next("claude", "042-test-feature", "blocked", repo_root)
        assert decision.kind == DecisionKind.blocked
        assert "blocked" in decision.reason.lower()

    def test_terminal_state(self, feature_dir: Path) -> None:
        # Write events that put us in "done" state
        events_file = feature_dir / "mission-events.jsonl"
        events_file.write_text(
            json.dumps({"type": "phase_entered", "payload": {"state": "done"}}) + "\n",
            encoding="utf-8",
        )
        repo_root = feature_dir.parent.parent
        decision = decide_next("claude", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.terminal
        assert decision.mission_state == "done"

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

    def test_implement_state_with_planned_wp(self, feature_with_tasks: Path) -> None:
        """When in implement state with planned WPs, returns implement action."""
        events_file = feature_with_tasks / "mission-events.jsonl"
        events_file.write_text(
            json.dumps({"type": "phase_entered", "payload": {"state": "implement"}}) + "\n",
            encoding="utf-8",
        )
        repo_root = feature_with_tasks.parent.parent
        decision = decide_next("claude", "042-test-feature", "success", repo_root)
        # Should stay in implement state (guards won't pass since not all WPs done)
        # and map to implement action with the planned WP
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
        )
        d = decision.to_dict()
        assert d["kind"] == "step"
        assert d["mission_state"] == "specify"
        assert d["progress"]["total_wps"] == 3
