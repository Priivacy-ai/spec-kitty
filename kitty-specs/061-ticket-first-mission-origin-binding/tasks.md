# Tasks: Ticket-First Mission Origin Binding

**Feature**: 061-ticket-first-mission-origin-binding
**Date**: 2026-04-01
**Target Branch**: main

## Subtask Register

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create `OriginCandidate` frozen dataclass | WP01 | [P] |
| T002 | Create `SearchOriginResult` frozen dataclass | WP01 | [P] |
| T003 | Create `MissionFromTicketResult` dataclass | WP01 | [P] |
| T004 | Add `set_origin_ticket()` mutation helper to `feature_metadata.py` | WP01 | |
| T005 | Add `origin_ticket` to `FeatureMetaOptional` TypedDict | WP01 | |
| T006 | Write tests for dataclass construction and field validation | WP01 | |
| T007 | Write tests for `set_origin_ticket()` — writes, preserves, validates | WP01 | |
| T008 | Add `MissionOriginBound` to `_PAYLOAD_RULES` dict in emitter | WP02 | |
| T009 | Add `emit_mission_origin_bound()` method to `EventEmitter` class | WP02 | |
| T010 | Add `MissionOriginBound` validators (feature_slug, provider, fields) | WP02 | |
| T011 | Write tests for `emit_mission_origin_bound()` payload validation | WP02 | |
| T012 | Write tests for event routing and offline queue behavior | WP02 | |
| T013 | Add `_SEARCH_ISSUES_PATH` and `_BIND_ORIGIN_PATH` class constants | WP03 | |
| T014 | Implement `search_issues()` method on `SaaSTrackerClient` | WP03 | |
| T015 | Implement `bind_mission_origin()` method on `SaaSTrackerClient` | WP03 | |
| T016 | Write tests for `search_issues()` — 200, empty, 401/403, 404, 422, 429 | WP03 | |
| T017 | Write tests for `bind_mission_origin()` — 200, same-origin, 409, 401 | WP03 | |
| T018 | Create `core/feature_creation.py` with `FeatureCreationResult` dataclass | WP04 | |
| T019 | Create `FeatureCreationError` exception class | WP04 | |
| T020 | Extract core logic from `create_feature()` into `create_feature_core()` | WP04 | |
| T021 | Refactor `create_feature()` typer command to thin wrapper | WP04 | |
| T022 | Write tests for `create_feature_core()` — happy path, errors | WP04 | |
| T023 | Verify existing `create_feature` CLI behavior unchanged (regression) | WP04 | |
| T024 | Implement `search_origin_candidates()` in `tracker/origin.py` | WP05 | |
| T025 | Implement `bind_mission_origin()` in `tracker/origin.py` (SaaS-first) | WP05 | |
| T026 | Implement `start_mission_from_ticket()` in `tracker/origin.py` | WP05 | |
| T027 | Implement slug derivation from ticket key/title | WP05 | |
| T028 | Write tests for `search_origin_candidates()` — all 6 spec scenarios | WP05 | |
| T029 | Write tests for `bind_mission_origin()` — ordering, re-bind semantics | WP05 | |
| T030 | Write tests for `start_mission_from_ticket()` — full orchestration | WP05 | |
| T031 | End-to-end test: search → confirm → bind with mocked HTTP | WP06 | |
| T032 | End-to-end test: `start_mission_from_ticket` full flow | WP06 | |
| T033 | Test error propagation across all layers | WP06 | |
| T034 | Test SaaS-first write ordering (SaaS fail → no local write) | WP06 | |
| T035 | Test offline event queuing for `MissionOriginBound` | WP06 | |

## Dependency Graph

```
WP01 (data models + metadata) ──┐
WP02 (event registration)   ────┤
WP03 (SaaS client transport) ───┼──▶ WP05 (orchestration) ──▶ WP06 (integration)
WP04 (create-feature extract) ──┘
```

**Parallelization**: WP01, WP02, WP03, WP04 have zero interdependencies and can run simultaneously (4-way parallel). WP05 is the convergence point. WP06 is the final gate.

---

## Phase 1: Foundation (parallel)

### WP01: Data Models and Metadata Helper

**Priority**: High (foundation for all downstream work)
**Subtasks**: T001–T007 (7 subtasks)
**Dependencies**: None
**Prompt**: `tasks/WP01-data-models-metadata-helper.md`
**Estimated size**: ~350 lines

**Goal**: Create the three origin dataclasses in `tracker/origin.py`, add the `set_origin_ticket()` mutation helper to `feature_metadata.py`, and write tests for all of them.

**Implementation sketch**:
1. Create `tracker/origin.py` with `OriginCandidate`, `SearchOriginResult`, `MissionFromTicketResult`
2. Add `set_origin_ticket()` to `feature_metadata.py` following `set_documentation_state()` pattern
3. Add `origin_ticket` to `FeatureMetaOptional` TypedDict
4. Write tests in `tests/sync/tracker/test_origin.py` (dataclass tests)
5. Write tests in `tests/specify_cli/test_feature_metadata.py` (metadata helper tests)

**Risks**: None — pure data structures and a thin mutation helper.

---

### WP02: Event Registration

**Priority**: High (foundation for downstream orchestration)
**Subtasks**: T008–T012 (5 subtasks)
**Dependencies**: None
**Prompt**: `tasks/WP02-event-registration.md`
**Estimated size**: ~300 lines

**Goal**: Register `MissionOriginBound` as a new event type in the emitter system with full payload validation and an `emit_mission_origin_bound()` method.

**Implementation sketch**:
1. Add `MissionOriginBound` entry to `_PAYLOAD_RULES` in `sync/emitter.py`
2. Add `emit_mission_origin_bound()` method to `EventEmitter`
3. Write payload validation tests
4. Write event routing / offline queue tests

**Risks**: Must follow existing event patterns exactly — validator lambdas, aggregate type.

---

### WP03: SaaS Client Transport Extensions

**Priority**: High (foundation for downstream orchestration)
**Subtasks**: T013–T017 (5 subtasks)
**Dependencies**: None
**Prompt**: `tasks/WP03-saas-client-transport.md`
**Estimated size**: ~400 lines

**Goal**: Add `search_issues()` and `bind_mission_origin()` to `SaaSTrackerClient` with full error handling and retry behavior.

**Implementation sketch**:
1. Add placeholder path constants
2. Implement `search_issues()` using `_request_with_retry()`
3. Implement `bind_mission_origin()` using `_request_with_retry()` + `Idempotency-Key`
4. Write HTTP-layer tests with mocked httpx.Client and `_make_response()` helper

**Risks**: SaaS endpoint paths are placeholders (Team B dependency). Tests use mocked HTTP so implementation proceeds regardless.

---

### WP04: create-feature Core Extraction

**Priority**: High (prerequisite for orchestration)
**Subtasks**: T018–T023 (6 subtasks)
**Dependencies**: None
**Prompt**: `tasks/WP04-create-feature-extraction.md`
**Estimated size**: ~450 lines

**Goal**: Extract the core feature-creation logic from the typer command into `src/specify_cli/core/feature_creation.py` as a reusable public function. Refactor the existing CLI command to a thin wrapper. Verify no regression.

**Implementation sketch**:
1. Create `core/feature_creation.py` with `FeatureCreationResult` + `FeatureCreationError`
2. Move core logic from `create_feature()` (lines 518–833 in `feature.py`)
3. Refactor `create_feature()` to call `create_feature_core()` + format output
4. Write unit tests for `create_feature_core()`
5. Run existing CLI tests to verify regression-free

**Risks**: Large refactor (~300 lines of logic to move). Must preserve all side effects (git commits, event emission, dossier sync).

---

## Phase 2: Orchestration

### WP05: Service-Layer Orchestration

**Priority**: Critical (normative API surface)
**Subtasks**: T024–T030 (7 subtasks)
**Dependencies**: WP01, WP02, WP03, WP04
**Prompt**: `tasks/WP05-service-layer-orchestration.md`
**Estimated size**: ~500 lines

**Goal**: Implement the three service-layer functions in `tracker/origin.py` that compose the foundation, transport, and creation layers into the normative API consumed by `/spec-kitty.specify`.

**Implementation sketch**:
1. Implement `search_origin_candidates()` — config load, validation, delegation
2. Implement `bind_mission_origin()` — SaaS-first ordering, local write, event emit
3. Implement `start_mission_from_ticket()` — slug derivation, create, bind
4. Write tests covering all 6 spec scenarios + ordering + re-bind semantics

**Risks**: Convergence of 4 dependencies. SaaS-first write ordering must be verified. Slug derivation edge cases.

---

## Phase 3: Validation

### WP06: Integration Testing

**Priority**: High (final quality gate)
**Subtasks**: T031–T035 (5 subtasks)
**Dependencies**: WP05
**Prompt**: `tasks/WP06-integration-testing.md`
**Estimated size**: ~350 lines

**Goal**: End-to-end integration tests that wire all layers together with mocked HTTP at the httpx boundary. Verify the full search → confirm → bind → create flow, error propagation, write ordering, and offline event queuing.

**Implementation sketch**:
1. Build test fixtures that compose real service functions with mocked HTTP
2. Test full happy-path flow
3. Test error propagation chain
4. Test SaaS-first ordering invariant
5. Test offline event queuing

**Risks**: Test complexity — many layers to compose. Keep fixtures focused and reusable.
