---
work_package_id: WP06
title: Device Flow Implementation + Token Refresh
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-004
- FR-005
- FR-006
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
- T048
history: []
authoritative_surface: src/specify_cli/auth/flows/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/flows/device_code.py
- src/specify_cli/auth/flows/refresh.py
- tests/auth/test_device_flow.py
- tests/auth/test_device_flow_integration.py
status: pending
tags: []
---

# WP06: Device Flow Implementation + Token Refresh

**Objective**: Implement headless login (Device Authorization Flow) and token refresh mechanism. Enables CLI to keep sessions alive indefinitely with automatic token renewal.

**Context**: Core feature for WP09 (commands). Depends on WP02 (device poller), WP03 (storage), WP04 (TokenManager).

**Acceptance Criteria**:
- [ ] Device flow successfully obtains tokens after user approval
- [ ] Token refresh calls /oauth/token with refresh_token grant
- [ ] Refresh error handling (invalid_grant, expired_token, session_invalid)
- [ ] User sees progress during polling
- [ ] All tests pass (100% coverage)

---

## Subtask Guidance

### T041-T046: Device Flow Orchestration + Refresh

Create `src/specify_cli/auth/flows/device_code.py` (extend from WP02):
```python
class DeviceCodeFlow:
    async def login(self, poller: DeviceFlowPoller) -> StoredSession:
        """Execute headless login.
        
        Returns: StoredSession on approval
        Raises: DeviceFlowError on denial/expiry
        """
        # Show user_code and verification_uri
        # Poll for approval
        # On success: exchange tokens, fetch user info, store session
        pass
```

Create `src/specify_cli/auth/flows/refresh.py`:
```python
class TokenRefreshFlow:
    async def refresh(self, session: StoredSession) -> StoredSession:
        """Refresh access token using refresh_token grant.
        
        Returns: Updated session with new tokens
        Raises: RefreshError on failure
        """
        # POST /oauth/token with refresh_token grant
        # Parse response: new access_token, new refresh_token (if rotated)
        # Return updated session
        pass
```

**Files**:
- `src/specify_cli/auth/flows/device_code.py` (~120 lines)
- `src/specify_cli/auth/flows/refresh.py` (~80 lines)

---

### T047-T048: Tests

**Tests**:
- [ ] Device flow obtains tokens after user approval
- [ ] Refresh succeeds with valid refresh_token
- [ ] Refresh fails gracefully (invalid_grant, expired_token)
- [ ] Session_invalid error forces re-login
- [ ] Poll progress shown to user

**Files**: `tests/auth/test_device_flow.py` + `tests/auth/test_refresh.py` (~180 lines)

---

## Definition of Done

- [ ] Device code polling integrates with WP02 logic
- [ ] User sees clear progress message
- [ ] Refresh works transparently (TokenManager calls refresh when needed)
- [ ] Refresh errors handled appropriately

