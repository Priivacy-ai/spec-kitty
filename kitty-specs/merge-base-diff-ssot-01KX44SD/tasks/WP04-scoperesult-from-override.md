---
work_package_id: WP04
title: Secondary — ScopeResult.from_override tidy (deferrable)
dependencies:
- WP01
- WP02
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: fix/merge-base-diff-ssot
merge_target_branch: fix/merge-base-diff-ssot
branch_strategy: Planning artifacts for this mission were generated on fix/merge-base-diff-ssot. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-base-diff-ssot unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
phase: Phase 3 - Secondary
shell_pid: "2680664"
history:
- timestamp: '2026-07-09T20:30:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/
create_intent:
- tests/specify_cli/review/test_scope_result_from_override.py
execution_mode: code_change
mission_id: 01KX44SDZPWMA4N7RPKNR3TQT1
owned_files:
- src/specify_cli/review/pre_review_gate.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP04
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Do not touch code until the profile is loaded and acknowledged.

# Work Package Prompt: WP04 – ScopeResult.from_override tidy (deferrable)

## Objective

Retire the hand-built `ScopeResult` construction in `tasks_move_task`'s FR-004 override tier behind a `ScopeResult.from_override(targets)` classmethod. **This is a secondary, deferrable WP** — if it widens scope or fights the symbol-identity guard, defer it to a follow-up ticket rather than forcing it.

## Context & Constraints

- Depends on WP01 (mission foundation) and **WP02** (WP02 lands the `tasks_move_task` diff first; this WP then makes a small out-of-map edit to that file).
- Read `../spec.md` (FR-007) and `../plan.md` (IC-03, F7).
- **F7 (symbol-identity guard)**: `tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py` asserts `module_defs == set(_MOVE_SET)`. Do **NOT** add or remove any module-level symbol in `tasks_move_task.py` — the override-tier change must stay inside existing functions.

## Subtasks & Detailed Guidance

### Subtask T013 – Add `ScopeResult.from_override`
- File: `src/specify_cli/review/pre_review_gate.py`. Add a `from_override(cls, targets)` classmethod on `ScopeResult` that builds the same object the FR-004 override tier builds by hand today. Keep it a pure constructor — no gate-policy change.

### Subtask T014 – Use it in the override tier (out-of-map edit)
- File: `src/specify_cli/cli/commands/agent/tasks_move_task.py` (owned by WP02 — this is a **documented out-of-map edit**, justified: it is the consumer of the new classmethod and cannot live elsewhere).
- Replace the hand-built `ScopeResult(...)` construction in the FR-004 override tier with `ScopeResult.from_override(targets)`. Change nothing else; add no module-level symbol (respect `_MOVE_SET`).

### Subtask T015 – Tests
- New file `tests/specify_cli/review/test_scope_result_from_override.py`: assert `from_override` yields a `ScopeResult` equal to the hand-built form.
- Run `test_tasks_move_task_seam.py` and confirm the `module_defs == _MOVE_SET` guard is still green.

## Branch Strategy

- Planning/base = merge target = `fix/merge-base-diff-ssot`. `spec-kitty agent action implement WP04 --agent <name>` (depends on WP01, WP02).

## Definition of Done

- [ ] `ScopeResult.from_override` added; override tier uses it; no gate-policy change.
- [ ] No module-level symbol added/removed in `tasks_move_task.py`; `_MOVE_SET` guard green.
- [ ] `from_override` unit test green; ruff + mypy clean.
- [ ] If deferred: WP closed with rationale and a follow-up ticket filed instead.

## Risks & Reviewer Guidance

- Reviewer: confirm this is pure tidy (no behaviour change to the override tier's scoping). Confirm the out-of-map `tasks_move_task` edit is minimal and adds no module-level symbol.

## Activity Log

- 2026-07-09T23:22:02Z – claude:sonnet:python-pedro:implementer – shell_pid=2624934 – Assigned agent via action command
- 2026-07-09T23:30:18Z – claude:sonnet:python-pedro:implementer – shell_pid=2624934 – Pure tidy: from_override classmethod; override tier repointed; no module-level symbol change (_MOVE_SET guard green); ruff exit 0
- 2026-07-09T23:32:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=2680664 – Started review via action command
