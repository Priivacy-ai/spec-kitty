---
work_package_id: WP04
title: Browser Login Flow (`auth login`)
dependencies:
- WP01
- WP02
requirement_refs:
- FR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
- T027
history: []
authoritative_surface: src/specify_cli/auth/flows/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/auth.py
- src/specify_cli/cli/commands/_auth_login.py
- src/specify_cli/auth/flows/__init__.py
- src/specify_cli/auth/flows/authorization_code.py
- src/specify_cli/auth/flows/refresh.py
- tests/cli/commands/test_auth_login.py
- tests/auth/test_authorization_code_flow.py
- tests/auth/test_refresh_flow.py
status: pending
tags: []
agent: "claude:opus-4-6:python-implementer:implementer"
shell_pid: "40434"
---

# WP04: Browser Login Flow (`auth login`)

**Objective**: REPLACE the existing `spec-kitty auth login` command with the
browser-mediated OAuth Authorization Code + PKCE flow. Set up the deferred-
import dispatch shell pattern for `cli/commands/auth.py` so that WP06 (logout)
and WP07 (status) can plug in their own `_auth_<command>.py` modules without
file overlap. Build the `AuthorizationCodeFlow` orchestrator and the
`TokenRefreshFlow` that TokenManager calls during refresh.

**Context**: This is the user-facing primary login command. The previous run
ADDED a parallel `oauth-login` command, leaving both old and new auth
systems coexisting. This run REPLACES the existing `login` command body in
place. After this WP, `spec-kitty auth login` IS the browser PKCE flow.

**CRITICAL**: T020 must DELETE the existing `login()` Typer command body in
`cli/commands/auth.py` (the one that calls `AuthClient.oauth_login()`). It
must REMOVE the imports of `AuthClient`, `CredentialStore`,
`read_queue_scope_from_credentials`, etc. The new `auth.py` is a deferred-
import dispatch shell.

**Acceptance Criteria**:
- [ ] `cli/commands/auth.py` no longer imports `AuthClient` or `CredentialStore`
- [ ] `spec-kitty auth login --help` does NOT mention username or password
- [ ] `spec-kitty auth login` opens the browser to the SaaS authorize endpoint
- [ ] On successful callback, the session is persisted via `TokenManager.set_session()`
- [ ] On failure (timeout, validation, network), a clear actionable error message is shown and exit code is non-zero
- [ ] `--force` flag triggers re-authentication even if already logged in
- [ ] `--headless` flag dispatches to `DeviceCodeFlow` via lazy import (raises NotImplementedError until WP05 lands)
- [ ] `AuthorizationCodeFlow.login()` returns a `StoredSession` ready for `TokenManager.set_session()`
- [ ] `TokenRefreshFlow.refresh(session)` returns an updated session with new tokens
- [ ] All unit + CliRunner tests pass

---

## Subtask Guidance

### T020: REWRITE `cli/commands/auth.py` as deferred-import dispatch shell

**Purpose**: Remove the legacy password-based `login`/`logout`/`status`
implementations and replace with thin Typer command wrappers that defer to
per-command modules.

**Verified current state of `src/specify_cli/cli/commands/auth.py`** (read on
2026-04-09 from the actual repo at `f0663139`):

The existing `login()` Typer command at line ~68 declares:
```python
@app.command()
def login(
    username: str | None = typer.Option(None, "--username", "-u", help="Your username or email"),
    password: str | None = typer.Option(
        None,
        "--password",
        "-p",
        hide_input=True,
        help="Your password",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Re-authenticate even if already logged in"),
) -> None:
    """Log in to the sync service."""
    if not is_saas_sync_enabled():
        ...
    if not username:
        username = typer.prompt("Username")
    if not password:
        password = typer.prompt("Password", hide_input=True)
    # ... constructs AuthClient(...) and calls obtain_tokens(username, password)
```

The file currently imports:
- `AuthClient`, `AuthenticationError` from `specify_cli.sync.auth`
- `is_saas_sync_enabled`, `saas_sync_disabled_message`, `SAAS_SYNC_ENV_VAR` (config helpers)
- `read_queue_scope_from_credentials`, `write_active_scope`, `read_active_scope` (account-switch helpers)
- `pending_events_for_scope` (queue helper)

**T020's job**: DELETE all of those imports and DELETE the entire body of
`login()`, `logout()`, and `status()` (which currently uses `AuthClient` similarly).
Replace each command with a deferred-import dispatch shell that calls into
the per-command implementation modules.

**Steps**:

1. Read the current `src/specify_cli/cli/commands/auth.py` (cited above)

2. REPLACE the entire file with a deferred-import dispatch shell:
   ```python
   """spec-kitty auth — OAuth login, logout, and status.

   This module is a thin Typer command shell. The actual implementation of
   each command lives in a sibling _auth_<name>.py module that is imported
   lazily when the command is invoked. This separation allows different work
   packages to own different commands without file conflicts.
   """
   from __future__ import annotations
   import asyncio
   import typer
   from rich.console import Console

   app = typer.Typer(name="auth", help="Authenticate with spec-kitty SaaS.")
   console = Console()


   @app.command()
   def login(
       headless: bool = typer.Option(
           False,
           "--headless",
           help="Use device authorization flow (for SSH or no-browser environments).",
       ),
       force: bool = typer.Option(
           False,
           "--force",
           "-f",
           help="Re-authenticate even if already logged in.",
       ),
   ) -> None:
       """Log in to spec-kitty SaaS via browser OAuth (or device flow with --headless)."""
       from specify_cli.cli.commands._auth_login import login_impl
       try:
           asyncio.run(login_impl(headless=headless, force=force))
       except KeyboardInterrupt:
           console.print("\n[yellow]Login cancelled by user.[/yellow]")
           raise typer.Exit(130)


   @app.command()
   def logout(
       force: bool = typer.Option(
           False,
           "--force",
           help="Skip server revocation; only delete local credentials.",
       ),
   ) -> None:
       """Log out and revoke the current session."""
       from specify_cli.cli.commands._auth_logout import logout_impl
       try:
           asyncio.run(logout_impl(force=force))
       except KeyboardInterrupt:
           console.print("\n[yellow]Logout cancelled.[/yellow]")
           raise typer.Exit(130)


   @app.command()
   def status() -> None:
       """Show current authentication status."""
       from specify_cli.cli.commands._auth_status import status_impl
       status_impl()
   ```

3. The lazy `from ... import ... impl` lines mean the WP06/WP07 modules don't
   need to exist when WP04 lands. The Typer command registration happens when
   the file is imported (at CLI startup), but the impl modules are only
   imported when the command is actually invoked.

4. Verify the module imports cleanly:
   ```bash
   python -c "from specify_cli.cli.commands.auth import app; print(app.info.name)"
   # Should print: auth
   ```

5. Verify NO references to legacy classes remain:
   ```bash
   grep -E 'AuthClient|CredentialStore|read_queue_scope|saas_sync' src/specify_cli/cli/commands/auth.py
   # Should return nothing
   ```

**Files**: `src/specify_cli/cli/commands/auth.py` (REWRITE, ~80 lines)

**Validation**:
- [ ] File imports cleanly
- [ ] No legacy imports remain
- [ ] Three Typer commands registered: login, logout, status
- [ ] `spec-kitty auth login --help` shows the new flag set

---

### T021: Create `cli/commands/_auth_login.py` with login_impl + --headless branch

**Purpose**: The actual implementation of the login command, called by the
dispatch shell.

**Steps**:

1. Create `src/specify_cli/cli/commands/_auth_login.py`:
   ```python
   """Implementation of `spec-kitty auth login`. Owned by WP04.

   The --headless branch lazy-imports DeviceCodeFlow which is provided by WP05.
   Until WP05 ships, the --headless branch will fail at import with a clear
   error message.
   """
   from __future__ import annotations
   import logging
   from rich.console import Console
   import typer
   from specify_cli.auth import (
       get_token_manager,
       AuthenticationError,
       NotAuthenticatedError,
       CallbackTimeoutError,
       CallbackValidationError,
       BrowserLaunchError,
       ConfigurationError,
   )
   from specify_cli.auth.config import get_saas_base_url

   log = logging.getLogger(__name__)
   console = Console()


   async def login_impl(*, headless: bool, force: bool) -> None:
       """Run the login flow. Called by cli.commands.auth.login."""
       try:
           saas_url = get_saas_base_url()
       except ConfigurationError as exc:
           console.print(f"[red]✗ {exc}[/red]")
           raise typer.Exit(1) from exc

       tm = get_token_manager()

       if tm.is_authenticated and not force:
           session = tm.get_current_session()
           console.print(f"[green]✓ Already logged in as {session.email}[/green]")
           console.print("Run [bold]spec-kitty auth login --force[/bold] to re-authenticate, or [bold]spec-kitty auth logout[/bold] first.")
           return

       if force and tm.is_authenticated:
           console.print("[dim]Forcing re-authentication...[/dim]")
           tm.clear_session()

       if headless:
           await _run_device_flow(tm, saas_url)
       else:
           await _run_browser_flow(tm, saas_url)


   async def _run_browser_flow(tm, saas_url: str) -> None:
       """Run the browser-based OAuth Authorization Code + PKCE flow."""
       from specify_cli.auth.flows.authorization_code import AuthorizationCodeFlow

       console.print(f"Opening browser for OAuth authentication...")
       console.print(f"[dim]SaaS: {saas_url}[/dim]")

       flow = AuthorizationCodeFlow(saas_base_url=saas_url)

       try:
           session = await flow.login()
       except CallbackTimeoutError:
           console.print("[red]✗ Authentication timed out (5 minutes elapsed)[/red]")
           console.print("Run [bold]spec-kitty auth login[/bold] again.")
           raise typer.Exit(1)
       except CallbackValidationError as exc:
           console.print(f"[red]✗ Callback validation failed: {exc}[/red]")
           console.print("This may indicate a CSRF attack. Run [bold]spec-kitty auth login[/bold] again.")
           raise typer.Exit(1)
       except BrowserLaunchError as exc:
           console.print(f"[red]✗ Could not launch browser: {exc}[/red]")
           console.print("Try [bold]spec-kitty auth login --headless[/bold] instead.")
           raise typer.Exit(1)
       except AuthenticationError as exc:
           console.print(f"[red]✗ Authentication failed: {exc}[/red]")
           raise typer.Exit(1)

       tm.set_session(session)
       _print_success(session)


   async def _run_device_flow(tm, saas_url: str) -> None:
       """Run the device authorization flow (RFC 8628)."""
       try:
           # Lazy import: WP05 ships this module
           from specify_cli.auth.flows.device_code import DeviceCodeFlow
       except ImportError as exc:
           console.print(
               "[red]✗ Headless login is not yet implemented (waiting on WP05).[/red]"
           )
           raise typer.Exit(1) from exc

       flow = DeviceCodeFlow(saas_base_url=saas_url)

       try:
           session = await flow.login(progress_writer=console.print)
       except AuthenticationError as exc:
           console.print(f"[red]✗ Device flow failed: {exc}[/red]")
           raise typer.Exit(1)

       tm.set_session(session)
       _print_success(session)


   def _print_success(session) -> None:
       """Print the post-login success message."""
       console.print()
       console.print(f"[green]✓ Authenticated as {session.email}[/green]")
       if session.teams:
           default_team = next((t for t in session.teams if t.id == session.default_team_id), None)
           if default_team:
               console.print(f"  Default team: {default_team.name}")
   ```

**Files**: `src/specify_cli/cli/commands/_auth_login.py` (~140 lines)

**Validation**:
- [ ] `from specify_cli.cli.commands._auth_login import login_impl` works
- [ ] `login_impl(headless=False, force=False)` raises NotAuthenticatedError if no env var (or other early error)
- [ ] Test via CliRunner: `runner.invoke(app, ["auth", "login"])` with mocked env

---

### T022: Create `auth/flows/authorization_code.py` (AuthorizationCodeFlow)

**Purpose**: The orchestration class that coordinates loopback callback,
browser launch, code exchange, user info fetch, and session creation.

**Steps**:

1. Create `src/specify_cli/auth/flows/__init__.py`:
   ```python
   from __future__ import annotations
   from .authorization_code import AuthorizationCodeFlow
   from .refresh import TokenRefreshFlow

   __all__ = ["AuthorizationCodeFlow", "TokenRefreshFlow"]
   ```

2. Create `src/specify_cli/auth/flows/authorization_code.py`:
   ```python
   from __future__ import annotations
   import logging
   from datetime import datetime, timedelta, timezone
   from urllib.parse import urlencode
   import httpx
   from ..session import StoredSession, Team
   from ..loopback.callback_server import CallbackServer
   from ..loopback.callback_handler import CallbackHandler
   from ..loopback.state_manager import StateManager
   from ..loopback.browser_launcher import BrowserLauncher
   from ..secure_storage import SecureStorage
   from ..errors import (
       AuthenticationError,
       CallbackError,
       BrowserLaunchError,
       NetworkError,
   )

   log = logging.getLogger(__name__)


   class AuthorizationCodeFlow:
       """Orchestrates the OAuth Authorization Code + PKCE flow."""

       def __init__(self, saas_base_url: str, client_id: str = "cli_native") -> None:
           self._saas_base_url = saas_base_url
           self._client_id = client_id
           self._state_manager = StateManager()

       async def login(self) -> StoredSession:
           """Execute the full browser-based login flow.

           Returns: a StoredSession ready for TokenManager.set_session()
           Raises: subclasses of AuthenticationError on failure
           """
           pkce_state = self._state_manager.generate()
           callback_server = CallbackServer()

           try:
               callback_url = callback_server.start()

               auth_url = self._build_auth_url(pkce_state, callback_url)
               if not BrowserLauncher.launch(auth_url):
                   raise BrowserLaunchError(
                       f"No browser available. Please visit:\n  {auth_url}"
                   )

               callback_params = await callback_server.wait_for_callback()
           finally:
               callback_server.stop()

           self._state_manager.validate_not_expired(pkce_state)

           handler = CallbackHandler(pkce_state.state)
           code, _ = handler.validate(callback_params)

           tokens = await self._exchange_code(code, pkce_state.code_verifier, callback_url)
           session = await self._build_session(tokens)
           return session

       def _build_auth_url(self, pkce_state, callback_url: str) -> str:
           params = {
               "client_id": self._client_id,
               "redirect_uri": callback_url,
               "response_type": "code",
               "scope": "offline_access",
               "code_challenge": pkce_state.code_challenge,
               "code_challenge_method": pkce_state.code_challenge_method,
               "state": pkce_state.state,
           }
           return f"{self._saas_base_url}/oauth/authorize?{urlencode(params)}"

       async def _exchange_code(self, code: str, code_verifier: str, redirect_uri: str) -> dict:
           """POST /oauth/token with the authorization code. See T024."""
           # Implementation in T024
           ...

       async def _build_session(self, tokens: dict) -> StoredSession:
           """Fetch user info and assemble StoredSession. See T025."""
           # Implementation in T025
           ...
   ```

3. The `_exchange_code` and `_build_session` methods are stubs here; T024
   and T025 implement them.

**Files**: `src/specify_cli/auth/flows/__init__.py` (~10 lines), `src/specify_cli/auth/flows/authorization_code.py` (~120 lines initially, grows in T024/T025)

**Validation**:
- [ ] `from specify_cli.auth.flows import AuthorizationCodeFlow` works
- [ ] `flow.login()` raises BrowserLaunchError when no browser is available
- [ ] `_build_auth_url` produces a valid URL with all required PKCE params

---

### T023: Create `auth/flows/refresh.py` (TokenRefreshFlow)

**Purpose**: The refresh flow used by TokenManager to renew an access token.

**Steps**:

1. Create `src/specify_cli/auth/flows/refresh.py`:
   ```python
   from __future__ import annotations
   import logging
   from datetime import datetime, timedelta, timezone
   import httpx
   from ..config import get_saas_base_url
   from ..session import StoredSession
   from ..errors import (
       TokenRefreshError,
       RefreshTokenExpiredError,
       SessionInvalidError,
       NetworkError,
   )

   log = logging.getLogger(__name__)


   class TokenRefreshFlow:
       """Refreshes an expired access token using the refresh_token grant."""

       async def refresh(self, session: StoredSession) -> StoredSession:
           """POST /oauth/token with grant_type=refresh_token.

           Returns: an updated StoredSession with new tokens.
           Raises:
               RefreshTokenExpiredError if SaaS rejects the refresh token
               SessionInvalidError if SaaS reports session_invalid
               TokenRefreshError on other failures
           """
           saas_url = get_saas_base_url()
           url = f"{saas_url}/oauth/token"
           data = {
               "grant_type": "refresh_token",
               "refresh_token": session.refresh_token,
               "client_id": "cli_native",
           }
           async with httpx.AsyncClient(timeout=10.0) as client:
               try:
                   response = await client.post(url, data=data)
               except httpx.RequestError as exc:
                   raise NetworkError(f"Network error during refresh: {exc}") from exc

           if response.status_code == 200:
               return self._update_session(session, response.json())

           if response.status_code == 400:
               body = response.json()
               error = body.get("error", "")
               if error == "invalid_grant":
                   raise RefreshTokenExpiredError(
                       "Refresh token is invalid or expired. Run `spec-kitty auth login` again."
                   )
               if error == "session_invalid":
                   raise SessionInvalidError(
                       "Session has been invalidated server-side. Run `spec-kitty auth login` again."
                   )

           raise TokenRefreshError(
               f"Token refresh failed: HTTP {response.status_code} — {response.text}"
           )

       def _update_session(self, session: StoredSession, tokens: dict) -> StoredSession:
           """Build an updated session from a refresh response.

           Per C-012 (LANDED 2026-04-09), refresh_token_expires_at is read
           directly from the SaaS token response on every refresh. The CLI
           never hardcodes a TTL and never computes the timestamp locally.
           """
           now = datetime.now(timezone.utc)
           new_access = tokens["access_token"]
           new_refresh = tokens.get("refresh_token", session.refresh_token)  # May not rotate
           expires_in = int(tokens.get("expires_in", 3600))

           # Refresh expiry: read directly from the SaaS response (landed
           # 2026-04-09). Prefer `refresh_token_expires_at` (absolute, no
           # clock math), fall back to `refresh_token_expires_in` (seconds).
           refresh_expires_at_raw = tokens.get("refresh_token_expires_at")
           if refresh_expires_at_raw is not None:
               refresh_token_expires_at = datetime.fromisoformat(
                   refresh_expires_at_raw.replace("Z", "+00:00")
               )
           else:
               refresh_expires_in = int(tokens["refresh_token_expires_in"])
               refresh_token_expires_at = now + timedelta(seconds=refresh_expires_in)

           return StoredSession(
               user_id=session.user_id,
               email=session.email,
               name=session.name,
               teams=session.teams,
               default_team_id=session.default_team_id,
               access_token=new_access,
               refresh_token=new_refresh,
               session_id=session.session_id,
               issued_at=now,
               access_token_expires_at=now + timedelta(seconds=expires_in),
               refresh_token_expires_at=refresh_token_expires_at,
               scope=tokens.get("scope", session.scope),
               storage_backend=session.storage_backend,
               last_used_at=now,
               auth_method=session.auth_method,
           )
   ```

**Files**: `src/specify_cli/auth/flows/refresh.py` (~110 lines)

**Validation**:
- [ ] Mock httpx response 200 → returns updated session
- [ ] Mock 400 with `invalid_grant` → raises RefreshTokenExpiredError
- [ ] Mock 400 with `session_invalid` → raises SessionInvalidError
- [ ] Mock network failure → raises NetworkError

---

### T024: Implement token exchange helper (POST /oauth/token + code)

**Purpose**: Fill in `AuthorizationCodeFlow._exchange_code()`.

**Steps**:

1. Add to `src/specify_cli/auth/flows/authorization_code.py`:
   ```python
   async def _exchange_code(self, code: str, code_verifier: str, redirect_uri: str) -> dict:
       url = f"{self._saas_base_url}/oauth/token"
       data = {
           "grant_type": "authorization_code",
           "code": code,
           "redirect_uri": redirect_uri,
           "client_id": self._client_id,
           "code_verifier": code_verifier,
       }
       async with httpx.AsyncClient(timeout=10.0) as client:
           try:
               response = await client.post(url, data=data)
           except httpx.RequestError as exc:
               raise NetworkError(f"Network error during code exchange: {exc}") from exc
       if response.status_code != 200:
           body = response.text
           raise AuthenticationError(
               f"Token exchange failed: HTTP {response.status_code} — {body}"
           )
       tokens = response.json()
       required = ("access_token", "refresh_token", "expires_in", "session_id")
       missing = [k for k in required if k not in tokens]
       if missing:
           raise AuthenticationError(
               f"Token response missing required fields: {missing}"
           )
       return tokens
   ```

**Files**: included in `auth/flows/authorization_code.py`

**Validation**:
- [ ] Successful exchange returns the parsed JSON dict
- [ ] Missing fields raise AuthenticationError
- [ ] Network errors raise NetworkError

---

### T025: Implement user info fetch (GET /api/v1/me + StoredSession build)

**Purpose**: Fill in `AuthorizationCodeFlow._build_session()`.

**Steps**:

1. Add to `src/specify_cli/auth/flows/authorization_code.py`:
   ```python
   async def _build_session(self, tokens: dict) -> StoredSession:
       """Fetch user info from /api/v1/me and assemble StoredSession.

       SaaS contract (from protected-endpoints.md GET /api/v1/me):
           returns: user_id, email, name, teams[], session_id, authenticated_at,
                    access_token_expires_at, refresh_token_expires_at, auth_flow

       NOTE: SaaS does NOT return `default_team_id` — the CLI picks the default
       on first login (teams[0].id) and persists it locally. A future mission
       can add `spec-kitty auth set-default-team` to let the user override.

       NOTE: `refresh_token_expires_at` is REQUIRED as of the 2026-04-09 SaaS
       amendment (LANDED — see contracts/saas-amendment-refresh-ttl.md). The
       CLI reads it directly from the token response (preferred) or from
       /api/v1/me, and stores the server-supplied datetime verbatim. Per
       C-012, the CLI never hardcodes or locally computes a refresh TTL.
       """
       url = f"{self._saas_base_url}/api/v1/me"
       headers = {"Authorization": f"Bearer {tokens['access_token']}"}
       async with httpx.AsyncClient(timeout=10.0) as client:
           try:
               response = await client.get(url, headers=headers)
           except httpx.RequestError as exc:
               raise NetworkError(f"Network error fetching user info: {exc}") from exc
       if response.status_code != 200:
           raise AuthenticationError(
               f"User info fetch failed: HTTP {response.status_code}"
           )
       me = response.json()

       teams = [
           Team(id=t["id"], name=t["name"], role=t["role"])
           for t in me.get("teams", [])
       ]
       if not teams:
           raise AuthenticationError(
               "User has no team memberships. Contact your administrator."
           )
       # Client-picked default: SaaS does not return default_team_id
       default_team_id = teams[0].id

       now = datetime.now(timezone.utc)
       expires_in = int(tokens["expires_in"])

       # Refresh expiry: always read directly from the SaaS response
       # (landed 2026-04-09). Prefer the absolute timestamp, fall back to
       # the seconds field if the server omits the absolute form. Never
       # store None — the contract now guarantees a concrete value.
       refresh_expires_at_raw = tokens.get("refresh_token_expires_at") or me.get(
           "refresh_token_expires_at"
       )
       if refresh_expires_at_raw is not None:
           refresh_token_expires_at = datetime.fromisoformat(
               refresh_expires_at_raw.replace("Z", "+00:00")
           )
       else:
           refresh_expires_in = int(tokens["refresh_token_expires_in"])
           refresh_token_expires_at = now + timedelta(seconds=refresh_expires_in)

       return StoredSession(
           user_id=me["user_id"],
           email=me["email"],                         # ← from /api/v1/me .email
           name=me.get("name", me["email"]),
           teams=teams,
           default_team_id=default_team_id,
           access_token=tokens["access_token"],
           refresh_token=tokens["refresh_token"],
           session_id=tokens["session_id"],
           issued_at=now,
           access_token_expires_at=now + timedelta(seconds=expires_in),
           refresh_token_expires_at=refresh_token_expires_at,  # always set
           scope=tokens.get("scope", "offline_access"),
           storage_backend="keychain",  # Will be overwritten by storage backend
           last_used_at=now,
           auth_method="authorization_code",
       )
   ```

**Files**: included in `auth/flows/authorization_code.py`

**Validation**:
- [ ] User with teams: returns valid StoredSession
- [ ] User with no teams: raises AuthenticationError
- [ ] 401 from /api/v1/me: raises AuthenticationError
- [ ] Network error: raises NetworkError

---

### T026: Wire TokenManager.set_session(); verify legacy login body removed

**Purpose**: Final wiring + verification that the legacy code is gone.

**Steps**:

1. Verify `_auth_login.py` calls `tm.set_session(session)` after successful login.
2. Verify `_auth_login.py` calls `tm.clear_session()` when `--force` is set.
3. Verify the storage_backend in the StoredSession matches the actual backend
   used by the TokenManager. Update `_build_session()` to read it from
   `tm._storage.backend_name` (passed in via constructor or set after).
4. Run grep verification:
   ```bash
   grep -E 'AuthClient|CredentialStore|read_queue_scope|saas_sync_disabled_message|SAAS_SYNC_ENV_VAR' \
       src/specify_cli/cli/commands/auth.py
   # Should return nothing
   ```
5. Run import smoke test:
   ```bash
   python -c "from specify_cli.cli.commands.auth import app, login, logout, status"
   # Should succeed
   ```

**Files**: minor edits to `_auth_login.py` and `authorization_code.py`

**Validation**:
- [ ] Grep returns nothing
- [ ] Import smoke test passes

---

### T027: Write unit + CliRunner tests for WP04

**Purpose**: Coverage of the flow class and the CLI command.

**Steps**:

1. `tests/auth/test_authorization_code_flow.py`: unit tests for AuthorizationCodeFlow with mocked CallbackServer, BrowserLauncher, and httpx.
2. `tests/auth/test_refresh_flow.py`: unit tests for TokenRefreshFlow with mocked httpx.
3. `tests/cli/commands/test_auth_login.py`:
   ```python
   import pytest
   from unittest.mock import AsyncMock, patch
   from typer.testing import CliRunner
   from specify_cli.cli.commands.auth import app
   from specify_cli.auth import reset_token_manager

   runner = CliRunner()


   @pytest.fixture(autouse=True)
   def _reset_tm(monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
       reset_token_manager()
       yield
       reset_token_manager()


   class TestAuthLoginCommand:

       def test_help_does_not_mention_password(self):
           result = runner.invoke(app, ["login", "--help"])
           assert result.exit_code == 0
           assert "password" not in result.stdout.lower()
           assert "username" not in result.stdout.lower()

       @patch("specify_cli.cli.commands._auth_login._run_browser_flow", new_callable=AsyncMock)
       def test_login_browser_path(self, mock_browser):
           result = runner.invoke(app, ["login"])
           assert mock_browser.called
           assert result.exit_code == 0

       @patch("specify_cli.cli.commands._auth_login._run_device_flow", new_callable=AsyncMock)
       def test_login_headless_path(self, mock_device):
           result = runner.invoke(app, ["login", "--headless"])
           assert mock_device.called
           assert result.exit_code == 0

       def test_login_no_saas_url(self, monkeypatch):
           monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
           result = runner.invoke(app, ["login"])
           assert result.exit_code != 0
           assert "SPEC_KITTY_SAAS_URL" in result.stdout
   ```

**Files**: 3 test files, ~400 lines total

**Validation**:
- [ ] All tests pass
- [ ] CliRunner tests use the real `app` from `specify_cli.cli.commands.auth`
- [ ] Help output explicitly tested for absence of password references

---

## Definition of Done

- [ ] All 8 subtasks completed
- [ ] All unit tests pass
- [ ] `cli/commands/auth.py` no longer references AuthClient or CredentialStore
- [ ] `spec-kitty auth login --help` shows the new flag set with no password references
- [ ] Browser PKCE flow tested end-to-end (with mocked SaaS)
- [ ] `--force` re-authenticates correctly
- [ ] `--headless` dispatches to device flow (gracefully fails until WP05 lands)
- [ ] No tokens or secrets logged

## Reviewer Guidance

- Verify `cli/commands/auth.py` is COMPLETELY rewritten (not just updated)
- Verify the legacy login command body is gone — grep for `AuthClient` returns nothing
- Verify `_auth_login.py` calls `tm.set_session(session)` after successful login
- Verify `_auth_login.py` uses `get_saas_base_url()` and never hardcodes a URL
- Verify the CliRunner test uses the real `app` from the module (not a mock)
- Verify `--headless` raises a clear error if WP05's device_code module is missing

## Risks & Edge Cases

- **Risk**: `asyncio.run` inside Typer command may conflict with already-running loop. **Mitigation**: Typer commands are sync, so `asyncio.run` is safe at that boundary.
- **Risk**: User has multiple browsers and the wrong one opens. **Mitigation**: Print the URL so the user can copy-paste if needed.
- **Edge case**: User cancels with Ctrl+C during callback wait. **Mitigation**: KeyboardInterrupt is caught at the dispatch shell level, prints a message, exits 130.
- **Edge case**: User runs `auth login` while already logged in without `--force`. **Mitigation**: Print "Already logged in as X" and exit 0.

## Activity Log

- 2026-04-09T17:47:22Z – opus:opus:implementer:implementer – shell_pid=7106 – Started implementation via action command
- 2026-04-09T18:08:19Z – opus:opus:implementer:implementer – shell_pid=7106 – Moved to planned
- 2026-04-09T18:08:28Z – opus:opus:implementer:implementer – shell_pid=22177 – Started implementation via action command
- 2026-04-09T18:15:32Z – opus:opus:implementer:implementer – shell_pid=22177 – Moved to planned
- 2026-04-09T18:24:55Z – claude:opus-4-6:python-implementer:implementer – shell_pid=40434 – Started implementation via action command
