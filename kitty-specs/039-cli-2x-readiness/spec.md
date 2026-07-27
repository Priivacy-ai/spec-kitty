# Feature Specification: CLI 2.x Readiness Sprint

**Feature Branch**: `039-cli-2x-readiness`
**Created**: 2026-02-12
**Status**: Draft
**Mission**: software-dev

## Problem Statement

The spec-kitty CLI targeting 2.x has four readiness gaps that prevent a production-quality release:

1. **Planning workflow blocker**: The `agent feature setup-plan` command previously failed with `NameError: get_feature_mission_key is not defined`. While the import has been fixed on current main (5332408f), the test environment now fails with `ModuleNotFoundError: typer`, and the full planning integration test (`test_full_planning_workflow_no_worktrees`) is marked xfail. The spec-to-plan flow is not reliably exercisable end-to-end.

2. **No authenticated sync infrastructure**: The CLI has a vendored `spec_kitty_events` library with event models, Lamport clocks, and status transitions, plus a thin adapter layer (`events/adapter.py`) and a storage stub (`events/store.py`). However, there is no batch ingest client, no offline queue, no replay mechanism, and no sync CLI commands for the authenticated SaaS path. Current observed behavior: `Synced: 0 Errors: 105` with no actionable detail surfaced.

3. **No global runtime resolution**: All template and mission resolution currently uses project-level `.kittify/` only (via `locate_project_root()` in `core/project_resolver.py` and `resolve_template_path()`). There is no `~/.kittify` (home directory) global runtime path. The convergence target is for templates and commands to resolve from `~/.kittify` with project-level overrides, and for `spec-kitty migrate` to produce a deterministic, warning-free state.

4. **7-lane vs 4-lane status mismatch**: The vendored `spec_kitty_events` library defines a 7-lane status model (`PLANNED`, `CLAIMED`, `IN_PROGRESS`, `FOR_REVIEW`, `DONE`, `BLOCKED`, `CANCELED` with `LANE_ALIASES` mapping `doing` to `IN_PROGRESS`). The CLI's canonical `LANES` constant in `task_helpers_shared.py` is a 4-tuple: `("planned", "doing", "for_review", "done")`. The sync payload must collapse 7 lanes to 4 for the current SaaS contract. This mapping is implicit and untested.

## Target State

After this sprint, the CLI provides:

- A fully passing `spec -> plan -> implement -> review` workflow exercised by integration tests and a new end-to-end smoke test.
- Authenticated batch event sync with actionable error diagnostics, an offline queue with replay, and a sync health dashboard.
- Deterministic global runtime resolution from `~/.kittify` with project-level overrides and a clean migration path.
- An explicit, tested lane collapse mapping from 7-lane canonical status to 4-lane sync fanout.
- A handoff contract document for `spec-kitty-saas` with exact event payloads, expected responses, and fixture data.

## User Scenarios & Testing

### User Story 1 - Fix Planning Workflow (Priority: P0)

A developer runs the full planning workflow (`create-feature` -> `setup-plan` -> task generation) from their project root. The workflow completes without import errors, missing dependency failures, or test environment issues.

**Why this priority**: This is a launch blocker. Without a working planning workflow, no features can progress from specification to implementation.

**Independent Test**: Can be fully tested by running `spec-kitty agent feature create-feature "test" && spec-kitty agent feature setup-plan` in a fresh project and verifying plan.md is created and committed.

**Acceptance Scenarios**:

1. **Given** a spec-kitty project with a feature that has spec.md, **When** the user runs `spec-kitty agent feature setup-plan`, **Then** plan.md is created in the feature directory and committed to the target branch without errors.
2. **Given** a test environment with all spec-kitty dependencies installed, **When** the planning workflow integration tests run, **Then** `test_planning_workflow.py`, `test_task_workflow.py`, and `test_workspace_per_wp_workflow.py` all pass (excluding pre-existing xfail markers unrelated to this feature).
3. **Given** a fresh project, **When** the user runs the full sequence `create-feature -> setup-plan -> finalize-tasks`, **Then** all artifacts (spec.md, plan.md, tasks.md, task prompt files) are created and committed.

---

### User Story 2 - Authenticated Sync with Diagnostics (Priority: P0)

A developer working on a SaaS-connected project runs `spec-kitty sync now` after making status transitions. Events are sent to the batch ingest endpoint. On failure, the CLI surfaces grouped error reasons with actionable next steps instead of a bare error count.

**Why this priority**: Launch-blocking for 2.x if the target includes SaaS/dev sync. Currently 105 events fail silently.

**Independent Test**: Can be tested by queuing synthetic events locally, running sync against a mock server, and verifying error grouping output.

**Acceptance Scenarios**:

1. **Given** queued events and valid credentials, **When** the user runs `spec-kitty sync now`, **Then** events are sent as a gzip-compressed batch to `POST /api/v1/events/batch/` with JWT authorization headers.
2. **Given** a batch response with per-event results (mix of success, duplicate, rejected), **When** the CLI processes the response, **Then** successes and duplicates are removed from the queue, rejections are retained with incremented retry count, and a summary is printed: `Synced: N, Duplicates: N, Failed: N (reason: schema_mismatch: X, auth_expired: Y)`.
3. **Given** a batch response with a blanket 400 error including a `details` field, **When** the CLI processes the response, **Then** both the `error` and `details` fields are surfaced to the user (not just the error field).
4. **Given** the CLI is offline or the server is unreachable, **When** the user runs `spec-kitty sync now`, **Then** events remain queued and a clear message indicates offline state with retry guidance.

---

### User Story 3 - Sync Queue Health and Diagnostics (Priority: P1)

A developer wants to understand the state of their local event queue. They run `spec-kitty sync status` or `spec-kitty sync diagnose` to inspect queue depth, event ages, retry distributions, and validate payloads against the schema before sending.

**Why this priority**: Enables self-service debugging of sync failures without requiring SaaS-side log access.

**Independent Test**: Can be tested by populating a queue with known events (some valid, some invalid) and verifying diagnostic output.

**Acceptance Scenarios**:

1. **Given** a queue with 50 events of varying ages and retry counts, **When** the user runs `spec-kitty sync status`, **Then** the output shows: queue depth (50), oldest event age, retry-count distribution, top failing event types/reasons, and connection/auth health.
2. **Given** a queue with events that have schema mismatches, **When** the user runs `spec-kitty sync diagnose`, **Then** each event is validated locally against the event schema and mismatches are reported with the specific field and expected value.
3. **Given** a large failure set (50+ events), **When** the user runs `spec-kitty sync now --report sync-errors.json`, **Then** a JSON file is written with per-event failure details for offline analysis.

---

### User Story 4 - Global Runtime Resolution (Priority: P1)

A developer has multiple spec-kitty projects. They run `spec-kitty migrate` once to converge their global runtime to `~/.kittify`. After migration, templates and mission assets resolve from the global path with project-level overrides, and no legacy fallback warnings appear.

**Why this priority**: Consistency/drift risk. Not a hard blocker but creates confusing mixed-origin behavior for users with multiple projects.

**Independent Test**: Can be tested by running `spec-kitty migrate` and verifying that `resolve_template_path()` finds templates in `~/.kittify` and that no warning messages are emitted during normal operations.

**Acceptance Scenarios**:

1. **Given** a user with a 1.x-style project (templates in project `.kittify/`), **When** they run `spec-kitty migrate`, **Then** global templates are installed to `~/.kittify/templates/` and `~/.kittify/missions/`, and the project's `.kittify/` retains only project-specific overrides.
2. **Given** a migrated environment, **When** `resolve_template_path()` is called for a standard template, **Then** it resolves in this order: project `.kittify/missions/{key}/templates/` -> project `.kittify/templates/` -> `~/.kittify/missions/{key}/templates/` -> `~/.kittify/templates/` -> package defaults. No fallback warnings are emitted.
3. **Given** a project that has NOT been migrated, **When** a template resolution falls through to legacy paths, **Then** a clear error is raised (not a silent fallback) directing the user to run `spec-kitty migrate`.

---

### User Story 5 - 7-Lane to 4-Lane Sync Fanout (Priority: P2)

The CLI emits events using the full 7-lane status model from `spec_kitty_events`. When these events are synced to the SaaS endpoint, the payload collapses lanes to the 4-lane model the SaaS contract expects.

**Why this priority**: Not blocking unless SaaS requires 7-lane fidelity now. The mapping is currently implicit and untested.

**Independent Test**: Can be tested by creating events for all 7 lanes, running them through the collapse function, and verifying the 4-lane output matches expected mapping.

**Acceptance Scenarios**:

1. **Given** a WP status event with `to_lane=CLAIMED`, **When** the event is prepared for sync, **Then** the payload's lane field is mapped to `doing` (the 4-lane equivalent).
2. **Given** the lane mapping: `PLANNED->planned`, `CLAIMED->doing`, `IN_PROGRESS->doing`, `FOR_REVIEW->for_review`, `DONE->done`, `BLOCKED->doing`, `CANCELED->done`, **When** the mapping function is called for each 7-lane value, **Then** it returns the correct 4-lane value.
3. **Given** a sync payload with collapsed lanes, **When** the SaaS endpoint processes it, **Then** the `StatusTransitionPayload` validates successfully against the 4-lane schema.

---

### User Story 6 - SaaS Handoff Contract Document (Priority: P0)

The spec-kitty-saas team receives a contract document that specifies the exact event envelope fields, the batch ingest request/response format, authentication headers, per-event status codes, and fixture data they can use for integration testing.

**Why this priority**: Required for coordinated CLI + SaaS debugging. Without it, the SaaS team cannot validate their endpoint against the CLI's actual payload format.

**Independent Test**: Can be validated by using the fixture data from the handoff doc to make a test request against the SaaS batch endpoint and comparing the response to the documented contract.

**Acceptance Scenarios**:

1. **Given** the handoff document, **When** the SaaS team reads it, **Then** they can construct a valid batch request using the documented envelope fields, headers, and compression format without consulting CLI source code.
2. **Given** the fixture data in the handoff doc, **When** it is posted to `POST /api/v1/events/batch/`, **Then** the response matches the documented per-event result format (`success|duplicate|rejected` with error details).
3. **Given** the lane mapping table in the handoff doc, **When** the SaaS team implements status processing, **Then** they handle all 4 sync lanes correctly and reject unknown lane values.

---

### Edge Cases

- What happens when the queue database (SQLite) is corrupted or locked by another process?
- How does the CLI handle token expiration mid-batch (access token expires between batch chunks)?
- What happens when `spec-kitty migrate` is run twice (idempotent behavior)?
- How does the system handle events emitted with 7-lane values that are later synced after a CLI downgrade to a version that only knows 4 lanes?
- What happens when `spec-kitty sync now` is interrupted mid-batch (partial success)?

## Requirements

### Functional Requirements

- **FR-001**: The `setup-plan` command MUST complete without import errors or missing dependency failures when all spec-kitty dependencies are installed.
- **FR-002**: The planning workflow integration tests (`test_planning_workflow.py`, `test_task_workflow.py`) MUST pass in the CI test environment.
- **FR-003**: The CLI MUST provide a `spec-kitty sync now` command that sends queued events to `POST /api/v1/events/batch/` with JWT `Authorization: Bearer <access_token>` headers and gzip-compressed JSON body `{"events": [...]}`.
- **FR-004**: The CLI MUST surface per-event error details from batch responses, grouping failures by reason category (schema mismatch, auth expired, server error) with counts and actionable next steps.
- **FR-005**: The CLI MUST maintain an offline event queue (SQLite database) that persists events when offline and replays them in FIFO order (timestamp ASC, id ASC) on reconnect.
- **FR-006**: The CLI MUST provide `spec-kitty sync status` showing: queue depth, oldest event age, retry-count distribution, top failing event types, and connection/auth health.
- **FR-007**: The CLI MUST provide `spec-kitty sync diagnose` that validates queued events locally against the event schema and reports mismatches per-event.
- **FR-008**: Queue replay MUST remove successfully synced and duplicate events, retain failures with incremented retry count, and print an actionable post-run summary.
- **FR-009**: Template resolution MUST support a global `~/.kittify` path in the resolution chain, between project-level paths and package defaults.
- **FR-010**: `spec-kitty migrate` MUST install global templates to `~/.kittify/` and leave project `.kittify/` with only project-specific overrides.
- **FR-011**: After migration, template resolution MUST NOT emit legacy fallback warnings during normal operation.
- **FR-012**: The CLI MUST provide an explicit, tested function that maps 7-lane canonical status values to 4-lane sync payload values.
- **FR-013**: The lane collapse mapping MUST be: PLANNED->planned, CLAIMED->doing, IN_PROGRESS->doing, FOR_REVIEW->for_review, DONE->done, BLOCKED->doing, CANCELED->done.
- **FR-014**: A handoff contract document MUST be produced specifying: event envelope fields, batch request/response format, authentication headers, per-event status codes, lane mapping table, and fixture data.
- **FR-015**: Token refresh MUST be attempted automatically when the access token is expired, using the stored refresh token. If refresh fails, the CLI MUST surface a clear "re-authenticate" message.
- **FR-016**: An end-to-end CLI smoke test MUST exercise the full `create-feature -> setup-plan -> implement -> review` sequence against a temporary repository.
- **FR-017**: Credentials MUST be stored in `~/.spec-kitty/credentials` (TOML format, chmod 600) with `tokens.access`, `tokens.refresh`, `expiries`, `user.username`, and `server.url`.
- **FR-018**: The `sync status --check` command MUST use the user's real auth token for connectivity probing, not a hardcoded test token.

### Key Entities

- **Event**: Immutable envelope with `event_id` (ULID), `event_type`, `aggregate_id`, `payload`, `timestamp`, `node_id`, `lamport_clock`, `causation_id`, `project_uuid`, `project_slug`, `correlation_id`, `schema_version`, `data_tier`.
- **QueueEntry**: Persisted event in SQLite with `id`, `data` (JSON text), `retry_count`, `created_at`, `last_attempt_at`, `status` (pending/failed/synced).
- **LaneMapping**: A function from 7-lane `Lane` enum values to 4-lane sync string values.
- **Credentials**: TOML file at `~/.spec-kitty/credentials` with JWT tokens, expiries, user info, and server URL.
- **GlobalRuntime**: Directory at `~/.kittify/` containing `templates/`, `missions/`, and shared configuration.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The full planning workflow (`create-feature -> setup-plan -> finalize-tasks`) completes in under 30 seconds on a standard development machine.
- **SC-002**: All planning and task workflow integration tests pass with zero failures (excluding pre-existing xfail markers unrelated to this feature).
- **SC-003**: `spec-kitty sync now` successfully syncs events when the server is reachable and credentials are valid, with per-event error details surfaced for any failures.
- **SC-004**: Users can diagnose and resolve sync failures without requiring access to server logs, using only CLI-side diagnostics.
- **SC-005**: After `spec-kitty migrate`, zero legacy fallback warnings appear during normal template resolution operations.
- **SC-006**: The lane collapse mapping is validated by automated tests covering all 7 input lanes with correct 4-lane outputs.
- **SC-007**: The SaaS handoff contract document enables the SaaS team to validate their batch endpoint against CLI payloads using the provided fixture data, without consulting CLI source code.
- **SC-008**: The end-to-end smoke test passes in both local and CI environments.

## Non-Goals

- **SaaS-side implementation changes**: This spec covers CLI-owned scope only. Required SaaS changes are documented in the handoff artifact but not implemented here.
- **Fixing all ~50 pre-existing cross-test pollution failures**: Only tests directly related to the four gaps must pass. No regressions against current baseline.
- **Requiring 7-lane fidelity in SaaS UI immediately**: The 4-lane collapse is the contract for now.
- **API key authentication**: The current JWT access+refresh token mechanism is retained. API keys may come later.
- **WebSocket real-time sync**: Only batch HTTP sync is in scope. The `wss://` path is deferred.

## Assumptions

- The `spec_kitty_events` library (vendored at `src/specify_cli/spec_kitty_events/`) is the authoritative source for event models and the 7-lane status enum.
- The SaaS batch endpoint at `POST /api/v1/events/batch/` accepts the documented payload format and returns per-event results.
- SQLite is acceptable as the local queue storage engine.
- The `~/.spec-kitty/credentials` TOML format is the established credential storage mechanism.
- The `spec-kitty migrate` command exists as a CLI entry point and can be extended for global runtime setup.

## Compatibility Requirements

- **1.x -> 2.x migration**: Projects with existing `.kittify/` project configs and `kitty-specs/` artifacts MUST be migratable via `spec-kitty migrate`. No clean break.
- **Pre-migration behavior**: Projects that have not run `spec-kitty migrate` MUST continue to function with project-level resolution only, with a clear message directing them to migrate.
- **Backward-compatible lane handling**: The 4-lane CLI constant `LANES = ("planned", "doing", "for_review", "done")` MUST remain the canonical CLI-side representation. The 7-lane model is internal to events.

## Required SaaS Changes/Dependencies

These items are out of scope for CLI implementation but are documented for the `spec-kitty-saas` team:

1. **Batch endpoint error detail**: The SaaS `POST /api/v1/events/batch/` endpoint SHOULD return the `details` field in 400 responses with per-event failure reasons, not just a blanket "Batch processing failed" message.
2. **Team/project authorization**: The ingest path must validate that the authenticated user has permission to submit events for the specified `team_slug` and `project_uuid`.
3. **Lane validation**: The SaaS endpoint should accept only the 4-lane sync values (`planned`, `doing`, `for_review`, `done`) and reject unknown lane strings with a descriptive error.
4. **Duplicate handling**: The SaaS endpoint should return `duplicate` status for events with previously-seen `event_id` values (idempotent ingest).
