# Lens D — Red-first ATDD repro design (merge/coord rollback transactionality)

Scope: #2786 (durable reconcile marker on failed coord `done` revert) and #2367
(coord-worktree tool-churn blocks merge + non-transactional coord-status rollback).
Read-only pre-spec research. No tests written/committed.

**Profile applied:** `researcher-robbie` — mode `investigation` + `validation`;
directive **003 Decision Documentation Requirement** (findings carry sources +
rationale). Avoidance boundary honoured: no production code, no test authoring,
no final decision — this is a repro *design* for the mission to land red-first.

---

## Ground truth established (sources)

- **#2786 existing red** lives at
  `tests/regression/test_issue_2786_revert_failure_split_brain.py`
  (`test_swallowed_revert_failure_re_opens_2711_split_brain`). It forces the
  coord-worktree `git revert` inside
  `specify_cli.merge.executor._revert_coord_done_commit` to return non-zero via
  `_revert_forced_to_fail()`, drives `_run_lane_based_merge`, and asserts
  `committed_lane == working_lane`. It imports its whole harness from the #2711
  sibling module.
- **The swallowed-failure branch** is `executor.py` `_revert_coord_done_commit`
  (`if revert.returncode != 0:` → `git revert --abort` + `warning` + `return`,
  no raise, **no durable marker**). Confirmed at `executor.py:458-536`.
- **#2367 Mechanism A defect** is in `src/specify_cli/git/ref_advance.py`
  `_dirty_entries` (lines 167-211). The `excluded_filenames` /
  `coord_owned_filenames` exclusion **only applies to untracked/ignored lines**
  (`if line.startswith(("??", "!!"))` → line 202-209). A **tracked-modified**
  `meta.json` (the uncommitted VCS-lock) falls through to the unconditional
  `dirty.append(line)` at line 210 → `RefAdvanceDirtyWorktreeError` → merge
  blocked. `coord_owned_filenames=COORD_OWNED_STATUS_FILES` (= `{status.events.jsonl,
  status.json}`, `status/__init__.py:210`) does **not** cover meta churn and does
  not cover tracked modifications at all.
- **VCS-lock is written but never committed at claim:** `implement.py:1007-1009`
  → `set_vcs_lock(feature_dir, vcs_type="git", locked_at=now_iso)` →
  `mission_metadata.set_vcs_lock` (line 512) `write_meta(...)` — **no commit**.
  The lock fields are exactly `_VCS_LOCK_META_FIELDS = frozenset({"vcs",
  "vcs_locked_at"})` (`implement_cores.py:51`).
- **Canonical predicate the fix should reuse:**
  `implement_cores._is_vcs_lock_only_meta_diff(committed, working)` (line 216) —
  returns True iff every changed meta key ∈ `_VCS_LOCK_META_FIELDS`. This is the
  existing, tested "is this only spec-kitty's own lock churn?" decision (#2222 /
  C-003). The #2367-A fix wires this (or an auto-commit at claim) into the merge
  dirty gate; the repro must go RED **because that wiring does not yet exist**.
- **The merge ref-advance seam that trips:** `merge/ordering.py:467`
  `advance_branch_ref(main_repo, mission_branch, new_sha,
  coord_owned_filenames=COORD_OWNED_STATUS_FILES)` during lane→mission
  consolidation. The coord worktree has the mission branch checked out
  (coord-topology), so its dirty tracked `meta.json` trips this call before any
  target advance.

---

## Issue #2786 — does the existing red suffice? (answer: only for the in-band-revert fix shape)

**Verdict:** the existing `committed_lane == working_lane` assertion suffices
**iff** the chosen fix reverts (or fails loud) *in lockstep during the same
merge invocation*. It is **insufficient** for the durable-reconcile-marker fix
shape that the charter/#2786 body explicitly allows ("record a durable reconcile
marker so the divergence is never silent"). A marker-only fix leaves committed
`done` stranded against working `approved` on purpose and repairs later — so the
existing assertion would **stay RED after a correct marker fix**. Worse, the
existing test's non-vacuity precondition (`assert isinstance(exc, RuntimeError)
and _INJECTED_TARGET_FAILURE in str(exc)`) means a fix that raises a *new*
reconcile error would flip that precondition to failing, not the contract.

**Therefore add an ADDITIONAL test** targeting the marker route. Design below.

### #2786 additional test

1. **Path + markers.** New test in the existing module
   `tests/regression/test_issue_2786_revert_failure_split_brain.py`
   (append; do not edit the harness import block), function
   `test_failed_coord_revert_leaves_durable_reconcile_marker_and_doctor_repairs`.
   Markers inherited from module `pytestmark = [regression, git_repo, non_sandbox]`.
2. **Arrange.** Reuse the *already-imported* helpers (no new harness):
   `_init_git_repo`, `_bootstrap_coord_mission`, `_assert_pre_target_done_path`
   (from #2711 sibling), and the module-local `_run_merge_with_target_and_revert_failing`
   / `_revert_forced_to_fail`. Same forced target-advance failure + forced
   revert-failure as the existing red — the setup is identical; only the assertion
   surface differs.
3. **Act.** `exc, revert_cmds = _run_merge_with_target_and_revert_failing(repo)`
   (the pre-existing `_run_lane_based_merge` entry point). Keep the two non-vacuity
   witnesses (injected-target `RuntimeError`; `revert_cmds` non-empty).
4. **Assert (RED now / GREEN after marker fix):**
   - **(a) Durable marker exists.** A durable reconcile record is present after the
     failed revert — asserted through a canonical read surface, **not** a hand-rolled
     path guess. Candidate surfaces the implementer must choose/create (harness gap):
     a field on `.kittify/merge-state.json` (e.g. `coord_reconcile_required` naming
     the stranded `WP01` + the two divergent lanes `done`/`approved`), or a sidecar
     marker under `kitty-specs/<slug>/`. Assert it exists AND names WP01 + both lanes.
     RED today: `_revert_coord_done_commit` writes nothing.
   - **(b) doctor detects the incoherence.** Invoke `spec-kitty doctor coordination
     --json` (CliRunner, patching `_coordination_doctor.locate_project_root` → repo,
     mirroring `test_merge_coord_topology_1772.test_doctor_flags_tracked_worktrees_content`).
     Assert exit 1 and a finding with a stable `error_code`
     (e.g. `COORD_REVERT_SPLIT_BRAIN`) carrying a `next_step` remediation hint.
     RED today: nothing durable for doctor to read, so no finding.
   - **(c) repair restores coherence.** Drive the repair (`spec-kitty merge --resume`
     through `_run_lane_based_merge`, or `doctor --repair` once it exists), then
     re-read via `_committed_coord_events` / `_working_coord_events` +
     `wp_lane_actor_from_events` and assert `committed_lane == working_lane`
     (both `approved`). RED today: no marker → resume cannot detect or repair the
     divergence (the existing red's whole point).
5. **Red-proof command.**
   `PWHEADLESS=1 uv run pytest tests/regression/test_issue_2786_revert_failure_split_brain.py -n0 -q`
   Both the existing coherence test and the new marker test are RED on the mission base.
6. **Harness gap the implementer must fill.** There is **no** durable-reconcile-marker
   read surface today. The implementer must (i) define the marker's canonical home
   (merge-state field vs sidecar) and a read accessor, and (ii) add a `doctor
   coordination` finding + `error_code`. The test's assertions (a)/(b)/(c) should
   consume those canonical surfaces, never a raw path.

> Recommendation: **keep the existing coherence red** (it pins the fail-loud/in-band
> route) **and add the marker test** (it pins the durable-marker route). Together they
> make either acceptable fix shape green while forbidding the silent-swallow status quo.

---

## Issue #2367 — NEW red-first repro (Mechanism A primary; Mechanism B companion)

### Mechanism A — coord-worktree VCS-lock tool-churn blocks the merge (primary, deterministic)

1. **Path + markers.** New module
   `tests/regression/test_issue_2367_coord_worktree_toolchurn_blocks_merge.py`,
   function `test_merge_not_blocked_by_uncommitted_coord_vcs_lock`.
   `pytestmark = [pytest.mark.regression, pytest.mark.git_repo, pytest.mark.non_sandbox]`.
2. **Arrange — reuse the canonical coord harness (do NOT improvise).** Import the
   #2711 regression-sibling fusion helpers (same precedent by which #2786 imports
   from #2711 — a `tests.regression.*` sibling, keeps `advance_branch_ref` + lane
   consolidation REAL):
   ```python
   from tests.regression.test_issue_2711_merge_rollback_resume_coherence import (
       MID8, MISSION_SLUG, LANE_CODE,
       _init_git_repo, _bootstrap_coord_mission, _merge_external_mocks, _git,
   )
   from specify_cli.coordination.workspace import CoordinationWorkspace
   ```
   `_bootstrap_coord_mission` materializes the coord worktree with the mission
   branch checked out (`CoordinationWorkspace.resolve`) and a real lane diff.
   `_merge_external_mocks` mocks only out-of-git side effects and **leaves
   `advance_branch_ref` + `consolidate_lane_into_mission` real** — the guard under
   test runs. (Structural template for the assertion inversion:
   `test_merge_coord_worktree_resync_1826.test_dirty_coord_worktree_refuses_loudly_and_preserves_data`,
   AC-B4 — which asserts refusal; this test asserts the OPPOSITE for tool-churn.)
   - **Seed the tool-churn (HARNESS GAP — new local helper).** No helper seeds a
     coord-worktree VCS-lock. Add `_seed_uncommitted_vcs_lock(coord_wt)`: read the
     coord worktree's tracked `kitty-specs/<slug>/meta.json`, call the *real*
     `mission_metadata.set_vcs_lock(coord_feature_dir, vcs_type="git",
     locked_at=<iso>)` (realistic data — the exact call `implement.py:1009` makes),
     and **do not commit**. Locate the worktree via
     `CoordinationWorkspace.worktree_path(repo, MISSION_SLUG, MID8)`.
   - Non-vacuity witness: assert `git -C <coord_wt> status --porcelain -- meta.json`
     shows ` M ...meta.json` before the act (the churn is genuinely dirty + tracked).
3. **Act.** Plain (non-injected) merge through the pre-existing entry point:
   ```python
   with _merge_external_mocks():
       _run_lane_based_merge(repo_root=repo, mission_slug=MISSION_SLUG, push=False,
           delete_branch=False, remove_worktree=False,
           strategy=MergeStrategy.SQUASH, allow_sparse_checkout=True)
   ```
   No injected failure — the *only* obstacle is spec-kitty's own meta churn.
4. **Assert (RED now / GREEN after fix).**
   - The merge does **not** raise (neither `RefAdvanceDirtyWorktreeError` nor the
     `typer.Exit` it surfaces as). Wrap in a "did it raise?" capture and assert clean.
   - The lane code reaches the target: `_file_on_branch(repo, "main", LANE_CODE)` True.
   - RED today: the first `advance_branch_ref` (lane→mission consolidation,
     `ordering.py:467`) dirty-checks the coord worktree, sees tracked-modified
     `meta.json`, raises `RefAdvanceDirtyWorktreeError` → merge blocked. GREEN after
     the fix teaches the merge dirty gate to treat a `_is_vcs_lock_only_meta_diff`
     meta change as auto-committable/excludable (or `implement` auto-commits the lock
     at claim).
5. **Red-proof command.**
   `PWHEADLESS=1 uv run pytest tests/regression/test_issue_2367_coord_worktree_toolchurn_blocks_merge.py -n0 -q`
6. **Harness gaps.** (i) `_seed_uncommitted_vcs_lock` (above) — new local helper.
   (ii) Code gap the fix closes: `ref_advance._dirty_entries` never runs a
   lock-only/coord-owned predicate over **tracked-modified** paths (exclusion is
   `??`/`!!`-only). The fix likely threads `_is_vcs_lock_only_meta_diff` (or a
   generalized "coord-owned tracked churn" predicate) into `_dirty_entries`, or
   auto-commits the lock. The test must stay agnostic to which — it asserts the
   *merge outcome*, not the internal mechanism.

### Mechanism B — non-transactional rollback leaves partial coord status writes (companion; overlaps #2786/#2711)

1. **Path + markers.** Second function in the same #2367 module,
   `test_rolled_back_merge_leaves_coord_worktree_resumable`
   (or fold into #2786 — see caveat). Same markers.
2. **Arrange.** Same #2711 harness; use `_run_failing_merge` (injected
   target-advance failure) to trigger the rollback.
3. **Act.** `_run_failing_merge(repo)`; then locate the coord worktree and inspect
   its tracked status files.
4. **Assert (RED if residue stranded).** After rollback, the coord worktree's
   tracked `status.events.jsonl` + `status.json` are **clean** (`git -C <coord_wt>
   status --porcelain -- kitty-specs/<slug>/status.events.jsonl
   kitty-specs/<slug>/status.json` is empty), so a subsequent `--resume` is not
   blocked by a dirty coord tree. RED if the aborted run's emissions sit uncommitted.
5. **Red-proof command.** Same module `-n0 -q` invocation.
6. **CAVEAT / overlap (validation finding).** #2711's
   `_restore_final_bookkeeping_snapshots` **already reverts the working-tree bytes**
   of the coord event log on the *target-advance-failure* path (the #2711 red asserts
   `working_lane == Lane.APPROVED`). So on that exact path Mechanism B may be
   **GREEN-on-base / vacuous**. The live #2367-B was observed on the **squash-conflict
   rollback path** (`consolidate_lane_into_mission` failing), which may capture a
   different snapshot set. **Implementer must confirm which rollback path leaves the
   residue** (inject a consolidation/squash conflict, not a target-advance failure)
   before pinning Mechanism B; if #2711/#2786's snapshot restore already covers it,
   Mechanism B folds into the #2786 durable-marker fix and should not be a separate
   red. Recommendation: **land Mechanism A as the mission's #2367 red; treat
   Mechanism B as a confirmation spike, promoting it to a red only if a
   squash-conflict rollback demonstrably strands coord status writes.**

---

## Charter-constraint checklist

- **Canonical sources:** reuses the real coord harness (#2711 fusion helpers,
  #1772/#1826 lineage) and the real entry point `_run_lane_based_merge`; the fix
  predicate is the canonical `_is_vcs_lock_only_meta_diff`. No improvised paths.
- **Red-first through the pre-existing entry point:** every assertion is driven
  through `_run_lane_based_merge` (+ `spec-kitty doctor coordination` for the
  marker route), never an isolated seam.
- **Realistic data:** the VCS-lock churn is seeded via the real `set_vcs_lock`
  call `implement` makes at claim; the coord mission is the production coord
  topology (mission branch checked out in the coord worktree, real lane diff).
- **Terminology canon:** Mission/coordination/lane throughout; no `feature*`
  aliases introduced.
