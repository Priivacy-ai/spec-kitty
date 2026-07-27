---
work_package_id: WP12
title: Agent Profile Initialization Command
lane: "done"
dependencies:
- WP11
- WP15
subtasks:
- T041
- T042
- T043
- T044
phase: Phase 4 - Runtime Integration
assignee: codex
agent: "codex"
shell_pid: ''
review_status: "approved"
reviewed_by: "codex"
history:
- timestamp: '2026-02-23T20:24:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP12 - Agent Profile Initialization Command

## Objectives & Success Criteria

- Add `spec-kitty agent profile init <profile-id>` command.
- Resolve inherited profile context and write tool-specific context fragment.
- Provide clear success/error output for profile/tool resolution.

## Context & Constraints

- Depends on WP11 output conventions and WP15 profile resolution.
- Keep initialization stateless and safe for parallel workflows.

## Implementation Command

- `spec-kitty implement WP12 --base WP11`
- If WP15 is not merged into the selected base, use: `spec-kitty implement WP12 --base WP15`

## Subtasks & Detailed Guidance

### Subtask T041 - Add init command contract

- **Purpose**: Expose initialization behavior through CLI.
- **Steps**:
  1. Add `init` subcommand to agent profile command group.
  2. Validate profile ID input and handle missing profile errors.
  3. Keep command help text explicit about effect.
- **Files**:
  - `src/specify_cli/cli/commands/agent/profile.py`
- **Parallel?**: No.
- **Notes**: Match existing command patterns and error style.

### Subtask T042 - Build resolved governance payload

- **Purpose**: Convert resolved profile into tool-init context.
- **Steps**:
  1. Load profile via repository and call `resolve_profile()`.
  2. Normalize directives, specialization boundaries, collaboration contracts, and mode defaults.
  3. Ensure payload format is stable and testable.
- **Files**:
  - profile command module
  - context generation helper (new if needed)
- **Parallel?**: No.
- **Notes**: Include inherited fields in payload by default.

### Subtask T043 - Tool detection and context fragment writing

- **Purpose**: Apply payload to active tool target deterministically.
- **Steps**:
  1. Detect active/available tool context from config/project markers.
  2. Select destination path(s) per tool integration rules.
  3. Write fragment idempotently and report output location.
- **Files**:
  - profile init helper modules
  - tool integration mapping/config modules
- **Parallel?**: No.
- **Notes**: Avoid global mutable session state files.

### Subtask T044 - Init command test suite

- **Purpose**: Lock runtime behavior and error handling.
- **Steps**:
  1. Add success-path test with resolved/inherited profile.
  2. Add missing-profile failure test.
  3. Add tool-detection/target-selection tests.
  4. Add idempotent rewrite/output contract checks.
- **Files**:
  - `tests/specify_cli/cli/commands/agent/test_profile_init.py`
- **Parallel?**: Yes.
- **Notes**: Use temp directories to assert written fragment content/paths.

## Test Strategy

- Start by writing command tests for expected outputs/paths.
- Implement command + helper logic until all tests pass.

## Risks & Mitigations

- Ambiguous tool selection: codify precedence and assert in tests.

## Review Guidance

- Reviewers should verify command applies merged profile (not raw child-only profile).

## Activity Log

- 2026-02-23T20:24:30Z - system - lane=planned - Prompt created.
- 2026-02-23T20:51:24Z – codex – lane=in_progress – Implementation started
- 2026-02-23T20:51:25Z – codex – lane=for_review – Implementation complete
- 2026-02-23T20:51:26Z – codex – lane=done – Implemented and validated
