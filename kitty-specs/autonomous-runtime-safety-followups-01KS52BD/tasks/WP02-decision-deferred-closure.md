---
work_package_id: WP02
title: Decision deferred closure
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: ''
history:
- at: '2026-05-21T10:53:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: runtime-riley
authoritative_surface: src/specify_cli/decisions/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/decisions/**
- src/specify_cli/cli/commands/decision.py
- src/specify_cli/acceptance/**
- tests/decisions/**
- tests/acceptance/**
- tests/cli/test_decision_deferred_closure.py
role: implementer
tags: []
---

# Work Package Prompt: WP02 - Decision deferred closure

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load runtime-riley
```

## Objective

Let missions close a planning-time deferred decision when the plan default is
accepted at terminus, without permanent verifier drift or acceptance blockage.

## Context

Issue #1256 reports `DECISION_TERMINAL_CONFLICT` for `deferred -> resolved`.
Removing the marker then produces `DEFERRED_WITHOUT_MARKER` drift. The preferred
fix is direct `deferred -> resolved` with an explicit final answer.

## Subtasks & Detailed Guidance

### T006 - Add transition regression

Cover open -> defer -> resolve through service or CLI, reproducing the current
terminal conflict.

### T007 - Implement explicit closure

Update the decision service/state handling so a deferred decision can be
resolved when a final answer/default rationale is provided.

### T008 - Update verifier

Teach `decision verify` that a closed decision no longer requires the inline
`[NEEDS CLARIFICATION]` marker.

### T009 - Update acceptance

Ensure acceptance clarification checks do not block on markers backed by closed
decisions.

### T010 - Verify

Run focused tests and mypy:

```bash
uv run pytest tests/decisions tests/acceptance tests/cli/test_decision_deferred_closure.py
uv run mypy --strict src/specify_cli/decisions src/specify_cli/acceptance src/specify_cli/cli/commands/decision.py
```

## Branch Strategy

Planning/base branch: `main`. Final merge target: `main`. Use the runtime
resolved lane workspace; do not create a separate branch manually.

## Definition of Done

- Deferred decision can be explicitly resolved.
- Removed marker does not cause verifier drift after closure.
- Acceptance gate does not report a closed clarification as outstanding.
- `open`, `defer`, and `cancel` contracts remain unchanged.

## Reviewer Guidance

Check that unresolved deferred decisions still require markers and still report
drift when appropriate.

## Activity Log

- 2026-05-21T10:53:40Z -- system -- Prompt created.
