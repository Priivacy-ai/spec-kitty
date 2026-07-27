---
work_package_id: WP06
title: Migrate Generated Agent Templates to Bootstrap Context
lane: "done"
dependencies:
- WP04
- WP05
base_branch: feature/agent-profile-implementation
base_commit: 588074a223ae51f8e46211412465192cce387e98
created_at: '2026-03-10T05:09:16.641535+00:00'
subtasks:
- T030
- T031
- T032
- T033
- T034
- T035
phase: Phase 3 - Generated Template Migration
assignee: ''
agent: copilot
shell_pid: '587112'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-09T14:23:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-008
- FR-009
---

# Work Package Prompt: WP06 - Migrate Generated Agent Templates to Bootstrap Context

## ⚠️ IMPORTANT: Review Feedback Status

- Check the feedback section before implementing if this WP has already been reviewed once.

---

## Review Feedback

*[Empty initially.]*  

---

## Markdown Formatting

Use fenced code blocks when documenting regexes, template snippets, or command blocks.

## Objectives & Success Criteria

- A new migration updates generated `specify`, `plan`, `implement`, and `review` prompts for configured agents.
- Inline governance prose is stripped from deployed prompts when present.
- Constitution bootstrap calls are inserted exactly once per prompt.
- Obsolete `.kittify/constitution/library/` directories are cleaned up by the migration.
- The migration is idempotent and fixture-tested across all supported agent directories.

## Context & Constraints

- Primary files:
  - `src/specify_cli/upgrade/migrations/m_2_0_1_fix_generated_command_templates.py`
  - new `src/specify_cli/upgrade/migrations/m_2_0_2_constitution_context_bootstrap.py`
  - `src/specify_cli/upgrade/registry.py` if manual imports or registration flow need adjustment
- Supporting helper:
  - `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` for `get_agent_dirs_for_project()`
- Existing migration tests:
  - `tests/specify_cli/test_constitution_template_migration.py`
- Implementation command: `spec-kitty implement WP06 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T030 - Audit migration patterns and generated prompt inventory

- **Purpose**: Follow the repo’s migration conventions instead of inventing a one-off upgrader.
- **Steps**:
  1. Read the existing command-template repair migration in `m_2_0_1_fix_generated_command_templates.py`.
  2. Confirm the supported generated prompt locations and filename patterns for all configured agents.
  3. Note where markdown and TOML formats differ so the implementation can stay centralized without losing correctness.
- **Files**:
  - `src/specify_cli/upgrade/migrations/m_2_0_1_fix_generated_command_templates.py`
  - related helper modules in the same package
- **Parallel?**: No
- **Notes**: This audit should explicitly identify the action mapping from filename to `--action` value.

### Subtask T031 - Implement migration detection logic

- **Purpose**: Determine whether a project actually needs the new migration.
- **Steps**:
  1. Build `detect()` around concrete sentinels:
     - missing bootstrap command for one of the four actions
     - presence of known inline governance sections that should now be extracted
     - presence of obsolete constitution library output if cleanup is in scope for the migration
  2. Keep detection cheap and file-based.
  3. Reuse configured-agent directory discovery so orphaned agent directories are not treated as active targets.
- **Files**:
  - new `src/specify_cli/upgrade/migrations/m_2_0_2_constitution_context_bootstrap.py`
- **Parallel?**: No
- **Notes**: Avoid false positives that would rewrite already-correct prompt files on every upgrade.

### Subtask T032 - Rewrite generated prompts idempotently

- **Purpose**: Apply the new bootstrap/runtime-doctrine contract to deployed prompt files safely.
- **Steps**:
  1. Insert the action-specific `spec-kitty constitution context --action <action> --json` bootstrap block if it is missing.
  2. Strip the known inline governance prose blocks that now live in runtime doctrine assets.
  3. Preserve workflow instructions, frontmatter, and format-specific syntax for markdown vs TOML agents.
  4. Guarantee a second application produces no additional diffs.
- **Files**:
  - new migration module
- **Parallel?**: No
- **Notes**: Keep the replacement strategy narrow and sentinel-driven; broad regexes over whole files will be brittle.

### Subtask T033 - Remove obsolete library artifacts during migration

- **Purpose**: Clean up the old generated-library footprint in upgraded projects.
- **Steps**:
  1. Remove `.kittify/constitution/library/` if it exists when applying the migration.
  2. Make the removal idempotent and dry-run aware.
  3. Record the cleanup in migration change output so users understand why the directory disappeared.
- **Files**:
  - new migration module
- **Parallel?**: No
- **Notes**: This is cleanup of generated artifacts, not user-authored doctrine content. Do not widen deletion scope beyond the obsolete library directory.

### Subtask T034 - Add parametrized 12-agent migration coverage

- **Purpose**: Prove the migration works across the supported agent matrix.
- **Steps**:
  1. Add/update tests covering each configured agent directory.
  2. Verify bootstrap-call insertion and inline-prose removal for all four commands where appropriate.
  3. Keep fixtures small and deterministic; they only need enough prompt content to validate the migration logic.
- **Files**:
  - `tests/specify_cli/test_constitution_template_migration.py`
- **Parallel?**: Yes
- **Notes**: Use configured-agent fixtures, not all directories unconditionally, to match upgrade behavior.

### Subtask T035 - Add idempotency and config-filtering coverage

- **Purpose**: Protect against duplicate insertions and accidental rewrites of inactive agent directories.
- **Steps**:
  1. Add a second-run assertion that the migration is a no-op after the first successful apply.
  2. Add coverage showing only configured agents are rewritten.
  3. Add a missing-directory case so upgrade runs remain resilient in partially initialized projects.
- **Files**:
  - `tests/specify_cli/test_constitution_template_migration.py`
- **Parallel?**: Yes
- **Notes**: Treat these as first-class migration requirements, not optional cleanup checks.

## Test Strategy

- Run: `pytest -q tests/specify_cli/test_constitution_template_migration.py`
- Include at least one dry-run assertion if the migration reports “Would update” style output.

## Risks & Mitigations

- Prompt formats differ across agents. Keep one migration path, but validate both markdown and TOML variants through fixtures.
- Cleanup logic is inherently destructive. Scope deletion strictly to `.kittify/constitution/library/` and keep dry-run behavior honest.

## Review Guidance

- Confirm the migration does not touch inactive agent directories.
- Confirm bootstrap insertion is exactly-once per prompt.
- Confirm a second migration run produces no extra changes.

## Activity Log

- 2026-03-09T14:23:30Z - system - lane=planned - Prompt created.
- 2026-03-10T05:09:22Z – copilot – shell_pid=538663 – lane=doing – Assigned agent via workflow command
- 2026-03-10T06:54:59Z – copilot – shell_pid=538663 – lane=for_review – Constitution bootstrap migration implemented with 12-agent coverage and idempotency tests
- 2026-03-10T06:55:48Z – copilot – shell_pid=587112 – lane=doing – Started review via workflow command
- 2026-03-10T07:01:58Z – copilot – shell_pid=587112 – lane=done – Review passed: migration clean, 79 tests (48 parametrised × 12 agents), idempotency + config-filtering verified.
