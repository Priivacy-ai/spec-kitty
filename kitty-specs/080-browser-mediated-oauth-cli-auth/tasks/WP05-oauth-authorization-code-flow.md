---
work_package_id: WP05
title: OAuth Authorization Code Flow Implementation
dependencies:
- WP01
- WP03
- WP04
requirement_refs:
- FR-001
- FR-002
- FR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
- T039
- T040
history: []
authoritative_surface: src/specify_cli/auth/flows/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/flows/authorization_code.py
- tests/auth/test_authorization_code_flow.py
- tests/auth/test_loopback_integration.py
status: pending
tags: []
---

# WP05: OAuth Authorization Code Flow Implementation

**Objective**: Implement interactive browser-based login orchestration using Authorization Code + PKCE. Coordinates loopback callback (WP01) and token exchange.

**Context**: Core user-facing feature. Depends on WP01 (loopback), WP03 (storage), WP04 (TokenManager).

**Acceptance Criteria**:
- [ ] Browser opens to authorization endpoint
- [ ] Callback received and validated
- [ ] Authorization code exchanged for tokens
- [ ] Session stored in secure storage
- [ ] User-friendly error messages
- [ ] All tests pass (100% coverage)

---

## Subtask Guidance

### T033-T037: Implement Auth Code Flow Orchestration

Create `src/specify_cli/auth/flows/authorization_code.py`:
```python
class AuthorizationCodeFlow:
    def __init__(self, token_manager, secure_storage, browser_launcher):
        self.tm = token_manager
        self.storage = secure_storage
        self.launcher = browser_launcher
        self.state_manager = StateManager()
    
    async def login(self) -> StoredSession:
        """Execute interactive browser login.
        
        Returns: StoredSession on success
        Raises: AuthFlowError on failure
        """
        # 1. Generate PKCE state
        pkce_state = self.state_manager.generate()
        
        # 2. Start loopback callback server
        callback_server = CallbackServer()
        callback_url = await callback_server.start()
        
        # 3. Open browser
        auth_url = self._build_auth_url(pkce_state, callback_url)
        self.launcher.launch(auth_url)
        
        try:
            # 4. Wait for callback
            callback_params = await callback_server.wait_for_callback()
            
            # 5. Validate callback
            handler = CallbackHandler(pkce_state.state)
            code, state = handler.validate(callback_params)
            
            # 6. Exchange code for tokens
            tokens = await self._exchange_code(code, pkce_state.code_verifier)
            
            # 7. Fetch user info and store session
            session = await self._create_session(tokens)
            await self.storage.write(session)
            
            return session
        
        finally:
            await callback_server.stop()
            self.state_manager.cleanup(pkce_state.state)
    
    def _build_auth_url(self, pkce_state, callback_url) -> str:
        """Construct authorization endpoint URL."""
        params = {
            'client_id': 'cli_native',
            'redirect_uri': callback_url,
            'response_type': 'code',
            'scope': 'offline_access',
            'code_challenge': pkce_state.code_challenge,
            'code_challenge_method': 'S256',
            'state': pkce_state.state,
        }
        return f"https://api.spec-kitty.com/oauth/authorize?" + urllib.parse.urlencode(params)
    
    async def _exchange_code(self, code: str, code_verifier: str) -> dict:
        """POST /oauth/token with code and verifier."""
        # Call SaaS /oauth/token endpoint
        # Return: {access_token, refresh_token, expires_in, scope, session_id}
        pass
    
    async def _create_session(self, tokens: dict) -> StoredSession:
        """Create StoredSession from token response and user info."""
        # Call /api/v1/me to get user, teams
        # Create StoredSession with all data
        pass
```

**Files**: `src/specify_cli/auth/flows/authorization_code.py` (~200 lines)

---

### T038: Implement Error Handling

Handle these errors:
- `CallbackTimeoutError`: Show "Authorization timeout. Please try again."
- `CallbackError` (error_code from SaaS): Show user-friendly message
- Network errors: Show "Failed to exchange authorization code: [error]. Retry with `auth login`."
- Missing fields in token response: Show "Authorization response missing required fields."

---

### T039-T040: Write Tests

**Unit Tests** (`tests/auth/test_authorization_code_flow.py`):
- [ ] Flow succeeds with valid callback
- [ ] State validation prevents CSRF
- [ ] Code exchange succeeds with correct response
- [ ] Error handling for access_denied, timeout, network error
- [ ] Session is stored and retrievable

**Integration Tests**:
- [ ] Full end-to-end flow with mock OAuth provider

**Files**: `tests/auth/test_authorization_code_flow.py` (~150 lines)

---

## Definition of Done

- [ ] Browser opens automatically
- [ ] User can log in via SaaS
- [ ] Callback is received and parsed
- [ ] Tokens are exchanged successfully
- [ ] Session is persisted
- [ ] Error messages guide user recovery

