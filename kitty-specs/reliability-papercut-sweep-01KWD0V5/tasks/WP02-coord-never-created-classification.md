---
work_package_id: WP02
title: Coord never-created classification & remediation logic
dependencies: []
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: fix/reliability-papercut-sweep
merge_target_branch: fix/reliability-papercut-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/reliability-papercut-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reliability-papercut-sweep unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "655275"
history:
- at: '2026-06-30T20:12:14Z'
  actor: claude
  note: WP authored from IC-02; C-001 read_topology purity pin (post-plan squad)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/surface_resolver.py
create_intent:
- tests/specify_cli/coordination/test_coord_never_created.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/surface_resolver.py
- src/specify_cli/migration/backfill_topology.py
- tests/specify_cli/coordination/test_coord_never_created.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries before proceeding.

## Objective

A flat mission whose `meta.json` declares a `coordination_branch` that was **never created**
must not be classified as a healthy `coord` topology, and its remediation must **lead with
"flatten the mission"**. Fix this WITHOUT changing the pure topology SSOT. (FR-002 / #2250)

## Context & BINDING constraint (C-001)

- `src/mission_runtime/context.py` — `classify_topology(coordination_branch, has_lanes)` (~:70) is
  a **pure** `(str|None, bool) → MissionTopology` mapper with 6 consumers. **DO NOT add I/O or a
  git probe here.**
- `src/specify_cli/migration/backfill_topology.py` — exports `read_topology` (→ `_derive_topology`
  → `classify_topology`), which is **consumed by Lane B's `runtime/next/runtime_bridge.py:173,189`**
  plus `src/mission_runtime/resolution.py:764` and `coordination/status_transition.py:601`. **DO NOT
  git-probe inside `read_topology`/`_derive_topology`** — that would silently reclassify a
  never-created branch for Lane B too (cross-lane behavioral shift). Keep `read_topology` pure.
- `src/specify_cli/coordination/surface_resolver.py` — `_coord_branch_exists` (:368, one
  `git rev-parse`, fails closed). `probe_coord_state` / `CoordState` are **defined in
  `src/specify_cli/missions/_read_path_resolver.py:281/:253`** and imported into surface_resolver
  (lines 59-60); T008 edits the **call-site** in `surface_resolver.py:763-772`, not the function
  body. The `CoordinationBranchDeleted` remediation (class `:175`, `next_step` string **:202-207**)
  currently leads with husk-remove, not flatten. (NOTE: `:110-120` is `_COORD_EMPTY_FALLBACK_WARNING`,
  a different surface — the string to reorder is `:202-207`.)
- Precedent: **#2219** (closed, backfill-topology repo-global). Cite it.

## Subtasks

### T006 — Red-first: declared-but-absent coord branch must not be healthy `coord`  [P]
Add `tests/specify_cli/coordination/test_coord_never_created.py`: fixture mission with
`meta.json` declaring a `coordination_branch` absent from git. Assert (a) the backfill/resolver
path does NOT treat it as healthy `coord`, and (b) the surfaced remediation leads with flatten.
RED on pre-fix code.

### T007 — Git-existence probe at the backfill WRITE path (REUSE the canonical probe; read stays pure)
In `migration/backfill_topology.py` (which has no git import today), add the git-existence check at
the **write/migrate** path (`backfill_mission_topology`), NOT in `read_topology`/`_derive_topology`.
**REUSE the canonical seam — `probe_coord_state(...) -> CoordState` (defined in
`src/specify_cli/missions/_read_path_resolver.py:281`, which already discriminates `UNMATERIALIZED`
vs `DELETED` and reuses `_coord_branch_exists` verbatim), or at minimum `_coord_branch_exists`
(`surface_resolver.py:368`)** — imported lazily to avoid a layer cycle. Do NOT add a fresh
`git rev-parse` (that would be a 4th parallel coord-existence probe). A declared branch absent from
git must not be backfilled/persisted as healthy `coord`. Leave `read_topology` and
`classify_topology` byte-for-byte behavior-identical.

### T008 — Lead remediation with flatten in surface_resolver
Reorder the `CoordinationBranchDeleted` remediation (and the never-created branch of
`probe_coord_state`) in `surface_resolver.py` to lead with "flatten the mission" for the
never-created case, reusing `_coord_branch_exists`. Scope to remediation ordering + classification
— NOT a reflog-grade never-vs-torn-down provenance distinction (not reliably possible).

### T009 — Purity regression guard
Add assertions (in the new test or a focused unit test) that `classify_topology` and `read_topology`
remain pure: same inputs → same outputs as pre-fix, no git calls. This guards C-001 against
future drift.

## Branch Strategy

Planning/base + merge target: `fix/reliability-papercut-sweep`. Worktrees allocated per `lanes.json`.
Run `spec-kitty agent action implement WP02 --agent claude`. **WP03 depends on this WP** (shared
`_coordination_doctor.py` is owned by WP03) — WP02 lands first.

## Definition of Done

- T006 RED pre-fix, GREEN after.
- A declared-but-absent coord branch is not classified healthy `coord`; remediation leads with flatten.
- `classify_topology` AND `read_topology` provably unchanged (purity guard green) — C-001 held.
- No edit to `_coordination_doctor.py` (that surface belongs to WP03).
- ruff + mypy clean; complexity ≤ 15.

## Reviewer guidance

The critical check: confirm the git probe is at the backfill WRITE path / surface_resolver, and
that `read_topology`/`classify_topology` are untouched (grep + run their unit tests). Verify no
Lane B consumer (runtime_bridge, resolution, status_transition) changes behavior. Confirm scope
stays at "lead-with-flatten", not provenance.

## Activity Log

- 2026-06-30T21:21:51Z – claude:sonnet:python-pedro:implementer – shell_pid=590810 – Assigned agent via action command
- 2026-06-30T21:36:38Z – claude:sonnet:python-pedro:implementer – shell_pid=590810 – Ready: reuses probe_coord_state/_coord_branch_exists seam, C-001 pure (read_topology/classify_topology untouched), T006 red-first green post-fix, T009 purity guards green, ruff+mypy clean
- 2026-06-30T21:37:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=655275 – Started review via action command
- 2026-06-30T21:49:25Z – user – shell_pid=655275 – Review passed: C-001 held (classify_topology/read_topology/_derive_topology byte-unchanged, pure-no-subprocess guards green); git probe added at backfill WRITE path only, reusing canonical _coord_branch_exists seam (no fresh rev-parse); remediation now leads with flatten; red-first verified (T006a backfill wrote->skip, T006b doctor-first->flatten-first both FAIL pre-fix, PASS post-fix); _coordination_doctor.py untouched (WP03); 26/26 + topology seam 18/18 green; ruff+mypy clean
