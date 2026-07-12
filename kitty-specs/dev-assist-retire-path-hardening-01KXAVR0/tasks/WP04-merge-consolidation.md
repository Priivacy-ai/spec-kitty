---
work_package_id: WP04
title: Merge-family compat-surface consolidation
dependencies: []
requirement_refs:
- FR-005
- FR-006
- NFR-002
- C-002
- C-003
tracker_refs:
- '2565'
planning_base_branch: feat/dev-assist-retire-path-hardening
merge_target_branch: feat/dev-assist-retire-path-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/dev-assist-retire-path-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dev-assist-retire-path-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dev-assist-retire-path-hardening-01KXAVR0
base_commit: 4e129fc35c2c4d8ee3b87208b14e6c2be7c9c237
created_at: '2026-07-12T11:55:01.891741+00:00'
subtasks:
- T001
- T002
- T003
phase: Compat-surface consolidation
shell_pid: "346367"
agent: "claude"
history:
- at: '2026-07-12T10:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-07-12T10:40:00Z'
  actor: claude
  action: Revised per post-tasks squad (Lens A/B/D) — corrected battery inventory (7 across 8 files, 4 names; forecast none), added {symbol→residual} map + identity-vs-native-redefine check, folded the ×8 one-way-import guards.
agent_profile: python-pedro
authoritative_surface: tests/merge/
create_intent:
- tests/merge/test_merge_compat_surface.py
execution_mode: code_change
owned_files:
- tests/merge/test_merge_compat_surface.py
- tests/merge/test_git_probes_seam.py
- tests/merge/test_constants_seam.py
- tests/merge/test_forecast_seam.py
- tests/merge/test_resolve_seam.py
- tests/merge/test_preflight_seam.py
- tests/merge/test_ordering_bake_seam.py
- tests/merge/test_done_bookkeeping_seam.py
- tests/merge/test_bookkeeping_projection_seam.py
role: implementer
tags: []
task_type: implement
---

# WP04 — Merge-family compat-surface consolidation

## Context

The merge decomposition left per-seam re-export identity batteries across `tests/merge/*_seam.py` — real, unique coverage of private relocated symbols (not covered by `tests/specify_cli/cli/commands/test_merge_cli_golden.py`, which only pins public commands), so **not deletable**, but fragmented and re-breaking per-seam. Consolidate to one guard (the `test_bridge_compat_surface.py` / `test_mission_shim_reexports.py` shape). Superset coverage is mandatory (NFR-002). Do NOT introduce a cross-family shared helper — keep this guard self-contained per the codebase convention (`test_bridge_compat_surface.py:132-138`).

### Ground truth — the batteries are NOT uniform (post-tasks squad Lens A/B)

The identity batteries are **8 test functions across 7 of the 8 seam files, under 4 different names, over 4 different constants — `forecast_seam.py` has NONE**. A literal grep of `test_shim_re_exports_the_same_object` finds only 5/8. Real inventory + the `{symbol → residual-module}` mapping (a flat name-union is WRONG — each seam re-exports from a different residual, and `preflight` splits across TWO):

| seam file | identity test(s) | constant | residual module |
|-----------|------------------|----------|-----------------|
| `test_git_probes_seam.py` | `test_shim_re_exports_the_same_object` | `RELOCATED_NAMES` | git_probes |
| `test_bookkeeping_projection_seam.py` | `test_shim_re_exports_the_same_object` | `SHIM_REEXPORTED` | `bp` |
| `test_done_bookkeeping_seam.py` | `test_shim_re_exports_the_same_object` | `SHIM_REEXPORTED` | `db` |
| `test_resolve_seam.py` | `test_shim_re_exports_the_same_object` | `SHIM_REEXPORTED` | resolve |
| `test_constants_seam.py` | `test_shim_re_exports_the_same_object` | (inline) | `_constants` |
| `test_ordering_bake_seam.py` | `test_shim_re_exports_bake_entrypoint` | (single symbol) | ordering |
| `test_preflight_seam.py` | `test_shim_re_exports_preflight_object` **and** `test_shim_re_exports_push_preflight_object` | `SHIM_REEXPORTED_FROM_PREFLIGHT`, `SHIM_REEXPORTED_FROM_PUSH_PREFLIGHT` | merge.preflight **and** merge.push_preflight (#1706 boundary) |
| `test_forecast_seam.py` | — none — | — | — |

## Approach

1. **T001 — author the consolidated guard** `tests/merge/test_merge_compat_surface.py`: iterate a `{symbol → residual-module}` MAP (not a flat name union) covering all seams' relocated symbols, asserting each is the identical object (`getattr(shim, name) is getattr(residual, name)`). **Before adding a symbol to the `is`-assertion set, confirm it is a genuine identity re-export, not a native re-definition** (cf. the `_load_feature_runs` hazard in `test_bridge_io.py`, mapped via a redefinition tuple). Assert the consolidated map's key-set is a strict **superset** of the union of the retired batteries so a dropped symbol fails.
2. **T002 — retire the fragmented scaffolding**: remove the 8 identity test functions above (folded into T001); remove the tautological byte-identical-literal pins in `test_constants_seam.py` (`test_relocated_string_literals_are_byte_identical`, `test_type_aliases_are_preserved`, `test_logger_namespace_is_preserved`). **Consolidate the ×8 byte-identical one-way-import guards** (`test_<seam>_does_not_import_the_command_shim`, identical AST-walk bodies at `test_git_probes_seam.py:48`, `bookkeeping_projection:42`, `done_bookkeeping:40`, `resolve:41`, `forecast:51`, `preflight:94`, `ordering_bake:35`, `constants:76`) into ONE parametrized guard (over `(module, alias)` pairs) in the new compat-surface file — do not keep 8 copies. KEEP each seam file's genuine functional tests (`_classify_porcelain_lines`, `_lane_already_integrated`, …) and external-contract literal pins (`_STATUS_FILENAME == "status.json"`, `_STATUS_EVENTS_FILENAME`).
3. **T003 — verify + anti-vacuity**: prove the consolidated key-set ⊇ union of retired batteries (no dropped private symbol); plant a broken re-export in a merge seam → the consolidated guard fails → revert; `PWHEADLESS=1 uv run pytest tests/merge/ -q` green.

## Acceptance

- One consolidated merge compat guard (symbol→residual map, identity-verified) + one parametrized import guard; the 8 identity batteries + tautological literal pins + 8 duplicated import guards retired; functional + external-contract tests preserved.
- Superset coverage proven; planted regression caught; merge suite green; `ruff` clean.

## Branch Strategy

Planning branch: `feat/dev-assist-retire-path-hardening`; final merge target the same (PR'd to `main`). Worktree per computed lane from `lanes.json`.

## Activity Log

- 2026-07-12T12:10:53Z – claude – shell_pid=346367 – Moved to for_review
- 2026-07-12T12:19:18Z – claude – shell_pid=346367 – LAND review ae26da13 (pre-existing merge fail independently confirmed on base)
