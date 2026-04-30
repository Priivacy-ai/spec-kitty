---
work_package_id: WP03
title: Refresh 409 Benign Replay Handling
dependencies:
- WP02
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-012
- FR-014
- FR-015
planning_base_branch: auth-tranche-2-5-cli-contract-consumption
merge_target_branch: auth-tranche-2-5-cli-contract-consumption
branch_strategy: Planning artifacts for this feature were generated on auth-tranche-2-5-cli-contract-consumption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into auth-tranche-2-5-cli-contract-consumption unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
agent: "claude:claude-sonnet-4-6:reviewer:reviewer"
shell_pid: "33338"
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/auth/refresh_transaction.py
execution_mode: code_change
owned_files:
- src/specify_cli/auth/flows/refresh.py
- src/specify_cli/auth/refresh_transaction.py
- tests/auth/test_refresh_flow.py
- tests/auth/concurrency/test_stale_grant_preservation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Add 409 benign-replay handling to the refresh stack. The handling must be:

1. **Atomic**: inside `_run_locked`, under the existing machine-wide lock. No new `RefreshOutcome` surfaced to `token_manager`.
2. **Safe**: the spent refresh token must never be submitted a second time. Only `repersisted.refresh_token` is used for the retry.
3. **Bounded**: one retry maximum. Any failure on the second attempt returns `LOCK_TIMEOUT_ERROR`.
4. **Transparent**: `token_manager.refresh_if_needed` sees only `REFRESHED` or `LOCK_TIMEOUT_ERROR`. Its outcome-handling switch is unchanged.

Also: capture the new `generation` field from successful refresh responses in `_update_session`.

---

## Context

**Repository root**: `/Users/robert/spec-kitty-dev/spec-kitty-20260430-084609-5Y0VM4/spec-kitty`

**Read before editing**:
- `src/specify_cli/auth/flows/refresh.py` — `TokenRefreshFlow.refresh()` and `_update_session()`
- `src/specify_cli/auth/refresh_transaction.py` — `_run_locked()` with existing rejection handler
- `src/specify_cli/auth/errors.py` — `RefreshReplayError` (added in WP01)

**Server contract** (409 shape — `error` field, not `error_code`):
```json
{
  "error": "refresh_replay_benign_retry",
  "error_description": "...",
  "error_uri": "...",
  "retry_after": 0
}
```

**Critical invariant**: The comparison in the retry-decision block uses `refresh_token` only (not full `_identity_matches`). The 409 means the server already rotated the token — `session_id` is unchanged, only `refresh_token` differs in persisted state.

**Spent-token invariant**: The retry call MUST use `repersisted` as its argument, not `persisted`. This is enforced structurally: `refresh_flow.refresh(repersisted)`.

---

## Branch Strategy

- **Planning base branch**: `auth-tranche-2-5-cli-contract-consumption`
- **Merge target**: `auth-tranche-2-5-cli-contract-consumption`
- **Start command**: `spec-kitty agent action implement WP03 --agent claude`

---

## Subtask T009 — Add 409 Branch in `TokenRefreshFlow.refresh()`

**File**: `src/specify_cli/auth/flows/refresh.py`

**Purpose**: Detect `refresh_replay_benign_retry` in the HTTP response and raise `RefreshReplayError` so `_run_locked` can handle it.

**Location**: After the `if response.status_code == 200:` block and before the existing `if response.status_code in {400, 401}:` block.

**Add**:
```python
if response.status_code == 409:
    try:
        body = response.json()
    except ValueError:
        body = {}
    if body.get("error") == "refresh_replay_benign_retry":
        from ..errors import RefreshReplayError  # noqa: PLC0415
        raise RefreshReplayError(retry_after=int(body.get("retry_after", 0)))
    # Non-replay 409 (unexpected) — fall through to generic TokenRefreshError below
```

Add the import at the top of the file (not inline) if not already present — check if `RefreshReplayError` is already imported from `..errors`. If the module uses a lazy import pattern (like `TokenRefreshFlow` in `token_manager.py`), use a top-level import instead.

**Validation**:
- [ ] A mock that returns `status_code=409` with body `{"error": "refresh_replay_benign_retry", "retry_after": 2}` causes `RefreshReplayError` to be raised with `retry_after=2`.
- [ ] A 409 with a different `error` value falls through to `TokenRefreshError`.
- [ ] The 200 path is unaffected.
- [ ] The 400/401 paths are unaffected.

---

## Subtask T010 — Add `RefreshReplayError` Handler in `_run_locked`

**File**: `src/specify_cli/auth/refresh_transaction.py`

**Purpose**: When `refresh_flow.refresh(persisted)` raises `RefreshReplayError`, reload the persisted session and decide: retry with newer token, or surface `LOCK_TIMEOUT_ERROR`.

**Location**: In `_run_locked`, add an `except RefreshReplayError` clause after the existing `except (RefreshTokenExpiredError, SessionInvalidError) as exc:` block. It catches the exception from the `try: updated = await asyncio.wait_for(refresh_flow.refresh(persisted), ...)` call.

**Implementation**:

```python
    except RefreshReplayError:
        # Server says the presented token was just spent (benign network race).
        # Re-read persisted session and retry once if a newer token is available.
        repersisted = storage.read()

        if repersisted is None:
            # Session cleared concurrently; surface as retryable.
            log.warning("409 replay: session cleared concurrently; surfacing as LOCK_TIMEOUT_ERROR")
            return RefreshResult(
                outcome=RefreshOutcome.LOCK_TIMEOUT_ERROR,
                session=in_memory_session,
                network_call_made=True,
            )

        if repersisted.refresh_token == persisted.refresh_token:
            # Persisted token matches the spent one — no newer token in storage yet.
            # Do NOT retry; surfacing LOCK_TIMEOUT_ERROR signals "please retry later",
            # which is the correct caller behavior. This is NOT machine lock contention;
            # the log below distinguishes it from actual _run_locked timeout cases.
            log.warning(
                "409 replay: no newer token in storage yet; "
                "surfacing LOCK_TIMEOUT_ERROR to trigger caller retry. "
                "This is a benign replay outcome, not lock contention."
            )
            return RefreshResult(
                outcome=RefreshOutcome.LOCK_TIMEOUT_ERROR,
                session=repersisted,
                network_call_made=True,
            )

        # Persisted token differs from spent — another process already rotated it.
        # Retry ONCE with the newer token. CRITICAL: never use `persisted` here.
        try:
            updated = await asyncio.wait_for(
                refresh_flow.refresh(repersisted), timeout=max_hold_s
            )
        except Exception:
            # Catch all failures on the second attempt: TokenRefreshError and
            # subclasses (expired, session-invalid, another replay), asyncio
            # TimeoutError, httpx network errors, and anything else.
            # Any second failure surfaces as LOCK_TIMEOUT_ERROR — no third attempt.
            log.warning("409 replay: second refresh attempt also failed; surfacing LOCK_TIMEOUT_ERROR")
            return RefreshResult(
                outcome=RefreshOutcome.LOCK_TIMEOUT_ERROR,
                session=repersisted,
                network_call_made=True,
            )

        storage.write(updated)
        return RefreshResult(
            outcome=RefreshOutcome.REFRESHED,
            session=updated,
            network_call_made=True,
        )
```

Add `RefreshReplayError` to the imports at the top of `refresh_transaction.py` (it comes from `.errors`).

**Why `except Exception` on the second attempt**: The original spec listed only `(RefreshTokenExpiredError, SessionInvalidError, RefreshReplayError, TimeoutError)`, but `TokenRefreshFlow.refresh()` can also raise the `TokenRefreshError` base class directly (generic HTTP failures) and httpx network errors (`httpx.RequestError`), which are neither `TokenRefreshError` nor `TimeoutError`. A bare `except Exception` is appropriate here because we're in a bounded, already-retried code path where all failures should collapse to the same "surface as retryable" outcome. The log line distinguishes this from actual lock contention.

**Why `LOCK_TIMEOUT_ERROR` for the no-newer-token case**: `token_manager.py` is explicitly out of scope for this WP. Adding a new `RefreshOutcome` would require modifying its outcome-handling switch. `LOCK_TIMEOUT_ERROR` maps to "please retry later" semantics in `token_manager`, which is the correct caller behavior: the spent token cannot be reused, and the rotated token hasn't propagated to local storage yet. The log warning above ensures this is distinguishable from genuine lock contention in debugging.

**Validation**:
- [ ] `RefreshReplayError` is imported at the top of the file.
- [ ] The retry call uses `repersisted` not `persisted` (verify by reading the code).
- [ ] Second attempt uses `except Exception` — covers `TokenRefreshError`, httpx errors, `TimeoutError`, and further replays.
- [ ] Log warning on the no-newer-token branch contains "benign replay outcome, not lock contention".
- [ ] `token_manager.py` is NOT changed (its outcome-handling switch is sufficient).

---

## Subtask T011 — Capture `generation` in `_update_session`

**File**: `src/specify_cli/auth/flows/refresh.py`, method `TokenRefreshFlow._update_session`

**Purpose**: The Tranche 2 refresh response includes `generation: int`. Store it in `StoredSession.generation` (added in WP01).

**Change**: In `_update_session`, add `generation` to the `StoredSession(...)` constructor call:

```python
return StoredSession(
    # … existing fields …
    auth_method=session.auth_method,
    generation=tokens.get("generation"),  # ADD — None if server doesn't send it
)
```

`tokens.get("generation")` returns `None` for any server that doesn't yet return the field — correct and safe.

**Validation**:
- [ ] A mock refresh response with `"generation": 5` produces `session.generation == 5`.
- [ ] A mock refresh response without `"generation"` produces `session.generation is None`.
- [ ] The existing `_resolve_refresh_expiry` logic is unchanged.

---

## Subtask T012 — Add 409 Tests in `tests/auth/test_refresh_flow.py`

**File**: `tests/auth/test_refresh_flow.py`

**Purpose**: Verify that `TokenRefreshFlow.refresh()` raises `RefreshReplayError` on 409 with the correct error code, and falls through to `TokenRefreshError` for other 409 bodies.

**Test cases to add**:

```python
@pytest.mark.asyncio
async def test_refresh_409_benign_replay_raises(mock_httpx, session):
    """409 + {"error": "refresh_replay_benign_retry", "retry_after": 2} → RefreshReplayError(retry_after=2)."""
    # Arrange: mock POST to return 409 with benign-replay body
    # Act: flow.refresh(session)
    # Assert: raises RefreshReplayError with retry_after == 2

@pytest.mark.asyncio
async def test_refresh_409_other_error_raises_token_refresh_error(mock_httpx, session):
    """409 + {"error": "some_other_error"} → TokenRefreshError (not RefreshReplayError)."""

@pytest.mark.asyncio
async def test_refresh_200_captures_generation(mock_httpx, session):
    """200 response with generation=7 → returned StoredSession.generation == 7."""

@pytest.mark.asyncio
async def test_refresh_200_missing_generation_is_none(mock_httpx, session):
    """200 response without generation key → returned StoredSession.generation is None."""
```

**Validation**:
- [ ] `uv run pytest tests/auth/test_refresh_flow.py -v` passes all existing + new tests.

---

## Subtask T013 — Add Replay Transaction Tests

**File**: `tests/auth/concurrency/test_stale_grant_preservation.py`

**Purpose**: Add test cases specifically for the `RefreshReplayError` branch in `_run_locked`. These sit alongside the existing stale-grant-preservation tests which cover the same concurrency territory.

**Test cases to add**:

```python
@pytest.mark.asyncio
async def test_replay_newer_persisted_retries_and_refreshes(storage, in_memory_session, mock_flow):
    """
    Scenario: flow.refresh(persisted) raises RefreshReplayError.
    Persisted session has a different (newer) refresh_token.
    Expected: _run_locked retries with repersisted; returns REFRESHED.
    Verify: mock_flow.refresh was called with repersisted, NOT with persisted.
    """

@pytest.mark.asyncio
async def test_replay_same_token_returns_lock_timeout(storage, in_memory_session, mock_flow):
    """
    Scenario: flow.refresh(persisted) raises RefreshReplayError.
    Persisted session has the SAME refresh_token as persisted.
    Expected: returns LOCK_TIMEOUT_ERROR; mock_flow.refresh called exactly once.
    """

@pytest.mark.asyncio
async def test_replay_none_persisted_returns_lock_timeout(storage, in_memory_session, mock_flow):
    """
    Scenario: flow.refresh(persisted) raises RefreshReplayError.
    storage.read() returns None (session cleared concurrently).
    Expected: returns LOCK_TIMEOUT_ERROR.
    """

@pytest.mark.asyncio
async def test_replay_retry_also_fails_returns_lock_timeout(storage, in_memory_session, mock_flow):
    """
    Scenario: first call raises RefreshReplayError; second call also raises RefreshReplayError.
    Expected: returns LOCK_TIMEOUT_ERROR; no third call.
    Verify no infinite loop: mock_flow.refresh.call_count == 2.
    """

@pytest.mark.asyncio
async def test_replay_spent_token_never_resubmitted(storage, in_memory_session, mock_flow):
    """
    Critical invariant test: after a 409, the retry MUST NOT use persisted.refresh_token.
    Arrange: persisted.refresh_token = "spent"; repersisted.refresh_token = "fresh".
    Assert: the second refresh call received a session with refresh_token="fresh".
    Assert: no call ever received refresh_token="spent" after the 409.
    """
```

**Implementation note**: These tests use `run_refresh_transaction` directly (not through `TokenManager`) by injecting a mock `TokenRefreshFlow` and a fake `SecureStorage`.

**Validation**:
- [ ] `uv run pytest tests/auth/concurrency/test_stale_grant_preservation.py -v` passes all existing + new tests.
- [ ] The "spent token never resubmitted" test asserts on the actual argument passed to the second `refresh()` call.

---

## Definition of Done

- [ ] `TokenRefreshFlow.refresh()` raises `RefreshReplayError` on 409 benign-replay.
- [ ] `_run_locked` handles `RefreshReplayError`: reload → compare → one retry or LOCK_TIMEOUT_ERROR.
- [ ] The retry call uses `repersisted`, never `persisted`.
- [ ] `_update_session` captures `generation` from the response.
- [ ] `uv run pytest tests/auth/test_refresh_flow.py tests/auth/concurrency/test_stale_grant_preservation.py -v` passes.
- [ ] `token_manager.py` is NOT modified.
- [ ] No modification to files outside `owned_files`.

## Risks

| Risk | Mitigation |
|------|-----------|
| Infinite retry loop | `except RefreshReplayError` in second attempt's catch block; max one retry |
| Spent token re-submitted | Retry call uses `repersisted` object reference; structurally impossible to pass `persisted` |
| `_identity_matches` used for replay comparison | Use `refresh_token ==` only (not session_id); a 409 doesn't change session_id |
| Token manager outcome switch needs update | It doesn't — `REFRESHED` and `LOCK_TIMEOUT_ERROR` are already handled |

## Activity Log

- 2026-04-30T13:33:30Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=20876 – Started implementation via action command
- 2026-04-30T13:45:15Z – claude:claude-sonnet-4-6:reviewer:reviewer – shell_pid=33338 – Started review via action command
