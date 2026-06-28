---
work_package_id: WP01
title: Add Universal Short Help Flag
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-002
- C-003
tracker_refs: []
planning_base_branch: feat/short-help-flag
merge_target_branch: feat/short-help-flag
branch_strategy: Planning artifacts for this mission were generated on feat/short-help-flag. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/short-help-flag unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - CLI usability
assignee: ''
agent: "cursor"
shell_pid: "74081"
history:
- at: '2026-06-28T08:39:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/cli/commands/test_short_help_flag.py
execution_mode: code_change
model: ''
owned_files:
- docs/reference/agent-subcommands.md
- docs/reference/cli-commands.md
- src/specify_cli/__init__.py
- src/specify_cli/cli/commands/__init__.py
- tests/specify_cli/cli/commands/test_short_help_flag.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 - Add Universal Short Help Flag

## Objectives & Success Criteria

- Make `-h` behave like `--help` wherever the CLI accepts help.
- Cover root, command group, and nested subcommand help paths.
- Preserve the existing `--help` long flag and command action safety.

## Context & Constraints

- Spec: `kitty-specs/short-help-flag-01KW6N7D/spec.md`
- Plan: `kitty-specs/short-help-flag-01KW6N7D/plan.md`
- Relevant implementation surfaces: `src/specify_cli/__init__.py`, `src/specify_cli/cli/commands/__init__.py`
- Relevant tests: `tests/specify_cli/cli/commands/test_short_help_flag.py`

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/short-help-flag; completed changes must merge back into feat/short-help-flag.
- **Planning base branch**: feat/short-help-flag
- **Merge target branch**: feat/short-help-flag

## Subtasks & Detailed Guidance

### Subtask T001 - Configure short help centrally

- **Purpose**: Avoid per-command drift and make `-h` broadly available.
- **Steps**: Add or apply shared help option settings at root app construction and command/group registration boundaries.
- **Files**: `src/specify_cli/__init__.py`, `src/specify_cli/cli/commands/__init__.py`
- **Parallel?**: No.
- **Notes**: Do not add new mission flags or alter command names.

### Subtask T002 - Add regression tests

- **Purpose**: Pin `-h` behavior anywhere `--help` works.
- **Steps**: Add tests for root help, a command group help path, and a nested subcommand help path.
- **Files**: `tests/specify_cli/cli/commands/test_short_help_flag.py`
- **Parallel?**: Yes.
- **Notes**: Use representative stable command paths such as root, `agent`, and `agent mission`.

### Subtask T003 - Verify help parity

- **Purpose**: Ensure `-h` and `--help` remain interchangeable for help access.
- **Steps**: Assert both flags exit successfully and include the same key help markers for each selected path.
- **Files**: `tests/specify_cli/cli/commands/test_short_help_flag.py`
- **Parallel?**: No.

### Subtask T004 - Run targeted tests

- **Purpose**: Confirm the PR is independently safe.
- **Steps**: Run the narrow short-help test file.
- **Files**: test command output only.
- **Parallel?**: No.

## Test Strategy

- Run `pytest tests/specify_cli/cli/commands/test_short_help_flag.py`.

## Risks & Mitigations

- **Risk**: Root-only configuration may not affect nested commands. **Mitigation**: Add nested command-group tests.
- **Risk**: Help tests become brittle due Rich formatting. **Mitigation**: Assert stable markers and exit codes rather than full output snapshots.

## Review Guidance

- Confirm `-h` works at every representative level tested.
- Confirm `--help` remains unchanged and available.

## Activity Log

- 2026-06-28T08:39:00Z - system - Prompt created.
- 2026-06-28T08:39:37Z – cursor – shell_pid=71807 – Assigned agent via action command
- 2026-06-28T08:43:13Z – cursor – shell_pid=71807 – Ready for review: implementation committed; targeted tests passed (4 passed).
- 2026-06-28T08:43:19Z – cursor – shell_pid=74081 – Started review via action command
- 2026-06-28T14:28:35Z – codex – Reroll: expanded short-help coverage to two groups and two nested groups; regenerated CLI reference docs for `-h` help rows.
