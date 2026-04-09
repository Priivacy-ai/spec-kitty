# Work Package Decomposition: Browser-Mediated OAuth CLI Authentication

**Mission**: 080-browser-mediated-oauth-cli-auth  
**Date**: 2026-04-09  
**Total Work Packages**: 11  
**Total Subtasks**: 91  
**Target Branch**: main

---

## Executive Summary

This feature replaces password-based CLI authentication with browser-mediated OAuth 2.0. Work is organized into 11 focused work packages: 2 foundational flow implementations (loopback + device), 1 storage layer, 4 core token/auth management, 1 HTTP transport, 1 CLI commands, 1 comprehensive testing, and 1 migration/release.

**Size Distribution**:
- **Average subtasks per WP**: 8.3
- **Range**: 7-10 subtasks per WP
- **Estimated total prompt lines**: ~3800-4200 (350-450 per WP)
- **All WPs within ideal range** (none exceeding 700 lines)

**Parallelization**:
- **Phase 1 (Foundation)**: WP01 + WP02 (loopback, device flow) → can run in parallel
- **Phase 2 (Storage & Core)**: WP03 + WP04 (after Phase 1 logic complete)
- **Phase 3 (Auth Flows)**: WP05 + WP06 (after Phase 2)
- **Phase 4 (Integration)**: WP07 + WP08 + WP09 (after Phase 3)
- **Phase 5 (Hardening)**: WP10 + WP11 (final cutover)

**MVP Scope**: Complete WP01-WP09 (all user-facing features); WP10-WP11 are migration/release (defer if timeline tight, but must complete before GA).

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|----|----|----|
| T001 | Create PKCEState dataclass and model | WP01 | |
| T002 | Implement PKCE code_verifier generation (43 chars, RFC 7636) | WP01 | |
| T003 | Implement PKCE code_challenge generation (SHA256 base64url) | WP01 | |
| T004 | Create CallbackServer HTTP server (localhost loopback) | WP01 | |
| T005 | Implement callback URL parsing and state validation | WP01 | |
| T006 | Create StateManager for transient PKCE state persistence | WP01 | |
| T007 | Implement cross-platform browser launcher | WP01 | [P] |
| T008 | Write unit tests for PKCE generation and validation | WP01 | |
| T009 | Write unit tests for loopback callback server | WP01 | |
| T010 | Create DeviceFlowState dataclass and model | WP02 | |
| T011 | Implement device code polling loop with exponential backoff | WP02 | |
| T012 | Implement polling state transitions (pending→approved/denied/expired) | WP02 | |
| T013 | Implement polling error handling (authorization_pending, access_denied, expired_token) | WP02 | |
| T014 | Create device flow timeout and expiry management | WP02 | |
| T015 | Write unit tests for device flow polling | WP02 | |
| T016 | Write integration test for device flow end-to-end | WP02 | |
| T017 | Create SecureStorage ABC and protocol | WP03 | |
| T018 | Implement Keychain backend (macOS, keyring library) | WP03 | [P] |
| T019 | Implement Credential Manager backend (Windows, pywin32) | WP03 | [P] |
| T020 | Implement Secret Service backend (Linux, secretstorage) | WP03 | [P] |
| T021 | Implement File backend (JSON, 0600 permissions) | WP03 | |
| T022 | Create platform_detector + factory (auto-detection, selection) | WP03 | |
| T023 | Implement file fallback workflow (user prompt, graceful degradation) | WP03 | |
| T024 | Write comprehensive backend tests (read/write/delete, platform-specific) | WP03 | |
| T025 | Create StoredSession dataclass (teams[], default_team_id, tokens, expiry) | WP04 | |
| T026 | Create Team dataclass (id, name, role) | WP04 | |
| T027 | Create OAuthToken, ComputedTokenExpiry classes | WP04 | |
| T028 | Implement TokenManager.__init__ and secure storage integration | WP04 | |
| T029 | Implement TokenManager._load_from_storage | WP04 | |
| T030 | Implement TokenManager.get_access_token (expiry check + lazy refresh) | WP04 | |
| T031 | Implement single-flight refresh coordination (asyncio.Lock) | WP04 | |
| T032 | Write unit tests for TokenManager state management | WP04 | |
| T033 | Implement authorization code flow orchestration | WP05 | |
| T034 | Integrate loopback callback handler (WP01 integration) | WP05 | |
| T035 | Implement code exchange via /oauth/token endpoint | WP05 | |
| T036 | Implement token response parsing and validation | WP05 | |
| T037 | Implement session storage after successful auth | WP05 | |
| T038 | Implement auth code flow error handling (invalid_request, access_denied, timeout) | WP05 | |
| T039 | Write unit tests for authorization code flow | WP05 | |
| T040 | Write integration tests with mock OAuth provider | WP05 | |
| T041 | Implement device flow orchestration (WP02 integration) | WP06 | |
| T042 | Implement polling loop with user progress display | WP06 | |
| T043 | Implement token response parsing (device flow variant) | WP06 | |
| T044 | Implement session storage after device approval | WP06 | |
| T045 | Implement token refresh flow (/oauth/token with refresh_token grant) | WP06 | |
| T046 | Implement refresh error handling (invalid_grant, expired_token, session_invalid) | WP06 | |
| T047 | Write unit tests for device flow + refresh | WP06 | |
| T048 | Write integration tests for full headless scenario | WP06 | |
| T049 | Create OAuthHttpClient wrapper (httpx integration) | WP07 | |
| T050 | Implement bearer token injection (Authorization header) | WP07 | |
| T051 | Implement 401 response handling | WP07 | |
| T052 | Implement auto-refresh on 401 (call TokenManager.refresh_if_needed) | WP07 | |
| T053 | Implement single-shot retry logic (1x retry after refresh) | WP07 | |
| T054 | Implement error propagation (non-401, non-retryable errors) | WP07 | |
| T055 | Write unit tests for HTTP transport | WP07 | |
| T056 | Write integration tests with mock API endpoints | WP07 | |
| T057 | Implement /api/v1/me call (fetch teams, user info) | WP08 | |
| T058 | Create TokenProvisioner for pre-connect workflow | WP08 | |
| T059 | Implement pre-connect access token refresh (expires within 5 min) | WP08 | |
| T060 | Implement /api/v1/ws-token call with team_id parameter | WP08 | |
| T061 | Implement ws_url and ephemeral token handling (1-hour TTL) | WP08 | |
| T062 | Implement session binding via query parameter | WP08 | |
| T063 | Write unit tests for WebSocket provisioning | WP08 | |
| T064 | Write integration tests with WebSocket endpoint | WP08 | |
| T065 | Implement 'spec-kitty auth login' command | WP09 | |
| T066 | Implement 'spec-kitty auth login --headless' option | WP09 | |
| T067 | Implement 'spec-kitty auth logout' command | WP09 | |
| T068 | Implement 'spec-kitty auth status' command | WP09 | |
| T069 | Implement progress messaging for login flows | WP09 | |
| T070 | Implement error messaging and recovery guidance | WP09 | |
| T071 | Implement status display (user, teams, token expiry, storage backend) | WP09 | |
| T072 | Write unit tests for command interfaces | WP09 | |
| T073 | Write integration tests for full command workflows | WP09 | |
| T074 | Write integration tests for browser login → API call → logout | WP10 | |
| T075 | Write integration tests for headless login → background task → auto-refresh | WP10 | |
| T076 | Write concurrency tests (10+ concurrent token refreshes) | WP10 | |
| T077 | Write concurrency tests (concurrent 401s on same token) | WP10 | |
| T078 | Write concurrency tests (concurrent WebSocket provisioning) | WP10 | |
| T079 | Write stress tests (file storage under concurrent access, file lock coordination) | WP10 | |
| T080 | Write error recovery tests (network failures, timeout, 500 responses) | WP10 | |
| T081 | Remove password prompts from auth.py | WP11 | |
| T082 | Remove legacy password-based token endpoints | WP11 | |
| T083 | Remove password handling from sync/client.py, batch.py, background.py | WP11 | |
| T084 | Remove password handling from tracker/saas_client.py | WP11 | |
| T085 | Update commands to require OAuth login | WP11 | |
| T086 | Remove legacy test fixtures for password auth | WP11 | |
| T087 | Create migration guide for users | WP11 | |
| T088 | Prepare release notes and changelog entry | WP11 | |

---

## Work Package Definitions

### WP01: Loopback Callback Handler + PKCE State Management

**Objective**: Build the HTTP server and cryptographic state machine for the Authorization Code + PKCE flow. This is the foundation that enables interactive browser-based login.

**Priority**: P0 (foundational)  
**Est. Prompt Size**: ~400 lines  
**Subtask Count**: 9

**Included Subtasks**:
- [x] T001: Create PKCEState dataclass and model
- [x] T002: Implement PKCE code_verifier generation (43 chars, RFC 7636)
- [x] T003: Implement PKCE code_challenge generation (SHA256 base64url)
- [x] T004: Create CallbackServer HTTP server (localhost loopback)
- [x] T005: Implement callback URL parsing and state validation
- [x] T006: Create StateManager for transient PKCE state persistence
- [x] T007: Implement cross-platform browser launcher
- [x] T008: Write unit tests for PKCE generation and validation
- [x] T009: Write unit tests for loopback callback server

**Implementation Notes**:
- PKCE generation uses secrets.token_urlsafe for cryptographic strength
- CallbackServer listens on localhost:PORT (searches 28888-28898, falls back to OS assignment)
- State validation prevents CSRF attacks during callback
- PKCEState expires after 5 minutes (matches SaaS contract)
- BrowserLauncher abstracts webbrowser module for cross-platform support

**Dependencies**: None (foundational)

**Parallel Opportunities**: T007 (browser launcher) can be implemented independently

**Risks**:
- Firewall blocking loopback ports (mitigated by OS port fallback)
- Browser may already have authorization cached (user may skip SaaS login)
- Callback timeout (5 min) may expire before user completes SaaS auth (acceptable per UX)

---

### WP02: Device Authorization Flow Poller

**Objective**: Build the polling loop for Device Authorization Flow, enabling headless login (SSH sessions, CI/CD). Orchestrates polling state machine with backoff and timeout handling.

**Priority**: P0 (foundational)  
**Est. Prompt Size**: ~350 lines  
**Subtask Count**: 7

**Included Subtasks**:
- [x] T010: Create DeviceFlowState dataclass and model
- [x] T011: Implement device code polling loop with exponential backoff
- [x] T012: Implement polling state transitions (pending→approved/denied/expired)
- [x] T013: Implement polling error handling (authorization_pending, access_denied, expired_token)
- [x] T014: Create device flow timeout and expiry management
- [x] T015: Write unit tests for device flow polling
- [x] T016: Write integration test for device flow end-to-end

**Implementation Notes**:
- Polling loop respects `interval` from SaaS (default 5s), capped at 10s on CLI
- Exponential backoff on transient errors (server_error)
- Device code lifetime ~15 minutes (from SaaS contract)
- User is shown device_code, verification_uri, and countdown
- State tracking: pending → approved/denied/expired

**Dependencies**: None (foundational)

**Parallel Opportunities**: Can implement and test independently alongside WP01

**Risks**:
- User approves on wrong network (browser != CLI environment) - acceptable UX
- Device code expires during user approval - handled with timeout message
- Polling interval too aggressive causes rate limiting (mitigated by interval cap)

---

### WP03: Secure Storage Abstraction + Multi-Backend Implementation

**Objective**: Build the pluggable storage layer that persists credentials securely in OS keychains (macOS, Windows, Linux) with file fallback for degraded environments.

**Priority**: P0 (foundational)  
**Est. Prompt Size**: ~450 lines  
**Subtask Count**: 8

**Included Subtasks**:
- [x] T017: Create SecureStorage ABC and protocol
- [x] T018: Implement Keychain backend (macOS, keyring library)
- [x] T019: Implement Credential Manager backend (Windows, pywin32)
- [x] T020: Implement Secret Service backend (Linux, secretstorage)
- [x] T021: Implement File backend (JSON, 0600 permissions)
- [x] T022: Create platform_detector + factory (auto-detection, selection)
- [x] T023: Implement file fallback workflow (user prompt, graceful degradation)
- [x] T024: Write comprehensive backend tests (read/write/delete, platform-specific)

**Implementation Notes**:
- SecureStorage ABC: read(), write(), delete() async methods
- Keychain backend uses keyring library (abstracts OS differences)
- File fallback saved to ~/.config/spec-kitty/credentials.json (0600 permissions)
- File fallback prompts user ("Secure storage unavailable; save credentials in file?")
- Factory returns platform-appropriate backend; if unavailable, prompts for file fallback
- Credentials stored as JSON (StoredSession serialized to dict)

**Dependencies**: None (foundational)

**Parallel Opportunities**: T018-T020 (OS-specific backends) can run in parallel; test against mocked library imports

**Risks**:
- Keychain/Credential Manager unavailable → requires file fallback prompt
- File corruption → defensive JSON parsing with error recovery
- Cross-platform testing (need to test on macOS, Windows, Linux environments or mocks)

---

### WP04: TokenManager Architecture + Session Model

**Objective**: Build the centralized credential provisioning engine (TokenManager) and session data model. This is the hub that all CLI commands and transports use for token access.

**Priority**: P0 (core)  
**Est. Prompt Size**: ~400 lines  
**Subtask Count**: 8

**Included Subtasks**:
- [x] T025: Create StoredSession dataclass (teams[], default_team_id, tokens, expiry)
- [x] T026: Create Team dataclass (id, name, role)
- [x] T027: Create OAuthToken, ComputedTokenExpiry classes
- [x] T028: Implement TokenManager.__init__ and secure storage integration
- [x] T029: Implement TokenManager._load_from_storage
- [x] T030: Implement TokenManager.get_access_token (expiry check + lazy refresh)
- [x] T031: Implement single-flight refresh coordination (asyncio.Lock)
- [x] T032: Write unit tests for TokenManager state management

**Implementation Notes**:
- StoredSession updated to include teams[] array + default_team_id (enables multi-team WebSocket)
- TokenManager is singleton (one per CLI instance)
- get_access_token() returns immediately if valid; auto-refreshes if expired
- asyncio.Lock prevents thundering herd on token refresh
- Sync wrapper: asyncio.run() for CLI boundary (commands are sync, internals are async)
- _load_from_storage() called on init; returns None if no session exists

**Dependencies**: WP03 (SecureStorage)

**Parallel Opportunities**: None (sequential, core logic)

**Risks**:
- Token expiry timing errors (clock skew) - mitigated by 5-min refresh buffer
- Multiple CLI instances → file lock coordination (WP10 addresses via file-based locking)
- Refresh fails → session_invalid error → forces re-login

---

### WP05: OAuth Authorization Code Flow Implementation

**Objective**: Implement the interactive browser login flow orchestration. Coordinates loopback callback (WP01) and token exchange with SaaS /oauth/token endpoint.

**Priority**: P0 (core)  
**Est. Prompt Size**: ~400 lines  
**Subtask Count**: 8

**Included Subtasks**:
- [x] T033: Implement authorization code flow orchestration
- [x] T034: Integrate loopback callback handler (WP01 integration)
- [x] T035: Implement code exchange via /oauth/token endpoint
- [x] T036: Implement token response parsing and validation
- [x] T037: Implement session storage after successful auth
- [x] T038: Implement auth code flow error handling (invalid_request, access_denied, timeout)
- [x] T039: Write unit tests for authorization code flow
- [x] T040: Write integration tests with mock OAuth provider

**Implementation Notes**:
- Flow: Generate state/challenge → start loopback → open browser → wait for callback → exchange code → store session
- Code exchange includes code_verifier (PKCE security)
- Token response parsed: access_token, refresh_token, expires_in, scope, session_id
- Session stored in secure storage (WP03)
- Error messages user-friendly (e.g., "Authorization denied. Please try again.")
- Loopback server timeout: 5 minutes

**Dependencies**: WP01 (loopback), WP03 (secure storage), WP04 (TokenManager)

**Parallel Opportunities**: None (sequential implementation)

**Risks**:
- Redirect_uri mismatch (SaaS rejects localhost:PORT if not registered) - use standard ports first
- PKCE validation failure - test with SaaS mock
- Token response missing fields - defensive validation, clear error message

---

### WP06: Device Flow Implementation + Token Refresh

**Objective**: Implement the headless login flow and the token refresh mechanism. Enables CLI to keep sessions alive indefinitely with automatic refresh.

**Priority**: P0 (core)  
**Est. Prompt Size**: ~400 lines  
**Subtask Count**: 8

**Included Subtasks**:
- [x] T041: Implement device flow orchestration (WP02 integration)
- [x] T042: Implement polling loop with user progress display
- [x] T043: Implement token response parsing (device flow variant)
- [x] T044: Implement session storage after device approval
- [x] T045: Implement token refresh flow (/oauth/token with refresh_token grant)
- [x] T046: Implement refresh error handling (invalid_grant, expired_token, session_invalid)
- [x] T047: Write unit tests for device flow + refresh
- [x] T048: Write integration tests for full headless scenario

**Implementation Notes**:
- Device flow: Request device_code → show user_code and URL → poll for approval → store session
- Polling loop integrates with WP02 DeviceFlowPoller
- Token refresh: GET access_token → check expiry → call /oauth/token with refresh_token if needed
- Refresh error handling: invalid_grant (token revoked) → force re-login; other errors → retry with backoff
- User progress: "Waiting for authorization... (X minutes remaining)"

**Dependencies**: WP02 (device poller), WP03 (secure storage), WP04 (TokenManager)

**Parallel Opportunities**: None (sequential implementation)

**Risks**:
- Refresh token expired (after ~90 days) → forces re-login (acceptable per design)
- Concurrent refresh calls → single-flight lock prevents redundant RPC (implemented in WP04)
- Polling timeout → user-friendly message with retry instruction

---

### WP07: HTTP Transport Integration + 401 Retry

**Objective**: Integrate OAuth authentication into the HTTP client layer. All API calls automatically inject bearer tokens and auto-refresh on 401.

**Priority**: P1 (integration)  
**Est. Prompt Size**: ~400 lines  
**Subtask Count**: 8

**Included Subtasks**:
- [x] T049: Create OAuthHttpClient wrapper (httpx integration)
- [x] T050: Implement bearer token injection (Authorization header)
- [x] T051: Implement 401 response handling
- [x] T052: Implement auto-refresh on 401 (call TokenManager.refresh_if_needed)
- [x] T053: Implement single-shot retry logic (1x retry after refresh)
- [x] T054: Implement error propagation (non-401, non-retryable errors)
- [x] T055: Write unit tests for HTTP transport
- [x] T056: Write integration tests with mock API endpoints

**Implementation Notes**:
- OAuthHttpClient wraps httpx.AsyncClient, intercepts requests/responses
- Bearer token injected as `Authorization: Bearer <token>` header
- On 401: call TokenManager.refresh_if_needed() → retry request (1x) → if still 401, propagate error
- Error codes recognized: access_token_expired (auto-refresh), session_invalid (force re-login), others (generic error)
- Non-401 errors passed through unchanged
- Single-shot retry prevents infinite loops

**Dependencies**: WP04 (TokenManager)

**Parallel Opportunities**: T055-T056 (testing) can run in parallel with other WPs

**Risks**:
- Refresh fails during 401 retry → request fails (acceptable; user re-runs command)
- Concurrent 401s on same token → single-flight lock prevents duplicate refreshes
- Token injection timing (middleware order) - test with mock client

---

### WP08: WebSocket Pre-Connect Token Provisioning

**Objective**: Implement team-aware WebSocket token provisioning. Fetches team list, refreshes access token before upgrade, obtains ephemeral WS token, binds to team.

**Priority**: P1 (integration)  
**Est. Prompt Size**: ~400 lines  
**Subtask Count**: 8

**Included Subtasks**:
- [x] T057: Implement /api/v1/me call (fetch teams, user info)
- [x] T058: Create TokenProvisioner for pre-connect workflow
- [x] T059: Implement pre-connect access token refresh (expires within 5 min)
- [x] T060: Implement /api/v1/ws-token call with team_id parameter
- [x] T061: Implement ws_url and ephemeral token handling (1-hour TTL)
- [x] T062: Implement session binding via query parameter
- [x] T063: Write unit tests for WebSocket provisioning
- [x] T064: Write integration tests with WebSocket endpoint

**Implementation Notes**:
- /api/v1/me called once at start of WebSocket session; fetches teams[] array
- User selects team_id (default: StoredSession.default_team_id)
- Pre-connect refresh: if access_token_expires_at < now + 5min, call /oauth/token with refresh_token
- /api/v1/ws-token request body: `{"team_id": "tm_acme"}`
- Response: ws_token (1-hour TTL), ws_url, session_id
- WebSocket connection: `ws_url?token=ws_token`
- Error handling: 403 (not team member) → show user's teams, prompt to select

**Dependencies**: WP04 (TokenManager), WP07 (HTTP transport)

**Parallel Opportunities**: None (sequential)

**Risks**:
- User not member of requested team → 403 response (acceptable; error message guides user)
- WebSocket token expires during long connection → WebSocket handles with in-frame auth (out of scope)
- Team list changes between /api/v1/me and /api/v1/ws-token (acceptable edge case)

---

### WP09: CLI Commands - Login, Logout, Status

**Objective**: Build the user-facing command interface. `spec-kitty auth login`, `spec-kitty auth login --headless`, `spec-kitty auth logout`, `spec-kitty auth status`.

**Priority**: P1 (user-facing)  
**Est. Prompt Size**: ~450 lines  
**Subtask Count**: 9

**Included Subtasks**:
- [x] T065: Implement 'spec-kitty auth login' command
- [x] T066: Implement 'spec-kitty auth login --headless' option
- [x] T067: Implement 'spec-kitty auth logout' command
- [x] T068: Implement 'spec-kitty auth status' command
- [x] T069: Implement progress messaging for login flows
- [x] T070: Implement error messaging and recovery guidance
- [x] T071: Implement status display (user, teams, token expiry, storage backend)
- [x] T072: Write unit tests for command interfaces
- [x] T073: Write integration tests for full command workflows

**Implementation Notes**:
- `auth login`: Auto-detect browser availability; use browser if available, else fallback to headless
- `auth login --headless`: Force device flow regardless of browser availability
- `auth logout`: Calls /api/v1/logout, deletes local credentials
- `auth status`: Displays current user, teams, access token expiry, refresh token expiry, storage backend
- Progress messaging: spinner for polling, countdown for callback timeout
- Error messages actionable (e.g., "Visit https://... and enter ABCD-1234")

**Dependencies**: WP05 (auth code), WP06 (device flow, refresh), WP04 (TokenManager)

**Parallel Opportunities**: T072-T073 (testing) can parallelize with other WPs

**Risks**:
- Browser detection fails (use heuristic + fallback to headless)
- No browser available but user tries browser login (show helpful message, suggest --headless)
- Session already exists (show "Already logged in as alice@example.com. Run `auth logout` first.")

---

### WP10: Concurrency Testing, Integration Testing, and Hardening

**Objective**: Comprehensive testing of all features under concurrent load, error scenarios, and edge cases. Ensures robustness before staging validation.

**Priority**: P1 (quality)  
**Est. Prompt Size**: ~400 lines  
**Subtask Count**: 7

**Included Subtasks**:
- [x] T074: Write integration tests for browser login → API call → logout
- [x] T075: Write integration tests for headless login → background task → auto-refresh
- [x] T076: Write concurrency tests (10+ concurrent token refreshes)
- [x] T077: Write concurrency tests (concurrent 401s on same token)
- [x] T078: Write concurrency tests (concurrent WebSocket provisioning)
- [x] T079: Write stress tests (file storage under concurrent access, file lock coordination)
- [x] T080: Write error recovery tests (network failures, timeout, 500 responses)

**Implementation Notes**:
- Integration tests use mock SaaS endpoints (mocked OAuth provider, API responses)
- Concurrency tests verify single-flight refresh (only one /oauth/token call for 10 concurrent requests)
- File lock coordination: if file storage backend, test that concurrent CLI instances don't corrupt file
- Error recovery: simulate network timeout, 500 response, 429 rate limit; verify retry logic
- Test scenarios:
  - Browser login succeeds → API call succeeds → logout succeeds
  - Headless login succeeds → background sync task → auto-refresh on 401 → sync continues
  - 10 concurrent API calls on expired token → 1 refresh → 10 retries → all succeed

**Dependencies**: WP05, WP06, WP07, WP08, WP09 (all features)

**Parallel Opportunities**: Can run tests in parallel; coordinate mock fixtures

**Risks**:
- Mock OAuth provider doesn't match real SaaS behavior → test with staging later (WP11)
- Concurrency tests flaky (timing-dependent) → use deterministic test harness
- File lock coordination fails → requires careful mutex implementation in StoredSession

---

### WP11: Password Removal, Migration, and Release Preparation

**Objective**: Complete the hard cutover. Remove all password-based auth code, update documentation, validate 72+ hour staging window, prepare GA release.

**Priority**: P2 (pre-release)  
**Est. Prompt Size**: ~350 lines  
**Subtask Count**: 8

**Included Subtasks**:
- [x] T081: Remove password prompts from auth.py
- [x] T082: Remove legacy password-based token endpoints
- [x] T083: Remove password handling from sync/client.py, batch.py, background.py
- [x] T084: Remove password handling from tracker/saas_client.py
- [x] T085: Update commands to require OAuth login
- [x] T086: Remove legacy test fixtures for password auth
- [x] T087: Create migration guide for users
- [x] T088: Prepare release notes and changelog entry

**Implementation Notes**:
- Password removal is hard cutover (no fallback)
- Commands that require auth will fail if not logged in (no password prompt as fallback)
- Migration guide: "Run `spec-kitty auth login` to authenticate. Stored credentials will be moved to secure storage."
- Staging validation window: 72+ hours on staging SaaS; monitor for bugs, performance issues
- Release notes: highlight browser-based auth as major UX improvement, note no password storage
- Changelog entry: "BREAKING: Password-based auth removed. Use `spec-kitty auth login` for OAuth."

**Dependencies**: WP09 (all commands), WP10 (all tests)

**Parallel Opportunities**: T081-T088 can run sequentially (cleanup, migration, docs)

**Risks**:
- Users still expecting password prompts → migration guide must be prominent
- Legacy config files with password hashes → audit for any remaining password storage
- Staging issues require fixes → staging window must be long enough (72+ hours)

---

## Cross-WP Dependencies

```
WP01 (Loopback) ────┐
                     ├──→ WP05 (Auth Code Flow)
WP03 (Storage) ─────┤
                     └──→ WP04 (TokenManager)
                           ├──→ WP07 (HTTP Transport)
                           ├──→ WP08 (WebSocket)
                           └──→ WP09 (Commands)
                                 └──→ WP10 (Testing)
                                      └──→ WP11 (Cutover)

WP02 (Device Flow) ──┐
                     ├──→ WP06 (Device Flow + Refresh)
WP03 (Storage) ─────┘
                     └──→ WP04 (TokenManager)

Phase sequence: WP01+WP02 parallel → WP03 → WP04 → WP05+WP06 → WP07+WP08+WP09 → WP10 → WP11
```

---

## Next Steps

1. **Generate WP prompt files**: Each WP will get a detailed `WPxx-slug.md` file with:
   - Subtask breakdown (steps, files, validation)
   - Implementation guidance (examples, edge cases)
   - Test strategy
   - Definition of Done
   - Reviewer guidance

2. **Finalize dependencies**: Run `spec-kitty agent mission finalize-tasks` to:
   - Parse dependencies from this file
   - Update WP frontmatter
   - Validate for cycles/conflicts
   - Commit to target branch

3. **Execution**: Run `/spec-kitty.implement` for each WP in order (or parallelize per phase)

---

## WP Sizing Summary

| WP | Title | Subtasks | Est. Lines | Status |
|----|-------|----------|-----------|--------|
| WP01 | Loopback + PKCE | 9 | ~400 | ✓ IDEAL |
| WP02 | Device Flow Poller | 7 | ~350 | ✓ IDEAL |
| WP03 | Secure Storage | 8 | ~450 | ✓ IDEAL |
| WP04 | TokenManager Core | 8 | ~400 | ✓ IDEAL |
| WP05 | Auth Code Flow | 8 | ~400 | ✓ IDEAL |
| WP06 | Device Flow + Refresh | 8 | ~400 | ✓ IDEAL |
| WP07 | HTTP Transport | 8 | ~400 | ✓ IDEAL |
| WP08 | WebSocket Provisioning | 8 | ~400 | ✓ IDEAL |
| WP09 | CLI Commands | 9 | ~450 | ✓ IDEAL |
| WP10 | Testing & Hardening | 7 | ~350 | ✓ IDEAL |
| WP11 | Cutover & Release | 8 | ~350 | ✓ IDEAL |
| **TOTAL** | **11 WPs** | **91** | **~4200** | ✓ ALL WITHIN RANGE |

**Distribution Analysis**:
- ✅ All WPs between 7-9 subtasks (target 3-7, max 10)
- ✅ All WP prompts estimated 350-450 lines (target 200-500, max 700)
- ✅ No WP exceeds size limit
- ✅ Average prompt size: ~380 lines (within ideal range)

---

**Status**: Ready for work package prompt generation and finalization.
