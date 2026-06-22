---
verdict: approved
reviewer: reviewer-renata
cycle: 1
---

# WP03 — Pure `resolve_context_for_mission` + retire ALL THREE derivations (review cycle 1)

**Verdict: APPROVED.** This is the mission keystone (FR-004 + FR-006 status-surface leg, the
death-spiral kill). Every DoD item is confirmed from the diff and a live run, not prose. Reviewed
WP03's self-contained commit `fa7f95627` (the 3 owned source files + tests); WP01/WP02 commits
(`cec75f2b6`/`9fbe17c69`) are the lane parents and out of WP03's scope.

## Per-criterion findings

### 1. Pure resolver (NFR-005 / C-003) — KEY ARCHITECTURAL CHECK — PASS
- `resolve_context_for_mission(mission_id, topology, *, ...)` exists in `resolution.py`. Its body
  performs **zero FS/git**: it calls `destination_kind_for_topology(topology)` (pure dict-like
  map over a `frozenset`), builds `CommitTarget` / `BranchRefFragment` /
  `ArtifactPlacementFragment` in-memory, and projects the **PURE door**
  `build_execution_context(**fields)`. No `open`/`read_text`/`load_meta`/`subprocess`/`git`/
  `*.exists()`/`*.stat()`/`_assemble_core_fragments` in the body. It does NOT construct
  `ExecutionContext` directly (door projection only) and does NOT re-read meta/lanes/git.
- The shell (`resolve_placement_only` `:1055`, `resolve_action_context` `:1105`) assembles
  fragments via `_assemble_core_fragments` and reads the stored topology via the new
  `_resolve_topology` (the SHELL reader — `ensure_topology` disk read lives here, correctly NOT
  in the resolver), then threads them in. SF-1 layer split is honored: the resolver sits one
  layer UP and projects only the pure factory.
- The T016 input-assertion (`_assert_topology_corroborated`) is also pure — it imports WP01's
  `classify_topology` (a pure 2×2 grid function) to compute the signal-implied topology; it does
  NOT read disk.
- **Mutation check — fixture-free purity:** `tests/mission_runtime/test_resolve_context_for_mission_pure.py`
  has ZERO `tmp_path`, ZERO repo init, ZERO `load_meta` monkeypatch (the only "load_meta"/
  "monkeypatch" string is the docstring negation). It builds `IdentityFragment` /
  `BranchRefFragment` / `StatusSurfaceFragment` in-memory with a production-shaped 26-char ULID,
  exercises all 4 topology cells, and covers the T016 mismatch (both topologies named) + the
  identity-mismatch fail-closed. If the resolver leaked I/O this test could not pass. **GREEN
  (19 passed incl. T019 gate).**

### 2. BOTH original derivations retired (FR-004 / SC-001) — PASS
- **(a)** `resolution.py` door (`_assemble_core_fragments`): the
  `if coordination_branch is not None ⇒ COORDINATION else ⇒ FLATTENED` block is GONE. Replaced by
  `destination_kind = destination_kind_for_topology(topology)`. `_resolve_coordination_branch`
  survives as the VALUE reader for the ref string (correct — only the inference-for-decision was
  retired). Stale WP08 docstrings at `:680-694`/`:711-714` updated to describe stored-topology
  classification.
- **(b)** `runtime_bridge.py`: `_mission_declares_coordination_branch` →
  `_mission_routes_through_coordination` reads stored topology via `ensure_topology`. The
  `_coord_path.exists() ⇒ COORDINATION` topology-classification ladder is GONE; the
  decision_target kind is now driven by `coord_routing_topology` (stored). `_coord_path.exists()`
  survives ONLY to select `worktree_root` (materialized → use it; else compose via
  `CoordinationWorkspace.resolve`) — a C-006 transient discrimination, NOT topology
  classification. `DecisionGitLogUnavailable` fail-closed (`:223-229`/`if coord_routing_topology`)
  PRESERVED.
- **T019 AST gate + my own check:** the gate proves zero live classification sites keying on the
  inference; the `_resolve_coordination_branch` value-reader survives as required.

### 3. surface_resolver:600 retired (FR-006 / the squad-expansion third derivation) — PASS
- `resolve_status_surface_with_anchor` gained an optional `topology` param threaded via
  `_resolve_status_surface_dir` → `resolve_status_surface`. The PRIMARY-vs-coord SHAPE is now
  decided by `effective_topology` (`topology` if supplied, else WP01's
  `classify_topology(coord_branch, has_lanes=False)` — the single SSOT, never a parallel
  `coordination_branch is None` inference). The guard
  `if not _topology_uses_coord_surface(effective_topology) or coord_branch is None:` keeps the
  `coord_branch is None` only as a VALUE guard (a coord-routing topology with no recoverable ref
  cannot compose a coord path), documented as such.
- DELETED/EMPTY probe arms intact (see #4).

### 4. C-006 transients PRESERVED (NFR-003) — CRITICAL NO-REGRESSION GATE — PASS (RAN THEM)
- The transient discrimination still uses `probe_coord_state`, NOT stored topology:
  `CoordState.DELETED` hard-fail (`:673`, #1848 `CoordinationBranchDeleted`) and
  `CoordState.EMPTY` loud-primary fallback (`:692`, #1716) are unchanged and reached only on the
  coord-routing path. `DecisionGitLogUnavailable` (#1718/#1848 create-window/coord-deleted)
  preserved in runtime_bridge.
- **Live run (62 passed):** `test_surface_resolver_coord_empty_warning.py`,
  `test_surface_resolver_collapse.py`, `test_surface_resolver.py`,
  `test_aggregate_coord_deleted_contract.py`, `test_decision_log_coord.py`
  (DecisionGitLogUnavailable / #1848), `test_read_path_create_window_invariant.py` (#1718), and
  the WP04 `test_surface_resolution_equivalence.py` differential gate (incl. flattened-stale-coord
  row) ALL GREEN. No transient collapsed into the enum.

### 5. T019 grep/AST gate non-vacuity — PASS
- AST-based (Compare/UnaryOp/BoolOp/Name-truthiness + `*coord*.exists()/.stat()`); covers
  negated/aliased spellings (`not coord_branch`, `coord_branch is None`, ternary IfExp). Flags a
  branch ONLY when it CLASSIFIES (assigns `CommitTargetKind`/`MissionTopology`/`decision_target`),
  correctly excluding value-reads and the C-006 Path-selection transient arm.
- **Three negative controls prove it CAN fail:** `test_negative_control_gate_catches_reintroduced_classifier`
  (negated-alias `not coord_branch ⇒ CommitTargetKind`), `test_negative_control_ternary_classifier_is_caught`
  (IfExp), and `test_value_read_and_transient_arms_are_not_flagged` (benign-not-flagged).
  `test_surface_resolver_600_gate_is_explicitly_covered` belts-and-braces the third derivation
  into the swept set. Not vacuous.

### 6. Scope / C-007 — PASS
- WP03's commit touches ONLY its 3 owned source files + test files (test-stub signature updates
  in `test_status_facade_adoption_wp02.py` / `test_decision_log_coord.py` are minimal, acceptable
  boy-scout). `CommitTargetKind` type NOT deleted (`class CommitTargetKind` still in context.py).
  WP03 did NOT touch `mission_runtime/__init__.py`, `context.py`, or `mission_creation.py` (those
  are WP01/WP02). The expected alphonso NIT-1 signature delta (`topology` param on
  `_assemble_core_fragments` + its two callers + the status-surface chain) is present and is NOT
  scope creep.

### 7. Gates (NFR-004) — PASS (diff-scoped)
- `ruff check` on the 3 owned files: **All checks passed.**
- `mypy` on the 3 owned files: **clean** (`checked 3 source files`, 0 errors in them). The single
  mypy error is in `src/runtime/next/_internal_runtime/schema.py` (external `StructuredError`
  typed `Any`) — that file is byte-identical between WP03 and the lane base, so it is
  **pre-existing**, not WP03's. No new `S1192`, no new suppressions in the diff.

## Known pre-existing item (NOT a WP03 defect) — confirmed
`tests/architectural/test_mission_runtime_surface.py::test_public_surface_matches_contract` is RED
on the lane tip: `assert mission_runtime.__all__ == _PUBLIC_SURFACE` fails at index 10
(`'MissionTopology' != 'StatusSurfaceFragment'`, "3 more items"). The 3 extra symbols
(`MissionTopology`, `classify_topology`, `routes_through_coordination`) were added to
`mission_runtime/__init__.py` by **WP01** (`cec75f2b6`); WP03 did NOT touch `__init__.py`. This is
the WP01 cumulative-gate gap the orchestrator is handling separately. Confirmed pre-existing,
moved on.

## Live evidence summary
- Pure + T019: 19 passed.
- C-006 transients + WP04 equivalence: 62 passed.
- runtime_bridge decision + surface gates + placement_only: 50 passed.
- ruff: clean; mypy: clean on owned files.

The resolver does not leak FS/git, all three derivations route through the single stored-topology
authority, and every C-006 transient guard is green. Keystone holds. **APPROVED** (with `--force`
across the known-benign lane-base divergence — WP03's 3 owned files are verified identical at base,
so no rebase).
