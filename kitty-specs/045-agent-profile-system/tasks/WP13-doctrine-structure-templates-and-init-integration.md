---
work_package_id: WP13
title: Doctrine Structure Templates and Init Integration
lane: "done"
dependencies:
- WP05
subtasks:
- T021
- T022
- T023
- T024
- T025
phase: Phase 2 - Foundation Wave
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

# Work Package Prompt: WP13 - Doctrine Structure Templates and Init Integration

## Objectives & Success Criteria

- Ship `REPO_MAP.md` and `SURFACES.md` templates in doctrine package.
- Extend init flow to offer optional generation of these files during onboarding.

## Context & Constraints

- Preserve existing init command behavior and prompts; add opt-in only.
- Templates should include placeholders suitable for manual/agent completion.

## Implementation Command

- `spec-kitty implement WP13 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T021 - Add structure templates to doctrine package

- **Purpose**: Provide shipped source templates for repository orientation artifacts.
- **Steps**:
  1. Add template files under `src/doctrine/templates/structure/`.
  2. Ensure placeholders for date/tree/surfaces metadata are present.
  3. Confirm files are included in package data rules (WP05 alignment).
- **Files**:
  - `src/doctrine/templates/structure/REPO_MAP.md`
  - `src/doctrine/templates/structure/SURFACES.md`
- **Parallel?**: No.
- **Notes**: Keep markdown structure stable for future automation.

### Subtask T022 - Template contract tests

- **Purpose**: Detect accidental template regressions.
- **Steps**:
  1. Add tests asserting both templates exist and are loadable from package resources.
  2. Assert required placeholder markers exist.
- **Files**:
  - `tests/doctrine/test_structure_templates.py`
- **Parallel?**: Yes.
- **Notes**: Avoid brittle full-text snapshots unless necessary.

### Subtask T023 - Init workflow prompt integration

- **Purpose**: Offer structure file generation during bootstrap.
- **Steps**:
  1. Add optional prompt in init flow for generating structure maps.
  2. Respect non-interactive/automation paths where applicable.
  3. Keep UX copy concise and consistent.
- **Files**:
  - init command modules under `src/specify_cli/`
- **Parallel?**: No.
- **Notes**: Do not require generation to continue init.

### Subtask T024 - File generation and overwrite safety

- **Purpose**: Prevent destructive writes and ambiguous output locations.
- **Steps**:
  1. Implement deterministic output path logic.
  2. Add overwrite checks/confirmations consistent with existing tooling.
  3. Surface clear next steps after generation.
- **Files**:
  - init generation helpers
- **Parallel?**: No.
- **Notes**: Prefer idempotent behavior when rerun.

### Subtask T025 - Integration tests for accept/decline paths

- **Purpose**: Guarantee onboarding behavior remains stable.
- **Steps**:
  1. Add tests for user accepts generation path.
  2. Add tests for user declines path.
  3. Assert produced files and messaging contracts.
- **Files**:
  - init command tests
- **Parallel?**: No.
- **Notes**: Reuse test harness patterns from existing interactive init tests.

## Test Strategy

- Add template presence tests first.
- Add init flow integration tests for both prompt outcomes.

## Risks & Mitigations

- Template generation path confusion: assert explicit file paths in CLI output.

## Review Guidance

- Reviewers should verify no template generation occurs when user declines.

## Activity Log

- 2026-02-23T20:24:30Z - system - lane=planned - Prompt created.
- 2026-02-23T20:51:10Z – codex – lane=in_progress – Implementation started
- 2026-02-23T20:51:11Z – codex – lane=for_review – Implementation complete
- 2026-02-23T20:51:12Z – codex – lane=done – Implemented and validated
