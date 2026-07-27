# Research — Decompose `merge.py` God-Module (issue #2057)

**Mission:** `decompose-merge-god-module-01KVXHDK` · **Branch:** `prog/2057-merge`
**Target module:** `src/specify_cli/cli/commands/merge.py` — **3383 LOC**, **maxCC 102**
**Goal:** Decompose into cohesive, independently-testable seams + a thin
command-registration shim, preserving the public `spec-kitty merge` CLI surface
**byte-for-byte**. This is a **behavior-preserving refactor** — no functional change.

**Prior art (read first):** `src/specify_cli/merge/` is the established sibling
package and the `baseline_merge_commit` cluster was *already* extracted there as
part of decomposition epic #2026 (`merge/baseline.py` header documents this).
The one-way-import discipline (`merge/` never imports `cli.commands.merge`) is
already in force — this mission continues that pattern, it does not invent it.

---

## 1. Public CLI surface — the frozen contract

`merge` is a **single top-level Typer command** (not a sub-app). It is registered
once at `cli/commands/__init__.py:216`:

```python
app.command()(merge_module.merge)
```

The command function: `merge.py:2970` (`@require_main_repo` decorator at `:2969`).
**There is no `merge_app`/`add_typer` — the whole surface is the options of one
function.** A golden CLI characterization test must pin exactly these options:

| Flag(s) | Type / default | merge.py:LINE | Notes |
|---|---|---|---|
| `--strategy` | `MergeStrategy\|None`, default `None`→SQUASH | `:2971` | merge\|squash\|rebase |
| `--delete-branch/--keep-branch` | bool, default `True` | `:2976` | |
| `--remove-worktree/--keep-worktree` | bool, default `True` | `:2977` | |
| `--push` | bool, default `False` | `:2978` | |
| `--target` | str, default `None` | `:2979` | auto-detected |
| `--dry-run` | bool, default `False` | `:2980` | |
| `--json` | bool, default `False` | `:2981` | dry-run-only (enforced `:3167`) |
| `--mission` | str, default `None` | `:2982` | mission slug |
| `--feature` | str, default `None`, **hidden** | `:2983` | legacy alias for `--mission` |
| `--resume` | bool, default `False` | `:2984` | |
| `--abort` | bool, default `False` | `:2985` | |
| `--context` | str, default `None` | `:2986` | **unused** compat flag (`del`'d `:3000`) |
| `--keep-workspace` | bool, default `False` | `:2987` | **unused** compat flag (`del`'d `:3000`) |
| `--allow-sparse-checkout` | bool, default `False` | `:2988` | logged override |
| `--yes / -y` | bool, default `False` | `:2997` | proceed past warnings |

Docstring (one-line help): *"Merge a lane-based feature into its target branch."* (`:2999`).

**Behavioral contract points the golden test must also pin (not just flag parse):**
- `--json` without `--dry-run` → prints `{"spec_kitty_version", "error": "--json is currently supported with --dry-run only."}` and exits 1 (`:3167-3176`).
- `--dry-run` JSON payload shape: keys `spec_kitty_version, mission_slug, target_branch, strategy, delete_branch, remove_worktree, push, mission_branch, lanes, would_assign_mission_number` (`:3285-3296`).
- `--abort` cleanup sequence (state clear, global lock file unlink, legacy `merge-state.json` unlink, git-merge abort, coordination teardown) (`:3012-3111`).
- `--resume` "No interrupted merge to resume." exit 1 (`:3124-3126`).
- Unresolved mission slug → "Mission slug could not be resolved. Use --mission <slug>." exit 1 (`:3179-3185`, `:3307-3309`).
- Review-artifact consistency gate in dry-run emits `REJECTED_REVIEW_ARTIFACT_CONFLICT` in both human + JSON (`:3201-3271`).

### External public-symbol contract (importers outside merge.py — must stay importable)

`merge.py` exports `__all__` (`:3358-3383`). Non-test, in-tree consumers:

| Symbol | Consumer | merge.py origin |
|---|---|---|
| `merge` (the command) | `agent/mission.py:42`, `agent/README.md` (`top_level_merge`) | `:2970` |
| `path_is_under_worktrees` | `doctor.py:3103`, `agent/mission.py:158` | `:178` |
| `_mark_wp_merged_done` | `orchestrator_api/commands.py:482` | `:348` |

Tests additionally import (must remain importable post-refactor): `_run_lane_based_merge`,
`_run_lane_based_merge_locked`, `_assert_merged_wps_reached_done`,
`_assert_merged_wps_done_on_target`, `_bake_mission_number_into_mission_branch`,
`_check_mission_branch`, `_effective_push_requested`, `_enforce_canonical_status_history`,
`_enforce_review_artifact_consistency`, `_has_transition_to`,
`_reconcile_completed_wps_for_resume`, `_resolve_mission_slug`, `_resolve_target_branch`.

**Implication:** the shim must re-export relocated symbols (`from .merge_xxx import *`
or explicit re-imports) so the 41 test files and 3 src consumers keep working
without edits — OR the mission updates those import sites. Re-export is the
lower-risk, behavior-preserving choice and keeps `__all__` stable.

---

## 2. Function inventory (top-level defs in merge.py)

64 top-level functions + the `merge` command. Complexity from `radon cc`.
**maxCC drivers (CC > 15 → MUST be internally decomposed, not just relocated):**

| CC | LOC | Lines | Function | Purpose |
|---:|---:|---|---|---|
| **102** | 706 | 2264-2969 | `_run_lane_based_merge_locked` | **THE god-function.** Whole locked merge flow: gates→lane merges→baseline SHA→mission_number bake→done bookkeeping→mission→target merge→snapshots/restore→porcelain invariant→safe_commit→assert done+baseline→dossier→stale-check→push→worktree/branch cleanup→coord teardown→state clear→summary. |
| **71** | 414 | 2970-3383 | `merge` (command) | Arg parse + `--abort`/`--resume`/`--dry-run` branches + dispatch to `_run_lane_based_merge`. |
| **22** | 185 | 348-532 | `_mark_wp_merged_done` | Emit canonical done (and intermediate approved) status transition per WP, with dedup + PLANNED-fallback force logic. |
| **21** | 53 | 2057-2109 | `_collect_hollow_review_warnings` | Scan WPs for hollow/self-approved reviews; build warning buckets. |
| **16** | 67 | 591-657 | `_assert_merged_wps_done_on_target` | Post-merge: assert every WP reached `done` on target branch. |

Sub-ceiling functions (CC ≤ 15 — relocate as-is, no internal split needed), grouped by concern:

**Git / branch primitives:** `_lane_already_integrated` (2,135), `_branch_trees_equal` (1,161), `path_is_under_worktrees` (1,178), `_raw_porcelain_status` (1,198), `_classify_porcelain_lines` (9,227), `_is_linear_history_rejection` (2,277), `_emit_remediation_hint` (1,316), `_has_branch_ref` (1,407), `_is_git_repo` (2,1090), `_refresh_primary_checkout_after_merge` (7,728), `_paths_have_status_changes` (6,765).

**Status / done bookkeeping:** `_has_transition_to` (1,325), `_assert_merged_wps_reached_done` (7,533), `_reconcile_completed_wps_for_resume` (5,658), `_record_merged_wps_done_for_merge` (4,692), `_enforce_canonical_status_history` (4,1962), `_resolve_merge_actor` (10,287).

**Bookkeeping-projection / snapshot-restore (status-surface trust):** `_validate_mission_slug_path_segment` (1,790), `_target_bookkeeping_status_paths` (2,799), `_read_optional_bytes` (2,824), `_restore_optional_bytes` (2,925), `_assert_status_path_within_target_surface` (1,830), `_assert_status_surface_path_is_trusted` (8,848), `_assert_status_surface_file_path_is_trusted` (3,902), `_assert_bookkeeping_snapshot_path_is_trusted` (1,933), `_capture_bookkeeping_snapshots` (2,956), `_restore_final_bookkeeping_snapshots` (3,971), `_target_branch_still_at_baseline` (4,987), `_project_status_bookkeeping_to_target` (5,1004).

**Mission-number bake (write-side, #1827 blast zone):** `_already_baked` (2,1067), `_mark_mission_number_baked` (2,1077), `_is_assigned_mission_number` (1,1102), `_compute_next_mission_number_or_none` (5,1107), `_write_mission_number_to_branch` (9,1166 — 154 LOC, git-worktree heavy), `_bake_mission_number_into_mission_branch` (6,1320), `_assign_planning_only_mission_number_if_needed` (3,1940).

**Mission-branch / slug / state resolution:** `_check_mission_branch` (4,1418), `_enforce_planning_artifact_target_branch` (4,1468), `_enforce_git_preflight` (5,1489), `_extract_mission_slug` (3,1510), `_resolve_mission_slug` (5,1525), `_merge_state_key_candidates` (5,1563), `_iter_merge_states_for_slug` (6,1588), `_load_merge_state_for_mission` (2,1606), `_load_merge_state_entry_for_mission` (6,1618), `_load_or_create_merge_state` (6,1637), `_clear_merge_state_for_mission` (7,1673), `_cleanup_merge_workspaces_for_state` (7,1691).

**Target-branch resolve/validate/sync-preflight:** `_resolve_target_branch` (1,1713), `_validate_target_branch` (8,1777), `_target_branch_sync_payload` (1,1817), `_target_branch_refresh_failed_payload` (2,1845), `_enforce_target_branch_sync_preflight` (9,1868), `_effective_push_requested` (2,1928).

**Gates / orchestration glue:** `_emit_merge_diff_summary` (9,1730), `_enforce_review_artifact_consistency` (7,2008), `_warn_or_confirm_hollow_reviews` (6,2110), `_run_lane_based_merge` (10,2136 — lock acquire/release wrapper).

---

## 3. Proposed seams (validate/refine the 6 candidates)

The issue's 6 candidates — *preflight / executor / forecast / status-resolver /
baseline-write / command-registration* — map cleanly, with two refinements:
**(a)** several map onto modules that ALREADY exist under `merge/` (so the work is
*relocate the merge.py glue into them*, not create new ones); **(b)** the
706-LOC executor needs a dedicated **bookkeeping/projection** seam split out of it,
otherwise the executor stays >15 CC.

### Seam set (resolved)

| Seam | Module (new/existing) | Member functions from merge.py | est. LOC moved | maxCC after |
|---|---|---|---:|---:|
| **command-registration (the shim)** | `cli/commands/merge.py` (stays) | `merge` command **only** — but decomposed into `_dispatch_abort`, `_dispatch_resume`, `_dispatch_dry_run`, `_run` helpers so the command body falls ≤15. Re-exports relocated symbols for `__all__`. | ~120 (down from 414) | ≤15 |
| **forecast** (dry-run) | NEW `merge/forecast.py` | dry-run preview block (extract from `merge` body): lanes-manifest preview, review-artifact gate preview, `would_assign_mission_number` scan, JSON/human payload build. | ~120 | ≤12 |
| **slug/state resolution** | EXISTING `merge/state.py` (+helpers) or NEW `merge/resolve.py` | `_extract_mission_slug`, `_resolve_mission_slug`, `_merge_state_key_candidates`, `_iter_merge_states_for_slug`, `_load_merge_state_for_mission`, `_load_merge_state_entry_for_mission`, `_load_or_create_merge_state`, `_clear_merge_state_for_mission`, `_cleanup_merge_workspaces_for_state`, `_resolve_target_branch`. | ~230 | ≤8 |
| **preflight** | EXISTING `merge/preflight.py` / `merge/push_preflight.py` | `_enforce_git_preflight`, `_enforce_planning_artifact_target_branch`, `_check_mission_branch`, `_has_branch_ref`, `_validate_target_branch`, `_target_branch_sync_payload`, `_target_branch_refresh_failed_payload`, `_enforce_target_branch_sync_preflight`, `_effective_push_requested`, `_enforce_canonical_status_history`, `_enforce_review_artifact_consistency`, `_collect_hollow_review_warnings`★, `_warn_or_confirm_hollow_reviews`. | ~360 | ≤12 (after ★ split) |
| **status-resolver / done-bookkeeping** | NEW `merge/done_bookkeeping.py` | `_mark_wp_merged_done`★, `_has_transition_to`, `_assert_merged_wps_reached_done`, `_assert_merged_wps_done_on_target`★, `_reconcile_completed_wps_for_resume`, `_record_merged_wps_done_for_merge`, `_resolve_merge_actor`. | ~430 | ≤12 (after ★ split) |
| **bookkeeping-projection / snapshot** | NEW `merge/bookkeeping_projection.py` | the status-surface trust + snapshot/restore + projection cluster: `_validate_mission_slug_path_segment`, `_target_bookkeeping_status_paths`, `_read_optional_bytes`, `_restore_optional_bytes`, `_assert_status_path_within_target_surface`, `_assert_status_surface_path_is_trusted`, `_assert_status_surface_file_path_is_trusted`, `_assert_bookkeeping_snapshot_path_is_trusted`, `_capture_bookkeeping_snapshots`, `_restore_final_bookkeeping_snapshots`, `_target_branch_still_at_baseline`, `_project_status_bookkeeping_to_target`. | ~310 | ≤8 |
| **baseline-write / mission-number** | EXISTING `merge/baseline.py` + EXISTING `merge/ordering.py` | record/assert baseline is ALREADY in `merge/baseline.py`. Relocate the mission_number bake cluster (`_already_baked`, `_mark_mission_number_baked`, `_is_assigned_mission_number`, `_is_git_repo`, `_compute_next_mission_number_or_none`, `_write_mission_number_to_branch`, `_bake_mission_number_into_mission_branch`, `_assign_planning_only_mission_number_if_needed`) into `merge/ordering.py` (it already holds `assign_next_mission_number`). | ~360 | ≤9 |
| **git primitives** | NEW `merge/git_probes.py` (or fold into executor) | `_lane_already_integrated`, `_branch_trees_equal`, `path_is_under_worktrees`†, `_raw_porcelain_status`, `_classify_porcelain_lines`, `_is_linear_history_rejection`, `_emit_remediation_hint`, `_refresh_primary_checkout_after_merge`, `_paths_have_status_changes`. | ~210 | ≤9 |
| **executor** | NEW `merge/executor.py` | `_run_lane_based_merge` (lock wrapper) + `_run_lane_based_merge_locked`★★ decomposed into ~7 phase helpers (see §6). Consumes all seams above. | ~300 (down from 834) | ≤15 (after ★★ split) |

★ = function itself exceeds CC 15 and needs **internal** decomposition during the move.
★★ = the 706-LOC/CC-102 driver — the bulk of the internal-decomposition work.
† `path_is_under_worktrees` is a public consumer symbol (doctor.py, mission.py) — keep importable via shim re-export wherever it lands.

**Shared constants/state to relocate or centralize:** `_STATUS_EVENTS_FILENAME`,
`_STATUS_FILENAME`, `_SAFE_PATH_SEGMENT_DIAGNOSTIC`, `TARGET_BRANCH_NOT_SYNCHRONIZED`,
`TARGET_BRANCH_SYNC_INVARIANT`, `LINEAR_HISTORY_REJECTION_TOKENS` (locked tuple — do
not reorder), `MissionBranchBlocker`, `HollowReviewWarnings` type aliases, module
`logger`. These should live in a `merge/_constants.py` (or each in its owning seam)
to avoid a duplicated-literal Sonar S1192 hit when multiple seams need them.

---

## 4. Coupling & import map

### What merge.py imports (top-of-file + lazy/in-function)

External-to-merge packages it depends on (top-level): `core.constants`,
`coordination.surface_resolver` (`is_under_worktrees_segment`, `resolve_status_surface`),
`missions._read_path_resolver` (`candidate_feature_dir_for_mission`,
`primary_feature_dir_for_mission`), `cli.helpers` (`console`, `show_banner`),
`core.context_validation` (`require_main_repo`), `core.git_ops`, `core.git_preflight`,
`core.commit_guard` (`GuardCapability`), `core.paths`, `core.utils`, `git` (`safe_commit`),
`git.commit_helpers`, `git.ref_advance` (`advance_branch_ref`), `git.sparse_checkout`,
`lanes.persistence`, `merge.{baseline,config,ordering,preflight,state,workspace}`,
`mission_metadata`, `post_merge.{review_artifact_consistency,retrospective_terminus,stale_assertions}`,
`sync`, `sync.dossier_pipeline`, `status`, `task_utils`, `mission_runtime`.

Lazy (in-function) imports — these stay lazy in their new seam: `lanes.branch_naming`,
`lanes.compute`, `lanes.merge`, `policy.config`, `policy.merge_gates`,
`coordination.CoordinationWorkspace`, `coordination.status_transition`, `status.*` enums.

### One-way-import feasibility — **CONFIRMED FEASIBLE**

- No `merge/` package module imports `cli.commands.merge` today (verified: only
  doc-comment references in `merge/baseline.py`, no `import`). The precedent
  extraction (#2026, baseline.py) already proved the seam pattern is cycle-free.
- The shim (`cli/commands/merge.py`) imports FROM seams; seams never import the shim.
- **Circular-import risk:** LOW but watch two edges:
  1. `merge/done_bookkeeping.py` will import `coordination.status_transition` and
     `status.*`. `orchestrator_api/commands.py:482` currently imports
     `_mark_wp_merged_done` from the shim — if it's relocated, either keep a shim
     re-export (recommended) or repoint that import. Either is one-way-safe.
  2. `merge/forecast.py` + `merge/preflight.py` both need
     `post_merge.review_artifact_consistency` — fine, that's a leaf dependency.
- `path_is_under_worktrees` is imported by `doctor.py` and `agent/mission.py`. Keep
  it re-exported from the shim regardless of which seam owns it, to avoid touching
  those modules.

---

## 5. Test-coverage baseline

**41 test files** reference `cli.commands.merge`; core unit/integration files:
`tests/specify_cli/cli/commands/test_merge.py` (41 tests),
`tests/merge/test_merge_recovery.py` (24), `tests/cli/commands/test_merge_strategy.py` (20),
`tests/merge/test_mission_number_idempotency.py`, `tests/merge/test_merge_done_recording.py`,
`tests/merge/test_merge_post_merge_invariant.py`, `tests/merge/test_target_branch_preflight.py`,
`tests/merge/test_push_preflight.py`, `tests/merge/test_hollow_review_warnings.py`,
`tests/merge/test_merge_bootstrap_history_gate.py`, `tests/merge/test_merge_preflight_mission_branch.py`,
`tests/merge/test_mid8_embedded_preflight.py`, `tests/integration/test_merge_resume.py`,
`tests/integration/test_post_merge_index_refresh.py`,
`tests/integration/sparse_checkout/test_merge_*` (3),
`tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py`,
`tests/specify_cli/cli/commands/test_merge_coord_worktree_resync_1826.py`,
`tests/specify_cli/cli/commands/test_merge_residue_gate_single_authority_wp13.py`,
`tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py`,
`tests/specify_cli/merge/test_1827_baseline_regression.py`★,
`tests/specify_cli/merge/test_baseline_module.py`.

### Coverage character — the critical finding

Existing tests are **unit-level against internal functions** (importing
`_run_lane_based_merge`, `_mark_wp_merged_done`, `_assert_*`, `_bake_*`, etc.) plus
**integration tests that call `_run_lane_based_merge` directly** (e.g.
`test_merge_resume.py:228`). The **CLI surface itself is barely exercised**:
`test_merge.py:413-419` builds a minimal Typer app wrapping `merge` and invokes via
`CliRunner` for **`--abort` only** (`test_abort_clears_lock_and_state`, `test_abort_idempotent`).

| Proposed seam | Existing coverage | Verdict |
|---|---|---|
| executor (`_run_lane_based_merge[_locked]`) | strong (recovery, resume, coord-topology, post-merge invariant, data-loss) | trustworthy for the *flow*, but pinned to internal-fn signatures that the refactor will move |
| preflight | strong (`test_target_branch_preflight`, `test_push_preflight`, `test_merge_preflight_mission_branch`, `test_mid8_embedded_preflight`, `test_merge_bootstrap_history_gate`, `test_hollow_review_warnings`) | good |
| done-bookkeeping | good (`test_merge_done_recording`, `test_merge.py` mark/assert tests) | good |
| baseline-write / mission-number | good (`test_1827_baseline_regression`★, `test_baseline_module`, `test_mission_number_idempotency`, `test_merge_time_number_assignment`) | good — #1827 already has a regression test |
| bookkeeping-projection | partial (`test_merge.py` target-bookkeeping-path + FR003 trust tests; `test_merge_residue_gate`) | adequate |
| forecast (dry-run) | partial (`test_merge_dry_run_review_artifact`, `test_merge_strategy` dry-run JSON) | adequate |
| **command-registration / full CLI surface** | **GAP — only `--abort` invoked via CliRunner** | **insufficient** |

### Verdict: capture golden CLI characterization tests BEFORE refactoring

The internal-function suite is strong enough to catch *logic* regressions in the
seams, but it does **not** pin the byte-for-byte CLI contract (flag names, help text,
hidden `--feature` alias, the `--json`-without-`--dry-run` error string, the exact
dry-run JSON key set, exit codes). Because the mission's success criterion is
"public surface preserved byte-for-byte," **Phase 0 of the plan must add a golden
CLI characterization test** (Typer `CliRunner` against the full registered app)
that snapshots: `merge --help` output, all flag/default parsing, the dry-run JSON
payload schema, and the headline error/exit-code paths. Capture it on the
*pre-refactor* module so the diff is the proof. The existing suite should NOT be
trusted alone as the byte-identity guarantor.

---

## 6. Risks / open questions for the plan

1. **The CC-102 `_run_lane_based_merge_locked` is the whole mission's risk.** It is
   one linear procedure with ~9 ordered phases and pervasive shared mutable state
   (`pre_target_bookkeeping_snapshots`, `final_bookkeeping_snapshots`,
   `done_marked_before_target`, `mission_number_meta_path`, `mission_already_applied`,
   `target_baseline_sha`, `_baseline_mission_id`). Decomposing it behavior-preservingly
   requires threading that state through a small context object/dataclass rather than
   closure-capturing it. Proposed phase helpers (each ≤15 CC):
   `_phase_gates_and_state` (2284-2346), `_phase_merge_lanes` (2348-2401),
   `_phase_bake_and_pre_target_done` (2403-2470), `_phase_mission_to_target` (2472-2553),
   `_phase_capture_and_baseline` (2555-2597), `_phase_record_done_and_project` (2610-2634),
   `_phase_porcelain_invariant` (2636-2707), `_phase_commit_and_assert` (2709-2773),
   `_phase_cleanup_and_summary` (2775-2966). The snapshot/restore-on-exception pattern
   (try/except that calls `_restore_final_bookkeeping_snapshots` then re-raises) appears
   ~6 times and must be preserved exactly at each phase boundary.

2. **#1827 baseline-write blast zone.** The record/verify functions already live in
   `merge/baseline.py` (`record_baseline_merge_commit`, `assert_baseline_merge_commit_on_target`,
   `BaselineMergeCommitError`) with a dedicated regression test
   (`test_1827_baseline_regression.py`). What *remains* in the maxCC-102 zone is the
   **call ordering**: baseline is recorded at `:2586` (after target merge, before done
   bookkeeping commit) and asserted at `:2762` (after the bookkeeping commit lands).
   The #1827 circular-failure lived in that ordering + the snapshot-restore-on-failure
   interplay. **Open question for plan:** does the executor decomposition preserve the
   exact record→commit→assert ordering and the restore-on-`BaselineMergeCommitError`
   behavior (`:2591-2597`)? This must be an explicit plan invariant + a phase-boundary test.

3. **Hardest-to-decompose functions:** `_run_lane_based_merge_locked` (CC102) >>
   `_mark_wp_merged_done` (CC22 — PLANNED-fallback/force-done branching with dedup
   guards is genuinely intricate) > `_collect_hollow_review_warnings` (CC21) >
   `_assert_merged_wps_done_on_target` (CC16). `_write_mission_number_to_branch`
   (154 LOC, CC9) is long but linear (git-worktree create→edit→commit→ff→cleanup) and
   relocates cleanly.

4. **Symbol re-export contract.** 3 src modules + 41 test files import internals from
   the shim. Decision needed: re-export everything from the shim (zero churn, keeps
   `__all__` byte-stable — recommended) vs repoint imports (larger diff, touches
   orchestrator_api + doctor + agent + tests). Recommend re-export to honor "preserve
   surface" and keep the diff reviewable.

5. **Shared-package boundary / Sonar.** New seams must pass `ruff` + `mypy` clean and
   keep every function ≤15 CC (the mission's whole point). Extract phase helpers WITH
   focused tests in the same WP (Sonar new-code-coverage gate). Watch S1192 on the
   shared constant literals — centralize them (§3).

6. **Lazy-import preservation.** Several imports are deliberately in-function (avoiding
   import cost / cycles): `lanes.merge`, `policy.merge_gates`, `coordination.*`. Keep
   them lazy in the seams; do not hoist to module top during the move (could
   reintroduce a cycle or change import-time side effects).
