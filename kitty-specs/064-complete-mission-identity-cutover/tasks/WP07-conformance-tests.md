---
work_package_id: WP07
title: Shape Conformance Tests
dependencies: [WP04, WP05, WP06]
requirement_refs:
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T042
- T043
- T044
- T045
- T046
phase: Phase D - Validation
assignee: ''
agent: ''
shell_pid: ''
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/contract/
execution_mode: code_change
owned_files:
- tests/contract/**
---

# Work Package Prompt: WP07 – Shape Conformance Tests

## Objective

Create shape-based assertion tests that validate all contract surfaces against the upstream 3.0.0 contract. Tests construct payloads via live code paths and assert the output shape matches the canonical contract — required fields present, forbidden fields absent.

## Context

C-002 and C-003 prevent direct package import testing (spec-kitty-events 2.9.0 installed, not 3.0.0; spec-kitty-saas not importable). Shape assertions are the conformance strategy.

Expected shapes are derived from:
- `kitty-specs/064-complete-mission-identity-cutover/contracts/event-envelope.md`
- `kitty-specs/064-complete-mission-identity-cutover/contracts/orchestrator-api.md`
- `kitty-specs/064-complete-mission-identity-cutover/contracts/body-sync.md`
- `kitty-specs/064-complete-mission-identity-cutover/contracts/tracker-bind.md`
- `kitty-specs/064-complete-mission-identity-cutover/contracts/upstream-3.0.0-shape.json`

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`

## Implementation

### T042: Create Test Directory and Fixtures

**Purpose**: Set up the contract test infrastructure.

**Steps**:
1. Create `tests/contract/__init__.py`
2. Create `tests/contract/conftest.py` with common fixtures:
   - `canonical_envelope_fields`: set of required envelope fields from the 3.0.0 contract
   - `forbidden_fields`: set of fields that must never appear in any live output
   - `canonical_body_sync_fields`: required body sync fields
   - Load these from `src/specify_cli/core/upstream_contract.json` (the vendored artifact)

### T043: Event Envelope Shape Test

**Purpose**: Events constructed via live code must match 3.0.0 envelope shape.

**Steps**:
1. Create `tests/contract/test_event_envelope.py`
2. Construct a test event using the actual `EventEmitter` (or its envelope construction path)
3. Assert:
   - `schema_version` is present and equals `"3.0.0"`
   - `build_id` is present and non-empty
   - `aggregate_type` equals `"Mission"` (not `"Feature"`)
   - `event_type` is a canonical type (e.g., `"MissionCreated"`, not `"FeatureCreated"`)
   - `feature_slug` is NOT a key in the envelope
   - `feature_number` is NOT a key in the envelope
4. Test for each canonical event type if feasible (MissionCreated, MissionClosed, WPStatusChanged at minimum)

### T044: Orchestrator API Response Shape Test

**Purpose**: CLI command output must match post-cutover contract.

**Steps**:
1. Create `tests/contract/test_orchestrator_api.py`
2. Invoke `mission-state` via the typer test runner (or subprocess) with a test fixture
3. Assert response JSON:
   - Contains `mission_slug`, NOT `feature_slug`
   - `command` field uses mission-era name
   - Error code on not-found is `MISSION_NOT_FOUND` (not `FEATURE_NOT_FOUND`)
4. Invoke `accept-mission` on incomplete fixture → assert `MISSION_NOT_READY`
5. Invoke `feature-state` → assert unknown command error (exit code != 0)
6. Invoke `mission-state --feature` → assert unknown option error

### T045: Body Sync Payload Shape Test

**Purpose**: Upload payload must match canonical body sync contract.

**Steps**:
1. Create `tests/contract/test_body_sync.py`
2. Construct a `NamespaceRef` with canonical fields
3. Construct a `BodyUploadTask` from the namespace ref
4. Call `_build_request_body(task)` (or the equivalent)
5. Assert payload:
   - Contains `mission_slug`, `mission_type`
   - Does NOT contain `feature_slug`, `mission_key`
   - All 9 expected fields present per `contracts/body-sync.md`

### T046: Tracker Bind Payload Shape Test

**Purpose**: Bind payload must include build_id.

**Steps**:
1. Create `tests/contract/test_tracker_bind.py`
2. Construct a `ProjectIdentity` from test fixtures
3. Build the `project_identity` dict as done in `tracker.py`
4. Assert:
   - Contains `build_id` (non-empty string)
   - Contains `uuid`, `slug`, `node_id`, `repo_slug`
   - Does NOT contain `feature_slug` or any feature-era fields

## Definition of Done

- [ ] `tests/contract/` directory with 4 test modules
- [ ] Event envelope shape validated (required + forbidden fields)
- [ ] Orchestrator API shape validated (commands, errors, payloads)
- [ ] Body sync shape validated (canonical fields only)
- [ ] Tracker bind shape validated (build_id present)
- [ ] All conformance tests pass
- [ ] NFR-002: 100% of envelope/payload fields validated

## Risks

- Tests may need mock fixtures for event construction — keep mocking minimal, prefer real code paths
- Orchestrator API tests need a test feature directory — use tmp_path fixtures
