---
work_package_id: WP08
title: WebSocket Pre-Connect Token Provisioning
dependencies:
- WP04
- WP07
requirement_refs:
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Work in execution worktree; merge to main via finalized lanes
subtasks:
- T057
- T058
- T059
- T060
- T061
- T062
- T063
- T064
history: []
authoritative_surface: src/specify_cli/auth/websocket/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/websocket/**
- tests/auth/test_websocket_provisioning.py
status: pending
tags: []
---

# WP08: WebSocket Pre-Connect Token Provisioning

**Objective**: Implement team-aware WebSocket token provisioning. Fetches team list, refreshes access token before upgrade, obtains ephemeral WS token.

**Context**: Enables WebSocket connections in commands. Depends on WP04 (TokenManager), WP07 (HTTP transport).

**Acceptance Criteria**:
- [ ] /api/v1/me call fetches user teams
- [ ] Pre-connect refresh if access token expires soon (within 5 min)
- [ ] /api/v1/ws-token called with team_id
- [ ] Ephemeral token (1-hour TTL) obtained
- [ ] WebSocket upgrade with query parameter token
- [ ] All tests pass (100% coverage)

---

## Implementation Guidance

Create `src/specify_cli/auth/websocket/provisioner.py`:
```python
class TokenProvisioner:
    def __init__(self, token_manager: TokenManager, http_client):
        self.tm = token_manager
        self.client = http_client
    
    async def provision_ws_token(self, team_id: str) -> dict:
        """Pre-connect setup: refresh if needed, get ephemeral token.
        
        Returns: {ws_token, ws_url, expires_in, session_id}
        """
        # Refresh if expires within 5 minutes
        await self.tm.ensure_fresh(min_ttl_seconds=300)
        
        # Get ephemeral token
        response = await self.client.post(
            'https://api.spec-kitty.com/api/v1/ws-token',
            json={'team_id': team_id}
        )
        response.raise_for_status()
        return response.json()
```

**Files**:
- `src/specify_cli/auth/websocket/provisioner.py` (~60 lines)
- `tests/auth/test_websocket_provisioning.py` (~100 lines)

---

## Definition of Done

- [ ] Pre-connect refresh works
- [ ] Ephemeral token obtained
- [ ] WebSocket URL and token provided to caller
- [ ] Error handling for not-team-member (403)

