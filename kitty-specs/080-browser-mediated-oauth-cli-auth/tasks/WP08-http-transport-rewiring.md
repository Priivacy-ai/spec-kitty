---
work_package_id: WP08
title: HTTP Transport Rewiring
dependencies:
- WP01
- WP09
requirement_refs:
- FR-011
- FR-016
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
- T047
history: []
authoritative_surface: src/specify_cli/auth/http/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/http/**
- src/specify_cli/sync/client.py
- src/specify_cli/sync/background.py
- src/specify_cli/sync/batch.py
- src/specify_cli/sync/body_transport.py
- src/specify_cli/sync/runtime.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/events.py
- src/specify_cli/tracker/saas_client.py
- tests/auth/test_http_transport.py
status: pending
tags: []
agent: "claude:opus-4-6:python-implementer:implementer"
shell_pid: "93744"
---

# WP08: HTTP Transport Rewiring

**Objective**: This is the **integration** WP. It builds the new
`OAuthHttpClient` AND rewires every legacy HTTP/WebSocket caller in
`src/specify_cli/sync/` and `src/specify_cli/tracker/` to obtain bearer tokens
from `get_token_manager()`. After this WP, no production code outside the
`auth/` package references the legacy `AuthClient` or `CredentialStore`.

**Context**: This is the WP that the previous run failed at most spectacularly.
WP07 (in the previous decomposition) built `OAuthHttpClient` in isolation but
did not rewire any caller. The result was a fully-tested `OAuthHttpClient`
class with **zero callers from production code** — dead code. This WP
explicitly owns the legacy transport files AND has two grep audits in its DoD
that fail the WP if dead code remains.

**CRITICAL**: WP08 owns multiple files outside the new `auth/` package. This
is intentional. The post-merge review found that WP-isolation was the root
cause of the previous failure. WP08 deliberately spans the new and old
code so the integration is forced.

**Acceptance Criteria**:
- [ ] `OAuthHttpClient` class exists in `src/specify_cli/auth/http/transport.py`
- [ ] OAuthHttpClient injects `Authorization: Bearer <token>` from `await get_token_manager().get_access_token()` on every request
- [ ] OAuthHttpClient retries once on 401 after calling `await get_token_manager().refresh_if_needed()`
- [ ] OAuthHttpClient propagates non-401 errors unchanged
- [ ] `sync/client.py` no longer imports `AuthClient` or `CredentialStore`
- [ ] `sync/client.py` HTTP requests get tokens from `get_token_manager()`
- [ ] `sync/client.py` WebSocket pre-connect uses `auth.websocket.provision_ws_token` (from WP09)
- [ ] `tracker/saas_client.py` no longer imports `AuthClient` or `CredentialStore`
- [ ] `tracker/saas_client.py` HTTP requests get tokens from `get_token_manager()`
- [ ] `sync/{background,batch,body_transport,runtime,emitter,events}.py` no longer import `AuthClient` or `CredentialStore`
- [ ] T045 GREP AUDIT passes (zero hits for legacy classes outside auth/)
- [ ] T046 GREP AUDIT passes (≥5 hits for `get_token_manager` from production code)
- [ ] All unit tests pass

---

## Subtask Guidance

### T041: Create `auth/http/transport.py` (OAuthHttpClient)

**Purpose**: The httpx wrapper that injects bearer tokens and handles 401 retry.

**Steps**:

1. Create `src/specify_cli/auth/http/__init__.py`:
   ```python
   from __future__ import annotations
   from .transport import OAuthHttpClient

   __all__ = ["OAuthHttpClient"]
   ```

2. Create `src/specify_cli/auth/http/transport.py`:
   ```python
   """OAuth-aware HTTP client for spec-kitty SaaS calls."""
   from __future__ import annotations
   import logging
   from typing import Any, Optional
   import httpx
   from .. import get_token_manager
   from ..errors import (
       NotAuthenticatedError,
       TokenRefreshError,
       NetworkError,
   )

   log = logging.getLogger(__name__)


   class OAuthHttpClient:
       """An httpx wrapper that injects bearer tokens and handles 401 with auto-refresh.

       Usage:
           async with OAuthHttpClient() as client:
               response = await client.get("https://saas/api/v1/me")

       The client gets the access token from the shared TokenManager
       (`get_token_manager()`) on every request. On 401, it calls
       `refresh_if_needed()` and retries once. Non-401 errors are propagated.
       """

       def __init__(self, timeout: float = 30.0) -> None:
           self._client: Optional[httpx.AsyncClient] = None
           self._timeout = timeout

       async def __aenter__(self) -> "OAuthHttpClient":
           self._client = httpx.AsyncClient(timeout=self._timeout)
           return self

       async def __aexit__(self, *exc_info) -> None:
           if self._client is not None:
               await self._client.aclose()
               self._client = None

       async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
           """Send an HTTP request with bearer token injection and 401 retry."""
           if self._client is None:
               raise RuntimeError("OAuthHttpClient must be used as an async context manager")

           tm = get_token_manager()
           token = await tm.get_access_token()  # may auto-refresh if near expiry

           headers = kwargs.pop("headers", {}) or {}
           headers["Authorization"] = f"Bearer {token}"

           try:
               response = await self._client.request(method, url, headers=headers, **kwargs)
           except httpx.RequestError as exc:
               raise NetworkError(f"Network error: {exc}") from exc

           if response.status_code != 401:
               return response

           # 401 → try refresh + single retry
           log.debug("Received 401, attempting refresh + retry")
           try:
               refreshed = await tm.refresh_if_needed()
           except TokenRefreshError:
               return response  # Caller sees the original 401
           if not refreshed:
               return response  # Refresh was a no-op (someone else refreshed)
           # Retry once with the new token
           token = await tm.get_access_token()
           headers["Authorization"] = f"Bearer {token}"
           try:
               return await self._client.request(method, url, headers=headers, **kwargs)
           except httpx.RequestError as exc:
               raise NetworkError(f"Network error on retry: {exc}") from exc

       async def get(self, url: str, **kwargs: Any) -> httpx.Response:
           return await self.request("GET", url, **kwargs)

       async def post(self, url: str, **kwargs: Any) -> httpx.Response:
           return await self.request("POST", url, **kwargs)

       async def put(self, url: str, **kwargs: Any) -> httpx.Response:
           return await self.request("PUT", url, **kwargs)

       async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
           return await self.request("DELETE", url, **kwargs)
   ```

**Files**: `src/specify_cli/auth/http/__init__.py` (~10 lines), `src/specify_cli/auth/http/transport.py` (~140 lines)

**Validation**:
- [ ] `from specify_cli.auth.http import OAuthHttpClient` works
- [ ] Can be used as async context manager
- [ ] Bearer token injected correctly
- [ ] 401 triggers refresh + retry
- [ ] Non-401 errors pass through

---

### T042: Rewire `sync/client.py` (HTTP and WebSocket paths) to TokenManager

**Purpose**: The biggest single rewiring. `sync/client.py` is the central
SaaS HTTP/WebSocket client used by the sync subsystem.

**Steps**:

1. Read the current `src/specify_cli/sync/client.py`. Identify:
   - All imports of `AuthClient`, `AuthenticationError`, `CredentialStore` from `specify_cli.sync.auth`
   - All call sites that read tokens (e.g., `self._auth_client.obtain_ws_token()`, `self._direct_token`, etc.)
   - WebSocket connection setup that needs the WS token from WP09

2. Replace imports:
   ```python
   # OLD
   from specify_cli.sync.auth import AuthClient, AuthenticationError

   # NEW
   from specify_cli.auth import get_token_manager
   from specify_cli.auth.errors import (
       AuthenticationError,
       NotAuthenticatedError,
       TokenRefreshError,
   )
   from specify_cli.auth.http import OAuthHttpClient
   ```

3. Remove all `auth_client: AuthClient | None` constructor parameters and
   `self._auth_client` attributes. The new pattern: `client.py` does not
   hold a reference to a TokenManager; it calls `get_token_manager()` each
   time it needs a token.

4. For HTTP requests, replace direct httpx calls with `OAuthHttpClient`:
   ```python
   # OLD
   async with httpx.AsyncClient() as http:
       response = await http.get(url, headers={"Authorization": f"Bearer {token}"})

   # NEW
   async with OAuthHttpClient() as http:
       response = await http.get(url)  # Bearer + 401 retry handled internally
   ```

5. For WebSocket pre-connect token, lazy-import from WP09's package:
   ```python
   # WS connect needs an ephemeral token
   from specify_cli.auth.websocket import provision_ws_token  # WP09 module
   ws_token_response = await provision_ws_token(team_id=...)
   ws_url_with_token = f"{ws_url}?token={ws_token_response['ws_token']}"
   ```

6. Verify the diff: the file should have no references to `AuthClient`,
   `CredentialStore`, `_auth_client`, `_direct_token`, or `obtain_ws_token`.

**Files**: `src/specify_cli/sync/client.py` (rewire — exact LOC depends on current size)

**Validation**:
- [ ] `grep -n 'AuthClient\|CredentialStore' src/specify_cli/sync/client.py` returns nothing
- [ ] `grep -n 'get_token_manager\|OAuthHttpClient' src/specify_cli/sync/client.py` returns at least 1 hit each
- [ ] Existing sync/client tests pass (may need updates — owned by this WP)

---

### T043: Rewire `tracker/saas_client.py` to TokenManager

**Purpose**: Same pattern as T042 but for the tracker subsystem's SaaS client.

**Steps**:

1. Read the current `src/specify_cli/tracker/saas_client.py`. The post-merge
   review found these references:
   ```
   line 16: from specify_cli.sync.auth import AuthClient, CredentialStore
   line 96: credential_store: ...
   line 107: credential_store: CredentialStore | None = None,
   line 112: self._credential_store = credential_store or CredentialStore()
   line 170: access_token = self._credential_store.get_access_token()
   line 176: team_slug = self._credential_store.get_team_slug()
   line 229: auth_client.credential_store = self._credential_store
   ```

2. Replace the `CredentialStore` initialization with TokenManager access:
   ```python
   # OLD
   self._credential_store = credential_store or CredentialStore()

   # NEW: nothing — TokenManager is fetched on demand via get_token_manager()
   ```

3. Replace `get_access_token()` calls:
   ```python
   # OLD
   access_token = self._credential_store.get_access_token()
   if access_token is None:
       raise AuthenticationError("...")

   # NEW
   tm = get_token_manager()
   if not tm.is_authenticated:
       raise NotAuthenticatedError("Run `spec-kitty auth login` to authenticate.")
   access_token = await tm.get_access_token()
   ```

4. Replace `get_team_slug()` calls. The team slug is now derived from the
   StoredSession's default team:
   ```python
   # OLD
   team_slug = self._credential_store.get_team_slug()

   # NEW
   session = tm.get_current_session()
   team = next((t for t in session.teams if t.id == session.default_team_id), None)
   team_slug = team.id if team else None
   ```

5. Replace direct httpx calls with `OAuthHttpClient` where appropriate.
   The 401 retry path is now handled by `OAuthHttpClient`, so the existing
   `auth_client.refresh_tokens()` cleanup logic can be removed.

**Files**: `src/specify_cli/tracker/saas_client.py` (rewire)

**Validation**:
- [ ] `grep -n 'AuthClient\|CredentialStore' src/specify_cli/tracker/saas_client.py` returns nothing
- [ ] `grep -n 'get_token_manager\|OAuthHttpClient' src/specify_cli/tracker/saas_client.py` returns ≥1 hit
- [ ] Existing tracker tests pass (may need updates)

---

### T044: Rewire sync/{background,batch,body_transport,runtime,emitter,events}.py

**Purpose**: Sweep the remaining sync modules. Each one currently imports
`AuthClient` from `specify_cli.sync.auth`. The pattern is the same as T042/T043.

**Steps**:

1. For each file in: `background.py`, `batch.py`, `body_transport.py`,
   `runtime.py`, `emitter.py`, `events.py`:
   - Remove `from .auth import AuthClient` (or similar)
   - Replace any constructor parameter `auth: AuthClient` or attribute
     `self.auth`
   - Replace token access:
     ```python
     # OLD
     access_token = self.auth.get_access_token()

     # NEW
     from specify_cli.auth import get_token_manager
     tm = get_token_manager()
     access_token = await tm.get_access_token()
     ```
   - For functions with `auth_token: str` parameters, decide:
     - If the function is called from within an async context, remove
       the parameter and call `get_token_manager().get_access_token()` inline
     - If the function is sync and called from an async caller, leave
       the parameter and let the caller fetch the token

2. The signature changes may cascade — that's expected. WP08 owns ALL of
   these files so the changes are atomic.

3. The `auth_token: JWT access token` docstring references should be removed
   (the spec moved away from JWT).

**Files**: 6 files in `src/specify_cli/sync/` (rewire each)

**Validation**:
- [ ] None of the 6 files import from `specify_cli.sync.auth`
- [ ] All imports of `AuthClient` are gone
- [ ] All tests for these modules pass after the rewire

---

### T045: GREP AUDIT — zero `CredentialStore`/`AuthClient` references outside `auth/`

**Purpose**: The hard gate that prevents WP08 from being approved with dead code remaining.

**Steps**:

1. Run the grep:
   ```bash
   grep -rn 'CredentialStore\|AuthClient' src/specify_cli/ --include='*.py' \
       | grep -v '^src/specify_cli/auth/'
   ```

2. The expected output is **empty** (no hits). Any hit means:
   - Either: a transport file still references the legacy classes (incomplete rewire) → fix the file
   - Or: a stale comment or string contains the names → remove it

3. Note: `src/specify_cli/sync/auth.py` itself still exists at this point.
   It is still on disk, but no one imports from it. WP10 will delete it.
   For now, the grep includes the substring match in `src/specify_cli/sync/auth.py`
   itself, so we exclude it explicitly:
   ```bash
   grep -rn 'CredentialStore\|AuthClient' src/specify_cli/ --include='*.py' \
       | grep -v '^src/specify_cli/auth/' \
       | grep -v '^src/specify_cli/sync/auth.py'
   ```

4. Add the exact grep command and expected output to the WP completion notes.

5. **WP08 is INCOMPLETE if this audit returns any hits.** Reviewer must reject.

**Files**: no file changes; this is a verification subtask

**Validation**:
- [ ] Grep returns empty
- [ ] Reviewer re-runs the grep before approving

---

### T046: GREP AUDIT — ≥5 `get_token_manager` callers from production code

**Purpose**: The positive gate that proves WP08 actually wired up the new TokenManager.

**Steps**:

1. Run the grep:
   ```bash
   grep -rn 'get_token_manager\b' src/specify_cli/ --include='*.py' \
       | grep -v '^src/specify_cli/auth/'
   ```

2. Expected: **at least 5 hits**, one per rewired file family:
   - sync/client.py
   - sync/background.py
   - sync/batch.py
   - sync/body_transport.py (or related)
   - tracker/saas_client.py
   - cli/commands/_auth_login.py (from WP04)
   - cli/commands/_auth_logout.py (from WP06)
   - cli/commands/_auth_status.py (from WP07)

3. The actual count depends on which sync files are rewired, but **≥5** is
   the minimum bar. Note that hits from `cli/commands/_auth_*.py` count
   even though those are owned by other WPs — they show that the foundation
   is being used by the user-facing layer too.

4. If fewer than 5 hits: at least one rewire is missing. Find the file and
   complete the rewire.

5. **WP08 is INCOMPLETE if this audit returns fewer than 5 hits.** Reviewer
   must reject.

**Files**: no file changes; this is a verification subtask

**Validation**:
- [ ] Grep returns at least 5 hits
- [ ] Reviewer re-runs the grep before approving

---

### T047: Write unit tests for OAuthHttpClient + update sync/client tests

**Purpose**: Coverage for the new HTTP wrapper plus updates to existing tests
that broke during the rewire.

**Steps**:

1. Create `tests/auth/test_http_transport.py`:
   ```python
   import pytest
   from unittest.mock import AsyncMock, patch
   import httpx
   from specify_cli.auth.http import OAuthHttpClient
   from specify_cli.auth import reset_token_manager
   from specify_cli.auth.errors import NetworkError, TokenRefreshError


   @pytest.fixture
   def mock_tm(monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
       reset_token_manager()
       # Inject a fake TokenManager
       from specify_cli.auth.token_manager import TokenManager
       fake_tm = AsyncMock(spec=TokenManager)
       fake_tm.get_access_token = AsyncMock(return_value="at_xyz")
       fake_tm.refresh_if_needed = AsyncMock(return_value=True)
       with patch("specify_cli.auth.http.transport.get_token_manager", return_value=fake_tm):
           yield fake_tm
       reset_token_manager()


   @pytest.mark.asyncio
   class TestOAuthHttpClient:

       async def test_bearer_injection(self, mock_tm, respx_mock):
           respx_mock.get("https://saas.test/api/test").mock(
               return_value=httpx.Response(200, json={"ok": True})
           )
           async with OAuthHttpClient() as client:
               response = await client.get("https://saas.test/api/test")
           assert response.status_code == 200
           assert respx_mock.calls[0].request.headers["Authorization"] == "Bearer at_xyz"

       async def test_401_triggers_refresh_and_retry(self, mock_tm, respx_mock):
           # First call returns 401, second call returns 200
           call_count = 0
           def handler(request):
               nonlocal call_count
               call_count += 1
               if call_count == 1:
                   return httpx.Response(401)
               return httpx.Response(200)
           respx_mock.get("https://saas.test/api/test").mock(side_effect=handler)
           async with OAuthHttpClient() as client:
               response = await client.get("https://saas.test/api/test")
           assert response.status_code == 200
           assert call_count == 2  # First 401, second success
           mock_tm.refresh_if_needed.assert_called_once()

       async def test_refresh_failure_propagates_401(self, mock_tm, respx_mock):
           mock_tm.refresh_if_needed = AsyncMock(side_effect=TokenRefreshError("expired"))
           respx_mock.get("https://saas.test/api/test").mock(return_value=httpx.Response(401))
           async with OAuthHttpClient() as client:
               response = await client.get("https://saas.test/api/test")
           assert response.status_code == 401  # Original 401 returned

       async def test_500_propagates_unchanged(self, mock_tm, respx_mock):
           respx_mock.get("https://saas.test/api/test").mock(return_value=httpx.Response(500))
           async with OAuthHttpClient() as client:
               response = await client.get("https://saas.test/api/test")
           assert response.status_code == 500
           # Refresh should NOT have been called (only 401 triggers refresh)
           mock_tm.refresh_if_needed.assert_not_called()
   ```

2. Update `tests/sync/test_client.py` (or wherever sync/client tests live) to
   mock `get_token_manager` instead of the legacy `AuthClient`. WP08 owns this
   file for the duration of this WP.

3. Run the tests:
   ```bash
   pytest tests/auth/test_http_transport.py tests/sync/test_client.py -v
   ```

**Files**: `tests/auth/test_http_transport.py` (~250 lines), updates to `tests/sync/test_client.py`

**Validation**:
- [ ] All new and updated tests pass

---

## Definition of Done

- [ ] All 7 subtasks completed
- [ ] T045 GREP AUDIT passes (zero hits)
- [ ] T046 GREP AUDIT passes (≥5 hits)
- [ ] All existing sync and tracker tests still pass after rewiring
- [ ] OAuthHttpClient unit tests pass
- [ ] No tokens or secrets logged

## Reviewer Guidance

**This is the most important review of the entire mission.** The previous
run failed at exactly this WP — built OAuthHttpClient in isolation, never
rewired any caller, shipped dead code. Reviewer must:

1. **Re-run T045 grep**: `grep -rn 'CredentialStore\|AuthClient' src/specify_cli/ --include='*.py' | grep -v '^src/specify_cli/auth/' | grep -v '^src/specify_cli/sync/auth.py'`. Expect empty.
2. **Re-run T046 grep**: `grep -rn 'get_token_manager\b' src/specify_cli/ --include='*.py' | grep -v '^src/specify_cli/auth/'`. Expect ≥5 hits.
3. **Visually inspect** sync/client.py, tracker/saas_client.py, sync/background.py: each must import from `specify_cli.auth` (not `specify_cli.sync.auth`).
4. **Reject if any rewire is half-done.** Better to fail this WP and have a clean rewire than ship dead code again.

## Risks & Edge Cases

- **Risk**: Existing sync/client tests use the legacy CredentialStore as a fixture. **Mitigation**: WP08 owns those test files and updates them as part of T047.
- **Risk**: `auth_token: str` parameters propagate through many call chains. **Mitigation**: WP08 owns all 6 sync files; the cascade is contained.
- **Risk**: WebSocket pre-connect needs WP09 to exist. **Mitigation**: WP08 deps include WP09. Lane allocator will sequence WP09 before WP08.
- **Edge case**: A consumer of `sync/client.py` outside the auth/sync subsystem (e.g., a CLI command) may fail because the constructor signature changed. **Mitigation**: WP08 grep audits catch this; reviewer fixes the caller.

## Activity Log

- 2026-04-09T17:43:53Z – opus:opus:implementer:implementer – shell_pid=1860 – Started implementation via action command
- 2026-04-09T18:08:23Z – opus:opus:implementer:implementer – shell_pid=1860 – Moved to planned
- 2026-04-09T18:11:04Z – opus:opus:implementer:implementer – shell_pid=24720 – Started implementation via action command
- 2026-04-09T18:15:59Z – opus:opus:implementer:implementer – shell_pid=24720 – Moved to planned
- 2026-04-09T19:50:30Z – claude:opus-4-6:python-implementer:implementer – shell_pid=93744 – Started implementation via action command
- 2026-04-09T20:53:21Z – claude:opus-4-6:python-implementer:implementer – shell_pid=93744 – Moved to for_review
