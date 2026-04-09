---
work_package_id: WP07
title: HTTP Transport Integration + 401 Retry
dependencies:
- WP04
requirement_refs:
- FR-014
- FR-015
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T049
- T050
- T051
- T052
- T053
- T054
- T055
- T056
history: []
authoritative_surface: src/specify_cli/auth/http/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/http/**
- tests/auth/test_http_transport.py
status: pending
tags: []
---

# WP07: HTTP Transport Integration + 401 Retry

**Objective**: Integrate OAuth authentication into HTTP client layer. All API calls automatically inject bearer tokens and auto-refresh on 401.

**Context**: Critical for WP09 (commands). Depends on WP04 (TokenManager).

**Acceptance Criteria**:
- [ ] OAuthHttpClient wraps httpx with token injection
- [ ] Bearer token added to all requests
- [ ] 401 responses trigger auto-refresh
- [ ] Single-shot retry after refresh
- [ ] Error propagation for non-401 errors
- [ ] All tests pass (100% coverage)

---

## Implementation Guidance

Create `src/specify_cli/auth/http/transport.py`:
```python
class OAuthHttpClient:
    def __init__(self, token_manager: TokenManager):
        self.tm = token_manager
        self.client = httpx.AsyncClient()
    
    async def request(self, method, url, **kwargs) -> httpx.Response:
        """Perform HTTP request with OAuth.
        
        - Injects bearer token
        - Retries on 401 with refresh
        - Propagates other errors
        """
        token = await self.tm.get_access_token()
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        kwargs['headers'] = headers
        
        response = await self.client.request(method, url, **kwargs)
        
        if response.status_code == 401:
            # Try refresh and retry once
            if await self.tm.refresh_if_needed():
                token = await self.tm.get_access_token()
                headers['Authorization'] = f'Bearer {token}'
                response = await self.client.request(method, url, **kwargs)
        
        return response
```

**Files**:
- `src/specify_cli/auth/http/transport.py` (~80 lines)
- `tests/auth/test_http_transport.py` (~120 lines)

---

## Definition of Done

- [ ] Bearer token injected into all requests
- [ ] 401 trigger refresh + 1x retry
- [ ] Non-401 errors passed through unchanged
- [ ] All tests pass

