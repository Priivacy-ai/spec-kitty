# API Logout Endpoint

**Endpoint**: `POST https://api.spec-kitty.com/api/v1/logout`  
**Purpose**: Revoke session and invalidate all tokens  
**Authentication**: Bearer token (via `Authorization` header)  
**Idempotency**: Idempotent (safe to call multiple times)  
**Content-Type**: `application/json`

---

## Request

### Headers
```
POST /api/v1/logout HTTP/1.1
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
  "status": "logged_out",
  "session_id": "sess_01HR6CYJK...",
  "message": "Session successfully revoked"
}
```

### Response Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Always `"logged_out"` on success |
| `session_id` | string | Session ID that was revoked (echo of request) |
| `message` | string | Human-readable confirmation |

---

## Idempotency Behavior

**If session already logged out**:
- Return `200 OK` with same response body
- Do not return an error (idempotent)
- Safe to call multiple times

**Example**:
```json
{
  "status": "logged_out",
  "session_id": "sess_01HR6CYJK...",
  "message": "Session successfully revoked"
}
```

---

## Error Responses

### Invalid Session (400 Bad Request)

```json
{
  "error": "invalid_session",
  "error_description": "Session ID not found or already revoked"
}
```

**When**: Session ID does not exist or was already logged out

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

## Side Effects

**When logout succeeds**:
1. Session marked as revoked in SaaS database
2. All API calls using tokens from this session are rejected with HTTP 401
3. Refresh token becomes invalid (cannot be used to obtain new access tokens)
4. User must re-authenticate to obtain new tokens

**CLI side**:
1. Delete stored session from secure storage (Keychain/file/etc.)
2. Clear in-memory TokenManager cache
3. Transition to `NotAuthenticated` state
4. Next API call will require re-login

---

## CLI Integration Points

1. **User runs `spec-kitty auth logout`**: CLI reads session from storage
2. **Extract session_id**: From stored session (ULID from token response)
3. **Call logout endpoint**: POST to `/api/v1/logout` with session_id
4. **Cleanup**:
   - If success: delete stored session, clear TokenManager cache
   - If failure: attempt cleanup anyway; log warning
5. **Report to user**: "Successfully logged out" (or "Failed to revoke session, but local credentials removed")

---

## Logout Flow States

```
[Authenticated] (has valid access/refresh tokens)
    │
    ├──→ CLI calls POST /api/v1/logout
    │    │
    │    ├──→ 200 OK: Session revoked
    │    │         └──→ Delete stored session, clear TokenManager
    │    │             └──→ [NotAuthenticated]
    │    │
    │    ├──→ 401 Unauthorized: Access token expired
    │    │         └──→ TokenManager raises session_invalid
    │    │             └──→ [NotAuthenticated] (force re-login message)
    │    │
    │    └──→ Network error or 500: Cannot reach SaaS
    │             └──→ Local cleanup anyway (delete stored session)
    │                 └──→ [NotAuthenticated] (with warning message)
    │
    ↓
[NotAuthenticated]
```

---

## Semantics

**Logout is best-effort**:
- CLI **always** deletes local credentials (even if SaaS call fails)
- **Best case**: SaaS revokes session AND CLI deletes credentials
- **Fallback**: CLI deletes credentials (SaaS may log session as orphaned)
- **Never**: Keep credentials if logout call fails (security principle: trust local deletion)

**Idempotency**:
- Safe to call logout multiple times (returns `200 OK` every time)
- If called after session already logged out elsewhere, returns `200 OK`

---

## Token Revocation Notes

**Access tokens**:
- Invalidated immediately (SaaS rejects all API calls with that token)
- TTL-based caches may retain old token briefly (until expiry)
- WebSocket connections using that token are disconnected

**Refresh tokens**:
- Invalidated immediately (cannot be exchanged for new access token)
- Cannot resume session with revoked refresh token

**Session state**:
- All session data associated with `session_id` is marked revoked
- No further API calls can use tokens from this session

---

## Rate Limiting

Not typically rate-limited (logout is low-frequency operation).

---

## Notes

- **Endpoint requires authentication** (Bearer token from session being logged out)
- **Idempotent** (safe to retry on network failure)
- **No client secret required** (session authentication only)
- **Session revocation is immediate** (all API calls are rejected instantly)
- **CLI cleanup is mandatory** (happens whether SaaS call succeeds or fails)
