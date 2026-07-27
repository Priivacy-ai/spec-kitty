---
work_package_id: WP06
title: Merge/Ship Preflight and Review Artifact Consistency
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- C-004
- C-005
- FR-012
- FR-013
- FR-014
- NFR-001
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
phase: Phase 3 - Release Readiness
assignee: ''
agent: "codex:gpt-5.3-codex:reviewer-renata:reviewer"
shell_pid: "83940"
history:
- at: '2026-05-02T08:10:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/**
- src/specify_cli/post_merge/**
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/cli/commands/merge_driver.py
- src/specify_cli/cli/commands/review.py
- tests/merge/**
- tests/post_merge/**
- tests/integration/test_mission_review_contract_gate.py
- tests/integration/test_merge_resume.py
role: implementer
tags: []
---

# Work Package Prompt: WP06 – Merge/Ship Preflight and Review Artifact Consistency

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

Fix #953 and #904 release-readiness surfaces. Merge/ship must detect diverged local `main` before unsafe continuation and must not silently sign off approved/done WPs whose latest review artifact still says `verdict: rejected`.

## Context & Constraints

- Contract: `kitty-specs/release-320-workflow-reliability-01KQKV85/contracts/merge-ship-preflight.yaml`
- Owned source: merge, post-merge, merge command, merge driver, and review command surfaces listed in frontmatter.
- Use review helper surfaces from WP03 for latest review artifact parsing; do not duplicate review internals in merge code.

## Subtasks & Detailed Guidance

### Subtask T031 – Add diverged target branch tests
- **Purpose**: Reproduce #953.
- **Steps**:
  1. Simulate local `main` ahead and behind `origin/main`.
  2. Run merge/ship preflight path.
  3. Assert unsafe continuation is blocked before branch reconstruction is left to the agent.
- **Files**: `tests/merge/**`, `tests/integration/test_merge_resume.py`.
- **Parallel?**: Yes.

### Subtask T032 – Add rejected review artifact consistency tests
- **Purpose**: Reproduce #904.
- **Steps**:
  1. Create approved and done WP state.
  2. Add latest `review-cycle-N.md` frontmatter with `verdict: rejected`.
  3. Assert mission-review or ship signoff warns hard or fails before acceptance.
- **Files**: `tests/post_merge/**`, `tests/integration/test_mission_review_contract_gate.py`.
- **Parallel?**: Yes.

### Subtask T033 – Implement branch divergence detection
- **Purpose**: Stop unsafe merge/ship early.
- **Steps**:
  1. Compare local target branch with its remote tracking branch.
  2. Detect ahead, behind, and diverged states.
  3. Use actual `merge_target_branch`, not a generic default.
- **Files**: `src/specify_cli/merge/**`, `src/specify_cli/cli/commands/merge.py`, `src/specify_cli/cli/commands/merge_driver.py`.
- **Parallel?**: No.

### Subtask T034 – Add focused PR branch remediation guidance
- **Purpose**: Give operators deterministic recovery when local target is unsafe.
- **Steps**:
  1. Derive or describe a focused PR branch path from mission-owned files/commits.
  2. Include exact diagnostic language and next steps.
  3. Avoid destructive git operations.
- **Files**: merge modules owned by this WP.
- **Parallel?**: No.

### Subtask T035 – Integrate review artifact consistency checks
- **Purpose**: Block stale rejected verdicts before signoff.
- **Steps**:
  1. Use WP03 review helper for latest artifact verdict.
  2. Check approved/done canonical state against latest rejected verdict.
  3. Fail or warn hard with mission/WP/artifact path diagnostics.
- **Files**: `src/specify_cli/post_merge/**`, `src/specify_cli/cli/commands/review.py`, merge command surfaces.
- **Parallel?**: No.

### Subtask T036 – Run merge/post-merge integration tests
- **Purpose**: Prove release-readiness gates work together.
- **Steps**:
  1. Run targeted merge/post-merge tests.
  2. Add final smoke expectations if gaps remain.
  3. Record commands and results in Activity Log.
- **Files**: tests owned by this WP.
- **Parallel?**: No.

## Test Strategy

Run:

```bash
uv run pytest tests/merge tests/post_merge tests/integration/test_mission_review_contract_gate.py tests/integration/test_merge_resume.py -q
```

## Risks & Mitigations

- **Risk**: Preflight blocks legitimate work with vague output. Provide deterministic remediation.
- **Risk**: Review artifact parsing drifts from review internals. Consume helper from WP03.

## Integration Verification

Before marking this WP complete, verify:
- [ ] Diverged local `main` is detected before unsafe merge/ship continuation.
- [ ] Focused PR branch remediation is deterministic.
- [ ] Latest rejected review artifact cannot silently coexist with approved/done signoff.

## Review Guidance

Reviewers should inspect failure diagnostics and make sure they are actionable without manual branch reconstruction.

## Activity Log

**Initial entry**:
- 2026-05-02T08:10:17Z – system – Prompt created.
- 2026-05-03T15:16:04Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Started implementation via action command
- 2026-05-03T15:24:46Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Ready for review: merge target sync preflight and review artifact consistency gates implemented
- 2026-05-03T15:27:03Z – codex:gpt-5.3-codex:reviewer-renata:reviewer – shell_pid=83940 – Started review via action command
- 2026-05-03T15:33:43Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Started implementation via action command
- 2026-05-03T15:38:31Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Ready for review: stable preflight diagnostic contract fields added
- 2026-05-03T15:39:50Z – codex:gpt-5.3-codex:reviewer-renata:reviewer – shell_pid=83940 – Started review via action command
- 2026-05-03T15:42:00Z – codex:gpt-5.3-codex:reviewer-renata:reviewer – shell_pid=83940 – Review passed: stable diagnostic contract fields verified for branch preflight and rejected review artifact conflicts
