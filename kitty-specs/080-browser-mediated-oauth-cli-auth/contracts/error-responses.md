# Standardized Error Responses

**Purpose**: Define common error formats and codes across all OAuth and API endpoints  
**Format**: JSON (OAuth 2.0 compliant, RFC 6749)  
**HTTP Status**: Varies by error type (see table)

---

## Standard Error Response Format

### JSON Structure
```json
{
  "error": "error_code",
  "error_description": "Human-readable error message",
  "error_uri": "https://api.spec-kitty.com/docs/errors/error_code"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error` | string | Yes | Machine-readable error code (see codes below) |
| `error_description` | string | No | Human-readable description of the error |
| `error_uri` | string | No | URL to error documentation |

---

## Error Codes by HTTP Status

### 400 Bad Request

**Common causes**: Malformed request, missing parameters, invalid values

| Error Code | Description | Retry | Example |
|------------|-------------|-------|---------|
| `invalid_request` | Missing or malformed parameters | No | Missing `client_id` in request |
| `invalid_client` | Unknown or untrusted client | No | `client_id` not recognized by SaaS |
| `invalid_scope` | Requested scope not available | No | Requested scope `admin` not available to client |
| `invalid_grant` | Code/token invalid, expired, or reused | No | Authorization code already exchanged once |
| `invalid_redirect_uri` | Redirect URI not registered | No | `redirect_uri` mismatch from authorization request |
| `unauthorized_client` | Client not permitted to use this flow | No | Client not allowed for this `grant_type` |
| `unsupported_grant_type` | Unknown grant type | No | Unknown value for `grant_type` parameter |
| `access_denied` | User denied the request | No | User clicked "Deny" in browser |
| `authorization_pending` | Device code: awaiting user approval | Yes | User has not yet approved device |
| `expired_token` | Device code or token has expired | No | Device code exceeded `expires_in` window |
| `server_error` | Transient server error | Yes | Temporary SaaS outage |

**Example**:
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_grant",
  "error_description": "Authorization code has expired or was already used"
}
```

### 401 Unauthorized

**Common causes**: Missing or invalid authentication

| Error Code | HTTP | Description | Retry |
|------------|------|-------------|-------|
| `invalid_token` | 401 | Access token missing, invalid, or expired | No (refresh token and retry) |
| `insufficient_scope` | 401 | Token valid but insufficient scope for operation | No (request new scope) |
| `token_revoked` | 401 | Token revoked via logout or SaaS admin | No (force re-login) |

**Example**:
```json
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": "invalid_token",
  "error_description": "Access token is invalid or expired"
}
```

### 403 Forbidden

**Common causes**: User lacks permission for requested operation

| Error Code | HTTP | Description | Retry |
|------------|------|-------------|-------|
| `access_denied` | 403 | User lacks permission for this operation | No |
| `insufficient_scope` | 403 | Token scope insufficient for operation | No |

**Example**:
```json
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "access_denied",
  "error_description": "You do not have permission to access this resource"
}
```

### 429 Too Many Requests

**Common causes**: Rate limit exceeded

| Error Code | HTTP | Description | Retry |
|------------|------|-------------|-------|
| `rate_limited` | 429 | Too many requests from this client | Yes (with backoff) |

**Example**:
```json
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60

{
  "error": "rate_limited",
  "error_description": "Rate limit exceeded; retry after 60 seconds"
}
```

### 500 Internal Server Error

**Common causes**: Server-side failure (transient)

| Error Code | HTTP | Description | Retry |
|------------|------|-------------|-------|
| `server_error` | 500 | Transient server error | Yes (with backoff) |
| `temporarily_unavailable` | 500 | Service temporarily unavailable | Yes (with backoff) |

**Example**:
```json
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "error": "server_error",
  "error_description": "Internal server error; please try again later"
}
```

### 502 Bad Gateway

**Common causes**: Upstream service failure

| Error Code | HTTP | Description | Retry |
|------------|------|-------------|-------|
| `server_error` | 502 | Upstream service error | Yes (with backoff) |

### 503 Service Unavailable

**Common causes**: Scheduled maintenance or overload

| Error Code | HTTP | Description | Retry |
|------------|------|-------------|-------|
| `temporarily_unavailable` | 503 | Service temporarily unavailable | Yes (with backoff) |

---

## CLI Error Handling Strategy

### By Error Type

**Terminal Errors** (do not retry):
- `invalid_request`, `invalid_client`, `invalid_scope`, `invalid_grant`, `invalid_redirect_uri`
- `access_denied`, `insufficient_scope`, `unauthorized_client`, `unsupported_grant_type`
- `invalid_token` (on API call, not token endpoint)

**Action**: Show error to user, require re-authentication or manual intervention

**Retryable Errors** (retry with backoff):
- `authorization_pending` (device flow polling)
- `server_error`, `temporarily_unavailable` (transient failures)
- `rate_limited` (rate limiting)

**Action**: Retry with exponential backoff (1s, 2s, 4s, …, max 60s)

**Refresh Errors** (on 401 API response):
- If `access_token_expired`: auto-refresh via `refresh_token` and retry request (1x)
- If `session_invalid`: force re-login, delete stored session
- If other 401: generic error handling

---

## Retry Strategy

### Exponential Backoff
```python
# For transient errors
backoff_seconds = min(60, 2 ** attempt_count)  # 1, 2, 4, 8, ..., 60
time.sleep(backoff_seconds + random(0, 1))    # Add jitter
```

### Max Retries
- **OAuth token endpoint**: 5 retries (5 minutes max with backoff)
- **Device flow polling**: Continue until `expires_in` exceeded
- **API calls**: 1 retry after token refresh

### Rate Limit Handling
- **Check Retry-After header** if present (prefer over backoff)
- **If Retry-After present**: wait that duration
- **If absent**: use exponential backoff

---

## OAuth 2.0 Error Code Reference

**Standard codes** (RFC 6749):
- `invalid_request`, `invalid_client`, `invalid_scope`, `invalid_grant`, `invalid_redirect_uri`
- `unauthorized_client`, `unsupported_grant_type`, `access_denied`

**Device flow codes** (RFC 8628):
- `authorization_pending`, `access_denied`, `expired_token`

**Custom codes** (spec-kitty extensions):
- `insufficient_scope`, `token_revoked`, `rate_limited`, `temporarily_unavailable`

---

## Device Flow Polling Errors

**During device code polling**, specific error codes guide retry strategy:

| Error | Meaning | CLI Action |
|-------|---------|-----------|
| `authorization_pending` | User hasn't approved yet | Wait `interval` seconds, retry |
| `access_denied` | User denied authorization | Stop polling, show "Authorization denied" |
| `expired_token` | Device code expired | Stop polling, show "Device code expired; run login again" |
| `server_error` | Transient failure | Retry with backoff |

---

## API Call Errors (401 Responses)

**When CLI receives 401 response on API call**:

```json
{
  "error": "access_token_expired",
  "error_description": "Access token has expired"
}
```

**or**

```json
{
  "error": "session_invalid",
  "error_description": "Session has been revoked or invalidated"
}
```

**CLI behavior**:

| Error | Action |
|-------|--------|
| `access_token_expired` | Refresh via `/oauth/token`, retry request (1x) |
| `session_invalid` | Delete session, show "Session expired; run login again" |
| Other `401` | Show error, require re-login |

---

## HTTP Status Summary

| Status | Use Case | Examples |
|--------|----------|----------|
| 200 | Success (all endpoints) | Token obtained, logout complete, etc. |
| 302 | Redirect (authorization endpoint) | Redirect to callback with code |
| 400 | Client error (bad request) | Malformed request, invalid grant, access denied |
| 401 | Auth failure | Missing/invalid token, expired token |
| 403 | Permission denied | Insufficient scope |
| 429 | Rate limited | Too many requests |
| 500 | Server error (transient) | Internal failure, retry recommended |
| 502 | Bad gateway | Upstream failure, retry recommended |
| 503 | Unavailable | Maintenance, retry recommended |

---

## Notes

- **All errors are JSON** (never HTML error pages)
- **Field descriptions are advisory** (may vary; use `error` code as canonical)
- **Retry logic should be smart**: Different codes have different retry strategies
- **Rate limiting headers**: Include `Retry-After` if present; use for backoff timing
- **Device flow**: `authorization_pending` is expected and normal; continue polling
- **401 on API vs. auth endpoint**: Different semantics; see "API Call Errors" above
