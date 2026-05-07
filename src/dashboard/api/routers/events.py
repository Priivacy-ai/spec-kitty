"""Server-Sent Events router for mission status streaming (FR-009–FR-012)."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from starlette.responses import StreamingResponse

from specify_cli.status.store import read_events

__all__ = ["register"]

_POLL_INTERVAL = 2.0  # seconds between event log polls
_KEEPALIVE_INTERVAL = 15.0  # seconds between keepalive comments


async def _stream_mission_events(project_dir: Path, last_event_id: str | None):
    """Async generator yielding SSE-formatted lines."""
    yield "event: connected\ndata: {}\n\n"

    last_keepalive = time.monotonic()

    while True:
        kitty_specs = project_dir / "kitty-specs"
        new_events = []

        if kitty_specs.exists():
            for feature_dir in kitty_specs.iterdir():
                if not feature_dir.is_dir():
                    continue
                try:
                    events = read_events(feature_dir)
                except Exception:
                    continue
                for event in events:
                    if last_event_id and event.event_id <= last_event_id:
                        continue
                    new_events.append(event)

        new_events.sort(key=lambda e: e.event_id)

        for event in new_events:
            last_event_id = event.event_id
            payload = {
                "mission_id": event.mission_id,
                "mission_slug": event.mission_slug,
                "wp_id": event.wp_id,
                "from_lane": event.from_lane.value if hasattr(event.from_lane, "value") else str(event.from_lane),
                "to_lane": event.to_lane.value if hasattr(event.to_lane, "value") else str(event.to_lane),
                "at": event.at if isinstance(event.at, str) else event.at.isoformat(),
            }
            yield f"id: {event.event_id}\nevent: mission_status\ndata: {json.dumps(payload)}\n\n"

        now = time.monotonic()
        if now - last_keepalive >= _KEEPALIVE_INTERVAL:
            yield ": keepalive\n\n"
            last_keepalive = now

        await asyncio.sleep(_POLL_INTERVAL)


def register(app: FastAPI) -> None:
    """Mount the SSE events router on ``app``."""
    router = APIRouter(tags=["events"])

    @router.get("/api/events/missions", include_in_schema=True)
    async def stream_mission_events(request: Request) -> StreamingResponse:
        """Stream mission status changes as Server-Sent Events.

        Supports Last-Event-ID header for resumption.
        Returns text/event-stream media type.
        """
        last_event_id = request.headers.get("last-event-id") or None

        # Validate Last-Event-ID is a plausible ULID (26 uppercase alphanumeric)
        if last_event_id and (len(last_event_id) != 26 or not last_event_id.isalnum()):
            last_event_id = None

        project_dir = request.app.state.project_dir

        return StreamingResponse(
            _stream_mission_events(project_dir, last_event_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    app.include_router(router)
