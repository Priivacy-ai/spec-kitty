# Tasks: Browser-Mediated OAuth/OIDC CLI Authentication

**Mission**: `080-browser-mediated-oauth-cli-auth`
**Plan**: [plan.md](plan.md)
**Spec**: [spec.md](spec.md)
**Generated**: 2026-04-09 (regeneration after post-merge mission review)
**Branch**: `main` | **Target**: `main`

> This is the **second** generation of tasks.md for this mission. The first
> generation was deleted because (a) it diverged from spec.md §10 WP
> decomposition, (b) FR mappings were systematically wrong, (c) WP `owned_files`
> excluded the legacy transport files that needed rewiring, and (d) no WP had
> a "verify integration via grep" subtask. See plan.md "Architectural Decisions
> (Locked)" for the constraints this generation honors.

---

## Executive Summary

11 work packages, 64 subtasks total. Mirrors spec.md §10 WP decomposition.
Estimated implementation time: 4-6 days with sequential execution per lane,
2-3 days with parallel lane execution.

**Critical structural changes from previous generation**:

1. WP08 (HTTP Transport Rewiring) explicitly owns the legacy transport files
   (sync/client.py, sync/background.py, sync/batch.py, sync/body_transport.py,
   sync/runtime.py, sync/emitter.py, sync/events.py, tracker/saas_client.py)
   and has a grep audit DoD that fails the WP if `CredentialStore` or
   `AuthClient` references remain anywhere outside the auth package.

2. CLI command WPs (WP04, WP06, WP07) own SEPARATE files
   (`_auth_login.py`, `_auth_logout.py`, `_auth_status.py`) instead of trying
   to share `cli/commands/auth.py`. WP04 owns the dispatch shell `auth.py`
   and uses deferred imports so logout/status modules can be added by their
   respective WPs without file overlap.

3. WP05 (headless login) owns only `auth/flows/device_code.py`. The
   `--headless` flag dispatch lives in WP04's `_auth_login.py` from day one
   via lazy import — when WP05 ships device_code.py the runtime import
   resolves naturally.

4. Every FR is mapped to exactly one WP, and the mapping matches what the WP
   actually builds. See FR Coverage Matrix below.

5. Integration tests (WP11) MUST use `CliRunner` or `subprocess` against the
   live `app` from `specify_cli.__main__`. Tests that import flow classes
   directly without using CliRunner are rejected at review (audit subtask
   T063).

6. Each WP that introduces a new public symbol has a "verify integration"
   subtask that grep-asserts callers exist. WP08 (the rewiring WP) is where
   the foundation TokenManager from WP01 must show 5+ live callers.

7. SaaS base URL comes from `get_saas_base_url()` (env-driven). No hardcoded
   `https://api.spec-kitty.com` or `https://example.com` anywhere.

8. WP04 REPLACES the existing `login` command body in
   `src/specify_cli/cli/commands/auth.py`. It does not add a parallel
   `oauth-login` command. After WP04, `spec-kitty auth login` IS the browser
   PKCE flow.

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `auth/__init__.py` with `get_token_manager()` factory | WP01 | | [D] |
| T002 | Create `auth/config.py` with `get_saas_base_url()` env helper | WP01 | [D] |
| T003 | Create `auth/errors.py` with full exception hierarchy | WP01 | [D] |
| T004 | Create `auth/session.py` with Team + StoredSession dataclasses | WP01 | [D] |
| T005 | Create `auth/secure_storage/` package + keychain backend | WP01 | | [D] |
| T006 | Implement `file_fallback.py` with scrypt KDF + AES-256-GCM | WP01 | | [D] |
| T007 | Create `auth/token_manager.py` with single-flight refresh | WP01 | | [D] |
| T008 | Write unit tests for WP01 components | WP01 | | [D] |
| T009 | Create `auth/loopback/pkce.py` (43-char verifier, S256 challenge) | WP02 | [D] |
| T010 | Create `auth/loopback/state.py` (PKCEState dataclass + 5-min expiry) | WP02 | [D] |
| T011 | Create `auth/loopback/state_manager.py` (lifecycle) | WP02 | | [D] |
| T012 | Create `auth/loopback/callback_server.py` (port discovery + timeout) | WP02 | | [D] |
| T013 | Create `auth/loopback/callback_handler.py` (CSRF state validation) | WP02 | | [D] |
| T014 | Create `auth/loopback/browser_launcher.py` (cross-platform) | WP02 | [D] |
| T015 | Write unit tests for WP02 components | WP02 | | [D] |
| T016 | Create `auth/device_flow/state.py` (DeviceFlowState dataclass) | WP03 | [D] |
| T017 | Create `auth/device_flow/poller.py` (interval-respecting loop) | WP03 | | [D] |
| T018 | Add user_code formatting + progress display helpers | WP03 | | [D] |
| T019 | Write unit tests for WP03 components | WP03 | | [D] |
| T020 | REWRITE `cli/commands/auth.py` as deferred-import dispatch shell | WP04 | | [D] |
| T021 | Create `cli/commands/_auth_login.py` with login_impl + --headless branch | WP04 | | [D] |
| T022 | Create `auth/flows/authorization_code.py` (AuthorizationCodeFlow) | WP04 | | [D] |
| T023 | Create `auth/flows/refresh.py` (TokenRefreshFlow) | WP04 | | [D] |
| T024 | Implement token exchange helper (POST /oauth/token + code) | WP04 | | [D] |
| T025 | Implement user info fetch (GET /api/v1/me + StoredSession build) | WP04 | | [D] |
| T026 | Wire TokenManager.set_session(); verify legacy login body removed | WP04 | | [D] |
| T027 | Write unit + CliRunner tests for WP04 | WP04 | | [D] |
| T028 | Create `auth/flows/device_code.py` (DeviceCodeFlow) | WP05 | | [D] |
| T029 | Implement device code request helper (POST /oauth/device) | WP05 | | [D] |
| T030 | Wire user info fetch; build StoredSession on approval | WP05 | | [D] |
| T031 | Write unit tests for DeviceCodeFlow | WP05 | | [D] |
| T032 | Add CliRunner test for `spec-kitty auth login --headless` | WP05 | | [D] |
| T033 | Create `cli/commands/_auth_logout.py` with logout_impl | WP06 | | [D] |
| T034 | Implement /api/v1/logout call via OAuthHttpClient | WP06 | | [D] |
| T035 | Add `--force` flag for local-only logout | WP06 | | [D] |
| T036 | Write unit + CliRunner tests for logout | WP06 | | [D] |
| T037 | Create `cli/commands/_auth_status.py` with status_impl | WP07 | | [D] |
| T038 | Add human-readable duration formatter ("59 min remaining") | WP07 | | [D] |
| T039 | Add storage backend display formatter | WP07 | | [D] |
| T040 | Write unit + CliRunner tests for status | WP07 | | [D] |
| T041 | Create `auth/http/transport.py` (OAuthHttpClient) | WP08 | | [D] |
| T042 | Rewire `sync/client.py` (HTTP and WebSocket paths) to TokenManager | WP08 | | [D] |
| T043 | Rewire `tracker/saas_client.py` to TokenManager | WP08 | | [D] |
| T044 | Rewire sync/{background,batch,body_transport,runtime,emitter,events}.py | WP08 | | [D] |
| T045 | GREP AUDIT: zero `CredentialStore`/`AuthClient` references outside `auth/` | WP08 | | [D] |
| T046 | GREP AUDIT: ≥5 `get_token_manager` callers from production code | WP08 | | [D] |
| T047 | Write unit tests for OAuthHttpClient + update sync/client tests | WP08 | | [D] |
| T048 | Create `auth/websocket/__init__.py` exporting `provision_ws_token` | WP09 | | [D] |
| T049 | Create `auth/websocket/token_provisioning.py` (TokenProvisioner) | WP09 | | [D] |
| T050 | Add 403/404/5xx error handling for ws-token endpoint | WP09 | | [D] |
| T051 | Write unit tests for WebSocketTokenProvisioner | WP09 | | [D] |
| T052 | DELETE `src/specify_cli/sync/auth.py`; verify no imports remain | WP10 | |
| T053 | Update or remove `tests/sync/test_auth.py` | WP10 | |
| T054 | Search and remove any password-prompt code | WP10 | |
| T055 | Verify `spec-kitty auth login --help` does not mention password | WP10 | |
| T056 | Regression test asserting Typer app has login/logout/status commands | WP10 | |
| T057 | Create `test_browser_login_e2e.py` (CliRunner + mock SaaS) | WP11 | |
| T058 | Create `test_headless_login_e2e.py` (CliRunner + mock device flow) | WP11 | |
| T059 | Create `test_logout_e2e.py` and `test_status_e2e.py` (CliRunner) | WP11 | |
| T060 | Create `test_transport_rewired.py` (verify sync/client uses TokenManager) | WP11 | |
| T061 | Create `test_single_flight_refresh.py` (10+ concurrent = 1 refresh) | WP11 | |
| T062 | Create `test_file_storage_concurrent.py` (atomic writes) | WP11 | |
| T063 | AUDIT: integration tests must use CliRunner/subprocess (not flow classes) | WP11 | |
| T064 | AUDIT: zero `CredentialStore`/`AuthClient` references in tests/ | WP11 | |

---

## Work Package Definitions

### WP01: TokenManager + SecureStorage Foundation

**Prompt**: [tasks/WP01-token-manager-and-secure-storage.md](tasks/WP01-token-manager-and-secure-storage.md)

**Goal**: Build the foundation: `TokenManager`, `SecureStorage` abstraction with
keychain + encrypted file fallback backends, `StoredSession` model, error
hierarchy, env-driven SaaS URL helper, `get_token_manager()` factory.

**Priority**: P0 (blocks everything else)
**Estimated prompt size**: ~450 lines | **Subtasks**: 8

**Included subtasks**:
- [x] T001 Create `auth/__init__.py` with `get_token_manager()` factory (WP01)
- [x] T002 Create `auth/config.py` with `get_saas_base_url()` env helper (WP01)
- [x] T003 Create `auth/errors.py` with full exception hierarchy (WP01)
- [x] T004 Create `auth/session.py` with Team + StoredSession dataclasses (WP01)
- [x] T005 Create `auth/secure_storage/` package + keychain backend (WP01)
- [x] T006 Implement `file_fallback.py` with scrypt KDF + AES-256-GCM (WP01)
- [x] T007 Create `auth/token_manager.py` with single-flight refresh (WP01)
- [x] T008 Write unit tests for WP01 components (WP01)

**Dependencies**: none — this is the root WP

**Owns**: `src/specify_cli/auth/__init__.py`, `src/specify_cli/auth/config.py`,
`src/specify_cli/auth/errors.py`, `src/specify_cli/auth/session.py`,
`src/specify_cli/auth/token_manager.py`, `src/specify_cli/auth/secure_storage/**`,
plus the corresponding test files.

**Risks**: scrypt key derivation must use random salt (D-8); single-flight
refresh must use asyncio.Lock with the double-check pattern.

---

### WP02: Loopback Callback Handler + PKCE

**Prompt**: [tasks/WP02-loopback-callback-and-pkce.md](tasks/WP02-loopback-callback-and-pkce.md)

**Goal**: Build the localhost HTTP server, PKCE state machine, and CSRF
validation needed for the Authorization Code flow.

**Priority**: P0 (blocks WP04)
**Estimated prompt size**: ~400 lines | **Subtasks**: 7

**Included subtasks**:
- [x] T009 Create `auth/loopback/pkce.py` (43-char verifier, S256 challenge) (WP02)
- [x] T010 Create `auth/loopback/state.py` (PKCEState dataclass + 5-min expiry) (WP02)
- [x] T011 Create `auth/loopback/state_manager.py` (lifecycle) (WP02)
- [x] T012 Create `auth/loopback/callback_server.py` (port discovery + timeout) (WP02)
- [x] T013 Create `auth/loopback/callback_handler.py` (CSRF state validation) (WP02)
- [x] T014 Create `auth/loopback/browser_launcher.py` (cross-platform) (WP02)
- [x] T015 Write unit tests for WP02 components (WP02)

**Dependencies**: WP01 (uses errors module)

**Owns**: `src/specify_cli/auth/loopback/**`, `tests/auth/test_pkce.py`,
`tests/auth/test_loopback_callback.py`, `tests/auth/test_state_manager.py`,
`tests/auth/test_browser_launcher.py`.

---

### WP03: Device Authorization Flow Poller

**Prompt**: [tasks/WP03-device-authorization-flow-poller.md](tasks/WP03-device-authorization-flow-poller.md)

**Goal**: Build the polling state machine for RFC 8628 device authorization
flow. Respects SaaS-provided interval, caps at 10s, detects terminal states.

**Priority**: P0 (blocks WP05)
**Estimated prompt size**: ~280 lines | **Subtasks**: 4

**Included subtasks**:
- [x] T016 Create `auth/device_flow/state.py` (DeviceFlowState dataclass) (WP03)
- [x] T017 Create `auth/device_flow/poller.py` (interval-respecting loop) (WP03)
- [x] T018 Add user_code formatting + progress display helpers (WP03)
- [x] T019 Write unit tests for WP03 components (WP03)

**Dependencies**: WP01 (uses errors module)

**Owns**: `src/specify_cli/auth/device_flow/**`,
`tests/auth/test_device_flow_poller.py`.

---

### WP04: Browser Login Flow (`auth login`)

**Prompt**: [tasks/WP04-browser-login-flow.md](tasks/WP04-browser-login-flow.md)

**Goal**: Replace the existing `spec-kitty auth login` command with the
browser-mediated OAuth Authorization Code + PKCE flow. Set up the deferred-
import dispatch shell that all CLI command WPs share.

**Priority**: P0 (user-facing primary login)
**Estimated prompt size**: ~500 lines | **Subtasks**: 8

**Included subtasks**:
- [x] T020 REWRITE `cli/commands/auth.py` as deferred-import dispatch shell (WP04)
- [x] T021 Create `cli/commands/_auth_login.py` with login_impl + --headless branch (WP04)
- [x] T022 Create `auth/flows/authorization_code.py` (AuthorizationCodeFlow) (WP04)
- [x] T023 Create `auth/flows/refresh.py` (TokenRefreshFlow) (WP04)
- [x] T024 Implement token exchange helper (POST /oauth/token + code) (WP04)
- [x] T025 Implement user info fetch (GET /api/v1/me + StoredSession build) (WP04)
- [x] T026 Wire TokenManager.set_session(); verify legacy login body removed (WP04)
- [x] T027 Write unit + CliRunner tests for WP04 (WP04)

**Dependencies**: WP01, WP02

**Owns**: `src/specify_cli/cli/commands/auth.py` (REWRITE),
`src/specify_cli/cli/commands/_auth_login.py` (NEW),
`src/specify_cli/auth/flows/__init__.py` (NEW),
`src/specify_cli/auth/flows/authorization_code.py` (NEW),
`src/specify_cli/auth/flows/refresh.py` (NEW),
`tests/cli/commands/test_auth_login.py`,
`tests/auth/test_authorization_code_flow.py`,
`tests/auth/test_refresh_flow.py`.

**CRITICAL**: T020 REWRITES the existing `cli/commands/auth.py`. Remove all
imports of `AuthClient`, `CredentialStore`, `read_queue_scope_from_credentials`.
Replace the existing `login()` Typer command body with a deferred call to
`from specify_cli.cli.commands._auth_login import login_impl; login_impl(...)`.

---

### WP05: Headless Login Flow (`auth login --headless`)

**Prompt**: [tasks/WP05-headless-login-flow.md](tasks/WP05-headless-login-flow.md)

**Goal**: Build the `DeviceCodeFlow` orchestrator. WP04 already has the
`--headless` branch in `_auth_login.py` that lazy-imports DeviceCodeFlow;
once WP05 ships `auth/flows/device_code.py` the import resolves naturally.

**Priority**: P0 (user-facing fallback)
**Estimated prompt size**: ~280 lines | **Subtasks**: 5

**Included subtasks**:
- [x] T028 Create `auth/flows/device_code.py` (DeviceCodeFlow) (WP05)
- [x] T029 Implement device code request helper (POST /oauth/device) (WP05)
- [x] T030 Wire user info fetch; build StoredSession on approval (WP05)
- [x] T031 Write unit tests for DeviceCodeFlow (WP05)
- [x] T032 Add CliRunner test for `spec-kitty auth login --headless` (WP05)

**Dependencies**: WP01, WP03, WP04

**Owns**: `src/specify_cli/auth/flows/device_code.py`,
`tests/auth/test_device_code_flow.py`. Note: WP05 does NOT touch
`cli/commands/_auth_login.py` — that file's `--headless` branch is already
in place from WP04 with a lazy import that resolves once this WP ships.

---

### WP06: Logout Command (`auth logout`)

**Prompt**: [tasks/WP06-logout-command.md](tasks/WP06-logout-command.md)

**Goal**: Implement `_auth_logout.py` with server-side `/api/v1/logout` call
plus local credential cleanup. Server failure must not block local cleanup.

**Priority**: P1
**Estimated prompt size**: ~270 lines | **Subtasks**: 4

**Included subtasks**:
- [x] T033 Create `cli/commands/_auth_logout.py` with logout_impl (WP06)
- [x] T034 Implement /api/v1/logout call via OAuthHttpClient (WP06)
- [x] T035 Add `--force` flag for local-only logout (WP06)
- [x] T036 Write unit + CliRunner tests for logout (WP06)

**Dependencies**: WP01, WP04, WP08 (uses OAuthHttpClient from WP08)

**Owns**: `src/specify_cli/cli/commands/_auth_logout.py`,
`tests/cli/commands/test_auth_logout.py`.

---

### WP07: Status Command (`auth status`)

**Prompt**: [tasks/WP07-status-command.md](tasks/WP07-status-command.md)

**Goal**: Implement `_auth_status.py` showing user, teams, token expiry,
and storage backend. Must display "Not authenticated" cleanly when no session.

**Priority**: P1
**Estimated prompt size**: ~270 lines | **Subtasks**: 4

**Included subtasks**:
- [x] T037 Create `cli/commands/_auth_status.py` with status_impl (WP07)
- [x] T038 Add human-readable duration formatter ("59 min remaining") (WP07)
- [x] T039 Add storage backend display formatter (WP07)
- [x] T040 Write unit + CliRunner tests for status (WP07)

**Dependencies**: WP01, WP04 (uses dispatch shell from WP04)

**Owns**: `src/specify_cli/cli/commands/_auth_status.py`,
`tests/cli/commands/test_auth_status.py`.

---

### WP08: HTTP Transport Rewiring

**Prompt**: [tasks/WP08-http-transport-rewiring.md](tasks/WP08-http-transport-rewiring.md)

**Goal**: Build `OAuthHttpClient` AND rewire all legacy HTTP/WS callers to
get tokens from `get_token_manager()`. This is the integration WP that makes
the new auth system actually live.

**Priority**: P0 (without this WP, the entire new auth system is dead code)
**Estimated prompt size**: ~480 lines | **Subtasks**: 7

**Included subtasks**:
- [x] T041 Create `auth/http/transport.py` (OAuthHttpClient) (WP08)
- [x] T042 Rewire `sync/client.py` (HTTP and WebSocket paths) to TokenManager (WP08)
- [x] T043 Rewire `tracker/saas_client.py` to TokenManager (WP08)
- [x] T044 Rewire sync/{background,batch,body_transport,runtime,emitter,events}.py (WP08)
- [x] T045 GREP AUDIT: zero `CredentialStore`/`AuthClient` references outside `auth/` (WP08)
- [x] T046 GREP AUDIT: ≥5 `get_token_manager` callers from production code (WP08)
- [x] T047 Write unit tests for OAuthHttpClient + update sync/client tests (WP08)

**Dependencies**: WP01, WP09 (sync/client.py needs WP09's auth/websocket
package to exist before its WS path can be rewired)

**Owns**: `src/specify_cli/auth/http/**`,
`src/specify_cli/sync/client.py`,
`src/specify_cli/sync/background.py`,
`src/specify_cli/sync/batch.py`,
`src/specify_cli/sync/body_transport.py`,
`src/specify_cli/sync/runtime.py`,
`src/specify_cli/sync/emitter.py`,
`src/specify_cli/sync/events.py`,
`src/specify_cli/tracker/saas_client.py`,
`tests/auth/test_http_transport.py`,
existing `tests/sync/test_client.py` and `tests/tracker/test_saas_client.py`
updates as needed.

**HARD AUDIT (T045)**: After this WP is done, the following grep MUST return
zero hits:
```bash
grep -rn 'CredentialStore\|AuthClient' src/specify_cli/ --include='*.py' \
    | grep -v '^src/specify_cli/auth/'
```

**HARD AUDIT (T046)**: After this WP is done, the following grep MUST return
at least 5 hits (one per rewired file):
```bash
grep -rn 'get_token_manager\b' src/specify_cli/ --include='*.py' \
    | grep -v '^src/specify_cli/auth/'
```

If either audit fails, WP08 is INCOMPLETE. Reviewer must reject.

---

### WP09: WebSocket Pre-Connect Token Provisioning

**Prompt**: [tasks/WP09-websocket-token-provisioning.md](tasks/WP09-websocket-token-provisioning.md)

**Goal**: Build the `auth/websocket/` package that provisions ephemeral
WebSocket tokens via `/api/v1/ws-token`. Pre-connect refresh if access
token expires within 5 minutes.

**Priority**: P1
**Estimated prompt size**: ~280 lines | **Subtasks**: 4

**Included subtasks**:
- [x] T048 Create `auth/websocket/__init__.py` exporting `provision_ws_token` (WP09)
- [x] T049 Create `auth/websocket/token_provisioning.py` (TokenProvisioner) (WP09)
- [x] T050 Add 403/404/5xx error handling for ws-token endpoint (WP09)
- [x] T051 Write unit tests for WebSocketTokenProvisioner (WP09)

**Dependencies**: WP01 only

**Owns**: `src/specify_cli/auth/websocket/**`,
`tests/auth/test_websocket_provisioning.py`.

---

### WP10: Password Removal & Legacy Cleanup

**Prompt**: [tasks/WP10-password-removal-and-cleanup.md](tasks/WP10-password-removal-and-cleanup.md)

**Goal**: DELETE `src/specify_cli/sync/auth.py` (the legacy AuthClient and
CredentialStore). Update or remove legacy auth tests. Verify no password
prompts remain anywhere.

**Priority**: P0 (hard cutover gate)
**Estimated prompt size**: ~260 lines | **Subtasks**: 5

**Included subtasks**:
- [ ] T052 DELETE `src/specify_cli/sync/auth.py`; verify no imports remain (WP10)
- [ ] T053 Update or remove `tests/sync/test_auth.py` (WP10)
- [ ] T054 Search and remove any password-prompt code (WP10)
- [ ] T055 Verify `spec-kitty auth login --help` does not mention password (WP10)
- [ ] T056 Regression test asserting Typer app has login/logout/status commands (WP10)

**Dependencies**: WP04, WP05, WP06, WP07, WP08 (everything that used to import
sync/auth.py must be done first)

**Owns**: `src/specify_cli/sync/auth.py` (DELETE),
`tests/sync/test_auth.py` (UPDATE or DELETE),
`tests/sync/test_auth_concurrent_refresh.py` (UPDATE or REPURPOSE).

---

### WP11: Integration Tests, Concurrency Tests, Staging Validation

**Prompt**: [tasks/WP11-integration-and-concurrency-tests.md](tasks/WP11-integration-and-concurrency-tests.md)

**Goal**: End-to-end integration tests via `CliRunner` against the real
`app`. Concurrency tests for single-flight refresh. Stress tests for file
storage. Audit subtasks that grep for forbidden patterns.

**Priority**: P0 (final gate before merge)
**Estimated prompt size**: ~480 lines | **Subtasks**: 8

**Included subtasks**:
- [ ] T057 Create `test_browser_login_e2e.py` (CliRunner + mock SaaS) (WP11)
- [ ] T058 Create `test_headless_login_e2e.py` (CliRunner + mock device flow) (WP11)
- [ ] T059 Create `test_logout_e2e.py` and `test_status_e2e.py` (CliRunner) (WP11)
- [ ] T060 Create `test_transport_rewired.py` (verify sync/client uses TokenManager) (WP11)
- [ ] T061 Create `test_single_flight_refresh.py` (10+ concurrent = 1 refresh) (WP11)
- [ ] T062 Create `test_file_storage_concurrent.py` (atomic writes) (WP11)
- [ ] T063 AUDIT: integration tests must use CliRunner/subprocess (not flow classes) (WP11)
- [ ] T064 AUDIT: zero `CredentialStore`/`AuthClient` references in tests/ (WP11)

**Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09, WP10

**Owns**: `tests/auth/integration/**`, `tests/auth/concurrency/**`,
`tests/auth/stress/**`.

**HARD AUDIT (T063)**: After this WP is done, the following must return empty:
```bash
grep -l 'AuthorizationCodeFlow\|DeviceCodeFlow' tests/auth/integration/*.py 2>/dev/null \
    | xargs -I{} sh -c 'grep -L "CliRunner\|subprocess" {}' 2>/dev/null
```

Any integration test that imports a flow class without also importing
CliRunner or subprocess is rejected. The integration test must hit the
real CLI entry point.

---

## Cross-WP Dependencies

```
WP01 ──┬─→ WP02 ─→ WP04 ──┬─→ WP05 ─→ WP10 ─→ WP11
       │                  ├─→ WP06 ─→ WP10 ─→ WP11
       │                  └─→ WP07 ─→ WP10 ─→ WP11
       ├─→ WP03 ─→ WP05
       └─→ WP09 ─→ WP08 ─→ WP06 ─→ WP10 ─→ WP11
```

**Critical path** (longest chain):
WP01 → WP02 → WP04 → WP08 → WP10 → WP11 (6 WPs deep)

Note: WP08 actually depends on WP01 and WP09. WP06 depends on WP08 (uses
OAuthHttpClient), so the resolved chain places WP08 before WP06 in execution.

**Parallelization opportunities**:
- WP02 and WP03 are siblings (both depend only on WP01) — parallel
- WP09 can run in parallel with WP02/WP03 (depends only on WP01)
- WP05, WP06, WP07 are siblings under WP04 — but since WP06 depends on
  WP08, only WP05 and WP07 are immediately parallel after WP04

**Lane allocation will be computed by `finalize-tasks`** based on
`owned_files` overlap.

---

## FR Coverage Matrix

Every functional requirement is mapped to exactly one WP (the WP that builds
the code path which satisfies the requirement). The mapping below is the
authoritative source for `spec-kitty agent tasks map-requirements --batch`.

| FR | Description (brief) | Owning WP |
|---|---|---|
| FR-001 | Browser PKCE primary, no password prompt | WP04 |
| FR-002 | Device flow fallback | WP05 |
| FR-003 | Loopback callback no port config | WP02 |
| FR-004 | 43-char crypto verifier RFC 7636 | WP02 |
| FR-005 | 5-min loopback callback timeout | WP02 |
| FR-006 | OS-backed secure storage when available | WP01 |
| FR-007 | File fallback with 0600 perms + consent | WP01 |
| FR-008 | No username/password prompts anywhere | WP10 |
| FR-009 | Auto-refresh before expiry | WP01 |
| FR-010 | Single-flight refresh | WP01 |
| FR-011 | 401 → auto-refresh + 1 retry | WP08 |
| FR-012 | Expired refresh terminates with clear message | WP01 |
| FR-013 | Logout calls `/api/v1/logout` | WP06 |
| FR-014 | Server logout failure does not block local delete | WP06 |
| FR-015 | Status shows user/team/expiry/storage backend | WP07 |
| FR-016 | TokenManager is sole source for ALL transports | WP08 |
| FR-017 | All HTTP callers use TokenManager | WP08 |
| FR-018 | Device polling respects interval, ≤10s cap | WP03 |
| FR-019 | User code human-friendly format | WP03 |
| FR-020 | `--headless` does not open browser | WP05 |

**Coverage**: 20/20 FRs mapped.

---

## Next Steps

1. Run `spec-kitty agent mission finalize-tasks --json --mission 080-browser-mediated-oauth-cli-auth`
   to compute lanes and commit.
2. Run `spec-kitty agent tasks map-requirements --batch '{...}'` with the
   mapping from the FR Coverage Matrix above.
3. Run `/spec-kitty-implement-review` to dispatch implementation.

---

## WP Sizing Summary

| WP | Subtasks | Est. lines | Status |
|---|---|---|---|
| WP01 | 8 | ~450 | ✓ |
| WP02 | 7 | ~400 | ✓ |
| WP03 | 4 | ~280 | ✓ |
| WP04 | 8 | ~500 | ✓ (largest, sets up dispatch shell) |
| WP05 | 5 | ~280 | ✓ |
| WP06 | 4 | ~270 | ✓ |
| WP07 | 4 | ~270 | ✓ |
| WP08 | 7 | ~480 | ✓ (critical path: rewires legacy transports) |
| WP09 | 4 | ~280 | ✓ |
| WP10 | 5 | ~260 | ✓ |
| WP11 | 8 | ~480 | ✓ (final gate with grep audits) |
| **Total** | **64** | **~3950** | **All within ideal range** |

All WPs sized 4-8 subtasks, all prompts estimated 260-500 lines. None exceed
the 700-line / 10-subtask hard limit.
