---
work_package_id: WP04
title: Active WP Ownership Guard
dependencies:
- WP01
requirement_refs:
- C-004
- FR-007
- FR-008
- NFR-001
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
phase: Phase 2 - Ownership Safety
assignee: ''
agent: codex
history:
- at: '2026-05-02T08:10:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/policy/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/policy/commit_guard.py
- src/specify_cli/policy/commit_guard_hook.py
- src/specify_cli/workspace/context.py
- src/specify_cli/ownership/**
- tests/policy/test_commit_guard.py
- tests/tasks/test_pre_commit_wp_guard_unit.py
- tests/runtime/test_workspace_context_unit.py
role: implementer
tags: []
---

# Work Package Prompt: WP04 – Active WP Ownership Guard

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

Fix #951. Ownership guards must validate against the active WP's `owned_files`, especially when a shared lane moves from one WP to another with disjoint file ownership.

## Context & Constraints

- Owned source: `src/specify_cli/policy/commit_guard.py`, `src/specify_cli/policy/commit_guard_hook.py`, `src/specify_cli/workspace/context.py`, `src/specify_cli/ownership/**`
- Do not broaden ownership globs to make tests pass.
- Guard output must distinguish stale/ambiguous context from a true out-of-scope file change.

## Subtasks & Detailed Guidance

### Subtask T019 – Add shared-lane ownership tests
- **Purpose**: Reproduce #951.
- **Steps**:
  1. Create a lane context where WP01 completed and WP04 becomes active.
  2. Give the two WPs disjoint `owned_files`.
  3. Assert the guard uses WP04 ownership after the lane advances.
- **Files**: `tests/policy/test_commit_guard.py`, `tests/tasks/test_pre_commit_wp_guard_unit.py`, `tests/runtime/test_workspace_context_unit.py`.
- **Parallel?**: Yes.

### Subtask T020 – Add stale-context diagnostic tests
- **Purpose**: Make guard failures actionable.
- **Steps**:
  1. Test true scope violation output.
  2. Test stale or ambiguous context output.
  3. Ensure diagnostics include active WP evidence when known.
- **Files**: policy/workspace tests owned by this WP.
- **Parallel?**: Yes.

### Subtask T021 – Resolve active WP id at guard time
- **Purpose**: Avoid stale lane-level assumptions.
- **Steps**:
  1. Audit current active WP resolution from workspace/status context.
  2. Resolve active WP during each guard invocation.
  3. Prefer canonical status/workspace state over branch-name inference.
- **Files**: `src/specify_cli/workspace/context.py`, `src/specify_cli/ownership/**`.
- **Parallel?**: No.

### Subtask T022 – Update commit guard ownership detection
- **Purpose**: Feed active WP ownership to existing validation.
- **Steps**:
  1. Read active WP frontmatter for `owned_files`.
  2. Preserve existing no-owned-files fallback behavior only when context is truly absent.
  3. Keep hook output concise but precise.
- **Files**: `src/specify_cli/policy/commit_guard.py`, `src/specify_cli/policy/commit_guard_hook.py`.
- **Parallel?**: No.

### Subtask T023 – Add stale/ambiguous context diagnostics
- **Purpose**: Make stale context separate from scope violation.
- **Steps**:
  1. Add stable diagnostic language or codes.
  2. Include lane id, active WP id, and context source when known.
  3. Avoid using stale ownership as authoritative after detecting ambiguity.
- **Files**: policy/workspace/ownership modules owned by this WP.
- **Parallel?**: No.

### Subtask T024 – Run policy/workspace tests
- **Purpose**: Verify guard behavior across old and new paths.
- **Steps**:
  1. Run targeted tests.
  2. Fix regressions without weakening guard policy.
  3. Record commands and results in Activity Log.
- **Files**: tests owned by this WP.
- **Parallel?**: No.

## Test Strategy

Run:

```bash
uv run pytest tests/policy/test_commit_guard.py tests/tasks/test_pre_commit_wp_guard_unit.py tests/runtime/test_workspace_context_unit.py -q
```

## Risks & Mitigations

- **Risk**: Guard context resolution becomes too permissive. Fail closed with a context diagnostic when active WP cannot be proven.
- **Risk**: Existing WPs without ownership metadata break. Preserve documented fallback behavior only for absent context, not stale context.

## Integration Verification

Before marking this WP complete, verify:
- [ ] Shared-lane sequential WP scenario uses current WP ownership.
- [ ] Stale context is diagnosed separately.
- [ ] True scope violations still block.

## Review Guidance

Reviewers should inspect whether the guard is using current state at invocation time, not cached or previous WP metadata.

## Activity Log

**Initial entry**:
- 2026-05-02T08:10:17Z – system – Prompt created.
