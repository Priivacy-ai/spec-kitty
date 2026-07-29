---
work_package_id: WP01
title: Lane-base common ancestor
dependencies: []
requirement_refs:
- FR-009
- NFR-005
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-write-side-seam-matrix-tracer-01KYP3MH
base_commit: 0bd7a72bf3a2a0bd2ef3268bb88f4e30b43ada29
created_at: '2026-07-29T10:39:03.774940+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/lanes/
create_intent:
- docs/adr/3.x/2026-07-29-1-lane-base-recorded-planning-commit.md
- tests/lanes/test_lane_base_common_ancestor.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/lanes/worktree_allocator.py
- src/specify_cli/lanes/auto_rebase.py
- src/specify_cli/merge/executor.py
- src/specify_cli/merge/ordering.py
- docs/adr/3.x/2026-07-29-1-lane-base-recorded-planning-commit.md
- tests/lanes/test_lane_base_common_ancestor.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2993'
- '1684'
- '2274'
---

# Work Package Prompt: WP01 – Lane-base common ancestor

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `architect-alphonso`
- **Role**: `implementer`

## Objective

Make an execution lane branch from the **recorded planning-artifact commit** (the finalize-tasks tip captured in `lanes.json`/`meta.json`), not the pre-planning coord tip nor a moving `target_branch` tip, so **PRIMARY-partition planning-artifact writes** (spec/plan/tasks/finalized plan/analysis-report) share a common ancestor with the consolidation base and are **not reverted at merge** (#2993). (Matrix/tracer are COORD-partitioned and serialize onto the coord surface — they do NOT traverse lane branches, so their durability is orthogonal to this base; see the `%O` note in T001.) This is a P0 git-topology change and is **ADR-first**.

## Context

- Today the coordination branch is minted at `mission create` off `target_branch` **before** spec/plan/tasks exist; planning artifacts land on `target_branch` afterward. A lane branched off the coord tip therefore has *no common ancestor containing planning artifacts* with the consolidation base — the #2993 P0.
- Governing decisions: this ADR **amends** `2026-04-03-1-execution-lanes-own-worktrees-and-mission-branches`; cite `2026-06-24-1` (§5 partition: planning on PRIMARY, matrix/tracer/status on COORD), `2026-06-24-2` (`target_branch`/`meta.json` anchor), `2026-07-23-2` (post-consolidation deferral — **no consolidation abort path**).
- `merge/ordering.py` is a pure frontmatter topo-sort — **not** ancestor-dependent — but is in scope so its invariants are re-verified against the new base.

## Subtasks

### T001 — Author the lane-base ADR
Create `docs/adr/3.x/2026-07-29-1-lane-base-recorded-planning-commit.md`. It MUST:
- Pin the lane base to a **recorded SHA** captured at finalize-tasks (in `lanes.json`/`meta.json`), never "current tip of `target_branch`" (moving-tip trap).
- **Resolve the coord-status-lineage question explicitly** in light of `2026-06-24-1` §5 and this mission's FR-007 routing: since matrix/tracer/status writes are routed OFF the lane onto coord (FR-007), the lane base carries **planning (PRIMARY) lineage**; decide and document whether/how the merge-base needs coord-status lineage given `auto_rebase._refuse_preexisting_lane_status_deletions` reasons over coord status in the merge-base. Disentangle FR-009 ancestry (primary) from FR-008 row-aware-merge durability (coord).
- **Record the DECIDED FR-008 merge-driver `%O` partition (E-B, adjudicated 2026-07-29 against code):** the driver's `%O` comes from the **seam-resolved matrix surface for the active topology** — coord lineage under coord topology, primary/`target_branch` lineage under flat — **NOT this WP's primary lane base**. `ISSUE_MATRIX`/`ACCEPTANCE_MATRIX` are COORD-partition kinds (`artifacts.py:172-183`) that `resolve_placement_only`/`declared_read_surface` place topology-dependently (`resolution.py:1602-1607`, `:1211-1217`), and under coord topology they **serialize onto the single coord worktree** (`commit_router.py:248-306`), never diverging on lane branches. Therefore WP01's recorded SHA governs **PRIMARY-partition (planning-artifact) durability through lane consolidation only**; matrix `%O` is orthogonal to it. State this explicitly with those citations; there is **no hard FR-008↔FR-009 coupling** (WP11-T045 seeds `%O` from the resolved surface, not this base).
- State **no consolidation abort path** (`2026-07-23-2`).
- Cite ADRs by slug.

### T002 — Record the planning SHA
Persist the finalize-tasks planning-artifact commit SHA into `lanes.json`/`meta.json` at finalize time (the value the allocator will read). Keep it immutable once recorded.

### T003 — Retarget the lane base
In `worktree_allocator.py` (~L211-227), base the lane worktree/branch on the recorded SHA from T002, not the moving tip. Preserve the existing worktree/branch naming.

### T004 — Reconcile rebase + dependent-lane invariant
In `auto_rebase.py`, reconcile merge-base reasoning with the new base; keep the dependent-lane invariant **#1684** intact. Note (do not fix here) that lane-hygiene guard **#2274** compares `kitty-specs/` by commit-history not content → a false-positive after the planning-rebase; coordinate #2273/#2626/#2570.

### T005 — Merge/ancestor regression tests
Add `tests/lanes/test_lane_base_common_ancestor.py`: a lane created from the recorded SHA shares a common ancestor with the consolidation base; a representative write on the lane survives consolidation with zero silent reversion; assert `merge/ordering.py` topo-sort is unchanged by the base change.

## Branch Strategy

Planning branch and final merge target are both `feat/write-side-seam-matrix-tracer`. `/spec-kitty.implement WP01` allocates this WP's execution worktree from the computed lane in `lanes.json`; do not reconstruct the path.

## Definition of Done
- ADR authored, amends `2026-04-03-1`, resolves coord-status-lineage, no abort path.
- Lane base reads the recorded SHA; `ruff`/`mypy` clean; complexity ≤ 15.
- Regression tests green; #1684 preserved.

## Risks / Reviewer guidance
- **Moving-tip trap** — reject any base derived from `HEAD`/`tip of target_branch` at allocate time; it MUST be the recorded SHA.
- Confirm the ADR actually decides the coord-status-lineage question (not defers it) — WP11's SC-003 durability regression depends on this WP.
- No consolidation abort path may be introduced.
