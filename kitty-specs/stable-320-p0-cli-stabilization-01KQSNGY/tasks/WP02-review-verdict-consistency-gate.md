---
work_package_id: WP02
title: Review Verdict Consistency Gate
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-stable-320-p0-cli-stabilization-01KQSNGY
base_commit: 531e94731375f2f32f0f26d2d6c82e4892a2f031
created_at: '2026-05-04T16:31:00.517215+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
shell_pid: '63916'
history:
- at: '2026-05-04T14:55:25Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/review/**
- src/specify_cli/post_merge/review_artifact_consistency.py
- src/specify_cli/cli/commands/review.py
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/cli/commands/agent/tasks.py
- tests/review/**
- tests/post_merge/test_review_artifact_consistency.py
- tests/tasks/**
- tests/specify_cli/cli/commands/agent/test_tasks.py
tags: []
task_type: implement
---

# Work Package Prompt: WP02 - Review Verdict Consistency Gate

## Objective

Implement the #904 fail-closed review consistency policy: a WP must not silently move to `approved` or `done`, and mission status, mission review, and merge preflight must not pass silently when the latest review-cycle artifact still has `verdict: rejected`.

## Context

Read:

- `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/spec.md`
- `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/review-verdict-consistency.md`
- `src/specify_cli/review/artifacts.py`
- `src/specify_cli/post_merge/review_artifact_consistency.py`
- `src/specify_cli/cli/commands/agent/tasks.py`

Existing helpers already parse latest review artifacts. Reuse them unless a small shared helper is needed to avoid duplicated logic.

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty agent action implement WP02 --agent <name>`
- Execution worktrees are allocated later from `lanes.json`; do not create worktrees manually.

## Subtasks

### T006 - Add latest-artifact fixtures and tests

Create regression fixtures for these cases:

- no review-cycle artifact: transition behavior is unchanged unless another guard blocks it;
- latest cycle rejected: approved/done transition is blocked;
- earlier rejected but latest approved: transition is allowed;
- malformed or unreadable artifact: command fails diagnostically rather than silently passing.

### T007 - Enforce fail-closed before state mutation

Locate every command path in scope that can move a WP to `approved` or `done`, especially `move-task` or workflow helpers in `src/specify_cli/cli/commands/agent/tasks.py`. Insert the review contradiction check before any frontmatter, event-log, or history mutation.

The diagnostic must name the WP id, latest rejected artifact path, and the required repair or override action.

### T008 - Add durable explicit override support

Provide a clear operator override path. The accepted design must persist structured evidence in review-cycle metadata or a linked override artifact. A one-shot flag that leaves no audit trail is not acceptable.

Tests must assert:

- override permits the intended transition;
- override evidence remains discoverable later;
- absent override still blocks.

### T009 - Extend mission status, mission review, and merge preflight

Ensure `spec-kitty agent tasks status`, mission review, and merge preflight do not silently pass when a done/approved WP is contradicted by latest rejected review evidence. `src/specify_cli/post_merge/review_artifact_consistency.py` is the likely shared starting point; top-level command gates may also need updates in `src/specify_cli/cli/commands/review.py` and `src/specify_cli/cli/commands/merge.py`.

### T010 - Preserve JSON stdout cleanliness

For any JSON-producing command touched by this WP, add or update tests that parse stdout as JSON. Warnings and diagnostics must go to stderr or structured JSON fields, not mixed text on stdout.

### T011 - Add end-to-end consistency coverage

Add a focused scenario that starts with a rejected latest review artifact, attempts completion, verifies no mutation occurred, then applies the supported override and verifies durable evidence plus successful transition.

## Definition of Done

- [ ] Latest rejected review-cycle artifacts block approved/done transitions before mutation.
- [ ] Mission status, mission review, and merge preflight catch done/approved plus latest rejected contradictions.
- [ ] Explicit override is durable and inspectable.
- [ ] JSON stdout remains parseable for touched JSON commands.
- [ ] Focused #904 tests pass.

## Reviewer Guidance

Reject warning-only behavior, post-mutation failures, or override mechanisms without durable evidence. Confirm PR #959 and PR #969 behavior is not reimplemented beyond current repro needs.
