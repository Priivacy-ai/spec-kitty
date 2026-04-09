# Implementation Plan: Browser-Mediated OAuth/OIDC CLI Authentication

**Mission:** 080-browser-mediated-oauth-cli-auth  
**Epic:** #559  
**Date:** 2026-04-09  
**Planning Status:** Complete  
**Phase:** Detailed Implementation Planning

---

## 1. Technical Context

### 1.1 Planning Decisions (Confirmed)

**Q1: Async Runtime & Concurrency Model → OPTION B (Hybrid)**
- Async internals (asyncio for concurrency primitives)
- Sync command boundaries with `asyncio.run()` wrappers at entry points
- Matches existing patterns: local_service.py, websocket sync code
- File-lock coordination for cross-process refresh (CLI single-process, but session file may be read by multiple processes)
- **Implication**: TokenManager has sync public API (`login()`, `get_access_token()`, `logout()`) + internal async machinery

**Q2: SaaS Contract Availability → OPTION B (Parallel, Contract-Agnostic Early Work)**
- Epic #49 (SaaS OAuth contract) is in parallel planning, not finalized
- WP01-WP03 (TokenManager, loopback, device flow) must be contract-agnostic
- Contract adapter boundary isolates SaaS endpoint/payload variability
- Mock SaaS server for early testing (exercises auth flow without real SaaS)
- WP04-WP05 (OAuth flows) can proceed with mocks or behind adapter; converge when #49 lands
- **Implication**: Core classes know about RFC 6749/7636/8628 contracts generically; SaaS details (host, client_id, endpoints) are behind adapter

**Q3: Dependency Injection → OPTION C (Hybrid)**
- Module-level `get_token_manager()` shared accessor for low-friction migration
- Explicit `TokenManager` injection available for tests, async consumers, runtime code
- No Typer-context plumbing overhead; keep migration minimal
- **Implication**: TokenManager in `specify_cli/auth/token_manager.py` has module-level singleton + explicit instance support

### 1.2 Architecture Boundaries (From Spec)

| Component | Scope | Dependency |
|-----------|-------|---|
| **TokenManager** | Credential provisioning, refresh coordination, storage access | Secure storage backend + SaaS contract adapter |
| **LoopbackCallbackServer** | OAuth callback capture, port discovery, state validation | None (self-contained) |
| **DeviceFlowPoller** | Device code request, polling loop, timeout handling | SaaS contract adapter |
| **SecureStorage** | Keychain/Credential Manager/Secret Service/file abstraction | OS-level keystore APIs |
| **SaaS Contract Adapter** | OAuth endpoint routing, request/response marshaling | Epic #49 (source of truth) |
| **HTTP Transport Integration** | 401 retry, token refresh on expired token | TokenManager |
| **WebSocket Integration** | Pre-connect refresh, 401 disconnect handling | TokenManager (async-aware) |

### 1.3 Charter Compliance Check

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
- Mock SaaS server in test suite (pytest fixture) for integration tests
- No external service dependencies in unit tests

---

## 2. Phase Gates & Evaluation

### Gate 1: Planning Completeness ✅
- [x] Specification approved (20 FR, 13 NFR, 14 C)
- [x] Planning questions resolved (Q1:B, Q2:B, Q3:C)
- [x] Architecture boundaries defined
- [x] Charter compliance confirmed
- [x] Work package decomposition mapped to issues

**Status:** PASS — Proceed to Phase 0

### Gate 2: Research Completeness (Phase 0 → Phase 1)
- SaaS contract surface must be documented (from epic #49 or assumed standard)
- Mock SaaS implementation strategy confirmed
- Keystore library selection finalized (Python `keyring` package assumed)
- Async/sync integration pattern documented
- **Blocker check**: No unresolved [NEEDS CLARIFICATION] items

**Status:** Deferred to Phase 0 report

### Gate 3: Design Review (Phase 1 → Task Generation)
- [x] Data model (OAuthToken, StoredSession, etc.) documented
- [x] API contracts (OAuth endpoints) specified
- [x] Agent context files updated (if needed)
- [x] Quickstart implementation guide written
- ✅ Charter compliance re-evaluated post-design

**Status:** Deferred to Phase 1 report

---

## 3. Phase 0: Research & Dependency Resolution

### 3.1 Unknowns & Research Tasks

**Unknown 1: SaaS Contract Finality**
- **Task**: Confirm epic #49 status and expected contract format
- **Scope**: Are endpoints finalized? Client ID provisioning? Token format (JWT or opaque)?
- **Output**: `research.md` section "SaaS Contract Status & Assumptions"

**Unknown 2: Keystore Library Selection**
- **Task**: Validate `keyring` Python package for cross-platform support
- **Scope**: Keychain (macOS), Credential Manager (Windows), Secret Service (Linux)
- **Output**: `research.md` section "Keystore Library & Alternatives"

**Unknown 3: Existing Async/Sync Integration Pattern**
- **Task**: Audit `local_service.py`, `sync/client.py`, websocket code for async/sync patterns
- **Scope**: How is `asyncio.run()` currently used? Where are boundaries?
- **Output**: `research.md` section "Async/Sync Integration Precedent"

**Unknown 4: Mock SaaS Implementation Strategy**
- **Task**: Design pytest fixture for mock OAuth server
- **Scope**: Should mock be in-memory or spawned process? How to parameterize contracts?
- **Output**: `research.md` section "Mock SaaS Server Design"

**Unknown 5: File Lock Strategy (Cross-Process Refresh)**
- **Task**: Evaluate file locking for cross-process credential store access
- **Scope**: CLI may be invoked multiple times; refresh must be single-flighted across processes
- **Output**: `research.md` section "Cross-Process Refresh Coordination"

### 3.2 Research Output

**Timeline**: Research to complete before Phase 1 design.

**Output**: Single consolidated `research.md` file at `/private/tmp/browser-auth/spec-kitty/kitty-specs/080-browser-mediated-oauth-cli-auth/research.md`

---

## 4. Phase 1: Design & Contracts

### 4.1 Data Model

**Artifact**: `data-model.md` at `/private/tmp/browser-auth/spec-kitty/kitty-specs/080-browser-mediated-oauth-cli-auth/data-model.md`

**Content**:
1. **Entity Definitions** (from spec section 7)
   - `OAuthToken` (access_token, refresh_token, expires_in, issued_at, etc.)
   - `ComputedTokenExpiry` (access_token_expires_at, refresh_token_expires_at)
   - `StoredSession` (user_id, username, email, org_id, org_name, tokens, expiry, storage_backend)
   - `PKCEState` (state, code_verifier, code_challenge, nonce, created_at, expires_at)
   - `DeviceFlowState` (device_code, user_code, verification_uri, expires_in, interval)

2. **Validation Rules**
   - `code_verifier` must be 43 characters, cryptographically secure random
   - `state` must be ≥128 bits cryptographically secure random
   - `access_token_expires_at` must be ≤24 hours from issued_at
   - `refresh_token_expires_at` must be ≤30 days from issued_at
   - File permissions must be 0600 for file-backed storage

3. **State Transitions**
   - TokenManager states: NotAuthenticated → Authenticated → NotAuthenticated
   - Token states: Valid → Expired → Refreshed → Revoked

### 4.2 API Contracts

**Artifact Directory**: `/private/tmp/browser-auth/spec-kitty/kitty-specs/080-browser-mediated-oauth-cli-auth/contracts/`

**Files**:
1. `oauth-rfc6749-rfc7636-endpoints.md` — Standard OAuth2 + PKCE endpoints
2. `device-flow-rfc8628-endpoints.md` — Device Authorization Flow (RFC 8628)
3. `contract-adapter-interface.md` — Internal CLI adapter (abstraction over epic #49)
4. `token-manager-public-api.md` — TokenManager sync interface
5. `http-client-integration-contract.md` — How HTTP clients use TokenManager

### 4.3 Implementation Quickstart

**Artifact**: `quickstart.md` at `/private/tmp/browser-auth/spec-kitty/kitty-specs/080-browser-mediated-oauth-cli-auth/quickstart.md`

**Content**:
- New file structure: `specify_cli/auth/` module layout
- Integration points: Files to modify (sync/client.py, tracker/saas_client.py, etc.)
- Dependency versions (keyring >= 23.0.0, pytest, etc.)
- Implementation sequence (WP01 → WP11)

### 4.4 Agent Context Update

**Current Status**: No agent-facing commands exposed in this feature. No agent context file update required.

---

## 5. Cross-Cutting Concerns

### 5.1 Error Handling & Recovery

**Principle**: Fail explicitly, provide actionable recovery messages.

**Error Scenarios**:

| Scenario | Error Type | User Message | Recovery |
|----------|---|---|---|
| Browser not available | BrowserNotAvailableError | "Browser not available. Use `--headless`." | Suggest --headless |
| Callback timeout | CallbackTimeoutError | "Callback timed out. Run `spec-kitty auth login` again." | Retry |
| Invalid state (CSRF) | CSRFError | "Invalid CSRF token. Possible attack." | Fail immediately |
| Token exchange fails | TokenExchangeError | "Failed to exchange code: [SaaS error]." | Retry or re-login |
| Refresh token expired | RefreshTokenExpiredError | "Session expired. Run: `spec-kitty auth login`" | Force re-login |
| No keystore available | KeystoreNotAvailableError | "No secure store. Continue with file fallback? [y/n]" | Prompt user |
| File permissions wrong | FilePermissionError | "Token file has wrong permissions. Fixing..." | Auto-fix + warn |

### 5.2 Concurrency & Single-Flight Refresh

**Principle**: Only one token refresh in-flight, even if multiple requests hit 401 simultaneously.

**Implementation**:
- Use `asyncio.Lock` for in-process coordination
- File lock for cross-process coordination (CLI invoked multiple times)
- Test with 10+ concurrent 401 requests (WP10)
- Verify single-flight: assert only 1 token exchange occurs

### 5.3 Testing Strategy

**Charter Requirement**: 90%+ test coverage for new code + integration tests for CLI commands

**Test Coverage**:
- Unit tests: TokenManager, storage, loopback, device flow
- Integration tests: auth login, logout, status (with mock SaaS)
- Concurrency tests: single-flight refresh with 10+ concurrent requests
- E2E tests: full user journeys (login → API → token expiry → refresh)

**Mock SaaS Fixture**:
```
tests/auth/fixtures/mock_oauth_server.py
  Implements: /oauth/authorize, /oauth/token, /oauth/revoke, 
             /oauth/device/code, /oauth/device/token
```

---

## 6. Risk Mitigation

### 6.1 SaaS Contract Risk
**Mitigation**: Contract adapter boundary isolates SaaS details. Mock adapter for early WPs. Thin wrapper when #49 lands.

### 6.2 Async/Sync Boundary Risk
**Mitigation**: `asyncio.run()` only at sync entry points. Internal async isolated. Explicit async methods for WebSocket.

### 6.3 Keystore Unavailability Risk
**Mitigation**: Explicit user prompt for file fallback. Diagnostic in `auth status`. Permission checks on read.

### 6.4 Refresh Race & Concurrency Risk
**Mitigation**: `asyncio.Lock` for in-process. File lock for cross-process. Stress test with 10+ concurrent 401s.

### 6.5 Security Risk (Token Leakage)
**Mitigation**: No logging of tokens/code_verifier/refresh_token. Code review for log statements. Test for message leakage.

---

## 7. Implementation Readiness

- [x] Specification approved
- [x] Planning questions resolved (3/3)
- [x] Architecture boundaries defined
- [x] Charter compliance confirmed
- [x] Data model documented
- [x] API contracts specified
- [x] Research tasks identified
- [x] Test strategy defined
- [x] Error handling documented
- [x] Concurrency specified
- [x] Risk mitigation strategies identified
- [x] Work package mapping confirmed (11 WPs)

**Status**: ✅ Ready for Phase 0 research execution

---

## 8. Next Steps

### Phase 0: Research Execution
1. Confirm epic #49 SaaS contract status (or assume RFC standards)
2. Validate `keyring` library for cross-platform support
3. Audit existing async/sync patterns
4. Design mock SaaS server (pytest fixture)
5. Finalize file-lock strategy

**Output**: `research.md`

### Phase 1: Design Finalization
1. Generate `data-model.md`
2. Create `/contracts/` directory with 5 contract files
3. Write `quickstart.md`
4. Update agent context (if applicable)

**Output**: data-model.md, contracts/*.md, quickstart.md

### Proceed to Task Generation
Once Phase 1 is complete:
```bash
/spec-kitty.tasks
```

This will generate individual work-package task files and compute execution lanes.

---

## End of Implementation Plan

**Status**: Phase 0 Research ready  
**Branch**: main (planning/base = main, merge target = main)  
**Next Phase**: Research artifacts (research.md)  
**Subsequent Command**: `/spec-kitty.tasks` (after Phase 1 design completion)
