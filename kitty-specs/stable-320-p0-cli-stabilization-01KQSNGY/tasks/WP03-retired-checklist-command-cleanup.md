---
work_package_id: WP03
title: Retired Checklist Command Cleanup
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-014
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-stable-320-p0-cli-stabilization-01KQSNGY
base_commit: 531e94731375f2f32f0f26d2d6c82e4892a2f031
created_at: '2026-05-04T16:40:06.301759+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
shell_pid: '81327'
history:
- at: '2026-05-04T14:55:25Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/shims/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/shims/**
- src/specify_cli/runtime/agent_commands.py
- src/specify_cli/runtime/doctor.py
- src/specify_cli/skills/command_installer.py
- tests/specify_cli/shims/**
- tests/specify_cli/runtime/test_agent_commands_routing.py
- tests/runtime/test_doctor_command_file_health.py
- tests/specify_cli/skills/test_command_installer.py
- docs/**
- CLAUDE.md
tags: []
task_type: implement
---

# Work Package Prompt: WP03 - Retired Checklist Command Cleanup

## Objective

Fix #968 by removing retired `checklist` from active command registries, generated command surfaces, runtime diagnostics, and active counts while keeping safe cleanup for stale package-managed files.

## Context

Read:

- `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/command-surface-generation.md`
- `src/specify_cli/shims/registry.py`
- `src/specify_cli/runtime/agent_commands.py`
- `src/specify_cli/runtime/doctor.py`
- `src/specify_cli/skills/command_installer.py`

The charter's customization preservation rule is binding: do not delete user-owned files based only on `spec-kitty.checklist*` naming.

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty agent action implement WP03 --agent <name>`
- Execution worktrees are allocated later from `lanes.json`; do not create worktrees manually.

## Subtasks

### T012 - Inventory retired checklist drift

Search all active command and skill surfaces for `checklist`. Classify each occurrence:

- active registry/generation surface: remove or update;
- stale cleanup compatibility path: preserve intentionally;
- historical docs/snapshots: update only if they claim current active behavior.

Use `rg -n "checklist" src tests docs CLAUDE.md README.md`.

### T013 - Remove checklist from active generation surfaces

Remove retired checklist from active registries and command routing/count surfaces. Do not recreate templates or command aliases for it.

### T014 - Preserve safe stale cleanup

Ensure old package-managed `spec-kitty.checklist*` files are removed or ignored intentionally during install/upgrade cleanup. Unknown files must be preserved unless manifest or package ownership proves they are managed.

### T015 - Align diagnostics and docs/comments

Update runtime doctor expectations, active command counts, and any docs/comments that state current counts. Keep historical archived artifacts alone unless they are used as current assertions.

### T016 - Add fresh command surface tests

Add tests that generate or inventory a fresh command surface and assert:

- no active `spec-kitty.checklist*` command exists;
- registry entries match packaged templates;
- count diagnostics match generated output;
- stale managed checklist cleanup remains covered.

## Definition of Done

- [ ] Fresh active command surface contains no checklist command.
- [ ] Stale package-managed checklist cleanup remains intentional.
- [ ] Unknown user-authored files are not deleted by broad name matching.
- [ ] Counts and diagnostics agree.
- [ ] #968 regression tests pass.

## Reviewer Guidance

Reject broad cleanup that deletes by filename pattern alone. Verify WP04-owned skill frontmatter files were not modified except where coordination is explicit.
