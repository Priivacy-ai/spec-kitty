# Implementation Plan: Complete Mission Identity Cutover

**Branch**: `main` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/064-complete-mission-identity-cutover/spec.md`

## Summary

Complete and clean up a partially-landed mission/build identity cutover already on `main`. The codebase has some canonical mission-era changes in place (MissionCreated/MissionClosed events, ProjectIdentity with build_id, canonical create command) but still exposes active feature-era surfaces: module names, identity alias injection, orchestrator API commands/error codes, body sync schema fields, and meta.json scaffolding. This plan removes all remaining feature-era surfaces from live paths, adds a central compatibility gate, and validates conformance against the upstream spec-kitty-events 3.0.0 and spec-kitty-saas contracts.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic, requests, httpx, websockets
**Storage**: Filesystem (YAML, JSON, Markdown) + SQLite (body upload queue, offline event queue)
**Testing**: pytest (90%+ coverage for new code), mypy --strict, integration tests for CLI commands
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Single Python package (src/specify_cli/)
**Constraints**: No fallback mechanisms (C-007), shims must be upgrade-only (C-006), upstream contracts immutable (C-001)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter Requirement | Status | Notes |
|-------------------|--------|-------|
| Python 3.11+ | PASS | Existing codebase requirement, no change |
| typer CLI framework | PASS | CLI commands use typer |
| rich console output | PASS | Status/progress output uses rich |
| ruamel.yaml for YAML | PASS | Config and frontmatter parsing |
| pytest 90%+ coverage | PASS | Required for all new/modified code |
| mypy --strict | PASS | All new code must pass strict type checking |
| Integration tests for CLI | PASS | Orchestrator API commands need integration tests |
| CLI ops < 2 seconds | PASS | Compatibility gate adds < 5ms (NFR-003) |
| Cross-platform | PASS | SQLite ALTER TABLE RENAME COLUMN available on all platforms (Python 3.11+ bundles SQLite 3.39+) |

No charter violations. No complexity justification needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/064-complete-mission-identity-cutover/
├── spec.md              # Feature specification (21 FRs, 5 NFRs, 7 Cs)
├── plan.md              # This file
├── research.md          # Phase 0: 8 architectural decisions
├── data-model.md        # Phase 1: 10 entity change specifications
├── quickstart.md        # Phase 1: implementation guide
├── contracts/
│   ├── orchestrator-api.md   # Post-cutover orchestrator API contract
│   ├── event-envelope.md     # 3.0.0 event envelope contract
│   ├── body-sync.md          # Post-cutover body sync contract
│   └── tracker-bind.md       # Post-cutover tracker bind contract
└── checklists/
    └── requirements.md       # Spec quality checklist
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   ├── mission_creation.py      # RENAMED from feature_creation.py
│   ├── identity_aliases.py      # DELETED (alias injection removed)
│   └── contract_gate.py         # NEW: central compatibility gate
├── mission_metadata.py          # RENAMED from feature_metadata.py
├── cli/commands/
│   ├── agent/
│   │   └── mission.py           # RENAMED from feature.py
│   ├── tracker.py               # MODIFIED: add build_id to bind
│   └── materialize.py           # MODIFIED: remove alias injection
├── sync/
│   ├── namespace.py             # MODIFIED: field renames
│   ├── body_queue.py            # MODIFIED: field renames + schema migration
│   ├── body_transport.py        # MODIFIED: payload field renames
│   ├── emitter.py               # MODIFIED: gate insertion
│   ├── batch.py                 # MODIFIED: gate insertion
│   └── client.py                # MODIFIED: gate insertion
├── tracker/
│   └── saas_client.py           # MODIFIED: gate insertion
├── orchestrator_api/
│   └── commands.py              # MODIFIED: command/error/payload renames
├── status/
│   ├── models.py                # MODIFIED: remove alias injection
│   ├── views.py                 # MODIFIED: remove alias injection
│   └── progress.py              # MODIFIED: remove alias injection
├── next/
│   └── decision.py              # MODIFIED: remove alias injection
└── upgrade/
    └── migration_064.py         # NEW: meta.json + queue migration

tests/
├── contract/                    # NEW: shape conformance tests
│   ├── test_event_envelope.py
│   ├── test_orchestrator_api.py
│   ├── test_body_sync.py
│   └── test_tracker_bind.py
├── specify_cli/core/
│   └── test_contract_gate.py    # NEW: gate unit tests
└── (existing test files with updated imports)
```

**Structure Decision**: Single Python package, existing layout. New files: `core/contract_gate.py` (gate), `upgrade/migration_064.py` (migration), `tests/contract/` (conformance tests). Module renames tracked above.

## Implementation Phases

### Phase A: Foundation (Independent, parallelizable)

**A1: Compatibility Gate**
- Vendor the machine-readable contract artifact `contracts/upstream-3.0.0-shape.json` into the package (e.g., `src/specify_cli/core/upstream_contract.json`) so it is loadable at runtime
- Create `src/specify_cli/core/contract_gate.py`
- Implement `validate_outbound_payload(payload: dict, context: str) -> None`
- Gate must load validation rules from the vendored `upstream-3.0.0-shape.json` artifact at runtime, NOT from hand-maintained constants
- Validation enforces `required_fields`, `forbidden_fields`, and `allowed`/`forbidden` enumerations from the artifact
- Raise `ContractViolationError` with diagnostic message on failure
- Insert at 6 chokepoints (see research.md Decision 3)
- Unit tests for all validation rules + pass-through behavior
- If upstream contract evolves, the fix is to update the vendored artifact from the authoritative source, not to patch gate code

**A2: meta.json Canonical Writes**
- Update the create-feature/create-mission scaffolding path to write canonical fields:
  - `mission_number` (not `feature_number`)
  - `mission_slug` (not `feature_slug`)
  - `mission_type` (not `mission`)
- Update all code paths that write meta.json (scaffolding, upgrade, status)
- Unit tests verifying new writes use canonical fields only

### Phase B: Core Renames (Sequential, high blast radius)

**B1: Rename feature_creation.py → mission_creation.py**
- `git mv src/specify_cli/core/feature_creation.py src/specify_cli/core/mission_creation.py`
- Update 2 production imports: `tracker/origin.py:335`, `cli/commands/agent/feature.py:548`
- Update 3 test files
- Run tests to verify

**B2: Rename feature_metadata.py → mission_metadata.py**
- `git mv src/specify_cli/feature_metadata.py src/specify_cli/mission_metadata.py`
- Update 10 production imports:
  - `upgrade/feature_meta.py:18`
  - `core/feature_creation.py:303` (now mission_creation.py)
  - `orchestrator_api/commands.py:956`
  - `acceptance.py:29`
  - `tracker/origin.py:20`
  - `status/emit.py:34`
  - `cli/commands/implement.py:19`
  - `dashboard/diagnostics.py:24`
  - `scripts/tasks/tasks_cli.py:70`
  - `doc_state.py:46`
- Update 3 test files
- Run tests to verify

**B3: Rename agent/feature.py → agent/mission.py**
- `git mv src/specify_cli/cli/commands/agent/feature.py src/specify_cli/cli/commands/agent/mission.py`
- Update 1 production import: `cli/commands/agent/tasks.py:1958`
- Update 35+ test imports across:
  - `tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py`
  - `tests/specify_cli/test_cli/test_map_requirements.py`
  - `tests/tasks/test_finalize_tasks_json_output_unit.py`
  - `tests/missions/test_feature_lifecycle_unit.py`
  - `tests/agent/test_agent_feature.py`
  - `tests/agent/cli/commands/test_feature_slug_validation.py`
  - `tests/agent/test_create_feature_branch_unit.py`
  - `tests/agent/test_create_feature_branch.py`
- Run tests to verify

**B4: Delete identity_aliases.py**
- Remove `src/specify_cli/core/identity_aliases.py`
- Update 7 production files to remove imports:
  - `next/decision.py:24` — emit `mission_slug` directly
  - `orchestrator_api/commands.py:32` — emit `mission_slug` directly
  - `status/models.py:15` — StatusSnapshot.to_dict emits `mission_slug` directly
  - `status/progress.py:19` — emit `mission_slug` directly
  - `status/views.py:18` — emit `mission_slug` directly
  - `cli/commands/agent/status.py:20` — emit `mission_slug` directly
  - `cli/commands/materialize.py:18` — emit `mission_slug` directly
- At each of the 27 call sites: replace `with_tracked_mission_slug_aliases(data)` with `data` (it already contains `mission_slug`)
- Run tests to verify no `feature_slug` appears in live outputs

### Phase C: Contract Cleanup (Partially parallelizable after Phase B)

**C1: Orchestrator API Rename**
- Rename 3 commands: `feature-state` → `mission-state`, `accept-feature` → `accept-mission`, `merge-feature` → `merge-mission`
- Rename 2 error codes: `FEATURE_NOT_FOUND` → `MISSION_NOT_FOUND`, `FEATURE_NOT_READY` → `MISSION_NOT_READY`
- Rename CLI parameter: `--feature` → `--mission` on all 8 commands that accept a mission slug (FR-022)
- Remove `feature_slug` from all 8 command response payloads (already handled by B4 identity_aliases removal, but verify)
- Update internal function names: `feature_state()` → `mission_state()`, `accept_feature()` → `accept_mission()`, `merge_feature()` → `merge_mission()`
- Update internal parameter names: `feature: str` → `mission: str` across all command functions
- Update all tests referencing old command names, parameter names, and error codes
- Integration tests verifying old command names fail as unknown and `--feature` flag is not accepted

**C2: Body Sync Migration**
- Rename `NamespaceRef` fields: `feature_slug` → `mission_slug`, `mission_key` → `mission_type`
- Rename `BodyUploadTask` fields: `feature_slug` → `mission_slug`, `mission_key` → `mission_type`
- Update `_build_request_body()` to emit canonical payload (see contracts/body-sync.md)
- Remove the `mission_slug` compatibility alias line and the TODO comment
- Create `upgrade/migration_064.py` with SQLite ALTER TABLE RENAME COLUMN for queue schema
- Register migration in upgrade chain
- Test: populated queue with legacy rows survives migration with zero loss

**C3: Tracker Bind build_id**
- Add `build_id` to the `project_identity` dict in `cli/commands/tracker.py:355-360`
- Source from `identity.build_id` (already available on ProjectIdentity)
- Update tracker integration tests
- Verify via shape test (see contracts/tracker-bind.md)

**C4: Event Envelope Verification**
- Audit all event emission paths for `build_id` presence
- Audit all event serialization/deserialization paths for `build_id` preservation
- Verify `aggregate_type` is `"Mission"` everywhere, never `"Feature"`
- Verify payloads use `mission_slug`, `mission_number`, `mission_type`
- Fix any gaps found

### Phase D: Validation

**D1: Shape Conformance Tests**
- Create `tests/contract/` directory
- `test_event_envelope.py` — construct events via live code, assert 3.0.0 shape
- `test_orchestrator_api.py` — invoke commands, assert response shape matches contract
- `test_body_sync.py` — construct upload payload, assert canonical fields present and legacy absent
- `test_tracker_bind.py` — construct bind payload, assert `build_id` present
- Expected shapes derived from upstream contracts (spec-kitty-events @ 5b8e6dc, spec-kitty-saas @ 3a0e4af)

**D2: End-to-End Audit**
- Grep `feature_slug` across `src/specify_cli/` excluding `upgrade/` and `migration/` — must return zero
- Grep `FEATURE_NOT_FOUND`, `FEATURE_NOT_READY`, `FeatureCreated`, `FeatureCompleted` across active paths — must return zero
- Grep `aggregate_type.*Feature` across active paths — must return zero
- Grep `mission_key` across active paths (excluding migration) — must return zero
- Document results

### Phase E: Release Coordination

**E1: spec-kitty-orchestrator Update**
- Priivacy-ai/spec-kitty-orchestrator#6 must be resolved
- Updated orchestrator must be validated against the renamed contract
- Production rollout blocked until consumer is ready

## Dependency Graph

```
A1 (gate) ──────────────┐
                         ├──► B1 → B2 → B3 → B4 ──► C1 ──┐
A2 (meta.json) ─────────┘                          C2 ──┤
                                                    C3 ──┤
                                                    C4 ──┤
                                                         ├──► D1 → D2 ──► E1
                                                         │
                                                         └────────────────┘
```

- **A1, A2**: Independent, parallelizable
- **B1 → B2 → B3 → B4**: Sequential (each rename must be stable before the next)
- **C1, C2, C3, C4**: Partially parallelizable after B4 (C1 depends on B4 for alias removal; C2, C3, C4 are independent of each other)
- **D1, D2**: After all C-phase work
- **E1**: After D-phase validation passes

## Risk Mitigation

| Risk | Mitigation | Owner |
|------|-----------|-------|
| Module renames break 50+ imports | Incremental: rename one module, run full test suite, commit, repeat | Implementation agent |
| Orchestrator API breaks spec-kitty-orchestrator | Issue filed (Priivacy-ai/spec-kitty-orchestrator#6), lockstep release (FR-021) | Release coordinator |
| Body queue migration loses pending uploads | Test with populated queue; ALTER TABLE within transaction | Implementation agent |
| Compatibility gate too strict | Derive rules from upstream contract, not assumptions; test with real payloads | Implementation agent |
| identity_aliases removal breaks status output | Replace each of 27 call sites individually, test after each batch | Implementation agent |

## Charter Check (Post-Design)

| Charter Requirement | Status | Notes |
|-------------------|--------|-------|
| Python 3.11+ | PASS | No change |
| pytest 90%+ coverage | PASS | New tests in `tests/contract/`, gate tests, migration tests |
| mypy --strict | PASS | All new modules typed; renamed modules retain existing types |
| Integration tests for CLI | PASS | Orchestrator API integration tests for renamed commands |
| CLI ops < 2 seconds | PASS | Gate is a dict key check, < 1ms |
| Cross-platform | PASS | SQLite 3.39+ ALTER TABLE RENAME COLUMN on all platforms |

No new charter violations introduced by this design.
