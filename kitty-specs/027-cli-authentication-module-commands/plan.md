# Implementation Plan: CLI Authentication Module and Commands

**Branch**: `027-cli-authentication-module-commands` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/027-cli-authentication-module-commands/spec.md`

**CRITICAL**: All implementation work is on **spec-kitty `2.x` branch**, NOT main.

## Summary

Implement CLI-side authentication for spec-kitty sync functionality. This feature creates the `sync/auth.py` module with token obtain/store/refresh functions, three CLI commands (`auth login`, `auth logout`, `auth status`), and secure credential storage in TOML format. The module integrates with existing SaaS authentication endpoints (Feature 008) and enables the `WebSocketClient` to authenticate. This is the P0 blocker extracted from Feature 009.

## Technical Context

**Language/Version**: Python 3.12 (from spec-kitty pyproject.toml)
**Primary Dependencies**:
- `httpx` - HTTP client for API calls (already in spec-kitty dependencies)
- `click` - CLI framework (existing CLI pattern)
- `toml` - Config/credentials file format (already used for config.toml)
- `filelock` - File locking for credential race conditions

**Storage**: TOML file at `~/.spec-kitty/credentials` (600 permissions)
**Testing**: pytest (existing test framework in spec-kitty)
**Target Platform**: macOS, Linux, Windows (cross-platform CLI)
**Project Type**: Single project (CLI tool)
**Performance Goals**: Authentication completes in <10 seconds, token refresh transparent to user
**Constraints**:
- Credentials file must have 600 permissions
- No passwords stored locally (tokens only)
- Token values never in logs
- HTTPS required for all auth requests (reject non-HTTPS server URLs)

**Scale/Scope**: Single developer workflow, 7-day refresh token sessions

## Constitution Check

**Status**: PASS

### Rule: External Repositories Have NO License

This rule applies to external deliverable repositories (like spec-kitty-events), NOT the main spec-kitty repository.

- ✅ **spec-kitty is MIT licensed** - constitution explicitly states this
- ✅ This feature modifies spec-kitty, not an external repository
- ✅ No license changes required

**No constitution violations.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/027-cli-authentication-module-commands/
├── spec.md              # Feature specification (COMPLETE)
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal - references Feature 009)
├── data-model.md        # Phase 1 output (credential/token entities)
└── tasks/               # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (spec-kitty repository, 2.x branch)

```
spec-kitty/src/specify_cli/
├── sync/
│   ├── __init__.py          # UPDATE: Export AuthClient
│   ├── auth.py              # CREATE: AuthClient, token functions (currently empty)
│   ├── client.py            # EXISTING: WebSocketClient (needs auth integration)
│   ├── config.py            # EXISTING: SyncConfig for server URL
│   ├── queue.py             # EXISTING: OfflineQueue
│   └── batch.py             # EXISTING: Batch sync
├── cli/
│   └── commands/
│       └── auth.py          # CREATE: auth login/logout/status commands
└── cli.py                   # UPDATE: Register auth command group

~/.spec-kitty/
├── config.toml              # EXISTING: Server URL configuration
└── credentials              # CREATE: TOML file with tokens (600 permissions)
```

**Structure Decision**: This feature adds to the existing spec-kitty CLI structure. The `sync/auth.py` module provides authentication logic, and `cli/commands/auth.py` provides the user-facing commands. This follows the existing pattern where `sync/` contains core logic and `cli/commands/` contains Click command definitions.

## Complexity Tracking

*No constitution violations - section not required.*

## Implementation Phases

### Phase 1: Auth Module Core (sync/auth.py)

**Files**:
- `src/specify_cli/sync/auth.py` - AuthClient class and token functions

**Deliverables**:
1. `AuthClient` class with:
   - `obtain_tokens(username, password)` → calls `/api/v1/token/`
   - `refresh_tokens(refresh_token)` → calls `/api/v1/token/refresh/`
   - `obtain_ws_token(access_token)` → calls `/api/v1/ws-token/`
   - `is_authenticated()` → checks stored credentials validity
   - `get_access_token()` → returns valid token, auto-refreshing if needed
   - `clear_credentials()` → removes stored tokens
   - Enforces HTTPS-only server URL usage for all auth requests

2. `CredentialStore` class with:
   - `load()` → read TOML credentials file
   - `save(access_token, refresh_token, expires_at)` → write TOML with 600 permissions
   - `clear()` → delete credentials file
   - File locking for concurrent access

**Dependencies**: None (foundational)

### Phase 2: CLI Commands (cli/commands/auth.py)

**Files**:
- `src/specify_cli/cli/commands/auth.py` - Click command group
- `src/specify_cli/cli.py` - Register command group

**Deliverables**:
1. `auth login` command:
   - Prompt for username (visible) and password (hidden)
   - Call `AuthClient.obtain_tokens()`
   - Store credentials via `CredentialStore`
   - Display success/error message

2. `auth logout` command:
   - Call `CredentialStore.clear()`
   - Display confirmation

3. `auth status` command:
   - Check `AuthClient.is_authenticated()`
   - Display username, server URL, token expiry status

**Dependencies**: Phase 1 (auth module)

### Phase 3: WebSocket Integration

**Files**:
- `src/specify_cli/sync/client.py` - Update WebSocketClient

**Deliverables**:
1. Update `WebSocketClient` to:
   - Use `AuthClient.get_access_token()` for auth
   - Obtain WebSocket token via `AuthClient.obtain_ws_token()`
   - Handle 401 errors by triggering token refresh

**Dependencies**: Phase 1 (auth module)

### Phase 4: Tests

**Files**:
- `tests/sync/test_auth.py` - Unit tests for AuthClient
- `tests/sync/test_credentials.py` - Unit tests for CredentialStore
- `tests/cli/test_auth_commands.py` - Integration tests for CLI commands

**Deliverables**:
1. Unit tests for token obtain/refresh/clear
2. Unit tests for credential file read/write/permissions
3. Integration tests for login/logout/status commands
4. Mock server responses for offline testing
5. Validate HTTPS-only enforcement for server URL
6. Validate token values are not present in error messages/log output

**Dependencies**: Phases 1-3

## API Contract Reference

### SaaS Endpoints (Feature 008)

**POST /api/v1/token/**
```json
Request:
{
  "username": "user@example.com",
  "password": "secret"
}

Response (200):
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}

Response (401):
{
  "detail": "No active account found with the given credentials"
}
```

**POST /api/v1/token/refresh/**
```json
Request:
{
  "refresh": "eyJ..."
}

Response (200):
{
  "access": "eyJ...",
  "refresh": "eyJ..."  // Rotated
}

Response (401):
{
  "detail": "Token is invalid or expired"
}
```

**POST /api/v1/ws-token/**
```
Authorization: Bearer {access_token}

Response (200):
{
  "ws_token": "uuid-ephemeral-token",
  "expires_at": "2026-02-03T17:00:00Z",
  "expires_in": 900
}
```

### Token Lifecycle

- **Access Token**: 15 minute TTL
- **Refresh Token**: 7 day TTL, rotated on each use
- **WebSocket Token**: 15 minute TTL, obtained on-demand (not stored)

## Credential File Format

```toml
# ~/.spec-kitty/credentials
# Permissions: 600 (owner read/write only)

[tokens]
access = "eyJ..."
refresh = "eyJ..."
access_expires_at = "2026-02-03T16:45:00Z"
refresh_expires_at = "2026-02-10T16:30:00Z"

[user]
username = "user@example.com"

[server]
url = "https://spec-kitty-dev.fly.dev"
```

## Error Handling Strategy

| Error | User Message | Action |
|-------|--------------|--------|
| Invalid credentials | "Invalid username or password" | No tokens stored |
| Network timeout | "Cannot reach server. Check your connection." | Suggest retry |
| Server error (5xx) | "Server temporarily unavailable" | Suggest retry later |
| Token refresh failed | "Session expired. Please log in again." | Clear credentials, prompt login |
| File permission error | "Cannot access credentials file. Check permissions." | Suggest chmod 600 |

## Security Checklist

- ✅ Credentials file has 600 permissions (owner-only)
- ✅ Passwords never stored (only tokens)
- ✅ Token values never logged or displayed
- ✅ HTTPS enforced for all API calls
- ✅ File locking prevents race conditions
- ✅ 401 responses trigger credential clear

---

## Plan Delivery Status

**This plan is COMPLETE.**

**Artifacts**:
- `plan.md` - This file
- `research.md` - Minimal (references Feature 009 research)
- `data-model.md` - Credential and token entities

**Next Step**: `/spec-kitty.tasks` to generate work packages

**Repository**: spec-kitty (2.x branch)
**Target Files**:
- `src/specify_cli/sync/auth.py` (CREATE)
- `src/specify_cli/cli/commands/auth.py` (CREATE)
- `src/specify_cli/cli.py` (UPDATE)
- `tests/sync/test_auth.py` (CREATE)

---

**END OF IMPLEMENTATION PLAN**
