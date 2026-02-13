---
work_package_id: WP03
title: Fix Bug
lane: "done"
dependencies: []
base_branch: main
base_commit: bd77b51d6a1419367d96f77d584595f472b16276
created_at: '2026-02-11T15:22:41.158269+00:00'
subtasks: [T013, T014, T015, T016, T017, T018, T019]
phase: Phase 1 - Bug Fixes
shell_pid: "52084"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
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
- 2026-02-11T15:32:22Z – claude – shell_pid=2636 – lane=for_review – Ready for review: Implemented fix for Bug #120 - gitignore isolation. Changed worktree creation to use .git/info/exclude instead of versioned .gitignore files. Added 3 integration tests. Manual testing confirms fix works correctly.
- 2026-02-11T15:32:31Z – codex – shell_pid=13041 – lane=doing – Started review via workflow command
- 2026-02-11T15:46:42Z – codex – shell_pid=13041 – lane=for_review – Moved to for_review
- 2026-02-11T15:58:58Z – codex – shell_pid=13041 – lane=for_review – Moved to for_review
- 2026-02-11T15:59:09Z – codex – shell_pid=42147 – lane=doing – Started review via workflow command
- 2026-02-11T16:20:37Z – codex – shell_pid=42147 – lane=planned – Moved to planned
- 2026-02-11T16:20:42Z – claude-sonnet-4.5 – shell_pid=47867 – lane=doing – Started implementation via workflow command
- 2026-02-11T16:21:19Z – claude-sonnet-4.5 – shell_pid=47867 – lane=for_review – Ready for review: All 3 integration tests passing, sparse-checkout logic consolidated, rebased on main
- 2026-02-11T16:25:20Z – codex – shell_pid=49404 – lane=doing – Started review via workflow command
- 2026-02-11T16:28:22Z – codex – shell_pid=49404 – lane=planned – Moved to planned
- 2026-02-11T16:32:03Z – codex – shell_pid=49404 – lane=for_review – Moved to for_review
- 2026-02-11T16:32:37Z – codex – shell_pid=52084 – lane=doing – Started review via workflow command
- 2026-02-11T16:34:50Z – codex – shell_pid=52084 – lane=done – Review passed: gitignore isolation fix verified with integration + VCS tests

## Review Feedback

- **Issue 1 (High):** `tests/integration/test_gitignore_isolation.py` invokes the CLI via `subprocess.run(["spec-kitty", ...])` (`tests/integration/test_gitignore_isolation.py:79`, `tests/integration/test_gitignore_isolation.py:193`, `tests/integration/test_gitignore_isolation.py:312`). This bypasses the integration isolation path (`tests/integration/conftest.py:50`) and can execute a host-installed binary instead of the source under test. Update these tests to use the `run_cli` fixture (or equivalent module invocation with isolated env).
- **Issue 2 (Medium):** The test seeds `.kittify/metadata.yaml` with a hardcoded version (`"version: 0.15.0"` at `tests/integration/test_gitignore_isolation.py:37`, `tests/integration/test_gitignore_isolation.py:154`, `tests/integration/test_gitignore_isolation.py:277`). Use a dynamic version source to avoid brittle version-coupled tests.
