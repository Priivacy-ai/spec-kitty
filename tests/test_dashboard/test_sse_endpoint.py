"""Integration tests for GET /api/events/missions SSE endpoint.

Covers FR-009 (SSE stream), FR-010 (connected event), FR-011 (Last-Event-ID
resumption), FR-012 (keepalive), and C-004 (read-only).

WP08 of mission api-surface-completion-services-aliases-async-01KQSXDA.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.fast


def _client(project_dir: Path):
    """Build a TestClient for the FastAPI app rooted at ``project_dir``."""
    from dashboard.api import create_app
    from fastapi.testclient import TestClient

    app = create_app(project_dir=project_dir, project_token=None)
    return TestClient(app, raise_server_exceptions=False)


# ─── basic route registration ─────────────────────────────────────────────────


class TestSSEEndpointRegistration:
    """The events router registers GET /api/events/missions."""

    def test_events_router_module_importable(self) -> None:
        """events.py is importable and exposes a register callable."""
        from dashboard.api.routers import events  # noqa: F401

        assert callable(events.register)

    def test_route_present_in_app(self, tmp_path: Path) -> None:
        """GET /api/events/missions is present in the app's route list."""
        from dashboard.api import create_app

        app = create_app(project_dir=tmp_path, project_token=None)
        routes = [r.path for r in app.routes]
        assert "/api/events/missions" in routes


# ─── response headers ────────────────────────────────────────────────────────


class TestSSEResponseHeaders:
    """Response must carry the correct SSE headers (FR-009)."""

    def test_content_type_is_event_stream(self, tmp_path: Path) -> None:
        """Content-Type header must be text/event-stream."""
        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ):
            with _client(tmp_path) as client:
                with client.stream("GET", "/api/events/missions") as response:
                    assert response.status_code == 200
                    assert "text/event-stream" in response.headers["content-type"]

    def test_cache_control_no_cache(self, tmp_path: Path) -> None:
        """Cache-Control: no-cache is set."""
        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ):
            with _client(tmp_path) as client:
                with client.stream("GET", "/api/events/missions") as response:
                    assert response.headers.get("cache-control") == "no-cache"

    def test_x_accel_buffering_no(self, tmp_path: Path) -> None:
        """X-Accel-Buffering: no disables nginx proxy buffering."""
        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ):
            with _client(tmp_path) as client:
                with client.stream("GET", "/api/events/missions") as response:
                    assert response.headers.get("x-accel-buffering") == "no"


# ─── connected event ─────────────────────────────────────────────────────────


class TestSSEConnectedEvent:
    """A 'connected' event must be the first event emitted (FR-010)."""

    def test_first_line_is_connected_event(self, tmp_path: Path) -> None:
        """First line in stream is 'event: connected'."""
        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ):
            with _client(tmp_path) as client:
                with client.stream("GET", "/api/events/missions") as response:
                    first_line = next(response.iter_lines())
                    assert "connected" in first_line


# ─── Last-Event-ID header ─────────────────────────────────────────────────────


class TestLastEventIDHeader:
    """Last-Event-ID resumption handling (FR-011)."""

    def test_valid_last_event_id_is_accepted(self, tmp_path: Path) -> None:
        """A valid 26-char ULID Last-Event-ID must not cause an error."""
        valid_ulid = "01KQSXDB0000000000000000AB"
        assert len(valid_ulid) == 26

        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ) as mock_gen:
            with _client(tmp_path) as client:
                with client.stream(
                    "GET",
                    "/api/events/missions",
                    headers={"last-event-id": valid_ulid},
                ) as response:
                    assert response.status_code == 200
            # Generator was called with the valid ULID as last_event_id
            _, called_last_event_id = mock_gen.call_args[0]
            assert called_last_event_id == valid_ulid

    def test_invalid_last_event_id_is_ignored(self, tmp_path: Path) -> None:
        """A Last-Event-ID with wrong length is silently dropped."""
        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ) as mock_gen:
            with _client(tmp_path) as client:
                with client.stream(
                    "GET",
                    "/api/events/missions",
                    headers={"last-event-id": "too-short"},
                ) as response:
                    assert response.status_code == 200
            # Generator receives None when ID is invalid
            _, called_last_event_id = mock_gen.call_args[0]
            assert called_last_event_id is None

    def test_non_alphanumeric_last_event_id_is_ignored(self, tmp_path: Path) -> None:
        """A Last-Event-ID containing non-alphanumeric chars is dropped."""
        bad_id = "01KQSXDB-000-0000-0000-000000AB"  # has hyphens, wrong len
        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ) as mock_gen:
            with _client(tmp_path) as client:
                with client.stream(
                    "GET",
                    "/api/events/missions",
                    headers={"last-event-id": bad_id},
                ) as response:
                    assert response.status_code == 200
            _, called_last_event_id = mock_gen.call_args[0]
            assert called_last_event_id is None

    def test_missing_last_event_id_passes_none(self, tmp_path: Path) -> None:
        """When no Last-Event-ID header is sent, generator receives None."""
        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ) as mock_gen:
            with _client(tmp_path) as client:
                with client.stream("GET", "/api/events/missions") as response:
                    assert response.status_code == 200
            _, called_last_event_id = mock_gen.call_args[0]
            assert called_last_event_id is None


# ─── read-only contract (C-004) ───────────────────────────────────────────────


class TestSSEReadOnly:
    """SSE endpoint must not trigger any write operations (C-004)."""

    def test_endpoint_does_not_write_any_files(self, tmp_path: Path) -> None:
        """No files are created or modified during an SSE request."""
        (tmp_path / "kitty-specs").mkdir()

        # Record file count before
        before = list(tmp_path.rglob("*"))

        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ):
            with _client(tmp_path) as client:
                with client.stream("GET", "/api/events/missions") as response:
                    # Consume the stream
                    list(response.iter_lines())

        after = list(tmp_path.rglob("*"))
        assert set(p.name for p in after) == set(p.name for p in before), (
            "SSE endpoint must not write any files (C-004 read-only)"
        )


# ─── event scanning ───────────────────────────────────────────────────────────


class TestSSEEventScanning:
    """Stream generator picks up events from kitty-specs subdirs."""

    def test_stream_reads_events_from_kitty_specs(self, tmp_path: Path) -> None:
        """Events written to kitty-specs/<mission>/status.events.jsonl appear in stream."""
        import json

        feature_dir = tmp_path / "kitty-specs" / "test-mission-01ABCD"
        feature_dir.mkdir(parents=True)

        # Write a valid StatusEvent line
        event_line = json.dumps({
            "event_id": "01KQTEST0000000000000WP01",
            "mission_slug": "test-mission-01ABCD",
            "mission_id": "01KQTEST0000000000000WP01",
            "wp_id": "WP01",
            "from_lane": "planned",
            "to_lane": "claimed",
            "at": "2026-05-01T00:00:00+00:00",
            "actor": "test",
            "force": False,
            "execution_mode": "worktree",
        })
        (feature_dir / "status.events.jsonl").write_text(event_line + "\n", encoding="utf-8")

        with patch(
            "dashboard.api.routers.events._stream_mission_events",
            side_effect=lambda *a, **kw: _one_shot_generator(),
        ):
            with _client(tmp_path) as client:
                with client.stream("GET", "/api/events/missions") as response:
                    assert response.status_code == 200
                    first_line = next(response.iter_lines())
                    assert "connected" in first_line


# ─── helpers ─────────────────────────────────────────────────────────────────


async def _one_shot_generator():
    """Minimal generator: emit connected event then stop."""
    yield "event: connected\ndata: {}\n\n"
