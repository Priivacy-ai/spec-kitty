# Work Packages: Fix Doctrine Migration Test Failures

**Inputs**: Design documents from `kitty-specs/062-fix-doctrine-migration-test-failures/`
**Prerequisites**: plan.md (required), spec.md (user stories)

**Tests**: Tests are the primary deliverable — this mission fixes broken tests and adds a contract test.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).

---

## Work Package WP01: Update Hardcoded Mission Paths (Priority: P1)

**Goal**: Replace all hardcoded `src/specify_cli/missions/` paths in 4 test files with `MissionTemplateRepository.default_missions_root()`.
**Independent Test**: All 4 test files pass: `pytest tests/missions/test_mission_software_dev_integration.py tests/missions/test_documentation_mission.py tests/missions/test_documentation_templates.py tests/specify_cli/test_command_template_cleanliness.py`
**Prompt**: `tasks/WP01-update-hardcoded-mission-paths.md`
**Requirement Refs**: FR-001, C-002

### Included Subtasks

- [x] T001 [P] Fix `tests/missions/test_mission_software_dev_integration.py` path (lines 34-40)
- [x] T002 [P] Fix `tests/missions/test_documentation_mission.py` path (lines 12-13, 19)
- [x] T003 [P] Fix `tests/missions/test_documentation_templates.py` path (line 11)
- [x] T004 [P] Fix `tests/specify_cli/test_command_template_cleanliness.py` path
- [x] T005 Run all 4 files and verify zero failures

### Implementation Notes

- Import `MissionTemplateRepository` from `doctrine.missions.repository`
- Replace `Path(__file__).parents[N] / "src" / "specify_cli" / "missions"` with `MissionTemplateRepository.default_missions_root()`
- This avoids hardcoding `src/doctrine/missions/` and prevents future breakage if paths move again

### Parallel Opportunities

- T001-T004 are all independent file edits — fully parallelizable.

### Dependencies

- None (starting package).

### Risks & Mitigations

- `MissionTemplateRepository` import may fail if doctrine package not installed → already in editable install, tested in CI

---

## Work Package WP02: Fix Terminology and Assertion Mismatches (Priority: P1)

**Goal**: Update 2 test files with stale terminology (`"Feature"` → `"Mission"`, `feature=` → `mission=`).
**Independent Test**: `pytest tests/sync/test_emitter_origin.py tests/missions/test_feature_lifecycle_unit.py`
**Prompt**: `tasks/WP02-fix-terminology-assertions.md`
**Requirement Refs**: FR-002

### Included Subtasks

- [ ] T006 [P] Fix `tests/sync/test_emitter_origin.py` aggregate_type assertion (line 203)
- [ ] T007 [P] Fix `tests/missions/test_feature_lifecycle_unit.py` parameter name in mock assertion (line 117)
- [ ] T008 Verify both files pass locally

### Implementation Notes

- T006: Change `assert event["aggregate_type"] == "Feature"` to `== "Mission"` (confirmed by commit `1c5a7927`)
- T007: Read `accept_feature()` signature to confirm parameter was renamed from `feature=` to `mission=`, then update the mock assertion

### Parallel Opportunities

- T006 and T007 are independent file edits.

### Dependencies

- None.

### Risks & Mitigations

- Parameter rename may have broader impact → check all callers of `accept_feature()` / `top_level_accept()`

---

## Work Package WP03: Repair Mock Targets and Missing Fixtures (Priority: P1)

**Goal**: Fix 3 test files with broken mock targets, missing directories, or stale import assertions.
**Independent Test**: `pytest tests/init/test_worktree_topology.py tests/agent/cli/commands/test_workflow_profile_injection.py tests/init/test_feature_detection_integration.py`
**Prompt**: `tasks/WP03-repair-mock-targets-fixtures.md`
**Requirement Refs**: FR-003, FR-004

### Included Subtasks

- [ ] T009 Fix `tests/init/test_worktree_topology.py` — update mock target for `read_frontmatter`
- [ ] T010 Fix `tests/agent/cli/commands/test_workflow_profile_injection.py` — fix `_proposed/` path
- [ ] T011 Fix `tests/init/test_feature_detection_integration.py` — update import assertions
- [ ] T012 Verify all 3 files pass locally

### Implementation Notes

- T009: Read `src/specify_cli/core/worktree_topology.py` to find where `read_frontmatter` is imported from. Update mock patch target to match the actual import path.
- T010: Check if `src/doctrine/agent_profiles/_proposed/` should exist. If not, update the test to use `shipped/` or create the fixture.
- T011: Read `src/specify_cli/cli/commands/implement.py` to understand current import structure. Update test assertions to match.

### Parallel Opportunities

- T009, T010, T011 are independent files — parallelizable.

### Dependencies

- None.

### Risks & Mitigations

- T009 may reveal deeper API refactoring → if `read_frontmatter` was removed entirely, the test logic needs rewriting (not just path swap). Document and handle in-WP.

---

## Work Package WP04: Fix Migration Test Logic (Priority: P1)

**Goal**: Fix documentation mission migration test to assert behavior consistent with current migration logic.
**Independent Test**: `pytest tests/upgrade/test_m_0_12_0_documentation_mission_unit.py`
**Prompt**: `tasks/WP04-fix-migration-test-logic.md`
**Requirement Refs**: FR-005

### Included Subtasks

- [ ] T013 Read migration code `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py` to understand current behavior
- [ ] T014 Determine whether test or migration is wrong regarding `command-templates/` directory
- [ ] T015 Apply fix (update test assertion or migration filtering) and verify

### Implementation Notes

- The test asserts `command-templates/` should NOT be copied by the migration, but the migration copies the full directory tree. Investigate which is the intended behavior.
- If migration is correct: update test to expect `command-templates/` to exist after migration
- If test is correct: add filtering to migration to exclude `command-templates/` (exception to C-001)

### Parallel Opportunities

- None — this is a single investigation.

### Dependencies

- None.

### Risks & Mitigations

- Changing migration behavior could affect existing projects → check if other tests depend on the migration copying command-templates

---

## Work Package WP05: Fix Dashboard Scanner and JS Key Mismatch (Priority: P1)

**Goal**: Validate the two dashboard fixes already applied during triage (scanner NameError, JS key mismatch).
**Independent Test**: Dashboard loads at `http://127.0.0.1:9239` and the feature selector shows missions.
**Prompt**: `tasks/WP05-fix-dashboard-scanner-js.md`
**Requirement Refs**: FR-008, FR-009

### Included Subtasks

- [ ] T016 Verify `src/specify_cli/dashboard/scanner.py` fix — `feature_dir` → `mission_dir` on lines 367, 371
- [ ] T017 Verify `src/specify_cli/dashboard/static/dashboard/dashboard.js` fix — `data.missions || data.features` on lines 1244-1246
- [ ] T018 Run dashboard locally and confirm feature selector populates

### Implementation Notes

- Both fixes were applied during the triage conversation. This WP validates they are correct and complete.
- Scanner fix: the `CanonicalStatusNotFoundError` handler referenced `feature_dir` (undefined) instead of `mission_dir` (in scope)
- JS fix: API response keys were renamed (`features` → `missions`, `active_feature_id` → `active_mission_id`) but JS not updated

### Parallel Opportunities

- T016 and T017 are independent verifications.

### Dependencies

- None.

### Risks & Mitigations

- JS backward-compat (`data.missions || data.features`) may mask future issues → WP08 architect review will evaluate clean break

---

## Work Package WP06: Add Dashboard API Contract Test (Priority: P2)

**Goal**: Create a pytest that validates the dashboard JS reads the same response keys the Python API emits.
**Independent Test**: `pytest tests/test_dashboard/test_api_contract.py`
**Prompt**: `tasks/WP06-dashboard-api-contract-test.md`
**Requirement Refs**: FR-010

### Included Subtasks

- [ ] T019 Extract canonical response keys from `handle_missions_list()` in `src/specify_cli/dashboard/handlers/missions.py`
- [ ] T020 Create `tests/test_dashboard/test_api_contract.py` with key-matching assertions
- [ ] T021 Add tests for kanban and constitution endpoints
- [ ] T022 Verify test catches the original bug (JS referencing `data.features` fails)

### Implementation Notes

- The test reads the JS file as text and asserts each response key appears as `data.<key>`, `data["<key>"]`, or `data['<key>']`
- Mark as `pytest.mark.fast` — no server needed, pure string matching
- Reference issue: Priivacy-ai/spec-kitty#361 for future TypedDict codegen approach

### Parallel Opportunities

- T019-T021 are sequential (need keys before writing test).

### Dependencies

- Depends on WP05 (the JS fix must be in place for the contract test to pass).

### Risks & Mitigations

- String matching is brittle (minification, variable aliasing) → acceptable for now, TypedDict codegen is the long-term fix

---

## Work Package WP07: Targeted Coverage + CI Gate Split (Priority: P2)

**Goal**: Write tests for critical changed paths and split the CI diff-cover gate into enforced (critical) + advisory (everything else).
**Independent Test**: Critical-path diff-coverage >= 90%. CI workflow validates with split gates.
**Prompt**: `tasks/WP07-targeted-coverage-ci-split.md`
**Requirement Refs**: FR-006, NFR-002

### Included Subtasks

- [ ] T023 Measure diff-coverage after WP01-06 to identify remaining gaps
- [ ] T024 [P] Write tests for `dashboard/handlers/missions.py` critical paths
- [ ] T025 [P] Write tests for `core/mission_detection.py` uncovered changed lines
- [ ] T026 Split `.github/workflows/ci-quality.yml` diff-cover into enforced critical + advisory full
- [ ] T027 Verify CI workflow config is syntactically valid

### Implementation Notes

- T023: Run `diff-cover` locally to see current state after other WPs land
- T024-T025: Only test critical paths (status, mission detection, dashboard API). Do NOT write tests for migrations, CLI scaffolding, or tracker code just to hit a number.
- T026: Replace single `--fail-under=80` with two steps:
  1. Enforced: `--fail-under=90 --include src/specify_cli/status/* --include src/specify_cli/core/mission_detection.py --include src/specify_cli/dashboard/handlers/* --include src/specify_cli/dashboard/scanner.py --include src/specify_cli/merge/* --include src/specify_cli/next/*`
  2. Advisory: no `--fail-under`, `|| true` to prevent failure

### Parallel Opportunities

- T024 and T025 can proceed in parallel once T023 identifies gaps.

### Dependencies

- Depends on WP01, WP02, WP03, WP04, WP05, WP06 (needs all fixes in place to measure accurately).

### Risks & Mitigations

- `diff-cover --include` flag syntax may not support glob patterns → test locally first; fall back to explicit file list
- CI flat coverage gate may still fail even after split → the advisory step uses `|| true` so it won't block

---

## Work Package WP08: Architectural Fitness Review (Priority: P3)

**Goal**: Architect reviews the branch direction and validates test patterns align with doctrine package vision.
**Independent Test**: Architect produces a review verdict (approve/request-changes) with documented rationale.
**Prompt**: `tasks/WP08-architectural-fitness-review.md`
**Requirement Refs**: FR-007

### Included Subtasks

- [ ] T028 Review path convention consistency across all fixed test files
- [ ] T029 Evaluate dashboard JS backward-compat approach (`data.missions || data.features`)
- [ ] T030 Grep for remaining `feature_dir` / `feature` → `mission_dir` / `mission` rename gaps
- [ ] T031 Produce review verdict with follow-up items

### Implementation Notes

- This is a review WP, not implementation. The architect reads the changes from WP01-07 and validates architectural alignment.
- Key questions: Are tests using `MissionTemplateRepository` consistently? Should the JS backward-compat be a clean break? Are there other rename gaps?

### Parallel Opportunities

- None — sequential review.

### Dependencies

- Depends on WP07 (all implementation must be complete before review).

### Risks & Mitigations

- Architect may find systemic issues requiring additional WPs → document as follow-up missions, don't expand scope of 062

---

## Dependency & Execution Summary

```
Wave 1 (parallel): WP01, WP02, WP03, WP04, WP05
Wave 2 (after WP05): WP06
Wave 3 (after all): WP07
Wave 4 (after WP07): WP08
```

- **Parallelization**: WP01-05 are fully independent — 5 agents can work simultaneously
- **MVP Scope**: WP01-05 (fixes all CI failures). WP06-08 are hardening and review.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP02 |
| FR-003 | WP03 |
| FR-004 | WP03 |
| FR-005 | WP04 |
| FR-006 | WP07 |
| FR-007 | WP08 |
| FR-008 | WP05 |
| FR-009 | WP05 |
| FR-010 | WP06 |
| NFR-001 | WP01-05 |
| NFR-002 | WP07 |
| NFR-003 | WP01-06 |
| C-001 | All (test-only except WP05 dashboard fixes, WP07 CI config) |
| C-002 | WP01 (uses MissionTemplateRepository) |
| C-003 | All |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Fix test_mission_software_dev_integration.py path | WP01 | P1 | Yes |
| T002 | Fix test_documentation_mission.py path | WP01 | P1 | Yes |
| T003 | Fix test_documentation_templates.py path | WP01 | P1 | Yes |
| T004 | Fix test_command_template_cleanliness.py path | WP01 | P1 | Yes |
| T005 | Verify WP01 tests pass | WP01 | P1 | No |
| T006 | Fix test_emitter_origin.py aggregate_type | WP02 | P1 | Yes |
| T007 | Fix test_feature_lifecycle_unit.py param name | WP02 | P1 | Yes |
| T008 | Verify WP02 tests pass | WP02 | P1 | No |
| T009 | Fix test_worktree_topology.py mock target | WP03 | P1 | Yes |
| T010 | Fix test_workflow_profile_injection.py _proposed/ | WP03 | P1 | Yes |
| T011 | Fix test_feature_detection_integration.py imports | WP03 | P1 | Yes |
| T012 | Verify WP03 tests pass | WP03 | P1 | No |
| T013 | Investigate m_0_12_0 migration behavior | WP04 | P1 | No |
| T014 | Fix test or migration for command-templates/ | WP04 | P1 | No |
| T015 | Verify WP04 test passes | WP04 | P1 | No |
| T016 | Verify scanner.py NameError fix | WP05 | P1 | Yes |
| T017 | Verify dashboard.js key mismatch fix | WP05 | P1 | Yes |
| T018 | Verify dashboard loads missions | WP05 | P1 | No |
| T019 | Extract response keys from Python handler | WP06 | P2 | No |
| T020 | Create test_api_contract.py | WP06 | P2 | No |
| T021 | Add kanban/constitution endpoint tests | WP06 | P2 | No |
| T022 | Verify contract test catches original bug | WP06 | P2 | No |
| T023 | Measure diff-coverage after WP01-06 | WP07 | P2 | No |
| T024 | Write tests for dashboard handlers critical paths | WP07 | P2 | Yes |
| T025 | Write tests for mission_detection.py uncovered lines | WP07 | P2 | Yes |
| T026 | Split CI diff-cover into enforced + advisory | WP07 | P2 | No |
| T027 | Verify CI workflow config validity | WP07 | P2 | No |
| T028 | Review path convention consistency | WP08 | P3 | No |
| T029 | Evaluate JS backward-compat approach | WP08 | P3 | No |
| T030 | Grep for remaining feature→mission renames | WP08 | P3 | No |
| T031 | Produce review verdict | WP08 | P3 | No |
