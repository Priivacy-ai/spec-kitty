# Quickstart: Browser-Mediated OAuth CLI Authentication Implementation

**Mission**: 080-browser-mediated-oauth-cli-auth  
**Phase**: Phase 1 Design  
**Status**: Ready for Implementation  
**Target Branch**: main

---

## Implementation Overview

This guide describes the recommended sequence and integration points for implementing browser-mediated OAuth/OIDC authentication for the spec-kitty CLI, replacing the current password-based SaaS login flow.

**Key phases**:
1. **Foundation** (WP01-WP02): Loopback callback, device flow poller, TokenManager + secure storage
2. **Integration** (WP03-WP05): OAuth flows, token refresh, HTTP/batch/background transport
3. **Commands & UX** (WP06-WP08): Login command, status, logout, error messaging
4. **Finalization** (WP09-WP11): Testing, migration, password removal, staging validation

---

## File Structure

**New directories**:
```
spec_kitty/
├── auth/                           # NEW: OAuth/OIDC + session management
│   ├── __init__.py
│   ├── session.py                  # StoredSession dataclass, validation
│   ├── token_manager.py            # TokenManager (orchestration)
│   ├── secure_storage/
│   │   ├── __init__.py
│   │   ├── abstract.py             # SecureStorage base class
│   │   ├── keychain.py             # macOS Keychain backend
│   │   ├── credential_manager.py   # Windows Credential Manager backend
│   │   ├── secret_service.py       # Linux Secret Service backend
│   │   ├── file_fallback.py        # File backend (0600 permissions)
│   │   ├── platform_detector.py    # Detect available backends
│   │   └── factory.py              # Backend selection + initialization
│   ├── flows/
│   │   ├── __init__.py
│   │   ├── authorization_code.py   # PKCE authorization code flow
│   │   ├── device_code.py          # Device authorization flow + polling
│   │   └── refresh.py              # Token refresh logic
│   ├── loopback/
│   │   ├── __init__.py
│   │   ├── callback_server.py      # HTTP server for loopback callback
│   │   ├── state_manager.py        # PKCEState persistence + validation
│   │   └── browser_launcher.py     # Cross-platform browser launch
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── token_provisioner.py    # Pre-connect refresh + ws-token acquisition
│   │   └── session_binder.py       # WebSocket auth via query parameter
│   ├── http/
│   │   ├── __init__.py
│   │   ├── transport.py            # HTTP client with OAuth integration
│   │   ├── retry_handler.py        # 401 retry with auto-refresh
│   │   └── bearer_provider.py      # Inject bearer token into requests
│   └── errors.py                   # OAuth error types, CLI error messages

tests/
├── auth/                           # NEW: Auth subsystem tests
│   ├── test_token_manager.py       # TokenManager unit tests
│   ├── test_secure_storage.py      # Storage backend tests
│   ├── test_authorization_code_flow.py
│   ├── test_device_code_flow.py
│   ├── test_loopback_callback.py
│   ├── test_websocket_provisioning.py
│   ├── test_http_integration.py
│   └── test_concurrent_refresh.py  # Concurrency, single-flight refresh
```

**Modified directories**:
```
spec_kitty/
├── commands/
│   ├── auth.py                     # MODIFIED: New login_interactive, login_headless, logout
│   ├── status.py                   # MODIFIED: Display current session info
│   └── ...
├── sync/
│   ├── auth.py                     # MODIFIED: Token retrieval now via TokenManager
│   ├── client.py                   # MODIFIED: Use new HTTP transport
│   ├── batch.py                    # MODIFIED: Token provisioning
│   ├── background.py               # MODIFIED: Token provisioning
│   ├── body_transport.py           # MODIFIED: Use new HTTP transport
│   └── sync_status.py              # MODIFIED: Display session info
├── tracker/
│   └── saas_client.py              # MODIFIED: Use TokenManager + HTTP transport
```

---

## Core Components

### 1. TokenManager

**Purpose**: Single entry point for credential provisioning, refresh, and lifecycle management

**Location**: `spec_kitty/auth/token_manager.py`

**Public interface**:
```python
class TokenManager:
    def __init__(self, secure_storage: SecureStorage, http_client):
        """Initialize TokenManager with storage backend."""
    
    async def load_from_storage(self) -> Optional[StoredSession]:
        """Load stored session from secure storage."""
    
    async def login_interactive(self, browser_launcher) -> StoredSession:
        """Browser-mediated login (Authorization Code + PKCE)."""
    
    async def login_headless(self) -> StoredSession:
        """Headless login (Device Authorization Flow)."""
    
    async def get_access_token(self) -> str:
        """Return current access token (refresh if needed)."""
    
    async def ensure_fresh(self, min_ttl_seconds=300):
        """Ensure access token is valid; refresh if expiring soon."""
    
    async def refresh_if_needed(self) -> bool:
        """Refresh access token if expired; return success/failure."""
    
    async def logout(self) -> bool:
        """Revoke session via SaaS + delete local credentials."""
    
    def get_current_session(self) -> Optional[StoredSession]:
        """Get current session (synchronous access)."""
    
    @property
    def is_authenticated(self) -> bool:
        """Return True if session exists and not expired."""
```

**Key behaviors**:
- Single-flight refresh coordination (asyncio.Lock prevents concurrent refreshes)
- Lazy refresh (check expiry before returning token)
- Auto-refresh on 401 API response (via retry handler)
- Secure storage abstraction (swappable backends)
- Thread-safe access (sync wrapper for async internals)

**Integration**: All HTTP, batch, background, tracker, and WebSocket callers use TokenManager

### 2. SecureStorage Abstraction

**Purpose**: Pluggable storage backend (Keychain, Credential Manager, Secret Service, file)

**Location**: `spec_kitty/auth/secure_storage/`

**Public interface**:
```python
class SecureStorage(ABC):
    async def read(self) -> Optional[StoredSession]:
        """Read session from storage; return None if missing/corrupt."""
    
    async def write(self, session: StoredSession):
        """Write session to storage."""
    
    async def delete(self):
        """Delete session from storage."""
    
    @property
    def name(self) -> str:
        """Backend name (keychain, credential_manager, secret_service, file)."""
```

**Concrete backends**:

| Backend | Platform | Implementation |
|---------|----------|-----------------|
| **Keychain** | macOS | `SecureStorageKeychain` → OS Keychain API |
| **Credential Manager** | Windows | `SecureStorageCredentialManager` → Win32 API |
| **Secret Service** | Linux | `SecureStorageSecretService` → D-Bus Secret Service |
| **File Fallback** | All | `SecureStorageFile` → `~/.config/spec-kitty/credentials.json` (0600) |

**Factory**: `secure_storage.factory.get_default_storage()` auto-detects and initializes appropriate backend

**File fallback workflow**:
1. Try Keychain/Credential Manager/Secret Service
2. If unavailable: prompt user ("Secure storage unavailable; store credentials in file?")
3. If user declines: no session saved; logout on exit
4. If user accepts: save to file with 0600 permissions

### 3. Authorization Code Flow (Browser)

**Purpose**: Primary interactive login flow

**Location**: `spec_kitty/auth/flows/authorization_code.py`

**Flow**:
```
User runs: spec-kitty auth login

1. Generate PKCEState (code_verifier, code_challenge, state)
2. Construct authorization URL
3. Open browser to authorization endpoint
4. Listen on localhost:PORT for callback
5. Receive code + state from callback
6. Validate state (CSRF check)
7. Exchange code for tokens via /oauth/token + code_verifier
8. Store tokens in secure storage
9. Show "Successfully logged in" message
```

**Key classes**:
- `PKCEState`: Cryptographic state + challenge (RFC 7636)
- `AuthorizationCodeFlow`: Orchestration + error handling

### 4. Device Authorization Flow (Headless)

**Purpose**: Fallback for environments without browser (CI/CD, remote servers)

**Location**: `spec_kitty/auth/flows/device_code.py`

**Flow**:
```
User runs: spec-kitty auth login --headless

1. Call /oauth/device → get device_code, user_code, verification_uri
2. Display user_code and verification_uri to user
3. Start polling loop: call /oauth/token with device_code every interval seconds
4. Wait for approval:
   - User opens verification_uri in browser, enters user_code
   - User approves in SaaS browser UI
5. Polling receives tokens in response
6. Store tokens in secure storage
7. Show "Successfully logged in" message
```

**Key classes**:
- `DeviceFlowState`: Device code, user code, polling state
- `DeviceCodePoller`: Polling loop with exponential backoff, timeout handling

### 5. Loopback Callback Handler

**Purpose**: HTTP server listening on localhost for authorization code callback

**Location**: `spec_kitty/auth/loopback/`

**Components**:
- `CallbackServer`: Minimal HTTP server (127.0.0.1:PORT)
- `StateManager`: PKCEState persistence + validation
- `BrowserLauncher`: Cross-platform browser launch

**Callback validation**:
1. Verify query params include `code` and `state`
2. Look up `state` in local PKCEState store
3. Validate `state` matches original request (CSRF check)
4. Return HTTP 200 with success message (or error if validation fails)
5. Extract `code` + `state` for token exchange

**Port selection**:
- Try standard ports first (8080, 8081, ...)
- Fall back to OS-assigned port if needed
- Report port to user if non-standard

### 6. HTTP Transport Integration

**Purpose**: Bearer token injection + 401 retry with auto-refresh

**Location**: `spec_kitty/auth/http/`

**Components**:
- `OAuthHttpClient`: HTTP client with OAuth integration
- `RetryHandler`: 401 response handling + auto-refresh
- `BearerProvider`: Token injection into `Authorization` header

**Behavior**:
```
HTTP request:
  1. Get access token from TokenManager
  2. Add Authorization: Bearer <token> header
  3. Send request
  4. If 401 response:
     a. Try refresh via TokenManager
     b. Retry request (1x) with new token
     c. If retry succeeds: return response
     d. If retry fails: propagate 401 (force re-login)
  5. If other response: return as-is
```

### 7. WebSocket Pre-Connect Token Provisioning

**Purpose**: Refresh access token before WebSocket upgrade; obtain ephemeral WS token

**Location**: `spec_kitty/auth/websocket/`

**Components**:
- `TokenProvisioner`: Pre-connect refresh + ws-token acquisition
- `SessionBinder`: Bind session to WebSocket upgrade (query parameter)

**Behavior**:
```
Before WebSocket connection:
  1. Check access_token_expires_at
  2. If expires within 5 min: refresh via /oauth/token
  3. Call /api/v1/ws-token → receive ws_token
  4. WebSocket upgrade with ?token=ws_token
```

---

## Integration Points

### Commands Layer

**New commands**:
- `spec-kitty auth login` → interactive browser login
- `spec-kitty auth login --headless` → device flow login
- `spec-kitty auth logout` → revoke session + cleanup
- `spec-kitty auth status` → display current session (user, team, token expiry)

**Modified commands**:
- All commands using SaaS API: check TokenManager.is_authenticated before proceeding

### Transport Layer

**HTTP clients**:
- `sync/client.py`: Use OAuthHttpClient
- `tracker/saas_client.py`: Use OAuthHttpClient
- `sync/background.py`, `sync/batch.py`: Use TokenManager for token provisioning

**Batch/Background operations**:
- Pre-connect: obtain access token
- Send token with request
- On 401: retry with refresh (via HTTP transport retry handler)

**WebSocket**:
- Pre-connect: ensure fresh access token (refresh if needed)
- Obtain ephemeral WS token via /api/v1/ws-token
- Connect with ?token=ws_token

### Status Display

**`spec-kitty status` output**:
```
Authentication:
  Status: Logged in
  User: alice@example.com (u_alice)
  Team: Acme Corp (tm_acme)
  Access token expires in: 45 minutes
  Refresh token expires in: 89 days
  Storage backend: macOS Keychain
```

**On token expiry**:
- Display in status (red if <5 min remaining)
- Auto-refresh on API call (transparent to user)
- Force re-login message if refresh fails

---

## Dependencies

### External Libraries

| Library | Purpose | Version |
|---------|---------|---------|
| `httpx` | Async HTTP client (with OAuth integration) | ≥0.24.0 |
| `keyring` | OS Keychain abstraction | ≥23.0 |
| `secretstorage` | Linux Secret Service client | ≥3.3.0 (Linux only) |
| `pyobjc-framework-Cocoa` | macOS Keychain API (if not using `keyring`) | ≥9.0 (macOS only) |
| `pydantic` | Data validation (StoredSession, etc.) | ≥2.0 |
| `rich` | Console output (auth messages) | Already present |

### Internal Dependencies

| Module | Purpose |
|--------|---------|
| `spec_kitty.config` | Config file paths, client_id |
| `spec_kitty.logger` | Logging |
| `spec_kitty.errors` | Exception types |
| `spec_kitty.platform_utils` | Cross-platform utilities (browser launch, etc.) |

---

## Implementation Sequence

**Recommended implementation order** (work packages WP01-WP11):

### Phase 1: Foundation (WP01-WP02)

**WP01: Loopback Callback + PKCE State**
- Implement `PKCEState` dataclass + generation
- Implement loopback HTTP server (CallbackServer)
- Implement callback URL validation + state verification
- Unit tests: state generation, callback validation
- Integration: manual testing with OAuth provider

**WP02: Device Code Flow Poller**
- Implement `DeviceFlowState` dataclass
- Implement device code polling loop
- Implement backoff + timeout handling
- Unit tests: state transitions, polling logic
- Integration: manual testing with OAuth provider

### Phase 2: Core TokenManager (WP03-WP05)

**WP03: SecureStorage Abstraction + Backends**
- Implement `SecureStorage` base class
- Implement all backends (Keychain, Credential Manager, Secret Service, File)
- Implement backend auto-detection + factory
- Implement file fallback workflow (user prompt, 0600 permissions)
- Unit tests: read/write/delete for each backend
- Integration: test cross-platform storage behavior

**WP04: TokenManager Orchestration**
- Implement `StoredSession` dataclass + validation
- Implement `TokenManager` core (load, authenticate, refresh, logout)
- Implement authorization code flow orchestration
- Implement single-flight refresh coordination (asyncio.Lock)
- Unit tests: auth flows, refresh logic, state transitions
- Integration: end-to-end browser + device flow testing

**WP05: HTTP Transport + 401 Retry**
- Implement `OAuthHttpClient` wrapper
- Implement `RetryHandler` (401 response → auto-refresh → retry)
- Integrate TokenManager with existing HTTP clients
- Unit tests: 401 handling, retry logic
- Integration: test with real SaaS endpoints

### Phase 3: Commands & UX (WP06-WP08)

**WP06: Login Command (Browser + Headless)**
- Implement `spec-kitty auth login` → browser flow
- Implement `spec-kitty auth login --headless` → device flow
- Implement progress messages, error handling, success confirmation
- Unit tests: command interface
- Integration: end-to-end user flows

**WP07: Status & Logout Commands**
- Implement `spec-kitty auth status` (display current session)
- Implement `spec-kitty auth logout` (revoke + delete)
- Implement expiry warnings in status display
- Unit tests: command interface
- Integration: test with stored sessions

**WP08: WebSocket Pre-Connect Provisioning**
- Implement pre-connect token refresh
- Implement `/api/v1/ws-token` acquisition
- Integrate with WebSocket connections
- Unit tests: token provisioning logic
- Integration: WebSocket endpoint connectivity

### Phase 4: Finalization (WP09-WP11)

**WP09: Testing Suite**
- Implement unit tests (100% coverage for new modules)
- Implement integration tests (auth flows, transport, commands)
- Implement concurrency tests (refresh coordination, multiple clients)
- Implement end-to-end tests (full login → API call → logout)
- Add to CI/CD (staging environment testing)

**WP10: Password Removal & Cutover**
- Remove password collection from auth.py
- Remove password-based token endpoints from all transports
- Remove legacy test fixtures
- Update migration guide for users
- Hard cutover (no password fallback at GA)

**WP11: Staging Validation & Release Prep**
- Deploy to staging environment
- Run full test suite against staging SaaS
- Validate 72+ hour staging window (no critical bugs)
- Update documentation (user guide, operator runbook)
- Prepare release notes

---

## Key Decisions & Trade-offs

### Authentication Architecture

**Decision**: Single TokenManager entry point (not per-command token caching)

**Rationale**:
- Simplifies token lifecycle management
- Centralizes refresh logic (single-flight coordination)
- Enables automatic 401 retry with refresh
- Reduces duplicate token storage

**Alternative**: Per-command token caches (rejected: harder to synchronize, more storage copies)

### Secure Storage

**Decision**: Keychain-first with file fallback

**Rationale**:
- Keychain/Credential Manager: OS-managed encryption at rest
- File fallback: Degrades gracefully when OS storage unavailable
- User control: Prompt before falling back to file

**Alternative**: Always use file (rejected: weaker security, no user choice)

### Concurrency Model

**Decision**: asyncio.Lock for single-flight refresh (async core, sync boundaries)

**Rationale**:
- Prevents thundering herd on refresh endpoint
- Single concurrent refresh maximizes efficiency
- Waiters get result without duplicate RPC
- Works across async/sync boundary via executor

**Alternative**: Thread-local locks (rejected: less efficient for high concurrency)

### Migration Strategy

**Decision**: Hard cutover (no password fallback at GA)

**Rationale**:
- Forces complete migration (no legacy code debt)
- Reduces test maintenance (no dual-code paths)
- Improves security (no mixed auth methods)

**Timeline**: 72+ hour staging validation before cutover

### Error Messaging

**Decision**: User-friendly messages in CLI, structured errors to logs

**Rationale**:
- Users get actionable guidance ("Visit https://... and enter ABCD-1234")
- Operators get structured logs for debugging
- Errors map to clear recovery paths

---

## Testing Strategy

### Unit Tests

**Coverage**: 90%+ for new code

**Modules**:
- `token_manager.py`: State transitions, refresh logic, auth flows
- `secure_storage/`: Backend read/write/delete, auto-detection
- `loopback/`: State validation, callback parsing
- `flows/`: PKCE generation, device code polling
- `http/`: Bearer token injection, 401 retry

### Integration Tests

**Scenarios**:
- Browser login (mock loopback callback)
- Headless login (mock device code polling)
- Token refresh (mock token endpoint)
- 401 retry (mock API endpoint with 401)
- Logout (mock logout endpoint)
- WebSocket pre-connect (mock ws-token endpoint)

**Environment**: Staging SaaS (real endpoints, test credentials)

### Concurrency Tests

**Scenarios**:
- 10+ concurrent token refreshes (verify single-flight)
- Concurrent API calls on expired token (verify 1x refresh, 1x retry)
- Multiple WebSocket connections (verify independent provisioning)
- Concurrent CLI instances (verify file lock coordination)

### End-to-End Tests

**User journeys**:
- First login → API call → logout → verify no lingering session
- Headless login → background task with auto-refresh → logout
- WebSocket connection → live updates → disconnect → re-connect
- Token expiry → auto-refresh → continue working (transparent)

---

## Staging Validation Runbook

**Before GA cutover**: 72+ hours in staging environment

**Checklist**:
- [ ] All WPs implemented and merged to main
- [ ] Full test suite passing (unit + integration + E2E)
- [ ] Staging environment deployed with new auth
- [ ] Manual testing: browser login, headless, status, logout
- [ ] Manual testing: auto-refresh on expired token
- [ ] Manual testing: WebSocket pre-connect + refresh
- [ ] Load testing: 100 concurrent logins (verify refresh coordination)
- [ ] Chaos testing: simulate network failures, timeout, 500s
- [ ] Documentation updated (user guide, operator runbook)
- [ ] Release notes prepared
- [ ] No critical issues found in staging
- [ ] Team sign-off on cutover

**Go/No-Go Decision**: SRE + product lead approval

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Browser adoption** | ≥95% of users | Usage telemetry |
| **Headless fallback** | ≥5% of users | Usage telemetry |
| **Auto-refresh SLO** | 99.9% success | Monitoring (refresh_attempts / refresh_success) |
| **Zero forced re-logins** | 0 per week | Incident tracking |
| **Token expiry messages** | <90s time-to-action | User feedback |
| **Keychain success rate** | ≥99% | Telemetry (storage_backend distribution) |
| **File fallback prompt acceptance** | ≥90% | User metrics |
| **WebSocket token provisioning** | <2s latency | Monitoring |

---

## Notes

- **Async/Sync Boundary**: TokenManager is internally async (uses asyncio); CLI commands use `asyncio.run()` to drive completion
- **Secure Storage**: If OS backend unavailable, file fallback prompt is mandatory (not silent)
- **Loopback Port**: CLI tries ports 8080-8090 before OS assignment
- **Token Expiry**: Access token ~1 hour, refresh token ~90 days (per SaaS contract)
- **Session Management**: session_id (from token response) enables logout + WebSocket binding
- **One Session Per User**: Only one stored session at a time; new login replaces previous
- **Logout Behavior**: Best-effort SaaS revocation + mandatory local cleanup
