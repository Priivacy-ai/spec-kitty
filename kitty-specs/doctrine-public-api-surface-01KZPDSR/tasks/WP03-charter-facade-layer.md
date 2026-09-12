---
work_package_id: WP03
title: Charter facade layer (symbol-level doors)
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- NFR-002
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 2 - Surface
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- src/charter/missions.py
- src/charter/model_routing.py
- src/charter/assets.py
- src/charter/glossary_packs.py
- src/charter/spdd_reasons.py
- src/charter/pack_paths.py
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- src/charter/drg.py
- src/charter/mission_steps.py
- src/charter/missions.py
- src/charter/model_routing.py
- src/charter/assets.py
- src/charter/glossary_packs.py
- src/charter/spdd_reasons.py
- src/charter/pack_paths.py
- src/charter/template_catalog.py
- tests/architectural/test_charter_facades_reexport_doctrine.py
role: implementer
tags: []
tracker_refs: []
wp_code: WP03
---

# Work Package Prompt: WP03 — Charter facade layer

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and apply its initialization, boundaries, directives,
and tactics. State which you applied.

## Objective

Grow the sanctioned `charter.*` doors so every PUBLIC / FACADE-ONLY doctrine path from WP01 has a
**symbol-level object-identity** re-export listed in `__all__`. This is what lets WP05–07 migrate
runtime off direct `doctrine.*` imports (FR-003, NFR-002, C-002).

## Context & Constraints

- The facade-identity gate `test_charter_facades_reexport_doctrine.py` asserts `facade.X is
  doctrine.X` and `X in facade.__all__`. Grow its `_FACADE_TABLE` for every new row.
- **Symbol-level, not whole-module.** `charter.model_routing` must re-export the callables
  `load`, `evaluate`, `RoutingRecommendation` — NOT the `evaluator`/`loader` submodules (a
  whole-module re-export passes identity but defeats curation).
- **PUBLIC symbols re-export from `doctrine.api`** (so WP02's dead-symbol gate has live callers);
  FACADE-ONLY-but-not-public symbols re-export from their origin submodule. Identity holds either
  way (`charter.X is doctrine.api.X is doctrine.<submodule>.X`).
- `DoctrineService` is NOT a facade row — it is the activation-aware wrapper (WP05 sole-door).

## Subtasks

### T010 — Widen `charter.drg`
- Add: `DRGLoadError`, `DRGValidationError`, `resolve_org_roots`, `OrgDRGConflict` (already exports
  `OrgDRGConflictError`). These absorb the whole `drg.*` reach-through cluster.

### T011 — Widen `charter.mission_steps`
- Add `GateBinding` (module is already fronted; the symbol is not).

### T012 — New `charter.missions`
- Re-export `MissionTemplateRepository`, `MissionsRootNotFound`, `MissionTypeRepository`,
  `builtin_mission_type_ids`, and (if WP01 dispositioned them FACADE-ONLY) `project_template_set`
  / `MissionStepRepository`.

### T013 — New `charter.model_routing` (symbol-level)
- Re-export `load` (from `doctrine.model_task_routing.loader`), `evaluate`, `RoutingRecommendation`
  (from `doctrine.model_task_routing.evaluator`). Confirmed no import cycle (model_task_routing
  imports only doctrine/kernel).

### T014 — New `charter.assets`
- Re-export `AssetRepository`, `AssetManifest`, `AssetNotFoundError`, `AssetPathEscapeError`.

### T015 — Narrow doors
- `charter.glossary_packs` (`GlossaryPack`), `charter.spdd_reasons` (`apply_spdd_blocks_for_project`),
  `charter.pack_paths` (`built_in_dir`, `built_in_root` — only the FACADE-ONLY symbols per WP01).
- **Widen `charter.template_catalog`** (post-tasks squad correction — data-model's "existing" was
  incomplete): it exports `TierRoot` but NOT `resolve_template_by_id`, which `runtime/resolver.py:528`
  (migrated in WP07/T036) needs. Add `resolve_template_by_id` to its `__all__` + `_FACADE_TABLE`,
  else T036 cannot green.

### T016 — Grow `_FACADE_TABLE` + wire PUBLIC from `doctrine.api`
- Add every new symbol/module pair; point PUBLIC symbols at `doctrine.api`. Run the identity test.

## Branch Strategy

Base + merge target `feat/doctrine-public-api-surface`; worktree per lane. Implement via
`spec-kitty agent action implement WP03 --agent <name>` (after WP01, WP02).

## Definition of Done

- [ ] All 8 door groups exist; every re-export symbol-level identity + in `__all__`.
- [ ] `_FACADE_TABLE` grown; PUBLIC symbols re-export from `doctrine.api`; identity test green.
- [ ] `mypy --strict` clean; no import cycle; `DoctrineService` not added to the table.

## Risks & Reviewer Guidance

- **Risk**: whole-module re-export of `model_routing` (passes identity, defeats curation).
  Reviewer: confirm `charter.model_routing.__all__` lists callables, not submodules.
- **Reviewer**: confirm PUBLIC rows point at `doctrine.api` (else WP02's dead-symbol gate degrades).
