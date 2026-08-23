---
work_package_id: WP01
title: Authoritative Domain Cycle Gate
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-009
- FR-010
planning_base_branch: fix/reject-cyclic-lane-graphs
merge_target_branch: fix/reject-cyclic-lane-graphs
branch_strategy: Planning artifacts for this mission were generated on fix/reject-cyclic-lane-graphs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reject-cyclic-lane-graphs unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundational MVP
history:
- at: '2026-08-23T14:06:21Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent:
- tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/compute.py
- tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py
- tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Authoritative Domain Cycle Gate

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Objective

Make `compute_lanes` the non-bypassable acceptance gate for the complete post-collapse execution-lane dependency graph. A cyclic result must raise a typed, deterministic domain error before depth calculation and before any `LanesManifest` is returned.

## Context

Read these mission artifacts before editing:

- `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/spec.md`, especially FR-001, FR-002, FR-005, FR-009, FR-010 and C-001/C-003.
- `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/plan.md`, sections Design 1–3.
- `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/research.md`, R-001 through R-004.
- `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/data-model.md` for normalized value invariants.

The relevant production seam is `src/specify_cli/lanes/compute.py`:

1. WPs are separated into code and planning-artifact groups.
2. Ownership/surface overlap collapses code WPs.
3. `wp_to_lane` and the complete `lane_deps` mapping are built.
4. `_compute_lane_depths` currently tolerates cycles as depth-zero anchors.

The new check belongs between steps 3 and 4. Do not move it into callers or persistence.

## Branch Strategy

- Planning base branch: `fix/reject-cyclic-lane-graphs`
- Final local merge target: `fix/reject-cyclic-lane-graphs`
- This WP has no dependency WP and is allocated to its execution worktree from the lane computed in `lanes.json`.
- Work only inside the declared `owned_files`; do not edit mission planning artifacts from the execution worktree.

## Subtasks and Detailed Guidance

### T001 — Add red-first detector and computation tests

Create `tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py` before production changes.

Cover the pure intended behavior:

- clean DAG returns no cycle;
- self-loop returns `("lane-a", "lane-a")` if self-loops are possible at the helper boundary;
- two-lane and three-lane directed cycles return closed paths;
- multiple cycles select the first encountered by sorted root and neighbor traversal;
- a cycle is rotated to its smallest member without reversing edge direction;
- set and mapping insertion order do not affect the returned tuple;
- `cycle_lanes` order follows first appearance and `wp_ids` are sorted.
- a directed cycle containing more nodes than `sys.getrecursionlimit()` raises the typed cycle error without `RecursionError`.

Declare the mandatory module-level taxonomy in the new file:

```python
pytestmark = [pytest.mark.unit, pytest.mark.fast]
```

Also build the real regression shape from issue #3431: an authored acyclic WP graph whose overlap unions cause the final execution lanes to depend on each other. Assert `compute_lanes` raises the typed error rather than returning a manifest.

Keep fixtures small and name their edges explicitly. The graph convention is “node depends on listed nodes”; test assertions must respect that direction.

Run the new file and confirm failure for the missing behavior, not import/setup noise.

### T002 — Define immutable structured diagnostics

In `src/specify_cli/lanes/compute.py`, introduce the smallest typed domain representation that satisfies the plan:

- `CycleLane` (or an equivalently named frozen value) with `lane_id: str` and `wp_ids: tuple[str, ...]`;
- `LaneDependencyCycleError(LaneComputationError)`;
- stable class or instance `error_code = "LANE_DEPENDENCY_CYCLE"`;
- immutable `cycle_path: tuple[str, ...]`;
- immutable `cycle_lanes: tuple[CycleLane, ...]`;
- a useful `str(error)` message naming the closed path.

Do not embed Rich markup, JSON dictionaries, Typer exits, filesystem paths, or mutation behavior in these values. The exception should be safe for broad existing `LaneComputationError` catches.

Add type annotations and docstrings consistent with Python 3.11 and the module style. Avoid exporting new public symbols unless consumers require them; if the CLI must import the error, that class is the intended public seam.

### T003 — Implement deterministic directed-cycle selection

Add a pure iterative helper such as `_find_lane_dependency_cycle(lane_deps)`.

Required algorithm behavior:

1. Traverse all lane IDs lexically.
2. Traverse each lane's dependencies lexically.
3. Track unvisited/active/completed state plus an explicit traversal stack and active-stack index.
4. On the first back edge to an active node, slice the directed cycle from the stack and close it by repeating the first node.
5. Rotate unique members so the smallest lane ID begins the path; append it again to close.
6. Preserve direction. Never sort the cycle members into a new adjacency order.
7. Stop after the first cycle; do not enumerate all cycles.

The helper should be O(V + E) apart from deterministic sorting. Recursive DFS is not acceptable: FR-010 declares no lane-count ceiling, so a graph beyond Python's recursion limit must still terminate with `LaneDependencyCycleError`. The 100-lane governed performance fixture is mandatory but is not the correctness ceiling.

Do not reuse `core.dependency_graph.detect_cycles` unchanged: it has different collection and ordering behavior.

### T004 — Enforce inside `compute_lanes`

Call the helper exactly once after every code and `lane-planning` edge has been added to `lane_deps`, and before `_compute_lane_depths`.

When a cycle is present:

1. Build lane-to-WP membership from the already computed assignment.
2. Include `lane-planning` membership when it appears.
3. Follow unique lane order from the normalized path, excluding the repeated closer.
4. Sort every lane's WP IDs.
5. Raise `LaneDependencyCycleError` immediately.

No manifest should be returned, no depth should be treated as accepted, and no caller flag should disable this gate. Empty graphs and planning-artifact-only graphs must retain their current valid behavior; if a planning-only early return makes a cycle impossible, keep that narrow return rather than inventing dependencies.

Update the `compute_lanes` docstring so “ready for persistence” explicitly implies an acyclic graph or documents the typed rejection.

### T005 — Reconcile cycle-safety coverage and verify

Update `tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py`:

- retain the direct `_compute_lane_depths` self-loop and multi-node cycle tests;
- retain clean-DAG depth assertions;
- change the public `compute_lanes` cyclic test to expect `LaneDependencyCycleError` and inspect its structured fields;
- update the module/test prose so it no longer says public computation accepts cycles.

Run:

```bash
uv run pytest \
  tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py \
  tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py \
  tests/lanes/test_compute.py -q
uv run ruff check src/specify_cli/lanes/compute.py tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py
uv run mypy --strict src/specify_cli/lanes/compute.py
```

If an unrelated failure is demonstrably pre-existing, follow charter DIR-013 before accepting it as baseline.

## Test Strategy

Tests are mandatory. Follow ATDD-first discipline: land the failing acceptance shape before the production gate, then make it green. Assert stable value fields, not incidental message punctuation, except for the requirement that the human message identify the path.

## Implementation Boundaries

- Do not modify ownership-collapse rules or union-find grouping to avoid producing the cycle; the mission requires detection of the final graph, not automatic repair.
- Do not add a caller flag such as `validate=True`; accepted-manifest acyclicity is unconditional.
- Do not place the error values in `lanes/models.py` unless an actual dependency or import-cycle constraint requires it. Locality favors the computation module used by the exception consumer.
- Do not change `write_lanes_json`; WP02 proves invalid results never reach it.
- Do not alter the generic authored-WP dependency validator. It operates before collapse and protects a distinct invariant.
- Do not use global mutable traversal state; each helper invocation must be isolated and repeatable.

## Evidence to Capture

In the Activity Log, record:

1. The red-test command and the expected failure reason before implementation.
2. The exact normalized path from the multiple-cycle fixture.
3. The green focused-test count.
4. Ruff and strict-mypy results.
5. Any intentional update to an existing assertion and why the old assertion contradicted FR-001/FR-002.

Include a compact diff summary separating the domain value, detector, enforcement seam, and test changes. This gives the reviewer a direct proof trail without requiring them to reconstruct intent from commit order.

## Definition of Done

- `compute_lanes` cannot return a cyclic final graph.
- Detector selection and normalization match the specification exactly.
- The typed exception contains no presentation-layer behavior.
- Planning-lane membership is representable in the diagnostic.
- Direct depth helper remains recursion-safe.
- Valid lane computation tests remain green.
- Focused pytest, ruff, and strict mypy commands have been run and recorded.

## Risks and Mitigations

- **Risk**: reconstructing a path in the wrong edge direction. **Mitigation**: assert every adjacent reported pair exists in the input dependency relation.
- **Risk**: set iteration leaks nondeterminism. **Mitigation**: sorted traversal at every choice point plus permutation tests.
- **Risk**: new behavior breaks a test by design. **Mitigation**: update only the contradictory public acceptance assertion; retain low-level safety assertions.
- **Risk**: optional caller validation reappears. **Mitigation**: reviewer verifies the gate is unconditional inside `compute_lanes`.

## Reviewer Guidance

Reject the WP if cycle validation is caller-managed, occurs after depth calculation, returns only a string, or mutates persistence. Verify the normalized path preserves directed adjacency and the exception remains a `LaneComputationError` subclass.

## Activity Log

- 2026-08-23T14:06:21Z – system – Prompt created.
