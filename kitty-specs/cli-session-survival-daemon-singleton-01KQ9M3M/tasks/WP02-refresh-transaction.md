---
work_package_id: WP02
title: Refresh transaction with stale-grant preservation
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-019
- FR-020
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-28T09:17:32+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
history:
- at: '2026-04-28T09:17:32Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
mission_slug: cli-session-survival-daemon-singleton-01KQ9M3M
owned_files:
- src/specify_cli/auth/refresh_transaction.py
- src/specify_cli/auth/token_manager.py
- tests/auth/test_token_manager.py
priority: P1
status: planned
tags: []
agent_profile: python-pedro
role: implementer
agent: claude
---

# WP02 — Refresh transaction with stale-grant preservation

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned agent profile via `/ad-hoc-profile-load <agent_profile>`. Profile-load must complete before any tool call against this repository.

## Objective

Build `src/specify_cli/auth/refresh_transaction.py` and rewire `TokenManager.refresh_if_needed` to delegate through it. The transaction is a bounded read-decide-refresh-reconcile sequence inside a `MachineFileLock` (WP01). It reloads persisted material before deciding (so two concurrent callers don't both refresh), and on any `invalid_grant` / `session_invalid` rejection it reloads again to distinguish stale-token rejection (preserve the local session) from current-token rejection (clear the session and tell the user how to re-login). This WP is **the actual incident fix**.

## Context

Today, `TokenManager.refresh_if_needed` calls `self.clear_session()` directly inside the `except RefreshTokenExpiredError` and `except SessionInvalidError` branches. With multiple processes, this is the bug: process A rotates → process B uses A's now-rotated-out refresh token → server replies `invalid_grant` → B clears the shared session, silently logging the user out. The fix is to make the `clear_session()` call conditional on the rejected material still being current persisted material.

**Key spec references** (see `spec.md`):
- FR-002: refresh runs as one bounded transaction (acquire → reload → decide → refresh → persist → reconcile).
- FR-003: keep the in-process `asyncio.Lock` single-flight as a fast path; do NOT rely on it cross-process.
- FR-004: when reloaded persisted is newer-and-valid, adopt and skip the network call.
- FR-005: rejection of current material clears local session.
- FR-006: rejection of stale material preserves local session.
- FR-007: on clear, surface a single user-readable message naming the recovery command.
- FR-016/FR-017: bounded lock-hold; lock-timeout adoption.
- FR-019: log every `RefreshOutcome` at INFO.
- FR-020: `auth status` output unchanged for the single-process happy path (golden test).
- NFR-001: ≤ 50 ms p95 overhead on the single-process happy path.

**Key planning references**:
- `research.md` D4 (identity comparison), D5 (RefreshOutcome state machine), D11 (mypy posture).
- `contracts/refresh-lock.md` (the lock contract WP01 ships).
- `data-model.md` §"AuthSession" identity rule: two sessions are "the same material" iff `(session_id, refresh_token)` are byte-equal.

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP02`. WP02 depends on WP01, so the resolver may rebase WP02 onto WP01's lane head before opening the worktree.

To start work:
```bash
spec-kitty implement WP02
```

## Subtasks

### T006 — `refresh_transaction.py` skeleton + `RefreshOutcome` enum

**Purpose**: Lay down the new module's contract: the public function, the outcome enum, and the data shape that `TokenManager` will consume.

**Files to create**: `src/specify_cli/auth/refresh_transaction.py`.

**Steps**:
1. Module docstring stating purpose, the bounded transaction model, and the FR-005/FR-006 invariant.
2. Define `class RefreshOutcome(str, Enum)` with members:
   - `ADOPTED_NEWER`
   - `REFRESHED`
   - `STALE_REJECTION_PRESERVED`
   - `CURRENT_REJECTION_CLEARED`
   - `LOCK_TIMEOUT_ADOPTED`
   - `LOCK_TIMEOUT_ERROR`
3. Define `@dataclass(frozen=True) class RefreshResult` with fields: `outcome: RefreshOutcome`, `session: StoredSession | None`, `network_call_made: bool`.
4. Define the public coroutine signature:
   ```python
   async def run_refresh_transaction(
       *,
       storage: SecureStorage,
       in_memory_session: StoredSession,
       refresh_flow: TokenRefreshFlow,
       lock_path: Path,
       max_hold_s: float = 10.0,
   ) -> RefreshResult: ...
   ```
   Body raises `NotImplementedError("WP02 T007")`.

**Validation**: `python -c "from specify_cli.auth.refresh_transaction import run_refresh_transaction, RefreshOutcome, RefreshResult"` succeeds.

### T007 — Reload-before-refresh + lock-timeout branches

**Purpose**: Implement the happy path and the lock-acquisition failure paths. Network refresh is wrapped in `asyncio.wait_for(..., timeout=max_hold_s)` so NFR-002's 10 s ceiling is hard-enforced.

**Steps**:
1. Inside `run_refresh_transaction`, wrap the body in `try: async with MachineFileLock(lock_path, max_hold_s=max_hold_s, acquire_timeout_s=max_hold_s) as _lock_record:`.
2. Inside the lock:
   - `persisted = storage.read()` (reload).
   - Identity-compare with `in_memory_session` using `(session_id, refresh_token)` byte equality.
   - If `persisted` differs AND `persisted.is_access_token_expired(buffer_seconds=5)` is False: return `RefreshResult(ADOPTED_NEWER, persisted, network_call_made=False)`.
   - Otherwise: call `await asyncio.wait_for(refresh_flow.refresh(persisted), timeout=max_hold_s)`. On success: `storage.write(updated)`. Return `RefreshResult(REFRESHED, updated, True)`.
3. On `LockAcquireTimeout` (from WP01): re-read `storage.read()` after the lock-wait. If the persisted token is non-expired: return `RefreshResult(LOCK_TIMEOUT_ADOPTED, persisted, False)`. Otherwise: return `RefreshResult(LOCK_TIMEOUT_ERROR, in_memory_session, False)` (the caller will raise/retry — see T009/T010).
4. On `asyncio.TimeoutError` from the network call: lock is released by the context manager; return `RefreshResult(LOCK_TIMEOUT_ERROR, in_memory_session, False)` (semantically a retryable error). Caller raises a network-timeout exception in T010.

**Files**: `src/specify_cli/auth/refresh_transaction.py`.

**Validation**: unit tests in `tests/auth/test_token_manager.py` (T011) cover each branch in isolation with a mock `refresh_flow` and a tmp-rooted lock path.

**Edge cases**: When persisted material is `None` (storage empty mid-transaction), treat as `LOCK_TIMEOUT_ERROR` and let the caller surface re-login required. Do NOT silently re-login.

### T008 — Stale-grant reconciler

**Purpose**: The actual incident fix. Wrap the network refresh in `try/except` for `RefreshTokenExpiredError` and `SessionInvalidError`. On rejection, **reload storage again** and compare the rejected refresh token to the now-persisted refresh token. If different ⇒ `STALE_REJECTION_PRESERVED`. If same ⇒ `CURRENT_REJECTION_CLEARED` and propagate the exception so the caller surfaces re-login required.

**Steps**:
1. Wrap the `await refresh_flow.refresh(persisted)` call in:
   ```python
   try:
       updated = await asyncio.wait_for(refresh_flow.refresh(persisted), timeout=max_hold_s)
   except (RefreshTokenExpiredError, SessionInvalidError) as exc:
       repersisted = storage.read()
       rejected_was_current = (
           repersisted is not None
           and repersisted.session_id == persisted.session_id
           and repersisted.refresh_token == persisted.refresh_token
       )
       if rejected_was_current:
           storage.delete()
           return RefreshResult(CURRENT_REJECTION_CLEARED, None, network_call_made=True)
       else:
           return RefreshResult(STALE_REJECTION_PRESERVED, repersisted, network_call_made=True)
   ```
2. Document the `(session_id, refresh_token)` identity rule with a code comment referencing `data-model.md` §"AuthSession".
3. Confirm the `storage.delete()` call happens ONLY in the `rejected_was_current` branch — that's the entire bug fix in two lines plus a guard.

**Files**: `src/specify_cli/auth/refresh_transaction.py`.

**Validation**: targeted unit tests in WP03 (T013) drive both branches deterministically. WP02-internal tests (T011) cover the same logic with mock storage and mock refresh_flow.

### T009 — User-readable re-login message

**Purpose**: When the local session is cleared (FR-007), the user must see ONE message that names the cause and the recovery command. Avoid stack traces. The wording is part of the contract for SC-003.

**Steps**:
1. In `refresh_transaction.py`, define `class CurrentSessionRejectedError(Exception)` with attributes `cause: Literal["refresh_token_expired", "session_invalid"]` and a `recovery_command: str = "spec-kitty auth login"`.
2. In `run_refresh_transaction` `CURRENT_REJECTION_CLEARED` branch, instead of returning the result directly, raise `CurrentSessionRejectedError(cause=...)` BEFORE returning. The `RefreshResult` is still returned via the exception's `__cause__` if needed; the caller catches and surfaces the message.
3. Re-export `CurrentSessionRejectedError` from `specify_cli.auth` package for callers.

Actually — after re-thinking: cleaner to keep `RefreshResult.outcome == CURRENT_REJECTION_CLEARED` as the signal AND raise the existing `RefreshTokenExpiredError`/`SessionInvalidError` from the caller (`TokenManager`) so existing test expectations don't churn. Implement this:

- `run_refresh_transaction` returns the `RefreshResult` (no new exception type needed).
- `TokenManager.refresh_if_needed` (T010) re-raises `RefreshTokenExpiredError` or `SessionInvalidError` after observing the outcome.

**Files**: `src/specify_cli/auth/refresh_transaction.py`.

**Validation**: T011 asserts the message in stderr matches the expected single line (e.g. "Session expired. Run `spec-kitty auth login` to re-authenticate.").

### T010 — `TokenManager.refresh_if_needed` delegates to the transaction

**Purpose**: Wire the new transaction module into `TokenManager`. Preserve the existing `asyncio.Lock` (FR-003) as the same-process fast path so multiple async callers in one process still produce one transaction. Add INFO logs per outcome (FR-019).

**Steps**:
1. In `src/specify_cli/auth/token_manager.py`, add module-level constant `_REFRESH_LOCK_PATH = Path.home() / ".spec-kitty" / "auth" / "refresh.lock"` (or, for Windows, route via the existing `RuntimeRoot` helper if applicable — match `_daemon_root()` style).
2. In `refresh_if_needed`, after the existing `asyncio.Lock` is acquired:
   - Replace the inline `clear_session()` paths with a call to `await run_refresh_transaction(storage=self._storage, in_memory_session=self._session, refresh_flow=flow, lock_path=_REFRESH_LOCK_PATH, max_hold_s=10.0)`.
   - Inspect `result.outcome`:
     - `ADOPTED_NEWER` / `REFRESHED` / `LOCK_TIMEOUT_ADOPTED`: set `self._session = result.session`, return `True` (refreshed) for `REFRESHED` and `False` otherwise.
     - `STALE_REJECTION_PRESERVED`: set `self._session = result.session` (the freshly persisted material), return `False`. **Do NOT clear**.
     - `CURRENT_REJECTION_CLEARED`: set `self._session = None`, raise the original exception (`RefreshTokenExpiredError` or `SessionInvalidError`) — the caller pattern at `auth/transport.py` is unchanged.
     - `LOCK_TIMEOUT_ERROR`: raise a new `RefreshLockTimeoutError(Exception)` with the recovery hint "another spec-kitty process is refreshing; retry in a moment".
3. Add `logger.info("refresh_transaction outcome=%s network_call=%s", result.outcome, result.network_call_made)` at the end of every transaction (FR-019).
4. Preserve the lazy-import of `TokenRefreshFlow` (existing pattern at `token_manager.py:160`).

**Files**: `src/specify_cli/auth/token_manager.py`.

**Validation**: existing `tests/auth/test_token_manager.py` cases pass without modification (FR-020 — single-process behavior unchanged); golden output for `auth status` unchanged.

**Edge cases**: When `self._session is None` going into `refresh_if_needed`, raise `NotAuthenticatedError` immediately (existing behavior; do not enter the transaction).

### T011 — Extend `tests/auth/test_token_manager.py` with new-flow coverage

**Purpose**: Cover every `RefreshOutcome` branch from inside `TokenManager` (with the storage and refresh_flow mocked). Concurrency tests (cross-process) live in WP03; this WP keeps its tests in-process.

**Steps**:
1. Add `test_adopts_newer_persisted_material_skips_network` — pre-write a newer-and-valid session to `tmp_path` storage; assert `refresh_flow.refresh` is never called and `_session` updates to the persisted version.
2. Add `test_stale_grant_preserves_session` — mock `refresh_flow.refresh` to raise `RefreshTokenExpiredError`; mid-test, write a different `refresh_token` to storage; assert no `clear_session` call and `_session.refresh_token` matches the freshly-persisted token.
3. Add `test_current_grant_rejection_clears_and_propagates` — mock raises `RefreshTokenExpiredError`; storage's refresh_token unchanged; assert `_session is None` and the exception propagates.
4. Add `test_lock_timeout_adopted` — patch `MachineFileLock` to raise `LockAcquireTimeout` immediately; pre-write a non-expired session to storage; assert outcome adopts and no exception.
5. Add `test_lock_timeout_error_raises` — patch `MachineFileLock` to raise `LockAcquireTimeout`; storage session is expired; assert `RefreshLockTimeoutError` raised.
6. Add `test_refresh_logs_outcome_at_info` — capture `caplog`; assert one INFO line per outcome.
7. Update existing tests: ensure the `clear_session` patch points stay valid (they should; the public surface is unchanged).
8. **Golden FR-020 test**: capture output of `spec-kitty auth status` (via `CliRunner`) for an authenticated session; assert byte-equal to a fixture string. Place fixture inline.

**Files**: `tests/auth/test_token_manager.py` (extended in place).

**Validation**: `pytest tests/auth/test_token_manager.py -v` passes; `coverage` ≥ 90 % for `auth/refresh_transaction.py` and `auth/token_manager.py`.

## Definition of Done

- All 6 subtasks complete.
- `mypy --strict` zero errors on `auth/refresh_transaction.py` and `auth/token_manager.py`.
- `ruff check` clean.
- Coverage ≥ 90 % on new and modified code.
- Existing single-process tests in `test_token_manager.py` still pass without modification of pre-existing cases (FR-020 byte-equal).
- INFO logs fire once per outcome (verified by `caplog`).
- No changes to `auth/secure_storage/`, `auth/flows/refresh.py`, or `auth/transport.py`.

## Risks

- **R1** — refresh hold exceeds 10 s under slow network. Counter: `asyncio.wait_for(..., timeout=max_hold_s)` wrapping the network call.
- **R2** — process killed mid-transaction. Counter: WP01 lock is age-stale-able; another process adopts after 60 s.
- **NFR-001** (50 ms p95): the lock acquire fast-path (uncontended) is one `flock` syscall + one `atomic_write`. Verify on the maintainer's reference machine.

## Reviewer Guidance

Verify:
1. `storage.delete()` is called ONLY in the `CURRENT_REJECTION_CLEARED` branch — that's the bug fix.
2. The identity check uses both `session_id` AND `refresh_token`; both must be equal.
3. The in-process `asyncio.Lock` is still acquired before the machine-wide lock (FR-003).
4. INFO logs fire on every outcome (FR-019).
5. `auth status` output is byte-equal to the pre-WP02 golden fixture (FR-020).
6. No code path can clear a newer persisted session.
