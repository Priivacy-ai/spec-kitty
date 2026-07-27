---
work_package_id: WP02
title: TokenManager Rehydrate Orchestrator + me_fetch Helper + Refresh Hook
dependencies: []
requirement_refs:
- FR-003
- FR-008
- FR-011
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-05-01T06:33:00+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
agent: "codex:gpt-5:reviewer-renata:reviewer"
shell_pid: "95248"
history:
- date: '2026-05-01'
  author: spec-kitty.tasks
  note: Initial WP generated
- date: '2026-05-01'
  author: spec-kitty.analyze
  note: Reworked to sync model (threading.Lock + sync HTTP) so call sites in batch.py/queue.py/emitter.py can call without event-loop bridging. Refresh hook moved into TokenManager.refresh_if_needed() and is now a WP02 subtask (T011), since flows/refresh.py is not the adoption boundary. default_team_id recomputed via pick_default_team_id() on rehydrate. Cache bust unconditional in set_session().
agent_profile: python-pedro
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/http/me_fetch.py
- src/specify_cli/auth/token_manager.py
- tests/auth/test_me_fetch.py
- tests/auth/test_token_manager.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the assigned agent profile so your behavior, tone, and boundaries match what this work package expects:

```
/ad-hoc-profile-load python-pedro
```

This sets your role to `implementer`, scopes your editing surface to the `owned_files` declared in the frontmatter above, and applies the Python-specialist authoring standards. Do not skip this step.

## Objective

Add three pieces to `TokenManager`, all working together as a sync recovery engine:

1. **`auth/http/me_fetch.py`** (new): a tiny **sync** helper `fetch_me_payload(saas_base_url, access_token) -> dict` that issues `GET /api/v1/me` via the existing sync HTTP entry point.
2. **`TokenManager.rehydrate_membership_if_needed(*, force=False) -> bool`** (sync): a one-shot rehydrate orchestrator with `threading.Lock` single-flight + process-lifetime negative cache. Recomputes `default_team_id` from the fresh teams list via `pick_default_team_id()`. Persists via the existing `set_session()`.
3. **Post-refresh hook in `TokenManager.refresh_if_needed()`** (existing async method, modified): after each `self._session = result.session` adoption point, when the adopted session lacks a Private Teamspace, call `self.rehydrate_membership_if_needed(force=True)`.

`set_session()` also gains an unconditional cache reset.

This WP is the recovery engine. Call sites in `sync/` (WP04, WP05) call `rehydrate_membership_if_needed()` synchronously. WP03 owns the integration tests for the refresh hook delivered here in T011.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP02 --agent <name>`; do not guess the worktree path

## Context

### Why this is sync (not async)

Direct-ingress call sites in `sync/batch.py`, `sync/queue.py`, and `sync/emitter.py` are sync — `def batch_sync(...)` at `sync/batch.py:331` uses `requests`/`httpx` synchronously, and `_current_team_slug()` at `sync/batch.py:42` is also sync. An `asyncio.Lock` cannot be acquired from a sync function without re-entering the event loop. Therefore:

- `rehydrate_membership_if_needed` is sync, protected by a new `threading.Lock`.
- `me_fetch.fetch_me_payload` is sync, using `request_with_fallback_sync(...)` from `src/specify_cli/auth/http/transport.py:377`.
- The websocket call site (`client.py`) is inside an async function but invokes the sync helper inline — no `await`, no event-loop bridging.
- The existing `asyncio.Lock` on `TokenManager` continues to protect the OAuth refresh flow only. The two locks protect different state.

### Why the refresh hook lives here

`TokenRefreshFlow.refresh(session)` in `auth/flows/refresh.py:56` only returns a fresh `StoredSession` — it does not adopt or persist. Adoption happens inside `TokenManager.refresh_if_needed()` at `auth/token_manager.py:171`, where `self._session = result.session` is assigned for each `RefreshOutcome` (REFRESHED, ADOPTED_NEWER, LOCK_TIMEOUT_ADOPTED, STALE_REJECTION_PRESERVED). The hook must run there because that is the only place where the just-adopted session is in scope for a sync `rehydrate_membership_if_needed(force=True)` call. T011 wires this in.

### Existing code surface

- `auth/token_manager.py:83+` — `class TokenManager` constructed with `SecureStorage`. It already owns:
  - `_get_lock()` (an `asyncio.Lock` initializer at line 90, reused for OAuth refresh)
  - `set_session(session)` (line 116, persists via `SecureStorage`)
  - `get_current_session()` (line 130)
  - `refresh_if_needed()` (line 171, async, calls `run_refresh_transaction` and adopts)
- `auth/flows/authorization_code.py:245+` and `device_code.py:252+` already call `GET /api/v1/me` (async) during login. We do **not** modify those — the new `me_fetch.py` is a sync helper used only by the rehydrate path.
- `auth/flows/authorization_code.py:281` shows how login derives `default_team_id`: `default_team_id = pick_default_team_id(teams)`. Comment at line 239 confirms the SaaS does NOT return `default_team_id` in `/api/v1/me`. The rehydrate path mirrors this.
- `auth/http/transport.py:377` exposes the sync entry point: `def request_with_fallback_sync(method: str, url: str, *, timeout: float = ..., client: httpx.Client | None = None, **kwargs: Any) -> httpx.Response`. Use it.

### Spec & contract references

- `spec.md` — FR-003, FR-008, FR-011, NFR-001, Scenarios 2, 3, 5
- `contracts/api.md` §2 (me_fetch), §3 (rehydrate orchestrator + set_session contract addition), §6 (refresh integration)
- `data-model.md` — negative-cache lifecycle, rehydrate-outcome shape
- `plan.md` §1.3, §1.6

## Scope guardrail (binding)

This WP MUST NOT:

- Touch any file in `src/specify_cli/sync/` or `src/specify_cli/auth/flows/`.
- Modify `pick_default_team_id` or `get_private_team_id` (WP01 / existing code).
- Introduce a new HTTP client; reuse `request_with_fallback_sync`.
- Persist the negative cache to disk — it is process-scoped only.
- Use `OAuthHttpClient` from inside `rehydrate_membership_if_needed` (would re-enter `TokenManager` and deadlock).
- Acquire the existing `asyncio.Lock` from a sync code path.

This WP MUST:

- Keep `mypy --strict` green for all touched files.
- Maintain ≥ 90% line coverage on new code.

## Subtasks

### T005 — Create `auth/http/me_fetch.py` with sync `fetch_me_payload`

**Purpose**: Tiny, sync, no-state-mutation helper for `GET /api/v1/me`. Lifts the HTTP shape into a single seam so the orchestrator (T006) can be unit-tested without an HTTP server.

**Steps**:

1. Create `src/specify_cli/auth/http/me_fetch.py`:

   ```python
   """Sync GET /api/v1/me — used by TokenManager.rehydrate_membership_if_needed.

   Intentionally tiny: no state mutation, no caching, no logging. Sync so it can be
   called from sync direct-ingress paths (batch.py, queue.py, emitter.py) without
   event-loop bridging. See contracts/api.md §2.
   """

   from __future__ import annotations

   from typing import Any

   from .transport import request_with_fallback_sync


   def fetch_me_payload(saas_base_url: str, access_token: str) -> dict[str, Any]:
       """GET <saas_base_url>/api/v1/me with Bearer <access_token>.

       Issues exactly one HTTP GET. No retries inside this function (the underlying
       request_with_fallback_sync handles transport-layer fallback once).

       Raises httpx.HTTPStatusError on non-2xx (caller decides how to handle).
       Returns the parsed JSON dict. Caller is responsible for extracting teams[].
       """
       url = saas_base_url.rstrip("/") + "/api/v1/me"
       response = request_with_fallback_sync(
           method="GET",
           url=url,
           headers={"Authorization": f"Bearer {access_token}"},
       )
       response.raise_for_status()
       return response.json()
   ```

2. Do **not** import `OAuthHttpClient` here — it would create a circular dependency on `TokenManager` if used during rehydrate.

**Files**:

- `src/specify_cli/auth/http/me_fetch.py` (new file, ~25 LOC).

**Validation**:

- [ ] Module imports cleanly: `python -c "from specify_cli.auth.http.me_fetch import fetch_me_payload"`.
- [ ] No state mutation, no logging, no print, no `OAuthHttpClient` import.
- [ ] `mypy --strict src/specify_cli/auth/http/me_fetch.py` passes.

---

### T006 — Add `_membership_negative_cache`, `_membership_lock`, and sync `rehydrate_membership_if_needed` to `TokenManager`

**Purpose**: The orchestration layer combining (a) early-return when private team already present, (b) negative-cache fast-path, (c) single-flight via a `threading.Lock`, (d) the `me_fetch` GET, and (e) `set_session` persistence with `default_team_id` recomputed.

**Steps**:

1. Add imports at the top of `src/specify_cli/auth/token_manager.py`:

   ```python
   import threading

   from .http.me_fetch import fetch_me_payload
   from .session import StoredSession, Team, get_private_team_id, pick_default_team_id
   ```

   Adjust to match what's already imported. `dataclasses.replace` from stdlib is also helpful (see step 4).

2. In `TokenManager.__init__` (currently line 83), after the existing field initializations, add:

   ```python
   self._membership_negative_cache: bool = False
   self._membership_lock: threading.Lock = threading.Lock()
   ```

3. Add the new sync method (place it near `refresh_if_needed` for locality):

   ```python
   def rehydrate_membership_if_needed(self, *, force: bool = False) -> bool:
       """Sync one-shot /api/v1/me rehydrate. Return True iff session now has a private team.

       See contracts/api.md §3 for the full contract.
       """
       with self._membership_lock:
           session = self._session
           if session is None:
               return False
           if get_private_team_id(session.teams) is not None:
               return True
           if self._membership_negative_cache and not force:
               return False

           try:
               payload = fetch_me_payload(self._saas_base_url, session.access_token)
           except Exception as exc:  # noqa: BLE001 — explicit "log and skip" boundary
               import logging
               logging.getLogger(__name__).warning(
                   "rehydrate_membership_if_needed: /api/v1/me fetch failed: %s",
                   exc,
               )
               return False

           teams = [Team.from_dict(t) for t in payload.get("teams", [])]
           if get_private_team_id(teams) is None:
               self._membership_negative_cache = True
               return False

           # Recompute default_team_id from fresh teams (mirrors auth login at
           # auth/flows/authorization_code.py:281; SaaS does NOT return this field).
           new_default_team_id = pick_default_team_id(teams)
           new_session = dataclasses.replace(
               session,
               teams=teams,
               default_team_id=new_default_team_id,
           )
           self.set_session(new_session)  # set_session also clears the negative cache (T007)
           return True
   ```

4. Notes:
   - `self._saas_base_url` may not exist yet. If `TokenManager` doesn't currently hold the SaaS base URL, thread it in via the constructor (`__init__(self, storage, saas_base_url)`) and update existing call sites that construct `TokenManager`. If a constant exists elsewhere (`from specify_cli.auth.config import get_saas_base_url`), import it and call it inline. Read the current `TokenManager.__init__` to decide.
   - Use `dataclasses.replace` so every existing `StoredSession` field is preserved automatically — only `teams` and `default_team_id` change.
   - The whole body is wrapped in `with self._membership_lock:` so concurrent threads see exactly one HTTP GET.

**Files**:

- `src/specify_cli/auth/token_manager.py` — add fields + method (~40 LOC).

**Validation**:

- [ ] `mypy --strict src/specify_cli/auth/token_manager.py` passes.
- [ ] No `async`/`await` on `rehydrate_membership_if_needed`.
- [ ] The existing `_get_lock()` (asyncio.Lock) is **not** acquired by this new method.
- [ ] No deadlock: lock release on every code path (`with` ensures it).

---

### T007 — Cache-bust unconditionally in `set_session()`

**Purpose**: Every login / repair / identity-change boundary that flows through `set_session` must reset the negative cache. Unconditional reset is simpler than checking `prior.email != new.email` and captures same-user re-login.

**Steps**:

1. In `TokenManager.set_session(...)`, immediately before persisting, reset:

   ```python
   def set_session(self, session: StoredSession) -> None:
       self._membership_negative_cache = False
       # ... existing persistence call (storage write + self._session = session)
   ```

2. Do not change any other behavior of `set_session`.

**Files**:

- `src/specify_cli/auth/token_manager.py` — modify `set_session` only.

**Validation**:

- [ ] `mypy --strict` passes.
- [ ] Existing tests for `set_session` still pass.
- [ ] T009's identity-change test remains green.

---

### T008 — Unit tests for `fetch_me_payload`

**Purpose**: Tiny but explicit coverage of the helper.

**Steps**:

1. Create `tests/auth/test_me_fetch.py`:

   ```python
   import httpx
   import pytest
   import respx

   from specify_cli.auth.http.me_fetch import fetch_me_payload


   @respx.mock
   def test_fetch_me_payload_success():
       respx.get("https://saas.example/api/v1/me").mock(
           return_value=httpx.Response(
               200,
               json={"email": "u@example.com", "teams": [{"id": "t1", "is_private_teamspace": True}]},
           )
       )
       payload = fetch_me_payload("https://saas.example", "tok")
       assert payload["email"] == "u@example.com"
       assert payload["teams"][0]["is_private_teamspace"] is True


   @respx.mock
   def test_fetch_me_payload_raises_on_401():
       respx.get("https://saas.example/api/v1/me").mock(return_value=httpx.Response(401))
       with pytest.raises(httpx.HTTPStatusError):
           fetch_me_payload("https://saas.example", "tok")


   @respx.mock
   def test_fetch_me_payload_passes_bearer_header():
       route = respx.get("https://saas.example/api/v1/me").mock(
           return_value=httpx.Response(200, json={"teams": []})
       )
       fetch_me_payload("https://saas.example", "my-tok")
       assert route.calls[0].request.headers["Authorization"] == "Bearer my-tok"
   ```

2. Tests are sync (no `pytest.mark.asyncio`). The `respx.mock` decorator works for both sync and async by default.

**Files**:

- `tests/auth/test_me_fetch.py` (new file).

**Validation**:

- [ ] `uv run pytest tests/auth/test_me_fetch.py -v` is green.
- [ ] Coverage on `me_fetch.py` is 100%.

---

### T009 — Unit tests for `rehydrate_membership_if_needed`

**Purpose**: Cover the seven contract branches.

**Steps**:

Add to `tests/auth/test_token_manager.py`:

```python
@respx.mock
def test_rehydrate_early_returns_when_session_already_has_private(token_manager_with_private_session):
    route = respx.get("https://saas.example/api/v1/me").mock(return_value=httpx.Response(200, json={}))
    assert token_manager_with_private_session.rehydrate_membership_if_needed() is True
    assert route.call_count == 0


@respx.mock
def test_rehydrate_fetches_persists_and_recomputes_default_team_id(token_manager_with_shared_only_session):
    """Spec FR-003 + design: default_team_id must be recomputed via pick_default_team_id(),
    NOT preserved from the old shared-only session."""
    respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {"id": "t-shared", "is_private_teamspace": False},
                    {"id": "t-private", "is_private_teamspace": True},
                ],
            },
        )
    )
    tm = token_manager_with_shared_only_session
    assert tm.rehydrate_membership_if_needed() is True
    updated = tm.get_current_session()
    assert any(t.is_private_teamspace for t in updated.teams)
    assert updated.default_team_id == "t-private"  # pick_default_team_id prefers private


@respx.mock
def test_rehydrate_sets_negative_cache_when_no_private_returned(token_manager_with_shared_only_session):
    respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={"email": "u@example.com", "teams": [{"id": "t-shared", "is_private_teamspace": False}]},
        )
    )
    tm = token_manager_with_shared_only_session
    assert tm.rehydrate_membership_if_needed() is False
    assert tm._membership_negative_cache is True


@respx.mock
def test_rehydrate_negative_cache_skips_http(token_manager_with_shared_only_session):
    tm = token_manager_with_shared_only_session
    tm._membership_negative_cache = True
    route = respx.get("https://saas.example/api/v1/me").mock(return_value=httpx.Response(200, json={}))
    assert tm.rehydrate_membership_if_needed() is False
    assert route.call_count == 0


@respx.mock
def test_rehydrate_force_true_bypasses_negative_cache(token_manager_with_shared_only_session):
    tm = token_manager_with_shared_only_session
    tm._membership_negative_cache = True
    route = respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={"email": "u@example.com", "teams": [{"id": "t-private", "is_private_teamspace": True}]},
        )
    )
    assert tm.rehydrate_membership_if_needed(force=True) is True
    assert route.call_count == 1
    assert tm._membership_negative_cache is False  # cleared via set_session in T007


@respx.mock
def test_rehydrate_returns_false_on_http_error_without_setting_cache(token_manager_with_shared_only_session, caplog):
    respx.get("https://saas.example/api/v1/me").mock(return_value=httpx.Response(500))
    tm = token_manager_with_shared_only_session
    assert tm.rehydrate_membership_if_needed() is False
    assert tm._membership_negative_cache is False  # transient errors do NOT poison
    assert any("/api/v1/me fetch failed" in rec.getMessage() for rec in caplog.records)


def test_set_session_unconditionally_clears_negative_cache(token_manager_with_shared_only_session, make_session):
    tm = token_manager_with_shared_only_session
    tm._membership_negative_cache = True
    tm.set_session(make_session(email=tm.get_current_session().email))  # SAME-user re-login
    assert tm._membership_negative_cache is False
```

Author or extend the fixtures `token_manager_with_private_session` and `token_manager_with_shared_only_session` in the test file (or `tests/auth/conftest.py`). Each builds a `TokenManager` with a `SecureStorage` mock and a `StoredSession` whose `teams` either does or does not contain a Private Teamspace. Set `_saas_base_url` (or whatever the implementation calls it) to `"https://saas.example"` for the respx routes.

**Files**:

- `tests/auth/test_token_manager.py` — add 7 test functions (and possibly 2 fixtures).

**Validation**:

- [ ] All seven tests pass.
- [ ] Coverage on `rehydrate_membership_if_needed` is 100%.
- [ ] No test reaches the real network.

---

### T010 — Concurrent-callers test (single-flight via `threading.Lock`)

**Purpose**: Prove the lock prevents the thundering herd: when N threads race on a shared-only session, exactly one HTTP GET is observed.

**Steps**:

```python
import concurrent.futures

@respx.mock
def test_rehydrate_concurrent_callers_serialize(token_manager_with_shared_only_session):
    """Four concurrent threads should produce exactly one /api/v1/me GET."""
    route = respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [{"id": "t-private", "is_private_teamspace": True}],
            },
        )
    )
    tm = token_manager_with_shared_only_session

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(tm.rehydrate_membership_if_needed) for _ in range(4)]
        results = [f.result() for f in futures]

    assert all(results)            # all four observed the now-private session
    assert route.call_count == 1   # but only one GET hit the network
```

The first thread acquires the lock, performs the GET, persists the new session via `set_session`, releases. The other three then acquire the lock in turn and find `get_private_team_id(session.teams) is not None` — they early-return without HTTP.

**Files**:

- `tests/auth/test_token_manager.py` — add 1 test function.

**Validation**:

- [ ] Test asserts `route.call_count == 1`.
- [ ] No deadlock — test completes within pytest's default timeout.

---

### T011 — Add post-refresh rehydrate hook in `TokenManager.refresh_if_needed()`

**Purpose**: When a token refresh adopts a `StoredSession` that lacks a Private Teamspace, immediately force a rehydrate so the membership recovery happens at the natural state-change boundary. Closes FR-008.

**Steps**:

1. Open `src/specify_cli/auth/token_manager.py` and locate `refresh_if_needed()` (currently around line 171–250). Find each `self._session = result.session` line — there are four (REFRESHED, ADOPTED_NEWER, LOCK_TIMEOUT_ADOPTED, STALE_REJECTION_PRESERVED branches, around lines 235–250).

2. After each adoption line, insert the hook:

   ```python
   self._session = result.session
   if get_private_team_id(result.session.teams) is None:
       self.rehydrate_membership_if_needed(force=True)
   ```

   (Or refactor into a small private helper `_apply_post_refresh_hook(self, session)` if you prefer; the test in T012 is what matters.)

3. The hook is a sync call inside an async method. That is fine — `rehydrate_membership_if_needed` does not block the event loop (the threading.Lock is held only for the duration of the sync HTTP GET, which has its own timeout). For long-lived event loops where this could be a concern, the call can be wrapped in `asyncio.get_running_loop().run_in_executor(None, ...)`; for this mission's CLI invocation lifetime, the inline call is acceptable.

4. `force=True` is required because token refresh is a state-change boundary; the negative cache from earlier in this process must not block recovery.

**Files**:

- `src/specify_cli/auth/token_manager.py` — modify `refresh_if_needed()` only (~5–8 added lines).

**Validation**:

- [ ] `mypy --strict` passes.
- [ ] Existing `refresh_if_needed` test cases still pass.
- [ ] WP03's tests (T012, T013) cover the integration end-to-end.
- [ ] `flows/refresh.py` is **not** modified (out of scope for this mission).

---

## Definition of Done

- [ ] `auth/http/me_fetch.py` exists with sync `fetch_me_payload(saas_base_url, access_token)`.
- [ ] `TokenManager` has `_membership_negative_cache: bool`, `_membership_lock: threading.Lock`, and sync `rehydrate_membership_if_needed(*, force=False) -> bool`.
- [ ] `TokenManager.set_session()` clears `_membership_negative_cache` unconditionally.
- [ ] `TokenManager.refresh_if_needed()` calls `rehydrate_membership_if_needed(force=True)` after each adoption point when the new session lacks a Private Teamspace.
- [ ] All new tests pass (T008: 3, T009: 7, T010: 1 — 11 total).
- [ ] All pre-existing `tests/auth/` tests pass.
- [ ] `mypy --strict` green for `me_fetch.py` and `token_manager.py`.
- [ ] `ruff check` green.
- [ ] Coverage on new code ≥ 90%.
- [ ] No path uses `OAuthHttpClient` from inside `rehydrate_membership_if_needed`.
- [ ] No path acquires the existing `asyncio.Lock` from a sync code path.

## Risks & reviewer guidance

| Risk | Mitigation |
|------|------------|
| Sync rehydrate inside an async `refresh_if_needed` blocks the event loop | The HTTP call has a transport-level timeout; the lock window is short. T012 (in WP03) verifies behavioral correctness. If a future operator-mode async loop needs nonblocking, wrap in `run_in_executor`. |
| `_saas_base_url` is not currently a `TokenManager` field | T006 step 4 calls this out explicitly: thread it through the constructor or import a config getter. Read existing `TokenManager.__init__` first. |
| `dataclasses.replace` doesn't apply because `StoredSession` isn't a dataclass | Read `auth/session.py:80+` first; it IS a dataclass. If something has changed, fall back to constructing a new `StoredSession(...)` with every field listed explicitly. |
| The hook in T011 uses `self.rehydrate_membership_if_needed(force=True)` from inside `refresh_if_needed`'s async body — the threading.Lock and asyncio.Lock could deadlock if interleaved | The two locks are independent. `refresh_if_needed` holds the asyncio.Lock; `rehydrate_membership_if_needed` acquires the threading.Lock. No code path acquires both simultaneously. |
| `Exception` catch in T006 is too broad | Intentional log-and-skip boundary. `BLE001` is suppressed only at this single line and the message includes the exception. |

**Reviewer should verify**:

- The body of `rehydrate_membership_if_needed` is wrapped in `with self._membership_lock:` for its entirety.
- The success path uses `pick_default_team_id(teams)` for `default_team_id` — NOT `payload.get("default_team_id", session.default_team_id)`.
- The success path preserves all token/email fields exactly via `dataclasses.replace(session, teams=..., default_team_id=...)`.
- The negative cache is **never** persisted to disk.
- T011's hook fires for all four `RefreshOutcome` adoption branches.

---

## Implementation command (after dependencies satisfied)

```bash
spec-kitty agent action implement WP02 --agent <name>
```

This WP has no dependencies and can start immediately.

## Activity Log

- 2026-05-01T08:51:53Z – claude:sonnet:python-pedro:implementer – shell_pid=24072 – Started implementation via action command
- 2026-05-01T09:37:22Z – claude:sonnet:python-pedro:implementer – shell_pid=24072 – Ready for review: sync rehydrate + me_fetch + refresh hook + 11 new tests.
- 2026-05-01T09:38:22Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=95248 – Started review via action command
- 2026-05-01T09:50:17Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=95248 – Moved to planned
- 2026-05-01T10:15:24Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=95248 – Arbiter approval: implementation committed at a8df84da, all gates green. The codex review verdict in review-cycle-4.md was contaminated by TMPDIR collision with sibling tracker repo (cf review file mentions 'tests/architectural/test_status_sync_boundary.py' which is from a different mission). Skipping artifact check intentionally.
