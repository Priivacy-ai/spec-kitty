---
work_package_id: WP11
title: Agent Profile Interview Authoring Flow
lane: "done"
dependencies:
- WP10
subtasks:
- T035
- T036
- T037
- T038
- T039
- T040
phase: Phase 3 - Authoring UX
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

# Work Package Prompt: WP11 - Agent Profile Interview Authoring Flow

## Objectives & Success Criteria

- Implement interactive profile creation flow via `--interview`.
- Implement reduced-question fast path via `--defaults`.
- Generated files validate against schema before persistence.

## Context & Constraints

- Follow existing constitution interview interaction patterns.
- Output lives in `.kittify/constitution/agents/<profile-id>.agent.yaml`.
- Role choice should prepopulate capabilities defaults.

## Implementation Command

- `spec-kitty implement WP11 --base WP10`

## Subtasks & Detailed Guidance

### Subtask T035 - Design interview question and answer model

- **Purpose**: Create structured flow that maps directly to AgentProfile schema.
- **Steps**:
  1. Define required vs optional prompts.
  2. Map answers to profile sections and CLI flags.
  3. Ensure defaults path uses required subset only.
- **Files**:
  - `src/specify_cli/cli/commands/agent/profile.py`
  - interview helper modules if introduced
- **Parallel?**: No.
- **Notes**: Keep prompt order stable for test determinism.

### Subtask T036 - Implement `--interview` interactive flow

- **Purpose**: Enable full guided authoring experience.
- **Steps**:
  1. Add branching CLI flow for interview mode.
  2. Capture role, purpose, specialization, collaboration, directive refs, modes.
  3. Normalize values into schema-compatible payload.
- **Files**:
  - CLI command implementation and helpers
- **Parallel?**: No.
- **Notes**: Handle cancellation/interrupt paths cleanly.

### Subtask T037 - Implement `--defaults` fast path

- **Purpose**: Reduce friction for quick profile generation.
- **Steps**:
  1. Ask only required fields defined by spec.
  2. Fill optional fields with sensible defaults.
  3. Ensure output remains valid and editable.
- **Files**:
  - same CLI command path and helper functions
- **Parallel?**: No.
- **Notes**: Keep required prompt count explicit in tests.

### Subtask T038 - Role capability prepopulation and schema validation

- **Purpose**: Improve generated quality and enforce correctness before write.
- **Steps**:
  1. Pull role defaults from capabilities mapping.
  2. Merge with user-provided overrides.
  3. Validate final document against schema; abort write on failure with clear errors.
- **Files**:
  - profile command module
  - validation integration helpers
- **Parallel?**: No.
- **Notes**: Validation failure messages should include actionable field context.

### Subtask T039 - Interview CLI tests

- **Purpose**: Guard interactive behavior and schema contract.
- **Steps**:
  1. Add tests for happy-path interview output.
  2. Add tests for defaults path required questions.
  3. Add tests for validation failures and duplicate profile ID protection.
- **Files**:
  - `tests/specify_cli/cli/commands/agent/test_profile_interview.py`
- **Parallel?**: Yes.
- **Notes**: Mock prompt inputs deterministically.

### Subtask T040 - Output messaging and safe writes

- **Purpose**: Ensure file creation is predictable and non-destructive.
- **Steps**:
  1. Add overwrite protection/error when target profile file exists.
  2. Provide completion output with created path and next steps.
  3. Ensure parent directory creation behavior is explicit.
- **Files**:
  - profile CLI command module
- **Parallel?**: No.
- **Notes**: Keep message format stable for tests.

## Test Strategy

- Start with CLI tests for interview/defaults flow.
- Implement feature paths until all interview tests pass.

## Risks & Mitigations

- Brittle prompt tests: encapsulate interaction layer and mock boundaries.

## Review Guidance

- Reviewers should verify generated YAML content matches question answers exactly.

## Activity Log

- 2026-02-23T20:24:30Z - system - lane=planned - Prompt created.
- 2026-02-23T20:51:20Z – codex – lane=in_progress – Implementation started
- 2026-02-23T20:51:21Z – codex – lane=for_review – Implementation complete
- 2026-02-23T20:51:22Z – codex – lane=done – Implemented and validated
