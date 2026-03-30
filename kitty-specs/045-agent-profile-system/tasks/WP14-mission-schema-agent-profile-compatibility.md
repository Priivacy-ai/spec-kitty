---
work_package_id: WP14
title: Mission Schema Agent-Profile Compatibility
lane: "done"
dependencies:
- WP05
subtasks:
- T026
- T027
- T028
- T029
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

# Work Package Prompt: WP14 - Mission Schema Agent-Profile Compatibility

## Objectives & Success Criteria

- Mission schemas accept optional `agent-profile` on states/steps.
- Existing mission files remain valid without modification.

## Context & Constraints

- Field should validate profile ID format (kebab-case pattern).
- This is schema compatibility, not orchestration behavior wiring.

## Implementation Command

- `spec-kitty implement WP14 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T026 - Mission schema optional `agent-profile` on states/steps

- **Purpose**: Add feature-level schema support.
- **Steps**:
  1. Update mission schema property definitions.
  2. Keep `agent-profile` optional.
  3. Add profile ID pattern constraints.
- **Files**:
  - `src/doctrine/schemas/mission.schema.yaml`
- **Parallel?**: No.
- **Notes**: Ensure schema remains readable and maintainable.

### Subtask T027 - Runtime DAG schema updates

- **Purpose**: Keep runtime format aligned with primary mission schema.
- **Steps**:
  1. Add optional `agent-profile` to runtime DAG step definitions.
  2. Keep omission behavior unchanged.
- **Files**:
  - runtime schema or mission runtime validation config in doctrine
- **Parallel?**: No.
- **Notes**: Match validation semantics between schema variants.

### Subtask T028 - Validation tests for valid/invalid/omitted values

- **Purpose**: Lock in compatibility behavior.
- **Steps**:
  1. Add tests covering valid profile IDs.
  2. Add tests covering invalid patterns.
  3. Add tests for omitted field acceptance.
- **Files**:
  - `tests/doctrine/test_mission_schema.py` (or equivalent)
- **Parallel?**: Yes.
- **Notes**: Include representative state and step samples.

### Subtask T029 - Backward compatibility for shipped missions

- **Purpose**: Guard against regressions on existing doctrine missions.
- **Steps**:
  1. Validate all shipped mission files against updated schema.
  2. Add regression assertion to keep this guarantee permanent.
- **Files**:
  - schema regression test module(s)
- **Parallel?**: No.
- **Notes**: Failures should identify specific mission file quickly.

## Test Strategy

- Create failing schema tests before schema edits.
- Run full mission validation regression suite.

## Risks & Mitigations

- Unintentional schema tightening: use explicit compatibility fixtures.

## Review Guidance

- Reviewers should inspect whether any existing mission files required edits (they should not).

## Activity Log

- 2026-02-23T20:24:30Z - system - lane=planned - Prompt created.
- 2026-02-23T20:51:13Z – codex – lane=in_progress – Implementation started
- 2026-02-23T20:51:14Z – codex – lane=for_review – Implementation complete
- 2026-02-23T20:51:15Z – codex – lane=done – Implemented and validated
