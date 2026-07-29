---
work_package_id: WP11
title: Row-aware matrix merge driver
dependencies:
- WP05
- WP01
requirement_refs:
- FR-008
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
- The driver MUST be **3-way base-aware** (`%O`/`%A`/`%B`) — a 2-way merge cannot distinguish an added row from a deleted row and re-leaks clobber. This is why this WP has a **hard dependency on WP01** (a real common ancestor); without a shared `%O` the driver degrades to 2-way and the SC-003 durability regression is false-green.
- The issue-matrix driver pattern in `lanes/merge.py` is currently `kitty-specs/**/issue-matrix.md` — repoint to `issue-matrix.json`. The acceptance-matrix pattern is already `.json`.
- **#2970 (E1):** `merge_driver.py` has 5 S2083 BLOCKER path-injection findings — fold the hardening here, **red-first**, without weakening the merge contract (Sonar attack-vector-campsite doctrine).

## Subtasks

### T039 — Red-first #2970 path-injection repro
Before the rewrite, add a failing test reproducing the 5 S2083 path-injection findings in `merge_driver.py` (untrusted `%O`/`%A`/`%B` path handling). Fix the path handling; the regression must stay green.

### T040 — Row-aware base-aware drivers
Rewrite the acceptance + issue-matrix drivers per the algorithm contract: 3-way `%O`/`%A`/`%B`; row-key canonicalization (`criterion_id` for acceptance; canonicalized `issue_ref` for issue); per-row three-way reconciliation; **delete-vs-stale** disambiguation; stable canonical output order (byte-determinism). Never re-author a computed verdict (acceptance `overall_verdict` stays a property).

### T041 — M6: registration at three sites
- `lanes/merge.py`: repoint the `spec-kitty-issue-matrix` driver pattern `kitty-specs/**/issue-matrix.md` → `kitty-specs/**/issue-matrix.json`.
- `cli/commands/init.py:73,194`: update the new-repo `.gitattributes` pattern.
- Create a **NEW forward migration** `src/specify_cli/upgrade/migrations/m_3_2_7_issue_matrix_driver_repoint.py` repointing `**/issue-matrix.md` → `issue-matrix.json` for upgraded repos. **Do NOT** mutate the historical `m_3_2_6_gate_artifact_merge_drivers.py`.

### T042 — Tests
`tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`: disjoint-row union (two lanes, different keys → no clobber); stale-residue (base row deleted on one side, untouched on the other → dropped); same-field divergence → structured conflict (no silent pick, no abort); byte-determinism (shuffled input order → identical output); #2970 path-injection regression.

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP11` (depends on WP05, WP01).

## Definition of Done
- Row-aware base-aware drivers over structured JSON; registration fixed at all 3 sites; #2970 hardened (red-first).
- `ruff`/`mypy` clean; complexity ≤ 15; all five test cases green.

## Risks / Reviewer guidance
- **3-way, not 2-way** — verify `%O` is actually used; the durability regression is meaningless without WP01's common ancestor.
- Verify the migration is a **new** file (not a mutation of `m_3_2_6`).
- The #2970 fix must not weaken any merge-reconciliation rule.
- **Commit each slice** (#2970 repro+fix, drivers, registration) so worktree progress is durable.
