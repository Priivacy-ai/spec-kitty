# Research: CLI Event Emission + Sync

**Feature**: 028-cli-event-emission-sync
**Date**: 2026-02-03
**Status**: Complete

## Overview

This research consolidates findings from prior features (003, 007, 008, 027) and validates design decisions for this feature. No new research was required - all technical approaches are validated by existing feature research.

## Design Decisions

### D1: Singleton EventEmitter vs Stateless Functions

**Decision**: Singleton EventEmitter class with `get_emitter()` accessor

**Rationale**:
- Centralizes Lamport clock state (no re-hydration per command)
- Keeps auth context and multi-tenant routing in one place
- Easier to unit test (inject fake emitter/queue)
- Matches existing CLI patterns (`SyncConfig`, `OfflineQueue` are reusable instances)

**Alternatives Considered**:
- Stateless functions: Rejected - requires passing clock/auth context through every call
- Context manager only: Rejected - adds ceremony to simple emit calls

### D2: Event ID Generation

**Decision**: Use ULID (Universally Unique Lexicographically Sortable Identifier)

**Rationale**:
- Time-sortable (first 48 bits are timestamp)
- Globally unique (no coordination needed)
- Already used by spec-kitty-events library (Feature 003)
- Standard library available: `python-ulid`

**Alternatives Considered**:
- UUID v4: Not time-sortable
- UUID v7: Similar to ULID but ULID already in use

### D3: Lamport Clock Persistence

**Decision**: JSON file at `~/.spec-kitty/clock.json`

**Rationale**:
- Simple atomic read/write
- Human-readable for debugging
- Same directory as other spec-kitty config
- Fast for single-value persistence

**Alternatives Considered**:
- SQLite: Overkill for single integer
- In-memory only: Loses clock on restart (violates spec FR-005)

### D4: Sync Strategy

**Decision**: Queue-first with opportunistic WebSocket

**Rationale** (from Feature 008 research):
- Offline-first architecture (never block on network)
- Events durable even if WebSocket drops mid-send
- Batch sync more efficient than individual sends
- Matches Heroku, Linear, Supabase patterns

**Alternatives Considered**:
- WebSocket-first: Fails offline users
- REST-only: Higher latency for real-time

### D5: Non-Blocking Emission

**Decision**: Event emission failures never block CLI commands

**Rationale**:
- Core CLI must work offline
- Users should never be blocked by sync issues
- Better UX - sync happens in background
- Errors logged as warnings, not exceptions

**Alternatives Considered**:
- Blocking sync: Violates offline-first principle
- Silent failures: Users lose visibility

## Dependencies Validated

### spec-kitty-events (Feature 003)

**Status**: Available
**Version**: v0.1.0-alpha
**Integration**: Git dependency per ADR-11

**Provides**:
- `LamportClock` class with `tick()`, `receive()`, `value` property
- Event schema definitions (Pydantic models)
- `is_concurrent()` conflict detection
- ULID generation utilities

### AuthClient (Feature 027)

**Status**: Available
**Location**: `src/specify_cli/auth/client.py`

**Provides**:
- `is_authenticated()` - check auth status
- `get_access_token()` - JWT for API calls
- `get_team_slug()` - multi-tenant routing
- `refresh_token()` - automatic token refresh

### Existing Sync Infrastructure

**Status**: Available
**Location**: `src/specify_cli/sync/`

**Provides**:
- `OfflineQueue` - SQLite queue with 10K limit
- `batch_sync()` - gzip-compressed batch POST
- `WebSocketClient` - real-time connection
- `SyncConfig` - server URL configuration

## API Contract Reference

### Batch Sync Endpoint (Feature 008)

```
POST /api/v1/events/batch/
Authorization: Bearer {jwt_token}
Content-Type: application/json
Content-Encoding: gzip

{
  "events": [
    {
      "event_id": "01HX...",
      "event_type": "WPStatusChanged",
      "aggregate_id": "WP01",
      ...
    }
  ]
}

Response 200:
{
  "results": [
    {"event_id": "01HX...", "status": "success"},
    {"event_id": "01HY...", "status": "duplicate"},
    {"event_id": "01HZ...", "status": "error", "error_message": "..."}
  ]
}
```

### Multi-Tenant Routing

Events include `team_slug` in payload. Server filters by authenticated user's team. Cross-tenant access returns 403 Forbidden.

## Risks Addressed

| Risk | Research Finding | Mitigation |
|------|-----------------|------------|
| Event schema mismatch | spec-kitty-events provides Pydantic validation | Validate before queuing |
| Clock drift | Lamport clocks don't depend on wall time | Use Lamport, not timestamps |
| Concurrent queue access | SQLite handles locking natively | Use with retry logic |
| Token expiry mid-sync | Feature 027 provides refresh flow | Auto-refresh on 401 |

## Conclusion

No new research required. All technical approaches validated by:
- Feature 003: Event schemas, Lamport clocks
- Feature 007: Sync protocol research
- Feature 008: Batch sync contract
- Feature 027: Authentication flow

Implementation can proceed with confidence.

---

**END OF RESEARCH**
