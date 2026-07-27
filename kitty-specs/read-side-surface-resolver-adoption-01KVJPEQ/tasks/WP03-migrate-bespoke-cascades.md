---
work_package_id: WP03
title: Migrate the 5 bespoke cascades (incl. runtime fold-in)
dependencies:
- WP01
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: feat/read-side-surface-resolver-adoption
merge_target_branch: feat/read-side-surface-resolver-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/read-side-surface-resolver-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-side-surface-resolver-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2392474"
history:
- at: '2026-06-20T14:30:00Z'
  actor: claude
  note: WP authored from plan IC-02b (FR-002/C-007). The 5 bespoke mid8 cascades (workflow, resolution, runtime fold-in, tasks:4047, acceptance).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/workflow.py
create_intent: []
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/mission_runtime/resolution.py
- src/runtime/next/runtime_bridge.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/acceptance/__init__.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Route the **five bespoke mid8 cascades** (no raw join, but the same disease — a hand-rolled `meta→mid8→resolve_mission_read_path` cascade, or a direct mid8-blind primitive call) through WP01's seam / the canonical `resolve_declared_mid8`. (IC-02b; FR-002, C-007)

## Context (squad scope-undersizing finding — code-verified 8-caller enumeration)
The 8 direct `resolve_mission_read_path` callers in `src/` are {orchestrator (seam source, WP01), context/mission/decision (WP02), workflow/resolution/runtime_bridge/tasks/acceptance (THIS WP)}. The five here:
- `agent/workflow.py:302-324` `_mid8_for_mission_read_path`/`_canonical_status_feature_dir` (3 read callers at :1349/:1433/:2302) — own `_load_coord_branch_meta` → `meta_mid8` → `resolve_mid8` cascade.
- `mission_runtime/resolution.py:_mid8_from_primary_meta` (~:185/:211) — `meta.mid8` → `mission_id[:8]` cascade ("mirrors `_coord_mid8` by hand").
- `runtime/next/runtime_bridge.py:2431-2450` `_resolve_runtime_feature_dir` (callers :2127/:2470) — `_resolve_mission_ulid` → `resolve_mid8` cascade.
- **`agent/tasks.py:4047-4052`** (squad F7) — `_mid8 = resolve_mid8(mission_slug, mission_id=None)` (mid8-BLIND for a bare slug → "" → silent primary read) then `resolve_mission_read_path(main_repo_root, mission_slug, _mid8)`. It *calls* the primitive but with empty mid8 — the exact #2046 disease. The inline comment claiming a "canonical-handle fallback re-derives the real mid8" is contradicted by 01KVGCE8's `coord-fresh/bare` strict-xfail — the primitive is mid8-blind for a bare slug. MUST migrate.
- **`acceptance/__init__.py:590-606`** `_status_read_feature_dir` — hand-rolled `meta.get("mid8") || mid8_from_slug(feature)` cascade + a direct `resolve_mission_read_path` call. Reads canonical `meta.mid8` first (so less broken than tasks.py), but the `mid8_from_slug` fallback is blind and it is a **parallel selection path**. Route the mid8 derivation through `resolve_declared_mid8`/the seam; preserve the acceptance-specific `status_dir if status_dir.exists() else feature_dir` fallback.
- **C-007 RESOLVED = FOLD IN** (boundary-safe): `runtime_bridge.py` ALREADY imports `specify_cli.missions._read_path_resolver` (line 87) + `resolve_mission_read_path` (:2443), so routing it through the seam adds NO new package-boundary edge.

## Subtasks
### T010 — Migrate `workflow.py:302-324` [P]
- Replace `_mid8_for_mission_read_path`'s bespoke cascade with the seam; the 3 read callers (`:1349/:1433/:2302`) consume the seam's dir. Preserve dependency-readiness/status behavior.
### T011 — Migrate `mission_runtime/resolution.py:_mid8_from_primary_meta`
- Replace the hand-rolled `meta.mid8`/`mission_id[:8]` cascade with the seam (or, if this is an internal mid8-only helper, route it through `resolve_declared_mid8` — the canonical cascade — so it is no longer a parallel implementation). Verify callers unchanged.
### T012 — Migrate `runtime_bridge.py:2431-2450` (FOLD-IN)
- Route `_resolve_runtime_feature_dir` through the seam (boundary-safe per C-007). Callers `:2127/:2470` consume it. Preserve the runtime read-path behavior.
### T025 — Migrate `tasks.py:4047-4052` (squad F7 mid8-blind residual)
- Replace `_mid8 = resolve_mid8(mission_slug, mission_id=None)` + the direct `resolve_mission_read_path` call with the seam `resolve_handle_to_read_path(main_repo_root, mission_slug)`. Remove the stale inline comment claiming a "canonical-handle fallback re-derives the real mid8" (the matrix proves the primitive is mid8-blind for a bare slug). Preserve the #984/#1918 legacy-fallback intent if the seam does not already cover it; if it does, note the subsumption.
### T026 — Migrate `acceptance/__init__.py:590-606` `_status_read_feature_dir`
- Replace the `meta.get("mid8") || mid8_from_slug(feature)` mid8 cascade with the canonical derivation (route mid8 through `resolve_declared_mid8` / the seam). Preserve the acceptance-specific `status_dir if status_dir.exists() else feature_dir` fallback. This removes the last parallel selection path so FR-006's ratchet needs NO acceptance allowlist entry.
### T013 — Per-site subsumption verify
- For each of the five sites: confirm the seam's `resolve_declared_mid8` subsumes the old cascade (same mid8 derived for the same meta) and the same dir resolves for `<slug>-<mid8>`/full-id. Note any divergence (e.g. workflow's `_load_coord_branch_meta` reads the coord branch meta vs the seam's primary meta — confirm the seam's primary-anchored read is correct for the read path, or flag).

## Branch Strategy
Planning/base + merge target: `feat/read-side-surface-resolver-adoption`. Worktree per lane. Depends **WP01** (the seam).

## Definition of Done
- [ ] All 5 bespoke cascades (workflow, resolution, runtime_bridge, tasks:4047, acceptance) routed through the seam (or the canonical `resolve_declared_mid8`); no parallel `resolve_mid8`/`mid8_from_slug` cascade remains at these sites.
- [ ] `tasks.py:4047` no longer passes `mission_id=None` (the F7 mid8-blind path); the stale "canonical-handle fallback" comment removed.
- [ ] `acceptance._status_read_feature_dir` keeps its `.exists() else feature_dir` fallback but derives mid8 canonically — no acceptance allowlist entry needed for FR-006.
- [ ] runtime_bridge fold-in is boundary-safe (no new import edge — it already imports `_read_path_resolver`).
- [ ] Per-site subsumption verified (same dir for non-bare-slug); behavior-preserving.
- [ ] ruff + mypy --strict clean; `tests/mission_runtime/` + agent/workflow + agent/tasks + acceptance + runtime tests pass.

## Risks / Reviewer guidance
- **Risk (subtlety)**: `workflow._load_coord_branch_meta` reads the COORD branch's meta, while the seam reads PRIMARY meta. For mid8 derivation the primary anchor is correct (mid8 is identity, same on both), but verify no caller relied on coord-branch-specific meta fields.
- **Reviewer**: confirm each site routes through the seam/canonical cascade; confirm runtime_bridge fold-in added no boundary violation (check `tests/architectural/test_shared_package_boundary.py` still passes); spot-check subsumption.

## Activity Log

- 2026-06-20T16:37:08Z – claude:opus:python-pedro:implementer – shell_pid=2352485 – Assigned agent via action command
- 2026-06-20T16:54:54Z – claude:opus:python-pedro:implementer – shell_pid=2352485 – 5 bespoke cascades → seam/resolve_declared_mid8; runtime_bridge fold-in boundary-safe (44 passed); tasks.py:4047 mission_id=None removed; acceptance fallback preserved; lane b07c6c579
- 2026-06-20T16:55:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=2392474 – Started review via action command
- 2026-06-20T17:02:22Z – user – shell_pid=2392474 – reviewer-renata APPROVE: 5 cascades→seam, coord→primary meta switch safe (mid8=mission_id identity), runtime_bridge boundary-safe (44 passed), tasks.py F7 fixed, acceptance fallback preserved, 6 mypy errors baseline-confirmed
