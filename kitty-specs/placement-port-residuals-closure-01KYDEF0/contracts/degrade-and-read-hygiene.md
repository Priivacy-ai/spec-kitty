# Contract — Degrade unification & best-effort read (FR-005, FR-006)

## C-DEGRADE-1 — One kind-parameterized write-target degrade helper (FR-005)

**Given** any of the three write surfaces (`events/decision_log.py`, `git/bookkeeping_commit.py`, `coordination/status_transition.py`) resolving a write target when the mission is not fully bootstrapped,
**Then** all three route through one shared `resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref)` in `src/mission_runtime/`,
**And** the two verbatim `_mission_meta_exists` clones are deleted,
**And** the helper is **kind-parameterized**: coord kinds (`STATUS_STATE`, …) degrade to the coord ref; primary kinds to the primary home — never flatten coord onto PRIMARY (C-004).

**Behavior-change coverage**: routing `status_transition._resolve_write_target` through the helper ADDS a `_mission_meta_exists` pre-gate it lacks today — cover the new pre-gate branch with a focused test.

**Red-first**: assert the three paths degrade through the shared helper in the bootstrap window, with `STATUS_STATE` resolving to the coord ref (a test asserting a single uniform ref would be wrong and is explicitly disallowed).

**Measure (SC-004)**: exactly 1 canonical implementation remains; 0 verbatim clones.

## C-READ-1 — `_load_traces` degrades on deleted coord (FR-006)

**Given** `generate_retrospective(...)` on a coord mission whose `coordination_branch` no longer exists,
**When** `_load_traces` calls `placement_seam(...).read_dir(TRACER_FILE)`,
**Then** the call is wrapped in `except (CoordinationBranchDeleted, StatusReadPathNotFound): return []` and generation completes with no traces (no crash).

**Scope (C-003)**: only this single call site — do NOT widen the except to bare `Exception`, and do NOT touch #2922's broader read-side set.

**Red-first**: `generate_retrospective` on a deleted-coord mission raises today; after the guard it returns `[]` traces. Entry point: `generate_retrospective` / `spec-kitty agent retrospect`.
