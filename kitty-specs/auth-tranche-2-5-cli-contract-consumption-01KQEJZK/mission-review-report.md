# Mission Review Report

**Mission**: `auth-tranche-2-5-cli-contract-consumption-01KQEJZK`  
**Mission Number**: 108  
**Branch**: `auth-tranche-2-5-cli-contract-consumption`  
**Review Date**: 2026-04-30  
**Reviewer**: Claude Sonnet 4.6 (senior review agent)  
**Verdict**: PASS WITH NOTES

---

## Executive Summary

All 5 WPs have been implemented, reviewed, and merged. The core auth contract migration is correct: `/oauth/revoke` replaces `/api/v1/logout`, 409 benign replay is handled safely inside `_run_locked`, `auth doctor --server` is gated behind an opt-in flag, and the offline doctor invariant is preserved. All 338 auth/CLI tests pass (2 skipped, pre-existing). Contract tests (237 pass) and architectural tests (92 pass, 1 skip) also pass clean.

One minor spec inconsistency is noted (FR-006 wording vs. contract reality). No blocking defects found.

---

## Step 1: Mission Orientation

| Field | Value |
|-------|-------|
| Mission ID | 01KQEJZKMQTQZHT4WY2CDQWQN2 |
| Created | 2026-04-30T06:59:51Z |
| Target branch | `auth-tranche-2-5-cli-contract-consumption` |
| Work packages | WP01–WP05 (all `done`) |
| Merge commit | `94007e4c` (squash merge) |
| VCS locked at | 2026-04-30T12:49:17Z |

All WPs transitioned through the full lifecycle (planned → claimed → in_progress → for_review → in_review → approved → done). WP02, WP03, WP04 were individually reviewed and approved. WP05 had one review rejection cycle (dev-smoke-checklist.md was temporarily deleted by a cleanup commit) that was resolved before final approval.

---

## Step 2: Contract Absorption

Three contract documents were present and fully specified:

- `contracts/revoke-call.md`: POST /oauth/revoke, form-encoded, 10s timeout, 5 outcome states
- `contracts/refresh-replay.md`: 409 benign replay handling with state machine, invariants on spent token
- `contracts/session-status-call.md`: GET /api/v1/session-status, refresh-then-check sequence

All three contracts were used faithfully in the implementation. The spec and implementation both use the server's canonical 409 field, `error: "refresh_replay_benign_retry"`, per `contracts/refresh-replay.md`.

---

## Step 3: Git Timeline

The squash merge commit (`94007e4c`) contains all source changes. Net diff from `main`:

- 45 files changed, 5028 insertions, 265 deletions
- Source changes: 7 files in `src/specify_cli/auth/` and `src/specify_cli/cli/commands/`
- Test changes: 7 files in `tests/`
- Planning artifacts: 30+ files in `kitty-specs/` directory

Source files changed:
- `src/specify_cli/auth/errors.py` (+16 lines: RefreshReplayError)
- `src/specify_cli/auth/session.py` (+4 lines: generation field)
- `src/specify_cli/auth/flows/refresh.py` (+11 lines: 409 detection)
- `src/specify_cli/auth/flows/revoke.py` (NEW, 75 lines)
- `src/specify_cli/auth/refresh_transaction.py` (+57 lines: replay handler)
- `src/specify_cli/cli/commands/_auth_doctor.py` (+153 lines: server path)
- `src/specify_cli/cli/commands/_auth_logout.py` (rewritten: -97 / +123)
- `src/specify_cli/cli/commands/auth.py` (+6 lines: --server flag)

---

## Step 4: WP Review History

| WP | Cycles | Final Verdict | Key Evidence |
|----|--------|---------------|--------------|
| WP01 | 1 | Approved | RefreshReplayError hierarchy correct; generation field backward-compat |
| WP02 | 1 | Approved | RevokeFlow correct; /api/v1/logout fully removed; 5xx never maps to REVOKED |
| WP03 | 1 | Approved | retry uses repersisted not persisted; spent token never resubmitted; one retry max |
| WP04 | 1 | Approved | ServerSessionStatus frozen dataclass; C-007 offline invariant preserved; --server wired |
| WP05 | 2 | Approved (cycle 2 after fix) | dev-smoke-checklist.md reintroduced; zero legacy /api/v1/logout assertions |

WP05 review cycle 1 was rejected because `dev-smoke-checklist.md` was deleted by a lane-cleanup commit. It was restored before the second review and is present at HEAD with all 6 required steps and the "Known Non-Issue" reference to #889.

---

## Step 5: FR Trace

### FR-001: POST /oauth/revoke replaces /api/v1/logout

**Status: PASS**

`src/specify_cli/auth/flows/revoke.py` implements `RevokeFlow.revoke()` which POSTs to `{saas_url}/oauth/revoke` with form-encoded `token=session.refresh_token&token_type_hint=refresh_token`. No `Authorization` header is included. `_auth_logout.py` calls `RevokeFlow().revoke(session)` when not using `--force`.

Test: `test_revoke_request_shape` in `tests/auth/test_revoke_flow.py` asserts the URL, body fields, and absence of Authorization header.

Zero legacy `/api/v1/logout` references remain in `src/` or `tests/`.

### FR-002: Logout output distinguishes three outcomes

**Status: PASS**

`_auth_logout.py._print_revoke_outcome()` maps all four `RevokeOutcome` values to distinct console lines:
- `REVOKED`: "Server revocation confirmed."
- `NETWORK_ERROR`: "Server revocation not confirmed (network error)."
- `SERVER_FAILURE`: "Server revocation not confirmed (server error)."
- `NO_REFRESH_TOKEN`: "Server revocation could not be attempted (no refresh token)."

Exit code 0 in all non-failure outcomes (only `clear_session()` failure triggers exit 1). Outcome (b) — server failure / network error — is explicitly not a command failure.

### FR-003: Local credential deletion unconditional

**Status: PASS**

`logout_impl()` calls `tm.clear_session()` unconditionally after the revoke call, regardless of `RevokeOutcome`. The `--force` flag also proceeds to local cleanup. Tests: `test_logout_server_failure_still_clears_local`, `test_logout_network_error_still_clears_local`.

### FR-004: No refresh token → best-effort local cleanup

**Status: PASS**

`RevokeFlow.revoke()` checks `if not session.refresh_token` and returns `RevokeOutcome.NO_REFRESH_TOKEN` immediately without making any HTTP call. `logout_impl()` still calls `tm.clear_session()`. Test: `test_revoke_no_refresh_token` asserts `async_client.post.assert_not_called()`.

### FR-005: 5xx not reported as successful revocation

**Status: PASS**

`RevokeFlow.revoke()` only returns `RevokeOutcome.REVOKED` when `response.status_code == 200` AND `body.get("revoked") is True`. All other status codes (including 5xx) return `SERVER_FAILURE`. Test: `test_revoke_500` asserts `outcome is RevokeOutcome.SERVER_FAILURE`.

### FR-006: Refresh flow detects 409 + refresh_replay_benign_retry

**Status: PASS**

`refresh.py` checks `if response.status_code == 409` then `if body.get("error") == "refresh_replay_benign_retry"`, raises `RefreshReplayError`. The implementation matches the contract.

Test: `test_refresh_409_benign_replay_raises` verifies `RefreshReplayError` is raised with `retry_after=2`.

Non-replay 409 (other error values) fall through to generic `TokenRefreshError`. Test: `test_refresh_409_other_error_raises_token_refresh_error`.

### FR-007: _run_locked reloads persisted on 409, retries if different refresh_token

**Status: PASS**

`refresh_transaction.py._run_locked()` catches `RefreshReplayError`, calls `storage.read()` to get `repersisted`, and only retries `refresh_flow.refresh(repersisted)` when `repersisted.refresh_token != persisted.refresh_token`.

Test: `test_replay_newer_persisted_retries_and_refreshes` — asserts `call_count == 2` and that the second call received the newer token.

### FR-008: Retry uses repersisted NOT persisted; same token → LOCK_TIMEOUT_ERROR

**Status: PASS**

When `repersisted.refresh_token == persisted.refresh_token`, `_run_locked` returns `RefreshOutcome.LOCK_TIMEOUT_ERROR` without making a second network call.

Test `test_replay_same_token_returns_lock_timeout` asserts `call_count == 1` and `LOCK_TIMEOUT_ERROR`.

Critical test `test_replay_spent_token_never_resubmitted` asserts `calls[1] == "fresh"` and `"spent" not in calls[1:]`.

### FR-009: One retry maximum; second failure → LOCK_TIMEOUT_ERROR

**Status: PASS**

The retry block in `_run_locked` uses a bare `except Exception` for the second attempt, mapping any failure (including `RefreshReplayError`) to `LOCK_TIMEOUT_ERROR`. No third attempt is possible.

Test: `test_replay_retry_also_fails_returns_lock_timeout` asserts `call_count == 2` and `LOCK_TIMEOUT_ERROR`.

### FR-010: generation field captured from refresh response

**Status: PASS**

`TokenRefreshFlow._update_session()` includes `generation=tokens.get("generation")` in the returned `StoredSession`, using `.get()` (returns `None` if absent).

Tests: `test_refresh_200_captures_generation` (generation=7 in response → session.generation==7) and `test_refresh_200_missing_generation_is_none` (absent key → None).

### FR-011: StoredSession.generation persisted and round-trip safe

**Status: PASS**

`session.py` adds `generation: int | None = None` as the last field. `to_dict()` emits `"generation": self.generation`. `from_dict()` uses `data.get("generation")` (backward-compatible; returns `None` for pre-Tranche-2 sessions).

Test: `test_from_dict_backward_compat_no_generation` deletes the key and asserts `session.generation is None` without `KeyError`.

### FR-012: clear_session() failure → typer.Exit(code=1)

**Status: PASS**

`logout_impl()` wraps `tm.clear_session()` in `try/except Exception` and raises `typer.Exit(code=1)` on any failure.

Test: `test_logout_local_cleanup_failure_exits_1` asserts exit code 1.

### FR-013: RevokeFlow raises nothing; outcomes map cleanly

**Status: PASS**

`RevokeFlow.revoke()` has a top-level `except Exception` that maps all unexpected exceptions to `SERVER_FAILURE`. The docstring says "Never raises."

Test: `test_revoke_unexpected_exception_is_server_failure` injects `RuntimeError` and asserts `SERVER_FAILURE`.

### FR-014: _auth_doctor.py default makes zero outbound calls

**Status: PASS**

`doctor_impl()` only calls `asyncio.run(_check_server_session())` when `server=True`. Default path (`server=False`) makes no outbound calls.

Test: `test_no_outbound_http` patches `httpx.AsyncClient` to raise `AssertionError` if instantiated, and calls `doctor_impl(server=False)` implicitly (default). Test passes clean.

### FR-015: C-007 preserved (offline doctor unchanged)

**Status: PASS**

`test_auth_doctor_offline.py::test_no_outbound_http` and `::test_no_state_mutation_default` both pass unchanged. The `doctor_impl` signature adds `server: bool = False` with a default that preserves the offline contract.

### FR-016: --server does refresh-then-check

**Status: PASS**

`_check_server_session()` calls `await tm.get_access_token()` first (which triggers refresh if needed), then GETs `/api/v1/session-status` with `Authorization: Bearer {access_token}`.

Tests: `test_check_server_session_active`, `test_check_server_session_401`, `test_check_server_session_network_error` all pass.

`test_doctor_impl_server_true_renders_active` and `test_doctor_impl_server_true_renders_reauthenticate` cover the full `doctor_impl(server=True)` path.

### FR-017: ServerSessionStatus frozen dataclass

**Status: PASS**

`ServerSessionStatus(active: bool, session_id: str | None = None, error: str | None = None)` is a `@dataclass(frozen=True)`. No raw tokens, token_family_id, is_revoked, or revocation_reason fields.

Test: `test_server_session_status_frozen` verifies the dataclass is frozen.

---

## Step 6: Anti-pattern Checks

### Dead Code

- `RevokeFlow` is imported and used only in `_auth_logout.py`. No dead code.
- `RefreshReplayError` is imported in `refresh.py` (raises it) and `refresh_transaction.py` (catches it). No dead code.
- `ServerSessionStatus` is defined and used in `_auth_doctor.py` only. Live and tested.

### Silent Failures

- `RevokeFlow.revoke()`: all exception paths return an outcome enum value (no silent `return None`). Unexpected exceptions map to `SERVER_FAILURE` with a `log.warning`.
- `_run_locked` replay path: all branches return `RefreshResult`. The bare `except Exception` on the retry catches cleanly.
- `_check_server_session()`: all paths return `ServerSessionStatus`. Never raises.

### No Spent Token Logged

- `revoke.py`: `session.refresh_token` is used only in the POST body dict. No `log.*` call includes the token value.
- `_auth_logout.py`: does not reference `session.refresh_token` directly. Outcome messages contain no token values.
- `refresh_transaction.py`: log warnings in the replay path use only type names and counts, not token values.

### Offline Contract

- `_auth_doctor.py` imports `httpx` inside `_check_server_session()` only (deferred import). The function is only called when `server=True`. The module-level `assemble_report()` and `render_report()` make no outbound calls.

---

## Step 7: Security Checks

| Check | Finding |
|-------|---------|
| HTTP timeouts | `revoke.py`: `_HTTP_TIMEOUT_SECONDS = 10.0` applied. `_auth_doctor.py`: `httpx.AsyncClient(timeout=10.0)`. Both match the plan's 10s requirement. |
| Token exposure | No refresh token or access token value appears in any log call, error message, or console output. |
| No subprocess | No `subprocess` or `shell=True` in any changed file. |
| Authorization header | Revoke call sends no Authorization header (verified by `test_revoke_request_shape`). |
| Sensitive fields in ServerSessionStatus | Dataclass has only `active`, `session_id`, `error`. No `token_family_id`, `is_revoked`, `revocation_reason`. |
| NFR-001 | Console output from `render_report()` includes only `format_duration(access_remaining)`, not the token value. Server output shows `session_id` only. |

---

## Step 8: Hard Gates

| Gate | Result |
|------|--------|
| `uv run pytest tests/contract/ -v` | 237 passed, 1 skipped |
| `uv run pytest tests/architectural/ -v` | 92 passed, 1 skipped |
| `uv run pytest tests/auth/ tests/cli/commands/test_auth_logout.py` | 338 passed, 2 skipped |
| Focused revoke+refresh+replay tests | 49 passed |
| Focused doctor tests | 25 passed |
| `grep -rn "api/v1/logout" src/ tests/` | 0 matches |
| `issue-matrix.md` | Not present (not required by this mission's spec) |
| `dev-smoke-checklist.md` | Present at HEAD with 6 steps + Known Non-Issue |

---

## Step 9: Findings Summary

### Confirmed Correct

1. **RFC 7009 revocation**: Form-encoded, no auth header, correct URL, 10s timeout, 5 outcome states.
2. **5xx never REVOKED**: Implementation correctly gates `REVOKED` on `body.get("revoked") is True`.
3. **Benign replay isolation**: Spent token never resubmitted; one retry only; all three edge cases (None persisted, same token, second failure) return `LOCK_TIMEOUT_ERROR`.
4. **generation capture**: `tokens.get("generation")` with None fallback; backward-compat via `data.get("generation")`.
5. **Offline doctor invariant**: `asyncio.run` for server check is inside `if server:` branch only; two strong tests enforce it.
6. **Token security**: No raw token values appear in logs, console output, or error messages anywhere in the changed surface.
7. **Exit codes**: exit 0 on all partial-success paths; exit 1 only on `clear_session()` failure.
8. **Legacy cleanup**: Zero `/api/v1/logout` references in source or tests.

### Notes (Non-Blocking)

1. **WP05 review cycle**: `dev-smoke-checklist.md` was temporarily deleted by a lane-cleanup commit during WP05, requiring a second review cycle. The file is present and correct at final HEAD. No ongoing concern.

2. **asyncio.run() in doctor_impl**: The implementation calls `asyncio.run(_check_server_session())` inside `doctor_impl`. Since `doctor_impl` is called from a synchronous typer command (no enclosing event loop), this is safe in the current context. However, if `doctor_impl` were ever called from an async context (e.g. tests using asyncio), this would raise `RuntimeError: This event loop is already running`. The current test suite avoids this because all doctor tests call `doctor_impl` synchronously. This is a latent fragility, not a current defect.

3. **No issue-matrix.md**: Not required by this mission's spec or tasks; absence is expected.

---

## FR Coverage Matrix

| FR | WP | Test File(s) | Verdict |
|----|----|--------------|---------|
| FR-001 | WP02 | `test_revoke_flow.py::test_revoke_request_shape`, `test_auth_logout.py::test_logout_success_revoked` | PASS |
| FR-002 | WP02 | `test_auth_logout.py` (5 outcome tests) | PASS |
| FR-003 | WP02 | `test_auth_logout.py::test_logout_*_still_clears_local` | PASS |
| FR-004 | WP02 | `test_revoke_flow.py::test_revoke_no_refresh_token` | PASS |
| FR-005 | WP02 | `test_revoke_flow.py::test_revoke_500` | PASS |
| FR-006 | WP03 | `test_refresh_flow.py::test_refresh_409_benign_replay_raises` | PASS (spec wording note) |
| FR-007 | WP03 | `test_stale_grant_preservation.py::test_replay_newer_persisted_retries_and_refreshes` | PASS |
| FR-008 | WP03 | `test_stale_grant_preservation.py::test_replay_same_token_returns_lock_timeout`, `test_replay_spent_token_never_resubmitted` | PASS |
| FR-009 | WP03 | `test_stale_grant_preservation.py::test_replay_retry_also_fails_returns_lock_timeout` | PASS |
| FR-010 | WP03 | `test_refresh_flow.py::test_refresh_200_captures_generation`, `test_refresh_200_missing_generation_is_none` | PASS |
| FR-011 | WP01 | `test_session.py::test_from_dict_backward_compat_no_generation` | PASS |
| FR-012 | WP02 | `test_auth_logout.py::test_logout_local_cleanup_failure_exits_1` | PASS |
| FR-013 | WP02 | `test_revoke_flow.py::test_revoke_unexpected_exception_is_server_failure` | PASS |
| FR-014 | WP04 | `test_auth_doctor_report.py::test_no_outbound_http` (via offline tests) | PASS |
| FR-015 | WP05 | `test_auth_doctor_offline.py::test_no_outbound_http`, `test_no_state_mutation_default` | PASS |
| FR-016 | WP04 | `test_auth_doctor_report.py::test_check_server_session_active`, `test_doctor_impl_server_true_renders_active` | PASS |
| FR-017 | WP04 | `test_auth_doctor_report.py::test_server_session_status_frozen` | PASS |

---

## Final Verdict

**PASS WITH NOTES**

The implementation correctly delivers all 17 functional requirements with strong test coverage. All hard gates pass. The latent `asyncio.run` fragility in `doctor_impl` is noted for awareness but is not a defect in the current test and usage context.
