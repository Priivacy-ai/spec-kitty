---
work_package_id: WP02
title: Parity ratchet over the status write path
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs:
- '1672'
planning_base_branch: feature/status-writepath-profile-surface-remediation
merge_target_branch: feature/status-writepath-profile-surface-remediation
branch_strategy: Planning artifacts for this mission were generated on feature/status-writepath-profile-surface-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/status-writepath-profile-surface-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
phase: 'Lane A — #1667 ownership'
agent: claude
history:
- at: '2026-06-05T08:32:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_execution_context_parity.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_execution_context_parity.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Parity ratchet over the status write path

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role `implementer`) before proceeding.

---

## Objectives & Success Criteria

Extend the existing CWD-invariance ratchet (#1672) to cover the status **write** transition now routed through the aggregate (depends on WP01).

- **FR-008**: assert that `spec-kitty agent status emit` (a write) produces identical results from the **main-checkout CWD** and a **lane-worktree CWD**, and that the ratchet fails if a surface re-derives execution context.

**Done when**: the ratchet exercises the write path, passes for both CWDs, has an anti-vacuity case, stays registered in CI, and **does not weaken** the existing read-parity assertions (C-008).

## Context & Constraints

- The ratchet (`tests/architectural/test_execution_context_parity.py`) today only proves the `agent tasks status --json` **read** is CWD-invariant. WP01 makes `agent status emit` route through `MissionStatus.transition()`; this WP ratchets that write.
- **C-008**: extend only; never weaken existing assertions. The file is a P0 surface owned by another contributor — be surgical.

## Branch Strategy

- **Planning base / merge target**: `feature/status-writepath-profile-surface-remediation`
- **Depends on**: WP01 (the wiring must exist to ratchet it).

## Subtasks & Detailed Guidance

### Subtask T007 – Add a write-transition step to the fixture

- **Steps**: reuse the existing real-worktree fixture; after the read-parity assertions, drive `agent status emit <WP> --to <lane>` from the main checkout, capturing the resulting event/snapshot.
- **Files**: `tests/architectural/test_execution_context_parity.py`

### Subtask T008 – Assert CWD-parity of the write

- **Steps**: run the same `agent status emit` from the lane-worktree CWD against an equivalently-seeded mission; assert the emitted event identity, resulting lane, and status output are identical across both CWDs.

### Subtask T009 – Anti-vacuity

- **Steps**: mirror the existing `test_ratchet_catches_divergence` pattern — deliberately corrupt the write path (e.g. force a wrong feature_dir) and assert the ratchet **fails**, proving it is not vacuously green.
- **Parallel?**: [P] with T010.

### Subtask T010 – CI registration

- **Steps**: confirm the extended test runs under the same CI job/marker as the existing ratchet (no new exclusion). Document the marker in the test module docstring.
- **Parallel?**: [P] with T009.

## Test Strategy

- `pytest tests/architectural/test_execution_context_parity.py` (note: spawns `git worktree`; honor existing `non_sandbox` marker).

## Risks & Mitigations

- **Weakening the gate** → only add assertions; run the full file before/after to prove the read-parity tests still pass.
- **Flakiness from worktree spawning** → reuse the existing module-scoped fixture rather than creating new worktrees per test.

## Review Guidance

- Confirm the existing read-parity tests are unchanged.
- Confirm the anti-vacuity case genuinely fails when the write path diverges.

## Activity Log

- 2026-06-05T08:32:05Z – system – Prompt created.
