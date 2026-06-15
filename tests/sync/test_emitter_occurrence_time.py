"""Producer occurrence time threads through the SaaS fan-out chain.

Mission: cli-saas-fanout-preserves-local-at-01KRNS87

The local ``StatusEvent.at`` MUST survive ``_saas_fan_out`` →
``fire_saas_fanout`` → ``emit_wp_status_changed`` (module) →
``EventEmitter.emit_wp_status_changed`` → ``EventEmitter._emit``, so that the
wire envelope's ``timestamp`` field equals the local lane-transition moment
(Rule R-T-01 in spec-kitty-events). When no ``occurred_at`` is provided, the
emitter mints ``datetime.now(UTC).isoformat()`` (current behavior, for
genuinely new events created at emission time).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.queue import OfflineQueue

pytestmark = pytest.mark.fast

PRODUCER_TIME_ISO = "2026-01-01T00:00:00+00:00"


class TestEmitOccurrenceTime:
    def test_emit_uses_explicit_occurred_at(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        event = emitter._emit(
            event_type="WPStatusChanged",
            aggregate_id="WP01",
            aggregate_type="WorkPackage",
            payload={
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "actor": "test",
                "mission_slug": "test-mission",
                "execution_mode": "direct_repo",
            },
            occurred_at=PRODUCER_TIME_ISO,
        )
        assert event is not None
        assert event["timestamp"] == PRODUCER_TIME_ISO

    def test_emit_mints_fresh_timestamp_when_no_occurred_at(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        before = datetime.now(UTC)
        event = emitter._emit(
            event_type="WPStatusChanged",
            aggregate_id="WP01",
            aggregate_type="WorkPackage",
            payload={
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "actor": "test",
                "mission_slug": "test-mission",
                "execution_mode": "direct_repo",
            },
        )
        after = datetime.now(UTC)
        assert event is not None
        emitted = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        # The fresh timestamp is bounded by [before, after] within the same call.
        assert before <= emitted <= after


class TestEmitWpStatusChangedOccurredAt:
    def test_method_threads_occurred_at_into_envelope(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
            actor="test",
            mission_slug="test-mission",
            occurred_at=PRODUCER_TIME_ISO,
        )
        assert event is not None
        assert event["timestamp"] == PRODUCER_TIME_ISO

    def test_method_without_occurred_at_mints_fresh(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        before = datetime.now(UTC)
        event = emitter.emit_wp_status_changed(
            wp_id="WP02",
            from_lane="planned",
            to_lane="in_progress",
            actor="test",
            mission_slug="test-mission",
        )
        after = datetime.now(UTC)
        assert event is not None
        emitted = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        assert before <= emitted <= after


class TestSaasFanOutThreadsAt:
    """The status emit pipeline's _saas_fan_out passes StatusEvent.at as occurred_at."""

    def test_saas_fan_out_forwards_event_at_as_occurred_at(self, monkeypatch):
        from specify_cli.status import adapters as adapters_module
        from specify_cli.status.emit import _saas_fan_out
        from specify_cli.status.models import Lane, StatusEvent

        captured = {}

        def fake_handler(**kwargs):
            captured.update(kwargs)

        # Replace registered handlers with our capture.
        monkeypatch.setattr(adapters_module, "_saas_handlers", [fake_handler])

        event = StatusEvent(
            event_id="01J6XW9KQT7M0YB3N4R5CQZ2EX",
            mission_slug="test-mission",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.IN_PROGRESS,
            at=PRODUCER_TIME_ISO,
            actor="test",
            force=False,
            execution_mode="direct_repo",
        )

        _saas_fan_out(event, mission_slug="test-mission", _repo_root=None)

        assert captured.get("occurred_at") == PRODUCER_TIME_ISO
        assert captured.get("wp_id") == "WP01"
        assert captured.get("from_lane") == "planned"
        assert captured.get("to_lane") == "in_progress"
