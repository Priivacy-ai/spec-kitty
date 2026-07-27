---
work_package_id: WP05
title: Doctrine Package Distribution Foundation
lane: "done"
dependencies: []
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Distribution Foundation
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

# Work Package Prompt: WP05 - Doctrine Package Distribution Foundation

## Objectives & Success Criteria

- Ensure wheel-installed environments can import and use `doctrine` without source-tree assumptions.
- Package includes shipped profiles, schemas, directives, and templates as runtime-accessible data.
- Distribution checks fail fast if doctrine assets are missing.

## Context & Constraints

- This is the root dependency for most remaining work packages.
- Respect existing dual-package intent from `plan.md` and distribution scenarios in `spec.md`.
- Use package-resource-safe access patterns; avoid brittle relative-path assumptions.

## Implementation Command

- `spec-kitty implement WP05`

## Subtasks & Detailed Guidance

### Subtask T001 - Doctrine package metadata and artifact inclusion

- **Purpose**: Establish packaging metadata/build config for doctrine and declare non-Python assets.
- **Steps**:
  1. Verify or add doctrine package build configuration.
  2. Include `*.yaml`, `*.md`, and any required template artifacts in wheel/sdist rules.
  3. Confirm build backend/package settings align with existing repository standards.
- **Files**:
  - `src/doctrine/pyproject.toml`
  - potentially root `pyproject.toml` for packaging linkage
- **Parallel?**: No.
- **Notes**: Keep version/dependency declarations minimal and explicit.

### Subtask T002 - Root dependency wiring for CLI distribution

- **Purpose**: Ensure `spec-kitty-cli` installs/uses doctrine correctly.
- **Steps**:
  1. Update root dependency declarations to include doctrine package dependency path/version contract.
  2. Confirm editable and wheel install workflows both resolve doctrine.
  3. Validate import from CLI entry contexts.
- **Files**:
  - `pyproject.toml`
- **Parallel?**: Yes.
- **Notes**: Avoid circular or conflicting dependency declarations.

### Subtask T003 - Resource-safe loading paths

- **Purpose**: Make runtime data loading resilient across source and wheel installs.
- **Steps**:
  1. Audit doctrine resource lookups for path assumptions.
  2. Switch lookups to package resources APIs where needed.
  3. Keep behavior unchanged for existing callers.
- **Files**:
  - `src/doctrine/agent_profiles/repository.py`
  - any helper modules used for schema/template/directive loading
- **Parallel?**: No.
- **Notes**: Preserve compatibility for tests using temp project overlays.

### Subtask T004 - Wheel smoke tests

- **Purpose**: Add automated regression protection for distribution behavior.
- **Steps**:
  1. Add tests that build/install wheel and assert `import doctrine` succeeds.
  2. Assert shipped profile list/read paths work post-install.
  3. Assert wheel contains key doctrine assets (profiles/directives/schemas/templates).
- **Files**:
  - `tests/doctrine/test_wheel_packaging.py` (or equivalent)
  - `tests/doctrine/test_package_smoke.py` (if split)
- **Parallel?**: Yes.
- **Notes**: Prefer deterministic checks and bounded test runtime.

### Subtask T005 - Build/install verification and guardrails

- **Purpose**: Close the loop with repeatable validation steps and developer guidance.
- **Steps**:
  1. Run local build/install smoke sequence from quickstart expectations.
  2. Document mandatory verification commands for future packaging changes.
  3. Ensure failure messages are actionable.
- **Files**:
  - `kitty-specs/045-agent-profile-system/quickstart.md` (only if updates are needed)
  - affected test documentation/comments
- **Parallel?**: No.
- **Notes**: Keep docs tied to actual CI checks.

## Test Strategy

- Add/extend distribution tests first, then implement packaging/resource changes.
- Minimum checks:
  - wheel build succeeds
  - clean install imports `doctrine`
  - shipped profile loading works
  - wheel asset assertions for doctrine data

## Risks & Mitigations

- Missing package data in built wheel: enforce zipfile assertions in tests.
- Source-tree-only behavior: run smoke tests from installed artifact context.

## Review Guidance

- Validate no code paths rely on repository-relative file access for doctrine assets.
- Confirm tests catch both import failures and missing-data failures.

## Activity Log

- 2026-02-23T20:24:30Z - system - lane=planned - Prompt created.
- 2026-02-23T20:50:56Z – codex – lane=in_progress – Implementation started
- 2026-02-23T20:50:57Z – codex – lane=for_review – Implementation complete
- 2026-02-23T20:50:59Z – codex – lane=done – Implemented and validated
