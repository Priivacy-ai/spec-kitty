---
work_package_id: WP09
title: Route _mission_id to the PRIMARY leg (#2966 part-1 remainder)
dependencies: []
requirement_refs:
- FR-008
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-read-side-placement-seam-migration-01KYHP67
base_commit: 6ee1927d2661de11991a0161e74c542fb46bfe0e
created_at: '2026-07-27T12:35:21.607789+00:00'
subtasks:
- T021
- T022
- T023
phase: Phase 1 - Bugfix
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/backfill_runtime_state.py
create_intent:
- tests/specify_cli/migration/test_mission_id_primary_leg.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/migration/backfill_runtime_state.py
- tests/specify_cli/migration/test_mission_id_primary_leg.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – Route _mission_id to the PRIMARY leg (#2966 part-1 remainder)

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `python-pedro` (implementer, claude).

## Objective
#2966 part-1's remaining half. `backfill_runtime_state._mission_id(feature_dir)` (`:250`, reads `load_meta(feature_dir, ...)` at `:257`) reads `meta.json` from the caller-passed leg. For coord topology that leg is the COORD leg, which has **no `meta.json`** (`PRIMARY_METADATA` lives only on PRIMARY per `core/paths.py`), so the deterministic seed ULIDs namespace on the coord **directory name** and the store logs "orphaned event; mission_id will be None". Route `_mission_id` to read from the PRIMARY `read_dir` leg — exactly as Mission E already did for `_synthesize_claim_anchor` (`:463`, which reads `load_meta(read_dir, ...)`; use it as the pattern/reference).

NOTE: `_synthesize_claim_anchor`'s half of #2966 part-1 is ALREADY fixed (by Mission E) — do not redo it. This WP is only the `_mission_id` leg.

## Subtasks
### T021 — Red-first repro
`tests/specify_cli/migration/test_mission_id_primary_leg.py`: build a coord-rooted fixture where `feature_dir` (COORD leg) has no `meta.json` but the PRIMARY `read_dir` carries `meta.json` with a known `mission_id`. Drive the seed path and assert (RED) that seed ULIDs currently namespace on the dir name / mission_id is None.
### T022 — Route to read_dir
Thread the PRIMARY `read_dir` leg into `_mission_id` (mirror the `_synthesize_claim_anchor` signature/leg-pin) so it reads `load_meta(read_dir, ...)`. Update all callers to pass `read_dir` (the seed/verify paths already thread `read_dir`). Keep fail-closed behavior when meta is genuinely absent on PRIMARY.
### T023 — Green
Assert seed ULIDs namespace on the mission ULID from PRIMARY `meta.json`; no "orphaned event" warning for the coord-rooted fixture.

## Gates (`uv run`)
`PWHEADLESS=1 uv run pytest tests/specify_cli/migration/test_mission_id_primary_leg.py -q`; `PWHEADLESS=1 uv run pytest -n0 tests/specify_cli/migration/ -q` (no regression; classify pre-existing reds); `ruff`; `mypy src/specify_cli/migration/backfill_runtime_state.py` (project-mode).

## DoD / Review
`_mission_id` reads PRIMARY `read_dir`; seed ULIDs namespace on the mission ULID; `_synthesize_claim_anchor` untouched (E already did it); no regression. Finish: commit, `mark-status T021 T022 T023 --status done`, `move-task WP09 --to for_review`.
