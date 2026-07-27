# Quickstart: Identity-Aware CLI Event Sync

**Feature**: 032-identity-aware-cli-event-sync
**Date**: 2026-02-07

## What This Feature Does

After this feature is implemented:

1. **Every CLI command that emits events** (implement, accept, merge, etc.) will include project identity (`project_uuid`, `project_slug`) in the event envelope.

2. **Background sync starts automatically** when you run any event-emitting command. No need to run `spec-kitty sync now` manually.

3. **Graceful degradation**: If you're not authenticated, events are queued locally and synced later.

## For Users

### Before (Current 2.x Behavior)

```bash
# Events emitted but lack project identity
spec-kitty implement WP01
# SaaS can't attribute events to your project :(
```

### After (This Feature)

```bash
# Events include project_uuid automatically
spec-kitty implement WP01
# SaaS shows your project's work packages in dashboard :)
```

### Opt-Out (If Needed)

Add to `.kittify/config.yaml`:
```yaml
sync:
  auto_start: false
```

## For Developers

### Key Files

| File | Purpose |
|------|---------|
| `sync/project_identity.py` | Generate and persist project identity |
| `sync/runtime.py` | Lazy singleton for sync services |
| `sync/emitter.py` | Inject identity into events |
| `sync/auth.py` | Team slug resolution |

### Testing

```bash
# Run sync tests
pytest tests/sync/ -v

# Run integration tests
pytest tests/integration/test_sync_e2e.py -v

# Type check
mypy src/specify_cli/sync/ --strict
```

### Debugging

```bash
# Check if identity is set
cat .kittify/config.yaml | grep -A3 "project:"

# Check event emissions (verbose)
SPEC_KITTY_DEBUG=1 spec-kitty implement WP01 2>&1 | grep -i event
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Command                             │
│                  (implement, accept, ...)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   get_emitter() [Lazy Singleton]            │
│  1. Load/generate ProjectIdentity                           │
│  2. Start SyncRuntime (if not started)                      │
│  3. Return EventEmitter                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   EventEmitter._emit()                       │
│  1. Inject project_uuid, project_slug, team_slug            │
│  2. Validate identity present                               │
│  3. Route: WebSocket (if connected) OR queue (always)       │
└─────────────────────────────────────────────────────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼                              ▼
    ┌─────────────────┐            ┌─────────────────┐
    │  WebSocketClient │            │   OfflineQueue   │
    │  (if auth)       │            │   (always)       │
    └─────────────────┘            └─────────────────┘
```

## Related Documentation

- [spec.md](./spec.md) - Full specification
- [plan.md](./plan.md) - Implementation plan
- [data-model.md](./data-model.md) - Entity definitions
- [contracts/](./contracts/) - Event schema updates
