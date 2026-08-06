---
work_package_id: WP10
title: Canonical flatten_coordination_metadata primitive (#3219)
dependencies:
- WP08
requirement_refs:
- FR-015
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T049
- T050
- T051
- T052
- T053
- T054
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/mission_metadata.py
create_intent:
- tests/coordination/test_flatten_primitive_single_source.py
- tests/regression/test_mission_close_discard_pops_topology.py
execution_mode: code_change
owned_files:
- src/specify_cli/mission_metadata.py
- src/specify_cli/cli/commands/_coordination_doctor.py
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/migration/backfill_topology.py
- tests/coordination/test_flatten_primitive_single_source.py
- tests/regression/test_mission_close_discard_pops_topology.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Extract **one** canonical `flatten_coordination_metadata(feature_dir)` in `mission_metadata.py` doing
all three coordination-flatten mutations (`del coordination_branch` + `pop topology` +
`flattened=True`) in a single `load → mutate → write_meta(validate=False)`, and converge all three call
sites onto it. **Fix the `mission close --discard` partial-flatten latent bug** (it clears
`coordination_branch` but never pops `topology`, so a discarded coord mission can still route through
coordination and hit `CoordinationBranchDeleted`). Add a non-vacuous single-source arch-guard so a 5th
re-inline reds (this is the 4th touch: #2069→#2120→#2614→#3086/#3218).

## Context

- **Requirements**: FR-015 (canonical flatten primitive); SC-009. Issue #3219.
- **Decision**: **D-PLAN-17** — extract the primitive; import the `topology`/`flattened` key constants
  from `backfill_topology.py` (their semantic owner); converge `merge/executor.py` (#3218),
  `_coordination_doctor.py:816-826`, and `mission_type.py::_flatten_discarded_mission`; correct the
  `mission close --discard` partial flatten; verify the `--push` origin-divergence note.
- **Domain note**: coordination-metadata SSOT, **adjacent to** (not part of) the verdict seam — the same
  canonical-source-unification pattern on a sibling field-set. Independent of the verdict-seam ICs.
- **Dependency assumption**: PR #3218 (the #3086 hotfix) is assumed **landed on the base** — this WP
  converges the executor call site #3218 introduced (`executor.py:1246-1302`). If #3218 is not on the
  base at rebase time, this WP waits (flag it, do not fabricate the call site).
- **Ownership resolution (executor.py shared with WP08)**: `merge/executor.py` is **WP08-owned**. WP10
  depends on WP08 and edits `executor.py:1246-1302` (the `_flatten_coordination_metadata_after_branch_delete`
  region, verified present) as an **out-of-map same-lane convergence edit** — safe because WP08 is fully
  upstream. Rationale: FR-015 requires converging exactly that call site; duplicating executor.py into
  WP10's owned_files would double-own it. This is the ownership-map-leeway pattern (flagged to orchestrator).

Verified anchors: `executor.py:1246` `_flatten_coordination_metadata_after_branch_delete`;
`_coordination_doctor.py:816-826`; `mission_type.py::_flatten_discarded_mission`.

## Subtasks

### T049 — Red-first: `mission close --discard` pops topology (the latent bug)
- **Purpose**: SC-009 — a discarded coord mission must have `topology` popped so it cannot route through
  coordination and hit `CoordinationBranchDeleted`.
- **Steps**: In new `tests/regression/test_mission_close_discard_pops_topology.py`, discard a coord
  mission and assert `meta.json` has **no** `topology` (and `flattened=True`, `coordination_branch`
  gone). Red against the current partial flatten.
- **Files**: `tests/regression/test_mission_close_discard_pops_topology.py`.
- **Validation**: fails before T051; green after.

### T050 — Extract `flatten_coordination_metadata(feature_dir)` in `mission_metadata.py`
- **Purpose**: FR-015 — one primitive doing all three mutations in a single load→mutate→write.
- **Steps**: Implement in `mission_metadata.py` (today `clear_coordination_metadata` does 1 of 3). Do
  all three: `del coordination_branch`, `pop topology`, set `flattened=True`, then a single
  `write_meta(validate=False)`. Import the `topology`/`flattened` key constants from
  `backfill_topology.py` (T052). This also closes the executor's double-write / mid-flatten-crash window.
- **Files**: `src/specify_cli/mission_metadata.py`.
- **Validation**: unit test of the primitive on a coord `meta.json`.

### T051 — Converge the three call sites onto the primitive
- **Purpose**: FR-015 / SC-009 — zero call sites re-inline any of the three mutations.
- **Steps**: Repoint `merge/executor.py` (`:1246-1302`, out-of-map — see Context), `_coordination_doctor.py`
  (`:816-826`), and `mission_type.py::_flatten_discarded_mission` to call the primitive. The
  `mission_type` convergence is what fixes T049 (it currently never pops `topology`).
- **Files**: `src/specify_cli/cli/commands/_coordination_doctor.py`,
  `src/specify_cli/cli/commands/mission_type.py`; out-of-map `src/specify_cli/merge/executor.py`.
- **Validation**: T049 green; all three sites call the one primitive.

### T052 — Promote the `topology`/`flattened` key constants to public, then import them
- **Purpose**: Single semantic owner for the key names (D-PLAN-17).
- **Steps**: The constants exist but are **module-private** — `_TOPOLOGY_KEY = "topology"` and
  `_FLATTENED_KEY = "flattened"` at `backfill_topology.py:37-38` (verified). **Promote them to public
  names** (e.g. `TOPOLOGY_KEY` / `FLATTENED_KEY`, keeping backward-compatible private aliases if any
  in-module use relies on them) so the primitive in `mission_metadata.py` can import them cleanly —
  **do not** string-re-spell `"topology"`/`"flattened"` at the import site (squad #16). Update in-module
  references to the promoted names.
- **Files**: `src/specify_cli/migration/backfill_topology.py`.
- **Validation**: grep confirms the primitive imports the promoted public constants; no inline
  `"topology"`/`"flattened"` literals in the converged sites; `backfill_topology.py`'s own tests green.

### T053 — Non-vacuous single-source arch-guard (SC-009)
- **Purpose**: The 5th re-inline must red (this is the 4th touch).
- **Steps**: In new `tests/coordination/test_flatten_primitive_single_source.py`, assert the
  co-occurring three-mutation set (`del coordination_branch` + `pop topology` + `flattened=True`) exists
  in **exactly one** function — the primitive. Add a synthetic re-inline that reds the guard (non-vacuity).
- **Files**: `tests/coordination/test_flatten_primitive_single_source.py`.
- **Validation**: guard green with one owner; synthetic re-inline reds it.

### T054 — Verify the `--push` origin-divergence note
- **Purpose**: #3218 landing-review residual — `_phase_push` (phase 11) runs before cleanup (phase 12),
  so a `--push` merge lands the flatten bookkeeping commit local-only; origin/target keep the stale
  `coordination_branch`.
- **Steps**: Verify the ordering; if the flatten bookkeeping must reach origin on `--push`, note the
  fix or confirm it is out-of-scope-but-not-regressed. Record the finding in the WP note (do not expand
  scope silently).
- **Files**: (verification) `src/specify_cli/merge/executor.py` phase ordering; WP note.
- **Validation**: the divergence is either fixed or explicitly documented as a known residual.

## Branch Strategy note

`already-confirmed`; base == target. Prepare with `spec-kitty implement WP10`. Depends on WP08 (shared
`executor.py`) and assumes PR #3218 landed on the base. Independent of the verdict-seam chain otherwise.
The executor edit is an out-of-map same-lane convergence (WP08 upstream).

## Definition of Done

- SC-009: the three mutations execute through exactly one canonical primitive (T050/T053); zero call
  sites re-inline any of the three (T051/T052); a discarded coord mission has `topology` popped (T049,
  no residual `CoordinationBranchDeleted` route). The `--push` divergence is verified/documented (T054).
- Gate: `pytest tests/coordination/test_flatten_primitive_single_source.py
  tests/regression/test_mission_close_discard_pops_topology.py
  tests/merge/test_coordination_flatten_on_branch_delete.py
  tests/integration/test_mission_close_discard_coord_teardown.py
  tests/merge/test_coord_deleted_degrade_paths.py -q` green (the three existing suites cover the
  converged call sites — squad #9, all verified present); `ruff` + `mypy --strict src/specify_cli`
  (touched surfaces) clean (NFR-003).

## Risks

- **#3218 not on base** — this WP waits; do not fabricate the executor call site (flag it).
- **4th-touch vacuity** — the arch-guard must be non-vacuous (T053) or a future 5th re-inline slips.
- **Executor region collision with WP08** — edit only the flatten bookkeeping region (`:1246-1302`).

## Reviewer guidance

Confirm all three mutations live in one primitive and all three call sites converge (SC-009). Confirm
the `mission close --discard` path now pops `topology` (T049 red-first). Confirm the arch-guard is
non-vacuous. Confirm the executor edit is confined to the flatten region (WP08 owns the rest).
