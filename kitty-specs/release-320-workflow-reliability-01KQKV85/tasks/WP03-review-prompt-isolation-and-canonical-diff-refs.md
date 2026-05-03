---
work_package_id: WP03
title: Review Prompt Isolation and Canonical Diff Refs
dependencies:
- WP01
requirement_refs:
- C-004
- C-005
- FR-004
- FR-005
- FR-006
- FR-014
- NFR-001
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Review Correctness
assignee: ''
agent: "codex:gpt-5.3-codex:reviewer-renata:reviewer"
shell_pid: "83940"
history:
- at: '2026-05-02T08:10:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/**
- src/specify_cli/cli/commands/agent/workflow.py
- tests/review/**
- tests/integration/review/**
role: implementer
tags: []
---

# Work Package Prompt: WP03 – Review Prompt Isolation and Canonical Diff Refs

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

Fix #949 and #950, and provide review-artifact verdict helper coverage needed by #904. Review prompts must be unique per repo, mission, WP, worktree, and invocation. Review dispatch must fail closed if prompt metadata mismatches the requested work.

## Context & Constraints

- Contract: `kitty-specs/release-320-workflow-reliability-01KQKV85/contracts/review-prompt-metadata.yaml`
- Owned source: `src/specify_cli/review/**`, `src/specify_cli/cli/commands/agent/workflow.py`
- WP06 owns merge/ship consumption of review artifact consistency checks; this WP owns review internals and helper surfaces.

## Subtasks & Detailed Guidance

### Subtask T013 – Add concurrent review prompt tests
- **Purpose**: Reproduce #949 with deterministic concurrency shapes.
- **Steps**:
  1. Use WP01 fixtures to build two repo roots and two mission identities.
  2. Generate review prompts for same-second or same-WP-like scenarios.
  3. Assert no file collision and no stale prompt reuse.
- **Files**: `tests/review/**`, `tests/integration/review/**`.
- **Parallel?**: Yes.

### Subtask T014 – Add mission-prefixed slug diff regression
- **Purpose**: Reproduce #950.
- **Steps**:
  1. Create a mission slug beginning with `mission-`.
  2. Exercise review diff generation.
  3. Assert diff refs come from canonical state, not reconstructed slug strings.
- **Files**: `tests/review/**`, `tests/integration/review/**`.
- **Parallel?**: Yes.

### Subtask T015 – Implement invocation-specific prompt metadata
- **Purpose**: Bind review prompt artifacts to the requested work.
- **Steps**:
  1. Add structured metadata fields listed in the contract.
  2. Store prompt files in invocation-specific paths.
  3. Include repo root, mission id/slug, WP id, worktree path, branch refs, base ref, and invocation id.
- **Files**: `src/specify_cli/review/**`, `src/specify_cli/cli/commands/agent/workflow.py`.
- **Parallel?**: No.

### Subtask T016 – Add fail-closed validation before dispatch
- **Purpose**: Prevent wrong prompt dispatch.
- **Steps**:
  1. Validate prompt metadata against requested context immediately before reviewer launch.
  2. On mismatch, return a diagnostic containing requested context and prompt context.
  3. Do not fall back to silently dispatching a mismatched prompt.
- **Files**: `src/specify_cli/review/**`, `src/specify_cli/cli/commands/agent/workflow.py`.
- **Parallel?**: No.

### Subtask T017 – Use canonical refs for review diffs
- **Purpose**: Remove slug reconstruction from diff command construction.
- **Steps**:
  1. Identify current diff command construction.
  2. Replace reconstructed refs with canonical mission/lane/workspace refs.
  3. Preserve user-facing command readability while fixing identity source.
- **Files**: `src/specify_cli/review/**`, `src/specify_cli/cli/commands/agent/workflow.py`.
- **Parallel?**: No.

### Subtask T018 – Add latest review artifact helper coverage
- **Purpose**: Provide a review-owned helper for WP06 consistency gates.
- **Steps**:
  1. Add or harden helper logic that reads latest `review-cycle-N.md` frontmatter.
  2. Cover `verdict: rejected` versus approved/done WP state.
  3. Keep the helper free of merge-specific policy decisions.
- **Files**: `src/specify_cli/review/**`, `tests/review/**`.
- **Parallel?**: No.

## Test Strategy

Run:

```bash
uv run pytest tests/review tests/integration/review -q
```

## Risks & Mitigations

- **Risk**: New metadata breaks existing prompt consumers. Keep validation attached to generated prompt dispatch and provide precise diagnostics.
- **Risk**: Branch refs remain partially reconstructed. Tests must include `mission-` prefixed slugs.

## Integration Verification

Before marking this WP complete, verify:
- [ ] Prompt paths are collision-proof.
- [ ] Metadata mismatches fail closed.
- [ ] Diff commands use canonical refs.
- [ ] Latest review artifact helper is covered and ready for WP06.

## Review Guidance

Reviewers should inspect identity boundaries carefully. The key question is whether a reviewer could still be dispatched against the wrong repo, mission, WP, or worktree.

## Activity Log

**Initial entry**:
- 2026-05-02T08:10:17Z – system – Prompt created.
- 2026-05-03T13:46:11Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Started implementation via action command
- 2026-05-03T13:55:00Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Ready for review: review prompt metadata isolation, canonical review diff refs, and latest verdict helper coverage
- 2026-05-03T13:57:06Z – codex:gpt-5.3-codex:reviewer-renata:reviewer – shell_pid=83940 – Started review via action command
- 2026-05-03T14:04:39Z – codex:gpt-5.3-codex:reviewer-renata:reviewer – shell_pid=83940 – Changes requested: see review-cycle-1.md
- 2026-05-03T14:05:44Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Started implementation via action command
- 2026-05-03T14:07:19Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Moved to for_review
- 2026-05-03T14:08:10Z – codex:gpt-5.3-codex:reviewer-renata:reviewer – shell_pid=83940 – Started review via action command
