---
work_package_id: WP05
title: Conduit closure + sole-door fix + service/org-pack CLI migration
dependencies:
- WP03
- WP04
requirement_refs:
- C-005
- FR-004
- FR-005
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
- T027
phase: Phase 3 - Migration
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- src/specify_cli/doctrine/config.py
- src/specify_cli/cli/commands/_doctrine_collect.py
- src/specify_cli/cli/commands/_doctrine_asset.py
- src/specify_cli/cli/commands/doctrine.py
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/_profile_health_render.py
- src/specify_cli/cli/commands/charter/_layer_roots.py
- src/specify_cli/cli/commands/charter/context.py
- src/specify_cli/charter_runtime/lint/checks/org_layer.py
- src/specify_cli/invocation/org_profiles.py
- src/specify_cli/mission_step_contracts/executor.py
role: implementer
tags: []
tracker_refs: []
wp_code: WP05
---

# Work Package Prompt: WP05 — Conduit closure + sole-door fix + service/org-pack CLI migration

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` and apply its initialization, boundaries, directives,
and tactics. State which you applied.

## Objective

Close the first-party re-export laundering conduit **atomically**, migrate the drg/org-pack/service
CLI cluster onto `charter.*` facades, and fix the raw `DoctrineService` sole-door bypasses
**without changing filtering semantics** (FR-004, FR-005, C-005). This is the highest-coupling
migration WP — keep the conduit change atomic.

## Context & Constraints

- Consumes WP03's doors (`charter.drg`, `charter.assets`, `charter.missions`, etc.) and WP04's
  ratchet (baseline shrinks as you migrate).
- **Conduit atomicity:** `specify_cli/doctrine/config.py` re-exports doctrine symbols
  (`resolve_org_roots`, `load_pack_registry`, …) consumed by non-exempt sites. De-export them AND
  repoint every consumer to the `charter.drg` door **in this one WP** — a partial change breaks
  imports at runtime between WPs.
- **Sole-door C-006 trap:** 4 of 5 raw sites (`_doctrine_collect.py:209/314/468/920`) deliberately
  construct with `pack_context=None` (unfiltered by intent). Routing them through
  `build_activation_aware_doctrine_service` would ADD filtering — a behavior change. Use
  `raw_repository()` off the wrapped door (or the builder's documented unfiltered path) for those
  4; only `_doctrine_asset.py:93` (real `pack_context`) uses the activation-aware builder.
- Keep genuinely load-bearing lazy shapes (circular-import/optional-dep/`try-except`) — only change
  the import *target* to `charter.*`.

## Subtasks

### T021 — De-export doctrine symbols from `specify_cli/doctrine/config.__all__`
- Remove doctrine-origin names from `config.__all__` (keep genuine first-party like
  `assert_pack_local_paths_exist`). This satisfies WP04's source-side laundering guard.

### T022 — Repoint config's non-exempt consumers to `charter.drg` (atomic with T021)
- Every non-exempt `from specify_cli.doctrine.config import <doctrine symbol>` → `from charter.drg
  import <symbol>`. Do all together with T021.
- **Full consumer set (post-tasks squad correction — the source-side `__all__` guard does NOT
  catch these):** besides the CLI files this WP already owns, the conduit-only consumers are
  `cli/commands/doctor.py`, `cli/commands/charter/_layer_roots.py`, `cli/commands/charter/context.py`,
  and `charter_runtime/lint/checks/org_layer.py` — all now owned by this WP. De-listing symbols
  from `config.__all__` (T021) makes WP04's guard green but leaves the module binding intact; the
  conduit is only truly closed when these files are repointed AND `config.py` drops its
  `from doctrine.drg.org_pack_config import …` binding. Do all in this one WP.

### T023 — Migrate `_doctrine_collect.py` onto facades
- `drg.models`→`charter.drg`, `service`→sole-door (T026), `agent_profiles.diagnostics`→`charter.profiles`,
  `glossary_packs`→`charter.glossary_packs`, `base`/`drg.override_policy` per WP01 disposition.

### T024 — Migrate `_doctrine_asset.py` onto facades
- `assets.*`→`charter.assets`; service construction → sole-door (T026, this is the filtered site).

### T025 — Migrate `cli/commands/doctrine.py` onto facades
- `org_pack_config`→`charter.drg` (`resolve_org_roots`), `validator`→`charter.drg`
  (`DRGValidationError`), `pack_paths`/`hand_authored_overlay`/mission repos per WP01 disposition.

### T026 — Sole-door: census-confirm, regression-guard (likely already satisfied)
- **Correction (post-tasks squad):** the raw `DoctrineService` sites are **already** wrapped
  inline (`ActivationAwareDoctrineService(RawDoctrineService(...), pack_context=None)`) and
  test-locked by the merged mission `charter-sole-door-bypass-closure-01KZ3WAA` —
  `test_charter_sole_door_doctrine_service.py` already reports zero *unwrapped* constructions and
  `test_unfiltered_diagnostic_sites_pass_none_pack_context` pins `pack_context=None` at the four
  diagnostic sites. So FR-005 is largely **already met**; do NOT introduce a `raw_repository()`
  shape — it would red that existing, un-owned test.
- Task: WP01's re-census confirms the current state. If zero unwrapped sites (expected), this
  subtask is a **regression-guard only** — run the sole-door gate, confirm green, change nothing.
  If the census surfaces a genuinely unwrapped site, wrap it via
  `build_activation_aware_doctrine_service` (filtered) or the wrapped door preserving its existing
  `pack_context`, and only then bring `test_charter_sole_door_doctrine_service.py` into
  `owned_files` with an explicit exclusion-update subtask.

### T027 — Migrate `org_profiles.py`, `mission_step_contracts/executor.py`, `_profile_health_render.py`
- `org_pack_config`→`charter.drg`; `drg.merge` (`OrgDRGConflict`)→`charter.drg`.

## Branch Strategy

Base + merge target `feat/doctrine-public-api-surface`; worktree per lane. Implement via
`spec-kitty agent action implement WP05 --agent <name>` (after WP03, WP04).

## Definition of Done

- [ ] `config.__all__` de-doctrined; all consumers repointed (atomic); source-side laundering guard green.
- [ ] All 7 files import doctrine only via `charter.*`; ratchet baseline shrinks for them.
- [ ] Sole-door test green; the 4 unfiltered sites remain unfiltered (verified), the 1 filtered stays filtered.
- [ ] No behavior change (regression-delta gate).

## Risks & Reviewer Guidance

- **Risk (C-006 trap)**: converting the 4 `pack_context=None` sites into filtered ones. Reviewer:
  diff the filtering behavior of each of the 5 sites before/after.
- **Reviewer**: confirm the conduit closure is atomic (no consumer left importing from
  `specify_cli.doctrine.config` a doctrine symbol).
