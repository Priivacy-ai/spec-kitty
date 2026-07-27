---
work_package_id: WP04
title: resolve_primary_branch consolidation
dependencies: []
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: feat/terminology-primary-merge-disambiguation
merge_target_branch: feat/terminology-primary-merge-disambiguation
branch_strategy: Planning artifacts for this mission were generated on feat/terminology-primary-merge-disambiguation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/terminology-primary-merge-disambiguation unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
phase: Phase 2 - Safe code
assignee: ''
shell_pid_created_at: "1784231120.45"
agent: "claude"
shell_pid: "1204296"
history:
- at: '2026-07-16T18:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/git_ops.py
- src/specify_cli/cli/commands/agent/tasks_shared.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/mission_branch_context.py
- tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py
- tests/specify_cli/cli/commands/agent/test_mission_branch_context.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – resolve_primary_branch consolidation

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` via `/ad-hoc-profile-load`. ATDD red-first.

## Objectives & Success Criteria
- ONE canonical `resolve_primary_branch` behavior (`core/git_ops.py:270`); NAME unchanged (D1).
- Resolve the `tasks_shared.py:56` delegating shim (keep-as-explicit-compat OR remove) + update `tasks.py.__all__` + `test_tasks_compat_surface` in lockstep.
- Fold `_resolve_primary_branch_for_recommendation` (`mission_branch_context.py:197`) into the canonical via a `bias` param, OR scope it out with a recorded rationale — no unremarked third re-implementation.

## Context & Constraints
- Squad correction: `tasks_shared` is NOT a divergent copy — it delegates. The real duplicate is the recommendation resolver (which has a deliberate no-feature-bias behavior that MUST be preserved).
- EXEMPT: the NAME `resolve_primary_branch` (D1) and `resolve_merge_target_branch`.

## Subtasks & Detailed Guidance
### T013 – Red-first: pin canonical behavior + recommendation no-feature-bias behavior (failing/characterization tests).
### T014 – Resolve the shim; update `tasks.py.__all__` + `test_tasks_compat_surface` (the pinned compat contract).
### T015 – Fold `_resolve_primary_branch_for_recommendation` via a **`bias` param with a backward-compatible default** (preferred — keeps signature + name stable), OR scope-out with rationale. **Constraint: keep `resolve_primary_branch`'s signature backward-compatible** so `orchestrator_api/commands.py:866-869` (owned by WP05) needs no change. **Caveat: if the recommendation name is REMOVED (not kept as a delegating wrapper), also update the re-export at `src/specify_cli/cli/commands/agent/mission.py:206` + `test_mission_shim_reexports.py`** — the guided `bias`-param path keeps the name and avoids this.
### T016 – Green: `test_git_ops`, `test_tasks_compat_surface`, `test_mission_branch_context` (red-first pin from T013 lands here); `ruff` + `mypy --strict`.

## Test Strategy
- `uv run pytest -k "git_ops or tasks_compat_surface or mission_branch_context"`; ATDD red before green.

## Risks & Mitigations
- Compat contract must move in lockstep; do not flatten the no-feature-bias branch of the recommendation path.

## Review Guidance
- One real def; compat surface honest; recommendation behavior preserved or explicitly scoped-out.

## Activity Log
- 2026-07-16T18:15:00Z – system – Prompt created.
- 2026-07-16T19:07:15Z – claude – shell_pid=1077138 – Assigned agent via action command
- 2026-07-16T19:26:53Z – claude – shell_pid=1077138 – Resolver consolidated; compat guard updated
- 2026-07-16T19:37:30Z – user – Moved to planned
- 2026-07-16T19:38:27Z – claude – shell_pid=1176481 – Started implementation via action command
- 2026-07-16T19:42:20Z – claude – shell_pid=1176481 – Addressed review-cycle-1: wrapped line-214 delegating return in str(); mypy now clean on owned lines (only pre-existing line-337 remains, unowned)
- 2026-07-16T19:45:27Z – claude – shell_pid=1204296 – Started review via action command
- 2026-07-16T19:45:55Z – user – shell_pid=1204296 – cycle-2: str-wrap fix verified (line 214 only); mypy no-any-return 2->1 (residual line 337 pre-existing/unowned); ruff clean; 602 tests green; approved
