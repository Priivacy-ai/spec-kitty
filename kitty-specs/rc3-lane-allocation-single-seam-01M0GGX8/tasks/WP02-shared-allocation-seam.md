---
work_package_id: WP02
title: Shared allocation seam resolve_lane_base_or_refuse
dependencies: []
requirement_refs:
- C-001
- FR-001
- FR-002
- FR-003
- NFR-001
planning_base_branch: rc3-lane-allocation-single-seam-01M0GGX8
merge_target_branch: rc3-lane-allocation-single-seam-01M0GGX8
branch_strategy: Planning artifacts for this mission were generated on rc3-lane-allocation-single-seam-01M0GGX8. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-lane-allocation-single-seam-01M0GGX8 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-lane-allocation-single-seam-01M0GGX8
base_commit: 2520e7ad4243857b18f3b6c26eb9e14df33b855a
created_at: '2026-08-22T06:28:02.009345+00:00'
subtasks:
- T004
- T005
- T006
- T007
- T008
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent:
- tests/specify_cli/lanes/test_lane_base_seam.py
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/worktree_allocator.py
- tests/specify_cli/lanes/test_lane_base_seam.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objective

Fold M1's two landed helpers — `_guard_base_honorable` (refusal path) and `_resolve_lane_parent`
(positive parent chooser) — into **one** seam `resolve_lane_base_or_refuse` returning a `LaneBaseDecision`,
and route **all four** allocation routes through it so no route can compute a parent ref inline
(FR-001/002/003, NFR-001). This is a **refactor that references M1's diff, not a re-land** (C-001).

**The seam honors `base` or RAISES `UnhonorableBaseError` — it never degrades** to the topology parent
(that silent fallback is exactly #3571). Hence `_or_refuse`, not `_or_degrade`.

## Context

- File: `src/specify_cli/lanes/worktree_allocator.py`. Landed M1 symbols (anchor on symbols, line numbers
  drift): `UnhonorableBaseError` (~:75), `_guard_base_honorable` (~:185), `_resolve_lane_parent` (~:247),
  `allocate_lane_worktree(base=...)` (~:250). Routes: reuse early-return (~:321), crash-recovery (~:368),
  `detached_base` pre-create guard (~:398), `dependency_lane` guard (~:407), fresh-coord create (~:414,
  inside `if coordination_branch is not None:`), fresh-legacy create (~:428).
- Precedent to mirror: `src/mission_runtime/write_target_degrade.py:67` (`resolve_write_target_or_degrade`
  — resolve first, structured return, caller-chosen fail policy).
- Contracts: `contracts/lane-base-seam.md` (signature, INV-0..7). Data model: `data-model.md`
  (`LaneBaseDecision`, `LaneAllocationRoute`). Research: `research.md` D1/D2.
- **Complexity (S3776 ≤ 15):** the seam is a THIN ORCHESTRATOR delegating to the existing flat helpers —
  do NOT inline the four triggers + the chooser into one function (`detached_base` already nests two
  levels). Keep helpers flat and separately unit-tested.

## Subtasks

### T004 — value objects
Add `LaneAllocationRoute` enum (`FRESH_COORD | FRESH_LEGACY | REUSE | CRASH_RECOVERY`) and
`LaneBaseDecision` frozen dataclass (`parent_ref: str`, `base_honored: bool`, `route: LaneAllocationRoute`,
`topology: LaneTopology`). **No `refusal` field** — refusal is only the `UnhonorableBaseError` raise.
Add `LaneTopology` (`COORD | LEGACY`) if not already present. Keep them in `worktree_allocator.py` (or a
small sibling module in `lanes/`) — do not cross the `mission_runtime`/`specify_cli` layer boundary.

### T005 — the seam
Implement `resolve_lane_base_or_refuse(*, base, route, coordination_branch, mission_branch, wp_id,
lane=None, planning_sha=None, repo_root=None) -> LaneBaseDecision`. It DELEGATES:
- calls `_guard_base_honorable(base, <trigger(s) for route>, wp_id, lane=..., planning_sha=..., repo_root=...)`
  (raises `UnhonorableBaseError` on an unhonorable route),
- then returns `LaneBaseDecision(parent_ref=_resolve_lane_parent(base, coordination_branch, mission_branch),
  base_honored=(base is not None), route=route, topology=...)`.
Map each `LaneAllocationRoute` to the trigger(s) `_guard_base_honorable` must check (reuse/crash_recovery
unconditional; fresh routes check `dependency_lane` + `detached_base`).

### T006 — route every route through the seam
Replace the direct `_guard_base_honorable` + `_resolve_lane_parent` call pairs at all four routes with a
single `resolve_lane_base_or_refuse(...)` call each. After this, `_resolve_lane_parent` and
`_guard_base_honorable` are called **only** from inside the seam. No inline
`coordination_branch if … else mission_branch` (or any `base`/`coordination_branch`/`mission_branch`
composition) remains outside the seam. Preserve atomicity: the seam call must precede
`_create_lane_worktree` / `_ensure_mission_branch` on both create routes.

### T007 — docstring regression-pin
Confirm the `--base` docstring on `allocate_lane_worktree` (~:279-287) still says the base is "threaded as
an EXPLICIT parameter (never smuggled through `lanes_manifest.mission_branch`)". Do NOT edit the unrelated
`_merge_recorded_planning_commit` docstring (~:450+). (INV-6 is a regression-pin — M1 already retired the proxy.)

### T008 — red-first tests (`tests/specify_cli/lanes/test_lane_base_seam.py`)
- **INV-0 (genuinely red on main):** assert the seam is the SOLE parent-computer — after this WP,
  `_guard_base_honorable` and `_resolve_lane_parent` are not called from `allocate_lane_worktree` directly
  (only via the seam). Author this to be red against pre-refactor `main`.
- **INV-1:** `base=None` on each of the four routes → `parent_ref` byte-identical to pre-M8 (NFR-001).
- **INV-2:** `base=<ref>` on reuse and crash_recovery → `UnhonorableBaseError` naming the route.
- **INV-7 (atomicity):** after `UnhonorableBaseError` on any route, no lane worktree/branch exists.
- Keep M1's `test_explicit_base_replaces_coord_parent_on_no_dep_lane` GREEN (standing #3571 guard, INV-3).

## Definition of Done
- `resolve_lane_base_or_refuse` exists; all four routes call it; no inline parent-choice remains.
- New tests pass; M1's existing base-honoring tests stay green; guardrails green (see quickstart sweep).
- `.venv/bin/ruff check .` and `.venv/bin/mypy src/` clean, no new suppressions; seam complexity ≤ 15.
- `.venv/bin/python -m pytest tests/specify_cli/lanes/ -q` green.

## Risks
- NFR-001 drift (mitigated by INV-1 per route). S3776 ceiling (thin orchestrator). Atomicity on
  relocating the guard into each route (INV-7).

## Reviewer Guidance
Verify: seam honors-or-raises (never returns a degraded parent); no inline parent-choice survives (this is
what WP3 will enforce structurally); helpers stay flat; NFR-001 parity tests are per-route; the standing
M1 #3571 test is untouched and green.
