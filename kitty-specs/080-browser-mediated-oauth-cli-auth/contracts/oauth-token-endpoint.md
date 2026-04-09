# OAuth 2.0 Token Endpoint

**Endpoint**: `POST https://api.spec-kitty.com/oauth/token`  
**RFC**: RFC 6749 (OAuth 2.0), RFC 7636 (PKCE), RFC 8628 (Device Flow)  
**Content-Type**: `application/x-www-form-urlencoded`  
**Flow**: All flows (Authorization Code, Device Code, Refresh Token)

---

## Request

### Headers
```
POST /oauth/token HTTP/1.1
Host: api.spec-kitty.com
Content-Type: application/x-www-form-urlencoded
Accept: application/json
```

### Common Parameters (All Requests)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | string | Yes | CLI OAuth client ID (format: `cli_<id>`) |
| `grant_type` | string | Yes | One of: `authorization_code`, `device_code`, `refresh_token` |

---

## Grant Type: `authorization_code`

**Purpose**: Exchange authorization code for tokens (final step of browser-based login)

### Request Body
```
POST /oauth/token HTTP/1.1
Host: api.spec-kitty.com
Content-Type: application/x-www-form-urlencoded

client_id=cli_abc123&
grant_type=authorization_code&
code=authcode_xyz789&
redirect_uri=http://localhost:8080/callback&
code_verifier=<43-char-pkce-verifier>
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | string | Yes | CLI OAuth client ID |
| `grant_type` | string | Yes | Must be `authorization_code` |
| `code` | string | Yes | Authorization code from `/oauth/authorize` callback |
| `redirect_uri` | string | Yes | Must match redirect URI used in `/oauth/authorize` request |
| `code_verifier` | string | Yes | PKCE verifier (43 ASCII characters; RFC 7636) |

### Field Constraints
- `code`: opaque string, single-use, 5–10 minute lifetime
- `redirect_uri`: must be exact match to authorization request
- `code_verifier`: exactly 43 characters (unreserved ASCII chars per RFC 7636)

---

## Grant Type: `device_code`

**Purpose**: Polling request for device code approval (headless flow)

### Request Body
```
POST /oauth/token HTTP/1.1
Host: api.spec-kitty.com
Content-Type: application/x-www-form-urlencoded

client_id=cli_abc123&
grant_type=device_code&
device_code=DEVICE_ABC123XYZ789
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | string | Yes | CLI OAuth client ID |
| `grant_type` | string | Yes | Must be `device_code` |
| `device_code` | string | Yes | Device code from `/oauth/device` response |

### Polling Behavior
- CLI calls this endpoint repeatedly every `interval` seconds (from `/oauth/device` response)
- Returns `200 OK` with tokens when user approves
- Returns `400 Bad Request` with error `authorization_pending` while awaiting approval
- Returns `400 Bad Request` with error `access_denied` if user denies
- Returns `400 Bad Request` with error `expired_token` if device code has expired

---

## Grant Type: `refresh_token`

**Purpose**: Obtain new access token using refresh token (keep session alive)

### Request Body
```
POST /oauth/token HTTP/1.1
Host: api.spec-kitty.com
Content-Type: application/x-www-form-urlencoded

client_id=cli_abc123&
grant_type=refresh_token&
refresh_token=rf_<refresh-token>
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | string | Yes | CLI OAuth client ID |
| `grant_type` | string | Yes | Must be `refresh_token` |
| `refresh_token` | string | Yes | Refresh token from prior token response |

---

## Response (All Grant Types)

### Success (200 OK)

**Status**: 200 OK  
**Content-Type**: `application/json`

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "refresh_token": "rf_5C4E9...",
  "expires_in": 3600,
  "refresh_token_expires_in": 7776000,
  "refresh_token_expires_at": "2026-07-08T13:37:14Z",
  "scope": "offline_access api.read api.write",
  "session_id": "sess_01HR6CYJK..."
}
```

### Response Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `access_token` | string | Bearer token for API calls (opaque or JWT) |
| `token_type` | string | Always `Bearer` (RFC 6750) |
| `refresh_token` | string | Long-lived token for renewal; TTL surfaced via `refresh_token_expires_in` / `refresh_token_expires_at` (landed 2026-04-09) |
| `expires_in` | integer | Access token lifetime in seconds (typically `3600` = 1 hour) |
| `refresh_token_expires_in` | integer | Refresh token TTL in seconds, from the server clock at issue time. Landed 2026-04-09 per `saas-amendment-refresh-ttl.md`. |
| `refresh_token_expires_at` | ISO 8601 string | Absolute refresh token expiry timestamp (UTC). Source of truth for session-end UX; CLI stores this verbatim without local clock math. Landed 2026-04-09. |
| `scope` | string | Space-separated scopes granted; must include `offline_access` |
| `session_id` | string | Server-side session identifier (ULID format, non-empty) |

### Field Constraints
- `access_token`: opaque string or JWT; never empty
- `token_type`: always `Bearer` (no alternatives)
- `refresh_token`: opaque string; never empty
- `expires_in`: positive integer; typically 3600 (1 hour) for access tokens
- `refresh_token_expires_in`: positive integer; MUST be ≥ `expires_in` (refresh outlives access)
- `refresh_token_expires_at`: ISO 8601 timestamp in UTC; MUST be a valid future datetime at issue time
- `scope`: must include `offline_access` for refresh token to be valid
- `session_id`: ULID format (non-empty), used for logout and session tracking

---

## Error Responses

See `error-responses.md` for standardized error codes.

### Authorization Code / Refresh Token Errors (400 Bad Request)

```json
{
  "error": "invalid_grant",
  "error_description": "Authorization code has expired or was already used"
}
```

| Error | HTTP | Meaning |
|-------|------|---------|
| `invalid_request` | 400 | Missing or malformed parameters |
| `invalid_client` | 400 | Unknown or untrusted `client_id` |
| `invalid_grant` | 400 | Code/token invalid, expired, or already used |
| `invalid_scope` | 400 | Requested scope not available |
| `unauthorized_client` | 400 | Client not permitted to use this grant type |
| `unsupported_grant_type` | 400 | Unknown `grant_type` value |
| `server_error` | 500 | Transient server error; CLI should retry with backoff |

### Device Code Polling Errors (400 Bad Request)

**In progress (awaiting approval)**:
```json
{
  "error": "authorization_pending",
  "error_description": "User has not yet approved the device"
}
```

**User denied**:
```json
{
  "error": "access_denied",
  "error_description": "User denied the authorization request"
}
```

**Device code expired**:
```json
{
  "error": "expired_token",
  "error_description": "Device code has expired; request new code from /oauth/device"
}
```

---

## CLI Retry Behavior

**Transient errors** (`server_error`, `authorization_pending`):
- Device flow: retry after `interval` seconds (from `/oauth/device`)
- Token exchange: retry with exponential backoff (1s, 2s, 4s, …, max 60s)

**Terminal errors** (`invalid_grant`, `access_denied`, `expired_token`):
- Do not retry; notify user and require re-authentication

**Security-related errors** (`invalid_client`, `unauthorized_client`):
- Do not retry; likely client configuration issue

---

## Session Management

**Session lifetime**:
- Access token: ~1 hour (`expires_in = 3600`)
- Refresh token: SaaS-managed TTL, surfaced via `refresh_token_expires_in` / `refresh_token_expires_at` on every token response (see logout behavior)
- CLI extends session indefinitely by calling refresh before access-token expiry, and stores the server-supplied refresh expiry verbatim

**Logout**:
- CLI calls `POST /api/v1/logout` with `session_id` to invalidate session
- See `api-logout-endpoint.md` for logout contract

---

## Token Characteristics

**Access token**:
- Format: Opaque string or JWT (client must not parse JWT)
- Use: `Authorization: Bearer <access_token>` header in API calls
- Lifetime: ~1 hour (from `expires_in`)
- Validation: SaaS verifies validity on each API call

**Refresh token**:
- Format: Opaque string (never a JWT)
- Use: Sent to `/oauth/token` with `grant_type=refresh_token`
- Lifetime: SaaS-managed; CLI tracks via `refresh_token_expires_in` / `refresh_token_expires_at` (landed 2026-04-09)
- Storage: Secure storage backend (Keychain, file, etc.)
- Never: logged, cached in plaintext, or transmitted to API endpoints

**Session ID**:
- Format: ULID (unique identifier, sortable by timestamp)
- Use: Provided in token response; used for logout
- Lifetime: Tied to refresh token (valid until logout or expiry)

---

## Rate Limiting

**SaaS may apply rate limits** (TBD in SaaS contract):
- Typical: 100 requests/minute per client_id
- Typical: 10 requests/minute per IP for `/oauth/device`
- CLI should implement adaptive backoff on 429 responses

---

## Notes

- **No client secret used** (public client auth via PKCE for authorization code)
- **All requests must use HTTPS** (no HTTP exceptions)
- **Tokens are bearer tokens** (include in `Authorization: Bearer` header)
- **Refresh tokens are long-lived** (enable indefinite session renewal)
- **Session ID enables revocation** (logout invalidates all API calls immediately)
