"""Mission-level ``actor`` population (spec-kitty-events 8.0.0 bump, #7).

``MissionCreatedPayload.actor`` / ``MissionClosedPayload.actor`` are optional
opaque identifiers in events 8.0.0; without them MissionCreated/MissionClosed
moments render with no WHO. The emitter resolves them at emit time (git
``user.email``, else ``"cli"``) so no caller had to change; an explicit value
wins.
"""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.events import emit_mission_closed, emit_mission_created

pytestmark = pytest.mark.fast


def _git_email(email: str) -> CompletedProcess[str]:
    return CompletedProcess(args=[], returncode=0, stdout=f"{email}\n", stderr="")


class TestEmitMissionCreatedActor:
    """EventEmitter.emit_mission_created populates payload["actor"]."""

    def test_resolves_actor_from_git_user_email(
        self,
        emitter: EventEmitter,
        temp_queue,
    ) -> None:
        with patch("subprocess.run", return_value=_git_email("robert@example.com")):
            event = emitter.emit_mission_created(
                mission_slug="079-post-hardening",
                mission_number=79,
                target_branch="main",
                wp_count=4,
            )
        assert event is not None
        assert event["payload"]["actor"] == "robert@example.com"

    def test_falls_back_to_cli_when_git_has_no_email(
        self,
        emitter: EventEmitter,
        temp_queue,
    ) -> None:
        with patch("subprocess.run", return_value=_git_email("")):
            event = emitter.emit_mission_created(
                mission_slug="079-post-hardening",
                mission_number=79,
                target_branch="main",
                wp_count=4,
            )
        assert event is not None
        assert event["payload"]["actor"] == "cli"

    def test_explicit_actor_wins_over_resolution(
        self,
        emitter: EventEmitter,
        temp_queue,
    ) -> None:
        with patch("subprocess.run", return_value=_git_email("robert@example.com")) as run:
            event = emitter.emit_mission_created(
                mission_slug="079-post-hardening",
                mission_number=79,
                target_branch="main",
                wp_count=4,
                actor="svc-bot",
            )
        run.assert_not_called()
        assert event is not None
        assert event["payload"]["actor"] == "svc-bot"

    def test_whitespace_only_actor_is_rejected_fail_closed(
        self,
        emitter: EventEmitter,
        temp_queue,
    ) -> None:
        """A blank explicit ``actor`` fails the payload rule and skips emission."""
        with patch("subprocess.run", return_value=_git_email("robert@example.com")):
            event = emitter.emit_mission_created(
                mission_slug="079-post-hardening",
                mission_number=79,
                target_branch="main",
                wp_count=4,
                actor="   ",
            )
        assert event is None


class TestEmitMissionClosedActor:
    """EventEmitter.emit_mission_closed populates payload["actor"]."""

    def test_resolves_actor_from_git_user_email(
        self,
        emitter: EventEmitter,
        temp_queue,
    ) -> None:
        with patch("subprocess.run", return_value=_git_email("robert@example.com")):
            event = emitter.emit_mission_closed(
                mission_slug="079-post-hardening",
                total_wps=4,
            )
        assert event is not None
        assert event["payload"]["actor"] == "robert@example.com"

    def test_explicit_actor_wins_over_resolution(
        self,
        emitter: EventEmitter,
        temp_queue,
    ) -> None:
        with patch("subprocess.run", return_value=_git_email("robert@example.com")) as run:
            event = emitter.emit_mission_closed(
                mission_slug="079-post-hardening",
                total_wps=4,
                actor="svc-bot",
            )
        run.assert_not_called()
        assert event is not None
        assert event["payload"]["actor"] == "svc-bot"


class TestEventsFacadeActorPassThrough:
    """Module-level wrappers forward an explicit actor to the singleton."""

    def test_emit_mission_created_forwards_actor(self) -> None:
        mock_emitter = MagicMock()
        with (
            patch("specify_cli.sync.events.get_emitter", return_value=mock_emitter),
            patch("specify_cli.sync.events._ensure_dashboard_sync_daemon_for_active_project", return_value=None),
            patch("specify_cli.sync.events._publish_event_via_sync_daemon"),
            patch("specify_cli.sync.events._request_dashboard_sync"),
        ):
            emit_mission_created(
                mission_slug="079-post-hardening",
                mission_number=79,
                target_branch="main",
                wp_count=4,
                actor="svc-bot",
            )
        call_kwargs = mock_emitter.emit_mission_created.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("actor") == "svc-bot"

    def test_emit_mission_closed_forwards_actor(self) -> None:
        mock_emitter = MagicMock()
        with (
            patch("specify_cli.sync.events.get_emitter", return_value=mock_emitter),
            patch("specify_cli.sync.events._ensure_dashboard_sync_daemon_for_active_project", return_value=None),
            patch("specify_cli.sync.events._publish_event_via_sync_daemon"),
            patch("specify_cli.sync.events._request_dashboard_sync"),
        ):
            emit_mission_closed(
                mission_slug="079-post-hardening",
                total_wps=4,
                actor="svc-bot",
            )
        call_kwargs = mock_emitter.emit_mission_closed.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("actor") == "svc-bot"
