---
work_package_id: WP05
title: Headless Login Flow (`auth login --headless`)
dependencies:
- WP01
- WP03
- WP04
requirement_refs:
- FR-002
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
history: []
authoritative_surface: src/specify_cli/auth/flows/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/flows/device_code.py
- tests/auth/test_device_code_flow.py
status: pending
tags: []
---

# WP05: Headless Login Flow (`auth login --headless`)

**Objective**: Implement `DeviceCodeFlow`, the orchestrator for the RFC 8628
Device Authorization Grant. Once this WP ships, WP04's `_auth_login.py`
`--headless` branch (which already exists with a lazy import) becomes fully
functional.

**Context**: WP04 has already wired the `--headless` flag dispatch with a
lazy import: `from specify_cli.auth.flows.device_code import DeviceCodeFlow`.
That import currently raises ImportError because this WP hasn't shipped yet.
After WP05 lands, the lazy import resolves naturally and `spec-kitty auth login --headless`
works.

**WP05 owns ONLY** `src/specify_cli/auth/flows/device_code.py` and
`tests/auth/test_device_code_flow.py`. WP05 does NOT touch
`cli/commands/_auth_login.py` (owned by WP04). The `--headless` branch
in WP04 is correct from day one and needs no changes.

**Acceptance Criteria**:
- [ ] `from specify_cli.auth.flows.device_code import DeviceCodeFlow` works
- [ ] `DeviceCodeFlow.login(progress_writer)` POSTs `/oauth/device`, displays the user code, polls until approval, returns a StoredSession
- [ ] User code is displayed in `ABCD-1234` chunks via `format_user_code()` from WP03
- [ ] Polling uses WP03's `DeviceFlowPoller` and respects the 10-second cap
- [ ] On approval, user info is fetched from `/api/v1/me` and a StoredSession is built
- [ ] On denial, raises `DeviceFlowDenied`
- [ ] On expiry, raises `DeviceFlowExpired`
- [ ] CliRunner test for `spec-kitty auth login --headless` passes (mocking SaaS HTTP)
- [ ] All unit tests pass

---

## Subtask Guidance

### T028: Create `auth/flows/device_code.py` (DeviceCodeFlow)

**Purpose**: The orchestration class for the device authorization flow.

**Steps**:

1. Create `src/specify_cli/auth/flows/device_code.py`:
   ```python
   """RFC 8628 Device Authorization Grant orchestration."""
   from __future__ import annotations
   import logging
   from datetime import datetime, timedelta, timezone
   from typing import Callable, Optional
   import httpx
   from ..session import StoredSession, Team
   from ..device_flow import DeviceFlowPoller, DeviceFlowState, format_user_code
   from ..errors import (
       AuthenticationError,
       DeviceFlowDenied,
       DeviceFlowExpired,
       NetworkError,
   )

   log = logging.getLogger(__name__)


   class DeviceCodeFlow:
       """Orchestrates the OAuth Device Authorization Grant."""

       def __init__(self, saas_base_url: str, client_id: str = "cli_native") -> None:
           self._saas_base_url = saas_base_url
           self._client_id = client_id

       async def login(
           self,
           progress_writer: Optional[Callable[[str], None]] = None,
       ) -> StoredSession:
           """Execute the device authorization flow.

           Args:
               progress_writer: optional callback for displaying progress messages
                   (e.g., `console.print`).

           Returns: a StoredSession ready for TokenManager.set_session()
           """
           writer = progress_writer or (lambda msg: None)

           # Step 1: request device code
           device_state = await self._request_device_code()

           # Step 2: display user code
           writer("")
           writer(f"[yellow]Visit:[/yellow] [bold blue]{device_state.verification_uri}[/bold blue]")
           writer(f"[yellow]Code:[/yellow]  [bold green]{format_user_code(device_state.user_code)}[/bold green]")
           if device_state.verification_uri_complete:
               writer(f"[dim]Or open: {device_state.verification_uri_complete}[/dim]")
           writer("")
           writer(f"[dim]Waiting for authorization (timeout in {device_state.expires_in // 60} minutes)...[/dim]")

           # Step 3: poll until approval
           poller = DeviceFlowPoller(device_state)

           def on_pending(state: DeviceFlowState) -> None:
               # Optional: emit a heartbeat per poll
               pass

           tokens = await poller.poll(self._poll_token_request, on_pending=on_pending)

           # Step 4: build session
           session = await self._build_session(tokens)
           writer("")
           writer(f"[green]✓ Authorization granted[/green]")
           return session

       async def _request_device_code(self) -> DeviceFlowState:
           """POST /oauth/device to request a device code."""
           url = f"{self._saas_base_url}/oauth/device"
           data = {"client_id": self._client_id, "scope": "offline_access"}
           async with httpx.AsyncClient(timeout=10.0) as client:
               try:
                   response = await client.post(url, data=data)
               except httpx.RequestError as exc:
                   raise NetworkError(f"Network error requesting device code: {exc}") from exc
           if response.status_code != 200:
               raise AuthenticationError(
                   f"Device code request failed: HTTP {response.status_code} — {response.text}"
               )
           return DeviceFlowState.from_oauth_response(response.json())

       async def _poll_token_request(self, device_code: str) -> dict:
           """POST /oauth/token with the device_code grant."""
           url = f"{self._saas_base_url}/oauth/token"
           data = {
               "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
               "device_code": device_code,
               "client_id": self._client_id,
           }
           async with httpx.AsyncClient(timeout=10.0) as client:
               try:
                   response = await client.post(url, data=data)
               except httpx.RequestError as exc:
                   raise NetworkError(f"Network error polling for token: {exc}") from exc
           # Both success and pending/error responses are JSON; the poller distinguishes
           if response.status_code in (200, 400):
               return response.json()
           raise AuthenticationError(
               f"Unexpected response from /oauth/token: HTTP {response.status_code}"
           )

       async def _build_session(self, tokens: dict) -> StoredSession:
           """Fetch user info and assemble StoredSession."""
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
               raise AuthenticationError("User has no team memberships.")
           default_team_id = me.get("default_team_id") or teams[0].id

           now = datetime.now(timezone.utc)
           expires_in = int(tokens["expires_in"])
           refresh_ttl = timedelta(days=90)
           return StoredSession(
               user_id=me["user_id"],
               username=me["username"],
               name=me.get("name", me["username"]),
               teams=teams,
               default_team_id=default_team_id,
               access_token=tokens["access_token"],
               refresh_token=tokens["refresh_token"],
               session_id=tokens["session_id"],
               issued_at=now,
               access_token_expires_at=now + timedelta(seconds=expires_in),
               refresh_token_expires_at=now + refresh_ttl,
               scope=tokens.get("scope", "offline_access"),
               storage_backend="keychain",  # Will be set by TokenManager
               last_used_at=now,
               auth_method="device_code",
           )
   ```

2. Note that `_build_session()` is essentially identical to
   `AuthorizationCodeFlow._build_session()` from WP04. Refactoring to a
   shared helper is a follow-up — for this WP, duplication is acceptable
   (the two flows are owned by different WPs).

**Files**: `src/specify_cli/auth/flows/device_code.py` (~180 lines)

**Validation**:
- [ ] Module imports cleanly
- [ ] `flow.login()` returns a StoredSession with `auth_method="device_code"`

---

### T029: Implement device code request helper

**Purpose**: Already implemented in T028 as `_request_device_code()`. T029 is
about edge cases and validation.

**Steps**:

1. Verify the request includes `scope=offline_access` (per spec C-005).
2. Verify the response is parsed via `DeviceFlowState.from_oauth_response()`.
3. Add error handling for malformed responses (missing `device_code`, missing `interval`).

**Files**: included in T028

**Validation**:
- [ ] Mock SaaS returning a valid device code response → DeviceFlowState
- [ ] Mock SaaS returning a 400 error → AuthenticationError
- [ ] Mock SaaS returning a 200 with missing `device_code` → KeyError or parse error

---

### T030: Wire user info fetch; build StoredSession on approval

**Purpose**: Already implemented in T028 as `_build_session()`. T030 is about
verification.

**Steps**:

1. Verify the user info fetch uses the bearer token from the device flow approval.
2. Verify the resulting StoredSession has `auth_method="device_code"` (NOT `authorization_code`).
3. Verify the storage_backend field is set correctly (from WP01).

**Files**: included in T028

**Validation**:
- [ ] StoredSession.auth_method == "device_code"
- [ ] StoredSession contains all required fields

---

### T031: Write unit tests for DeviceCodeFlow

**Purpose**: Coverage of the flow class with mocked HTTP and poller.

**Steps**:

1. `tests/auth/test_device_code_flow.py`:
   ```python
   import pytest
   from datetime import datetime, timedelta, timezone
   from unittest.mock import AsyncMock, patch
   from specify_cli.auth.flows.device_code import DeviceCodeFlow
   from specify_cli.auth.errors import (
       DeviceFlowDenied,
       DeviceFlowExpired,
       AuthenticationError,
       NetworkError,
   )


   _SAAS = "https://saas.test"


   def _device_response():
       return {
           "device_code": "dc_xyz",
           "user_code": "ABCD-1234",
           "verification_uri": f"{_SAAS}/device",
           "expires_in": 900,
           "interval": 0,  # 0s for fast tests
       }


   def _token_response():
       return {
           "access_token": "at_xyz",
           "refresh_token": "rt_xyz",
           "expires_in": 3600,
           "scope": "offline_access",
           "session_id": "sess_xyz",
       }


   def _me_response():
       return {
           "user_id": "u_alice",
           "username": "alice@example.com",
           "name": "Alice Developer",
           "teams": [{"id": "tm_acme", "name": "Acme", "role": "admin"}],
           "default_team_id": "tm_acme",
       }


   class _MockResponse:
       def __init__(self, status_code: int, json_body: dict):
           self.status_code = status_code
           self._json = json_body
           self.text = str(json_body)
       def json(self):
           return self._json


   @pytest.mark.asyncio
   class TestDeviceCodeFlow:

       async def test_full_happy_path(self):
           flow = DeviceCodeFlow(saas_base_url=_SAAS)
           # Mock httpx for both _request_device_code and _build_session
           call_log = []
           async def mock_post(url, data=None, headers=None):
               call_log.append(url)
               if url.endswith("/oauth/device"):
                   return _MockResponse(200, _device_response())
               if url.endswith("/oauth/token"):
                   return _MockResponse(200, _token_response())
               raise AssertionError(f"Unexpected POST: {url}")
           async def mock_get(url, headers=None):
               call_log.append(url)
               if url.endswith("/api/v1/me"):
                   return _MockResponse(200, _me_response())
               raise AssertionError(f"Unexpected GET: {url}")
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               instance.get = mock_get
               session = await flow.login()
           assert session.user_id == "u_alice"
           assert session.auth_method == "device_code"
           assert any("/oauth/device" in u for u in call_log)
           assert any("/oauth/token" in u for u in call_log)
           assert any("/api/v1/me" in u for u in call_log)

       async def test_user_denial(self):
           flow = DeviceCodeFlow(saas_base_url=_SAAS)
           async def mock_post(url, data=None, headers=None):
               if url.endswith("/oauth/device"):
                   return _MockResponse(200, _device_response())
               if url.endswith("/oauth/token"):
                   return _MockResponse(400, {"error": "access_denied"})
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               with pytest.raises(DeviceFlowDenied):
                   await flow.login()

       async def test_expired_token(self):
           flow = DeviceCodeFlow(saas_base_url=_SAAS)
           async def mock_post(url, data=None, headers=None):
               if url.endswith("/oauth/device"):
                   return _MockResponse(200, _device_response())
               if url.endswith("/oauth/token"):
                   return _MockResponse(400, {"error": "expired_token"})
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               with pytest.raises(DeviceFlowExpired):
                   await flow.login()

       async def test_device_request_fails(self):
           flow = DeviceCodeFlow(saas_base_url=_SAAS)
           async def mock_post(url, data=None, headers=None):
               return _MockResponse(500, {"error": "server_error"})
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               with pytest.raises(AuthenticationError):
                   await flow.login()
   ```

**Files**: `tests/auth/test_device_code_flow.py` (~250 lines)

**Validation**:
- [ ] All test cases pass
- [ ] Mocking strategy isolates the test from real network

---

### T032: Add CliRunner test for `spec-kitty auth login --headless`

**Purpose**: Verify that the CLI command actually invokes the device flow
end-to-end via the dispatch shell.

**Steps**:

1. Add to `tests/auth/test_device_code_flow.py` (in WP05's owned file, NOT
   in WP04's `tests/cli/commands/test_auth_login.py`):
   ```python
   class TestAuthLoginHeadlessCliRunner:
       """End-to-end CliRunner test for `spec-kitty auth login --headless`."""

       def test_headless_login_via_clirunner(self, monkeypatch):
           from typer.testing import CliRunner
           from specify_cli.cli.commands.auth import app
           from specify_cli.auth import reset_token_manager
           reset_token_manager()
           monkeypatch.setenv("SPEC_KITTY_SAAS_URL", _SAAS)
           runner = CliRunner()

           # Mock httpx so the actual HTTP calls don't go out
           async def mock_post(url, data=None, headers=None):
               if url.endswith("/oauth/device"):
                   return _MockResponse(200, _device_response())
               if url.endswith("/oauth/token"):
                   return _MockResponse(200, _token_response())
           async def mock_get(url, headers=None):
               if url.endswith("/api/v1/me"):
                   return _MockResponse(200, _me_response())

           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               instance.get = mock_get
               # Also mock the storage backend so we don't write to keychain
               with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
                   mock_storage = mock_se.return_value
                   mock_storage.read.return_value = None
                   mock_storage.write = lambda s: None
                   mock_storage.delete = lambda: None
                   mock_storage.backend_name = "file"
                   reset_token_manager()
                   result = runner.invoke(app, ["login", "--headless"])

           assert result.exit_code == 0, f"stdout: {result.stdout}"
           assert "Authenticated" in result.stdout or "alice" in result.stdout.lower()
   ```

2. This test exercises the full path: CLI dispatch → `_auth_login.login_impl`
   → `_run_device_flow` → `DeviceCodeFlow.login` → mocked HTTP → returned
   StoredSession → `tm.set_session()`. It verifies the dispatch shell from WP04
   actually wires up correctly with WP05's flow class.

3. Importantly, this test imports BOTH `CliRunner` and `DeviceCodeFlow`, so
   the WP11 audit (T063) recognizes it as a valid integration test.

**Files**: included in `tests/auth/test_device_code_flow.py`

**Validation**:
- [ ] CliRunner test passes
- [ ] Test imports `CliRunner` (passes WP11's T063 audit)
- [ ] Test does not call any flow class directly outside of mocked context

---

## Definition of Done

- [ ] All 5 subtasks completed
- [ ] All unit tests pass
- [ ] CliRunner test for `--headless` passes
- [ ] DeviceCodeFlow returns StoredSession with `auth_method="device_code"`
- [ ] User code displayed in chunked format
- [ ] No tokens or secrets logged

## Reviewer Guidance

- Verify WP05 does NOT touch `cli/commands/_auth_login.py` (would conflict with WP04)
- Verify the CliRunner test imports `CliRunner` AND `DeviceCodeFlow` (so WP11's T063 audit passes)
- Verify `auth_method="device_code"` in the resulting session
- Verify the device endpoint POST includes `scope=offline_access`
- Verify the polling uses WP03's `DeviceFlowPoller`, not a hand-rolled loop

## Risks & Edge Cases

- **Risk**: SaaS device endpoint returns `verification_uri_complete` (not standard) → not all clients support it. **Mitigation**: optional field; we display it as a "Or open" hint.
- **Risk**: User reads the wrong code from the terminal. **Mitigation**: format with hyphens for readability; print in bold green.
- **Edge case**: User approves between polls but the next poll happens to fail with a network error. **Mitigation**: poller retries on NetworkError.
