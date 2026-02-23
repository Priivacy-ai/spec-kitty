"""Tests for CLI Lamport clock forward compatibility with connector-originated events.

Feature 011 (WP04): Verify the CLI sync client handles GatePassed, GateFailed,
and completely unknown event types gracefully when receiving SaaS-originated
events via WebSocket. The Lamport clock must update for ALL event types.

Covers:
- T023: clock.receive() works with GatePassed/GateFailed lamport_clock values
- T024: Unknown event types don't crash the WebSocket client
- T025: End-to-end test with message handler wired to clock
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from specify_cli.sync.clock import LamportClock
from specify_cli.sync.client import WebSocketClient, ConnectionStatus


# ---------------------------------------------------------------------------
# Sample SaaS-originated event messages (wrapped in WebSocket 'event' envelope)
# ---------------------------------------------------------------------------

def _gate_passed_message(lamport_clock: int = 42) -> dict:
    """Build a WebSocket message containing a GatePassed event from SaaS."""
    return {
        "type": "event",
        "event_id": "01HZQ1234567890ABCDEFGHIJ",
        "event_type": "GatePassed",
        "aggregate_id": "project-uuid-123",
        "lamport_clock": lamport_clock,
        "node_id": "saas-connector",
        "payload": {
            "check_name": "CI / test",
            "conclusion": "success",
            "repository": "acme/widgets",
            "branch": "main",
            "head_sha": "abc1234567890def",
            "html_url": "https://github.com/acme/widgets/runs/12345",
            "connector_type": "github",
        },
    }


def _gate_failed_message(lamport_clock: int = 55) -> dict:
    """Build a WebSocket message containing a GateFailed event from SaaS."""
    return {
        "type": "event",
        "event_id": "01HZQ1234567890ABCDEFGHIK",
        "event_type": "GateFailed",
        "aggregate_id": "project-uuid-456",
        "lamport_clock": lamport_clock,
        "node_id": "saas-connector",
        "payload": {
            "check_name": "CI / lint",
            "conclusion": "failure",
            "repository": "acme/widgets",
            "branch": "feature/new-thing",
            "head_sha": "def4567890abcdef",
            "html_url": "https://github.com/acme/widgets/runs/67890",
            "connector_type": "github",
        },
    }


def _unknown_future_event_message(lamport_clock: int = 99) -> dict:
    """Build a WebSocket message with a completely unknown future event type."""
    return {
        "type": "event",
        "event_id": "01HZQ1234567890ABCDEFGHIL",
        "event_type": "SomeUnknownFutureEventType",
        "aggregate_id": "project-uuid-789",
        "lamport_clock": lamport_clock,
        "node_id": "saas-future-service",
        "payload": {"some_field": "some_value"},
    }


def _unknown_message_type() -> dict:
    """Build a WebSocket message with a completely unknown message type."""
    return {
        "type": "some_new_protocol_message",
        "version": 2,
        "data": {"info": "future protocol extension"},
    }


# ---------------------------------------------------------------------------
# T023: Lamport clock receive() handles GatePassed/GateFailed values
# ---------------------------------------------------------------------------

class TestLamportClockReceiveConnectorEvents:
    """Verify clock.receive() correctly updates for connector event clock values.

    The clock.receive() method is type-agnostic -- it only takes an int.
    These tests lock the behaviour so it cannot regress when new event types
    are added by the SaaS connector layer.
    """

    def test_receive_updates_for_gate_passed_clock_value(self, tmp_path: Path):
        """clock.receive() updates correctly with a GatePassed event's lamport_clock."""
        clock = LamportClock(value=5, node_id="cli-node", _storage_path=tmp_path / "c.json")
        msg = _gate_passed_message(lamport_clock=42)

        result = clock.receive(msg["lamport_clock"])

        assert result == 43  # max(5, 42) + 1
        assert clock.value == 43

    def test_receive_updates_for_gate_failed_clock_value(self, tmp_path: Path):
        """clock.receive() updates correctly with a GateFailed event's lamport_clock."""
        clock = LamportClock(value=10, node_id="cli-node", _storage_path=tmp_path / "c.json")
        msg = _gate_failed_message(lamport_clock=55)

        result = clock.receive(msg["lamport_clock"])

        assert result == 56  # max(10, 55) + 1
        assert clock.value == 56

    def test_receive_updates_for_unknown_event_clock_value(self, tmp_path: Path):
        """clock.receive() updates correctly with an unknown event's lamport_clock."""
        clock = LamportClock(value=50, node_id="cli-node", _storage_path=tmp_path / "c.json")
        msg = _unknown_future_event_message(lamport_clock=99)

        result = clock.receive(msg["lamport_clock"])

        assert result == 100  # max(50, 99) + 1
        assert clock.value == 100

    def test_receive_when_local_clock_is_ahead_of_connector(self, tmp_path: Path):
        """clock.receive() still increments when local clock > connector clock."""
        clock = LamportClock(value=200, node_id="cli-node", _storage_path=tmp_path / "c.json")
        msg = _gate_passed_message(lamport_clock=42)

        result = clock.receive(msg["lamport_clock"])

        assert result == 201  # max(200, 42) + 1
        assert clock.value == 201

    def test_receive_persists_after_connector_event(self, tmp_path: Path):
        """clock.receive() persists the updated value to disk after a connector event."""
        clock_path = tmp_path / "c.json"
        clock = LamportClock(value=5, node_id="cli-node", _storage_path=clock_path)
        msg = _gate_passed_message(lamport_clock=42)

        clock.receive(msg["lamport_clock"])

        # Reload from disk and verify
        reloaded = LamportClock.load(clock_path)
        assert reloaded.value == 43


# ---------------------------------------------------------------------------
# T024: WebSocket client doesn't crash on unknown event types
# ---------------------------------------------------------------------------

class TestWebSocketClientForwardCompatibility:
    """Verify the WebSocket client handles unknown event/message types gracefully.

    The _handle_message() dispatcher routes on data['type'] (snapshot/event/ping).
    The _handle_event() method delegates to message_handler without inspecting event_type.
    These tests lock both behaviours.
    """

    @pytest.mark.asyncio
    async def test_handle_event_with_gate_passed_no_crash(self):
        """_handle_event with GatePassed event does not crash (no handler set)."""
        client = WebSocketClient("ws://localhost:8000", "test-token")
        # No message_handler set -- this should silently pass
        msg = _gate_passed_message(lamport_clock=42)

        # Should not raise
        await client._handle_event(msg)

    @pytest.mark.asyncio
    async def test_handle_event_with_gate_failed_no_crash(self):
        """_handle_event with GateFailed event does not crash (no handler set)."""
        client = WebSocketClient("ws://localhost:8000", "test-token")
        msg = _gate_failed_message(lamport_clock=55)

        await client._handle_event(msg)

    @pytest.mark.asyncio
    async def test_handle_event_with_unknown_type_no_crash(self):
        """_handle_event with unknown event type does not crash (no handler set)."""
        client = WebSocketClient("ws://localhost:8000", "test-token")
        msg = _unknown_future_event_message(lamport_clock=99)

        await client._handle_event(msg)

    @pytest.mark.asyncio
    async def test_handle_message_unknown_message_type_no_crash(self):
        """_handle_message with unknown message type does not crash."""
        client = WebSocketClient("ws://localhost:8000", "test-token")
        msg = _unknown_message_type()

        # Should silently pass through the else branch
        await client._handle_message(msg)

    @pytest.mark.asyncio
    async def test_handle_message_routes_gate_passed_to_handler(self):
        """_handle_message routes GatePassed event to the message handler."""
        client = WebSocketClient("ws://localhost:8000", "test-token")
        handler = AsyncMock()
        client.set_message_handler(handler)

        msg = _gate_passed_message(lamport_clock=42)
        await client._handle_message(msg)

        handler.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_handle_message_routes_gate_failed_to_handler(self):
        """_handle_message routes GateFailed event to the message handler."""
        client = WebSocketClient("ws://localhost:8000", "test-token")
        handler = AsyncMock()
        client.set_message_handler(handler)

        msg = _gate_failed_message(lamport_clock=55)
        await client._handle_message(msg)

        handler.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_handle_message_routes_unknown_event_to_handler(self):
        """_handle_message routes unknown event type to the message handler."""
        client = WebSocketClient("ws://localhost:8000", "test-token")
        handler = AsyncMock()
        client.set_message_handler(handler)

        msg = _unknown_future_event_message(lamport_clock=99)
        await client._handle_message(msg)

        handler.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_handle_message_does_not_route_unknown_message_type_to_handler(self):
        """Unknown message types (not 'event') should NOT reach the message handler."""
        client = WebSocketClient("ws://localhost:8000", "test-token")
        handler = AsyncMock()
        client.set_message_handler(handler)

        msg = _unknown_message_type()
        await client._handle_message(msg)

        handler.assert_not_awaited()


# ---------------------------------------------------------------------------
# T025: End-to-end: message handler wired to clock updates for all event types
# ---------------------------------------------------------------------------

class TestClockUpdateViaMessageHandler:
    """Verify a message handler that wires clock.receive() works for all event types.

    This tests the intended integration pattern: when a message_handler is set
    that extracts lamport_clock from the incoming event and calls clock.receive(),
    the clock updates correctly regardless of event_type.
    """

    @pytest.mark.asyncio
    async def test_gate_passed_updates_clock_via_handler(self, tmp_path: Path):
        """End-to-end: GatePassed event updates Lamport clock via wired handler."""
        clock = LamportClock(value=10, node_id="cli-node", _storage_path=tmp_path / "c.json")
        client = WebSocketClient("ws://localhost:8000", "test-token")

        async def clock_updating_handler(data: dict):
            if "lamport_clock" in data:
                clock.receive(data["lamport_clock"])

        client.set_message_handler(clock_updating_handler)

        msg = _gate_passed_message(lamport_clock=42)
        await client._handle_message(msg)

        assert clock.value == 43  # max(10, 42) + 1

    @pytest.mark.asyncio
    async def test_gate_failed_updates_clock_via_handler(self, tmp_path: Path):
        """End-to-end: GateFailed event updates Lamport clock via wired handler."""
        clock = LamportClock(value=10, node_id="cli-node", _storage_path=tmp_path / "c.json")
        client = WebSocketClient("ws://localhost:8000", "test-token")

        async def clock_updating_handler(data: dict):
            if "lamport_clock" in data:
                clock.receive(data["lamport_clock"])

        client.set_message_handler(clock_updating_handler)

        msg = _gate_failed_message(lamport_clock=55)
        await client._handle_message(msg)

        assert clock.value == 56  # max(10, 55) + 1

    @pytest.mark.asyncio
    async def test_unknown_event_updates_clock_via_handler(self, tmp_path: Path):
        """End-to-end: Unknown future event updates Lamport clock via wired handler."""
        clock = LamportClock(value=50, node_id="cli-node", _storage_path=tmp_path / "c.json")
        client = WebSocketClient("ws://localhost:8000", "test-token")

        async def clock_updating_handler(data: dict):
            if "lamport_clock" in data:
                clock.receive(data["lamport_clock"])

        client.set_message_handler(clock_updating_handler)

        msg = _unknown_future_event_message(lamport_clock=99)
        await client._handle_message(msg)

        assert clock.value == 100  # max(50, 99) + 1

    @pytest.mark.asyncio
    async def test_multiple_connector_events_advance_clock_monotonically(self, tmp_path: Path):
        """Clock advances monotonically through a sequence of connector events."""
        clock = LamportClock(value=0, node_id="cli-node", _storage_path=tmp_path / "c.json")
        client = WebSocketClient("ws://localhost:8000", "test-token")

        async def clock_updating_handler(data: dict):
            if "lamport_clock" in data:
                clock.receive(data["lamport_clock"])

        client.set_message_handler(clock_updating_handler)

        # Simulate a sequence of events from the SaaS connector
        events = [
            _gate_passed_message(lamport_clock=10),
            _gate_failed_message(lamport_clock=15),
            _gate_passed_message(lamport_clock=12),  # Out of order -- lower than previous
            _unknown_future_event_message(lamport_clock=20),
        ]

        clock_values = []
        for event in events:
            await client._handle_message(event)
            clock_values.append(clock.value)

        # Clock must be monotonically increasing
        assert clock_values == sorted(clock_values)
        assert all(b > a for a, b in zip(clock_values, clock_values[1:]))

        # Verify final value: max(0,10)+1=11, max(11,15)+1=16, max(16,12)+1=17, max(17,20)+1=21
        assert clock_values == [11, 16, 17, 21]

    @pytest.mark.asyncio
    async def test_handler_without_lamport_clock_field_does_not_crash(self, tmp_path: Path):
        """Message missing lamport_clock field does not crash the handler."""
        clock = LamportClock(value=10, node_id="cli-node", _storage_path=tmp_path / "c.json")
        client = WebSocketClient("ws://localhost:8000", "test-token")

        async def clock_updating_handler(data: dict):
            if "lamport_clock" in data:
                clock.receive(data["lamport_clock"])

        client.set_message_handler(clock_updating_handler)

        # Malformed event: missing lamport_clock
        msg = {
            "type": "event",
            "event_id": "01HZQ1234567890ABCDEFGHIM",
            "event_type": "GatePassed",
            "aggregate_id": "project-uuid-123",
            "node_id": "saas-connector",
            "payload": {},
        }
        await client._handle_message(msg)

        # Clock should not have changed
        assert clock.value == 10


# ---------------------------------------------------------------------------
# T024 supplement: VALID_EVENT_TYPES only gates outgoing events
# ---------------------------------------------------------------------------

class TestValidEventTypesOnlyGatesOutgoing:
    """Verify VALID_EVENT_TYPES allowlist only applies to outgoing event emission.

    The emitter validates event_type against VALID_EVENT_TYPES before sending.
    Incoming events received via WebSocket bypass this validation entirely.
    This is correct behaviour for forward compatibility.
    """

    def test_gate_passed_not_in_valid_event_types(self):
        """GatePassed is not in VALID_EVENT_TYPES (and that's fine for incoming)."""
        from specify_cli.sync.emitter import VALID_EVENT_TYPES
        assert "GatePassed" not in VALID_EVENT_TYPES

    def test_gate_failed_not_in_valid_event_types(self):
        """GateFailed is not in VALID_EVENT_TYPES (and that's fine for incoming)."""
        from specify_cli.sync.emitter import VALID_EVENT_TYPES
        assert "GateFailed" not in VALID_EVENT_TYPES

    def test_valid_event_types_only_contains_cli_originated_types(self):
        """VALID_EVENT_TYPES contains only CLI-originated event types."""
        from specify_cli.sync.emitter import VALID_EVENT_TYPES
        expected = {
            "WPStatusChanged", "WPCreated", "WPAssigned",
            "FeatureCreated", "FeatureCompleted", "HistoryAdded",
            "ErrorLogged", "DependencyResolved",
            "MissionDossierArtifactIndexed",
            "MissionDossierArtifactMissing",
            "MissionDossierParityDriftDetected",
            "MissionDossierSnapshotComputed",
        }
        assert VALID_EVENT_TYPES == expected
