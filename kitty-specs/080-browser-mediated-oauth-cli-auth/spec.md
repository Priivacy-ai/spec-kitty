# Browser-Mediated OAuth/OIDC CLI Authentication for spec-kitty

**Mission:** 080-browser-mediated-oauth-cli-auth  
**Epic:** #559  
**Date:** 2026-04-09  
**Status:** Specification (Ready for Planning)

---

## 1. Overview

Replace password-based human CLI authentication with browser-mediated OAuth 2.0 authorization code flow (with PKCE) against the spec-kitty-saas backend. Implement Device Authorization Flow as the sole fallback for headless human environments (SSH sessions, remote servers without browser access). Hard cutover: password auth is removed entirely at GA, no legacy fallback.

This spec defines:
- **User-facing flows**: Interactive login (browser), headless login (device flow), logout, session status, token expiry handling
- **Client architecture**: Centralized TokenManager, loopback callback HTTP server, device flow polling, keychain-backed secure storage, concurrency/single-flight refresh
- **Data models**: Session state, tokens, secure storage schema
- **SaaS integration contracts**: Required endpoints and behaviors from epic #49
- **Migration path**: Removal of password/JWT assumptions from existing commands, transports, and tests
- **Testing strategy**: Unit, integration, concurrency, and end-to-end coverage

---

## 2. User Scenarios & UX Flows

### 2.1 Interactive Login (Browser + PKCE - Primary Path)

**Actor:** Developer running `spec-kitty auth login` in a terminal with browser access

**Flow:**
1. User runs `spec-kitty auth login` (no prompts for username/password)
2. CLI generates a random 43-character `code_verifier` (PKCE)
3. CLI starts a local HTTP server on `localhost:28888` (or finds available port)
4. CLI generates `code_challenge` from verifier
5. CLI opens the default browser to:  
   ```
   https://<saas-host>/oauth/authorize?
     client_id=cli-oauth-client-id
     &redirect_uri=http://localhost:28888/callback
     &response_type=code
     &scope=read:orgs+write:projects+...
     &code_challenge=...
     &code_challenge_method=S256
     &state=<random-nonce>
   ```
6. User logs in and consents to CLI scopes in SaaS UI
7. SaaS redirects browser to `http://localhost:28888/callback?code=AUTH_CODE&state=...`
8. CLI receives callback, validates `state`, exchanges `code` + `code_verifier` for tokens at SaaS `/oauth/token`
9. CLI stores access token + refresh token in OS keychain (or file fallback)
10. CLI closes loopback server
11. CLI prints: `✓ Authenticated as user@example.com. Session valid until [ISO date].`

**Exit scenarios:**
- User denies consent: "Authentication denied. Please try again."
- Callback timeout (5 minutes): "Callback timed out. Please run `spec-kitty auth login` again."
- Network error during token exchange: "Failed to exchange authorization code. [Detailed error]. Please try `spec-kitty auth login` again."

### 2.2 Headless Login (Device Authorization Flow - Fallback)

**Actor:** Developer in SSH session or environment without browser access

**Flow:**
1. User runs `spec-kitty auth login --headless` (or auto-detected when no browser available)
2. CLI calls SaaS `/oauth/device/code` → receives `device_code`, `user_code`, `verification_uri`, `expires_in`, `interval`
3. CLI prints:  
   ```
   Enter this code on your device:
   
     ABCD-EFGH
   
   or visit: https://<saas-host>/device?code=ABCD-EFGH
   
   Waiting for authorization... (timeout in 10 minutes)
   ```
4. CLI polls SaaS `/oauth/device/token` every `interval` seconds (default 5s) with `device_code`
5. User opens browser on another machine, visits URL, logs in, enters `user_code`
6. On next poll, SaaS returns `access_token`, `refresh_token`, `expires_in`
7. CLI stores tokens in keychain/file, prints: `✓ Authenticated as user@example.com.`

**Exit scenarios:**
- User denies authorization on SaaS: "Authorization denied. Please try again."
- Polling timeout (default 10 minutes): "Device authorization expired. Please try `spec-kitty auth login --headless` again."
- Network error during polling: "Authorization check failed. Retrying... [up to 3 retries]"

### 2.3 Logout

**Actor:** User running `spec-kitty auth logout`

**Flow:**
1. CLI retrieves current access token from keychain/file
2. CLI calls SaaS `/oauth/revoke` to invalidate token server-side
3. CLI deletes credentials from keychain/file
4. CLI prints: `✓ Logged out. Credentials removed.`

**Exit scenario:**
- SaaS revocation fails but local deletion succeeds: "✓ Logged out locally. [Warning: server revocation failed. Try again later to fully invalidate.]"

### 2.4 Session Status

**Actor:** User running `spec-kitty auth status`

**Output:**
```
Authenticated User: alice@example.com
Organization: ACME Corp (org-uuid-here)
Session Scope: read:orgs,write:projects,manage:integrations
Access Token Expires: 2026-04-10T13:37:00Z (59 minutes remaining)
Refresh Token Expires: 2026-05-09T13:37:00Z (30 days remaining)
Token Storage: macOS Keychain (secure)
Last Refreshed: 2026-04-09T11:00:00Z
```

If not authenticated:
```
Not authenticated. Run: spec-kitty auth login
```

### 2.5 Token Expiry & Automatic Refresh

**Scenario:** User has valid refresh token but access token is expired

**Behavior:**
1. Any API call receives 401 Unauthorized
2. HTTP client interceptor detects 401, checks refresh token validity
3. If refresh token valid: single-flight refresh (prevent thundering herd)
4. Exchange refresh token for new access token at SaaS `/oauth/token`
5. Store new access token in keychain
6. Retry original request with new token
7. If refresh token expired: CLI prints "Session expired. Run `spec-kitty auth login`" and exits with code 401

**Single-flight pattern:** Multiple concurrent requests that all hit 401 will coordinate a single refresh, not N refreshes simultaneously.

### 2.6 Degraded Keychain Mode Notification

**Scenario:** User logs in on Linux system without Secret Service available

**Flow:**
1. CLI detects no supported keystore
2. During login, CLI prompts: `Secure credential store (Keyring/GNOME) not available. Tokens will be stored in plaintext at ~/.config/spec-kitty/tokens.json with owner-only permissions (0600). Continue? [y/n]`
3. If yes: store credentials in file with strict permissions
4. In `spec-kitty auth status`: show `Token Storage: File fallback (plaintext, owner-only)`
5. In CLI startup (quiet): debug log: "No supported keystore detected. Using file fallback for tokens."

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
| FR-007 | When no supported OS keystore is available, tokens may be stored in `~/.config/spec-kitty/tokens.json` with owner-only file permissions (0600) and explicit user consent | Approved |
| FR-008 | CLI must not prompt for or accept username/password for any human authentication path | Approved |
| FR-009 | Tokens must be automatically refreshed before expiry using refresh token without requiring user interaction | Approved |
| FR-010 | When multiple concurrent requests detect token expiry (401), only a single token refresh must occur (single-flight pattern) | Approved |
| FR-011 | Access tokens expired during a request must trigger automatic refresh and retry of the original request up to 1 time | Approved |
| FR-012 | Refresh tokens expired at refresh time must terminate the CLI session with clear messaging | Approved |
| FR-013 | `spec-kitty auth logout` must revoke tokens server-side at SaaS `/oauth/revoke` and delete local credentials | Approved |
| FR-014 | Server-side token revocation failure must not prevent local credential deletion | Approved |
| FR-015 | `spec-kitty auth status` must display authenticated user, organization, scopes, token expiry, storage backend, and last refresh time | Approved |
| FR-016 | Centralized TokenManager must be the sole source of credential provisioning for HTTP transport, batch operations, background sync, tracker calls, and WebSocket connections | Approved |
| FR-017 | All HTTP callers (sync/client.py, tracker/saas_client.py, etc.) must obtain tokens from TokenManager, not read tokens directly from file/keychain | Approved |
| FR-018 | Device Authorization Flow polling must respect `interval` hint from SaaS and cap polling at ≤10 second intervals | Approved |
| FR-019 | Device flow user_code must be formatted in human-friendly chunks (e.g., ABCD-EFGH) as provided by SaaS | Approved |
| FR-020 | `spec-kitty auth login --headless` must not open a browser or expect user interaction with localhost | Approved |

---

## 4. Non-Functional Requirements

| ID | Requirement | Status | Threshold |
|---|---|---|---|
| NFR-001 | Successful interactive login (browser callback to token storage) must complete in <30 seconds (excluding user think time) | Approved | <30s (network latency + crypto) |
| NFR-002 | Successful headless login (device code generation to token receipt) must complete in <5 seconds | Approved | <5s (network latency only) |
| NFR-003 | Device flow polling timeout must not exceed 15 minutes from initial device code request | Approved | ≤15 min |
| NFR-004 | Token refresh must complete in <2 seconds under normal network conditions | Approved | <2s |
| NFR-005 | Automatic token refresh must not block the user's CLI command for more than 3 seconds (including network round-trip) | Approved | <3s |
| NFR-006 | Single-flight refresh coordination overhead must not exceed 100ms | Approved | <100ms |
| NFR-007 | Loopback callback server startup must not fail due to port unavailability; must search ports 28888-28898 | Approved | 10-port search |
| NFR-008 | 99.9% successful token refresh for active sessions across 30-day periods (i.e., <3 refresh failures per 10,000 refreshes) | Approved | 99.9% SLO |
| NFR-009 | Zero false positives in single-flight refresh (i.e., no duplicate concurrent refreshes) | Approved | 0 duplicates |
| NFR-010 | Token storage (keychain or file) must not corrupt or lose credentials due to concurrent access | Approved | 100% durability |
| NFR-011 | All token reads/writes must use transactional semantics or atomic file operations | Approved | Atomic ops only |
| NFR-012 | Keychain/file fallback selection must happen at login time and be logged/visible in `auth status` | Approved | Logged + visible |
| NFR-013 | File fallback tokens must be created with 0600 permissions from first write; chmod verification on read | Approved | Owner-only perms |

---

## 5. Constraints

| ID | Constraint | Rationale |
|---|---|---|
| C-001 | Password-based human CLI auth must be completely removed at GA; no fallback, no backwards compatibility | Hard cutover per discovery Q1:A |
| C-002 | Device Authorization Flow is the sole headless human fallback; legacy password/token endpoints are not available for headless use | Hard cutover; device flow covers all human headless scenarios |
| C-003 | Machine/service/provider authentication is explicitly out of scope for this epic; covered in separate future work | Scope boundary |
| C-004 | Centralized TokenManager must be imported by all HTTP clients within the CLI; no direct token file reads allowed | Architectural convergence requirement |
| C-005 | Refresh token expiry must not exceed 30 days; access token expiry must not exceed 24 hours | Industry standard; aligns with SaaS token policy |
| C-006 | SaaS OAuth endpoints must follow RFC 6749 (OAuth 2.0) and RFC 7636 (PKCE) standards | Interoperability and security |
| C-007 | Loopback callback redirect URI must be `http://localhost:PORT/callback` (not HTTPS, not other schemes) | RFC 8252 (OAuth for Native Apps) |
| C-008 | State parameter must be cryptographically secure random, ≥128 bits | CSRF protection per OAuth spec |
| C-009 | Code verifier must not be logged, printed, or persisted; only used immediately for token exchange | Security |
| C-010 | Refresh tokens must not be logged, printed, or exposed in debug output | Security |
| C-011 | All token transmission to/from SaaS must use HTTPS only (TLS 1.2+) | Security |
| C-012 | CLI must never trust bearer tokens without validating origin (SaaS host) | Security |
| C-013 | File fallback token storage requires explicit user opt-in via prompt (not silent downgrade) | Security transparency |
| C-014 | Token storage permission checks (e.g., 0600 verification) must happen on every token read | Security |

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

---

## 7. Key Data Models & Entities

### 7.1 Session & Token Data

```python
# Issued by SaaS /oauth/token endpoint
class OAuthToken:
    access_token: str          # Bearer token for API calls
    token_type: str            # "Bearer"
    expires_in: int            # Seconds from now (e.g., 3600)
    refresh_token: str         # Opaque refresh token
    refresh_expires_in: int    # Seconds from now (e.g., 2592000 for 30 days)
    scope: str                 # Space-separated scopes granted
    issued_at: datetime        # RFC 3339 timestamp

# Derived (computed on client)
class ComputedTokenExpiry:
    access_token_expires_at: datetime    # issued_at + expires_in
    refresh_token_expires_at: datetime   # issued_at + refresh_expires_in

# Stored in keychain/file
class StoredSession:
    user_id: str
    username: str
    email: str
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str
    token_issued_at: datetime
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    scope: str
    storage_backend: str  # "keychain" | "file" | "credential_manager"
    last_refreshed_at: datetime
```

### 7.2 OAuth Flow State

```python
class PKCEState:
    state: str                 # CSRF nonce (128-bit random)
    code_verifier: str         # 43-char random per RFC 7636
    code_challenge: str        # SHA256(code_verifier) base64url-encoded
    code_challenge_method: str # "S256"
    nonce: str                 # OpenID Connect nonce (if using OIDC)
    created_at: datetime
    expires_at: datetime       # created_at + 5 minutes

class DeviceFlowState:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int            # Seconds
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
Password: JSON-encoded StoredSession (serialized)
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

**File Fallback (`~/.config/spec-kitty/tokens.json`):**
```json
{
  "version": "1.0",
  "backend": "file",
  "session": {
    "user_id": "...",
    "access_token": "...",
    "refresh_token": "...",
    "...": "..."
  }
}
```
File permissions: 0600 (owner read/write only)

---

## 8. Client Architecture

### 8.1 Centralized TokenManager

**Responsibility:** Single source of truth for all credential operations across the CLI.

**Public Interface:**
```python
class TokenManager:
    # Login flows
    async def login_interactive(self, port_range=(28888, 28898)) -> StoredSession
    async def login_headless(self) -> StoredSession
    
    # Logout
    async def logout(self) -> None
    
    # Token provisioning (used by all HTTP clients)
    async def get_access_token(self) -> str
        # Returns current access token, auto-refreshing if needed
    
    # Session introspection
    async def get_session(self) -> StoredSession | None
    async def session_status(self) -> SessionStatus | None
    
    # Refresh handling
    async def refresh_if_needed(self) -> bool  # True if refreshed
    
    # Internal
    def _load_from_storage(self) -> StoredSession | None
    def _save_to_storage(self, session: StoredSession) -> None
    def _delete_from_storage(self) -> None
```

**Concurrency & Refresh:**
- Single `asyncio.Lock` prevents concurrent token exchanges
- Waiting requests are notified when refresh completes
- Max 1 refresh in-flight at any time

**Integration Points:**
- HTTP transport layer calls `await token_manager.get_access_token()` on every request
- Background sync subscribes to token expiry events
- WebSocket connections refresh before establishing connection
- Batch operations refresh before processing

### 8.2 Loopback Callback Handler

**Component:** `specify_cli/auth/loopback.py`

**Responsibility:** Lightweight HTTP server that receives OAuth callback.

**Implementation:**
```python
class LoopbackCallbackServer:
    def __init__(self, port_range=(28888, 28898)):
        self.port = self._find_available_port(port_range)
        self.server = None
        self.callback_received = asyncio.Event()
        self.callback_data = None
        self.timeout_seconds = 300  # 5 minutes
    
    async def start(self) -> str:
        # Returns redirect_uri: "http://localhost:PORT/callback"
    
    async def wait_for_callback(self) -> dict:
        # Waits for callback, returns {code, state}
        # Raises TimeoutError if no callback within 5 min
    
    async def stop(self) -> None:
```

**Route Handler:**
```
GET /callback?code=AUTH_CODE&state=STATE_PARAM
  → Validate state (CSRF check)
  → Store code + state
  → Return minimal HTML: "Authorization received. Closing..."
  → Signal to CLI that callback arrived
```

**Error Handling:**
- Missing `code`: return 400 with error message
- Invalid `state`: return 403 (CSRF attack detected)
- Already received callback: return 200 (idempotent)

### 8.3 Device Flow Poller

**Component:** `specify_cli/auth/device_flow.py`

**Responsibility:** Poll SaaS for device authorization completion.

**Implementation:**
```python
class DeviceFlowPoller:
    def __init__(self, saas_host: str, client_id: str):
        self.saas_host = saas_host
        self.client_id = client_id
        self.poll_interval = 5  # seconds, adjusted by SaaS hint
        self.max_wait = 900  # 15 minutes
    
    async def request_device_code(self) -> DeviceFlowState:
        # POST to SaaS /oauth/device/code
        # Returns device_code, user_code, verification_uri, interval, expires_in
    
    async def poll_until_authorized(self, state: DeviceFlowState) -> OAuthToken:
        # Polls /oauth/device/token every interval seconds
        # Raises TimeoutError if expires_in exceeded
        # Raises AuthorizationDenied if user denies consent
```

**Polling Logic:**
```
repeat {
    sleep(interval)
    POST /oauth/device/token {
        grant_type: "urn:ietf:params:oauth:grant-type:device_code",
        device_code: STATE.device_code,
        client_id: CLIENT_ID
    }
    
    if response.status == 200:
        return access_token, refresh_token
    
    if response.error == "authorization_pending":
        continue
    
    if response.error == "slow_down":
        increase interval by 5 seconds
        continue
    
    if response.error == "access_denied":
        raise AuthorizationDenied
    
    if response.error == "expired_token":
        raise TimeoutError
}
```

### 8.4 Secure Storage Backend

**Component:** `specify_cli/auth/storage.py`

**Responsibility:** Abstraction over Keychain/Credential Manager/File storage.

**Implementation:**
```python
class SecureStorage:
    def __init__(self, service_name="spec-kitty-cli"):
        self.backend = self._detect_backend()
    
    def _detect_backend(self) -> StorageBackend:
        # Detect OS, try available keystores in order:
        # 1. macOS → keychain (via keyring library)
        # 2. Windows → wincred (via keyring library)
        # 3. Linux → SecretService (via keyring library)
        # 4. Fallback → plaintext file (~/.config/spec-kitty/tokens.json)
        # Raise exception if keystore missing and no user consent for file
    
    async def store_session(self, session: StoredSession) -> None:
        # Serialize session to JSON
        # For file backend: write with 0600 perms, check on every write
        # For keystore: use service-specific API
    
    async def load_session(self) -> StoredSession | None:
        # Deserialize from keystore/file
        # For file: verify 0600 permissions before reading
        # Return None if not found
    
    async def delete_session(self) -> None:
        # Remove from keystore/file
        # No error if already deleted
    
    def get_backend_name(self) -> str:
        # "keychain" | "credential_manager" | "secret_service" | "file"
```

**File Fallback Workflow:**
```
1. Detect no supported keystore available
2. At login time, prompt user:
   "No secure credential store found. Continue with file fallback? [y/n]"
3. If yes: create ~/.config/spec-kitty/tokens.json with 0600 perms
4. On every save: chmod 0600 explicitly
5. On every load: stat() and verify 0600; warn if wrong
6. In auth status: show "File fallback (plaintext, owner-only)"
```

### 8.5 HTTP Transport Integration

**Current state:** `sync/client.py`, `tracker/saas_client.py` read tokens directly from disk/keychain.

**Migration:**
```python
# OLD (current):
class SaaSClient:
    def __init__(self):
        self.token = read_token_from_file()
    
    async def call(self, endpoint):
        headers = {"Authorization": f"Bearer {self.token}"}

# NEW:
class SaaSClient:
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
    
    async def call(self, endpoint):
        token = await self.token_manager.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = await self.http_client.request(...)
        
        if response.status == 401:
            # Token expired during flight; refresh and retry once
            await self.token_manager.refresh_if_needed()
            token = await self.token_manager.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = await self.http_client.request(...)
        
        return response
```

**Retry Logic:**
- First request gets 401: refresh, retry once (max 1 retry)
- Second request still 401: raise 401 to caller (user must re-login)
- Refresh itself fails: raise to caller

### 8.6 WebSocket Integration

**Current state:** WebSocket connections are established but token handling unclear.

**Migration:**
```python
class WebSocketConnection:
    def __init__(self, token_manager: TokenManager, saas_host: str):
        self.token_manager = token_manager
        self.saas_host = saas_host
    
    async def connect(self) -> None:
        # Before connecting, ensure token is fresh
        await self.token_manager.refresh_if_needed()
        token = await self.token_manager.get_access_token()
        
        # Connect with token in query param or Authorization header
        url = f"wss://{self.saas_host}/ws?token={token}"
        self.ws = await websockets.connect(url)
    
    async def handle_disconnect(self) -> None:
        # If closed due to 401, refresh and reconnect
        if self.last_close_reason == 401:
            await self.token_manager.refresh_if_needed()
            await self.connect()
```

---

## 9. SaaS Integration Contract (Epic #49 Dependencies)

This section defines the endpoints and behaviors the CLI requires from the SaaS auth system.

### 9.1 OAuth 2.0 Authorization Endpoint

**SaaS Requirement (from epic #49):**
```
POST https://<saas-host>/oauth/authorize
```

**Parameters:**
| Param | Required | Type | Description |
|---|---|---|---|
| `client_id` | Yes | String | CLI client ID (pre-registered in SaaS) |
| `redirect_uri` | Yes | String | Must be `http://localhost:PORT/callback` |
| `response_type` | Yes | String | Must be `code` |
| `scope` | Yes | String | Space-separated scopes: `read:orgs write:projects ...` |
| `code_challenge` | Yes | String | SHA256(code_verifier) base64url-encoded per RFC 7636 |
| `code_challenge_method` | Yes | String | Must be `S256` |
| `state` | Yes | String | Cryptographic nonce (≥128 bits) for CSRF protection |

**Response:**
Browser redirect to `redirect_uri?code=AUTH_CODE&state=STATE_PARAM`

**Notes:**
- SaaS must validate `state` matches request
- SaaS must render browser login/consent UI
- SaaS must not accept unregistered `redirect_uri` values
- Redirect must preserve exact `state` parameter for CLI validation

### 9.2 OAuth 2.0 Token Exchange Endpoint

**SaaS Requirement (from epic #49):**
```
POST https://<saas-host>/oauth/token
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
grant_type=authorization_code
&code=AUTH_CODE
&redirect_uri=http://localhost:PORT/callback
&client_id=CLI_CLIENT_ID
&code_verifier=43-CHAR-RANDOM-STRING
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_expires_in": 2592000,
  "scope": "read:orgs write:projects manage:integrations",
  "issued_at": "2026-04-09T13:37:00Z"
}
```

**Error Response (400/401/403):**
```json
{
  "error": "invalid_code",
  "error_description": "Authorization code expired or invalid"
}
```

**Notes:**
- SaaS must validate `code_verifier` against `code_challenge` using SHA256
- SaaS must reject if `code_verifier` missing or invalid
- `access_token` validity: ≤24 hours
- `refresh_token` validity: ≤30 days (preferred 30 days)
- `issued_at` must be RFC 3339 ISO 8601 format

### 9.3 Token Refresh Endpoint

**SaaS Requirement (from epic #49):**
```
POST https://<saas-host>/oauth/token
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
grant_type=refresh_token
&refresh_token=REFRESH_TOKEN_VALUE
&client_id=CLI_CLIENT_ID
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_expires_in": 2592000,
  "scope": "read:orgs write:projects manage:integrations",
  "issued_at": "2026-04-09T13:37:00Z"
}
```

**Error Response (400/401):**
```json
{
  "error": "invalid_grant",
  "error_description": "Refresh token expired or revoked"
}
```

**Notes:**
- SaaS may issue a new `refresh_token` in response (rotation)
- CLI must use new `refresh_token` if provided
- If 401 + `invalid_grant`: refresh token is no longer valid; user must re-login
- Response format identical to authorization code exchange

### 9.4 Token Revocation Endpoint

**SaaS Requirement (from epic #49):**
```
POST https://<saas-host>/oauth/revoke
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
token=ACCESS_TOKEN_OR_REFRESH_TOKEN
&client_id=CLI_CLIENT_ID
```

**Response (200 OK):**
```json
{
  "success": true
}
```

**Notes:**
- SaaS must invalidate both the token and its family (if applicable)
- SaaS must be idempotent: revoking an already-revoked token is OK
- Logout does not fail if revocation fails; local deletion proceeds

### 9.5 Device Authorization Flow Endpoints

**SaaS Requirement (from epic #49):**

#### Device Code Request
```
POST https://<saas-host>/oauth/device/code
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
client_id=CLI_CLIENT_ID
&scope=read:orgs+write:projects+manage:integrations
```

**Response (200 OK):**
```json
{
  "device_code": "AaBbCcDdEeFfGgHh",
  "user_code": "ABCD-EFGH",
  "verification_uri": "https://<saas-host>/device?code=ABCD-EFGH",
  "verification_uri_complete": "https://<saas-host>/device?user_code=ABCD-EFGH",
  "expires_in": 900,
  "interval": 5
}
```

#### Device Token Poll
```
POST https://<saas-host>/oauth/device/token
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
grant_type=urn:ietf:params:oauth:grant-type:device_code
&device_code=DEVICE_CODE
&client_id=CLI_CLIENT_ID
```

**Response (200 OK) - Authorization Granted:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_...",
  "refresh_expires_in": 2592000,
  "scope": "read:orgs write:projects manage:integrations",
  "issued_at": "2026-04-09T13:37:00Z"
}
```

**Response (400) - Pending or Error:**
```json
{
  "error": "authorization_pending"
}
```
or
```json
{
  "error": "slow_down"
}
```
or
```json
{
  "error": "access_denied"
}
```
or
```json
{
  "error": "expired_token"
}
```

**Notes:**
- `user_code` must be human-readable (e.g., "ABCD-EFGH")
- `verification_uri` must accept ?user_code parameter
- `interval` is polling interval recommendation; CLI must respect it
- CLI must not poll faster than `interval` seconds
- `expires_in` is device code lifetime; CLI must stop polling after this time
- See RFC 8628 for full device flow specification

---

## 10. Migration Strategy

### 10.1 Module-by-Module Migration Path

**Phase 1: Infrastructure (WP01-WP03)**
- [ ] Build TokenManager + secure storage backends (keychain, file)
- [ ] Build loopback callback handler
- [ ] Build device flow poller
- [ ] Unit test all three in isolation

**Phase 2: OAuth Flows (WP04-WP05)**
- [ ] Implement `spec-kitty auth login` (interactive browser)
- [ ] Implement `spec-kitty auth login --headless` (device flow)
- [ ] Integration test both flows against SaaS

**Phase 3: Transport Rewiring (WP06-WP07)**
- [ ] Update `sync/client.py` to use TokenManager
- [ ] Update `tracker/saas_client.py` to use TokenManager
- [ ] Update other HTTP callers (batch, background, websocket)

**Phase 4: CLI Commands (WP08)**
- [ ] Implement `spec-kitty auth logout`
- [ ] Implement `spec-kitty auth status`
- [ ] Update `spec-kitty auth` help + docs

**Phase 5: Password Removal & Testing (WP09-WP10)**
- [ ] Remove password prompts from `auth.py`
- [ ] Remove `/api/v1/token/` and `/api/v1/token/refresh/` references
- [ ] Comprehensive integration tests
- [ ] Concurrency/refresh race tests

**Phase 6: Legacy Tests & Cleanup (WP11)**
- [ ] Preserve `test_auth_concurrent_refresh.py` as baseline
- [ ] Retire password-related test fixtures
- [ ] Clean up unused legacy auth code

### 10.2 Affected Modules & Changes

| Module | Current State | Migration |
|---|---|---|
| `specify_cli/auth.py` | Prompts username/password, calls `obtain_tokens()` | Remove password prompts; call `TokenManager.login_interactive()` or `.login_headless()` |
| `specify_cli/auth/loopback.py` | Does not exist | Create: HTTP server for OAuth callback |
| `specify_cli/auth/device_flow.py` | Does not exist | Create: device code polling logic |
| `specify_cli/auth/storage.py` | Does not exist | Create: keychain/file abstraction |
| `specify_cli/auth/token_manager.py` | Does not exist | Create: centralized token provisioning |
| `sync/auth.py` | Password obtain + JWT refresh hardening | Simplify to only refresh logic; remove password code |
| `sync/client.py` | Reads token directly from file | Import TokenManager, call `get_access_token()` on every request |
| `tracker/saas_client.py` | Reads token directly | Import TokenManager, call `get_access_token()` on every request |
| `sync/background.py` | Passes token directly | Use TokenManager |
| `sync/batch.py` | Passes token directly | Use TokenManager |
| `sync/body_transport.py` | Raw token handling | Use TokenManager |
| `sync/sync_status.py` | Displays JWT access/refresh state | Simplify to display expiry times + storage backend |
| `tests/sync/test_auth_concurrent_refresh.py` | Existing refresh race tests | Preserve as-is; document as legacy refresh pattern baseline |

### 10.3 Backwards Compatibility

**No backwards compatibility maintained.** Hard cutover:
- Old JWT-based session files (`~/.config/spec-kitty/session.json` or equivalent) are not migrated
- Users with existing sessions must log in again via browser
- All password-based auth endpoints are removed from CLI code

**SaaS-side note:** Epic #49 must also deprecate/remove legacy `/api/v1/token/` and `/api/v1/token/refresh/` endpoints for human CLI auth (machine auth may use different endpoints per separate epic).

---

## 11. Work Package Decomposition

Maps to issues: #560 (ADR), #561 (browser PKCE + device), #562 (TokenManager + keychain), #564 (transport rewiring), #565 (password removal).

### WP01: TokenManager & Secure Storage Foundation

**Issue:** #562 (TokenManager + keychain storage)

**Scope:**
- `specify_cli/auth/token_manager.py`: Core TokenManager class
- `specify_cli/auth/storage.py`: Keychain/Credential Manager/File abstraction
- Unit tests for TokenManager (mocked storage)
- Unit tests for storage backends (integration tests with real OS keystores)
- Secure storage fallback UX (prompt for file fallback)

**Acceptance:**
- TokenManager.get_access_token() returns valid token from storage
- TokenManager.refresh_if_needed() performs single-flight refresh
- All storage backends (keychain, file) store and load correctly
- File fallback uses 0600 permissions and requires user opt-in

### WP02: Loopback Callback Handler

**Issue:** #561 (browser PKCE + device fallback)

**Scope:**
- `specify_cli/auth/loopback.py`: HTTP server + callback handler
- Port discovery and fallback
- State validation (CSRF protection)
- Timeout handling (5 minutes)
- Unit tests + integration tests

**Acceptance:**
- Server starts on available port in range 28888-28898
- Receives OAuth callback with code + state
- Validates state to prevent CSRF
- Timeout after 5 minutes of waiting
- Returns callback data to calling process

### WP03: Device Authorization Flow

**Issue:** #561 (browser PKCE + device fallback)

**Scope:**
- `specify_cli/auth/device_flow.py`: Device code request + polling
- Poll interval respecting SaaS hint
- User code formatting
- Timeout handling (≤15 minutes)
- Unit tests + integration tests

**Acceptance:**
- Device code request succeeds and returns user_code + verification_uri
- Polling respects SaaS interval and caps at 10s
- Authorization granted: returns access + refresh tokens
- Authorization denied: raises exception with clear message
- Timeout: raises exception after expires_in seconds

### WP04: Browser Login Flow (auth login)

**Issue:** #561 (browser PKCE + device fallback)

**Scope:**
- `spec-kitty auth login` command
- PKCE code_verifier generation (43 chars, cryptographically secure)
- Browser open (using Python `webbrowser` or equivalent)
- Loopback callback coordination
- Token exchange with SaaS
- Fallback to `--headless` if no browser detected
- Full end-to-end test against mock/real SaaS

**Acceptance:**
- `spec-kitty auth login` opens browser, user logs in, callback received, token stored
- `spec-kitty auth login --headless` requests device code, user enters code, token stored
- Browser not available: auto-fallback to device flow
- Timeout scenarios handled gracefully

### WP05: Logout Command (auth logout)

**Issue:** #561 or #562

**Scope:**
- `spec-kitty auth logout` command
- Server-side revocation at SaaS `/oauth/revoke`
- Local credential deletion
- Messaging for revocation failure (local deletion still succeeds)
- Unit + integration tests

**Acceptance:**
- `spec-kitty auth logout` revokes token + deletes local credentials
- Revocation failure doesn't block local deletion
- Status shows "Not authenticated" after logout
- 0 cases where local deletion fails due to revocation failure

### WP06: Status Command (auth status)

**Issue:** #562 or #565

**Scope:**
- `spec-kitty auth status` command
- Display authenticated user, org, scopes, expiry, storage backend, last refresh
- Handle unauthenticated case
- Color output for readability
- Unit tests

**Acceptance:**
- Shows authenticated user + org when logged in
- Shows token expiry times (access + refresh)
- Shows storage backend (Keychain | Credential Manager | File)
- Shows "Not authenticated" when no session

### WP07: HTTP Transport Rewiring (sync/client, tracker/saas_client)

**Issue:** #564 (auth transport rewiring)

**Scope:**
- `sync/client.py`: Replace direct token reads with TokenManager
- `tracker/saas_client.py`: Replace direct token reads with TokenManager
- `sync/background.py`, `sync/batch.py`, `sync/body_transport.py`: Use TokenManager
- 401 retry logic: auto-refresh + single retry
- Unit + integration tests for retry behavior
- Concurrency tests for single-flight refresh

**Acceptance:**
- All HTTP callers use TokenManager.get_access_token()
- 401 response triggers refresh + 1 retry
- Concurrent requests coordinate refresh (no thundering herd)
- Refresh SLO: <2s, non-blocking <3s to caller

### WP08: WebSocket Integration

**Issue:** #564 or separate

**Scope:**
- WebSocket auth + token refresh
- Refresh before connect
- Disconnect/401 handling (refresh + reconnect)
- Integration test with mock SaaS WebSocket

**Acceptance:**
- WebSocket connections are authenticated with fresh token
- 401 disconnect triggers refresh + reconnect
- Concurrent WebSocket clients coordinate refresh

### WP09: Password Removal & CLI Cleanup

**Issue:** #565 (legacy password-era removal)

**Scope:**
- Remove password prompts from `specify_cli/auth.py`
- Remove references to `/api/v1/token/` and `/api/v1/token/refresh/` (human CLI auth)
- Simplify `sync/auth.py` (remove password code, keep refresh only)
- Update help text + docs
- Deprecation warnings if applicable
- Unit tests for new behavior (no password prompts)

**Acceptance:**
- `spec-kitty auth login` does NOT prompt for username/password
- No code references to legacy password endpoints
- All tests pass with new auth flows

### WP10: Refresh Race Hardening & Concurrency Tests

**Issue:** #562 or part of WP07

**Scope:**
- Single-flight refresh lock implementation
- Concurrent request coordination tests
- `test_auth_concurrent_refresh.py` baseline preservation
- Stress test with 10+ concurrent 401s
- Verify 0 duplicate refreshes

**Acceptance:**
- 99.9% refresh success under concurrent load
- 0 duplicate concurrent refreshes
- test_auth_concurrent_refresh.py passes with new code

### WP11: Legacy Test Cleanup & Documentation

**Issue:** #565 or general cleanup

**Scope:**
- Document `test_auth_concurrent_refresh.py` as legacy baseline
- Retire password-related test fixtures
- Add new OAuth flow integration tests
- Update docs: auth.md, cli-auth-flow.md
- Changelog entry for hard cutover

**Acceptance:**
- All tests pass
- Documentation covers browser login, headless, logout, status
- Changelog describes hard cutover + migration instructions

---

## 12. Testing Strategy

### 12.1 Unit Tests

**TokenManager:**
- `test_token_manager_get_access_token_from_storage`
- `test_token_manager_refresh_single_flight` (with mocked storage + refresh endpoint)
- `test_token_manager_refresh_concurrent_requests` (verify 1 refresh, N waiting requests)
- `test_token_manager_refresh_on_expired_token`
- `test_token_manager_refresh_on_invalid_grant_raises`

**Secure Storage:**
- `test_storage_keychain_store_and_load` (macOS only or mocked)
- `test_storage_file_store_and_load_with_0600_perms`
- `test_storage_file_fallback_prompt` (user opts in)
- `test_storage_file_fallback_reject` (user opts out)
- `test_storage_delete_removes_credentials`
- `test_storage_backend_detection`

**Loopback Callback:**
- `test_loopback_starts_and_listens_on_available_port`
- `test_loopback_validates_csrf_state`
- `test_loopback_timeout_after_5_minutes`
- `test_loopback_callback_extraction`

**Device Flow:**
- `test_device_flow_request_device_code`
- `test_device_flow_polling_authorization_pending`
- `test_device_flow_polling_access_denied`
- `test_device_flow_polling_slow_down` (increase interval)
- `test_device_flow_timeout_after_expires_in`

### 12.2 Integration Tests

**Browser Login:**
- `test_auth_login_interactive_full_flow` (with SaaS mock or staging)
- `test_auth_login_browser_not_available_fallback_to_headless`
- `test_auth_login_callback_timeout`
- `test_auth_login_network_error_during_token_exchange`

**Headless Login:**
- `test_auth_login_headless_full_flow` (with SaaS mock or staging)
- `test_auth_login_headless_user_denies_consent`
- `test_auth_login_headless_timeout_after_15_minutes`

**Logout:**
- `test_auth_logout_revokes_server_side` (with SaaS mock)
- `test_auth_logout_deletes_local_credentials`
- `test_auth_logout_server_revocation_fails_local_deletion_succeeds`

**Status:**
- `test_auth_status_authenticated` (displays user, org, expiry, storage)
- `test_auth_status_not_authenticated` (displays "Not authenticated")

**HTTP Retry:**
- `test_http_client_401_triggers_refresh_and_retry` (sync/client.py)
- `test_http_client_401_after_refresh_still_401` (user must re-login)
- `test_http_client_concurrent_401s_single_refresh` (single-flight)

**WebSocket:**
- `test_websocket_refreshes_before_connect`
- `test_websocket_401_disconnect_refresh_and_reconnect`

### 12.3 Concurrency & Stress Tests

**Refresh Coordination:**
- 10+ concurrent requests all hit 401 → single refresh, N waiting requests succeed
- Verify no duplicate refresh-token exchanges
- Measure refresh SLO (<2s exchange, <3s to caller)

**Token Expiry:**
- Access token expires after ≤24 hours; automatic refresh succeeds
- Refresh token expires after ≤30 days; expired token flow works
- Stale-token detection + re-login flow

**File Fallback Stress:**
- Concurrent store/load of credentials from file
- Verify 0600 permissions integrity across concurrent access

### 12.4 End-to-End Tests

**Full User Journey:**
1. First-time user: `spec-kitty auth login` → browser → storage → subsequent calls work
2. Token expiry: Wait/simulate token expiry → next API call refreshes → succeeds
3. Logout: `spec-kitty auth logout` → credentials deleted → next API call fails with "Not authenticated"
4. Device flow: Headless SSH session → device code → user logs in elsewhere → tokens received

**SaaS Integration:**
- All tests run against SaaS staging or mock (per epic #49 contract)
- Verify exact request/response format compliance

---

## 13. Assumptions

1. **SaaS OAuth endpoints exist and follow RFC 6749/RFC 7636/RFC 8628 standards.** Epic #49 will define exact details; this spec assumes standard patterns.

2. **Client ID and scopes are pre-configured in SaaS.** CLI does not dynamically register; SaaS admin provisions `CLI_CLIENT_ID`.

3. **OS keystore libraries (e.g., `keyring` Python package) work cross-platform.** Fallback to file if unavailable.

4. **Browser access for interactive login is available in >95% of use cases.** Device flow covers the <5% (SSH, remote, etc.).

5. **Token expiry SLOs (access ≤24h, refresh ≤30d) are acceptable for this CLI.** SaaS may use shorter/longer; CLI adapts.

6. **Single-flight refresh coordination via `asyncio.Lock` is sufficient.** No distributed lock required (CLI is single-process).

7. **WebSocket connections are authenticated separately or share the same token.** Spec assumes same token; SaaS may differ per epic #49.

8. **Existing `test_auth_concurrent_refresh.py` is preserved as a baseline reference.** New tests supplement, not replace.

9. **No machine/service authentication is in scope.** Separate future epic; this spec is human CLI only.

10. **File fallback is for truly degraded environments, not a permanent solution.** UX will be clear about limitations.

---

## 14. References & ADRs

- **Epic #559**: Browser-mediated CLI auth against spec-kitty-saas (parent epic)
- **Epic #49**: SaaS-side OAuth/OIDC auth system (parallel, source of truth for contracts)
- **Issue #560**: ADR supersession (architectural decision)
- **Issue #561**: Browser PKCE + device fallback
- **Issue #562**: TokenManager + keychain storage
- **Issue #564**: Auth transport rewiring
- **Issue #565**: Legacy password-era removal
- **ADR**: `architecture/2.x/adr/2026-04-09-2-cli-saas-auth-is-browser-mediated-oauth-not-password.md`
- **RFC 6749**: OAuth 2.0 Authorization Framework
- **RFC 7636**: Proof Key for Public OAuth 2.0 Authorization Code Flow (PKCE)
- **RFC 8628**: OAuth 2.0 Device Authorization Grant (Device Flow)
- **RFC 8252**: OAuth 2.0 for Native Apps

---

## 15. Open Questions for SaaS Contract (Epic #49)

1. **OIDC vs OAuth2 Only**: Should the CLI request OIDC ID tokens in addition to access tokens? (Spec assumes OAuth2 access tokens only; OIDC is optional.)

2. **Scope Granularity**: Are the scopes (e.g., `read:orgs`, `write:projects`) determined by SaaS or CLI configuration?

3. **Token Signing**: Are access/refresh tokens JWTs or opaque? (Spec assumes opaque; JWT details TBD by SaaS.)

4. **Rate Limiting**: Are there rate limits on `/oauth/token` (refresh) or `/oauth/device/token` (polling)?

5. **Consent Flow**: Does SaaS show a consent screen or auto-approve certain scopes for CLI client?

6. **Multi-org Support**: Can a user authenticate once and switch organizations, or must they re-authenticate per org?

---

## 16. Success Criteria (Measurable)

- [x] 95%+ interactive logins use browser/PKCE within 30 days of GA
- [x] 0 supported human CLI flows prompt for or accept passwords after cutover
- [x] 99.9% token refresh success SLO (≤3 failures per 10,000 refreshes)
- [x] 0 cases of valid user forced to re-login due to refresh bugs or staleness
- [x] Logout + revocation reliably terminate access within 5 seconds
- [x] OS keystore used by default; file fallback only when unavailable
- [x] 0 Sev1/Sev2 security incidents related to password collection or token mishandling
- [x] Headless users can authenticate in <90 seconds (excluding SaaS login time)

---

## End of Specification

**Next Phase**: `/spec-kitty.plan` will decompose requirements into detailed task workflows, resource allocation, and timeline.
