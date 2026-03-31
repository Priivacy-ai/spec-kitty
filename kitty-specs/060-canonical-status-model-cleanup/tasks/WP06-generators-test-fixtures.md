---
work_package_id: WP06
title: Generators + Test Fixtures
dependencies: []
requirement_refs:
- FR-005
- FR-011
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 5136cf9893211b4065292f56452a5e9cc773e0b8
created_at: '2026-03-31T07:22:39.518059+00:00'
subtasks: [T021, T022, T023]
shell_pid: "88096"
history:
- at: '2026-03-31T06:58:09+00:00'
  actor: planner
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/core/worktree.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/worktree.py
- tests/conftest.py
---

# WP06: Generators + Test Fixtures

## Objective

Update worktree.py README generator to describe lane-free frontmatter. Remove `lane` from conftest.py WP fixtures. Update any active tests that assert `lane:` in modern WP frontmatter.

## Context

- `core/worktree.py:384` generates README content for task directories, currently documenting `lane:` in WP frontmatter
- `tests/conftest.py:399,508` creates WP fixtures with `lane: doing` for testing
- Various tests may assert on frontmatter lane in non-migration contexts
- WP02 and WP03 must be done first so finalize-tasks can seed canonical state for tests that need lane info

## Implementation Command

```bash
spec-kitty implement WP06 --base WP02
```

---

## Subtask T021: Update worktree.py README Generator

**Location**: `src/specify_cli/core/worktree.py` around line 384

**Steps**:
1. Find the README generation code that documents WP frontmatter with `lane:` field
2. Replace with 3.0 model description: status lives in `status.events.jsonl`, not frontmatter
3. Match the content from the already-updated `tasks/README.md` in this feature

---

## Subtask T022: Remove lane from conftest.py Fixtures

**Location**: `tests/conftest.py` around lines 399, 508

**Steps**:
1. Find WP fixture creation that includes `lane: doing` or other lane values
2. Remove `lane` from the fixture frontmatter
3. If tests need WP status, they should seed it via `emit_status_transition()` or `bootstrap_canonical_state()` rather than frontmatter

---

## Subtask T023: Update Active Tests

**Steps**:
1. Search for test files that assert `lane:` in modern WP frontmatter (not migration tests)
2. Update assertions to check canonical state (`status.json` or event log) instead of frontmatter
3. Where tests create WP fixtures, ensure they don't include `lane:` in frontmatter
4. Migration-specific test fixtures MAY keep `lane:` — those are explicitly testing legacy behavior

**Search pattern**: `grep -rn 'lane.*planned\|lane.*doing\|lane.*for_review\|lane.*done' tests/ --include='*.py'`
Filter out: files under `tests/*/migration*`, `tests/*/upgrade*`

---

## Definition of Done

- [ ] worktree.py generates lane-free README content
- [ ] conftest.py fixtures have no `lane` in WP frontmatter
- [ ] Active tests don't assert `lane:` in modern WP frontmatter (migration tests exempt)
- [ ] Full test suite passes after fixture changes
