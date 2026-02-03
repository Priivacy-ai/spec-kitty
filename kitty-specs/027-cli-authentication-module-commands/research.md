# Research Decision Log

Document the outcomes of Phase 0 discovery work.

## Summary

- **Feature**: 027-cli-authentication-module-commands
- **Date**: 2026-02-03
- **Research Status**: MINIMAL - Leverages Feature 009 research

This feature was extracted from Feature 009 (CLI-SaaS Event Sync and Dashboards). The Phase 0 research for Feature 009 already investigated:
- CLI repository structure (spec-kitty 2.x branch)
- SaaS authentication endpoints
- Existing sync infrastructure

See: `kitty-specs/009-cli-saas-event-sync-dashboards/research.md`

---

## Decisions & Rationale

| Decision | Rationale | Evidence | Status |
|----------|-----------|----------|--------|
| Use TOML for credentials | Consistency with existing config.toml pattern | CLI already uses toml library for SyncConfig | Final |
| Store in ~/.spec-kitty/credentials | Standard XDG-like location, matches config.toml | Existing config pattern in sync/config.py | Final |
| Use httpx for HTTP client | Already in spec-kitty dependencies, async-capable | pyproject.toml shows httpx dependency | Final |
| Use filelock for file locking | Cross-platform, prevents credential race conditions | Standard Python library for this use case | Final |
| Silent token refresh | User confirmed during planning interrogation | Planning session 2026-02-03 | Final |

---

## Key Findings from Feature 009 Research

### CLI Repository (spec-kitty 2.x)

**Verified Components**:
- `sync/auth.py` - Empty file, needs full implementation
- `sync/client.py` - WebSocketClient expects token parameter (235 lines)
- `sync/config.py` - SyncConfig with server_url (38 lines)
- `sync/queue.py` - OfflineQueue implementation (204 lines)
- `sync/batch.py` - Batch sync implementation (238 lines)

**Key Insight**: The sync infrastructure is complete except for authentication. The `WebSocketClient.__init__()` takes a `token` parameter - this feature provides the mechanism to obtain that token.

### SaaS Repository (spec-kitty-saas)

**Authentication Endpoints (Feature 008)**:
- `POST /api/v1/token/` - Obtain access + refresh tokens
- `POST /api/v1/token/refresh/` - Refresh access token
- `POST /api/v1/ws-token/` - Exchange access token for WebSocket token

**JWT Configuration**:
- Access token TTL: 15 minutes
- Refresh token TTL: 7 days
- Token rotation enabled (new refresh token on each refresh)

**Verified via**: `/tmp/spec-kitty-test/test_api.sh` test script

---

## Open Questions

None - all questions resolved during planning.

---

## References

- Feature 009 Research: `kitty-specs/009-cli-saas-event-sync-dashboards/research.md`
- Feature 008 Plan: `kitty-specs/008-sync-protocol-rest-websocket/plan.md`
- Test Script: `/tmp/spec-kitty-test/test_api.sh`

---

**END OF RESEARCH**
