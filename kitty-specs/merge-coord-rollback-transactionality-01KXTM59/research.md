# Phase 0 Research — Merge coord-write rollback transactionality

Consolidates the 6-lens pre-spec research (`research/lens-a..f-*.md`) and the post-spec squad
(reviewer-renata + python-pedro). Every decision below is code-verified against `main`.

## D1 — Marker home: extend `MergeState`, not a sidecar file

- **Decision**: Add `pending_coord_reconcile: dict[str, Any] | None` to `MergeState`
  (`src/specify_cli/merge/state.py`), persisted through the existing `save_state`.
- **Rationale**: `MergeState` already persists to `.kittify/merge-state.json` and survives across
  `merge --resume`; `from_dict` drops unknown keys, so an old state file simply rehydrates the
  field as `None` — **no migration**. A sidecar file would add a new artifact + its own lifecycle.
- **Alternatives considered**: dedicated sidecar JSON (rejected — needless artifact + migration);
  a new dataclass field (rejected by pedro — `from_dict` rehydrates a plain `dict`, so a nested
  dataclass would silently arrive as a dict; type it `dict[str, Any] | None`).

## D2 — Fix seam: extend the executor rollback, don't wrap it in a transaction

- **Decision**: Extend the executor's existing coord-write rollback seam
  (`_MergeRunState` + `_restore_pre_target_if_at_baseline` / `_revert_coord_done_commit` /
  `_restore_final_bookkeeping_snapshots`). Mark at the two strand sites; heal on resume.
- **Rationale (B-vs-E divergence resolved)**: the per-WP `coordination.transaction.BookkeepingTransaction`
  is a **single-commit, single-lock** chokepoint; the merge's pre-target done write-set is a
  **multi-WP loop** (`_record_merged_wps_done_for_merge`, each WP opening its own transactional emit).
  Wrapping the linear phase driver in one `BookkeepingTransaction` is a genuine **grain mismatch** —
  that, not a ratchet, is the load-bearing reason it is wrong (alphonso: a `with` wrapper would
  *indent* but not *reorder* the phase substrings, so it likely would **not** trip the ordering
  ratchet). Extending the existing seam is minimal and ratchet-safe (inner-only changes).
- **Citation correction (alphonso LOW)**: the enforced INV-5 #1827 ratchet is
  `tests/merge/test_executor_phase_boundary.py::test_locked_driver_calls_phases_in_frozen_order`
  (asserts frozen `_phase_*` call order). "C-002" was mis-borrowed — in this corpus it maps to
  *doctrine governance union*, not a merge-phase constraint. **Task guardrail:** if the resume heal is
  inserted *within* the driver, it must NOT be added to the asserted `expected_order` list, or the
  ratchet flips red on a correct change (a tests-as-scaffold trap).
- **Alternatives considered**: wrap in `BookkeepingTransaction` (rejected — grain mismatch +
  #1827 tripwire); raise on failure (rejected — see D4).

## D3 — #2367-B is the SAME mechanism as #2786 (post-spec correction)

- **Decision**: Treat #2367-B and #2786 as one defect class. The live #2367-B strand is a failure
  **inside `_record_merged_wps_done_for_merge`** whose byte-restore-only branch
  (`executor.py:406-408`) restores working bytes **without** calling `_revert_coord_done_commit` —
  the identical "byte-restore-without-revert" mechanism as #2786 (where the revert is *called but
  fails*). One marker-at-both-sites fix closes both.
- **Rationale**: renata + pedro traced the paths against `main`. The *target-advance* and
  *squash-conflict* rollback paths already run `_restore_final_bookkeeping_snapshots` +
  `_revert_coord_done_commit` (`executor.py:535-536`), so a #2367-B repro there is **vacuously
  green**. The strand only exists on the bake path.
- **Alternatives considered**: reproduce #2367-B on the squash-conflict path (rejected — vacuous;
  lens-D's original guess, now superseded); descope #2367-B as a phantom (rejected — it is real on
  the bake path).

## D4 — Mark-not-raise on strand

- **Decision**: On revert failure (or the bake byte-restore branch), *persist the marker and
  continue*; do **not** raise.
- **Rationale**: raising out of the rollback would skip leg-b byte-restore, leaving the working
  tree dirty AND masking the real target-advance fault that triggered the rollback. Marking keeps
  the working tree consistent and defers the (committed-side) coherence repair to resume/doctor.
- **Alternatives considered**: raise + abort (rejected — masks the primary fault, worse operator
  state).

## D5 — Repair is coherence-gated, git-re-derived, and idempotent

- **Decision**: Heal on `merge --resume` via a dedicated `_heal_pending_coord_reconcile` entry
  (NOT an overload of `_reconcile_completed_wps_for_resume`). The re-heal acts **only while
  committed-vs-working is still incoherent** (re-derived from the coord ref via
  `wp_lane_actor_from_events`), then clears the marker atomically.
- **Rationale (renata double-heal finding)**: a blind `git revert captured_sha..HEAD` on resume
  would revert the *successful* revert and re-apply `done`. Gating on live incoherence — not on
  `head != captured_sha` — makes a second resume a no-op (NFR-002), including a crash between heal
  and clear (the next run re-derives coherent → no-op → clears).
- **Alternatives considered**: unconditional re-revert (rejected — double-heal re-applies `done`);
  clear-then-heal (rejected — a clear-without-heal would drop the strand silently).

## D6 — Doctor re-verifies, never trusts the marker

- **Decision**: `doctor coordination` loads `MergeState` markers, **re-verifies** committed-vs-working
  incoherence from git, and only then reports (stable `error_code`, exit 1); `--fix` runs the same
  repair as resume.
- **Rationale**: marker-presence alone is fakeable and can go stale (e.g. a prior resume healed but
  crashed before clearing). Re-verification makes the check truthful and the fix idempotent.
- **Alternatives considered**: report on marker-presence only (rejected — false positives on stale
  markers; not the contract US2-S4 demands).

## D7 — Non-fakeable marker contents *(REVISED post-plan — architect-alphonso HIGH)*

- **Decision**: `stranded_wp_ids` = the WP(s) **this merge marked `done`** (its pre-target done
  write-set) that still reduce to `DONE` on the **committed coordination ref** after rollback —
  derived via `_durable_done_wps_on_coordination_ref(candidate_wps=<this merge's write-set>)`. NOT a
  static list; NOT a live committed-vs-working worktree diff.
- **Rationale**: a committed-vs-working diff computed *at the #2786 mark point* (inside
  `_revert_coord_done_commit`, **before** the later `_restore_final_bookkeeping_snapshots`) returns an
  **empty delta** — that restore touches **primary `repo_root`** paths, never the coord worktree, so
  both sides read `done` → no marker → silent strand-drop (the mission's own failure mode). The
  committed ref is the reliable authority at any mark point; the "approved" side is known **by
  construction** (the rollback's intent). Scoping candidates to *this merge's* write-set excludes a
  genuinely-pre-existing-`done` WP; the committed-ref membership excludes a never-committed coherent
  WP — together satisfying renata's ≥2-WP non-fakeability fixture (a hardcoded `["WP01"]` or an
  over-broad `all_wp_ids` both fail).
- **Alternatives considered**: committed-vs-working delta via `wp_lane_actor_from_events` (rejected —
  empty at the #2786 mark point; the original pre-plan framing, now superseded); static/all-WP list
  (rejected — fakeable).
- **Note**: the *existing* on-main #2786 test asserts final-state committed-vs-working (post-restore),
  a **different** observation point where the diff IS non-empty — that assertion stays valid; only the
  *marker's* internal derivation changes to the committed-ref authority. Confirm the empty-at-mark-point
  timing with the IC-01 repro before locking the derivation (alphonso's static trace, conceded).

## D8 — Scope fence: #2367-A deferred

- **Decision**: #2367-A (VCS-lock resync) is **out of scope**, tracked under #2017; the #2222 churn
  classifier already exists for it.
- **Rationale (B-vs-C divergence resolved)**: paula + planner agree the shared root closes
  #2786 + #2367-B with one seam; #2367-A is a distinct lock-resync concern. Bundling it would widen
  past one coherent seam and delay the P0 split-brain fix.

## D9 — Canonical surfaces: one coherence owner, correct doctor home, right repair transport *(post-plan)*

- **Decision**: (a) one `coordination`-layer `coord_incoherent_done_wps(coord_ref, candidate_wps)`
  (thin wrapper over `_durable_done_wps_on_coordination_ref`) consumed by mark + heal-gate + doctor —
  no per-call-site re-implementation; (b) the repair primitive (`git revert` of the stranded commit)
  homed as a coordination-layer function consumed by both executor-resume and `doctor --fix`, NOT
  executor-private; (c) the doctor check/fix registers into the **canonical** coordination-doctor
  surface `src/specify_cli/cli/commands/_coordination_doctor.py` (`_collect_coordination_findings`,
  `DoctorFinding.error_code`, the existing `--fix` dispatch), NOT `src/specify_cli/doctor/` (orphan-ops).
- **Rationale (paula HIGH + alphonso Q1/Q4)**: three independent re-derivations of the strand set is
  the ownership-confusion smell that produces #2786-C drift; a diagnostic command depending on
  merge-executor internals inverts the dependency; a second coordination-doctor home is a DIR-044
  canonical-source split. The repair is a forward `git revert` (not `advance_branch_ref`, which refuses
  the non-FF move) — AC-B3/AC-F1 clean.
- **Alternatives considered**: private executor helpers for the delta (rejected — layer leak);
  `advance_branch_ref` for repair (rejected — structurally refuses non-FF); a new `doctor/` coordination
  check (rejected — canonical split).

## D10 — SaaS/dashboard outbound-emit reconciliation fenced OUT *(post-plan — alphonso Q5)*

- **Decision**: out of scope. `git revert` heals the tracked coord artifacts + committed materialization,
  but the outbound SaaS emit for the transient `done` cannot be un-sent; the hosted projection may
  transiently show `done` for a rolled-back WP until the next authoritative emit reconciles it.
- **Rationale**: SaaS is advisory / eventually-consistent; a compensating emit is a distinct concern.
  Recorded as an explicit scope fence (Complexity Tracking + doctor remediation notes), not a silent
  omission (DIR-031).
- **Alternatives considered**: emit a compensating `approved` transition during heal (deferred — widens
  scope past the split-brain fix; separate follow-up if product deems the transient projection unacceptable).

## D11 — Root-cause enumeration, not two-sites *(post-plan — paula HIGH)*

- **Decision**: FR-008 enumerates all six `_restore_final_bookkeeping_snapshots` sites (≈406, 536, 670,
  691, 757, 786), documents that site ≈691 (post-target `_record_merged_wps_done_for_merge` failure) is
  the same restore-without-revert shape and is dead-for-coord **only** via the `done_marked_before_target`
  invariant (≈350-352), and prefers co-locating the coherence-mark at the restore **primitive**
  (`_restore_and_guard_coord_coherence`) so a future restore site cannot strand silently.
- **Rationale**: marking two hand-picked callers proves the marker path for one injected rollback but
  does not close the enumeration — a flipped `done_marked_before_target` or a new coord-routed restore
  reintroduces the strand. Co-locating at the primitive is **inner** (not the phase-driver wrapper INV-5
  forbids) → converts "mark at two callers" into "mark by construction at the restore seam".
- **Alternatives considered**: mark only at 406-408 + 500-514 (rejected — leaves 691 as a #2786-C seed);
  full transaction rewrite (rejected — grain, D2).

## Feasibility confirmation (python-pedro)

`MergeState` / `save_state` / `DoctorFinding.error_code` / `resolve_placement_only` /
`wp_lane_actor_from_events` all exist on `main` and behave as the plan assumes. Three helper
extractions keep the touched functions ≤ CC-15. INV-5 #1827 / AC-B3 / AC-F1 ratchets stay green as
long as changes remain inner-only (no wrapper around the phase driver, no raw `git update-ref`,
coord env via `_make_merge_env`). **Verdict: buildable as specified.**
