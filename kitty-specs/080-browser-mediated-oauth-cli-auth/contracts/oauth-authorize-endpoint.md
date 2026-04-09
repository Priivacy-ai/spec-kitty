# OAuth 2.0 Authorization Endpoint

**Endpoint**: `POST https://api.spec-kitty.com/oauth/authorize`  
**RFC**: RFC 6749 (OAuth 2.0), RFC 7636 (PKCE)  
**Flow**: Authorization Code + PKCE  
**Client Type**: Public (browser callback to localhost loopback)

---

## Request

### URL Parameters
None. All parameters in request body or query string per RFC 6749.

### Query String Format (Recommended for browser redirect)

```
GET https://api.spec-kitty.com/oauth/authorize?
  client_id=cli_<client-id>&
  redirect_uri=http://localhost:8080/callback&
  response_type=code&
  scope=offline_access+api.read+api.write&
  state=<128-bit-random-base64url>&
  code_challenge=<SHA256-base64url>&
  code_challenge_method=S256
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | string | Yes | CLI OAuth client ID (format: `cli_<id>`) |
| `redirect_uri` | string | Yes | Loopback callback URL (must be `http://localhost:PORT/callback`) |
| `response_type` | string | Yes | Must be `"code"` (authorization code flow) |
| `scope` | string | Yes | Space-separated scopes; must include `offline_access` |
| `state` | string | Yes | CSRF nonce (≥128 bits entropy, base64url-encoded) |
| `code_challenge` | string | Yes | SHA256(code_verifier) base64url-encoded (RFC 7636) |
| `code_challenge_method` | string | Yes | Must be `"S256"` (SHA256); `"plain"` not supported |

### Scope Values

Standard scopes for CLI:
- `offline_access` — **REQUIRED**; enables refresh token issuance
- `api.read` — Read access to API resources
- `api.write` — Write access to API resources

Example: `offline_access api.read api.write`

---

## Response

### Success (302 Redirect)

**Status**: 302 Found

**Location Header**:
```
http://localhost:8080/callback?
  code=<authorization-code>&
  state=<echo-original-state>
```

### Response Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | string | Authorization code (opaque, 5–10 min lifetime) |
| `state` | string | Echo of request `state` parameter (for CSRF validation) |

**Example**:
```
HTTP/1.1 302 Found
Location: http://localhost:8080/callback?code=authcode_abc123def456&state=base64url_state_value
```

### Code Validation Rules
- Authorization code is **single-use** (cannot be exchanged twice)
- Lifetime: 5–10 minutes from issuance
- Must be exchanged at `/oauth/token` with matching `code_verifier`

---

## Error Responses

See `error-responses.md` for standardized error codes. Common errors:

| Error | Description |
|-------|-------------|
| `invalid_request` | Missing/malformed parameters (e.g., no `client_id`) |
| `invalid_client` | Unknown or untrusted `client_id` |
| `invalid_scope` | Requested scope not available to client |
| `invalid_redirect_uri` | `redirect_uri` not registered for this client |
| `unauthorized_client` | Client not permitted to use this flow |
| `server_error` | Transient server error; user should retry |
| `access_denied` | User denied authorization in browser |

**Example**:
```
HTTP/1.1 302 Found
Location: http://localhost:8080/callback?
  error=access_denied&
  error_description=User+declined+authorization&
  state=base64url_state_value
```

---

## CLI Integration Points

1. **Launch browser**: CLI constructs authorization URL and opens browser with `start_browser(auth_url)`
2. **Loopback callback**: CLI listens on `localhost:PORT` and captures `code` + `state`
3. **State validation**: CLI verifies `state` matches original PKCE state
4. **Code exchange**: CLI calls `/oauth/token` with `code` + `code_verifier`
5. **Timeout**: If no callback within 5 minutes, authorization request expires (show user "Authorization timeout" message)

---

## Security Requirements

- **PKCE mandatory** (no `plain` method; must use `S256`)
- **State parameter validation** required (prevents CSRF)
- **Redirect URI enforcement** (loopback only; must be registered)
- **HTTPS for all production calls** (localhost callback is exempt)
- **User agent** (not client credentials) — user is required to authenticate in browser

---

## Notes

- This is the **user-facing interactive flow**. Machine/service auth uses separate endpoints.
- Callback must be to `http://localhost:*` (port arbitrary, determined at runtime).
- No client secret required (public client).
- Authorization scope includes `offline_access` to obtain refresh token.
