# Research: Identity-Aware CLI Event Sync

**Feature**: 032-identity-aware-cli-event-sync
**Date**: 2026-02-07
**Status**: Complete (minimal research needed - requirements clear from discovery)

## Research Summary

This feature has clear requirements from the discovery phase. Minimal research needed.

## Decisions Made During Planning

### 1. Runtime Bootstrap Pattern

**Decision**: Lazy Singleton via `get_emitter()`

**Alternatives Considered**:
- (A) Typer Callback - Rejected: Adds 50-100ms overhead to every command
- (C) Decorator - Rejected: Brittle, requires maintaining decorator list

**Rationale**: Zero overhead for non-event commands, centralized, fits existing 2.x structure.

### 2. Config Schema Evolution

**Decision**: Graceful Backfill with atomic writes

**Alternatives Considered**:
- (B) Explicit Migration - Rejected: Adds friction for existing projects
- (C) Init-Only Generation - Rejected: Poor UX, requires user action

**Rationale**: Seamless UX, handles read-only repos gracefully, no migration needed.

### 3. Identity Scope

**Decision**: 
- `project_uuid`: Per project, stable, stored in config.yaml
- `node_id`: Per machine, stable across sessions, stored in config.yaml
- `project_slug`: Derived from repo directory name or git remote

**Rationale**: Enables SaaS to uniquely identify projects and track which machines contribute.

## Existing Infrastructure (2.x Branch)

Based on discovery, the following modules exist on 2.x:

| Module | Status | Notes |
|--------|--------|-------|
| `sync/client.py` | EXISTS | WebSocketClient with reconnection |
| `sync/emitter.py` | EXISTS | EventEmitter with all event types |
| `sync/auth.py` | EXISTS | AuthClient (missing get_team_slug) |
| `sync/queue.py` | EXISTS | OfflineQueue for local persistence |
| `sync/clock.py` | EXISTS | LamportClock for causal ordering |
| `sync/config.py` | EXISTS | SyncConfig class |
| `sync/background.py` | EXISTS | BackgroundSyncService |
| `implement.py` | EXISTS | Has duplicate emission issue |
| `accept.py` | EXISTS | Has duplicate emission issue |

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `ulid` | existing | Generate ULIDs for event_id |
| `uuid` | stdlib | Generate project_uuid (UUID4) |
| `ruamel.yaml` | existing | Parse/write config.yaml |
| `websockets` | existing | WebSocket client |

## No Outstanding Clarifications

All NEEDS CLARIFICATION items were resolved during discovery:
- Runtime bootstrap: Lazy Singleton ✅
- Config schema: Graceful Backfill ✅
- Default behavior: Always-on with graceful degradation ✅
