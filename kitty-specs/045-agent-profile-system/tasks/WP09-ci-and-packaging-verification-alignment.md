---
work_package_id: WP09
title: CI and Packaging Verification Alignment
lane: "done"
dependencies:
- WP05
subtasks:
- T011
- T012
- T013
- T014
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

# Work Package Prompt: WP09 - CI and Packaging Verification Alignment

## Objectives & Success Criteria

- CI runs doctrine-focused tests and packaging smoke checks consistently.
- Entry-point and install-time behavior is validated in automation.

## Context & Constraints

- Keep CI runtime practical while increasing distribution confidence.
- Prefer tests that validate installed artifacts, not only source checkouts.

## Implementation Command

- `spec-kitty implement WP09 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T011 - CI coverage alignment for doctrine tests

- **Purpose**: Ensure doctrine test suite is always exercised.
- **Steps**:
  1. Audit existing CI workflow test selection logic.
  2. Add/adjust doctrine test invocation in mandatory paths.
  3. Confirm failure surfaces clearly in CI output.
- **Files**:
  - `.github/workflows/*.yml`
  - CI helper scripts if present
- **Parallel?**: No.
- **Notes**: Avoid duplicate test runs that inflate time unnecessarily.

### Subtask T012 - Install-time smoke checks

- **Purpose**: Catch runtime failures that only appear post-install.
- **Steps**:
  1. Add smoke check for `python -m specify_cli --help`.
  2. Add smoke check for doctrine imports/profile loading.
  3. Integrate these checks in CI path that uses built artifacts.
- **Files**:
  - test modules under `tests/doctrine/` or CI scripts
- **Parallel?**: No.
- **Notes**: Keep command output assertions stable.

### Subtask T013 - Wheel content verification assertions

- **Purpose**: Ensure doctrine resources are in wheel payload.
- **Steps**:
  1. Add deterministic assertions for expected directory/file patterns.
  2. Validate shipped profiles/directives/schemas/templates presence.
  3. Fail with clear missing-file diagnostics.
- **Files**:
  - packaging test module(s)
- **Parallel?**: Yes.
- **Notes**: Reuse helper logic from WP05 tests where possible.

### Subtask T014 - Local/CI parity docs

- **Purpose**: Reduce “works locally but not CI” drift.
- **Steps**:
  1. Document command set expected to pass pre-merge.
  2. Align quickstart/dev docs with CI checks.
- **Files**:
  - `kitty-specs/045-agent-profile-system/quickstart.md` and/or contributor docs
- **Parallel?**: No.
- **Notes**: Keep list short and high-signal.

## Test Strategy

- Ensure CI workflow changes are accompanied by local command validation notes.
- Run targeted doctrine and packaging tests before finalizing.

## Risks & Mitigations

- CI flakiness from heavy artifact steps: keep smoke checks minimal and deterministic.

## Review Guidance

- Reviewers should verify CI jobs changed are the required branch protections.

## Activity Log

- 2026-02-23T20:24:30Z - system - lane=planned - Prompt created.
- 2026-02-23T20:51:03Z – codex – lane=in_progress – Implementation started
- 2026-02-23T20:51:04Z – codex – lane=for_review – Implementation complete
- 2026-02-23T20:51:05Z – codex – lane=done – Implemented and validated
