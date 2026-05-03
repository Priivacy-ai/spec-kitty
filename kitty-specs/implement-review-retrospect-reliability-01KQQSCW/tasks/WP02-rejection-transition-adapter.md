---
work_package_id: WP02
title: Rejection Transition Adapter
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-006
- FR-007
- NFR-001
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "codex:gpt-5:default:implementer"
shell_pid: "3912"
history:
- at: '2026-05-03T20:58:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- tests/integration/review/test_reject_from_in_review.py
- tests/status/test_transitions.py
- tests/status/test_emit.py
priority: P0
tags: []
---

# Work Package Prompt: WP02 - Rejection Transition Adapter

## Objective

Make normal reviewer rejection from `in_review` work through `spec-kitty agent tasks move-task` without manual lower-level repair.

## Branch Strategy

- Planning/base branch at prompt creation: `main`
- Final merge target for completed work: `main`
- Actual execution workspace is resolved later by the implement action.

## Context

- Depends on WP01's `specify_cli.review.cycle` boundary.
- Primary code surface: `src/specify_cli/cli/commands/agent/tasks.py`
- Status guard already requires `review_result` for outbound `in_review` transitions.

## Subtasks

### T006 - Replace local artifact creation

Replace the current rejection artifact write path in `tasks.py` with the shared WP01 boundary. Keep `_persist_review_feedback` only as a compatibility wrapper if needed, but route its behavior through the shared module.

### T007 - Derive rejected `ReviewResult` before mutation

Before calling `emit_status_transition`, derive a rejected `ReviewResult` whose reference is the canonical pointer. Pass both `review_ref` and `review_result` into `TransitionRequest`.

### T008 - Add fail-before-mutation regressions

Test missing feedback file, empty feedback file, and invalid artifact cases. Each failure must leave the status event log unchanged and return an actionable diagnostic.

### T009 - Add `in_review -> planned` integration coverage

Build or adapt a CLI fixture that moves a WP to `in_review`, then rejects it with `--review-feedback-file`. Assert the event carries the canonical pointer and the transition succeeds without `--force`.

### T010 - Run targeted status tests

Run and fix targeted regressions in:

```bash
uv run pytest tests/status/test_transitions.py tests/status/test_emit.py tests/integration/review/test_reject_from_in_review.py -q
```

## Definition of Done

- [ ] #960 rejection works from `in_review` with normal CLI surface.
- [ ] Invalid feedback fails before artifact or status mutation.
- [ ] Existing approval/done paths still pass targeted tests.

## Risks

- Approval transitions must not inherit rejection-only behavior.

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent <name>
```

## Activity Log

- 2026-05-03T21:40:32Z – codex:gpt-5:default:implementer – shell_pid=3912 – Started implementation via action command
- 2026-05-03T21:40:36Z – codex:gpt-5:default:implementer – shell_pid=3912 – Ready for review
