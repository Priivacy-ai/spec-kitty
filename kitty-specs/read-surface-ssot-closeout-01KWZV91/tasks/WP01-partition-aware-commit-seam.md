---
work_package_id: WP01
title: Partition-aware commit_for_mission seam (foundation)
dependencies: []
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2700616"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_commit_router_partition.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/commit_router.py
- tests/specify_cli/coordination/test_commit_router_partition.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile via `/ad-hoc-profile-load` for
`python-pedro` (implementer). Adopt its identity, governance scope, and boundaries. Then read
`kitty-specs/read-surface-ssot-closeout-01KWZV91/spec.md`, `plan.md`, and
`contracts/partition-aware-commit-seam.md`. **Append to `traces/design-decisions.md` when you
make a per-file classification or fast-path decision, and to `traces/tooling-friction.md` if a
gate or command fights you.**

## Objective

Make `commit_for_mission` **per-file partition-aware** so a mixed-partition file batch stops
misrouting coordination artifacts to the primary branch. This is the **root fix for #2404 at the
seam** (C-006, Directive-043) — it closes `spec_commit_cmd.py` (`kind=SPEC`) and
`mission_finalize.py` (`kind=TASKS_INDEX`) **by construction**, with no per-caller patch. This WP
is the foundation WP02/WP03 consume.

## Context

- **Defect** (`commit_router.py:152`): `commit_for_mission(..., *, kind, ...)` resolves ONE
  placement for the whole batch — `resolve_placement_only(repo_root, mission_slug, kind=kind)`. A
  batch mixing a PRIMARY kind (e.g. TASKS_INDEX) with `acceptance-matrix.json` (COORD) commits
  every file under the caller's single kind → coord artifact lands on primary → `accept` reads a
  stale copy (#2404).
- **The landed base gives you everything** (from #2462): `kind_for_mission_file(path, mission_slug=...)`
  (`mission_runtime/artifacts.py`) classifies per file; `is_primary_artifact_kind` + the frozensets
  are public; the kind-aware leaf helpers already take `kind` and enforce
  `PrimaryKindReachedCoordStagingError`.
- **Contract**: `contracts/partition-aware-commit-seam.md` (INV-C1, C-002, no fast-path regression).
- `_planning_commit_worktree` was renamed by #2462 → `_resolve_commit_worktree_for_kind` (alias kept).

## Subtasks

### T001 — Red-first: mixed batch misroutes; None-file batch still lands
Add `tests/specify_cli/coordination/test_commit_router_partition.py`:
- **RED-1**: submit a batch mixing a PRIMARY file (e.g. `plan.md`/`tasks.md`) and a COORD file
  (`acceptance-matrix.json`) under `kind=TASKS_INDEX`; assert (currently failing) that each file
  lands on its OWN partition's ref. Prove it's RED against current code first.
- **RED-2**: submit a batch containing a `None`-classified file (`kind_for_mission_file` → `None`,
  e.g. a gap-analysis / generator-config path) under `kind=SPEC`; assert it still commits (to the
  caller-kind ref). Prove the naive rewrite would drop/misroute it.
Use realistic mission fixtures (coord topology + a valid minted mid8 — reuse `tests/lane_test_utils.py`).

### T002 — Per-file classify + group
In `commit_for_mission`, before the single `resolve_placement_only` call: for each file compute
`kind_f = kind_for_mission_file(file, mission_slug=mission_slug)`, `surface_f = PRIMARY if
is_primary_artifact_kind(kind_f) else PLACEMENT`. Group files by `surface_f`.

### T003 — None-fallback + single-partition fast path
`None`-classified files (`kind_f is None`) fall back to the **caller-supplied `kind`** group — never
dropped, never coerced. If all files share one partition (the common case), keep the **exact current
fast path**: one `resolve_placement_only` + one commit, no behavioural change.

### T004 — Per-group commit + INV-C1
For each partition group, resolve its `CommitTarget` (`resolve_placement_only(kind=<representative
kind of group>)`) and commit via the existing materialize-then-retry path (PLACEMENT groups use the
coord-worktree path). Add the INV-C1 assertion: no file committed to a ref other than its partition's.
Decide split-and-commit (a, preferred) vs guard-reject (b) — pin one in the test; document rationale
in `traces/design-decisions.md`.

### T005 — Quality + tracer
`ruff` + `mypy` zero issues on the diff; keep `commit_for_mission` complexity ≤15 (extract a
`_group_files_by_partition` helper if needed, with its own focused test). Append the chosen shape +
rationale to `traces/design-decisions.md`.

## Branch Strategy

Planning branch: `design/read-surface-ssot-closeout`. Final merge target:
`design/read-surface-ssot-closeout`. Execution worktrees are allocated per computed lane from
`lanes.json` — run `spec-kitty agent action implement WP01 --agent <name>`.

## Definition of Done
- [ ] RED-1 + RED-2 proven red pre-fix, green post-fix.
- [ ] Mixed batch: each file on its partition ref (INV-C1). None-file: lands via caller-kind fallback.
- [ ] Single-partition batch unchanged (fast path); C-002 mapping untouched.
- [ ] `spec_commit_cmd.py` + `mission_finalize.py` fixed by construction (no edits to them).
- [ ] ruff/mypy clean; complexity ≤15; tracer updated.

## Reviewer guidance (opus / reviewer-renata)
Verify the fix is at the SEAM (not per-caller). Confirm the `None`-fallback path and the
single-partition fast path both have tests. Confirm no kind→partition membership changed (C-002).
Check the red-first tests genuinely fail against pre-fix code.

## Activity Log

- 2026-07-08T07:30:36Z – claude:sonnet:python-pedro:implementer – shell_pid=2434298 – Assigned agent via action command
- 2026-07-08T07:56:16Z – claude:sonnet:python-pedro:implementer – shell_pid=2434298 – Ready: per-file partition-aware seam (split-and-commit, coalesced by resolved ref for coordless topologies), red-first RED-1/RED-2 proven + green, ruff/mypy clean, fast-path preserved, no regressions in full commit_router/status suite sweep
- 2026-07-08T07:58:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=2700616 – Started review via action command
- 2026-07-08T08:07:58Z – user – shell_pid=2700616 – Review passed (renata, opus): C-006 seam fix, red-first RED-1 proven against pre-fix, ref-coincidence merge SOUND (splits only on genuine ref divergence, INV-C1 preserved, #2404 not reintroduced, #2155 atomic bundle preserved), fast-path byte-identical, 279 tests green. --force: blocked only by shared-traces divergence (mission-level, not a WP01 defect).
