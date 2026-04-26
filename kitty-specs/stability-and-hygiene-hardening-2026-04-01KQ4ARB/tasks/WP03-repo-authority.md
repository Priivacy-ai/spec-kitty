---
work_package_id: WP03
title: Repo Authority + Status Emit Correctness
dependencies: []
requirement_refs:
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: lane-based
subtasks:
- T013
- T014
- T015
- T016
- T017
history:
- at: 2026-04-26T07:36:00Z
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
authoritative_surface: src/specify_cli/workspace/
execution_mode: code_change
mission_id: 01KQ4ARB0P4SFB0KCDMVZ6BXC8
mission_slug: stability-and-hygiene-hardening-2026-04-01KQ4ARB
owned_files:
- src/specify_cli/workspace/root_resolver.py
- src/specify_cli/workspace/__init__.py
- src/specify_cli/status/emit.py
- tests/contract/test_canonical_root_when_in_worktree.py
- tests/integration/test_status_emit_on_alloc_failure.py
- tests/unit/workspace/test_root_resolver.py
tags: []
---

# WP03 — Repo Authority + Status Emit Correctness

## Objective

Provide a single resolver that names the canonical mission repo from any
CWD (worktree or main repo). Route status emit, charter writes, and config
writes through it so that no command writes to a stale worktree-local copy.
Emit `planned -> in_progress` BEFORE any worktree allocation that could
fail, and emit a recoverable failure event on allocation failure.

## Context

When a command runs from inside a lane worktree, several emitters today
resolve the canonical repo independently — some get it right, some don't.
The bug is that status events sometimes land in the worktree's stale
`status.events.jsonl` instead of the canonical mission repo. This WP makes
the resolver a single helper used by every emitter.

WP04 depends on this WP for runtime correctness work.

## Branch strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Lane workspace**: assigned by `finalize-tasks`. Use
  `spec-kitty agent action implement WP03 --agent <name>` to enter the
  workspace. Note: WP04 is dependent and rebases onto WP03's tip.

## Subtasks

### T013 — `workspace/root_resolver.py`

**Purpose**: One function: given a CWD, return the canonical repo root.

**Steps**:

1. Create `src/specify_cli/workspace/root_resolver.py` exposing:
   ```python
   def resolve_canonical_root(cwd: Path | None = None) -> Path: ...
   ```
   - If `cwd` is in a regular git repo (no `.git/worktrees/`), return
     the repo root.
   - If `cwd` is in a worktree (`.git` is a file pointing at
     `.git/worktrees/<name>`), read `<name>/commondir` and return the
     parent of `<commondir>`.
   - If `cwd` is not in a git repo at all, raise
     `WorkspaceRootNotFound(cwd=...)`.
2. Add `src/specify_cli/workspace/__init__.py` exporting the helper.
3. Add `tests/unit/workspace/test_root_resolver.py`:
   - Main repo: returns repo root.
   - Worktree: returns canonical (main) repo, not worktree path.
   - Subdirectory inside worktree: returns canonical.
   - Non-git directory: raises `WorkspaceRootNotFound`.

**Validation**:
- `pytest tests/unit/workspace/` green.
- Helper is the only file in `workspace/` that touches `.git/worktrees/`
  parsing logic.

### T014 — Wire emit pipelines through resolver

**Purpose**: All emitters (status, charter, config) use the resolver.

**Steps**:

1. Audit `src/specify_cli/status/emit.py` and any helper that writes to
   `kitty-specs/<slug>/status.events.jsonl`. Replace ad-hoc root logic
   with `resolve_canonical_root(cwd)`.
2. Audit charter context writes (`src/specify_cli/charter/`) and config
   writes (`src/specify_cli/cli/commands/agent_config.py`,
   `src/specify_cli/lanes/*` if they write). Wire them through the
   resolver.
3. Update any callers that compute roots in their own way to delegate
   to the helper.
4. The resolver is called once per command invocation; cache the result
   in a request-scoped module-level cache (resets per process) to avoid
   redundant filesystem stats.

**Validation**:
- `grep -rn "is_dir.*\.git/worktrees" src/specify_cli/` returns hits ONLY
  in `workspace/root_resolver.py`.
- `grep -rn "with_name.*kitty-specs" src/specify_cli/` returns hits that
  all originate from the resolver result.

### T015 — `planned -> in_progress` before worktree alloc

**Purpose**: A worktree allocation failure does not leave a WP looking
inactive when it actually started.

**Steps**:

1. In the runtime path that handles `implement WPxx`
   (`src/specify_cli/next/` or `src/specify_cli/cli/commands/implement.py`):
   - Emit `planned -> in_progress` BEFORE calling the worktree
     allocator.
   - Wrap allocator in try/except. On failure, emit
     `in_progress -> blocked` with `reason="worktree_alloc_failed"`
     and include the underlying exception text in `evidence`.
2. The fix uses `emit_status_transition()` which now routes through the
   canonical root from T014.

**Validation**:
- Manual trace of the implement path shows the emit happens before the
  alloc attempt.
- Allocator failure path emits the blocked event with the structured
  reason.

### T016 — Contract test: canonical root from a worktree

**Purpose**: Pin the resolver behavior under contract test.

**Steps**:

1. Add `tests/contract/test_canonical_root_when_in_worktree.py`.
2. Build a test fixture: temp git repo with one branch, create a
   worktree via `git worktree add`, `chdir` into the worktree, and
   call `resolve_canonical_root()`.
3. Assert the returned path is the original repo root, not the
   worktree path.
4. Run an `emit_status_transition()` from inside the worktree; assert
   the resulting append in `status.events.jsonl` lands in the
   canonical repo's `kitty-specs/<slug>/`.

**Validation**:
- `pytest tests/contract/test_canonical_root_when_in_worktree.py -v`
  green.

### T017 — Integration test: emit on alloc failure

**Purpose**: Pin the FR-014 emit-before-alloc-failure semantics.

**Steps**:

1. Add `tests/integration/test_status_emit_on_alloc_failure.py`.
2. Mock `worktree_alloc()` to raise an `OSError` on first call.
3. Drive `spec-kitty implement WPxx` (via the test harness) and assert:
   - The first event in `status.events.jsonl` is the
     `planned -> in_progress` transition.
   - The second event is the `in_progress -> blocked` transition with
     `reason="worktree_alloc_failed"` and a non-empty `evidence` field.

**Validation**:
- Integration test passes.
- No regression in
  `pytest tests/integration/test_implement_workflow.py` (or analogue).

## Definition of Done

- All five subtasks complete with listed validation passing.
- `pytest tests/unit/workspace/ tests/contract/test_canonical_root_when_in_worktree.py tests/integration/test_status_emit_on_alloc_failure.py` green.
- `grep` audit confirms the resolver is the single canonicalizer in the
  codebase.
- Brief documentation note in `docs/explanation/workspace-resolver.md`
  (one short page).

## Risks

- The resolver must handle `.git/worktrees/<name>/commondir` content that
  is sometimes a relative path; resolve it relative to the worktree's
  `.git` file.
- The cache in T014 must NOT span processes — a stale cache would defeat
  the purpose. Module-level state in a long-running test runner is
  fine; reset is implicit per process.
- T015's emit-then-alloc order matters. A previous attempt emit-after-
  alloc would still hide failures. The reviewer must verify the order
  by reading the diff, not just running the test.

## Reviewer guidance

1. T013: `git worktree` test fixture is the load-bearing one. Make sure
   the test creates a real worktree (not a mock) so that the
   `commondir` parsing is exercised.
2. T014: review by `grep`. Any direct `.git/worktrees/` parsing outside
   the resolver is a regression to fix.
3. T015: read the diff for the implement path. The `emit_status_transition`
   call must precede the allocator call. A test that mocks the allocator
   to fail after the alloc starts is fine; what matters is whether the
   `planned -> in_progress` event was already on disk when the allocator
   blew up.
