---
work_package_id: WP10
title: Shipped Directives and Consistency Enforcement
lane: "done"
dependencies:
- WP05
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
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

# Work Package Prompt: WP10 - Shipped Directives and Consistency Enforcement

## Objectives & Success Criteria

- Add complete directive set (`001`-`019`) used by shipped profiles.
- Enforce consistency so every referenced directive exists and titles match profile references.

## Context & Constraints

- Follow `directive.schema.yaml` format and naming conventions.
- Unreferenced directives are allowed; unresolved references are failures.

## Implementation Command

- `spec-kitty implement WP10 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T015 - Build canonical profile-to-directive map

- **Purpose**: Create source-of-truth mapping before editing directive files.
- **Steps**:
  1. Parse all shipped profiles for directive references.
  2. Produce normalized list of expected code/name pairs.
  3. Detect duplicates/conflicts and resolve explicitly.
- **Files**:
  - `src/doctrine/agent_profiles/shipped/*.agent.yaml`
  - working notes/test fixture definitions
- **Parallel?**: No.
- **Notes**: This map drives both file generation and consistency tests.

### Subtask T016 - Add missing directive YAML files

- **Purpose**: Ensure referenced directives exist as shipped artifacts.
- **Steps**:
  1. Create/update directive files under `src/doctrine/directives/` for all referenced codes.
  2. Ensure required schema fields are present and meaningful.
  3. Keep title strings aligned with profile declarations.
- **Files**:
  - `src/doctrine/directives/*.directive.yaml`
- **Parallel?**: No.
- **Notes**: Maintain stable filename/code conventions.

### Subtask T017 - Schema validation coverage for directives

- **Purpose**: Ensure directives conform structurally.
- **Steps**:
  1. Add/extend tests validating directive files against schema.
  2. Include at least one negative fixture to confirm schema enforcement.
- **Files**:
  - doctrine directive validation tests
- **Parallel?**: Yes.
- **Notes**: Reuse existing schema loader helpers when available.

### Subtask T018 - Profile/directive consistency test

- **Purpose**: Prevent future reference drift.
- **Steps**:
  1. Implement test that scans shipped profiles for directive refs.
  2. Assert each referenced code resolves to a directive file.
  3. Assert title/name correspondence.
- **Files**:
  - `tests/doctrine/test_directive_consistency.py`
- **Parallel?**: No.
- **Notes**: Test should provide actionable failure output (missing code, mismatch details).

### Subtask T019 - Negative-path fixtures and failure-mode tests

- **Purpose**: Prove consistency checks fail for known bad states.
- **Steps**:
  1. Add synthetic missing-reference and title-mismatch fixtures.
  2. Assert failure messages are explicit.
- **Files**:
  - fixture files + consistency test module
- **Parallel?**: Yes.
- **Notes**: Keep isolated so shipped artifact tests remain clean.

### Subtask T020 - Contributor guidance for directive upkeep

- **Purpose**: Make maintenance workflow explicit.
- **Steps**:
  1. Add concise guidance for adding/updating profile directive refs.
  2. Link required tests and schema expectations.
- **Files**:
  - contributor docs or doctrine README sections
- **Parallel?**: No.
- **Notes**: Keep policy tightly scoped to consistency contract.

## Test Strategy

- Start with failing consistency tests.
- Add directive files and iterate until consistency + schema validation pass.

## Risks & Mitigations

- Title mismatch churn across files: centralize map in test helper/fixture.

## Review Guidance

- Reviewers should cross-check at least one profile’s directive list against generated files.

## Activity Log

- 2026-02-23T20:24:30Z - system - lane=planned - Prompt created.
- 2026-02-23T20:51:06Z – codex – lane=in_progress – Implementation started
- 2026-02-23T20:51:07Z – codex – lane=for_review – Implementation complete
- 2026-02-23T20:51:08Z – codex – lane=done – Implemented and validated
