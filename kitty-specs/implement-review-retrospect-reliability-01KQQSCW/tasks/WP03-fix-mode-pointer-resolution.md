---
work_package_id: WP03
title: Fix-Mode Pointer Resolution
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
agent: "codex:gpt-5:default:reviewer"
shell_pid: "5378"
history:
- at: '2026-05-03T20:58:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- tests/agent/test_workflow_review_cycle_pointer.py
priority: P1
tags: []
---

# Work Package Prompt: WP03 - Fix-Mode Pointer Resolution

## Objective

Make implement/fix-mode prompt loading resolve review feedback through the same shared pointer boundary used by rejection persistence.

## Branch Strategy

- Planning/base branch at prompt creation: `main`
- Final merge target for completed work: `main`
- Execution workspace is resolved later by the implement action.

## Context

- Depends on WP01's pointer resolver.
- Existing surface: `src/specify_cli/cli/commands/agent/workflow.py`
- Fix-mode must load the focused rejection context from canonical `review-cycle://...` pointers.

## Subtasks

### T011 - Route fix-mode resolution through shared resolver

Replace local pointer parsing with the shared resolver. Keep prompt rendering behavior focused on the resolved artifact content and warning list.

### T012 - Preserve sentinel and warning behavior

Continue to ignore `force-override` and `action-review-claim` as operational sentinels. Warn when a legacy `feedback://` pointer is used or when a pointer cannot be resolved.

### T013 - Add prompt tests for canonical and legacy pointers

Add active 3.x tests in `tests/agent/test_workflow_review_cycle_pointer.py`. Avoid relying on branch-gated 2.x tests for new coverage.

### T014 - Add focused context loading regression

Assert the generated implement/fix prompt includes the rejected review-cycle body and does not include `action-review-claim` as feedback context.

## Definition of Done

- [ ] Fix-mode loads canonical review-cycle feedback.
- [ ] Legacy pointers warn but remain readable.
- [ ] Operational sentinels are not mistaken for feedback.

## Risks

- Existing prompt tests may use legacy "feature" wording. Keep new user-facing text aligned to Mission terminology.

## Implementation Command

```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Activity Log

- 2026-05-03T21:40:49Z – codex:gpt-5:default:implementer – shell_pid=4888 – Started implementation via action command
- 2026-05-03T21:40:53Z – codex:gpt-5:default:implementer – shell_pid=4888 – Ready for review
- 2026-05-03T21:40:55Z – codex:gpt-5:default:reviewer – shell_pid=5378 – Started review via action command
- 2026-05-03T21:40:57Z – codex:gpt-5:default:reviewer – shell_pid=5378 – Review passed: fix-mode pointer tests passed
