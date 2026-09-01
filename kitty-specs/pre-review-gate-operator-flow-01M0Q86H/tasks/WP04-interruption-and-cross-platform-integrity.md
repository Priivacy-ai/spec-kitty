---
work_package_id: WP04
title: Interruption and Cross-Platform Integrity Evidence
dependencies:
- WP02
requirement_refs:
- C-004
- FR-002
- FR-006
- FR-007
- NFR-003
- NFR-005
planning_base_branch: fix/pre-review-gate-operator-flow
merge_target_branch: fix/pre-review-gate-operator-flow
branch_strategy: Planning artifacts for this mission were generated on fix/pre-review-gate-operator-flow. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/pre-review-gate-operator-flow unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
phase: Phase 3 - Interruption evidence
history:
- at: '2026-08-23T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: debugger-debbie
authoritative_surface: tests/review/test_pre_review_gate_process_tree.py
create_intent:
- tests/review/test_pre_review_gate_process_tree.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_parent_death.py
execution_mode: code_change
model: ''
owned_files:
- tests/review/test_pre_review_gate_process_tree.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_parent_death.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2573'
- '#2762'
---

# Work Package Prompt: WP04 – Interruption and Cross-Platform Integrity Evidence

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `debugger-debbie`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: tests/review/test_pre_review_gate_process_tree.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Before implementing, inspect the current WP event log for `review_ref`. Address every review item and append progress chronologically to the Activity Log.

## Objective and success criteria

Add isolated evidence for the interruption contract without editing WP02/WP03 production surfaces. Catchable timeout/cancellation must reap the command-owned tree; uncatchable parent `SIGKILL` must leave lane/event state unchanged but makes no orphan-cleanup claim.

Done when POSIX real-process tests and deterministic Windows contract tests pass, with platform skips narrowly applied.

## Context and constraints

- Reuse incumbent launch/termination functions; this WP is evidence for behavior already planned as landed—verify.
- The abrupt-parent test must wait until candidate-head validation is actually running before killing the CLI parent.
- Read lane/event state from an independent process/handle after the kill.
- Never assert orphan cleanup after uncatchable parent death; #2762 retains that broader concern.
- If a production gap is found, reject/escalate to WP02 rather than editing outside `owned_files`.
- Any operational unknown-budget candidate observed outside synthetic fixtures must be appended immediately through the canonical `tracer-append` command with `provenance: operational`; synthetic process tests never enter the metadata-review queue.

## Subtasks

### T016 – Focused process fixtures

Create helpers that spawn an owned child/grandchild tree, expose readiness deterministically, and always clean fixture processes in test teardown. Keep tests bounded with polling deadlines.

### T017 – POSIX timeout and cancellation

On POSIX, exercise real timeout and catchable cancellation through the runner; assert the owned process group is reaped, one terminal outcome is returned, and no successful transition evidence is produced.

### T018 – Windows termination contract

With deterministic unit seams, assert the exact `taskkill /PID <pid> /T` tree command and escalation behavior. Mark the test `@pytest.mark.windows_ci` so `.github/workflows/ci-windows.yml` discovers it. Do not pretend a POSIX host executed Windows; WP05 must record the actual Windows job result.

### T019 – Abrupt parent death integrity

Launch the real CLI against a temporary mission/WP, wait for head validation readiness, send exactly `os.kill(parent_pid, signal.SIGKILL)` to the parent PID—not its process group—then independently read and prove no lane move or transition event append before bounded fixture teardown. Process-group/child termination is teardown only. Explicitly omit any orphan-reaping assertion.

## Test strategy

Run both owned files. On POSIX, tests use actual processes/signals; Windows-command behavior stays deterministic. Use deadlines and teardown guards to prevent leaks/flakes.

## Review guidance

Confirm the hard-kill test reaches the candidate-head phase and verifies durable state rather than trusting parent stdout. Reject broad platform skips or orphan-cleanup promises.

## Activity Log

- 2026-08-23T15:30:00Z – system – Prompt created.
