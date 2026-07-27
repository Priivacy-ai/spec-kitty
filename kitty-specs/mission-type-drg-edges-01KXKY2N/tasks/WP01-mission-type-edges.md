---
work_package_id: WP01
title: Mission-type edges → regenerate the monolith
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-005
tracker_refs: []
planning_base_branch: feat/mission-type-drg-edges
merge_target_branch: feat/mission-type-drg-edges
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-drg-edges. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-drg-edges unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "164313"
shell_pid_created_at: "1784189787.52"
history:
- Seeded by /spec-kitty.tasks (edges-first two-phase decomposition)
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/migration/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/drg/migration/extractor.py
- src/doctrine/drg/models.py
- src/doctrine/graph.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its lens, standards, and TDD workflow for the entirety of this work package.

## Objective

**Phase 1, #2677.** Emit `mission_type:X → action:X/<step>` `requires` edges (one per step in each built-in
mission type's `action_sequence`), regenerate the **single-file monolith** `src/doctrine/graph.yaml`, and
commit it byte-identically. This de-orphans the 8 nodes #2651 minted (mission_type ×4 + action:plan ×4) and
brings the shipped-graph orphan count from **18 → 10** (≤ the unchanged ceiling of 14). Do **not** touch the
sharding surface — that is Phase 2 (WP03–WP06). You are working against the monolith on purpose.

**ATDD red-first is demonstrated INSIDE this WP (DD-12).** Author a minimal failing assertion first — e.g. a
throwaway/kept test that `mission_type:plan` has an outbound `requires` edge — run it, watch it RED against the
current edge-free generator, THEN implement T001-T002 to green. Do not skip the observed-red step; the charter
requires red-first and WP02 (which `depends: WP01`) cannot observe it across the seam. WP02 is the comprehensive
green-pinning + re-pin + residual follow-on, NOT the red-first owner.

## Context

- `#2651` created `mission_type:<id>` and `action:<type>/<step>` nodes but deferred edges —
  `src/doctrine/drg/models.py:46` reads `MISSION_TYPE = "mission_type"  # (nodes only, no edges yet)`.
- The generator is `src/doctrine/drg/migration/extractor.py`. `generate_graph` (~:811) composes extraction +
  calibration and writes via `_write_graph_yaml` (~:891). `_discover_mission_type_nodes` (~:768) already
  mints the mission_type nodes — your new pass is its sibling.
- The 21 edges = software-dev 5 + documentation 7 + research 5 + plan 4 (`action_sequence` lengths in
  `src/doctrine/missions/mission_types/<id>.yaml`). Verified against the live tree; every step has a matching
  `actions/<step>/` index dir (zero dangling).
- Relation is `Relation.REQUIRES` (cascade-aligned; C-004/C-006 — grounded in the #883 brief, do not improvise).

## Subtasks

### T001 — `extract_mission_type_edges(doctrine_root) -> list[DRGEdge]`

Add a new pass in `extractor.py`, sibling of `_discover_mission_type_nodes` (~:768). For each
`mission_types/<id>.yaml`, read `action_sequence`; for each `<step>` emit
`DRGEdge(source=f"mission_type:{id}", target=f"action:{id}/{step}", relation=Relation.REQUIRES)`.

- Reuse the existing mission-type-file discovery helper `_discover_mission_type_nodes` uses (do not re-glob
  ad hoc — canonical source).
- If a `"missions"` (or similar) path literal now appears ≥3× in the module, hoist it to a module constant
  (Sonar S1192).
- Keep the function a linear read→emit loop (complexity ≤ 15).
- **Edge case**: `retrospect` is in no `action_sequence` — do **not** synthesize an edge for it (it is already
  non-orphan via `scope`). Only emit for steps actually listed.

### T002 — Concatenate into `all_edges` before calibration

Wire the new edges into `all_edges` (~:847, a list concatenation) **before** `calibrate_surfaces` (~:851) and
the deterministic `(source,target,relation)` sort (~:866-871), so calibration and ordering treat them
uniformly. Duplicate-edge safety is enforced downstream by `assert_valid` (there is no `_add_edge` dedup
helper at this seam) — ensure the pass emits each edge once (NFR-001).

### T003 — `_KIND_MAP` entry + retire the stale caveat (C-007)

Add `"mission_type": NodeKind.MISSION_TYPE` to `_KIND_MAP` (`extractor.py:122-131`). Today the mission_type
nodes are pre-created in Step 4b so the backfill loop never fires for them — but the backfill silently drops
endpoints missing from `_KIND_MAP`, so the entry is safer against future partial-node states. Update the
now-obsolete docstring caveat at ~`:778` ("Nodes only … do not add a `_KIND_MAP` entry until edges exist").

### T004 — Correct the `models.py:46` comment (FR-005)

Change `MISSION_TYPE = "mission_type"  # URN prefix: "mission_type:<id>" (nodes only, no edges yet)` to state
that mission_type nodes now carry `requires` edges to their actions.

### T005 — Regenerate + commit the monolith (byte-identity)

Run `spec-kitty doctrine regenerate-graph` and commit the regenerated `src/doctrine/graph.yaml` in this WP.
**Expect a diff wider than 21 lines** — `calibrate_surfaces` reweights existing edges once the new edges
join `all_edges` (C-008); this is expected, not a bug. Do **not** hand-edit `graph.yaml`; it is generated.

## Branch Strategy

- Planning/base branch: **`feat/mission-type-drg-edges`**. Final merge target: **`feat/mission-type-drg-edges`**.
- Execution worktrees are allocated per computed lane from `lanes.json` after finalize — enter the workspace
  the implement command resolves; do not reconstruct the path.
- No dependencies: `spec-kitty agent action implement WP01 --agent claude`.

## Test strategy

WP02 owns the assertions (ATDD RED-first, committed before this code lands in the merge order). For your own
loop: after T005, run the focused DRG tests and `assert_valid`:
```
uv run pytest tests/doctrine/drg -q
uv run spec-kitty doctrine regenerate-graph --check
```

## Definition of Done

- [ ] `extract_mission_type_edges` emits 21 edges (5+7+5+4) with `Relation.REQUIRES`; no `retrospect` edge.
- [ ] Edges enter `all_edges` before calibration/sort; no duplicate/dangling/cycle (`assert_valid` passes).
- [ ] `_KIND_MAP` gains `"mission_type"`; `:778` caveat retired; `models.py:46` comment corrected.
- [ ] `src/doctrine/graph.yaml` regenerated + committed; `regenerate-graph --check` is fresh (byte-identity).
- [ ] ruff + mypy --strict clean on touched files; zero new suppressions; complexity ≤ 15.

## Risks & reviewer guidance

- **Calibration diff-width (C-008)**: reviewer should expect a broad `graph.yaml` diff; verify via a clean
  re-run of `regenerate-graph --check`, not by eyeballing line count.
- **Ownership note for downstream**: WP05 (Phase 2) will edit this file's `generate_graph`/`_write_graph_yaml`
  write-step as a documented out-of-map edit; you own `extractor.py` here — keep the edge pass cleanly
  separable from the write step so WP05's change is localized.

## Activity Log

- 2026-07-16T08:04:19Z – claude:sonnet:python-pedro:implementer – shell_pid=132762 – Assigned agent via action command
- 2026-07-16T08:15:47Z – claude:sonnet:python-pedro:implementer – shell_pid=132762 – Ready for review: 21 mission_type->action requires edges emitted (sw-dev 5 + docs 7 + research 5 + plan 4), monolith regenerated (regenerate-graph --check fresh), assert_valid green, orphan count 18->10, ruff+mypy --strict clean. NOTE: one stale test tests/doctrine/drg/test_mission_type_nodes.py::test_mission_type_nodes_have_no_incident_edges is now RED by design (pins retired no-edges invariant) - re-pin is WP02's scope per the edges-first/re-pin decomposition; outside WP01 owned_files.
- 2026-07-16T08:16:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=164313 – Started review via action command
- 2026-07-16T08:21:42Z – user – shell_pid=164313 – Review passed: 21 requires edges (sw-dev 5+docs 7+research 5+plan 4), no retrospect; orphans 18->10 <=14 ceiling unchanged; regenerate --check fresh; assert_valid green; ruff+mypy strict clean; only new red is WP02-owned re-pin test.
