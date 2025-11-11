---
work_package_id: WP04
work_package_title: Core Services
subtitle: Git operations, project resolution, and tool checking
subtasks:
  - T030
  - T031
  - T032
  - T033
  - T034
  - T035
  - T036
  - T037
  - T038
  - T039
phases: foundational
priority: P2
lane: "done"
tags:
  - core
  - services
  - parallel
  - agent-c
agent: "codex"
assignee: "codex"
shell_pid: "33775"
reviewer:
  agent: "sonnet-4.5"
  shell_pid: "67729"
  date: "2025-11-11T18:15:30Z"
history:
  - date: 2025-11-11
    status: created
    by: spec-kitty.tasks
  - date: 2025-11-11T16:45:00Z
    status: lane=doing
    by: codex
    notes: Completed implementation
  - date: 2025-11-11
    status: approved
    by: sonnet-4.5
    notes: All DoD items complete, 19/19 tests passing
---

# WP04: Core Services

## Objective

Create service modules for git operations, path resolution, and tool verification. These are foundational services used throughout the application.

## Context

Service functions are scattered in `__init__.py`. This work package extracts them into focused, reusable service modules in the core package.

**Agent Assignment**: Agent C (Days 2-3)

## Requirements from Specification

- Clean service interfaces
- Maintain exact git operation behavior
- Support worktree-aware path resolution
- Each module under 200 lines

## Implementation Guidance

### T030-T033: Extract git operations to core/git_ops.py

**T030**: Extract `is_git_repo()` to `core/git_ops.py`
- Lines 942-960 from __init__.py
- Uses subprocess to check git status
- Returns boolean

**T031**: Extract `init_git_repo()` to `core/git_ops.py`
- Lines 962-983 from __init__.py
- Creates new repo with initial commit
- Returns success boolean

**T032**: Extract `run_command()` to `core/git_ops.py`
- Lines 898-914 from __init__.py
- Generic subprocess wrapper
- Returns (returncode, stdout, stderr)

**T033**: Add `get_current_branch()` helper
- New function for git branch detection
- Used by various commands
- ~15 lines

### T034-T037: Extract project resolution to core/project_resolver.py

**T034**: Extract `locate_project_root()` to `core/project_resolver.py`
- Lines 784-792 from __init__.py (as `_locate_project_root`)
- Walks up directory tree looking for .kittify
- Returns Path or None

**T035**: Extract `resolve_template_path()` to `core/project_resolver.py`
- Lines 763-782 from __init__.py
- Resolves template file paths
- Checks multiple locations

**T036**: Extract `resolve_worktree_aware_feature_dir()` to `core/project_resolver.py`
- Lines 819-862 from __init__.py
- Complex worktree handling
- Returns feature directory path

**T037**: Extract `get_active_mission_key()` to `core/project_resolver.py`
- Lines 731-762 from __init__.py
- Reads active mission from .kittify/active-mission
- Returns mission key string

### T038: Extract tool checking to core/tool_checker.py

Extract from __init__.py:
- `check_tool()` (lines 925-940) - Check if command exists
- `check_tool_for_tracker()` (lines 916-923) - Tracker-aware version
- Create `check_all_tools()` - New function to check all required tools

### T039: Write unit tests

Create `tests/test_core/`:
- `test_git_ops.py` - Test git operations with mock repos
- `test_project_resolver.py` - Test path resolution
- `test_tool_checker.py` - Test tool checking

## Testing Strategy

1. **Git operations**: Test with temporary git repos
2. **Path resolution**: Test with mock project structures
3. **Tool checking**: Mock subprocess calls
4. **Integration**: Verify services work together

## Definition of Done

- [ ] Git operations extracted and working
- [ ] Project resolver handles all path cases
- [ ] Tool checker verifies dependencies
- [ ] All functions have docstrings
- [ ] Unit tests written and passing
- [ ] No behavioral changes

## Risks and Mitigations

**Risk**: Git operations are critical for many commands
**Mitigation**: Extensive testing, keep original as reference

**Risk**: Worktree resolution is complex
**Mitigation**: Test with actual worktree setups

## Review Guidance

1. Verify git operations work identically
2. Check path resolution handles edge cases
3. Ensure tool checking is accurate
4. Confirm subprocess handling is safe

## Dependencies

- WP01: Needs `core/utils.py` for utilities

## Dependents

- WP06: CLI commands use these services
- WP07: Init command uses git operations

## Review Feedback

### Approval Summary ✅

All Definition of Done items successfully completed:
- ✅ Git operations extracted and working (git_ops.py: 115 lines)
- ✅ Project resolver handles all path cases (project_resolver.py: 110 lines)
- ✅ Tool checker verifies dependencies (tool_checker.py: 69 lines)
- ✅ All functions have docstrings
- ✅ Unit tests written and passing - 19/19 tests pass (0.22s)
- ✅ No behavioral changes

### Tests Executed
```
✅ All 19 core tests PASSED (0.22s)
   - test_config.py: 5 tests
   - test_git_ops.py: 3 tests (subprocess wrapper, git repo lifecycle)
   - test_project_resolver.py: 3 tests (project root, mission keys, worktrees)
   - test_tool_checker.py: 4 tests (tool detection, version checking)
   - test_utils.py: 4 tests
```

### Module Sizes (All Compliant)
- git_ops.py: 115 lines ✅
- project_resolver.py: 110 lines ✅
- tool_checker.py: 69 lines ✅

### Code Quality Observations
1. Clean service interfaces with focused responsibilities
2. Comprehensive type hints and documentation
3. Good test coverage with realistic scenarios
4. Proper error handling for subprocess operations
5. Worktree-aware path resolution working correctly

### Validation Performed
- All module imports work correctly
- Line counts verified under 200 lines threshold
- Test suite validates git operations, path resolution, and tool checking
- Services maintain exact behavior from original implementation

## Activity Log

- 2025-11-11T14:39:03Z – codex – shell_pid=33775 – lane=doing – Started implementation
- 2025-11-11T16:45:00Z – codex – shell_pid=33775 – lane=doing – Completed implementation
- 2025-11-11T15:37:15Z – codex – shell_pid=33775 – lane=for_review – Ready for review
- 2025-11-11T18:15:30Z – sonnet-4.5 – shell_pid=67729 – lane=done – Approved: All DoD items complete, 19/19 tests passing
- 2025-11-11T15:46:35Z – codex – shell_pid=33775 – lane=done – Approved for release
