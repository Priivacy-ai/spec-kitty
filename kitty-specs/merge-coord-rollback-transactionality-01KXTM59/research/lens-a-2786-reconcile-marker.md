# Lens A — #2786: the swallowed coord-`done` revert during rollback

**Investigator:** Debugger Debbie (profile `debugger-debbie`)
**Applied directives:** D-001 (Architectural Integrity — reuse the single canonical
merge-transaction authority, refuse a sidecar), D-003 (Decision Documentation —
persist the falsified marker-home alternatives), D-030 (Test/Typecheck Gate — the
red-first repro already exists and the fix must flip it), D-032 (Conceptual
Alignment — committed↔working coord divergence is the alignment failure the
divergence matrix surfaces). Tactics: review-intent-and-risk-first, five-paradigm
convergence.
**Mode:** READ-ONLY pre-spec research. No product code edited.

---

## 1. Exact swallowed-failure site

**File:** `src/specify_cli/merge/executor.py`

### 1a. The swallow — `_revert_coord_done_commit`, failure branch (lines 500–514)

```python
    revert = subprocess.run(
        ["git", "-C", str(coord_worktree), "revert", "--no-edit", f"{captured_sha}..HEAD"],
        capture_output=True, text=True, check=False, env=env,
    )
    if revert.returncode != 0:
        subprocess.run(
            ["git", "-C", str(coord_worktree), "revert", "--abort"],
            capture_output=True, text=True, check=False, env=env,
        )
        logger.warning(
            "#2711: could not revert coordination 'done' commit(s) on %s (%s..HEAD); "
            "committed/working coherence may be degraded: %s",
            coord_ref, captured_sha[:12],
            (revert.stderr or revert.stdout or "").strip(),
        )
        # <-- implicit `return None`: no raise, no durable write, nothing recorded
```

On a `git revert` conflict/failure the helper runs `revert --abort`, logs a
`warning`, and falls off the end (implicit `return None`). **Nothing durable is
written.** No `save_state`, no marker field, no event, no sentinel file. The only
trace is a log line that vanishes with the process.

### 1b. The enclosing flow — `_restore_pre_target_if_at_baseline` (lines 517–536)

```python
def _restore_pre_target_if_at_baseline(run: _MergeRunState) -> None:
    if run.done_marked_before_target and _target_branch_still_at_baseline(
        run.main_repo, run.lanes_manifest.target_branch, run.target_baseline_sha,
    ):
        _revert_coord_done_commit(run)                       # (a) revert committed done -> approved
        _restore_final_bookkeeping_snapshots(                # (b) restore working bytes -> approved
            run.pre_target_bookkeeping_snapshots
        )
```

The two rollback legs run **sequentially and unconditionally**: leg (a) reverts the
*committed* coord `done`; leg (b) restores the *working* bytes to `approved`. When
leg (a) silently no-ops on a revert failure, leg (b) still runs — so the committed
ref is stranded at `done` while the working tree reduces to `approved`. This helper
is the shared rollback exit reached from `_reject_zero_diff_noop_squash` (551),
`_handle_mission_merge_result` (579), and `_phase_mission_to_target`'s `except`
(614). The #2786 test drives the (614) path via an injected
`integrate_mission_into_target` `RuntimeError`.

### 1c. Confirmation that nothing durable survives the failure

- `_revert_coord_done_commit` has no `save_state` / marker / event write on any path.
- `clear_state` fires **only** at `_phase_finalize_and_summary` (line 973), never on
  rollback — so `.kittify/runtime/merge/<mission_id>/state.json` **survives** the
  failed merge with `completed_wps` still listing the WP whose committed `done` is
  now stranded. That surviving `MergeState` is the durable object the marker rides
  on: it already outlives the rollback and is already the resume authority.
- Grep confirms `executor.py` writes no state during rollback (only the finalize
  `clear_state`). The divergence is therefore **undetectable** by any later
  resume/doctor pass — exactly the silent re-open the red pins.

---

## 2. The durable reconcile marker — surface + shape (single canonical authority)

**Verdict: put the marker on `MergeState` (`src/specify_cli/merge/state.py`),
persisted to the existing `.kittify/runtime/merge/<mission_id>/state.json`. Do NOT
add a sidecar file, and do NOT invent a new status event.**

Why `MergeState` is the canonical owner (D-001, single-canonical-authority):

1. **It is already the durable authority for merge-transaction progress/resume.**
   The incoherence is a *merge-transaction* fact ("a rollback could not restore
   committed↔working coherence"), not a lane-lifecycle fact. Its natural home is the
   merge-transaction record, not the event log.
2. **It already survives the rollback** (`clear_state` runs only at finalize) and is
   already re-loaded by both `merge --resume` (`_dispatch_resume` →
   `_load_merge_state_for_mission`) and available to `doctor`. Zero new lifecycle.
3. **It already carries the reconcile seam.** `done_bookkeeping._reconcile_completed_wps_for_resume`
   already reconciles `completed_wps` against durable `done` evidence — the marker's
   repair is the *inverse* of logic that already lives one function away.
4. The event log is the authority for *lane state*; `MergeState` is the authority for
   *merge transactions*. Recording "reconcile needed" on `MergeState` while *reading*
   the event log to heal keeps each authority single — no second authority is minted.

### Marker shape (new optional field on `MergeState`)

```python
@dataclass
class MergeState:
    ...
    # #2786: set by the rollback when the coherent coord-``done`` revert FAILS,
    # stranding the committed ``done`` against the rolled-back working ``approved``.
    # None on a healthy transaction; populated => a repair is owed before the
    # transaction can be considered coherent. Read by merge --resume and
    # `doctor coordination`. Cleared when the revert is re-attempted successfully
    # (or the whole state file is cleared at merge finalize).
    pending_coord_reconcile: dict[str, Any] | None = None
```

Payload written by the rollback:

```json
{
  "coord_ref":       "kitty/mission-<slug>-<mid8>-coord",   // run.pre_target_coord_ref
  "captured_sha":    "<pre-emit coord tip>",                 // run.pre_target_coord_sha
  "coord_worktree":  "<abs path to coord worktree>",         // _coord_worktree_root(run)
  "stranded_wp_ids": ["WP01", ...],                          // run.all_wp_ids marked done pre-target
  "revert_error":    "<git revert stderr/stdout, trimmed>",
  "detected_at":     "2026-07-18T…Z"
}
```

`from_dict` already filters unknown keys, so the field is backward/forward
compatible with pre-#2786 state files (loads as `None`) — no migration.

- **Writer (rollback):** `_revert_coord_done_commit`'s failure branch sets
  `run.state.pending_coord_reconcile = {…}` and calls
  `save_state(run.state, run.main_repo)` **before** returning. This is the entire
  behavioral change on the write side: turn the silent `return` into a durable
  record, then keep returning (see §4 on why it still returns rather than raises).
- **Readers/repairers:** `merge --resume` and `doctor coordination` (see §3).

---

## 3. Repair semantics — who reads and heals

"Repair" = make the **committed** coord ref agree again with the **working**
reduction. Two symmetric heals, both grounded in code that already exists:

### 3a. Roll-back heal (re-attempt the coherent revert)

The revert failed because the coord worktree was transiently non-revertable (dirty
index, conflict, broken worktree). Once the operator clears that, re-running the
**same** `git revert <captured_sha>..HEAD` in the coord worktree rolls the committed
`done` back to `approved` — coherent with the already-rolled-back working tree.
This is a straight re-invocation of `_revert_coord_done_commit` seeded from the
marker's `coord_ref`/`captured_sha`/`coord_worktree`. On success, clear
`pending_coord_reconcile` and `save_state`.

### 3b. Roll-forward heal (resume the merge)

If the operator instead `merge --resume`s, the merge re-advances the target; the
committed `done` becomes *correct* once the mission actually lands, and finalize's
`clear_state` drops the whole state file (marker included). So a successful resume
is self-healing — the marker only needs to *survive an abandoned* transaction.

### Surfacing + healing wiring

- **`merge --resume`:** extend the existing reconcile seam. Before
  `_record_merged_wps_done_for_merge`, if `state.pending_coord_reconcile` is set,
  attempt 3a (re-revert); if it still fails, keep the marker and fail loud with a
  remediation hint (`doctor coordination --fix` / `merge --abort`). This sits
  naturally beside `_reconcile_completed_wps_for_resume`, which already drops stale
  `completed_wps` — the two together make resume idempotent in both divergence
  directions.
- **`doctor coordination`** (`src/specify_cli/cli/commands/_coordination_doctor.py`):
  add a check `_check_coord_done_reconcile_pending(repo_root, mission_meta)` alongside
  the existing `_coord_worktree_head/dirty/stale_finding` probes. It loads the
  mission's `MergeState` and, when `pending_coord_reconcile` is set, emits:

  ```python
  DoctorFinding(
      severity="error",                       # a stranded committed done is a real defect, not advisory
      message="Coordination 'done' revert failed during a rolled-back merge; the "
              "committed coord ref is stranded at 'done' while the working tree is "
              "'approved' (mission <slug>, WPs <ids>).",
      next_step="Run `spec-kitty doctor coordination --fix` to re-attempt the "
                "coherent revert, or `spec-kitty merge --resume` to roll forward.",
      error_code="COORDINATION_DONE_REVERT_STRANDED",
      extra={"mission_slug": ..., "captured_sha": ..., "coord_worktree": ...,
             "stranded_wp_ids": [...]},
  )
  ```

  `doctor coordination --fix` already has a `--fix` loop (`_fix_never_created_branches`);
  add a sibling `_fix_stranded_coord_done(findings)` that re-runs the coherent revert
  from the marker and clears it on success — the exact `--fix` pattern this module
  already uses.

  *Defense-in-depth option:* the doctor check can additionally **recompute** the
  divergence directly (reduce committed coord-ref events vs working-file events, the
  `wp_lane_actor_from_events` comparison the #2786 test already uses) so the finding
  fires even for a state file that was cleared out-of-band. The marker stays the
  primary, cheap signal; the recomputation is the belt-and-suspenders authority.

---

## 4. Raise-vs-mark verdict

**Recommendation: MARK durably; do NOT raise from `_revert_coord_done_commit`.**

The reviewer is correct that raising "wouldn't mask a success" — the enclosing merge
is already failing. But raising from the helper is still the wrong lever, for two
code-grounded reasons the reviewer's framing doesn't cover:

1. **Raising skips the second rollback leg.** In
   `_restore_pre_target_if_at_baseline`, `_revert_coord_done_commit` and
   `_restore_final_bookkeeping_snapshots` run **sequentially** (lines 535–536). An
   exception out of the revert helper would bypass the working-byte restore, leaving
   the working tree mid-rollback — trading the *committed-done/working-approved*
   split-brain for a *committed-done/working-done-but-target-not-advanced* one. That
   is a **different** incoherence, not a cure.
2. **Raising obscures the real rollback trigger.** The rollback exists *because* the
   target advance failed (the injected `RuntimeError`). A revert-conflict exception
   would surface at the CLI *instead of* that root fault, sending the operator to
   debug the revert rather than the merge failure that caused it.

Meanwhile the actual requirement the red encodes is **detectability + repairability**,
not additional loudness: the enclosing merge already exits non-zero and prints the
target-advance error, so the CLI failure is *not* silent — only the residual
divergence is. The durable marker (§2) closes exactly that gap and lets the byte
restore complete, keeping the rollback single-purpose.

**Concrete minimal fix:** in the failure branch, replace the bare `return` with
`set pending_coord_reconcile + save_state` (keep the existing `warning`), then
return. Add the resume + doctor readers of §3. This flips
`test_swallowed_revert_failure_re_opens_2711_split_brain` green **by repair**, not by
suppression.

**Falsified / deferred alternatives (D-003):**
- *Sidecar reconcile file* (`.kittify/…/coord-incoherence.json`) — rejected: mints a
  second authority beside `MergeState`, violates single-canonical-authority (D-001).
- *New status event on the coord log* — rejected: writing another coord event during
  a failed coord revert is the surface that is already broken; the event log is the
  *lane* authority, not the *merge-transaction* authority.
- *Skip the byte-restore on revert failure so both legs stay `done`* (coherent-but-
  not-rolled-back, and arguably resume-friendlier) — **not** the minimal fix: it
  reorders INV-6 and leaves a `done` that is wrong if the transaction is abandoned
  (still needs the marker for that case). Flagged for architect consideration, out of
  scope for the #2786 close.

---

## Terminology note
Uses canonical **Mission** throughout; no `feature*` aliases introduced.
