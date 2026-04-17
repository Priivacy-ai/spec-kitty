"""Tests for mission_id field in emit_mission_created() payload (T019 / FR-205, FR-206)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.events import emit_mission_created

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# T3.6 — emit_mission_created includes mission_id in payload when provided
# ---------------------------------------------------------------------------


class TestEmitMissionCreatedMissionId:
    """Tests for mission_id propagation through emit_mission_created."""

    def test_emitter_includes_mission_id_in_payload(
        self,
        emitter: EventEmitter,
        temp_queue,
    ) -> None:
        """EventEmitter.emit_mission_created adds mission_id to payload when provided."""
        event = emitter.emit_mission_created(
            mission_slug="079-post-hardening",
            mission_number=79,  # int, not str (FR-044, WP02)
            target_branch="main",
            wp_count=4,
            mission_id="01KNRQK0R1ZDS8Z57M1TRXF0XR",
        )
        assert event is not None
        assert "mission_id" in event["payload"]
        assert event["payload"]["mission_id"] == "01KNRQK0R1ZDS8Z57M1TRXF0XR"

    def test_emitter_omits_mission_id_when_none(
        self,
        emitter: EventEmitter,
        temp_queue,
    ) -> None:
        """EventEmitter.emit_mission_created does NOT include mission_id key when not provided."""
        event = emitter.emit_mission_created(
            mission_slug="079-post-hardening",
            mission_number=79,  # int, not str (FR-044, WP02)
            target_branch="main",
            wp_count=4,
            # mission_id omitted — legacy call
        )
        assert event is not None
        assert "mission_id" not in event["payload"]

    def test_events_facade_passes_mission_id_to_emitter(self) -> None:
        """emit_mission_created() in events.py forwards mission_id= to the singleton emitter."""
        mock_emitter = MagicMock()
        mock_emitter.emit_mission_created.return_value = {"payload": {"mission_id": "01TESTULID12345678901234AB"}}

        with (
            patch("specify_cli.sync.events.get_emitter", return_value=mock_emitter),
            patch("specify_cli.sync.events._ensure_dashboard_sync_daemon_for_active_project", return_value=None),
            patch("specify_cli.sync.events._publish_event_via_sync_daemon"),
            patch("specify_cli.sync.events._request_dashboard_sync"),
        ):
            emit_mission_created(
                mission_slug="079-post-hardening",
                mission_number=79,  # int, not str (FR-044, WP02)
                target_branch="main",
                wp_count=4,
                mission_id="01TESTULID12345678901234AB",
            )

        call_kwargs = mock_emitter.emit_mission_created.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("mission_id") == "01TESTULID12345678901234AB" or (
            len(call_kwargs.args) > 5 and call_kwargs.args[5] == "01TESTULID12345678901234AB"
        ), f"mission_id not forwarded: {call_kwargs}"

    def test_events_facade_legacy_call_no_mission_id(self) -> None:
        """emit_mission_created() without mission_id does not pass mission_id= to emitter (or passes None)."""
        mock_emitter = MagicMock()
        mock_emitter.emit_mission_created.return_value = {"payload": {}}

        with (
            patch("specify_cli.sync.events.get_emitter", return_value=mock_emitter),
            patch("specify_cli.sync.events._ensure_dashboard_sync_daemon_for_active_project", return_value=None),
            patch("specify_cli.sync.events._publish_event_via_sync_daemon"),
            patch("specify_cli.sync.events._request_dashboard_sync"),
        ):
            emit_mission_created(
                mission_slug="028-sync",
                mission_number=28,  # int, not str (FR-044, WP02)
                target_branch="main",
                wp_count=5,
                # No mission_id
            )

        call_kwargs = mock_emitter.emit_mission_created.call_args
        assert call_kwargs is not None
        # mission_id should be None or absent from the call
        passed_mission_id = call_kwargs.kwargs.get("mission_id")
        assert passed_mission_id is None
