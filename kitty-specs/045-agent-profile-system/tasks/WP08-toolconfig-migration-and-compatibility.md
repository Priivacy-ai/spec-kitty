---
work_package_id: WP08
title: ToolConfig Migration and Compatibility
lane: "done"
dependencies:
- WP05
subtasks:
- T006
- T007
- T008
- T009
- T010
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

# Work Package Prompt: WP08 - ToolConfig Migration and Compatibility

## Objectives & Success Criteria

- Ship upgrade migration that renames `.kittify/config.yaml` key `agents` to `tools`.
- Keep runtime backward compatibility: legacy key still readable with deprecation warning.
- Ensure config writing paths standardize on `tools`.

## Context & Constraints

- This WP must not break existing projects mid-upgrade.
- Keep migration idempotent and safe if rerun.

## Implementation Command

- `spec-kitty implement WP08 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T006 - Add migration module for key rename

- **Purpose**: Convert persisted config to canonical key.
- **Steps**:
  1. Create migration file in upgrade migrations directory.
  2. Load `.kittify/config.yaml` safely when present.
  3. If `agents` exists and `tools` absent, rename key preserving values.
  4. Leave files unchanged when already canonical.
- **Files**:
  - `src/specify_cli/upgrade/migrations/m_*_tool_config_rename.py`
- **Parallel?**: No.
- **Notes**: Preserve comments/order where practical.

### Subtask T007 - Register migration in upgrade pipeline

- **Purpose**: Ensure migration executes during `spec-kitty upgrade`.
- **Steps**:
  1. Add migration to registry/discovery list.
  2. Verify ordering relative to adjacent migrations.
  3. Confirm metadata version boundaries are correct.
- **Files**:
  - migration registry modules under `src/specify_cli/upgrade/`
- **Parallel?**: No.
- **Notes**: Missing registration is a silent failure risk.

### Subtask T008 - Runtime compatibility in ToolConfig loading/writing

- **Purpose**: Maintain read compatibility while canonicalizing writes.
- **Steps**:
  1. Update load logic to read `tools` first.
  2. If fallback to `agents`, emit deprecation warning with remediation.
  3. Ensure save/write paths emit `tools` only.
- **Files**:
  - `src/specify_cli/core/tool_config.py`
  - any CLI writer paths touching `.kittify/config.yaml`
- **Parallel?**: No.
- **Notes**: Treat absent keys as defaults; no hard errors.

### Subtask T009 - Migration + compatibility test matrix

- **Purpose**: Prevent regressions across legacy/current config states.
- **Steps**:
  1. Add tests for legacy-only, canonical-only, both keys, and no keys.
  2. Assert warning behavior on legacy fallback.
  3. Assert migration idempotency and non-destructive rewrite.
- **Files**:
  - `tests/specify_cli/upgrade/test_tool_config_migration.py`
  - `tests/specify_cli/core/test_tool_config.py` (or existing test module)
- **Parallel?**: Yes.
- **Notes**: Use temporary files and fixture-driven inputs.

### Subtask T010 - Docs/help/deprecation messaging alignment

- **Purpose**: Make canonical naming clear to contributors/users.
- **Steps**:
  1. Update relevant docs/help strings to use `tools` terminology.
  2. Ensure deprecation warning text is explicit and actionable.
  3. Keep messaging consistent with glossary intent.
- **Files**:
  - relevant docs and CLI help strings
- **Parallel?**: No.
- **Notes**: Avoid broad unrelated wording changes.

## Test Strategy

- Write failing migration/compat tests before implementation.
- Run migration tests plus ToolConfig unit tests after code updates.

## Risks & Mitigations

- Incomplete migration coverage: use key-state matrix tests.
- Unexpected YAML rewrites: compare before/after fixtures.

## Review Guidance

- Verify loader priority: `tools` > `agents` fallback.
- Verify migration does not erase unrelated config keys.

## Activity Log

- 2026-02-23T20:24:30Z - system - lane=planned - Prompt created.
- 2026-02-23T20:51:00Z – codex – lane=in_progress – Implementation started
- 2026-02-23T20:51:01Z – codex – lane=for_review – Implementation complete
- 2026-02-23T20:51:02Z – codex – lane=done – Implemented and validated
