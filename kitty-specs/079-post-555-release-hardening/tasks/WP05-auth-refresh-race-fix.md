---
work_package_id: WP05
title: Track 5 — Auth Refresh Race Fix
dependencies: []
requirement_refs:
- FR-401
- FR-402
- FR-403
- FR-404
- FR-405
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
shell_pid: "4240"
agent: "claude:opus:reviewer:reviewer"
history:
- at: '2026-04-09T07:30:50Z'
  event: created
authoritative_surface: src/specify_cli/sync/auth.py
execution_mode: code_change
mission_slug: 079-post-555-release-hardening
owned_files:
- src/specify_cli/sync/auth.py
- tests/sync/test_auth_concurrent_refresh.py
tags: []
---

# WP05 — Track 5: Auth Refresh Race Fix

**Spec FRs**: FR-401, FR-402, FR-403, FR-404, FR-405
**Priority**: RELEASE GATE — 3.1.1 MUST NOT ship without this fix (FR-405). Background sync remains enabled.
**Estimated size**: ~300 lines

## Objective

Extend the `filelock.FileLock` in `sync/auth.py` from per-I/O scope to the **full `refresh_tokens()` transaction**. On a 401 from the refresh endpoint, re-read on-disk credentials under the same lock before treating the failure as terminal grounds for clearing. This closes the race where two concurrent processes race a refresh, one wins (rotates the token), and the loser's 401 clears the winning process's rotated token from disk.

## Context

**Current lock contract** (from Phase 0 research):

`CredentialStore._acquire_lock()` at lines 38-40 creates `filelock.FileLock(self.lock_path, timeout=10)` (cross-process safe). The lock is currently acquired and released separately inside each of `load()`, `save()`, `clear()` — i.e., per-I/O, not per-transaction.

**Current `refresh_tokens()` shape** (lines 324-394):
```
1. get_refresh_token()         ← acquires lock, reads, releases
2. POST /token/refresh/        ← NO LOCK HELD
3. if 401: clear_credentials() ← acquires lock, deletes, releases — WITHOUT re-reading
4. if 200: save(new_tokens)    ← acquires lock, writes, releases
```

**Race**: Process A and Process B both read the same refresh token (step 1). A finishes first (step 4), rotates the token. B's refresh request is now stale, server returns 401. B clears credentials (step 3) without re-reading — wiping A's rotated token from disk.

**Correct pattern** (reference implementation in `tracker/saas_client.py:226-249`): refresh + retry within the same locked session.

**FileLock reentrancy**: `filelock.FileLock` is reentrant per-thread. Inner `load()`/`save()` calls inside the locked transaction reacquire the lock as a no-op (same thread). This is the key property that makes the fix safe.

**Background sync**: `sync/background.py` daemon thread calls `auth.get_access_token()` which may trigger `refresh_tokens()`. The cross-process file lock now correctly serializes refresh transactions across CLI processes and the background daemon.

## Branch Strategy

Plan in `main`, implement in the lane worktree. Merge back to `main` on completion.

## Subtask Guidance

### T020 — Extend `FileLock` scope in `refresh_tokens()`

**File**: `src/specify_cli/sync/auth.py`

**Steps**:

1. Find `refresh_tokens()` at lines 324-394. Its current structure (simplified):
   ```python
   def refresh_tokens(self) -> None:
       refresh_token = self.credential_store.get_refresh_token()
       if not refresh_token: return
       
       response = self.http_client.post("/api/v1/token/refresh/", ...)
       
       if response.status_code == 401:
           self.clear_credentials()
           raise AuthenticationError("Session expired...")
       
       data = response.json()
       new_access = data["access"]
       new_refresh = data["refresh"]
       self.credential_store.save(Credentials(access=new_access, refresh=new_refresh, ...))
   ```

2. Wrap the entire function body in the lock:
   ```python
   def refresh_tokens(self) -> None:
       with self.credential_store._acquire_lock():
           # Inner calls to load()/save()/clear() will reacquire the same lock
           # as a no-op (reentrancy). That's correct.
           refresh_token = self.credential_store.get_refresh_token_no_lock()
           # ... OR call the existing get_refresh_token() which reacquires under same thread
   ```

3. There are two implementation approaches:
   - **Option A (simpler)**: Call the existing `load()`, `save()`, `clear()` methods inside the lock. Since FileLock is reentrant per-thread, the inner acquisitions are no-ops. The existing methods don't need to change.
   - **Option B (explicit)**: Create `_no_lock` variants of `load()`, `save()`, `clear()` that skip the lock acquisition, and call those inside the already-locked block.

   **Recommended: Option A.** It requires the least code change and relies on the documented reentrancy of `filelock.FileLock`. Add a comment explaining the reentrancy assumption so reviewers understand it.

4. New structure:
   ```python
   def refresh_tokens(self) -> None:
       # Acquire the lock for the FULL transaction (read → network → persist).
       # Inner load()/save()/clear() calls reacquire the same lock as no-ops
       # (filelock.FileLock is reentrant per thread). See FR-401.
       with self.credential_store._acquire_lock():
           refresh_token = self.credential_store.get_refresh_token()  # reacquires: no-op
           if not refresh_token:
               return
           
           entry_refresh_token = refresh_token  # capture for stale-401 check (T021)
           
           response = self.http_client.post("/api/v1/token/refresh/", ...)
           
           if response.status_code == 401:
               # T021 handles this branch (re-read-on-401)
               ...
           
           data = response.json()
           new_access = data["access"]
           new_refresh = data["refresh"]
           self.credential_store.save(Credentials(...))  # reacquires: no-op
   ```

**Validation**:
- After the change, the lock is held from function entry to function exit.
- Inner `load()`/`save()` calls do not raise (reentrancy confirmed).

---

### T021 — Re-read-on-401 path

**File**: `src/specify_cli/sync/auth.py`

**Steps**:

This subtask implements the stale-401 detection inside the lock (inside T020's `with` block).

**Current code** (simplified):
```python
if response.status_code == 401:
    self.clear_credentials()
    raise AuthenticationError("Session expired. Please log in again.")
```

**New code**:
```python
if response.status_code == 401:
    # Re-read credentials under the same lock.
    # If the refresh token has changed since we started this transaction,
    # another process already refreshed successfully — our 401 is stale.
    # Exit cleanly without clearing. See FR-402.
    current_creds = self.credential_store.load()  # reacquires lock as no-op
    if current_creds is not None and current_creds.refresh != entry_refresh_token:
        # Stale 401: another process rotated the token. We can exit without clearing.
        return  # Caller should retry get_access_token() which will use the new token.
    
    # Real 401: the token we held is still on disk and the server rejected it.
    # Clear under lock (the lock is already held). See FR-403.
    self.credential_store.clear()  # reacquires lock as no-op
    raise AuthenticationError("Session expired. Please log in again.")
```

**Key detail**: `entry_refresh_token` must be captured at the start of the transaction (before the network call), then compared after the 401. This is done in T020's refactor.

**Edge cases**:
- `current_creds is None` (credentials file was deleted by another party): treat as a real 401 (no credentials to protect), proceed to clear and raise.
- `entry_refresh_token is None` (called without a valid refresh token): guard at function entry (existing behavior), return early.

**Validation**:
- Race simulation (T023): two threads, one rotates successfully, other gets 401. The 401 thread detects the rotation and exits cleanly (no clear).
- Single-thread 401 (T023): one thread, server returns 401, on-disk token is unchanged → clear credentials.

---

### T022 — Verify httpx timeout < lock timeout

**File**: `src/specify_cli/sync/auth.py`

**Purpose**: Holding the `FileLock` during the HTTP POST creates a worst-case latency of "HTTP request timeout". If the HTTP client has no timeout, a hung server request would hold the lock indefinitely, deadlocking other CLI invocations.

**Steps**:

1. Find where the httpx client is configured in `refresh_tokens()` or in `AuthClient.__init__()`. Check if there is an explicit `timeout=` parameter.

2. If there is NO explicit timeout on the HTTP call, add one:
   ```python
   response = self.http_client.post(
       "/api/v1/token/refresh/",
       json={"refresh": refresh_token},
       timeout=8.0,  # Must be < FileLock timeout (10s) to prevent deadlock. See FR-401.
   )
   ```

3. If there IS already an explicit timeout, verify it is < 10s. If it's >= 10s, reduce it to 8s and add the comment.

4. Add a `# INVARIANT: HTTP timeout (N s) < FileLock timeout (10 s) — prevents deadlock` comment.

**Validation**:
- The httpx call in `refresh_tokens()` has an explicit timeout ≤ 8s.
- The comment is present.

---

### T023 — Regression tests for Track 5

**File**: `tests/sync/test_auth_concurrent_refresh.py` (new file)

**Test T5.1 — Lock is held for the full transaction**:
```python
def test_refresh_lock_held_during_network_call(monkeypatch):
    """Verify the FileLock is held while the HTTP POST is in flight."""
    import threading
    
    lock_held_during_call = threading.Event()
    
    def mock_post(*args, **kwargs):
        # While "in the network call", try to acquire the lock from another thread.
        # It should block (lock is held).
        lock_acquired = threading.Event()
        
        def try_acquire():
            try:
                with auth_client.credential_store._acquire_lock():
                    lock_acquired.set()
            except filelock.Timeout:
                pass
        
        t = threading.Thread(target=try_acquire)
        t.start()
        # Give the other thread time to try to acquire
        time.sleep(0.1)
        # The other thread should NOT have acquired the lock yet
        assert not lock_acquired.is_set(), "Lock was not held during network call"
        lock_held_during_call.set()
        return MockResponse(200, {"access": "new-access", "refresh": "new-refresh", ...})
    
    monkeypatch.setattr(auth_client.http_client, "post", mock_post)
    auth_client.refresh_tokens()
    assert lock_held_during_call.is_set()
```

**Test T5.2 — Stale 401 does NOT clear credentials** (the main race):
```python
def test_stale_401_does_not_clear_credentials(tmp_path, monkeypatch):
    """Two concurrent refresh attempts: one rotates the token, other gets stale 401.
    The stale 401 must NOT clear credentials."""
    
    # Setup: store credentials with refresh token "original-refresh"
    store = CredentialStore(tmp_path / "creds")
    store.save(Credentials(refresh="original-refresh", access="access", ...))
    auth_client = AuthClient(credential_store=store, ...)
    
    call_count = 0
    
    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: success, rotates refresh token on disk
            store.save(Credentials(refresh="rotated-refresh", access="new-access", ...))
            return MockResponse(200, {"access": "new-access", "refresh": "rotated-refresh", ...})
        else:
            # Second call: stale 401 (uses the old "original-refresh")
            return MockResponse(401, {})
    
    monkeypatch.setattr(auth_client.http_client, "post", mock_post)
    
    # Simulate: second call uses old refresh token (reads "original-refresh" at entry)
    # but by the time 401 arrives, disk has "rotated-refresh"
    # Result: stale 401 should exit cleanly without clearing
    
    # This test may need careful threading or mocking to simulate the race precisely.
    # Acceptable: patch `get_refresh_token` to return "original-refresh" on entry,
    # but `load()` after 401 to return credentials with "rotated-refresh".
    
    # After the call:
    current_creds = store.load()
    assert current_creds is not None, "Credentials must not be cleared by a stale 401"
    assert current_creds.refresh == "rotated-refresh"
```

**Test T5.3 — Real 401 DOES clear credentials**:
```python
def test_real_401_clears_credentials(tmp_path, monkeypatch):
    """Non-stale 401: on-disk token unchanged → credentials cleared."""
    
    store = CredentialStore(tmp_path / "creds")
    store.save(Credentials(refresh="my-refresh", access="my-access", ...))
    auth_client = AuthClient(credential_store=store, ...)
    
    def mock_post(*args, **kwargs):
        # 401, and disk still has "my-refresh" (no concurrent rotation)
        return MockResponse(401, {})
    
    monkeypatch.setattr(auth_client.http_client, "post", mock_post)
    
    with pytest.raises(AuthenticationError):
        auth_client.refresh_tokens()
    
    # Credentials should be cleared
    assert store.load() is None
```

**Test T5.4 — Reentrancy: inner load()/save() don't deadlock**:
```python
def test_inner_lock_reacquisition_is_no_op(tmp_path, monkeypatch):
    """Verify that load()/save() inside the locked refresh_tokens() don't deadlock."""
    
    store = CredentialStore(tmp_path / "creds")
    store.save(Credentials(refresh="good-refresh", access="access", ...))
    auth_client = AuthClient(credential_store=store, ...)
    
    def mock_post(*args, **kwargs):
        return MockResponse(200, {"access": "new-access", "refresh": "new-refresh", ...})
    
    monkeypatch.setattr(auth_client.http_client, "post", mock_post)
    
    # Should complete without deadlock
    auth_client.refresh_tokens()
    
    # Credentials should be updated
    creds = store.load()
    assert creds.access == "new-access"
    assert creds.refresh == "new-refresh"
```

## Definition of Done

- [ ] `refresh_tokens()` acquires `FileLock` at entry and releases in `finally`.
- [ ] The HTTP POST occurs inside the held lock.
- [ ] On 401: on-disk credentials are re-read; if token has rotated (stale 401), exits cleanly without clearing.
- [ ] On 401: if token is unchanged (real 401), clears credentials and raises `AuthenticationError`.
- [ ] httpx timeout in `refresh_tokens()` is ≤ 8s (confirmed with comment).
- [ ] All 4 regression tests (T5.1–T5.4) pass deterministically (run 5 times without flake).
- [ ] `mypy --strict src/specify_cli/sync/auth.py` clean.
- [ ] Existing `tests/sync/test_auth.py` tests still pass.

## Risks

| Risk | Mitigation |
|------|-----------|
| `filelock.FileLock` reentrancy assumption is wrong for this library version | Add T5.4 specifically to verify reentrancy. If it fails (deadlock), switch to Option B from T020 (explicit `_no_lock` variants). |
| The test (T5.2) is timing-dependent | Use mocking + monkeypatching rather than real threading sleeps. Simulate the race through function patching, not timing. |
| httpx client is async | If the client uses `asyncio`, `filelock.FileLock` works in a thread but not as an `async with`. Check if `auth.py` is sync or async and adapt accordingly (use `AsyncFileLock` if needed). |

## Reviewer Guidance

1. Confirm the `with self.credential_store._acquire_lock():` wraps the ENTIRE function body, including the HTTP call.
2. Run the T5.3 (real 401) and T5.2 (stale 401) tests — these are the most critical behavioral tests.
3. Confirm: if a hung HTTP request causes the lock to be held for > 10s, it will timeout with `filelock.Timeout`. That is acceptable — it surfaces as an error rather than a deadlock.
4. Existing `tests/sync/test_auth.py` must pass unchanged.

## Activity Log

- 2026-04-09T09:00:07Z – unknown – shell_pid=114 – Dispatching implementation
- 2026-04-09T09:09:50Z – unknown – shell_pid=114 – FileLock covers full refresh transaction via cached lock object (reentrancy), stale-401 handled with re-read-on-401 pattern, 7 new concurrent tests pass 5/5 runs without flake
- 2026-04-09T09:10:00Z – claude:opus:reviewer:reviewer – shell_pid=4240 – Started review via action command
