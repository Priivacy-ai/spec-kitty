---
work_package_id: WP01
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
title: Guards Module - Pre-flight Validation
phase: Phase 1 - Foundation
lane: "done"
assignee: "codex"
agent: "claude"
shell_pid: "53768"
history:
- timestamp: '2025-01-16T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
activity_log: "  - timestamp: \"2025-11-16T12:45:07Z\"\n    lane: \"planned\"\n  \
  \  agent: \"system\"\n    shell_pid: \"54352\"\n    action: \"Auto-repaired lane\
  \ metadata (was: for_review)\"\n"
---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Guards Module - Pre-flight Validation"
phase: "Phase 1 - Foundation"
lane: "for_review"
assignee: ""
agent: "codex"
shell_pid: "45439"
history:
  - timestamp: "2025-01-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
# Work Package Prompt: WP01 – Guards Module - Pre-flight Validation

## Objectives & Success Criteria

**Goal**: Create `src/specify_cli/guards.py` module with shared pre-flight validation logic, eliminating 60+ lines of duplication across 8 command prompt files.

**Success Criteria**:
- Guards module exists with `validate_worktree_location()` and `validate_git_clean()` functions
- Unit tests achieve 100% coverage
- Running commands from main branch fails with standardized error from guards module
- Command prompts can call Python validation instead of inline bash checks
- All 7 subtasks (T001-T007) completed and validated

## Context & Constraints

**Problem Statement**: Every command (plan, implement, review, merge) duplicates 20+ lines of identical "Location Pre-flight Check" bash code. This creates:
- Maintenance burden (updates require changing 8+ files)
- Risk of inconsistency (different prompts may diverge)
- Violation of DRY principle

**Supporting Documents**:
- Spec: `kitty-specs/005-refactor-mission-system/spec.md` (User Story 1)
- Plan: `kitty-specs/005-refactor-mission-system/plan.md` (Architecture Decision #1)
- Research: `kitty-specs/005-refactor-mission-system/research.md` (Pre-command validation approach)

**Architectural Constraints**:
- Must validate BEFORE command prompts execute (fail fast)
- Error messages must be actionable (show exact commands to fix)
- Backwards compatible with existing worktree behavior
- Cross-platform (macOS, Linux, Windows)
- Zero new dependencies (Python stdlib only)

**Current Behavior to Preserve**:
```bash
# From .kittify/missions/software-dev/commands/plan.md:19-39
git branch --show-current
# Expected: feature branch like 001-feature-name
# If main: Error with worktree navigation instructions
```

## Subtasks & Detailed Guidance

### Subtask T001 – Create guards.py module structure

**Purpose**: Establish module with docstring, imports, and exception classes.

**Steps**:
1. Create file: `src/specify_cli/guards.py`
2. Add module docstring explaining purpose (pre-flight validation for commands)
3. Add imports:
   ```python
   from __future__ import annotations
   from dataclasses import dataclass
   from pathlib import Path
   from typing import List, Optional
   import subprocess
   ```
4. Define exception:
   ```python
   class GuardValidationError(Exception):
       """Raised when pre-flight validation fails."""
       pass
   ```

**Files**: `src/specify_cli/guards.py` (new)

**Parallel?**: No (foundation for other subtasks)

**Notes**: Keep it simple - just structure, no logic yet.

---

### Subtask T002 – Define WorktreeValidationResult dataclass

**Purpose**: Create typed result object for validation outcomes.

**Steps**:
1. Add dataclass to guards.py:
   ```python
   @dataclass
   class WorktreeValidationResult:
       """Result of worktree location validation."""
       current_branch: str
       is_feature_branch: bool
       is_main_branch: bool
       worktree_path: Optional[Path]
       errors: List[str]

       @property
       def is_valid(self) -> bool:
           """True if in valid worktree location."""
           return self.is_feature_branch and not self.errors

       def format_error(self) -> str:
           """Format error message for display."""
           # Implementation in T005
           pass
   ```

**Files**: `src/specify_cli/guards.py`

**Parallel?**: No (required by T004)

**Notes**: Data model only - format_error implementation comes in T005.

---

### Subtask T003 – Write unit tests (TDD)

**Purpose**: Define expected behavior via tests before implementation.

**Steps**:
1. Create file: `tests/unit/test_guards.py`
2. Add imports and test fixtures
3. Write test cases:
   ```python
   def test_validate_worktree_on_feature_branch():
       """Should pass when on feature branch."""
       # Mock git to return feature branch
       result = validate_worktree_location()
       assert result.is_valid
       assert result.is_feature_branch

   def test_validate_worktree_on_main_branch():
       """Should fail when on main branch."""
       # Mock git to return 'main'
       result = validate_worktree_location()
       assert not result.is_valid
       assert result.is_main_branch
       assert "main" in result.format_error()

   def test_validate_git_clean_with_changes():
       """Should fail when git has uncommitted changes."""
       result = validate_git_clean()
       assert not result.is_valid
       assert len(result.errors) > 0
   ```
4. Run tests: `pytest tests/unit/test_guards.py` (expect all to fail - TDD red phase)

**Files**: `tests/unit/test_guards.py` (new)

**Parallel?**: Yes (can write while T001-T002 proceed)

**Notes**: Use pytest fixtures to mock git commands. Tests will fail until T004-T006 implemented.

---

### Subtask T004 – Implement validate_worktree_location()

**Purpose**: Core validation function checking current branch and worktree location.

**Steps**:
1. Add function to guards.py:
   ```python
   def validate_worktree_location(project_root: Optional[Path] = None) -> WorktreeValidationResult:
       """Validate command is running from feature worktree.

       Args:
           project_root: Optional project root (defaults to cwd)

       Returns:
           Validation result with errors if invalid location
       """
       if project_root is None:
           project_root = Path.cwd()

       # Get current branch
       result = subprocess.run(
           ["git", "branch", "--show-current"],
           capture_output=True,
           text=True,
           cwd=project_root
       )

       if result.returncode != 0:
           return WorktreeValidationResult(
               current_branch="unknown",
               is_feature_branch=False,
               is_main_branch=False,
               worktree_path=None,
               errors=["Not a git repository"]
           )

       current_branch = result.stdout.strip()
       is_main = current_branch in ("main", "master")
       is_feature = bool(re.match(r'^\d{3}-[\w-]+$', current_branch))

       errors = []
       if is_main:
           errors.append("Command must run from feature worktree, not main branch")

       return WorktreeValidationResult(
           current_branch=current_branch,
           is_feature_branch=is_feature,
           is_main_branch=is_main,
           worktree_path=project_root if is_feature else None,
           errors=errors
       )
   ```

2. Test with: `pytest tests/unit/test_guards.py -k worktree`

**Files**: `src/specify_cli/guards.py`

**Parallel?**: No (core logic)

**Notes**: Match existing bash behavior exactly. Feature branch pattern: `###-kebab-case`

---

### Subtask T005 – Implement helpful error formatting

**Purpose**: Provide actionable error messages with worktree navigation instructions.

**Steps**:
1. Complete `WorktreeValidationResult.format_error()` implementation:
   ```python
   def format_error(self) -> str:
       """Format error message for display."""
       if not self.errors:
           return ""

       output = [
           "Location Pre-flight Check Failed:",
           ""
       ]
       for error in self.errors:
           output.append(f"  {error}")

       if self.is_main_branch:
           output.extend([
               "",
               "You are on the 'main' branch. Commands must run from feature worktrees.",
               "",
               "Available worktrees:",
               "  $ ls .worktrees/",
               "",
               "Navigate to worktree:",
               "  $ cd .worktrees/<feature-name>",
               "",
               "Verify branch:",
               "  $ git branch --show-current"
           ])

       return "\n".join(output)
   ```

2. Test error message output manually

**Files**: `src/specify_cli/guards.py`

**Parallel?**: No (depends on T004)

**Notes**: Match existing prompt error message format for consistency.

---

### Subtask T006 – Add validate_git_clean() for mission switching

**Purpose**: Validate git repository has no uncommitted changes (required for mission switching).

**Steps**:
1. Add function to guards.py:
   ```python
   def validate_git_clean(project_root: Optional[Path] = None) -> WorktreeValidationResult:
       """Validate git repository has no uncommitted changes.

       Required before mission switching to ensure clean state.
       """
       if project_root is None:
           project_root = Path.cwd()

       result = subprocess.run(
           ["git", "status", "--porcelain"],
           capture_output=True,
           text=True,
           cwd=project_root
       )

       errors = []
       if result.stdout.strip():
           changes = [line for line in result.stdout.strip().split('\n') if line]
           errors.append(
               f"Uncommitted changes detected ({len(changes)} files). "
               "Commit or stash changes before switching missions."
           )

       return WorktreeValidationResult(
           current_branch="",  # Not relevant for git-clean check
           is_feature_branch=False,
           is_main_branch=False,
           worktree_path=None,
           errors=errors
       )
   ```

2. Add test: `test_validate_git_clean()` in test_guards.py

**Files**: `src/specify_cli/guards.py`, `tests/unit/test_guards.py`

**Parallel?**: Yes (independent function, can implement alongside T004-T005)

**Notes**: Used by WP03 (mission switch command). Similar to existing tasks_support.py git_status_lines().

---

### Subtask T007 – Run tests and verify coverage

**Purpose**: Ensure guards module has comprehensive test coverage.

**Steps**:
1. Run full test suite: `pytest tests/unit/test_guards.py -v`
2. Run with coverage: `pytest tests/unit/test_guards.py --cov=src/specify_cli/guards --cov-report=term-missing`
3. Verify 100% coverage (all lines tested)
4. If coverage gaps exist, add tests for untested branches
5. Run from different locations (main branch, feature branch, non-git directory) to verify all code paths

**Files**: `tests/unit/test_guards.py`

**Parallel?**: No (final validation step)

**Notes**: Guards module is critical path - must be bulletproof. Target 100% coverage.

---

## Test Strategy

**TDD Approach - Write Tests First**:

1. **Phase 1 - Red**: Write failing tests (T003)
   - `test_validate_worktree_on_feature_branch()` → expect pass
   - `test_validate_worktree_on_main_branch()` → expect fail with error
   - `test_validate_git_clean_with_changes()` → expect fail
   - `test_validate_git_clean_without_changes()` → expect pass
   - `test_format_error_for_main_branch()` → expect helpful message

2. **Phase 2 - Green**: Implement to make tests pass (T004-T006)
   - Implement validate_worktree_location()
   - Implement validate_git_clean()
   - Implement format_error()

3. **Phase 3 - Refactor**: Clean up and verify (T007)
   - Check coverage
   - Refactor for clarity
   - Ensure all edge cases covered

**Test Fixtures**:
```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_git_feature_branch(monkeypatch):
    """Mock git returning feature branch."""
    def mock_run(*args, **kwargs):
        result = Mock()
        result.returncode = 0
        result.stdout = "001-test-feature\n"
        return result
    monkeypatch.setattr(subprocess, "run", mock_run)

@pytest.fixture
def mock_git_main_branch(monkeypatch):
    """Mock git returning main branch."""
    def mock_run(*args, **kwargs):
        result = Mock()
        result.returncode = 0
        result.stdout = "main\n"
        return result
    monkeypatch.setattr(subprocess, "run", mock_run)
```

**Commands**:
- Run tests: `pytest tests/unit/test_guards.py`
- Coverage: `pytest tests/unit/test_guards.py --cov=src/specify_cli/guards`
- Verbose: `pytest tests/unit/test_guards.py -vv`

---

## Risks & Mitigations

**Risk 1**: Guards module breaks existing command execution
- **Mitigation**: Match existing bash check behavior exactly, test from both valid/invalid locations

**Risk 2**: Git commands fail in non-git directories
- **Mitigation**: Handle subprocess errors gracefully, return clear "not a git repository" error

**Risk 3**: Inconsistent behavior across platforms (macOS/Linux/Windows)
- **Mitigation**: Test on multiple platforms, use cross-platform git commands only

**Risk 4**: Performance impact (Python startup time)
- **Mitigation**: Keep validation logic lightweight, measure performance (<200ms target)

---

## Definition of Done Checklist

- [ ] `src/specify_cli/guards.py` exists with complete implementation
- [ ] `WorktreeValidationResult` dataclass defined
- [ ] `validate_worktree_location()` implemented and working
- [ ] `validate_git_clean()` implemented and working
- [ ] Error formatting provides actionable guidance
- [ ] Unit tests in `tests/unit/test_guards.py` pass
- [ ] Test coverage is 100%
- [ ] Tested from main branch (should fail)
- [ ] Tested from feature branch (should pass)
- [ ] Tested from non-git directory (should fail gracefully)
- [ ] No regression in existing functionality

---

## Review Guidance

**Critical Checkpoints**:
1. Error messages must match existing behavior (users see same guidance)
2. Validation logic must handle edge cases (broken git, detached HEAD, etc.)
3. Test coverage must be comprehensive (no untested branches)
4. Performance must be acceptable (<200ms for validation)

**What Reviewers Should Verify**:
- Run `/spec-kitty.plan` from main branch → should fail with guards.py error
- Run from feature worktree → should pass validation
- Check test coverage report → should show 100%
- Read error messages → should be helpful and actionable

---

## Activity Log

- 2025-01-16T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-11-16T12:26:07Z – codex – shell_pid=45439 – lane=doing – Started implementation
- 2025-11-16T12:33:11Z – codex – shell_pid=45439 – lane=doing – Completed implementation
- 2025-11-16T12:33:20Z – codex – shell_pid=45439 – lane=for_review – Ready for review
- 2025-11-16T12:45:19Z – codex – shell_pid=45439 – lane=for_review – Moved to for_review
- 2025-11-16T12:45:49Z – claude – shell_pid=53768 – lane=done – Code review complete: APPROVED. Excellent implementation with 11 comprehensive tests (all passing), proper edge case handling, clear actionable error messages, follows TDD approach, improves on prompt with better is_valid logic and unexpected branch detection. Ready for integration.
