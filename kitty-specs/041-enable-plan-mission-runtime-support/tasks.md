# Work Packages: Enable Plan Mission Runtime Support on 2.x

**Feature**: 041-enable-plan-mission-runtime-support
**Branch**: 2.x
**Created**: 2026-02-22
**Total Work Packages**: 5
**Total Subtasks**: 19

---

## Overview

The plan mission system currently blocks the runtime loop because it lacks:
1. Runtime schema (mission-runtime.yaml)
2. Mission-scoped command templates (4 steps)
3. Comprehensive tests

This feature is organized into 5 focused work packages, organized by phase:
- **Phase 1**: Foundation (WP01) - Runtime schema setup
- **Phase 2**: Mission Templates (WP02) - Command templates for all 4 steps
- **Phase 3**: Support (WP03) - Content templates and test setup
- **Phase 4**: Testing (WP04) - Integration, resolution, and regression tests
- **Phase 5**: Finalization (WP05) - Dependency parsing and commit

---

## Work Package Breakdown

### WP01: Runtime Schema Foundation
**Priority**: P0 (blocking)
**Dependencies**: None
**Estimated Size**: 4 subtasks, ~280 lines
**Status**: Planned

**Goal**: Create the runtime schema that enables the runtime bridge to discover and load the plan mission.

**Included Subtasks**:
- [x] T001: Study existing mission-runtime.yaml patterns
- [x] T002: Create mission-runtime.yaml with 4-step schema
- [x] T003: Validate against runtime bridge expectations
- [x] T016: Create directory structure

**Implementation Sketch**:
1. Examine software-dev and research mission runtime definitions
2. Create plan mission-runtime.yaml following the same schema
3. Define 4 sequential steps (specify → research → plan → review)
4. Ensure directories exist for command templates and content templates

**Parallel Opportunities**: None (foundational)

**Risks**:
- Schema incompatibility with runtime bridge
- Mitigation: Follow existing patterns exactly

**Definition of Done**:
- mission-runtime.yaml created at correct path
- Schema validates (4 steps, linear sequence, terminal step defined)
- Directories created and ready for templates
- No broken references to runtime bridge

---

### WP02: All Command Templates
**Priority**: P0
**Dependencies**: WP01 (directories must exist)
**Estimated Size**: 6 subtasks, ~420 lines
**Status**: Planned
**Parallelization**: [P] Templates can be created in parallel after WP01 is done

**Goal**: Create 4 mission-scoped command templates that guide agents through the planning workflow.

**Included Subtasks**:
- [x] T004: Create specify.md (step 1 - feature definition)
- [x] T005: Create research.md (step 2 - research gathering)
- [x] T006: Create plan.md (step 3 - design artifacts)
- [x] T007: Create review.md (step 4 - final validation)
- [x] T008: Validate all templates for completeness
- [x] T009: Analyze for content template references

**Implementation Sketch**:
1. Create specify.md with entry point context, deliverables, instructions
2. Create research.md with research phase guidance
3. Create plan.md with design artifact generation
4. Create review.md with validation criteria
5. Each template follows Markdown + YAML frontmatter structure
6. Scan for any references to content templates (../templates/...)

**Parallel Opportunities**: [P] All 4 templates can be created in parallel after WP01

**Risks**:
- Inconsistent template structure between files
- Missing content template references detected too late
- Mitigation: Validate all templates before moving to WP03

**Definition of Done**:
- All 4 template files created at correct paths
- Frontmatter YAML parses correctly
- All required sections present (Context, Deliverables, Instructions, Success Criteria)
- No broken references to other files
- Content template references identified

---

### WP03: Content Templates & Test Setup
**Priority**: P1
**Dependencies**: WP02 (need to know what templates are referenced)
**Estimated Size**: 3 subtasks, ~260 lines
**Status**: Planned

**Goal**: Create any referenced content templates and set up the test framework.

**Included Subtasks**:
- [x] T010: Create any referenced content templates
- [x] T011: Create test file (test_plan_mission_runtime.py)
- [x] T012: Set up test fixtures and mocks

**Implementation Sketch**:
1. Review content template references from WP02 T009
2. Create any referenced templates (e.g., research-outline.md, design-checklist.md)
3. Create tests/specify_cli/next/test_plan_mission_runtime.py
4. Set up pytest fixtures: temp_project, plan_feature, mock_runtime_bridge
5. Create reusable mocks for runtime bridge and command resolver

**Parallel Opportunities**: None (must wait for WP02)

**Risks**:
- Content templates missing if references analyzed incorrectly
- Test fixtures may not work with real runtime bridge
- Mitigation: Unit test fixtures before writing integration tests

**Definition of Done**:
- Content templates created (if any referenced)
- Test file created with proper structure
- Fixtures and mocks functional
- Test file imports correctly (no syntax errors)
- Ready for test implementation (WP04)

---

### WP04: Integration & Regression Tests
**Priority**: P0
**Dependencies**: WP03 (test setup required)
**Estimated Size**: 5 subtasks, ~380 lines
**Status**: Planned

**Goal**: Comprehensive testing to ensure plan mission works end-to-end and other missions remain unaffected.

**Included Subtasks**:
- [x] T013: Implement mission discovery integration test
- [x] T014: Implement command resolution tests (all 4 steps)
- [x] T015: Implement regression tests (software-dev, research)
- [ ] T016: Verify test coverage and CI compatibility (UPDATED: was T016, renamed)
- [ ] T017: Run tests locally and verify all pass

**Implementation Sketch**:

**T013 - Mission Discovery Integration**:
- Create feature with mission=plan
- Call `spec-kitty next --feature <slug>`
- Verify return status is not blocked
- Assert no "Mission 'plan' not found" error

**T014 - Command Resolution Tests**:
- Test resolver for each step: specify, research, plan, review
- Load each template file
- Verify YAML frontmatter parses
- Verify all required sections present
- Check for missing references

**T015 - Regression Tests**:
- Run existing software-dev mission tests
- Run existing research mission tests
- Verify no broken functionality
- Ensure backward compatibility

**T016 - Coverage & CI**:
- Generate coverage report
- Verify deterministic test execution (no timing deps, no random data)
- Test with pytest headless flags
- Ensure isolation (no cross-test contamination)

**T017 - Local Verification**:
- Run full test suite locally: `pytest tests/specify_cli/next/test_plan_mission_runtime.py -v`
- Verify all pass (100% pass rate)
- Check coverage metrics (target: >85%)
- Verify no external dependencies or network calls

**Parallel Opportunities**: [P] Integration tests can run in parallel with regression tests

**Risks**:
- Tests may have timing-dependent assertions
- Cross-test contamination in fixtures
- Regression tests fail due to other changes
- Mitigation: Use deterministic data, isolated fixtures, mock external calls

**Definition of Done**:
- All test classes implemented (Integration, Resolution, Regression)
- 100% test pass rate locally
- Coverage >85%
- No external service dependencies
- No timing-dependent assertions
- All tests deterministic and repeatable
- Ready for finalization

---

### WP05: Finalization & Commit
**Priority**: P0 (blocking release)
**Dependencies**: WP04 (all tests must pass)
**Estimated Size**: 1 subtask, ~50 lines
**Status**: Planned

**Goal**: Parse dependencies and commit all work to the 2.x branch.

**Included Subtasks**:
- [ ] T018: Run finalize-tasks command and verify commit

**Implementation Sketch**:
1. Run `spec-kitty agent feature finalize-tasks --json`
2. Verify JSON output: "commit_created": true
3. Capture commit hash
4. Verify all WP files in tasks/ directory
5. Verify frontmatter has dependencies field populated
6. Verify no cycles in dependency graph
7. Confirm commit was pushed to 2.x branch (if applicable)

**Parallel Opportunities**: None (final step)

**Risks**:
- Dependencies not parsed correctly
- Commit fails due to untracked files
- Dependency cycle detected (would block)
- Mitigation: Verify JSON output carefully

**Definition of Done**:
- `spec-kitty agent feature finalize-tasks` succeeds
- JSON output shows commit_created: true
- All WP frontmatter updated with dependencies
- Git log shows new commit on 2.x
- Feature ready for implementation (`spec-kitty implement WP01`)

---

## Phase Dependencies

```
WP01: Foundation
  ↓ (must complete first)
WP02: Templates
  ↓ (templates must exist)
WP03: Test Setup
  ↓ (test framework ready)
WP04: Tests
  ↓ (tests passing)
WP05: Finalization
  ↓ (commit to 2.x)
Ready for Implementation
```

---

## MVP Scope Recommendation

**Minimum Viable Product**: WP01 + WP02 + WP04 (Minimal Tests)
- Core functionality (schema + templates) working
- Basic integration test passing
- No full test suite

**Recommended Scope**: WP01 + WP02 + WP03 + WP04 (Full)
- Complete implementation with comprehensive testing
- Content templates included
- Regression tests ensure no breakage
- Recommended for merge to 2.x

**Extended Scope**: All 5 WPs
- Full implementation with finalization
- All tests passing
- Committed to 2.x branch
- Ready for agent implementation

---

## Size Distribution

| WP | Subtasks | Est. Lines | Status |
|----|----------|-----------|--------|
| WP01 | 4 | 280 | ✓ Planned |
| WP02 | 6 | 420 | ✓ Planned |
| WP03 | 3 | 260 | ✓ Planned |
| WP04 | 5 | 380 | ✓ Planned |
| WP05 | 1 | 50 | ✓ Planned |
| **Total** | **19** | **~1390** | - |

**Assessment**:
- ✓ All WPs within ideal range (200-500 lines)
- ✓ All WPs have 1-6 subtasks (target: 3-7, max: 10)
- ✓ No WP exceeds 700 lines (max safe for agents)
- ✓ Balanced distribution of work across phases

---

## Parallelization Opportunities

**Sequential Critical Path** (required order):
1. WP01 (foundation - 4 subtasks)
2. WP02 (templates - 6 subtasks)
3. WP03 (test setup - 3 subtasks)
4. WP04 (tests - 5 subtasks)
5. WP05 (finalization - 1 subtask)

**Parallel Opportunities** (after critical path):
- [P] WP02 templates can be created in parallel (once WP01 directories exist)
- [P] WP04 integration tests can run in parallel with regression tests

**Estimated Timeline**:
- Sequential: ~5 agents × 1-2 hours each = 5-10 hours
- With parallelization: 3-4 agents in parallel = 3-5 hours

---

## Risk Summary

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Schema incompatibility with runtime bridge | HIGH | Follow existing patterns exactly (software-dev, research) |
| Content templates missing or incomplete | MEDIUM | Analyze references thoroughly before creating |
| Tests fail due to external dependencies | MEDIUM | Mock all external services, use deterministic data |
| Regression in other missions | HIGH | Comprehensive regression tests in WP04 |
| 2.x path conflicts | MEDIUM | Keep all paths local to missions/plan/, no doctrine paths |

---

## Notes for Implementers

1. **2.x Branch Only**: All changes must be on the 2.x branch. No mainline changes.

2. **Reference Patterns**: Follow software-dev and research mission structures exactly. Don't invent new patterns.

3. **Testing is Critical**: WP04 is not optional. Comprehensive testing ensures no regressions.

4. **Content Templates**: Only create if explicitly referenced by command templates. Don't create generic templates.

5. **Deterministic Tests**: No timing dependencies, no random data, no external service calls. Tests must pass consistently in CI.

6. **Path Safety**: All paths must be 2.x-compatible. No doctrine paths, no mainline paths.

---

## Next Steps After Task Generation

1. **Review**: Verify all WP prompt files generated correctly
2. **Estimate**: Each agent should review estimated time before starting
3. **Implement**: Agents implement WPs in sequence: WP01 → WP02 → WP03 → WP04 → WP05
4. **Test**: After WP04, run full test suite locally
5. **Finalize**: WP05 commits all work to 2.x branch
6. **Review**: Code review of all artifacts
7. **Merge**: Merge to 2.x when tests pass

---

## Prompt File References

Individual work package prompts are generated in `tasks/` directory:
- `WP01-runtime-schema-foundation.md` - Runtime schema setup
- `WP02-command-templates.md` - All 4 step templates
- `WP03-content-test-setup.md` - Supporting templates and test framework
- `WP04-integration-regression-tests.md` - Comprehensive test suite
- `WP05-finalization-commit.md` - Finalization and commit

Each prompt includes detailed implementation guidance, code examples, test cases, and success criteria.
