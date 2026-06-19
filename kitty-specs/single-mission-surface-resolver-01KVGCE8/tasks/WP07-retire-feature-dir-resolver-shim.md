---
work_package_id: WP07
title: Retire the feature_dir_resolver shim (51-importer bulk-edit)
dependencies:
- WP03
- WP06
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
agent: claude
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: 'WP authored from plan IC-06/T6 (FR-007). Bulk-edit: 51 import sites via scoped occurrence_map.'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/feature_dir_resolver.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/missions/feature_dir_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Bulk-edit notice
This WP is an **import-path bulk edit** (retire `missions/feature_dir_resolver.py`, migrate its **51 importers** to the canonical module). Load the `spec-kitty-bulk-edit-classification` skill and produce a **scoped `occurrence_map.yaml`** (the `import_paths` category is primary; classify all 8 categories with explicit actions) BEFORE editing. The 51 caller edits are mechanical import-renames governed by the occurrence map; `owned_files` lists only the retired module (the caller edits are the classified bulk change, recorded with rationale — they run last, after WP06, so there is no parallel-WP collision).

## Objective
Retire the C-004 `missions/feature_dir_resolver.py` strangler shim and migrate all 51 importers to the canonical primitives (unified in WP03) / resolver (WP06). (IC-06; FR-007/T6)

## Context
- `feature_dir_resolver.py` re-exports `candidate_feature_dir_for_mission` + (post-WP03) re-exports the unified `primary_feature_dir_for_mission`. 51 import sites (`rg "feature_dir_resolver import" src/` = 51 at plan time).
- Gated on WP03 (the canonical primitive exists, so migration is behavior-safe) and WP06 (canonical resolver in place).

## Subtasks
### T027 — Classify (occurrence_map.yaml)
- Produce `kitty-specs/single-mission-surface-resolver-01KVGCE8/occurrence_map.yaml`: enumerate the 51 `from ...feature_dir_resolver import X` sites; action = rewrite to the canonical module; all 8 categories have an explicit action (most `not_applicable`).
### T028 — Migrate callers + delete the shim
- Rewrite each import to the canonical source; delete `feature_dir_resolver.py`. Behavior-preserving (the canonical primitive is the WP03-unified one).
### T029 — Gates
- `rg "feature_dir_resolver import" src/` → 0; `ruff` + `mypy --strict` clean; full suite green (the migration touches many packages — run broadly).

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends **WP03** + **WP06** (run last — no parallel WP touches these import sites by then).

## Definition of Done
- [ ] `occurrence_map.yaml` classifies all 51 sites (+ 8 categories actioned).
- [ ] All importers migrated; `feature_dir_resolver.py` deleted; `rg "feature_dir_resolver import" src/` → 0.
- [ ] Behavior-preserving (canonical primitive = WP03's unified def); ruff + mypy --strict clean; full suite green.

## Risks / Reviewer guidance
- **Risk**: a caller relied on the OLD raw-slug behavior (pre-WP03 divergence) — WP03 made the canonical form mid8-composing; verify no caller silently changed dir. (WP02 equivalence + WP03 per-caller tests cover this.)
- **Reviewer**: confirm the occurrence_map covers exactly the importer set; confirm zero `feature_dir_resolver` imports remain; spot-check 3 migrated callsites resolve the same dir.
