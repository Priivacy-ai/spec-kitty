"""Tests for the runtime-to-sync emitter adapter."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

pytestmark = pytest.mark.fast

_MISSION_ID = "01JTJ8M3Z3ZV4A6J3B1Q4JQ8RM"


def _actor(actor_id: str, actor_type: str = "llm") -> SimpleNamespace:
    return SimpleNamespace(actor_id=actor_id, actor_type=actor_type)


class TestSyncRuntimeEventEmitter:
    def test_adapter_emits_mission_run_and_lifecycle_sequence(
        self,
        emitter,
        temp_queue,
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(
            "specify_cli.sync.runtime_event_emitter.get_emitter",
            lambda: emitter,
        )

        adapter = SyncRuntimeEventEmitter(
            mission_slug="042-test-feature",
            mission_type="software-dev",
            mission_id=_MISSION_ID,
        )

        adapter.emit_mission_run_started(
            SimpleNamespace(
                run_id="run-001",
                mission_type="software-dev",
                actor=_actor("system", "service"),
            )
        )
        adapter.emit_next_step_issued(
            SimpleNamespace(
                run_id="run-001",
                step_id="specify",
                agent_id="codex",
                actor=_actor("codex"),
            )
        )
        adapter.emit_decision_input_requested(
            SimpleNamespace(
                run_id="run-001",
                decision_id="dec-001",
                step_id="specify",
                question="Proceed?",
                options=("yes", "no"),
                input_key=None,
                actor=_actor("codex"),
            )
        )
        adapter.emit_decision_input_answered(
            SimpleNamespace(
                run_id="run-001",
                decision_id="dec-001",
                answer="yes",
                actor=_actor("robert", "human"),
            )
        )
        adapter.emit_mission_run_completed(
            SimpleNamespace(
                run_id="run-001",
                mission_type="software-dev",
                actor=_actor("codex"),
            )
        )

        events = temp_queue.drain_queue()
        assert [event["event_type"] for event in events] == [
            "MissionRunStarted",
            "MissionStarted",
            "PhaseEntered",
            "NextStepIssued",
            "DecisionInputRequested",
            "DecisionInputAnswered",
            "MissionRunCompleted",
            "MissionCompleted",
        ]
        assert events[1]["payload"]["initial_phase"] == "not_started"
        assert events[2]["payload"]["previous_phase"] == "not_started"
        assert events[2]["payload"]["phase_name"] == "specify"
        assert events[-1]["payload"]["final_phase"] == "specify"

    def test_seed_from_snapshot_avoids_duplicate_phase_entry(
        self,
        emitter,
        temp_queue,
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(
            "specify_cli.sync.runtime_event_emitter.get_emitter",
            lambda: emitter,
        )

        adapter = SyncRuntimeEventEmitter(
            mission_slug="042-test-feature",
            mission_type="software-dev",
            mission_id=_MISSION_ID,
        )
        adapter.seed_from_snapshot(
            SimpleNamespace(
                issued_step_id="implement",
                completed_steps=["specify", "plan"],
                pending_decisions={},
                decisions={},
                blocked_reason=None,
            )
        )
        adapter.emit_next_step_issued(
            SimpleNamespace(
                run_id="run-001",
                step_id="implement",
                agent_id="codex",
                actor=_actor("codex"),
            )
        )

        events = temp_queue.drain_queue()
        assert [event["event_type"] for event in events] == ["NextStepIssued"]
