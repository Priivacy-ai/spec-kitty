# Feature Specification: CLI Event Log Integration

**Feature Branch**: `025-cli-event-log-integration`
**Created**: 2026-01-27
**Status**: Draft
**Input**: Integrate the completed spec-kitty-events library into the CLI to replace primitive YAML activity logs with structured event log using Lamport clocks and CRDT merge rules.

## Overview

Spec-kitty currently uses primitive YAML activity logs for tracking workflow state. This feature integrates the completed spec-kitty-events library (Feature 003) to provide:
- Causal ordering via Lamport clocks (eliminates wall-clock dependency)
- Conflict detection for concurrent CLI operations
- Deterministic merge rules (CRDT for tags/counters, state-machine for workflows)
- Foundation for CLI ↔ Django sync protocol (Dependency 0 for SaaS platform)

**Target Branch**: 2.x development (greenfield implementation, no 1.x backward compatibility)

**Branch Strategy (CRITICAL - READ FIRST)**:

⚠️ **This feature requires creating a NEW `2.x` branch. Do NOT implement on `main` branch.**

**Before any implementation**:
```bash
# Create 2.x branch from current main (v0.13.7)
git checkout main
git pull origin main
git checkout -b 2.x
git push origin 2.x
```

**Branch responsibilities**:
- **main branch** (v0.13.x): Will become 1.x maintenance branch (YAML activity logs, stable CLI)
  - ❌ **DO NOT modify for this feature**
  - ✅ Maintenance-only: security fixes, critical bugs

- **2.x branch** (NEW): SaaS transformation with event sourcing (greenfield architecture)
  - ✅ **All Feature 025 implementation happens here**
  - ✅ Events-only (no YAML logs, no 1.x compatibility)
  - ✅ Breaking changes allowed (pre-release)

**Rationale**: Per ADR-12 (Two-Branch Strategy), main/1.x and 2.x are **incompatible parallel tracks**. Event sourcing architecture cannot coexist with YAML activity logs.

**Dependency Management**: Git dependency with commit pinning per ADR-11 (Dual-Repository Pattern). SSH deploy key for CI/CD autonomy.

**Out of Scope for This Feature**:
- Vendoring script for PyPI releases (deferred to "2.x Release Preparation" feature)
- Migration from 1.x YAML logs (deferred until 2.x nears completion)
- Creating 1.x branch from main (will happen when first v1.0.0 release is cut)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Event Emission on Workflow State Changes (Priority: P1)

A developer runs `spec-kitty agent tasks move-task WP01 --to doing` to start work on a work package. The CLI emits a `WPStatusChanged` event to `.kittify/events/2026-01-27.jsonl` with Lamport clock metadata, enabling causal ordering without wall-clock timestamps.

**Why this priority**: Core event sourcing capability - without events being emitted, no other features work.

**Independent Test**: Run status change command, verify JSONL file contains event with correct structure (event_id, lamport_clock, entity_id, event_type, payload).

**Acceptance Scenarios**:

1. **Given** feature WP is in "planned" lane, **When** developer moves it to "doing", **Then** `.kittify/events/YYYY-MM-DD.jsonl` contains `WPStatusChanged` event with `old_status: planned, new_status: doing`
2. **Given** no events directory exists, **When** first event is emitted, **Then** system creates `.kittify/events/` directory automatically
3. **Given** multiple status changes in single day, **When** events are emitted, **Then** all events append to same daily file with monotonically increasing Lamport clocks
4. **Given** Lamport clock file doesn't exist, **When** first event is emitted, **Then** system initializes `.kittify/clock.json` with clock value 1

---

### User Story 2 - Reading Workflow State from Event Log (Priority: P1)

A developer runs `spec-kitty status` to see current feature state. The CLI reads from the event log, applies CRDT merge rules to reconstruct current state, and displays the kanban board with correct WP positions.

**Why this priority**: Must be able to read events to make system functional - paired with P1 write capability.

**Independent Test**: Emit several events manually, run status command, verify board reflects event sequence correctly.

**Acceptance Scenarios**:

1. **Given** event log contains `WPStatusChanged` events, **When** developer runs `spec-kitty status`, **Then** kanban board shows WPs in correct lanes based on event history
2. **Given** events were written out of Lamport clock order (concurrent operations), **When** status is read, **Then** system sorts by Lamport clock before applying state transitions
3. **Given** no event log exists (fresh project), **When** developer runs `spec-kitty status`, **Then** system displays empty board (graceful degradation)
4. **Given** event log contains invalid JSON line, **When** status is read, **Then** system skips invalid line with warning and continues processing valid events

---

### User Story 3 - SQLite Query Index for Fast Aggregates (Priority: P1)

A developer runs `spec-kitty status --feature 012-documentation-mission` on a project with 1000+ events. The CLI uses a SQLite index to quickly filter events by feature without reading all JSONL files.

**Why this priority**: Performance is critical for usability - reading all events linearly would be too slow for mature projects.

**Independent Test**: Generate 1000 events across 10 features, verify status command with feature filter completes in <500ms.

**Acceptance Scenarios**:

1. **Given** event log has 1000+ events, **When** JSONL file is written, **Then** system updates `.kittify/events/index.db` SQLite index in background
2. **Given** developer queries for specific feature, **When** using index, **Then** system reads only events for that feature (not full event log)
3. **Given** index database is missing, **When** CLI reads events, **Then** system rebuilds index from JSONL files automatically
4. **Given** index database is corrupted, **When** CLI detects corruption, **Then** system deletes index and rebuilds from JSONL source of truth

---

### User Story 4 - Conflict Detection for Concurrent Operations (Priority: P2)

Two developers (or agents) concurrently move the same WP to different states. Both operations emit events with overlapping Lamport clocks. The CLI detects the conflict using `is_concurrent()` and applies deterministic merge rules from spec-kitty-events library.

**Why this priority**: Enables safe parallel agent operations without coordination - key for multi-agent workflows.

**Independent Test**: Simulate concurrent events manually, verify CLI detects conflict and applies merge rules correctly.

**Acceptance Scenarios**:

1. **Given** Agent A emits `WPStatusChanged(WP01, doing)` at clock=5, **When** Agent B emits `WPStatusChanged(WP01, for_review)` at clock=5 (concurrent), **Then** system detects conflict with `is_concurrent()`
2. **Given** concurrent state transition conflict detected, **When** applying merge rules, **Then** state-machine merge rule applies (later event_id wins per deterministic ordering)
3. **Given** concurrent tag additions to same WP, **When** applying merge rules, **Then** CRDT set merge rule applies (both tags are kept)
4. **Given** conflict is resolved via merge rules, **When** user runs `spec-kitty status`, **Then** output includes conflict warning with explanation of which rule applied

---

### User Story 5 - Daily File Rotation with Outbox Pattern (Priority: P2)

Developer works on a feature across multiple days. The CLI creates separate JSONL files per day (`.kittify/events/2026-01-27.jsonl`, `.kittify/events/2026-01-28.jsonl`). Old events remain immutable, new events append to current day's file.

**Why this priority**: File rotation keeps individual files manageable size, enables efficient Git merging (append-only daily files).

**Independent Test**: Emit events across simulated day boundary, verify correct file rotation.

**Acceptance Scenarios**:

1. **Given** current date is 2026-01-27, **When** event is emitted, **Then** event appends to `.kittify/events/2026-01-27.jsonl`
2. **Given** date changes to 2026-01-28, **When** next event is emitted, **Then** new file `.kittify/events/2026-01-28.jsonl` is created
3. **Given** Git merge conflict on event file, **When** both branches appended events to same daily file, **Then** Git merge succeeds (append-only files merge cleanly)
4. **Given** outbox pattern for replay, **When** system restarts mid-day, **Then** current day's events can be replayed from JSONL (no events lost)

---

### User Story 6 - Git Dependency Integration with Commit Pinning (Priority: P1)

Developer checks out the 2.x branch and runs `pip install -e .`. The CLI installs spec-kitty-events library from Git repository using commit hash pinning specified in `pyproject.toml`.

**Why this priority**: Foundational infrastructure - without library integration, no event log functionality works.

**Independent Test**: Fresh clone of spec-kitty, pip install, verify spec-kitty-events imports successfully.

**Acceptance Scenarios**:

1. **Given** `pyproject.toml` specifies `spec-kitty-events = { git = "https://github.com/Priivacy-ai/spec-kitty-events.git", rev = "abc1234" }`, **When** developer runs `pip install -e .`, **Then** exact commit `abc1234` is installed (deterministic build)
2. **Given** SSH deploy key is configured in CI, **When** GitHub Actions runs build, **Then** CI successfully clones private spec-kitty-events repo and installs dependency
3. **Given** library is updated in spec-kitty-events repo, **When** spec-kitty updates commit hash in pyproject.toml, **Then** next pip install uses new library version
4. **Given** SSH key is not configured, **When** pip tries to install, **Then** system provides clear error with setup instructions for deploy key

---

### User Story 7 - Error Logging with Manus Pattern (Priority: P3)

An agent attempts to transition WP from "planned" to "done" (invalid state transition). The CLI emits an error event to `.kittify/errors/YYYY-MM-DD.jsonl` with context about the violation, enabling future agents to learn from the mistake.

**Why this priority**: Nice-to-have learning capability - system works without it, but improves over time with error tracking.

**Independent Test**: Trigger invalid state transition, verify error log contains event with clear explanation.

**Acceptance Scenarios**:

1. **Given** agent attempts invalid state transition, **When** validation fails, **Then** error event is logged to `.kittify/errors/YYYY-MM-DD.jsonl`
2. **Given** error event is logged, **When** reviewing error log, **Then** event includes: error_type, entity_id, attempted_operation, reason, timestamp
3. **Given** multiple errors in single day, **When** errors occur, **Then** all errors append to same daily file (parallel structure to event log)
4. **Given** agent reviews error log before operating, **When** similar invalid transition is attempted, **Then** agent can learn to avoid repeating past mistakes (Manus pattern)

---

### Edge Cases

- **What happens when Lamport clock file is corrupted?** System reinitializes clock from max clock value found in event log + 1
- **What happens when event log and SQLite index diverge?** JSONL files are source of truth - system rebuilds index from JSONL on next read
- **How does system handle concurrent writes to same daily JSONL file from multiple processes?** File locking ensures atomic appends (POSIX advisory locks)
- **What happens if Git merge creates duplicate events (same event_id)?** System deduplicates by event_id when reading log (idempotent processing)
- **How are events handled during clock drift scenarios?** Lamport clocks are logical (no wall-clock dependency) - drift doesn't affect ordering
- **What happens when spec-kitty-events library is updated mid-development?** Update commit hash in pyproject.toml, reinstall - no data migration needed (events are versioned)

## Requirements *(mandatory)*

### Functional Requirements

#### Git Dependency Integration
- **FR-001**: System MUST declare spec-kitty-events as Git dependency in pyproject.toml with commit hash pinning
- **FR-002**: System MUST use SSH Git URL for private repository access
- **FR-003**: System MUST document deploy key setup instructions for CI/CD in development docs
- **FR-004**: System MUST fail gracefully with clear error message if spec-kitty-events cannot be installed

#### Event Storage
- **FR-005**: System MUST emit events to `.kittify/events/YYYY-MM-DD.jsonl` in append-only mode
- **FR-006**: System MUST create daily JSONL files with ISO date format (YYYY-MM-DD)
- **FR-007**: System MUST persist Lamport clock state in `.kittify/clock.json` after each event emission
- **FR-008**: System MUST ensure atomic appends to JSONL files using POSIX file locking

#### Event Types
- **FR-009**: System MUST emit `WPStatusChanged` events when work package moves between lanes
- **FR-010**: System MUST emit `SpecCreated` events when new feature specification is created
- **FR-011**: System MUST emit `WPCreated` events when work packages are generated
- **FR-012**: System MUST emit `WorkspaceCreated` events when workspace is initialized for WP

#### Event Reading
- **FR-013**: System MUST read events from JSONL files sorted by Lamport clock (causal ordering)
- **FR-014**: System MUST apply CRDT merge rules for concurrent tag/counter events
- **FR-015**: System MUST apply state-machine merge rules for concurrent workflow transitions
- **FR-016**: System MUST skip invalid JSON lines with warning (graceful degradation)

#### SQLite Query Index
- **FR-017**: System MUST maintain SQLite index at `.kittify/events/index.db` with columns: event_id, lamport_clock, entity_id, event_type, date
- **FR-018**: System MUST update index automatically when new events are appended to JSONL
- **FR-019**: System MUST rebuild index from JSONL files if index is missing or corrupted
- **FR-020**: System MUST use index for filtering queries (by feature, by WP, by date range)

#### Conflict Detection
- **FR-021**: System MUST detect concurrent events using `is_concurrent()` from spec-kitty-events library
- **FR-022**: System MUST resolve conflicts using deterministic merge rules (no user prompts)
- **FR-023**: System MUST log conflict resolutions to stderr with explanation of merge rule applied
- **FR-024**: System MUST surface conflict warnings in `spec-kitty status` output

#### Error Logging
- **FR-025**: System MUST log validation errors to `.kittify/errors/YYYY-MM-DD.jsonl`
- **FR-026**: System MUST include error context: error_type, entity_id, attempted_operation, reason
- **FR-027**: System MUST not block operations when error logging fails (best-effort)

#### Migration (Deferred)
- **FR-028**: System MUST NOT implement 1.x → 2.x migration in this feature (deferred to future feature when 2.x nears completion)

### Key Entities

- **Event**: Immutable record of state change with metadata (event_id ULID, lamport_clock, entity_id, event_type, payload, timestamp)
- **LamportClock**: Logical clock providing causal ordering without wall-clock dependency (monotonically increasing counter)
- **EventStore**: Storage adapter for persisting events to JSONL files (append-only, daily rotation)
- **ClockStorage**: Storage adapter for persisting Lamport clock state to JSON file
- **ErrorStorage**: Storage adapter for persisting error events to separate JSONL files
- **EventIndex**: SQLite database for fast event queries (filtered by entity, date range, type)
- **ConflictDetector**: Component using `is_concurrent()` to identify conflicting events
- **MergeRuleEngine**: Component applying CRDT or state-machine rules to resolve conflicts deterministically

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers' workflow state changes are automatically tracked with 100% coverage (no state changes are lost or bypassed)
- **SC-002**: Developers can view complete project history with events ordered correctly by causality (not wall-clock time)
- **SC-003**: Developers see accurate current state when running status command (100% accuracy in reconstructing state from history)
- **SC-004**: Developers working concurrently can merge their work without manual intervention (automatic conflict-free merging)
- **SC-005**: All existing CLI functionality continues to work without regressions (zero breaking changes for users)
- **SC-006**: Developers can query project history instantly (queries complete in <500ms even for projects with 1000+ events)
- **SC-007**: Concurrent operations from multiple developers are detected and resolved automatically 100% of the time (no data loss from conflicts)
- **SC-008**: CI/CD pipeline builds succeed without manual intervention (automated deployment infrastructure works reliably)

## Assumptions

- SSH deploy key can be configured in GitHub Actions secrets for CI/CD access to private spec-kitty-events repo
- Daily JSONL file rotation is sufficient for Git merge performance (files don't grow so large that Git struggles)
- POSIX file locking is available on all target platforms (Linux, macOS, Windows with WSL)
- Lamport clocks are sufficient for causal ordering (no need for vector clocks or hybrid logical clocks in CLI context)
- SQLite is acceptable dependency for query index (already used elsewhere in spec-kitty)
- Developers have basic understanding of event sourcing concepts (not required to understand Lamport clocks deeply)
- 2.x branch will not be released until SaaS features are substantially complete (no pressure for 1.x migration yet)
