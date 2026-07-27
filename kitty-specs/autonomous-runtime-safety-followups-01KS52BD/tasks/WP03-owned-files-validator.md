---
work_package_id: WP03
title: owned_files validator
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
agent: ''
history:
- at: '2026-05-21T10:53:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: runtime-riley
authoritative_surface: src/specify_cli/cli/commands/agent/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- tests/tasks/test_finalize_tasks_owned_files_validation.py
- tests/agent/test_finalize_tasks_owned_files_validation.py
- tests/architectural/test_wp_owned_files_no_kitty_specs.py
role: implementer
tags: []
---

# Work Package Prompt: WP03 - owned_files validator

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load runtime-riley
```

## Objective

Catch `kitty-specs/` entries in WP `owned_files` during task finalization, before
lane implementation reaches a branch gate that rejects those paths.

## Context

Issue #1235 shows `finalize-tasks` accepting
`kitty-specs/<slug>/occurrence_map.yaml`, while lane handoff later rejects
`kitty-specs/` changes. Preferred fix is rejection at finalization time with a
clear structured error.

## Subtasks & Detailed Guidance

### T011 - Add invalid ownership fixture

Build a finalize-tasks fixture with one WP owning a `kitty-specs/` path.

### T012 - Implement validation

Add shared validation used by both `--validate-only` and mutating finalization.

### T013 - Structure the error

In JSON mode, include a stable error code and the offending `wp_id` and `path`.

### T014 - Add architectural test

Scan committed WP prompt frontmatter and fail if any `owned_files` entry starts
with `kitty-specs/`.

### T015 - Verify

Run:

```bash
uv run pytest tests/tasks/test_finalize_tasks_owned_files_validation.py tests/agent/test_finalize_tasks_owned_files_validation.py tests/architectural/test_wp_owned_files_no_kitty_specs.py
uv run mypy --strict src/specify_cli/cli/commands/agent/mission.py
```

## Branch Strategy

Planning/base branch: `main`. Final merge target: `main`. Use the runtime
resolved lane workspace.

## Definition of Done

- Validate-only and full finalization reject the invalid ownership.
- Error names WP and path.
- Architectural guard prevents future committed WP prompts from regressing.

## Reviewer Guidance

Confirm the validation is scoped to WP `owned_files` and does not ban all
mission planning artifacts from existing non-lane flows.

## Activity Log

- 2026-05-21T10:53:40Z -- system -- Prompt created.
