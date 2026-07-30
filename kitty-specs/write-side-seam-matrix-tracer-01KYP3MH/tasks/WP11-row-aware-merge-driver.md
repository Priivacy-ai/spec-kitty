---
work_package_id: WP11
title: Row-aware matrix merge driver
dependencies:
- WP05
requirement_refs:
- FR-008
- FR-002
- C-008
- NFR-005
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T039
- T040
- T041
- T042
- T045
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- src/specify_cli/upgrade/migrations/m_3_2_7_issue_matrix_driver_repoint.py
- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/merge_driver.py
- src/specify_cli/lanes/merge.py
- src/specify_cli/cli/commands/init.py
- src/specify_cli/upgrade/migrations/m_3_2_7_issue_matrix_driver_repoint.py
- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2482'
- '2970'
---

# Work Package Prompt: WP11 – Row-aware matrix merge driver

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Replace the whole-file "more-filled-side" acceptance/issue-matrix merge drivers with **row-aware, base-aware** drivers over the structured JSON so concurrent disjoint-row writes union without clobber (#2482 + the disjoint-row gap). Fold the #2970 path-injection hardening. Fix driver **registration at all three sites** (M6). See [contracts/merge-driver-algorithm.md](../contracts/merge-driver-algorithm.md).

## Context

- Grounding **refuted** the "row-aware" claim: `spec-kitty-acceptance-matrix`/`-issue-matrix` are whole-file `_write_more_filled_side` (`merge_driver.py:333/347/357`); only `-traces`/`-event-log` union. This WP builds genuine row-aware drivers over the WP05 structured schema.
- The driver MUST be **3-way base-aware** (`%O`/`%A`/`%B`) — a 2-way merge cannot distinguish an added row from a deleted row and re-leaks clobber. **`%O` is topology-resolved** (adjudicated 2026-07-29, see `contracts/merge-driver-algorithm.md` + WP01-T001): it is the git merge-base blob on the **seam-resolved matrix surface for the active topology** — coord lineage under coord topology (this mission), primary/`target_branch` lineage under flat. Matrices are COORD-partitioned and, under coord topology, **serialize onto the single coord worktree** (`commit_router.py:248-306`) — they never diverge on lane branches, so **FR-008 durability does NOT depend on WP01's primary lane base**. The WP01 hard edge is dropped; WP11 needs only a real (non-synthetic) `%O` from the resolved consolidation lineage.
- The issue-matrix driver pattern in `lanes/merge.py` is currently `kitty-specs/**/issue-matrix.md` — repoint to `issue-matrix.json`. The acceptance-matrix pattern is already `.json`.
- **#2970 (E1):** `merge_driver.py` has 5 S2083 BLOCKER path-injection findings — fold the hardening here, **red-first**, without weakening the merge contract (Sonar attack-vector-campsite doctrine).

## Subtasks

### T039 — Red-first #2970 path-injection repro
Before the rewrite, add a **true red-first repro** (not a scanner-count mirror): drive the driver's real `main(argv)` entry with untrusted `%O`/`%A`/`%B` arguments containing traversal/absolute-path vectors (e.g. `../`, an absolute `/etc/...` path) and assert the driver refuses/sanitizes rather than reading/writing outside the intended matrix path — the concrete shape of the 5 S2083 findings in `merge_driver.py`. Fix the path handling; the regression must stay green.

### T040 — Row-aware base-aware drivers
Rewrite the acceptance + issue-matrix drivers per the algorithm contract: 3-way `%O`/`%A`/`%B`; row-key canonicalization (`criterion_id` for acceptance; canonicalized `issue_ref` for issue); per-row three-way reconciliation; **delete-vs-stale** disambiguation; stable canonical output order (byte-determinism). Never re-author a computed verdict (acceptance `overall_verdict` stays a property).

### T041 — M6: registration at three sites
- `lanes/merge.py`: repoint the `spec-kitty-issue-matrix` driver pattern `kitty-specs/**/issue-matrix.md` → `kitty-specs/**/issue-matrix.json`.
- `cli/commands/init.py:73,194`: update the new-repo `.gitattributes` pattern.
- Create a **NEW forward migration** `src/specify_cli/upgrade/migrations/m_3_2_7_issue_matrix_driver_repoint.py` repointing `**/issue-matrix.md` → `issue-matrix.json` for upgraded repos. **Do NOT** mutate the historical `m_3_2_6_gate_artifact_merge_drivers.py`.

### T042 — Tests (driver-unit, synthetic %O)
`tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`: disjoint-row union (two lanes, different keys → no clobber); stale-residue (base row deleted on one side, untouched on the other → dropped); same-field divergence → structured conflict (no silent pick, no abort); **intra-side duplicate-key** (two raw rows on one side normalizing to the same key → structured error/deterministic dedupe, never silent drop); byte-determinism (shuffled input order → identical output); #2970 path-injection regression. These construct `%O`/`%A`/`%B` synthetically and pass **regardless of WP01** — they prove the algorithm, not the durability.

### T045 — SC-003 durability-integration regression (real `%O` from the resolved surface)
Add the integration test that actually bites (T042's unit tests use synthetic `%O` and pass regardless). Seed `%O` from the **seam-resolved matrix surface for the active topology**, NOT a synthetic base and NOT WP01's lane SHA: for this mission's **coord** topology, drive a real-git merge whose base is the **coord-branch** matrix blob, with two divergent sides writing **disjoint** rows, and assert both rows survive via the row-aware driver — zero clobber, zero silent reversion (SC-003). Also cover the **flat-topology** case (matrices on `target_branch`, `%O` from the target lineage) since that is where lane-branch divergence actually occurs. Because matrices serialize onto the single coord worktree under coord topology (`commit_router.py:248-306`), document that the coord-topology disjoint-row case is a coord-surface / coord↔target-integration merge, not a lane→mission 3-way. No dependency on WP01 (matrix `%O` is coord-lineage, orthogonal to the primary lane base).

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP11` (depends on WP05, WP01).

## Definition of Done
- Row-aware base-aware drivers over structured JSON; registration fixed at all 3 sites; #2970 hardened (red-first).
- `ruff`/`mypy` clean; complexity ≤ 15; all five test cases green.

## Risks / Reviewer guidance
- **3-way, not 2-way** — verify `%O` is actually used and drawn from the **seam-resolved matrix surface for the active topology** (coord lineage here), not a synthetic base and not WP01's primary lane SHA.
- Verify the migration is a **new** file (not a mutation of `m_3_2_6`).
- The #2970 fix must not weaken any merge-reconciliation rule.
- **Commit each slice** (#2970 repro+fix, drivers, registration) so worktree progress is durable.
