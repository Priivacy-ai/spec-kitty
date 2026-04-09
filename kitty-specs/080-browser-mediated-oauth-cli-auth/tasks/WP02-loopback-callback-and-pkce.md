---
work_package_id: WP02
title: Loopback Callback Handler + PKCE
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
- T015
history: []
authoritative_surface: src/specify_cli/auth/loopback/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/loopback/**
- tests/auth/test_pkce.py
- tests/auth/test_loopback_callback.py
- tests/auth/test_state_manager.py
- tests/auth/test_browser_launcher.py
status: pending
tags: []
agent: "opus:opus:implementer:implementer"
shell_pid: "56836"
---

# WP02: Loopback Callback Handler + PKCE

**Objective**: Build the localhost HTTP server, PKCE state machine, and CSRF
validation needed for the Authorization Code + PKCE flow. This is everything
the browser interaction needs except the orchestration layer (which is WP04).

**Context**: Foundation for WP04 (Browser Login Flow). Without this, the CLI
cannot receive the OAuth callback redirect from the browser. RFC 7636 PKCE +
RFC 6749 Authorization Code Grant.

**Acceptance Criteria**:
- [ ] `generate_code_verifier()` returns exactly 43 ASCII characters using `secrets.token_urlsafe`
- [ ] `generate_code_challenge(verifier)` returns SHA256(verifier) base64url-encoded without padding (S256 method)
- [ ] `CallbackServer` listens on `localhost:PORT`, searching ports 28888-28898 first, then asking the OS for any available port
- [ ] `CallbackServer` returns the callback parameters via `wait_for_callback()` async method
- [ ] `CallbackServer` times out after 5 minutes (300 seconds) raising `CallbackTimeoutError`
- [ ] `CallbackHandler.validate(params)` raises `CallbackValidationError` if state mismatch (CSRF protection)
- [ ] `PKCEState` expires after 5 minutes from creation
- [ ] `BrowserLauncher.launch(url)` opens the URL via stdlib `webbrowser`, returns False if no browser available
- [ ] All unit tests pass

---

## Subtask Guidance

### T009: Create `auth/loopback/pkce.py`

**Purpose**: PKCE code_verifier and code_challenge generation per RFC 7636.

**Steps**:

1. Create `src/specify_cli/auth/loopback/pkce.py`:
   ```python
   from __future__ import annotations
   import base64
   import hashlib
   import secrets


   def generate_code_verifier() -> str:
       """Return a 43-character cryptographically secure code_verifier per RFC 7636 §4.1.

       The verifier is `secrets.token_urlsafe(32)` which produces 43 base64url
       characters (32 bytes encoded). The result is in the [A-Z][a-z][0-9]_- alphabet.
       """
       return secrets.token_urlsafe(32)


   def generate_code_challenge(verifier: str) -> str:
       """Return base64url(SHA256(verifier)) without padding per RFC 7636 §4.2 (S256 method)."""
       digest = hashlib.sha256(verifier.encode("ascii")).digest()
       return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


   def generate_pkce_pair() -> tuple[str, str]:
       """Return a (code_verifier, code_challenge) tuple."""
       verifier = generate_code_verifier()
       challenge = generate_code_challenge(verifier)
       return verifier, challenge
   ```

2. The 32-byte input to `token_urlsafe` produces 43 base64url characters
   (`ceil(32 * 4/3) = 43`, no padding). Verifying: `len(secrets.token_urlsafe(32)) == 43`.

**Files**: `src/specify_cli/auth/loopback/pkce.py` (~40 lines)

**Validation**:
- [ ] `len(generate_code_verifier()) == 43`
- [ ] All characters are in `[A-Za-z0-9_-]`
- [ ] Known-answer test: for verifier `"dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"`, challenge equals `"E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"` (RFC 7636 example)
- [ ] No padding `=` in the challenge

---

### T010: Create `auth/loopback/state.py` (PKCEState dataclass + 5-min expiry)

**Purpose**: The transient state for an in-flight OAuth Authorization Code flow.

**Steps**:

1. Create `src/specify_cli/auth/loopback/state.py`:
   ```python
   from __future__ import annotations
   import secrets
   from dataclasses import dataclass, field
   from datetime import datetime, timedelta, timezone


   _STATE_TTL = timedelta(minutes=5)


   @dataclass
   class PKCEState:
       """In-flight Authorization Code + PKCE state for one login attempt."""
       state: str                    # CSRF nonce
       code_verifier: str            # Random secret
       code_challenge: str           # SHA256(verifier) base64url
       code_challenge_method: str    # Always "S256"
       created_at: datetime
       expires_at: datetime

       @classmethod
       def create(cls, verifier: str, challenge: str) -> "PKCEState":
           now = datetime.now(timezone.utc)
           return cls(
               state=secrets.token_urlsafe(32),
               code_verifier=verifier,
               code_challenge=challenge,
               code_challenge_method="S256",
               created_at=now,
               expires_at=now + _STATE_TTL,
           )

       def is_expired(self) -> bool:
           return datetime.now(timezone.utc) >= self.expires_at
   ```

**Files**: `src/specify_cli/auth/loopback/state.py` (~40 lines)

**Validation**:
- [ ] `PKCEState.create(verifier, challenge)` populates all fields
- [ ] `expires_at - created_at == 5 minutes`
- [ ] `is_expired()` returns True after 5 minutes (test with monkeypatched datetime or `freezegun`)

---

### T011: Create `auth/loopback/state_manager.py` (lifecycle)

**Purpose**: Helper that wraps PKCE state creation and validation. Provides
a single API for the flow orchestrator (WP04) to call.

**Steps**:

1. Create `src/specify_cli/auth/loopback/state_manager.py`:
   ```python
   from __future__ import annotations
   from .pkce import generate_pkce_pair
   from .state import PKCEState
   from ..errors import StateExpiredError


   class StateManager:
       """Manages PKCE state lifecycle for in-flight Authorization Code flows."""

       def generate(self) -> PKCEState:
           """Generate a fresh PKCEState with verifier, challenge, and CSRF nonce."""
           verifier, challenge = generate_pkce_pair()
           return PKCEState.create(verifier, challenge)

       def validate_not_expired(self, state: PKCEState) -> None:
           """Raise StateExpiredError if the state has expired."""
           if state.is_expired():
               raise StateExpiredError(
                   f"PKCEState expired (created {state.created_at}, "
                   f"expires {state.expires_at})"
               )

       def cleanup(self, state: PKCEState) -> None:
           """No-op for in-memory state. Hook for future persistent state."""
           pass
   ```

**Files**: `src/specify_cli/auth/loopback/state_manager.py` (~30 lines)

**Validation**:
- [ ] `generate()` returns a fresh PKCEState with a 43-char verifier
- [ ] `validate_not_expired()` raises StateExpiredError on expired state

---

### T012: Create `auth/loopback/callback_server.py`

**Purpose**: Localhost HTTP server that receives the OAuth redirect callback.

**Steps**:

1. Create `src/specify_cli/auth/loopback/callback_server.py`:
   ```python
   from __future__ import annotations
   import asyncio
   import socket
   from http.server import BaseHTTPRequestHandler, HTTPServer
   from threading import Thread
   from typing import Optional
   from urllib.parse import parse_qs, urlparse
   from ..errors import CallbackTimeoutError

   _PORT_RANGE = range(28888, 28899)  # 28888..28898 inclusive
   _HOST = "127.0.0.1"
   _DEFAULT_TIMEOUT = 300.0  # 5 minutes


   class _CallbackHTTPHandler(BaseHTTPRequestHandler):
       def do_GET(self):
           parsed = urlparse(self.path)
           if parsed.path != "/callback":
               self.send_response(404)
               self.end_headers()
               return
           params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
           self.server.callback_params = params  # type: ignore[attr-defined]
           self.send_response(200)
           self.send_header("Content-Type", "text/html; charset=utf-8")
           self.end_headers()
           self.wfile.write(
               b"<html><body><h1>Authentication complete</h1>"
               b"<p>You can close this tab and return to your terminal.</p>"
               b"</body></html>"
           )

       def log_message(self, format, *args):
           pass  # Silence default stderr logging


   class CallbackServer:
       """Localhost HTTP server for receiving OAuth callbacks."""

       def __init__(self, timeout_seconds: float = _DEFAULT_TIMEOUT) -> None:
           self._timeout = timeout_seconds
           self._server: Optional[HTTPServer] = None
           self._thread: Optional[Thread] = None
           self._port: Optional[int] = None

       @property
       def port(self) -> int:
           if self._port is None:
               raise RuntimeError("CallbackServer is not started")
           return self._port

       @property
       def callback_url(self) -> str:
           return f"http://{_HOST}:{self.port}/callback"

       def start(self) -> str:
           """Start the server and return the callback URL."""
           self._port = self._find_port()
           self._server = HTTPServer((_HOST, self._port), _CallbackHTTPHandler)
           self._server.callback_params = None  # type: ignore[attr-defined]
           self._thread = Thread(target=self._server.serve_forever, daemon=True)
           self._thread.start()
           return self.callback_url

       def stop(self) -> None:
           if self._server is not None:
               self._server.shutdown()
               self._server.server_close()
               self._server = None
           if self._thread is not None:
               self._thread.join(timeout=2.0)
               self._thread = None

       async def wait_for_callback(self) -> dict[str, str]:
           """Async wait for the callback to arrive. Times out after self._timeout seconds."""
           assert self._server is not None
           deadline = asyncio.get_event_loop().time() + self._timeout
           while asyncio.get_event_loop().time() < deadline:
               params = self._server.callback_params  # type: ignore[attr-defined]
               if params is not None:
                   return params
               await asyncio.sleep(0.1)
           raise CallbackTimeoutError(
               f"Callback timed out after {self._timeout} seconds. "
               f"Run `spec-kitty auth login` again."
           )

       def _find_port(self) -> int:
           """Find an available port. Try 28888-28898 first, then ask OS."""
           for port in _PORT_RANGE:
               if self._is_port_free(port):
                   return port
           # Fallback: ask OS for any free port
           with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
               s.bind((_HOST, 0))
               return s.getsockname()[1]

       @staticmethod
       def _is_port_free(port: int) -> bool:
           with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
               s.settimeout(0.5)
               try:
                   s.bind((_HOST, port))
                   return True
               except OSError:
                   return False
   ```

2. The server runs in a daemon thread so the main async loop can poll for the
   callback via `wait_for_callback()`. Daemon thread ensures the server dies
   on process exit.

**Files**: `src/specify_cli/auth/loopback/callback_server.py` (~140 lines)

**Validation**:
- [ ] Server starts on a port in 28888-28898 when free
- [ ] Server falls back to OS-assigned port when 28888-28898 are all busy
- [ ] `wait_for_callback()` returns when the browser hits `/callback?code=X&state=Y`
- [ ] `wait_for_callback()` raises `CallbackTimeoutError` after the timeout
- [ ] `stop()` cleanly shuts down the server

---

### T013: Create `auth/loopback/callback_handler.py`

**Purpose**: Validate callback parameters and extract the authorization code.
CSRF protection via state matching.

**Steps**:

1. Create `src/specify_cli/auth/loopback/callback_handler.py`:
   ```python
   from __future__ import annotations
   from typing import Tuple
   from ..errors import CallbackValidationError, CallbackError


   class CallbackHandler:
       """Validates the OAuth callback parameters against the expected state."""

       def __init__(self, expected_state: str) -> None:
           self._expected_state = expected_state

       def validate(self, params: dict[str, str]) -> Tuple[str, str]:
           """Validate the callback and return (code, state).

           Raises:
               CallbackValidationError on missing fields or state mismatch
               CallbackError on SaaS-reported errors
           """
           # Check for SaaS-reported error
           if "error" in params:
               error = params["error"]
               desc = params.get("error_description", "")
               raise CallbackError(f"OAuth provider returned error: {error} ({desc})")

           if "code" not in params:
               raise CallbackValidationError("Missing 'code' in callback parameters")
           if "state" not in params:
               raise CallbackValidationError("Missing 'state' in callback parameters")

           if params["state"] != self._expected_state:
               raise CallbackValidationError(
                   "State mismatch (CSRF attack detected): expected "
                   f"{self._expected_state[:8]}..., got {params['state'][:8]}..."
               )

           return params["code"], params["state"]


   def validate_callback_params(params: dict[str, str], expected_state: str) -> Tuple[str, str]:
       """Functional wrapper around CallbackHandler.validate()."""
       return CallbackHandler(expected_state).validate(params)
   ```

**Files**: `src/specify_cli/auth/loopback/callback_handler.py` (~50 lines)

**Validation**:
- [ ] Valid params return (code, state)
- [ ] Missing code → CallbackValidationError
- [ ] Missing state → CallbackValidationError
- [ ] State mismatch → CallbackValidationError
- [ ] error in params → CallbackError

---

### T014: Create `auth/loopback/browser_launcher.py`

**Purpose**: Cross-platform browser launching with graceful fallback.

**Steps**:

1. Create `src/specify_cli/auth/loopback/browser_launcher.py`:
   ```python
   from __future__ import annotations
   import logging
   import webbrowser

   log = logging.getLogger(__name__)


   class BrowserLauncher:
       """Cross-platform browser launcher using stdlib `webbrowser`."""

       @staticmethod
       def is_available() -> bool:
           """Return True if a browser controller is available on this system."""
           try:
               webbrowser.get()
               return True
           except webbrowser.Error:
               return False

       @staticmethod
       def launch(url: str) -> bool:
           """Open the URL in the default browser. Return True on success."""
           try:
               opened = webbrowser.open(url, new=2, autoraise=True)
               if not opened:
                   log.warning("webbrowser.open returned False for %s", url)
               return opened
           except webbrowser.Error as exc:
               log.warning("Failed to launch browser: %s", exc)
               return False
   ```

**Files**: `src/specify_cli/auth/loopback/browser_launcher.py` (~40 lines)

**Validation**:
- [ ] `is_available()` returns True on a system with a browser
- [ ] `launch(url)` returns True when the browser opens
- [ ] `launch(url)` returns False when no browser is available (mock `webbrowser.get` to raise)

---

### T015: Write unit tests for WP02 components

**Purpose**: Coverage of all loopback modules with no real network or browser.

**Steps**:

1. `tests/auth/test_pkce.py`: 43-char verifier, S256 challenge, RFC 7636 known-answer test
2. `tests/auth/test_state_manager.py`: PKCE state lifecycle, expiry, generate, validate
3. `tests/auth/test_loopback_callback.py`: CallbackHandler with valid/missing/mismatched params; CallbackServer with simulated browser request via `urllib.request.urlopen` to localhost
4. `tests/auth/test_browser_launcher.py`: mock `webbrowser.get` and `webbrowser.open`

5. Critical: tests must NOT actually open a real browser. Use `monkeypatch` on
   `webbrowser.open` to return True without launching anything.

6. CallbackServer tests: start the server, then in a thread/task simulate
   the browser by `urllib.request.urlopen(server.callback_url + "?code=X&state=Y")`,
   then await `server.wait_for_callback()`.

**Files**: 4 test files, ~400 lines total

**Validation**:
- [ ] All tests pass
- [ ] No real browser launched
- [ ] No real network requests except localhost loopback

---

## Definition of Done

- [ ] All 7 subtasks completed
- [ ] All unit tests pass
- [ ] PKCE generation passes RFC 7636 example known-answer test
- [ ] CallbackServer tested end-to-end via localhost loopback
- [ ] CSRF state validation tested
- [ ] No tokens or secrets logged

## Reviewer Guidance

- Verify `generate_code_verifier()` uses `secrets.token_urlsafe(32)` (not `random.choice`)
- Verify the SHA256 challenge is base64url with padding stripped
- Verify CallbackServer searches 28888-28898 BEFORE asking the OS
- Verify CallbackHandler raises `CallbackValidationError` on state mismatch (not just any exception)
- Verify the browser launcher uses stdlib `webbrowser`, not subprocess to `open`/`xdg-open`

## Risks & Edge Cases

- **Risk**: Firewall blocks localhost ports → server can't bind. **Mitigation**: 11-port search range + OS fallback.
- **Risk**: User has multiple browsers; default may not be the one they're logged into. **Mitigation**: Document in error message that the user can paste the URL manually.
- **Risk**: Callback received twice (browser refresh). **Mitigation**: First callback wins; server `callback_params` is set once and `wait_for_callback()` returns immediately.
- **Edge case**: PKCE state expires while waiting for callback (5 min). **Mitigation**: WP04 orchestrator checks `state.is_expired()` after `wait_for_callback()` returns.

## Activity Log

- 2026-04-09T17:27:13Z – opus:opus:implementer:implementer – shell_pid=56836 – Started implementation via action command
