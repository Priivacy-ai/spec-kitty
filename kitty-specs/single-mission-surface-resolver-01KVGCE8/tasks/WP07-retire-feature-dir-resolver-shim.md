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
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2057655"
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
This WP is an **import-path bulk edit** (retire `missions/feature_dir_resolver.py`, migrate its importers to the canonical module). At plan time `rg "feature_dir_resolver import" src/` = **51 import sites across ~49 files** (`resolution.py` and `tasks.py` each have 2) — **reconfirm the live count at implement time** and classify exactly that set. Load the `spec-kitty-bulk-edit-classification` skill and produce a **scoped `occurrence_map.yaml`** (the `import_paths` category is primary; classify all 8 categories with explicit actions) BEFORE editing. The caller edits are mechanical import-renames governed by the occurrence map; `owned_files` lists only the retired module (the caller edits are the classified bulk change, recorded with rationale — they run last, after WP06, so there is no parallel-WP collision).

**Cross-owner sites (3) — rationale-noted leeway.** Three importers live in files owned by earlier WPs that run before this one: `src/mission_runtime/resolution.py` (WP05, 2 sites) and `src/specify_cli/coordination/surface_resolver.py` + `coordination/status_transition.py` (WP06). Because WP07 runs **after** WP05/WP06 complete, these are sequential edits (no merge collision), but they are outside `owned_files`. Enumerate them explicitly in `occurrence_map.yaml` with a one-line rationale each (per the ownership-leeway practice). Prefer: if WP05/WP06 already re-pointed their own imports while editing those files, WP07 only needs to confirm 0 residual — note which case applies.

## Objective
Retire the C-004 `missions/feature_dir_resolver.py` strangler shim and migrate all 51 importers to the canonical primitives (unified in WP03) / resolver (WP06). (IC-06; FR-007/T6)

## Context
- `feature_dir_resolver.py` re-exports `candidate_feature_dir_for_mission` + (post-WP03) re-exports the unified `primary_feature_dir_for_mission`. 51 import sites (`rg "feature_dir_resolver import" src/` = 51 at plan time).
- Gated on WP03 (the canonical primitive exists, so migration is behavior-safe) and WP06 (canonical resolver in place).

## Subtasks
### T027 — Classify (occurrence_map.yaml)
- Produce `kitty-specs/single-mission-surface-resolver-01KVGCE8/occurrence_map.yaml`: enumerate every live `feature_dir_resolver import` site (reconfirmed count; ~51); action = rewrite to the canonical module; all 8 categories have an explicit action (most `not_applicable`). Flag the 3 cross-owner sites with rationale.
### T028 — Migrate callers + delete the shim
- Rewrite each import to the canonical source; delete `feature_dir_resolver.py`. Behavior-preserving — and consistent with WP03's **disambiguation** outcome: callers that used the shim's `primary_feature_dir_for_mission` get the canonical **raw-slug** form; any caller that genuinely needed mid8/topology resolution is re-pointed to the resolver (per WP03's recorded per-caller decision), NOT silently changed.
### T029 — Gates (completeness proof, not a gameable regex)
- Deleting the module is the real completeness proof: after deletion, any residual import is an `ImportError` the full suite surfaces. Run `rg -e 'feature_dir_resolver' src/ tests/` → only references gone (0 live), AND `feature_dir_resolver.py` deleted, AND full suite green (catches multiline/module-style imports the single-line regex would miss). `ruff` + `mypy --strict` clean.

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends **WP03** + **WP06** (run last — no parallel WP touches these import sites by then).

## Definition of Done
- [ ] `occurrence_map.yaml` classifies every live site (reconfirmed count; + 8 categories actioned; 3 cross-owner sites flagged with rationale).
- [ ] All importers migrated; `feature_dir_resolver.py` **deleted**; `rg -e 'feature_dir_resolver' src/ tests/` → 0 live references; full suite green (ImportError-clean).
- [ ] Behavior-preserving and consistent with WP03's disambiguation (raw-slug canonical; topology callers re-pointed deliberately); ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk**: a caller relied on the OLD raw-slug behavior (pre-WP03 divergence) — WP03 made the canonical form mid8-composing; verify no caller silently changed dir. (WP02 equivalence + WP03 per-caller tests cover this.)
- **Reviewer**: confirm the occurrence_map covers exactly the importer set; confirm zero `feature_dir_resolver` imports remain; spot-check 3 migrated callsites resolve the same dir.

## Activity Log

- 2026-06-20T11:17:32Z – claude:opus:python-pedro:implementer – shell_pid=2011754 – Assigned agent via action command
- 2026-06-20T11:40:17Z – claude:opus:python-pedro:implementer – shell_pid=2011754 – Shim retired (c23c06e14): 56 sites repointed to _read_path_resolver, 2 real fns relocated byte-identical, 3 cross-owner sites repointed (WP05/WP06 didnt), shim deleted, rg→0 live, broad suite no ImportError (27 fails stash-verified pre-existing), ruff clean 60 files. occurrence_map committed.
- 2026-06-20T11:40:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=2057655 – Started review via action command
- 2026-06-20T12:06:17Z – user – shell_pid=2057655 – reviewer-renata APPROVED: shim deleted, rg→0 live refs, broad suite ImportError-clean (completeness proof), 2 fns relocated byte-identical (lazy mission_runtime import preserved, no cycle), behavior-preservation spot-checks pass, occurrence_map fully classified + 3 cross-owner exceptions, 27 fails + 7 mypy errors confirmed pre-existing on dep base.
