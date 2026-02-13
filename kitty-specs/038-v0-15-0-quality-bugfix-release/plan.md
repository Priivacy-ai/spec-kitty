# Implementation Plan: v0.15.0 Quality Bugfix Release

**Branch**: `038-v0-15-0-quality-bugfix-release` | **Date**: 2026-02-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/038-v0-15-0-quality-bugfix-release/spec.md`

## Summary

Fix 7 critical community-reported bugs (GitHub issues #95, #120, #117, #124, #119, #122, #123) on spec-kitty main branch using test-first discipline. Release v0.15.0 on main, cherry-pick all fixes to 2.x for v2.0.0a2, and thank contributors with personalized messages.

**Approach**: One isolated commit per bug (surgical cherry-picking), comprehensive tests with each fix (54+ new tests), verify on both branches, release and communicate.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer (CLI framework), rich (console output), pytest (testing), git (version control)
**Storage**: Filesystem (git repository, .kittify metadata, test fixtures)
**Testing**: pytest with fixtures (tests/conftest.py), integration tests, regression tests
**Target Platform**: macOS, Linux (CLI tool, cross-platform)
**Project Type**: Single project (spec-kitty CLI tool in spec-kitty repo)
**Performance Goals**: Test suite completes in <5 minutes, no degradation from bugfixes
**Constraints**:
- Backward compatibility (no breaking changes)
- Both main and 2.x branches must receive fixes
- Test-first discipline (failing test → fix → green) for all bugs
**Scale/Scope**:
- 7 bugs to fix across 8 Python files
- 54+ new tests to write across 8-11 test files
- 2 releases (v0.15.0 on main, v2.0.0a2 on 2.x)
- 2 branches with 577 commit divergence

**Codebase Context**:
- Repository: https://github.com/Priivacy-ai/spec-kitty
- Main branch: v0.14.2 (stable maintenance)
- 2.x branch: v1b-complete (active SaaS development)
- Test count: ~1733 existing tests → 1787+ after
- Known divergence: `acceptance_core.py` exists on main, not on 2.x (use `acceptance.py`, `acceptance_support.py` instead)

## Constitution Check

**Status**: No constitution file exists (`.kittify/memory/constitution.md` not found)

**Skipped**: Constitution check skipped (file absent)

**Note**: This is a bugfix release on existing codebase - no architectural changes, no new patterns, no constitution gates to validate.

## Project Structure

### Documentation (this feature)

```
kitty-specs/038-v0-15-0-quality-bugfix-release/
├── spec.md              # ✅ Created - Feature specification
├── meta.json            # ✅ Created - Feature metadata
├── plan.md              # ✅ This file - Implementation plan
├── data-model.md        # To be created - Bug/Commit/Test entity models
├── quickstart.md        # To be created - Quick reference for testing fixes
├── checklists/
│   └── requirements.md  # ✅ Created - Spec quality validation
└── tasks/               # To be created by /spec-kitty.tasks
    └── (WP files generated later)
```

### Source Code (spec-kitty repository)

**Repository Root**: `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty`

**Files to Modify** (8 files across 7 bugs):

```
src/specify_cli/
├── cli/commands/
│   ├── agent/
│   │   ├── feature.py           # Bug #95: Add kebab-case validation (line 224-288)
│   │   ├── workflow.py          # Bug #120: Fix gitignore mutation (line 985)
│   │   │                        # Bug #124: Unify branch resolution
│   │   └── tasks.py             # Bug #124: Unify branch resolution
│   ├── implement.py             # Bug #124: Unify branch resolution (line 1050-1097)
│   │                            # Bug #122: Safe commit helper usage
│   └── dashboard.py             # Bug #117: Better error messages (line 45-46)
├── core/
│   └── acceptance_core.py       # Bug #119: Relax assignee gate (line 455)
├── dashboard/
│   └── lifecycle.py             # Bug #117: False-failure detection (line 407, 423)
├── merge/
│   └── executor.py              # Bug #122: Safe commit helper (NOT lines 253,280 - dry-run text)
└── orchestrator/
    └── integration.py           # Bug #123: Atomic state transitions (lines 461, 699, 857, 937)
```

**Test Files to Create** (8-11 new files):

```
tests/
├── specify_cli/
│   ├── cli/commands/
│   │   ├── test_feature_slug_validation.py        # Bug #95: 8 tests
│   │   └── test_implement_branch_respect.py       # Bug #124: 5 tests
│   ├── core/
│   │   └── test_acceptance_assignee_validation.py # Bug #119: 5 tests
│   ├── merge/
│   │   └── test_executor_git_staging.py           # Bug #122: 8 tests
│   ├── orchestrator/
│   │   └── test_integration_state_transitions.py  # Bug #123: 12 tests
│   ├── dashboard/
│   │   └── test_lifecycle_errors.py               # Bug #117: 6 tests
│   └── test_dashboard_error_messages.py           # Bug #117: 4 tests
└── integration/
    ├── test_merge_respects_staging_area.py        # Bug #122 integration
    ├── test_orchestrator_lane_transition_order.py # Bug #123 integration
    ├── test_feature_creation_validation.py        # Bug #95 integration
    └── test_worktree_gitignore_isolation.py       # Bug #120 integration
```

**Structure Decision**: Single project (spec-kitty CLI) - no frontend/backend split. All changes are within existing CLI codebase structure. Tests follow existing pytest patterns in `tests/` directory.

## Complexity Tracking

**Status**: No constitution violations (bugfix release, no new patterns)

**Note**: This release fixes existing code, does not introduce new architectural patterns or complexity. All fixes work within established spec-kitty architecture.

---

## Phase 0: Research & Technical Decisions

### R-001: Test-First Approach Validation

**Decision**: Use strict test-first discipline (red → green) for all 7 bugs

**Rationale**:
- Ensures bugs are reproducible via failing tests
- Prevents regressions (tests remain in suite)
- Validates fix actually resolves the issue
- Enables confident cherry-picking (tests verify behavior on 2.x)

**Alternatives Considered**:
- Write tests after fix: Rejected (can't prove bug existed, tests might not catch edge cases)
- Manual testing only: Rejected (regressions will occur, no CI protection)

**Implementation**: Each bug fix follows strict cycle:
1. Write failing test (proves bug exists)
2. Run test: ❌ RED
3. Implement fix
4. Run test: ✅ GREEN
5. Run full suite
6. Commit atomically (fix + tests together)

---

### R-002: Cherry-Pick Strategy for Diverged Branches

**Decision**: Surgical per-issue cherry-picks with `-x` flag, manual port only where file doesn't exist

**Rationale**:
- main and 2.x have diverged (577 commits)
- One commit per bug enables surgical cherry-picking
- `-x` flag provides audit trail (`cherry picked from commit <sha>`)
- Most files exist on both branches (6/7 bugs cherry-pick directly)

**Known Divergences**:
- Bug #119: `acceptance_core.py` exists on main, NOT on 2.x
  - 2.x equivalent: `acceptance.py`, `acceptance_support.py`
  - Strategy: Manually port fix to 2.x acceptance modules

**Alternatives Considered**:
- Batch cherry-pick all 7: Rejected (harder to resolve conflicts, all-or-nothing)
- Reimplement on 2.x from scratch: Rejected (duplicates work, loses git history link)
- Merge main into 2.x: Rejected (577 commits would create massive conflicts)

---

### R-003: Safe Commit Helper Pattern (Bug #122)

**Decision**: Create reusable `safe_commit()` helper that explicitly stages only intended files

**Rationale**:
- Current git commit calls capture ALL staged files (not just intended)
- Multiple command touchpoints need same fix (`_commit_to_branch`, `finalize-tasks`, `mark-status`)
- Centralized helper ensures consistent behavior

**Implementation Pattern**:
```python
def safe_commit(repo_path: Path, files: List[Path], message: str) -> bool:
    """Commit only specified files, preserving staging area for unrelated files."""
    # Stage only intended files
    for file in files:
        subprocess.run(["git", "add", str(file)], cwd=repo_path)

    # Commit staged files
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path,
        capture_output=True
    )

    return result.returncode == 0
```

**Alternatives Considered**:
- `git commit --only`: Rejected (doesn't work with partial staging)
- `git stash` before commit: Rejected (complex, risk of stash conflicts)
- Document "don't stage unrelated files": Rejected (user error-prone, not enforceable)

---

### R-004: Bug Fix Ordering Strategy

**Decision**: Fix bugs in dependency order (foundation bugs first, complex bugs last)

**Order Rationale**:
1. **Bug #95** (kebab-case): Foundation - prevents bad data from entering system
2. **Bug #120** (gitignore): Low risk, isolated change
3. **Bug #117** (dashboard): Error messaging, no logic changes
4. **Bug #124** (branch routing): Medium risk, affects multiple commands
5. **Bug #119** (assignee): Medium risk, acceptance validation
6. **Bug #122** (safe commits): High risk, affects git operations
7. **Bug #123** (state machine): Highest risk, core orchestration

**Rationale**:
- Simple/safe fixes first build confidence
- Complex/risky fixes last allow rollback without affecting earlier fixes
- Independent commits allow selective cherry-picking if needed

**Alternative**: Fix in issue number order (#95, #117, #119, #120, #122, #123, #124)
**Rejected Because**: Issue numbers don't reflect risk or complexity

---

## Phase 1: Design Artifacts

### D-001: Bug Fix Implementation Matrix

| Bug | File(s) | Lines | Fix Strategy | Test Count | Risk |
|-----|---------|-------|--------------|------------|------|
| #95 | feature.py | 224-288 | Add regex validation | 8 | LOW |
| #120 | workflow.py | 985 | Use .git/info/exclude | 6 | LOW |
| #117 | lifecycle.py, dashboard.py | 407, 423, 45-46 | Detect false failures | 10 | MEDIUM |
| #124 | implement.py, workflow.py, tasks.py, feature.py | Multiple | Unified branch resolver | 5 | MEDIUM |
| #119 | acceptance_core.py | 455 | Relax assignee gate | 5 | MEDIUM |
| #122 | Multiple (commit helpers) | Multiple | Safe commit helper | 8 | HIGH |
| #123 | integration.py | 461, 699, 857, 937 | Call transition before status | 12 | HIGH |

**Total**: 8 source files modified, 54 tests added

---

### D-002: Test Coverage Strategy

**Coverage Target**: 95%+ on all modified files

**Test Pyramid**:
- **Unit Tests**: 42 tests (validate individual functions, call order, validation logic)
- **Integration Tests**: 12 tests (verify end-to-end workflows, cross-file interactions)
- **Regression Tests**: All tests serve as regression protection (prevent bug recurrence)

**Test-First Discipline**:
```
For each bug:
  1. Write failing test (❌ RED)
  2. Implement fix
  3. Run test (✅ GREEN)
  4. Run full suite (✅ ALL GREEN)
  5. Commit (fix + tests together)
```

**Critical Test Cases**:
- Bug #95: Invalid slugs rejected (spaces, underscores, uppercase, numbers-first)
- Bug #120: Worktree merge doesn't pollute .gitignore
- Bug #117: Dashboard process detection vs health check timeout
- Bug #124: Branch preserved across commands (no auto-checkout)
- Bug #119: Acceptance succeeds for done WPs without assignee
- Bug #122: Staged unrelated files remain staged after status commit
- Bug #123: Lane transition commits before status change (4 call sites)

---

### D-003: Release Process Flow

**Main Branch** (v0.14.2 → v0.15.0):
```
1. Create milestone "0.15.0 - 1.x Quality Bugfixes"
2. Create tracking issue with acceptance checklist
3. Fix bugs 1-7 (one commit each, test-first)
4. Version bump: pyproject.toml, CHANGELOG.md
5. Create release branch: release/0.15.0
6. Create PR to main
7. Merge after CI green
8. Tag: v0.15.0
9. Publish to PyPI
```

**2.x Branch** (v2.0.0a1 → v2.0.0a2):
```
1. Cherry-pick bugs #95, #120, #117, #124, #122, #123 with -x
2. Manually port bug #119 (acceptance_core.py → acceptance.py)
3. Adapt tests for 2.x structure
4. Run full test suite on 2.x
5. Version bump: pyproject.toml, CHANGELOG.md
6. Create release branch: release/2.0.0a2
7. Tag: v2.0.0a2
8. Publish to PyPI
```

**Post-Release**:
```
1. Close all 7 GitHub issues with thank-you messages
2. Post general announcement (your voice)
3. Monitor for regressions (first 48 hours)
4. Reserve 0.15.1+ for post-release hotfixes only
```

---

### D-004: Safe Commit Helper Design (Bug #122)

**Interface**:
```python
def safe_commit(
    repo_path: Path,
    files_to_commit: List[Path],
    commit_message: str,
    allow_empty: bool = False
) -> CommitResult:
    """
    Commit only specified files, preserving staging area for unrelated files.

    Args:
        repo_path: Repository root path
        files_to_commit: Explicit list of files to include in commit
        commit_message: Commit message
        allow_empty: If True, don't fail on "nothing to commit"

    Returns:
        CommitResult with success status, commit SHA, or error
    """
```

**Implementation Strategy**:
1. Create helper in `src/specify_cli/git/commit_helpers.py` (new module)
2. Helper explicitly stages only provided files
3. Commits staged files
4. Preserves existing staging area (other files remain staged)
5. Handles "nothing to commit" gracefully if `allow_empty=True`

**Replacement Sites**:
- `cli/commands/agent/feature.py`: Status commits
- `cli/commands/agent/tasks.py`: move-task commits
- `cli/commands/implement.py`: Lane-claim commits
- Any other `subprocess.run(["git", "commit", ...])` that doesn't explicitly stage

---

### D-005: Unified Branch Resolution (Bug #124)

**Interface**:
```python
def resolve_target_branch(
    feature_slug: str,
    repo_path: Path,
    current_branch: str,
    respect_current: bool = True
) -> BranchResolution:
    """
    Resolve target branch for feature operations.

    Args:
        feature_slug: Feature identifier (e.g., "015-bugfix-release")
        repo_path: Repository root
        current_branch: User's current branch (from git rev-parse)
        respect_current: If True, prefer current branch over target_branch

    Returns:
        BranchResolution with target, current, should_notify, action
    """
```

**Behavior**:
- Read `target_branch` from `kitty-specs/<feature>/meta.json`
- If `current_branch == target_branch`: proceed silently
- If `current_branch != target_branch` and `respect_current=True`:
  - Show notification: "You are on '{current}', target is '{target}'"
  - Proceed on current branch (don't auto-checkout)
  - Return action: "stay_on_current"
- If `respect_current=False`: auto-checkout allowed (explicit opt-in)

**Replacement Sites**:
- `cli/commands/implement.py:1050-1097`
- `cli/commands/agent/workflow.py`
- `cli/commands/agent/tasks.py`
- `cli/commands/agent/feature.py`

---

### D-006: Dashboard Lifecycle False-Failure Detection (Bug #117)

**Focused Fix Scope** (per user guidance: option B):
- Detect when dashboard process is running despite health check timeout
- Avoid reporting error when dashboard is actually functional
- Provide specific error messages for real failures

**Detection Strategy**:
```python
def detect_dashboard_state(project_dir: Path, port: int) -> DashboardState:
    """
    Accurately detect dashboard state (running, failed, or unknown).

    Strategy:
    1. Check if process exists (PID file or port listener)
    2. If process exists, attempt health check (with timeout)
    3. If health check times out but process exists: RUNNING (not FAILED)
    4. If process doesn't exist: check why (missing metadata, port conflict, etc.)

    Returns:
        DashboardState: RUNNING, FAILED (with specific reason), or UNKNOWN
    """
```

**Changes**:
- `dashboard/lifecycle.py:407`: Check process existence before declaring failure
- `dashboard.py:45-46`: Specific error messages (metadata missing, port conflict, permission error)

**NOT in scope** (full refactor):
- Health check protocol redesign
- Startup state machine
- Metadata resilience improvements

---

## Phase 1 Artifacts Summary

**Created**:
- ✅ `plan.md` (this file)
- ✅ `data-model.md` (see below)
- ✅ `quickstart.md` (see below)

**No contracts needed**: Bugfix release - no API changes, no contracts to define

**Agent context**: Will be updated automatically by setup-plan script

---

## Next Phase

**Command**: `/spec-kitty.tasks`

**What it does**: Generate work packages (WP files) in `kitty-specs/038-v0-15-0-quality-bugfix-release/tasks/`

**Expected WPs** (7-9 total):
- WP01: Bug #95 - Kebab-case validation
- WP02: Bug #120 - Gitignore isolation
- WP03: Bug #117 - Dashboard false-failure
- WP04: Bug #124 - Branch routing unification
- WP05: Bug #119 - Assignee relaxation
- WP06: Bug #122 - Safe commit helper
- WP07: Bug #123 - Atomic state transitions
- WP08: Release process (version bump, CHANGELOG, tagging)
- WP09: Contributor communication (close issues, thank-you messages)

**Dependencies**:
- WP01-WP07 can be done in parallel (independent bugs)
- WP08 depends on WP01-WP07 (all fixes complete)
- WP09 depends on WP08 (release published)
