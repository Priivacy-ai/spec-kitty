---
work_package_id: WP07
title: 'Runtime migration: missions + skills + bundles cluster'
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
phase: Phase 3 - Migration
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/template/
create_intent: []
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- src/specify_cli/template/manager.py
- src/specify_cli/template/asset_generator.py
- src/specify_cli/dossier/manifest.py
- src/specify_cli/migration/rewrite_shims.py
- src/specify_cli/skills/command_installer.py
- src/specify_cli/skills/command_renderer.py
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/cli/commands/charter/activate.py
- src/specify_cli/cli/commands/charter/mission_type.py
- src/specify_cli/cli/commands/charter/list_cmd.py
- src/specify_cli/runtime/resolver.py
- src/specify_cli/runtime/show_origin.py
- src/specify_cli/mission_loader/command.py
- src/specify_cli/tool_surface/bundles/claude.py
- src/specify_cli/tool_surface/bundles/codex.py
- src/specify_cli/upgrade/migrations/m_2_1_3_restore_prompt_commands.py
- src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py
- src/specify_cli/upgrade/migrations/m_3_2_0rc35_activate_builtin_mission_types.py
role: implementer
tags: []
tracker_refs: []
wp_code: WP07
---

# Work Package Prompt: WP07 — Runtime migration: missions + skills + bundles cluster

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` and apply its initialization, boundaries, directives,
and tactics. State which you applied.

## Objective

Migrate the mission-repository, mission-type, template-catalog, spdd, and pack_paths consumers onto
`charter.missions`, `charter.spdd_reasons`, `charter.pack_paths`, and the existing
`charter.template_catalog` (FR-004). Behavior-preserving.

## Context & Constraints

- Consumes WP03 doors + WP04 ratchet. `runtime/resolver.py` migrating its `template_catalog` import
  to the existing `charter.template_catalog` is the cleanest "prover" the ratchet shrinks.
- `tool_surface/bundles/codex.py` uses a bare `import doctrine` for package-metadata introspection
  — handle per WP04's documented disposition (this is metadata, not a symbol reach-through).
- Group edits per subtask to stay behavior-preserving; keep lazy shapes, change only the target.

## Subtasks

### T033 — `template/manager.py`, `dossier/manifest.py`, `migration/rewrite_shims.py`  [P]
- `missions.repository` (`MissionTemplateRepository`) → `charter.missions`.

### T034 — `skills/command_installer.py`, `skills/command_renderer.py`, `template/asset_generator.py`  [P]
- `missions.repository` → `charter.missions`; `spdd_reasons.apply_spdd_blocks_for_project` →
  `charter.spdd_reasons`.

### T035 — `cli/commands/mission_type.py`, `charter/{activate,mission_type,list_cmd}.py`  [P]
- `mission_type_repository` (`MissionTypeRepository`, `builtin_mission_type_ids`),
  `mission_step_repository`, `step_projection` → `charter.missions` (per WP01 disposition).

### T036 — `runtime/resolver.py`, `runtime/show_origin.py`, `mission_loader/command.py`  [P]
- `template_catalog` → `charter.template_catalog`; `mission_type_repository` → `charter.missions`;
  `step_contracts` → `charter.mission_steps`.

### T037 — `tool_surface/bundles/{claude,codex}.py`  [P]
- `artifact_kinds.ArtifactKind` → `charter.drg`; `pack_paths.built_in_dir` → `charter.pack_paths`;
  `agent_profiles` → `charter.profiles`; handle the bare `import doctrine` metadata case per WP04.

### T038 — `upgrade/migrations/{m_2_1_3,m_2_1_4,m_3_2_0rc35}*.py`  [P]
- `missions.repository` → `charter.missions`. Verify migrations still run (they only fire after
  `pip install -e .` — reinstall before testing to avoid stale-install false reds).

## Branch Strategy

Base + merge target `feat/doctrine-public-api-surface`; worktree per lane. Implement via
`spec-kitty agent action implement WP07 --agent <name>` (after WP03, WP04).

## Definition of Done

- [ ] All 18 files import doctrine only via `charter.*`; ratchet baseline shrinks for them.
- [ ] `codex.py` bare metadata import handled per WP04 disposition. No behavior change.
- [ ] Migrations re-verified after reinstall.

## Risks & Reviewer Guidance

- **Risk**: migrations report false reds from a stale install. Reviewer: confirm `pip install -e .`
  before judging migration tests.
- **Reviewer**: confirm `runtime/resolver.py` uses the existing `charter.template_catalog` (no new door needed).
