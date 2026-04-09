---
work_package_id: WP06
title: Logout Command (`auth logout`)
dependencies:
- WP01
- WP04
- WP08
requirement_refs:
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
history: []
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_auth_logout.py
- tests/cli/commands/test_auth_logout.py
status: pending
tags: []
agent: "claude:opus-4-6:python-implementer:implementer"
shell_pid: "76066"
---

# WP06: Logout Command (`auth logout`)

**Objective**: Implement the `_auth_logout.py` module that the dispatch shell
in `cli/commands/auth.py` (owned by WP04) imports lazily. The logout command
must call POST `/api/v1/logout` server-side AND delete local credentials.
Server failure must NOT block local cleanup (FR-014).

**Context**: WP04 set up the dispatch shell with `from specify_cli.cli.commands._auth_logout import logout_impl`
inside the Typer command body. This WP provides that module. WP06 depends on
WP08 because it uses the `OAuthHttpClient` from `auth/http/transport.py` to
call the logout endpoint.

**Acceptance Criteria**:
- [ ] `from specify_cli.cli.commands._auth_logout import logout_impl` works after this WP
- [ ] `spec-kitty auth logout` calls POST `get_saas_base_url() + '/api/v1/logout'` with the bearer token
- [ ] **No request body** — the SaaS contract is bearer-only. The session being revoked is identified server-side by the bound session_id of the token, not by a client-provided field
- [ ] On 200 OK response: prints success, clears local session
- [ ] On non-200 response: prints warning, STILL clears local session (FR-014)
- [ ] On network error: prints warning, STILL clears local session (FR-014)
- [ ] Already-logged-out: prints "ℹ️  Not logged in" and exits 0
- [ ] `--force` flag skips the server call entirely (local-only logout)
- [ ] All unit + CliRunner tests pass

---

## Subtask Guidance

### T033: Create `cli/commands/_auth_logout.py` with logout_impl

**Purpose**: The implementation function that the dispatch shell calls.

**Steps**:

1. Create `src/specify_cli/cli/commands/_auth_logout.py`:
   ```python
   """Implementation of `spec-kitty auth logout`. Owned by WP06."""
   from __future__ import annotations
   import logging
   import httpx
   from rich.console import Console
   import typer
   from specify_cli.auth import (
       get_token_manager,
       NotAuthenticatedError,
       ConfigurationError,
   )
   from specify_cli.auth.config import get_saas_base_url

   log = logging.getLogger(__name__)
   console = Console()


   async def logout_impl(*, force: bool) -> None:
       """Run the logout flow.

       Server-side logout failure does not block local credential deletion (FR-014).
       """
       tm = get_token_manager()

       if not tm.is_authenticated:
           console.print("ℹ️  Not logged in.")
           return

       session = tm.get_current_session()

       if not force:
           # Try to revoke server-side
           try:
               saas_url = get_saas_base_url()
           except ConfigurationError as exc:
               console.print(
                   f"[yellow]⚠ Cannot reach SaaS (config error): {exc}. "
                   f"Proceeding with local logout only.[/yellow]"
               )
           else:
               await _call_server_logout(saas_url, session.access_token)
       else:
           console.print("[dim]Skipping server revocation (--force).[/dim]")

       # Always clear local session, even if server logout failed
       tm.clear_session()
       console.print("[green]✓ Logged out.[/green]")


   async def _call_server_logout(saas_url: str, access_token: str) -> None:
       """Call POST /api/v1/logout. On any failure, log a warning but do not raise.

       Per the SaaS contract (protected-endpoints.md), the logout endpoint is
       bearer-only with NO request body. The session being revoked is identified
       server-side by the bound session_id of the token.
       """
       url = f"{saas_url}/api/v1/logout"
       headers = {"Authorization": f"Bearer {access_token}"}
       try:
           async with httpx.AsyncClient(timeout=10.0) as client:
               response = await client.post(url, headers=headers)  # NO body
       except httpx.RequestError as exc:
           console.print(
               f"[yellow]⚠ Server logout failed (network error: {exc}). "
               f"Local credentials will still be deleted.[/yellow]"
           )
           return
       except Exception as exc:
           log.warning("Unexpected exception during server logout: %s", exc)
           console.print(
               f"[yellow]⚠ Server logout failed: {exc}. "
               f"Local credentials will still be deleted.[/yellow]"
           )
           return

       if response.status_code == 200:
           # Success — server-side session is invalidated
           return
       if response.status_code in (401, 403):
           console.print(
               f"[yellow]⚠ Server reports session already invalid "
               f"(HTTP {response.status_code}). Local credentials will be deleted.[/yellow]"
           )
           return
       # 4xx/5xx other than auth errors
       console.print(
           f"[yellow]⚠ Server logout returned HTTP {response.status_code}. "
           f"Local credentials will still be deleted.[/yellow]"
       )
   ```

2. Note: this WP uses `httpx.AsyncClient` directly (not `OAuthHttpClient`)
   because logout is a single fire-and-forget call that should NOT trigger
   automatic refresh on 401. If the access token is already invalid, that's
   fine — we still delete locally.

3. Critical: the `tm.clear_session()` call is OUTSIDE the try/except block
   for the server call. Local cleanup ALWAYS happens, regardless of server
   outcome. FR-014.

**Files**: `src/specify_cli/cli/commands/_auth_logout.py` (~110 lines)

**Validation**:
- [ ] `from specify_cli.cli.commands._auth_logout import logout_impl` works
- [ ] `logout_impl(force=False)` calls server logout
- [ ] `logout_impl(force=True)` skips server logout
- [ ] `tm.clear_session()` is always called

---

### T034: Implement /api/v1/logout call

**Purpose**: Already implemented in T033 as `_call_server_logout()`. T034 is
about edge case coverage and fault tolerance.

**Steps**:

1. Verify the request:
   - URL: `f"{get_saas_base_url()}/api/v1/logout"`
   - Method: POST
   - Headers: `Authorization: Bearer <access_token>`
   - Body: `{"session_id": "<session_id>"}` as JSON

2. Verify the error handling matrix:
   - 200 OK → success, no message
   - 401 → already invalid, print warning but continue
   - 403 → already invalid, print warning but continue
   - 4xx other → print warning but continue
   - 5xx → print warning but continue
   - Network error → print warning but continue
   - Any unexpected exception → log warning, continue

3. Verify NO `raise` statements in `_call_server_logout` (except possibly
   re-raising specific authentication errors that the caller handles).

**Files**: included in T033

**Validation**:
- [ ] All status codes handled gracefully
- [ ] Network errors do not propagate
- [ ] `tm.clear_session()` is reached in all cases

---

### T035: Add `--force` flag for local-only logout

**Purpose**: Already implemented in T033 via the `force: bool` parameter.

**Steps**:

1. Verify `force=True` skips the server call entirely.
2. Verify `force=True` still calls `tm.clear_session()`.
3. Verify the dispatch shell in `cli/commands/auth.py` (WP04) passes the
   `--force` flag through to `logout_impl(force=...)`.

**Files**: included in T033

**Validation**:
- [ ] CliRunner test for `auth logout --force` does not make any HTTP calls
- [ ] CliRunner test for `auth logout --force` still removes the session

---

### T036: Write unit + CliRunner tests for logout

**Purpose**: Coverage of all paths.

**Steps**:

1. Create `tests/cli/commands/test_auth_logout.py`:
   ```python
   import pytest
   from datetime import datetime, timedelta, timezone
   from unittest.mock import AsyncMock, patch, MagicMock
   from typer.testing import CliRunner
   from specify_cli.cli.commands.auth import app
   from specify_cli.auth import reset_token_manager, get_token_manager
   from specify_cli.auth.session import StoredSession, Team

   runner = CliRunner()


   def _make_session(expires_in_seconds: int = 3600) -> StoredSession:
       now = datetime.now(timezone.utc)
       return StoredSession(
           user_id="u_alice",
           email="alice@example.com",
           name="Alice",
           teams=[Team(id="tm_acme", name="Acme", role="admin")],
           default_team_id="tm_acme",
           access_token="at_xyz",
           refresh_token="rt_xyz",
           session_id="sess_xyz",
           issued_at=now,
           access_token_expires_at=now + timedelta(seconds=expires_in_seconds),
           refresh_token_expires_at=now + timedelta(days=90),
           scope="offline_access",
           storage_backend="file",
           last_used_at=now,
           auth_method="authorization_code",
       )


   @pytest.fixture(autouse=True)
   def _isolate(monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
       reset_token_manager()
       yield
       reset_token_manager()


   class TestLogoutCommand:

       def test_not_logged_in(self):
           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
               mock_storage = mock_se.return_value
               mock_storage.read.return_value = None
               mock_storage.delete = lambda: None
               mock_storage.backend_name = "file"
               reset_token_manager()
               result = runner.invoke(app, ["logout"])
           assert result.exit_code == 0
           assert "Not logged in" in result.stdout

       def test_logout_success_server_200(self):
           class _Resp:
               status_code = 200
           async def _post(url, json=None, headers=None):
               return _Resp()
           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
               mock_storage = mock_se.return_value
               mock_storage.read.return_value = _make_session()
               mock_storage.write = lambda s: None
               mock_storage.delete = MagicMock()
               mock_storage.backend_name = "file"
               reset_token_manager()
               with patch("httpx.AsyncClient") as mock_client:
                   instance = mock_client.return_value.__aenter__.return_value
                   instance.post = _post
                   result = runner.invoke(app, ["logout"])
           assert result.exit_code == 0
           assert "Logged out" in result.stdout
           mock_storage.delete.assert_called_once()

       def test_logout_server_failure_still_clears_local(self):
           import httpx
           async def _post(url, json=None, headers=None):
               raise httpx.RequestError("network down")
           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
               mock_storage = mock_se.return_value
               mock_storage.read.return_value = _make_session()
               mock_storage.write = lambda s: None
               mock_storage.delete = MagicMock()
               mock_storage.backend_name = "file"
               reset_token_manager()
               with patch("httpx.AsyncClient") as mock_client:
                   instance = mock_client.return_value.__aenter__.return_value
                   instance.post = _post
                   result = runner.invoke(app, ["logout"])
           assert result.exit_code == 0
           assert "Server logout failed" in result.stdout
           assert "Logged out" in result.stdout  # Local cleanup still happened
           mock_storage.delete.assert_called_once()

       def test_logout_force_skips_server(self):
           server_called = []
           async def _post(url, json=None, headers=None):
               server_called.append(url)
               class _R:
                   status_code = 200
               return _R()
           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
               mock_storage = mock_se.return_value
               mock_storage.read.return_value = _make_session()
               mock_storage.write = lambda s: None
               mock_storage.delete = MagicMock()
               mock_storage.backend_name = "file"
               reset_token_manager()
               with patch("httpx.AsyncClient") as mock_client:
                   instance = mock_client.return_value.__aenter__.return_value
                   instance.post = _post
                   result = runner.invoke(app, ["logout", "--force"])
           assert result.exit_code == 0
           assert len(server_called) == 0  # Server NOT called
           mock_storage.delete.assert_called_once()
   ```

**Files**: `tests/cli/commands/test_auth_logout.py` (~200 lines)

**Validation**:
- [ ] All 4 test methods pass
- [ ] Test `test_logout_server_failure_still_clears_local` verifies FR-014
- [ ] CliRunner is used (test passes WP11 T063 audit)

---

## Definition of Done

- [ ] All 4 subtasks completed
- [ ] All unit tests pass
- [ ] FR-013 verified: server-side logout endpoint is called on normal logout
- [ ] FR-014 verified: server failure does not block local cleanup
- [ ] `--force` flag skips server call
- [ ] No tokens logged

## Reviewer Guidance

- Verify `tm.clear_session()` is called UNCONDITIONALLY (outside any try/except)
- Verify the server call uses `httpx.AsyncClient` directly (not OAuthHttpClient — we don't want auto-refresh during logout)
- Verify the `--force` test asserts that NO HTTP call is made
- Verify the network-error test asserts that local cleanup still happens

## Risks & Edge Cases

- **Risk**: Server returns 401 because the token expired since the user logged in. **Mitigation**: 401/403 is treated as "already invalid", warn but continue.
- **Risk**: SPEC_KITTY_SAAS_URL is unset → ConfigurationError during logout. **Mitigation**: catch the error, print warning, proceed with local-only cleanup.
- **Edge case**: User runs `auth logout` while not logged in. **Mitigation**: print "Not logged in" and exit 0.

## Activity Log

- 2026-04-09T19:38:38Z – claude:opus-4-6:python-implementer:implementer – shell_pid=76066 – Started implementation via action command
