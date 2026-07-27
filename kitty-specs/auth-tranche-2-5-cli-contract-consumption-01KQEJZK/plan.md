# Implementation Plan: CLI Auth Tranche 2.5 Contract Consumption

**Branch**: `auth-tranche-2-5-cli-contract-consumption` | **Date**: 2026-04-30 | **Spec**: [spec.md](spec.md)

## Summary

Update four CLI surfaces to consume the Tranche 2 server auth contract: (1) swap `auth logout` from `POST /api/v1/logout` (bearer-only, retired) to `POST /oauth/revoke` (token-possession, RFC 7009), with distinct output for three logout outcomes; (2) add 409 benign-replay handling inside `run_refresh_transaction`'s `_run_locked`, keeping the retry atomic under the existing machine-wide lock; (3) add `auth doctor --server` as an opt-in network path that refreshes then calls `GET /api/v1/session-status`, while preserving the default offline doctor contract; (4) update tests to remove legacy `/api/v1/logout` assertions and cover all new paths. A new `RevokeFlow` class in `auth/flows/revoke.py` owns the revoke HTTP call. `StoredSession` gains an optional `generation: int | None` field for forward-compatibility with token-family lineage.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: httpx (HTTP), typer (CLI), Rich (output), pytest + pytest-asyncio (tests)
**Storage**: Encrypted local session file via `SecureStorage`; machine-wide file lock for refresh serialization
**Testing**: pytest with `typer.testing.CliRunner` for CLI paths; httpx mocked at `httpx.AsyncClient` seam; `pytest-asyncio` for async auth flows
**Target Platform**: macOS/Linux/Windows (cross-platform via `specify_cli.paths`)
**Performance Goals**: Revoke call bounded to 10s timeout; refresh transaction bounded to `_REFRESH_MAX_HOLD_S = 10.0s`
**Constraints**: No new auth endpoints; retired `/api/v1/logout` must not be called; spent refresh token must never be re-submitted; default `auth doctor` must make zero outbound calls

## Charter Check

- **Language**: Python — confirmed. All changes are within `src/specify_cli/`.
- **Testing**: All new code paths require test coverage via `pytest`. CLI paths use `CliRunner`. HTTP paths mock at `httpx.AsyncClient`.
- **No implementation details in spec**: Confirmed; plan aligns with spec's behavioral requirements.
- **Branch strategy**: All changes land on `auth-tranche-2-5-cli-contract-consumption`.
- **No server changes**: Confirmed; `spec-kitty-saas` is reference-only.
- **Dependency**: `spec-kitty-saas` contract files are read-only references at `kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/`.

Charter check: **PASS** — no violations.

## Project Structure

### Documentation (this mission)

```
kitty-specs/auth-tranche-2-5-cli-contract-consumption-01KQEJZK/
├── plan.md              # This file
├── research.md          # Phase 0: contract findings and decision rationale
├── data-model.md        # Phase 1: changed/new types and state machines
├── contracts/           # Phase 1: CLI-facing contract summaries
│   ├── revoke-call.md
│   ├── refresh-replay.md
│   └── session-status-call.md
└── tasks/               # Created by /spec-kitty.tasks
```

### Source Code (affected files)

```
src/specify_cli/auth/
├── errors.py                    # + RefreshReplayError (new)
├── session.py                   # + generation: int | None = None field
├── flows/
│   ├── refresh.py               # + 409 detection → raises RefreshReplayError
│   └── revoke.py                # NEW: RevokeFlow class
├── refresh_transaction.py       # + replay handling in _run_locked
└── token_manager.py             # no interface change; outcome set unchanged

src/specify_cli/cli/commands/
├── auth.py                      # + --server flag on doctor command
├── _auth_logout.py              # rewritten: RevokeFlow replaces _call_server_logout
└── _auth_doctor.py              # + server: bool param + ServerSessionStatus + hint

tests/
├── auth/
│   ├── test_refresh_transaction.py   # + 409 replay paths
│   ├── flows/
│   │   ├── test_refresh_flow.py      # + 409 response handling
│   │   └── test_revoke_flow.py       # NEW
│   └── integration/
│       └── test_logout_e2e.py        # updated for /oauth/revoke
├── cli/commands/
│   ├── test_auth_logout.py           # updated: /api/v1/logout → /oauth/revoke
│   └── test_auth_doctor.py           # + --server flag paths

kitty-specs/auth-tranche-2-5-cli-contract-consumption-01KQEJZK/
└── dev-smoke-checklist.md            # Created in WP05
```

## Work Packages

### WP01 — Error Foundation and StoredSession Extension

**Goal**: Establish the type changes that WP02, WP03, and WP04 all depend on. Small surface, high leverage.

**Files**:
- `src/specify_cli/auth/errors.py` — add `RefreshReplayError`
- `src/specify_cli/auth/session.py` — add `generation: int | None = None`

**Changes**:

1. **`errors.py`**: Add `RefreshReplayError(TokenRefreshError)`. Carries `retry_after: int` from the server's 409 `retry_after` field (0–5s). The retry decision is made by `_run_locked`, not the caller, but the field may be useful for future logging.

2. **`session.py`**: Add `generation: int | None = None` to `StoredSession` as the last field (default `None` for backward-compatible deserialization). Update `to_dict()` to emit `"generation": self.generation`. Update `from_dict()` to read `data.get("generation")` (returns `None` for existing stored sessions that predate Tranche 2).

**Tests**: Verify existing `StoredSession` round-trip tests still pass (field is optional with default `None`).

---

### WP02 — RevokeFlow and Logout Migration

**Goal**: Replace the retired `/api/v1/logout` bearer call with RFC 7009-compliant `/oauth/revoke`, distinguishing three outcome states in output.

**Files**:
- `src/specify_cli/auth/flows/revoke.py` — NEW
- `src/specify_cli/cli/commands/_auth_logout.py` — rewrite server call
- `tests/auth/flows/test_revoke_flow.py` — NEW
- `tests/cli/commands/test_auth_logout.py` — update

**Changes**:

1. **`revoke.py`** — `RevokeFlow` class with `RevokeOutcome` enum:
   - `REVOKED`: HTTP 200 + `{"revoked": true}`
   - `SERVER_FAILURE`: 4xx/5xx or unexpected body (5xx must never be reported as success)
   - `NETWORK_ERROR`: `httpx.RequestError`
   - `NO_REFRESH_TOKEN`: session has no refresh token
   - POSTs `token=session.refresh_token` + `token_type_hint=refresh_token` form-encoded; 10s timeout
   - Never raises; unexpected exceptions map to `SERVER_FAILURE` with log warning

2. **`_auth_logout.py`** — `logout_impl` update:
   - Call `RevokeFlow().revoke(session)`, map outcome to output line
   - Local cleanup (`tm.clear_session()`) runs unconditionally after the revoke call
   - Remove `_call_server_logout` entirely

3. **`test_auth_logout.py`** — update:
   - Remove all assertions on `POST /api/v1/logout`
   - Assert revoke called with correct URL and body shape (`token=...`, `token_type_hint=refresh_token`)
   - Cover: 200 success, 5xx failure, network error, no-refresh-token, `--force`

---

### WP03 — Refresh 409 Benign Replay Handling

**Goal**: Handle `refresh_replay_benign_retry` atomically inside `_run_locked`. One transaction. Spent token never re-submitted.

**Files**:
- `src/specify_cli/auth/flows/refresh.py` — detect 409
- `src/specify_cli/auth/refresh_transaction.py` — replay handler in `_run_locked`
- `tests/auth/flows/test_refresh_flow.py` — new 409 cases
- `tests/auth/test_refresh_transaction.py` — new replay paths

**Changes**:

1. **`refresh.py`**: Add 409 branch — check `body.get("error") == "refresh_replay_benign_retry"`, raise `RefreshReplayError(retry_after=body.get("retry_after", 0))`.

2. **`refresh_transaction.py`**: Add `except RefreshReplayError` in `_run_locked` after the existing rejection handler:
   - Re-read persisted session
   - If `None` or same refresh token as spent → return `LOCK_TIMEOUT_ERROR`
   - If different refresh token → retry `refresh_flow.refresh(repersisted)` once
   - Retry success → `storage.write(updated)`, return `REFRESHED`
   - Retry failure (any exception) → return `LOCK_TIMEOUT_ERROR`

3. **`_update_session`**: Capture `generation=tokens.get("generation")` in returned `StoredSession`.

**Tests**:
- 409 body → `RefreshReplayError` raised by `TokenRefreshFlow`
- Replay + newer persisted token → `REFRESHED`, retry called with new token not spent token
- Replay + same persisted token → `LOCK_TIMEOUT_ERROR`, no second network call
- Replay + `None` persisted → `LOCK_TIMEOUT_ERROR`

---

### WP04 — Auth Doctor `--server` Flag

**Goal**: Opt-in server-aware session check. Default offline behavior and all existing tests unchanged.

**Files**:
- `src/specify_cli/cli/commands/_auth_doctor.py` — add server path
- `src/specify_cli/cli/commands/auth.py` — wire `--server` flag
- `tests/cli/commands/test_auth_doctor.py` — add server-path tests

**Changes**:

1. **`_auth_doctor.py`**:
   - Add `ServerSessionStatus(active, session_id, error)` frozen dataclass
   - Add `async def _check_server_session() -> ServerSessionStatus`: call `get_access_token()` (auto-refresh), GET `/api/v1/session-status`, map 200/401/error to `ServerSessionStatus`; no token internals in result
   - `doctor_impl` gains `server: bool = False`; when True: run server check, render "Server Session" section
   - Default output (server=False): append "Run `spec-kitty auth doctor --server` to verify server session status."

2. **`auth.py`**: Add `server: bool = typer.Option(False, "--server", ...)` to doctor command; pass to `doctor_impl`.

**Tests**:
- Default `doctor` still makes zero outbound calls (existing tests pass unchanged)
- `--server` + 200 → output shows "active", session_id displayed, no token content
- `--server` + 401 → output shows re-authenticate guidance
- `--server` + network error → graceful message, no crash

---

### WP05 — Integration Tests and Dev Smoke

**Goal**: Full suite green, no legacy assertions, dev smoke checklist produced.

**Files**:
- `tests/auth/integration/test_logout_e2e.py` — update for `/oauth/revoke`
- `kitty-specs/auth-tranche-2-5-cli-contract-consumption-01KQEJZK/dev-smoke-checklist.md` — NEW

**Steps**:
1. `uv run pytest tests/cli/commands/test_auth_logout.py tests/auth/integration/test_logout_e2e.py` — zero legacy `/api/v1/logout` calls
2. `uv run pytest tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_repair.py tests/auth/test_auth_doctor_offline.py` — offline doctor tests unchanged
3. `uv run pytest tests/auth tests/cli/commands/test_auth_status.py` — full auth suite
4. Produce `dev-smoke-checklist.md` with commands and expected output for login → status → doctor → doctor --server → logout against `https://spec-kitty-dev.fly.dev`

## Execution Lanes

```
WP01 (foundation: errors.py + session.py)
├── Lane A: WP02 (revoke/logout) → WP03 (refresh 409)
└── Lane B: WP04 (doctor --server)   [independent of WP02/03]

[both lanes complete] → WP05 (integration + smoke)
```

WP04 is independent of WP02 and WP03 after WP01 completes. WP02 and WP03 share the refresh transaction stack and must be sequential within Lane A.

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 409 retry location | Inside `_run_locked` (one transaction) | Replay is mechanical recovery under the same concurrency contract as stale-session reconciliation. Keeps token_manager outcome set unchanged. |
| `generation` field | `StoredSession.generation: int | None = None` | Forward-compatible at zero cost. Backward-compatible via `.get()` deserialization. Enables future local/server generation comparison. |
| Revoke client | `auth/flows/revoke.py` `RevokeFlow` | Security-relevant false-success behavior warrants its own boundary, injection seam for tests, and consistent module layout with `TokenRefreshFlow`. |
| `auth doctor --server` | Opt-in flag; default stays offline | Preserves existing test assertions and user expectation that `doctor` is a safe read-only diagnostic. |
| Revoke encoding | Form-encoded | Matches contract's supported types and existing httpx usage in logout. |
| Replay retry limit | One retry only | If the second attempt fails, surface `LOCK_TIMEOUT_ERROR`. Avoids loops; the one retry covers the network-drop scenario. |
