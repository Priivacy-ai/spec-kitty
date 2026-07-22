# Lens E — Canonical Seam Alignment (Architect Alphonso)

**Scope:** READ-ONLY pre-spec seam-alignment research for the contemplated fix in
mission `merge-coord-rollback-transactionality-01KXTM59` (#2786 + #2367): a
**transactional boundary for the merge's coord writes** (coord-branch ref moves +
status writes + worktree resync roll back atomically on failure, leaving a durable,
`doctor`/`merge --resume`-detectable reconcile marker).

**Lens:** DIRECTIVE_044 (Canonical Sources & Unification) + DIRECTIVE_001
(Architectural Integrity) + DIRECTIVE_043 (Close Defect Classes by Construction).
Central question per seam: does the contemplated boundary **route-through / extend /
avoid** each canonical authority, and what is the split-brain / duplication risk if it
bypasses.

**Directives applied:** 001, 003, 031, 043, 044 (044 load-bearing).

**Framing correction that drives every verdict below:** the merge pipeline
**already has** a coord-write transaction. It is not a single named object — it is the
`merge/executor.py` phase decomposition + `_MergeRunState`-threaded rollback
(`_restore_pre_target_if_at_baseline`, `_restore_final_bookkeeping_snapshots`) + the
#2711 committed-`done` coherent revert (`_revert_coord_done_commit`) + the INV-5/INV-6
ordering ratchets. The contemplated "transactional boundary" is therefore an
**extension of an existing transaction**, not a greenfield one. Every duplication risk
below flows from treating it as greenfield.

---

## Seam 1 — Coord/primary surface resolution

**Canonical symbol/module:** `coordination/surface_resolver.py` —
`resolve_status_surface` / `resolve_status_surface_with_anchor`
(`ResolvedStatusSurface{surface_path, primary_anchor}`), plus the placement facade
`mission_runtime.resolve_placement_only(repo_root, slug, kind=STATUS_STATE).ref`.
Read-path primitives it composes live in `missions/_read_path_resolver.py`
(`candidate_feature_dir_for_mission`, `coord_feature_dir`, `probe_coord_state`,
`stored_topology_from_meta`).

**Verdict: ROUTE-THROUGH (do not add a second resolver).**

The module docstring declares itself the **sole** canonical authority for coord-vs-primary
surface selection (FR-001/FR-007, NFR-003): "no secondary fallback or parallel resolution
mechanism survives outside this seam." The merge pipeline already obeys this:

- `_phase_baseline_and_surface` reads `resolve_status_surface(main_repo, slug)` and derives
  `canonical_events_path` / `canonical_status_path` from it — never a hand-composed
  `.worktrees/<slug>-coord/...` path.
- The #2711 additions `_capture_pre_target_coord_ref_sha` and
  `_durable_done_wps_on_coordination_ref` both source the coord ref from
  `resolve_placement_only(..., kind=STATUS_STATE).ref`, explicitly *not* an inline
  `meta.get("coordination_branch")` (the retired D-2 CWD-divergence class).
- `_coord_worktree_root(run)` re-derives the coord worktree by walking *up* from the
  already-resolved `canonical_events_path` — it does not re-resolve.

**Split-brain risk if bypassed:** a boundary that hand-rolls its own coord-ref/surface
derivation (e.g. `meta["coordination_branch"]` or a fresh `.worktrees` path compose)
reintroduces the #1589 / #1821 / #2069 class: CWD-dependent branch selection, a
wrong-but-plausible `kitty-specs/<mid8>/` surface, or topology re-inferred from
`coordination_branch is None` instead of the stored topology SSOT. The rollback would then
capture/revert a *different* ref than the one the write committed to — the exact coherence
break the mission exists to close.

---

## Seam 2 — Status write-target contract (the crux)

**Canonical symbols/modules:**
- `coordination/transaction.py::BookkeepingTransaction` — "the single owner of writes that
  target the coordination branch" / "single chokepoint for coordination-branch writes":
  `acquire → policy gate → append → materialize → commit → outbound → release`, with
  **surgical-truncate** event-log rollback (FR-010) + byte-snapshot artifact restore on
  exception, C-009 (never `git checkout --`).
- `coordination/status_transition.py` — `_read_contract_from_transaction_target`,
  `_resolve_write_target` (routes through `resolve_placement_only(...STATUS_STATE).ref`),
  `_TransactionIdentity`, the worktree-vs-committed-ref `EventLogReadContract` selection.
- `status/event_log_merge.py` — pure, deterministic three-way union of append-only event
  logs (dedupe by `event_id`, sort by `at`); a stateless helper, not a transaction.

**Verdict: EXTEND the executor's merge-time transaction; do NOT wrap
`BookkeepingTransaction` from outside, and do NOT build a third transaction object.**

This is where the duplication trap lives, so name the two granularities precisely:

1. **`BookkeepingTransaction` is the seam for a SINGLE coord status transition** (one
   `emit_status_transition_transactional` → one `safe_commit` on the coord branch, with
   in-process surgical rollback). It is already the atomic authority at that grain and must
   stay it.
2. **The merge's atomicity is a DIFFERENT grain** — a multi-phase span across *many* status
   writes (per-WP `done`), a mission→target branch integration, a `mission_number` bake, a
   baseline record, and a bookkeeping projection commit. The executor already runs its own
   rollback orchestration for this span (`_capture_bookkeeping_snapshots` /
   `_restore_final_bookkeeping_snapshots` / `_restore_pre_target_if_at_baseline` + #2711
   `_revert_coord_done_commit`). Notably the merge path does **not** funnel its status
   writes through `BookkeepingTransaction` — it uses `commit_merge_bookkeeping` /
   `_mark_wp_merged_done` + its own snapshot machinery.

An "outer coord merge transaction" that *wraps* `BookkeepingTransaction` (or wraps the phase
driver) would become a **second transaction authority** governing the same coord branch —
two rollback mechanisms with two commit orderings racing over one ref. That is the
DIRECTIVE_044 violation. The seam-aligned move is to **consolidate and name the executor's
existing per-phase rollback** into the mission's "coord merge transaction" — extending the
`_MergeRunState` + `_restore_*` + `_revert_coord_done_commit` machinery — while each
*individual* coord status write it performs continues to compose the same
`status_transition` / `safe_commit` primitives. `event_log_merge` is consumed as-is for any
log reconciliation; it is not a transaction and needs no change.

**Split-brain risk if bypassed:** two authorities that both "own coordination-branch writes"
is the definitional single-canonical-authority breach — divergent rollback semantics
(surgical-truncate vs snapshot-restore vs ref-revert) applied to the same ref produce
exactly the committed-vs-working `done`/`approved` divergence #2711 just closed.

---

## Seam 3 — Ref-move seam

**Canonical symbol/module:** `git/ref_advance.py::advance_branch_ref` — the single
sanctioned forward branch-ref advance, with the #1826 invariant (no worktree left checked
out behind an advanced ref), the AC-B3 ratchet (no raw `git update-ref` in `src/specify_cli`
outside this module — `tests/architectural/test_merge_pipeline_ratchets.py`), and AC-F1
(`_make_merge_env`). It **refuses non-fast-forward moves by design**
(`RefAdvanceNonFastForwardError`).

**Verdict: ROUTE-THROUGH for forward advances; for ROLLBACK use the established
forward-revert pattern (`_revert_coord_done_commit`), NOT a backward `update-ref`.**

The #2711 code already models the correct asymmetry: forward coord/lane/mission advances go
through `advance_branch_ref`; the rollback of a committed coord `done` cannot use
`advance_branch_ref` (moving the ref *back* to the captured tip is the non-FF move it
refuses), so `_revert_coord_done_commit` performs a **forward reversing `git revert`** inside
the coord worktree (HEAD+index+working-tree resync), wrapped in `_make_merge_env` (AC-F1),
never a raw `update-ref` (AC-B3-symmetric). The contemplated boundary must adopt this exact
pattern for any coord-write rollback.

**Split-brain / duplication risk if bypassed:** a transactional rollback reaching for
`git update-ref <ref> <old_sha>` (a) trips the AC-B3 ratchet, and (b) recreates the #1826
defect class — a coord/lane worktree left behind its own HEAD, so the next safe-commit
through it sees phantom staged deletions. The "worktree resync" leg named in the mission
must therefore *be* `advance_branch_ref`'s resync (forward) + `git revert`'s resync
(rollback), not a new reset routine.

---

## Seam 4 — Durable marker authority

**Canonical symbol/module:** `merge/state.py::MergeState` at
`.kittify/runtime/merge/<mission_id>/state.json` (per-mission), with
`save_state`/`load_state`/`clear_state`/`has_active_merge`, the merge lock, and the resume
reconcile `done_bookkeeping._reconcile_completed_wps_for_resume` →
`_durable_done_wps_on_coordination_ref`. Contrast: `status/doctor.py` (a set of stateless
`check_*` advisories — no merge-state ownership) and `status/doctor_husks.py`.

**Verdict: EXTEND `MergeState` — a new FIELD, not a new sidecar, not a `doctor.py` marker.**

`MergeState` is already the canonical durable, resumable, `doctor`/`merge --resume`-visible
merge marker: it carries `current_wp`, `has_pending_conflicts`, `mission_number_baked`,
`push_requested` — precisely the "durable pointer the operator can repair from" role the
contemplated reconcile marker wants. The #2711 design is the precedent: `completed_wps` is
explicitly demoted to an **advisory hint** (docstring on the field), and the *authority* for
resume progress is the **durable committed event log** on the coord ref
(`_durable_done_wps_on_coordination_ref`), against which the hint is reconciled and stale
entries dropped + re-saved. So the marker split is already doctrine:

- **Authority of truth** = the committed coordination-branch event log (via
  `resolve_placement_only` + `read_event_log`).
- **Repairable index/pointer** = `MergeState` fields.

A reconcile marker should be a new `MergeState` field (e.g. a rollback/repair-needed flag +
the captured pre-emit coord tip already modelled transiently as
`_MergeRunState.pre_target_coord_sha`), persisted via `save_state`.

**Split-brain / duplication risk if bypassed:** a new sidecar file (e.g.
`.kittify/coord-reconcile.json`) or a marker owned by `status/doctor.py` forks the
resume-state authority `MergeState` already owns — two files answering "is a merge
mid-flight / needs repair" that `--resume`, the lock, and `clear_state` would then have to
keep in sync. That is a second authority by construction.

---

## Seam 5 — INV-5 / #1827 phase-ordering ratchet

**Canonical guards:** `merge/executor.py::_run_lane_based_merge_locked` frozen phase list;
`tests/merge/test_executor_phase_boundary.py`
(`test_locked_driver_calls_phases_in_frozen_order`,
`test_record_then_commit_then_assert_ordering`, INV-6 restore-then-reraise tests);
`tests/specify_cli/merge/test_1827_baseline_regression.py`. Frozen order: baseline **RECORD**
(`_phase_capture_and_baseline`, post-target-merge / pre-bookkeeping-commit) → bookkeeping
**safe_commit** → baseline **ASSERT** (`_phase_commit_and_assert`, post-commit); INV-6 =
`_restore_final_bookkeeping_snapshots`-then-reraise at each failure exit, per-exception-class
scoped.

**Verdict: REAL RISK — an *outer* boundary would violate it; the safe form is *inner*
extension (the #2711 pattern).**

An outer contextmanager wrapping the whole coord-write span with its own
commit/rollback sequencing is the dangerous shape: it can reorder RECORD → commit → ASSERT,
or move the commit relative to the baseline record, or add a rollback exit that the INV-6
per-class scoping and the frozen-order test do not cover. #2711 demonstrates the sanctioned
way to add coord-rollback coherence **without touching INV-5**: it added `pre_target_coord_ref`
/ `pre_target_coord_sha` *fields* to `_MergeRunState`, a capture call inside the existing
`_phase_bake_and_pre_target_done`, and a revert call *inside* the existing
`_restore_pre_target_if_at_baseline` — the phase list and the RECORD/commit/ASSERT order were
untouched, and the phase-boundary + 1827 regression tests stayed green. The contemplated
boundary must extend the same way: new `_MergeRunState` fields, new helpers called from
*within* existing phases and the existing `_restore_*` sites — never a wrapper around the
phase driver.

**Risk flag:** any design that introduces a `with CoordMergeTransaction(...)` around
`_run_lane_based_merge_locked` (or around `_phase_commit_and_assert`) should be treated as an
INV-5 regression until proven otherwise against both test files.

---

## VERDICT

A "coord merge transaction + durable reconcile marker" **is seam-aligned — but only as an
EXTENSION of the merge executor's already-existing coord-write transaction**, not as a new
authority. It **routes-through** `surface_resolver` / `resolve_placement_only` for every
coord ref/surface read (Seam 1), **routes-through** `advance_branch_ref` for forward moves
and the `_revert_coord_done_commit` forward-revert for rollback (Seam 3), and **consumes**
`event_log_merge` as-is. It **extends** `MergeState` with the durable marker as a field
(Seam 4) and **extends** `BookkeepingTransaction`'s per-write atomicity only at the
single-transition grain (Seam 2). It **must not** become an outer wrapper (Seam 5 / INV-5).

**It risks a second authority** — and should be rejected in that form — if implemented as:
(a) an outer transaction object wrapping the phase driver or `BookkeepingTransaction`;
(b) a new sidecar reconcile file outside `MergeState`;
(c) any hand-rolled coord-ref / surface / ref-move / topology resolver;
(d) a backward `git update-ref` rollback (AC-B3 breach + #1826 revival).

**Single recommended seam to extend:** the **`merge/executor.py` `_MergeRunState`-threaded
phase-rollback orchestration** — specifically `_restore_pre_target_if_at_baseline` +
`_revert_coord_done_commit` + the `_restore_final_bookkeeping_snapshots` exit sites — with
the durable marker persisted as a **`MergeState` field** via `save_state`. This is the merge
pipeline's coord-write transaction; the #2711 change is the exact, tested precedent for
growing it coherently without disturbing INV-5.
