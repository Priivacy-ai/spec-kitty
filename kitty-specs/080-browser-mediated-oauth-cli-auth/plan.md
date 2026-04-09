# Implementation Plan: Browser-Mediated OAuth/OIDC CLI Authentication

**Mission:** 080-browser-mediated-oauth-cli-auth  
**Epic:** #559  
**SaaS Counterpart:** Epic #49 (spec-kitty-saas)  
**Date:** 2026-04-09  
**Planning Status:** Complete (Synchronized with SaaS Contract)  
**Phase:** Detailed Implementation Planning

---

## 1. Technical Context

### 1.1 Planning Decisions (Confirmed)

**Q1: Async Runtime & Concurrency Model → OPTION B (Hybrid)**
- Async internals (asyncio for concurrency primitives)
- Sync command boundaries with `asyncio.run()` wrappers at entry points
- Matches existing patterns: local_service.py, websocket sync code
- File-lock coordination for cross-process refresh
- **Implication**: TokenManager has sync public API (`login()`, `get_access_token()`, `logout()`) + internal async machinery

**Q2: SaaS Contract Availability → OPTION B, NOW SYNCHRONIZED**
- Epic #49 (SaaS OAuth contract) WAS in parallel planning
- **UPDATE**: Contract now finalized (2026-04-09) and synchronized in this spec
- WP01-WP03 (TokenManager, loopback, device flow) are fully contract-aligned (no longer contract-agnostic)
- Contract adapter boundary still exists but now wraps finalized SaaS endpoints (not hypothetical)
- Mock SaaS for unit/integration testing; staging for validation before GA
- **Implication**: Core classes know exact endpoints (/oauth/authorize, /oauth/device, /api/v1/logout, etc.); minimal abstraction needed

**Q3: Dependency Injection → OPTION C (Hybrid)**
- Module-level `get_token_manager()` shared accessor for low-friction migration
- Explicit `TokenManager` injection available for tests, async consumers, runtime code
- No Typer-context plumbing overhead; keep migration minimal
- **Implication**: TokenManager in `specify_cli/auth/token_manager.py` has module-level singleton + explicit instance support

### 1.2 SaaS Contract Alignment (Key Changes from Discovery Phase)

**Endpoint Corrections:**
1. ✅ **Logout path**: `/api/v1/logout` (NOT `/oauth/revoke`)
2. ✅ **Device flow**: Single `POST /oauth/device` endpoint (NOT separate /oauth/device/code)
3. ✅ **Device polling**: Uses main `POST /oauth/token` with `device_code` grant type
4. ✅ **WebSocket auth**: Separate `/api/v1/ws-token/` endpoint (NOT direct access_token on WebSocket)
5. ✅ **Authorization scope**: Must include `offline_access` to trigger refresh token issuance

**Token Model Corrections:**
1. ✅ **Response schema**: Includes `session_id` (no `issued_at`, no `refresh_expires_in`)
2. ✅ **Access token TTL**: ~1 hour (3600s), not "≤24h"
3. ✅ **Refresh token TTL**: ~90 days (not "≤30 days")
4. ✅ **Status output**: Cannot show "Refresh Token Expires" (SaaS doesn't return TTL in token response)

**Rollout Alignment:**
1. ✅ **Staging validation**: 72+ hour window on SaaS before GA cutover
2. ✅ **Atomic cutover**: Both CLI and SaaS cut over simultaneously; no split deployments

### 1.3 Architecture Boundaries (Finalized)

| Component | Scope | Dependency |
|-----------|-------|---|
| **TokenManager** | Credential provisioning, refresh coordination, storage access | Secure storage backend + finalized SaaS endpoints |
| **LoopbackCallbackServer** | OAuth callback capture, port discovery, state validation | None (self-contained) |
| **DeviceFlowPoller** | Device code request, polling loop, timeout handling | Finalized SaaS `/oauth/device` + `/oauth/token` endpoints |
| **SecureStorage** | Keychain/Credential Manager/Secret Service/file abstraction | OS-level keystore APIs |
| **HTTP Transport Integration** | 401 retry, token refresh on expired token | TokenManager |
| **WebSocket Integration** | Token fetch via `/api/v1/ws-token/`, connection auth | TokenManager + finalized SaaS ws-token endpoint |

### 1.4 Charter Compliance Check

**Charter Requirements:**
- ✅ **typer** - CLI framework (existing)
- ✅ **rich** - Console output (existing)
- ✅ **pytest** - Testing framework (90%+ coverage required)
- ✅ **mypy --strict** - Type checking (no errors)
- ✅ **Integration tests** - CLI commands (required)

**Compliance Strategy:**
- All new code in `specify_cli/auth/` must pass `mypy --strict`
- Test coverage target: 90%+ for TokenManager, storage, loopback, device flow
- Integration tests for `spec-kitty auth login`, `auth login --headless`, `auth logout`, `auth status`
- Mock SaaS server in test suite (pytest fixture) for early integration tests
- Staging validation on real SaaS before GA (72+ hours)

---

## 2. Phase Gates & Evaluation

### Gate 1: Planning Completeness ✅
- [x] Specification approved and synchronized with SaaS contract
- [x] Planning questions resolved (Q1:B, Q2:B, Q3:C)
- [x] Architecture boundaries defined (6 components)
- [x] Contract endpoints finalized (no longer speculative)
- [x] Token models aligned to SaaS response schema
- [x] Work package decomposition mapped to issues

**Status:** PASS — Proceed to Phase 1 design

### Gate 2: Design Review (Phase 1 → Task Generation)
- [x] Data model synchronized with SaaS CliSession, token responses
- [x] API contracts match finalized SaaS endpoints
- [x] Agent context files updated (if needed)
- [x] Quickstart implementation guide written
- [x] Charter compliance re-evaluated post-sync

**Status:** Ready post-sync

### Gate 3: Staging Validation (Pre-GA)
- [ ] 72+ hour staging deployment (SaaS side)
- [ ] Error rate monitoring confirms 99.9% success
- [ ] Concurrent refresh stress test passes
- [ ] Go/no-go decision before GA cutover

**Status:** SaaS responsibility (deferred to SaaS epic #49 plan)

---

## 3. Phase 1: Design & Contracts (Aligned to SaaS)

### 3.1 Data Model

**Artifact**: `data-model.md` (to be generated)

**Content:**
1. **Entity Definitions** (synchronized with SaaS CliSession)
   - `OAuthTokenResponse` (exact fields from SaaS /oauth/token)
   - `ComputedTokenExpiry` (derived from SaaS response)
   - `StoredSession` (CLI storage format, includes session_id from SaaS)
   - `PKCEState` (40-char code_verifier, S256 challenge)
   - `DeviceFlowState` (device_code, user_code, 15-minute expiry)

2. **Validation Rules** (derived from SaaS constraints)
   - Scopes must include `offline_access`
   - Access token expires in ~3600s (1 hour)
   - Refresh token expires in ~90 days (SaaS policy)
   - Device code expires in 900s (15 minutes)

3. **State Transitions**
   - TokenManager: NotAuthenticated → Authenticated → NotAuthenticated
   - Token errors: `access_token_expired`, `session_invalid`, `authorization_pending`, `expired_token`

### 3.2 API Contracts (Finalized)

**Artifact Directory**: `contracts/` (to be generated)

**Files:**
1. `oauth-authorize-endpoint.md` — GET /oauth/authorize (browser redirect)
2. `oauth-device-endpoint.md` — POST /oauth/device (device code issuance)
3. `oauth-token-endpoint.md` — POST /oauth/token (all exchanges + refresh)
4. `api-logout-endpoint.md` — POST /api/v1/logout (session invalidation)
5. `api-ws-token-endpoint.md` — POST /api/v1/ws-token/ (WebSocket auth)
6. `error-responses.md` — SaaS error codes and CLI handling

### 3.3 Implementation Quickstart

**Artifact**: `quickstart.md` (to be generated)

**Content:**
- New file structure: `specify_cli/auth/` module layout
- Integration points: Files to modify (sync/client.py, tracker/saas_client.py, etc.)
- Dependency versions (keyring >= 23.0.0, pytest, pytest-asyncio)
- Implementation sequence (WP01 → WP11)
- Mock SaaS for unit tests; staging for integration validation

### 3.4 Agent Context Update

**Current Status**: No agent-facing commands exposed in this feature. No agent context file update required.

---

## 4. Cross-Cutting Concerns

### 4.1 Error Handling & Recovery

**Aligned to SaaS Error Codes:**

| SaaS Error Code | HTTP | CLI Meaning | CLI Recovery |
|---|---|---|---|
| `access_token_expired` | 401 | Access token expired; refresh available | Auto-refresh + retry |
| `session_invalid` | 401 | Session revoked or expired; no refresh | Force re-login |
| `authorization_pending` | 400 | Device code not approved yet | Keep polling (up to 15 min) |
| `expired_token` | 400 | Device code expired | Restart device flow |
| `access_denied` | 400 | User denied authorization | Inform user, suggest retry |
| `invalid_grant` | 401 | Authorization code invalid | Restart browser login |

**Exception Classes:**
```python
class AuthError(Exception): pass
class BrowserNotAvailableError(AuthError): pass
class CallbackTimeoutError(AuthError): pass
class CSRFError(AuthError): pass
class TokenExchangeError(AuthError): pass
class SessionInvalidError(AuthError): pass  # Requires re-login
class RefreshError(AuthError): pass  # May be retryable
class KeystoreNotAvailableError(AuthError): pass
class FilePermissionError(AuthError): pass
```

### 4.2 Concurrency & Single-Flight Refresh

**Implementation:**
- `asyncio.Lock` prevents concurrent token exchanges in-process
- File lock coordinates cross-process refresh (CLI may be invoked multiple times)
- Test: 10+ concurrent 401s → 1 token exchange, N waiting requests notified

### 4.3 Testing Strategy

**Unit Tests** (90%+ coverage):
- TokenManager: load, refresh, expiry, error codes
- Storage: keychain, file fallback, permissions, concurrent access
- Loopback: port discovery, CSRF validation, timeout
- Device flow: device code gen, polling, expiry

**Integration Tests** (mock SaaS):
- Browser login flow (callback captured, code exchanged)
- Headless login flow (device code polling until approval)
- Logout and session invalidation
- HTTP client 401 handling (refresh + 1 retry)
- WebSocket token fetch before connect
- Concurrent refresh (10+ 401s → 1 exchange)

**Staging Validation** (SaaS side, 72+ hours):
- Auth success rate target: 99.9%
- Token refresh latency: <500ms (P99)
- Error logs reviewed for unexpected failures
- Go/no-go decision before GA cutover

---

## 5. Risk Mitigation

### 5.1 Contract Drift Risk
**Mitigation**: Contract now finalized (2026-04-09). CLI spec synchronized with SaaS. Minimal change risk going forward.

### 5.2 Async/Sync Boundary Risk
**Mitigation**: `asyncio.run()` only at sync entry points. Internal async isolated. Explicit async methods for WebSocket.

### 5.3 Keystore Unavailability Risk
**Mitigation**: Explicit user prompt for file fallback. Diagnostic in `auth status`. Permission checks on read.

### 5.4 Refresh Race & Concurrency Risk
**Mitigation**: `asyncio.Lock` for in-process. File lock for cross-process. Stress test with 10+ concurrent 401s.

### 5.5 Token Leakage Risk
**Mitigation**: No logging of tokens/code_verifier/refresh_token. Code review checklist. Test for message leakage.

---

## 6. Implementation Readiness

- [x] Specification complete and synchronized with SaaS contract
- [x] Planning questions resolved (3/3)
- [x] Architecture boundaries defined (6 components, finalized endpoints)
- [x] Charter compliance confirmed
- [x] SaaS contract now finalized (not parallel/uncertain)
- [x] Token models aligned to SaaS schema
- [x] Error codes mapped to CLI handling
- [x] WebSocket flow corrected to use /api/v1/ws-token/
- [x] Access/refresh token TTLs updated to SaaS policy
- [x] Status display updated (no refresh_expires_in)
- [x] Staging validation window documented (72+ hours)
- [x] Work package mapping confirmed (11 WPs)

**Status**: ✅ Ready for Phase 1 design generation (no research needed; contract finalized)

---

## 7. Work Packages (Updated)

### WP01: TokenManager & Secure Storage
- Finalized SaaS contract: use exact endpoints
- No contract uncertainty
- Dependency: None

### WP02: Loopback Callback Handler
- Port range 28888-28898 (compatible with SaaS accepting any localhost:PORT)
- Dependency: WP01

### WP03: Device Flow Poller
- Endpoint: POST /oauth/device (single)
- Polling: POST /oauth/token with device_code grant type
- Dependency: WP01

### WP04: Browser Login
- Scope includes `offline_access` (required for refresh token)
- Dependency: WP01, WP02

### WP05: Headless Login
- Dependency: WP01, WP03

### WP06: Logout Command
- Endpoint: POST /api/v1/logout (NOT /oauth/revoke)
- Dependency: WP01

### WP07: Status Command
- Shows access_token_expires_at only (no refresh_token expiry)
- Shows session_id from SaaS
- Dependency: WP01

### WP08: HTTP Transport Rewiring
- 401 error codes: `access_token_expired` (auto-refresh), `session_invalid` (re-login)
- Dependency: WP01

### WP09: WebSocket Integration
- Call `/api/v1/ws-token/` before connect (NOT direct access_token)
- Dependency: WP01, WP08

### WP10: Password Removal
- Dependency: WP04-WP09

### WP11: Concurrency Tests & Staging Validation
- Staging validation: 72+ hours (SaaS side aligns)
- Dependency: WP01-WP10

---

## 8. Next Steps

### Phase 1: Design Finalization
1. Generate `data-model.md` (synchronized with SaaS CliSession)
2. Create `/contracts/` directory with 6 contract files (finalized endpoints)
3. Write `quickstart.md` (file structure, integration points, sequence)
4. Update agent context (if applicable — currently none)

**Output**: data-model.md, contracts/*.md, quickstart.md

### Proceed to Task Generation
Once Phase 1 design is committed:
```bash
/spec-kitty.tasks
```

This will generate individual task files (tasks/WP01.md, etc.) and compute execution lanes.

---

## 9. Appendix: SaaS Contract Synchronization Summary

**Changed from Specification Phase Discovery → Now Finalized:**

| What | Was (Speculative) | Now (Finalized, Epic #49) | Impact |
|---|---|---|---|
| Device endpoints | /oauth/device/code + /oauth/device/token | /oauth/device only (code), /oauth/token (polling) | WP03: Single endpoint for device code |
| Logout path | /oauth/revoke | /api/v1/logout | WP06: Change endpoint path |
| WebSocket auth | Direct access_token on conn | /api/v1/ws-token/ exchange first | WP09: Separate token fetch |
| Token response | Included issued_at, refresh_expires_in | Returns expires_in (relative), session_id | Token model: Align to actual schema |
| Access TTL | "≤24 hours" (acceptable) | ~1 hour (3600s) | Success criteria: Update to SaaS reality |
| Refresh TTL | "≤30 days" | ~90 days | Token model: Update to SaaS policy |
| Status display | Shows refresh_expires_in | Cannot (not in response) | WP07: Only show access_expires_at |
| Scopes | Generic (read:orgs, write:projects) | Must include offline_access | WP04: Explicit scope in auth request |
| Error codes | Generic | Specific (access_token_expired, session_invalid, etc.) | Error handling: Map to SaaS codes |
| Staging window | Hard cutover | 72+ hours validation | Plan: Align to SaaS rollout |

**No architectural changes required.** All changes are at the contract boundary (endpoints, schemas, error codes), not in core auth logic.

---

## End of Implementation Plan

**Status**: Phase 1 design ready (no Phase 0 research needed; contract finalized)  
**Branch**: main  
**Next Command**: Phase 1 design generation, then `/spec-kitty.tasks`
