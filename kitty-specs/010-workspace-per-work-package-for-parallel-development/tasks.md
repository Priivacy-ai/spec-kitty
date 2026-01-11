# Work Packages: Workspace-per-Work-Package for Parallel Development

**Feature**: 010-workspace-per-work-package-for-parallel-development
**Inputs**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md)

**Organization**: This feature follows TDD approach - tests written first, then implementation. Work packages are sequenced: Test infrastructure → Core utilities → Command modifications → Template updates → Integration validation.

**Prompt Files**: Each work package references a matching prompt file in `tasks/` directory. Lane status tracked in YAML frontmatter (`lane: planned|doing|for_review|done`).

---

## Work Package WP01: Dependency Graph Utilities (TDD Foundation) (Priority: P0)

**Goal**: Create dependency_graph.py module with parsing, cycle detection, and validation utilities. Write comprehensive unit tests FIRST per TDD mandate.
**Independent Test**: All dependency graph unit tests pass (cycle detection, validation, parsing).
**Prompt**: `tasks/WP01-dependency-graph-utilities-tdd-foundation.md`

### Included Subtasks
- [ ] T001 Write unit tests for dependency parsing (parse_wp_dependencies)
- [ ] T002 Write unit tests for graph building (build_dependency_graph)
- [ ] T003 Write unit tests for cycle detection (detect_cycles) - various graph shapes
- [ ] T004 Write unit tests for dependency validation (validate_dependencies)
- [ ] T005 Write unit tests for dependent lookup (get_dependents)
- [ ] T006 Implement src/specify_cli/core/dependency_graph.py module to pass tests
- [ ] T007 Verify >90% test coverage for dependency_graph.py

### Implementation Notes
1. Tests first (T001-T005) - all should FAIL initially
2. Implement dependency_graph.py (T006) to make tests pass
3. Use DFS algorithm for cycle detection (O(V+E) complexity)
4. YAML frontmatter parsing with ruamel.yaml (existing dependency)

### Parallel Opportunities
- Tests T001-T005 can be written in parallel (different test functions)

### Dependencies
- None (foundation work package)

### Risks & Mitigations
- **Risk**: Cycle detection algorithm incorrect → false positives/negatives
- **Mitigation**: Comprehensive test cases covering all graph shapes (no cycles, simple cycle, complex DAG)

---

## Work Package WP02: Migration Tests (TDD - Template Source Validation) (Priority: P0)

**Goal**: Write migration tests that verify template SOURCE files are updated for workspace-per-WP workflow. Tests must FAIL initially to ensure WP07 updates templates correctly.
**Independent Test**: Migration test suite runs, fails on missing template updates, validates template source content.
**Prompt**: `tasks/WP02-migration-tests-tdd-agent-template-coverage.md`

### Included Subtasks
- [ ] T008 Create test_workspace_per_wp_migration.py in tests/specify_cli/
- [ ] T009 Write test for template directory existence
- [ ] T010 Write test for specify.md template updates (no worktree creation)
- [ ] T011 Write test for plan.md template updates (no worktree reference)
- [ ] T012 Write test for tasks.md template updates (dependency generation)
- [ ] T013 Write test for implement.md template existence and --base flag docs
- [ ] T015 Run tests - verify tests FAIL (templates not yet updated)

### Implementation Notes
- Test 4 template SOURCE files in `.kittify/missions/software-dev/command-templates/`
- Agent directories (`.claude/`, `.gemini/`, etc.) are gitignored, generated from templates
- Migration (WP07) updates template sources, not individual agent files
- Users get updated agent files after upgrade when they run `spec-kitty init`

### Parallel Opportunities
- Tests T009-T013 can be written in parallel (different test functions)

### Dependencies
- Depends on WP01 (foundational testing patterns)

### Risks & Mitigations
- **Risk**: Template updates don't propagate to generated agent files
- **Mitigation**: Migration guide instructs users to regenerate agent assets OR migration auto-regenerates

---

## Work Package WP03: Frontmatter Schema Extension (Priority: P0)

**Goal**: Add `dependencies: []` field to WP frontmatter schema, update WP_FIELD_ORDER, ensure backward compatibility with existing WPs.
**Independent Test**: WP files with and without dependencies field parse correctly.
**Prompt**: `tasks/WP03-frontmatter-schema-extension.md`

### Included Subtasks
- [ ] T016 Update WP frontmatter schema in src/specify_cli/frontmatter.py
- [ ] T017 Add dependencies field (optional, defaults to empty list)
- [ ] T018 Update WP_FIELD_ORDER to include dependencies after lane
- [ ] T019 Add validation: dependencies must be list of strings matching WP## pattern
- [ ] T020 Test frontmatter parsing with dependencies field
- [ ] T021 Test backward compatibility (WPs without dependencies field still parse)

### Implementation Notes
- Insert dependencies field in logical location (after lane, before subtasks)
- Default value: [] (empty list) if field missing
- Validation regex: `WP\d{2}` pattern

### Parallel Opportunities
- None (single file modification)

### Dependencies
- Depends on WP01 (uses dependency validation utilities)

### Risks & Mitigations
- **Risk**: Breaking existing WP files that lack dependencies field
- **Mitigation**: Make field optional with default value, test backward compatibility

---

## Work Package WP04: Planning Workflow Refactoring (Priority: P1)

**Goal**: Modify specify, plan, tasks commands to work in main repository and commit directly without creating worktrees.
**Independent Test**: Run specify → plan → tasks workflow, verify artifacts in main, verify NO worktrees created.
**Prompt**: `tasks/WP04-planning-workflow-refactoring.md`

### Included Subtasks
- [ ] T022 Modify src/specify_cli/cli/commands/agent/feature.py - remove worktree creation from create-feature
- [ ] T023 Update feature creation to work in main repo (create kitty-specs/###-feature/ directly)
- [ ] T024 Add git commit after spec.md creation (auto-commit to main)
- [ ] T025 Verify plan command works in main (no worktree context required)
- [ ] T026 Add git commit after plan.md creation
- [ ] T027 Modify src/specify_cli/cli/commands/agent/tasks.py - parse dependencies from tasks.md
- [ ] T028 Generate dependencies field in WP frontmatter during tasks generation
- [ ] T029 Add git commit after tasks/*.md creation
- [ ] T030 Write integration test for planning workflow (specify → plan → tasks, no worktrees)

### Implementation Notes
1. feature.py: Remove create_feature_worktree() call
2. After creating spec.md, run: git add kitty-specs/###-feature/spec.md && git commit -m "Add spec for feature ###"
3. tasks.py: Parse tasks.md structure, detect dependencies, write to frontmatter

### Parallel Opportunities
- Specify and plan command changes (T022-T026) can be implemented in parallel with tasks command changes (T027-T029)

### Dependencies
- Depends on WP01 (uses dependency_graph utilities)
- Depends on WP03 (uses extended frontmatter schema)

### Risks & Mitigations
- **Risk**: Auto-commit fails → leaves main in dirty state
- **Mitigation**: Validate clean state before commit, provide clear error if commit fails

---

## Work Package WP05: Implement Command (NEW) (Priority: P1)

**Goal**: Create new `spec-kitty implement WP##` command with --base flag for dependency-aware workspace creation.
**Independent Test**: Run implement WP01 (creates workspace from main), run implement WP02 --base WP01 (creates workspace from WP01 branch).
**Prompt**: `tasks/WP05-implement-command-new.md`

### Included Subtasks
- [ ] T031 Create src/specify_cli/cli/commands/implement.py module
- [ ] T032 Implement workspace creation logic (git worktree add with proper branching)
- [ ] T033 Add --base WPXX parameter with validation (base workspace must exist)
- [ ] T034 Parse WP frontmatter to get dependencies, suggest --base if missing
- [ ] T035 Detect feature number and slug from current directory or git branch
- [ ] T036 Create workspace naming: .worktrees/###-feature-WP##/
- [ ] T037 Branch naming: ###-feature-WP## (for no deps) or branch from base (for deps)
- [ ] T038 Add StepTracker progress display (detect, validate, create, setup)
- [ ] T039 Register implement command in CLI router
- [ ] T040 Write unit tests for implement command (mocked git operations)

### Implementation Notes
- Command signature: `implement(wp_id: str, base: str = None)`
- Git commands:
  - No deps: `git worktree add .worktrees/010-feature-WP01 -b 010-feature-WP01`
  - With deps: `git worktree add .worktrees/010-feature-WP02 -b 010-feature-WP02 010-feature-WP01`
- Validation order: WP exists → dependencies match --base → base workspace exists → create

### Parallel Opportunities
- Can be implemented in parallel with WP04 (different files)

### Dependencies
- Depends on WP01 (uses dependency_graph for validation)
- Depends on WP03 (reads dependencies from frontmatter)

### Risks & Mitigations
- **Risk**: Base workspace validation fails silently → creates workspace with wrong base
- **Mitigation**: Explicit validation with clear error messages, test all error paths

---

## Work Package WP06: Merge Command Updates (Priority: P1)

**Goal**: Modify merge command to handle workspace-per-WP structure - validate all WP worktrees before merging, merge entire feature.
**Independent Test**: Create feature with 3 WP workspaces, merge feature, verify all WP branches merged.
**Prompt**: `tasks/WP06-merge-command-updates.md`

### Included Subtasks
- [ ] T041 Update src/specify_cli/cli/commands/merge.py - detect workspace-per-WP structure
- [ ] T042 Scan .worktrees/ for ###-feature-WP## pattern (multiple worktrees)
- [ ] T043 Validate all WP branches exist and are ready for merge
- [ ] T044 Merge all WP branches to main (iterate over WP01, WP02, WP03...)
- [ ] T045 Add cleanup logic: remove all WP worktrees after merge (if --remove-worktree flag)
- [ ] T046 Delete all WP branches after merge (if --delete-branch flag)
- [ ] T047 Update help text to document workspace-per-WP merge behavior
- [ ] T048 Write integration test for merge with workspace-per-WP

### Implementation Notes
- Detection: Check if .worktrees contains ###-feature-WP## directories (multiple)
- Merge order: Iterate WP01, WP02, WP03... (alphabetical by WP ID)
- Each WP branch merges independently to main
- Final result: All WPs integrated into main as separate commits

### Parallel Opportunities
- None (merge is sequential operation)

### Dependencies
- Depends on WP05 (implement command creates WP workspaces that merge validates)

### Risks & Mitigations
- **Risk**: Partial merge failure leaves some WPs merged, others not
- **Mitigation**: Dry-run mode, validate all WPs before starting merge

---

## Work Package WP07: Migration Implementation (Priority: P1)

**Goal**: Implement m_0_11_0_workspace_per_wp.py migration with pre-upgrade validation and template source updates. Make migration tests (WP02) pass.
**Independent Test**: Migration tests (WP02) pass - all 4 template sources validated as updated.
**Prompt**: `tasks/WP07-migration-implementation.md`

### Included Subtasks
- [ ] T049 Create src/specify_cli/upgrade/migrations/m_0_11_0_workspace_per_wp.py
- [ ] T050 Implement pre-upgrade validation (scan for legacy worktrees)
- [ ] T051 Implement legacy worktree detection (.worktrees/###-feature/ pattern)
- [ ] T052 Block upgrade if legacy worktrees found, provide clear error with cleanup guidance
- [ ] T053 Update .kittify/missions/software-dev/command-templates/specify.md - remove worktree creation
- [ ] T054 Update .kittify/missions/software-dev/command-templates/plan.md - remove worktree references
- [ ] T055 Update .kittify/missions/software-dev/command-templates/tasks.md - add dependency generation
- [ ] T056 Create .kittify/missions/software-dev/command-templates/implement.md - NEW template
- [ ] T057 Run migration tests (WP02) - verify all tests PASS
- [ ] T058 Add list-legacy-features utility command for pre-upgrade cleanup

### Implementation Notes
- **CORRECTED SCOPE**: Update 4 template SOURCE files (not 48 agent files)
- Template location: `.kittify/missions/software-dev/command-templates/`
- Agent directories (`.claude/`, `.gemini/`, etc.) are gitignored, generated from templates
- After migration, users regenerate agent files via `spec-kitty init` or migration auto-regenerates
- Template changes:
  - specify.md: Remove worktree creation, add commit to main workflow
  - plan.md: Remove worktree navigation, work in main repo
  - tasks.md: Add dependency parsing and frontmatter generation
  - implement.md: NEW template documenting spec-kitty implement WP## [--base WP##]

### Parallel Opportunities
- Template updates (T053-T056) can run in parallel (different files)
- Modest parallelization: 4 templates (reduced from original 48-file scope)

### Dependencies
- Depends on WP02 (migration tests exist to validate against)

### Risks & Mitigations
- **Risk**: Missing template update → broken workflow for all agents
- **Mitigation**: Migration tests validate all 4 template sources updated

---

## Work Package WP08: Integration Tests (Full Workflow Validation) (Priority: P2)

**Goal**: Write and validate integration tests for complete workflow: specify → plan → tasks → implement with dependencies.
**Independent Test**: Integration test suite passes, covering happy path and error cases.
**Prompt**: `tasks/WP08-integration-tests-full-workflow-validation.md`

### Included Subtasks
- [ ] T070 Create tests/specify_cli/test_integration/test_workspace_per_wp_workflow.py
- [ ] T071 Write test: specify → plan → tasks in main (no worktrees created)
- [ ] T072 Write test: implement WP01 creates workspace from main
- [ ] T073 Write test: implement WP02 --base WP01 creates workspace from WP01 branch
- [ ] T074 Write test: parallel implementation (WP01, WP03 simultaneously)
- [ ] T075 Write test: dependency validation errors (missing base, circular deps)
- [ ] T076 Write test: merge with workspace-per-WP (all WP branches merged)
- [ ] T077 Write test: pre-upgrade validation blocks if legacy worktrees exist
- [ ] T078 Run full integration test suite - verify all pass

### Implementation Notes
- Use pytest tmp_path fixture for isolated test environments
- Test actual git operations (not mocked) in temp repos
- Cover both happy paths and error cases
- Validate filesystem state (worktrees created, commits to main)

### Parallel Opportunities
- Tests T071-T077 can be written in parallel (different test functions)

### Dependencies
- Depends on WP01 (dependency graph utilities implemented)
- Depends on WP03 (frontmatter schema extended)
- Depends on WP04 (planning workflow refactored)
- Depends on WP05 (implement command exists)
- Depends on WP06 (merge command updated)
- Depends on WP07 (migration implemented)

### Risks & Mitigations
- **Risk**: Integration tests don't catch real-world workflow issues
- **Mitigation**: Test on actual Spec Kitty codebase (dogfooding), cover error paths thoroughly

---

## Work Package WP09: Review Feedback Warning System (Priority: P2)

**Goal**: Add warnings to implement and review prompts when dependent WPs need rebase after parent WP changes.
**Independent Test**: Modify WP01 while WP02 (dependent) is in progress, verify warnings displayed.
**Prompt**: `tasks/WP09-review-feedback-warning-system.md`

### Included Subtasks
- [ ] T079 Add dependent WP detection to implement command (query dependency_graph)
- [ ] T080 Display warning when resuming WP whose base has changed (git log comparison)
- [ ] T081 Include rebase command in warning: cd .worktrees/###-feature-WP## && git rebase ###-feature-WPXX
- [ ] T082 Add dependent WP warnings to review command/prompts
- [ ] T083 Display warning when reviewing WP that has dependents in progress (lanes: planned, doing)
- [ ] T084 Update WP prompt templates to include dependency rebase guidance
- [ ] T085 Test warning display logic (various dependency scenarios)

### Implementation Notes
- Use get_dependents() from dependency_graph.py
- Check WP lane status to determine if dependents are in progress
- Warning format: "⚠️ WP02, WP03 depend on WP01. If changes requested, they'll need manual rebase."
- Include specific git command for rebase

### Parallel Opportunities
- Implement command warnings (T079-T081) and review command warnings (T082-T083) can be done in parallel

### Dependencies
- Depends on WP01 (uses get_dependents() function)
- Depends on WP03 (reads dependencies from frontmatter)
- Depends on WP05 (modifies implement command)

### Risks & Mitigations
- **Risk**: Warning not displayed → users forget to rebase, work on stale code
- **Mitigation**: Prominent warning display (Rich formatting), include in multiple places (implement, review)

---

## Work Package WP10: Documentation and Migration Guide (Priority: P3)

**Goal**: Document workspace-per-WP workflow, create upgrade guide, update README with breaking change notes.
**Independent Test**: User can follow migration guide to upgrade from 0.10.x to 0.11.0 successfully.
**Prompt**: `tasks/WP10-documentation-and-migration-guide.md`

### Included Subtasks
- [ ] T086 Create docs/workspace-per-wp.md - explain new workflow with examples
- [ ] T087 Create docs/upgrading-to-0-11-0.md - step-by-step migration guide
- [ ] T088 Document pre-upgrade checklist (check for legacy worktrees, merge or delete)
- [ ] T089 Document dependency syntax in WP frontmatter
- [ ] T090 Update README.md with 0.11.0 breaking change notes
- [ ] T091 Update CHANGELOG.md with 0.11.0 entry (breaking changes, new features)
- [ ] T092 Add examples to quickstart.md (already exists, expand with real scenarios)
- [ ] T093 Update CLAUDE.md development guidelines with workspace-per-WP patterns

### Implementation Notes
- Migration guide critical path: list worktrees → merge or delete → upgrade → verify
- Emphasize: Breaking change, no automatic migration, irreversible upgrade
- Include rollback (downgrade to 0.10.12) instructions

### Parallel Opportunities
- All documentation tasks (T086-T093) can be written in parallel (different files)

### Dependencies
- Depends on all previous WPs (documents complete system)

### Risks & Mitigations
- **Risk**: Incomplete migration guide → users stuck during upgrade
- **Mitigation**: Test migration guide on real project (spec-kitty itself), peer review documentation

---

## Dependency & Execution Summary

**Dependency Chain:**
```
WP01 (Dependency Graph) ─┬─→ WP02 (Migration Tests)
                         ├─→ WP03 (Frontmatter) ─┬─→ WP04 (Planning Workflow) ─→ WP08 (Integration Tests) ─→ WP10 (Docs)
                         │                       ├─→ WP05 (Implement Command) ─┘
                         │                       └─→ WP09 (Review Warnings) ───┘
                         └─→ WP06 (Merge Updates) ─────────────────────────────┘
                         └─→ WP07 (Migration Impl) depends on WP02 ──────────────┘
```

**Parallelization Strategy:**
- **Wave 1**: WP01 only (foundation)
- **Wave 2**: WP02, WP03, WP06 in parallel (independent)
- **Wave 3**: WP04, WP05, WP07 in parallel (all need WP01, WP03; WP07 needs WP02)
- **Wave 4**: WP09 in parallel with WP08 start
- **Wave 5**: WP08 completes (validates everything), then WP10 (final docs)

**MVP Scope**: WP01-WP07 constitute the minimal viable release. WP08 (integration tests) and WP09 (warnings) are quality enhancements. WP10 (docs) is required for release but not for functionality.

**Critical Path**: WP01 → WP03 → WP04 → WP08 (longest dependency chain)

**Estimated Completion**: With 3 agents working in parallel:
- Wave 1: 1 WP (WP01)
- Wave 2: 3 WPs parallel (WP02, WP03, WP06)
- Wave 3: 3 WPs parallel (WP04, WP05, WP07)
- Wave 4: 2 WPs parallel (WP08, WP09)
- Wave 5: 1 WP (WP10)

**Total**: 10 work packages, ~5 waves with parallelization

---

## Subtask Index (Reference)

### Phase 0: Test Infrastructure (T001-T021)
- T001-T007: Dependency graph tests and implementation (WP01)
- T008-T013, T015: Migration tests for template source validation (WP02) - 6 subtasks
- T016-T021: Frontmatter schema extension (WP03)

**Note**: T014 removed from WP02 (pre-upgrade validation testing moved to WP07)

### Phase 1: Core Implementation (T022-T048)
- T022-T030: Planning workflow refactoring (WP04)
- T031-T040: Implement command creation (WP05)
- T041-T048: Merge command updates (WP06)

### Phase 2: Migration & Templates (T049-T058)
- T049-T058: Migration implementation and template source updates (WP07) - 10 subtasks
- T059-T069: REMOVED (original WP07 had agent directory updates, corrected to template sources only)

### Phase 3: Quality & Polish (T070-T093)
- T070-T078: Integration tests (WP08)
- T079-T085: Review feedback warnings (WP09)
- T086-T093: Documentation and migration guide (WP10)

**Total Subtasks**: 80 (reduced from 93)

**Scope Corrections**:
- WP02: 8 → 6 subtasks (removed T014, test template sources not agent dirs)
- WP07: 21 → 10 subtasks (update 4 template sources, not 48 agent files)

---

## Test Coverage Goals

- **Unit tests**: dependency_graph.py (>90% coverage)
- **Migration tests**: All 12 agent templates validated (100% coverage of agents)
- **Integration tests**: Full workflows covered (specify → implement → merge)
- **Overall**: >85% coverage for modified code

---

## Success Metrics

- ✅ All migration tests pass (4 template sources validated)
- ✅ All dependency graph tests pass (cycle detection, validation)
- ✅ Integration tests pass (specify in main, implement creates worktrees)
- ✅ Pre-upgrade validation blocks legacy worktrees (100% of attempts)
- ✅ Parallel WP development validated (3 agents on different WPs simultaneously)
- ✅ Documentation complete (migration guide enables self-service upgrade)

---

## Next Steps

Run `/spec-kitty.implement WP01` to begin implementation following TDD approach (tests first!).
