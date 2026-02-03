# Feature Specification: CLI Authentication Module and Commands

**Feature Branch**: `027-cli-authentication-module-commands`
**Created**: 2026-02-03
**Status**: Draft
**Input**: P0 blocker extracted from Feature 009 - implement CLI-side authentication for spec-kitty sync

## Clarifications

### Session 2026-02-03

- Q: Token refresh behavior when JWT expires? → A: Auto-refresh silently in background, user never sees expiration
- Q: This feature extracted from Feature 009 due to scope? → A: Yes, CLI auth is the P0 blocker that must be completed before event emission or dashboards

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Logs In to Sync Service (Priority: P0)

A developer needs to authenticate their CLI installation with the SaaS server so they can sync work package events to the cloud dashboard.

**Why this priority**: Authentication is the foundational gate for all sync functionality. Without auth, no events can be sent to the server. This blocks Feature 009 (event emission + dashboards).

**Independent Test**: Can be fully tested by running `spec-kitty auth login`, entering valid credentials, and verifying the CLI stores tokens and can connect to the server.

**Acceptance Scenarios**:

1. **Given** developer has valid SaaS account credentials, **When** developer runs `spec-kitty auth login`, **Then** CLI prompts for username and password
2. **Given** developer enters valid credentials, **When** authentication succeeds, **Then** CLI stores access and refresh tokens securely and displays success message
3. **Given** developer enters invalid credentials, **When** authentication fails, **Then** CLI displays clear error message and does not store any tokens
4. **Given** developer is already logged in, **When** developer runs `spec-kitty auth login`, **Then** CLI informs user they are already authenticated and offers to re-authenticate

---

### User Story 2 - Developer Logs Out from Sync Service (Priority: P1)

A developer needs to log out from the sync service to clear stored credentials, either for security reasons or to switch accounts.

**Why this priority**: Logout is essential for security hygiene and multi-account scenarios, but is secondary to the ability to log in.

**Independent Test**: Can be fully tested by running `spec-kitty auth logout` after being logged in and verifying credentials are removed.

**Acceptance Scenarios**:

1. **Given** developer is logged in with stored credentials, **When** developer runs `spec-kitty auth logout`, **Then** CLI removes all stored tokens and displays confirmation
2. **Given** developer is not logged in, **When** developer runs `spec-kitty auth logout`, **Then** CLI displays message that no active session exists
3. **Given** developer logs out, **When** developer attempts sync operation, **Then** CLI prompts user to log in first

---

### User Story 3 - CLI Automatically Refreshes Expired Tokens (Priority: P0)

A developer working for an extended period needs the CLI to automatically refresh tokens in the background so their session continues without interruption.

**Why this priority**: Silent token refresh is critical for developer experience during long work sessions. Without it, users would be interrupted every 15 minutes (access token TTL).

**Independent Test**: Can be fully tested by logging in, waiting for access token to expire (or simulating expiration), then performing a sync operation and verifying it succeeds without user intervention.

**Acceptance Scenarios**:

1. **Given** access token has expired but refresh token is valid, **When** CLI attempts any authenticated operation, **Then** CLI automatically obtains new access token and completes operation without user prompt
2. **Given** both access and refresh tokens have expired, **When** CLI attempts authenticated operation, **Then** CLI prompts user to re-authenticate
3. **Given** token refresh succeeds, **When** new tokens are obtained, **Then** CLI updates stored credentials silently

---

### User Story 4 - Developer Checks Authentication Status (Priority: P2)

A developer needs to verify their current authentication status to troubleshoot connection issues or confirm which account is active.

**Why this priority**: Status checking is a convenience feature for troubleshooting, not required for core sync functionality.

**Independent Test**: Can be fully tested by running `spec-kitty auth status` and verifying it shows correct login state.

**Acceptance Scenarios**:

1. **Given** developer is logged in, **When** developer runs `spec-kitty auth status`, **Then** CLI displays username/email, server URL, and token validity status
2. **Given** developer is not logged in, **When** developer runs `spec-kitty auth status`, **Then** CLI displays "Not authenticated" message
3. **Given** developer has expired tokens, **When** developer runs `spec-kitty auth status`, **Then** CLI displays token expiration status

---

### Edge Cases

**Network Failure During Login:**
- **Given** developer enters valid credentials but network fails during token request, **When** request times out, **Then** CLI displays network error and suggests checking connectivity

**Credential File Permissions:**
- **Given** credentials file exists with wrong permissions, **When** CLI attempts to read/write credentials, **Then** CLI displays permission error and suggests fix (chmod 600)

**Corrupted Credential File:**
- **Given** credentials file is corrupted or malformed, **When** CLI attempts to load credentials, **Then** CLI treats as logged out and suggests re-authenticating

**Server Unavailable:**
- **Given** SaaS server is down or unreachable, **When** developer attempts login, **Then** CLI displays server unavailable error with retry suggestion

**Token Refresh Race Condition:**
- **Given** multiple CLI processes attempt token refresh simultaneously, **When** refreshes overlap, **Then** only one refresh succeeds, others use updated token (file locking)

**Account Disabled/Deleted:**
- **Given** user account is disabled on server, **When** CLI attempts token refresh, **Then** CLI receives 401, clears stored credentials, and prompts re-authentication

---

## Requirements *(mandatory)*

### Functional Requirements

#### Auth Module (sync/auth.py)

- **FR-001**: CLI MUST provide an `AuthClient` class that handles all authentication operations
- **FR-002**: CLI MUST implement `obtain_tokens(username, password)` function that calls the SaaS `/api/v1/token/` endpoint
- **FR-003**: CLI MUST implement `refresh_tokens(refresh_token)` function that calls the SaaS `/api/v1/token/refresh/` endpoint
- **FR-004**: CLI MUST implement `obtain_ws_token(access_token)` function that calls the SaaS `/api/v1/ws-token/` endpoint
- **FR-005**: CLI MUST implement `is_authenticated()` function that checks for valid stored credentials
- **FR-006**: CLI MUST implement `get_access_token()` function that returns valid access token, auto-refreshing if expired
- **FR-007**: CLI MUST implement `clear_credentials()` function that removes all stored tokens

#### Credential Storage

- **FR-008**: CLI MUST store credentials in `~/.spec-kitty/credentials` file
- **FR-009**: CLI MUST set credentials file permissions to 600 (owner read/write only)
- **FR-010**: CLI MUST store both access token and refresh token
- **FR-011**: CLI MUST store token expiration timestamps for refresh logic
- **FR-012**: CLI MUST create `~/.spec-kitty/` directory if it does not exist
- **FR-013**: CLI MUST use file locking when reading/writing credentials to prevent race conditions

#### Auth Commands

- **FR-014**: CLI MUST provide `spec-kitty auth login` command for user authentication
- **FR-015**: CLI MUST prompt for username and password during login (password input hidden)
- **FR-016**: CLI MUST provide `spec-kitty auth logout` command to clear stored credentials
- **FR-017**: CLI MUST provide `spec-kitty auth status` command to display authentication state
- **FR-018**: CLI MUST display clear success/error messages for all auth operations

#### Token Lifecycle

- **FR-019**: CLI MUST automatically refresh access token when expired and refresh token is valid
- **FR-020**: CLI MUST perform token refresh silently without user interaction
- **FR-021**: CLI MUST prompt for re-authentication when refresh token expires
- **FR-022**: CLI MUST handle 401 responses by attempting token refresh before failing

#### Error Handling

- **FR-023**: CLI MUST display user-friendly error messages for authentication failures
- **FR-024**: CLI MUST distinguish between invalid credentials, network errors, and server errors
- **FR-025**: CLI MUST not expose sensitive token data in error messages or logs

### Key Entities

- **Access Token**: Short-lived JWT (15 min TTL) used for API authentication; stored in credentials file
- **Refresh Token**: Long-lived JWT (7 day TTL) used to obtain new access tokens; stored in credentials file
- **WebSocket Token**: Ephemeral token (15 min TTL) exchanged from access token for WebSocket connections; not stored, obtained on-demand
- **Credentials File**: TOML file at `~/.spec-kitty/credentials` containing tokens and metadata; permissions 600

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can authenticate with CLI using valid SaaS credentials in under 10 seconds
- **SC-002**: CLI maintains authenticated session for 7+ days without requiring manual re-login (via silent refresh)
- **SC-003**: Developer can verify authentication status with a single command
- **SC-004**: CLI handles all authentication errors with clear, actionable messages
- **SC-005**: Credentials are stored securely with appropriate file permissions (not readable by other users)
- **SC-006**: Token refresh happens automatically without any user intervention or visible delay

---

## Assumptions *(optional)*

- SaaS authentication endpoints (`/api/v1/token/`, `/api/v1/token/refresh/`, `/api/v1/ws-token/`) are implemented and operational (Feature 008)
- Server URL is configured via `~/.spec-kitty/config.toml` (existing SyncConfig class)
- Access token TTL is 15 minutes, refresh token TTL is 7 days (Feature 008 configuration)
- CLI is running on systems with standard POSIX file permissions

---

## Dependencies *(optional)*

- **Feature 008: Sync Protocol REST + WebSocket** - Provides the SaaS-side authentication endpoints this feature calls
- **Existing CLI Infrastructure**: `SyncConfig` class for server URL, `~/.spec-kitty/` directory structure

---

## Constraints *(mandatory)*

### Repository and Branch

**CRITICAL**: All implementation work for this feature MUST be done on the **spec-kitty 2.x branch**, NOT main.

- Base branch: `2.x`
- All work packages branch from and merge back to `2.x`
- Do NOT merge to `main`

### Security

- Credentials file MUST have 600 permissions (owner-only access)
- Passwords MUST NOT be stored locally (only tokens)
- Token values MUST NOT appear in logs or error messages
- HTTPS MUST be used for all authentication requests

### Compatibility

- MUST work with existing `WebSocketClient` that expects a token parameter
- MUST integrate with existing CLI command structure (Click framework)
- MUST work on macOS, Linux, and Windows (POSIX and Windows file permissions)

---

## References

### Feature 009 Research (CLI Auth Context)

- `kitty-specs/009-cli-saas-event-sync-dashboards/research.md` - Documents SaaS auth endpoints
- `kitty-specs/009-cli-saas-event-sync-dashboards/data-model.md` - API contract details

### Feature 008 Implementation (SaaS Auth Endpoints)

- `POST /api/v1/token/` - Username/password → access + refresh tokens
- `POST /api/v1/token/refresh/` - Refresh token → new access token
- `POST /api/v1/ws-token/` - Access token → ephemeral WebSocket token
- JWT configuration: 15 min access TTL, 7 day refresh TTL, rotation enabled

### CLI Repository (spec-kitty 2.x branch)

- `src/specify_cli/sync/auth.py` - Target file for auth module (currently empty)
- `src/specify_cli/sync/client.py` - WebSocketClient that needs auth integration
- `src/specify_cli/sync/config.py` - SyncConfig for server URL

---

**END OF SPECIFICATION**
