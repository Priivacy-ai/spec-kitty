---
work_package_id: WP01
title: Merge & Lane Dependency Safety
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-stability-and-hygiene-hardening-2026-04-01KQ4ARB
base_commit: 78c626d61f689225b0cb3553be1cf85a3f47deb7
created_at: '2026-04-26T07:47:28.670359+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
shell_pid: "81695"
agent: "claude:opus-4-7:reviewer:reviewer"
history:
- at: 2026-04-26T07:36:00Z
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
authoritative_surface: src/specify_cli/merge/
execution_mode: code_change
mission_id: 01KQ4ARB0P4SFB0KCDMVZ6BXC8
mission_slug: stability-and-hygiene-hardening-2026-04-01KQ4ARB
owned_files:
- src/specify_cli/merge/**
- src/specify_cli/lanes/**
- tests/integration/test_merge_lane_planning_data_loss.py
- tests/integration/test_merge_resume.py
- tests/integration/test_post_merge_index_refresh.py
- tests/integration/test_post_merge_unrelated_untracked.py
- tests/integration/test_lane_db_isolation.py
- tests/unit/lanes/test_dependent_wp_scheduling.py
tags: []
---

# WP01 — Merge & Lane Dependency Safety

## Objective

Make `spec-kitty merge` correct, recoverable, and tolerant of normal repo
hygiene. Make the lane planner refuse to schedule a dependent WP into a lane
whose base does not contain its dependencies. Stop parallel SaaS / Django
lanes from colliding on a single shared test database.

## Context

Operators have hit four merge-and-lane bugs:

1. Approved commits from a `lane-planning` lane have been silently omitted in
   merge results that also include normal implementation lanes.
2. An interrupted `spec-kitty merge` cannot be cleanly resumed; the operator
   ends up in a half-merged state.
3. After merge, `git status` shows phantom deletions because the index was
   not refreshed against on-disk reality.
4. Untracked `.worktrees/` and unrelated untracked files block post-merge
   bookkeeping.

A fifth bug is the lane planner: it has placed dependent WPs into a separate
lane whose base did not include the dependency branch, leaving the dependent
WP without the source files it needs.

A sixth bug is the parallel-lanes test database: two SaaS / Django lanes
running concurrently have shared a single test DB, causing flakes.

## Branch strategy

- **Planning base**: `main` (this WP's lane is rebased onto `main`).
- **Final merge target**: `main`.
- **Lane workspace**: assigned by `finalize-tasks`. The implementation
  command is `spec-kitty agent action implement WP01 --agent <name>`, which
  resolves the actual workspace path. Do not invent paths.

## Subtasks

### T001 — Pin lane-planning data-loss regression and fix merge inclusion

**Purpose**: Prove the bug, then fix it.

**Steps**:

1. Add `tests/integration/test_merge_lane_planning_data_loss.py`. Build a
   fixture mission with three implementation WPs and one `lane-planning` WP
   that produces a planning artifact (a file under
   `kitty-specs/<slug>/research/`). Drive each WP to `approved`. Run
   `spec-kitty merge`. Assert that every approved commit (including the
   planning artifact) appears in `git log <merge-target>` after merge.
2. Run the test. It should fail against current `main` (or, if it does
   not fail, document why and tighten the assertion to capture the bug
   recorded in the issues — see Reviewer Guidance).
3. Trace `src/specify_cli/merge/executor.py` and
   `src/specify_cli/merge/state.py`. Identify where `lane-planning` lanes
   are filtered out of the wp_order. The fix is one of:
   - Include `lane-planning` lanes in `wp_order` and merge them in the
     same pass.
   - If they must be merged differently, do it explicitly in a second
     pass and assert no commits are dropped.
4. Run the new test plus the full
   `pytest tests/integration/test_merge*.py` suite.

**Validation**:
- New test passes.
- All existing merge tests still pass.
- `pytest tests/integration/ -k merge` is green.

### T002 — `spec-kitty merge --resume` is resumable and bounded

**Purpose**: An operator who is interrupted mid-merge can finish without
losing work or producing a half-merged state.

**Steps**:

1. Audit `MergeState` in `src/specify_cli/merge/state.py` and
   `src/specify_cli/merge/executor.py`. Identify resume entry points.
2. Add `tests/integration/test_merge_resume.py` that:
   - Runs `spec-kitty merge` until at least one WP is in `completed_wps`,
     then injects an interrupt (raise mid-merge or kill subprocess).
   - Re-runs `spec-kitty merge --resume` and asserts the merge completes
     with all WPs in `completed_wps` and target branch contains all
     commits.
   - Asserts wall-clock for the resumed run is ≤ 30s on a 10-lane
     fixture (NFR-005).
3. If resume is not idempotent today, fix it. The state file under
   `.kittify/merge-state.json` is the source of truth for what is
   completed; do not re-merge already-completed WPs.
4. Run `pytest tests/integration/test_merge_resume.py -v`.

**Validation**:
- Resume after interrupt completes within 30s for the 10-lane fixture.
- Re-running on a clean state is a no-op (idempotent).

### T003 — Post-merge index refresh

**Purpose**: After merge, `git status` should not show phantom deletions of
files that exist on disk.

**Steps**:

1. In `src/specify_cli/merge/executor.py`, after the final merge commit,
   call `git update-index --refresh` (subprocess) and verify exit code; if
   non-zero, log the output but do not fail (refresh-divergence is
   informational).
2. Add `tests/integration/test_post_merge_index_refresh.py` that drives a
   merge and asserts `git status --porcelain` shows no `D ` lines for files
   that exist on disk.

**Validation**:
- New test passes.
- No regression in `tests/integration/test_merge*.py`.

### T004 — Post-merge bookkeeping tolerates untracked files

**Purpose**: Untracked `.worktrees/` and unrelated untracked files must not
block the post-merge bookkeeping pass.

**Steps**:

1. Identify the post-merge cleanup path in
   `src/specify_cli/merge/executor.py` and any helpers that call
   `git status` and bail on untracked output.
2. Filter out untracked entries that are not relevant to the merged
   feature (e.g., `.worktrees/`, files outside `kitty-specs/<slug>/`).
   The filter must be a documented allowlist; do not silently swallow
   tracked changes.
3. Add `tests/integration/test_post_merge_unrelated_untracked.py` that
   creates `.worktrees/scratch/` plus a stray `tmp.txt` before merge and
   asserts post-merge bookkeeping completes successfully.

**Validation**:
- New test passes.
- Operator-supplied tracked changes still cause a clear, structured error
  (no silent suppression).

### T005 — Dependent-WP scheduler in lane planner

**Purpose**: A WP that depends on another WP must land in a lane whose base
includes the dependency, OR sequentially in the same lane.

**Steps**:

1. Read `src/specify_cli/lanes/planner.py` and the existing lane-planning
   tests. Capture the current scheduling rule.
2. Add `tests/unit/lanes/test_dependent_wp_scheduling.py`:
   - Build a WP graph with `WPa -> WPb` (b depends on a).
   - Assert: the planner places them in the same lane in dependency
     order, OR in two different lanes where lane(b)'s base contains
     lane(a)'s tip.
   - Negative case: assert the planner refuses to place b into a lane
     whose base does not contain a.
3. Adjust the planner. The simplest correct rule is: if `WPb` has any
   `depends_on` entry, place it in the lane that holds the latest
   dependency, sequentially after that dependency. Only fan out
   independent WPs into parallel lanes.
4. Re-run `pytest tests/unit/lanes/`.

**Validation**:
- All new tests pass.
- Existing lane fan-out tests for independent WPs continue to pass.

### T006 — Lane-specific test database isolation

**Purpose**: Two parallel SaaS / Django lanes must not share a single test
database.

**Steps**:

1. Identify how lanes pass `DJANGO_SETTINGS_MODULE` and the test DB URL to
   their per-lane test invocation.
2. Compute a lane-suffixed DB name: e.g. `test_<feature>_<lane_id>`.
   Inject via env (`SPEC_KITTY_TEST_DB_NAME`) when launching per-lane
   tests, and have the test settings module read it.
3. Add `tests/integration/test_lane_db_isolation.py` that simulates two
   lanes booting their test DB concurrently and asserts the DB names
   differ.

**Validation**:
- New test passes.
- Documented in `docs/explanation/execution-lanes.md` (one paragraph).

## Definition of Done

- All six subtasks complete with their listed validation passing.
- `pytest tests/integration/ -k 'merge or post_merge or lane'` green.
- `pytest tests/unit/lanes/` green.
- No regression in `tests/architectural/`.
- WP transitions from `planned` → `claimed` → `in_progress` → `for_review`
  via the standard runtime emit pipeline.

## Risks

- A fix for T005 that is too aggressive could serialize parallel work that
  is currently independent. Test by including independent-WP fan-out
  fixtures in the new tests.
- Index refresh in T003 can show divergence on file-mode-only changes;
  tolerate that case rather than failing.
- Untracked-tolerance in T004 must not silently absorb tracked changes —
  the allowlist is the contract.

## Reviewer guidance

When reviewing this WP, focus on:

1. The data-loss regression test in T001 must fail against `main` unless
   the bug has already been fixed. If the test passes against `main`
   without changes, document why in `research.md` and either pick a
   tighter assertion or close the corresponding GitHub issues with a
   `verified-already-fixed` verdict in WP08.
2. Resume idempotence (T002): re-running with state in
   `.kittify/merge-state.json` already complete should produce no commits
   and exit zero.
3. Lane planning negative case (T005): the planner refuses to place a
   dependent WP into a lane that lacks its dependency. This is the
   regression that allowed dependent WPs to execute without dependency
   files.
4. No silent suppression in T004 — the test for unrelated tracked changes
   should still surface a structured error.

## Activity Log

- 2026-04-26T07:47:30Z – claude:opus-4-7:implementer:implementer – shell_pid=76291 – Assigned agent via action command
- 2026-04-26T08:02:59Z – claude:opus-4-7:implementer:implementer – shell_pid=76291 – WP01 ready for review: merge data-loss regression pinned (T001), resume idempotent (T002), index refresh (T003), untracked tolerance (T004), dependent-WP scheduler (T005), lane DB isolation (T006). Tests in tests/integration/ and tests/unit/lanes/ green.
- 2026-04-26T08:03:47Z – claude:opus-4-7:reviewer:reviewer – shell_pid=81695 – Started review via action command
