# WebSocket Token Endpoint

**Endpoint**: `POST https://api.spec-kitty.com/api/v1/ws-token`  
**Purpose**: Obtain ephemeral token for WebSocket upgrade  
**Authentication**: Bearer token (via `Authorization` header)  
**Content-Type**: `application/json`

---

## Request

### Headers
```
POST /api/v1/ws-token HTTP/1.1
Host: api.spec-kitty.com
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
```

### Body

```json
{
  "session_id": "sess_01HR6CYJK..."
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session ID from token response (ULID format) |

### Field Constraints
- `session_id`: non-empty ULID string (must match session in tokens)

---

## Response

### Success (200 OK)

**Status**: 200 OK  
**Content-Type**: `application/json`

```json
{
  "ws_token": "wst_ephemeral_xyz...",
  "expires_in": 300,
  "message": "WebSocket token issued"
}
```

### Response Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `ws_token` | string | Ephemeral token for WebSocket authentication (opaque) |
| `expires_in` | integer | Token lifetime in seconds (typically `300` = 5 minutes) |
| `message` | string | Human-readable confirmation |

### Field Constraints
- `ws_token`: opaque string; never empty
- `expires_in`: positive integer; typically 300 seconds (5 minutes)

---

## Error Responses

### Invalid Session (400 Bad Request)

```json
{
  "error": "invalid_session",
  "error_description": "Session ID not found or revoked"
}
```

**When**: Session ID does not exist or was logged out

### Missing Session ID (400 Bad Request)

```json
{
  "error": "invalid_request",
  "error_description": "Missing required field: session_id"
}
```

**When**: Request body missing `session_id` field

### Authentication Failure (401 Unauthorized)

```json
{
  "error": "invalid_token",
  "error_description": "Access token is invalid or expired"
}
```

**When**: Authorization header missing or token invalid

### Server Error (500 Internal Server Error)

```json
{
  "error": "server_error",
  "error_description": "Internal server error"
}
```

**When**: Transient server failure; CLI should retry with backoff

---

## WebSocket Upgrade

**After obtaining `ws_token`, CLI upgrades to WebSocket**:

### WebSocket Connection Request
```
GET /api/v1/ws?token=<ws_token> HTTP/1.1
Host: api.spec-kitty.com
Upgrade: websocket
Connection: Upgrade
```

### WebSocket Handshake Headers
```
GET /api/v1/ws?token=<ws_token> HTTP/1.1
Host: api.spec-kitty.com:443
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: <base64-encoded-16-bytes>
Sec-WebSocket-Version: 13
```

### Token Location
- Passed as **query parameter**: `?token=<ws_token>`
- NOT in headers (WebSocket upgrade does not allow `Authorization` header)
- Single-use: token is consumed on successful handshake

---

## Pre-Connect Refresh Logic

**TokenManager pre-connect behavior**:

1. **Before any WebSocket connection**, TokenManager checks access token expiry
2. **If access token expires within 5 minutes**:
   - Call `/oauth/token` with `refresh_token` to obtain new access token
   - Update stored session with new tokens
   - Proceed with WebSocket upgrade
3. **If access token still valid** (>5 min lifetime remaining):
   - Skip refresh; proceed immediately to `/api/v1/ws-token`
4. **Result**: WebSocket connection uses fresh tokens (access token valid for ≥5 min)

**Refresh flow before WebSocket**:
```
[WebSocket Needed]
    │
    ├──→ Check access_token_expires_at
    │    │
    │    ├──→ Expires within 5 min
    │    │    └──→ POST /oauth/token (refresh_token grant)
    │    │        ├──→ Success: update stored session, proceed
    │    │        └──→ Fail: session_invalid, force re-login
    │    │
    │    └──→ Valid for >5 min: skip refresh
    │
    ├──→ POST /api/v1/ws-token
    │    └──→ Receive ws_token (ephemeral)
    │
    └──→ WebSocket GET with ?token=ws_token
         └──→ SaaS validates ws_token and establishes connection
```

---

## Token Lifecycle

**WebSocket token**:
- Issued by `/api/v1/ws-token` endpoint
- Lifetime: typically 5 minutes (`expires_in=300`)
- Single-use: consumed on WebSocket upgrade handshake
- Not stored: ephemeral, used once then discarded
- Never transmitted to SaaS API after WebSocket connects (session_id used instead)

**Access token** (for `/api/v1/ws-token` call):
- Must be valid at request time
- May expire during WebSocket session (SaaS handles in-flight)
- Refresh happens pre-connect (CLI side) or on 401 (SaaS side)

---

## Concurrent WebSocket Scenarios

**Multiple WebSocket connections**:
- Each requires separate `/api/v1/ws-token` call
- Each gets unique ephemeral token
- Each token is single-use
- Safe to obtain multiple tokens concurrently

**Token refresh coordination**:
- If multiple threads/tasks need WebSocket pre-connect refresh:
  - TokenManager uses asyncio.Lock (single-flight refresh)
  - First caller refreshes; others wait for result
  - All proceed with refreshed token once ready
  - Prevents thundering herd on token endpoint

---

## CLI Integration Points

1. **WebSocket connection needed** (e.g., live tracker update)
2. **TokenManager._ensure_fresh()**: Check access token expiry; refresh if needed
3. **POST /api/v1/ws-token**: Obtain ephemeral token
4. **WebSocket GET upgrade**: Include token as query parameter
5. **On successful upgrade**: WebSocket connection authenticated and ready
6. **On failure** (invalid token, expired, etc.): Force re-login and retry

---

## Security Notes

- **Token is ephemeral**: Single-use, short-lived (5 min), consumed on upgrade
- **Query parameter**: WebSocket upgrade cannot use `Authorization` header (WebSocket spec limitation)
- **HTTPS required**: WebSocket upgrade is `wss://` (WSS over TLS)
- **No client secret**: Session authentication only (via token)
- **Access token refresh pre-connect**: Ensures fresh credentials before upgrade

---

## Rate Limiting

Not typically rate-limited (low-frequency operation).

---

## Notes

- **Requires valid session**: Must be authenticated (access token valid)
- **Session ID must match**: `session_id` must be from current session
- **Access token refresh automatic**: Pre-connect refresh happens transparently to user
- **WebSocket token is single-use**: Consumed on upgrade, cannot be reused
- **Ephemeral token TTL**: Typically 5 minutes; CLI should obtain fresh token for each WebSocket connection
