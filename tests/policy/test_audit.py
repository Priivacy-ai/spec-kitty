"""Tests for policy audit log."""

from specify_cli.policy.audit import (
    PolicyAuditEvent,
    append_audit_event,
    create_audit_event,
    read_audit_events,
)


class TestPolicyAuditEvent:
    def test_create_event(self):
        event = create_audit_event(
            event_type="risk_override",
            feature_slug="010-feat",
            actor="claude",
            reason="Operator approved high-risk parallelization",
            details={"risk_score": 0.8, "threshold": 0.6},
        )
        assert event.event_type == "risk_override"
        assert event.feature_slug == "010-feat"
        assert event.event_id  # ULID generated
        assert event.at  # Timestamp generated

    def test_round_trip_json(self):
        event = create_audit_event(
            event_type="merge_gate_override",
            feature_slug="010-feat",
            actor="robert",
            reason="Manual override",
        )
        line = event.to_json_line()
        restored = PolicyAuditEvent.from_json_line(line)
        assert restored.event_id == event.event_id
        assert restored.event_type == event.event_type
        assert restored.actor == event.actor


class TestAuditPersistence:
    def test_append_and_read(self, tmp_path):
        e1 = create_audit_event("risk_override", "feat", "alice", "reason 1")
        e2 = create_audit_event("merge_gate_override", "feat", "bob", "reason 2")

        append_audit_event(tmp_path, e1)
        append_audit_event(tmp_path, e2)

        events = read_audit_events(tmp_path)
        assert len(events) == 2
        assert events[0].event_type == "risk_override"
        assert events[1].event_type == "merge_gate_override"

    def test_read_empty(self, tmp_path):
        events = read_audit_events(tmp_path)
        assert events == []

    def test_read_missing_file(self, tmp_path):
        events = read_audit_events(tmp_path / "nonexistent")
        assert events == []
