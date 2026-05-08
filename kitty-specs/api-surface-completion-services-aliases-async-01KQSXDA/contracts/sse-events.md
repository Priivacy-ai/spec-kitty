# SSE Contract — `GET /api/events/missions`

Mission: `api-surface-completion-services-aliases-async-01KQSXDA`
FR refs: FR-009, FR-010, FR-011, FR-012

---

## 1. Endpoint Overview

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/api/events/missions` |
| Protocol | HTTP/1.1 |
| Media type | `text/event-stream` (Server-Sent Events, [WHATWG spec](https://html.spec.whatwg.org/multipage/server-sent-events.html)) |
| Direction | Server → client only (read-only; C-004) |
| Authentication | Project token (same as other dashboard routes; no auth in localhost-only deployments) |

---

## 2. HTTP Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Accept: text/event-stream` | Recommended | Standard SSE negotiation header |
| `Last-Event-ID: <ulid>` | Optional | Resume from a specific event. Value is a 26-character ULID from a prior session. |
| `Cache-Control: no-cache` | Recommended | Prevents proxy caching of the stream |

### Example Request

```http
GET /api/events/missions HTTP/1.1
Host: localhost:8765
Accept: text/event-stream
Cache-Control: no-cache
Last-Event-ID: 01KQSXDB0000000000000000AB
```

---

## 3. HTTP Response Headers

| Header | Value | Description |
|--------|-------|-------------|
| `Content-Type` | `text/event-stream; charset=utf-8` | Required for SSE |
| `Cache-Control` | `no-cache` | Prevents proxy/CDN buffering |
| `Connection` | `keep-alive` | Required for long-lived streams |
| `X-Accel-Buffering` | `no` | Disables nginx proxy buffering; prevents events from being held |
| `Transfer-Encoding` | `chunked` | Implicit for streaming responses in HTTP/1.1 |

### Example Response (start of stream)

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

---

## 4. Wire Format — Event Types

The SSE wire format uses `\n` line endings. Each event is terminated by a blank line (`\n\n`).

### 4.1 `connected` Event

Sent immediately when the HTTP connection is established, before any domain events.
Clients can use this to detect that the stream is live.

```
event: connected
data: {"version": "1", "ts": "2026-07-01T12:00:00+00:00"}
id: 01KQSXDAAAAAAAAAAAAAAAAAA

```

| Field | Type | Description |
|-------|------|-------------|
| `version` | `str` | Protocol version string, always `"1"` for this mission |
| `ts` | `str` | ISO-8601 UTC timestamp at connection time |

The `id:` field is a server-generated ULID. It is not useful for `Last-Event-ID` resumption (no domain events precede it) but is included for wire format consistency.

### 4.2 `mission_status` Event

Emitted for each `StatusEvent` appended to any mission's `status.events.jsonl`.

```
event: mission_status
data: {"mission_id": "01J6XW9KABCDE01234567890AB", "mission_slug": "083-my-mission", "wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress", "actor": "claude", "at": "2026-07-01T12:01:00+00:00", "event_id": "01KQSXDB0000000000000000AB"}
id: 01KQSXDB0000000000000000AB

```

Data payload fields:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `mission_id` | `str` | `StatusEvent.mission_id` | ULID — canonical mission identity |
| `mission_slug` | `str` | `StatusEvent.mission_slug` | Human slug (e.g. `083-my-mission`) |
| `wp_id` | `str` | `StatusEvent.wp_id` | Work package ID (e.g. `WP01`) |
| `from_lane` | `str` | `StatusEvent.from_lane` | Source lane value (e.g. `planned`) |
| `to_lane` | `str` | `StatusEvent.to_lane` | Target lane value (e.g. `in_progress`) |
| `actor` | `str` | `StatusEvent.actor` | Agent or user that triggered the transition |
| `at` | `str` | `StatusEvent.at` | ISO-8601 timestamp from the event log |
| `event_id` | `str` | `StatusEvent.event_id` | ULID — also used as the SSE `id:` field |

The SSE `id:` field is always set to `event_id`. This is the value the client must send back as `Last-Event-ID` on reconnect to resume the stream.

### 4.3 Keepalive Comment

Sent every **15 seconds** when no domain events are available.

```
: keepalive

```

Comments (lines starting with `:`) are defined in the SSE specification as ignored by the `EventSource` API's `onmessage` handler. They do not reset the `retry` timer on the client but they do prevent proxy timeouts and browser-side "connection closed" detection. The 15-second interval is below the typical 30-second proxy/browser idle timeout.

---

## 5. `Last-Event-ID` Resumption Behaviour

### Client responsibility

On reconnect (network drop or browser page reload), the browser's native `EventSource` API automatically re-sends the `Last-Event-ID` header with the `id:` value from the last received event. `curl` callers must pass the header manually.

### Server behaviour on reconnect

1. The handler reads the `Last-Event-ID` header value from the incoming request.
2. If present and valid (26-char ULID): call `read_events(feature_dir)` from `specify_cli.status.store` across all watched missions, and collect all events whose `event_id` is **lexicographically greater than** the received ULID. ULIDs sort chronologically by construction.
3. Emit the backlogged events (in chronological order) as `mission_status` events before entering the live-tail polling loop.
4. If the `Last-Event-ID` is absent, malformed, or not found in the event log: start from the live tail (no replay).

### Replay guarantee

The server provides a **best-effort replay**: events that have already been garbage-collected (if any log rotation is implemented in future) will not be replayed. Within the retention window the replay is complete and in-order. Clients must be idempotent with respect to duplicate events (a reconnect that overlaps is possible if the client's `Last-Event-ID` exactly matches the most-recent event).

---

## 6. Client Disconnect / Resource Cleanup Guarantee (NFR-004)

When the client disconnects (TCP close, browser tab close, `curl` Ctrl-C), the ASGI framework detects the disconnect on the next `await` point in the async generator body. The generator will be garbage-collected by Python, releasing:

- Any open file handles to `status.events.jsonl`
- Any `asyncio.sleep` tasks in the polling loop

**Implementation requirement:** The async generator body must not hold persistent resources between `yield` points. File reads must be opened, consumed, and closed within each polling tick (standard `Path.read_text()` is sufficient; no persistent file handles). This ensures resource cleanup is bounded by the polling interval (≤ 15 s) after disconnect.

**No background threads:** The polling loop uses `asyncio.sleep` only. No `threading.Thread` or `concurrent.futures` executors are created, so there is no thread leak on disconnect.

---

## 7. Error Cases

### 7.1 Server-side exception during streaming

If a Python exception is raised inside the async generator **after** the `connected` event has been emitted (i.e., after the HTTP 200 response headers are sent):

- The ASGI server cannot change the response status code.
- The server logs the exception at `ERROR` level.
- The async generator exits, causing the HTTP connection to close.
- The client's `EventSource` will detect the close and schedule a reconnect after the `retry:` interval (default 3 seconds in browsers; the server does not customise this).

**Error event (optional, not required):** Implementations MAY emit a final SSE error event before closing:

```
event: error
data: {"code": "internal_error", "message": "Stream interrupted. Reconnect to resume."}

```

This event is informational only. Clients should not depend on it being present (the stream may close abruptly on hard crashes).

### 7.2 Project directory unavailable

If `request.app.state.project_dir` is not set or does not exist when the request arrives (before any streaming begins):

- The handler raises `HTTPException(status_code=503, detail="project_dir not configured")`.
- FastAPI converts this to a standard JSON error response (HTTP 503, before any `text/event-stream` bytes are written).
- No `connected` event is emitted.

### 7.3 Client sends invalid `Last-Event-ID`

If the `Last-Event-ID` header value is present but is not a valid 26-char ULID:

- The server logs a `DEBUG`-level warning.
- The server silently falls back to live-tail mode (no replay).
- No error is sent to the client.

---

## 8. Retry and Reconnect

The server does not customise the SSE `retry:` field. Browsers default to 3 seconds between reconnect attempts. If a custom retry interval is needed in future, add:

```
retry: 5000

```

in the `connected` event (value is in milliseconds).
