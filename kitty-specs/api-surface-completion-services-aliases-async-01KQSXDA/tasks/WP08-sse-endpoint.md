---
work_package_id: WP08
title: SSE Endpoint
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-012
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
created_at: '2026-05-04T17:07:04Z'
subtasks:
- T037
- T038
- T039
- T040
- T041
- T042
agent: "copilot:claude-sonnet-4-6:alphonso:reviewer"
shell_pid: "2041398"
history:
- at: '2026-05-04T17:07:04Z'
  event: created
  note: Initial task breakdown
authoritative_surface: src/dashboard/api/routers/
execution_mode: code_change
lane: planned
mission_id: 01KQSXDASEMGGZNAX3A5FXSEPM
owned_files:
- src/dashboard/api/routers/events.py
- tests/test_dashboard/test_sse_endpoint.py
tags: []
---

## Objective

Create `GET /api/events/missions` as a Server-Sent Events (SSE) endpoint. The endpoint streams `mission_status` events from `status.events.jsonl` files for all missions in the project directory, sends `: keepalive` comments every 15 seconds, and supports `Last-Event-ID` resumption using ULID lexicographic ordering. The implementation uses zero new dependencies — Starlette's built-in `StreamingResponse` is already a transitive dep of FastAPI.

## Context

### Why SSE, not WebSocket (from `research.md` section D)

C-004 mandates read-only semantics. SSE is the correct unidirectional push primitive for this use case. WebSocket is bidirectional and heavier; clients need only a standard `EventSource`. No new dependency is needed: Starlette's `StreamingResponse` with `media_type="text/event-stream"` provides everything required.

### SSE wire format (from `contracts/sse-events.md`)

```
# Connected handshake:
event: connected
data: {"version": "1", "ts": "2026-07-01T12:00:00+00:00"}
id: <server-ulid>

# Domain event:
event: mission_status
data: {"mission_id": "01J6XW9K...", "mission_slug": "083-my-mission", "wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress", "actor": "claude", "at": "...", "event_id": "01KQSXDA..."}
id: 01KQSXDA...

# Keepalive comment (no blank line after — it IS a complete SSE comment):
: keepalive

```

### `Last-Event-ID` resumption

On reconnect, the client sends `Last-Event-ID: <event_id>`. The server:
1. Reads all events from all mission `status.events.jsonl` files
2. Skips events whose `event_id` ≤ the received ULID (ULID string comparison is lexicographic = chronological)
3. Emits the backlog in order, then enters the live-tail polling loop

### Polling strategy

Poll `status.events.jsonl` every 2 seconds using `asyncio.sleep`. No `inotify`, no threads, no new deps. Track the last emitted `event_id` per session to avoid re-sending. Use `Path.read_text()` within each polling tick — no persistent file handles.

### Resource cleanup (NFR-004)

The async generator must not hold open file handles between `yield` points. When the client disconnects, the generator is garbage-collected after the current polling tick (≤ 15 s). No background threads are created.

### Error cases

- `project_dir` not configured → `HTTPException(503)` before any streaming begins
- Exception after `connected` event → log at ERROR, close the stream; client reconnects automatically
- Invalid `Last-Event-ID` header → DEBUG log, fall back to live-tail (no replay)

This WP is **intentionally independent** — it can run in parallel with all other WPs, including WP01.

## Branch Strategy

- `planning_base_branch`: `feature/645-api-surface-completion-mission-c`
- `merge_target_branch`: `feature/645-api-surface-completion-mission-c`
- No WP dependencies — can start on the base branch immediately.

## Subtask Guide

### T037: Create `src/dashboard/api/routers/events.py` with Router and Route

**Purpose:** Set up the router module with the `GET /api/events/missions` route skeleton.

**Steps:**

1. Create `src/dashboard/api/routers/events.py`:

```python
"""SSE endpoint for mission status events.

GET /api/events/missions — streams StatusEvent entries from all missions'
status.events.jsonl files as Server-Sent Events.

Wire format reference: contracts/sse-events.md
FR refs: FR-009, FR-010, FR-011, FR-012
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Polling interval in seconds (FR-010)
_POLL_INTERVAL_S = 2

# Keepalive interval in seconds (FR-012, contracts/sse-events.md section 4.3)
_KEEPALIVE_INTERVAL_S = 15

# ULID pattern: 26 characters from the ULID alphabet
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


@router.get("/api/events/missions")
async def stream_mission_events(request: Request) -> StreamingResponse:
    """Stream mission status events as Server-Sent Events.

    Supports Last-Event-ID resumption. Sends keepalive comments every
    15 seconds. Read-only (C-004).
    """
    project_dir: Path | None = getattr(request.app.state, "project_dir", None)
    if project_dir is None or not project_dir.exists():
        raise HTTPException(status_code=503, detail="project_dir not configured")

    last_event_id = request.headers.get("last-event-id", "")
    if last_event_id and not _ULID_RE.match(last_event_id):
        logger.debug("Ignoring invalid Last-Event-ID header: %r", last_event_id)
        last_event_id = ""

    return StreamingResponse(
        _stream_mission_events(project_dir, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

2. Verify the module imports without error: `cd src && python -c "from dashboard.api.routers.events import router; print('OK')"`.

**Files:** `src/dashboard/api/routers/events.py` (new)

**Validation:**
- [x] File exists at `src/dashboard/api/routers/events.py`
- [x] `router = APIRouter()` is defined
- [x] `GET /api/events/missions` route is declared
- [x] Returns `StreamingResponse` with `media_type="text/event-stream"`
- [x] Required response headers are set (`Cache-Control`, `Connection`, `X-Accel-Buffering`)
- [x] Module imports without error

---

### T038: Implement SSE Async Generator `_stream_mission_events`

**Purpose:** The core of the SSE endpoint — the async generator that emits `connected`, `mission_status` events, and handles the polling loop.

**Steps:**

1. Add the `_stream_mission_events` async generator to `events.py`. Key design decisions:
   - `connected` event is emitted first with a server-generated timestamp
   - Read events from `specify_cli.status.store.read_events(feature_dir)` for each mission
   - Filter events by ULID if `last_event_id` is provided
   - `event_id` is the ULID from `StatusEvent.event_id`; it is also the SSE `id:` field

```python
async def _stream_mission_events(
    project_dir: Path,
    last_event_id: str,
) -> AsyncGenerator[str, None]:
    """Async generator for the SSE stream body.

    Emits:
      1. connected event immediately
      2. Backlogged events (if last_event_id provided)
      3. Live-tail events as they arrive (polling every _POLL_INTERVAL_S seconds)
      4. Keepalive comments every _KEEPALIVE_INTERVAL_S seconds

    Resource guarantee (NFR-004): no persistent file handles between yields.
    """
    from specify_cli.status.store import read_events  # avoid circular import at module level

    # 1. Emit connected event
    ts = datetime.now(tz=timezone.utc).isoformat()
    yield f"event: connected\ndata: {json.dumps({'version': '1', 'ts': ts})}\nid: \n\n"

    # Track which event_id we last emitted to avoid re-sending
    seen_event_id = last_event_id

    last_keepalive = asyncio.get_event_loop().time()

    while True:
        now = asyncio.get_event_loop().time()
        found_new = False

        # Collect all mission feature dirs
        feature_dirs = _collect_feature_dirs(project_dir)

        for feature_dir in feature_dirs:
            try:
                events = read_events(feature_dir)
            except Exception:
                logger.debug("Could not read events from %s", feature_dir)
                continue

            for event in events:
                event_id = event.event_id  # ULID string
                # Skip already-seen events (ULID lexicographic = chronological order)
                if seen_event_id and event_id <= seen_event_id:
                    continue
                # Emit mission_status event
                payload = {
                    "mission_id": event.feature_slug,  # adjust per actual StatusEvent attrs
                    "mission_slug": getattr(event, "mission_slug", event.feature_slug),
                    "wp_id": event.wp_id,
                    "from_lane": event.from_lane,
                    "to_lane": event.to_lane,
                    "actor": event.actor,
                    "at": event.at,
                    "event_id": event_id,
                }
                yield f"event: mission_status\ndata: {json.dumps(payload)}\nid: {event_id}\n\n"
                seen_event_id = event_id
                found_new = True
                last_keepalive = now

        # 3. Keepalive comment if idle for _KEEPALIVE_INTERVAL_S
        if not found_new and (now - last_keepalive) >= _KEEPALIVE_INTERVAL_S:
            yield ": keepalive\n\n"
            last_keepalive = now

        await asyncio.sleep(_POLL_INTERVAL_S)


def _collect_feature_dirs(project_dir: Path) -> list[Path]:
    """Return all feature directories under kitty-specs/ that have a status.events.jsonl."""
    kitty_specs = project_dir / "kitty-specs"
    if not kitty_specs.exists():
        return []
    return [
        d
        for d in kitty_specs.iterdir()
        if d.is_dir() and (d / "status.events.jsonl").exists()
    ]
```

2. **Important:** Read the actual `StatusEvent` attributes from `specify_cli.status.models` before writing the payload dict. The generator must use the correct attribute names from the live codebase. Run:
   ```bash
   cd src && python -c "from specify_cli.status.models import StatusEvent; import inspect; print(inspect.get_annotations(StatusEvent))"
   ```

3. Update the `payload` dict keys to match the SSE contract from `contracts/sse-events.md` section 4.2:
   - `mission_id`, `mission_slug`, `wp_id`, `from_lane`, `to_lane`, `actor`, `at`, `event_id`

**Files:** `src/dashboard/api/routers/events.py` (update)

**Validation:**
- [x] `_stream_mission_events` is an `AsyncGenerator[str, None]`
- [x] First yield is the `connected` event
- [x] `mission_status` events use all 8 fields from the SSE contract
- [x] `id:` field is set to `event_id` on each event
- [x] File handles are opened and closed within each polling tick (no persistent handles)

---

### T039: Implement Keepalive Comment

**Purpose:** Prevent client and proxy timeouts when no domain events arrive for 15 seconds.

**Steps:**

The keepalive logic is already embedded in `_stream_mission_events` (T038). Specifically verify:

1. `last_keepalive` is initialised to `asyncio.get_event_loop().time()` before the loop.
2. After each polling tick where no new events were found, check `(now - last_keepalive) >= _KEEPALIVE_INTERVAL_S`.
3. If true, yield `": keepalive\n\n"` and reset `last_keepalive = now`.
4. `last_keepalive` is also reset whenever a real event is emitted (so keepalive is not sent within 15 s of a real event).
5. The keepalive comment starts with `:` (per SSE spec: comment lines begin with `:`). No `event:` or `data:` field — just the bare comment line followed by a blank line.

**Files:** `src/dashboard/api/routers/events.py` (keepalive logic within `_stream_mission_events`)

**Validation:**
- [x] Keepalive interval is exactly 15 seconds (`_KEEPALIVE_INTERVAL_S = 15`)
- [x] Keepalive format is `": keepalive\n\n"` (comment line + blank line)
- [x] Keepalive timer resets when a real event is emitted
- [x] Keepalive is not sent within 15 s of the `connected` event

---

### T040: Implement `Last-Event-ID` Header Handling

**Purpose:** Enable clients to resume the stream after a reconnect without missing events.

**Steps:**

The `Last-Event-ID` handling has two parts — already outlined in T037 and T038:

1. **Header reading (in route handler, T037):**
   - Read `request.headers.get("last-event-id", "")`.
   - Validate with `_ULID_RE.match(last_event_id)` (26-char ULID pattern).
   - If invalid, log at DEBUG and pass `""` to the generator.

2. **Filtering (in generator, T038):**
   - Track `seen_event_id` initialised to `last_event_id`.
   - Skip events where `event_id <= seen_event_id` (ULID string comparison = chronological order).
   - After emitting an event, update `seen_event_id = event_id`.

3. Verify with a manual test scenario:
   - Create two events in a test `status.events.jsonl` with ULIDs A and B (A < B chronologically).
   - Call the generator with `last_event_id = A`.
   - Verify only event B is emitted (event A is skipped).

4. Verify with invalid header:
   - Call the route handler with `Last-Event-ID: not-a-ulid`.
   - Verify the handler falls back to live-tail (no error response, no replay).

**Files:** `src/dashboard/api/routers/events.py`

**Validation:**
- [x] Valid ULID in `Last-Event-ID` → only events with `event_id > last_event_id` are streamed
- [x] Invalid/absent `Last-Event-ID` → live-tail mode (no replay, no error)
- [x] ULID validation uses `re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")`
- [x] DEBUG log emitted for invalid header

---

### T041: Register Events Router in `src/dashboard/api/__init__.py`

**Purpose:** The new events router must be registered with the FastAPI `create_app()` function so `GET /api/events/missions` is reachable.

**Steps:**

1. Open `src/dashboard/api/__init__.py` (or wherever `create_app` adds routers — look for `app.include_router(...)` calls).

2. Find the section where existing routers are registered:
   ```python
   from dashboard.api.routers import health, diagnostics, sync, ...
   app.include_router(health.router)
   app.include_router(diagnostics.router)
   # etc.
   ```

3. Add the events router:
   ```python
   from dashboard.api.routers import events
   app.include_router(events.router)
   ```

4. Verify the route is visible in the running app:
   ```bash
   cd src && python -c "
   from pathlib import Path
   from dashboard.api import create_app
   app = create_app(project_dir=Path('.'), project_token=None)
   routes = [r.path for r in app.routes]
   assert '/api/events/missions' in routes, f'Route not found. Routes: {routes}'
   print('Route registered OK')
   "
   ```

**Files:** `src/dashboard/api/__init__.py` (update)

**Validation:**
- [x] `events.router` is imported and registered with `app.include_router`
- [x] `GET /api/events/missions` appears in the app routes list
- [x] App instantiation does not raise

---

### T042: Write `tests/test_dashboard/test_sse_endpoint.py`

**Purpose:** Integration tests for the SSE endpoint verifying the wire format, keepalive, `Last-Event-ID` resumption, content type, and read-only semantics.

**Steps:**

1. Create `tests/test_dashboard/test_sse_endpoint.py`:

```python
"""Integration tests for GET /api/events/missions SSE endpoint.

Uses FastAPI TestClient with stream=True for SSE wire format testing.
Mocks asyncio.sleep to make keepalive tests instantaneous.

FR refs: FR-009, FR-010, FR-011, FR-012, C-004, NFR-003, NFR-004
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_project(tmp_path):
    """FastAPI app with project_dir set to tmp_path."""
    from dashboard.api import create_app
    return create_app(project_dir=tmp_path, project_token=None)


@pytest.fixture
def client(app_with_project):
    return TestClient(app_with_project, raise_server_exceptions=False)


class TestSSEContentType:
    def test_content_type_is_event_stream(self, client):
        """GET /api/events/missions returns text/event-stream content type."""
        with client.stream("GET", "/api/events/missions") as response:
            assert "text/event-stream" in response.headers["content-type"]
            # Read just the first chunk (connected event)
            for _ in response.iter_lines():
                break


class TestSSEConnectedEvent:
    def test_first_event_is_connected(self, client):
        """The first SSE event received is the connected handshake."""
        lines = []
        with client.stream("GET", "/api/events/missions") as response:
            for line in response.iter_lines():
                lines.append(line)
                if "" == line:  # blank line ends an event
                    break

        event_lines = [l for l in lines if l.startswith("event:")]
        data_lines = [l for l in lines if l.startswith("data:")]
        assert any("connected" in l for l in event_lines)
        assert len(data_lines) == 1
        payload = json.loads(data_lines[0].removeprefix("data:").strip())
        assert payload["version"] == "1"
        assert "ts" in payload


class TestSSEProjectDirNotConfigured:
    def test_returns_503_when_project_dir_missing(self, tmp_path):
        """Returns HTTP 503 if project_dir is not set."""
        from dashboard.api import create_app
        missing = tmp_path / "nonexistent"
        app = create_app(project_dir=missing, project_token=None)
        with TestClient(app) as client:
            response = client.get("/api/events/missions")
            assert response.status_code == 503


class TestSSELastEventID:
    def test_invalid_last_event_id_falls_back_to_live_tail(self, client):
        """Invalid Last-Event-ID header is silently ignored (no error, no replay)."""
        with client.stream(
            "GET",
            "/api/events/missions",
            headers={"Last-Event-ID": "not-a-valid-ulid"},
        ) as response:
            assert response.status_code == 200
            for line in response.iter_lines():
                if line.startswith("event:"):
                    assert "connected" in line
                    break

    def test_valid_last_event_id_skips_earlier_events(self, tmp_path):
        """Events with event_id <= last_event_id are skipped."""
        # Create a status.events.jsonl with two events
        feature_dir = tmp_path / "kitty-specs" / "test-mission"
        feature_dir.mkdir(parents=True)

        # Two events with known ULIDs (lexicographic order = chronological)
        ulid_a = "01KQSXDAAAAAAAAAAAAAAAAAAA"
        ulid_b = "01KQSXDABBBBBBBBBBBBBBBBB"

        events_file = feature_dir / "status.events.jsonl"
        events_file.write_text(
            json.dumps({
                "event_id": ulid_a, "wp_id": "WP01",
                "from_lane": "planned", "to_lane": "in_progress",
                "actor": "claude", "at": "2026-01-01T00:00:00Z",
                "feature_slug": "test-mission",
            }) + "\n" +
            json.dumps({
                "event_id": ulid_b, "wp_id": "WP01",
                "from_lane": "in_progress", "to_lane": "for_review",
                "actor": "claude", "at": "2026-01-01T00:01:00Z",
                "feature_slug": "test-mission",
            }) + "\n"
        )

        from dashboard.api import create_app
        app = create_app(project_dir=tmp_path, project_token=None)
        received_ids = []
        with TestClient(app).stream(
            "GET", "/api/events/missions",
            headers={"Last-Event-ID": ulid_a},
        ) as response:
            for line in response.iter_lines():
                if line.startswith("id:"):
                    received_ids.append(line.removeprefix("id:").strip())
                if len(received_ids) >= 2:
                    break

        # Event A should NOT be in received_ids (it was skipped)
        assert ulid_a not in received_ids
        # Event B SHOULD be in received_ids
        assert ulid_b in received_ids


class TestSSEReadOnly:
    def test_post_not_allowed(self, client):
        """POST /api/events/missions is not an allowed method (C-004)."""
        response = client.post("/api/events/missions")
        assert response.status_code in (404, 405)

    def test_no_mutation_calls_triggered(self, client):
        """GET /api/events/missions does not trigger any write operations."""
        # This is a design check: verify the endpoint only calls read_events, not emit_status_transition
        with patch("specify_cli.status.emit.emit_status_transition") as mock_emit:
            with client.stream("GET", "/api/events/missions") as response:
                for line in response.iter_lines():
                    if "connected" in line:
                        break
            mock_emit.assert_not_called()
```

2. Run: `cd src && pytest ../tests/test_dashboard/test_sse_endpoint.py -v`

3. Fix any test failures. Common issues:
   - `create_app` signature differs → check `src/dashboard/api/__init__.py`
   - `iter_lines()` vs `iter_text()` on the streaming response → adjust to match TestClient API
   - The `status.events.jsonl` format may differ from the hand-written JSON above → check `StatusEvent` model and `read_events()` format

**Files:** `tests/test_dashboard/test_sse_endpoint.py` (new)

**Validation:**
- [x] `pytest tests/test_dashboard/test_sse_endpoint.py -v` passes
- [x] `connected` event test passes
- [x] `Last-Event-ID` skip test passes
- [x] Read-only semantics test passes (no `emit_status_transition` called)
- [x] Content-type test passes

---

## Definition of Done

- [x] `src/dashboard/api/routers/events.py` exists with `router` and `GET /api/events/missions`
- [x] First event emitted is `connected` with `version` and `ts` fields
- [x] `mission_status` events include all 8 fields from `contracts/sse-events.md` section 4.2
- [x] Keepalive comment `": keepalive\n\n"` is sent every 15 seconds when idle
- [x] `Last-Event-ID` header is read, ULID-validated, and used to skip already-seen events
- [x] Invalid `Last-Event-ID` falls back to live-tail silently
- [x] Events router is registered in `src/dashboard/api/__init__.py`
- [x] `GET /api/events/missions` returns `text/event-stream` content type
- [x] No new package dependencies added (Starlette `StreamingResponse` only)
- [x] `tests/test_dashboard/test_sse_endpoint.py` passes

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `StatusEvent` attribute names differ from the SSE contract payload fields | High | T038 explicitly checks `StatusEvent` attributes before writing the payload dict |
| Client disconnect causes exception in generator body | Medium | The generator uses only `asyncio.sleep` and `Path.read_text()`; both are safe to interrupt |
| `asyncio.get_event_loop()` deprecated in Python 3.10+ | Low | Replace with `asyncio.get_running_loop()` inside the async generator |
| TestClient SSE streaming API differs between httpx versions | Low | Use `client.stream("GET", ...)` with `response.iter_lines()` — standard httpx pattern |
| ULID comparison fails for events with non-standard formats | Low | The ULID regex validator in T040 rejects non-conforming headers before the generator runs |

## Reviewer Guidance

1. Read `contracts/sse-events.md` and verify the wire format emitted by `_stream_mission_events` matches exactly (event names, data field names, `id:` field).
2. Confirm `_stream_mission_events` opens and closes files within each polling tick (no persistent file handles across `yield`).
3. Confirm `X-Accel-Buffering: no` header is set (prevents nginx buffering).
4. Run the integration tests and confirm all pass.
5. Check that `POST /api/events/missions` returns 404 or 405 (C-004: read-only).
6. Verify `_KEEPALIVE_INTERVAL_S = 15` and `_POLL_INTERVAL_S = 2` are constants (not magic numbers inline).

Implement command: `spec-kitty agent action implement WP08 --agent <name>`

## Activity Log

- 2026-05-04T18:31:18Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=2035673 – Started implementation via action command
- 2026-05-04T18:35:30Z – copilot:claude-sonnet-4-6:alphonso:implementer – shell_pid=2035673 – SSE endpoint created with keepalive, Last-Event-ID resumption, and integration tests
- 2026-05-04T18:36:01Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=2041398 – Started review via action command
- 2026-05-04T18:38:28Z – copilot:claude-sonnet-4-6:alphonso:reviewer – shell_pid=2041398 – Review passed: SSE endpoint with StreamingResponse, keepalive, Last-Event-ID resumption, 12 integration tests, 338 tests pass
