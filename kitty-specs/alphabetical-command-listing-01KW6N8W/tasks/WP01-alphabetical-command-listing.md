---
work_package_id: WP01
title: Sort Root Command Listing
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
tracker_refs: []
planning_base_branch: feat/alphabetical-command-listing
merge_target_branch: feat/alphabetical-command-listing
branch_strategy: Planning artifacts for this mission were generated on feat/alphabetical-command-listing. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/alphabetical-command-listing unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - CLI usability
assignee: ''
agent: "cursor"
shell_pid: "79394"
history:
- at: '2026-06-28T08:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_root_command_order.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/__init__.py
- tests/specify_cli/cli/commands/test_root_command_order.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 - Sort Root Command Listing

## Objectives & Success Criteria

- Sort the user-facing root command list alphabetically.
- Preserve all existing root commands and command behavior.
- Add focused regression tests for ordering and representative command presence.

## Context & Constraints

- Spec: `kitty-specs/alphabetical-command-listing-01KW6N8W/spec.md`
- Plan: `kitty-specs/alphabetical-command-listing-01KW6N8W/plan.md`
- Relevant implementation surface: `src/specify_cli/cli/commands/__init__.py`
- Relevant tests: `tests/specify_cli/cli/commands/test_root_command_order.py`

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/alphabetical-command-listing; completed changes must merge back into feat/alphabetical-command-listing.
- **Planning base branch**: feat/alphabetical-command-listing
- **Merge target branch**: feat/alphabetical-command-listing

## Subtasks & Detailed Guidance

### Subtask T001 - Sort root command metadata

- **Purpose**: Make bare root command output scan predictably.
- **Steps**: Sort the root command metadata after registration so displayed command names are alphabetical.
- **Files**: `src/specify_cli/cli/commands/__init__.py`
- **Parallel?**: No.

### Subtask T002 - Add root ordering tests

- **Purpose**: Prevent future command registration changes from regressing ordering.
- **Steps**: Add tests that inspect generated root command names and assert they are sorted.
- **Files**: `tests/specify_cli/cli/commands/test_root_command_order.py`
- **Parallel?**: Yes.

### Subtask T003 - Verify command preservation

- **Purpose**: Ensure sorting does not omit commands.
- **Steps**: Assert representative existing commands remain present.
- **Files**: `tests/specify_cli/cli/commands/test_root_command_order.py`
- **Parallel?**: No.

### Subtask T004 - Run targeted tests

- **Purpose**: Confirm the PR is independently safe.
- **Steps**: Run the narrow root command order test file.
- **Files**: test command output only.
- **Parallel?**: No.

## Test Strategy

- Run `pytest tests/specify_cli/cli/commands/test_root_command_order.py`.

## Risks & Mitigations

- **Risk**: Typer stores groups and commands separately. **Mitigation**: Test the generated command object order seen by users.
- **Risk**: Sorting internal metadata could affect hidden commands. **Mitigation**: Sort by displayed command name and verify representative command preservation.

## Review Guidance

- Confirm command names and hierarchy are unchanged.
- Confirm root command list order is alphabetic.

## Activity Log

- 2026-06-28T08:45:00Z - system - Prompt created.
- 2026-06-28T08:45:58Z – cursor – shell_pid=77236 – Assigned agent via action command
- 2026-06-28T08:50:02Z – cursor – shell_pid=77236 – Ready for review: implementation committed; targeted tests passed (2 passed).
- 2026-06-28T08:50:12Z – cursor – shell_pid=79394 – Started review via action command
