---
work_package_id: WP04
title: TokenManager Architecture + Session Model
dependencies:
- WP03
requirement_refs:
- FR-007
- FR-008
- FR-011
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
- T031
- T032
history: []
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/session.py
- src/specify_cli/auth/token_manager.py
- tests/auth/test_token_manager.py
status: pending
tags: []
---

# WP04: TokenManager Architecture + Session Model

**Objective**: Build the centralized credential provisioning engine (TokenManager) and session data models. This is the hub that all CLI commands and transports use for token access.

**Context**: Foundation for WP05-WP08. Depends on WP03 (SecureStorage).

**Acceptance Criteria**:
- [ ] StoredSession captures user, teams[], tokens, expiry
- [ ] TokenManager provides thread-safe token access
- [ ] Single-flight refresh coordination prevents thundering herd
- [ ] get_access_token() auto-refreshes if expired
- [ ] Async internals with sync boundary for CLI
- [ ] All tests pass (100% coverage)

---

## Subtask Guidance

### T025-T027: Create Data Models

**StoredSession** (`src/specify_cli/auth/session.py`):
```python
@dataclass
class Team:
    id: str
    name: str
    role: str

@dataclass
class StoredSession:
    user_id: str
    username: str
    name: str
    teams: list[Team]              # From /api/v1/me
    default_team_id: str           # User's default for WebSocket
    
    access_token: str
    refresh_token: str
    session_id: str
    
    issued_at: datetime
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    
    scope: str
    storage_backend: str
    last_used_at: datetime
    auth_method: str  # "authorization_code" | "device_flow"
```

**OAuthToken, ComputedTokenExpiry** - helper classes for expiry management.

**Files**: `src/specify_cli/auth/session.py` (~100 lines)

---

### T028-T031: Implement TokenManager

```python
class TokenManager:
    def __init__(self, secure_storage: SecureStorage):
        self.storage = secure_storage
        self.session: Optional[StoredSession] = None
        self._refresh_lock = asyncio.Lock()
    
    async def load_from_storage(self):
        """Load session on startup."""
        self.session = await self.storage.read()
    
    async def get_access_token(self) -> str:
        """Return token, auto-refresh if needed."""
        if not self.session:
            raise NotAuthenticatedError()
        
        if self.session.access_token_expires_at < datetime.utcnow() + timedelta(seconds=5):
            # Refresh if expires within 5 seconds
            await self.refresh_if_needed()
        
        return self.session.access_token
    
    async def refresh_if_needed(self) -> bool:
        """Refresh access token. Return True if successful."""
        async with self._refresh_lock:
            # Single-flight: only one thread refreshes at a time
            # Call /oauth/token with refresh_token grant
            # Update self.session with new tokens
            # Save to storage
            pass
    
    def get_current_session(self) -> Optional[StoredSession]:
        """Sync access to current session."""
        return self.session
    
    @property
    def is_authenticated(self) -> bool:
        return self.session is not None and not self._is_expired()
```

**Files**: `src/specify_cli/auth/token_manager.py` (~150 lines)

---

### T032: Write Unit Tests

**Tests** (`tests/auth/test_token_manager.py`):
- [ ] load_from_storage() loads session
- [ ] get_access_token() returns valid token
- [ ] Auto-refresh triggers when expires soon
- [ ] Single-flight refresh (10 concurrent calls = 1 /oauth/token request)
- [ ] Refresh failures handled gracefully
- [ ] Session state persists across load/save

**Files**: `tests/auth/test_token_manager.py` (~120 lines)

---

## Definition of Done

- [ ] All models serialize/deserialize correctly
- [ ] TokenManager is thread-safe (asyncio.Lock)
- [ ] Single-flight refresh works under concurrency
- [ ] Auto-refresh buffer is 5 seconds
- [ ] No token leaks in logs or error messages

