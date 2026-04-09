# Browser-Mediated OAuth/OIDC CLI Authentication for spec-kitty

**Mission:** 080-browser-mediated-oauth-cli-auth  
**Epic:** #559  
**SaaS Counterpart:** Epic #49 (spec-kitty-saas)  
**Date:** 2026-04-09  
**Status:** Specification (Synchronized with SaaS Epic #49)

---

## 1. Overview

Replace password-based human CLI authentication with browser-mediated OAuth 2.0 authorization code flow (with PKCE) against the spec-kitty-saas backend. Implement Device Authorization Flow as the sole fallback for headless human environments (SSH sessions, remote servers without browser access). Hard cutover: password auth is removed entirely at GA, no legacy fallback.

This spec defines:
- **User-facing flows**: Interactive login (browser), headless login (device flow), logout, session status, token expiry handling
- **Client architecture**: Centralized TokenManager, loopback callback HTTP server, device flow polling, keychain-backed secure storage, concurrency/single-flight refresh
- **Data models**: Session state, tokens, secure storage schema
- **SaaS integration contracts**: Exact endpoints and behaviors from epic #49 (synchronized as of 2026-04-09)
- **Migration path**: Removal of password/JWT assumptions from existing commands, transports, and tests
- **Testing strategy**: Unit, integration, concurrency, and end-to-end coverage
- **Rollout cadence**: 72+ hour staging validation runway on SaaS side; atomic GA cutover when SaaS deploys

---

## 2. User Scenarios & UX Flows

### 2.1 Interactive Login (Browser + PKCE - Primary Path)

**Actor:** Developer running `spec-kitty auth login` in a terminal with browser access

**Flow:**
1. User runs `spec-kitty auth login` (no prompts for username/password)
2. CLI generates a random 43-character `code_verifier` (PKCE)
3. CLI starts a local HTTP server on `localhost:PORT` (searches 28888-28898 or first available)
4. CLI generates `code_challenge` from verifier
5. CLI opens the default browser to:  
   ```
   https://api.spec-kitty.com/oauth/authorize?
     client_id=cli_native
     &redirect_uri=http://localhost:PORT/callback
     &response_type=code
     &scope=offline_access
     &code_challenge=...
     &code_challenge_method=S256
     &state=<random-nonce>
   ```
6. User logs in and consents to CLI scopes in SaaS UI (via django-allauth)
7. SaaS redirects browser to `http://localhost:PORT/callback?code=AUTHZ_CODE&state=...`
8. CLI receives callback, validates `state`, exchanges `code` + `code_verifier` for tokens at SaaS `POST /oauth/token`
9. CLI stores access token + refresh token in OS keychain (or file fallback)
10. CLI closes loopback server
11. CLI prints: `✓ Authenticated as alice@example.com. Session valid for ~1 hour.`

**Exit scenarios:**
- User denies consent: "Authentication denied. Please try again."
- Callback timeout (5 minutes): "Callback timed out. Please run `spec-kitty auth login` again."
- Network error during token exchange: "Failed to exchange authorization code. [Detailed error]. Please try `spec-kitty auth login` again."

### 2.2 Headless Login (Device Authorization Flow - Fallback)

**Actor:** Developer in SSH session or environment without browser access

**Flow:**
1. User runs `spec-kitty auth login --headless` (or auto-detected when no browser available)
2. CLI calls SaaS `POST /oauth/device` → receives `device_code`, `user_code`, `verification_uri`, `expires_in`, `interval`
3. CLI prints:  
   ```
   Visit: https://api.spec-kitty.com/device
   Enter code: ABCD-1234
   
   Waiting for authorization... (timeout in 15 minutes)
   ```
4. CLI polls SaaS `POST /oauth/token` with `grant_type=urn:ietf:params:oauth:grant-type:device_code` and `device_code` every `interval` seconds (default 5s)
5. User opens browser on another machine, visits URL, enters `user_code`
6. SaaS shows approval UI; user clicks "Grant access"
7. On next poll, SaaS returns `access_token`, `refresh_token`, `session_id`, `expires_in`, `scope`
8. CLI stores tokens in keychain/file, prints: `✓ Authenticated as alice@example.com.`

**Exit scenarios:**
- User denies authorization on SaaS: "Authorization denied. Please try again."
- Polling timeout (15 minutes from device code creation): "Device authorization expired. Please try `spec-kitty auth login --headless` again."
- Network error during polling: "Authorization check failed. Retrying... [up to 3 retries]"

### 2.3 Logout

**Actor:** User running `spec-kitty auth logout`

**Flow:**
1. CLI retrieves current access token from keychain/file
2. CLI calls SaaS `POST /api/v1/logout` with Bearer token to invalidate session server-side
3. CLI deletes credentials from keychain/file
4. CLI prints: `✓ Logged out. Credentials removed.`

**Exit scenario:**
- SaaS logout fails but local deletion succeeds: `✓ Logged out locally. [Warning: server-side logout failed. Token may remain valid until expiry or admin revocation.]`

### 2.4 Session Status

**Actor:** User running `spec-kitty auth status`

**Output:**
```
Authenticated User: alice@example.com
Default Team: ACME Corp (tm_acme)
Access Token Expires: 2026-04-09T14:37:00Z (59 minutes remaining)
Token Storage: macOS Keychain (secure)
Session ID: sess_...
Last Used: 2026-04-09T13:37:00Z
```

If not authenticated:
```
Not authenticated. Run: spec-kitty auth login
```

**Note:** CLI displays the default team context for convenience; actual team is indicated per-command via CLI flag or env var.

### 2.5 Token Expiry & Automatic Refresh

**Scenario:** User has valid refresh token but access token is expired

**Behavior:**
1. Any API call receives 401 Unauthorized with error code `access_token_expired` or `session_invalid`
2. HTTP client interceptor detects 401, checks error code and refresh token validity
3. If error is `access_token_expired` and refresh token valid: single-flight refresh (prevent thundering herd)
4. Exchange refresh token for new access token at SaaS `POST /oauth/token` with `grant_type=refresh_token`
5. Store new access token + new refresh token (if rotated) in keychain
6. Retry original request with new token
7. If error is `session_invalid`: CLI prints "Session expired or revoked. Run `spec-kitty auth login`" and exits with code 401

**Single-flight pattern:** Multiple concurrent requests that all hit 401 will coordinate a single refresh, not N refreshes simultaneously.

### 2.6 Degraded Keychain Mode Notification

**Scenario:** User logs in on Linux system without Secret Service available

**Flow:**
1. CLI detects no supported keystore
2. During login, CLI prompts: `Secure credential store not available. Tokens will be stored in plaintext at ~/.config/spec-kitty/credentials.json with owner-only permissions (0600). Continue? [y/n]`
3. If yes: store credentials in file with strict permissions
4. In `spec-kitty auth status`: show `Token Storage: File fallback (plaintext, owner-only)`
5. In CLI debug log: "No supported keystore detected. Using file fallback for tokens."

---

## 3. Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Browser OAuth login (Authorization Code + PKCE) must be the primary interactive flow, with no user prompt for username/password | Approved |
| FR-002 | Device Authorization Flow must be available as fallback for headless human environments (SSH, remote servers) via `--headless` flag or auto-detection | Approved |
| FR-003 | Loopback callback handler must listen on localhost, accept redirect from SaaS, and not require manual port configuration | Approved |
| FR-004 | All generated `code_verifier` values must be cryptographically secure random, 43 characters, and compliant with RFC 7636 Section 4.1 | Approved |
| FR-005 | Loopback callback server must timeout after 5 minutes of listening without successful callback | Approved |
| FR-006 | Access tokens must be stored exclusively in OS-backed secure storage (Keychain/Credential Manager) when available | Approved |
| FR-007 | When no supported OS keystore is available, tokens may be stored in `~/.config/spec-kitty/credentials.json` with owner-only file permissions (0600) and explicit user consent | Approved |
| FR-008 | CLI must not prompt for or accept username/password for any human authentication path | Approved |
| FR-009 | Tokens must be automatically refreshed before expiry using refresh token without requiring user interaction | Approved |
| FR-010 | When multiple concurrent requests detect token expiry (401), only a single token refresh must occur (single-flight pattern) | Approved |
| FR-011 | Access tokens expired during a request must trigger automatic refresh and retry of the original request up to 1 time | Approved |
| FR-012 | Refresh tokens expired at refresh time must terminate the CLI session with clear messaging | Approved |
| FR-013 | `spec-kitty auth logout` must call SaaS `POST /api/v1/logout` to invalidate session server-side and delete local credentials | Approved |
| FR-014 | Server-side logout failure must not prevent local credential deletion | Approved |
| FR-015 | `spec-kitty auth status` must display authenticated user, default team, access token expiry, storage backend, session ID, and last-used time | Approved |
| FR-016 | Centralized TokenManager must be the sole source of credential provisioning for HTTP transport, batch operations, background sync, tracker calls, and WebSocket connections | Approved |
| FR-017 | All HTTP callers (sync/client.py, tracker/saas_client.py, etc.) must obtain tokens from TokenManager, not read tokens directly from file/keychain | Approved |
| FR-018 | Device Authorization Flow polling must respect `interval` hint from SaaS and cap polling at ≤10 second intervals | Approved |
| FR-019 | Device flow user_code must be formatted in human-friendly chunks (e.g., ABCD-1234) as provided by SaaS | Approved |
| FR-020 | `spec-kitty auth login --headless` must not open a browser or expect user interaction with localhost | Approved |

---

## 4. Non-Functional Requirements

| ID | Requirement | Status | Threshold |
|---|---|---|---|
| NFR-001 | Successful interactive login (browser callback to token storage) must complete in <30 seconds (excluding user think time) | Approved | <30s (network latency + crypto) |
| NFR-002 | Successful headless login (device code generation to token receipt) must complete in <5 seconds | Approved | <5s (network latency only) |
| NFR-003 | Device flow polling timeout must not exceed 15 minutes from initial device code request (matches SaaS device_code expiry) | Approved | ≤15 min |
| NFR-004 | Token refresh must complete in <500ms (P99) under normal network conditions, matching SaaS NFR | Approved | <500ms |
| NFR-005 | Automatic token refresh must not block the user's CLI command for more than 3 seconds (including network round-trip) | Approved | <3s |
| NFR-006 | Single-flight refresh coordination overhead must not exceed 100ms | Approved | <100ms |
| NFR-007 | Loopback callback server startup must not fail due to port unavailability; must search ports 28888-28898 or equivalent | Approved | 10-port search |
| NFR-008 | 99.9% successful token refresh for active sessions across 30-day periods (matching SaaS NFR-003) | Approved | 99.9% SLO |
| NFR-009 | Zero false positives in single-flight refresh (i.e., no duplicate concurrent refreshes) | Approved | 0 duplicates |
| NFR-010 | Token storage (keychain or file) must not corrupt or lose credentials due to concurrent access | Approved | 100% durability |
| NFR-011 | All token reads/writes must use transactional semantics or atomic file operations | Approved | Atomic ops only |
| NFR-012 | Keychain/file fallback selection must happen at login time and be logged/visible in `auth status` | Approved | Logged + visible |
| NFR-013 | File fallback tokens must be created with 0600 permissions from first write; chmod verification on read | Approved | Owner-only perms |

---

## 5. Constraints

| ID | Constraint | Rationale |
|---|---|---|
| C-001 | Password-based human CLI auth must be completely removed at GA; no fallback, no backwards compatibility | Hard cutover per epic #559 discovery |
| C-002 | Device Authorization Flow is the sole headless human fallback; no password/token endpoints available for headless use | Hard cutover; device flow covers all human headless scenarios per epic #49 |
| C-003 | Machine/service/provider authentication is explicitly out of scope for this epic; covered in separate future work | Scope boundary per epic #49 |
| C-004 | Centralized TokenManager must be imported by all HTTP clients within the CLI; no direct token file reads allowed | Architectural convergence requirement |
| C-005 | OAuth scope must include `offline_access` to trigger refresh token issuance (per SaaS epic #49) | SaaS contract requirement |
| C-006 | Device code polling must use single `/oauth/device` endpoint (POST) and exchange via `/oauth/token` with device_code grant type | SaaS contract per epic #49 |
| C-007 | Logout must call `/api/v1/logout`, not `/oauth/revoke` | SaaS contract per epic #49 |
| C-008 | Access token TTL is ~1 hour (3600s); refresh token TTL is ~90 days | SaaS token policy (CliSession model, epic #49) |
| C-009 | Session is server-managed (CliSession model); no JWT self-contained state | SaaS architecture per epic #49 |
| C-010 | Staging validation: 72+ hour window before GA cutover (aligned with SaaS epic #49 plan) | Rollout cadence per epic #49 |

---

## 6. Success Criteria

1. **User Migration**: 95%+ of interactive human CLI logins use browser/PKCE path within 30 days of GA
2. **Password Elimination**: 0 supported human CLI flows collect or prompt for SaaS passwords after cutover
3. **Token Refresh Reliability**: 99.9% successful token refresh/session renewal for active CLI sessions (SLO over 30-day period)
4. **Refresh Race Prevention**: 0 known cases where a valid active user is forced to re-login due to token staleness or refresh race bugs
5. **Logout Correctness**: Explicit logout and server-side revocation reliably terminate CLI access within 5 seconds
6. **Keystore Coverage**: OS-backed secure storage used by default where available; file fallback only when no supported secure store exists
7. **Security Posture**: 0 Sev1 or Sev2 security incidents related to CLI password collection or token mishandling
8. **Device Flow Usability**: Headless users can complete authentication in <90 seconds (excluding SaaS login time)
9. **Staging Validation**: 72+ hour error-rate monitoring on staging before GA cutover confirms 99.9% success on new auth path

---

## 7. Key Data Models & Entities

### 7.1 Session & Token Data (Aligned to SaaS Epic #49)

```python
# Returned by SaaS POST /oauth/token (all flows)
class OAuthTokenResponse:
    access_token: str          # Bearer token for API calls
    token_type: str            # "Bearer"
    expires_in: int            # Seconds from now (e.g., 3600 for 1 hour)
    refresh_token: str         # Opaque refresh token
    scope: str                 # Space-separated scopes granted (includes "offline_access")
    session_id: str            # Server-side session identifier (ULID)

# Computed by CLI
class ComputedTokenExpiry:
    access_token_expires_at: datetime    # now + expires_in
    refresh_token_expires_at: datetime   # ~90 days from now (SaaS policy)

# Stored in keychain/file
class StoredSession:
    user_id: str               # "u_..."
    username: str              # "alice@example.com"
    team_id: str               # "tm_acme" (default team for status display)
    team_name: str             # "ACME Corp"
    access_token: str
    refresh_token: str
    token_issued_at: datetime
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    scope: str
    session_id: str            # From SaaS
    storage_backend: str       # "keychain" | "credential_manager" | "secret_service" | "file"
    last_used_at: datetime
```

### 7.2 OAuth Flow State

```python
class PKCEState:
    state: str                 # CSRF nonce (128-bit random)
    code_verifier: str         # 43-char random per RFC 7636
    code_challenge: str        # SHA256(code_verifier) base64url-encoded
    code_challenge_method: str # "S256"
    created_at: datetime
    expires_at: datetime       # created_at + 5 minutes

class DeviceFlowState:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int            # Seconds (typically 900 = 15 minutes)
    interval: int              # Polling interval from SaaS
    created_at: datetime
    last_polled_at: datetime
    poll_count: int
```

### 7.3 Secure Storage Schema

**Keychain (macOS):**
```
Service: "spec-kitty-cli"
Account: "session"
Password: JSON-encoded StoredSession
```

**Credential Manager (Windows):**
```
Target: "spec-kitty-cli/session"
Credential: JSON-encoded StoredSession
```

**Secret Service (Linux/GNOME Keyring):**
```
Collection: "default"
Label: "spec-kitty-cli session"
Attributes: { "app": "spec-kitty-cli", "type": "session" }
Secret: JSON-encoded StoredSession
```

**File Fallback (`~/.config/spec-kitty/credentials.json`):**
```json
{
  "version": "1.0",
  "backend": "file",
  "session": {
    "user_id": "...",
    "access_token": "...",
    "refresh_token": "...",
    "session_id": "...",
    "...": "..."
  }
}
```
File permissions: 0600 (owner read/write only)

---

## 8. SaaS Integration Contract (Epic #49)

### 8.1 OAuth 2.0 Authorization Endpoint

**SaaS Endpoint:** `GET https://api.spec-kitty.com/oauth/authorize`

**Parameters:**
| Param | Required | Type | Description |
|---|---|---|---|
| `client_id` | Yes | String | CLI client ID: `cli_native` |
| `redirect_uri` | Yes | String | Must be `http://localhost:PORT/callback` (any PORT) |
| `response_type` | Yes | String | Must be `code` |
| `scope` | Yes | String | **Must include `offline_access`** to trigger refresh token issuance |
| `code_challenge` | Yes | String | SHA256(code_verifier) base64url-encoded per RFC 7636 |
| `code_challenge_method` | Yes | String | Must be `S256` |
| `state` | Yes | String | Cryptographic nonce (≥128 bits) for CSRF protection |

**Response:**
Browser redirect to `redirect_uri?code=AUTHZ_CODE&state=STATE_PARAM`

**Notes:**
- SaaS delegates user login to django-allauth
- SaaS validates `state` matches request
- SaaS only accepts registered `http://localhost:PORT/callback` URIs
- Scope consent shown in browser UI
- PKCE mandatory for public/native clients

### 8.2 Device Authorization Endpoint

**SaaS Endpoint:** `POST https://api.spec-kitty.com/oauth/device`

**Request:**
```json
{
  "client_id": "cli_native"
}
```

**Response (200 OK):**
```json
{
  "device_code": "DEV_5C4E9...",
  "user_code": "ABCD-1234",
  "verification_uri": "https://api.spec-kitty.com/device",
  "verification_uri_complete": "https://api.spec-kitty.com/device?user_code=ABCD-1234",
  "expires_in": 900,
  "interval": 5
}
```

**Notes:**
- Device code issued; expires after `expires_in` seconds (typically 900 = 15 minutes)
- User code is human-readable (e.g., "ABCD-1234")
- CLI polls `/oauth/token` every `interval` seconds
- Verification URI shows approval UI

### 8.3 Token Endpoint

**SaaS Endpoint:** `POST https://api.spec-kitty.com/oauth/token`

#### Authorization Code Exchange
```json
{
  "grant_type": "authorization_code",
  "code": "AUTHZ_CODE",
  "code_verifier": "43-CHAR-RANDOM-STRING",
  "client_id": "cli_native",
  "redirect_uri": "http://localhost:PORT/callback"
}
```

#### Device Code Exchange
```json
{
  "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
  "device_code": "DEV_...",
  "client_id": "cli_native"
}
```

#### Refresh Token Exchange
```json
{
  "grant_type": "refresh_token",
  "refresh_token": "rf_...",
  "client_id": "cli_native"
}
```

**Success Response (200 OK):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "rf_...",
  "scope": "offline_access cli api.read api.write",
  "session_id": "sess_..."
}
```

**Error Responses:**

Authorization Code Invalid (401):
```json
{
  "error": "invalid_grant",
  "error_description": "Authorization code is invalid or expired."
}
```

Device Code Pending (400):
```json
{
  "error": "authorization_pending",
  "error_description": "User has not yet approved the device code."
}
```

Device Code Expired (400):
```json
{
  "error": "expired_token",
  "error_description": "Device code expired."
}
```

Session Invalidated (401):
```json
{
  "error": "session_invalid",
  "error_description": "Session has been revoked. Please re-authenticate."
}
```

**Notes:**
- Access token validity: 3600 seconds (~1 hour)
- Refresh token validity: ~90 days
- Session ID returned; CLI stores for status/diagnostics
- Refresh token may be rotated (new token in response)

### 8.4 Logout Endpoint

**SaaS Endpoint:** `POST https://api.spec-kitty.com/api/v1/logout`

**Request (Bearer token required):**
```
POST /api/v1/logout
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "status": "logged_out"
}
```

**Notes:**
- Revokes all tokens in the session server-side
- Further API calls with that token return 401
- Idempotent: calling twice is safe

### 8.5 WebSocket Token Endpoint

**SaaS Endpoint:** `POST https://api.spec-kitty.com/api/v1/ws-token/`

**Request:**
```json
{
  "access_token": "eyJ0eXAi..."
}
```

**Response (200 OK):**
```json
{
  "ws_token": "ws_eyJ0eXAi...",
  "expires_in": 3600,
  "session_id": "sess_..."
}
```

**Notes:**
- Exchanges access token for WebSocket-specific token (short-lived, bound to session)
- WebSocket server validates ws_token for authentication
- On token expiry, client must re-call this endpoint (using refresh flow first if needed)

### 8.6 Me Endpoint

**SaaS Endpoint:** `GET https://api.spec-kitty.com/api/v1/me`

**Request:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "user_id": "u_alice",
  "email": "alice@example.com",
  "teams": [
    {"id": "tm_acme", "name": "Acme Corp"},
    {"id": "tm_widgets", "name": "Widgets Inc"}
  ],
  "session_id": "sess_...",
  "authenticated_at": "2026-04-09T13:37:14Z",
  "access_token_expires_at": "2026-04-09T14:37:14Z"
}
```

**Response on Invalid Token (401):**
```json
{
  "error": "access_token_expired",
  "error_description": "Access token has expired. Please refresh."
}
```
or
```json
{
  "error": "session_invalid",
  "error_description": "Session has been revoked or invalidated."
}
```

---

## 9. Migration Strategy

### 9.1 Module-by-Module Migration Path

**Phase 1: Infrastructure (WP01-WP03)**
- [ ] Build TokenManager + secure storage backends (keychain, file)
- [ ] Build loopback callback handler
- [ ] Build device flow poller
- [ ] Unit test all three in isolation

**Phase 2: OAuth Flows (WP04-WP05)**
- [ ] Implement `spec-kitty auth login` (interactive browser)
- [ ] Implement `spec-kitty auth login --headless` (device flow)
- [ ] Integration test both flows against SaaS (staging or mock)

**Phase 3: Transport Rewiring (WP06-WP08)**
- [ ] Update `sync/client.py` to use TokenManager
- [ ] Update `tracker/saas_client.py` to use TokenManager
- [ ] Update WebSocket connection to call `/api/v1/ws-token/` before connecting
- [ ] Update other HTTP callers (batch, background)

**Phase 4: CLI Commands (WP09)**
- [ ] Implement `spec-kitty auth logout`
- [ ] Implement `spec-kitty auth status`
- [ ] Update `spec-kitty auth` help + docs

**Phase 5: Password Removal & Testing (WP10-WP11)**
- [ ] Remove password prompts from `auth.py`
- [ ] Remove references to legacy endpoints
- [ ] Comprehensive integration tests
- [ ] Concurrency/refresh race tests
- [ ] Staging validation (72+ hours on SaaS before GA cutover)

### 9.2 Affected Modules & Changes

| Module | Current State | Migration |
|---|---|---|
| `specify_cli/auth.py` | Prompts username/password, calls `obtain_tokens()` | Remove password prompts; call `TokenManager.login_interactive()` or `.login_headless()` |
| `specify_cli/auth/token_manager.py` | Does not exist | Create: centralized token provisioning |
| `specify_cli/auth/storage.py` | Does not exist | Create: keychain/file abstraction |
| `specify_cli/auth/loopback.py` | Does not exist | Create: HTTP server for OAuth callback |
| `specify_cli/auth/device_flow.py` | Does not exist | Create: device code polling logic |
| `sync/client.py` | Reads token directly from file | Import TokenManager, call `get_access_token()` on every request |
| `tracker/saas_client.py` | Reads token directly | Import TokenManager, call `get_access_token()` on every request |
| `sync/websocket.py` | Direct connection with access token | Call `/api/v1/ws-token/` endpoint before connecting |
| `sync/background.py`, `sync/batch.py` | Direct token passing | Use TokenManager |
| `tests/sync/test_auth_concurrent_refresh.py` | Existing refresh race tests | Preserve as-is; document as legacy refresh pattern baseline |

### 9.3 Backwards Compatibility

**No backwards compatibility maintained.** Hard cutover:
- Old JWT-based session files are not migrated
- Users with existing sessions must log in again via browser
- All password-based auth endpoints are removed from CLI code
- SaaS removes `/api/v1/token/` and `/api/v1/token/refresh/` endpoints at GA (per epic #49)

---

## 10. Work Package Decomposition

Maps to issues: #560 (ADR), #561 (browser PKCE + device), #562 (TokenManager + keychain), #564 (auth transport rewiring), #565 (legacy password-era removal).

### WP01: TokenManager & Secure Storage Foundation

**Issue:** #562 | **Dependency:** None (critical path)

**Scope:**
- TokenManager class (sync public API + async internals)
- SecureStorage abstraction (Keychain, Credential Manager, Secret Service, file)
- Hybrid DI: shared accessor + explicit injection
- File fallback UX (user prompt, permission checks)

**Acceptance:**
- TokenManager.get_access_token() returns valid token from storage
- TokenManager.refresh_if_needed() performs single-flight refresh
- All storage backends store/load correctly
- File fallback requires user opt-in + 0600 permissions

### WP02: Loopback Callback Handler

**Issue:** #561 | **Dependency:** WP01

**Scope:**
- HTTP server listening on localhost:PORT (28888-28898 or equivalent)
- Callback route: GET /callback?code=...&state=...
- State validation (CSRF protection)
- Port discovery and fallback
- Timeout handling (5 minutes)

**Acceptance:**
- Server starts on available port
- Receives OAuth callback with code + state
- Validates state to prevent CSRF
- Timeout after 5 minutes

### WP03: Device Authorization Flow Poller

**Issue:** #561 | **Dependency:** WP01

**Scope:**
- Device code request: POST /oauth/device
- Token polling: POST /oauth/token with device_code grant type
- Poll interval respecting SaaS hint (cap at 10s)
- Timeout handling (≤15 minutes)

**Acceptance:**
- Device code request succeeds
- Polling respects SaaS interval
- Authorization granted: returns tokens
- Authorization denied: raises exception
- Timeout: raises exception after expires_in seconds

### WP04: Browser Login Flow (auth login)

**Issue:** #561 | **Dependency:** WP01, WP02

**Scope:**
- `spec-kitty auth login` command
- PKCE code_verifier generation (43 chars)
- Browser open (webbrowser library)
- Loopback callback coordination
- Token exchange with SaaS
- Fallback to --headless if no browser detected

**Acceptance:**
- Browser login succeeds; callback received; tokens stored
- Headless fallback works when browser unavailable
- Timeout scenarios handled gracefully
- Tokens stored in keychain/file with correct permissions

### WP05: Headless Login Flow (auth login --headless)

**Issue:** #561 | **Dependency:** WP01, WP03

**Scope:**
- `spec-kitty auth login --headless` command
- Device code request and user code display
- Polling loop with backoff
- Timeout handling

**Acceptance:**
- Device code request succeeds
- User code displayed clearly
- Polling continues until approval or timeout
- Tokens stored on approval

### WP06: Logout Command (auth logout)

**Issue:** #561 | **Dependency:** WP01

**Scope:**
- `spec-kitty auth logout` command
- Call SaaS POST /api/v1/logout
- Local credential deletion
- Messaging for revocation failure

**Acceptance:**
- Logout succeeds; local credentials deleted
- Revocation failure doesn't block local deletion
- Status shows "Not authenticated" after logout

### WP07: Status Command (auth status)

**Issue:** #562 | **Dependency:** WP01

**Scope:**
- `spec-kitty auth status` command
- Display user, team, expiry, storage backend, session ID
- Unauthenticated case handling

**Acceptance:**
- Shows all required fields when authenticated
- Shows "Not authenticated" when no session
- Storage backend displayed correctly

### WP08: HTTP Transport Rewiring (sync/client, tracker/saas_client)

**Issue:** #564 | **Dependency:** WP01

**Scope:**
- sync/client.py: TokenManager integration
- tracker/saas_client.py: TokenManager integration
- 401 retry logic: auto-refresh + 1 retry
- Concurrency: single-flight refresh

**Acceptance:**
- All HTTP callers use TokenManager
- 401 triggers refresh + 1 retry
- Concurrent requests coordinate (1 refresh, N waiting)

### WP09: WebSocket Integration (ws-token)

**Issue:** #564 | **Dependency:** WP01, WP08

**Scope:**
- Call `/api/v1/ws-token/` before WebSocket connect
- WebSocket token refresh on expiry
- Integration with long-lived connections

**Acceptance:**
- WebSocket authenticated with ws_token
- Token refresh before expiry
- Long-lived connections remain open

### WP10: Password Removal & CLI Cleanup

**Issue:** #565 | **Dependency:** WP04-WP09

**Scope:**
- Remove password prompts from auth.py
- Remove legacy endpoint references
- Update help text + docs

**Acceptance:**
- `spec-kitty auth login` does NOT prompt for password
- No legacy endpoint references
- All tests pass with new auth

### WP11: Concurrency Tests & Staging Validation

**Issue:** #562 | **Dependency:** WP01-WP10

**Scope:**
- Single-flight refresh (10+ concurrent 401s → 1 exchange)
- 72+ hour staging validation (SaaS side aligns)
- Stress tests under concurrent load
- Monitor 99.9% success rate

**Acceptance:**
- Zero duplicate concurrent refreshes
- 99.9% refresh success under load
- Staging validation confirms readiness

---

## 11. Testing Strategy

**Unit Tests** (pytest, 90%+ coverage):
- TokenManager: load, refresh, expiry, errors
- Storage: keychain, file fallback, permissions
- Loopback: port discovery, state validation, timeout
- Device flow: code request, polling, timeout

**Integration Tests** (mock SaaS or staging):
- Browser login end-to-end
- Headless login end-to-end
- Logout and revocation
- HTTP client 401 retry
- WebSocket token refresh
- Concurrent 401s (single-flight verification)

**Staging Validation** (72+ hours):
- Monitor auth success rates (target 99.9%)
- Performance (refresh <500ms P99)
- Error logs for unexpected failures
- Go/no-go gate before GA cutover

---

## 12. Assumptions

1. **SaaS Contract (Epic #49)** finalized endpoints match this spec exactly (synchronized as of 2026-04-09)
2. **OS keystore libraries** (keyring) work cross-platform; fallback to file if unavailable
3. **Browser access** available in >95% of interactive use cases; device flow covers <5% headless
4. **Token expiry SLOs** (~1h access, ~90d refresh) acceptable for CLI workloads
5. **Single-flight refresh** via asyncio.Lock sufficient (CLI single-process)
6. **File fallback** is degraded-security option, not primary path
7. **No machine/service auth** in scope; separate future epic
8. **Staging validation** (72h) happens on SaaS side before GA cutover

---

## 13. References

- **Epic #559**: Browser-mediated CLI auth (this epic)
- **Epic #49**: SaaS OAuth/renewable sessions (spec-kitty-saas, source of truth)
- **Issues**: #560 (ADR), #561 (PKCE+device), #562 (TokenManager), #564 (transport), #565 (password removal)
- **RFCs**: 6749 (OAuth 2.0), 7636 (PKCE), 8628 (Device Flow)

---

## End of Specification

**Next Phase**: `/spec-kitty.plan` implementation planning (Phase 0 research, Phase 1 design)
