# Implementation Plan: Merge coord-write rollback transactionality (#2786 + #2367-B)

**Branch**: `fix/merge-coord-rollback-transactionality` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/merge-coord-rollback-transactionality-01KXTM59/spec.md`

## Summary

A merge that rolls back after committing coord-`done` bookkeeping can leave the coordination
branch **incoherent** — the committed reduction says a WP is `done` while the working-tree
reduction (and reality) says `approved` — re-opening the #2711 split-brain. Two strands share
**one mechanism** (byte-restore-of-working-tree *without* reverting the committed coord commit):

- **#2786** — `_revert_coord_done_commit` is *called but fails*; the failure is swallowed
  (`executor.py:500-514`) and rollback continues, stranding the committed `done`.
- **#2367-B** — a failure *inside* `_record_merged_wps_done_for_merge` hits the byte-restore-only
  branch (`executor.py:406-408`) that *never calls* `_revert_coord_done_commit` at all.

**Approach (chosen):** make any rollback that strands committed coord state either **revert** or
**mark-and-repair**. Persist a durable `MergeState.pending_coord_reconcile` marker at both strand
sites (mark-not-raise, so leg-b byte-restore still runs), heal it on `merge --resume` via a
dedicated coherence-gated repair entry, and surface + `--fix` it from `doctor coordination`. The
executor's existing coord-write rollback seam is *extended*, not wrapped — no new transaction
abstraction (rejected: grain mismatch vs per-WP `BookkeepingTransaction`; see research.md).

**Rejected alternatives:** (a) *raise on revert failure* — skips leg-b byte-restore and masks the
underlying target-advance fault; (b) *wrap the phase driver in a BookkeepingTransaction* — wrong
grain + trips the INV-5 #1827 phase-ordering ratchet (C-002); (c) *sidecar marker file* — needless
new artifact + migration when `MergeState` already persists and `from_dict` drops unknown keys.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib + existing `specify_cli.merge` / `specify_cli.coordination` / `specify_cli.status` / `specify_cli.doctor` packages; no new third-party dependency
**Storage**: canonical per-mission runtime state `.kittify/runtime/merge/<mission_id>/state.json` (existing `MergeState`, extended with one optional field; NOT the legacy `.kittify/merge-state.json`); coord branch `status.events.jsonl` (append-only event log, unchanged format)
**Testing**: pytest ATDD/red-first — `tests/regression/test_issue_2786_*`, `tests/regression/test_issue_2367_*`, `tests/merge/`, `tests/architectural/` (INV-5 #1827 via `tests/merge/test_executor_phase_boundary.py` + AC-B3/AC-F1 ratchets), doctor tests. Reuse the #2711 coord harness (`_init_git_repo`, `_bootstrap_coord_mission`, `CoordinationWorkspace.worktree_path`); committed-ref reduction via `_durable_done_wps_on_coordination_ref`
**Target Platform**: Linux/macOS dev + CI (git worktree merge machinery)
**Project Type**: single (CLI/library — `src/specify_cli`)
**Performance Goals**: none new — the marker/repair path runs only on the rollback/resume/doctor cold paths; the happy-path merge stays byte-identical (NFR-001)
**Constraints**: repair is a forward coord-worktree `git revert` (env via `_make_merge_env`, AC-F1) — **NOT** `git/ref_advance.py::advance_branch_ref` (it refuses the non-FF move to `captured_sha`); no raw `git update-ref` (AC-B3); no wrapper around the phase driver (INV-5 #1827 — wrong on *grain*, see research D2); touched functions stay ≤ CC-15 via helper extraction; ATDD red-first before fix; no direct push to origin/main
**Scale/Scope**: 4 WPs; ~1 new `MergeState` field, 2 mark call-sites, 1 resume repair entry, 1 doctor check + fix, 3 helper extractions, ~3 regression test files (2 new + 1 modified)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Loaded via `spec-kitty charter context --action plan` (compact; DIR-001…DIR-013).

| Gate / Standing Order | Applies? | How this plan satisfies it |
|---|---|---|
| **ATDD-first / red-first (test-remediation discipline)** | ✅ | WP01 lands red-first repros before any fix; existing #2786 assertion is *modified* (FR-001) so it can go green post-repair rather than stay permanently red. |
| **Red-main-is-honest (ADR 2026-07-17-1)** | ✅ | Repros carry `@pytest.mark.regression` + issue-referencing docstrings; they fail for the product reason, not setup. |
| **Architectural gate discipline** | ✅ | INV-5 #1827 (no wrapper around phase driver), AC-B3 (no raw `update-ref`), AC-F1 (`_make_merge_env`) held green; FR-008 adds a *non-vacuous* class-closing guard. |
| **Single canonical authority (DIR-044)** | ✅ | Marker lives on the canonical `MergeState`; repair reuses the resume path; doctor reuses `DoctorFinding.error_code`. No parallel state. |
| **Campsite cleaning / CC-15** | ✅ | 3 helper extractions keep `_record_merged_wps_done_for_merge`, the resume entry, and the doctor check ≤ CC-15; each extraction gets focused tests. |
| **Canonical sources, no improvisation** | ✅ | Extends the existing executor rollback seam + `resolve_placement_only`/`wp_lane_actor_from_events`; no hand-rolled coord-ref reads. |
| **Git/workflow discipline (no direct push)** | ✅ | Lands via consolidation → local `main` → `pr/<slug>` PR (same as #2785); never `git push origin main`. |
| **Tracker Ticket Assignment Rule** | ✅ | #2786 = Bug/P0/parent **#1795**. #2367 **reparented** #2392(closed)→**#1795** + **retyped Task→Bug**; Mechanism A **split out to #2795** (Bug, parent **#2017**, reuses #2222). The mission PR **partially addresses #2367** (Mechanism B) — must NOT auto-close it (A tracked by #2795). Done + verified 2026-07-18. |
| **Pre-existing Failure Reporting Rule** | ✅ | Baseline reds (known-P0 / CI-env / stale-install) classified per the folded gotcha doc; only branch-red-∧-base-green folded. |

**One gate PENDING (tracker hygiene), no unjustified code violations.** The Complexity Tracking rows below record the deliberate scope fences (#2367-A + SaaS-emit reconciliation fenced out).

## Project Structure

### Documentation (this mission)

```
kitty-specs/merge-coord-rollback-transactionality-01KXTM59/
├── plan.md              # This file
├── spec.md              # Committed, substantive (post-spec squad folded)
├── research.md          # Phase 0 — consolidated decisions (this command)
├── data-model.md        # Phase 1 — the pending_coord_reconcile marker shape (this command)
├── research/            # 6-lens pre-spec research (lens-a..f) — already committed
└── tasks/               # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── merge/
│   ├── executor.py        # strand sites: _record_merged_wps_done_for_merge failure (≈406-408),
│   │                      #   _revert_coord_done_commit failure branch (≈500-514);
│   │                      #   third same-shape site ≈690-692 (dead-for-coord via done_marked_before_target ≈350-352);
│   │                      #   + _persist_coord_reconcile_marker helper (marks at both live sites);
│   │                      #   + _heal_pending_coord_reconcile at resume startup (strand-gated);
│   │                      #   FR-008: co-locate mark at _restore_and_guard_coord_coherence primitive (inner-only)
│   ├── done_bookkeeping.py # _durable_done_wps_on_coordination_ref (committed-ref strand reader — reuse)
│   └── state.py           # MergeState.pending_coord_reconcile: dict[str, Any] | None (+ from_dict); runtime state path
├── coordination/          # coord_incoherent_done_wps(coord_ref, candidate_wps) — SINGLE coherence owner
│   │                      #   (over _durable_done_wps_on_coordination_ref) consumed by mark + heal + doctor;
│   │                      #   + git-revert repair primitive (coordination-homed, not executor-private)
│   └── status_service.py  # wp_lane_actor_from_events / EventLogReadContract.coordination_branch_ref
└── cli/commands/
    └── _coordination_doctor.py  # CANONICAL doctor coordination surface: register _check_stranded_coord_revert
                            #   into _collect_coordination_findings + _fix into the existing --fix dispatch
                            #   (reuse DoctorFinding.error_code) — NOT a new src/specify_cli/doctor/ home

tests/
├── regression/
│   ├── test_issue_2786_revert_failure_split_brain.py   # MODIFY: assert coherence AFTER heal (SC-006)
│   └── test_issue_2367_*.py                            # NEW — bake-mid-write-set strand repro (≥2-WP fixture)
├── merge/
│   ├── test_executor_phase_boundary.py                 # INV-5 #1827 frozen phase-order ratchet (do not add heal to expected_order)
│   └── ...                                             # helper-level unit coverage
└── architectural/                                      # AC-B3/AC-F1 + FR-008 behavioral guard
```

**Structure Decision**: Single-project CLI/library. No new package. The fix extends the existing
`merge` executor rollback seam, adds one optional `MergeState` field, one `coordination`-layer
coherence owner + repair primitive (consumed by resume AND doctor), and registers a check/fix into
the **canonical** coordination-doctor surface. The strand set is derived from the committed coord ref
(not a worktree diff — data-model D7). No data model beyond the marker; no API contracts (internal
merge machinery).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| #2367-A (VCS-lock resync) fenced out of this mission | Deliberate stop-gap: the shared root closes #2786 + #2367-B with one seam; #2367-A is a distinct lock-resync concern with its own churn classifier (#2222) | Bundling #2367-A would widen scope past one coherent seam and delay the P0 split-brain fix; tracked separately under #2017 |
| **SaaS/dashboard outbound-emit reconciliation fenced OUT** (alphonso Q5) | `git revert` heals tracked coord artifacts + committed materialization, but the transient `done` SaaS emit cannot be un-sent; SaaS is advisory / eventually-consistent | A compensating emit widens scope past the split-brain fix; the hosted projection self-heals on the next authoritative emit. Separate follow-up if product deems the transient projection unacceptable (FR-010) |
| Helper extractions (`_persist_coord_reconcile_marker`, `_heal_pending_coord_reconcile`, `coord_incoherent_done_wps`, coordination-homed `git-revert` repair, doctor `_check_stranded_coord_revert`) | Keep touched functions ≤ CC-15; one shared coherence owner prevents the three-way strand-derivation drift (#2786-C seed); coordination-homed repair avoids doctor→executor dependency inversion | Inlining would push the touched functions past CC-15 and leave new branches only integration-covered; three private re-derivations of the strand set is the ownership-confusion smell paula flagged |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Red-first reproduction (git-reducible reds only)

- **Purpose**: Prove both #2786 (revert-failed) and #2367-B (revert-never-called) strand committed coord state, and un-break the permanently-red existing assertion — using only assertions whose surfaces exist today.
- **Relevant requirements**: FR-001, FR-003, split-brain half of FR-002; US1 scenarios 1,3 + the split-brain half of scenario 2.
- **Affected surfaces**: `tests/regression/test_issue_2786_revert_failure_split_brain.py` (MODIFY the ~line-204 assertion → assert coherence *after* the heal step, SC-006; never bare-delete), `tests/regression/test_issue_2367_*.py` (NEW — inject failure inside `_record_merged_wps_done_for_merge` after ≥1 committed `done`), **≥2-WP fixture** (one stranded / one coherent), reuse #2711 coord harness; committed-ref reduction via `_durable_done_wps_on_coordination_ref`.
- **Sequencing/depends-on**: none (first). **Expected-red until IC-03 lands — single-PR landing unit.**
- **Risks (priti sequencing):** marker-exists / doctor-exit-1 assertions do NOT belong here — those surfaces don't exist yet, so asserting them would red with `AttributeError` (setup-red, forbidden by ADR 2026-07-17-1). They move to IC-02/IC-03. #2367-B must inject on the **bake** path (target-advance/squash-conflict are revert-covered/vacuous, alphonso).

### IC-02 — Durable marker + single coherence owner + mark-not-raise at both strand sites

- **Purpose**: Persist a non-fakeable marker naming the *specific* stranded WP (committed-ref authority) so no strand is silently swallowed; establish the ONE coherence owner.
- **Relevant requirements**: FR-004, FR-005, FR-009; US2 scenario 1 + FR-002's marker-names-specific-WP assertion.
- **Affected surfaces**: `src/specify_cli/merge/state.py` (`pending_coord_reconcile: dict[str, Any] | None`, `from_dict`; canonical runtime state path), `src/specify_cli/coordination/` (`coord_incoherent_done_wps(coord_ref, candidate_wps)` over `_durable_done_wps_on_coordination_ref` — the SINGLE owner), `src/specify_cli/merge/executor.py` (extract `_persist_coord_reconcile_marker(run, error)` calling the owner; call from the ≈500-514 revert-failure branch AND the ≈406-408 bake branch; `save_state`; mark-not-raise so leg-b byte-restore still runs).
- **Sequencing/depends-on**: IC-01 (red first).
- **Risks (alphonso HIGH):** `stranded_wp_ids` MUST derive from the **committed coord ref** over *this merge's* write-set — a live committed-vs-working diff is **empty at the #2786 mark point** (restore touches primary paths, not the coord worktree) → silent strand-drop. `from_dict` rehydrates a plain dict (type `dict[str,Any]|None`). Must not perturb the happy path (NFR-001).

### IC-03 — Strand-gated repair (resume) + canonical doctor detection/fix

- **Purpose**: Heal the strand deterministically and idempotently; make it operator-detectable via the canonical doctor surface.
- **Relevant requirements**: FR-006, FR-007; US2 scenarios 2–5, NFR-002.
- **Affected surfaces**: `src/specify_cli/merge/executor.py` (dedicated `_heal_pending_coord_reconcile` at resume startup — strand-gated on committed-ref DONE, atomic clear; NOT an overload of `_reconcile_completed_wps_for_resume`), `src/specify_cli/coordination/` (git-revert repair primitive, consumed by resume AND doctor), **`src/specify_cli/cli/commands/_coordination_doctor.py`** (register `_check_stranded_coord_revert` into `_collect_coordination_findings` + `_fix_stranded_reverts` into the existing `--fix` dispatch; reuse `DoctorFinding.error_code` + `coord_incoherent_done_wps`).
- **Sequencing/depends-on**: IC-02 (marker + owner must exist).
- **Risks (alphonso/paula):** doctor home is the CANONICAL `_coordination_doctor.py`, NOT `src/specify_cli/doctor/` (orphan-ops — a second authority = DIR-044 breach). Repair = forward `git revert` (env via `_make_merge_env`), NOT `advance_branch_ref` (refuses non-FF). Re-heal gates on *live* strand-on-ref (a blind revert re-applies `done`); doctor needs the **negative** AC (marker+coherent→exit 0). Resume-twice byte-identical incl. a crash between heal and clear (NFR-002).

### IC-04 — Class-closing invariant guard (behavioral)

- **Purpose**: Prevent regression of the whole defect class — any rollback leaving a stranded `done` on the committed coord ref MUST leave a durable marker.
- **Relevant requirements**: FR-008; SC-005.
- **Affected surfaces**: `tests/architectural/` (behavioral property/guard test), and preferably the executor `_restore_and_guard_coord_coherence` primitive.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks (renata/paula):** MUST be **behavioral** — red under a *runtime-stubbed* mark (no-op `_persist_coord_reconcile_marker`/`coord_incoherent_done_wps`) driving a real bake strand; a source-grep-for-the-call guard is a tautology and is rejected. MUST enumerate all six `_restore_final_bookkeeping_snapshots` sites (≈406/536/670/691/757/786) and assert site ≈691 is dead-for-coord only via `done_marked_before_target` (≈350-352). Preferred structural close: co-locate the mark at the restore primitive so a future restore site cannot strand silently (inner-only, INV-5-safe).
