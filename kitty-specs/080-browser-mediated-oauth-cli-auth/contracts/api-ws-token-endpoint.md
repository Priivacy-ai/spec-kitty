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
  "team_id": "tm_acme"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | Team ID to request WebSocket access for (from `/api/v1/me` teams array) |

### Field Constraints
- `team_id`: non-empty team identifier (must be one of user's teams from `/api/v1/me`)

---

## Response

### Success (200 OK)

**Status**: 200 OK  
**Content-Type**: `application/json`

```json
{
  "ws_token": "ws_eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 3600,
  "session_id": "sess_01HR6CYJK...",
  "ws_url": "wss://api.spec-kitty.com/ws"
}
```

### Response Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `ws_token` | string | Short-lived WebSocket auth token (opaque) |
| `expires_in` | integer | Token lifetime in seconds (typically `3600` = 1 hour) |
| `session_id` | string | Session ID (for audit and reference) |
| `ws_url` | string | WebSocket endpoint to connect to |

### Field Constraints
- `ws_token`: opaque string; never empty
- `expires_in`: positive integer; typically 3600 seconds (1 hour)
- `session_id`: session identifier from current session
- `ws_url`: fixed HTTPS WebSocket endpoint

---

## Error Responses

### Missing Team ID (400 Bad Request)

```json
{
  "error": "invalid_request",
  "error_description": "Missing required field: team_id"
}
```

**When**: Request body missing `team_id` field

### User Not Team Member (403 Forbidden)

```json
{
  "error": "forbidden",
  "error_description": "User is not a member of team tm_acme"
}
```

**When**: `team_id` is valid but user is not a member of that team

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

**After obtaining `ws_token` and `ws_url`, CLI upgrades to WebSocket**:

### WebSocket Connection Request
```
GET /ws?token=<ws_token> HTTP/1.1
Host: api.spec-kitty.com
Upgrade: websocket
Connection: Upgrade
```

### WebSocket Handshake Headers
```
GET /ws?token=<ws_token> HTTP/1.1
Host: api.spec-kitty.com:443
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: <base64-encoded-16-bytes>
Sec-WebSocket-Version: 13
```

### Token Location
- Passed as **query parameter**: `?token=<ws_token>` appended to `ws_url`
- NOT in headers (WebSocket upgrade does not allow `Authorization` header)
- Single-use: token is consumed on successful handshake

### Connection URL Formula
Use the `ws_url` from the `/api/v1/ws-token` response:
```
{ws_url}?token={ws_token}
```

**Example**:
```
wss://api.spec-kitty.com/ws?token=ws_eyJ0eXAi...
```

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
- Lifetime: typically 1 hour (`expires_in=3600`)
- Single-use on upgrade: consumed on WebSocket upgrade handshake
- Not stored: ephemeral, used once then discarded during upgrade
- Session binding: WebSocket session bound to `team_id` requested
- After upgrade: session_id used for subsequent WebSocket message authentication

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
