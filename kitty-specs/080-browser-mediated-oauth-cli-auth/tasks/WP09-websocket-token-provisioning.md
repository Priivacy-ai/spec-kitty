---
work_package_id: WP09
title: WebSocket Pre-Connect Token Provisioning
dependencies:
- WP01
requirement_refs:
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T048
- T049
- T050
- T051
history: []
authoritative_surface: src/specify_cli/auth/websocket/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/websocket/**
- tests/auth/test_websocket_provisioning.py
status: pending
tags: []
agent: "opus:opus:implementer:implementer"
shell_pid: "67527"
---

# WP09: WebSocket Pre-Connect Token Provisioning

**Objective**: Build the `auth/websocket/` package that obtains ephemeral
WebSocket tokens via `/api/v1/ws-token`. The CLI calls this just before
opening a WebSocket connection — the ephemeral token is then passed as a
query parameter on the WS upgrade.

**Context**: The SaaS WebSocket endpoint requires a separate ephemeral
token (1-hour TTL) issued via REST. The flow is:
1. Refresh access token if it expires within 5 minutes (NFR-005 buffer)
2. POST `/api/v1/ws-token` with bearer token + team_id
3. Receive `{ws_token, ws_url, expires_in}`
4. Open WS connection at `ws_url?token=<ws_token>`

WP09 owns ONLY the new `auth/websocket/` package. The integration into
`sync/client.py` (where the WS connection is actually opened) is handled by
WP08. WP08 depends on WP09 because WP08 needs WP09's `provision_ws_token`
function to exist before it can rewire the WS code path.

**Acceptance Criteria**:
- [ ] `from specify_cli.auth.websocket import provision_ws_token` works
- [ ] `provision_ws_token(team_id)` returns `{ws_token, ws_url, expires_in, session_id}` dict
- [ ] Pre-connect refresh: if access token expires within 300 seconds, refresh first
- [ ] 403 response (not team member): raise `WebSocketProvisioningError("Not a member of team X")`
- [ ] 404 response (team not found): raise `WebSocketProvisioningError("Team X not found")`
- [ ] 5xx response: raise `WebSocketProvisioningError` with HTTP status
- [ ] Network error: raise `NetworkError`
- [ ] All unit tests pass

---

## Subtask Guidance

### T048: Create `auth/websocket/__init__.py` exporting `provision_ws_token`

**Purpose**: The public surface for the package.

**Steps**:

1. Create `src/specify_cli/auth/websocket/__init__.py`:
   ```python
   """WebSocket pre-connect token provisioning for spec-kitty SaaS."""
   from __future__ import annotations
   from .token_provisioning import (
       provision_ws_token,
       WebSocketTokenProvisioner,
       WebSocketProvisioningError,
   )

   __all__ = [
       "provision_ws_token",
       "WebSocketTokenProvisioner",
       "WebSocketProvisioningError",
   ]
   ```

2. The error class `WebSocketProvisioningError` is defined in
   `token_provisioning.py` (T049) and re-exported here.

**Files**: `src/specify_cli/auth/websocket/__init__.py` (~20 lines)

**Validation**:
- [ ] `from specify_cli.auth.websocket import provision_ws_token` works after T049

---

### T049: Create `auth/websocket/token_provisioning.py` (TokenProvisioner)

**Purpose**: The class and helper function that fetches the ephemeral token.

**Steps**:

1. Create `src/specify_cli/auth/websocket/token_provisioning.py`:
   ```python
   """WebSocket pre-connect token provisioner."""
   from __future__ import annotations
   import logging
   from datetime import datetime, timedelta, timezone
   from typing import Optional
   import httpx
   from .. import get_token_manager
   from ..config import get_saas_base_url
   from ..errors import (
       AuthenticationError,
       NotAuthenticatedError,
       NetworkError,
   )

   log = logging.getLogger(__name__)

   _PRE_CONNECT_REFRESH_BUFFER_SECONDS = 300  # 5 minutes


   class WebSocketProvisioningError(AuthenticationError):
       """Raised when WebSocket token provisioning fails."""


   class WebSocketTokenProvisioner:
       """Fetches ephemeral WebSocket tokens from /api/v1/ws-token."""

       def __init__(self, *, refresh_buffer_seconds: int = _PRE_CONNECT_REFRESH_BUFFER_SECONDS) -> None:
           self._refresh_buffer = refresh_buffer_seconds

       async def provision(self, team_id: str) -> dict:
           """Provision a WebSocket token for the given team.

           Returns:
               dict with keys: ws_token, ws_url, expires_in, session_id

           Raises:
               NotAuthenticatedError: if no session
               WebSocketProvisioningError: on 4xx/5xx response
               NetworkError: on transport failure
           """
           tm = get_token_manager()
           if not tm.is_authenticated:
               raise NotAuthenticatedError(
                   "WebSocket provisioning requires authentication. "
                   "Run `spec-kitty auth login`."
               )

           # Pre-connect refresh: if access token expires within the buffer, refresh now
           session = tm.get_current_session()
           if session is not None and session.is_access_token_expired(buffer_seconds=self._refresh_buffer):
               log.debug("Pre-connect refresh: access token near expiry")
               await tm.refresh_if_needed()

           access_token = await tm.get_access_token()

           saas_url = get_saas_base_url()
           url = f"{saas_url}/api/v1/ws-token"
           headers = {"Authorization": f"Bearer {access_token}"}
           payload = {"team_id": team_id}

           async with httpx.AsyncClient(timeout=10.0) as client:
               try:
                   response = await client.post(url, json=payload, headers=headers)
               except httpx.RequestError as exc:
                   raise NetworkError(f"WebSocket provisioning network error: {exc}") from exc

           return self._handle_response(response, team_id)

       def _handle_response(self, response: httpx.Response, team_id: str) -> dict:
           if response.status_code == 200:
               body = response.json()
               required = ("ws_token", "ws_url", "expires_in", "session_id")
               missing = [k for k in required if k not in body]
               if missing:
                   raise WebSocketProvisioningError(
                       f"WS token response missing fields: {missing}"
                   )
               return body

           # See T050 for error response handling
           return self._raise_for_error(response, team_id)

       def _raise_for_error(self, response: httpx.Response, team_id: str) -> None:
           # Implementation in T050
           ...


   async def provision_ws_token(team_id: str) -> dict:
       """Convenience wrapper around WebSocketTokenProvisioner.provision()."""
       return await WebSocketTokenProvisioner().provision(team_id)
   ```

**Files**: `src/specify_cli/auth/websocket/token_provisioning.py` (~120 lines initially, grows in T050)

**Validation**:
- [ ] `provision_ws_token("tm_acme")` works with mocked HTTP
- [ ] Pre-connect refresh triggered when access token within buffer
- [ ] Bearer token correctly injected

---

### T050: Add 403/404/5xx error handling

**Purpose**: Fill in `_raise_for_error()` from T049.

**Steps**:

1. Add to `src/specify_cli/auth/websocket/token_provisioning.py`:
   ```python
   def _raise_for_error(self, response: httpx.Response, team_id: str) -> None:
       status = response.status_code
       try:
           body = response.json()
       except ValueError:
           body = {}

       error = body.get("error", "")
       desc = body.get("error_description", "")

       if status == 401:
           raise WebSocketProvisioningError(
               "Authentication required. Run `spec-kitty auth login`."
           )
       if status == 403:
           if error == "not_a_team_member":
               raise WebSocketProvisioningError(
                   f"You are not a member of team '{team_id}'. "
                   f"Check the team ID or contact your team admin."
               )
           raise WebSocketProvisioningError(
               f"Forbidden: {desc or 'access denied'}"
           )
       if status == 404:
           raise WebSocketProvisioningError(
               f"Team '{team_id}' not found. Check the team ID."
           )
       if 500 <= status < 600:
           raise WebSocketProvisioningError(
               f"SaaS server error (HTTP {status}). Try again in a few minutes."
           )

       raise WebSocketProvisioningError(
           f"Unexpected response from /api/v1/ws-token: HTTP {status}"
       )
   ```

**Files**: included in `token_provisioning.py`

**Validation**:
- [ ] 401 → WebSocketProvisioningError with "auth login" message
- [ ] 403 with `not_a_team_member` → user-friendly message naming the team
- [ ] 404 → "team not found" message
- [ ] 500 → "server error" message
- [ ] Other status → generic message

---

### T051: Write unit tests for WebSocketTokenProvisioner

**Purpose**: Coverage of all paths.

**Steps**:

1. Create `tests/auth/test_websocket_provisioning.py`:
   ```python
   import pytest
   from datetime import datetime, timedelta, timezone
   from unittest.mock import AsyncMock, MagicMock, patch
   import httpx
   from specify_cli.auth.websocket import (
       provision_ws_token,
       WebSocketTokenProvisioner,
       WebSocketProvisioningError,
   )
   from specify_cli.auth import reset_token_manager
   from specify_cli.auth.errors import NotAuthenticatedError, NetworkError
   from specify_cli.auth.session import StoredSession, Team


   def _make_session(access_remaining_seconds: int = 3600) -> StoredSession:
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
           access_token_expires_at=now + timedelta(seconds=access_remaining_seconds),
           refresh_token_expires_at=now + timedelta(days=90),
           scope="offline_access",
           storage_backend="file",
           last_used_at=now,
           auth_method="authorization_code",
       )


   class _MockResponse:
       def __init__(self, status_code: int, json_body: dict):
           self.status_code = status_code
           self._json = json_body
       def json(self):
           return self._json


   @pytest.fixture
   def mock_tm(monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
       reset_token_manager()
       fake_tm = MagicMock()
       fake_tm.is_authenticated = True
       fake_tm.get_current_session.return_value = _make_session()
       fake_tm.get_access_token = AsyncMock(return_value="at_xyz")
       fake_tm.refresh_if_needed = AsyncMock(return_value=False)
       with patch("specify_cli.auth.websocket.token_provisioning.get_token_manager", return_value=fake_tm):
           yield fake_tm
       reset_token_manager()


   @pytest.mark.asyncio
   class TestWebSocketTokenProvisioner:

       async def test_success(self, mock_tm):
           ws_response = {
               "ws_token": "ws_xyz",
               "ws_url": "wss://saas.test/ws",
               "expires_in": 3600,
               "session_id": "sess_xyz",
           }
           async def mock_post(url, json=None, headers=None):
               return _MockResponse(200, ws_response)
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               result = await provision_ws_token("tm_acme")
           assert result == ws_response

       async def test_not_authenticated(self, mock_tm):
           mock_tm.is_authenticated = False
           with pytest.raises(NotAuthenticatedError):
               await provision_ws_token("tm_acme")

       async def test_pre_connect_refresh_when_near_expiry(self, mock_tm):
           # Session expires in 60s, buffer is 300s → must refresh
           mock_tm.get_current_session.return_value = _make_session(access_remaining_seconds=60)
           ws_response = {
               "ws_token": "ws_xyz",
               "ws_url": "wss://saas.test/ws",
               "expires_in": 3600,
               "session_id": "sess_xyz",
           }
           async def mock_post(url, json=None, headers=None):
               return _MockResponse(200, ws_response)
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               await provision_ws_token("tm_acme")
           mock_tm.refresh_if_needed.assert_called_once()

       async def test_403_not_team_member(self, mock_tm):
           async def mock_post(url, json=None, headers=None):
               return _MockResponse(403, {"error": "not_a_team_member"})
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               with pytest.raises(WebSocketProvisioningError, match="not a member"):
                   await provision_ws_token("tm_acme")

       async def test_404_team_not_found(self, mock_tm):
           async def mock_post(url, json=None, headers=None):
               return _MockResponse(404, {})
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               with pytest.raises(WebSocketProvisioningError, match="not found"):
                   await provision_ws_token("tm_acme")

       async def test_500_server_error(self, mock_tm):
           async def mock_post(url, json=None, headers=None):
               return _MockResponse(500, {})
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               with pytest.raises(WebSocketProvisioningError, match="server error"):
                   await provision_ws_token("tm_acme")

       async def test_network_error(self, mock_tm):
           async def mock_post(url, json=None, headers=None):
               raise httpx.RequestError("connection refused")
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               with pytest.raises(NetworkError):
                   await provision_ws_token("tm_acme")
   ```

**Files**: `tests/auth/test_websocket_provisioning.py` (~250 lines)

**Validation**:
- [ ] All test cases pass
- [ ] Pre-connect refresh test asserts that `refresh_if_needed` was called

---

## Definition of Done

- [ ] All 4 subtasks completed
- [ ] All unit tests pass
- [ ] `provision_ws_token(team_id)` returns the ephemeral token dict
- [ ] All 4xx/5xx status codes handled with user-friendly errors
- [ ] Pre-connect refresh works
- [ ] No tokens or secrets logged

## Reviewer Guidance

- Verify the pre-connect refresh check uses `is_access_token_expired(buffer_seconds=300)`
- Verify the 403 with `not_a_team_member` produces a user-friendly error naming the team
- Verify the unit test for pre-connect refresh asserts on `refresh_if_needed` being called

## Risks & Edge Cases

- **Risk**: SaaS returns a non-standard error code. **Mitigation**: catch-all branch raises a generic WebSocketProvisioningError with the HTTP status.
- **Risk**: WS token expires before the connection actually opens. **Mitigation**: out of scope for this WP — `sync/client.py` (WP08) is responsible for opening the WS within the token's TTL.
- **Edge case**: User's only team is the default team and they pass it explicitly. **Mitigation**: that's the normal case; the team_id is passed through to SaaS.

## Activity Log

- 2026-04-09T17:31:45Z – opus:opus:implementer:implementer – shell_pid=67527 – Started implementation via action command
