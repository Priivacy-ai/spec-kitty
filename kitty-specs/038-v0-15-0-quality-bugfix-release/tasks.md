# Work Package Breakdown: v0.15.0 Quality Bugfix Release

**Feature**: 038-v0-15-0-quality-bugfix-release
**Created**: 2026-02-11
**Total Subtasks**: 63
**Total Work Packages**: 10

## Subtask Inventory

### Setup & Tracking (WP01)
- **T001**: Create GitHub milestone "0.15.0 - 1.x Quality Bugfixes"
- **T002**: Create tracking issue linking all 7 bug reports
- **T003**: Add acceptance checklist to tracking issue
- **T004**: Verify all 7 issues are properly labeled

### Bug #95 - Kebab-Case Validation (WP02)
- **T005**: [TEST] Write failing test for invalid slug with spaces
- **T006**: [TEST] Write test for invalid slug with underscores
- **T007**: [TEST] Write test for invalid slug starting with number
- **T008**: [TEST] Write test for uppercase in slug
- **T009**: [FIX] Add regex validation to feature.py create_feature()
- **T010**: [FIX] Add clear error message with examples
- **T011**: [VERIFY] Run tests, verify all pass
- **T012**: [COMMIT] Atomic commit (fix + 4 tests)

### Bug #120 - Gitignore Isolation (WP03)
- **T013**: [TEST] Write integration test for worktree creation (no .gitignore changes)
- **T014**: [TEST] Write test for worktree merge (no .gitignore pollution)
- **T015**: [TEST] Write test for .git/info/exclude usage
- **T016**: [FIX] Modify workflow.py:985 to use .git/info/exclude
- **T017**: [FIX] Remove .gitignore mutation logic
- **T018**: [VERIFY] Run integration tests, verify clean merges
- **T019**: [COMMIT] Atomic commit (fix + 3 tests)

### Bug #117 - Dashboard False-Failure (WP04)
- **T020**: [TEST] Write test for process detection vs health check timeout
- **T021**: [TEST] Write test for missing metadata specific error
- **T022**: [TEST] Write test for port conflict specific error
- **T023**: [TEST] Write test for dashboard --kill after startup fallback
- **T024**: [FIX] Add process detection logic in lifecycle.py
- **T025**: [FIX] Improve health check timeout handling
- **T026**: [FIX] Add specific error messages in dashboard.py
- **T027**: [VERIFY] Run tests, verify accurate state detection
- **T028**: [COMMIT] Atomic commit (fix + 4 tests)

### Bug #124 - Branch Routing Unification (WP05)
- **T029**: [TEST] Write integration test for branch preservation
- **T030**: [TEST] Write test for worktree base branch correctness
- **T031**: [TEST] Write test for status commit branch targeting
- **T032**: [FIX] Create unified branch resolution function (git/branch_utils.py)
- **T033**: [FIX] Replace logic in implement.py
- **T034**: [FIX] Replace logic in workflow.py
- **T035**: [FIX] Replace logic in tasks.py
- **T036**: [FIX] Replace logic in feature.py
- **T037**: [VERIFY] Run integration tests on all 4 commands
- **T038**: [COMMIT] Atomic commit (fix + 3 tests)

### Bug #119 - Assignee Relaxation (WP06)
- **T039**: [TEST] Update regression test for done WPs without assignee
- **T040**: [TEST] Write test verifying strict check for doing/for_review lanes
- **T041**: [TEST] Write test for all required fields still enforced
- **T042**: [FIX] Modify acceptance_core.py:455 to make assignee optional for done lane
- **T043**: [VERIFY] Run acceptance tests, verify workflow not broken
- **T044**: [COMMIT] Atomic commit (fix + 3 tests)

### Bug #122 - Safe Commit Helper (WP07)
- **T045**: [TEST] Write integration test for staged file preservation
- **T046**: [TEST] Write test for "nothing to commit" graceful handling
- **T047**: [TEST] Write test for multiple unrelated staged files
- **T048**: [FIX] Create safe_commit() helper in git/commit_helpers.py
- **T049**: [FIX] Replace unsafe commits in feature.py
- **T050**: [FIX] Replace unsafe commits in tasks.py
- **T051**: [FIX] Replace unsafe commits in implement.py
- **T052**: [VERIFY] Run integration tests with dirty staging area
- **T053**: [COMMIT] Atomic commit (fix + 3 tests + helper module)

### Bug #123 - Atomic State Transitions (WP08)
- **T054**: [TEST] Write unit tests for call order (transition before status)
- **T055**: [TEST] Write test for all 4 call sites in integration.py
- **T056**: [TEST] Write integration test for orchestrator consistency
- **T057**: [FIX] Fix integration.py:461 (start_implementation)
- **T058**: [FIX] Fix integration.py:699 (start_review)
- **T059**: [FIX] Fix integration.py:857 (complete_without_review)
- **T060**: [FIX] Fix integration.py:937 (complete_after_fallback_review)
- **T061**: [VERIFY] Run orchestrator integration tests
- **T062**: [VERIFY] Check no "No transition defined" warnings in logs
- **T063**: [COMMIT] Atomic commit (fix at 4 locations + 3 tests)

### Release v0.15.0 on Main (WP09)
- **T064**: [RELEASE] Bump version in pyproject.toml (0.14.2 → 0.15.0)
- **T065**: [RELEASE] Update CHANGELOG.md with all 7 bug descriptions
- **T066**: [RELEASE] Run full test suite (pytest tests/ -v)
- **T067**: [RELEASE] Run linting (ruff check . && ruff format --check .)
- **T068**: [RELEASE] Create release branch: release/0.15.0
- **T069**: [RELEASE] Create PR to main with comprehensive description
- **T070**: [RELEASE] Tag v0.15.0 after merge
- **T071**: [RELEASE] Push tag, verify PyPI publication

### Cherry-Pick to 2.x + Release v2.0.0a2 (WP10)
- **T072**: [CHERRY] Cherry-pick Bug #95 fix to 2.x with -x flag
- **T073**: [CHERRY] Cherry-pick Bug #120 fix to 2.x with -x flag
- **T074**: [CHERRY] Cherry-pick Bug #117 fix to 2.x with -x flag
- **T075**: [CHERRY] Cherry-pick Bug #124 fix to 2.x with -x flag
- **T076**: [CHERRY] Manually port Bug #119 fix to 2.x (acceptance.py, acceptance_support.py)
- **T077**: [CHERRY] Cherry-pick Bug #122 fix to 2.x with -x flag
- **T078**: [CHERRY] Cherry-pick Bug #123 fix to 2.x with -x flag
- **T079**: [CHERRY] Adapt tests for 2.x structure (update imports/paths)
- **T080**: [CHERRY] Run full test suite on 2.x
- **T081**: [RELEASE] Version bump on 2.x (2.0.0a1 → 2.0.0a2)
- **T082**: [RELEASE] Update CHANGELOG.md on 2.x
- **T083**: [RELEASE] Tag v2.0.0a2, push, verify PyPI

### Contributor Communication (WP11)
- **T084**: [COMM] Close issue #95 with personalized thank-you
- **T085**: [COMM] Close issue #120 with personalized thank-you
- **T086**: [COMM] Close issue #117 with personalized thank-you
- **T087**: [COMM] Close issue #124 with personalized thank-you
- **T088**: [COMM] Close issue #119 with personalized thank-you
- **T089**: [COMM] Close issue #122 with personalized thank-you
- **T090**: [COMM] Close issue #123 with personalized thank-you
- **T091**: [COMM] Post general announcement to all issues (user's voice)
- **T092**: [COMM] Update release notes with contributor acknowledgments

---

## Work Package 01: Setup Milestone and Tracking

**Summary**: Create GitHub milestone and tracking issue to coordinate all 7 bug fixes.

**Priority**: P0 (foundation - enables tracking)

**Independent Test**: Milestone exists on GitHub, tracking issue links all 7 bugs

**Subtasks**:
- [x] T001: Create GitHub milestone
- [x] T002: Create tracking issue
- [x] T003: Add acceptance checklist
- [x] T004: Verify issue labels

**Dependencies**: None

**Estimated Prompt Size**: ~200 lines (4 subtasks × 50 lines)

**Parallel Opportunities**: None (sequential setup)

**Risks**: None (low risk, GitHub API operations)

**Implementation Sketch**:
1. Use gh CLI to create milestone
2. Create tracking issue with template
3. Link all 7 issues in description
4. Add checklist for each bug + release steps

---

## Work Package 02: Fix Bug #95 - Kebab-Case Validation

**Summary**: Add validation to prevent invalid feature slugs (spaces, underscores, uppercase).

**Priority**: P1 (foundation fix)

**Independent Test**: `spec-kitty agent create-feature "Invalid Slug"` fails with clear error

**Subtasks**:
- [x] T005: Write test for spaces
- [x] T006: Write test for underscores
- [x] T007: Write test for number start
- [x] T008: Write test for uppercase
- [x] T009: Add regex validation
- [x] T010: Add error message
- [x] T011: Verify tests pass
- [x] T012: Commit atomically

**Dependencies**: None

**Estimated Prompt Size**: ~350 lines (8 subtasks × 45 lines)

**Parallel Opportunities**: Can be done in parallel with other bug fixes

**Risks**: LOW - input validation only, isolated change

**Implementation Sketch**:
1. TEST-FIRST: Write 4 failing tests for invalid slugs
2. Add regex pattern `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` in feature.py
3. Add validation before directory creation (line 288)
4. Verify all tests green
5. Commit: fix + all 4 test cases together

---

## Work Package 03: Fix Bug #120 - Gitignore Isolation

**Summary**: Use `.git/info/exclude` for worktree ignores instead of versioned `.gitignore`.

**Priority**: P1 (prevents git pollution)

**Independent Test**: Create worktree, merge, verify no .gitignore changes in history

**Subtasks**:
- [x] T013: Write test for worktree creation (no tracked .gitignore)
- [x] T014: Write test for merge (no .gitignore pollution)
- [x] T015: Write test for .git/info/exclude usage
- [x] T016: Fix workflow.py:985
- [x] T017: Remove .gitignore mutation
- [x] T018: Verify integration tests
- [x] T019: Commit atomically

**Dependencies**: None

**Estimated Prompt Size**: ~320 lines (7 subtasks × 45 lines)

**Parallel Opportunities**: Can be done in parallel with other bug fixes

**Risks**: LOW - isolated to worktree creation, well-understood git mechanism

**Implementation Sketch**:
1. TEST-FIRST: Write integration tests for clean merge behavior
2. Modify workflow.py line 985: write to `.git/info/exclude` instead of `.gitignore`
3. Remove tracked .gitignore mutation logic
4. Verify merges are clean (no .gitignore in changed files)
5. Commit: fix + 3 integration tests

---

## Work Package 04: Fix Bug #117 - Dashboard False-Failure

**Summary**: Improve dashboard lifecycle to detect running state accurately (avoid false failures).

**Priority**: P2 (UX improvement)

**Independent Test**: Dashboard running despite health timeout → CLI reports success (not error)

**Subtasks**:
- [x] T020: Write test for process detection vs health timeout
- [x] T021: Write test for missing metadata error
- [x] T022: Write test for port conflict error
- [x] T023: Write test for dashboard --kill after fallback
- [x] T024: Add process detection in lifecycle.py
- [x] T025: Improve health check timeout handling
- [x] T026: Add specific error messages in dashboard.py
- [x] T027: Verify accurate state detection
- [x] T028: Commit atomically

**Dependencies**: None

**Estimated Prompt Size**: ~400 lines (9 subtasks × 45 lines)

**Parallel Opportunities**: Can be done in parallel with other bug fixes

**Risks**: MEDIUM - dashboard lifecycle changes, needs careful testing

**Implementation Sketch**:
1. TEST-FIRST: Write 4 tests covering false-failure scenarios
2. Add process detection: check PID file or port listener before declaring failure
3. Improve health check: timeout doesn't mean failure if process exists
4. Add specific errors: metadata missing, port conflict, permission denied
5. Verify all error paths tested
6. Commit: fix + 4 tests

---

## Work Package 05: Fix Bug #124 - Branch Routing Unification

**Summary**: Create unified branch resolver, stop implicit fallback to main/master across all commands.

**Priority**: P1 (critical workflow bug)

**Independent Test**: Run commands from feature branch, verify no auto-checkout to master

**Subtasks**:
- [x] T029: Write integration test for branch preservation
- [x] T030: Write test for worktree base branch
- [x] T031: Write test for status commit targeting
- [x] T032: Create unified resolve_target_branch() function
- [x] T033: Replace logic in implement.py
- [x] T034: Replace logic in workflow.py
- [x] T035: Replace logic in tasks.py
- [x] T036: Replace logic in feature.py
- [x] T037: Verify integration tests on all 4 commands
- [x] T038: Commit atomically

**Dependencies**: None

**Estimated Prompt Size**: ~450 lines (10 subtasks × 45 lines) - AT LIMIT

**Parallel Opportunities**: Can be done in parallel with other bug fixes

**Risks**: MEDIUM - affects 4 command files, behavior change

**Implementation Sketch**:
1. TEST-FIRST: Write 3 integration tests for branch behavior
2. Create unified function in git/branch_utils.py (or similar)
3. Replace duplicated logic in 4 command files
4. Add notifications when current != target
5. Verify no auto-checkout in any command
6. Commit: fix across 4 files + 3 integration tests

---

## Work Package 06: Fix Bug #119 - Assignee Relaxation

**Summary**: Relax strict assignee gate in acceptance validation (make optional for done WPs).

**Priority**: P2 (validation fix)

**Independent Test**: Complete WP without assignee, run acceptance, verify success

**Subtasks**:
- [x] T039: Update regression test for done WPs without assignee
- [x] T040: Write test for strict check on doing/for_review
- [x] T041: Write test for required fields still enforced
- [x] T042: Modify acceptance_core.py:455 (make assignee optional)
- [x] T043: Verify acceptance workflow not broken
- [x] T044: Commit atomically

**Dependencies**: None

**Estimated Prompt Size**: ~270 lines (6 subtasks × 45 lines)

**Parallel Opportunities**: Can be done in parallel with other bug fixes

**Risks**: MEDIUM - acceptance validation logic, affects merge workflow

**2.x Note**: acceptance_core.py doesn't exist on 2.x - will need manual port in WP10

**Implementation Sketch**:
1. TEST-FIRST: Update existing regression test to expect success
2. Write 2 new tests for validation behavior
3. Modify line 455: make assignee optional or downgrade to warning
4. Keep strict checks for lane, agent, shell_pid
5. Verify acceptance still works
6. Commit: fix + 3 tests

---

## Work Package 07: Fix Bug #122 - Safe Commit Helper

**Summary**: Create safe commit helper that only commits intended files (preserves staging area).

**Priority**: P1 (critical git workflow bug)

**Independent Test**: Stage unrelated file, run move-task, verify unrelated file remains staged

**Subtasks**:
- [x] T045: Write integration test for staged file preservation
- [x] T046: Write test for "nothing to commit" graceful handling
- [x] T047: Write test for multiple unrelated staged files
- [x] T048: Create safe_commit() helper in git/commit_helpers.py
- [x] T049: Replace unsafe commits in feature.py
- [x] T050: Replace unsafe commits in tasks.py
- [x] T051: Replace unsafe commits in implement.py
- [x] T052: Verify integration tests with dirty staging
- [x] T053: Commit atomically

**Dependencies**: None

**Estimated Prompt Size**: ~400 lines (9 subtasks × 45 lines)

**Parallel Opportunities**: Can be done in parallel with other bug fixes

**Risks**: HIGH - affects git operations across multiple commands, must preserve staging area integrity

**Implementation Sketch**:
1. TEST-FIRST: Write 3 integration tests for staging scenarios
2. Create safe_commit helper: explicit file staging, preserves index
3. Find all unsafe `git commit` calls (search codebase)
4. Replace with safe_commit() in 3+ command files
5. Test with various staging scenarios
6. Commit: helper + fixes in 3 files + 3 integration tests

---

## Work Package 08: Fix Bug #123 - Atomic State Transitions

**Summary**: Fix orchestrator to call transition_wp_lane() BEFORE updating wp.status (4 locations).

**Priority**: P1 (core orchestration bug)

**Independent Test**: Run orchestrator, verify no "No transition defined" warnings

**Subtasks**:
- [x] T054: Write unit test for call order verification
- [x] T055: Write test covering all 4 call sites
- [x] T056: Write integration test for orchestrator consistency
- [x] T057: Fix integration.py:461 (start_implementation)
- [x] T058: Fix integration.py:699 (start_review)
- [x] T059: Fix integration.py:857 (complete_without_review)
- [x] T060: Fix integration.py:937 (complete_after_fallback_review)
- [x] T061: Run orchestrator integration tests
- [x] T062: Verify no warnings in logs
- [x] T063: Commit atomically

**Dependencies**: None

**Estimated Prompt Size**: ~450 lines (10 subtasks × 45 lines) - AT LIMIT

**Parallel Opportunities**: Can be done in parallel with other bug fixes

**Risks**: HIGH - core orchestration logic, affects state machine consistency

**Implementation Sketch**:
1. TEST-FIRST: Write 3 tests for call order and consistency
2. Fix all 4 call sites: move transition_wp_lane before status update
3. Verify atomic behavior (transition fails → status unchanged)
4. Run full orchestrator test suite
5. Check logs for absence of warnings
6. Commit: fixes at 4 locations + 3 comprehensive tests

---

## Work Package 09: Release v0.15.0 on Main

**Summary**: Version bump, CHANGELOG update, create release branch, tag, and publish to PyPI.

**Priority**: P1 (release process)

**Independent Test**: Fresh install shows v0.15.0, all fixes verified

**Subtasks**:
- [x] T064: Bump version in pyproject.toml
- [x] T065: Update CHANGELOG.md (all 7 bugs documented)
- [x] T066: Run full test suite (expect 1787+ pass)
- [x] T067: Run linting (ruff)
- [x] T068: Create release/0.15.0 branch
- [x] T069: Create PR with release notes
- [x] T070: Tag v0.15.0 after merge
- [x] T071: Verify PyPI publication

**Dependencies**: WP02, WP03, WP04, WP05, WP06, WP07, WP08 (all bug fixes complete)

**Estimated Prompt Size**: ~350 lines (8 subtasks × 45 lines)

**Parallel Opportunities**: None (must wait for all bug fixes)

**Risks**: LOW - standard release process, well-documented

**Implementation Sketch**:
1. Edit pyproject.toml version field
2. Add CHANGELOG.md section with all 7 bugs
3. Run full test suite, verify green
4. Create release branch
5. Create PR with comprehensive notes
6. Wait for CI, merge
7. Tag and push
8. Monitor PyPI automation

---

## Work Package 10: Cherry-Pick to 2.x + Release v2.0.0a2

**Summary**: Cherry-pick all 7 bug fixes from main to 2.x, handle divergences, test, and release.

**Priority**: P1 (ensure 2.x gets fixes too)

**Independent Test**: 2.x has all 7 fixes, tests pass, v2.0.0a2 published

**Subtasks**:
- [x] T072: Cherry-pick #95 to 2.x
- [x] T073: Cherry-pick #120 to 2.x
- [x] T074: Cherry-pick #117 to 2.x
- [x] T075: Cherry-pick #124 to 2.x
- [x] T076: Manually port #119 to 2.x (file divergence)
- [x] T077: Cherry-pick #122 to 2.x
- [x] T078: Cherry-pick #123 to 2.x
- [x] T079: Adapt tests for 2.x
- [x] T080: Run test suite on 2.x
- [x] T081: Version bump 2.x
- [x] T082: Update CHANGELOG 2.x
- [x] T083: Tag and publish v2.0.0a2

**Dependencies**: WP09 (v0.15.0 released on main)

**Estimated Prompt Size**: ~550 lines (12 subtasks × 45 lines) - ACCEPTABLE

**Parallel Opportunities**: None (sequential cherry-picking)

**Risks**: MEDIUM - manual porting needed for #119, test adaptation needed

**Implementation Sketch**:
1. Checkout 2.x, pull latest
2. Cherry-pick 6 bugs with `git cherry-pick -x <sha>`
3. Manually port Bug #119 to acceptance.py (acceptance_core.py doesn't exist)
4. Adapt test imports/paths for 2.x structure
5. Run full test suite, resolve any failures
6. Version bump and CHANGELOG for 2.x
7. Tag v2.0.0a2, push, verify PyPI

---

## Work Package 11: Contributor Communication

**Summary**: Close all 7 GitHub issues with personalized thank-you messages and post general announcement.

**Priority**: P2 (important for community)

**Independent Test**: All 7 issues closed, thank-you messages posted, contributors acknowledged

**Subtasks**:
- [x] T084-T090: Close 7 issues (one per bug)
- [x] T091: Post general announcement (user's voice)
- [x] T092: Update release notes with acknowledgments

**Dependencies**: WP09, WP10 (both releases published)

**Estimated Prompt Size**: ~400 lines (9 subtasks × 45 lines)

**Parallel Opportunities**: None (must wait for releases)

**Risks**: NONE - communication only

**Implementation Sketch**:
1. Use thank-you template for each issue (specific fix details)
2. Post comment using gh CLI
3. Close issue with label "fixed-in-0.15.0"
4. Post general announcement (user's voice from plan)
5. Update release notes on GitHub

---

## Summary

**Total Work Packages**: 11
**Total Subtasks**: 92
**Estimated Total Effort**: 16-20 hours

**WP Size Distribution**:
- WP01: 4 subtasks (~200 lines) ✓
- WP02: 8 subtasks (~350 lines) ✓
- WP03: 7 subtasks (~320 lines) ✓
- WP04: 9 subtasks (~400 lines) ✓
- WP05: 10 subtasks (~450 lines) ⚠️ (at limit)
- WP06: 6 subtasks (~270 lines) ✓
- WP07: 9 subtasks (~400 lines) ✓
- WP08: 10 subtasks (~450 lines) ⚠️ (at limit)
- WP09: 8 subtasks (~350 lines) ✓
- WP10: 12 subtasks (~550 lines) ⚠️ (could split, but acceptable)
- WP11: 9 subtasks (~400 lines) ✓

**Size Validation**: ✓ All WPs within acceptable range (200-550 lines)
- 8 WPs in ideal range (200-400 lines)
- 3 WPs at upper limit (450-550 lines) - acceptable for complex work

**Parallelization**:
- Phase 1 (Parallel): WP02-WP08 (7 bug fixes can be done simultaneously)
- Phase 2 (Sequential): WP09 (depends on all bug fixes)
- Phase 3 (Sequential): WP10 (depends on WP09 release)
- Phase 4 (Sequential): WP11 (depends on WP09 + WP10 releases)

**MVP Scope**: WP01-WP09 (setup through main release) - 2.x cherry-pick can follow

**Critical Path**: WP01 → WP02-WP08 (parallel) → WP09 → WP10 → WP11
