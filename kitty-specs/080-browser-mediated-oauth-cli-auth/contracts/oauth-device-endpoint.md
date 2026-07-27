# OAuth 2.0 Device Authorization Endpoint

**Endpoint**: `POST https://api.spec-kitty.com/oauth/device`  
**RFC**: RFC 8628 (Device Authorization Grant)  
**Flow**: Device Authorization Flow (headless fallback)  
**Content-Type**: `application/x-www-form-urlencoded`

---

## Request

### Headers
```
POST /oauth/device HTTP/1.1
Host: api.spec-kitty.com
Content-Type: application/x-www-form-urlencoded
Accept: application/json
```

### Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | string | Yes | CLI OAuth client ID (format: `cli_<id>`) |
| `scope` | string | Yes | Space-separated scopes (must include `offline_access`) |

**Example Request**:
```
POST /oauth/device HTTP/1.1
Host: api.spec-kitty.com
Content-Type: application/x-www-form-urlencoded

client_id=cli_abc123&scope=offline_access+api.read+api.write
```

---

## Response

### Success (200 OK)

**Status**: 200 OK  
**Content-Type**: `application/json`

```json
{
  "device_code": "DEVICE_ABC123XYZ789",
  "user_code": "ABCD-1234",
  "verification_uri": "https://api.spec-kitty.com/device",
  "expires_in": 900,
  "interval": 5
}
```

### Response Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `device_code` | string | Opaque device code used by CLI for polling (never show to user) |
| `user_code` | string | Human-readable code shown to user (format: `XXXX-XXXX`; 8 chars + hyphen) |
| `verification_uri` | string | URL user visits in browser to authorize (no parameters; fixed URL) |
| `expires_in` | integer | Device code lifetime in seconds (typically `900` = 15 minutes) |
| `interval` | integer | Recommended polling interval in seconds (typically `5`; CLI caps at `10`) |

### Field Constraints
- `device_code`: opaque string, ≥32 characters, URL-safe
- `user_code`: exactly 8 alphanumeric characters + hyphen (e.g., `ABCD-1234`)
- `verification_uri`: fixed HTTPS URL with no query parameters
- `expires_in`: positive integer, typically 900 seconds
- `interval`: positive integer ≥1 second; CLI applies max 10-second cap

---

## CLI Integration Points

1. **Request device code**: CLI calls `POST /oauth/device` with `client_id` and `scope`
2. **Display to user**: Show `user_code` and `verification_uri` ("Visit https://... and enter ABCD-1234")
3. **Start polling loop**: CLI polls `/oauth/token` with `device_code` every `interval` seconds (capped at 10s)
4. **Timeout**: If polling exceeds `expires_in` seconds without approval, stop and show "Device code expired"
5. **Approval handler**: When user approves in browser, `/oauth/token` returns tokens (see oauth-token-endpoint.md)

---

## Error Responses

See `error-responses.md` for standardized error codes. Common errors:

| Error | Description |
|-------|-------------|
| `invalid_request` | Missing or malformed parameters |
| `invalid_client` | Unknown or untrusted `client_id` |
| `invalid_scope` | Requested scope not available to client |
| `server_error` | Transient server error; user should retry |

**Example**:
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_client",
  "error_description": "Client not recognized"
}
```

---

## User Verification Flow (Separate Browser UI)

The `verification_uri` is a **fixed URL** that the SaaS provides; CLI does not construct it.

**User browser flow**:
1. User opens `https://api.spec-kitty.com/device` in browser
2. Prompted to enter `user_code` (e.g., "ABCD-1234")
3. SaaS looks up device by `user_code` and displays what the CLI is requesting
4. User approves (authenticates if needed)
5. SaaS marks device code as approved
6. CLI's polling loop receives approval at next poll

---

## Security Notes

- **Device code never exposed to user** (only `user_code` is shown)
- **User verification UI is SaaS responsibility** (not CLI)
- **No client secret required** (public client)
- **Scope must include `offline_access`** for refresh token issuance
- **Codes are single-use and time-limited** (prevent reuse attacks)

---

## Polling Behavior

See `oauth-token-endpoint.md` for polling request format and responses.

**Polling continues until one of**:
- `expires_in` seconds elapse (device code expires)
- User approves (tokens returned)
- User denies (error `access_denied`)
- Polling receives error `expired_token` (device code revoked)

---

## Notes

- This endpoint is called once per headless login session.
- Multiple CLI instances cannot share the same device code (polling is per-CLI instance).
- User verification UI is entirely SaaS-hosted; CLI only displays `user_code` and `verification_uri`.
