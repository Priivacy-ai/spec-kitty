# Feature Specification: v0.15.0 Quality Bugfix Release

**Feature Branch**: `038-v0-15-0-quality-bugfix-release`
**Created**: 2026-02-11
**Status**: Draft
**Target Branch**: main
**Input**: Community feedback from 7 GitHub issues; detailed plan at ~/.claude/plans/curious-wishing-metcalfe.md

## Overview

The spec-kitty community has reported 7 critical bugs affecting daily workflow quality. This release fixes all 7 bugs on the main branch (v0.14.2 → v0.15.0) using test-first discipline, then cherry-picks fixes to the 2.x branch for v2.0.0a2, ensuring both maintenance and development tracks benefit from improved quality.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Feature Creation (Bug #95 - Priority: P1)

A developer uses the CLI to create a new feature. The system should prevent invalid feature slugs that would cause downstream failures.

**Why this priority**: Invalid slugs break worktree creation and git branch naming, blocking all subsequent work.

**Independent Test**: Run `spec-kitty agent create-feature "Invalid Feature Name"` and verify it fails with clear error message before creating any directories.

**Acceptance Scenarios**:

1. **Given** a developer runs `spec-kitty agent create-feature "user-authentication"`, **When** the command executes, **Then** feature 038-user-authentication is created successfully (valid kebab-case).

2. **Given** a developer runs `spec-kitty agent create-feature "User Authentication"` (with spaces), **When** the command executes, **Then** the command fails immediately with error message: "Invalid feature slug 'User Authentication'. Must be kebab-case (lowercase letters, numbers, hyphens only). Examples: 'user-auth', 'fix-bug-123', 'new-dashboard'".

3. **Given** a developer runs `spec-kitty agent create-feature "user_authentication"` (with underscore), **When** the command executes, **Then** the command fails with kebab-case validation error.

---

### User Story 2 - Worktree Ignores Don't Pollute History (Bug #120 - Priority: P1)

When creating worktrees for work packages, temporary ignore patterns should not leak into the main branch's git history.

**Why this priority**: Polluted .gitignore files in merge commits create confusion and version control noise.

**Independent Test**: Create worktree, make changes, merge back to main, verify main's .gitignore is unchanged.

**Acceptance Scenarios**:

1. **Given** a developer runs `spec-kitty implement WP01` (creates worktree), **When** the worktree needs to ignore WP status files, **Then** exclusion rules are written to `.git/info/exclude` (local, not versioned).

2. **Given** a WP worktree has been merged back to main, **When** checking git history, **Then** no `.gitignore` changes appear in the merge commit.

3. **Given** worktree-specific ignore patterns exist in `.git/info/exclude`, **When** the worktree is removed, **Then** patterns are cleaned up automatically.

---

### User Story 3 - Dashboard Startup Reports Accurate Status (Bug #117 - Priority: P2)

When starting the dashboard, the CLI should accurately detect whether the dashboard is actually running or failed, avoiding false negatives.

**Why this priority**: Users waste time troubleshooting when dashboard works but CLI reports errors.

**Independent Test**: Start dashboard with various failure modes, verify CLI reports match actual dashboard state.

**Acceptance Scenarios**:

1. **Given** dashboard process is running but health check times out, **When** running `spec-kitty dashboard`, **Then** CLI detects running process and reports success (not failure).

2. **Given** `.kittify` directory missing, **When** running `spec-kitty dashboard`, **Then** CLI reports specific error: "Dashboard metadata not found. Run 'spec-kitty init .' to initialize project."

3. **Given** dashboard failed to start due to port conflict, **When** running `spec-kitty dashboard`, **Then** CLI reports specific error: "Port X unavailable" (not generic "unable to start").

---

### User Story 4 - Branch Routing Respects User Context (Bug #124 - Priority: P1)

When working on a feature branch, CLI commands should respect the user's current branch and not auto-switch to main/master without permission.

**Why this priority**: Unexpected branch switching causes work to be committed to wrong branches, creating merge conflicts.

**Independent Test**: Run commands from feature branch, verify current branch is preserved.

**Acceptance Scenarios**:

1. **Given** user is on feature branch `feature/new-auth`, **When** running `spec-kitty implement WP01`, **Then** worktree is created from `feature/new-auth` (not main).

2. **Given** user is on branch `develop` but feature target is `main`, **When** running status-changing commands, **Then** CLI shows notification ("You are on 'develop', target is 'main'") but does NOT auto-checkout main.

3. **Given** user wants to stay on current branch, **When** making status commits, **Then** commits land on current branch, not auto-switched to target.

---

### User Story 5 - Acceptance Works for Complete WPs (Bug #119 - Priority: P2)

When a work package is complete and in 'done' lane, acceptance validation should not require optional metadata fields that aren't relevant to completed work.

**Why this priority**: Strict validation blocks legitimate merges, forcing manual frontmatter edits.

**Independent Test**: Complete WP without assignee field, run acceptance, verify it succeeds.

**Acceptance Scenarios**:

1. **Given** WP01 is in 'done' lane with no `assignee` field in frontmatter, **When** running `spec-kitty accept`, **Then** acceptance validation passes (assignee not required for done WPs).

2. **Given** WP02 is in 'doing' lane with no `assignee` field, **When** running `spec-kitty accept`, **Then** validation warns or fails (assignee still meaningful for active work).

3. **Given** WP03 is in 'for_review' lane with no `assignee` field, **When** running acceptance, **Then** validation behavior is consistent with active work policy.

---

### User Story 6 - Status Commits Don't Capture Unrelated Work (Bug #122 - Priority: P1)

When CLI commands make status commits (moving tasks, marking progress), only intended files should be committed, not unrelated staged files.

**Why this priority**: Accidental commits pollute git history and make code review difficult.

**Independent Test**: Stage unrelated file, run `spec-kitty agent tasks move-task WP01 --to doing`, verify unrelated file remains staged but uncommitted.

**Acceptance Scenarios**:

1. **Given** user has staged `debug-notes.txt` for a separate commit, **When** running `spec-kitty agent tasks move-task WP01 --to doing`, **Then** status commit includes only WP01 status file, and `debug-notes.txt` remains staged.

2. **Given** status update command needs to commit frontmatter change, **When** git staging area contains unrelated files, **Then** safe commit helper stages only the frontmatter file before committing.

3. **Given** "nothing to commit" scenario (status already up-to-date), **When** safe commit helper runs, **Then** command succeeds gracefully without affecting staging area.

---

### User Story 7 - State Transitions Are Atomic (Bug #123 - Priority: P1)

When the orchestrator transitions work packages through lanes, lane updates must commit successfully before status changes, ensuring state consistency.

**Why this priority**: Race conditions cause "No transition defined" warnings and inconsistent kanban state.

**Independent Test**: Run orchestrator on feature, verify all lane transitions complete before status changes.

**Acceptance Scenarios**:

1. **Given** WP01 starts implementation, **When** orchestrator processes the transition, **Then** `transition_wp_lane()` is called and commits lane change BEFORE `wp.status = IMPLEMENTATION` is set.

2. **Given** WP02 review is approved, **When** completing review, **Then** lane transitions to 'done' BEFORE `wp.status = COMPLETED` is set.

3. **Given** lane transition fails (git commit fails), **When** orchestrator handles failure, **Then** WP status remains unchanged (atomic behavior).

---

## Functional Requirements

### FR-001: Input Validation (Bug #95)

**Requirement**: Feature slug must be validated against kebab-case pattern before creating directories.

**Validation Rule**: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` (lowercase letters, numbers, hyphens only; must start with letter)

**Error Handling**: Reject invalid slugs with actionable error message showing valid examples.

**Testability**: Unit tests verify regex matching; integration tests verify command rejection.

---

### FR-002: Worktree Ignore Isolation (Bug #120)

**Requirement**: Worktree-specific ignore patterns must use local git exclude mechanisms, not versioned .gitignore files.

**Implementation Constraint**: Write patterns to `.git/info/exclude` in worktree (local, not tracked).

**Validation**: Merging worktree branch does not introduce .gitignore changes in commit history.

**Testability**: Integration test creates worktree, merges, verifies no .gitignore noise in planning branch.

---

### FR-003: Dashboard Lifecycle Accuracy (Bug #117)

**Requirement**: Dashboard startup detection must distinguish between "process failed to start" and "process running but health check incomplete".

**Specific Behavior**: If dashboard process is running on expected port, report success even if health token check times out.

**Error Messages**: Specific errors for missing metadata, port conflicts, permission issues (not generic "unable to start").

**Testability**: Unit tests for each error path; integration test for false-failure detection.

---

### FR-004: Branch Routing Unification (Bug #124)

**Requirement**: CLI commands must unify branch resolution logic and stop implicit fallback to main/master.

**Behavior**: Respect user's current branch; show notification when current differs from target; never auto-checkout without explicit user action.

**Affected Commands**: implement, workflow, tasks, feature (all use unified branch resolver).

**Testability**: Integration tests run commands from non-main branches, verify no auto-checkout occurs.

---

### FR-005: Assignee Validation Relaxation (Bug #119)

**Requirement**: Acceptance validation must not require `assignee` field for work packages in 'done' lane.

**Rationale**: Assignee is only meaningful for active work; completed work doesn't need active assignee tracking.

**Strict Checks Retained**: lane, agent, shell_pid remain required fields.

**Testability**: Unit tests verify validation logic; integration test completes WP without assignee and accepts successfully.

---

### FR-006: Safe Commit Helpers (Bug #122)

**Requirement**: All CLI commit operations must use safe commit helper that stages only intended files.

**Helper Behavior**:
1. Identify specific files to commit (explicit list)
2. Stage only those files: `git add <file1> <file2>`
3. Commit staged files
4. Preserve existing staging area state (don't affect unrelated staged files)

**Affected Operations**: `_commit_to_branch`, `finalize-tasks`, `mark-status`, implement lane-claim commit.

**Testability**: Integration test pre-stages unrelated file, runs commit operation, verifies unrelated file remains staged/uncommitted.

---

### FR-007: Atomic State Transitions (Bug #123)

**Requirement**: Orchestrator must call `transition_wp_lane()` BEFORE updating `wp.status` in all state transitions.

**Affected Locations**: 4 transition points in integration.py (lines 461, 699, 857, 937).

**Atomic Behavior**: If lane transition fails, status remains unchanged (rollback-safe).

**Testability**: Unit tests verify call order; integration tests verify lane/status consistency under failures.

---

## Success Criteria

**Release Quality**:
- All 7 bugs fixed with verified behavior changes
- 54+ new tests added with 95%+ coverage on modified files
- All existing tests passing (1787+ total tests)
- No new linting errors introduced

**Release Process**:
- v0.15.0 published to PyPI successfully from main branch
- v2.0.0a2 published to PyPI from 2.x branch (cherry-picked fixes)
- GitHub releases created with complete notes

**Cherry-Pick Success**:
- 6 bugs cherry-pick cleanly to 2.x
- 1 bug (# 119) manually ported to 2.x acceptance modules
- All tests pass on both main and 2.x

**Community Engagement**:
- All 7 GitHub issues closed with personalized thank-you messages
- Contributors acknowledged by name in release notes
- Upgrade path documented and tested

**Installation Verification**:
- Fresh install from PyPI shows correct version (0.15.0 on main track)
- Each fixed bug manually verified in clean environment
- No regressions reported in first 48 hours

---

## Scope

### In Scope

**Bug Fixes**:
- ✅ #95: Kebab-case slug validation
- ✅ #120: Worktree gitignore isolation
- ✅ #117: Dashboard startup accuracy (focused fix, not full refactor)
- ✅ #124: Branch routing unification
- ✅ #119: Assignee validation relaxation
- ✅ #122: Safe commit helper
- ✅ #123: Atomic state transitions

**Testing**:
- ✅ Test-first discipline (failing test → fix → green)
- ✅ 54+ new tests (unit + integration + regression)
- ✅ Full CI verification on both branches

**Release**:
- ✅ v0.15.0 on main branch
- ✅ v2.0.0a2 on 2.x branch (cherry-picked)
- ✅ PyPI publication for both versions

**Communication**:
- ✅ Contributor thank-you messages (7 issues)
- ✅ Release notes with detailed fix descriptions
- ✅ Upgrade instructions

### Out of Scope

**Not Included**:
- ❌ Dashboard lifecycle full refactor (only focused false-failure fix)
- ❌ New features or enhancements (bugfixes only)
- ❌ Breaking changes (maintain backward compatibility)
- ❌ Performance optimizations unrelated to bugs
- ❌ Documentation updates beyond bug fix explanations

**Deferred to Later**:
- Feature requests from issues (e.g., #121 deterministic enforcement, #84 blocked-by UI)
- Enhancement requests (e.g., #125 skip rebase, #65 avoid new requests)
- Agent support additions (e.g., #76 Google Antigravity)

---

## Assumptions

1. **Branch Strategy**: main is stable maintenance track (0.x → 1.x), 2.x is active SaaS development (2.x). Both receive bugfixes.

2. **Architectural Divergence**: main and 2.x have diverged (577 commits difference). Cherry-picks may need adaptation, especially for acceptance validation (#119).

3. **Test Framework**: pytest is standard; existing test patterns in `tests/` directory provide templates.

4. **Git Workflow**: Contributors use git for version control; .git directory structure is standard.

5. **CI/CD**: GitHub Actions runs tests automatically on PR; PyPI publication is automated.

6. **User Environment**: Developers have Python 3.11+, git, spec-kitty installed.

7. **Contributor Communication**: All 7 issue reporters are active on GitHub and will see thank-you comments.

8. **Release Timing**: v0.15.0 is patch release (not major/minor), follows semantic versioning.

---

## Key Entities

### Bug (Data Entity)

**Attributes**:
- Issue number (e.g., #95, #120)
- Title (e.g., "Kebab-case validation")
- Reporter (GitHub username)
- Priority (P1, P2)
- Risk level (LOW, MEDIUM, HIGH)
- File location (path + line numbers)
- Fix description
- Test count

**Relationships**:
- Bug → Commit (one-to-one: one isolated commit per bug)
- Bug → Tests (one-to-many: multiple tests per bug)
- Bug → GitHub Issue (one-to-one)

---

### Commit (Data Entity)

**Attributes**:
- SHA (unique identifier)
- Message (follows format: `fix: {description} (fixes #{number})`)
- Files changed (code + tests together)
- Branch (main or 2.x)
- Cherry-pick status (direct, needs adaptation, or manual port)

**Relationships**:
- Commit → Bug (one-to-one: fixes one bug)
- Commit → Tests (embedded: tests in same commit as fix)
- Main Commit → 2.x Commit (cherry-pick relationship with `-x` flag)

---

### Test (Data Entity)

**Attributes**:
- Type (unit, integration, regression)
- File path (location in tests/ directory)
- Coverage target (which bug it validates)
- Pass/fail status
- Branch compatibility (works on main, 2.x, or needs adaptation)

**Relationships**:
- Test → Bug (many-to-one: multiple tests validate one bug fix)
- Test → Commit (embedded: created in same commit as fix)

---

### Release (Data Entity)

**Attributes**:
- Version (v0.15.0 on main, v2.0.0a2 on 2.x)
- Branch (main or 2.x)
- Publication status (tagged, pushed, PyPI published)
- Changelog entry (markdown formatted)
- Bugs fixed (list of 7)

**Relationships**:
- Release → Commits (one-to-many: includes 7 bug fix commits + version bump)
- Release → Tests (one-to-many: includes all new tests)

---

## Dependencies

### Internal Dependencies

**Feature Dependencies**: None (bugfix release is standalone)

**Code Dependencies**:
- Existing test framework (pytest, fixtures in `tests/conftest.py`)
- Existing git utilities (`src/specify_cli/git/`)
- Existing CLI framework (typer, rich console)

**Data Dependencies**:
- Plan file: `~/.claude/plans/curious-wishing-metcalfe.md` (comprehensive implementation plan)
- GitHub issues: #95, #120, #117, #124, #119, #122, #123

### External Dependencies

**Development Tools**:
- pytest >= 7.0 (testing)
- ruff (linting)
- git >= 2.30 (version control)

**Release Tools**:
- gh CLI (GitHub operations: milestones, issues, PRs)
- PyPI credentials (package publication)
- GitHub Actions (CI/CD automation)

**Optional**:
- Coverage.py (test coverage reporting)

---

## Risks & Mitigations

### Risk: State Machine Fix Breaks Orchestrator (Bug #123)

**Likelihood**: Medium
**Impact**: High
**Severity**: HIGH

**Mitigation**:
- Comprehensive integration tests (12+ tests covering all 4 transition points)
- Run full orchestrator smoke test on multi-WP feature
- Verify lane/status consistency under failure scenarios
- Easy rollback (single commit revert)

---

### Risk: Safe Commit Helper Breaks Merge Workflow (Bug #122)

**Likelihood**: Medium
**Impact**: High
**Severity**: HIGH

**Mitigation**:
- Test with various staging scenarios (clean, dirty, mixed)
- Verify "nothing to commit" case handles gracefully
- Test stash/unstash edge cases
- Integration test with real merge workflow
- Easy rollback (single commit revert)

---

### Risk: Cherry-Pick Conflicts on 2.x

**Likelihood**: High (especially Bug #119)
**Impact**: Medium
**Severity**: MEDIUM

**Mitigation**:
- Known divergence: `acceptance_core.py` doesn't exist on 2.x
- Manual port strategy documented for #119
- Test adaptation process defined
- Surgical cherry-picks (-x flag) allow easy conflict identification

---

### Risk: Dashboard Fix Insufficient (Bug #117)

**Likelihood**: Medium
**Impact**: Low
**Severity**: LOW

**Mitigation**:
- Focused scope (false-failure detection only, not full refactor)
- Can enhance in v0.15.1 if more issues reported
- Tests verify specific error paths work correctly

---

## Out of Scope *(optional)*

**Explicitly NOT Included**:

1. **Dashboard Full Lifecycle Refactor**: Bug #117 uses focused fix (1-2 hours), not comprehensive refactor (3-4 hours)

2. **Performance Optimizations**: No performance work in this release (bugfixes only)

3. **New Features**: Enhancement requests from issues (#121, #84, #125, #65) deferred to future releases

4. **Breaking Changes**: All fixes maintain backward compatibility

5. **Agent Support**: No new agent integrations (e.g., #76 Google Antigravity)

6. **Monorepo Support**: Major feature request (#67) deferred

---

## Notes

**Test-First Discipline**: Each bug fix follows strict TDD:
1. Write failing regression test (demonstrates bug exists)
2. Implement fix
3. Run test: ✅ GREEN
4. Run full CI
5. Commit atomically (fix + tests in one commit for surgical cherry-picking)

**Cherry-Pick Strategy**: Use `git cherry-pick -x <sha>` for audit traceability. Manual port only for Bug #119 due to 2.x architectural divergence.

**Version Numbering**:
- main: 0.14.2 → 0.15.0 (minor version bump, 7 bugfixes)
- 2.x: 2.0.0a1 → 2.0.0a2 (alpha increment, cherry-picked fixes)

**Contributor Acknowledgment**:
- @brkastner, @umuteonder, @MRiabov, @digitalanalyticsdeveloper, @fabiodouek
- Personalized thank-you messages in your voice
- Recognition in release notes

**Timeline**: 16-20 hours total execution (including testing, cherry-picking, release process, communication)
