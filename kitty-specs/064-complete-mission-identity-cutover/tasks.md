# Tasks: Complete Mission Identity Cutover

**Feature**: 064-complete-mission-identity-cutover
**Date**: 2026-04-06
**Total Subtasks**: 50
**Work Packages**: 9

## Dependency Graph

```
WP01 (gate) ────────────────────────┐
WP02 (core renames) ──► WP03 ──┐   │
                                ├──►WP04 (orchestrator) ──┐
                                │                          │
WP01 ──────────────────────────►WP05 (body sync) ─────────┤
WP01 + WP02 ──────────────────►WP06 (tracker+envelope) ──┤
                                                           ├──► WP07 (tests) ──► WP08 (audit) ──► WP09 (release)
```

**Parallel opportunities:**
- WP01, WP02 can run in parallel (no deps)
- WP05, WP06 can start after WP01 (before WP03/WP04 finish)
- WP04, WP05, WP06 can run in parallel once their deps are met

---

## Phase A: Foundation

### WP01 – Compatibility Gate Core
**File**: `tasks/WP01-compatibility-gate.md`
**Priority**: High | **Dependencies**: None | **Subtasks**: 5

Build the central compatibility gate that validates outbound payloads against the vendored upstream 3.0.0 contract artifact. Does NOT insert at chokepoints — downstream WPs insert the gate at their respective surfaces.

- [ ] T001: Vendor `upstream-3.0.0-shape.json` into package as `src/specify_cli/core/upstream_contract.json`
- [ ] T002: Create `ContractViolationError` exception class
- [ ] T003: Create `validate_outbound_payload(payload, context)` that loads vendored artifact
- [ ] T004: Write unit tests for all forbidden/required field validation rules
- [ ] T005: Write unit tests for pass-through behavior on valid payloads

**Requirement refs**: FR-012, FR-013, FR-023

---

### WP02 – Rename Core Modules + Canonical meta.json Writes
**File**: `tasks/WP02-rename-core-modules.md`
**Priority**: High | **Dependencies**: None | **Subtasks**: 7

Rename `feature_creation.py` → `mission_creation.py` and `feature_metadata.py` → `mission_metadata.py`. Update all imports. Fix meta.json scaffolding to write canonical field names.

- [ ] T006: `git mv` feature_creation.py → mission_creation.py + update 2 prod imports
- [ ] T007: Update meta.json scaffolding in mission_creation.py to write `mission_slug`, `mission_number`, `mission_type`
- [ ] T008: Update 3 test files for mission_creation import
- [ ] T009: `git mv` feature_metadata.py → mission_metadata.py + update 10 prod imports
- [ ] T010: Update 3 test files for mission_metadata import
- [ ] T011: Update other meta.json write paths (upgrade/feature_meta.py) to use canonical fields
- [ ] T012: Write tests verifying new meta.json writes use canonical fields only

**Requirement refs**: FR-016, FR-019

---

## Phase B: Agent Layer + Alias Removal

### WP03 – Agent Module Rename + Alias Removal (Non-Orchestrator)
**File**: `tasks/WP03-agent-rename-alias-removal.md`
**Priority**: High | **Dependencies**: WP02 | **Subtasks**: 6

Rename `agent/feature.py` → `agent/mission.py`. Remove `identity_aliases.py` usage from 6 non-orchestrator files (19 call sites). Does NOT touch `orchestrator_api/commands.py` — that is WP04's scope.

- [ ] T013: `git mv` agent/feature.py → agent/mission.py + update tasks.py import
- [ ] T014: Update 35+ test imports for agent/mission.py
- [ ] T015: Remove `identity_aliases` import + calls from `status/models.py`, `status/progress.py`, `status/views.py`
- [ ] T016: Remove `identity_aliases` import + calls from `next/decision.py`, `cli/commands/materialize.py`
- [ ] T017: Remove `identity_aliases` import + 4 calls from `cli/commands/agent/status.py`
- [ ] T018: Verify outputs still contain `mission_slug` (not `feature_slug`)

**Requirement refs**: FR-003, FR-016

---

## Phase C: Contract Surface Cleanup

### WP04 – Orchestrator API Rename
**File**: `tasks/WP04-orchestrator-api-rename.md`
**Priority**: High | **Dependencies**: WP01, WP03 | **Subtasks**: 7

Rename 3 commands, 2 error codes, and `--feature` → `--mission` parameter. Remove remaining alias injection (8 calls). Insert compatibility gate. This is the externally-visible breaking change gated by FR-021.

- [ ] T019: Remove `identity_aliases` import + 8 `with_tracked_mission_slug_aliases()` calls from commands.py
- [ ] T020: Delete `src/specify_cli/core/identity_aliases.py` (zero consumers remain)
- [ ] T021: Rename 3 commands: `feature-state` → `mission-state`, `accept-feature` → `accept-mission`, `merge-feature` → `merge-mission`
- [ ] T022: Rename 2 error codes: `FEATURE_NOT_FOUND` → `MISSION_NOT_FOUND`, `FEATURE_NOT_READY` → `MISSION_NOT_READY`
- [ ] T023: Rename `--feature` → `--mission` parameter on all 8 commands
- [ ] T024: Update internal function names, parameter names, insert compatibility gate call
- [ ] T025: Update tests + add integration test verifying old command names fail as unknown

**Requirement refs**: FR-003, FR-004, FR-012, FR-022

---

### WP05 – Body Sync Migration
**File**: `tasks/WP05-body-sync-migration.md`
**Priority**: High | **Dependencies**: WP01 | **Subtasks**: 7

Rename `NamespaceRef` and `BodyUploadTask` fields. Migrate SQLite queue schema. Update transport payload. Insert compatibility gate at body sync chokepoints.

- [ ] T026: Rename `NamespaceRef` fields: `feature_slug` → `mission_slug`, `mission_key` → `mission_type`
- [ ] T027: Rename `BodyUploadTask` fields: `feature_slug` → `mission_slug`, `mission_key` → `mission_type`
- [ ] T028: Update `_build_request_body()` in body_transport.py to emit canonical payload
- [ ] T029: Insert compatibility gate at `enqueue()` and `push_content()` chokepoints
- [ ] T030: Create SQLite queue schema migration (`ALTER TABLE RENAME COLUMN`)
- [ ] T031: Register migration in upgrade chain
- [ ] T032: Test queue migration with populated queue — zero task loss (FR-020)

**Requirement refs**: FR-010, FR-011, FR-012, FR-020

---

### WP06 – Tracker Bind + Event Envelope Verification
**File**: `tasks/WP06-tracker-bind-event-envelope.md`
**Priority**: High | **Dependencies**: WP01, WP02 | **Subtasks**: 7

Add `build_id` to tracker bind. Insert gate at tracker, emitter, batch sync, and WebSocket chokepoints. Audit event paths for `build_id` preservation.

- [ ] T033: Add `build_id` to tracker bind `project_identity` dict in `tracker.py`
- [ ] T034: Insert gate at `SaaSTrackerClient._request()` chokepoint
- [ ] T035: Insert gate at `EventEmitter._emit()`, `batch_sync()`, `WebSocketClient.send_event()` chokepoints
- [ ] T036: Audit event emission paths for `build_id` presence and fix gaps
- [ ] T037: Audit event serialization/deserialization for `build_id` preservation through queue/replay
- [ ] T038: Verify `aggregate_type` is `"Mission"` everywhere (never `"Feature"`)
- [ ] T039: Update tracker integration tests

**Requirement refs**: FR-007, FR-008, FR-009, FR-012, FR-018

---

## Phase D: Validation

### WP07 – Shape Conformance Tests
**File**: `tasks/WP07-conformance-tests.md`
**Priority**: Medium | **Dependencies**: WP04, WP05, WP06 | **Subtasks**: 5

Create shape-based assertion tests validating all contract surfaces against upstream 3.0.0 shape.

- [ ] T040: Create `tests/contract/` directory and fixture data from upstream contracts
- [ ] T041: `test_event_envelope.py` — construct events via live code, assert 3.0.0 shape
- [ ] T042: `test_orchestrator_api.py` — invoke commands, assert response matches contract
- [ ] T043: `test_body_sync.py` — construct upload payload, assert canonical fields
- [ ] T044: `test_tracker_bind.py` — construct bind payload, assert `build_id` present

**Requirement refs**: NFR-002

---

### WP08 – End-to-End Audit + Cleanup
**File**: `tasks/WP08-audit-cleanup.md`
**Priority**: Medium | **Dependencies**: WP07 | **Subtasks**: 4

Grep-based audit of entire codebase for leaked feature-era surfaces. Fix anything found.

- [ ] T045: Grep `feature_slug` in `src/specify_cli/` excluding upgrade/migration → must be zero
- [ ] T046: Grep `FEATURE_NOT_FOUND`, `FEATURE_NOT_READY`, `FeatureCreated`, `FeatureCompleted` → must be zero
- [ ] T047: Grep `aggregate_type.*Feature`, `mission_key` excluding migration → must be zero
- [ ] T048: Fix any remaining leaks and document audit results

**Requirement refs**: FR-015, FR-016, FR-017

---

## Phase E: Release

### WP09 – Release Coordination
**File**: `tasks/WP09-release-coordination.md`
**Priority**: Medium | **Dependencies**: WP08 | **Subtasks**: 2

Verify external consumer readiness. Document release gate status.

- [ ] T049: Verify Priivacy-ai/spec-kitty-orchestrator#6 status and readiness
- [ ] T050: Validate updated orchestrator against renamed contract; document release readiness

**Requirement refs**: FR-021
