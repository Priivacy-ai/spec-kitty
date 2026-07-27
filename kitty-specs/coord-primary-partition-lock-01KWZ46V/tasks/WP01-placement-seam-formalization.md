---
work_package_id: WP01
title: Placement seam formalization (foundation)
dependencies: []
requirement_refs:
- C-001
- C-002
- FR-001
- FR-002
- FR-003
- FR-005
- FR-006
- FR-012
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: design/coord-primary-partition-lock
merge_target_branch: design/coord-primary-partition-lock
branch_strategy: Planning artifacts for this mission were generated on design/coord-primary-partition-lock. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-primary-partition-lock unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1468015"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent:
- tests/mission_runtime/test_placement_seam.py
execution_mode: code_change
owned_files:
- src/mission_runtime/resolution.py
- src/mission_runtime/artifacts.py
- src/mission_runtime/context.py
- tests/mission_runtime/test_placement_seam.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile via `/ad-hoc-profile-load` for
`python-pedro` (implementer). Adopt its identity, governance scope, and boundaries. Then
read `kitty-specs/coord-primary-partition-lock-01KWZ46V/spec.md`, `plan.md`, `research.md`,
`data-model.md`, and `contracts/seam-api.md`.

## Objective

Formalize the **placement seam** as the single kind-aware public authority over the existing
`resolve_action_context` root. This is the foundation every routing WP (WP02–WP05) consumes.
**Do not build a parallel authority** — expose the existing SSOT (`artifact_home_for` /
`MissionArtifactHome`) through two projections. (C-001, Directive-044.)

## Context

- The SSOT already exists: `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` +
  `artifact_home_for()` / `MissionArtifactHome` (`src/mission_runtime/artifacts.py`).
- The derivation root is `resolve_action_context` / `_assemble_artifact_placement_fragment`
  (`resolution.py`); the write projection `resolve_placement_only(...) -> CommitTarget`
  (`resolution.py:1130`) already exists.
- Topology is the 2×2 grid; route ONLY via `routes_through_coordination(stored_topology)`
  (`context.py`). See `data-model.md` invariants P-1, T-1, T-2, H-1, C-1.

## Subtasks

### T001 — Add `write_target(kind)` / `read_dir(kind)` projections
- Expose one authority (the public face of `resolve_action_context`) with:
  - `write_target(kind: MissionArtifactKind) -> CommitTarget` — projects `MissionArtifactHome.commit_target`.
  - `read_dir(kind: MissionArtifactKind) -> Path | ResolvedSurface` — projects `read_surface`.
- Both derive from stored topology + `artifact_home_for`; never from the current checkout.
- Keep the existing leaf resolvers as delegating implementation details (thin authority — do NOT rewrite them).
- **RETROSPECTIVE (squad H-1):** the seam's `RETROSPECTIVE` leg MUST delegate to the existing single authority `resolve_retrospective_home` (`retrospective/writer.py:37`, from #2119) — do NOT compute a second RETROSPECTIVE home. It has its own single-authority test (`tests/retrospective/test_home_resolution_single_authority.py`); a parallel authority is a C-001/Directive-044 violation. WP07 will allow-list `retrospective/writer.py` in the new grammar's boundary.

### T002 — Bind routing to the predicate; assert invariants
- Coord-routing is decided ONLY by `routes_through_coordination(stored_topology)` over `{COORD, LANES_WITH_COORD}`.
- FR-012 (partial): the seam reads the **stored** `meta.json` topology, never an on-disk `-coord` husk.
- Add a guard/assert enforcing P-1 (frozensets disjoint + total) and T-1 (no inline `topology == COORD`).

### T003 — Seam unit tests
- New `tests/mission_runtime/test_placement_seam.py`: parametrize over the full 2×2 topology grid × all 14 `MissionArtifactKind` members; assert `write_target`/`read_dir` land partition-correct (coord kinds → coord surface only when `routes_through_coordination`; primary kinds → primary; non-coord topology → all primary).

### T004 — Consolidate the `_planning_read_dir` wrappers (DRY-only, low-risk)
- The four `_planning_read_dir` copies already delegate to `resolve_planning_read_dir`; repoint them to call `seam.read_dir(kind)` (one shared helper).
- The four call sites live outside this WP's owned files (`mission_feature_resolution.py`, `orchestrator_api/commands.py`, `acceptance/__init__.py`, `agent/mission.py`) — make these as **documented out-of-map edits** (one-line delegation each, with a rationale comment). This is DRY-only; do not refactor those files further.

### T005 — Campsite (Sonar, in-band)
See **Campsite** below. In `artifacts.py`, promote the `'primary'`/`'placement'` surface
literals to a `Surface` enum/constant **as part of the seam** (this is strangle work, and
clears S1192). In `resolution.py`, hoist `FEATURE_CONTEXT_UNRESOLVED` (×4) to a module constant.

## Campsite (Sonar issues in owned files)

| File | Rule | Location | Class | Action |
|------|------|----------|-------|--------|
| `artifacts.py` | S1192 | `'primary'`/`'placement'` surface literals | SAFE (in-band) | Promote to `Surface` enum/constant as part of the seam |
| `resolution.py` | S1192 | `FEATURE_CONTEXT_UNRESOLVED` ×4 (l.319/353/839/1195) | SAFE | Hoist to module constant |
| `resolution.py` | S1192 | action names `'implement'`/`'tasks'`/`'review'` | ADJACENT | Consolidate only if you touch those sites |
| `context.py` | — | clean | — | — |

(The `_planning_read_dir` host files — `orchestrator_api/commands.py`, `acceptance/__init__.py`
— carry OUT-class god-file complexity debt; do NOT clean it here, tracked home = their own decomposition.)

## Branch Strategy

Planning base: `design/coord-primary-partition-lock`. Final merge target:
`design/coord-primary-partition-lock` (mission branch → operator opens PR to `main`).
Execution worktree is allocated per computed lane from `lanes.json` — enter the resolved
workspace via `spec-kitty agent action implement WP01 --agent claude`; do not reconstruct paths.

## Definition of Done

- `write_target`/`read_dir` land on the authority; both derive from stored topology via `artifact_home_for`.
- `test_placement_seam.py` green across 2×2 × 14 kinds.
- The 4 `_planning_read_dir` sites delegate to the seam (documented leeway edits).
- `ruff` + `mypy` clean; every touched function ≤15 complexity; Surface/error-code constants hoisted.
- No parallel placement authority introduced (C-001).

## Risks & Reviewer guidance

- **Thin authority, not a rewrite** — reviewer must reject any duplication of the leaf resolvers' logic.
- Verify `read_dir` for coord kinds resolves via branch ref when the coord worktree is unmaterialized (aligns with WP06 FR-012).
- Confirm the `Surface` constant does not change which surface a kind maps to (C-002).

## Activity Log

- 2026-07-07T21:57:47Z – claude:opus:python-pedro:implementer – shell_pid=1301041 – Assigned agent via action command
- 2026-07-07T22:01:20Z – user – shell_pid=1301041 – Moved to planned
- 2026-07-07T22:01:33Z – claude:sonnet:python-pedro:implementer – shell_pid=1309735 – Started implementation via action command
- 2026-07-07T22:38:45Z – claude:sonnet:python-pedro:implementer – shell_pid=1309735 – Ready for review (handoff completed by orchestrator after implementer stall); 121 seam tests pass, ruff+mypy clean, RETROSPECTIVE delegates to resolve_retrospective_home, seam called live from orchestrator_api+mission_feature_resolution
- 2026-07-07T22:40:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=1468015 – Started review via action command
- 2026-07-07T22:44:20Z – user – shell_pid=1468015 – Review passed (reviewer-renata): PlacementSeam/placement_seam is thin authority, not a fork — write_target delegates to resolve_placement_only, read_dir to resolve_planning_read_dir; RETROSPECTIVE leg delegates to resolve_retrospective_home (H-1, single-authority guard still green 4/4). Surface StrEnum preserves =="primary" comparisons (C-002); FEATURE_CONTEXT_UNRESOLVED hoisted; P-1 assert_partition_invariant guards construction; T-1 source-inspection test forbids inline topology==COORD. 121 seam tests (2x2 x 14 kinds, real production path — non-vacuous) green; ruff+mypy clean. Net context.py diff EMPTY (cruft cleaned). Out-of-map delegation edits at 3 sites + arch-test allow-list extensions (retrospective upward edge; PlacementSeam/placement_seam pinned) all documented/justified — gates strengthened not weakened. Live callers confirmed at mission_feature_resolution.py:105, orchestrator_api/commands.py:360, acceptance:828. Anti-pattern checklist 8/8 PASS.
