---
work_package_id: WP02
title: Status Transition Atomicity
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-001
- NFR-003
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - Workflow State Trust
assignee: ''
agent: claude
history:
- at: '2026-05-02T08:10:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/**
- src/specify_cli/cli/commands/agent/tasks.py
- tests/status/**
- tests/tasks/test_move_task_git_validation_unit.py
- tests/unit/status/test_review_claim_transition.py
role: implementer
tags: []
---

# Work Package Prompt: WP02 – Status Transition Atomicity

## ⚡ Do This First: Load Agent Profile

Before reading further or changing files, load the assigned agent profile:

```text
/ad-hoc-profile-load python-pedro
```

Use that profile's implementation discipline for the rest of this WP.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` decides the lane workspace path and records the lane branch in `base_branch`.

## Objectives & Success Criteria

Fix #945 and verify #944. A transition command may report success only after the expected event exists in `status.events.jsonl` and can be read back. Backgrounded, interrupted, or slow implement/review paths must not strand WPs in `claimed`.

Success means:
- `move-task` and related status command paths fail non-zero when the expected event is not persisted.
- Worktree/subagent paths resolve the canonical mission event log.
- #944 remains covered by regression tests.

## Context & Constraints

- Contract: `kitty-specs/release-320-workflow-reliability-01KQKV85/contracts/status-transition-atomicity.yaml`
- Owned source: `src/specify_cli/status/**`, `src/specify_cli/cli/commands/agent/tasks.py`
- Keep changes focused on local status durability. Hosted sync failures after local success are WP05.

## Subtasks & Detailed Guidance

### Subtask T007 – Add move-task event persistence tests
- **Purpose**: Reproduce #945 directly.
- **Steps**:
  1. Add tests that exercise `spec-kitty agent tasks move-task` success paths.
  2. Assert the expected transition event exists in `status.events.jsonl`.
  3. Add a failure fixture where event append/readback is blocked and assert non-zero result.
- **Files**: `tests/status/**`, `tests/tasks/test_move_task_git_validation_unit.py`.
- **Parallel?**: No.

### Subtask T008 – Add #944 claimed recovery coverage
- **Purpose**: Verify closed #944 remains fixed.
- **Steps**:
  1. Simulate backgrounded, interrupted, and slow implement/review flows using local fixtures.
  2. Assert WPs do not remain stranded in `claimed` without recovery evidence or diagnostic.
  3. Keep tests deterministic; do not rely on real process timing unless unavoidable.
- **Files**: `tests/status/**`, `tests/unit/status/test_review_claim_transition.py`.
- **Parallel?**: Yes, after WP01.

### Subtask T009 – Implement post-write event readback invariants
- **Purpose**: Make local command success depend on durable evidence.
- **Steps**:
  1. Add or reuse a status helper that appends an event and reads back the expected transition.
  2. Return a structured failure when the expected event is missing.
  3. Include mission id/slug, WP id, target lane, and event path when known.
- **Files**: `src/specify_cli/status/**`, `src/specify_cli/cli/commands/agent/tasks.py`.
- **Parallel?**: No.

### Subtask T010 – Resolve canonical event log from worktree paths
- **Purpose**: Ensure subagent/worktree invocations write to the right mission event log.
- **Steps**:
  1. Audit path resolution in transition command paths.
  2. Use existing repository root and mission resolver helpers.
  3. Add tests for root checkout and lane worktree contexts.
- **Files**: `src/specify_cli/status/**`, `src/specify_cli/cli/commands/agent/tasks.py`.
- **Parallel?**: No.

### Subtask T011 – Harden blocked event-emission diagnostics
- **Purpose**: Prevent dirty/unowned file checks from silently blocking event persistence.
- **Steps**:
  1. Identify preflight branches that can stop event writes.
  2. Convert hidden blocks into explicit hard failures with remediation.
  3. Preserve existing safety checks; only improve observability and exit status.
- **Files**: `src/specify_cli/status/**`, `src/specify_cli/cli/commands/agent/tasks.py`.
- **Parallel?**: No.

### Subtask T012 – Run targeted lifecycle tests
- **Purpose**: Prove the WP meets the release-blocker contract.
- **Steps**:
  1. Run status and task lifecycle tests.
  2. Add any focused regression assertions required by failures.
  3. Record commands and results in the Activity Log.
- **Files**: tests owned by this WP.
- **Parallel?**: No.

## Test Strategy

Run:

```bash
uv run pytest tests/status tests/tasks/test_move_task_git_validation_unit.py tests/unit/status/test_review_claim_transition.py -q
```

## Risks & Mitigations

- **Risk**: Readback checks introduce duplicated reducer behavior. Use existing status store/reducer helpers.
- **Risk**: Command JSON changes break consumers. Keep output additive and covered by tests.

## Integration Verification

Before marking this WP complete, verify:
- [ ] Successful transitions have corresponding durable events.
- [ ] Missing events produce non-zero command results.
- [ ] Worktree context resolves the canonical mission event log.
- [ ] #944 regression coverage passes.

## Review Guidance

Reviewers should focus on the atomicity invariant: success means durable event evidence, not merely an attempted mutation.

## Activity Log

**Initial entry**:
- 2026-05-02T08:10:17Z – system – Prompt created.
