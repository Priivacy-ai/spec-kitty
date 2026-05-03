---
work_package_id: WP01
title: Regression Harness and Workflow Fixtures
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- C-006
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-release-320-workflow-reliability-01KQKV85
base_commit: 35a2f79ee4aa3ed1737fff8996f64bf820f107bf
created_at: '2026-05-02T08:31:36.083678+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Regression Foundation
assignee: ''
agent: "codex"
shell_pid: '83940'
history:
- at: '2026-05-02T08:10:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/reliability/
execution_mode: code_change
model: ''
owned_files:
- tests/reliability/fixtures/**
- tests/reliability/test_workflow_fixture_smoke.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 – Regression Harness and Workflow Fixtures

## ⚡ Do This First: Load Agent Profile

Before reading further or changing files, load the assigned agent profile:

```text
/ad-hoc-profile-load python-pedro
```

Use that profile's implementation discipline for the rest of this WP.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` decides the lane workspace path and records the lane branch in `base_branch`. Sequential WPs in the same lane reuse the same worktree.
- **If the resolved workspace differs from your expectation**: trust the path printed by `spec-kitty agent workflow implement/review`; do not manually create a different worktree.

## Objectives & Success Criteria

Create a small deterministic reliability fixture layer under `tests/reliability/` that later WPs can reuse for status events, work-package files, review artifacts, sync failure fakes, and branch/preflight scenarios.

Success means:
- Fixture helpers can build a temporary mission directory with realistic `meta.json`, `status.events.jsonl`, `tasks/WP*.md`, review artifacts, and optional workspace context.
- The helpers do not call real hosted services.
- A smoke test proves all planned blocker scenario shapes are representable.

## Context & Constraints

- Primary spec: `kitty-specs/release-320-workflow-reliability-01KQKV85/spec.md`
- Plan: `kitty-specs/release-320-workflow-reliability-01KQKV85/plan.md`
- Contracts: `kitty-specs/release-320-workflow-reliability-01KQKV85/contracts/`
- Machine rule: command paths that exercise SaaS, tracker, hosted auth, or sync behavior must use `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, but this WP should use mocks/fakes rather than real network calls.
- Keep ownership limited to `tests/reliability/**`.

## Subtasks & Detailed Guidance

### Subtask T001 – Create shared reliability fixture helpers
- **Purpose**: Give later WPs a reusable way to create workflow states without copying setup code.
- **Steps**:
  1. Add a new helper module under `tests/reliability/fixtures/`.
  2. Include builders for repository root, mission directory, tasks directory, and basic `meta.json`.
  3. Prefer simple dataclasses or small functions over a large fixture framework.
- **Files**: `tests/reliability/fixtures/`.
- **Parallel?**: No. This defines the base shape.

### Subtask T002 – Add mission/work-package fixture builders
- **Purpose**: Support transition, ownership, review, and merge tests with realistic WP files.
- **Steps**:
  1. Add helpers to write `tasks/WP01-*.md` with YAML frontmatter.
  2. Support `work_package_id`, `dependencies`, `owned_files`, `authoritative_surface`, `execution_mode`, and `requirement_refs`.
  3. Add helpers to append status events and reduce/materialize when needed through existing status APIs.
- **Files**: `tests/reliability/fixtures/`.
- **Parallel?**: No, depends on T001.

### Subtask T003 – Add sync-failure fakes
- **Purpose**: Let WP05 test final-sync failures after local success without network calls.
- **Steps**:
  1. Provide fake emitter/client objects that can raise controlled lock, shutdown, and transport diagnostics.
  2. Include a way to assert whether stdout remains parseable separately from stderr diagnostics.
  3. Do not import SaaS app code.
- **Files**: `tests/reliability/fixtures/`.
- **Parallel?**: Yes, after T001.

### Subtask T004 – Add review prompt collision fixtures
- **Purpose**: Let WP03 test concurrent prompt generation deterministically.
- **Steps**:
  1. Add helpers for two temporary repo roots and two mission identities.
  2. Include fixed timestamps/invocation ids to force same-second prompt scenarios.
  3. Include a helper to assert prompt metadata identity.
- **Files**: `tests/reliability/fixtures/`.
- **Parallel?**: Yes, after T001.

### Subtask T005 – Add fixture smoke test
- **Purpose**: Prove the harness can support every blocker without touching production code.
- **Steps**:
  1. Add `tests/reliability/test_workflow_fixture_smoke.py`.
  2. Exercise builders for status events, review artifacts, sync fakes, shared-lane ownership context, and branch divergence state.
  3. Keep smoke assertions focused on fixture output shape.
- **Files**: `tests/reliability/test_workflow_fixture_smoke.py`.
- **Parallel?**: No, after T002-T004.

### Subtask T006 – Document fixture contracts and sync flag rule
- **Purpose**: Make fixture usage obvious to later WPs.
- **Steps**:
  1. Add concise module docstrings or README text under `tests/reliability/fixtures/`.
  2. Mention that hosted sync tests should be mocked unless explicitly scoped.
  3. Mention the local `SPEC_KITTY_ENABLE_SAAS_SYNC=1` rule for command paths that touch sync.
- **Files**: `tests/reliability/fixtures/`.
- **Parallel?**: No.

## Test Strategy

Run:

```bash
uv run pytest tests/reliability -q
```

## Risks & Mitigations

- **Risk**: Fixture code duplicates production state logic. Prefer calling existing status helpers instead of reimplementing reducers.
- **Risk**: Later WPs need extra helper shape. Keep helpers easy to extend but avoid speculative abstractions.

## Integration Verification

Before marking this WP complete, verify:
- [ ] `uv run pytest tests/reliability -q` passes.
- [ ] No production source files were changed.
- [ ] No real network calls are made.
- [ ] Fixture helper names make the intended workflow state clear.

## Review Guidance

Reviewers should check that the fixture layer is narrow, deterministic, and genuinely reusable by WP02-WP06.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Initial entry**:
- 2026-05-02T08:10:17Z – system – Prompt created.
- 2026-05-03T12:25:45Z – codex – shell_pid=83940 – Implemented regression harness fixtures and verified with uv run pytest tests/reliability -q
