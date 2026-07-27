---
description: "Work package task list — Decompose the merge.py God-Module (#2057)"
---

# Work Packages: Decompose the `merge.py` God-Module (#2057)

**Inputs**: Design documents from `/kitty-specs/decompose-merge-god-module-01KVXHDK/`
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/cli-surface-contract.md, quickstart.md

**Tests**: Test work is explicit and load-bearing. WP01 captures the golden CLI characterization test FIRST (byte-identity proof). Every seam WP ships focused per-seam tests (≥90% coverage of moved code). The executor WP adds a #1827 phase-boundary regression test.

**Organization**: This is a **strictly-linear WP chain** — WP01 → WP02 → … → WP11, each WP depending ONLY on the immediately-preceding WP. This keeps lanes nesting cleanly (avoiding the multi-lane divergence that plagued #2058).

**Ownership model (zero owned_files overlap)**: each seam WP owns ONLY its new/extended seam module(s) + its test file. `src/specify_cli/cli/commands/merge.py` is owned SOLELY by the final WP (WP11). Seam WPs make small, documented out-of-map wiring edits to `merge.py` to import-from / re-export the relocated seam; those edits are not ownership claims.

**Prompt Files**: Each WP references a matching prompt file in `/tasks/`.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components) within a WP. Across WPs the chain is strictly serial.

## Path Conventions

- Single Python project: `src/specify_cli/`, `tests/`. Seam package: `src/specify_cli/merge/`. Shim: `src/specify_cli/cli/commands/merge.py`.

---

## Work Package WP01: Golden CLI characterization harness (Priority: P1) 🎯 GATE

**Goal**: Capture the `spec-kitty merge` byte-identity contract against the PRE-refactor module via Typer `CliRunner` on the fully registered app.
**Independent Test**: Golden test passes on the current module and pins help/flags/dry-run-JSON/error-paths.
**Prompt**: `/tasks/WP01-golden-cli-harness.md`
**Requirement Refs**: FR-001, C-005

### Included Subtasks
- [x] T001 Author `tests/specify_cli/cli/commands/test_merge_cli_golden.py` invoking the registered app (WP01)
- [x] T002 Snapshot `merge --help`, every flag/default + hidden `--feature` alias (WP01)
- [x] T003 Pin the `--json`-without-`--dry-run` error string + exit 1 (WP01)
- [x] T004 Pin the `--dry-run --json` payload key set + headline error/exit-code paths (WP01)
- [x] T005 Run on the pre-refactor module; record the baseline as the byte-identity proof (WP01)

### Dependencies
- None (gate; authored first per ATDD; gates the entire chain).

### Risks & Mitigations
- Re-wrapping the command instead of the registered app → invoke through the real app object.

---

## Work Package WP02: Shared constants seam — `merge/_constants.py` (Priority: P1)

**Goal**: Centralize shared literals / type aliases / logger into `merge/_constants.py` (S1192-safe foundation).
**Independent Test**: `merge/_constants.py` imports cleanly; golden test still green; constants byte-identical.
**Prompt**: `/tasks/WP02-constants-seam.md`
**Requirement Refs**: FR-003, C-008, NFR-003

### Included Subtasks
- [x] T006 Create `src/specify_cli/merge/_constants.py` with the shared literals/aliases/logger (WP02)
- [x] T007 Preserve `LINEAR_HISTORY_REJECTION_TOKENS` order/membership byte-for-byte (WP02)
- [x] T008 Wire `merge.py` to import from `_constants` + re-export for `__all__` (WP02)
- [x] T009 Add `tests/merge/test_constants_seam.py` covering the moved constants (WP02)

### Dependencies
- WP01.

### Risks & Mitigations
- Constant drift → assert exact tuple in the seam test.

---

## Work Package WP03: Git primitives seam — `merge/git_probes.py` (Priority: P1)

**Goal**: Relocate branch/tree/porcelain git primitives incl. public `path_is_under_worktrees`.
**Independent Test**: `git_probes` imports cleanly; `path_is_under_worktrees` re-exported; doctor/mission importers green.
**Prompt**: `/tasks/WP03-git-probes-seam.md`
**Requirement Refs**: FR-003, FR-006, C-006

### Included Subtasks
- [x] T010 Create `src/specify_cli/merge/git_probes.py`; move branch/tree/porcelain primitives (WP03)
- [x] T011 Re-export `path_is_under_worktrees` from the shim (doctor.py + agent/mission.py importers) (WP03)
- [x] T012 Wire `merge.py` import-from + re-export; confirm one-way imports (WP03)
- [x] T013 Add `tests/merge/test_git_probes_seam.py` (≥90% of moved code) (WP03)

### Dependencies
- WP02.

### Risks & Mitigations
- Breaking doctor/mission imports → re-export and run those importers' tests.

---

## Work Package WP04: Slug/state/target resolution seam — `merge/resolve.py` (Priority: P1)

**Goal**: Relocate slug extraction, merge-state load/clear/cleanup, and target-branch resolution.
**Independent Test**: `resolve` imports cleanly; `_resolve_mission_slug`/`_resolve_target_branch` re-exported; resolver tests green.
**Prompt**: `/tasks/WP04-resolve-seam.md`
**Requirement Refs**: FR-003, FR-006, C-002

### Included Subtasks
- [x] T014 Create `src/specify_cli/merge/resolve.py`; move slug/state/target resolvers (consuming `merge/state.py`) (WP04)
- [x] T015 Re-export the test-imported resolvers from the shim (WP04)
- [x] T016 Wire `merge.py` import-from + re-export (WP04)
- [x] T017 Add `tests/merge/test_resolve_seam.py` (≥90% of moved code) (WP04)

### Dependencies
- WP03.

### Risks & Mitigations
- State-key candidate ordering → preserve exactly; cover in seam test.

---

## Work Package WP05: Preflight seam — extend `merge/preflight.py` (Priority: P1)

**Goal**: Relocate git/target/mission-branch/review-artifact/hollow-review preflights; split `_collect_hollow_review_warnings` (CC21) to ≤15.
**Independent Test**: Preflight importers green; `_collect_hollow_review_warnings` ≤15 CC; existing preflight tests pass.
**Prompt**: `/tasks/WP05-preflight-seam.md`
**Requirement Refs**: FR-003, FR-005, FR-006, C-002

### Included Subtasks
- [x] T018 Relocate preflight functions into `merge/preflight.py` (+ `push_preflight.py` support) (WP05)
- [x] T019 Split `_collect_hollow_review_warnings` into helpers, each ≤15 CC (WP05)
- [x] T020 Re-export test-imported preflight symbols from the shim (WP05)
- [x] T021 Wire `merge.py` import-from + re-export (WP05)
- [x] T022 Extend `tests/merge/test_*preflight*.py` / add focused tests for the split (≥90%) (WP05)

### Dependencies
- WP04.

### Risks & Mitigations
- Review-artifact gate behavior → keep `post_merge.review_artifact_consistency` as leaf dep; cover both branches.

---

## Work Package WP06: Forecast seam — `merge/forecast.py` (Priority: P1)

**Goal**: Extract the dry-run preview + JSON/human payload build out of the `merge` body.
**Independent Test**: Dry-run JSON key set unchanged (golden test green); forecast unit tests pass.
**Prompt**: `/tasks/WP06-forecast-seam.md`
**Requirement Refs**: FR-001, FR-003, FR-004

### Included Subtasks
- [x] T023 Create `src/specify_cli/merge/forecast.py`; move dry-run preview/payload build (WP06)
- [x] T024 Preserve dry-run JSON key set + `REJECTED_REVIEW_ARTIFACT_CONFLICT` emission (WP06)
- [x] T025 Wire `merge.py` import-from (WP06)
- [x] T026 Add `tests/merge/test_forecast_seam.py` (≥90% of moved code) (WP06)

### Dependencies
- WP05.

### Risks & Mitigations
- Dry-run schema drift → assert exact key set; golden test re-run.

---

## Work Package WP07: Mission-number bake seam — extend `merge/ordering.py` (Priority: P1)

**Goal**: Relocate the mission-number bake cluster into `merge/ordering.py`.
**Independent Test**: `_bake_mission_number_into_mission_branch` re-exported; idempotency tests pass.
**Prompt**: `/tasks/WP07-ordering-bake-seam.md`
**Requirement Refs**: FR-003, FR-006, C-002

### Included Subtasks
- [x] T027 Relocate the bake cluster into `merge/ordering.py` (WP07)
- [x] T028 Re-export `_bake_mission_number_into_mission_branch` from the shim (WP07)
- [x] T029 Wire `merge.py` import-from + re-export; keep lazy imports lazy (WP07)
- [x] T030 Extend `tests/merge/test_mission_number_*` / add focused bake tests (≥90%) (WP07)

### Dependencies
- WP06.

### Risks & Mitigations
- `_write_mission_number_to_branch` (154 LOC) git-worktree heavy → relocate verbatim; lazy imports unchanged.

---

## Work Package WP08: Done-bookkeeping seam — `merge/done_bookkeeping.py` (Priority: P1)

**Goal**: Relocate done/approved transition emission + done asserts + resume reconcile; split `_mark_wp_merged_done` (CC22) and `_assert_merged_wps_done_on_target` (CC16) to ≤15.
**Independent Test**: `_mark_wp_merged_done` re-exported (orchestrator_api importer green); done-recording tests pass; both split fns ≤15 CC.
**Prompt**: `/tasks/WP08-done-bookkeeping-seam.md`
**Requirement Refs**: FR-003, FR-005, FR-006

### Included Subtasks
- [x] T031 Create `src/specify_cli/merge/done_bookkeeping.py`; move done/approved emission + asserts + reconcile (WP08)
- [x] T032 Split `_mark_wp_merged_done` (PLANNED-fallback/force-done/dedup) into helpers ≤15 CC (WP08)
- [x] T033 Split `_assert_merged_wps_done_on_target` to ≤15 CC (WP08)
- [x] T034 Re-export `_mark_wp_merged_done` + asserts from the shim (orchestrator_api/commands.py importer) (WP08)
- [x] T035 Wire `merge.py` import-from + re-export (WP08)
- [x] T036 Add `tests/merge/test_done_bookkeeping_seam.py` (≥90%, exercises split branches) (WP08)

### Dependencies
- WP07.

### Risks & Mitigations
- Intricate dedup/force branching → focused tests per branch; preserve behavior exactly.

---

## Work Package WP09: Bookkeeping-projection / snapshot seam — `merge/bookkeeping_projection.py` (Priority: P1)

**Goal**: Relocate the status-surface trust + snapshot/restore + projection cluster.
**Independent Test**: Trust/projection tests pass; `_restore_final_bookkeeping_snapshots` signature stable for the executor split.
**Prompt**: `/tasks/WP09-bookkeeping-projection-seam.md`
**Requirement Refs**: FR-003, FR-006, INV-6

### Included Subtasks
- [x] T037 Create `src/specify_cli/merge/bookkeeping_projection.py`; move trust + snapshot/restore + projection (WP09)
- [x] T038 Preserve `_restore_final_bookkeeping_snapshots` signature/behavior for INV-6 (WP09)
- [x] T039 Wire `merge.py` import-from + re-export (WP09)
- [x] T040 Add `tests/merge/test_bookkeeping_projection_seam.py` (≥90% of moved code) (WP09)

### Dependencies
- WP08.

### Risks & Mitigations
- Path-trust assertions are security-sensitive → cover trusted + rejected paths.

---

## Work Package WP10: Executor seam + CC-102 decomposition — `merge/executor.py` (Priority: P1) 🎯 HIGH-RISK

**Goal**: Relocate `_run_lane_based_merge` + `_run_lane_based_merge_locked` and internally decompose the CC-102 driver into ~9 phase helpers (each ≤15) via a `_MergeRunState` dataclass; preserve #1827 ordering (INV-5) and the ~6 snapshot-restore-on-exception sites exactly (INV-6).
**Independent Test**: Executor + phase-boundary #1827 regression tests pass; every executor function ≤15 CC; recovery/resume/coord-topology suites green.
**Prompt**: `/tasks/WP10-executor-decomposition.md`
**Requirement Refs**: FR-003, FR-005, FR-006, FR-007

### Included Subtasks
- [x] T041 Define `_MergeRunState` dataclass threading shared mutable state (WP10)
- [x] T042 Create `merge/executor.py`; move `_run_lane_based_merge` + the locked driver (WP10)
- [x] T043 Decompose `_run_lane_based_merge_locked` into ~9 phase helpers, each ≤15 CC (WP10)
- [x] T044 Preserve #1827 baseline record→commit→assert ordering + restore-on-error (INV-5/INV-6) (WP10)
- [x] T045 Re-export `_run_lane_based_merge[_locked]` from the shim (WP10)
- [x] T046 Add `tests/merge/test_executor_phase_boundary.py` (#1827 ordering + restore regression) (WP10)

### Dependencies
- WP09.

### Risks & Mitigations
- THE mission risk → thread state via dataclass not closures; keep lazy imports lazy (C-007); add the phase-boundary regression test before claiming done.

---

## Work Package WP11: Shim thinning + #2057 pointer comment + full gate sweep (Priority: P1)

**Goal**: Decompose the `merge` command (CC71) into `_dispatch_abort`/`_dispatch_resume`/`_dispatch_dry_run`/`_run_real_merge` (≤15 each); install the #2057 pointer comment; finalize re-exports + `__all__` byte-stability; run the full gate sweep. Sole owner of `cli/commands/merge.py`.
**Independent Test**: Golden test byte-identical; `merge.py` ~120 LOC; radon/ruff/mypy clean; all ~41 importers + 3 src consumers green.
**Prompt**: `/tasks/WP11-shim-thinning-gate-sweep.md`
**Requirement Refs**: FR-001, FR-002, FR-005, FR-006, NFR-001, NFR-002, NFR-003

### Included Subtasks
- [x] T047 Decompose the `merge` command into dispatch helpers, each ≤15 CC (WP11)
- [x] T048 Install the top-of-file #2057 decomposition pointer comment (FR-002 convention) (WP11)
- [x] T049 Finalize shim re-exports; assert `__all__` ordering byte-stable (WP11)
- [x] T050 Run the full gate sweep: golden test, radon ≤15, ruff, mypy --strict, coverage ≥90% (WP11)
- [x] T051 Verify the 3 src consumers + ~41 test files import cleanly with zero edits (WP11)

### Dependencies
- WP10.

### Risks & Mitigations
- `__all__` drift → assert exact ordering; golden test is the final byte-identity gate.
