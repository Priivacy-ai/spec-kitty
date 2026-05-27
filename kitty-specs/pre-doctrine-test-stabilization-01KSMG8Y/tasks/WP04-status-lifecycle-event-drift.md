---
work_package_id: WP04
title: Status / lifecycle event drift
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
agent: claude
history:
- date: '2026-05-27'
  event: created
agent_profile: debugger-debbie
authoritative_surface: src/specify_cli/tasks/
execution_mode: code_change
owned_files:
- src/specify_cli/core/mission_creation.py
- src/specify_cli/status/emit.py
- src/specify_cli/git/**
- src/specify_cli/tasks/move_task.py
- src/specify_cli/cli/commands/implement.py
- tests/specify_cli/status/test_atomic_status_commits_unit.py
- tests/specify_cli/test_mission_creation_specify_started.py
- tests/specify_cli/tasks/test_move_task_git_validation_unit.py
- tests/specify_cli/test_status_emit_on_alloc_failure.py
role: investigator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load debugger-debbie
```

---

## Objective

Fix four independent status/lifecycle event regressions. WP04 has **exclusive ownership of `src/specify_cli/tasks/move_task.py`** — WP05 must not touch this file. If WP05 item 5 (rejection-cycle handoff) is also rooted in `move_task.py`, fold it into this WP rather than creating a parallel-lane conflict.

**Closes**: GitHub issue #1306

---

## Context

Each of the four failures is independent and can be investigated and fixed in any order. The common thread is that status events are being emitted incorrectly or not at all. Every fix must read the failing test first to understand the exact expected contract before editing production code.

**Invariant**: All `meta.json` mutations must route through `src/specify_cli/feature_metadata/mission_metadata.py` (C-004). Do not introduce direct file writes.

---

## Subtask T013 — Fix SpecifyStarted event not emitted at mission create (#1067 regression)

**Purpose**: The `SpecifyStarted` status event should be emitted when a mission is created. It was previously working but regressed.

**Steps**:

1. Run the failing test to understand the expected contract:
   ```bash
   pytest tests/ -v --tb=long -k "specify_started or SpecifyStarted" 2>&1 | head -60
   ```
   Note the exact test name (`test_mission_creation_specify_started` or similar).

2. Read the test to identify:
   - Which function call is expected to emit `SpecifyStarted`
   - What the test asserts about the event log after mission creation

3. Locate the mission creation code:
   ```bash
   grep -n "SpecifyStarted\|specify_started\|mission_create" src/specify_cli/core/mission_creation.py | head -20
   grep -rn "SpecifyStarted" src/specify_cli/ --include="*.py" | head -20
   ```

4. Find where `SpecifyStarted` was previously emitted and restore the emit call at the correct call site.

5. Run the test to confirm:
   ```bash
   pytest tests/ -v --tb=short -k "specify_started or SpecifyStarted"
   ```

**Files**: `src/specify_cli/core/mission_creation.py` or `src/specify_cli/status/emit.py` (per test output)

**Validation**:
- [ ] `test_mission_creation_specify_started` passes
- [ ] The event appears in `status.events.jsonl` after mission create in the test
- [ ] No other test regressed

---

## Subtask T014 — Fix atomic commit leaving dirty artifacts after move_task

**Purpose**: After `move_task` completes, status artifacts must be committed atomically. Currently they are left dirty (uncommitted or partially staged).

**Steps**:

1. Run the failing test:
   ```bash
   pytest tests/specify_cli/status/test_atomic_status_commits_unit.py -v --tb=long 2>&1 | head -80
   ```

2. Read the test to understand:
   - What the expected git state is after the operation
   - Which specific artifacts are left dirty

3. Trace the atomic commit flow in `src/specify_cli/git/`:
   ```bash
   find src/specify_cli/git/ -name "*.py" | xargs grep -l "atomic\|commit" | head -5
   ```

4. Identify the code path that should commit status artifacts atomically and restore the commit call or fix the staging logic.

5. Run the test to confirm:
   ```bash
   pytest tests/specify_cli/status/test_atomic_status_commits_unit.py -v
   ```

**Files**: `src/specify_cli/git/` (atomic commit helpers)

**Validation**:
- [ ] `test_atomic_status_commits_unit` passes
- [ ] Status artifacts are committed (not dirty) after the operation

---

## Subtask T015 — Fix wrong commit message on lane branch in move_task.py

**Purpose**: `move_task` is surfacing the wrong commit message to the lane branch. WP04 has exclusive ownership of `move_task.py` — if WP05 also needs changes here, coordinate.

**Steps**:

1. Run the commit-message variant of the move_task test:
   ```bash
   pytest tests/specify_cli/tasks/test_move_task_git_validation_unit.py -v --tb=long 2>&1 | head -80
   ```

2. Read the test to understand:
   - What the expected commit message format is
   - Which commit is getting the wrong message (the status commit? the task commit?)

3. Trace the commit message propagation in `src/specify_cli/tasks/move_task.py`:
   ```bash
   grep -n "commit_message\|commit_msg\|message" src/specify_cli/tasks/move_task.py | head -20
   ```

4. Fix the commit message formation or propagation path.

5. Run the test to confirm:
   ```bash
   pytest tests/specify_cli/tasks/test_move_task_git_validation_unit.py -v
   ```

**Files**: `src/specify_cli/tasks/move_task.py`

**Validation**:
- [ ] `test_move_task_git_validation_unit` (commit-message variant) passes
- [ ] The lane branch receives the correct commit message

---

## Subtask T016 — Fix implement not blocking on alloc failure

**Purpose**: When lane allocation fails, the `implement` command must block (exit non-zero or raise) rather than continuing silently.

**Steps**:

1. Run the failing test:
   ```bash
   pytest tests/ -v --tb=long -k "alloc_failure or status_emit_on_alloc" 2>&1 | head -80
   ```
   Note the exact test name (`test_status_emit_on_alloc_failure` or similar).

2. Read the test to understand what "blocking" means — exit code? exception? event emission?

3. Locate the alloc failure path in `src/specify_cli/cli/commands/implement.py`:
   ```bash
   grep -n "alloc\|allocat\|lane" src/specify_cli/cli/commands/implement.py | head -20
   ```

4. Add or restore the guard that blocks on alloc failure and emits the status event.

5. Run the test to confirm:
   ```bash
   pytest tests/ -v --tb=short -k "alloc_failure or status_emit_on_alloc"
   ```

**Files**: `src/specify_cli/cli/commands/implement.py` or related alloc path

**Validation**:
- [ ] `test_status_emit_on_alloc_failure` passes
- [ ] `implement` command blocks (does not continue) when lane allocation fails

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`

**WP05 coordination**: WP04 holds exclusive ownership of `move_task.py`. Before WP05 begins item 5 (rejection-cycle handoff), the WP05 implementer must check whether the fix is in `move_task.py`. If it is, it must be folded into WP04's lane.

To start implementation:
```bash
spec-kitty agent action implement WP04 --agent claude
```

---

## Definition of Done

- [ ] `test_atomic_status_commits_unit` passes
- [ ] `test_mission_creation_specify_started` passes
- [ ] `test_move_task_git_validation_unit` (commit-message variant) passes
- [ ] `test_status_emit_on_alloc_failure` passes
- [ ] No new test failures introduced in `tests/specify_cli/`
- [ ] No direct `meta.json` file writes introduced (C-004 compliance)

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| WP05 also needs move_task.py changes | Medium | Coordinate early; fold WP05 item 5 into WP04 if confirmed |
| Restoring SpecifyStarted emit breaks other tests | Low | Run full status test suite after T013 |
| Atomic commit fix affects non-status commits | Low | Run git-related tests after T014 |

---

## Reviewer Guidance

1. Each of the four failing tests must now pass
2. `move_task.py` changes are in WP04's lane only (no WP05 modifications to this file)
3. No `meta.json` writes bypass `mission_metadata.py`
4. Status events appear in `status.events.jsonl` (not frontmatter) after the operations
</content>