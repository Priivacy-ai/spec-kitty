# Mission Specification: Merge coord-write rollback transactionality (P0 #2786 + #2367-B)

**Mission Branch**: `kitty/mission-merge-coord-rollback-transactionality-01KXTM59`
**Created**: 2026-07-18
**Status**: Draft (pre-spec 6-lens research folded)
**Input**: Complete the #2711 Option-A arc — make the merge's coord-write rollback
transactional and failure-detectable. Remediate **#2786** (a failed coord-`done` revert
during rollback is swallowed, silently re-opening the #2711 split-brain — its red-first repro
is already on `main`) and **#2367 Mechanism B** (the merge's multi-WP coord write-set is not
one atomic unit, so an aborted run strands partial/uncommitted coord state).

<!--
  Grounded by a pre-spec research squad (findings in ./research/lens-{a,b,c,d,e,f}-*.md):
  A debugger — #2786 reconcile-marker design; B architect — #2367 coord-worktree resync;
  C paula — shared transactional seam + scope; D researcher — red-first repro design;
  E architect — canonical-seam alignment; F planner — related-surface / work-graph discovery.
-->

## ⚠️ Scope decision requiring operator sign-off

**#2367 is a P0 you (HiC) own, and this mission addresses only its Mechanism B.** Per lenses C
and F, #2367 is a "one-invariant-three-seams" issue:

- **Mechanism B** (non-transactional rollback of coord `status.*` writes) is the **same seam**
  as #2786 → **IN SCOPE** (fold-in).
- **Mechanism A** (an uncommitted VCS-lock in tracked `meta.json` at claim blocks `spec-kitty
  merge` because the `advance_branch_ref` dirty gate excludes only *untracked* status files) is
  a **different, claim-time seam** and a **deliberate #2222 / C-003 race stop-gap** — lens C:
  "committing it would reverse that call." → **DEFERRED** to a tracked follow-up (candidate
  parent #2017). Its clean deterministic repro (lens D) is captured for that follow-up.

Confirm this partial-#2367 scope before implementation, or redirect.

## Problem & Root Cause *(context)*

This is the recurring class **"merge leaves coordination state partial/incoherent on
failure"** — #1826 (closed) → #1878 → #2711 Option-A → **#2786**. Each prior fix patched a
site; the class is not closed by construction.

**The coord-write transaction already exists** (lens E): it is `merge/executor.py`'s
`_MergeRunState`-threaded phase pipeline + the #2711 committed-`done` revert
(`_revert_coord_done_commit`) + the INV-5/INV-6 ratchets. `coordination/transaction.py::BookkeepingTransaction`
is the atomic authority at the **single-transition** grain; the merge's **multi-phase**
atomicity is a *different grain the executor already owns*. The defects are gaps *inside* that
executor transaction, not a missing outer one.

- **#2786 — the rollback is not failure-detectable.** `merge/executor.py::_revert_coord_done_commit`
  (the `if revert.returncode != 0:` branch, ~lines 500–514) runs `git revert --abort`, logs
  `warning("…coherence may be degraded")`, and falls off the end — **no raise, no durable
  record**. Its caller `_restore_pre_target_if_at_baseline` (~517–536) then runs
  `_restore_final_bookkeeping_snapshots` **unconditionally**, restoring the working tree to
  `approved` while the committed `done` is stranded. `clear_state` fires only at finalize, so
  `MergeState` survives the rollback with no signal. The committed-`done`-vs-reverted-`approved`
  split-brain re-opens silently and breaks resume dedup. Red-first repro already on `main`:
  `tests/regression/test_issue_2786_revert_failure_split_brain.py`.
- **#2367-B — the coord write-set is not atomic; the SAME mechanism as #2786.** (Post-spec
  correction, lens renata+pedro.) `merge/done_bookkeeping.py` marks each WP done via its **own**
  `BookkeepingTransaction` (N independent committed transactions). The genuine non-atomic strand
  is a **failure mid `_record_merged_wps_done_for_merge`**: its failure branch (`executor.py:406-408`)
  restores **working bytes only — it does NOT call `_revert_coord_done_commit`**, so per-WP
  committed `done` commits already on the coord ref remain while working bytes revert to
  `approved` → tracked-dirty coord worktree + committed/working split-brain. This is the
  **identical byte-restore-without-revert mechanism** as #2786 (#2786 = the revert itself
  *failed*; #2367-B = the revert was *never called* because failure preceded it). The #1826
  safe-resync guard (`git/ref_advance.py::advance_branch_ref`, the *victim* not the defect) then
  correctly refuses to `reset --hard` over the strand, blocking the next merge/resume. **Note
  (lens pedro/renata):** the *target-advance* and *squash-conflict* rollback paths already run
  `_restore_final_bookkeeping_snapshots` + `_revert_coord_done_commit` (executor.py:535-536), so
  a repro on those paths is **vacuously green** — the repro MUST inject failure inside
  `_record_merged_wps_done_for_merge`. So one unified fix — *any rollback that strands committed
  coord state either reverts or marks-and-repairs* — closes both #2786 and #2367-B.

## The fix posture (seam-aligned — lens E verdict)

Extend the executor's existing coord-write transaction; do **not** add an outer wrapper, a
sidecar marker, a hand-rolled resolver, or a backward `update-ref`:

- **Durable marker → a `MergeState` field** (`merge/state.py`, persisted `state.json`) — the
  authority that already survives rollback and is read by `--resume`/`doctor`. New
  `pending_coord_reconcile` field; `from_dict` already drops unknown keys → **no migration, no
  sidecar** (single canonical authority).
- **Repair reads that marker** — `--resume` extends `_reconcile_completed_wps_for_resume`;
  `spec-kitty doctor coordination` gains a stranded-revert check + `--fix`.
- **Surface/ref seams route through canon** — coord ref via `resolve_placement_only(..., kind=MissionArtifactKind.STATUS_STATE).ref`;
  ref move / revert via `git/ref_advance.py` and a **forward** `git revert` (AC-B3: never raw
  `update-ref`; AC-F1: env via `_make_merge_env`).
- **INV-5 #1827 safety** — all new logic is an **inner** extension (fields/helpers called inside
  existing phases and `_restore_*` sites, per the #2711 precedent) — **never** a wrapper around
  the phase driver (that would trip `test_executor_phase_boundary.py` / `test_1827_baseline_regression.py`).

## User Scenarios & Testing *(mandatory)*

> **RED-integrity note (binding):** every reproduction is RED-for-the-right-reason — the first
> failing assertion is the contract, not setup (SC-001).

### User Story 1 — Red-first reproductions land first (Priority: P1)

As a maintainer, I want committed failing reproductions that witness both defects before any
fix, so they are witnessed against live code and can never silently regress.

**Acceptance Scenarios**:

1. **(#2786 — the existing on-main repro MUST be modified, not left permanently red — BLOCKER
   fix.)** `tests/regression/test_issue_2786_revert_failure_split_brain.py::test_swallowed_revert_failure_re_opens_2711_split_brain`
   asserts `committed_lane == working_lane` with **no resume step (line ~204)** — under
   mark-not-raise (FR-005) the committed `done` is *deliberately* stranded until repair, so that
   assertion **can never go green** and the mission would ship a permanent red (violates
   SC-001/SC-004). The WP MUST (delete-the-assertion-not-the-test) **replace** that synchronous
   coherence assertion with the post-repair contract, OR add the `--resume`/heal step before it.
2. **(#2786 companion — non-fakeable marker + doctor + repair.)** **Given** a merge whose
   coord-`done` revert fails during rollback, **Then**: (a) a durable marker exists whose
   `stranded_wp_ids` equals the **specific** WP(s) whose *committed* reduction is `done` while
   *working* reduces to `approved` — derived from the committed-vs-working event delta
   (`wp_lane_actor_from_events` over the coord ref, as the existing test does), NOT a static/over-broad
   list; (b) `spec-kitty doctor coordination --json` exits 1 with a stable `error_code`, and the
   check **re-verifies committed-vs-working incoherence** (not merely marker-presence); (c) after
   `--resume`/`--fix`, `committed_lane`/`working_lane` **re-reduced from the actual coord ref**
   (not read from the marker) are equal — so a resume that clears-without-healing FAILS. RED today.
3. **(#2367-B — the REAL path is bake-mid-write-set failure, not target-advance/squash-conflict.)**
   **Given** a coord multi-WP merge that fails **inside `_record_merged_wps_done_for_merge`**
   (after some per-WP `done` commits land, before `_revert_coord_done_commit` runs), **When** it
   rolls back via the `executor.py:406-408` byte-restore-only branch, **Then** the coord worktree's
   tracked `status.*` are clean AND committed==working — asserted RED today (the strand exists
   there). The repro MUST inject failure on THIS path; the target-advance and squash-conflict
   paths are revert-covered (vacuously green) — do not reproduce there. Since this is the same
   mechanism as #2786, if the fix's marker/repair already covers it, the WP folds #2367-B into
   the unified fix with a documented note rather than inventing a second mechanism.

### User Story 2 — A failed rollback revert is detectable and repairable (Priority: P1)

As an operator whose merge fails and whose coord-`done` revert then also fails, I want the
incoherence recorded durably and healed by `doctor`/`--resume`, not silently degraded.

**Acceptance Scenarios**:

1. **Given** `_revert_coord_done_commit` fails, **When** rollback completes, **Then** a
   `MergeState.pending_coord_reconcile` marker is persisted (coord_ref, captured_sha,
   coord_worktree, stranded_wp_ids, revert_error, detected_at) — and the rollback **marks, does
   not raise** (raising would skip leg-b byte-restore and mask the real target-advance fault).
2. **Given** a persisted marker, **When** `spec-kitty merge --resume` runs, **Then** it re-heals
   coherence and clears the marker — but the re-heal is **coherence-gated**: it acts only while
   committed-vs-working is *still incoherent* (re-derived from git), and the marker clear is
   atomic with the heal. (A blind second `git revert captured_sha..HEAD` after a successful heal
   would revert the revert and re-apply `done` — so re-attempt MUST gate on live incoherence, not
   on `head != captured_sha`.)
3. **Given** a healed merge, **When** `--resume` (or `doctor --fix`) runs a **second** time,
   **Then** the coord event log is byte-identical to after the first heal and the marker stays
   cleared (NFR-002 — no destructive double-heal, incl. a crash between heal and clear).
4. **Given** a persisted marker AND a strand still `DONE` on the committed coord ref, **When**
   `spec-kitty doctor coordination` runs, **Then** it loads the `MergeState` markers, **re-verifies**
   the strand from the committed ref, reports it with a stable `error_code` (exit 1), and `--fix`
   repairs it — registered in the canonical `cli/commands/_coordination_doctor.py` surface.
5. **(negative — separates re-verification from marker-presence)** **Given** a marker present but the
   committed coord ref re-derives **coherent** (e.g. a prior heal cleared the strand but crashed before
   clearing the marker), **When** `doctor coordination` runs, **Then** it exits 0 with no finding — a
   doctor that reports on marker-presence alone FAILS this.

### User Story 3 — The merge coord write-set rolls back atomically (Priority: P1)

As an operator, I want an aborted merge to leave zero uncommitted/partial coord `status.*` in
the coordination worktree, so the safe-resync guard does not block the next merge/resume.

**Acceptance Scenarios**:

1. **Given** a merge that aborts mid multi-WP write-set, **When** it rolls back, **Then** the
   coordination worktree is clean of merge-owned partial state (the resync guard finds nothing
   tracked-dirty to refuse).
2. **Given** the fix, **When** a normal (non-aborting) merge runs, **Then** behavior is
   byte-identical to today (no regression; INV-5 ratchets green).

### Edge Cases

- A genuinely-`done` WP before the abort must survive rollback+resume without re-emission.
- Non-coord topologies (`single_branch`/`lanes`) have no coord worktree — the marker/repair path
  is a proven no-op.
- Marker repair must be idempotent under repeated `--resume` and under the post-merge finalize.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | Priority | Status |
|----|-------|----------|--------|
| FR-001 | **Modify** the existing on-main `test_issue_2786_*` synchronous `committed==working` assertion (permanently red under mark-not-raise) → replace with the post-repair contract (assert coherence *after* the heal step), never bare-delete the assertion. Pinned by SC-006 (red-on-base + post-heal coherence). | High | Open |
| FR-002 | Red-first #2786 companion repro on a **≥2-WP fixture** (one WP stranded done/approved, one coherent): assert `stranded_wp_ids == [the_stranded_one]` (the coherent WP **excluded** — falsifies both a hardcoded `["WP01"]` and an over-broad `all_wp_ids`); marker derived from the **committed coord ref** (`_durable_done_wps_on_coordination_ref` over this merge's write-set), NOT a live worktree diff (empty at the #2786 mark point — see data-model D7). The doctor-exit-1 sub-assertion lands with FR-007's surface (WP03), not WP01 (priti sequencing). | High | Open |
| FR-003 | Red-first #2367-B repro injecting failure inside `_record_merged_wps_done_for_merge` **after ≥1 committed `done`** (the bake byte-restore-without-revert branch, executor ≈406-408) — NOT target-advance/squash-conflict (vacuous) | High | Open |
| FR-004 | Durable reconcile marker as a `MergeState.pending_coord_reconcile` field, typed `dict[str, Any] \| None`, persisted via `save_state` to the **canonical per-mission runtime state** (`.kittify/runtime/merge/<mission_id>/state.json`, NOT legacy `.kittify/merge-state.json`); rehydrates as plain dict via `from_dict`; no sidecar, no migration | High | Open |
| FR-005 | Rollback MARKS on any strand (revert failure #2786 ≈500-514 AND bake failure #2367-B ≈406-408) via one `_persist_coord_reconcile_marker`, persists via `save_state`, does NOT raise; leg-b byte-restore still runs. Candidate set = **this merge's pre-target done write-set** (a NEW `_MergeRunState` field), NOT `run.all_wp_ids` (which re-strands a pre-existing-done WP on resume). | High | Open |
| FR-006 | Repair via a dedicated `_heal_pending_coord_reconcile` entry at resume startup (NOT overloading `_reconcile_completed_wps_for_resume`); **strand-gated** re-heal (act only while a WP still reduces DONE-on-committed-ref), atomic clear, idempotent; repair = forward `git revert` (NOT `advance_branch_ref` — refuses the non-FF move; AC-B3 clean) | High | Open |
| FR-007 | `doctor coordination` registers into the **canonical** `cli/commands/_coordination_doctor.py` surface (`_collect_coordination_findings` + `--fix` dispatch, NOT `src/specify_cli/doctor/`); enumerates ALL markers via a NEW `iter_pending_coord_reconcile_markers(repo_root)` in `state.py` (NOT `load_state(mission_id=None)` — it *raises* on ≥2 markers); RE-VERIFIES strand from the committed ref (positive: marker+strand → exit 1 stable `error_code`; **negative: marker present but ref re-derives coherent → exit 0 / no finding** — the AC that separates re-verification from marker-presence); `--fix` repairs | High | Open |
| FR-008 | Class-closing guard — **behavioral, not a source grep**: runtime-stub the mark to a no-op, drive a real bake-path strand, require the checker to red on `strand-on-ref ∧ marker-absent`. MUST enumerate the `_restore_final_bookkeeping_snapshots` sites **programmatically** (SEVEN today: ≈407/536/670/691/701/757/786 — never a hardcoded count), assert ≈691 is dead-for-coord via `done_marked_before_target` (≈350-352), AND assert ≈701 is coord-reachable-and-routed-through-the-marking-primitive. | Medium | Open |
| FR-009 | Single coherence owner: `coordination`-layer `coord_incoherent_done_wps(coord_ref, candidate_wps)` (over `_durable_done_wps_on_coordination_ref`) consumed by mark + heal-gate + doctor — no re-implementation in `merge/executor.py` private helpers; the repair primitive homed in `coordination/`, consumed by executor-resume AND `doctor --fix` (no dependency inversion). | High | Open |
| FR-010 | SaaS/dashboard outbound-emit reconciliation is **explicitly OUT of scope** (fenced): `git revert` heals tracked coord artifacts but cannot un-send the transient `done` emit; documented in Complexity Tracking + doctor remediation notes, not silently omitted. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No happy-path regression | A non-aborting merge is byte-identical to pre-fix; INV-5 #1827 + AC-B3/AC-F1 ratchets stay green. | Reliability | High | Open |
| NFR-002 | Repair idempotency | `--resume`/`doctor --fix` run N times → byte-stable coord log, marker cleared exactly once. | Reliability | High | Open |
| NFR-003 | Scoped test surface | `tests/regression/test_issue_2786_*`, `tests/regression/test_issue_2367_*`, `tests/merge/`, `tests/merge/test_executor_phase_boundary.py`, `tests/specify_cli/merge/test_1827_baseline_regression.py`, the doctor tests. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Priority | Status |
|----|-------|------------|----------|--------|
| C-001 | Single canonical authority | Extend the executor's existing coord-write transaction + `MergeState`; do NOT add an outer wrapper, a sidecar marker, a hand-rolled coord-ref resolver, or wrap `BookkeepingTransaction` (wrong grain — lens E). | High | Open |
| C-002 | INV-5 inner-only | New logic lives inside existing phases / `_restore_*` sites (the #2711 precedent); never a wrapper around the phase driver. | High | Open |
| C-003 | AC-B3 / AC-F1 | Repair is a forward coord-worktree `git revert` (env via `_make_merge_env`); **NOT** `advance_branch_ref` (it refuses the non-FF move back to `captured_sha` by design); never raw `update-ref`. | High | Open |
| C-004 | Scope fence | #2367-A (vcs-lock resync), the parallel-engine retirement (fold executor rollback into `BookkeepingTransaction`), and non-merge coord paths are DEFERRED / OUT. | High | Open |
| C-005 | Rebase-first + housekeeping | Rebase onto the post-#2785 baseline; the fix edits code merged today (`_revert_coord_done_commit`, executor.py). Clean up the stale `…01KXRRB7` coord/lane worktrees before implementing. | High | Open |
| C-006 | Terminology canon | `Mission` not `feature`; `--mission`. | Medium | Open |

### Key Entities

- **`MergeState.pending_coord_reconcile`** — the durable reconcile marker (canonical authority for "a rollback left coord incoherent"): coord_ref, captured_sha, coord_worktree, `stranded_wp_ids` (derived via `_durable_done_wps_on_coordination_ref` over this merge's write-set — committed-ref authority, not a worktree diff), revert_error, detected_at. Persisted at `.kittify/runtime/merge/<mission_id>/state.json`.
- **`coord_incoherent_done_wps(coord_ref, candidate_wps)`** — the single `coordination`-layer coherence owner + `git revert` repair primitive, consumed by mark + heal-gate + doctor (FR-009).
- **Executor coord-write transaction** — `_MergeRunState` + phase pipeline + `_restore_pre_target_if_at_baseline`/`_revert_coord_done_commit`/`_restore_final_bookkeeping_snapshots` (the seam to extend; six restore sites enumerated in FR-008).
- **Doctor coordination check** — the stranded-revert detector + `--fix` repair, in canonical `cli/commands/_coordination_doctor.py`.

## Success Criteria *(mandatory)*

- **SC-001**: Both new repros are RED on the mission base with the first failing assertion being the contract (not setup), GREEN on the final commit.
- **SC-002**: After a failed rollback revert, a durable marker exists; `doctor coordination` exits 1 with a stable `error_code`; `--resume`/`--fix` restores `committed == working` — repair, not suppression.
- **SC-003**: An aborted merge (bake-mid-write-set failure, #2367-B) leaves zero tracked-dirty coord `status.*` after repair — or, if the repro proves genuinely vacuous, #2367-B is descoped with a documented finding per FR-003.
- **SC-004**: NFR-001 — non-aborting merge byte-identical; INV-5 #1827 + AC-B3/AC-F1 + full merge suite green.
- **SC-005**: The FR-008 guard reds under a **runtime-stubbed** mark (stub `_persist_coord_reconcile_marker`/`coord_incoherent_done_wps` to a no-op, drive a real bake-path strand) — a guard that stays green under a runtime-stubbed mark, or that only source-greps for the mark call, is a tautology and is rejected. The guard enumerates the six restore sites and asserts ≈691's topology-gating.
- **SC-006**: The *modified* `test_issue_2786_*` is RED on the mission base (pre-fix) and asserts `committed == working` (re-reduced from the coord ref) **after** the heal step — a bare deletion of the old assertion without a post-repair contract fails this SC.
- **SC-007**: `stranded_wp_ids` is derived from the committed coord ref over *this merge's* write-set; in the ≥2-WP fixture it equals exactly the stranded WP (coherent WP excluded), and the SaaS-emit reconciliation is documented as fenced-out (FR-010), not silently dropped.

## Implementation Notes for Planning *(non-binding — from the research squad)*

Suggested WP slicing (red-first first; #2786 and #2367-B are one mechanism → one marker fix).
**Post-plan sequencing correction (priti):** each red assertion co-locates with the surface it
needs — a marker/doctor assertion in WP01 would red with `AttributeError` (setup-red, forbidden by
ADR 2026-07-17-1). WP01 keeps only the **git-reducible** reds. The whole set lands in **one PR**
(do NOT split repros from fix — a lone WP01 would open a red-main window).

- **WP01** — red-first, git-reducible reds only (FR-001/003 + split-brain half of FR-002):
   **modify** the existing `test_issue_2786_*` synchronous assertion so it asserts coherence *after*
   the heal step (SC-006 — never bare-delete); add the #2367-B repro (≥1 committed `done` then
   failure inside `_record_merged_wps_done_for_merge`, executor ≈406-408). Use a **≥2-WP fixture**
   (one stranded, one coherent). Reuse the #2711 coord harness (`_init_git_repo`,
   `_bootstrap_coord_mission`, `CoordinationWorkspace.worktree_path`; committed-ref reduction via
   `_durable_done_wps_on_coordination_ref`). *Expected-red until WP03 lands (single landing unit).*
- **WP02** — durable marker + shared owner (FR-004/005/009): add `pending_coord_reconcile`
   (`dict[str,Any]|None`) to `MergeState`, persisted at `.kittify/runtime/merge/<mission_id>/state.json`;
   add the `coordination`-layer `coord_incoherent_done_wps(coord_ref, candidate_wps)` (over
   `_durable_done_wps_on_coordination_ref`); extract `_persist_coord_reconcile_marker(run, error)`
   (CC≤15) calling it from BOTH strand sites (≈500-514 AND ≈406-408); mark-not-raise. Move FR-002's
   *marker-names-specific-WP* assertion here (surface now exists).
- **WP03** — repair + doctor (FR-006/007): dedicated `_heal_pending_coord_reconcile` at resume startup
   (strand-gated on committed-ref DONE, atomic clear; repair = forward `git revert`, NOT
   `advance_branch_ref`); register the check/fix into canonical
   `cli/commands/_coordination_doctor.py` (`_collect_coordination_findings` + `--fix` dispatch),
   reusing `DoctorFinding.error_code` and `coord_incoherent_done_wps`. Move FR-002's *doctor-exit-1*
   + FR-007's *negative* AC (marker+coherent→exit 0) here.
- **WP04** — class-closing guard (FR-008): **behavioral** guard reds under a runtime-stubbed mark;
   enumerate the six `_restore_final_bookkeeping_snapshots` sites, assert ≈691 topology-gating;
   prefer co-locating the mark at the `_restore_and_guard_coord_coherence` primitive (inner-only).

## Post-Spec Squad Findings (folded) *(audit trail)*

Two fresh lenses (reviewer-renata, python-pedro), read-only, code-verified. Verdict: **safe to
plan with-changes** — all folded above.

- **[BLOCKER, renata]** the existing on-main #2786 test asserts `committed==working` with no
  resume → permanently red under mark-not-raise → **FR-001 replaces that assertion**.
- **[HIGH, renata] #2367-B path corrected** — the real strand is a failure inside
  `_record_merged_wps_done_for_merge` (`executor.py:406-408` byte-restore-**without**-revert),
  NOT target-advance/squash-conflict (revert-covered, vacuous). It is the **same mechanism** as
  #2786 → one unified marker fix (FR-005 marks at both strand sites). #2367-B is real, not a
  phantom — folded, not descoped.
- **[HIGH, renata] non-fakeability** — marker names the *specific* stranded WP (committed-vs-working
  delta, not a static list); repair re-derives coherence from git (no clear-without-heal); doctor
  re-verifies incoherence (not marker-presence). Folded into FR-002/006/007.
- **[HIGH, renata] double-heal** — re-attempted revert must be **coherence-gated** (heal only
  while incoherent; a blind `git revert captured_sha..HEAD` re-applies `done`); + a resume-twice
  byte-identical AC. Folded into FR-006 / US2-S2,S3 / NFR-002.
- **[LOW, pedro] marker typing** — `from_dict` rehydrates a nested marker as a plain dict → type
  it `dict[str,Any]|None`. Folded into FR-004.
- **[MED, pedro] resume-repair** — needs a dedicated `_heal_pending_coord_reconcile` entry, not an
  overload of `_reconcile_completed_wps_for_resume`. Folded into FR-006.
- **[INFO, pedro] feasibility CONFIRMED** — `MergeState`/`save_state`/`DoctorFinding.error_code`/
  `resolve_placement_only` all exist and behave as claimed; three helper extractions keep the
  touched functions under CC-15; INV-5 tripwires safe as long as it stays inner-only (no wrapper
  around the phase driver, C-002).

**Tracker (actioned + verified post-plan, 2026-07-18):** #2786 = Bug/P0/parent **#1795**. #2367
**reparented** #2392(closed)→**#1795** and **retyped Task→Bug**. Mechanism A **split out to #2795**
(Bug, parent **#2017**, reuses the #2222 churn classifier); #2367 stays open tracking the A-residual
until #2795 lands. The mission PR **partially addresses #2367** (Mechanism B) — must NOT auto-close it.
Deferred (tracked): **#2795** (Mechanism A), the parallel-engine→`BookkeepingTransaction` retirement.

## Post-Plan Squad Findings (folded) *(audit trail)*

Four lenses (architect-alphonso, paula-patterns, planner-priti, reviewer-renata), read-only,
code-verified. All four verdicts **SAFE-WITH-CHANGES**; all folded above. One divergence adjudicated.

- **[HIGH, alphonso — design-changing] `stranded_wp_ids` derivation was wrong.**
  `_restore_final_bookkeeping_snapshots` restores **primary** paths, not the coord worktree → a
  committed-vs-working diff at the #2786 mark point returns **empty → no marker → silent strand-drop**.
  Corrected to derive from the **committed coord ref** via `_durable_done_wps_on_coordination_ref` over
  this merge's write-set. Folded into FR-002/004, data-model D7, research D7. **Divergence resolved:**
  supersedes the renata/paula/data-model "committed-vs-working delta" framing; renata's ≥2-WP fixture is
  *compatible* and verifies it (coherent WP excluded by construction).
- **[HIGH, paula] third same-shape strand site** at executor ≈690-692, dead-for-coord only via the
  unstated `done_marked_before_target` invariant → FR-008 enumerates six restore sites + asserts the
  gating; prefer marking at the restore primitive. Folded into FR-008, data-model, research D11.
- **[HIGH, paula + alphonso] one coherence owner + correct surfaces** — `coord_incoherent_done_wps` in
  `coordination/` consumed by mark+heal+doctor; doctor home corrected `doctor/` → canonical
  `cli/commands/_coordination_doctor.py`; repair primitive coordination-homed. Folded into FR-007/009,
  research D9.
- **[MED, alphonso] repair transport** — forward `git revert`, NOT `advance_branch_ref` (refuses non-FF).
  Folded into FR-006, C-003, data-model.
- **[MED, alphonso] SaaS emit** cannot be un-sent → explicit scope fence (FR-010, data-model D10).
- **[LOW, alphonso] storage path** — canonical `.kittify/runtime/merge/<mission_id>/state.json`, not
  legacy. Folded into FR-004, data-model.
- **[LOW, alphonso] INV-5 citation** — real ratchet is `test_executor_phase_boundary.py`; wrapping is
  wrong on *grain*, not that ratchet; "C-002" mis-borrowed. Folded into research D2 + note.
- **[HIGH, renata] anti-fakeability** — FR-002 ≥2-WP fixture; FR-008 behavioral falsifier
  (runtime-stubbed mark); FR-007 negative AC (marker+coherent→exit 0); FR-001 red-on-base SC. Folded
  into FR-001/002/007/008 + SC-005/006/007.
- **[HIGH, priti] sequencing** — FR-002's marker/doctor sub-asserts move to WP02/WP03 (else WP01 reds
  with `AttributeError`, forbidden setup-red); one-PR landing. **[HIGH/MED, priti] tracker** — see the
  Tracker line above (reparent/retype #2367, file #2367-A, partial-close).

## Post-Tasks Squad Findings (folded) *(audit trail)*

Three lenses (reviewer-renata, python-pedro, paula-patterns) on the 5 WPs, read-only, code-verified.
All three **SAFE-WITH-CHANGES**; all folded into the WP prompts + FR-005/007/008 + data-model.

- **[HIGH — renata + pedro DOUBLE-confirmed] SEVEN restore sites, not six.** `executor.py:701`
  (`_project_status_bookkeeping_to_target` failure) runs **outside** the `done_marked_before_target`
  guard → coord-reachable, un-marked, same #2786 shape. My six-site list would let WP05's DoD pass while
  the class stays open at 701. → FR-008 + WP03-T010 + WP05-T016 enumerate **programmatically** (SEVEN:
  407/536/670/691/701/757/786), route 701 through the marking primitive, assert its coord-reachability;
  691 stays dead-for-coord.
- **[HIGH — paula + renata converged] candidate set is unowned + untested.** `_MergeRunState` carries
  only `all_wp_ids`; passing it re-strands a pre-existing-`done` WP on resume. Every fixture uses
  "coherent = only-ever-approved" (excluded regardless), so `all_wp_ids` passes them all. → WP03 adds a
  `_MergeRunState` pre-target-write-set field; WP02/WP03 add a **pre-existing-done fixture** asserting
  that WP is excluded (DoD checkbox). Folded into FR-005 + data-model.
- **[HIGH — paula] doctor marker enumeration falls between WP02 and WP04.** `load_state(mission_id=None)`
  *raises* on ≥2 markers; no list-all API. → WP02 adds `iter_pending_coord_reconcile_markers(repo_root)`
  in `state.py` + test; WP04 consumes it. Folded into FR-007 + data-model.
- **[MED — paula + renata] WP03 DoD gaps** — pin the specific-WP `stranded_wp_ids` at the
  marker-construction site (not only WP02's reducer) + gate single-owner consumption (an inline
  `_durable_done_wps_on_coordination_ref` would pass the loose DoD → drift reopens). WP03-T010 primary
  over T008 (mark *through* the primitive; WP05's "routes-through-primitive" is the acceptance contract).
- **[MED — pedro] WP01 harness** — the #2711 `_bootstrap_coord_mission` is single-WP and has no
  bake-loop injection hook; it is in **no** WP's `owned_files`. WP01 authors its own multi-WP bootstrap
  in its owned file (reusing only `_init_git_repo`/`_git`), must NOT edit the unowned harness.
- **[LOW — pedro] cycle guard** — `coherence.py` repair fn must **function-locally** import
  `_make_merge_env` (module-top creates `merge.executor→coordination.coherence→lanes.merge→merge.config`).
  Reader half is clean. **[LOW — pedro] WP04** extract `_apply_coordination_fixes` for CC.
  **[LOW — renata] WP01** DoD: verify `merge --resume` no-ops (not raises) on base.
- **Concessions (all three):** WP05 behavioral falsifier, WP04 negative AC, WP01 no-bare-delete, NFR-002
  byte-identical, disjoint `owned_files`, real WP03∥WP04 parallelism, single-PR framing — all well-pinned.
  WP03 CC-15 not at risk (T010 delegation *reduces* CC); WP02 layer-clean (no coordination→merge import).

## Pre-Spec Squad Findings (folded) *(audit trail)*

Six lenses; convergent on the seam (extend the executor transaction, `MergeState` marker), one
divergence resolved:

- **A (debugger):** swallowed site `executor.py:500–514`; marker on `MergeState`; **mark-not-raise**; repair via resume+doctor.
- **B (architect):** #2367-B is #2711's root one level up (per-WP `BookkeepingTransaction`s + parallel rollback engine, not one atomic set); #2222 churn classifier already exists (for the deferred #2367-A).
- **C (paula):** shared-root **PARTIAL** — one seam closes #2786 + #2367-B; **#2367-A fenced out** (deliberate stop-gap). Recurrence #1826→#1878→#2711→#2786.
- **D (researcher):** existing #2786 red insufficient for the marker fix → **companion test needed**; #2367-B may be vacuous on the target-advance path. *(Superseded by post-spec: the live #2367-B strand is the bake-mid-write-set path at `executor.py:406-408`, NOT squash-conflict — see Post-Spec Squad Findings.)*
- **E (architect, seam-alignment):** **EXTEND** the executor's coord-write transaction; do **not** wrap `BookkeepingTransaction` (single-transition grain ≠ multi-phase grain — a second authority / 044 breach). Marker as a `MergeState` field. INV-5 safe **inner-only**. *(Resolves B's "one `BookkeepingTransaction`" toward an executor-transaction extension.)*
- **F (planner):** FOLD #2786 + #2367-B; DEFER #2367-A + cousins; parent under **#1795**; **no active collision** (sibling `…01KXRRB7` merged; worktree lingers = housekeeping); rebase onto post-#2785.
