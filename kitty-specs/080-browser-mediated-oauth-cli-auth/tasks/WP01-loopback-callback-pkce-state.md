---
work_package_id: WP01
title: Loopback Callback Handler + PKCE State Management
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
history: []
authoritative_surface: src/specify_cli/auth/loopback/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/loopback/**
- tests/auth/test_loopback_callback.py
- tests/auth/test_pkce.py
status: pending
tags: []
---

# WP01: Loopback Callback Handler + PKCE State Management

**Objective**: Build the HTTP server and cryptographic state machine for the OAuth 2.0 Authorization Code + PKCE flow. Enables interactive browser-based login by providing a local callback endpoint and secure state validation.

**Context**: This is the foundation for WP05 (auth code flow orchestration). Without this, the CLI cannot handle the browser redirect during interactive login.

**Acceptance Criteria**:
- [ ] PKCE state generation produces exactly 43-character code_verifier
- [ ] code_challenge is SHA256(code_verifier) base64url-encoded
- [ ] Loopback server successfully receives callback on localhost:PORT
- [ ] State parameter validation prevents CSRF attacks
- [ ] Callback timeout (5 minutes) properly expires PKCEState
- [ ] All tests pass (100% coverage for new modules)
- [ ] Cross-platform browser launching works on macOS, Linux, Windows

---

## Detailed Subtask Guidance

### T001: Create PKCEState Dataclass and Model

**Purpose**: Define the data structure for transient OAuth state during the authorization code flow.

**Steps**:
1. Create `src/specify_cli/auth/loopback/state.py`:
   ```python
   from dataclasses import dataclass, field
   from datetime import datetime, timedelta
   import uuid
   
   @dataclass
   class PKCEState:
       """PKCE state for OAuth authorization code flow."""
       # CSRF Protection
       state: str                      # ≥128 bits entropy, base64url
       
       # PKCE Challenge
       code_verifier: str              # 43 ASCII chars (RFC 7636)
       code_challenge: str             # SHA256(code_verifier) base64url
       code_challenge_method: str      # "S256"
       
       # Lifecycle
       created_at: datetime            # UTC timestamp
       expires_at: datetime            # created_at + 5 minutes
       
       def is_expired(self) -> bool:
           return datetime.utcnow() > self.expires_at
       
       def is_valid(self) -> bool:
           return not self.is_expired() and all([
               self.state,
               self.code_verifier,
               self.code_challenge
           ])
   ```

2. Add validation methods:
   - `is_expired()`: Check if current time exceeds expires_at
   - `is_valid()`: Check all required fields are non-empty and not expired

3. Document field constraints in docstring (matching data-model.md)

**Files**:
- `src/specify_cli/auth/loopback/state.py` (new, ~50 lines)
- `src/specify_cli/auth/__init__.py` (update imports)

**Validation**:
- [ ] PKCEState instantiation works
- [ ] Expiry calculation is correct (5 minutes from now)
- [ ] is_expired() returns False immediately, True after expiry

---

### T002: Implement PKCE code_verifier Generation

**Purpose**: Generate cryptographically secure random code_verifier (43 unreserved ASCII characters per RFC 7636).

**Steps**:
1. Create `src/specify_cli/auth/loopback/pkce.py`:
   ```python
   import secrets
   import hashlib
   import base64
   
   def generate_code_verifier() -> str:
       """Generate RFC 7636 code_verifier.
       
       Returns exactly 43 characters from unreserved set:
       A-Z a-z 0-9 - . _ ~
       """
       # Generate 32 bytes (256 bits) of entropy
       entropy = secrets.token_bytes(32)
       # Encode as base64url, strip padding
       verifier = base64.urlsafe_b64encode(entropy).decode('utf-8').rstrip('=')
       # Trim to exactly 43 chars (RFC allows 43-128)
       return verifier[:43]
   ```

2. Add validation:
   - Assert length == 43
   - Assert all chars in unreserved set (regex: `^[A-Za-z0-9\-._~]+$`)

3. Test entropy (use unittest to verify randomness over multiple calls)

**Files**:
- `src/specify_cli/auth/loopback/pkce.py` (new, ~40 lines)

**Validation**:
- [ ] Generated verifier is exactly 43 characters
- [ ] Characters are all in unreserved set
- [ ] Multiple calls produce different values (entropy check)

---

### T003: Implement PKCE code_challenge Generation

**Purpose**: Generate SHA256(code_verifier) base64url-encoded code_challenge.

**Steps**:
1. In `src/specify_cli/auth/loopback/pkce.py`, add:
   ```python
   def generate_code_challenge(code_verifier: str) -> str:
       """Generate RFC 7636 code_challenge.
       
       Returns SHA256(code_verifier) base64url-encoded without padding.
       """
       digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
       challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
       return challenge
   ```

2. Validate:
   - code_challenge is base64url (no padding `=`)
   - Length is 43 characters (SHA256 → 32 bytes → 43 base64url chars)

3. Add combined function:
   ```python
   def generate_pkce_pair() -> tuple[str, str]:
       """Generate (code_verifier, code_challenge) pair."""
       verifier = generate_code_verifier()
       challenge = generate_code_challenge(verifier)
       return verifier, challenge
   ```

**Files**:
- `src/specify_cli/auth/loopback/pkce.py` (update existing)

**Validation**:
- [ ] SHA256 hash is computed correctly
- [ ] Base64url encoding removes padding
- [ ] Challenge length is exactly 43 characters
- [ ] For known verifier, challenge matches expected value

---

### T004: Create CallbackServer HTTP Server

**Purpose**: Build a minimal HTTP server listening on localhost:PORT to receive OAuth authorization code callback.

**Steps**:
1. Create `src/specify_cli/auth/loopback/callback_server.py`:
   ```python
   import asyncio
   from aiohttp import web
   from typing import Optional, Tuple
   
   class CallbackServer:
       """HTTP server for OAuth callback on loopback."""
       
       def __init__(self, port: Optional[int] = None, timeout_seconds: int = 300):
           self.port = port or await self._find_available_port()
           self.timeout_seconds = timeout_seconds
           self.app = web.Application()
           self.app.router.add_get('/callback', self.handle_callback)
           self.runner = None
           self.received_callback = None
       
       async def _find_available_port(self) -> int:
           """Try standard ports (28888-28898), fall back to OS assignment."""
           for port in range(28888, 28899):
               try:
                   # Test if port is available
                   sock = socket.socket()
                   sock.bind(('127.0.0.1', port))
                   sock.close()
                   return port
               except:
                   continue
           # Fall back to OS assignment (port=0)
           return 0
       
       async def handle_callback(self, request: web.Request) -> web.Response:
           """Handle GET /callback?code=...&state=..."""
           self.received_callback = dict(request.query)
           # Return HTML success message
           return web.Response(text="Authorization successful. You can close this window.")
       
       async def start(self) -> str:
           """Start server, return callback URL."""
           self.runner = web.AppRunner(self.app)
           await self.runner.setup()
           site = web.TCPSite(self.runner, '127.0.0.1', self.port)
           await site.start()
           return f"http://127.0.0.1:{self.port}/callback"
       
       async def wait_for_callback(self) -> dict:
           """Wait for callback with timeout, return query params."""
           # Implement timeout with asyncio.wait_for
           try:
               callback_data = await asyncio.wait_for(
                   self._wait_for_callback_impl(),
                   timeout=self.timeout_seconds
               )
               return callback_data
           except asyncio.TimeoutError:
               raise CallbackTimeoutError(f"Callback timeout after {self.timeout_seconds}s")
       
       async def stop(self):
           """Stop server and clean up."""
           if self.runner:
               await self.runner.cleanup()
   ```

2. Handle edge cases:
   - Port binding failure → try next port
   - Callback timeout → raise CallbackTimeoutError
   - Multiple requests → ignore after first

**Files**:
- `src/specify_cli/auth/loopback/callback_server.py` (new, ~100 lines)
- `src/specify_cli/auth/errors.py` (add CallbackTimeoutError)

**Validation**:
- [ ] Server starts on localhost:PORT
- [ ] GET /callback?code=abc&state=xyz is received
- [ ] Timeout after 5 minutes raises CallbackTimeoutError
- [ ] Server stops cleanly without hanging

---

### T005: Implement Callback URL Parsing and State Validation

**Purpose**: Parse query parameters from callback, validate state parameter matches original request (CSRF protection).

**Steps**:
1. Create `src/specify_cli/auth/loopback/callback_handler.py`:
   ```python
   class CallbackHandler:
       """Validate OAuth callback parameters."""
       
       def __init__(self, expected_state: str):
           self.expected_state = expected_state
       
       def validate(self, callback_params: dict) -> Tuple[str, str]:
           """Extract code and validate state.
           
           Returns: (code, state)
           Raises: CallbackValidationError
           """
           code = callback_params.get('code')
           state = callback_params.get('state')
           error = callback_params.get('error')
           
           # Check for error from SaaS
           if error:
               raise CallbackError(f"SaaS returned error: {error}")
           
           # Validate code present
           if not code:
               raise CallbackValidationError("Missing 'code' parameter")
           
           # Validate state matches (CSRF check)
           if not state:
               raise CallbackValidationError("Missing 'state' parameter")
           
           if state != self.expected_state:
               raise CallbackValidationError("State mismatch (CSRF attack?)")
           
           return code, state
   ```

2. Handle error codes from SaaS:
   - `access_denied`: User declined authorization
   - `invalid_request`: Malformed request
   - Other 4xx: Pass through with error message

**Files**:
- `src/specify_cli/auth/loopback/callback_handler.py` (new, ~60 lines)
- `src/specify_cli/auth/errors.py` (add CallbackValidationError, CallbackError)

**Validation**:
- [ ] Valid callback (code + matching state) extracts correctly
- [ ] Missing code raises CallbackValidationError
- [ ] State mismatch raises CallbackValidationError
- [ ] error parameter triggers CallbackError

---

### T006: Create StateManager for PKCE State Persistence

**Purpose**: Manage PKCEState lifecycle: generate, store, retrieve, validate, cleanup.

**Steps**:
1. Create `src/specify_cli/auth/loopback/state_manager.py`:
   ```python
   class StateManager:
       """Manage PKCEState for authorization code flow."""
       
       def __init__(self, storage_dir: Optional[Path] = None):
           # Store in temp dir or ~/.cache/spec-kitty/pkce_state/
           self.storage_dir = storage_dir or Path.home() / '.cache' / 'spec-kitty' / 'pkce_state'
           self.storage_dir.mkdir(parents=True, exist_ok=True)
       
       def generate(self) -> PKCEState:
           """Generate new PKCEState, store it, return."""
           state_id = str(uuid.uuid4())
           verifier, challenge = generate_pkce_pair()
           
           pkce_state = PKCEState(
               state=state_id,
               code_verifier=verifier,
               code_challenge=challenge,
               code_challenge_method="S256",
               created_at=datetime.utcnow(),
               expires_at=datetime.utcnow() + timedelta(minutes=5)
           )
           
           # Persist to file (JSON)
           state_file = self.storage_dir / f"{state_id}.json"
           with open(state_file, 'w') as f:
               json.dump(pkce_state.to_dict(), f)
           
           return pkce_state
       
       def retrieve(self, state_id: str) -> Optional[PKCEState]:
           """Retrieve PKCEState by ID."""
           state_file = self.storage_dir / f"{state_id}.json"
           if not state_file.exists():
               return None
           
           with open(state_file) as f:
               data = json.load(f)
           
           pkce_state = PKCEState.from_dict(data)
           
           if pkce_state.is_expired():
               state_file.unlink()  # Clean up expired state
               return None
           
           return pkce_state
       
       def cleanup(self, state_id: str):
           """Delete state file after use."""
           state_file = self.storage_dir / f"{state_id}.json"
           state_file.unlink(missing_ok=True)
   ```

2. Implement serialization (to_dict, from_dict for PKCEState)

**Files**:
- `src/specify_cli/auth/loopback/state_manager.py` (new, ~80 lines)

**Validation**:
- [ ] generate() creates and persists PKCEState
- [ ] retrieve() loads state from disk
- [ ] Expired states are cleaned up automatically
- [ ] cleanup() removes state file

---

### T007: Implement Cross-Platform Browser Launcher

**Purpose**: Open user's default browser to the OAuth authorization URL, handling platform differences.

**Steps**:
1. Create `src/specify_cli/auth/loopback/browser_launcher.py`:
   ```python
   import webbrowser
   import subprocess
   import platform
   from typing import Optional
   
   class BrowserLauncher:
       """Open browser to OAuth authorize endpoint."""
       
       @staticmethod
       def launch(auth_url: str) -> bool:
           """Open default browser to URL.
           
           Returns: True if successful, False if no browser available.
           """
           try:
               # Try standard webbrowser module (works on most platforms)
               if webbrowser.open(auth_url):
                   return True
               
               # Fallback: try platform-specific commands
               system = platform.system()
               if system == "Darwin":  # macOS
                   subprocess.run(["open", auth_url], check=True)
                   return True
               elif system == "Linux":
                   subprocess.run(["xdg-open", auth_url], check=True)
                   return True
               elif system == "Windows":
                   subprocess.run(["start", auth_url], shell=True, check=True)
                   return True
               
               return False
           except Exception:
               return False
   ```

2. Handle failures gracefully (return False, don't raise)

**Files**:
- `src/specify_cli/auth/loopback/browser_launcher.py` (new, ~40 lines)

**Validation**:
- [ ] webbrowser.open() is called
- [ ] Platform-specific fallbacks work on macOS/Linux/Windows
- [ ] Failures return False without raising

---

### T008 & T009: Write Unit Tests

**Purpose**: Comprehensive unit tests for PKCE generation, state management, and loopback server.

**Tests**:
1. PKCE Tests (`tests/auth/test_pkce.py`):
   - [ ] code_verifier is exactly 43 characters
   - [ ] code_challenge is SHA256(verifier) base64url
   - [ ] Multiple calls generate different values
   - [ ] For known verifier, challenge matches expected

2. State Management Tests (`tests/auth/test_loopback_state_manager.py`):
   - [ ] generate() creates valid PKCEState
   - [ ] retrieve() loads state from disk
   - [ ] Expired states return None
   - [ ] cleanup() removes state file

3. Callback Server Tests (`tests/auth/test_loopback_callback_server.py`):
   - [ ] Server starts on available port
   - [ ] GET /callback?code=X&state=Y is received
   - [ ] Timeout raises CallbackTimeoutError
   - [ ] Server stops cleanly

4. Callback Handler Tests (`tests/auth/test_loopback_callback_handler.py`):
   - [ ] Valid callback extracts (code, state)
   - [ ] Missing code raises error
   - [ ] State mismatch raises error
   - [ ] error parameter from SaaS raises CallbackError

**Files**:
- `tests/auth/test_pkce.py` (new, ~80 lines)
- `tests/auth/test_loopback_state_manager.py` (new, ~100 lines)
- `tests/auth/test_loopback_callback_server.py` (new, ~120 lines)
- `tests/auth/test_loopback_callback_handler.py` (new, ~80 lines)

**Coverage Goal**: 100% coverage for all new modules

---

## Implementation Sketch

```
1. Define PKCEState model (T001)
2. Implement PKCE generation (T002, T003)
3. Build loopback server (T004)
4. Add callback parsing and validation (T005)
5. Create state persistence manager (T006)
6. Add browser launcher (T007)
7. Write comprehensive tests (T008, T009)
```

## Definition of Done

- [ ] All subtasks completed
- [ ] All unit tests pass
- [ ] 100% code coverage for new modules
- [ ] PKCE generation is cryptographically secure
- [ ] Loopback server handles timeout and cleanup
- [ ] State validation prevents CSRF attacks
- [ ] Cross-platform browser launching works
- [ ] No TODOs or FIXMEs in code
- [ ] Code is peer-reviewed and approved

## Risks & Edge Cases

**Risk**: Firewall or network issues block loopback ports
- **Mitigation**: Try multiple ports (28888-28898), fall back to OS assignment

**Risk**: Browser already has authorization cached
- **Mitigation**: Users may skip SaaS login; explain in docs

**Risk**: State file corruption or permission errors
- **Mitigation**: Graceful error handling, retry with fallback

**Risk**: PKCE verifier leaked in browser history
- **Mitigation**: Document to users; use private/incognito mode

## Reviewer Guidance

Look for:
- [ ] PKCE verifier is cryptographically random (uses secrets module)
- [ ] code_challenge is correct SHA256(verifier) encoding
- [ ] State validation prevents CSRF (exact string match)
- [ ] Callback timeout is exactly 5 minutes (300 seconds)
- [ ] Loopback server cleans up resources (no hanging connections)
- [ ] Error messages are user-friendly (actionable guidance)
- [ ] Tests cover happy path and error cases
- [ ] No secrets (tokens, keys) logged or exposed

