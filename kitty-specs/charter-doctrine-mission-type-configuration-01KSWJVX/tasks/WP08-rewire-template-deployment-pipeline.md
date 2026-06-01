---
work_package_id: WP08
title: Rewire template deployment pipeline; update CLAUDE.md
dependencies:
- WP02
- WP07
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 5db56cf60d7f0c1fe8cbf7098b7d1fee581c003c
created_at: '2026-05-30T20:55:03.963438+00:00'
subtasks:
- T048
- T049
- T050
- T051
- T052
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3431372"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/specify_cli/skills/
execution_mode: code_change
owned_files:
- src/specify_cli/skills/command_renderer.py
- src/specify_cli/skills/command_installer.py
- CLAUDE.md
- tests/specify_cli/skills/test_command_renderer.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP08 — Rewire template deployment pipeline; update CLAUDE.md

## Context

The template deployment pipeline (which generates agent command files for `.claude/commands/`, `.amazonq/prompts/`, etc.) currently reads prompt templates from `src/specify_cli/missions/*/command-templates/`. After WP02 moves all templates to `src/doctrine/missions/mission-steps/`, the pipeline must be updated to read from the new path.

The key files are:
- `src/specify_cli/skills/command_renderer.py` — renders source templates into agent-skills format
- `src/specify_cli/skills/command_installer.py` — installs skill packages
- Upgrade migrations that call `get_agent_dirs_for_project()` and write to agent directories

`CLAUDE.md`'s "Template Source Location" section must also be updated (FR-010).

## Objective

Update `command_renderer.py` and `command_installer.py` to read prompt templates from the new doctrine source path. Update any upgrade migration that references the old path. Update `CLAUDE.md`. Write an NFR-004 gate test.

## New Template Source Path

**Before**: `src/specify_cli/missions/{mission_type}/command-templates/{step_id}.md`

**After**: `src/doctrine/missions/mission-steps/{mission_type}/{step_id}/prompt.md`

## Subtasks

### T048 — Update command_renderer.py

Open `src/specify_cli/skills/command_renderer.py`.

Find the code that constructs the path to the source template. It currently points into `src/specify_cli/missions/*/command-templates/`. Update it to:

```python
# New source path
template_path = (
    Path(__file__).parent.parent.parent.parent  # → src/
    / "doctrine"
    / "missions"
    / "mission-steps"
    / mission_type
    / step_id
    / "prompt.md"
)
```

(Adjust the `parent` chain to reach `src/` from the current file's location.)

Also update any display strings, error messages, or comments that reference the old path.

### T049 — Update command_installer.py

Open `src/specify_cli/skills/command_installer.py`.

Update any hardcoded or derived references to `src/specify_cli/missions/*/command-templates/` to use the new doctrine path. If the installer delegates to `command_renderer.py` for path resolution, this may require no additional change — verify.

### T050 — Update upgrade migration pipeline

Find the upgrade migration that deploys template files to agent directories (`.claude/commands/`, `.amazonq/prompts/`, etc.). Based on research, this is likely in `src/specify_cli/upgrade/migrations/m_3_2_5_fix_prompt_file_workaround.py` or a similar migration.

Check each migration for references to `command-templates/` and update to the new path. Use `get_agent_dirs_for_project()` from `m_0_9_1_complete_lane_migration` as required by CLAUDE.md.

Important: migrations must use `get_agent_dirs_for_project()` (config-aware helper), not iterate over a hardcoded agent directory list.

### T051 — Update CLAUDE.md "Template Source Location" section

Open `CLAUDE.md`. Find the "Template Source Location" section (it has a table and code examples).

Update:
1. The table row: change "SOURCE templates" location from `src/specify_cli/missions/*/command-templates/` to `src/doctrine/missions/mission-steps/`
2. The code example: update the `vim src/specify_cli/missions/software-dev/command-templates/implement.md` example to `vim src/doctrine/missions/mission-steps/software-dev/implement/prompt.md`
3. Update the "How templates flow" diagram description

### T052 — NFR-004 gate test

Write `tests/specify_cli/skills/test_command_renderer.py` (or extend it if it exists):

Test case — NFR-004 gate:
- Given the `software-dev/specify` step exists at the new doctrine path
- When `command_renderer.render("software-dev", "specify")` is called
- Then the output is the content of `src/doctrine/missions/mission-steps/software-dev/specify/prompt.md`
- And the output does NOT come from `src/specify_cli/missions/software-dev/command-templates/specify.md` (which should not exist after WP02)

Also test that all four mission types and all their steps can be rendered without error.

## Acceptance Criteria

- [ ] `command_renderer.py` reads from `src/doctrine/missions/mission-steps/` path
- [ ] No references to `src/specify_cli/missions/*/command-templates/` remain in `command_renderer.py` or `command_installer.py`
- [ ] CLAUDE.md "Template Source Location" section reflects the new path
- [ ] `tests/specify_cli/skills/test_command_renderer.py` NFR-004 gate test passes
- [ ] All four built-in mission types' steps render successfully from the new path
- [ ] `mypy --strict` clean on modified files

## References

- FR-010: Template migration and deployment pipeline rewiring
- NFR-004: Zero regression in deployed agent commands
- CLAUDE.md §"Template Source Location" — section to update
- research.md §"Research Task 5" — deployment pipeline findings
- CLAUDE.md §"Agent Management Best Practices" — `get_agent_dirs_for_project()` pattern

## Activity Log

- 2026-05-30T20:55:04Z – claude:sonnet:python-pedro:implementer – shell_pid=3403375 – Assigned agent via action command
- 2026-05-30T21:02:57Z – claude:sonnet:python-pedro:implementer – shell_pid=3403375 – Ready for review: rewired template deployment pipeline from src/specify_cli/missions/*/command-templates/ to src/doctrine/missions/mission-steps/{mission_type}/{step_id}/prompt.md; updated CLAUDE.md; added NFR-004 gate tests; all 249 skills tests pass
- 2026-05-30T21:05:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=3431372 – Started review via action command
