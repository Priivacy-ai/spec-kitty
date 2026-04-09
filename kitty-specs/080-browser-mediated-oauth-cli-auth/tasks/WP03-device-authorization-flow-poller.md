---
work_package_id: WP03
title: Device Authorization Flow Poller
dependencies:
- WP01
requirement_refs:
- FR-018
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
history: []
authoritative_surface: src/specify_cli/auth/device_flow/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/device_flow/**
- tests/auth/test_device_flow_poller.py
status: pending
tags: []
---

# WP03: Device Authorization Flow Poller

**Objective**: Build the polling state machine for RFC 8628 Device Authorization
Grant. The poller takes a `DeviceFlowState` (containing `device_code`,
`interval`, `expires_in`) and polls the token endpoint until approval, denial,
or expiry.

**Context**: Foundation for WP05 (Headless Login Flow). The poller is the
mechanical loop; WP05 wraps it with HTTP calls and session creation.

**Acceptance Criteria**:
- [ ] `DeviceFlowState` dataclass tracks device_code, user_code, verification_uri, expires_in, interval, created_at, last_polled_at, poll_count
- [ ] Poller respects the `interval` field from SaaS, capped at 10 seconds maximum
- [ ] Poller stops on `authorization_pending` (continues), `slow_down` (increases interval), `access_denied` (raises DeviceFlowDenied), `expired_token` (raises DeviceFlowExpired)
- [ ] On success, poller returns the parsed token response dict
- [ ] User code formatter outputs `ABCD-1234` chunks for human readability
- [ ] Progress display writes to stderr (not stdout) so the user sees it but it doesn't pollute pipes
- [ ] All unit tests pass

---

## Subtask Guidance

### T016: Create `auth/device_flow/state.py` (DeviceFlowState dataclass)

**Purpose**: The data model for an in-flight device authorization flow.

**Steps**:

1. Create `src/specify_cli/auth/device_flow/__init__.py`:
   ```python
   from __future__ import annotations
   from .state import DeviceFlowState
   from .poller import DeviceFlowPoller, format_user_code

   __all__ = ["DeviceFlowState", "DeviceFlowPoller", "format_user_code"]
   ```

2. Create `src/specify_cli/auth/device_flow/state.py`:
   ```python
   from __future__ import annotations
   from dataclasses import dataclass, field
   from datetime import datetime, timedelta, timezone
   from typing import Optional


   @dataclass
   class DeviceFlowState:
       """In-flight device authorization flow state per RFC 8628."""
       device_code: str
       user_code: str
       verification_uri: str
       verification_uri_complete: Optional[str]  # Optional convenience URL with embedded user_code
       expires_in: int           # Seconds (typically 900 = 15 minutes)
       interval: int             # SaaS-suggested polling interval in seconds
       created_at: datetime
       expires_at: datetime
       last_polled_at: Optional[datetime] = None
       poll_count: int = 0

       @classmethod
       def from_oauth_response(cls, response: dict) -> "DeviceFlowState":
           """Build a DeviceFlowState from a /oauth/device response."""
           now = datetime.now(timezone.utc)
           expires_in = int(response.get("expires_in", 900))
           return cls(
               device_code=response["device_code"],
               user_code=response["user_code"],
               verification_uri=response["verification_uri"],
               verification_uri_complete=response.get("verification_uri_complete"),
               expires_in=expires_in,
               interval=int(response.get("interval", 5)),
               created_at=now,
               expires_at=now + timedelta(seconds=expires_in),
           )

       def is_expired(self) -> bool:
           return datetime.now(timezone.utc) >= self.expires_at

       def time_remaining(self) -> timedelta:
           return self.expires_at - datetime.now(timezone.utc)

       def record_poll(self) -> None:
           self.last_polled_at = datetime.now(timezone.utc)
           self.poll_count += 1
   ```

**Files**: `src/specify_cli/auth/device_flow/__init__.py` (~10 lines), `src/specify_cli/auth/device_flow/state.py` (~60 lines)

**Validation**:
- [ ] `from_oauth_response()` parses the SaaS device endpoint response
- [ ] `is_expired()` returns True after `expires_in` seconds
- [ ] `record_poll()` increments `poll_count` and updates `last_polled_at`

---

### T017: Create `auth/device_flow/poller.py` (interval-respecting loop)

**Purpose**: The async polling loop that calls the token endpoint until a
terminal state is reached.

**Steps**:

1. Create `src/specify_cli/auth/device_flow/poller.py`:
   ```python
   from __future__ import annotations
   import asyncio
   import logging
   from typing import Awaitable, Callable, Optional
   from .state import DeviceFlowState
   from ..errors import DeviceFlowDenied, DeviceFlowExpired, NetworkError

   log = logging.getLogger(__name__)

   _MAX_INTERVAL_SECONDS = 10  # FR-018: cap polling at 10s


   def format_user_code(user_code: str) -> str:
       """Format user code for human display: 'ABCD1234' -> 'ABCD-1234'."""
       cleaned = user_code.replace("-", "").replace(" ", "")
       if len(cleaned) <= 4:
           return cleaned
       # Insert hyphen every 4 characters
       chunks = [cleaned[i : i + 4] for i in range(0, len(cleaned), 4)]
       return "-".join(chunks)


   class DeviceFlowPoller:
       """Polls the OAuth token endpoint until the device flow reaches a terminal state."""

       def __init__(self, state: DeviceFlowState) -> None:
           self._state = state

       @property
       def state(self) -> DeviceFlowState:
           return self._state

       async def poll(
           self,
           token_request: Callable[[str], Awaitable[dict]],
           on_pending: Optional[Callable[[DeviceFlowState], None]] = None,
       ) -> dict:
           """Poll until success, denial, expiry, or timeout.

           Args:
               token_request: async function that takes the device_code and POSTs
                   /oauth/token. Should return the SaaS response dict on success
                   OR a dict with `error` key on a non-success response.
                   Network errors should raise.
               on_pending: optional callback called after each pending poll.

           Returns:
               Token response dict on approval (contains access_token, refresh_token, etc.)

           Raises:
               DeviceFlowDenied: if SaaS returns access_denied
               DeviceFlowExpired: if SaaS returns expired_token or local expiry hits
               NetworkError: on transport-level failures
           """
           interval = min(self._state.interval, _MAX_INTERVAL_SECONDS)

           while True:
               if self._state.is_expired():
                   raise DeviceFlowExpired(
                       f"Device authorization expired after {self._state.expires_in} seconds. "
                       f"Run `spec-kitty auth login --headless` again."
                   )

               # Wait for the polling interval before the first poll too — gives
               # the user time to actually approve in the browser
               await asyncio.sleep(interval)
               self._state.record_poll()

               try:
                   response = await token_request(self._state.device_code)
               except NetworkError as exc:
                   log.warning("Network error during device flow poll: %s", exc)
                   continue

               error = response.get("error")
               if error is None:
                   # Success — response contains tokens
                   return response

               if error == "authorization_pending":
                   if on_pending is not None:
                       on_pending(self._state)
                   continue

               if error == "slow_down":
                   # Per RFC 8628 §3.5, increase interval by 5 seconds
                   interval = min(interval + 5, _MAX_INTERVAL_SECONDS)
                   continue

               if error == "access_denied":
                   raise DeviceFlowDenied(
                       "User denied the authorization request. "
                       "Run `spec-kitty auth login --headless` to try again."
                   )

               if error == "expired_token":
                   raise DeviceFlowExpired(
                       "Device code expired before approval. "
                       "Run `spec-kitty auth login --headless` to try again."
                   )

               # Unknown error — propagate as DeviceFlowDenied with description
               desc = response.get("error_description", error)
               raise DeviceFlowDenied(f"Unexpected device flow error: {desc}")
   ```

2. Critical: the `_MAX_INTERVAL_SECONDS = 10` constant enforces FR-018. SaaS
   may send `interval: 30` but the CLI ignores anything above 10.

3. Critical: `await asyncio.sleep(interval)` happens BEFORE the first poll,
   not after. This gives the user time to actually approve in the browser.

4. The `slow_down` error per RFC 8628 §3.5 increases the interval by 5 seconds
   (still capped at 10).

**Files**: `src/specify_cli/auth/device_flow/poller.py` (~120 lines)

**Validation**:
- [ ] Poller returns the response dict on success
- [ ] Poller raises DeviceFlowDenied on access_denied
- [ ] Poller raises DeviceFlowExpired on expired_token
- [ ] Poller continues on authorization_pending
- [ ] Poller respects the interval, capped at 10 seconds
- [ ] Poller honors slow_down by increasing interval (capped at 10)
- [ ] Poller raises DeviceFlowExpired when the local state expires before SaaS does

---

### T018: Add user_code formatting + progress display helpers

**Purpose**: User-facing display helpers. The user_code formatter and a
simple stderr progress writer.

**Steps**:

1. `format_user_code()` is already in `poller.py` from T017.

2. Add a progress display helper inline (no new file):
   - The progress messaging is the responsibility of the WP05 flow that uses
     the poller. WP03's `on_pending` callback hook lets WP05 supply its own
     progress writer.

3. Add a docstring example for `format_user_code()`:
   ```
   >>> format_user_code("ABCD1234")
   'ABCD-1234'
   >>> format_user_code("ABCD-1234")
   'ABCD-1234'
   >>> format_user_code("ABCD12345678")
   'ABCD-1234-5678'
   ```

**Files**: included in `auth/device_flow/poller.py`

**Validation**:
- [ ] `format_user_code("ABCD1234") == "ABCD-1234"`
- [ ] Already-formatted codes are stable: `format_user_code("ABCD-1234") == "ABCD-1234"`
- [ ] Long codes chunked correctly

---

### T019: Write unit tests for WP03 components

**Purpose**: Coverage of state lifecycle and poller logic with mocked HTTP.

**Steps**:

1. `tests/auth/test_device_flow_poller.py`:
   ```python
   import asyncio
   import pytest
   from datetime import datetime, timedelta, timezone
   from specify_cli.auth.device_flow import DeviceFlowPoller, DeviceFlowState, format_user_code
   from specify_cli.auth.errors import DeviceFlowDenied, DeviceFlowExpired


   class TestFormatUserCode:
       def test_short_code(self):
           assert format_user_code("ABCD") == "ABCD"
       def test_8char_code(self):
           assert format_user_code("ABCD1234") == "ABCD-1234"
       def test_already_formatted(self):
           assert format_user_code("ABCD-1234") == "ABCD-1234"
       def test_12char_code(self):
           assert format_user_code("ABCD12345678") == "ABCD-1234-5678"


   def make_state(expires_in: int = 900, interval: int = 1) -> DeviceFlowState:
       return DeviceFlowState.from_oauth_response({
           "device_code": "dc_xyz",
           "user_code": "ABCD-1234",
           "verification_uri": "https://saas.test/device",
           "expires_in": expires_in,
           "interval": interval,
       })


   @pytest.mark.asyncio
   class TestDeviceFlowPoller:

       async def test_success_after_two_pending(self):
           state = make_state(interval=0)  # 0s interval for fast tests
           poller = DeviceFlowPoller(state)
           responses = [
               {"error": "authorization_pending"},
               {"error": "authorization_pending"},
               {"access_token": "at_xyz", "refresh_token": "rt_xyz", "expires_in": 3600, "scope": "offline_access", "session_id": "sess_1"},
           ]
           call_count = 0
           async def mock_request(device_code):
               nonlocal call_count
               r = responses[call_count]
               call_count += 1
               return r
           result = await poller.poll(mock_request)
           assert result["access_token"] == "at_xyz"
           assert state.poll_count == 3

       async def test_access_denied(self):
           state = make_state(interval=0)
           poller = DeviceFlowPoller(state)
           async def mock_request(device_code):
               return {"error": "access_denied"}
           with pytest.raises(DeviceFlowDenied):
               await poller.poll(mock_request)

       async def test_expired_token(self):
           state = make_state(interval=0)
           poller = DeviceFlowPoller(state)
           async def mock_request(device_code):
               return {"error": "expired_token"}
           with pytest.raises(DeviceFlowExpired):
               await poller.poll(mock_request)

       async def test_local_expiry(self):
           # State expires_in=0, so the poller raises before the first poll
           state = make_state(expires_in=0, interval=0)
           # Allow a tiny pause for "now" to be > expires_at
           await asyncio.sleep(0.01)
           poller = DeviceFlowPoller(state)
           async def mock_request(device_code):
               raise AssertionError("Should not be called")
           with pytest.raises(DeviceFlowExpired):
               await poller.poll(mock_request)

       async def test_interval_capped_at_10(self):
           # SaaS sends interval=30; poller must use 10
           state = DeviceFlowState.from_oauth_response({
               "device_code": "dc",
               "user_code": "ABCD",
               "verification_uri": "https://saas.test/device",
               "expires_in": 900,
               "interval": 30,
           })
           poller = DeviceFlowPoller(state)
           # We can't easily test the actual sleep duration without monkeypatching
           # asyncio.sleep, but we can assert the cap by inspecting the interval
           # value the poller uses internally
           # (Implementation detail: rely on a sleep tracker)
           sleep_durations = []
           orig_sleep = asyncio.sleep
           async def tracking_sleep(d):
               sleep_durations.append(d)
               await orig_sleep(0)
           import unittest.mock
           call_count = 0
           async def mock_request(device_code):
               nonlocal call_count
               call_count += 1
               if call_count >= 2:
                   return {"access_token": "at", "refresh_token": "rt", "expires_in": 3600, "scope": "", "session_id": "s"}
               return {"error": "authorization_pending"}
           with unittest.mock.patch("specify_cli.auth.device_flow.poller.asyncio.sleep", side_effect=tracking_sleep):
               await poller.poll(mock_request)
           assert all(d <= 10 for d in sleep_durations), f"All sleeps must be ≤10s, got {sleep_durations}"
   ```

2. Run `pytest tests/auth/test_device_flow_poller.py -v` and verify all pass.

**Files**: `tests/auth/test_device_flow_poller.py` (~250 lines)

**Validation**:
- [ ] All test cases pass
- [ ] Coverage for state.py and poller.py is ≥ 90%

---

## Definition of Done

- [ ] All 4 subtasks completed
- [ ] All unit tests pass
- [ ] Polling interval is capped at 10 seconds even when SaaS sends a higher value
- [ ] User code formatter handles short, 8-char, and 12-char codes
- [ ] Poller terminates correctly on all RFC 8628 error codes
- [ ] No tokens or secrets logged

## Reviewer Guidance

- Verify the `_MAX_INTERVAL_SECONDS = 10` constant is enforced (FR-018)
- Verify `slow_down` increases the interval but still caps at 10
- Verify `expired_token` and local `is_expired()` both raise `DeviceFlowExpired`
- Verify `access_denied` raises `DeviceFlowDenied`
- Verify the test for interval-capping actually monkeypatches `asyncio.sleep` and asserts on the duration

## Risks & Edge Cases

- **Risk**: SaaS returns an unknown error code → poller crashes. **Mitigation**: catch-all branch raises `DeviceFlowDenied` with the error description.
- **Risk**: Network error during polling → poller crashes. **Mitigation**: `NetworkError` is caught and the loop continues (transient errors are retried).
- **Edge case**: `expires_in = 0` from SaaS → poller raises immediately. **Mitigation**: that's the correct behavior; the local state is already expired.
- **Edge case**: User approves authorization between two polls → next poll succeeds. **Mitigation**: that's the normal happy path.
