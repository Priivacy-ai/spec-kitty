# Implementation Plan: Decompose the `merge.py` God-Module

**Branch**: `prog/2057-merge` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/decompose-merge-god-module-01KVXHDK/spec.md`

## Summary

Decompose `src/specify_cli/cli/commands/merge.py` (3383 LOC, maxCC ~102) into the
research-resolved 9-seam set under the existing `src/specify_cli/merge/` package plus
a thin command-registration shim, preserving the `spec-kitty merge` CLI surface
byte-for-byte. Verification is golden-test-first: WP01 captures a CLI characterization
test on the pre-refactor module; subsequent WPs each relocate one seam (behavior-
preserving move + focused per-seam tests) in a strictly-linear dependency chain; a
dedicated WP internally decomposes the CC-102 `_run_lane_based_merge_locked` via a
`_MergeRunState` dataclass threaded through ~9 phase helpers; the final WP installs
the #2057 pointer comment, thins the shim to command registration + re-exports, and
runs the full gate sweep. Approach and seam boundaries are drawn directly from
[research.md](research.md) and [data-model.md](data-model.md).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), pytest + pytest-xdist (tests), mypy (`--strict`), ruff (lint + C901 complexity), radon (cyclomatic-complexity measurement). No new third-party dependency is introduced.
**Storage**: N/A (no runtime data shapes change; status surfaces are existing JSONL/JSON files, untouched in behavior)
**Testing**: pytest unit + integration. Golden CLI characterization test via Typer `CliRunner` against the fully registered app (captured pre-refactor as the byte-identity baseline). Per-seam focused unit tests with ≥90% coverage of moved code. Existing ~41 importing test files must pass unchanged.
**Target Platform**: Linux/macOS developer + CI environment (the `spec-kitty` CLI)
**Project Type**: single (Python CLI package under `src/specify_cli/`)
**Performance Goals**: N/A — behavior-preserving refactor; no performance change intended or measured.
**Constraints**: maxCC ≤ 15 every function (NFR-001); ≥90% new-code coverage (NFR-002); `ruff` + `mypy --strict` clean with zero new suppressions (NFR-003, C-004); CLI surface byte-identical (FR-001, C-001); one-way imports preserved (C-006); lazy imports stay lazy (C-007); locked constants untouched (C-008); #1827 ordering preserved (FR-007).
**Scale/Scope**: One 3383-LOC source module + ~41 importing test files + 3 src consumers; target ~120-LOC shim plus ~8 seam modules (mix of new + extended existing under `merge/`).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **No new functional surface** — behavior-preserving refactor; no command/flag/API
  change (C-001, C-003). No charter directive on feature scope is engaged.
- **Terminology Canon** — module/symbol names retain canonical "Mission" vocabulary;
  no `feature*` aliases introduced.
- **No-direct-push** — all work lands on lane branches → `prog/2057-merge` via the
  standard workflow; no direct origin/main push.
- **Sonar / complexity ceiling** — the mission's explicit goal aligns with the
  charter's complexity ceiling (≤15) and S1192/S3776 expectations; new branches/
  helpers carry focused tests in the same WP.

**Result: PASS — no charter violations.** Complexity Tracking table left empty (no
violations to justify).

## Project Structure

### Documentation (this mission)

```
kitty-specs/decompose-merge-god-module-01KVXHDK/
├── plan.md              # This file
├── research.md          # Resolved 9-seam set, mega-function findings, test verdict
├── data-model.md        # Target module topology, symbol contract, invariants
├── quickstart.md        # Verification recipe (golden test, radon, ruff, mypy)
├── contracts/
│   └── cli-surface-contract.md   # Frozen merge CLI contract = golden-test target
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/
│   └── merge.py                    # SHIM after refactor (~120 LOC, maxCC ≤15):
│                                   #   merge command (decomposed into _dispatch_abort/
│                                   #   _dispatch_resume/_dispatch_dry_run/_run_real_merge)
│                                   #   + re-exports of relocated symbols (keeps __all__)
│                                   #   + #2057 pointer comment (FR-002)
└── merge/                          # SEAM PACKAGE (existing — extend, don't reinvent)
    ├── _constants.py               # NEW  shared literals/type-aliases/logger (S1192-safe)
    ├── executor.py                 # NEW  _run_lane_based_merge + _run_lane_based_merge_locked
    │                               #       (CC102 → ~9 phase helpers) + _MergeRunState dataclass
    ├── git_probes.py               # NEW  branch/tree/porcelain primitives + path_is_under_worktrees
    ├── forecast.py                 # NEW  dry-run preview + JSON/human payload
    ├── done_bookkeeping.py         # NEW  _mark_wp_merged_done(split) + done/approved transitions + asserts
    ├── bookkeeping_projection.py   # NEW  status-surface trust + snapshot/restore + projection
    ├── resolve.py                  # NEW  slug/state/target resolution
    ├── baseline.py                 # EXISTING  record/assert baseline (#1827 home — unchanged)
    ├── ordering.py                 # EXISTING  + mission-number bake cluster relocated in
    ├── preflight.py                # EXISTING  + git/target/mission-branch/review/hollow preflights
    ├── push_preflight.py           # EXISTING  target-branch-sync support
    ├── state.py                    # EXISTING  MergeState, lock, load/save/clear
    └── workspace.py                # EXISTING  worktree/runtime-dir cleanup

tests/
├── specify_cli/cli/commands/
│   └── test_merge_cli_golden.py    # NEW (WP01) golden CLI characterization harness
└── merge/                          # NEW per-seam focused test files (one per seam WP)
```

**Structure Decision**: Single Python package. The shim stays at
`src/specify_cli/cli/commands/merge.py` (its registration site at
`cli/commands/__init__.py:216` is unchanged). All seams live under the existing
`src/specify_cli/merge/` package — extending existing modules (`baseline.py`,
`ordering.py`, `preflight.py`, `push_preflight.py`, `state.py`, `workspace.py`) where
they already own the concern (C-002), and adding new modules (`executor.py`,
`git_probes.py`, `forecast.py`, `done_bookkeeping.py`, `bookkeeping_projection.py`,
`resolve.py`, `_constants.py`) only for genuinely new seams. One-way imports
(shim → seams; seams → leaf/sibling packages only) are preserved (C-006, INV-2).

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into a
> strictly-linear WP chain. The IC ordering below mirrors the intended linear
> sequence so lanes nest and merge cleanly.

### IC-01 — Golden CLI characterization harness

- **Purpose**: Capture the `spec-kitty merge` contract (help text, every flag/default,
  hidden `--feature` alias, `--json`-without-`--dry-run` error, dry-run JSON schema,
  headline exit codes) as the byte-identity baseline BEFORE any seam moves.
- **Relevant requirements**: FR-001, C-005, NFR (verification gate)
- **Affected surfaces**: NEW `tests/specify_cli/cli/commands/test_merge_cli_golden.py` (+ fixtures)
- **Sequencing/depends-on**: none (must be first)
- **Risks**: Must run against the fully registered app, not a re-wrapped command, to
  pin real registration. Capture on the pre-refactor module so the diff is the proof.

### IC-02 — Shared constants seam (`merge/_constants.py`)

- **Purpose**: Centralize shared literals / type aliases / logger so multiple seams can
  import them without S1192 duplication; foundation for every later move.
- **Relevant requirements**: FR-003, C-008 (locked-constant fidelity), NFR-003
- **Affected surfaces**: NEW `merge/_constants.py`; small wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: `LINEAR_HISTORY_REJECTION_TOKENS` tuple order/membership must be byte-stable.

### IC-03 — Git primitives seam (`merge/git_probes.py`)

- **Purpose**: Relocate branch/tree/porcelain git primitives incl. the public
  `path_is_under_worktrees` symbol.
- **Relevant requirements**: FR-003, FR-006 (public re-export), C-006
- **Affected surfaces**: NEW `merge/git_probes.py`; shim re-export; wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-02
- **Risks**: `path_is_under_worktrees` consumed by doctor.py + agent/mission.py — must stay importable.

### IC-04 — Slug/state/target resolution seam (`merge/resolve.py`)

- **Purpose**: Relocate slug extraction, merge-state load/clear/cleanup, and target-branch resolution.
- **Relevant requirements**: FR-003, FR-006, C-002
- **Affected surfaces**: NEW `merge/resolve.py` (consumes existing `merge/state.py`); wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-03
- **Risks**: Several resolvers are test-imported (`_resolve_mission_slug`, `_resolve_target_branch`) — re-export.

### IC-05 — Preflight seam (extend `merge/preflight.py`)

- **Purpose**: Relocate git/target/mission-branch/review-artifact/hollow-review preflights;
  split `_collect_hollow_review_warnings` (CC21) to ≤15.
- **Relevant requirements**: FR-003, FR-005, FR-006, C-002
- **Affected surfaces**: EXISTING `merge/preflight.py` (+ `push_preflight.py`); wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-04
- **Risks**: `_check_mission_branch`, `_resolve_*`, `_effective_push_requested`,
  `_enforce_canonical_status_history`, `_enforce_review_artifact_consistency` are
  test-imported — re-export. Both forecast + preflight need `post_merge.review_artifact_consistency` (leaf dep, fine).

### IC-06 — Forecast seam (`merge/forecast.py`)

- **Purpose**: Extract the dry-run preview + JSON/human payload build out of the `merge` body.
- **Relevant requirements**: FR-001 (dry-run JSON schema), FR-003, FR-004
- **Affected surfaces**: NEW `merge/forecast.py`; wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-05
- **Risks**: Dry-run JSON key set is part of the frozen contract (golden test pins it).

### IC-07 — Mission-number bake seam (extend `merge/ordering.py`)

- **Purpose**: Relocate the mission-number bake cluster into `merge/ordering.py` (which
  already holds `assign_next_mission_number`).
- **Relevant requirements**: FR-003, FR-006, C-002
- **Affected surfaces**: EXISTING `merge/ordering.py`; wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-06
- **Risks**: `_bake_mission_number_into_mission_branch` is test-imported — re-export.
  `_write_mission_number_to_branch` (154 LOC, CC9) is long but linear — relocates cleanly.

### IC-08 — Done-bookkeeping seam (`merge/done_bookkeeping.py`)

- **Purpose**: Relocate done/approved transition emission + done asserts + resume
  reconcile; split `_mark_wp_merged_done` (CC22) and `_assert_merged_wps_done_on_target`
  (CC16) to ≤15.
- **Relevant requirements**: FR-003, FR-005, FR-006
- **Affected surfaces**: NEW `merge/done_bookkeeping.py`; shim re-export; wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-07
- **Risks**: `_mark_wp_merged_done` consumed by orchestrator_api/commands.py — re-export.
  PLANNED-fallback/force-done branching with dedup is intricate; preserve exactly.

### IC-09 — Bookkeeping-projection / snapshot seam (`merge/bookkeeping_projection.py`)

- **Purpose**: Relocate the status-surface trust + snapshot/restore + projection cluster.
- **Relevant requirements**: FR-003, FR-006, INV-6 (snapshot/restore fidelity)
- **Affected surfaces**: NEW `merge/bookkeeping_projection.py`; wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-08
- **Risks**: `_restore_final_bookkeeping_snapshots` participates in the ~6 restore-on-
  exception sites — its signature/behavior must survive the executor split (IC-10).

### IC-10 — Executor seam + CC-102 decomposition (`merge/executor.py`)

- **Purpose**: Relocate `_run_lane_based_merge` (lock wrapper) + `_run_lane_based_merge_locked`
  and internally decompose the CC-102 driver into ~9 phase helpers (each ≤15) via a
  `_MergeRunState` dataclass; preserve #1827 ordering (INV-5) and the ~6 snapshot-
  restore-on-exception sites exactly (INV-6).
- **Relevant requirements**: FR-003, FR-005, FR-006, FR-007
- **Affected surfaces**: NEW `merge/executor.py` (consumes IC-02..IC-09 seams); shim re-export; wiring edit to `merge.py`
- **Sequencing/depends-on**: IC-09 (the executor consumes every prior seam)
- **Risks**: THE mission risk. ~9 ordered phases with pervasive shared mutable state.
  Baseline record (post-target-merge/pre-bookkeeping-commit) → safe_commit → assert
  (post-commit) ordering and restore-on-`BaselineMergeCommitError` must be preserved
  exactly; add a phase-boundary regression test (FR-007). Lazy imports stay lazy (C-007).

### IC-11 — Shim thinning, pointer comment, full gate sweep

- **Purpose**: Decompose the `merge` command (CC71) into `_dispatch_abort` /
  `_dispatch_resume` / `_dispatch_dry_run` / `_run_real_merge` (≤15 each); install the
  #2057 pointer comment (FR-002, matching #2056/#1623 convention); finalize re-exports
  and `__all__` byte-stability; run the full radon/ruff/mypy/golden/suite gate sweep.
- **Relevant requirements**: FR-001, FR-002, FR-005, FR-006, NFR-001/002/003
- **Affected surfaces**: `src/specify_cli/cli/commands/merge.py` (sole owner here)
- **Sequencing/depends-on**: IC-10 (everything relocated first)
- **Risks**: `__all__` ordering must stay byte-stable for FR-006; golden test must pass
  byte-for-byte; verify the 3 src consumers + ~41 test files import cleanly with zero edits.
