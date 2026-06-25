# Data Model — Target Module Topology for `merge.py` Decomposition (#2057)

This is a **behavior-preserving refactor**: the "data model" is the target *module
topology* (shim + seams), the symbol/import contract, and the invariants the plan
must hold. No runtime data shapes change.

## Target topology

```
src/specify_cli/cli/commands/merge.py          # SHIM — command registration only (~120 LOC, maxCC ≤15)
    │  registers via cli/commands/__init__.py:216  app.command()(merge_module.merge)
    │  decomposes `merge` into _dispatch_abort / _dispatch_resume / _dispatch_dry_run / _run_real_merge
    │  re-exports relocated symbols so __all__ + external importers stay byte-stable
    ▼ imports (one-way) from:

src/specify_cli/merge/                          # SEAM PACKAGE (existing — extend, don't reinvent)
    ├── _constants.py            NEW   shared literals/type-aliases/logger (S1192-safe)
    ├── executor.py              NEW   _run_lane_based_merge + _run_lane_based_merge_locked
    │                                  (CC102 → ~9 phase helpers, each ≤15) + a phase-state dataclass
    ├── git_probes.py            NEW   branch/tree/porcelain primitives
    ├── forecast.py              NEW   dry-run preview + JSON/human payload
    ├── done_bookkeeping.py      NEW   _mark_wp_merged_done(★split) + done/approved transitions + asserts
    ├── bookkeeping_projection.py NEW  status-surface trust + snapshot/restore + projection
    ├── resolve.py               NEW (or fold into state.py)  slug/state/target resolution
    ├── baseline.py              EXISTING  record/assert baseline_merge_commit  (#1827 home — unchanged)
    ├── ordering.py              EXISTING  + relocate mission_number bake cluster
    ├── preflight.py             EXISTING  + relocate git/target/mission-branch/review/hollow preflights
    ├── push_preflight.py        EXISTING  target-branch-sync preflight support
    ├── state.py                 EXISTING  MergeState, lock, load/save/clear
    ├── workspace.py             EXISTING  worktree/runtime-dir cleanup
    ├── config.py                EXISTING  MergeStrategy, load_merge_config
    ├── conflict_classifier.py   EXISTING  (untouched)
    └── conflict_resolver.py     EXISTING  (untouched)
```

## Symbol contract (entities that must remain importable)

| Symbol | Pre-refactor location | Post-refactor home | Re-exported by shim? |
|---|---|---|---|
| `merge` (Typer command) | `cli/commands/merge.py:2970` | shim (stays) | n/a (is the shim) |
| `path_is_under_worktrees` | `:178` | `merge/git_probes.py` | YES (doctor.py, agent/mission.py) |
| `_mark_wp_merged_done` | `:348` | `merge/done_bookkeeping.py` | YES (orchestrator_api/commands.py) |
| `_run_lane_based_merge` / `_locked` | `:2136` / `:2264` | `merge/executor.py` | YES (tests, integration) |
| `_assert_merged_wps_reached_done` / `_done_on_target` | `:533` / `:591` | `merge/done_bookkeeping.py` | YES (tests) |
| `_bake_mission_number_into_mission_branch` | `:1320` | `merge/ordering.py` | YES (tests) |
| `_check_mission_branch`, `_resolve_mission_slug`, `_resolve_target_branch`, `_effective_push_requested`, `_enforce_canonical_status_history`, `_enforce_review_artifact_consistency`, `_has_transition_to`, `_reconcile_completed_wps_for_resume` | various | preflight / resolve / done_bookkeeping | YES (tests) |
| `LINEAR_HISTORY_REJECTION_TOKENS`, `BaselineMergeCommitError`, etc. in `__all__` | top of file | `_constants.py` / `baseline.py` | YES |

## Invariants (binding constraints for plan + WPs)

- **INV-1 — CLI byte-identity.** `spec-kitty merge --help`, every flag/short/default,
  the hidden `--feature` alias, exit codes, the `--json`-without-`--dry-run` error
  string, and the dry-run JSON key set are byte-for-byte unchanged. Proven by a
  golden CLI characterization test captured on the pre-refactor module.
- **INV-2 — One-way imports.** No `merge/*` seam imports `cli.commands.merge`. The
  shim imports from seams; seams import only leaf/sibling packages. (Already true;
  must stay true — enforce with an architectural test mirroring
  `tests/architectural/test_*_boundary.py`.)
- **INV-3 — maxCC ≤ 15.** Every function in every resulting module is ≤15 cyclomatic
  (radon/ruff C901 / Sonar S3776 aligned). The 5 current offenders (CC 102/71/22/21/16)
  are internally decomposed, not merely relocated.
- **INV-4 — `__all__` stability + re-export.** External importers (3 src, 41 test
  files) keep working without edits via shim re-exports; `__all__` ordering preserved.
- **INV-5 — #1827 ordering preserved.** baseline record (post-target-merge,
  pre-bookkeeping-commit) → bookkeeping safe_commit → baseline assert (post-commit),
  including the restore-on-`BaselineMergeCommitError` rollback, is preserved exactly.
- **INV-6 — Snapshot/restore-on-exception fidelity.** The ~6 try/except sites that call
  `_restore_final_bookkeeping_snapshots(...)` then re-raise keep identical
  exception-class scoping and ordering across phase-helper boundaries.
- **INV-7 — Lazy imports stay lazy.** In-function imports (`lanes.merge`,
  `policy.merge_gates`, `coordination.*`, `status` enums) are not hoisted to module top.
- **INV-8 — Locked constants untouched.** `LINEAR_HISTORY_REJECTION_TOKENS` tuple order
  and membership unchanged (spec-locked).

## Phase-state object (proposed) for executor decomposition

To thread shared mutable state through the split `_run_lane_based_merge_locked`
phase helpers without closures (supports INV-3 + INV-6):

```
@dataclass
class _MergeRunState:
    main_repo: Path
    mission_slug: str
    canonical_id: str
    feature_dir: Path
    target_feature_dir: Path
    lanes_manifest: object
    all_wp_ids: list[str]
    state: MergeState
    is_resume: bool
    planning_artifact_only: bool
    target_baseline_sha: str
    baseline_mission_id: str | None
    done_marked_before_target: bool
    mission_already_applied: bool
    mission_number_meta_path: Path | None
    pre_target_bookkeeping_snapshots: dict[Path, bytes | None]
    final_bookkeeping_snapshots: dict[Path, bytes | None]
    # paths
    canonical_events_path / canonical_status_path / merge_state_path: Path
```
Each phase helper takes `_MergeRunState`, mutates the documented fields, returns None;
the orchestrator `_run_lane_based_merge_locked` becomes the linear phase caller.
