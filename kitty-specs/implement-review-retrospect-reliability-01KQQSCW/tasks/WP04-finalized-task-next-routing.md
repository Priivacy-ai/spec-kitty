---
work_package_id: WP04
title: Finalized Task Next Routing
dependencies: []
requirement_refs:
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
history:
- at: '2026-05-03T20:58:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/next/decision.py
- tests/next/test_finalized_task_routing.py
priority: P1
tags: []
---

# Work Package Prompt: WP04 - Finalized Task Next Routing

## Objective

Ensure `spec-kitty next` routes from finalized task board and WP lane state instead of stale discovery-phase runtime state.

## Branch Strategy

- Planning/base branch at prompt creation: `main`
- Final merge target for completed work: `main`
- Execution workspace is resolved later by the implement action.

## Context

- Contract: `contracts/next-routing.md`
- Existing code: `src/specify_cli/next/runtime_bridge.py` and `src/specify_cli/next/decision.py`
- Preserve the public `Decision` JSON contract and prompt-file invariant.

## Subtasks

### T015 - Add finalized-task routing fixture

Create a fixture mission with `spec.md`, `plan.md`, `tasks.md`, `tasks/WP*.md`, canonical status events, and stale discovery runtime state.

### T016 - Prefer finalized WP lane state

Adjust next-routing logic so finalized task/WP state overrides stale early mission phase state for implement-review flow.

### T017 - Cover routing outcomes

Test implementable WPs, reviewable WPs, approved/done WPs, blocked WPs, and terminal/completion states.

### T018 - Preserve JSON and prompt invariants

Assert `Decision` output shape remains compatible and `kind="step"` still includes a resolvable prompt file.

## Definition of Done

- [ ] Finalized fixtures never route to discovery solely because stale phase state says discovery.
- [ ] Existing next tests still pass for non-finalized paths.

## Risks

- Runtime changes can affect custom missions. Keep the override narrowly gated on finalized software-dev task/WP state.

## Implementation Command

```bash
spec-kitty agent action implement WP04 --agent <name>
```
