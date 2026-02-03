# Feature Specification: CLI Event Emission + Sync

**Feature Branch**: `028-cli-event-emission-sync`
**Created**: 2026-02-03
**Status**: Draft
**Input**: Wire real event emission into 8 CLI commands and ensure events are queued and synced to SaaS via the Feature 008 contract.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CLI Command Emits Status Change Events (Priority: P0 - FOUNDATIONAL)

A developer using `spec-kitty implement WP01` needs the command to automatically emit a `WPStatusChanged` event (planned→doing) so that the team dashboard reflects the status change in real-time without manual intervention.

**Why this priority**: This is the core value proposition - CLI actions should automatically sync to the SaaS dashboard. Without event emission, there is no sync. This story validates the entire event factory and queue infrastructure.

**Independent Test**: Can be fully tested by running `spec-kitty implement WP01` after `spec-kitty auth login`, then verifying an event appears in the local offline queue (if disconnected) or is sent via WebSocket/batch sync (if connected).

**Acceptance Scenarios**:

1. **Given** user is authenticated (`spec-kitty auth login` completed), **When** running `spec-kitty implement WP01`, **Then** a `WPStatusChanged` event is emitted with `previous_status=planned`, `new_status=doing`, correct `aggregate_id`, and valid Lamport clock metadata
2. **Given** user is offline (no network connection), **When** running `spec-kitty implement WP01`, **Then** the event is queued to local SQLite queue (`~/.spec-kitty/queue.db`) and CLI displays `[Offline]` indicator
3. **Given** user is online and authenticated, **When** event is emitted, **Then** event is sent via WebSocket within 500ms or queued for batch sync if WebSocket unavailable
4. **Given** event emission fails (schema validation error), **When** CLI attempts to emit, **Then** core CLI action (workspace creation) still succeeds and failure is logged to console with warning

---

### User Story 2 - Batch Sync Replays Offline Events (Priority: P0 - FOUNDATIONAL)

A developer who worked offline for several hours needs their queued events to sync automatically when connectivity resumes so that the dashboard reflects all work done during the offline period.

**Why this priority**: Offline-first is a core requirement. Without batch sync working with real events, the system cannot deliver on the "never lose work" promise.

**Independent Test**: Can be tested by disconnecting network, performing CLI actions (implement, move-task), reconnecting, and verifying all events reach the server via batch sync endpoint.

**Acceptance Scenarios**:

1. **Given** 50 events queued during offline work, **When** network connectivity resumes and batch sync runs, **Then** all events are sent to `/api/v1/events/batch/` with gzip compression and JWT authentication
2. **Given** batch sync completes successfully, **When** server returns per-event status, **Then** successfully synced events are removed from local queue
3. **Given** some events fail validation (e.g., invalid Lamport clock), **When** batch sync returns errors, **Then** failed events remain in queue with incremented retry count and success/failure summary is displayed
4. **Given** queue contains 5000+ events from extended offline work, **When** batch sync runs, **Then** events are processed in batches of 1000 with progress indicator displayed

---

### User Story 3 - Task Commands Emit Workflow Events (Priority: P1)

An agent using `spec-kitty agent tasks move-task WP01 --to for_review` needs the command to emit a `WPStatusChanged` event so that the dashboard kanban board updates when work packages move between lanes.

**Why this priority**: Task commands are the primary interface for status updates. Dashboard value depends on these events flowing through correctly.

**Independent Test**: Can be tested by running move-task command and verifying event appears in queue or is synced to server.

**Acceptance Scenarios**:

1. **Given** WP01 is in `doing` lane, **When** running `spec-kitty agent tasks move-task WP01 --to for_review`, **Then** `WPStatusChanged` event is emitted with `previous_status=doing`, `new_status=for_review`
2. **Given** WP01 lane change succeeds, **When** event is emitted, **Then** event contains correct `team_slug` from auth context for multi-tenant routing
3. **Given** WP01 lane change is triggered by merge command, **When** merge completes, **Then** `WPStatusChanged` event is emitted with `doing→for_review` transition
4. **Given** multiple task commands run in sequence, **When** each command completes, **Then** Lamport clock is incremented correctly for each event (monotonically increasing)
5. **Given** a task command fails with a validation/runtime error, **When** the error is handled, **Then** an `ErrorLogged` event is emitted with `error_type`, `error_message`, and `agent_id` (if available)

---

### User Story 4 - Finalize-Tasks Emits Batch Creation Events (Priority: P1)

A developer running `spec-kitty agent feature finalize-tasks` needs the command to emit `WPCreated` events for all work packages and a `FeatureCreated` event so that the dashboard shows the new feature and its work packages immediately.

**Why this priority**: Feature initialization is a key moment - without these events, features don't appear in the dashboard at all.

**Independent Test**: Can be tested by running finalize-tasks after tasks.md is ready, verifying FeatureCreated + N x WPCreated events are emitted.

**Acceptance Scenarios**:

1. **Given** tasks.md defines 7 work packages, **When** running `spec-kitty agent feature finalize-tasks`, **Then** 1 `FeatureCreated` event + 7 `WPCreated` events are emitted
2. **Given** work packages have dependencies defined, **When** `WPCreated` events are emitted, **Then** each event payload includes `dependencies` array with WP IDs
3. **Given** finalize-tasks completes, **When** events are queued, **Then** all events share the same `causation_id` linking them to the finalize-tasks action
4. **Given** feature metadata exists (meta.json), **When** `FeatureCreated` is emitted, **Then** event includes `feature_slug`, `feature_number`, `target_branch`, `created_at`

---

### User Story 5 - Orchestrate Emits Assignment and Lifecycle Events (Priority: P1)

A developer running `spec-kitty orchestrate --feature 028-cli-event-emission-sync` needs the orchestrator to emit `WPAssigned` events when agents claim work packages so that the dashboard shows which agent is working on what.

**Why this priority**: Orchestration is the automated multi-agent workflow. Without assignment events, there's no visibility into agent activity.

**Independent Test**: Can be tested by running orchestrate with mock agents, verifying WPAssigned events are emitted when agents start work.

**Acceptance Scenarios**:

1. **Given** orchestrator assigns WP01 to `claude` agent, **When** implementation starts, **Then** `WPAssigned` event is emitted with `agent_id=claude`, `wp_id=WP01`, `phase=implementation`
2. **Given** WP01 implementation completes and review starts, **When** reviewer agent is assigned, **Then** second `WPAssigned` event is emitted with `phase=review`
3. **Given** agent fails and orchestrator retries with fallback agent, **When** new agent is assigned, **Then** `WPAssigned` event is emitted with new `agent_id` and `retry_count` metadata
4. **Given** orchestration completes all WPs, **When** feature is done, **Then** `FeatureCompleted` event is emitted with summary metadata
5. **Given** WP01 completes and unblocks WP02, **When** the dependency is resolved, **Then** a `DependencyResolved` event is emitted with `wp_id`, `dependency_wp_id`, and `resolution_type`

---

### User Story 6 - Connection Status Visible in CLI (Priority: P2)

A developer using any spec-kitty command needs to see sync connection status so they know whether their work is syncing in real-time or being queued for later.

**Why this priority**: User feedback is important but not blocking core functionality.

**Independent Test**: Can be tested by toggling network connectivity and observing CLI output indicators.

**Acceptance Scenarios**:

1. **Given** user is connected via WebSocket, **When** running any command that emits events, **Then** CLI displays `[Connected]` or similar indicator
2. **Given** WebSocket connection drops, **When** running command, **Then** CLI displays `[Offline]` and events queue locally
3. **Given** max reconnection attempts exhausted, **When** CLI falls back to batch mode, **Then** CLI displays `[Offline - Batch Mode]` and events continue queuing
4. **Given** user runs `spec-kitty sync status`, **When** executed, **Then** CLI shows queue size, connection state, and last sync timestamp

---

### User Story 7 - Background Sync Service Auto-Flushes Queue (Priority: P2)

A developer working in an active session needs queued events to sync automatically in the background so they don't have to manually trigger sync after each command.

**Why this priority**: Improves UX but core functionality works without it (manual batch sync).

**Independent Test**: Can be tested by starting background service, performing offline work, restoring connectivity, and verifying events sync without user action.

**Acceptance Scenarios**:

1. **Given** background sync service is running, **When** connectivity is restored after offline period, **Then** queued events automatically sync within 30 seconds
2. **Given** active CLI session with events queuing, **When** 5 minutes elapse since last sync, **Then** background service attempts batch sync if queue is non-empty
3. **Given** background sync encounters auth failure (token expired), **When** sync attempt fails with 401, **Then** service logs warning and waits for user to re-authenticate
4. **Given** user explicitly runs `spec-kitty sync now`, **When** executed, **Then** immediate batch sync is triggered regardless of background service state

---

### Edge Cases

**Network failure during event emission:**
- **Given** WebSocket send fails mid-transmission, **When** error detected, **Then** event is automatically queued to offline queue (no data loss)

**Invalid event schema:**
- **Given** event factory produces malformed event (missing required field), **When** validation runs, **Then** error is logged but CLI action is not blocked; event is discarded with warning

**Lamport clock desync:**
- **Given** local Lamport clock falls behind server (e.g., client restored from backup), **When** server rejects event with clock error, **Then** client reconciles by fetching current clock from server

**Queue overflow:**
- **Given** offline queue reaches 10,000 event limit, **When** user attempts new action, **Then** CLI warns but action proceeds; new event is dropped with explicit warning

**Concurrent event emission:**
- **Given** multiple CLI processes emit events simultaneously, **When** accessing shared queue.db, **Then** SQLite handles locking; events are serialized without corruption

**Token expiry during batch sync:**
- **Given** access token expires mid-batch-sync, **When** 401 response received, **Then** sync pauses, refresh token is used, and sync resumes automatically

---

## Requirements *(mandatory)*

### Functional Requirements

#### Event Factory Module

- **FR-001**: System MUST provide event factory at `src/specify_cli/sync/events.py` with builder functions for all 8 event types
- **FR-002**: Event factory MUST generate events conforming to spec-kitty-events library schemas (Feature 003)
- **FR-003**: Each event builder MUST accept domain parameters and return fully-formed event dict with: `event_id`, `event_type`, `aggregate_id`, `payload`, `node_id`, `lamport_clock`, `causation_id`, `timestamp`, `project_uuid`, `project_slug` (if available)
- **FR-004**: Event factory MUST use ULID for `event_id` generation (time-sortable, globally unique)
- **FR-005**: Event factory MUST manage Lamport clock state via `~/.spec-kitty/clock.json` or equivalent persistent storage
- **FR-006**: Event factory MUST increment Lamport clock on each event creation via `tick()` operation
- **FR-007**: Event factory MUST derive `node_id` from stable machine identifier (e.g., hostname + username hash)

#### Event Types

- **FR-008**: System MUST support `WPStatusChanged` event with fields: `wp_id`, `previous_status`, `new_status`, `changed_by` (agent or user)
- **FR-009**: System MUST support `WPCreated` event with fields: `wp_id`, `title`, `dependencies`, `feature_slug`
- **FR-010**: System MUST support `WPAssigned` event with fields: `wp_id`, `agent_id`, `phase` (implementation/review), `retry_count`
- **FR-011**: System MUST support `FeatureCreated` event with fields: `feature_slug`, `feature_number`, `target_branch`, `wp_count`
- **FR-012**: System MUST support `FeatureCompleted` event with fields: `feature_slug`, `completed_at`, `total_wps`, `total_duration`
- **FR-013**: System MUST support `HistoryAdded` event with fields: `wp_id`, `entry_type`, `entry_content`, `author`
- **FR-014**: System MUST support `ErrorLogged` event with fields: `wp_id`, `error_type`, `error_message`, `stack_trace`, `agent_id`
- **FR-015**: System MUST support `DependencyResolved` event with fields: `wp_id`, `dependency_wp_id`, `resolution_type`

#### Command Integration

- **FR-016**: `spec-kitty implement` MUST emit `WPStatusChanged(planned→doing)` after workspace creation succeeds
- **FR-017**: `spec-kitty merge` MUST emit `WPStatusChanged(doing→for_review)` when WP moves to review
- **FR-018**: `spec-kitty accept` MUST emit `WPStatusChanged(for_review→done)` when WP is accepted
- **FR-019**: `spec-kitty agent tasks move-task` MUST emit `WPStatusChanged` with correct status transition
- **FR-020**: `spec-kitty agent tasks mark-status` MUST emit `WPStatusChanged` with new status
- **FR-021**: `spec-kitty agent tasks add-history` MUST emit `HistoryAdded` event
- **FR-022**: `spec-kitty agent feature finalize-tasks` MUST emit `FeatureCreated` + `WPCreated` events for all WPs
- **FR-023**: `spec-kitty orchestrate` MUST emit `WPAssigned` events when agents are assigned to WPs

#### Queue and Sync Integration

- **FR-024**: All event emission MUST go through shared `emit_event()` function that handles queue/sync decision
- **FR-025**: `emit_event()` MUST check authentication status before attempting sync
- **FR-026**: `emit_event()` MUST queue events to OfflineQueue when WebSocket unavailable or user not authenticated
- **FR-027**: `emit_event()` MUST respect existing `SyncConfig` for server URL and settings
- **FR-028**: `emit_event()` MUST include `team_slug` from `AuthClient` session for multi-tenant routing
- **FR-029**: System MUST NOT block CLI command execution when event emission fails
- **FR-030**: System MUST log event emission failures to console as warnings (not errors that halt execution)

#### Team Slug Resolution

- **FR-028a**: `team_slug` MUST be sourced from the authenticated session (AuthClient credential store or token claims)
- **FR-028b**: If `team_slug` is unavailable, `emit_event()` MUST warn and queue the event without attempting sync until `team_slug` becomes available

#### Project Identity Resolution

- **FR-028c**: `project_uuid` MUST be sourced from `.kittify/config.yaml` (or equivalent) for the current project root
- **FR-028d**: If `project_uuid` is unavailable, `emit_event()` MUST warn and queue the event without attempting sync until identity is configured

#### Background Sync Service

- **FR-031**: System MUST provide background sync capability that periodically flushes queue
- **FR-032**: Background sync MUST use exponential backoff on repeated failures (500ms → 30s)
- **FR-033**: Background sync MUST respect rate limits (max 1000 events/batch, max 1 batch/5 seconds)
- **FR-034**: Background sync MUST authenticate using refresh token flow from Feature 027
- **FR-035**: Background sync MUST stop gracefully when CLI session ends

#### Connection Status

- **FR-036**: System MUST track connection status: Connected, Reconnecting, Offline, Offline-BatchMode
- **FR-037**: Connection status MUST be surfaceable via `spec-kitty sync status` command
- **FR-038**: Connection status SHOULD be displayed inline during event-emitting commands (non-blocking)

### Key Entities

- **Event**: Immutable sync record with causal metadata, conforming to spec-kitty-events schema
- **EventFactory**: Singleton providing builder methods for each event type, managing Lamport clock
- **OfflineQueue**: SQLite-backed queue for storing events when offline (already exists in `sync/queue.py`)
- **WebSocketClient**: Real-time connection for event streaming (already exists in `sync/client.py`)
- **BatchSyncResult**: Result object from batch sync operation (already exists in `sync/batch.py`)
- **SyncConfig**: Configuration for server URL and sync settings (already exists in `sync/config.py`)
- **AuthClient**: Authentication client from Feature 027 providing JWT tokens and team context

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `spec-kitty implement WP01` after authentication produces a `WPStatusChanged` event in the offline queue or synced to server
- **SC-002**: Running `spec-kitty merge` produces a `WPStatusChanged(doing→for_review)` event
- **SC-003**: Running `spec-kitty accept` produces a `WPStatusChanged(for_review→done)` event
- **SC-004**: Running `spec-kitty agent feature finalize-tasks` with 7 WPs produces 1 `FeatureCreated` + 7 `WPCreated` events
- **SC-005**: Running `spec-kitty orchestrate` produces `WPAssigned` events for each agent assignment
- **SC-006**: Offline queue correctly stores events when disconnected (verified by inspecting queue.db)
- **SC-007**: Batch sync successfully sends queued events to server when connectivity resumes
- **SC-008**: CLI commands complete successfully even when event emission fails (non-blocking behavior verified)
- **SC-009**: Lamport clock increments correctly across commands (verified via event inspection)
- **SC-010**: Events include correct `team_slug` for multi-tenant routing (verified via event inspection)
- **SC-011**: ErrorLogged events are emitted on command errors (verified via task command tests)
- **SC-012**: DependencyResolved events are emitted when dependencies are unblocked (verified via orchestrate tests)

---

## Assumptions *(optional)*

- **A-001**: Feature 027 (Auth) is complete and `AuthClient` is available with working JWT token management
- **A-002**: Feature 008 (Sync Protocol) contract is stable - batch endpoint accepts events in documented format
- **A-003**: Feature 003 (spec-kitty-events) library v0.1.0+ is available for schema validation
- **A-004**: Existing sync infrastructure (`OfflineQueue`, `batch_sync`, `WebSocketClient`) is functional
- **A-005**: SaaS server is deployed and accessible at configured URL (or tests use mock server)
- **A-006**: Multi-tenant routing works via `team_slug` header/parameter per Feature 008 contract

---

## Out of Scope *(optional)*

- **Dashboard UI changes** - This feature is CLI-only; dashboard work is separate
- **New authentication flows** - Uses existing Feature 027 auth; no new auth work
- **SaaS server modifications** - Server already implements Feature 008 contract
- **Event schema changes** - Uses existing spec-kitty-events schemas
- **WebSocket real-time streaming enhancements** - Use existing WebSocketClient for best-effort realtime when available; no new streaming features in this scope
- **Conflict resolution logic** - Server handles merges per Feature 003; CLI just emits events
- **Advanced telemetry** - Basic events only; detailed telemetry is Phase 4

---

## Dependencies *(optional)*

- **Feature 003: spec-kitty-events library** - Provides event schemas, Lamport clock, validation
- **Feature 008: Sync Protocol REST + WebSocket** - Defines batch sync endpoint, event format, API contract
- **Feature 027: OAuth2 Authentication** - Provides `AuthClient` with JWT tokens and team context
- **Existing sync module** - `src/specify_cli/sync/` with OfflineQueue, batch_sync, WebSocketClient, SyncConfig
- **Python 3.10+** - Language runtime (existing spec-kitty requirement)
- **httpx or requests** - HTTP client for batch sync (existing dependency)
- **websockets** - WebSocket client (existing dependency)

---

## Constraints *(optional)*

### Technical

- **MUST use spec-kitty-events schemas** - All events must conform to library definitions
- **MUST NOT block CLI commands** - Event emission failures must be non-blocking
- **MUST maintain offline-first behavior** - Core CLI works without network connectivity
- **MUST respect existing sync module structure** - Add events.py alongside existing files

### Security

- **MUST include team_slug for multi-tenant routing** - Prevents cross-tenant event leakage
- **MUST NOT log sensitive event payloads** - Warnings should not expose PII or tokens
- **MUST use JWT authentication for all sync operations** - No unauthenticated event sync

### Performance

- **<100ms event emission overhead** - Creating and queuing an event should not noticeably slow commands
- **Batch sync throughput >33 events/sec** - Matches Feature 008 requirement

---

## References

### Internal Documentation

- **Feature 008 Spec**: `spec-kitty-planning/kitty-specs/008-sync-protocol-rest-websocket/spec.md`
  - Batch sync endpoint: POST /api/v1/events/batch/
  - Event format and validation requirements
  - Multi-tenant routing via team filter

- **Feature 003 Spec**: `spec-kitty-planning/kitty-specs/003-event-log-causal-metadata-error-tracking-library/spec.md`
  - Event schema definitions
  - Lamport clock management
  - ULID event ID generation

- **Feature 027**: OAuth2 Authentication implementation
  - AuthClient for JWT token management
  - Team context for multi-tenant routing

- **Existing Sync Module**: `src/specify_cli/sync/`
  - `queue.py` - OfflineQueue implementation
  - `batch.py` - batch_sync function
  - `client.py` - WebSocketClient
  - `config.py` - SyncConfig

### External References

- **ULID Spec**: https://github.com/ulid/spec - Event ID format
- **Lamport Clocks**: https://en.wikipedia.org/wiki/Lamport_timestamp - Causal ordering

---

## Notes *(optional)*

### Work Package Structure

Based on user-provided analysis:

| WP | Scope | Size Estimate |
|----|-------|---------------|
| WP01 | Event factory module (sync/events.py) - create event builders for all 8 types | ~200 lines |
| WP02 | Wire events into implement, merge, accept commands | ~150 lines |
| WP03 | Wire events into move-task, mark-status, add-history task commands | ~150 lines |
| WP04 | Wire events into finalize-tasks (batch WPCreated + FeatureCreated) | ~100 lines |
| WP05 | Wire events into orchestrate (WPAssigned + lifecycle events) | ~100 lines |
| WP06 | Background sync service (auto-flush queue during active session) | ~150 lines |
| WP07 | Tests for event emission + integration test against running SaaS | ~300 lines |

### Dependency Graph

```
WP01 (Event Factory)
  │
  ├── WP02 (implement/merge/accept)
  ├── WP03 (task commands)
  ├── WP04 (finalize-tasks)
  └── WP05 (orchestrate)
        │
        └── WP06 (Background Sync)
              │
              └── WP07 (Tests)
```

**Parallelization**: WP02-WP05 can run in parallel after WP01 completes.

### Design Rationale

**Why a centralized event factory?**
- Single source of truth for event creation logic
- Consistent Lamport clock management across all commands
- Easier testing - mock the factory, not every command
- Clean separation between domain logic (commands) and sync logic (events)

**Why non-blocking event emission?**
- Core CLI functionality must work offline
- Users should never be blocked by sync issues
- Better UX - sync happens in background, commands feel snappy

**Why queue-first approach?**
- Offline-first architecture per Feature 008 research
- Events are durable even if WebSocket drops mid-send
- Batch sync is more efficient than individual sends

---

**END OF SPECIFICATION**
