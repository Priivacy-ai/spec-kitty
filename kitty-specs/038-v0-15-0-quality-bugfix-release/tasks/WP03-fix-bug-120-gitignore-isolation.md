---
work_package_id: WP03
title: Fix Bug
lane: "doing"
dependencies: []
base_branch: main
base_commit: bd77b51d6a1419367d96f77d584595f472b16276
created_at: '2026-02-11T15:22:41.158269+00:00'
subtasks: [T013, T014, T015, T016, T017, T018, T019]
phase: Phase 1 - Bug Fixes
shell_pid: "2636"
agent: "claude"
---

# Work Package Prompt: WP03 – Fix Bug #120 - Gitignore Isolation

## Objectives

- Worktree creation uses `.git/info/exclude` for local ignores
- No `.gitignore` changes leak into planning branch merge commits
- 6 tests passing (3 integration tests)
- Fix committed atomically

**Command**: `spec-kitty implement WP03`

## Context

- **Issue**: #120 by @umuteonder
- **File**: `src/specify_cli/cli/commands/agent/workflow.py:985`
- **Bug**: Worktree .gitignore mutation pollutes planning branch history
- **Fix**: Use `.git/info/exclude` instead of versioned `.gitignore`

## Test-First Subtasks

### T013-T015: Write Failing Integration Tests

1. Test worktree creation doesn't modify tracked .gitignore
2. Test worktree merge has no .gitignore pollution
3. Test .git/info/exclude contains exclusion patterns

### T016-T017: Implement Fix

- Modify workflow.py:985 to write to `.git/info/exclude`
- Remove .gitignore mutation logic

### T018-T019: Verify and Commit

- Run integration tests (expect ✅ GREEN)
- Commit: `fix: use local git exclude for worktree ignores (fixes #120)`

## Activity Log

- 2026-02-11T15:23:22Z – claude – shell_pid=2636 – lane=doing – Assigned agent via workflow command
