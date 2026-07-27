# Implementation Plan: Merge squash provenance + rollback/resume coherence (P0 #2709/#2711)

**Branch**: `kitty/mission-merge-squash-provenance-and-rollback-coherence-01KXRRB7` | **Date**: 2026-07-17 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `kitty-specs/merge-squash-provenance-and-rollback-coherence-01KXRRB7/spec.md`

## Summary

Two related P0 defects in the mission-merge core, both surfaced in the #2658 merge, both
symptoms of one architectural class — the merge core writes to the committed target/coord
branch without reconciling against the durable event-log authority:

- **#2709 (happy path):** `git merge --squash -X theirs` clobbers target-newer `meta.json`
  acceptance/VCS fields and `traces/*.md`; separately, `_project_status_bookkeeping_to_target`
  blind-overwrites the target event log. Fix by per-artifact-class reconciliation (planning
  artifacts stay mission-authoritative; `meta.json` field-merged; traces unioned; event-log
  projection routed through the canonical `merge_event_payloads`).
- **#2711 (failure path):** rollback reverts only working-tree bytes, leaving the committed
  coord-branch `done` commit standing over reverted working status; `--resume` derives
  progress from a byte-reverted `MergeState` and re-emits duplicate `done`. Fix by **Option A**
  (revert the coord `done` commit on rollback → restores committed==working coherence) plus
  durable-log resume derivation.

Delivered ATDD-first: a red-first reproduction for each defect lands before its fix, on two
**decoupled chains** under one mission so the release-blocking #2709 can land independently of
the deeper #2711 surgery.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: git (custom `.gitattributes` merge drivers), typer, ruamel.yaml; internal `specify_cli.status.event_log_merge`, `specify_cli.merge.*`, `specify_cli.lanes.merge`, `specify_cli.coordination.status_transition`, `specify_cli.acceptance`
**Storage**: git-tracked mission artifacts — `status.events.jsonl` (append-only event authority), `meta.json`, `traces/*.md`; `.kittify/merge-state.json`
**Testing**: pytest; real-git coord harness (`tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py`), regression suite convention (`tests/regression/test_issue_<n>.py` with `pytestmark`), INV ratchets (`tests/architectural/test_merge_pipeline_ratchets.py`)
**Target Platform**: Linux/macOS/Windows CLI
**Project Type**: single project (CLI library)
**Performance Goals**: no merge-path latency regression; NFR-001 byte-identical no-divergence squash
**Constraints**: mypy --strict, ruff (complexity ≤ 15), no new-code Sonar regressions; INV-5 (#1827) ratchet must stay green; `-X theirs` planning-artifact authority (#1732) preserved
**Scale/Scope**: ~4–5 coordinated files for the `.gitattributes` driver wiring; localized executor/rollback edits; two new regression tests + invariant guards

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-first / red-first (C-011, DIRECTIVE_041/034):** PASS by construction — WP01a/WP01b
  commit failing reproductions (RED-for-the-right-reason per SC-001) before any fix; reviewer
  verifies RED-on-base → GREEN-on-final.
- **Single canonical authority (DIRECTIVE_044):** PASS — event-log reconciliation reuses
  `merge_event_payloads`; the new `meta.json` field reconciler is a fit-for-purpose reconciler
  for a *different* artifact, not a duplicate authority (C-001 wording clarified in spec).
- **Architectural gate discipline (DIRECTIVE_043):** the class-closing guard (FR-008) must be
  **non-vacuous and cover BOTH loss mechanisms** — a no-blind-copy lint over `merge/` projection
  (the `write_bytes` vector) **plus** a driver-registry-completeness lint (the `-X theirs`/no-driver
  vector in `lanes/merge.py`, blind to the projection lint — paula HIGH). Not a re-run of WP01.
  Split per chain (WP04a/WP04b) + one cross-cutting lint.
- **Canonical sources (DIRECTIVE_044):** PASS — repros drive the real `_run_lane_based_merge`
  entry point and reuse the canonical coord harness; no reconstructed paths.
- **Terminology canon (C-005):** `Mission` not `feature`; `--mission` flags.
- **Git/workflow discipline (DIRECTIVE_045):** PRs only, operator merges; no version numbers in
  scope; rebase-first (C-003) since the merge core was freshly refactored (#2057/#2173/#2632/#2675).
- **Tiered rigour:** core merge/rollback logic gets maximum rigour (it is core domain); test
  harness extensions get standard rigour.

**Phase-1 re-check RESOLVED (architect, code-verified):** Option A does NOT violate the INV-5
#1827 ordering ratchet — rollback runs on the failure path *before* the RECORD→commit→ASSERT
sequence and reorders nothing. **Anchor correction:** the INV-5 #1827 ratchet lives in
`tests/merge/test_executor_phase_boundary.py` + `tests/specify_cli/merge/test_1827_baseline_regression.py`,
NOT `tests/architectural/test_merge_pipeline_ratchets.py` (which locks #1826/#1736 — AC-B3
no-raw-`update-ref`, AC-F1 `_make_merge_env` env authority). Those AC-B3/AC-F1 lints *do* bind
IC-04's coord-`done`-revert mechanism (it moves a branch ref) — use `git/ref_advance.py::advance_branch_ref`
or coord-worktree `git revert`, never raw `update-ref`.

## Project Structure

### Documentation (this mission)

```
kitty-specs/merge-squash-provenance-and-rollback-coherence-01KXRRB7/
├── plan.md              # This file
├── spec.md              # Mission spec (squad-folded)
├── research/            # Pre-spec squad findings (lens-a..d)
├── tasks.md             # Phase 2 output (/spec-kitty.tasks)
└── tasks/               # WP prompt files
```

### Source Code (repository root)

```
src/specify_cli/
├── lanes/merge.py                     # _merge_branch_into squash (-X theirs), driver self-heal, _make_merge_env  (#2709)
├── merge/
│   ├── executor.py                    # _phase_bake_and_pre_target_done, _phase_mission_to_target, rollback   (#2711)
│   ├── bookkeeping_projection.py      # _project_status_bookkeeping_to_target (blind write_bytes), snapshot restore (#2709 FR-005, #2711)
│   ├── done_bookkeeping.py            # pre-target done emit, resume reconcile                                  (#2711)
│   ├── state.py                       # MergeState.completed_wps → advisory hint                               (#2711 FR-007)
│   └── baseline.py                    # record_baseline_merge_commit (idempotency surface)                     (#2709 edge)
├── coordination/status_transition.py  # worktree-first read contract (do NOT re-route — FR-007)
├── status/event_log_merge.py          # merge_event_payloads (canonical reconciler — reuse)                    (#2709 FR-005)
├── acceptance/__init__.py             # canonical acceptance field shapes                                      (#2709 FR-004)
└── cli/commands/
    ├── merge.py                       # _run_lane_based_merge (canonical entry point)
    ├── merge_driver.py                # existing event-log driver command (sibling for new drivers)            (#2709 FR-003/004)
    └── __init__.py                    # driver registration

tests/
├── regression/test_issue_2709_squash_provenance.py                 # WP01a
├── regression/test_issue_2711_merge_rollback_resume_coherence.py   # WP01b
├── specify_cli/cli/commands/test_merge_coord_topology_1772.py      # harness to extend
├── merge/test_merge_target_resolution.py                           # coord-worktree materialization pattern
├── merge/test_executor_phase_boundary.py                          # REAL INV-5 #1827 ratchet (must stay green)
├── specify_cli/merge/test_1827_baseline_regression.py             # REAL INV-5 #1827 baseline (must stay green)
└── architectural/test_merge_pipeline_ratchets.py                  # AC-B3/AC-F1 (#1826/#1736) lints; FR-008 lint home (NOT INV-5)
```

Also relevant: `src/specify_cli/git/ref_advance.py::advance_branch_ref` (sanctioned ref-move
for IC-04's coord-`done`-revert) and `src/specify_cli/merge/_constants.py` (`_STATUS_FILENAME`).

**Structure Decision**: Single-project CLI. Changes are confined to `src/specify_cli/{lanes,merge,coordination,status,acceptance,cli}` with new regression tests under `tests/regression/` and the class guard under `tests/architectural/`. No new top-level packages.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|-------------------------------------|
| New `meta.json` field-level merge driver (FR-004) | No reconciler exists for `meta.json`; `-X theirs` clobbers acceptance provenance | "Reuse `merge_event_payloads`" rejected — it is keyed event-union, structurally wrong for a keyed JSON object; a post-squash reconcile pass is the fallback if the driver proves unfit |
| Isolate the FR-004 driver **spike** into its own WP (architect MEDIUM) | The meta.json driver is the top unknown; bundling it with replicable wiring stalls the whole #2709 chain on a spike failure | Keeping it in WP02 rejected — a spike failure would block the release-blocking chain's low-risk work |
| Option A (revert coord `done` commit) over Option B (defer commit) | Restores committed==working coherence without touching the read-contract SSOT; **verified not to violate INV-5 #1827** | Option B rejected — it inverts `done_marked_before_target` machinery and fights the INV-5 #1827 phase-ordering ratchet |
| Helper extractions (`_revert_coord_done_commit`, `_union_event_logs`, **`_rematerialize_status_snapshot`**) | `_restore_pre_target_if_at_baseline` / projection near the 15-CC ceiling; FR-005's status.json re-reduce adds a pass | Inlining rejected — would breach complexity ceiling and lack focused test coverage |
| IC-04 co-top-risk with FR-004 (Ivan/architect) | Option A reaches across the executor↔coordination boundary (coord-ref resolve + revert) that does not exist today | Treating IC-04 as low-risk plumbing rejected — the coord-branch-ref capture/revert is net-new cross-boundary work |

## Implementation Concern Map

> Concerns are architectural areas, not WPs.
>
> **Old→final WP numbering (post-tasks renumber):** the prose below and the spec use the
> original draft IDs WP01a/WP01b/WP02/WP03/WP04a/WP04b. The finalized WPs are:
> WP01a→**WP01** (#2709 red), WP01b→**WP02** (#2711 red), WP02→**WP03** (#2709 fix),
> WP03→**WP04** (#2711 fix), WP04a→**WP05** (#2709 guard), WP04b→**WP06** (#2711 guard).
> Chains: WP01→WP03→WP05 (#2709) ∥ WP02→WP04→WP06 (#2711). See `tasks.md` for the authoritative graph.

### IC-01 — Red-first reproduction harness

- **Purpose**: Witness both defects against live code before any fix, RED-for-the-right-reason.
- **Relevant requirements**: FR-001, FR-002; SC-001.
- **Affected surfaces**: `tests/regression/test_issue_2709_*.py`, `tests/regression/test_issue_2711_*.py`; harness extensions in `test_merge_coord_topology_1772.py` (per-branch accept helpers, coord-worktree materialization, `real_baseline_recording` real-done seam, `review_status: approved` seed).
- **Sequencing/depends-on**: none (root of both chains); the two repros are independent.
- **Risks**: green-on-base traps — #2709 needs both-sides `meta.json` divergence; #2711 needs `done_marked_before_target=True` + committed-`done` precondition asserted. Canonical failure-injection target is `specify_cli.lanes.merge.integrate_mission_into_target` (NOT `specify_cli.merge.executor.*`).

### IC-02 — Squash artifact reconciliation (#2709 content)

- **Purpose**: Reconcile mission artifacts with target-newer canonical state instead of wholesale `-X theirs` replacement.
- **Relevant requirements**: FR-003 (per-class + traces union contract), FR-004 (meta.json field-merge — **spike-flagged top risk**), C-002 (#1732 preserved), C-006 (.gitattributes multi-surface wiring).
- **Affected surfaces**: `lanes/merge.py` (incl. **generalizing** `_ensure_event_log_merge_driver_config` — parametrize name/command, do NOT clone it, DIRECTIVE_044), `cli/commands/merge_driver.py` (+ new driver), `cli/commands/__init__.py`, root `.gitattributes`, `init.py`, a driver-config migration sibling, `acceptance/__init__.py` (field shapes).
- **Sequencing/depends-on**: IC-01 (the #2709 repro). **Split the FR-004 meta.json-driver spike into its own WP** (architect MEDIUM) so a spike failure fails fast without stalling the replicable traces/wiring work.
- **Risks**: FR-004 meta.json driver is the top spike risk; traces have no natural dedup key → union contract must be concrete or descoped to a post-merge pass; driver-under-`--squash -X theirs` is empirically confirmed to fire; `_make_merge_env` PATH pin already auto-covers new drivers; idempotency vs the post-merge baseline `meta.json` write.

### IC-03 — Event-log projection union + snapshot rematerialization (#2709 event log)

- **Purpose**: Stop the coord→target projection from blind-overwriting the target event log **and** the derived `status.json` snapshot.
- **Relevant requirements**: FR-005; C-001.
- **Affected surfaces**: `merge/bookkeeping_projection.py::_project_status_bookkeeping_to_target` — TWO blind writes: `:306` `status.events.jsonl` (→ union `source ∪ original`, both byte-sets already captured at `:302-303`, via `merge_event_payloads`) **and** `:308` `status.json` (→ **rematerialize from the unioned events via `reduce()`**, NOT blind-copy; it is a reduced snapshot, `_STATUS_FILENAME`). **Write both back through the already-resolved `trusted_*` target paths** returned by `_target_bookkeeping_status_paths` (seam-resolved via `primary_feature_dir_for_mission`) — compose no new path. Assert `snapshot == reduce(union)`.
- **Sequencing/depends-on**: IC-01 (needs its own witnessing RED — US2-S4, incl. a target-newer `status.json` field).
- **Risks**: NOT a ~5-line swap (both-side JSONL parse/serialize + a reduce pass); ensure the union is order-stable for NFR-001; a `_rematerialize_status_snapshot` helper (CC).

### IC-04 — Rollback/resume coherence (#2711 failure path) — **co-top-risk with FR-004**

- **Purpose**: Keep committed and working mission state coherent on rollback, and make `--resume` derive progress from durable events without duplicating transitions.
- **Relevant requirements**: FR-006 (Option A coord-`done`-revert), FR-007 (durable-log resume, `completed_wps`→hint); NFR-002 idempotency.
- **Affected surfaces**: `merge/executor.py` (`_restore_pre_target_if_at_baseline`; capture coord ref SHA before the pre-target done emit — **not captured today**, `pre_target_bookkeeping_snapshots` holds working bytes only), `merge/done_bookkeeping.py` (resume reconcile), `merge/state.py`, **`git/ref_advance.py::advance_branch_ref`** (sanctioned ref-move for the revert). **Source the ref-to-revert from `resolve_placement_only(repo_root, slug, kind=STATUS_STATE).ref`** (the canonical write-target the `done` commit used — NOT an inline `meta.get("coordination_branch")`, which reintroduces the retired D-2 CWD-divergence class). **FR-007 resume derivation consumes `read_event_log(EventLogReadContract.coordination_branch_ref(...))` + `wp_lane_actor_from_events()` (`coordination/status_service.py`) — do NOT author a new reducer, and do NOT re-route the `status_transition.py` read contract.** **Revert mechanism must be `advance_branch_ref` or coord-worktree `git revert` — never raw `update-ref` (AC-B3), env via `_make_merge_env` (AC-F1).** Note: the surface-resolution seam is path-only (`surface_path`/`primary_anchor`) and deliberately does not surface refs — do not seek the ref from `_with_anchor`.
- **Sequencing/depends-on**: IC-01 (the #2711 repro); rebase-first (C-003) + re-resolve anchors by symbol.
- **Risks**: co-equal top risk — Option A is net-new executor↔coordination cross-boundary work; coord ref SHA not currently captured; helper extraction near CC ceiling; **real** INV-5 #1827 ratchet homes (`test_executor_phase_boundary.py`, `test_1827_baseline_regression.py`) must stay green. **WP03 open question (resolve first):** confirm the coord `done` commit is made via `git commit` vs `update-ref` inside `BookkeepingTransaction`, and that `_read_contract_from_transaction_target` (`status_transition.py:680-693`) reads the worktree leg — governs whether AC-B3 binds the revert and whether Option A restores dedup "for free".

### IC-05 — Class-closing invariant guards (TWO mechanisms)

- **Purpose**: Prevent recurrence of the "merge silently overwrites target-newer canonical/durable state" class — covering BOTH the `write_bytes` projection vector AND the `-X theirs`/no-driver vector.
- **Relevant requirements**: FR-008; SC-005.
- **Affected surfaces**: `tests/architectural/` — (1) no-blind-copy AST lint over `merge/` projection paths; (2) **driver-registry-completeness lint**: every both-sides-divergent `kitty-specs/**` canonical glob has a registered merge driver (today root `.gitattributes` registers only `status.events.jsonl`); plus a property assertion `merge_output ⊇ target-newer canonical fields`. Precedent: `test_merge_pipeline_ratchets.py` already runs AST per-call-site lints.
- **Sequencing/depends-on**: co-delivered per chain — WP04a with the #2709 fix (IC-02/03), WP04b with the #2711 fix (IC-04); plus one thin cross-cutting lint.
- **Risks**: must be non-vacuous (a self-mutation check), not a re-run of IC-01 tests; the driver-registry lint is the piece that closes the class against *future* artifacts (paula HIGH).

### Cross-chain ownership note (Ivan MEDIUM)

The two "decoupled" chains are **not file-disjoint**: `merge/bookkeeping_projection.py` is edited
by both IC-03/WP02 (projection union) and IC-04/WP03 (rollback machinery — `_restore_final_bookkeeping_snapshots`,
`_capture_bookkeeping_snapshots` live here too). `/spec-kitty.tasks` MUST publish a
function-level ownership map for this module (or serialize the two edits) to avoid a merge
conflict when the chains land. **Campsite (DIRECTIVE_025) while in these files:** the stale
`_project_status_bookkeeping_to_target` shadow re-export in `cli/commands/merge.py.__all__`, and
the tracked temp artifact `tests/architectural/tmp_ratchet_baseline.txt`.
