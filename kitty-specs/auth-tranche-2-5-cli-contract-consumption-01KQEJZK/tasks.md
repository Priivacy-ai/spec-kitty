# Tasks: CLI Auth Tranche 2.5 Contract Consumption

**Mission**: `auth-tranche-2-5-cli-contract-consumption-01KQEJZK`
**Branch**: `auth-tranche-2-5-cli-contract-consumption`
**Generated**: 2026-04-30

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `RefreshReplayError(TokenRefreshError)` to `auth/errors.py` | WP01 | No | [D] |
| T002 | Add `generation: int \| None = None` field to `StoredSession` | WP01 | No | [D] |
| T003 | Update `to_dict()` and `from_dict()` for `generation` field (backward-compat) | WP01 | No | [D] |
| T004 | Verify existing `StoredSession` round-trip tests pass with new field | WP01 | No | [D] |
| T005 | Create `auth/flows/revoke.py` with `RevokeOutcome` enum and `RevokeFlow` class | WP02 | No |
| T006 | Rewrite `_auth_logout.py` to use `RevokeFlow`, map outcomes to three output states | WP02 | No |
| T007 | Write `tests/auth/test_revoke_flow.py` covering all `RevokeOutcome` paths | WP02 | No |
| T008 | Update `tests/cli/commands/test_auth_logout.py`: remove `/api/v1/logout` assertions, add `/oauth/revoke` assertions | WP02 | No |
| T009 | Add 409 branch in `TokenRefreshFlow.refresh()` — raise `RefreshReplayError` | WP03 | No |
| T010 | Add `except RefreshReplayError` handler in `_run_locked`: reload, compare, one retry | WP03 | No |
| T011 | Capture `generation` from response in `TokenRefreshFlow._update_session()` | WP03 | No |
| T012 | Add 409 test cases in `tests/auth/test_refresh_flow.py` | WP03 | No |
| T013 | Add replay transaction test cases in `tests/auth/concurrency/test_stale_grant_preservation.py` | WP03 | No |
| T014 | Add `ServerSessionStatus` frozen dataclass to `_auth_doctor.py` | WP04 | No |
| T015 | Add `async def _check_server_session()` to `_auth_doctor.py` | WP04 | No |
| T016 | Extend `doctor_impl` with `server: bool = False` parameter and server-check branch | WP04 | No |
| T017 | Add default doctor hint: "Run `spec-kitty auth doctor --server` to verify server session status." | WP04 | No |
| T018 | Wire `--server` flag in `auth.py` doctor command; pass to `doctor_impl` | WP04 | No |
| T019 | Add `--server` tests in `tests/auth/test_auth_doctor_report.py` and verify offline tests unchanged in `tests/auth/test_auth_doctor_offline.py` | WP04 | No |
| T020 | Update `tests/auth/integration/test_logout_e2e.py` for `/oauth/revoke` expectations | WP02 | No |
| T021 | Run focused logout + doctor test suites; confirm zero legacy `/api/v1/logout` assertions | WP05 | No |
| T022 | Run full auth + status test suite; confirm doctor offline tests pass unchanged | WP05 | No |
| T023 | Produce `dev-smoke-checklist.md` with step-by-step commands and expected output | WP05 | No |

---

## Work Packages

### WP01 — Error Foundation and StoredSession Extension

**Priority**: Critical (blocks WP02 and WP03)
**Estimated prompt size**: ~250 lines
**Dependencies**: none
**Lane**: A (foundation)

**Goal**: Establish the two new types — `RefreshReplayError` and `StoredSession.generation` — that every subsequent WP depends on. Small surface, zero risk of regression beyond the session round-trip.

**Subtasks**:
- [x] T001 Add `RefreshReplayError(TokenRefreshError)` to `auth/errors.py` (WP01)
- [x] T002 Add `generation: int | None = None` field to `StoredSession` (WP01)
- [x] T003 Update `to_dict()` and `from_dict()` for `generation` field (WP01)
- [x] T004 Verify existing `StoredSession` round-trip tests pass with new field (WP01)

**Risks**: Session deserialization regression if `from_dict()` uses `data["generation"]` instead of `data.get("generation")`. Must use `.get()` for backward compat.

**Prompt file**: `tasks/WP01-error-foundation-and-stored-session-extension.md`

---

### WP02 — RevokeFlow and Logout Migration

**Priority**: High
**Estimated prompt size**: ~380 lines
**Dependencies**: WP01
**Lane**: A (sequential with WP01)

**Goal**: Replace the retired `/api/v1/logout` bearer call with RFC 7009 `/oauth/revoke`, create a dedicated `RevokeFlow` class with testable outcome enum, update all logout tests including the e2e integration test, and surface local cleanup failure as exit 1.

**Subtasks**:
- [ ] T005 Create `auth/flows/revoke.py` with `RevokeOutcome` enum and `RevokeFlow` class (WP02)
- [ ] T006 Rewrite `_auth_logout.py` to use `RevokeFlow`, map outcomes, wrap `clear_session()` with exit-1 failure path (WP02)
- [ ] T007 Write `tests/auth/test_revoke_flow.py` covering all `RevokeOutcome` paths (WP02)
- [ ] T008 Update `tests/cli/commands/test_auth_logout.py`: remove `/api/v1/logout` assertions, add cleanup-failure test (WP02)
- [ ] T020 Update `tests/auth/integration/test_logout_e2e.py` for `/oauth/revoke` expectations (WP02)

**Risks**: Must not report `REVOKED` on 5xx. `typer.Exit(code=1)` propagates through `asyncio.run()` correctly. No spent refresh token in any output or log.

**Prompt file**: `tasks/WP02-revoke-flow-and-logout-migration.md`

---

### WP03 — Refresh 409 Benign Replay Handling

**Priority**: High
**Estimated prompt size**: ~420 lines
**Dependencies**: WP02 (sequential in Lane A; requires WP01 for `RefreshReplayError`)
**Lane**: A (sequential with WP02)

**Goal**: Handle `refresh_replay_benign_retry` inside `_run_locked` — reload persisted, compare tokens, one retry if newer token available. Zero additional submissions of the spent token. Capture `generation` from successful refresh responses.

**Subtasks**:
- [ ] T009 Add 409 branch in `TokenRefreshFlow.refresh()` — raise `RefreshReplayError` (WP03)
- [ ] T010 Add `except RefreshReplayError` handler in `_run_locked` (WP03)
- [ ] T011 Capture `generation` from response in `TokenRefreshFlow._update_session()` (WP03)
- [ ] T012 Add 409 test cases in `tests/auth/test_refresh_flow.py` (WP03)
- [ ] T013 Add replay transaction test cases in `tests/auth/concurrency/test_stale_grant_preservation.py` (WP03)

**Risks**: Infinite retry loop if `RefreshReplayError` from the second attempt is not caught. Spent token re-submission if retry is called with `persisted` instead of `repersisted`.

**Prompt file**: `tasks/WP03-refresh-409-benign-replay-handling.md`

---

### WP04 — Auth Doctor `--server` Flag

**Priority**: High
**Estimated prompt size**: ~370 lines
**Dependencies**: none (independent of Lane A)
**Lane**: B (parallel with WP02/WP03)

**Goal**: Add `auth doctor --server` as an opt-in server-aware path. Default offline behavior and all existing doctor tests remain unchanged. New `ServerSessionStatus` dataclass. Refresh-then-check-status sequence.

**Subtasks**:
- [ ] T014 Add `ServerSessionStatus` frozen dataclass to `_auth_doctor.py` (WP04)
- [ ] T015 Add `async def _check_server_session()` to `_auth_doctor.py` (WP04)
- [ ] T016 Extend `doctor_impl` with `server: bool = False` parameter (WP04)
- [ ] T017 Add default doctor hint text (WP04)
- [ ] T018 Wire `--server` flag in `auth.py` doctor command (WP04)
- [ ] T019 Add `--server` tests; verify offline tests unchanged (WP04)

**Risks**: Must not call `asyncio.run()` if already inside an event loop (use `anyio.from_thread.run_sync` or check event loop state). Default doctor must make zero outbound calls even after this change.

**Prompt file**: `tasks/WP04-auth-doctor-server-flag.md`

---

### WP05 — Integration Tests and Dev Smoke

**Priority**: High (completion gate)
**Estimated prompt size**: ~280 lines
**Dependencies**: WP03, WP04
**Lane**: merge (both lanes complete)

**Goal**: Run the full suite to confirm zero legacy assertions and no regressions in offline doctor (e2e test was updated in WP02), and produce the dev smoke checklist.

**Subtasks**:
- [ ] T021 Run focused test suites; confirm zero legacy `/api/v1/logout` assertions (WP05)
- [ ] T022 Run full auth + status test suite; confirm offline doctor tests unchanged (WP05)
- [ ] T023 Produce `dev-smoke-checklist.md` with step-by-step commands and expected output (WP05)

**Risks**: Integration test environment differences (SPEC_KITTY_SAAS_URL not set). Dev smoke requires live dev server access.

**Prompt file**: `tasks/WP05-integration-tests-and-dev-smoke.md`
