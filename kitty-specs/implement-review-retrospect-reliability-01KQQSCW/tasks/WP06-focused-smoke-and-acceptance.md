---
work_package_id: WP06
title: Focused Smoke and Acceptance
dependencies:
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-011
- NFR-001
- NFR-002
- NFR-005
- NFR-006
- C-001
- C-002
- C-004
- C-005
- C-006
- C-007
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
agent: "codex:gpt-5:default:reviewer"
shell_pid: "8290"
history:
- at: '2026-05-03T20:58:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/integration/
execution_mode: code_change
owned_files:
- tests/integration/test_implement_review_retrospect_smoke.py
- kitty-specs/implement-review-retrospect-reliability-01KQQSCW/quickstart.md
priority: P2
tags: []
---

# Work Package Prompt: WP06 - Focused Smoke and Acceptance

## Objective

Prove the full implement-review-retrospect control loop works and keep optional issues explicitly scoped.

## Branch Strategy

- Planning/base branch at prompt creation: `main`
- Final merge target for completed work: `main`
- Execution workspace is resolved later by the implement action.

## Context

- This WP runs after WP02, WP03, WP04, and WP05.
- It owns only the final smoke test and quickstart adjustments for changed verification commands.

## Subtasks

### T023 - Build focused end-to-end smoke fixture

Create a temporary mission fixture covering:

1. Finalized tasks.
2. WP enters review.
3. Rejection with feedback file.
4. Valid review-cycle artifact and canonical pointer.
5. Fix-mode context loading.
6. Approval or completion.
7. `spec-kitty next` routing from task/WP state.
8. Retrospective path on completed mission.

### T024 - Verify optional issue scope

Confirm #967, #966, #964, and #968 remain deferred unless a small adjacent fix was included by an earlier WP. If any was included, document why and which tests cover it.

### T025 - Run acceptance tests

Run the targeted acceptance set from `quickstart.md`. Update the quickstart if implementation changed exact test file names.

### T026 - Record local sync rationale

For purely local fixtures, document that SaaS sync is out of scope and that commands may run with `SPEC_KITTY_ENABLE_SAAS_SYNC=0`. If any acceptance path touches hosted auth, tracker, SaaS sync, or sync finalization on this computer, run it with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

## Definition of Done

- [ ] Focused smoke passes.
- [ ] Optional issue decisions are explicit.
- [ ] Quickstart verification commands match the implemented test files.
- [ ] No broad test-runner rewrite was introduced for #967.

## Risks

- This WP can become a dumping ground. Keep it to smoke and acceptance; production fixes belong in WP01-WP05.

## Implementation Command

```bash
spec-kitty agent action implement WP06 --agent <name>
```

## Activity Log

- 2026-05-03T21:41:44Z – codex:gpt-5:default:implementer – shell_pid=7795 – Started implementation via action command
- 2026-05-03T21:41:48Z – codex:gpt-5:default:implementer – shell_pid=7795 – Ready for review
- 2026-05-03T21:41:49Z – codex:gpt-5:default:reviewer – shell_pid=8290 – Started review via action command
- 2026-05-03T21:41:51Z – codex:gpt-5:default:reviewer – shell_pid=8290 – Review passed: smoke and acceptance set passed
