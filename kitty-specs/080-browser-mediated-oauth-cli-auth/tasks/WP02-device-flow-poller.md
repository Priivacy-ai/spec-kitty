---
work_package_id: WP02
title: Device Authorization Flow Poller
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
- T016
history: []
authoritative_surface: src/specify_cli/auth/device_flow_poller/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/device_flow_poller/**
- tests/auth/test_device_flow_poller.py
status: pending
tags: []
---

# WP02: Device Authorization Flow Poller

**Objective**: Implement the polling loop for Device Authorization Flow (RFC 8628), enabling headless login for SSH sessions and CI/CD environments without browser access.

**Context**: Foundational for WP06 (device flow + refresh). Can be implemented in parallel with WP01 (loopback).

**Acceptance Criteria**:
- [ ] Device code polling respects `interval` from SaaS (capped at 10 seconds on CLI)
- [ ] Polling continues until approval, denial, or expiry
- [ ] State transitions tracked (pending → approved/denied/expired)
- [ ] Error handling for authorization_pending, access_denied, expired_token
- [ ] User-friendly progress display ("Waiting for authorization... 14:23 remaining")
- [ ] All tests pass (100% coverage)

---

## Subtask Guidance (Condensed)

### T010: Create DeviceFlowState Dataclass

Create `src/specify_cli/auth/flows/device_code.py` with:
```python
@dataclass
class DeviceFlowState:
    device_code: str              # Opaque code from /oauth/device
    user_code: str                # Human-readable code (e.g., ABCD-1234)
    verification_uri: str         # URL user visits
    expires_in: int               # Device code lifetime (seconds, ~900)
    interval: int                 # Polling interval (seconds, default 5)
    created_at: datetime
    expires_at: datetime          # created_at + expires_in
    last_polled_at: Optional[datetime]
    poll_count: int               # Number of polling attempts
    status: str                   # "pending" | "approved" | "denied" | "expired"
```

**Files**: `src/specify_cli/auth/flows/device_code.py` (~80 lines)

---

### T011-T014: Implement Polling Loop

Create `DeviceFlowPoller` class:
```python
class DeviceFlowPoller:
    def __init__(self, device_state: DeviceFlowState, http_client):
        self.state = device_state
        self.client = http_client
    
    async def poll(self) -> dict:
        """Poll until approval, denial, or expiry.
        
        Returns: Token response dict on approval
        Raises: DeviceFlowError on denial/expiry/timeout
        """
        while not self.state.is_expired():
            try:
                token_response = await self._poll_once()
                if token_response:
                    return token_response  # Success
                
                # Still pending, wait and retry
                await asyncio.sleep(min(self.state.interval, 10))
            
            except DeviceFlowError as e:
                if e.is_terminal():  # denied, expired
                    raise
                # For transient errors, retry

    async def _poll_once(self) -> Optional[dict]:
        """Single polling attempt.
        
        Returns: Token response on approval, None on pending, raises on error
        """
        # Call POST /oauth/token with device_code
        # Handle responses:
        # - 200 OK: approval, return tokens
        # - 400 authorization_pending: continue polling
        # - 400 access_denied: raise DeviceFlowDenied
        # - 400 expired_token: raise DeviceFlowExpired
```

**Files**: `src/specify_cli/auth/flows/device_code.py` (continued, ~150 lines total)

**Validation**:
- [ ] Polling continues while status="pending"
- [ ] Polling stops on approval/denial/expiry
- [ ] Interval is respected (capped at 10s)
- [ ] Poll count increments on each attempt

---

### T015-T016: Unit & Integration Tests

Create `tests/auth/test_device_flow.py`:
- [ ] Polling loop succeeds after approval
- [ ] Polling fails on user denial
- [ ] Polling times out after expires_in seconds
- [ ] error: "authorization_pending" continues polling
- [ ] Error messages are user-friendly

**Files**: `tests/auth/test_device_flow.py` (~120 lines)

---

## Definition of Done

- [ ] All subtasks completed
- [ ] Polling loop tests pass
- [ ] Error handling covers all RFC 8628 error codes
- [ ] User sees progress message with countdown
- [ ] No polling loops hang or leak resources

