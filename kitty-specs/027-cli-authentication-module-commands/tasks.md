# Work Packages: CLI Authentication Module and Commands

**Inputs**: Design documents from `/kitty-specs/027-cli-authentication-module-commands/`
**Prerequisites**: plan.md (required), spec.md (user stories), data-model.md

**CRITICAL**: All implementation work is on **spec-kitty `2.x` branch**, NOT main.

**Tests**: Included as final work package for validation.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/` directory.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Include precise file paths or modules.

---

## Work Package WP01: Credential Storage Foundation (Priority: P0)

**Goal**: Implement the `CredentialStore` class for secure TOML-based token storage with file locking.
**Independent Test**: Can load/save/clear credentials file with proper permissions and concurrent access protection.
**Prompt**: `tasks/WP01-credential-storage-foundation.md`
**Estimated Size**: ~300 lines

### Included Subtasks
- [x] T001 Create `CredentialStore` class in `src/specify_cli/sync/auth.py` with TOML read/write
- [x] T002 Implement file locking using `filelock` library for concurrent access
- [x] T003 Implement token expiry timestamp parsing and validation
- [x] T004 Update `src/specify_cli/sync/__init__.py` to export `CredentialStore` and `AuthClient`

### Implementation Notes
- Credentials file location: `~/.spec-kitty/credentials`
- Permissions: 600 (owner read/write only)
- Use `filelock.FileLock` with `.lock` suffix file
- TOML schema defined in data-model.md
- Create `~/.spec-kitty/` directory if not exists

### Parallel Opportunities
- T001-T003 work on the same file, must be sequential
- T004 can be done after T001 skeleton exists

### Dependencies
- None (foundational work package)

### Risks & Mitigations
- Windows permission handling differs → use `filelock` which handles cross-platform
- TOML parsing errors → handle gracefully, treat corrupted file as "not authenticated"

---

## Work Package WP02: AuthClient Implementation (Priority: P0)

**Goal**: Implement the `AuthClient` class with all token operations (obtain, refresh, clear).
**Independent Test**: Can obtain tokens from SaaS API, refresh expired tokens, and clear credentials.
**Prompt**: `tasks/WP02-authclient-implementation.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T005 Create `AuthClient` class in `src/specify_cli/sync/auth.py` with `SyncConfig` integration
- [x] T006 Implement `obtain_tokens(username, password)` calling `/api/v1/token/`
- [x] T007 Implement `refresh_tokens(refresh_token)` calling `/api/v1/token/refresh/`
- [x] T008 Implement `obtain_ws_token(access_token)` calling `/api/v1/ws-token/`
- [x] T009 Implement `get_access_token()` with automatic silent refresh logic
- [x] T010 Implement `is_authenticated()` checking stored credential validity
- [x] T011 Implement `clear_credentials()` delegating to `CredentialStore`
- [x] T023 Enforce HTTPS-only server URLs for all auth requests (reject non-HTTPS with clear error)
- [x] T024 Ensure auth errors/logging never include token values (redact or omit sensitive fields)

### Implementation Notes
- Use `httpx` for HTTP client (already in dependencies)
- Server URL from `SyncConfig.get_server_url()`
- Reject non-HTTPS server URLs with a clear, user-friendly error message
- Token expiry: calculate from JWT claims or response
- Auto-refresh: if access expired but refresh valid, call refresh silently
- Error handling: distinguish 401 (bad creds) vs network errors vs 5xx
- Never include token values in error messages or logs

### Parallel Opportunities
- T006, T007, T008 are similar patterns, could be done in parallel if multiple developers
- T009 depends on T006, T007 (needs both methods)
- T010, T011 are independent utility methods

### Dependencies
- Depends on WP01 (CredentialStore must exist)

### Risks & Mitigations
- Token rotation: SaaS rotates refresh token on each use → save new refresh token on every refresh
- Network failures: use appropriate timeouts (10s), clear error messages
- JWT parsing: use standard library or decode expiry from response

---

## Work Package WP03: CLI Commands and Registration (Priority: P0)

**Goal**: Implement `auth login`, `auth logout`, `auth status` CLI commands and register them.
**Independent Test**: Developer can run `spec-kitty auth login`, authenticate, and verify with `spec-kitty auth status`.
**Prompt**: `tasks/WP03-cli-commands-and-registration.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [x] T012 Create `auth` command group in `src/specify_cli/cli/commands/auth.py`
- [x] T013 Implement `auth login` command with username prompt and hidden password input
- [x] T014 Implement `auth logout` command to clear stored credentials
- [x] T015 Implement `auth status` command to display authentication state
- [x] T016 Register `auth` command group in `src/specify_cli/cli.py`
- [x] T017 Add user-friendly error messages for all auth failure modes

### Implementation Notes
- Use Click framework (existing CLI pattern)
- `auth login`: `click.prompt()` for username, `click.prompt(hide_input=True)` for password
- `auth status`: show username, server URL, access token expiry, refresh token expiry
- Error messages per plan.md Error Handling Strategy table
- Check if already authenticated before login, offer to re-authenticate

### Parallel Opportunities
- T013, T014, T015 are independent commands, can be developed in parallel
- T016, T017 are finishing touches after commands exist

### Dependencies
- Depends on WP02 (AuthClient methods must exist)

### Risks & Mitigations
- Password echo on some terminals → always use `hide_input=True`
- Click version compatibility → use patterns from existing CLI commands

---

## Work Package WP04: WebSocket Integration (Priority: P1)

**Goal**: Integrate authentication with existing `WebSocketClient` for seamless authenticated connections.
**Independent Test**: `WebSocketClient` can connect using tokens from `AuthClient`, and handles 401 with retry.
**Prompt**: `tasks/WP04-websocket-integration.md`
**Estimated Size**: ~250 lines

### Included Subtasks
- [x] T018 Update `WebSocketClient` in `src/specify_cli/sync/client.py` to use `AuthClient` for token retrieval
- [x] T019 Implement 401 response handling with automatic token refresh and retry

### Implementation Notes
- Current `WebSocketClient.__init__` takes `token` parameter directly
- Change to use `AuthClient.obtain_ws_token()` internally
- On 401 during connection or operation: call `AuthClient.get_access_token()` (triggers refresh), get new WS token, retry
- Max 1 retry to prevent infinite loops

### Parallel Opportunities
- None (both subtasks modify same file with related logic)

### Dependencies
- Depends on WP02 (AuthClient must provide `obtain_ws_token()` and `get_access_token()`)

### Risks & Mitigations
- Breaking existing WebSocketClient interface → maintain backward compatibility or update all callers
- Retry loops → limit to 1 retry, fail with clear message on second 401

---

## Work Package WP05: Tests and Validation (Priority: P2)

**Goal**: Create comprehensive tests for credential storage, auth client, and CLI commands.
**Independent Test**: All tests pass, covering happy paths and error scenarios.
**Prompt**: `tasks/WP05-tests-and-validation.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [x] T020 Create unit tests for `CredentialStore` in `tests/sync/test_credentials.py`
- [x] T021 Create unit tests for `AuthClient` in `tests/sync/test_auth.py`
- [x] T022 Create integration tests for CLI commands in `tests/cli/test_auth_commands.py`
- [x] T025 Add tests that reject non-HTTPS server URLs for auth requests
- [x] T026 Add tests ensuring token values are not present in error messages/log output

### Implementation Notes
- Use pytest (existing test framework)
- Mock HTTP responses for AuthClient tests (don't call real SaaS)
- Test file permissions on Unix (skip on Windows or use mock)
- Test concurrent access with file locking
- CLI tests: use Click's `CliRunner` for command testing

### Parallel Opportunities
- All three test files can be developed in parallel

### Dependencies
- Depends on WP01, WP02, WP03 (code must exist to test)

### Risks & Mitigations
- Flaky tests with real file system → use temp directories
- Platform-specific behavior → conditional tests or mocks for Windows

---

## Dependency & Execution Summary

```
WP01 (Credential Storage)
  │
  └── WP02 (AuthClient)
        │
        ├── WP03 (CLI Commands)
        │
        └── WP04 (WebSocket Integration)
              │
              └── WP05 (Tests) ← depends on WP01-WP04
```

- **Sequence**: WP01 → WP02 → WP03 & WP04 (parallel) → WP05
- **MVP Scope**: WP01 + WP02 + WP03 (developer can authenticate and check status)
- **Full Scope**: All 5 work packages (includes WebSocket integration and tests)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create CredentialStore class | WP01 | P0 | No |
| T002 | Implement file locking | WP01 | P0 | No |
| T003 | Implement token expiry handling | WP01 | P0 | No |
| T004 | Update sync/__init__.py exports | WP01 | P0 | Yes |
| T005 | Create AuthClient class | WP02 | P0 | No |
| T006 | Implement obtain_tokens() | WP02 | P0 | Yes |
| T007 | Implement refresh_tokens() | WP02 | P0 | Yes |
| T008 | Implement obtain_ws_token() | WP02 | P0 | Yes |
| T009 | Implement get_access_token() | WP02 | P0 | No |
| T010 | Implement is_authenticated() | WP02 | P0 | Yes |
| T011 | Implement clear_credentials() | WP02 | P0 | Yes |
| T012 | Create auth command group | WP03 | P0 | No |
| T013 | Implement auth login | WP03 | P0 | Yes |
| T014 | Implement auth logout | WP03 | P0 | Yes |
| T015 | Implement auth status | WP03 | P0 | Yes |
| T016 | Register auth in cli.py | WP03 | P0 | No |
| T017 | Add error messages | WP03 | P0 | No |
| T018 | Update WebSocketClient | WP04 | P1 | No |
| T019 | Handle 401 with retry | WP04 | P1 | No |
| T020 | Unit tests for CredentialStore | WP05 | P2 | Yes |
| T021 | Unit tests for AuthClient | WP05 | P2 | Yes |
| T022 | Integration tests for CLI | WP05 | P2 | Yes |
| T023 | Enforce HTTPS-only server URLs | WP02 | P0 | Yes |
| T024 | Redact tokens in errors/logs | WP02 | P0 | Yes |
| T025 | Tests for HTTPS-only enforcement | WP05 | P2 | Yes |
| T026 | Tests for token redaction | WP05 | P2 | Yes |

---

**Total**: 26 subtasks across 5 work packages
**MVP**: WP01 + WP02 + WP03 (19 subtasks)
