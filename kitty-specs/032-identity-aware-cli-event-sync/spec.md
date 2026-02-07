# Feature Specification: Identity-Aware CLI Event Sync

**Feature Branch**: `032-identity-aware-cli-event-sync`
**Created**: 2026-02-07
**Status**: Draft
**Target Branch**: 2.x
**Input**: Make CLI events identity-aware and auto-syncing so multiple local projects appear in SaaS dashboards

## Overview

The spec-kitty CLI 2.x already emits events (WPStatusChanged, FeatureCreated, etc.) via the sync infrastructure. However, events currently lack project identity, preventing the SaaS from correctly attributing events to specific projects. This feature adds project identity (`project_uuid`, `project_slug`) to all emitted events and enables automatic background sync on CLI startup.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Project Identity Persistence (Priority: P1)

A developer initializes spec-kitty in a new repository. The CLI automatically generates a unique project identity that persists across sessions. When events are emitted, they include this identity so the SaaS can correctly associate work packages with the project.

**Why this priority**: Without project identity, events cannot be attributed to specific projects - the entire sync feature is broken.

**Independent Test**: Run `spec-kitty init` in a fresh repo, verify config.yaml contains `project_uuid` and `project_slug`, then run any event-emitting command and verify the event envelope includes the identity.

**Acceptance Scenarios**:

1. **Given** a new repository without spec-kitty initialized, **When** user runs `spec-kitty init`, **Then** config.yaml is created with `project_uuid` (valid UUID4), `project_slug` (derived from repo directory name), and `node_id` (stable machine identifier derived from the LamportClock generator).

2. **Given** a repository with existing config.yaml missing `project_uuid`, **When** user runs any spec-kitty command, **Then** the CLI auto-generates and persists `project_uuid` before proceeding.

3. **Given** a repository with complete project identity, **When** user runs `spec-kitty implement WP01`, **Then** the emitted WPStatusChanged event includes `project_uuid` in the envelope.

---

### User Story 2 - Auto-Start Background Sync (Priority: P1)

When a developer runs any spec-kitty command, the background sync runtime starts automatically. If authenticated, events are sent via WebSocket in real-time. If not authenticated, events are queued locally for later batch sync.

**Why this priority**: Manual sync startup is a friction point that leads to missed events and sync gaps.

**Independent Test**: Run `spec-kitty implement WP01` without explicitly starting sync, verify the BackgroundSyncService is running and events are either sent (if authenticated) or queued (if not).

**Acceptance Scenarios**:

1. **Given** user is authenticated (`spec-kitty auth login` completed), **When** user runs `spec-kitty implement WP01`, **Then** BackgroundSyncService starts automatically, WebSocketClient connects, and the event is sent in real-time.

2. **Given** user is NOT authenticated, **When** user runs `spec-kitty implement WP01`, **Then** BackgroundSyncService starts, WebSocket connection is skipped, event is queued locally, and a warning is logged ("Events queued locally; run `spec-kitty auth login` to enable real-time sync").

3. **Given** user has `sync.auto_start: false` in `.kittify/config.yaml`, **When** user runs any command, **Then** background sync is NOT started (explicit opt-out honored).

---

### User Story 3 - Event Identity Injection (Priority: P1)

All events emitted by CLI commands include `project_uuid` and optionally `project_slug` in the event envelope. Events without project identity are rejected at validation time and queued only (not sent via WebSocket).

**Why this priority**: Identity-aware events are the core deliverable - without this, SaaS cannot materialize projects.

**Independent Test**: Emit an event via `emitter.emit_wp_status_changed()`, verify the returned event dict contains `project_uuid`.

**Acceptance Scenarios**:

1. **Given** project identity exists in config.yaml, **When** any `emit_*` method is called, **Then** the event envelope includes `project_uuid` (required) and `project_slug` (optional).

2. **Given** config.yaml is missing `project_uuid`, **When** any `emit_*` method is called, **Then** a warning is logged ("Event missing project_uuid; queued locally only"), event is queued but NOT sent via WebSocket.

3. **Given** project identity exists, **When** WebSocket is connected and event is emitted, **Then** the event is sent immediately with `project_uuid` in the payload.

---

### User Story 4 - Team Slug Resolution (Priority: P2)

The EventEmitter resolves `team_slug` from the authenticated user's context. This enables the SaaS to associate events with the correct team. If not authenticated, `team_slug` defaults to "local".

**Why this priority**: Team context is important for multi-team SaaS but not blocking for single-user scenarios.

**Independent Test**: Authenticate, then emit an event, verify `team_slug` matches the logged-in team.

**Acceptance Scenarios**:

1. **Given** user is authenticated with a team, **When** event is emitted, **Then** `team_slug` is included in the event envelope.

2. **Given** user is NOT authenticated, **When** event is emitted, **Then** `team_slug` defaults to "local".

3. **Given** user runs `spec-kitty auth login`, **When** login completes successfully, **Then** `team_slug` is stored in credentials for future use.

---

### User Story 5 - Fix Duplicate Event Emissions (Priority: P2)

The `implement` and `accept` commands currently emit WPStatusChanged events in multiple code paths, causing duplicates. This is fixed by consolidating to a single emission point per command.

**Why this priority**: Duplicate events cause incorrect state in SaaS dashboards and inflate event counts.

**Independent Test**: Run `spec-kitty implement WP01`, verify exactly ONE WPStatusChanged event is emitted (not two).

**Acceptance Scenarios**:

1. **Given** a WP in "planned" lane, **When** user runs `spec-kitty implement WP01`, **Then** exactly ONE WPStatusChanged(planned->doing) event is emitted.

2. **Given** a WP in "for_review" lane, **When** user runs `spec-kitty accept`, **Then** exactly ONE WPStatusChanged(for_review->done) event is emitted per WP.

---

### Edge Cases

- **Missing git remote**: If no git remote is configured, `project_slug` defaults to the directory name.
- **Corrupted config.yaml**: If config.yaml is malformed, CLI should warn and regenerate identity fields.
- **Network timeout during sync**: Events should be queued locally; BackgroundSyncService should retry with exponential backoff.
- **Multiple spec-kitty processes**: Each process uses the same `node_id` (machine-level, derived from hostname+username) but different Lamport clock values for ordering.
- **Config.yaml race condition**: If two processes try to generate `project_uuid` simultaneously, the first write wins; subsequent reads use the persisted value.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a UUID4 `project_uuid` during `spec-kitty init` if not already present in config.yaml.
- **FR-002**: System MUST derive `project_slug` from the repository directory name (kebab-case) or git remote origin if available.
- **FR-003**: System MUST persist `node_id` (stable machine identifier from `sync.clock.generate_node_id()`) in config.yaml for event attribution.
- **FR-004**: System MUST inject `project_uuid` into every event envelope via `emitter._emit()`.
- **FR-005**: System MUST validate that `project_uuid` is present before sending events via WebSocket; events without identity are queued only.
- **FR-006**: System MUST log a warning when emitting events without project identity.
- **FR-007**: System MUST auto-start BackgroundSyncService on CLI command execution (unless `sync.auto_start: false` in `.kittify/config.yaml`).
- **FR-008**: System MUST connect WebSocketClient automatically if user is authenticated.
- **FR-009**: System MUST gracefully degrade to queue-only mode when not authenticated.
- **FR-010**: AuthClient MUST expose `get_team_slug()` returning the stored team slug or None.
- **FR-011**: System MUST store `team_slug` in credentials upon successful `spec-kitty auth login`.
- **FR-012**: System MUST emit exactly ONE WPStatusChanged event per status transition in `implement` command.
- **FR-013**: System MUST emit exactly ONE WPStatusChanged event per WP in `accept` command.

### Key Entities

- **ProjectIdentity**: Represents the unique identity of a spec-kitty project (`project_uuid`, `project_slug`, `node_id`). Persisted in `.kittify/config.yaml`.
- **EventEnvelope**: The wrapper around event payload that includes identity metadata (`project_uuid`, `project_slug`, `team_slug`, `node_id`, `lamport_clock`).
- **SyncRuntime**: Lightweight bootstrap that starts BackgroundSyncService and attaches WebSocketClient to the EventEmitter when authenticated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `spec-kitty init` creates config.yaml with valid `project_uuid` (UUID4 format) and `project_slug` in 100% of cases.
- **SC-002**: All events emitted after authentication include `project_uuid` in the envelope.
- **SC-003**: CLI commands complete successfully whether authenticated or not (graceful degradation).
- **SC-004**: Zero duplicate WPStatusChanged events emitted by `implement` or `accept` commands.
- **SC-005**: Background sync starts within 100ms of CLI command execution (no user-perceptible delay).
- **SC-006**: Events missing project identity are queued locally and a warning is visible to the user.

## Assumptions

- The sync infrastructure (WebSocketClient, EventEmitter, OfflineQueue, LamportClock) exists on the 2.x branch and is functional.
- The `spec_kitty_events` library will be updated separately to accept `project_uuid` and `project_slug` fields.
- The SaaS will be updated separately to materialize Projects/Features/WPs from identity-aware events.

## Out of Scope

- SaaS-side changes (covered by spec-kitty-saas team prompt)
- Event library changes (covered by spec-kitty-events team prompt)
- Retry logic for failed WebSocket sends (existing BackgroundSyncService handles this)
- UI/dashboard updates
