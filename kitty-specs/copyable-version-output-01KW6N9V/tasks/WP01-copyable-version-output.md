---
work_package_id: WP01
title: Make Version Output Copyable
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-002
- C-003
tracker_refs: []
planning_base_branch: feat/copyable-version-output
merge_target_branch: feat/copyable-version-output
branch_strategy: Planning artifacts for this mission were generated on feat/copyable-version-output. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/copyable-version-output unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - CLI usability
assignee: ''
agent: "cursor"
shell_pid: "83448"
history:
- at: '2026-06-28T08:52:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/cli/commands/test_version_output.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/__init__.py
- tests/specify_cli/cli/commands/test_version_output.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 - Make Version Output Copyable

## Objectives & Success Criteria

- Make version output begin with `spec-kitty-cli version ...`.
- Remove the large ASCII art from `--version` / `-v` output.
- Preserve the version callback's exit behavior.

## Context & Constraints

- Spec: `kitty-specs/copyable-version-output-01KW6N9V/spec.md`
- Plan: `kitty-specs/copyable-version-output-01KW6N9V/plan.md`
- Relevant implementation surface: `src/specify_cli/__init__.py`
- Relevant tests: `tests/specify_cli/cli/commands/test_version_output.py`

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/copyable-version-output; completed changes must merge back into feat/copyable-version-output.
- **Planning base branch**: feat/copyable-version-output
- **Merge target branch**: feat/copyable-version-output

## Subtasks & Detailed Guidance

### Subtask T001 - Update version callback

- **Purpose**: Make issue-report copy/paste easy.
- **Steps**: Change `version_callback` so it prints the version line directly without rendering the banner first.
- **Files**: `src/specify_cli/__init__.py`
- **Parallel?**: No.

### Subtask T002 - Add version output tests

- **Purpose**: Pin output order and banner absence.
- **Steps**: Add tests for both `--version` and `-v`.
- **Files**: `tests/specify_cli/cli/commands/test_version_output.py`
- **Parallel?**: Yes.

### Subtask T003 - Verify version flags

- **Purpose**: Ensure both aliases have the same copyable behavior.
- **Steps**: Assert both flags exit successfully and start with the version line.
- **Files**: `tests/specify_cli/cli/commands/test_version_output.py`
- **Parallel?**: No.

### Subtask T004 - Run targeted tests

- **Purpose**: Confirm the PR is independently safe.
- **Steps**: Run the narrow version output test file.
- **Files**: test command output only.
- **Parallel?**: No.

## Test Strategy

- Run `pytest tests/specify_cli/cli/commands/test_version_output.py`.

## Risks & Mitigations

- **Risk**: Users may miss branding in version output. **Mitigation**: Branding remains available in banner-appropriate flows such as `init`.

## Review Guidance

- Confirm the first line is copyable version text.
- Confirm no large cat banner appears in version output.

## Activity Log

- 2026-06-28T08:52:00Z - system - Prompt created.
- 2026-06-28T08:52:43Z – cursor – shell_pid=81971 – Assigned agent via action command
- 2026-06-28T08:54:18Z – cursor – shell_pid=81971 – Ready for review: implementation committed; targeted tests passed (4 passed).
- 2026-06-28T08:54:24Z – cursor – shell_pid=83448 – Started review via action command
- 2026-06-28T08:54:50Z – user – shell_pid=83448 – Review passed: version output now starts with a copyable version line, banner removed from version callback, and targeted tests passed (4 passed).
