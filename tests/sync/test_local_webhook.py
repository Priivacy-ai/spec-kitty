"""Tests for the opt-in local event webhook (SPEC_KITTY_EVENT_WEBHOOK).

Covers:
- env unset -> no HTTP call
- env set -> envelope POSTed as JSON with correct Content-Type
- unreachable / raising endpoint -> no exception propagates
- non-http scheme -> ignored, no call
- integration through events.emit_wp_created with SaaS sync disabled
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.fast

from specify_cli.sync.local_webhook import EVENT_WEBHOOK_ENV, forward_event


SAMPLE_EVENT = {
    "event_id": "01HQXYZ" + "A" * 19,
    "event_type": "WPCreated",
    "aggregate_id": "WP01",
    "payload": {"wp_id": "WP01"},
}


class TestForwardEvent:
    """Unit tests for forward_event()."""

    def test_env_unset_makes_no_http_call(self, monkeypatch):
        """No webhook configured -> urlopen is never touched."""
        monkeypatch.delenv(EVENT_WEBHOOK_ENV, raising=False)
        with patch("specify_cli.sync.local_webhook.urllib.request.urlopen") as mock_open:
            forward_event(SAMPLE_EVENT)
        mock_open.assert_not_called()

    def test_env_set_posts_envelope_as_json(self, monkeypatch):
        """Configured URL -> full envelope POSTed as JSON with correct headers."""
        url = "http://localhost:9999/hook"
        monkeypatch.setenv(EVENT_WEBHOOK_ENV, url)

        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with patch(
            "specify_cli.sync.local_webhook.urllib.request.urlopen",
            return_value=response,
        ) as mock_open:
            forward_event(SAMPLE_EVENT)

        mock_open.assert_called_once()
        request = mock_open.call_args.args[0]
        assert request.full_url == url
        assert request.method == "POST"
        assert request.get_header("Content-type") == "application/json"
        assert json.loads(request.data.decode("utf-8")) == SAMPLE_EVENT

    def test_unreachable_endpoint_swallows_exception(self, monkeypatch):
        """A raising urlopen must never propagate out of forward_event."""
        monkeypatch.setenv(EVENT_WEBHOOK_ENV, "http://localhost:9999/hook")
        with patch(
            "specify_cli.sync.local_webhook.urllib.request.urlopen",
            side_effect=OSError("connection refused"),
        ):
            forward_event(SAMPLE_EVENT)  # must not raise

    def test_non_http_scheme_ignored(self, monkeypatch):
        """A non-http(s) URL is ignored without any network call."""
        monkeypatch.setenv(EVENT_WEBHOOK_ENV, "file:///etc/passwd")
        with patch("specify_cli.sync.local_webhook.urllib.request.urlopen") as mock_open:
            forward_event(SAMPLE_EVENT)
        mock_open.assert_not_called()

    def test_empty_env_ignored(self, monkeypatch):
        """An empty string is treated as unset."""
        monkeypatch.setenv(EVENT_WEBHOOK_ENV, "")
        with patch("specify_cli.sync.local_webhook.urllib.request.urlopen") as mock_open:
            forward_event(SAMPLE_EVENT)
        mock_open.assert_not_called()

    def test_https_url_accepted(self, monkeypatch):
        """https URLs are honoured just like http."""
        monkeypatch.setenv(EVENT_WEBHOOK_ENV, "https://example.test/hook")

        response = MagicMock()
        response.status = 202
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with patch(
            "specify_cli.sync.local_webhook.urllib.request.urlopen",
            return_value=response,
        ) as mock_open:
            forward_event(SAMPLE_EVENT)
        mock_open.assert_called_once()


class TestEventsIntegration:
    """Webhook fires through the events.py emit path, independent of SaaS sync."""

    def test_emit_wp_created_forwards_to_webhook_with_saas_disabled(
        self, emitter, temp_queue, monkeypatch
    ):
        """emit_wp_created delivers the envelope to the webhook even when
        SaaS sync is disabled (that is the whole point of the seam)."""
        from specify_cli.sync import events

        monkeypatch.setenv(EVENT_WEBHOOK_ENV, "http://localhost:9999/hook")
        # SaaS sync stays disabled: the daemon publish/trigger helpers are
        # no-ops, so only the webhook should fire.
        monkeypatch.setattr(events, "is_saas_sync_enabled", lambda: False)
        monkeypatch.setattr(events, "get_emitter", lambda **_: emitter)
        monkeypatch.setattr(
            events, "_ensure_dashboard_sync_daemon_for_active_project", lambda **_: None
        )

        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with patch(
            "specify_cli.sync.local_webhook.urllib.request.urlopen",
            return_value=response,
        ) as mock_open:
            event = events.emit_wp_created("WP01", "Implement sync", "028-sync")

        assert event is not None
        mock_open.assert_called_once()
        request = mock_open.call_args.args[0]
        assert request.method == "POST"
        assert json.loads(request.data.decode("utf-8")) == event
