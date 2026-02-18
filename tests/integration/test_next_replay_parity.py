"""Replay parity checks against canonical spec-kitty-events mission-next fixtures."""

from __future__ import annotations

from spec_kitty_events.conformance import load_replay_stream
from spec_kitty_events.mission_next import MissionRunStatus, reduce_mission_next_events
from spec_kitty_events.models import Event


def test_mission_next_replay_fixture_reduces_to_expected_state() -> None:
    """spec-kitty must remain compatible with the canonical mission-next replay stream."""
    envelopes = load_replay_stream("mission-next-replay-full-lifecycle")
    events = [Event(**envelope) for envelope in envelopes]

    reduced = reduce_mission_next_events(events)

    assert reduced.run_id == "replay-run-001"
    assert reduced.mission_key == "replay-mission"
    assert reduced.run_status == MissionRunStatus.COMPLETED
    assert reduced.current_step_id is None
    assert reduced.completed_steps == ("step-setup-env", "step-configure-db")
    assert "input:db-password" in reduced.answered_decisions
    assert "input:db-password" not in reduced.pending_decisions
    assert reduced.event_count == len(events)
    assert len(reduced.anomalies) == 0
