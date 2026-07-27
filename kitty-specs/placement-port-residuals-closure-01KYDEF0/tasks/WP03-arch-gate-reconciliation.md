---
work_package_id: WP03
title: Arch-gate reconciliation (allow-list + prefix narrowing + wording)
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-007
- FR-008
- FR-012
planning_base_branch: placement-port-residuals
merge_target_branch: placement-port-residuals
branch_strategy: Planning artifacts for this mission were generated on placement-port-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into placement-port-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T030
history:
- at: '2026-07-25T21:12:34Z'
  actor: tasks
  note: WP created from IC-03+IC-05 (FR-008, FR-012, FR-003, FR-004)
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_no_write_side_rederivation.py
- tests/architectural/test_guard_capability_call_sites.py
- tests/architectural/_placement_whole_tree_scan.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading anything else**, load `python-pedro` (role `implementer`) via `/ad-hoc-profile-load`;
adopt its directives/tactics and state which you applied. Then proceed.

## Objective

Green all four architectural gates PR #2920 left/deferred red — **entirely via test-side allow-list /
prefix edits + a documentation reconciliation** (no product-code change; the coord-seed commit is
legitimate as-is). Covers FR-008, FR-012, FR-003, FR-004.

Read first: `spec.md` (FR-003/004/008/012, SC-002, C-002), `plan.md` (IC-05 — the lockstep + 3-consumer
verification), `contracts/gate-reconciliation.md`, and the load-bearing memory
[[reference-write-side-rederivation-gate-grammar]].

## Context (post-squad, adjudicated from source)

- The write-side gate + guard-capability gate flag the SAME coord-seed `safe_commit(target=CommitTarget(ref=coord_ref), …, capability=MERGE_BOOKKEEPING)` at `merge/executor.py:1053-1060`. It is legitimate: best-effort write of `status.events.jsonl` (STATUS_STATE→COORD) to the captured `pre_target_coord_ref` on a merge path that must never abort. Resolution = **allow-list**, NOT seam-route, NOT downgrade to STANDARD.
- `BOUNDARY_SANCTIONED_PREFIXES` (`_placement_whole_tree_scan.py:95`) is a SHARED scope imported by three gates (`test_no_write_side_rederivation`, `test_safe_commit_import_boundary`, `test_read_surface_placement_guard`). The `migration/` subtree has ZERO `CommitTarget`/`safe_commit` calls, so dropping its prefix reds nothing on `_flip_phase` (C-001 corrected).
- **LOCKSTEP**: `test_no_write_side_rederivation.py:511` holds `_PINNED_BOUNDARY_SANCTIONED_PREFIXES` and `:916` hard-asserts equality with `BOUNDARY_SANCTIONED_PREFIXES`. Editing one without the other reds that meta-test.
- A SEPARATE, intentional `migration/` blanket lives in `test_mission_resolver_walker_gate.py::_MIGRATION_WALKER_DIR_PREFIXES` (C-004 rationale) — **do NOT touch it**; SC-002 is scoped to the placement-enforcement scan only.

## Subtasks

### T011 — FR-008: allow-list the coord-seed on the write-side gate
Add `"src/specify_cli/merge/executor.py"` to `test_no_write_side_rederivation`'s `BOUNDARY_SANCTIONED_MODULES`
(or the module's designated allow-list) with a dated rationale naming the merge coord-seed flow (best-effort
STATUS_STATE→COORD write of the captured `pre_target_coord_ref`). Verify the test greens.

### T012 — FR-012: allow-list the coord-seed on the guard-capability gate
Add `"src/specify_cli/merge/executor.py"` to `_PROTECTED_FLOW_ALLOWLISTS["MERGE_BOOKKEEPING"]`
(`test_guard_capability_call_sites.py:50`) with a rationale naming the ONE flow it authorizes (merge coord-seed).
Respect the bidirectional exact-binding check at `:114-118`. Verify green.

### T013 — FR-003: narrow the migration/ prefix (LOCKSTEP)
In `_placement_whole_tree_scan.py`, remove `"src/specify_cli/migration/"` from `BOUNDARY_SANCTIONED_PREFIXES`
and add per-file `BOUNDARY_SANCTIONED_MODULES` entries (each with an individual rationale) ONLY for genuine
sanctioned primitives; let every non-primitive migration module fall back into scope. **In the same commit**,
update `_PINNED_BOUNDARY_SANCTIONED_PREFIXES` (`test_no_write_side_rederivation.py:511`) to match, or the
`:916` meta-test reds. Keep `"src/mission_runtime/"` and `"src/specify_cli/upgrade/migrations/"` prefixes (C-002).

### T014 — Empirical C-001 check + 3-consumer verification
Confirm empirically that dropping the migration/ prefix does NOT red the write-side gate on `_flip_phase`
(the source-proof: migration/ has no CommitTarget/safe_commit). Then verify all THREE shared-scan consumers
green: `test_no_write_side_rederivation`, `test_safe_commit_import_boundary`, `test_read_surface_placement_guard`.
(Recorded refutation: the read-surface guard has no whole-scope offender scan, so no #2922 collision — C-003 holds.)

### T015 — FR-004: reconcile the guarantee wording
Update the SC-002/NFR-001 wording in the merged `coord-write-placement-closure-01KYCF83/spec.md` **by heading/anchor**
(not stale line numbers) to "closed for the `migration/` subtree in the placement-enforcement scan;
`upgrade/migrations/` prefix retained per C-002; the C-004 resolver-walker blanket is a separate permanent carve-out".
Do not overclaim an un-qualified "any module". **Out-of-map note**: this edits
`kitty-specs/coord-write-placement-closure-01KYCF83/spec.md` (not in `owned_files` — WPs cannot own
kitty-specs paths); it is a small, rationale-backed doc reconciliation — record the one-line rationale.

### T016 — Gate clean
`ruff` + `mypy --strict` clean; run the full `PWHEADLESS=1 pytest tests/architectural/ -q` — green.

### T030 — Tracker hygiene (FR-007) — VERIFY-ONLY (do NOT write from this worktree)
FR-007's artifacts are **orchestrator-seeded at planning**, NOT produced from this lane worktree — writing the
kitty-specs issue-matrix or minting GitHub issues from a code worktree is the exact coord/PRIMARY placement
hazard this mission closes (post-tasks squad: renata+priti). This WP only **verifies**:
- `kitty-specs/placement-port-residuals-closure-01KYDEF0/issue-matrix.md` exists and maps per-FR→one-issue
  1:1 (12 FR rows / 4 child issues): `#2923`←FR-001/002/003/004; `#2924`←FR-005/006; `#2926`←FR-008/012;
  Part-C←FR-009/010/011; FR-007=this hygiene row.
- The GitHub epic + native links (#2923/#2924/#2926 parented) are landed by the ORCHESTRATOR at PR/landing
  time (a mission-level step, outside every lane worktree). If not yet done at review, flag it — do not do it here.

## Branch Strategy
Planning base / merge target `placement-port-residuals`. Worktree per `lanes.json` via
`spec-kitty agent action implement WP03 --agent claude`. Depends on WP02 (Lane A serial).

## Definition of Done
- [ ] All four gates green (write-side, guard-capability, whole-tree scan, and the pinned meta-test).
- [ ] LOCKSTEP pinned-tuple edit done in the same commit as the prefix drop.
- [ ] All 3 shared-scan consumers green; empirical C-001 observation recorded.
- [ ] SC-002/NFR-001 wording precise (migration/-subtree-scoped); walker-gate untouched.
- [ ] Full `tests/architectural/` green; ruff/mypy clean.
- [ ] FR-007: orchestrator-seeded `issue-matrix.md` verified 1:1 (12 FR / 4 issues); GitHub epic-linking flagged if not yet landed (NOT done from this worktree).

## Risks / reviewer guidance
- Forgetting the pinned-tuple lockstep reds the meta-test — verify both edited together.
- Do NOT convert / touch the `_MIGRATION_WALKER_DIR_PREFIXES` blanket.
- Reviewer: confirm allow-list rationales are dated and name the single flow; confirm no product code changed; confirm `mission_runtime/` + `upgrade/migrations/` prefixes retained.
