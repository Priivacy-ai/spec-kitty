# Tasks: SaaS-Mediated CLI Tracker Reflow

**Feature**: 059-saas-mediated-cli-tracker-reflow
**Branch**: main → main
**Date**: 2026-03-30
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Create SaaSTrackerClient class skeleton with CredentialStore/SyncConfig integration | WP01 | |
| T002 | Implement _request() base method: auth injection, X-Team-Slug, server URL, error parsing | WP01 | |
| T003 | Implement retry behaviors: 401 refresh+retry, 429 retry_after, network fail-fast | WP01 | |
| T004 | Implement synchronous endpoints: pull(), status(), mappings() | WP01 | |
| T005 | Implement _poll_operation() with exponential backoff | WP01 | |
| T006 | Implement async-capable endpoints: push(), run() with Idempotency-Key + 200/202 | WP01 | |
| T007 | Write test_saas_client.py for all endpoints and error paths | WP01 | |
| T008 | Add project_slug to TrackerProjectConfig + update serialization | WP02 | [P] |
| T009 | Update is_configured for provider-aware check | WP02 | [P] |
| T010 | Define SAAS_PROVIDERS, LOCAL_PROVIDERS, REMOVED_PROVIDERS constants | WP02 | [P] |
| T011 | Write config tests for project_slug roundtrip + provider classification | WP02 | [P] |
| T012 | Create SaaSTrackerService class with SaaS client integration | WP03 | |
| T013 | Implement bind/unbind for SaaS-backed providers | WP03 | |
| T014 | Implement pull/push/run/status/map_list via SaaS client delegation | WP03 | |
| T015 | Implement map_add + sync_publish hard-fails with guidance | WP03 | |
| T016 | Write test_saas_service.py with mocked client | WP03 | |
| T017 | Create LocalTrackerService class skeleton | WP04 | [P] |
| T018 | Extract bind/unbind from current TrackerService | WP04 | [P] |
| T019 | Extract status + sync_pull/push/run (direct connector) | WP04 | [P] |
| T020 | Extract map_add/map_list (SQLite mappings) | WP04 | [P] |
| T021 | Write test_local_service.py for beads/fp behavior | WP04 | [P] |
| T022 | Refactor service.py into thin façade with _resolve_backend() | WP05 | |
| T023 | Remove all old direct-provider code from service.py | WP05 | |
| T024 | Remove SaaS-backed + Azure entries from factory.py | WP05 | |
| T025 | Update SUPPORTED_PROVIDERS, normalize_provider(), __init__.py | WP05 | |
| T026 | Delete test_service_publish.py (10,526 lines) | WP05 | |
| T027 | Write test_service.py for façade dispatch | WP05 | |
| T028 | Update bind command (--project-slug, hard-fail --credential for SaaS) | WP06 | |
| T029 | Update unbind/status commands (façade dispatch, SaaS display) | WP06 | |
| T030 | Update sync pull/push/run commands (façade dispatch, SaaS envelope display) | WP06 | |
| T031 | Update sync publish (hard-fail) + map add/list (hard-fail add for SaaS) | WP06 | |
| T032 | Update providers list + help text (SaaS vs local distinction) | WP06 | |
| T033 | Update JSON output for SaaS envelope structures | WP06 | |
| T034 | Update test_tracker.py CLI integration tests | WP06 | |

## Work Packages

### Phase 1: Foundation (parallel)

#### WP01 — SaaS Tracker Client
**Priority**: P1 (critical path)
**Prompt**: [tasks/WP01-saas-tracker-client.md](tasks/WP01-saas-tracker-client.md)
**Subtasks**: T001–T007 (7 subtasks, ~500 lines)
**Dependencies**: None
**Goal**: Create the HTTP transport layer for all SaaS tracker API communication. Covers auth injection, error envelope parsing, retry behaviors, operation polling, and all 6 endpoint methods.
**Success**: All SaaS tracker endpoints callable with proper auth, errors parsed, 202 polling works, tests pass.

#### WP02 — Config Model + Provider Classification
**Priority**: P1 (parallel with WP01)
**Prompt**: [tasks/WP02-config-provider-classification.md](tasks/WP02-config-provider-classification.md)
**Subtasks**: T008–T011 (4 subtasks, ~250 lines)
**Dependencies**: None
**Goal**: Add project_slug to tracker config for SaaS-backed bindings. Define provider classification constants (SAAS/LOCAL/REMOVED).
**Success**: Config roundtrips project_slug correctly, provider constants defined, tests pass.

### Phase 2: Service Implementations (parallel after Phase 1)

#### WP03 — SaaSTrackerService
**Priority**: P1
**Prompt**: [tasks/WP03-saas-tracker-service.md](tasks/WP03-saas-tracker-service.md)
**Subtasks**: T012–T016 (5 subtasks, ~400 lines)
**Dependencies**: WP01, WP02
**Goal**: Create the SaaS-backed tracker service that delegates all operations to SaaSTrackerClient. Hard-fails map_add and sync_publish.
**Success**: All SaaS-backed operations delegate to client, hard-fails work with guidance, tests pass.

#### WP04 — LocalTrackerService
**Priority**: P1 (parallel with WP03)
**Prompt**: [tasks/WP04-local-tracker-service.md](tasks/WP04-local-tracker-service.md)
**Subtasks**: T017–T021 (5 subtasks, ~350 lines)
**Dependencies**: WP02
**Goal**: Extract beads/fp direct-connector logic from current TrackerService into a dedicated class. Mechanical move, not rewrite.
**Success**: beads/fp behavior identical to before, existing credential + store tests still pass.

### Phase 3: Integration

#### WP05 — Façade, Factory + Dead Code Removal
**Priority**: P1
**Prompt**: [tasks/WP05-facade-factory-dead-code.md](tasks/WP05-facade-factory-dead-code.md)
**Subtasks**: T022–T027 (6 subtasks, ~450 lines)
**Dependencies**: WP03, WP04
**Goal**: Refactor TrackerService into thin façade dispatching to SaaS/local backends. Remove SaaS-backed + Azure entries from factory. Delete 10,526 lines of obsolete snapshot publish tests.
**Success**: Façade dispatches correctly, factory only has beads/fp, dead code gone, tests pass.

### Phase 4: CLI Surface (parallel)

#### WP06 — CLI Command Updates
**Priority**: P1
**Prompt**: [tasks/WP06-cli-command-updates.md](tasks/WP06-cli-command-updates.md)
**Subtasks**: T028–T034 (7 subtasks, ~500 lines)
**Dependencies**: WP05
**Goal**: Update all tracker CLI commands to dispatch through the new façade. Hard-break guidance for SaaS-backed legacy operations. Updated help text and JSON output.
**Success**: All commands work for both SaaS and local providers, hard-breaks display correct guidance, JSON output coherent, tests pass.

## Dependency Graph

```
WP01 (SaaS Client) ──────────┐
                               ├──▶ WP03 (SaaS Service) ──┐
WP02 (Config + Constants) ──┬─┘                            ├──▶ WP05 (Façade) ──▶ WP06 (CLI)
                            └──▶ WP04 (Local Service) ─────┘
```

## Parallelization Waves

| Wave | WPs | Agents |
|------|-----|--------|
| 1 | WP01, WP02 | 2 parallel |
| 2 | WP03, WP04 | 2 parallel |
| 3 | WP05 | 1 (integration) |
| 4 | WP06 | 1 (CLI surface) |

**Critical path**: WP01 → WP03 → WP05 → WP06 (4 sequential steps)
**Total with parallelization**: 4 waves instead of 6 sequential

## Requirement Coverage

| WP | Requirements |
|----|-------------|
| WP01 | FR-002, FR-003, FR-004, FR-005, FR-015, FR-016, FR-017, FR-018, FR-019, FR-020 |
| WP02 | FR-001, FR-012, FR-013 |
| WP03 | FR-001, FR-002, FR-003, FR-004, FR-006, FR-007, FR-008, FR-009, FR-011 |
| WP04 | FR-014 |
| WP05 | FR-012, FR-013, FR-021, FR-022, FR-023 |
| WP06 | FR-001, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-013, FR-024, FR-025, FR-026 |
