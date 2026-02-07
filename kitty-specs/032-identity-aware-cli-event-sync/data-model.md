# Data Model: Identity-Aware CLI Event Sync

**Feature**: 032-identity-aware-cli-event-sync
**Date**: 2026-02-07

## Entities

### ProjectIdentity

Represents the unique identity of a spec-kitty project. Persisted in `.kittify/config.yaml`.

```python
@dataclass
class ProjectIdentity:
    """Unique identity for a spec-kitty project."""
    
    project_uuid: UUID | None = None
    """UUID4 identifying this project. Generated once, stable forever."""
    
    project_slug: str | None = None
    """Human-readable slug derived from repo directory or git remote."""
    
    node_id: str | None = None
    """Machine-unique identifier. Stable across sessions on same machine."""
    
    @property
    def is_complete(self) -> bool:
        """True if all identity fields are populated."""
        return all([self.project_uuid, self.project_slug, self.node_id])
    
    def with_defaults(self) -> "ProjectIdentity":
        """Return new identity with missing fields filled in."""
        return ProjectIdentity(
            project_uuid=self.project_uuid or uuid4(),
            project_slug=self.project_slug or derive_slug_from_repo(),
            node_id=self.node_id or generate_node_id(),
        )
```

**Persistence** (in `.kittify/config.yaml`):
```yaml
project:
  uuid: "550e8400-e29b-41d4-a716-446655440000"
  slug: "my-project"
  node_id: "node-abc123"
```

**Generation Rules**:
- `project_uuid`: UUID4, generated once per project
- `project_slug`: Kebab-case from directory name, or from git remote `origin` URL
- `node_id`: UUID4, generated once per machine (stable across restarts)

---

### EventEnvelope (Updated)

The event envelope includes identity metadata for attribution.

```python
# Existing fields (from spec-kitty-events)
event_id: str          # ULID
event_type: str        # e.g., "WPStatusChanged"
aggregate_id: str      # e.g., "WP01"
aggregate_type: str    # e.g., "WorkPackage"
payload: dict          # Event-specific data
timestamp: str         # ISO 8601
node_id: str           # From LamportClock
lamport_clock: int     # Causal ordering
causation_id: str | None  # Parent event

# NEW fields (this feature)
project_uuid: str      # UUID4 string (required for WebSocket send)
project_slug: str | None  # Human-readable slug (optional)
team_slug: str         # From auth or "local" if unauthenticated
```

**Validation Rules**:
- `project_uuid` MUST be present for WebSocket send (queue-only if missing)
- `project_uuid` MUST be valid UUID4 format
- `team_slug` defaults to "local" if not authenticated

---

### SyncRuntime

Manages background sync services. Singleton pattern.

```python
@dataclass
class SyncRuntime:
    """Background sync runtime managing WebSocket and queue."""
    
    background_service: BackgroundSyncService | None = None
    ws_client: WebSocketClient | None = None
    started: bool = False
    
    def start(self) -> None:
        """Start background services (idempotent)."""
        if self.started:
            return
        
        self.background_service = BackgroundSyncService()
        
        if is_authenticated():
            self.ws_client = WebSocketClient(...)
            self.ws_client.connect()
            self.background_service.set_ws_client(self.ws_client)
        else:
            logger.info("Not authenticated; events queued locally")
        
        self.background_service.start()
        self.started = True
    
    def stop(self) -> None:
        """Stop background services."""
        if self.background_service:
            self.background_service.stop()
        if self.ws_client:
            self.ws_client.disconnect()
        self.started = False
```

**Lifecycle**:
1. Created lazily on first `get_emitter()` call
2. Starts BackgroundSyncService unconditionally
3. Starts WebSocketClient only if authenticated
4. Stopped on process exit (atexit handler)

---

### Config.yaml Schema (Updated)

```yaml
# Existing fields
vcs:
  type: git
agents:
  available: [claude, opencode, codex]
  selection:
    strategy: random

# NEW fields (this feature)
project:
  uuid: "550e8400-e29b-41d4-a716-446655440000"
  slug: "my-project"
  node_id: "node-abc123"

sync:
  auto_start: true  # Optional, default true
```

---

## Relationships

```
ProjectIdentity (1) ─── persisted in ──→ Config.yaml (1)
       │
       │ injected into
       ▼
EventEnvelope (*) ─── routed by ──→ SyncRuntime (1)
       │                                   │
       │                                   │ manages
       │                                   ▼
       │                          BackgroundSyncService (1)
       │                                   │
       ├── if authenticated ──→ WebSocketClient (1)
       │
       └── always ──→ OfflineQueue (1)
```

---

## State Transitions

### Event Routing State Machine

```
                    ┌─────────────────┐
                    │  Event Created  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Has Identity?  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │ NO           │              │ YES
              ▼              │              ▼
    ┌─────────────────┐      │    ┌─────────────────┐
    │  Log Warning    │      │    │  Is Connected?  │
    │  Queue Only     │      │    └────────┬────────┘
    └─────────────────┘      │             │
                             │   ┌─────────┼─────────┐
                             │   │ NO      │         │ YES
                             │   ▼         │         ▼
                             │  Queue      │    Send via WS
                             │  Event      │    + Queue backup
                             └─────────────┴─────────────────
```
