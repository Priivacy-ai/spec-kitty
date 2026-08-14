---
work_package_id: WP02
title: 'Partition-correct the P0 auto-commit + Seam-A guard + #2549'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
- C-004
- C-006
- C-008
planning_base_branch: mission/write-path-integrity
merge_target_branch: mission/write-path-integrity
branch_strategy: Planning artifacts for this mission were generated on mission/write-path-integrity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/write-path-integrity unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-write-path-integrity-01KZZD69
base_commit: 8a1356aa7dff122de98644837c0ca498dc532de4
created_at: '2026-08-14T14:02:19.873807+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Partition purity
history:
- at: '2026-08-14T08:00:00+00:00'
  actor: system
  action: Prompt generated during tasks phase
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/integration/test_wp_integrity_p0_repro.py
- tests/integration/test_wp_integrity_cross_partition_scan.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/coordination/coherence.py
- src/specify_cli/coordination/transaction.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/lanes/worktree_allocator.py
- tests/integration/test_wp_integrity_p0_repro.py
- tests/integration/test_wp_integrity_cross_partition_scan.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Partition-correct the P0 auto-commit + Seam-A guard + #2549

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` via `/ad-hoc-profile-load`. This WP is the mission's **P0** — take the time.

## Objectives & Success Criteria

Close the #3371 P0 at its root: `implement.py`'s verbatim `placement_ref` arm commits a mixed
PRIMARY+COORD batch to one (coord) ref, landing PRIMARY `lanes.json` on coord and causing the lane
allocator's add/add merge conflict. Make the commit **partition-aware**, add the **Seam-A guard** so a
mis-route fails loud, and fix the residual **#2549** lane-status leak.

**Done when**:
- The non-vacuous SC-001 reproduction goes **RED→GREEN** (T007). (SC-001, FR-004)
- The `placement_ref` arm routes PRIMARY→`target_branch`, COORD-residue→coord, skips empty groups.
  (FR-001, C-006)
- A crash between the two commits recovers by idempotent re-drive. (FR-001, C-006)
- The Seam-A guard raises on PRIMARY→coord / COORD→lane, exempting `meta.json` co-travel. (FR-002, C-008)
- #2549: `move-task --force` status lands on coord, not the lane ref. (FR-003)
- SC-002 scan finds zero cross-partition artifacts. (SC-002, NFR-001)

## Context & Constraints

- Root cause (git-true): `implement.py::_commit_planning_artifacts_transaction` `:890-902`; the split
  helper `_partition_files_for_commit` `:714` is dead on this arm (used only by the legacy `else` arm
  `:947-961`). Reproduction commit `c3d92a364`. Plan IC-02/IC-03; ADR `2026-07-29-1` §3.
- **C-004 reversal is sanctioned**: this arm is a pinned verbatim deferral — rewrite the pinned tests,
  don't delete them.
- **Two mechanisms**: the guarded `commit_for_mission` classifier already refuses primary-on-coord; the
  P0 path is the **kind-agnostic `BookkeepingTransaction`** — it needs BOTH the split (T008) and a new
  guard (T011).
- **Landing order inside this WP**: split (T008) BEFORE the guard gets teeth (T011) — no silent
  mis-route window.

## Subtasks & Detailed Guidance

### Subtask T007 – RED-first non-vacuous SC-001 reproduction
- **Purpose**: A P0 acceptance test that is genuinely RED against current code and cannot false-GREEN.
- **Steps**: Do NOT reuse `tests/integration/coord_topology_fixture.py` (static read-routing; never
  drives implement). Compose the **real** path: create a coord-topology + PR-bound `--start-branch`
  mission, run real `_ensure_planning_artifacts_committed_git` then real `allocate_lane_worktree`.
  Before asserting the error, **pin two non-vacuity pre-assertions**: (a) `git ls-tree -r <coord_ref>`
  shows `lanes.json` on coord (the mis-route happened); (b) the `planning_commit_sha` tree also contains
  `lanes.json`. Then assert the **specific** `PlanningCommitMergeConflictError` (never a generic
  non-zero). Document why `--start-branch`/PR-bound is load-bearing (coord base and recorded planning
  tip genuinely diverge).
- **Files**: `tests/integration/test_wp_integrity_p0_repro.py`.

### Subtask T008 – Partition the `placement_ref` arm
- **Steps**: In `_commit_planning_artifacts_transaction`, replace the verbatim `placement_ref is not
  None` batch commit with `_partition_files_for_commit` → PRIMARY group to `target_branch`, COORD-residue
  to the coord ref. Copy the legacy arm's **skip-empty caller guard** (`if primary_files:` `:948` / `if
  coord_files:` `:961`) — **no `transaction.py` change** for skip-empty.
- **Files**: `src/specify_cli/cli/commands/implement.py`.

### Subtask T009 – Idempotent re-drive (crash-recovery)
- **Steps**: Switch `commit()`→`commit_idempotent()` across the **four** arms sharing
  `_run_planning_artifact_commit` so a crash between the PRIMARY and COORD commits recovers on
  re-invocation. Re-baseline those arms' tests (this is a deliberate behavior change).
- **Files**: `src/specify_cli/cli/commands/implement.py`, `src/specify_cli/coordination/transaction.py`.

### Subtask T010 – Rewrite the pinned verbatim tests
- **Steps**: `tests/…/test_implement_placement_routing.py` — `test_effective_destination_ref_is_placement_ref_verbatim`
  and siblings capture last-write-wins; rewrite with a **list-capture + mixed-kind** fixture asserting
  BOTH refs receive their partition. Preserve the structured-error/forbidden-ternary sibling guards.

### Subtask T011 – Seam-A guard + `meta.json` exemption
- **Steps**: At `_run_planning_artifact_commit`, classify staged paths by kind; apply the **single**
  `is_self_bookkeeping_churn` (`coherence.py:82`) exemption **before** kind classification; raise
  `PrimaryKindReachedCoordStagingError` (or equivalent) on PRIMARY→coord / COORD→lane. Add the positive
  test: a coord status commit co-traveling `meta.json` **succeeds**. Note: the FR-001 **split** routes
  by `is_coord_residue_churn` (meta.json already PRIMARY) — the self-bookkeeping predicate is for the
  **guard** + the SC-002 scan only (C-008).
- **Files**: `src/specify_cli/coordination/commit_router.py`, `src/specify_cli/coordination/coherence.py`,
  `src/specify_cli/cli/commands/implement.py`.

### Subtask T012 – #2549 reproduction + route/pin (WP entry gate for the #2549 slice)
- **Steps**: FIRST author a current-code reproduction naming which move-task path leaks:
  `tasks_move_task.py::_mt_commit_lane_deliverables` (`safe_commit` on the lane branch — bypasses Seam A)
  vs the port-based `commit_status` (wraps `commit_for_mission` — already guarded). If `--force` status
  lands on the **lane** ref via the first path → route it through Seam A. If the reproduction is GREEN
  (already routed on the #3383 base) → reduce to a regression pin. Respect Trigger A (status→coord under
  coord topology is correct).
- **Files**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`.

### Subtask T013 – SC-002 cross-partition scan
- **Steps**: Real-git lifecycle fixture asserting zero PRIMARY files on any coord ref and zero COORD
  files on any lane ref (`meta.json` excluded from the count), covering `implement` and `move-task
  --force`.
- **Files**: `tests/integration/test_wp_integrity_cross_partition_scan.py`.

## Definition of Done

- SC-001 RED→GREEN with the two pre-assertions; SC-002 scan green; the guard raises on mis-route and
  passes on `meta.json` co-travel; #2549 routed-or-pinned per the reproduction; pinned tests rewritten;
  `ruff`/`mypy` clean; no new arch-gate regression vs merge-base (NFR-003).

## Risks & Reviewer Guidance

- **Reviewer**: confirm T007's pre-assertions actually prove the mis-route (else false-GREEN). Confirm
  `commit_idempotent` switch covers all four arms. Confirm the guard exempts `meta.json` **before**
  classification (a coord+meta.json commit must not raise). Confirm the #2549 reproduction names the
  leaking mechanism and that the fix targets THAT path (not a no-op reroute of the already-guarded port).
